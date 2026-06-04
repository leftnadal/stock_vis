# 자주 발생하는 버그

## 기본 실수 (1~5)

1. Processor 메서드에서 return문 누락
2. `DailyPrice` 대신 `HistoricalPrice` 사용
3. 심볼에 `.upper()` 호출 누락
4. Alpha Vantage None/빈 값 처리 누락
5. N+1 쿼리 문제 (select_related/prefetch_related 미사용)

## SSE Async Loop 충돌 (#6)

Django ASGI(Daphne)에서 동기 뷰 내 `asyncio.new_event_loop()` 사용 시 연결 끊김
- 증상: "Application instance took too long to shut down" 에러, 요청 pending
- 해결: 비동기 이벤트를 먼저 수집 후 동기적으로 yield하거나, 완전한 async 뷰 사용

## FMP API volume 데이터 누락 (#7)

`/stable/biggest-gainers` 응답에 `volume` 필드 없음
- 증상: RVOL이 0.00x로 계산됨
- 해결: `item.get('volume')` 대신 `quote.get('volume')` 사용
- 참고: Market Movers 엔드포인트는 volume 미제공, Quote API에서 별도 조회 필요

## Celery Worker에서 async LLM 호출 금지 (#8)

- 증상: "Event loop is closed" 에러, LLM 호출 실패
- 원인: Celery Worker는 자체 이벤트 루프를 관리, async 코드와 충돌
- 해결: `genai.Client`의 동기 API 직접 사용 (async 대신)
```python
# ❌ 잘못된 방법
async def call_llm():
    return await async_client.generate(...)

# ✅ 올바른 방법
def call_llm():
    return sync_client.models.generate_content(...)
```

## LLM max_output_tokens 부족으로 JSON 잘림 (#9)

- 증상: "Unterminated string" JSON 파싱 에러
- 원인: 한국어 응답은 토큰 소비가 많아 출력이 중간에 잘림
- 해결: max_output_tokens 충분히 설정 (800 → 1200) + regex 복구 로직
```python
pattern = r'"([^"]+)"'
matches = re.findall(pattern, text)
if len(matches) >= 2:
    return matches[:5]  # 부분 복구
```

## Celery 비동기 태스크 완료 전 onSuccess 호출 (#10)

- 증상: mutation.onSuccess에서 데이터 재조회해도 결과 없음
- 원인: onSuccess는 API 요청 완료 시점, Celery 태스크 완료 시점 아님
- 해결: setTimeout으로 예상 완료 시간 후 재조회 또는 폴링
```typescript
onSuccess: (data) => {
  const delayMs = stockCount * 6000; // 종목당 6초
  setTimeout(() => fetchKeywords(), delayMs);
}
```

## 프론트엔드 string[] vs Keyword[] 타입 불일치 (#11)

- 증상: "Each child should have unique key" 또는 undefined 에러
- 원인: API가 `string[]` 반환, 컴포넌트가 `Keyword[]` 기대
- 해결: 정규화 함수로 타입 변환
```typescript
function normalizeKeywords(keywords: string[] | Keyword[]): Keyword[] {
  if (typeof keywords[0] === 'string') {
    return keywords.map((text, i) => ({ id: `kw-${i}`, text, ... }));
  }
  return keywords;
}
```

## React 컴포넌트 undefined props 접근 (#12)

- 증상: "undefined is not an object (evaluating 'colors.bg')"
- 원인: optional 필드가 undefined일 때 객체 속성 접근
- 해결: 기본값 폴백 패턴 사용
```typescript
const colors = CATEGORY_COLORS[keyword.category] || DEFAULT_COLORS;
```

## yfinance pandas Series 타입 불일치 (#13)

- 증상: "AttributeError: 'Series' object has no attribute 'date'"
- 원인: `ticker.splits`, `ticker.dividends`는 pandas Series (Timestamp 인덱스)
- 해결: `.items()` 메서드로 반복, `timestamp.date()`로 변환
```python
# ❌ 잘못된 방법
for split_date in ticker.splits:
    date_obj = split_date.date()  # 에러!

# ✅ 올바른 방법
for split_timestamp, ratio in ticker.splits.items():
    date_obj = split_timestamp.date()
```

## FMP Key Metrics TTM API 필드명 불일치 (#14)

