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

## httpx는 Wikipedia 봇탐지에 UA 무관 403 → requests 사용 (#47) `[infra]` `[scraping]`

- **증상**: TH-6 유니버스 복구에서 Wikipedia "List of S&P 500 companies" 파싱 시 `httpx.get`이 **User-Agent를 브라우저형(Mozilla/5.0)으로 줘도 403 Forbidden**. 동일 URL·동일 UA를 `requests.get`으로 부르면 **200**(503행 정상).
- **원인**: Wikipedia 봇 탐지가 **httpx의 TLS 지문·헤더 순서(HTTP2 등)를 UA와 무관하게 차단**. UA 문자열만으로는 우회 불가.
- **해결**: 스크래핑성 GET은 `requests` 사용(httpx 아님) + 브라우저형 UA(`Mozilla/5.0 (compatible; ...)`). 정책 준수 식별자 포함. (`serverless_client.get_sp500_constituents` 2026-07-09.)
- **왜**: 프로젝트 공용 httpx 클라이언트(`self.client`)를 재사용하려는 유혹이 있으나, 외부 사이트 봇탐지 앞에선 requests가 더 관대. 실측 분기(httpx 403 / requests 200)로 확정 후 선택할 것 — UA만 바꿔 재시도 반복 금지.

## [게이트 재현성] 검증 산출 스크립트는 스크래치패드 금지 — 커밋 필수 (G2 dry-run, 2026-07-24) `[harness]`

- **증상**: TH-C3-LLM-DICT-1 쓰기1단 세션이 G2 게이트 목표치(92/19/0/0)를 `scratchpad/final_confirmed.py`로 산출했으나, 스크래치패드는 세션 종료 시 정리 → 스크립트 **소멸**. 다음 세션이 재개하려니 "이 숫자를 어떻게 냈나"의 절차·명령·산식이 어느 커밋에도 없어 **3f HALT**(즉석 발명 금지 조건에 걸려 정지). 복원에 트랜스크립트 포렌식 1세션 소요.
- **원인**: 판정·게이트를 만드는 코드가 `/private/tmp/.../scratchpad/`에만 존재. 재개점 노트엔 결과 수치만 있고 산출 하네스가 repo 밖 → 재현 불가.
- **규칙**: **게이트·판정·검산의 산출 로직은 스크래치패드가 아니라 repo 관리 명령/서비스로 커밋**한다(`apps/*/management/commands/` + 순수함수 서비스). 일회성 탐색은 스크래치패드 OK지만, **결과가 재개점·승인 근거가 되는 순간 커밋 대상**. 재개점 노트엔 "목표 92/19/0/0"이 아니라 "`manage.py g2_dry_run --date-cut ...`로 재현"을 적는다.
- **왜**: 하네스 원칙(Agent=Model+Harness)에서 검증은 인프라다. 인프라가 휘발성 임시본이면 다음 세션은 그것을 신뢰도 재현도 못 해 정지한다. "산출 스크립트 = 커밋" = 게이트의 재현성 보장.

## [기준선 함정] 살아있는 테이블에 정적 행수 기준 금지 — 기준일 스코프로 못박아라 (G2 dry-run, 2026-07-24) `[harness]` `[testing]`

- **증상**: G2 dry-run 재개점 노트가 "코퍼스 동결 ≤07-11 전제"를 적었으나 `DailyNewsKeyword`는 매일 유입(07-24 현재 최신)이라, 아무 필터 없이 재집계하면 동결 시점과 **다른 값**이 나온다. "왜 92/19가 재현 안 되지"의 원천이 될 뻔.
- **원인**: 검산 기준을 "테이블 전체"로 잡으면 그 테이블이 증가형(append-only 원장)일 때 시점마다 답이 달라진다. 정적 스냅샷처럼 취급한 게 오류.
- **규칙**: 증가형 테이블(`DailyNewsKeyword`·`ThemeNewsVolume`·`EstimateSnapshot` 등) 위 검산·재현은 **반드시 `date__lte=<기준일>` 스코프**로 못박고, 산출 메타에 그 기준일을 출력한다(`g2_dry_run`은 `date_cut` + `corpus_days`/`corpus_term_hits`를 메타로 노출). 재현 명령에 기준일을 인자로 강제(`--date-cut`, 기본값 명시).
- **왜**: "동결 코퍼스"는 프로세스 규율이 아니라 **쿼리 스코프**로 강제해야 실효. 노트의 "동결 전제"는 다음 세션이 안 지키면 깨지지만, `date__lte` 필터는 코드가 지킨다. STEP 0에서 `date≤cut distinct 행수`를 실측 보고하는 것도 같은 이유.

## [세션 위치] 셸 기동 위치 ≠ 세션 worktree — STEP 0에서 원장 대조로 확정 (G2 dry-run, 2026-07-24) `[harness]`

- **증상**: `manage.py shell` 실행 시 cwd/트리에 따라 다른 코드·다른 DB를 볼 수 있음. TH 트랙은 `~/worktrees/sv-theme-heat`(브랜치 전용, 미머지 WIP)에서만 `ThemeTermOverride`·마이그 0024가 존재 — 공유 트리 `Desktop/stock_vis`에서 돌리면 모델 부재로 오판. 실제로 `get_model('chain_sight',...)`가 앱 라벨 불일치로 실패하거나, `apps.news` 부재(monorepo는 `services.news`) 등 트리별 차이가 드러남.
- **원인**: 세션이 여러 worktree를 오가며 작업하는데, 셸 명령의 실행 위치(cwd + venv + DJANGO_SETTINGS_MODULE)를 확정하지 않으면 "어느 코드·어느 원장을 보는가"가 모호.
- **규칙**: **STEP 0에서 실행 위치를 원장 대조로 확정**한다 — `git -C <worktree> rev-parse HEAD`(코드 버전) + 핵심 테이블 실측 행수(예 `ThemeTermOverride 215`)로 "이 트리가 맞다"를 증명한 뒤 작업. 명령은 절대경로 worktree + 명시 venv + `DJANGO_SETTINGS_MODULE`로 고정(`cd ~/worktrees/sv-theme-heat && ... "$VENV/bin/python" manage.py ...`).
- **왜**: 다중 worktree 환경에서 "지금 어디서 도는가"는 암묵이 아니라 실측이어야 한다. HEAD 해시 + 원장 행수 대조 = 위치의 유일한 진실. 위치를 틀리면 무쓰기 프로브조차 엉뚱한 트리를 읽어 잘못된 결론을 낸다.
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

**C-L3 구현 실측 반전(2026-07-24, D-CL3-ARCHIVE-BLIND)**: 착수 시 실측 = 과거분(2023-08·2024-05·2025-11)이 **현재 대부분 `is_archived=False`**(archive_old_articles가 아직 미실행). 즉 지금은 필터해도 안 걸리지만, **미래 아카이브 시 벙어리화**가 진짜 위험. → `grounding.fetch_day_candidates`는 is_archived로 **필터하지 않음**(True/False 무관). 회귀 테스트 `test_fetch_includes_archived_articles`가 is_archived=True 행 포함을 명시 단언(미래 아카이브 대비 잠금). 원지시서의 "is_archived=True 포함 필수"는 방향이 "True를 잃지 말라"는 뜻으로, 실제 구현 = **무필터**가 정답.

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

**보충(2026-07-27, MGMT-BATCH-14)**: 금지 대상은 **내용 열람·출력·복사**뿐이다. 신규 worktree에서 Django/Next 런타임 구동을 위한 **.env 심링크 생성·연결(`ln -sf …/stock_vis/.env <worktree>/.env`)은 허용** — 심링크는 파일 내용을 열지 않고 로더 경로만 잇는다(gitignore로 추적 제외 확인 필수). 선례: `sess-cov-c1-api`(실 API 조인 실측)·`sess-cov-c1-fe`가 실 응답 타이핑을 위해 심링크 동반. 즉 "미개봉"은 **byte 열람 금지**이지 **경로 연결 금지가 아니다**.

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

**종결(2026-07-24, ⑳-G 배포 실증)**: ⑳-G FE를 `~/worktrees/sv-web-runtime/frontend`에서 재빌드→`npm run start`→⑳-G 등급 배지·카드 섹션 변경이 :3000 라이브 반영(S5 4종 사용자 확인·`curl 200`). **∴ 서빙 트리 = sv-web-runtime 확정**(원본 공유 리포 아님). 공유 리포 `.next`의 05-24 BUILD_ID(Dwq0DX9…)는 **미서빙 트리의 잔재**로 확정 = ⑳-F Q4 "지도 튜닝 미반영" 판정은 **원본리포 오측정**(부분 오측정→확정). 논리 결론이 실증으로 봉인됨. **측정 경로 대조 교훈**: 서빙 판별의 최종 실측은 "파일 BUILD_ID"가 아니라 **배포 재빌드가 라이브에 반영되는가**(BUILD_ID는 트리 특정 후에만 의미). cf. [[reference_web_runtime_prod_build]].

## refresh beat의 scenario 처리가 kwargs 오타로 전건 무발화 — try/except 밖 TypeError (#65, 2026-07-21 HOLD-P1 STEP 0) [backend] [monitor]

**증상**: monitor 가격 시나리오의 `last_price_zone`이 생성 후 며칠이 지나도 **전부 None**, 전이 알림도 무발화. RECON은 "refresh beat가 아직 안 돎"으로 오해석하기 쉬움(실제론 매 beat 크래시).

**원인**: `pipeline.py::refresh_monitor`가 `process_monitor_scenarios(monitor, as_of_date=as_of)`로 호출하나 함수 시그니처는 `process_monitor_scenarios(monitor, as_of=None)` — 키워드 인자명 불일치로 **`TypeError: unexpected keyword argument 'as_of_date'`**. 이 호출은 evaluate 격리용 try/except **밖**에 있어(그 try/except는 evaluate_monitor 전용) 예외가 refresh_monitor 전체를 중단시킴 → scenario_events 미생성, zone 저장 영영 안 됨. 단위테스트는 digest를 수동 events로만 검증해 이 경로를 커버 안 함(미검출 잠복).

**해결**: 호출부를 `process_monitor_scenarios(monitor, as_of=as_of)`로 교정. **교훈**: ⑴ 파이프라인 통합 지점의 kwargs는 시그니처 대조 필수(테스트가 서비스 함수를 직접 호출·수동 events만 쓰면 통합 경로가 잠복). ⑵ "관측값이 계속 None" = "아직 안 돎"이 아니라 "매번 조용히 실패" 가능성을 먼저 의심. [[feedback_ui_slice_live_screenshot]]와 동류 — green ≠ 통합 경로 작동.

## 배포 실물은 서빙/공유 트리 디스크가 아니라 `git show origin/main:<path>`로 추출 — 세션 트리 산출물은 뒤처질 수 있다 (#66, 2026-07-24 LAUNCHD-WEB-PLIST-LOAD) [ops] [deploy]

**증상**: plist load 집행 시 서빙 세션트리(`Desktop/stock_vis` @ `sess-hold-p1`, base `6973bda`)의 디스크 plist `docs/operations/com.stockvis.web-frontend.plist`가 **교정 전 초안**(`/bin/bash -lc … npm run start`)이었다. 그대로 `cp ~/Library/LaunchAgents`로 설치했다면 로그인셸 npm=`/usr/local/bin/npm`(node v20.11.0) 오해석 버그(OPS-PLIST-FIX가 고친 바로 그 결함)가 재현될 뻔했다.

**원인**: 배포 대상 파일은 origin/main `9f2e6c5`(OPS-PLIST-FIX `56251a9`)에서 교정됐으나, 집행 세션이 그 머지보다 **이전 base**의 브랜치(`sess-hold-p1` base `6973bda`)에 체크아웃돼 있어 디스크 산출물이 구본이었다. 공유/세션 트리의 디스크 상태는 "현재 체크아웃된 브랜치"에 종속 = origin/main 최신과 무관하게 뒤처질 수 있다.

**해결**: **배포 실물(plist·설정 파일·스크립트 등)은 디스크 cp가 아니라 `git show origin/main:<path>`로 추출**해 배치한다. 근본: "무엇이 배포돼 있는가(origin/main)"와 "무엇이 현 트리에 있는가(체크아웃 브랜치)"를 분리 사고. cf. #64(서빙 빌드 판별=HTTP BUILD_ID)·[[reference_web_runtime_prod_build]]와 동류 — 트리 파일만으론 배포 실체 불확정. 실측: 배치 전 `plutil -lint` + `PlistBuddy -c "Print :ProgramArguments"`로 교정본 확인 필수.

## 라이브 자동화 배치는 origin/main 추적 트리만 참조 — 공유 세션 트리를 읽으면 체크아웃 브랜치 따라 배포 drift (#67, 2026-07-24~28 OPS-VERIFY-EXEC-TREE) [ops] [deploy]

**증상**: verify launchd(`com.stockvis.verify-pair`, 02:30)의 section D(Phase 3 파수꾼)가 origin/main에 배선(`b76d9ab`)됐는데도 라이브 02:30 로그에 **section D가 전무**. "코드 착지=라이브 발현"으로 오판하기 쉬움(07-20 "라이브 PASS"는 실은 dev 트리 관찰이었음).

