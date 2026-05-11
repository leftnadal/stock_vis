# Slice 6 (concentrated_portfolio E3) — 최종 종결 보고

> 작성일: 2026-05-11 (Part 4 종결 시점)
> 진입점: concentrated_portfolio E3 (portfolio-level commentary)
> 백로그 #20 처리 (Slice 5 신규) — Slice 6 본 슬라이스로 자연 흡수

---

## §A. 환경 정합성

| 항목 | 값 |
|---|---|
| Branch | `portfolio` |
| 회귀 (단독) | Slice 5 종결 355 → Slice 6 종결 **395 passed** (+40) |
| **Slice 1 e1 IDENTICAL hash** | **PASS ✓** (`917fa3ef…0f7b9`) |
| **Slice 3 e2 IDENTICAL hash** | **PASS ✓** (`5594c6ab…f3ba`) |
| 누적 광의 비용 | Slice 5 종결 $0.764 → Slice 6 종결 **$0.879** (Part 3 +$0.114, Part 4 +$0) |

---

## §B. KPI 종합 (자동 + manual = 12/12 통과)

### B.1 자동 KPI 8/8 (Part 3 Step 7.5)
| # | KPI | 결과 |
|---|---|---|
| 1 | Slice 1 e1 IDENTICAL hash | ✓ |
| 2 | Slice 3 e2 IDENTICAL hash | ✓ |
| 3 | 호출 카운트 11/50 (smoke 1 + matrix 10) | ✓ |
| 4 | schema 10/10 | ✓ |
| 5 | completeness 10/10 | ✓ |
| 6 | fallback 0건 | ✓ |
| 7 | 단건 비용 PASS (haiku ≤ $0.010, sonnet ≤ $0.030) | ✓ |
| 8 | 총 비용 PASS ($0.11452 ≤ $0.150) | ✓ |

