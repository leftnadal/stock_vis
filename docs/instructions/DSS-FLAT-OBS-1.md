# DSS-FLAT-OBS-1 — 관찰 게이트 실측 + 조건부 FMP 정찰 + 장부 편승 지시서

## 계약 헤더
- 트랙: DSS-FLAT-OBS(관찰 집행) + 장부 편승 2건 / 지시서 ID: DSS-FLAT-OBS-1
- 세션 종류: 관찰(read-mostly) + 한정 쓰기 / worktree ~/worktrees/sv-dss-flatobs1
  · 브랜치 monorepo/sess-dss-flatobs1 (origin/main 기점 신규)
- 쓰기 허용 (이외 전면 금지):
  (W1) docs 4파일 — docs/instructions/DSS-FLAT-OBS-1.md · DECISIONS.md · TASKQUEUE.md ·
       sub_claude_md/common-bugs.md
  (W2) DB INSERT 한정 — SymbolDemandSignal(anchor 2026-08-21) · ThemeDemandScore(date 2026-08-21,
       11행). 기존 행 UPDATE/DELETE 절대 금지. 마이그레이션 금지. 신규 코드 파일 금지 —
       기존 demand_signal 서비스/dss_backfill 경로로만 계산·적재하고, 코드 수정이 필요하다고
       판단되면 집행하지 말고 HALT(범위 밖).
- FMP 예산: 기본 0회. §3 재발 분기 발동 시에만 ≤10회. 초과 필요 판단 시 HALT.
- 실행: foreground-only · machine clock. git add 명시 지정(-A 금지) · force 금지.
  push = D-PUSH-DELEG. behind>0 흡수: docs-only면 D-GOBS-REBASE-STANDING,
  코드/DB 산출물 포함 상황이면 D-PUSHDELEG-REBASE-ABSORB 5조건. 예상 밖 충돌 HALT.
- 커밋 계획: 커밋 1 = 본 지시서(0번째 게이트 — 승인 게이트 이전 유일 허용 쓰기)
  → 이후 연속 집행(중간 승인 게이트 없음 — 판정 기준 전부 기계화됨). HALT-0 기본.

## STEP 0 — read-only 실측
0-1. worktree 생성·확인 / origin/main HEAD / health_check(WARN 시 유형 구분 명시) / machine clock.
0-2. EstimateSnapshot 회차 실측: 7회차(08-21) 발화 여부·행수·심볼수.
     미발화면 → 적재 파이프라인(beat) 이상 신호 = HALT·보고(이후 절차 진행 금지).
0-3. SymbolDemandSignal에 anchor 08-21 기존재 여부 실측.
     기존재 → §1 계산 skip, 기존 행으로 §2 판정 진행(이중 적재 금지).
0-4. 유니버스 active 수·EA 상태 1줄(분모 예측치 확립).

## §1 — 08-21 anchor 계산·적재 (0-3 부재 시에만)
- 기존 서비스로 08-14→08-21 WoW 계산: 동일-FY 조인(D-DSS-FY-MATCH) + |Δanalysts|≥2 제외
  (D-DSS-ANALYST-FILTER) 그대로. Signal INSERT + Score 11행 INSERT(components에 breadth·유효분모).
- date-scoped invariant 검산(IMPL-1 Slice 4와 동일): up+down+flat+excl=시도 수 /
  breadth∈[−1,+1] / 전 섹터 유효분모>0. 실패 시 HALT.
- 예측 대조 보고: HONA는 08-14 데이터 기존재이므로 이번 쌍에서 excluded=missing_prev가
  아니어야 정상 — 결과 명시.

## §2 — 게이트 판정 (기계 기준, 사전 확정)
flat_ratio = flat / (n − excluded) 산출 후:
- < 60% → [정상 복귀] TASKQUEUE의 DSS-FLAT-OBS에 "08-14 = 저신호 주간(원인: FMP 해당 주
  무갱신 추정·재발 없음) 기록 종결" + 양 주(08-14/08-21) flat 비율 수치 기입. FMP 0회.
- ≥ 90% → [재발] §3 FMP 정찰 발동. TASKQUEUE에는 수치 + "정찰 결과 첨부·디렉터 판정 대기"로
  기입(종결 기입 금지).
- 60~90% → [회색지대] 수치만 기입, 종결 기입 금지, 보고에 "디렉터 판정 대기" 명기. FMP 0회.

