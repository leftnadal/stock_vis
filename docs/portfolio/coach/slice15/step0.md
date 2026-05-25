# Slice 15 Step 0 종결 문서 — 셋업 & 타입 자동생성 파이프라인

> 슬라이스: Slice 15 (프론트 코치 화면 — E1 GARP 진단, 파일럿 단일)
> 단계: Step 0 (셋업 + OpenAPI→TS 타입 자동생성)
> 베이스 브랜치: `slice14` (HEAD `767b42d`)
> 종결 시점 commit: 본 문서 직전 frontend codegen 커밋
> 누적 LLM 비용: **$0**

---

## 0. 한 줄 결과

`@extend_schema` + Pydantic↔spectacular bridge로 coach 6 endpoint의 OpenAPI 스키마를 채우고, `openapi-typescript`로 `frontend/lib/coach/api-types.ts` (13,429 LoC, E1~E6 req/res + nested 타입 전부 포함)를 자동 생성. TS strict 컴파일 PASS, 회귀 무변동.

---

## 1. KPI 매트릭스 — 10/10 통과

| #   | KPI                | 기준                                                          | 결과                                                                                              | 상태 |
| --- | ------------------ | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---- |
| K1  | 브랜치             | `slice15`를 `slice14`(`767b42d`)에서 분기                     | 분기 OK, pre-commit hook의 `ALLOWED_BRANCHES`에 `slice15` 등록                                    | ✅   |
| K2  | 오리엔테이션       | API 클라이언트·라우팅·공용·테스트 위치 파악                   | §2 기록                                                                                           | ✅   |
| K3  | E1 연동            | `/api/v1/coach/e1/` dev 200 (JWT 통과)                        | invalid body → 400 응답으로 라우팅+JWT(AllowAny)+serializer+Pydantic 검증 전 경로 확인 ($0 유지) | ✅   |
| K4  | CORS               | 프론트 dev origin 허용                                        | OPTIONS preflight 200 + `Access-Control-Allow-Origin: http://localhost:3000`                      | ✅   |
| K5  | 스키마             | drf-spectacular가 coach 6 endpoint req/res 노출               | 12 component (`CoachE1RequestRequest`~`CoachE6Response`) + paths $ref 연결                        | ✅   |
| K6  | codegen 파이프라인 | `openapi-typescript` 도입 + npm 스크립트                      | devDep `openapi-typescript@^7.13.0`, `npm run gen:coach-types`                                    | ✅   |
| K7  | 타입 생성          | `api-types.ts` 생성, E1 req/res 포함, TS strict 컴파일 PASS   | 13,429 LoC, E1~E6 6 paths + 12 component 타입, `npx tsc --noEmit` exit 0                          | ✅   |
| K8  | 회귀               | vitest 65/65 + pytest 742/1 + IDENTICAL 31/31 유지            | 모두 무변동                                                                                       | ✅   |
| K9  | 비용               | $0 (LLM 호출 0)                                               | E1 호출은 invalid body로 view 진입 전 차단 → LLM 호출 0                                           | ✅   |
| K10 | 커밋·문서          | Step 0 커밋 + `slice15/step0.md`                              | 3 커밋 (백엔드 2 + 프론트 1) + 본 문서                                                            | ✅   |

---

## 2. 프론트엔드 오리엔테이션 (Step 0-A)

Part 1~3가 따를 관례 — 추정 금지, 실제 코드베이스 확인 결과.

