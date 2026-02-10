"""
Neo4j Chain Sight Service

Neo4j 그래프 DB를 활용한 Chain Sight 온톨로지 서비스.
PostgreSQL StockRelationship과 동기화하며 그래프 탐색 기능 제공.

Node Types:
- Stock: symbol, name, sector, industry, market_cap
- Sector: name, display_name
- Industry: name, sector
- Theme: id, name, description (Phase 2)

Relationship Types:
- PEER_OF: Stock -> Stock (경쟁사)
- SAME_INDUSTRY: Stock -> Stock (동일 산업)
- CO_MENTIONED: Stock -> Stock (뉴스 동시언급)
- BELONGS_TO_SECTOR: Stock -> Sector
- BELONGS_TO_INDUSTRY: Stock -> Industry
- HAS_THEME: Stock -> Theme (Phase 2)

Usage:
    service = Neo4jChainSightService()

    # 노드 생성
    service.create_stock_node('NVDA', 'NVIDIA', 'Technology', 'Semiconductors', 1e12)

    # 관계 생성
    service.create_relationship('NVDA', 'AMD', 'PEER_OF', 0.85, 'fmp')

    # N-depth 그래프 조회
    graph = service.get_n_depth_graph('NVDA', depth=2)
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache

from rag_analysis.services.neo4j_driver import get_neo4j_driver


logger = logging.getLogger(__name__)


class Neo4jChainSightService:
    """
    Neo4j 기반 Chain Sight 온톨로지 서비스

    핵심 기능:
    1. Stock/Sector/Industry 노드 관리
    2. 관계 생성 및 조회 (PEER_OF, SAME_INDUSTRY, CO_MENTIONED)
    3. N-depth 그래프 탐색
    4. PostgreSQL 동기화
    """

    CACHE_TTL = 300  # 5분

    # 관계 타입 매핑
    RELATIONSHIP_TYPES = {
        'PEER_OF': 'PEER_OF',
        'SAME_INDUSTRY': 'SAME_INDUSTRY',
        'CO_MENTIONED': 'CO_MENTIONED',
        'HAS_THEME': 'HAS_THEME',
        'SUPPLIES_TO': 'SUPPLIES_TO',
        'CUSTOMER_OF': 'CUSTOMER_OF',
    }

    def __init__(self):
        self.driver = get_neo4j_driver()
        if self.driver is None:
            logger.warning("Neo4j driver not available, running in fallback mode")

    def is_available(self) -> bool:
        """Neo4j 연결 상태 확인"""
        return self.driver is not None

    # ========================================
    # Node Operations
    # ========================================

    def create_stock_node(
        self,
        symbol: str,
        name: str,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        market_cap: Optional[float] = None
    ) -> bool:
        """
        Stock 노드 생성/업데이트

        Args:
            symbol: 종목 심볼
            name: 회사명
            sector: 섹터
            industry: 산업
            market_cap: 시가총액

        Returns:
            성공 여부
        """
        if not self.is_available():
            return False

        try:
            with self.driver.session() as session:
                query = """
                MERGE (s:Stock {symbol: $symbol})
                SET s.name = $name,
                    s.sector = $sector,
                    s.industry = $industry,
                    s.market_cap = $market_cap,
                    s.updated_at = datetime()
                RETURN s.symbol AS symbol
                """
                result = session.run(
                    query,
                    symbol=symbol.upper(),
                    name=name,
                    sector=sector,
                    industry=industry,
                    market_cap=market_cap
                )
                record = result.single()
                return record is not None

        except Exception as e:
            logger.error(f"Stock 노드 생성 실패 {symbol}: {e}")
            return False

    def create_sector_node(self, name: str, display_name: Optional[str] = None) -> bool:
        """Sector 노드 생성"""
        if not self.is_available():
            return False

        try:
            with self.driver.session() as session:
                query = """
                MERGE (s:Sector {name: $name})
                SET s.display_name = $display_name,
                    s.updated_at = datetime()
                """
                session.run(query, name=name, display_name=display_name or name)
                return True

        except Exception as e:
            logger.error(f"Sector 노드 생성 실패 {name}: {e}")
            return False

    def create_industry_node(self, name: str, sector: str) -> bool:
        """Industry 노드 생성"""
        if not self.is_available():
            return False

        try:
            with self.driver.session() as session:
                query = """
                MERGE (i:Industry {name: $name})
                SET i.sector = $sector,
                    i.updated_at = datetime()
                """
                session.run(query, name=name, sector=sector)
                return True

        except Exception as e:
            logger.error(f"Industry 노드 생성 실패 {name}: {e}")
            return False

    # ========================================
    # Relationship Operations
    # ========================================

    def create_relationship(
        self,
        source_symbol: str,
        target_symbol: str,
        rel_type: str,
        weight: float = 1.0,
        source_provider: str = 'manual',
        context: Optional[Dict] = None
    ) -> bool:
        """
        두 종목 간 관계 생성

        Args:
            source_symbol: 원본 종목
            target_symbol: 대상 종목
            rel_type: 관계 타입 (PEER_OF, SAME_INDUSTRY, CO_MENTIONED)
            weight: 관계 강도 (0.0 ~ 1.0)
            source_provider: 데이터 소스 (fmp, finnhub, news, manual)
            context: 추가 컨텍스트 정보

        Returns:
            성공 여부
        """
        import json

        if not self.is_available():
            return False

        if rel_type not in self.RELATIONSHIP_TYPES:
            logger.warning(f"Unknown relationship type: {rel_type}")
            return False

        try:
            with self.driver.session() as session:
                # 동적 관계 타입 쿼리 생성
                cypher_rel_type = self.RELATIONSHIP_TYPES[rel_type]

                # context를 JSON 문자열로 직렬화 (Neo4j는 Map을 프로퍼티로 저장 불가)
                context_json = json.dumps(context) if context else '{}'

                query = f"""
                MATCH (source:Stock {{symbol: $source}})
                MATCH (target:Stock {{symbol: $target}})
                MERGE (source)-[r:{cypher_rel_type}]->(target)
                SET r.weight = $weight,
                    r.source = $source_provider,
                    r.context_json = $context_json,
                    r.updated_at = datetime()
                RETURN type(r) AS rel_type
                """

                result = session.run(
                    query,
                    source=source_symbol.upper(),
                    target=target_symbol.upper(),
                    weight=weight,
                    source_provider=source_provider,
                    context_json=context_json
                )
                record = result.single()
                return record is not None

        except Exception as e:
            logger.error(f"관계 생성 실패 {source_symbol}->{target_symbol}: {e}")
            return False

    def create_sector_relationship(self, symbol: str, sector: str) -> bool:
        """Stock -> Sector 관계 생성"""
        if not self.is_available():
            return False

        try:
            with self.driver.session() as session:
                query = """
                MATCH (s:Stock {symbol: $symbol})
                MERGE (sector:Sector {name: $sector})
                MERGE (s)-[r:BELONGS_TO_SECTOR]->(sector)
                SET r.updated_at = datetime()
                """
                session.run(query, symbol=symbol.upper(), sector=sector)
                return True

        except Exception as e:
            logger.error(f"Sector 관계 생성 실패 {symbol}->{sector}: {e}")
            return False

    def create_industry_relationship(self, symbol: str, industry: str) -> bool:
        """Stock -> Industry 관계 생성"""
        if not self.is_available():
            return False

        try:
            with self.driver.session() as session:
                query = """
                MATCH (s:Stock {symbol: $symbol})
                MERGE (i:Industry {name: $industry})
                MERGE (s)-[r:BELONGS_TO_INDUSTRY]->(i)
                SET r.updated_at = datetime()
                """
                session.run(query, symbol=symbol.upper(), industry=industry)
                return True

        except Exception as e:
            logger.error(f"Industry 관계 생성 실패 {symbol}->{industry}: {e}")
            return False

    # ========================================
    # Graph Query Operations
    # ========================================

    def get_related_stocks(
        self,
        symbol: str,
        rel_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        관련 종목 조회

        Args:
            symbol: 기준 종목
            rel_type: 관계 타입 (None이면 전체)
            limit: 최대 반환 개수

        Returns:
            관련 종목 리스트
        """
        import json

        if not self.is_available():
            return []

        try:
            with self.driver.session() as session:
                if rel_type and rel_type in self.RELATIONSHIP_TYPES:
                    cypher_rel_type = self.RELATIONSHIP_TYPES[rel_type]
                    query = f"""
                    MATCH (s:Stock {{symbol: $symbol}})-[r:{cypher_rel_type}]-(related:Stock)
                    RETURN related.symbol AS symbol,
                           related.name AS name,
                           related.sector AS sector,
                           related.industry AS industry,
                           related.market_cap AS market_cap,
                           r.weight AS weight,
                           type(r) AS relationship_type,
                           r.source AS source,
                           r.context_json AS context_json
                    ORDER BY r.weight DESC
                    LIMIT $limit
                    """
                else:
                    # 모든 관계 타입
                    query = """
                    MATCH (s:Stock {symbol: $symbol})-[r]-(related:Stock)
                    WHERE type(r) IN ['PEER_OF', 'SAME_INDUSTRY', 'CO_MENTIONED']
                    RETURN related.symbol AS symbol,
                           related.name AS name,
                           related.sector AS sector,
                           related.industry AS industry,
                           related.market_cap AS market_cap,
                           r.weight AS weight,
                           type(r) AS relationship_type,
                           r.source AS source,
                           r.context_json AS context_json
                    ORDER BY r.weight DESC
                    LIMIT $limit
                    """

                result = session.run(query, symbol=symbol.upper(), limit=limit)

                stocks = []
                for record in result:
                    # context_json 파싱
                    context_json = record.get('context_json', '{}')
                    try:
                        context = json.loads(context_json) if context_json else {}
                    except (json.JSONDecodeError, TypeError):
                        context = {}

                    stocks.append({
                        'symbol': record['symbol'],
                        'name': record['name'],
                        'sector': record['sector'],
                        'industry': record['industry'],
                        'market_cap': record['market_cap'],
                        'weight': record['weight'],
                        'relationship_type': record['relationship_type'],
                        'source': record['source'],
                        'context': context,
                    })

                return stocks

        except Exception as e:
            logger.error(f"관련 종목 조회 실패 {symbol}: {e}")
            return []

    def get_n_depth_graph(
        self,
        symbol: str,
        depth: int = 2,
        limit_per_node: int = 5
    ) -> Dict[str, Any]:
        """
        N-depth 그래프 조회 (시각화용)

        Args:
            symbol: 시작 종목
            depth: 탐색 깊이 (1-3 권장)
            limit_per_node: 노드당 최대 관계 수

        Returns:
            {
                "nodes": [
                    {"id": "NVDA", "name": "NVIDIA", "sector": "Technology", "group": "center"},
                    {"id": "AMD", "name": "AMD", "sector": "Technology", "group": "depth-1"},
                    ...
                ],
                "edges": [
                    {"source": "NVDA", "target": "AMD", "type": "PEER_OF", "weight": 0.85},
                    ...
                ]
            }
        """
        if not self.is_available():
            return {"nodes": [], "edges": []}

        # 캐시 확인
        cache_key = f'neo4j_graph:{symbol}:{depth}:{limit_per_node}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            with self.driver.session() as session:
                # 가변 길이 경로 쿼리 (최대 depth까지)
                query = f"""
                MATCH (center:Stock {{symbol: $symbol}})
                OPTIONAL MATCH path = (center)-[r*1..{depth}]-(related:Stock)
                WHERE ALL(rel IN relationships(path) WHERE type(rel) IN ['PEER_OF', 'SAME_INDUSTRY', 'CO_MENTIONED'])
                WITH center, path, related, relationships(path) AS rels
                UNWIND CASE WHEN path IS NULL THEN [null] ELSE rels END AS rel
                WITH center, related, rel,
                     CASE WHEN startNode(rel) IS NOT NULL
                          THEN startNode(rel).symbol
                          ELSE null END AS source_symbol,
                     CASE WHEN endNode(rel) IS NOT NULL
                          THEN endNode(rel).symbol
                          ELSE null END AS target_symbol
                RETURN DISTINCT
                    center.symbol AS center_symbol,
                    center.name AS center_name,
                    center.sector AS center_sector,
                    related.symbol AS related_symbol,
                    related.name AS related_name,
                    related.sector AS related_sector,
                    source_symbol,
                    target_symbol,
                    CASE WHEN rel IS NOT NULL THEN type(rel) ELSE null END AS rel_type,
                    CASE WHEN rel IS NOT NULL THEN rel.weight ELSE null END AS weight
                LIMIT 100
                """

                result = session.run(query, symbol=symbol.upper())

                nodes = {}
                edges = []

                for record in result:
                    # 중심 노드
                    center_sym = record['center_symbol']
                    if center_sym and center_sym not in nodes:
                        nodes[center_sym] = {
                            'id': center_sym,
                            'name': record['center_name'] or center_sym,
                            'sector': record['center_sector'],
                            'group': 'center'
                        }

                    # 관련 노드
                    related_sym = record['related_symbol']
                    if related_sym and related_sym not in nodes:
                        nodes[related_sym] = {
                            'id': related_sym,
                            'name': record['related_name'] or related_sym,
                            'sector': record['related_sector'],
                            'group': 'related'
                        }

                    # 엣지
                    source_sym = record['source_symbol']
                    target_sym = record['target_symbol']
                    rel_type = record['rel_type']

                    if source_sym and target_sym and rel_type:
                        edge_key = f"{source_sym}-{target_sym}-{rel_type}"
                        # 중복 방지
                        if not any(
                            e['source'] == source_sym and
                            e['target'] == target_sym and
                            e['type'] == rel_type
                            for e in edges
                        ):
                            edges.append({
                                'source': source_sym,
                                'target': target_sym,
                                'type': rel_type,
                                'weight': record['weight'] or 0.5
                            })

                graph_data = {
                    'nodes': list(nodes.values()),
                    'edges': edges
                }

                # 캐시 저장
                cache.set(cache_key, graph_data, self.CACHE_TTL)

                return graph_data

        except Exception as e:
            logger.error(f"N-depth 그래프 조회 실패 {symbol}: {e}")
            return {"nodes": [], "edges": []}

    # ========================================
    # PostgreSQL Sync Operations
    # ========================================

    def sync_from_postgres(self, symbol: str) -> Dict[str, int]:
        """
        PostgreSQL StockRelationship에서 Neo4j로 동기화

        Args:
            symbol: 동기화할 종목 심볼

        Returns:
            동기화된 관계 수
        """
        from serverless.models import StockRelationship
        from serverless.services.fmp_client import FMPClient

        if not self.is_available():
            return {'synced': 0, 'failed': 0}

        symbol = symbol.upper()
        synced = 0
        failed = 0

        try:
            # 1. 소스 종목 프로필 조회 및 노드 생성
            fmp_client = FMPClient()
            try:
                profile = fmp_client.get_company_profile(symbol)
                self.create_stock_node(
                    symbol=symbol,
                    name=profile.get('companyName', symbol),
                    sector=profile.get('sector'),
                    industry=profile.get('industry'),
                    market_cap=profile.get('marketCap')  # mktCap → marketCap
                )

                # Sector/Industry 관계
                if profile.get('sector'):
                    self.create_sector_relationship(symbol, profile['sector'])
                if profile.get('industry'):
                    self.create_industry_relationship(symbol, profile['industry'])
            except Exception as e:
                logger.warning(f"프로필 조회 실패 {symbol}: {e}")

            # 2. PostgreSQL 관계 조회
            relationships = StockRelationship.objects.filter(source_symbol=symbol)

            for rel in relationships:
                # 타겟 종목 노드 생성 (존재하지 않으면)
                try:
                    target_profile = fmp_client.get_company_profile(rel.target_symbol)
                    self.create_stock_node(
                        symbol=rel.target_symbol,
                        name=target_profile.get('companyName', rel.target_symbol),
                        sector=target_profile.get('sector'),
                        industry=target_profile.get('industry'),
                        market_cap=target_profile.get('marketCap')  # mktCap → marketCap
                    )
                except Exception:
                    # 프로필 없으면 심볼만으로 생성
                    self.create_stock_node(
                        symbol=rel.target_symbol,
                        name=rel.target_symbol
                    )

                # 관계 생성
                success = self.create_relationship(
                    source_symbol=symbol,
                    target_symbol=rel.target_symbol,
                    rel_type=rel.relationship_type,
                    weight=float(rel.strength),
                    source_provider=rel.source_provider,
                    context=rel.context
                )

                if success:
                    synced += 1
                else:
                    failed += 1

            logger.info(f"Neo4j 동기화 완료: {symbol} -> synced={synced}, failed={failed}")

            return {'synced': synced, 'failed': failed}

        except Exception as e:
            logger.error(f"PostgreSQL 동기화 실패 {symbol}: {e}")
            return {'synced': synced, 'failed': failed}

    def sync_all_from_postgres(self, batch_size: int = 100) -> Dict[str, int]:
        """
        모든 PostgreSQL 관계를 Neo4j로 동기화

        Args:
            batch_size: 배치 크기

        Returns:
            동기화 결과
        """
        from serverless.models import StockRelationship

        if not self.is_available():
            return {'total_symbols': 0, 'synced': 0, 'failed': 0}

        # 유니크 심볼 목록
        symbols = StockRelationship.objects.values_list(
            'source_symbol', flat=True
        ).distinct()

        total_synced = 0
        total_failed = 0

        for symbol in symbols:
            result = self.sync_from_postgres(symbol)
            total_synced += result['synced']
            total_failed += result['failed']

        return {
            'total_symbols': len(symbols),
            'synced': total_synced,
            'failed': total_failed
        }

    # ========================================
    # Index & Maintenance Operations
    # ========================================

    def create_indexes(self) -> bool:
        """인덱스 생성"""
        if not self.is_available():
            return False

        try:
            with self.driver.session() as session:
                # Stock.symbol 인덱스
                session.run(
                    "CREATE INDEX chain_sight_stock_symbol IF NOT EXISTS "
                    "FOR (s:Stock) ON (s.symbol)"
                )

                # Sector.name 인덱스
                session.run(
                    "CREATE INDEX chain_sight_sector_name IF NOT EXISTS "
                    "FOR (s:Sector) ON (s.name)"
                )

                # Industry.name 인덱스
                session.run(
                    "CREATE INDEX chain_sight_industry_name IF NOT EXISTS "
                    "FOR (i:Industry) ON (i.name)"
                )

                logger.info("Neo4j Chain Sight 인덱스 생성 완료")
                return True

        except Exception as e:
            logger.error(f"인덱스 생성 실패: {e}")
            return False

    def get_statistics(self) -> Dict[str, int]:
        """그래프 통계 조회"""
        if not self.is_available():
            return {}

        try:
            with self.driver.session() as session:
                stock_count = session.run(
                    "MATCH (s:Stock) RETURN count(s) AS count"
                ).single()['count']

                sector_count = session.run(
                    "MATCH (s:Sector) RETURN count(s) AS count"
                ).single()['count']

                peer_count = session.run(
                    "MATCH ()-[r:PEER_OF]->() RETURN count(r) AS count"
                ).single()['count']

                industry_rel_count = session.run(
                    "MATCH ()-[r:SAME_INDUSTRY]->() RETURN count(r) AS count"
                ).single()['count']

                co_mentioned_count = session.run(
                    "MATCH ()-[r:CO_MENTIONED]->() RETURN count(r) AS count"
                ).single()['count']

                return {
                    'stock_nodes': stock_count,
                    'sector_nodes': sector_count,
                    'peer_of_relationships': peer_count,
                    'same_industry_relationships': industry_rel_count,
                    'co_mentioned_relationships': co_mentioned_count,
                }

        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {}

    def clear_all(self) -> bool:
        """모든 Chain Sight 데이터 삭제"""
        if not self.is_available():
            return False

        try:
            with self.driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
                logger.warning("Neo4j Chain Sight 데이터 전체 삭제됨")
                return True

        except Exception as e:
            logger.error(f"데이터 삭제 실패: {e}")
            return False
