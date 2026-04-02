"""분기 재무 지표 조회 서비스 — Thesis Dashboard용

단일 종목의 최신 분기 재무제표를 조회하고,
MetricCalculator를 통해 지표값을 계산한 뒤
이전 분기/전년 동기와 비교 + 최근 20분기(5개년) 히스토리를 반환한다.
"""

import logging
from typing import Optional

from stocks.models import IncomeStatement, BalanceSheet, CashFlowStatement, Stock
from validation.models import CompanyMetricLatest
from validation.services.metric_calculator import MetricCalculator, _safe, _safe_nonzero

logger = logging.getLogger(__name__)

# 5개년 = 20분기, 비교용 여분 포함
HISTORY_QUARTERS = 20
STATEMENT_FETCH_LIMIT = HISTORY_QUARTERS + 8  # 비교 대상용 여분

# 분기 계산을 지원하지 않는 지표 (연간 데이터 의존 or SBC 전용 필드)
UNSUPPORTED_QUARTERLY = {
    'dilution_3y_cum',
    'cash_from_ops_trend',
    'sbc_to_revenue',
    'buyback_offsets_sbc',
}

# MetricCalculator 33개 외 커스텀 지표 (재무제표에서 직접 계산)
CUSTOM_METRICS = {'eps_quarterly'}

# 지표별 비교 방식: yoy=전년 동기, qoq=직전 분기
COMPARISON_TYPE_MAP = {
    # YoY — 계절성이 강한 지표
    'revenue_growth_yoy': 'yoy',
    'operating_income_growth': 'yoy',
    'fcf_growth_yoy': 'yoy',
    'gross_margin': 'yoy',
    'net_margin': 'yoy',
    'operating_margin': 'yoy',
    'eps_quarterly': 'yoy',
    # QoQ — 추세 변화가 중요한 지표
    'roe': 'qoq',
    'roic': 'qoq',
    'current_ratio': 'qoq',
    'interest_coverage': 'qoq',
    'net_debt_to_ebitda': 'qoq',
    'fcf_margin': 'qoq',
    'ev_to_ebitda': 'qoq',
    'fcf_yield': 'qoq',
    'dso': 'qoq',
    'asset_turnover': 'qoq',
    'accruals_ratio': 'qoq',
    'net_shareholder_yield': 'qoq',
}

# display_unit='%'일 때 비율(0~1) → 백분율 변환이 필요한 지표
RATIO_METRICS = {
    'gross_margin', 'operating_margin', 'net_margin', 'roe', 'roic',
    'fcf_margin', 'revenue_growth_yoy', 'operating_income_growth',
    'fcf_growth_yoy', 'debt_to_equity', 'short_term_debt_pct',
    'ocf_to_net_income', 'capex_to_ocf', 'accruals_ratio', 'fcf_conversion',
    'ar_to_revenue', 'sga_to_revenue', 'asset_turnover',
    'net_shareholder_yield', 'fcf_yield',
}


def _get_prev_quarter(fy: int, fq: int) -> tuple[int, int]:
    """직전 분기 (year, quarter). Q1이면 전년 Q4."""
    if fq == 1:
        return fy - 1, 4
    return fy, fq - 1


def _get_quarterly_statements(symbol: str, limit: int = 5):
    """최근 분기 재무제표 조회. (fiscal_year, fiscal_quarter) 기준 최신순 정렬."""
    inc_qs = IncomeStatement.objects.filter(
        stock_id=symbol,
        period_type='quarterly',
        fiscal_quarter__isnull=False,
    ).order_by('-fiscal_year', '-fiscal_quarter')[:limit]

    bal_qs = BalanceSheet.objects.filter(
        stock_id=symbol,
        period_type='quarterly',
        fiscal_quarter__isnull=False,
    ).order_by('-fiscal_year', '-fiscal_quarter')[:limit]

    cf_qs = CashFlowStatement.objects.filter(
        stock_id=symbol,
        period_type='quarterly',
        fiscal_quarter__isnull=False,
    ).order_by('-fiscal_year', '-fiscal_quarter')[:limit]

    return list(inc_qs), list(bal_qs), list(cf_qs)


def _find_statement(statements: list, fiscal_year: int, fiscal_quarter: int):
    """리스트에서 (fiscal_year, fiscal_quarter)가 매칭되는 재무제표 반환."""
    for s in statements:
        if s.fiscal_year == fiscal_year and s.fiscal_quarter == fiscal_quarter:
            return s
    return None


