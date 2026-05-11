# Slice 7 Part 3 Step 3 — DIMENSION_LOOKUP 결정

> **작성일**: 2026-05-11
> **선결**: Part 2 §1.4 보류 사항 — Part 3 §3에서 확정.

---

## §1. 검토 결과

### 1.1 실제 DIMENSION_LOOKUP 위치 + 역할

`scripts/validation/score_step8.py` line 33~93:
- **scoring config 전용** — manual eval 점수 산출 메타
- 필드: `dim1/dim2` (평점 키) + `manual_field` + `model_label_field` + `result_structure` + `default_raw/scored` path + `weight` + `additional_lex_check`
- 등록된 entry: e1·e2·e3·e3_portfolio·e5·e6
- **schema dispatch나 service layer dispatch 역할 아님**

### 1.2 실제 service dispatch 패턴

각 진입점은 독립 service 파일 + 직접 import 호출:
- `portfolio/services/e1_garp.py`
- `portfolio/services/e2_diagnostic_card.py`
- `portfolio/services/e3_metric_comment.py`
- `portfolio/services/e3_portfolio_service.py`
- `portfolio/services/e5_adjustment_parser.py`
- `portfolio/services/e6_comparison.py`

Provider 매핑은 `portfolio/services/_llm_kwargs.py` `PROVIDER_KWARGS` + `resolve_provider_kwargs(label)`.

### 1.3 판단

(a) **기존 진입점이 service layer dispatch 사용** → E4도 동일 패턴 채택.

---

## §2. E4 결정사항

### 2.1 Service dispatch — 직접 import (DIMENSION_LOOKUP entry 불요)

Part 3 §4·§5 스크립트(`run_step6_smoke.py`, `run_step7_matrix.py`)는 다음을 직접 import:

```python
from portfolio.prompts.e4.builder import build_e4_prompt
from portfolio.schemas.e4_conversation import E4ConversationInput, E4ConversationOutput
from portfolio.llm.client import LLMClient
from portfolio.services._llm_kwargs import resolve_provider_kwargs
from portfolio.llm.cost_guard import CostGuard
```

이전 슬라이스 패턴 일관 — 추가 dispatch table 없이도 동작.

### 2.2 Scoring entry — Part 4 진입 시 추가

Manual eval 점수 산출(Step 8 dump 후 Part 4 진입)에는 DIMENSION_LOOKUP entry 필요.
**Part 4 진입 시점**에 다음 entry 추가:

```python
# scripts/validation/score_step8.py
"e4_conversation": {
    "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
    "dim2": {"key": "insight", "manual_field": "insight_manual"},
    "model_label_field": "model_label",
    "result_structure": "nested",
    "default_raw": "docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json",
    "default_scored": "docs/portfolio/coach/slice7/step8_2way_e4_conversation_scored.json",
    "weight": 0.5,
    "additional_lex_check": "completeness_auto",
}
```

**Part 3 단계에서는 추가하지 않음** (Step 8 dump 시점에 함께 처리).

---

## §3. 회귀 영향

- §3 단독 회귀 추가: **0건** (decision docs만)
- service layer 신규 dispatch 코드 불요 — 기존 패턴 mirror
- §4·§5 스크립트에서 직접 import 패턴 사용

---

## §4. 후속 조치 (Part 4 진입 전)

- [ ] Step 8 dump 완료 후 `score_step8.py` DIMENSION_LOOKUP에 `e4_conversation` entry 추가
- [ ] entry 추가 후 회귀 +1~3건 예상 (기존 `test_score_unified.py` 패턴 mirror)
- [ ] PROJECT_LAYOUT.md "DIMENSION_LOOKUP 정책" 섹션 갱신 (entry 추가 후)