## §3 — 조건부 FMP 표본 대조 정찰 (§2 재발 시에만, ≤10회)
- 표본 5심볼: 섹터 분산해 DB에서 선정(대형주 우선), 각 1회 = 5회. 잔여 예산은 재시도 전용.
- 기존 FMP client의 추정치 엔드포인트로 현재 컨센서스 조회 → 08-21 스냅샷 저장값과
  심볼별 대조(EPS 동일/상이) + 응답 내 갱신 시각류 필드(date/lastUpdated 등) 원문 캡처.
- 판정은 하지 않는다 — 대조표·필드 원문만 보고(원인 판결 = 디렉터).

## §4 — 장부 편승 (문안 확정본 — 내용 변경 금지, 번호는 실측 최대+1)
B-1. common-bugs 신규 채번: "health WARN 유형 판정 기준 — (i) 환경·동기화 신호성 WARN
     (예: 미푸시 세션 상태로 인한 sync 계열)은 보고 후 진행 가능. (ii) 시스템 검사에서 신규
     발생한 WARN/FAIL은 명목 HALT. STEP 0 보고에 유형 구분을 명시한다.
     실증: MGMT-LEDGER-1 STEP 0-2 (08-19)."
B-2. DECISIONS의 D-BRANCH-DELETE-MANUAL에 부기 1줄: "위임 불가 실증 — 디렉터 경유 명령에도
     CC 자발 보류·상신 (08-19, MGMT-LEDGER-1)."

## HALT 트리거
health FAIL 또는 신규 WARN(B-1 기준 (ii)) / 0-2 미발화 / 쓰기 허용 범위 밖 변경 /
invariant 실패 / 코드 수정 필요 상황 / FMP 예산 초과 필요 / 예상 밖 상황 일체.

## 보고 양식
STEP 0 표 → §1 적재 수치(또는 skip 근거)·검산·HONA 대조 → §2 판정(flat_ratio 양 주 비교)
→ (해당 시) §3 대조표·필드 원문 → §4 반영 확인 → 커밋 해시 → HALT 이력 →
push 대기 블록(behind/ahead, D-PUSH-DELEG 가드 재확인 문언).

---

## 집행 결과 (DSS-FLAT-OBS-1, 2026-08-24 machine clock)

### STEP 0
| 항목 | 결과 |
|---|---|
| 0-1 worktree/HEAD/clock | sv-dss-flatobs1 @ origin/main `be6888ea` · 2026-08-24 12:57 KST |
| 0-1 health_check | 14 OK / 1 WARN / 1 ERROR — 둘 다 **(i) 환경·동기화 신호성** (ERROR=PROGRESS 89.5h stale, WARN=runtime_check 드리프트 동기 신호). 신규 시스템 WARN/FAIL 0 → HALT 미발동 |
| 0-2 EstimateSnapshot 7회차(08-21) | **발화 ✅ rows=1005 · syms=503** (6회차 08-14 동일) |
| 0-3 SymbolDemandSignal anchor 08-21 | **부재 → §1 계산 진행**. anchor 08-14 존재(502행) |
| 0-4 유니버스·EA | UniverseSnapshot 08-23 n=503 · EA(Electronic Arts) estimates 08-14/08-21 = 0(+1 유령 해소)·유니버스 부재 |

### §1 적재 (0-3 부재 → 집행)
- `store_for_anchor(2026-08-21, dry_run=False)`: written_signals=**502**, written_scores=**11**. append-only(사전존재 skip 내장, UPDATE/DELETE 0).
- date-scoped invariant: inv1 합=n(502==502) ✅ · inv2 breadth∈[−1,1] ✅ · inv3 유효분모>0(11 scored, not_computed 0) ✅ · Score 11행 ✅ → **PASS**.
- HONA @08-21: excluded=False, dir=−1 → **missing_prev 아님**(예측 정합). exclude 사유 = analyst_delta 35 (missing_prev 0).

### §2 판정 — [정상 복귀]
- **flat_ratio: 08-14 = 498/500 = 99.60% → 08-21 = 35/467 = 7.49%** (<60%).
- 08-14 = 저신호 주간(원인: FMP 해당 주 무갱신 추정·재발 없음) **기록 종결**. FMP 0회, §3 미발동.

### §4 장부 편승
- B-1 = common-bugs **#118** (문안 확정본 verbatim).
- B-2 = DECISIONS D-BRANCH-DELETE-MANUAL 부기 1줄.
- TASKQUEUE DSS-FLAT-OBS 종결 기입.
