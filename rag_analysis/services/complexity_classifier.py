"""
Complexity Classifier - 질문 복잡도 분류기

질문의 복잡도를 분석하여 적절한 LLM 모델과 설정을 결정합니다.

Complexity Levels:
    - SIMPLE: 단순 정보 조회 (가격, PER 등) → 경량 모델
    - MODERATE: 일반적인 분석 → 중간 모델
    - COMPLEX: 심층 분석, 비교 분석 → 고성능 모델
"""

import re
import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class QuestionComplexity(Enum):
    """질문 복잡도 레벨"""
    SIMPLE = "simple"       # 단순 정보 조회 → Haiku/Gemini Flash
    MODERATE = "moderate"   # 일반 분석 → Sonnet/Gemini Flash
    COMPLEX = "complex"     # 심층 분석 → Sonnet/Gemini Pro


@dataclass
class ModelConfig:
    """모델 설정"""
    model: str
    max_tokens: int
    temperature: float = 0.7
    estimated_cost_per_1k_tokens: float = 0.0


class ComplexityClassifier:
    """
    질문 복잡도 분류기

    패턴 매칭과 휴리스틱을 사용하여 질문의 복잡도를 분류합니다.
    """

    # 복잡도별 패턴
    SIMPLE_PATTERNS = [
        r'현재\s*(가격|주가|시세)',
        r'(PER|PBR|ROE|ROA|EPS|BPS)\s*(은|는|가|이)?(\s*얼마)?',
        r'시가총액',
        r'52주\s*(최고|최저|고가|저가)',
        r'배당\s*(금|률|수익률)',
        r'몇\s*(주|달러|원)',
        r'(상장|설립)\s*일',
        r'섹터|업종',
        r'거래량',
    ]

    COMPLEX_PATTERNS = [
        r'비교.*분석',
        r'(영향|관계).*분석',
        r'전망|예측|예상',
        r'(투자|매수|매도)\s*전략',
        r'리스크.*분석',
        r'장단점',
        r'포트폴리오',
        r'상관관계',
        r'시나리오',
        r'(어떻게|왜).*영향',
        r'(상승|하락)\s*요인',
        r'경쟁\s*(구도|분석|현황)',
        r'밸류에이션.*분석',
        r'재무제표.*분석',
        r'(사업|수익)\s*구조',
    ]

    # 복잡도 증가 요인
    COMPLEXITY_BOOSTERS = [
        (r'\s*그리고\s*', 0.1),
        (r'\s*또한\s*', 0.1),
        (r'\s*동시에\s*', 0.15),
        (r'\s*(비교|대비)\s*', 0.2),
        (r'[,;]\s*', 0.05),  # 쉼표로 구분된 다중 요청
    ]

    # Gemini 모델 설정 (기본값)
    GEMINI_CONFIGS = {
        QuestionComplexity.SIMPLE: ModelConfig(
            model='gemini-2.5-flash',
            max_tokens=800,
            temperature=0.5,
            estimated_cost_per_1k_tokens=0.00015
        ),
        QuestionComplexity.MODERATE: ModelConfig(
            model='gemini-2.5-flash',
            max_tokens=1500,
            temperature=0.7,
            estimated_cost_per_1k_tokens=0.00015
        ),
        QuestionComplexity.COMPLEX: ModelConfig(
            model='gemini-2.5-flash',  # 비용 최적화를 위해 Flash 유지, 토큰만 증가
            max_tokens=2500,
            temperature=0.7,
            estimated_cost_per_1k_tokens=0.00015
        ),
    }

    # Claude 모델 설정 (대안)
    CLAUDE_CONFIGS = {
        QuestionComplexity.SIMPLE: ModelConfig(
            model='claude-3-5-haiku-20241022',
            max_tokens=800,
            temperature=0.5,
            estimated_cost_per_1k_tokens=0.0008
        ),
        QuestionComplexity.MODERATE: ModelConfig(
            model='claude-sonnet-4-20250514',
            max_tokens=1500,
            temperature=0.7,
            estimated_cost_per_1k_tokens=0.003
        ),
        QuestionComplexity.COMPLEX: ModelConfig(
            model='claude-sonnet-4-20250514',
            max_tokens=2500,
            temperature=0.7,
            estimated_cost_per_1k_tokens=0.003
        ),
    }

    def __init__(self, provider: str = 'gemini'):
        """
        Args:
            provider: 'gemini' 또는 'claude'
        """
        self.provider = provider
        self._compiled_simple = [re.compile(p, re.IGNORECASE) for p in self.SIMPLE_PATTERNS]
        self._compiled_complex = [re.compile(p, re.IGNORECASE) for p in self.COMPLEX_PATTERNS]
        self._compiled_boosters = [(re.compile(p, re.IGNORECASE), w) for p, w in self.COMPLEXITY_BOOSTERS]

    def classify(
        self,
        question: str,
        entities_count: int = 0,
        context_tokens: int = 0
    ) -> QuestionComplexity:
        """
        질문 복잡도 분류

        Args:
            question: 사용자 질문
            entities_count: 추출된 엔티티 수
            context_tokens: 컨텍스트 토큰 수 (예상)

        Returns:
            QuestionComplexity 레벨
        """
        score = self._calculate_complexity_score(question, entities_count, context_tokens)

        if score <= 0.3:
            complexity = QuestionComplexity.SIMPLE
        elif score <= 0.6:
            complexity = QuestionComplexity.MODERATE
        else:
            complexity = QuestionComplexity.COMPLEX

        logger.debug(f"Question complexity: {complexity.value} (score: {score:.2f})")
        return complexity

    def _calculate_complexity_score(
        self,
        question: str,
        entities_count: int,
        context_tokens: int
    ) -> float:
        """
        복잡도 점수 계산 (0.0 ~ 1.0)

        Factors:
            - 패턴 매칭 (SIMPLE: -0.3, COMPLEX: +0.3)
            - 질문 길이 (길수록 +)
            - 엔티티 수 (많을수록 +)
            - 컨텍스트 크기 (클수록 +)
            - 복잡도 부스터 (특정 키워드)
        """
        score = 0.5  # 기본값: MODERATE

        # 1. 패턴 매칭
        for pattern in self._compiled_simple:
            if pattern.search(question):
                score -= 0.15
                break  # 첫 매칭만

        for pattern in self._compiled_complex:
            if pattern.search(question):
                score += 0.15

        # 2. 질문 길이 (50자 이하: -0.1, 150자 이상: +0.1)
        q_len = len(question)
        if q_len <= 50:
            score -= 0.1
        elif q_len >= 150:
            score += 0.1

        # 3. 엔티티 수 (1개: -0.1, 3개 이상: +0.1)
        if entities_count <= 1:
            score -= 0.1
        elif entities_count >= 3:
            score += 0.15

        # 4. 컨텍스트 크기 (1000 이상: +0.1)
        if context_tokens >= 1000:
            score += 0.1

        # 5. 복잡도 부스터
        for pattern, weight in self._compiled_boosters:
            if pattern.search(question):
                score += weight

        # 범위 제한
        return max(0.0, min(1.0, score))

    def get_model_config(self, complexity: QuestionComplexity) -> ModelConfig:
        """
        복잡도에 따른 모델 설정 반환

        Args:
            complexity: 질문 복잡도

        Returns:
            ModelConfig
        """
        if self.provider == 'claude':
            return self.CLAUDE_CONFIGS[complexity]
        return self.GEMINI_CONFIGS[complexity]

    def classify_and_configure(
        self,
        question: str,
        entities_count: int = 0,
        context_tokens: int = 0
    ) -> Dict[str, Any]:
        """
        분류 + 설정을 한번에 반환

        Returns:
            {
                'complexity': QuestionComplexity,
                'complexity_score': float,
                'model': str,
                'max_tokens': int,
                'temperature': float,
                'estimated_cost': float
            }
        """
        score = self._calculate_complexity_score(question, entities_count, context_tokens)

        if score <= 0.3:
            complexity = QuestionComplexity.SIMPLE
        elif score <= 0.6:
            complexity = QuestionComplexity.MODERATE
        else:
            complexity = QuestionComplexity.COMPLEX

        config = self.get_model_config(complexity)

        return {
            'complexity': complexity,
            'complexity_score': score,
            'model': config.model,
            'max_tokens': config.max_tokens,
            'temperature': config.temperature,
            'estimated_cost_per_1k': config.estimated_cost_per_1k_tokens,
        }


