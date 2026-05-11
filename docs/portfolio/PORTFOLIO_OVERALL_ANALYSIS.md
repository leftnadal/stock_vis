# Portfolio Coach — 전체 종합 재분석

> 작성일: 2026-05-07 (Slice 3 종결 직후)
> 범위: D-시리즈 (D-0a~D-8) + Slice 1/2/3 누적
> 회귀 baseline: 123 passed
> 누적 LLM 호출 (각 슬라이스 reset): Slice 1 10 / Slice 2 32 / Slice 3 15
> 실측 누적 비용: ~$0.49

---

## 1. 진입점 구현 현황 매트릭스

| 진입점 | 정의                    | 입력                          | 출력                                                      | 상태                 | Winner | 비용/호출 | URL                                   |
| ------ | ----------------------- | ----------------------------- | --------------------------------------------------------- | -------------------- | ------ | --------- | ------------------------------------- |
| **E1** | 한 줄 진단 (D-2)        | AnalysisContext               | OneLineDiagnosis (headline + summary)                     | ✅ Slice 1           | haiku  | ~$0.001   | `GET /api/coach/e1/garp/`             |
| **E2** | 진단 카드 4요소 (D-3)   | AnalysisContext               | E2DiagnosticCard (summary + strengths/weaknesses/actions) | ✅ Slice 3           | haiku  | ~$0.003   | `POST /api/coach/e2/diagnostic-card/` |
| E3     | 지표 코멘트 (D-4)       | AnalysisContext               | MetricComments                                            | ⚠️ prompt 스켈레톤만 | —      | —         | (미구현)                              |
| E4     | 대화 Q&A Tier 1~3 (D-5) | 대화 컨텍스트                 | ConversationResponse                                      | ⚠️ prompt 스켈레톤만 | —      | —         | (미구현)                              |
| **E5** | 조정 파싱 (D-6)         | AnalysisContext + 자연어 명령 | E5Response (adjustments[])                                | ✅ Slice 2           | sonnet | ~$0.005   | `POST /api/coach/e5/adjustment/`      |
| E6     | 조정 후 비교 해설 (D-7) | E5 결과 + 원본                | (정의 미완)                                               | ⚠️ prompt 스켈레톤만 | —      | —         | (미구현)                              |

**구현 완료 3 / 진입점 6** — Phase 1 절반 진행. E3/E4/E6은 prompt 디렉토리만 생성된 상태로 schema/service/view 미구현.

---

## 2. 작업 종류 ↔ 모델 Winner 가설 (3 슬라이스 정착)

| Slice | 진입점 | 작업 종류                  | LLM 사용 패턴                        | Winner     | 점수 차이                                        |
| ----- | ------ | -------------------------- | ------------------------------------ | ---------- | ------------------------------------------------ |
| 1     | E1     | **글쓰기** (자연어 생성)   | naturalness + insight                | **haiku**  | label_means 33.68 vs sonnet 13.89 / gemini 13.38 |
| 2     | E5     | **추출** (자연어 → 구조화) | intent_match + no_extra_changes      | **sonnet** | lex_pass 100% vs haiku 85.71%                    |
| 3     | E2     | **글쓰기** (4요소 카드)    | naturalness + insight + completeness | **haiku**  | 31.71 vs sonnet 12.80                            |

**가설**: 작업 종류로 default provider 결정 가능. 글쓰기 = haiku (비용 효율 우세) / 추출 = sonnet (정확도 우세).

**예측 (Phase 2 진입점)**:

- E3 (지표 코멘트) → 글쓰기 차원 → **haiku** 예상
- E4 (대화 Q&A) → 혼합 (Tier별 다름) → Tier 1 추출 sonnet / Tier 2~3 글쓰기 haiku 예상
- E6 (비교 해설) → 글쓰기 + 비교 → **haiku** 예상

---

## 3. 인프라 누적 (3 슬라이스)

### 3.1 LLM 인프라 (`portfolio/llm/`)

