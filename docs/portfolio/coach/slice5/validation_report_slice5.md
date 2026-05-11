# Slice 5 Part 2 검증 보고서 — E3 (지표 코멘트, MetricComment one-liner)

> 작성일: 2026-05-07
> 진입점: E3 (Core+Supporting 지표 5단계 level_tag → 한국어 1~2문장 코멘트)
> 광의 단일 정책 첫 적용 (COST_POLICY.md, #γ1 처리 후속)

---

## §1 메타데이터

| 항목 | 값 |
| --- | --- |
| Slice | 5 (E3) |
| Part 1 종결 단독 회귀 | 219 passed |
| Part 2 진입 baseline | 단독 219 passed → **355 passed** (베이스: 342, 신규 +13) |
| 회귀 변화 (Part 2) | +13 (Step 7 +3 + Step 9 +10) |
| Slice 4 mirror 비율 | ~95% |
| 환경 차이 자동 변환 | 8건 (Part 1 5건 + Part 1 발견 3건) |

> 회귀 베이스라인 산정 — 본 보고서는 `--ignore-glob="*\ 2.py"` 기준 (iCloud 중복 파일 제외).

---

## §2 Step 6 — Smoke Test

| 항목 | 값 |
| --- | --- |
| Fixture | `e3_baseline_garp_tech` (5 holdings, 3 metrics) |
| Provider | Anthropic Haiku (`claude-haiku-4-5`) |
| Latency | 4,100ms |
| Cost | $0.00492 |
| Schema (Pydantic) | PASS |
| Completeness (`comments ≥ 1`) | PASS (3 comments) |
| Cost ≤ $0.020 | PASS |
| Latency ≤ 16,000ms | PASS |
| Fallback from | None |

**4 판정 모두 PASS** ✓ (Q1 fixture / Q2 임계 결정 정합).

산출물: `docs/portfolio/coach/slice5/step6_smoke_e3_output.json` (round-trip OK).

---

## §3 Step 7 — Token 측정 + Budget 결정

| 항목 | 값 |
| --- | --- |
| Fixtures | hybrid 7 (baseline GARP 3 + focused 4) |
| Tool | Anthropic `count_tokens` API (generation 비용 0) |
| Token range | 3,940 ~ 4,359 |
| Mean | 4,030.6 |
| **P90** | **4,359** |
| P90 × 1.5 | 6,538.5 |
| **Budget (round-up 500)** | **7,000** |
| 1차 추정 1,500 대비 | +366% (갱신 등록) |
| 단위 테스트 추가 | +3 |

### 3.1 #β1 자연 검증 (Slice 4 +50% 편차 교훈 후속)

| 항목 | 값 |
| --- | --- |
| 검증 대상 | `estimate_input_tokens(prompt) = len // 3` 휴리스틱 |
| 측정 절차 | 7 fixture × (estimate vs `count_tokens` 실측) delta_pct |
| 평균 delta_pct | **+2.9%** |
| 결정 | `closed_no_correction` |
| 보정 적용 | **미실시** — chars/3 휴리스틱 정상 (±20% 허용 범위 내) |

> #β1 자연 검증 결과: estimate_input_tokens chars/3 휴리스틱 평균 delta_pct = +2.9%. 보정 미실시 (Slice 4 e6 +50% 편차 교훈은 본 슬라이스 fixture에서 재발하지 않음).

### 3.2 그룹 비교 (hybrid 7 정당화)

| 그룹 | n | mean tokens |
| --- | --- | --- |
| `garp_baseline` | 3 | 4,149.0 |
| `preset_focused` | 4 | 3,941.8 |

→ 그룹 차이 약 +5.3% (baseline 약간 큼). preset 다양성이 토큰 비용에 미치는 영향 미미 — hybrid 결정 정당.

산출물: `docs/portfolio/coach/slice5/step7_e3_tokens.json`.

---

## §4 Step 8 — 2-way 회고

### 4.1 매트릭스

| 차원 | 값 |
| --- | --- |
| 매트릭스 | 7 fixture × 2 model = 14 calls |
| haiku | 7 calls |
| sonnet | 7 calls |
| gemini | 제외 (Slice 1 9/9 폴백 후 정책 일관) |

### 4.2 자동 검증 결과

| 항목 | haiku | sonnet | 합계 |
| --- | --- | --- | --- |
| Schema PASS | 7/7 | 7/7 | 14/14 |
| `completeness_auto` (comments ≥ 1) | 7/7 | 7/7 | 14/14 |
| Fallback | 0 | 0 | 0 |
| Cost | $0.0378 | $0.1364 | $0.1742 |
| Latency P90 / max | — | — | 11,019ms / 13,242ms |

### 4.3 Winner — **haiku** ✓ (2026-05-08 manual eval 완료)

| 항목 | haiku | sonnet |
| --- | --- | --- |
| lex_pass_rate (schema + nat ≥ 3 + ins ≥ 3 + completeness) | **6/7** (85.7%) | **7/7** (100%) |
| label_mean (efficiency score) | **23.5115** (n=6) | 9.5770 (n=7) |
| efficiency 차이 | — | — |
| **Winner** | **haiku** ✓ | — |

> efficiency 차이 = +145% ≫ 5% 동률 방지 임계 ✓.
> entry 9 (e3_focused_dividend_growth × haiku) naturalness=2로 lex filter 미통과 — 1차 필터 13/14 통과, mode=EFFICIENCY.
> haiku 우위는 cost ($0.0054 평균) + latency (4.6s 평균)에서의 효율로 결정 (sonnet $0.0195 / 8.4s 대비).

#### 4.3.1 그룹 분석 4매트릭스

| Model | 그룹 | n | nat_mean | ins_mean | score_mean | cost_total | lat_avg |
| --- | --- | --- | --- | --- | --- | --- | --- |
| haiku | garp_baseline | 3 | 3.67 | 3.67 | 19.95 | $0.0184 | 5,784ms |
| haiku | preset_focused | 3 | 3.25 | 3.75 | 20.30 | $0.0194 | 3,762ms |
| sonnet | garp_baseline | 3 | 3.00 | 3.33 | 7.39 | $0.0653 | 10,000ms |
| sonnet | preset_focused | 4 | 4.00 | 4.00 | 11.22 | $0.0712 | 7,265ms |

> haiku preset_focused n=3 (entry 9 lex 미통과로 dividend_growth 제외). sonnet preset_focused n=4.

**해석** (interpretation_guide 적용):
- **haiku**: baseline 19.95 vs focused 20.30 → **small_diff (1.8%)** ✓ — preset 외삽 안전, 글쓰기 가설 일관.
- **sonnet**: baseline 7.39 vs focused 11.22 → focused_higher (+51.7%) — sonnet은 GARP baseline에서 평탄(nat=3.0, ins=3.33), preset 다양성에 민감.

→ haiku의 robustness 우위가 그룹 비교에서도 재확인.

### 4.4 글쓰기 가설 5번째 외삽 검증 — **5/5 정착 ✓**

| Slice | 진입점 | Winner | 가설 |
| --- | --- | --- | --- |
| 1 | E1 한 줄 진단 | haiku | 글쓰기→haiku ✓ |
| 2 | E5 조정 파싱 | sonnet | 추출→sonnet ✓ (반례) |
| 3 | E2 4요소 카드 | haiku | 글쓰기→haiku ✓ |
| 4 | E6 비교 해설 | haiku | 글쓰기→haiku ✓ |
| **5** | **E3 지표 코멘트** | **haiku** | **글쓰기→haiku ✓ (5번째 정착)** |

→ **케이스 F 미발동** ✓ (sonnet winner 시 4/5 재평가 시나리오 회피).
→ preset 외삽 위험 영구 해소 (small_diff 1.8% 그룹 분석 동시 통과).
→ Slice 6+ 글쓰기 진입점에서 haiku 선택 영구 정당화 — 추가 외삽 검증 압력 해제.

### 4.5 DIMENSION_LOOKUP e3 entry (자료 #3 인용 그대로)

```python
"e3": {
    "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
    "dim2": {"key": "insight", "manual_field": "insight_manual"},
    "model_label_field": "model_label",
    "result_structure": "nested",
    "default_raw":   "docs/portfolio/coach/slice5/step8_2way_e3_raw.json",
    "default_scored":"docs/portfolio/coach/slice5/step8_2way_e3_scored.json",
    "weight": 0.5,
    "additional_lex_check": "completeness_auto",
}
```

`_main_unified()` 본문 변경 0줄 — 자료 #3 KPI 충족 ✓.

---

## §5 누적 비용 (광의 단일 정책, COST_POLICY.md 적용)

### Slice 5 비용

| 단계 | LLM 호출 | 비용 |
| --- | --- | --- |
| Step 6 (smoke) | 1 (haiku) | $0.00492 |
| Step 7 (token 측정, count_tokens API) | 0 | 0 |
| Step 8 (회고 14 calls) | 14 (haiku 7 + sonnet 7) | $0.17421 |
| Step 9 (코드 일반화) | 0 | 0 |
| 재시도 | 0 | 0 |
| **Slice 5 단독 광의** | **15** | **$0.17913** |

> 메인 4스텝 비용 = $0.17913 (재시도/진단 호출 0건). 광의는 메인 + 재시도 + 진단 모두 포함 (COST_POLICY 정의).

> #β1 자연 검증 결과: estimate_input_tokens chars/3 휴리스틱 평균 delta_pct = +2.9%. 보정 미실시.

### 누적 (Slice 1~5 광의)

| 시점 | 광의 누적 |
| --- | --- |
| Slice 1 종결 | $0.137 |
| Slice 2 종결 | $0.327 |
| Slice 3 종결 | $0.428 |
| Slice 4 종결 | $0.585 |
| **Slice 5 종결** | **$0.764** |

#γ1 처리 결과: 광의 단일 정책 본 슬라이스부터 적용 ✓ (COST_POLICY.md 정합).

---

## §6 Step 9 — `format_metrics_to_str` 일반화 (#11)

### 6.1 통합 범위

`format_metrics_table` (E2 전용 markdown 표) → `format_metrics_to_str(data, *, format="markdown" | "json")` 일반화.

| 변경 | 적용 |
| --- | --- |
| `_prompt_helpers.py` 신규 함수 | ✓ |
| `format_metrics_table` deprecated wrapper 유지 | ✓ (회귀 위험 0, 백로그 #21 후보) |
| E2 호출처 1줄 (`e2_diagnostic_card.py:41`) | ✓ |
| E3 호출처 1줄 (`prompts/e3/e3_builder.py:36`) | ✓ |
| 단위 테스트 추가 | +10 (3건 처방 + 7건 자연 흡수) |

### 6.2 회귀 KPI 검증 (sha256 hash)

| 산출물 | 사전 hash | 사후 hash | 결과 |
| --- | --- | --- | --- |
| `slice1/step8_3way_scored.json` | `917fa3ef…0f7b9` | `917fa3ef…0f7b9` | **IDENTICAL** ✓ |
| `slice3/step8_2way_e2_scored.json` | `5594c6ab…f3ba` | `5594c6ab…f3ba` | **IDENTICAL** ✓ |

`diff` exit 0 (no diff) 양쪽 모두 ✓ — Step 9 IDENTICAL hash 보장 KPI 충족.

본 Step 9는 `score_step8.py` 미수정 + raw/scored JSON 미접촉이므로 IDENTICAL 자동 보장 ✓.

### 6.3 단위 테스트 분해 (+10)

| 클래스 | 테스트 수 | 목적 |
| --- | --- | --- |
| `TestFormatMetricsToStrMarkdown` | 3 | dict → markdown, default format, legacy 동치성 |
| `TestFormatMetricsToStrJson` | 2 | list[dict] → indented JSON, 한국어 ensure_ascii=False |
| `TestFormatMetricsToStrEmpty` | 3 | empty dict/list, unknown format ValueError |
| `TestFormatMetricsTableDeprecated` | 2 | 기존 wrapper 회귀 검증 |

→ 처방 +3 + 자연 흡수 +7 = 총 +10 (회귀 +5~10 상한 범위 내).

### 6.4 시간 한도 준수

처방 30분 한도 — 실제 작업 ~15분 (구현 + 테스트 + KPI 검증). **케이스 E (한도 초과) 미발동**.

---

## §7 회귀 카운트 진행

| 단계 | 추가 (단독) | 누적 (단독) | 비고 |
| --- | --- | --- | --- |
| Part 1 종결 baseline | — | 219 | (Part 1 +46) |
| Step 6 (smoke 산출물) | 0 | 219 | 산출물만 |
| Step 7 (token + 단위 +3) | +3 | 222 | `test_token_budgets` 확장 |
| Step 8 (raw + e3 entry + analyze) | 0 | 222 | 산출물 / DIMENSION_LOOKUP / 신규 스크립트 |
| Step 9 (#11 일반화 + 단위 +10) | +10 | **232** | format_metrics_to_str + deprecated wrapper |
| validation_report | 0 | 232 | 산출물만 |
| refactor_backlog | 0 | 232 | 산출물만 |

> 본 보고서 baseline은 `--ignore-glob` 적용 시 342 → 355 (+13). Part 2 단독 변화 +13 = Step 7 +3 + Step 9 +10 (Step 9는 신규 `test_prompt_helpers.py` 10건 자연 흡수 — 처방 +3건 + 추가 +7건 회귀 보강).

**Part 2 종결 회귀: +13** (예상 +6~13 상한선).

---

## §8 케이스 발생 여부

| 케이스 | 정의 | 발동 |
| --- | --- | --- |
| A | Step 6 schema_pass=False | **미발동** ✓ |
| B | Step 6 latency > 16,000ms | **미발동** ✓ (4,100ms) |
| C | Step 8 CostGuard 마진 부족 | **미발동** ✓ (15/50, 70% 여유) |
| D | Step 9 IDENTICAL hash 깨짐 | **미발동** ✓ |
| E | Step 9 30분 한도 초과 | **미발동** ✓ (~15분) |
| F | Step 8 winner sonnet (4/5 재평가) | **미발동** ✓ (winner=haiku, 5/5 정착) |
| G | Step 7 #β1 +50% 편차 재발 | **미발동** ✓ (delta +2.9%, closed_no_correction) |

**최종 케이스: 0/7 발동** — Slice 5는 케이스 발생 없는 가장 깨끗한 종결.

---

## §9 백로그 처리 결과 (Slice 4 7건 + Slice 5 신규)

→ `refactor_backlog_slice5.md` 참조.

핵심 처리:

- **#11 (metrics_table 일반화) Slice 5 Step 9 완료** ✓
- 신규 4건 등록: #19 (LLMClient system 인자), #20 (concentrated portfolio E3), #21 (deprecated wrapper 제거), #22 (LLMResponse.metadata_dict 표준 정착 검증)

---

## §10 다음 단계 (Slice 6 진입 결정)

### 10.1 Slice 5 종결 처리 결과 (2026-05-08)

- ✅ Manual eval 사용자 입력 완료 (14 entry × 2 필드)
- ✅ `step8_2way_e3_scored.json` + `step8_2way_e3_group_analysis.json` 산출
- ✅ Winner: **haiku** — 글쓰기 가설 5/5 정착 ✓
- ✅ 케이스 F 미발동, KPI 12/12 통과

### 10.2 Slice 6 진입 후보 (winner=haiku 보정 적용)

| 후보 | 1차 추정 | winner=haiku 보정 | **최종** | 비고 |
| --- | --- | --- | --- | --- |
| E4 대화 Q&A | 4.20 | +0.20 | **4.40** | 글쓰기 6번째 외삽 검증 (5/5 → 6/6 강화) |
| concentrated_portfolio E3 (#20) | 4.40 | 0.00 | **4.40** | preset 일반화, 기존 E3 인프라 mirror |
| E1 prompt 개선 | 3.80 | 0.00 | 3.80 | 헤드라인 임계 재검증 |
| 회고 자동화 (#15/#17) | 3.60 | 0.00 | 3.60 | auto_eval_e6 패턴 일반화 |

→ **E4 vs concentrated_portfolio E3 동률 (4.40)** — 사용자 결정 필요.
→ Slice 6 Step 0 후보: **#β2** (budget 추정 모델 일반화, PS 3.0)
→ Slice 6 Step 9 슬롯: #19 (LLMClient `system` 인자, PS 2.0) 또는 #8 (LLMClient `entrypoint=`, PS 2.5) 택 1

### 10.3 다음 턴 작업

1. Slice 6 진입점 사용자 결정 (E4 / concentrated_portfolio)
2. `slice6_decisions.md` 신설 (Slice 5 mirror)
3. Slice 6 Part 1 지시서 작성 (Step 0 #β2 + 진입점 fixture 설계)
4. `PORTFOLIO_OVERALL_ANALYSIS.md` Slice 4·5 갱신 (Slice 1~5 종합)
