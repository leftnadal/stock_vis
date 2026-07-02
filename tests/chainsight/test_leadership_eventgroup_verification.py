"""
L3 검증 하네스 — EventGroup 정책 C leadership (Slice B). 이게 게이트.

L1 불변식: 피어셋 출처·역할 분리·capture 항등식·비소속 무점수·소표본 NULL·정상범위.
L2 구신 diff 특성화: all-core → 옛 theme LOO와 동일(reduction), 다중위성 → 발산(설명됨).
L3 독립 오라클: 대표 표본 + 엣지에서 코어/위성 두 경로 각각 프로덕션과 일치.
"""

import math
from datetime import date, timedelta

import pytest

from apps.chain_sight.models import CompanyChainProfile
from apps.chain_sight.models.event_group import EventGroup, GroupMembership
from apps.chain_sight.models.leadership import StockLeadershipScore
from apps.chain_sight.services.leadership_compute import compute_leadership_scores
from apps.chain_sight.services.leadership_eventgroup import (
    KIND_CORE,
    KIND_SAT,
    compute_eventgroup_leadership_scores,
    eg_theme_key,
)
from packages.shared.stocks.models import DailyPrice, Stock
from tests.chainsight.oracles import leadership_c_oracle as oracle

AS_OF = date(2026, 6, 12)


def _stock(sym):
    return Stock.objects.get_or_create(
        symbol=sym, defaults={"stock_name": f"{sym} Inc.", "sector": "Technology"}
    )[0]


def _make_prices(sym, phase, n_days=30, amp=0.02, drift=0.001, base=100.0):
    """진동+드리프트 종가 → 부호 섞인 수익률(capture up/down 존재). phase로 종목 차별."""
    stock = _stock(sym)
    objs = []
    close = base
    for i in range(n_days):
        r = drift + amp * math.sin(i * 0.7 + phase)
        close *= (1.0 + r)
        d = AS_OF - timedelta(days=(n_days - 1 - i))
        objs.append(DailyPrice(
            stock=stock, date=d,
            open_price=close, high_price=close * 1.01,
            low_price=close * 0.99, close_price=close, volume=1_000_000,
        ))
    DailyPrice.objects.bulk_create(objs, ignore_conflicts=True)


def _mk_eg(slug, members, n_days=30):
    """members=[(sym, role, phase)]."""
    eg = EventGroup.objects.create(
        name=f"grp {slug}", slug=slug, source="news_jaccard",
        confidence=0.5, cohesion=0.5,
        member_count=len(members),
        core_count=sum(1 for m in members if m[1] == "core"),
        is_hidden=False,
    )
    for sym, role, phase in members:
        _make_prices(sym, phase, n_days=n_days)
        GroupMembership.objects.create(group=eg, symbol_id=sym, role=role)
    return eg


def _oracle_returns(symbols, window):
    return {s: oracle.load_window_returns(s, AS_OF, window) for s in symbols}


APPROX = dict(rel=1e-6, abs=1e-7)


# ─────────────────────────────── L3 독립 오라클 (게이트) ───────────────────────────────

