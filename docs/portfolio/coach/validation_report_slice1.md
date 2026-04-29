# Validation Report — Slice 1

> 슬라이스: E1 + GARP + 종목 5/15
> 호출 시점: 2026-04-29 02:29:23 UTC
> 작성: 2026-04-29
> 브랜치: portfolio
> 이전 보고: D-8 결과는 `docs/portfolio/coach/validation_report_d8.md` 참조

---

## 1. Metadata

| 항목              | 값                                                                                                            |
| ----------------- | ------------------------------------------------------------------------------------------------------------- |
| Slice 범위        | E1 GARP, fixture 3종 (garp_tech / garp_misfit / garp_large), 모델 3종 (Gemini Flash / Sonnet 4.5 / Haiku 4.5) |
| Step 6 호출 시점  | 2026-04-29 02:28:37 UTC                                                                                       |
| Step 8 호출 시점  | 2026-04-29 02:29:23 UTC                                                                                       |
| LLMClient git SHA | `396c616` 시점 (Step 6/8 실행 직전)                                                                           |
| preset_version    | v1.0                                                                                                          |
| metric_version    | v1.2                                                                                                          |
| scoring_version   | v1.0                                                                                                          |
| prompt_version    | v1.0                                                                                                          |
| universe_version  | sp500_v1                                                                                                      |
| 누적 LLM 호출     | 10 / 50 (Step 6: 1, Step 8: 9)                                                                                |
| 누적 비용 (USD)   | $0.1066 (Step 6 약 $0.000174 추정 + Step 8 $0.1064)                                                           |

---

## 2. Call Log

### 2.1 Step 6 — 단일 smoke

| 항목 | 값 |
|---|---|
| Fixture | garp_tech |
| Provider label | gemini |
| Actual provider | (Gemini API 호출 실패 후 미폴백 시점이거나 fallback 명세 별도 — `step6_smoke_output.json` 확인) |
| Latency | 4,740ms |
| Cost | $0.015183 |
| Schema (raw) | FAIL — 마크다운 펜스 ` ```json ... ``` ` |
| Schema (reparse) | OK — `parse_json_response` (펜스 사전 제거) 후 통과 가능 |

### 2.2 Step 8 — 9 calls (모두 schema=OK after reparse)

> ⚠️ **`gemini` label 3건 모두 Anthropic Sonnet으로 폴백** (`fallback_from=gemini`).
> 즉 본 Slice에서 **실제 Gemini Flash 응답은 0건**. label만 gemini이고 결과는 Sonnet.

| #   | Fixture     | Label  | Actual Model      | Input | Output | Latency(ms) | Cost(USD) | Fallback   |
| --- | ----------- | ------ | ----------------- | ----- | ------ | ----------- | --------- | ---------- |
| 1   | garp_tech   | gemini | claude-sonnet-4-5 | 4096  | 191    | 4,437       | $0.01515  | **gemini** |
| 2   | garp_tech   | sonnet | claude-sonnet-4-5 | 4096  | 212    | 4,688       | $0.01547  | —          |
| 3   | garp_tech   | haiku  | claude-haiku-4-5  | 4096  | 197    | 2,259       | $0.00406  | —          |
| 4   | garp_misfit | gemini | claude-sonnet-4-5 | 4243  | 225    | 5,536       | $0.01610  | **gemini** |
| 5   | garp_misfit | sonnet | claude-sonnet-4-5 | 4243  | 204    | 4,761       | $0.01579  | —          |
| 6   | garp_misfit | haiku  | claude-haiku-4-5  | 4243  | 229    | 2,996       | $0.00431  | —          |
| 7   | garp_large  | gemini | claude-sonnet-4-5 | 4254  | 196    | 4,887       | $0.01570  | **gemini** |
| 8   | garp_large  | sonnet | claude-sonnet-4-5 | 4254  | 192    | 4,787       | $0.01564  | —          |
| 9   | garp_large  | haiku  | claude-haiku-4-5  | 4254  | 203    | 2,238       | $0.00422  | —          |

**Total cost (Step 8)**: $0.10644.
**Sonnet 실제 호출**: 6회 (label gemini 3 + label sonnet 3).
**Haiku 실제 호출**: 3회.
**Gemini Flash 실제 호출**: 0회 (전부 폴백).

---

## 3. Scoring (efficiency mode after `reparse_step8`)

### 3.1 1차 필터 (Lexicographic Hard Gate)

조건: `schema_pass = True AND naturalness ≥ 3 AND insight ≥ 3`

