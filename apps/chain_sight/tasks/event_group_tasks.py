"""
코어-위성 EventGroup 적재 태스크 (M2 v1.1 Phase 1).

⚠️ Phase 1 = 쉐도우 적재. Celery Beat **미등록**(수동 트리거 전용).
   자동 스케줄 등록은 reader 전환 세션에서 (라이브 화면 영향 게이트 통과 후).
   수동 실행: `compute_event_groups_shadow.delay()` 또는 manage 명령.
"""

import logging

from celery import shared_task

from apps.chain_sight.services.event_group_pipeline import load_event_groups

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
