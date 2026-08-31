"""MIG-BUNDLE-1 C-5 — co-mention 활동 캐시(SymbolStoryActivity) 회귀.

물질화 정확성(IDENTICAL: 캐시-서빙 == 라이브), fallback(부재·stale), 전역 조회,
카드 API 무회귀. 소스=story_activity 서비스 재사용(중복 구현 없음).
"""

import datetime

import pytest
from django.test import Client

from apps.chain_sight.models import CoMentionEdge, SymbolStoryActivity
from apps.chain_sight.services.story_activity import (
    _compute_story_threads_live,
    get_global_activity_top,
    get_symbol_story_threads,
)
from apps.chain_sight.tasks.story_activity_tasks import materialize_story_activity
from services.news.models import NewsArticle, NewsEntity

NOW = datetime.datetime(2026, 8, 28, 12, 0, tzinfo=datetime.timezone.utc)


def _edge(a, b, count90, last_days_ago):
    CoMentionEdge.objects.create(
        symbol_a=a, symbol_b=b, co_mention_count=count90,
        last_co_mention_date=(NOW.date() - datetime.timedelta(days=last_days_ago)),
        first_co_mention_date=NOW.date() - datetime.timedelta(days=89),
    )


_seq = [0]


def _article(symbols, days_ago):
    _seq[0] += 1
    art = NewsArticle.objects.create(
        url=f"http://c/{_seq[0]}", url_hash=f"ch{_seq[0]}", title="t", source="av",
        published_at=NOW - datetime.timedelta(days=days_ago),
    )
    for s in symbols:
        NewsEntity.objects.create(
            news=art, symbol=s, entity_name=s, entity_type="equity", source="av"
        )
    return art


@pytest.mark.django_db
class TestStoryActivityCache:
    def _seed(self):
        _edge("AAA", "BBB", 90, last_days_ago=1)
        for d in (1, 3, 6):
            _article(["AAA", "BBB"], days_ago=d)
        _edge("AAA", "CCC", 13, last_days_ago=40)

    def test_materialize_creates_rows(self):
        self._seed()
        r = materialize_story_activity(now=NOW)
        assert r["symbols"] >= 1
        # AAA·BBB·CCC 전부 대상(양방향 등장)
        assert SymbolStoryActivity.objects.filter(symbol="AAA").count() == 2
        row = SymbolStoryActivity.objects.get(symbol="AAA", partner="BBB")
        assert row.count_7d == 3
        assert row.count_90d == 90
        assert row.thread_total == 2
        assert row.materialized_at == NOW

    def test_cache_served_identical_to_live(self):
        # IDENTICAL 원칙(C-5): 물질화 후 캐시-서빙 결과 == 라이브 계산 결과.
        self._seed()
        materialize_story_activity(now=NOW)
        cached = get_symbol_story_threads("AAA", now=NOW, use_cache=True)
        live = _compute_story_threads_live("AAA", now=NOW)
        assert cached == live

    def test_cache_is_served_not_recomputed(self):
        # 캐시 신선 시 라이브 재계산 없이 캐시값 반환 — 물질화 후 소스 변해도 캐시값 유지.
        self._seed()
        materialize_story_activity(now=NOW)
        # 물질화 후 7일 내 기사 추가(라이브라면 count_7d 증가)
        _article(["AAA", "BBB"], days_ago=2)
        out = get_symbol_story_threads("AAA", now=NOW, use_cache=True)
        bbb = next(t for t in out["threads"] if t["partner"] == "BBB")
        assert bbb["count_7d"] == 3  # 캐시값(3) — 새 기사(→4) 미반영 = 캐시 서빙 증거

    def test_fallback_when_no_cache(self):
        # 캐시 부재 → 라이브 fallback(빈 화면 금지).
        self._seed()
        assert SymbolStoryActivity.objects.count() == 0
        out = get_symbol_story_threads("AAA", now=NOW, use_cache=True)
        assert out["thread_total"] == 2
        assert any(t["partner"] == "BBB" for t in out["threads"])

    def test_fallback_when_stale(self):
        # 캐시 stale(materialized_at 오래됨) → 라이브 fallback → 변경된 소스 반영.
        self._seed()
        stale_now = NOW - datetime.timedelta(days=3)  # CACHE_STALE_HOURS(48h) 초과
        materialize_story_activity(now=stale_now)
        # stale 이후 기사 추가 → 라이브면 count_7d=4
        _article(["AAA", "BBB"], days_ago=2)
        out = get_symbol_story_threads("AAA", now=NOW, use_cache=True)
        bbb = next(t for t in out["threads"] if t["partner"] == "BBB")
        assert bbb["count_7d"] == 4  # 라이브 재계산(추가분 반영) = fallback 증거

    def test_use_cache_false_forces_live(self):
        self._seed()
        materialize_story_activity(now=NOW)
        _article(["AAA", "BBB"], days_ago=2)  # 캐시엔 없는 신규
        out = get_symbol_story_threads("AAA", now=NOW, use_cache=False)
        bbb = next(t for t in out["threads"] if t["partner"] == "BBB")
        assert bbb["count_7d"] == 4  # 라이브 강제 → 신규 반영

    def test_global_activity_top_ordered_by_ratio(self):
        # 전역 활동 상위(S2 예비) — activity_ratio 내림차순.
        _edge("AAA", "HIGH", 7, last_days_ago=1)   # weekly_avg≈0.54
        for _ in range(3):
            _article(["AAA", "HIGH"], days_ago=2)  # 7d=3 → ratio≈5.56
        _edge("AAA", "LOW", 90, last_days_ago=1)   # weekly_avg=7.0
        _article(["AAA", "LOW"], days_ago=2)        # 7d=1 → ratio≈0.14
        materialize_story_activity(now=NOW)
        top = get_global_activity_top(limit=10)
        partners = [r["partner"] for r in top]
        assert partners.index("HIGH") < partners.index("LOW")  # ratio 내림차순

    def test_card_api_regression_after_materialize(self):
        # 물질화가 존재해도 카드 API 무회귀(캐시/라이브 어느 경로든 동일 형상).
        # 카드 뷰는 now 미주입 → 실제 now 기준 신선도로 경로가 갈릴 수 있으나,
        # thread_total·파트너 멤버십은 7일 창과 무관해 두 경로 모두 성립.
        self._seed()
        materialize_story_activity(now=NOW)
        d = Client().get("/api/v1/chainsight/mindmap/card/AAA/").json()
        assert "story" in d
        assert d["story"]["thread_total"] == 2
        partners = {t["partner"] for t in d["story"]["threads"]}
        assert "BBB" in partners