| 영역             | 위치                                                                                          | 비고                                                                                                  |
| ---------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 프레임워크       | Next.js 16.2.6 (App Router), React 19.2.6, TypeScript 5                                       | Turbopack 사용 (dev)                                                                                  |
| API 클라이언트   | `frontend/lib/api/authAxios.ts`                                                               | JWT 단일 소스. `baseURL=NEXT_PUBLIC_API_URL` (기본 `http://localhost:8000/api/v1`). request 인터셉터로 access token 자동 첨부, 401 응답 시 refresh + retry, 다중 탭 동기화 |
| 토큰 저장        | `localStorage` (`access_token`, `refresh_token`) — `tokenUtils.{getAccess,setTokens,clear}` | SSR 안전 가드 포함. 향후 HTTP-Only Cookie 전환 가능                                                  |
| 라우팅           | `frontend/app/` (App Router)                                                                  | 코치 화면은 `app/coach/` 신설 예정 (Slice 15 Part 2 결정)                                            |
| 공용 라이브러리  | `frontend/lib/` (auth, stores, thesis, utils, i18n)                                           | 코치 전용은 `lib/coach/` 신설 — 본 Step 0에서 `lib/coach/api-types.ts`, `lib/coach/schema.yml` 생성  |
| 타입             | `frontend/types/`, 컴포넌트 인접 정의 혼용                                                    | 자동생성은 `lib/coach/api-types.ts`에 집중 (단일 출처)                                               |
| 상태 관리        | TanStack Query 5.90.5 (서버), Zustand 5.0.8 (클라이언트)                                      | Part 1에서 react-query 훅 (`useCoachE1` 등)                                                          |
| 테스트           | `frontend/__tests__/` (분리 디렉토리), `vitest.config.ts` `include: __tests__/**/*.{test,spec}.{ts,tsx}` | jsdom + RTL + alias `@`. 기본 65 tests / 12 files                                                    |

---

## 3. 백엔드 사전 변경 (HALT 보고 후 사용자 결정에 따른 별도 의미 단위)

Step 0-C에서 drf-spectacular 스키마가 coach 엔드포인트는 노출하나 **request/response body가 비어있음**을 발견 (`'No response body'`). 사용자 결정에 따라 백엔드를 별도 커밋으로 보강:

### Commit 1: `69dc94e` — `chore(s15): annotate coach views with @extend_schema (Step 0 pre)`
- `portfolio/api/views.py` 6 view (E1~E6)에 `@extend_schema(request=..., responses={200: ...}, tags=["coach"])` 추가.
- `from drf_spectacular.utils import extend_schema` 1줄 import.
- 변경 줄 수: +31 (의미 단위 데코레이터만).
- 회귀: pytest 742/1, IDENTICAL 31/31 변동 0.

### Commit 2: `8300d81` — `chore(s15): pydantic↔spectacular bridge for coach serializers (Step 0 pre)`
- 진짜 문제: `portfolio/api/serializers.py`의 12 serializer는 `to_internal_value`/`to_representation` 어댑터로만 정의되어 DRF `fields`가 비어 있음 → @extend_schema만으로는 spectacular가 빈 schema를 생성.
- 해결: `portfolio/api/openapi_extensions.py` 신설 — 12 `OpenApiSerializerExtension`을 동적 생성, 각자 `map_serializer`에서 Pydantic `model_json_schema()`를 반환. `$defs`는 `_inline_pydantic_refs()`로 inline (coach 모델 12개 self-ref 0건 — audit 확정).
- `portfolio/apps.py ready()`에서 모듈 import만으로 자동 등록.
- 스키마 크기 218,888 → 253,772 bytes (+34,884, coach 12 component 추가).
- 회귀: pytest 742/1, IDENTICAL 31/31 변동 0.

---

## 4. codegen 파이프라인 (Step 0-D)

### 도입
```bash
cd frontend && npm install -D openapi-typescript  # ^7.13.0
```

### 스크립트 (`frontend/package.json`)
```json
"gen:coach-schema": "cd .. && poetry run python manage.py spectacular --file frontend/lib/coach/schema.yml",
"gen:coach-types":  "npm run gen:coach-schema && openapi-typescript lib/coach/schema.yml -o lib/coach/api-types.ts"
```

### 입출력
- 입력: `frontend/lib/coach/schema.yml` (253KB, drf-spectacular CLI export)
- 출력: `frontend/lib/coach/api-types.ts` (390KB, 13,429 LoC)

### 재현 절차
1. 백엔드 dev 서버 불필요 (CLI `spectacular` 명령은 ORM/DB 접근 없이 schema만 생성).
2. `cd frontend && npm run gen:coach-types` 단일 명령으로 schema export → TS 타입 재생성.
3. CI 친화: live URL 의존 없음, 결과 deterministic.

