"""
DataValidator 단위 테스트 (수학 모델 v2.3.2, Section 2)

validate_reading() 검증 순서:
  1. null → 2. non_finite → 3. min/max → 4. stale(72h) → 5. extreme_jump
"""

import math
import pytest
from datetime import timedelta

from django.utils import timezone

from thesis.models import Thesis, ThesisPremise, ThesisIndicator, IndicatorReading
from thesis.services.data_validator import validate_reading


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_thesis(user):
    return Thesis.objects.create(
        user=user,
        title="Test Thesis",
        direction="bullish",
        target="AAPL",
        target_type="stock",
        thesis_type="trend",
        entry_source="free_input",
    )


def _make_indicator(thesis, **kwargs):
    defaults = dict(
        name="Test Indicator",
        indicator_type="market_data",
        data_source="fmp",
        support_direction="positive",
    )
    defaults.update(kwargs)
    return ThesisIndicator.objects.create(thesis=thesis, **defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestValidateNull:
    def test_validate_null_returns_false(self, user):
        thesis = _make_thesis(user)
        indicator = _make_indicator(thesis)

        is_valid, reason = validate_reading(indicator, None, timezone.now())

        assert is_valid is False
        assert reason == "null_value"


@pytest.mark.django_db
class TestValidateNonFinite:
    def test_validate_nan_returns_non_finite(self, user):
        thesis = _make_thesis(user)
        indicator = _make_indicator(thesis)

        is_valid, reason = validate_reading(indicator, float("nan"), timezone.now())

        assert is_valid is False
        assert reason == "non_finite"

    def test_validate_positive_inf_returns_non_finite(self, user):
        thesis = _make_thesis(user)
        indicator = _make_indicator(thesis)

        is_valid, reason = validate_reading(indicator, float("inf"), timezone.now())

        assert is_valid is False
        assert reason == "non_finite"

    def test_validate_negative_inf_returns_non_finite(self, user):
        thesis = _make_thesis(user)
        indicator = _make_indicator(thesis)

        is_valid, reason = validate_reading(indicator, float("-inf"), timezone.now())

        assert is_valid is False
        assert reason == "non_finite"


@pytest.mark.django_db
class TestValidateRange:
    def test_validate_below_minimum(self, user):
        thesis = _make_thesis(user)
        indicator = _make_indicator(thesis, min_valid_value=0.0)

        is_valid, reason = validate_reading(indicator, -1.0, timezone.now())

        assert is_valid is False
        assert reason == "below_minimum"

    def test_validate_above_maximum(self, user):
        thesis = _make_thesis(user)
        indicator = _make_indicator(thesis, max_valid_value=100.0)

        is_valid, reason = validate_reading(indicator, 101.0, timezone.now())

        assert is_valid is False
        assert reason == "above_maximum"

    def test_validate_at_boundary_passes(self, user):
        """경계값 자체는 유효."""
        thesis = _make_thesis(user)
        indicator = _make_indicator(thesis, min_valid_value=0.0, max_valid_value=100.0)

        is_valid_min, _ = validate_reading(indicator, 0.0, timezone.now())
        is_valid_max, _ = validate_reading(indicator, 100.0, timezone.now())

        assert is_valid_min is True
        assert is_valid_max is True


@pytest.mark.django_db
class TestValidateStale:
    def test_validate_stale_72h(self, user):
        """73시간 전 asof → stale_data."""
        thesis = _make_thesis(user)
        indicator = _make_indicator(thesis)

        stale_asof = timezone.now() - timedelta(hours=73)

        is_valid, reason = validate_reading(indicator, 50.0, stale_asof)

        assert is_valid is False
        assert reason == "stale_data"

    def test_stale_checked_before_jump(self, user):
        """
        stale + extreme jump 동시 발생 시 stale이 먼저 감지되어야 한다 (v2.3.2).

        조건: prev=100, raw=300 (200% 변화 > 기본 50%), asof=73h 전
        """
        thesis = _make_thesis(user)
        indicator = _make_indicator(thesis, max_change_pct=0.5)

        # 기준값 설정: 유효한 이전 reading 추가
        valid_asof = timezone.now() - timedelta(hours=1)
        IndicatorReading.objects.create(
            indicator=indicator,
            value=100.0,
            raw_value=100.0,
            asof=valid_asof,
            validation_status="ok",
        )

        # 73시간 전 + 극단 점프 값
        stale_asof = timezone.now() - timedelta(hours=73)

        is_valid, reason = validate_reading(indicator, 300.0, stale_asof)

        assert is_valid is False
        assert reason == "stale_data"  # jump보다 stale이 먼저


@pytest.mark.django_db
class TestValidateExtremeJump:
    def test_extreme_jump_returns_false_when_not_allowed(self, user):
        """allow_extreme_jump=False → extreme_jump (skip)."""
        thesis = _make_thesis(user)
        indicator = _make_indicator(thesis, max_change_pct=0.5, allow_extreme_jump=False)

        # 이전 유효 reading: 100
        IndicatorReading.objects.create(
            indicator=indicator,
            value=100.0,
            raw_value=100.0,
            asof=timezone.now() - timedelta(hours=1),
            validation_status="ok",
        )

        # 200% 변화 (> 50% 임계)
        is_valid, reason = validate_reading(indicator, 300.0, timezone.now())

        assert is_valid is False
        assert reason == "extreme_jump"

    def test_extreme_jump_allowed_returns_true(self, user):
        """allow_extreme_jump=True → extreme_jump_allowed (save)."""
        thesis = _make_thesis(user)
        indicator = _make_indicator(thesis, max_change_pct=0.5, allow_extreme_jump=True)

        IndicatorReading.objects.create(
            indicator=indicator,
            value=100.0,
            raw_value=100.0,
            asof=timezone.now() - timedelta(hours=1),
            validation_status="ok",
        )

        is_valid, reason = validate_reading(indicator, 300.0, timezone.now())

        assert is_valid is True
        assert reason == "extreme_jump_allowed"


@pytest.mark.django_db
class TestLatestValidatedValue:
    def test_latest_validated_value_skips_invalid_readings(self, user):
        """
        latest_validated_value는 ok/extreme_jump_allowed 상태 reading만 반환하고
        null_value, stale_data 등 무효 상태 reading은 무시한다.
        """
        thesis = _make_thesis(user)
        indicator = _make_indicator(thesis)

        now = timezone.now()

        # 가장 최근이지만 무효인 reading
        IndicatorReading.objects.create(
            indicator=indicator,
            value=999.0,
            raw_value=999.0,
            asof=now - timedelta(minutes=10),
            validation_status="stale_data",
        )

        # 그 전에 유효한 reading
        IndicatorReading.objects.create(
            indicator=indicator,
            value=42.0,
            raw_value=42.0,
            asof=now - timedelta(hours=2),
            validation_status="ok",
        )

        # extreme_jump_allowed도 유효로 처리되어야 함
        IndicatorReading.objects.create(
            indicator=indicator,
            value=55.0,
            raw_value=55.0,
            asof=now - timedelta(hours=1),
            validation_status="extreme_jump_allowed",
        )

        # extreme_jump_allowed가 ok보다 더 최근이므로 그 값이 반환되어야 함
        assert indicator.latest_validated_value == 55.0
