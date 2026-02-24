# RAG Analysis (AI 분석) - Phase 3

## 파이프라인 버전

| 버전 | 설명 | API 파라미터 |
|------|------|-------------|
| lite | 기존 바구니 기반 | `?pipeline=lite` |
| v2 | RAG 기반 (Entity + Hybrid Search) | `?pipeline=v2` |
| **final** | **Phase 3 통합 (권장)** | `?pipeline=final` |

## AnalysisPipelineFinal 스테이지

| Stage | 컴포넌트 | 역할 |
|-------|---------|------|
| 0 | Semantic Cache | 유사 질문 캐시 (SIMILARITY=0.85) |
| 1 | Complexity Classifier | 질문 복잡도 분류 |
| 2 | Token Budget Manager | 토큰 예산 할당 |
| 3 | Adaptive LLM | 복잡도 기반 모델 선택 |
| 4 | Cost Tracker | 비용 추적 및 로깅 |

## 복잡도별 설정

| 복잡도 | max_tokens | context 예산 |
|--------|------------|-------------|
| simple | 800 | 400 |
| moderate | 1500 | 800 |
| complex | 2500 | 1500 |

## 모니터링 API

```bash
GET /api/v1/rag/monitoring/usage/?hours=24   # 사용량 통계
GET /api/v1/rag/monitoring/cost/             # 비용 요약
GET /api/v1/rag/monitoring/cache/            # 캐시 통계
```
