"""
C2b 발행 신호 파이프라인 (TH-3) — FMP filings/IPO → ThemeFilingCount.

설계서 theme_heat_design.md v1.2.1 §5.2 (재정의판):
- C2b = [기상장사 2차발행: 424B5 90일 건수 z] + [신규 공급: IPO 캘린더 90일 건수 z] 의 평균.
- S-1/424B4 는 폐기(symbol 결측 60~62% = IPO 이전 기업). 기상장사 증자 = S-3 선반등록 +
  424B5 경로. 424B2(은행 구조화상품·MTN)는 제외 확정.
- 본문 파싱 아님 — 폼타입·날짜·심볼 카운팅만.

수집 규칙 (프로브 실측):
1. form-type 필터는 prefix 매칭 → 소비 측 formType **정확 일치 자체 필터** 필수.
2. 응답 ~100건 캡 → 페이지네이션 가정 금지, **일 단위 날짜 창 순회**(424B5 일 26~40건).
3. IPO 캘린더 = NYSE/NASDAQ **거래소 필터** (OTC·해외 2% 노이즈 제거).
4. dedup_key = hash(symbol, cik, accession) — accession 은 link 필드에 내포.

실행 원칙: 장기 수집은 **전경 블로킹** 배치(백그라운드 금지). 멱등 upsert.
"""

import hashlib
import logging
import re
from datetime import date, timedelta
from typing import Any, Iterable, Optional

from apps.chain_sight.models import ThemeFilingCount

logger = logging.getLogger(__name__)

# ── 폼/마커 상수 (§5.2) ──
FORM_424B5 = "424B5"          # 기상장사 2차발행 (시즌드) — 정확 일치만
FORM_IPO = "IPO"              # IPO 캘린더 이벤트 마커 (폼타입 아님)

# IPO 거래소 필터 (§5.2-3) — NYSE/NASDAQ 계열만 (변형 접두 허용)
IPO_EXCHANGE_PREFIXES = ("NYSE", "NASDAQ", "NGS", "NMS", "NCM")

_ACCESSION_RE = re.compile(r"(\d{10}-\d{2}-\d{6})")


# ────────────────────────────── 공통 (dedup / 매핑) ──────────────────────────────
def extract_accession(link: str) -> str:
    """link(.../{accession}-index.htm)에서 accession 번호 추출. 없으면 link 원문 폴백."""
    if not link:
        return ""
    m = _ACCESSION_RE.search(link)
    return m.group(1) if m else link


def build_filing_dedup_key(symbol: str, cik: str, accession: str) -> str:
    """§6.5 dedup_key = sha256(symbol, cik, accession). 64-hex = varchar(64) 정합."""
    parts = [str(symbol or "").upper(), str(cik or ""), str(accession or "")]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _upsert_filing(
    symbol: str, filing_date: str, form_type: str, dedup_key: str, exchange: str = ""
) -> bool:
    """dedup_key 멱등 upsert. 생성 시 True."""
    _, created = ThemeFilingCount.objects.update_or_create(
        dedup_key=dedup_key,
        defaults={
            "symbol": (symbol or "").upper()[:16],
            "filing_date": filing_date,
            "form_type": (form_type or "")[:16],
            "exchange": (exchange or "")[:16],  # varchar(16) — 'NASDAQ Global Select' 등 절단
            "source": ThemeFilingCount.SOURCE_FMP,
        },
    )
    return created


# ────────────────────────────── 424B5 수집 (일 단위 창 순회) ──────────────────────────────
def collect_424b5_for_day(client, day: date) -> dict:
    """
    하루치 424B5 수집. 정확 일치 필터(§5.2-1) 후 멱등 upsert.

    반환 = {fetched, exact, created, skipped_form, skipped_no_symbol}.
    """
    iso = day.isoformat()
    rows = client.get_sec_filings_by_form_type(FORM_424B5, iso, iso)
    fetched = len(rows)
    created = exact = skipped_form = skipped_no_symbol = 0
    for r in rows:
        # 정확 일치 필터 — prefix 오염(424B5 외 변형) 차단
        if r.get("formType") != FORM_424B5:
            skipped_form += 1
            continue
        exact += 1
        symbol = str(r.get("symbol") or "").upper()
        if not symbol:
            # symbol 결측분(~10%)은 카운트 제외 + 결손 집계 (귀속 불가 침묵 유입 방지, §5.2 G3)
            skipped_no_symbol += 1
            continue
        cik = str(r.get("cik") or "")
        accession = extract_accession(str(r.get("link") or r.get("finalLink") or ""))
        fdate = str(r.get("filingDate") or "")[:10] or iso
        dedup_key = build_filing_dedup_key(symbol, cik, accession)
        created += _upsert_filing(symbol, fdate, FORM_424B5, dedup_key)
    return {
        "fetched": fetched,
        "exact": exact,
        "created": created,
        "skipped_form": skipped_form,
        "skipped_no_symbol": skipped_no_symbol,
    }