**원인**: verify 래퍼 `scripts/verify-pair.sh`가 `PROJECT_DIR="…/Desktop/stock_vis"`(공유 세션 트리)를 **하드코딩+`cd`** → 그 트리의 체크아웃 브랜치(`sess-hold-p1`, `b76d9ab` 미포함)를 실행. 공유트리엔 `ops_verify_checks.py` 파일 자체가 없어 section D 없는 구버전 py를 돌렸다. 라이브 자동화가 "현재 체크아웃된 브랜치에 종속되는 공유 편집 트리"를 읽으면, origin/main에 무엇이 있든 실행물은 그 트리의 브랜치를 따른다(#66과 동류 — 읽기 접촉판).

**해결**: **라이브 자동화 배치(launchd·cron)는 origin/main 추적 트리(런타임/전용 트리)만 참조**한다. 래퍼는 `PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`로 **self-locate** → plist가 지향한 트리의 코드를 돈다. 브랜치별 cherry-pick은 수리 아님(drift 재발) — 배치 자체를 교정. **"무접촉" 주장 시 읽기/쓰기 구분 필수**: verify의 `cd`+실행은 쓰기가 아니어도 읽기 접촉이므로 공유트리 브랜치에 종속된다(놓치기 쉬움). cf. `sv sync`/`sv`(D-SYNC-ENTRYPOINT)가 스크립트 진입점을 origin/main 트리로 고정하는 것과 동일 원리.

## 지시서는 repo 커밋이 0번째 게이트 — 미커밋 지시서는 소비 불가, 발행 시점 보존 (#68, 2026-07-24~28 OPS-ISO 트랙) [harness]

**증상**: 실행 지시서(`*_directive.md`)를 대화/디스크에만 두고 소비하면, 소비 근거·발행 시점·개정 이력이 휘발돼 사후 추적 불가. 승인 스펙이 물리적으로 불가한 지점을 발견해도(예: plist-only repoint) 원 지시서와 개정문의 관계가 남지 않는다.

**원인**: 지시서는 휘발성이라 repo에 보관 안 하는 관행이었으나, 소비(집행) 전 커밋을 강제하지 않으면 "무엇을 근거로 무엇을 했는가"의 계보가 끊긴다.

**해결**: **지시서 소비의 0번째 게이트 = 해당 파일이 `docs/instructions/`에 커밋돼 있을 것.** 원 지시서는 **수정하지 않고**(발행 시점 보존), 스펙 변경·불가 발견은 **개정문(`*_amendment*.md`)을 별도 커밋**으로 쌓는다(원본 불변, 개정 계보 누적). 세션 종료 전 CLAUDE.md Harness Protocol의 "지시서 폐기 전 흡수 확인"(비자명 결정의 '왜'가 DECISIONS에 흡수·task ID 추적)과 병행. 실측 사례: OPS-VERIFY-EXEC-TREE = 원 지시서(`b8d767aa`) + 개정문1(self-locate, origin/main) + 개정문2(야간 번들) 3층 계보.

## PROGRESS 72h 위생 검사는 세션 종류 불문 FAIL — build 사이클이 72h 넘길 전망이면 mgmt 배치를 LAND보다 선행한다 (#69, 2026-07-27 C1-FE-LAND HALT) [harness] [process]

**증상**: `health_check.py`의 "origin/main 해시" 검사(PROGRESS.md 마지막 갱신 age 기반)가 **73.9h > 임계 72h**로 ❌FAIL 트립. C1-FE-LAND(merge 세션)의 pre-merge 게이트가 "FAIL만 HALT"에 걸려 정당 HALT — merge는 메타 4종 무변경이라 PROGRESS를 못 고쳐 자체 해소 불가.

**원인**: 72h 검사는 세션 종류(merge/build/mgmt)를 구분하지 않는다. build→build→LAND로 이어지는 사이클이 길어지면 그 사이 PROGRESS가 갱신 안 돼 LAND 시점에 임계를 넘긴다. merge 세션은 PROGRESS 쓰기 권한이 없어(구획 밖) 스스로 못 푼다 = 구조적 교착.

**해결**: **build 사이클이 72h를 넘길 전망이면 mgmt 장부 배치를 LAND보다 선행 배치**한다(PROGRESS 갱신으로 72h 리셋 후 LAND). 실측: 2026-07-27 C1-FE-LAND HALT → MGMT-BATCH-14 선행(이 배치) → PROGRESS 갱신으로 FAIL 소멸 → LAND 재개. 후속 검토(등재만): `HEALTH-72H-SEVERITY-SPLIT`(TASKQUEUE) — 72h severity를 세션 종류별 분리(merge=WARN/mgmt=FAIL)할지. cf. #47(실행트리 정합=transient WARN)과 달리 72h는 시간 경과라 머지로 안 풀림.

## 표면별 서빙 경로 분기 — ego 복구가 한 표면만 전환, 나머지 이월 누락 (#70a, 2026-07-28 ⑳-3 S1) [frontend] [chainsight]
*(채번 충돌로 구분자 부가, D-NUMBERING-DUP 참조. 기존 '#70' 단독 인용은 문맥상 해당 내용 쪽. a=선착지 92994048 15:30)*

**증상**: ⑳-E가 ego 동선(market-graph 표면)을 PG로 복구했으나, 같은 "종목 관계 그래프"를 그리는 **다른 표면**(`/chainsight/[symbol]` 전용 워크스페이스 · `stocks/[symbol]` GraphMiniView)은 여전히 레거시 Neo4j `/graph/`·`/suggestions/`를 호출 → Neo4j 동결로 전 심볼 500 → "데이터가 없습니다"·"카테고리 없음". 데이터(RelationConfidence)는 PG에 실재(HAL 39엣지)하는데도 표면이 죽어 보임.

**원인**: 같은 도메인 데이터를 **복수 표면이 서로 다른 서빙 경로**(PG ego vs 레거시 Neo4j)로 소비. 한 표면만 전환하면 나머지는 조용히 구경로에 남아 이월 누락. FE는 500/에러를 무데이터로 뭉뚱그려 표시(에러≠무데이터 정직성 부재).

**해결**: ⑴ 도메인 데이터의 **표면 인벤토리**를 만들고(소비 훅·엔드포인트 grep), 경로 전환 시 **전 소비자 일괄** 전환(STEP 0-B의 소비자 전수 검색이 GraphMiniView 제2소비자를 발견 = 누락 방지). ⑵ 어댑터를 **단일 순수함수로 공유**(`egoToGraphResponse` — 표면별 복제 금지). ⑶ FE는 로딩/오류(준비 중)/데이터 **3상태 분리**. cf. #64(서빙 경로 실측), DECISIONS D-GRAPH-EGO-BACKEND(ego=PG)·D-20-3-LEGACY-CONSUMER-MIGRATION.
## pytest default maxfail 조기정지는 부분 실패 수를 전체로 오인시킨다 — 실패 수 인용 전 전수 실행으로 확정 (#70b, 2026-07-28 SEC β 킥오프) [testing] [process]
*(채번 충돌로 구분자 부가, D-NUMBERING-DUP 참조. 기존 '#70' 단독 인용은 문맥상 해당 내용 쪽. b=후착지 9b0d89cd 16:08)*

**증상**: SEC β 킥오프 STEP 0에서 전스위트를 `pytest -q`로 돌리자 "**5 failed, 29 passed**"로 종료 — 이를 "실패 5건"으로 인용하려던 순간, 다른 실행에서는 "**13 failed, 4050 passed**"가 나와 모순 발생. 부분 census를 전체로 오인할 뻔함.

**원인**: 이 repo의 pytest addopts에 **`--maxfail=5`(또는 `-x` 계열)**가 설정돼 있어, 5번째 실패에서 **조기 정지**한다(34개만 실행하고 멈춤). 알파벳 순서상 `tests/chainsight/test_attention.py`가 앞이라 그 5개 실패에서 즉시 정지 → 전체 4116개 중 34개만 본 부분 결과를 "전체 실패 수"로 오인.

**해결**: **실패 수를 보고·인용하기 전에 전수 실행으로 확정**한다 — `--maxfail=60`(임계 상향) 또는 `--maxfail=0`(해제)로 재실행. 교차검증: 알려진 사전존재 파일만 따로 `--maxfail` 상향 실행해 그 합이 full census 총수와 일치하는지 확인(07-28: attention 6 + leadership 7 = 13 = full census 13 → 신규 0 확정). 부수: `-q` 리다이렉트 시 `\r` 진행표시가 FAILED 목록을 덮으므로 `tr '\r' '\n'` 후 grep. "N failed"만 보고 세부 노드를 안 세면 조기정지 여부를 놓친다.

> ⚠ **채번 충돌 관측(MGMT-BATCH-15, 2026-07-28)**: 위 두 항목(⑳-3 S1 · SEC β 킥오프)이 병렬 세션에서 **둘 다 `#70`을 부여**함(채번 실측+1 규율 #44 미준수 선례 — 각 세션이 상대의 등재를 못 보고 동시 채번). 소급 재번호는 참조 깨짐 위험이라 **보류**(둘 다 `#70`으로 존치), 신규 채번은 **#71부터** 이어간다. 재발 방지 = 채번 직전 `grep -oE '\(#[0-9]+' | sort -n | tail`로 최댓값 실측(헤딩·본문 구분).

## 표면 배선(스트립·위젯·훅) 지시서는 소유권 글롭이 아니라 라우트 실주소(파일+URL)를 명시 — 글롭만 믿으면 레거시에 착지 (#71b, 2026-07-28 DASH-SURFACE-SPLIT-SURVEY) [frontend] [process]
*(채번 충돌로 구분자 부가, D-NUMBERING-DUP 참조. 기존 '#71' 단독 인용은 문맥상 해당 내용 쪽. b=후착지 04f943f3 17:05 MGMT-BATCH-15)*

**증상**: P2-COVERAGE-C1-FE가 `CoverageStrip`을 `app/dashboard/page.tsx`(2025-11 방치 레거시, 네비 도달 경로 0·impression 계측 0)에 배선. 정작 실 대시보드는 루트 `/`(`app/page.tsx`, impression 실데이터 44행 전량 발생지)라, 스트립이 **사용자가 도달하지 않는 표면**에 놓여 사실상 비노출(07-28 SURVEY로 발견).

**원인**: 디렉터 지시서가 "dashboard 구획"만 명시하고 **라우트 실주소(파일 경로 + 실제 URL)를 미명시**. 실행자가 소유권 지도 글롭 `app/dashboard/**`를 문자 그대로 해석해 동명 레거시 파일에 배선. 표면 관련 기존 결정(D-OWN-HOME=실 랜딩은 `app/page.tsx`)을 교차 확인하지 않음.

**해결**: **표면 배선(스트립·위젯·훅 부착) 지시서는 라우트 실주소를 명시**한다 — "`app/page.tsx`(URL `/`) L1.5 위치" 처럼 파일+URL+삽입 지점. 글롭 `app/dashboard/**`는 소유권(누가 고치나)이지 배선처(어디에 렌더되나)가 아니다. 지시서 작성 시 **표면 관련 기존 결정 교차 확인 필수**(D-OWN-HOME·소유권 지도 AMEND 등). cf. 동명 파일 함정 — `app/page.tsx`(실 랜딩) vs `app/dashboard/page.tsx`(레거시)가 둘 다 "대시보드"라 불려 혼동. 교정 = D-DASH-SURFACE-UNIFY(스트립 `/`로 이동 + `/dashboard`→`/` redirect).

## launchd 검증 PASS는 스냅샷 — orphan이 포트 선점하면 조용히 crash loop("재빌드 미반영" 증상) (#72b, 2026-07-24~27 web-frontend) [ops] [deploy]
*(채번 충돌로 구분자 부가, D-NUMBERING-DUP 참조. 기존 '#72' 단독 인용은 문맥상 해당 내용 쪽. b=후착지 04f943f3 17:05 MGMT-BATCH-15)*

**증상**: `/dashboard/coverage` 신규 라우트를 재빌드했는데 라이브가 404. `com.stockvis.web-frontend` launchd job은 07-24 load 때 "검증 3종 PASS"였으나, 07-27 재빌드가 라이브에 반영 안 됨. 실제로는 job이 **`runs=34,664`회 EADDRINUSE crash loop**(약 4일), 실서빙은 job 밖 orphan(PID 36207 npm, 07-24 11:32~ + 자식 next-server, **구 빌드 ca062581** 고착)이 수행 중이었다.

**원인**: launchd 승격 "검증 PASS"는 그 순간의 스냅샷일 뿐. 07-24 load 직후 별도 프로세스(orphan)가 :3000을 선점하자, launchd job은 새 프로세스 기동마다 `EADDRINUSE`로 exit 1 → ThrottleInterval(10s) 재시도를 4일간 반복(좀비 loop). 포트는 orphan이 물고 있어 서빙은 계속되지만 코드는 07-24 시점 빌드에 고착. `kickstart -k`도 orphan 앞에선 무효(EADDRINUSE 지속).

**해결**: 검출 = `launchctl print gui/$(id -u)/<label>`의 **`runs` 폭증 + `last exit code=1`** + 실서빙 PID의 **cwd·ppid 대조**(`lsof -a -p <pid> -d cwd`, `ps -o ppid`)로 job 밖 orphan 판별. 해소 = **#61 orphan 정리**(`kill -TERM <npm 부모 pid>` → 자식 전파) → KeepAlive가 즉시 :3000 탈환(새 빌드 로드). 재발 방지 = 배포 후 `runs` 카운터 불변 + `/신규라우트` 200 확인. launchd 승격 직후엔 orphan 잔존 여부를 반드시 `lsof :3000` PID의 ppid로 확정(launchd 직속 아니면 orphan). cf. [[reference_web_runtime_prod_build]] · TASKQUEUE `HEALTH-LAUNCHD-LOOP-CHECK`(자동 검출 검토).
## 레거시 에러(500)를 "없음"으로 오번역 — 3상태 정직화가 소진 순서 (#71a, 2026-07-28 ⑳-3 S2) [frontend] [chainsight]
*(채번 충돌로 구분자 부가, D-NUMBERING-DUP 참조. 기존 '#71' 단독 인용은 문맥상 해당 내용 쪽. a=선착지 b53e78f2 16:55)*

**증상**: 죽은 레거시 Neo4j 엔드포인트의 500을 FE가 "데이터 없음"류로 오번역. 실측 2사례: ⑴ AIGuidePanel suggestions 500 → "탐색 가능한 카테고리가 없습니다"(S1) ⑵ Chain Trace 500 → "경로 없음"(NVDA→MPWR가 실제 직접 이웃인데 "경로 없음"으로 표시). 기능 미비/서버 오류인데 사용자에겐 "빈 결과·관계 없음"으로 읽혀 오해.

**원인**: FE가 **error와 empty를 한 갈래로 렌더**. 레거시 표면이 통째로 죽어있으면(Neo4j 동결) 모든 조회가 조용히 "없음"처럼 보인다. 데이터(RC)가 PG에 실재해도 화면은 "관계 없음".

**해결**: **로딩 / 오류(준비 중) / 데이터 3상태 분리** + 죽은 레거시는 아예 미호출. trace는 traceTarget 미설정 → `useTrace(enabled:!!from&&!!to)` 자연 비발화(0 호출). "준비 중"으로 정직 표시(에러≠무데이터). 순서: 소비자 전환(#70) → 잔여 레거시 표면 3상태화 → 레거시 제거. cf. #70(표면별 서빙경로 분기), D-REL-QUALIFICATION.
## [드리프트] 백필 창 보정 논리가 창 뒷날을 삼킴 — EARLIEST + limit cap → 표적 1일 창으로 회피 (#72a, C-N-REPAIR 2026-07-28)
*(채번 충돌로 구분자 부가, D-NUMBERING-DUP 참조. 기존 '#72' 단독 인용은 문맥상 해당 내용 쪽. a=선착지 d5614c68 10:40)*

**증상**: broad 뉴스 백필(7일 창·EARLIEST 정렬·1000행 cap)이 "122/122 창 완료" 후에도 커버 구간 내 **154일 0건**. 요일 편중(금 65·목 47·수 30·화 12) = 고볼륨 창의 뒷날들이 통째로 누락. 하류 C-L3 생성이 그 154일 null(빈약 맥락).

**원인**: 고볼륨 7일 창에서 EARLIEST 정렬이 앞날부터 1000행 cap을 소진 → 창 뒷날(주 후반)이 AV 응답에 안 담김. "다음 창이 보정한다"는 논리는 **비중첩 연속 창에서 성립하지 않음**(각 7일 창 독립 — 다음 창은 다음 7일이라 이번 창 뒷날을 채우지 않음). + "표본 2창 확인"을 683 전체로 일반화한 오류(→ D-CN-COMPLETE 판정 폐기).

**해결**: 표적 재수집 = **누락일만 명시하는 1일 독립 창**(`backfill_broad_news --dates D1,D2,… --window-days 1`, --dates는 가산 옵션) — 창당 1일이라 cap이 삼킬 뒷날 자체가 없음. 주말·공휴일 낭비 0(거래일만 명시). 완료 판정은 "창 완료"가 아니라 **일 단위 존재 검증**(각 날 `published_at__date` >0). cf. D-CN-COMPLETE 폐기·D-CN-REPAIR-* (2026-07-28).

## [드리프트] 무인 배치 순번을 "경과일 산술"로 계산 → 시작일≠실행일이면 첫 배치 영구 스킵 — 체크포인트 카운터로 회피 (#73, C-N-REPAIR 자동화 2026-07-29)

**증상**: 다일 배치(N일에 걸쳐 하루 1개)를 무인 스케줄러로 돌릴 때, 순번을 `batch_no = (오늘 − 시작일) + 1`로 계산하면 **시작일에 실제로 batch1을 안 돌렸는데 다음 날부터 자동화를 켜는 순간 batch1이 영구 누락**됨. 실측: 시작일 07-28, 활성화 07-29 → 경과일1 → "경과일+1"=batch2로 점프, batch1(07-28분) 미수집 방치.

**원인**: 캘린더 산술은 "매일 빠짐없이 돌았다"를 전제로 순번을 파생 → 실제 실행 이력과 결합되지 않음. 하루라도 건너뛰거나 시작이 지연되면 그만큼 앞 배치가 스킵된다.

**해결**: **체크포인트 카운터** — `status.json.next_batch`를 **성공 시에만 전진**시키고 실행 이력(saved/updated/exit/status)을 함께 기록. 실패·이상(0건)은 전진 보류 → 다음 실행이 같은 배치 재시도(누락 0). `max(next_batch, batch+1)`로 재실행 역행 방지. 멱등 수집(url upsert + skip-covered)이면 재실행도 무해. cf. D-CN-REPAIR-AUTO-CHECKPOINT (2026-07-29), `scripts/cn_repair_status.py`.
## health_check 결과 보고 시 측정 트리(브랜치·HEAD) 병기 필수 — 옛 worktree 결과를 origin/main 상태로 오인 (#74, 2026-07-29 MP-UNIFY 착지) [harness] [process]

**증상**: MP-UNIFY-1 착지 검증에서 health_check가 `❌ PROGRESS.md 180.9h stale`를 보고 → "origin/main에 방치 ❌ 있음, mgmt 배치 필요"로 오판. 실제 origin/main은 처음부터 `❌0`이었음(오보).

**원인**: health_check를 **옛 worktree(`sess-hold-p1`, HEAD `b8d767a`, 07-21 stamp)**에서 실행. 이 트리는 07-28 원장 리프레시(MGMT-BATCH-15 등) 이전 상태를 담고 있어, health의 "PROGRESS staleness"가 **그 트리 로컬 조건**을 잰 것. origin/main(`f7f3f63d`↑)에서 재실행하면 `❌0`. health 출력에 측정 트리가 안 적히면 "옛 트리 로컬 결함"이 "canonical(origin/main) 결함"으로 승격 오인된다.

**해결**: **health_check 결과를 보고·판단에 쓸 때 측정 트리(worktree 경로 + 브랜치 + HEAD hash)를 반드시 병기**한다. staleness·정합 계열 ❌/WARN은 origin/main 추적 트리(또는 origin/main 기준 worktree)에서 재확인 후 판정. mgmt 배치 범위를 ❌ 근거로 잡기 전 "그 ❌가 canonical 트리에도 있나?"를 먼저 검증. cf. `scripts/health_check.py` 항목 `실행 트리 정합`(HEAD≠origin/main WARN)이 이미 신호이나, 보고 습관으로 못박음.

## 짧은 심볼 substring 매칭이 단어 속 우연 문자에 오탐 → 무근거 auto 승격 (#75, ⑳-3 S2-C 2026-07-30) [chainsight] [validation]

**증상**: 관계 도메인 태깅 `machine_check`의 타깃 실존 판정 `other.lower() in basis`가 짧은 심볼(V=Visa, A=Agilent, MA, CO 등)을 단어 속 우연 문자에 매칭(V∈"over/value", A∈"and")해 `target_in_basis=True` → conf만 높으면 auto_candidate로 승격. CSV 재분류상 이런 오탐 auto 5건 실측(CPAY↔V 등).

**원인**: 심볼 substring 매칭에 길이·경계 가드 부재. 사명 토큰만 `len≥4` 가드가 있고 심볼은 무가드 → 1~3자 심볼이 거의 모든 basis에 우연 매칭. 근거(grounding) 검증의 취지(타깃이 evidence에 실존)가 무력화.

**해결**: 심볼은 단어경계(`\bSYM\b`)로만 매칭, 사명은 유의어 토큰(≥4자)을 나열 구분자(`;,:()"'&/`)까지 분해해 매칭. 이러면 "Halliburton"→HAL은 **사명 경로로 복구**(단어경계 심볼은 실패해도), "over"의 v는 배제. 오탐 방지 테스트 필수(나열 아닌 문장의 우연 매칭이 auto 승격 안 되는지). cf. `apps/chain_sight/services/domain_tagging.py` machine_check(S2-C-2), D-REL-DIRECTION-CONVENTION.

## 저장 CSV 재분류는 이름 의존 룰을 재현 못 함 — dry-run 효과 0을 "룰 무효"로 오해 금지 (#76, ⑳-3 S2-C 2026-07-30) [chainsight] [process]

**증상**: 캘리브레이션 CSV(review_batch.csv)로 gate v2 재분류 dry-run 시, target 재판정 룰(S2-C-2)의 효과가 0으로 나옴 → "룰이 무의미"로 오판할 뻔.

**원인**: CSV는 basis 원문은 전량 담아도(≤110자, 캡 내) **stock_name 컬럼이 없음**. machine_check의 타깃 실존은 심볼+사명 둘 다 쓰는데, CSV엔 사명이 없어 이름 경로를 재현 불가 → 이름 의존 룰의 dry-run 델타가 구조적으로 0. 이름 독립 룰(자가모순 필터)만 CSV로 측정 가능.

**해결**: 재분류 dry-run에서 룰을 **이름 독립/의존으로 분류**하고, 이름 의존 룰은 "CSV 재현 불가, 코어 단위테스트로 검증·차기 라이브 배치에서 실효 확인"으로 명시. 효과 0을 룰 무효로 결론짓지 말 것. 필요하면 CSV 산출 시 target_name 컬럼을 추가(향후). cf. `reclassify_domain_batch` 커맨드 docstring, reclassify_v2_analysis.md.

## 동결된 임계가 지배 블로커면 게이트 룰 튜닝이 검수 volume을 못 줄인다 (#77, ⑳-3 S2-C 2026-07-30) [chainsight] [process]

**증상**: 자가모순 필터·나열 인식 등 gate 룰 튜닝을 넣었는데 B'(개별 검수) 감축 미달(162>120 목표). 룰은 review "성격"만 정정(타입변경 오인 119→진짜 66)하고 검수량은 거의 그대로.

**원인**: pending의 지배 블로커가 confidence 임계(0.75, 이번 스코프에서 동결)와 evidence 절단(100자 캡)이었음. 자가모순 53건 중 나머지 3검증 통과는 1건뿐, 52건은 conf<0.75로 재차 막힘. 룰 튜닝은 임계·evidence를 못 건드리니 volume 레버가 아님.

**해결**: "룰 개선 = 분류 정확도↑"와 "volume 감축"을 분리 판단. 감축 목표가 있으면 먼저 **지배 블로커를 실측**(블로커별 분해)하고, 그게 동결 임계·evidence면 룰 튜닝 대신 임계 재튜닝(분포 확보 후) 또는 evidence 재추출(EVIDENCE-CAP-REEXTRACT)을 레버로 지정. cf. reclassify_v2_analysis.md §3, TASKQUEUE EVIDENCE-CAP-REEXTRACT.

## heat/celery beat 로그는 stocks.log가 아니라 launchd StandardErrorPath에만 기록됨 — "로그 없음"을 "미실행"으로 오판 금지 (#78b, SEAL-PUSH-1b 2026-07-31) [ops] [chainsight] [process]
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. 기존 '#78' 단독 인용은 문맥상 해당 내용 쪽. b=착지 9540993a 2026-07-31 11:38)*

**증상**: 07-29 theme-heat-daily 실행 상세(섹터별 not_computed·미저장 사유)를 확인하려 `stocks.log`를 grep했으나 `heat`·`2026-07-29` 라인 **0건**. 미실행으로 오판할 뻔함(실제로는 09:57 정상 발화·저장 6행).

**원인**: chainsight heat 로거(`logger = logging.getLogger(__name__)`)의 출력은 celery worker 프로세스 stdout/stderr로 가고, celery는 launchd로 기동되므로 **`~/Library/Logs/stockvis/celery-worker-error.log`**(plist `StandardErrorPath`)에만 남는다. repo 루트 `stocks.log`는 Django dev-server(runserver) 경로용이라 beat/worker 실행 로그가 없다. 심지어 worker **런타임 트리**(`~/worktrees/sv-worker-runtime/stocks.log`)에도 heat 라인은 없음(FileHandler 미배선).

**해결**: beat/worker 태스크 로그를 찾을 땐 **launchd plist의 `StandardOutPath`/`StandardErrorPath`를 먼저 확인**(`grep -A1 StandardErrorPath ~/Library/LaunchAgents/com.stockvis.celery-*.plist`) → 해당 파일을 grep. heat 계열 = `celery-worker-error.log`. "stocks.log에 없음 = 미실행" 추론 금지. cf. [[reference_worker_runtime_tree]] · plist 목록 `com.stockvis.celery-{worker,worker-neo4j,beat}.plist`.
## 화면 ✓ ≠ DB 영속 — 상태 생성 UI 체크는 확인 쿼리 동반 필수 (#78a, 20b-f2 GOAL-CREATE-UI 2026-07-31) [portfolio][coach][process]
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. 기존 '#78' 단독 인용은 문맥상 해당 내용 쪽. a=선착지 3ba4cf00 2026-07-31 11:04)*

**증상**: 20b-f1 온보딩 라이브 검증에서 "목표 입력 ✓"로 체크했으나, 실제 DB에는 goid545 UserGoal 0건 — beat 대상(`portfolio_goal__isnull=False`) 0명이 되어 nightly가 아무것도 안 만들 뻔함. 화면상 "입력했다"는 인상과 DB 영속이 불일치.

**원인**: (1) 그 상태를 **생성하는 UI 경로가 실제로 없었음**(knobs PATCH는 기존 UserGoal 요구, 목표 생성은 admin/shell만) → 사용자가 화면에서 뭔가 눌렀어도 목표가 안 만들어짐. (2) 라이브 체크리스트가 "화면에서 봤다"만 확인하고 DB 영속을 안 봄.

**해결**: **상태를 새로 생성하는 검증(온보딩·목표 설정·최초 등록 등)은 화면 ✓만으로 PASS 금지 — 반드시 확인 쿼리(`.objects.filter(...).count()`/존재)로 DB 영속을 동반 증명**한다. cf. G-S4 `goal 보유자: []`가 이 갭을 잡아냄. [[lesson_dev_prod_shared_db]](캡처 데모 청소도 검증 쿼리 동반 규약과 동형).
## [게이트] 2-dot diff(A..B)로 브랜치 병합/손실 판정 시 오탐 — 3-dot(A...B)·merge-base 명시 비교로 회피 (#78c, 2026-07-31 SEC β R2) [git][process]
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. 기존 '#78' 단독 인용은 문맥상 해당 내용 쪽. c=후착지 663b17e5 2026-07-31 12:54)*

