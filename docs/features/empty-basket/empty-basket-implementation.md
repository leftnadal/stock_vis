# 빈 바스켓 대응 - 구현 예시 코드

이 문서는 **empty-basket-guidelines.md**의 실제 구현 코드를 제시합니다.

---

## 1. Django Backend 구현

### 1.1 프롬프트 시스템 (rag_analysis/prompts/system_prompts.py)

```python
# rag_analysis/prompts/system_prompts.py

"""
빈 바스켓 상황별 시스템 프롬프트
"""

SYSTEM_PROMPT_BASE = """
당신은 Stock-Vis의 AI 투자 분석 비서입니다.

## 당신의 역할
- 투자 초보자를 위한 쉬운 설명
- 객관적이고 데이터 기반의 정보 제공
- 투자 개념을 이해하기 쉽게 전달

## 중요한 제약사항
1. 절대 특정 종목 매매 권유 금지
   ❌ "A사를 사세요" ❌ "지금이 매수 타이밍입니다"
   ✅ "A사의 PER은 이정도입니다" ✅ "이런 지표를 봅니다"

2. 데이터 없으면 분석 불가능
   - 데이터가 없으면 그 사실을 명시
   - 없는 데이터로 분석하는 척 하지 않기
   - 대신 개념 설명이나 학습 가이드 제공

3. 모든 수치는 기준일 명시
   ❌ "Apple의 가격은 $200입니다"
   ✅ "Apple의 종가는 $200입니다 (2025-12-11 기준)"

4. 법적 안전성
   - 투자 결정은 사용자의 책임임을 명시
   - 모든 분석 마지막에 면책조항 포함
   - 긴급성 조성 금지 ("지금 바로 사야 합니다")

## 응답 스타일
- 친근하고 따뜻한 톤
- 초보자도 이해할 수 있는 언어
- 다음 단계를 명확히 제시
"""

SYSTEM_PROMPT_EMPTY_BASKET = """
{SYSTEM_PROMPT_BASE}

## 특수 상황: 바구니가 비어있습니다

사용자가 아직 분석할 데이터를 추가하지 않았습니다.
이는 첫 사용자이거나, 새로운 분석을 시작하는 것일 수 있습니다.

### 당신의 역할
1. **상황을 인정**
   - "분석할 데이터가 없네요" 명확히
   - 부정적 표현 피하기 ("불가능합니다" 대신 "지금은 이 정도만")

2. **가치를 제시**
   - 데이터 없이도 할 수 있는 것 설명
   - Stock-Vis의 가치를 구체적으로 보여주기
   - 3-4가지 활용 사례 제시

3. **명확한 다음 단계**
   - "종목을 추가하세요" (막연함)
   - "메인 화면의 '종목 검색'에서 Apple 입력 → '바구니에 추가' → 분석 시작"
   - 각 단계에 버튼명, 위치 명시

4. **친근한 톤**
   - "함께 시작해봅시다"
   - "좋은 시작점입니다"
   - 초보자를 환영하는 느낌

### 절대 금지
❌ "아무 데이터가 없어서 답변할 수 없습니다" (너무 딱딱함)
❌ "Apple(AAPL)의 가격은 현재 $180이고 PER은 28입니다" (데이터 없는데 분석)
❌ "지금 시장이 불안정해서 투자하지 않기를 권합니다" (투자 권유)
❌ "이것도 모르는 사람은 투자하면 안 됩니다" (계몽적 톤)

### 바구니가 비어있지만 할 수 있는 것
✅ 투자 개념 설명 ("PER이 뭐예요?")
✅ 일반적 투자 전략 설명 ("분산투자는 왜 중요한가요?")
✅ 시장 지식 공유 ("미국 주식은 어떻게 사나요?")
✅ 학습 가이드 ("주식 초보자는 뭐부터 시작할까요?")
"""

SYSTEM_PROMPT_PARTIAL_DATA = """
{SYSTEM_PROMPT_BASE}

## 특수 상황: 데이터가 부분적으로 부족합니다

사용자가 일부 데이터는 추가했지만, 질문에 완전히 답하기엔 부족합니다.
예: "A사의 경쟁사 분석" 요청인데 A사 데이터만 있음

### 당신의 역할
1. **있는 데이터로 분석**
   - 확보한 정보 범위 내에서 최대한 분석
   - "A사의 데이터로는 이렇게 분석할 수 있습니다"

2. **부족함 명시**
   - "경쟁사 정보가 없어서 완전한 비교분석은 어렵습니다"
   - 무엇이 부족한지 구체적으로
   - "경쟁사 3-4개의 데이터가 있으면 더 정확합니다"

3. **필요한 것 제시**
   - "이렇게 추가하면 됩니다"
   - 구체적인 데이터명 (예: "B사, C사 재무제표")
   - 추가 후 어떻게 달라질지 설명

4. **대안 제공**
   - "지금 할 수 있는 분석"
   - "다음 단계로 할 수 있는 분석"

### 절대 금지
❌ 없는 데이터 가정하고 분석 ("A사의 예상 PER은...")
❌ 부정확한 추정치 제시
❌ "더 많은 데이터가 필요합니다" (그 다음이 없음)
"""

SYSTEM_PROMPT_GENERAL_EDUCATION = """
{SYSTEM_PROMPT_BASE}

## 특수 상황: 일반 투자 개념 질문

사용자가 투자 개념을 배우고 싶어합니다.
데이터는 불필요합니다.
예: "PER이 뭐예요?", "분산투자는 왜 중요한가요?"

### 당신의 역할
1. **3단계 설명 구조**
   [초급] 비유를 통한 쉬운 설명 (1-2문장)
   [중급] 구체적 계산법, 활용법 (3-4문장)
   [고급] 이론, 한계점, 고급 팁 (2-3문장)

2. **구체적 실제 사례**
   - "예를 들어 Apple과 Microsoft를..."
   - 수치 예시 (현재 정확하지 않으면 "예시로")
   - 단순 비교 제시

3. **실전 연결**
   - "Stock-Vis에서 이걸 어떻게 활용하나요?"
   - "데이터를 추가하면 직접 계산해볼 수 있습니다"
   - 학습 → 실습 연결

4. **흥미와 동기 유발**
   - "투자의 핵심을 이해하는 거네요"
   - "이 개념을 알면 포트폴리오 관리가 훨씬 쉬워집니다"
   - 배운 개념의 가치 강조

### 절대 금지
❌ "PER = Price-to-Earnings Ratio입니다" (너무 기술적)
❌ "PER이 낮으면 사세요" (투자 권유)
❌ "그건 너무 복잡해서..." (포기)
❌ 이미 알려진 내용 반복 (상대방을 무시한 듯한 느낌)
"""
```

