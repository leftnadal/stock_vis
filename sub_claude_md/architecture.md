# 아키텍처

## 전체 구조

```
Frontend (Next.js) ──REST API──▶ Backend (Django)
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
             Alpha Vantage      PostgreSQL        ML Models
               yfinance          (Data)           (예정)
```

## Backend 3계층 패턴

```
API Client → Processor → Service → Models/Views → REST API
```

- **Client**: 외부 API 통신 (Rate limiting, 에러 핸들링)
- **Processor**: 응답 데이터 변환 (snake_case 변환, 타입 처리)
- **Service**: 트랜잭션 관리, 데이터베이스 저장

## Django 앱 구조

| 앱 | 역할 | URL |
|----|------|-----|
| stocks | 주가, 재무제표 데이터 | `/api/v1/stocks/*` |
| users | 사용자, 포트폴리오 관리, Watchlist | `/api/v1/users/*` |
| analysis | 기술적 지표, 시장 분석 | `/api/v1/analysis/*` |
| macro | 거시경제 대시보드 (Market Pulse) | `/api/v1/macro/*` |
| news | 뉴스 기반 종목 인사이트, 수집 카테고리 | `/api/v1/news/*` |
| graph_analysis | 그래프 온톨로지 상관관계 분석 (모델/서비스만, API 미구현) | ⏳ `/api/v1/graph/*` |
| rag_analysis | LLM 기반 RAG 분석 | `/api/v1/rag/*` |
| serverless | Market Movers, Screener, Chain Sight, 키워드 | `/api/v1/serverless/*` |

## 모델 관계

```
Stock (PK: symbol)
  ├── DailyPrice (FK: stock, unique: stock+date)
  ├── WeeklyPrice (FK: stock, unique: stock+date)
  ├── BalanceSheet (FK: stock, unique: stock+period_type+fiscal_year+fiscal_quarter)
  ├── IncomeStatement (FK: stock, unique: stock+period_type+fiscal_year+fiscal_quarter)
  └── CashFlowStatement (FK: stock, unique: stock+period_type+fiscal_year+fiscal_quarter)

User
  └── Watchlist (FK: user, unique: user+name)
        └── WatchlistItem (FK: watchlist+stock, unique: watchlist+stock)
              - target_entry_price: 목표 진입가
              - notes: 메모
              - position_order: 정렬 순서
```
