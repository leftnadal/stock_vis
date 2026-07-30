"""도메인 태깅 캘리브레이션 CSV 재분류 dry-run (⑳-3 S2-C-4).

기존 review_batch.csv(LLM 출력)를 입력으로 gate v2 룰(S2-C-1 자가모순 필터 +
정규화)을 CSV 계층에서만 재적용한다. **LLM·DB 무접촉**(재호출 없음).

    python manage.py reclassify_domain_batch          # review_batch.csv → review_batch_v2.csv

★한계(정직): CSV엔 stock_name·전체 evidence가 없어 S2-C-2 target 재판정은 재현 불가
  (target_in_basis는 v1 값 유지). S2-C-2는 코어 단위테스트로 검증했고, 실효는 차기
  라이브 배치에서 확인한다. 본 재분류의 수치 변화는 S2-C-1(자가모순, 이름 독립)에 기인.
  참고로 심볼 단어경계 실패 auto(오탐 후보)는 symbol_boundary_ok 컬럼으로 표기만 한다.
"""

import csv
import os
import re
from collections import Counter

from django.core.management.base import BaseCommand

from apps.chain_sight.services.domain_tagging import (
    _is_enumeration,
    _norm_type,
    _threshold,
    decide_gate,
    normalize_tag,
)

OUTPUT_DIR = "outputs/domain_tagging"
IN_CSV = os.path.join(OUTPUT_DIR, "review_batch.csv")
OUT_CSV = os.path.join(OUTPUT_DIR, "review_batch_v2.csv")


def _b(x):
    return str(x).strip().lower() in ("true", "1")


def _s(x):
    return (x or "").strip()


class Command(BaseCommand):
    help = "캘리브레이션 CSV를 gate v2로 재분류(dry-run, LLM·DB 무접촉)"

    def handle(self, *args, **opts):
        if not os.path.exists(IN_CSV):
            self.stderr.write(f"입력 없음: {IN_CSV}")
            return
        with open(IN_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        th = _threshold()

        out_rows = []
        gate_v2 = Counter()
        boundary_fp = 0  # 심볼 단어경계 실패인데 auto (오탐 후보)
        for r in rows:
            relation_type = _s(r["relation_type"])
            suggested = _s(r["suggested_type"])
            type_match_ok = _b(r["type_match"])
            conf = float(r["confidence"] or 0)
            basis = _s(r["basis"])
            # CSV 컬럼 → machine_check 재구성(target_in_basis 등은 v1 값 유지)
            mc = {
                "target_in_basis": _b(r["target_in_basis"]),
                "type_signature_ok": _b(r["type_signature_ok"]),
                "confidence_ok": conf >= th,
                "type_match_ok": type_match_ok,
                "suggested_type": suggested or None,
                "self_contradiction": (
                    (not type_match_ok)
                    and bool(suggested)
                    and _norm_type(suggested) == _norm_type(relation_type)
                ),
            }
            gclass, gstatus = decide_gate(mc)
            gate_v2[gclass] += 1

            # 심볼 단어경계 표기(오탐 자문용, gate는 미변경)
            _, other = (_s(r["symbol_pair"]).split("↔") + [""])[:2]
            sym_boundary = bool(other) and re.search(
                rf"\b{re.escape(other)}\b", basis
            ) is not None
            # 오탐 후보 = 짧은 심볼(≤3자)이 substring만 걸리고 단어경계 실패한 auto.
            #   (긴 사명 매칭 auto는 정당 → 제외. CSV엔 사명 없어 심볼 신호만 판별)
            sym_substr = bool(other) and other.lower() in basis.lower()
            if (
                gclass == "auto_candidate" and mc["target_in_basis"]
                and len(other) <= 3 and sym_substr and not sym_boundary
            ):
                boundary_fp += 1

            out_rows.append({
                **r,
                "gate_class_v2": gclass,
                "review_status_v2": gstatus,
                "self_contradiction": mc["self_contradiction"],
                "is_enumeration": _is_enumeration(basis),
                "symbol_boundary_ok": sym_boundary,
                "normalized_tag": normalize_tag(_s(r["draft_domain"])),
            })

        # ── v2 CSV 산출 ──
        fieldnames = list(rows[0].keys()) + [
            "gate_class_v2", "review_status_v2", "self_contradiction",
            "is_enumeration", "symbol_boundary_ok", "normalized_tag",
        ]
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(out_rows)

        # ── A'/B'/C' 구획 ──
        A = gate_v2.get("noise_self_contradiction", 0)   # 자가모순 패턴 일괄
        C = gate_v2.get("auto_candidate", 0)             # auto 스팟
        B = gate_v2.get("pending", 0)                    # 개별 검수
        est_min = (A * 8 + B * 30 + C * 10) // 60
        norm_distinct = len({row["normalized_tag"] for row in out_rows if row["normalized_tag"]})

        self.stdout.write(f"v2 CSV: {OUT_CSV} ({len(out_rows)}행)")
        self.stdout.write(f"gate_class_v2 = {dict(gate_v2)}")
        self.stdout.write(
            f"구획 재산정: A'(자가모순 일괄)={A}  B'(개별)={B}  C'(auto 스팟)={C}  "
            f"합={A + B + C}"
        )
        self.stdout.write(f"예상 검수 ~{est_min}분 (A'8s·B'30s·C'10s)")
        self.stdout.write(f"B'={B} vs 120 → {'감축 미달' if B > 120 else '충족'}")
        self.stdout.write(f"정규화 후 distinct 태그 = {norm_distinct}종")
        self.stdout.write(f"심볼 단어경계 실패 auto(S2-C-2 오탐 후보, 표기만) = {boundary_fp}건")
