"""DSS-QUADRANT 섹터 사분면 payload 조립 (QUAD-IMPL-1 Slice 1).

Heat(ThemeHeatScore) × 수요 breadth(ThemeDemandScore) 2축. read-only 조립(쓰기 0).
화살표 suppression = DSS-FLAT-OBS-1 §2 기계 기준 재사용 — anchor global flat_ratio ≥ 90%면
전 섹터 화살표 숨김(전주 스냅샷 축퇴 = 이동 신뢰 불가). 신규 튜닝 파라미터 0.

결정: D-DSS-QUAD-PLACE/TEMPORAL/ENCODE (DECISIONS 2026-08-27).
경계 x(heat 중앙값)·구역 판정은 FE 순수 함수(Slice 2) 소관 — 여기선 원장 투영만.
"""
from django.db.models import Max

from apps.chain_sight.models import (
    HeatEntity,
    SymbolDemandSignal,
    ThemeDemandScore,
    ThemeHeatScore,
)

# DSS-FLAT-OBS-1 §2 [재발] 임계 재사용 — 신규 노브 아님(문서화된 기존 기준).
SUPPRESS_FLAT_RATIO = 0.90


def _anchor_flat_ratio(anchor):
    """anchor의 global flat_ratio = flat / (n − excluded). §2 정의(SymbolDemandSignal 정본).

    유효분모 0(또는 anchor None)이면 None — suppression 판정에서 미충족으로 취급.
    """
    if anchor is None:
        return None
    n = flat = excl = 0
    for direction, excluded in SymbolDemandSignal.objects.filter(
        anchor_date=anchor
    ).values_list("direction", "excluded"):
        n += 1
        if excluded:
            excl += 1
        elif direction == 0:
            flat += 1
    denom = n - excl
    if denom <= 0:
        return None
    return flat / denom


def build_quadrant() -> dict:
    """11 섹터 × 사분면 행 + 차트 메타. append/write 없음."""
    heat_date = ThemeHeatScore.objects.aggregate(m=Max("date"))["m"]
    anchors = list(
        ThemeDemandScore.objects.values_list("date", flat=True)
        .distinct()
        .order_by("-date")[:2]
    )
    anchor_curr = anchors[0] if anchors else None
    anchor_prev = anchors[1] if len(anchors) > 1 else None

    fr_curr = _anchor_flat_ratio(anchor_curr)
    fr_prev = _anchor_flat_ratio(anchor_prev)
    arrow_suppressed = bool(
        (fr_curr is not None and fr_curr >= SUPPRESS_FLAT_RATIO)
        or (fr_prev is not None and fr_prev >= SUPPRESS_FLAT_RATIO)
    )

    heat_map = {}
    if heat_date is not None:
        heat_map = {
            r["theme__ref_id"]: r["score"]
            for r in ThemeHeatScore.objects.filter(date=heat_date).values(
                "theme__ref_id", "score"
            )
        }

    def _demand_map(anchor):
        if anchor is None:
            return {}
        return {
            r["theme__ref_id"]: (r["components"] or {})
            for r in ThemeDemandScore.objects.filter(date=anchor).values(
                "theme__ref_id", "components"
            )
        }

    dcur = _demand_map(anchor_curr)
    dprev = _demand_map(anchor_prev)

    heat_iso = heat_date.isoformat() if heat_date else None
    ac_iso = anchor_curr.isoformat() if anchor_curr else None
    ap_iso = anchor_prev.isoformat() if anchor_prev else None

    sectors = []
    for ref_id in (
        HeatEntity.objects.filter(kind=HeatEntity.KIND_SECTOR)
        .order_by("ref_id")
        .values_list("ref_id", flat=True)
    ):
        cur = dcur.get(ref_id) or {}
        prev = dprev.get(ref_id) or {}
        sectors.append(
            {
                "sector": ref_id,
                "heat": heat_map.get(ref_id),  # None = 미산출 → FE 하단 목록
                "heat_date": heat_iso,
                "breadth_curr": cur.get("breadth"),
                "breadth_prev": prev.get("breadth"),
                "denom_curr": cur.get("valid_denom"),
                "denom_prev": prev.get("valid_denom"),
                "anchor_curr": ac_iso,
                "anchor_prev": ap_iso,
                "arrow_suppressed": arrow_suppressed,
            }
        )

    return {
        "heat_date": heat_iso,
        "anchor_curr": ac_iso,
        "anchor_prev": ap_iso,
        "arrow_suppressed": arrow_suppressed,
        "flat_ratio_curr": fr_curr,
        "flat_ratio_prev": fr_prev,
        "sectors": sectors,
    }
