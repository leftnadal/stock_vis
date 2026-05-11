# CS-4-1~4-3: Chain Sight REST API

> **완료일**: 2026-04-03
> **마일스톤**: M4 달성

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `chainsight/api/views.py` | ChainSightGraphView, ChainSightSuggestionView, ChainSightTraceView |
| `chainsight/api/urls.py` | 3개 엔드포인트 |
| `config/urls.py` (수정) | `/api/v1/chainsight/` include |

## API 엔드포인트

### CS-4-1: Graph Exploration
```
GET /api/v1/chainsight/{symbol}/graph/
```
- 지정 종목의 Neo4j 이웃 그래프 반환
- depth, rel_types 파라미터 지원
- 응답: nodes[], edges[], center_node

### CS-4-2: Suggestion
```
GET /api/v1/chainsight/{symbol}/suggestions/
```
- Chain Sight 프로파일 기반 관련 종목 추천
- GrowthStage, CapitalDNA, sector 유사도 기반
- 응답: suggestions[] (symbol, name, reason, score)

### CS-4-3: Trace
```
POST /api/v1/chainsight/trace/
Body: {"from": "AAPL", "to": "TSM"}
```
- 두 종목 간 관계 경로 추적
- Neo4j shortestPath 활용
- 응답: path[], relationship_types[], total_confidence

## 다음 작업

→ CS-5 Frontend (그래프 시각화) 또는 SEC Pipeline
