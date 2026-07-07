"""
Heat 8성분 계산기 (TH-3) — 설계서 theme_heat_design.md v1.2.1 §2 · §3 · §5.

각 성분은 **독립 함수**이며 출력 계약을 통일한다:

    {"z": float|None, "s": float|None, "raw": Any, "missing_reason": str|None}

- z = 성분 표준화 점수 (설계서 §3-1: 분모 = 3년 히스토리 σ, 모(population) σ).
- s = sigmoid(z) (§3-2). z 결측이면 None.
- raw = 표준화 이전 원값 (evidence·감사용).
- missing_reason = 결측 사유. None 이면 유효. 결측은 합성기(§3-5)가 비례 재분배.

부호 규약 (전수 §2 표 대조):
  Heat 는 "과열 축" 단일 방향 — s 가중합이 높을수록 과열. 따라서 모든 성분은
  **raw 상승 = 과열 상승**이 되도록 z 부호를 잡는다. Cycle 1 8성분은 전부 **정방향**
  (raw↑ → z↑ → 과열↑) — 역방향(부호 반전) 성분은 Cycle 2 DSS 의 D2(DIO)뿐이며 본
  모듈에 없다. 각 함수 docstring 에 "raw↑ = 과열↑" 근거와 설계서 § 를 명시한다.

구현 범위:
  C1, C2a, C3, C4, C5, C6, C7, C2b = 실계산 함수.
  C8                          = 계약 만족 스텁 + missing_reason(콜드 스타트, 후속 슬라이스).

z 는 성분별 **집계 시계열(series) + 현재값(current)** 을 입력받아 계산한다. 시계열을
DB/외부에서 만드는 fetch 는 별도 관심사(호출부·배치)로 분리 — 계산기는 순수·테스트 가능.
C2a 만 완결된 백필 데이터 위 DB 백엔드 헬퍼(c2a_insider_from_db)를 함께 제공한다.
"""

import logging
from datetime import date, timedelta
from typing import Any, Iterable, Optional, Sequence

from apps.chain_sight.services.heat_synthesis import sigmoid

logger = logging.getLogger(__name__)

# 시계열 z 최소 표본 — 이 미만이면 히스토리 부족 결측. 3년 주간 스텝(~156) 기준 여유 하한.
DEFAULT_MIN_N = 20


# ────────────────────────────── 공통 계약·z 코어 ──────────────────────────────
def make_component(
    z: Optional[float], raw: Any = None, missing_reason: Optional[str] = None
) -> dict:
    """통일 출력 계약 빌더. z 결측(None)이거나 missing_reason 있으면 s=None·z=None."""
    if missing_reason is not None or z is None:
        return {
            "z": None,
            "s": None,
            "raw": raw,
            "missing_reason": missing_reason or "insufficient_history",
        }
    zf = float(z)
    return {"z": zf, "s": sigmoid(zf), "raw": raw, "missing_reason": None}


def timeseries_z(
    current: Optional[float],
    history: Sequence[Optional[float]],
    min_n: int = DEFAULT_MIN_N,
) -> Optional[float]:
    """
    시계열 z = (current − mean(history)) / std(history). 정방향 (§3-1).

    - 분모 = 모(population) 표준편차 (설계서 "3년 히스토리 σ").
    - 유효 표본(None 제외) < min_n → None (히스토리 부족).
    - std == 0 (전부 동값) → None (표준화 불능).
    - current 자체가 None → None.
    """
    if current is None:
        return None
    vals = [float(v) for v in history if v is not None]
    if len(vals) < min_n:
        return None
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    std = var ** 0.5
    if std == 0:
        return None
    return (float(current) - mean) / std


def cross_sectional_z(
    value: Optional[float], population: Sequence[Optional[float]], min_n: int = 3
) -> Optional[float]:
    """
    크로스섹셔널 z = (value − mean(population)) / std(population). 정방향.

    당일 전 모집단(예: 전 테마) 분포 내 상대 위치. C8 콜드 스타트(§5.3) 등에서 사용.
    value 는 population 에 포함되어 있다고 가정(당사자 포함 분포). std==0/표본부족 → None.
    """
    if value is None:
        return None
    vals = [float(v) for v in population if v is not None]
    if len(vals) < min_n:
        return None
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    std = var ** 0.5
    if std == 0:
        return None
    return (float(value) - mean) / std


