"""
Neo4j Service - Lightweight Graph Queries

Critical: 모든 메서드는 Neo4j가 없어도 fallback 데이터를 반환해야 함
"""

import logging
from typing import Optional, List, Dict, Any
from neo4j import Session
from .neo4j_driver import get_neo4j_driver

logger = logging.getLogger(__name__)


class Neo4jServiceLite:
    """
    Neo4j 그래프 쿼리 서비스 (Lite 버전)

    Features:
        - Supply chain relationships
        - Competitor analysis
        - Sector peer discovery
        - Health check

    Safety:
        - Neo4j 연결 실패 시 빈 데이터 반환 (앱 중단 없음)
        - 모든 쿼리에 timeout 적용
    """

    QUERY_TIMEOUT = 2000  # ms (2초)
    MAX_RESULTS = 5  # 각 카테고리별 최대 결과 수

    def __init__(self):
        self.driver = get_neo4j_driver()

    def get_stock_relationships(
        self,
        symbol: str,
        max_depth: int = 1
    ) -> Dict[str, Any]:
        """
        종목의 관계 정보 조회

        Args:
            symbol: 종목 심볼 (e.g., 'AAPL')
            max_depth: 관계 탐색 깊이 (기본 1)

        Returns:
            {
                'symbol': 'AAPL',
                'supply_chain': [...],
                'competitors': [...],
                'sector_peers': [...],
                '_meta': {'source': 'neo4j' | 'fallback', '_error': None | str}
            }
        """
        if self.driver is None:
            logger.warning(f"Neo4j unavailable - returning empty relationships for {symbol}")
            return self._empty_relationships(symbol, 'neo4j_unavailable')

        try:
            with self.driver.session() as session:
                # 공급망 관계 조회
                supply_chain = self._get_supply_chain(session, symbol)

                # 경쟁사 조회
                competitors = self._get_competitors(session, symbol)

                # 섹터 동료 조회
                sector_peers = self._get_sector_peers(session, symbol)

                return {
                    'symbol': symbol,
                    'supply_chain': supply_chain,
                    'competitors': competitors,
                    'sector_peers': sector_peers,
                    '_meta': {
                        'source': 'neo4j',
                        '_error': None,
                        'max_depth': max_depth,
                    }
                }

        except Exception as e:
            logger.error(f"Neo4j query error for {symbol}: {e}")
            return self._empty_relationships(symbol, str(e))

    def _get_supply_chain(self, session: Session, symbol: str) -> List[Dict[str, Any]]:
        """
        공급망 관계 조회 (SUPPLIES, SUPPLIED_BY)

        Returns:
            [
                {
                    'symbol': 'NVDA',
                    'name': 'NVIDIA Corporation',
                    'relationship': 'SUPPLIES',
                    'strength': 0.85
                },
                ...
            ]
        """
        query = """
        MATCH (s:Stock {symbol: $symbol})-[r:SUPPLIES|SUPPLIED_BY]-(related:Stock)
        RETURN related.symbol AS symbol,
               related.name AS name,
               type(r) AS relationship,
               COALESCE(r.strength, 0.5) AS strength
        ORDER BY strength DESC
        LIMIT $limit
        """

        try:
            result = session.run(
                query,
                symbol=symbol.upper(),
                limit=self.MAX_RESULTS,
                timeout=self.QUERY_TIMEOUT
            )

            return [
                {
                    'symbol': record['symbol'],
                    'name': record['name'],
                    'relationship': record['relationship'],
                    'strength': float(record['strength'])
                }
                for record in result
            ]

        except Exception as e:
            logger.error(f"Supply chain query error for {symbol}: {e}")
            return []

    def _get_competitors(self, session: Session, symbol: str) -> List[Dict[str, Any]]:
        """
        경쟁사 조회 (COMPETES_WITH)

        Returns:
            [
                {
                    'symbol': 'MSFT',
                    'name': 'Microsoft Corporation',
                    'overlap_score': 0.75
                },
                ...
            ]
        """
        query = """
        MATCH (s:Stock {symbol: $symbol})-[r:COMPETES_WITH]-(related:Stock)
        RETURN related.symbol AS symbol,
               related.name AS name,
               COALESCE(r.overlap_score, 0.5) AS overlap_score
        ORDER BY overlap_score DESC
        LIMIT $limit
        """

        try:
            result = session.run(
                query,
                symbol=symbol.upper(),
                limit=self.MAX_RESULTS,
                timeout=self.QUERY_TIMEOUT
            )

            return [
                {
                    'symbol': record['symbol'],
                    'name': record['name'],
                    'overlap_score': float(record['overlap_score'])
                }
                for record in result
            ]

        except Exception as e:
            logger.error(f"Competitors query error for {symbol}: {e}")
            return []

    def _get_sector_peers(self, session: Session, symbol: str) -> List[Dict[str, Any]]:
        """
        섹터 동료 조회 (같은 섹터에 속한 종목들)

        Returns:
            [
                {
                    'symbol': 'GOOGL',
                    'name': 'Alphabet Inc.',
                    'sector': 'Technology',
                    'market_cap': 1500000000000
                },
                ...
            ]
        """
        query = """
        MATCH (s:Stock {symbol: $symbol})-[:BELONGS_TO]->(sector:Sector)<-[:BELONGS_TO]-(peer:Stock)
        WHERE peer.symbol <> $symbol
        RETURN peer.symbol AS symbol,
               peer.name AS name,
               sector.name AS sector,
               COALESCE(peer.market_cap, 0) AS market_cap
        ORDER BY market_cap DESC
        LIMIT $limit
        """

        try:
            result = session.run(
                query,
                symbol=symbol.upper(),
                limit=self.MAX_RESULTS,
                timeout=self.QUERY_TIMEOUT
            )

            return [
                {
                    'symbol': record['symbol'],
                    'name': record['name'],
                    'sector': record['sector'],
                    'market_cap': int(record['market_cap']) if record['market_cap'] else None
                }
                for record in result
            ]

        except Exception as e:
            logger.error(f"Sector peers query error for {symbol}: {e}")
            return []

    def _empty_relationships(self, symbol: str, error: str) -> Dict[str, Any]:
        """
        Fallback: 빈 관계 데이터 반환

        Note:
            - Neo4j 연결 실패 또는 쿼리 에러 시 사용
            - 앱은 계속 작동하며, 단순히 그래프 기능이 비활성화됨
        """
        return {
            'symbol': symbol,
            'supply_chain': [],
            'competitors': [],
            'sector_peers': [],
            '_meta': {
                'source': 'fallback',
                '_error': error
            }
        }

    def health_check(self) -> Dict[str, Any]:
        """
        Neo4j 연결 상태 확인

        Returns:
            {
                'status': 'healthy' | 'degraded' | 'unavailable',
                'connected': bool,
                'error': None | str,
                'node_count': int | None,
                'relationship_count': int | None
            }
        """
        if self.driver is None:
            return {
                'status': 'unavailable',
                'connected': False,
                'error': 'Driver not initialized',
                'node_count': None,
                'relationship_count': None
            }

        try:
            with self.driver.session() as session:
                # 노드 개수 확인
                node_result = session.run(
                    "MATCH (n) RETURN count(n) AS count",
                    timeout=self.QUERY_TIMEOUT
                )
                node_count = node_result.single()['count']

                # 관계 개수 확인
                rel_result = session.run(
                    "MATCH ()-[r]->() RETURN count(r) AS count",
                    timeout=self.QUERY_TIMEOUT
                )
                rel_count = rel_result.single()['count']

                return {
                    'status': 'healthy',
                    'connected': True,
                    'error': None,
                    'node_count': node_count,
                    'relationship_count': rel_count
                }

        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return {
                'status': 'degraded',
                'connected': False,
                'error': str(e),
                'node_count': None,
                'relationship_count': None
            }

    def create_stock_node(
        self,
        symbol: str,
        name: str,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        market_cap: Optional[int] = None
    ) -> bool:
        """
        Stock 노드 생성 또는 업데이트

        Args:
            symbol: 종목 심볼
            name: 회사명
            sector: 섹터
            industry: 업종
            market_cap: 시가총액

        Returns:
            성공 여부
        """
        if self.driver is None:
            logger.warning(f"Neo4j unavailable - cannot create node for {symbol}")
            return False

        query = """
        MERGE (s:Stock {symbol: $symbol})
        SET s.name = $name,
            s.sector = $sector,
            s.industry = $industry,
            s.market_cap = $market_cap,
            s.updated_at = datetime()
        RETURN s.symbol AS symbol
        """

        try:
            with self.driver.session() as session:
                result = session.run(
                    query,
                    symbol=symbol.upper(),
                    name=name,
                    sector=sector,
                    industry=industry,
                    market_cap=market_cap,
                    timeout=self.QUERY_TIMEOUT
                )
                created = result.single() is not None
                if created:
                    logger.info(f"Created/updated Stock node: {symbol}")

                    # 섹터 관계 생성
                    if sector:
                        self._create_sector_relationship(session, symbol, sector)

                return created

        except Exception as e:
            logger.error(f"Failed to create Stock node for {symbol}: {e}")
            return False

    def _create_sector_relationship(
        self,
        session: Session,
        symbol: str,
        sector: str
    ):
        """
        Stock -> Sector 관계 생성
        """
        query = """
        MATCH (s:Stock {symbol: $symbol})
        MERGE (sector:Sector {name: $sector})
        MERGE (s)-[:BELONGS_TO]->(sector)
        """

        try:
            session.run(
                query,
                symbol=symbol.upper(),
                sector=sector,
                timeout=self.QUERY_TIMEOUT
            )
            logger.debug(f"Created sector relationship: {symbol} -> {sector}")
        except Exception as e:
            logger.error(f"Failed to create sector relationship for {symbol}: {e}")

    def delete_stock_node(self, symbol: str) -> bool:
        """
        Stock 노드 삭제 (모든 관계 포함)

        Args:
            symbol: 종목 심볼

        Returns:
            성공 여부
        """
        if self.driver is None:
            logger.warning(f"Neo4j unavailable - cannot delete node for {symbol}")
            return False

        query = """
        MATCH (s:Stock {symbol: $symbol})
        DETACH DELETE s
        """

        try:
            with self.driver.session() as session:
                session.run(
                    query,
                    symbol=symbol.upper(),
                    timeout=self.QUERY_TIMEOUT
                )
                logger.info(f"Deleted Stock node: {symbol}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete Stock node for {symbol}: {e}")
            return False


# Singleton instance
_neo4j_service: Optional[Neo4jServiceLite] = None


def get_neo4j_service() -> Neo4jServiceLite:
    """
    Neo4j Service singleton 반환
    """
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jServiceLite()
    return _neo4j_service
