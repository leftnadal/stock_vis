# DC-2: ETF Holdings → Neo4j Theme

> **완료일**: 2026-04-04

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `chainsight/management/commands/load_themes_to_neo4j.py` | ETF→Theme 변환 + Neo4j 로드 |

## 데이터 원천

기존 `serverless/models.py`의 ETFProfile (21개) + ETFHolding (4,915건) 활용.
Finnhub ETF Holdings 403 → 운용사 CSV 기반 데이터 이미 적재됨 (decisions/003).

## 결과

### Neo4j :Theme 노드 (21개)

| 종류 | 테마 | ETF |
|------|------|-----|
| Theme | Semiconductor | SOXX |
| Theme | Robotics & AI | BOTZ |
| Theme | Clean Energy | ICLN |
| Theme | Lithium & Battery | LIT |
| Theme | Disruptive Innovation | ARKK |
| Theme | Genomic Revolution | ARKG |
| Theme | Cybersecurity | HACK |
| Theme | Sports Betting & Gaming | BETZ |
| Theme | China Internet | KWEB |
| Theme | Solar Energy | TAN |
| Sector | Technology, Healthcare, Financials, Energy 등 11개 | XLK~XLB |

### HAS_THEME 관계 (534개)

상위 테마:
- Industrials: 80 stocks
- Financials: 76 stocks
- Technology: 73 stocks
- Healthcare: 60 stocks
- Semiconductor: 17 stocks

### 샘플 (NVDA)
```
NVDA → Technology (15.4%, XLK)
NVDA → Semiconductor (8.2%, SOXX)
NVDA → Robotics & AI (8.1%, BOTZ)
```

## Neo4j 전체 현황

| 노드/관계 | 건수 |
|-----------|------|
| :Stock | 597 |
| :Sector | 17 |
| :Industry | 127 |
| :Theme | **21** (신규) |
| :NewsEvent | 100 |
| PEER_OF | 8,350 |
| BELONGS_TO | 1,038 |
| RELATED_TO | 1,631 |
| **HAS_THEME** | **534** (신규) |
| CUSTOMER_OF | 2 |

→ **M1.5 마일스톤 달성**: "관계가 풍부해짐" — ETF Theme + Supply Chain 추가

## 다음 작업

→ CS-5 Frontend 그래프 시각화
