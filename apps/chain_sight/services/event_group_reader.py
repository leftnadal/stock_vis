"""
EventGroup 리더 어댑터 (M2 v1.1 reader 전환 — Slice A).

소비자(이벤트 보드 등)가 부를 **단일 정식 인터페이스**. theme_tags 경로는 건드리지
않는다(additive). 플래그 ON 배선·beat·캐시는 후속 세션 — 이 모듈은 어댑터만.

게이팅 중앙집중:
    이 어댑터는 **kept(is_hidden=False) 그룹만** 반환한다. 게이팅(코어 cohesion<0.2
    또는 산출불가)은 적재 시 EventGroup.is_hidden으로 표식되며, 여기서 한 번 필터한다.
    소비자는 kept만 받으므로 중복 필터가 필요 없다.

경계(BOUNDARY-2):
    chain_sight → stocks 방향만 읽는다. shared는 이 모듈을 import하지 않는다.

스코어 비관여:
    attention/leadership 점수 계산·조인은 어댑터 책임이 아니다. 어댑터는 그룹 메타와
    멤버십(symbol·role)만 제공하고, 점수 집계는 소비자가 멤버십으로 수행한다.
    (leadership은 theme-상대 LOO 지표라 EventGroup 재배선은 별도 후속 세션.)
"""

from datetime import date

from apps.chain_sight.models.event_group import EventGroup

# 멤버 정렬: 코어 먼저, 그 안에서 edge_confidence 내림차순.
_ROLE_ORDER = {"core": 0, "satellite": 1}


def _member_dto(m) -> dict:
    return {
        "symbol": m.symbol_id,
        "role": m.role,
        "edge_confidence": m.edge_confidence,
        "anchor_symbol": m.anchor_symbol,
        "cohold_institutions": m.cohold_institutions,
    }


def _group_dto(eg: EventGroup) -> dict:
    members = sorted(
        eg.memberships.all(),
        key=lambda m: (_ROLE_ORDER.get(m.role, 9), -m.edge_confidence, m.symbol_id),
    )
    return {
        "slug": eg.slug,
        "name": eg.name,  # n3 이름(적재 시 auto_name=name_candidates["n3"])
        "cohesion": eg.cohesion,
        "source": eg.source,
        "confidence": eg.confidence,
        "window_days": eg.window_days,
        "as_of_date": eg.as_of_date.isoformat() if eg.as_of_date else None,
        "core_count": eg.core_count,
        "member_count": eg.member_count,
        "name_candidates": eg.name_candidates,
        "members": [_member_dto(m) for m in members],
    }


def get_kept_event_groups(as_of_date: date | None = None) -> list[dict]:
    """
    kept(is_hidden=False) EventGroup 목록을 cohesion 내림차순으로 반환.

    Args:
        as_of_date: 지정 시 해당 as_of_date 그룹만. None이면 전체 kept.

    Returns:
        list[dict] — 각 그룹: slug·name(n3)·cohesion·core/member count·members.
        정렬은 cohesion 내림차순(None 마지막). 점수(avg_score) 기준 재정렬은
        소비자 몫(어댑터는 점수를 모른다).
    """
    qs = EventGroup.objects.filter(is_hidden=False).prefetch_related("memberships")
    if as_of_date is not None:
        qs = qs.filter(as_of_date=as_of_date)
    groups = list(qs)
    # cohesion 내림차순(None은 kept에 없어야 정상이나 방어적으로 마지막).
    groups.sort(key=lambda eg: (eg.cohesion is None, -(eg.cohesion or 0.0), eg.slug))
    return [_group_dto(eg) for eg in groups]


def get_event_group(slug: str) -> dict | None:
    """
    slug로 단일 kept 그룹 조회. gated(is_hidden=True)거나 부재면 None.

    게이팅은 어댑터가 책임지므로, 소비자는 gated 그룹에 접근할 수 없다.
    """
    eg = (
        EventGroup.objects.filter(slug=slug, is_hidden=False)
        .prefetch_related("memberships")
        .first()
    )
    return _group_dto(eg) if eg else None