### 1.2 상황 판별 함수 (rag_analysis/services/context_detector.py)

```python
# rag_analysis/services/context_detector.py

"""
사용자 질문과 바구니 상태를 분석하여
빈 바스켓 상황 타입을 판별합니다.
"""

from enum import Enum
from typing import Optional
import re


class EmptyBasketReason(Enum):
    """빈 바스켓 상황 분류"""
    COMPLETELY_EMPTY = "completely_empty"
    PARTIAL_QUESTION = "partial_question"
    GENERAL_EDUCATION = "general_education"
    NORMAL = "normal"  # 바구니가 있고 분석 가능


class ContextDetector:
    """사용자 질문 및 데이터 상태 분석"""

    # 특정 종목을 지칭하는 키워드
    STOCK_KEYWORDS = {
        "how": ["is", "good", "should", "worth", "buy", "sell"],
        "ko": ["어떤가요", "괜찮은가요", "사야할까요", "팔까요", "좋은가요"],
    }

    # 일반 개념을 묻는 키워드
    EDUCATION_KEYWORDS = {
        "what": ["is", "mean", "why", "how", "important"],
        "ko": ["뭐예요", "뭐예", "무엇인가요", "왜", "어떻게"],
    }

    @staticmethod
    def detect_empty_reason(
        question: str,
        has_basket_items: bool,
        item_count: int = 0
    ) -> EmptyBasketReason:
        """
        사용자 질문과 바구니 상태를 분석하여 상황 판별

        Args:
            question: 사용자의 질문
            has_basket_items: 바구니에 아이템이 있는지 여부
            item_count: 바구니 아이템 개수

        Returns:
            EmptyBasketReason 열거형
        """

        # 바구니가 있으면 일반 분석
        if has_basket_items and item_count > 0:
            return EmptyBasketReason.NORMAL

        # 바구니가 비어있으면, 질문 유형 분석
        if not question or question.strip() == "":
            return EmptyBasketReason.COMPLETELY_EMPTY

        # 특정 종목을 묻는 질문?
        if ContextDetector._is_specific_stock_question(question):
            return EmptyBasketReason.PARTIAL_QUESTION

        # 일반 개념을 묻는 질문?
        if ContextDetector._is_general_education_question(question):
            return EmptyBasketReason.GENERAL_EDUCATION

        # 기본값: 부분 질문
        return EmptyBasketReason.PARTIAL_QUESTION

    @staticmethod
    def _is_specific_stock_question(question: str) -> bool:
        """특정 종목을 지칭하는 질문 판별"""

        # 회사명/티커 포함?
        company_pattern = r"\b(?:Apple|AAPL|Microsoft|MSFT|Tesla|TSLA|Google|Alphabet|GOOGL|Amazon|AMZN|Meta|META|Nvidia|NVDA|[A-Z]{1,5})\b"
        if re.search(company_pattern, question, re.IGNORECASE):
            return True

        # 특정 종목 질문 패턴?
        specific_patterns = [
            r"이\s*회사",  # "이 회사는"
            r"이\s*종목",  # "이 종목은"
            r"([가-힣]+)\s*[어/은가]",  # "A는/어/가"
            r"should\s+[A-Z]{1,4}\b",  # "should AAPL"
            r"is\s+[A-Z]{1,4}\b",  # "is AAPL"
        ]

        for pattern in specific_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def _is_general_education_question(question: str) -> bool:
        """일반 투자 개념을 묻는 질문 판별"""

        # 개념 설명 요청 패턴
        education_patterns = [
            r"(뭐예|뭐|무엇|정의|의미|개념)",  # 정의 요청
            r"(왜.*중요|중요한.*이유)",  # 중요성 질문
            r"(어떻게.*활용|어떻게.*쓰)",  # 활용법 질문
            r"(입문|초보|처음|배우)",  # 학습 요청
            r"(what\s+is|what\s+does|why)",  # 영문 패턴
            r"(PER|PBR|ROE|ROIC|EPS|WACC)",  # 금융 지표명
        ]

        for pattern in education_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def extract_mentioned_stocks(question: str) -> list[str]:
        """질문에 언급된 종목 추출"""

        pattern = r"\b(?:Apple|AAPL|Microsoft|MSFT|Tesla|TSLA|Google|Alphabet|GOOGL|Amazon|AMZN|Meta|META|Nvidia|NVDA|[A-Z]{1,5})\b"
        matches = re.findall(pattern, question, re.IGNORECASE)
        return list(set(matches))

    @staticmethod
    def extract_financial_metrics(question: str) -> list[str]:
        """질문에 언급된 금융 지표 추출"""

        metrics = {
            "PER": ["PER", "PE", "price.*earnings", "배수"],
            "PBR": ["PBR", "가격", "자산"],
            "ROE": ["ROE", "자기자본", "수익률"],
            "EPS": ["EPS", "주당순이익"],
            "배당": ["배당", "dividend", "yield"],
        }

        found = []
        for metric_name, patterns in metrics.items():
            for pattern in patterns:
                if re.search(pattern, question, re.IGNORECASE):
                    found.append(metric_name)
                    break

        return found
```

