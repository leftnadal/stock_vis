#!/usr/bin/env python3
"""
AI Analysis 구현 교훈을 KB에 일괄 추가하는 스크립트
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared_kb.add import main as add_main
from shared_kb.schema import KnowledgeType, ConfidenceLevel
import uuid
from shared_kb.ontology_kb import OntologyKB
from shared_kb.schema import KnowledgeItem

# KB 연결
kb = OntologyKB()

lessons = [
    {
        "title": "Django ASGI + SSE 스트리밍 패턴",
        "content": """Django Daphne ASGI 환경에서 Server-Sent Events(SSE) 스트리밍 구현 시 주의사항:

문제 1: asyncio.new_event_loop() 금지
- 에러: 'cannot schedule new futures after interpreter shutdown'
- 원인: Daphne는 이미 이벤트 루프를 관리하고 있음
- 해결: asgiref.sync.async_to_sync 사용

해결 패턴: async_to_sync 사용
```python
from asgiref.sync import async_to_sync

class ChatStreamView(APIView):
    def post(self, request, pk):
        async def run_pipeline():
            # 비동기 로직
            yield event

        # async 함수를 동기적으로 실행
        events = async_to_sync(run_pipeline)()

        def event_generator():
            for event in events:
                yield f"data: {json.dumps(event)}\\n\\n"

        return StreamingHttpResponse(
            event_generator(),
            content_type='text/event-stream'
        )
```

문제 2: DRF 커스텀 렌더러 필요
- 에러: 406 Not Acceptable
- 원인: DRF 기본 렌더러가 text/event-stream 미지원
- 해결: EventStreamRenderer 추가

문제 3: SSE 인증 토큰 처리
- 에러: 401 Unauthorized
- 원인: EventSource API는 헤더 설정 불가
- 해결: fetch API + SSE 조합 사용

출처: Stock-Vis AI Analysis 기능 구현""",
        "knowledge_type": KnowledgeType.PATTERN,
        "domain": "tech",
        "tags": ["django", "asgi", "sse", "streaming", "daphne"],
        "confidence": ConfidenceLevel.VERIFIED
    },
    {
        "title": "Django ORM async 컨텍스트 안전 호출 패턴",
        "content": """async 컨텍스트에서 Django ORM을 호출할 때 발생하는 SynchronousOnlyOperation 에러 해결 패턴

문제:
- 에러: "You cannot call this from an async context"
- 원인: Django ORM은 동기 함수이며 async 컨텍스트에서 직접 호출 불가

해결: @sync_to_async 데코레이터 사용
```python
from asgiref.sync import sync_to_async

class ContextFormatter:
    @sync_to_async
    def _format_context(self):
        # Django ORM 호출 (동기 코드)
        items = BasketItem.objects.filter(basket=basket)
        stock = Stock.objects.get(symbol=symbol)
        return formatted_context

    async def format(self):
        # async 컨텍스트에서 안전하게 호출
        return await self._format_context()
```

적용 위치:
1. Pipeline 서비스 (rag_analysis/services/pipeline.py)
2. Context Formatter (rag_analysis/services/context.py)
3. 모든 async 함수 내 ORM 호출

주의사항:
- sync_to_async는 별도 스레드에서 동기 함수를 실행
- DB 연결 풀 관리 주의 (thread_sensitive=True 고려)
- 성능: 잦은 컨텍스트 전환 시 오버헤드 발생

출처: Stock-Vis AI Analysis 기능 구현""",
        "knowledge_type": KnowledgeType.PATTERN,
        "domain": "tech",
        "tags": ["django", "orm", "async", "sync_to_async", "asgiref"],
        "confidence": ConfidenceLevel.VERIFIED
    },
    {
        "title": "React SSE 스트림 처리 및 캐시 무효화 패턴",
        "content": """Server-Sent Events를 React에서 처리하고 TanStack Query 캐시를 적절히 무효화하는 패턴

1. SSE 커스텀 훅
```typescript
// hooks/useSSEStream.ts
interface SSEEvent {
  phase: 'preparing' | 'context_ready' | 'analyzing' | 'streaming' | 'complete'
  data?: any
}

export function useSSEStream(url: string) {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [basketCleared, setBasketCleared] = useState(false)

  useEffect(() => {
    const eventSource = new EventSource(url)
    eventSource.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.phase === 'basket_cleared') {
        setBasketCleared(true)
      }
    }
    return () => eventSource.close()
  }, [url])

  return { events, basketCleared }
}
```

2. 캐시 무효화 타이밍
```typescript
const { basketCleared } = useSSEStream(streamUrl)
const queryClient = useQueryClient()

useEffect(() => {
  if (basketCleared && currentBasketId) {
    queryClient.invalidateQueries({
      queryKey: QUERY_KEYS.basket(currentBasketId)
    })
  }
}, [basketCleared, currentBasketId, queryClient])
```

