# Slice 15 Part 1 작업 지시서 — E1 데이터 연동 레이어

> 대상: Claude Code 실행 환경
> 슬라이스: Slice 15 (프론트 코치 화면 — E1 GARP 진단, 파일럿 단일)
> 이번 단계: Part 1 — Step 0가 깐 생성 타입 위에서 "API 호출 → 진단 결과 수신" 데이터 레이어 구축. UI(Part 2)와 분리된 순수 데이터 계층.

---

## 0. 컨텍스트 & 작업 원칙

### 0.1 현재 위치

- Step 0 종결(`slice15` HEAD = `301a832`): codegen 파이프라인 + `frontend/lib/coach/api-types.ts`(13,429 LoC, E1~E6 req/res 타입 포함) + 백엔드 `@extend_schema` 6 view + Pydantic↔spectacular bridge.
- Part 1은 그 생성 타입 위에 **데이터 레이어**를 올린다. 화면(UI)은 Part 2 — 이번엔 손대지 않는다.

### 0.2 Step 0에서 확정된 코드베이스 관례 (이대로 따른다)

- API 클라이언트: `frontend/lib/api/authAxios.ts` — JWT 단일 소스(interceptor + token refresh queue). 코치 API 호출은 **반드시 이 인스턴스 경유.**
- 공용 코드: `frontend/lib/` — 코치 데이터 레이어는 `frontend/lib/coach/` 하위.
- 생성 타입: `frontend/lib/coach/api-types.ts` (Step 0 산출).
- 테스트: `frontend/__tests__/`, vitest include `__tests__/**/*.{test,spec}.{ts,tsx}`, jsdom + RTL + alias `@`.
- 상태/데이터: react-query(앱 루트에 QueryClientProvider 기존).

### 0.3 작업 원칙 (HALT 규칙)

- **타입 게이트**: TS strict 컴파일(`npx tsc --noEmit`) 실패 시 → 즉시 중단·보고.
- **회귀 게이트**: 기존 vitest 65건 중 신규 실패가 나오면 → 중단·보고.
- **mock 충실성 게이트**: MSW E1 mock 응답이 생성 타입 `E1Response`에 타입상 부합하지 않으면 → 중단·보고. (가짜 응답이 실제 스키마와 어긋나면 Part 3 통합 테스트가 거짓 위에 서게 됨.)
- Part 1은 프론트 전용 — 백엔드 코드 무변경. `pytest 742/1`·`IDENTICAL 31/31`은 손대지 않음.
- LLM 실호출 0 — 모든 검증은 MSW 가짜 응답으로. 예상 비용 $0.

### 0.4 브랜치

`slice15` 계속(HEAD `301a832`). Part 1 커밋은 `slice15` 위에.

---

## P1-A — 타입 alias 레이어

생성 파일 `api-types.ts`는 기계 생성물이라 이름이 거칠다(`COMPONENT_SPLIT_REQUEST: True`로 인해 request 컴포넌트가 `CoachE1RequestRequest` — Request 접미 이중 부착). 화면·훅이 이 거친 이름을 직접 import하지 않도록 **깨끗한 도메인 이름의 alias 레이어**를 만든다.

1. `frontend/lib/coach/types.ts` 신설.
2. 생성 타입에서 E1 req/res를 깨끗한 이름으로 re-export:
   - `export type E1Request = ...` (생성물의 `CoachE1RequestRequest` 컴포넌트)
   - `export type E1Response = ...` (생성물의 `CoachE1Response` 컴포넌트)
   - 접근 경로(`components['schemas'][...]` 등)는 `api-types.ts` 실제 출력 구조에 맞춘다.
3. 이 alias 레이어가 **유일한 코치 타입 진입점** — Part 2 이후 화면은 `lib/coach/types`에서만 import. 생성물 직접 참조 금지.
4. (선택) E2~E6도 같은 패턴으로 alias해 두면 Slice 16+ 복제가 수월 — 이번엔 E1 필수, 나머지는 여유 시.

---

## P1-B — API 클라이언트 함수

E1 코치 엔드포인트를 호출하는 타입 안전 함수 1개.

