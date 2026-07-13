# SLICE 18 지시서 — Portfolio Coach: 사용자 상태 그릇 (Container Persistence Layer)

> **배치 경로(강제):** 이 파일을 repo의 `docs/portfolio/coach/slice18/SLICE18_INSTRUCTION.md`에 두고, 새 Claude Code 세션 첫 메시지로 이 경로를 전달한다. (이번 트랙에서 확인된 "지시서-파일-부재 구멍" 재발 방지 — 지시서는 repo 안에 있어야 미래 세션이 찾는다.)
>
> **세션 종류:** 실행(execution) 세션. 설계 결정 3건(D1~D3)은 §4에서 **이미 닫혀 있다** — 이 세션은 결정을 다시 열지 않고 기록·구현만 한다. 단 STEP 0 실측이 D1의 전제를 깨면 HALT(§2, §7).
>
> **이 슬라이스가 본편에서 차지하는 자리:** 서비스 플로우 `Dashboard → Chain Sight → Node Monitoring → 1차 검증 → 포트폴리오 변화`의 **맨 끝 "그릇"**. 사용자의 *투자 목표·관심 종목·실보유·현금*을 담는 4개 영속 테이블을 만든다. 이 위에 "무엇을 사고 무엇을 지킬지"를 목표 대비로 권유하는 엔진(Slice 19a/19b)과 화면(Slice 20)이 올라간다. 즉 **19·20의 데이터 토대**다.

---

## 0. 산출물 정의 (Definition of Done)

이 슬라이스가 끝났다고 말하려면 아래가 전부 참이어야 한다.

1. 신규 모델 4종이 `apps/portfolio`에 존재: **UserGoal · WatchlistItem · WalletHolding · CashBalance**.
2. 4종 전부 **user 스코프 이음새**를 통해 사용자에 귀속된다(§4 D2 = `UserScopedModel` 추상 베이스 + 스코핑 매니저).
3. 각 모델에 대한 최소 CRUD 경로(생성·조회·수정·삭제)가 user 스코프 안에서 동작한다.
4. **교차 사용자 격리 테스트**가 존재하고 통과한다(§4 D3 = 스코프 모델 전체를 커버하는 파라미터라이즈드 누수-0 테스트 + 신규 스코프 모델 등록 가드).
5. DECISIONS.md에 **D1·D2·D3 3건이 "왜"와 함께 선행 기록**되어 있고, 그 커밋이 모델 커밋보다 앞선다.
6. codegen(마이그레이션·타입/스텁 등 repo가 요구하는 생성물)이 최신화되어 있고, `makemigrations --check`가 깨끗하다.
7. **직전 세션 baseline 회귀가 보존**된다: STEP 0에서 측정한 pytest green 수를 종료 시 재측정해 동일 이상(신규 테스트만큼 증가) — 기존 테스트 **깨짐 0**.
8. `scripts/health_check.py` 통과, 경계 아키텍처 테스트(`shared→apps` 위반) 통과(동결 목록 증가 0).

---

## 1. 절대 규칙 (넘으면 즉시 HALT — §7)

- **메모리·이 문서에 적힌 수치를 신뢰하지 않는다.** 브랜치·HEAD·테스트 수·기존 모델 목록은 전부 STEP 0에서 *명령으로* 측정한다. (직전 기록: `origin/main = 2d0c605`, pytest `567/0 green` — **이 값은 재측정 대상이지 전제가 아니다.**)
- **한 방향 규칙:** `apps → shared`만. 신규 4모델은 `apps/portfolio` 소속이므로 shared import는 합법. **shared가 이 모델들을 거꾸로 import하게 만들지 않는다**(shared→apps 위반 = 아키텍처 테스트가 잡음).
- **행위보존 최우선:** 이 슬라이스는 *가산(additive)* 이다 — 기존 테이블·행위를 건드리지 않는다. 기존 pytest가 하나라도 깨지면 그건 회귀이고 HALT.
- **파괴적 작업 유보:** prod DB 반영·강제 삭제·원격 브랜치 삭제 등은 이 세션에서 하지 않는다. 마이그레이션은 *생성·로컬 적용*까지만. prod 적용은 후보로만 보고한다.
- **결정 재오픈 금지:** D1~D3는 닫혀 있다. 구현 중 더 나은 안이 보이면 **바꾸지 말고** 닫기 보고에 "재검토 후보"로 남긴다(단 STEP 0가 D1 전제를 깨는 경우는 예외 = HALT 후 사용자 판단).

