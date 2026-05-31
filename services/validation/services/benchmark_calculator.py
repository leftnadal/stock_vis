"""
Task 3: Peer 선정 + Benchmark 계산

Step 1: select_peers — industry + size bucket 기반 peer 선정
Step 2: benchmark 계산 — peer/industry별 median, p25, p75
Step 3: company_benchmark_delta — percentile_rank, rank, total
Step 4: peer_list_cache 갱신
"""

import logging
from decimal import Decimal
from typing import Optional

import numpy as np
from django.db.models import Q

from packages.shared.metrics.models import (
    CompanyMetricSnapshot,
    IndustryMetricBenchmark,
    MetricDefinition,
    PeerListCache,
    PeerMetricBenchmark,
)
from packages.shared.stocks.models import SP500Constituent, Stock
from validation.models import CompanyBenchmarkDelta

logger = logging.getLogger(__name__)

SIZE_BUCKETS = ["small", "mid", "large", "mega"]


def assign_size_bucket(market_cap: Optional[float]) -> str:
    if market_cap is None:
        return "mid"
    if market_cap >= 200_000_000_000:
        return "mega"
    elif market_cap >= 10_000_000_000:
        return "large"
    elif market_cap >= 2_000_000_000:
        return "mid"
    return "small"


def get_adjacent_buckets(bucket: str) -> list[str]:
    idx = SIZE_BUCKETS.index(bucket) if bucket in SIZE_BUCKETS else 2
    return SIZE_BUCKETS[max(0, idx - 1) : min(len(SIZE_BUCKETS), idx + 2)]


