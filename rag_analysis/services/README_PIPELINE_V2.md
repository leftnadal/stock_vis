# Pipeline V2 - RAG 기반 분석 파이프라인

## 개요

PipelineV2는 Entity Extraction, Hybrid Search, Reranking, Context Compression을 결합한 고급 RAG 파이프라인입니다.

## 아키텍처

```
User Question
    ↓
Stage 1: Entity Extraction (Haiku)
    → stocks, metrics, concepts, timeframe
    ↓
Stage 2: Hybrid Search
    → Vector (의미) + BM25 (키워드) + Graph (관계)
    ↓
Stage 3: Reranking (Cross-Encoder)
    → Top-K 문서 선별
    ↓
Stage 4: Context Compression (Haiku)
    → 토큰 수 획기적 감소
    ↓
Stage 5: LLM Analysis (Sonnet 4.5)
    → 최종 답변 생성
```

## SSE 이벤트 흐름

```javascript
// 1. Entity Extraction
{phase: 'extracting', message: '질문에서 엔티티를 추출하고 있습니다...'}
{phase: 'entities_extracted', entities: {stocks: [...], metrics: [...]}}

// 2. Hybrid Search
{phase: 'searching', message: '관련 문서를 검색하고 있습니다...'}
{phase: 'search_complete', results_count: 15}

// 3. Reranking
{phase: 'ranking', message: '문서 관련성을 재평가하고 있습니다...'}
{phase: 'ranking_complete', top_k: 5}

// 4. Compression
{phase: 'compressing', message: '컨텍스트를 압축하고 있습니다...'}
{phase: 'compression_complete', stats: {
  original_tokens: 2000,
  compressed_tokens: 500,
  compression_ratio: 0.25
}}

// 5. LLM Analysis
{phase: 'analyzing', message: 'AI 분석을 시작합니다...'}
{phase: 'streaming', chunk: '애플...'}
{phase: 'streaming', chunk: '의 실적은...'}
{phase: 'complete', data: {...}}
```

## 사용법

### 1. API 호출 (Frontend)

```typescript
// PipelineV2 사용
const response = await fetch(
  `/api/v1/rag/sessions/${sessionId}/chat?pipeline=v2`,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      message: 'AAPL의 최근 실적은 어때?'
    })
  }
);

// SSE 이벤트 처리
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const {done, value} = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));

      switch (event.phase) {
        case 'entities_extracted':
          console.log('추출된 엔티티:', event.entities);
          break;
        case 'compression_complete':
          console.log('압축률:', event.stats.compression_ratio);
          break;
        case 'streaming':
          // UI 업데이트
          appendText(event.chunk);
          break;
        case 'complete':
          console.log('파이프라인 통계:', event.data.pipeline_stats);
          break;
      }
    }
  }
}
```

### 2. Python에서 직접 사용

```python
from rag_analysis.models import AnalysisSession
from rag_analysis.services import AnalysisPipelineV2

# 세션 생성
session = AnalysisSession.objects.get(pk=session_id)

# 파이프라인 초기화
pipeline = AnalysisPipelineV2(
    session=session,
    rerank_top_k=10,  # Reranking 전 선별 문서 수
    final_top_k=5     # 최종 압축 후 사용 문서 수
)

# 분석 실행 (비동기)
async for event in pipeline.analyze("AAPL의 재무 상태는?"):
    if event['phase'] == 'streaming':
        print(event['chunk'], end='', flush=True)
    elif event['phase'] == 'complete':
        print("\n\n최종 결과:", event['data'])
```

### 3. 문서 제공 (선택적)

```python
# 외부 문서 제공 (DB 조회 생략)
documents = [
    {
        'id': 'AAPL_2024-01-01_financial',
        'symbol': 'AAPL',
        'type': 'financial',
        'title': 'AAPL 2024 Q1 실적',
        'content': '매출 1000억 달러...',
        'date': '2024-01-01'
    },
    # ...
]

pipeline = AnalysisPipelineV2(
    session=session,
    documents=documents  # 문서 직접 제공
)
```

## 설정 옵션

### SearchWeights (Hybrid Search)

```python
from rag_analysis.services import SearchWeights

weights = SearchWeights(
    vector=0.4,  # 의미 검색 가중치
    bm25=0.3,    # 키워드 검색 가중치
    graph=0.3    # 관계 검색 가중치
)

pipeline = AnalysisPipelineV2(session, search_weights=weights)
```

### Context Compression

```python
# 기본 압축기 (빠름)
from rag_analysis.services import ContextCompressor
compressor = ContextCompressor()

# 질문 기반 압축기 (더 관련성 높음)
from rag_analysis.services import QuestionAwareCompressor
compressor = QuestionAwareCompressor()

pipeline.compressor = compressor
```

## 성능 지표

### 토큰 사용량 비교

| 모드 | 입력 토큰 | 압축 후 | 압축률 |
|------|-----------|---------|--------|
| PipelineLite (바구니) | 8,000 | - | - |
| PipelineV2 (RAG 압축 전) | 15,000 | - | - |
| PipelineV2 (압축 후) | 15,000 | 2,000 | 13% |

### 레이턴시

- Entity Extraction: ~500ms
- Hybrid Search: ~200ms
- Reranking: ~300ms
- Compression (5 docs): ~1,000ms
- LLM Analysis: ~3,000ms
- **Total: ~5,000ms**

## 에러 핸들링

```python
async for event in pipeline.analyze(question):
    if event['phase'] == 'error':
        error_code = event['error']['code']
        error_msg = event['error']['message']

        if error_code == 'LLM_ERROR':
            # LLM API 에러
            handle_llm_error(error_msg)
        elif error_code == 'PIPELINE_ERROR':
            # 파이프라인 에러
            handle_pipeline_error(error_msg)
```

## PipelineLite vs PipelineV2

| Feature | PipelineLite | PipelineV2 |
|---------|--------------|------------|
| 데이터 소스 | DataBasket (사용자가 선택) | DB/Neo4j (자동 검색) |
| 검색 방식 | 없음 | Hybrid (Vector+BM25+Graph) |
| 재순위화 | 없음 | Cross-Encoder |
| 압축 | 없음 | Haiku 압축 (50단어) |
| 토큰 제한 | 8,000 | 압축 후 ~2,000 |
| 적합한 경우 | 사용자가 데이터 큐레이션 | 자동 관련 문서 검색 |

## 주의사항

1. **API 비용**: PipelineV2는 Haiku를 추가로 사용하여 비용이 증가합니다.
   - Entity Extraction: 1회 (Haiku)
   - Compression: N회 (문서 개수만큼, Haiku)
   - LLM Analysis: 1회 (Sonnet 4.5)

2. **레이턴시**: 5단계로 인해 PipelineLite보다 느립니다 (~5초 vs ~3초)

3. **문서 준비**: `documents` 파라미터를 제공하지 않으면 DB 조회가 필요합니다.
   - 현재 `_fetch_documents()` 메서드는 구현되지 않음 (TODO)

4. **의존성**: sentence-transformers, rank-bm25 패키지 필요
   ```bash
   pip install sentence-transformers rank-bm25
   ```

## 다음 단계

- [ ] `_fetch_documents()` 구현 (stocks 앱 연동)
- [ ] Neo4j 관계 데이터 통합
- [ ] 압축 품질 평가 (ROUGE, BERTScore)
- [ ] 캐싱 전략 (검색 결과, 압축 결과)
- [ ] 배치 압축 (여러 세션 동시 처리)
