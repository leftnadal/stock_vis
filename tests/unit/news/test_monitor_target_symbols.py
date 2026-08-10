"""_get_monitor_target_symbols + collect_daily_news 합집합 주입 (NEWS-P0-FIX T3/S2).

배경(RECON-NEWS-P0): TLN 등 비SP500 보유종목은 monitor로는 추적되지만
뉴스 유니버스(mover 상위20 / orchestrator SP500 / category custom) 어디에도
없어 NewsEntity 0 사각지대에 놓인다. collect_daily_news가
mover ∪ monitor-target(활성 stock-scope) 합집합으로 심볼을 결정하도록 보강했다.

경계 준수: services/news는 apps.monitor를 정적 import하지 않는다(leaf 역결합
금지) — Django 앱 레지스트리(`django.apps.apps.get_model`)로 느슨하게 참조한다.
"""
from unittest.mock import MagicMock, patch

import pytest

from services.news.tasks import _get_monitor_target_symbols, collect_daily_news


@pytest.mark.django_db
class TestGetMonitorTargetSymbols:
    def _make_user(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        return User.objects.create_user(username="mtsym-user", password="x")

    def test_returns_operational_stock_scope_targets(self):
        # NEWS-S2 확정(2026-08-10): "운용 중" = archived 제외 전부 — setting_up·active·paused 포함.
        # (보유 종목이 전부 setting_up이라 status=ACTIVE 문자 그대로면 no-op이 됨.)
        from apps.monitor.models.monitor import Monitor

        user = self._make_user()
        Monitor.objects.create(
            user=user, scope=Monitor.Scope.STOCK, target_ref="tln",  # 소문자→대문자 정규화 확인
            name="TLN monitor", status=Monitor.Status.ACTIVE,
        )
        # scope != stock → 제외
        Monitor.objects.create(
            user=user, scope=Monitor.Scope.SECTOR, target_ref="tech",
            name="tech sector monitor", status=Monitor.Status.ACTIVE,
        )
        # setting_up = 운용 중 → 포함(보유종목 실제 상태)
        Monitor.objects.create(
            user=user, scope=Monitor.Scope.STOCK, target_ref="AAPL",
            name="AAPL setting up", status=Monitor.Status.SETTING_UP,
        )
        # paused = 운용 중(재개 가능) → 포함 (NEWS-S2 확정: archived만 제외)
        Monitor.objects.create(
            user=user, scope=Monitor.Scope.STOCK, target_ref="MSFT",
            name="MSFT paused", status=Monitor.Status.PAUSED,
        )
        # archived → 제외(유일한 제외 status)
        Monitor.objects.create(
            user=user, scope=Monitor.Scope.STOCK, target_ref="NVDA",
            name="NVDA archived", status=Monitor.Status.ARCHIVED,
        )

        result = _get_monitor_target_symbols(max_symbols=10)

        # setting_up + active + paused 포함, archived + sector 제외
        assert set(result) == {"TLN", "AAPL", "MSFT"}

    def test_respects_max_symbols(self):
        from apps.monitor.models.monitor import Monitor

        user = self._make_user()
        for i in range(5):
            Monitor.objects.create(
                user=user,
                scope=Monitor.Scope.STOCK,
                target_ref=f"SYM{i}",
                name=f"sym{i}",
                status=Monitor.Status.ACTIVE,
            )

        result = _get_monitor_target_symbols(max_symbols=3)

        assert len(result) == 3

    def test_no_active_monitors_returns_empty_list(self):
        result = _get_monitor_target_symbols(max_symbols=10)
        assert result == []

    def test_swallows_exception_and_returns_empty_list(self):
        with patch(
            "django.apps.apps.get_model", side_effect=LookupError("monitor app missing")
        ):
            assert _get_monitor_target_symbols() == []


class TestCollectDailyNewsMoverMonitorUnion:
    @pytest.mark.django_db
    def test_dedupe_and_cap_at_30(self):
        mover = [f"M{i}" for i in range(20)]
        monitor_targets = ["M0", "TLN", "IONQ", "IREN", "M1", "M2", "M3", "M4", "M5", "M6"]

        agg = MagicMock()
        agg.fetch_and_save_company_news.return_value = {"saved": 0, "updated": 0}
        agg.fetch_and_save_market_news.return_value = {"saved": 0, "updated": 0}

        with patch("services.news.tasks._get_mover_symbols", return_value=mover), \
             patch(
                 "services.news.tasks._get_monitor_target_symbols",
                 return_value=monitor_targets,
             ), \
             patch(
                 "services.news.services.aggregator.NewsAggregatorService",
                 return_value=agg,
             ), \
             patch("services.news.tasks.time.sleep"):
            result = collect_daily_news.apply(kwargs={}).get()

        called_symbols = [
            c.kwargs.get("symbol", c.args[0] if c.args else None)
            for c in agg.fetch_and_save_company_news.call_args_list
        ]

        # 합집합 dedupe: M0 은 mover에도 monitor_targets에도 있음 → 1회만
        assert called_symbols.count("M0") == 1
        # 신규 편입 심볼(TLN·IONQ·IREN 등)이 실제로 수집 대상에 포함됐는지
        assert "TLN" in called_symbols
        assert "IONQ" in called_symbols
        assert "IREN" in called_symbols
        # 상한 30 (mover 20 + monitor 10 최대) 준수
        assert len(called_symbols) <= 30
        assert result["symbols_processed"] == len(called_symbols)

    @pytest.mark.django_db
    def test_no_monitor_targets_falls_back_to_mover_only(self):
        mover = [f"M{i}" for i in range(5)]

        agg = MagicMock()
        agg.fetch_and_save_company_news.return_value = {"saved": 0, "updated": 0}
        agg.fetch_and_save_market_news.return_value = {"saved": 0, "updated": 0}

        with patch("services.news.tasks._get_mover_symbols", return_value=mover), \
             patch("services.news.tasks._get_monitor_target_symbols", return_value=[]), \
             patch(
                 "services.news.services.aggregator.NewsAggregatorService",
                 return_value=agg,
             ), \
             patch("services.news.tasks.time.sleep"):
            result = collect_daily_news.apply(kwargs={}).get()

        assert result["symbols_processed"] == 5

    @pytest.mark.django_db
    def test_explicit_symbols_arg_bypasses_union(self):
        """symbols 인자를 명시하면 mover/monitor 합집합 로직을 타지 않는다(기존 행위 보존)."""
        agg = MagicMock()
        agg.fetch_and_save_company_news.return_value = {"saved": 0, "updated": 0}
        agg.fetch_and_save_market_news.return_value = {"saved": 0, "updated": 0}

        with patch("services.news.tasks._get_mover_symbols") as mock_mover, \
             patch("services.news.tasks._get_monitor_target_symbols") as mock_monitor, \
             patch(
                 "services.news.services.aggregator.NewsAggregatorService",
                 return_value=agg,
             ), \
             patch("services.news.tasks.time.sleep"):
            result = collect_daily_news.apply(kwargs={"symbols": ["ZZZ"]}).get()

        mock_mover.assert_not_called()
        mock_monitor.assert_not_called()
        assert result["symbols_processed"] == 1