# ────────────────────────────── C1 밸류에이션 (0.18) ──────────────────────────────
def c1_valuation(
    current_median: Optional[float],
    history_median: Sequence[Optional[float]],
    min_n: int = DEFAULT_MIN_N,
) -> dict:
    """
    C1 밸류에이션 z (§2). 구성종목 EV/Sales·Fwd P/E 중앙값의 3년 z.

    부호: 밸류에이션 배수 상승 = 멀티플 팽창 = **과열 상승** → 정방향(raw↑ → z↑). (§2 C1)
    raw = 당일 밸류에이션 중앙값. history_median = 3년(주간 등) 중앙값 시계열.
    입력 결측이면 missing_reason="c1_no_valuation".
    """
    if current_median is None:
        return make_component(None, raw=None, missing_reason="c1_no_valuation")
    z = timeseries_z(current_median, history_median, min_n=min_n)
    return make_component(z, raw=current_median)


# ────────────────────────────── C2a 내부자 (0.12, C2 내부 배분) ──────────────────────────────
def c2a_insider(
    current_ratio: Optional[float],
    history_ratio: Sequence[Optional[float]],
    min_n: int = DEFAULT_MIN_N,
) -> dict:
    """
    C2a 내부자 순매도 비율 z (§5.1). net_sell_ratio_90d 테마 합산의 3년 z.

    net_sell_ratio = Σ(매도금액×가중) / Σ((매도+매수)금액×가중) ∈ [0, 1].
    부호: 내부자 순매도 비율 상승 = 고점 분산매도(공급 반응) = **과열 상승** →
    정방향(raw↑ → z↑). (§2 C2 "공급 반응 고점 신뢰도" + §10.3 evidence "내부자 매도 +2.4σ")
    raw = 당일 net_sell_ratio. history_ratio = 3년 비율 시계열. 결측이면 c2a_no_insider.
    """
    if current_ratio is None:
        return make_component(None, raw=None, missing_reason="c2a_no_insider")
    z = timeseries_z(current_ratio, history_ratio, min_n=min_n)
    return make_component(z, raw=current_ratio)


def c2a_insider_from_db(
    symbols: Iterable[str],
    as_of: date,
    window_days: int = 90,
    lookback_days: int = 365 * 3,
    step_days: int = 7,
    min_n: int = DEFAULT_MIN_N,
) -> dict:
    """
    완결된 백필 데이터(InsiderTransactionRecord) 위 C2a 계산 — 즉시 가동 (설계서 §5.1).

    절차:
      1. [as_of − lookback − window, as_of] 구간 레코드를 1회 로드 (심볼 = 스냅샷 모집단).
      2. as_of − lookback 부터 as_of 까지 step_days 간격으로 트레일링 window 순매도비율 산출
         → 3년 비율 시계열(history).
      3. 당일(as_of) window 비율 = current.
      4. timeseries_z(current, history) → 계약.

    방어 필터(공란·A-Award 제외, 금액가중, owner 가중)는 insider_service.compute_c2a_
    net_sell_ratio 재사용 (§5.1 단일 소스). 데이터 없으면 missing_reason 반환.
    """
    from apps.chain_sight.models import InsiderTransactionRecord
    from apps.chain_sight.services.insider_service import compute_c2a_net_sell_ratio

    syms = [s.upper() for s in symbols]
    if not syms:
        return make_component(None, raw=None, missing_reason="c2a_empty_universe")

    earliest = as_of - timedelta(days=lookback_days + window_days)
    records = list(
        InsiderTransactionRecord.objects.filter(
            symbol__in=syms,
            transaction_date__gte=earliest,
            transaction_date__lte=as_of,
        ).only(
            "transaction_date",
            "transaction_type",
            "price",
            "securities_transacted",
            "type_of_owner",
            "direct_or_indirect",
        )
    )
    if not records:
        return make_component(None, raw=None, missing_reason="c2a_no_insider")

    def _ratio_at(anchor: date) -> Optional[float]:
        lo = anchor - timedelta(days=window_days)
        window = [r for r in records if lo < r.transaction_date <= anchor]
        return compute_c2a_net_sell_ratio(window)

    # 히스토리 시계열 (as_of 제외 — as_of 는 current)
    history: list[Optional[float]] = []
    cursor = as_of - timedelta(days=lookback_days)
    while cursor < as_of:
        history.append(_ratio_at(cursor))
        cursor += timedelta(days=step_days)

    current = _ratio_at(as_of)
    if current is None:
        return make_component(None, raw=None, missing_reason="c2a_no_recent_window")
    z = timeseries_z(current, history, min_n=min_n)
    return make_component(z, raw=current)


