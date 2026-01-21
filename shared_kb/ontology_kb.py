"""
OAG KB Core - Ontology Knowledge Base
Neo4j 기반 지식 그래프 관리 클래스
"""

import os
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

# .env 파일 로딩 (프로젝트 루트에서)
try:
    from dotenv import load_dotenv
    # shared_kb 상위 디렉토리의 .env 로딩
    project_root = Path(__file__).parent.parent
    load_dotenv(project_root / ".env")
except ImportError:
    pass  # python-dotenv가 없으면 환경변수만 사용

from neo4j import GraphDatabase

from .schema import (
    KnowledgeType,
    ConfidenceLevel,
    KnowledgeStatus,
    KnowledgeItem,
    SearchResult,
)


class OntologyKB:
    """
    Ontology Knowledge Base - Neo4j 기반 지식 그래프

    사용법:
        kb = OntologyKB()
        kb.add_knowledge(item)
        results = kb.search("PER 지표")
        kb.close()
    """

    def __init__(self, uri: str = None, username: str = None, password: str = None):
        """
        Neo4j 연결 초기화

        환경변수:
            NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
        """
        self.uri = uri or os.getenv("NEO4J_URI")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")

        if not self.uri or not self.password:
            raise ValueError(
                "Neo4j 연결 정보가 필요합니다. "
                "환경변수 NEO4J_URI, NEO4J_PASSWORD를 설정하세요."
            )

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password)
        )
        self._ensure_indexes()

    def _ensure_indexes(self):
        """필수 인덱스 생성"""
        with self.driver.session() as session:
            # Knowledge 노드 인덱스
            session.run("""
                CREATE INDEX knowledge_id IF NOT EXISTS
                FOR (k:Knowledge) ON (k.id)
            """)
            session.run("""
                CREATE INDEX knowledge_type IF NOT EXISTS
                FOR (k:Knowledge) ON (k.knowledge_type)
            """)
            session.run("""
                CREATE INDEX knowledge_domain IF NOT EXISTS
                FOR (k:Knowledge) ON (k.domain)
            """)
            # 전문 검색 인덱스 (텍스트 검색용)
            try:
                session.run("""
                    CREATE FULLTEXT INDEX knowledge_fulltext IF NOT EXISTS
                    FOR (k:Knowledge) ON EACH [k.title, k.content, k.tags_text]
                """)
            except Exception:
                pass  # 이미 존재하거나 지원 안 되는 경우

    def close(self):
        """연결 종료"""
        if self.driver:
            self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== CRUD Operations ====================

    def add_knowledge(self, item: KnowledgeItem) -> str:
        """
        지식 추가

        Args:
            item: KnowledgeItem 인스턴스

        Returns:
            생성된 지식의 ID
        """
        if not item.id:
            item.id = str(uuid.uuid4())

        with self.driver.session() as session:
            session.run("""
                CREATE (k:Knowledge {
                    id: $id,
                    title: $title,
                    content: $content,
                    knowledge_type: $knowledge_type,
                    tags: $tags,
                    tags_text: $tags_text,
                    source: $source,
                    confidence: $confidence,
                    status: $status,
                    domain: $domain,
                    applicable_to: $applicable_to,
                    created_at: $created_at,
                    updated_at: $updated_at,
                    created_by: $created_by,
                    usage_count: $usage_count
                })
            """, {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "knowledge_type": item.knowledge_type.value,
                "tags": item.tags,
                "tags_text": " ".join(item.tags),
                "source": item.source,
                "confidence": item.confidence.value,
                "status": item.status.value,
                "domain": item.domain,
                "applicable_to": item.applicable_to,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
                "created_by": item.created_by,
                "usage_count": item.usage_count,
            })

            # 관계 생성
            for related_id in item.related_to:
                session.run("""
                    MATCH (k1:Knowledge {id: $id1})
                    MATCH (k2:Knowledge {id: $id2})
                    MERGE (k1)-[:RELATED_TO]->(k2)
                """, {"id1": item.id, "id2": related_id})

            if item.parent_id:
                session.run("""
                    MATCH (child:Knowledge {id: $child_id})
                    MATCH (parent:Knowledge {id: $parent_id})
                    MERGE (child)-[:CHILD_OF]->(parent)
                """, {"child_id": item.id, "parent_id": item.parent_id})

        return item.id

    def get_knowledge(self, knowledge_id: str) -> Optional[KnowledgeItem]:
        """ID로 지식 조회"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (k:Knowledge {id: $id})
                OPTIONAL MATCH (k)-[:RELATED_TO]->(r:Knowledge)
                OPTIONAL MATCH (k)-[:CHILD_OF]->(p:Knowledge)
                RETURN k, collect(DISTINCT r.id) as related, p.id as parent
            """, {"id": knowledge_id})

            record = result.single()
            if not record:
                return None

            node = record["k"]
            return self._node_to_item(node, record["related"], record["parent"])

    def update_knowledge(self, item: KnowledgeItem) -> bool:
        """지식 업데이트"""
        item.updated_at = datetime.now()

        with self.driver.session() as session:
            result = session.run("""
                MATCH (k:Knowledge {id: $id})
                SET k.title = $title,
                    k.content = $content,
                    k.knowledge_type = $knowledge_type,
                    k.tags = $tags,
                    k.tags_text = $tags_text,
                    k.source = $source,
                    k.confidence = $confidence,
                    k.status = $status,
                    k.domain = $domain,
                    k.applicable_to = $applicable_to,
                    k.updated_at = $updated_at
                RETURN k
            """, {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "knowledge_type": item.knowledge_type.value,
                "tags": item.tags,
                "tags_text": " ".join(item.tags),
                "source": item.source,
                "confidence": item.confidence.value,
                "status": item.status.value,
                "domain": item.domain,
                "applicable_to": item.applicable_to,
                "updated_at": item.updated_at.isoformat(),
            })

            return result.single() is not None

    def delete_knowledge(self, knowledge_id: str) -> bool:
        """지식 삭제"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (k:Knowledge {id: $id})
                DETACH DELETE k
                RETURN count(*) as deleted
            """, {"id": knowledge_id})

            record = result.single()
            return record and record["deleted"] > 0

    # ==================== Search Operations ====================

    def search(
        self,
        query: str,
        knowledge_type: Optional[KnowledgeType] = None,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        confidence_min: Optional[ConfidenceLevel] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """
        지식 검색

        Args:
            query: 검색어
            knowledge_type: 지식 유형 필터
            domain: 도메인 필터
            tags: 태그 필터 (OR 조건)
            confidence_min: 최소 신뢰도
            limit: 결과 수 제한

        Returns:
            SearchResult 리스트 (점수순 정렬)
        """
        with self.driver.session() as session:
            # 기본 검색 쿼리 (CONTAINS 사용)
            where_clauses = []
            params = {"query": query.lower(), "limit": limit}

            # 텍스트 검색 조건
            where_clauses.append(
                "(toLower(k.title) CONTAINS $query OR "
                "toLower(k.content) CONTAINS $query OR "
                "toLower(k.tags_text) CONTAINS $query)"
            )

            # 필터 조건
            if knowledge_type:
                where_clauses.append("k.knowledge_type = $knowledge_type")
                params["knowledge_type"] = knowledge_type.value

            if domain:
                where_clauses.append("k.domain = $domain")
                params["domain"] = domain

            if tags:
                where_clauses.append("ANY(tag IN k.tags WHERE tag IN $tags)")
                params["tags"] = tags

            # 신뢰도 필터
            confidence_order = ["verified", "high", "medium", "low", "deprecated"]
            if confidence_min:
                min_idx = confidence_order.index(confidence_min.value)
                allowed = confidence_order[:min_idx + 1]
                where_clauses.append("k.confidence IN $allowed_confidence")
                params["allowed_confidence"] = allowed

            # 활성 상태만
            where_clauses.append("k.status = 'active'")

            where_clause = " AND ".join(where_clauses)

            cypher = f"""
                MATCH (k:Knowledge)
                WHERE {where_clause}
                WITH k,
                     CASE
                        WHEN toLower(k.title) CONTAINS $query THEN 3
                        WHEN toLower(k.tags_text) CONTAINS $query THEN 2
                        ELSE 1
                     END as score
                RETURN k, score
                ORDER BY score DESC, k.usage_count DESC
                LIMIT $limit
            """

            result = session.run(cypher, params)

            search_results = []
            for record in result:
                node = record["k"]
                item = self._node_to_item(node)

                # 매칭 필드 결정
                matched = []
                query_lower = query.lower()
                if query_lower in node["title"].lower():
                    matched.append("title")
                if query_lower in node["content"].lower():
                    matched.append("content")
                if query_lower in node.get("tags_text", "").lower():
                    matched.append("tags")

                search_results.append(SearchResult(
                    item=item,
                    score=record["score"] / 3.0,  # 정규화
                    matched_fields=matched,
                ))

            return search_results

    def get_related(self, knowledge_id: str, depth: int = 1) -> List[KnowledgeItem]:
        """관련 지식 조회"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (k:Knowledge {id: $id})-[:RELATED_TO*1..$depth]-(related:Knowledge)
                WHERE related.status = 'active'
                RETURN DISTINCT related
                LIMIT 20
            """, {"id": knowledge_id, "depth": depth})

            return [self._node_to_item(record["related"]) for record in result]

    def get_by_type(
        self,
        knowledge_type: KnowledgeType,
        domain: Optional[str] = None,
        limit: int = 50,
    ) -> List[KnowledgeItem]:
        """유형별 지식 조회"""
        with self.driver.session() as session:
            params = {
                "knowledge_type": knowledge_type.value,
                "limit": limit,
            }

            where_clause = "k.knowledge_type = $knowledge_type AND k.status = 'active'"
            if domain:
                where_clause += " AND k.domain = $domain"
                params["domain"] = domain

            result = session.run(f"""
                MATCH (k:Knowledge)
                WHERE {where_clause}
                RETURN k
                ORDER BY k.usage_count DESC, k.updated_at DESC
                LIMIT $limit
            """, params)

            return [self._node_to_item(record["k"]) for record in result]

    # ==================== Statistics ====================

    def get_stats(self) -> Dict[str, Any]:
        """KB 통계 조회"""
        with self.driver.session() as session:
            # 전체 수
            total = session.run("""
                MATCH (k:Knowledge)
                RETURN count(k) as total
            """).single()["total"]

            # 유형별 수
            by_type = {}
            result = session.run("""
                MATCH (k:Knowledge)
                RETURN k.knowledge_type as type, count(*) as count
            """)
            for record in result:
                by_type[record["type"]] = record["count"]

            # 도메인별 수
            by_domain = {}
            result = session.run("""
                MATCH (k:Knowledge)
                RETURN k.domain as domain, count(*) as count
            """)
            for record in result:
                by_domain[record["domain"]] = record["count"]

            # 신뢰도별 수
            by_confidence = {}
            result = session.run("""
                MATCH (k:Knowledge)
                RETURN k.confidence as confidence, count(*) as count
            """)
            for record in result:
                by_confidence[record["confidence"]] = record["count"]

            # 관계 수
            relationships = session.run("""
                MATCH ()-[r:RELATED_TO]->()
                RETURN count(r) as count
            """).single()["count"]

            return {
                "total_knowledge": total,
                "by_type": by_type,
                "by_domain": by_domain,
                "by_confidence": by_confidence,
                "total_relationships": relationships,
            }

    def increment_usage(self, knowledge_id: str):
        """사용 횟수 증가"""
        with self.driver.session() as session:
            session.run("""
                MATCH (k:Knowledge {id: $id})
                SET k.usage_count = k.usage_count + 1,
                    k.last_used = $now
            """, {"id": knowledge_id, "now": datetime.now().isoformat()})

    # ==================== Helper Methods ====================

    def _node_to_item(
        self,
        node,
        related_ids: List[str] = None,
        parent_id: str = None,
    ) -> KnowledgeItem:
        """Neo4j 노드를 KnowledgeItem으로 변환"""
        return KnowledgeItem(
            id=node["id"],
            title=node["title"],
            content=node["content"],
            knowledge_type=KnowledgeType(node["knowledge_type"]),
            tags=node.get("tags", []),
            source=node.get("source"),
            confidence=ConfidenceLevel(node.get("confidence", "medium")),
            status=KnowledgeStatus(node.get("status", "active")),
            related_to=related_ids or [],
            parent_id=parent_id,
            domain=node.get("domain", "general"),
            applicable_to=node.get("applicable_to", []),
            created_at=datetime.fromisoformat(node["created_at"]) if node.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(node["updated_at"]) if node.get("updated_at") else datetime.now(),
            created_by=node.get("created_by", "system"),
            usage_count=node.get("usage_count", 0),
            last_used=datetime.fromisoformat(node["last_used"]) if node.get("last_used") else None,
        )
