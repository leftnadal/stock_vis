"""
코어-위성 EventGroup 파이프라인 (M2 v1.1 Phase 1).

scratchpad 하니스(검증됨)의 jaccard 코어-위성 로직을 prod ORM으로 이식.
입력 전부 prod 테이블에서 read-only로 읽음:
  - co-mention 엣지: ChainNewsEvent(symbol + co_mentioned_symbols + published_at)
  - sectors/cohesion: stocks.Stock.sector / stocks.DailyPrice
  - 13F 공동보유(가산 신호): serverless.InstitutionalHolding

confidence = 다중신호 가산 weight: jaccard 1-hop 강도 × (1 + 13F 가산) × (1 + 코어연결 가산).
13F는 **가산만**(없어도 안 깎음 — 인덱스펀드 편향이 거절로 작동하지 않게).
"""

import logging
import math
from collections import defaultdict
from datetime import date
from itertools import combinations

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)

# 확정 파라미터 (하니스 동치)
DEFAULT_WINDOW_DAYS = 21  # as_of 기준 co-mention 집계 윈도우(일). window 밖은 그룹핑서 제외.
DEFAULT_CORE_THR = 0.2
DEFAULT_SAT_THR = 0.05
DEFAULT_MIN_MEMBERS = 3

# confidence 가산 계수
W_COHOLD = 0.1       # 13F 공유기관수당 가산
W_CORECONN = 0.15    # 추가 코어 연결당 가산


# ── 입력 레이어 (prod ORM) ───────────────────────────────────────────
def _build_base(window_days=DEFAULT_WINDOW_DAYS):
    """ChainNewsEvent → 쌍별 co_count + 종목별 doc_count + as_of.

    EventGroup은 stocks.Stock FK이므로 co_mentioned_symbols 중 Stock 미존재
    심볼은 클러스터링 단계에서 제외(적재 시 FK-skip로 코어가 축소되는 것 방지).

    window_days: as_of(최신 유효 이벤트일) 기준 이 일수 이내
    (pub.date() >= as_of - window_days)만 co/doc 카운팅. window 밖(오래된) co-mention은
    그룹핑 희석(stale 뿌리) 방지 위해 제외한다. as_of(max_d)는 window 적용 **전** 전량
    유효 2+종목 이벤트 기준 max라 윈도우 축소와 무관하게 고정된다.
    """
    from datetime import timedelta

    from apps.chain_sight.models.news_event import ChainNewsEvent
    from packages.shared.stocks.models import Stock

    valid = set(Stock.objects.values_list("symbol", flat=True))
    # 1패스: 유효 2+종목 이벤트만 정제 수집 + as_of(전량 max) 산출
    events = []
    max_d = None
    rows = ChainNewsEvent.objects.filter(is_duplicate=False).values_list(
        "symbol_id", "co_mentioned_symbols", "published_at"
    )
    for symbol_id, co, pub in rows:
        syms = sorted({symbol_id, *(co or [])})
        syms = [s for s in syms if s and s in valid]
        if len(syms) < 2:
            continue
        d = pub.date()
        max_d = d if max_d is None or d > max_d else max_d
        events.append((syms, d))

    # 2패스: window 적용(as_of - window_days 이내)만 co/doc 카운팅
    lower = None if max_d is None else max_d - timedelta(days=window_days)
    co_count = defaultdict(int)
    occ = defaultdict(list)
    doc_count = defaultdict(int)
    N = 0
    for syms, d in events:
        if lower is not None and d < lower:
            continue
        N += 1
        for s in syms:
            doc_count[s] += 1
        for a, b in combinations(syms, 2):
            co_count[(a, b)] += 1
            occ[(a, b)].append(d)
    return co_count, doc_count, occ, N, max_d


def _jaccard_weights(co_count, doc_count):
    return {
        (a, b): co / (doc_count[a] + doc_count[b] - co)
        for (a, b), co in co_count.items()
    }


def _cohold_map():
    """serverless.InstitutionalHolding → {(a,b): 공유 기관 수}. 없으면 빈 dict."""
    try:
        from services.serverless.models import InstitutionalHolding
    except Exception:
        return {}
    holdings = defaultdict(set)
    for sym, cik in InstitutionalHolding.objects.values_list(
        "stock_symbol", "institution_cik"
    ):
        holdings[sym].add(cik)
    cohold = {}
    syms = sorted(holdings)
    for a, b in combinations(syms, 2):
        sh = len(holdings[a] & holdings[b])
        if sh:
            cohold[(a, b)] = sh
    return cohold


def _cohold_count(cohold, a, b):
    return cohold.get((a, b) if a < b else (b, a), 0)


