"""
Token Budget Manager - 토큰 예산 관리자

LLM 호출 시 토큰 예산을 관리하고 최적화합니다.

Features:
    - 컨텍스트 크기 제한
    - 동적 토큰 할당
    - 우선순위 기반 컨텐츠 선택
    - 압축률 최적화
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ContentPriority(Enum):
    """컨텐츠 우선순위"""
    CRITICAL = 1    # 필수 (그래프 관계, 핵심 수치)
    HIGH = 2        # 높음 (최근 뉴스, 주요 지표)
    MEDIUM = 3      # 중간 (과거 데이터, 부가 정보)
    LOW = 4         # 낮음 (배경 정보, 일반 설명)


@dataclass
class ContentBlock:
    """컨텐츠 블록"""
    content: str
    priority: ContentPriority
    token_count: int
    source: str  # 'graph', 'news', 'financial', 'overview', etc.
    metadata: Optional[Dict[str, Any]] = None

    @property
    def tokens_per_priority(self) -> float:
        """우선순위 대비 토큰 효율"""
        return self.token_count / self.priority.value


class TokenBudgetManager:
    """
    토큰 예산 관리자

    제한된 토큰 예산 내에서 가장 가치 있는 컨텐츠를 선택합니다.
    """

    # 기본 예산 설정
    DEFAULT_BUDGETS = {
        'simple': {
            'system_prompt': 150,
            'context': 400,
            'question': 50,
            'total_input': 600,
            'max_output': 800,
        },
        'moderate': {
            'system_prompt': 200,
            'context': 800,
            'question': 100,
            'total_input': 1100,
            'max_output': 1500,
        },
        'complex': {
            'system_prompt': 250,
            'context': 1500,
            'question': 150,
            'total_input': 1900,
            'max_output': 2500,
        },
    }

    # 소스별 기본 우선순위
    SOURCE_PRIORITY = {
        'graph_relationship': ContentPriority.CRITICAL,
        'current_price': ContentPriority.CRITICAL,
        'recent_news': ContentPriority.HIGH,
        'financial_summary': ContentPriority.HIGH,
        'technical_indicator': ContentPriority.MEDIUM,
        'historical_data': ContentPriority.MEDIUM,
        'company_overview': ContentPriority.LOW,
        'sector_info': ContentPriority.LOW,
    }

    def __init__(self, complexity: str = 'moderate'):
        """
        Args:
            complexity: 'simple', 'moderate', 'complex'
        """
        self.complexity = complexity
        self.budget = self.DEFAULT_BUDGETS.get(complexity, self.DEFAULT_BUDGETS['moderate'])

    def allocate(
        self,
        content_blocks: List[ContentBlock],
        reserved_tokens: int = 0
    ) -> Tuple[List[ContentBlock], Dict[str, Any]]:
        """
        토큰 예산 내에서 컨텐츠 할당

        Args:
            content_blocks: 컨텐츠 블록 리스트
            reserved_tokens: 시스템 프롬프트 등 예약된 토큰

        Returns:
            (선택된 블록 리스트, 할당 정보)
        """
        available_budget = self.budget['context'] - reserved_tokens
        if available_budget <= 0:
            return [], {'error': 'No budget available'}

        # 우선순위로 정렬
        sorted_blocks = sorted(content_blocks, key=lambda b: b.priority.value)

        selected = []
        used_tokens = 0
        excluded = []

        for block in sorted_blocks:
            if used_tokens + block.token_count <= available_budget:
                selected.append(block)
                used_tokens += block.token_count
            else:
                # 부분 포함 시도 (CRITICAL 우선순위만)
                if block.priority == ContentPriority.CRITICAL:
                    remaining = available_budget - used_tokens
                    if remaining > 50:  # 최소 50토큰 이상이면 부분 포함
                        truncated = self._truncate_content(block, remaining)
                        if truncated:
                            selected.append(truncated)
                            used_tokens += truncated.token_count
                    else:
                        excluded.append(block)
                else:
                    excluded.append(block)

        allocation_info = {
            'budget': available_budget,
            'used': used_tokens,
            'remaining': available_budget - used_tokens,
            'utilization': used_tokens / available_budget if available_budget > 0 else 0,
            'selected_count': len(selected),
            'excluded_count': len(excluded),
            'by_priority': self._count_by_priority(selected),
        }

        logger.info(
            f"Token allocation: {used_tokens}/{available_budget} tokens, "
            f"{len(selected)} blocks selected, {len(excluded)} excluded"
        )

        return selected, allocation_info

    def _truncate_content(self, block: ContentBlock, max_tokens: int) -> Optional[ContentBlock]:
        """컨텐츠 잘라내기"""
        if max_tokens < 20:
            return None

        # 대략적인 토큰-글자 비율 (한글: 1.5, 영어: 0.25)
        words = block.content.split()
        estimated_ratio = block.token_count / len(words) if words else 1

        target_words = int(max_tokens / estimated_ratio)
        truncated_content = ' '.join(words[:target_words]) + '...'

        return ContentBlock(
            content=truncated_content,
            priority=block.priority,
            token_count=max_tokens,
            source=block.source,
            metadata={**(block.metadata or {}), 'truncated': True}
        )

    def _count_by_priority(self, blocks: List[ContentBlock]) -> Dict[str, int]:
        """우선순위별 카운트"""
        counts = {}
        for block in blocks:
            key = block.priority.name
            counts[key] = counts.get(key, 0) + 1
        return counts

    def build_context(
        self,
        selected_blocks: List[ContentBlock],
        include_sources: bool = True
    ) -> str:
        """
        선택된 블록으로 컨텍스트 문자열 생성

        Args:
            selected_blocks: 선택된 컨텐츠 블록
            include_sources: 소스 태그 포함 여부

        Returns:
            포맷된 컨텍스트 문자열
        """
        if not selected_blocks:
            return ""

        # 소스별 그룹화
        by_source = {}
        for block in selected_blocks:
            source = block.source
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(block)

        # 섹션별 포맷팅
        sections = []

        # 그래프 관계 먼저
        if 'graph_relationship' in by_source:
            section = "## 종목 관계\n"
            for block in by_source['graph_relationship']:
                section += f"{block.content}\n"
            sections.append(section)

        # 현재 가격/지표
        for source in ['current_price', 'financial_summary']:
            if source in by_source:
                section = f"## {self._source_to_title(source)}\n"
                for block in by_source[source]:
                    section += f"{block.content}\n"
                sections.append(section)

        # 뉴스
        if 'recent_news' in by_source:
            section = "## 최근 뉴스\n"
            for i, block in enumerate(by_source['recent_news'], 1):
                section += f"{i}. {block.content}\n"
            sections.append(section)

        # 기타
        other_sources = [s for s in by_source if s not in [
            'graph_relationship', 'current_price', 'financial_summary', 'recent_news'
        ]]
        for source in other_sources:
            section = f"## {self._source_to_title(source)}\n"
            for block in by_source[source]:
                section += f"{block.content}\n"
            sections.append(section)

        return '\n'.join(sections)

    def _source_to_title(self, source: str) -> str:
        """소스를 제목으로 변환"""
        titles = {
            'graph_relationship': '종목 관계',
            'current_price': '현재 가격',
            'financial_summary': '재무 요약',
            'recent_news': '최근 뉴스',
            'technical_indicator': '기술적 지표',
            'historical_data': '과거 데이터',
            'company_overview': '기업 개요',
            'sector_info': '섹터 정보',
        }
        return titles.get(source, source.replace('_', ' ').title())

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        텍스트의 토큰 수 추정

        대략적인 추정:
        - 영어: 4글자 = 1토큰
        - 한글: 1.5글자 = 1토큰
        """
        if not text:
            return 0

        # 한글 비율 계산
        korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7af')
        total_chars = len(text)

        if total_chars == 0:
            return 0

        korean_ratio = korean_chars / total_chars

        # 가중 평균 토큰 추정
        if korean_ratio > 0.5:
            # 한글 위주
            return int(total_chars / 1.5)
        else:
            # 영어 위주
            return int(total_chars / 4)

    def create_content_block(
        self,
        content: str,
        source: str,
        priority: Optional[ContentPriority] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContentBlock:
        """
        컨텐츠 블록 생성 헬퍼

        Args:
            content: 컨텐츠 텍스트
            source: 소스 타입
            priority: 우선순위 (None이면 소스 기반 자동 결정)
            metadata: 추가 메타데이터
        """
        if priority is None:
            priority = self.SOURCE_PRIORITY.get(source, ContentPriority.MEDIUM)

        return ContentBlock(
            content=content,
            priority=priority,
            token_count=self.estimate_tokens(content),
            source=source,
            metadata=metadata
        )


class DynamicBudgetManager(TokenBudgetManager):
    """
    동적 토큰 예산 관리자

    실시간 사용량과 비용 제한을 고려하여 예산을 조정합니다.
    """

    def __init__(
        self,
        complexity: str = 'moderate',
        cost_limit_usd: float = 0.01,
        target_cost_per_request: float = 0.001
    ):
        super().__init__(complexity)
        self.cost_limit_usd = cost_limit_usd
        self.target_cost = target_cost_per_request

    def adjust_budget_for_cost(
        self,
        current_daily_cost: float,
        daily_limit: float
    ) -> Dict[str, int]:
        """
        비용 상황에 따라 예산 조정

        Args:
            current_daily_cost: 현재 일일 누적 비용
            daily_limit: 일일 비용 한도

        Returns:
            조정된 예산
        """
        remaining_budget = daily_limit - current_daily_cost
        usage_ratio = current_daily_cost / daily_limit if daily_limit > 0 else 0

        adjusted = self.budget.copy()

        if usage_ratio >= 0.9:
            # 90% 이상 사용: 최소 모드
            adjusted['context'] = int(adjusted['context'] * 0.5)
            adjusted['max_output'] = int(adjusted['max_output'] * 0.5)
            logger.warning("Budget adjusted to minimal mode due to cost limit")

        elif usage_ratio >= 0.7:
            # 70% 이상 사용: 절약 모드
            adjusted['context'] = int(adjusted['context'] * 0.7)
            adjusted['max_output'] = int(adjusted['max_output'] * 0.7)
            logger.info("Budget adjusted to economy mode")

        return adjusted


# 편의 함수
def get_token_budget_manager(complexity: str = 'moderate') -> TokenBudgetManager:
    """TokenBudgetManager 인스턴스 반환"""
    return TokenBudgetManager(complexity)


def get_dynamic_budget_manager(
    complexity: str = 'moderate',
    cost_limit: float = 0.01
) -> DynamicBudgetManager:
    """DynamicBudgetManager 인스턴스 반환"""
    return DynamicBudgetManager(complexity, cost_limit)
