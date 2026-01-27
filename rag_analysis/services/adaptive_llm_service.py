"""
Adaptive LLM Service - 적응형 LLM 서비스

질문 복잡도에 따라 최적의 모델을 선택하여 비용을 최적화합니다.

Features:
    - 복잡도 기반 모델 자동 선택
    - 토큰 예산 관리
    - 비용 추적 통합
    - 스트리밍 지원
"""

import logging
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime
import time

from django.conf import settings

from .complexity_classifier import (
    ComplexityClassifier,
    QuestionComplexity,
    get_complexity_classifier
)
from .cost_tracker import get_cost_tracker

logger = logging.getLogger(__name__)


class AdaptiveLLMService:
    """
    적응형 LLM 서비스

    질문 복잡도를 분석하여 최적의 모델과 설정으로 응답을 생성합니다.
    """

    # 시스템 프롬프트 템플릿
    SYSTEM_PROMPT_TEMPLATE = """당신은 Stock-Vis AI 투자 분석 어시스턴트입니다.

## 기본 원칙
1. 모든 분석은 **{snapshot_date} 기준** 데이터입니다.
2. 투자 결정에 대한 책임은 투자자 본인에게 있습니다.
3. 객관적인 데이터 기반 분석을 제공합니다.

## 응답 형식
- 핵심 내용을 먼저 제시
- 구체적인 수치와 근거 포함
- 간결하고 명확한 문장 사용

{depth_instruction}

## 응답 마무리
응답 끝에 다음 형식으로 탐색 제안을 제공하세요:
<suggestions>
{{"symbol": "종목코드", "reason": "탐색 이유"}}
</suggestions>

--- 면책 조항 ---
본 분석은 참고용이며, 투자 조언이 아닙니다. 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다."""

    # 분석 깊이별 지침
    DEPTH_INSTRUCTIONS = {
        'shallow': "간단하고 핵심적인 정보만 제공하세요. 1-2문단 이내로 답변하세요.",
        'medium': "주요 분석 포인트를 포함하여 답변하세요. 필요시 수치와 근거를 제시하세요.",
        'deep': "심층적인 분석을 제공하세요. 다각도로 분석하고, 리스크 요인과 기회 요인을 모두 검토하세요.",
    }

    def __init__(
        self,
        provider: str = 'gemini',
        enable_cost_tracking: bool = True
    ):
        """
        Args:
            provider: 'gemini' 또는 'claude'
            enable_cost_tracking: 비용 추적 활성화 여부
        """
        self.provider = provider
        self.enable_cost_tracking = enable_cost_tracking
        self.classifier = get_complexity_classifier(provider)
        self.cost_tracker = get_cost_tracker() if enable_cost_tracking else None

        # LLM 클라이언트 초기화
        self._init_client()

    def _init_client(self):
        """LLM 클라이언트 초기화"""
        if self.provider == 'gemini':
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._genai = genai
                logger.info("Gemini client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self._genai = None
        else:
            try:
                from anthropic import AsyncAnthropic
                self._anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                logger.info("Anthropic client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                self._anthropic = None

    async def generate_stream(
        self,
        context: str,
        question: str,
        entities_count: int = 0,
        user_id: Optional[int] = None,
        session_id: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        적응형 스트리밍 응답 생성

        Args:
            context: 분석 컨텍스트
            question: 사용자 질문
            entities_count: 엔티티 수
            user_id: 사용자 ID (비용 추적용)
            session_id: 세션 ID (비용 추적용)

        Yields:
            {'type': 'config', 'data': {...}}  # 선택된 설정
            {'type': 'delta', 'content': str}  # 스트리밍 청크
            {'type': 'final', 'input_tokens': int, 'output_tokens': int, ...}
            {'type': 'error', 'message': str}
        """
        start_time = time.time()

        # 1. 복잡도 분석 및 모델 설정
        context_tokens = len(context.split())  # 대략적 추정
        config = self.classifier.classify_and_configure(
            question, entities_count, context_tokens
        )

        yield {
            'type': 'config',
            'data': {
                'complexity': config['complexity'].value,
                'complexity_score': round(config['complexity_score'], 2),
                'model': config['model'],
                'max_tokens': config['max_tokens'],
            }
        }

        # 2. 시스템 프롬프트 생성
        depth = self._get_depth_from_complexity(config['complexity'])
        system_prompt = self._build_system_prompt(depth)

        # 3. LLM 호출 (스트리밍)
        try:
            if self.provider == 'gemini':
                async for chunk in self._generate_gemini_stream(
                    system_prompt, context, question, config
                ):
                    yield chunk
            else:
                async for chunk in self._generate_claude_stream(
                    system_prompt, context, question, config
                ):
                    yield chunk

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            yield {'type': 'error', 'message': str(e)}

        # 4. 비용 추적
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"Adaptive LLM: complexity={config['complexity'].value}, "
            f"model={config['model']}, latency={latency_ms}ms"
        )

    async def _generate_gemini_stream(
        self,
        system_prompt: str,
        context: str,
        question: str,
        config: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Gemini 스트리밍 생성"""
        if not self._genai:
            yield {'type': 'error', 'message': 'Gemini client not available'}
            return

        try:
            model = self._genai.GenerativeModel(
                model_name=config['model'],
                system_instruction=system_prompt,
                generation_config={
                    'max_output_tokens': config['max_tokens'],
                    'temperature': config['temperature'],
                }
            )

            # 프롬프트 구성
            prompt = f"""## 컨텍스트
{context}

## 질문
{question}

## 분석"""

            # 스트리밍 생성
            response = await model.generate_content_async(
                prompt,
                stream=True
            )

            full_response = ""
            input_tokens = 0
            output_tokens = 0

            async for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    yield {'type': 'delta', 'content': chunk.text}

            # 토큰 사용량 (Gemini API에서 제공하는 경우)
            if hasattr(response, 'usage_metadata'):
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
            else:
                # 추정값 사용
                input_tokens = len((system_prompt + context + question).split()) * 1.3
                output_tokens = len(full_response.split()) * 1.3

            yield {
                'type': 'final',
                'content': full_response,
                'input_tokens': int(input_tokens),
                'output_tokens': int(output_tokens),
                'model': config['model'],
                'complexity': config['complexity'].value,
            }

        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            yield {'type': 'error', 'message': str(e)}

    async def _generate_claude_stream(
        self,
        system_prompt: str,
        context: str,
        question: str,
        config: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Claude 스트리밍 생성"""
        if not self._anthropic:
            yield {'type': 'error', 'message': 'Anthropic client not available'}
            return

        try:
            # 프롬프트 구성
            user_message = f"""## 컨텍스트
{context}

## 질문
{question}

## 분석"""

            async with self._anthropic.messages.stream(
                model=config['model'],
                max_tokens=config['max_tokens'],
                temperature=config['temperature'],
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            ) as stream:
                full_response = ""

                async for text in stream.text_stream:
                    full_response += text
                    yield {'type': 'delta', 'content': text}

                # 최종 메시지
                final_message = await stream.get_final_message()

                yield {
                    'type': 'final',
                    'content': full_response,
                    'input_tokens': final_message.usage.input_tokens,
                    'output_tokens': final_message.usage.output_tokens,
                    'model': config['model'],
                    'complexity': config['complexity'].value,
                }

        except Exception as e:
            logger.error(f"Claude generation error: {e}")
            yield {'type': 'error', 'message': str(e)}

    def _build_system_prompt(self, depth: str) -> str:
        """시스템 프롬프트 생성"""
        depth_instruction = self.DEPTH_INSTRUCTIONS.get(depth, self.DEPTH_INSTRUCTIONS['medium'])

        return self.SYSTEM_PROMPT_TEMPLATE.format(
            snapshot_date=datetime.now().strftime('%Y-%m-%d'),
            depth_instruction=depth_instruction
        )

    def _get_depth_from_complexity(self, complexity: QuestionComplexity) -> str:
        """복잡도에서 분석 깊이 결정"""
        mapping = {
            QuestionComplexity.SIMPLE: 'shallow',
            QuestionComplexity.MODERATE: 'medium',
            QuestionComplexity.COMPLEX: 'deep',
        }
        return mapping.get(complexity, 'medium')

    async def estimate_cost(
        self,
        question: str,
        context_length: int,
        entities_count: int = 0
    ) -> Dict[str, Any]:
        """
        예상 비용 추정

        Returns:
            {
                'complexity': str,
                'model': str,
                'estimated_input_tokens': int,
                'estimated_output_tokens': int,
                'estimated_cost_usd': float
            }
        """
        config = self.classifier.classify_and_configure(
            question, entities_count, context_length
        )

        # 토큰 추정
        estimated_input = context_length + len(question.split()) * 1.3 + 200  # 시스템 프롬프트
        estimated_output = config['max_tokens'] * 0.6  # 평균적으로 max의 60% 사용

        # 비용 추정
        cost_per_1k = config['estimated_cost_per_1k']
        estimated_cost = (
            (estimated_input / 1000) * cost_per_1k * 0.5 +  # 입력은 절반 가격
            (estimated_output / 1000) * cost_per_1k
        )

        return {
            'complexity': config['complexity'].value,
            'model': config['model'],
            'estimated_input_tokens': int(estimated_input),
            'estimated_output_tokens': int(estimated_output),
            'estimated_cost_usd': round(estimated_cost, 6)
        }


# 싱글톤 인스턴스
_adaptive_llm_instance: Optional[AdaptiveLLMService] = None


def get_adaptive_llm_service(
    provider: str = 'gemini',
    enable_cost_tracking: bool = True
) -> AdaptiveLLMService:
    """AdaptiveLLMService 싱글톤 반환"""
    global _adaptive_llm_instance
    if _adaptive_llm_instance is None:
        _adaptive_llm_instance = AdaptiveLLMService(provider, enable_cost_tracking)
    return _adaptive_llm_instance