1. `frontend/lib/coach/api.ts` 신설.
2. `postE1Coach(req: E1Request): Promise<E1Response>` 구현:
   - `authAxios` 인스턴스로 `POST /api/v1/coach/e1/` 호출(baseURL·JWT는 authAxios가 처리 — 직접 토큰 다루지 말 것).
   - 요청 본문은 `E1Request`, 반환은 `response.data`를 `E1Response`로 타입.
3. 엔드포인트 경로는 상수로(`COACH_E1_PATH = '/api/v1/coach/e1/'` 등) — Part 2+에서 재사용.

---

## P1-C — react-query 훅

화면이 호출할 `useE1Coach` 훅.

1. `frontend/lib/coach/hooks.ts` 신설.
2. `useE1Coach` 구현 — **`useMutation` 사용**(`useQuery` 아님):
   - 근거: E1은 "포트폴리오 제출 → 진단 생성"이라는 사용자 행동이고, 백엔드에서 LLM을 구동하는 비용 행위다. 쿼리로 다루면 react-query가 자동 재요청·캐싱하려 들어 의도치 않은 재호출·비용이 발생한다. mutation이 맞다.
   - `mutationFn`은 P1-B의 `postE1Coach`.
   - 반환은 react-query mutation 표준 인터페이스(`mutate`/`data`/`isPending`/`error` 등) — Part 2가 로딩·에러·결과 상태를 여기서 받는다.
3. 캐싱·재요청은 도입하지 않는다(파일럿 단순성). 동일 포트폴리오 재진단 캐싱은 추후 개선 후보로만 남김.

---

## P1-D — MSW 셋업 + E1 mock 핸들러 (결정 ④ 인프라)

테스트가 실제 LLM·실서버 없이 "API 호출 → 응답" 흐름을 검증하도록 Mock Service Worker 인프라를 깐다. 이는 백엔드의 mock fixture 단계가 프론트로 옮겨온 것.

1. **`msw` devDependency 추가**(없으면). MSW v2 기준 — `setupServer`는 `msw/node`.
2. **테스트 서버 셋업** — 프로젝트 테스트 관례에 맞는 위치(예: `frontend/__tests__/mocks/`)에:
   - `server.ts` — `setupServer(...handlers)`.
   - vitest 셋업 파일에 `beforeAll(server.listen)` / `afterEach(server.resetHandlers)` / `afterAll(server.close)` 배선. (셋업 파일이 없으면 vitest config의 `setupFiles`로 등록.)
3. **E1 mock 핸들러** — `handlers.ts`에 `POST /api/v1/coach/e1/`를 가로채 현실적인 가짜 E1 응답 반환:
   - ⚠️ **응답 객체는 생성 타입 `E1Response`에 타입상 부합해야 한다**(mock 충실성 게이트). 가능하면 백엔드 E1 fixture의 기대 출력을 참고해 현실성 확보.
   - happy-path(200) 핸들러 + 에러(400 또는 500) 핸들러를 함께 마련 — 테스트에서 골라 쓴다.
4. MSW 핸들러는 6화면 재사용 자산 — `lib/coach`/테스트 관례에 맞춰 코치 mock을 한곳에 모은다.

---

## P1-E — 데이터 레이어 테스트 (MSW 기반)

`useE1Coach` 훅을 MSW 위에서 검증. (화면 통합 테스트는 Part 3 — 여기선 데이터 계층만.)

1. 테스트 파일: `frontend/__tests__/coach/useE1Coach.test.ts`(테스트 관례에 맞춰).
2. 훅 테스트는 fresh `QueryClient`를 만든 `QueryClientProvider`로 감싸 렌더(RTL `renderHook`).
3. 검증 케이스(최소):
   - **happy-path**: MSW 200 핸들러 → `mutate(validE1Request)` → `data`가 `E1Response` 형태로 도착.
   - **error-path**: MSW 에러 핸들러 → `error` 상태가 노출되는지.
4. 신규 테스트 N건 추가 → vitest `65 → 65+N`.

---

## P1-F — 회귀 & 커밋

