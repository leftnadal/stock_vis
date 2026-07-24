"""MP2-ANALOG Slice C-L3 — 그라운딩 선별(결정론, LLM·외부 API 0).

역할: 이웃일 T의 "그날" broad 시장 뉴스(services.news.NewsArticle) → market-relevant 상위 N.
  결정론 순수 랭킹(rank_headlines) + DB 페치(fetch_day_candidates) 분리 → 랭킹은 LLM·DB 무의존 단위 테스트.
소비처: apps/market_pulse/management/commands/generate_analog_context.py (L3 생성 커맨드).

창 정의(D-CL3-GROUNDING-WINDOW): T의 `published_at__date` = DB TZ(settings.TIME_ZONE='Asia/Seoul',
  USE_TZ=True) 기준 캘린더일. backfill_broad_news `_window_count`(동일 lookup)와 **동형** →
  백필이 커버한 뉴스 집합과 정확히 일치. (원 지시서의 "UTC 캘린더일" 명명은 STEP0 실측으로 정정:
  DB date lookup은 UTC가 아니라 서버 TZ(KST) 기준.)

★is_archived 무필터(D-CL3-ARCHIVE-BLIND, common-bugs 등재분): archive_old_articles가 6개월+
  과거분을 soft delete(is_archived=True)로 전환하므로, 기본 필터(is_archived=False)로 조회하면
  과거 이웃 전부가 벙어리가 된다. STEP0 실측 = 현재 과거분 대부분 is_archived=False(미아카이브)나,
  미래 아카이브 시 벙어리화를 막기 위해 그라운딩 쿼리는 is_archived로 **필터하지 않는다**(True/False 무관).

선별 신호(STEP0 실측 = 2024-05 broad 974건): importance_score 0%(rule engine 미적용) →
  주신호 = abs(sentiment_score)(AV overall_sentiment, 100%) + entity_count(ticker_sentiment 수, 100%)
  + 소스 다양성(편중 소스 PR Newswire류 컷). relevance 항목은 실측 미지원으로 제외(D-CL3-SELECT-RULE).
"""

from __future__ import annotations

from datetime import date as date_cls
from typing import Any

GROUNDING_TOP_N = 12
GROUNDING_SOURCE_CAP = 3  # 소스당 상한 — 편중 소스(PR Newswire 등) 독점 방지, 최소 ceil(N/cap) 소스 보장


def rank_headlines(
    candidates: list[dict[str, Any]],
    *,
    n: int = GROUNDING_TOP_N,
    source_cap: int = GROUNDING_SOURCE_CAP,
) -> list[dict[str, Any]]:
    """결정론 선별: 그날 후보 헤드라인 → market-relevant 상위 N.

    candidates 각 = {id, title, url, source, sentiment_score(None 가능), entity_count, published_at}.
    정렬(내림차순): abs(sentiment_score or 0) → entity_count → published_at → str(id) (완전 결정론 tie-break).
    소스 다양성: source당 최대 source_cap개, 정렬 순 greedy로 top-N 채움.
    """
    def sort_key(c: dict[str, Any]) -> tuple:
        s = c.get("sentiment_score")
        strength = abs(float(s)) if s is not None else 0.0
        ec = int(c.get("entity_count") or 0)
        pub = c.get("published_at")
        # reverse=True에서 published_at 최신 우선. None 발행시각은 최하(방어).
        pub_key = pub.isoformat() if hasattr(pub, "isoformat") else str(pub or "")
        return (strength, ec, pub_key, str(c.get("id", "")))

    ordered = sorted(candidates, key=sort_key, reverse=True)
    picked: list[dict[str, Any]] = []
    per_source: dict[str, int] = {}
    for c in ordered:
        src = c.get("source") or ""
        if per_source.get(src, 0) >= source_cap:
            continue
        picked.append(c)
        per_source[src] = per_source.get(src, 0) + 1
        if len(picked) >= n:
            break
    return picked


def fetch_day_candidates(target_date: date_cls) -> list[dict[str, Any]]:
    """T의 그날 뉴스 후보(is_archived 무필터) + entity_count annotate.

    창 = published_at__date == target_date (DB TZ 캘린더일, backfill 동형). ★is_archived 필터 없음.
    """
    from django.db.models import Count

    from services.news.models import NewsArticle

    rows = (
        NewsArticle.objects.filter(published_at__date=target_date)  # is_archived 무필터(D-CL3-ARCHIVE-BLIND)
        .annotate(entity_count=Count("entities"))
        .values("id", "title", "url", "source", "sentiment_score", "entity_count", "published_at")
    )
    return list(rows)


def select_grounding(
    target_date: date_cls,
    *,
    n: int = GROUNDING_TOP_N,
    source_cap: int = GROUNDING_SOURCE_CAP,
) -> list[dict[str, Any]]:
    """T의 그날 후보 페치 → 결정론 랭킹 상위 N. 그날 헤드라인 0건이면 빈 리스트(억지 생성 금지 신호)."""
    return rank_headlines(fetch_day_candidates(target_date), n=n, source_cap=source_cap)
