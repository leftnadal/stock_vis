"""§8.5 flag off no-op · §8.6 verify (결측→ERROR, 주말 통과)."""
import logging
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

import pytest

from apps.credit_signals.constants import FRED_SERIES
from apps.credit_signals.models import MacroSeriesHistory
from apps.credit_signals import tasks


class TestFlagOff:
    def test_ingest_noop_when_flag_off(self, settings):
        settings.CREDIT_SIGNALS_ENABLED = False
        with mock.patch("packages.shared.api_request.fred_client.FREDClient") as m:
            result = tasks.ingest_fred_daily_task.apply().result
        assert result == {"enabled": False}
        m.assert_not_called()  # 네트워크 진입 전 return

    def test_compute_noop_when_flag_off(self, settings):
        settings.CREDIT_SIGNALS_ENABLED = False
        result = tasks.compute_credit_signals_task.apply().result
        assert result == {"enabled": False}

    def test_verify_noop_when_flag_off(self, settings):
        settings.CREDIT_SIGNALS_ENABLED = False
        result = tasks.check_credit_ingest_succeeded.apply().result
        assert result == {"enabled": False}


@pytest.mark.django_db
class TestVerify:
    MONDAY = date(2026, 7, 6)     # 월요일
    SATURDAY = date(2026, 7, 4)   # 토요일

    def _seed_fresh(self, as_of):
        for sid in FRED_SERIES:
            MacroSeriesHistory.objects.create(
                series_id=sid, date=as_of, value=Decimal("3.50")
            )

    def test_weekday_missing_data_logs_error(self, settings, caplog):
        """미 영업일 + 데이터 결측 → ERROR 로그, ok=False."""
        settings.CREDIT_SIGNALS_ENABLED = True
        with mock.patch.object(tasks.timezone, "localdate", return_value=self.MONDAY):
            with caplog.at_level(logging.ERROR, logger="apps.credit_signals.tasks"):
                result = tasks.check_credit_ingest_succeeded.apply().result
        assert result["ok"] is False
        assert len(result["stale"]) == len(FRED_SERIES)
        assert any("verify FAILED" in r.message for r in caplog.records)

    def test_weekday_fresh_data_ok(self, settings, caplog):
        """미 영업일 + 최신 데이터 → ok=True, ERROR 없음."""
        settings.CREDIT_SIGNALS_ENABLED = True
        self._seed_fresh(self.MONDAY)
        with mock.patch.object(tasks.timezone, "localdate", return_value=self.MONDAY):
            with caplog.at_level(logging.ERROR, logger="apps.credit_signals.tasks"):
                result = tasks.check_credit_ingest_succeeded.apply().result
        assert result["ok"] is True
        assert not any(r.levelno >= logging.ERROR for r in caplog.records)

    def test_weekday_stale_data_logs_error(self, settings, caplog):
        """데이터가 있어도 stale(임계 초과) → ERROR."""
        settings.CREDIT_SIGNALS_ENABLED = True
        old = self.MONDAY - timedelta(days=30)
        self._seed_fresh(old)
        with mock.patch.object(tasks.timezone, "localdate", return_value=self.MONDAY):
            with caplog.at_level(logging.ERROR, logger="apps.credit_signals.tasks"):
                result = tasks.check_credit_ingest_succeeded.apply().result
        assert result["ok"] is False
        assert any(r.levelno >= logging.ERROR for r in caplog.records)

    def test_weekend_passes_even_with_missing_data(self, settings, caplog):
        """주말은 데이터 결측이어도 통과 (에러 없음)."""
        settings.CREDIT_SIGNALS_ENABLED = True
        with mock.patch.object(tasks.timezone, "localdate", return_value=self.SATURDAY):
            with caplog.at_level(logging.ERROR, logger="apps.credit_signals.tasks"):
                result = tasks.check_credit_ingest_succeeded.apply().result
        assert result["skipped"] == "weekend"
        assert not any(r.levelno >= logging.ERROR for r in caplog.records)


@pytest.mark.django_db
class TestIngestChainsCompute:
    def test_ingest_triggers_compute(self, settings):
        """ingest 성공 → compute 태스크 체이닝 (.delay 호출)."""
        settings.CREDIT_SIGNALS_ENABLED = True
        fake_obs = [{"date": "2026-07-06", "value": "3.50"}]

        fake_client = mock.MagicMock()
        fake_client.get_series_observations.return_value = fake_obs

        with mock.patch(
            "packages.shared.api_request.fred_client.FREDClient",
            return_value=fake_client,
        ), mock.patch.object(
            tasks.compute_credit_signals_task, "delay"
        ) as mock_delay:
            result = tasks.ingest_fred_daily_task.apply().result

        assert result["enabled"] is True
        mock_delay.assert_called_once()
        # 6개 시리즈 전부 조회
        assert fake_client.get_series_observations.call_count == len(FRED_SERIES)
