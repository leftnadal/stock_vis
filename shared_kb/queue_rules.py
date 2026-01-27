"""
OAG KB Queue Rules
자동 큐 저장 규칙 - 에이전트가 지식을 발견할 때 자동으로 큐에 추가
"""

from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from .schema import KnowledgeType, KnowledgeItem
from .queue import CurationQueue


@dataclass
class QueueRule:
    """큐 저장 규칙 정의"""
    name: str                          # 규칙 이름
    description: str                   # 규칙 설명
    knowledge_types: List[KnowledgeType]  # 적용 지식 유형
    domains: List[str]                 # 적용 도메인
    priority: int = 0                  # 기본 우선순위
    auto_add: bool = True              # 자동 추가 여부
    condition: Optional[Callable[[KnowledgeItem], bool]] = None  # 조건 함수


# ==================== 사전 정의된 규칙들 ====================

INVESTMENT_TERM_RULE = QueueRule(
    name="investment_term",
    description="투자 용어는 높은 우선순위로 자동 추가",
    knowledge_types=[KnowledgeType.TERM, KnowledgeType.METRIC],
    domains=["investment"],
    priority=10,
    auto_add=True,
)

TROUBLESHOOT_RULE = QueueRule(
    name="troubleshoot",
    description="문제 해결 지식은 즉시 추가",
    knowledge_types=[KnowledgeType.TROUBLESHOOT],
    domains=["tech", "project"],
    priority=15,
    auto_add=True,
)

PATTERN_RULE = QueueRule(
    name="coding_pattern",
    description="코딩 패턴은 검토 후 추가",
    knowledge_types=[KnowledgeType.PATTERN, KnowledgeType.API],
    domains=["tech"],
    priority=5,
    auto_add=True,
)

DECISION_RULE = QueueRule(
    name="decision_record",
    description="의사결정 기록은 보관 우선순위",
    knowledge_types=[KnowledgeType.DECISION],
    domains=["project"],
    priority=8,
    auto_add=True,
)


# 기본 규칙 목록
DEFAULT_RULES = [
    INVESTMENT_TERM_RULE,
    TROUBLESHOOT_RULE,
    PATTERN_RULE,
    DECISION_RULE,
]


class QueueRuleEngine:
    """
    큐 규칙 엔진

    지식 아이템이 생성될 때 규칙을 평가하고
    조건에 맞으면 자동으로 큐에 추가
    """

    def __init__(self, queue: CurationQueue = None, rules: List[QueueRule] = None):
        """
        Args:
            queue: CurationQueue 인스턴스
            rules: 적용할 규칙 목록 (기본: DEFAULT_RULES)
        """
        self.queue = queue or CurationQueue()
        self.rules = rules or DEFAULT_RULES.copy()

    def add_rule(self, rule: QueueRule):
        """규칙 추가"""
        self.rules.append(rule)

    def remove_rule(self, rule_name: str) -> bool:
        """규칙 제거"""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                self.rules.pop(i)
                return True
        return False

    def evaluate(self, item: KnowledgeItem) -> Optional[QueueRule]:
        """
        지식 아이템에 대해 규칙 평가

        Args:
            item: 평가할 KnowledgeItem

        Returns:
            매칭되는 규칙 (없으면 None)
        """
        for rule in self.rules:
            # 지식 유형 체크
            if item.knowledge_type not in rule.knowledge_types:
                continue

            # 도메인 체크
            if item.domain not in rule.domains:
                continue

            # 커스텀 조건 체크
            if rule.condition and not rule.condition(item):
                continue

            return rule

        return None

    def process(
        self,
        item: KnowledgeItem,
        suggested_by: str = "system",
        reason: str = None,
    ) -> Optional[str]:
        """
        지식 아이템 처리 - 규칙 평가 및 큐 추가

        Args:
            item: 처리할 KnowledgeItem
            suggested_by: 제안자
            reason: 추가 이유

        Returns:
            큐에 추가된 경우 큐 아이템 ID, 아니면 None
        """
        rule = self.evaluate(item)

        if rule and rule.auto_add:
            queue_id = self.queue.add(
                title=item.title,
                content=item.content,
                knowledge_type=item.knowledge_type,
                action="add",
                tags=item.tags,
                source=item.source,
                domain=item.domain,
                priority=rule.priority,
                reason=reason or f"자동 추가 (규칙: {rule.name})",
                suggested_by=suggested_by,
            )
            return queue_id

        return None

    def get_applicable_rules(self, item: KnowledgeItem) -> List[QueueRule]:
        """적용 가능한 모든 규칙 조회"""
        applicable = []
        for rule in self.rules:
            if item.knowledge_type in rule.knowledge_types:
                if item.domain in rule.domains:
                    applicable.append(rule)
        return applicable


# ==================== 에이전트별 규칙 ====================

def create_agent_rules(agent_name: str) -> List[QueueRule]:
    """에이전트별 맞춤 규칙 생성"""

    if agent_name == "investment-advisor":
        return [
            QueueRule(
                name="investment_explanation",
                description="투자 설명 콘텐츠 자동 추가",
                knowledge_types=[KnowledgeType.TERM, KnowledgeType.METRIC, KnowledgeType.STRATEGY],
                domains=["investment"],
                priority=10,
                auto_add=True,
            ),
        ]

    elif agent_name == "backend":
        return [
            QueueRule(
                name="api_pattern",
                description="API 패턴 자동 추가",
                knowledge_types=[KnowledgeType.API, KnowledgeType.PATTERN],
                domains=["tech"],
                priority=5,
                auto_add=True,
            ),
        ]

    elif agent_name == "frontend":
        return [
            QueueRule(
                name="ui_pattern",
                description="UI 패턴 자동 추가",
                knowledge_types=[KnowledgeType.PATTERN],
                domains=["tech"],
                priority=5,
                auto_add=True,
            ),
        ]

    elif agent_name == "qa-architect":
        return [
            QueueRule(
                name="quality_lesson",
                description="품질 관련 교훈 자동 추가",
                knowledge_types=[KnowledgeType.LESSON, KnowledgeType.TROUBLESHOOT],
                domains=["tech", "project"],
                priority=8,
                auto_add=True,
            ),
        ]

    return DEFAULT_RULES