---

## 2. STEP 0 — ground truth 측정 (코드 한 줄 쓰기 전)

STARTUP_CHECKLIST Step 0(계약 헤더: 세션 종류·범위·baseline)을 채운 뒤, 아래를 **명령으로 측정**하고 결과를 세션 로그에 남긴다. 하나라도 예상과 어긋나면 해당 항목의 HALT 조건을 본다.

**(a) git·worktree 좌표**
- `git worktree list` — 어느 worktree에서 작업 중인지, 동기 상태.
- `git rev-parse HEAD` / `git log --oneline -5` — 현재 base가 직전 기록(`2d0c605`)과 일치하는지. **다르면** 왜 다른지 확인(main이 더 전진했으면 그 위에서 분기).
- 작업 브랜치는 **`monorepo/sess-<식별자>`** 로 새로 판다(commit hook 화이트리스트 `monorepo/*` 재사용 — `sess/*`는 거부됨). 새 worktree에서 시작.

**(b) baseline 테스트 상태 (회귀 기준선)**
- `pytest`(portfolio 관련 스코프 + 아키텍처 테스트 포함) 전체를 돌려 **green 수/실패 수를 기록**한다. 이 수가 종료 시 회귀 판정의 기준선이다.
- 직전 기록 `567/0`과 다르면 그 차이를 먼저 설명(신규 테스트 유입/환경 차이). **red가 1개라도 있으면** 신규 작업 전 HALT — 깨끗한 출발선 위에서만 슬라이스를 얹는다(이번 트랙이 만든 게이트).

**(c) ⚠️ 가장 중요 — 기존 영속 모델 의미 중복 대조 (HALT 후보 1순위)**
- portfolio(및 shared)에서 **현재 존재하는 영속 모델 전수**를 뽑는다(예: `grep -rn "models.Model" apps/portfolio packages/shared` + Django `showmigrations`/`inspectdb` 교차확인 — 정확한 방법은 repo 구조에 맞춰 측정).
- 직전 기록상 **기존 13개 영속 모델**이 있다고 본다 — 이 수와 목록을 실측으로 확정한다.
- 신규 4종(UserGoal·WatchlistItem·WalletHolding·CashBalance) 각각에 대해 **의미가 겹치는 기존 모델이 있는지** 대조한다:
  - 이미 "watchlist/관심목록", "holding/보유/포지션", "goal/목표", "cash/현금/잔고" 성격의 테이블이 있는가?
  - 있으면 → **신규 생성 대신 재사용/확장**이 맞을 수 있다. **의미 중복이 하나라도 확인되면 즉시 HALT**하고, "재사용 vs 신규" 판단 근거를 표로 사용자에게 보고한다. (중복 테이블을 만들면 진실의 소스가 둘로 갈라진다 = moat인 시계열 궤적이 쪼개짐.)
- **교차앱 소비자 점검(D1 전제 검증):** 기존 코드/TASKQUEUE/방향 문서에서 watchlist·holding·goal·cash 데이터를 **portfolio 외의 앱(dashboard·chain_sight·market_pulse·미래 Node Monitoring)이 이미/곧 소비**하도록 요구하는 흔적이 있는가?
  - 있으면 → **D1의 전제("지금은 portfolio만 소비")가 깨진다** → HALT, D1 재결정(해당 모델의 shared 승격 여부). §4 D1 참조.

**(d) shared 자산 실측 (박힌 경로 신뢰 금지)**
- portfolio가 실제로 import하는 shared 모듈 전수(User/auth 소스, 지표/시장 데이터 모델, LLM/FMP 래퍼 위치). 특히 **`AUTH_USER_MODEL`의 실제 위치·형태**를 확인한다(D2의 FK 대상).

**(e) 하네스 상태**
- TASKQUEUE에서 portfolio/Slice 18 관련 미해결 항목, DECISIONS.md 최신 엔트리, common-bugs.md의 관련 함정, 비용 원장 상태를 훑어 이 슬라이스와 충돌하는 게 없는지 본다.

> STEP 0 산출 = "계약 헤더 + baseline 테스트 수 + 기존 모델 전수표 + 4종 각각의 재사용/신규 판정 + 교차앱 소비자 유무 + AUTH_USER_MODEL 실위치". 이 표는 닫기 보고에 그대로 들어간다(§6 검증축 3).

---

## 3. worktree · 브랜치 · 커밋 규약

