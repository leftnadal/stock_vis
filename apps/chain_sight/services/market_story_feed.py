"""R2-S2 — "오늘 시장의 이야기" 피드 (읽기 전용 서빙, 마이그 0·외부콜 0·prod write 0).

카드 v1(사용자 확정 2026-09-01):
- daily_spike : 일간 급등 버스트 — 단일일(first==last) co-mention 폭발, 14일 창, 발생일 명기.
- weekly_active: 이번 주 활발(steady) — count_7d 절대 상위(SymbolStoryActivity 캐시).
- new_sec     : 신규 SEC 연결 — 8-K filing_date 30일 창, filing일 명기.

ratio '동조 급증' 카드는 미구현(90일 co-mention 기저선 부재 — count_90d==count_7d, ratio 상수
아티팩트). HIST-BASELINE-MATURITY(뉴스 히스토리 ≥90일 관측 시) 재개. 규칙 준수:
- 규칙 2(정문 무공허): weekly_active 가 항상 채움. 임계·문구로 사건 부풀림 금지.
- 규칙 3(신뢰 위계): co_mention 카드는 kind='co_mention'(관계 아님·동시 언급), SEC 카드는
  kind='sec_evidence'. FE 가 배지·문구·색으로 구분한다.

서비스 층 분리 — S2 후속(조감 카드)·S3 재사용.
"""

import datetime

from django.apps import apps
from django.db.models import F, Q
from django.utils import timezone

# ── 임계 (STEP 0 실측 도출, 2026-09-02) ─────────────────────────────
DAILY_SPIKE_DAYS = 14        # 일간 급등 관측 창
DAILY_SPIKE_MIN_COUNT = 5    # 단일일 co-mention 폭발 하한(14일내 단일일 count 분포 p99=2·상위 8건)
WEEKLY_ACTIVE_MIN_7D = 1     # steady 카드 최소 7일 활동
NEW_SEC_DAYS = 30            # 신규 SEC filing_date 창(7일=0이라 완화 — 사용자 확정)
FEED_MAX_DEFAULT = 30
SEC4_TYPES = ("COMPETES_WITH", "PARTNER_WITH", "SUPPLIES_TO", "DEPENDS_ON")
_COMPANION_MAX = 4


def _daily_spike_cards(now, since14):
    """단일일(span0) 고 co-mention 엣지 = 일간 급등. 발생일 명기."""
    from apps.chain_sight.models import CoMentionEdge

    edges = list(
        CoMentionEdge.objects.filter(
            first_co_mention_date=F("last_co_mention_date"),
            last_co_mention_date__gte=since14,
            co_mention_count__gte=DAILY_SPIKE_MIN_COUNT,
        )
        .order_by("-co_mention_count", "-last_co_mention_date")
        .values("symbol_a", "symbol_b", "co_mention_count", "last_co_mention_date")
    )
    cards = []
    for e in edges:
        a, b, d = e["symbol_a"], e["symbol_b"], e["last_co_mention_date"]
        # 동반 멤버: 같은 날 단일일로 a 또는 b 와 함께 언급된 다른 종목(클러스터).
        companions = _same_day_companions(a, b, d)
        cards.append(
            {
                "type": "daily_spike",
                "kind": "co_mention",  # 규칙 3: 관계 아님·동시 언급
                "symbol_a": a,
                "symbol_b": b,
                "count": e["co_mention_count"],
                "occurred_on": d.isoformat() if d else None,
                "days_since": (now.date() - d).days if d else None,
                "companions": companions,
            }
        )
    return cards


def _same_day_companions(a, b, d):
    """발생일 d 에 a 또는 b 와 함께 단일일 언급된 다른 종목 상위(클러스터 표시용)."""
    from apps.chain_sight.models import CoMentionEdge

    if not d:
        return []
    rows = CoMentionEdge.objects.filter(
        first_co_mention_date=F("last_co_mention_date"),
        last_co_mention_date=d,
    ).filter(Q(symbol_a__in=(a, b)) | Q(symbol_b__in=(a, b))).values_list(
        "symbol_a", "symbol_b", "co_mention_count"
    )
    tally = {}
    for sa, sb, c in rows:
        for s in (sa, sb):
            if s in (a, b):
                continue
            tally[s] = max(tally.get(s, 0), c)
    return [s for s, _ in sorted(tally.items(), key=lambda kv: -kv[1])[:_COMPANION_MAX]]


