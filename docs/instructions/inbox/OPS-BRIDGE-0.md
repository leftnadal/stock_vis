---
track: OPS-BRIDGE-0
status: dispatched 2026-09-16 (Cowork 디렉터)
status: done @f4754d22 (2026-09-17 3차 실행 — S2 `85eae8d8` · S4 `0ff0949e`→`f4754d22` · S3 ⓐ 분해 랜딩)
approved_by: 병진 2026-09-16 "동의해. 진행하자" — 관제판 §08 ①②(즉시 랜딩 2건 + 배포) 승인
approved_sha: b0fadfa3 (CS-S3-1D, 본체 main 직접 커밋분) · e1b8e345 (EOD-TIME-1, monorepo/sess-eod-time1)
---

# OPS-BRIDGE-0 — main 발산 해소 + 즉시 랜딩 2건 + 배포 + 결정 3건 등재

**세션**: ops · cwd = 본체 `~/Desktop/stock_vis`(main 전용 머지 지점). 부트스트랩 체인(CLAUDE.md → STARTUP_CHECKLIST → SESSION_CONTRACT) 준수.
**승인 범위**: 위 `approved_sha` 두 커밋에 한정. **브랜치 HEAD가 그 SHA가 아니면 HALT**(INC-005 — 승인 SHA 이탈 금지).
**디렉터 실측(13:33 KST, 재측정 대상)**: 본체 main=`b0fadfa3`(ahead1/behind5) · origin/main=`bdadd045` · sess-eod-time1=`e1b8e345`(ahead2/behind46) · 런타임 3트리=`2eca515d`.

## S0 — 앵커 (다르면 HALT)
`git fetch origin --prune` → 본체 `main`==`b0fadfa3`, `origin/main`==`bdadd045`(전진했으면 새 해시 보고 후 계속 가능), 본체 tracked dirty 0(`git status --porcelain --untracked-files=no`), `monorepo/sess-cs-s3-1d` **부재** 확인.
본체 `.git/index.lock.stale-cowork-20260916`(0바이트, 디렉터 사고 잔여)는 무해 — 건드리지 않는다.

## S1 — 발산 해소 (내용 판단 없음: 커밋을 브랜치로 옮기고 main을 되돌린다)
1. `git branch monorepo/sess-cs-s3-1d b0fadfa3` → `git merge-base --is-ancestor b0fadfa3 monorepo/sess-cs-s3-1d` 참 확인.
2. `git worktree add ~/worktrees/sv-cs-s3-1d monorepo/sess-cs-s3-1d`.
3. 본체: `git reset --hard origin/main` → `main`==origin/main 확인. (커밋은 1에서 보존됨 — 유실 0. 비추적 29건은 reset 영향 없음.)

## S2 — CS-S3-1D 랜딩 (worktree `sv-cs-s3-1d`)
역머지 `git merge origin/main` → 충돌 시 **HALT**(장부 3파일 충돌만 양쪽 보존 append 허용) → 게이트: `vitest` 전체 · `pytest tests/` 전체 · `tsc --noEmit` **모두 0 failed** 아니면 HALT+실패 목록 → 본체 main no-ff 머지 → 머지 직전 `fetch`로 origin/main 재확인(움직였으면 GUARD-1D 규칙: 흡수 후 1층 재실행) → push → `fetch` 후 ahead 0 확인.

## S3 — EOD-TIME-1 랜딩 (worktree `sv-eod-time1`, HEAD `e1b8e345`)
1. **장부 선기재(이 브랜치에서, 머지 전)**:
   - `docs/instructions/inbox/` 4파일(README·OPS-BRIDGE-0·OPS-GATE-1·OPS-DISPATCH-1)을 본체에서 이 worktree로 복사해 커밋(0번 게이트 사후 충족).
   - `DECISIONS.md` **D-OPS-BRIDGE**: 병진 승인 3건 — ⑴ 지시서 통로 = A 메일박스+디스패처(4.20) 구축, 구축 중 B Remote Control(3.75) 운용 ⑵ 랜딩 게이트 = ⓑ 랜딩 승인 1회(4.25, 타이브레이커 안전) — `approvals/<트랙>.ok`(sha) → 역머지→게이트→머지→push→sync→FE리빌드, HALT는 충돌/RED/마이그·beat·plist·prod-write 동반 3경우, 병진 수동 항목 불변 ⑶ 장부 = ⓑ STATUS 자동생성+회전(4.15). 근거 문서: 프로젝트 `claude/판독_하네스점검_결정3건_20260916.md`. D-PUSH-DELEG (ii)·"푸시 1회 1승인"은 **OPS-GATE-1 착지 시 v2로 대체 예정**(그때까지 현행).
   - `TASKQUEUE.md`: EOD-TIME-1 → LANDED 예정 표기 / 신규 `OPS-GATE-1`·`OPS-DISPATCH-1`·`OPS-STATUS-1` 등재(inbox 참조) / `EOD-FRESH-2` "R1 재측정 선행" 유지.
   - `PROGRESS.md` 갱신 1블록.
