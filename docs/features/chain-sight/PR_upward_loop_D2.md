# PR: 상향 학습 루프 D2 — v5.1 FINAL (통합 선행)

- 문서 상태: **v5.1 FINAL — v4 전면 대체.** 사용자 결정 ⑩(pair→main 통합 선행) + ⑪(period 07-05 갭 허용) + 블로커 봉인 확정 (2026-07-06).
- 승계(v4): ⑨-C(코드 내 체인 트리거)·§2 구현 범위·§4 규칙 문언·§5 채집 방식.
- 개정(v5): 의존 체인·잠금① 정의·실행 순서(통합을 D2 관찰 앞으로).
- 실행 단위 = T-1 → T-5 순차. 각 단계 게이트는 문서가 아니라 **실측 데이터**.

---

## §1. 결정 기록 및 봉인

### 결정 ⑩ — 의존 체인 역전 (pair→main 통합을 D2 관찰 앞으로)
- 구(v4): D2 실행 → 관찰 → whipsaw → 통합 → SEC β
- 신(v5): **통합(T-1)** → 잠금① 충족(T-2) → D2 구현 PR(T-3) → flag-on(T-4) → 관찰(T-5) → whipsaw·튜닝 회부 → SEC β
- 근거: ⑴ 원 순서 근거("D2 관찰로 pair 검증 후 편입")는 D2가 무코드 flag-on이던 시절 논리 — v4에서 별도 구현 PR로 전환되며 소멸. ⑵ 통합 대상 전부 검증·봉인 완료(Gate 2 종결 16d38b2, 감사 봉인 c690307 무오염, 역방향 동기화 무충돌 9ce1698, D1 flag-off+4-path GREEN+가산 마이그 13,697행 무손실). ⑶ 통합은 구조 블로커를 예외 없이 **존재 자체로 소멸**(nightly가 main 리셋해도 main에 태스크 존재 → 충돌 불성립).

### 결정 ⑪ — 잠금① 갭 허용
- period 07-05 영구 결번(날짜 키 틱, 미소급). 잠금① = **"07-01~04 4틱 + 통합 후 첫 신규 틱 = 5틱째"**.
- 근거: 잠금①의 목적은 파이프라인 안정성 증거. 갭 원인은 파이프라인 결함이 아니라 외부 사고(worktree 리셋 재발)로 규명·봉인. 07-05는 일요일(비거래일)이라 상향 원료 손실 없음. 거래일 3틱 판정은 관찰 창에서 별도 충족.

### 구조 블로커 봉인 (07-06)
> 07-04 작업트리 탈취 사고의 재발 2차. nightly 자동화가 `~/worktrees/sv-worker-runtime`을 origin/main(aggregate_def=0)으로 리셋 — 기본 워커가 여기서 실행되어 pair 전용 aggregate 태스크가 매 틱 unregistered, period 07-01~04 이후 미적립(07-05 영구 갭), verify FAIL(07-06 02:30). 임시 규칙("git 상태 변경은 pair 트랙 세션만")은 세션만 구속하고 자동화는 못 막음. OPS-WORKTREE-ISOLATION 트리거를 "통합 후"로 잡은 범위 오판이 遠因. 해소 = 결정 ⑩(통합 선행). 재발 방지 = OPS-WORKTREE-ISOLATION 대기열 선두 승격(§7).