@pytest.mark.django_db
class TestL3Oracle:
    def test_core_path_matches_oracle(self):
        """코어 종목 점수 == 오라클 코어-LOO 결과(α/β·capture)."""
        members = [("A", "core", 0.0), ("B", "core", 1.1), ("C", "core", 2.2),
                   ("D", "satellite", 3.3), ("E", "satellite", 4.4)]
        _mk_eg("orc-1", members)
        compute_eventgroup_leadership_scores(AS_OF)

        window = 20
        core_syms = ["A", "B", "C"]
        core_rets = _oracle_returns(core_syms, window)
        for sym in core_syms:
            bench = oracle.core_loo_benchmark(core_rets, sym)
            assert bench is not None
            o_alpha, o_beta = oracle.alpha_beta(core_rets[sym], bench)
            o_up, o_down, o_spread = oracle.capture(core_rets[sym], bench)
            row = StockLeadershipScore.objects.get(
                theme=eg_theme_key("orc-1"), stock_id=sym, window=window)
            assert row.benchmark_kind == KIND_CORE
            assert row.theme_beta == pytest.approx(o_beta, **APPROX)
            assert row.theme_alpha == pytest.approx(o_alpha, **APPROX)
            assert row.up_capture == pytest.approx(o_up, **APPROX)
            assert row.down_capture == pytest.approx(o_down, **APPROX)

    def test_satellite_path_matches_oracle(self):
        """위성 종목 점수 == 오라클 전체-코어-평균 결과."""
        members = [("A", "core", 0.0), ("B", "core", 1.1), ("C", "core", 2.2),
                   ("D", "satellite", 3.3), ("E", "satellite", 4.4)]
        _mk_eg("orc-2", members)
        compute_eventgroup_leadership_scores(AS_OF)

        window = 20
        core_rets = _oracle_returns(["A", "B", "C"], window)
        for sym in ["D", "E"]:
            srets = oracle.load_window_returns(sym, AS_OF, window)
            bench = oracle.core_mean_benchmark(core_rets, len(srets))
            assert bench is not None
            o_alpha, o_beta = oracle.alpha_beta(srets, bench)
            o_up, o_down, _ = oracle.capture(srets, bench)
            row = StockLeadershipScore.objects.get(
                theme=eg_theme_key("orc-2"), stock_id=sym, window=window)
            assert row.benchmark_kind == KIND_SAT
            assert row.theme_beta == pytest.approx(o_beta, **APPROX)
            assert row.theme_alpha == pytest.approx(o_alpha, **APPROX)
            assert row.up_capture == pytest.approx(o_up, **APPROX)
            assert row.down_capture == pytest.approx(o_down, **APPROX)

    def test_edge_single_core_oracle_null(self):
        """엣지: 코어 1개 → 오라클도 None, 프로덕션도 코어 α/β NULL."""
        _mk_eg("orc-edge", [("A", "core", 0.0), ("S1", "satellite", 1.0),
                            ("S2", "satellite", 2.0), ("S3", "satellite", 3.0)])
        compute_eventgroup_leadership_scores(AS_OF)
        core_rets = _oracle_returns(["A"], 20)
        assert oracle.core_loo_benchmark(core_rets, "A") is None  # 오라클: LOO 불가
        row = StockLeadershipScore.objects.get(
            theme=eg_theme_key("orc-edge"), stock_id="A", window=20)
        assert row.theme_beta is None  # 프로덕션도 NULL


# ─────────────────────────────── L1 불변식 스위트 ───────────────────────────────

@pytest.mark.django_db
class TestL1Invariants:
    @pytest.fixture
    def two_groups(self):
        _mk_eg("inv-1", [("A", "core", 0.0), ("B", "core", 1.1), ("C", "core", 2.2),
                         ("D", "satellite", 3.3)])
        _mk_eg("inv-2", [("M", "core", 0.5), ("N", "core", 1.5), ("O", "core", 2.5),
                         ("P", "satellite", 3.5), ("Q", "satellite", 4.5)])
        _stock("OUTSIDER")
        _make_prices("OUTSIDER", 9.0)
        compute_eventgroup_leadership_scores(AS_OF)

    def test_role_benchmark_separation(self, two_groups):
        """코어→core_loo, 위성→sat_coremean. 역할 오분류 0."""
        for slug, cores, sats in [("inv-1", {"A", "B", "C"}, {"D"}),
                                   ("inv-2", {"M", "N", "O"}, {"P", "Q"})]:
            theme = eg_theme_key(slug)
            kinds = {r.stock_id: r.benchmark_kind
                     for r in StockLeadershipScore.objects.filter(theme=theme, window=20)}
            for c in cores:
                assert kinds[c] == KIND_CORE
            for s in sats:
                assert kinds[s] == KIND_SAT

    def test_capture_spread_identity(self, two_groups):
        """capture_spread == up_capture − down_capture (둘 다 non-null일 때)."""
        for r in StockLeadershipScore.objects.filter(theme__startswith="eg:"):
            if r.up_capture is not None and r.down_capture is not None:
                assert r.capture_spread == pytest.approx(r.up_capture - r.down_capture, abs=1e-9)
            else:
                assert r.capture_spread is None

    def test_non_member_no_eg_score(self, two_groups):
        """EventGroup 비소속 종목엔 eg: 점수 없음."""
        assert not StockLeadershipScore.objects.filter(
            stock_id="OUTSIDER", theme__startswith="eg:").exists()

    def test_beta_in_sane_range(self, two_groups):
        """β 정상범위(합성 데이터 — 상식 경계). 이탈 시 실패(플래그)."""
        for r in StockLeadershipScore.objects.filter(theme__startswith="eg:", window=20):
            if r.theme_beta is not None:
                assert -50.0 < r.theme_beta < 50.0, f"{r.stock_id} β 이탈: {r.theme_beta}"

    def test_small_sample_core_null(self):
        """코어 2개 → 코어 LOO 자기제외 후 <2 → α/β NULL."""
        _mk_eg("inv-thin", [("A", "core", 0.0), ("B", "core", 1.0), ("S", "satellite", 2.0)])
        compute_eventgroup_leadership_scores(AS_OF)
        a = StockLeadershipScore.objects.get(theme=eg_theme_key("inv-thin"), stock_id="A", window=20)
        assert a.theme_beta is None
        assert a.trend_quality is not None


