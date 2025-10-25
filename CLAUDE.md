# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**프로젝트명**: Stock-Vis (인공지능이 도와주는 투자분석 페이지)

Alpha Vantage API를 통해 수집된 미국 주식 데이터(주가, 재무제표, 기업 정보)를 기반으로 머신러닝/딥러닝 모델을 활용한 퀀트 투자 분석 플랫폼입니다.

**기술 스택**:
- Backend: Django REST Framework (Python 3.12+)
- Frontend: Next.js + TypeScript (예정)
- Database: PostgreSQL (예정, 현재는 SQLite 사용 중)
- ML/DL: 투자 예측 및 분석 모델 (개발 예정)

## 개발 환경 설정

### Backend (Django)

**의존성 관리**: Poetry 사용 (`pyproject.toml` 참조)
- Python 3.12+
- Django 5.1.7
- Django REST Framework
- psycopg2-binary (PostgreSQL 연결용, 추가 예정)

**환경 설정**:
```bash
# 의존성 설치
poetry install

# PostgreSQL 설치 (macOS)
brew install postgresql@15
brew services start postgresql@15

# 환경 변수 설정 (필수)
export ALPHA_VANTAGE_API_KEY=your_key_here
export DATABASE_URL=postgresql://user:password@localhost:5432/stock_vis
# 또는 .env 파일 생성:
# ALPHA_VANTAGE_API_KEY=your_key_here
# DATABASE_URL=postgresql://user:password@localhost:5432/stock_vis

# 데이터베이스 생성
createdb stock_vis

# 마이그레이션 실행
python manage.py migrate

# 백엔드 개발 서버 실행
python manage.py runserver

# 시스템 체크
python manage.py check
```

### Frontend (Next.js + TypeScript, 예정)

```bash
# 프론트엔드 디렉토리로 이동
cd frontend

# 의존성 설치
npm install
# 또는
yarn install

# 개발 서버 실행
npm run dev
# 또는
yarn dev

# 프로덕션 빌드
npm run build
# 또는
yarn build
```

**데이터베이스**: PostgreSQL (권장) / SQLite (현재 개발 환경)

## 아키텍처

### 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                      │
│  - TypeScript                                               │
│  - React Components                                         │
│  - TanStack Query (데이터 페칭)                             │
│  - Recharts/TradingView (차트 라이브러리)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ REST API
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend (Django REST Framework)                │
│  - API Endpoints (stocks, users, analysis)                 │
│  - Authentication & Authorization                           │
│  - Caching Layer (Redis 예정)                              │
│  - ML Model Serving (예정)                                 │
└─────────────────────────────────────────────────────────────┘
         │                              │
         │ Data Collection              │ ML/DL Processing
         ▼                              ▼
┌──────────────────────┐    ┌──────────────────────────┐
│  Alpha Vantage API   │    │   ML/DL Models (예정)    │
│  - Stock Quotes      │    │   - 가격 예측            │
│  - Financial Data    │    │   - 패턴 인식            │
│  - Company Info      │    │   - 포트폴리오 최적화    │
└──────────────────────┘    └──────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │  PostgreSQL Database │
                    │  - Stock Data        │
                    │  - Financial Records │
                    │  - ML Predictions    │
                    └──────────────────────┘