- 증상: Enhanced 스크리너에서 PE, ROE가 항상 None
- 원인: FMP API 필드명이 직관적이지 않음
  - `peRatioTTM` 필드 존재 안 함 → `earningsYieldTTM` 사용 (역수 계산)
  - `roeTTM` 존재 안 함 → `returnOnEquityTTM` 사용 (decimal, 1.5 = 150%)
- 해결: 정확한 필드명 사용 + 값 변환
```python
# ❌ 잘못된 방법
pe_ratio = m.get('peRatioTTM')  # None!
roe = m.get('roeTTM')  # None!

# ✅ 올바른 방법
earnings_yield = m.get('earningsYieldTTM')
pe_ratio = round(1 / earnings_yield, 2) if earnings_yield > 0 else None

roe_decimal = m.get('returnOnEquityTTM')
roe_percent = round(roe_decimal * 100, 2) if roe_decimal else None
```

## Market Movers 캐시 키 불일치 (#15)

- 증상: 업데이트 버튼 클릭 후에도 데이터가 빈 배열로 반환됨
- 원인: `sync_now`에서 `movers:{date}:{type}` 키를 삭제하지만, `market_movers_api`는 `movers_with_keywords:{date}:{type}` 키를 사용
- 해결: `sync_now`에서 올바른 캐시 키 삭제
```python
# ✅ 올바른 방법 (API와 동일한 키 패턴)
cache_key = f'movers_with_keywords:{today}:{mover_type}'
cache.delete(cache_key)
cache.delete(f'movers:{today}:{mover_type}')  # 하위 호환
```

## ETF CSV 다운로드 실패 - SPDR XLSX (#16)

- 증상: SPDR ETF (XLK, XLV 등) CSV 파싱 실패, 0개 holdings
- 원인: SPDR은 CSV가 아닌 XLSX 형식 반환
- 해결: openpyxl로 XLSX 파싱, Content-Type 자동 감지
```python
if content[:4] == b'PK\x03\x04':  # ZIP 시그니처 = XLSX
    return self._parse_xlsx(content, parser_type, etf_symbol)
```

## ETF XLSX iter_rows 소비 문제 (#17)

- 증상: XLSX 파싱 시 0개 holdings 반환
- 원인: `ws.iter_rows()`는 제너레이터, 헤더 검색 시 소비됨
- 해결: `list(ws.iter_rows(values_only=True))`로 미리 변환

## ETF Holdings 중복 키 제약 위반 (#18)

- 증상: "duplicate key value violates unique constraint" (ICLN 등)
- 원인: 동일 종목이 CSV에 2회 등장 (다른 클래스)
- 해결: 중복 ticker 감지 후 weight 합산
```python
seen = {}
for h in holdings:
    if h['symbol'] in seen:
        seen[h['symbol']]['weight'] += h['weight']
    else:
        seen[h['symbol']] = h
```

## 프론트엔드 API URL 중복 (#19)

- 증상: ETF 동기화 등 API 호출 시 404 에러
- 원인: `.env`에 `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` 설정되어 있는데, 코드에서 `${API_BASE}/api/v1/...` 사용
- 해결: 코드에서 중복 `/api/v1` 제거
```typescript
// ✅ 올바른 방법
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const url = `${API_BASE}/serverless/etf/sync`;
```

## Next.js dev lock 파일 충돌 (#20)

- 증상: `npm run dev` 실행 시 "Unable to acquire lock at .next/dev/lock" 에러, 브라우저 접속 불가
- 원인: 이전 `next dev` 프로세스가 비정상 종료되면서 `.next/dev/lock` 파일이 남아있음
- 해결: `package.json`에 `predev` 스크립트 추가하여 dev 실행 전 lock 파일 자동 삭제
```json
{
  "scripts": {
    "predev": "rm -f .next/dev/lock",
    "dev": "next dev"
  }
}
```
- 참고: npm은 `dev` 실행 전 `predev`를 자동 실행 (npm lifecycle hooks)

## Chain Sight 카테고리 count만 표시되고 종목 목록 빈 배열 (#21)