### 드리프트 #5 봉인 (⑨-A 폐기)
> ⑨-A("인라인, beat 1개, aggregate→decay→upward 한 태스크 체인")는 "upward beat 11:35" 드리프트(#4) 정정 중 발생한 과교정. 실태 = 3개 독립 태스크 + upward 미배선(config dict beat는 DatabaseScheduler 무시, #28 패턴) + 골격 본문. 프리플라이트 규율이 flag-on 전 차단(관찰 창 낭비 방지).

---

## §2. T-1 — pair→main 통합 (본 세션 유일의 main 쓰기)

### 2-a. 프리플라이트 (읽기 전용, 불일치 시 중단·보고)
| # | 항목 | 기대 |
|---|---|---|
| A-1 | pair 최신 커밋에 Gate 2 종결·D1·aggregate 태스크 포함 | 일치 |
| A-2 | origin/main 최신 (fetch 후 실측) | 기록 |
| A-3 | 9ce1698 이후 main 신규 커밋 수 | 기록 |
| A-4 | 작업트리 clean, beat/워커 PID 기록 | 기록 |
| A-5 | verify 최신 = FAIL(07-06 02:30)이 구조 블로커 원인 재확인 (신규 원인이면 중단) | 일치 |

### 2-b. merge (P-0 규율 전면 적용)
- pair → main. **산출물 필수: merge 커밋 해시 + 충돌 목록 + rerere 기록.**
- **chain_sight 수치 영역 충돌 임의 해결 금지** — 발견 즉시 중단·보고.
- 기전(main이 sess-main-integrate에 체크아웃): origin/main→pair catch-up merge(충돌 해결은 pair) → main을 pair로 FF → origin/main push.
- merge 후 기존 테스트 GREEN 확인.

### 2-c. 워커 정합 (07-04 교훈)
- sv-worker-runtime을 push된 origin/main으로 갱신 — **nightly 리셋 방향과 수렴하므로 임시 규칙 위반 아님(본 문서로 예외 승인)**.
- 워커·beat 재기동, PID 기록. **inspect로 aggregate 등록 확인 = "unregistered" 소멸이 T-1 종결 조건.** upward(골격) 등록도 기록.
- 07-07 00:30 KST 틱 전 완료.

## §3. T-2 — 잠금① 충족 (관찰, 무작업)
- 통합 후 첫 자율 틱(07-07 00:30 KST 예상) 신규 period 1개 + 기존 4 = 5틱째(⑪). period 총 5개 각 9,562행.
- 게이트 = period 날짜가 아니라 **"통합 후 신규 period 적립 여부"** — 키 값은 실측 기록만.
- 07-07 02:30 verify PASS 필요. FAIL → §9.
- T-3은 T-2 대기 없이 착수 가능(flag False 불활성). **T-4는 T-2·T-3 양자 완료 전제.**

## §4. T-3 — D2 구현 PR (v4 §2 승계, main 기준 새 브랜치)
- **2-a 트리거**: aggregate 말미 flag 가드 `.delay(period=...)`, 실패 try/except 흡수(aggregate 무영향), ⑨-C 주석, DECISIONS 1줄.
- **2-b 본문**: D1 서비스 배선(THRESHOLD=60, STREAK_MIN=3, stale→probable, Tier-1 fast-path + `fastpath_triggered_at`), 로그 `task_id/period/evaluated/upgraded/fastpath/소요`, **upgraded=0=INFO(정상)**, 동일 period 멱등.
- **2-c 격벽**: 예외 태스크 경계 종결, 자동 재시도 없음, flag False 시 skip 로그 1줄.
- **2-d 테스트 4종** + D1 4-path GREEN 유지.
- **2-e 비변경**: decay(토 4am 주간) 불변, register 불변, 파라미터 불변. `config/celery.py:736` 죽은 config dict beat 제거(라인 실측 후).

## §5. T-4 — flag-on
1. T-2(5틱+verify PASS)·T-3(merge+GREEN) 실측 확인
2. `CHAINSIGHT_UPWARD_LEARNING_ENABLED = True` 1건
3. 워커·beat 재기동, PID·코드 정합 실측
4. 자율 틱 대기 — **쉘/수동 `.delay()` 금지. aggregate 말미 flag 가드 트리거가 정상 경로.** 첫 발화는 자율 틱 산출만 인정.

## §6. T-5 — 관찰 창 (거래일 3틱)
- 채집 = upward 태스크 로그 단독, `task_id` 단위 3튜플(evaluated/upgraded/fastpath)+소요.
- 이분법: 트리거 로그 있음+upgraded=0 = **정상**(STREAK≥3) / 트리거 로그 없음 = 고장.
- **동결(pair 소멸 반영)**: 관찰 창 동안 **main의 chain_sight 영역 merge/rebase 금지.** nightly 발견은 fix/ 브랜치 적재만, Gate D2-2 후 처리.
- whipsaw 30% 브레이크 → flag-off + 회부.

## §7. 후속 (T-1 완료 즉시)
- **OPS-WORKTREE-ISOLATION**: 트리거 충족 → 대기열 선두 승격. 근거에 본 봉인(재발 2차) 추가. 착수는 관찰 창과 안 겹치게 사용자 호출.
- **SEC β**: §0 잠금(통합 완료) 해제. 착수 별도 호출(PR_sec_beta_grounding.md, V-A). chain_sight 접촉 시 동결 우선.
- **pair 브랜치 정리**: 통합 확인 후 태그 봉인→삭제. 2브랜치 규율 복원.
- **임시 규칙 폐지**: "git 상태 변경은 pair 트랙 세션만" — pair 소멸로 실효, PROGRESS 기록.

## §8. 의존 체인 (v5 확정)
T-1 통합(07-06) → T-2 잠금① 5틱(07-07 틱+verify) → T-3 구현(T-1 후 병행) → T-4 flag-on → T-5 관찰(거래일 3틱, ~07-10) → whipsaw·튜닝 회부 → [병렬: SEC β / OPS-WORKTREE-ISOLATION — 각 사용자 호출]

## §9. 이상 경로
- §2-a 불일치 / merge 수치 영역 충돌 / 테스트 RED → 중단·보고, main 무접촉 유지.
- T-1 후 07-07 틱에서도 미적립·verify FAIL → **구조 블로커 외 신규 원인** — flag-on 금지, 원인 판정, 회부.
- 관찰 창 중 워커/worktree 이상(3차) → 즉시 보고, OPS-WORKTREE-ISOLATION 긴급 승격 회부.
