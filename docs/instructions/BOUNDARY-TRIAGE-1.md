# BOUNDARY-TRIAGE-1 — 경계 회귀 동결 격리 + mgmt 채번 배치

## 계약 헤더
- 트랙: 경계 가드 회귀 대응(ops 소유) + mgmt 장부 / ID: BOUNDARY-TRIAGE-1
- 세션: mgmt(채번 자격 有) / worktree ~/worktrees/sv-btriage1
  · 브랜치 monorepo/sess-mgmt-btriage1 (origin/main 기점 신규)
- 성격: 동결(격리)만. 위반 코드의 실제 수정은 범위 밖 — 소진 트랙 등재만.
- 쓰기 허용 (이외 전면 금지): docs/instructions/BOUNDARY-TRIAGE-1.md ·
  tests/architecture/test_shared_boundary.py(KNOWN_VIOLATIONS만) ·
  scripts/health_check.py(동결 동기만) · DECISIONS.md · TASKQUEUE.md ·
  sub_claude_md/common-bugs.md · PROGRESS.md.
  eod_signal_calculator.py 등 위반 코드 자체 수정 금지.
- DB read-only · FMP 0 · foreground · add 명시(-A 금지) · force 금지 · push=D-PUSH-DELEG.
- 커밋: 1=지시서(0게이트) → 2=동결+동기 → 3=장부. 중간 승인 게이트 없음. HALT-0.

## STEP 0 — read-only
0-1. 통상(worktree/HEAD/health/clock). 경계 ERROR 존재 재확인(전제).
0-2. 위반 전수 실측: 아키텍처 테스트 2종(shared_boundary·llm_direct_call) 실행, 위반 목록 전수.
     동결 목록은 이 실측이 정본(1건 가정 금지).
0-3. 경위 실측(사실만·판단 금지): 7ec24c62 커밋 메시지·본문에 경계 red 인지/신고 문구 존재
     여부, 변경 파일 목록. INC 판정 재료.
0-4. 소진 재료 실측: 해당 import의 사용처(함수·호출자)와 apps.monitor 측 모델 성격 —
     방향1(소비자 이동)/방향2(주입)/방향C(승격) 판단 재료 수집만, 방향 결정은 디렉터.
0-5. 채번 베이스: common-bugs 최대 번호 실측.

## 작업 (T1~T5) — 지시서 §작업 원문 준수

## HALT
0-2 위반이 예상 밖 다수(>3) / 동결 후 green 미회복 / 쓰기 범위 밖 필요 / 예상 밖 일체.

---

## 집행 결과 (BOUNDARY-TRIAGE-1, 2026-08-27 machine clock)

### STEP 0
| # | 항목 | 결과 |
|---|---|---|
| 0-1 | worktree/HEAD/clock | sv-btriage1 @ origin/main `69605758` · 2026-08-27 15:51 KST |
| 0-1 | health / 경계 ERROR | 14 OK / 1 WARN(runtime_check=(i)) / **1 ERROR "shared 경계 우회 1건"** — 전제 성립 ✅ |
| 0-2 | 위반 전수 | **shared_boundary = 1건**: `stocks/services/eod_signal_calculator.py:50 ← from apps.monitor.models.monitor`. **llm_direct_call_boundary = GREEN(6 pass, 위반 0)**. 동결 목록 정본 = 1건(HALT >3 미달) |
| 0-3 | 경위(사실) | 7ec24c62(2026-08-26, EODUNIV-P15-V01 PART A). 메시지 A-2 = "Monitor(scope=stock) target_ref union 편입" 기능 설명만 — **경계 red 인지/신고 문구 부재**. 변경 3파일(backfill 커맨드 신규·eod_pipeline·eod_signal_calculator +95줄, 위반 유입). |
| 0-4 | 소진 재료 | 위반 함수 = `eod_universe_symbols()`(line 28), lazy import(50)→`Monitor(scope=stock).target_ref` union(52). 호출자 전부 packages/shared 내부(backfill_eod_signals_universe·eod_pipeline:297,570). Monitor = user-data 모델(scope/target_ref). 방향 재료: 방향2(주입=호출자 심볼 주입) / 방향C(승격=VIXProvider식 의존역전, BOUNDARY-3 선례). **방향 결정=디렉터**. |
| 0-5 | 채번 베이스 | common-bugs 최대 = #118(LAND-SCAN-B1) → 채번 #119·#120·#121 |

### T1 동결 (커밋 2)
- 동결 키(양쪽 동일): `("stocks/services/eod_signal_calculator.py", "apps.monitor.models.monitor")`
- test_shared_boundary.py:KNOWN_VIOLATIONS + health_check.py:_BOUNDARY_KNOWN_VIOLATIONS 동시 갱신(SSOT).
- 등록 후: shared_boundary 테스트 GREEN · health 경계 ERROR 해소 확인.

### T2~T5 장부 (커밋 3)
- TASKQUEUE BOUNDARY-BURNDOWN-EOD 등재(동결 1→0 소진, 재료=0-4, 방향=디렉터, EODUNIV-P15 통지 필요).
- DECISIONS 동결 결정(회귀 격리·소진 예약·0-3 경위 인용).
- common-bugs 채번 3건: #119 health WARN 유형(verbatim) · #120 비-mgmt #NN 금지(verbatim) · #121 경계 red 착지 회귀(신규).
- PROGRESS 갱신.
