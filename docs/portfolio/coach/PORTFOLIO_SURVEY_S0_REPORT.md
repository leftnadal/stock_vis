# PORTFOLIO 전수조사 보고서 (S0 · READ-ONLY SURVEY)

> 세션 종류: SURVEY (read-only). 코드 변경·커밋·마이그레이션 생성 없음. 본 보고서 1개 파일만 신규 생성(커밋 안 함).
> 작성일: 2026-07-10
> 지시서: `docs/portfolio/coach/PORTFOLIO_SURVEY_S0_INSTRUCTION.md`

---

## 1. 계약 헤더 + STEP 0 측정값

### SESSION_CONTRACT 헤더
- **세션 종류**: SURVEY (read-only)
- **범위**: `apps/portfolio` + frontend의 portfolio/coach 라우트·컴포넌트 + 관련 하네스 항목
- **baseline**: 아래 STEP 0 참조

### STEP 0 — ground truth 측정값

| 항목 | 실측값 | 실행 명령 |
|---|---|---|
| 세션 working tree | `/Users/byeongjinjeong/Desktop/stock_vis` | `git worktree list` |
| 세션 HEAD | **`66c364d`** (detached HEAD) | `git status` / `git rev-parse HEAD` |
| origin/main | **`307306d`** | `git log --oneline -5 origin/main` |
| 세션 HEAD vs origin/main | **ahead 0 / behind 25** ⚠️ | `git rev-list --left-right --count 66c364d...origin/main` → `0  25` |
| working tree dirty | **tracked 변경 0** (untracked만: `.superpowers/`, `docs/` 미추적 문서 다수) | `git status` |
| **조사 기준 트리(대체)** | **`/Users/byeongjinjeong/Desktop/sess-main-integrate`** (branch=main, HEAD `307306d`, clean, origin/main과 0/0) | `git -C sess-main-integrate rev-list --left-right --count HEAD...origin/main` → `0  0` |
| health_check | **✅ 12 / ⚠ 1 / ❌ 0** (유일 WARN = "실행 트리가 origin/main 뒤처짐 #47", 나머지 8✅ 유지·shared/LLM 경계 동결 잔여 0) | `python scripts/health_check.py` |

> **STEP 0 핵심 판정**: 세션 트리(`66c364d`)가 origin/main보다 25 커밋 뒤처진 stale 상태(health_check WARN과 일치). 정확한 ground truth 측정을 위해 **조사 전량을 `sess-main-integrate`(=origin/main `307306d`, clean) 트리에서 수행**. 단, `frontend/`와 `apps/portfolio/`는 `66c364d..origin/main` 사이 **변경 파일 0건**임을 `git diff --stat`으로 확증했으므로, node_modules/.env가 필요한 프론트·migration 검증만 Desktop 트리에서 실행(코드 동일성 보장).

### TASKQUEUE portfolio/coach 항목 전수 (명령: `grep -niE "portfolio|coach" TASKQUEUE.md`)