주의사항:
- EventSource는 GET만 지원 → POST 필요 시 fetch API 사용
- SSE 연결은 컴포넌트 언마운트 시 반드시 close()
- 여러 이벤트 타입에 대한 명확한 phase 정의 필요

출처: Stock-Vis AI Analysis 기능 구현""",
        "knowledge_type": KnowledgeType.PATTERN,
        "domain": "tech",
        "tags": ["react", "sse", "tanstack-query", "cache-invalidation", "typescript"],
        "confidence": ConfidenceLevel.VERIFIED
    },
    {
        "title": "LLM 스트리밍 응답 내 XML 태그 파싱 패턴",
        "content": """LLM이 특정 형식의 XML 태그로 구조화된 응답을 반환할 때 실시간으로 파싱하는 패턴

사용 사례:
AI가 분석 중 "바구니에 데이터 추가" 액션을 XML로 제안

파싱 구현:
```python
import re
from xml.etree import ElementTree as ET

def parse_basket_actions(text: str) -> list[dict]:
    pattern = r'<basket_actions>(.*?)</basket_actions>'
    matches = re.findall(pattern, text, re.DOTALL)

    actions = []
    for match in matches:
        try:
            xml_str = f"<basket_actions>{match}</basket_actions>"
            root = ET.fromstring(xml_str)
            for add_elem in root.findall('add'):
                actions.append({
                    'symbol': add_elem.get('symbol'),
                    'item_type': add_elem.get('item_type'),
                })
        except ET.ParseError:
            continue  # 불완전한 XML 무시 (스트리밍 중)
    return actions
```

스트리밍 처리:
```python
async for chunk in llm_stream:
    full_text += chunk
    actions = parse_basket_actions(full_text)
    if actions:
        new_actions = actions[len(processed_actions):]
        for action in new_actions:
            await add_to_basket(action['symbol'], action['item_type'])
        processed_actions = actions
```

주의사항:
1. 불완전한 XML 허용: 스트리밍 중에는 XML이 잘릴 수 있음
2. 중복 방지: 이미 처리한 액션 추적
3. 프롬프트 엔지니어링: LLM에게 명확한 XML 형식 지시

출처: Stock-Vis AI Analysis 기능 구현""",
        "knowledge_type": KnowledgeType.PATTERN,
        "domain": "tech",
        "tags": ["llm", "xml", "parsing", "streaming", "claude"],
        "confidence": ConfidenceLevel.HIGH
    },
    {
        "title": "AI 기능 UX - 심플함의 중요성",
        "content": """AI Analysis 기능 개발 시 초기 과설계에서 심플화 과정의 교훈

문제: 초기 과설계
1. 화려한 애니메이션: 로딩 스피너, 페이드 인/아웃, 타이핑 효과
2. 과도한 아이콘: 각 단계마다 아이콘 추가
3. 큰 컴포넌트 크기: 화면의 25% 차지

결과:
- 개발 시간 낭비 (불필요한 애니메이션 구현)
- 사용자 주의 분산 (본질: 분석 결과, 주의 소모: 화려한 UI)
- 유지보수 복잡도 증가

해결: 심플화
1. 애니메이션 최소화: 필수 로딩 표시만 유지
2. 텍스트 중심: "AI가 분석 중..." (아이콘 제거)
3. 컴포넌트 축소: 25% → 20% → 더 작게

교훈:
- AI 기능은 결과물이 핵심, UI는 보조 수단
- "Claude가 분석 중" → "AI가 분석 중" (브랜딩 최소화)
- 빠른 MVP 출시 > 화려한 초기 버전
- 사용자 피드백 후 필요한 부분만 개선

적용 원칙:
1. 첫 구현: 가장 심플한 버전 (텍스트 + 기본 로딩)
2. 출시 후: 사용자 불편 사항 수집
3. 점진적 개선: 필요한 UX만 추가

출처: Stock-Vis AI Analysis 기능 구현""",
        "knowledge_type": KnowledgeType.LESSON,
        "domain": "project",
        "tags": ["ux", "over-engineering", "ai-interface", "simplicity"],
        "confidence": ConfidenceLevel.HIGH
    },
    {
        "title": "Django 모델 필드명 일관성 - stock.name vs stock.stock_name",
        "content": """Stock-Vis 프로젝트에서 발생한 AttributeError 디버깅 사례

에러:
AttributeError: 'Stock' object has no attribute 'name'

원인:
Stock 모델은 stock_name 필드를 사용하지만, 코드에서 stock.name으로 접근 시도

Stock 모델 정의:
```python
class Stock(models.Model):
    symbol = models.CharField(max_length=10, primary_key=True)
    stock_name = models.CharField(max_length=200)  # NOT 'name'
    sector = models.CharField(max_length=100, blank=True)
```

해결:
```python
# 잘못된 코드
stock_info = {'name': stock.name}  # ❌ AttributeError

# 올바른 코드
stock_info = {'name': stock.stock_name}  # ✅
```