```

### Backend 3계층 데이터 플로우 패턴

외부 API 통합을 위한 일관된 3계층 아키텍처를 따릅니다:

```
API Client → Processor → Service → Django Models/Views → REST API
```

**1계층: Client** (`API request/alphavantage_client.py`)
- Alpha Vantage API와 직접 통신
- Rate limiting 처리 (무료 티어: 요청 간 12초 대기)
- API 응답 에러 핸들링
- 메서드: `get_stock_quote()`, `get_company_overview()`, `get_daily_stock_data()`, `get_balance_sheet()` 등

**2계층: Processor** (`API request/alphavantage_processor.py`)
- API 응답을 데이터베이스 저장 가능한 형태로 변환
- 각 데이터 타입별 정적 메서드: `process_stock_quote()`, `process_company_overview()`, `process_historical_prices()` 등
- 안전 변환 유틸리티: `_safe_decimal()`, `_safe_int()`, `_safe_date()` - None, 빈 문자열, 잘못된 데이터 처리
- **중요**: 모든 processor 메서드는 반드시 처리된 데이터를 return해야 함 (return문 누락 주의)

**3계층: Service** (`API request/alphavantage_service.py`)
- Client + Processor + 데이터베이스 작업을 조율
- 배치 저장을 위한 트랜잭션 관리
- 메서드: `update_stock_data()`, `update_historical_prices()`, `update_financial_statements()` 등
- 중복 방지를 위해 `update_or_create()` 사용

### Backend Django 앱 구조

**stocks** (핵심 데이터 앱):
- 모델: `Stock`, `DailyPrice`, `WeeklyPrice`, `BalanceSheet`, `IncomeStatement`, `CashFlowStatement`
- 뷰에서 다른 TTL로 캐싱 구현:
  - 차트 데이터: 60초 (실시간성 중요)
  - Overview: 600초 (10분 - 가격 + 기본 정보)
  - 재무제표: 3600초 (1시간 - 분기/연간 업데이트)
- URL 패턴: `/api/v1/stocks/*`
- **PostgreSQL 최적화**: 대용량 시계열 데이터 처리를 위한 인덱싱 필수

**users**:
- 커스텀 유저 모델: `AUTH_USER_MODEL = 'users.User'`
- 포트폴리오, 관심종목, 알림 설정 관리
- URL 패턴: `/api/v1/users/*`

**analysis** (ML/DL 통합 예정):
- 경제 지표 및 시장 분석
- **예정**: ML 모델 예측 결과 저장 및 제공
- **예정**: 기술적 지표 계산 (RSI, MACD, Bollinger Bands 등)
- **중요**: `DailyPrice` 모델 사용, `HistoricalPrice`는 존재하지 않음
- URL 패턴: `/api/v1/analysis/*`

**ml_models** (앱 생성 예정):
- 머신러닝/딥러닝 모델 관리
- 모델 학습, 평가, 예측 파이프라인
- 모델: `PredictionModel`, `TrainingHistory`, `ModelPrediction` 등

### 모델 관계도

```
Stock (PK: symbol)
  ├── DailyPrice (FK: stock, unique: stock+date)
  ├── WeeklyPrice (FK: stock, unique: stock+date)
  ├── BalanceSheet (FK: stock, unique: stock+period_type+fiscal_year+fiscal_quarter)
  ├── IncomeStatement (FK: stock, unique: stock+period_type+fiscal_year+fiscal_quarter)
  └── CashFlowStatement (FK: stock, unique: stock+period_type+fiscal_year+fiscal_quarter)
```

모든 가격/재무 모델은 `to_field='symbol'`과 `on_delete=models.CASCADE`로 Stock에 ForeignKey 연결됨.

### 캐싱 전략

두 가지 캐싱 구현이 존재:

1. **기본 캐싱** (현재 `stocks/views.py`에서 사용):
   - Django 기본 캐시 백엔드 (현재 로컬 메모리)
   - 단순한 캐시 키: `f"chart_{symbol}_{type}_{period}"`
   - 각 뷰에서 수동으로 cache get/set

2. **보안 강화 캐싱** (`stocks/cache_utils.py`):
   - `SecureStockCache` 클래스 - 검증, 로깅, 해시 키 생성
   - 데코레이터 패턴: `@secure_cached_api(cache_type='...', timeout=...)`
   - 입력값 검증, 레이트 리미팅, DoS 방지
   - 구현되었으나 아직 완전히 통합되지 않음

**프로덕션 환경 계획**:
- Redis 캐시 백엔드로 변경 예정
- Celery + Redis를 활용한 비동기 작업 처리
- ML 모델 예측 결과 캐싱

## API 엔드포인트

### Backend REST API

모든 엔드포인트는 URL 경로에 symbol 사용 (예: `/api/v1/stocks/api/chart/AAPL/`)

**차트 데이터**: `/api/v1/stocks/api/chart/<symbol>/`
- 쿼리 파라미터: `type` (daily/weekly), `period` (1d, 5d, 1m, 3m, 6m, 1y, 2y, 5y, max), `days` (커스텀)
- 응답 형식: Next.js 차트 라이브러리에 최적화된 JSON

**재무 탭**: `/api/v1/stocks/api/{overview|balance-sheet|income-statement|cashflow}/<symbol>/`
- 쿼리 파라미터: `period` (annual/quarterly), `limit` (기본값 5)

**ML 예측 (예정)**: `/api/v1/analysis/predict/<symbol>/`
- 쿼리 파라미터: `model_type` (price_prediction, trend_analysis, risk_assessment)
- 응답: 예측값, 신뢰도, 시각화 데이터

### Frontend-Backend 통신

**데이터 페칭 패턴** (Next.js):
```typescript
// TanStack Query 사용 예시
const { data, isLoading } = useQuery({
  queryKey: ['stock', symbol, 'chart', period],
  queryFn: () => fetch(`/api/v1/stocks/api/chart/${symbol}/?period=${period}`)
})
```

**TypeScript 타입 정의**:
- Backend serializer에서 생성된 JSON 스키마를 TypeScript 타입으로 변환
- `api/types.ts`에 중앙 집중식 타입 정의 (예정)

## 일반적인 패턴 및 주의사항

### PostgreSQL 마이그레이션 시 주의사항

현재 SQLite에서 PostgreSQL로 전환 예정:

1. **데이터 타입 차이**:
   - SQLite의 유연한 타입 시스템과 달리 PostgreSQL은 엄격함
   - `DecimalField`의 `max_digits`, `decimal_places` 검증 강화
   - `DateField`, `DateTimeField`의 타임존 처리 주의

2. **마이그레이션 전략**:
   ```bash
   # 기존 데이터 덤프
   python manage.py dumpdata > backup.json

   # PostgreSQL 설정 후 마이그레이션
   python manage.py migrate

   # 데이터 복원
   python manage.py loaddata backup.json
   ```

3. **인덱스 최적화**:
   - 시계열 데이터(`DailyPrice`, `WeeklyPrice`)에 대한 복합 인덱스 추가
   - `Stock.symbol`, `date` 필드 조합 인덱싱 필수
   - PostgreSQL 특화 인덱스 타입 고려 (B-tree, GiST 등)

### ML/DL 모델 통합 시

1. **모델 저장 및 버전 관리**:
   - 학습된 모델 파일은 `media/ml_models/` 디렉토리에 저장
   - 모델 버전별로 성능 메트릭 기록
   - 프로덕션 배포 전 백테스팅 필수

2. **예측 파이프라인**:
   - 실시간 예측: Celery 비동기 작업으로 처리
   - 배치 예측: Django management command로 스케줄링
   - 예측 결과 캐싱으로 API 응답 속도 개선

3. **데이터 전처리**:
   - 주가 데이터 정규화/스케일링
   - 결측치 처리 (forward fill, interpolation)
   - Feature engineering (기술적 지표 계산)

### 새 데이터 타입 추가 시

1. `alphavantage_processor.py`에 processor 메서드 생성 - **return문 누락 금지**
2. `alphavantage_service.py`에 transaction.atomic()과 함께 service 메서드 추가
3. 적절한 unique_together 제약조건으로 모델 생성/업데이트
4. 기존 명명 규칙 따라 시리얼라이저 추가: 탭용은 `<Model>TabSerializer`, 일반용은 `<Model>Serializer`
5. **Frontend 타입 정의**: TypeScript 인터페이스 생성 및 동기화

### Backend 모델 작업 시

- `Stock.symbol`이 기본 키 (CharField, AutoField 아님)
- `get_object_or_404(Stock, symbol=symbol.upper())` 사용 - 항상 심볼을 대문자로
- 재무 데이터 기간: `period_type='annual'` 또는 `'quarterly'` 사용, `'quarter'` 아님
- 가격 데이터: `DailyPrice`와 `WeeklyPrice`는 `BasePriceData` 추상 모델 상속
- **PostgreSQL 전환 시**: 대용량 시계열 데이터 쿼리 최적화 필요 (select_related, prefetch_related 활용)

### Frontend 컴포넌트 작업 시 (예정)

- **차트 컴포넌트**: Recharts 또는 TradingView 라이브러리 사용
- **상태 관리**:
  - 서버 상태: TanStack Query (React Query)
  - 클라이언트 상태: Zustand 또는 Context API
- **타입 안정성**:
  - Backend API 응답에 대한 Zod 스키마 검증
  - TypeScript strict mode 활성화

### 시리얼라이저

- 차트 시리얼라이저는 프론트엔드 차트 라이브러리용으로 `to_representation()` 오버라이드
- 모델 프로퍼티(`change_percent_numeric`, `is_profitable`)에는 `ReadOnlyField()` 사용
- 재무 시리얼라이저는 `fields = '__all__'` 사용 (포괄적 데이터 필요)

### 자주 발생하는 버그

**Backend**:
1. Processor 메서드에서 return문 누락 (암묵적으로 None 반환)
2. analysis 앱에서 `DailyPrice` 대신 `HistoricalPrice` 사용
3. 주식 심볼에 `.upper()` 호출 누락
4. Alpha Vantage 응답에서 None/빈 값 처리 누락
5. 배치 작업 시 트랜잭션 관리 누락
6. PostgreSQL 전환 시 타임존 설정 불일치 (USE_TZ=True 필수)
7. 대용량 쿼리 시 N+1 문제 (select_related/prefetch_related 미사용)

**Frontend** (예정):
1. API 응답 타입 불일치 (Backend 변경 시 타입 동기화 필수)
2. 차트 데이터 포맷 변환 오류
3. 무한 스크롤/페이지네이션에서 중복 데이터 요청
4. 서버 상태와 클라이언트 상태 동기화 문제

## 로깅 및 모니터링

**Backend 로깅**:
- 로거는 `config/settings.py`에서 설정
- 로그 파일: `stocks.log`
- 모듈 레벨 로거 사용: `logger = logging.getLogger(__name__)`
- Service/Client 계층은 API 호출, 에러, rate limiting 로깅
- **프로덕션 환경**: 구조화된 로깅 (JSON 포맷) 권장

**ML 모델 모니터링** (예정):
- 모델 성능 메트릭 추적 (정확도, 손실, 예측 신뢰도)
- 데이터 드리프트 감지
- 예측 결과 실제 값과의 비교 분석

**Frontend 모니터링** (예정):
- 에러 추적: Sentry 또는 유사 서비스
- 성능 모니터링: Web Vitals, Lighthouse CI
- 사용자 행동 분석

## Alpha Vantage API 참고사항

- 무료 티어: 5 calls/분, 500 calls/일
- Rate limiting 강제: 요청 간 12초 대기
- camelCase 필드명 반환 (예: "fiscalDateEnding") - processor가 snake_case로 변환
- 일반적인 응답 패턴:
  - 에러: `{"Error Message": "..."}`
  - Rate limit: `{"Note": "API call frequency..."}`
  - 빈 데이터는 null이 아닌 `{}` 반환
