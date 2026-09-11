"""R2-S2 + S3-1 — "오늘 시장의 이야기" 피드 (읽기 전용 서빙, 마이그 0·외부콜 0·prod write 0).

카드 v1(사용자 확정 2026-09-01):
- daily_spike : 일간 급등 버스트 — 단일일(first==last) co-mention 폭발, 14일 창, 발생일 명기.
- weekly_active: 이번 주 활발(steady) — count_7d 절대 상위(SymbolStoryActivity 캐시).
- new_sec     : 신규 SEC 연결 — 8-K filing_date 30일 창, filing일 명기.

S3-1(2026-09-04) 확장:
- A-2 묶음: 같은 발생일의 daily_spike 쌍을 companions/멤버 합집합(union-find)으로 묶어
  묶음 카드 1장으로. members[]·pairs[]·max_mentions·companions_outside[]. type/kind 유지.
- A-3 제목(인용만·LLM 0): 8-K = 공시 사실 템플릿(story_source.eight_k_title). 동시언급/steady =
  근거 기사 제목 원문(story_source.articles_for_pair 상위 1건). 기사 0건 → title=None.
- A-4 이야기 id: 결정론 슬러그(story_source.story_slug, 저장 없음).
- A-5 헤더 정직화: meta{as_of, new_today, stories, by_type}. 정렬 = occurred_on desc →
  사건성(new_sec>daily_spike>weekly_active) → max_mentions desc.
- A-6 근거 팩: 카드마다 evidence[] = [{kind:"article"|"8k", ref, title, url, date}].

ratio '동조 급증' 카드는 미구현(90일 co-mention 기저선 부재). HIST-BASELINE-MATURITY 재개.
규칙 준수: 규칙 2(정문 무공허 — steady 항상 채움), 규칙 3(신뢰 위계 kind), 배수/평소대비 표기 0.

서비스 층 분리 — S3 리포트 페이지(§2~§6)가 재사용.
"""

import datetime
from collections import defaultdict
from zoneinfo import ZoneInfo

from django.apps import apps
from django.db.models import F, Q
from django.utils import timezone

from apps.chain_sight.services.story_source import (
    articles_for_pair,
    eight_k_title,
    story_key,
    story_slug,
)

# ── 임계 (STEP 0 실측 도출, 2026-09-02) ─────────────────────────────
DAILY_SPIKE_DAYS = 14        # 일간 급등 관측 창
DAILY_SPIKE_MIN_COUNT = 5    # 단일일 co-mention 폭발 하한(14일내 단일일 count 분포 p99=2·상위 8건)
WEEKLY_ACTIVE_MIN_7D = 1     # steady 카드 최소 7일 활동
WEEKLY_ACTIVE_WINDOW_DAYS = 7  # steady 활동 관측 창(count_7d)
NEW_SEC_DAYS = 30            # 신규 SEC filing_date 창(7일=0이라 완화 — 사용자 확정)
FEED_MAX_DEFAULT = 30
_COMPANION_MAX = 4
_EVIDENCE_MAX = 5

_ET = ZoneInfo("America/New_York")
# 정렬 사건성 순위(낮을수록 상단): 신규 SEC > 일간 급등 > 이번 주 활발.
_TYPE_RANK = {"new_sec": 0, "daily_spike": 1, "weekly_active": 2}


# ── daily_spike: 단일일 엣지 → 발생일별 묶음 카드(A-2) ───────────────
def _spike_edges(since14):
    """단일일(span0) 고 co-mention 엣지 목록(발생일·쌍·언급 수)."""
    from apps.chain_sight.models import CoMentionEdge

    return list(
        CoMentionEdge.objects.filter(
            first_co_mention_date=F("last_co_mention_date"),
            last_co_mention_date__gte=since14,
            co_mention_count__gte=DAILY_SPIKE_MIN_COUNT,
        )
        .order_by("-co_mention_count", "-last_co_mention_date")
        .values("symbol_a", "symbol_b", "co_mention_count", "last_co_mention_date")
    )


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


