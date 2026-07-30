"""관계 도메인 태깅 배치 (⑳-3 S2-B Slice 2/5).

SEC 계열 관계에 LLM 도메인 태그 초안을 산출한다. 코어=domain_tagging(커맨드·훅 공유).

    python manage.py tag_relation_domains --dry-run            # CSV만(DB 무기록) — 이 세션 기본
    python manage.py tag_relation_domains --new-only --dry-run # 미태깅(draft null)만
    python manage.py tag_relation_domains --limit 10 --dry-run # 소표본(캘리브레이션/HALT 검증)
    python manage.py tag_relation_domains --all                # DB 기록(migrate 후 Phase 2, ★승인 필요)

★안전핀: --dry-run은 DB를 절대 쓰지 않는다(CSV/요약만). 승인본(relation_domain) 미기록은 코어가 보장.
HALT: JSON 파싱붕괴 > 10%(표본≥10) 또는 서킷 오픈 반복 → 즉시 중단·보고.
"""

import csv
import json
import os
import time
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.services.domain_tagging import SEC_RELATION_TYPES, tag_one
from packages.shared.stocks.models import Stock

OUTPUT_DIR = "outputs/domain_tagging"
RATE_SLEEP_S = 4.2  # Gemini free 15 RPM 안전 여유


class Command(BaseCommand):
    help = "SEC 계열 관계에 LLM 도메인 태그 초안 산출(자동-C 파이프라인 첫 배치)"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="전체 SEC 관계")
        parser.add_argument("--new-only", action="store_true", help="draft null만")
        parser.add_argument("--dry-run", action="store_true", help="DB 무기록·CSV만(기본 권장)")
        parser.add_argument("--limit", type=int, default=0, help="소표본 상한(0=무제한)")

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]
        new_only = opts["new_only"]
        limit = opts["limit"]

        qs = RelationConfidence.objects.filter(relation_type__in=SEC_RELATION_TYPES)
        if new_only:
            qs = qs.filter(Q(relation_domain_draft__isnull=True))
        qs = qs.order_by("relation_type", "symbol_a", "symbol_b")
        rows = list(qs.values(
            "id", "symbol_a", "symbol_b", "relation_type",
            "relation_status", "truth_score", "relation_basis_summary",
        ))
        if limit:
            rows = rows[:limit]

        if not rows:
            self.stdout.write("대상 0건 — 종료(현재 유입 없음이면 정상).")
            return

        # 사명 조회(machine_check 타깃 실존용)
        syms = {r["symbol_a"] for r in rows} | {r["symbol_b"] for r in rows}
        names = dict(Stock.objects.filter(symbol__in=syms).values_list("symbol", "stock_name"))

        from apps.market_pulse.llm.client import generate_with_circuit

        def llm_call(system, contents):
            resp = generate_with_circuit(system_instruction=system, contents=contents)
            return getattr(resp, "text", "") or ""

        results = []
        json_fail = 0
        circuit_fail = 0
        n = len(rows)
        self.stdout.write(f"대상 {n}건 (dry_run={dry_run}, new_only={new_only})")

        for i, r in enumerate(rows, 1):
            # center = symbol_a 기준(엣지 방향 무관, 타깃=반대편)
            try:
                out = tag_one(
                    symbol_a=r["symbol_a"], symbol_b=r["symbol_b"], center=r["symbol_a"],
                    relation_type=r["relation_type"],
                    basis=r["relation_basis_summary"] or "",
                    target_name=names.get(r["symbol_b"], ""),
                    llm_call=llm_call,
                )
            except Exception as e:  # 서킷 오픈·API 오류
                circuit_fail += 1
                self.stderr.write(f"  [{i}/{n}] LLM 오류: {type(e).__name__}: {e}")
                if circuit_fail >= 3:
                    self.stderr.write("HALT: 서킷/LLM 오류 3회 — 중단.")
                    break
                time.sleep(RATE_SLEEP_S)
                continue

            if not out["ok"]:
                json_fail += 1
            results.append((r, out))

            # HALT: JSON 붕괴 > 10% (표본 ≥ 10)
            if len(results) >= 10 and json_fail / len(results) > 0.10:
                self.stderr.write(
                    f"HALT: JSON 파싱붕괴 {json_fail}/{len(results)} > 10% — 프롬프트 재설계 필요."
                )
                break

            if i % 20 == 0:
                self.stdout.write(f"  진행 {i}/{n} (json_fail={json_fail})")
            time.sleep(RATE_SLEEP_S)

        # ── DB 기록(비-dry-run, Phase 2·migrate 후) ──
        if not dry_run:
            self._write_db(results)
            self.stdout.write(f"DB 기록 완료: {len(results)}건 (draft·machine_check·status)")
        else:
            self.stdout.write("dry-run: DB 무기록.")

        # ── CSV + 요약 산출 ──
        self._write_csv(results)
        self._write_summary(results, json_fail, circuit_fail)

    # ── DB 기록(승인본 relation_domain 절대 미기록) ──
    def _write_db(self, results):
        from django.db import transaction
        with transaction.atomic():
            for r, out in results:
                RelationConfidence.objects.filter(id=r["id"]).update(
                    relation_domain_draft=out["draft"],
                    domain_review_status=out["review_status"],
                    domain_machine_check=out["machine_check"],
                    # relation_domain(승인본)은 절대 건드리지 않음(검수=Phase 2)
                )

    def _write_csv(self, results):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        path = os.path.join(OUTPUT_DIR, "review_batch.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "symbol_pair", "relation_type", "basis", "draft_domain",
                "type_match", "suggested_type", "gate_class", "review_status",
                "target_in_basis", "type_signature_ok", "confidence", "json_ok",
            ])
            for r, out in results:
                mc = out["machine_check"]
                w.writerow([
                    f'{r["symbol_a"]}↔{r["symbol_b"]}', r["relation_type"],
                    (r["relation_basis_summary"] or "")[:160], out["draft"] or "",
                    mc.get("type_match_ok"), mc.get("suggested_type") or "",
                    out["gate_class"], out["review_status"],
                    mc.get("target_in_basis"), mc.get("type_signature_ok"),
                    mc.get("confidence"), mc.get("json_parse"),
                ])
        self.stdout.write(f"CSV: {path} ({len(results)}행)")

    def _write_summary(self, results, json_fail, circuit_fail):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        gate = Counter(out["gate_class"] for _, out in results)
        status = Counter(out["review_status"] for _, out in results)
        tags = Counter(out["draft"] for _, out in results if out["draft"])
        pending_reasons = Counter()
        for _, out in results:
            if out["gate_class"] != "auto_candidate":
                mc = out["machine_check"]
                if not mc.get("json_parse"):
                    pending_reasons["json_parse_fail"] += 1
                elif mc.get("self_contradiction"):
                    pending_reasons["noise_self_contradiction"] += 1  # S2-C-1
                elif (not mc.get("type_match_ok")) or mc.get("suggested_type"):
                    pending_reasons["type_change_proposed"] += 1
                elif not mc.get("target_in_basis"):
                    pending_reasons["target_not_in_basis"] += 1
                elif not mc.get("type_signature_ok"):
                    pending_reasons["type_signature_fail"] += 1
                elif not mc.get("confidence_ok"):
                    pending_reasons["low_confidence"] += 1
                else:
                    pending_reasons["other"] += 1
        summary = {
            "total": len(results),
            "json_fail": json_fail, "circuit_fail": circuit_fail,
            "gate_class": dict(gate), "review_status": dict(status),
            "pending_reasons": dict(pending_reasons),
            "tag_frequency_top": tags.most_common(30),
            "distinct_tags": len(tags),
        }
        path = os.path.join(OUTPUT_DIR, "summary.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        self.stdout.write(f"요약: {path}")
        self.stdout.write(
            f"  gate={dict(gate)} status={dict(status)} distinct_tags={len(tags)} "
            f"json_fail={json_fail}"
        )
