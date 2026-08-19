# 지시서 MGMT-LEDGER-1 — 장부 일괄 정산 + G-sunmon 실측

- 발행: 감독 세션, 2026-08-19
- 트랙: ops/mgmt 장부 정산 + TH-SUNMON-REEXTRACT-1 종결 게이트
- 세션: mgmt docs-only(채번 자격 有) / worktree `~/worktrees/sv-mgmt-ledger1` · 브랜치 `monorepo/sess-mgmt-ledger1`(origin/main `24043cd4` 기점)

## 쓰기 허용 4파일
`docs/instructions/MGMT-LEDGER-1.md` · `DECISIONS.md` · `TASKQUEUE.md` · `sub_claude_md/common-bugs.md`. 이외·코드·마이그레이션 금지. DB read-only. FMP 0회. push=D-PUSH-DELEG. behind>0 흡수=D-GOBS-REBASE-STANDING(docs-only 역머지, 자동 머지 한정·예상 밖 충돌 HALT).

## STEP 0 실측 결과 (2026-08-19 10:50 KST, base 24043cd4)
- health 15/0/0. **G-sunmon GREEN**: corpus 08-16(일) published_at 1,616·08-17(월) 1,610(양일>0) + TNV_CHAIN 라인 존재(celery-worker-error.log date=2026-08-06 written=4·sv-worker-runtime/stocks.log date=2026-08-07 written=3).
- DIFF521 미반영(TASKQUEUE 여전히 "판정 대기") → A-4 발동. 채번 후보 실측 20건. common-bugs 최대 #96 → 신규 #97+. health WARN 유형 판정② = common-bugs 미등재(gap, 보고).

## 반영 항목 (커밋 2, 문안 디렉터 확정본·번호/형식만 관례화)
- **A TASKQUEUE**: A-1 DSS-RECON-1/IMPL-1-CLEANUP → done(08-18 병진 수동, -D 통산 0). A-2 DSS-FLAT-OBS 등재(08-21 7회차 flat 중계 게이트). A-3 G-sunmon GREEN → TH-SUNMON-REEXTRACT-1 종결(실측 수치 동반). A-4 DIFF521 확정 반영(V2 스코프 356=351+NULL 5·쿼리 갱신 위임).
- **B DECISIONS**: B-1 D-DSS-EPSILON 보류. B-2 D-DSS-TAU 보류. B-3 rebase 흡수 부칙 신규 채번(D-PUSH-DELEG 하위).
- **C common-bugs**: C-1 신규 채번(-d 근본원인·HEAD:main 직행 upstream 부재). C-2 잔여 채번 후보 20건 실번호 일괄 부여(#97+, 원문 유지).

## HALT 트리거
health FAIL / 4파일 밖 변경 / 역머지 예상 밖 충돌 / 0-3 grep 모순(단순 기반영 skip 제외) / 예상 밖.
