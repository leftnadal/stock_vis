# 지시서 SECB-G15-DECOMP-0811 — Gate 1.5 not_found 분해 조사 + 거버넌스 장부 편승

- 발행: 감독 세션, 2026-08-11
- 성격: 혼합 — Part A(하네스 문서 커밋) + Part B(read-only 분해 조사)
- 선행: 1차 분해 `4d0ed3b5`(07-28, not_found 437). 본 지시서 = 배타적 우선순위 분류 v2 정련.

## 세션 계약

- 쓰기 범위: `TASKQUEUE.md` / `sub_claude_md/common-bugs.md` / 지시서 파일 / 분해 스크립트 1건(신규 `scripts/` 하위) / 분해 보고서 1건(신규 `docs/` SEC β 트랙).
  이 외 파일·기존 코드·설정·테스트 수정 금지.
- DB: 전 구간 read-only (SELECT/조회만 — INSERT/UPDATE/DELETE/DDL 금지).
- HALT-0 기본. behind>0 조우 시 D-PUSH-DELEG 공통 가드대로 무조건 HALT.

## 격리 (사전 승인)

- 브랜치 `monorepo/sess-secb-g15` + 격리 worktree 신설 승인(실측 origin/main 분기).
- 사후 정리 = D-BRANCH-DELETE-MANUAL — TASKQUEUE 등재만, CC 실행 금지.

## STEP 0 — ground truth 재실측

- 0-1. origin/main fetch → base 해시 실측(참조 9115541f 이후 전진 가능, 실측 정본).
- 0-2. status clean / health_check(참조 15/0/0 — 악화 편차만 HALT, 개선 편차는 보고 후 진행).
- 0-3. 채번 자격 판정(D-NUMBERING-MGMT-ONLY): 조사 세션 = 자격 없음 예상 → common-bugs 채번 후보로만.
- 0-4. SEC β 현재 상태 실측: Gate 2 not_found 재측정(437 = 이월 금지 참조값, 실측 정본; 편차 ±10% 초과 시 HALT). not_found 판정 로직 코드 위치·기준 grep(추측 분류 금지).
- 0-5. TASKQUEUE의 GOVCLEANUP-0810-CLEANUP·D-PUSHDELEG-PROVE 현재 문구 확인.

## Part A — 장부 커밋 2건

- [커밋 1] 지시서 등재 — `docs/instructions/SECB-G15-DECOMP-0811.md`.
- [커밋 2] 거버넌스 장부 정합:
  - (a) TASKQUEUE: GOVCLEANUP-0810-CLEANUP → done + 경위 주석; 신규 경량 "SECB-G15 사후 정리 — worktree/브랜치 병진 수동".
  - (b) common-bugs 채번 후보 1건: "-d 거부 조우 시 첫 수는 강제가 아니라 거부 원인 규명 — 어느 트리 HEAD 기준 판정인지 확인(08-10 cwd 오탐: -C 지정으로 강제 없이 해소)".
  - git add 명시 지정(-A 금지).

## Part B — not_found 분해 조사 (read-only)

- [B-1] 분해 스크립트: `scripts/` 명명 관례 준수. 입력 = Gate 2 not_found 전건. 출력 = 건별 태그 + 집계표. 결정론(재실행 동일)·DB 쓰기 0.
- [B-2] 분류 체계(우선순위 배타, 한 건 = 한 태그):
  - ① DUP-EXTRACT: 동일 (filing, 문장) 쌍 복수 추출 중복 계상분(추출 레코드 키 중복 실측).
  - ② ITEM-MISSING: 대조 원문 섹션 자체가 저장 파이프라인에 부재(해당 filing 저장 item 목록 실측).
  - ③ NORM-MISS: 원문 실존하나 정규화 차이(공백·유니코드·개행·엔티티)로 exact match 실패(소문자화·공백압축·NFKC 완화 재대조 매치 성공).
  - ④ TRUE-NONVERBATIM: 위 셋 전부 아님(LLM 패러프레이즈 추정 잔여).
  - ⑤ OTHER: 위 넷으로 설명 안 되는 건(유형 서술 필수).
  - ※ ③을 ④와 분리하는 이유: 정규화 미스는 대조기 개선으로 해소 가능 — V-B 재추출 없이 구제되므로 V-B 분모에서 구분.
- [B-3] 분해 보고서(`docs/` SEC β 트랙): 태그별 건수·비율(분모 = 실측 모수), 태그별 대표 사례 각 2건, ③ 완화 재대조 매치율, 판정·권고 없음(분류 사실만).

## 금지 사항

- Gate 2 정지 유지(게이트 재가동·파이프라인 실행 금지). 대조 로직·추출 코드 수정 금지(③ 완화 재대조는 스크립트 내 임시 비교).
- push: D-PUSH-DELEG(커밋 완료 보고 후 명시 지시 대기, behind>0 무조건 HALT). 브랜치·worktree 삭제 금지. DB 쓰기 금지. 날짜 machine clock(#89).

## 집행 결과 요지 (2026-08-11 CC 집행)

- STEP 0: base = origin/main `f27bca59`(9115541f 이후 8커밋 전진, 참조 포함). health 15/0/0(편차 0). not_found **438**(참조 437 +1, +0.23%, ±10% 이내). GOVCLEANUP worktree/브랜치 실측 제거 확인.
- Part B 결과: 438 = DUP-EXTRACT 254 + [ITEM-MISSING 0 · NORM-MISS 3 · TRUE-NONVERBATIM 181 · OTHER 0](유니크 184). V-B 실분모 = 181 유니크(98.37%). NORM-MISS 소문자 완화 구제 = 3(1.63%, 문장 첫 글자 대문자화).