### 1.3 프롬프트 선택 로직 (rag_analysis/services/prompt_manager.py)

```python
# rag_analysis/services/prompt_manager.py

"""
사용자의 상황에 따라 적절한 시스템 프롬프트를 선택합니다.
"""

from django.conf import settings
from .context_detector import ContextDetector, EmptyBasketReason
from .prompts.system_prompts import (
    SYSTEM_PROMPT_BASE,
    SYSTEM_PROMPT_EMPTY_BASKET,
    SYSTEM_PROMPT_PARTIAL_DATA,
    SYSTEM_PROMPT_GENERAL_EDUCATION,
)


class PromptManager:
    """
    상황별 시스템 프롬프트 관리
    """

    # 면책조항 (모든 상황에 추가)
    DISCLAIMER = """
※ 중요 공지사항
본 분석은 정보 제공 목적이며, 투자 조언이 아닙니다.
투자 결정은 충분한 조사와 전문가 상담 후 스스로 판단하세요.
과거 성과가 미래 수익을 보장하지 않습니다.
    """

    @staticmethod
    def get_system_prompt(
        question: str,
        has_basket_items: bool,
        item_count: int = 0,
        include_disclaimer: bool = True
    ) -> str:
        """
        사용자 상황에 맞는 시스템 프롬프트 반환

        Args:
            question: 사용자의 질문
            has_basket_items: 바구니에 아이템이 있는지
            item_count: 바구니 아이템 개수
            include_disclaimer: 면책조항 포함 여부

        Returns:
            최종 시스템 프롬프트 (문자열)
        """

        # 상황 판별
        reason = ContextDetector.detect_empty_reason(
            question,
            has_basket_items,
            item_count
        )

        # 상황별 프롬프트 선택
        if reason == EmptyBasketReason.NORMAL:
            # 바구니가 있고 분석 가능
            prompt = SYSTEM_PROMPT_BASE
        elif reason == EmptyBasketReason.COMPLETELY_EMPTY:
            # 바구니가 완전히 비어있음
            prompt = SYSTEM_PROMPT_EMPTY_BASKET
        elif reason == EmptyBasketReason.PARTIAL_QUESTION:
            # 데이터 부분 부족 + 특정 질문
            prompt = SYSTEM_PROMPT_PARTIAL_DATA
        elif reason == EmptyBasketReason.GENERAL_EDUCATION:
            # 일반 개념 질문
            prompt = SYSTEM_PROMPT_GENERAL_EDUCATION
        else:
            prompt = SYSTEM_PROMPT_BASE

        # 면책조항 추가
        if include_disclaimer:
            prompt += "\n\n" + PromptManager.DISCLAIMER

        return prompt

    @staticmethod
    def get_guidance_data(
        reason: EmptyBasketReason,
        question: str = ""
    ) -> dict:
        """
        UI에 표시할 가이드 데이터 반환

        Args:
            reason: 빈 바스켓 이유
            question: 사용자의 질문 (맥락용)

        Returns:
            {
                'type': 'completely_empty' | 'partial_question' | 'general_education',
                'title': 화면에 표시할 제목,
                'message': 가이드 메시지,
                'steps': 단계별 가이드,
                'example': 예시 시나리오
            }
        """

        guidance_map = {
            EmptyBasketReason.COMPLETELY_EMPTY: {
                'type': 'completely_empty',
                'title': '분석을 시작해보겠습니다!',
                'message': '아직 바구니가 비어있네요. 하지만 좋은 시작점입니다.',
                'steps': [
                    '관심 종목 선택 (Apple, Tesla 등)',
                    '바구니에 추가 (최소 1개, 최대 5개)',
                    '분석 시작 → AI가 종합 분석 제시'
                ],
                'examples': [
                    {
                        'scenario': '기술주 투자를 생각 중',
                        'action': 'Apple, NVIDIA, Microsoft 추가',
                        'benefit': 'AI가 경쟁 관계와 공급망 분석'
                    },
                    {
                        'scenario': '배당주를 찾고 있어요',
                        'action': 'Coca-Cola, P&G, Verizon 추가',
                        'benefit': 'AI가 배당 정책과 재무 안정성 비교'
                    }
                ]
            },

            EmptyBasketReason.PARTIAL_QUESTION: {
                'type': 'partial_question',
                'title': '좋은 질문입니다!',
                'message': '지금은 개념 설명만 가능합니다. 구체적 분석이 필요하다면 관련 종목을 추가하세요.',
                'steps': [
                    f'"{question}" 관련 종목 검색',
                    '종목 데이터를 바구니에 추가',
                    '분석 시작 → 구체적 답변 획득'
                ],
                'examples': [
                    {
                        'scenario': '"Apple의 경쟁력은?"',
                        'action': 'Apple 데이터 추가',
                        'benefit': 'AI가 경쟁사(Microsoft, Google) 비교 분석'
                    }
                ]
            },

            EmptyBasketReason.GENERAL_EDUCATION: {
                'type': 'general_education',
                'title': '좋은 질문입니다!',
                'message': '투자 개념을 학습하는 중이시네요. 아래 AI 분석을 통해 이해도를 높이고, 실제 종목을 추가해 직접 적용해보세요!',
                'steps': [
                    '아래 개념 설명 읽기',
                    '관심 종목 선택 및 바구니에 추가',
                    '배운 개념을 실제로 적용해보기'
                ],
                'examples': []
            }
        }

        return guidance_map.get(
            reason,
            guidance_map[EmptyBasketReason.COMPLETELY_EMPTY]
        )
```

