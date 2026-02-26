# Celery Beat 스케줄 미실행으로 인한 주식 데이터 동기화 중단

**발견 일자**: 2026-02-26
**상태**: 조사 완료, 모니터링 중 (2/27 확인 예정)
**우선순위**: 🔴 Critical
**영향 범위**: S&P500 재무제표, Daily Price, 구성종목 동기화 전체

---

## 증상

Dashboard 주식 섹션에서 S&P500 동기화, Daily Price, Balance Sheet, Income Statement, Cash Flow Statement가 최신 데이터로 업데이트되지 않음.

| 데이터 | 마지막 업데이트 | 기대값 |
|--------|---------------|--------|
| Daily Price | 2026-02-25 (495종목) | 매 거래일 |
| Balance Sheet | 2025-12-08 | 매 분기 |
| Income Statement | 2025-12-08 | 매 분기 |
| Cash Flow Statement | 2025-12-08 | 매 분기 |

---

## 근본 원인

### Celery Beat가 2026-02-25 07:58 ET에 처음 시작됨

DB의 모든 `PeriodicTask.date_changed`가 `2026-02-25 12:58:35 UTC (= 07:58 ET)`로 동일.
이 시점에 Beat가 `config/celery.py`의 `beat_schedule` 딕셔너리를 `django_celery_beat` DB에 처음 동기화한 것.

**그 이전에는 Beat가 실행되지 않았거나, 스케줄이 DB에 등록되어 있지 않았음.**
재무제표 마지막 업데이트가 2025-12-08인 것도 수동 입력이었음을 뒷받침.

### 미실행 태스크의 시간 패턴

Beat 시작(07:58 ET) 이전 스케줄은 전부 놓치고, 이후 스케줄만 실행됨:

```
01:00 ET  update-economic-calendar       ← MISS (이미 지남)
04:00 ET  cleanup-expired-semantic-cache  ← MISS
06:00 ET  collect-daily-news              ← MISS
06:30 ET  collect-category-news-high      ← MISS
07:00 ET  collect-category-news-medium    ← MISS
07:30 ET  sync-daily-market-movers        ← MISS
────── 07:58 ET: Beat 시작 ──────
08:00 ET  keyword-generation-pipeline     ← ✅ (2분 후 실행)
12:00 ET  collect-market-news-noon        ← ✅
17:00 ET  update-daily-prices             ← ✅
18:00 ET  sync-sp500-eod-prices           ← ✅ (run_count: 1)
20:00 ET  sync-sp500-financials           ← 아직 미도달 (01:00 UTC)
```

### 태스크별 실행 현황 (2/25 기준)

| 태스크 | 스케줄 | 총 실행 | 상태 |
|--------|--------|---------|------|
| `sync-sp500-financials` | 평일 20:00 ET | 0회 | 오늘 밤 첫 실행 예정 |
| `sync-sp500-eod-prices` | 평일 18:00 ET | 1회 | 2/25 실행됨 |
| `sync-sp500-constituents` | 매월 1일 02:00 ET | 0회 | 3/1 실행 예정 |
| `aggregate-weekly-prices` | 토 01:00 ET | 0회 | 2/28 실행 예정 |

---

## 현재 환경 설정

### Provider 설정 (.env) - 정상

```
STOCK_PROVIDER_BALANCE_SHEET=fmp
STOCK_PROVIDER_INCOME_STATEMENT=fmp
STOCK_PROVIDER_CASH_FLOW=fmp
STOCK_PROVIDER_DAILY_PRICES=fmp
```

FMP (300 calls/분, 10,000 calls/일) 사용 중이므로 rate limit 문제 없음.

### Celery 설정 - 정상

- Scheduler: `django_celery_beat.schedulers:DatabaseScheduler`
- Timezone: `America/New_York`
- 모든 태스크 import 정상 확인됨

### DB 현황

- S&P500 활성 종목: 503개
- Daily Price 총 레코드: 2,947개
- Balance Sheet: 551개 (마지막: 2025-12-08)
- Income Statement: 552개 (마지막: 2025-12-08)
- Cash Flow Statement: 530개 (마지막: 2025-12-08)

---

## 추가 발견: 레거시 태스크 중복 → ✅ 정리 완료 (2026-02-26)

DB에 `sync-market-movers`(레거시, run_count=11)와 `sync-daily-market-movers`(현재, run_count=0)가 공존했음.
둘 다 같은 태스크(`serverless.tasks.sync_daily_market_movers`)를 호출하며 enabled=True였음.

- `sync-market-movers`: `30 7 * * *` (매일 07:30) — 주말 포함, 불필요
- `sync-daily-market-movers`: `30 7 * * 1-5` (평일 07:30) — 현재 정상 스케줄

**조치**: 레거시 `sync-market-movers`를 DB에서 삭제 완료. `sync-daily-market-movers`만 남아있음.