def _daily_spike_group_cards(now, since14):
    """단일일 급등 엣지를 발생일별 companions/멤버 합집합으로 묶은 묶음 카드(A-2).

    같은 occurred_on 안에서 멤버(쌍 종목)를 공유하는 엣지를 union-find 로 병합.
    """
    edges = _spike_edges(since14)
    by_day = defaultdict(list)
    for e in edges:
        by_day[e["last_co_mention_date"]].append(e)

    cards = []
    for d, day_edges in by_day.items():
        n = len(day_edges)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            parent[find(x)] = find(y)

        pair_syms = [{e["symbol_a"], e["symbol_b"]} for e in day_edges]
        for i in range(n):
            for j in range(i + 1, n):
                if pair_syms[i] & pair_syms[j]:
                    union(i, j)

        clusters = defaultdict(list)
        for i in range(n):
            clusters[find(i)].append(i)

        for idxs in clusters.values():
            members = set()
            comps = set()
            pairs = []
            for i in idxs:
                e = day_edges[i]
                a, b = e["symbol_a"], e["symbol_b"]
                members |= {a, b}
                comps |= set(_same_day_companions(a, b, d))
                pairs.append({"symbol_a": a, "symbol_b": b, "count": e["co_mention_count"]})
            pairs.sort(key=lambda p: p["count"], reverse=True)
            top = pairs[0]
            comps_outside = sorted(comps - members)
            members_sorted = sorted(members)
            occurred = d.isoformat() if d else None
            cards.append(
                {
                    "type": "daily_spike",
                    "kind": "co_mention",  # 규칙 3: 관계 아님·동시 언급
                    "is_group": True,
                    "story_id": story_slug("daily_spike", members_sorted, occurred),
                    "story_key": story_key("daily_spike", members_sorted, occurred),
                    "title": None,  # 제목 인용은 표시 카드 한정 후처리(A-3)
                    "members": members_sorted,
                    "symbol_a": top["symbol_a"],
                    "symbol_b": top["symbol_b"],
                    "pairs": pairs,
                    "count": top["count"],  # backward compat = max_mentions
                    "max_mentions": top["count"],
                    "companions": comps_outside,  # backward compat = companions_outside
                    "companions_outside": comps_outside,
                    "occurred_on": occurred,
                    "days_since": (now.date() - d).days if d else None,
                    "window_label": f"{DAILY_SPIKE_DAYS}일 중 이 하루",  # 카드 자기 창(B안·상수 파생)
                    "evidence": [],
                }
            )
    return cards


def _weekly_active_cards(now):
    """count_7d 절대 상위(무방향 dedup). steady — 항상 채우는 fallback(규칙 2).

    H(정직성 보강): window_label "최근 7일 활동"은 캐시 신선도가 아니라 **쿼리**가 보장한다.
    materialize(ET 12:00)가 밀려도 창 밖(last_co_mention_date < now-7d) 행이 그 라벨을
    달고 노출되지 않도록 last_co_mention_date 하한을 건다(상수 파생).
    """
    from apps.chain_sight.models import SymbolStoryActivity

    since7 = now.date() - datetime.timedelta(days=WEEKLY_ACTIVE_WINDOW_DAYS)
    seen = set()
    cards = []
    for r in (
        SymbolStoryActivity.objects.filter(
            count_7d__gte=WEEKLY_ACTIVE_MIN_7D, last_co_mention_date__gte=since7
        )
        .order_by("-count_7d", "-last_co_mention_date")
        .values("symbol", "partner", "count_7d", "last_co_mention_date")
        .iterator()
    ):
        key = frozenset((r["symbol"], r["partner"]))
        if key in seen:
            continue
        seen.add(key)
        d = r["last_co_mention_date"]
        occurred = d.isoformat() if d else None
        members_sorted = sorted((r["symbol"], r["partner"]))
        cards.append(
            {
                "type": "weekly_active",
                "kind": "co_mention",  # 규칙 3
                "is_group": False,
                "story_id": story_slug("weekly_active", members_sorted, occurred),
                "story_key": story_key("weekly_active", members_sorted, occurred),
                "title": None,
                "members": members_sorted,
                "symbol_a": r["symbol"],
                "symbol_b": r["partner"],
                "count": r["count_7d"],
                "max_mentions": r["count_7d"],
                "occurred_on": occurred,
                "days_since": (now.date() - d).days if d else None,
                "window_label": f"최근 {WEEKLY_ACTIVE_WINDOW_DAYS}일 활동",  # 카드 자기 창(B안·상수 파생)
                "companions": [],
                "companions_outside": [],
                "evidence": [],
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
            "filing__accession_no", "filing__primary_doc_url",
        )
    ):
        a, b, rel = e["source_symbol"], e["resolved_ticker"], e["relationship_type"]
        key = (frozenset((a, b)), rel)
        if key in seen:
            continue
        seen.add(key)
        d = e["filing_date"]
        occurred = d.isoformat() if d else None
        members_sorted = sorted((a, b))
        title = eight_k_title(a, b, e["item_code"])
        url = e["filing__primary_doc_url"] or None
        cards.append(
            {
                "type": "new_sec",
                "kind": "sec_evidence",  # 규칙 3: SEC 근거 관계
                "is_group": False,
                "story_id": story_slug("new_sec", members_sorted, occurred),
                "story_key": story_key("new_sec", members_sorted, occurred),
                "title": title,
                "members": members_sorted,
                "symbol_a": a,
                "symbol_b": b,
                "relation_type": rel,
                "item_code": e["item_code"],
                "occurred_on": occurred,
                "days_since": (now.date() - d).days if d else None,
                "window_label": f"{NEW_SEC_DAYS}일 내 신규 공시",  # 카드 자기 창(B안·상수 파생)
                "companions": [],
                "companions_outside": [],
                "max_mentions": 0,
                "evidence": [
                    {
                        "kind": "8k",
                        "ref": e["filing__accession_no"],
                        "title": title,
                        "url": url,
                        "date": occurred,
                    }
                ],
            }
        )
    return cards