2. 역머지 `git merge origin/main`(behind 46+) → 충돌 규칙 S2와 동일 → 게이트 → 본체 no-ff 머지 → 직전 fetch 재확인 → push → ahead 0.

## S4 — 배포 (§H D-DEPLOY-DELEGATE + 위 승인 인용)
`sv sync`(**`~/bin/sv` 래퍼 경유**, worker_sync.sh 직접 호출 금지) → 3트리 HEAD==새 origin/main 확인 → CS-S3-1D에 frontend 변경 있음 → **web 프로덕션 리빌드 = `docs/runbook/DEPLOY.md` §2.2 절차 그대로**(빌드 실패 시 .next.bak 복원·중단) → `:3000` 200 · daphne 401 정상 · `python scripts/health_check.py` ❌ 신규 0.

## 금지
force/force-with-lease · 브랜치·worktree **삭제** · 원격 브랜치 삭제 · prod DB migrate/쓰기 · launchd plist 변경 · beat 엔트리 변경 · 타 세션 브랜치(`sv-dss-asof` 등 활성) 무접근.

## 보고 — `docs/instructions/outbox/OPS-BRIDGE-0_보고.md` (커밋) + 채팅 답신, **25줄 이내**
① 판정 1줄(합격/불합격/HALT) ② 해시 표: 본체 main·origin/main **전/후**, 3트리, 새 머지 커밋 2개 ③ 게이트 숫자(vitest/pytest/tsc × 2회) ④ 배포 확인 3종(:3000·daphne·health) ⑤ 장부 추기 커밋 ⑥ HALT였다면 지점·원인·디렉터에게 묻는 질문 1줄.

## 재개 지시 2026-09-17T11:45+09:00 (디렉터 · 1차 HALT 판독 후)
- **판독**: 1차 실행 합격. S0 일치·S1 해소·S2 게이트 2회 GREEN·S3.1 장부 선기재 = git 대조 일치. 머지 직전 정지 처신 **옳았음**(공유 트리 동시 사용 + 분류기 거부). `EOD-FRESH-2` 미등재 판단도 옳았음 — 그 항목은 프로젝트 문서에만 있고 repo 장부에 없었다(디렉터 지시서 결함).
- **재개 범위 = (A)**: 병진 승인(2026-09-16 "동의해. 진행하자", 승인 SHA `b0fadfa3`·`e1b8e345` 포함 브랜치)은 S2 머지·push → S3 → S4 `sv sync`·web 리빌드까지 유효하다. 새 승인 불요.
- **재개 절차 (순서 고정)**:
  1. 본체에서 `git fetch` → `main == origin/main` · tracked dirty 0 · `.git/MERGE_HEAD` 부재 · `git worktree list`에 새 항목 없음을 재확인. 하나라도 어긋나면 HALT(공유 트리 동시 사용 의심).
  2. 본체에 락: `.git/land.lock` 파일을 만들고(`set -o noclobber`) 내용에 `OPS-BRIDGE-0 <ISO> pid`를 적는다. 이미 있으면 HALT. 완료·HALT 시 반드시 제거.
  3. S2: `sess-cs-s3-1d`가 origin/main 대비 behind 0이면 그대로, 아니면 역머지+1층 재실행 → 본체 `git merge --no-ff monorepo/sess-cs-s3-1d` → `git push origin main` → fetch·ahead 0.
  4. S3: `sess-eod-time1` 역머지(장부 3파일 union) → 게이트 3종 → 본체 no-ff 머지 → push → ahead 0. 이 inbox 파일의 본체 사본(재개 지시 포함)과 `OPS-GATE-1.md` 갱신분을 브랜치 사본에 반영해 함께 랜딩.
  5. S4: `sv sync` → 3트리==origin/main → web §2.2 리빌드 → `:3000` 200 · health 신규 ❌0.
  6. 락 제거 → outbox 보고를 **갱신**(같은 파일, 상단에 "2차 실행" 절 추가) → 커밋·push.
