"""
Peer Phase 7: LLM 대화형 Peer 조정

자연어 → 구조화 필터 (Gemini Flash) → 필터 실행 → 결과 반환.

예시:
  "성숙기 기업만" → {"growth_stage": ["mature"]}
  "해외 매출 50% 이상" → {"foreign_revenue_pct_min": 50}
  "부채비율 30% 이하" → {"metric_filters": [{"code": "debt_to_equity", "op": "<=", "value": 0.3}]}
"""

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

FILTER_PARSING_PROMPT = """You are a financial data filter parser. Convert the user's natural language peer filter request into a structured JSON filter.

**Available filter fields:**

1. Chain Sight profiles:
   - growth_stage: ["mature", "accelerating", "declining", "turnaround", "cash_cow", "early_growth"]
   - capital_type: ["balanced", "heavy_investor", "cash_hoarder", "shareholder_first", "aggressive_growth"]
   - rate_sensitivity: ["high", "medium", "low"]
   - forex_sensitivity: ["high", "medium", "low"]
   - regulation_type: ["fda", "financial", "environmental", "telecom", "none"]
   - insider_signal: ["strong_buy", "buy", "neutral", "sell", "strong_sell"]

2. Metric filters (metric_code with operator and value):
   - revenue_growth_yoy (%), gross_margin (%), operating_margin (%), net_margin (%)
   - roe (%), roa (%), roic (%)
   - debt_to_equity (ratio), current_ratio (ratio)
   - pe_ratio, pb_ratio, dividend_yield (%)
   - rd_to_revenue (%)

3. Sector/Industry exclusion:
   - exclude_sectors: ["Technology", "Healthcare", ...]
   - exclude_industries: ["Banks", ...]

4. Other:
   - foreign_revenue_pct_min: number (%)
   - foreign_revenue_pct_max: number (%)

**User request**: {user_input}

**Current symbol context**: {symbol} (sector: {sector})

Return a JSON object with applicable filter fields. Only include fields mentioned by the user.
Example: {{"growth_stage": ["mature"], "metric_filters": [{{"code": "roe", "op": ">=", "value": 15}}]}}
If the request is unclear, return {{"error": "Could not parse filter request"}}.
"""


def parse_filter_with_llm(user_input: str, symbol: str, sector: str = "") -> dict:
    """자연어 → 구조화 필터 변환 (Gemini Flash)."""
    from google.genai import types

    from packages.shared.llm import complete

    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return {"error": "GEMINI_API_KEY not configured"}

    prompt = FILTER_PARSING_PROMPT.format(
        user_input=user_input,
        symbol=symbol,
        sector=sector,
    )

    try:
        # shared/llm complete() 경유(슬라이스 ④, IDENTICAL). response_format="json"→
        # response_mime_type, max_tokens 미지정(Gemini 폴백 없음), thinking_config→extra. 정책 off.
        response = complete(
            prompt,
            provider="gemini",
            model="gemini-2.5-flash",
            temperature=0.1,
            response_format="json",
            extra={"thinking_config": types.ThinkingConfig(thinking_budget=0)},
        )

        text = response.text if hasattr(response, "text") and response.text else "{}"
        return json.loads(text)

    except Exception as e:
        logger.error(f"LLM filter parsing failed: {e}")
        return {"error": str(e)}


