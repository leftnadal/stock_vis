"""L2 Peer 도메인 태깅 배치 (L2-ADOPT, D-L2-SOURCE 결정 2).

PEER_OF 쌍에 LLM 도메인 태그를 채택하되, 판정기 거부권(grounded ≤ 0.2)으로 기각→버킷 폴백.
코어 = peer_domain_tagging(커맨드·훅 공유 단일 소스).

    python manage.py tag_peer_domains --dry-run              # CSV만(DB 무기록) — 기본
    python manage.py tag_peer_domains --dry-run --limit 20   # 소표본(HALT/캘리브레이션)
    python manage.py tag_peer_domains --pilot-csv PATH       # ★A3 파일럿: 기존 실험 CSV dry-run(신규 LLM 0)
    python manage.py tag_peer_domains --apply                # ★게이트: DB 기록(비용 발생, 병진 승인 필수)

★안전핀:
  - --dry-run은 DB를 절대 쓰지 않는다(CSV/요약만). relation_domain(승인본) 미기록은 코어가 보장.
  - --apply는 relation_domain_draft·domain_review_status·domain_machine_check만 기록.
  - idempotent·재개: 이미 L2-ADOPT machine_check 있는 쌍은 건너뜀(--force로 재태깅).
  - HALT: JSON 파싱붕괴 > 10%(표본≥10) 또는 서킷/LLM 오류 3회.
"""

import csv
import json
import os
import time
from collections import Counter

from django.core.management.base import BaseCommand

from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.services.peer_domain_tagging import (
    PEER_RELATION_TYPES,
    TAG_SOURCE,
    is_estimate_cell,
    tag_peer_one,
)
from packages.shared.stocks.models import Stock

OUTPUT_DIR = "outputs/peer_domain_tagging"
RATE_SLEEP_S = 4.2  # Gemini free 15 RPM 안전 여유


def _norm_pair(a, b):
    return tuple(sorted((a, b)))