**증상**: "이 브랜치가 main에 병합됐나 / 지우면 손실 있나" 게이트에서 `git diff main..branch`(2-dot)가 실제와 어긋난 결과(무관 차이 혼입 = 오탐, 또는 병합 판정 오음)를 냄. 특히 main이 그새 전진하면 2-dot이 오도한다.

**원인**: 2-dot `A..B`(diff) = 두 tip의 **직접 트리 차이**(양쪽 고유분 혼재) → merge-base 이후 B가 더한 것만 보려는 병합/포함 판정에는 부적합. 원하는 것은 merge-base 기준 = **3-dot `A...B`**(diff) 또는 `git merge-base --is-ancestor`. ※ `git log A..B`는 diff의 A..B와 의미가 달라(=B에만 있는 커밋) 혼동 주의.

**올바른 패턴**: 병합 여부 = `git merge-base --is-ancestor B A`(B⊂A?) · 손실 여부(브랜치 고유 변경) = `git diff A...B`(3-dot) · 고유 커밋 목록 = `git log A..B`.

**재발 점검 순서**: ⑴ 판정 목적 명확화(병합? 손실? 고유커밋?) ⑵ diff는 3-dot/merge-base·log는 목적에 맞게 ⑶ main 전진 여부 재확인 후 판정.

**기록 상태**: 구체 발생 사건의 traceback은 **기록 불충분** — 본 항목은 규칙 골격만 등재(감독 R2 지시 준용, 사실 창작 없음).

## [프로세스] 검증 안 된 라벨·수치의 세션 간 이월(carry-forward) — 실측+HEAD 해시 앵커 필수 (#79, 2026-07-31 SEC β R2) [process][testing]

**증상**: "13건 사전존재 = Neo4j-env"가 **7+세션 DECISIONS에 verbatim 이월**(라인 553·3761·3783·3810·3843·3877·3909…), 코드 실측 시 neo4j 참조 0·격리 29 통과로 반증됨(오라벨). 별건: 캐노니컬 스위트 기대 "4084"가 실측 4463과 불일치(stale 추정치 이월).

**원인**: 한 세션의 미검증 관찰(라벨·수치)이 근거 재확인 없이 다음 세션 보고·원장에 복사됨 → drift가 사실처럼 굳는다. 특히 "사전존재 N건" 같은 실패 census는 원인 tracebacks 없이 라벨만 이월돼 오진이 영속.

**규칙**: ⑴ 베이스라인 수치 = **세션마다 재실측 + HEAD 해시 병기**(해시 없는 정적 수치 이월 금지, D-SECB-BASELINE) ⑵ 실패 census = **원인 tracebacks 동반**(라벨만 기록 금지, TASKQUEUE SECB-REGRESSION-WATCH) ⑶ 이월 오류 발견 시 실측 재검·정정 append(과거 라인 편집 금지).

**재발 점검 순서**: 수치·라벨 인용 전 → 근거 커밋/실측 있나? → 없으면 재측정 → HEAD 해시 병기 후 인용.

## [LLM] 관계 도메인/타입 LLM 재호출이 이전 판정과 모순 — 검수 verdict가 최종 권위 (#80b, 2026-08-01 REVIEW-P2) [chainsight][llm]
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. b=후착지 6d610d67 2026-08-01 13:40, REVIEW-P2 세션 — 채번 경위 ⓑ)*

**증상**: 동일 관계를 LLM에 재호출하면 도메인 태그·타입 시그니처 판정이 이전 호출과 달라짐(예: CAH↔IONQ 계열에서 한 번은 유지, 다른 번은 타입 변경 제안). D-DOMAIN-AUTOMATION 첫 배치 270건에서 **type_change 제안 44%** = SEC 원본 타입과 LLM 이견(다수가 오라벨). 재호출로 라벨이 흔들려 "무엇이 맞는가"가 비결정적.

**원인**: gemini-2.5-flash 분류가 비결정적(temperature·프롬프트 민감). 관계 타입/도메인은 정오답이 명확하지 않은 경계 케이스가 많아 재호출마다 다른 답 → LLM 자기일관성을 신뢰 소스로 쓰면 drift. cf. [[lesson_insight_quality_structure]].

**해결**: ⑴ **타입 변경은 영구 비자동**(D-DOMAIN-AUTOMATION 안전핀) — LLM 제안은 pending 예외로만, 승인 권위는 인간 검수(verdict CHANGE/CHANGE_REV). ⑵ 검수 verdict(`domain_review_status`)가 **최종 권위**로 머신값을 덮어씀(D-REVIEW-VERDICT-VOCAB). ⑶ LLM 재호출 결과를 "정정"으로 자동 반영 금지 — 사람 재정 없이는 이전 승인본 불변. **기록 상태**: CAH↔IONQ 구체 재호출 로그는 review-tool 세션 산출(본 세션 미재현) — 규칙 골격 등재, 사실 창작 없음.

## [tool] 검수 도구 localStorage 캐시가 새 CSV보다 우선 — stale verdict 표시 함정 (#81b, 2026-08-01 REVIEW-P2) [tool][process]
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. b=후착지 6d610d67 2026-08-01 13:40, REVIEW-P2 세션 — 채번 경위 ⓑ)*

**증상**: 검수 도구(`tools/review/domain_review.html`)에서 새 배치 CSV를 로드해도 이전 세션의 verdict가 그대로 보임 — 브라우저 localStorage에 캐시된 검수 상태가 방금 로드한 CSV의 값보다 우선 적용돼, 갱신된 라벨/후보가 반영 안 됨.

**원인**: 도구가 진행 상태(입력한 verdict)를 localStorage에 영속하고, CSV 로드 시 "이미 저장된 verdict 우선" 병합 로직 → 새 CSV의 값이 캐시에 덮여 가려짐. 사용자는 "새 데이터를 본다"고 착각하나 실제는 stale 캐시.

**해결**: ⑴ **CSV가 진실의 소스** — 도구는 새 CSV 로드 시 캐시 무효화(또는 "캐시 vs CSV 충돌" 명시 프롬프트) 필요. ⑵ 검수 결과 반영은 **도구 UI가 아니라 동결 CSV → 로더(apply_review_verdicts)** 경로로 DB 반영(도구는 라벨링만). ⑶ 배치 교체 시 localStorage 수동 클리어를 절차에 포함. **기록 상태**: 도구 개선은 TASKQUEUE REVIEW-TOOL-V6-IMPROVE. cf. [[lesson_dev_prod_shared_db]](진실 소스=DB, 도구는 입력 보조).
## Gate 4 사용자 명령서는 실행 환경(detached HEAD·python 경로) 실측 후 발급 (#80a, 2026-08-01 COVERAGE-DETAIL migrate) [process] [ops]
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. 기존 '#80' 단독 인용은 문맥상 해당 내용 쪽. a=선착지 fa3e20de 2026-08-01 13:39, BATCH-18 mgmt 채번)*

**증상**: migrate 적용(Gate 4 사용자 실행)을 위해 발급한 명령 `git pull` + `python manage.py migrate`가 서빙 트리에서 **2중 실패** — ⑴ `git pull` → "You are not currently on a branch"(런타임 트리는 **detached HEAD 관례**, worker_sync가 re-detach하므로 브랜치 없음) ⑵ `python` → pyenv가 3.11만 잡고 프로젝트 poetry venv(3.12) 미발견.

**원인**: 디렉터/발급자가 명령서를 **기억·일반 관례**(git pull, python)로 작성. 서빙 트리의 실제 상태(detached HEAD, poetry venv python 경로)를 실측하지 않음. 런타임 트리는 detached HEAD가 표준이고 python은 시스템/pyenv가 아닌 poetry venv 절대경로여야 한다.

**해결**: **Gate 4 사용자 명령서는 실행 환경을 실측한 뒤 발급**한다 — ⑴ 트리 최신화는 detached면 `git fetch origin && git reset --hard origin/main`(git pull 아님) ⑵ python은 poetry venv **절대경로**(`~/Library/Caches/pypoetry/virtualenvs/…/bin/python`). 발급 전 `git -C <tree> status --branch`(detached 확인)·`ls <venv>/bin/python`(경로 확인) 1패스. cf. #81(실행 환경 참조 절대경로 고정).

## 실행 환경 참조는 절대경로 고정 — 셸 PATH 간헐 유실 + pyenv/venv 불일치 (#81a, 2026-07~08 다수 실증) [process] [ops]
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. 기존 '#81' 단독 인용은 문맥상 해당 내용 쪽. a=선착지 fa3e20de 2026-08-01 13:39, BATCH-18 mgmt 채번)*

