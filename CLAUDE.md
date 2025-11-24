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
	queryKey: ["stock", symbol, "chart", period],
	queryFn: () => fetch(`/api/v1/stocks/api/chart/${symbol}/?period=${period}`),
});
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

## 실시간 데이터 업데이트 시스템 (Celery + Redis)

### 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Celery Beat (스케줄러)                    │
│  - 주기적 태스크 스케줄링                                    │
│  - 시장 시간대 고려한 스케줄 조정                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Redis (메시지 브로커)                      │
│  - 태스크 큐 관리                                           │
│  - 캐싱 백엔드                                              │
│  - 실시간 데이터 저장                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Celery Workers (작업자)                    │
│  - 비동기 태스크 실행                                       │
│  - Alpha Vantage API 호출                                   │
│  - 데이터베이스 업데이트                                    │
└─────────────────────────────────────────────────────────────┘
```

### 구현 계획

#### 1. 환경 설정

**필요한 패키지 설치**:

```bash
# Poetry로 패키지 추가
poetry add celery redis django-celery-beat django-celery-results channels channels-redis

# Redis 설치 (macOS)
brew install redis
brew services start redis

# Redis 동작 확인
redis-cli ping  # PONG 응답 확인
```

**Django 설정** (`config/settings.py`):

```python
# Celery 설정
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/New_York'  # NYSE 시간대
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Redis 캐시 백엔드
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# WebSocket 설정 (실시간 알림용)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

#### 2. Celery 앱 구성

**`config/celery.py` 생성**:

```python
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('stock_vis')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# 정기 태스크 스케줄 설정
app.conf.beat_schedule = {
    # 실시간 주가 업데이트 (시장 개장 시간)
    'update-realtime-prices': {
        'task': 'stocks.tasks.update_realtime_prices',
        'schedule': crontab(minute='*/1', hour='9-16', day_of_week='1-5'),
        'kwargs': {'priority': 'high'}
    },

    # 일일 종가 업데이트 (시장 마감 후)
    'update-daily-prices': {
        'task': 'stocks.tasks.update_daily_prices',
        'schedule': crontab(hour=17, minute=0, day_of_week='1-5'),
    },

    # 주간 데이터 업데이트 (주말)
    'update-weekly-prices': {
        'task': 'stocks.tasks.update_weekly_prices',
        'schedule': crontab(hour=0, minute=0, day_of_week=6),
    },

    # 재무제표 업데이트 (분기별)
    'update-financial-statements': {
        'task': 'stocks.tasks.update_financial_statements',
        'schedule': crontab(hour=2, minute=0, day_of_month=1),
    },

    # 포트폴리오 가치 계산
    'calculate-portfolio-values': {
        'task': 'users.tasks.calculate_portfolio_values',
        'schedule': crontab(minute='*/5', hour='9-16', day_of_week='1-5'),
    },
}
```

#### 3. 태스크 구현

**`stocks/tasks.py` 생성**:

