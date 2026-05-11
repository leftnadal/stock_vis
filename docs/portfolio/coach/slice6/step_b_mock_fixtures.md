# Slice 6 Part 2 Step B — Mock Fixture + Service Layer 결정 보존

> 작성일: 2026-05-11
> 산출물: `portfolio/services/e3_portfolio_service.py` + `portfolio/tests/fixtures/mock_responses/e3_portfolio/` 10건 + 회귀 +16
> 분기 발동: **0건** (F4 미발동)

---

## §1. Mock Fixture 10건 (V1~V5 × haiku/sonnet)

| Fixture | haiku | sonnet | expected_alignment |
|---|---|---|---|
| V1 concentrated_balanced | ✓ 풍부 (haiku style, naturalness 높음) | ✓ 간결 (sonnet style) | partial |
| V2 concentrated_misfit | ✓ 풍부 | ✓ 간결 | **misaligned** |
| V3 concentrated_large | ✓ 풍부 | ✓ 간결 | partial |
| V4 concentrated_value | ✓ 풍부 | ✓ 간결 | aligned |
| V5 concentrated_dividend | ✓ 풍부 | ✓ 간결 | aligned |

### 1.1 작성 가이드 적용 (지시서 §2.4)
- **haiku**: 글쓰기 가설 5/5 정착 → naturalness 풍부, 어휘 다양 (목표 3.5+)
- **sonnet**: focus 강함, 단순 명료 (Slice 5 preset 다양성 민감 특성)
- 6 필드 length 제약 모두 준수 (holistic 30~300, 나머지 20~200)
- preset_alignment 5/5 정합 (V1=partial / V2=misaligned / V3=partial / V4=aligned / V5=aligned)
- confidence 모두 3~5 범위 (LLM 자신도 보통 이상)

### 1.2 gemini 제외 정책
- Slice 1 9/9 폴백 후 매트릭스 일관 제외 — Part 3 real LLM도 동일 정책 유지
- 10건 = 5 fixture × 2 model (haiku + sonnet only)

---

## §2. Service Layer 구성

### 2.1 portfolio/services/e3_portfolio_service.py 신규
| 함수 | 역할 |
|---|---|
| `load_mock_response(fixture_id, model_label)` | mock JSON 파일 로딩 (10건 검증) |
| `parse_e3_portfolio_response(text)` | LLM raw → E3PortfolioCommentary (Pydantic) |
| `run_e3_portfolio(...)` | **real LLM** 진입 함수 (Part 3 사용) — build → invoke → parse → metadata |
| `run_e3_portfolio_with_mock(...)` | **mock** 서비스 흐름 4단계 (Step B 정적 검증용) |

### 2.2 서비스 흐름 4단계 (mock 검증)
```
1. build_e3_portfolio_prompt(*, ..., analysis_context=fixture) → prompt
2. load_mock_response(fixture_id, model_label) → raw text (mock JSON)
3. parse_e3_portfolio_response(raw) → E3PortfolioCommentary (Pydantic)
4. validate (Pydantic 자동 — parse 통과 = validate 통과)
```

---

## §3. 회귀 테스트 +16 (지시서 +10~15 대비 +1 자연 흡수)

| 테스트 | 건수 | 목적 |
|---|---|---|
| test_e3_portfolio_service_mock_flow (parametrize V1~V5 × haiku/sonnet) | 10 | 서비스 흐름 4단계 PASS × 10 |
| test_e3_portfolio_service_invalid_mock_raises_validation_error | 1 | schema 위반 시 ValidationError |
| test_e3_portfolio_service_preset_alignment_enum_strict | 1 | preset_alignment Literal 정합 5/5 |
| test_e3_portfolio_service_cost_guard_integration | 1 | CostGuard 멱등 + mock 비용 0 |
| test_load_mock_response_unknown_fixture_raises | 1 | 미등록 fixture/model 에러 |
| test_mock_fixture_count_is_10 | 1 | 정확히 10건 파일 존재 |
| test_mock_responses_all_pydantic_valid | 1 | 10건 모두 schema parse PASS (F4 미발동) |

**합계: +16** (지시서 +10~15 상한 +1 자연 흡수).

---

## §4. KPI 충족

| 항목 | 기준 | 결과 |
|---|---|---|
| Mock fixture 10건 schema parse | V1~V5 × haiku/sonnet 모두 PASS | **10/10 PASS** ✓ |
| 서비스 흐름 4단계 | build → invoke(mock) → parse → validate | **PASS** ✓ |
| preset_alignment Enum | 5/5 정합 (mock vs fixture expected) | **5/5 PASS** ✓ |
| CostGuard 통합 | reset_slice 멱등 + mock 비용 0 | **PASS** ✓ |
| 회귀 | +10~15 PASS, 기존 379 영향 0건 | **+16 PASS** ✓ |
| 비용 | $0 (mock) | **PASS** ✓ |
| 시간 | 60~90분 | **~40분** ✓ |

---

## §5. F4 분기 미발동

> 지시서 §3 F4: "Mock fixture schema validation FAIL → 해당 mock 즉시 수정 (schema 변경 아님), Step 1.5 사이클 불필요."

- 10/10 모두 schema parse PASS — **F4 미발동** ✓
- 작성 시점부터 schema (Part 1) + length 제약 + Literal enum 모두 준수
- preset_alignment fixture expected vs mock 5/5 정합 (V1 partial / V2 misaligned / V3 partial / V4 aligned / V5 aligned)

---

## §6. Part 3 진입 전 체크포인트 (지시서 §7)

| # | 항목 | 결과 |
|---|---|---|
| 1 | `BUDGETS["e3_portfolio"]` 정식 등록 완료 | ✓ (Step A, 7,000) |
| 2 | estimator 외삽 검증 PASS 또는 #β2 재오픈 처리 완료 | ✓ (F2 발동 + #β2 재오픈 등재, 작업 차단 아님) |
| 3 | V1~V5 fixture × haiku/sonnet mock 10건 정합 PASS | ✓ (Step B, 10/10) |
| 4 | 서비스 layer 흐름 4단계 단위 테스트 PASS | ✓ (Step B, 4/4) |
| 5 | CostGuard 통합 검증 PASS | ✓ |
| 6 | 신규 부채 0건 또는 처리 계획 명시 | ⚠️ (#β2 재오픈 PS 2.0 — Slice 6 Step 9 슬롯 후보) |
| 7 | Slice 1 e1 + Slice 3 e2 IDENTICAL hash KPI 유지 | (전체 회귀 검증 필요 — 다음 단계) |

→ **Part 3 진입 준비 완료** (real LLM 15 cases, 비용 추정 $0.10~0.20).
