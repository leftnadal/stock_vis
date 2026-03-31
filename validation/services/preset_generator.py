"""
Peer 프리셋 자동 생성 서비스

Phase 2: default, sector_all, size_peers
Phase 3: quality_top, lifecycle (추후)
"""

import logging
from stocks.models import Stock, SP500Constituent
from validation.models import PeerPreset
from validation.services.benchmark_calculator import assign_size_bucket, get_adjacent_buckets

logger = logging.getLogger(__name__)


class PresetGenerator:
    """종목당 프리셋 자동 생성"""

    def generate_for_symbol(self, symbol: str) -> dict:
        symbol = symbol.upper()
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            return {'symbol': symbol, 'error': 'Stock not found'}

        sp500_symbols = set(
            SP500Constituent.objects.filter(is_active=True)
            .values_list('symbol', flat=True)
        )
        base_qs = Stock.objects.filter(symbol__in=sp500_symbols).exclude(symbol=symbol)

        presets_created = 0

        # 1. default (업종 표준)
        presets_created += self._generate_default(stock, base_qs)

        # 2. sector_all (섹터 전체)
        presets_created += self._generate_sector_all(stock, base_qs)

        # 3. size_peers (체급 동종) — mega/large만
        mcap = float(stock.market_capitalization) if stock.market_capitalization else None
        bucket = assign_size_bucket(mcap)
        if bucket in ('mega', 'large'):
            presets_created += self._generate_size_peers(stock, base_qs, bucket)

        return {'symbol': symbol, 'presets_created': presets_created}

    def generate_for_symbols(self, symbols: list[str] = None) -> dict:
        if symbols is None:
            symbols = list(
                SP500Constituent.objects.filter(is_active=True)
                .values_list('symbol', flat=True)
            )

        total = len(symbols)
        success = 0
        for i, sym in enumerate(symbols):
            try:
                r = self.generate_for_symbol(sym)
                if not r.get('error'):
                    success += 1
            except Exception as e:
                logger.error(f"preset gen failed {sym}: {e}")

            if (i + 1) % 50 == 0:
                logger.info(f"Preset gen: {i+1}/{total}")

        return {'total': total, 'success': success}

    def _generate_default(self, stock, base_qs) -> int:
        """업종 표준: industry + size bucket fallback"""
        mcap = float(stock.market_capitalization) if stock.market_capitalization else None
        bucket = assign_size_bucket(mcap)
        adjacent = get_adjacent_buckets(bucket)

        peers = []
        basis = 'industry_size'
        summary = ''

        if stock.industry:
            # Step 1: industry + adjacent size
            qs = self._filter_by_size(
                base_qs.filter(industry__iexact=stock.industry), adjacent
            )
            if qs.count() >= 8:
                peers = list(qs.values_list('symbol', flat=True))
                summary = f"{stock.industry} 업종 내 유사 시가총액 {len(peers)}개"
            else:
                # Step 2: industry 전체
                qs = base_qs.filter(industry__iexact=stock.industry)
                if qs.count() >= 5:
                    peers = list(qs.values_list('symbol', flat=True))
                    basis = 'industry'
                    summary = f"{stock.industry} 업종 전체 {len(peers)}개"

        if not peers and stock.sector:
            # Step 3: sector fallback
            qs = base_qs.filter(sector__iexact=stock.sector)
            peers = list(qs.values_list('symbol', flat=True))
            basis = 'sector'
            summary = f"{stock.sector} 섹터 전체 {len(peers)}개"

        if not peers:
            return 0

        confidence = self._calc_confidence(len(peers), stock)

        PeerPreset.objects.update_or_create(
            symbol=stock, preset_key='default',
            defaults={
                'display_name': '업종 표준',
                'logic_summary': summary,
                'peer_symbols': peers[:50],
                'peer_count': len(peers),
                'generation_method': f'auto_{basis.split("_")[0]}',
                'confidence_score': confidence,
                'is_default': True,
                'is_active': True,
            }
        )
        return 1

    def _generate_sector_all(self, stock, base_qs) -> int:
        """섹터 전체: 같은 sector S&P 500 전체"""
        if not stock.sector:
            return 0

        peers = list(
            base_qs.filter(sector__iexact=stock.sector)
            .values_list('symbol', flat=True)
        )
        if len(peers) < 3:
            return 0

        confidence = self._calc_confidence(len(peers), stock)

        PeerPreset.objects.update_or_create(
            symbol=stock, preset_key='sector_all',
            defaults={
                'display_name': '섹터 전체',
                'logic_summary': f"{stock.sector} 섹터 전체 {len(peers)}개와 비교",
                'peer_symbols': peers[:100],
                'peer_count': len(peers),
                'generation_method': 'auto_sector',
                'confidence_score': confidence,
                'is_default': False,
                'is_active': True,
            }
        )
        return 1

    def _generate_size_peers(self, stock, base_qs, bucket: str) -> int:
        """체급 동종: 같은 sector + 같은 size bucket"""
        if not stock.sector:
            return 0

        qs = self._filter_by_size(
            base_qs.filter(sector__iexact=stock.sector), [bucket]
        )
        peers = list(qs.values_list('symbol', flat=True))

        if len(peers) < 3:
            return 0

        bucket_label = {'mega': '초대형주(Mega Cap)', 'large': '대형주(Large Cap)'}.get(bucket, bucket)
        confidence = self._calc_confidence(len(peers), stock)

        PeerPreset.objects.update_or_create(
            symbol=stock, preset_key='size_peers',
            defaults={
                'display_name': '체급 동종',
                'logic_summary': f"{stock.sector} 내 {bucket_label} {len(peers)}개와 비교",
                'peer_symbols': peers[:50],
                'peer_count': len(peers),
                'generation_method': 'auto_size',
                'confidence_score': confidence,
                'is_default': False,
                'is_active': True,
            }
        )
        return 1

    def _filter_by_size(self, qs, buckets: list[str]):
        from django.db.models import Q
        conditions = Q()
        for bucket in buckets:
            if bucket == 'mega':
                conditions |= Q(market_capitalization__gte=200_000_000_000)
            elif bucket == 'large':
                conditions |= Q(market_capitalization__gte=10_000_000_000, market_capitalization__lt=200_000_000_000)
            elif bucket == 'mid':
                conditions |= Q(market_capitalization__gte=2_000_000_000, market_capitalization__lt=10_000_000_000)
            elif bucket == 'small':
                conditions |= Q(market_capitalization__lt=2_000_000_000)
        return qs.filter(conditions)

    def _calc_confidence(self, peer_count: int, stock) -> float:
        """confidence_score 계산 (설계서 섹션 5)"""
        score = 1.0
        if peer_count < 5:
            score -= 0.3
        elif peer_count < 10:
            score -= 0.1

        # 특수 산업 패널티
        from stocks.models import IndustryClassification
        if stock.industry:
            ic = IndustryClassification.objects.filter(industry__iexact=stock.industry).first()
            if ic and ic.handling_mode == 'special':
                score -= 0.15

        return max(0.0, min(1.0, score))
