# Slice 15 종결 문서 — 프론트 코치 화면 E1 GARP 진단 파일럿

> 슬라이스: Slice 15 (프론트 코치 화면 — E1 GARP 진단, 파일럿 단일)
> 종결일: 2026-05-26
> 종결 commit: 본 문서 직전 P3-D 커밋
> 베이스: `slice14` (HEAD `767b42d`)
> 누적 LLM 비용: **$0.0053248** (P3-C 실 round-trip 1회) — 슬라이스 cap $1.00 대비 0.53%

---

## 0. 한 줄 결과

Stock-Vis 처음으로 **투자자가 직접 보는 코치 화면**(E1 GARP 진단)을 end-to-end 완성. OpenAPI→TS 자동 codegen 파이프라인 + Pydantic↔spectacular bridge + 데이터 레이어(useE1Coach) + UI(라우트·폼·CommentaryCard·3-상태) + MSW 통합 테스트 + 실 백엔드 round-trip 1회 실증으로 **전 스택 정합 확인**. 회귀 무손실(pytest 742/1·IDENTICAL 31/31·vitest 65→74·TS strict). E2~E6 복제 본보기 확립.

---

## 1. Slice 15 종합 KPI 매트릭스 (Step 0 + P1 + P2 + P3)

### Step 0 — 셋업 + 타입 자동생성 파이프라인 (10/10)

| #   | KPI                | 결과                                                                              |
| --- | ------------------ | --------------------------------------------------------------------------------- |
| K1  | 브랜치             | `slice15` ← `slice14@767b42d`, pre-commit ALLOWED_BRANCHES 등록 ✅                |
| K2  | 오리엔테이션       | API/라우팅/공용/테스트 관례 4영역 모두 기록 ✅                                    |
| K3  | E1 연동            | invalid body POST → 400 (라우팅·serializer·Pydantic 전 경로 검증, $0) ✅          |
| K4  | CORS               | OPTIONS preflight 200 + ACAO `http://localhost:3000` 명시 ✅                       |
| K5  | 스키마             | (P1-0 교정 후) `/api/v2/schema/`에 coach 6 endpoint 봉투 형태 노출 ✅              |
| K6  | codegen 파이프라인 | `openapi-typescript@^7.13.0` + `gen:coach-types` ✅                               |
| K7  | 타입 생성          | `api-types.ts` 13,523 LoC, E1~E6 6 paths + 12 components, `tsc --noEmit` exit 0 ✅ |
| K8  | 회귀               | vitest 65/65 + pytest 742/1 + IDENTICAL 31/31 무손실 ✅                            |
| K9  | 비용               | $0 (LLM 0) ✅                                                                     |
| K10 | 커밋·문서          | 3 chore 커밋 + `step0.md` ✅                                                      |

### Part 1 — E1 데이터 레이어 (10/10)

| #     | KPI                | 결과                                                            |
| ----- | ------------------ | --------------------------------------------------------------- |
| P1-K1 | 타입 alias         | `lib/coach/types.ts` E1~E6 12개, `tsc` exit 0 ✅                |
| P1-K2 | API 클라이언트     | `postE1Coach` + COACH_E[1-6]_PATH 상수, authAxios 경유 ✅       |
| P1-K3 | 훅                 | `useE1Coach` = `useMutation` ✅                                 |
| P1-K4 | MSW 인프라         | msw@^2.14.6, server + handlers + lifecycle 배선 ✅              |
| P1-K5 | E1 mock 핸들러     | success/validation/server-error 3개, **봉투 형태 충실** ✅      |
| P1-K6 | 데이터 레이어 테스트 | happy + error 2건 PASS ✅                                       |
| P1-K7 | 타입·회귀          | `tsc` exit 0, vitest 65→67 (+2) ✅                              |
| P1-K8 | 백엔드 무변경      | P1-0 외 백엔드 무손, 회귀 0 ✅                                  |
| P1-K9 | 비용               | $0 ✅                                                           |
| P1-K10 | 커밋·문서         | 4 커밋 (P1-0 fix + data feat + test infra + docs) ✅            |

### Part 2 — E1 화면 UI (10/10)

