"""
Heat beat 오케스트레이션 (TH-5) — 유니버스 → C1~C8 → 신시사이저 → ThemeHeatScore upsert.

설계 앵커 theme_heat_design.md v1.2.2 §7 (`compute_theme_heat_task` 일간 ET 18:00).

배선 범위 (2026-07-09 승인): DB 빌더 있는 **C2(=C2a+C2b)·C8만 실배선**, 나머지 C1·C3·C4·
C5·C6·C7 = missing("not_wired", 각 데이터 파이프라인 후속 슬라이스). 결과적으로 결측 ≥3 →
대부분 not_computed(§6.1 status 미포함 → 저장 안 함). 결정6 로 실전 소비는 어차피 차단.

결정8 (universe_stale): 유니버스 최종 갱신일(SP500Constituent.updated_at max)이 30일 초과면
저장 행 components 에 universe_stale=true + universe_as_of 기록 → 소비층 코드 차단 신호.

섹터 택소노미: HeatEntity.ref_id(Yahoo/FMP 계열) ≠ SP500Constituent.sector(GICS) — 6/11 명칭
불일치(발견 2026-07-09) → HEAT_ENTITY_TO_SP500_SECTOR 매핑으로 비파괴 해소(TASKQUEUE
TH-HEATENTITY-SECTOR-RECONCILE 조율).
"""

import logging
import statistics
from collections import Counter
from datetime import date
from typing import Callable, Optional

from apps.chain_sight.services.filing_service import c2b_from_db
from apps.chain_sight.services.heat_components import (
    c2_supply_reaction,
    c2a_insider_from_db,
    sigmoid,
)
from apps.chain_sight.services.heat_synthesis import HEAT_WEIGHTS, synthesize_heat
from apps.chain_sight.services.universe_snapshot import (
    get_or_create_universe_snapshot,
    sector_constituents,
)

logger = logging.getLogger(__name__)

# 결정8 — 유니버스 stale 임계 (단일 정의)
UNIVERSE_STALE_DAYS = 30

# HeatEntity.ref_id(Yahoo/FMP) → SP500Constituent.sector(GICS) 매핑 (발견 2026-07-09)
HEAT_ENTITY_TO_SP500_SECTOR = {
    "Basic Materials": "Materials",
    "Communication Services": "Communication Services",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Energy": "Energy",
    "Financial Services": "Financials",
    "Healthcare": "Health Care",
    "Industrials": "Industrials",
    "Real Estate": "Real Estate",
    "Technology": "Information Technology",
    "Utilities": "Utilities",
}

# 배선 안 된 성분 — 데이터 파이프라인 후속 슬라이스
_NOT_WIRED = ("C1", "C3", "C4", "C5", "C6", "C7")


# ────────────────────────────── 순수 판정 ──────────────────────────────
def is_universe_stale(universe_as_of: Optional[date], as_of: date) -> bool:
    """유니버스 최종 갱신일이 임계(30일) 초과 → stale (결정8). None → stale."""
    if universe_as_of is None:
        return True
    return (as_of - universe_as_of).days > UNIVERSE_STALE_DAYS


def universe_last_updated_date() -> Optional[date]:
    """유니버스 최종 갱신일 = max(SP500Constituent.updated_at) → date. 없으면 None."""
    from django.db.models import Max

    from packages.shared.stocks.models import SP500Constituent

    dt = SP500Constituent.objects.filter(is_active=True).aggregate(
        m=Max("updated_at")
    )["m"]
    return dt.date() if dt else None


# ────────────────────────────── 성분 조립 ──────────────────────────────
def _aggregate_c8_for_sector(sector_symbols: list[str], c8_by_symbol: dict) -> dict:
    """섹터 C8 = 구성종목 C8_raw 중앙값 + z_mode 다수결(동률 cross_sectional). 없으면 결측."""
    vals, modes = [], []
    for s in sector_symbols:
        c = c8_by_symbol.get(s.upper())
        if c and c.get("z") is not None:
            vals.append(float(c["z"]))
            modes.append(c.get("z_mode"))
    if not vals:
        return {"z": None, "s": None, "raw": None,
                "missing_reason": "c8_no_sector_data", "z_mode": None}
    z = statistics.median(vals)
    # 다수결 — 동률/전무 시 cross_sectional (더 보수적)
    mode = Counter(m for m in modes if m).most_common(1)
    z_mode = mode[0][0] if mode else "cross_sectional"
    return {"z": z, "s": sigmoid(z), "raw": {"n": len(vals)},
            "missing_reason": None, "z_mode": z_mode}


