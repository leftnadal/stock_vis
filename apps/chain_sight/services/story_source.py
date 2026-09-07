"""CS-S3-1 StorySourceService — 근거 기사 재조회 · 8-K 제목 · 결정론 슬러그.

인용 계약(규칙 2): 제목은 근거 기사 **원문** 또는 8-K 템플릿(공시 사실)만. LLM 호출 0.
S3-PRE 실측(P1): CoMentionEdge 엣지에 기사 링크 없음 → (쌍,날짜)로 ChainNewsEvent(직결
제목) 또는 NewsEntity 교집합(→NewsArticle) 재조회로 복원. 커버리지 8/8(표본).

읽기 전용(prod write 0·외부콜 0·마이그 0). 관계·엣지 무변경.
"""

import datetime
import hashlib

# A-3: 8-K item 코드 → 한글 뜻(공시 사실만). S3-PRE 실측: DB distinct = 1.01·2.01 2종.
# shared 승격은 둘째 소비자가 생길 때(현재 chain_sight 내부 상수).
EIGHT_K_ITEM_LABELS = {
    "1.01": "중요 계약 체결",
    "2.01": "자산 인수·처분 완료",
}


def eight_k_title(symbol_a: str, symbol_b: str, item_code: str) -> str:
    """8-K 카드 제목 = 공시 사실 템플릿(LLM 0). 미매핑 item = fallback(공시 중복 없음)."""
    label = EIGHT_K_ITEM_LABELS.get(item_code)
    if label:
        return f"{symbol_a}, {symbol_b}와 {label} 공시"
    return f"{symbol_a}, {symbol_b}와 8-K 공시 (item {item_code})"


def story_key(story_type: str, members, occurred_on) -> str:
    """사람이 읽는 이야기 키 = type:정렬멤버:날짜(원문 병기용)."""
    occ = occurred_on.isoformat() if hasattr(occurred_on, "isoformat") else str(occurred_on)
    return f"{story_type}:{'-'.join(sorted(members))}:{occ}"


def story_slug(story_type: str, members, occurred_on) -> str:
    """A-4 결정론 슬러그(저장 없음). 같은 입력 → 같은 10-hex(blake2b digest_size=5)."""
    return hashlib.blake2b(
        story_key(story_type, members, occurred_on).encode("utf-8"), digest_size=5
    ).hexdigest()


def _as_date(occurred_on):
    if isinstance(occurred_on, datetime.date):
        return occurred_on
    return datetime.date.fromisoformat(str(occurred_on))


def articles_for_pair(symbol_a: str, symbol_b: str, occurred_on, limit: int = 5) -> list[dict]:
    """(a,b,occurred_on) 근거 기사 = [{id, title, url, published_at, symbols_covered}].

    우선순위: ChainNewsEvent 직결 제목 → NewsEntity 교집합(NewsArticle). 정렬:
    symbols_covered 많은 순 → published_at 최신. 결과 없음 = 빈 리스트(예외 아님).
    """
    a, b = symbol_a.upper(), symbol_b.upper()
    d = _as_date(occurred_on)
    out: list[dict] = []
    seen_titles: set[str] = set()

    # 발행시각 창 = 발생일 ±1일(UTC-aware). naive 창은 settings.TIME_ZONE 로 해석돼
    # UTC 저녁 기사가 잘리므로(co-mention 엣지 날짜 산정 TZ 불명) ±1일 UTC 버퍼로 흡수.
    lo = datetime.datetime.combine(
        d - datetime.timedelta(days=1), datetime.time.min, tzinfo=datetime.timezone.utc
    )
    hi = datetime.datetime.combine(
        d + datetime.timedelta(days=1), datetime.time.max, tzinfo=datetime.timezone.utc
    )

    # 1) ChainNewsEvent 직결(제목 원문 보유 + co_mentioned_symbols).
    from django.db.models import Q

    from apps.chain_sight.models.news_event import ChainNewsEvent

    cne = (
        ChainNewsEvent.objects.filter(published_at__range=(lo, hi))
        .filter(Q(co_mentioned_symbols__contains=[a]) | Q(symbol__symbol=a))
        .filter(Q(co_mentioned_symbols__contains=[b]) | Q(symbol__symbol=b))
        .values("id", "symbol_id", "title", "url", "published_at", "co_mentioned_symbols")
    )
    for e in cne:
        covered = _covered_symbols(e["symbol_id"], e["co_mentioned_symbols"])
        out.append({
            "id": f"cne:{e['id']}",
            "title": e["title"],
            "url": e["url"] or None,
            "published_at": e["published_at"].isoformat() if e["published_at"] else None,
            "symbols_covered": covered,
        })
        seen_titles.add(e["title"])

    # 2) NewsEntity 교집합(두 종목 모두 언급된 NewsArticle) — 제목 원문.
    from services.news.models import NewsEntity

    ids_a = NewsEntity.objects.filter(
        symbol=a, news__published_at__range=(lo, hi)
    ).values("news_id")
    arts = (
        NewsEntity.objects.filter(symbol=b, news_id__in=ids_a)
        .select_related("news")
        .values("news_id", "news__title", "news__url", "news__published_at")
    )
    for r in arts:
        title = r["news__title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)
        # 이 기사가 언급한 전 종목(커버 폭 많은 기사가 상위 — 클러스터 중심 기사 우선).
        covered = _newsentity_covered(r["news_id"])
        out.append({
            "id": f"news:{r['news_id']}",
            "title": title,
            "url": r["news__url"] or None,
            "published_at": r["news__published_at"].isoformat() if r["news__published_at"] else None,
            "symbols_covered": covered,
        })

    # symbols_covered 많은 순 우선 → published_at 최신 순.
    out.sort(key=lambda x: (len(x["symbols_covered"]), x["published_at"] or ""), reverse=True)
    return out[:limit]


def _covered_symbols(symbol_id, co_mentioned) -> list[str]:
    """ChainNewsEvent 한 건이 커버하는 종목 집합."""
    return sorted({symbol_id, *(co_mentioned or [])})


def _newsentity_covered(news_id) -> list[str]:
    """NewsArticle 한 건이 언급한 전 종목(커버 폭 랭킹용)."""
    from services.news.models import NewsEntity

    syms = set(
        NewsEntity.objects.filter(news_id=news_id).values_list("symbol", flat=True)
    )
    return sorted(syms)