- 증상: ETF 동반 종목(107개), 테마 종목(33개) 등 카테고리 count는 보이지만 클릭 시 종목 목록이 빈 배열
- 원인: `get_category_stocks()`에서 `relationship_type`이 있으면 모두 `StockRelationship` 모델에서 조회했으나, `ETF_PEER`와 `HAS_THEME`는 각각 `ETFHolding`/`ThemeMatch` 모델에 저장됨
- 핵심: **카테고리 count 계산 모델과 종목 조회 모델이 불일치**
- 해결: `chain_sight_stock_service.py`에서 타입별 분기 처리
```python
# ❌ 잘못된 방법 (모든 relationship_type을 StockRelationship에서 조회)
if category.get('relationship_type'):
    stocks = self._get_relationship_stocks(symbol, category['relationship_type'], limit)

# ✅ 올바른 방법 (타입별 적절한 모델에서 조회)
rel_type = category.get('relationship_type')
if rel_type == 'ETF_PEER':
    stocks = self._get_etf_peer_stocks(symbol, limit)        # ETFHolding 모델
elif rel_type == 'HAS_THEME':
    stocks = self._get_theme_stocks(symbol, theme_id, limit)  # ThemeMatch 모델
elif rel_type:
    stocks = self._get_relationship_stocks(symbol, rel_type, limit)  # StockRelationship
```
- 교훈: 새 카테고리 추가 시 count 계산과 종목 조회가 **같은 모델/쿼리**를 사용하는지 반드시 확인

## 재무제표 저장 시 모델 필드명 불일치 (#22)

- 증상: 모든 종목의 재무제표가 `balance_sheets: 0, income_statements: 0, cash_flows: 0`으로 저장됨
- 원인: `stock_service.py`의 `update_or_create(defaults=...)` 에서 사용하는 키가 Django 모델 필드명과 불일치
- 해결: 6개 필드명 수정 (`stock_service.py`의 `_save_balance_sheets`, `_save_income_statements`, `_save_cash_flows`)
```python
# ❌ 잘못된 필드명 → ✅ 올바른 모델 필드명
'fiscal_date_ending'        → 'reported_date'                          # 3개 모델 전체
'reported_currency'         → 'currency'                               # 3개 모델 전체
'cash_and_cash_equivalents' → 'cash_and_cash_equivalents_at_carrying_value'  # BalanceSheet
'accounts_payable'          → 'current_accounts_payable'               # BalanceSheet
'depreciation_amortization' → 'depreciation_depletion_and_amortization'  # CashFlowStatement
'change_in_cash'            → 'change_in_cash_and_cash_equivalents'    # CashFlowStatement
```
- 교훈: Normalized 데이터클래스 필드명과 Django 모델 필드명은 다를 수 있음. 저장 전 반드시 모델 필드 확인

## FMP 프리미엄 전용 심볼 402 에러 (#23)

- 증상: BRK.B, BF.B 등 `.` 포함 심볼에서 FMP 402 에러 + 3회 재시도 + Alpha Vantage fallback도 실패
- 원인: FMP Starter Plan에서 `.` 포함 심볼(Share Class 구분) 미지원
- 해결:
  1. `fmp/client.py`: `FMPPremiumError` 예외 추가, 402 시 재시도 없이 즉시 실패
  2. `fmp/provider.py`: `FMPPremiumError` catch → `PREMIUM_ONLY` 에러코드 반환
  3. `stocks/tasks.py`: `sync_sp500_financials`, `bulk_sync_sp500_financials`에서 `.` 포함 심볼 자동 제외
- 참고: `docs/infrastructure/fmp-premium-symbols.md`에 전체 목록 문서화

## Next.js Client Component에서 Date.now() hydration 불일치 (#24)

- 증상: "Hydration failed because the server rendered text didn't match the client" 에러
- 원인: Next.js App Router는 `'use client'` 컴포넌트도 서버에서 pre-render함. 모듈 레벨 `Date.now()`가 SSR 시점과 CSR hydration 시점에 다른 값을 생성 → 렌더링 결과 불일치
- 사례: Mock 데이터에서 `new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString()` 사용 → `relativeTime()` 결과가 서버("3시간 전")와 클라이언트("5시간 전")에서 다름
- 해결: 고정 ISO 문자열 사용 또는 `useEffect`/`useState`로 클라이언트 전용 렌더링
```tsx
// ❌ 잘못된 방법 (모듈 레벨 Date.now() — SSR/CSR 불일치)
export const MOCK_DATA = {
  created_at: new Date(Date.now() - 3 * 3600000).toISOString(),
}

// ✅ 올바른 방법 1: 고정 값
export const MOCK_DATA = {
  created_at: '2026-03-11T07:00:00Z',
}

// ✅ 올바른 방법 2: 클라이언트 전용 (suppressHydrationWarning)
<span suppressHydrationWarning>{relativeTime(dateStr)}</span>

// ✅ 올바른 방법 3: useEffect로 클라이언트 전용 렌더링
const [time, setTime] = useState('')
useEffect(() => setTime(relativeTime(dateStr)), [dateStr])
```
- 교훈: **Next.js Client Component는 서버에서도 실행됨**. `Date.now()`, `Math.random()`, `new Date()` 등 비결정적 값을 모듈/컴포넌트 레벨에서 직접 사용하면 hydration 불일치 발생. 시간 기반 렌더링은 반드시 클라이언트 전용으로 처리

