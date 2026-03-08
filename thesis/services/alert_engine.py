"""Alert Engine + Throttling (수학 모델 v2.3.2, Section 6 + 12.4)"""

import logging
from datetime import timedelta

from django.utils import timezone

from thesis.models import ThesisAlert
from thesis.services.data_validator import check_stale_indicators

logger = logging.getLogger(__name__)

COOLDOWN_HOURS = {
    'direction_flip': 24,
    'sharp_move': 24,
    'extreme_volatility': 6,
    'weakest_link': 24,
    'premise_divergence': 24,
    'stale_data': 9999,
    'indicator_overlap': 9999,
    'indicator_bias': 9999,
    'state_change': 24,
    'milestone': 9999,
    'needs_review': 720,  # 30일
}

USER_VISIBLE_ALERTS = {
    'push_email': [
        'extreme_volatility', 'direction_flip', 'sharp_move',
        'weakest_link', 'critical', 'expired', 'needs_review',
    ],
    'feed_only': [
        'state_change', 'milestone', 'indicator_overlap',
        'indicator_bias', 'premise_divergence', 'stale_data',
    ],
}

SEVERITY_MAP = {
    'extreme_volatility': 'critical',
    'direction_flip': 'high',
    'sharp_move': 'high',
    'weakest_link': 'medium',
    'premise_divergence': 'medium',
    'stale_data': 'low',
    'indicator_overlap': 'low',
    'indicator_bias': 'low',
    'state_change': 'low',
    'milestone': 'low',
    'needs_review': 'low',
}

# 방향 전환/sharp_move 기준
SHARP_MOVE_THRESHOLD = 0.4


def should_send_alert(thesis, alert_type, target_id, cooldown_hours):
    """ThesisAlert에서 cooldown 체크. cooldown 내 동일 알림 존재하면 False."""
    cutoff = timezone.now() - timedelta(hours=cooldown_hours)
    exists = ThesisAlert.objects.filter(
        thesis=thesis,
        alert_type=alert_type,
        target_id=target_id,
        created_at__gte=cutoff,
    ).exists()
    return not exists


def create_alert_if_needed(thesis, alert_type, title, message,
                           indicator=None, target_id=''):
    """throttling 통과 시에만 ThesisAlert 생성. 반환: 생성된 alert or None."""
    cooldown = COOLDOWN_HOURS.get(alert_type, 24)
    severity = SEVERITY_MAP.get(alert_type, 'low')

    if not should_send_alert(thesis, alert_type, target_id, cooldown):
        return None

    is_pushed = alert_type in USER_VISIBLE_ALERTS.get('push_email', [])

    alert = ThesisAlert.objects.create(
        thesis=thesis,
        indicator=indicator,
        alert_type=alert_type,
        severity=severity,
        target_id=target_id,
        cooldown_hours=cooldown,
        title=title,
        message=message,
        is_pushed=is_pushed,
    )

    logger.info(f"[Alert] {thesis.id} {alert_type}: {title}")
    return alert