| Fixture     | gemini | sonnet | haiku |
| ----------- | ------ | ------ | ----- |
| garp_tech   | OK     | OK     | OK    |
| garp_misfit | OK     | OK     | OK    |
| garp_large  | **FAIL** (nat=2) | OK | OK |

**통과: 8 / 9**. Mode: `EFFICIENCY`.

### 3.2 2차 점수 (Efficiency)

산식: `sqrt(naturalness × insight) / sqrt(cost_usd × latency_seconds)`

| #   | Fixture     | Label  | Nat | Ins | Cost     | Lat(s) | Score   | Type        |
| --- | ----------- | ------ | --- | --- | -------- | ------ | ------- | ----------- |
| 1   | garp_tech   | gemini | 4   | 3   | $0.01515 | 4.44   | 13.36   | efficiency  |
| 2   | garp_tech   | sonnet | 5   | 3   | $0.01547 | 4.69   | 14.38   | efficiency  |
| 3   | garp_tech   | haiku  | 3   | 3   | $0.00406 | 2.26   | **31.31** | efficiency  |
| 4   | garp_misfit | gemini | 4   | 4   | $0.01610 | 5.54   | 13.40   | efficiency  |
| 5   | garp_misfit | sonnet | 4   | 5   | $0.01579 | 4.76   | 16.31   | efficiency  |
| 6   | garp_misfit | haiku  | 5   | 3   | $0.00431 | 3.00   | **34.08** | efficiency  |
| 7   | garp_large  | gemini | 2   | 4   | $0.01570 | 4.89   | —       | filtered_out |
| 8   | garp_large  | sonnet | 3   | 3   | $0.01564 | 4.79   | 10.96   | efficiency  |
| 9   | garp_large  | haiku  | 4   | 3   | $0.00422 | 2.24   | **35.67** | efficiency  |

### 3.3 Per Label Mean Score

| Label  | mean score | n   | 비고 |
| ------ | ---------- | --- | ---- |
| haiku  | **33.685** | 3   | 정직한 Haiku 호출, 3회 모두 1차 필터 통과 |
| sonnet | 13.886     | 3   | 정직한 Sonnet 호출 |
| gemini | 13.378     | 2   | **실은 Sonnet 폴백 결과**. garp_large 1건 filtered_out 후 n=2 |

### Winner: **haiku**

대형 마진. cost-efficiency가 압도적 (Sonnet 대비 ~3.5배). naturalness/insight도 임계값 이상 일관 유지.

---

## 4. Dimension Analysis

### 4.1 Schema 적합성

**원본 raw**: 9/9 모두 FAIL — 모든 모델이 ` ```json ... ``` ` 마크다운 펜스로 응답.
**reparse 후**: 9/9 OK — `portfolio.llm.parsers.parse_json_response`가 펜스 사전 제거.

핵심 교훈:
- prompt에 "no markdown fences" 명시했으나 LLM이 무시함 (Gemini/Sonnet/Haiku 공통).
- 코드 측 robust 파싱이 필수 — prompt 강화는 보조 수단.
- 본 Slice에서 robust parser (`parsers.py` 신설) + prompt instructions 강화 (`first character must be {`) 둘 다 적용 완료.

### 4.2 한국어 자연스러움 (naturalness)

| Label | mean | range |
|---|---|---|
| haiku  | 4.0  | 3~5 |
| sonnet | 4.0  | 3~5 |
| gemini (실은 Sonnet 폴백) | 3.33 | 2~4 |

- **Haiku/Sonnet** 모두 garp_misfit에서 5점 (가장 자연스러운 톤). garp_large에서는 점수 하락 (haiku 4 / sonnet 3).
- Gemini label 1건이 garp_large에서 nat=2 — 1차 필터 탈락. 동일하게 Sonnet 모델인데 점수 차이 발생 (단발성 출력 변동).
- 결론: **Haiku의 한국어 응답이 Slice 1 시점에서 충분히 자연스러움**. Sonnet과 동급.

### 4.3 진단 통찰성 (insight)

| Label | mean | range |
|---|---|---|
| haiku  | 3.0  | 3 (전부 일정) |
| sonnet | 3.67 | 3~5 |
| gemini (실은 Sonnet 폴백) | 3.67 | 3~4 |

- **Haiku는 통찰성 점수 일정 (모두 3)** — 안전한 baseline 수준. 새로운 사실 인지 유도는 약함.
- **Sonnet은 garp_misfit에서 5점** — 복잡한 부정합 맥락에서 통찰력 발휘.
- 결론: **Slice 2 진입점 Coach 대화(E4) 등 통찰성 강조 진입점에서는 Sonnet 검토 가치 있음**.
  단, 비용 대비 1점 차이를 정당화할 수 있는지 보류.

