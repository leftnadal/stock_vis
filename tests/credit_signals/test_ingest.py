"""§8.1 upsert 멱등성 + revise."""
from decimal import Decimal

import pytest

from apps.credit_signals.models import MacroSeriesHistory
from apps.credit_signals.services.ingest_service import upsert_observations


@pytest.mark.django_db
class TestUpsertObservations:
    SID = "BAMLH0A0HYM2"

    def test_insert_creates_rows(self):
        obs = [
            {"date": "2026-07-01", "value": "3.50"},
            {"date": "2026-07-02", "value": "3.52"},
        ]
        result = upsert_observations(self.SID, obs)
        assert result == {"created": 2, "updated": 0, "skipped": 0}
        assert MacroSeriesHistory.objects.filter(series_id=self.SID).count() == 2

    def test_reingest_is_idempotent(self):
        """같은 (series_id, date) 재수집 → 중복 없음, update 0."""
        obs = [{"date": "2026-07-01", "value": "3.50"}]
        upsert_observations(self.SID, obs)
        result = upsert_observations(self.SID, obs)
        assert result == {"created": 0, "updated": 0, "skipped": 0}
        assert MacroSeriesHistory.objects.filter(series_id=self.SID).count() == 1

    def test_reingest_precision_no_false_update(self):
        """저장 정밀도(4자리)와 raw 미세 차이가 허위 revise를 유발하지 않음."""
        upsert_observations(self.SID, [{"date": "2026-07-01", "value": "3.5"}])
        # 동일 값을 더 긴 정밀도로 재수집 → quantize 후 동일 → no-op
        result = upsert_observations(self.SID, [{"date": "2026-07-01", "value": "3.50000"}])
        assert result == {"created": 0, "updated": 0, "skipped": 0}

    def test_revise_updates_value_and_sets_revised_at(self):
        """FRED revise: value 갱신 + revised_at 기록, ingested_at 유지."""
        upsert_observations(self.SID, [{"date": "2026-07-01", "value": "3.50"}])
        row = MacroSeriesHistory.objects.get(series_id=self.SID, date="2026-07-01")
        original_ingested = row.ingested_at
        assert row.revised_at is None

        result = upsert_observations(self.SID, [{"date": "2026-07-01", "value": "3.99"}])
        assert result == {"created": 0, "updated": 1, "skipped": 0}
        row.refresh_from_db()
        assert row.value == Decimal("3.9900")
        assert row.revised_at is not None
        assert row.ingested_at == original_ingested  # 최초 적재 시각 유지

    def test_missing_values_skipped(self):
        """FRED 결측('.'/빈값)은 skip (에러 아님)."""
        obs = [
            {"date": "2026-07-01", "value": "."},
            {"date": "2026-07-02", "value": ""},
            {"date": "2026-07-03", "value": "3.50"},
        ]
        result = upsert_observations(self.SID, obs)
        assert result == {"created": 1, "updated": 0, "skipped": 2}