- 분류기가 또 거부하면: 거부된 **명령 원문**과 사유를 보고에 적고 HALT. 우회·재시도 금지.

## 재개 지시 2 — 2026-09-17T15:40+09:00 (디렉터 · 2차 HALT 판독 후 · 병진 결정 반영)
- **판독**: 2차 실행 합격. S2 착지(`85eae8d8`, origin/main 포함 확인) · S3 역머지 충돌에서 abort·락 제거·보고 = 처신 옳음. 자가 해소 불가 판단도 옳음.
- **병진 결정 15:35 — ⓐ 분해 랜딩** (선택지 ⓐ 4.45 / ⓒ 4.00 / ⓑ 2.70): main의 T4 판정 로직 **유지**(행위보존 IDENTICAL), EOD-TIME-1에서 가치 확증분만 이식, **R1(baker is_stale TZ) 제외** → EOD-FRESH-2 재측정으로 이관.
- **디렉터 결함 인정**: EOD-TIME-1 승인 시 R1(근거 미확정·공유 존)과 R4(가치 확증)가 한 커밋(`f45fcb78`)에 묶인 것을 분리하지 않고 통째로 승인했다. 이번에 바로잡는다.
- **현재 실측(15:38)**: origin/main `0ff0949e`(recover-1 착지 15:14 포함) · 본체 **`monorepo/sess-near-stop` 체크아웃 + tracked dirty 4** = 타 세션이 본체 점유 중 → **본체에서의 머지·push 금지**(아래 절차는 본체 무접촉). 런타임 worker/api `2eca515d`, web `029f57f6`(14:27 타 주체). 2eca515d..0ff0949e = 20커밋 · 마이그 0 · 의존성 0 · frontend 12파일.

### 절차 (본체 무접촉 · 순서 고정)
1. **S4 선행 — 지금 origin/main(`0ff0949e`) 배포** (승인 범위 내 · 본체 불필요): `~/bin/sv sync` → worker/api/web 3트리 == `0ff0949e` 확인 → DEPLOY.md §2.2 web 리빌드(.next.bak 백업 → build → kickstart → `:3000` 200 → BUILD_ID 갱신 확인) → `python scripts/health_check.py` 신규 ❌ 0. `deploy_history.log`에 기록되는지 확인.
2. **S3' 새 브랜치**: `bash scripts/wt-open.sh eod-time1-r4 "EOD-TIME-1 분해 랜딩(R4 테스트+3원칙 문서)"` → `~/worktrees/sv-eod-time1-r4`(base origin/main). 기존 `sess-eod-time1`·`sv-eod-time1`은 **삭제 금지**(이력 보존, 처분은 병진 수동).
3. **이식 (from `f45fcb78`, 파일 단위)**:
   - `auto_agent_system/dogfood/market_calendar.py`: `trading_days_between` + `__all__` 추가(additive).
   - `tests/dogfood/test_market_calendar.py`: 추가분 그대로.
   - `auto_agent_system/dogfood/check_quant.py`: **판정(`status`)은 main T4(`trading >= previous_trading_day(session)`) 그대로**. note 문자열만 확장: `"… 지연 {lag_calendar}일(거래일 기준 {lag_trading}일 — 주말/휴장 포함|없음)"` 형태로 `trading_days_between` 값을 병기(3원칙 ③). `MAX_FRESHNESS_LAG_TRADING_DAYS` 상수는 도입하지 않는다.
   - `tests/dogfood/test_quant_schema.py`: R4 테스트 6종(`test_freshness_ok_holiday_gap_regression_09_09` · `_ok_weekend_gap_monday` · `_ok_consecutive_weekday` · `_ok_thanksgiving_three_day_pattern` · `_fails_when_two_trading_days_behind` · `_note_flags_weekend_holiday_inclusion`) 이식. T4 기존 테스트 2종 유지. 6종이 T4 로직에서 **그대로 GREEN이어야** 한다 — RED가 나오면 로직 차이가 실재한다는 뜻이니 **HALT하고 어느 케이스가 갈리는지 보고**(수리 금지).
   - `docs/harness/SESSION_CONTRACT.md` §J(3원칙) + `sub_claude_md/common-bugs.md` 3원칙 절(채번 대기 표기 유지·채번 금지): 이식.
   - **제외**: `packages/shared/stocks/services/eod_json_baker.py` · `tests/unit/stocks/test_eod_json_baker.py` · common-bugs의 R1(TZ) 서술이 있으면 그 부분.