- **새 worktree**에서 시작(세션·프로젝트 간 git 충돌 방지). `git worktree list`로 위치 확인 후 진입.
- 브랜치: `monorepo/sess-slice18-<날짜/짧은식별자>`.
- 커밋은 **의미 단위 분리**(3계층 Slice/Part/Step). 한 슬라이스 = 여러 커밋. Part 경계에서 커밋한다(§5).
- 커밋 메시지에 Part/Step을 명시한다(예: `slice18(Part A): record D1-D3 in DECISIONS`).
- 이 슬라이스는 가산이라 IDENTICAL hash 대상 변경은 없다 — **행위보존 증거는 "기존 pytest green 유지"** 로 대신한다(Part 종료마다 회귀 확인).

---

## 4. 선행 결정 3건 (Part A에서 DECISIONS.md에 "왜"와 함께 기록·커밋 — 모델보다 먼저)

> 아래는 **닫힌 결정**이다. 근거·가중합은 디렉터 세션에서 확정됨. 이 세션은 각 항목을 DECISIONS.md에 기록(요지 + 근거 + STEP 0 의존 조건)하고 그대로 구현한다.

### D1 — 신규 4모델의 소속: **전부 `apps/portfolio`** (STEP 0 교차앱 점검 통과 조건부)
- **무슨 결정인가:** 4개 테이블을 앱에 둘지(portfolio) 토대로 올릴지(shared)의 문제. 판정 기준 = "어느 앱을 몰라도 되는 범용 재료인가". 지금 이 데이터를 소비하는 건 portfolio(진단·코멘트·목표 대비 권유)뿐이므로 **portfolio 소속**이 맞다("재료는 자기가 어느 요리에 들어갈지 몰라야 한다" — 아직 다른 요리가 없다).
- **왜 shared가 아닌가:** 지금 shared로 올리면 shared가 "사용자-포트폴리오 전용 데이터"를 알게 되어 범용성이 깨진다(YAGNI 위반). 신규 테이블이라 나중에 승격해도 *테이블 이동 없는* 케이스가 되기 쉬워, 미리 올릴 이득이 적다.
- **전제(STEP 0가 검증):** "지금은 portfolio만 소비." STEP 0 (c)의 교차앱 소비자 점검에서 watchlist 등이 이미 다른 앱에서 필요하다고 드러나면 **이 전제가 깨지고 → HALT → D1 재결정**(그 모델만 shared 승격 후보, `makemigrations --dry-run`으로 이동 성격 검증).
- **미래 승격 경로(닫기만 해둠):** 2번째 앱이 watchlist를 필요로 하면 그때 방향C(토대 승격)로 shared로 올린다. 지금은 apps→apps 결합을 만들지 않는 게 핵심.

### D2 — user 스코프 이음새 메커니즘: **`UserScopedModel` 추상 베이스 (FK + 스코핑 매니저)**
- **무슨 결정인가:** 행(row)을 사용자에 귀속시키는 방식. 방향 B("검증된 코어를 나중에 서비스로 포장 — 다중 사용자 이음새 보존")를 만족하되 지금 멀티테넌트 하드닝은 하지 않는다.
- **채택:** 4모델이 공통 상속하는 추상 베이스 `UserScopedModel`을 둔다. 구성 = `user = ForeignKey(AUTH_USER_MODEL, on_delete=CASCADE, ...)` + **기본 스코핑 매니저**(`for_user(user)` 류 헬퍼로 사용자 필터를 쿼리 계층 기본값으로). 이렇게 하면 "사용자 격리"가 4모델 각각에 흩어진 규칙이 아니라 **한 곳의 이음새**가 된다.
- **왜 이 방식인가(vs 순수 FK / vs 정수 user_id):** 순수 FK는 반복되고 격리를 강제하지 못한다. 정수 필드는 참조 무결성·cascade가 없다. 추상 베이스는 (1) 이음새를 한 곳에 모아 서비스 포장 시 확장점이 1개, (2) 교차 사용자 누수 방지를 **쿼리 계층 기본값**으로 만들어 D3(격리 테스트)와 맞물린다, (3) 4모델 반복 제거(DRY).
- **구조:**
```
        apps/portfolio/models/
          _base.py    UserScopedModel(abstract)   ── user FK(AUTH_USER_MODEL) + ScopedManager.for_user()
                         ▲        ▲        ▲        ▲
        UserGoal ────────┘        │        │        └──────── CashBalance
                     WatchlistItem┘        └WalletHolding
        (신규 스코프 모델은 전부 이 베이스를 상속 → 격리 이음새 자동 계승)
```