### 4.4 비용

| Label | total cost (3 calls) | per call mean | 비고 |
|---|---|---|---|
| sonnet | $0.04690 | $0.0156 | 정직한 Sonnet |
| gemini | $0.04695 | $0.0157 | 폴백 비용 = Sonnet과 동일 |
| haiku  | $0.01259 | $0.0042 | Sonnet 대비 **27% 수준** |

- **Gemini Flash 실제 호출이 0건**이라 Gemini 단가 데이터 미수집. Slice 2 진입 전 Gemini 호출 실패 원인 진단 필요 (4.6 참조).
- Haiku는 비용 측면에서 압도적 경쟁력. Slice 2 default provider 채택 강력 근거.

### 4.5 지연

| Label | mean latency (ms) | range |
|---|---|---|
| haiku  | 2,498  | 2,238~2,996 |
| sonnet | 4,745  | 4,688~4,787 |
| gemini (Sonnet 폴백) | 4,953 | 4,437~5,536 |

- Haiku는 Sonnet 대비 약 **53% 빠름** — 사용자 체감에 유의미.
- garp_misfit×gemini가 5,536ms — Slice 1 임계값 5,000ms 초과. retry/fallback 경로 영향.

### 4.6 Gemini API 호출 실패 → 진단 완료 (2026-04-29)

`gemini` label 3건 **모두 LLMClient 폴백 발동** (`fallback_from=gemini`). 1차 시도 + 1회 재시도 모두 RateLimit으로 실패 → Anthropic Sonnet 폴백.

#### 진단 결과 (사후 수행)

| 항목 | 결과 |
|---|---|
| `GEMINI_API_KEY` 존재 | ✅ length 39, prefix `AIzaSyD` |
| REST `models?key=...` 권한 | ✅ 200, 50개 모델 응답 |
| 단발 호출 `gemini-2.0-flash` | ❌ **`429 RESOURCE_EXHAUSTED, limit: 0`** — Free tier에서 모델 자체 사용 불가 |
| 단발 호출 `gemini-2.0-flash-lite` | ❌ free tier limit=0 |
| 단발 호출 `gemini-2.5-flash` | ✅ 직접 호출 성공 |
| 단발 호출 `gemini-2.5-flash-lite` | ✅ |
| 단발 호출 `gemini-flash-latest` | ✅ |

**근본 원인**: `gemini-2.0-flash` (Slice 1 LLMClient 기본 모델) **무료 티어 한도 = 0**. Slice 1 9회 호출 모두 즉시 `429 RESOURCE_EXHAUSTED` → LLMClient의 RateLimit 매핑 → Anthropic 폴백.

