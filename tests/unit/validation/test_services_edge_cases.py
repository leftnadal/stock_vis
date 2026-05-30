"""
validation 서비스 추가 edge case 단위 테스트

기존 보강 테스트(test_services_complementary / extended / uncovered /
validation_additional)가 다루지 않은 분기와 상호작용을 보강한다.

대상:
  - PresetGenerator (preset_generator.py)
  - BenchmarkCalculator (benchmark_calculator.py)
  - MetricCalculator (metric_calculator.py)
  - RelativeMetricCalculator (relative_metrics.py)
  - interpretation 모듈 (interpretation.py)
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from packages.shared.metrics.models import (
    CompanyMetricSnapshot,
    IndustryMetricBenchmark,
    MetricDefinition,
    PeerListCache,
    PeerMetricBenchmark,
)
from packages.shared.stocks.models import (
    IndustryClassification,
    SP500Constituent,
    Stock,
)
from validation.models import (
    CompanyBenchmarkDelta,
    CompanyMetricLatest,
    PeerPreset,
)
from validation.services.benchmark_calculator import (
    BenchmarkCalculator,
    assign_size_bucket,
    get_adjacent_buckets,
)
from validation.services.interpretation import (
    determine_trend,
    generate_leader_summary,
    generate_metric_interpretation,
    generate_summary_text,
)
from validation.services.metric_calculator import (
    MetricCalculator,
    _div,
    _safe,
    _safe_nonzero,
)
from validation.services.preset_generator import PresetGenerator
from validation.services.relative_metrics import RelativeMetricCalculator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stock(symbol="AAPL", sector="Technology",
                industry="Consumer Electronics", market_cap=3_000_000_000_000):
    return Stock.objects.get_or_create(
        symbol=symbol,
        defaults={
            "stock_name": f"{symbol} Inc",
            "exchange": "NASDAQ",
            "sector": sector,
            "industry": industry,
            "market_capitalization": (
                Decimal(str(market_cap)) if market_cap is not None else None
            ),
        },
    )[0]


def _make_sp500(symbol, sector="Technology", is_active=True):
    return SP500Constituent.objects.get_or_create(
        symbol=symbol,
        defaults={
            "company_name": f"{symbol} Corp",
            "sector": sector,
            "is_active": is_active,
        },
    )[0]


def _ensure_metric_def(code, category="profitability", higher_is_better=True,
                      is_benchmarkable=True):
    return MetricDefinition.objects.get_or_create(
        metric_code=code,
        defaults={
            "display_name": code,
            "display_name_en": code,
            "category": category,
            "unit": "ratio",
            "higher_is_better": higher_is_better,
            "is_benchmarkable": is_benchmarkable,
        },
    )[0]


def _make_snapshot(stock, code, fy, value, status="normal"):
    md = _ensure_metric_def(code)
    return CompanyMetricSnapshot.objects.update_or_create(
        symbol=stock,
        fiscal_year=fy,
        metric_code=md,
        defaults={
            "metric_value": Decimal(str(value)),
            "value_status": status,
        },
    )[0]


def _signal(category, signal, score=50.0):
    return SimpleNamespace(category=category, signal=signal, score=score)


# ===========================================================================
# PresetGenerator — 추가 분기 8개
# ===========================================================================


@pytest.mark.django_db
class TestPresetGeneratorBranches:
    def test_default_preset_marks_is_default_true(self):
        target = _make_stock("AAPL")
        _make_sp500("AAPL")
        # 8개 이상의 industry+size 동종 종목
        for i in range(10):
            sym = f"AAP{i}"
            _make_stock(sym, sector="Technology",
                        industry="Consumer Electronics",
                        market_cap=2_500_000_000_000)
            _make_sp500(sym)

        PresetGenerator().generate_for_symbol("AAPL")

        preset = PeerPreset.objects.get(symbol=target, preset_key="default")
        assert preset.is_default is True
        assert preset.is_active is True
        assert preset.peer_count >= 8

    def test_sector_all_peer_symbols_capped_at_100(self):
        target = _make_stock("AAPL")
        _make_sp500("AAPL")
        for i in range(110):
            sym = f"X{i:03d}"
            _make_stock(sym, sector="Technology",
                        industry=f"Misc{i % 5}",
                        market_cap=5_000_000_000)
            _make_sp500(sym)

        PresetGenerator().generate_for_symbol("AAPL")

        preset = PeerPreset.objects.filter(
            symbol=target, preset_key="sector_all"
        ).first()
        assert preset is not None
        assert len(preset.peer_symbols) <= 100

    def test_size_peers_skipped_for_mid_cap(self):
        target = _make_stock("MID1", market_cap=5_000_000_000)  # mid
        _make_sp500("MID1")
        for i in range(10):
            sym = f"MIDP{i}"
            _make_stock(sym, sector="Technology",
                        industry="Software", market_cap=5_000_000_000)
            _make_sp500(sym)

        PresetGenerator().generate_for_symbol("MID1")
        # mid 시가총액은 size_peers 분기에서 제외
        assert not PeerPreset.objects.filter(
            symbol=target, preset_key="size_peers"
        ).exists()

    def test_size_peers_created_for_mega_cap(self):
        target = _make_stock("MEGA1", market_cap=500_000_000_000)
        _make_sp500("MEGA1")
        for i in range(8):
            sym = f"MGP{i}"
            _make_stock(sym, sector="Technology",
                        industry="Software",
                        market_cap=300_000_000_000)
            _make_sp500(sym)

        PresetGenerator().generate_for_symbol("MEGA1")

        preset = PeerPreset.objects.filter(
            symbol=target, preset_key="size_peers"
        ).first()
        assert preset is not None
        assert "Mega Cap" in preset.logic_summary

    def test_filter_by_size_returns_intersection_of_buckets(self):
        gen = PresetGenerator()
        _make_stock("A1", market_cap=300_000_000_000)  # mega
        _make_stock("A2", market_cap=50_000_000_000)   # large
        _make_stock("A3", market_cap=5_000_000_000)    # mid
        _make_stock("A4", market_cap=1_000_000_000)    # small

        qs = Stock.objects.all()
        large_only = gen._filter_by_size(qs, ["large"])
        mega_large = gen._filter_by_size(qs, ["mega", "large"])

        assert set(large_only.values_list("symbol", flat=True)) == {"A2"}
        assert set(mega_large.values_list("symbol", flat=True)) == {"A1", "A2"}

    def test_confidence_mid_count_penalty(self):
        # peer_count 9이면 -0.1, 5이면 -0.3
        gen = PresetGenerator()
        stock = _make_stock("CONF1", industry="Software")
        c_high = gen._calc_confidence(15, stock)
        c_mid = gen._calc_confidence(9, stock)
        c_low = gen._calc_confidence(4, stock)
        assert c_high == pytest.approx(1.0)
        assert c_mid == pytest.approx(0.9)
        assert c_low == pytest.approx(0.7)

    def test_confidence_special_industry_penalty(self):
        stock = _make_stock("BANK", industry="Banks - Diversified")
        IndustryClassification.objects.get_or_create(
            industry="Banks - Diversified",
            defaults={"handling_mode": "special"},
        )
        c = PresetGenerator()._calc_confidence(20, stock)
        # 1.0 - 0.15 = 0.85
        assert c == pytest.approx(0.85)

    def test_generate_for_symbol_returns_error_on_missing_stock(self):
        out = PresetGenerator().generate_for_symbol("DOES_NOT_EXIST")
        assert out["error"] == "Stock not found"
        assert out["symbol"] == "DOES_NOT_EXIST"

    def test_batch_swallows_exceptions_and_counts_success(self):
        _make_stock("OK1")
        _make_sp500("OK1")
        with patch.object(
            PresetGenerator, "generate_for_symbol",
            side_effect=[{"presets_created": 1}, RuntimeError("boom")],
        ):
            out = PresetGenerator().generate_for_symbols(["OK1", "BAD1"])
        assert out["total"] == 2
        assert out["success"] == 1


# ===========================================================================
# BenchmarkCalculator — 추가 통합 분기 9개
# ===========================================================================


@pytest.mark.django_db
class TestBenchmarkCalculatorBranches:
    def test_select_peers_falls_back_to_sector_when_industry_below_5(self):
        target = _make_stock("TGT", sector="Energy", industry="Oil & Gas")
        _make_sp500("TGT", sector="Energy")
        # industry 동종이 너무 적음 (2개) → sector fallback
        for i, s in enumerate(["OIL1", "OIL2"]):
            _make_stock(s, sector="Energy", industry="Oil & Gas",
                        market_cap=5_000_000_000)
            _make_sp500(s, sector="Energy")
        # 같은 sector 다른 industry 추가
        for i, s in enumerate(["NRG1", "NRG2", "NRG3"]):
            _make_stock(s, sector="Energy", industry="Refining",
                        market_cap=5_000_000_000)
            _make_sp500(s, sector="Energy")

        peers, basis = BenchmarkCalculator()._select_peers(target)
        assert basis == "sector"
        assert peers.count() >= 4

    def test_select_peers_returns_industry_when_5_to_7(self):
        target = _make_stock("TGT2", sector="Tech", industry="Software",
                             market_cap=3_000_000_000_000)
        _make_sp500("TGT2", sector="Tech")
        # 5~7개 → 'industry' basis
        for i in range(5):
            s = f"SW{i}"
            _make_stock(s, sector="Tech", industry="Software",
                        market_cap=1_000_000_000)  # small bucket
            _make_sp500(s, sector="Tech")

        peers, basis = BenchmarkCalculator()._select_peers(target)
        assert basis == "industry"
        assert peers.count() == 5

    def test_industry_benchmark_skipped_for_low_sample(self):
        # industry에 종목이 2개 미만이면 skip
        out = BenchmarkCalculator()._calculate_industry_benchmarks(
            "VeryRareIndustry", [2024]
        )
        assert out == 0

    def test_calculate_industry_benchmarks_creates_rows(self):
        _ensure_metric_def("roe", category="profitability")
        # 같은 industry 종목 3개에 동일 fiscal year snapshot
        stocks_ = []
        for i, s in enumerate(["IND1", "IND2", "IND3"]):
            stk = _make_stock(s, sector="Tech", industry="Widgets",
                              market_cap=5_000_000_000)
            _make_sp500(s, sector="Tech")
            stocks_.append(stk)
            _make_snapshot(stk, "roe", 2024, value=0.10 + i * 0.05)

        cnt = BenchmarkCalculator()._calculate_industry_benchmarks(
            "Widgets", [2024]
        )
        assert cnt >= 1
        bench = IndustryMetricBenchmark.objects.filter(
            industry="Widgets", fiscal_year=2024, metric_code_id="roe"
        ).first()
        assert bench is not None
        assert bench.sample_count == 3
        # median = 0.15
        assert float(bench.median_value) == pytest.approx(0.15, abs=1e-3)

    def test_get_available_years_returns_distinct_descending_max_5(self):
        stock = _make_stock("YR1")
        for fy in [2019, 2020, 2021, 2022, 2023, 2024]:
            _make_snapshot(stock, "roe", fy, 0.1)
        years = BenchmarkCalculator()._get_available_years("YR1")
        assert years == [2024, 2023, 2022, 2021, 2020]

    def test_peer_list_cache_use_industry_fallback_true_when_sector_basis(self):
        target = _make_stock("CACHE1", sector="Tech", industry=None)
        _make_sp500("CACHE1", sector="Tech")
        # sector 종목 4개
        for s in ["C1", "C2", "C3", "C4"]:
            _make_stock(s, sector="Tech", industry="Widget",
                        market_cap=5_000_000_000)
            _make_sp500(s, sector="Tech")

        BenchmarkCalculator().calculate_for_symbol("CACHE1")

        cache = PeerListCache.objects.get(symbol=target)
        assert cache.benchmark_basis == "sector"
        assert cache.use_industry_fallback is True
        assert cache.fallback_reason.startswith("peer")

    def test_calculate_for_symbol_runs_full_pipeline(self):
        # industry+size로 8개 peer → industry_size, snapshot 동기화
        _ensure_metric_def("roe")
        target = _make_stock("PIPE", sector="Tech", industry="Software",
                             market_cap=300_000_000_000)
        _make_sp500("PIPE", sector="Tech")
        _make_snapshot(target, "roe", 2024, 0.30)

        for i in range(9):
            sym = f"SP{i}"
            stk = _make_stock(sym, sector="Tech", industry="Software",
                              market_cap=200_000_000_000)
            _make_sp500(sym, sector="Tech")
            _make_snapshot(stk, "roe", 2024, 0.10 + i * 0.02)

        result = BenchmarkCalculator().calculate_for_symbol("PIPE")
        assert result["peer_count"] == 9
        assert result["benchmark_basis"] == "industry_size"
        # PeerMetricBenchmark 생성
        bench = PeerMetricBenchmark.objects.filter(
            symbol=target, fiscal_year=2024, metric_code_id="roe"
        ).first()
        assert bench is not None
        # CompanyBenchmarkDelta 생성
        delta = CompanyBenchmarkDelta.objects.filter(
            symbol=target, fiscal_year=2024, metric_code_id="roe"
        ).first()
        assert delta is not None
        assert delta.benchmark_type == "peer"
        # 30%는 peer 분포(10~26%) 대비 최상위
        assert float(delta.percentile_rank) >= 75

    def test_calculate_for_symbols_default_runs_active_sp500(self):
        with patch.object(
            BenchmarkCalculator, "calculate_for_symbol",
            return_value={"peer_count": 8, "benchmark_basis": "industry_size"},
        ) as m:
            _make_sp500("BSP1", is_active=True)
            _make_sp500("BSP2", is_active=False)
            out = BenchmarkCalculator().calculate_for_symbols()
        # 활성 종목만
        assert m.call_count == 1
        assert out["total"] == 1

    def test_industry_benchmark_confidence_buckets(self):
        _ensure_metric_def("gross_margin", category="profitability")
        # 3개 → low, 7개 → medium, 12개 → high
        scenarios = [(3, "low"), (7, "medium"), (12, "high")]
        for n, expected in scenarios:
            ind = f"Conf{n}"
            for i in range(n):
                sym = f"{ind}_{i}"
                stk = _make_stock(sym, sector="Tech", industry=ind,
                                  market_cap=5_000_000_000)
                _make_sp500(sym, sector="Tech")
                _make_snapshot(stk, "gross_margin", 2024, 0.3 + i * 0.01)
            BenchmarkCalculator()._calculate_industry_benchmarks(ind, [2024])
            b = IndustryMetricBenchmark.objects.get(
                industry=ind, fiscal_year=2024, metric_code_id="gross_margin"
            )
            assert b.benchmark_confidence == expected


# ===========================================================================
# MetricCalculator — 추가 계산 분기 12개
# ===========================================================================


def _stock_obj(symbol="AAPL", mcap=3_000_000_000_000, pe=25):
    """Stock 모방 객체 (DB 저장 안 함)"""
    return SimpleNamespace(
        symbol=symbol,
        market_capitalization=Decimal(str(mcap)) if mcap else None,
        pe_ratio=Decimal(str(pe)) if pe else None,
    )


def _inc(**kw):
    defaults = dict(
        total_revenue=1000.0,
        gross_profit=500.0,
        operating_income=200.0,
        net_income=150.0,
        income_tax_expense=40.0,
        income_before_tax=190.0,
        cost_of_revenue=500.0,
        selling_general_and_administrative=100.0,
        ebitda=250.0,
        interest_expense=10.0,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _bal(**kw):
    defaults = dict(
        total_assets=2000.0,
        total_current_assets=600.0,
        total_current_liabilities=400.0,
        total_shareholder_equity=800.0,
        short_term_debt=100.0,
        long_term_debt=300.0,
        cash_and_cash_equivalents_at_carrying_value=200.0,
        current_net_receivables=120.0,
        inventory=80.0,
        common_stock_shares_outstanding=1_000_000.0,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _cf(**kw):
    defaults = dict(
        operating_cashflow=180.0,
        capital_expenditures=60.0,
        dividend_payout=10.0,
        payments_for_repurchase_of_common_stock=20.0,
        proceeds_from_issuance_of_common_stock=5.0,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


class TestMetricCalculatorEdge:
    def test_safe_returns_float_for_negative(self):
        assert _safe(Decimal("-12.5")) == -12.5

    def test_safe_nonzero_returns_negative_floats(self):
        assert _safe_nonzero(-5.0) == -5.0

    def test_div_returns_none_when_denominator_zero(self):
        assert _div(100, 0) is None

    def test_calc_roic_uses_default_tax_when_zero_income_before_tax(self):
        calc = MetricCalculator()
        inc = _inc(income_before_tax=0)  # 분모 0 → default tax_rate 0.21
        bal = _bal()
        val, status, _ = calc._calc_roic(inc, bal)
        # NOPAT = 200 * 0.79 = 158, IC = 800 + 300 = 1100
        assert status == "normal"
        assert val == pytest.approx(158 / 1100, rel=1e-3)

    def test_calc_interest_coverage_not_applicable_when_no_debt(self):
        calc = MetricCalculator()
        bal = _bal(short_term_debt=0, long_term_debt=0)
        val, status, reason = calc._calc_interest_coverage(_inc(), bal, None)
        assert status == "not_applicable"
        assert val is None
        assert "무차입" in reason

    def test_calc_interest_coverage_missing_when_no_interest(self):
        calc = MetricCalculator()
        inc = _inc(interest_expense=None)
        val, status, _ = calc._calc_interest_coverage(inc, _bal(), None)
        assert status == "missing"

    def test_calc_cash_runway_returns_not_applicable_when_profitable(self):
        calc = MetricCalculator()
        cf = _cf(operating_cashflow=100.0)  # 흑자
        val, status, _ = calc._calc_cash_runway(_bal(), cf)
        assert status == "not_applicable"

    def test_calc_cash_runway_uses_abs_ocf_when_negative(self):
        calc = MetricCalculator()
        cf = _cf(operating_cashflow=-50.0)
        bal = _bal(cash_and_cash_equivalents_at_carrying_value=200.0)
        val, status, _ = calc._calc_cash_runway(bal, cf)
        assert status == "normal"
        assert val == pytest.approx(4.0)

    def test_calc_inventory_days_service_company_not_applicable(self):
        calc = MetricCalculator()
        bal = _bal(inventory=0)
        val, status, reason = calc._calc_inventory_days(bal, _inc())
        assert status == "not_applicable"
        assert "서비스" in reason

    def test_calc_dso_normal(self):
        calc = MetricCalculator()
        # AR/Revenue * 365 = 120/1000 * 365 = 43.8
        val, status, _ = calc._calc_dso(_bal(), _inc())
        assert status == "normal"
        assert val == pytest.approx(43.8, abs=0.1)

    def test_calc_dilution_3y_missing_when_no_3y_history(self):
        calc = MetricCalculator()
        val, status, reason = calc._calc_dilution_3y(_bal(), None)
        assert status == "missing"
        assert "3년 전" in reason

    def test_calc_shareholder_yield_uses_buyback_minus_issuance(self):
        calc = MetricCalculator()
        stock = _stock_obj(mcap=1000)
        cf = _cf(dividend_payout=10, payments_for_repurchase_of_common_stock=30,
                 proceeds_from_issuance_of_common_stock=5)
        # (10 + 30 - 5) / 1000 = 0.035
        val, status, _ = calc._calc_shareholder_yield(cf, stock)
        assert status == "normal"
        assert val == pytest.approx(0.035, rel=1e-3)

    def test_calc_pe_passes_stock_field(self):
        calc = MetricCalculator()
        val, status, _ = calc._calc_pe(_stock_obj(pe=22.5))
        assert status == "normal"
        assert val == 22.5

    def test_calc_ev_ebitda_missing_when_ebitda_zero(self):
        calc = MetricCalculator()
        val, status, _ = calc._calc_ev_ebitda(_stock_obj(), _inc(ebitda=0))
        assert status == "missing"

@pytest.mark.django_db
class TestMetricCalculatorUpdateLatest:
    def test_calc_for_symbol_returns_error_when_stock_missing(self):
        out = MetricCalculator().calculate_for_symbol("NOPE_404")
        assert out["error"] == "Stock not found"
        assert out["metrics_saved"] == 0

    def test_update_latest_writes_one_row_per_snapshot(self):
        stock = _make_stock("ULA1")
        _make_snapshot(stock, "roe", 2024, 0.20)
        _make_snapshot(stock, "operating_margin", 2024, 0.18)

        n = MetricCalculator()._update_latest(stock, 2024)
        assert n == 2
        rows = CompanyMetricLatest.objects.filter(symbol=stock)
        assert rows.count() == 2
        for r in rows:
            assert r.latest_fiscal_year == 2024
            assert r.latest_value is not None

    def test_update_latest_with_no_snapshots_returns_zero(self):
        stock = _make_stock("EMPTY1")
        n = MetricCalculator()._update_latest(stock, 2024)
        assert n == 0


# ===========================================================================
# RelativeMetricCalculator — 추가 시나리오 5개
# ===========================================================================


@pytest.mark.django_db
class TestRelativeMetricEdge:
    def test_creates_snapshot_with_source_detail(self):
        _ensure_metric_def("revenue_growth_yoy", category="growth")
        _ensure_metric_def("rev_growth_vs_industry", category="growth")
        stock = _make_stock("REL1", industry="Software")
        _make_snapshot(stock, "revenue_growth_yoy", 2024, 0.30)
        IndustryMetricBenchmark.objects.create(
            industry="Software", fiscal_year=2024,
            metric_code=MetricDefinition.objects.get(
                metric_code="revenue_growth_yoy"
            ),
            median_value=Decimal("0.10"),
            sample_count=5,
        )

        ok = RelativeMetricCalculator()._calc_rev_growth_vs_industry("REL1")
        assert ok is True

        rel = CompanyMetricSnapshot.objects.get(
            symbol=stock, fiscal_year=2024,
            metric_code_id="rev_growth_vs_industry",
        )
        assert float(rel.metric_value) == pytest.approx(0.20)
        assert rel.source_detail["company_growth"] == pytest.approx(0.30)
        assert rel.source_detail["industry_median"] == pytest.approx(0.10)
        assert "calculated_at" in rel.source_detail

    def test_returns_false_when_stock_has_no_industry(self):
        _make_stock("NOINDU", industry=None)
        ok = RelativeMetricCalculator()._calc_rev_growth_vs_industry("NOINDU")
        assert ok is False

    def test_returns_false_when_no_revenue_snapshot(self):
        _make_stock("NOSNAP", industry="Software")
        ok = RelativeMetricCalculator()._calc_rev_growth_vs_industry("NOSNAP")
        assert ok is False

    def test_skip_year_when_industry_benchmark_missing(self):
        _ensure_metric_def("revenue_growth_yoy", category="growth")
        stock = _make_stock("SKIPY", industry="Software")
        _make_snapshot(stock, "revenue_growth_yoy", 2024, 0.30)
        # IndustryMetricBenchmark 없음
        ok = RelativeMetricCalculator()._calc_rev_growth_vs_industry("SKIPY")
        assert ok is False

    def test_batch_default_uses_sp500_active_only(self):
        _make_sp500("BSP_A", is_active=True)
        _make_sp500("BSP_B", is_active=False)
        with patch.object(
            RelativeMetricCalculator,
            "_calc_rev_growth_vs_industry",
            return_value=True,
        ) as m:
            out = RelativeMetricCalculator().calculate_for_symbols()
        assert m.call_count == 1
        assert out["total"] == 1
        assert out["success"] == 1


# ===========================================================================
# interpretation 모듈 — 추가 분기 8개
# ===========================================================================


class TestInterpretationEdge:
    def test_summary_picks_top2_greens_by_score(self):
        signals = [
            _signal("profitability", "green", 95.0),
            _signal("growth", "green", 60.0),
            _signal("valuation", "green", 80.0),
        ]
        out = generate_summary_text(signals)
        # 95(수익성) + 80(밸류에이션)이 top2
        assert "수익성" in out and "밸류에이션" in out
        assert "성장성" not in out

    def test_summary_includes_red_warning_when_one_red(self):
        signals = [
            _signal("profitability", "green", 90.0),
            _signal("financial_structure", "red", 5.0),
        ]
        out = generate_summary_text(signals)
        assert "재무구조" in out and "주의 필요" in out

    def test_summary_returns_neutral_when_empty(self):
        assert "중립 구간" in generate_summary_text([])

    def test_metric_interpretation_percentile_75_boundary_top(self):
        out = generate_metric_interpretation(
            "roe", True, percentile_rank=75.0,
            trend="", value_status="normal",
            benchmark_confidence="high",
        )
        # 75 이상 → 상위 25% 표기
        assert "peer 상위 25%" in out

    def test_metric_interpretation_percentile_25_boundary_bottom(self):
        out = generate_metric_interpretation(
            "debt_to_equity", False, percentile_rank=25.0,
            trend="", value_status="normal",
            benchmark_confidence="high",
        )
        assert "peer 하위 25%" in out

    def test_metric_interpretation_no_position_when_percentile_none(self):
        out = generate_metric_interpretation(
            "roe", True, percentile_rank=None,
            trend="improving", value_status="normal",
            benchmark_confidence="high",
        )
        # 위치 표기 없음
        assert "peer 상위" not in out
        assert "peer 하위" not in out
        assert "개선 추세" in out

    def test_determine_trend_at_exact_5pct_lower_is_stable(self):
        # 100 → 95.0 (정확히 -5%): recent[-1]=95, 95 < 95 (False) → stable
        # actual: 95 < 100*0.95=95 (False) and 95 > 100*1.05=105 (False) → stable
        assert determine_trend([100.0, 97.0, 95.0]) == "stable"

    def test_determine_trend_uses_last_3_only(self):
        # 첫 항목은 무시되고 마지막 3개로 판단: [50, 60, 100]
        assert determine_trend([1.0, 1.0, 50.0, 60.0, 100.0]) == "improving"

    def test_leader_summary_truncates_to_3_categories(self):
        advantages = [
            {"category": "profitability"},
            {"category": "growth"},
            {"category": "financial_structure"},
            {"category": "cash_flow_quality"},
        ]
        out = generate_leader_summary(advantages, [])
        # 처음 3개만 노출
        assert "현금흐름" not in out
        assert "수익성" in out and "성장성" in out and "재무구조" in out


# ===========================================================================
# Utility — assign_size_bucket / get_adjacent_buckets 추가
# ===========================================================================


class TestSizeBucketsExtra:
    def test_assign_size_bucket_boundaries(self):
        assert assign_size_bucket(199_999_999_999) == "large"
        assert assign_size_bucket(200_000_000_000) == "mega"
        assert assign_size_bucket(9_999_999_999) == "mid"
        assert assign_size_bucket(10_000_000_000) == "large"
        assert assign_size_bucket(1_999_999_999) == "small"

    def test_get_adjacent_buckets_for_mega_returns_two(self):
        # mega는 가장 위 → [large, mega] 정도
        out = get_adjacent_buckets("mega")
        assert "mega" in out
        assert "large" in out

    def test_get_adjacent_buckets_for_small_does_not_underflow(self):
        out = get_adjacent_buckets("small")
        assert "small" in out
        # 인접 = mid 정도까지만
        assert all(b in ("small", "mid") for b in out)
