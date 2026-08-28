"""R2-S1 — co-mention 파트너 활동 스레드 집계 (엣지 직접·마이그0).

"이 종목의 이야기" = 종목의 co-mention 이웃(파트너 스레드). 각 파트너별로
최근 7일 동반 언급 수·90일 주간 평균 대비 비율·마지막 언급일을 산출한다.

소스 결정(A안·2026-08-27 디렉터 확정, [[DECISIONS]]):
- EventGroup은 조감용 sparse 클러스터(허브 배제는 의도된 게이팅) → 카드 패널 소스 부적합
  (NVDA·AAPL·MRNA=0그룹·커버 170/757). S2 카드 유형 후보로 보존.
- 90d count·마지막일 = `CoMentionEdge`(일일 재집계·빠름). 7일 count만 `NewsEntity`
  라이브 집계(표시 후보 상한으로 bounded).

이 함수는 뷰에 인라인하지 않고 서비스 층에 두어 S2 전역 활동 뷰의 소스로 재사용한다.
관계·그룹 멤버십을 생성/수정하지 않는다(읽기 집계만).
"""

import datetime

from django.db.models import Count, Q, Subquery
from django.utils import timezone

from apps.chain_sight.models import CoMentionEdge

WINDOW_RECENT_DAYS = 7
WINDOW_BASE_DAYS = 90
CANDIDATE_N = 24  # 7일 집계 대상 후보 상한(최근순 — 7d 활성 파트너는 최상단에 포함됨)
DEFAULT_TOP_N = 10


def _weekly_avg(count_90d: int) -> float:
    """90일 누적 → 주간 평균."""
    if not count_90d:
        return 0.0
    return round(count_90d / (WINDOW_BASE_DAYS / 7.0), 2)


def _recent_counts(symbol: str, partner_syms: list[str], now) -> dict[str, int]:
    """후보 파트너 한정 최근 7일 동반 언급 수(기사 단위) — bounded NewsEntity 집계.

    symbol 이 등장한 최근 7일 기사에서, 후보 파트너별 동반 등장 기사 수를 센다.
    unique_together(news, symbol) → 파트너당 기사당 1행(중복 없음).
    """
    if not partner_syms:
        return {}
    from services.news.models import NewsEntity

    cutoff = now - datetime.timedelta(days=WINDOW_RECENT_DAYS)
    news_ids = NewsEntity.objects.filter(
        symbol=symbol, news__published_at__gte=cutoff
    ).values("news_id")
    rows = (
        NewsEntity.objects.filter(
            news_id__in=Subquery(news_ids),
            news__published_at__gte=cutoff,
            symbol__in=partner_syms,
        )
        .exclude(symbol=symbol)
        .values("symbol")
        .annotate(n=Count("id"))
        .values_list("symbol", "n")
    )
    return dict(rows)


def get_symbol_story_threads(
    symbol: str,
    top_n: int = DEFAULT_TOP_N,
    candidate_n: int = CANDIDATE_N,
    now=None,
) -> dict:
    """종목의 co-mention 파트너 활동 스레드.

    Returns:
        {threads: [...top_n], thread_total, threads_capped, shown}
        thread = {partner, count_7d, count_90d, weekly_avg_90d, activity_ratio,
                  last_co_mention_date, days_since, quiet}
        quiet=True → 최근 7일 활동 0(게이지 대신 "조용함" 표시용, 규칙 6).
    """
    symbol = symbol.upper()
    now = now or timezone.now()
    ref_date = now.date()

    # 1) CoMentionEdge 파트너 후보 (90d count + 마지막일). 관계 생성 없음(읽기).
    partners: dict[str, dict] = {}
    for e in (
        CoMentionEdge.objects.filter(Q(symbol_a=symbol) | Q(symbol_b=symbol)).values(
            "symbol_a", "symbol_b", "co_mention_count", "last_co_mention_date"
        )
    ):
        other = e["symbol_b"] if e["symbol_a"] == symbol else e["symbol_a"]
        partners[other] = {
            "count_90d": e["co_mention_count"] or 0,
            "last_co_mention_date": e["last_co_mention_date"],
        }
    total = len(partners)
    if not total:
        return {"threads": [], "thread_total": 0, "threads_capped": False, "shown": 0}

    # 2) 최근순 후보 선별 — 7d 활성(last_date within 7d) 파트너가 최상단에 모두 포함됨.
    ranked = sorted(
        partners.items(),
        key=lambda kv: (
            kv[1]["last_co_mention_date"] or datetime.date.min,
            kv[1]["count_90d"],
        ),
        reverse=True,
    )
    cand_syms = [s for s, _ in ranked[:candidate_n]]

    # 3) 7일 count (후보 한정 라이브 집계)
    counts_7d = _recent_counts(symbol, cand_syms, now)

    # 4) 스레드 구성 + 활동 지표
    threads = []
    for s in cand_syms:
        p = partners[s]
        c7 = counts_7d.get(s, 0)
        wavg = _weekly_avg(p["count_90d"])
        last = p["last_co_mention_date"]
        threads.append(
            {
                "partner": s,
                "count_7d": c7,
                "count_90d": p["count_90d"],
                "weekly_avg_90d": wavg,
                "activity_ratio": round(c7 / wavg, 2) if wavg else None,
                "last_co_mention_date": last.isoformat() if last else None,
                "days_since": (ref_date - last).days if last else None,
                "quiet": c7 == 0,
            }
        )

    # 5) 활동순 정렬(7d 내림차순 → 최근일) + top_n 상한
    threads.sort(
        key=lambda t: (t["count_7d"], t["last_co_mention_date"] or ""), reverse=True
    )
    shown = threads[:top_n]
    return {
        "threads": shown,
        "thread_total": total,
        "threads_capped": total > len(shown),
        "shown": len(shown),
    }