### D3 — 보안 트리거 재정의: **"user 차원 보유 테이블 = 격리 테스트 필수", 파라미터라이즈드 가드로 구현**
- **무슨 결정인가(재정의의 대상):** 방향 문서상 *서비스 외피(멀티테넌트 하드닝)*는 "동결"이다. 그런데 Slice 18은 진짜 user 컬럼을 가진 테이블을 처음으로 들인다. 그래서 "보안을 언제 강제하나"의 트리거를 **재정의**한다:
  - (구) "멀티테넌트 하드닝은 동결" → (신) **"멀티테넌트 하드닝(온보딩/권한/테넌시 격벽)은 여전히 동결. 단 *user 차원을 가진 테이블이 새로 생기면* 그 테이블은 교차 사용자 누수-0 격리 테스트를 반드시 동반한다."**
  - 즉 "이음새 보존(방향 B)"과 "외피 동결"의 경계를 명확히 그어, 데이터 계층 격리는 지금부터 강제하고 UI/과금/온보딩은 계속 얼려 둔다.
- **구현:** 모델별 4벌 테스트가 아니라, **`UserScopedModel` 하위 전체를 자동 순회하는 파라미터라이즈드 격리 테스트** 하나 + **"새 스코프 모델이 등록되면 이 테스트에 자동 포함"되게 하는 등록 가드**. (사용자 A의 데이터가 사용자 B의 `for_user` 조회에 새지 않음을 각 모델에 대해 assert.)
- **왜:** 신규 스코프 모델(19·20에서 늘어난다)이 테스트에서 누락되는 사고를 구조적으로 막는다 — 아키텍처 경계 가드가 "우회 0"을 지키는 것과 같은 철학.

> **가중합 요지(기록용):** D2 = 추상베이스 4.50 vs FK 3.25 → 마진 1.25(자동확정). D3 = 파라미터라이즈드 4.70 vs 모델별 3.60 → 마진 1.10(자동확정). D1 = portfolio 4.25 vs watchlist-shared 3.25 → 마진 1.00(임계 경계) → **STEP 0 교차앱 소비자 부재 확인을 타이브레이커/확정 조건으로** 채택. 가중치·점수 상세는 DECISIONS.md 본문에 그대로 옮긴다.

---

## 5. 실행 계획 (Part / Step)

각 Part 끝에서 커밋하고, **Part B 이후 매 Part 종료 시 `pytest`로 회귀(기존 green 유지) 확인**.

**Part A — 결정 선행 기록**
- Step A1: DECISIONS.md에 D1·D2·D3를 각각 (요지 · 근거 · 가중합 점수 · STEP 0 의존 조건)으로 기록.
- Step A2: 커밋 `slice18(Part A): record D1-D3 (placement / user-scope base / security-trigger redef)`.
- **게이트:** 이 커밋이 아래 모든 모델 커밋보다 앞선다(미래 세션이 "왜 이렇게 만들었나"를 코드보다 먼저 읽게).

**Part B — 모델 + 이음새 베이스**
- Step B1: `UserScopedModel` 추상 베이스(+ 스코핑 매니저) 작성.
- Step B2: UserGoal · WatchlistItem · WalletHolding · CashBalance 정의. 필드는 **19a(목표 대비 권유 엔진)가 최소로 요구하는 것**만(과설계 금지 — YAGNI). 최소 권장:
  - `UserGoal`: 목표 유형/목표치·기준 통화·기간 등 "목표 대비" 계산에 필요한 최소.
  - `WatchlistItem`: 종목 식별자(shared 종목 모델 참조 방식은 STEP 0 실측에 맞춤) + 관찰 사유/추가시각.
  - `WalletHolding`: 종목 + 수량 + 평단(취득가) 등 실보유 스냅샷 최소.
  - `CashBalance`: 통화 + 금액 (+ 스냅샷 시각).
  - *정확한 필드는 STEP 0에서 본 기존 모델·shared 종목 식별 방식에 맞춰 확정하고, 확정 근거를 닫기 보고에 남긴다.*
- Step B3: `makemigrations` → 로컬 마이그레이션 생성(프로덕션 적용 아님). `makemigrations --check` 깨끗한지 확인.
- Step B4: 커밋 + 회귀 확인.

**Part C — user 스코프 CRUD**
- Step C1: 4모델 각각 user 스코프 내 생성·조회·수정·삭제 경로. 조회는 반드시 `for_user`(스코핑 매니저) 경유 — 전역 조회로 사용자 경계를 넘지 않는다.
- Step C2: 커밋 + 회귀 확인.