```python
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
from django.db import transaction
from .models import Stock, DailyPrice
from API_request.alphavantage_service import AlphaVantageService
import time

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3)
def update_realtime_prices(self, symbols=None, priority='normal'):
    """실시간 주가 업데이트 태스크"""
    try:
        if not symbols:
            # 관심종목 또는 포트폴리오에 있는 종목만 업데이트
            symbols = Stock.objects.filter(
                portfolio__isnull=False
            ).distinct().values_list('symbol', flat=True)[:10]  # Rate limit 고려

        service = AlphaVantageService()
        updated_count = 0

        for symbol in symbols:
            try:
                # Rate limiting (12초 대기)
                if updated_count > 0:
                    time.sleep(12)

                # API 호출 및 업데이트
                data = service.update_stock_quote(symbol)

                # 캐시 무효화
                cache.delete(f'stock_quote_{symbol}')

                # WebSocket으로 실시간 알림 (선택적)
                send_price_update_notification(symbol, data)

                updated_count += 1
                logger.info(f"Updated realtime price for {symbol}")

            except Exception as e:
                logger.error(f"Error updating {symbol}: {e}")
                continue

        return f"Updated {updated_count} stocks"

    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise self.retry(exc=e, countdown=60)

@shared_task
def update_daily_prices():
    """일일 종가 데이터 업데이트"""
    # 포트폴리오에 있는 모든 종목
    symbols = Stock.objects.filter(
        portfolio__isnull=False
    ).distinct().values_list('symbol', flat=True)

    service = AlphaVantageService()

    for batch in chunks(symbols, 5):  # 5개씩 배치 처리
        update_batch_daily_prices.delay(batch)

@shared_task
def update_batch_daily_prices(symbols):
    """배치 단위 일일 가격 업데이트"""
    service = AlphaVantageService()

    for symbol in symbols:
        try:
            with transaction.atomic():
                service.update_historical_prices(symbol, period='1d')
                time.sleep(12)  # Rate limiting
        except Exception as e:
            logger.error(f"Failed to update daily prices for {symbol}: {e}")

@shared_task(bind=True)
def update_financial_statements(self):
    """재무제표 업데이트 (월별 실행)"""
    symbols = Stock.objects.all().values_list('symbol', flat=True)

    for symbol in symbols:
        update_single_financial_statement.delay(symbol)

@shared_task
def update_single_financial_statement(symbol):
    """단일 종목 재무제표 업데이트"""
    service = AlphaVantageService()

    try:
        with transaction.atomic():
            service.update_balance_sheet(symbol)
            time.sleep(12)
            service.update_income_statement(symbol)
            time.sleep(12)
            service.update_cash_flow(symbol)

        logger.info(f"Updated financial statements for {symbol}")
    except Exception as e:
        logger.error(f"Failed to update financial statements for {symbol}: {e}")
```

**`users/tasks.py` 생성**:

```python
from celery import shared_task
from django.db.models import Sum, F
from .models import Portfolio, PortfolioHistory
from stocks.models import Stock
from decimal import Decimal

@shared_task
def calculate_portfolio_values():
    """포트폴리오 가치 계산 및 히스토리 저장"""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    for user in User.objects.filter(portfolio__isnull=False).distinct():
        try:
            portfolios = Portfolio.objects.filter(user=user).select_related('stock')

            total_value = Decimal('0')
            total_cost = Decimal('0')

            for portfolio in portfolios:
                # 현재가 * 수량으로 가치 계산
                current_price = portfolio.stock.real_time_price or Decimal('0')
                portfolio_value = current_price * portfolio.quantity
                portfolio_cost = portfolio.average_price * portfolio.quantity

                total_value += portfolio_value
                total_cost += portfolio_cost

            # 히스토리 저장
            PortfolioHistory.objects.create(
                user=user,
                total_value=total_value,
                total_cost=total_cost,
                profit_loss=total_value - total_cost,
                profit_loss_percentage=((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
            )

        except Exception as e:
            logger.error(f"Failed to calculate portfolio for user {user.id}: {e}")
```

#### 4. WebSocket 실시간 통신 (선택적)

**`stocks/consumers.py` 생성**:

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class StockPriceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.symbol = self.scope['url_route']['kwargs']['symbol']
        self.room_group_name = f'stock_{self.symbol}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def price_update(self, event):
        """실시간 가격 업데이트 전송"""
        await self.send(text_data=json.dumps({
            'type': 'price_update',
            'symbol': event['symbol'],
            'price': event['price'],
            'change': event['change'],
            'change_percent': event['change_percent'],
            'timestamp': event['timestamp']
        }))
```

#### 5. 실행 및 모니터링

**개발 환경 실행**:

```bash
# Redis 서버 시작
redis-server

# Celery Worker 시작 (별도 터미널)
celery -A config worker -l info

# Celery Beat 시작 (별도 터미널)
celery -A config beat -l info

# Flower 모니터링 도구 (선택적)
poetry add flower
celery -A config flower
# http://localhost:5555 에서 모니터링
```

**프로덕션 환경 실행 (Supervisor 사용)**:

```ini
# /etc/supervisor/conf.d/celery_worker.conf
[program:celery_worker]
command=/path/to/venv/bin/celery -A config worker -l info
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log

