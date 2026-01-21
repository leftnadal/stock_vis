"""
OAG KB Schema Definitions
Enum, dataclass 정의 - 지식 베이스의 핵심 데이터 구조
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


class KnowledgeType(Enum):
    """지식 유형 분류"""
    # 투자 도메인
    TERM = "term"                      # 용어 정의
    METRIC = "metric"                  # 지표/메트릭
    STRATEGY = "strategy"              # 투자 전략
    REGULATION = "regulation"          # 규제/법규

    # 기술 도메인
    PATTERN = "pattern"                # 코딩 패턴
    API = "api"                        # API 사용법
    CONFIG = "config"                  # 설정 가이드
    ARCHITECTURE = "architecture"      # 아키텍처 결정

    # 프로젝트 도메인
    DECISION = "decision"              # 의사결정 기록
    LESSON = "lesson"                  # 교훈/배운점
    TROUBLESHOOT = "troubleshoot"      # 문제 해결
    WORKFLOW = "workflow"              # 워크플로우


class ConfidenceLevel(Enum):
    """신뢰도 수준"""
    VERIFIED = "verified"              # 검증됨 (공식 문서, 테스트 완료)
    HIGH = "high"                      # 높음 (전문가 확인)
    MEDIUM = "medium"                  # 중간 (일반적 합의)
    LOW = "low"                        # 낮음 (추정, 미검증)
    DEPRECATED = "deprecated"          # 폐기됨


class KnowledgeStatus(Enum):
    """지식 상태"""
    ACTIVE = "active"                  # 활성 (사용 가능)
    PENDING = "pending"                # 대기 (검토 필요)
    ARCHIVED = "archived"              # 보관됨
    REJECTED = "rejected"              # 거부됨


@dataclass
class KnowledgeItem:
    """지식 아이템 데이터 구조"""
    # 필수 필드
    id: str                            # 고유 ID (UUID)
    title: str                         # 제목
    content: str                       # 본문 내용
    knowledge_type: KnowledgeType      # 지식 유형

    # 메타데이터
    tags: List[str] = field(default_factory=list)
    source: Optional[str] = None       # 출처
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE

    # 관계
    related_to: List[str] = field(default_factory=list)  # 관련 지식 ID들
    parent_id: Optional[str] = None    # 상위 지식 ID

    # 컨텍스트
    domain: str = "general"            # 도메인 (investment, tech, project)
    applicable_to: List[str] = field(default_factory=list)  # 적용 대상

    # 타임스탬프
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"         # 생성자 (에이전트 또는 사용자)

    # 사용 통계
    usage_count: int = 0               # 조회 횟수
    last_used: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "knowledge_type": self.knowledge_type.value,
            "tags": self.tags,
            "source": self.source,
            "confidence": self.confidence.value,
            "status": self.status.value,
            "related_to": self.related_to,
            "parent_id": self.parent_id,
            "domain": self.domain,
            "applicable_to": self.applicable_to,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeItem":
        """딕셔너리에서 생성"""
        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            knowledge_type=KnowledgeType(data["knowledge_type"]),
            tags=data.get("tags", []),
            source=data.get("source"),
            confidence=ConfidenceLevel(data.get("confidence", "medium")),
            status=KnowledgeStatus(data.get("status", "active")),
            related_to=data.get("related_to", []),
            parent_id=data.get("parent_id"),
            domain=data.get("domain", "general"),
            applicable_to=data.get("applicable_to", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            created_by=data.get("created_by", "system"),
            usage_count=data.get("usage_count", 0),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
        )


@dataclass
class SearchResult:
    """검색 결과 데이터 구조"""
    item: KnowledgeItem
    score: float                       # 관련도 점수 (0.0 ~ 1.0)
    matched_fields: List[str] = field(default_factory=list)  # 매칭된 필드들
    highlight: Optional[str] = None    # 하이라이트된 텍스트

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "item": self.item.to_dict(),
            "score": self.score,
            "matched_fields": self.matched_fields,
            "highlight": self.highlight,
        }


@dataclass
class QueueItem:
    """큐레이션 큐 아이템"""
    id: str                            # 고유 ID
    knowledge_item: KnowledgeItem      # 지식 아이템
    action: str                        # 액션 (add, update, review, merge)
    priority: int = 0                  # 우선순위 (높을수록 먼저)
    reason: Optional[str] = None       # 큐에 추가된 이유
    suggested_by: str = "system"       # 제안자
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "knowledge_item": self.knowledge_item.to_dict(),
            "action": self.action,
            "priority": self.priority,
            "reason": self.reason,
            "suggested_by": self.suggested_by,
            "created_at": self.created_at.isoformat(),
        }
