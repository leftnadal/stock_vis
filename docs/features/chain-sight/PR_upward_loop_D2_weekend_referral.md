# D2 관찰 창 주말 회부 패키지 (T-5 종결, 2026-07-12)

- 상태: 회부. 관찰 창(07-08~12) 종결. 사용자 결정 4건(§5) 대기.
- 근거: 확인 1~4 실측 + 07-09 포렌식 + 07-10 재분류(성과 #2). 관련 초안 = `PR_upward_loop_D2_T3b_draft.md`.
- flag·§6 동결·코드 전부 무변경 상태로 회부.

## §1. 창 판정 자료

### 틱별 3튜플 (07-08~12)
| 틱(KST) | period | evaluated | upgraded | fastpath | 발화 |
|---|---|---|---|---|---|
| 07-08 | 07-07 | 270 | 30 | 30 | 1 (+DB beat 2차, 당일 disable) |
| 07-09 | 07-08 | 0 | 0 | 0 | 1 |
| 07-10 | 07-09 | 270 | 30 | 30 | 1 |
| 07-11 | 07-10 | 0 | 0 | 0 | 1 |
| 07-12 | 07-11 | 270 | 30 | 30 | 1 |

- **발화 단일 경로 유지**(DB beat disable 후 07-09~12 전부 1회) — 드리프트 #7 조치 유효.
- **evaluated 격일 진동 270/0** = 선별 date-aliasing(period=UTC일자 vs __date=Seoul일자 + SEC seed 01:01 타이밍). "1일 지연"의 실체.
- **코호트 = 고정 30쌍**(외부 확산 0). 매 활성 틱 upgraded=fastpath=30, 전이 probable→probable(net-zero).

### N·M·판정
- **N(decay 하향 코호트) = 0** (07-11 decay 144건은 코호트·재시드 pair 미접촉 — 코호트 fresh). §1-3 예측 적중.
- **M(decay↔upward 진동기, C∩B) = 0** — 예상한 decay whipsaw **미발현**.
- **§4 브레이크 4조건 전부 미충족** → **창 판정 = 통과(조건부)**. 조건부 = 성과 #2(권위 충돌 flap) 잔존.

### 쓰기 증폭 (before 기준선 — T-3b 효과 측정용 보존)
- upward 270 save/틱(활성 틱, 30 유의미 + 240 no-op) / SEC seed 330 update/일 / neo4j_dirty 270 → 30 flap쌍 일일 재sync churn(net 상태 변화 0).

## §2. 성과 요약 (관찰 창 산출)
- **성과 #1**: 첫 실발화 정상(Gate D2-1 통과) + 멱등 가드 실전 검증(00:35 evaluated=0).
- **성과 #2 (핵심)**: **SEC seed↔upward 권위 규칙 충돌** 실증 — SEC seed(score<85→probable, `tasks.py:379`) ↔ fast-path(Tier-1+60→승급)가 매일 flap, net-zero churn. 타임스탬프 증거(07-09 15:31 upward → 16:01 seed 리셋). 멱등 가드 타임스탬프 관통.
- **성과 #3**: 예상한 decay↔upward whipsaw는 **미발현**(M=0) — decay bulk .update()(auto_now 우회) + decay 임계 90/60/30일 vs 재시드 pair 매일 신선. 관찰 창이 "무엇이 문제가 아닌지"도 확정.

## §3. T-3b 최종안 (①②③ⓓⓔ) — 적용 회부
- **① 선별 F() 교체 + 콜드스타트 백필**(date-aliasing 격일 진동 제거).
- **② save update_fields 전 지점**(upward auto_now 자가오염 차단; decay 현행 유지·SEC seed 정당 액터 명시).
- **③ period 로그 전용 + localdate**.
- **ⓓ 권위 충돌 해소(성과 #2 대응, 선별 수정만으론 미해결) — 후보 3(사용자 선택)**:
  | 후보 | 내용 | 장점 | 영향 범위 |
  |---|---|---|---|
  | ⓓ-1 SEC confirmed 보호 | seed update_or_create가 상향 상태(confirmed) 하향 못 하게 defaults 보호 | 최소 변경, SEC 스케줄 무변 | SEC seed 저장 로직 1곳 |
  | ⓓ-2 status 권위 일원화 | status 결정을 confidence 엔진으로, seed는 관측·score만 공급 | 근본 해소, 단일 권위 | 다지점(seed·confidence·upward) — 큼 |
  | ⓓ-3 fast-path 상태 가드 | 이미 목표 이상이면 fast-path skip | upward 국소, 안전 | upward 1곳 (ⓔ와 결합 자연) |
- **ⓔ 멱등 상태 기반화**: confirmed면 fast-path skip + fastpath_triggered_at 최초 1회만(덮어쓰기 금지).

## §4. ④ 스케줄 선택지 (1일 지연 처리)
- ④-i upward 분리(⑨-C 해체, DB beat 재도입 위험) / ④-ii seed 전진(SEC 스케줄, 타 도메인) / ④-iii 현상 유지(1일 지연 수용 — ①으로 신호 정확, 권고 기본).

## §5. 사용자 결정 4건 (회부문)
1. **창 판정**: 통과(조건부) 승인 여부 — §4 브레이크 미발동, 성과 #2 잔존.
2. **T-3b 적용 승인** — ①②③ⓔ + **ⓓ 후보 선택**(ⓓ-1/-2/-3). 적용 시 §6 동결 해제 + 관찰 재개 여부 포함.
3. **④ 선택** — i/ii/iii.
4. **정리 목록 착수 순서** — DB beat 정식 삭제+등록 주체 규명(run 3건 타임스탬프) / pair 브랜치 삭제(태그 봉인 상태) / OPS-WORKTREE-ISOLATION 착수 / SEC β 착수 시점.

## §6. 미해결 질문 (정리 목록 부속)
- **"SEC seed 재관측이 왜 정확히 270쌍(update 330)인가"** — seed 선별 기준 미규명. SEC β 착수 시 자연 해소 후보.
- DB beat `chainsight-upward-learning` 등록 주체(run 3건 07-06/07/08 타임스탬프부터 규명).
