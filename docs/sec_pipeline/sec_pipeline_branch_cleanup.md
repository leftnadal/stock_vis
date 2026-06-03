# 지시서 — sec-pipeline 브랜치 정리 (+ 세션 계약서 첫 실사용 검증)

## 너의 역할 / 현재 위치

- 세션 종류: **관리(mgmt)**. worktree = `stock_vis_mgmt`에서 시작.
- baseline: main = origin/main = `e92991e` (동기). health 8✅/0⚠/0❌. 경계 ✅ 우회 0 / 동결 2(#4·#5).
- **이중 목적:** ① 막 만든 세션 계약서를 _처음으로_ 실사용(검증) ② main에 머지된 sec-pipeline 브랜치 2개 정리.
- 안전·가역 작업이라 새 프로세스 첫 시험용으로 적합. **검증이 본 목적, 브랜치 정리는 그 핑계감.**

## ⛔ 절대 규칙 (위반 시 즉시 HALT · 보고)

1. **머지된 브랜치만 삭제.** 삭제는 `git branch -d`(소문자)만 사용 — git이 미머지 브랜치를 자동 거부하는 내장 안전장치. `-D`(강제) **금지**.
2. **삭제 후보가 `git branch --merged main` 목록에 없으면 즉시 HALT** + 보고. 머지 안 된 sec-pipeline 브랜치는 손대지 않음.
3. **원격(origin) 브랜치는 이 세션에서 삭제하지 않음.** 후보만 보고하고 사용자 결정 대기(원격 삭제 = 공유 상태 변경).
4. **main·기타 브랜치 무변경.** sec-pipeline 외 어떤 브랜치도 손대지 않음.
5. 삭제 전 각 브랜치의 tip 커밋 해시를 기록(삭제해도 reflog로 복구 가능하게).

## STEP 0 — 계약서 첫 실사용 + 사실 확인

1. **worktree 확인:** `git worktree list` → 지금 `stock_vis_mgmt`인지, main 위에 있고 origin/main(`e92991e`)과 동기인지.
2. **계약 헤더 채우기** — STARTUP_CHECKLIST Step 0대로 SESSION_CONTRACT §C 헤더 작성(세션 종류=mgmt / 범위=sec-pipeline 브랜치 정리 / baseline=`e92991e`). ← **이게 계약서 첫 실사용. 흐름을 의식하며 진행.**
3. `python scripts/health_check.py` → **8✅** 확인.
4. **브랜치 실측:**
   - `git branch --merged main` → 머지 완료 목록.
   - `git branch | grep -i sec` → sec-pipeline 브랜치 식별(2개 기대).
   - 그 2개가 `--merged` 목록에 **포함**되는지 교차 확인. (sanity: `git branch --no-merged main` 에는 **없어야** 함.)
   - 각 tip 기록: `git log -1 --oneline <branch>`.
     → **STEP 0 결과 보고 후 진행.** 2개가 머지 목록에 없거나 sec-pipeline 브랜치 개수가 다르면 HALT.

## Part 1 — 로컬 브랜치 정리

- `git branch -d <sec-branch-1> <sec-branch-2>` (소문자 `-d`).
- 삭제 결과 + 각 tip 해시 보고.

## Part 2 — 원격 후보 보고 (삭제 금지)

- `git branch -r | grep -i sec` → 원격 sec-pipeline 후보 목록.
- **삭제하지 말 것.** 목록만 보고 → 사용자가 `git push origin --delete <branch>` 여부를 별도로 결정.

## Part 3 — 계약서 검증 + 정착

- **계약서 첫 실사용 후기(핵심 산출물):** 헤더 채우기·STARTUP_CHECKLIST·worktree 진입 흐름이 매끄러웠나? 막힌 지점 / 모호했던 지점 / 빠진 항목 / 개선 아이디어를 구체적으로 기록 → 계약서 다듬기 입력.
- health **8✅** 유지 재확인.
- 문서: PROGRESS에 "sec-pipeline 로컬 정리 완료 + 세션 계약서 첫 실사용" 한 줄. 필요 시 SESSION_CONTRACT에 개선 메모.
- main 무변경 확인(`e92991e` 그대로 — 브랜치 ref 삭제는 main을 움직이지 않음).

## 보고 산출물

- **계약서 첫 실사용 후기**(friction·개선점) ← 이번 세션의 진짜 목표
- STEP 0: `--merged` 교차 확인 결과 + sec-pipeline 브랜치 2개 식별
- 삭제된 로컬 브랜치 + tip 해시(복구용)
- 원격 후보 목록(사용자 결정 대기)
- health 8✅ / main `e92991e` 무변경 확인
