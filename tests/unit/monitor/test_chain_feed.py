"""관계망 이벤트 피드 단위 테스트 (EVT-CHAIN-1 STEP 1).

이웃 필터(임계·상태) / top-k 컷 / a·b 정규화 / 창 경계(시드 이벤트 유·무) /
after_count / 이웃 0 → neighbors [] / 부호 중립(DTO 키) / 캐시.
et_today = timezone.now() 이므로 이벤트는 오늘 상대 오프셋으로 생성(결정성).
"""
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.chain_sight.models.relation_discovery import RelationConfidence
from apps.monitor.services.chain_feed import CHAIN_PARAMS, _ET, build_chain_feed
from packages.shared.stocks.models import CalendarEvent

User = get_user_model()


def _today():
    return timezone.now().astimezone(_ET).date()


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="chain_u1", password="pw12345")


def _rel(a, b, *, truth, status="confirmed", rtype="SUPPLIES_TO"):
    return RelationConfidence.objects.create(
        symbol_a=a, symbol_b=b, relation_type=rtype,
        relation_status=status, truth_score=truth,
    )


def _earn(sym, d, *, est=None, status=CalendarEvent.Status.SCHEDULED, doc=1,
          etype=CalendarEvent.EventType.EARNINGS):
    return CalendarEvent.objects.create(
        event_type=etype, symbol=sym, event_date=d,
        status=status, eps_estimated=est, date_observed_count=doc,
    )


# ────────────────────────── 이웃 필터 ──────────────────────────
class TestNeighborFilter:
    def test_threshold_and_status_filter(self, user):
        seed = "IREN"
        _rel(seed, "PASSA", truth=0.90, status="confirmed")   # 통과
        _rel(seed, "EDGE", truth=0.85, status="confirmed")    # 경계 통과(≥0.85)
        _rel(seed, "LOWTR", truth=0.84, status="confirmed")   # 임계 미달 탈락
        _rel(seed, "PROB", truth=0.99, status="probable")     # 상태 미달 탈락
        _rel(seed, "STALE", truth=0.99, status="stale")       # 상태 미달 탈락
        feed = build_chain_feed(user, seed)
        syms = {n["symbol"] for n in feed["neighbors"]}
        assert syms == {"PASSA", "EDGE"}

    def test_zero_neighbors_returns_empty_list(self, user):
        seed = "TLN"
        _rel(seed, "X", truth=0.10, status="hidden")  # 필터 전부 탈락
        feed = build_chain_feed(user, seed)
        assert feed["neighbors"] == []
        assert feed["items"] == []
        assert feed["after_count"] == 0

    def test_zero_neighbors_still_returns_seed_events(self, user):
        """이웃 0이어도 시드 자신 이벤트(위젯 pill)는 유지."""
        seed = "TLN"
        _earn(seed, _today() + timedelta(days=20), est="1.0")
        feed = build_chain_feed(user, seed)
        assert feed["neighbors"] == []
        assert len(feed["seed_events"]) == 1
        assert feed["seed_next_event"]["kind"] == "earnings"


# ────────────────────────── top-k · 정규화 ──────────────────────────
class TestTopKAndNormalization:
    def test_top_k_cut(self, user):
        seed = "PLTR"
        # 12개 confirmed 이웃(truth 하강) → top-10만
        for i in range(12):
            _rel(seed, f"N{i:02d}", truth=0.85 + i * 0.001)
        feed = build_chain_feed(user, seed)
        assert len(feed["neighbors"]) == CHAIN_PARAMS["top_k"] == 10
        # 최고 truth 순 → N11이 1위
        assert feed["neighbors"][0]["symbol"] == "N11"

    def test_ab_normalization_opposite_symbol(self, user):
        seed = "IREN"
        _rel(seed, "ASIDE", truth=0.90)          # 시드 = symbol_a → 이웃 = ASIDE
        _rel("BSIDE", seed, truth=0.88)          # 시드 = symbol_b → 이웃 = BSIDE
        feed = build_chain_feed(user, seed)
        syms = {n["symbol"] for n in feed["neighbors"]}
        assert syms == {"ASIDE", "BSIDE"}
        assert seed not in syms  # 자기 자신 등장 금지


