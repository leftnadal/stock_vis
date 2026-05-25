# Slice 15 Step 0 작업 지시서 — 셋업 & 타입 자동생성 파이프라인

> 대상: Claude Code 실행 환경
> 슬라이스: Slice 15 (프론트 코치 화면 — E1 GARP 진단, 파일럿 단일)
> 사전 결정 확정: ① 진입점 E1 ② 구조 A 파일럿 단일 ③ 타입 B 자동생성 ④ 테스트 B MSW 통합
> 이번 단계: Step 0 — Part 1(react-query 훅)이 생성 타입에 의존하므로 선행되는 셋업 단계

---

## 0. 컨텍스트 & 작업 원칙

### 0.1 현재 위치

- 14슬라이스(백엔드 두뇌) + API 6진입점(`/api/v1/coach/eN/`, Slice 13) + 보안 C 계획 완료.
- Slice 15 = **처음으로 투자자가 화면에서 직접 쓰는 부분.** 기존 Next.js 앱(App Router / react-query + zustand + axios + JWT)에 코치 진단 화면 추가.
- 파일럿 구조(결정 ②): Slice 15는 **E1 화면 하나만** end-to-end 완성. E2~E6은 Slice 16+에서 복제.

### 0.2 Slice 15 로드맵 (이번은 Step 0만)

| 단계                     | 내용                                                                   |
| ------------------------ | ---------------------------------------------------------------------- |
| **Step 0 (이번 지시서)** | 셋업 검증 + OpenAPI→TS 타입 자동생성 파이프라인 구축                   |
| Part 1                   | API 연동 레이어 — react-query 훅, API 클라이언트, MSW mock 핸들러 기반 |
| Part 2                   | E1 화면 UI — 라우트, 입력 폼, CommentaryCard, 로딩/에러 상태           |
| Part 3                   | MSW 통합 테스트 + vitest 회귀 + 종결 문서                              |

### 0.3 브랜치

```
git checkout slice14          # HEAD = 3b81052 (C-bundle 머지 완료 상태)
git checkout -b slice15
```

Slice 15는 보안 C 계획이 통합된 `slice14`(`3b81052`)에서 분기.

### 0.4 작업 원칙 (HALT 규칙)

- **연동 검증 게이트**: API 연결·JWT 인증·CORS 검증에서 실패가 나오면 → **즉시 중단, 보고.** 백엔드 설정을 임의로 수정하지 말 것 — 설정 변경은 별도 판단이 필요할 수 있음.
- **스키마 게이트**: drf-spectacular 스키마에 coach 엔드포인트가 없으면 → 중단, 보고.
- **타입/회귀 게이트**: TS strict 컴파일 실패, 또는 vitest 회귀가 65/65에서 깨지면 → 중단, 보고.
- 코드 0줄의 LLM 호출 — Step 0는 셋업뿐. 예상 비용 $0.

---

## Step 0-A — 프론트엔드 코드베이스 오리엔테이션

본 작업 전에 기존 프론트 구조를 파악한다(경로를 추정하지 말고 실제로 확인).

1. 프론트 루트(`frontend/`) 진입, 스택 확인 — Next.js 버전, App Router 구조.
2. **API 클라이언트 위치** — axios 인스턴스가 어디서 설정되는지(baseURL, 인터셉터), JWT 토큰이 요청에 어떻게 실리는지.
3. **라우팅 구조** — App Router 라우트가 어디에 정의되는지(`app/` 하위). 코치 화면을 어디에 둘지 관례 파악(예: `app/coach/`).
4. **공용 코드 위치** — `lib/`·`types/`·`components/` 등의 관례. 생성 타입과 코치 코드를 둘 위치 결정 근거.
5. **테스트 셋업** — vitest 설정 파일, 기존 테스트 위치·관례, RTL 사용 여부.
6. 파악 결과를 Step 0 종결 문서에 간단히 기록(Part 1~3가 이 관례를 따름).

---

## Step 0-B — API 연동 & 인증 검증 (HALT 게이트)

코치 화면이 의존할 백엔드 연결이 dev 환경에서 정상인지 **검증만** 한다(빌드 아님).

1. 백엔드 dev 서버 기동 가능 확인.
2. `/api/v1/coach/e1/` 엔드포인트가 dev에서 정상 응답하는지 확인 — 기존 axios + JWT 인증 흐름을 통해. (E1 요청 스키마에 맞는 최소 샘플 요청으로 200 응답 확인.)
3. **CORS** — 프론트 dev origin이 백엔드 CORS 허용 목록에 있는지 확인.
4. 위 3건 중 하나라도 실패 → **HALT.** 무엇이 어떻게 실패했는지 그대로 보고. 백엔드 설정을 임의 수정하지 않는다.

---

## Step 0-C — OpenAPI 스키마 확인 (HALT 게이트)

1. drf-spectacular는 이미 작동 중(병진 확인). 스키마 엔드포인트(통상 `/api/schema/`)가 coach 6 엔드포인트(`/api/v1/coach/e1/`~`e6/`)를 **요청·응답 스키마와 함께** 노출하는지 확인.
2. 특히 E1의 request body / response body 스키마가 스키마 문서에 제대로 들어 있는지 확인.
3. coach 엔드포인트가 스키마에 누락돼 있으면 → **HALT, 보고.**

---

## Step 0-D — 타입 자동생성 파이프라인 구축 (결정 ③ 본작업)

백엔드 스키마 ↔ 프론트 TS 타입을 자동 동기화하는 파이프라인을 만든다.

