# Slice 16 Part 2 — E6 코치 화면 (비교 분석)

> 목표: Part 1에서 검증된 E2 화면 패턴을 E6(비교 분석) 화면으로 복제.
> 패턴이 E1·E2로 두 번 검증됨 — 진입점만 치환하는 기계적 복제. 신규 결정 없음.
> 분기 기준: `slice16` 브랜치, HEAD `8e6f596` (Part 1 종결).
> 진입 순서(§부록): E2 ✅ → **E6 (본 Part)** → E3 → E5 → E4.

---

## 0. Pre-flight (코드 작성 전 필수)

### 0-1. 환경 안전장치 (#71 대응)

- `git branch --show-current` → `slice16` 확인.
- `git rev-parse HEAD` → `8e6f596` 확인 (Part 1 종결 커밋).
- 안전 태그 생성: `git tag slice16-part1-done 8e6f596`
- 작업 중 working tree가 `iron-trading-api`로 전환되면 **즉시 HALT·보고**.
  → 복구: `git checkout slice16` (신규 파일은 untracked로 보존).
- 참고: Part 1은 HALT 0회. iron-trading 폴더 분리가 유효했던 것으로 보이나, 안전장치는 유지.

### 0-2. 사실관계 점검 (메모리 추정 금지)

지시서의 필드명·구조는 추정이다. **코드 작성 전 실제 소스를 확인**하고 불일치 시 HALT·보고.

1. **E6 codegen 타입 존재 확인** — `CoachE6RequestRequest` / `CoachE6Response`(봉투 포함)가
   생성 타입 파일에 있는지. 없으면 codegen 재실행.
2. **E6 Pydantic schema 실제 필드 확인** — `portfolio/schemas/` 의 E6 Request/Response 정의를
   직접 열어 실측 shape 확보. 폼·타입은 이 실측값 기준.
3. **E6 service 확인** — `portfolio/services/coach/e6_service.py` 에 Step 0에서 추가된
   `entry_point="e6"` 가 이미 반영돼 있음. 변경 불필요, 확인만.
4. **복제 함정 5건** — §1 참조.
5. **★ E6 output ↔ CommentaryCardData 호환성 점검 (§3 게이트)** — §3 참조. 이 점검 결과로
   §3 커밋 필요 여부가 갈린다.

---

## 1. 복제 함정 (E2 → E6 동일 적용)

- `fetched_at` 은 **제출 핸들러 내부에서만** 생성 (hydration 불일치 회피).
- `holdings` 의 `sector` / `asset_class` / `name` = `null` 자동 채움 (Pydantic nullable).
- `garp_metrics` 는 ticker별 nested dict `{TICKER: {metric: value}}` 구조.
- API path = `/coach/e6/` (axios baseURL에 `/api/v1` 포함 — path 중복 금지).
- 응답은 **봉투** 형태 `{output, llm_metadata, gate_tier?, preset_id?, scores?}` —
  진단 본체는 `response.output`.

---

## 2. P2-A — E6 데이터레이어

`frontend/.../lib/coach` 에 E6 추가 (E2 패턴 그대로):

- **타입** — codegen 산출 `CoachE6RequestRequest` / `CoachE6Response` 재사용 (수기 정의 금지).
- **api 함수** — `postE6Coach()`, `POST /coach/e6/`. authAxios(JWT 자동 첨부) 사용.
- **훅** — `useE6Coach` (`useE2Coach` 패턴 — react-query mutation, 3-상태 노출).
- **MSW 핸들러** — `/coach/e6/` 모의 응답. 응답은 **봉투 형태**로 작성
  (`{output: {...}, llm_metadata: {...}}`) — inner 모델만 반환 금지.

---

## 3. §3 게이트 — CommentaryCard 호환성 (이번엔 조건부)

Part 1에서 `CommentaryCardData` 공통 base(E1·E2 output 합집합)를 신설했다.
E6는 그 base를 **재사용**하되, 0-2 점검에서 아래를 판정한다:

- **E6 output 필드가 모두 `CommentaryCardData`에 이미 있으면** → §3 작업 없음. 카드 그대로 재사용.
- **E6 output에 base에 없는 신규 필드가 있으면** → A안 설계대로 처리:
  `CommentaryCardData`에 해당 필드(optional) + 렌더 섹션 1개 추가. graceful 미렌더 유지
  (빈 값·undefined면 섹션 미렌더). → 이 변경은 **별도 커밋**(`refactor: CommentaryCardData E6 필드 확장`)
  으로 분리.
