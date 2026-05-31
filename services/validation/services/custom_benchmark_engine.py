"""
Compute-on-Read 엔진: 커스텀 peer에 대해 DB 저장 없이 benchmark를 실시간 계산.

설계 원칙:
- CompanyMetricSnapshot에서 벌크 1회 쿼리
- numpy로 percentile/rank/signal 계산 (in-memory)
- 결과를 dict로 반환 (DB 쓰기 없음)
- Redis 캐시 (TTL 1시간)
"""

import logging

from django.core.cache import cache

from packages.shared.metrics.models import CompanyMetricSnapshot, MetricDefinition
from services.validation.services.category_signal_calculator import (
    CATEGORY_DISPLAY,
    CATEGORY_METRICS,
)

logger = logging.getLogger(__name__)

CACHE_TTL = 3600  # 1시간


def _cache_key(user_id: int, symbol: str) -> str:
    return f"custom_validation:{user_id}:{symbol}"


class CustomBenchmarkEngine:
    """커스텀 peer에 대한 on-the-fly benchmark 계산"""

    def compute_summary(
        self, symbol: str, custom_peers: list[str], user_id: int = 0
    ) -> dict:
        """
        커스텀 peer로 summary 계산.
        Returns: summary API 응답과 동일한 dict 구조
        """
        # 캐시 확인
        ck = _cache_key(user_id, symbol)
        cached = cache.get(ck)
        if cached:
            return cached

        # 벌크 데이터 로드
        all_symbols = custom_peers + [symbol]
        metric_codes = list(
            MetricDefinition.objects.filter(is_benchmarkable=True).values_list(
                "metric_code", flat=True
            )
        )

        # 최신 fiscal_year 결정
        latest_fy = (
            CompanyMetricSnapshot.objects.filter(symbol_id=symbol)
            .values_list("fiscal_year", flat=True)
            .distinct()
            .order_by("-fiscal_year")
            .first()
        )
        if not latest_fy:
            return {"error": "no_data", "message": "지표 데이터 없음"}

        # 1회 벌크 쿼리: 모든 peer + 자사의 모든 연도/지표
        fiscal_years = list(
            CompanyMetricSnapshot.objects.filter(symbol_id=symbol)
            .values_list("fiscal_year", flat=True)
            .distinct()
            .order_by("-fiscal_year")[:5]
        )

        snaps = list(
            CompanyMetricSnapshot.objects.filter(
                symbol_id__in=all_symbols,
                fiscal_year__in=fiscal_years,
                metric_code_id__in=metric_codes,
                value_status="normal",
                metric_value__isnull=False,
            ).values("symbol_id", "fiscal_year", "metric_code_id", "metric_value")
        )

        # dict로 그룹핑: {(fiscal_year, metric_code): {symbol: value}}
        data = {}
        for s in snaps:
            key = (s["fiscal_year"], s["metric_code_id"])
            if key not in data:
                data[key] = {}
            data[key][s["symbol_id"]] = float(s["metric_value"])

        # Category Signal 계산
        category_signals = []
        for category, codes in CATEGORY_METRICS.items():
            valid_pcts = []
            for mc in codes:
                key = (latest_fy, mc)
                if key not in data or symbol not in data[key]:
                    continue
                peer_vals = [
                    v for s, v in data[key].items() if s != symbol and s in custom_peers
                ]
                if len(peer_vals) < 2:
                    continue
                company_val = data[key][symbol]
                below = sum(1 for v in peer_vals if v < company_val)
                equal = sum(1 for v in peer_vals if v == company_val)
                pct = ((below + 0.5 * equal) / len(peer_vals)) * 100
                valid_pcts.append(pct)

            if not valid_pcts:
                signal = "gray"
                reason = "데이터 부족"
                score = None
            else:
                score = sum(valid_pcts) / len(valid_pcts)
                if score >= 65:
                    signal = "green"
                elif score >= 35:
                    signal = "yellow"
                else:
                    signal = "red"
                green_count = sum(1 for p in valid_pcts if p >= 65)
                reason = f"{len(valid_pcts)}개 지표 중 {green_count}개 상위 35%"

            category_signals.append(
                {
                    "category": category,
                    "display_name": CATEGORY_DISPLAY.get(category, category),
                    "signal": signal,
                    "signal_reason": reason,
                    "metric_count": len(codes),
                    "description": "",
                }
            )

        # 한줄 요약
        green_cats = [c for c in category_signals if c["signal"] == "green"]
        red_cats = [c for c in category_signals if c["signal"] == "red"]
        if len(green_cats) >= 5:
            summary_text = "전반적으로 양호한 재무 체질."
        elif len(red_cats) >= 2:
            summary_text = "여러 영역에서 주의 필요. 심층 분석 권장."
        elif green_cats:
            summary_text = f"{green_cats[0]['display_name']}이(가) 강점."
        else:
            summary_text = "대부분 지표가 중립 구간."

        result = {
            "symbol": symbol,
            "company_name": "",
            "data_fiscal_year": latest_fy,
            "data_freshness": None,
            "category_signals": category_signals,
            "summary_text": f"[커스텀 {len(custom_peers)}개 peer] {summary_text}",
            "summary_source": "custom",
            "peer_info": {
                "industry": "",
                "peer_count": len(custom_peers),
                "confidence": "custom",
                "benchmark_basis": "custom",
                "size_bucket": "",
                "basis_description": f"직접 설정한 {len(custom_peers)}개 종목과 비교",
                "top_peers": custom_peers[:10],
                "industry_leader": None,
            },
            "industry_position": {"ranks": []},
        }

        # 캐시 저장
        cache.set(ck, result, CACHE_TTL)
        return result

    def invalidate_cache(self, user_id: int, symbol: str):
        cache.delete(_cache_key(user_id, symbol))
