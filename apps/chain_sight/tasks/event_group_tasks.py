"""
코어-위성 EventGroup 적재 태스크 (M2 v1.1).

- compute_event_groups_shadow: Phase 1 쉐도우 적재(수동 트리거).
- compute_event_group_leadership_daily: 보드 ON 신선도 — 그룹 재적재 + C leadership.
  beat 등록은 `python manage.py register_chainsight_beats`(22:15 UTC, prod 수동).
"""

import logging

from celery import shared_task
from django.db.models import Max

from apps.chain_sight.services.event_group_pipeline import load_event_groups
from apps.chain_sight.services.leadership_eventgroup import (
    compute_eventgroup_leadership_scores,
)
from packages.shared.stocks.models import DailyPrice

logger = logging.getLogger(__name__)


@shared_task(
    name="chainsight-event-groups-shadow",
    max_retries=2,
    default_retry_delay=120,
    soft_time_limit=900,
)
def compute_event_groups_shadow():
    """
    jaccard 코어-위성 그룹 계산 → EventGroup/GroupMembership 쉐도우 적재(멱등 덮어쓰기).

    기존 theme_tags 소비자 무영향(새 테이블만 씀).

    Returns:
        dict: groups/hidden/total_members/as_of.
    """
    summary = load_event_groups()
    logger.info("compute_event_groups_shadow: %s", summary)
    return summary


@shared_task(
    name="chainsight-event-group-leadership-daily",
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=1200,
)
def compute_event_group_leadership_daily():
    """
    보드 ON 신선도: EventGroup 그룹 재적재 → C leadership 재컴퓨트(최신 가격일).

    순서: 그룹 먼저(load_event_groups, 멱등 덮어쓰기) → 그 위에 C 점수
    (compute_eventgroup_leadership_scores, theme='eg:{slug}' 멱등 upsert). attention/
    leadership(22:30/22:40)보다 앞서(22:15) 돌아 보드가 읽기 전 그룹·점수가 최신.

    옛 theme_tags 경로/행 무영향(eg: 키 분리). leadership 점수 로직 불변(읽는 게 아니라
    이미 검증된 compute 호출 — 수식 재발명 아님).

    Returns:
        dict: groups(적재 요약)/leadership_rows/as_of.
    """
    group_summary = load_event_groups()
    as_of = DailyPrice.objects.aggregate(m=Max("date"))["m"]
    if as_of is None:
        logger.warning("compute_event_group_leadership_daily: DailyPrice 없음")
        return {"groups": group_summary, "leadership_rows": 0, "as_of": None}
    rows = compute_eventgroup_leadership_scores(as_of)
    summary = {"groups": group_summary, "leadership_rows": rows, "as_of": str(as_of)}
    logger.info("compute_event_group_leadership_daily: %s", summary)
    return summary
