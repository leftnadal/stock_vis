# 클로즈 선언: ⓒ OPS-WORKTREE-ISOLATION → D2 트랙 클로즈

- 선언일: 2026-07-28
- 성격: 회수·봉인·종결. 근거 지시서 `docs/instructions/ops_iso_close_recovery_directive.md`(STEP 0 판정 G).
- 범위: D2 상향학습 정리목록의 ⓒ 항목(OPS-WORKTREE-ISOLATION) 봉인 → D2 트랙 전체 클로즈. 잔여 ⓓ(SEC β)는 차기 트랙 이관.

---

## 1. 봉인 판정 (STEP 0 = G)

2026-07-28 **02:30:05 KST 라이브 첫 section D 발화** — `D(ops isolation): OK — drift/marker/codever = ok/ok/ok`, PRE/A/B/C 보존, PASS. launchd 자연 발화(수동 아님).

**전후 대조(결정적 증거)**: 07-19~27 라이브 02:30 로그엔 section D 라인이 **전무**했다(repoint 전 = verify 래퍼가 공유 세션 트리 `sess-hold-p1`의 section D 없는 구버전 py를 실행). repoint 직후 첫 자연 사이클에서만 section D가 발현 → 배치 교정이 실효했음을 라이브로 확증.

## 2. 결정 색인

### D2 상향학습(T-3b) 정본 — 상세 = DECISIONS "T-3b"(2026-07-13), `PR_upward_loop_D2*.md`
- **① 선별 F() 교체 + 콜드스타트 백필**: `last_computed_at isnull | last_observed_at > F(last_computed_at)`. 구 `last_observed_at__date=period` date-aliasing 격일 진동(270/0) 제거. 마이그 0016(NULL 13,427→0).
- **② save `update_fields`(auto_now 제외)**: upward `pair.save()`가 `last_observed_at`(RC 유일 auto_now)을 자가오염 → update_fields로 선별 신호 보존. ①과 필수 동반.
- **③ period 로그 전용 + `localdate`**: UTC/Seoul tz 불일치 교정.
- **ⓔ 멱등 상태화**: confirmed면 fast-path·save skip, `fastpath_triggered_at` 최초 1회, `last_upgraded_at` 실 전이 시만.
- **ⓓ-2 status 권위 도메인 분할**: 비-market 상향=upward 엔진(`HIGHSCORE_THRESHOLD=85` 단일출처), 하향=decay 전담. SEC seed는 관측·score만 공급(기존 pair status 무기록). ⓓ-1(단조 가드)·ⓓ-3(상태 가드) 미채택.
- 포렌식 3중 결함 = ⓐ 타이밍(seed 01:00 KST가 upward 00:30 뒤) · ⓑ auto_now 자가오염 · ⓒ tz 불일치.

### OPS-WORKTREE-ISOLATION(격리 3층) — 상세 = DECISIONS "OPS-WORKTREE-ISOLATION 클로즈"(2026-07-28)
- **Phase 1 세션 마커**(`1f2bf5f`): respect verdict(신선→skip/stale≥24h→heal/부재→proceed), 런타임 트리 R1 예외, wt-open/close 수명주기(3차 대책=미커밋 WIP 프롬프트).
- **Phase 2 공유트리 git hook**(존치·트리거 대기): 원 차단 대상 `sess-mon-timing-p25` 트리 소멸로 OBE. 방어종심 존치, 재트리거=공유 dirty 트리 재출현 시 재스코프.
- **Phase 3 verify 무인 파수꾼 section D**(`b76d9ab`): 조상기반 drift(계보밖 diverged만 warn=07-04 hijack 시그니처)·stale 마커(≥24h)·코드버전(HEAD 커밋 > 워커 기동). WARN 상한(FAIL 없음)·try/except 격벽·미확인 skip.
- **repoint(OPS-VERIFY-EXEC-TREE)**: 래퍼 `PROJECT_DIR` self-locate(`BASH_SOURCE`) 채택 — plist-only 불가(공유트리 하드코딩+cd). §1=α(sv-worker-runtime). 야간 번들→주간 집행(게이트 충족). origin/main `b9ddf41a`.

## 3. 드리프트 사건 재해석 (통산 — "됐다고 믿은 것 vs 런타임")

D2 트랙이 반복 노출시킨 축 = **"소스에 있음"과 "런타임이 그것을 돎"의 괴리**.

| # | 사건 | "됐다고 믿은 것" | 실제 런타임 |
|---|------|-----------------|-------------|
| 07-04 | 트리 탈취(hijack) | 워커트리가 main 정합 | 수동 체크아웃으로 계보밖 diverged |
| #4 | upward beat 11:35 드리프트 | beat 배선됨 | config dict beat = DatabaseScheduler 무시(#28) → 미배선 |
| #7 | 이중경로(⑨-C) | 단일 태스크 체인 | 인라인/별도 이중경로 잠복 |
| flap | SEC seed net-zero | 상향 확정 유지 | 01:00 seed가 30분 뒤 probable 리셋(격일 churn) |
| **verify 배치 drift(본 트랙 최신)** | **section D가 origin/main 배선됨=라이브 발현** | **verify 래퍼가 공유 세션 트리 브랜치의 구버전 py 실행 → 라이브 section D 전무** |

교훈 항구화 = common-bugs **#67**(라이브 자동화는 origin/main 추적 트리만 참조; "무접촉" 주장은 읽기/쓰기 구분).

## 4. 성과 요약

- **쓰기 증폭 ~97% 감소**: 구 upward 270 save/일(30 유의미 + 240 no-op) → T-3b 후 ~7 save/일(skip 263 무저장). PROGRESS "T-3b 검증"(07-17) 실측.
- **flap 완치**: SEC seed 330 updated/일 통과해도 confirmed 하향 **0**(3일치), net-zero confirmed **2326 완전 고정**(진동 0). status 권위 도메인 분할(ⓓ-2)로 flap 불성립.
- **격리 3층 방어선 봉인**: 마커(예방)·hook(차단, 존치)·verify 파수꾼(탐지, 봉인) — 동시성 사고 3계열(트리 탈취/워커 리셋/미커밋 WIP)에 대응. §3-2 인위 발화로 파수꾼 실전 탐지력 실증(marker warn→원복→ok).

## 5. 잔여 질문 → SEC β 이관

- **seed status 무기록 승계**: ⓓ-2로 SEC seed의 status 권위는 제거했으나, seed가 공급하는 관측·score와 엔진 status의 장기 정합(재관측 시 **270 save / 330 seed** 규모의 상호작용)은 β 트랙 관측 대상.
- **ⓓ 권위 충돌의 구조적 해소**: ⓓ-1/ⓓ-3 미채택분(seed 단조 가드·상태 가드)의 필요성 재평가.
- **이관처 = ⓓ SEC β**: `docs/features/chain-sight/PR_sec_beta_grounding.md`(기커밋 `9df14f6`). §0 잠금 해제, chain_sight 접촉 시 동결 우선. **착수는 별도 세션**(본 클로즈는 이관만).

## 6. 클로즈 선언

**ⓒ OPS-WORKTREE-ISOLATION 봉인 완료 → D2 트랙 클로즈.** 잔여 정리(DB beat #7 삭제·pair 브랜치·본 세션 브랜치 삭제·plist 백업)는 파괴적 작업 클래스로 **병진 수동 결정에 유보**(삭제 후보 보고만). 차기 트랙 = ⓓ SEC β 착수(별도 세션).
