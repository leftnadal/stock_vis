"""MPS-1 Part 1 — 신규 수집 2종 배선 가드(수집만·스코어 미편입·SOFR 보류·seed 정합).

계약(D-MPS-INDICATORS): DTWEXBGS·STLFSI4는 FRED 재귀 수집에 편입되나 스코어 성분(load_inputs
  대상)에는 진입하지 않는다. SOFR는 배선 보류(MPS-SOFR 별건).
"""

from __future__ import annotations

import importlib

import pytest

from apps.market_pulse.regime.inputs import INDICATOR_CODE_MAP
from apps.market_pulse.regime.stress import STRESS_SCORE_KEYS
from apps.market_pulse.tasks.sync_indicators import FRED_RECURRING_SERIES

pytestmark = [pytest.mark.unit]

NEW_COLLECTED = ("DTWEXBGS", "STLFSI4")
DEFERRED = "SOFR"


class TestStressCollectionWiring:
    def test_new_series_added_to_recurring(self):
        for code in NEW_COLLECTED:
            assert code in FRED_RECURRING_SERIES

    def test_sofr_deferred_not_wired(self):
        # SOFR 파생 인프라 부재 → market_pulse 재귀에 미편입(MPS-SOFR 별건).
        assert not any("SOFR" in s for s in FRED_RECURRING_SERIES)

    def test_new_series_not_in_scoring_path(self):
        # 수집만·미편입: load_inputs(INDICATOR_CODE_MAP) 및 스코어 성분에 없어야.
        loaded = set(INDICATOR_CODE_MAP.values())
        for code in NEW_COLLECTED + (DEFERRED,):
            assert code not in loaded
            assert code not in STRESS_SCORE_KEYS

    def test_seed_migration_matches_collected(self):
        mod = importlib.import_module(
            "macro.migrations.0007_seed_mp_stress_indicators"
        )
        seeded = {row[0] for row in mod.SERIES}
        assert seeded == set(NEW_COLLECTED)
        # data_source 라벨 정확(오기재 전례 회피) — 둘 다 진짜 FRED.
        assert all(row[3] == "fred" for row in mod.SERIES)