예방:
1. 모델 정의 확인: 작업 전 models.py 검토
2. IDE 자동완성 활용: 존재하지 않는 필드 탐지
3. 테스트 작성: 모델 직렬화 테스트 추가

관련 모델 필드 (Stock-Vis):
- Stock.stock_name (NOT name)
- Stock.market_cap (NOT marketCap)
- DailyPrice.adj_close (NOT adjClose)

출처: Stock-Vis AI Analysis 기능 구현""",
        "knowledge_type": KnowledgeType.TROUBLESHOOT,
        "domain": "project",
        "tags": ["django", "models", "debugging", "stock-vis"],
        "confidence": ConfidenceLevel.VERIFIED
    },
    {
        "title": "Django Model Choices 동적 확장 시 마이그레이션 필수",
        "content": """Django 모델의 choices 필드에 새로운 선택지를 추가할 때 발생하는 에러 해결

에러:
"'overview' 은/는 올바른 선택사항이 아닙니다"

원인:
BasketItem.ItemType에 새로운 타입들(OVERVIEW, PRICE, FINANCIAL_SUMMARY)을 추가했지만 마이그레이션 미실행

해결 단계:
1. 모델에 choices 추가
```python
class BasketItem(models.Model):
    class ItemType(models.TextChoices):
        OVERVIEW = 'overview'  # ✅ 추가
        PRICE = 'price'
        FINANCIAL_SUMMARY = 'financial_summary'
```

2. 마이그레이션 생성: python manage.py makemigrations
3. 마이그레이션 실행: python manage.py migrate

주의사항:
- Choices 변경 = 스키마 변경 → 마이그레이션 필수
- 기존 데이터가 있다면 데이터 마이그레이션 고려
- 선택지 제거 시: 기존 데이터 처리 계획 수립

출처: Stock-Vis AI Analysis 기능 구현""",
        "knowledge_type": KnowledgeType.TROUBLESHOOT,
        "domain": "tech",
        "tags": ["django", "models", "choices", "migration"],
        "confidence": ConfidenceLevel.VERIFIED
    },
    {
        "title": "SSE Phase 기반 진행 상태 통신 패턴",
        "content": """Server-Sent Events를 활용한 단계별 진행 상태 전달 패턴

사용 사례:
LLM 분석 파이프라인의 진행 상태를 프론트엔드에 실시간 전달

Phase 정의:
PHASES = ['preparing', 'context_ready', 'analyzing', 'streaming', 'complete']

백엔드 구현:
```python
async def run_analysis_pipeline(basket_id, query):
    yield {'phase': 'preparing', 'message': '분석 준비 중...'}
    context = await load_context(basket_id)
    yield {'phase': 'context_ready', 'data': {'item_count': len(context)}}
    yield {'phase': 'analyzing'}
    async for chunk in llm_stream(context, query):
        yield {'phase': 'streaming', 'data': {'chunk': chunk}}
    yield {'phase': 'complete'}
```

프론트엔드 처리:
```typescript
eventSource.onmessage = (e) => {
  const event = JSON.parse(e.data)
  switch(event.phase) {
    case 'preparing': setStatus('준비 중...'); break
    case 'streaming': appendMessage(event.data.chunk); break
    case 'complete': eventSource.close(); break
  }
}
```

장점:
1. 명확한 상태 관리: 각 단계별 명확한 구분
2. 에러 핸들링: 특정 phase에서 에러 발생 시 디버깅 용이
3. UX 개선: 사용자에게 진행 상황 명확히 전달
4. 확장성: 새로운 phase 추가 용이

주의사항:
- Phase 순서 보장 필요
- 각 phase는 명확한 의미를 가져야 함
- 프론트/백엔드 phase 정의 동기화

출처: Stock-Vis AI Analysis 기능 구현""",
        "knowledge_type": KnowledgeType.PATTERN,
        "domain": "tech",
        "tags": ["sse", "progress-tracking", "state-machine", "streaming"],
        "confidence": ConfidenceLevel.HIGH
    }
]

print("AI Analysis 구현 교훈 KB 추가 시작...\n")

for i, lesson in enumerate(lessons, 1):
    try:
        item = KnowledgeItem(
            id=str(uuid.uuid4()),
            title=lesson["title"],
            content=lesson["content"],
            knowledge_type=lesson["knowledge_type"],
            domain=lesson["domain"],
            tags=lesson["tags"],
            confidence=lesson["confidence"],
            source="Stock-Vis AI Analysis 기능 구현",
            created_by="qa-architect"
        )

        knowledge_id = kb.add_knowledge(item)
        print(f"✅ {i}/{len(lessons)} 추가 완료: {lesson['title']}")
        print(f"   ID: {knowledge_id[:8]}...\n")

    except Exception as e:
        print(f"❌ {i}/{len(lessons)} 추가 실패: {lesson['title']}")
        print(f"   에러: {str(e)}\n")

kb.close()
print("\n모든 교훈 추가 완료!")
print("\n확인: python shared_kb/search.py 'AI Analysis' --type pattern")
