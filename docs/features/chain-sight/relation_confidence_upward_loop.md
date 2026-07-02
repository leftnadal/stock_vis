# RelationConfidence 상향 학습 루프 (upward learning loop) — 설계

> **트랙**: 본진 (Direction B moat 심장 — 궤적을 학습으로 전환).
> **상태**: **설계 문서**. 구현 후속. 실데이터 검증(D2)은 **#28 Gate 2 종결 + 자율 궤적 N틱 적립 후로 게이트**.
> **철학 확정**: B(비대칭 보수) 기본 + C(Tier-1 fast-path) 가속 레인. 채점 **B 0.7725 > C 0.685 > A 0.6225**.
> **입력**: `RelationPairSnapshot` 궤적(#28) + 신규 증거 이벤트.
> **앵커**: 하향 `apps/chain_sight/tasks/relation_tasks.py:406 check_stale_and_decay` / 모델 `apps/chain_sight/models/relation_discovery.py RelationConfidence` / 정책표 `docs/chain_sight/update_v2/RELATION_CONFIDENCE.md` / 궤적 `RelationPairSnapshot`(unique (canonical_a,canonical_b,period), upsert형).

---

## 0. 배경 & 원칙

- 현재 RelationConfidence는 **감쇠 전용(단방향)**. `check_stale_and_decay`가 무증거 시 confirmed→stale, probable→weak, weak→hidden으로 **내리기만** 함. 올리는 길이 없어 "한 번 식으면 못 데워지는" 반쪽 상태.
- 상향 학습 루프 = **올라가는 길**. #28이 매일 적립하는 궤적 + 신규 증거로 재확인된 관계를 위로 되돌림.
- **원칙(B)**: "잃긴 쉽고 되찾긴 어렵다." 하향은 빠르고 상향은 느리고 엄격 → 궤적 품질 = moat.
- **예외(C)**: 권위 있는 하드 증거(Tier-1)는 한 단계 가속. 궤적 우회가 아니라 "B 안의 가속 레인".

## 1. 상태 전이 맵

강도 사다리: `hidden < weak < probable < confirmed`. `stale` = confirmed의 cold 상태(측면).

```
[ 하향 — 기존, 빠름, 무증거 (유지·미변경) ]
   confirmed ─► stale        probable ─► weak        weak ─► hidden

[ 상향 — 신규 ]
   일반(B):        hidden ─► weak ─► probable ─► confirmed   (1단계/틱, 이중임계 + streak≥3)
   stale 회복(B):  stale ─► probable                         (confirmed 직행 금지 = 재획득)
   fast-path(C):   Tier-1 신규증거 ─► +1단계 즉시            (streak 면제 / 상향임계 충족 / 최대 1단계)
```

- **결정 1 (B 반영)**: `stale → probable` 채택. confirmed 직행은 B와 상충 → 배제.
- **결정 2 (충돌 규칙)**: 한 pair는 한 틱에 하향/상향 **배타** — 증거 있으면 하향 스킵 + 상향 평가(streak 유지), 없으면 하향 + streak 리셋.

## 2. 모델 필드 설계 (전부 신규 additive — 현재 전무)

| 필드 | 타입 | 용도 |
|---|---|---|
| `evidence_streak` | int (default 0) | 연속 재확인 틱 수. 하향/무증거 시 0 리셋. B의 streak≥3 판정. |
| `last_upgraded_at` | datetime, null | 상향 전이 witness. |
| `last_downgraded_at` | datetime, null | 하향 전이 witness. |
| `last_computed_at` | datetime, null | 궤적 점 계산 시각 — **기존 드리프트(부재) 해소**. upsert형 감사용. |
| `fastpath_triggered_at` | datetime, null | C fast-path 발동 감사(오상향 추적). |

- 임계값(`upward_threshold`/`downward_threshold`)은 **`RELATION_CONFIDENCE.md` 정책표 연동** — 코드 하드코딩 금지. 상향 임계 = 하향 임계 + margin(§4).
- 마이그레이션: 전 필드 nullable/default → 기존 행 무손상. `last_computed_at`은 백필 시 기존 스냅샷 최신 period로 초기화.

## 3. 태스크 흐름

11:30 ET 파이프라인에 상향 단계를 **하향 뒤에** 접속:

```
aggregate_relation_pairs_task (#28)      ← 궤적 적립 (11:30 ET)
        ▼
check_stale_and_decay (하향, 기존)        ← 증거 있는 pair는 제외(결정 2)
        ▼
apply_upward_learning (상향, 신규)        ← 증거 있는 pair만 평가
```

```python
def apply_upward_learning(pair, evidence_this_tick, trajectory):
    if not evidence_this_tick:
        return  # 증거 없음 → 하향 경로가 처리(streak 리셋), 여기선 no-op
    score = recompute_truth_score(pair, trajectory)          # 정책표 기반
    if is_tier1_authoritative(evidence_this_tick) and score >= UPWARD_THRESHOLD:
        upgrade_one_step(pair); pair.fastpath_triggered_at = now()   # C: streak 면제, 1단계
    else:
        pair.evidence_streak += 1
        if score >= UPWARD_THRESHOLD and pair.evidence_streak >= STREAK_MIN:
            upgrade_one_step(pair); pair.evidence_streak = 0          # B: 승급 후 리셋
    pair.last_computed_at = now()
    # upgrade_one_step: 사다리 1칸, stale→probable, confirmed 상한
```

## 4. 파라미터 초기값 (보수적, 튜닝 대상)

| 파라미터 | 초기값 | 근거 |
|---|---|---|
| `DOWNWARD_THRESHOLD` | 정책표 실측 (예 0.4) | 기존 하향 기준 유지 |
| `UPWARD_THRESHOLD` | 하향 + margin (예 0.6) | 이중 임계 = anti-whipsaw |
| `STREAK_MIN` | 3틱 (3일 연속) | B 보수. 하루살이 신호 차단 |
| fast-path 최대 | 1단계/이벤트 | C를 가속 레인으로 제한 |

→ **튜닝 게이트**: 자율 궤적 며칠 적립 후 실데이터로 재조정. 초기값은 "안전하게 느린" 쪽.

## 5. 검증 계획 (2단)

### Gate D1 — 설계 스모크 (구현 직후 가능)
- [ ] 상태 전이 함수 단위 테스트: 합성 궤적으로 상향(hidden→weak→…), stale→probable, fast-path, 충돌 규칙(증거 유무 배타) 각 경로.
- [ ] **07-01/07-02 수동점**으로 파이프라인 접속 스모크(하향→상향 순서, 예외 없이 완주).

### Gate D2 — 실데이터 검증 (게이트: #28 Gate 2 종결 + 궤적 N틱 후)
- [ ] 자율 궤적 ≥5틱 적립 후, 실제 상향 발화 관찰(정당한 재확인 pair가 규정대로 승급).
- [ ] whipsaw 없음(같은 pair가 며칠 새 오르내림 반복 안 함).
- [ ] fast-path 발동 로그 감사(오상향 없음, 되돌림도 정상 하향 경로).

## 6. 스코프

**In**: 상태 전이 맵, 모델 필드(+`last_computed_at` 드리프트 해소), 태스크 접속, 보수 기본값, D1 스모크.
**Out (별도/후속)**: 파라미터 정밀 튜닝(실데이터 후), "시간이 증명한 관계" 배지 UI(FE 별도), SEC β(예약), #28 드리프트 D1/D2·30분 갭.

## 7. 리스크 / 관찰

- **whipsaw**: B(이중 임계+streak)가 구조적 방지. streak가 안전핀.
- **fast-path 오상향**: 1단계 제한 + 상향 임계 요구 + 되돌림도 정상 하향 경로 + `fastpath_triggered_at` 감사.
- **파라미터 미성숙**: 보수 기본값 + D2 튜닝 게이트로 완충.
- **`last_computed_at` 마이그레이션**: nullable 시작 + 백필로 기존 데이터 무손상.
- **의존**: D2는 #28 Gate 2 종결(자율 틱 궤적)에 게이트 — 그 전엔 D1(설계·스모크)까지만.
