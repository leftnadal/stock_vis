# CS-3-3: GDS 알고리즘 배치

> **완료일**: 2026-04-18
> **상태**: 이미 구현됨 — 검증 완료

## GDS 환경

- **GDS version**: 2.13.2 ✅
- **노드 수**: 532개 (pagerank/community/betweenness 모두 적용)

## PageRank Top 10

| # | 종목 | 이름 | PageRank |
|---|------|------|---------|
| 1 | MSFT | Microsoft | 1.9234 |
| 2 | META | Meta Platforms | 1.8933 |
| 3 | CSCO | Cisco Systems | 1.8602 |
| 4 | GOOGL | Alphabet | 1.8377 |
| 5 | MSI | Motorola Solutions | 1.8319 |
| 6 | HPE | Hewlett Packard Enterprise | 1.8290 |
| 7 | GOOG | Alphabet | 1.7093 |
| 8 | AAPL | Apple | 1.6148 |
| 9 | EA | Electronic Arts | 1.6130 |
| 10 | GEHC | GE HealthCare | 1.6015 |

## Community Detection

- **총 커뮤니티 수**: 23개
- 최대 커뮤니티: 98 stocks (Community 184)
- 섹터 기반 클러스터링 패턴 확인

## Betweenness Top 5

| 종목 | Betweenness |
|------|------------|
| ACGL | 24,351.5 |
| AVGO | 22,374.1 |
| ABNB | 22,339.3 |
| ADP | 17,151.3 |
| LLY | 16,139.8 |

★ M3 달성: "Neo4j가 풍부해짐"

→ 다음: cs_41 (Phase 4 시작)