1. **회귀 게이트**:
   - `npx tsc --noEmit` → exit 0 (TS strict).
   - `vitest` → 기존 65건 전건 통과 + 신규 N건 통과 = `65+N`.
   - 백엔드 미변경 — `pytest`/`IDENTICAL`은 실행 불필요(변경했다면 HALT).
2. **커밋** — 다단계 커밋 패턴, 의미 단위 분리(권장 2커밋):
   - 데이터 레이어: `types.ts` + `api.ts` + `hooks.ts` → `feat(s15): E1 coach data layer — typed API client + useE1Coach hook (Part 1)`
   - MSW + 테스트: MSW 셋업 + 핸들러 + 훅 테스트 → `test(s15): MSW infra + E1 coach data-layer tests (Part 1)`
3. Part 1 종결 문서: `docs/portfolio/coach/slice15/part1.md` — 데이터 레이어 구조(alias/api/hook 경로·인터페이스), MSW 사용법, KPI 결과.

---

## Slice 15 Part 1 KPI 매트릭스

| #      | KPI                  | 통과 기준                                                                       |
| ------ | -------------------- | ------------------------------------------------------------------------------- |
| P1-K1  | 타입 alias           | `lib/coach/types.ts` — `E1Request`/`E1Response` 깨끗한 이름 export, 컴파일 PASS |
| P1-K2  | API 클라이언트       | `postE1Coach` — authAxios 경유, 타입 안전                                       |
| P1-K3  | 훅                   | `useE1Coach` = `useMutation` 기반, mutation 인터페이스 노출                     |
| P1-K4  | MSW 인프라           | `msw` 도입 + 테스트 서버 셋업 + vitest 배선                                     |
| P1-K5  | E1 mock 핸들러       | 200/에러 핸들러, 200 응답이 `E1Response` 타입 부합                              |
| P1-K6  | 데이터 레이어 테스트 | happy + error 케이스 통과                                                       |
| P1-K7  | 타입·회귀            | `tsc --noEmit` exit 0, vitest 65→65+N (기존 65 무손실)                          |
| P1-K8  | 백엔드 무변경        | pytest 742/1·IDENTICAL 31/31 불변(미실행 가능)                                  |
| P1-K9  | 비용                 | $0 (LLM 실호출 0)                                                               |
| P1-K10 | 커밋·문서            | Part 1 커밋(권장 2) + `slice15/part1.md`                                        |

---

## 산출물 목록

1. `frontend/lib/coach/types.ts` — 타입 alias 레이어
2. `frontend/lib/coach/api.ts` — `postE1Coach` + 경로 상수
3. `frontend/lib/coach/hooks.ts` — `useE1Coach`
4. MSW: `server.ts` + `handlers.ts`(코치 mock) + vitest 셋업 배선
5. `frontend/__tests__/coach/useE1Coach.test.ts` — 데이터 레이어 테스트
6. `frontend/package.json` — `msw` devDep
7. `docs/portfolio/coach/slice15/part1.md` — Part 1 종결 문서

---

## HALT 규칙 요약

- `tsc --noEmit` 실패 / 기존 vitest 65 깨짐 → 중단·보고
- MSW E1 mock 200 응답이 `E1Response` 타입과 불일치 → 중단·보고
- 백엔드 코드 변경 필요가 생기면 → 중단·보고 (Part 1은 프론트 전용)

---

## 한눈 요약

```
P1-A : 타입 alias 레이어 — 거친 생성 이름을 E1Request/E1Response로 정리
P1-B : API 클라이언트 — postE1Coach (authAxios 경유, 타입 안전)
P1-C : react-query 훅 — useE1Coach = useMutation (행동·비용 행위라 query 아님)
P1-D : MSW 셋업 + E1 mock 핸들러 (응답은 E1Response 타입 부합 필수)
P1-E : 데이터 레이어 테스트 — useE1Coach happy/error (MSW 기반)
P1-F : tsc + vitest 65+N 확인 → 커밋 2건 + Part 1 종결 문서
다음 : Part 2 — E1 화면 UI (라우트·입력 폼·CommentaryCard, 이 데이터 레이어 소비)
```