# ─────────────────────────────── L2 구신 diff 특성화 ───────────────────────────────

@pytest.mark.django_db
class TestL2DiffCharacterization:
    def test_all_core_reduces_to_legacy(self):
        """
        all-core EventGroup == 동일 멤버 theme_tags theme: 코어-LOO == theme-LOO.
        멤버십 동일 → 점수 동일(reduction). 이동의 '바닥'을 고정.
        """
        syms = [("A", 0.0), ("B", 1.1), ("C", 2.2), ("D", 3.3)]
        for s, ph in syms:
            _make_prices(s, ph)
            CompanyChainProfile.objects.update_or_create(
                symbol_id=s, defaults={"theme_tags": ["LEGACYTHEME"]})
        # 옛 경로
        compute_leadership_scores(AS_OF)
        # 새 경로: 동일 4종목 전부 코어
        EventGroup.objects.create(
            name="allcore", slug="allcore", source="news_jaccard",
            confidence=0.5, cohesion=0.5, member_count=4, core_count=4, is_hidden=False)
        eg = EventGroup.objects.get(slug="allcore")
        for s, _ in syms:
            GroupMembership.objects.create(group=eg, symbol_id=s, role="core")
        compute_eventgroup_leadership_scores(AS_OF)

        moved = 0
        for s, _ in syms:
            old = StockLeadershipScore.objects.get(theme="LEGACYTHEME", stock_id=s, window=20)
            new = StockLeadershipScore.objects.get(theme=eg_theme_key("allcore"), stock_id=s, window=20)
            assert new.theme_beta == pytest.approx(old.theme_beta, **APPROX), f"{s} reduction 실패"
            if old.theme_beta is not None and new.theme_beta is not None:
                if abs(old.theme_beta - new.theme_beta) > 1e-6:
                    moved += 1
        assert moved == 0  # 동일 멤버십 → 이동 0

    def test_satellite_diverges_from_legacy_theme(self):
        """
        core{A,B,C}+sat{D,E} 새 경로 vs theme{A,B,C,D,E} 옛 경로:
        위성 D 벤치마크(코어평균 A,B,C)는 옛 theme-LOO(A,B,C,E — E 포함)와 다름 → 점수 이동.
        이동이 '멤버십/벤치마크 차이(E 제외)'로 설명됨을 특성화.
        """
        syms = [("A", 0.0, "core"), ("B", 1.1, "core"), ("C", 2.2, "core"),
                ("D", 3.3, "satellite"), ("E", 4.4, "satellite")]
        for s, ph, _ in syms:
            _make_prices(s, ph)
            CompanyChainProfile.objects.update_or_create(
                symbol_id=s, defaults={"theme_tags": ["MIXED"]})
        compute_leadership_scores(AS_OF)  # 옛: 5종목 한 theme
        _mk_eg("mixed", [(s, role, ph) for s, ph, role in syms])  # _make_prices 재호출 ignore_conflicts
        compute_eventgroup_leadership_scores(AS_OF)

        old_d = StockLeadershipScore.objects.get(theme="MIXED", stock_id="D", window=20)
        new_d = StockLeadershipScore.objects.get(theme=eg_theme_key("mixed"), stock_id="D", window=20)
        # 위성 D: 옛(A,B,C,E LOO) vs 새(A,B,C mean) → E 제외로 발산
        assert old_d.theme_beta is not None and new_d.theme_beta is not None
        assert abs(old_d.theme_beta - new_d.theme_beta) > 1e-9, "위성 발산 미검출(특성화 실패)"

        # 설명 검증: 새 D 벤치마크 == 코어평균(A,B,C), 옛 D 벤치마크 == LOO(A,B,C,E)
        core_rets = _oracle_returns(["A", "B", "C"], 20)
        all_rets = _oracle_returns(["A", "B", "C", "E"], 20)
        srets = oracle.load_window_returns("D", AS_OF, 20)
        _, new_beta_oracle = oracle.alpha_beta(srets, oracle.core_mean_benchmark(core_rets, len(srets)))
        loo_abce = [sum(all_rets[m][i] for m in ["A", "B", "C", "E"]) / 4 for i in range(len(srets))]
        _, old_beta_oracle = oracle.alpha_beta(srets, loo_abce)
        assert new_d.theme_beta == pytest.approx(new_beta_oracle, **APPROX)  # 새=코어평균
        assert old_d.theme_beta == pytest.approx(old_beta_oracle, **APPROX)  # 옛=theme LOO
