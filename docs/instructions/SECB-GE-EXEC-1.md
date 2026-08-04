# 지시서 SECB-GE-EXEC-1 — G-e 정의서 비준 심사 + 조건부 실행 + SEC β 종결 준비

**트랙:** SEC β (grounding 검증층)
**세션 종류:** 혼합 — Phase A(읽기 전용 심사 자료 추출) → 디렉터 비준 HALT → Phase B(G-e 실행) → Phase C(종결 준비)
**worktree:** 신규 생성, 브랜치 `monorepo/sess-secb-ge`
**작성일:** 2026-08-01 (디렉터 세션)

---

## §-1. 배달 게이트 (다른 어떤 작업보다 먼저)

1. 이 지시서 원문을 `docs/instructions/SECB-GE-EXEC-1.md`로 저장하고 **단독 커밋**한다 (명시적 파일 지정, `git add -A` 금지).
2. 커밋 해시를 보고 첫 줄에 기록한다.
3. 이후 모든 실행은 **커밋된 사본**을 기준으로 한다 (문서-증거 선행 순서 보존, 배달사고 원장 #6·#7 재발 방지).

## §0. STEP 0 — ground truth 실측 (읽기 전용, 변이 금지)

1. `git fetch` (모든 실측의 전제).
2. 셸 시작 위치를 worktree 원장과 대조 (common-bugs #3). 신규 worktree `monorepo/sess-secb-ge` 생성 후 그 안에서만 작업.
3. main HEAD / origin 동기 / 떠 있는 브랜치·worktree 전수 기록.
4. **베이스라인 재실측·재앵커** (D-SECB-BASELINE): full suite 실행 → "N GREEN / M pre-existing (사유)" 형식으로 앵커. 직전 관측치 4473/0/53 @ b5854d6d는 **이월 금지, 참고만** (common-bugs #79).
5. prod 읽기 확인 (무변경 입증용 사전 스냅샷):
   - marker `deterministic_v1` 건수 = 1751/1751
   - 등급 분포 = verified 1273 / normalized 41 / partial_match 410 / not_found 27
   - 불일치 발견 시 → **HALT** (재조사 아님, 보고 후 디렉터 판단).

## §0.5. 0번째 게이트 — G-e 정의서 존재·해시 대조

- `docs/features/chain-sight/sec_beta_ge_prompt_v2_scope.md` 존재 확인 + `git log --oneline -- <경로>`로 커밋 해시 대조.
- 부재·불일치·워킹트리 dirty 상태 → **HALT**.

## §A. Phase A — 정의서 심사 자료 추출 (읽기 전용 · LLM 호출 0)

정의서와 코드베이스를 대조해 아래 4개 심사 포인트를 **증거 인용과 함께** 보고서로 작성한다. 이 Phase에서 어떤 쓰기·LLM 호출도 금지.

| # | 심사 포인트 | 요구 증거 수준 |
|---|---|---|
| ⑴ | **신규추출 전용 확증** — 기존 1,751건 재추출·수정 경로 부재 | 코드 수준: 해당 실행 경로 grep/인용으로, 기존 레코드에 도달하는 쓰기 경로가 없음을 입증 |
| ⑵ | **표본 규모·비용** — 재추출 표본 filings 정확 건수(≤5)·건당 LLM 호출 수·비용 상한 | 정의서 명시치 인용 + 산식 |
| ⑶ | **측정 정의** — tail 발산 감소의 판정식 | v2 표본 (partial_match+not_found)율 산식, v1 기준 23.4%+1.5%와의 비교 가능성(동일 등급 판정기 사용 여부 코드 확인) |
| ⑷ | **기록 위치** — 표본 결과 저장의 격리성 | 저장 대상(테이블/파일/스키마) 명시 + prod 테이블 무접촉 확증 |

**보고서 제출 후 즉시 HALT — 디렉터 비준 대기.** 비준 없는 Phase B 착수 절대 금지 (G-e는 이 트랙 최초·유일 LLM 호출).

## §B. Phase B — G-e 실행 (병진이 디렉터 비준 결과를 전달한 후에만)

1. 정의서 **그대로** 실행. 표본 ≤5 filings, **초과 확장 절대 금지** (확장은 별도 결정 사이클).
2. 대형 실행은 foreground blocking (common-bugs #8). 부분 실패 → 즉시 HALT, 재시도·임기응변 금지.
3. 비용 상한 접근 징후 → HALT.
4. 결과 집계:
   - v2 표본 등급 분포 (verified / normalized / partial_match / not_found)
   - tail율 (partial_match+not_found) vs v1 기준 24.9% — 판정식 ⑶ 그대로 적용
5. 무변경 입증: §0-5 prod 스냅샷 재실측 → 사전/사후 동일 확인. 격리 저장소에만 기록되었음을 경로로 입증.

## §C. Phase C — SEC β 종결 선언 준비 (Phase B 게이트 통과 후)

1. **종결 선언문 초안** 작성: 트랙 전체 호(Gate 1→2→G-e) 요약 + 잔여 이관 목록 — SECB-EXPOSURE(디렉터 목업 사이클), SECB-REGRESSION-WATCH, SECB-V-B-STANDBY(미발동), CN-AUTO-REVIEW 회수(병진 별도 세션).
2. **삭제 후보 회부** (목록 보고만, 실행 금지): `sess-secb-land`·`sess-secb-g16` 브랜치·worktree — 파괴적 = 병진 수동.
3. **TH 트리거 발화 문안**: corpus unfreeze + TNV 백필(07-12→현재, 50일+) Session 1 개시 조건 명시.
4. DECISIONS diff · TASKQUEUE diff 정리 (G-e 종결 반영, SECB-PROMPT-V2 소비 완료 처리).

## §H. 위임 경계 (불변)

- plist 변경·launchctl·라이브 워커 재기동 = 병진 수동 전용. 이 세션은 해당 없음 — 발생 시 HALT.
- prod DB 쓰기 = 없음 (G-e는 격리 저장만). main 랜딩은 보고 후 디렉터 확인 하에 `git push origin HEAD:main` 원자 패턴 (common-bugs #5).
- force-push 금지 · `git add -A` 금지 · 시크릿 마스킹은 Python `len/head[:4]`만 (common-bugs #10).

## §R. 최종 보고 형식 (필수 항목)

- 지시서 커밋 해시 (§-1) / 커밋 수 (`git log --oneline | wc -l`) / push 해시 / ahead 수
- full suite "N GREEN / M pre-existing (사유)" — 세션 시작·종료 각 1회
- Phase A 심사 보고서 (4포인트 × 증거)
- Phase B 결과표 (등급 분포·tail율·prod 사전/사후 스냅샷 동일 확인)
- Phase C 산출물 3종 (선언문 초안·삭제 후보 목록·TH 트리거 문안)
- DECISIONS diff · TASKQUEUE diff

## §S. 고정 사실 (재조사 금지 — 단 §0-5 무변경 입증용 재실측은 예외)

- Gate 2 실질 완결 (개정 1: G-a 백업 · G-b 마이그 0003 · G-c 백필 1751 · G-d 제거→SECB-EXPOSURE 이관).
- 롤백 경로: marker 표적 SET NULL + 백업 덤프 `secb_pre_gate2_20260801` (44M, 무결성 검증됨) — **이번 세션에서 사용 금지**, 존재 확인만.
- R1 종결: 결과 D. "Neo4j-env" 오라벨은 D-SECB-MISLABEL로 공식 정정됨 — 재론 금지.
- SECB-EXPOSURE는 디렉터 세션 소관 — **실행 세션이 화면·API 등 선제 구축 금지** (γ규율·common-bugs #82).

## HALT 조건 총괄

배달 게이트 실패 / 0번째 게이트 실패 / prod 사전 스냅샷 불일치 / 정의서-코드 괴리(#82 패턴) / 비준 없는 Phase B 진입 압력 / 표본 부분 실패 / 비용 상한 접근 / 표본 5 초과 요구 / prod 쓰기 요구 발생 — 전부 즉시 HALT, 임기응변 금지, 디렉터 보고.
