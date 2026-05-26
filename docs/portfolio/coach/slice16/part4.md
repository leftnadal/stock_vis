# Slice 16 Part 4 — E5 코치 화면 (추출 + 시계열 컨텍스트) ⚠ 특수 케이스

> 목표: E5(추출 진입점) 화면 구현. E1~E3·E6과 달리 `TimeSeriesContext` 입력을 받는 유일한 진입점.
> 화면 골격은 기존 패턴 복제, 단 `time_series_context` 폼 UI는 사전 결정(안 C)을 따른다.
> 분기 기준: `slice16` 브랜치, HEAD `98d4e89` (Part 3 종결).
> 진입 순서(§부록): E2 ✅ → E6 ✅ → E3 ✅ → **E5 (본 Part)** → E4.

---

## 0. Pre-flight (코드 작성 전 필수)

### 0-1. 환경 안전장치 (#71 대응)

- `git branch --show-current` → `slice16` 확인.
- `git rev-parse HEAD` → `98d4e89` 확인 (Part 3 종결 커밋).
- 안전 태그 생성: `git tag slice16-part3-done 98d4e89`
- 작업 중 working tree가 `iron-trading-api`로 전환되면 **즉시 HALT·보고**.
  → 복구: `git checkout slice16` (신규 파일은 untracked로 보존).
- 참고: Part 1·2·3 연속 HALT 0회.

### 0-2. 사실관계 점검 (사전 실측 완료분 — 재확인만)

Part 4 사전 실측에서 아래가 확인됨. 코드와 어긋나면 HALT·보고.

- `TimeSeriesContext` (`portfolio/schemas/commentary_input.py:25~64`) — 평탄 BaseModel,
  `extra="forbid"`. 필드 4개: `current: Decimal`(필수) / `window_1q·4q·12q: Optional[Decimal]`(None 가능).
  `delta_4q_pct`는 property(서버 계산) — JSON 직렬화 미포함, **UI 입력 필드 아님**.
- `CommentaryInputE5` (`commentary_input.py:158~168`) — E5 고유 필드 정확히 2개:
  `extraction_targets: list[str]` (`min_length=1`) + `time_series_context: Optional[TimeSeriesContext]`
  (default None). 나머지는 `CommentaryInputBase` 상속.
- `E5Output` (`commentary_output.py:118~122`) — 고유 필드 `action_items` + `quoted_metrics`,
  둘 다 `CommentaryCardData` base에 이미 존재. `risk_flags` 없음(optional → graceful 미렌더).
- codegen 타입 — `CoachE5RequestRequest` / `CoachE5Response` 봉투 모두 존재
  (`frontend/lib/coach/api-types.ts:6470~6628`). `time_series_context`는 **별도 component 아닌 inline**.
- `e5_service.py` — `entry_point="e5"` 적용 확인(:59~65). 컨텍스트는 service가 아닌
  `E5PromptBuilder`가 소비(:285~325), None일 때 "(없음)" 분기.
- fixture — `portfolio/tests/fixtures/coach/portfolio_a2.json:93~101` E5 샘플 존재.

### 0-3. §3 게이트 — 작업 없음 (확정)

E5Output 필드 전부 `CommentaryCardData` base에 존재(실측 확인). 신규 필드 0건 → §3 커밋 없음.
`CommentaryCard` 그대로 재사용. (Part 2 base 완화 효과 — E3에 이어 두 번째 자동 호환.)

---

## 1. 복제 함정 (E2/E3/E6 → E5 동일 적용)

- `fetched_at` 은 **제출 핸들러 내부에서만** 생성 (hydration 불일치 회피).
- `holdings` 의 `sector` / `asset_class` / `name` = `null` 자동 채움 (Pydantic nullable).
- `garp_metrics` 는 ticker별 nested dict `{TICKER: {metric: value}}` 구조.
- API path = `/coach/e5/` (axios baseURL에 `/api/v1` 포함 — path 중복 금지).
- 응답은 **봉투** 형태 `{output, llm_metadata, gate_tier?, preset_id?, scores?}` —
  진단 본체는 `response.output`.
