# RAG Analysis Services

Stock-Vis AI 분석 시스템의 LLM 서비스 모듈입니다.

## 개요

```
DataBasket → DateAwareContextFormatter → LLMServiceLite → ResponseParser → AnalysisMessage
```

## 모듈 구성

### 1. `context.py` - DateAwareContextFormatter

DataBasket의 아이템들을 LLM이 이해할 수 있는 컨텍스트로 변환합니다.

#### 핵심 기능
- 날짜 기반 컨텍스트 포맷팅 (snapshot_date 명시)
- 아이템 타입별 최적화된 포맷팅 (stock, news, financial, macro)
- 토큰 효율적인 구조화

#### 사용 예제
```python
from rag_analysis.models import DataBasket
from rag_analysis.services import DateAwareContextFormatter

# DataBasket 조회
basket = DataBasket.objects.get(id=1)

# 컨텍스트 생성
formatter = DateAwareContextFormatter(basket)
context = formatter.format()

print(context)
# === 분석 데이터 바구니 ===
# 분석 기준일: 2024년 3월 15일
# 바구니명: My Basket
# 총 아이템 수: 3개
#
# [1] 종목: Apple Inc.
# 심볼: AAPL
# 데이터 기준일: 2024-03-14
# 주가: $170.50 (기준: 2024-03-14)
# ...
```

#### 포맷팅 전략

| 아이템 타입 | 주요 필드 |
|------------|---------|
| stock | price, market_cap, rsi, ma_50/200 |
| news | summary, sentiment, related_symbols |
| financial | revenue, net_income, eps, cash_flow |
| macro | value, previous_value, change |

---

### 2. `llm_service.py` - LLMServiceLite

Claude API 기반 LLM 서비스입니다.

#### 핵심 기능
- 스트리밍 응답 (AsyncGenerator)
- 지수 백오프 재시도 (RateLimitError 처리)
- 투자 분석 특화 시스템 프롬프트
- 토큰 사용량 추적

#### 사용 예제
```python
from rag_analysis.services import LLMServiceLite

llm = LLMServiceLite()

# 스트리밍 분석
async for event in llm.generate_stream(context, question):
    if event['type'] == 'delta':
        print(event['content'], end='', flush=True)

    elif event['type'] == 'final':
        print(f"\n\n토큰 사용량: {event['input_tokens']} / {event['output_tokens']}")

    elif event['type'] == 'error':
        print(f"에러: {event['message']}")
```

#### 시스템 프롬프트 특징
- 날짜 명시 규칙 (모든 수치에 기준일 포함)
- 면책 조항 자동 포함
- `<suggestions>` 태그로 추천 종목 제안

#### 에러 핸들링
- RateLimitError: 지수 백오프 재시도 (1s, 2s, 4s)
- APIError: 즉시 에러 반환
- Exception: 로깅 후 에러 반환

---

### 3. `llm_service.py` - ResponseParser

LLM 응답에서 `<suggestions>` 태그를 파싱합니다.

#### 사용 예제
```python
from rag_analysis.services import ResponseParser

response = """
AAPL의 주요 공급사를 분석하면...

<suggestions>
[
  {"symbol": "TSM", "reason": "AAPL의 주요 반도체 공급사"},
  {"symbol": "QCOM", "reason": "5G 칩셋 경쟁사"}
]
</suggestions>

⚠️ 투자 유의사항...
"""

cleaned_content, suggestions = ResponseParser.parse_suggestions(response)

print(cleaned_content)  # <suggestions> 태그 제거된 본문
print(suggestions)  # [{'symbol': 'TSM', 'reason': '...'}, ...]
```

#### Suggestions 형식
```python
[
    {
        "symbol": "TSM",  # 대문자로 정규화됨
        "reason": "AAPL의 주요 반도체 공급사"
    }
]
```

---

### 4. `pipeline.py` - AnalysisPipelineLite

전체 분석 파이프라인을 관리합니다.

#### Phase 기반 이벤트 스트리밍

| Phase | 설명 | 이벤트 형식 |
|-------|------|-----------|
| preparing | 데이터 준비 | `{'phase': 'preparing', 'message': '...'}` |
| context_ready | 컨텍스트 생성 완료 | `{'phase': 'context_ready', 'message': '...', 'context_length': 1500}` |
| analyzing | LLM 분석 시작 | `{'phase': 'analyzing', 'message': '...'}` |
| streaming | LLM 응답 스트리밍 | `{'phase': 'streaming', 'chunk': 'text...'}` |
| complete | 분석 완료 | `{'phase': 'complete', 'data': {...}}` |
| error | 에러 발생 | `{'phase': 'error', 'error': {'code': '...', 'message': '...'}}` |

