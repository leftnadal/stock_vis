# Slice 7 (E4 대화 Q&A) 최종 종결 보고

> **종결일**: 2026-05-15
> **종결 commit**: TBD (이 보고서 작성 후)
> **누적 commit**: 3f79d21 (Phase A) → 8fc9c7c (Phase B/C) → 이번 commit (Phase D + 종결)

---

## §1. KPI 종합

| 항목 | 값 | 비고 |
|------|-----|------|
| 회귀 (portfolio/tests) | 369 → **392** (+23) | Part 4 KPI 목표 +7~11 초과달성 |
| IDENTICAL hash | 7/7 PASS | Slice 1 e1 + Slice 3 e2 보호 유지 |
| 호출 카운트 | 29 (Part 3) + 52 (Part 4 §3) = **81** | Slice cap 80 직후 ← 부채 등록 |
| 누적 광의 비용 | **$1.5950** | 임계 $1.50 **0.6% 초과** ⚠ |
| Stage 1 평가 완료 | **26/26** (haiku) | |
| Stage 2 평가 완료 | **25/26** (sonnet) | 1건 누락은 미미 영향 |
| 분포 폭 KPI (§C.6 ≥ 3.0) | **FAIL (2)** | nat 3~5 / ins 3~5 수렴 → #26 keep_open |

---

## §2. Winner & 글쓰기 가설

### 통합 efficiency (label_mean / avg_cost)

| Slice | Winner | haiku eff | sonnet eff | gap |
|-------|--------|----------|-----------|-----|
| slice5 | **haiku** | 608.48 | 183.28 | +232% |
| slice6 | **haiku** | 755.93 | 207.13 | +265% |
| slice7 | **haiku** | 1,192.02 | 320.67 | **+272%** |

### 가설 status

- **6_of_6_pending_slice1_3_4_verification** ✓
- Slice 5/6 winner 모두 haiku 유지 → 재판정 불필요
- **Slice 1·3·4 재검토 생략 가능** (M1 분기)
- **글쓰기 가설 6/6 정착 후보 ✓** (Slice 1·3·4·5·6·7 모두 haiku winner)

### Tier별 (Slice 7 전용)

| Tier | n | haiku label | sonnet label | 신호 |
|------|---|-------------|--------------|------|
| Tier 1 | 12 | 3.67 | **4.25** | sonnet 우세 |
| Tier 2 | 9 | 4.00 | 4.00 | 동일 |
| Tier 3 | 6 | 3.50 | 4.00 | sonnet 약간 우세 (weak signal n<6) |

→ **품질만 보면 sonnet 약간 우세**, 하지만 cost 4× 차이 → efficiency 압도적 haiku

---

## §3. Insight Rationale 구조 분석 (사용자 관찰 기반 신규 발견)

### 3.1 데이터

- 52건 sonnet rationale 분석 (slice5 14 + slice6 10 + slice7 28)
- **75%가 "구체성 부족" 지적** — 우연 아닌 구조적 신호
- 58% "왜?(이유) 미설명", 37% "피상적 분석"
- 평균 길이 253자

### 3.2 분포 (압도적 일관성)

| 분할 | 구체성 부족 빈도 |
|------|----------------|
| slice5 | 57% |
| **slice6** | **100%** |
| slice7 | 75% |
| haiku | 58% |
| **sonnet** | **92%** |

→ sonnet도 92% 지적받음. **모델 능력이 아닌 시스템 구조 문제**.

### 3.3 원인 (영향도순)

| # | 원인 | 영향 |
|---|------|------|
| ① | **Input fixture에 종목별 데이터 부재** (집계 지표만) | ★★★★★ |
| ② | **Output schema에 actionable 슬롯 없음** (자유 텍스트 1필드) | ★★★★ |
| ③ | **System prompt가 "구체성"을 강제 안 함** | ★★★ |
| ④ | **Generator-Evaluator gap** (rubric ≠ prompt) | ★★★ |
| ⑤ | **Few-shot example 부재** (Sample 5 미인용) | ★★ |

### 3.4 해결 방향 (Slice 8 백로그 #27~30 등록)

- **#27 + #28 + #29** trio가 핵심 (input + schema + prompt). 셋이 함께 들어가야 gap이 닫힘.
- 자세한 내용: `docs/portfolio/coach/slice7/refactor_backlog_slice7.md` 참조.

---

## §4. 분기 발동 종합 (§14 양식)