def collect_424b5_range(client, from_date: date, to_date: date, log_fn=None) -> dict:
    """
    [from_date, to_date] 일 단위 창 순회 424B5 수집 (전경 블로킹). 멱등.

    페이지네이션 가정 금지 — 하루당 1콜(424B5 일 26~40건 = 100 캡 비접촉). 멱등이라
    재개 안전(중단 시 --from 재지정). 진행은 log_fn 로 주기 보고.
    """
    agg = {"days": 0, "fetched": 0, "exact": 0, "created": 0,
           "skipped_form": 0, "skipped_no_symbol": 0}
    cursor = from_date
    while cursor <= to_date:
        res = collect_424b5_for_day(client, cursor)
        agg["days"] += 1
        for k in ("fetched", "exact", "created", "skipped_form", "skipped_no_symbol"):
            agg[k] += res[k]
        if log_fn and agg["days"] % 30 == 0:
            log_fn(f"  … {cursor} (누적 created={agg['created']}, no_symbol={agg['skipped_no_symbol']})")
        cursor += timedelta(days=1)
    return agg


# ────────────────────────────── IPO 수집 (범위 + 거래소 + 진성 운영기업 필터) ──────────────────────────────
def _exchange_ok(exchange: str) -> bool:
    """NYSE/NASDAQ 계열만 (§5.2-3)."""
    ex = (exchange or "").upper()
    return any(ex.startswith(p) for p in IPO_EXCHANGE_PREFIXES)


# 진성 운영기업 IPO 모집단 정의 (위생 점검 2026-07-08 실측 반영):
#   C2b IPO 레그 모집단 = NYSE/NASDAQ **진성 운영기업 IPO** — SPAC 블랭크체크 셸 ·
#   유닛/워런트/권리 파생증권 · ETF/펀드 상장을 제외한 실제 신규 지분 공급만.
# 실측(06-15~07-02 103건): "Acquisition Corp" SPAC 셸 + 그 Units(U)/Warrants(W)/
# Rights(R) 파생 + First Eagle/DEFIANCE ETF 다수 혼입 → 신규 공급 신호 오염.
_IPO_NAME_EXCLUDE = re.compile(
    # "acquisition"(블랭크체크 SPAC 관용어 — 'Aeon Acquisition I Corp.'처럼 사이 숫자/로마자
    # 삽입형도 회수) · blank check · 파생증권 서술어 · ETF/펀드.
    r"(\bacquisition\b|blank check|"
    r"\bwarrants?\b|\brights?\b|\bunits?\b|\betf\b|\bfund\b)",
    re.IGNORECASE,
)
# SPAC 파생 심볼 접미(유닛 U/UN·워런트 W/WS·권리 R/RT) — 이름에 표기 없는 파생(예: IQMXW)
# 회수. len≥5 로 짧은 진성 티커(COPR 4자 등) 오탐 방지.
_IPO_SYMBOL_DERIVATIVE = re.compile(r"^[A-Z]{3,}(UN|WS|RT|U|W|R)$")


def is_genuine_operating_ipo(row: dict) -> bool:
    """진성 운영기업 IPO 여부. SPAC 셸·파생증권·ETF/펀드 제외."""
    name = str(row.get("company") or row.get("name") or "")
    symbol = str(row.get("symbol") or "").upper()
    if _IPO_NAME_EXCLUDE.search(name):
        return False
    if len(symbol) >= 5 and _IPO_SYMBOL_DERIVATIVE.match(symbol):
        return False
    return True


