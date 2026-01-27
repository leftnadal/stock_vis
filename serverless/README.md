# Serverless - Market Movers

Django 기반 Market Movers 구현 (AWS Lambda 전환 대상)

## 개요

Phase 1: Django 로컬 구현으로 Market Movers 기능을 완전히 구현
Phase 2-4: AWS Lambda + DynamoDB로 점진적 전환

## 구현 완료 사항

### 1. 모델 (models.py)
- **MarketMover**: 메인 데이터 모델 (gainers/losers/actives)
- **SectorETFMapping**: 섹터-ETF 매핑 (Phase 2용)
- **StockSectorInfo**: 종목 섹터 정보 (Phase 2용)
- **VolatilityBaseline**: 변동성 백분위 (Phase 2용)

### 2. FMP API 클라이언트 (services/fmp_client.py)
- `get_market_gainers()`: 상승 TOP 20
- `get_market_losers()`: 하락 TOP 20
- `get_market_actives()`: 거래량 TOP 20
- `get_quote(symbol)`: 실시간 시세 (OHLC)
- `get_historical_ohlcv(symbol, days=20)`: 히스토리 데이터
- `get_company_profile(symbol)`: 기업 프로필

**특징**:
- httpx 동기 클라이언트 사용
- Django 캐시 통합 (5분 TTL)
- 에러 핸들링

### 3. 지표 계산 로직 (services/indicators.py)
Phase 1 (구현 완료):
- **RVOL**: 당일 거래량 / 20일 평균
- **Trend Strength**: (종가-시가) / (고가-저가)

Phase 2 (스텁만 작성):
- Sector Alpha
- ETF Sync Rate
- Volatility Percentile

**중요**: AWS Lambda로 전환 시 이 클래스를 그대로 재사용 가능 (Django 의존성 없음)

### 4. 데이터 동기화 (services/data_sync.py)
- `MarketMoversSync.sync_daily_movers()`: FMP API → 지표 계산 → DB 저장
- 트랜잭션 관리
- 데이터 품질 추적

### 5. Celery Task (tasks.py)
- `sync_daily_market_movers`: 매일 07:30 실행 (settings.py에서 스케줄 설정)
- 재시도 로직 (max_retries=3)

### 6. REST API (views.py, urls.py)
- `GET /api/v1/serverless/movers?type=gainers&date=2025-01-06`
- `GET /api/v1/serverless/movers/AAPL?date=2025-01-06`
- `POST /api/v1/serverless/sync` (수동 동기화)
- `GET /api/v1/serverless/health`

### 7. Django Admin (admin.py)
- MarketMover, SectorETFMapping, StockSectorInfo, VolatilityBaseline 관리

## 설치 및 실행

### 1. 패키지 설치
```bash
poetry add httpx
```

### 2. 마이그레이션 적용
```bash
python manage.py migrate
```

### 3. 수동 동기화 테스트
```bash
# Django Shell
python manage.py shell
>>> from serverless.tasks import sync_daily_market_movers
>>> result = sync_daily_market_movers.delay()
>>> result.get()
{'gainers': 20, 'losers': 20, 'actives': 20, 'errors': 0}
```

### 4. API 테스트
```bash
# 헬스체크
curl http://localhost:8000/api/v1/serverless/health

# Gainers 조회
curl "http://localhost:8000/api/v1/serverless/movers?type=gainers"

# 특정 종목 상세
curl "http://localhost:8000/api/v1/serverless/movers/AAPL"
```

### 5. Celery Worker/Beat 실행
```bash
# Worker
celery -A config worker -l info

# Beat (스케줄러)
celery -A config beat -l info
```

## 데이터 구조

### MarketMover 모델
```python
{
    "date": "2025-01-06",
    "mover_type": "gainers",
    "rank": 1,
    "symbol": "AAPL",
    "company_name": "Apple Inc.",
    "price": 150.00,
    "change_percent": 3.50,
    "volume": 100000000,
    "open_price": 148.50,
    "high": 151.00,
    "low": 148.00,
    "rvol": 2.50,
    "rvol_display": "2.5x",
    "trend_strength": 0.85,
    "trend_display": "▲0.85",
    "data_quality": {
        "has_20d_volume": true,
        "has_ohlc": true,
        "historical_days": 20
    }
}
```