class QuestionAnalyzer:
    """
    질문 분석기 (확장)

    복잡도 분류 외에 질문 유형과 의도도 분석합니다.
    """

    class QuestionType(Enum):
        FACTUAL = "factual"           # 사실 확인 (가격, 지표)
        ANALYTICAL = "analytical"     # 분석 요청
        COMPARATIVE = "comparative"   # 비교 분석
        PREDICTIVE = "predictive"     # 예측/전망
        STRATEGIC = "strategic"       # 전략/추천

    # 질문 유형 패턴
    TYPE_PATTERNS = {
        QuestionType.FACTUAL: [
            r'(얼마|몇|언제|누가|어디)',
            r'현재\s*(가격|주가)',
            r'(PER|PBR|ROE|시가총액)',
        ],
        QuestionType.COMPARATIVE: [
            r'비교',
            r'(보다|대비|vs)',
            r'차이',
            r'더\s*(좋|나은|높|낮)',
        ],
        QuestionType.PREDICTIVE: [
            r'(전망|예측|예상)',
            r'(오를|내릴|상승|하락)\s*(까|까요)',
            r'앞으로',
            r'향후',
        ],
        QuestionType.STRATEGIC: [
            r'(투자|매수|매도)\s*(할|해도|하면)',
            r'전략',
            r'추천',
            r'포트폴리오',
        ],
    }

    def __init__(self):
        self.complexity_classifier = ComplexityClassifier()
        self._type_patterns = {
            t: [re.compile(p, re.IGNORECASE) for p in patterns]
            for t, patterns in self.TYPE_PATTERNS.items()
        }

    def analyze(
        self,
        question: str,
        entities_count: int = 0,
        context_tokens: int = 0
    ) -> Dict[str, Any]:
        """
        질문 종합 분석

        Returns:
            {
                'complexity': QuestionComplexity,
                'question_type': QuestionType,
                'model_config': ModelConfig,
                'analysis_depth': str,  # 'shallow', 'medium', 'deep'
            }
        """
        # 복잡도 분류
        complexity_result = self.complexity_classifier.classify_and_configure(
            question, entities_count, context_tokens
        )

        # 질문 유형 분류
        question_type = self._classify_type(question)

        # 분석 깊이 결정
        analysis_depth = self._determine_depth(
            complexity_result['complexity'],
            question_type
        )

        return {
            **complexity_result,
            'question_type': question_type,
            'analysis_depth': analysis_depth,
        }

    def _classify_type(self, question: str) -> 'QuestionType':
        """질문 유형 분류"""
        for q_type, patterns in self._type_patterns.items():
            for pattern in patterns:
                if pattern.search(question):
                    return q_type

        return self.QuestionType.ANALYTICAL  # 기본값

    def _determine_depth(
        self,
        complexity: QuestionComplexity,
        question_type: 'QuestionType'
    ) -> str:
        """분석 깊이 결정"""
        if complexity == QuestionComplexity.SIMPLE:
            return 'shallow'

        if question_type in [self.QuestionType.COMPARATIVE, self.QuestionType.STRATEGIC]:
            return 'deep'

        if complexity == QuestionComplexity.COMPLEX:
            return 'deep'

        return 'medium'


# 싱글톤 인스턴스
_classifier_instance: Optional[ComplexityClassifier] = None


def get_complexity_classifier(provider: str = 'gemini') -> ComplexityClassifier:
    """ComplexityClassifier 싱글톤 반환"""
    global _classifier_instance
    if _classifier_instance is None or _classifier_instance.provider != provider:
        _classifier_instance = ComplexityClassifier(provider)
    return _classifier_instance