---

## Macro 태스크 반복 실패 → 조사 완료 (2026-02-26)

`macro.tasks.update_economic_indicators`와 `macro.tasks.update_market_indices`가 `MaxRetriesExceededError`로 반복 실패.

### 원인 1: `update_economic_indicators` — `cache.delete_pattern` 미지원 → ✅ 수정 완료

```
AttributeError: 'RedisCache' object has no attribute 'delete_pattern'
```

캐시 백엔드가 `django.core.cache.backends.redis.RedisCache` (Django 내장)인데,
`cache.delete_pattern()`은 `django-redis` (서드파티)에만 있는 메서드.
FRED API 호출과 DB 저장은 성공하지만, 마지막 캐시 무효화에서 에러 → 전체 태스크 실패 처리됨.

**조치**: `cache.delete_pattern('macro:*')` → `cache.delete_many([...])` 으로 교체.
`macro/tasks.py`의 3곳 모두 수정 완료.

### 원인 2: `update_market_indices` — FMP Starter Plan 배치 조회 제한 → ✅ 수정 완료

```
402 Payment Required: Special Endpoint : This value set for 'symbol' is not available
under your current subscription
```

FMP Starter Plan에서 콤마 구분 배치 조회(`/stable/quote?symbol=A,B,C`)가 프리미엄 전용.
개별 조회(`/stable/quote?symbol=A`)는 정상 동작.
`get_batch_quotes()`가 배치 방식을 사용하고 있어 모든 시장 지수 조회가 실패했음.

**조치**:
- `macro/services/fmp_client.py`: `get_batch_quotes()`를 개별 `get_quote()` 반복 방식으로 변경
- 미지원 심볼 `^GDAXI` (DAX) 제거 — 개별 조회에서도 402 반환
- `macro/services/macro_service.py`: 응답에서 `dax` 키 제거
- `frontend/types/macro.ts`: `GlobalIndices`에서 `dax` 필드 제거
- `frontend/components/macro/GlobalMarketsCard.tsx`: DAX 행 제거

수정 후 8개 지수 전부 정상 조회 확인됨 (S&P 500, Dow, NASDAQ, Russell 2000, VIX, FTSE 100, Nikkei 225, Hang Seng).

### 원인 3: `/serverless/breadth` 500 에러 — yfinance 미설치 → ✅ 수정 완료

```
ModuleNotFoundError: No module named 'yfinance'
```

`serverless/views.py`의 `_get_market_indices()` 헬퍼 함수가 `import yfinance as yf`를 사용.
yfinance 미설치 상태에서 breadth 엔드포인트 호출 시 500 에러 발생.

**조치**:
- `serverless/views.py`: `_get_market_indices()`를 `serverless.services.fmp_client.FMPClient`의 `get_quote()` 개별 호출 방식으로 교체
- yfinance 의존성 완전 제거 완료 (macro/services/yfinance_client.py 삭제 포함)

---

## 2/27 확인 체크리스트

### 1. sync-sp500-financials 실행 확인
```python
from django_celery_beat.models import PeriodicTask
t = PeriodicTask.objects.get(name='sync-sp500-financials')
print(f'run_count: {t.total_run_count}, last_run: {t.last_run_at}')
```

### 2. 재무제표 업데이트 확인
```python
from stocks.models import BalanceSheet
from django.db.models import Max
print(BalanceSheet.objects.aggregate(Max('created_at')))
```

### 3. Daily Price 오늘 날짜 확인
```python
from stocks.models import DailyPrice
from django.db.models import Count
recent = DailyPrice.objects.order_by('-date').values('date').annotate(cnt=Count('stock_id', distinct=True))[:5]
for r in recent:
    print(f'{r["date"]}: {r["cnt"]} stocks')
```

### 4. 아침 태스크 실행 확인
```python
from django_celery_beat.models import PeriodicTask
for name in ['collect-daily-news', 'collect-category-news-high-morning', 'sync-daily-market-movers']:
    t = PeriodicTask.objects.get(name=name)
    print(f'{name}: run_count={t.total_run_count}, last_run={t.last_run_at}')
```

### 5. ~~레거시 태스크 정리 여부 결정~~ ✅ 완료
레거시 `sync-market-movers` DB에서 삭제 완료 (2026-02-26).

---

## 결론

코드 버그가 아닌 **운영 환경 이슈**. Celery Beat가 이전에 실행되지 않았기 때문에 자동 동기화가 전혀 이루어지지 않았음. 2025-12-08의 재무제표 데이터는 수동 입력이었던 것으로 추정.

Beat가 2/25부터 정상 가동 중이므로, 각 태스크의 스케줄 시간이 도래하면 순차적으로 실행될 것. **2/27까지 모든 평일 태스크가 최소 1회 이상 실행되었는지 확인 필요.**