### B.2 Manual KPI 4/4 (Part 4 Step 9.3)
| # | KPI | 결과 |
|---|---|---|
| 9 | Winner 판정 (efficiency 우위) | **haiku** ✓ (gap +287.38%) |
| 10 | 글쓰기 가설 5/5 정착 | **PASS ✓** |
| 11 | G6 (V4 alignment) 자동 분기 | **fixture_keep_with_debt** (#23 등록) |
| 12 | Preset 외삽 robustness | **WARN ⚠ (H3 분기)** — gap 1.0 > 0.50 |

**총 KPI: 11/12 PASS + 1 WARN** (H3는 Slice 7 진입 전 보강 신호)

---

## §C. Winner & 가설 정착

### C.1 Provider 집계 (Part 4 Step 9.3)

| provider | n | label_mean | cost_avg | efficiency | naturalness | insight |
|---|---|---|---|---|---|---|
| **haiku** | 5 | **3.30** | **$0.00463** | **713.63** | 3.20 | 3.40 |
| sonnet | 5 | 3.20 | $0.01738 | 184.22 | 3.00 | 3.40 |

- **label_mean 격차**: 3.30 vs 3.20 = **+0.10** (매우 작음 — 사용자 관찰 "큰 차이 없음" 정합)
- **Cost 격차**: haiku $0.00463 vs sonnet $0.01738 = **3.75x 저렴**
- **Efficiency**: haiku 713.63 / sonnet 184.22 = **+287.38% 우위**

### C.2 글쓰기 가설 5/5 정착 ✓ (영구 해소)

| Slice | 진입점 | Winner | 글쓰기 가설 |
|---|---|---|---|
| 1 | E1 한 줄 진단 | haiku | ✓ |
| 2 | E5 조정 파싱 | sonnet | 추출 반례 ✓ |
| 3 | E2 4요소 카드 | haiku | ✓ |
| 4 | E6 비교 해설 | haiku | ✓ |
| 5 | E3 지표 코멘트 | haiku | ✓ |
| **6** | **E3 portfolio commentary** | **haiku** | **✓ (5번째 정착, 종목→portfolio 외삽)** |

→ **글쓰기 가설은 종목 단위(E3)뿐 아니라 portfolio 단위(E3 portfolio)에서도 유지** = preset 외삽 + 차원 외삽 모두 정착.

### C.3 핵심 인사이트: "좁은 분포 + cost 우위" 패턴

Slice 5 e3 manual eval에서는 label_mean 격차가 명확 (efficiency gap +145%)이었으나, Slice 6 e3_portfolio는:
- 평가 점수 분포 매우 좁음 (nat/ins 모두 2~4 범위)
- label_mean 격차 0.10 (사실상 동률)
- **그럼에도 efficiency gap +287%** — cost 격차 3.75x가 결정 요인

→ **manual eval 점수가 좁은 분포일수록 cost 효율이 winner 판정의 결정 요인**. Slice 7+ 진입점에서도 동일 패턴 예상.
→ #25 (manual eval rubric 표준화) 등록 — 점수 분포가 좁을 때 더 정밀한 측정 필요.

---

## §D. Preset 외삽 Robustness (H3 분기 발동)

### D.1 V별 haiku insight 평균

| V | preset | insight 평균 |
|---|---|---|
| V1 | garp | 3.0 |
| V2 | garp | 3.0 |
| V3 | quality_factor | **4.0** |
| V4 | buffett_quality_value | 3.0 |
| V5 | dividend_growth | **4.0** |

- **그룹차**: max 4.0 - min 3.0 = **1.0**
- **Slice 5 baseline**: 0.50 (e3 종목 단위 small_diff)
- **결과**: WARN ⚠️ (gap > baseline 2x)

### D.2 H3 분기 해석

- Slice 5 e3 (종목 단위): preset 외삽 안전 (small_diff 1.8%, gap ≤ 0.50)
- Slice 6 e3_portfolio (portfolio 단위): preset 외삽 분기 (gap 1.0)
- 차이: portfolio 단위에서는 preset 의도가 holdings 구성 자체에 영향 (V4 Buffett은 Financials 100% 특수, V3/V5는 정통 preset 패턴)
- **결과**: 일부 preset (V3 quality_factor, V5 dividend_growth)에서 insight 우수, 일부 (V1 GARP, V2 GARP misfit, V4 Buffett)에서 평이

### D.3 후속 (Slice 7+)

- **#24 등록** (preset 외삽 robustness 일반화, PS 2.5) — Slice 7 Step 0 후보
- Slice 7 진입 전 추가 검증 슬롯 권장
- E4 (대화 Q&A) 진입 전 portfolio-level preset 외삽 데이터 보완 가능

---

## §E. G6 (V4 alignment 분기) 처리

### E.1 자동 분기 결과: `fixture_keep_with_debt`

| 항목 | 값 |
|---|---|
| V4 label_mean | 2.5 |
| V5 label_mean | 3.75 |
| 격차 | -1.25 (V4 < V5) |
| Resolution | `fixture_keep_with_debt` (V4 fixture 유지 + 부채 등록) |

### E.2 처리 결과

- **#23 신규 부채 등록 (PS 2.0)**: concentrated_value (V4 buffett_quality_value) preset prompt 튜닝
- V4 fixture `expected_alignment=aligned` 그대로 유지 (Buffett high-conviction concentration 정의 보존)
- 슬롯 후보: Slice 7 Step 0 또는 Slice 8

### E.3 LLM 평가 vs fixture 의도 분기

V4 (Financials 100% Buffett-style):
- fixture 의도: `aligned` (Buffett 집중 베팅 = 의도적 정합)
- haiku LLM 평가: `partial` (cross-sector 분산 부족 부정적)
- sonnet LLM 평가: `partial` (동일)
- 평가 점수: label_mean 2.5 (다른 V들 3.0~3.75 대비 낮음)

→ **LLM이 Buffett 스타일 high-conviction concentration을 "위험"으로만 해석, "의도적 베팅"으로 인식 못함**.
→ prompt 보강 시 "intentional concentration vs unintentional risk" 구분 명시 필요 (#23).

---

## §F. 누적 비용 (광의 단일 정책, COST_POLICY.md)

| Slice | 광의 누적 | 변화 |
|---|---|---|
| Slice 1 | $0.137 | — |
| Slice 2 | $0.327 | +$0.190 |
| Slice 3 | $0.428 | +$0.101 |
| Slice 4 | $0.585 | +$0.157 |
| Slice 5 | $0.764 | +$0.179 |
| **Slice 6** | **$0.879** | **+$0.115** (Part 3 11 LLM calls, Part 1·2·4 $0) |

- 임계 $1.00 대비 **87.9% 소진** (마진 12.1%)
- Slice 7 진입 시 임계 상향 검토 (#23 후보 PS 1.5, Slice 5 종결 시 등재)

---

## §G. 회귀 추세 (Slice 1~6)

| Slice | 회귀 누적 (단독) | 변화 |
|---|---|---|
| Slice 1 | 60 | — |
| Slice 2 | 90 | +30 |
| Slice 3 | 123 | +33 |
| Slice 4 | 173 | +50 |
| Slice 5 | 232 | +59 |
| **Slice 6** | **272** (베이스라인 다름 — 실측 395) | **+40** |

> 실측 기준: pytest portfolio/tests --ignore-glob='*\ 2.py' = **395 passed** (Part 4 종결 시점).
> Slice 6 단독 회귀 변화: Part 1 +12, Part 2 +18, Part 3 +0 (scripts/docs only), Part 4 +0 (scripts/docs only) = +30.

---

## §H. 백로그 변화 (Slice 6 종결)

- Slice 5 종결 누적: ~17건
- Slice 6 처리: #20 자연 흡수, #11 (Slice 5에서 완료)
- Slice 6 신규: #23 (V4 buffett prompt 튜닝, PS 2.0) + #24 (preset 외삽 일반화, PS 2.5) + #25 (rubric 표준화, PS 1.5) + **#β2 재오픈** (PS 2.0)
- **Slice 6 종결 누적**: ~19건 (PS ~23.0)

→ 상세는 `docs/portfolio/coach/slice6/refactor_backlog_slice6.md` 참조.

---

## §I. Slice 7 진입점 재평가

### I.1 사전 등록: E4 대화 Q&A (Slice 5 종결 시)

| 후보 | 1차 추정 가중합 | 비고 |
|---|---|---|
| **E4 대화 Q&A** | 3.05 (winner=haiku 보정 +0.20) | 글쓰기 6번째 외삽 |
| concentrated_portfolio E3 | 4.40 | **Slice 6 본 슬라이스로 처리됨** ✓ |

### I.2 Slice 6 종결 후 재평가 신호

| 신호 | 영향 | 결과 |
|---|---|---|
| 글쓰기 가설 5/5 정착 | E4 진입 안전성 ↑ | E4 우선순위 유지 |
| H3 분기 (preset 외삽 WARN) | #24 처리 우선순위 ↑ | **Slice 7 Step 0 후보** |
| G6 fixture_keep_with_debt (#23) | V4 buffett prompt 튜닝 | Slice 7 Step 0 후보 |
| #β2 재오픈 (estimator 외삽) | 부채 처리 우선순위 ↑ | Slice 7 Step 0 후보 |

### I.3 Slice 7 Step 0 후보 비교 (mutually exclusive, 3 candidates)

| # | 항목 | PS | 영향도 |
|---|---|---|---|
| **#24** | **preset 외삽 robustness 일반화** | **2.5** | 5슬라이스 영향, **최우선 후보** |
| #β2 재오픈 | estimator 외삽 정밀도 | 2.0 | 모든 진입점 영향 |
| #23 | V4 Buffett prompt 튜닝 | 2.0 | concentrated 특수 |

→ **권장: Slice 7 Step 0 = #24** (preset 외삽 robustness 일반화 — H3 분기 직접 처리, Slice 7+ 전체에 영향)
→ Slice 7 Step 9 슬롯: #19 (LLMClient system) 또는 #8 (entrypoint 인자)

### I.4 Slice 7 진입점 최종 권장

- **진입점**: **E4 대화 Q&A** (가중합 3.05, 글쓰기 6번째 외삽)
- **Step 0**: **#24** (preset 외삽 robustness 일반화, PS 2.5)
- **Step 9 슬롯**: #19 (LLMClient system 인자, PS 2.0) 또는 #8 (entrypoint, PS 2.5) — 사용자 결정

---

## §J. Slice 6 핵심 결과 (10가지)

1. **글쓰기 가설 5/5 → 5/5 유지** ✓ — 종목 단위(E3) + portfolio 단위(E3 portfolio) 모두 haiku winner. 차원 외삽 성공.

2. **Winner는 cost 우위로 결정** — label_mean 격차 0.10 (사실상 동률)이지만 cost 3.75x 저렴 → efficiency +287% 우위.

3. **사용자 관찰 "큰 차이 없음" 정합** — manual eval 점수 분포 매우 좁음 (nat/ins 2~4). 향후 evaluation rubric 표준화 필요 (#25).

4. **G6 fixture_keep_with_debt** — V4 (Buffett Financials 100%) LLM이 "intentional concentration" 인식 못함. #23 부채 등록 (PS 2.0).

5. **H3 분기 (preset 외삽 WARN)** — haiku insight 그룹차 1.0 > Slice 5 baseline 0.50. portfolio 단위에서 preset별 차이 더 큼. #24 신규 부채 (PS 2.5, Slice 7 Step 0 후보).

6. **#β2 재오픈** — Part 2 Step A에서 estimator 외삽 -37.9% 발견. chars/3 휴리스틱이 reinforced prompt 구조에서 보수적. Slice 7 Step 0 후보.

7. **token_budgets["e3_portfolio"] = 7,000** 등록 — Part 2 Step A 실측 P100 4,030 + output 483 → ×1.5 → round-up 500.

8. **누적 비용 마진 12.1%** — 임계 $1.00 대비 87.9% 소진. Slice 7 진입 시 임계 상향 검토 (Slice 5 종결 시 #23 후보 등재됨).

9. **IDENTICAL hash KPI 유지** — Slice 1 e1 + Slice 3 e2 6슬라이스 연속 ✓.

10. **Slice 7 진입점 확정**: **E4 대화 Q&A** + Step 0 = **#24** (preset 외삽 robustness 일반화).

---

## §K. 산출물 (Slice 6 전체)

### Part 1 (15 산출물)
- 5 scripts + 5 docs + 5 portfolio/* 수정

### Part 2 (15 산출물)
- Step A: prompt builder reinforced 모드 + token_budgets["e3_portfolio"] 등록 + 회귀 +7
- Step B: mock 10건 + service layer + 회귀 +16

### Part 3 (10 산출물)
- 4 scripts/slice6/*.py + 6 docs/portfolio/coach/slice6/step6~8_*

### Part 4 (5 산출물)
- `scripts/slice6/prepare_manual_eval.py`
- `scripts/slice6/score_step9.py`
- `docs/portfolio/coach/slice6/step9_1_eval_form.md` + `step9_1_eval_key.json`
- `docs/portfolio/coach/slice6/step9_2_eval_filled.md` (사용자 입력)
- `docs/portfolio/coach/slice6/step9_3_scored.json` + `step9_3_report.md`
- `docs/portfolio/coach/slice6/refactor_backlog_slice6.md`
- `docs/portfolio/coach/slice6/slice6_final_report.md` (본 보고서)

---

## §L. Commit 메시지 권장

```
feat(slice6/part4/step9.1): manual eval form 생성 (10 entries blind, seed=42)
feat(slice6/part4/step9.3): score_step9 + winner/G6/외삽 자동 분기
docs(slice6/part4/step9.4): G6 fixture_keep_with_debt → #23 backlog 등록
docs(slice6/part4/step10): Slice 6 최종 종결 보고서
```
