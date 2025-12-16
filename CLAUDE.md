# CLAUDE.md - Stock-Vis

## 프로젝트 개요

**Stock-Vis**: AI 기반 투자 분석 플랫폼

- **Backend**: Django REST Framework + PostgreSQL
- **Frontend**: Next.js 14+ (TypeScript)
- **Async**: Celery + Redis
- **LLM**: Claude API (RAG 분석)

---

## 개발 환경 설정

### Backend

```bash
# 의존성 설치
poetry install

# 환경 변수 (.env 파일)
ALPHA_VANTAGE_API_KEY=your_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/stock_vis

# 데이터베이스
createdb stock_vis
python manage.py migrate

# 서버 실행
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # 개발 서버
npm run build      # 프로덕션 빌드
```

### 비동기 작업 (Celery + Redis)

```bash
# Redis 시작
brew services start redis

# Celery Worker/Beat 실행
celery -A config worker -l info
celery -A config beat -l info
```

---

## 아키텍처

### 전체 구조

```
Frontend (Next.js) ──REST API──▶ Backend (Django)
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
             Alpha Vantage      PostgreSQL        ML Models
               yfinance          (Data)           (예정)
```

### Backend 3계층 패턴

```
API Client → Processor → Service → Models/Views → REST API
```

- **Client**: 외부 API 통신 (Rate limiting, 에러 핸들링)
- **Processor**: 응답 데이터 변환 (snake_case 변환, 타입 처리)
- **Service**: 트랜잭션 관리, 데이터베이스 저장

### Django 앱 구조

| 앱 | 역할 | URL |
|----|------|-----|
| stocks | 주가, 재무제표 데이터 | `/api/v1/stocks/*` |
| users | 사용자, 포트폴리오 관리 | `/api/v1/users/*` |
| analysis | 기술적 지표, 시장 분석 | `/api/v1/analysis/*` |
| macro | 거시경제 대시보드 (Market Pulse) | `/api/v1/macro/*` |
| rag_analysis | LLM 기반 분석 | `/api/v1/rag/*` |

### 모델 관계

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

---

## 주요 API 엔드포인트

### 주식 데이터

- `GET /api/v1/stocks/api/chart/<symbol>/` - 차트 데이터
- `GET /api/v1/stocks/api/overview/<symbol>/` - 기업 개요
- `GET /api/v1/stocks/api/balance-sheet/<symbol>/` - 재무상태표
- `GET /api/v1/stocks/api/income-statement/<symbol>/` - 손익계산서
- `GET /api/v1/stocks/api/cashflow/<symbol>/` - 현금흐름표
- `GET /api/v1/stocks/api/indicators/<symbol>/` - 기술적 지표

### Watchlist (관심종목)

- `GET /api/v1/users/watchlist/` - 관심종목 리스트 목록
- `POST /api/v1/users/watchlist/` - 관심종목 리스트 생성
- `GET /api/v1/users/watchlist/<id>/` - 관심종목 리스트 상세
- `PATCH /api/v1/users/watchlist/<id>/` - 관심종목 리스트 수정
- `DELETE /api/v1/users/watchlist/<id>/` - 관심종목 리스트 삭제
- `POST /api/v1/users/watchlist/<id>/add-stock/` - 종목 추가
- `GET /api/v1/users/watchlist/<id>/stocks/` - 종목 목록 + 실시간 가격
- `PATCH /api/v1/users/watchlist/<id>/stocks/<symbol>/` - 종목 설정 수정
- `DELETE /api/v1/users/watchlist/<id>/stocks/<symbol>/remove/` - 종목 제거

### Market Pulse (거시경제)

- `GET /api/v1/macro/pulse/` - 전체 대시보드
- `GET /api/v1/macro/fear-greed/` - 공포/탐욕 지수
- `GET /api/v1/macro/interest-rates/` - 금리/수익률 곡선
- `GET /api/v1/macro/global-markets/` - 글로벌 시장
- `POST /api/v1/macro/sync/` - 데이터 동기화 시작
- `GET /api/v1/macro/sync/status/` - 동기화 상태 확인

---

## 코딩 규칙

### Backend

- 심볼 처리: `symbol.upper()` 필수
- 모델 조회: `get_object_or_404(Stock, symbol=symbol.upper())`
- Processor: 반드시 `return` 문 포함
- 기간 타입: `period_type='annual'` 또는 `'quarterly'`
- 가격 모델: `DailyPrice` 사용 (`HistoricalPrice` 없음)

### Frontend

- TypeScript strict mode
- 서버 상태: TanStack Query
- 클라이언트 상태: Zustand
- `'use client'` 필요한 컴포넌트만

### 비동기 (Celery)

- Rate limiting: Alpha Vantage 12초 간격
- 태스크 idempotent 구현
- 재시도: max_retries=3, exponential backoff

---

## 외부 API

### Alpha Vantage

- 무료 티어: 5 calls/분, 500 calls/일
- 요청 간 12초 대기 필수
- 응답: camelCase → Processor가 snake_case로 변환