| #     | KPI                | 결과                                                                                       |
| ----- | ------------------ | ------------------------------------------------------------------------------------------ |
| P2-K1 | 라우트             | `app/coach/e1/page.tsx`, `'use client'` + AuthGuard 패턴 ✅                                |
| P2-K2 | 입력 폼            | portfolio_id/preset/동적 종목 행, 제출 시 typed `E1Request` 조립 ✅                        |
| P2-K3 | CommentaryCard     | `components/coach/CommentaryCard.tsx` 순수 표시, output prop ✅                            |
| P2-K4 | 3-상태 처리        | empty/loading/error/success 4분기, aria-live·role=alert·aria-busy 명시 ✅                  |
| P2-K5 | 데이터 레이어 불변 | `lib/coach/*`·MSW 인프라 무수정 (git diff 확인) ✅                                         |
| P2-K6 | 화면 테스트        | 빈/happy/error 3건 PASS ✅                                                                 |
| P2-K7 | 타입·회귀          | `tsc` exit 0, vitest 67→70 (+3) ✅                                                         |
| P2-K8 | 백엔드 무변경      | 회귀 0 ✅                                                                                  |
| P2-K9 | 비용               | $0 ✅                                                                                      |
| P2-K10 | 커밋·문서         | 4 커밋 (CommentaryCard + page + tests + docs) ✅                                           |

### Part 3 — 통합 검증 + 종결 (8/8)

| #     | KPI                | 결과                                                                                       |
| ----- | ------------------ | ------------------------------------------------------------------------------------------ |
| P3-K1 | 테스트 보강        | a11y(aria-busy/role=alert) + 폼 검증 4건 추가, vitest 70→74 (+4) ✅                         |
| P3-K2 | 종합 KPI           | 본 §1 매트릭스 — Step 0 + P1 + P2 + P3 전부 PASS ✅                                        |
| P3-K3 | 회고·함정 목록     | §3 회고 + §4 복제 함정 목록 본 문서에 명시 ✅                                              |
| P3-K4 | 부채 등록          | `debts.md` §1에 #70 AllowAny / #71 환경 / #72 KPI 교훈 등록 ✅                             |
| P3-K5 | 실 스모크 (P3-C)   | HTTP 200 + 봉투 형태 일치 + `E1Response` codegen 정합 + ledger 자동 기록 ✅               |
| P3-K6 | 최종 회귀          | vitest 74/74 + tsc exit 0 + pytest 742/1 + IDENTICAL 31/31 ✅                              |
| P3-K7 | 비용               | $0.0053248 (P3-C 1콜) — cap $1.00 내 ✅                                                    |
| P3-K8 | 종결               | 본 문서 + Part 3 커밋, Slice 15 종결 ✅                                                    |

**합계: 38/38 KPI 통과**

---

## 2. 누적 산출물 (전 슬라이스 통합)

### Backend (3 chore commit)
| 파일 | 변경 | 역할 |
|------|------|------|
| `portfolio/api/views.py` | +31 | 6 view에 `@extend_schema(request=..., responses={200: ...})` |
| `portfolio/api/openapi_extensions.py` | +152 (P1-0 wrapper 포함) | OpenApiSerializerExtension 12개 동적 등록, Pydantic `model_json_schema()` + `_inline_pydantic_refs` + `_wrap_response_envelope` |
| `portfolio/apps.py` | +5 | `ready()` import로 자동 등록 트리거 |

### Frontend (Part 1 + Part 2 + Part 3-A 통합)
| 영역 | 파일 | LoC |
|------|------|-----|
| codegen 산출 | `frontend/lib/coach/api-types.ts` + `schema.yml` | 13,523 + (yaml) |
| 데이터 레이어 | `frontend/lib/coach/{types,api,hooks}.ts` | 97 |
| UI | `frontend/components/coach/CommentaryCard.tsx` + `frontend/app/coach/e1/page.tsx` | 121 + 275 |
| MSW 인프라 | `frontend/__tests__/mocks/{server,handlers}.ts` + vitest.setup.ts 배선 | 107 + 9 |
| 테스트 | `frontend/__tests__/coach/{useE1Coach,e1-page,e1-page-hardening}.test.tsx` | 73 + 97 + 114 |
| devDep | `openapi-typescript@^7.13.0`, `msw@^2.14.6` | — |

