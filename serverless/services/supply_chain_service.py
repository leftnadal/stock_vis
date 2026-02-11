"""
Supply Chain Service - 공급망 관계 동기화 서비스

SEC 10-K에서 추출한 공급사/고객사 관계를 PostgreSQL 및 Neo4j에 동기화합니다.

Usage:
    service = SupplyChainService()

    # 단일 종목 동기화
    result = service.sync_supply_chain('TSM')

    # 배치 동기화
    result = service.sync_batch(['TSM', 'NVDA', 'AAPL'])

    # 공급망 조회
    supply_chain = service.get_supply_chain('TSM')
"""
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from api_request.sec_edgar_client import SECEdgarClient, SECEdgarError
from serverless.services.supply_chain_parser import SupplyChainParser, SupplyChainRelation
from serverless.models import StockRelationship


logger = logging.getLogger(__name__)


class SupplyChainService:
    """
    공급망 관계 동기화 서비스

    주요 기능:
    1. SEC 10-K 다운로드 및 파싱
    2. PostgreSQL StockRelationship 저장
    3. Neo4j 그래프 동기화
    4. 캐싱 및 배치 처리
    """

    # 캐시 TTL: 30일 (10-K는 연간 보고서)
    CACHE_TTL = 60 * 60 * 24 * 30

    # 배치 처리 간 대기 시간 (SEC rate limit 준수)
    BATCH_DELAY = 0.2  # 200ms

    def __init__(self):
        """Initialize service"""
        self.edgar_client = SECEdgarClient()
        self.parser = SupplyChainParser()

    def sync_supply_chain(self, symbol: str) -> Dict[str, Any]:
        """
        단일 종목 공급망 동기화

        Args:
            symbol: 종목 심볼

        Returns:
            {
                'symbol': 'TSM',
                'status': 'success',
                'customers': [
                    {
                        'symbol': 'AAPL',
                        'name': 'Apple Inc.',
                        'confidence': 'high',
                        'revenue_percent': 25
                    }
                ],
                'suppliers': [...],
                'customer_count': 3,
                'supplier_count': 2,
                'processing_time_ms': 5000
            }
        """
        symbol = symbol.upper()
        start_time = time.time()

        logger.info(f"Supply chain sync started: {symbol}")

        # 캐시 확인
        cache_key = f'supply_chain:{symbol}'
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Supply chain cache hit: {symbol}")
            cached['cached'] = True
            return cached

        try:
            # 1. SEC 10-K 다운로드
            text = self._download_10k(symbol)
            if not text:
                return self._error_result(symbol, "10-K not found", start_time)

            # 2. Item 1A 추출 및 파싱
            item_1a = self.edgar_client.extract_item_1a(text)
            relations = self.parser.parse_10k(item_1a, symbol)

            if not relations:
                # 전체 텍스트로 재시도
                logger.info(f"Retrying with full text for {symbol}")
                relations = self.parser.parse_10k(text[:200000], symbol)

            # 3. 관계 분류
            customers = [r for r in relations if r.relation_type == 'customer']
            suppliers = [r for r in relations if r.relation_type == 'supplier']

            # 4. PostgreSQL 저장
            saved_count = self._save_relationships(symbol, relations)

            # 5. Neo4j 동기화
            neo4j_synced = self._sync_to_neo4j(symbol, relations)

            # 결과 구성
            result = {
                'symbol': symbol,
                'status': 'success',
                'customers': [r.to_dict() for r in customers],
                'suppliers': [r.to_dict() for r in suppliers],
                'customer_count': len(customers),
                'supplier_count': len(suppliers),
                'saved_count': saved_count,
                'neo4j_synced': neo4j_synced,
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'cached': False
            }

            # 캐시 저장
            cache.set(cache_key, result, self.CACHE_TTL)

            logger.info(
                f"Supply chain sync completed: {symbol} - "
                f"{len(customers)} customers, {len(suppliers)} suppliers"
            )

            return result

        except SECEdgarError as e:
            logger.error(f"SEC EDGAR error for {symbol}: {e}")
            return self._error_result(symbol, str(e), start_time)

        except Exception as e:
            logger.exception(f"Supply chain sync failed for {symbol}: {e}")
            return self._error_result(symbol, str(e), start_time)

    def sync_batch(
        self,
        symbols: List[str],
        delay: float = None
    ) -> Dict[str, Any]:
        """
        배치 공급망 동기화

        Args:
            symbols: 종목 심볼 리스트
            delay: 종목 간 대기 시간 (초)

        Returns:
            {
                'total': 10,
                'success': 8,
                'failed': 2,
                'results': {...},
                'failed_symbols': ['UNKNOWN1', 'UNKNOWN2']
            }
        """
        delay = delay or self.BATCH_DELAY

        logger.info(f"Supply chain batch sync started: {len(symbols)} symbols")

        results = {}
        success_count = 0
        failed_symbols = []

        for symbol in symbols:
            try:
                result = self.sync_supply_chain(symbol)

                if result['status'] == 'success':
                    success_count += 1
                else:
                    failed_symbols.append(symbol)

                results[symbol] = result

            except Exception as e:
                logger.error(f"Batch sync error for {symbol}: {e}")
                failed_symbols.append(symbol)
                results[symbol] = {
                    'symbol': symbol,
                    'status': 'error',
                    'error': str(e)
                }

            # Rate limit 준수
            time.sleep(delay)

        return {
            'total': len(symbols),
            'success': success_count,
            'failed': len(failed_symbols),
            'results': results,
            'failed_symbols': failed_symbols
        }

    def get_supply_chain(self, symbol: str) -> Dict[str, Any]:
        """
        종목의 공급망 조회 (캐시 우선)

        Args:
            symbol: 종목 심볼

        Returns:
            {
                'symbol': 'TSM',
                'suppliers': [...],
                'customers': [...],
                'last_updated': '2026-01-15'
            }
        """
        symbol = symbol.upper()

        # 캐시 확인
        cache_key = f'supply_chain:{symbol}'
        cached = cache.get(cache_key)
        if cached:
            return {
                'symbol': symbol,
                'suppliers': cached.get('suppliers', []),
                'customers': cached.get('customers', []),
                'cached': True
            }

        # DB 조회
        suppliers = self._get_relationships(symbol, 'SUPPLIED_BY')
        customers = self._get_relationships(symbol, 'CUSTOMER_OF')

        return {
            'symbol': symbol,
            'suppliers': suppliers,
            'customers': customers,
            'cached': False
        }

    def get_suppliers(self, symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
        """종목의 공급사 목록 조회"""
        return self._get_relationships(symbol, 'SUPPLIED_BY', limit)

    def get_customers(self, symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
        """종목의 고객사 목록 조회"""
        return self._get_relationships(symbol, 'CUSTOMER_OF', limit)

    def clear_cache(self, symbol: str) -> bool:
        """종목 캐시 삭제"""
        cache_key = f'supply_chain:{symbol.upper()}'
        return cache.delete(cache_key)

    # ========================================
    # Private Methods
    # ========================================

    def _download_10k(self, symbol: str) -> Optional[str]:
        """10-K 다운로드"""
        try:
            text = self.edgar_client.download_latest_10k(symbol)
            return text
        except SECEdgarError as e:
            logger.warning(f"10-K download failed for {symbol}: {e}")
            return None

    @transaction.atomic
    def _save_relationships(
        self,
        symbol: str,
        relations: List[SupplyChainRelation]
    ) -> int:
        """
        PostgreSQL에 관계 저장

        Args:
            symbol: 소스 종목 심볼
            relations: 추출된 관계 리스트

        Returns:
            저장된 관계 수
        """
        saved_count = 0

        for rel in relations:
            try:
                # 관계 타입 매핑
                if rel.relation_type == 'customer':
                    # 분석 대상(source)이 판매자, target이 고객
                    # source -> CUSTOMER_OF -> target
                    relationship_type = 'CUSTOMER_OF'
                else:
                    # 분석 대상(source)이 구매자, target이 공급사
                    # source -> SUPPLIED_BY -> target
                    relationship_type = 'SUPPLIED_BY'

                # target_symbol이 없으면 저장하지 않음
                # (티커 매칭 실패한 회사는 제외)
                if not rel.target_symbol:
                    logger.debug(f"Skipping unmatched company: {rel.target_name}")
                    continue

                # 강도 계산 (confidence + revenue_percent 기반)
                strength = self._calculate_strength(rel)

                # 컨텍스트 구성
                context = {
                    'company_name': rel.target_name,
                    'confidence': rel.confidence,
                    'revenue_percent': rel.revenue_percent,
                    'evidence': rel.evidence[:500] if rel.evidence else None,
                    'source': 'SEC 10-K',
                    'extracted_at': timezone.now().isoformat()
                }

                # upsert
                relationship, created = StockRelationship.objects.update_or_create(
                    source_symbol=symbol,
                    target_symbol=rel.target_symbol,
                    relationship_type=relationship_type,
                    defaults={
                        'strength': strength,
                        'source_provider': 'sec_10k',
                        'context': context,
                        'last_verified_at': timezone.now()
                    }
                )

                saved_count += 1

                if created:
                    logger.debug(
                        f"Created relationship: {symbol} -> {rel.target_symbol} "
                        f"({relationship_type})"
                    )
                else:
                    logger.debug(
                        f"Updated relationship: {symbol} -> {rel.target_symbol} "
                        f"({relationship_type})"
                    )

            except Exception as e:
                logger.warning(f"Failed to save relationship: {e}")
                continue

        return saved_count

    def _sync_to_neo4j(
        self,
        symbol: str,
        relations: List[SupplyChainRelation]
    ) -> int:
        """
        Neo4j에 관계 동기화

        Args:
            symbol: 소스 종목 심볼
            relations: 추출된 관계 리스트

        Returns:
            동기화된 관계 수
        """
        try:
            from serverless.services.neo4j_chain_sight_service import Neo4jChainSightService
            neo4j_service = Neo4jChainSightService()

            if not neo4j_service.is_available():
                logger.debug("Neo4j not available, skipping sync")
                return 0

            synced_count = 0

            for rel in relations:
                if not rel.target_symbol:
                    continue

                try:
                    # Neo4j 관계 타입 매핑
                    if rel.relation_type == 'customer':
                        neo4j_rel_type = 'CUSTOMER_OF'
                    else:
                        neo4j_rel_type = 'SUPPLIES_TO'

                    # Stock 노드 생성 (없으면)
                    neo4j_service.create_stock_node(
                        symbol=rel.target_symbol,
                        name=rel.target_name
                    )

                    # 관계 생성
                    strength = float(self._calculate_strength(rel))
                    context = {
                        'confidence': rel.confidence,
                        'revenue_percent': rel.revenue_percent,
                        'source': 'SEC 10-K'
                    }

                    success = neo4j_service.create_relationship(
                        source_symbol=symbol,
                        target_symbol=rel.target_symbol,
                        rel_type=neo4j_rel_type,
                        weight=strength,
                        source_provider='sec_10k',
                        context=context
                    )

                    if success:
                        synced_count += 1

                except Exception as e:
                    logger.warning(f"Neo4j sync failed for {rel.target_symbol}: {e}")
                    continue

            return synced_count

        except ImportError:
            logger.debug("Neo4j service not available")
            return 0
        except Exception as e:
            logger.warning(f"Neo4j sync error: {e}")
            return 0

    def _calculate_strength(self, rel: SupplyChainRelation) -> Decimal:
        """
        관계 강도 계산

        Args:
            rel: SupplyChainRelation

        Returns:
            Decimal 0.0 ~ 1.0
        """
        base_strength = {
            'high': 0.9,
            'medium-high': 0.7,
            'medium': 0.5
        }.get(rel.confidence, 0.5)

        # 매출 비중에 따른 보정
        if rel.revenue_percent:
            if rel.revenue_percent >= 20:
                base_strength = min(1.0, base_strength + 0.1)
            elif rel.revenue_percent >= 10:
                base_strength = min(1.0, base_strength + 0.05)

        return Decimal(str(round(base_strength, 3)))

    def _get_relationships(
        self,
        symbol: str,
        relationship_type: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """DB에서 관계 조회"""
        relationships = StockRelationship.objects.filter(
            source_symbol=symbol.upper(),
            relationship_type=relationship_type
        ).order_by('-strength')[:limit]

        results = []
        for rel in relationships:
            context = rel.context or {}
            results.append({
                'symbol': rel.target_symbol,
                'company_name': context.get('company_name', rel.target_symbol),
                'confidence': context.get('confidence', 'medium'),
                'revenue_percent': context.get('revenue_percent'),
                'strength': float(rel.strength),
                'evidence': context.get('evidence', ''),
                'source_provider': rel.source_provider,
                'last_verified_at': rel.last_verified_at.isoformat() if rel.last_verified_at else None
            })

        return results

    def _error_result(
        self,
        symbol: str,
        error: str,
        start_time: float
    ) -> Dict[str, Any]:
        """에러 결과 생성"""
        return {
            'symbol': symbol,
            'status': 'error',
            'error': error,
            'customers': [],
            'suppliers': [],
            'customer_count': 0,
            'supplier_count': 0,
            'processing_time_ms': int((time.time() - start_time) * 1000),
            'cached': False
        }


# ========================================
# Convenience Functions
# ========================================

def sync_supply_chain_for_symbol(symbol: str) -> Dict[str, Any]:
    """단일 종목 공급망 동기화 (편의 함수)"""
    service = SupplyChainService()
    return service.sync_supply_chain(symbol)


def get_supply_chain_for_symbol(symbol: str) -> Dict[str, Any]:
    """종목 공급망 조회 (편의 함수)"""
    service = SupplyChainService()
    return service.get_supply_chain(symbol)
