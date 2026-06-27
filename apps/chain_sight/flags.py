"""
Chain Sight 피처 플래그 (M2 v1.1 reader 전환 — 보드 그룹 소스).

단일 토글 `CHAINSIGHT_GROUP_SOURCE`(settings, .env 주입)로 이벤트 보드가 읽는
그룹 소스를 전환한다. 기본 OFF = 레거시 theme_tags(오늘과 IDENTICAL).

repo에 기존 플래그 패턴 부재 → settings getattr 토글 최소안(신규 메커니즘 발명 아님).
"""

from django.conf import settings

GROUP_SOURCE_THEME_TAGS = "theme_tags"  # OFF (기본)
GROUP_SOURCE_EVENT_GROUP = "event_group"  # ON (go-live)


def group_source() -> str:
    """현재 그룹 소스. 기본 'theme_tags'(OFF)."""
    return getattr(settings, "CHAINSIGHT_GROUP_SOURCE", GROUP_SOURCE_THEME_TAGS)


def use_event_group_board() -> bool:
    """ON이면 True — 보드가 EventGroup(kept/n3) + eg leadership을 읽는다."""
    return group_source() == GROUP_SOURCE_EVENT_GROUP