**증상**: ⑴ 서브셸/파이프에서 `git`·`tail` 등이 `command not found`(BRANCH-CLEANUP-FORCE 07-30: for 루프 내 git 유실) ⑵ `python`이 pyenv 3.11로 해석돼 poetry venv(3.12) 미발견(#80). 상대 명령(`git`, `python`, `tail`)이 세션·서브셸마다 다른 바이너리로 해석되거나 미발견.

**원인**: 이 환경의 셸 PATH가 서브셸·파이프·for 루프에서 간헐 유실되고, pyenv shim이 poetry venv를 가림. 상대 명령은 해석 결과가 비결정적.

**해결**: **실행 환경 참조(명령·인터프리터)는 절대경로 고정** — `git`→`/usr/bin/git`, python→poetry venv 절대경로, 또는 명령 블록 서두에 `export PATH=/usr/bin:/bin:…`. for 루프·파이프 회피(개별 명령 나열). cf. #80(Gate 4 명령서 실측), [[feedback_secret_masking_policy]] 계열의 "환경 가정 금지".

## [프로세스] 문서-코드 선행 괴리 — 지시서·요청서의 실행 단계가 미존재 인프라를 전제 (#82, 2026-08-01 SEC β G-d) [process][ops]

> ※ 채번: 감독 지시 "#80"이나 #80·#81 각 2건 병렬 선점(REVIEW-P2·COVERAGE-DETAIL) → #82로 등록(소급 재번호 금지 관례).

**증상**: SEC β Gate 2 사인오프 요청서의 실행 단계 **G-d(flag-on 1 filing → read-path 노출 스모크)**가, 착수 시점에 전제 인프라(`SEC_GROUNDING_ENABLED` flag·grounding_status 노출 read-path)가 **코드에 전무**함이 실측(grep)으로 드러남. 요청서·증빙 4건이 "존재하지 않는 노출 경로"를 전제 → flag flip이 아닌 신규 구축 필요로 판명.

**원인**: 요청서 작성 시 실행 단계의 **전제 코드 경로를 실측 확증하지 않고** 문서(설계 의도)로 선행 기술. grounding 필드는 additive·미노출(설계상 read-path 무관)이었으나 요청서는 노출이 존재하는 듯 기술. 문서 선행이 코드 선행을 대체하지 못함(#79 변종).

**해결·점검**: 지시서·요청서의 **각 실행 단계는 착수 前 전제 코드 경로를 grep/실측 확증** 후 비준. 부재 시 → 그 단계는 "구축 필요"로 재분류·별도 트랙 이관(사변 구축 금지). SEC β 사례 = D-SECB-GATE2-AMEND-1(G-d 제거→SECB-EXPOSURE 이관). cf. #79.

## [chainsight] 파이프라인 배포 ≠ 데이터 적재 — 코드 착지가 DB 반영을 뜻하지 않음 (#83b, 2026-08-03 S3-MINDMAP) [chainsight][process]
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. b=후착지 2daa386f 2026-08-03 09:53, S3-MINDMAP 비mgmt 세션)*

**증상**: D-DOMAIN-AUTOMATION(도메인 태깅 파이프라인)이 배포·원장상 "완료"로 기록됐으나, S3-MINDMAP 착수 시 실측(S3-R)하니 `relation_domain`·`relation_domain_draft`·`domain_machine_check` **DB 전건 0**. 마인드맵 카테고리 재료가 전무 → 착수조건("relation_domain 승인본 반영")이 미충족인데 충족으로 오인될 뻔함.

**원인**: 파이프라인 커맨드(`tag_relation_domains`)가 **dry-run(CSV만·DB무기록)으로만** 실행됐고 `--apply`(실기록)는 미실행. "코드/마이그레이션 착지 = 데이터 적재"로 착각. 태그는 검수 CSV에만 존재, DB엔 부재.

**해결·점검**: ⑴ "파이프라인 배포"와 "데이터 적재"를 **원장에서 분리 기록**(배포=코드 착지, 적재=`--apply` 실행+행수 실측). ⑵ 다운스트림(마인드맵 등) 착수조건은 **DB 행수 실측으로 확증**(`.exclude(field__isnull=True).count()`), 원장 "완료" 라벨 신뢰 금지. ⑶ 본 건 복구 = S0 `backfill_review_domains`(검수 CSV→DB 133건). cf. #79·[[lesson_dev_prod_shared_db]].

## [chainsight] 2단계 apply에서 키 변형 후 재실행 매칭 실패 — already-applied 감지 필요 (#84b, 2026-08-03 REVIEW-P2 회고) [chainsight]
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. b=후착지 2daa386f 2026-08-03 09:53, S3-MINDMAP 비mgmt 세션)*

**증상**: REVIEW-P2 실반영에서 `apply_review_verdicts --apply`(CHANGE 타입 교체) 후 `--apply-change-rev`가 build_plan을 재실행할 때, CHANGE 행의 원 키(PARTNER_WITH)가 이미 COMPETES_WITH로 바뀌어 forward-exact 매칭=0 → H-C(부분반영 금지) 오발·HALT. DB는 안전했으나(무변경 HALT) 2단계 진행이 막힘.

**원인**: 매칭 키(symbol_a,symbol_b,relation_type)가 **반영으로 변형되는데**(CHANGE=type 교체, CHANGE_REV=방향 스왑), 2단계 커맨드가 매 단계 build_plan을 전량 재실행 → 이미 반영된 행이 원 키로 안 잡혀 unmatched=H-C. CHANGE_REV엔 already_swapped 멱등 감지가 있었으나 CHANGE엔 누락(비대칭).

**해결·점검**: 키가 변형되는 반영은 **결과 키로 '이미 반영됨'을 감지**(already_applied: 결과 키+approved 확인)해 unmatched 대신 흡수 → 전체 재실행 idempotent. CHANGE·CHANGE_REV 대칭 처리. 교훈: 다단계 apply에서 매칭 키가 변형되면 각 단계의 재매칭이 앞 단계 결과를 삼킬 수 있음 — 멱등 감지를 모든 변형 유형에 대칭 적용.
<!-- 아래 3건 = SFI-I1(build 세션) 발견·채번 회수분(자가채번 #80~82 → origin/main 선점 충돌로 회수). BATCH-20 push-직전 재grep으로 #83~#85 부여(실측+1, SFI-I1-BUGNUM 완료). -->

## FMPFundamentals.get_rating이 `/stable/rating`(404 오경로) 호출 — 올바른 경로 `/stable/ratings-snapshot` (#83a, SFI-I1 Part A 2026-08-01) [backend][stocks]
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. 기존 '#83' 단독 인용은 문맥상 해당 내용 쪽. a=선착지 9363cac9 2026-08-03 09:37, BATCH-20 mgmt 채번)*

**증상**: `FMPFundamentals.get_rating(symbol)`이 항상 None 반환(로그 `FMP API HTTP 오류 (rating/X): 404`). 종합 투자등급이 화면·엔진 어디에도 채워지지 않음.

**원인**: `/stable/rating`은 현 FMP 플랜에서 404(폐기/미제공). 실제 종합등급(A~F + 항목별 점수 DCF/ROE/ROA/D-E/PE/PB) 경로는 `/stable/ratings-snapshot`. recon 프리플라이트 + 6월 `fmp_api_audit/report.md`(라인 28) 모두 404 실측.

**규칙**: SFI-I1에서 `get_rating`을 `/stable/ratings-snapshot`로 교정. **항상 None이었으므로 회귀 없음 — 행위 변화는 "None→값"뿐**(테스트로 명시). 신규 래퍼 메서드 `get_ratings_snapshot`가 정본 경로, `get_rating`은 이를 위임.

## `/stable/analyst-estimates`는 `period` 파라미터 필수 — 누락 시 HTTP 400, 6월 audit "http-400"은 오진 (#84a, SFI-I1 Part A 2026-08-01) [backend][stocks]
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. 기존 '#84' 단독 인용은 문맥상 해당 내용 쪽. a=선착지 9363cac9 2026-08-03 09:37, BATCH-20 mgmt 채번)*

**증상**: `/stable/analyst-estimates?symbol=X` → 400 `Query Error: Invalid or missing query parameter - period`. 6월 `fmp_api_audit/report.md`(라인 157)가 이를 `http-400`으로 기록 → "이 엔드포인트는 못 씀(플랜 차단)"으로 오해될 소지.

**원인**: 엔드포인트가 `period`(annual/quarter) **필수**. 누락 시 400(플랜 차단 아님). 실측(recon):
- `period=annual` → **200 OK, Starter 가용** (미래 fiscal 연도별 revenue/EBITDA/EBIT/netIncome/EPS Low·High·Avg + numAnalysts). AAPL·TLN(소형)까지 가용.
- `period=quarter` → **402 Premium 차단**.

**규칙**: 래퍼 `get_analyst_estimates`는 `period="annual"` **고정**(quarter는 402이므로 파라미터로 열지 않음). audit의 `analyst-estimates http-400` 항목은 "period 누락 오진"으로 정정 인식.

## recon/측정 세션이 stale base 위에서 "부재" 오판(false-missing) — fresh origin/main 강제 (#85, RECON-STALE-BASE, SFI-I1 2026-08-01) [process][harness][git]

**증상**: SIGNAL-FORWARD-INFRA 프리플라이트 recon이 실측 대상 2건을 "repo 부재"로 오판:
- `RUN-TOTAL-PERSIST` 백로그 = "TASKQUEUE 무매치"(실제 origin/main TASKQUEUE:1103 등재됨).
- `EstimateSnapshot` 모델·수집 파이프라인 = "이 트리 부재"(실제 chain_sight에 배포·가동 중, beat 등록).

**원인**: recon 브랜치가 origin/main(`d484b9cb`)이 아닌 **분기된 HOLD-P1 라인(`b8d767aa`, 208 커밋 뒤처짐)** 위에 기반. 그 base엔 f2 랜딩(RUN-TOTAL)·theme_heat 모델(EstimateSnapshot)이 아직 없어 "부재"로 보임(false-missing). 측정 자체는 정확했으나 **잘못된 base가 사실을 가림**. cf. #79(미검증 라벨 이월)·common-bugs #59(worktree 최신성 STEP 0 강제).

**규칙**: ⑴ recon·측정·설계 세션은 **fresh `origin/main`에서 시작**(신규 트랙 base = origin/main, 분기 라인 위 기반 금지). ⑵ 보고 **첫 줄에 base HEAD 해시 명기**(#79 해시 앵커 규율의 base 판). ⑶ "부재/무매치" 판정 전 `git show origin/main:<path>`로 origin/main 대조 필수(로컬 브랜치 grep만으로 부재 단정 금지). ⑷ stale 발견 시 `git rebase --onto origin/main <old-base>`로 즉시 교정 후 재측정.

**재발 점검 순서**: "X 부재" 인용 전 → 내 base = origin/main인가?(`git rev-list --count HEAD..origin/main`=0?) → 아니면 `git show origin/main:path` 대조 → 그래도 부재면 확정.

## GLOBAL-SCOPE-TASK — 태스크에서 ORM 직접 읽기 시 user 스코프 명시 의무 (#95, SFI-I-1b 2026-08-04, 채번 MGMT-BATCH-A 2026-08-11) [backend][process]

**증상**: SFI-I1 `_coach_universe()`(celery 태스크)가 `WalletHolding/WatchlistItem.objects.all()` 무필터로 읽어 **타 유저(admin) 테스트 데이터(레버리지 ETF 5종)까지 coach 유니버스에 유입** → 자동발화가 admin 심볼 수집. 동일 모델의 화면·dashboard·advisory 소비처는 전부 per-user였음(비대칭).

**원인**: DRF 뷰는 `get_queryset`이 `request.user`로 스코프를 **구조적으로 강제**하지만, **celery 태스크·management 커맨드는 request가 없어 아무도 안 막아준다**. 개발자가 뷰의 per-user 관례를 태스크로 옮길 때 스코프를 빠뜨리기 쉽다(뷰 코드엔 필터가 있으니 "모델은 원래 per-user"라 착각).

**규칙**: 태스크·커맨드에서 유저 소유 모델(Watchlist·Wallet·Portfolio 등)을 ORM 직접 조회할 때 **user 스코프를 명시**하라(어느 유저 집합인지 코드+docstring에 못박음). 멀티테넌트 유니버스는 소유자 정의(전 유저? 특정 유저 집합?)를 먼저 확정. 참조 좌표 = 같은 도메인의 nightly 태스크 필터(예: advisory `portfolio_goal__isnull=False`).

**재발 점검**: 태스크에서 `<UserOwnedModel>.objects.all()`/무필터 `.filter()` 발견 → user 스코프 있나? → 없으면 소유자 정의 확인 후 명시.
## 단일 공유 test DB에 pytest suite 동시 실행 시 가짜 에러 (#86a, TH-SESSION-1 2026-08-03) [testing][process]
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. 기존 '#86' 단독 인용은 문맥상 해당 내용 쪽. a=선착지 6beb7b43 author 2026-08-04 10:33, mgmt형 meta-only 채번 = 병렬 충돌·위반 아님)*

**증상**: 세션 종료 앵커 suite가 갑자기 다수 에러 — reuse-db 경로는 `psycopg2.errors.DuplicateColumn: column "…" already exists`, `--create-db` 경로는 `database "test_stock_vis" is being accessed by other users` → `SystemExit: 2` → **전 테스트 setup error, 8초대 조기 종료**(collected N items 직후 EE…).

**원인**: pytest는 단일 test DB(`test_stock_vis`)를 공유. suite를 백그라운드로 **겹쳐 실행**(run_in_background 다수, 또는 `( … ) &` 오르핀)하면 두 프로세스가 같은 DB를 동시 접근 → 한 런의 half-applied 마이그가 다른 런에 DuplicateColumn으로, 또는 --create-db가 DROP 실패. **코드 회귀 아님** — 오케스트레이션 아티팩트. 실측: 동일 커밋이 단독 실행 시 GREEN.

**규칙**: 앵커/전체 suite는 **동시에 1개만**. 실행 전 `ps aux | grep pytest`(=0) + `psql -d stock_vis -tAc "SELECT count(*) FROM pg_stat_activity WHERE datname='test_stock_vis'"`(=0) 확인. 8초 내 다수 error = 거의 항상 이 동시성(또는 import 에러). 오르핀 발견 시 종료·DB 연결 0 확인 후 단독 재실행. cf. #27·#79(reuse-db 오염), lesson_dev_prod_shared_db(prod DB는 별개).

## CC의 `git branch -D` 경계 — 병진 명시 + 손실 0 입증 동시 충족만 (#87, TH-SESSION-1 2026-08-03) [process][harness][git]

**맥락**: cherry-pick으로 내용을 착지시킨 브랜치(예: sess-th-recon, 원본 커밋 6f8c6c7d → 새 해시 915494c1)는 `git branch -d`가 **커밋 미도달로 거부**(patch 등가성 미인식). `-D`가 필요하나 파괴적.

