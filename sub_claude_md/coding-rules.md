# 코딩 규칙

## Backend

- 심볼 처리: `symbol.upper()` 필수
- 모델 조회: `get_object_or_404(Stock, symbol=symbol.upper())`
- Processor: 반드시 `return` 문 포함
- 기간 타입: `period_type='annual'` 또는 `'quarterly'`
- 가격 모델: `DailyPrice` 사용 (`HistoricalPrice` 없음)

## Frontend

- TypeScript strict mode
- 서버 상태: TanStack Query
- 클라이언트 상태: Zustand
- `'use client'` 필요한 컴포넌트만

## 비동기 (Celery)

- Rate limiting: Alpha Vantage 12초 간격
- 태스크 idempotent 구현
- 재시도: max_retries=3, exponential backoff
- Celery Worker에서 LLM 호출 시 **동기 API만** 사용 (async 금지)

## Celery Beat 스케줄 (2곳에 분산 정의)

**config/settings.py** (`CELERY_BEAT_SCHEDULE`):
| 태스크 | 스케줄 |
|--------|--------|
| sync-market-movers | 매일 07:30 EST |
| calculate-market-breadth | 평일 16:30 ET |
| calculate-sector-heatmap | 평일 16:35 ET |

**config/celery.py** (`app.conf.beat_schedule`):
| 태스크 | 스케줄 |
|--------|--------|
| update-realtime-prices | 장중 5분마다 |
| update-daily-prices | 평일 17:00 |
| update-weekly-prices | 토요일 자정 |
| update-financial-statements | 매월 1일 02:00 |
| calculate-portfolio-values | 장중 10분마다 |
| update-economic-indicators | 매시간 |
| update-market-indices | 장중 5분마다 |
| update-economic-calendar | 매일 01:00 |
| refresh-market-pulse-cache | 장중 1분마다 |
| cleanup-old-macro-data | 일요일 03:00 |
| neo4j-health-check | 5분마다 |
| cleanup-expired-semantic-cache | 매일 04:00 |
| warm-semantic-cache | 일요일 04:30 |
| keyword-generation-pipeline | 매일 08:00 EST |
| extract-daily-news-keywords | 매일 08:00 EST |
| sync-etf-holdings | 월요일 06:00 EST |
| sync-supply-chain-batch | 매월 15일 03:00 EST |
| check-screener-alerts | 장중 15분마다 |

## 로깅

- 로그 파일: `stocks.log`
- 사용법: `logger = logging.getLogger(__name__)`

---

# 외부 API

## Alpha Vantage

- 무료 티어: 5 calls/분, 500 calls/일
- 요청 간 12초 대기 필수
- 응답: camelCase → Processor가 snake_case로 변환

## FMP (Financial Modeling Prep)

**Market Movers 전용 API**

- **플랜**: Starter Plan 사용
- **Rate Limit**: 10 calls/분, 250 calls/일
- **엔드포인트**: `/stable/*` 경로 사용 (Legacy `/api/v3/*` 더 이상 지원 안 함)
- **주요 API**:
  - `/stable/biggest-gainers` - 상승 TOP 종목
  - `/stable/biggest-losers` - 하락 TOP 종목
  - `/stable/most-actives` - 거래량 TOP 종목
  - `/stable/quote?symbol=AAPL` - 실시간 시세 (volume 포함)
  - `/stable/historical-price-eod/full?symbol=AAPL` - 히스토리 OHLCV
  - `/stable/profile?symbol=AAPL` - 기업 프로필 (섹터 정보)
  - `/stable/company-screener` - 종목 스크리닝 (market_cap, volume 등)
  - `/stable/key-metrics-ttm?symbol=AAPL` - 펀더멘탈 지표 (PE, ROE 등)
- **캐싱**: Redis 5분~24시간 (엔드포인트별 상이)
- **프리미엄 심볼 제외**: `.` 포함 심볼(BRK.B, BF.B)은 Starter Plan 미지원 (402 에러)
  - `FMPPremiumError` 예외로 즉시 실패 (재시도 안 함)
  - 재무제표 배치 동기화에서 자동 제외
  - 상세: `docs/infrastructure/fmp-premium-symbols.md`
- **섹터 ETF 매핑**:
  ```python
  SECTOR_ETF_MAP = {
      'Technology': 'XLK',
      'Financial Services': 'XLF',
      'Healthcare': 'XLV',
      'Consumer Cyclical': 'XLY',
      'Industrials': 'XLI',
      'Energy': 'XLE',
      # ... 총 11개 섹터
  }
  ```

## yfinance (Yahoo Finance)

**사용처**: Market Pulse (거시경제 지표), Corporate Action 감지

**특징**: 무료, Rate limit 없음

```python
INDEX_SYMBOLS = {'^GSPC': 'S&P 500', '^DJI': 'Dow Jones', '^IXIC': 'NASDAQ'}
SECTOR_ETFS = {'XLK': 'Technology', 'XLF': 'Financials', ...}
COMMODITIES = {'GC=F': 'Gold', 'CL=F': 'Crude Oil', ...}
FOREX = {'EURUSD=X': 'EUR/USD', 'KRW=X': 'USD/KRW', ...}
```

**주의사항**:
- Lazy import 필수 (`import yfinance as yf` - 사용 시점에 import)
- `ticker.splits`, `ticker.dividends`는 pandas Series (`.items()` 메서드 사용)
- `split.date()`로 날짜 변환 (pandas Timestamp → Python date)
- 에러 발생 시 로깅만 하고 None 반환 (메인 플로우 중단 안 함)

---

# 캐싱 전략

| 데이터 타입 | TTL | 비고 |
|-----------|-----|------|
| 차트 데이터 | 60초 | 실시간성 중요 |
| Overview | 600초 | 가격 + 기본 정보 |
| 재무제표 | 3600초 | 분기/연간 업데이트 |
| 거시경제 지표 | 3600초 | FRED 데이터 |
| Watchlist 목록 | 300초 | 사용자별 캐시 키 |
| Watchlist 종목 | 60초 | 실시간 가격 포함 |
| Market Movers 리스트 | 300초 | FMP Gainers/Losers/Actives |
| FMP Quote | 60초 | 실시간 시세 |
| FMP Historical | 3600초 | OHLCV 히스토리 |
| FMP Profile | 86400초 | 섹터 정보 (24시간) |
| FMP Company Screener | 300초 | 종목 스크리닝 결과 |
| FMP Key Metrics TTM | 3600초 | 펀더멘탈 지표 (PE/ROE) |