## pytest가 운영 Redis 캐시를 flush (#27)

- 증상: `/chainsight` 접속 시 "섹터를 선택하세요"만 표시. API 응답은 200이지만 `seeds=[], sector_summary=[]` 빈 배열. Celery Beat 태스크는 성공 기록(TaskResult SUCCESS)인데 Redis DB=1에 `chainsight:seeds:{date}` 키가 사라짐
- 원인: `tests/conftest.py`의 `@pytest.fixture(autouse=True) clear_cache_after_test`가 매 테스트 종료마다 `cache.clear()` 호출. Django `default` 캐시가 `redis://127.0.0.1:6379/1` (운영)인데 테스트용 override 없이 같은 DB 사용 → django-redis의 `cache.clear()`가 **`FLUSHDB`로 Redis DB=1 전체 삭제**. 운영 시드/시그널/섹터 그래프 캐시 모두 증발
- 감지 단서: Redis uptime 44일(재시작 아님), `evicted_keys=0, maxmemory=0`(eviction 아님), TaskResult는 SUCCESS → 저장은 성공했으나 TTL 만료 전에 소실. `.pytest_cache/` mtime이 증발 시점과 일치
- 해결:
  1. `config/settings_test.py` 신설, `CACHES[default] = LocMemCache`로 override
  2. `pytest.ini`에 `DJANGO_SETTINGS_MODULE = config.settings_test`
  3. `conftest.py:clear_cache_after_test`에 `assert 'locmem' in backend` 안전 가드 추가 (실수로 운영 Redis 바라보면 즉시 실패)
  4. 시드 데이터를 `SeedSnapshot` 모델로 DB 영속화 — Redis 휘발해도 복구 가능
  5. `_get_today_seeds()` 3단 폴백: Redis → DB → async recovery 트리거 (setnx lock으로 중복 방지)
- 교훈: **운영 인프라(Redis, DB, 외부 API)와 테스트 인프라는 반드시 물리적으로 분리**. `django.core.cache.cache.clear()`는 KEY_PREFIX와 무관하게 FLUSHDB로 DB 전체를 삭제하므로 공유는 금물. Celery Beat 같은 "하루 한 번만 생성되는 운영 상태"는 Redis 단독에 두지 말고 DB에 영속화할 것. [상세: sub_claude_md/chain-sight.md `SeedSnapshot`]

## Celery Beat schedule drift — config dict vs DB PeriodicTask 불일치 (#28)

- 증상: `config/celery.py`의 `beat_schedule` dict에 정의한 태스크인데 `TaskResult`에 실행 이력 0회. 스케줄에 표시된 시간이 지나도 돌지 않음
- 원인: `settings.py`가 `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'` 사용 → **`app.conf.beat_schedule` dict는 런타임에 완전히 무시됨**. 진실의 소스는 DB `django_celery_beat.PeriodicTask` 테이블. DB에 등록 안 된 태스크는 dict에만 있어도 실행되지 않음
- 사례: `chainsight-heat-score-daily` (Heat Score 배치), `sec-seed-relations-to-chainsight` (SEC 10-K → Chain Sight 관계 동기화) 두 태스크가 처음부터 DB 미등록 상태로 방치 → Neo4j `:Stock`에 heat_score 값이 한 번도 기록된 적 없어 시드 선정 입력 품질 저하
- 감지: `set(config dict 키) - set(PeriodicTask.objects.values_list('name', flat=True))` 로 drift 체크
- 해결:
  1. `PeriodicTask.objects.update_or_create(name=..., defaults={'task': ..., 'crontab': CrontabSchedule(...), 'enabled': True})` 로 DB 등록
  2. `PeriodicTasks.update_changed()` 호출 → Beat가 다음 tick에 schedule reload (beat log에 `DatabaseScheduler: Schedule changed.` 찍힘)
  3. 수동 실행(`task_fn()`) 혹은 `task_fn.delay()`로 즉시 동작 검증
  4. `config/celery.py` 상단 주석에 "이 dict는 reference 용도, 실제 스케줄은 DB" 명시