def collect_ipos_range(client, from_date: date, to_date: date) -> dict:
    """
    IPO 캘린더 범위 수집 + 거래소 필터(§5.2-3) + **진성 운영기업 필터** + 멱등 upsert.

    모집단 = NYSE/NASDAQ 진성 운영기업 IPO (SPAC 셸·유닛/워런트/권리·ETF/펀드 제외).
    dedup_key = hash(symbol, cik='', date) — IPO 는 accession 부재라 date 로 대체.
    """
    rows = client.get_ipos_calendar(from_date.isoformat(), to_date.isoformat())
    fetched = len(rows)
    created = skipped_exchange = skipped_no_symbol = skipped_non_operating = 0
    for r in rows:
        symbol = str(r.get("symbol") or "").upper()
        if not symbol:
            skipped_no_symbol += 1
            continue
        exchange = str(r.get("exchange") or r.get("exchangeShortName") or "")
        if not _exchange_ok(exchange):
            skipped_exchange += 1
            continue
        if not is_genuine_operating_ipo(r):
            skipped_non_operating += 1
            continue
        fdate = str(r.get("date") or "")[:10]
        if not fdate:
            continue
        dedup_key = build_filing_dedup_key(symbol, "", fdate)
        created += _upsert_filing(symbol, fdate, FORM_IPO, dedup_key, exchange=exchange)
    return {
        "fetched": fetched,
        "created": created,
        "skipped_exchange": skipped_exchange,
        "skipped_no_symbol": skipped_no_symbol,
        "skipped_non_operating": skipped_non_operating,
    }


# ────────────────────────────── C2b 집계 (90일 건수 + z 시계열) ──────────────────────────────
def count_filings_90d(
    symbols: Iterable[str], as_of: date, form_type: str, window_days: int = 90
) -> int:
    """트레일링 window 내 특정 폼타입 건수 (심볼 = 스냅샷 모집단)."""
    start = as_of - timedelta(days=window_days)
    return ThemeFilingCount.objects.filter(
        symbol__in=[s.upper() for s in symbols],
        form_type=form_type,
        filing_date__gt=start,
        filing_date__lte=as_of,
    ).count()


def _count_series(
    symbols: list[str], as_of: date, form_type: str,
    window_days: int, lookback_days: int, step_days: int,
) -> tuple[Optional[int], list[Optional[int]]]:
    """
    (current_count, history_count_series) — as_of window 건수 + 과거 스텝별 window 건수.

    ThemeFilingCount 를 1회 로드 후 in-memory 로 window 슬라이싱 (쿼리 N+1 회피).
    """
    earliest = as_of - timedelta(days=lookback_days + window_days)
    dates = list(
        ThemeFilingCount.objects.filter(
            symbol__in=[s.upper() for s in symbols],
            form_type=form_type,
            filing_date__gt=earliest,
            filing_date__lte=as_of,
        ).values_list("filing_date", flat=True)
    )

    def _count_at(anchor: date) -> int:
        lo = anchor - timedelta(days=window_days)
        return sum(1 for d in dates if lo < d <= anchor)

    history: list[Optional[int]] = []
    cursor = as_of - timedelta(days=lookback_days)
    while cursor < as_of:
        history.append(_count_at(cursor))
        cursor += timedelta(days=step_days)
    current = _count_at(as_of)
    return current, history


def c2b_from_db(
    symbols: Iterable[str],
    as_of: date,
    window_days: int = 90,
    lookback_days: int = 365 * 3,
    step_days: int = 7,
    min_n: int = 20,
    include_ipo: bool = True,
) -> dict:
    """
    수집된 ThemeFilingCount 위 C2b 계산 (§5.2) — 424B5 + (선택) IPO 레그 평균.

    각 레그: 90일 건수의 3년 z. 부호 = 발행 건수↑ = 공급 증가 = 과열↑ (정방향).
    계약 {z, s, raw, missing_reason} 반환. 유효 레그 0 → missing.

    ⚠️ **배포 전제 = 3년 백필 완결** (C2a·TH-2 와 동형). 히스토리가 얕으면(수집 며칠분)
    과거 window 건수가 인위적 0 이라 현재 소량 발행이 허위 스파이크(수σ)로 계산된다.
    배치 오케스트레이션은 백필 완결 전까지 C2b 를 §3-5 결측으로 두거나(콜드 스타트 게이트)
    3년 `collect_theme_filings` 백필 후 활성화한다.
    """
    from apps.chain_sight.services.heat_components import c2b_issuance

    syms = [s.upper() for s in symbols]
    if not syms:
        return c2b_issuance(None, [], missing_reason="c2b_empty_universe")

    cur_424, hist_424 = _count_series(
        syms, as_of, FORM_424B5, window_days, lookback_days, step_days
    )
    cur_ipo = hist_ipo = None
    if include_ipo:
        cur_ipo, hist_ipo = _count_series(
            syms, as_of, FORM_IPO, window_days, lookback_days, step_days
        )
    return c2b_issuance(
        cur_424, hist_424,
        current_ipo_count=cur_ipo, history_ipo_counts=hist_ipo,
        min_n=min_n,
    )
