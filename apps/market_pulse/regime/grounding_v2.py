"""SELECT-V2 — L3 그라운딩용 뉴스 선별 v2 (결정론, LLM·외부 API 0).

역할: 이웃일 T의 broad 시장 뉴스(services.news.NewsArticle) → **macro-relevant** 상위 N.
  v1(grounding.py)이 abs(sentiment)+entity_count로 뽑아 "고감정 개별 기업"을 상위에 올린
  품질 한계(D-CL3-QUALITY-LIMIT)를 교정 — 랭킹 주축을 **텍스트 기반 macro 어휘 점수**로 전환.

왜 어휘·규칙(결정 D-SELECT-V2-RULE, 가중합 8.55 vs 하이브리드 7.78 vs 메타우선 4.15):
  STEP0 실측 — AV `topics`/`relevance`는 저장조차 안 됨(provider drop). category는 재수집분
  전부 'company'(분별 불가), sentiment 채움률 재수집 100% vs 기존 51%(불균일). **유일하게
  균일·상시 존재하는 신호 = title+summary 텍스트**(양 구간 ~100%). → 어휘 점수만이 683 전
  구간 균일 적용 + macro-relevance 직격. sentiment/entity는 v1 편향의 원천이라 랭킹 축에서
  제외하고 동점 tie-break으로만 사용.

불변 요건: ①결정론(동일 입력→동일 출력) ②품질 하한(min_score 미달이면 N 미만 허용, 억지 채움
  금지 — REGEN-V2의 why=null 원칙과 접속) ③provenance(score·hits·rank 동반) ④버전 태그.

인터페이스(REGEN-V2 계약): 반환 dict는 v1과 동일 키(id,title,url,source,sentiment_score,
  entity_count,published_at) + v2 추가(score,hits,rank,select_version). context_generator가
  provenance를 id/url/title로 조립하므로 그 3키는 불변 보장.

★is_archived 무필터(D-CL3-ARCHIVE-BLIND) — v1과 동일.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date as date_cls
from typing import Any

SELECT_VERSION = "select_v2.0"

# 캘리브레이션 초안(STEP0 분포 기준, 정밀 튜닝은 샘플 게이트 소관):
#   재수집 일별 볼륨 p50=234·p90=451, macro STRONG 히트 커버일 0~6건 → N=6이면 미달 억지채움 없음.
SELECT_V2_TOP_N = 6         # 최종 상한(macro 헤드라인은 희소 → 6이면 충분·초과 억지채움 0)
SELECT_V2_SOURCE_CAP = 3    # 소스당 상한(v1과 동일, 편중 소스 독점 방지)
SELECT_V2_MIN_SCORE = 1.2   # 품질 하한 — 최소 STRONG-summary(3.0×0.4) 1건 상당. 미달=제외

# ── macro 어휘(계층) — STEP0 오탐 실측 반영(티커/ETF명이 s&p500·nasdaq·gdp 오매치) ──
# STRONG: 명백한 거시 구문(오탐 낮음). MID: 광의 시장/애매어(가드 하에 저가중).
_STRONG_TERMS = [
    r"federal reserve", r"\bfomc\b", r"\bthe fed\b",
    r"fed (?:cut|hike|rais|hold|signal|meet|chair|rate|polic|offic|minutes)",
    r"interest rates?", r"rate cuts?", r"rate hikes?", r"rate decision",
    r"\binflation\b", r"consumer price", r"\bcpi\b", r"\bpce\b",
    r"jobs report", r"nonfarm", r"payrolls?", r"unemployment rate", r"labor market",
    r"treasury (?:yield|bill|note|bond)", r"yield curve", r"bond yield", r"gdp growth",
    r"\brecession\b", r"\btariffs?\b", r"trade war", r"crude oil", r"oil prices?",
    r"central bank", r"jerome powell", r"\bpowell\b", r"\becb\b", r"bank of japan",
    r"\bboj\b", r"soft landing", r"debt ceiling", r"quantitative (?:easing|tightening)",
    r"jobless claims", r"retail sales", r"\bfiscal\b", r"monetary policy",
]
_MID_TERMS = [
    r"stock market", r"wall street", r"\bequities\b", r"bond market", r"u\.?s\.? dollar",
    r"dollar index", r"10-year", r"market (?:rally|selloff|sell-off|rout)",
    r"\bvolatility\b", r"\bvix\b", r"major indices", r"\bbull market\b", r"\bbear market\b",
    r"dow (?:jones|hits|falls|rises)", r"s&p 500 (?:hits|falls|rises|closes|gains|drops)",
]
# 티커/ETF 보일러플레이트 — 매치 시 macro 점수 중화(개별종목 잡보의 index-name 오매치 제거)
_TICKER_NOISE = re.compile(
    r"NASDAQ:|NYSE:|NYSEARCA:|\bETF\b|:[A-Z]{1,6}\b|price target|"
    r"\bstock (?:right )?(?:price|forecast|analysis)\b|\bbuy or sell\b",
    re.IGNORECASE,
)
_TICKER_NOISE_PENALTY = 0.3  # 티커 보일러플레이트 매치 시 곱 페널티

_RX_STRONG = re.compile("|".join(_STRONG_TERMS), re.IGNORECASE)
_RX_MID = re.compile("|".join(_MID_TERMS), re.IGNORECASE)

_W_STRONG_TITLE, _W_STRONG_SUMMARY = 3.0, 1.2
_W_MID_TITLE, _W_MID_SUMMARY = 1.5, 0.6

# 소스 가중(곱) — PR/신디케이션 감점, 품질 와이어 소폭 가점. macro 점수의 종속 조정.
_SOURCE_WEIGHT = {
    "pr newswire": 0.7, "globenewswire": 0.7, "globe newswire": 0.7, "business wire": 0.7,
    "accesswire": 0.7, "newsfile": 0.7, "prnewswire": 0.7, "stock titan": 0.8,
    "reuters": 1.15, "bloomberg": 1.15, "cnbc": 1.15, "the wall street journal": 1.15,
    "wall street journal": 1.15, "financial times": 1.15, "associated press": 1.1,
    "marketwatch": 1.1, "the economist": 1.15, "barron's": 1.1,
}


def _uniq_hits(rx: re.Pattern, text: str) -> list[str]:
    """정규화 매치의 유니크 소문자 히트(결정론 정렬)."""
    return sorted({m.group(0).lower() for m in rx.finditer(text)})


def macro_score(title: str | None, summary: str | None) -> tuple[float, list[str]]:
    """제목+요약의 macro-relevance 결정론 점수 + 히트 어휘. 순수함수(테스트 가능).

    점수 = Σ STRONG(제목 3.0·요약 1.2) + Σ MID(제목 1.5·요약 0.6), 어휘당 1회.
    티커/ETF 보일러플레이트가 제목에 있으면 곱 페널티(0.3)로 개별종목 잡보 오매치 중화.
    """
    t = title or ""
    s = summary or ""
    st_title = _uniq_hits(_RX_STRONG, t)
    st_summ = [h for h in _uniq_hits(_RX_STRONG, s) if h not in st_title]
    mid_title = _uniq_hits(_RX_MID, t)
    mid_summ = [h for h in _uniq_hits(_RX_MID, s) if h not in mid_title]

    score = (
        _W_STRONG_TITLE * len(st_title) + _W_STRONG_SUMMARY * len(st_summ)
        + _W_MID_TITLE * len(mid_title) + _W_MID_SUMMARY * len(mid_summ)
    )
    if score > 0 and _TICKER_NOISE.search(t):
        score *= _TICKER_NOISE_PENALTY

    hits = sorted(set(st_title) | set(st_summ) | set(mid_title) | set(mid_summ))
    return round(score, 4), hits


def _norm_title(title: str | None) -> str:
    """near-dup 접기용 제목 정규화: NFKC·소문자·영숫자만·공백정리·앞 12단어."""
    t = unicodedata.normalize("NFKC", title or "").lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    words = t.split()
    return " ".join(words[:12])


def _source_weight(source: str | None) -> float:
    return _SOURCE_WEIGHT.get((source or "").strip().lower(), 1.0)


def rank_headlines_v2(
    candidates: list[dict[str, Any]],
    *,
    n: int = SELECT_V2_TOP_N,
    source_cap: int = SELECT_V2_SOURCE_CAP,
    min_score: float = SELECT_V2_MIN_SCORE,
) -> list[dict[str, Any]]:
    """결정론 macro 선별. candidate = {id,title,url,source,summary,sentiment_score,entity_count,published_at}.

    ① macro_score×source_weight 산정 → min_score 미달 제외(품질 하한, 억지채움 없음)
    ② near-dup 제목 접기(최고점 유지, 동점=str(id) 최소)
    ③ 정렬: score → entity_count → recency → str(id) (macro가 주축, 나머지 tie-break)
    ④ source_cap greedy top-N. 각 결과에 score·hits·rank·select_version 부착.
    """
    scored: list[tuple[float, list[str], dict[str, Any]]] = []
    for c in candidates:
        base, hits = macro_score(c.get("title"), c.get("summary"))
        if base <= 0:
            continue
        final = round(base * _source_weight(c.get("source")), 4)
        if final < min_score:
            continue
        scored.append((final, hits, c))

    # ② near-dup 접기: 정규화 제목당 최고 final(동점=str(id) 최소) 1건
    best: dict[str, tuple[float, list[str], dict[str, Any]]] = {}
    for final, hits, c in scored:
        key = _norm_title(c.get("title"))
        cur = best.get(key)
        if cur is None or (final, ) > (cur[0], ) or (
            final == cur[0] and str(c.get("id", "")) < str(cur[2].get("id", ""))
        ):
            best[key] = (final, hits, c)
    deduped = list(best.values())

    # ③ 정렬(내림차순): final → entity_count → recency → str(id)
    def sort_key(item: tuple[float, list[str], dict[str, Any]]) -> tuple:
        final, _hits, c = item
        ec = int(c.get("entity_count") or 0)
        pub = c.get("published_at")
        pub_key = pub.isoformat() if hasattr(pub, "isoformat") else str(pub or "")
        return (final, ec, pub_key, str(c.get("id", "")))

    ordered = sorted(deduped, key=sort_key, reverse=True)

    # ④ source_cap greedy top-N + provenance 부착
    picked: list[dict[str, Any]] = []
    per_source: dict[str, int] = {}
    for rank_idx, (final, hits, c) in enumerate(ordered):
        src = c.get("source") or ""
        if per_source.get(src, 0) >= source_cap:
            continue
        out = dict(c)
        out.pop("summary", None)  # 랭킹 재료였을 뿐, 반환 스키마에는 불포함(v1 호환)
        out["score"] = final
        out["hits"] = hits
        out["rank"] = len(picked) + 1
        out["select_version"] = SELECT_VERSION
        picked.append(out)
        per_source[src] = per_source.get(src, 0) + 1
        if len(picked) >= n:
            break
    return picked


def fetch_day_candidates_v2(target_date: date_cls) -> list[dict[str, Any]]:
    """T의 그날 뉴스 후보(is_archived 무필터) + entity_count + summary(어휘 점수용).

    v1 fetch와 동일 쿼리 + `summary` 추가(어휘 점수 재료). 창 = published_at__date == target_date.
    """
    from django.db.models import Count

    from services.news.models import NewsArticle

    rows = (
        NewsArticle.objects.filter(published_at__date=target_date)  # is_archived 무필터
        .annotate(entity_count=Count("entities"))
        .values(
            "id", "title", "url", "source", "summary",
            "sentiment_score", "entity_count", "published_at",
        )
    )
    return list(rows)


def select_grounding_v2(
    target_date: date_cls,
    *,
    n: int = SELECT_V2_TOP_N,
    source_cap: int = SELECT_V2_SOURCE_CAP,
    min_score: float = SELECT_V2_MIN_SCORE,
) -> list[dict[str, Any]]:
    """T의 그날 후보 페치 → macro 결정론 선별 상위 N. macro 신호 없으면 빈 리스트(억지 생성 금지)."""
    return rank_headlines_v2(
        fetch_day_candidates_v2(target_date), n=n, source_cap=source_cap, min_score=min_score
    )
