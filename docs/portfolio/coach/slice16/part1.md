# Slice 16 Part 1 — E2 코치 화면 (E1 패턴 복제)

> 목표: Slice 15에서 확립한 E1 화면 패턴을 E2(종합 진단) 화면으로 기계적 복제.
> 신규 결정 사항 없음 — 패턴 복제 + P3-C(E2) 실 검증.
> 분기 기준: `slice16` 브랜치, HEAD `b6f3e51` (Step 0 종결).

---

## 0. Pre-flight (코드 작성 전 필수)

### 0-1. 환경 안전장치 (#71 대응)

- 작업 시작 직후 `git branch --show-current` → `slice16` 확인.
- `git rev-parse HEAD` → `b6f3e51` 확인 (Step 0 종결 커밋).
- 아래 태그가 없으면 생성: `git tag slice16-step0-done b6f3e51`
- 작업 중 working tree가 `iron-trading-api`로 전환되면 **즉시 HALT·보고**.
  → 복구: `git checkout slice16` (신규 파일은 untracked로 보존됨).

### 0-2. 사실관계 점검 (메모리 추정 금지 — Slice 15 학습)

지시서의 필드명·구조는 추정이다. **코드 작성 전 실제 소스를 확인**하고, 아래와 불일치하면 HALT·보고할 것.

1. **E2 codegen 타입 존재 확인** — Slice 15 Step 0 codegen이 6 endpoint 전부를 커버했는지.
   `CoachE2Request` / `CoachE2Response`(봉투 포함)가 생성 타입 파일에 있는지 확인.
   → 없으면 codegen 파이프라인 재실행 (`openapi_extensions.py` bridge 경유).
2. **E2 Pydantic schema 실제 필드 확인** — `portfolio/schemas/` 의 E2 Request/Response 정의를
   직접 열어 실제 shape 확보. 폼·타입은 이 실측값 기준으로 작성.
3. **E2 service 확인** — `portfolio/services/coach/e2_service.py` 에 Step 0에서 추가된
   `entry_point="e2"` 가 이미 반영돼 있음. 변경 불필요, 확인만.
4. **복제 함정 10건** — `slice15/closing.md` 의 복제 함정 목록 재확인 (아래 §1에 핵심 5건 발췌).
5. **E2 output 구조 확인** — E2는 E1과 달리 "종합 진단 = 요약 + 섹터 할당" 형태.
   `CommentaryCard`가 이 output을 수용 가능한지 사전 판단 → §3 참조.

---

## 1. 복제 함정 (E1 → E2 적용)

`slice15/closing.md` 정리분 중 E2에 그대로 적용되는 핵심:

- `fetched_at` 은 **제출 핸들러 내부에서만** 생성 (hydration 불일치 회피).
- `holdings` 의 `sector` / `asset_class` / `name` = `null` 자동 채움 (Pydantic nullable).
- `garp_metrics` 는 ticker별 nested dict `{TICKER: {metric: value}}` 구조.
- API path = `/coach/e2/` (axios baseURL에 `/api/v1` 포함 — path에 중복 금지).
- 응답은 **봉투** 형태 `{output, llm_metadata, gate_tier?, preset_id?, scores?}` —
  진단 본체는 `response.output`. (Slice 15 P1-0 봉투 누락 버그 재발 주의.)

---

## 2. P1-A — E2 데이터레이어

`frontend/.../lib/coach` 에 E2 추가 (E1 패턴 그대로):

- **타입** — codegen 산출 `CoachE2Request` / `CoachE2Response` 재사용 (수기 정의 금지).
- **api 함수** — `postE2Coach()` 등, `POST /coach/e2/` 호출. authAxios(JWT 자동 첨부) 사용.
- **훅** — `useE2Coach` (E1의 `useE1Coach` 패턴 — react-query mutation, 3-상태 노출).
- **MSW 핸들러** — `/coach/e2/` 모의 응답. 응답은 **봉투 형태**로 작성
  (`{output: {...}, llm_metadata: {...}}`) — inner 모델만 반환하지 말 것.

---

