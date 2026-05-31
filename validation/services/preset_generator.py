"""
Peer 프리셋 자동 생성 서비스

Phase 2: default, sector_all, size_peers
Phase 3: quality_top, lifecycle
"""

import logging

import numpy as np

from packages.shared.metrics.models import CompanyMetricSnapshot
from packages.shared.stocks.models import SP500Constituent, Stock
from validation.models import PeerPreset
from validation.services.benchmark_calculator import (
    assign_size_bucket,
    get_adjacent_buckets,
)

logger = logging.getLogger(__name__)


class PresetGenerator:
    """종목당 프리셋 자동 생성"""

    def generate_for_symbol(self, symbol: str) -> dict:
        symbol = symbol.upper()
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            return {"symbol": symbol, "error": "Stock not found"}

        sp500_symbols = set(
            SP500Constituent.objects.filter(is_active=True).values_list(
                "symbol", flat=True
            )
        )
        base_qs = Stock.objects.filter(symbol__in=sp500_symbols).exclude(symbol=symbol)

        presets_created = 0

        # 1. default (업종 표준)
        presets_created += self._generate_default(stock, base_qs)

        # 2. sector_all (섹터 전체)
        presets_created += self._generate_sector_all(stock, base_qs)

        # 3. size_peers (체급 동종) — mega/large만
        mcap = (
            float(stock.market_capitalization) if stock.market_capitalization else None
        )
        bucket = assign_size_bucket(mcap)
        if bucket in ("mega", "large"):
            presets_created += self._generate_size_peers(stock, base_qs, bucket)

        # 4. quality_top (우량주 비교) — sector >= 25종목
        presets_created += self._generate_quality_top(stock, base_qs)

        # 5. lifecycle (성장단계 유사) — sector >= 25종목 + CAGR 데이터
        presets_created += self._generate_lifecycle(stock, base_qs)

        # 6. thematic (비즈니스 모델 유사) — Phase 6: Chain Sight DNA 기반
        presets_created += self._generate_thematic(stock, base_qs)

        return {"symbol": symbol, "presets_created": presets_created}

    def generate_for_symbols(self, symbols: list[str] = None) -> dict:
        if symbols is None:
            symbols = list(
                SP500Constituent.objects.filter(is_active=True).values_list(
                    "symbol", flat=True
                )
            )

        total = len(symbols)
        success = 0
        for i, sym in enumerate(symbols):
            try:
                r = self.generate_for_symbol(sym)
                if not r.get("error"):
                    success += 1
            except Exception as e:
                logger.error(f"preset gen failed {sym}: {e}")

            if (i + 1) % 50 == 0:
                logger.info(f"Preset gen: {i + 1}/{total}")

        return {"total": total, "success": success}

    def _generate_default(self, stock, base_qs) -> int:
        """업종 표준: industry + size bucket fallback"""
        mcap = (
            float(stock.market_capitalization) if stock.market_capitalization else None
        )
        bucket = assign_size_bucket(mcap)
        adjacent = get_adjacent_buckets(bucket)

        peers = []
        basis = "industry_size"
        summary = ""

        if stock.industry:
            # Step 1: industry + adjacent size
            qs = self._filter_by_size(
                base_qs.filter(industry__iexact=stock.industry), adjacent
            )
            if qs.count() >= 8:
                peers = list(qs.values_list("symbol", flat=True))
                summary = f"{stock.industry} 업종 내 유사 시가총액 {len(peers)}개"
            else:
                # Step 2: industry 전체
                qs = base_qs.filter(industry__iexact=stock.industry)
                if qs.count() >= 5:
                    peers = list(qs.values_list("symbol", flat=True))
                    basis = "industry"
                    summary = f"{stock.industry} 업종 전체 {len(peers)}개"

        if not peers and stock.sector:
            # Step 3: sector fallback
            qs = base_qs.filter(sector__iexact=stock.sector)
            peers = list(qs.values_list("symbol", flat=True))
            basis = "sector"
            summary = f"{stock.sector} 섹터 전체 {len(peers)}개"

        if not peers:
            return 0

        confidence = self._calc_confidence(len(peers), stock)

        PeerPreset.objects.update_or_create(
            symbol=stock,
            preset_key="default",
            defaults={
                "display_name": "업종 표준",
                "logic_summary": summary,
                "peer_symbols": peers[:50],
                "peer_count": len(peers),
                "generation_method": f"auto_{basis.split('_')[0]}",
                "confidence_score": confidence,
                "is_default": True,
                "is_active": True,
            },
        )
        return 1

    def _generate_sector_all(self, stock, base_qs) -> int:
        """섹터 전체: 같은 sector S&P 500 전체"""
        if not stock.sector:
            return 0

        peers = list(
            base_qs.filter(sector__iexact=stock.sector).values_list("symbol", flat=True)
        )
        if len(peers) < 3:
            return 0

        confidence = self._calc_confidence(len(peers), stock)

        PeerPreset.objects.update_or_create(
            symbol=stock,
            preset_key="sector_all",
            defaults={
                "display_name": "섹터 전체",
                "logic_summary": f"{stock.sector} 섹터 전체 {len(peers)}개와 비교",
                "peer_symbols": peers[:100],
                "peer_count": len(peers),
                "generation_method": "auto_sector",
                "confidence_score": confidence,
                "is_default": False,
                "is_active": True,
            },
        )
        return 1

    def _generate_size_peers(self, stock, base_qs, bucket: str) -> int:
        """체급 동종: 같은 sector + 같은 size bucket"""
        if not stock.sector:
            return 0

        qs = self._filter_by_size(base_qs.filter(sector__iexact=stock.sector), [bucket])
        peers = list(qs.values_list("symbol", flat=True))

        if len(peers) < 3:
            return 0

        bucket_label = {"mega": "초대형주(Mega Cap)", "large": "대형주(Large Cap)"}.get(
            bucket, bucket
        )
        confidence = self._calc_confidence(len(peers), stock)

        PeerPreset.objects.update_or_create(
            symbol=stock,
            preset_key="size_peers",
            defaults={
                "display_name": "체급 동종",
                "logic_summary": f"{stock.sector} 내 {bucket_label} {len(peers)}개와 비교",
                "peer_symbols": peers[:50],
                "peer_count": len(peers),
                "generation_method": "auto_size",
                "confidence_score": confidence,
                "is_default": False,
                "is_active": True,
            },
        )
        return 1

    def _filter_by_size(self, qs, buckets: list[str]):
        from django.db.models import Q

        conditions = Q()
        for bucket in buckets:
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

    def _generate_quality_top(self, stock, base_qs) -> int:
        """우량주 비교: sector 내 ROIC/Operating Margin/FCF Margin 상위 20%"""
        if not stock.sector:
            return 0

        sector_peers = list(
            base_qs.filter(sector__iexact=stock.sector).values_list("symbol", flat=True)
        )
        if len(sector_peers) < 25:
            return 0

        # 최신 fiscal_year 결정
        latest_fy = (
            CompanyMetricSnapshot.objects.filter(symbol_id=stock.symbol)
            .values_list("fiscal_year", flat=True)
            .distinct()
            .order_by("-fiscal_year")
            .first()
        )
        if not latest_fy:
            return 0

        # 특수 산업: ROIC → ROE
        from packages.shared.stocks.models import IndustryClassification

        is_special = False
        if stock.industry:
            ic = IndustryClassification.objects.filter(
                industry__iexact=stock.industry
            ).first()
            is_special = ic and ic.handling_mode == "special"

        quality_metrics = [
            "roe" if is_special else "roic",
            "operating_margin",
            "fcf_margin",
        ]

        # sector 내 모든 종목의 quality 지표 수집
        all_symbols = sector_peers + [stock.symbol]
        snaps = CompanyMetricSnapshot.objects.filter(
            symbol_id__in=all_symbols,
            fiscal_year=latest_fy,
            metric_code_id__in=quality_metrics,
            value_status="normal",
            metric_value__isnull=False,
        ).values("symbol_id", "metric_code_id", "metric_value")

        # 종목별 평균 percentile 계산
        from collections import defaultdict

        symbol_values = defaultdict(dict)
        for s in snaps:
            symbol_values[s["symbol_id"]][s["metric_code_id"]] = float(
                s["metric_value"]
            )

        # 각 지표별 percentile 계산
        symbol_scores = {}
        for sym, vals in symbol_values.items():
            if len(vals) < 2:  # 최소 2개 지표 필요
                continue
            pct_sum = 0
            pct_count = 0
            for mc in quality_metrics:
                if mc not in vals:
                    continue
                all_vals = sorted(
                    [v.get(mc, None) for s2, v in symbol_values.items() if mc in v]
                )
                all_vals = [v for v in all_vals if v is not None]
                if not all_vals:
                    continue
                rank = sum(1 for v in all_vals if v < vals[mc])
                pct = (rank / len(all_vals)) * 100
                pct_sum += pct
                pct_count += 1
            if pct_count > 0:
                symbol_scores[sym] = pct_sum / pct_count

        if not symbol_scores:
            return 0

        # 상위 20% 추출
        threshold = np.percentile(list(symbol_scores.values()), 80)
        top_symbols = [
            s
            for s, sc in symbol_scores.items()
            if sc >= threshold and s != stock.symbol
        ]

        if len(top_symbols) < 5:
            return 0

        confidence = self._calc_confidence(len(top_symbols), stock)

        PeerPreset.objects.update_or_create(
            symbol=stock,
            preset_key="quality_top",
            defaults={
                "display_name": "우량주 비교",
                "logic_summary": f"{stock.sector} 섹터 내 수익성 상위 {len(top_symbols)}개와 비교",
                "peer_symbols": top_symbols[:50],
                "peer_count": len(top_symbols),
                "generation_method": "auto_quality",
                "confidence_score": confidence,
                "is_default": False,
                "is_active": True,
            },
        )
        return 1

    def _generate_lifecycle(self, stock, base_qs) -> int:
        """성장단계 유사: sector 내 Revenue CAGR 3Y 기준 그룹핑"""
        if not stock.sector:
            return 0

        sector_peers = list(
            base_qs.filter(sector__iexact=stock.sector).values_list("symbol", flat=True)
        )
        if len(sector_peers) < 25:
            return 0

        all_symbols = sector_peers + [stock.symbol]

        # revenue_growth_yoy의 최신 값으로 성장 단계 근사
        latest_fy = (
            CompanyMetricSnapshot.objects.filter(symbol_id=stock.symbol)
            .values_list("fiscal_year", flat=True)
            .distinct()
            .order_by("-fiscal_year")
            .first()
        )
        if not latest_fy:
            return 0

        growth_snaps = CompanyMetricSnapshot.objects.filter(
            symbol_id__in=all_symbols,
            fiscal_year=latest_fy,
            metric_code_id="revenue_growth_yoy",
            value_status="normal",
            metric_value__isnull=False,
        ).values("symbol_id", "metric_value")

        growth_map = {s["symbol_id"]: float(s["metric_value"]) for s in growth_snaps}

        if len(growth_map) < 10:
            return 0

        # percentile 기준 그룹핑
        all_growths = list(growth_map.values())
        p25 = float(np.percentile(all_growths, 25))
        p75 = float(np.percentile(all_growths, 75))

        my_growth = growth_map.get(stock.symbol)
        if my_growth is None:
            return 0

        # 내 그룹 결정
        if my_growth > p75:
            group_label = "고성장"
            group_symbols = [
                s for s, g in growth_map.items() if g > p75 and s != stock.symbol
            ]
        elif my_growth >= p25:
            group_label = "안정형"
            group_symbols = [
                s
                for s, g in growth_map.items()
                if p25 <= g <= p75 and s != stock.symbol
            ]
        else:
            group_label = "저성장/턴어라운드"
            group_symbols = [
                s for s, g in growth_map.items() if g < p25 and s != stock.symbol
            ]

        if len(group_symbols) < 5:
            return 0

        confidence = self._calc_confidence(len(group_symbols), stock)

        PeerPreset.objects.update_or_create(
            symbol=stock,
            preset_key="lifecycle",
            defaults={
                "display_name": "성장단계 유사",
                "logic_summary": f"{group_label} {stock.sector} {len(group_symbols)}개와 비교 (매출 성장률 기준)",
                "peer_symbols": group_symbols[:50],
                "peer_count": len(group_symbols),
                "generation_method": "auto_lifecycle",
                "confidence_score": confidence,
                "is_default": False,
                "is_active": True,
            },
        )
        return 1

    def _generate_thematic(self, stock, base_qs) -> int:
        """
        Phase 6: 비즈니스 모델 유사 (Chain Sight DNA 기반)

        GrowthStage × CapitalDNA 조합으로 섹터 횡단 테마 클러스터링.
        같은 (stage, capital_type) 조합 = 비슷한 비즈니스 DNA.
        """
        from apps.chain_sight.models import CompanyCapitalDNA, CompanyGrowthStage

        # 내 프로파일 조회
        my_gs = CompanyGrowthStage.objects.filter(symbol_id=stock.symbol).first()
        my_cd = CompanyCapitalDNA.objects.filter(symbol_id=stock.symbol).first()

        if not my_gs or not my_cd:
            return 0

        my_stage = my_gs.stage
        my_capital = my_cd.capital_type

        # 같은 DNA 조합인 종목 찾기 (섹터 무관)
        same_stage_symbols = set(
            CompanyGrowthStage.objects.filter(stage=my_stage).values_list(
                "symbol_id", flat=True
            )
        )
        same_capital_symbols = set(
            CompanyCapitalDNA.objects.filter(capital_type=my_capital).values_list(
                "symbol_id", flat=True
            )
        )

        # 교집합 (같은 stage + 같은 capital_type)
        dna_peers = same_stage_symbols & same_capital_symbols
        dna_peers.discard(stock.symbol)

        # 다른 섹터 종목 위주 (같은 섹터는 이미 default/sector_all에서 커버)
        cross_sector_peers = [
            s
            for s in dna_peers
            if Stock.objects.filter(symbol=s)
            .exclude(sector__iexact=stock.sector or "")
            .exists()
        ]

        # 같은 섹터도 포함 (cross_sector가 적으면)
        all_dna_peers = list(dna_peers)

        # 최소 5개 필요
        target_peers = (
            cross_sector_peers if len(cross_sector_peers) >= 5 else all_dna_peers
        )
        if len(target_peers) < 5:
            return 0

        # 테마 라벨 생성
        STAGE_LABELS = {
            "mature": "성숙기",
            "accelerating": "성장기",
            "declining": "하락기",
            "turnaround": "턴어라운드",
            "cash_cow": "캐시카우",
            "early_growth": "초기성장",
        }
        CAPITAL_LABELS = {
            "balanced": "균형형",
            "heavy_investor": "적극투자형",
            "cash_hoarder": "현금축적형",
            "shareholder_first": "주주환원형",
            "aggressive_growth": "공격적성장형",
        }
        stage_label = STAGE_LABELS.get(my_stage, my_stage)
        capital_label = CAPITAL_LABELS.get(my_capital, my_capital)
        theme_label = f"{stage_label} + {capital_label}"

        is_cross = len(cross_sector_peers) >= 5
        summary = (
            f"섹터 횡단 {theme_label} DNA 유사 {len(target_peers)}개"
            if is_cross
            else f"{theme_label} DNA 유사 {len(target_peers)}개"
        )

        confidence = self._calc_confidence(len(target_peers), stock)
        if is_cross:
            confidence = min(confidence + 0.1, 1.0)  # cross-sector 보너스

        PeerPreset.objects.update_or_create(
            symbol=stock,
            preset_key="thematic",
            defaults={
                "display_name": f"비즈니스 DNA ({theme_label})",
                "logic_summary": summary,
                "peer_symbols": target_peers[:50],
                "peer_count": len(target_peers),
                "generation_method": "curated",
                "confidence_score": confidence,
                "is_default": False,
                "is_active": True,
            },
        )
        return 1

    def _calc_confidence(self, peer_count: int, stock) -> float:
        """confidence_score 계산 (설계서 섹션 5)"""
        score = 1.0
        if peer_count < 5:
            score -= 0.3
        elif peer_count < 10:
            score -= 0.1

        # 특수 산업 패널티
        from packages.shared.stocks.models import IndustryClassification

        if stock.industry:
            ic = IndustryClassification.objects.filter(
                industry__iexact=stock.industry
            ).first()
            if ic and ic.handling_mode == "special":
                score -= 0.15

        return max(0.0, min(1.0, score))
