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
- **★ 정정 (2026-07-10 tz 사고)**: 위 "dict는 런타임에 완전히 무시됨"은 **부정확 — dispatch 타이밍 한정**이다. **`DatabaseScheduler`는 beat 기동 시 `app.conf.beat_schedule` dict를 DB로 sync한다(create/update PeriodicTask+CrontabSchedule)**. 따라서:
  - **stale config 트리에서 beat를 띄우면**(예: 브랜치 표류한 편집 repo) 옛 dict가 **매 재기동마다 DB를 덮어써 수동 교정을 무효화**한다. 실사고: `collect-av-broad-news`의 crontab을 DB에서 UTC로 교정해도, beat가 옛 dict(`crontab(hour=1)`=CELERY_TIMEZONE ET 해석)를 로드·sync해 재기동마다 ET로 되돌림. → **beat는 반드시 origin/main 정렬된 런타임 트리에서 기동**(celery-beat.sh PROJECT_DIR = `~/worktrees/sv-worker-runtime`, worker와 동일 B′).
  - dict crontab의 tz = **CELERY_TIMEZONE(app tz, 여기선 America/New_York)** 로 해석된다. UTC 의도면 dict `crontab(hour=1)`은 ET가 되어 위험. **UTC 고정이 필요한 beat는 dict에 두지 말고** 전용 관리명령(`register_news_av_beat`)으로 `CrontabSchedule(timezone='UTC')` 직접 등록.
  - **비-dict DB 엔트리는 startup sync가 삭제·변경하지 않는다**. 즉 dict에서 뺀 엔트리는 DB 값(UTC)이 재기동에도 보존된다(위 전용 등록이 durable해지는 근거).
- **★ 재정정 (2026-07-11 주기 sync 실측)**: 위 07-10 정정의 함의("beat **기동 시** sync")는 **불충분**하다. `DatabaseScheduler`는 `app.conf.beat_schedule` dict를 **startup 뿐 아니라 주기 sync로 상시** DB에 반영(create/update PeriodicTask+CrontabSchedule)한다. 즉 "dict 런타임 무시"는 **dispatch 타이밍 한정**이고, dict→DB 반영은 상시다. 따라서 **stale config 트리에서 beat가 실행 중이면 DB 수동 교정(ORM UPDATE)은 재기동 없이도 수분 내 무효화**된다 — 07-10 실측: 재기동 없이 crontab을 UTC로 고쳐도 다음 sync에서 옛 dict(`crontab(hour=1)`=ET)로 재변질. **90초 내구 실험**(교정 후 90초 관찰 → ET 복귀 확인)으로 원인을 격리한 뒤, 해당 태스크를 dict에서 제외(`config/celery.py` L261 주석)해야 고정됐다. 비-dict DB 엔트리는 sync가 삭제·변경하지 않으므로, **UTC 고정이 필요한 태스크는 dict에서 빼고 전용 관리명령(`register_news_av_beat`)으로만 등록**하는 것이 유일한 durable 경로. (07-11 재확인: crontab id=101 tz=UTC durable, 재기동 없이 01:00 UTC 정시 발화.)
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

## ORM에서 읽은 aware datetime에 naive `.date()` 직접 호출 금지 — tz 경계 하루 밀림 (#51, 2026-07-13 MON-CLOSE)

