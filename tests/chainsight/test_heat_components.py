"""
Heat 8성분 계산기 테스트 (TH-3, 설계서 §2 · §3 · §5).

각 실계산 성분(C1, C2a, C3, C4, C5, C6, C7)마다 최소 3건 (지시서 요구):
  1. 정상 계산 — 유효 series+current → z·s 산출, 계약 준수.
  2. 결측 → missing_reason — 입력 결측/히스토리 부족 → z=None + 사유.
  3. 부호 방향 — 과열 케이스(current ≫ history mean)에서 z > 0 (정방향 전수 검증).

스텁(C2b, C8)은 계약 만족 결측 반환 검증. z 코어(timeseries/cross-sectional)도 검증.
"""

import math

import pytest

from apps.chain_sight.services import heat_components as hc


# 평온한 3년 히스토리 (평균≈0.5, 표본 충분) — 정상/부호 테스트 공용
CALM = [0.48, 0.50, 0.52, 0.49, 0.51, 0.50, 0.47, 0.53, 0.50, 0.49,
        0.51, 0.50, 0.48, 0.52, 0.50, 0.49, 0.51, 0.50, 0.48, 0.52,
        0.50, 0.49, 0.51, 0.50]  # n=24 ≥ DEFAULT_MIN_N(20)


def _assert_contract(comp):
    """출력 계약 키 4종 존재 확인."""
    assert set(comp.keys()) == {"z", "s", "raw", "missing_reason"}


class TestContractAndZCore:
    def test_make_component_valid(self):
        comp = hc.make_component(1.0, raw=0.7)
        _assert_contract(comp)
        assert comp["z"] == 1.0
        assert comp["s"] == pytest.approx(hc.sigmoid(1.0))
        assert comp["raw"] == 0.7
        assert comp["missing_reason"] is None

    def test_make_component_missing_forces_none(self):
        comp = hc.make_component(None, raw=0.7, missing_reason="foo")
        assert comp["z"] is None and comp["s"] is None
        assert comp["missing_reason"] == "foo"

    def test_timeseries_z_positive_direction(self):
        # current 가 mean 보다 크면 z>0 (정방향)
        z = hc.timeseries_z(0.9, CALM)
        assert z is not None and z > 0

    def test_timeseries_z_insufficient_history_none(self):
        assert hc.timeseries_z(0.9, [0.5, 0.5, 0.5]) is None  # n<min_n

    def test_timeseries_z_zero_std_none(self):
        assert hc.timeseries_z(0.9, [0.5] * 30) is None  # std==0

    def test_cross_sectional_z(self):
        z = hc.cross_sectional_z(3.0, [1.0, 2.0, 3.0])
        assert z is not None and z > 0


# ── 실계산 성분 파라미터화: (함수, missing_reason 접두) ──
REAL_COMPONENTS = [
    ("c1_valuation", hc.c1_valuation, "c1_"),
    ("c2a_insider", hc.c2a_insider, "c2a_"),
    ("c3_narrative", hc.c3_narrative, "c3_"),
    ("c4_etf_flow", hc.c4_etf_flow, "c4_"),
    ("c5_speculation", hc.c5_speculation, "c5_"),
    ("c6_correlation", hc.c6_correlation, "c6_"),
    ("c7_dollar_volume", hc.c7_dollar_volume, "c7_"),
]


@pytest.mark.parametrize("name,fn,prefix", REAL_COMPONENTS)
class TestRealComponents:
    def test_normal_computation(self, name, fn, prefix):
        """정상 계산: 유효 series+current → 계약 준수, s=sigmoid(z), raw 보존."""
        comp = fn(0.55, CALM)
        _assert_contract(comp)
        assert comp["missing_reason"] is None
        assert comp["z"] is not None
        assert comp["s"] == pytest.approx(hc.sigmoid(comp["z"]))
        assert comp["raw"] == 0.55

    def test_missing_reason_on_none_current(self, name, fn, prefix):
        """결측: current=None → z=None + 성분별 missing_reason."""
        comp = fn(None, CALM)
        assert comp["z"] is None and comp["s"] is None
        assert comp["missing_reason"].startswith(prefix)

    def test_missing_reason_on_insufficient_history(self, name, fn, prefix):
        """결측: 히스토리 부족 → z=None (재분배 대상)."""
        comp = fn(0.55, [0.5, 0.5, 0.5])
        assert comp["z"] is None
        assert comp["missing_reason"] is not None

    def test_sign_direction_overheated_positive_z(self, name, fn, prefix):
        """부호 방향(전수): 과열 케이스(current ≫ mean) → z>0. 8성분 전부 정방향."""
        comp = fn(0.95, CALM)  # 0.95 ≫ mean(≈0.50)
        assert comp["z"] is not None
        assert comp["z"] > 0, f"{name}: 과열인데 z<=0 (부호 역전 의심)"


