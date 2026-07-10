"""
C3 내러티브 볼륨 — 테마 집계 원장 + 게이트 fetch (TH-10, 결정16=A) — 설계 앵커 §2 C3 · v1.2.7.

집계 규칙(§2 v1.2.7 보완): DailyNewsKeyword 키워드(search_terms_en)를 정규화(소문자·공백 정리)
후 테마 키워드 시드(KEYWORD_SECTOR_MAP) **완전 일치** 매칭 → 섹터명 → HeatEntity → 테마×일자
mention_count 합산. 부분·유사도 매칭 금지(정밀도 우선). 전방 축적 + 기존분 소급(외부 3년 백필
금지, 결정16).

게이트(결정13 동형): 유효 diff<26 결측(c3_insufficient_history) / 26≤<60 확장 창
(time_series_expanding) / ≥60 정식(time_series). 상수 26/60 = 결정7/13 체계 병기.
순수함수 heat_components.c3_narrative 재사용(§2 산식·부호 불변).
"""

import logging
from collections import defaultdict
from datetime import date
from typing import Optional

from apps.chain_sight.services.heat_components import c3_narrative, make_component

logger = logging.getLogger(__name__)

C3_EXPAND_MIN = 26   # 결정13 체계 병기
C3_WINDOW_FULL = 60
C3_MA_WINDOW = 20    # §2 "20일 합"

# KEYWORD_SECTOR_MAP 섹터명 → HeatEntity.ref_id(GICS 정본). 비섹터(Crypto/ESG/Geopolitical/
# Macro/Regulation)는 매핑 없음(무시). 11 GICS 전수 커버.
KW_SECTOR_TO_HEAT_ENTITY = {
    "Technology": "Technology",
    "Communication Services": "Communication Services",
    "Healthcare": "Healthcare",
    "Financials": "Financial Services",
    "Consumer Discretionary": "Consumer Cyclical",
    "Consumer Staples": "Consumer Defensive",
    "Materials": "Basic Materials",
    "Energy": "Energy",
    "Industrials": "Industrials",
    "Real Estate": "Real Estate",
    "Utilities": "Utilities",
}


def _normalize(term: str) -> str:
    """소문자 + 공백 정리 (매칭 전처리)."""
    return " ".join(str(term).lower().split())


# 오배정 유발 토큰 제외 훅 (결정17 — 표본 감사로 발견 시 추가). 현재 비어있음.
MATCH_EXCLUDE_TOKENS: frozenset = frozenset()


def match_term_to_sectors(term: str, keyword_map: dict) -> set:
    """
    검색어 → 매칭 섹터명 집합 (결정17 1차 규칙, 순수함수).

    - 단일 단어 시드(공백 없음): 정규화 검색어의 **토큰 완전 일치**(부분 문자열 금지).
    - 다단어 시드(공백 있음): 검색어 문자열에 **구 포함 일치**(공백 경계 자연 확보).
    - 유사도·부분 문자열(단어) 금지. 제외 토큰(MATCH_EXCLUDE_TOKENS)은 단어 매칭에서 배제.
    """
    norm = _normalize(term)
    if not norm:
        return set()
    tokens = set(norm.split()) - MATCH_EXCLUDE_TOKENS
    sectors = set()
    for kw, sec in keyword_map.items():
        if " " in kw:
            if kw in norm:  # 구 포함 일치
                sectors.add(sec)
        elif kw in tokens:  # 토큰 완전 일치
            sectors.add(sec)
    return sectors


def aggregate_theme_news_volume(target_date: Optional[date] = None) -> dict:
    """
    DailyNewsKeyword → ThemeNewsVolume 집계 (멱등). target_date=None 이면 전체 소급.

    각 일자 키워드의 search_terms_en 을 정규화·완전 일치 매칭해 섹터별 카운트 → 테마×일자 upsert.
    """
    from apps.chain_sight.models import HeatEntity, ThemeNewsVolume
    from services.news.models import DailyNewsKeyword
    from services.news.services.keyword_sector_map import KEYWORD_SECTOR_MAP

    entities = {e.ref_id: e for e in HeatEntity.objects.filter(kind="sector")}
    qs = DailyNewsKeyword.objects.exclude(keywords__isnull=True)
    if target_date is not None:
        qs = qs.filter(date=target_date)

    days = written = 0
    for dnk in qs.only("date", "keywords"):
        counts: dict[str, int] = defaultdict(int)
        for kw in dnk.keywords or []:
            if not isinstance(kw, dict):
                continue
            for term in kw.get("search_terms_en") or []:
                for sec in match_term_to_sectors(term, KEYWORD_SECTOR_MAP):
                    ref = KW_SECTOR_TO_HEAT_ENTITY.get(sec)
                    if ref and ref in entities:
                        counts[ref] += 1
        days += 1
        for ref, cnt in counts.items():
            ThemeNewsVolume.objects.update_or_create(
                theme=entities[ref], date=dnk.date, defaults={"mention_count": cnt}
            )
            written += 1

    logger.info("ThemeNewsVolume 집계: days=%d rows_upserted=%d", days, written)
    return {"days": days, "written": written}


def c3_narrative_from_db(
    entity,
    as_of: date,
    expand_min: int = C3_EXPAND_MIN,
    window_full: int = C3_WINDOW_FULL,
    ma_window: int = C3_MA_WINDOW,
) -> dict:
    """ThemeNewsVolume 위 C3 계산 + 결정13 동형 게이트. c3_narrative 재사용 + z_mode."""
    from apps.chain_sight.models import ThemeNewsVolume

    rows = (
        ThemeNewsVolume.objects.filter(theme=entity, date__lte=as_of)
        .order_by("date")
        .values_list("date", "mention_count")
    )
    dates = [d for d, _ in rows]
    counts = [c or 0 for _, c in rows]
    valid = len(dates)

    if valid < expand_min:
        comp = make_component(None, raw=None, missing_reason="c3_insufficient_history")
        comp["z_mode"] = None
        return comp

    # 20일 이동합 시계열 (가용분 부분합)
    series = []
    for i in range(len(counts)):
        lo = max(0, i - ma_window + 1)
        series.append(sum(counts[lo : i + 1]))

    win = min(valid, window_full)
    current = series[-1]
    history = series[-win:-1]
    comp = c3_narrative(current, history, min_n=min(expand_min - 1, len(history)))
    comp["z_mode"] = (
        ("time_series" if valid >= window_full else "time_series_expanding")
        if comp["z"] is not None
        else None
    )
    return comp