**규칙**: CC의 `-D`는 **⑴ 병진의 건별 명시 지시 + ⑵ 손실 0 사전 입증(삭제 대상 브랜치의 고유 커밋 `git log origin/main..<br>`이 내용상 origin/main에 존재 = `git cat-file -e origin/main:<path>` 또는 파일 diff 공집합) 둘 다 충족 시에만**. 일괄·재량 -D 불허. ⚠️ `git diff origin/main <br>`(2-dot 전체 트리)의 삽입/삭제는 **브랜치가 뒤처져서** 생기는 아티팩트일 수 있음(#78 변종) → 손실 판정은 `origin/main..<br>` 고유 커밋 기준으로만. `git branch -d` 거부는 안전망 = 기본 존중, 뚫기 전 위 2조건 재확인.

## 병진 수동 prod 커맨드는 별도 터미널 전용 — CC `!` 경유 시 harness 2분 truncate (#88, TH-TNV-CHAIN-1 2026-08-04) [process][harness][ops]

**증상**: CC가 병진에게 준 prod 백필 커맨드를 CC 프롬프트 `!` 경유(또는 CC 안내대로 foreground)로 실행 시, **harness 2분 foreground 한계에 걸려 커맨드가 truncate**됨. 실측 2회: TH-SESSION-1 ②(heat 재산출, "moved to background" 후 완료) · TH-TNV-CHAIN-1 §C ②(heat 재산출, "timed out after 2m" — 08-04 heat 6행 중 5행만 기록되고 kill, 출력 3줄 미표시).

**원인**: 대형 DB 연산(compute_theme_heat 루프 등)이 2분 초과. `!`/foreground 경로는 harness 타임아웃 대상. 멱등 연산(update_or_create)이라 이번엔 무해했으나, **비멱등 연산이면 부분 실행 사고**(절반 쓰고 kill).

**규칙**: ⑴ 지시서의 병진 커맨드 안내에 **"별도 터미널(Terminal.app)에서 실행" 명기 필수** — CC `!` 프롬프트 경유 금지(2분 한계 + 첫글자 탈락 #, 이중 함정). ⑵ truncate 발생 시 **재실행 前 반드시 읽기 assess**로 부분 상태 규명(어느 date/row까지 기록됐나·진행 프로세스 잔존 여부) → **멱등 확인 후에만 완결 재실행**(blind 재시도 금지). cf. lesson_background_task_reaping.

## health_check는 worktree-local — 정체 트리에서 PROGRESS 신선도 거짓 FAIL (#89a, MGMT-BATCH-24 / LAND-C2-S1-B1 2026-08-06) `[process][harness][git]`
*(채번 정정 #89 이중할당→a/b, D-NUMBERING-DUP, MGMT-BATCH-26: **a=선착**(BATCH-24 mgmt 채번, author 08-06)·b=TH-TNV-CHAIN-1F 세션날짜금지(L1362, 비mgmt 채번·post-A 위반, 아래). author date 순.)

**증상**: LAND 세션에서 `health_check.py`를 **현재 앉아있는 세션 브랜치 워크트리**(예: `sess-signal-fwd-recon` @ 0790c8f, PROGRESS.md 07-21 정체)에서 실행하면 `origin/main 해시`·`PROGRESS 갱신 stale` **FAIL 2건**이 뜸(실측 11 OK/2 WARN/2 FAIL). 착지 대상 트리(`main`=origin/main, PROGRESS 08-06 신선)에서 재측정하면 **14/1/0**으로 정상 → 앞의 2 FAIL은 거짓이었음.

**원인**: health_check는 **PROGRESS.md 신선도·origin/main 해시를 현재 워크트리 기준으로** 읽음(tree-position-sensitive). 세션 브랜치가 오래된 PROGRESS.md를 물고 있으면 그 브랜치 기준으로 정체가 측정됨. #47(`실행 트리 정합` WARN)이 같은 뿌리의 신호이나, #47은 WARN이고 본 함정은 **FAIL 오탐**이라 문언상 "FAIL=HALT"에 걸려 정상 착지를 막을 수 있음. (부수: health_check가 내부 `git fetch`를 하는 듯 — 실행 중 origin/main이 전진할 수 있으니 게이트 재fetch #40 필수. LAND-C2-S1-B1에서 실측: health 실행 중 origin/main `e76237a8→0b0621e8` 전진.)

**규칙**: ⑴ 게이트 health는 **착지 대상 트리(main 체크아웃 = origin/main) 또는 origin/main 기준 신규 worktree에서 측정** — 정체 세션 브랜치서 재지 말 것. ⑵ `실행 트리 정합` WARN(#47)이 보이면 트리 위치 재확인. ⑶ **실행자 로컬 메모(auto-memory 등)는 비정본** — 교훈 정본화는 장부(common-bugs/DECISIONS) 등재로만. cf. DECISIONS `D-LANDING-ONE-SESSION-PER-APPROVAL` 보강(게이트 health 측정 트리).

## 상태 어휘의 트랙 간 의미 충돌 — 'rejected'가 ego 서빙서 엣지 은닉 (#86b, 2026-08-04) `[data][process]`
*(채번 충돌 구분자, D-NUMBERING-DUP 참조. b=후착지 86961ec4 author 2026-08-04 20:51, L2-FULL-SWEEP 비mgmt 세션 채번 = 규칙 위반. B 트리거 미해당 — 세션 시작(첫 커밋 88850fce author 08-03 18:24) < A 착지(05211a02 08-05 10:16), pre-A 시작. REVIEW-P2·S3-MINDMAP에 이은 3번째 위반)*
## 상태 어휘의 트랙 간 의미 충돌 — 'rejected'가 ego 서빙서 엣지 은닉 (#97, L2-FULL-SWEEP 2026-08-04) `[data][process]`

> ⚠ 채번 각주(PRE-DEPLOY-FIX 2026-08-05): 본 항목 추가 커밋(`86961ec4`, L2-FULL-SWEEP P3~P6) 메시지엔 **#86**으로 언급됨 — 처방 A(2026-08-03, 비mgmt 자가채번 금지) 인지 전 채번. **번호는 mgmt 채번 시 확정**.

**증상**: L2-ADOPT 거부권(veto) 발동 PEER를 `domain_review_status='rejected'`로 기록하면, 마인드맵/카드에서
관계 자체가 **사라짐**(태그만 빠지는 게 아니라 엣지 통째 은닉).

**원인**: `domain_review_status` 어휘가 **두 트랙에서 다른 의미**로 쓰임 —
- ⑳-3 REVIEW/S3(SEC 검수 트랙): `'rejected'` = **soft-drop**(나쁜 관계 은닉). `ego_views` 메인 쿼리가
  `.exclude(domain_review_status='rejected')`로 은닉.
- L2-ADOPT(거부권 트랙): 거부권 = "LLM **태그** 기각 → 업종 버킷 폴백"이지 "**관계** 은닉"이 아님.

같은 필드·같은 값이 트랙마다 의미가 달라, L2에서 무심코 'rejected'를 쓰면 SEC 트랙의 은닉 로직에
걸림. (A3 발견 — P4 라이브서 재확인: 거부권 쌍 엣지 미은닉·버킷 폴백 정상.)

**해결/규칙**: 거부권 미채택은 **`'pending'`**(엣지 유지·서빙서 버킷 폴백), **`'rejected'`는 은닉 의미로만
예약**. 상태 CharField를 트랙 간 공유할 때는 ⑴ 각 값의 **서빙 측 부수효과**(exclude 등)를 먼저 확인하고
⑵ 새 트랙이 기존 값을 재사용하기 전 그 값에 걸린 필터를 grep(`domain_review_status=`)해 의미 충돌을 점검한다.

## rebase 후 원장 내 커밋 해시 앵커 무효화 — dangling 참조 (#98, PRE-DEPLOY-FIX 2026-08-05) `[git][process]`

**증상**: 세션 중 원장(DECISIONS·TASKQUEUE·리포트)에 커밋 해시(슬라이스별 커밋·머지 hash)를 앵커로 기록한 뒤,
머지 전 origin/main 전진으로 rebase하면 **그 커밋들이 새 해시로 재작성** → 원장 텍스트의 해시가
존재하지 않는 커밋을 가리키는 **dangling 참조**가 됨. 다음 세션이 `git show <해시>`·grep하면 미발견 →
추적성(커밋↔task ID) 파손·혼선.

**원인**: 하네스 규율(#79)이 "실측+HEAD 해시 앵커"를 요구해 원장에 해시를 적게 되는데, rebase는
해시를 바꾼다. 앵커를 **rebase 전에** 적으면 무효화. (line 756은 merge-base 검증 실패 — 별건. #79는
앵커를 처방하나 rebase 무효화는 미언급 — 본 항목이 그 caveat.)

**규칙**: ⑴ 커밋 해시 앵커는 **최종 rebase 이후에 확정 기록**(rebase 예정이면 잠정 표시). ⑵ 부득이
rebase 전 기록 시, **머지 직전 구 해시 전수 grep→신 해시 교체**(커밋 메시지는 불변, 히스토리 재작성 금지).
⑶ 교체 후 `git grep <구해시들>` = 0 확인(dangling 잔존 점검). 앵커 후보 = 슬라이스별 커밋·머지 hash.
**★변종 (#88b, TH-TNV-CHAIN-1F 2026-08-06)**: 긴 1줄 명령을 프롬프트에 붙여넣으면 **터미널 소프트랩이 실제 개행을 삽입**해 `source`/경로/인자가 쪼개짐(실측: `source ... activate`→arg 분리, 긴 scratchpad 경로→`scratch`/`pad/…` 분리, `bash`→첫글자 탈락 `ash`, `checkout --detach\n origin/main`→인자 유실). **해결 = 모든 긴 병진 명령을 짧은 셸 스크립트 파일로 만들고**(홈 디렉터리·긴 경로 내부화) 병진은 `bash ~/짧은.sh` 한 줄만 실행. 스크립트는 CC가 쓰고(파일 쓰기=DB/launchctl 아님) 병진이 트리거(레일 유지).

## 세션 대화의 날짜·시각 가정 금지 — 발화/배포 선후는 machine clock·last_run 실측 전용 (#89b, TH-TNV-CHAIN-1F 2026-08-06) [process][harness][ops]
*(채번 정정 #89 이중할당→a/b, D-NUMBERING-DUP, MGMT-BATCH-26: b=후착(TH-TNV-CHAIN-1F **비mgmt** 채번, `8a41c842`가 common-bugs 실변경). **처방 B 위반 확정** — 세션 최소 author date(landed 최소 `d6f6f9b5` 08-07 10:55) > A착지(`05211a02` 08-05 10:16) = **post-A**. 집행(훅 설치)은 사용자 승인 회부(DECISIONS D-NUMBERING-MGMT-ONLY 참조).)

**증상**: G-fire 판정에서 "18:00 ET 08-05 발화 = 검증 대상"으로 가정했으나, 실측하니 그 발화(last_run ET 18:00 08-05 = KST 07:00 08-06)가 **배포(KST 11:50 08-06)보다 먼저** → 구 코드 발화 = 체인 로그 부재가 정상. 감독의 날짜 지정조차 실측이 재교정.

**원인**: KST-ET **13h 시차**(EDT 기준)로 "오늘/어제/발화일" 대화 감각이 자주 틀림. 세션이 며칠 걸치면 date-change 알림도 KST 기준이라 ET 날짜와 어긋남.

**규칙**: 발화/배포/롤오버의 **선후·날짜 판정은 반드시 machine clock·`PeriodicTask.last_run_at`·row `created_at` 실측으로만**. 대화 속 날짜 문장(감독 포함)은 가정 금지·실측으로 검증. 로그/DB의 UTC를 `astimezone`으로 ET·KST 병기해 대조. cf. #88b.

## LOGGING 로거 미라우팅 갭 — logger.info 호출 ≠ 파일 기록 ("활성화≠배포"의 로깅판) (#90, TH-TNV-CHAIN-1F 2026-08-06) [logging][observability]

**증상**: heat_tasks가 `logger.info("TNV_CHAIN …")`로 관측성 로그를 남기도록 구현(§B.1)했으나, 실전 발화 후 celery-worker.log·stocks.log 어디에도 없음. 체인은 DB로 실행 입증됐는데 **로그만 부재**.

**원인**: `config/settings.py` LOGGING이 `packages.shared.stocks`·`celery.error_monitor` 로거만 파일 핸들러에 연결. `apps.chain_sight.tasks.heat_tasks`(=`getLogger(__name__)`)는 미등록 → INFO가 root last-resort(WARNING 임계)로 빠져 **드롭**. `logger.info` 호출이 있다고 파일 기록이 되는 게 아님.

**규칙**: ⑴ 관측성 로그를 **설계 근거(게이트 증거)로 쓸 때는 로거 라우팅(파일 핸들러 도달)까지 실측 확인** — "코드가 log 호출함" ≠ "파일에 남음". ⑵ 신규 앱 로거는 LOGGING `loggers`에 등재(또는 상위 `apps` 로거로 포괄). ⑶ ⚠️ **`propagate: False` 주의** — root 전파 차단 시 pytest `caplog`(root 레벨 캡처)가 빈 상태가 돼 **caplog 기반 로그 검증 테스트가 붕괴**(실측: apps 로거 propagate=False로 5 테스트 실패). 파일 핸들러 + caplog 병존하려면 `propagate=True`. cf. #28(beat 활성화≠배포).

## 비트 태스크의 FieldError 무음 전량 실패 — collect_press_releases_fmp (#미채번 mgmt 배치 대기, NEWS-P0-FIX 2026-08-06) `[news][process]`
*(D-NUMBERING-DUP 처방 A 준수 — 비mgmt 자가채번 금지, 번호는 mgmt 채번 시 확정)*

**증상**: `collect_press_releases_fmp` beat(45 7 ET, enabled)가 **매 실행 FieldError로 전량 실패**하나
로그 외 관측 신호 없음 → 보도자료 수집 0건이 조용히 지속(무음 실패 클래스).

**원인**: `services/news/tasks.py`의 `SP500Constituent.objects.filter(is_active=True).order_by("-market_cap")` —
`SP500Constituent`에 **`market_cap` 필드·컬럼 자체가 없음**(RECON-NEWS-P0 N1). `.order_by`가 존재하지 않는
필드를 참조 → 쿼리 즉시 `FieldError: Cannot resolve keyword 'market_cap'`. (HA-P0 R5의 "전건 None"은
부정확 — None이 아니라 필드 부재.) market_cap을 채우는 write 경로도 부재(FMP 402 #23과 무관).

**교훈**: ⑴ **비트 태스크는 무음 실패한다** — 스케줄만 enabled면 "돌고 있다"는 착시. 실효 검증은
`last_run`이 아니라 **산출물 행 증가**(NewsEntity 등)로. ⑵ ORM `.order_by/filter`의 필드 참조는
**모델 `_meta` 실측**으로 검증(문서·기억 아님). ⑶ 수리 = NEWS-P0-FIX(Stock.market_capitalization
조인 정렬 대체) + 비트 경로 통합 테스트(FieldError 재발 시 red).

## 현장 승인 건은 채팅 1줄 중계 원칙 — §H 재기동·프로브 결과 등 실행 승인/판정은 채팅에 원값 1줄로 남긴다 (#91, CLOSE-0808 2026-08-10) [process][harness]

**교훈**: §H 워커 재기동·프로브 합격/HALT 판정처럼 "현장에서 즉시 승인·집행되는 건"은 하네스 파일에 옮기기 전에 **채팅에 결과를 원값 1줄로 중계**한다(예: "sv sync 완료·3트리 18d8c698·daphne401"). 디렉터가 파일 커밋을 기다리지 않고 상태를 즉시 판단할 수 있고, 사후 하네스 반영 시 대조 기준이 된다. 승인 인용 규율([[feedback_deploy_approval_explicit_quote]])과 짝.

## 필터 망라성은 문법 변형 포함 광역 grep 필수 — 리스트 컴프리헨션만 잡으면 제너레이터·조건절 형태를 놓친다 (#92, TH-UNIVERSE-DOTSYM 2026-08-08) [process][search]

**증상**: DOTSYM STEP 0에서 dot 배제 필터를 `[s for s in … if "." not in s]` 형태로만 grep → 3개소로 보고. 실제로는 제너레이터(`s for s in … if "." not in s`)·별도 커맨드 파일까지 **6개소**였고, Slice 2 착수 후 광역 재grep에서 3개 추가 발견(스코프 재판정 유발).

**교훈**: "모든 필터/호출 지점"을 세는 작업은 **문법 변형을 포함한 광역 grep**으로. 리스트 컴프리헨션·제너레이터 표현식·`if` 조건절·다른 파일의 동일 목적 코드를 한 번에 잡는 패턴(`"\." +(not )?in` 등)을 쓰고, 커밋 전 재grep으로 잔여 0 확증. 단일 문법 가정은 census 누락의 상시 원인.

## 마감 블록은 하네스 진실이 아님 — 세션 원장의 "잔여/수치"는 다음 세션 STEP 0 재검증 필수 (#93, CLOSE-0808 2026-08-10) [process][harness]

**증상**: SEAL-PUSH-1 지시서가 07-29 마감 블록의 "push 1줄 잔여"를 근거로 push를 지시했으나, STEP 0 실측 결과 그 커밋은 이미 origin/main에 착지 완료(잔여 소멸). 마감 블록 수치가 stale이었음.

**교훈**: 세션 원장·마감 블록의 "잔여 작업·스위트 수치·베이스라인"은 기록 시점 스냅샷일 뿐 하네스 진실이 아니다. 다음 세션은 **STEP 0 재실측을 정본으로** 삼고, 마감 블록은 참조로만. 베이스라인 기록 시 "이월 금지·재실측이 정본" 명시([[lesson_origin_main_advance_union_rebase]] 계열).

## 고아 스냅샷 — 비정규 요일 수집분은 금요일 anchor − 56/63 정확 매칭에 안 걸려 C8에 기여하지 않는다 (#94, TH-HEAT-C8-COLDSTART-CHECK 2026-08-10) [chainsight][data]

**증상**: EstimateSnapshot에 07-29(수요일, TH-DEPLOY catch-up 발화)가 있으나, C8 EPS diff는 `anchor − lag`(56/63일) **정확 날짜 매칭**(`eps_diff_at` estimate_revision.py:56)이라 금요일 anchor에서 07-29(수)를 파트너로 잡지 못함. 07-29 회차는 rows는 채웠지만 C8 리비전 계산엔 사실상 고아.

**교훈**: lag 기반 정확-매칭 시계열(diff)은 **수집 요일이 규칙적이어야** 파트너가 성립한다. catch-up·수동 등 비정규 요일 스냅샷은 행은 늘리지만 lag 매칭에서 누락 → 콜드스타트 임계 산출은 **정규 요일 첫 스냅샷**(DOTSYM=07-17 금)을 기산점으로. 임계 대기와 배선 결함을 가를 땐 파트너 존재 여부를 캘린더로 실측.

## `__date` 룩업은 로컬 tz 버킷팅 — UTC 자정 경계 발화가 거짓 0건, 날짜 필터는 UTC 범위로 (#96, SPOT RECON 2026-08-11) [backend][data][process]

**증상**: 2026-08-11 SPOT recon에서 `AnalystSignalSnapshot.objects.filter(captured_at__date=date(2026,8,10))` = **0건** → "발화 부재 의심"으로 STOP 조건 오발동 직전. 실제로는 23:30Z(08-10) 발화 **9행 실재**(beat last_run 2026-08-10 23:30:00Z). `TruncDate` 집계도 동일하게 그 9행을 **08-11**로 버킷팅.

**원인**: Django `__date`/`TruncDate`는 tz-aware datetime을 **프로젝트 `TIME_ZONE`(로컬)로 변환한 뒤** 날짜를 뗀다. UTC 23:30(08-10)은 로컬(KST +9)에서 08-11 08:30 → 로컬 날짜=08-11. 저장은 UTC지만 날짜 룩업이 로컬 경계를 쓰므로 **UTC 자정 근처 발화가 인접 날짜로 새는** 오프바이원.

**규칙**: 특정 UTC "발화 회차"를 조회할 땐 `__date` 금지 — **UTC 반열린 범위**(`captured_at__gte=lo, captured_at__lt=hi`, tzinfo=UTC)로 필터. STOP/0건 판정 전 UTC 범위로 재확인(거짓 0건 방지). 집계 날짜 축이 필요하면 `TruncDate(..., tzinfo=timezone.utc)` 명시. cf. #24(Date.now hydration 계열 tz 함정).
## 배치 진척·완주 지표에 창-합(target_windows) 사용 금지 — skip-covered 스필오버로 영구 저계상 (#99, CN-B7-PROBE 2026-08-10) `[ops][data][harness]`

## 병렬 마이그레이션 리프 — 랜딩 시점 단일 0014가 배포 시점 타 트랙 0014와 병존 → 지시서 STEP 0에 "마이그 직전 fetch + 최신 번호 재확인" 상설 (#97, I3-SPLIT-GUARD 2026-08-18) [backend][process][harness]

**증상**: I3-SPLIT-GUARD 배포(HALT ②) STEP 0에서 `showmigrations stocks`가 기대 "0014 [X]" 대신 **`0014_stocksplit[X]` + `0014_stock_cik[X]`(타 트랙 CS-P3) + `0015_merge [ ] 미적용`**을 노출. 내 랜딩(08-13) 시점엔 stocks 리프가 단일 0014였으나, 배포(08-18) 사이 CS-P3가 **같은 0013에서 분기한 별도 `0014_stock_cik`**를 랜딩 → Django 리프 2개 → 제3자가 `makemigrations --merge`로 `0015_merge`(no-op) 생성.

**원인**: 동일 앱에 **여러 세션이 병렬로 0013→0014를 분기**하면 번호가 충돌하지 않아도(파일명은 다름) 마이그레이션 그래프에 **리프 2개**가 생기고, prod엔 merge 마이그가 미적용으로 남는다. 지시서/원장의 "0014 [X]" 기대값은 랜딩 시점 스냅샷이라 배포 시점엔 stale.

**규칙**: ⑴ 마이그레이션 **생성·검증 직전 `git fetch` + 해당 앱 최신 번호 재확인**(makemigrations 前 리프 상태 실측). ⑵ 지시서 STEP 0 템플릿에 "**마이그 번호는 캐시 — 집행 직전 fetch 후 재확인**" 상설 조항. ⑶ 병렬 리프 조우 시 merge 마이그는 `sqlmigrate`로 **DDL 0(no-op) 확인 후에만** 적용(승인). cf. 기대값=캐시(#93 계열)·[[lesson_land_health_measure_in_target_tree]].

## recon 지시서는 "발화 도래 여부"를 선확인해야 — 미도래를 실패로 오판 방지 (#98, I3-SPLIT-GUARD 첫 발화 recon 2026-08-18) [process][ops]

**증상**: "08-18 19:45 ET 발화 recon" 지시가 현재 ET 02:34(발화 17시간 前)에 수행됨 → last_run None·StockSplit 0·로그 0. 발화 실패가 아니라 **아직 스케줄 시각 미도래**.

**규칙**: 발화 후 recon 지시서는 STEP 0에 **"현재 시각 vs 스케줄 발화 시각 선비교"** 조항 필수. 미도래면 산출 없음을 보고하고 **수동 실행으로 선점 금지**(자연 첫 발화의 created 카운트가 오염됨 — 멱등 append/skip이라 수동 실행 시 첫 자연 발화가 created 0으로 바뀜). 도래 후 재수행.

## 프리플라이트 절단 출력(`head -c`·`| head`)은 하한일 뿐 — 전수 카운트 판단은 절단 없이 (#99, I3-SPLIT-GUARD 2026-08-18) [process][data]

**증상**: 프리플라이트에서 FMP splits를 `curl ... | head -c 400`으로 읽어 AAPL 분할을 **3개**로 기록 → "총 ~13행" 기대. 실발화 실측 = AAPL **5개**(2020·2014·2005·2000·1987)로 총 **15행**. 예상 −2 차이의 원인 = 절단.

**규칙**: 카운트·전수 판단이 걸린 값은 `head -c`/`| head` 같은 **절단 출력으로 산정 금지**(절단분은 하한). 기대값 산정 시 `jq length`·`wc -l`·DB 카운트 등 **절단 없는 집계**로. 절단 출력으로 얻은 수는 "≥N"으로만 취급.
## 배치 진척·완주 지표에 창-합(target_windows) 사용 금지 — skip-covered 스필오버로 영구 저계상 (채번 후보, CN-B7-PROBE 2026-08-10) `[ops][data][harness]`
*(D-NUMBERING-DUP 처방 A 준수 — 비mgmt 자가채번 금지, 번호는 mgmt 채번 시 확정)*

**증상**: C-N-REPAIR 8배치 완료 시점 아침 점검이 진척을 **158/192**로 보고했으나, 8배치×20일=160 기대 대비 2일 부족으로 오인. 실제 DB 커버는 **160/160**(구멍 0).

**원인**: `status.json`의 `target_windows` 합(=배치가 실제 **백필한 창 수**)을 "커버된 일수"로 오독. 연속 배치의 창 가장자리가 다음 배치 첫 날짜를 미리 채움(`--skip-covered`) → 그 배치는 20이 아닌 **19창만 백필**(batch4=2025-05-09·batch5=2025-07-10 각 1일 pre-covered). 창-합은 skip-covered만큼 **영구 저계상**되나 해당 일자는 실제로 커버돼 있음. 완주 시점(192/192)에도 창-합은 <192로 남아 헛경보 유발.

**교훈**: ⑴ 진척·완주 판정의 **유일 유효 지표 = DB 일-존재 스캔**(plan 일자 각 `NewsArticle.filter(published_at__date=D)>0` 카운트). 창 수·target_windows 합은 **판정에 쓰지 말 것**(관측 로그용). ⑵ 멱등 파이프라인(`--skip-covered`)에서 "처리한 단위 수"와 "커버된 대상 수"는 **다른 양** — 스필오버·중복 스킵이 개입하면 전자 < 후자. ⑶ D-CN-COMPLETE 폐기 교훈("창 완료 122/122" 금지)의 재현 — 항상 **대상 단위 존재**로 완료 선언. CHECK-DAILY v2 §3·§6이 이 지표로 고정됨.

## AV summary=null 정당 드롭은 not-null 관문 정상 작동 (이상 아님) — skipped 카운터 의미 정의 (#100, CN-B7-PROBE 2026-08-10) `[news][data][ops]`
*(D-NUMBERING-DUP 처방 A 준수 — 비mgmt 자가채번 금지)*

**증상**: C-N-REPAIR batch7 로그에 `Failed to save article: null value in column "summary" ... violates not-null constraint` **8건** 출현, `skipped 8`에 계상. "무음 데이터 드롭 아니냐"는 경계 신호.

**원인·판정**: Alpha Vantage NEWS_SENTIMENT가 일부 정형 기사(MarketBeat instant-alerts·13F/insider 신고류)를 **`summary=null`로 제공** → `news_articles.summary` not-null 제약이 저장 시점에 정당 거부. **이상 아님**(관문 승리): ⑴ 해당일(2025-10-08·10-15·11-04)은 드롭과 무관하게 **≥3 커버 유지**(드롭 6유니크 기사가 그날 유일 기사가 아님), ⑵ exit0·status=ok·**시스템 ALERT 무**가 설계상 정상(정당 드롭은 무알림). CN-B7-PROBE로 원인 (A) AV 응답 결함 확정(우리 파싱 결함 (B) 아님 — Failing row가 AV 원본 summary=null임을 직접 노출).

**교훈**: ⑴ **`skipped` 카운터 = save 실패(드롭) 건수** — 재시도분 포함(6유니크가 8회 시도로 계상). 별도 fetch-레벨 skip(url-too-long)은 이 카운터에 미포함. ⑵ 정당 드롭(외부 제공자 결함)과 코드 결함(우리 파싱)의 구분은 **로그 Failing row 원문**으로(요약 아님). ⑶ 커버 완전성(≥1) + 정당 드롭은 **모순 아님** — 커버는 대상일 기사 존재로 판정, 드롭은 개별 기사 품질 문제. 복구 불요(저가치 정형기사·해당일 커버 유지). 근본 수리는 별도 트랙(모델 `summary` default="" or provider 보정).

## 정상 어휘가 티커 필터에 오소거 — 단일토큰 회사명 매칭 (#101, NEWS-VOCAB-BUILD Rev.1→2 2026-08-06) `[data][process]`

**증상**: 뉴스 n-gram에서 종목명·티커를 기계 제거할 때, 회사 `stock_name`의 **단일 토큰**(energy·data·center 등 흔한 도메인어)까지 필터 재료로 넣으면 정상 카테고리 어휘가 오소거됨. Rev.1에서 `data center`·`renewable energy`·`clean energy`·`real estate`가 "회사명 토큰 포함"으로 탈락 → 핵심 교차 테마가 어휘에서 소실.

**원인**: `stock_name`에 흔한 명사(Energy, Data …)가 다수 포함 → 단일 토큰을 회사명 시그널로 쓰면 도메인 일반어와 충돌. 티커도 짧은 것(AI·MU)은 도메인어와 겹침(단, 토큰 길이>2 필터로 대부분 회피).

**규칙**: 티커/회사명 제거는 **풀네임 n-gram 매칭 + 티커 토큰(길이>2) + 거래소어(nasdaq/nyse)만**. **회사명 단일 토큰 매칭 금지**. Rev.2에서 교정 = `data center` 등 부활 확인.

## 규약 충돌 grep은 금지 어휘 외 위임 어휘도 포함해야 한다 — "금지"만 찾으면 "대행·승인 불필요"를 놓친다 (#102, GOV-PUSHDELEG-0810 2026-08-10) [process][harness]

**증상**: D-PUSH-DELEG 명문화 STEP 0-5에서 push 규약 정본을 `push.*금지` 패턴으로 grep → session_isolation_guide.md 1곳만 잡고 "중복 없음"으로 판정. 그러나 SESSION_CONTRACT.md §H `D-DEPLOY-DELEGATE`("CC 대행 기본 — **승인 불필요** origin push")가 이미 존재·정면 상충. 편집 중에야 발견(HALT·상신).

**교훈**: 규약 충돌·중복 census는 **금지 어휘(금지/불가/막는다)만이 아니라 위임 어휘(대행·위임·불필요·자동·기본)까지 포함**한 광역 grep으로. 같은 행위(push)를 한쪽은 "금지", 다른 쪽은 "대행 승인 불필요"로 규정하면 문자열이 안 겹쳐 단일 어휘 grep이 상충을 놓친다. cf. #92(문법 변형 광역 grep)의 규약판.

## 참조 대비 개선 편차도 보고 필수 — WARN→OK 같은 호전도 STEP 0 게이트에선 "다름"이니 자의 통과 금지 (#103, GOV-PUSHDELEG-0810 2026-08-10) [process][harness]

**교훈**: STEP 0 게이트가 "참조와 다르면 HALT"일 때, health가 14/1/0→**15/0/0(WARN 해소=개선)**처럼 **좋아진 편차도 "다름"**이다. 개선이라는 자가 판단으로 통과하지 말고 **보고 후 병진 판정을 받는다**(진행 가능하나 보고는 필수). "무충돌 실측은 진행 근거가 아니라 보고 내용"(INC-001 교훈)의 health판 — 편차의 방향이 아니라 편차의 존재가 게이트 대상.

## git branch -d 거부는 HALT 신호 — 손실 0 실측으로 -D 자가 전환 금지 (#104, GOV-CLEANUP-0810 2026-08-10) [process][harness]

**교훈**: `git branch -d`가 "not fully merged"로 거부하면 **정지 신호**로 받는다. `origin/main..브랜치 = 0`(손실 0)을 실측했더라도 **그것을 근거로 `-D` 자가 전환하지 않는다** — 무해 실측은 보고 내용이지 진행 근거가 아니다(INC-001/INC-002 공통). 삭제 자체가 병진 수동 고정(D-BRANCH-DELETE-MANUAL)이므로 거부 조우 시 후보+실측만 보고·대기. `-d`가 로컬 main 미ff로 오탐할 수 있으나(브랜치는 origin/main엔 착지), 그 판단·해소도 병진 몫.

## 예외 승인 원용 시 근거 규약을 정확히 명시 — 무관 규약 원용 금지 (#105, GOV-CLEANUP-0810 2026-08-10) [process][harness]

**증상**: 브랜치 삭제를 집행하며 근거로 SESSION_CONTRACT §H `D-DEPLOY-DELEGATE`를 원용했으나, §H는 **코드 배포 위임 규약**으로 브랜치 삭제와 무관(INC-002). 무관 규약 원용은 "규약 근거 있음" 외양만 갖추고 실제 관할 규약(삭제=병진 수동)을 우회.

**교훈**: 예외 승인·규약 원용 시 **해당 행위를 실제 관할하는 규약을 정확히 지목**한다. 인접·유사 규약(§H=배포 위임 ↔ 삭제)을 근거로 끌어오지 말 것. 행위별 관할 규약 대조를 원용 전에 실측.

## 하드매칭 AST 스캐너의 별칭 사각지대 — burn-down "종결" 선언이 false-negative (#106, BOUNDARY-LLM-CB 2026-08-11) `[architecture][testing][process]`
*(D-NUMBERING-DUP 처방 A 준수 — 비mgmt 자가채번 금지, 번호는 mgmt 채번 시 확정)*

**증상**: BOUNDARY-LLM 경계 테스트(`test_llm_direct_call_boundary.py`)·health_check `외부-LLM 경계`가 **FROZEN_COUNT=0 = "전 LLM 소비처 packages/shared/llm 단일 경유·종결(23→0)"**로 GREEN. 그러나 `apps/market_pulse/llm/client.py`는 여전히 `genai_module.Client(api_key=)`로 Gemini를 **직접 인스턴스화**(+7 소비처가 이 래퍼 소비, chain_sight 교차앱 포함).

**원인**: AST 매처가 `func.attr=="Client" and func.value.id=="genai"`로 **이름 하드매칭**. market_pulse는 `from google import genai as genai_module` 별칭 → `genai_module.Client`가 `func.value.id=="genai_module"`이라 **미검출**. 도구가 "0"이라 말하지만 실제 0이 아님(false-negative). 별칭 도입(커밋 `51046350`)은 우회 의도 아닌 단순 명명이나(ALIAS 판정 (나)), 효과는 은닉.

**교훈**: ⑴ **"도구가 0이라 말함 ≠ 실제 0"** — burn-down/gauge류 스캐너는 매칭 커버리지를 주기적으로 역검증(별칭·재export·간접 참조). ⑵ 이름 하드매칭 대신 **import 바인딩 추적**(`import X as Y` → Y도 검출)으로 이름 무관 검출. 수리 = `_genai_bound_names`로 별칭 집합 추적 후 `func.value.id in genai_names`(BOUNDARY-LLM-CB Part C). ⑶ 스캐너 복제본(테스트 ↔ health_check)은 **양쪽 동시 보강**(규약 2장). ⑷ 검출 후 정직 등재(FROZEN 0→1) → 이관 시 해제(1→0)가 정직한 계정.
## `git branch -d` 거부의 첫 수 = 강제(-D)가 아니라 거부 원인 규명 — 어느 트리 HEAD 기준 판정인지 확인 (#107, GOVCLEANUP-0810-CLEANUP 2026-08-11) [process][harness]
*(D-NUMBERING-DUP 처방 A 준수 — 비mgmt 자가채번 금지)*

**증상**: 격리 worktree 브랜치를 `git branch -d`로 삭제하려 하면 "not fully merged"로 거부. 브랜치는 이미 origin/main에 착지(`origin/main..브랜치 = 0`)했는데도 거부 → "강제 `-D`로 넘어가야 하나?"는 유혹.

**원인·판정**: `-d`의 "merged" 판정은 **명령 실행 트리의 HEAD**(또는 upstream) 기준. 로컬 main 체크아웃이 origin/main보다 뒤처져 있거나 cwd가 엉뚱한 worktree면, origin/main엔 착지한 브랜치도 **그 트리 HEAD 기준으론 미머지로 오탐**(08-10 GOVCLEANUP 사례: cwd 오탐). 삭제 자체가 병진 수동 고정(D-BRANCH-DELETE-MANUAL·[[lesson_branch_d_upstream_refusal]]).

**교훈**: `-d` 거부의 **첫 수는 `-D` 강제가 아니라 거부 원인 규명** — ⑴ `git merge-base --is-ancestor 브랜치 origin/main`로 실제 소진 재확인, ⑵ **어느 트리 HEAD 기준 판정인지** 확인(`git -C <origin/main 추종 트리> branch -d`로 정정 = 강제 없이 해소). 손실 0 실측은 `-D` 근거가 아니라 보고 내용(INC-001/INC-002). cf. 직전 항목 "-d 거부는 HALT 신호"(자가 -D 전환 금지)의 **해소 메커니즘** 보완.

## 버전 마이그레이션 소비 필터 = supersession, naive 버전 필터는 v1-only 과잉배제 (#108, SECB-V2-ROLLOUT 2026-08-12) `[data][process]`

**증상**: 프롬프트/스키마 v1→v2 롤아웃에서 "소비측 v2 필터"를 `filter(prompt_version='v2')`(naive)로 걸자 **v2 미존재 행(v1-only)까지 배제** → 기존 테스트 13건 실패 + 배포~롤아웃 창에 집계·RC·리포트 0 급락(회귀). 이중집계 방지가 아니라 **데이터 과잉배제**. **교훈**: 신·구 버전 **병존(coexist) 소비 필터는 항상 supersession-aware** — "신버전 있으면 신버전, 없으면 구버전"(단위=대체 경계, 예: filing/document). `exclude(old, unit IN (신버전 보유 unit))`. 단일 소스 메서드(`.current()`)로 정의해 naive↔supersession 전환을 1곳에서. 테스트 대량 실패 = 프로덕션 회귀의 프록시(테스트만 고치면 회귀 출하). cf. D-SECB-V2-CURRENT.

## "캡 제거" 정책 변경 시 절단 지점 grep은 `[:N]` 전 변형을 훑어야 (프롬프트만·`[:300]`만 = 은닉 절단 잔존) (#109, SECB-V2-ROLLOUT 2026-08-13) `[data][process]`

**증상**: evidence 300 캡 제거에서 프롬프트 캡 + `[:300]`만 grep해 제거했으나 `validator`의 **`evidence[:297] + "..."`**(다른 슬라이스 리터럴)를 놓침 → v2 롤아웃 1단 497행 중 **143행이 "..."로 끝남**(mid-sentence 절단·verbatim 위배). nf율은 정상(1.21%)이나 **verified 67.6% 저조**로만 발현(절단이 grounding 대조를 조용히 깸). **교훈**: ⑴ 길이/절단 정책 변경은 **프롬프트→파서→validator→save 전 계층** 훑기, grep은 특정 숫자 아닌 `\[: *[0-9]+`·`\.\.\.` 전 변형. ⑵ 롤아웃 게이트에 **길이 max·`endswith('...')` 카운트** 포함(nf율만 보면 놓침). ⑶ 오염분은 coexist(v1 보존)라 v2만 삭제 후 재추출로 복구. cf. D-SECB-V2-LEN.
## 동일 트랙 선행 산출물 발견 시 1줄 확인 후 진행 — 의도적 정련인지 중복 집행인지 상신 (#110, SECB-VB-ABSORB-0811 2026-08-11) `[process][harness]`
*(D-NUMBERING-DUP 처방 A 준수 — 비mgmt 자가채번 금지)*

**증상**: G1.5 분해 지시서 집행 중 동명 목적 스크립트·보고서·사전 지시서가 **이미 origin/main에 착지**(4d0ed3b5)돼 있음을 발견. 지시서가 참조값(437)을 인용 = 그 산출물 출력값 → 선행 존재를 알고도 재발주한 정황.

**교훈**: 지시서 집행 초입에 **동일 트랙 선행 산출물을 grep으로 census**하고, 있으면 ⑴ 지시서가 그 출력을 참조하는가(=디렉터 인지 하 의도적 정련) ⑵ 분류·파일명이 **차분(delta)인가 중복인가**를 실측해 **1줄 상신** 후 진행. 판별 근거 = 지시서의 참조값 출처·신규 분류축(예: 소문자 완화 = 선행 미실시)·파일명 구분. 무판별 병렬 산출물 생성은 원장 혼선. cf. [[feedback_spec_infeasible_surface_before_substitute]].

## 원격 세션 브랜치는 rebase 후 갱신하지 않는다 — force 회피, HEAD:main 직행 (#111, SECB-VB-ABSORB-0811 2026-08-11) `[process][git][harness]`

**증상**: 세션 브랜치를 origin/main에 union rebase(흡수)하면 커밋 해시가 재작성됨. 이미 push된 원격 세션 브랜치를 갱신하려면 `push --force`가 필요 → force 유발.

**교훈**: rebase 흡수 후 **원격 세션 브랜치를 갱신하지 않는다**. 착지는 `git push origin HEAD:main`(main으로 직행 ff-push) — 원격 세션 브랜치(구 해시)는 **미갱신 잔존**시키고 **수동 삭제 목록(D-BRANCH-DELETE-MANUAL)** 으로 넘긴다. 이렇게 하면 rebase가 있어도 **force 필요 상황 자체를 만들지 않는다**(D-PUSH-DELEG (iii) 준수). 08-11 SECB-G15 착지에서 확립(D-PUSHDELEG-PROVE 3차 GREEN).

## SEC EDGAR 8-K 원문 다운로드 = submissions primaryDocument 직접 URL (디렉토리 스크래퍼 `//index.htm` 404) (#112, CS-P2-8K 2026-08-13) `[data][sec]`

**증상**: `SECEdgarClient.download_8k_text`가 filing 디렉토리 인덱스(`.../{acc}/`)를 스크래핑해 primary doc 링크를 찾는 경로가 `//index.htm` 404 다발(표본 20/20 실패). CIK zero-padding·디렉토리 리스팅 형식 취약.

**해결**: submissions JSON의 `primaryDocument[i]`를 직접 사용 → `https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nodash}/{primary}` (CIK leading-zero 제거). 8-K 다운로드 20/20·885건 실패 0. CS-P2-8K는 로컬 헬퍼로 우회(공유 client 무접촉·수리는 TASKQUEUE `P28K-CLIENT-FIX`). 10-K는 `download_10k_text`가 primary_document 직접 사용이라 무관.
## 모듈 이관 시 소비자 전수 grep 범위에 `tests/` 포함 — 누락 소비자의 import 깨짐이 '선존 실패'로 위장 (#113, MPS-1-LAND 2026-08-13) `[testing][boundary][process]`
*(D-NUMBERING-DUP 처방 A 준수 — 비mgmt 자가채번 금지)*

**증상**: 모듈 이관(예: BOUNDARY-LLM-CB `apps/market_pulse/llm/client.py`→`packages/shared/llm/legacy_gemini.py`)에서 소비자 import를 일괄 갱신할 때 **`tests/` 하위 소비자를 누락**. 앱 코드 9곳은 갱신됐으나 10번째 소비자(테스트)가 구 경로를 유지 → `ImportError: cannot import name 'client'`. 이 실패가 다음 세션엔 **"선존 실패"로 위장**(내 diff 무관으로 오판)돼 방치되고, known-fail 레지스트리에도 미등록으로 남는다.

**교훈**: 소비자 전수 grep 범위에 **`tests/`를 명시**한다(`grep -rn '<구 경로>' apps/ packages/ tests/`). 이관 완료 판정 = 앱+테스트 양쪽 0건. **위장 식별법**: "선존 실패"로 분류하기 전에 실패가 **모듈 부재/import 오류**면 이관 drift 의심(코드 로직 실패와 구분). 모킹 대상도 함께 정합 — 호출시점 로컬 import(`def f(): from X import g`)는 **소스 모듈 X를 패치**해야 monkeypatch가 유효(소비 모듈 패치는 무효). cf. BOUNDARY-LLM-CB([[project_boundary_llm_track]]).

## `backfill_v2_a1`은 `--econ-only` 없으면 심볼(MarketIndexPrice)까지 백필 — `--series-id`는 econ만 스코프 (#114, INC-MPS-BACKFILL-SCOPE 2026-08-14) `[data][ops]`
*(D-NUMBERING-DUP 처방 A 준수 — 비mgmt 자가채번 금지)*

**증상**: 단일 econ series 백필 의도로 `backfill_v2_a1 --series-id DTWEXBGS --from 2023-07-01`(--econ-only 없이) 실행 → **섹터 ETF 11종 MarketIndexPrice에 각 +689행(총 7,579행) 의도 밖 삽입**. `--series-id`는 **Economic 파트만** 스코프하고 **Market(심볼) 파트는 무스코프**(전 섹터 ETF 대상). **원인**: 커맨드가 econ+symbol 이중 타깃이며 위험한 기본값(심볼 전량)이 --series-id로 안 좁혀짐. **해결**: econ만 원하면 **`--econ-only` 필수**. (무해 판정 근거: SPY만 purge 예외라 섹터 ETF 초과분은 롤링 365일 purge로 자연 소멸.)

## 백필 프리뷰는 수치 대조 **전에** 쓰기 대상 테이블 전수를 대조 — grep 필터가 파트를 가린다 (#115, INC-MPS-BACKFILL-SCOPE 2026-08-14) `[ops][process]`
*(D-NUMBERING-DUP 처방 A 준수 — 비mgmt 자가채번 금지)*

**증상**: `backfill_v2_a1 --dry-run` 출력에 `[DRY-RUN] Economic (1): [...]` + **`[DRY-RUN] Market (11): [...]`** 두 파트가 모두 표시됐으나, 출력을 `grep -iE "series명|row|건"`으로 필터링해 **Market 파트를 화면에서 놓침** → 심볼 백필을 미대조하고 실행. **교훈**: 프리뷰(dry-run) 검토는 **grep 필터 없이 전체 출력**을 보고 **쓰기 대상 테이블/엔티티 전수**(Economic + Market 등)를 확인한 뒤 실행. 프리뷰 필터링은 "수치만 보고 스코프를 안 보는" 함정. cf. INC-MPS-BACKFILL-SCOPE.

## `launchctl kickstart -k`가 관리 이탈 orphan을 못 죽여 EADDRINUSE — 서빙 교체 실패(구 빌드 계속) (#116, D-MPS-OPS-WEBSYNC 2026-08-14) `[infra][ops]`
*(D-NUMBERING-DUP 처방 A 준수 — 비mgmt 자가채번 금지)*

**증상**: 웹 런타임 리빌드 후 `launchctl kickstart -k com.stockvis.web-frontend`로 서빙 교체 시도 → 새 인스턴스가 `Error: listen EADDRINUSE :::3000`로 기동 실패, **구 빌드가 계속 서빙**(StressCard 미표시). `launchctl list`가 `-  <exit>  <label>`(관리 PID 없음). **원인**: 이전에 launchd가 관리를 놓친 **구 프로세스가 PPID→1로 reparent**돼 :3000을 계속 점유(예: npm start + next-server 쌍, 며칠 전 기동). kickstart는 **launchd가 추적하는 인스턴스만** 재기동하므로 orphan은 살아남아 포트 점유. **판정**: `lsof -i :3000 -sTCP:LISTEN`의 PID 기동시각(`ps -o lstart`)이 **오늘이 아니면 orphan**. **해결**: orphan(부모 npm start + 자식 next-server) `kill -TERM` → KeepAlive 자동재기동 or 클린 kickstart → 새 프로세스(오늘 기동·새 .next)가 :3000 단독 바인딩·launchd 관리 복구. **검증**: 리스너 PID 기동시각=지금 + `lsof -ti :3000` 단일 + 서빙 프로세스 cwd=동기 트리. cf. DEPLOY-RUNBOOK.

> **3번째 실증 (api :18765 daphne, D-MPS-OPS-APISYNC 2026-08-19)**: 동일 패턴이 API 관문에서도 발생. 관리 이탈 고아 daphne(PID 63228, 08-13 09AM~)가 :18765 점유·stress 라우트 없는 구코드 응답 → `/api/v2/market-pulse/regime/stress` 404(StressCard 에러). launchd `com.stockvis.web`은 포트 막혀 대기. 판정 동일(`lsof -i :18765` 기동시각·ppid). 해소 = 08-18 14:57 병렬 세션 `sv sync`(worker_sync)가 고아 사망+ff 동기+kickstart로 정상화. **3건 공통 근인 = 관리이탈 고아의 포트 점유** → DEPLOY-RUNBOOK 런북 1장=고아 스윕으로 성문화.

## `git branch -d` 거부 근본원인 — HEAD:main 직행 push가 세션 브랜치에 upstream을 안 남겨 stale primary HEAD 기준 오탐 (#117, MGMT-LEDGER-1 2026-08-19) [git][process][harness]

**증상**: 세션 브랜치를 `git push origin HEAD:main`(직행)으로 착지시킨 뒤 `git branch -d <세션브랜치>`가 "not fully merged"로 거부. 브랜치는 origin/main에 완전 포함(`origin/main..브랜치=0`)인데도 거부. 08-18 sess-dss-impl1·sess-dss-recon1 등 **3회 재현**.

**원인**: HEAD:main 직행 push 체계는 세션 브랜치에 **upstream을 남기지 않는다**(`push -u` 미사용). upstream 없으면 `git branch -d`는 **명령 실행 트리의 현재 HEAD** 기준으로만 머지 판정. primary 체크아웃이 stale 브랜치(예 `cca67275`)에 정체돼 있으면 그 HEAD가 브랜치를 미포함 → **미머지 오탐**.

**해소**: `git branch --set-upstream-to=origin/main <브랜치>` 후 `git branch -d <브랜치>` 재시도 → `-d`가 **origin/main 기준 머지 판정**(브랜치가 조상=포함) → force 없이 삭제. 또는 origin/main 체크아웃 트리에서 실행. **`-D` 전환 절대 금지**(손실 0 실측은 진행 근거 아님 — D-BRANCH-DELETE-MANUAL 상호 참조). cf. #104(-d 거부=HALT 신호)·#107(첫 수=원인 규명). -D 통산 0회 유지 실증.

## drf-spectacular OpenApiSerializerExtension target_class가 pre-monorepo 경로면 컴포넌트 무음 드롭 (채번 대기, D1-SCOREBOARD 2026-08-20) [openapi][monorepo][frontend]

**증상**: `manage.py spectacular` 재생성 시 `CoachE1~E6` 등 명명 컴포넌트가 스키마에서 **경고 없이 사라짐**. 커밋된 (stale) schema.yml에는 있었으나 재생성본에는 path만 남고 `responses: No response body`. FE `lib/coach/types.ts`가 `Schemas['CoachE1Response']`를 참조 → tsc가 phantom 참조로 대량 실패(coach 6페이지·hooks·api·9 테스트 전파).

**원인**: 스키마는 passthrough 앵커 serializer + `OpenApiSerializerExtension`(target_class 문자열 매칭)으로 명명 컴포넌트를 방출한다. 모노레포 이전 후 `openapi_extensions.py`의 target_class가 구 경로 `portfolio.api.serializers.*` 잔존 → serializer 실제 `__module__`(`apps.portfolio.api.serializers.*`)과 불일치 → extension 미매칭 → 컴포넌트 무음 드롭. `advisory_schema.py`는 이미 `apps.` 접두라 정상(대조).

**해소**: extension target_class = **serializer의 실제 `__module__` 전체 경로**(모노레포 `apps.` 접두 필수). 재생성 전 `git show HEAD:schema.yml | grep -c <컴포넌트>` vs 재생성본 대조로 드롭 선탐지. 규칙은 이미 memory `reference` + `advisory_schema.py` 주석에 명시 — 신규 extension 추가 시 준수. cf. DECISIONS D-COACH-SCHEMA-EXT-PATH.

## LAND health DoD를 절대값(0W/0F)으로 두면 시간 부패형 검사에 교착 — 세션 시작 기준선 대비 델타로 판정 (#118, LAND-SCAN-B1 2026-08-24) `[process][harness]`

**증상**: LAND 세션 양식이 STEP 4 health를 **절대값 0 WARN/0 FAIL**로 요구했으나, LAND-SCAN-B1(08-24) 착지 후 `health_check.py`가 **PROGRESS.md 86h 미갱신(>72h) FAIL**을 보고. 이 FAIL은 착지 diff(dashboard 17파일)와 **무관** — 경과 시간(마지막 PROGRESS 갱신 = 08-20 BATCH-35)으로 72h 임계를 넘긴 **시간 부패형** 검사다.

**원인**: LAND 세션은 **메타 4종 변경 금지**(코드 착지 전용)이므로 PROGRESS stale을 **수리할 수 없다**. 절대값 0/0 요구는 "LAND가 못 고치는 검사"를 게이트에 넣어 **구조적 교착**을 만든다. 유사 검사: DECISIONS 갱신일·PROGRESS stale 등 시간 임계 기반 전부 동일 위험.

**해소**: LAND health DoD = **절대값 아닌 세션 시작 기준선 대비 델타 0**. LAND 양식 STEP 0에 health 기준선 측정을 추가하고, STEP 4는 "신규 FAIL/WARN 0(= 착지가 새 결함을 만들지 않음)"으로 판정. 시간 부패형 FAIL은 착지 무관으로 명시·soncan(mgmt PROGRESS 갱신)에 회부. cf. [[lesson_land_health_measure_in_target_tree]] · MGMT-BATCH-36이 본 stale 해소.

---

## 부존재 판정 규율 — 절단 목록·이름 grep만으로 '없음' 판정 금지 (2026-08-24, EVT-SURVEY 회고)

**증상**: 조사에서 "X가 없다"고 단정했으나 실제로는 존재. 오판이 후속 결정의 잘못된 전제가 됨.

**사례 2건 (EVT 트랙 조사)**:
- **EVT-0 beat drift 오경보**: `PeriodicTask` 목록을 `head -50`으로 잘라 보고 "`update-economic-calendar` DB 미등록(#28 drift)"로 판정 → 실제로는 알파벳순('u')이 절단선 뒤라 잘렸을 뿐. DB에 정상 등록·가동 중(EVT-1 재측정에서 last_run 실측으로 정정).
- **EVT-1 shared 모델 0건 오판 소지**: 이름 패턴 grep(`class *Calendar*`)만으로 "shared에 관련 모델 없음"에 근접 → 실제 packages/shared는 ~28개 모델 보유(StockSplit 포함). 이름 grep은 명명이 다르면 놓침.

**규율**: 부존재('없음'/'0건') 판정 전 반드시 —
1. **전수성 검증**: 목록을 `head -N`으로 자르지 말고 `wc -l` 대조 또는 필터+정렬로 전량 확인. 절단 출력으로 '없음' 단정 금지.
2. **의미 기반 재탐색**: 이름 패턴 grep이 비면 테이블명·db_table·행 존재(SQL)·소비처 grep 등 **다른 축**으로 교차 확인.
3. 판정을 후속 결정의 전제로 쓰기 전 **행이 증거**(DB 실행 수·last_run 타임스탬프)로 재확인.

---

## 지시서 파일 의존물 규율 — 배치 경로 + §0 존재 확인 명문화 (2026-08-24, EVT-IMPL-1 회고)

**증상**: 지시서가 외부 전달 파일(설계 앵커 등)에 의존하는데 **정확한 배치 경로가 미명시**되면, 실행 세션이 파일을 못 찾아 §0 게이트에서 HALT. 착수 지연.

**사례**: EVT-IMPL-1 §0-5가 "사용자 전달 파일 event_calendar_design.md"만 언급하고 **어디에 두는지(Desktop? 채팅 첨부?)를 미명시** → 실행 세션이 Desktop·Downloads·scratchpad·git 전수 탐색 후 부재 확인 HALT. 사용자가 채팅에 전문 붙여넣어 재개.

**규율**: 지시서가 의존 파일을 요구할 때 —
1. **정확한 배치 경로 명시**: "`~/Desktop/<파일명>`에 저장" 또는 "채팅에 전문 첨부" 등 전달 방식을 못박는다.
2. **§0에 존재 확인 스텝**: 착수 전 `test -f`/헤더 grep으로 존재·버전을 검증하고, 부재 시 HALT 조건으로 명시.
3. 의존물이 repo 내 산출물이면 커밋 해시·경로를 함께 적어 재현 가능하게 한다.
## health WARN 유형 판정 기준 — 환경·동기화 신호성=보고 후 진행 / 신규 발생 WARN·FAIL=명목 HALT (채번 후보, DSS-FLAT-OBS-1 2026-08-24) [harness][process][ops]
## health WARN 유형 판정 기준 — 환경·동기화 신호성=보고 후 진행 / 신규 발생 WARN·FAIL=명목 HALT (#119, DSS-FLAT-OBS-1 2026-08-24) [harness][process][ops]

health WARN 유형 판정 기준 — (i) 환경·동기화 신호성 WARN (예: 미푸시 세션 상태로 인한 sync 계열)은 보고 후 진행 가능. (ii) 시스템 검사에서 신규 발생한 WARN/FAIL은 명목 HALT. STEP 0 보고에 유형 구분을 명시한다. 실증: MGMT-LEDGER-1 STEP 0-2 (08-19).

## 비-mgmt 세션 지시서의 common-bugs #NN 사전 지정 금지 — '채번 후보'로 작성, 번호는 mgmt 배치 실측+1 (#120, DSS-FLAT-OBS-1 2026-08-24) [harness][process][git]

비-mgmt 세션 지시서에 common-bugs #NN 번호 사전 지정 금지. 비-mgmt 세션은 '채번 후보'로 작성하고 번호 부여는 mgmt 배치에서 실측+1로 수행(D-NUMBERING-MGMT-ONLY·훅 가드 준수). 실증: DSS-FLAT-OBS-1 커밋 2 훅 차단 (08-24).
## 한 화면이 마운트에 N개 엔드포인트 동시 fetch + RQ 재시도 증폭 + 하드리프레시 반복 → throttle 초과 → 429 캐스케이드 → 게이팅 쿼리 isError → 전면 에러 (채번 대기, INC-P16-1 2026-08-24) `[frontend][infra][performance]`

**증상**: market-pulse-v2 페이지를 하드리프레시로 반복 로드하면 어느 순간 화면 전체가 "데이터를 불러오지 못했습니다"로 전환. 단건 curl로는 재현 안 됨(200 정상) — 브라우저 경로(동시 다엔드포인트 + refresh 누적)에서만 발생.

**원인**: 페이지 마운트 시 **동시 4엔드포인트**(overview·regime/stress·regime/analog·playbook) fetch. 각 쿼리는 TanStack Query 전역 `retry: 2`로 실패 시 최대 3배 요청 증폭. 하드리프레시를 빠르게 반복하면 분당 요청이 `market_pulse_user` throttle(당시 60/min)을 초과 → 429. **429에도 RQ가 재시도**하면 rate window 안에서 예산을 더 태워 429가 눈덩이(캐스케이드). 게이팅 쿼리(useOverview)가 isError로 떨어지면 page.tsx가 **전면 에러**로 게이팅. 1.6-S1이 4번째 엔드포인트(playbook)를 추가해 footprint를 3→4로 올린 것이 촉진자(근인은 선존 fragility).

**해소(A+B+C 3중)**: **A** 전역 retry를 함수형(`shouldRetryQuery`)으로 — 429는 즉시 무재시도(그 외 실패는 기존 최대 2회 보존). 429에 재시도 안 함이 정답(백오프해도 window 내 재소비). **B** fold 아래 카드(PlaybookCardContainer)는 `useInViewOnce`로 뷰포트 진입 시점까지 fetch 지연 → 초기 동시 요청 감소(렌더 불변, fetch 시점만 늦춤). **C** `market_pulse_user` 60→120/min(예산 2배 보험). **재발 방지 규칙**: 신규 홈/랜딩 엔드포인트 추가 시 = ⑴ lazy(뷰포트 진입 fetch) 우선 검토 or ⑵ throttle 예산 재점검 필수. 단건 curl은 이 유형을 구조적으로 못 잡음 → 브라우저 경로 스모크(SMOKE-BROWSER-PATH) 필요. DRF ScopedRateThrottle은 429에 Retry-After 세팅 → 향후 Retry-After 존중 재시도로 고도화 여지. cf. common-bugs #23(FMP 402)·#41(모듈 상수 변경=재기동 필수).

---

## 지시서-앵커 drift 규율 — 지시서 작성 시 앵커 하드 요건 체크리스트 대조 필수 (2026-08-27, EVT-IMPL-2 회고)

**증상**: 설계 앵커의 **하드 요건이 구현 지시서에 미배선**되면, 코드는 요건을 flag만 하고 실제 방어를 안 해 무언 데이터 소실이 남는다. dry-run에서야 포착.

**사례**: EVT-IMPL-2가 앵커 §3의 캡 방어 원안("창 이분 재시도")을 STEP 3에 미배선(detect_truncation을 flag-only로 단순화하고 재시도를 미연결) → dry-run 실측에서 earnings chunk2(45일)가 4,000 캡 도달·앞 ~24일 소실 → HALT로 포착 → 보정1(적응형 이분 배선)으로 복원.

**규율**:
1. **지시서 작성 시 앵커 하드 요건 체크리스트 대조**: 앵커의 "하드 요건·게이트·불변" 항목을 지시서 STEP에 1:1 매핑했는지 확인. flag만 하고 방어 미배선인 항목 색출.
2. **dry-run은 하드 요건의 실증 게이트**: 계절·규모 의존 요건(밀도·캡 등)은 실측(dry-run)으로만 드러난다 → 실측 전 "안전" 단정 금지.
3. drift 발견 시 = 신규 결정이 아니라 **앵커 원안 복원**(보정)으로 처리, 기존 커밋 유지하고 이어서 배선.
## 경계 red 착지 회귀 — 세션 종료 전 health·아키텍처 가드 GREEN 확인은 착지 조건 (#121, BOUNDARY-TRIAGE-1 2026-08-27) [process][harness][ops]

경계 red 착지 회귀 — 세션 종료 전 health·아키텍처 가드 GREEN 확인은 착지 조건. 위반이 불가피하면 KNOWN_VIOLATIONS 동결+소진 등재를 착지 커밋에 동반한다(등록 없는 red 착지 금지). 실증: 7ec24c62(08-26) → BOUNDARY-TRIAGE-1 동결(08-27).
## "속성만 추가" 슬라이스에서 wrapper `<div>`를 끼우면 행위보존이 깨진다 — 앵커는 대상 컴포넌트 루트에 속성으로, 증명은 diff-modulo-token으로 (채번 후보, GUIDE-S1 2026-08-27) `[frontend][process][harness]`

**증상**: "기존 화면 렌더 결과 불변" 계약의 슬라이스에서 앵커(`data-guide` 등)를 붙이려고 페이지 JSX에 `<div data-guide="..."><Component /></div>` 래퍼를 끼움. 속성만 넣은 것 같지만 **DOM 트리가 바뀐다** — 대상이 grid/flex 직계 자식이면 `lg:col-span-2` 같은 클래스가 래퍼에 먹혀 레이아웃이 조용히 깨지고, `space-y-*` 간격·`:first-child` 계열 셀렉터도 어긋난다. 테스트가 통과해도 시각 회귀는 남는다.

**규율**:
1. 앵커는 **대상 컴포넌트의 최외곽 요소에 속성으로만** 부여한다(`<div data-guide="x" className="기존값">`). 래퍼 신설 금지. 컴포넌트 파일을 건드리게 되더라도 그쪽이 옳다.
2. props로 넘기면 안 된다 — `<PortfolioSummary data-guide="..."/>`는 컴포넌트가 스프레드하지 않으면 **DOM에 도달하지 않고 조용히 사라진다**(무소음 실패).
3. 증명은 눈이 아니라 기계로. 변경 파일마다 `git show <base>:<path>`와 **속성 토큰만 제거한 현재 파일**을 문자열 비교해 전부 일치하면 "삽입 외 변경 0"이 증명된다:
   ```python
   strip = re.compile(r'\s*data-guide="[^"]*"')
   assert strip.sub('', open(f).read()) == git_show(base, f)
   ```
   GUIDE-S1 실증: 앵커 편집 12파일 전건 통과.
4. 데이터의 앵커 목록과 소스의 속성이 따로 움직이면 배지가 **말없이 사라진다** → 양방향 집합 일치 테스트(선언⊆소스, 소스⊆선언, 파일 중복 금지)를 함께 심는다.

## 이 repo의 eslint `react-hooks/set-state-in-effect` — 신규 컴포넌트의 localStorage 읽기·레이아웃 측정은 effect 본문 setState 금지 (채번 후보, GUIDE-S1 2026-08-27) `[frontend]`

**증상**: 하이드레이션 안전 관용구(`useEffect(() => { setX(localStorage.getItem(k)) }, [])`)를 새 컴포넌트에 쓰면 lint 오류. 기존 `Header.tsx`·`MobileNav.tsx`가 같은 패턴으로 **선존 오류를 이미 갖고 있어** 전체 lint 총계만 보면 자기 신규분이 묻힌다.

**해소**:
- 외부 저장소(localStorage) 구독 → `useSyncExternalStore(subscribe, clientSnapshot, () => 서버기본값)`. 같은 탭 쓰기는 `storage` 이벤트가 안 뜨므로 **모듈 수준 리스너 Set으로 직접 통지**. 서버 스냅샷을 "숨김" 쪽으로 두면 하이드레이션 불일치도 함께 해결된다.
- 레이아웃 측정(`getBoundingClientRect`) → effect 본문이 아니라 `requestAnimationFrame` 콜백에서 setState. 규칙이 "콜백 안 setState"는 허용한다. 단 테스트는 다음 프레임을 기다려야 하므로 `await waitFor(...)`로 바꾼다.
- prop 변화에 따른 리셋은 effect가 아니라 **렌더 중 이전값 비교**(`if (last !== cur) { setLast(cur); ... }`) 패턴.

**측정 규율**: 신규분 판정은 총계가 아니라 **기준선 대조**로. `git stash -u` → `npm run lint` → pop 하여 origin/main 총계와 비교(GUIDE-S1: 327 → 327, 순증 0).

## 네비 링크의 href를 바꾸면 active 표시가 컴포넌트마다 갈린다 — 파생 판정식(startsWith(item.href)) vs 하드코딩 prefix (채번 후보, GUIDE-S1C 2026-08-27) `[frontend]`

**증상**: Market Pulse 네비 목적지를 `/market-pulse` → `/market-pulse-v2`로 바꿨더니, **구 경로에 직접 접근했을 때 활성 표시가 두 컴포넌트에서 달라졌다.**
- `Header.tsx`: 판정식이 `pathname.startsWith(item.href)` — href에서 **파생**되므로 href를 바꾸면 판정도 같이 바뀐다 → 구 경로에서 **비활성**.
- `MobileNav.tsx`: 판정식이 `active: pathname.startsWith('/market-pulse')` — **하드코딩 prefix**라 href와 무관 → 구 경로에서도 **활성**.

한 줄만 고쳤는데 두 표면의 동작이 갈리고, 새 경로(`/market-pulse-v2`)에서는 둘 다 활성이라 **정상 동선만 보면 발견되지 않는다**. 구 경로 직접 접근이라는 잔여 경로에서만 드러난다.

**규율**:
1. 네비 항목의 href를 바꿀 때는 **그 항목의 active 판정식이 href 파생인지 하드코딩인지 전 표면에서 확인**한다(Header·MobileNav·사이드바·브레드크럼 등). "링크 한 줄"이 아니다.
2. 구 경로를 존치(리다이렉트 없이)하는 전환에서는 **구 경로 직접 접근 시의 활성 표시를 테스트로 고정**한다. 통일할지 말지는 은퇴 결정과 함께 — 임시로 코드를 맞춰 두면 은퇴 시 되돌릴 근거가 사라진다.
3. 활성 여부 단언은 **클래스 토큰 일치**로. `className.toContain('text-blue-600')`은 `hover:text-blue-600`에 **오탐**한다 → `className.split(/\s+/).includes('text-blue-600')`.

**부기(같은 세션 실측)**: 계약 테스트에 임의 상한을 박으면 나중에 **승인된 콘텐츠를 자기 테스트가 막는다**. GUIDE-S1이 `regions 3~5개`로 둔 상한이 S1C에서 승인된 7영역 문구를 red로 만들었다 — 상한을 7로 완화하고 "S1의 5는 임의값"임을 주석에 남겼다. 계약 테스트의 수치 경계는 **근거가 있을 때만** 박을 것.

## daphne access log(stdout·블록버퍼) vs error log(stderr·라인버퍼) desync → 로그 실시간 판독 시 "전부 200" 착시 (채번 대기, INC-P16-2/CLOSE 2026-08-27) `[infra][observability][ops]`

**증상**: 09:13 인시던트 로그 판독 시 `web.log`(access)는 09:13:20에서 끊겨 market-pulse 요청이 "전부 200·429 0건"으로 보였으나, `web-error.log`(Django logger)에는 같은 시각 09:13:21~23에 429("Too Many Requests") 18건이 존재. 두 소스가 429 경계에서 상반된 그림 → 잘못된 1차 판정 위험.

**원인**: `com.stockvis.web.plist`가 daphne의 stdout=`web.log`(access), stderr=`web-error.log`로 분리. **비-TTY에서 Python stdout은 블록 버퍼링** → access 라인이 청크 단위로 밀려, 읽는 순간 버퍼 미flush분(09:13:21~)이 파일에 아직 안 보임. stderr는 라인/무버퍼라 즉시 기록. = 데이터 유실이 아닌 **버퍼 desync**.

**해소**: `scripts/daphne-web.sh`에 `export PYTHONUNBUFFERED=1`(exec 직전) → stdout 즉시 flush. 랜딩 후 재기동 필요(#41). **판독 규칙**: 인시던트 로그 대조 시 access·error 두 소스를 **항상 교차** 확인(한 소스의 절단을 다른 소스가 메움). cf. INC-P16-2 부수건.

## HTML 문구 매칭으로 화면 상태를 판정할 때 — 부분 토큰 마커와 Next RSC 인라인 페이로드가 전 라우트를 거짓 fail로 만든다 (채번 후보, AGENT-S1 2026-08-27) `[frontend][ops][agent]`

**증상**: 야간 점검 러너가 "화면에 실패 문구가 노출됐는가"를 SSR HTML 문자열 포함으로 판정했더니 **점검 대상 7개 라우트가 전부 fail**로 나왔다. 실제로는 전부 정상이었다. 두 번 연속 다른 원인으로 재현됐다.

**원인 ⑴ — 부분 토큰 마커**: 실패 마커에 `"500"`을 넣음. tailwind 클래스(`text-gray-500`)·티커명(`SP500`)·인라인 CSS(`font-weight:500`)에 전부 걸린다. 마커는 **화면에 실제로 뜨는 문구 전체**여야 한다.

**원인 ⑵ — Next.js RSC 인라인 페이로드**: `"This page could not be found"`로 바꿨더니 **여전히 7/7 fail**. Next.js는 RSC 플라이트 데이터와 not-found 컴포넌트 문자열을 `self.__next_f.push(...)` 형태로 **모든 페이지의 인라인 `<script>`에** 실어 보낸다. 원문 HTML에 매칭하면 정상 페이지에서도 404 문구가 잡힌다.

**해소**: 판정 전 `<script>`·`<style>` 블록을 제거하고 태그를 벗긴 **가시 텍스트에만** 매칭한다.
```python
_SCRIPT_OR_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
text = re.sub(r"<[^>]+>", " ", _SCRIPT_OR_STYLE.sub(" ", html))
```
**규율**: ⑴ 마커는 12자 이상 전체 문구만(테스트로 강제 — `test_error_markers_have_no_short_tokens`). ⑵ 셸 마커(있어야 정상)도 같은 가시 텍스트로 판정. ⑶ **매일 발송되는 자동 점검에서 거짓 경보는 곧 그 점검의 폐기**다 — 임계·마커는 도입 전에 실데이터로 1회 돌려 오탐 0을 확인하고 넣는다.

**부기**: SSR HTML로는 **클라이언트 렌더 데이터가 안 보인다**. 대시보드·모니터·포트폴리오는 마운트 후 fetch하므로 HTML에는 셸/로딩만 있고 `data-guide` 앵커도 없다. 따라서 HTTP 전용 점검의 사거리는 "셸이 뜨는가 · 에러 문구가 없는가"까지이고, 데이터 유무는 **API·baked JSON을 따로 봐야** 한다(AGENT-S1이 그렇게 나눈 이유).
