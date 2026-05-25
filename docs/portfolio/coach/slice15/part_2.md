# Slice 15 Part 2 작업 지시서 — E1 화면 UI

> 대상: Claude Code 실행 환경
> 슬라이스: Slice 15 (프론트 코치 화면 — E1 GARP 진단, 파일럿 단일)
> 이번 단계: Part 2 — Part 1 데이터 레이어를 소비하는 **투자자가 실제로 보는 화면**. 라우트 + 포트폴리오 입력 + 진단 결과 표시.

---

## 0. 컨텍스트 & 작업 원칙

### 0.1 현재 위치

- Part 1 종결(`slice15` HEAD = `9de1cdb`): 데이터 레이어 완성 — `lib/coach/{types,api,hooks}.ts`, MSW 인프라, `useE1Coach` 훅, `defaultE1Response`(봉투 형태 baseline).
- Part 2는 그 위에 **UI 계층**을 올린다. 데이터 레이어(`useE1Coach`)는 그대로 소비만 — 수정하지 않는다.
- E1 응답은 봉투 형태: `{ output: {summary, key_observations, confidence, action_items, risk_flags, metrics_table}, llm_metadata, gate_tier?, preset_id?, scores? }`. 화면이 표시하는 진단 본체는 `response.output`.

### 0.2 Step 0/Part 1에서 확정된 관례 (이대로 따른다)

- 라우팅: `frontend/app/` (App Router) — 코치 화면은 `app/coach/` 신설.
- 컴포넌트: `frontend/components/` 관례.
- 데이터 진입점: `lib/coach/hooks.ts`의 `useE1Coach`, 타입은 `lib/coach/types.ts`.
- 테스트: `frontend/__tests__/`, jsdom + RTL + alias `@`, MSW 서버는 Part 1에서 셋업 완료.
- react-query QueryClientProvider는 앱 루트 기존.

### 0.3 작업 원칙 (HALT 규칙)

- **타입 게이트**: `npx tsc --noEmit` 실패 시 → 중단·보고.
- **회귀 게이트**: 기존 vitest 67건 중 신규 실패 → 중단·보고.
- **데이터 레이어 불변**: `lib/coach/{types,api,hooks}.ts`·MSW 인프라는 Part 2에서 수정하지 않는다. 수정 필요가 생기면 → 중단·보고(Part 1 설계 결함 신호).
- Part 2는 프론트 전용 — 백엔드 무변경. `pytest`/`IDENTICAL` 손대지 않음.
- LLM 실호출 0 — 화면 동작 확인은 MSW 가짜 응답으로. 예상 비용 $0.

### 0.4 디자인 원칙

- **기존 디자인 시스템 재사용** — 프론트에 이미 있는 컴포넌트·토큰·스타일 관례를 따른다. 새 디자인 언어를 만들지 않는다(파일럿이므로 일관성 우선).
- 이 화면이 **6개 코치 화면의 UI 본보기** — 컴포넌트 분해를 E2~E6가 복제 가능한 형태로.

### 0.5 브랜치

`slice15` 계속(HEAD `9de1cdb`). Part 2 커밋은 `slice15` 위에.

---

## P2-A — 라우트 & 페이지 골격

1. **코치 라우트 신설** — `frontend/app/coach/e1/page.tsx` (App Router 관례에 맞춰; `app/coach/` 하위 구조는 기존 라우팅 패턴 확인 후 결정).
2. 페이지는 **클라이언트 컴포넌트**(`'use client'`) — `useE1Coach`(react-query 훅)와 폼 상태를 쓰므로.
3. 페이지 골격: 제목/설명 영역 + 입력 폼 영역(P2-B) + 결과 영역(P2-C). 결과 영역은 진단 전에는 비어 있거나 안내 문구.
4. 인증: 코치 화면은 로그인 사용자 대상 — 기존 앱의 보호 라우트(protected route) 관례가 있으면 그대로 적용. 없으면 페이지에서 별도 처리하지 말고 보고.