- 증상: **진단/관측 스크립트**에서 ORM으로 읽은 aware datetime에 `.date()`를 직접 호출하면 하루 밀린 값이 나온다. MON-OPS-FIRSTFIRE/ALERTFIRE 진단에서 `IndicatorReading.asof`(저장 시 `make_aware(combine(d, time.min), 'Asia/Seoul')` = 자정 KST)를 `values_list("asof").first().date()`로 읽어 "AAPL reading max asof=07-08/07-09"로 **오관측** → "T-1 구조적 지연"이라는 **존재하지 않는 결함**을 좇음(실제는 시스템 정상, 진단 쿼리 버그).
- 원인: 자정 KST = **전일 15:00 UTC**. Django가 aware datetime을 UTC로 반환할 때 `dt.date()`는 UTC date(=전일)를 준다. `.date()`는 tz 변환을 하지 않으므로 저장 시점의 로컬 자정이 조회 시 UTC 전일로 밀린다. #29(`timezone.now().date()`)의 사촌 — 본건은 **ORM에서 읽은 임의 aware datetime**에 발생.
- 해결: 날짜 추출/비교는 `.date()` 직접 호출 금지. (a) ORM `__date` lookup `filter(asof__date=d)`(connection.timezone 기준 tz-aware), (b) `QuerySet.dates('asof','day')`(현재 tz 기준 정확한 date 목록), (c) 굳이 파이썬에서 좁힐 땐 `timezone.localtime(dt).date()`.
- 교훈: **진단 스크립트도 코드와 동일한 tz 규칙을 적용**하라. 관측 도구의 tz 버그가 시스템 이상으로 오판되면 없는 결함을 좇고 잘못된 배포 판단(발화 시각 변경 등)까지 갈 수 있다. aware datetime을 date로 좁힐 땐 항상 tz를 명시.

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
- **원인 메커니즘(2026-07-09 강화, MGMT-BATCH-7)**: 활성 블록이 여러 세션에 걸쳐 **재커밋**될 때 `merge=union` 드라이버가 옛 스냅샷 + 새 스냅샷을 **양쪽 보존** → 같은 블록의 진화 스냅샷이 2·3·…개로 **누적**(비-동일본, 길이 상이). 실증: Monitor 허브 블록 ×5(2939→5482자)·MP2-TREND ×2. 신규 헤더만 스캔하면 "제목 1건"으로 보여 못 잡고, 내용이 갈라져 `uniq`도 안 걸림.
- **규칙 승격**: ⑴ 활성 블록 **재커밋 전 자기-블록 dedup 셀프체크**(같은 트랙의 이전 스냅샷을 최신 superset로 흡수, 내용 유실 0). ⑵ **번호·슬롯 예약 금지 = 등재 시점 실측 +1**(common-bugs 신규 번호도 하드코딩 금지, 본선 max 실측 후 +1 — theme-heat #47 충돌 선례). ⑶ per-copy가 **비-동일본이면 blind collapse 금지** — superset 검증 후 병합(별도 dedup 태스크로 분리).

## 공유 트리 브랜치 표류 → 워커 silent 구코드 bake (#45) `[infra]` `[celery]` `[git]`

- 증상: land된 신규 코드(예: baker recommendations)가 자동 bake 산출물에 **안 나옴**. 런타임 에러 0, 파이프라인은 정상 완주.
- 원인: celery worker가 import하는 트리 = **공유 편집 트리**(`~/Desktop/stock_vis`, `celery-worker.sh` PROJECT_DIR 하드코딩). 이 트리의 체크아웃 브랜치는 **세션 활동으로 가변** → land 전 브랜치(예: `sess-cs-pair-relevance`)에 머물면 워커가 **구 코드로 bake**. origin/main에 land돼도 워커는 못 봄.
- 함정: OBSERVE(실산출물 검사) 게이트가 **아니면** 통과함 — 유닛 테스트 green + push 성공이 "반영됐다"는 착시. #41(모듈 변경 후 재기동)·#42(공유 트리 편집 금지)의 확장.
- 해결(임시): 공유 트리를 `git checkout --detach origin/main` + 워커 재기동. **단 detached는 유지 안 됨**(다른 세션이 재체크아웃 → 재표류) = 트레드밀. **항구 해결 = worker 전용 worktree**(TASKQUEUE `P1-B-WORKER-WORKTREE`).
- 예방: land마다 "워커 트리 == origin/main?" 확인 + 재기동. 자동 beat 전 diff 점검(`P1-BEAT-PRECHECK`).
- **★web 판(2026-07-06 확인·해소)**: 동일 결합이 **dev server(next dev :3000)에도 존재** — next dev가 공유 트리 frontend를 서빙하므로 land된 FE(예: 캐러셀 `24b0e47`)가 공유 트리 브랜치에 없으면 **화면 미도달**(유닛 green·push 성공이어도). → **W′(D-W-WEB-AMEND-1, web 전용 트리 `sv-web-runtime`)로 해소** `75cb4d3`. ※ 애초 `com.stockvis.web`(daphne)로 오지목했으나 실서빙은 next dev(:3000) — 대상 정정. worker(B′)+web(W′) 양쪽 분리로 완결.
- **★세 번째 인스턴스(daphne, 2026-07-06 최종 해소 `803e9a9`)**: `com.stockvis.web` = **daphne 백엔드(:18765)** 도 공유 트리에서 실행 → API 응답이 구코드일 수 있었음. → DAPHNE-BUILD로 **해소**(daphne 전용 트리 `sv-api-runtime` + `worker_sync.sh` api 섹션 + plist 전환). 검증: 재기동 전후 baseline 일치·CWD api트리·WS 101. **런타임 3종(celery worker B′·next dev W′·daphne) 전부 공유 편집 트리에서 분리 = #45 전면 종결.** 갱신 = `worker_sync.sh` 단일 출처(단, 반드시 런타임 트리 사본으로 실행 — [[#47]] 참조).

## worker_sync.sh는 런타임 트리 사본으로 실행 (공유 트리 사본 = stale) (#47) `[infra]` `[git]` `[ops]`

- 증상: `bash scripts/worker_sync.sh`를 실행했는데 **worker·web만 동기화되고 api 트리는 건너뜀**(부분 동기화). 에러 0, 조용히 일부만 정렬.
- 원인: **공유 편집 트리**(`~/Desktop/stock_vis`)의 `scripts/worker_sync.sh`가 세션 브랜치(예: `sess-cs-pair-relevance`)에 머물러 **api 섹션이 없는 구버전**. 확장판(api 섹션 = D-DAPHNE-RUNTIME)은 origin/main(`803e9a9`+)에만 존재 → 공유 트리 사본은 stale. #45의 재귀(#45가 "코드가 stale"이면, #47은 "동기화 스크립트 자체가 stale").
- 함정: 스크립트 파일이 존재하고 정상 종료(exit 0)라 "다 돌았다"는 착시 — 실제로는 최신 트리 하나(api)를 누락.
- 해결: **반드시 런타임 트리 사본으로 실행** — `bash /Users/byeongjinjeong/worktrees/sv-worker-runtime/scripts/worker_sync.sh`(런타임 트리는 detached origin/main이라 항상 확장판 보유). 실행 전 `grep -c API_TREE <사본>`로 api 섹션 유무 확인(0이면 stale, 사용 금지).
- 예방(고정 진입점 미결): 항상 런타임 사본을 실행하는 래퍼/별칭 = TASKQUEUE `SYNC-ENTRYPOINT`(미결). 그 전까지 **수동 주의**(사본 경로 명시 지정).
- **첫 준수 사례(2026-07-07)**: MGMT 세션이 공유 트리 사본(api 섹션 0)을 포착·거부하고 런타임 트리 사본으로 실행 → worker·web·api 3종 `9fe326f` 정상 동기화 + daphne 재기동. 자동화 부재 시 수동 규율로 우회 가능함을 실증.
- **재귀 2건째(health_check, 2026-07-08)**: `python scripts/health_check.py`를 공유 트리에서 실행 → **구버전 10건**(HC-BUILD 신항목 "발행 로그 신선도" 없음). 신항목은 origin/main(`ad3ae77`)에만 → 공유 트리 사본 stale. 런타임 트리 사본(`sv-worker-runtime/scripts/health_check.py`, +.env)에서 실행하니 **11건**(신항목 OK). → **일반화**: "repo 스크립트를 어느 트리 사본으로 실행하나"는 worker_sync 한정이 아니라 **repo 스크립트 소비 전반**의 함정(실행자가 최신 코드를 본다는 보장 없음).
- **★해소(2026-07-09, D-SYNC-ENTRYPOINT land)**: 래퍼 `~/bin/sv`(exec 전 런타임 트리 최신화) + 스크립트 자기가드(`worker_sync.sh` stale abort exit 2 / `health_check.py` "실행 트리 정합" WARN)로 **구조적 해소**. land `942a991`·`f084cd6`. 실증: stale 사본 abort·WARN, `sv sync` 3종 일치, `sv health` 12/12. 이후 repo 스크립트는 `sv`로 실행.

## 심링크 node_modules × vitest4/rolldown → full-suite 거짓 red (#48) `[frontend]` `[test]` `[env]`

- 증상: worktree에서 `vitest run`(전체) 시 **140 테스트 거짓 실패**(21파일). 코드 회귀 아님 — 같은 코드가 실설치 환경에선 전건 green.
- 원인: worktree의 `node_modules`가 **공유 트리 심링크**일 때, vitest4의 번들러 **rolldown이 native binding(`.node`)을 심링크 경로에서 resolve 실패**. 특정 파일이 그 native 경로를 타면 로드 자체 실패(Startup Error). W′의 turbopack 심링크 비호환과 동형(도구별 심링크 엄격도 상이).
- 증상 2형(공통 뿌리 = 심링크 경로 native resolve 실패): ⑴ **React 이중 인스턴스형**(심링크로 react가 두 경로 resolve) ⑵ **@rolldown 바인딩 부재형**(`Cannot find native binding @rolldown/binding-darwin-arm64`).
- 재현 조건: **공유 트리 심링크 node_modules + full-suite**. scoped 테스트(자기 구획, 예 eod 7/7)는 심링크에서도 **green(오탐 아님)**.
- 판정 근거(VERIFY-SUITE-BASELINE, 2026-07-09): 격리 **npm ci(비-심링크) + node v22.19.0**에서 **519/519 green** · react가 worktree 실경로 단일 resolve · `.node` 실존 로드. 심링크에서 12/6 실패하던 파일이 실설치 전건 green.
- 선례: eod land 시 with/without 커밋 대조로 무관 입증 → **push HALT는 정당한 보수적 정지**(거짓 red를 실회귀로 오인 안 함). 
- 대응: **D-TEST-ENV**(full-suite 게이트 = 격리 npm ci + node 고정에서만 유효 / scoped는 심링크 허용). `sv health` "full-suite 전 npm ci 확인" 안내(`TEST-ENV-GUIDE`).
- **★서사 보정(2026-07-09, D-THEMEHEAT-AUDIT ⑶)**: 이 거짓 red의 오염원은 "특정 세션의 잘못"이 아니라 **심링크 관행 × primary 트리의 stale node_modules(5/25 설치) × 복수 세션 공유**의 구조적 합작. 책임 귀속(누가 깨뜨렸나)이 아니라 환경 구조를 고쳐야 재발이 멎음 → D-TEST-ENV 이원 정책이 그 처방.

## migration 미적용 → write 실패에도 파이프라인 무중단 완주 (#46) `[infra]` `[db]`

- 증상: 모델은 land됐는데 해당 테이블 write가 **조용히 실패**(0행), 상위 파이프라인은 성공으로 완주.
- 원인: 운영 DB에 migration **미적용**(테이블 부재, `UndefinedTable`). land은 코드만 옮기지 **운영 `migrate`를 자동 실행하지 않음**. 예: `stocks_issuance_log` 부재 → IssuanceLog write 예외. 단 baker는 `atomic_swap`(파일 반영)이 DB write보다 **앞서** 있어 JSON 산출물은 정상 → 결함이 파일만 보면 안 보임.
- 함정: **스키마 부재 = 조용한 로깅 손실**. JSON만 검사하면 통과, DB까지 봐야 잡힘(OBSERVE는 DB 확인 필수).
- 해결: `sqlmigrate`로 순수 add 육안 검증 → `migrate`. 재발 방지 = **land에 migration 포함 시 운영 migrate를 배포 단계로 명시**(runbook `P1-RUNBOOK-MIGRATE`) + **health_check "bake 완주 시 IssuanceLog 행 증가"**(`P1-HC-ISSUANCE`, #45와 짝).

## 1브랜치를 복수 세션이 공유하면 tip이 세션 모르게 전진 (#49) `[git]` `[harness]`

- 증상: 세션 시작 스냅샷의 브랜치 tip과 현재 tip이 다름 — 내가 커밋한 적 없는데 tip이 3커밋 전진(theme-heat TH-6 `cc7ed9c`·`cf6062c`·`86ddbc2` 실증).
- 원인: 동일 브랜치(`monorepo/sess-cs-theme-heat`)를 **복수 세션이 공유**(primary 트리 + 타 세션). 한 세션이 커밋하면 다른 세션은 모른 채 tip이 움직임 → 이력 오귀속·중복 편집·표류.
- 함정: `git status`가 clean이라 "내 작업만 있다"는 착시. 커밋 주체가 불분명해 land 시 이력 추적·AMEND 대상 판정이 흐려짐.
- 규칙: **1브랜치-1세션**, `worktree-per-세션`과 짝(각 세션 전용 worktree+브랜치). 공유 primary 트리에 세션 브랜치를 얹지 않는다 — 작업은 전용 worktree로 이주([[#45]] 런타임 격리의 편집 세션판).
- 참조: D-THEMEHEAT-AUDIT ⑷(RELOCATE = 브랜치를 `~/worktrees/sv-theme-heat`로 이주, primary는 detached origin/main).

## 트랙 세션이 메타 4종을 직접 편집·커밋 = mgmt 분리 규약 위반 (#50) `[harness]` `[git]`

- 증상: 트랙(구현) 세션 브랜치 이력이 DECISIONS·PROGRESS·TASKQUEUE·common-bugs를 **광범위 직접 편집·커밋**(theme-heat `origin/main..86ddbc2` = DECISIONS 8·PROGRESS 11·TASKQUEUE 6·common-bugs 1, "결정7·8·9" mgmt 밖 등재 포함).
- 원인: 메타 4종(장부)은 **mgmt 세션 전담**(union 드라이버·번호 관리·dedup 규율의 단일 통제점)인데 트랙 세션이 우회해 직접 기입 → 번호 충돌(#47)·union 중복 누적(#44)·미검토 결정 등재.
- 함정: 트랙 세션은 "내 작업 기록"으로 장부를 만지지만 mgmt 통제 밖이라 dedup·번호 실측·정합 검토가 누락 → land 시 정산 부채로 폭발.
- 규칙: 트랙 세션은 장부 **직접 편집 금지** — 교훈·결정은 mgmt에 위임(또는 지연 커밋 블록). **mgmt 분리 규약을 트랙 Project 지시문에 전파**해야 구조적으로 멎음.
- 참조: D-THEMEHEAT-AUDIT ⑵, THEMEHEAT-LAND-GATE(land 전 mgmt 선행 정산).

### Turbopack이 심링크 node_modules 거부 — worktree dev/캡처는 실제 npm ci 필요 (Slice 20b, 2026-07-16) `[frontend][dev-infra]`

- 증상: worktree frontend에서 `node_modules`를 main repo로 심링크한 뒤 `next dev`(Turbopack) 기동 시 `Symlink [project]/node_modules is invalid, it points out of the filesystem root` → 컴파일 실패.
- 원인: Turbopack은 파일시스템 루트 밖을 가리키는 심링크 node_modules를 거부(webpack과 다름). **scoped `vitest`는 심링크로 OK**(memory `project_color_ops_testenv_arc`)지만 dev 서버는 불가.
- 해결: worktree에서 라이브 dev/캡처가 필요하면 심링크 제거 후 **실제 `npm ci`**(node v22.19.0). 캡처 종료 후 worktree 제거 시 자연 정리(gitignored).
- 캡처 격리 레시피(Slice 20b): Django `runserver 127.0.0.1:8010`(`DJANGO_CORS_ALLOW_ALL=True`+dev DB) + `next dev -p 3010`(`NEXT_PUBLIC_API_URL=http://127.0.0.1:8010/api/v1`) + JWT `RefreshToken.for_user` 발급→`localStorage.access_token/refresh_token` 주입(로그인 UI 우회). 공유 launchd 런타임(:18765) 무접촉.

### React Query mutation 거부가 vitest서 unhandled로 표면화 — 컴포넌트 에러 테스트는 훅 mock (Slice 20b, 2026-07-16) `[frontend][testing]`

- 증상: `service.updateKnobs`를 `mockRejectedValue`로 mock하고 컴포넌트 저장 버튼 클릭 → 컴포넌트가 `mutateAsync`를 try/catch로 잡아 로컬 에러 state를 세팅해도, vitest가 `Error: xxx`를 **unhandled rejection으로 잡아 테스트 실패**. `mutations:{retry:false}`·`mutate`+onError·mutateAsync+catch 전부 누수.
- 원인: 서비스를 mock하면 React Query 실 mutation 머신(Retryer/MutationObserver)이 거부 promise를 생성→vitest 프로세스 리스너가 unhandled로 포착. CloseModal이 통과하는 건 표면적 유사일 뿐, 격리 조건이 다름.
- 해결: 컴포넌트의 **에러 상태 테스트는 훅(`useUpdateKnobs`)을 mock**(서비스 mock 아님) — `{ mutateAsync: vi.fn().mockRejectedValue(...), isPending, isError }` 반환. RQ 실 머신을 우회해 거부가 컴포넌트 try/catch 안에서만 처리됨. 컴포넌트 자체는 mutateAsync+try/catch+로컬 에러 state(CloseModal 관례) 유지. range input은 jsdom서 키보드 조정 불가 → `fireEvent.change(slider,{target:{value}})`.

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

## [AV NEWS_SENTIMENT 함정] topics 다중=교집합 0 + 25/day 리셋은 rolling 24h (2026-07-03 실증)

Alpha Vantage broad 뉴스 재설계(co-mention 소스, `services/news/providers/alphavantage.py`) 진단에서 확정한 2개 함정:

- **topics 다중 지정 = 결과 급감(사실상 AND/교집합).** 실측 동일 창(06-13, 1일, EARLIEST, limit=1000): topics 1개(technology)→1000기사 / 4개→~80 / **11개(DEFAULT_TOPICS)→0**. broad 백필이 `fetched=0`이던 뿌리 = topics 11개. **해결: broad 수집은 topics 미지정**(전체) 또는 topic별 분리 호출. topics 미지정 시 하루 1창 1000기사·2+종목 141(14%)·distinct 824종목(4월 co-mention 17/일 압도).
- **25 req/day 리셋은 UTC 자정이 아니라 rolling 24h.** 실측: 07-02 예산 소진 후 07-03 00:27·05:06 UTC 모두 한도 지속(UTC 자정·ET 자정 04:00 둘 다 기각), **10:01 UTC 성공**(어제 마지막 호출 ~09:40 UTC +24h). → 백필/캘리브레이션 스케줄은 rolling 24h 기준으로 예산 배분. 한도 응답은 HTTP 200 + JSON `Information` 필드(에러 아님) — `feed` 부재로 감지.

## [저장 함정] 대량 루프 + 단일 transaction = 포이즌 1건이 배치 전멸 (2026-07-04 실증)

- `aggregator._save_articles`가 기사 리스트를 **한 transaction**에서 루프 저장 → 한 기사의 DB 에러(필드 길이 초과 등)가 transaction을 오염시켜 **나머지가 연쇄 실패**(`current transaction is aborted` = "atomic block" 에러). AV broad 백필에서 url `varchar(2000)` 초과 **1건**이 그 반창의 **596건을 전멸**시킴(일별 적재 급락으로 표면화).
- **방어(`72c1825`)**: ⑴ `_save_articles` 루프를 기사별 `transaction.atomic()`(savepoint)로 격리 — 1건 실패가 rollback되어도 나머지 저장 진행(성공 경로는 savepoint 즉시 release라 동작 무변경). ⑵ broad 계층 길이 sanitize — `url>2000`은 **skip**(unique 키라 truncation 금지, 충돌 위험), `image_url>2000`은 **null/빈값**(비필수).
- **재발 감지 신호** = 일별/창별 적재 수 급락(정상 700~900 대비 100대). skip 카운터 급증(창당 수십+)도 새 유형 포이즌 정황.
- 이 패턴은 AV 전용 아님 — **대량 벌크 저장 루프 일반의 함정**. 다른 수집 경로도 savepoint 격리 권장.

## [AV rolling 예산 함정] 확인 프로브도 실호출 — 로그 회계로 대체 (2026-07-04)

- rolling 24h 체제에서 **예산 확인용 프로브 1건도 실호출**이라 내일 그 시각까지 예산 1을 잠근다. 게다가 `feed` 반환은 "잔여 ≥1"만 의미하므로 **배치 가능 여부(≥3+α) 판별력이 없다**(잔여 1이어도 feed는 옴).
- **예산 확인은 직전 24h 호출 로그 회계로 한다** — 각 호출 시각 +24h = 해제 시각. 로그가 유실돼 회계 불가일 때만 프로브 1건 예외(보고에 명시).
## [관찰 도구 함정] 고정 tail-window 로그 스캔 = 폭주 로그에서 오탐 (verify_pair, 2026-07-03)

- **증상**: `verify_pair_aggregation.py`가 정상 발화한 자율 틱을 ALERT(오탐)로 판정. 실제 파이프라인은 정상(beat 발송 → worker succeeded → DB 적립)이었으나, 틱 +2h 예약 실행 시 성공 로그를 못 찾음.
- **원인**: `check_last_tick_succeeded`가 worker 로그 **고정 `[-5000:]`줄**만 읽음. worker-error.log가 시간당 ~2.7k줄(heartbeat + task received)로 폭주 → 틱+2h 지점엔 성공 로그가 창 밖(파일 끝에서 5,396>5,000줄)으로 스크롤아웃. tz 비교 로직은 정상 — 성공 라인 자체가 읽은 바이트 범위 밖.
- **해결**: 고정 tail창 → `grep`으로 매칭 라인만 **전수 스캔** + 직전 틱 **boundary 이후만** 집계. 로그 폭주 무관하게 증거 누락 없음. 전수 스캔 부작용(이미 해소된 과거 unregistered 부활)은 boundary 이전 제외로 봉인. unregistered FAIL은 `succeeded==0`일 때만(회복된 틱 면제). 커밋 `261b5e3`.
- **교훈**: 로그 기반 관찰 도구는 "최근 N줄"이 아니라 "관심 이벤트 시각 경계 이후"로 스캔 범위를 정의하라. 고빈도 로그 소스에서 N줄 tail은 시간창이 아니라 이벤트-밀도창이라 시각 기준 판정이 오염된다.
## [병렬 에이전트] 기존재 오인 → 실행 전 심볼 정의 수 grep으로 중복 방지 (MP2-DELTA, 2026-07-04)

- **증상**: 병렬/다중 에이전트가 "이미 누가 만들었겠지"라고 기존재를 오인하거나, 반대로 이미 있는 함수·타입·블록을 모른 채 재구현 → 중복 정의·충돌.
- **실측**: MP2-DELTA S1에서 FE 에이전트가 BE 기존재를 오인해 재확인(중복 0으로 방어됨). S2에서는 착수 전 `grep -c 'def compute_anomaly_delta\|interface AnomalyDelta\|anomaly_delta'`로 정의 수를 세어 0건 확인 후 신규 작성.
- **규칙**: 신규 심볼(함수·타입·컴포넌트 블록) 작성 **직전** `grep`으로 **정의 수를 센다**. 0이면 신규, 1+이면 기존 편집. wiring 지점(`_build_payload`·page.tsx prop)도 동일하게 grep으로 기존 배치 확인 후 additive.
- **왜**: 병렬 세션은 서로의 working tree를 못 본다. "본 것 같다"는 기억이 아니라 grep 카운트가 유일한 진실. 실행 전 1회 grep이 중복 커밋·충돌 정리 비용(1h+)을 막는다.

## [STEP 0 실측] 골격 전수 grep은 `services/` 포함 필수 — apps/·packages/만 보면 놓친다 (MP2-ALERTS, 2026-07-06)

- **증상**: MP2-ALERTS STEP 0에서 기존 알림 골격을 `packages`·`apps`만 grep → **0건**으로 오판할 뻔. 재실측(`services/` 포함)에서 `services/serverless/ScreenerAlert`+`AlertHistory`(사용자 알림 프레임워크 상당 부분)·`services/news/AlertLog`(ops)·`check_pipeline_alerts`가 무더기로 나옴.
- **원인**: monorepo 이동(PR8a)으로 news·serverless·rag_analysis·validation·sec_pipeline이 `services/*`로 재배치됨. 앱 레이어가 `apps/`·`packages/`·**`services/`** 3곳에 분산 → 한 곳만 grep하면 절반을 놓친다.
- **규칙**: "기존재 전수" 성격의 STEP 0 grep은 **`apps packages services` 3곳 전부**를 대상에 넣는다(+ `config/`도 celery 등록·settings 확인). "없을 것" 가정 금지 + grep 범위 자체를 의심하라.
- **왜**: STEP 0의 존재 이유가 "발명 금지"인데, grep 범위 누락은 발명 금지를 무력화한다(greenfield 오판 → 중복 프레임워크 구축 위험).
## [휴면 앱 CUT] 코드+prod 스키마는 순서 있는 원자적 제거 (D-REHOME-GRAPH, 2026-07)

- **증상**: Django 앱(모델+마이그레이션 적용됨)을 지울 때 INSTALLED_APPS에서 먼저 빼거나 코드를 먼저 `git rm`하면, Django가 앱을 잊어 **drop 마이그레이션을 자동생성하지 않음** → prod 테이블이 고아로 잔존.
- **규칙(순서 불변)**: ① 앱이 INSTALLED_APPS+코드로 **살아있을 때** `DeleteModel` 마이그레이션 생성 → **prod 적용**(테이블 DROP) → ② **그 다음** 코드+INSTALLED_APPS `git rm`. STAGE 분리(migrate → 코드 rm).
- **검증**: 코드 제거 후 `python manage.py makemigrations --dry-run` = **"No changes detected"**(잔재 모델참조 0). 삭제 대상 0 rows면 데이터 위험 0·reversible(`migrate <app> 0001`).
- **왜**: 마이그레이션은 앱이 등록돼 있어야 DROP을 실행한다. 순서가 뒤바뀌면 DB에 빈 고아 테이블 + `django_migrations` 고아행이 남는다(무해하나 위생 저하).

## [fast-main land] 순간 ff-land엔 `git push origin HEAD:main` (2026-07)

- **증상**: 인간 병렬 CC 세션이 분당 커밋하는 fast-main에서, `git checkout main && git merge --ff-only`는 (a) main이 다른 worktree에 물려 `checkout` 거부, (b) rebase가 그 브랜치의 다른 worktree 때문에 거부, (c) merge~push 사이 main 전진으로 non-ff — 반복 실패.
- **규칙**: 브랜치가 정확히 `origin/main+1`(그 브랜치 worktree에서 `git rebase origin/main` 선행)일 때, **`git push origin HEAD:main`** = 원자적 ff-push. worktree/checkout/merge 춤 불필요, main이 그새 전진하면 서버가 non-ff로 **안전 거부**(force 아님) → rebase 재시도.
- **왜**: `push <src>:main`은 서버측 ff 조건을 원자적으로 검사한다. 로컬 checkout/merge 시퀀스는 다중 worktree + 전진 창에 취약. 단 **에이전트의 main 직접 push는 auto-mode가 차단** → land는 사용자 수동 단계로 유지(에이전트는 rebase까지).

## [운영 메모] 메일 CTA 링크 = BE 기동 + 브라우저 로그인 세션 전제 (LINK-DATA-FAIL, 2026-07-07)

- **증상**: 알림 메일 CTA(`/market-pulse-v2`) 클릭 → 화면은 뜨나 "데이터를 불러오지 못했습니다".
- **원인(트리아지 확정, 코드 버그 아님)**: mp 데이터 API(overview·cards)는 `IsAuthenticated`. JWT는 브라우저 **localStorage `access_token`**. 미로그인 브라우저(로그아웃/토큰 삭제/access 만료+refresh 실패)에서 CTA를 열면 overview 401 → mp 페이지가 인증 가드/리다이렉트 없이 바로 실패 문구 표시.
- **전제**: 메일 링크 정상 동작 = ⑴ BE(daphne :18765) 기동 + ⑵ **해당 브라우저의 로그인 세션**(localStorage JWT). CORS(localhost:3000 허용)·FE base(:18765)·딥링크 라우트는 정상(전부 배제됨).
- **개발 전용**: `FRONTEND_BASE_URL=localhost:3000`(prod 도메인 부재)이라 메일 링크는 **개발 PC 전용**. prod 배포 시 도메인 설정 필요.
- **수리 후보(선택)**: 401 구분 문구 + 로그인 리다이렉트(return-to) = TASKQUEUE `MP-401-MSG`(조건부 보류, 실사용 세션만료 혼동 시 트리거).

## [통합 절차] 병행 폭주 + `--rebase-merges` 재정렬 시 브랜치 `-d` 조상검증 구조적 실패 (S3 후속, 2026-07)

- **증상**: fast-main 병행 폭주로 push 경합 → `git rebase --rebase-merges origin/main`로 머지 구조 보존 재정렬 시, 머지·개별 커밋이 **새 해시로 재작성**됨. 결과 원래 feature/mgmt 브랜치 tip이 origin/main의 조상이 아니게 되어 `git branch -d`(머지 검증) + `merge-base --is-ancestor tip origin/main`이 **구조적으로 실패**("미반영"으로 오판).
- **처리 절차**: 브랜치 tip 조상 검증 실패 시 곧바로 `-D`하지 말고, **내용이 origin/main에 실제 반영됐는지 검증**(산출 파일 존재 `git cat-file -e origin/main:<path>` + 대표 변경 라인 grep) → 반영 확인되면 `-D`는 **후보로 보고**, 실행은 사용자 수동(직접 `-D` 금지 — 오삭제 방어).
- **왜**: `--rebase-merges`는 replay라 커밋 객체를 새로 만든다. "브랜치가 안 머지됐다"는 `-d`의 신호는 이 경우 **거짓 음성**이므로, 조상 그래프가 아니라 **내용 반영**을 진실의 소스로 삼는다.

## [앱 철거] `migrate <app> zero`는 데이터-스키마 불일치 시 부분 실패 → 전량 폐기엔 raw DROP CASCADE (D-MONITOR-REBUILD, 2026-07-08)

- **증상**: thesis 앱 철거 중 `python manage.py migrate thesis zero`(전 마이그레이션 역적용=테이블 drop)가 **중간에서 IntegrityError로 중단**. `django.db.utils.IntegrityError: column "value" of relation "thesis_indicatorreading" contains null values`. DB가 **부분 상태**(테이블 12→11, django_migrations 9→2)로 남음.
- **원인**: `migrate zero`는 각 마이그레이션을 **충실히 역재생**한다 — 과거의 필드 변경(예: NOT NULL 제약 추가)을 되돌리며 **옛 스키마를 복원**하려는데, 그 사이 쌓인 데이터(현재 null 허용 컬럼에 실제 null 존재)가 옛 NOT NULL 제약과 충돌. 즉 "reverse migration"은 **데이터가 옛 스키마에 맞을 때만** 안전. 데이터 폐기가 목적인 철거에서는 이 충실한 복원이 오히려 방해.
- **처리(전량 폐기 목적)**: reverse 복원이 불필요하므로 **raw SQL로 직접 DROP** — `DROP TABLE t1, t2, ... CASCADE` (앱 내부 FK는 CASCADE가 처리) + `DELETE FROM django_migrations WHERE app='<app>'` (고아 마이그레이션 레코드 정리). 단일 트랜잭션. **선행 필수**: ⑴ `pg_dump -t '<app>_*'` 아카이브, ⑵ inbound FK 0 확인(leaf면 CASCADE가 타 앱 데이터 미전파: `information_schema` constraint_column_usage 조회).
- **왜 zero를 먼저 시도했나 = 교훈**: graph_analysis CUT 선례(DeleteModel 마이그레이션)와 달리 `migrate zero`가 더 간단해 보였으나, **데이터가 있는** 앱에선 reverse 충실성이 함정. 데이터 없는 앱은 zero 안전, **데이터 있는 앱 폐기 = raw DROP**이 정석. beat는 DB PeriodicTask 기준이라 disable→행 삭제 별도 필요(#28).

## [git 위생] `git add` 다중 pathspec 중 하나라도 미매칭이면 add 전체 중단 → 신규 파일 누락 (Monitor 트랙, 2026-07-09, 반복 3회)

- **증상**: `git add A B C` 실행 시 하나(예: 이미 `git rm`된 경로 `A`)가 워킹트리에 없어 `fatal: pathspec 'A' did not match any files`가 나면, **git add가 전체를 중단**하고 B·C도 스테이징되지 않는다. 이어서 pathspec 없는 `git commit`을 하면 **직전에 `git rm`으로 스테이징된 삭제분만** 커밋되고(=broken commit), **신규/수정 파일은 미커밋**으로 남는다. Monitor 트랙에서 3회 반복(C2 FE 철거·53889bb thesis 처분·ede1160 P3-S1): 각각 "삭제만 커밋되고 실체 누락".
- **원인**: git add는 나열된 pathspec을 원자적으로 검증 → 하나라도 미매칭이면 non-zero exit + 아무것도 add 안 함(부분 add 아님). 이미 `git rm`/`git mv`로 처리된 경로를 뒤이은 `git add`에 다시 넣으면 그 경로가 워킹트리에 없어 미매칭.
- **처방**:
  1. `git rm`/`git mv`로 처리한 경로는 **뒤따르는 `git add`에 다시 넣지 않는다**(이미 인덱스에 반영됨).
  2. `git commit` 직후 **`git status --short`로 미커밋 잔여 0 확인**(신규 `??` 파일 특히 주의). 잔여 있으면 add 후 `--amend`(미push 시)로 정합화.
  3. 안전책: 삭제·이동과 신규·수정을 **별도 스테이징 단계**로 분리하거나, `git add -A <디렉터리>`로 디렉터리 단위 스테이징.
- **탐지**: 커밋 stat이 "deletions only"인데 관련 신규 파일이 있어야 하면 이 버그를 의심. rename/신규가 사라진 broken 중간 커밋은 push 전 `git show --stat HEAD`로 검출.

## [Celery beat] ET 스케줄 태스크에서 `timezone.localdate()`는 Seoul 날짜 → 거래일 off-by-one (MON-P2-BEAT, 2026-07-09)

- **증상**: 미국 EOD 후(예: 18:45 America/New_York) 도는 beat 태스크가 `timezone.localdate()`로 "오늘"을 구하면, 프로젝트 `TIME_ZONE=Asia/Seoul`(USE_TZ=True)이라 **Seoul 날짜(=ET 기준 +1일)**를 반환한다. 18:45 ET ≈ 다음날 07:45 KST이기 때문. 결과: 신선도 가드가 엉뚱한 날짜를 검사하고, ingest 범위·스냅샷 `asof_date`가 실제 EOD 거래일보다 하루 앞서 기록됨.
- **원인**: `CELERY_TIMEZONE='America/New_York'`(스케줄 발화 시각)와 `TIME_ZONE='Asia/Seoul'`(localdate 기준)이 다르다. beat 발화는 ET로 맞지만, 태스크 본문의 날짜 계산은 Seoul 기준이라 어긋난다.
- **처방**: ET 기준 거래일이 필요한 태스크는 명시 계산한다 — `timezone.now().astimezone(ZoneInfo("America/New_York")).date()` (예: `apps/monitor/tasks.py:et_today`). 이 값을 신선도 가드(`max(EODSignal.date) == et_today`)와 서비스 `as_of_date`에 일관 주입해 EOD 거래일에 정합시킨다. `localdate()`는 사용자 로컬 표시용이지 미국 거래일 판정용이 아니다.
- **일반화**: EODSignal·DailyPrice 등 미국 거래일(ET) 키를 다루는 모든 Celery 태스크에 적용. beat 시각대(CELERY_TIMEZONE)와 날짜 계산 시각대(TIME_ZONE)가 다를 때 항상 의심.
## [측정 함정] 소급 시뮬 수락 앵커는 입력 데이터 스냅샷에 결박 — 후속 재현은 경계값에서 ±1 갈림 (CD-STAB A′, 2026-07-09)

- **증상**: 측정 세션이 소급 시뮬로 산출한 수락 앵커(CD-STAB C = 총 반전 83·반전율 0.175)를 다음 세션의 랜딩 구현이 재현하려 하자 **84 / 0.1776**이 나옴(1반전 차이). 방법론 자체는 옳음 — 동일 파이프라인으로 Slice B 앵커(99/0.209)는 **정확 재현**됨.
- **원인**: 앵커는 **측정 시점의 입력 데이터 스냅샷에 결박**된다. ⑴ 경계값(XLU 2026-05-19 rel5=+0.00998, 카운트 창 idx=5 경계)이 baseline 0에 razor-thin으로 근접 → 입력 미세 변화에 부호가 갈림. ⑵ 측정 세션 이후 가격 재fetch·스냅샷 갱신으로 데이터 상태가 이동(시뮬 83이 저장값 기준 84·가격 재계산 82 **사이**에 위치 = 데이터 드리프트 지문). 정밀도 반올림(6자리)은 무관(변형 4종 전부 84).
- **처방(측정 세션)**: 앵커 수치와 **함께 입력 지문**을 기록 — 대상 행 수·창 경계(from/to)·관련 테이블 최종 갱신 시점(예: SectorFlowSnapshot 528행/48일, SPY MarketIndexPrice ≤07-09/101행). 그래야 후속 세션이 "같은 데이터였는가"를 판정 가능.
- **처방(하드 게이트 문안)**: "정확 재현" 게이트에 *"동일 데이터 상태 전제, 경계 1건 이내 편차는 원인 규명 시 디렉터 판정"*을 명시. 규칙 #3(서빙-정확 입력=저장값)과 시뮬(재계산 가능)이 다르면 **서빙값 기준이 진실** — 앵커를 서빙값으로 이원화(방법론 앵커=알고리즘 충실성 증명 / 서빙 앵커=랜딩 실측). 참조 D-CD-XAXIS-SCOPE.
- **왜**: 소급 시뮬은 "그때 그 데이터"의 함수다. 앵커를 불변 상수로 취급하면 경계값 1건이 갈릴 때 멀쩡한 구현이 게이트에 막힌다. 앵커는 **입력 지문과 한 쌍**일 때만 재현 가능한 계약이 된다.

## [dev 환경] Turbopack "@swc/helpers 모듈 못 찾음"은 파일 존재해도 발생 — .next 청소 무효, npm ci가 해결 (DEV-3000-DOWN, 2026-07-09)

- **증상**: :3000 next dev(Next 16.2.6 Turbopack)가 페이지 요청에 **500 + 빈 화면**. 콘솔/로그 = `Error: Cannot find module '@swc/helpers/_/_interop_require_default'`, **Next.js 자체 client 런타임 청크**(`node_modules_next_dist_client_*.js`)에서 발생 = **앱 코드 진입 전** 실패(어느 앱 페이지든 동일). 증상 프로필의 함정: **파일은 물리적으로 존재하고 `node require.resolve`로도 정상 해석되는데** 오직 Turbopack 번들러만 못 찾는다.
- **확정 진단(전부 read-only로 기각)**: ⑴ node 버전 정상(실행 프로세스 lsof txt → v22.19.0, /usr/local/bin의 구 v20.11 아님). ⑵ node_modules = 실디렉토리(심링크 아님), git re-detach가 안 건드림(mtime이 checkout 이전). ⑶ `@swc/helpers` 0.5.15 = `next` package.json 기대치 정확 일치, `cjs/esm` 각 104파일 완비, exports 맵에 `./_/_interop_require_default` 항목 존재, 중복 패키지 0, `node -e require.resolve(...)` 성공. ⑷ `rm -rf .next`(903M) + 재기동해도 **재현**(→ .next 캐시 아님).
- **확정 원인·처방**: **`npm ci`(실경로 node_modules, v22.19.0) + `rm -rf .next` + 재기동 → HTTP 200·에러 0으로 복구.** 즉 원인은 @swc/helpers 자체 결함이 아니라(그건 멀쩡) **node_modules 설치 상태의 미묘한 불일치**(package-lock과의 드리프트/부분 상태) — **node의 관대한 resolver는 통과시키나 Turbopack의 엄격한 resolver가 거부**하며, 그 증상이 하필 next 런타임의 @swc/helpers import에서 표면화. `.next` 청소로는 안 풀리고 **전체 재설치(npm ci)만** 정규화한다.
- **복구 사다리(싼 것부터, 한 칸씩 검증)**: ⒜ 실행 프로세스 node 버전 확인 → 불일치면 nvm 올바른 버전으로 재기동만. ⒝ node_modules 실체(심링크/mtime) 확인 → 트리 불일치면 실경로 정리. ⒞ **⒜⒝ 기각 시 `npm ci`(실경로) + `.next` 제거 + 재기동**(이번 건 여기서 복구). ⒟ 그래도 재현이면 Turbopack 자체 버그 가능성 → webpack dev 폴백 등은 디렉터 결정.
- **운영 함정(관측, 인과 미확정)**: 이번엔 `worker_sync.sh`(sv sync)가 web 런타임 트리를 origin/main으로 **re-detach(git checkout)하는 동안 next dev 서버가 계속 기동 중**이었다(reflog 16:01·16:42·16:53 checkout, 그 사이 dev PID 생존). worker_sync는 web 트리를 **재기동 없이 "핫리로드 반영"만** 한다(주석 명시). 라이브 checkout이 위 불일치를 유발했는지는 **확정 못 했으나**(node_modules mtime은 checkout 이전이라 checkout이 파일을 바꾼 건 아님), 복구에 dev **완전 재기동 + npm ci**가 필요했던 점에서 — **worker_sync의 web 트리 처리에 "next dev 선종료→재기동" 추가 여부**를 후속 검토 대상으로 남긴다(P1 일상 표면이므로 조용한 500은 치명적).

## [백필 함정] FREDClient.get_series_observations 기본 limit=100·sort desc — 심층 백필 시 반드시 override (B1-S1, 2026-07-10)

- **증상**: `backfill_v2_a1`의 FRED 경로 9건 전부 "0 obs inserted"(에러 없음). Yahoo 경로(VIX3M·MOVE·SPY)는 정상 삽입. 인증·CB 무관(키 정상, 좁은 창 23건 실값 반환).
- **원인**: `FREDClient.get_series_observations(...)` 기본 인자 **`limit=100, sort_order='desc'`**. `_fetch_fred`가 이를 **넘기지 않아** 3년 창이라도 **최신 100건(desc)만** 요청 → 그 100건은 전부 최근 날짜(현 DB min 이후)라 `get_or_create`가 **기존으로 skip → 0 삽입**. 심층 과거 행(예: HY 2023-07~2026-02)은 **요청 자체가 안 됨**. Yahoo(`yf.history`)엔 이 cap이 없어 정상이었음.
- **처방**: 심층 백필 호출엔 **`limit=100000`(FRED 최대)·`sort_order='asc'` 명시**. backfill_v2_a1은 이 수정으로 해소(`7759265`). **신규 FRED 소비처 작성 시 주의** — 증분 sync(최신 N건)는 기본 limit=100으로 충분하나, **백필/히스토리 성격이면 반드시 limit override**(안 하면 조용히 최신 100만).
- **로깅 교훈**: "N obs inserted" 단일 출력은 **"0=이미 존재"와 "0=못 가져옴"을 침묵 동치**로 만든다 → `fetched N, inserted M` 구분 출력으로 해소(같은 커밋). 백필 커맨드는 fetch 수와 insert 수를 항상 분리 노출할 것.

## [리허설 사각] dry-run은 API 무호출 — fetch 층 결함은 리허설로 미탐지 (B1-S1, 2026-07-10)

- **증상**: B1-S1 후보 리포트에서 `--dry-run`은 대상·창을 정상 출력했으나, 실제 실행에서 FRED 전건 0행(위 limit 함정)이 드러남.
- **원인**: `backfill_v2_a1`의 `--dry-run`은 대상 목록만 출력하고 **fetch 호출 전에 return**(API 무호출). fetch 층(get_series_observations limit)의 결함은 리허설 경로를 **구조적으로 지나침**.
- **교훈**: dry-run 통과 ≠ fetch 정상. 신규/변경 백필 경로 검증엔 **좁은 창 실 fetch 1콜**(예: 1개월)을 별도로 돌려 반환 건수를 눈으로 확인할 것. 후보 리포트에 "실 fetch 리허설 1콜" 항목을 포함하면 이 사각을 닫는다.

## [백필 함정] 소급 행이 '경계 앵커'를 스스로 오염 — 멱등 재실행 시 보호 창 붕괴 (B1-S2, 2026-07-10)

- **증상**: `backfill_v2_regime_vectors`가 대상 창 상한을 `RegimeSnapshot.objects.min(date)`(라이브 최초일)에서 파생. 1차 실행이 과거 행을 합성하면 min(date)가 과거로 끌려내려가, **재실행 시 상한 = 합성 최초일 − 1** → 창이 붕괴(빈 창 CommandError). 첫 회는 정상, 재실행만 깨짐(멱등성 위반).
- **원인**: 보호 경계를 "쓰기 대상과 같은 테이블의 집계"에서 파생하면, 쓰기가 경계를 이동시킨다(자기참조 오염). get_or_create의 "기존행 불가침"은 지켜지지만 **창 산정 자체가 무너짐**.
- **해결**: 합성행에 **불가시 provenance 마커**(여기선 `summary="[BACKFILL_V2]"` — 이 필드는 어떤 RegimeSnapshot serializer에도 미노출임을 grep으로 확인)를 박고, 경계는 `exclude(summary=MARK).min(date)`로 **합성행을 제외**해 산정. 라이브 행만 경계에 기여 → 재실행 무해.
- **교훈**: 백필/멱등 커맨드에서 **보호 경계는 쓰기 대상이 오염시킬 수 없는 소스에서 파생**할 것. 같은 테이블에서 파생해야 한다면 합성분을 구별하는 마커가 필수. 마커 필드는 사용자 노출 여부를 먼저 확인(노출되면 UI 오염). 회귀 테스트에 "재실행 시 synthesized=0/skipped=N + 창 불변"을 박제.

## [이관 함정] 앱 재배치(`portfolio`→`apps.portfolio`) 후 테스트가 구 경로를 참조 — 2형, green이 조기 maxfail로 착시 (PF-TEST, 2026-07-13)

- **증상**: PR7에서 `portfolio/`를 `apps/portfolio/`로 `git mv` 후, coach 테스트 **43건**이 실패. 소스·마이그레이션은 정상(no changes detected)인데 테스트만 red.
- **원인 2형(둘 다 이관 잔재, 로직 회귀 아님)**:
  1. **경로 문자열 stale (31건)**: `mock.patch("portfolio.api.views.run_e1_coach")`·`@parametrize("portfolio.services.coach.eN_service")` 등 **문자열로 된 모듈 경로**는 `git mv`가 갱신하지 않음 → `ModuleNotFoundError: No module named 'portfolio'`. (import 문은 IDE/grep로 잡히지만 patch/parametrize **문자열은 안 잡힘**.)
  2. **경로 오프셋 `parents[N]` (12건)**: `Path(__file__).resolve().parents[2] / "docs/..."`가 앱이 `apps/` 하위로 **한 단계 깊어져** repo_root 계산이 어긋남 → `apps/docs/...` FileNotFoundError·빈 `load_raw()`(`assert 0 == 14`). `parents[2]→parents[3]`.
- **착시 함정**: `pytest`가 기본 addopts의 `maxfail`로 "5 failed"에서 조기 중단 → 실제 43건을 과소평가(TASKQUEUE도 "5건"으로 등재됨). **선행 게이트 판정 시 `--maxfail=1000`으로 전수 확인** 필수. 반대로 `-o addopts=""`로 덮으면 ini의 `filterwarnings`(구 Django 카테고리)까지 노출돼 별도 에러 → **addopts 유지 + `--maxfail` 만 CLI 오버라이드**.
- **오탐 주의(무접촉 대상)**: 같은 grep에 걸려도 `caplog.at_level(logger="portfolio.llm.cost_guard")`(로거명)·회귀 분류기 데이터 `["portfolio/llm/cost_guard.py"]`(경로 패턴)는 **stale 아님**(현재 통과 중). 치환 전 "실패 목록에 대응하는가"로 필터링 — 통과 테스트를 깨지 말 것.

## [보존 함정] 롤링 purge가 백필 자산을 먹음 — 블랭킷 date cutoff가 심볼 무인지 (A-S0, 2026-07-13)

- **증상**: B1-S2가 백필한 SPY EOD 768행(2023~)이 3일 만에 265행(최근 1년)으로 축소. analog 사후수익률 모집단 683→**199(71% 결손)**. IndicatorValue 3년 백필도 동일 축소.
- **원인**: `apps/market_pulse/tasks/macro.py::cleanup_old_data`(celery beat `cleanup-old-macro-data`, 주간 일요일)가 `MarketIndexPrice.filter(date__lt=today-365).delete()` — **블랭킷 date cutoff, 심볼/출처 무인지**. 백필 자산(과거 3년)이 롤링 창 밖이라 매주 재삭제 → 백필과 purge가 상쇄(백필→다음 일요일 소실).
- **해결(A-S0, 방식 나)**: `PRESERVED_INDEX_SYMBOLS`(SPY) 도입 → purge에서 `.exclude(index__symbol__in=...)`. 모델 무변경(마커 필드 X = prod 마이그레이션 회피). 재백필 전에 보존 예외가 **먼저/함께 land**해야 재소실 방지(순서 규율).
- **교훈**: 백필로 채운 과거 자산이 있으면 **롤링 purge/retention이 그것을 인지하는지 먼저 확인**. 심볼/출처 무인지 blanket cutoff는 백필과 상충. 백필 커맨드 DoD에 "보존 예외 대상인가" 포함. 마커(가) vs 심볼 예외(나) 택일 = 정책 형태 + 마이그레이션 비용(모델 변경이 prod 마이그레이션이면 나 우선).
- **⚠️ 미해소 동류 지뢰 (IndicatorValue)**: 같은 `cleanup_old_data`가 `IndicatorValue.filter(date__lt=today-365).delete()`도 실행 — B1-S2가 백필한 매크로지표 3년치도 매주 삭제 중. **현재 analog 벡터는 stored(RegimeSnapshot.inputs JSON)라 무영향**이나, **S4-REBASE 재합성(라이브+소급 재-z) 시 71% 결손이 재현**된다. A-S0는 SPY만 보존 → IndicatorValue는 미보존. TASKQUEUE `INDVAL-PURGE-LANDMINE`(트리거=S4-REBASE)로 등재. 재합성 착수 시 A-S0와 동형(코드/시리즈 보존 예외) 선행 필수.
- **교훈**: 앱 재배치 시 ⑴ `grep -rn "[\"']<oldapp>\." tests/`로 **문자열 경로**를 별도 스윕, ⑵ `parents[N]` 상수를 전수 재계산, ⑶ green 판정은 `--maxfail` 해제 전수. 유형은 CS-TEST(chainsight)와 동일 — 이관 PR은 "테스트 문자열·경로 상수 스윕"을 DoD에 포함.

## 해소된 결정이 구 'pending' 블록 미갱신으로 stale 잔존 → 인계로 무검증 전파 (#52, 2026-07-13 MGMT-HARDEN) `[harness]` `[decision]`

- **증상**: 결정/항목이 해소(LANDED/확정)됐는데 그 사실이 **새 PROGRESS 블록 append로만** 기록되고, 원래의 'pending/대기'(⏸️) 블록은 그대로 잔존. 다음 세션이 구 블록만 읽고 "아직 대기"로 **무검증 전파**(2026-07 D2 phantom: T-3b(`3a3e921`)로 소화된 "결정 4건 대기"를 후속 인계가 "대기 중"으로 오전파). **부수 위험**: 배치 지시서의 일부 슬라이스가 조용히 누락돼도 append-only 기록은 "다 했다"처럼 읽힘.
- **원인**: PROGRESS는 union-merge append 로그라 새 블록이 계속 쌓이지만, **구 블록의 상태는 자동 갱신되지 않는다**. 해소 사실과 원 pending 블록이 물리적으로 분리되면, 스캔 순서·상속 메모에 따라 구 상태가 살아남는다.
- **소진(3층 방지, MGMT-HARDEN)**:
  1. **A 백-어노테이션 규약**(SESSION_CONTRACT DoD): 해소 시 원 블록에 **해소 델타(→ RESOLVED/LANDED/SUPERSEDED @커밋) 부기 필수** — 새 블록 append로 끝내지 않는다. 원문은 취소선/註로 보존(삭제 금지).
  2. **C health_check WARN**(`scripts/health_check.py::check_stale_pending_backannotation`): PROGRESS의 ⏸️ 블록 중 해소 델타 없이 3 거래일 초과 방치 → WARN(FAIL 아님). TASKQUEUE 제외(큐는 장기 pending 보유 설계).
  3. **D STEP 0 재측정**(SESSION_STARTUP_CHECKLIST): 상속된 인계 메모/타 트랙 'pending' 주장은 **행동 전 그 트랙 현재 장부로 재측정**(추정 전파 금지).
- **교훈**: append-only 로그에서 "상태"는 스스로 갱신되지 않는다 — 해소는 **원 지점 back-annotation**으로 닫아야 한다. 그리고 **실행 보고는 반드시 지시서 DoD 전수 대조**(일부 슬라이스 조용한 누락 방지). 검문소는 "해소 델타 유무"라는 값싼 신호로 phantom을 잡는다.
## [백필 함정] FMP 뉴스 과거 조회 = 402 유료벽 + 페이지 캡 → AV NEWS_SENTIMENT가 과거 소스 (Slice C-N, 2026-07-13)

**증상**: analog 카드 L3(그날의 맥락) 그라운딩용 과거 시장 뉴스를 FMP로 백필하려 하니 `/stable/news/stock`·`general-latest`에 `from`/`to` 날짜 파라미터 = **402 Premium Query Parameter**. 페이지네이션도 page~200부터 400(캡), page50(limit100)이 ~2026-05 도달 한계. 모집단(2023~) 미도달.

**원인**: FMP Starter 플랜은 뉴스·경제캘린더 공히 **historical 날짜 범위 = 프리미엄**. 최근 뉴스만 limit로 제공(그래서 NewsArticle이 2025-12+ 7개월뿐).

**해결**: **Alpha Vantage NEWS_SENTIMENT** 사용. `AlphaVantageNewsProvider.fetch_broad_news(time_from, time_to, limit≤1000, sort)`가 과거 창 조회 지원(실측 2023-09 도달, 모집단 전 구간 커버). 제약 = 무료 25 req/day·1 req/s → 전량 백필은 병진 수일(`--max-requests` 배치). 커맨드 `services/news/management/commands/backfill_broad_news.py`가 라이브 broad 수집과 동일 save 경로(dedup+url upsert 멱등) 재사용.

**교훈**: 과거 데이터 소스는 provider별 tier 차이가 크다 — FMP historical=프리미엄, AV NEWS_SENTIMENT=무료 과거창(단 25/day). 백필 착수 전 GN(과거 타당성) 프로브 필수. 지시서가 특정 provider(FMP)를 지목해도 GN 정신(과거 가용성)은 대체 provider로 충족 가능.

## [보존 함정 후속] NewsArticle은 나이 purge 아닌 soft delete(is_archived) — 백필분 영속, 단 그라운딩 쿼리는 is_archived 포함 (Slice C-N, 2026-07-13)

**맥락**: A-S0(SPY)·IndicatorValue는 롤링 purge에 삭제되어 보존 예외가 필요했으나, **NewsArticle은 삭제 경로 없음**. `archive_old_articles`(services/news/tasks.py)가 6개월+ 기사를 `is_archived=True`로 **soft delete**만 — 행 영속. → 과거 뉴스 백필은 SPY식 보존 예외 불필요.

**함정**: 그러나 백필한 과거 뉴스는 즉시 `is_archived=True` 대상(6개월+). **C-L3 그라운딩 쿼리가 `is_archived=False` 필터를 걸면 백필분 전량 누락**. → 그라운딩은 `is_archived` 무관(또는 True 포함)으로 조회해야 함.

## [테스트 함정] FMP autouse 더미키 픽스처 — "키 부재" 시나리오는 본문에서 로컬 override 필수 (⑮ 도입, ⑯ 등재 2026-07-14) [process]

**맥락**: `tests/conftest.py`의 `_ensure_fmp_api_key`(autouse)가 FMP 키 부재(falsy) 시 `settings.FMP_API_KEY` + `os.environ`에 더미(`test_dummy_fmp_key`)를 주입한다(⑮ FMP-TESTDEBT env-독립화). 덕분에 provider 인스턴스화가 CI(키 없는 env)에서도 결정론적으로 성공한다.

**함정**: 따라서 **"키 부재" 시나리오를 테스트하려면 테스트 본문에서 로컬 override로 키를 명시적으로 제거**해야 한다 — 안 하면 autouse 픽스처가 더미를 깔아 테스트가 "키 있음" 경로로 **조용히 통과**한다(거짓 green). 올바른 선례: `tests/marketpulse/fetchers/test_fmp_weights.py::TestRequestEtfHolderGuards::test_missing_api_key_raises` — `settings` 픽스처로 `settings.FMP_API_KEY=None`을 테스트 본문에서 세팅 후 `pytest.raises`(본문이 픽스처 setup보다 후행이라 override 성립).

**일반화(동형 함정 주의)**: autouse 픽스처/ambient `.env`가 설정값을 채워 격리성을 주는 경우, 그 값의 **부재/반대 상태를 검증하는 테스트는 반드시 로컬 override로 상태를 되돌려야** 한다. **미상환 동형 사례(⑯ 발견)**: `.env`에 `CHAINSIGHT_GROUP_SOURCE=event_group`(go-live)이 있어 `settings_test`가 이를 상속 → EventBoard/Ranking 테스트가 `theme_tags`로 시드하면서 플래그를 고정하지 않아 event_group 경로로 읽혀 실패(**chainsight 13 red = attention 6 + leadership 7**, 전부 test-only). 해법 동일 = 테스트에서 `override_settings(CHAINSIGHT_GROUP_SOURCE=...)`로 플래그를 결정론적으로 고정. **★해소됨(⑰ S3, 2026-07-14 `8377ba5`)**: override 주입 대신 **chainsight 13 red 테스트를 `event_group` 시드로 재작성**(go-live 플래그와 정합) → theme_tags 경로 의존 제거. 검증: pristine origin/main(`6013865`) 전체회귀 **3866 passed·0 failed**(⑱ STEP 0 실측)로 재확인 — attention 6 + leadership 7 red 소멸.

## [검증 함정] 서브에이전트의 "통과" 주장 = 해당 worktree에서 직접 재실행으로만 신뢰 (⑰ S2 실증, ⑱ 등재) [process]

**증상**: 서브에이전트(또는 타 세션)가 "tsc 0 / pytest green"을 보고해도, 그 검증이 **다른 worktree·다른 브랜치·공유 test DB** 위에서 돌았다면 현 세션 트리의 실상과 어긋날 수 있다. cross-worktree 환경에서 green은 "그 트리에서 green"일 뿐, 인계받는 트리의 보증이 아니다.

**원인**: ① worktree마다 체크아웃 코드·`node_modules`(심링크 여부)·`.env`가 다름 ② 공유 test DB/캐시 오염(stale 시드·`_dormant` 잔재)이 특정 트리에서만 red/green을 만듦(예: news-av-broad 트랙의 `_dormant/graph_analysis` + 공유 test DB가 attention 5건 오탐) ③ 서브에이전트는 자기 컨텍스트의 트리를 검증하지, 호출자 트리를 검증하지 않음.

**해결**: 서브에이전트의 tsc/pytest 통과 주장은 **인계 후 호출자 자신의 worktree에서 직접 재실행**으로만 확정한다(주장을 그대로 승계 금지). UI/시각 산출물은 [[feedback_ui_slice_live_screenshot]]과 동형 — 라이브 재현으로만 종결. 판정이 오염에 민감한 chainsight류는 **pristine 체크아웃**(origin/main 신규 worktree)에서 재측정.

**교훈**: "누가 어느 트리에서 green을 봤는가"가 green 자체보다 중요하다. 검증의 신뢰 경계는 worktree다 — 경계를 넘은 green은 재실행 전까지 미검증이다. #45/#47(repo 스크립트를 어느 트리 사본으로 실행하나)의 검증판 동형.

## [배포 절차] daphne/celery는 런타임 트리에서 서빙 → main 머지만으로 화면 미반영, worker_sync 동기화 + 재시작 필수 (⑰-M 실증, ⑱ 등재) [ops] [git]

**증상**: FE/BE 코드를 origin/main에 머지했는데도 **라이브 화면·API 응답이 구코드**. 테스트 green·push 성공인데 사용자 화면에 반영 안 됨.

**원인**: 런타임 3종(celery worker=`sv-worker-runtime`·next dev web=`sv-web-runtime`·daphne API=`sv-api-runtime`)은 **공유 편집 트리가 아닌 전용 런타임 트리**(detached origin/main)에서 서빙된다(#45 종결의 귀결). main 머지는 origin 참조만 전진시킬 뿐, 런타임 트리 사본을 자동 갱신하지 않는다.

**해결**: 배포 = **⑴ main 머지 → ⑵ `sv sync`(=런타임 트리 사본 `worker_sync.sh`, 3트리 origin/main로 재-detach) → ⑶ daphne·celery 재시작** 순서를 반드시 완주. next dev(web)는 핫리로드지만 daphne/celery는 프로세스 재기동 필요. 머지에서 멈추면 "머지했는데 화면 그대로" 함정. 스크립트는 반드시 런타임 트리 사본으로([[#47]] `sv` 래퍼), 공유 트리 사본은 stale.

**교훈**: "머지 = 배포"가 아니다. 런타임 분리 아키텍처에서 배포의 마지막 칸은 **런타임 트리 동기화 + 재시작**이다. 코드가 origin에 있음 ≠ 서버가 그 코드를 실행 중.

## 배포 체크리스트 — 마이그레이션·env 인라인 포함 슬라이스 (단일 출처) [ops] [deploy]

> **단일 출처**: 마이그레이션 또는 FE env 인라인을 포함하는 슬라이스의 배포 규약은 **본 항목 하나**에 둔다. 세션 지시서·CLAUDE.md는 포인터만(복제 금지 — drift). 런타임 트리 동기화·재시작은 위 [배포 절차](⑰-M, sv sync) 항목과 짝.

마이그레이션·env 인라인을 포함하는 슬라이스는 **배포 단계**에 다음을 명시·완주한다:
1. **prod migrate**: `sqlmigrate`로 순수 add 육안 → `migrate` → `showmigrations`로 적용 확인. (코드 착지 ≠ DB 적용 — #53.)
2. **적용 검증은 서빙 프로세스와 동일 env/연결 기준**: "테이블 존재"·"번들 반영"은 **서빙 프로세스가 실제로 보는 DB 연결/체크아웃**에서 확인(셸 env ≠ 서빙 env — #54).
3. **FE env 인라인 변경 시**: 재빌드 + 재기동 + **번들 검증**(컴파일 산출물에 절대 URL/env 리터럴이 인라인됐는지 grep). `NEXT_PUBLIC_*`은 빌드타임 인라인 — 머지·핫리로드만으로 미반영 가능(#55).

## 코드 착지 ≠ prod DB 적용 — migrate는 배포 단계, 착지 보고만 믿지 말 것 (#53, 2026-07-16 P2-IMPR-CLOSE) [db] [ops] [deploy]

**증상**: 모델·마이그레이션을 origin/main에 머지·"착지 완료" 보고했는데 런타임 write 500. (P2-IMPRESSION: `apps/platform` ImpressionLog 테이블 부재 → ingest 500.)

**원인**: 마이그레이션 파일 착지 = 코드일 뿐, **prod DB 적용은 별개의 배포 단계**. 착지 보고를 "적용됨"으로 오독.

**해결**: land에 migration 포함 시 **배포 단계에 prod migrate를 명시**(위 배포 체크리스트 ①). 착지 보고와 DB 적용을 분리 추적. cf. #46(migration 미적용 → write 조용히 실패), 런북 `P1-RUNBOOK-MIGRATE`.

## 적용 검증은 서빙 프로세스 기준 — 셸 env ≠ 서빙 env (#54, 2026-07-16 P2-IMPR-CLOSE) [ops] [db] [deploy]

**증상**: "테이블 있음"·"코드 최신"을 셸에서 확인했는데 서빙은 여전히 실패/구코드.

**원인**: 확인에 쓴 셸의 env/DB 연결·체크아웃 트리가 **서빙 프로세스(런타임 트리·launchd env)와 다름**. 셸에서 보이는 상태 ≠ 서버가 보는 상태.

**해결**: 적용·번들 검증은 **서빙 프로세스가 실제로 보는 것**으로. DB는 서빙 DB 연결에서 `showmigrations`, FE 번들은 서빙 트리 `.next` 컴파일 산출물 grep. cf. #45(공유 트리 표류→구코드 bake), 배포 체크리스트 ②.

## FE 신규 API 호출은 앱 base 규약(NEXT_PUBLIC_API_URL 절대 base) 준수 — 상대 URL 금지 (#55, 2026-07-16 P2-IMPR-CLOSE) [frontend] [ops]

**증상**: FE 신규 API 호출이 죽은 포트(:8000)로 라우팅되어 실패. (P2-IMPRESSION telemetry가 상대경로 `/api/v1/telemetry/impressions` 호출 → Next dev origin에 붙어 stale rewrite로 :8000.)

**원인**: 상대 URL은 페이지 origin(:3000)에 붙어 **next.config의 stale rewrite**로 흘러감. 앱 API 호출은 `NEXT_PUBLIC_API_URL`(=/api/v1 포함 절대 base) 규약을 쓰는데 신규 호출이 이를 우회.

**해결**: 신규 FE API 호출은 반드시 **앱 base 규약**(authAxios와 동일 `NEXT_PUBLIC_API_URL` 절대 base) 준수. **죽은 포트 하드코딩 폴백 금지** — env 미설정 시 skip+warn(유실 허용 데이터) 또는 앱 표준 폴백. 해소 = FIX-1(`46e6865`, 번들 검증까지). cf. 배포 체크리스트 ③.

## 실행자 세션은 .env 파일을 열지 않는다 — 환경변수 확인은 키 존재 bool까지, 값 출력 금지 (#56, 2026-07-16 STEP0-P2-AXIS) [security] [process]

**증상**: 실행 세션이 환경변수를 확인하려 `.env`를 grep/cat하다가 시크릿 원문이 stdout·로그에 노출. (07-16 STEP0-P2-AXIS: 마스킹 정규식이 `GEMINI_API_KEY_..._PROJECT=` 형태를 놓쳐 **API 키 원문 1회 노출** → 키 회전 조치 유발.)

**원인**: `.env` 개봉 자체가 노출 표면. 마스킹 sed/정규식은 키 이름 변형(접미사·언더스코어)에 취약 — 한 줄이라도 빠지면 유출.

**해결**: **실행자 세션은 `.env`를 열지 않는다(grep 포함).** 환경변수 확인이 필요하면 ⑴ 프로세스 env 로드는 기존 설정 경로(Django settings·Next 로더)에 맡기고, ⑵ 확인은 **키 존재 여부 bool까지만**(`bool(os.environ.get(...))` 또는 파일 미개봉 `grep -c '^KEY='` 카운트) — **값·head/tail·풀 문자열 출력 절대 금지**([[feedback_secret_masking_policy]] 승계). **자기점검**: 지시서에 ".env 접근 금지" 조항이 포함됐는지 확인하고, 없으면 실행자가 보수적으로 금지 적용.

## [DoD 함정] celery 태스크 신설 = tasks/__init__ import 누락을 단위 테스트가 못 잡는다 (⑲ 배포 실증) [process] [celery]

**증상**: 신규 celery 태스크의 단위 테스트(함수 직접 호출·`.apply()`)는 전부 green인데, 실배포 워커가 태스크를 **미등록**(`celery inspect registered`에 없음) → beat 등록해도 "task not registered"로 미발화.

**원인**: `tasks/` 가 **패키지**일 때 celery autodiscover는 `tasks/__init__.py`만 임포트한다. 서브모듈(`centrality_tasks.py` 등)은 `__init__.py`에서 명시 import해야 `@shared_task`가 레지스트리에 등록된다. 단위 테스트는 모듈을 직접 import해 호출하므로 이 누락을 우회(거짓 green). ⑲ S3에서 `centrality_tasks` import 누락 → 배포 중 워커 registered 검증에서 포착, fix `f2397b4`.

**해결**: 신규 celery 태스크 슬라이스의 **DoD에 등록 검증 필수** — `app.loader.import_default_modules()` 후 `'<task path>' in app.tasks` 또는 라이브 워커 `celery inspect registered` 확인. [[lesson_celery_task_registration]](워커 재시작 필수)의 등록판. 배포 시 `worker_sync` 재기동 후 registered 재확인.

## ego 그래프 렌더 단절 = FE↔BE URL 미스매치(미검증 이월) (#57, 2026-07-16 ⑳-D DIAG) [frontend] [chainsight] [process]

**증상**: market-graph focus/ego 경로가 **모든 심볼에서 빈 캔버스**. 리더보드 행 클릭 → `?focus=SYM` → 그래프 안 그려짐. API·테스트는 전부 green이었음.

**원인 (2중 게이트, 실측)**:
1. **URL 미스매치(주근인)** — 백엔드 라우트 `apps/chain_sight/api/urls.py:36` = `ego/<symbol>/`(동적 경로와 충돌 회피 위해 `ego/` 프리픽스 분리), 그러나 프론트 `chainsightService.ts:85` `fetchEgo`는 구 패턴 `/chainsight/${symbol}/ego/` 호출. resolver 실측: `/chainsight/AAPL/ego/` → **404**, `/chainsight/ego/AAPL/` → OK. 프론트 배선 첫 커밋(`a9256b8` S2)부터 어긋나 **한 번도 작동한 적 없음**(회귀 아님·미검증).
2. **시드 제약(부근인)** — `market-graph/page.tsx:24` focus 핸들러가 `seedData.seeds.find(...)` 있을 때만 초기화. 리더보드 상위(centrality)는 대체로 비-시드(NVDA#1·MSFT·AAPL이 오늘 시드 20개에 없음) → 조용히 무시.

ego API 자체는 **PG 네이티브(`EgoGraphView`)·Neo4j 무의존**으로 건강(NVDA 48노드/224엣지 200 405ms). 섹터 모드만 별개로 Neo4j 동결로 빈 렌더.

**해결**: 프론트 경로 순서 정합(`/chainsight/${symbol}/ego/` → `/chainsight/ego/${symbol}/`) + 시드 게이트 우회(PG ego 직행) + `contracts/` OpenAPI에 ego 경로 명시(드리프트 재발 방지). **교훈**: API green·단위테스트 green ≠ 화면 작동. [[feedback_ui_slice_live_screenshot]] 규약(라이브 렌더 확인 전 완료 아님)의 실증 사례 — focus→ego 라이브 검증 누락으로 URL 불일치가 배포까지 이월. 상세=`docs/chain_sight/ego_render_diag_2026-07-16/REPORT.md`.

## [잡음 차단] pre-commit iCloud 경고는 무해·비차단 — 판단 소모 금지 [ops]

**증상**: 커밋 시 pre-commit hook이 "iCloud 측 작업 의심. 확인 후 진행하세요 (강제 차단 아님)" stderr 출력.

**해결**: **비차단 경고** — 커밋은 정상 통과한다. iCloud sync는 OFF 상태([[project_icloud_sync_off]])라 오탐. 이 경고에 판단·조사 소모하지 말고 커밋 결과(`✅ pre-commit 검증 통과`)만 확인하고 진행.

## FE↔BE URL 계약은 계약 테스트로 못박아라 — 미검증 이월 방지 (#58, 2026-07-17 ⑳-E) [frontend] [process]

**증상**: FE가 부르는 API 경로와 BE 라우트가 어긋나 404인데도 API green·단위테스트 green으로 통과, 실화면 미검증으로 배포까지 이월(#57 ego a9256b8부터 404).

**원인**: FE URL을 인라인 문자열로 산재 하드코딩 → BE가 라우트를 옮겨도(예: `<sym>/ego/`→`ego/<sym>/`) FE 미추종. 두 진영이 서로의 계약을 강제하는 테스트가 없음.

**해결**: ⑴ FE URL은 **단일 상수/헬퍼**로 수렴(`chainsightPaths.ts::egoPath`). ⑵ **양측 계약 테스트 표준화**: FE(vitest)에서 헬퍼가 만드는 경로 문자열 검증 + BE(pytest)에서 **동일 경로가 해당 View로 resolve**하고 구 패턴은 `Resolver404`임을 검증. 하드코딩 경로 신설 = 계약 테스트 동반 필수. cf. [[feedback_ui_slice_live_screenshot]].

## 전 세션 STEP 0에 worktree 최신성(origin/main 대비) 확인 강제 (#59, 2026-07-17 ⑳-E) [process] [harness]

**증상**: 편집 worktree가 origin/main보다 수십~백 커밋 뒤(stale)인데 그 위에서 조사·구현 → 배포 실화면과 다른 코드를 봐 오진(⑳-D에서 worktree 102 커밋 stale, ego 신규 파일 부재를 못 보고 초기 탐색 2건 오판).

**해결**: **조사·구현 불문 모든 세션 STEP 0에 최신성 확인 강제** — `git fetch && git rev-list --left-right --count origin/main...HEAD`로 behind 기록. behind>0이면 브랜치를 `origin/main` 기준으로 새로 파거나 merge. 배포 실화면 판정은 반드시 origin/main 정합 트리에서. ⑳-E는 이 규칙 적용해 니어미스 회피(진입 시 behind 8 확인 후 origin/main에서 브랜치 생성).

## react-query 실패 쿼리가 fetchStatus='paused'에 갇혀 isError 미도달 → 에러 UI 미발화 (#60, 2026-07-17 ⑳-E 라이브) [frontend]

**증상**: API가 503을 정확히 반환하는데도 프론트 에러 상태 UI가 안 뜨고 조용한 빈 화면. react-query 캐시 실측 시 해당 쿼리 `status:'pending', fetchStatus:'paused', failureCount:1`.

**원인**: react-query `onlineManager`가 오프라인으로 오판(`navigator.onLine=true`인데도) → **첫 실패 후 retry 직전에 pause**. 성공 쿼리(첫 시도 성공)는 무영향, 실패 쿼리만 error 상태에 도달 못해 `isError`가 영영 false. `networkMode:'always'`만으로는 이 버전에서 retry-pause를 못 막음(쿼리 옵션엔 반영되나 여전히 paused).

**해결**: 에러 상태 UI가 필수인 쿼리(localhost API 등)는 **`retry:false`**(+`networkMode:'always'`)로 첫 실패를 즉시 error 확정 → 에러 패널 발화, 사용자 재시도는 "다시 시도" 버튼으로. 진단 팁: fiber에서 QueryClient 추출해 `getQueryCache().getAll()`의 `state.fetchStatus`를 실측(좌표·화면만 보면 "로딩 안 끝남"으로 오판). 발견 경로=라이브 검증(단위테스트 GREEN 통과, [[feedback_ui_slice_live_screenshot]]).

## 서빙 포트 기동 전 완전 정리 — 기존 리스너 kill → 45초+ 무respawn 확인 후 기동 (#61, 2026-07-18 FE-8000-PROD-APPLY) [ops]

**증상**: 새 서버(prod `next start`)를 기동했는데 **~34초 만에 사망**하고, 다른 프로세스(임시 `npm run dev`)가 그 포트(:3000)를 재점유. 화면은 뜨지만 의도한 모드/코드가 아님.

**원인**: 기동 시점에 **잔존 리스너(구 dev)가 살아있거나 곧 되살아나** 새 서버와 포트 경합 → 한쪽이 밀려 사망. supervisor(launchd KeepAlive) 유무를 확인하지 않고 기동하면 respawn과 충돌.

**해결**: 서빙 포트 기동 절차에 **완전 정리 단계**를 포함한다 — ⑴ `lsof -iTCP:<port> -sTCP:LISTEN`로 기존 리스너 kill → **리스너 0 확인** ⑵ **45초+ 무respawn 관측**(감독자 존재 시 되살아남 = 그 감독자를 먼저 처리/판단) ⑶ 그 후 신규 기동. **자기점검**: 기동 절차에 "리스너 0 확인" 단계가 포함됐는지. cf. WEB-RUNTIME-RUNBOOK §2, [[reference_worker_runtime_tree]].

## FE 배포는 재빌드 필수 — :3000이 prod 빌드(npm run start)면 sv sync만으론 미반영 (#62, 2026-07-20 ⑳-2) [frontend] [ops] [deploy]

**증상**: 프론트 코드 머지·`sv sync`(web 트리 re-detach) 후에도 :3000 화면이 구 코드 그대로. next dev로 착각해 핫리로드를 기대.

**원인**: sv-web-runtime :3000은 `npm run start` = **prod 빌드 서빙**(`.next` 정적 산출물). `sv sync`는 소스 트리만 origin/main으로 갱신할 뿐 **`.next`를 재생성하지 않음** → 서빙은 옛 빌드. next dev(핫리로드)와 다름.

**해결**: FE 변경 배포 = `sv sync` 후 **web 트리에서 `npm run build` → `npm run start` 재시작**([[reference_web_runtime_prod_build]]). 신규 컴포넌트·훅 옵션은 특히 재빌드 없이는 절대 반영 안 됨. 절차: 리스너 0 확인(#61) → build → start → :3000 200·신규 표식 grep 확인. cf. FE-SERVE-MODE-TIDY(격리 dev 서빙 도입 시 이 마찰 해소).

## 표시 필드 명명은 근원 필드의 의미 실측 후 — auto_now를 "최근 언급일"로 오라벨 (#63, 2026-07-21 ⑳-F/⑳-G) [frontend] [backend]

**증상**: ego 카드가 "최근 언급 N일" / 근거 뉴스일로 노출한 `last_mentioned`가 실제로는 관계가 마지막 뉴스에 언급된 날이 아님. SEC 공시 관계(evidence 0건)에 07-20 같은 날짜가 붙어 "근거 0건인데 최근 언급?" 모순으로 보임.

**원인**: `last_mentioned` ← `RelationConfidence.last_observed_at`인데 이 필드는 모델에서 **`auto_now=True`** = 행이 마지막 `save()`된 시각(배치 실행 시각)이지 뉴스 언급일이 아니다. 07-20/06-20 군집 = SEC 배치 vs peer 배치의 마지막 실행 시각 차이. ⑳-2 지시서가 근원 필드 의미를 실측하지 않고 표시 라벨("최근 언급일")을 명명한 결함.

**해결**: 표시 필드 명명 전 **근원 컬럼의 의미(auto_now/auto_now_add/파생/원값)를 실측**한다. ⑳-G에서 라벨을 "확인일"(last_observed_at 명시 필드)로 교정. 진짜 언급일이 필요하면 `CoMentionEdge.last_co_mention_date`(뉴스 실제 최종 동시출현일) 사용. 교훈: 카드 신뢰도 "전원 85"도 같은 뿌리 — 표시(연속 신뢰도)가 근원(tier 계단값)의 실체와 불일치. 진단 `docs/chain_sight/confidence_diag_2026-07-21/REPORT.md`.

## 서빙 프로세스 cwd 실측 도구 hang 시 HTTP BUILD_ID로 우회 (#64, 2026-07-22 ⑳-G STEP 0) [ops]

**증상**: ⑳-F Q4가 원본 리포 `frontend/.next`(05-24 빌드)를 서빙 트리로 보고 "지도 튜닝 미반영" 판정. 그러나 ⑳-2(07-21)는 배포·라이브 확인됨 → 05-24 빌드에 07-21 카드가 있을 수 없어 **서빙 트리가 원본 리포가 아닐 가능성**(부분 오측정).

**원인**: :3000 next-server의 실제 cwd 실측 도구(`lsof -p`, `psutil.Process().cwd()`, `curl`, `urllib`)가 이 환경(sandbox)에서 전부 hang. grep/find/파이프 계열도 동일 hang. worktree엔 `.next` 부재라 어느 트리가 서빙하는지 파일만으론 불확정.

**해결**: 서빙 빌드 판별은 ⑴ 배포 재빌드 후 **HTTP로 `_next/static/<BUILD_ID>/` 추출**(HTTP 응답 가능 시), ⑵ next-server 부모 스크립트/런타임 트리 문서([[reference_daphne_api_tree_sync_gap]], WEB-RUNTIME-RUNBOOK)로 트리 특정, ⑶ 어느 쪽이든 07-21 커밋 반영은 재빌드 필요(#62)이므로 배포 단계 재빌드로 실측 대체. 판별 미완 시 표시층 처치(오버레이)는 빌드 상태 무관하게 안전.
