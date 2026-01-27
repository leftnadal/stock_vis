# Stock-Vis AI Analysis System v4.3 - Phase 3

## 완성 및 최적화 (Completion & Optimization)

**Phase**: 3 of 3  
**기간**: 4주  
**목표**: 캐싱 고도화, 성능 모니터링, 비용 최적화  
**선행 조건**: Phase 1, 2 완료

---

## 📋 목차

1. [Phase 3 개요](#1-phase-3-개요)
2. [Week 1: Semantic Cache](#2-week-1-semantic-cache)
3. [Week 2: 성능 모니터링](#3-week-2-성능-모니터링)
4. [Week 3: 비용 최적화](#4-week-3-비용-최적화)
5. [Week 4: 통합 및 배포](#5-week-4-통합-및-배포)
6. [Phase 3 완료 기준 (DoD)](#6-phase-3-완료-기준)

---

## 1. Phase 3 개요

### 1.1 목표

| 영역 | 목표 | 핵심 지표 |
|------|------|----------|
| **캐싱** | 유사 질문 캐시 히트율 60% | 반복 질문 응답 < 500ms |
| **모니터링** | 실시간 성능 추적 | 이상 탐지, 알림 |
| **비용** | 분석당 비용 50% 추가 절감 | $0.002 → $0.001 |
| **안정성** | 99.5% 가용성 | 에러율 < 0.5% |

### 1.2 최종 성능 목표

| 지표 | Phase 2 | Phase 3 목표 | 개선 |
|------|---------|-------------|------|
| 캐시 히트 응답 | N/A | < 500ms | 신규 |
| 캐시 미스 응답 | 8초 | 6초 | 25% ↑ |
| 캐시 히트율 | 20% | 60% | 3x ↑ |
| 분석당 비용 | $0.002 | $0.001 | 50% ↓ |

---

## 2. Week 1: Semantic Cache

### 2.1 개요

**Semantic Cache**는 유사한 질문에 대해 과거 분석 결과를 재사용합니다.

### 2.2 Neo4j 벡터 인덱스 설정

```python
# rag_analysis/services/semantic_cache_setup.py

def setup_semantic_cache_index():
    """Neo4j 벡터 인덱스 설정"""
    
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )
    
    with driver.session() as session:
        # 벡터 인덱스 생성 (384차원)
        session.run("""
            CREATE VECTOR INDEX analysis_question_embedding IF NOT EXISTS
            FOR (c:AnalysisCache)
            ON c.question_embedding
            OPTIONS {
                indexConfig: {
                    `vector.dimensions`: 384,
                    `vector.similarity_function`: 'cosine'
                }
            }
        """)
    
    driver.close()
```

### 2.3 Semantic Cache Service

```python
# rag_analysis/services/semantic_cache.py

class SemanticCacheService:
    """시맨틱 캐시 서비스"""
    
    SIMILARITY_THRESHOLD = 0.85
    CACHE_TTL_DAYS = 7
    
    async def find_similar(
        self,
        question: str,
        entities: list[str],
        user_id: int = None
    ) -> Optional[dict]:
        """유사한 과거 분석 검색"""
        
        embedding = self.encoder.encode(question).tolist()
        
        async with self.driver.session() as session:
            result = await session.run("""
                CALL db.index.vector.queryNodes(
                    'analysis_question_embedding', 10, $embedding
                ) YIELD node as cache, score
                WHERE score >= $threshold
                  AND cache.expires_at > datetime()
                
                OPTIONAL MATCH (cache)-[:ANALYZED]->(stock:Stock)
                WHERE stock.symbol IN $entities
                WITH cache, score, count(stock) as entity_matches
                
                WITH cache, 
                     score * 0.6 + (toFloat(entity_matches) / size($entities)) * 0.4 as final_score
                WHERE final_score >= 0.7
                
                ORDER BY final_score DESC
                LIMIT 1
                
                RETURN cache.id, cache.response, cache.suggestions, final_score
            """, embedding=embedding, threshold=self.SIMILARITY_THRESHOLD, entities=entities)
            
            record = await result.single()
            if record:
                return {'cache_hit': True, 'response': record['cache.response'], ...}
        
        return None
    
    async def store(self, question, entities, response, suggestions, usage, ...):
        """분석 결과 캐시 저장"""
        # Neo4j에 캐시 노드 생성 및 종목 연결
```

### 2.4 Week 1 완료 기준

- [ ] Neo4j 벡터 인덱스 설정
- [ ] SemanticCacheService 구현
- [ ] CacheWarmer 구현
- [ ] 캐시 히트율 테스트 (목표: 40%+)

---

## 3. Week 2: 성능 모니터링

### 3.1 Prometheus 메트릭

```python
# rag_analysis/metrics.py

from prometheus_client import Counter, Histogram, Gauge

ANALYSIS_REQUESTS = Counter(
    'stockvis_analysis_requests_total',
    'Total analysis requests',
    ['status', 'cache_hit']
)

ANALYSIS_LATENCY = Histogram(
    'stockvis_analysis_latency_seconds',
    'Analysis request latency',
    ['phase'],
    buckets=[0.5, 1, 2, 3, 5, 8, 10, 15, 30]
)

CACHE_HIT_RATE = Gauge(
    'stockvis_cache_hit_rate',
    'Cache hit rate (rolling 1h)',
)

TOKEN_USAGE = Histogram(
    'stockvis_token_usage',
    'Token usage per request',
    ['type'],
    buckets=[100, 200, 500, 1000, 2000, 5000]
)
```

### 3.2 비용 추적

```python
# rag_analysis/services/cost_tracker.py

class CostTracker:
    """비용 추적 서비스"""
    
    PRICING = {
        'haiku': {'input': 0.25, 'output': 1.25},
        'sonnet': {'input': 3.0, 'output': 15.0},
    }
    
    def calculate_cost(self, model, input_tokens, output_tokens):
        prices = self.PRICING.get(model, self.PRICING['sonnet'])
        return (input_tokens / 1_000_000) * prices['input'] + \
               (output_tokens / 1_000_000) * prices['output']
    
    def log_usage(self, user_id, session_id, model, input_tokens, output_tokens, cached=False):
        cost = 0 if cached else self.calculate_cost(model, input_tokens, output_tokens)
        UsageLog.objects.create(
            user_id=user_id, session_id=session_id, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            cost_usd=cost, cached=cached
        )
```

### 3.3 Week 2 완료 기준

- [ ] Prometheus 메트릭 구현
- [ ] UsageLog 모델 및 CostTracker 구현
- [ ] Grafana 대시보드 설정
- [ ] 알림 규칙 설정

---

## 4. Week 3: 비용 최적화

### 4.1 질문 복잡도 분류기

```python
# rag_analysis/services/complexity_classifier.py

class QuestionComplexity(Enum):
    SIMPLE = "simple"       # → Haiku
    MODERATE = "moderate"   # → Sonnet
    COMPLEX = "complex"     # → Sonnet (더 많은 토큰)

class ComplexityClassifier:
    
    def classify(self, question: str, entities_count: int = 0) -> QuestionComplexity:
        # 패턴 매칭으로 복잡도 분류
        if re.search(r'비교.*분석|영향.*분석|전망', question):
            return QuestionComplexity.COMPLEX
        if re.search(r'현재\s*가격|PER|시가총액', question):
            return QuestionComplexity.SIMPLE
        return QuestionComplexity.MODERATE
    
    def get_model_config(self, complexity: QuestionComplexity) -> dict:
        configs = {
            QuestionComplexity.SIMPLE: {'model': 'claude-3-5-haiku-20241022', 'max_tokens': 1000},
            QuestionComplexity.MODERATE: {'model': 'claude-sonnet-4-20250514', 'max_tokens': 1500},
            QuestionComplexity.COMPLEX: {'model': 'claude-sonnet-4-20250514', 'max_tokens': 2500},
        }
        return configs[complexity]
```

### 4.2 적응형 LLM 서비스

```python
# rag_analysis/services/adaptive_llm_service.py

class AdaptiveLLMService:
    """적응형 LLM 서비스 (비용 최적화)"""
    
    async def generate_stream(self, context, question, entities_count, ...):
        # 복잡도 분류
        complexity = self.classifier.classify(question, entities_count)
        config = self.classifier.get_model_config(complexity)
        
        # 해당 모델로 스트리밍 생성
        async with self.client.messages.stream(
            model=config['model'],
            max_tokens=config['max_tokens'],
            ...
        ) as stream:
            # 스트리밍 처리
```

### 4.3 Week 3 완료 기준

- [ ] ComplexityClassifier 구현
- [ ] AdaptiveLLMService 구현
- [ ] TokenBudgetManager 구현
- [ ] 비용 절감 테스트 (목표: 추가 50%)

---

## 5. Week 4: 통합 및 배포

### 5.1 최종 파이프라인

```python
# rag_analysis/services/pipeline_final.py

class AnalysisPipelineFinal:
    """최종 분석 파이프라인 (v4.3 완성)"""
    
    async def analyze(self, question: str):
        # Stage 0: 캐시 확인
        cache_result = await self.semantic_cache.find_similar(question, entities)
        if cache_result:
            return cache_result  # 즉시 반환
        
        # Stage 1: 복잡도 분류
        complexity = self.classifier.classify(question, len(entities))
        
        # Stage 2: 하이브리드 검색
        search_results = await self.hybrid_search.search(...)
        
        # Stage 3: GraphRAG Reranking
        top_docs = await self.graphrag_scorer.score_and_select(...)
        
        # Stage 4: 압축
        compressed = await self.compressor.compress(top_docs, question)
        
        # Stage 5: 컨텍스트 구성 (예산 내)
        context = self._build_context_within_budget(...)
        
        # Stage 6: 적응형 LLM 분석
        response = await self.llm.generate_stream(context, question, ...)
        
        # Stage 7: 캐시 저장
        await self.semantic_cache.store(question, entities, response, ...)
        
        return response
```

### 5.2 배포 체크리스트

```markdown
## 배포 전 체크리스트

### 인프라
- [ ] Neo4j Aura 프로덕션 인스턴스
- [ ] Redis 클러스터 설정
- [ ] Prometheus + Grafana 배포

### 환경 변수
- [ ] ANTHROPIC_API_KEY
- [ ] NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
- [ ] REDIS_URL

### 성능
- [ ] 캐시 워밍 실행
- [ ] 인덱스 최적화
- [ ] 로드 테스트 통과 (100 concurrent users)
```

### 5.3 Week 4 완료 기준

- [ ] AnalysisPipelineFinal 통합
- [ ] 전체 E2E 테스트 통과
- [ ] 로드 테스트 통과
- [ ] 배포 체크리스트 완료

---

## 6. Phase 3 완료 기준

### 6.1 성능 체크리스트

| 지표 | 목표 | 완료 |
|------|------|------|
| 캐시 히트 응답 | < 500ms | [ ] |
| 캐시 미스 응답 | < 8초 | [ ] |
| 캐시 히트율 | ≥ 60% | [ ] |
| 분석당 비용 | ≤ $0.001 | [ ] |
| 에러율 | < 0.5% | [ ] |
| 가용성 | ≥ 99.5% | [ ] |

---

## 📊 v4.3 최종 요약

```
┌─────────────────────────────────────────────────────────────────┐
│                    Stock-Vis AI Analysis v4.3                    │
│                    GraphRAG + Token Optimization                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: 기반 (4주)                                            │
│  ├── DataBasket / Session 모델                                  │
│  ├── Neo4j 기본 연결                                            │
│  └── SSE 스트리밍                                               │
│                                                                  │
│  Phase 2: 토큰 최적화 (4주)                                     │
│  ├── Entity Extraction (Haiku)                                  │
│  ├── Hybrid Search (Vector + BM25 + Graph)                      │
│  ├── Cross-Encoder Reranking                                    │
│  └── Context Compression (Haiku)                                │
│                                                                  │
│  Phase 3: 완성 (4주)                                            │
│  ├── Semantic Cache (Neo4j Vector)                              │
│  ├── 성능 모니터링 (Prometheus + Grafana)                       │
│  ├── 비용 최적화 (Adaptive Model Selection)                     │
│  └── 배포 및 안정화                                             │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  최종 성과:                                                      │
│  ├── 토큰 절감: 88% (5,000 → 600)                               │
│  ├── 비용 절감: 93% ($0.015 → $0.001)                           │
│  ├── 캐시 히트율: 60%+                                          │
│  └── 응답 시간: TTFT 3초, 전체 8초                              │
└─────────────────────────────────────────────────────────────────┘
```

---

*Phase 3 - Completion & Optimization*
*v1.0.0 - 2025-12-13*

## 토큰 최적화 핵심 (Token Optimization Core)

**Phase**: 2 of 3  
**기간**: 4주  
**목표**: GraphRAG + Reranking + Compression으로 토큰 88% 절감  
**선행 조건**: Phase 1 완료

---

## 📋 목차

1. [Phase 2 개요](#1-phase-2-개요)
2. [Week 1: Entity Extraction](#2-week-1-entity-extraction)
3. [Week 2: Hybrid Search](#3-week-2-hybrid-search)
4. [Week 3: Reranking](#4-week-3-reranking)
5. [Week 4: Context Compression](#5-week-4-context-compression)
6. [Phase 2 완료 기준 (DoD)](#6-phase-2-완료-기준)

---

## 1. Phase 2 개요

### 1.1 목표

Phase 2에서는 **토큰 최적화**의 핵심 컴포넌트를 구현합니다:

| 컴포넌트 | 효과 | 토큰 절감 |
|----------|------|----------|
| Entity Extraction | 질문에서 핵심 엔티티 추출 | 검색 정확도 ↑ |
| Hybrid Search | Vector + BM25 + Graph 결합 | 불필요한 문서 제거 |
| Reranker | 관련성 기반 Top-K 선별 | 20개 → 3개 |
| Compression | 문서 요약 후 주입 | 500토큰 → 30토큰 |

**최종 목표**: 입력 토큰 **2,500 → 800** (68% 절감)

### 1.2 Phase 2 파이프라인 흐름

```
사용자 질문: "TSMC 실적이 삼성전자에 미치는 영향은?"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: Entity Extraction (Haiku) - ~50 토큰                  │
│  Output: [TSMC, 삼성전자, 실적, 영향]                           │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 2: Hybrid Search - 0 토큰 (검색)                         │
│  ├── Graph: TSMC ↔ 삼성전자 관계                                │
│  ├── Vector: 의미 유사 문서 20개                                │
│  ├── BM25: 키워드 매칭 10개                                     │
│  └── Filter: 날짜/섹터 → 15개                                   │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 3: Reranking (Cross-Encoder) - 로컬                      │
│  Input: 15개 후보 × 질문                                        │
│  Output: Top-3 선별                                             │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 4: Compression (Haiku) - ~200 토큰                       │
│  Input: 3개 × 500토큰 = 1,500토큰                               │
│  Output: 3개 × 30토큰 = 90토큰                                  │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 5: LLM Analysis (Sonnet) - ~600 토큰 입력                │
│  ├── Graph Context: 200토큰                                     │
│  ├── Compressed Docs: 90토큰                                    │
│  ├── System Prompt: 200토큰                                     │
│  └── Question: 50토큰                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 비용 비교

| 단계 | Phase 1 | Phase 2 | 절감 |
|------|---------|---------|------|
| 입력 토큰 | ~2,500 | ~600 | 76% |
| Haiku 비용 | $0 | ~$0.0004 | - |
| Sonnet 비용 | ~$0.008 | ~$0.002 | 75% |
| **총 비용** | **$0.008** | **$0.0024** | **70%** |

---

## 2. Week 1: Entity Extraction

### 2.1 개요

사용자 질문에서 **핵심 엔티티**(종목명, 지표, 개념)를 추출하여 검색 정확도를 높입니다.

```
Input:  "TSMC 실적이 삼성전자에 미치는 영향은?"
Output: {
    "stocks": ["TSMC", "삼성전자"],
    "metrics": ["실적"],
    "concepts": ["영향"],
    "timeframe": null
}
```

### 2.2 EntityExtractor 구현

```python
# rag_analysis/services/entity_extractor.py

from anthropic import AsyncAnthropic
from django.conf import settings
from typing import TypedDict
import json
import logging

logger = logging.getLogger(__name__)


class ExtractedEntities(TypedDict):
    stocks: list[str]
    metrics: list[str]
    concepts: list[str]
    timeframe: str | None


class EntityExtractor:
    """엔티티 추출기 (Haiku 기반)"""
    
    MODEL = "claude-3-5-haiku-20241022"
    MAX_TOKENS = 200
    
    EXTRACTION_PROMPT = """주어진 질문에서 다음 엔티티를 추출하세요:

1. stocks: 종목명 또는 종목코드 (예: AAPL, 삼성전자, TSMC)
2. metrics: 재무/투자 지표 (예: PER, 매출, 영업이익, 실적)
3. concepts: 투자 개념 (예: 저평가, 성장주, 리스크, 영향)
4. timeframe: 시간 범위 (예: 2024년, 최근 3개월, Q3)

JSON 형식으로만 응답하세요. 없는 항목은 빈 리스트 또는 null로 표시합니다.

질문: {question}

JSON:"""
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    async def extract(self, question: str) -> ExtractedEntities:
        """질문에서 엔티티 추출"""
        
        try:
            response = await self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                messages=[{
                    "role": "user",
                    "content": self.EXTRACTION_PROMPT.format(question=question)
                }]
            )
            
            content = response.content[0].text.strip()
            
            # JSON 파싱
            # 마크다운 코드 블록 제거
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            entities = json.loads(content)
            
            return ExtractedEntities(
                stocks=entities.get("stocks", []),
                metrics=entities.get("metrics", []),
                concepts=entities.get("concepts", []),
                timeframe=entities.get("timeframe")
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Entity extraction JSON parse error: {e}")
            return self._fallback_extraction(question)
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return self._fallback_extraction(question)
    
    def _fallback_extraction(self, question: str) -> ExtractedEntities:
        """폴백: 간단한 규칙 기반 추출"""
        import re
        
        # 대문자 종목코드 패턴
        stock_pattern = r'\b[A-Z]{2,5}\b'
        stocks = re.findall(stock_pattern, question)
        
        # 한글 종목명 (간단한 패턴)
        korean_stocks = ['삼성전자', '삼성SDI', 'SK하이닉스', 'LG에너지솔루션', 
                        '현대차', 'NAVER', '카카오']
        found_korean = [s for s in korean_stocks if s in question]
        
        return ExtractedEntities(
            stocks=list(set(stocks + found_korean)),
            metrics=[],
            concepts=[],
            timeframe=None
        )


class EntityNormalizer:
    """엔티티 정규화"""
    
    # 종목명 → 심볼 매핑
    STOCK_MAPPING = {
        '삼성전자': '005930.KS',
        'TSMC': 'TSM',
        '애플': 'AAPL',
        '엔비디아': 'NVDA',
        '마이크로소프트': 'MSFT',
        '구글': 'GOOGL',
        '아마존': 'AMZN',
        '테슬라': 'TSLA',
    }
    
    # 지표 정규화
    METRIC_MAPPING = {
        '실적': ['revenue', 'earnings'],
        '매출': ['revenue'],
        '영업이익': ['operating_income'],
        '순이익': ['net_income'],
        'PER': ['pe_ratio'],
        'PBR': ['pb_ratio'],
    }
    
    def normalize_stocks(self, stocks: list[str]) -> list[str]:
        """종목명 정규화"""
        normalized = []
        for stock in stocks:
            if stock in self.STOCK_MAPPING:
                normalized.append(self.STOCK_MAPPING[stock])
            else:
                normalized.append(stock)
        return list(set(normalized))
    
    def normalize_metrics(self, metrics: list[str]) -> list[str]:
        """지표 정규화"""
        normalized = []
        for metric in metrics:
            if metric in self.METRIC_MAPPING:
                normalized.extend(self.METRIC_MAPPING[metric])
            else:
                normalized.append(metric.lower())
        return list(set(normalized))
```

### 2.3 통합 테스트

```python
# rag_analysis/tests/test_entity_extractor.py

import pytest
from ..services.entity_extractor import EntityExtractor, EntityNormalizer


@pytest.mark.asyncio
async def test_entity_extraction_basic():
    """기본 엔티티 추출 테스트"""
    extractor = EntityExtractor()
    
    question = "TSMC 실적이 삼성전자에 미치는 영향은?"
    entities = await extractor.extract(question)
    
    assert "TSMC" in entities["stocks"] or "TSM" in entities["stocks"]
    assert "삼성전자" in entities["stocks"]
    assert len(entities["metrics"]) > 0 or "실적" in str(entities)


@pytest.mark.asyncio
async def test_entity_extraction_with_timeframe():
    """시간 범위 포함 추출 테스트"""
    extractor = EntityExtractor()
    
    question = "2024년 Q3 애플의 매출 성장률은?"
    entities = await extractor.extract(question)
    
    assert entities["timeframe"] is not None


def test_entity_normalizer():
    """엔티티 정규화 테스트"""
    normalizer = EntityNormalizer()
    
    stocks = ["삼성전자", "TSMC", "AAPL"]
    normalized = normalizer.normalize_stocks(stocks)
    
    assert "005930.KS" in normalized
    assert "TSM" in normalized
    assert "AAPL" in normalized
```

### 2.4 Week 1 완료 기준

- [ ] EntityExtractor 클래스 구현
- [ ] Haiku API 연동
- [ ] 폴백 로직 구현
- [ ] EntityNormalizer 구현
- [ ] 단위 테스트 통과

---

## 3. Week 2: Hybrid Search

### 3.1 개요

세 가지 검색 방식을 결합하여 최적의 후보 문서를 찾습니다:

| 검색 방식 | 강점 | 약점 |
|----------|------|------|
| **Vector** | 의미적 유사성 | 고유명사 약함 |
| **BM25** | 정확한 키워드 | 동의어 약함 |
| **Graph** | 관계 기반 | 새로운 관계 모름 |

### 3.2 Vector Search 구현

```python
# rag_analysis/services/vector_search.py

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Tuple
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class VectorSearchService:
    """벡터 유사도 검색 서비스"""
    
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    
    def __init__(self):
        self.model = SentenceTransformer(self.MODEL_NAME)
        self._document_embeddings = {}  # 캐시
    
    def encode(self, text: str) -> np.ndarray:
        """텍스트를 벡터로 인코딩"""
        return self.model.encode(text, convert_to_numpy=True)
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """배치 인코딩"""
        return self.model.encode(texts, convert_to_numpy=True)
    
    def search(
        self, 
        query: str, 
        documents: List[dict],
        top_k: int = 20
    ) -> List[Tuple[dict, float]]:
        """벡터 유사도 검색"""
        
        if not documents:
            return []
        
        # 쿼리 인코딩
        query_embedding = self.encode(query)
        
        # 문서 인코딩 (캐시 활용)
        doc_texts = [d.get('content', d.get('text', '')) for d in documents]
        doc_embeddings = self.encode_batch(doc_texts)
        
        # 코사인 유사도 계산
        similarities = np.dot(doc_embeddings, query_embedding) / (
            np.linalg.norm(doc_embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # 상위 K개 선택
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append((documents[idx], float(similarities[idx])))
        
        return results


class VectorIndex:
    """Neo4j 벡터 인덱스 활용"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
    
    async def search_similar_news(
        self, 
        query_embedding: list, 
        limit: int = 10,
        filters: dict = None
    ) -> list:
        """Neo4j 벡터 인덱스로 유사 뉴스 검색"""
        
        filter_clause = ""
        params = {"embedding": query_embedding, "limit": limit}
        
        if filters:
            if filters.get("sector"):
                filter_clause += "AND n.sector = $sector "
                params["sector"] = filters["sector"]
            if filters.get("after_date"):
                filter_clause += "AND n.published_date >= $after_date "
                params["after_date"] = filters["after_date"]
        
        async with self.driver.session() as session:
            result = await session.run(f"""
                CALL db.index.vector.queryNodes(
                    'news_embedding_index',
                    $limit,
                    $embedding
                ) YIELD node as n, score
                WHERE score >= 0.5 {filter_clause}
                RETURN n.id as id,
                       n.title as title,
                       n.content as content,
                       n.published_date as date,
                       n.source as source,
                       score
                ORDER BY score DESC
            """, **params)
            
            return [dict(record) async for record in result]
```

### 3.3 BM25 Search 구현

```python
# rag_analysis/services/bm25_search.py

from rank_bm25 import BM25Okapi
from typing import List, Tuple
import re


class BM25SearchService:
    """BM25 키워드 검색 서비스"""
    
    def __init__(self):
        self._index = None
        self._documents = None
    
    def _tokenize(self, text: str) -> List[str]:
        """텍스트 토큰화"""
        # 한글, 영문, 숫자 토큰화
        tokens = re.findall(r'[가-힣]+|[a-zA-Z]+|[0-9]+', text.lower())
        return tokens
    
    def build_index(self, documents: List[dict]):
        """BM25 인덱스 구축"""
        self._documents = documents
        
        # 문서 토큰화
        tokenized_docs = []
        for doc in documents:
            text = doc.get('content', doc.get('text', ''))
            title = doc.get('title', '')
            combined = f"{title} {text}"
            tokenized_docs.append(self._tokenize(combined))
        
        self._index = BM25Okapi(tokenized_docs)
    
    def search(
        self, 
        query: str, 
        documents: List[dict] = None,
        top_k: int = 10
    ) -> List[Tuple[dict, float]]:
        """BM25 검색"""
        
        if documents:
            self.build_index(documents)
        
        if not self._index or not self._documents:
            return []
        
        # 쿼리 토큰화
        query_tokens = self._tokenize(query)
        
        # BM25 점수 계산
        scores = self._index.get_scores(query_tokens)
        
        # 상위 K개 선택
        top_indices = sorted(
            range(len(scores)), 
            key=lambda i: scores[i], 
            reverse=True
        )[:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # 점수가 0보다 큰 것만
                results.append((self._documents[idx], float(scores[idx])))
        
        return results
```

### 3.4 Hybrid Search 통합

```python
# rag_analysis/services/hybrid_search.py

from typing import List, Tuple, Optional
from .vector_search import VectorSearchService
from .bm25_search import BM25SearchService
from .neo4j_service import Neo4jServiceLite
from .entity_extractor import ExtractedEntities
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


class HybridSearchService:
    """하이브리드 검색 서비스"""
    
    # 검색 결과 가중치
    WEIGHTS = {
        'vector': 0.4,
        'bm25': 0.3,
        'graph': 0.3,
    }
    
    def __init__(self):
        self.vector_search = VectorSearchService()
        self.bm25_search = BM25SearchService()
        self.neo4j = Neo4jServiceLite()
    
    async def search(
        self,
        question: str,
        entities: ExtractedEntities,
        documents: List[dict],
        filters: Optional[dict] = None,
        top_k: int = 15
    ) -> List[Tuple[dict, float, dict]]:
        """하이브리드 검색 실행
        
        Returns:
            List of (document, combined_score, score_breakdown)
        """
        
        # 1. 메타데이터 필터 적용
        filtered_docs = self._apply_metadata_filters(documents, filters)
        logger.info(f"After metadata filter: {len(filtered_docs)} docs")
        
        # 2. Vector Search
        vector_results = self.vector_search.search(
            question, 
            filtered_docs, 
            top_k=20
        )
        vector_scores = {id(doc): score for doc, score in vector_results}
        
        # 3. BM25 Search
        bm25_results = self.bm25_search.search(
            question,
            filtered_docs,
            top_k=10
        )
        bm25_scores = {id(doc): score for doc, score in bm25_results}
        
        # BM25 점수 정규화 (0-1 범위)
        if bm25_scores:
            max_bm25 = max(bm25_scores.values())
            if max_bm25 > 0:
                bm25_scores = {k: v / max_bm25 for k, v in bm25_scores.items()}
        
        # 4. Graph-based Boosting
        graph_boost = await self._get_graph_boost(entities)
        
        # 5. 점수 결합
        combined_results = []
        seen_docs = set()
        
        # 모든 후보 문서 수집
        all_candidates = set()
        for doc, _ in vector_results:
            all_candidates.add(id(doc))
        for doc, _ in bm25_results:
            all_candidates.add(id(doc))
        
        # 점수 계산
        for doc in filtered_docs:
            doc_id = id(doc)
            if doc_id not in all_candidates:
                continue
            
            # 개별 점수
            v_score = vector_scores.get(doc_id, 0)
            b_score = bm25_scores.get(doc_id, 0)
            g_score = self._calculate_graph_score(doc, graph_boost)
            
            # 가중 합계
            combined = (
                self.WEIGHTS['vector'] * v_score +
                self.WEIGHTS['bm25'] * b_score +
                self.WEIGHTS['graph'] * g_score
            )
            
            combined_results.append((
                doc,
                combined,
                {
                    'vector': v_score,
                    'bm25': b_score,
                    'graph': g_score
                }
            ))
        
        # 정렬 및 상위 K개 반환
        combined_results.sort(key=lambda x: x[1], reverse=True)
        return combined_results[:top_k]
    
    def _apply_metadata_filters(
        self, 
        documents: List[dict], 
        filters: Optional[dict]
    ) -> List[dict]:
        """메타데이터 필터 적용"""
        
        if not filters:
            return documents
        
        filtered = documents
        
        # 날짜 필터
        if filters.get('after_date'):
            after_date = filters['after_date']
            filtered = [
                d for d in filtered 
                if d.get('date', d.get('published_date', '')) >= str(after_date)
            ]
        
        # 섹터 필터
        if filters.get('sector'):
            sector = filters['sector'].lower()
            filtered = [
                d for d in filtered 
                if sector in d.get('sector', '').lower()
            ]
        
        # 종목 필터 (관련 종목만)
        if filters.get('stocks'):
            stocks = set(s.upper() for s in filters['stocks'])
            filtered = [
                d for d in filtered
                if any(s in d.get('related_stocks', []) for s in stocks)
                or any(s in d.get('content', '') for s in stocks)
            ]
        
        return filtered
    
    async def _get_graph_boost(self, entities: ExtractedEntities) -> dict:
        """그래프 기반 부스트 점수 계산"""
        
        boost = {
            'related_stocks': set(),
            'sectors': set()
        }
        
        for stock in entities['stocks']:
            try:
                relationships = await self.neo4j.get_stock_relationships(stock)
                
                # 관련 종목 수집
                for rel_type in ['supply_chain', 'competitors', 'sector_peers']:
                    for rel in relationships.get(rel_type, []):
                        boost['related_stocks'].add(rel.get('symbol', ''))
                
            except Exception as e:
                logger.warning(f"Graph boost error for {stock}: {e}")
        
        return boost
    
    def _calculate_graph_score(self, doc: dict, boost: dict) -> float:
        """그래프 기반 점수 계산"""
        
        score = 0.0
        
        # 관련 종목이 문서에 언급되면 부스트
        doc_stocks = set(doc.get('related_stocks', []))
        doc_content = doc.get('content', '')
        
        for stock in boost['related_stocks']:
            if stock in doc_stocks or stock in doc_content:
                score += 0.2
        
        return min(score, 1.0)  # 최대 1.0


class MetadataFilterBuilder:
    """메타데이터 필터 빌더"""
    
    @staticmethod
    def from_entities(
        entities: ExtractedEntities,
        default_days: int = 90
    ) -> dict:
        """엔티티에서 필터 생성"""
        
        filters = {}
        
        # 시간 범위
        if entities.get('timeframe'):
            filters['after_date'] = MetadataFilterBuilder._parse_timeframe(
                entities['timeframe']
            )
        else:
            # 기본값: 최근 90일
            filters['after_date'] = date.today() - timedelta(days=default_days)
        
        # 종목 필터
        if entities.get('stocks'):
            filters['stocks'] = entities['stocks']
        
        return filters
    
    @staticmethod
    def _parse_timeframe(timeframe: str) -> date:
        """시간 범위 문자열 파싱"""
        import re
        
        today = date.today()
        
        # "최근 N일/주/개월"
        match = re.search(r'최근\s*(\d+)\s*(일|주|개월|달)', timeframe)
        if match:
            num = int(match.group(1))
            unit = match.group(2)
            
            if unit == '일':
                return today - timedelta(days=num)
            elif unit == '주':
                return today - timedelta(weeks=num)
            elif unit in ('개월', '달'):
                return today - timedelta(days=num * 30)
        
        # "2024년" 형식
        year_match = re.search(r'(\d{4})년', timeframe)
        if year_match:
            year = int(year_match.group(1))
            return date(year, 1, 1)
        
        # 기본값
        return today - timedelta(days=90)
```

### 3.5 Week 2 완료 기준

- [ ] VectorSearchService 구현
- [ ] BM25SearchService 구현
- [ ] HybridSearchService 통합
- [ ] MetadataFilterBuilder 구현
- [ ] 검색 품질 테스트 (Precision/Recall)

---

## 4. Week 3: Reranking

### 4.1 개요

검색 결과를 **Cross-Encoder**로 재순위화하여 가장 관련성 높은 Top-K를 선별합니다.

```
Input:  15개 후보 문서 + 질문
Output: 관련성 점수 기반 Top-3
```

### 4.2 Cross-Encoder Reranker 구현

```python
# rag_analysis/services/reranker.py

from sentence_transformers import CrossEncoder
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Cross-Encoder 기반 재순위화"""
    
    MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    def __init__(self):
        self.model = CrossEncoder(self.MODEL_NAME)
    
    def rerank(
        self,
        question: str,
        documents: List[Tuple[dict, float, dict]],
        top_k: int = 3
    ) -> List[Tuple[dict, float, dict]]:
        """문서 재순위화
        
        Args:
            question: 사용자 질문
            documents: (document, score, breakdown) 튜플 리스트
            top_k: 반환할 상위 개수
            
        Returns:
            재순위화된 상위 K개 문서
        """
        
        if not documents:
            return []
        
        if len(documents) <= top_k:
            return documents
        
        # Cross-Encoder 입력 준비
        pairs = []
        for doc, _, _ in documents:
            doc_text = self._get_document_text(doc)
            pairs.append([question, doc_text])
        
        # 점수 계산
        scores = self.model.predict(pairs)
        
        # 점수와 함께 재정렬
        scored_docs = []
        for i, (doc, orig_score, breakdown) in enumerate(documents):
            rerank_score = float(scores[i])
            
            # 원본 점수와 rerank 점수 결합 (선택적)
            # combined = 0.3 * orig_score + 0.7 * self._normalize_score(rerank_score)
            
            breakdown['rerank'] = rerank_score
            scored_docs.append((doc, rerank_score, breakdown))
        
        # 재정렬
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Reranked {len(documents)} docs, top score: {scored_docs[0][1]:.3f}")
        
        return scored_docs[:top_k]
    
    def _get_document_text(self, doc: dict) -> str:
        """문서에서 텍스트 추출"""
        
        title = doc.get('title', '')
        content = doc.get('content', doc.get('text', ''))
        
        # 길이 제한 (Cross-Encoder 최대 512 토큰)
        combined = f"{title}\n{content}"
        return combined[:1000]
    
    def _normalize_score(self, score: float) -> float:
        """점수 정규화 (sigmoid)"""
        import math
        return 1 / (1 + math.exp(-score))


class RerankerWithThreshold:
    """임계값 기반 필터링 추가 Reranker"""
    
    def __init__(self, reranker: CrossEncoderReranker, threshold: float = 0.5):
        self.reranker = reranker
        self.threshold = threshold
    
    def rerank(
        self,
        question: str,
        documents: List[Tuple[dict, float, dict]],
        top_k: int = 3,
        min_docs: int = 1
    ) -> List[Tuple[dict, float, dict]]:
        """임계값 이상인 문서만 반환
        
        Args:
            min_docs: 최소 반환 문서 수 (임계값 미달해도 반환)
        """
        
        reranked = self.reranker.rerank(question, documents, top_k=len(documents))
        
        # 임계값 필터링
        filtered = [
            (doc, score, breakdown) 
            for doc, score, breakdown in reranked 
            if score >= self.threshold
        ]
        
        # 최소 문서 수 보장
        if len(filtered) < min_docs:
            filtered = reranked[:min_docs]
        
        return filtered[:top_k]
```

### 4.3 GraphRAG Scorer 통합

```python
# rag_analysis/services/graphrag_scorer.py

from typing import List, Tuple
from .reranker import CrossEncoderReranker
from .neo4j_service import Neo4jServiceLite
from .entity_extractor import ExtractedEntities
import logging

logger = logging.getLogger(__name__)


class GraphRAGScorer:
    """GraphRAG 통합 점수 계산기"""
    
    # 점수 가중치
    WEIGHTS = {
        'rerank': 0.5,      # Cross-Encoder 점수
        'graph_rel': 0.3,   # 그래프 관계 점수
        'recency': 0.2,     # 최신성 점수
    }
    
    def __init__(self):
        self.reranker = CrossEncoderReranker()
        self.neo4j = Neo4jServiceLite()
    
    async def score_and_select(
        self,
        question: str,
        entities: ExtractedEntities,
        documents: List[Tuple[dict, float, dict]],
        top_k: int = 3
    ) -> List[Tuple[dict, float, dict]]:
        """GraphRAG 통합 점수 계산 및 선별"""
        
        # 1. Cross-Encoder Reranking
        reranked = self.reranker.rerank(question, documents, top_k=10)
        
        # 2. 그래프 관계 점수 추가
        graph_context = await self._get_graph_context(entities)
        
        # 3. 최종 점수 계산
        final_scores = []
        for doc, rerank_score, breakdown in reranked:
            
            # 그래프 관계 점수
            graph_score = self._calculate_graph_relevance(doc, graph_context)
            
            # 최신성 점수
            recency_score = self._calculate_recency_score(doc)
            
            # 가중 합계
            final = (
                self.WEIGHTS['rerank'] * self._normalize(rerank_score) +
                self.WEIGHTS['graph_rel'] * graph_score +
                self.WEIGHTS['recency'] * recency_score
            )
            
            breakdown.update({
                'graph_rel': graph_score,
                'recency': recency_score,
                'final': final
            })
            
            final_scores.append((doc, final, breakdown))
        
        # 최종 정렬
        final_scores.sort(key=lambda x: x[1], reverse=True)
        
        return final_scores[:top_k]
    
    async def _get_graph_context(self, entities: ExtractedEntities) -> dict:
        """그래프 컨텍스트 조회"""
        
        context = {
            'stocks': set(entities['stocks']),
            'related': set(),
            'relationships': []
        }
        
        for stock in entities['stocks']:
            try:
                rels = await self.neo4j.get_stock_relationships(stock)
                
                for rel_type in ['supply_chain', 'competitors', 'sector_peers']:
                    for rel in rels.get(rel_type, []):
                        context['related'].add(rel.get('symbol', ''))
                        context['relationships'].append({
                            'from': stock,
                            'to': rel.get('symbol'),
                            'type': rel_type
                        })
                        
            except Exception as e:
                logger.warning(f"Graph context error: {e}")
        
        return context
    
    def _calculate_graph_relevance(self, doc: dict, graph_context: dict) -> float:
        """그래프 관련성 점수"""
        
        score = 0.0
        doc_stocks = set(doc.get('related_stocks', []))
        doc_content = doc.get('content', '').upper()
        
        # 직접 언급된 종목
        direct_mentions = doc_stocks & graph_context['stocks']
        score += len(direct_mentions) * 0.3
        
        # 관련 종목 언급
        related_mentions = doc_stocks & graph_context['related']
        score += len(related_mentions) * 0.15
        
        # 컨텐츠 내 종목 언급
        for stock in graph_context['stocks']:
            if stock in doc_content:
                score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_recency_score(self, doc: dict) -> float:
        """최신성 점수 (0-1)"""
        from datetime import date, timedelta
        
        doc_date_str = doc.get('date', doc.get('published_date', ''))
        if not doc_date_str:
            return 0.5  # 기본값
        
        try:
            # 문자열을 날짜로 변환
            if isinstance(doc_date_str, str):
                doc_date = date.fromisoformat(doc_date_str[:10])
            else:
                doc_date = doc_date_str
            
            days_ago = (date.today() - doc_date).days
            
            # 7일 이내: 1.0, 30일: 0.7, 90일: 0.3, 그 이상: 0.1
            if days_ago <= 7:
                return 1.0
            elif days_ago <= 30:
                return 0.7 + 0.3 * (30 - days_ago) / 23
            elif days_ago <= 90:
                return 0.3 + 0.4 * (90 - days_ago) / 60
            else:
                return 0.1
                
        except Exception:
            return 0.5
    
    def _normalize(self, score: float) -> float:
        """점수 정규화 (sigmoid)"""
        import math
        return 1 / (1 + math.exp(-score))
```

### 4.4 Week 3 완료 기준

- [ ] CrossEncoderReranker 구현
- [ ] RerankerWithThreshold 구현
- [ ] GraphRAGScorer 통합
- [ ] Reranking 품질 테스트 (nDCG)
- [ ] 처리 시간 < 500ms 확인

---

## 5. Week 4: Context Compression

### 5.1 개요

선별된 문서를 **Haiku로 요약**하여 토큰을 획기적으로 줄입니다.

```
Input:  "TSMC의 2024년 4분기 실적 발표에 따르면, 매출은 200억 달러로 
        전년 대비 15% 증가했으며, 이는 AI 반도체 수요 증가에 
        따른 것으로 분석됩니다. 특히 NVIDIA와 Apple의 주문이 
        크게 늘었으며..." (500 토큰)
        
Output: "TSMC 24Q4: 매출 $20B(+15% YoY), AI 수요 강세, 
        NVIDIA·Apple 주문 증가" (30 토큰)
```

### 5.2 Context Compressor 구현

```python
# rag_analysis/services/context_compressor.py

from anthropic import AsyncAnthropic
from django.conf import settings
from typing import List, Tuple
import asyncio
import logging

logger = logging.getLogger(__name__)


class ContextCompressor:
    """컨텍스트 압축기 (Haiku 기반)"""
    
    MODEL = "claude-3-5-haiku-20241022"
    MAX_TOKENS_PER_DOC = 100
    
    COMPRESSION_PROMPT = """다음 문서를 핵심 정보만 남기고 50단어 이내로 압축하세요.
날짜, 수치, 고유명사는 반드시 포함하세요.

문서:
{document}

압축된 내용 (50단어 이내):"""
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    async def compress(
        self,
        documents: List[Tuple[dict, float, dict]],
        question: str
    ) -> List[dict]:
        """문서 리스트 압축"""
        
        # 병렬 압축
        tasks = [
            self._compress_single(doc, question)
            for doc, _, _ in documents
        ]
        
        compressed = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 필터링 (실패한 것 제외)
        results = []
        for i, result in enumerate(compressed):
            if isinstance(result, Exception):
                logger.warning(f"Compression failed for doc {i}: {result}")
                # 원본 일부 사용 (폴백)
                doc = documents[i][0]
                results.append({
                    'original_id': doc.get('id'),
                    'compressed': self._fallback_truncate(doc),
                    'compression_ratio': 0.5
                })
            else:
                results.append(result)
        
        return results
    
    async def _compress_single(self, doc: dict, question: str) -> dict:
        """단일 문서 압축"""
        
        original_text = self._get_document_text(doc)
        original_tokens = len(original_text.split())  # 대략적 토큰 수
        
        response = await self.client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS_PER_DOC,
            messages=[{
                "role": "user",
                "content": self.COMPRESSION_PROMPT.format(document=original_text)
            }]
        )
        
        compressed_text = response.content[0].text.strip()
        compressed_tokens = len(compressed_text.split())
        
        return {
            'original_id': doc.get('id'),
            'title': doc.get('title', ''),
            'compressed': compressed_text,
            'original_tokens': original_tokens,
            'compressed_tokens': compressed_tokens,
            'compression_ratio': compressed_tokens / max(original_tokens, 1)
        }
    
    def _get_document_text(self, doc: dict) -> str:
        """문서 텍스트 추출 (최대 1000자)"""
        title = doc.get('title', '')
        content = doc.get('content', doc.get('text', ''))
        
        combined = f"{title}\n{content}"
        return combined[:1000]
    
    def _fallback_truncate(self, doc: dict) -> str:
        """폴백: 단순 잘라내기"""
        text = self._get_document_text(doc)
        # 처음 100단어
        words = text.split()[:100]
        return ' '.join(words) + '...'


class QuestionAwareCompressor(ContextCompressor):
    """질문 맥락을 고려한 압축기"""
    
    COMPRESSION_PROMPT = """다음 문서를 질문과 관련된 핵심 정보만 남기고 50단어 이내로 압축하세요.

질문: {question}

문서:
{document}

질문과 관련된 압축 내용 (50단어 이내):"""
    
    async def _compress_single(self, doc: dict, question: str) -> dict:
        """질문 맥락 포함 압축"""
        
        original_text = self._get_document_text(doc)
        original_tokens = len(original_text.split())
        
        response = await self.client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS_PER_DOC,
            messages=[{
                "role": "user",
                "content": self.COMPRESSION_PROMPT.format(
                    question=question,
                    document=original_text
                )
            }]
        )
        
        compressed_text = response.content[0].text.strip()
        compressed_tokens = len(compressed_text.split())
        
        return {
            'original_id': doc.get('id'),
            'title': doc.get('title', ''),
            'compressed': compressed_text,
            'original_tokens': original_tokens,
            'compressed_tokens': compressed_tokens,
            'compression_ratio': compressed_tokens / max(original_tokens, 1)
        }
```

### 5.3 Pre-computed Summary Cache

```python
# rag_analysis/services/summary_cache.py

from django.core.cache import cache
from typing import Optional
import hashlib
import logging

logger = logging.getLogger(__name__)


class StockSummaryCache:
    """종목 요약 사전 생성 캐시"""
    
    TTL = 3600 * 6  # 6시간
    
    def __init__(self, compressor):
        self.compressor = compressor
    
    async def get_or_create(self, stock_symbol: str, stock_data: dict) -> str:
        """캐시된 요약 반환 또는 새로 생성"""
        
        cache_key = f"stock_summary:{stock_symbol}"
        
        # 캐시 확인
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Summary cache hit for {stock_symbol}")
            return cached
        
        # 새로 생성
        summary = await self._generate_summary(stock_symbol, stock_data)
        
        # 캐시 저장
        cache.set(cache_key, summary, self.TTL)
        logger.info(f"Generated and cached summary for {stock_symbol}")
        
        return summary
    
    async def _generate_summary(self, symbol: str, data: dict) -> str:
        """종목 요약 생성"""
        
        doc = {
            'title': f"{symbol} Summary",
            'content': self._format_stock_data(symbol, data)
        }
        
        result = await self.compressor._compress_single(doc, f"{symbol} 분석")
        return result['compressed']
    
    def _format_stock_data(self, symbol: str, data: dict) -> str:
        """종목 데이터 포맷팅"""
        return f"""
        {symbol} ({data.get('name', 'N/A')})
        섹터: {data.get('sector', 'N/A')}
        시가총액: ${data.get('market_cap', 0):,.0f}
        PER: {data.get('pe_ratio', 'N/A')}
        52주 최고/최저: {data.get('high_52w', 'N/A')} / {data.get('low_52w', 'N/A')}
        최근 뉴스: {data.get('recent_news', 'N/A')[:200]}
        """


class NewsSummaryCache:
    """뉴스 요약 캐시"""
    
    TTL = 3600 * 24  # 24시간 (뉴스는 변하지 않음)
    
    def __init__(self, compressor):
        self.compressor = compressor
    
    async def get_or_create(self, news_id: str, news_data: dict) -> str:
        """캐시된 뉴스 요약 반환 또는 새로 생성"""
        
        cache_key = f"news_summary:{news_id}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # 새로 생성
        result = await self.compressor._compress_single(
            news_data, 
            "뉴스 요약"
        )
        summary = result['compressed']
        
        cache.set(cache_key, summary, self.TTL)
        return summary
```

### 5.4 통합 파이프라인 업데이트

```python
# rag_analysis/services/pipeline_v2.py

from typing import AsyncGenerator
from .entity_extractor import EntityExtractor, EntityNormalizer
from .hybrid_search import HybridSearchService, MetadataFilterBuilder
from .graphrag_scorer import GraphRAGScorer
from .context_compressor import QuestionAwareCompressor
from .context import DateAwareContextFormatter
from .llm_service import LLMServiceLite, ResponseParser
from ..models import AnalysisSession
import logging

logger = logging.getLogger(__name__)


class AnalysisPipelineV2:
    """Phase 2 분석 파이프라인 (토큰 최적화)"""
    
    def __init__(self, session: AnalysisSession):
        self.session = session
        
        # 컴포넌트 초기화
        self.entity_extractor = EntityExtractor()
        self.entity_normalizer = EntityNormalizer()
        self.hybrid_search = HybridSearchService()
        self.graphrag_scorer = GraphRAGScorer()
        self.compressor = QuestionAwareCompressor()
        self.llm = LLMServiceLite()
    
    async def analyze(self, question: str) -> AsyncGenerator[dict, None]:
        """최적화된 분석 파이프라인"""
        
        try:
            # Stage 1: Entity Extraction
            yield {'phase': 'extracting', 'message': '질문 분석 중...'}
            
            entities = await self.entity_extractor.extract(question)
            normalized_entities = {
                'stocks': self.entity_normalizer.normalize_stocks(entities['stocks']),
                'metrics': self.entity_normalizer.normalize_metrics(entities['metrics']),
                'concepts': entities['concepts'],
                'timeframe': entities['timeframe']
            }
            
            yield {
                'phase': 'entities_extracted',
                'data': {
                    'stocks': normalized_entities['stocks'],
                    'metrics': normalized_entities['metrics']
                }
            }
            
            # Stage 2: Hybrid Search
            yield {'phase': 'searching', 'message': '관련 정보 검색 중...'}
            
            # 바구니에서 문서 가져오기
            documents = await self._get_basket_documents()
            
            # 메타데이터 필터 생성
            filters = MetadataFilterBuilder.from_entities(normalized_entities)
            
            # 하이브리드 검색
            search_results = await self.hybrid_search.search(
                question=question,
                entities=normalized_entities,
                documents=documents,
                filters=filters,
                top_k=15
            )
            
            yield {
                'phase': 'search_complete',
                'data': {'candidates': len(search_results)}
            }
            
            # Stage 3: Reranking + GraphRAG Scoring
            yield {'phase': 'ranking', 'message': '관련성 평가 중...'}
            
            top_docs = await self.graphrag_scorer.score_and_select(
                question=question,
                entities=normalized_entities,
                documents=search_results,
                top_k=3
            )
            
            yield {
                'phase': 'ranking_complete',
                'data': {'selected': len(top_docs)}
            }
            
            # Stage 4: Compression
            yield {'phase': 'compressing', 'message': '컨텍스트 최적화 중...'}
            
            compressed_docs = await self.compressor.compress(top_docs, question)
            
            total_original = sum(d['original_tokens'] for d in compressed_docs)
            total_compressed = sum(d['compressed_tokens'] for d in compressed_docs)
            
            yield {
                'phase': 'compression_complete',
                'data': {
                    'original_tokens': total_original,
                    'compressed_tokens': total_compressed,
                    'reduction': f"{(1 - total_compressed/max(total_original, 1)) * 100:.0f}%"
                }
            }
            
            # Stage 5: Build Final Context
            context = self._build_optimized_context(
                normalized_entities,
                compressed_docs,
                await self.graphrag_scorer._get_graph_context(normalized_entities)
            )
            
            # Stage 6: LLM Analysis
            yield {'phase': 'analyzing', 'message': '분석 생성 중...'}
            
            full_response = ""
            async for chunk in self.llm.generate_stream(context, question):
                if chunk['type'] == 'delta':
                    full_response += chunk['content']
                    yield {'phase': 'streaming', 'chunk': chunk['content']}
                    
                elif chunk['type'] == 'final':
                    main_content, suggestions = ResponseParser.parse_suggestions(full_response)
                    
                    yield {
                        'phase': 'complete',
                        'data': {
                            'content': main_content,
                            'suggestions': suggestions,
                            'usage': {
                                'input_tokens': chunk['input_tokens'],
                                'output_tokens': chunk['output_tokens']
                            },
                            'optimization': {
                                'original_context_tokens': total_original,
                                'optimized_context_tokens': total_compressed,
                                'token_reduction': f"{(1 - total_compressed/max(total_original, 1)) * 100:.0f}%"
                            }
                        }
                    }
                    
                elif chunk['type'] == 'error':
                    yield {'phase': 'error', 'message': chunk['message']}
                    
        except Exception as e:
            logger.error(f"Pipeline V2 error: {e}")
            yield {'phase': 'error', 'message': '분석 중 오류가 발생했습니다.'}
    
    async def _get_basket_documents(self) -> list:
        """바구니에서 문서 추출"""
        from asgiref.sync import sync_to_async
        
        basket = await sync_to_async(lambda: self.session.basket)()
        if not basket:
            return []
        
        items = await sync_to_async(list)(basket.items.all())
        
        documents = []
        for item in items:
            documents.append({
                'id': f"{item.item_type}_{item.reference_id}",
                'type': item.item_type,
                'title': item.title,
                'content': str(item.data_snapshot),
                'date': str(item.snapshot_date),
                'related_stocks': [item.reference_id] if item.item_type == 'stock' else []
            })
        
        return documents
    
    def _build_optimized_context(
        self,
        entities: dict,
        compressed_docs: list,
        graph_context: dict
    ) -> str:
        """최적화된 컨텍스트 구성"""
        
        sections = []
        
        # 그래프 컨텍스트 (간결하게)
        if graph_context['relationships']:
            graph_lines = ["## 종목 관계"]
            for rel in graph_context['relationships'][:5]:
                graph_lines.append(f"- {rel['from']} → {rel['to']} ({rel['type']})")
            sections.append('\n'.join(graph_lines))
        
        # 압축된 문서
        if compressed_docs:
            doc_lines = ["## 관련 정보"]
            for i, doc in enumerate(compressed_docs, 1):
                doc_lines.append(f"{i}. {doc.get('title', '')}: {doc['compressed']}")
            sections.append('\n'.join(doc_lines))
        
        # 엔티티 요약
        entity_summary = f"""## 분석 대상
종목: {', '.join(entities['stocks'])}
지표: {', '.join(entities['metrics']) if entities['metrics'] else '전반적 분석'}"""
        sections.append(entity_summary)
        
        return '\n\n'.join(sections)
```

### 5.5 Week 4 완료 기준

- [ ] ContextCompressor 구현
- [ ] QuestionAwareCompressor 구현
- [ ] StockSummaryCache 구현
- [ ] AnalysisPipelineV2 통합
- [ ] 토큰 절감률 측정 (목표: 68%+)

---

## 6. Phase 2 완료 기준

### 6.1 기능 체크리스트

- [ ] Entity Extraction (Haiku 기반)
- [ ] Hybrid Search (Vector + BM25 + Graph)
- [ ] Cross-Encoder Reranking
- [ ] Context Compression (Haiku 기반)
- [ ] GraphRAG 통합 점수
- [ ] 메타데이터 필터링

### 6.2 성능 체크리스트

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| 입력 토큰 | ≤ 800 | LLM 사용량 로깅 |
| 토큰 절감률 | ≥ 68% | (원본 - 압축) / 원본 |
| Reranking 시간 | ≤ 500ms | 타이머 측정 |
| 전체 파이프라인 | ≤ 8초 | TTFT 기준 |
| 검색 정확도 | Precision ≥ 0.7 | 수동 평가 |

### 6.3 품질 체크리스트

- [ ] Entity 추출 정확도 테스트
- [ ] 검색 결과 품질 평가
- [ ] Reranking 품질 평가 (nDCG)
- [ ] 압축 품질 평가 (정보 보존)
- [ ] E2E 테스트 통과

### 6.4 통합 테스트

```python
# rag_analysis/tests/test_pipeline_v2.py

import pytest
from ..services.pipeline_v2 import AnalysisPipelineV2


@pytest.mark.asyncio
async def test_token_reduction():
    """토큰 절감률 테스트"""
    # ... 테스트 구현
    
    # 목표: 68% 이상 절감
    assert token_reduction >= 0.68


@pytest.mark.asyncio
async def test_pipeline_latency():
    """파이프라인 지연 시간 테스트"""
    # ... 테스트 구현
    
    # 목표: 8초 이내
    assert latency_seconds <= 8
```

---

## 📎 Phase 3 예고

Phase 2 완료 후, Phase 3에서는 다음을 구현합니다:

- Semantic Cache (Neo4j Vector Index)
- 캐시 워밍 및 무효화
- 성능 모니터링 대시보드
- 비용 최적화 (모델 분리)

→ `AI_ANALYSIS_v4.3_PHASE3.md` 참조

---

*Phase 2 - Token Optimization Core*
*v4.3.0 - 2025-12-13*