def _weekly_active_cards(now):
    """count_7d 절대 상위(무방향 dedup). steady — 항상 채우는 fallback(규칙 2)."""
    from apps.chain_sight.models import SymbolStoryActivity

    seen = set()
    cards = []
    for r in (
        SymbolStoryActivity.objects.filter(count_7d__gte=WEEKLY_ACTIVE_MIN_7D)
        .order_by("-count_7d", "-last_co_mention_date")
        .values("symbol", "partner", "count_7d", "last_co_mention_date")
        .iterator()
    ):
        key = frozenset((r["symbol"], r["partner"]))
        if key in seen:
            continue
        seen.add(key)
        d = r["last_co_mention_date"]
        cards.append(
            {
                "type": "weekly_active",
                "kind": "co_mention",  # 규칙 3
                "symbol_a": r["symbol"],
                "symbol_b": r["partner"],
                "count": r["count_7d"],
                "occurred_on": d.isoformat() if d else None,
                "days_since": (now.date() - d).days if d else None,
                "companions": [],
            }
        )
        if len(cards) >= 40:  # 상한(정렬·cap은 상위에서)
            break
    return cards


def _new_sec_cards(now, since30):
    """8-K filing_date 30일 창 신규 SEC 연결. filing일 명기 — 신뢰 위계 상단."""
    SEC8K = apps.get_model("sec_pipeline", "SEC8KCounterpartyEvidence")
    cards = []
    seen = set()
    for e in (
        SEC8K.objects.filter(landed=True, filing_date__gte=since30)
        .order_by("-filing_date")
        .values(
            "source_symbol", "resolved_ticker", "relationship_type",
            "filing_date", "item_code",
        )
    ):
        a, b, rel = e["source_symbol"], e["resolved_ticker"], e["relationship_type"]
        key = (frozenset((a, b)), rel)
        if key in seen:
            continue
        seen.add(key)
        d = e["filing_date"]
        cards.append(
            {
                "type": "new_sec",
                "kind": "sec_evidence",  # 규칙 3: SEC 근거 관계
                "symbol_a": a,
                "symbol_b": b,
                "relation_type": rel,
                "item_code": e["item_code"],
                "occurred_on": d.isoformat() if d else None,
                "days_since": (now.date() - d).days if d else None,
                "companions": [],
            }
        )
    return cards


def build_market_story_feed(now=None, limit=FEED_MAX_DEFAULT):
    """오늘 시장의 이야기 피드. Returns {as_of, summary, cards}.

    정렬(A-5, 단순 규칙): 신규 SEC(희소·최고신뢰) → 일간 급등(사건성·count desc) →
    이번 주 활발(steady fill). 정교한 랭킹은 후속(S3).
    """
    now = now or timezone.now()
    since14 = now.date() - datetime.timedelta(days=DAILY_SPIKE_DAYS)
    since30 = now.date() - datetime.timedelta(days=NEW_SEC_DAYS)

    sec = _new_sec_cards(now, since30)
    spike = _daily_spike_cards(now, since14)
    steady = _weekly_active_cards(now)

    # steady 에서 이미 사건 카드로 나온 페어 제거(중복 회피 — 사건 우선).
    event_pairs = {frozenset((c["symbol_a"], c["symbol_b"])) for c in sec + spike}
    steady = [c for c in steady if frozenset((c["symbol_a"], c["symbol_b"])) not in event_pairs]

    ordered = sec + spike + steady
    cards = ordered[:limit]

    summary = {
        "new_sec": sum(1 for c in cards if c["type"] == "new_sec"),
        "daily_spike": sum(1 for c in cards if c["type"] == "daily_spike"),
        "weekly_active": sum(1 for c in cards if c["type"] == "weekly_active"),
    }
    # 규칙 2: 사건(new_sec+daily_spike) 0장이어도 steady 가 채움 → 정문 무공허.
    has_event = summary["new_sec"] + summary["daily_spike"] > 0
    return {
        "as_of": now.date().isoformat(),
        "has_event": has_event,
        "summary": summary,
        "total": len(cards),
        "cards": cards,
    }
