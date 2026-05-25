# Slice 15 Part 1 종결 문서 — E1 데이터 연동 레이어

> 슬라이스: Slice 15 (프론트 코치 화면 — E1 GARP 진단, 파일럿 단일)
> 단계: Part 1 (데이터 레이어, UI는 Part 2)
> 베이스: Step 0 종결 `301a832`
> 종결 시점: `38bcf99` (test infra commit)
> 누적 LLM 비용: **$0**

---

## 0. 한 줄 결과

Step 0 브릿지의 response 매핑 결함을 **P1-0에서 사전 발견·교정**(평탄 → 봉투 `{output, llm_metadata, gate_tier?, preset_id?, scores?}`)한 후, 그 위에 도메인 alias / `postE1Coach` / `useE1Coach` mutation / MSW 인프라 / happy+error 데이터 레이어 테스트 2건을 올림. 회귀 무손실, $0.

---

## 1. KPI 매트릭스 — 10/10 통과

| #      | KPI                  | 기준                                                        | 결과                                                                                | 상태 |
| ------ | -------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------- | ---- |
| P1-K1  | 타입 alias           | `lib/coach/types.ts` E1Request/E1Response 깨끗 export       | E1~E6 12개 alias 모두 export, `npx tsc --noEmit` exit 0                             | ✅   |
| P1-K2  | API 클라이언트       | `postE1Coach` authAxios 경유, 타입 안전                     | `lib/coach/api.ts` 18줄, COACH_E[1-6]_PATH 상수 + `postE1Coach` ─ JWT 인터셉터 단일 소스 | ✅   |
| P1-K3  | 훅                   | `useE1Coach` = useMutation, mutation 인터페이스 노출        | `lib/coach/hooks.ts`, AxiosError 타입 narrowing 포함                                | ✅   |
| P1-K4  | MSW 인프라           | msw 도입 + 테스트 서버 + vitest 배선                        | msw@^2.14.6, `__tests__/mocks/{server,handlers}.ts`, vitest.setup.ts lifecycle 3개  | ✅   |
| P1-K5  | E1 mock 핸들러       | 200/에러 핸들러, 200이 E1Response 타입 부합 (mock 충실성)   | `mockE1Success/ValidationError/ServerError` 3개. defaultE1Response = 봉투 형태      | ✅   |
| P1-K6  | 데이터 레이어 테스트 | happy + error 케이스 통과                                   | useE1Coach happy(봉투 검증) + error(500 + data undefined) 2건 PASS                  | ✅   |
| P1-K7  | 타입·회귀            | tsc exit 0, vitest 65→65+N (기존 무손실)                    | tsc exit 0, vitest 12→13 files, 65→67 tests (+2)                                    | ✅   |
| P1-K8  | 백엔드 무변경        | pytest 742/1·IDENTICAL 31/31 불변                           | P1-0(브릿지 메타 수정)에서 회귀 0 검증. P1-A~F는 백엔드 무손               | ✅   |
| P1-K9  | 비용                 | $0 (LLM 실호출 0)                                           | 모든 검증 MSW 가짜 응답으로                                                          | ✅   |
| P1-K10 | 커밋·문서            | Part 1 커밋(권장 2) + part1.md                              | 3 커밋 (P1-0 fix + data layer feat + test infra) + 본 문서                          | ✅   |

---

## 2. P1-0 — Step 0 브릿지 응답 매핑 결함 교정 (사용자 결정 A안)

### 발견
Part 1 P1-A 진입 전 사전 점검에서 다음 부정합 확인:
- `portfolio/api/serializers.py:64~352`의 모든 `E*ResponseSerializer.to_representation`이 **wrapper**로 감싸 반환:
  `{output: E*Output dict, llm_metadata: {...}, gate_tier?: str, preset_id?: str, scores?: dict}`
- 그러나 Step 0의 `_make_extension`은 response serializer → `E*Output` 직접 매핑 → codegen된 `CoachE*Response`가 봉투 없이 평탄.
- 결과: MSW mock과 실제 백엔드 응답 shape 불일치 위험 → mock 충실성 게이트 발동 가능성.

### 교정
`portfolio/api/openapi_extensions.py` 구조 분리:
- `_wrap_response_envelope(output_model)` 신설 — 6 response 공통 wrapper 빌더 (output + llm_metadata + 3 optional).
- `_make_request_extension` / `_make_response_extension` 분리.
- `_REQUEST_MAPPINGS` (6) + `_RESPONSE_MAPPINGS` (6) 매핑 분리.

