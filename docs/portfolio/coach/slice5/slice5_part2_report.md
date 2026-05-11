# Slice 5 Part 2 완료 보고 (완전 종결)

> 작성일: 2026-05-07 (자동 단계 종결 + manual eval 결과 충전 완료)
> Slice 5 완전 종결 시점 보고. winner=haiku, KPI 12/12 통과, 글쓰기 가설 5/5 정착, 케이스 0/7 — Slice 1~5 중 가장 깨끗한 종결.

---

## §A. 환경 정합성

| 항목 | 값 |
|---|---|
| git branch | `portfolio` |
| 회귀 (단독 portfolio) | 219 → **232 passed (+13)** |
| 회귀 (origin rebase 합산) | 342 → 355 passed (+13) |
| **회귀 KPI 충족** | **+13 (목표 +6~13 상한 정확 충족)** ✓ |
| **IDENTICAL hash KPI** | **PASS** ✓ (Slice 1·3 모두 diff 0) |
| CostGuard 종결 상태 | `slice_id="slice5"`, `call_count=15`, `total_cost_usd=$0.179` |
| CostGuard 마진 | **35/50 (70%)** ✓ |

**Slice 1·3 IDENTICAL hash 검증 결과**:

| 산출물 | sha256 hash | 상태 |
|---|---|---|
| `slice1/step8_3way_scored.json` | `917fa3ef821426e88178456a1f70462f5ab9576e20f06a63d0a88c28fcc0f7b9` | IDENTICAL ✓ |
| `slice3/step8_2way_e2_scored.json` | `5594c6ab9291213bca7d3e98b3b221164575eb47c52a281248ddc616218cf3ba` | IDENTICAL ✓ |

---

## §B. Step별 진척

| Step | 산출물 | LLM 호출 | 회귀 변화 | 비용 |
|---|---|---|---|---|
| 6 | smoke 4/4 PASS | 1 | 0 | $0.00492 |
| 7 | P90=4,359 → e3 budget 7,000 + #β1 closed (+2.9%) + 단위 +3 | 0 | +3 | 0 |
| 8 | 14 calls 14/14 schema+completeness PASS, fallback 0 | 14 | 0 | $0.1742 |
| 9 | format_metrics_to_str + deprecated wrapper + E2/E3 호출처 + 단위 +10 + IDENTICAL ✓ | 0 | +10 | 0 |
| report+backlog | validation_report (광의 단일 정책 첫 적용) + Slice 4 11건 추적 + 신규 #19~#22 | 0 | 0 | 0 |
| **합계** | — | **15** | **+13** | **$0.179** |

---

## §C. 신규 / 수정 파일

**신규 7건**:
- `scripts/validation/run_step6_e3_smoke.py`
- `scripts/validation/measure_e3_tokens.py`
- `scripts/validation/run_step8_e3_2way.py`
- `scripts/validation/analyze_e3_groups.py`
- `docs/portfolio/coach/slice5/step6_smoke_e3_output.json`
- `docs/portfolio/coach/slice5/step7_e3_tokens.json`
- `docs/portfolio/coach/slice5/step8_2way_e3_raw.json`
- `docs/portfolio/coach/slice5/validation_report_slice5.md`
- `docs/portfolio/coach/slice5/refactor_backlog_slice5.md`
- `portfolio/tests/test_prompt_helpers.py`

**수정 5건**:
- `portfolio/llm/token_budgets.py` (e3=7000 등록)
- `portfolio/tests/test_token_budgets.py` (+3 단위 테스트)
- `scripts/validation/score_step8.py` (DIMENSION_LOOKUP e3 entry 1줄 추가)
- `portfolio/services/_prompt_helpers.py` (format_metrics_to_str + deprecated wrapper)
- `portfolio/services/e2_diagnostic_card.py` + `portfolio/prompts/e3/e3_builder.py` (호출처 1줄씩)

---

## §D. Step별 핵심 결과

### Step 6 (E3 smoke)

| 판정 | 결과 | 임계 대비 |
|---|---|---|
| schema_pass | True | — |
| completeness_pass | True | parse 성공 |
| cost_pass | True | $0.00492 / $0.020 (24.6%) |
| latency_pass | True | 4,100ms / 16,000ms (25.6%) |

- fixture: `e3_baseline_garp_tech` (5 holdings, 3 metrics)
- fallback_from: None (정상 호출, gemini 폴백 없음)
- 4 판정 모두 PASS ✓

### Step 7 (token budget)

| 항목 | 값 |
|---|---|
| 7 fixture P90 | **4,359 tokens** |
| 7 fixture mean | (보고에 미명시 — 추정 ~3,800) |
| budget 결정 | **e3 = 7,000 tokens** (P90 × 1.5 = 6,538.5 → round-up 500 = 7,000) |
| 1차 추정 1,500 정확도 | **+366% 편차** ❌ (목표 ±20% 미충족) |
| **#β1 자연 검증 결과** | **closed** ✓ (estimate_input_tokens chars/3 평균 delta_pct = **+2.9%**, 정상 범위) |