- 교훈: **`DatabaseScheduler`를 쓰면 config의 `beat_schedule` dict는 선언적 reference로만 기능**. 스케줄 추가 시 반드시 Django admin 또는 `PeriodicTask.objects.create()`로 DB에 등록해야 실행됨. 코드 리뷰 시 "dict에 추가했으면 됐지" 착각에 주의. `celery -A config beat` 프로세스 자체의 생존 확인도 필요 (`ps aux | grep 'celery.*beat'`)
- 항구 해결 (2026-06-01, PR8b-2 Track A): **task 이동/리네임 시 `sync_beat_schedule` reconcile 커맨드 + beat 재시작 절차로 표준화**. 일회용 shell one-liner를 더 이상 쓰지 않는다.
  ```bash
  # source-of-truth = config/celery.py beat_schedule dict
  poetry run python manage.py sync_beat_schedule              # dry-run, diff 출력만
  poetry run python manage.py sync_beat_schedule --apply      # 실제 DB UPDATE (task 컬럼만)
  poetry run python manage.py sync_beat_schedule              # 0 rows (idempotent 검증)
  # 운영에서는 위 절차 후 반드시 celery beat 재시작 (스케줄러 캐시 갱신)
  brew services restart celery-beat   # 또는 systemd: systemctl restart celery-beat
  ```
  - 위치: `apps/market_pulse/management/commands/sync_beat_schedule.py`. 테스트: `tests/marketpulse/test_sync_beat_schedule.py` 4건 (dry-run / apply+idempotent / extra-db 보존 / missing-db 경고).
  - 정책: schedule/crontab/enabled 등 다른 필드는 안 건드림. **task 경로 컬럼만 reconcile**. dict 부재 name 은 보존(extra 정보 출력). dict 에 있지만 DB 부재 name 은 경고만(생성 안 함).
  - 첫 적용 (2026-06-01 dev): 누적 75 row reconcile (macro 5 + serverless / news / chainsight / stocks / validation / sec_pipeline 70). monorepo PR4~PR8a 누적 드리프트가 한 번에 정리됨. 운영 DB 적용은 **사용자 트리거** (`--dry-run` 확인 → `--apply` → beat 재시작).

## `timezone.now().date()`가 KST 자정~오전 9시에 잘못된 날짜 반환 (#29)

- 증상: KST 자정~오전 9시 사이에 news/market_feed/ml_weight_optimizer 등에서 "오늘 날짜" 기반 쿼리·필터·문자열 생성이 어긋남. 예) `select_for_analysis()`가 어제 기사를 포함, `_enrich_keywords_with_news()`의 news_count=0, `_generate_version()`의 count가 증가하지 않음 (`assert 1 > 1`)
- 원인: `USE_TZ=True` + `TIME_ZONE='Asia/Seoul'` 환경에서 `timezone.now()`는 **항상 UTC aware datetime**을 반환. 따라서 `timezone.now().date()`도 **UTC date** (KST date 아님). 의도는 KST "오늘"인데 UTC date를 사용 → KST 자정~오전 9시(=UTC 15시~UTC 0시) 사이 두 date가 1일 차이. `make_aware(combine(today, ...))`가 KST 기준으로 처리되면서 cutoff가 어제 KST 15시 기준으로 형성됨. ORM `__date` lookup은 connection.timezone(KST) 기준이라 `__date=timezone.now().date()`(UTC)와도 어긋남
- 감지 단서: 동일 테스트가 KST 점심에는 통과, KST 새벽에는 실패. 야간 자동화 결과(2089 passed)와 다음날 아침 회귀가 다른 결과를 내면 timezone 의심. `test_old_articles_not_selected`가 가장 명확한 단서 (어제 기사가 "오늘" 윈도우에 포함되는지)
- 해결:
  1. `timezone.now().date()` → `timezone.localdate()` 일괄 치환 (`USE_TZ=True` 환경에서 default tz 기준 date 반환)
  2. `timezone.now().strftime(...)` → `timezone.localtime().strftime(...)`
  3. `tz.now().date()` 등 alias 패턴도 동일 처리
  4. ORM `__date` lookup의 비교값도 `localdate()` 사용 (connection.timezone과 정렬)