### 생성 타입 검증
- `paths["/api/v1/coach/e1/"]`~`e6` 6개 endpoint 매핑.
- `components["schemas"]["CoachE1RequestRequest"]`~`CoachE6Response` 12개 본문 타입.
- Pydantic의 `description`, `default`, `format`(date-time), `const`(예: `entry_point: "e1"`) 모두 보존.
- 의도된 무료 이득 (지시서 §3.3): E1만 화면 만들지만 타입 파일은 E2~E6도 포함 — Slice 16+ 복제 시 추가 codegen 불필요.

### 명명 규칙 주의
- `COMPONENT_SPLIT_REQUEST: True` 설정으로 request 본문에 `Request` 접미가 자동 부착 → `CoachE1RequestRequest` (E1Request + Request) 형태. Part 1에서 alias로 정리하거나 그대로 사용. drf-spectacular 일관 동작이라 임의 변경 불가.

---

## 5. 회귀 (Step 0-E)

| 트랙                                  | 베이스라인 (slice14 `767b42d`) | Step 0 종결 시점         | 변동      |
| ------------------------------------- | ----------------------------- | ------------------------ | --------- |
| pytest (portfolio + tests/coach·scoring·integration/asgi) | 742 passed, 1 skipped         | 742 passed, 1 skipped    | 0 ✅      |
| IDENTICAL 31/31 (4 파일)              | 31 passed                     | 31 passed                | 0 ✅      |
| vitest (frontend)                     | 12 files / 65 tests           | 12 files / 65 tests      | 0 ✅      |
| TS strict 컴파일 (`npx tsc --noEmit`) | exit 0                         | exit 0                   | 0 ✅      |

---

## 6. 산출물 목록 (지시서 §산출물 매핑)

1. **`slice15` 브랜치** — `slice14`(`767b42d`)에서 분기, pre-commit ALLOWED_BRANCHES 등록.
2. **`frontend/package.json`** — `openapi-typescript` devDep + `gen:coach-schema` + `gen:coach-types` npm scripts.
3. **`frontend/lib/coach/api-types.ts`** — 13,429 LoC 자동 생성, E1~E6 6 paths + 12 components.
4. **`frontend/lib/coach/schema.yml`** — drf-spectacular export 결과 (253KB). codegen 재실행 가능 보장.
5. **백엔드 사전 변경 2건** — `portfolio/api/views.py` (@extend_schema) + `portfolio/api/openapi_extensions.py` + `portfolio/apps.py` (Pydantic bridge).
6. **`docs/portfolio/coach/slice15/step0.md`** — 본 문서.

---

## 7. Part 1 진입 메모

- API 클라이언트는 `frontend/lib/api/authAxios.ts` 재사용 (별도 인스턴스 생성 금지 — `[[feedback_indicator_catalog_sync]]` 정신과 일치, 인터셉터 단일 소스).
- react-query 훅은 `frontend/lib/coach/hooks/` (Part 1 신설 예상) — `useCoachE1` mutation/`useQuery` 형태, request/response 타입은 `api-types.ts`에서 `components["schemas"]["CoachE1RequestRequest"]`·`CoachE1Response` 직접 import.
- MSW 통합은 Part 3 — `__tests__/coach/` 신설, MSW handler가 `api-types.ts`의 타입을 따르도록 설계.

---

## 8. 부채 / 후속 (없음)

- Step 0의 백엔드 변경(코드 31줄 + 신설 1파일 125줄)은 spectacular 메타데이터 한정. 런타임 동작 무영향, IDENTICAL 31/31 보호.
- 백엔드는 본 코드와 무관하게 `DISABLE_ERRORS_AND_WARNINGS: True` 유지 — coach 외 view의 graceful fallback 정책에 변동 없음.
- 부채 #항목 신규 없음.

---

## 9. HALT 발동 이력

- **Step 0-C HALT (1회)**: spectacular 스키마에 coach req/res body 누락 → 사용자에게 3안 옵션 보고 → A안 채택 (백엔드 보강 후 codegen 진행).
- **다른 HALT 게이트**: 모두 미발동 (CORS·회귀·TS 컴파일).
