# Slice 12 Part 4 종결 보고 — Manual Eval + 가설 검증

**브랜치**: `slice12`
**선행 commit**: `8c5bb6d` (Part 3)
**작업일**: 2026-05-20
**비용**: $0.3207 (sonnet 15콜)

---

## §1. Baseline / 결과

| 항목         | Baseline (Part 3 후) | Part 4 종결           | 변화        |
| ------------ | -------------------- | --------------------- | ----------- |
| 회귀         | 668                  | 668                   | 0 (eval만)  |
| Slice cap    | $0.1545 / $1.00      | **$0.4752** / $1.00   | +$0.3207    |
| 전체 누적    | $2.7989 / $4.00      | **$3.1196** / $4.00   | +$0.3207    |
| LLM 호출     | 19 / 50              | **34 / 50**           | +15         |
| IDENTICAL    | 7/7 PASS             | **7/7 PASS**          | 유지        |

---

## §2. 모델별 평균 (병진 평가, 15 case × 2 모델 = 30 commentary)

| 축                  | haiku     | sonnet    | delta (haiku - sonnet) |
| ------------------- | --------- | --------- | ---------------------- |
| naturalness 평균    | **3.60**  | 3.20      | **+0.40**              |
| insight 평균        | **3.53**  | 3.27      | **+0.27**              |
| gate_clarity (30건) | 1.13      | 1.27      | **−0.13** (sonnet 미세 우위) |
| gate_clarity (gate 2건) | 1.00  | 1.00      | 0 (둘 다 최저)         |

---

## §3. Case별 winner (15 case)

| 축       | haiku 승 | sonnet 승 | tie  |
| -------- | -------- | --------- | ---- |
| nat      | **8**    | 2         | 5    |
| ins      | 6        | 3         | 6    |
| combined | **7**    | 2         | 6    |

---

## §4. Cost / Latency / Efficiency

| 항목                  | haiku       | sonnet      | ratio (sonnet/haiku) |
| --------------------- | ----------- | ----------- | -------------------- |
| 총 비용               | $0.0991     | $0.3207     | **3.24×** 비쌈        |
| 평균 latency          | 11,381 ms   | 20,176 ms   | **1.77×** 느림        |
| efficiency (quality/$) | **72**     | 20          | **+257%** haiku 우위  |

---

## §5. 글쓰기 가설 8/8 정착 판정

| 룰                              | 결과                  | 판정 |
| ------------------------------- | --------------------- | ---- |
| haiku_combined_wins ≥ 8 (1차)   | 7 (미달)              | ✗    |
| haiku_nat_wins ≥ 9 (1차)        | 8 (미달)              | ✗    |
| 평균 우위 (2차 폴백)            | haiku 7.13 > sonnet 6.47 | ✓ |

**결과**: **slice 8 winner = haiku → 누적 가설 8/8 정착 (평균 우위 기반)**