### 변동
- 스키마: 261KB (+8KB vs Step 0).
- `api-types.ts`: 13,429 → 13,523 LoC.
- `CoachE1Response`~`E6Response` 6개 모두 봉투 갱신.

### 게이트 검증
- **pytest 742/1 PASS** (변동 0 — 메타데이터만 변경, 런타임 무영향).
- **IDENTICAL 31/31 PASS** (변동 0).
- **/api/v2/schema/** E1 response.200 = `{output, llm_metadata, gate_tier, preset_id, scores}` 확인.
- **tsc --noEmit** exit 0.
- **vitest 65/65 PASS** (P1-0 시점에서는 신규 테스트 전).

### 커밋
`1718d47` — `fix(s15): bridge response schema as wrapper envelope (Part 1 P1-0)`

---

## 3. P1-A — 타입 alias 레이어

**파일**: `frontend/lib/coach/types.ts` (39줄)

생성 타입의 거친 이름(`CoachE1RequestRequest`)을 도메인 이름으로 정리:
```ts
export type E1Request = Schemas['CoachE1RequestRequest']
export type E1Response = Schemas['CoachE1Response']
// ... E2~E6 동일 패턴
```

E2~E6도 함께 alias — Slice 16+ 복제 시 hand-wrap 0줄로 바로 사용 가능 (지시서 §P1-A.4 선택 옵션 채택).

**규칙**: 화면·훅은 `lib/coach/types`에서만 import. `lib/coach/api-types.ts` 직접 import 금지.

---

## 4. P1-B — API 클라이언트

**파일**: `frontend/lib/coach/api.ts` (24줄)

```ts
export const COACH_E1_PATH = '/coach/e1/'  // baseURL이 /api/v1까지 포함 (#19)
// ... E2~E6 상수

export async function postE1Coach(req: E1Request): Promise<E1Response> {
  const { data } = await authAxios.post<E1Response>(COACH_E1_PATH, req)
  return data
}
```

- `authAxios` (lib/api/authAxios.ts)의 JWT 인터셉터·refresh queue 단일 소스 경유.
- baseURL = `NEXT_PUBLIC_API_URL` (기본 `http://localhost:8000/api/v1`). path는 `/coach/e1/`만 — `/api/v1` 중복 회피 (#19 패턴).

---

## 5. P1-C — react-query 훅

**파일**: `frontend/lib/coach/hooks.ts` (34줄)

```ts
export function useE1Coach(): UseMutationResult<E1Response, AxiosError, E1Request> {
  return useMutation<E1Response, AxiosError, E1Request>({ mutationFn: postE1Coach })
}
```

- `useMutation` 사용 (지시서 §P1-C.2 결정 근거 그대로): E1은 사용자 행동 + LLM 비용 행위 → `useQuery`의 자동 재요청·캐싱 부작용 회피.
- 파일럿 단순성: 캐싱·dedup·재요청 미도입. Slice 16+에서 동일 포트폴리오 재진단 캐싱 검토 후보.

---

## 6. P1-D — MSW 인프라

### 도입
```bash
npm install -D msw  # ^2.14.6
```

### 파일
- `frontend/__tests__/mocks/server.ts` — `setupServer(...handlers)`.
- `frontend/__tests__/mocks/handlers.ts` — coach mock 통합:
  - `defaultE1Response: E1Response` — 봉투 형태에 부합하는 baseline (mock 충실성 게이트 충족).
  - `mockE1Success(custom?)` — 200 핸들러, output/llm_metadata 부분 override 가능.
  - `mockE1ValidationError()` — 400 핸들러.
  - `mockE1ServerError()` — 500 핸들러.
- `frontend/vitest.setup.ts` — `beforeAll(server.listen)` + `afterEach(server.resetHandlers)` + `afterAll(server.close)` lifecycle 배선. `onUnhandledRequest: 'error'`로 mock 누락 명시적 탐지.

### mock 충실성 게이트 충족
- `defaultE1Response` 타입은 `E1Response` (P1-0 봉투 갱신 후)를 그대로 따름. TS strict가 봉투 누락을 컴파일 타임에 탐지.

---

## 7. P1-E — 데이터 레이어 테스트

**파일**: `frontend/__tests__/coach/useE1Coach.test.tsx` (73줄)

### 테스트 케이스
1. **happy-path** — `server.use(mockE1Success({output: {summary: 'test summary', confidence: 'high', metrics_table: ''}}))` → `data.output.summary === 'test summary'`, `data.llm_metadata.provider === 'haiku'`.
2. **error-path** — `server.use(mockE1ServerError())` → `error.response.status === 500`, `data === undefined`.

### 격리
- 매 테스트 fresh `QueryClient` (`{retry: false}`) + `QueryClientProvider`로 감쌈.

### 검증 절차
- `renderHook(() => useE1Coach(), { wrapper })` + `result.current.mutate(validRequest)`.
- `waitFor(() => expect(result.current.isSuccess).toBe(true))` (timeout 3s).

### validRequest fixture
- 실제 `E1Request` 타입에 부합 — `holdings`에 sector/asset_class/name 모두 명시, `garp_metrics`는 ticker별 dict 형태 (`{AAPL: {...}, MSFT: {...}}`).

---

## 8. 회귀 매트릭스

| 트랙                 | 베이스 (Step 0 종결) | P1-0 후    | P1-F 종결  | 변동 |
| -------------------- | -------------------- | ---------- | ---------- | ---- |
| pytest               | 742/1                | 742/1      | 742/1*     | 0    |
| IDENTICAL 31/31      | 31                   | 31         | 31*        | 0    |
| vitest               | 12 files / 65 tests  | 12/65       | 13/67      | +2   |
| `npx tsc --noEmit`   | exit 0               | exit 0     | exit 0     | 0    |

*P1-A~F는 백엔드 무손이라 P1-0 이후 미실행. 백엔드 마지막 검증 시점은 P1-0 (`1718d47`).

---

## 9. 커밋 (3건)

| Commit | 의미 단위 | 변경 |
|---|---|---|
| `1718d47` | P1-0: 브릿지 응답 wrapper 교정 + 재 codegen | 3 files, +841 -518 |
| `d4c5e7c` | P1-A~C: 데이터 레이어 (types/api/hooks) | 3 files, +97 |
| `38bcf99` | P1-D~E: MSW 인프라 + 테스트 + msw devDep | 6 files, +719 -1 |

---

## 10. 산출물 매핑 (지시서 §산출물)

| # | 지시서 항목 | 실제 파일 |
|---|------|------|
| 1 | `lib/coach/types.ts` | ✅ 39줄 |
| 2 | `lib/coach/api.ts` | ✅ 24줄 |
| 3 | `lib/coach/hooks.ts` | ✅ 34줄 |
| 4 | MSW server + handlers + vitest 셋업 | ✅ server.ts(13줄) + handlers.ts(94줄) + vitest.setup.ts(+9줄) |
| 5 | `__tests__/coach/useE1Coach.test.ts` | ✅ useE1Coach.test.tsx (73줄, .tsx로 JSX 사용) |
| 6 | `frontend/package.json` msw devDep | ✅ `^2.14.6` |
| 7 | Part 1 종결 문서 | ✅ 본 문서 |

---

## 11. HALT 발동 이력

- **P1-0 HALT (1회, 사전 발견)**: Step 0 브릿지 response 매핑 결함 → 사용자에게 3안 옵션 보고 → A안 채택 (브릿지 수정 + 재 codegen + Part 1 진행). Part 1 §0.3 "백엔드 무변경" 게이트 명시적 예외 (Step 0 산출물 결함이 원인이라 별도 의미 단위 커밋으로 분리, 회귀 0 검증).
- **다른 HALT 게이트**: 모두 미발동 (tsc 회귀·vitest 회귀·mock 충실성).

---

## 12. Part 2 진입 메모

- Part 2 책임: E1 화면 UI — 라우트 (`app/coach/e1/` 추정), 입력 폼, CommentaryCard, 로딩/에러 상태 표시.
- 데이터는 본 Part 1의 `useE1Coach`를 그대로 소비:
  ```tsx
  const { mutate, data, isPending, error } = useE1Coach()
  // 폼 제출 → mutate(formData)
  // data?.output.summary, data?.output.action_items, data?.output.risk_flags 등 렌더
  ```
- 타입 import는 `@/lib/coach/types` (alias 레이어)만 사용. 생성물 직접 참조 금지.
- MSW 핸들러는 Part 3 화면 통합 테스트에서도 그대로 재사용 (코치 mock 단일 소스).

---

## 13. 부채 / 후속

- 부채 신규 0건.
- 후속 (Slice 15 내): Part 2 (UI), Part 3 (MSW 화면 통합 테스트).
- 후속 (Slice 16+): E2~E6 화면 복제 시 `lib/coach/types.ts`의 E2~E6 alias·`api.ts`의 COACH_E[2-6]_PATH 상수·MSW handlers 패턴을 그대로 확장. P1-0 봉투 형태가 모든 진입점 공통이라 hand-wrap 0줄.
