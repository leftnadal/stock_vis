"""
LLMServiceLite - Gemini 2.5 Flash 기반 경량 LLM 서비스

스트리밍 응답, 재시도 로직, 에러 핸들링을 포함한 Gemini API 래퍼입니다.
"""

import re
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List, Tuple
from datetime import date

from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)


class LLMServiceLite:
    """
    Gemini 2.5 Flash 기반 LLM 서비스

    Features:
    - 스트리밍 응답 (generate_stream)
    - 지수 백오프 재시도
    - 투자 분석 특화 시스템 프롬프트
    - 토큰 사용량 추적
    - 복잡도 기반 설정 지원 (Phase 3)
    """

    MODEL = "gemini-2.5-flash"
    MAX_TOKENS = 2000
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # 지수 백오프 (초)

    # 복잡도별 기본 설정
    COMPLEXITY_CONFIGS = {
        'simple': {'max_tokens': 800, 'temperature': 0.5},
        'moderate': {'max_tokens': 1500, 'temperature': 0.7},
        'complex': {'max_tokens': 2500, 'temperature': 0.7},
    }

    # 면책 조항 (필수)
    DISCLAIMER = """
⚠️ 투자 유의사항
본 분석은 정보 제공 목적이며 투자 권유가 아닙니다.
투자 결정에 따른 책임은 투자자 본인에게 있습니다.
모든 투자에는 위험이 따르며, 원금 손실 가능성이 있습니다.
"""

    def __init__(self):
        """Gemini API 클라이언트 초기화"""
        api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None)

        if not api_key:
            raise ValueError(
                "GOOGLE_AI_API_KEY 또는 GEMINI_API_KEY가 설정되지 않았습니다. "
                "환경 변수를 확인하세요."
            )

        self.client = genai.Client(api_key=api_key)

    def get_system_prompt(self) -> str:
        """
        투자 분석 AI 시스템 프롬프트

        핵심 규칙:
        - 모든 날짜 명시
        - 면책 조항 포함
        - <suggestions> 태그로 추천 종목 제안
        """
        today = date.today().strftime('%Y년 %m월 %d일')

        return f"""당신은 전문 투자 분석 AI입니다.

## 역할
사용자가 제공한 데이터 바구니를 기반으로 투자 인사이트를 제공합니다.

## 핵심 규칙

1. **날짜 명시**: 모든 수치와 분석에 기준일을 명시하세요.
   - 예시: "2024년 3월 기준 매출은..."
   - 오늘 날짜: {today}

2. **면책 조항**: 모든 응답 끝에 다음 면책 조항을 포함하세요.
{self.DISCLAIMER}

3. **추천 종목 제안**: 분석 중 관련 종목을 발견하면 <suggestions> 태그로 제안하세요.
   ```
   <suggestions>
   [
     {{"symbol": "TSM", "reason": "AAPL의 주요 반도체 공급사"}},
     {{"symbol": "QCOM", "reason": "5G 칩셋 경쟁사"}}
   ]
   </suggestions>
   ```

4. **분석 스타일**:
   - 명확하고 구조화된 답변
   - 수치 기반 근거 제시
   - 리스크와 기회 모두 언급
   - 전문 용어는 쉽게 설명

5. **데이터 상황별 대응**:
   - 데이터가 있는 경우: 제공된 데이터 기반으로만 분석
   - 데이터가 없는 경우: 일반적인 투자 원칙에서 간략히 답변 (1-2문단)
   - 데이터가 없을 때 관련 종목을 바구니에 추가하도록 제안

6. **바구니 추가 제안 형식**:
   사용자가 특정 종목에 대해 질문했는데 바구니에 해당 데이터가 없으면,
   응답 끝에 다음 형식으로 추가 제안:

   ```
   <basket-action>
   {{"symbol": "AAPL", "name": "Apple Inc.", "recommended": ["overview", "price"], "available": ["overview", "price", "financial_summary", "financial_full", "indicator", "news"]}}
   </basket-action>
   ```

7. **제한사항**:
   - 제공된 데이터 외 추측 금지
   - 확실하지 않은 경우 명시
   - 단기 투자 조언 금지

현재 날짜: {today}
"""

    async def generate_stream(
        self,
        context: str,
        question: str,
        max_retries: Optional[int] = None,
        complexity: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        스트리밍 응답 생성

        Args:
            context: 데이터 바구니 컨텍스트
            question: 사용자 질문
            max_retries: 최대 재시도 횟수 (기본값: self.MAX_RETRIES)
            complexity: 질문 복잡도 ('simple', 'moderate', 'complex')

        Yields:
            dict: 이벤트 딕셔너리
                - {'type': 'delta', 'content': str}  # 텍스트 청크
                - {'type': 'final', 'input_tokens': int, 'output_tokens': int}  # 완료
                - {'type': 'error', 'message': str}  # 에러
        """
        retries = max_retries if max_retries is not None else self.MAX_RETRIES

        # 복잡도 기반 설정 적용
        complexity_config = self.COMPLEXITY_CONFIGS.get(
            complexity or 'moderate',
            self.COMPLEXITY_CONFIGS['moderate']
        )
        max_tokens = complexity_config['max_tokens']
        temperature = complexity_config['temperature']

        logger.info(
            f"LLM config: complexity={complexity}, "
            f"max_tokens={max_tokens}, temperature={temperature}"
        )

        # Gemini용 설정
        config = types.GenerateContentConfig(
            system_instruction=self.get_system_prompt(),
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        for attempt in range(retries):
            try:
                # 사용자 메시지 구성
                user_content = f"{context}\n\n질문: {question}"

                # 비동기 스트리밍
                total_input_tokens = 0
                total_output_tokens = 0

                stream = await self.client.aio.models.generate_content_stream(
                    model=self.MODEL,
                    contents=user_content,
                    config=config,
                )

                async for chunk in stream:
                    # 텍스트 청크 스트리밍
                    if chunk.text:
                        yield {
                            'type': 'delta',
                            'content': chunk.text
                        }

                    # 토큰 사용량 추적 (마지막 청크에서 제공)
                    if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                        if hasattr(chunk.usage_metadata, 'prompt_token_count'):
                            total_input_tokens = chunk.usage_metadata.prompt_token_count or 0
                        if hasattr(chunk.usage_metadata, 'candidates_token_count'):
                            total_output_tokens = chunk.usage_metadata.candidates_token_count or 0

                # 최종 메시지 (토큰 사용량 포함)
                yield {
                    'type': 'final',
                    'input_tokens': total_input_tokens,
                    'output_tokens': total_output_tokens
                }

                # 성공 시 루프 종료
                return

            except Exception as e:
                error_str = str(e).lower()

                # Rate limit 에러 체크
                if 'rate' in error_str or 'quota' in error_str or '429' in error_str:
                    if attempt < retries - 1:
                        delay = self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS) - 1)]
                        logger.warning(
                            f"Rate limit exceeded. Retrying in {delay}s... "
                            f"(Attempt {attempt + 1}/{retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded after {retries} retries")
                        yield {
                            'type': 'error',
                            'message': 'API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.'
                        }
                        return

                # 기타 에러
                logger.exception(f"Gemini API error: {e}")
                yield {
                    'type': 'error',
                    'message': f'LLM API 오류가 발생했습니다: {str(e)}'
                }
                return


class ResponseParser:
    """
    LLM 응답 파싱 유틸리티

    <suggestions> 태그 추출 및 구조화
    """

    # <suggestions> 태그 패턴
    SUGGESTIONS_PATTERN = re.compile(
        r'<suggestions>\s*(\[.*?\])\s*</suggestions>',
        re.DOTALL
    )

    @staticmethod
    def parse_suggestions(content: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        응답에서 <suggestions> 태그 파싱

        Args:
            content: LLM 응답 전체 텍스트

        Returns:
            tuple: (cleaned_content, suggestions)
                - cleaned_content: <suggestions> 태그가 제거된 본문
                - suggestions: [{'symbol': 'TSM', 'reason': '...'}]
        """
        match = ResponseParser.SUGGESTIONS_PATTERN.search(content)

        if not match:
            # suggestions 없음
            return content, []

        # JSON 파싱 시도
        try:
            import json
            suggestions_json = match.group(1)
            suggestions = json.loads(suggestions_json)

            # 태그 제거
            cleaned_content = ResponseParser.SUGGESTIONS_PATTERN.sub('', content).strip()

            # 유효성 검증
            if not isinstance(suggestions, list):
                logger.warning("Suggestions is not a list, ignoring")
                return content, []

            # 각 항목 검증
            valid_suggestions = []
            for item in suggestions:
                if isinstance(item, dict) and 'symbol' in item and 'reason' in item:
                    valid_suggestions.append({
                        'symbol': item['symbol'].upper(),
                        'reason': item['reason']
                    })
                else:
                    logger.warning(f"Invalid suggestion item: {item}")

            return cleaned_content, valid_suggestions

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse suggestions JSON: {e}")
            return content, []

        except Exception as e:
            logger.exception(f"Unexpected error parsing suggestions: {e}")
            return content, []

    @staticmethod
    def parse_basket_actions(content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        응답에서 <basket-action> 태그 파싱

        Args:
            content: LLM 응답 전체 텍스트

        Returns:
            tuple: (cleaned_content, basket_actions)
                - cleaned_content: <basket-action> 태그가 제거된 본문
                - basket_actions: [{
                    'symbol': 'AAPL',
                    'name': 'Apple Inc.',
                    'recommended': ['overview', 'price'],
                    'available': ['overview', 'price', 'financial_summary', ...]
                  }]
        """
        import json

        pattern = r'<basket-action>\s*(.*?)\s*</basket-action>'
        actions = []

        for match in re.finditer(pattern, content, re.DOTALL):
            try:
                action = json.loads(match.group(1))

                # 필수 필드 검증
                if all(key in action for key in ['symbol', 'name', 'recommended', 'available']):
                    # symbol 대문자 변환
                    action['symbol'] = action['symbol'].upper()
                    actions.append(action)
                else:
                    logger.warning(f"Invalid basket-action format: {action}")

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse basket-action JSON: {e}")

        # 태그 제거
        cleaned = re.sub(pattern, '', content, flags=re.DOTALL).strip()

        return cleaned, actions

    @staticmethod
    def validate_suggestion(suggestion: Dict[str, Any]) -> bool:
        """
        Suggestion 항목 유효성 검증

        Args:
            suggestion: {'symbol': str, 'reason': str}

        Returns:
            bool: 유효하면 True
        """
        if not isinstance(suggestion, dict):
            return False

        if 'symbol' not in suggestion or 'reason' not in suggestion:
            return False

        if not suggestion['symbol'] or not suggestion['reason']:
            return False

        return True