---

## P2-B — 포트폴리오 입력 폼

투자자가 진단받을 포트폴리오를 입력하는 영역. 제출 시 `useE1Coach.mutate(request)` 호출.

1. 입력 폼은 `E1Request` 타입(`lib/coach/types.ts`)이 요구하는 필드 구조를 따른다 — `E1Request`의 실제 형태를 확인해 그에 맞는 입력 UI 구성(종목·비중 등 포트폴리오 구성 입력).
2. 폼 상태 관리는 가벼운 로컬 상태(React `useState`)로 충분 — 파일럿이므로 폼 라이브러리 도입은 보류. 기존 앱에 폼 컨벤션이 있으면 그걸 따른다.
3. **제출 동작**: 제출 버튼 → `E1Request` 형태로 조립 → `mutate()` 호출.
4. **제출 전 최소 검증**: 빈 포트폴리오 등 명백히 무효한 입력은 제출 막기(클라이언트 측 가벼운 검증). 단 본격 검증은 백엔드 serializer가 하므로 과하게 만들지 않는다.
5. **제출 중 상태**: `isPending` 동안 버튼 비활성화 + 로딩 표시.

---

## P2-C — 진단 결과 표시 (CommentaryCard)

`useE1Coach`가 돌려준 진단(`response.output`)을 표시하는 컴포넌트. **6화면 재사용을 염두에 둔 본보기 컴포넌트.**

1. `frontend/components/coach/CommentaryCard.tsx` 신설(컴포넌트 관례 경로에 맞춰).
2. `E1Output`의 표시 필드를 렌더:
   - `summary` — 진단 요약
   - `key_observations` — 핵심 관찰 목록
   - `confidence` — 신뢰도
   - `action_items` — 액션 아이템 목록
   - `risk_flags` — 리스크 플래그
   - `metrics_table` — 지표 표
   - 각 필드의 실제 타입은 `lib/coach/types.ts`의 `E1Response`/`E1Output`에서 확인.
3. **세 가지 상태를 명시 처리** — 코치 화면 UX의 핵심:
   - **로딩**(`isPending`): 진단 생성 중임을 알리는 표시.
   - **에러**(`error`): 진단 실패 시 사용자에게 알림(원시 에러 노출 금지 — 사람이 읽을 메시지).
   - **빈 상태**(제출 전): 결과 영역의 안내 문구.
4. CommentaryCard는 `E1Output`(혹은 더 일반화하면 공통 output) 데이터를 prop으로 받는 **순수 표시 컴포넌트**로 — 데이터 페칭을 컴포넌트 안에서 하지 않는다. 그래야 E2~E6가 같은 카드를 재사용한다.

---

## P2-D — 화면 렌더 테스트

E1 화면을 MSW 위에서 렌더 검증. (데이터 레이어 단위 테스트는 Part 1에서 완료 — 여기선 화면 컴포넌트.)

1. 테스트 파일: `frontend/__tests__/coach/e1-page.test.tsx`(테스트 관례에 맞춰).
2. RTL로 E1 페이지 렌더, `QueryClientProvider`로 감싼다. MSW 서버는 Part 1 셋업 재사용.
3. 검증 케이스(최소):
   - **빈 상태**: 진단 전 결과 영역이 안내 문구/빈 상태로 렌더.
   - **happy-path**: 폼 입력 → 제출 → MSW 200(`defaultE1Response`) → CommentaryCard에 `summary`·`action_items` 등이 표시.
   - **에러-path**: MSW 에러 핸들러 → 사람이 읽을 에러 메시지 표시.
4. 신규 테스트 M건 추가 → vitest `67 → 67+M`.

---

## P2-E — 회귀 & 커밋

1. **회귀 게이트**:
   - `npx tsc --noEmit` → exit 0.
   - `vitest` → 기존 67건 전건 통과 + 신규 M건 = `67+M`.
   - 백엔드 미변경 — `pytest`/`IDENTICAL` 미실행 가능(변경 시 HALT).