### 1.4 파이프라인 통합 (rag_analysis/services/pipeline_lite.py)

```python
# rag_analysis/services/pipeline_lite.py (부분)

"""
v4.2-lite 분석 파이프라인 (빈 바스켓 대응 포함)
"""

from typing import AsyncIterator
import json
from .context_detector import ContextDetector, EmptyBasketReason
from .prompt_manager import PromptManager
from .llm_service_lite import LLMServiceLite
from .neo4j_service_lite import Neo4jServiceLite


class AnalysisPipelineLite:
    """v4.2-lite 분석 파이프라인"""

    def __init__(self):
        self.llm_service = LLMServiceLite()
        self.neo4j_service = Neo4jServiceLite()
        self.prompt_manager = PromptManager()

    async def analyze(
        self,
        session,  # AnalysisSession
        question: str
    ) -> AsyncIterator[dict]:
        """
        분석 파이프라인

        yields:
            {
                'phase': str,
                'data': any,
                'message': str (optional)
            }
        """

        basket = session.basket
        has_items = basket.items.exists()
        item_count = basket.items.count() if has_items else 0

        # ===== Step 0: 바구니 상태 및 질문 분석 =====
        reason = ContextDetector.detect_empty_reason(
            question,
            has_items,
            item_count
        )

        yield {
            'phase': 'context_detected',
            'reason': reason.value,
        }

        # ===== 바구니가 비어있는 경우 =====
        if reason != EmptyBasketReason.NORMAL:
            yield from await self._handle_empty_or_incomplete(
                reason,
                question,
                session
            )
            return

        # ===== 정상 분석 흐름 (기존 로직) =====
        yield from await self._handle_normal_analysis(question, session)

    async def _handle_empty_or_incomplete(
        self,
        reason: EmptyBasketReason,
        question: str,
        session
    ) -> AsyncIterator[dict]:
        """빈 바스켓 / 부분 데이터 처리"""

        yield {
            'phase': 'analyzing_empty',
            'message': '정보를 준비 중입니다...'
        }

        # 가이드 데이터 생성
        guidance = self.prompt_manager.get_guidance_data(reason, question)

        yield {
            'phase': 'guidance_ready',
            'guidance': guidance
        }

        # 시스템 프롬프트 선택
        system_prompt = self.prompt_manager.get_system_prompt(
            question,
            has_basket_items=False,
            include_disclaimer=True
        )

        # LLM 메시지 구성
        messages = [
            {
                'role': 'system',
                'content': system_prompt
            },
            {
                'role': 'user',
                'content': question if question else "Stock-Vis를 어떻게 사용하나요?"
            }
        ]

        # 스트리밍 응답
        yield {'phase': 'streaming_start'}

        full_response = ""
        async for chunk in self.llm_service.stream(messages, max_tokens=2048):
            full_response += chunk
            yield {
                'phase': 'streaming',
                'chunk': chunk
            }

        # 완료
        yield {
            'phase': 'complete',
            'data': {
                'analysis': full_response,
                'reason': reason.value,
                'guidance': guidance
            }
        }

        # 메시지 저장 (추적용)
        await self._save_empty_message(
            session,
            question,
            full_response,
            reason
        )

    async def _handle_normal_analysis(
        self,
        question: str,
        session
    ) -> AsyncIterator[dict]:
        """기존 분석 로직 (바구니가 있는 경우)"""

        # ... 기존 코드 ...
        pass

    async def _save_empty_message(
        self,
        session,
        question: str,
        response: str,
        reason: EmptyBasketReason
    ):
        """빈 바스켓 메시지 저장 (분석 추적용)"""

        from rag_analysis.models import AnalysisMessage

        AnalysisMessage.objects.create(
            session=session,
            role='user',
            content=question,
            empty_basket_reason=reason.value,
        )

        AnalysisMessage.objects.create(
            session=session,
            role='assistant',
            content=response,
            empty_basket_reason=reason.value,
        )
```