### 문서
- `docs/portfolio/coach/slice15/{step_0,part_1,part_2,part3}.md` — 4 지시서 archival
- `docs/portfolio/coach/slice15/{step0,part1,part2,closing}.md` — 4 종결 문서
- `docs/portfolio/coach/debts.md` — Slice 15 부채 3건 등록 (#70/#71/#72)

---

## 3. 회고 — E2~E6 복제 시 따를 패턴

### 데이터 레이어 패턴 (Part 1)
```
types alias (lib/coach/types.ts)          ← codegen 거친 이름 → 도메인 이름
   ↓
api 클라이언트 (lib/coach/api.ts)         ← authAxios + path 상수
   ↓
useMutation 훅 (lib/coach/hooks.ts)       ← useQuery 아님 (LLM 비용 행위)
```
E2~E6는 Slice 15 P1-A에서 이미 alias 완료 → 새 슬라이스에서 `postE2Coach` + `useE2Coach`만 추가하면 됨 (hand-wrap 0줄).

### UI 패턴 (Part 2)
```
app/coach/eN/page.tsx
└── ENCoachPage (default, AuthGuard 래퍼)
    └── ENCoachContent (named export, 테스트 진입점)
        ├── 헤더 (제목 + 설명)
        ├── 폼 (입력값 → ENRequest 조립)
        └── 결과 영역 (aria-live=polite)
            ├── empty-state (isIdle)
            ├── loading-state (isPending, aria-busy)
            ├── error-state (isError, role=alert, 친화 문구)
            └── CommentaryCard (isSuccess, output)
```

### 테스트 패턴 (Part 2 + Part 3-A)
- AuthGuard 우회: `ENCoachContent` named export로 테스트 직접 진입
- MSW: Part 1 인프라(`server.use(mockENSuccess()/mockENServerError())`) 재사용
- 매 테스트 fresh `QueryClient({retry: false})` + Provider 격리
- 케이스: 빈/happy/error 3건 + a11y(aria-busy/role=alert) + 폼 검증 = 진입점당 ~7건

### 봉투 응답 패턴 (P1-0)
모든 진입점 응답이 동일 wrapper:
```
{
  output: ENOutput,       // 진단 본체
  llm_metadata: {...},
  gate_tier?, preset_id?, scores?
}
```
CommentaryCard는 `output`만 prop으로 받으므로 E2~E6 그대로 재사용. metadata는 페이지 측에서 별도 처리 가능 (예: 호출 비용 표시).

---

## 4. 복제 함정 목록 (E2~E6 복제 시 회피)

| # | 함정 | 회피책 |
|---|------|--------|
| 1 | **모듈 레벨 `new Date()`** | `fetched_at`은 제출 핸들러 내부에서만 호출 — hydration mismatch(#24) 차단 |
| 2 | **`holdings` 누락 필드** | sector/asset_class/name 모두 nullable이지만 명시 필수 — 화면에 노출 안 하면 `null` 자동 채움 |
| 3 | **`garp_metrics` 평탄 dict** | ticker별 nested dict `{TICKER: {metric: value}}` 형태가 정확 (평탄 dict 거부됨) |
| 4 | **API path `/api/v1` 중복** | path는 `/coach/eN/`만 — baseURL이 `/api/v1` 포함 (#19) |
| 5 | **`response.output` 미접근** | `useEN.data`는 봉투. 진단 본체는 `data.output` — `data.summary` 등 평탄 접근 금지 |
| 6 | **drf-spectacular response 매핑** | response serializer를 Pydantic output 모델에 직접 매핑 금지 — `_wrap_response_envelope()` 패턴 사용 (`to_representation`이 만드는 wrapper 반영) |
| 7 | **`COMPONENT_SPLIT_REQUEST` 접미** | request 컴포넌트는 `CoachENRequestRequest` 형태 (이중 Request 접미). 직접 import 금지, `lib/coach/types.ts`의 alias만 사용 |
| 8 | **AllowAny 의존 호출** | 현재 6 view 모두 AllowAny — 누구나 LLM 호출 가능. dev only. #70 close 전에 공개/배포 금지 |
| 9 | **MSW `onUnhandledRequest: 'error'`** | 새 코치 호출이 mock 누락이면 즉시 실패. 새 진입점 호출 추가 시 handler도 함께 추가 |
| 10 | **외부 자동화 history 오염** | 슬라이스 작업 직후 `git log --oneline` 확인. `git reflog`로 복구 가능 (#71) |

---

## 5. P3-C 실 백엔드 round-trip 실증 결과

### 입력
- 엔드포인트: `POST http://127.0.0.1:8000/api/v1/coach/e1/?provider=haiku`
- 페이로드: 2 종목 (AAPL 50% + MSFT 50%) GARP 지표 포함, `portfolio_id="slice15-p3c-smoke"`
- 인증: 없음 (E1 view `AllowAny`)

### 결과
| 항목 | 값 |
|------|------|
| HTTP status | 200 |
| 응답 시간 | 10.02s |
| `output.summary` | "AAPL과 MSFT 모두 GARP 기준을 충족하나, 포트폴리오 집중도가 높고 밸류에이션 재평가 위험이 존재합니다." |
| `output.confidence` | "high" |
| `output.key_observations` | 5건 |
| `output.action_items` | 3건 (priority high×1, medium×2) |
| `output.risk_flags` | 4건 |
| `llm_metadata.provider` | "anthropic" |
| `llm_metadata.model` | "claude-haiku-4-5" |
| `llm_metadata.input_tokens` | 1,516 |
| `llm_metadata.output_tokens` | 1,028 |
| `llm_metadata.cost_usd` | **0.0053248** |
| `llm_metadata.latency_ms` | 10,003 |
| `gate_tier` / `preset_id` / `scores` | 응답 미포함 (optional 정상) |

### 정합 검증
| 검증 항목 | 결과 |
|----------|------|
| 봉투 형태 `{output, llm_metadata}` | ✅ |
| `output` 필드 (summary/confidence/action_items/risk_flags/key_observations/metrics_table) | ✅ 모두 존재 + 타입 일치 |
| `llm_metadata` free-form object | ✅ |
| codegen `CoachE1Response` (`api-types.ts`) shape | ✅ 일치 |
| optional 필드 미포함 시 정합 | ✅ (TypeScript `?` 정의대로) |
| cost_ledger 자동 append | ✅ P3-C 시점에 25행 확인 (이후 외부 자동화 reset으로 1행 유실 — §부록 참조, 본 문서에 실측값 영구 기록) |

### 부정합 발견 (별도 부채 §`debts.md` #68과 일치)
- `cost_ledger` 행의 `slice` = `"default"` (slice15 식별자 미세팅 — view에서 CostGuard slice_id 전달 안 함)
- `cost_ledger` 행의 `entry_point` = null (#68 그대로)

이는 cost 추적 부정합으로 Slice 15 작업 범위 밖. Slice 16에서 #68과 함께 처리 권장.

### 비용 정산
- Slice 15 누적: **$0.0053248** (P3-C 1콜만)
- Slice cap $1.00 대비: **0.53%**
- 누적 1콜이라 추가 안전 마진 충분

---

## 6. 회귀 매트릭스 (전 슬라이스 종합)

| 트랙               | Slice 14 종결 (`767b42d`) | Slice 15 종결 | 변동 |
| ------------------ | ------------------------- | -------------- | ---- |
| pytest             | 742 passed, 1 skipped     | 742 passed, 1 skipped | 0 |
| IDENTICAL          | 31/31                     | 31/31          | 0 |
| vitest             | 12 files / 65 tests       | 15 files / 74 tests | +3 files / +9 tests |
| `tsc --noEmit`     | exit 0                    | exit 0         | 0 |
| `/api/v2/schema/` LoC | 218,888 bytes          | 260,561 bytes  | +41,673 (coach 6 봉투 + 12 컴포넌트) |
| `api-types.ts` LoC | (신설)                    | 13,523         | (신설) |
| coach API paths    | 0                         | 6 (E1~E6)      | +6 |
| coach 화면         | 0                         | 1 (E1)         | +1 (E2~E6는 Slice 16) |

---

## 7. 커밋 히스토리 (Slice 15)

| # | Commit | 단계 | 의미 |
|---|--------|------|------|
| 1 | `69dc94e` | Step 0 pre | chore: @extend_schema 6 view 어노테이션 |
| 2 | `8300d81` | Step 0 pre | chore: Pydantic↔spectacular bridge (12 확장) |
| 3 | `301a832` | Step 0 | chore: openapi-typescript 파이프라인 + codegen 산출 |
| 4 | `1718d47` | Part 1 P1-0 | fix: response wrapper envelope 교정 |
| 5 | `d4c5e7c` | Part 1 P1-A~C | feat: 데이터 레이어 (types/api/hooks) |
| 6 | `38bcf99` | Part 1 P1-D~E | test: MSW 인프라 + useE1Coach 테스트 |
| 7 | `9de1cdb` | Part 1 docs | docs: Part 1 종결 + archival |
| 8 | `ec61c1c` | Part 2 | feat: CommentaryCard |
| 9 | `a488d67` | Part 2 | feat: E1 페이지 + 폼 |
| 10 | `79c9724` | Part 2 | test: E1 화면 렌더 테스트 |
| 11 | `4dee270` | Part 2 docs | docs: Part 2 종결 + archival |
| — | `82aa9b4` | (외부 오염) | feat(iron-trading): ... — Slice 15와 무관, #71 |
| 12 | `75904c7` | Part 3 P3-A | test: a11y + 폼 검증 보강 4건 |
| 13 | (본 커밋) | Part 3 P3-D | docs: Slice 15 closing + debts 갱신 |

12 정상 commit + 1 외부 오염(82aa9b4).

---

## 8. HALT 발동 이력 (전 슬라이스)

| 시점 | 유형 | 결과 |
|------|------|------|
| Step 0-C | 스키마 게이트 | drf-spectacular가 coach 6 endpoint req/res body 미노출 → 사용자 A안: 백엔드 보강 + bridge 추가 |
| Part 1 P1-A 직전 | mock 충실성 게이트 | bridge response 매핑이 wrapper 미반영 (평탄 매핑) 발견 → 사용자 A안: P1-0 단계로 분리해 wrapper envelope 교정 후 진행 |
| Part 2 도중 | 환경 이슈 | 외부 자동화가 working tree를 `iron-trading-api`로 전환 → slice15 HEAD 무사 확인 후 `git checkout slice15` 복귀 |
| Part 3 P3-A 직후 | 환경 이슈 | 외부 자동화가 slice15에 iron-trading commit + reset --hard로 P3-A 제거 → `git reflog`에서 `75904c7` 복원 → P3-A 살아남, history에 `82aa9b4` 잔존 (#71) |

---

## 9. Slice 16 진입 메모

### 본작업
**E2~E6 화면을 Slice 15 E1 패턴으로 복제** (5 진입점 × 7 케이스 ≈ 35 테스트 신규 예상).

### 동시 처리 권장 부채
1. **#70 AllowAny → IsAuthenticated** — 6 view 동시 전환 (Slice 16이 E2~E6도 만지는 김에). 공개/배포 차단성.
2. **#72 P3-C E2~E6 동등 검증** — 각 진입점 1회씩 round-trip + 봉투 정합 단언. 예상 비용 ~$0.03–0.10 (5 × $0.005–0.02).

### 진입 전 결정 사항
- **`82aa9b4` (iron-trading commit) 처리**: slice15 history에 잔존. (a) 그대로 두기 / (b) `git revert` / (c) Slice 16을 `4dee270`에서 분기(82aa9b4 우회). 사용자 결정 필요.
- **#68 cost ledger entry_point null**: Slice 16에서 6 view 만지는 김에 동시 close 가능.

### 베이스라인 (Slice 16 진입 시 측정 권장)
- pytest 742/1 + IDENTICAL 31/31 + vitest 74/74 + tsc exit 0 + 누적 ledger 25행 ($X.XX)

---

## 부록: cost_ledger 1행 유실 (외부 자동화 재발)

P3-C 호출 직후 `tail -1`로 25행 확인:
```json
{"timestamp": "2026-05-25T13:06:12.991134+00:00", "slice": "default", "entry_point": null, "provider": "anthropic", "model": "claude-haiku-4-5", "input_tokens": 1516, "output_tokens": 1028, "cost_usd": 0.0053248, "fallback_from": null}
```

그러나 외부 자동화가 슬라이스 작업 도중 `git reset --hard`로 working tree를 되돌리면서 ledger도 24행으로 복원됨. P3-C 호출은 실제로 일어났고 비용 발생했으나 영구 기록은 본 closing.md만 남음.

**처리**: Slice 16 진입 시 ledger 1행 보정 검토 (수동 append 또는 P3-C 재실행 후 비용 합산). 본 결정은 Slice 16 책임 — Slice 15 누적 비용 산정은 본 closing.md를 진실의 소스로 한다.

---

## 10. 부채 변동

- 신규 등록: **#70 AllowAny (PS 2.0), #71 외부 자동화 환경 이슈, #72 스키마 KPI 교훈 (PS 1.0)**
- close: 0건
- net: **+3** (Slice 15 동안)

상세는 [debts.md §1·§4·§5](../debts.md) 참조.
