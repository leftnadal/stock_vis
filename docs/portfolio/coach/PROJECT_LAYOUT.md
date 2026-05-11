# Stock-Vis Portfolio Coach — 프로젝트 레이아웃

> **목적**: 작업 지시서 작성 시 경로 정합성 보장.
> Slice 7 Part 2에서 발견한 지시서 경로(`portfolio/coach/X`) vs 실제(`portfolio/X`)
> 불일치 재발 방지 (#3=B 부채 처리).
> **작성일**: 2026-05-11 (Slice 7 Part 3 §1).

---

## 디렉토리 매핑 (canonical)

| 카테고리          | 실제 경로                                | 비고                                                         |
| ----------------- | ---------------------------------------- | ------------------------------------------------------------ |
| Pydantic schemas  | `portfolio/schemas/`                     | `llm_outputs.py` (E1~E6 통합) + `e4_conversation.py` (Slice 7) |
| LLM 인프라        | `portfolio/llm/`                         | `client.py`, `token_budgets.py`, `eval_metrics.py`, `cost_guard.py`, `budget_estimator.py` |
| Prompt builders   | `portfolio/prompts/{entrypoint}/`        | e1·e2·e3·e3_portfolio·e4·e5·e6·tier0 각각 디렉토리           |
| 진입점별 service  | `portfolio/services/`                    | `e1_garp.py`, `e2_diagnostic_card.py`, `e3_metric_comment.py`, `e3_portfolio_service.py` 등 |
| Prompt helpers    | `portfolio/services/_prompt_helpers.py`  | `format_metrics_to_str` 등 공통 utility                      |
| 회귀 테스트       | `portfolio/tests/`                       | pytest 대상 (`tests/portfolio/coach/...` 아님)               |
| 회귀 fixtures     | `portfolio/tests/fixtures/{topic}/`      | mock 입력/출력 (`e4_conversation/`, `mock_responses/e3_portfolio/`) |
| Scripts (1회성)   | `scripts/slice{N}/`                      | 슬라이스 검증 스크립트                                       |
| Validation 공통   | `scripts/validation/`                    | score_step8.py, measure_*_tokens.py 등                       |
| Docs (영구)       | `docs/portfolio/coach/`                  | 정책, 보고서, 설계 (COST_POLICY.md, manual_eval_rubric.md, PROJECT_LAYOUT.md) |
| Docs (슬라이스별) | `docs/portfolio/coach/slice{N}/`         | 슬라이스 산출물                                              |

---

## 회귀 hash 정책

- `portfolio/tests/test_static_integrity.py` 7 항목으로 IDENTICAL hash 검증
- 보호 대상: 모듈 import + preset/metric count + schema 필드명 + Django models import
- Slice 1 e1_garp + Slice 3 e2_diversification 핵심 출력 hash는 본 7 항목 통과로 간접 보장
- 새 진입점 추가 시 7 항목 영향 0 확인 필수

---

## CostGuard 정책

- 싱글톤 (`CostGuard.get_instance()`) + `reset_slice(slice_id, max_calls)` (Slice 3 정착)
- 호출 카운트 상한 50/슬라이스 (기본)
- 단건 비용 임계: $0.020 (Slice 1부터 일관)
- 누적 광의 비용 임계: $1.50 (Slice 7 Part 1 갱신)

---

## LLM Client API (핵심)

`portfolio/llm/client.py` `LLMClient.complete(prompt: str, provider, max_tokens, model)`
- 단일 prompt string (messages 배열 아님). system + user 합성 후 전달.
- provider: `"gemini"` | `"anthropic"`
- Anthropic Haiku 호출: `provider="anthropic"`, `model=ANTHROPIC_HAIKU_MODEL`
- 응답: `LLMResponse` attribute access (`.text`, `.input_tokens`, `.cost_usd`, `.fallback_from` 등)
- `#19` (LLMClient system 인자 별도 처리) — Slice 7 Step 9 슬롯에서 처리 예정

---

## DIMENSION_LOOKUP 정책

- 실제 위치: `scripts/validation/score_step8.py` (**scoring config 전용**)
- 역할: 진입점별 manual eval 점수 산출 메타 (dim1/dim2/manual_field/raw·scored path)
- 일반적 schema dispatch 아님 — service layer는 직접 import 패턴
- 새 진입점 평가 시 entry 추가 (e1/e2/e3/e3_portfolio/e5/e6 등록 완료)
- E4 entry는 Step 8 평가 단계에서 추가 (Slice 7 Part 3 §3 결정)

---

## 슬라이스 종결 산출물 표준

각 슬라이스 종결 시 `docs/portfolio/coach/slice{N}/` 하위:
- `slice{N}_final_report.md` — 종결 보고
- `step6_smoke_result.{json,md}` — smoke test 결과
- `step7_matrix_raw.json` + `step7_matrix_metrics.json` + `step7_matrix_report.md` — real LLM matrix
- `step7_5_kpi_report.md` — KPI 자동 검증
- `step8_2way_{entrypoint}_raw.json` + `step8_2way_{entrypoint}_scored.json` — Part 4 입력
- `step9_*_eval_*.{md,json}` — manual eval 산출물
- `step9_3_report.md` + `step9_3_scored.json` — winner 판정
