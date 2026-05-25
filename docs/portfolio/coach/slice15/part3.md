# Slice 15 Part 3 작업 지시서 — 통합 검증 + Slice 15 종결

> 대상: Claude Code 실행 환경
> 슬라이스: Slice 15 (프론트 코치 화면 — E1 GARP 진단, 파일럿 단일) — **마지막 Part**
> 이번 단계: Part 3 — 통합 테스트 보강 + 실 백엔드 스모크(P3-C) + Slice 15 종결(KPI 종합·회고·부채·문서)

---

## 0. 컨텍스트 & 작업 원칙

### 0.1 현재 위치

- Step 0 + Part 1 + Part 2 종결(`slice15` HEAD = `4dee270`): codegen 파이프라인, 데이터 레이어(`useE1Coach`), E1 화면(라우트·폼·CommentaryCard·3-상태), 회귀 vitest 70 / pytest 742/1 / IDENTICAL 31/31.
- Part 3는 신규 기능이 아니라 **마무리** — 검증 보강 + 실 연동 실증 + 슬라이스 종결.

### 0.2 작업 원칙 (HALT 규칙)

- **타입·회귀 게이트**: `npx tsc --noEmit` 실패, 또는 기존 vitest 70건 중 신규 실패 → 중단·보고.
- **데이터·UI 불변**: Part 3는 검증·종결만 — `lib/coach/*`·E1 화면·CommentaryCard 로직을 바꾸지 않는다. 보강 테스트가 버그를 드러내면 → 중단·보고(별도 수정 판단 필요).
- **비용**: P3-C 미포함 시 $0. 포함 시 LLM 1콜(~$0.01–0.02) — CostGuard·cost ledger 경유, 슬라이스 cap $1.00 내.
- 백엔드 코드 무변경.

### 0.3 브랜치

`slice15` 계속(HEAD `4dee270`). Part 3 커밋은 `slice15` 위에. Part 3 종결 = Slice 15 종결 → Slice 16은 종결된 `slice15` HEAD에서 분기.

---

## P3-A — 통합 테스트 보강 (light)

Part 2의 화면 테스트(빈/happy/error 3건)를 종결 수준으로 보강. **과하게 늘리지 않는다** — 파일럿 규모에 맞춰 핵심 갭만.

1. **접근성 단언 추가** — Part 2가 넣은 `aria-live`/`role=alert`/`aria-busy`가 각 상태에서 실제로 올바르게 붙는지 테스트로 단언(로딩 시 `aria-busy`, 에러 시 `role=alert` 등).
2. **폼 검증 동작** — 빈/무효 포트폴리오 제출이 막히는지 1케이스.
3. **에러 문구 비노출 재확인** — 원시 `AxiosError`/500이 화면에 안 뜨는지(Part 2가 이미 검증했으면 중복 생략).
4. 신규 테스트 N건 → vitest `70 → 70+N`. 보강이 불필요할 만큼 Part 2 커버리지가 충분하면 그 판단을 종결 문서에 기록하고 생략 가능.

---

## P3-B — Slice 15 KPI 종합 & 회고 & 부채

1. **Slice 15 종합 KPI 매트릭스** — Step 0 + Part 1 + Part 2 + Part 3의 KPI를 한 표로 집계(전부 PASS 확인).
2. **회고** — E1 파일럿이 확립한 것, E2~E6 복제 시 따를 패턴:
   - 데이터 레이어 패턴(types alias → api → useMutation 훅)
   - UI 패턴(클라이언트 페이지 + 폼 + 순수 CommentaryCard + 3-상태)
   - AuthGuard 우회 테스트 패턴(default export 보호 / named export 테스트 진입)
   - **복제 함정 목록**(Part 2에서 수집된 것 포함, 종결 문서에 명시):
     - `fetched_at`은 제출 핸들러 내부에서만 생성(hydration 회피)
     - `holdings`의 `sector`/`asset_class`/`name` = `null` 자동 채움(Pydantic nullable)
     - `garp_metrics`는 ticker별 nested dict `{TICKER: {metric: value}}`
     - API path는 `/coach/e1/` (baseURL이 `/api/v1` 포함)
     - 응답은 봉투 형태 `{output, llm_metadata, ...}` — `response.output`이 진단 본체