---

## 2. API 뷰 (Django REST Framework)

### 2.1 분석 스트리밍 엔드포인트

```python
# rag_analysis/views.py (부분)

"""
스트리밍 분석 API
SSE (Server-Sent Events)를 통해 실시간 응답
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
import json
import asyncio


class AnalysisStreamView(APIView):
    """
    POST /api/v1/rag/analysis/<session_id>/stream/

    Request body:
    {
        "message": "사용자의 질문 또는 분석 요청"
    }

    Response:
    Server-Sent Events 스트림
    각 이벤트 형식:
    {
        "phase": "context_detected" | "streaming" | "complete" | ...,
        "data": {...},
        "message": "..."
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        """분석 스트리밍 시작"""

        from rag_analysis.models import AnalysisSession
        from rag_analysis.services.pipeline_lite import AnalysisPipelineLite

        # 세션 가져오기
        session = get_object_or_404(
            AnalysisSession,
            id=session_id,
            user=request.user
        )

        question = request.data.get('message', '').strip()

        # 파이프라인 초기화
        pipeline = AnalysisPipelineLite()

        def event_stream():
            """이벤트 스트림 제너레이터"""

            async def async_analyze():
                """비동기 분석 실행"""
                async for event in pipeline.analyze(session, question):
                    yield event

            # 이벤트 스트림 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                async_gen = async_analyze()

                while True:
                    try:
                        event = loop.run_until_complete(
                            async_gen.__anext__()
                        )
                        # SSE 형식으로 전송
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                    except StopAsyncIteration:
                        break
                    except Exception as e:
                        yield f"data: {json.dumps({'phase': 'error', 'message': str(e)})}\n\n"
                        break

            finally:
                loop.close()

        # StreamingHttpResponse 반환
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream',
            charset='utf-8'
        )

        # CORS 헤더
        response['Cache-Control'] = 'no-cache'
        response['Connection'] = 'keep-alive'
        response['X-Accel-Buffering'] = 'no'

        return response
```

