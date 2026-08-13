# 지시서 SECB-VB-ABSORB-0811 — V-B → V2 롤아웃 흡수 확정 + G1.5 트랙 종결 장부

- 발행: 감독 세션, 2026-08-11
- 성격: 혼합 — Part A(read-only 교집합 실측) + Part B(하네스 문서 커밋)
- 선행: SECB-G15-DECOMP-0811(438 분해·181 확정)·SECB-G15-COVERAGE(입력 item 1+7 실측).

## 세션 계약

- 쓰기 범위: `DECISIONS.md` / `TASKQUEUE.md` / `sub_claude_md/common-bugs.md` / `docs/features/chain-sight/` 실측 부록 1건(신규) / 지시서 파일. 그 외·코드·설정·테스트·프롬프트 수정 금지(소문자 완화 포함 — 등재만, 구현은 V2 실행 세션 관할).
- DB: 전 구간 read-only. HALT-0 기본. behind>0 조우 시 D-PUSH-DELEG 무조건 HALT.

## 격리 (사전 승인)

- 브랜치 `monorepo/sess-vbabsorb` + 격리 worktree(실측 origin/main 분기). 사후 정리 = D-BRANCH-DELETE-MANUAL(TASKQUEUE 등재만, CC 실행 금지).

## STEP 0 — ground truth 재실측

- 0-1. origin/main fetch → base 실측(참조 c7020c96 이후 전진 가능). 0-2. status clean / health(참조 15/0/0, 악화만 HALT). 0-3. 채번 자격(D-NUMBERING-MGMT-ONLY — 자격 없으면 후보). 0-4. 실측 대상: ④ 181 식별자 추출(재실행 시 ≠181이면 HALT)·V2 대상 351 정의 소스 grep. 0-5. TASKQUEUE(SECB-G15-CLEANUP·D-PUSHDELEG-PROVE·SECB-V2-ROLLOUT).

## Part A — 교집합 실측 (read-only)

- A-1. ④ 181 소속 filing 집합 F_nb(유니크 filing 수). A-2. F_v2(351)와 ∩/− (filing·evidence 이중 집계, 미포함 목록 전건). A-3. `docs/features/chain-sight/` 부록 저장(판정 없이 집계·목록만).

## Part B — 장부 종결 커밋

- [커밋 1] 지시서 등재 `docs/instructions/SECB-VB-ABSORB-0811.md`.
- [커밋 2] 본체:
  - (a) DECISIONS D-SECB-VB-ABSORB: G1.5 재판정 완주 요지 + COVERAGE 실측 → **V-B 전용 파이프라인 불개설, 181은 V2 흡수**. 가중합 A 3.60 / **B 4.25** / C 2.90(마진 0.65, 병진 승인 2026-08-11). C 회귀 예약(V2 100건 체크포인트 nf율 개선 실패 시). Gate 2 정지 현행.
  - (b) TASKQUEUE: V2 체크포인트 기준 추가·SECB-V2-NORMFIX(소문자 완화, 편승)·SECB-DUP-EXTRACT(중복 추출 트랙, V2 이후)·(차집합≠0 시)미포함분 대상 추가 판정 대기·SECB-G15-CLEANUP 확장(원격 브랜치+sv-vbabsorb)·D-PUSHDELEG-PROVE 3차 실증.
  - (c) common-bugs 채번 후보 2건.
  - git add 명시 지정(-A 금지).

## 금지 사항

- V2 파이프라인 실행·재추출 발화 금지(흡수 집행 = V2 세션 관할). 코드 수정 금지(소문자 완화 등재만). push = D-PUSH-DELEG(명시 지시 대기, behind>0 HALT, 원장 hot 파일 교집합 시 전진분·교집합 보고 후 흡수 승인 대기). 브랜치·worktree 삭제 금지. DB 쓰기 금지. machine clock(#89).

## 집행 결과 요지 (2026-08-11 CC 집행)

- STEP 0: base = origin/main `7a0ef653`(c7020c96 이후 SECB-V2-ROLLOUT §1+§2 1커밋 전진). health 14✅/1WARN(#47 실행트리-origin/main 뒤처짐 신호·비악화)/0. 181 재확인 ✅(v1 필터).
- Part A: F_nb 128 filing / 181 evidence. F_v2 = deterministic_v1 351. ∩ = **127 filing / 180 evidence**(99.4% 자연 흡수). 차집합 = **1 filing [521]**(PAYX, 미접지 straggler). 부록 `sec_beta_vb_absorb_intersection.md`.