### yfinance (Yahoo Finance)

FMP API 대체용 - 무료, Rate limit 없음

```python
# 주요 심볼
INDEX_SYMBOLS = {'^GSPC': 'S&P 500', '^DJI': 'Dow Jones', '^IXIC': 'NASDAQ'}
SECTOR_ETFS = {'XLK': 'Technology', 'XLF': 'Financials', ...}
COMMODITIES = {'GC=F': 'Gold', 'CL=F': 'Crude Oil', ...}
FOREX = {'EURUSD=X': 'EUR/USD', 'KRW=X': 'USD/KRW', ...}
```

---

## 캐싱 전략

| 데이터 타입 | TTL | 비고 |
|-----------|-----|------|
| 차트 데이터 | 60초 | 실시간성 중요 |
| Overview | 600초 | 가격 + 기본 정보 |
| 재무제표 | 3600초 | 분기/연간 업데이트 |
| 거시경제 지표 | 3600초 | FRED 데이터 |
| Watchlist 목록 | 300초 | 사용자별 캐시 키 |
| Watchlist 종목 | 60초 | 실시간 가격 포함 |

---

## 자주 발생하는 버그

1. Processor 메서드에서 return문 누락
2. `DailyPrice` 대신 `HistoricalPrice` 사용
3. 심볼에 `.upper()` 호출 누락
4. Alpha Vantage None/빈 값 처리 누락
5. N+1 쿼리 문제 (select_related/prefetch_related 미사용)
6. **SSE Async Loop 충돌**: Django ASGI(Daphne)에서 동기 뷰 내 `asyncio.new_event_loop()` 사용 시 연결 끊김
   - 증상: "Application instance took too long to shut down" 에러, 요청 pending
   - 해결: 비동기 이벤트를 먼저 수집 후 동기적으로 yield하거나, 완전한 async 뷰 사용

---

## 멀티에이전트 시스템

### 에이전트 담당 영역

| 에이전트 | 담당 영역 |
|---------|----------|
| @backend | stocks/, users/, analysis/, API_request/ |
| @frontend | frontend/ 전체 |
| @rag-llm | rag_analysis/ 전체 |
| @infra | */tasks.py, */consumers.py, config/, docker/ |
| @qa | tests/, docs/ |
| @investment-advisor | 투자 도메인 콘텐츠 |

### 워크플로우

1. Orchestrator가 작업 분배 미리보기 제공
2. 사용자 확인 후 에이전트 순차 호출
3. 에이전트 완료/도움 요청 시 사용자가 조율

---

## RAG Analysis (AI 분석) - Phase 3

### 파이프라인 버전

| 버전 | 설명 | API 파라미터 |
|------|------|-------------|
| lite | 기존 바구니 기반 | `?pipeline=lite` |
| v2 | RAG 기반 (Entity + Hybrid Search) | `?pipeline=v2` |
| **final** | **Phase 3 통합 (권장)** | `?pipeline=final` |

### AnalysisPipelineFinal 스테이지

| Stage | 컴포넌트 | 역할 |
|-------|---------|------|
| 0 | Semantic Cache | 유사 질문 캐시 (SIMILARITY=0.85) |
| 1 | Complexity Classifier | 질문 복잡도 분류 |
| 2 | Token Budget Manager | 토큰 예산 할당 |
| 3 | Adaptive LLM | 복잡도 기반 모델 선택 |
| 4 | Cost Tracker | 비용 추적 및 로깅 |

### 복잡도별 설정

| 복잡도 | max_tokens | context 예산 |
|--------|------------|-------------|
| simple | 800 | 400 |
| moderate | 1500 | 800 |
| complex | 2500 | 1500 |

### 모니터링 API

```bash
GET /api/v1/rag/monitoring/usage/?hours=24   # 사용량 통계
GET /api/v1/rag/monitoring/cost/             # 비용 요약
GET /api/v1/rag/monitoring/cache/            # 캐시 통계
```

---

## 구현 완료 기능

- ✅ JWT 인증 시스템
- ✅ 포트폴리오 CRUD
- ✅ 기술적 지표 (RSI, MACD, Bollinger Bands 등)
- ✅ Alpha Vantage API 통합
- ✅ WebSocket 실시간 통신
- ✅ Celery 비동기 태스크
- ✅ Redis 캐싱
- ✅ 차트 UX (Nice Numbers, 색상 테마, 반응형)
- ✅ Market Pulse 거시경제 대시보드
- ✅ yfinance 글로벌 시장 데이터
- ✅ Watchlist 관심종목 관리 (목표가, 메모, 실시간 가격)
- ✅ RAG Analysis Phase 3 (Semantic Cache, Cost Optimization)
- ⏳ ML/DL 모델 통합
- ⏳ PostgreSQL 마이그레이션

---

## 로깅

- 로그 파일: `stocks.log`
- 사용법: `logger = logging.getLogger(__name__)`