def _real_sector_components(
    sector_symbols: list[str], as_of: date, c8_by_symbol: dict
) -> dict:
    """실배선 성분 dict (C2=C2a+C2b, C8 집계; 나머지 not_wired)."""
    components = {k: {"z": None, "s": None, "raw": None, "missing_reason": "not_wired"}
                  for k in _NOT_WIRED}
    if sector_symbols:
        c2a = c2a_insider_from_db(sector_symbols, as_of)
        c2b = c2b_from_db(sector_symbols, as_of)
        components["C2"] = c2_supply_reaction(c2a, c2b)
    else:
        components["C2"] = {"z": None, "s": None, "raw": None, "missing_reason": "c2_no_symbols"}
    components["C8"] = _aggregate_c8_for_sector(sector_symbols, c8_by_symbol)
    return components


# ────────────────────────────── 오케스트레이션 ──────────────────────────────
def compute_theme_heat(
    as_of: date,
    build_components: Optional[Callable] = None,
    universe_as_of: Optional[date] = None,
) -> list[dict]:
    """
    Heat 일배치 — 유니버스 스냅샷 → 섹터별 C1~C8 → 신시사이저 → ThemeHeatScore upsert(멱등).

    - build_components(entity, sector_symbols) → 8성분 dict. 기본 = 실배선(C2/C8),
      테스트는 fixture 주입.
    - not_computed 섹터(결측 ≥3, §6.1 status 미포함)는 **저장하지 않고 로그**.
    - 저장 행 components 에 universe_stale/universe_as_of 마킹(결정8).
    - upsert = update_or_create(theme, date) 멱등(중복 행 금지).

    반환 = 섹터별 {entity, status, stored, created}.
    """
    from apps.chain_sight.models import HeatEntity, ThemeHeatScore

    universe_symbols, _snap, _diff = get_or_create_universe_snapshot(
        batch_date=as_of, log_fn=logger.info
    )
    if universe_as_of is None:
        universe_as_of = universe_last_updated_date()
    stale = is_universe_stale(universe_as_of, as_of)

    if build_components is None:
        from apps.chain_sight.services.estimate_revision import compute_c8_from_db

        c8_by_symbol, c8_mix = compute_c8_from_db(universe_symbols, as_of)
        # TH-4 z_mode mix 로그를 beat 실행 로그로 승격 (§7)
        logger.info(
            "z_mode mix: ts=%d cs=%d none=%d (heat beat as_of=%s)",
            c8_mix["ts"], c8_mix["cs"], c8_mix["none"], as_of,
        )

        def build_components(entity, sector_symbols):
            return _real_sector_components(sector_symbols, as_of, c8_by_symbol)

    results = []
    for entity in HeatEntity.objects.filter(kind="sector").order_by("ref_id"):
        # 섹터별 try/except 실패 격리 (§7) — 한 섹터 실패가 나머지 중단·부분오염 금지
        try:
            gics = HEAT_ENTITY_TO_SP500_SECTOR.get(entity.ref_id, entity.ref_id)
            sector_symbols = sector_constituents(gics, universe_symbols)
            components = build_components(entity, sector_symbols)
            synth = synthesize_heat(components)

            if synth["score"] is None:  # not_computed → 미저장 (§6.1 status 미포함)
                logger.info("heat: %s not_computed (missing=%d) — 미저장",
                            entity.ref_id, synth.get("missing_count", 0))
                results.append({"entity": entity.ref_id, "status": "not_computed", "stored": False})
                continue

            stored_components = dict(synth["components"])
            stored_components["universe_stale"] = stale
            stored_components["universe_as_of"] = (
                universe_as_of.isoformat() if universe_as_of else None
            )
            _obj, created = ThemeHeatScore.objects.update_or_create(
                theme=entity, date=as_of,
                defaults={
                    "score": synth["score"], "status": synth["status"],
                    "components": stored_components, "evidence": synth["evidence"],
                },
            )
            results.append({
                "entity": entity.ref_id, "status": synth["status"],
                "stored": True, "created": created, "universe_stale": stale,
            })
        except Exception as e:  # noqa: BLE001 — 섹터 격리, 부분 저장 없이 해당 섹터만 스킵
            logger.error("heat: %s 계산 실패(격리): %s", entity.ref_id, e)
            results.append({"entity": entity.ref_id, "status": "error", "stored": False})

    stored = sum(1 for r in results if r["stored"])
    logger.info("heat beat 완료 (%s): 섹터 %d, 저장 %d, universe_stale=%s",
                as_of, len(results), stored, stale)
    return results