- **★ E5 신규 함정 — Decimal 직렬화:** `current`/`window_*` 값은 **string으로 전달**
  (`"3.45"`). codegen 타입은 `number | string` union이고 fixture도 string. 큰 값 정밀도 안전을 위해
  UI는 string으로 통일. number 입력을 받더라도 제출 시 string으로 변환.

---

## 2. P4-A — E5 데이터레이어

`frontend/.../lib/coach` 에 E5 추가 (E3 패턴 그대로):

- **타입** — codegen 산출 `CoachE5RequestRequest` / `CoachE5Response` 재사용 (수기 정의 금지).
- **★ TS helper 정의** — `TimeSeriesContext`가 별도 component로 codegen되지 않아 inline 구조.
  참조 편의를 위해 helper alias 1개 정의:
  `type E5TimeSeriesContext = NonNullable<CoachE5RequestRequest['time_series_context']>`
  (정확한 키 경로는 codegen 타입 실측 기준으로 맞출 것).
- **api 함수** — `postE5Coach()`, `POST /coach/e5/`. authAxios(JWT 자동 첨부) 사용.
- **훅** — `useE5Coach` (`useE3Coach` 패턴 — react-query mutation, 3-상태 노출).
- **MSW 핸들러** — `/coach/e5/` 모의 응답. 응답은 **봉투 형태**로 작성.

---

## 3. P4-B — E5 화면 (폼 설계 = 사전 결정 안 C)

`frontend/.../app/coach/e5/page.tsx` 신설. 3-상태·AuthGuard·a11y는 E3와 동일 패턴.
E5 폼은 아래 두 입력 블록을 가진다.

### 3-1. `extraction_targets` 입력

- 콤마 또는 태그 형태의 다중 문자열 입력 (키 list).
- **폼 검증** — `min_length=1` 강제: 빈 list면 제출 차단 + `role=alert` 에러 메시지.
- fixture 참고 키 예시: `dividend_yield` / `sector_diversification` / `beta` / `expense_ratio`.

### 3-2. `time_series_context` 입력 — 안 C (토글 + 4칸 + 예시 채우기)

**확정 설계 — 사전 결정 안 C. 임의 변경 금지.**

- **토글** — "시계열 컨텍스트 포함" on/off. **default = off.**
  - off → 제출 payload의 `time_series_context = null` (service의 "(없음)" 분기 — 정상 경로).
  - on → 아래 4칸 입력 영역 노출.
- **입력 4칸** (on일 때):
  - `current` — **필수.** 비어 있으면 제출 차단 + `role=alert` 에러.
  - `window_1q` / `window_4q` / `window_12q` — optional. 비우면 payload에서 해당 키 `null` 또는 생략.
  - 모든 값 **string으로 전달** (§1 Decimal 함정).
- **`delta_4q_pct` 입력칸 없음** — 서버 자동 계산. UI에 노출하지 않음.
- **★ "예시 값 채우기" 버튼:**
  - 클릭 시 4칸을 검증된 fixture 값으로 채움 — 프론트엔드 **상수**로 박아둘 것
    (`portfolio_a2.json`을 런타임에 읽지 말 것 — 백엔드 테스트 자산임).
    상수 값: `current:"3.45"`, `window_1q:"3.40"`, `window_4q:"3.30"`, `window_12q:"3.15"`.
  - **오인 방지** (안 C 단점 보완 — 필수):
    - 버튼 라벨에 "예시"를 명시 (예: "예시 값 채우기").
    - 예시로 채운 상태임을 알리는 옅은 안내 텍스트 노출
      (예: "예시 데이터입니다 — 실제 값으로 교체하세요").
    - 토글 default는 off 유지 — 사용자가 명시적으로 토글 on + 버튼 클릭을 해야만 예시가 들어옴.

### 3-3. `CommentaryCard` 재사용

§3 작업 없음 — E5Output(`summary`/`key_observations`/`confidence`/`action_items`/`quoted_metrics`)을
`CommentaryCard`에 직접 prop 전달. `risk_flags`·`metrics_table` 없음 → graceful 미렌더.

---

## 4. P4-C — 실 round-trip 1회 (E5)

> 외부 commit 아님 — 결과를 P4-D closing 문서에 기록.

