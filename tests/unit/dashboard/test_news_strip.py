"""NEWSAXIS-BUILD Slice 1 — 뉴스 스트립 BFF 테스트 (fixture 기반, 외부 호출 0). [D-NEWSAXIS-CONTRACT]

검증: 티어 쿼터·공석 충원·접기 3조건(같은 종목 다른 사건 비접합 필수)·θ 분위·
배지 우대·계약 shape·빈 데이터 200.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.chain_sight.models.relation_discovery import RelationConfidence
from apps.dashboard.services import strip_service
from packages.shared.stocks.models import IssuanceLog, Stock
from packages.shared.users.models import Watchlist, WatchlistItem
from services.news.models import NewsArticle, NewsEntity

User = get_user_model()

ITEM_KEYS = {
    "headline", "symbols", "direction", "tier", "relevance_line",
    "collapsed_count", "badge", "published_at", "article_url",
}


def _article(url, title, symbols, *, hours_ago=1, sentiment=0.0, importance=0.0):
    art = NewsArticle.objects.create(
        url=url,
        title=title,
        source="test",
        published_at=timezone.now() - timezone.timedelta(hours=hours_ago),
        sentiment_score=Decimal(str(sentiment)),
        importance_score=importance,
    )
    for s in symbols:
        NewsEntity.objects.create(
            news=art, symbol=s, entity_name=s, entity_type="ticker",
            match_score=Decimal("1.00000"),
        )
    return art


def _user(name="u1"):
    return User.objects.create_user(username=name, password="x")


def _watch(user, symbols):
    wl = Watchlist.objects.create(user=user, name="w")
    for s in symbols:
        Stock.objects.get_or_create(symbol=s)
        WatchlistItem.objects.create(watchlist=wl, stock_id=s)
    return wl


# ── 계약 shape + 빈 데이터 ────────────────────────────────────────────


@pytest.mark.django_db
def test_empty_news_returns_empty_items():
    user = _user()
    out = strip_service._assemble(user)
    assert out["items"] == []
    assert "as_of" in out and "theta" in out


@pytest.mark.django_db
def test_contract_item_shape():
    user = _user()
    _watch(user, ["AAA"])
    _article("http://n/1", "AAA 실적 서프라이즈", ["AAA"], sentiment=0.5)
    out = strip_service._assemble(user)
    assert len(out["items"]) == 1
    item = out["items"][0]
    assert set(item.keys()) == ITEM_KEYS
    assert item["symbols"] == ["AAA"]
    assert item["direction"] == "up"
    assert item["tier"] == 3
    assert item["collapsed_count"] == 0
    assert item["article_url"] == "http://n/1"


# ── 티어 쿼터 + 공석 충원 ──────────────────────────────────────────────


@pytest.mark.django_db
def test_tier_quota_max_two_per_tier():
    user = _user()
    _watch(user, ["AAA"])  # T3
    # T3 후보 4건(서로 다른 사건: 제목 핵심어 상이) → 쿼터 2만
    for i in range(4):
        _article(f"http://n/t3-{i}", f"AAA 뉴스{i} 이벤트{i}", ["AAA"], hours_ago=i + 1)
    out = strip_service._assemble(user)
    t3 = [c for c in out["items"] if c["tier"] == 3]
    assert len(t3) == 2  # 티어당 최대 2


@pytest.mark.django_db
def test_vacancy_backfill_no_t1_when_holdings_empty():
    user = _user()
    _watch(user, ["AAA"])  # T3만, T1 보유는 공석(WalletHolding 0)
    for i in range(3):
        _article(f"http://n/{i}", f"AAA 소식{i} 별건{i}", ["AAA"], hours_ago=i + 1)
    out = strip_service._assemble(user)
    tiers = {c["tier"] for c in out["items"]}
    assert 1 not in tiers  # T1 공석 → 칩 없음
    assert out["items"]  # 하위 티어로 충원됨


# ── 접기 3조건 ────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_collapse_same_event():
    user = _user()
    _watch(user, ["AAA"])
    # 같은 심볼 + 24h 내 + 제목 핵심어 공유("리콜") → 접힘
    _article("http://n/a", "AAA 리콜 사태 발생", ["AAA"], hours_ago=1)
    _article("http://n/b", "AAA 리콜 관련 후속", ["AAA"], hours_ago=2)
    out = strip_service._assemble(user)
    t3 = [c for c in out["items"] if c["tier"] == 3]
    assert len(t3) == 1  # 1건으로 접힘
    assert t3[0]["collapsed_count"] == 1  # +1건


@pytest.mark.django_db
def test_no_collapse_same_symbols_different_event():
    """★안전핀: 같은 종목·다른 사건(제목 핵심어 미공유)은 비접합."""
    user = _user()
    _watch(user, ["AAA"])
    _article("http://n/a", "AAA 리콜 사태", ["AAA"], hours_ago=1)
    _article("http://n/b", "AAA 신제품 출시", ["AAA"], hours_ago=2)
    out = strip_service._assemble(user)
    t3 = [c for c in out["items"] if c["tier"] == 3]
    assert len(t3) == 2  # 안전핀 = 별개 유지
    assert all(c["collapsed_count"] == 0 for c in t3)


@pytest.mark.django_db
def test_no_collapse_outside_24h():
    user = _user()
    _watch(user, ["AAA"])
    _article("http://n/a", "AAA 리콜 사태", ["AAA"], hours_ago=1)
    _article("http://n/b", "AAA 리콜 사태", ["AAA"], hours_ago=30)  # 24h 밖
    out = strip_service._assemble(user)
    t3 = [c for c in out["items"] if c["tier"] == 3]
    assert len(t3) == 2


# ── θ 분위 ────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_theta_is_p85_of_distribution():
    for i, score in enumerate([0, 10, 20, 30, 40, 50, 60, 70, 80, 85]):
        RelationConfidence.objects.create(
            symbol_a=f"S{i}", symbol_b="ZZZ", relation_type="PEER_OF",
            truth_score=score,
        )
    theta = strip_service.compute_confidence_theta()
    # 10개 값의 p85 (percentile_cont 보간) — 76.75
    assert 70 <= theta <= 85


# ── 배지 ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_badge_present_when_edge_connects_to_watched():
    user = _user()
    _watch(user, ["AAA"])  # seed
    _article("http://n/1", "BBB 관련 뉴스", ["BBB"], hours_ago=1, importance=9.0)
    # 분포를 낮게 깔아 θ 낮춤 + 강한 엣지
    RelationConfidence.objects.create(
        symbol_a="BBB", symbol_b="AAA", relation_type="SUPPLIES_TO", truth_score=80,
    )
    for i in range(5):
        RelationConfidence.objects.create(
            symbol_a=f"L{i}", symbol_b="QQQ", relation_type="PEER_OF", truth_score=1,
        )
    out = strip_service._assemble(user)
    chips = [c for c in out["items"] if "BBB" in c["symbols"]]
    assert chips
    badge = chips[0]["badge"]
    assert badge is not None
    assert "AAA" in badge["pair"] and "BBB" in badge["pair"]
    assert badge["confidence"] == 80.0


@pytest.mark.django_db
def test_badge_has_news_source_tiebreak():
    user = _user()
    _watch(user, ["AAA"])
    _article("http://n/1", "BBB CCC 동반 뉴스", ["BBB", "CCC"], hours_ago=1, importance=9.0)
    # 동률 truth=80, has_news_source True인 CCC↔AAA 우대
    RelationConfidence.objects.create(
        symbol_a="BBB", symbol_b="AAA", relation_type="PEER_OF",
        truth_score=80, has_news_source=False,
    )
    RelationConfidence.objects.create(
        symbol_a="CCC", symbol_b="AAA", relation_type="PEER_OF",
        truth_score=80, has_news_source=True,
    )
    out = strip_service._assemble(user)
    chips = [c for c in out["items"] if "BBB" in c["symbols"]]
    assert chips
    assert "CCC" in chips[0]["badge"]["pair"]  # has_news_source 우대


# ── 엔드포인트 인증 ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_endpoint_requires_auth():
    from rest_framework.test import APIClient

    client = APIClient()
    resp = client.get("/api/dashboard/news-strip/")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_endpoint_authed_returns_200_empty():
    from rest_framework.test import APIClient

    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get("/api/dashboard/news-strip/")
    assert resp.status_code == 200
    assert resp.data["items"] == []


# ── STRIP-FOLD-TUNE: 접기 안전핀 강화 (D-STRIP-FOLD-TUNE) ─────────────────


@pytest.mark.django_db
def test_fold_stopword_blocks_generic_only_share():
    """ⓐ 일반어(stock)만 공유하는 상이 사건은 비접합 — stopword 안전핀."""
    a = _article("http://f/1", "AAPL stock climbs", ["AAPL"], hours_ago=1)
    b = _article("http://f/2", "AAPL stock tumbles", ["AAPL"], hours_ago=2)
    groups = strip_service._collapse([a, b])
    assert len(groups) == 2  # 'stock'=stopword → 특이어 미공유 → 비접합(정반대 사건)


@pytest.mark.django_db
def test_genuine_same_event_still_collapses():
    """과소접힘 회귀 방지: 특이어(recall) 공유 = 여전히 접힘."""
    a = _article("http://f/3", "AAPL recall crisis widens", ["AAPL"], hours_ago=1)
    b = _article("http://f/4", "AAPL recall investigation opens", ["AAPL"], hours_ago=2)
    groups = strip_service._collapse([a, b])
    assert len(groups) == 1
    assert groups[0]["collapsed_count"] == 1


@pytest.mark.django_db
def test_roundup_not_absorbed():
    """ⓑ 라운드업(심볼>3)은 흡수 금지 — 독립 대표로 잔류."""
    roundup = _article(
        "http://f/r", "recall crisis roundup", ["AAA", "BBB", "CCC", "DDD", "EEE"],
        hours_ago=1,
    )
    single = _article("http://f/s", "AAA recall crisis", ["AAA"], hours_ago=2)
    groups = strip_service._collapse([roundup, single])
    assert len(groups) == 2  # 라운드업 비흡수(심볼 5 > 상한 3)


@pytest.mark.django_db
def test_group_size_cap_splits_oversized():
    """ⓒ 그룹 상한 = MAX_GROUP_SIZE(rep+2). 초과 동일사건은 분할·독립 잔류."""
    arts = [
        _article(f"http://f/g{i}", "AAPL recall crisis event", ["AAPL"], hours_ago=i + 1)
        for i in range(6)
    ]
    groups = strip_service._collapse(arts)
    assert all(
        g["collapsed_count"] <= strip_service.MAX_GROUP_SIZE - 1 for g in groups
    )
    assert len(groups) >= 2  # 6 동일사건 → 그룹당 3 상한 → 최소 2그룹


@pytest.mark.django_db
def test_aapl_plus10_overcollapse_regression():
    """★07-09 AAPL '+10건' 오접합 박제: 상이 사건들이 한 칩으로 안 뭉친다."""
    titles = [
        "App Store Growth Report",
        "Oil Drops Sharply Overnight",
        "Meta Bull Bear Prediction",
        "Nikkei Rebounds Broadly",
        "Chip Sector Rotation Begins",
    ]
    arts = [
        _article(f"http://f/x{i}", t, ["AAPL"], hours_ago=i + 1)
        for i, t in enumerate(titles)
    ]
    groups = strip_service._collapse(arts)
    # 상이 사건 5건 → 1칩 뭉침 없음(다수 칩) + 어떤 그룹도 상한 초과 안 함
    assert len(groups) >= 3
    assert max(g["collapsed_count"] for g in groups) <= strip_service.MAX_GROUP_SIZE - 1
