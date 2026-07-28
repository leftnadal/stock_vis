"""뉴스 스트립(S1) 응축 조립 — /api/dashboard/news-strip BFF. [D-NEWSAXIS-CONTRACT]

읽기 전용(뉴스·관계망 쓰기 0). 티어 F2(계층+쿼터) × 자체 접기(심볼겹침½∧24h∧제목핵심어)
× RelationConfidence θ배지 × 서버 15분 캐시. 응답 item = 계약 shape 그대로.

의존 방향: app(dashboard) → app(chain_sight)·services(news)·shared(stocks/users) = 단방향 합법.
Neo4j 미접근 — Postgres RelationConfidence만.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import timedelta

from django.core.cache import cache
from django.db import connection
from django.db.models import Count
from django.utils import timezone

# 티어당 최대 칩 · 총 칩 상한 · 후보 신선도 창(일) · 접기 창(시간)
TIER_QUOTA = 2
TOTAL_CAP = 5
CANDIDATE_WINDOW_DAYS = 7
COLLAPSE_WINDOW_HOURS = 24
CACHE_TTL_SECONDS = 15 * 60  # 서버 15분 TTL
_CACHE_KEY = "dashboard:news_strip:v1:user:{uid}"

# 접기 안전핀 상수 (D-STRIP-FOLD-TUNE — STRIP-FOLD-TUNE STEP 0 실데이터 근거).
# ⓑ 라운드업 배제: 언급 심볼 수 > MAX_ABSORB_SYMBOLS인 기사는 타 기사 흡수 금지
#    (자신은 대표로 잔류). 근거: 기사당 심볼 수 최근 7일 p95=3 → >3(≥4)=라운드업.
MAX_ABSORB_SYMBOLS = 3
# ⓒ 그룹 크기 상한: 한 접기 그룹 최대 멤버(대표+흡수). 초과분 독립 잔류.
#    근거: 심볼별 24h 기사 수 median=1·q3=2 → 같은-사건 클러스터 소형. rep+2.
MAX_GROUP_SIZE = 3

# ⓐ 제목 핵심어 stopword(접기 안전핀 — 특이어 공유만 접합 근거로 인정).
# 근거: STEP 0 T0-2 최근 7일 제목 토큰 문서빈도 상위(일반 금융어·구조어·회사 접미).
# 이 일반어 공유는 "같은 사건"의 근거가 못 됨(라운드업이 stock/price/market 공유로
# 오접합하던 경로 차단). 심볼 토큰 제외는 _collapse에서 별도 유지.
_STOPWORDS = {
    # 구조어(영문)
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "as", "its", "with", "from", "by", "us", "after", "why", "you", "at", "be",
    # 일반 금융·시장어(T0-2 상위 DF)
    "stock", "stocks", "price", "prices", "shares", "market", "markets",
    "nasdaq", "nyse", "sec", "etf", "earnings", "investors", "investor",
    "buy", "sell", "hold", "growth", "value", "forward", "financial",
    "enterprise", "corp", "inc", "group", "ltd", "co", "company",
    # 숫자성 잡음
    "2026", "2025", "000",
    # 일반어(한글)
    "그", "이", "저", "및", "등", "관련", "뉴스", "속보", "종목", "주가",
    "상승", "하락", "전망", "마감", "시장", "주식", "투자", "분석",
}
_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")


def _title_keywords(title: str) -> set[str]:
    """제목 → 핵심어 집합(2자+ 토큰, stopword 제외). 접기 안전핀."""
    return {
        t.lower()
        for t in _TOKEN_RE.findall(title or "")
        if len(t) >= 2 and t.lower() not in _STOPWORDS
    }


def compute_confidence_theta() -> float:
    """배지 임계 θ = RelationConfidence.truth_score 실분포 상위 ~15% 분위(p85).

    상수 하드코딩 금지 — 매 조립 시 라이브 분포에서 계산(분포 이동 자동 추종).
    데이터 부재 시 0.0(배지 후보 없음과 동치).
    """
    with connection.cursor() as cur:
        cur.execute(
            "SELECT percentile_cont(0.85) WITHIN GROUP (ORDER BY truth_score) "
            "FROM chainsight_relation_confidence WHERE truth_score IS NOT NULL"
        )
        row = cur.fetchone()
    return float(row[0]) if row and row[0] is not None else 0.0


def _held_watched_symbols(user) -> tuple[set[str], set[str]]:
    """T1 보유(WalletHolding)·T3 관심(WatchlistItem) 심볼 집합. 부재 = 빈 집합(공석)."""
    from apps.portfolio.models import WalletHolding
    from packages.shared.users.models import WatchlistItem

    held = set(
        WalletHolding.objects.filter(wallet__user=user)
        .values_list("stock_id", flat=True)
        .distinct()
    )
    watched = set(
        WatchlistItem.objects.filter(watchlist__user=user)
        .values_list("stock_id", flat=True)
        .distinct()
    )
    return {s for s in held if s}, {s for s in watched if s}


def _recommendation_symbols() -> set[str]:
    """T2 오늘 추천 연결 — IssuanceLog 최신 signal_date 심볼."""
    from packages.shared.stocks.models import IssuanceLog

    latest = IssuanceLog.objects.order_by("-signal_date").values_list(
        "signal_date", flat=True
    ).first()
    if latest is None:
        return set()
    return {
        s
        for s in IssuanceLog.objects.filter(signal_date=latest).values_list(
            "stock_id", flat=True
        )
        if s
    }


def _network_edges(seed_symbols: set[str], theta: float) -> list:
    """T4 재료 + 배지 재료 — seed(보유·관심)에 연결된 RelationConfidence 엣지(truth_score≥θ).

    반환: [(other_symbol, RelationConfidence)] — other=seed 반대편.
    """
    if not seed_symbols:
        return []
    from apps.chain_sight.models.relation_discovery import RelationConfidence
    from django.db.models import Q

    qs = (
        RelationConfidence.objects.filter(truth_score__gte=theta)
        .filter(Q(symbol_a__in=seed_symbols) | Q(symbol_b__in=seed_symbols))
        .order_by("-truth_score", "-has_news_source")
    )
    edges = []
    for rc in qs:
        other = rc.symbol_b if rc.symbol_a in seed_symbols else rc.symbol_a
        edges.append((other, rc))
    return edges


def _resolve_tiers(user, theta: float) -> tuple[dict[int, set[str]], list]:
    """티어별 심볼 집합(T1~T4) + 배지용 엣지 목록. T5는 심볼 무관(시장 전반)."""
    held, watched = _held_watched_symbols(user)
    recs = _recommendation_symbols()
    edges = _network_edges(held | watched, theta)
    network_syms = {other for other, _ in edges}

    tiers = {
        1: set(held),
        2: set(recs),
        3: set(watched),
        4: set(network_syms),
    }
    return tiers, edges


def _fetch_candidates(symbols: set[str], since, used_ids: set[int]):
    """symbols를 언급하는 최근 NewsArticle 후보(신선도·언급 수 주석). used 제외."""
    from services.news.models import NewsArticle

    qs = (
        NewsArticle.objects.filter(
            entities__symbol__in=symbols, published_at__gte=since
        )
        .exclude(id__in=used_ids)
        .annotate(mention_count=Count("entities"))
        .distinct()
        .order_by("-published_at")
    )
    return list(qs)


def _fetch_market_candidates(since, used_ids: set[int]):
    """T5 시장 전반 — 중요도 상위 최근 기사(심볼 무관)."""
    from services.news.models import NewsArticle

    qs = (
        NewsArticle.objects.filter(published_at__gte=since)
        .exclude(id__in=used_ids)
        .annotate(mention_count=Count("entities"))
        .order_by("-importance_score", "-published_at")
    )
    return list(qs[:20])


def _article_symbols(article) -> set[str]:
    return {e.symbol for e in article.entities.all()}


def _collapse(articles: list) -> list[dict]:
    """자체 접기 — 심볼겹침≥½ ∧ 24h ∧ 제목 핵심어 공유. 대표=최다 언급 + collapsed_count.

    규칙 기반 근사(한계: 오접힘/미접힘 = 도그푸딩 관찰, v2=bake LLM 클러스터링).
    """
    enriched = []
    for a in articles:
        syms = _article_symbols(a)
        # 제목 핵심어에서 심볼 토큰 제거 — 심볼은 겹침 차원이지 사건 식별 차원이 아님
        # (안 하면 같은 종목 기사가 티커 공유만으로 늘 접혀 안전핀 무력화).
        keywords = _title_keywords(a.title) - {s.lower() for s in syms}
        enriched.append(
            {
                "article": a,
                "symbols": syms,
                "keywords": keywords,
                "mention": getattr(a, "mention_count", 0),
                "published_at": a.published_at,
            }
        )

    used = [False] * len(enriched)
    groups = []
    for i, base in enumerate(enriched):
        if used[i]:
            continue
        members = [base]
        used[i] = True
        # ⓑ 라운드업(심볼 수 > 상한)은 타 기사를 흡수하지 못함 — 단독 대표로 잔류.
        base_is_roundup = len(base["symbols"]) > MAX_ABSORB_SYMBOLS
        if not base_is_roundup:
            for j in range(i + 1, len(enriched)):
                if used[j]:
                    continue
                if len(members) >= MAX_GROUP_SIZE:  # ⓒ 그룹 상한 — 초과분 독립 잔류
                    break
                cand = enriched[j]
                # ⓑ 라운드업 후보도 흡수 대상 제외(독립 잔류).
                if len(cand["symbols"]) > MAX_ABSORB_SYMBOLS:
                    continue
                if _same_event(base, cand):
                    members.append(cand)
                    used[j] = True
        rep = max(members, key=lambda m: (m["mention"], m["published_at"]))
        rep_symbols = set()
        for m in members:
            rep_symbols |= m["symbols"]
        groups.append(
            {
                "article": rep["article"],
                "symbols": rep_symbols,
                "mention": rep["mention"],
                "published_at": rep["published_at"],
                "collapsed_count": len(members) - 1,
                "article_ids": {m["article"].id for m in members},
            }
        )
    return groups


def _same_event(a: dict, b: dict) -> bool:
    """접기 3조건 동시 충족: 심볼겹침≥½ ∧ 24h 창 ∧ 제목 핵심어 ≥1 공유(안전핀)."""
    sa, sb = a["symbols"], b["symbols"]
    if not sa or not sb:
        return False
    overlap = len(sa & sb)
    smaller = min(len(sa), len(sb))
    if overlap * 2 < smaller:  # 겹침 < ½
        return False
    if abs((a["published_at"] - b["published_at"]).total_seconds()) > COLLAPSE_WINDOW_HOURS * 3600:
        return False
    if not (a["keywords"] & b["keywords"]):  # 제목 핵심어 미공유 = 다른 사건(안전핀)
        return False
    return True


def _direction(article) -> str:
    """sentiment 부호 → 방향. up/down/neutral."""
    s = article.sentiment_score
    if s is None:
        return "neutral"
    s = float(s)
    if s > 0:
        return "up"
    if s < 0:
        return "down"
    return "neutral"


_TIER_LINE = {
    1: "보유 종목 관련",
    2: "오늘 추천과 연결",
    3: "관심 종목 관련",
    4: "관계망 인접 종목",
    5: "시장 전반",
}


def _build_badge(chip_symbols: set[str], seed_symbols: set[str], theta: float):
    """칩 심볼과 보유·관심 노드를 잇는 최강 RelationConfidence 엣지 1개(≥θ). 없으면 None."""
    if not chip_symbols or not seed_symbols:
        return None
    from apps.chain_sight.models.relation_discovery import RelationConfidence
    from django.db.models import Q

    qs = (
        RelationConfidence.objects.filter(truth_score__gte=theta)
        .filter(
            (Q(symbol_a__in=chip_symbols) & Q(symbol_b__in=seed_symbols))
            | (Q(symbol_b__in=chip_symbols) & Q(symbol_a__in=seed_symbols))
        )
        .order_by("-truth_score", "-has_news_source")
    )
    rc = qs.first()
    if rc is None:
        return None
    return {"pair": f"{rc.symbol_a}↔{rc.symbol_b}", "confidence": float(rc.truth_score)}


def build_news_strip(user) -> dict:
    """스트립 응답 조립(캐시 경유). item = D-NEWSAXIS-CONTRACT 계약."""
    uid = getattr(user, "id", None) or "anon"
    key = _CACHE_KEY.format(uid=uid)
    cached = cache.get(key)
    if cached is not None:
        return cached

    result = _assemble(user)
    cache.set(key, result, CACHE_TTL_SECONDS)
    return result


def _assemble(user) -> dict:
    now = timezone.now()
    since = now - timedelta(days=CANDIDATE_WINDOW_DAYS)
    theta = compute_confidence_theta()
    tiers, _edges = _resolve_tiers(user, theta)
    held, watched = _held_watched_symbols(user)
    seed = held | watched

    chips: list[dict] = []
    used_ids: set[int] = set()

    for tier_num in (1, 2, 3, 4, 5):
        if len(chips) >= TOTAL_CAP:
            break
        if tier_num == 5:
            candidates = _fetch_market_candidates(since, used_ids)
        else:
            syms = tiers.get(tier_num, set())
            if not syms:  # 티어 공석(안전조항) → 다음 티어로 충원
                continue
            candidates = _fetch_candidates(syms, since, used_ids)
        if not candidates:
            continue

        groups = _collapse(candidates)
        # 티어 내 정렬: 신선도 → 언급
        groups.sort(key=lambda g: (g["published_at"], g["mention"]), reverse=True)

        take = min(TIER_QUOTA, TOTAL_CAP - len(chips))
        for g in groups[:take]:
            art = g["article"]
            chips.append(
                {
                    "headline": art.title,
                    "symbols": sorted(g["symbols"]),
                    "direction": _direction(art),
                    "tier": tier_num,
                    "relevance_line": _TIER_LINE[tier_num],
                    "collapsed_count": g["collapsed_count"],
                    "badge": _build_badge(g["symbols"], seed, theta),
                    "published_at": art.published_at.isoformat(),
                    "article_url": art.url,
                }
            )
            used_ids |= g["article_ids"]
            if len(chips) >= TOTAL_CAP:
                break

    return {"as_of": now.isoformat(), "theta": theta, "items": chips}
