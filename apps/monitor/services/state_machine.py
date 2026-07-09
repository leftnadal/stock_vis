"""Stage 3: Monitor State Machine (수학 모델 v2.3.2, Section 5 이식).

MON-P2-S2 이식: thesis_state_machine → apps/monitor. 소비 = Monitor 인스턴스.
status 매핑: 구 thesis 'closed' → Monitor 'archived'. current_state·target_date_end 사용.
`score_to_phase`(달 위상)는 순수 함수 그대로.
"""

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)

# 상태 전환 보류 기준
DATA_COVERAGE_THRESHOLD = 0.6
WARMING_UP_DAYS = 5
NEEDS_REVIEW_DAYS = 90
CRITICAL_SCORE_THRESHOLD = -0.6
DAILY_CHANGE_CRITICAL = 0.3
TREND_THRESHOLD = 0.15
TREND_MIN_SNAPSHOTS = 3


def determine_state(monitor, overall_score, prev_score,
                    data_coverage, days_active, score_history):
    """
    Monitor 상태 판정.

    Args:
        monitor: Monitor 인스턴스
        overall_score: 현재 overall score
        prev_score: 직전 스냅샷의 overall score (없으면 None)
        data_coverage: 유효 지표 비율 (0~1)
        days_active: Monitor 생성 후 경과 일수
        score_history: 최근 5일간 overall score 목록

    Returns:
        dict with state, state_changed, reminder_needed
    """
    current_state = monitor.current_state

    # 이미 보관(archived)된 Monitor는 상태 변경 안 함 (구 thesis 'closed' 대응)
    if monitor.status == 'archived':
        return {
            'state': current_state,
            'state_changed': False,
            'reminder_needed': False,
        }

    # data_coverage < 0.6이면 상태 전환 보류 (현상 유지)
    if data_coverage < DATA_COVERAGE_THRESHOLD:
        return {
            'state': current_state,
            'state_changed': False,
            'reminder_needed': False,
        }

    # paused 상태 체크
    if monitor.status == 'paused':
        new_state = 'paused'
        return {
            'state': new_state,
            'state_changed': new_state != current_state,
            'reminder_needed': False,
        }

    # warming_up: 5일 미만
    if days_active < WARMING_UP_DAYS:
        new_state = 'warming_up'
        return {
            'state': new_state,
            'state_changed': new_state != current_state,
            'reminder_needed': False,
        }

    # expired: target_date_end 지남
    if monitor.target_date_end and timezone.localdate() > monitor.target_date_end:
        new_state = 'expired'
        return {
            'state': new_state,
            'state_changed': new_state != current_state,
            'reminder_needed': False,
        }

    # needs_review: 90일 이상 + target_date_end 미설정
    if not monitor.target_date_end and days_active >= NEEDS_REVIEW_DAYS:
        new_state = 'needs_review'
        return {
            'state': new_state,
            'state_changed': new_state != current_state,
            'reminder_needed': True,
        }

    # 최근 스냅샷 기반 판정 (수학 모델 Section 5 의사코드 순서 그대로)
    recent = score_history[-5:] if score_history else []

    if len(recent) < TREND_MIN_SNAPSHOTS:
        new_state = 'active'
        return {
            'state': new_state,
            'state_changed': new_state != current_state,
            'reminder_needed': False,
        }

    # critical: 일일 score 변화 >= 0.3 (수학 모델 12.7)
    if len(recent) >= 2 and abs(recent[-1] - recent[-2]) > DAILY_CHANGE_CRITICAL:
        new_state = 'critical'
        return {
            'state': new_state,
            'state_changed': new_state != current_state,
            'reminder_needed': False,
        }

    # strengthening/weakening: 추세 판정
    trend = recent[-1] - recent[0]
    if trend > TREND_THRESHOLD:
        new_state = 'strengthening'
    elif trend < -TREND_THRESHOLD:
        new_state = 'weakening'
    # critical: overall_score < -0.6 (추세 판정 후 체크)
    elif overall_score < CRITICAL_SCORE_THRESHOLD:
        new_state = 'critical'
    else:
        new_state = 'active'

    return {
        'state': new_state,
        'state_changed': new_state != current_state,
        'reminder_needed': False,
    }


# 상태 심각도 랭크 (높을수록 건강) — 전이 악화/개선 판정 단일 출처 (MON-P3-ALERT).
# 트리아지 정렬(api/views._SEVERITY_WHENS)과 방향 일치: critical/expired/needs_review 최하.
STATE_RANK = {
    "strengthening": 4,
    "active": 3,
    "warming_up": 3,
    "paused": 3,
    "weakening": 2,
    "needs_review": 1,
    "critical": 0,
    "expired": 0,
}


def is_deterioration(from_state, to_state):
    """전이가 악화(심각도 랭크 하락)인가. 미지 상태는 중립(3)으로 방어."""
    return STATE_RANK.get(to_state, 3) < STATE_RANK.get(from_state, 3)


def score_to_phase(score):
    """score -> Moon Phase 시각화 (수학 모델 Section 5.4)."""
    if score > 0.6:
        return {'phase': 'full_moon', 'label': '가설이 빛나고 있어요', 'icon': '🌕'}
    elif score > 0.2:
        return {'phase': 'waxing', 'label': '조금씩 밝아지고 있어요', 'icon': '🌔'}
    elif score > -0.2:
        return {'phase': 'half_moon', 'label': '반반이에요', 'icon': '🌓'}
    elif score > -0.6:
        return {'phase': 'waning', 'label': '조금씩 어두워지고 있어요', 'icon': '🌒'}
    else:
        return {'phase': 'new_moon', 'label': '가설이 힘을 잃고 있어요', 'icon': '🌑'}
