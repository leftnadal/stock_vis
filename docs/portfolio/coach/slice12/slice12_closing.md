# Slice 12 종결 보고 — Preset Scoring Engine + Gate 패턴

**브랜치**: `slice12`
**종결일**: 2026-05-20
**구조**: Step 0 + Part 1~4 (5-Part)
**최종 commit**: `4e5363b` (Part 4)
**종결 사이클 commit**: (다음 commit)

---

## §1. Slice 12 전체 누적

| Part | commit | 회귀 | 비용 | 결과 |
|---|---|---|---|---|
| Step 0 | `f013c48` | 571 → 580 (+9) | $0.0554 | multi-debt mini 첫 사례 (#58/#41/#59 E3 close) |
| Part 1 | `74fd49b` | 580 → 605 (+25) | $0 | scoring base + 5 adapter 스켈레톤 |
| Part 2 | `88f6274` | 605 → 641 (+36) | $0 | 5 ScoringEngine 풀 + PresetSpec + gate 3건 |
| Part 3 | `8c5bb6d` | 641 → 668 (+27) | $0.0991 | E3+concentrated 통합 + 15 smoke + #58 production 검증 |
| Part 4 | `4e5363b` | 668 → 668 (+0) | $0.3207 | manual eval blind 30 commentary + 가설 8/8 약 정착 |
| **합계** | | **571 → 668 (+97)** | **$0.4752** | |

| 지표 | 값 |
|---|---|
| Slice cap | $0.4752 / $1.00 (마진 52.5%) |
| 전체 누적 | $3.1196 / $4.00 (마진 22.0%) |
| LLM 호출 | 34 / 50 (마진 16) |
| IDENTICAL | 7/7 PASS (7슬라이스 누적) |
| `--no-verify` | 0회 |

---

## §2. 종결 사이클 결정 4건 (2026-05-20 확정)

| 결정 | 채택 | 가중합 |
|---|---|---|
| **D1** Slice 13 multi-debt 구성 | **D1-B**: #51 + #60 (multi-debt mini 두 번째 사례) | 4.45 |
| **D2** #26 분포 폭 재발 처리 | **D2-B**: close 유지 + lesson 메모 | 4.05 |
| **D3** 글쓰기 가설 약 정착 후속 | **D3-B**: 강 정착 재검증 슬라이스 사전 등록 (Slice 14+) | 4.15 |
| **D4** KPI matrix component buildup 룰 | **D4-B**: 표준 +25~40 | 4.10 |

---

## §3. 신규 자산 (Slice 12 산출)

| 자산 | 위치 |
|---|---|
| 5 카테고리 ScoringEngine 풀 | `portfolio/services/scoring/presets/{value,growth,income,factor,special}.py` |
| 12 preset matrix | value 2 / growth 2 / income 2 / factor 4 / special 2 |
| PresetSpec schema | `portfolio/services/scoring/preset_spec.py` (frozen + extra=forbid + weights 1.0 validator) |
| gate 패턴 3건 | income×2 (yield ≥ 0.02) + factor low_volatility (beta ≤ 1.2) |
| PRESET_SCORERS dict + helpers | `portfolio/services/scoring/__init__.py` (get_scorer, resolve_category, format_scores_for_prompt) |
| parsers Tier 3 raw_decode | `portfolio/llm/parsers.py` (#58 close, production 검증) |
| E3 service metrics 통합 | `portfolio/services/coach/e3_service.py` (keyword-only preset_id/metrics, IDENTICAL 보장) |
| HTML blind eval 도구 | `docs/portfolio/coach/slice12/part4_blind_eval.html` (재활용 자산) |

---

## §4. Manual Eval 핵심 결과 (Part 4)

| 축 | haiku (15) | sonnet (15) | delta |
|---|---|---|---|
| naturalness | 3.60 | 3.20 | **+0.40** |
| insight | 3.53 | 3.27 | **+0.27** |
| gate_clarity (30건) | 1.13 | 1.27 | −0.13 |

| Cost / Efficiency | haiku | sonnet | ratio |
|---|---|---|---|
| 총 비용 | $0.0991 | $0.3207 | 3.24× |
| 평균 latency | 11,381 ms | 20,176 ms | 1.77× |
| efficiency | 72 | 20 | **+257%** haiku 우위 |

**글쓰기 가설**: 8/8 약 정착 (combined wins 7/15, tie 6/15, 평균 우위 2차 룰 PASS).
**haiku double win**: 품질 + efficiency 재확인.

---

## §5. 부채 변화

| ID | 상태 | 처리 |
|---|---|---|
| #58 | **close** (Step 0) | parsers Tier 3 raw_decode, Part 3에서 production 효과 입증 (15/15) |
| #41 | **close** (Step 0) | output schema 통합 base |
| #59 E3 | **close** (Step 0) | E3 action measurability 규칙 |
| #60 | **active 확정** (Part 4) | gate-aware prompt — Slice 13 Step 0 2순위 (PS 1.5) |
| #26 | **close 유지** (Part 4 D2-B) | 평가 도구별 분포 폭 자연 격차 인정, lesson 메모 추가 |
| #51 | 유지 | Slice 13 Step 0 1순위 (output_token multivariate estimator, PS 1.5) |
| #59 E5 | 유지 | Slice 14+ 후보 (PS 0.5, E5 진입점 결합) |

**Slice 12 부채 net**: close 3 / active 결정 1 / 신규 0 / 유지 2.

---

## §6. KPI Matrix 갱신 (D4-B 적용 완료)

`docs/portfolio/coach/kpi_matrix.md` §6에 신규 슬라이스 유형 추가:

| 슬라이스 유형 | 회귀 +Δ 기대값 | ±30% 임계 |
|---|---|---|
| Component buildup 슬라이스 | **+25~40** | **+17~52** |

**적용 조건**: parametrize-heavy + base/adapter/spec/통합/smoke의 다단계 자산 축적.
**검증**: Slice 12 P1 +25 / P2 +36 / P3 +27 모두 ±30% 임계 [+17, +52] 내 PASS.

---

## §7. Lesson 메모 (D2-B 적용)

**`lesson_eval_tool_distribution_width.md`** 신규 추가:

> 평가 도구 형식별 분포 폭 자연 격차: 단일 평가는 폭 ≥3, A/B 비교 평가는 폭 1~2 자연. Slice 11 P5(단일, 폭 3)와 Slice 12 P4(A/B, 폭 1~2)의 차이는 평가자 의도가 아닌 도구 본질 특성. #26 close 유지 + 평가 도구별 룰 분리.

향후 Slice 13+ manual eval에서 도구 선택 가이드:
- 글쓰기 가설 강 정착 검증 → 단일 평가
- 모델 직접 비교 (haiku vs sonnet) → A/B blind
- gate clarity 등 특정 축 진단 → A/B 비교

---

## §8. Slice 13 사전 등록 (D1-B + D3-B 적용)

### Step 0: multi-debt mini-slice 두 번째 사례

| 항목 | 내용 |
|---|---|
| Step 0a | **#51** output_token multivariate estimator (PS 1.5, 1순위) |
| Step 0b | **#60** gate-aware prompt (PS 1.5, 2순위, active) |
| 회귀 예상 | +8~12 (Step 0 mini-slice 임계 +13~20 약간 미달 가능) |
| 비용 예상 | $0 (계산·prompt만, smoke 없음) |
| 검증 | multi-debt mini 패턴 두 번째 적용 (Slice 12 첫 사례 검증 완료) |

### 본 work

진입점 미정 — Slice 13 사전 결정 사이클에서 확정.

### Slice 14+ 사전 등록 (D3-B)

**글쓰기 가설 강 정착 재검증**:
- #60 적용 후 manual eval 1회 (단일 평가 도구, Slice 11 P5 패턴)
- 분포 폭 ≥ 3 + combined wins ≥ 9 시 강 정착 갱신
- 미달 시 약 정착 한계 명시 + 모델 정책 재검토
- 비용 ~$0.34 (sonnet batch 1회), 평가 ~1.5h

---

## §9. Slice 13 진입 Baseline

| 항목 | 값 |
|---|---|
| 브랜치 | `slice13` (신규 생성 필요) |
| baseline 회귀 | 668 |
| 전체 누적 비용 | $3.1196 / $4.00 (마진 22.0%) |
| Slice cap | $0 / $1.00 (slice 13 신규 cap, reset) |
| LLM 호출 | 0 / 50 (slice 13 신규 budget, reset) |
| IDENTICAL | 7/7 (8슬라이스째 유지 목표) |
| Step 0 | multi-debt mini #51 + #60 |
| pre-commit hook | ALLOWED_BRANCHES에 `slice13` 추가 완료 (종결 사이클 commit 포함) |

---

## §10. 결론

- **Slice 12 5-Part 구조 완주** (Step 0 + Part 1~4)
- preset 스코어링 엔진 모듈 end-to-end 완성: 점수 계산 → E3 통합 → manual 검증
- **글쓰기 가설 8/8 약 정착**, haiku double win 재확인
- **#60 gate-aware prompt active** — Slice 13에서 사용자 UX 개선 즉시 처리
- **component buildup KPI 유형 정착** — 향후 scoring engine 확장 슬라이스 false alarm 차단
- **평가 도구별 분포 폭 lesson 등록** — Slice 13+ manual eval 도구 선택 가이드
- 전체 누적 비용 마진 22% / LLM 마진 16 — Slice 13 진입 안전

Slice 12 종결. Slice 13 사전 결정 사이클 진입 대기.