# ────────────────────────────── C3 내러티브 볼륨 (0.14) ──────────────────────────────
def c3_narrative(
    current_volume: Optional[float],
    history_volume: Sequence[Optional[float]],
    min_n: int = DEFAULT_MIN_N,
) -> dict:
    """
    C3 내러티브 볼륨 z (§2). 테마 키워드 언급량 20일 합의 3년 z (원천 DailyNewsKeyword).

    부호: 키워드 언급량 상승 = 내러티브 과열(관심 쏠림) = **과열 상승** → 정방향. (§2 C3)
    raw = 당일 20일 합 언급량. 결측이면 c3_no_keywords.
    """
    if current_volume is None:
        return make_component(None, raw=None, missing_reason="c3_no_keywords")
    z = timeseries_z(current_volume, history_volume, min_n=min_n)
    return make_component(z, raw=current_volume)


# ────────────────────────────── C4 ETF 플로우 (0.12) ──────────────────────────────
def c4_etf_flow(
    current_flow: Optional[float],
    history_flow: Sequence[Optional[float]],
    min_n: int = DEFAULT_MIN_N,
) -> dict:
    """
    C4 ETF 플로우 z (§2). Σ(Δshares_out × NAV) 20일 이동합의 3년 z (FMP 근사).

    부호: 순유입(창출) 상승 = 돈의 유입 = **과열 상승** → 정방향(raw↑ → z↑). (§2 C4)
    raw = 당일 20일 이동합 플로우. 결측이면 c4_no_etf_flow.
    """
    if current_flow is None:
        return make_component(None, raw=None, missing_reason="c4_no_etf_flow")
    z = timeseries_z(current_flow, history_flow, min_n=min_n)
    return make_component(z, raw=current_flow)


# ────────────────────────────── C5 투기 심리 (0.12) ──────────────────────────────
def c5_speculation(
    current_ratio: Optional[float],
    history_ratio: Sequence[Optional[float]],
    min_n: int = DEFAULT_MIN_N,
) -> dict:
    """
    C5 투기 심리 z (§2). 레버리지÷원본 ETF 거래량 20일 비율의 3년 z (FMP T1).

    부호: 레버리지/원본 거래량 비율 상승 = 투기적 포지셔닝 확대 = **과열 상승** → 정방향. (§2 C5)
    레버리지 ETF 부재 테마(ThemeEtfMap 없음)는 missing → c5_no_leveraged_etf (§6.4).
    raw = 당일 레버리지/원본 거래량 비율.
    """
    if current_ratio is None:
        return make_component(None, raw=None, missing_reason="c5_no_leveraged_etf")
    z = timeseries_z(current_ratio, history_ratio, min_n=min_n)
    return make_component(z, raw=current_ratio)


# ────────────────────────────── C6 상관 응집 (0.09) ──────────────────────────────
def c6_correlation(
    current_corr: Optional[float],
    history_corr: Sequence[Optional[float]],
    min_n: int = DEFAULT_MIN_N,
) -> dict:
    """
    C6 상관 응집 z (§2). pairwise rolling Pearson(60일) 평균의 3년 z (가격, Layer C 재활용).

    부호: 평균 pairwise 상관 상승 = 동조화(herding)·응집 = **과열 상승** → 정방향. (§2 C6)
    raw = 당일 평균 pairwise 상관 ∈ [-1, 1]. 결측이면 c6_no_correlation.
    """
    if current_corr is None:
        return make_component(None, raw=None, missing_reason="c6_no_correlation")
    z = timeseries_z(current_corr, history_corr, min_n=min_n)
    return make_component(z, raw=current_corr)