| 시나리오 | 발동 | 처리 |
|---------|------|------|
| M1 (winner 유지 + 분포 ≥ 3.0) | **부분 발동** | winner는 유지 / 분포 폭 미달은 #26 keep_open |
| M2 (winner 변경) | 미발동 | — |
| M3 (분포 폭 < 3.0) | **발동** | #26 keep_open + rubric §B sample 보완 백로그 |
| M4 (Stage 1 애매 3.0~3.5) | **발동** (3.58) | Stage 2 proceed |
| M5 (sonnet 우세) | 미발동 (label은 sonnet ↑, 그러나 efficiency haiku ↑) | primary haiku 유지 |
| M6 (citation_accuracy < 0.7 다수) | **측정 불가** | portfolio_metrics 키가 None → metadata 0.0 거의 모두 |
| M7 (Tier 3 n<6 weak signal) | **발동** | Slice 8 mock fixture 확장 백로그 #31 |
| M8 (#19 IDENTICAL hash 깨짐) | 미발동 | 7/7 유지 |

---

## §5. 처리 완료 부채

### #25 (rubric §B sample) — **closed ✓**

Part 4 §2에서 Sample 5건 영구 추가 + 회귀 3건. rubric §B.1 섹션 신설.

### #19 (LLMClient system 인자) — **closed ✓**

Part 4 §12에서 처리. `LLMClient.complete(..., system=None)` 분리, Anthropic SDK의 system 별도 인자 활용. system=None일 때 IDENTICAL hash 유지 (회귀 +4).

---

## §6. 신규 부채 (Slice 8+ 백로그)

| ID | 항목 | PS | 진입 |
|----|------|-----|------|
| **#26** | 분포 폭 KPI keep_open | 2.0 | Slice 8 Step 0 — rubric §B sample 5→10건 확장 |
| **#27** | E4 input에 종목별 holdings 데이터 추가 | **3.0** | Slice 8 Step 1 |
| **#28** | E4 output schema에 `action_items` 강제 슬롯 | **3.0** | Slice 8 Step 2 |
| **#29** | E4 system prompt "출력 형식 4요소" + Sample 5 few-shot | **2.5** | Slice 8 Step 3 |
| **#30** | 2-stage generation (narrative + action 분리) | 1.5 | Slice 9 후보 |
| **#31** | Slice 7 Tier 3 mock fixture 확장 (n=6 → n=10+) | 1.0 | Slice 8 백로그 |
| **#β2** | budget estimator systematic -50% bias | 3.0 (기존) | Slice 8 Step 0 |
| **비용 임계 초과** | Slice 7 누적 $1.595 > $1.50 (0.6%) | 1.0 | Slice 8 COST_POLICY 갱신 |

상세: `docs/portfolio/coach/slice7/refactor_backlog_slice7.md`

---

## §7. Slice 8 진입점 후보 (PS 가중합 기준)

| 후보 | PS | 가설 외삽 | 우선순위 |
|------|-----|----------|---------|
| **insight 품질 부채 trio (#27+#28+#29)** | **8.5 합산** | 구체성 closure | **1순위** |
| #β2 estimator 재설계 | 3.0 | 비용 안정성 | 2순위 |
| #24 preset 외삽 일반화 | 2.5 | preset 일관성 | 3순위 |
| #26 rubric §B 확장 | 2.0 | 분포 폭 회복 | 4순위 |
| Slice 1·3·4 재검토 | — | M1 발동으로 **생략** | — |

**Slice 8 시작 조건**: 비용 마진 회복 (COST_POLICY 임계 $1.50 → $2.00 갱신 또는 호출량 감축 전략)

---

## §8. Commit 메시지 권장 (§17 양식)

```
[slice7] Part 4 Phase D + 종결: #19 system 인자 + Stage 1/2 평가 + 종결 보고

- §8/§10: Stage 1 verdict + 통합 winner (slice5/6/7 모두 haiku)
- §11: 글쓰기 가설 6/6 정착 후보, Slice 1·3·4 재검토 생략
- §12: #19 LLMClient.complete(system=None) 분리, IDENTICAL hash 7/7 유지
- §13: Slice 7 종결 보고 + insight rationale 구조 분석 (75% 구체성 부족)
- 신규 부채 #27~30 (insight trio + 2-stage), #31 (Tier 3 fixture)
- 회귀 369 → 392 (+23)
- 누적 광의 $1.595 (임계 $1.50 0.6% 초과, Slice 8에서 정책 갱신)
```

---

## §V. 핵심 결과

1. **회귀 369 → 392 (+23) + IDENTICAL hash 7/7 유지**
2. **글쓰기 가설 6/6 정착 후보** (Slice 1·3·4·5·6·7 모두 haiku winner)
3. **Slice 1·3·4 재검토 생략 가능** (M1 분기, 시간 절약)
4. **분포 폭 KPI FAIL** (2 vs 임계 3.0) → #26 keep_open
5. **insight 품질 구조 결함 발견** — 75% 구체성 부족 (Slice 8 우선순위 1)
6. **#19 + #25 close 완료**
7. **누적 광의 $1.595** (임계 0.6% 초과, 단기 부채)