def _enrich_titles(cards):
    """표시 카드(co_mention)에 근거 기사 제목·evidence 부착(A-3·A-6). 인용만·LLM 0.

    표시 대상(limit 이후)만 조회 → 조회 비용 bounded. 8-K 는 이미 템플릿 제목 보유.
    """
    for c in cards:
        if c["type"] not in ("daily_spike", "weekly_active"):
            continue
        if not c["occurred_on"]:
            continue
        arts = articles_for_pair(
            c["symbol_a"], c["symbol_b"], c["occurred_on"], limit=_EVIDENCE_MAX
        )
        c["title"] = arts[0]["title"] if arts else None
        c["evidence"] = [
            {
                "kind": "article",
                "ref": a["id"],
                "title": a["title"],
                "url": a["url"],
                "date": a["published_at"],
            }
            for a in arts
        ]
    return cards


def _enrich_relation_lines(cards):
    """표시 카드에 관계 종류 한 줄(D-S3-8) 부착 — serving_layer 축. 일괄 조회(N+1 금지)."""
    from apps.chain_sight.services.relation_lookup import (
        lookup_pairs,
        relation_line_for,
        relation_recorded,
    )

    pairs = [(c["symbol_a"], c["symbol_b"]) for c in cards]
    rowmap = lookup_pairs(pairs)
    for c in cards:
        rows = rowmap.get(frozenset((c["symbol_a"], c["symbol_b"])), [])
        c["relation_line"] = relation_line_for(rows)
        c["relation_recorded"] = relation_recorded(rows)
    return cards


def _occ_ordinal(occ):
    """occurred_on(iso) → 정수 서수(desc 정렬용). 없으면 0(가장 과거)."""
    if not occ:
        return 0
    try:
        return datetime.date.fromisoformat(occ).toordinal()
    except ValueError:
        return 0


def _sort_key(c):
    # 확정 스펙(D-DIRECTOR-READ 2026-09-04): 사건성 asc(new_sec>daily_spike>weekly_active)
    # → occurred_on desc → max_mentions desc. 사건 카드가 잔잔한 최신 steady 위에 온다.
    return (
        _TYPE_RANK[c["type"]],
        -_occ_ordinal(c["occurred_on"]),
        -(c.get("max_mentions") or 0),
    )


def build_market_story_feed(now=None, limit=FEED_MAX_DEFAULT):
    """오늘 시장의 이야기 피드. Returns {as_of, has_event, summary, meta, total, cards}."""
    now = now or timezone.now()
    since14 = now.date() - datetime.timedelta(days=DAILY_SPIKE_DAYS)
    since30 = now.date() - datetime.timedelta(days=NEW_SEC_DAYS)

    sec = _new_sec_cards(now, since30)
    spike = _daily_spike_group_cards(now, since14)
    steady = _weekly_active_cards(now)

    # steady 에서 이미 사건 카드(SEC·급등 묶음의 모든 쌍)로 나온 페어 제거(사건 우선).
    event_pairs = {frozenset((c["symbol_a"], c["symbol_b"])) for c in sec}
    for g in spike:
        for p in g["pairs"]:
            event_pairs.add(frozenset((p["symbol_a"], p["symbol_b"])))
    steady = [
        c for c in steady
        if frozenset((c["symbol_a"], c["symbol_b"])) not in event_pairs
    ]

    ordered = sorted(sec + spike + steady, key=_sort_key)
    cards = ordered[:limit]
    _enrich_titles(cards)  # 표시 카드만 제목·evidence 조회(A-3·A-6)
    _enrich_relation_lines(cards)  # 관계 종류 한 줄(D-S3-8·serving_layer 축·일괄 조회)

    by_type = {
        "new_sec": sum(1 for c in cards if c["type"] == "new_sec"),
        "daily_spike": sum(1 for c in cards if c["type"] == "daily_spike"),
        "weekly_active": sum(1 for c in cards if c["type"] == "weekly_active"),
    }
    today_et = now.astimezone(_ET).date().isoformat()
    new_today = sum(1 for c in cards if c.get("occurred_on") == today_et)
    has_event = by_type["new_sec"] + by_type["daily_spike"] > 0
    as_of = now.date().isoformat()
    return {
        "as_of": as_of,
        "has_event": has_event,
        "summary": by_type,  # backward compat(유형별 수)
        "meta": {
            "as_of": as_of,
            "new_today": new_today,
            "stories": len(cards),
            "by_type": by_type,
        },
        "total": len(cards),
        "cards": cards,
    }