| 항목 ID | 내용 | 상태 |
|---|---|---|
| **PF-TEST** | coach 테스트 `mock.patch("portfolio.…")` → `apps.portfolio.` 경로 수정 (PR7 이관 후 stale mock, `ModuleNotFoundError`). ※지시서는 "5건"이라 표기하나 **실측 43건 fail**(아래 §5) | 🆕 보류 |
| **PF-LEGACY-FE** | `app/portfolio`·`components/portfolio`·`services/portfolio.ts`(레거시 `users.Portfolio` 소비)의 귀속 = portfolio 트랙 vs users·auth 경계 결정 안건 | 🆕 보류 |
| **PF-SCORING** | `tests/scoring/**` 소속 확정(coach scoring 소유권) | 🆕 보류 |
| **PF-LLM-CLIENT** | `apps/portfolio/llm/client.py`(anthropic·google.genai 직접) → `packages/shared/llm` 코어 합성 | 🆕 보류(BOUNDARY-LLM 위임) |
| **COLOR-STAGE2-portfolio** | portfolio 수익=rose/손실=sky 색 전환(5파일 글로벌축 잔존) | 💤 보류(portfolio 트랙 재개 첫 슬라이스 선행) |
| **MP2-CROSS-SURFACE** | cross-surface 통합(대시보드↔chain_sight↔portfolio) | 🔴 게이트(선행 트랙 land 후) |
| **SR (트랙)** | 서비스 리모델링 — Dashboard/Chain Sight/**Portfolio** 3탭 전환. 44일 정체(2026-04-14~) | 미시작 |

---

## 2. §1 — 백엔드 전수: `apps/portfolio` 구조

> 조사 트리: `sess-main-integrate`. 명령: `find apps/portfolio -type f -name "*.py" | sort` (약 150 파일, `__pycache__` 제외).

### 2.1 디렉터리 트리 + 모듈 책임(요약)

- **루트**: `urls.py`(빈 urlpatterns — legacy view 제거 #65, 호환용), `views.py`(빈 deprecated 껍데기), `apps.py`(AppConfig), `models.py`(13개 모델).
- **`api/`** (유일한 실 REST 진입점): `urls.py`(coach e1~e6 POST 6개), `views.py`(`@api_view(["POST"])` 6개, 에러 매핑), `serializers.py`(Request/Response, Pydantic↔DRF), `openapi_extensions.py`.
- **`llm/`**: `client.py`(`LLMClient` — Gemini/Anthropic 통합, 1회 재시도+폴백, 비용가드, shared 경유), `token_budgets.py`(진입점별 input budget), `budget_estimator.py`, `cost_guard.py`(싱글턴 캡), `cost_ledger.py`(append-only 원장), `eval_metrics.py`, `exceptions.py`, `mocks.py`, `parsers.py`.
- **`measure/`**: `estimator_v3.py`(진입점×모델 토큰 회귀, `DEFAULT_MODEL="claude-haiku-4-5"`), `message_dumper.py`.
- **`metrics/definitions/`**: `presets.py`(12 preset 메타 SSOT), `metrics.py`(지표 카탈로그), `preset_metrics.py`, `versions.py`.
- **`schemas/`**: 12개 Pydantic 계약 (holding/diagnostic/commentary_input·output/e4_conversation/user_profile 등).
- **`services/`**: `coach/e1~e6_service.py`(`run_eN_coach`), `coach/prompt_builder.py`, `e1_garp.py`·`e2_diagnostic_card.py`·`e3_metric_comment.py`·`e3_portfolio_service.py`·`e5_adjustment_parser.py`·`e6_comparison.py`(진입점별 LLM 호출+파싱), `scoring/base.py`(`ScoringEngineBase`), `scoring/preset_spec.py`, `scoring/presets/{value,growth,income,factor,special}.py`.
- **`prompts/`**: `tier0/`(공통 시스템 프롬프트), `e1~e6/`·`e3_portfolio/`·`rationale/`(진입점별 builder), `e4/`(tier1/2/3 대화 depth 분기).
- **`migrations/`**: `0001_initial.py` 단일(13 모델 전체).

### 2.2 DRF 엔드포인트 전수 (`api/urls.py`, config prefix `/api/v1/`)

| URL | View | 메서드 | 권한 | 서비스 |
|---|---|---|---|---|
| `coach/e1/`~`coach/e6/` | `views.coach_e1`~`coach_e6` | POST | `IsAuthenticated` | `run_e1~e6_coach` |

- **`/api/v1/coach/e1~e6` 6개 전부 실존**(`api/urls.py:19-24`). 그 외 엔드포인트 **없음**.
- 공통 시그니처: query `?provider=haiku|sonnet|anthropic`(기본 haiku). `_VALID_PROVIDERS=("haiku","sonnet","anthropic")` — **"gemini"는 뷰에서 400 거부**.
- 권한: Slice 16 Step 0-B #70에서 6개 뷰 전부 `AllowAny → IsAuthenticated` 통일.
- 에러 매핑: 검증 400 / `LLMBudgetExceededError` 429 / `LLMError` 502 / 기타 500(스택트레이스 비노출).

### 2.3 모델 전수 (`models.py`, 13개, app_label=`portfolio`, db_table 기본 `portfolio_*`)

| 모델 | 외부 FK / 관계 |
|---|---|
| `Wallet` | **FK→AUTH_USER_MODEL**(user, CASCADE) |
| `WalletHolding` | FK→Wallet, **FK→stocks.Stock**(PROTECT), unique(wallet,stock) |
| `WalletSnapshot` | FK→Wallet |
| `Portfolio` | FK→Wallet. holding은 `wallet_holding_ids` JSONField(FK 아님) |
| `AnalysisRun` | FK→Portfolio, FK→WalletSnapshot(SET_NULL). `preset_id`=CharField(FK 아님) |
| `MetricResult` | FK→AnalysisRun, **FK→stocks.Stock**(PROTECT). save() `metric_id ∈ METRICS` 검증 |
| `DiagnosticCard` | FK→AnalysisRun, **FK→stocks.Stock**(PROTECT, nullable) |
| `LLMComment` | FK→AnalysisRun, **FK→stocks.Stock**(PROTECT) |
| `StoredAnalysis` | OneToOne→AnalysisRun |
| `PercentileCache` | 외부 FK 없음 |
| `ChatSession` | **FK→AUTH_USER_MODEL**(CASCADE), FK→AnalysisRun(SET_NULL) |
| `Message` | FK→ChatSession |
| `Decision` | **FK→AUTH_USER_MODEL**(CASCADE), FK→AnalysisRun(SET_NULL) |

- 교차앱 FK 대상 = `stocks.Stock`(4곳) + `AUTH_USER_MODEL`(3곳). **shared 앱 FK 없음.**
- 불변성: `AnalysisRun.is_finalized=True` 이후 자신+하위 3모델 save() 차단(`_force_save`로만 우회).

### 2.4 스코어링 엔진 현황

- **게이트 2종 분리**: `_apply_gate`(활성, 실패 시 `score=0.0` 강제) / `_evaluate_gate_tier`(ADDITIVE, 점수 무손상, commentary prompt 전용, Slice 13 #60).
- **`gate_tiers` = 전면 휴면(wired-but-inert)**: 스키마·엔진·6 coach service에 배선됐으나 **12 preset 중 실제 정의 0건** → 전부 `None` → `_evaluate_gate_tier`는 항상 `"pass"`. `preset_spec.py:42` 주석 "Slice 14 #61 calibration" **미실행**.
- **활성 binary `gate` 3건**: `income.py:26`(dividend_yield≥0.02), `income.py:38`(shareholder_yield≥0.02), `factor.py:42`(beta≤1.2). 나머지 9 preset `gate=None`.
- **preset 12개(SSOT 이원화)**: 메타 = `metrics/definitions/presets.py`(`PRESETS`), scoring 공식 = `services/scoring/presets/*.py`(`*_SPECS`). 카테고리: value 2 / growth 2 / income 2 / factor 4 / special 2. weights 합 = `PresetSpec._validate_weights`가 1.0±0.001 강제.

### 2.5 LLM 파이프라인 실측

| 항목 | 실측값(파일:라인) |
|---|---|
| Gemini 모델 | `client.py:43` `"gemini-2.5-flash"` |
| Anthropic 기본 | `client.py:44` `"claude-sonnet-4-5"` |
| Anthropic Haiku | `client.py:46` `"claude-haiku-4-5"` |
| **primary provider** | **`haiku`** — 6 coach/service 전부 `provider="haiku"` 기본 (MEMORY "haiku double win" 일치) |
| fallback | `client.py:182` `RateLimitError`/`TimeoutError`에서만 gemini↔anthropic 1회 스왑. Auth/InvalidPrompt는 raise |
| 실 호출 경로 | `packages.shared.llm.complete()` 경유 (BOUNDARY-LLM ③④ 흡수, IDENTICAL) |
| input 토큰 budget | `llm/token_budgets.py:21` `ENTRYPOINT_TOKEN_BUDGETS` (e1:5000, e3:7000, e2/e6:1500, e5:2000, e4 tier1/2/3:6000/8000/12000) |
| 호출당 max_tokens | `client.py:135` 기본 2000 |
| 호출 횟수 캡 | `client.py:125` `settings.LLM_BUDGET_MAX_CALLS` (Django settings, 앱 밖) |

### 2.6 user_id 스코프 이음새 (방향 B)

- **모델 레이어 보존**: `Wallet.user`/`ChatSession.user`/`Decision.user` = FK→AUTH_USER_MODEL. 하위 모델은 `wallet.user`로 간접 스코프.
- **⚠️ REST 표면 authorization 부재**: `api/views.py`에 **`request.user` 참조 0건**. E1~E6은 `IsAuthenticated`(인증)만 있고, body의 `portfolio_id`/`holdings` 소유권 검증(authorization) 없음.
- **원인 = coach는 순수 stateless LLM 커멘터리 생성기**: `input_data`를 요청 body에서 전부 받아 LLM에 전달, §2.3의 13개 모델을 **live REST가 조회·저장하지 않음**. DB read가 없어 현재 IDOR 유출은 없으나, 소유권 확인 지점도 없음.
- **단일 사용자 하드코딩 없음**: `user_id=1`/`pk=1`/`User.objects.get` grep 결과 test 밖 0건.

---

## 3. §2 — 프론트엔드 전수: portfolio/coach 화면

> 명령: `grep -rn "coach\|portfolio" frontend/ --include="*.ts*" -l`. vitest(scoped)는 Desktop 트리(node_modules 완비)에서, 코드 동일성 확증됨.

### 3.1 라우트 전수

| 라우트 | 파일 | 렌더 |
|---|---|---|
| `/portfolio` | `frontend/app/portfolio/page.tsx` | **레거시** 포트폴리오 관리(Summary/StockCard/Modal/Chart/Table). `services/portfolio`+`useState`, react-query 아님. **coach와 무관** |
| `/coach/e1`~`/coach/e6` | `frontend/app/coach/eN/page.tsx` | E1 GARP 진단 / E2 종합 진단 / E3 집중도 / E4 대화 Q&A / E5 추출 / E6 비교. 각 `AuthGuard`로 감싼 `EN CoachContent` |

### 3.2 ★ 화면 내 위치 이동의 실체 (지시서 특이사항)

- **변경 실체**: Portfolio 진입점이 **전역 top nav에서 제거 → `My` 서브탭 4번째(`/portfolio`)로 이동**.
  - 전역 top nav 6칸(`components/layout/Header.tsx:13-20`): 대시보드 · Market Pulse · Chain Sight · 뉴스 · 스크리너 · **My**. 주석: "포트폴리오·마이페이지는 top nav에서 제거 → My 서브탭·아바타로 이동".
  - `MySubNav.tsx`: `MY_SUBPAGES=['/watchlist','/monitor','/portfolio']`, 탭 = Watchlist · Thesis(→`/monitor`) · Wallet(href=null 자리예약) · **Portfolio(→`/portfolio`)**.
  - `MobileNav.tsx`: 6칸 체계 정합, 포트폴리오는 My로 통합.
- **커밋 상태**: **커밋 완료**. 커밋 `2ca7e36` "MON-P3-S3(monitor): 전역 내비 6칸+아바타 + My 서브탭 (전역 shell 변경)". origin/main + 세션 트리(`66c364d`) **양쪽에 이미 반영**(`2ca7e36`는 `66c364d`의 조상). **미커밋 아님** — 전체 worktree dirty 스캔에서 portfolio/coach/nav 관련 미커밋 변경 **0건**.
- **깨진 링크/import 없음**: coach 페이지가 참조하는 `@/lib/coach/*`, `@/components/coach/*`, `@/components/auth/AuthGuard` 전부 실재. tsc 소스 에러 0(§5).
- **⚠️ coach UI 진입점 부재(dead-end 라우트)**: `/coach/eN` 6개 라우트로 렌더 가능하나, `MySubNav` 등 **어떤 nav/`<Link>`도 coach 라우트를 가리키지 않음**(코드 grep 0건, 테스트 mock URL만 매치). 직접 URL 입력으로만 도달. 깨진 링크가 아니라 "링크 미연결" 상태.

### 3.3 E1~E6 화면 + Slice 17 산출물

- Slice 17 컴포넌트 10개(`frontend/components/coach/`): `BaseCard`, `CardSection`, `SectionHeader`, `ConfidenceBadge`, `CommentaryCard`, `ActionItemsSection`, `KeyObservationsSection`, `QuotedMetricsSection`, `RiskFlagsSection`, `E4MessageBubble`.
- 결선: `CommentaryCard`→`BaseCard`(→`ConfidenceBadge`)+`CardSection`+4 Section(→`SectionHeader`). `E4MessageBubble`→`ConfidenceBadge`.
- 사용처: E1/E2/E3/E5/E6이 `mutation.isSuccess && data`일 때 `<CommentaryCard>` 렌더, E4만 `E4MessageBubble`. **coach 컴포넌트 외부 import = coach 페이지 6개뿐**(그 외 0).

### 3.4 API 결합 (react-query 훅 ↔ 엔드포인트)

- 전부 `useMutation`(useQuery 없음 — LLM 비용 방지, 주석 명시). `authAxios` 경유(JWT 단일 소스).
- `useE1Coach`~`useE6Coach` ↔ `postE1~E6Coach` ↔ `COACH_E1_PATH='/coach/e1/'`~`/coach/e6/`. 백엔드 `coach_e1~e6` 뷰와 **1:1 정합**.
- codegen 산출물: `frontend/lib/coach/schema.yml`(260KB), `api-types.ts`(396KB). 생성 스크립트 `gen:coach-schema`/`gen:coach-types`(spectacular→openapi-typescript). **최신성 판정 불가**(전 파일 mtime 공통 체크아웃 시각 `Jul 2`, drift는 재생성 diff로만 확인 가능).

### 3.5 vitest 현황 (scoped 실측)

- **coach 관련 test 파일 25개** (`grep -rl "coach\|portfolio" --include="*.test.ts*"`): `__tests__/coach/` 22개(컴포넌트 10 + 페이지 6 + 훅 6), 나머지 3은 "portfolio" 우연 매치(coach 무관).
- **레거시 `components/portfolio/` 테스트 0건.**
- **실행 결과: `npx vitest run coach` → 22 files, 97 passed / 0 failed** (Desktop 트리, node v22.19.0, default reporter). 전체 수집 587.
- ⚠️ `--reporter=basic`은 리포터 모듈 로드 실패(`ERR_LOAD_URL`) → default reporter로 우회 성공(§HALT).

---

## 4. §3 — 의존성 전수: portfolio ↔ shared 경계

| 항목 | 실측 |
|---|---|
| portfolio → shared/타 앱 import(non-test) | **타 앱(apps.stocks/macro/users) import 0건**. 외부 경계 넘는 것은 **`packages.shared.llm` 2건뿐**: `llm/client.py:21`(`from packages.shared.llm import complete`), `measure/estimator_v3.py:24`(`count_tokens`) |
| shared → portfolio 역방향 | **코드 역참조 0건**. `packages/shared/users/*`의 `Portfolio` 모델(users 앱 소유, `users_portfolio`)은 **별개 도메인**(레거시 보유종목), coach 아님. `shared/llm/*` 주석의 "portfolio" 언급은 문서 주석일 뿐 import 아님 |
| 외부 API(FMP/LLM) 직접 호출 | **0건**. `client.py`는 전부 `shared.llm.complete(provider=...)` 경유. `genai`/`anthropic`은 docstring·`Literal` 타입 라벨뿐. `requests`/`httpx` 0, `FMP`는 metrics 설명 문자열뿐 |
| tests/architecture | 존재(`test_llm_direct_call_boundary.py`, `test_shared_boundary.py`). **실행 결과 7 passed** |

- test 문자열에 구경로 `portfolio.` 참조 34건(§5 fail 원인, mock.patch/파라미터). 예: `test_s16_step0_ledger_integration.py:133-138`의 `"portfolio.services.coach.eN_service"`.

---

## 5. §4 — 데이터·마이그레이션 상태

| 항목 | 실측 | 명령 |
|---|---|---|
| makemigrations --check | **No changes detected** (미생성 마이그레이션 없음) | `python manage.py makemigrations portfolio --check --dry-run` (Desktop 트리, .env 로드) |
| showmigrations portfolio | **`[X] 0001_initial`** (적용 완료, 단일) | `python manage.py showmigrations portfolio` |
| BOUNDARY-3(macro→shared) 영향 | **없음** — `grep macro apps/portfolio` = **0건**(test 포함). portfolio는 macro 미참조 | `grep -rn "macro" apps/portfolio` |

---

## 6. §5 — 테스트·비용·품질 게이트

| 게이트 | 실측 | 명령 |
|---|---|---|
| **pytest apps/portfolio** | **43 failed / 524 passed** (총 567) | `pytest apps/portfolio -q --maxfail=1000` (sess-main-integrate) |
| **vitest coach** | **97 passed / 0 failed** (22 files) | `npx vitest run coach` (Desktop, node v22.19.0) |
| **tsc(소스)** | **소스 에러 0** (`.next/` 캐시가 폐기된 `app/thesis/*` 라우트 참조 12건은 stale 빌드 캐시, 실 소스 아님) | `npx tsc --noEmit | grep -v '.next/'` |
| **비용 원장(ledger)** | **존재**: `docs/portfolio/coach/cost_ledger.jsonl`, **31행, 누적 $0.158026** (git 추적됨) | `wc -l` + `sum(cost_usd)` |

### pytest 43 fail 카테고리 (전부 앱 재배치 후 stale 경로 잔재로 추정)

| 테스트 파일 | fail 수 | 근본 원인 |
|---|---|---|
| `api/test_e{1,2,3}_endpoint.py` | ~12 | `mock.patch("portfolio.…")` → `ModuleNotFoundError: No module named 'portfolio'` (구 경로) |
| `api/test_e{4,5,6}_endpoint.py` | 10 | 동일(구 경로 patch) |
| `test_rubric_samples.py` | 7 | rubric 파일/경로 참조 stale(추정) |
| `test_s16_step0_ledger_integration.py` | 6 | `"portfolio.services.coach.eN_service"` 문자열(구 경로) |
| `test_slice7_part4_scripts.py` | 5 | scripts 경로 참조 stale(추정) |
| `test_cost_ledger.py` | 1 | ledger 관련 |

> ⚠️ 근본 원인 1건(E1)은 `ModuleNotFoundError: No module named 'portfolio'`로 직접 확인. 나머지는 동일 유형(구 `portfolio.` prefix)일 가능성이 높으나 rubric/slice7 2류(12건)는 별도 원인일 수 있어 **fix 세션에서 개별 재현 필요**. TASKQUEUE `PF-TEST`는 "5건"으로만 표기되어 있어 **실측 43건과 큰 괴리**(큐 과소평가).

---

## 7. §6 — KEEP / CUT / PROMOTE 분류 재료 (판정 아님, 사실만)

> 커밋 수는 monorepo PR7(`225ff47`, 2026-05-31 `git mv`)로 경로 이동됐으므로 **구 `portfolio/` + 신 `apps/portfolio/` 합산**(2026-04-11~).

| 단위 | 최근 90일 커밋 | 테스트 커버 | 다른 앱 참조? | 사용자 #1 실사용 흔적 | 비고 |
|---|---|---|---|---|---|
| E1~E6 진입점(api+coach service) | 코멘트 파이프라인 18 + api 13 | pytest **43 fail** 중 22가 E endpoint(구경로), coach 로직 자체는 통과분 포함 | FE coach 6페이지가 소비 | ledger 31행 $0.158026(실 LLM 호출 흔적 있음) | **UI 진입점 부재**(dead-end 라우트) |
| 스코어링 엔진(`services/scoring/`) | 8 | pytest 통과분 | 내부 전용 | — | gate_tiers 전면 휴면 |
| preset(12개) | 7 | 통과분 | 내부 | — | SSOT 이원화(메타/공식) |
| 코멘트 파이프라인(coach+eN) | 18 | 통과분 다수 | FE 소비 | ledger 기록 | primary=haiku |
| 프론트 coach 화면(app/coach) | **6** | vitest 97 passed | — | — | 활성 |
| 프론트 coach 컴포넌트(components/coach) | **9** | vitest 97 passed | coach 페이지만 | — | Slice 17 산출 |
| **레거시 app/portfolio + components/portfolio** | **0 / 0** | **vitest 0건** | `MySubNav`가 `/portfolio` 링크 | — | `users.Portfolio` 소비, coach와 별개. PF-LEGACY-FE 경계 미결 |
| 영속 모델(13개) | models.py 5 | — | stocks.Stock·AUTH_USER | — | **live REST가 미사용**(stateless) |

- **Thesis Control rehome 후보**: `MySubNav`의 Thesis 탭은 `/monitor`(Monitor 재건)로 연결됨 — thesis 앱은 이미 폐기·Monitor로 재건 상태(MEMORY). portfolio로 rehome될 휴면 엔진은 코드상 별도 식별 안 됨(wallet/portfolio 엔진은 Monitor 트랙 별도 track).

---

## 8. 메모리 대조표 (기억값 vs 실측값)

| 항목 | 기억값 | 실측값 | 판정 |
|---|---|---|---|
| vitest coach | "34/162"(Slice 17 시점) | **coach 97 passed(22 files)**, 전체 수집 587 | 시점 차이(이후 monitor/mp2 대량 추가). 어긋남 = 정상 진화 |
| 누적 비용 | $0.0254128(Slice 16 cap), 미검증 | **ledger 실측 31행 $0.158026** | **실측 확정**(메모리 슬라이스별 값 ≠ ledger 누적 총합) |
| pytest | Slice 종결 시 3172 passed 등 | **apps/portfolio 범위 43 fail / 524 pass** | 이관 후 stale mock(43건). PF-TEST 큐는 "5건"으로 과소 |
| 세션 트리 HEAD | (미기록) | `66c364d`, origin/main보다 **behind 25** | STEP 0 신규 실측 |
| primary LLM | "haiku double win" | **haiku 확정**(6 service `provider="haiku"`) | 일치 |
| shared 경계 | "동결 잔여 0" | **역참조 0 / 외부 API 직접 0 / architecture 7 passed** | 일치 |

---

## 9. HALT 목록 (조사 중 만난 예상 밖 상황)

1. **세션 트리 stale (behind 25)**: 세션 working tree `66c364d`가 origin/main `307306d`보다 25 커밋 뒤. → **뚫지 않고 `sess-main-integrate`(origin/main clean) 트리로 조사 우회**. frontend·apps/portfolio 코드 동일성(diff 0)을 확증한 뒤 진행.
2. **worktree .env 부재**: `sess-main-integrate`에 `.env` 없음(SECRET_KEY/NEO4J_PASSWORD 미설정) → `manage.py` 직접 실행 불가. → migration 검증만 .env·DB 완비된 Desktop 트리에서 실행(apps/portfolio diff 0 확증).
3. **vitest `--reporter=basic` 로드 실패**: `ERR_LOAD_URL`/`MODULE_NOT_FOUND`(sess-main-integrate엔 frontend node_modules 미설치, Desktop에선 basic reporter 모듈 로드 실패). → default reporter로 우회, coach scoped 97 passed 확보. **full-suite 격리 실행은 미수행**(MEMORY 교훈: full-suite는 격리 npm ci 필요).
4. **pytest 43 fail(첫 실행 착시)**: 기본 addopts의 maxfail로 첫 실행이 "5 failed"에서 조기 중단 → maxfail 해제 재실행으로 **43 fail** 확정. (`-o addopts=""`로 덮으니 filterwarnings 설정 충돌 별도 에러 발생 → addopts 유지+`--maxfail=1000`로 해결.)
5. **coach 화면 UI 진입점 부재**: 예상과 달리 nav에서 `/coach/eN`로 가는 링크 0건(dead-end 라우트). 위치 이동(§3.2)과 별개의 구조적 사실.

---

## 10. 다음 결정에 필요한 질문 목록 (판정 없이 나열)

1. **coach 43 fail 테스트를 이번 방향(도그푸딩 우선·외피 동결)에서 KEEP/FIX할 것인가, CUT할 것인가?** PF-TEST는 "5건 mock 경로 수정"으로만 큐잉돼 있으나 실측 43건(rubric 7·slice7 5 포함). fix 범위 재정의 필요.
2. **coach 화면(E1~E6)을 UI에 재연결할 것인가(dead-end 해소), 아니면 의도적 비노출 상태로 둘 것인가?** 현재 직접 URL로만 접근.
3. **레거시 `app/portfolio`(users.Portfolio 소비) 귀속** — portfolio 트랙 vs users/auth 표면(PF-LEGACY-FE 미결). My 서브탭이 이 레거시 화면을 가리킴.
4. **coach REST authorization 부재**를 지금 보강할 것인가(향후 DB read 확장 대비), stateless 유지로 유예할 것인가?
5. **gate_tiers 휴면(calibration 미실행, Slice 14 #61)** — calibrate하여 활성화할 것인가, 코드 제거(CUT)할 것인가?
6. **preset SSOT 이원화**(메타 `presets.py` / 공식 `*_SPECS`) 단일화 여부.
7. **모델 문자열 유령 기본값** `schemas/rationale.py:30` `"claude-sonnet-4-6"`(실 상수는 4-5뿐) 정리 여부.
8. **13개 영속 모델 vs stateless REST 괴리** — 모델 계층을 실사용 경로로 연결(PROMOTE)할지, 미사용 유지할지.

---

## 3줄 요약

- **(a) 코드베이스 상태**: `apps/portfolio`(coach) 백엔드는 구조·경계 건전(shared 역참조 0·외부 API 직접 0·macro 0·migration 정합·architecture 7 passed·vitest coach 97 passed)하나, **pytest 43 fail**(앱 재배치 후 구 `portfolio.` 경로 stale mock) + gate_tiers 전면 휴면 + 13 영속 모델이 stateless REST와 분리된 미결 상태.
- **(b) 위치 이동 상태**: Portfolio 진입점이 전역 top nav → **My 서브탭 4번째(`/portfolio`)로 이동, 커밋 완료**(`2ca7e36` MON-P3-S3, 미커밋 아님, 깨진 링크 없음). 별개로 **coach E1~E6은 UI 진입점이 없는 dead-end 라우트**.
- **(c) 가장 큰 불일치/리스크**: 세션 트리가 origin/main보다 **25 커밋 stale**(health_check WARN)이라 조사를 origin/main 트리로 우회했고, **PF-TEST 큐 "5건" 표기가 실측 43 fail과 크게 괴리** — fix 범위 재정의가 다음 결정의 최우선 안건.