| 모듈                   | 역할                                                           | 슬라이스                     |
| ---------------------- | -------------------------------------------------------------- | ---------------------------- |
| `client.py`            | LLMClient (Gemini + Anthropic 통합 wrapper, 폴백 + 1회 재시도) | Slice 1                      |
| `exceptions.py`        | LLMError 계층 (RateLimit/Timeout/Auth/Budget/InvalidPrompt)    | Slice 1                      |
| `mocks.py`             | MockLLMClient + text_strategy (e1/e5/e2)                       | Slice 1, 확장: 2,3           |
| `parsers.py`           | parse_json_response (마크다운 펜스 제거 + Pydantic 검증)       | Slice 1                      |
| **`cost_guard.py`**    | CostGuard (싱글톤, slice 단위 reset, 한도 초과 시 raise)       | **Slice 3 신규 (D3.C)**      |
| **`token_budgets.py`** | ENTRYPOINT_TOKEN_BUDGETS (e1=5000, e5=2000, e2=1500)           | **Slice 3 신규 (백로그 #5)** |

### 3.2 Schema 인프라 (`portfolio/schemas/`)

| 파일                                                                          | 역할                                                                            |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `analysis_context.py`                                                         | AnalysisContext (D-0a) — Pydantic Tier 1                                        |
| `holding.py` / `metric_result.py` / `return_breakdown.py` / `user_profile.py` | 도메인 schemas                                                                  |
| `diagnostic.py`                                                               | DiagnosticCard (D-3 단일 약점, legacy)                                          |
| `llm.py`                                                                      | **LLMResponse + E1/E5/E2 Request/Response + AdjustmentItem + E2DiagnosticCard** |
| `llm_outputs.py`                                                              | E1~E6 출력 schemas (OneLineDiagnosis, MetricComment 등)                         |

### 3.3 Service 인프라 (`portfolio/services/`)

| 모듈                        | 역할                                                            | 슬라이스         |
| --------------------------- | --------------------------------------------------------------- | ---------------- |
| `e1_garp.py`                | E1+GARP Mock 진입 (run_e1_garp)                                 | Slice 1          |
| `e5_adjustment_parser.py`   | E5 자연어 → adjustments                                         | Slice 2          |
| **`e2_diagnostic_card.py`** | E2 4요소 카드                                                   | **Slice 3 신규** |
| **`_llm_kwargs.py`**        | PROVIDER_KWARGS 공유 (백로그 #3 흡수)                           | **Slice 3 신규** |
| **`_prompt_helpers.py`**    | format_holdings/analysis_summary/metrics_table (백로그 #4 흡수) | **Slice 3 신규** |

### 3.4 검증 인프라 (`scripts/validation/`)

| 스크립트                                                              | 역할                                          |
| --------------------------------------------------------------------- | --------------------------------------------- |
| `_setup.py`                                                           | init_django + reset_for_slice                 |
| `diagnose_gemini.py`                                                  | Gemini API 진단 (Slice 2)                     |
| `measure_tokens.py` / `measure_e5_tokens.py` / `measure_e2_tokens.py` | 진입점별 토큰 측정                            |
| `run_step6_*` (smoke/e5/e2)                                           | 각 진입점 1회 실 호출 검증                    |
| `run_step8_3way.py` (Slice 1)                                         | 9 calls (3 fixture × 3 model)                 |
| `run_step8_e5_2way.py` (Slice 2)                                      | 14 calls (gemini 제외)                        |
| `run_step8_e2_2way.py` (Slice 3)                                      | 14 calls + group 분석                         |
| `score_step8.py`                                                      | DIMENSION_LOOKUP (e1/e5/e2) + dispatch 일반화 |
| `score_step8_e5.py`                                                   | E5 산식 별도 (delegation)                     |
| `analyze_e2_groups.py`                                                | Q4 hybrid 검증 (group 비교)                   |
| `reparse_step6.py` / `reparse_step8.py`                               | 재파싱 (마크다운 펜스 사후 처리)              |

### 3.5 Fixture 인프라 (`portfolio/tests/fixtures/`)

| 파일                           | 진입점                                                   | fixture 수 |
| ------------------------------ | -------------------------------------------------------- | ---------- |
| `sample_analysis_context.py`   | E1 (Slice 1) — garp_tech/misfit/large 외                 | 6+         |
| `sample_adjustment_context.py` | E5 (Slice 2) — clear*\*/no_intent*\*/large_multi         | 7          |
| `sample_diagnostic_context.py` | E2 (Slice 3) — slice1_baseline 3 + e2_focused 4 (hybrid) | 7          |

---

## 4. 슬라이스별 패턴 진화 (회귀 + 비용 추세)

| 슬라이스 | 진입점   | 회귀 카운트     | 누적 LLM 호출            | 실측 비용  | Step 9 작업                                        |
| -------- | -------- | --------------- | ------------------------ | ---------- | -------------------------------------------------- |
| Slice 1  | E1       | 0 → 37          | 10/50                    | ~$0.10     | refactor_backlog_slice1.md (Step 9 패턴 슬롯 정립) |
| Slice 2  | E5       | 37 → 76         | 32/50 (1차 14 손실 별도) | ~$0.21     | DIMENSION_LOOKUP + e5 delegation                   |
| Slice 3  | E2       | 76 → **123**    | 15/50 (Q5 reset)         | ~$0.10     | token_budgets.py 상수 도입                         |
| **누적** | 3 진입점 | **+123 테스트** | —                        | **~$0.41** | 6 백로그 항목 처리 (3 흡수 + 1 부분 + 2 이연)      |

### 4.1 회귀 증가 분포

```
Slice 1 (E1):   0 → 37  (+37)  — schema/service/view 기초
Slice 2 (E5):  37 → 76  (+39)  — 7 fixture parametrize 효과
Slice 3 (E2): 76 → 123 (+47)   — hybrid fixture (3+4) + CostGuard + token_budgets
```

### 4.2 슬라이스별 핵심 발견

**Slice 1**:

- haiku winner (글쓰기 차원, 비용 효율 압도적)
- gemini-2.0-flash free tier limit=0 발견 → 2.5-flash 갱신 (Slice 2 Step 0 진단)

**Slice 2**:

- sonnet winner (추출 차원)
- 1차 손실 14건 (set 직렬화) → D4 회피 가이드 정립 (`_json_default` + round-trip)
- DIMENSION_LOOKUP 부분 일반화 (산식 차이로 e5 delegation 결정)

**Slice 3**:

- haiku winner (글쓰기 재확인 — 가설 정착)
- Q4 hybrid 검증 (focused 그룹이 sonnet 차별화에 가치)
- CostGuard 코드 구현 — Slice 단위 자동 reset 메커니즘
- E2 출력 latency 5,000ms 임계 부적절 발견 → Slice 4 16,000ms 상향

---

## 5. 백로그 누적 진행 (Slice 1→2→3 처리 추적)

| #   | 항목                               | PS     | Slice 1   | Slice 2               | Slice 3                                      | 상태                 |
| --- | ---------------------------------- | ------ | --------- | --------------------- | -------------------------------------------- | -------------------- |
| 1   | LLMResponse metadata_dict() 헬퍼   | 3.0    | 추가      | (Slice 1 Step 9 처리) | —                                            | ✅ 완료              |
| 2   | score 산식 통합 (e1+e5+e2)         | 3.0    | —         | 신규 (PS 3.0)         | 이연                                         | ⏳ Slice 4           |
| 3   | PROVIDER_KWARGS 공유               | 2.0    | —         | 신규                  | **Step 2 흡수**                              | ✅ 완료              |
| 4   | prompt_helpers 분리                | 2.0    | —         | 신규                  | **Step 2 흡수**                              | ✅ 완료              |
| 5   | TOKEN_BUDGET 상수 + LLMClient 가드 | 2.0    | —         | 신규                  | **token_budgets 도입 (LLMClient 통합 이연)** | ⏳ 부분              |
| 6   | Step 8 CSV 옵션                    | 1.0    | 신규 (#7) | 이연                  | 이연                                         | ⏳ Slice 4           |
| 7   | Mock mode dict 매핑                | 1.0    | 신규 (#8) | 이연                  | 이연                                         | ⏳ Slice 4           |
| 8   | LLMClient entrypoint 인자          | 2.5    | —         | —                     | 신규                                         | ⏳ Slice 4           |
| 9   | latency 임계 16,000ms 상향         | 2.0    | —         | —                     | 신규                                         | ⏳ Slice 4           |
| 10  | E2 keyword_match 룰 보완           | 1.5    | —         | —                     | 신규                                         | ⏳ Slice 4           |
| 11  | metrics_table 일반화               | 1.5    | —         | —                     | 신규                                         | ⏳ Slice 4           |
| 12  | DiagnosticCard 가중치              | 조건부 | —         | —                     | 신규                                         | ⏳ Slice 5 (Phase 2) |
| 13  | LLM-as-judge                       | 5.0    | —         | —                     | 신규 (Q7)                                    | ⏳ Slice 5 (Phase 2) |

**누적 처리 효율**:

- 완료: 3건 (#1, #3, #4) — 자연 흡수 패턴 효과
- 부분 완료: 1건 (#5) — 슬롯 한도 보존
- 이연: 9건 (Slice 4 5건 + Slice 5 Phase 2 2건 + 기타)

---

## 6. 검증 인프라 일반화 진행

### 6.1 score_step8.py — DIMENSION_LOOKUP 진화

```python
# Slice 2 Step 9에서 도입 (옵션 H — 가벼운 일반화)
DIMENSION_LOOKUP = {
    "e1": {flat 구조, e1 산식, 동적 normalize},      # Slice 1
    "e5": {nested 구조, delegation → score_step8_e5}, # Slice 2 산식 차이
}

# Slice 3 Step 8에서 확장
DIMENSION_LOOKUP["e2"] = {
    "nested 구조",
    "additional_lex_check": "completeness_auto",  # Q3.C 자동 측정
    # 산식: e1 mirror + completeness 1차 필터 추가
    # _main_e2() flatten 후 e1 산식 재사용
}
```

**Slice 4 통합 계획**: e5의 delegation 패턴 정리 + e1/e2 산식을 한 main()으로 통합. PriorityScore 3.0 (60분).

### 6.2 D4 회피 가이드 (1차 손실 재발 방지)

Slice 2에서 발견된 set 직렬화 실패 패턴 → Slice 3 모든 run 스크립트에 의무화:

```python
def _json_default(obj):
    if isinstance(obj, set): return sorted(obj)
    if isinstance(obj, (datetime, date)): return obj.isoformat()
    if isinstance(obj, Decimal): return float(obj)
    raise TypeError(...)

# write 후 read-back round-trip
loaded = json.loads(path.read_text())
assert loaded == data
```

**효과**: Slice 3 14호출 1차 시도 손실 0 (Slice 2는 14건 손실).

### 6.3 CostGuard 멱등 reset (Slice 3 신규)

```python
# scripts/validation/_setup.py
def reset_for_slice(slice_id, max_calls=50):
    guard = CostGuard.get_instance()
    if guard.slice_id != slice_id:  # 멱등
        guard.reset_slice(slice_id, max_calls)
    return guard
```

**효과**: 매 슬라이스 진입 시 한 줄로 자동 카운터 0 시작. Slice 4 진입 시 동일 패턴 사용 가능.

---

## 7. 비용 가드 누적 분석

| 슬라이스 | reset 시점    | 사용             | 마진 | 실측 비용  | Reset 메커니즘          |
| -------- | ------------- | ---------------- | ---- | ---------- | ----------------------- |
| Slice 1  | (수동)        | 10/50            | 40   | ~$0.10     | 인스턴스별 \_call_count |
| Slice 2  | (수동)        | 32/50 (+14 손실) | 18   | ~$0.21     | 인스턴스별 \_call_count |
| Slice 3  | **자동 (Q5)** | 15/50            | 35   | ~$0.10     | **CostGuard 싱글톤**    |
| **누적** | —             | 57 calls         | —    | **~$0.41** | —                       |

**가드 효과**:

- Slice 1/2는 인스턴스 카운터만 — 슬라이스 간 누적 안 됨 (사실상 슬라이스별 50씩 한도)
- Slice 3부터 CostGuard 싱글톤 + reset_for_slice 멱등 패턴으로 자동화
- Slice 4 진입 시 한 줄로 reset, 카운터 0 시작 보장

---

## 8. 미구현 진입점 우선순위 (Slice 4+)

### 8.1 진입점 우선순위 (사용자 가치 + 구현 비용 P×R×S/C)

| 진입점           | 사용자 가치 | 의존성         | 구현 복잡도 | 권장 슬라이스              |
| ---------------- | ----------- | -------------- | ----------- | -------------------------- |
| E6 (비교 해설)   | 중          | E5 산출물 입력 | 중          | **Slice 4** — E5 흐름 통합 |
| E3 (지표 코멘트) | 중          | 단독           | 낮음        | Slice 5                    |
| E4 (대화 Q&A)    | 매우 높음   | Tier 1~3 다층  | 높음        | Slice 6 (Phase 2)          |

### 8.2 권장 슬라이스 4 진입점: **E6**

근거:

- E5(Slice 2)와 자연스러운 흐름 통합 — 사용자 시나리오: 분석 → 명령 → 적용 → 비교 해설
- 글쓰기 작업 (haiku 예상) → token_budgets에 e6 추가 패턴 검증
- score 산식 통합 (#2 백로그 PS 3.0)을 Slice 4 Step 9에서 처리 — e6 산식이 e1/e2 mirror면 자연스러운 통합 케이스

대안 (E3 우선): 단독 진입점이라 의존성 낮으나, E5→E6 흐름 검증 가치 우세.

---

## 9. 코드 품질 지표

| 지표                                         | 값                                | 비고                                  |
| -------------------------------------------- | --------------------------------- | ------------------------------------- |
| Python 파일 수 (portfolio/)                  | 99                                | tests + fixtures + schemas + services |
| Validation 스크립트 수 (scripts/validation/) | 17                                | 슬라이스별 run/measure/score          |
| 테스트 카운트                                | **123 passed**                    | 0 fail                                |
| 회귀 stability                               | Slice 1/2 모두 IDENTICAL (diff 0) | Slice 3 Step 9 검증                   |
| 평균 fixture/슬라이스                        | 7                                 | hybrid 패턴 정립                      |
| 평균 신규 코드/슬라이스                      | ~1,000 줄                         | schema/service/view/test/fixture      |

---

## 10. 슬라이스 4 진입 권장사항

### 10.1 결정 사항

| Q                   | 결정                                                                               |
| ------------------- | ---------------------------------------------------------------------------------- |
| Q1 진입점           | **E6 (조정 후 비교 해설)**                                                         |
| Q2 default provider | **haiku** (글쓰기 가설 적용)                                                       |
| Q3 fixture 전략     | **하이브리드 7개** — Slice 2 E5 fixture (with adjustments) 재활용 + 신규           |
| Q4 평가 차원        | **naturalness + insight + completeness 자동** (E2 mirror)                          |
| Q5 reset            | **CostGuard.reset_slice("slice4")** — 한 줄 자동                                   |
| Q6 score 산식       | **DIMENSION_LOOKUP[e6] 추가 + e1/e2 통합 (#2 백로그 처리)**                        |
| Q7 백로그 처리      | **Slice 4 Step 9 슬롯 = #8 (LLMClient entrypoint, 20분) + #9 (latency 임계, 5분)** |

### 10.2 비용 예산 (50 calls / Slice 단위)

| Step               | 호출 수    | 누적             |
| ------------------ | ---------- | ---------------- |
| Step 6 (haiku 1회) | 1          | 1                |
| Step 7 (오프라인)  | 0          | 1                |
| Step 8 (7×2=14)    | 14         | 15               |
| Step 8 재시도 예비 | ~3         | ~18              |
| Step 9 (리팩토링)  | 0          | ~18              |
| **합계 예상**      | **~18/50** | **안전 마진 32** |

### 10.3 회귀 카운트 예상

```
Slice 3 종결: 123
Slice 4 진입 (CostGuard reset, Mock e6, schema e6, service e6, view e6, fixture):
  Step 0: +5
  Step 1: +6
  Step 2: +6
  Step 3+4: +7
  Step 5: +18
  Step 9 (#8 entrypoint 가드): +5
예상 종결: ~170 passed
```

---

## 부록 A — 디렉토리 트리 (요약)

```
portfolio/
├── llm/             (6 파일 — client/cost_guard/exceptions/mocks/parsers/token_budgets)
├── prompts/         (6 진입점 디렉토리 e1~e6 + tier0)
├── schemas/         (8 파일)
├── services/        (5 파일 — _llm_kwargs/_prompt_helpers/e1_garp/e2_diagnostic_card/e5_adjustment_parser)
├── tests/           (15 테스트 + 5 fixture)
├── views.py         (3 진입점 — coach_e1_garp/coach_e2_diagnostic_card/coach_e5_adjustment)
└── urls.py          (3 path)

scripts/validation/  (17 스크립트 — 슬라이스별 run/measure/score)

docs/portfolio/
├── coach/
│   ├── slice1/      (5 산출물 — Slice 1)
│   ├── slice2/      (7 산출물 — Slice 2)
│   ├── slice3/      (7 산출물 — Slice 3)
│   └── validation_report_d8.md (D-시리즈)
└── instructions/    (Slice 1/2/3 part 1/2 지시서)
```

---

## 부록 B — Slice 3 종결 시점 키 메트릭 요약

| 메트릭              | 값                                                                                   |
| ------------------- | ------------------------------------------------------------------------------------ |
| 진입점 구현         | 3/6 (E1/E2/E5)                                                                       |
| 회귀 테스트         | 123 passed                                                                           |
| 누적 LLM 호출       | Slice 1: 10 / Slice 2: 32 / Slice 3: 15 = **57 / 150 (Slice별 50)**                  |
| 실측 누적 비용      | ~$0.41                                                                               |
| Winner 일관성       | 글쓰기→haiku (Slice 1, 3) / 추출→sonnet (Slice 2) — **3/3 가설 일치**                |
| 백로그 누적 처리율  | 3 완료 + 1 부분 + 9 이연 = 13 항목                                                   |
| Step 9 슬롯 활용률  | Slice 2 100% (DIMENSION_LOOKUP) / Slice 3 50% (token_budgets만, LLMClient 통합 이연) |
| D4 회피 가이드 효과 | Slice 3 1차 손실 0건 (Slice 2 대비 14건 차단)                                        |

# §Slice 4 (E6 — 조정 후 비교 해설) 종결 분석

## 핵심 결과

- **회귀**: 단독 +13 (목표 +8~13) → portfolio 단독 173 passed
- **Step 8 winner**: haiku (efficiency 21.7590 vs sonnet 7.7294, 차이 64.5%)
- **글쓰기 가설**: 4/4 정착 (S1 E1 / S3 E2 / S4 E6 모두 haiku, S2 E5 추출 반례 일관)
- **호출 / 비용**: 15/50 / $0.1576
- **Step 9 IDENTICAL**: Slice 1·3 모두 hash 일치 → \_main_unified 통합 안정성 검증
- **케이스 A~F**: 모두 미발동

## 정책 검증

- **분석 엔진 의존성 회피** 일관 유지 (Part 1 → Part 2). E6 schema는 정량 재계산 미사용, LLM 자연어 추론 위임. Phase 2 백로그 #12로 등록 (PS 5.0)
- **#9 latency 16,000ms 임계 e6 한정 신규 적용** — 기존 5 파일 baseline 보존
- **Step 9 통합 범위 e1/e2/e6 한 \_main_unified() + e5 delegation 유지** — e5 산식 본질 차이 보존

# §종합 — Slice 1~4 누적 추이

## 회귀 증가율

| Slice | 단독 회귀 증가 | 누적 (단독)                           | 진입점          |
| ----- | -------------- | ------------------------------------- | --------------- |
| 1     | +37            | 37                                    | E1 (한 줄 진단) |
| 2     | +49            | 86                                    | E5 (조정 파싱)  |
| 3     | +37            | 123                                   | E2 (4요소 카드) |
| 4     | +37            | 160 (Part 1) → +13 (Part 2) → **173** | E6 (비교 해설)  |

평균 증가율: ~37/slice. Slice 4가 패턴 안정 (Part 1 +37 / Part 2 +13).

## 호출 / 비용 추이

| Slice | 단독 호출                              | 단독 비용                     | 효율 ($/call)     |
| ----- | -------------------------------------- | ----------------------------- | ----------------- |
| 1     | 10 (협의) / 16 (광의)                  | $0.122 (협의) / $0.137 (광의) | $0.0122 / $0.0086 |
| 2     | 18 (협의) / 32 (광의 1차 손실 14 포함) | (재집계 필요) / $0.19         | —                 |
| 3     | 15                                     | $0.10                         | $0.0067           |
| 4     | 15                                     | $0.1576                       | $0.0105           |

**비용 정합 부채** (이슈 γ): Slice 1·2 헤더 vs 본문 차이 추적 + 단일 산출 정책 미확정. Slice 5 Step 0 처리.

## 글쓰기 가설 검증 추이

| Slice | 진입점 | 작업 종류 | Winner     | 가설 외삽                      |
| ----- | ------ | --------- | ---------- | ------------------------------ |
| 1     | E1     | 글쓰기    | **haiku**  | 1/1                            |
| 2     | E5     | 추출      | **sonnet** | 가설 일관 반례 (글쓰기 ≠ 추출) |
| 3     | E2     | 글쓰기    | **haiku**  | 2/2 정착                       |
| 4     | E6     | 글쓰기    | **haiku**  | **4/4 정착** (반례 포함 일관)  |

**결론**: 글쓰기 가설 외삽 위험 해소. Slice 5 preset 외삽 시 default haiku 안전.

## haiku vs sonnet efficiency 격차 추이 (Step 8 label_means)

| Slice | haiku         | sonnet        | 격차 (배수) | 격차 (%) |
| ----- | ------------- | ------------- | ----------- | -------- |
| 1     | 33.68         | 13.89         | 2.42×       | 142%     |
| 3     | (보고 미수신) | (보고 미수신) | —           | —        |
| 4     | 21.7590       | 7.7294        | 2.815×      | 181%     |

추세: 격차 확대 (Slice 1 142% → Slice 4 181%). haiku 우세 견고.

## CostGuard / 호출 마진 추이

- 50/slice 한도 대비 사용률: S1 32% / S2 64% / S3 30% / S4 30%
- Slice 2의 1차 손실 14건 영향으로 단발 피크. 이후 안정 (~15 calls/slice)

## 분석 엔진 의존성 회피 정책 일관성

- Slice 1~4 모두 LLM 자연어 추론 위임. 정량 재계산 미사용
- Phase 2 백로그 #12 (E6 분석 엔진 재계산, PS 5.0)에 누적 위임
- 누적 회피 비용: ~3~5 슬라이스 분량 작업 (Phase 2 단일 슬라이스로 통합 가능 여부 별도 검토)

## Slice 4 종결 시점 누적 백로그

- Slice 5 이연: 6건 (Slice 3 7건 중 #2/#9 처리 차감 + 보고 #10 누락 검증)
- Slice 4 신규: 6건 (#12~#17)
- 검증 단계 신규: 1건 (#18)
- 누적 백로그: ~13건. PS 합 ~21.5

# §Slice 5 진입 결정

- **권장: E3 (preset 외삽 검증)** — 가중합 4.70/5.00 (vs E4 2.40, preset 확장 3.25)
- **Slice 6 사전 등록 후보**: E4 또는 preset 일반화 (Slice 5 종결 시 결정)
- **Slice 5 Step 0 부채 우선순위**: #γ1 (비용 정합) → #β1 (token 휴리스틱)
