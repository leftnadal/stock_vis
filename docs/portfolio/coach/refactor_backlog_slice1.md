# Refactor Backlog — Slice 1

> 작성일: 2026-04-29
> 작성 시점: Slice 1 Part 2 Step 6~8 회고 직후, Step 9 30분 슬롯 진입 전.
> 산식: `PriorityScore = (CostSaving × Frequency) / (RiskOfBreakage × TimeRequired)`
> TimeRequired 단위: 1=~5분, 5=~30분. 합산 ≤ 5 까지 Slice 1 적용.

---

## Candidates (PriorityScore 내림차순)

| # | 항목 | CostSaving | Frequency | RiskOfBreakage | TimeRequired | PriorityScore | Slice 1? |
|---|------|------------|-----------|----------------|--------------|---------------|----------|
| 1 | **`portfolio.llm.parsers.parse_json_response` 신설** — 모든 진입점이 마크다운 펜스 제거를 거치도록 표준화. Slice 1에서 Step 6/8 schema FAIL 9/9 의 근본 원인. | 5 | 5 | 1 | 1 | 25.0 | **DONE** |
| 2 | **prompt instructions 출력 규칙 강화** — `instructions.py`에 "first character must be `{`" 명시. Slice 2 호출부터 효과. | 4 | 5 | 1 | 1 | 20.0 | **DONE** |
| 3 | **Anthropic 단가 dict 매핑** — Sonnet/Haiku 분기를 `_ANTHROPIC_PRICING` dict로. Step 8 진입 조건이었음. | 4 | 4 | 1 | 1 | 16.0 | **DONE** |
| 4 | **scripts/validation django boilerplate 공통화** — 4개 스크립트 모두 `os.environ.setdefault + django.setup()` 동일 6줄 반복. `scripts/validation/_setup.py`에 추출. | 2 | 4 | 1 | 1 | 8.0 | YES |
| 5 | **LLMResponse → metadata dict 변환 헬퍼** — `services/e1_garp.py`와 `run_step6_smoke.py`/`run_step8_3way.py`가 동일하게 `provider/model/latency_ms/...` 7개 필드 수동 추출. `LLMResponse.metadata_dict()` 메서드. | 2 | 3 | 2 | 1 | 3.0 | YES |
| 6 | **measure_tokens budget 환경변수화** — Slice 1에서 8000 → 5000 갱신. Slice 2/3에서 또 갱신될 가능성. `LLM_E1_INPUT_BUDGET` env로 분리. | 2 | 2 | 1 | 1 | 4.0 | YES |
| 7 | **Step 8 CSV 출력 옵션** — raw json은 평가 입력용, 사람이 보기 좋은 CSV가 별도 필요. score_step8에 `--csv` 플래그. | 2 | 2 | 2 | 2 | 1.0 | NO |
| 8 | **Mock LLMClient의 mode 분기를 dict 매핑** — 현재 if-elif 5단. 가독성 미미한 향상. | 1 | 2 | 2 | 1 | 1.0 | NO |
| 9 | **Gemini 호출 실패 진단 로깅** — `_classify_gemini_error`가 raw 에러 문자열을 디버그 로그로 남기지 않음. Slice 1에서 9/9 Gemini 폴백 원인 파악 못 함. | 4 | 4 | 2 | 2 | 4.0 | NO (Slice 2 Blocker) |

> #1, #2, #3은 Step 6~8 진행 중 이미 적용됨 (가장 시급한 회귀 차단).

---

## Applied in Slice 1 (Step 9 슬롯)

| # | 항목 | Commit (예정) | 회귀 결과 | 소요 시간 |
|---|------|---------------|-----------|-----------|
| 1 | `parsers.parse_json_response` + service/scripts 적용 | (slice 1 part 2 commit 포함) | 37 passed | 5분 |
| 2 | prompt instructions 펜스 금지 강화 | (slice 1 part 2 commit 포함) | 37 passed | 2분 |
| 3 | `_ANTHROPIC_PRICING` dict + `complete(model=)` 분기 | (slice 1 part 2 commit 포함) | 37 passed | 7분 |
| 4 | scripts boilerplate 공통화 (`scripts/validation/_setup.py`) | (slice 1 part 2 후속 commit) | 37 passed | ~4분 |
| 5 | `LLMResponse.metadata_dict()` 헬퍼 + service/scripts 적용 | (slice 1 part 2 후속 commit) | 37 passed | ~5분 |

> Step 9 슬롯 누적 ~21분 (#1+#2+#3+#4+#5). 30분 한도 내 완료. 잔여 ~9분은 Slice 2 진입 시 추가 후보 식별에 사용 가능.

---

## Deferred to Slice 2

| # | 항목 | 이연 사유 |
|---|------|-----------|
| 7 | Step 8 CSV 출력 옵션 | PriorityScore 1.0, 운영 편의 — Slice 2/3 활용도 보고 결정 |
| 8 | Mock LLMClient mode dict 매핑 | PriorityScore 1.0, RiskOfBreakage 2 (Mock 회귀 위험), 가치 미미 |
| 9 | ~~Gemini 호출 실패 진단 로깅~~ | **✅ 해소 (d72671a + 후속 commit)**. 진단 결과: free tier `gemini-2.0-flash` 한도 0. 모델 ID `gemini-2.5-flash` 갱신 + Slice 1 Decision §5.1 옵션 A 채택 (default provider = haiku, Gemini 분기는 호환성 위해 보존) |

---

## 후보 식별 메모 (퀀트 공학)

분자 (`CostSaving × Frequency`):
- 회귀 차단 항목 (#1, #2, #3) = `5×5`, `4×5`, `4×4` — 모든 진입점 영향, 즉시 가치 큼.
- 운영 편의 항목 (#7) = `2×2` — Slice 1 시점 활용도 낮음.

분모 (`RiskOfBreakage × TimeRequired`):
- robust parser는 신규 모듈, 회귀 위험 1 (기존 코드 미수정 — service만 alias 교체).
- 단가 dict는 매핑 변경 1줄 — 회귀 위험 1.

→ 분자 큰 + 분모 작은 항목 (#1~#3)이 Slice 1 진행 중 자연스럽게 적용됨.
→ 30분 슬롯에서 추가 적용 가능한 가장 가치 있는 항목: #4, #5.