**JWT 절차 — Part 1 정착분 재사용:**
`admin / stock_vis123` → `POST /api/v1/users/jwt/login/` → 토큰을 `Bearer` 헤더로 첨부.

1. dev 백엔드 기동 → `POST /api/v1/coach/e5/` 실 호출 1회.
   - payload baseline — `portfolio_a2.json` E5 패턴:
     `extraction_targets: ["dividend_yield","sector_diversification","beta","expense_ratio"]`
     - `time_series_context` = fixture 값(string). **즉 토글 on 경로를 실 검증.**
2. **봉투 정합 검증** — 실 응답이 codegen `CoachE5Response`와 shape 완전 일치
   (봉투/필드/타입/optional). → 일치 시 **#72 의 E5분 충족**.
3. **cost_ledger 자동 기록 확인** — 행에 `entry_point="e5"`, `slice="runtime"`.
4. 비용 ~$0.005–0.02 (E3가 $0.0095로 가장 컸음 — E5도 시계열 블록 포함이라 다소 클 수 있음).
   슬라이스 cap $1.00 내. 누적 비용 갱신.

### HALT 조건 (P4-C)

- 실 호출 401 → JWT 절차 문제. 보고.
- 실 응답 shape ≠ codegen 타입 → 봉투/bridge 결함. 보고 (임의 우회 금지).
- `time_series_context` string 값이 백엔드 Decimal 변환에서 거부 → 직렬화 형식 재점검. 보고.

---

## 5. 검증 (Part 4 종결 게이트)

- **vitest** — E5 신규 테스트 (기존 95건 무손실). 아래를 반드시 포함:
  - 빈/happy/error 3 + a11y/form (≈7건 기준).
  - `extraction_targets` 빈 list 제출 차단 검증.
  - `time_series_context` 토글 off → payload `null` 검증.
  - 토글 on + `current` 미입력 → 제출 차단 검증.
  - "예시 값 채우기" 버튼 → 4칸이 fixture 상수로 채워짐 검증.
- **pytest** — `IDENTICAL 31/31` 유지 (`test_input_v2_smoke.py` 등 Slice 8 시계열 가드 포함).
- **tsc** — exit 0.
- **비용** — P4-C 행 ledger 정상 기록 (`entry_point="e5"`).
- **#72** — E5 실 응답 shape 일치 확인 (E5분 충족).

---

## 6. 커밋 (의미 단위 분리 — Stock-Vis 패턴)

§3 작업 없음 → 3 커밋 (Part 3과 동일 형태):

- P4-A — `feat: E5 데이터레이어 (postE5Coach + useE5Coach + MSW + E5TimeSeriesContext helper)`
- P4-B — `feat: E5 화면 + 테스트 (extraction_targets + time_series_context 토글 폼)`
- P4-D — `docs: Part 4 closing + ledger 자동 append`

---

## 7. 진행 보고 형식 (종결 시)

- 각 커밋 hash + 단계 + 의미 요약.
- §3 게이트 결과 (작업 없음 — base 호환).
- 폼 — `time_series_context` 안 C 구현 결과 (토글/4칸/예시 버튼/오인 방지 처리).
- 회귀 수치 (vitest / pytest / IDENTICAL / tsc).
- P4-C 결과 — HTTP 상태, latency, cost, 봉투 정합, ledger 행(`entry_point="e5"`).
- #72 진행 (E1·E2·E6·E3·E5 ✅, **E4만 잔여 — 5/6**).
- 부채 변동 / HALT 이력.
- 누적 비용 (Slice 16).
- Part 5 진입 메모 — 마지막 진입점 **E4** (대화 Q&A).
  ⚠ E4는 대화형 — 폼 UX가 근본적으로 다름(질문 입력 + history 표시). `CommentaryCard` 적용 방식
  재점검 필요. Part 5 지시서는 E4 고유 패턴을 반영해 별도 작성 예정.

---

## 부록 — Slice 16 진입 순서 (확정)

E2 ✅ → E6 ✅ → E3 ✅ → E5 (본 Part) → E4 (대화형이라 마지막).
Part 5(E4) 종결 후 → Slice 16 closing(#72 일괄 close, "Part 5 후 C 리팩터링 재검토" 후속 후보 정리).
