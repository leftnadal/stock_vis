# 자주 발생하는 버그·재발 함정 KB

> **이 파일의 역할**: 재발하는 함정·버그의 **1차 소스**. **판정 기준** = *"다음 세션이 몰라서 시간을 날리거나 사고를 낼 수 있는가?"* — Yes면 여기, No면 보고서/PROGRESS.
> 일회성 수치·PID·날짜 디테일 **자체**는 여기 대상이 아니다. 진단 체크리스트·재발방지 규칙으로 **일반화**해 남긴다. 상세 incident 로그는 `docs/nightly_auto_system/triage/` 또는 PROGRESS.
>
> **역할 분담** (KB 1차 소스 경계):
> | 종류 | 1차 소스 |
> |------|----------|
> | 순수 함정·버그 (증상→원인→해결) | **이 파일 (common-bugs)** |
> | 아키텍처 결정·근거(Why) | **`DECISIONS.md`** |
> | 어디에도 안 맞는 운영 교훈(프로세스 규율) | common-bugs 내 `[process]` 태그로 표기 |
>
> **카테고리 태그 컨벤션** (검색·골라읽기용, 제목 끝에 `[태그]` 표기): `[git]` `[data]` `[indicator]` `[infra]` `[boundary]` `[process]`
>
> **동기화**: 새 버그 → 이 파일 **먼저** → `shared_kb` 큐 → (세션 종료 의식) 검색KB 드레인. 큐는 종착지가 아니라 백업·검색용 복사본. 상세 [CLAUDE.md "common-bugs.md ↔ KB 동기화 원칙"].
> **채번**: 신규 번호는 origin/main 말미에서만 채번(브랜치별 독립 증식 금지). 과거 중복 번호(#31·#33)는 이력 보존상 미정정 — 참조 시 제목으로 식별.

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
- 예방: 코드의 task 경로(app_label/모듈)가 바뀌면 Beat DB(PeriodicTask)의 `task` 컬럼은 자동으로 따라오지 않는다. 배포/마이그레이션 절차에 `python manage.py setup_marketpulse_beat` 재실행을 포함해 DB `task` 경로를 코드와 재동기화할 것. (marketpulse는 `config/celery.py`의 `beat_schedule` dict가 아니라 `setup_marketpulse_beat` 커맨드가 DB 직접 등록 → `sync_beat_schedule`로는 갱신되지 않음.)
- 드리프트 발생 시 즉시 수정: `task` 컬럼만 ORM UPDATE(옵션②, 부작용 0) 또는 `setup_marketpulse_beat` 멱등 재실행(옵션①, 전 필드 덮어씀). 동시에 좀비 beat(launchd 외 프로세스) 유무도 점검 (`ps aux | grep 'celery.*beat'` → 1개여야 함).
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

> **#31 (shared 역방향 import 5건 — 전건 청소 완료, 2026-06-04)** `[boundary]` → **종결**: 본 파일 말미 [아카이브 섹션](#아카이브-종결일회성--이력-보존)으로 이동. 재사용 패턴(포트+`apps.ready()` 등록)은 `DECISIONS.md` "BOUNDARY-3 (2026-06-04)"에 보존. 검문소: `tests/architecture/test_shared_boundary.py`.

## 좀비 Beat (다중 process) — 메일 2회 발송 + Bug #28 재발 (#33, 2026-06-06)

- 증상: 매일 같은 daily report 메일 2회 발송 (07:00 KST + 약 6~7분 뒤), `celery-worker-error.log`에 `Received unregistered task of type 'marketpulse.tasks.regime.mp_calc_regime_15min'` 반복 (Bug #28 패턴이지만 DB·dict는 정합 상태).
- 근본 원인: **celery beat 프로세스가 1개가 아니라 2개**. 정상 1개(launchd `com.stockvis.celery-beat`, DatabaseScheduler) + 좀비 1개(터미널에서 수동 기동, default scheduler). 좀비가 옛 task name(prefix가 다름)으로 발사하면 워커는 KeyError, 같은 일정의 다른 task는 메일 2회 발사.
- 본 사건 좀비 메타: PID 56670, PPID 13862(부모 셸 살아있음, orphan 아님), cwd=`~/.Trash/stock_vis.icloud_backup.20260516_144329` (5/16 iCloud sync OFF 후 Trash로 옮겨진 옛 코드 트리), 시작 5/21 10:06, 종료 6/6 21:30, 16일간 invisible. 부모 셸이 `/dev/ttys003`에 묶여 있어 SIGHUP 안 받고 생존.
- 진단 체크리스트:
  1. `ps aux | grep -E "celery.*beat" | grep -v grep` → 행이 2 이상이면 좀비 의심
  2. `lsof -p <PID> | grep cwd` → cwd가 `.Trash` / 백업 경로 / 옛 트리면 좀비 확정
  3. 워커 에러 로그의 task 헤더 `origin` 필드(`genXXXX@host`)에서 PID 추출 → 의도하지 않은 PID면 그 process가 좀비
  4. `TaskResult` (`django_celery_results`) — 같은 task가 짧은 간격(수 분)으로 2회 SUCCESS면 Beat 다중성 의심
- 조치: `kill <좀비_PID>` (SIGTERM). PersistentScheduler는 schedule을 in-memory만 갖고 lsof에 schedule 파일이 안 보이면 영구 소실, 재기동 불가 (무해).
- 행위보존: 정상 Beat(launchd) 무영향. 워커 무영향. 메일 발송 정상 회복(1회/일).
- 재발 방지 (NT-11 가드 트랙, 가드 범위 결정 대기):
  - watchdog 또는 daily report에 `ps -e | grep "celery.*beat" | wc -l > 1` 감지 룰 추가 → 즉시 알림.
  - 가드는 **origin 기반**이 좋음 (cwd가 정상 트리(`Desktop/stock_vis`) 밖이면 좀비 가능성 ↑).
  - 정상 Beat는 항상 `--scheduler django_celery_beat.schedulers:DatabaseScheduler` 명시 — `ps aux`에서 옵션 없는 beat는 좀비.
- 📎 참조: `DECISIONS.md` "좀비 Beat 56670 = 5/21 Trash stray 기동의 잔불 (2026-06-06)", `TASKQUEUE.md` NT-10/NT-7/NT-11, `_briefs/2026-06-06/sprint_a1_ops_singletons.md` STEP 0 결과
- 🧭 정본 규칙(S4-1): 이 항목(**함정·진단 체크리스트**)이 common-bugs 정본, DECISIONS는 **결정·근거(왜 좀비였나)** 정본 — **의도적 facet 분리이지 중복 아님**(둘 중 하나를 "dedup"으로 삭제 금지). PROGRESS 언급은 캐시. 큐 복사본은 검색KB로 드레인 완료(2026-06-17).

## 잘못된 경로 grep = 거짓 0% 측정 (#31)

- 증상: STEP 0 측정에서 `grep -rEn "market_pulse" frontend/src/` → 0건 → "K/L 프론트엔드 0% 부재"로 보고. 실제는 `frontend/app/market-pulse-v2/`에 page.tsx + 5 Summary + 5 Detail + 5 패널 + API 클라이언트 30+ 타입이 **이미 전건 구현**되어 있었음.
- 원인: 모노레포가 `frontend/src/` 가 아니라 `frontend/app/` 직접 구조(Next.js 16 app router)인데 측정 에이전트가 `frontend/src/` 경로를 가정하고 grep. **검색 경로 자체가 부재**하면 grep 결과 0건은 "그 경로에 없음" = "어디에도 없음"이 아님. 의미 혼동.
- 사례: 2026-06-07 Explore agent의 Phase 1 카탈로그 역산 STEP 0 측정. K/L "0%" 보고 → DECISIONS L1352 / TASKQUEUE MP1-K/L `(TBD frontend/src/...)`까지 stale 경로가 박혀 mgmt 사이클 1회 분량(3일) 동안 잘못된 진실로 유통됨. 2026-06-10 보강 STEP 0에서 `ls frontend/` 1회 실행으로 즉시 발각.
- 감지: 측정 결과가 "0건" / "부재"일 때 검색 경로 자체의 실재 여부를 확인. `ls <경로>` 또는 `test -d <경로>` 가 첫 번째 검증 단계.
- 해결:
  1. **경로 실재 확인을 grep 보다 먼저**: `find <repo_root> -maxdepth 2 -type d -name "<후보>"` 로 후보 경로의 존재를 먼저 검증한 뒤 grep 수행.
  2. **0건 결과를 기록할 때 검색 경로 명시**: "grep `<pattern>` `<path>` = 0건"으로 path를 같이 박아야 후속 측정자가 path 자체를 의심할 수 있음. path 없이 "0건" / "부재" 로만 기록하면 잘못된 진실이 단정으로 굳어짐.
  3. **`find <repo_root> -name "<symbol>*"` 광역 1회 병행**: 특정 경로 grep과 별개로 repo 전수 find로 같은 심볼이 다른 디렉토리에 있는지 cross-check. 본 사례에선 `find frontend -name "market*"` 1회로 즉시 발각 가능.
- 교훈: **측정도 메모리만큼 위험**. 측정 결과가 단정(0%, 부재)일수록 경로 가정의 검증이 필수. 메모리·문서 stale은 자동 검증(health_check)이 잡지만, 측정 경로 가정의 stale은 다음 측정 사이클에서야 발각 — 사이클 사이 잘못된 결정(완료/잔여/우선순위)을 누적시킴. **0건 보고는 항상 "어디서 0건인지" + "그 어디가 실재하는지" 둘 다 명시**.
- 📎 참조: `DECISIONS.md` "[2026-06-10] K/L static 완료 + 라이브 검증 출시 게이트 분리 (옵션 C)", TASKQUEUE `MP1-K/L` 행 stale 경로 정정 이력.

---

> **번호 비고 (2026-06-11)**: 직전 말미가 `#31` **중복**(line 362 "shared 역방향 import" + 위 "잘못된 경로 grep")이고 `#32`(FMPClient 동명 3 모듈, line 347)가 이미 점유되어 있어, 신규 3건은 **#33~#35**로 등록(지시서 `#32~34`에서 +1 조정). 기존 #31 중복은 범위 외로 미수정.

## fetch 없는 baseline 판단 = 갈라진 토대 위 작업 (#33)

- 증상: 로컬 `main` ref로 origin 상태를 추정하고 그 위에서 작업 → 우리가 push한 최근 5 commit이 부재한 **갈라진 토대**(merge-base `d4a9690`)에서 진행. 회귀 기준선이 어긋나(`pytest 136` vs 정상 토대 `138`) 발각.
- 원인: 로컬 `main`이 `origin/main`보다 뒤처졌는데 `git fetch` 없이 로컬 ref를 진실로 가정. `ce0be51`(stress 훅 +2 테스트)가 origin/main엔 있고 로컬 토대엔 없어 baseline이 136으로 측정됨.
- 감지: 회귀 수치가 **알고 있는 기준선과 다르면** 토대 오류 신호. 정상 토대 138인데 136이 나오면 "테스트가 줄었다"가 아니라 "토대가 과거다"를 먼저 의심.
- 해결: baseline 검증은 **반드시 `git fetch origin` 후 `origin/main` 직접 측정**(`git rev-parse origin/main`). 작업 worktree HEAD == origin/main 확인을 STEP 0 표준 항목으로. 회귀 수치 불일치 시 HALT.
- 교훈: 로컬 ref는 캐시일 뿐 진실이 아니다. fetch 없는 baseline = stale 메모리와 동급 위험.
- 📎 참조: DECISIONS "[2026-06-11] MP-KL-F2 게이트 선행 + 복구 이식 기록".

## 공유 메인 디렉터리에서 세션 작업 = 타 트랙 커밋 혼입 (#34)

- 증상: 여러 트랙이 공유하는 메인 repo 디렉터리(`/Desktop/stock_vis`)에 작업 브랜치를 체크아웃하고 작업 → 동시에 도는 다른 트랙/자동화의 커밋이 **체크아웃된 브랜치에 혼입**.
- 원인: 단일 워킹 디렉터리에서 브랜치를 바꿔가며 작업하면 그 시점 체크아웃된 브랜치가 모든 커밋의 목적지가 됨. 본 사례: `82afddb`(trash 청산 트랙)가 F3·F2 커밋 사이에 끼어듦 — 로컬 main의 `cb5473e`와 **동일 메시지·별개 hash** 이중 commit으로 혼입 확정.
- 감지: `git log --oneline <base>..HEAD`에 작업과 무관한 주제의 커밋이 끼어 있으면 혼입. author/시각이 같아도 주제가 다르면 의심.
- 해결: **모든 세션은 전용 worktree**(`git worktree add ../sess-<track>-<task>`). `pwd`가 메인 디렉터리면 즉시 HALT를 지시서 표준 항목으로. 혼입 발생 시 깨끗한 토대로 `cherry-pick -x` 이식.
- 교훈: 디렉터리 격리는 브랜치 격리와 다르다. worktree = 트랙 동시 작업의 물리적 격리.
- 📎 참조: DECISIONS "[2026-06-11] 트랙별 소유권 지도 v2" 공통 규칙 5, 복구 이식 기록.

## 짧은 라벨 비고유 = 세션 모호성 (#35)

- 증상: 사용자가 `F1~F3`로 지시 → repo 내 감사 리포트 3종(6/8 api_dependency·6/8 beat_schedule·6/6 api_dependency)에 동명 `F1/F2/F3` 라벨이 있어 어느 것인지 특정 불가.
- 원인: `F1` 같은 짧은 라벨이 여러 문서에서 재사용됨. 전체 ID(`MP-KL-F1`) 없이는 비고유.
- 감지: 라벨 grep 시 복수 문서 매치 = 비고유 신호. (본 사례는 Claude Code가 HALT + 사용자 확인으로 정확히 대응)
- 해결: 항목 참조는 **전체 ID만 사용**(`MP-KL-F1`, `NT-7` 등). 지시서·장부 공통. 짧은 라벨 단독 지시 시 출처 문서 명시.
- 교훈: 라벨의 고유성은 네임스페이스에서 나온다. 트랙 prefix 없는 라벨은 검색 충돌을 부른다.
- 📎 참조: 2026-06-11 MP-KL 세션 진입 시 `F1~F3` 출처 특정 과정.

## 프로젝트 업로드 사본으로 repo 파일 덮어쓰기 (#36)

> **채번 규칙(2026-06-11)**: common-bugs 번호는 **origin/main 기준 말미에서만 채번**. 브랜치별 독립 증식 금지 — 미머지 브랜치(예: nt11)가 자체적으로 같은 번호를 달면 머지 시 충돌(2026-06-11 nt11 자체 #33 ↔ 본 트랙 #33 동시 존재 사례). 신규 번호 부여 전 origin/main 말미 확인 의무.

- 증상: 메인 디렉터리 working tree에 `docs/claude_project_instructions/project_convention_instruction.md` 미커밋 변경 — 마크다운 깨짐(`circuit_breaker`→`circuit*breaker`, `_직접_`→`*직접\_`) + "관리(mgmt)/ops 세션 범위" bullet 통째 삭제. origin/main엔 정상본 존재.
- 원인: 채팅 프로젝트에 **업로드된 참조 문서는 업로드 시점의 파생 사본**. 그 사본으로 repo 신본을 역방향 덮어씀. repo가 항상 원본 — 동기화는 **repo→프로젝트 단방향만** 허용.
- 감지: `git diff`에 의도하지 않은 마크다운 깨짐/내용 삭제가 보이고 repo 원본이 더 신선하면 역방향 덮어쓰기 의심.
- 해결: `git restore <파일>`로 origin/main 정상본 복원(단일 파일 한정). repo 문서 개정 시 각 프로젝트 업로드본 교체를 후속 항목으로 등록(repo→프로젝트 갱신).
- 교훈: 업로드 사본은 읽기 참조용 스냅샷. repo로의 역류 금지. 메인 디렉터리 미접촉 원칙(#34)이 이 역류도 차단.
- 📎 참조: 2026-06-11 worktree 정리 세션 — restore로 복구.

## ff 거부(로컬 main 분기) 시 즉시 HALT — merge 강행 금지 (#37) `[git]` `[infra]`

- 증상: `git merge --ff-only origin/main`이 `Not possible to fast-forward, aborting` 거부. 이때 곧바로 `git merge --no-ff <feature>`를 실행하면 **분기된 잘못된 base 위에 merge 커밋**이 생겨 prod·origin과 어긋남 (CS-M2-MERGE 사고, 2026-06-17, commit 15fa044).
- 원인 `[infra]`: **나이틀리 자동화(`com.stockvis.nightly` 감사 보고서)가 로컬 main에 직접 commit하고 push하지 않음**. 병렬 세션이 origin을 전진시키는 동안 로컬 main이 ahead(미push 커밋)/behind 양방향으로 분기됨. → 근본 해결은 자동화가 별도 브랜치를 쓰거나 commit 후 즉시 push 하는 것 (`TASKQUEUE.md MAIN-SYNC-FIX`, `DECISIONS.md` "MAIN-SYNC — ff 거부 = HALT").
- 감지: `git merge --ff-only origin/main` 거부 = 즉시 HALT 신호. 먼저 분기 구조 측정: `git rev-list --left-right --count origin/main...main`, `git log origin/main..main --no-merges`.
- 해결 (재발 방지 규칙):
  1. **ff-only 거부 = HALT**. merge 강행 금지. 분기 구조부터 측정.
  2. 로컬 main 미push 커밋의 정체를 먼저 파악 — docs/disjoint면 보존 가능, **코드 커밋이 섞이면 HALT·보고**.
  3. 분기 해소는 **rebase 금지**(미push 커밋 유실 위험), merge 전략만: `git merge --no-ff origin/main`(미push 보존 + origin 흡수) → behind 0 확인 → feature merge → push.
  4. 각 merge 후 `git status`로 완료/진행중 상태 반드시 확인 (직전 사고는 상태 오판).
  5. 잘못된 미push 머지커밋은 `git reset --hard <merge직전>`로 안전 복원 (reflog 복구 가능, push 전이면 무손실).
  6. 충돌은 하네스 문서(DECISIONS/PROGRESS/TASKQUEUE/.env.example)만 preserve-both 수동 해소, **코드/migration 충돌은 무조건 HALT**.
- 교훈: 로컬 main은 캐시일 뿐 진실이 아니다(#33 fetch baseline과 같은 뿌리). 세션 시작 시 `git fetch origin` 먼저, baseline은 `origin/main` 직접 측정.
- 📎 참조: `DECISIONS.md` "MAIN-SYNC — ff 거부 = HALT (2026-06-17)", `TASKQUEUE.md MAIN-SYNC-FIX`, 메모리 MAIN-SYNC/MP-OPS-RESTART 패턴, common-bugs #33(fetch baseline)·#34(worktree 격리).

## 동적 라우트 그룹명 이중 인코딩 → 상세 빈 목록 (#38) `[frontend]` `[chainsight]`

- 증상: 공백·`&` 포함 다단어 그룹명(`Communication Services`·`Robotics & AI` 등) 상세 페이지가 **빈 목록** + 제목이 `Communication%20Services`(인코딩된 채 노출). 보드에 뜨는 그룹도 상세는 깨짐(필터 누락 그룹 한정 아님). CS-RD3 QA 2026-06-23 발견.
- 원인 `[frontend]`: `EventBoard.tsx` 카드 클릭 `router.push(`/chainsight/events/${item.theme}`)`가 **encodeURIComponent 없이 raw push** → Next App Router param이 인코딩된 채 도착 → `fetchRanking`이 `encodeURIComponent`로 **또 인코딩**(이중) → 백엔드 `theme_tags__contains=[theme]` 조회 키 불일치 → 빈 목록. 단어1개 그룹(`Technology`)은 인코딩 무관해 정상 → 증상이 다단어 그룹에만 나타나 진단 지연.
- 감지: 상세 제목에 `%20`/`%26` 같은 percent-encoding이 그대로 보이면 이중 인코딩 신호. URL 바는 `Robotics%20&%20AI`(공백만 %20, `&`는 literal)처럼 혼합 인코딩.
- 해결: **인코딩은 단일 출처로** — 링크 생성 측(`router.push`)에 `encodeURIComponent(theme)` + 페이지 경계(`[theme]/page.tsx`)에서 `decodeURIComponent(theme)` 1회 디코딩. decodeURIComponent는 멱등(% 없으면 no-op)이라 Next 자동디코딩 여부와 무관하게 안전(그룹명에 literal `%` 없음 전제). fetchRanking의 encodeURIComponent는 그대로 두면 단일 인코딩으로 정합.
- 교훈: 동적 라우트 세그먼트에 사용자 표시 문자열(공백·`&`·한글)을 넣을 땐 **생성·소비 양측 인코딩 단계를 한 번씩만** 세고 왕복 테스트로 검증. 링크 생성 지점 전수 grep(누락 시 일부 진입로만 깨짐).
- 📎 참조: `DECISIONS.md` "[2026-06-23] chain_sight 소규모 그룹 — URL 인코딩 버그(ⓑ)", `frontend/components/chainsight/EventBoard.tsx`·`app/chainsight/events/[theme]/page.tsx`, 테스트 `routeReversal.test.tsx`(왕복 10건).

## verify용 클론은 PORT=3000 — 다른 포트는 CORS 차단('503'처럼 표면화) (#39) `[frontend]` `[infra]`

- 증상: verify용 깨끗한 클론을 `:3100` 등 비표준 포트로 띄우면, 로그인된 세션인데도 `/market-pulse-v2` 등 **전 인증요청이 실패** + 화면은 "데이터를 불러오지 못했습니다". 브라우저 네트워크 패널엔 BE overview/i18n이 **503**으로 찍히나, BE(daphne :18765) access 로그엔 503이 **0건**·전부 `401 Unauthorized`. `curl`(토큰 없음)로는 동일 엔드포인트가 401 — 모순처럼 보임. MP1.5-FIX 시각검증 2026-06-25 발견.
- 원인 `[infra]`: BE `CORS_ALLOWED_ORIGINS`(`config/settings.py:318`)에 **`http://localhost:3000`·`http://127.0.0.1:3000`만** 등록. `:3100` origin의 preflight(OPTIONS)는 **200이나 응답에 `Access-Control-Allow-Origin` 헤더(ACAO)가 누락** → 브라우저가 본응답을 차단 → axios는 `Network Error`. dev 프록시 계층이 차단된 요청을 **503으로 표기**해 'BE 503'처럼 오인됨(실체는 미인증/CORS). 카드 0렌더라 결함이 데이터/백엔드 문제로 잘못 보임.
- 감지: `curl -s -D - -o /dev/null -X OPTIONS -H "Origin: http://localhost:3100" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: authorization" http://localhost:18765/api/v2/market-pulse/overview` → `Access-Control-Allow-Origin` 헤더 **부재**면 차단 확정(`:3000`으로 바꾸면 ACAO + `Access-Control-Allow-Credentials: true` 동반). BE access 로그(`~/Library/Logs/stockvis/web-error.log`)가 503이 아니라 401만 찍으면 'BE 503'은 착시.
- 해결: **클론은 `PORT=3000`으로 띄운다** — 메인 `:3000` dev가 미가동이면 그 포트 재사용이 정석(메인·BE·settings 전부 무접촉, 검증 대상 코드 무변경). `cd <clone>/frontend && PORT=3000 npm run dev` → `:3000`에서 로그인 → CORS 통과(overview 200). 대안: `.env`에 `DJANGO_CORS_ALLOW_ALL=True`(개발 전체허용) — **되돌림 필요·비권장**(BE 재시작 + 운영 전체허용 리스크). settings에 `:3100` 영구 추가도 가능하나 메인 코드 변경이라 검증 세션엔 부적절.
- 교훈: 카드 0렌더 + '503'을 보면 BE/데이터부터 의심하기 쉬우나, **로그인 세션의 인증요청이 전건 실패하면 CORS origin 화이트리스트를 먼저 의심**한다. preflight 200 ≠ 허용(ACAO 헤더 유무가 진실). 검증환경 포트는 항상 BE가 허용한 origin과 일치시킨다.
- 📎 참조: `DECISIONS.md` "[2026-06-25] MP1.5-FIX 화면게이트 = 조건부 통과(D-P15-SCREENGATE)", `config/settings.py:318` `CORS_ALLOWED_ORIGINS`, `frontend/app/market-pulse-v2/details/CardDetailContainer.tsx:48`(cache 가드).

## 세션 중 origin/main 빈번 전진 → push 직전 재확인 + 원장은 merge=union rebase 복구 (#40) `[git]` `[harness]`

- 증상: 공유 main에서 한 트랙이 작업·검증하는 동안 **다른 트랙/자동화가 origin/main을 1~2 commit씩 반복 전진**시킴(cs reader→leadership→board 4세션 연속 관측: 매 push 전 0/0이었다가 push 시점 non-ff). 머지/push 직전 갑자기 non-ff 거부 또는 분기 발생.
- 원인: origin/main은 외부 트랙이 비동기로 갱신하는 공유 ref. 세션 시작 STEP 0의 "0/0 동기"는 **그 순간 스냅샷**일 뿐, push까지 유지 보장 없음.
- 감지: `git push` 직전 `git fetch` → `git merge-base --is-ancestor origin/main main` 미충족이면 그 사이 전진. (#33 fetch-baseline의 push 단계 변형.)
- 해결: ① push 직전 항상 `git fetch` + ff 가능여부 재확인(STEP 0의 1회 fetch로 끝내지 말 것). ② non-ff면 `git rebase origin/main`으로 흡수 후 push. ③ **원장 4파일(`PROGRESS.md`·`DECISIONS.md`·`TASKQUEUE.md`·`sub_claude_md/common-bugs.md`)은 `.gitattributes`에 `merge=union`** → append 충돌이 자동 해소되므로 rebase가 거의 항상 무충돌(실측: MP-VIX-STALE `20f0e6d` 등 disjoint 트랙 흡수 충돌 0). 코드 파일이 겹치면 일반 충돌 → 수동.
- 교훈: 공유 main에서 "동기됨"은 영속 상태가 아니라 만료되는 스냅샷. fetch는 분기 전(#33)뿐 아니라 **push 직전에도** 재실행. 원장은 union-merge라 append-only 규율만 지키면 동시 갱신이 안전하게 합쳐진다.
- 📎 참조: #33(fetch 없는 baseline), #34(공유 디렉터리 혼입), `.gitattributes`(merge=union 4파일), `feedback_commit_pathspec_shared_main`(메모리).

## 모듈 상수 변경 후 celery 워커 재기동 필수 — push만으론 조용한 갭 (#41) `[infra]` `[celery]`

- 증상: 코드(예 `FRED_RECURRING_SERIES` 7→11)를 push·머지했는데도 자동 task가 여전히 옛 동작(7종만 sync) → 일부 지표 stale 지속. 에러 없이 조용히 누락(silent coverage gap).
- 원인: celery 워커는 **시작 시점에 모듈을 import**해 상수를 메모리에 적재. 코드 파일이 바뀌어도 **실행 중 워커 프로세스는 옛 상수를 그대로 들고 있음**. push/머지는 디스크 코드만 갱신, 워커 메모리는 미반영. (MP-VIX-STALE 실측: 로컬 main 11종인데 워커 PID 7일 전 시작 = 메모리 7종.)
- 감지: 코드 종수 vs 실제 task 결과 종수 대조 — `.delay()`(워커 실행)로 트리거 후 결과 확인. ※`.apply()`는 현재 셸에서 실행되어 **항상 새 코드**라 워커 검증에 무의미 — 반드시 `.delay()`.
- 해결: 코드 push 후 **워커 재기동까지가 1셋트**. `launchctl kickstart -k gui/$(id -u)/com.stockvis.celery-worker`(default 큐 = sync 실행 주체). 재기동 후 `.delay()` 1회로 새 상수 적재 입증(uptime 리셋 + 결과 종수 확인). beat는 스케줄 발행만이라 보통 worker만으로 충분(task 인자는 worker가 모듈에서 읽음).
- 교훈: 모듈 레벨 상수/리스트를 자동 task가 읽으면, 그 변경의 운영 반영은 "merge"가 아니라 "워커 재기동"에서 완성된다. [[lesson_celery_task_registration]]의 신규 task 등록과 같은 뿌리(워커 메모리 ≠ 디스크 코드).
- 📎 참조: `DECISIONS.md` "[2026-06-29] MP-VIX-BACKFILL"·"D-MP-VIX-STALE", 메모리 `lesson_celery_task_registration`.

## 공유 main 작업트리 직접 편집 금지 — 워커 코드베이스 + 타 트랙 pull 차단 (#42) `[git]` `[harness]` `[infra]`

- 증상: ⒜ 워커가 옛 코드로 돎(#41과 연동) ⒝ 다른 트랙의 `git pull`/정합이 *"local changes would be overwritten"* 으로 막힘 ⒞ 로컬 main이 origin과 divergence.
- 원인: `~/Desktop/stock_vis`(공유 main 작업트리)는 **celery 워커가 직접 import하는 코드베이스**(별도 deploy/clone 없음, 우회 불가). 여기서 직접 편집하면 ① 미커밋 변경이 타 트랙 pull을 차단 ② 커밋해도 origin과 분기 ③ 워커는 그 디렉토리 코드를 봄. (실측: cs-board go-live 문서를 메인 작업트리에 직접 작성→미커밋→`eee3b19`로 divergence 유발.)
- 감지: `git -C ~/Desktop/stock_vis status --porcelain`에 예상 밖 tracked 미커밋(M). 세션 시작 STEP 0에서 점검.
- 해결: **모든 작업은 worktree에서 격리**(`git worktree add <path> -b <branch> origin/main`). 공유 main 작업트리는 워커 가동·pull 정합 전용으로 두고 직접 Edit/Write 금지. 미커밋이 이미 있으면 비파괴 패치 보존(handoff) 후 원작자 정합 대기(함부로 stash/checkout 금지).
- 교훈: 공유 main 작업트리는 "편집하는 곳"이 아니라 "워커가 읽고 트랙들이 정합하는 곳". 격리 worktree가 기본, 메인 트리 직접 편집은 운영·정합 둘 다 깨뜨린다.
- 📎 참조: `DECISIONS.md` "D-MP-VIX-STALE 부수 사건", #34(worktree 격리), #41(워커 재기동), `feedback_commit_pathspec_shared_main`(메모리).

---

## 결정 정합 — 로그/모델 스키마가 write 시점·표면 주장과 모순 없는지 자기점검 (#43) `[decision]` `[harness]`

- 증상: 결정 등재 후 후속 세션이 "이 스키마 필드를 언제·어디서 채우나?"에서 막힘. 모델/로그 결정의 **필드**와 **write 시점·표면 주장**이 은근히 모순.
- 사례: `D-P1-RECPROD`가 한 스키마에 `user_id`(누가 봤나) + "bake 시점 write / 새 write 표면 0"(사용자 미상 = EOD bake는 전 사용자 공용 1회)을 합쳐 **정면 모순**. STEP0가 이미 "생성-시점 로깅은 per-user 모름 부적합"이라 경고했으나 RECPROD가 재현.
- 해결: **발행 로그(issuance, user 무관, grain=signal_date) vs 임프레션 로그(per-user, 노출 시점) 분리**. user_id는 nullable 예약 컬럼으로 구조만 보존(방향 B), day-1 미충족 명시. "제시 시각"이 발행 시각인지 본 시각인지 **용어 확정**.
- 예방(DoD 규율): 로그/모델 결정 등재 시 각 필드에 대해 **"언제·어느 표면에서 write 되나 + write 시점에 그 값이 알려져 있나"** 자기점검 1패스. union-중복 자기점검과 같은 계열의 결정-등재 DoD.
- 📎 참조: `DECISIONS.md` D-P1-STEP0 ❓① ↔ D-P1-RECPROD [impression 단위] 정정 주석(2026-07-02).

## 메타 dedup 셀프체크 — 활성작업/큐 섹션 전체 스캔 (union-merge 중복 방지) (#44) `[harness]` `[git]`

- 증상: PROGRESS "현재 활성 작업"·TASKQUEUE 큐에 **같은 항목이 2건** 생김. 하나는 다른 항목 내용이 뒤에 뭉쳐(union-merge 아티팩트) 있기도.
- 원인: 원장 4파일은 `merge=union`(rebase 무충돌 대가) → **여러 세션이 인접 위치에 삽입하면 양쪽 다 살아남아** 중복·뭉침 발생. 신규 헤더만 보고 커밋하면 못 잡음.
- 사례: `D-OWN·D-SCHEMA` 활성작업 항목이 2건(하나에 `MP2-SURFACE` 내용 뭉침)으로 union-merge 잔존 → META-TOUCH(2026-07-02)에서 D-OWN·D-SCHEMA 1건 + MP2-SURFACE 독립 1건으로 dedup(내용 유실 0).
- 예방(DoD 규율): PROGRESS/TASKQUEUE 편집 시 **신규 헤더뿐 아니라 해당 활성작업/큐 섹션 전체를 스캔**해 union-merge 중복이 없는지 확인(정의 각 1건). 뭉친 항목은 제거 아닌 **분리 독립화**(내용 유실 0). union-중복 자기점검(#43 계열)과 동일 DoD.
- 📎 durable 규율은 **repo 하네스에 단일 등재**(코어 지시문 복제 금지 규약 — 복제는 drift). 관련 [[lesson_origin_main_advance_union_rebase]] · #40(merge=union rebase).

---

## 아카이브 (종결·일회성 — 이력 보존)

> 트랙이 **완전히 종결**돼 더는 능동적 함정이 아닌 항목을 이력 보존용으로 이동(HARNESS-KB S4, **삭제 0**). 재사용 지식(패턴·규칙)은 능동 섹션 또는 DECISIONS에 별도 보존돼 있다. 영구 삭제는 사용자 수동 판단.

### shared 역방향 import 5건 — 전건 청소 완료 (#31, 2026-06-04 종결) `[boundary]`

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

## [프로파일링 함정] violation 단위(client 인스턴스) ≠ call 단위 (BOUNDARY-LLM 슬라이스 ④, 2026-06-26)

- 증상: STEP 0 프로파일이 외부-LLM violation을 **genai.Client 인스턴스 단위**로 세고 대표 call_symbol 1개만 기록 → `keyword_generator.py`를 "sync"로 분류. 실제로는 한 `self.client`를 `_call_llm_sync`(sync) + `_call_llm`(aio)가 공유.
- 함정: sync-only Part에서 sync call만 `complete()`로 이관해도 aio 경로가 그 client를 계속 써서 **genai.Client 제거(동결 −1) 불가**. `complete()`는 동기 전용이라 aio 경로는 같은 Part에서 못 옮김.
- 교훈: 이관 전 각 client의 **전 호출 경로를 전수 확인**할 것(대표 call_symbol 1개로 판단 금지). "sync/aio"는 call 단위가 아니라 **client 단위 속성** — aio-touched client는 통째로 aio Part 소속.
- 탐지 한 줄: `grep -c "\.aio\." <file>` — 0 아니면 그 파일의 client는 dual, sync-only Part 제외.

## [환경 known-fail] Finnhub 회귀 1건 — 이관/코드와 무관 (2026-06-27 등록)

- `tests/unit/news/test_api.py::TestNewsViewSet::test_stock_news_refresh_true`는 **FINNHUB_API_KEY 미설정**(테스트 환경) 때문에 실패한다. 환경 의존이며 이관·코드 회귀가 아니다.
- (2026-06-29 추가) `tests/news/test_news_entity_deduplication.py`의 3건(`TestNewsSystemIntegration::test_multiple_symbol_fetches_no_cross_contamination` + `TestAggregatorEntityDeduplication::test_no_duplicate_entities_on_multiple_saves`·`::test_existing_article_entity_unchanged`)도 동일 **Finnhub API 키 미설정**(`finnhub.py:38 ValueError`) — 막간 test 위생 전수 분류에서 선존 확인(`94f082c`, #19 이전). KNOWN_TEST_FAILS 등록.
- 회귀 게이트에서 **known-fail로 제외**(이관 회귀 신호를 가리지 않게). SSOT = `scripts/health_check.py:KNOWN_TEST_FAILS` + health_check "known-fail 레지스트리" 항목.
- 회귀 판정 규칙: `pytest` fail 목록에서 KNOWN_TEST_FAILS를 뺀 나머지가 0이어야 회귀 0. 새 fail이 이 목록 밖이면 진짜 회귀.

## [의도된 미구현] async Anthropic(`agenerate`)은 슬라이스 ③까지 NotImplementedError (2026-06-28)

- `packages/shared/llm/providers/anthropic.py:agenerate`는 `raise NotImplementedError`다. **버그/누락 아님 — 의도.**
- 이유: aio Part(②b로 풀린 #10·11·16·17 + #12·#16) 소비처가 **전부 Gemini**라 async Anthropic 불요(YAGNI). `acomplete(provider='anthropic')`가 조용히 sync로 폴백하면 행위 위장 → 명시 차단.
- 채우는 시점: **슬라이스 ③ Anthropic 이관**(portfolio Anthropic·rag adaptive AsyncAnthropic)에서 AsyncAnthropic로 신설. 그 전에 "빠진 구현"으로 오해해 채우지 말 것.
- circuit breaker 보존 패턴(Part ①-aio #10): 소비처가 파라미터화 CB(`get_circuit(name, failure_threshold, recovery)`)를 쓰면, acomplete의 circuit 정책(`get_circuit(name)`만)으로 통합하지 말고 **소비자 CB 래퍼 존치 + 감싸는 대상만 acomplete로 교체**. acomplete circuit은 파라미터 미전달이라 threshold/recovery 유실.

## [이관 동반작업] site 이관 = 기존 테스트 seam 갱신 동반 (서프라이즈 방지)

- site 이관(genai 직접호출 → complete()/acomplete())은 `self.client`(옛 seam)를 제거한다 → **그 site의 기존 단위테스트가 옛 seam을 mock하고 있으면 전부 깨진다.** 이관 작업의 일부로 테스트 seam을 함께 갱신해야 한다(미예상 시 회귀 게이트에서 대량 fail로 터짐).
- 갱신 방법: 옛 `svc.client`/`svc.client.aio.models.generate_content` mock → `google.genai.Client` patch(`.aio.models`(async AsyncMock) / `.models`(sync)). mock 응답에 **`usage_metadata = None` 필수**(코어 provider `_extract_raw`가 `int(getattr(usage, ...) or 0)` → MagicMock이면 TypeError). 피처플래그 site는 `svc.client=mock/None` → `svc._llm_enabled=True/False`.
- 예외: complete()/acomplete()는 genai 예외를 `_classify`로 분류 후 raise → 테스트의 예외타입 단언 조정(분류 규칙 미매칭 시 원본 그대로 전파). CB site는 1 fail < threshold면 미개방, 실 CB 통과.
- **이관 지시서마다 이 동반작업을 예상 작업으로 선반영**할 것. 실측: #13(33개 7파일)·Part ①-aio(3파일) churn 발생.

## [병렬 에이전트] 기존재 오인 → 실행 전 심볼 정의 수 grep으로 중복 방지 (MP2-DELTA, 2026-07-04)

- **증상**: 병렬/다중 에이전트가 "이미 누가 만들었겠지"라고 기존재를 오인하거나, 반대로 이미 있는 함수·타입·블록을 모른 채 재구현 → 중복 정의·충돌.
- **실측**: MP2-DELTA S1에서 FE 에이전트가 BE 기존재를 오인해 재확인(중복 0으로 방어됨). S2에서는 착수 전 `grep -c 'def compute_anomaly_delta\|interface AnomalyDelta\|anomaly_delta'`로 정의 수를 세어 0건 확인 후 신규 작성.
- **규칙**: 신규 심볼(함수·타입·컴포넌트 블록) 작성 **직전** `grep`으로 **정의 수를 센다**. 0이면 신규, 1+이면 기존 편집. wiring 지점(`_build_payload`·page.tsx prop)도 동일하게 grep으로 기존 배치 확인 후 additive.
- **왜**: 병렬 세션은 서로의 working tree를 못 본다. "본 것 같다"는 기억이 아니라 grep 카운트가 유일한 진실. 실행 전 1회 grep이 중복 커밋·충돌 정리 비용(1h+)을 막는다.

## [휴면 앱 CUT] 코드+prod 스키마는 순서 있는 원자적 제거 (D-REHOME-GRAPH, 2026-07)

- **증상**: Django 앱(모델+마이그레이션 적용됨)을 지울 때 INSTALLED_APPS에서 먼저 빼거나 코드를 먼저 `git rm`하면, Django가 앱을 잊어 **drop 마이그레이션을 자동생성하지 않음** → prod 테이블이 고아로 잔존.
- **규칙(순서 불변)**: ① 앱이 INSTALLED_APPS+코드로 **살아있을 때** `DeleteModel` 마이그레이션 생성 → **prod 적용**(테이블 DROP) → ② **그 다음** 코드+INSTALLED_APPS `git rm`. STAGE 분리(migrate → 코드 rm).
- **검증**: 코드 제거 후 `python manage.py makemigrations --dry-run` = **"No changes detected"**(잔재 모델참조 0). 삭제 대상 0 rows면 데이터 위험 0·reversible(`migrate <app> 0001`).
- **왜**: 마이그레이션은 앱이 등록돼 있어야 DROP을 실행한다. 순서가 뒤바뀌면 DB에 빈 고아 테이블 + `django_migrations` 고아행이 남는다(무해하나 위생 저하).

## [fast-main land] 순간 ff-land엔 `git push origin HEAD:main` (2026-07)

- **증상**: 인간 병렬 CC 세션이 분당 커밋하는 fast-main에서, `git checkout main && git merge --ff-only`는 (a) main이 다른 worktree에 물려 `checkout` 거부, (b) rebase가 그 브랜치의 다른 worktree 때문에 거부, (c) merge~push 사이 main 전진으로 non-ff — 반복 실패.
- **규칙**: 브랜치가 정확히 `origin/main+1`(그 브랜치 worktree에서 `git rebase origin/main` 선행)일 때, **`git push origin HEAD:main`** = 원자적 ff-push. worktree/checkout/merge 춤 불필요, main이 그새 전진하면 서버가 non-ff로 **안전 거부**(force 아님) → rebase 재시도.
- **왜**: `push <src>:main`은 서버측 ff 조건을 원자적으로 검사한다. 로컬 checkout/merge 시퀀스는 다중 worktree + 전진 창에 취약. 단 **에이전트의 main 직접 push는 auto-mode가 차단** → land는 사용자 수동 단계로 유지(에이전트는 rebase까지).
