# 개정문 1: verify launchd repoint — 대체안 승인 (self-locate 래퍼 + α 트리)

- 발행: 감독 세션, 2026-07-24
- 원 지시서: `docs/instructions/Verify launchd repoint directive.md` (2026-07-21 발행) — **수정 불가, 발행 시점 보존**
- 개정 사유: STEP 0 실측에서 원 지시서 §2-1의 "plist 경로만 최소 변경" 스펙이 **물리적 불가**로 확인됨. 래퍼 `verify-pair.sh`가 `PROJECT_DIR`를 공유트리 경로로 하드코딩하고 `cd`하므로 plist repoint만으로는 실행 트리가 바뀌지 않는다(래퍼가 다시 공유트리로 복귀).

## STEP 0 확정 사실 (실측)

- 현행 plist `com.stockvis.verify-pair`: ProgramArguments·WorkingDirectory 모두 `/Users/byeongjinjeong/Desktop/stock_vis`(공유 세션트리, sess-hold-p1).
- 공유트리엔 `scripts/lib/ops_verify_checks.py` 파일 부재(b76d9ab 미포함) → 라이브 verify는 section D 없는 구버전 py 실행. drift 재확증.
- origin/main 전진: `9f2e6c5`→`adf0e09d`. b76d9ab(section D) ⊂ adf0e09d 확인.
- 런타임 트리 worker/api = adf0e09d(오늘 09:08 동기화)·의존 클로저(래퍼+py+ops_verify_checks+.env) 완비. web = .env 없음(탈락).
- `verify_pair_aggregation.py`는 `__file__` 기준 repo 루트 self-locate → cwd 무관하게 자기 트리 코드 사용. 유일한 cwd 결합 = 래퍼의 하드코딩 `cd`.

## 승인 결정

- **대체안 1안 승인**: `verify-pair.sh`의 `PROJECT_DIR`를 `BASH_SOURCE` 기준 self-locate로 도출(최소 변경).
- **§1 결정 = α (sv-worker-runtime)**: origin/main 추적·worker_sync 전파·.env 완비. 경계는 도메인 런타임에 얹히나 이동부품 추가 없음.

## 집행 순서 (엄수)

0. 개정문 커밋(본 파일). 원 지시서 미수정.
1. 코드 수정(격리 worktree): `verify-pair.sh` `PROJECT_DIR`→`BASH_SOURCE` self-locate 최소 변경. 명시 pathspec만.
2. 행위보존 입증(착지 전): 래퍼가 `Desktop/stock_vis/scripts/verify-pair.sh` 위치에 있을 때 self-locate 결과 == 기존 하드코딩 값 `/Users/byeongjinjeong/Desktop/stock_vis` 실측 증명(같은 위치 호출 시 거동 IDENTICAL). 실패 시 HALT.
3. 착지: origin/main으로 아톰 ff-push.
4. 전파 확인: worker_sync 다음 주기 실측, sv-worker-runtime 래퍼에 self-locate 반영을 파일 내용으로 확인. 다음 자연 주기가 오늘 02:30 이전이면 대기. 이후면 worker_sync 1회 수동 발화를 본 승인으로 인용 허용 — 발화 후 같은 shell 재조회로 반영 확증.
5. plist(병진 수동, 원 지시서 §2-2 불변): ProgramArguments·WorkingDirectory→sv-worker-runtime 래퍼 기준 후보 plist diff를 CC가 작성·제시, 병진이 백업→교체→bootout→bootstrap, CC가 §2-3 실효 경로 재실측.
6. §3 양방향 자가검증 원 지시서 그대로(수동 발화 PRE/A/B/C IDENTICAL + section D 인위 발화·원복 확증).

## 금지 불변

- Desktop 공유 트리 쓰기 접촉 금지.
- 이 범위 밖 파일 접촉 발생 시 HALT.
- Phase 3 봉인은 여전히 익일 라이브 02:30 관찰로만 선언.