def _calc_custom_metric(metric_code: str, inc, bal, cf, stock=None) -> Optional[float]:
    """MetricCalculator에 없는 커스텀 지표를 직접 계산."""
    if metric_code == 'eps_quarterly':
        ni = _safe(inc.net_income)
        if ni is None:
            return None
        # 1) BalanceSheet의 shares_outstanding 시도
        shares = _safe_nonzero(getattr(bal, 'common_stock_shares_outstanding', None))
        if shares:
            return ni / shares
        # 2) Stock의 market_cap / 현재가로 추정
        if stock:
            mcap = _safe_nonzero(getattr(stock, 'market_capitalization', None))
            price = _safe_nonzero(getattr(stock, 'real_time_price', None))
            if mcap and price:
                est_shares = mcap / price
                return ni / est_shares
        return None
    return None


def _calc_single_metric(
    calculator: MetricCalculator,
    inc,
    bal,
    cf,
    prev_inc,
    prev_bal,
    prev_cf,
    stock,
    metric_code: str,
) -> Optional[float]:
    """
    MetricCalculator._calculate_all_metrics를 호출해
    metric_code에 해당하는 단일값을 float으로 반환.

    커스텀 지표(CUSTOM_METRICS)이면 직접 계산.
    계산 실패 or missing 상태이면 None 반환.
    """
    if metric_code in CUSTOM_METRICS:
        return _calc_custom_metric(metric_code, inc, bal, cf, stock)

    try:
        results = calculator._calculate_all_metrics(
            inc, bal, cf, prev_inc, prev_bal, prev_cf, None, stock,
        )
        if metric_code not in results:
            return None
        value, value_status, _ = results[metric_code]
        if value_status == 'missing' or value is None:
            return None
        return float(value)
    except Exception as e:
        logger.warning(f"분기 지표 계산 실패 ({metric_code}): {e}")
        return None


def _build_quarterly_history(
    calculator: MetricCalculator,
    stock,
    inc_list: list,
    bal_list: list,
    cf_list: list,
    metric_code: str,
    comparison_type: str,
    limit: int = 4,
) -> list[dict]:
    """
    최근 N분기의 지표값을 계산하여 히스토리 리스트 반환.

    Returns:
        오래된 것부터 정렬된 [{'fy': int, 'fq': int, 'value': float}, ...].
        값이 없는 분기는 건너뛴다.
    """
    history = []

    # inc_list는 이미 최신순으로 정렬됨
    # 비교용 여분을 포함하여 충분히 순회
    for inc in inc_list[:limit + 4]:
        fy, fq = inc.fiscal_year, inc.fiscal_quarter
        bal = _find_statement(bal_list, fy, fq)
        cf = _find_statement(cf_list, fy, fq)

        if not bal or not cf:
            continue

        # 비교 대상 (prev) 결정
        if comparison_type == 'yoy':
            p_fy, p_fq = fy - 1, fq
        else:
            p_fy, p_fq = _get_prev_quarter(fy, fq)

        p_inc = _find_statement(inc_list, p_fy, p_fq)
        p_bal = _find_statement(bal_list, p_fy, p_fq)
        p_cf = _find_statement(cf_list, p_fy, p_fq)

        val = _calc_single_metric(
            calculator, inc, bal, cf, p_inc, p_bal, p_cf, stock, metric_code,
        )

        if val is not None:
            history.append({'fy': fy, 'fq': fq, 'value': val})

        if len(history) >= limit:
            break

    # 오래된 것부터 오름차순 정렬
    history.reverse()
    return history


def _fallback_to_annual(symbol: str, metric_code: str) -> Optional[dict]:
    """
    분기 데이터를 사용할 수 없을 때 CompanyMetricLatest(연간)에서 fallback.

    Returns:
        연간 지표 dict (fiscal_quarter=None, 히스토리 없음) 또는 None.
    """
    try:
        latest = CompanyMetricLatest.objects.filter(
            symbol_id=symbol,
            metric_code_id=metric_code,
        ).first()

        if not latest or latest.latest_value is None:
            return None

        return {
            'value': float(latest.latest_value),
            'fiscal_year': latest.latest_fiscal_year,
            'fiscal_quarter': None,
            'reported_date': None,
            'prev_value': None,
            'change_pct': None,
            'comparison_type': None,
            'quarterly_history': None,
        }
    except Exception as e:
        logger.warning(f"연간 fallback 실패 ({symbol}/{metric_code}): {e}")
        return None