---

## 3. Frontend 구현

### 3.1 Basket 상태 감지 및 UI

```typescript
// frontend/components/AnalysisChat/useEmptyBasketDetection.ts

"""
빈 바스켓 상태를 감지하고 UI에 반영하는 훅
"""

import { useEffect, useState } from 'react';

interface EmptyBasketGuidance {
  type: 'completely_empty' | 'partial_question' | 'general_education';
  title: string;
  message: string;
  steps: string[];
  examples: Array<{
    scenario: string;
    action: string;
    benefit: string;
  }>;
}

export function useEmptyBasketDetection(
  basketItems: any[],
  userQuestion: string
) {
  const [emptyReason, setEmptyReason] = useState<string | null>(null);
  const [guidance, setGuidance] = useState<EmptyBasketGuidance | null>(null);

  useEffect(() => {
    // 빈 바스켓이 아니면 가이드 숨김
    if (basketItems && basketItems.length > 0) {
      setEmptyReason(null);
      setGuidance(null);
      return;
    }

    // 백엔드에서 전송받은 empty_basket_detected 이벤트 처리
    // (여기서는 로컬에서 판별)

    if (!userQuestion || userQuestion.trim() === '') {
      setEmptyReason('completely_empty');
      setGuidance({
        type: 'completely_empty',
        title: '분석을 시작해보겠습니다!',
        message: '아직 바구니가 비어있네요. 하지만 좋은 시작점입니다.',
        steps: [
          '관심 종목 선택 (Apple, Tesla 등)',
          '바구니에 추가 (최소 1개, 최대 5개)',
          '분석 시작 → AI가 종합 분석 제시'
        ],
        examples: [
          {
            scenario: '기술주 투자를 생각 중',
            action: 'Apple, NVIDIA, Microsoft 추가',
            benefit: 'AI가 경쟁 관계와 공급망 분석'
          }
        ]
      });
    }
  }, [basketItems, userQuestion]);

  return { emptyReason, guidance };
}
```

### 3.2 가이드 UI 컴포넌트