#### 사용 예제
```python
from rag_analysis.models import AnalysisSession
from rag_analysis.services import AnalysisPipelineLite

# 세션 조회
session = AnalysisSession.objects.get(id=1)

# 파이프라인 생성
pipeline = AnalysisPipelineLite(session)

# 분석 실행
async for event in pipeline.analyze(question="AAPL의 실적 전망은?"):
    if event['phase'] == 'preparing':
        print(event['message'])

    elif event['phase'] == 'context_ready':
        print(f"컨텍스트 준비 완료: {event['context_length']} chars")

    elif event['phase'] == 'streaming':
        print(event['chunk'], end='', flush=True)

    elif event['phase'] == 'complete':
        data = event['data']
        print(f"\n\n분석 완료!")
        print(f"제안 종목: {data['suggestions']}")
        print(f"토큰: {data['usage']}")
        print(f"레이턴시: {data['latency_ms']}ms")

    elif event['phase'] == 'error':
        error = event['error']
        print(f"에러 [{error['code']}]: {error['message']}")
```

#### Complete 이벤트 데이터 구조
```python
{
    'phase': 'complete',
    'data': {
        'content': '분석 결과 전체 텍스트',
        'suggestions': [
            {'symbol': 'TSM', 'reason': 'AAPL의 반도체 공급사'}
        ],
        'usage': {
            'input_tokens': 1500,
            'output_tokens': 800
        },
        'latency_ms': 3200
    }
}
```

#### 에러 코드

| 코드 | 설명 |
|------|------|
| BASKET_NOT_FOUND | 데이터 바구니를 찾을 수 없음 |
| LLM_ERROR | LLM API 호출 실패 |
| GRAPH_ERROR | Neo4j 쿼리 실패 |
| PIPELINE_ERROR | 파이프라인 내부 오류 |

---

## Django Async 안정성

### DB 연결 관리

```python
from asgiref.sync import sync_to_async
from django.db import close_old_connections

# DB 접근은 반드시 sync_to_async로 래핑
@sync_to_async
def _save_message(self, ...):
    close_old_connections()  # 연결 정리
    AnalysisMessage.objects.create(...)

# 파이프라인 종료 시 finally 블록에서 연결 정리
async def analyze(self, question):
    try:
        # ... streaming logic
    finally:
        await sync_to_async(close_old_connections)()
```

---

## 환경 설정

### 1. 의존성 설치

```bash
poetry add anthropic
```

### 2. 환경 변수 (.env)

```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### 3. settings.py

```python
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
```

---

## API 사용 예제 (View에서)

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from rag_analysis.services import AnalysisPipelineLite
from rag_analysis.models import AnalysisSession

class AnalysisStreamView(APIView):
    async def post(self, request, session_id):
        session = await sync_to_async(AnalysisSession.objects.get)(id=session_id)
        question = request.data.get('question')

        pipeline = AnalysisPipelineLite(session)

        async def event_stream():
            async for event in pipeline.analyze(question):
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
```

---

## 면책 조항 (필수)

모든 LLM 응답은 자동으로 다음 면책 조항을 포함합니다:

```
⚠️ 투자 유의사항
본 분석은 정보 제공 목적이며 투자 권유가 아닙니다.
투자 결정에 따른 책임은 투자자 본인에게 있습니다.
모든 투자에는 위험이 따르며, 원금 손실 가능성이 있습니다.
```

---

## 제약사항

- Claude API Model: `claude-sonnet-4-20250514`
- Max Tokens: 2000
- Max Retries: 3 (1s, 2s, 4s 지수 백오프)
- Basket Max Items: 15

---

## 다음 단계

- @infra: Celery 태스크 인터페이스 구현 필요
- @frontend: SSE (Server-Sent Events) 스트리밍 UI 구현 필요
- @backend: API 엔드포인트 (views.py) 구현 필요

---

## 참고

- [Anthropic API Documentation](https://docs.anthropic.com/en/api/messages-streaming)
- [Django Async Views](https://docs.djangoproject.com/en/stable/topics/async/)
- [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