## 3. P1-B — E2 화면

`frontend/.../app/coach/e2/page.tsx` 신설 (E1의 `app/coach/e1/` 패턴):

- **폼** — `E2Request` 실측 필드 기반. 폼 검증 + a11y(`aria-busy`, `role=alert`) 포함
  (Slice 15 P3-A에서 E1에 적용한 것과 동등 수준).
- **3-상태** — 로딩 / 성공 / 에러 UI.
- **`CommentaryCard` 재사용** — E2 output(요약 + 섹터 할당)을 렌더.
  ⚠ **CommentaryCard가 E2 output을 수용 불가하면 HALT·보고할 것.**
  이 경우 "CommentaryCard 확장 vs E2 전용 카드" 결정이 필요하므로 임의 진행 금지.
- **AuthGuard** — E1과 동일 패턴 적용.

---

## 4. P1-C — P3-C(E2) 실 round-trip 1회

> #70 close 영향: 모든 coach view가 `IsAuthenticated` → 실 호출 시 **유효 JWT 필수**.
> (Slice 15 P3-C(E1)는 `AllowAny` 시절이라 토큰 없이 호출됐음 — 이제 안 됨.)

1. **dev JWT 토큰 확보** — dev 사용자 생성/조회 후 토큰 발급 (절차를 closing에 기록).
   토큰 미확보 시 P3-C 진입 금지.
2. **dev 백엔드 기동** → `POST /api/v1/coach/e2/` 실 호출 1회 (Authorization 헤더 첨부).
3. **봉투 정합 검증** — 실 응답이 codegen `CoachE2Response` 와 shape 완전 일치하는지 확인
   (봉투 / 필드 / 타입 / optional). → 일치 시 **#72 의 E2분 충족**.
4. **cost_ledger 자동 기록 확인** — 행에 `entry_point="e2"`, `slice="runtime"`(또는 env값)
   으로 정상 기록되는지 확인. → Step 0 #68 close의 **첫 운영 view 실증**.
   (기존 `default`/`null` 부정합이 차단됐는지가 핵심.)
5. 비용 ~$0.005–0.02, 슬라이스 cap $1.00 내. 누적 비용 갱신.

### HALT 조건 (P1-C)

- 실 호출 401 → JWT 절차 문제. 보고.
- 실 응답 shape ≠ codegen 타입 → P1-0류 봉투/bridge 결함. 보고 (임의 우회 금지).

---

## 5. 검증 (Part 1 종결 게이트)

- **vitest** — E2 신규 테스트 (빈/happy/error 3 + a11y/form 4 ≈ 7건). 기존 74건 무손실.
- **pytest** — `IDENTICAL 31/31` 유지.
- **tsc** — exit 0.
- **비용** — P3-C 행이 ledger에 정상 기록 (entry_point/slice 정합).
- **#72** — E2 실 응답 shape 일치 확인 (E2분 충족, close는 슬라이스 closing에서 일괄).

---

## 6. 커밋 (의미 단위 분리 — Stock-Vis 패턴)

한 Part = 여러 커밋. 최소 2~3 커밋으로 분리:

- P1-A (데이터레이어) / P1-B (화면) / P1-C (P3-C 실 검증 + 비용 기록).
- P3-C는 외부 commit 아님 — 결과를 closing 메모에 기록 (Slice 15 P3-C 방식과 동일).

---

## 7. 진행 보고 형식 (종결 시)

- 각 커밋 hash + 단계 + 결과 요약.
- 회귀 수치 (vitest / pytest / IDENTICAL / tsc).
- P3-C 결과 — HTTP 상태, latency, cost, 봉투 정합 여부, ledger 행 내용.
- 부채 변동 (신규/close).
- HALT 이력.
- Part 2 진입 메모 — 다음 진입점은 **E6** (순서: E2→E6→E3→E5→E4).

---

## 부록 — Slice 16 진입 순서 (확정)

E2 → E6 → E3 → E5 → E4 (단순→복잡순. E4는 대화형 폼이라 마지막).
각 Part는 본 지시서와 동일 구조로 복제.