[program:celery_beat]
command=/path/to/venv/bin/celery -A config beat -l info
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/beat.log
```

### 성능 최적화 전략

1. **우선순위 큐 설정**:

   - 실시간 가격: high priority
   - 일일 업데이트: medium priority
   - 재무제표: low priority

2. **Rate Limiting 최적화**:

   - Alpha Vantage API 호출 간 12초 대기
   - 배치 처리로 효율성 향상
   - 캐싱으로 중복 호출 방지

3. **데이터베이스 최적화**:

   - bulk_create/bulk_update 사용
   - select_for_update로 동시성 제어
   - 인덱스 최적화

4. **모니터링 및 알림**:
   - Flower로 태스크 모니터링
   - Sentry로 에러 추적
   - 중요 이벤트 로깅

### 장애 대응

1. **재시도 전략**:

   - API 실패 시 exponential backoff
   - 최대 3회 재시도
   - Dead Letter Queue 활용

2. **서킷 브레이커**:

   - API 연속 실패 시 일시 중단
   - 복구 후 점진적 재개

3. **데이터 일관성**:
   - 트랜잭션 보장
   - 중복 실행 방지 (idempotency)
   - 정합성 체크 태스크

## Alpha Vantage API 참고사항

- 무료 티어: 5 calls/분, 500 calls/일
- Rate limiting 강제: 요청 간 12초 대기
- camelCase 필드명 반환 (예: "fiscalDateEnding") - processor가 snake_case로 변환
- 일반적인 응답 패턴:
  - 에러: `{"Error Message": "..."}`
  - Rate limit: `{"Note": "API call frequency..."}`
  - 빈 데이터는 null이 아닌 `{}` 반환

## 최근 주요 업데이트 (2025-11-24)

### 백그라운드 데이터 수집 시스템 (신규)
포트폴리오에 종목 추가 시 HTTP 응답 지연 문제를 해결하기 위한 백그라운드 처리 시스템:

**문제점**:
- 데이터 수집에 36초+ 소요 (Rate limiting 12초 x 3회)
- 사용자 페이지 이탈 시 데이터 수집 불완전

**해결책**:
- Python threading으로 백그라운드 데이터 수집
- Frontend 폴링으로 실시간 상태 표시

**구현 내용**:
```python
# users/views.py - 포트폴리오 생성 시 즉시 응답 후 백그라운드 수집
def post(self, request):
    portfolio = serializer.save()

    def background_fetch():
        fetch_stock_data_background(portfolio.stock.symbol)

    thread = threading.Thread(target=background_fetch, daemon=True)
    thread.start()

    return Response(PortfolioSerializer(portfolio).data, status=201)