- 영향 범위 (운영 코드 22개 파일, 49건): news/services/_*, news/api/views.py, serverless/_*, chainsight/tasks/seed_tasks.py, macro/_*, thesis/_*, sec_pipeline/intelligence.py, rag_analysis/models.py, config/management/commands/celery_errors.py 등
- 교훈: **`USE_TZ=True` + non-UTC `TIME_ZONE`이면 `timezone.now().date()` 사용 금지**. 항상 `timezone.localdate()` 또는 `timezone.localtime().date()`. CI는 UTC로 도는 게 일반적이라 잘 안 잡히고, 한국 운영 환경의 자정~오전 9시 구간에서 잠복하다 회귀로 드러남. 날짜 의존 테스트는 freezegun 등으로 시간 고정 권장

## 문서·git 정합성 stale 패턴 (#30)

- 증상: PROGRESS.md·TASKQUEUE.md·Claude 메모리가 git 현실과 어긋남
  - 예 1: PROGRESS에 `origin/main = be2d6c7` 표기, 실제 `git rev-parse origin/main` = `3e76bc8` (2 commits 차이)
  - 예 2: PROGRESS가 worktree 보존이라 표기한 `/Users/.../stock_vis_chainsight_v2` 폴더 실제 부재 (PR-#8 머지 후 정리됐는데 표기 안 갱신)
  - 예 3: TASKQUEUE 한 항목이 `todo` 표기, 실제로는 외부 PR 머지로 완료된 상태 (CS-R9 사례)
  - 예 4: PROGRESS 마지막 갱신 후 16일간 167 commits 누적, PROGRESS는 4회만 변경 (모두 5/12 시점)
  - 예 5: 메모리에 박힌 brunch/HEAD 정보가 stale PROGRESS를 캐시한 결과물 → PROGRESS 갱신 안 하면 메모리도 stale
  - 예 6: slice 격리 brunch 143 commits이 origin/main에 0% 반영, 누적 후 단일 시점 통합 시 충돌 위험
- 원인:
  - **수동 유지 의존** — 매 슬라이스 종결 시 PROGRESS 갱신 의무 명시됐으나 brunch 격리 작업 + main 정착 단계 지연 + 외부 자동화 audit commit 끼어들기 등 복합 원인으로 누락 발생
  - **다중 진실의 소스** — git, PROGRESS, TASKQUEUE, DECISIONS, 메모리가 모두 "현재 상태"를 표기하는데 동기화 통로 부재
  - **검문소 부재** — stale 발생을 감지할 자동 검증 없음. 사람·에이전트가 PROGRESS 읽을 때만 우연히 발견
- 감지: `python scripts/health_check.py` 5건 항목 자동 검증
  - exit 0 = OK, 1 = warning (작업 진행 가능, 정리 시 보정), 2 = error (다른 작업 전 보정 우선)
  - 검증 항목: origin/main 해시 표기 / brunch·worktree 존재 / PROGRESS 갱신 stale / TASKQUEUE done 매칭 / DECISIONS 갱신일 / slice* 미머지 (보조)
- 해결:
  1. **scripts/health_check.py 정기 실행** — 매 세션 시작 시 `python scripts/health_check.py` 우선 실행, warning 이상 발견 시 작업 전 보정
  2. **PROGRESS.md 자동/수동 영역 분리** — origin/main 해시·brunch 현황 등은 health_check 출력을 토대로 갱신, blocker/결정/작업 단위는 사람·에이전트 수동
  3. **TASKQUEUE done 표기는 외부 PR 머지 직후 즉시 갱신** — 머지 commit 매칭이 진실 기준
  4. **메모리는 PROGRESS의 캐시로만 다룸** — PROGRESS가 진실 소스, 메모리에 표기 차이 발견 시 PROGRESS 먼저 갱신 후 메모리 갱신
  5. Layer 1~4 단계화 도입 (DECISIONS.md "문서·git 정합성 관리 원칙" 참조)
- 교훈: **stale은 1회성 실수가 아니라 시스템적 결함**. 매 세션 시작 시 검문소(health_check.py) 통과를 의무화. 16일 stale + 6 패턴 동시 발현(2026-05-28)이 시그널 — Layer 1(즉시) + Layer 2(monorepo 도입 시) + Layer 3(pre-commit hook) + Layer 4(`make progress` 완전 자동화) 단계 도입으로 재발 차단
- 야간 자동화 통합 메모 (2026-05-28~, 단계 1):
  - `scripts/run_health_check_nightly.sh` wrapper가 매일 23:00 nightly_v3.sh Phase 5에서 호출되어 `docs/nightly_auto_system/YYYYMM/DD/health_check.json`에 정합성 누적 기록 저장
  - 검증 7 항목: origin/main 해시 / brunch·worktree 존재 / PROGRESS stale / TASKQUEUE 매칭 / DECISIONS 신선도 / slice* 미머지 / **외부 자동화 commit 감지 (#71 close monitoring)**
  - **사용자에게 자동 알림 없음** — 다음 세션 시작 시 또는 주기적으로 직접 health_check.json 확인 필요. `find docs/nightly_auto_system -name health_check.json -mtime -7 | xargs jq '.[] | select(.status >= 1)'` 패턴으로 최근 7일 warning/error 일괄 점검 가능
  - 알림 임계는 **단계 2 (2026-06-중 예정)에서 1~2주 관찰 데이터 위에서 결정** — false positive 분포 + 실제 stale 빈도를 보고 warning vs error 라인을 잡는다. 이메일/Slack 알림 채널도 그 시점에 정함
  - wrapper는 항상 exit 0 — nightly 전체가 fail로 잡히지 않게. 실제 health_check exit code는 JSON 본문 status 필드로 보존
- 📎 참조: `scripts/health_check.py`, `scripts/run_health_check_nightly.sh`, `docs/infra/nightly_v3.sh` Phase 5, `DECISIONS.md` "문서·git 정합성 관리 원칙", `PROGRESS.md` "정합성 문제 발견 (2026-05-28)" 섹션

## FMPClient 동명 3 모듈 — namespace 통합 (#32, 2026-06-01 1단계 종료)

- 트리거: PR8b-2 reachability 판정에서 발견 (2026-06-01). `FMPClient`라는 이름의 클래스가 **서로 다른 3 모듈**에 존재하며, 책임·인터페이스가 다르다.
- **1단계 종료 (2026-06-01, `ccbdce5`)**: 3 모듈을 `packages/shared/api_request/providers/fmp/` 아래 격자로 모음. 클래스 이름은 유지(행위보존), 모듈 경로만 통일. "동명 3곳" 신호어는 해소.

  | 현재 모듈 경로 | 역할 | 주 소비처 |
  |---|---|---|
  | `packages.shared.api_request.providers.fmp.client.FMPClient` | **canonical** — Premium/RateLimit/Auth 에러 분리, 재무제표·검색·뉴스 | thesis, FMPNewsProvider |
  | `packages.shared.api_request.providers.fmp.market_pulse_client.FMPClient` | Market Pulse v1 거시 도메인 (Quote / 지수 / Calendar / Sector / Forex / Commodities) | `apps.market_pulse.services.macro_service` |
  | `packages.shared.api_request.providers.fmp.serverless_client.FMPClient` | 레거시 serverless (FMPAPIError, screener / market movers / sp500 constituents / OHLCV) | `packages.shared.stocks.services.sp500_*`, serverless 다수 |

- 규칙: **항상 절대 경로로 import** (`from packages.shared.api_request.providers.fmp.<sub>_client import FMPClient` 패턴). 상대경로 `from .fmp_client` 금지.
- 2단계 부채 (별도 트랙): canonical(`client.py`)이 나머지 2개를 흡수하는 메서드 단일화. 24개 메서드 갈라짐(거시 11 + 레거시 8 + 재무 13) + 에러 정책 통일(`FMPClientError`/`FMPAPIError` 합치기) 필요. **행위보존 경계** 위반 위험이라 별도 사이클 (사용자 트리거).
- 📎 참조: `sub_claude_md/common-bugs.md #23` (FMP 402 / Premium 에러 패턴), `DECISIONS.md` "버킷A — FMP 통합 1단계"

## shared 역방향 import 5건 — 전건 청소 완료 (#31, 2026-06-04 종결)

- 트리거: PR8b STEP 0 fact-check (2026-06-01) — `packages/shared/`가 거꾸로 `apps/*`·`macro`를 import하는 5건 검출. shared는 단방향 base 경계이므로 위반.
- 위반 5건 (전건 ~~CLOSE~~):
  | # | 파일 (packages/shared/ 기준) | import module | 형태 | CLOSE |
  |---|---|---|---|---|
  | ~~1~~ | `stocks/services/sp500_eod_service.py:15` | `apps.market_pulse.utils.circuit_breaker` | top-level | 2026-06-01 BOUNDARY-1 |
  | ~~2~~ | `stocks/services/sp500_service.py:13` | `apps.market_pulse.utils.circuit_breaker` | top-level | 2026-06-01 BOUNDARY-1 |
  | ~~3~~ | `metrics/services/daily_report.py:242` | `apps.chain_sight.models` | 함수 내 lazy | 2026-06-01 BOUNDARY-2 |
  | ~~4~~ | `stocks/services/eod_regime_calculator.py:77` | `macro.models` | 함수 내 lazy | 2026-06-04 BOUNDARY-3 |
  | ~~5~~ | `stocks/services/eod_pipeline.py:617` | `macro.models` | 함수 내 lazy | 2026-06-04 BOUNDARY-3 |
- 감지: `tests/architecture/test_shared_boundary.py` — `ast.parse`로 전수 검출. KNOWN_VIOLATIONS에 없는 신규 위반은 pytest FAIL.
- 보조: `scripts/health_check.py` 8번째 항목 `shared 경계` — 우회 0 ✅ / 우회 ≥1 ❌. 동결 0건 도달(burn-down 5→3→2→0).
- 야간 추적: `docs/harness/boundary_ledger.jsonl` — burn-down 한 줄/일. **자동 수정 없음, read-only.**
- 청소 트랙별 패턴:
  1. ~~`BOUNDARY-1`~~ **CLOSE 2026-06-01** (#1·#2): circuit_breaker → `packages/shared/api_request/` 승격, shared→shared 정합. burn-down 5→3.
  2. ~~`BOUNDARY-2`~~ **CLOSE 2026-06-01** (#3): `apps.get_model("chainsight", "CompanyChainProfile")` 동적 lookup으로 정적 import 제거(cross-app aggregator 표준). burn-down 3→2.
  3. ~~`BOUNDARY-3`~~ **CLOSE 2026-06-04** (#4·#5): **의존 역전 + 등록 패턴** = `VIXProvider` 포트를 `packages/shared/stocks/services/`에 두고, `MacroVIXProvider` 구현체는 `apps/market_pulse/services/`에 두고, `MarketpulseConfig.ready()`에서 `register_vix_provider(MacroVIXProvider())` 등록. shared 코드는 apps를 lazy로라도 import하지 않음(주석/예외 메시지의 문자열 언급은 ast 검사 비대상). 모델 이동 0 / 마이그레이션 0 / 회귀 302 GREEN. burn-down 2→0. 머지 `a9bb229` (slice [33e5437..662fdc4]).
- 교훈: 단방향 경계는 **검문소가 없으면 새 우회가 PR마다 슬며시 추가**된다. PR8b STEP 0에서 5건이 한꺼번에 드러난 게 시그널. monorepo 단계마다 경계가 새로 생기면 즉시 ast 기반 아키텍처 테스트를 박는 게 비용 가장 싸다.
- 패턴 정착(BOUNDARY-3): **포트 + apps.ready() 등록**이 모델 이동 없이 macro→shared 의존 방향을 안전하게 끊는 표준. shared 내부 역의존(tasks·mgmt·다른 service)이 있어 "소비자 이동(방향1)"이 막힐 때 1순위 후보.
- 📎 참조: `docs/harness/SHARED_BOUNDARY_GUARD.md`, `tests/architecture/test_shared_boundary.py`, `scripts/health_check.py:check_shared_boundary`, `DECISIONS.md` "shared 경계 검문소 (2026-06-01)" + "BOUNDARY-3 (2026-06-04)"