```typescript
// frontend/components/AnalysisChat/EmptyBasketGuide.tsx

"""
빈 바스켓 상황에서 표시할 가이드 UI
"""

interface EmptyBasketGuideProps {
  guidance: EmptyBasketGuidance;
  onAddStockClick: () => void;
}

export function EmptyBasketGuide({
  guidance,
  onAddStockClick
}: EmptyBasketGuideProps) {
  return (
    <div className="flex flex-col gap-6 p-6 bg-blue-50 rounded-lg border border-blue-200">
      {/* 제목 */}
      <div>
        <h3 className="text-lg font-semibold text-gray-800 mb-2">
          {guidance.title}
        </h3>
        <p className="text-gray-600">
          {guidance.message}
        </p>
      </div>

      {/* 단계별 가이드 */}
      <div className="bg-white rounded-lg p-4">
        <h4 className="font-semibold text-gray-800 mb-3">시작하기</h4>
        <div className="space-y-3">
          {guidance.steps.map((step, index) => (
            <div key={index} className="flex gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center font-semibold text-sm">
                {index + 1}
              </div>
              <p className="text-gray-700 leading-relaxed pt-1">
                {step}
              </p>
            </div>
          ))}
        </div>

        {/* CTA 버튼 */}
        <button
          onClick={onAddStockClick}
          className="mt-4 w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded-lg transition"
        >
          종목 추가하기
        </button>
      </div>

      {/* 예시 시나리오 */}
      {guidance.examples.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-800 mb-3">예시 시나리오</h4>
          <div className="space-y-3">
            {guidance.examples.map((example, index) => (
              <div key={index} className="bg-white rounded-lg p-4 border-l-4 border-blue-400">
                <p className="text-sm font-medium text-gray-900 mb-2">
                  {example.scenario}
                </p>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>
                    <strong>추가:</strong> {example.action}
                  </p>
                  <p>
                    <strong>효과:</strong> {example.benefit}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 면책조항 */}
      <div className="bg-yellow-50 border-l-4 border-yellow-300 p-3">
        <p className="text-xs text-gray-700">
          <strong>안내:</strong> 본 분석은 정보 제공 목적이며,
          투자 조언이 아닙니다. 투자 결정은 충분한 조사와
          전문가 상담 후 스스로 판단하세요.
        </p>
      </div>
    </div>
  );
}
```

### 3.3 스트림 응답 처리

```typescript
// frontend/components/AnalysisChat/AnalysisStream.tsx

"""
서버 스트림 응답을 처리하여 UI에 표시
"""

interface StreamEvent {
  phase: string;
  data?: any;
  message?: string;
  chunk?: string;
  reason?: string;
  guidance?: EmptyBasketGuidance;
}

export function useAnalysisStream(sessionId: number) {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startStream = async (message: string) => {
    setIsLoading(true);
    setError(null);
    setEvents([]);

    try {
      const response = await fetch(
        `/api/v1/rag/analysis/${sessionId}/stream/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message })
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error('No response body');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));
              setEvents(prev => [...prev, event]);

              // 특정 phase에서 UI 업데이트
              if (event.phase === 'empty_basket_detected') {
                // 가이드 표시
                console.log('Empty basket detected:', event.reason);
              }

              if (event.phase === 'complete') {
                setIsLoading(false);
              }
            } catch (e) {
              console.error('Failed to parse SSE:', e);
            }
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsLoading(false);
    }
  };

  return { events, isLoading, error, startStream };
}
```

---

## 4. 통합 예시: 전체 흐름

```python
# 1. 사용자 요청
"""
POST /api/v1/rag/analysis/123/stream/
{
  "message": "PER이 뭐예요?"
}
"""

# 2. Backend 분석
"""
1. AnalysisSession 조회
2. basket.items.count() = 0 (바구니 비어있음)
3. ContextDetector.detect_empty_reason()
   → EmptyBasketReason.GENERAL_EDUCATION
4. PromptManager.get_system_prompt()
   → SYSTEM_PROMPT_GENERAL_EDUCATION 선택
5. LLM에 전송하여 스트리밍 응답
"""

# 3. Frontend 수신
"""
SSE Events:
1. phase: 'context_detected', reason: 'general_education'
2. phase: 'analyzing_empty', message: '정보를 준비 중입니다...'
3. phase: 'guidance_ready', guidance: {...}
4. phase: 'streaming', chunk: 'PER은 주가 ...'
5. phase: 'streaming', chunk: '... 분석 지표입니다.'
...
n. phase: 'complete', analysis: '...'
"""

# 4. UI 렌더링
"""
1. EmptyBasketGuide 표시 (가이드)
2. 스트리밍 응답 표시 (학습 콘텐츠)
3. 다음 단계 버튼: "종목 추가하기"
4. 면책조항 표시
"""
```

---

## 5. 테스트 케이스

```python
# tests/test_empty_basket.py

"""
빈 바스켓 대응 테스트
"""

import pytest
from django.contrib.auth.models import User
from rag_analysis.models import AnalysisSession, DataBasket, AnalysisMessage
from rag_analysis.services.context_detector import ContextDetector, EmptyBasketReason
from rag_analysis.services.prompt_manager import PromptManager