## Phase 2 계획

1. **추가 지표 구현**:
   - Sector Alpha (섹터 대비 초과수익)
   - ETF Sync Rate (섹터 ETF 동행률)
   - Volatility Percentile (변동성 백분위)

2. **단위 테스트**:
   - `serverless/tests/test_indicators.py`
   - `serverless/tests/test_fmp_client.py`
   - `serverless/tests/test_data_sync.py`

3. **성능 측정**:
   - 동기화 속도 (목표: < 5분)
   - API 응답 시간 (목표: < 500ms)

## AWS Lambda 전환 (Phase 3-4)

### Lambda 재사용 가능 모듈
- `services/indicators.py` → `lambda/common/indicators.py` (그대로 복사)
- `services/fmp_client.py` → `lambda/common/fmp_client.py` (설정만 변경)

### DynamoDB 스키마
```python
PK: DATE#2025-01-06
SK: TYPE#GAINERS#RANK#01
```

## 문제 해결

### FMP API 에러
- 확인: `.env` 파일에 `FMP_API_KEY` 설정
- Rate Limit: FMP는 10 calls/min (Starter Plan)

### httpx 미설치
```bash
poetry add httpx
```

### 마이그레이션 오류
```bash
python manage.py migrate --fake-initial
```

## KB 참고

- FMP API Market Movers 구현 패턴
- Django 3계층 아키텍처

## 키워드 시스템 (Phase 2.5)

### 개요

Market Movers 각 종목에 대해 **LLM 기반 3-5개 핵심 키워드** 자동 생성

**목표**: 사용자가 한눈에 급등/급락 이유 파악

### 모델

**StockKeyword**:
- `symbol`, `company_name`, `date`
- `keywords` (JSONField, 문자열 배열)
- `status` ('pending', 'processing', 'completed', 'failed')
- `llm_model`, `generation_time_ms`, `prompt_tokens`, `completion_tokens`
- `expires_at` (TTL 7일)

### 서비스 레이어

**KeywordGenerationService** (`services/keyword_service.py`):
- `generate_keyword()`: 단일 종목 키워드 생성
- `batch_generate()`: 일괄 생성 (Celery 태스크용)
- Fallback 키워드 (LLM 실패 시)

**MarketMoversProcessor** (`processors.py`):
- `get_movers_with_keywords()`: MarketMover + StockKeyword 조합 (N+1 방지)

### API 응답 (키워드 포함)

```json
{
  "success": true,
  "data": {
    "movers": [
      {
        "symbol": "NVDA",
        "keywords": ["AI 반도체 수요", "데이터센터 확장", "실적 서프라이즈"]
      }
    ]
  }
}
```

### Celery 태스크 (by @infra)

1. **generate_daily_keywords**: 매일 08:00 (Market Movers 동기화 후)
2. **cleanup_expired_keywords**: 매일 02:00 (만료 데이터 정리)

### 테스트

```bash
# 단위 테스트
pytest tests/serverless/test_keyword_service.py -v
pytest tests/serverless/test_processors.py -v
```

### 비용

- **LLM**: Gemini 2.5 Flash
- **일일**: 60개 종목 × $0.0018 = **월 75원**

### 참고 문서

- 설계 문서: `/docs/MARKET_MOVERS_KEYWORD_DESIGN.md`
- 상세 가이드: `serverless/KEYWORD_SYSTEM_SUMMARY.md`

---

## 다음 단계

1. **@infra**: Celery 태스크 구현 (`generate_daily_keywords`, `cleanup_expired_keywords`)
2. **@qa**: 통합 테스트 작성
3. **@frontend**: MoverCard에 키워드 배지 UI 추가