# ── 코어-위성 클러스터링 (하니스 동치) ──────────────────────────────
def compute_event_groups(
    window_days=DEFAULT_WINDOW_DAYS,
    core_thr=DEFAULT_CORE_THR,
    sat_thr=DEFAULT_SAT_THR,
    min_members=DEFAULT_MIN_MEMBERS,
):
    """코어-위성 그룹 계산(메모리). DB 미투입 — 적재/동치검증 공용."""
    co_count, doc_count, occ, N, as_of = _build_base(window_days)
    weights = _jaccard_weights(co_count, doc_count)
    cohold = _cohold_map()

    # 코어: jaccard ≥ core_thr 연결요소 + ≥min_members
    Gcore = nx.Graph()
    for (a, b), w in weights.items():
        if w >= core_thr:
            Gcore.add_edge(a, b, weight=w)
    core_groups = [
        sorted(c) for c in nx.connected_components(Gcore) if len(c) >= min_members
    ]

    # 전체 jaccard 인접 (위성 확장용)
    Gfull = nx.Graph()
    for (a, b), w in weights.items():
        Gfull.add_edge(a, b, weight=w)
    in_core = {s: gi for gi, g in enumerate(core_groups) for s in g}

    # 위성: 코어 멤버의 이웃 중 코어 미소속 + [sat_thr, core_thr)
    sat_best = {}  # sym -> (gi, anchor, weight)
    sat_coreconn = defaultdict(lambda: defaultdict(int))  # sym -> {gi: 연결수}
    for gi, g in enumerate(core_groups):
        for cm in g:
            if cm not in Gfull:
                continue
            for nb in Gfull[cm]:
                if nb in in_core:
                    continue
                w = Gfull[cm][nb]["weight"]
                if w < sat_thr or w >= core_thr:
                    continue
                sat_coreconn[nb][gi] += 1
                if nb not in sat_best or w > sat_best[nb][2]:
                    sat_best[nb] = (gi, cm, w)

    groups = []
    for gi, core in enumerate(core_groups):
        # 코어 confidence = 그룹 내 가중 차수
        members = []
        for s in core:
            wdeg = sum(
                Gcore[s][n]["weight"] for n in Gcore[s] if n in core
            ) if s in Gcore else 0.0
            members.append({
                "symbol": s, "role": "core",
                "edge_confidence": round(wdeg, 4),
                "anchor_symbol": "", "cohold_institutions": 0,
                "evidence": {"core_wdegree": round(wdeg, 4)},
            })
        leader = max(members, key=lambda m: m["edge_confidence"])["symbol"] if members else ""
        # 위성
        sats = []
        for sym, (g2, anc, w) in sat_best.items():
            if g2 != gi:
                continue
            cc = _cohold_count(cohold, anc, sym)
            coreconn = sat_coreconn[sym][gi]
            conf = w * (1 + W_COHOLD * cc) * (1 + W_CORECONN * (coreconn - 1))
            sats.append({
                "symbol": sym, "role": "satellite",
                "edge_confidence": round(conf, 4),
                "anchor_symbol": anc, "cohold_institutions": cc,
                "evidence": {
                    "jaccard_1hop": round(w, 4),
                    "anchor": anc, "core_connections": coreconn,
                    "cohold_institutions": cc,
                },
            })
        sats.sort(key=lambda x: -x["edge_confidence"])
        all_syms = core + [s["symbol"] for s in sats]
        groups.append({
            "core": core,
            "leader": leader,
            "members": members + sats,
            "core_count": len(core),
            "member_count": len(all_syms),
            "confidence": round(
                float(np.mean([m["edge_confidence"] for m in members])) if members else 0.0, 4
            ),
            # cohesion = 코어 멤버 기준(게이팅 임계 0.2의 캘리브레이션 기준)
            "cohesion": _pairwise_cohesion(core),
            "breadth": _group_breadth(all_syms),
        })
    # TF-IDF 코어 이름 부여 (corpus = 전 그룹 코어 텍스트)
    _attach_core_names(groups)
    return {"groups": groups, "as_of": as_of, "params": {
        "window_days": window_days, "core_thr": core_thr,
        "sat_thr": sat_thr, "min_members": min_members,
    }}


# ── 그룹 지표 (DailyPrice) ───────────────────────────────────────────
def _returns(closes):
    items = sorted(closes.items())
    if len(items) < 2:
        return None
    px = np.array([p for _, p in items], dtype=float)
    return dict(zip([d for d, _ in items][1:], np.diff(px) / px[:-1]))


_PRICE_CACHE = {}