1. **`openapi-typescript`를 프론트 devDependency로 추가** (`npm install -D openapi-typescript` 또는 프로젝트 패키지 매니저 방식).
2. **codegen 스크립트 추가** — `package.json`에 npm 스크립트(예: `gen:coach-types`). 권장 구조(재현성):
   - 백엔드에서 OpenAPI 스키마를 파일로 export (`python manage.py spectacular --file schema.yml` 또는 프로젝트에 이미 있는 export 경로 활용).
   - 그 스키마 파일을 입력으로 `openapi-typescript`가 TS 타입 파일 생성.
   - 라이브 URL 직접 읽기보다 export 파일 기반이 재현성·CI 친화적. 단 프로젝트에 이미 다른 관례가 있으면 그걸 따른다.
3. **타입 파일 생성** — codegen 스크립트를 1회 실행해 타입 파일 생성. 위치는 Step 0-A에서 파악한 `lib/` 관례에 맞춰(예: `frontend/lib/coach/api-types.ts`).
   - 참고: `openapi-typescript`는 스키마 전체를 한 파일로 생성하므로, **api-types.ts는 자연히 E1~E6 6개 엔드포인트 타입을 모두 포함**한다. E1 화면만 만들지만(파일럿) 타입 파일은 전체 커버 — Slice 16+ 복제 시 추가 codegen 불필요. 이는 의도된 무료 이득.
4. **검증** — 생성된 타입 파일에 E1(및 나머지) coach 엔드포인트의 req/res 타입이 포함됐는지 확인. **TS strict 컴파일이 새 파일 포함 상태에서 PASS**해야 한다.

---

## Step 0-E — 회귀 확인 & 커밋

1. **회귀 게이트**:
   - 프론트 `vitest` → **65/65 유지** (Step 0는 화면을 추가하지 않으므로 변동 없어야 정상).
   - 백엔드 `pytest` → 742/1, **IDENTICAL 31/31** — Step 0는 백엔드 코드 무변경이므로 그대로. (변경 시 HALT.)
2. **커밋** — Stock-Vis 다단계 커밋 패턴. Step 0의 의미 단위:
   - 코드/설정 커밋: `openapi-typescript` devDep + codegen 스크립트 + 생성된 `api-types.ts` (+ 필요 시 export된 schema 파일).
   - **커밋 메시지 예**: `chore(s15): set up OpenAPI->TS coach type-gen pipeline (Step 0)`
3. Step 0 종결 문서: `docs/portfolio/coach/slice15/step0.md` — 오리엔테이션 결과(API 클라이언트·라우팅·테스트 관례 위치), 연동 검증 결과, codegen 파이프라인 사용법(스크립트명·입출력 경로), KPI 결과.

---

## Slice 15 Step 0 KPI 매트릭스

| #   | KPI                | 통과 기준                                                   |
| --- | ------------------ | ----------------------------------------------------------- |
| K1  | 브랜치             | `slice15`을 `slice14`(`3b81052`)에서 분기                   |
| K2  | 오리엔테이션       | API 클라이언트·라우팅·공용코드·테스트 셋업 위치 파악·기록   |
| K3  | E1 연동            | `/api/v1/coach/e1/` dev 200 응답 (JWT 인증 통과)            |
| K4  | CORS               | 프론트 dev origin 허용 확인                                 |
| K5  | 스키마             | drf-spectacular 스키마가 coach 6 엔드포인트 req/res 노출    |
| K6  | codegen 파이프라인 | `openapi-typescript` 도입 + npm 스크립트 추가               |
| K7  | 타입 생성          | `api-types.ts` 생성, E1 req/res 포함, TS strict 컴파일 PASS |
| K8  | 회귀               | vitest 65/65 + pytest 742/1 + IDENTICAL 31/31 유지          |
| K9  | 비용               | $0 (LLM 호출 0)                                             |
| K10 | 커밋·문서          | Step 0 커밋 + `slice15/step0.md`                            |

---

## 산출물 목록

1. `slice15` 브랜치
2. `frontend/package.json` — `openapi-typescript` devDep + `gen:coach-types` 스크립트
3. `frontend/lib/coach/api-types.ts` (관례에 맞춘 경로) — 생성된 6 엔드포인트 타입
4. (해당 시) export된 OpenAPI schema 파일
5. `docs/portfolio/coach/slice15/step0.md` — Step 0 종결 문서

---

## HALT 규칙 요약

- API 연결·JWT·CORS 검증 실패 → 중단·보고 (백엔드 설정 임의 수정 금지)
- drf-spectacular 스키마에 coach 엔드포인트 누락 → 중단·보고
- TS strict 컴파일 실패 / vitest 65/65 깨짐 / 백엔드 회귀·IDENTICAL 변동 → 중단·보고

---

## 한눈 요약

```
Step 0-A : 프론트 코드베이스 오리엔테이션 (API 클라이언트·라우팅·테스트 관례 파악)
Step 0-B : E1 API 연동 검증 — dev 200 응답 + JWT + CORS (검증만, HALT 게이트)
Step 0-C : drf-spectacular 스키마가 coach 엔드포인트 노출하는지 확인
Step 0-D : openapi-typescript 파이프라인 구축 → api-types.ts 생성 (E1~E6 전체 커버)
Step 0-E : vitest 65/65 유지 확인 → Step 0 커밋 + 종결 문서
다음     : Part 1 — react-query 훅 + API 클라이언트 (생성 타입 위에서)
```
