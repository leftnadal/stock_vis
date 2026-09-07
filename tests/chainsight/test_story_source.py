"""CS-S3-1 — StorySourceService(A-1 기사 재조회·A-3 8-K 제목·A-4 결정론 슬러그) 단위.

인용 계약: 제목은 근거 기사 원문 또는 8-K 템플릿(공시 사실)만. LLM 0. 기사 0건이면 [].
마이그 0·prod write 0(읽기 조회).
"""

import datetime

import pytest

from apps.chain_sight.services.story_source import (
    EIGHT_K_ITEM_LABELS,
    articles_for_pair,
    eight_k_title,
    story_key,
    story_slug,
)

DAY = datetime.date(2026, 8, 21)


def _article(url, title, published, symbols):
    from services.news.models import NewsArticle, NewsEntity

    art = NewsArticle.objects.create(
        url=url, url_hash=url[-40:], title=title, source="test",
        published_at=published,
    )
    for s in symbols:
        NewsEntity.objects.create(
            news=art, symbol=s, entity_name=s, entity_type="equity",
        )
    return art


def _chain_event(symbol, co_syms, title, published, url="", source_id=None):
    from apps.chain_sight.models.news_event import ChainNewsEvent
    from packages.shared.stocks.models import Stock

    Stock.objects.get_or_create(symbol=symbol, defaults={"stock_name": symbol})
    return ChainNewsEvent.objects.create(
        symbol_id=symbol, source="marketaux",
        source_id=source_id or f"cne-{symbol}-{title[:10]}",
        title=title, url=url, published_at=published,
        co_mentioned_symbols=list(co_syms),
    )


# ── A-3 8-K 제목 ──────────────────────────────────────────────
class TestEightKTitle:
    def test_known_item_101(self):
        assert eight_k_title("MRVL", "GOOGL", "1.01") == "MRVL, GOOGL와 중요 계약 체결 공시"

    def test_known_item_201(self):
        assert eight_k_title("A", "B", "2.01") == "A, B와 자산 인수·처분 완료 공시"

    def test_unknown_item_fallback_no_double_gongsi(self):
        # 미매핑 item → "8-K 공시 (item X.XX)" 형태(공시 중복 없음).
        t = eight_k_title("A", "B", "5.02")
        assert t == "A, B와 8-K 공시 (item 5.02)"

    def test_mapping_has_only_two_known(self):
        assert set(EIGHT_K_ITEM_LABELS) == {"1.01", "2.01"}


# ── A-4 결정론 슬러그 ─────────────────────────────────────────
class TestStorySlug:
    def test_deterministic_same_input(self):
        a = story_slug("daily_spike", ["PANW", "ORCL", "TJX"], "2026-08-21")
        b = story_slug("daily_spike", ["TJX", "ORCL", "PANW"], "2026-08-21")  # 순서 무관
        assert a == b

    def test_slug_length_10_hex(self):
        s = story_slug("daily_spike", ["A", "B"], "2026-08-21")
        assert len(s) == 10
        int(s, 16)  # hex 파싱 가능

    def test_different_input_different_slug(self):
        a = story_slug("daily_spike", ["A", "B"], "2026-08-21")
        b = story_slug("daily_spike", ["A", "B"], "2026-08-22")
        c = story_slug("new_sec", ["A", "B"], "2026-08-21")
        assert a != b and a != c

    def test_story_key_human_readable(self):
        assert story_key("daily_spike", ["ORCL", "PANW"], "2026-08-21") == (
            "daily_spike:ORCL-PANW:2026-08-21"
        )


# ── A-1 기사 재조회 ───────────────────────────────────────────
@pytest.mark.django_db
class TestArticlesForPair:
    def test_chainnews_event_priority(self):
        # ChainNewsEvent 직결 제목이 우선(NewsEntity보다).
        pub = datetime.datetime(2026, 8, 21, 13, 0, tzinfo=datetime.timezone.utc)
        _chain_event("ORCL", ["PANW"], "Oracle-Palo Alto 제휴 발표", pub)
        rows = articles_for_pair("ORCL", "PANW", DAY)
        assert len(rows) >= 1
        assert rows[0]["title"] == "Oracle-Palo Alto 제휴 발표"
        assert "PANW" in rows[0]["symbols_covered"] and "ORCL" in rows[0]["symbols_covered"]

    def test_newsentity_intersection_fallback(self):
        # CNE 없음 → NewsEntity 교집합(두 종목 모두 언급된 기사)로 폴백.
        pub = datetime.datetime(2026, 8, 21, 9, 0, tzinfo=datetime.timezone.utc)
        _article("http://x/1", "두 회사 동반 기사", pub, ["ORCL", "PANW"])
        _article("http://x/2", "한 회사만", pub, ["ORCL"])  # 교집합 아님
        rows = articles_for_pair("ORCL", "PANW", DAY)
        titles = [r["title"] for r in rows]
        assert "두 회사 동반 기사" in titles
        assert "한 회사만" not in titles

    def test_no_articles_returns_empty_not_error(self):
        rows = articles_for_pair("ZZZ", "YYY", DAY)
        assert rows == []

    def test_sorted_by_symbols_covered_then_recent(self):
        # 더 많은 종목을 커버한 기사가 우선, 그다음 최신.
        early = datetime.datetime(2026, 8, 21, 8, 0, tzinfo=datetime.timezone.utc)
        late = datetime.datetime(2026, 8, 21, 20, 0, tzinfo=datetime.timezone.utc)
        _article("http://x/a", "2종목", early, ["ORCL", "PANW"])
        _article("http://x/b", "3종목", late, ["ORCL", "PANW", "TJX"])
        rows = articles_for_pair("ORCL", "PANW", DAY)
        assert rows[0]["title"] == "3종목"  # 커버 많음 우선

    def test_limit_respected(self):
        pub = datetime.datetime(2026, 8, 21, 9, 0, tzinfo=datetime.timezone.utc)
        for i in range(8):
            _article(f"http://x/{i}", f"기사{i}", pub, ["ORCL", "PANW"])
        rows = articles_for_pair("ORCL", "PANW", DAY, limit=3)
        assert len(rows) == 3
