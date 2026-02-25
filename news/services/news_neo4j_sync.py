"""
뉴스 이벤트 Neo4j 동기화 서비스 (News Intelligence Pipeline v3 - Phase 3)

LLM 심층 분석 결과를 Neo4j에 동기화하여 뉴스 이벤트 그래프를 구축합니다.
- NewsEvent 노드 생성
- DIRECTLY_IMPACTS / INDIRECTLY_IMPACTS / CREATES_OPPORTUNITY 관계 생성
- AFFECTS_SECTOR 관계 생성 (sector_ripple)
- 관계 강화 (같은 방향 뉴스 3건+ → confidence 상향)
- TTL 기반 만료 관계 정리
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from django.core.cache import cache
from django.utils import timezone

from rag_analysis.services.neo4j_driver import get_neo4j_driver

logger = logging.getLogger(__name__)


class NewsNeo4jSyncService:
    """
    뉴스 이벤트 → Neo4j 동기화 서비스

    노드 타입:
    - NewsEvent: article_id, title, source, importance_score, tier, published_at
    - Stock: symbol (기존 노드 참조)
    - Sector: name (기존 노드 참조)

    관계 타입:
    - DIRECTLY_IMPACTS: NewsEvent → Stock (confidence, direction, reason)
    - INDIRECTLY_IMPACTS: NewsEvent → Stock (confidence, direction, chain_logic)
    - CREATES_OPPORTUNITY: NewsEvent → Stock (confidence, thesis, timeframe)
    - AFFECTS_SECTOR: NewsEvent → Sector (direction, reason)

    TTL:
    - DIRECTLY_IMPACTS: 30일
    - INDIRECTLY_IMPACTS: 21일
    - CREATES_OPPORTUNITY: 14일
    - AFFECTS_SECTOR: 21일
    """

    RELATIONSHIP_TTL = {
        'DIRECTLY_IMPACTS': 30,
        'INDIRECTLY_IMPACTS': 21,
        'CREATES_OPPORTUNITY': 14,
        'AFFECTS_SECTOR': 21,
    }

    # 관계 강화: 같은 방향 뉴스 N건 이상이면 confidence 상향
    REINFORCEMENT_THRESHOLD = 3
    REINFORCEMENT_BOOST = 0.1  # +10%

    # Sector Ripple 가드레일
    MAX_SECTOR_RIPPLE_HOPS = 2
    MAX_RELATIONSHIPS_PER_NODE = 20

    CACHE_TTL = 300  # 5분

    def __init__(self):
        self.driver = get_neo4j_driver()
        if self.driver is None:
            logger.warning("Neo4j driver not available, NewsNeo4jSync in fallback mode")

    def is_available(self) -> bool:
        """Neo4j 연결 상태 확인"""
        return self.driver is not None

    # ========================================
    # Node Operations
    # ========================================

    def create_news_event_node(
        self,
        article_id: str,
        title: str,
        source: str,
        importance_score: float,
        tier: str,
        published_at: datetime,
    ) -> bool:
        """
        NewsEvent 노드 생성/업데이트

        Returns:
            성공 여부
        """
        if not self.is_available():
            return False

        try:
            with self.driver.session() as session:
                query = """
                MERGE (ne:NewsEvent {article_id: $article_id})
                SET ne.title = $title,
                    ne.source = $source,
                    ne.importance_score = $importance_score,
                    ne.tier = $tier,
                    ne.published_at = $published_at,
                    ne.updated_at = datetime()
                RETURN ne.article_id AS article_id
                """
                result = session.run(
                    query,
                    article_id=str(article_id),
                    title=title[:200],
                    source=source,
                    importance_score=importance_score,
                    tier=tier,
                    published_at=published_at.isoformat(),
                )
                record = result.single()
                return record is not None

        except Exception as e:
            logger.error(f"NewsEvent 노드 생성 실패 {article_id}: {e}")
            return False

    # ========================================
    # Relationship Operations
    # ========================================

    def create_direct_impact(
        self,
        article_id: str,
        symbol: str,
        direction: str,
        confidence: float,
        reason: str,
    ) -> bool:
        """NewsEvent → Stock DIRECTLY_IMPACTS 관계 생성"""
        if not self.is_available():
            return False

        try:
            with self.driver.session() as session:
                query = """
                MATCH (ne:NewsEvent {article_id: $article_id})
                MERGE (s:Stock {symbol: $symbol})
                MERGE (ne)-[r:DIRECTLY_IMPACTS]->(s)
                SET r.direction = $direction,
                    r.confidence = $confidence,
                    r.reason = $reason,
                    r.created_at = CASE WHEN r.created_at IS NULL
                                       THEN datetime() ELSE r.created_at END,
                    r.updated_at = datetime(),
                    r.expires_at = datetime() + duration({days: $ttl_days})
                RETURN type(r) AS rel_type
                """
                result = session.run(
                    query,
                    article_id=str(article_id),
                    symbol=symbol.upper(),
                    direction=direction,
                    confidence=min(confidence, 1.0),
                    reason=reason[:500],
                    ttl_days=self.RELATIONSHIP_TTL['DIRECTLY_IMPACTS'],
                )
                return result.single() is not None

        except Exception as e:
            logger.error(f"DIRECTLY_IMPACTS 생성 실패 {article_id}->{symbol}: {e}")
            return False

    def create_indirect_impact(
        self,
        article_id: str,
        symbol: str,
        direction: str,
        confidence: float,
        reason: str,
        chain_logic: str,
    ) -> bool:
        """NewsEvent → Stock INDIRECTLY_IMPACTS 관계 생성"""
        if not self.is_available():
            return False

        try:
            with self.driver.session() as session:
                query = """
                MATCH (ne:NewsEvent {article_id: $article_id})
                MERGE (s:Stock {symbol: $symbol})
                MERGE (ne)-[r:INDIRECTLY_IMPACTS]->(s)
                SET r.direction = $direction,
                    r.confidence = $confidence,
                    r.reason = $reason,
                    r.chain_logic = $chain_logic,
                    r.created_at = CASE WHEN r.created_at IS NULL
                                       THEN datetime() ELSE r.created_at END,
                    r.updated_at = datetime(),
                    r.expires_at = datetime() + duration({days: $ttl_days})
                RETURN type(r) AS rel_type
                """
                result = session.run(
                    query,
                    article_id=str(article_id),
                    symbol=symbol.upper(),
                    direction=direction,
                    confidence=min(confidence, 1.0),
                    reason=reason[:500],
                    chain_logic=chain_logic[:1000],
                    ttl_days=self.RELATIONSHIP_TTL['INDIRECTLY_IMPACTS'],
                )
                return result.single() is not None

        except Exception as e:
            logger.error(f"INDIRECTLY_IMPACTS 생성 실패 {article_id}->{symbol}: {e}")
            return False

    def create_opportunity(
        self,
        article_id: str,
        symbol: str,
        thesis: str,
        timeframe: str,
        confidence: float,
    ) -> bool:
        """NewsEvent → Stock CREATES_OPPORTUNITY 관계 생성"""
        if not self.is_available():
            return False

        try:
            with self.driver.session() as session:
                query = """
                MATCH (ne:NewsEvent {article_id: $article_id})
                MERGE (s:Stock {symbol: $symbol})
                MERGE (ne)-[r:CREATES_OPPORTUNITY]->(s)
                SET r.thesis = $thesis,
                    r.timeframe = $timeframe,
                    r.confidence = $confidence,
                    r.created_at = CASE WHEN r.created_at IS NULL
                                       THEN datetime() ELSE r.created_at END,
                    r.updated_at = datetime(),
                    r.expires_at = datetime() + duration({days: $ttl_days})
                RETURN type(r) AS rel_type
                """
                result = session.run(
                    query,
                    article_id=str(article_id),
                    symbol=symbol.upper(),
                    thesis=thesis[:500],
                    timeframe=timeframe[:50],
                    confidence=min(confidence, 1.0),
                    ttl_days=self.RELATIONSHIP_TTL['CREATES_OPPORTUNITY'],
                )
                return result.single() is not None

        except Exception as e:
            logger.error(f"CREATES_OPPORTUNITY 생성 실패 {article_id}->{symbol}: {e}")
            return False

    def create_sector_ripple(
        self,
        article_id: str,
        sector: str,
        direction: str,
        reason: str,
    ) -> bool:
        """NewsEvent → Sector AFFECTS_SECTOR 관계 생성"""
        if not self.is_available():
            return False

        try:
            with self.driver.session() as session:
                query = """
                MATCH (ne:NewsEvent {article_id: $article_id})
                MERGE (sec:Sector {name: $sector})
                MERGE (ne)-[r:AFFECTS_SECTOR]->(sec)
                SET r.direction = $direction,
                    r.reason = $reason,
                    r.created_at = CASE WHEN r.created_at IS NULL
                                       THEN datetime() ELSE r.created_at END,
                    r.updated_at = datetime(),
                    r.expires_at = datetime() + duration({days: $ttl_days})
                RETURN type(r) AS rel_type
                """
                result = session.run(
                    query,
                    article_id=str(article_id),
                    sector=sector,
                    direction=direction,
                    reason=reason[:500],
                    ttl_days=self.RELATIONSHIP_TTL['AFFECTS_SECTOR'],
                )
                return result.single() is not None

        except Exception as e:
            logger.error(f"AFFECTS_SECTOR 생성 실패 {article_id}->{sector}: {e}")
            return False

    def propagate_sector_ripple(
        self,
        article_id: str,
        sector: str,
        direction: str,
        confidence: float,
    ) -> dict:
        """
        Sector Ripple 2-hop 확산 로직

        해당 섹터에 속한 Stock 노드에 INDIRECTLY_IMPACTS 관계를 생성합니다.
        이미 DIRECTLY_IMPACTS로 연결된 종목은 제외하며, 최대 MAX_RELATIONSHIPS_PER_NODE개까지 생성합니다.
        confidence는 원본의 0.4배로 감쇠하여 간접 영향임을 표현합니다.

        Stock 노드 조회 방식:
        1. Sector 노드와 BELONGS_TO 관계로 연결된 Stock 조회 (우선)
        2. BELONGS_TO 관계가 없으면 Stock 노드의 sector 속성으로 조회 (폴백)

        Args:
            article_id: 뉴스 이벤트 ID
            sector: 섹터 이름
            direction: 영향 방향 (bullish/bearish/neutral)
            confidence: 원본 confidence (0.4배 감쇠 후 사용)

        Returns:
            dict: {'propagated': int, 'sector': str}
        """
        if not self.is_available():
            return {'propagated': 0, 'sector': sector}

        propagated_confidence = round(confidence * 0.4, 4)
        chain_logic = f"Sector ripple: {sector} 섹터 영향 확산"
        reason = f"{sector} 섹터 뉴스 이벤트의 간접 영향"

        try:
            with self.driver.session() as session:
                # 1차 시도: BELONGS_TO 관계 기반 조회
                query_belongs_to = """
                MATCH (sec:Sector {name: $sector})<-[:BELONGS_TO]-(s:Stock)
                WHERE NOT EXISTS {
                    MATCH (ne:NewsEvent {article_id: $article_id})-[:DIRECTLY_IMPACTS]->(s)
                }
                WITH s
                LIMIT $max_limit
                MATCH (ne:NewsEvent {article_id: $article_id})
                MERGE (ne)-[r:INDIRECTLY_IMPACTS]->(s)
                SET r.direction = $direction,
                    r.confidence = $confidence,
                    r.reason = $reason,
                    r.chain_logic = $chain_logic,
                    r.source = 'sector_ripple',
                    r.created_at = CASE WHEN r.created_at IS NULL THEN datetime() ELSE r.created_at END,
                    r.updated_at = datetime(),
                    r.expires_at = datetime() + duration({days: $ttl_days})
                RETURN count(r) AS propagated
                """
                result = session.run(
                    query_belongs_to,
                    article_id=str(article_id),
                    sector=sector,
                    direction=direction,
                    confidence=propagated_confidence,
                    reason=reason,
                    chain_logic=chain_logic,
                    max_limit=self.MAX_RELATIONSHIPS_PER_NODE,
                    ttl_days=self.RELATIONSHIP_TTL['INDIRECTLY_IMPACTS'],
                )
                record = result.single()
                propagated = record['propagated'] if record else 0

                # BELONGS_TO 관계로 찾지 못한 경우 Stock.sector 속성으로 폴백
                if propagated == 0:
                    query_sector_prop = """
                    MATCH (s:Stock)
                    WHERE s.sector = $sector
                      AND NOT EXISTS {
                          MATCH (ne:NewsEvent {article_id: $article_id})-[:DIRECTLY_IMPACTS]->(s)
                      }
                    WITH s
                    LIMIT $max_limit
                    MATCH (ne:NewsEvent {article_id: $article_id})
                    MERGE (ne)-[r:INDIRECTLY_IMPACTS]->(s)
                    SET r.direction = $direction,
                        r.confidence = $confidence,
                        r.reason = $reason,
                        r.chain_logic = $chain_logic,
                        r.source = 'sector_ripple',
                        r.created_at = CASE WHEN r.created_at IS NULL THEN datetime() ELSE r.created_at END,
                        r.updated_at = datetime(),
                        r.expires_at = datetime() + duration({days: $ttl_days})
                    RETURN count(r) AS propagated
                    """
                    result = session.run(
                        query_sector_prop,
                        article_id=str(article_id),
                        sector=sector,
                        direction=direction,
                        confidence=propagated_confidence,
                        reason=reason,
                        chain_logic=chain_logic,
                        max_limit=self.MAX_RELATIONSHIPS_PER_NODE,
                        ttl_days=self.RELATIONSHIP_TTL['INDIRECTLY_IMPACTS'],
                    )
                    record = result.single()
                    propagated = record['propagated'] if record else 0

                if propagated > 0:
                    logger.info(
                        f"Sector ripple 확산: {sector} 섹터 → {propagated}개 종목 "
                        f"(article_id={article_id}, confidence={propagated_confidence})"
                    )

                return {'propagated': propagated, 'sector': sector}

        except Exception as e:
            logger.error(f"Sector ripple 확산 실패 {article_id}->{sector}: {e}")
            return {'propagated': 0, 'sector': sector}

    # ========================================
    # Sync Operations
    # ========================================

    def sync_article(self, article) -> dict:
        """
        단일 뉴스 기사의 LLM 분석 결과를 Neo4j에 동기화

        Args:
            article: NewsArticle 인스턴스 (llm_analyzed=True, llm_analysis != None)

        Returns:
            dict: {nodes_created: int, relationships_created: int, errors: int}
        """
        if not self.is_available():
            return {'nodes_created': 0, 'relationships_created': 0, 'errors': 0}

        analysis = article.llm_analysis
        if not analysis:
            return {'nodes_created': 0, 'relationships_created': 0, 'errors': 0}

        nodes = 0
        rels = 0
        errors = 0

        # 1. NewsEvent 노드 생성
        tier = analysis.get('tier', 'A')
        success = self.create_news_event_node(
            article_id=str(article.id),
            title=article.title,
            source=article.source,
            importance_score=article.importance_score or 0.0,
            tier=tier,
            published_at=article.published_at,
        )
        if success:
            nodes += 1
        else:
            errors += 1
            return {'nodes_created': nodes, 'relationships_created': rels, 'errors': errors}

        # 2. Direct impacts
        for impact in analysis.get('direct_impacts', []):
            symbol = impact.get('symbol', '')
            if not symbol:
                continue
            ok = self.create_direct_impact(
                article_id=str(article.id),
                symbol=symbol,
                direction=impact.get('direction', 'neutral'),
                confidence=impact.get('confidence', 0.5),
                reason=impact.get('reason', ''),
            )
            if ok:
                rels += 1
            else:
                errors += 1

        # 3. Indirect impacts
        for impact in analysis.get('indirect_impacts', []):
            symbol = impact.get('symbol', '')
            if not symbol:
                continue
            ok = self.create_indirect_impact(
                article_id=str(article.id),
                symbol=symbol,
                direction=impact.get('direction', 'neutral'),
                confidence=impact.get('confidence', 0.3),
                reason=impact.get('reason', ''),
                chain_logic=impact.get('chain_logic', ''),
            )
            if ok:
                rels += 1
            else:
                errors += 1

        # 4. Opportunities
        for opp in analysis.get('opportunities', []):
            symbol = opp.get('symbol', '')
            if not symbol:
                continue
            ok = self.create_opportunity(
                article_id=str(article.id),
                symbol=symbol,
                thesis=opp.get('thesis', ''),
                timeframe=opp.get('timeframe', ''),
                confidence=opp.get('confidence', 0.3),
            )
            if ok:
                rels += 1
            else:
                errors += 1

        # 5. Sector ripple
        for ripple in analysis.get('sector_ripple', []):
            sector = ripple.get('sector', '')
            if not sector:
                continue
            ok = self.create_sector_ripple(
                article_id=str(article.id),
                sector=sector,
                direction=ripple.get('direction', 'neutral'),
                reason=ripple.get('reason', ''),
            )
            if ok:
                rels += 1

                # 2-hop 확산: 해당 섹터의 Stock 노드에 INDIRECTLY_IMPACTS 관계 생성
                propagate_result = self.propagate_sector_ripple(
                    article_id=str(article.id),
                    sector=sector,
                    direction=ripple.get('direction', 'neutral'),
                    confidence=ripple.get('confidence', 0.5),
                )
                rels += propagate_result['propagated']
            else:
                errors += 1

        return {
            'nodes_created': nodes,
            'relationships_created': rels,
            'errors': errors,
        }

    def sync_batch(self, max_articles: int = 100) -> dict:
        """
        미동기화 뉴스 기사를 배치로 Neo4j에 동기화

        llm_analyzed=True이면서 아직 Neo4j에 동기화하지 않은 기사를 처리합니다.
        neo4j_synced 필드가 없으므로, Neo4j에 이미 존재하는 article_id를 제외합니다.

        Returns:
            dict: {synced: int, skipped: int, errors: int, total_nodes: int, total_rels: int}
        """
        from ..models import NewsArticle

        if not self.is_available():
            return {
                'synced': 0, 'skipped': 0, 'errors': 0,
                'total_nodes': 0, 'total_rels': 0,
            }

        # LLM 분석 완료된 기사 (최근 30일) 조회
        cutoff = timezone.now() - timedelta(days=30)
        articles = NewsArticle.objects.filter(
            llm_analyzed=True,
            llm_analysis__isnull=False,
            published_at__gte=cutoff,
        ).order_by('-importance_score')[:max_articles]

        # 이미 Neo4j에 존재하는 article_id 확인
        existing_ids = self._get_existing_event_ids()

        synced = 0
        skipped = 0
        errors = 0
        total_nodes = 0
        total_rels = 0

        for article in articles:
            article_id_str = str(article.id)

            # 이미 동기화된 기사 스킵
            if article_id_str in existing_ids:
                skipped += 1
                continue

            try:
                result = self.sync_article(article)
                if result['errors'] == 0:
                    synced += 1
                else:
                    errors += result['errors']
                total_nodes += result['nodes_created']
                total_rels += result['relationships_created']
            except Exception as e:
                logger.error(f"sync_batch: article {article.id} failed: {e}")
                errors += 1

        return {
            'synced': synced,
            'skipped': skipped,
            'errors': errors,
            'total_nodes': total_nodes,
            'total_rels': total_rels,
        }

    def _get_existing_event_ids(self) -> set:
        """Neo4j에 이미 존재하는 NewsEvent article_id 집합 반환"""
        if not self.is_available():
            return set()

        try:
            with self.driver.session() as session:
                result = session.run(
                    "MATCH (ne:NewsEvent) RETURN ne.article_id AS aid"
                )
                return {record['aid'] for record in result}
        except Exception as e:
            logger.error(f"기존 NewsEvent ID 조회 실패: {e}")
            return set()

    # ========================================
    # Reinforcement (관계 강화)
    # ========================================

    def reinforce_relationships(self, symbol: str, days: int = 7) -> dict:
        """
        같은 종목에 대한 같은 방향 뉴스가 N건 이상이면 confidence 상향

        Args:
            symbol: 종목 심볼
            days: 조회 범위 일수

        Returns:
            dict: {reinforced: int}
        """
        if not self.is_available():
            return {'reinforced': 0}

        try:
            with self.driver.session() as session:
                # 같은 종목에 대한 같은 방향 직접 영향 관계 수 집계
                query = """
                MATCH (ne:NewsEvent)-[r:DIRECTLY_IMPACTS]->(s:Stock {symbol: $symbol})
                WHERE ne.published_at > datetime() - duration({days: $days})
                WITH s, r.direction AS direction, collect(r) AS rels, count(r) AS cnt
                WHERE cnt >= $threshold
                UNWIND rels AS r
                SET r.confidence = CASE
                    WHEN r.confidence + $boost > 1.0 THEN 1.0
                    ELSE r.confidence + $boost
                END,
                    r.reinforced = true,
                    r.reinforced_at = datetime()
                RETURN count(r) AS reinforced_count
                """
                result = session.run(
                    query,
                    symbol=symbol.upper(),
                    days=days,
                    threshold=self.REINFORCEMENT_THRESHOLD,
                    boost=self.REINFORCEMENT_BOOST,
                )
                record = result.single()
                count = record['reinforced_count'] if record else 0
                return {'reinforced': count}

        except Exception as e:
            logger.error(f"관계 강화 실패 {symbol}: {e}")
            return {'reinforced': 0}

    # ========================================
    # Cleanup Operations
    # ========================================

    def cleanup_expired_relationships(self) -> dict:
        """
        TTL 만료된 뉴스 이벤트 관계 정리

        Returns:
            dict: {deleted_relationships: int, deleted_nodes: int}
        """
        if not self.is_available():
            return {'deleted_relationships': 0, 'deleted_nodes': 0}

        deleted_rels = 0
        deleted_nodes = 0

        try:
            with self.driver.session() as session:
                # 만료된 관계 삭제
                for rel_type in self.RELATIONSHIP_TTL:
                    query = f"""
                    MATCH ()-[r:{rel_type}]->()
                    WHERE r.expires_at IS NOT NULL AND r.expires_at < datetime()
                    DELETE r
                    RETURN count(r) AS deleted
                    """
                    result = session.run(query)
                    record = result.single()
                    count = record['deleted'] if record else 0
                    deleted_rels += count
                    if count > 0:
                        logger.info(f"Cleaned up {count} expired {rel_type} relationships")

                # 관계가 하나도 없는 고립 NewsEvent 노드 삭제
                orphan_query = """
                MATCH (ne:NewsEvent)
                WHERE NOT (ne)-[]-()
                DELETE ne
                RETURN count(ne) AS deleted
                """
                result = session.run(orphan_query)
                record = result.single()
                deleted_nodes = record['deleted'] if record else 0

                if deleted_nodes > 0:
                    logger.info(f"Cleaned up {deleted_nodes} orphaned NewsEvent nodes")

        except Exception as e:
            logger.error(f"만료 관계 정리 실패: {e}")

        return {
            'deleted_relationships': deleted_rels,
            'deleted_nodes': deleted_nodes,
        }

    # ========================================
    # Query Operations
    # ========================================

    def get_news_events_for_symbol(
        self, symbol: str, days: int = 7, limit: int = 20,
    ) -> list:
        """
        특정 종목 관련 뉴스 이벤트 조회

        Args:
            symbol: 종목 심볼
            days: 조회 기간
            limit: 최대 반환 개수

        Returns:
            list: 뉴스 이벤트 리스트
        """
        if not self.is_available():
            return []

        cache_key = f'news_events:{symbol}:{days}:{limit}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            with self.driver.session() as session:
                query = """
                MATCH (ne:NewsEvent)-[r]->(s:Stock {symbol: $symbol})
                WHERE ne.published_at > datetime() - duration({days: $days})
                  AND type(r) IN ['DIRECTLY_IMPACTS', 'INDIRECTLY_IMPACTS', 'CREATES_OPPORTUNITY']
                RETURN ne.article_id AS article_id,
                       ne.title AS title,
                       ne.source AS source,
                       ne.importance_score AS importance_score,
                       ne.tier AS tier,
                       ne.published_at AS published_at,
                       type(r) AS relationship_type,
                       r.direction AS direction,
                       r.confidence AS confidence,
                       r.reason AS reason,
                       r.chain_logic AS chain_logic,
                       r.thesis AS thesis,
                       r.timeframe AS timeframe,
                       r.reinforced AS reinforced
                ORDER BY ne.published_at DESC
                LIMIT $limit
                """
                result = session.run(
                    query,
                    symbol=symbol.upper(),
                    days=days,
                    limit=limit,
                )

                events = []
                for record in result:
                    event = {
                        'article_id': record['article_id'],
                        'title': record['title'],
                        'source': record['source'],
                        'importance_score': record['importance_score'],
                        'tier': record['tier'],
                        'published_at': str(record['published_at']),
                        'relationship_type': record['relationship_type'],
                        'direction': record['direction'],
                        'confidence': record['confidence'],
                        'reinforced': record.get('reinforced', False),
                    }
                    # 관계 타입별 추가 필드
                    if record['relationship_type'] == 'INDIRECTLY_IMPACTS':
                        event['chain_logic'] = record.get('chain_logic', '')
                    elif record['relationship_type'] == 'CREATES_OPPORTUNITY':
                        event['thesis'] = record.get('thesis', '')
                        event['timeframe'] = record.get('timeframe', '')

                    if record.get('reason'):
                        event['reason'] = record['reason']

                    events.append(event)

                cache.set(cache_key, events, self.CACHE_TTL)
                return events

        except Exception as e:
            logger.error(f"뉴스 이벤트 조회 실패 {symbol}: {e}")
            return []

    def get_impact_map(self, days: int = 7, limit: int = 50) -> dict:
        """
        전체 뉴스 영향도 맵 (시각화용)

        Returns:
            dict: {nodes: [...], edges: [...], stats: {...}}
        """
        if not self.is_available():
            return {'nodes': [], 'edges': [], 'stats': {}}

        cache_key = f'news_impact_map:{days}:{limit}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            with self.driver.session() as session:
                query = """
                MATCH (ne:NewsEvent)-[r]->(target)
                WHERE ne.published_at > datetime() - duration({days: $days})
                  AND type(r) IN [
                      'DIRECTLY_IMPACTS', 'INDIRECTLY_IMPACTS',
                      'CREATES_OPPORTUNITY', 'AFFECTS_SECTOR'
                  ]
                WITH ne, r, target
                ORDER BY ne.importance_score DESC
                LIMIT $limit
                RETURN ne.article_id AS event_id,
                       ne.title AS event_title,
                       ne.importance_score AS event_score,
                       ne.tier AS tier,
                       type(r) AS rel_type,
                       r.direction AS direction,
                       r.confidence AS confidence,
                       labels(target)[0] AS target_type,
                       CASE
                           WHEN 'Stock' IN labels(target) THEN target.symbol
                           WHEN 'Sector' IN labels(target) THEN target.name
                           ELSE 'unknown'
                       END AS target_id,
                       CASE
                           WHEN 'Stock' IN labels(target) THEN target.name
                           WHEN 'Sector' IN labels(target) THEN target.name
                           ELSE 'unknown'
                       END AS target_name
                """
                result = session.run(query, days=days, limit=limit)

                nodes = {}
                edges = []

                for record in result:
                    event_id = record['event_id']
                    target_id = record['target_id']
                    target_type = record['target_type']

                    # NewsEvent 노드
                    if event_id not in nodes:
                        nodes[event_id] = {
                            'id': event_id,
                            'label': record['event_title'][:60],
                            'type': 'NewsEvent',
                            'importance_score': record['event_score'],
                            'tier': record['tier'],
                        }

                    # 타겟 노드 (Stock/Sector)
                    target_key = f"{target_type}:{target_id}"
                    if target_key not in nodes:
                        nodes[target_key] = {
                            'id': target_id,
                            'label': record['target_name'] or target_id,
                            'type': target_type,
                        }

                    # 엣지
                    edges.append({
                        'source': event_id,
                        'target': target_id,
                        'type': record['rel_type'],
                        'direction': record['direction'],
                        'confidence': record['confidence'],
                    })

                # 통계
                stats = {
                    'total_events': len([n for n in nodes.values() if n['type'] == 'NewsEvent']),
                    'total_stocks': len([n for n in nodes.values() if n['type'] == 'Stock']),
                    'total_sectors': len([n for n in nodes.values() if n['type'] == 'Sector']),
                    'total_relationships': len(edges),
                }

                map_data = {
                    'nodes': list(nodes.values()),
                    'edges': edges,
                    'stats': stats,
                }

                cache.set(cache_key, map_data, self.CACHE_TTL)
                return map_data

        except Exception as e:
            logger.error(f"영향도 맵 조회 실패: {e}")
            return {'nodes': [], 'edges': [], 'stats': {}}

    def get_symbol_impact_summary(self, symbol: str, days: int = 7) -> dict:
        """
        특정 종목의 뉴스 영향 요약

        Returns:
            dict: {
                symbol, total_events, bullish_count, bearish_count,
                avg_confidence, direct_count, indirect_count,
                opportunity_count, top_events
            }
        """
        if not self.is_available():
            return self._empty_impact_summary(symbol)

        cache_key = f'news_impact_summary:{symbol}:{days}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            with self.driver.session() as session:
                query = """
                MATCH (ne:NewsEvent)-[r]->(s:Stock {symbol: $symbol})
                WHERE ne.published_at > datetime() - duration({days: $days})
                  AND type(r) IN ['DIRECTLY_IMPACTS', 'INDIRECTLY_IMPACTS', 'CREATES_OPPORTUNITY']
                RETURN count(DISTINCT ne) AS total_events,
                       sum(CASE WHEN r.direction = 'bullish' THEN 1 ELSE 0 END) AS bullish,
                       sum(CASE WHEN r.direction = 'bearish' THEN 1 ELSE 0 END) AS bearish,
                       avg(r.confidence) AS avg_confidence,
                       sum(CASE WHEN type(r) = 'DIRECTLY_IMPACTS' THEN 1 ELSE 0 END) AS direct,
                       sum(CASE WHEN type(r) = 'INDIRECTLY_IMPACTS' THEN 1 ELSE 0 END) AS indirect,
                       sum(CASE WHEN type(r) = 'CREATES_OPPORTUNITY' THEN 1 ELSE 0 END) AS opportunity
                """
                result = session.run(query, symbol=symbol.upper(), days=days)
                record = result.single()

                summary = {
                    'symbol': symbol.upper(),
                    'days': days,
                    'total_events': record['total_events'] if record else 0,
                    'bullish_count': record['bullish'] if record else 0,
                    'bearish_count': record['bearish'] if record else 0,
                    'avg_confidence': round(record['avg_confidence'], 3) if record and record['avg_confidence'] else 0.0,
                    'direct_count': record['direct'] if record else 0,
                    'indirect_count': record['indirect'] if record else 0,
                    'opportunity_count': record['opportunity'] if record else 0,
                }

                cache.set(cache_key, summary, self.CACHE_TTL)
                return summary

        except Exception as e:
            logger.error(f"영향 요약 조회 실패 {symbol}: {e}")
            return self._empty_impact_summary(symbol)

    def _empty_impact_summary(self, symbol: str) -> dict:
        return {
            'symbol': symbol.upper(),
            'days': 0,
            'total_events': 0,
            'bullish_count': 0,
            'bearish_count': 0,
            'avg_confidence': 0.0,
            'direct_count': 0,
            'indirect_count': 0,
            'opportunity_count': 0,
        }