**Part D — 격리 테스트 (D3)**
- Step D1: `UserScopedModel` 하위 전체를 순회하는 **파라미터라이즈드 누수-0 격리 테스트**. 사용자 A/B 픽스처 → A의 데이터가 B의 `for_user` 결과에 없음을 4모델 각각 assert.
- Step D2: **등록 가드** — 스코프 모델 목록을 introspection으로 모아 테스트가 자동 커버하게 하고, 새 스코프 모델이 생겼는데 테스트에서 빠지면 실패하도록.
- Step D3: 커밋 + 전체 pytest(신규 테스트만큼 green 증가, 기존 깨짐 0).

**Part E — codegen 최신화**
- Step E1: repo가 요구하는 생성물(타입/스텁/OpenAPI 등 있으면) 재생성. `makemigrations --check`·codegen drift 0 확인.
- Step E2: 커밋.

**Part F — 닫기 보고**(§6 형식) + `scripts/health_check.py` 통과 + 아키텍처 테스트(동결 증가 0) 확인.

> **prod 마이그레이션:** 생성된 마이그레이션의 prod 적용은 **후보로만** 닫기 보고에 싣는다(파괴적/운영 반영은 사용자 수동). 로컬 sqlite/dev DB 적용까지만 이 세션에서 한다.

---

## 6. 닫기 보고 형식 (디렉터가 이 축으로 검증한다 — 반드시 채울 것)

1. **좌표:** 최종 브랜치·HEAD, base가 된 main HEAD, 생성 커밋 목록(Part별).
2. **회귀 증거:** STEP 0 baseline pytest 수 → 종료 pytest 수. 기존 깨짐 0임을 명시. 아키텍처 테스트(shared→apps) 통과·동결 증가 0.
3. **STEP 0 대조표(핵심):** 기존 영속 모델 전수 목록 + 신규 4종 각각의 **재사용 vs 신규 판정과 근거**. 교차앱 소비자 점검 결과(D1 전제 유지/파기).
4. **DECISIONS 3건:** D1·D2·D3가 DECISIONS.md에 기록됐고 모델 커밋보다 앞섬을 커밋 순서로 증명.
5. **격리 테스트:** 신규 4테이블(UserGoal·WatchlistItem·WalletHolding·CashBalance)의 user 스코프 격리 테스트 존재·통과, 등록 가드 동작.
6. **필드 확정 근거:** 각 모델 필드가 STEP 0의 무엇(기존 모델·shared 종목 식별)에 맞춰 최소 설계됐는지.
7. **후보(유보):** prod 마이그레이션 적용 후보, 구현 중 발견한 "재검토 후보"(D 재오픈 금지 대상), TASKQUEUE에 넘길 잔여.
8. **HALT 발생 여부:** STEP 0/구현 중 HALT가 있었으면 무엇을·어떻게 처리했는지.

---

## 7. HALT 트리거 요약 (멈추고 사용자에게 보고)

- **STEP 0에서 기존 모델과 의미 중복 발견** → 재사용 가능성. (§2c) — 1순위.
- **STEP 0 교차앱 소비자 발견** → D1 전제 파기, shared 승격 재결정 필요. (§2c, §4 D1)
- **baseline pytest에 red 존재** → 깨끗한 출발선 아님. (§2b)
- **빈 스키마 / 마이그레이션 dry-run이 예상 밖 테이블 대공사** 신호.
- **shared→apps 경계를 넘어야만 풀리는 상황** / 아키텍처 테스트 신규 위반.
- **파괴적 작업(prod 반영·삭제)이 필요해 보이는 지점** → 후보로만 보고, 강행 금지.
- **결정 절대 규칙(D 재오픈 금지)을 넘어야 하는 상황** → 사용자 수동 승인.

---

## 8. 다음(19a) 연결 — 왜 지금 이걸 이렇게 만드나 (참고, 이번 세션 작업 아님)
Slice 19a "목표 대비 권유 엔진"은 `UserGoal`(목표) vs `WalletHolding`+`CashBalance`(현재 상태)를 비교하고, `WatchlistItem`(후보)을 목표 갭에 대어 "무엇을 사고 무엇을 지킬지"를 만든다. 그래서 18의 필드는 *19a의 비교 연산에 필요한 최소*로 잡는다(과설계는 19a에서 후회로 돌아옴). Slice 20은 이 위의 화면.