class TestC2bIssuance:
    """C2b 발행 신호 (§5.2) — 424B5 + IPO 레그 z 평균. 실계산."""

    # 3년 평온한 건수 히스토리 (평균≈4건/window)
    CALM_COUNTS = [4, 5, 3, 4, 6, 4, 5, 3, 4, 5, 4, 3, 5, 4, 6, 4, 3, 5, 4, 4,
                   5, 3, 4, 6]

    def test_normal_single_leg_424b5(self):
        """정상: 424B5 단독(IPO 미제공) → 424B5 z 그대로."""
        comp = hc.c2b_issuance(5, self.CALM_COUNTS)
        _assert_contract(comp)
        assert comp["missing_reason"] is None
        assert comp["z"] is not None
        assert comp["s"] == pytest.approx(hc.sigmoid(comp["z"]))
        assert comp["raw"]["count_424b5"] == 5
        assert comp["raw"]["legs"]["z_ipo"] is None

    def test_normal_two_legs_average(self):
        """정상: 두 레그 유효 → 산술평균."""
        comp = hc.c2b_issuance(
            5, self.CALM_COUNTS, current_ipo_count=5, history_ipo_counts=self.CALM_COUNTS
        )
        assert comp["z"] is not None
        z424 = comp["raw"]["legs"]["z_424b5"]
        zipo = comp["raw"]["legs"]["z_ipo"]
        assert comp["z"] == pytest.approx((z424 + zipo) / 2)

    def test_missing_when_no_legs(self):
        """결측: 두 레그 모두 None → missing_reason."""
        comp = hc.c2b_issuance(None, [], current_ipo_count=None)
        assert comp["z"] is None and comp["s"] is None
        assert comp["missing_reason"] == "c2b_no_issuance"

    def test_missing_reason_passthrough(self):
        """상위(from_db)가 명시한 missing_reason 전달 (빈 유니버스 등)."""
        comp = hc.c2b_issuance(None, [], missing_reason="c2b_empty_universe")
        assert comp["missing_reason"] == "c2b_empty_universe"

    def test_sign_direction_overheated_positive_z(self):
        """부호: 발행 건수 급증(current ≫ mean) → z>0 (공급 증가 = 과열, 정방향)."""
        comp = hc.c2b_issuance(20, self.CALM_COUNTS)  # 20 ≫ mean(≈4)
        assert comp["z"] is not None and comp["z"] > 0


class TestC8Combiner:
    """C8 = z_price − z_eps (§2). 계약 = 기본 4키 + C8 전용 z_mode."""

    def test_valid_has_zmode_and_diff(self):
        comp = hc.c8_estimate_revision(z_price=1.0, z_eps=0.2, z_mode="cross_sectional")
        assert set(comp.keys()) == {"z", "s", "raw", "missing_reason", "z_mode"}
        assert comp["z"] == pytest.approx(0.8)
        assert comp["z_mode"] == "cross_sectional"
        assert comp["missing_reason"] is None

    def test_missing_leg_nulls_zmode(self):
        comp = hc.c8_estimate_revision(z_price=None, z_eps=0.2)
        assert comp["z"] is None and comp["z_mode"] is None
        assert comp["missing_reason"] == "c8_z_unavailable"


@pytest.mark.django_db
class TestC2aFromDB:
    """완결 백필 데이터 위 C2a DB 백엔드 — 즉시 가동(§5.1) 스모크."""

    def test_empty_universe_missing(self):
        from datetime import date

        comp = hc.c2a_insider_from_db([], date(2026, 7, 7))
        assert comp["missing_reason"] == "c2a_empty_universe"

    def test_no_records_missing(self):
        from datetime import date

        comp = hc.c2a_insider_from_db(["NOSUCH"], date(2026, 7, 7))
        assert comp["missing_reason"] == "c2a_no_insider"

    def test_computes_z_from_backfilled_records(self):
        """현재 window 순매도가 히스토리보다 뚜렷이 높으면 z>0 (과열, 정방향)."""
        from datetime import date, timedelta
        from decimal import Decimal

        from apps.chain_sight.models import InsiderTransactionRecord

        as_of = date(2026, 7, 7)

        def _rec(dkey, txn_date, ttype, qty, price):
            InsiderTransactionRecord.objects.create(
                symbol="AAA",
                filing_date=txn_date,
                transaction_date=txn_date,
                transaction_type=ttype,
                securities_transacted=Decimal(qty),
                price=Decimal(price),
                type_of_owner="officer",
                dedup_key=dkey,
            )

        # 히스토리 구간(오래 전): 매수 우위 (낮은 net_sell_ratio)
        base = as_of - timedelta(days=800)
        for i in range(60):
            d = base + timedelta(days=i * 7)
            _rec(f"buy{i}", d, "P-Purchase", "1000", "10")
            _rec(f"sell{i}", d, "S-Sale", "100", "10")  # 매도 소량
        # 현재 window(최근 90일): 매도 폭증 (높은 net_sell_ratio → 과열)
        for i in range(8):
            d = as_of - timedelta(days=i * 10 + 1)
            _rec(f"cursell{i}", d, "S-Sale", "5000", "10")

        comp = hc.c2a_insider_from_db(["AAA"], as_of, step_days=7, min_n=20)
        assert comp["missing_reason"] is None, comp
        assert comp["z"] is not None
        assert comp["z"] > 0  # 현재 순매도 급증 = 과열 = 정방향 z>0
        assert 0.0 <= comp["raw"] <= 1.0  # net_sell_ratio 범위
