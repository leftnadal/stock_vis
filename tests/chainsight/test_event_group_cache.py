"""
ON 보드 어댑터 캐시 테스트 (Slice D).

검증:
- get_kept_event_groups(전체)는 캐시 → 2번째 호출은 DB 변경을 안 봄(캐시 히트).
- invalidate_kept_cache() 후엔 재조회(신선).
- as_of_date 지정 시 미캐시(항상 신선).
- OFF 경로(_board_from_theme_tags)는 어댑터를 안 타므로 캐시 무관(IDENTICAL).
"""

import pytest
from django.core.cache import cache

from apps.chain_sight.models.event_group import EventGroup
from apps.chain_sight.services import event_group_reader as reader
from packages.shared.stocks.models import Stock


def _eg(slug, hidden=False):
    Stock.objects.get_or_create(symbol=f"S_{slug}", defaults={"stock_name": slug})
    eg = EventGroup.objects.create(
        name=slug, slug=slug, source="news_jaccard", confidence=0.5, cohesion=0.5,
        member_count=1, core_count=1, is_hidden=hidden,
    )
    eg.memberships.create(symbol_id=f"S_{slug}", role="core")
    return eg


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestKeptCache:
    def test_second_call_hits_cache(self):
        _eg("g1")
        first = reader.get_kept_event_groups()
        assert len(first) == 1
        # DB에 그룹 추가했지만 캐시 히트라 안 보임
        _eg("g2")
        second = reader.get_kept_event_groups()
        assert len(second) == 1  # 캐시 히트(g2 미반영)

    def test_invalidate_refreshes(self):
        _eg("g1")
        reader.get_kept_event_groups()  # 캐시 적재
        _eg("g2")
        reader.invalidate_kept_cache()
        after = reader.get_kept_event_groups()
        assert len(after) == 2  # 무효화 후 재조회(g2 반영)

    def test_as_of_date_not_cached(self):
        from datetime import date
        eg = _eg("g1")
        eg.as_of_date = date(2026, 6, 26)
        eg.save(update_fields=["as_of_date"])
        # as_of 지정 → 캐시 우회(매번 신선)
        r1 = reader.get_kept_event_groups(as_of_date=date(2026, 6, 26))
        assert len(r1) == 1
        _eg("g2")
        EventGroup.objects.filter(slug="g2").update(as_of_date=date(2026, 6, 26))
        r2 = reader.get_kept_event_groups(as_of_date=date(2026, 6, 26))
        assert len(r2) == 2  # 미캐시 → 즉시 반영

    def test_gated_still_excluded_through_cache(self):
        _eg("kept1")
        _eg("gated1", hidden=True)
        r = reader.get_kept_event_groups()
        slugs = {g["slug"] for g in r}
        assert slugs == {"kept1"}  # 캐시돼도 gated 미노출