def fetch_quarterly_metric(symbol: str, metric_code: str) -> Optional[dict]:
    """
    단일 종목의 최신 분기 지표값 + 비교 + 4분기 히스토리를 반환한다.

    분기 데이터가 없거나 계산할 수 없는 지표이면
    CompanyMetricLatest(연간)로 fallback하고, 연간도 없으면 None 반환.

    Args:
        symbol: 종목 심볼 (대소문자 무관)
        metric_code: MetricDefinition의 metric_code

    Returns:
        {
            'value': float,
            'fiscal_year': int,
            'fiscal_quarter': int | None,
            'reported_date': str | None,    # ISO 형식 날짜 or None
            'prev_value': float | None,
            'change_pct': float | None,
            'comparison_type': 'qoq' | 'yoy' | None,
            'quarterly_history': [{'fy': int, 'fq': int, 'value': float}, ...] | None,
        }
        또는 None (데이터 완전 없을 때)
    """
    symbol = symbol.upper()

    # 분기 미지원 지표는 즉시 연간 fallback
    if metric_code in UNSUPPORTED_QUARTERLY:
        return _fallback_to_annual(symbol, metric_code)

    comparison_type = COMPARISON_TYPE_MAP.get(metric_code, 'qoq')

    stock = Stock.objects.filter(symbol=symbol).first()
    if not stock:
        return None

    # 최근 5개년(20분기) + 비교용 여분 조회
    inc_list, bal_list, cf_list = _get_quarterly_statements(symbol, limit=STATEMENT_FETCH_LIMIT)

    if not inc_list or not bal_list or not cf_list:
        return _fallback_to_annual(symbol, metric_code)

    # 3개 테이블 모두 존재하는 가장 최신 분기 결정
    latest_inc = inc_list[0]
    latest_fy = latest_inc.fiscal_year
    latest_fq = latest_inc.fiscal_quarter

    latest_bal = _find_statement(bal_list, latest_fy, latest_fq)
    latest_cf = _find_statement(cf_list, latest_fy, latest_fq)

    if not latest_bal or not latest_cf:
        return _fallback_to_annual(symbol, metric_code)

    calculator = MetricCalculator()

    # 비교 대상 분기 결정
    if comparison_type == 'yoy':
        prev_fy, prev_fq = latest_fy - 1, latest_fq
    else:
        prev_fy, prev_fq = _get_prev_quarter(latest_fy, latest_fq)

    prev_inc = _find_statement(inc_list, prev_fy, prev_fq)
    prev_bal = _find_statement(bal_list, prev_fy, prev_fq)
    prev_cf = _find_statement(cf_list, prev_fy, prev_fq)

    # 최신 분기 값 계산
    current_value = _calc_single_metric(
        calculator, latest_inc, latest_bal, latest_cf,
        prev_inc, prev_bal, prev_cf, stock, metric_code,
    )

    if current_value is None:
        return _fallback_to_annual(symbol, metric_code)

    # 비교 기준값 계산 (prev 분기의 값)
    prev_value = None
    if prev_inc and prev_bal and prev_cf:
        # prev의 비교 대상(prev-prev) 결정
        if comparison_type == 'yoy':
            pp_fy, pp_fq = prev_fy - 1, prev_fq
        else:
            pp_fy, pp_fq = _get_prev_quarter(prev_fy, prev_fq)

        pp_inc = _find_statement(inc_list, pp_fy, pp_fq)
        pp_bal = _find_statement(bal_list, pp_fy, pp_fq)
        pp_cf = _find_statement(cf_list, pp_fy, pp_fq)

        prev_value = _calc_single_metric(
            calculator, prev_inc, prev_bal, prev_cf,
            pp_inc, pp_bal, pp_cf, stock, metric_code,
        )

    # change_pct 계산
    change_pct = None
    if prev_value is not None and prev_value != 0:
        change_pct = round(((current_value - prev_value) / abs(prev_value)) * 100, 2)

    # 5개년(20분기) 히스토리
    quarterly_history = _build_quarterly_history(
        calculator, stock, inc_list, bal_list, cf_list,
        metric_code, comparison_type, limit=HISTORY_QUARTERS,
    )

    reported_date = None
    if latest_inc.reported_date:
        reported_date = latest_inc.reported_date.isoformat()

    return {
        'value': current_value,
        'fiscal_year': latest_fy,
        'fiscal_quarter': latest_fq,
        'reported_date': reported_date,
        'prev_value': prev_value,
        'change_pct': change_pct,
        'comparison_type': comparison_type,
        'quarterly_history': quarterly_history,
    }