def _load_prices(symbols):
    from packages.shared.stocks.models import DailyPrice

    need = [s for s in symbols if s not in _PRICE_CACHE]
    if need:
        tmp = defaultdict(dict)
        for sym, d, c in DailyPrice.objects.filter(stock_id__in=need).values_list(
            "stock_id", "date", "close_price"
        ):
            if c is not None:
                tmp[sym][d.isoformat()] = float(c)
        for s in need:
            _PRICE_CACHE[s] = _returns(tmp[s]) if s in tmp else None
    return {s: _PRICE_CACHE[s] for s in symbols if _PRICE_CACHE.get(s)}


def _pairwise_cohesion(symbols, min_overlap=20):
    series = _load_prices(symbols)
    syms = list(series)
    if len(syms) < 2:
        return None
    cors = []
    for a, b in combinations(syms, 2):
        common = sorted(set(series[a]) & set(series[b]))
        if len(common) < min_overlap:
            continue
        va = np.array([series[a][d] for d in common])
        vb = np.array([series[b][d] for d in common])
        if va.std() == 0 or vb.std() == 0:
            continue
        cors.append(np.corrcoef(va, vb)[0, 1])
    return round(float(np.mean(cors)), 4) if cors else None


def _group_breadth(symbols, min_members=2):
    series = _load_prices(symbols)
    if len(series) < min_members:
        return None
    all_dates = set()
    for s in series.values():
        all_dates |= set(s)
    agrees = []
    for d in all_dates:
        vals = [series[s][d] for s in series if d in series[s]]
        if len(vals) < min_members:
            continue
        up = sum(1 for v in vals if v > 0)
        agrees.append(max(up / len(vals), 1 - up / len(vals)))
    return round(float(np.mean(agrees)), 4) if agrees else None


# ── TF-IDF 코어 이름 (코어 멤버 등장 뉴스 텍스트) ────────────────────
_NAME_STOP = set("""a an the of in on at to for and or but with by from as is are was were be been
being this that these those it its their his her our your they them we you i he she has have had
do does did will would can could should may might must not no nor so than then up down out over
under more most less least very just also about into onto off above below after before during
inc corp co ltd llc plc group holdings holding company companies share shares stock stocks
position decreases increases reduces raises buys sells sold buy sell new report reports reported
q1 q2 q3 q4 quarter third second first fourth year years market markets price prices target
analyst analysts rating ratings says said according amid via per pct percent value stake
million billion trillion fund management asset llp lp ag sa nv systems technologies""".split())


