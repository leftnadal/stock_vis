# Slice 11 Part 4 — Step 1 Production 인벤토리

**작성일**: 2026-05-19
**대상**: E2~E6 진입점 기존 production service 식별 + Part 1/2 schema 비대칭 표

---

## §1. 진입점별 service / schema 매핑

| 진입점 | production service 파일                     | production 함수      | production output schema                  | Part 1 input schema  | Part 2 output schema | frontend 사용 |
| ------ | ------------------------------------------- | -------------------- | ----------------------------------------- | -------------------- | -------------------- | ------------- |
| E1     | `portfolio/services/e1_garp.py`             | `run_e1_garp`        | `OneLineDiagnosis` (legacy, Slice 1)      | `CommentaryInputE1`  | `E1Output`           | 사용중        |
| E2     | `portfolio/services/e2_diagnostic_card.py`  | `run_e2`             | `E2Response.card` (4요소 카드, Slice 3)   | `CommentaryInputE2`  | `E2Output`           | 사용중        |
| E3     | `portfolio/services/e3_portfolio_service.py` | `run_e3_portfolio`  | `E3PortfolioCommentary` (Slice 6 Part 2)  | `CommentaryInputE3`  | `E3Output`           | 사용중        |
| E4     | (없음 — 대화 Q&A 진입점 신규)               | -                    | -                                         | `CommentaryInputE4`  | `E4Output`           | 미사용 (신규) |
| E5     | `portfolio/services/e5_adjustment_parser.py` | `run_e5`            | `E5Response` (adjustments + confidence)   | `CommentaryInputE5`  | `E5Output`           | 사용중        |
| E6     | `portfolio/services/e6_comparison.py`       | `run_e6`             | `E6ComparisonResponse` (6필드 비교 해설)   | `CommentaryInputE6`  | `E6Output`           | 사용중        |

> **Part 3 정착 원칙 (재확인)**: 기존 production 함수는 **무변경**. Part 4 `run_e{N}_coach`는 신규 함수로 추가 (E1 패턴 미러).

---

## §2. schema 비대칭 표 (production → Part 2 output)

| 진입점 | production output 필드                                                      | Part 2 `E{N}Output` 필드                                              | 비대칭 처리                                                  |
| ------ | --------------------------------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------ |
| E1     | `OneLineDiagnosis` (legacy)                                                 | summary / key_observations / action_items / risk_flags / confidence  | Part 3 정착: prompt에서 신 schema 강제 (E1PromptBuilder)     |
| E2     | summary / strengths / weaknesses / actions (4요소 카드)                     | summary / key_observations / quoted_metrics / confidence              | prompt 재작성 (action 항목은 quoted_metrics에 흡수)         |
| E3     | headline / structure / strengths / risk_flags / suggestions / overall_view  | summary / key_observations / action_items / risk_flags / confidence   | suggestions → action_items, headline → summary 매핑          |
| E4     | (production 없음)                                                           | summary / key_observations / confidence                               | base만 — 신규 prompt 직접 작성 (Tier 1~3 분기 없이 단순)     |
| E5     | adjustments[].(ticker/action/delta_weight/...) + confidence(1~5)            | summary / key_observations / action_items / quoted_metrics / confidence | adjustments → action_items 매핑, quoted_metrics에 ticker별 추출값 |
| E6     | headline / before_summary / after_summary / key_changes[] / ...             | summary / key_observations / risk_flags / quoted_metrics / confidence | 비교 해설 → 분석엔진 결과 종합으로 prompt 의미 재정의       |

> **핵심 결정**: production endpoint와 `run_e{N}_coach`는 **목적과 schema가 다르다**. coach service는 Part 1/2 통합 A2 진입점이며, 의미는 production 패턴을 참고하되 prompt와 출력 형식은 Part 2 output schema에 강제 적합.

---

## §3. production prompt 코드 dump (builder 이식 참고용)

### E2 (`e2_diagnostic_card.py`)
- 구조: `당신은 ... 전문가 / preset / 현재 포트폴리오 / 분석 요약 / 주요 지표 / 작업 / 규칙`
- 핵심: 4요소 카드 (summary/strengths/weaknesses/actions), 매수/매도 추천 금지, 단순 수치 나열 금지

### E3 (`e3_portfolio_service.py` → `portfolio/prompts/e3_portfolio/`)
- 구조: build_e3_portfolio_prompt(preset_id, preset_intent, holdings_summary, sector_concentration, diversification_score, risk_concentration_score, core_metrics_summary, analysis_context)
- 핵심: hhi / sector_concentration / risk_concentration_score 등 portfolio-level 지표 입력

### E5 (`e5_adjustment_parser.py`)
- 구조: holdings / 분석 결과 요약 / 사용자 명령 / 작업 (JSON schema) / 규칙
- 핵심: schema 강제, 의도 매칭, reason_quote 강제, confidence 1~5

### E6 (`e6_comparison.py`)
- 구조: 프리셋 / 원본 포트폴리오 / 조정 명령 / 출력 요구 (JSON schema) / 규칙
- 핵심: 정량 재계산 금지, 매수/매도 추천 금지, 자연어 비교만

---

## §4. fixture (portfolio_a2) 데이터 가용성

| 진입점 | fixture 키                                                                   | 가용성 |
| ------ | ---------------------------------------------------------------------------- | ------ |
| E1     | `inputs.e1.garp_metrics` (5종목 × PER/PEG/ROE/yield)                          | OK     |
| E2     | `inputs.e2.portfolio_return_1y` (8.2), `sector_allocation` (4섹터)            | OK     |
| E3     | `inputs.e3.concentration_metrics` (hhi 0.2125, top3 0.65, sector_top 0.35, single_name_max 0.25) | OK |
| E4     | `inputs.e4.user_question` ("배당 안정성"), `conversation_history` (빈 list)  | OK     |
| E5     | `inputs.e5.extraction_targets` (4종), `time_series_context` (current/1q/4q/12q) | OK   |
| E6     | `inputs.e6.analysis_results` (5종목 × score/signals/notes)                   | OK     |

---

## §5. Part 4 builder 설계 결정

1. **E2 builder**: portfolio_return_1y + sector_allocation → 종합 진단 (quoted_metrics에 섹터 비중 인용)
2. **E3 builder**: concentration_metrics (hhi/top3/sector_top/single_name_max) → action_items + risk_flags 강제
3. **E4 builder**: user_question + conversation_history → base만 (action_items/risk_flags 없음)
4. **E5 builder**: extraction_targets + time_series_context → action_items + quoted_metrics (추출값 인용)
5. **E6 builder**: analysis_results (종목별 score/signals) → risk_flags + quoted_metrics (종목별 점수)

> **공통 패턴**: E1 builder의 `_format_holdings` 헬퍼 재사용. system_prompt는 base의 `build_system_prompt` (output schema JSON 자동 injection) 자연 활용.

---

## §6. KPI 1 결과

| 항목                              | 결과 |
| --------------------------------- | ---- |
| 5 진입점 service 파일 식별        | PASS (E2/E3/E5/E6 production 식별, E4는 신규) |
| production 함수명 매핑            | PASS |
| production endpoint 사용 여부 표 | PASS |
| schema 비대칭 표                  | PASS (5건 비대칭 모두 식별) |
| fixture 가용성 확인               | PASS (6/6) |

**Step 1 결론**: builder 구현 → run_e{N}_coach 신규 함수 추가 → production 무변경 패턴 확정.
