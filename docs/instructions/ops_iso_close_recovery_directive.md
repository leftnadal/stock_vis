# 지시서: Phase 3 봉인 판정 → OPS-ISO-CLOSE → D2 트랙 클로즈 (회수·종결 세션)

- 발행: 감독 세션, 2026-07-27
- 소비 조건: **본 파일이 `docs/instructions/`에 커밋되어 있을 것**
- 성격: 회수·봉인·종결 세션. **STEP 0 판정이 GREEN일 때만 §1 이후 진행** — 판정 분기가 이 지시서의 심장이다.
- 전제 사실 (재조사 금지): repoint 07-27 11:48~11:51 집행 완료(실패 0), 실효 경로 sv-worker-runtime, 수동 발화 section D = ok/ok/ok, 07-19~27 라이브 로그에 section D 전무(전후 대조 증거), plist 백업 = pre_repoint_backup, 수동 로그 = verify_repoint_manual_20260727_1151.log.

---

## STEP 0 — 07-28 02:30 KST 라이브 로그 실측 → 봉인 판정 (읽기 전용)

verify-pair 라이브 로그에서 07-28 02:30 사이클을 실측하고 아래 셋 중 하나로 판정한다.

- **판정 G (봉인)**: section D 3항목(drift/marker/codever) 발현 1회 + 전부 ok + PRE/A/B/C 보존 → §1로 진행.
- **판정 W (오탐)**: section D 발현했으나 1개 이상 비-ok인데 실상은 정상(오탐) → **즉시 경고 강등**(차단 아님) 기록 + 감독 회부. §1 진행 금지. (실상이 진짜 이상이면 오탐이 아니라 파수꾼의 첫 실전 적발 — 그 경우도 회부하되 "적발"로 구분 보고.)
- **판정 N (미발현)**: 02:30 사이클 자체 부재 또는 section D 라인 없음 → HALT, launchctl 로드 상태·실효 경로 재실측 첨부하여 회부.

## §1 — Phase 3 봉인 기록 (판정 G 전용)

- PROGRESS.md에 Phase 3 봉인: 라이브 첫 발현 시각·3항목 판정·수동 발화와의 전후 대조 근거 1행.
- OPS-WORKTREE-ISOLATION 상태 = Phase 1 가동 / Phase 2 트리거 대기(TASKQUEUE 존치 확인) / Phase 3 봉인.

## §2 — §3-2 인위 발화 테스트 (봉인 후에만)

- 임시 stale 마커(또는 3항목 중 인위 조건 구성이 가장 안전한 1개)를 만들고 verify 수동 1회 발화 → **해당 항목이 비-ok로 우는 것** 확인 → 원복 → **같은 shell 재조회**로 원복 확증 → 재발화 1회로 ok 복귀 확인.
- 이 테스트의 로그는 라이브 로그와 구분되도록 수동 로그 파일로 저장. 실패(안 울림/원복 미확증) 시 HALT 회부.

## §3 — 정밀 IDENTICAL 비교

- 구 라이브 로그(07-19~27 임의 1개) vs 신 라이브 로그(07-28 02:30): PRE/A/B/C 섹션의 **형식·항목 집합 동일**(검사 대상 데이터 차이 제외) 입증. section D 추가분 제외 diff = 0 계열.
- 비교 스크립트를 쓰면 scratchpad 금지 — 커밋 (common-bugs #1).

## §4 — 문서 main 편입 + 브랜치 처리

- sess-verify-repoint(7c1acfd4)의 개정문2 + 야간 명령서를 main에 편입. 방식: 본 세션 worktree에서 해당 커밋 반영 후 아톰 `git push origin HEAD:main`. 명시 pathspec 규율 유지.
- **브랜치 삭제는 하지 않는다** — 원격 브랜치 삭제는 파괴적 작업 클래스. "삭제 후보: monorepo/sess-verify-repoint (내용 main 편입 완료)"로 보고만 하고 병진 수동 결정에 유보.
- plist 백업 파일(pre_repoint_backup)도 동일: 존치, 삭제 후보 보고만.

## §5 — §5-2 일괄 정리

- DECISIONS.md: 이 트랙의 결정 색인 정리(래퍼 self-locate 채택, §1=α, 야간→주간 집행 변경과 게이트 충족 근거 포함).
- 임시규칙 일괄 폐지: D2/OPS-ISO 트랙에서 세운 한시 규칙을 전수 나열 → 폐지 대상/영구 승격 대상 구분. **영구 승격 확정 2건**: ⑴ "지시서는 repo 커밋이 0번째 게이트" ⑵ "라이브 자동화 배치는 origin/main 추적 트리만 참조" (common-bugs 기등록 여부 확인, 없으면 등록).
- PROGRESS 봉인 + TASKQUEUE 정리: 완료 항목 제거, 존치 확인 = Phase 2 트리거 대기 · §H hardening(c) 트리거 대기.

## §6 — 클로즈 선언 (T3b_hold_resume_close_directive.md §C 양식)

- **ⓒ 종결 → OPS-ISO-CLOSE → D2 트랙 클로즈** 선언문 작성·커밋. 포함: 결정 색인(①~⑪·ⓓ-2 + 본 트랙 결정), 드리프트 사건 재해석(통산 목록에 verify 배치 drift 추가 — "됐다고 믿은 것 vs 런타임" 계열 최신 사례), 성과 요약(쓰기 증폭 97%·flap 완치·격리 3층 방어선), 잔여 질문의 SEC β 이관(재관측 270/330쌍 질문 포함).
- 클로즈 선언문에 **차기 트랙 포인터**: ⓓ SEC β 착수(PR_sec_beta_grounding.md, 기커밋 9df14f6) — 착수 자체는 별도 세션.

## HALT 조건

판정 W/N / §2 발화 실패·원복 미확증 / §3 IDENTICAL 실패 / §4 편입 중 충돌 / 범위 밖 접촉 — 전부 즉시 정지·회부. 파괴적 작업(브랜치·백업 삭제) 실행 금지, 후보 보고만.

## 보고 양식

- STEP 0 판정 1행(G/W/N + 근거 로그 인용) · §1~§6 각 상태 1행
- 커밋 수·해시 · N GREEN / M 사전존재(사유) · 삭제 후보 목록 · TASKQUEUE diff · DECISIONS diff