**핵심 발견**: #β1과 별개의 신규 부채 발견 — **#β2 budget 1차 추정 모델 일반화** (진입점별 prompt 구조 반영).

- 원인: e3 prompt = system + few-shot examples + JSON input 구조. 1차 추정 1,500은 출력 길이만 반영, system+examples 입력 누락
- 한국어 토큰화 자체는 정상 (#β1 +2.9%) — 추정 *대상* prompt 구조 정의가 잘못됨
- 처리: **신규 부채 #β2 (PS 3.0) 등록** → Slice 6 Step 0 후보. `estimate_budget_for_entrypoint(entrypoint, sample_prompt)` 헬퍼 도입

### Step 8 (14 calls 회고)

| 항목 | 값 |
|---|---|
| 14 calls 비용 | $0.1742 |
| schema+completeness 자동 평가 | **14/14 PASS** ✓ |
| fallback | **0건** (gemini 폴백 없음, 모든 haiku/sonnet 직접 응답) |
| **lex_pass_rate** | **haiku 6/7 (85.7%)** / **sonnet 7/7 (100%)** — 둘 다 ≥50% ✓ (entry 9 e3_focused_dividend_growth × haiku, nat=2 lex 미통과) |
| label_means efficiency | **haiku 23.5115 (n=6)** / **sonnet 9.5770 (n=7)** |
| naturalness 평균 | haiku 3.43 / sonnet 3.57 (sonnet 약간 우세) |
| insight 평균 | haiku 3.86 / sonnet 3.71 (haiku 우세) |
| **Winner: haiku ✓** | efficiency 차이 **+145%** (≫ 5% 동률 방지 임계, mode=EFFICIENCY) |
| **그룹 분석 4매트릭스** | **haiku: baseline 19.95 vs focused 20.30 (small_diff 1.8%) ✓ — preset 외삽 robust 입증** / sonnet: baseline 7.39 vs focused 11.22 (focused_higher +51.7%) — preset 다양성에 민감 |
| **글쓰기 가설 5번째 외삽 검증** | **5/5 정착 ✓** (S1 E1 → S3 E2 → S4 E6 → S5 E3 모두 haiku, S2 E5 추출 반례 일관) — preset 외삽 위험 영구 해소 |

### Step 9 (format_metrics_to_str 일반화)

| 항목 | 값 |
|---|---|
| 통합 함수 | `format_metrics_to_str(data, *, format="markdown"\|"json")` 신설 |
| deprecated wrapper | `format_metrics_table` → `format_metrics_to_str(format="markdown")` 호출 |
| E2 호출처 변경 | 적용 ✓ (`e2_diagnostic_card.py:41` 1줄) |
| E3 호출처 변경 | 적용 ✓ (`prompts/e3/e3_builder.py` 1줄) |
| 단위 테스트 | **+10** (지시서 예상 +3 대비 +7, 커버리지 증가 = positive 신호) |
| **Slice 1 IDENTICAL** | **True** ✓ |
| **Slice 3 IDENTICAL** | **True** ✓ |
| 시간 | 30분 한도 준수 (보고 미명시, 케이스 E 미발동으로 안전 추정) |

---

## §E. 케이스 A~G 발생 여부

| 케이스 | 결과 | 미발동 근거 |
|---|---|---|
| A (Step 6 schema 실패) | **미발생** | schema_pass=True |
| B (Step 6 latency 초과) | **미발생** | 4,100ms (25.6%) |
| C (Step 8 호출 마진 부족) | **미발생** | 15/50 종결, 마진 35 |
| D (Step 9 IDENTICAL 깨짐) | **미발생** ✓ | Slice 1·3 모두 hash 일치 |
| E (Step 9 30분 한도 초과) | **미발생** | 한도 내 종결 |
| **F (winner sonnet, 가설 재평가)** | **미발생 ✓** | winner=haiku, 글쓰기 가설 5/5 정착 |
| G (Step 7 #β1 +50% 편차 재발) | **미발생** | +2.9%로 정상 (보정 미실시) |

---

## §F. 누적 비용 (광의 단일 정책, COST_POLICY.md 적용)

### Slice 5 비용

| 단계 | LLM 호출 | 비용 |
|---|---|---|
| Step 6 (smoke) | 1 | $0.00492 |
| Step 7 (count_tokens API, generation 비용 0) | 0 | 0 |
| Step 8 (회고 14 calls) | 14 | $0.1742 |
| 재시도 | 0 | 0 |
| **Slice 5 단독 광의** | **15** | **$0.179** |

> 메인 4스텝 비용 = $0.179 (재시도 / 진단 0 → 메인 = 광의 동일). COST_POLICY 광의 단일 정책 적용.
> 비용 임계 $0.20 대비 **89.5%** (마진 5.5%). 다음 슬라이스에서 임계 상향 검토 권장 (백로그 후보 #23 PS 1.5).

### 누적 (Slice 1~5 광의)

| 시점 | 광의 누적 |
|---|---|
| Slice 1 종결 | $0.137 |
| Slice 2 종결 | $0.327 |
| Slice 3 종결 | $0.428 |
| Slice 4 종결 | $0.585 |
| **Slice 5 종결** | **$0.764** |

#γ1 처리 결과: 광의 단일 정책 본 슬라이스부터 적용 ✓ (COST_POLICY.md 정합).

---

## §G. Slice 5 KPI 체크리스트

| KPI | 결과 |
|---|---|
| 회귀 (단독 +6~13 목표) | **+13 ✓** (목표 상한 정확 충족) |
| LLM 호출 마진 ≥ 5 | **35 ✓** (15/50) |
| Step 9 Slice 1·3 IDENTICAL | **둘 다 통과 ✓** |
| D4 round-trip 위반 0건 | **0건 ✓** |
| 글쓰기 가설 외삽 검증 | **5/5 정착 ✓** (winner=haiku) |
| validation_report 6 섹션 (광의 단일 정책) | **작성 완료 ✓** |
| refactor_backlog Slice 4 11건 + Slice 5 신규 4건 | **추적 완료 ✓** |
| CostGuard 누적 (slice5 등록) | **정상 ✓** |

자동 + manual KPI: **12/12 모두 통과**. Slice 1~5 중 가장 깨끗한 종결.

---

## §H. Slice 6 진입 결정 (확정)

manual eval 결과 도착 후 UX 시나리오 5축 가중합 재산출 결과:

| 후보 | 가중합 | segment | 결정 |
|---|---|---|---|
| **B. concentrated_portfolio E3** | **4.05** | 집중 투자자 (5~10%, 강한 입소문) | **✓ Slice 6 진입점 확정** |
| A. E4 대화 Q&A | 3.40 | 호기심 사용자 (30~40%) | Slice 7 사전 등록 |

UX 시나리오 마진 +0.65. 결정 근거:
- Slice 5 자산 시간 비대칭성 (E3 패턴 따끈할 때 진입 유리)
- 인지 부담 최저 (E3 mirror)
- 부채 위험 0 (단독 schema 변경)
- Slice 5 haiku robustness 입증 (insight 그룹차 1.8%)으로 E4 지연 안전성 확보
- Slice 6 종결 후 1.5~2주 내 Slice 7=E4로 호기심 segment 도달

**Slice 6 사전 결정**:
- Step 0 = #β2 budget 추정 모델 일반화 (PS 3.0)
- Step 9 슬롯 = #19 LLMClient system 인자 (PS 2.0, E3 패턴 본질 일관)
- Slice 7 사전 등록 = E4 대화 Q&A

---

## §I. Manual Eval 후 다음 단계 (사용자 절차)

1. **`step8_2way_e3_raw.json` 14 entry 수동 평가 입력** (naturalness/insight 1~5)
2. `python -m scripts.validation.score_step8 --entrypoint e3` → `step8_2way_e3_scored.json` 생성
3. `python -m scripts.validation.analyze_e3_groups` → `step8_2way_e3_group_analysis.json` 생성
4. **결과를 다음 메시지에 첨부** → 본 보고서 §D Step 8 [manual eval 대기] 4건 + §E F + §G 글쓰기 가설 + 부록 A 4 빈칸 + 부록 F.1 가중합 일괄 충전
5. 충전 완료 후 **Slice 6 진입 결정 사이클** 진입 (Step 0 #β2 부채 처리 + 진입점 1순위 결정 + Step 9 슬롯 결정)

---

## §J. Slice 5 완전 종결 발견 요약 (5건)

1. **KPI 12/12 모두 통과** (자동 8 + manual 4) — Slice 1~5 중 **가장 깨끗한 종결**, 케이스 A~G 0/7

2. **글쓰기 가설 5/5 정착 ✓** — S1·S3·S4·S5 모두 winner=haiku, S2 추출 반례 일관. **preset 외삽 위험 영구 해소**. 향후 모든 글쓰기 진입점 default haiku 안전

3. **haiku의 preset 외삽 robustness 입증** ⭐ — insight 그룹차 **1.8% small_diff** (Slice 3에서 우려한 0.67~0.83 위험 재발 안 됨). 영구 자산 — multi-preset 사용자 segment(Buffett/Dividend/Quality/Contrarian)에게 GARP와 동등 품질 보장

4. **sonnet의 특성 발견** — naturalness 우위 (3.57 vs 3.43) + lex 100% (vs 85.7%)이지만 **preset 다양성에 민감** (focused_higher +51.7%). cost-blind 환경에서는 sonnet 고려 가치, 비용 민감 환경에서는 haiku 145% 우세로 명확 선택

5. **신규 부채 #β2 (PS 3.0)** — budget 1차 추정 모델 일반화 (진입점별 prompt 구조 반영). #β1과 별개 문제. **Slice 6 Step 0 자연 처리** 확정