def check_and_create_alerts(thesis, scoring_result, prev_snapshot=None):
    """
    scoring_result로부터 발생할 알림 전체 처리.

    Args:
        thesis: Thesis 인스턴스
        scoring_result: dict from snapshot_builder (indicator_scores, overall_score, etc.)
        prev_snapshot: 이전 ThesisSnapshot (없으면 None)

    Returns:
        list[ThesisAlert] - 생성된 알림 목록
    """
    alerts = []

    # 1. extreme_volatility
    for ev in scoring_result.get('extreme_vol_indicators', []):
        alert = create_alert_if_needed(
            thesis=thesis,
            alert_type='extreme_volatility',
            title=f'{ev["indicator_name"]} 극단적 변동',
            message=ev['message'],
            target_id=ev.get('indicator_id', ''),
        )
        if alert:
            alerts.append(alert)

    # 2. direction_flip: 이전 스냅샷 대비 degree 방향 전환
    if prev_snapshot:
        prev_degrees = prev_snapshot.indicator_degrees or {}
        curr_scores = scoring_result.get('indicator_scores', {})

        for ind_id, curr_score in curr_scores.items():
            if curr_score is None:
                continue
            prev_degree = prev_degrees.get(ind_id)
            if prev_degree is None:
                continue

            # 이전: degree < 90 (지지) -> 현재: score < 0 (반박), 또는 반대
            prev_supporting = prev_degree < 90
            curr_supporting = curr_score > 0

            if prev_supporting != curr_supporting:
                ind_name = scoring_result.get('indicator_names', {}).get(ind_id, ind_id)
                alert = create_alert_if_needed(
                    thesis=thesis,
                    alert_type='direction_flip',
                    title=f'{ind_name} 방향 전환',
                    message=f'{ind_name}이(가) {"지지 -> 반박" if prev_supporting else "반박 -> 지지"}으로 전환했어요.',
                    target_id=ind_id,
                )
                if alert:
                    alerts.append(alert)

    # 3. sharp_move: |score 변화| >= 0.4
    if prev_snapshot:
        prev_scores = prev_snapshot.universe_snapshot or {}
        curr_scores = scoring_result.get('indicator_scores', {})

        for ind_id, curr_score in curr_scores.items():
            if curr_score is None:
                continue
            prev_score = prev_scores.get(ind_id)
            if prev_score is None:
                continue
            if abs(curr_score - prev_score) >= SHARP_MOVE_THRESHOLD:
                ind_name = scoring_result.get('indicator_names', {}).get(ind_id, ind_id)
                delta = curr_score - prev_score
                direction = '상승' if delta > 0 else '하락'
                alert = create_alert_if_needed(
                    thesis=thesis,
                    alert_type='sharp_move',
                    title=f'{ind_name} 급격한 변화',
                    message=f'{ind_name} 점수가 {abs(delta):.2f} {direction}했어요.',
                    target_id=ind_id,
                )
                if alert:
                    alerts.append(alert)

    # 4. weakest_link
    wl = scoring_result.get('weakest_link')
    if wl:
        alert = create_alert_if_needed(
            thesis=thesis,
            alert_type='weakest_link',
            title='최약고리 감지',
            message=f'"{wl.get("premise_content", wl.get("indicator_name", ""))}"이(가) 강하게 반박되고 있어요.',
            target_id=wl.get('premise_id', wl.get('indicator_id', '')),
        )
        if alert:
            alerts.append(alert)

    # 5. premise_divergence
    if scoring_result.get('divergence_count', 0) > 0:
        alert = create_alert_if_needed(
            thesis=thesis,
            alert_type='premise_divergence',
            title='전제 간 불일치',
            message='전제들이 서로 다른 방향을 가리키고 있어요.',
        )
        if alert:
            alerts.append(alert)

    # 6. stale_data
    stale_indicators = check_stale_indicators(thesis)
    for ind in stale_indicators:
        alert = create_alert_if_needed(
            thesis=thesis,
            alert_type='stale_data',
            title=f'{ind.name} 데이터 미갱신',
            message=f'"{ind.name}" 데이터가 72시간째 업데이트되지 않았어요.',
            indicator=ind,
            target_id=str(ind.id),
        )
        if alert:
            alerts.append(alert)

    # 7. indicator_overlap / indicator_bias
    thesis_bias = scoring_result.get('thesis_bias_warning')
    if thesis_bias:
        alert = create_alert_if_needed(
            thesis=thesis,
            alert_type='indicator_bias',
            title='지표 편향 감지',
            message=thesis_bias['message'],
        )
        if alert:
            alerts.append(alert)

    # 8. state_change
    state_result = scoring_result.get('state_result')
    if state_result and state_result.get('state_changed'):
        new_state = state_result['state']
        alert = create_alert_if_needed(
            thesis=thesis,
            alert_type='state_change',
            title=f'상태 변경: {new_state}',
            message=f'가설 상태가 "{new_state}"(으)로 변경되었어요.',
        )
        if alert:
            alerts.append(alert)

    # 9. needs_review
    if state_result and state_result.get('reminder_needed'):
        alert = create_alert_if_needed(
            thesis=thesis,
            alert_type='needs_review',
            title='가설 점검 필요',
            message='이 가설을 세운 지 90일이 지났어요. 아직 지켜보시나요?',
        )
        if alert:
            alerts.append(alert)

    # 10. milestone: overall +-0.5 첫 돌파
    overall = scoring_result.get('overall_score', 0.0)
    if abs(overall) >= 0.5:
        direction = '지지' if overall > 0 else '반박'
        alert = create_alert_if_needed(
            thesis=thesis,
            alert_type='milestone',
            title=f'마일스톤: 강한 {direction}',
            message=f'가설 점수가 {overall:.2f}로, 강한 {direction} 영역에 진입했어요.',
        )
        if alert:
            alerts.append(alert)

    return alerts
