# 지시서 SECB-V2-ROLLOUT-1 (CC 전달용)

**트랙**: SEC β 2차 롤아웃 (v2 프롬프트 전량 적용)
**결정 근거**: D-SECB-V2-LEN = C(캡 제거·sanity 경고선 2,000자·로그만·절단 금지) · D-SECB-V2-COEXIST = B(v1 보존·소비측 v2 필터) · 비용 go(≤$3.3·351콜·100건 체크포인트) · V-B STANDBY 유지(트리거: 롤아웃 후 nf율 >15%).
**worktree**: `sv-secb-v2-recon` 재사용. SUNMON worktree 무접촉.
**작성일**: 2026-08-10

---

## §-1. 착지 커밋 (0번째 게이트)

커밋 1건 — ① `docs/features/secb/secb_v2_recon_report.md`(정찰 전문) ② `DECISIONS.md`(D-SECB-V2-LEN·D-SECB-V2-COEXIST + ⑴⑷ 기록) ③ `TASKQUEUE.md`(전제 종결→실행 중 전이) ④ 이 지시서. 커밋 후 push 채비 상신(원자 스크립트) → 병진 push → 착지 확인 후 §0 진입. **미착지 상태로 §0 진입 금지**.

## §0. 실측 — 소비 경로 전수 (B의 절대 조건)

1. 판정 테이블(`SupplyChainEvidence`)을 읽는 **모든 소비 지점 grep** — 구문 변형 전수(모델명 직접 참조·related manager·raw SQL·serializer·tasks의 `[:100]`/`[:200]` 절단 지점 포함). "filter 전수는 broad grep" 교훈.
2. 각 지점별 "prompt_version 무구분 시 v1+v2 이중 집계 발생?" 판정표.
3. `rematch .delete()` 경로 실측 — v2 병존 후 rematch가 v1·v2 무차별 삭제하는지. 하면 필터 필요 지점에 추가.
4. **HALT 조건**: 소비 지점이 grep으로 확정 불가한 동적 경로 발견 시 상신.

## §1. 구현

1. 프롬프트 v2: 300자 캡 지시 제거(`prompts.py:23,66`) → "인용은 원문 verbatim·완결 단위". `prompt_version='v2'` 기록.
2. 소비측 필터: §0 판정표의 이중 집계 지점 전부에 **supersession 필터** `.current()`(D-SECB-V2-CURRENT, (가)→(나): filing에 v2 있으면 v2·없으면 v1). v1 무접촉 보존. naive `filter(v2)`는 v1-only 과잉배제로 폐기(테스트 13건·창 회귀 실증).
3. 저장측 sanity: `evidence_text > 2,000자` 시 **경고 로그만**(절단·거부 금지).
4. grounding 검증(verbatim 대조)은 v1 로직 재사용 — 캡 제거로 원문 매칭이 쉬워지는 방향임을 테스트로 확인.

## §2. 검증 게이트 (suite)

신규 테스트(v2 필터 정합·v1 보존·sanity 경고 경로) + 기존 suite GREEN("전체 N GREEN / M 사전존재" 형식) + 표본 filing 1건 dry-run으로 v2 인용의 원문 대조 실증.

## §3. 본실행 (prod write — 병진 승인 게이트 2단)

CC가 실행 스크립트 준비: **1단 = 100건 체크포인트** 배치 → 자동 정지 → nf율·인용 길이 분포(p50/p90/max)·grounding 정합률·v1 무접촉 확인 상신 → 병진 승인 후 **2단 = 잔여 251건**. 표준 페이싱(v1 rate 재사용).
**HALT 조건**: 체크포인트에서 nf율이 v1 잔여(2.03%) 대비 유의 악화 또는 grounding 정합 이상 → 2단 진입 금지·상신. 실행은 병진 별도 터미널(#88 스크립트화).

## §4. 종결 실측

전량 완료 후 — v2 행수·filing 커버리지(351/351)·nf율 재측정·V-B STANDBY 트리거 판정(>15%?)·v1 1751행 무접촉 대조(#79: 전부 재실측) → 종결 보고 + 정리 목록(worktree·스크립트) 상신.