```

**새로운 API 엔드포인트**:
- `GET /api/v1/users/portfolio/symbol/<symbol>/status/` - 데이터 수집 상태 확인

**Frontend 폴링 패턴** (`PortfolioStockCard.tsx`):
```typescript
useEffect(() => {
  const intervalId = setInterval(async () => {
    const status = await portfolioService.getStockDataStatus(symbol);
    if (status.is_complete) {
      clearInterval(intervalId);
      onDataComplete?.();
    }
  }, 10000); // 10초 간격
  return () => clearInterval(intervalId);
}, [symbol]);
```

**데이터 상태 응답 구조**:
```json
{
  "symbol": "AAPL",
  "stock_exists": true,
  "has_overview": true,
  "has_prices": true,
  "has_financial": true,
  "is_complete": true,
  "details": {
    "daily_prices": 730,
    "weekly_prices": 129,
    "balance_sheets": 24,
    "income_statements": 25,
    "cash_flows": 23
  }
}
```

### 429 Rate Limit 에러 처리
- 종목 검색 시 429 에러 발생 시 "해당 종목은 관찰되지 않습니다." 메시지 표시
- `PortfolioModal.tsx`에서 처리

## 이전 업데이트 (2025-11-21)

### 주식 상세 페이지 구현 완료
- 종목별 상세 정보 페이지 (`/stocks/[symbol]`)
- 실시간 차트 및 재무제표 탭
- 포트폴리오 종목 간 빠른 네비게이션

## 이전 업데이트 (2025-11-19)

### 1. WebSocket 실시간 통신 시스템 구현
- **Django Channels 통합**: ASGI 서버 설정 및 WebSocket 라우팅 구현
- **실시간 주가 업데이트**: WebSocket을 통한 1초 간격 가격 푸시
- **포트폴리오 실시간 계산**: 보유 종목 가치 자동 업데이트
- **Frontend WebSocket 컴포넌트**:
  - RealtimePortfolio: 실시간 포트폴리오 관리
  - useWebSocket 커스텀 훅: 재사용 가능한 WebSocket 연결 관리
  - 자동 재연결 로직 구현

### 2. Celery 태스크 시스템 완성
- **스케줄링 태스크**:
  - 실시간 주가 업데이트 (시장 시간대 1분마다)
  - 일일 종가 업데이트 (시장 마감 후)
  - 포트폴리오 가치 계산 (5분마다)
  - 재무제표 업데이트 (월 1회)
- **우선순위 큐**: high/medium/low 우선순위 설정
- **Rate Limiting**: Alpha Vantage API 제한 고려

### 3. Frontend 실시간 컴포넌트 개발
- **RealtimePortfolio 컴포넌트**: WebSocket 연결 상태 관리 및 실시간 업데이트
- **PortfolioChart 개선**: 실시간 데이터 반영 및 애니메이션
- **연결 상태 인디케이터**: 시각적 연결 상태 표시

### 4. 시스템 통합 및 성능 최적화
- **ASGI 설정**: HTTP + WebSocket 동시 처리
- **Redis Channel Layer**: 다중 클라이언트 메시지 브로드캐스팅
- **메모리 최적화**: 효율적인 구독 관리 및 메시지 배치 처리

## 이전 업데이트 (2025-11-18)

### 1. 사용자 인터페이스 개선
- **마이페이지 구현**: 사용자 프로필 편집 기능 추가
- **Header 네비게이션**: 로그인 상태별 조건부 UI 렌더링
- **인증 UI**: lucide-react 아이콘을 활용한 직관적인 디자인

### 2. Alpha Vantage 종목 검색 통합
- **실시간 검색**: 300ms 디바운스로 최적화된 API 호출
- **API 엔드포인트**:
  - `/api/v1/stocks/api/search/symbols/` - 종목 심볼 검색
  - `/api/v1/stocks/api/search/validate/<symbol>/` - 심볼 유효성 검증
  - `/api/v1/stocks/api/search/popular/` - 인기 종목 리스트
- **Frontend 통합**: PortfolioModal에 드롭다운 자동완성 구현

### 3. 기술적 지표 시스템
- **구현된 지표**: RSI, MACD, Bollinger Bands, SMA, EMA, Stochastic, OBV, ATR
- **매매 신호 시스템**: 개별 및 종합 신호 계산
- **API 엔드포인트**: `/api/v1/stocks/api/indicators/<symbol>/`

## 환경 설정 필수사항

```bash
# .env 파일 필수 설정
ALPHA_VANTAGE_API_KEY="your_api_key_here"

# settings.py 상단에 필수 (이미 적용됨)
from dotenv import load_dotenv
load_dotenv()

# Redis 실행 (실시간 기능 필수)
redis-server

# Celery Worker 실행
celery -A config worker -l info

# Celery Beat 실행 (스케줄링)
celery -A config beat -l info
```

## 구현 완료 기능 체크리스트
- ✅ JWT 인증 시스템
- ✅ 포트폴리오 CRUD
- ✅ 기술적 지표 계산 (RSI, MACD, Bollinger Bands 등)
- ✅ Alpha Vantage API 통합 (실시간 가격, 종목 검색)
- ✅ 마이페이지 및 사용자 프로필 관리
- ✅ 종목 검색 자동완성
- ✅ WebSocket 실시간 통신
- ✅ 백그라운드 데이터 수집 (Python threading)
- ✅ Frontend 데이터 상태 폴링 (10초 간격)
- ✅ 429 Rate Limit 에러 처리
- ✅ Celery 비동기 태스크 시스템
- ✅ Redis 캐싱 및 메시지 브로커
- ⏳ ML/DL 모델 통합 (미구현)
- ⏳ PostgreSQL 마이그레이션 (미구현)