4. **장부 이식**: 구 브랜치의 docs 커밋 `af915df3`·`d65e832c`·`e731a21e`·`290d9341`·`ef63b5f8`를 새 브랜치에 cherry-pick(장부 3파일 충돌은 union). 그 위에 추기: TASKQUEUE `EOD-TIME-1` → "R4 분해 랜딩 @<커밋> · R1 → EOD-FRESH-2(재측정 선행: compute_is_stale과 베이커 플래그 동일 함수 여부 → 09-08~11 True/09-14 False 시계열이 정상 동작인지 판정)" · DECISIONS `D-OPS-BRIDGE`에 "ⓐ 분해 랜딩 결정 15:35" 1줄 · PROGRESS 갱신. 이 inbox 파일(재개 지시 2 포함) 사본 반영.
5. **게이트**: vitest 전체 · `pytest tests/` 전체 · tsc — 0 failed. 특히 `tests/dogfood` 8종 전부 GREEN 명시.
6. **랜딩 — 본체 우회**: 본체가 main이 아니므로 **임시 랜딩 worktree**로 머지한다: `git worktree add ~/worktrees/sv-land-tmp origin/main --detach` → `cd` → `git merge --no-ff monorepo/sess-eod-time1-r4` → 직전 `fetch` 재확인(origin/main 전진 시 흡수+1층 재실행) → `git push origin HEAD:main`(force 금지) → fetch·`origin/main`==머지 커밋 확인 → `git worktree remove ~/worktrees/sv-land-tmp`(**자기 임시 트리만** — INC-006 예외: 이 지시서가 명시 허용). 본체 main 로컬 ref는 건드리지 않는다(near-stop 세션이 끝나면 `git pull --ff-only`로 따라옴).
7. **S4 후속**: 6 착지 후 다시 `sv sync` + web 리빌드(frontend 무변경이면 리빌드 생략 가능 — `git diff --name-only <이전 배포 해시> origin/main -- frontend/` 0이면 생략, 근거 기재).
8. outbox 보고 갱신("3차 실행" 절 상단 추가) → 새 브랜치에 커밋 → 6에서 함께 랜딩되도록 순서 조정(보고는 랜딩 전 커밋, 최종 해시만 push 후 1줄 추기·재커밋·재푸시 허용).

### 금지·HALT
본체(`~/Desktop/stock_vis`) 무접촉(읽기 제외) · 기존 브랜치/worktree 삭제 금지(임시 `sv-land-tmp` 제외) · R1 코드 반입 금지 · 3에서 테스트 RED = HALT · sv sync/리빌드 실패 = 되돌리기(.next.bak) 후 HALT.

## 재개 지시 3 — 2026-09-17T16:00+09:00 (디렉터 · 3차 HALT 판독 후)
- **판독**: 3차 실행 합격. S4 선행 배포 완료 — 3트리 `0ff0949e` · BUILD_ID `K28tDV8a…`→`FJH-7rSq…` · `:3000` 200 · health 신규 ❌0 = 디렉터 실측(15:54) 일치. `.next.bak` `rm -rf` 거부에서 정지한 처신 옳음.
- **`.next.bak` 처분 = 삭제하지 않고 개명**: `mv ~/worktrees/sv-web-runtime/frontend/.next.bak ~/worktrees/sv-web-runtime/frontend/.next.bak.stale-20260917-1536` (rm 계열 명령 사용 금지 — 분류기 거부 원인 제거 + "영구 삭제는 병진 수동" 규칙 준수). 보고 ⑦에 "삭제 후보: 위 경로"로 등재. 절차 7의 리빌드 전에도 같은 방식(직전 `.next.bak`을 개명 후 새 백업).
- 그 외 재개 지시 2의 **절차 2~8 그대로 진행**. 현재 실측(15:55): origin/main `0ff0949e` 무변경 · 본체 `sess-near-stop` `d2f2b7a2` dirty 0(여전히 점유 → 본체 무접촉 유지) · 새 활성 worktree `sv-s3-1d`(base 0ff0949e)·`sv-mgmt-b49` 관측됨 — 랜딩 직전 fetch 재확인 규칙(절차 6)으로 흡수.