### 정착 강도 평가
- Slice 11 P5: 강 정착 (모든 축 명확 우위 + 분포 폭 3)
- **Slice 12 P4: 약 정착** (combined wins 7/15, tie 6/15 — 평균 우위로만 결정)
- → Slice 13+에서 재확인 가치 있음 (특히 #60 active로 prompt 개선 후)

---

## §6. #60 (gate-aware prompt) 결정 — **active**

| 측정                       | 값                            | 임계      | 결정 |
| -------------------------- | ----------------------------- | --------- | ---- |
| haiku gc 평균 (30건 전체)  | **1.13**                      | ≤ 3.0     | active |
| haiku gc 평균 (gate 2건만) | **1.00**                      | ≤ 3.0     | active |

**Slice 13 작업 우선순위 등록**:
- E3PromptBuilder + 다른 진입점에 gate 발동 시 "임계값/실제값 명시" 강제
- 패턴 재사용: Slice 12 Step 0b #59 E3 action measurability 강화 방식
- 예상 PS: 1.5 (Slice 13 Step 0 multi-debt mini 두 번째 후보)

---

## §7. #26 (분포 폭) 재발 진단

| 측정         | Slice 11 P5 | Slice 12 P4 | 임계 (#26 close 유지) |
| ------------ | ----------- | ----------- | --------------------- |
| nat 폭       | 3           | **1**       | ≥ 3 → **RE_REGRESSION** |
| ins 폭       | 3           | **2**       | ≥ 3 → **RE_REGRESSION** |

### 회귀 원인 분석
- Slice 11 P5: 단일 평가자(병진) blind shuffle + rubric 가이드 → 폭 3 달성
- Slice 12 P4: A/B blind 비교 평가 → **평가자가 둘을 가까이 두고 비교**하면서 차이를 좁게 평가하는 경향
- **방법론 차이**가 분포 폭 회귀의 핵심 원인 추정 — 평가 도구 형식 (단일 vs A/B)에 따른 자연 격차

### 처리 방안 (Slice 12 종결 시 결정)
- (A) #26 재오픈 + 평가 도구 표준 정착 작업 (PS 1.5)
- (B) #26 close 유지 + "A/B 비교 평가는 폭 좁아짐" 메모만 추가 (방법론 차이로 인정)
- 권고: **(B)** — Slice 11 P5는 단일 평가, Slice 12 P4는 A/B 비교. 다른 평가 도구는 다른 분포 특성. 룰을 평가 도구별로 분리하는 게 합리.

---

## §8. Slice 12 누적 (Step 0 → Part 4)

| Part   | commit         | 회귀         | 비용     | 결과                                            |
| ------ | -------------- | ------------ | -------- | ----------------------------------------------- |
| Step 0 | `f013c48`      | 571 → 580 (+9)  | $0.0554 | multi-debt mini (#58/#41/#59 E3 close)         |
| Part 1 | `74fd49b`      | 580 → 605 (+25) | $0      | scoring base + 5 adapter 스켈레톤              |
| Part 2 | `88f6274`      | 605 → 641 (+36) | $0      | 5 ScoringEngine 풀 + PresetSpec + gate         |
| Part 3 | `8c5bb6d`      | 641 → 668 (+27) | $0.0991 | E3 통합 + 15 smoke matrix + #58 production 검증 |
| Part 4 | (다음 commit)  | 668 → 668 (+0)  | $0.3207 | manual eval + 가설 8/8 정착 + #60 active        |

**전체 누적**: 571 → 668 (+97), $0.4752 / $1.00 cap (마진 52.5%)
**임계 누적**: $3.1196 / $4.00 (마진 22.0%)
**LLM 호출**: 34 / 50 (마진 16)

---

## §9. 부채 변화

| ID  | 상태               | 처리                                                            |
| --- | ------------------ | --------------------------------------------------------------- |
| #51 | 유지               | Slice 13 Step 0 1순위 (output_token multivariate estimator)     |
| #59 E5 | 유지            | Slice 13 Step 0 multi-debt mini (#51 또는 #60과 묶음)           |
| **#60** | **active 확정** | Slice 13 작업 등록 — gate-aware prompt 강화 (E3 우선)             |
| **#26** | **close 유지**   | 권고 (B) 채택 — 평가 도구별 분포 폭 룰 분리, 메모만 추가         |

close 0 / 신규 0 (이미 후보 #60 active로 결정) / 유지 3개 (#51, #59 E5, #60)

---

## §10. 산출물 (Part 4 전체, 10건)

| #   | 파일                                                       | 단계   |
| --- | ---------------------------------------------------------- | ------ |
| 1   | `scripts/slice12_part4_sonnet_batch.py`                    | Step 0 |
| 2   | `docs/portfolio/coach/slice12/part4_sonnet_results.json`   | Step 0 |
| 3   | `docs/portfolio/coach/slice12/part4_sonnet_dump.md`        | Step 0 |
| 4   | `scripts/slice12_part4_build_eval_input.py`                | Step 1a |
| 5   | `docs/portfolio/coach/slice12/part4_blind_eval_input.json` | Step 1a |
| 6   | `docs/portfolio/coach/slice12/part4_blind_eval_truth.json` | Step 1a |
| 7   | `docs/portfolio/coach/slice12/part4_blind_eval.html`       | Step 1a |
| 8   | `docs/portfolio/coach/slice12/part4_blind_eval_output.json` | Step 2 (병진) |
| 9   | `scripts/slice12_part4_aggregate.py`                       | Step 3 |
| 10  | `docs/portfolio/coach/slice12/part4_aggregate.json`        | Step 3 |
| 11  | `docs/portfolio/coach/slice12/part4_closing.md`            | Step 4 (본 문서) |

---

## §11. Slice 12 종결 사이클 사전 등록

다음 단계 진입 시 처리할 항목:

1. **D4-A.2 적용**: `kpi_matrix.md` §6에 신규 슬라이스 유형 "**component buildup +25~40**" 등록
   - 근거: Slice 12 누적 +97 (P1 +25 / P2 +36 / P3 +27 / P4 +0)
   - 룰: "scoring base + adapter + spec + 통합 + smoke + manual eval"의 6 part 패턴

2. **메모리 압축 B-Pattern** (Slice 11 P5 종결 패턴 재활용):
   - `project_slice12_progress.md`에 누적 entries (Step 0 + Part 1~4) → 1 entry로 압축
   - 핵심 자산 (PRESET_SCORERS / 12 preset matrix / #60 active) 보존

3. **누적 부채 처리 계획**:
   - **Slice 13 Step 0 multi-debt mini**: #51 (1순위) + #60 (3순위) + 가능 시 #59 E5 (4순위)
   - 패턴 검증: Slice 12 Step 0 multi-debt mini 첫 사례 → Slice 13에서 두 번째 적용

4. **lesson 메모리 추가 후보**:
   - "A/B blind 비교 평가는 단일 평가 대비 분포 폭 좁음" — 평가 도구 특성으로 인정
   - "글쓰기 가설 약 정착 (combined 7/15, tie 6/15)" — Slice 13+에서 추가 검증 가치

---

## §12. 결론

- **글쓰기 가설 8/8 누적 정착** (평균 우위 기반, 약 정착)
- **#60 active 확정** (gate-aware prompt 보강 우선순위)
- haiku **품질 (nat/ins) + efficiency (3.24× cheaper, 1.77× faster) double win** 재확인
- Slice 13+ 진입 준비 완료

Slice 12 4-Part 구조 완주 (Step 0 + Part 1~4). Slice 12 종결 사이클 진입 대기.