def execute_peer_filter(
    symbol: str, parsed_filter: dict, base_peers: list = None
) -> dict:
    """
    구조화 필터를 실행하여 peer 리스트 반환.

    Args:
        symbol: 기준 종목
        parsed_filter: parse_filter_with_llm() 결과
        base_peers: 기존 프리셋 peer 리스트 (None이면 S&P 500 전체)

    Returns:
        {'peers': [...], 'count': int, 'filters_applied': [...]}
    """
    from apps.chain_sight.models import (
        CompanyCapitalDNA,
        CompanyGrowthStage,
        CompanyInsiderSignal,
        CompanySensitivityProfile,
    )
    from packages.shared.metrics.models.metric_snapshot import CompanyMetricSnapshot
    from packages.shared.stocks.models import SP500Constituent, Stock

    symbol = symbol.upper()

    if "error" in parsed_filter:
        return {"peers": [], "count": 0, "error": parsed_filter["error"]}

    # 기본 후보 풀
    if base_peers:
        candidates = set(base_peers)
    else:
        candidates = set(
            SP500Constituent.objects.filter(is_active=True).values_list(
                "symbol", flat=True
            )
        )
    candidates.discard(symbol)

    filters_applied = []

    # ── Chain Sight 프로파일 필터 ──
    if "growth_stage" in parsed_filter:
        stages = parsed_filter["growth_stage"]
        matched = set(
            CompanyGrowthStage.objects.filter(stage__in=stages).values_list(
                "symbol_id", flat=True
            )
        )
        candidates &= matched
        filters_applied.append(f"GrowthStage: {stages}")

    if "capital_type" in parsed_filter:
        types_list = parsed_filter["capital_type"]
        matched = set(
            CompanyCapitalDNA.objects.filter(capital_type__in=types_list).values_list(
                "symbol_id", flat=True
            )
        )
        candidates &= matched
        filters_applied.append(f"CapitalDNA: {types_list}")

    if "rate_sensitivity" in parsed_filter:
        levels = parsed_filter["rate_sensitivity"]
        matched = set(
            CompanySensitivityProfile.objects.filter(
                rate_sensitivity__in=levels
            ).values_list("symbol_id", flat=True)
        )
        candidates &= matched
        filters_applied.append(f"Rate Sensitivity: {levels}")

    if "forex_sensitivity" in parsed_filter:
        levels = parsed_filter["forex_sensitivity"]
        matched = set(
            CompanySensitivityProfile.objects.filter(
                forex_sensitivity__in=levels
            ).values_list("symbol_id", flat=True)
        )
        candidates &= matched
        filters_applied.append(f"Forex Sensitivity: {levels}")

    if "regulation_type" in parsed_filter:
        types_list = parsed_filter["regulation_type"]
        matched = set(
            CompanySensitivityProfile.objects.filter(
                regulation_type__in=types_list
            ).values_list("symbol_id", flat=True)
        )
        candidates &= matched
        filters_applied.append(f"Regulation: {types_list}")

    if "insider_signal" in parsed_filter:
        signals = parsed_filter["insider_signal"]
        matched = set(
            CompanyInsiderSignal.objects.filter(insider_signal__in=signals).values_list(
                "symbol_id", flat=True
            )
        )
        candidates &= matched
        filters_applied.append(f"Insider Signal: {signals}")

    # ── 환율 민감도 (foreign_revenue_pct) ──
    if "foreign_revenue_pct_min" in parsed_filter:
        threshold = parsed_filter["foreign_revenue_pct_min"]
        matched = set(
            CompanySensitivityProfile.objects.filter(
                foreign_revenue_pct__gte=threshold
            ).values_list("symbol_id", flat=True)
        )
        candidates &= matched
        filters_applied.append(f"Foreign Revenue >= {threshold}%")

    if "foreign_revenue_pct_max" in parsed_filter:
        threshold = parsed_filter["foreign_revenue_pct_max"]
        matched = set(
            CompanySensitivityProfile.objects.filter(
                foreign_revenue_pct__lte=threshold
            ).values_list("symbol_id", flat=True)
        )
        candidates &= matched
        filters_applied.append(f"Foreign Revenue <= {threshold}%")

    # ── 섹터/산업 제외 ──
    if "exclude_sectors" in parsed_filter:
        sectors = parsed_filter["exclude_sectors"]
        excluded = set(
            Stock.objects.filter(sector__in=sectors).values_list("symbol", flat=True)
        )
        candidates -= excluded
        filters_applied.append(f"Exclude sectors: {sectors}")

    if "exclude_industries" in parsed_filter:
        industries = parsed_filter["exclude_industries"]
        excluded = set(
            Stock.objects.filter(industry__in=industries).values_list(
                "symbol", flat=True
            )
        )
        candidates -= excluded
        filters_applied.append(f"Exclude industries: {industries}")

    # ── 메트릭 필터 ──
    if "metric_filters" in parsed_filter:
        latest_fy = (
            CompanyMetricSnapshot.objects.filter(symbol_id=symbol)
            .values_list("fiscal_year", flat=True)
            .distinct()
            .order_by("-fiscal_year")
            .first()
        )

        for mf in parsed_filter["metric_filters"]:
            code = mf.get("code", "")
            op = mf.get("op", ">=")
            value = mf.get("value", 0)

            qs = CompanyMetricSnapshot.objects.filter(
                metric_code_id=code,
                value_status="normal",
                metric_value__isnull=False,
            )
            if latest_fy:
                qs = qs.filter(fiscal_year=latest_fy)

            if op == ">=":
                qs = qs.filter(metric_value__gte=value)
            elif op == "<=":
                qs = qs.filter(metric_value__lte=value)
            elif op == ">":
                qs = qs.filter(metric_value__gt=value)
            elif op == "<":
                qs = qs.filter(metric_value__lt=value)

            matched = set(qs.values_list("symbol_id", flat=True))
            candidates &= matched
            filters_applied.append(f"{code} {op} {value}")

    peers = sorted(candidates)
    return {
        "peers": peers,
        "count": len(peers),
        "filters_applied": filters_applied,
    }
