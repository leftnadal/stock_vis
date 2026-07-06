"""
Heat 합성기 (TH-3, 설계서 theme_heat_design.md v1.2.1 §3 + §2).

양 축(Heat/DSS) 공통 골격:
  1. 성분별 z (계산기가 산출).
  2. 시그모이드 s_i = 1/(1+exp(-z_i)).
  3. 가중합 → ×100 → round.
  4. 밴드 판정 (§3-4).
  5. 결측: 가중치 비례 재분배 + missing_reason. Heat 결측 ≥3 이면 미산출 (§3-5).

가중치는 **상수 모듈** — 합 1.00 을 import 시 assert (§2 표, C2 는 0.18 단일 슬롯이며
내부 C2a 0.12/C2b 0.06 결합은 C2 계산기 책임). z_mode 등 성분별 메타는 components 에 보존.
"""

import math
from typing import Any, Optional

# ── Heat 8성분 가중치 (§2 표) — 합 1.00 ──
HEAT_WEIGHTS = {
    "C1": 0.18,  # 밸류에이션
    "C2": 0.18,  # 공급 반응 (C2a 0.12 + C2b 0.06)
    "C3": 0.14,  # 내러티브 볼륨
    "C4": 0.12,  # ETF 플로우
    "C5": 0.12,  # 투기 심리
    "C6": 0.09,  # 상관 응집
    "C7": 0.09,  # 거래대금
    "C8": 0.08,  # 추정치 리비전 괴리
}

# 설계 강제: 가중치 합 1.00 (부동소수 오차 허용). 위반 시 import 실패 = 조기 발견.
_WEIGHT_SUM = round(sum(HEAT_WEIGHTS.values()), 6)
assert _WEIGHT_SUM == 1.0, f"HEAT_WEIGHTS 합 != 1.00 (={_WEIGHT_SUM})"

# 밴드 임계 (§3-4)
HEAT_OVERHEATED = 70
HEAT_WARNING = 40

# 결측 상한 (§3-5): 결측 성분 ≥ 이 값이면 축 미산출
MISSING_LIMIT = 3


def sigmoid(z: float) -> float:
    """s = 1/(1+exp(-z)). 오버플로 가드."""
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def heat_band(score: int) -> str:
    """§3-4 밴드: 과열 ≥70 / 주의 40~69 / 냉각 <40."""
    if score >= HEAT_OVERHEATED:
        return "overheated"
    if score >= HEAT_WARNING:
        return "warning"
    return "cool"


def _is_present(comp: Optional[dict]) -> bool:
    """성분 유효 여부: dict + z not None + missing_reason 없음."""
    if not comp:
        return False
    if comp.get("missing_reason"):
        return False
    return comp.get("z") is not None


def synthesize_heat(components: dict[str, Any]) -> dict:
    """
    8성분 → Heat 점수/상태/evidence (§3).

    components = {"C1": {"z": float|None, "raw": ..., "missing_reason": str|None}, ...}
    반환 = {score, status, components(s 주석), evidence, missing_count}.
      - 결측 ≥3 → status="not_computed", score=None (§3-5).
      - 그 외 → 결측 가중치를 present 에 비례 재분배 → 가중합 ×100 round → 밴드.
    """
    present = {k: c for k, c in components.items() if k in HEAT_WEIGHTS and _is_present(c)}
    missing_count = len(HEAT_WEIGHTS) - len(present)

    # 성분별 s 주석 (present 만)
    annotated = dict(components)
    for k, c in present.items():
        annotated[k] = {**c, "s": sigmoid(float(c["z"]))}

    if missing_count >= MISSING_LIMIT:
        return {
            "score": None,
            "status": "not_computed",
            "components": annotated,
            "evidence": [],
            "missing_count": missing_count,
        }

    present_weight = sum(HEAT_WEIGHTS[k] for k in present)
    if present_weight <= 0:
        return {
            "score": None, "status": "not_computed",
            "components": annotated, "evidence": [], "missing_count": missing_count,
        }

    # 결측 가중치 비례 재분배 (§3-5): w_i' = w_i / Σ_present w
    weighted = 0.0
    for k, c in present.items():
        w_norm = HEAT_WEIGHTS[k] / present_weight
        weighted += w_norm * sigmoid(float(c["z"]))
    score = round(weighted * 100)

    # evidence: |z| 상위 2 성분 (§10.3)
    evidence = sorted(
        ({"component": k, "z": float(c["z"])} for k, c in present.items()),
        key=lambda e: abs(e["z"]),
        reverse=True,
    )[:2]

    return {
        "score": score,
        "status": heat_band(score),
        "components": annotated,
        "evidence": evidence,
        "missing_count": missing_count,
    }