def _name_tokens(text, member_syms):
    import re

    text = (text or "").lower()
    text = re.sub(r"\$[a-z]+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    member_lower = {m.lower() for m in member_syms}
    return [t for t in text.split()
            if len(t) >= 3 and t not in _NAME_STOP and t not in member_lower]


def _attach_core_names(groups):
    """그룹별 코어 멤버 등장 뉴스 텍스트로 TF-IDF 이름 후보 부여(N=2/3 + 원시 텀5).

    엣지: 코어 1명/텍스트 부족 → name_candidates 빈 dict, name "—".
    """
    import math
    from collections import Counter

    from apps.chain_sight.models.news_event import ChainNewsEvent

    # 전 코어 멤버 합집합으로 이벤트 텍스트 1회 로드
    all_core = set()
    for g in groups:
        all_core |= set(g["core"])
    # 심볼별 등장 이벤트 텍스트 모음
    sym_texts = defaultdict(list)
    for symbol_id, co, title, summary in ChainNewsEvent.objects.filter(
        is_duplicate=False
    ).values_list("symbol_id", "co_mentioned_symbols", "title", "summary"):
        syms = {symbol_id, *(co or [])} & all_core
        if not syms:
            continue
        txt = f"{title or ''} {summary or ''}"
        for s in syms:
            sym_texts[s].append(txt)

    # 그룹별 코어 토큰 카운트
    gtok = []
    for g in groups:
        cnt = Counter()
        cset = set(g["core"])
        for s in g["core"]:
            for txt in sym_texts.get(s, []):
                cnt.update(_name_tokens(txt, cset))
        gtok.append(cnt)

    Ngrp = len(gtok) or 1
    df = Counter()
    for cnt in gtok:
        for t in cnt:
            df[t] += 1

    for g, cnt in zip(groups, gtok):
        if len(g["core"]) < 1 or not cnt:
            g["name_candidates"] = {}
            g["auto_name"] = "—"
            continue
        gtotal = sum(cnt.values()) or 1
        scores = {}
        for t, f in cnt.items():
            if Ngrp >= 3 and df[t] >= Ngrp:  # 충분한 corpus에서만 보편텀 제거
                continue
            idf = math.log(Ngrp / df[t]) if Ngrp >= 3 else 1.0
            scores[t] = (f / gtotal) * idf
        top = [t for t, _ in sorted(scores.items(), key=lambda x: -x[1])[:5]]
        if not top:  # 폴백: raw TF 상위(단일 그룹 corpus 등)
            top = [t for t, _ in cnt.most_common(5)]
        if not top:
            g["name_candidates"] = {}
            g["auto_name"] = "—"
            continue
        g["name_candidates"] = {
            "n2": " ".join(top[:2]),
            "n3": " ".join(top[:3]),
            "terms": top,
        }
        g["auto_name"] = g["name_candidates"]["n3"]


# ── 쉐도우 적재 (EventGroup/GroupMembership) ─────────────────────────
def _slugify(leader, gi):
    base = "".join(ch for ch in (leader or "grp").lower() if ch.isalnum())
    return f"news-{base or 'grp'}-{gi}"


COHESION_GATE = 0.2  # 확정: 코어 cohesion < 0.2 = 저신뢰 잡탕 후보 → is_hidden


def load_event_groups(cohesion_gate=COHESION_GATE, **params):
    """
    파이프라인 실행 → EventGroup/GroupMembership 적재 (Phase 1 덮어쓰기 모드).

    기존 theme_tags 소비자 무영향 — 새 테이블에만 쓴다(쉐도우).
    게이팅(플래그, 드롭 아님): 코어 cohesion < cohesion_gate(또는 산출불가) → is_hidden=True.
    그룹명 = 코어 TF-IDF 이름(n3), 후보는 name_candidates에 보존.

    Returns: 적재 요약 dict(게이트 분포 포함).
    """
    from django.db import transaction

    from apps.chain_sight.models.event_group import EventGroup, GroupMembership
    from packages.shared.stocks.models import Stock

    _PRICE_CACHE.clear()
    result = compute_event_groups(**params)
    groups = result["groups"]
    as_of = result["as_of"]
    valid_symbols = set(Stock.objects.values_list("symbol", flat=True))

    hidden = gated_low = gated_none = 0
    cohesions = []
    with transaction.atomic():
        # Phase 1 덮어쓰기: 기존 쉐도우 전량 교체 (새 테이블만 — 기존 reader 무영향)
        GroupMembership.objects.all().delete()
        EventGroup.objects.all().delete()
        for gi, g in enumerate(groups):
            # 게이팅(플래그): 코어 cohesion < gate 또는 산출불가 → is_hidden (드롭 아님)
            coh = g["cohesion"]
            if coh is not None:
                cohesions.append(coh)
            if coh is None:
                is_hidden = True
                gated_none += 1
            elif coh < cohesion_gate:
                is_hidden = True
                gated_low += 1
            else:
                is_hidden = False
            if is_hidden:
                hidden += 1
            auto_name = g.get("auto_name", "—")
            eg = EventGroup.objects.create(
                name=auto_name if auto_name != "—" else f"{g['leader']} 외 {g['member_count']-1}",
                slug=_slugify(g["leader"], gi),
                source="news_jaccard",
                confidence=g["confidence"],
                window_days=result["params"]["window_days"],
                cohesion=g["cohesion"],
                breadth=g["breadth"],
                name_candidates=g.get("name_candidates", {}),
                member_count=g["member_count"],
                core_count=g["core_count"],
                is_hidden=is_hidden,
                as_of_date=as_of,
            )
            ms = []
            for m in g["members"]:
                if m["symbol"] not in valid_symbols:
                    continue  # Stock에 없는 심볼은 FK 불가 → 스킵
                ms.append(GroupMembership(
                    group=eg, symbol_id=m["symbol"], role=m["role"],
                    edge_confidence=m["edge_confidence"],
                    anchor_symbol=m["anchor_symbol"],
                    cohold_institutions=m["cohold_institutions"],
                    evidence=m["evidence"],
                ))
            GroupMembership.objects.bulk_create(ms)
            # FK 스킵으로 멤버수 변동 시 보정
            actual = len(ms)
            if actual != eg.member_count:
                eg.member_count = actual
                eg.core_count = sum(1 for x in ms if x.role == "core")
                eg.save(update_fields=["member_count", "core_count"])

    cohesions.sort()
    def _pct(p):
        return round(cohesions[min(len(cohesions) - 1, int(p * len(cohesions)))], 3) if cohesions else None
    return {
        "groups": len(groups),
        "hidden": hidden,
        "kept": len(groups) - hidden,
        "gated_low_cohesion": gated_low,
        "gated_no_cohesion": gated_none,
        "cohesion_gate": cohesion_gate,
        "cohesion_p10_p50_p90": [_pct(0.1), _pct(0.5), _pct(0.9)],
        "named": sum(1 for g in groups if g.get("auto_name", "—") != "—"),
        "total_members": GroupMembership.objects.count(),
        "as_of": str(as_of),
    }
