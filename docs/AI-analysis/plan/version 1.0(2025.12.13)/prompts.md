# Stock-Vis Claude Code Prompts v1.0.0

## AI Analysis 시스템 구현용 프롬프트

**버전**: 1.0.0  
**최종 수정**: 2025-12-13  
**관련 문서**: AI_ANALYSIS_v1.0.0_OVERVIEW.md

---

## 📋 목차

1. [개요](#1-개요)
2. [Phase 1 프롬프트](#2-phase-1-프롬프트)
3. [Phase 2 프롬프트](#3-phase-2-프롬프트)
4. [Phase 3 프롬프트](#4-phase-3-프롬프트)
5. [유틸리티 프롬프트](#5-유틸리티-프롬프트)
6. [트러블슈팅 프롬프트](#6-트러블슈팅-프롬프트)

---

## 1. 개요

### 1.1 문서 목적

이 문서는 Stock-Vis AI Analysis 시스템을 Claude Code로 구현할 때 사용하는 프롬프트 모음입니다.
각 프롬프트는 특정 기능 구현에 최적화되어 있습니다.

### 1.2 사용 방법

```bash
# Claude Code에서 프롬프트 실행
claude "프롬프트 내용"

# 또는 파일에서 읽기
claude < prompt.txt
```

### 1.3 에이전트 역할

| 에이전트 | 역할 | 주요 작업 |
|----------|------|----------|
| `backend` | Django 백엔드 | 모델, API, 서비스 |
| `frontend` | Next.js 프론트엔드 | 컴포넌트, 상태 관리 |
| `infra` | 인프라/DevOps | Docker, CI/CD |
| `kb-curator` | 지식베이스 | Neo4j 스키마, 데이터 |
| `qa-architecture` | QA/아키텍처 | 테스트, 리뷰 |

---

## 2. Phase 1 프롬프트

### 2.1 Django 앱 생성 및 모델 정의

```
@backend

Stock-Vis 프로젝트에 AI 분석 시스템용 Django 앱을 생성해줘.

## 요구사항

1. 앱 이름: `rag_analysis`

2. 모델 정의:
   - DataBasket: 사용자의 분석 바구니
     - user (FK to User)
     - name (CharField, max 100)
     - description (TextField, optional)
     - MAX_ITEMS = 15 (하드 제한)
     - created_at, updated_at
   
   - BasketItem: 바구니 아이템
     - basket (FK to DataBasket)
     - item_type (choices: stock, news, financial, macro)
     - reference_id (종목코드, 뉴스ID 등)
     - title, subtitle
     - data_snapshot (JSONField) - 담을 당시 데이터 스냅샷
     - snapshot_date
     - unique_together: (basket, item_type, reference_id)
   
   - AnalysisSession: 분석 세션
     - user (FK)
     - basket (FK, nullable)
     - status (choices: active, completed, error)
     - exploration_path (JSONField) - 탐험 경로 기록
   
   - AnalysisMessage: 대화 메시지
     - session (FK)
     - role (choices: user, assistant, system)
     - content (TextField)
     - suggestions (JSONField)
     - input_tokens, output_tokens

3. 검증 로직:
   - BasketItem 저장 시 바구니 아이템 수 체크 (15개 제한)
   - clean() 메서드로 ValidationError 발생

4. Admin 등록

참고 문서: AI_ANALYSIS_v1.0.0_PHASE1.md 섹션 2.2
```

### 2.2 DRF Serializers 및 ViewSets

```
@backend

rag_analysis 앱의 API를 구현해줘.

## Serializers (serializers.py)

1. BasketItemSerializer
   - item_type_display (읽기 전용)
   - snapshot_date, created_at (읽기 전용)

2. DataBasketSerializer
   - items (nested, 읽기 전용)
   - items_count (읽기 전용)
   - can_add_item (SerializerMethodField)

3. AnalysisMessageSerializer
4. AnalysisSessionSerializer
   - messages (nested)
   - basket (nested 읽기, ID 쓰기)

## ViewSets (views.py)

1. DataBasketViewSet (ModelViewSet)
   - permission: IsAuthenticated
   - queryset: 현재 사용자 바구니만
   - actions:
     - add_item: POST /baskets/{id}/add_item/
     - remove_item: DELETE /baskets/{id}/items/{item_id}/
     - clear: DELETE /baskets/{id}/clear/

2. AnalysisSessionViewSet (ModelViewSet)
   - 사용자 세션만 조회

## URL 설정 (urls.py)
- DefaultRouter 사용
- /api/v1/rag/ 하위에 등록

참고 문서: AI_ANALYSIS_v1.0.0_PHASE1.md 섹션 2.3-2.5
```

### 2.3 Neo4j 연결 및 서비스

```
@backend

Neo4j 연결 및 기본 서비스를 구현해줘.

## 요구사항

1. neo4j_driver.py
   - 싱글톤 패턴으로 AsyncGraphDatabase driver 관리
   - get_neo4j_driver() 함수
   - close_neo4j_driver() 함수 (앱 종료 시)
   - 설정: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

2. neo4j_service.py - Neo4jServiceLite 클래스
   - QUERY_TIMEOUT = 2000ms
   
   - get_stock_relationships(symbol, max_depth=1):
     - supply_chain: SUPPLIES, SUPPLIED_BY 관계
     - competitors: COMPETES_WITH 관계
     - sector_peers: 동일 섹터 종목
     - 각 최대 5개 반환
     - Graceful Degradation: 타임아웃/에러 시 빈 결과 + _meta.source='fallback'
   
   - health_check(): 연결 상태 확인

3. 쿼리 예시:
```cypher
// 공급망
MATCH (s:Stock {symbol: $symbol})-[r:SUPPLIES|SUPPLIED_BY]-(related:Stock)
RETURN related.symbol, related.name, type(r), r.strength
ORDER BY r.strength DESC LIMIT 5

// 경쟁사
MATCH (s:Stock {symbol: $symbol})-[r:COMPETES_WITH]-(related:Stock)
RETURN related.symbol, related.name, r.overlap_score
ORDER BY r.overlap_score DESC LIMIT 5
```

참고 문서: AI_ANALYSIS_v1.0.0_PHASE1.md 섹션 3.2
```

### 2.4 LLM 서비스 및 SSE 스트리밍

```
@backend

Claude API 연동 및 SSE 스트리밍을 구현해줘.

## llm_service.py

1. LLMServiceLite 클래스
   - MODEL = "claude-sonnet-4-20250514"
   - MAX_TOKENS = 2000
   - 재시도: 3회, 지수 백오프 (1, 2, 4초)

2. get_system_prompt():
   - 투자 분석 AI 역할 정의
   - 규칙:
     - 모든 수치에 날짜 명시
     - 면책조항 포함
     - <suggestions> 태그로 탐험 제안

3. generate_stream(context, question):
   - AsyncGenerator[dict, None] 반환
   - yield {'type': 'delta', 'content': ...}
   - yield {'type': 'final', 'input_tokens': ..., 'output_tokens': ...}
   - yield {'type': 'error', 'message': ...}

4. ResponseParser 클래스
   - parse_suggestions(content): (main_content, suggestions) 반환
   - <suggestions> 태그 파싱

## views.py 추가

5. AnalysisSessionViewSet.chat_stream 액션
   - POST /sessions/{id}/chat/stream/
   - StreamingHttpResponse (text/event-stream)
   - SSE 형식: "data: {json}\n\n"

참고 문서: AI_ANALYSIS_v1.0.0_PHASE1.md 섹션 4.2-4.4
```

### 2.5 분석 파이프라인 (Phase 1)

```
@backend

Phase 1 분석 파이프라인을 구현해줘.

## pipeline.py - AnalysisPipelineLite 클래스

1. __init__(session: AnalysisSession)
   - Neo4jServiceLite, LLMServiceLite 초기화

2. analyze(question: str) -> AsyncGenerator:
   전체 흐름:
   
   a) 준비 단계
      yield {'phase': 'preparing', 'message': '분석 준비 중...'}
   
   b) 컨텍스트 구성
      - DateAwareContextFormatter로 바구니 포맷팅
      - Neo4j에서 첫 번째 종목의 관계 정보 조회
      yield {'phase': 'context_ready'}
   
   c) LLM 스트리밍
      yield {'phase': 'analyzing'}
      async for chunk in llm.generate_stream():
          yield {'phase': 'streaming', 'chunk': ...}
   
   d) 완료
      - ResponseParser로 suggestions 추출
      - 메시지 DB 저장
      yield {'phase': 'complete', 'data': {...}}
   
   e) 에러 처리
      yield {'phase': 'error', 'message': ...}

## context.py - DateAwareContextFormatter 클래스

3. format() -> str:
   - 헤더: 분석 기준일, 바구니명, 아이템 수
   - 아이템별 포맷팅 (item_type에 따라)
   - 모든 수치에 snapshot_date 명시

참고 문서: AI_ANALYSIS_v1.0.0_PHASE1.md 섹션 4.1, 4.3
```

---

## 3. Phase 2 프롬프트

### 3.1 Entity Extraction

```
@backend

Haiku 기반 엔티티 추출기를 구현해줘.

## entity_extractor.py

1. ExtractedEntities TypedDict:
   - stocks: list[str]
   - metrics: list[str]
   - concepts: list[str]
   - timeframe: str | None

2. EntityExtractor 클래스
   - MODEL = "claude-3-5-haiku-20241022"
   - MAX_TOKENS = 200
   
   - EXTRACTION_PROMPT: JSON 형식 응답 유도
     - stocks: 종목명/종목코드
     - metrics: 재무/투자 지표 (PER, 매출 등)
     - concepts: 투자 개념 (저평가, 리스크 등)
     - timeframe: 시간 범위
   
   - extract(question: str) -> ExtractedEntities
     - Haiku 호출
     - JSON 파싱 (마크다운 코드블록 제거)
     - 실패 시 _fallback_extraction 호출

3. _fallback_extraction(question):
   - 정규식으로 대문자 종목코드 추출
   - 한글 종목명 매칭 (삼성전자, SK하이닉스 등)

4. EntityNormalizer 클래스
   - STOCK_MAPPING: 한글명 → 심볼
   - METRIC_MAPPING: 한글 → 영문 필드
   - normalize_stocks(), normalize_metrics()

참고 문서: AI_ANALYSIS_v1.0.0_PHASE2.md 섹션 2.2
```

### 3.2 Hybrid Search

```
@backend

Vector + BM25 + Graph 하이브리드 검색을 구현해줘.

## vector_search.py

1. VectorSearchService 클래스
   - MODEL = "sentence-transformers/all-MiniLM-L6-v2"
   - encode(text), encode_batch(texts)
   - search(query, documents, top_k=20):
     - 코사인 유사도 계산
     - 상위 K개 반환: List[Tuple[doc, score]]

## bm25_search.py

2. BM25SearchService 클래스
   - _tokenize(text): 한글/영문/숫자 토큰화
   - build_index(documents)
   - search(query, documents, top_k=10):
     - rank_bm25.BM25Okapi 사용
     - 점수 > 0인 결과만 반환

## hybrid_search.py

3. HybridSearchService 클래스
   - WEIGHTS = {'vector': 0.4, 'bm25': 0.3, 'graph': 0.3}
   
   - search(question, entities, documents, filters, top_k=15):
     a) 메타데이터 필터 적용 (_apply_metadata_filters)
     b) Vector Search (top 20)
     c) BM25 Search (top 10, 점수 정규화)
     d) Graph Boosting (_get_graph_boost)
     e) 가중 합계로 최종 점수
     f) List[Tuple[doc, score, breakdown]] 반환

4. MetadataFilterBuilder 클래스
   - from_entities(entities, default_days=90):
     - timeframe 파싱
     - 종목 필터 생성

참고 문서: AI_ANALYSIS_v1.0.0_PHASE2.md 섹션 3.2-3.4
```

### 3.3 Cross-Encoder Reranking

```
@backend

Cross-Encoder 기반 재순위화를 구현해줘.

## reranker.py

1. CrossEncoderReranker 클래스
   - MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
   
   - rerank(question, documents, top_k=3):
     - documents: List[Tuple[doc, score, breakdown]]
     - Cross-Encoder로 (question, doc_text) 쌍 점수 계산
     - breakdown에 'rerank' 점수 추가
     - 재정렬 후 top_k 반환
   
   - _get_document_text(doc): 최대 1000자

2. RerankerWithThreshold 클래스
   - threshold = 0.5
   - min_docs = 1 (최소 반환 수)
   - 임계값 미달해도 min_docs 보장

## graphrag_scorer.py

3. GraphRAGScorer 클래스
   - WEIGHTS = {'rerank': 0.5, 'graph_rel': 0.3, 'recency': 0.2}
   
   - score_and_select(question, entities, documents, top_k=3):
     a) Cross-Encoder Reranking (top 10)
     b) 그래프 관계 점수 추가
     c) 최신성 점수 추가
     d) 가중 합계로 최종 점수
   
   - _calculate_graph_relevance(doc, graph_context):
     - 직접 언급 종목: +0.3
     - 관련 종목 언급: +0.15
   
   - _calculate_recency_score(doc):
     - 7일 이내: 1.0
     - 30일: 0.7
     - 90일: 0.3
     - 그 이상: 0.1

참고 문서: AI_ANALYSIS_v1.0.0_PHASE2.md 섹션 4.2-4.3
```

### 3.4 Context Compression

```
@backend

Haiku 기반 컨텍스트 압축을 구현해줘.

## context_compressor.py

1. ContextCompressor 클래스
   - MODEL = "claude-3-5-haiku-20241022"
   - MAX_TOKENS_PER_DOC = 100
   
   - COMPRESSION_PROMPT:
     "다음 문서를 핵심 정보만 남기고 50단어 이내로 압축하세요.
      날짜, 수치, 고유명사는 반드시 포함하세요."
   
   - compress(documents, question) -> List[dict]:
     - asyncio.gather로 병렬 압축
     - 결과: original_id, title, compressed, compression_ratio
   
   - _fallback_truncate(doc): 실패 시 처음 100단어

2. QuestionAwareCompressor(ContextCompressor)
   - 질문 맥락을 포함한 압축
   - "질문과 관련된 핵심 정보만 남기고..."

## summary_cache.py

3. StockSummaryCache 클래스
   - TTL = 6시간
   - get_or_create(symbol, stock_data):
     - 캐시 확인
     - 없으면 생성 후 캐시

4. NewsSummaryCache 클래스
   - TTL = 24시간 (뉴스는 불변)

참고 문서: AI_ANALYSIS_v1.0.0_PHASE2.md 섹션 5.2-5.3
```

### 3.5 Phase 2 파이프라인 통합

```
@backend

Phase 2 분석 파이프라인으로 업그레이드해줘.

## pipeline_v2.py - AnalysisPipelineV2 클래스

전체 흐름:

1. Entity Extraction
   yield {'phase': 'extracting'}
   entities = await entity_extractor.extract(question)
   normalized = entity_normalizer.normalize(entities)
   yield {'phase': 'entities_extracted', 'data': {...}}

2. Hybrid Search
   yield {'phase': 'searching'}
   documents = await _get_basket_documents()
   filters = MetadataFilterBuilder.from_entities(entities)
   search_results = await hybrid_search.search(
       question, entities, documents, filters, top_k=15
   )
   yield {'phase': 'search_complete', 'data': {'candidates': len(...)}}

3. GraphRAG Reranking
   yield {'phase': 'ranking'}
   top_docs = await graphrag_scorer.score_and_select(
       question, entities, search_results, top_k=3
   )
   yield {'phase': 'ranking_complete'}

4. Context Compression
   yield {'phase': 'compressing'}
   compressed = await compressor.compress(top_docs, question)
   yield {'phase': 'compression_complete', 'data': {
       'original_tokens': ...,
       'compressed_tokens': ...,
       'reduction': "68%"
   }}

5. Build Optimized Context
   context = _build_optimized_context(entities, compressed, graph_context)

6. LLM Analysis (Phase 1과 동일)

7. Complete with optimization metrics

참고 문서: AI_ANALYSIS_v1.0.0_PHASE2.md 섹션 5.4
```

---

## 4. Phase 3 프롬프트

### 4.1 Semantic Cache

```
@backend

Neo4j 벡터 인덱스 기반 시맨틱 캐시를 구현해줘.

## semantic_cache_setup.py

1. setup_semantic_cache_index():
   - AnalysisCache 노드 제약조건 생성
   - 384차원 벡터 인덱스 생성 (cosine)
   - expires_at 인덱스 생성

## semantic_cache.py

2. SemanticCacheService 클래스
   - SIMILARITY_THRESHOLD = 0.85
   - CACHE_TTL_DAYS = 7
   - EMBEDDING_MODEL = "all-MiniLM-L6-v2"
   
   - find_similar(question, entities, user_id) -> Optional[dict]:
     a) 질문 임베딩
     b) Neo4j 벡터 검색 + 엔티티 매칭
     c) 최종 점수: 벡터 60% + 엔티티 40%
     d) 0.7 이상이면 캐시 히트
     
   - store(question, entities, response, suggestions, usage, ...):
     - UUID 생성
     - 임베딩 생성
     - Neo4j 노드 생성
     - 종목 관계 연결

3. CacheWarmer 클래스
   - warm_popular_queries(top_n=100)
   - precompute_stock_summaries(symbols)

참고 문서: AI_ANALYSIS_v1.0.0_PHASE3.md 섹션 2.2-2.3
```

### 4.2 성능 모니터링

```
@backend

Prometheus 메트릭 및 비용 추적을 구현해줘.

## metrics.py

1. Prometheus 메트릭 정의:
   - ANALYSIS_REQUESTS (Counter): status, cache_hit 라벨
   - LLM_CALLS (Counter): model, status 라벨
   - ANALYSIS_LATENCY (Histogram): phase 라벨, 버킷 [0.5~30초]
   - TOKEN_USAGE (Histogram): type(input/output) 라벨
   - CACHE_HIT_RATE (Gauge)
   - ACTIVE_SESSIONS (Gauge)

2. MetricsCollector 클래스:
   - record_analysis_start()
   - record_analysis_complete(latency, cache_hit, tokens_in, tokens_out, success)
   - record_llm_call(model, latency, success)
   - record_phase_latency(phase, latency)

## cost_tracker.py

3. UsageLog 모델:
   - user (FK)
   - session (FK, nullable)
   - model (choices)
   - input_tokens, output_tokens
   - cost_usd (Decimal)
   - cached (Boolean)
   - created_at

4. CostTracker 클래스:
   - PRICING = {haiku: {input: 0.25, output: 1.25}, sonnet: {...}}
   - calculate_cost(model, input_tokens, output_tokens)
   - log_usage(...)
   - get_user_usage(user_id, start_date, end_date) -> stats
   - get_daily_summary(days=30)

참고 문서: AI_ANALYSIS_v1.0.0_PHASE3.md 섹션 3.2-3.3
```

### 4.3 비용 최적화

```
@backend

복잡도 기반 적응형 LLM 서비스를 구현해줘.

## complexity_classifier.py

1. QuestionComplexity Enum:
   - SIMPLE: 단순 사실 질문 → Haiku
   - MODERATE: 일반 분석 → Sonnet
   - COMPLEX: 심층 분석 → Sonnet (더 많은 토큰)

2. ComplexityClassifier 클래스:
   - SIMPLE_PATTERNS: [r'현재\s*가격', r'PER|PBR', ...]
   - COMPLEX_PATTERNS: [r'비교.*분석', r'전망.*예측', ...]
   
   - classify(question, entities_count) -> QuestionComplexity:
     - 패턴 매칭 우선
     - 엔티티 수로 보완 (>=3: COMPLEX, <=1: SIMPLE)
   
   - get_model_config(complexity) -> dict:
     - SIMPLE: haiku, 1000 tokens, temp 0.3
     - MODERATE: sonnet, 1500 tokens, temp 0.5
     - COMPLEX: sonnet, 2500 tokens, temp 0.7

## adaptive_llm_service.py

3. AdaptiveLLMService 클래스:
   - generate_stream(context, question, entities_count, user_id, session_id):
     a) 복잡도 분류
     b) 모델 설정 가져오기
     c) 해당 모델로 스트리밍
     d) 메트릭 + 비용 로깅

## token_budget.py

4. TokenBudget dataclass: total, used, remaining, utilization
5. TokenBudgetManager:
   - BUDGETS: simple=500, moderate=1000, complex=2000
   - ALLOCATION: graph 25%, docs 45%, system 20%, question 10%
   - truncate_to_budget(text, max_tokens, strategy)

참고 문서: AI_ANALYSIS_v1.0.0_PHASE3.md 섹션 4.1-4.4
```

### 4.4 최종 파이프라인

```
@backend

Phase 3 최종 파이프라인으로 업그레이드해줘.

## pipeline_final.py - AnalysisPipelineFinal 클래스

전체 흐름:

0. 캐시 확인
   yield {'phase': 'cache_check'}
   entities = await entity_extractor.extract(question)
   cache_result = await semantic_cache.find_similar(question, entities)
   
   if cache_result:
       yield {'phase': 'cache_hit', 'data': {...}}
       # 캐시 응답 스트리밍 (타이핑 효과)
       yield {'phase': 'complete', 'data': {..., 'from_cache': True}}
       return

1. 복잡도 분류
   yield {'phase': 'classifying'}
   complexity = classifier.classify(question, len(entities))
   budget = budget_manager.get_budget(complexity)

2. 하이브리드 검색 (Phase 2)

3. GraphRAG Reranking (Phase 2)

4. 컨텍스트 압축 (Phase 2)

5. 예산 내 컨텍스트 구성
   context = _build_context_within_budget(entities, compressed, graph, allocation)

6. 적응형 LLM 분석
   async for chunk in llm.generate_stream(
       context, question, entities_count, user_id, session_id
   ):
       yield chunk

7. 후처리
   - 응답 파싱
   - 시맨틱 캐시 저장
   - 메시지 DB 저장
   - 메트릭 기록

8. 완료
   yield {'phase': 'complete', 'data': {
       'content': ...,
       'suggestions': ...,
       'usage': {...},
       'latency_ms': ...,
       'complexity': ...,
       'from_cache': False
   }}

참고 문서: AI_ANALYSIS_v1.0.0_PHASE3.md 섹션 5.1
```

---

## 5. 유틸리티 프롬프트

### 5.1 Neo4j 시드 데이터

```
@kb-curator

Neo4j 그래프 시드 데이터를 생성해줘.

## management/commands/seed_neo4j_graph.py

1. Command 클래스:
   - --clear 옵션: 기존 데이터 삭제
   
   - handle():
     a) 인덱스 생성 (_create_indexes)
     b) 종목 노드 생성 (_seed_stocks)
     c) 섹터 노드/관계 생성 (_seed_sectors)
     d) 관계 생성 (_seed_relationships)

2. 인덱스:
   - stock_symbol ON Stock(symbol)
   - sector_name ON Sector(name)
   - news_id ON News(id)

3. 관계 예시 데이터:
   - AAPL -[SUPPLIED_BY]-> TSM (0.9)
   - NVDA -[SUPPLIED_BY]-> TSM (0.95)
   - AAPL -[COMPETES_WITH]- MSFT (0.6)
   - AMD -[COMPETES_WITH]- NVDA (0.9)

실행: python manage.py seed_neo4j_graph --clear
```

### 5.2 Signal 기반 동기화

```
@backend

Stock 모델 변경 시 Neo4j 자동 동기화를 구현해줘.

## signals.py

1. stock_saved (post_save):
   - Stock 저장 시 sync_stock_to_neo4j.delay() 호출

2. stock_deleted (post_delete):
   - Stock 삭제 시 delete_stock_from_neo4j.delay() 호출

## tasks.py (Celery)

3. sync_stock_to_neo4j(symbol, name, sector, industry):
   - MERGE Stock 노드
   - 섹터 관계 업데이트

4. delete_stock_from_neo4j(symbol):
   - MATCH + DETACH DELETE

## apps.py

5. ready()에서 signals import
```

### 5.3 캐시 관리 명령어

```
@backend

캐시 관리용 Django 명령어를 만들어줘.

## management/commands/cache_management.py

1. warm_cache 명령어:
   - 인기 질문 캐시 워밍
   - 주요 종목 요약 사전 생성
   
   python manage.py warm_cache --top-queries=100 --top-stocks=50

2. clear_expired_cache 명령어:
   - 만료된 시맨틱 캐시 정리
   - Redis 캐시 정리
   
   python manage.py clear_expired_cache

3. cache_stats 명령어:
   - 캐시 히트율 통계
   - 메모리 사용량
   
   python manage.py cache_stats --days=7
```

---

## 6. 트러블슈팅 프롬프트

### 6.1 Neo4j 연결 문제

```
@backend

Neo4j 연결 문제를 디버깅해줘.

## 증상
- "ServiceUnavailable" 에러
- 쿼리 타임아웃

## 체크리스트
1. 환경변수 확인: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
2. 네트워크 연결: telnet {host} {port}
3. 드라이버 버전 호환성
4. 연결 풀 설정 확인

## 해결책
- Graceful Degradation 구현
- 재시도 로직 추가
- 헬스체크 엔드포인트
```

### 6.2 LLM 응답 파싱 실패

```
@backend

LLM 응답 파싱 오류를 해결해줘.

## 증상
- <suggestions> 태그 파싱 실패
- JSON 파싱 에러 (Entity Extraction)

## 해결책
1. 정규식 패턴 개선:
   - re.DOTALL 플래그
   - 태그 대소문자 무시

2. JSON 파싱 강화:
   - 마크다운 코드블록 제거
   - 후행 쉼표 처리
   - 폴백 로직

3. 프롬프트 개선:
   - 더 명확한 출력 형식 지정
   - 예시 포함
```

### 6.3 SSE 스트리밍 문제

```
@backend

SSE 스트리밍이 끊기는 문제를 해결해줘.

## 증상
- 응답이 중간에 끊김
- 버퍼링으로 한꺼번에 도착

## 해결책
1. 응답 헤더 확인:
   - Content-Type: text/event-stream
   - Cache-Control: no-cache
   - X-Accel-Buffering: no (Nginx)

2. Nginx 설정:
   proxy_buffering off;
   proxy_cache off;

3. Gunicorn 설정:
   - timeout 증가
   - worker 타입: uvicorn.workers.UvicornWorker
```

### 6.4 토큰 예산 초과

```
@backend

토큰 예산 초과 문제를 해결해줘.

## 증상
- LLM 응답이 잘림
- 비용 예상보다 높음

## 해결책
1. 입력 컨텍스트 추적:
   - 각 컴포넌트별 토큰 수 로깅
   - 압축 전후 비교

2. 동적 예산 조절:
   - 질문 길이에 따라 문서 수 조절
   - 압축률 동적 조정

3. 모니터링:
   - 토큰 사용량 대시보드
   - 임계값 알림
```

---

## 📎 프롬프트 사용 팁

### 효과적인 프롬프트 작성

```
1. 역할 명시: @backend, @frontend 등
2. 참조 문서 명시: AI_ANALYSIS_v1.0.0_PHASE1.md 섹션 X.X
3. 구체적인 요구사항 나열
4. 코드 예시 포함
5. 테스트 케이스 언급
```

### 프롬프트 체이닝

```
# 단계적 구현
1. 먼저 모델만 구현
2. 테스트 확인
3. API 구현
4. 테스트 확인
5. 프론트엔드 연동
```

---

*CLAUDE_CODE_PROMPTS v1.0.0 - 2025-12-13*