# ────────────────────────────── C7 거래대금 (0.09) ──────────────────────────────
def c7_dollar_volume(
    current_dollar_volume: Optional[float],
    history_dollar_volume: Sequence[Optional[float]],
    min_n: int = DEFAULT_MIN_N,
) -> dict:
    """
    C7 거래대금 z (§2). 테마 합산 거래대금(Σ price×volume) 20일의 3년 z (가격).

    부호: 거래대금 상승 = 참여·회전 확대(확인성) = **과열 상승** → 정방향. (§2 C7)
    raw = 당일 20일 테마 합산 거래대금. 결측이면 c7_no_dollar_volume.
    """
    if current_dollar_volume is None:
        return make_component(None, raw=None, missing_reason="c7_no_dollar_volume")
    z = timeseries_z(current_dollar_volume, history_dollar_volume, min_n=min_n)
    return make_component(z, raw=current_dollar_volume)


# ────────────────────────────── C2b 발행 (0.06, C2 내부 배분) ──────────────────────────────
def c2b_issuance(
    current_424b5_count: Optional[float],
    history_424b5_counts: Sequence[Optional[float]],
    current_ipo_count: Optional[float] = None,
    history_ipo_counts: Optional[Sequence[Optional[float]]] = None,
    min_n: int = DEFAULT_MIN_N,
    missing_reason: Optional[str] = None,
) -> dict:
    """
    C2b 발행 신호 z (§5.2 재정의판). 424B5 시즌드 발행 + IPO 신규 공급의 **레그 z 평균**.

    - 424B5 레그: 기상장사 2차발행(S-3 선반등록 + 424B5) 90일 건수의 3년 z.
    - IPO 레그: 신규 공급(IPO 캘린더, NYSE/NASDAQ) 90일 건수의 3년 z. (선택 — 없으면 424B5 단독.)
    부호: 발행 건수 상승 = "종이 공급" 증가(고점 신뢰도) = **과열 상승** → 정방향(count↑ → z↑).
    (§2 C2 "공급 반응", §5.2. S-1/424B4·424B2 는 재정의로 폐기·제외.)

    C2b = 유효(z 산출된) 레그들의 산술평균. 유효 레그 0 → missing_reason.
    raw = {count_424b5, count_ipo, legs:{z_424b5, z_ipo}} — evidence·감사용.
    """
    if missing_reason is not None:
        return make_component(None, raw=None, missing_reason=missing_reason)

    raw: dict[str, Any] = {}
    legs: list[float] = []

    z_424 = None
    if current_424b5_count is not None:
        raw["count_424b5"] = current_424b5_count
        z_424 = timeseries_z(current_424b5_count, history_424b5_counts, min_n=min_n)
        if z_424 is not None:
            legs.append(z_424)

    z_ipo = None
    if current_ipo_count is not None:
        raw["count_ipo"] = current_ipo_count
        z_ipo = timeseries_z(current_ipo_count, history_ipo_counts or [], min_n=min_n)
        if z_ipo is not None:
            legs.append(z_ipo)

    raw["legs"] = {"z_424b5": z_424, "z_ipo": z_ipo}

    if not legs:
        return make_component(None, raw=raw or None, missing_reason="c2b_no_issuance")
    z = sum(legs) / len(legs)
    return make_component(z, raw=raw)


# ────────────────────────────── C8 추정치 리비전 (스텁 — 콜드 스타트) ──────────────────────────────
def c8_estimate_revision(*args, **kwargs) -> dict:
    """
    C8 추정치 리비전 괴리 (§5.3) — **이 슬라이스 미구현 스텁 (콜드 스타트)**.

    주가 60일 수익률 z − EPS 컨센서스 60일 변화 z (양수 = 멀티플 단독 팽창 = 과열, 정방향).
    리비전 시계열은 EstimateSnapshot 주간 스냅샷 → 60일 diff 로 자체 생성하며, 배포 후
    60일 축적 전까지는 구조적 결측(§3-5 재분배). z_mode(cross_sectional→time_series) 감사
    필드는 실구현 슬라이스에서 components 에 기록. 지금은 계약 만족 결측 반환.
    """
    return make_component(None, raw=None, missing_reason="c8_cold_start")
