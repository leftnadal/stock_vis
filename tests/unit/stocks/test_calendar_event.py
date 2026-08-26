"""CalendarEvent 원장 단위 테스트 (EVT-IMPL-1 STEP 2-4).

멱등 upsert(record_observation) · date_observed_count 증가 · unique_together ·
status/session/event_type 유효값. DB = pytest 자동 생성(실 DB migrate 무관).
"""
from datetime import date

import pytest
from django.db import IntegrityError, transaction

from packages.shared.stocks.models import CalendarEvent


@pytest.mark.django_db
class TestCalendarEventUpsert:
    def test_record_observation_creates_then_increments(self):
        """동일 (type,symbol,date) 재관측 → 1행 유지 + date_observed_count 증가."""
        obj1, created1 = CalendarEvent.record_observation(
            event_type=CalendarEvent.EventType.EARNINGS,
            symbol="NVDA",
            event_date=date(2026, 8, 27),
            defaults={"session": CalendarEvent.Session.AMC, "eps_estimated": "1.2500"},
        )
        assert created1 is True
        assert obj1.date_observed_count == 1

        obj2, created2 = CalendarEvent.record_observation(
            event_type=CalendarEvent.EventType.EARNINGS,
            symbol="NVDA",
            event_date=date(2026, 8, 27),
            defaults={"eps_estimated": "1.3000"},
        )
        assert created2 is False
        assert obj2.pk == obj1.pk
        assert obj2.date_observed_count == 2
        assert str(obj2.eps_estimated) == "1.3000"  # defaults 갱신
        assert CalendarEvent.objects.count() == 1  # 중복 미생성

    def test_record_observation_uppercases_symbol(self):
        obj, created = CalendarEvent.record_observation(
            event_type=CalendarEvent.EventType.DIVIDEND,
            symbol="aapl",
            event_date=date(2026, 9, 1),
        )
        assert obj.symbol == "AAPL"

    def test_unique_together_blocks_raw_duplicate(self):
        CalendarEvent.objects.create(
            event_type=CalendarEvent.EventType.SPLIT,
            symbol="TSLA",
            event_date=date(2026, 9, 10),
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                CalendarEvent.objects.create(
                    event_type=CalendarEvent.EventType.SPLIT,
                    symbol="TSLA",
                    event_date=date(2026, 9, 10),
                )

    def test_different_type_same_symbol_date_coexist(self):
        """멱등 키에 event_type 포함 → 같은 종목·날짜라도 유형 다르면 별개 행."""
        d = date(2026, 9, 15)
        CalendarEvent.objects.create(event_type=CalendarEvent.EventType.EARNINGS, symbol="MSFT", event_date=d)
        CalendarEvent.objects.create(event_type=CalendarEvent.EventType.DIVIDEND, symbol="MSFT", event_date=d)
        assert CalendarEvent.objects.filter(symbol="MSFT", event_date=d).count() == 2


@pytest.mark.django_db
class TestCalendarEventDefaults:
    def test_defaults(self):
        obj = CalendarEvent.objects.create(
            event_type=CalendarEvent.EventType.EARNINGS,
            symbol="AMD",
            event_date=date(2026, 10, 1),
        )
        assert obj.session == CalendarEvent.Session.UNKNOWN
        assert obj.status == CalendarEvent.Status.SCHEDULED
        assert obj.date_observed_count == 1
        assert obj.source == "fmp"
        assert obj.first_seen_at is not None
        assert obj.last_seen_at is not None

    def test_status_transition_values(self):
        """status 유효 전이값 = scheduled/occurred/stale."""
        assert set(CalendarEvent.Status.values) == {"scheduled", "occurred", "stale"}
        obj = CalendarEvent.objects.create(
            event_type=CalendarEvent.EventType.EARNINGS, symbol="INTC", event_date=date(2026, 10, 5),
        )
        obj.status = CalendarEvent.Status.OCCURRED
        obj.eps_actual = "0.4500"
        obj.save()
        obj.refresh_from_db()
        assert obj.status == "occurred"
        assert str(obj.eps_actual) == "0.4500"

    def test_event_type_and_session_choices(self):
        assert set(CalendarEvent.EventType.values) == {"EARNINGS", "DIVIDEND", "SPLIT"}
        assert set(CalendarEvent.Session.values) == {"BMO", "AMC", "UNKNOWN"}