class TestContextDetector:
    """상황 판별 테스트"""

    def test_completely_empty_basket_no_question(self):
        """바구니 비고 질문 없음"""
        reason = ContextDetector.detect_empty_reason(
            question="",
            has_basket_items=False
        )
        assert reason == EmptyBasketReason.COMPLETELY_EMPTY

    def test_specific_stock_question_no_basket(self):
        """특정 종목 질문, 바구니 비어있음"""
        reason = ContextDetector.detect_empty_reason(
            question="Apple이 좋은 종목인가요?",
            has_basket_items=False
        )
        assert reason == EmptyBasketReason.PARTIAL_QUESTION

    def test_general_education_question(self):
        """일반 개념 질문"""
        reason = ContextDetector.detect_empty_reason(
            question="PER이 뭐예요?",
            has_basket_items=False
        )
        assert reason == EmptyBasketReason.GENERAL_EDUCATION

    def test_normal_with_basket_items(self):
        """바구니가 있으면 정상 분석"""
        reason = ContextDetector.detect_empty_reason(
            question="분석해주세요",
            has_basket_items=True,
            item_count=3
        )
        assert reason == EmptyBasketReason.NORMAL

    def test_extract_mentioned_stocks(self):
        """질문에서 종목 추출"""
        stocks = ContextDetector.extract_mentioned_stocks(
            "Apple과 Microsoft 중 뭐가 낫나요?"
        )
        assert 'Apple' in stocks or 'AAPL' in stocks
        assert 'Microsoft' in stocks or 'MSFT' in stocks

    def test_extract_financial_metrics(self):
        """질문에서 금융 지표 추출"""
        metrics = ContextDetector.extract_financial_metrics(
            "Apple의 PER과 ROE가 어떻게 되나요?"
        )
        assert 'PER' in metrics
        assert 'ROE' in metrics


class TestPromptManager:
    """프롬프트 선택 테스트"""

    def test_get_system_prompt_empty_basket(self):
        """빈 바스켓 프롬프트"""
        prompt = PromptManager.get_system_prompt(
            question="",
            has_basket_items=False
        )
        assert "바구니가 비어있을 때" in prompt or "데이터를 추가" in prompt

    def test_get_system_prompt_general_education(self):
        """일반 교육 프롬프트"""
        prompt = PromptManager.get_system_prompt(
            question="PER이 뭐예요?",
            has_basket_items=False
        )
        assert "3단계" in prompt or "초급" in prompt or "중급" in prompt

    def test_disclaimer_always_included(self):
        """면책조항 항상 포함"""
        prompt = PromptManager.get_system_prompt(
            question="테스트",
            has_basket_items=False,
            include_disclaimer=True
        )
        assert "투자 조언" in prompt or "정보 제공" in prompt

    def test_get_guidance_data(self):
        """가이드 데이터 생성"""
        guidance = PromptManager.get_guidance_data(
            EmptyBasketReason.COMPLETELY_EMPTY
        )
        assert guidance['type'] == 'completely_empty'
        assert len(guidance['steps']) == 3
        assert 'examples' in guidance


@pytest.mark.asyncio
class TestAnalysisPipeline:
    """분석 파이프라인 테스트"""

    @pytest.fixture
    async def setup(self, db):
        """테스트 환경 설정"""
        user = User.objects.create_user('testuser', password='123456')
        basket = DataBasket.objects.create(user=user, name='테스트 바구니')
        session = AnalysisSession.objects.create(
            user=user,
            basket=basket
        )
        return session

    async def test_empty_basket_analysis(self, setup):
        """빈 바스켓 분석 흐름"""
        from rag_analysis.services.pipeline_lite import AnalysisPipelineLite

        session = setup
        pipeline = AnalysisPipelineLite()

        phases = []
        async for event in pipeline.analyze(session, "PER이 뭐예요?"):
            phases.append(event['phase'])

        assert 'context_detected' in phases
        assert 'guidance_ready' in phases or 'streaming_start' in phases
        assert 'complete' in phases

    async def test_completely_empty_without_question(self, setup):
        """완전히 비어있고 질문도 없음"""
        from rag_analysis.services.pipeline_lite import AnalysisPipelineLite

        session = setup
        pipeline = AnalysisPipelineLite()

        first_event = None
        async for event in pipeline.analyze(session, ""):
            first_event = event
            break

        assert first_event['phase'] == 'context_detected'
        assert first_event['reason'] == 'completely_empty'
```

---

이 구현 예시를 통해 빈 바스켓 대응을 완전히 구현할 수 있습니다.

*Empty Basket Implementation v1.0 - 2025-12-15*