- **E6 output이 구조적으로 크게 다르면**(예: 비교 대상 N개의 배열 구조 등 단순 합집합으로 흡수 불가)
  → **HALT·보고.** 임의 진행 금지. (E6는 "비교 분석·단순"으로 분류돼 있어 가능성은 낮으나 확인.)

> 참고: "Part 5 후 C 리팩터링(BaseCard split + EP별 Section) 재검토"는 Slice 16 closing 후속 후보로
> 이미 등록됨. Part 2~5는 A안 base 확장으로 계속 진행.

---

## 4. P2-B — E6 화면

`frontend/.../app/coach/e6/page.tsx` 신설 (E2의 `app/coach/e2/` 패턴):

- **폼** — `E6Request` 실측 필드 기반. 폼 검증 + a11y(`aria-busy`, `role=alert`) 포함
  (Part 1 E2 화면과 동등 수준).
- **3-상태** — 로딩 / 성공 / 에러 UI.
- **`CommentaryCard` 재사용** — §3 판정 결과 반영(재사용 또는 확장된 base).
- **AuthGuard** — E1·E2와 동일 패턴.
- E6 고유 입력 로직(비교 대상 구성 등)이 있으면 실측 schema 기반으로 반영.

---

## 5. P2-C — 실 round-trip 1회 (E6)

> 외부 commit 아님 — 결과를 P2-D closing 문서에 기록 (Part 1 P1-C 방식과 동일).

**JWT 절차 — Part 1에서 정착, 그대로 재사용:**
`admin / stock_vis123` → `POST /api/v1/users/jwt/login/` → 받은 토큰을 `Bearer` 헤더로 첨부.

1. dev 백엔드 기동 → `POST /api/v1/coach/e6/` 실 호출 1회 (Authorization 헤더 첨부).
2. **봉투 정합 검증** — 실 응답이 codegen `CoachE6Response`와 shape 완전 일치(봉투/필드/타입/optional).
   → 일치 시 **#72 의 E6분 충족**.
3. **cost_ledger 자동 기록 확인** — 행에 `entry_point="e6"`, `slice="runtime"`으로 기록되는지.
   (Part 1에서 #68/#70 운영 실증 완료 — E6도 동일하게 정합되는지 확인.)
4. 비용 ~$0.005–0.02, 슬라이스 cap $1.00 내. 누적 비용 갱신.

### HALT 조건 (P2-C)

- 실 호출 401 → JWT 절차 문제. 보고.
- 실 응답 shape ≠ codegen 타입 → 봉투/bridge 결함. 보고 (임의 우회 금지).

---

## 6. 검증 (Part 2 종결 게이트)

- **vitest** — E6 신규 테스트 (빈/happy/error 3 + a11y/form 4 ≈ 7건). 기존 81건 무손실.
- **pytest** — `IDENTICAL 31/31` 유지.
- **tsc** — exit 0.
- **비용** — P2-C 행이 ledger에 정상 기록 (entry_point="e6" / slice 정합).
- **#72** — E6 실 응답 shape 일치 확인 (E6분 충족, close는 슬라이스 closing에서 일괄).

---

## 7. 커밋 (의미 단위 분리 — Stock-Vis 패턴)

최소 2~3 커밋 (§3 확장이 필요하면 +1):

- (조건부) §3 — `refactor: CommentaryCardData E6 필드 확장`
- P2-A — `feat: E6 데이터레이어`
- P2-B — `feat: E6 화면 + 테스트`
- P2-D — `docs: Part 2 closing` (P2-C 실 round-trip 결과 + ledger 보존 기록 포함)

---

## 8. 진행 보고 형식 (종결 시)

- 각 커밋 hash + 단계 + 의미 요약.
- §3 게이트 판정 결과 (재사용 / base 확장 / HALT).
- 회귀 수치 (vitest / pytest / IDENTICAL / tsc).
- P2-C 결과 — HTTP 상태, latency, cost, 봉투 정합, ledger 행 내용(entry_point="e6").
- #72 진행 (E1·E2·E6 ✅, E3·E5·E4 잔여).
- 부채 변동 / HALT 이력.
- 누적 비용 (Slice 16).
- Part 3 진입 메모 — 다음 진입점은 **E3** (순서: E2→E6→E3→E5→E4).

---

## 부록 — Slice 16 진입 순서 (확정)

E2 ✅ → E6 (본 Part) → E3 → E5 → E4 (단순→복잡순. E4는 대화형 폼이라 마지막).
각 Part는 본 지시서와 동일 구조로 복제.
