"""
RelationshipService - 종목 간 관계 동기화 서비스

Chain Sight Stock 기능을 위한 관계 데이터 관리.
FMP API와 NewsEntity를 사용하여 종목 간 관계를 동기화합니다.

Relationship Types:
- PEER_OF: 경쟁사 (FMP Peers API)
- SAME_INDUSTRY: 동일 산업 (FMP Profile)
- CO_MENTIONED: 뉴스 동시언급 (NewsEntity)
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from serverless.models import StockRelationship
from serverless.services.fmp_client import FMPClient, FMPAPIError


logger = logging.getLogger(__name__)


class RelationshipService:
    """
    종목 관계 동기화 서비스

    Usage:
        service = RelationshipService()

        # 피어 동기화
        count = service.sync_peers('NVDA')

        # 산업 동기화
        count = service.sync_industry('NVDA')

        # 뉴스 동시언급 동기화
        count = service.sync_co_mentioned('NVDA')

        # 관계 조회
        peers = service.get_relationships('NVDA', 'PEER_OF')
    """

    def __init__(self):
        self.fmp_client = FMPClient()

    def sync_peers(self, symbol: str) -> int:
        """
        FMP Peers API를 사용하여 경쟁사 관계 동기화

        /stable/stock-peers 엔드포인트 사용 (Starter Plan 지원)

        Args:
            symbol: 종목 심볼

        Returns:
            동기화된 관계 수
        """
        symbol = symbol.upper()
        logger.info(f"피어 동기화 시작: {symbol}")

        try:
            # FMP Peers API 호출 (/stable/stock-peers)
            peers = self.fmp_client.get_stock_peers(symbol)

            if not peers:
                logger.warning(f"피어 데이터 없음: {symbol}")
                return 0

            # 원본 종목의 시가총액 조회 (강도 계산용)
            try:
                profile = self.fmp_client.get_company_profile(symbol)
                source_mc = profile.get('mktCap', 0)
            except FMPAPIError:
                source_mc = 0

            count = 0
            for peer in peers[:20]:  # 최대 20개
                peer_symbol = peer.get('symbol')
                if not peer_symbol or peer_symbol == symbol:
                    continue

                try:
                    # 시가총액 유사도 기반 강도 계산
                    peer_mc = peer.get('mktCap', 0)
                    strength = self._calculate_market_cap_similarity(source_mc, peer_mc)

                    self._create_or_update_relationship(
                        source_symbol=symbol,
                        target_symbol=peer_symbol,
                        relationship_type='PEER_OF',
                        strength=strength,
                        source_provider='fmp',
                        context={
                            'source': 'FMP Stock Peers API',
                            'peer_name': peer.get('companyName'),
                            'peer_price': peer.get('price'),
                        }
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"피어 관계 생성 실패 {symbol} -> {peer_symbol}: {e}")
                    continue

            logger.info(f"피어 동기화 완료: {symbol} -> {count}개")
            return count

        except FMPAPIError as e:
            logger.error(f"FMP 피어 API 에러: {e}")
            return 0

    def sync_industry(self, symbol: str) -> int:
        """
        같은 산업 내 종목 관계 동기화

        Args:
            symbol: 종목 심볼

        Returns:
            동기화된 관계 수
        """
        symbol = symbol.upper()
        logger.info(f"산업 동기화 시작: {symbol}")

        try:
            # 종목 프로필 조회
            profile = self.fmp_client.get_company_profile(symbol)
            industry = profile.get('industry')

            if not industry:
                logger.warning(f"산업 정보 없음: {symbol}")
                return 0

            # 같은 산업 종목 조회
            industry_stocks = self.fmp_client.get_industry_stocks(industry, limit=30)

            count = 0
            for stock in industry_stocks:
                target_symbol = stock.get('symbol')
                if not target_symbol or target_symbol == symbol:
                    continue

                try:
                    # 관계 생성 (강도는 시가총액 유사도 기반)
                    source_mc = profile.get('mktCap', 0)
                    target_mc = stock.get('marketCap', 0)

                    strength = self._calculate_market_cap_similarity(source_mc, target_mc)

                    self._create_or_update_relationship(
                        source_symbol=symbol,
                        target_symbol=target_symbol,
                        relationship_type='SAME_INDUSTRY',
                        strength=strength,
                        source_provider='fmp',
                        context={
                            'industry': industry,
                            'sector': profile.get('sector'),
                            'source': 'FMP Industry Screener'
                        }
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"산업 관계 생성 실패 {symbol} -> {target_symbol}: {e}")
                    continue

            logger.info(f"산업 동기화 완료: {symbol} -> {count}개 ({industry})")
            return count

        except FMPAPIError as e:
            logger.error(f"FMP 프로필 API 에러: {e}")
            return 0

    def sync_co_mentioned(self, symbol: str, days: int = 7) -> int:
        """
        최근 N일 뉴스에서 동시 언급된 종목 관계 동기화

        Args:
            symbol: 종목 심볼
            days: 조회할 기간 (기본 7일)

        Returns:
            동기화된 관계 수
        """
        from news.models import NewsEntity
        from django.db.models import Count

        symbol = symbol.upper()
        logger.info(f"뉴스 동시언급 동기화 시작: {symbol} (최근 {days}일)")

        cutoff_date = timezone.now() - timedelta(days=days)

        try:
            # 해당 종목이 언급된 뉴스 조회
            # NewsEntity 모델 필드: symbol, entity_type ('equity' 등)
            mentioned_news_ids = NewsEntity.objects.filter(
                entity_type='equity',
                symbol=symbol,
                news__published_at__gte=cutoff_date
            ).values_list('news_id', flat=True).distinct()

            if not mentioned_news_ids:
                logger.info(f"뉴스 언급 없음: {symbol}")
                return 0

            # 같은 뉴스에서 언급된 다른 종목 조회
            co_mentioned = NewsEntity.objects.filter(
                entity_type='equity',
                news_id__in=mentioned_news_ids
            ).exclude(
                symbol=symbol
            ).values('symbol').annotate(
                mention_count=Count('id')
            ).order_by('-mention_count')[:30]

            count = 0
            for item in co_mentioned:
                target_symbol = item['symbol']
                mention_count = item['mention_count']

                try:
                    # 강도는 동시 언급 횟수 기반 (정규화)
                    max_mentions = co_mentioned[0]['mention_count'] if co_mentioned else 1
                    strength = Decimal(str(min(1.0, mention_count / max_mentions)))

                    self._create_or_update_relationship(
                        source_symbol=symbol,
                        target_symbol=target_symbol,
                        relationship_type='CO_MENTIONED',
                        strength=strength,
                        source_provider='news',
                        context={
                            'mention_count': mention_count,
                            'period_days': days,
                            'source': 'NewsEntity Co-mention'
                        }
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"동시언급 관계 생성 실패 {symbol} -> {target_symbol}: {e}")
                    continue

            logger.info(f"뉴스 동시언급 동기화 완료: {symbol} -> {count}개")
            return count

        except Exception as e:
            logger.error(f"뉴스 동시언급 동기화 에러: {e}")
            return 0

    def sync_all(self, symbol: str) -> Dict[str, int]:
        """
        종목의 모든 관계 동기화

        Args:
            symbol: 종목 심볼

        Returns:
            {
                'peer_count': 10,
                'industry_count': 15,
                'co_mentioned_count': 5,
                'supply_chain_count': 3
            }
        """
        symbol = symbol.upper()

        return {
            'peer_count': self.sync_peers(symbol),
            'industry_count': self.sync_industry(symbol),
            'co_mentioned_count': self.sync_co_mentioned(symbol),
        }

    def sync_supply_chain(self, symbol: str) -> Dict[str, int]:
        """
        Phase 4: 공급망 관계 동기화

        SEC 10-K에서 공급사/고객사 관계를 추출하여 동기화합니다.

        Args:
            symbol: 종목 심볼

        Returns:
            {
                'customer_count': 3,
                'supplier_count': 2,
                'status': 'success'
            }
        """
        symbol = symbol.upper()
        logger.info(f"공급망 동기화 시작: {symbol}")

        try:
            from serverless.services.supply_chain_service import SupplyChainService
            service = SupplyChainService()
            result = service.sync_supply_chain(symbol)

            return {
                'customer_count': result.get('customer_count', 0),
                'supplier_count': result.get('supplier_count', 0),
                'status': result.get('status', 'unknown')
            }

        except Exception as e:
            logger.error(f"공급망 동기화 실패 {symbol}: {e}")
            return {
                'customer_count': 0,
                'supplier_count': 0,
                'status': 'error',
                'error': str(e)
            }

    def get_relationships(
        self,
        symbol: str,
        relationship_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        종목의 관계 조회

        Args:
            symbol: 종목 심볼
            relationship_type: 관계 타입 (None이면 전체)
            limit: 최대 반환 개수

        Returns:
            [
                {
                    'target_symbol': 'AMD',
                    'relationship_type': 'PEER_OF',
                    'strength': 0.85,
                    'context': {...},
                    'discovered_at': datetime
                }
            ]
        """
        symbol = symbol.upper()

        queryset = StockRelationship.objects.filter(
            source_symbol=symbol
        ).order_by('-strength')

        if relationship_type:
            queryset = queryset.filter(relationship_type=relationship_type)

        relationships = queryset[:limit]

        return [
            {
                'target_symbol': r.target_symbol,
                'relationship_type': r.relationship_type,
                'relationship_type_display': dict(StockRelationship.RELATIONSHIP_TYPES).get(
                    r.relationship_type, r.relationship_type
                ),
                'strength': float(r.strength),
                'context': r.context,
                'source_provider': r.source_provider,
                'discovered_at': r.discovered_at.isoformat(),
            }
            for r in relationships
        ]

    def get_relationship_counts(self, symbol: str) -> Dict[str, int]:
        """
        관계 타입별 개수 조회

        Args:
            symbol: 종목 심볼

        Returns:
            {'PEER_OF': 10, 'SAME_INDUSTRY': 15, 'CO_MENTIONED': 5}
        """
        from django.db.models import Count

        symbol = symbol.upper()

        counts = StockRelationship.objects.filter(
            source_symbol=symbol
        ).values('relationship_type').annotate(
            count=Count('id')
        )

        return {item['relationship_type']: item['count'] for item in counts}

    def has_relationships(self, symbol: str) -> bool:
        """종목이 관계 데이터를 가지고 있는지 확인"""
        return StockRelationship.objects.filter(source_symbol=symbol.upper()).exists()

    def get_target_profile(self, symbol: str) -> Optional[Dict]:
        """
        관계 대상 종목의 프로필 + 시세 조회 (캐시 활용)

        Args:
            symbol: 종목 심볼

        Returns:
            프로필 정보 또는 None
        """
        try:
            profile = self.fmp_client.get_company_profile(symbol)

            # Quote API에서 가격 변동/시가총액 조회
            try:
                quote = self.fmp_client.get_quote(symbol)
                price = quote.get('price')
                change = quote.get('change')
                change_percentage = quote.get('changePercentage')
                market_cap = quote.get('marketCap')
            except FMPAPIError:
                price = profile.get('price')
                change = None
                change_percentage = None
                market_cap = profile.get('mktCap')

            return {
                'symbol': symbol,
                'company_name': profile.get('companyName'),
                'sector': profile.get('sector'),
                'industry': profile.get('industry'),
                'price': price,
                'change': change,
                'changes_percentage': change_percentage,
                'market_cap': market_cap,
            }
        except FMPAPIError:
            return None

    # ========================================
    # Private Methods
    # ========================================

    def _create_or_update_relationship(
        self,
        source_symbol: str,
        target_symbol: str,
        relationship_type: str,
        strength: Decimal,
        source_provider: str,
        context: Dict
    ) -> StockRelationship:
        """관계 생성 또는 업데이트"""
        relationship, created = StockRelationship.objects.update_or_create(
            source_symbol=source_symbol.upper(),
            target_symbol=target_symbol.upper(),
            relationship_type=relationship_type,
            defaults={
                'strength': strength,
                'source_provider': source_provider,
                'context': context,
                'last_verified_at': timezone.now(),
            }
        )

        if created:
            logger.debug(f"관계 생성: {source_symbol} -> {target_symbol} ({relationship_type})")
        else:
            logger.debug(f"관계 업데이트: {source_symbol} -> {target_symbol} ({relationship_type})")

        return relationship

    def _calculate_market_cap_similarity(
        self,
        source_mc: float,
        target_mc: float
    ) -> Decimal:
        """시가총액 유사도 계산 (0.0 ~ 1.0)"""
        if not source_mc or not target_mc:
            return Decimal('0.5')

        # 로그 스케일로 비교
        import math
        log_source = math.log10(source_mc) if source_mc > 0 else 0
        log_target = math.log10(target_mc) if target_mc > 0 else 0

        # 차이가 작을수록 유사도 높음 (최대 2 orders of magnitude 허용)
        diff = abs(log_source - log_target)
        similarity = max(0, 1 - diff / 2)

        return Decimal(str(round(similarity, 3)))


# Django models import (lazy)
from django.db import models
