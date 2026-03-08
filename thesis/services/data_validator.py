"""Stage 0: Data Validation Layer (수학 모델 v2.3.2, Section 2)"""

import math
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

STALE_THRESHOLD_SECONDS = 259200  # 72h

VALIDATION_ACTIONS = {
    'null_value': 'skip',
    'non_finite': 'skip',
    'below_minimum': 'skip',
    'above_maximum': 'skip',
    'stale_data': 'skip',
    'extreme_jump': 'skip',
    'extreme_jump_allowed': 'save',
    'ok': 'save',
}


def validate_reading(indicator, raw_value, asof, fetched_at=None):
    """
    데이터 유효성 검증. (is_valid, reason) 반환.

    검증 순서 (v2.3.2 확정):
      1. null       - 값 자체가 없음
      2. non_finite - NaN/inf (API 오류)
      3. min/max    - 범위 벗어남
      4. stale      - 데이터가 오래됨 (jump보다 먼저)
      5. jump       - 전일 대비 급변 (정상 데이터끼리만 비교)
    """
    # 1. null
    if raw_value is None:
        return False, 'null_value'

    # 2. NaN/inf
    if not math.isfinite(raw_value):
        return False, 'non_finite'

    # 3. 범위 체크
    if indicator.min_valid_value is not None and raw_value < indicator.min_valid_value:
        return False, 'below_minimum'
    if indicator.max_valid_value is not None and raw_value > indicator.max_valid_value:
        return False, 'above_maximum'

    # 4. 신선도 (72시간) - jump보다 먼저
    effective_asof = asof or fetched_at
    if effective_asof:
        age_seconds = (timezone.now() - effective_asof).total_seconds()
        if age_seconds > STALE_THRESHOLD_SECONDS:
            return False, 'stale_data'

    # 5. 전일 대비 급변 - stale이 아닌 정상 데이터끼리만 비교
    prev = indicator.latest_validated_value
    if prev is not None and prev != 0:
        threshold = indicator.max_change_pct or 0.5
        change_pct = abs((raw_value - prev) / prev)
        if change_pct > threshold:
            if indicator.allow_extreme_jump:
                return True, 'extreme_jump_allowed'
            return False, 'extreme_jump'

    return True, 'ok'


def check_stale_indicators(thesis):
    """72시간 이상 validated reading이 없는 지표 목록 반환."""
    from thesis.models import ThesisIndicator

    stale = []
    indicators = thesis.indicators.filter(is_active=True, is_paused=False)
    now = timezone.now()

    for ind in indicators:
        latest = ind.readings.filter(
            validation_status__in=['ok', 'extreme_jump_allowed']
        ).order_by('-asof').first()

        if latest and (now - latest.asof).total_seconds() > STALE_THRESHOLD_SECONDS:
            stale.append(ind)
        elif not latest:
            stale.append(ind)

    return stale