2. **커밋** — 다단계 커밋 패턴, 의미 단위 분리(권장 2~3커밋):
   - 결과 표시 컴포넌트: `CommentaryCard` → `feat(s15): CommentaryCard — coach diagnosis display component (Part 2)`
   - 라우트 + 입력 폼: `app/coach/e1/` 페이지 + 폼 → `feat(s15): E1 coach screen — route + portfolio input form (Part 2)`
   - 화면 테스트: `test(s15): E1 screen render tests (Part 2)`
3. Part 2 종결 문서: `docs/portfolio/coach/slice15/part2.md` — 화면 구조(라우트·컴포넌트 경로·분해), 3-상태(로딩/에러/빈) 처리, KPI 결과.

---

## Slice 15 Part 2 KPI 매트릭스

| #      | KPI                | 통과 기준                                                       |
| ------ | ------------------ | --------------------------------------------------------------- |
| P2-K1  | 라우트             | `app/coach/e1/` 페이지 신설, 클라이언트 컴포넌트로 동작         |
| P2-K2  | 입력 폼            | `E1Request` 형태 조립, 제출 시 `useE1Coach.mutate` 호출         |
| P2-K3  | CommentaryCard     | `E1Output` 표시 필드 렌더, 순수 표시 컴포넌트(데이터 페칭 없음) |
| P2-K4  | 3-상태 처리        | 로딩·에러·빈 상태 각각 명시 UI                                  |
| P2-K5  | 데이터 레이어 불변 | `lib/coach/*`·MSW 인프라 무수정                                 |
| P2-K6  | 화면 테스트        | 빈·happy·에러 3 케이스 통과                                     |
| P2-K7  | 타입·회귀          | `tsc --noEmit` exit 0, vitest 67→67+M(기존 67 무손실)           |
| P2-K8  | 백엔드 무변경      | pytest 742/1·IDENTICAL 31/31 불변                               |
| P2-K9  | 비용               | $0 (LLM 실호출 0)                                               |
| P2-K10 | 커밋·문서          | Part 2 커밋(권장 2~3) + `slice15/part2.md`                      |

---

## 산출물 목록

1. `frontend/app/coach/e1/page.tsx` — E1 코치 화면 라우트
2. 포트폴리오 입력 폼 (페이지 내 또는 분리 컴포넌트)
3. `frontend/components/coach/CommentaryCard.tsx` — 진단 결과 표시 컴포넌트
4. `frontend/__tests__/coach/e1-page.test.tsx` — 화면 렌더 테스트
5. `docs/portfolio/coach/slice15/part2.md` — Part 2 종결 문서

---

## HALT 규칙 요약

- `tsc --noEmit` 실패 / 기존 vitest 67 깨짐 → 중단·보고
- `lib/coach/*`·MSW 인프라 수정 필요 발생 → 중단·보고 (Part 1 설계 결함 신호)
- 백엔드 코드 변경 필요 발생 → 중단·보고 (Part 2는 프론트 전용)
- 보호 라우트 등 인증 처리에 기존 관례가 없어 새 결정이 필요하면 → 중단·보고

---

## 한눈 요약

```
P2-A : 라우트 — app/coach/e1/ 페이지 골격 (클라이언트 컴포넌트)
P2-B : 포트폴리오 입력 폼 — E1Request 조립 → useE1Coach.mutate
P2-C : CommentaryCard — 진단 결과(response.output) 표시, 6화면 재사용 본보기
       + 로딩/에러/빈 3-상태 명시 처리
P2-D : 화면 렌더 테스트 — 빈·happy·에러 (MSW 기반)
P2-E : tsc + vitest 67+M 확인 → 커밋 2~3건 + Part 2 종결 문서
다음 : Part 3 — MSW 통합 테스트 강화 + Slice 15 종결
```