class BenchmarkCalculator:
    """Peer 선정 + Benchmark 계산 엔진"""

    def calculate_for_symbol(self, symbol: str) -> dict:
        """단일 종목의 peer 선정 + benchmark 계산"""
        symbol = symbol.upper()
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            return {"symbol": symbol, "error": "Stock not found"}

        # Step 1: Peer 선정
        peers, benchmark_basis = self._select_peers(stock)
        peer_symbols = [p.symbol for p in peers]
        peer_count = len(peer_symbols)

        # Confidence 판정
        confidence = self._determine_confidence(peer_count, benchmark_basis)

        # Size bucket
        mcap = (
            float(stock.market_capitalization) if stock.market_capitalization else None
        )
        size_bucket = assign_size_bucket(mcap)

        # Step 2: Benchmark 계산 (peer 기준)
        fiscal_years = self._get_available_years(symbol)
        metrics_calculated = 0

        for fy in fiscal_years:
            metrics_calculated += self._calculate_benchmarks_for_year(
                stock, fy, peer_symbols, benchmark_basis, confidence
            )

        # Industry benchmark도 계산
        industry_calculated = 0
        if stock.industry:
            industry_calculated = self._calculate_industry_benchmarks(
                stock.industry, fiscal_years
            )

        # Step 3: peer_list_cache 갱신
        PeerListCache.objects.update_or_create(
            symbol=stock,
            defaults={
                "peer_symbols": peer_symbols[:50],
                "peer_count": peer_count,
                "benchmark_basis": benchmark_basis,
                "size_bucket": size_bucket,
                "use_industry_fallback": benchmark_basis == "sector",
                "fallback_reason": f"peer {peer_count}개 ({benchmark_basis})"
                if benchmark_basis != "industry_size"
                else "",
                "source": "validation_batch",
            },
        )

        return {
            "symbol": symbol,
            "peer_count": peer_count,
            "benchmark_basis": benchmark_basis,
            "confidence": confidence,
            "size_bucket": size_bucket,
            "fiscal_years": fiscal_years,
            "metrics_calculated": metrics_calculated,
            "industry_calculated": industry_calculated,
        }

    def calculate_for_symbols(self, symbols: list[str] = None) -> dict:
        """배치 benchmark 계산"""
        if symbols is None:
            symbols = list(
                SP500Constituent.objects.filter(is_active=True).values_list(
                    "symbol", flat=True
                )
            )

        total = len(symbols)
        success = 0
        fail = 0
        error_details = []

        for i, symbol in enumerate(symbols):
            try:
                result = self.calculate_for_symbol(symbol)
                if result.get("error"):
                    fail += 1
                    error_details.append({"symbol": symbol, "error": result["error"]})
                else:
                    success += 1
            except Exception as e:
                fail += 1
                error_details.append({"symbol": symbol, "error": str(e)})
                logger.error(f"[{i + 1}/{total}] benchmark failed {symbol}: {e}")

            if (i + 1) % 50 == 0:
                logger.info(
                    f"Benchmark progress: {i + 1}/{total} (success={success}, errors={fail})"
                )

        return {
            "total": total,
            "success": success,
            "errors": fail,
            "error_details": error_details[:20],
        }

    def _select_peers(self, stock: Stock) -> tuple:
        """
        Peer 선정 알고리즘.
        Returns: (queryset, benchmark_basis)
        """
        mcap = (
            float(stock.market_capitalization) if stock.market_capitalization else None
        )
        bucket = assign_size_bucket(mcap)
        adjacent = get_adjacent_buckets(bucket)

        # SP500 활성 종목만 대상
        sp500_symbols = set(
            SP500Constituent.objects.filter(is_active=True).values_list(
                "symbol", flat=True
            )
        )

        base_qs = Stock.objects.filter(symbol__in=sp500_symbols).exclude(
            symbol=stock.symbol
        )

        # Step 1: 같은 industry + 인접 size bucket (case-insensitive)
        if stock.industry:
            peers = self._filter_by_size(
                base_qs.filter(industry__iexact=stock.industry), adjacent
            )
            if peers.count() >= 8:
                return peers, "industry_size"

            # Step 2: 같은 industry, size 제한 없음
            peers = base_qs.filter(industry__iexact=stock.industry)
            if peers.count() >= 5:
                return peers, "industry"

        # Step 3: 같은 sector (case-insensitive)
        if stock.sector:
            peers = base_qs.filter(sector__iexact=stock.sector)
            return peers, "sector"

        return base_qs[:20], "sector"

    def _filter_by_size(self, qs, adjacent_buckets: list[str]):
        """size bucket 필터 (market_cap 범위로 변환)"""
        conditions = Q()
        for bucket in adjacent_buckets:
            if bucket == "mega":
                conditions |= Q(market_capitalization__gte=200_000_000_000)
            elif bucket == "large":
                conditions |= Q(
                    market_capitalization__gte=10_000_000_000,
                    market_capitalization__lt=200_000_000_000,
                )
            elif bucket == "mid":
                conditions |= Q(
                    market_capitalization__gte=2_000_000_000,
                    market_capitalization__lt=10_000_000_000,
                )
            elif bucket == "small":
                conditions |= Q(market_capitalization__lt=2_000_000_000)
        return qs.filter(conditions)

    def _determine_confidence(self, peer_count: int, benchmark_basis: str) -> str:
        if peer_count >= 15 and benchmark_basis == "industry_size":
            return "high"
        elif peer_count >= 8:
            return "medium"
        elif peer_count >= 4:
            return "low"
        return "limited"

    def _get_available_years(self, symbol: str) -> list[int]:
        """이 종목의 snapshot이 있는 연도 목록"""
        return list(
            CompanyMetricSnapshot.objects.filter(symbol_id=symbol)
            .values_list("fiscal_year", flat=True)
            .distinct()
            .order_by("-fiscal_year")[:5]
        )

    def _calculate_benchmarks_for_year(
        self, stock, fiscal_year, peer_symbols, benchmark_basis, confidence
    ) -> int:
        """특정 연도의 peer benchmark + delta 계산"""
        metric_codes = list(
            MetricDefinition.objects.filter(is_benchmarkable=True).values_list(
                "metric_code", flat=True
            )
        )
        count = 0

        for mc in metric_codes:
            # peer들의 해당 연도 값 수집
            peer_values = list(
                CompanyMetricSnapshot.objects.filter(
                    symbol_id__in=peer_symbols,
                    fiscal_year=fiscal_year,
                    metric_code_id=mc,
                    value_status="normal",
                    metric_value__isnull=False,
                ).values_list("metric_value", flat=True)
            )

            if len(peer_values) < 2:
                continue

            vals = np.array([float(v) for v in peer_values])
            p25 = float(np.percentile(vals, 25))
            median = float(np.percentile(vals, 50))
            p75 = float(np.percentile(vals, 75))

            # PeerMetricBenchmark 저장
            PeerMetricBenchmark.objects.update_or_create(
                symbol=stock,
                fiscal_year=fiscal_year,
                metric_code_id=mc,
                defaults={
                    "p25_value": Decimal(str(round(p25, 6))),
                    "median_value": Decimal(str(round(median, 6))),
                    "p75_value": Decimal(str(round(p75, 6))),
                    "peer_count": len(peer_values),
                    "peer_symbols_used": peer_symbols[:30],
                    "benchmark_confidence": confidence,
                },
            )

            # CompanyBenchmarkDelta 계산
            company_snap = CompanyMetricSnapshot.objects.filter(
                symbol=stock,
                fiscal_year=fiscal_year,
                metric_code_id=mc,
                value_status="normal",
                metric_value__isnull=False,
            ).first()

            if company_snap:
                company_val = float(company_snap.metric_value)
                # percentile_rank 계산
                below = sum(1 for v in vals if v < company_val)
                equal = sum(1 for v in vals if v == company_val)
                pct_rank = ((below + 0.5 * equal) / len(vals)) * 100

                # rank 계산 (higher_is_better 고려)
                md = MetricDefinition.objects.filter(pk=mc).first()
                if md and md.higher_is_better:
                    rank = sum(1 for v in vals if v > company_val) + 1
                else:
                    rank = sum(1 for v in vals if v < company_val) + 1

                CompanyBenchmarkDelta.objects.update_or_create(
                    symbol=stock,
                    fiscal_year=fiscal_year,
                    metric_code_id=mc,
                    defaults={
                        "company_value": company_snap.metric_value,
                        "benchmark_type": "peer",
                        "benchmark_median": Decimal(str(round(median, 6))),
                        "benchmark_p25": Decimal(str(round(p25, 6))),
                        "benchmark_p75": Decimal(str(round(p75, 6))),
                        "benchmark_basis": benchmark_basis,
                        "benchmark_confidence": confidence,
                        "delta_vs_median": Decimal(str(round(company_val - median, 6))),
                        "percentile_rank": Decimal(str(round(pct_rank, 2))),
                        "rank": rank,
                        "total": len(peer_values) + 1,
                    },
                )
            count += 1

        return count

    def _calculate_industry_benchmarks(
        self, industry: str, fiscal_years: list[int]
    ) -> int:
        """Industry 전체 기준 benchmark 계산"""
        # industry에 속한 모든 S&P 500 종목
        sp500_symbols = set(
            SP500Constituent.objects.filter(is_active=True).values_list(
                "symbol", flat=True
            )
        )
        industry_symbols = list(
            Stock.objects.filter(
                industry__iexact=industry, symbol__in=sp500_symbols
            ).values_list("symbol", flat=True)
        )

        if len(industry_symbols) < 2:
            return 0

        metric_codes = list(
            MetricDefinition.objects.filter(is_benchmarkable=True).values_list(
                "metric_code", flat=True
            )
        )
        count = 0

        for fy in fiscal_years:
            for mc in metric_codes:
                values = list(
                    CompanyMetricSnapshot.objects.filter(
                        symbol_id__in=industry_symbols,
                        fiscal_year=fy,
                        metric_code_id=mc,
                        value_status="normal",
                        metric_value__isnull=False,
                    ).values_list("metric_value", flat=True)
                )
                if len(values) < 2:
                    continue

                vals = np.array([float(v) for v in values])
                IndustryMetricBenchmark.objects.update_or_create(
                    industry=industry,
                    fiscal_year=fy,
                    metric_code_id=mc,
                    defaults={
                        "p25_value": Decimal(
                            str(round(float(np.percentile(vals, 25)), 6))
                        ),
                        "median_value": Decimal(
                            str(round(float(np.percentile(vals, 50)), 6))
                        ),
                        "p75_value": Decimal(
                            str(round(float(np.percentile(vals, 75)), 6))
                        ),
                        "mean_value": Decimal(str(round(float(np.mean(vals)), 6))),
                        "sample_count": len(values),
                        "benchmark_confidence": "high"
                        if len(values) >= 10
                        else ("medium" if len(values) >= 5 else "low"),
                    },
                )
                count += 1

        return count