def compute_terciles(pair_min_mcaps):
    """쌍 pair_mcap(=min(a,b)) 리스트 → (t1, t2) 3분위 경계. 빈 리스트면 (None,None)."""
    xs = sorted(m for m in pair_min_mcaps if m is not None)
    if len(xs) < 3:
        return None, None
    return xs[len(xs) // 3], xs[2 * len(xs) // 3]


def tercile_of(pair_mcap, t1, t2):
    if pair_mcap is None or t1 is None:
        return ""
    return "하" if pair_mcap < t1 else ("중" if pair_mcap < t2 else "상")


class Command(BaseCommand):
    help = "PEER_OF 쌍 L2 도메인 태깅(LLM 채택 + 거부권 폴백). --apply는 게이트."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="DB 기록(★게이트, 비용 발생)")
        parser.add_argument("--dry-run", action="store_true", help="DB 무기록·CSV만(기본)")
        parser.add_argument("--limit", type=int, default=0, help="소표본 상한(0=무제한)")
        parser.add_argument("--force", action="store_true", help="이미 태깅된 쌍도 재태깅")
        parser.add_argument("--pilot-csv", type=str, default="",
                            help="A3 파일럿: 기존 실험 CSV를 파이프라인 판정에 태움(신규 LLM 0)")

    def handle(self, *args, **opts):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        if opts["pilot_csv"]:
            self._pilot(opts["pilot_csv"])
            return
        apply_db = opts["apply"]
        dry_run = opts["dry_run"] or not apply_db  # 명시 --apply 아니면 항상 dry-run
        self._run(dry_run=dry_run, limit=opts["limit"], force=opts["force"])

    # ── 쌍 수집 + 컨텍스트 ──
    def _collect_pairs(self, force):
        qs = RelationConfidence.objects.filter(
            relation_type__in=PEER_RELATION_TYPES
        ).exclude(domain_review_status="rejected")
        rows = list(qs.values(
            "symbol_a", "symbol_b", "domain_machine_check",
        ))
        pairs = {}   # norm_pair -> already_tagged(bool)
        for r in rows:
            a, b = r["symbol_a"], r["symbol_b"]
            if a == b:
                continue
            key = _norm_pair(a, b)
            mc = r.get("domain_machine_check") or {}
            tagged = isinstance(mc, dict) and mc.get("source") == TAG_SOURCE
            pairs[key] = pairs.get(key, False) or tagged
        return pairs

    def _run(self, *, dry_run, limit, force):
        pairs = self._collect_pairs(force)
        todo = [p for p, tagged in pairs.items() if force or not tagged]
        skipped_tagged = len(pairs) - len(todo)
        if limit:
            todo = todo[:limit]

        self.stdout.write(
            f"PEER distinct 쌍 {len(pairs)} · 태깅 대상 {len(todo)} "
            f"(이미 태깅 {skipped_tagged} 건너뜀) · dry_run={dry_run}"
        )
        if not todo:
            self.stdout.write("대상 0건 — 종료.")
            return

        syms = {s for p in todo for s in p}
        names = dict(Stock.objects.filter(symbol__in=syms).values_list("symbol", "stock_name"))
        inds = dict(
            Stock.objects.filter(symbol__in=syms)
            .exclude(industry__isnull=True).exclude(industry="")
            .values_list("symbol", "industry")
        )
        descs = dict(Stock.objects.filter(symbol__in=syms).values_list("symbol", "description"))
        mcaps = dict(
            Stock.objects.filter(symbol__in=syms)
            .exclude(market_capitalization__isnull=True).exclude(market_capitalization=0)
            .values_list("symbol", "market_capitalization")
        )

        # tercile 경계(태깅 가능 쌍 pair_mcap 모집단)
        pair_mcaps = []
        for a, b in todo:
            if a in mcaps and b in mcaps:
                pair_mcaps.append(min(float(mcaps[a]), float(mcaps[b])))
        t1, t2 = compute_terciles(pair_mcaps)

        from apps.chain_sight.services.peer_adjudicator import load_dict
        dct = load_dict()

        from apps.market_pulse.llm.client import generate_with_circuit

        def llm_call(system, contents):
            resp = generate_with_circuit(system_instruction=system, contents=contents)
            return getattr(resp, "text", "") or ""

        results = []
        json_fail = circuit_fail = 0
        n = len(todo)
        for i, (a, b) in enumerate(todo, 1):
            pair_mcap = (
                min(float(mcaps[a]), float(mcaps[b])) if a in mcaps and b in mcaps else None
            )
            terc = tercile_of(pair_mcap, t1, t2)
            same = None
            if a in inds and b in inds:
                same = inds[a].strip().lower() == inds[b].strip().lower()
            try:
                out = tag_peer_one(
                    symbol_a=a, symbol_b=b,
                    name_a=names.get(a, ""), name_b=names.get(b, ""),
                    industry_a=inds.get(a, ""), industry_b=inds.get(b, ""),
                    desc_a=descs.get(a, ""), desc_b=descs.get(b, ""),
                    mcap_tercile=terc, industry_same=same, dct=dct, llm_call=llm_call,
                )
            except Exception as e:  # noqa: BLE001 — 서킷/API 오류
                circuit_fail += 1
                self.stderr.write(f"  [{i}/{n}] LLM 오류: {type(e).__name__}: {e}")
                if circuit_fail >= 3:
                    self.stderr.write("HALT: 서킷/LLM 오류 3회 — 중단.")
                    break
                time.sleep(RATE_SLEEP_S)
                continue

            if not out["ok"]:
                json_fail += 1
            results.append(((a, b), terc, same, out))
            if len(results) >= 10 and json_fail / len(results) > 0.10:
                self.stderr.write(
                    f"HALT: JSON 파싱붕괴 {json_fail}/{len(results)} > 10% — 프롬프트 재설계 필요."
                )
                break
            if i % 20 == 0:
                self.stdout.write(f"  진행 {i}/{n} (json_fail={json_fail})")
            time.sleep(RATE_SLEEP_S)

        if not dry_run:
            self._write_db(results)
            self.stdout.write(f"✅ DB 기록 {len(results)}쌍 (draft·status·machine_check, 승인본 무접촉)")
        else:
            self.stdout.write("dry-run: DB 무기록.")

        self._write_csv(results)
        self._write_summary(results, json_fail, circuit_fail)

    # ── DB 기록(쌍 단위 — 방향 엣지 양쪽에 동일 태그. 승인본 relation_domain 무접촉) ──
    def _write_db(self, results):
        from django.db import transaction
        from django.db.models import Q
        with transaction.atomic():
            for (a, b), _terc, _same, out in results:
                RelationConfidence.objects.filter(
                    Q(symbol_a=a, symbol_b=b) | Q(symbol_a=b, symbol_b=a),
                    relation_type__in=PEER_RELATION_TYPES,
                ).update(
                    relation_domain_draft=out["draft"],
                    domain_review_status=out["review_status"],
                    domain_machine_check=out["machine_check"],
                    # relation_domain(승인본)은 절대 미기록(하드 룰)
                )

    def _write_csv(self, results):
        path = os.path.join(OUTPUT_DIR, "peer_tag_batch.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "symbol_pair", "mcap_tercile", "industry_same", "draft_tag",
                "adopted_tag", "review_status", "veto", "veto_reason",
                "is_estimate", "grounded_ratio", "grounded_en", "llm_conf", "json_ok",
            ])
            for (a, b), terc, same, out in results:
                mc = out["machine_check"]
                w.writerow([
                    f"{a}↔{b}", terc, same, out["draft"] or "",
                    out["adopted_tag"] or "", out["review_status"],
                    mc.get("veto"), mc.get("veto_reason"), mc.get("is_estimate"),
                    mc.get("grounded_ratio"), mc.get("grounded_en"),
                    mc.get("llm_conf"), mc.get("json_parse"),
                ])
        self.stdout.write(f"CSV: {path} ({len(results)}행)")

    def _write_summary(self, results, json_fail, circuit_fail):
        status = Counter(out["review_status"] for _, _, _, out in results)
        veto_n = sum(1 for _, _, _, out in results if out["veto"])
        est_n = sum(1 for _, _, _, out in results if out["is_estimate"])
        adopted = sum(1 for _, _, _, out in results if out["adopted_tag"])
        tags = Counter(out["adopted_tag"] for _, _, _, out in results if out["adopted_tag"])
        n = len(results) or 1
        summary = {
            "total": len(results),
            "json_fail": json_fail, "circuit_fail": circuit_fail,
            "review_status": dict(status),
            "adopted": adopted, "veto": veto_n,
            "veto_rate": round(veto_n / n, 4),
            "is_estimate": est_n, "estimate_rate": round(est_n / n, 4),
            "distinct_adopted_tags": len(tags),
            "tag_frequency_top": tags.most_common(30),
        }
        path = os.path.join(OUTPUT_DIR, "summary.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        self.stdout.write(
            f"요약: adopted={adopted} veto={veto_n}({summary['veto_rate']:.1%}) "
            f"estimate={est_n}({summary['estimate_rate']:.1%}) "
            f"status={dict(status)} distinct_tags={len(tags)} json_fail={json_fail} → {path}"
        )

    # ── A3 파일럿: 기존 실험 CSV(㉯ 결과)를 파이프라인 판정에 태움(신규 LLM 0) ──
    def _pilot(self, csv_path):
        if not os.path.exists(csv_path):
            self.stderr.write(f"파일럿 CSV 없음: {csv_path}")
            return
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        # ㉯(variant B)만 대상 — A3 계약.
        b_rows = [r for r in rows if (r.get("prompt_variant") or "").strip().upper() == "B"]
        self.stdout.write(f"파일럿: 전체 {len(rows)}행 중 ㉯(B) {len(b_rows)}행 판정(신규 LLM 0)")

        from apps.chain_sight.services.peer_adjudicator import load_dict, veto
        dct = load_dict()
        syms = {r["symbol_a"] for r in b_rows} | {r["symbol_b"] for r in b_rows}
        descs = dict(Stock.objects.filter(symbol__in=syms).values_list("symbol", "description"))

        adopted = veto_n = est_n = no_claim = 0
        cells = Counter()
        out_rows = []
        from apps.chain_sight.services.peer_adjudicator import ground_claim
        for r in b_rows:
            a, b = r["symbol_a"], r["symbol_b"]
            # 기존 실험 rationale(한국어 claim)에서 claim 추출 — ground_claim 언어무관.
            claim = ""
            raw = (r.get("rationale_B") or "").strip() or (r.get("rationale_A") or "").strip()
            if raw:
                try:
                    claim = json.loads(raw).get("claim", "")
                except Exception:  # noqa: BLE001
                    claim = ""
            g = ground_claim(claim, a, b, descs.get(a, ""), descs.get(b, ""), dct)
            vetoed = veto(g["grounded_ratio"])
            same = (r.get("industry_same") or "").strip() == "동일"
            terc = (r.get("mcap_tercile") or "").strip()
            est = is_estimate_cell(terc, False if (r.get("industry_same") or "").strip() == "상이" else same)
            if vetoed:
                veto_n += 1
            else:
                adopted += 1
            if est:
                est_n += 1
            if g["grounded_ratio"] is None:
                no_claim += 1
            cells[(terc, r.get("industry_same"))] += 1 if vetoed else 0
            out_rows.append({
                "pair": f"{a}↔{b}", "mcap_tercile": terc,
                "industry_same": r.get("industry_same"),
                "llm_tag": r.get("llm_tag", ""),
                "grounded_ratio": g["grounded_ratio"],
                "veto": vetoed, "adopted": not vetoed, "is_estimate": est,
            })
        n = len(b_rows) or 1
        self.stdout.write(
            f"── A3 파일럿 판정: 채택={adopted} 거부권={veto_n}({veto_n/n:.1%}) "
            f"추정라벨={est_n} claim없음={no_claim} ──"
        )
        self.stdout.write(f"── 구획별 거부권: {dict(cells)} ──")
        path = os.path.join(OUTPUT_DIR, "pilot_120.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
        self.stdout.write(f"✅ 파일럿 결과 {len(out_rows)}행 → {path}")
