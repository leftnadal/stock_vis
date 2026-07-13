"""P2-IMPRESSION-BUILD S1: ImpressionLog 스키마 스모크 테스트.

순수 스키마 검증(모델 마이그레이션 + 기본 CRUD + partial unique 제약).
write(upsert/증가) 로직은 S2 소관 — 여기서는 스키마 계약만 확인한다.

경계(lesson #43): 이 테스트는 IssuanceLog를 참조·import하지 않는다.
구획 준수: tests/ 밖 in-app 배치(DoD = packages/shared/** 만).
"""

from datetime import datetime, timezone

import pytest
from django.db import IntegrityError, transaction

from packages.shared.stocks.models import ImpressionLog

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _dt():
    return datetime(2026, 7, 13, 12, 0, 0, tzinfo=timezone.utc)


def test_create_impression_and_click_rows():
    """impression·click 행 생성 + 필드 왕복(기본 CRUD)."""
    imp = ImpressionLog.objects.create(
        user_id=42,
        surface=ImpressionLog.SURFACE_DASHBOARD_EOD,
        object_ref="AAPL:2026-07-13:V1",
        event_type=ImpressionLog.EVENT_IMPRESSION,
        first_seen_at=_dt(),
        seen_count=3,
        session_id="sess-abc",
    )
    click = ImpressionLog.objects.create(
        user_id=42,
        surface=ImpressionLog.SURFACE_NEWS_CHIP,
        object_ref="news-chip-7",
        event_type=ImpressionLog.EVENT_CLICK,
        first_seen_at=_dt(),
        session_id="sess-abc",
    )

    imp.refresh_from_db()
    assert imp.pk is not None
    assert imp.seen_count == 3
    assert imp.created_at is not None and imp.updated_at is not None
    assert click.event_type == ImpressionLog.EVENT_CLICK
    assert click.seen_count == 0  # click 행은 미사용(기본 0)
    assert ImpressionLog.objects.count() == 2


def test_partial_unique_impression_key():
    """(user_id, surface, object_ref) partial unique = impression 행에만 적용."""
    common = dict(
        user_id=7,
        surface=ImpressionLog.SURFACE_DASHBOARD_EOD,
        object_ref="MSFT:2026-07-13:V1",
        first_seen_at=_dt(),
        session_id="s1",
    )
    ImpressionLog.objects.create(event_type=ImpressionLog.EVENT_IMPRESSION, **common)

    # 같은 키 impression 재삽입 → 제약 위반
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            ImpressionLog.objects.create(
                event_type=ImpressionLog.EVENT_IMPRESSION, **common
            )


def test_click_rows_not_constrained():
    """click 행에는 partial unique 없음 — 같은 키 다중 click 허용."""
    common = dict(
        user_id=7,
        surface=ImpressionLog.SURFACE_DASHBOARD_EOD,
        object_ref="NVDA:2026-07-13:V1",
        first_seen_at=_dt(),
        session_id="s1",
    )
    ImpressionLog.objects.create(event_type=ImpressionLog.EVENT_CLICK, **common)
    ImpressionLog.objects.create(event_type=ImpressionLog.EVENT_CLICK, **common)
    assert (
        ImpressionLog.objects.filter(
            event_type=ImpressionLog.EVENT_CLICK, object_ref="NVDA:2026-07-13:V1"
        ).count()
        == 2
    )


def test_different_object_ref_allowed():
    """impression이라도 object_ref가 다르면 허용."""
    base = dict(
        user_id=7,
        surface=ImpressionLog.SURFACE_DASHBOARD_EOD,
        event_type=ImpressionLog.EVENT_IMPRESSION,
        first_seen_at=_dt(),
        session_id="s1",
    )
    ImpressionLog.objects.create(object_ref="A:1", **base)
    ImpressionLog.objects.create(object_ref="A:2", **base)
    assert ImpressionLog.objects.filter(event_type="impression").count() == 2


def test_choices_constants_present():
    """surface·event_type 상수/choices 분리 확인."""
    surfaces = {c[0] for c in ImpressionLog.SURFACE_CHOICES}
    assert {"dashboard_eod", "chain_sight", "news_chip"} <= surfaces
    events = {c[0] for c in ImpressionLog.EVENT_TYPE_CHOICES}
    assert events == {"impression", "click"}