# ────────────────────────── 창 경계 · after_count ──────────────────────────
class TestWindowBoundary:
    def test_window_to_seed_next_event_and_after_count(self, user):
        seed = "IREN"
        _rel(seed, "NBR", truth=0.90)
        t = _today()
        # 시드 다음 이벤트 = 오늘+30 (창 상한)
        _earn(seed, t + timedelta(days=30), est="-0.2")
        # 이웃 어닝: 창 내(오늘+10) · 창 이후(오늘+50) · 90일 밖(오늘+120)
        _earn("NBR", t + timedelta(days=10), est="1.0")
        _earn("NBR2", t + timedelta(days=50), est="1.0")  # NBR2는 이웃 아님 → 무시
        _rel(seed, "NBR2", truth=0.90)                    # NBR2도 이웃으로
        _earn("NBR", t + timedelta(days=120), est="1.0")  # after_days 밖 → 카운트 안 됨
        feed = build_chain_feed(user, seed)
        item_dates = [it["event_date_et"] for it in feed["items"]]
        assert (t + timedelta(days=10)).isoformat() in item_dates       # 창 내
        assert (t + timedelta(days=50)).isoformat() not in item_dates   # 창 밖(본문 아님)
        assert feed["seed_next_event"]["event_date_et"] == (t + timedelta(days=30)).isoformat()
        assert feed["after_count"] == 1  # 오늘+50 (오늘+120은 90일 밖)

    def test_no_seed_event_window_is_today_plus_after_days(self, user):
        seed = "IREN"
        _rel(seed, "NBR", truth=0.90)
        t = _today()
        # 시드 이벤트 없음 → 창 = 오늘 + 90
        _earn("NBR", t + timedelta(days=60), est="1.0")   # 창 내
        _earn("NBR", t + timedelta(days=100), est="1.0")  # 90 밖 → after도 아님
        feed = build_chain_feed(user, seed)
        assert feed["seed_next_event"] is None
        item_dates = [it["event_date_et"] for it in feed["items"]]
        assert (t + timedelta(days=60)).isoformat() in item_dates
        assert feed["after_count"] == 0


# ────────────────────────── 부호 중립 ──────────────────────────
class TestSignNeutral:
    _FORBIDDEN = ("direction", "sentiment", "signal", "bull", "bear", "verdict", "positive", "negative")

    def test_no_direction_or_sentiment_keys(self, user):
        seed = "IREN"
        _rel(seed, "NBR", truth=0.90, rtype="SUPPLIES_TO")
        _earn(seed, _today() + timedelta(days=30), est="-0.2")
        _earn("NBR", _today() + timedelta(days=10), est="1.0")
        feed = build_chain_feed(user, seed)
        # neighbors 키 = {symbol, relation_type, truth_score} 정확히
        for n in feed["neighbors"]:
            assert set(n.keys()) == {"symbol", "relation_type", "truth_score"}
        # items relation 키 = {type, truth_score} 정확히
        for it in feed["items"]:
            assert set(it["relation"].keys()) == {"type", "truth_score"}
        # 어디에도 방향/센티먼트 키 부재
        import json
        blob = json.dumps(feed).lower()
        for kw in self._FORBIDDEN:
            assert kw not in blob, f"부호 중립 위반: '{kw}' 존재"


# ────────────────────────── 캐시 ──────────────────────────
class TestCache:
    def test_symbol_keyed_cache(self, user):
        seed = "IREN"
        _rel(seed, "NBR", truth=0.90)
        feed1 = build_chain_feed(user, seed)
        assert len(feed1["neighbors"]) == 1
        # 이웃 추가 후에도 캐시된 결과 반환(15분)
        _rel(seed, "NBR2", truth=0.90)
        feed2 = build_chain_feed(user, seed)
        assert len(feed2["neighbors"]) == 1  # 캐시 히트
        cache.clear()
        feed3 = build_chain_feed(user, seed)
        assert len(feed3["neighbors"]) == 2  # 캐시 미스 → 신규 반영

    def test_empty_symbol_returns_empty(self, user):
        feed = build_chain_feed(user, "")
        assert feed["seed"] == ""
        assert feed["neighbors"] == []
