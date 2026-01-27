# Reranking 시스템 가이드

Phase 2 Week 3: Cross-Encoder 기반 재순위화 및 GraphRAG 통합 스코어링

## 개요

이 모듈은 검색 결과를 고급 스코어링 기법으로 재순위화하여 최상의 문서를 선별합니다.

### 구성 요소

1. **CrossEncoderReranker**: Cross-Encoder 모델 기반 재순위화
2. **RerankerWithThreshold**: 임계값 필터링 추가 재순위화
3. **GraphRAGScorer**: Cross-Encoder + Graph 관계 + 최신성 통합 스코어링

---

## 1. CrossEncoderReranker

### 기능

- MS MARCO 사전학습 모델 (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- 질문-문서 쌍의 관련성 점수 계산
- 싱글톤 패턴으로 모델 재사용 (메모리 효율)

### 사용법

```python
from rag_analysis.services import CrossEncoderReranker

# 인스턴스 생성 (싱글톤)
reranker = CrossEncoderReranker()

# 문서 재순위화
documents = [
    ({'title': 'AAPL Q4 실적', 'content': '...'}, 0.85, {}),
    ({'title': 'MSFT 클라우드', 'content': '...'}, 0.75, {}),
    ({'title': 'NVDA GPU', 'content': '...'}, 0.65, {}),
]

question = "AAPL 재무 분석"
reranked = reranker.rerank(question, documents, top_k=2)

# 결과
# [
#     ({'title': 'AAPL Q4 실적', ...}, 0.92, {'rerank': 0.92, 'original_score': 0.85}),
#     ({'title': 'MSFT 클라우드', ...}, 0.68, {'rerank': 0.68, 'original_score': 0.75})
# ]
```

### 주요 파라미터

- `question`: 사용자 질문
- `documents`: `(document, score, breakdown)` 튜플 리스트
- `top_k`: 반환할 상위 문서 수

---

## 2. RerankerWithThreshold

### 기능

- CrossEncoderReranker 래핑
- 최소 점수 임계값 필터링
- 최소 문서 수 보장

### 사용법

```python
from rag_analysis.services import get_reranker

# 임계값 필터링 포함 reranker
reranker = get_reranker(with_threshold=True, threshold=0.6)

# 재순위화 + 필터링
reranked = reranker.rerank(
    question="NVDA GPU 분석",
    documents=documents,
    top_k=3,
    min_docs=1  # 최소 보장 문서 수
)

# 점수 0.6 이상 문서만 반환, 없으면 상위 1개 보장
```

### 주요 파라미터

- `threshold`: 최소 점수 임계값 (0.0 ~ 1.0)
- `min_docs`: 최소 보장 문서 수 (임계값 미달이어도 반환)

---

## 3. GraphRAGScorer (통합 스코어링)

### 기능

- **Cross-Encoder**: 의미 관련성 (가중치 0.5)
- **Graph 관계**: Neo4j 연결 강도 (가중치 0.3)
- **최신성**: 시간 가중치 (가중치 0.2)

### 사용법

```python
from rag_analysis.services import GraphRAGScorer, ScoringWeights

# 기본 가중치 사용
scorer = GraphRAGScorer()

# 커스텀 가중치
weights = ScoringWeights(rerank=0.6, graph_rel=0.2, recency=0.2)
scorer = GraphRAGScorer(weights=weights)

# 통합 스코어링
documents = [
    ({'symbol': 'AAPL', 'date': '2024-01-15', 'content': '...'}, 0.8, {}),
    ({'symbol': 'NVDA', 'date': '2024-01-10', 'content': '...'}, 0.7, {}),
]

scored = scorer.score(
    question="AAPL 공급망 분석",
    documents=documents,
    symbol="AAPL",  # Graph 검색 기준
    top_k=3,
    use_graph=True,
    use_recency=True
)

# 결과
# [
#     (
#         {'symbol': 'AAPL', 'date': '2024-01-15', ...},
#         0.95,  # 최종 점수
#         {
#             'rerank_normalized': 0.9,
#             'graph_relation': 1.0,  # 동일 심볼
#             'recency': 1.0,  # 오늘
#             'final_score': 0.95,
#             'weights': {'rerank': 0.5, 'graph_rel': 0.3, 'recency': 0.2}
#         }
#     ),
#     ...
# ]
```

### Graph 관계 점수 로직

| 관계 | 점수 |
|-----|------|
| 동일 심볼 | 1.0 |
| Supply chain | strength 값 (0.5 ~ 1.0) |
| Competitor | overlap_score × 0.8 |
| Sector peer | 0.6 |
| 무관계 | 0.0 |

### 최신성 점수 로직

| 기간 | 점수 |
|-----|------|
| 오늘 | 1.0 |
| 1주일 이내 | 0.9 |
| 1개월 이내 | 0.7 |
| 3개월 이내 | 0.5 |
| 1년 이내 | 0.3 |
| 1년 이상 | 0.1 |
| 날짜 없음 | 0.5 (중립) |

---

## 파이프라인 통합 예시

### 하이브리드 검색 + 재순위화

```python
from rag_analysis.services import (
    HybridSearchService,
    GraphRAGScorer
)

# 1. 하이브리드 검색
hybrid_search = HybridSearchService()
search_results = hybrid_search.search(
    query="AAPL 재무 분석",
    documents=all_documents,
    top_k=10,
    symbol="AAPL"
)

# 2. GraphRAG 재순위화
scorer = GraphRAGScorer()
final_results = scorer.score(
    question="AAPL 재무 분석",
    documents=[
        (res['document'], res['score'], res['scores'])
        for res in search_results
    ],
    symbol="AAPL",
    top_k=3
)

# 3. 최종 Top-3 문서 선별 완료
```

### Context Builder 통합

```python
from rag_analysis.services import (
    GraphRAGScorer,
    DateAwareContextFormatter
)

# 1. 재순위화로 Top-K 선별
scorer = GraphRAGScorer()
top_docs = scorer.score(question, documents, symbol, top_k=5)

# 2. Context Builder에 전달
context_formatter = DateAwareContextFormatter()
context = context_formatter.format_context(
    question=question,
    documents=[doc for doc, _, _ in top_docs],
    max_tokens=8000
)
```

---

## 의존성

```bash
# sentence-transformers 설치
pip install sentence-transformers

# 또는 poetry
poetry add sentence-transformers
```

---

## 성능 고려사항

### 모델 초기화

- 최초 호출 시 모델 다운로드 (~80MB)
- 이후 호출은 싱글톤 캐시 사용
- 메모리 사용량: ~300MB (모델 로드 시)

### 추론 속도

- Cross-Encoder는 문서별 개별 추론 필요
- 10개 문서 재순위화: ~100ms (CPU)
- 100개 문서 재순위화: ~1000ms (CPU)
- GPU 사용 권장 (프로덕션 환경)

### 최적화 팁

1. **Top-K 제한**: `top_k`를 작게 설정 (3~10)
2. **배치 처리**: 대량 문서는 배치로 분할
3. **캐싱**: 동일 질문-문서 쌍은 캐싱 고려

---

## 테스트

```bash
# Reranker 테스트
pytest rag_analysis/tests/test_reranker.py -v

# GraphRAG Scorer 테스트
pytest rag_analysis/tests/test_graphrag_scorer.py -v

# 전체 테스트
pytest rag_analysis/tests/test_reranker.py rag_analysis/tests/test_graphrag_scorer.py -v
```

---

## 참고 자료

- [Cross-Encoder 논문](https://arxiv.org/abs/1908.10084)
- [MS MARCO 데이터셋](https://microsoft.github.io/msmarco/)
- [Sentence-Transformers 문서](https://www.sbert.net/docs/pretrained_cross-encoders.html)