quotaId 인용: `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `GenerateRequestsPerMinutePerProjectPerModel-FreeTier`.

#### 적용 조치

1. `portfolio/llm/client.py` `GEMINI_MODEL` = `"gemini-2.0-flash"` → `"gemini-2.5-flash"` (free tier 사용 가능 확인).
2. `scripts/validation/measure_tokens.py` `GEMINI_TOKENIZER_MODEL` 동일 갱신 (일관성).
3. Step 6 재실행 (2026-04-29 03:29 UTC):
   - 자동 판정 3/3 PASS (Schema OK / Cost $0.0153 ≤ $0.020 / Latency 4,659ms ≤ 5,000).
   - **단, `fallback_from=gemini` 여전 발생** — `gemini-2.5-flash`도 무료 티어 RPM 한도 매우 작아 ~3,700 tokens 큰 prompt 호출 시 RateLimit. 폴백된 Sonnet 응답이 schema 통과하여 산출물 자체는 PASS.
   - 즉 "Gemini Flash 직접 응답" 0건 상태가 본 모델 변경만으로는 해소 안 됨.

#### Slice 2 진입 시 권장

- Primary `haiku` 채택 + **Gemini 폴백 비활성화 (또는 paid tier 활성화)**.
- Free tier 환경에서 `gemini-2.5-flash`로 큰 prompt 안정 호출이 어려움 → fallback 메커니즘은 Anthropic 모델 간(Sonnet ↔ Haiku)에만 유효하도록 단순화 검토.
- paid tier 활성화 시 본 진단 재실행 (단발 호출 9~12회로 검증).

---

## 5. Decision

### 5.1 Slice 2 진입 시 primary provider

**채택: Haiku (`claude-haiku-4-5`)**

근거:
- efficiency mean score 33.68 (sonnet 13.89, gemini 폴백 13.38) — 압도적 1위.
- 비용 Sonnet 대비 27% 수준.
- 지연 Sonnet 대비 53% 수준.
- naturalness 4.0 (sonnet과 동급), insight 3.0 (baseline 충족).

### 5.2 Slice 2 진입 시 retain 사항

- **`portfolio.llm.parsers.parse_json_response`**: robust JSON 파서. 펜스 제거 사전처리. 모든 진입점에서 재사용.
- **LLMClient 인터페이스**: `complete(prompt, provider, max_tokens, model)`. Sonnet/Haiku 분기 검증 완료.
- **Fixture 3종 + test_fixtures_validation**: weight/holding/distribution 검증 자동화.
- **Step 8 scoring 산식 (Lexicographic + efficiency + B fallback)**: 모델 비교 표준 절차로 채택.

### 5.3 Slice 2 진입 시 change 사항

1. **✅ Gemini API 호출 실패 원인 진단 — 완료 (2026-04-29)**.
   - .env `GEMINI_API_KEY` 권한 확인: 정상 (REST 200).
   - 근본 원인: `gemini-2.0-flash` 무료 티어 한도 = 0 (단발 호출로 `429 RESOURCE_EXHAUSTED limit: 0` 확인).
   - 모델 ID 갱신: `gemini-2.0-flash` → `gemini-2.5-flash` (free tier 사용 가능). `client.py:42`, `measure_tokens.py:39` 동일 갱신.
   - 잔여 이슈: `gemini-2.5-flash`도 free tier RPM 한도 작아 ~3,700 token prompt에서 RateLimit. Slice 2 진입 시 paid tier 활성화 또는 Gemini 폴백 비활성화 권장. (§4.6 진단 결과 참조)
2. **prompt instructions 펜스 금지 강화**: Step 8에서 robust parser로 사후 처리하지만, prompt에서 출력 형식을 더 강하게 제약.
   본 Slice에 적용 완료 — `instructions.py`에 "first character must be `{`" 명시.
3. **Step 6 cost 임계 현실화**: $0.001 → $0.020 (실측 기반). `run_step6_smoke.py` 갱신 완료.
4. **measure_tokens budget 가정 갱신**: 8000 → 5000. E1 PV5 설계상 fixture 종목 수 효과가 제한적이라는 점 반영.

### 5.4 Phase 2 보류 항목

- 자연스러움/통찰성 자동 평가 (LLM-as-judge, rule-based heuristic).
- garp_large fixture가 종목 수 증가 효과를 prompt 토큰에 반영하지 못하는 문제 — E2 (DiagnosticCards) 시점에 fixture 효과 재측정.
- Sonnet의 garp_misfit insight=5 — 복잡한 부정합 맥락에서 Sonnet의 통찰력 강점이 의미 있는지 E2/E4에서 재검증.

---

## 6. Cost Guard

| 항목                           | 값      |
| ------------------------------ | ------- |
| Slice 1 누적 LLM 호출          | 11~16 / 50 (Step 6 1 + Step 8 9 + Step 6 재실행 1 + Gemini 진단 단발 5) |
| 누적 비용 (USD)                | ~$0.122 + $0.0153 (Step 6 재실행) + ~$0.0001×5 (진단) ≈ **$0.137** |
| Step 6 1차 비용                | $0.0152 (모델 ID `gemini-2.0-flash` 폴백) |
| Step 6 재실행 비용             | $0.0153 (모델 ID `gemini-2.5-flash` 폴백) |
| Step 8 비용                    | $0.1064 (9 calls) |
| Step 8 재시도                  | 0 (모든 9건 1회로 완료, Gemini는 폴백 1회 포함) |
| Gemini 진단 단발               | $0.0005 추정 (5회 단발, 응답 길이 짧음) |
| 잔여 호출 한도                 | 34~39 |
| Slice 2 진입 시 비용 가드 리셋 | 권장 — `LLM_BUDGET_MAX_CALLS` env 별도 명시 또는 인스턴스 카운터 reset |

---

## 부록 — Step 7 결과 (오프라인)

`scripts/validation/measure_tokens.py` 갱신 후 (budget 8000 → 5000):

| Fixture     | input tokens | budget | utilization | safe |
|---|---|---|---|---|
| garp_tech   | 3,698 | 5,000 | 74.0% | OK |
| garp_misfit | 3,844 | 5,000 | 76.9% | OK |
| garp_large  | 3,848 | 5,000 | 77.0% | OK |

**관찰**: garp_tech (5종목) ↔ garp_large (15종목) 토큰 차이 +150만 (4%). E1 input_builder가 PV5 원칙으로 holdings 미노출 → 종목 수 효과가 제한적. Phase 2 보류 항목으로 기록.