3. **부채 정리** — Slice 15에서 발생/확인된 부채를 `debts.md`에 등록:
   - E1 view `permission_classes([AllowAny])` (감사 P0 #5) — 공개/배포 전 해소 필요(추적 부채).
   - 외부 자동화의 working tree 브랜치 전환 재발성 환경 이슈 — 사례 기록.
   - Step 0 KPI가 "타입 존재+컴파일"만 검증하고 "실 응답 shape 일치"를 누락했던 점(P1-0에서 사후 해소) — 스키마 파이프라인 KPI 설계 교훈.

---

## P3-C — 실 백엔드 E1 스모크 (조건부 — 결정 A 채택 시; B 채택 시 이 절 생략)

E1 화면이 의존하는 전 스택을 실제 백엔드로 1회 실증한다.

1. dev 백엔드 기동. 유효한 JWT 확보(기존 dev 인증 흐름).
2. **실제 `POST /api/v1/coach/e1/` 호출 1회** — 작고 현실적인 포트폴리오 입력(`E1Request` 형태)으로. 스크립트/`curl` 방식으로 충분(브라우저 구동 불요).
3. 검증:
   - HTTP 200.
   - 응답이 봉투 형태 `{output, llm_metadata, gate_tier?, preset_id?, scores?}`인지.
   - `output`이 `E1Output` 필드(`summary`/`key_observations`/`confidence`/`action_items`/`risk_flags`/`metrics_table`)를 갖는지 — 즉 **실 응답이 생성 타입 `E1Response`와 실제로 일치**하는지.
4. **비용** — LLM 1콜. CostGuard 경유, cost ledger에 기록. ~$0.01–0.02 예상, 슬라이스 cap $1.00 내 확인.
5. 스모크 결과(응답 shape 일치 여부, 비용)를 종결 문서에 기록. 실패·불일치 시 → HALT, 보고.
6. (선택, 병진 수동) dev 서버에서 브라우저로 E1 화면을 직접 한 번 확인 — 자동화 범위 밖, 권장 사항으로만 안내.

---

## P3-D — Slice 15 종결

1. **종결 문서**: `docs/portfolio/coach/slice15/closing.md` — 종합 KPI, 회고, 복제 함정 목록, 부채, (P3-C 시) 스모크 결과·비용.
2. **최종 회귀 확인**: `vitest 70+N` 전건 + `tsc` exit 0 + `pytest 742/1` + `IDENTICAL 31/31`.
3. **커밋** — 다단계 패턴, 의미 단위:
   - (P3-A 시) `test(s15): integration test hardening — a11y + form validation (Part 3)`
   - `docs(s15): Slice 15 closing — KPI rollup, retrospective, replication traps`
4. Slice 15 종결 — `slice15` HEAD가 종결 상태. Slice 16은 여기서 분기.

---

## Slice 15 Part 3 KPI 매트릭스

| #     | KPI                | 통과 기준                                                              |
| ----- | ------------------ | ---------------------------------------------------------------------- |
| P3-K1 | 테스트 보강        | a11y·폼 검증 단언 추가(또는 충분 판단 기록), vitest 70→70+N            |
| P3-K2 | 종합 KPI           | Step 0+P1+P2+P3 KPI 집계, 전부 PASS                                    |
| P3-K3 | 회고·함정 목록     | E2~E6 복제 패턴 + 복제 함정 목록 종결 문서에 명시                      |
| P3-K4 | 부채 등록          | AllowAny(P0 #5)·환경 이슈·KPI 교훈 `debts.md` 등록                     |
| P3-K5 | 실 스모크 (조건부) | A 채택 시: 실 E1 200 + 봉투 형태 + `E1Response` 일치 확인, ledger 기록 |
| P3-K6 | 최종 회귀          | vitest 70+N + tsc exit 0 + pytest 742/1 + IDENTICAL 31/31              |
| P3-K7 | 비용               | P3-C 미포함 $0 / 포함 시 cap $1.00 내, ledger 기록                     |
| P3-K8 | 종결               | `slice15/closing.md` + Part 3 커밋, Slice 15 종결                      |

---

## 산출물 목록

1. (P3-A 시) 보강 테스트 — `__tests__/coach/` 내 a11y·폼 검증
2. `docs/portfolio/coach/slice15/closing.md` — Slice 15 종결 문서
3. `debts.md` 갱신 — Slice 15 부채 등록
4. (P3-C 시) cost ledger 항목 — E1 스모크 1콜

---

## HALT 규칙 요약

- `tsc --noEmit` 실패 / 기존 vitest 70 깨짐 → 중단·보고
- 보강 테스트가 화면·데이터 레이어 버그를 드러냄 → 중단·보고 (별도 수정 판단)
- (P3-C) 실 스모크가 비-200 또는 응답 shape ↔ `E1Response` 불일치 → 중단·보고
- 백엔드 코드 변경 필요 발생 → 중단·보고

---

## 한눈 요약

```
P3-A : 통합 테스트 보강 — a11y 단언 + 폼 검증 (light, 과확장 금지)
P3-B : Slice 15 종합 KPI + 회고 + 복제 함정 목록 + 부채 등록
P3-C : (조건부/추천) 실 백엔드 E1 스모크 1회 — 전 스택 round-trip 실증, ~$0.01-0.02
P3-D : closing.md + 최종 회귀 → Slice 15 종결
다음 : Slice 16 — E2~E6 화면을 E1 패턴으로 복제 (종결된 slice15에서 분기)
```
