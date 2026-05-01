# Slice 2 — Part 2 작업 지시서 (Step 6~9)

> 작성일: 2026-04-30
> 대상: Stock-Vis Portfolio Coach 슬라이스 2 후반부
> 진입점: E5 (Slice 2 Part 1 산출물 활용)
> 전제: Slice 2 Part 1 (Step 0~5) 완료, 회귀 73 passed, 누적 호출 ~17/50
> 브랜치: portfolio
> 누적 LLM 호출: ~17 / 50 (Part 1 종결 시점)

---

## 결정 사항 (사용자 확정)

본 지시서는 다음 9개 결정을 모두 반영하여 작성됨. **v2 갱신 최소화**가 목표.

| Q   | 결정                                                         | 영향                  |
| --- | ------------------------------------------------------------ | --------------------- |
| Q1  | **옵션 C — 7 fixture × 2 model = 14 calls (gemini 제외)**    | Step 8 매트릭스       |
| Q3  | **옵션 A — Step 6 provider = haiku**                         | Step 6                |
| Q4  | **옵션 A — intent_match ≥ 3 ∧ no_extra_changes ≥ 3**         | Step 8 lexicographic  |
| Q5  | **옵션 C — 신설 score_step8_e5.py + Step 9에서 일반화**      | Step 8 score + Step 9 |
| Q6  | **옵션 B — slice2/ 서브디렉토리 분리 + Slice 1 산출물 이동** | Step 0.4 사전 작업    |
| Q7  | **옵션 A — Slice 2 종료 시 비용 가드 reset**                 | Slice 종료 회고       |
| N1  | **옵션 A+C — JSON 직접 편집 + 인라인 평가 가이드**           | Step 8 산출물         |
| N2  | **옵션 B — 동등 가중 sqrt(곱) + raw 값 보존**                | score 산출물          |
| N3  | **옵션 C — Step 8 진입 전 Mock 통합**                        | Step 0.5 사전 처리    |

### 결정의 정량적 근거 (퀀트 공학 기반)

| 결정                       | 산식/지표                           | 값                                                   |
| -------------------------- | ----------------------------------- | ---------------------------------------------------- |
| Q1 호출 한도               | (잔여 한도 - 안전 마진) ÷ 평균 비용 | (50-17-5) ÷ ~$0.012 ≈ 23 calls 한도. 14 ≤ 23 ✓       |
| Q1 fixture 우선            | 정보 이득(fixture 다양성) ÷ 비용    | (7-5)/(14-10) = 0.5 fixture/call ratio ✓             |
| Q4 임계                    | Slice 1 baseline 일관성 보존        | 비교 가능성 = 1.0 (변경 시 0)                        |
| Q5 일반화 PriorityScore    | (재사용성 × Severity) ÷ 비용        | 4.0 (참고자료 §4 표)                                 |
| N3 Mock 통합 PriorityScore | (재사용성 × Severity) ÷ 비용        | 3.0 (참고자료 §4 표). Q5 (4.0)와 함께 처리 시 시너지 |
| N2 가중치 일관성           | Slice 1 sqrt(× 곱) 패턴 보존율      | 100% (가중치 0.5/0.5)                                |

---

## 0. 사전 검증

### 0.1 Part 1 완료 확인

```bash
git rev-parse --abbrev-ref HEAD
# 예상: portfolio

pytest portfolio/tests/ -q
# 예상: 73 passed
# (Part 1 v2 71 + Part 1 실행 중 발견된 fixture +2 추정. 실제 카운트 우선)

# Part 1 산출물 무결성
ls docs/portfolio/coach/
# 예상: gemini_diagnosis.md, step6_smoke_output.json (reparse 갱신),
#       step8_3way_raw.json, step8_3way_scored.json,
#       validation_report_slice1.md, refactor_backlog_slice1.md, validation_report_d8.md
```

### 0.2 비용 가드 예산 분배 (잔여 33 calls)

| Step                         | 호출 수 | 누적   | 안전 마진 |
| ---------------------------- | ------- | ------ | --------- |
| Part 1 종료                  | —       | 17     | 33        |
| Step 6 (실 haiku 1회)        | 1       | 18     | 32        |
| Step 7 (오프라인 토큰 측정)  | 0       | 18     | 32        |
| Step 8 (7 fixture × 2 model) | 14      | 32     | 18        |
| Step 8 재시도 예비           | ~3      | ~35    | ~15       |
| Step 9 (리팩토링)            | 0       | ~35    | ~15       |
| 회귀/디버깅 예비             | 0~5     | ~35~40 | ~10~15    |

최대 35~40 / 50 (70~80%). 안전 마진 10~15.

### 0.3 환경 사전 검증 (참고자료 §7 반영)

```bash
# Slice 1 fixture 무결성 (Slice 2 fixture가 의존)
python -c "
from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_tech, get_context_garp_misfit, get_context_garp_large,
)
print('garp_tech holdings:', len(get_context_garp_tech().analysis_target_portfolio.holdings_summary))
print('garp_misfit holdings:', len(get_context_garp_misfit().analysis_target_portfolio.holdings_summary))
print('garp_large holdings:', len(get_context_garp_large().analysis_target_portfolio.holdings_summary))
"
# 예상: 5 / 5 / 15

# Slice 2 Part 1 fixture 무결성
python -c "
from portfolio.tests.fixtures.sample_adjustment_context import ALL_FIXTURES, COMMANDS
print(f'fixtures: {len(ALL_FIXTURES)}, commands: {len(COMMANDS)}')
"
# 예상: 7 / 7

# E5 service entry 검증
python -c "
from portfolio.services.e5_adjustment_parser import run_e5, build_e5_prompt, PROVIDER_KWARGS
print('PROVIDER_KWARGS keys:', list(PROVIDER_KWARGS.keys()))
"
# 예상: ['haiku', 'sonnet', 'gemini'] 또는 사용자 환경 키

# LLMClient 모델 상수 검증
python -c "
from portfolio.llm.client import (
    ANTHROPIC_HAIKU_MODEL, ANTHROPIC_SONNET_MODEL, GEMINI_MODEL,
)
print('haiku:', ANTHROPIC_HAIKU_MODEL)
print('sonnet:', ANTHROPIC_SONNET_MODEL)
print('gemini:', GEMINI_MODEL)
"
# 예상: claude-haiku-4-5 / claude-sonnet-4-5 / gemini-2.5-flash (Part 1 갱신값)
```

---

### 0.4 Slice 1 산출물 이동 (Q6.B 적용 — 사전 작업, ~20분)

**목표**: Slice 1 산출물 7건을 `docs/portfolio/coach/slice1/`로 이동. 의존 코드의 경로 수정. 회귀 73 passed 유지.

**이동 대상**:

```
docs/portfolio/coach/
├── step6_smoke_output.json           → slice1/
├── step8_3way_raw.json               → slice1/
├── step8_3way_scored.json            → slice1/
├── validation_report_slice1.md       → slice1/
├── refactor_backlog_slice1.md        → slice1/
├── validation_report_d8.md           → (상위 유지 — D-8은 D-시리즈 검증으로 슬라이스 무관)
└── gemini_diagnosis.md               → slice2/ (Slice 2 산출물)
```

**작업 단계**:

```bash
mkdir -p docs/portfolio/coach/slice1
mkdir -p docs/portfolio/coach/slice2

git mv docs/portfolio/coach/step6_smoke_output.json docs/portfolio/coach/slice1/
git mv docs/portfolio/coach/step8_3way_raw.json docs/portfolio/coach/slice1/
git mv docs/portfolio/coach/step8_3way_scored.json docs/portfolio/coach/slice1/
git mv docs/portfolio/coach/validation_report_slice1.md docs/portfolio/coach/slice1/
git mv docs/portfolio/coach/refactor_backlog_slice1.md docs/portfolio/coach/slice1/
git mv docs/portfolio/coach/gemini_diagnosis.md docs/portfolio/coach/slice2/
# validation_report_d8.md는 그대로
```

**경로 의존 코드 수정** (5개 파일 추정):

```bash
# Slice 1 경로 참조하는 코드 검색
grep -rn "docs/portfolio/coach/step6\|docs/portfolio/coach/step8\|docs/portfolio/coach/validation_report_slice1\|docs/portfolio/coach/refactor_backlog_slice1" \
    scripts/ portfolio/ docs/ --include="*.py" --include="*.md" 2>/dev/null
```

발견된 모든 경로를 `docs/portfolio/coach/slice1/...`로 수정. 주요 후보:

- `scripts/validation/score_step8.py` (Slice 1 — input/output 경로)
- `scripts/validation/reparse_step6.py` (Slice 1 — Part 1 v2에서 갱신됨)
- `scripts/validation/run_step6_smoke.py` (Slice 1 — output 경로)
- `scripts/validation/run_step8_3way.py` (Slice 1 — output 경로)
- 보고서 내 경로 언급 (md 파일)

**검증**:

```bash
# 경로 수정 후 회귀
pytest portfolio/tests/ -q
# 예상: 73 passed (이동만 했으므로 변경 없음)

# Slice 1 score 재실행 검증 (회귀 보장)
python -m scripts.validation.score_step8 \
    --input docs/portfolio/coach/slice1/step8_3way_raw.json \
    --output /tmp/test_slice1_rescore.json
diff <(jq -S 'del(.timestamp)' /tmp/test_slice1_rescore.json) \
     <(jq -S 'del(.timestamp)' docs/portfolio/coach/slice1/step8_3way_scored.json)
# 예상: 차이 없음 (동일 입력 → 동일 출력 보장)
```

### 0.4 검증 판정

| #   | 판정                           | 임계                  | 자동/수동 |
| --- | ------------------------------ | --------------------- | --------- |
| 1   | 디렉토리 생성                  | slice1/, slice2/ 존재 | 자동      |
| 2   | 파일 이동 git mv               | git status 확인       | 자동      |
| 3   | 경로 수정 후 회귀              | 73 passed             | 자동      |
| 4   | Slice 1 score 재실행 동일 결과 | diff 차이 없음        | 자동      |

### 0.4 산출물

- `docs/portfolio/coach/slice1/` (5개 파일 이동)
- `docs/portfolio/coach/slice2/gemini_diagnosis.md` (이동)
- 경로 수정된 코드 ~5건

### 0.4 비용 가드

- LLM 호출: 0회
- 누적: 17 / 50

---

### 0.5 Mock LLMClient 통합 (N3.C 적용 — 사전 작업, ~20분)

**목표**: Slice 2 Part 1에서 정의된 `_E5MockLLMClient`(테스트 파일 내부 클래스)를 `portfolio/llm/mocks.py:MockLLMClient`로 통합. 모델별 Mock 텍스트 전략 도입.

**현재 상태 (참고자료 §1)**:

- `portfolio/llm/mocks.py:MockLLMClient` — 기본 응답이 OneLineDiagnosis JSON (E1용)
- `portfolio/tests/test_e5_view.py:_E5MockLLMClient` — `_mock_response` 오버라이드로 E5Response JSON 반환

**통합 설계**:

```python
# portfolio/llm/mocks.py 갱신

from typing import Callable, Optional
from portfolio.schemas.llm import LLMResponse


# 진입점별 mock text strategy
_MOCK_TEXT_STRATEGIES: dict[str, Callable[[str], str]] = {
    "e1": _mock_text_e1,        # OneLineDiagnosis JSON
    "e5": _mock_text_e5,        # E5Response JSON
    # Slice 3 진입 시: "e2": _mock_text_e2 등 추가
}


def _mock_text_e1(prompt: str) -> str:
    """E1: OneLineDiagnosis JSON. 기존 _MOCK_TEXT 그대로 이동."""
    return '{"diagnosis": "GARP 적합도 양호.", "fit_class": "good"}'


def _mock_text_e5(prompt: str) -> str:
    """E5: E5Response JSON. _E5MockLLMClient에서 이동."""
    return (
        '{"adjustments":[],"confidence":3,"ambiguity_notes":null,'
        '"no_actionable_intent":true}'
    )


class MockLLMClient:
    """범용 Mock LLMClient. 진입점별 text strategy 적용 가능.

    Args:
        mode: "normal" | "rate_limit_first" | "timeout_first" | "auth_error"
              | "budget_exceeded"
        text_strategy: "e1" (default) | "e5" | 등록된 다른 진입점
    """
    def __init__(
        self,
        mode: str = "normal",
        text_strategy: str = "e1",
    ):
        self.mode = mode
        self._call_count = 0
        if text_strategy not in _MOCK_TEXT_STRATEGIES:
            raise ValueError(
                f"Unknown text_strategy: {text_strategy}. "
                f"Available: {list(_MOCK_TEXT_STRATEGIES.keys())}"
            )
        self._text_fn = _MOCK_TEXT_STRATEGIES[text_strategy]

    def complete(
        self,
        prompt: str,
        provider: str = "gemini",
        max_tokens: int = 2000,
        model: Optional[str] = None,
    ) -> LLMResponse:
        self._call_count += 1
        # 기존 mode 분기 로직 그대로 보존
        # (rate_limit_first / timeout_first / auth_error / budget_exceeded)
        ...
        # text 생성 부분만 strategy에서 분기
        text = self._text_fn(prompt)
        return LLMResponse(
            text=text,
            provider=provider,
            model=model or "mock-model",
            ...
        )
```

**기존 테스트 갱신** (N3.C 단점 보완 — Slice 1 회귀 재검증):

```python
# portfolio/tests/test_e5_view.py
# _E5MockLLMClient 정의 제거. 다음으로 대체:

from portfolio.llm.mocks import MockLLMClient


def _build_e5_mock(mode: str = "normal") -> MockLLMClient:
    """E5 진입점용 mock factory."""
    return MockLLMClient(mode=mode, text_strategy="e5")


# 기존 _E5MockLLMClient 사용처를 _build_e5_mock으로 교체
```

```python
# portfolio/tests/test_e1_garp_view.py (Slice 1)
# 기존 MockLLMClient(mode=...) 호출 → 명시적으로 text_strategy="e1" 추가
# (default가 e1이므로 변경 불필요. 검증 차원에서만 추가)

mock = MockLLMClient(mode="normal")  # text_strategy="e1" default
# 또는 명시적:
mock = MockLLMClient(mode="normal", text_strategy="e1")
```

**Slice 1 회귀 검증** (N3.C 핵심 단점 — 충돌 위험 차단):

```bash
# 1. 통합 후 Slice 1 회귀
pytest portfolio/tests/test_e1_garp_view.py -v
# 예상: Slice 1 baseline 동일 통과

# 2. 통합 후 Slice 2 회귀
pytest portfolio/tests/test_e5_view.py -v
# 예상: Slice 2 Part 1 baseline 동일 통과

# 3. 전체 회귀
pytest portfolio/tests/ -q
# 예상: 73 passed (회귀 0)

# 4. text_strategy 단위 테스트 추가 (+2 테스트)
pytest portfolio/tests/test_mocks.py -v
```

**단위 테스트 추가** (`portfolio/tests/test_mocks.py` 신설 또는 확장):

```python
import pytest
from portfolio.llm.mocks import MockLLMClient


def test_mock_text_strategy_e1_default():
    """default text_strategy는 e1."""
    mock = MockLLMClient()
    resp = mock.complete(prompt="test")
    assert "diagnosis" in resp.text


def test_mock_text_strategy_e5_explicit():
    """e5 strategy 선택 시 E5Response JSON."""
    mock = MockLLMClient(text_strategy="e5")
    resp = mock.complete(prompt="test")
    assert "adjustments" in resp.text
    assert "no_actionable_intent" in resp.text


def test_mock_text_strategy_unknown_rejected():
    """미등록 strategy는 ValueError."""
    with pytest.raises(ValueError, match="Unknown text_strategy"):
        MockLLMClient(text_strategy="e99_nonexistent")
```

### 0.5 검증 판정

| #   | 판정                                 | 임계        | 자동 |
| --- | ------------------------------------ | ----------- | ---- |
| 1   | \_MOCK_TEXT_STRATEGIES 등록 (e1, e5) | 2 strategy  | 자동 |
| 2   | \_E5MockLLMClient 제거               | grep 0건    | 자동 |
| 3   | text_strategy 단위 테스트 통과       | 3/3         | 자동 |
| 4   | Slice 1 + Slice 2 회귀 유지          | 73 passed   | 자동 |
| 5   | 누적 카운트                          | 73 + 3 = 76 | 자동 |

### 0.5 산출물

- `portfolio/llm/mocks.py` (확장, +30줄)
- `portfolio/tests/test_e5_view.py` (정리, \_E5MockLLMClient 제거)
- `portfolio/tests/test_e1_garp_view.py` (선택적 명시화)
- `portfolio/tests/test_mocks.py` (신설 또는 확장, +20줄)

### 0.5 비용 가드

- LLM 호출: 0회
- 누적: 17 / 50

---

# Step 6 — 실 haiku 1회 호출 (Q3.A 적용)

## 6.1 목표

E5 진입점의 첫 실제 LLM 호출. clear_decrease fixture(가장 명확한 단일 종목 축소 명령)로 baseline 측정.

**판정 차원 (E5 특화, Slice 1과 다름)**:

- schema 통과 (E5Response Pydantic)
- 의도 매칭 (수동 1~5): adjustments에 TSLA + decrease 포함 여부
- 비용 ≤ $0.020 (Slice 1 갱신 임계 동일)
- 지연 ≤ 5,000ms

## 6.2 fixture 결정 근거

`clear_decrease` 선택:

- 단일 종목 + 명시적 action(decrease) + 수치 명시(없으나 decrease 의도 명확)
- 의도 매칭 검증의 baseline (가장 쉬운 케이스가 통과 못하면 다른 fixture는 무의미)
- 7 fixture 중 LLM 출력 변동성 가장 낮음 → schema_pass 측정 noise 최소

## 6.3 작업 단계

### 6.3.1 스크립트 신설

`scripts/validation/run_step6_e5_smoke.py`:

```python
"""Step 6 — E5 진입점 실 haiku 1회 호출 (smoke test).

Slice 2 Part 2의 baseline 측정.
clear_decrease fixture × haiku provider × 1회 호출.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.validation._setup import init_django

init_django()

from portfolio.llm.client import LLMClient, ANTHROPIC_HAIKU_MODEL
from portfolio.schemas.llm import E5Request, E5Response
from portfolio.services.e5_adjustment_parser import build_e5_prompt, parse_e5_response
from portfolio.tests.fixtures.sample_adjustment_context import ALL_FIXTURES


THRESHOLDS = {
    "cost_usd_max": 0.020,
    "latency_ms_max": 5000,
}


def main() -> int:
    fixture = ALL_FIXTURES["clear_decrease"]()
    request = E5Request(
        analysis_context=fixture["analysis_context"],
        user_command=fixture["user_command"],
    )
    prompt = build_e5_prompt(request)

    client = LLMClient()
    resp = client.complete(
        prompt=prompt,
        provider="anthropic",
        model=ANTHROPIC_HAIKU_MODEL,
    )

    # schema 검증
    try:
        parsed = parse_e5_response(resp.text)
        schema_pass = True
        schema_error = None
        parsed_dict = parsed.model_dump()
    except Exception as e:
        parsed = None
        schema_pass = False
        schema_error = f"{type(e).__name__}: {str(e)[:200]}"
        parsed_dict = None

    # 임계 판정
    cost_pass = resp.cost_usd <= THRESHOLDS["cost_usd_max"]
    latency_pass = resp.latency_ms <= THRESHOLDS["latency_ms_max"]

    # 의도 매칭 가이드 (수동 평가 시 참조)
    intent_match_guide = {
        "5": "TSLA + decrease 모두 정확. 다른 종목/액션 추가 없음.",
        "4": "TSLA + decrease OK. 사소한 부수 변경(예: target_weight null 누락 등).",
        "3": "TSLA decrease는 있으나 추가 임의 변경 1~2개.",
        "2": "TSLA decrease 부분 매칭. 또는 임의 변경 3+개.",
        "1": "TSLA 또는 decrease 누락.",
    }

    output = {
        "step": "step6_e5_smoke",
        "fixture": "clear_decrease",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "request": {
            "user_command": request.user_command,
            "holdings_count": len(request.analysis_context.get("holdings", [])),
        },
        "raw_content": resp.text,
        "parsed": parsed_dict,
        "metadata": resp.metadata_dict(),
        "judgments": {
            "schema_pass": schema_pass,
            "schema_error": schema_error,
            "cost_pass": cost_pass,
            "latency_pass": latency_pass,
            "intent_match_manual": None,  # 수동 평가 입력 필요
        },
        "thresholds": THRESHOLDS,
        "evaluation_guide": {
            "intent_match": intent_match_guide,
        },
        "status_summary": {
            "schema_pass": schema_pass,
            "cost_pass": cost_pass,
            "latency_pass": latency_pass,
            "manual_eval_required": "intent_match_manual",
        },
    }

    output_path = Path("docs/portfolio/coach/slice2/step6_smoke_e5_output.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[Saved] {output_path}")
    print(f"  schema_pass:  {schema_pass}")
    print(f"  cost_pass:    {cost_pass} (${resp.cost_usd:.5f} / ${THRESHOLDS['cost_usd_max']:.4f})")
    print(f"  latency_pass: {latency_pass} ({resp.latency_ms}ms / {THRESHOLDS['latency_ms_max']}ms)")
    print(f"  fallback_from: {resp.fallback_from}")
    print()
    print("⚠️  intent_match_manual 필드를 1~5로 직접 입력 필요.")
    print(f"    파일: {output_path}")
    print(f"    가이드: output['evaluation_guide']['intent_match'] 참조")
    return 0 if (schema_pass and cost_pass and latency_pass) else 1


if __name__ == "__main__":
    sys.exit(main())
```

### 6.3.2 실행

```bash
python -m scripts.validation.run_step6_e5_smoke
```

### 6.3.3 수동 평가 (N1.A 적용)

산출물 JSON 열어 `judgments.intent_match_manual` 필드를 1~5 정수로 직접 편집:

```bash
# 평가 가이드는 같은 파일 내 evaluation_guide 섹션 참조 (N1.C 인라인)
jq '.evaluation_guide.intent_match' docs/portfolio/coach/slice2/step6_smoke_e5_output.json

# 평가 후 직접 편집
vim docs/portfolio/coach/slice2/step6_smoke_e5_output.json
# "intent_match_manual": null  →  "intent_match_manual": 5 (예시)
```

## 6.4 검증 판정 (4개)

| #   | 판정                | 임계               | 자동/수동 |
| --- | ------------------- | ------------------ | --------- |
| 1   | schema_pass         | true               | 자동      |
| 2   | intent_match_manual | 정수 1~5 (≥3 권장) | 수동      |
| 3   | cost_pass           | ≤ $0.020           | 자동      |
| 4   | latency_pass        | ≤ 5,000ms          | 자동      |

## 6.5 롤백 / 실패 시 처리

**케이스 A. schema_pass=false (Pydantic ValidationError)**:

- raw_content 검토. 마크다운 펜스, 누락 필드, action 일관성 위반 등 원인 파악
- 프롬프트 규칙 강화(예: "마크다운 펜스 금지" 강조) 후 재호출
- 호출 1회 추가 → 누적 19/50

**케이스 B. cost_pass=false (단일 호출 $0.020 초과)**:

- 원인: 입력 prompt가 예상보다 큼 (analysis_context 200자 제한 미작동) 또는 출력이 길어짐
- Step 7 토큰 측정으로 정확한 원인 파악 후 결정
- 임계 갱신 검토 (Slice 1 $0.001 → $0.020 패턴 mirror)

**케이스 C. latency_pass=false (5초 초과)**:

- Anthropic API 일시 지연 가능. 재시도 1회 (호출 1회 추가)
- 지속되면 임계 7,000ms로 상향 검토

**케이스 D. intent_match_manual < 3**:

- LLM이 의도 매칭 못함 → 프롬프트 설계 재검토 신호
- Step 8 진입 전 프롬프트 보강 + Step 6 재실행

## 6.6 산출물

- `scripts/validation/run_step6_e5_smoke.py` (신규, ~130줄)
- `docs/portfolio/coach/slice2/step6_smoke_e5_output.json` (실행 산출물)

## 6.7 비용 가드

- LLM 호출: 1회 (haiku)
- 예상 비용: ~$0.0042
- 누적: 18 / 50

---

# Step 7 — E5 토큰 측정 (오프라인)

## 7.1 목표

E5 prompt의 입력/출력 토큰 분포를 측정. 다음을 확정:

1. E5 budget 임계 (E1 갱신값 5,000 대비 어느 수준이 적정한가)
2. analysis_summary 200자 truncate가 토큰에 미치는 효과 (I4 모니터링 — Part 1 v2에서 이연됨)
3. Step 8 비용 예측 정확도

## 7.2 budget 가정 갱신 검토

E1 측정 baseline (Slice 1):

- 단일 prompt: ~3,700 tokens (input)
- 갱신된 budget: 5,000 (Slice 1 회고에서 갱신)

E5 예상:

- holdings_summary: ~50 tokens (5종목 기준)
- analysis_summary: ≤ 200자 ≈ ~150 tokens
- 사용자 명령: ≤ 100 tokens
- 프롬프트 템플릿: ~600 tokens
- **합계 추정: ~900~1,000 tokens (E1의 27% 수준)**

large fixture(15종목)의 경우:

- holdings_summary: ~150 tokens
- 전체 추정: ~1,300 tokens

## 7.3 작업 단계

### 7.3.1 스크립트 신설

`scripts/validation/measure_e5_tokens.py`:

```python
"""Step 7 — E5 prompt 토큰 측정 (오프라인, LLM 호출 없음).

7개 fixture별 input prompt 토큰 분포 + budget utilization 측정.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.validation._setup import init_django

init_django()

from portfolio.schemas.llm import E5Request
from portfolio.services.e5_adjustment_parser import build_e5_prompt
from portfolio.tests.fixtures.sample_adjustment_context import ALL_FIXTURES


# anthropic SDK의 token counting 또는 tiktoken 사용
def count_tokens(text: str, provider: str = "anthropic") -> int:
    """Provider별 토큰 카운터. Slice 1 measure_tokens.py와 동일 패턴."""
    if provider == "anthropic":
        from anthropic import Anthropic
        client = Anthropic()
        # SDK token counting API
        resp = client.messages.count_tokens(
            model="claude-haiku-4-5",
            messages=[{"role": "user", "content": text}],
        )
        return resp.input_tokens
    raise NotImplementedError(provider)


# E5 budget 가정 (측정 후 갱신)
INITIAL_BUDGET = 5000  # E1 동일값으로 시작. 측정 후 결정.


def main() -> int:
    results = []

    for name, getter in ALL_FIXTURES.items():
        fixture = getter()
        request = E5Request(
            analysis_context=fixture["analysis_context"],
            user_command=fixture["user_command"],
        )
        prompt = build_e5_prompt(request)
        token_count = count_tokens(prompt)
        utilization = token_count / INITIAL_BUDGET

        results.append({
            "fixture": name,
            "prompt_chars": len(prompt),
            "input_tokens": token_count,
            "budget": INITIAL_BUDGET,
            "utilization": round(utilization, 4),
            "holdings_count": len(fixture["analysis_context"].get("holdings", [])),
            "command_chars": len(fixture["user_command"]),
        })

    # 통계
    tokens = [r["input_tokens"] for r in results]
    stats = {
        "min": min(tokens),
        "max": max(tokens),
        "mean": sum(tokens) / len(tokens),
        "p50": sorted(tokens)[len(tokens) // 2],
        "p90": sorted(tokens)[int(len(tokens) * 0.9)],
    }

    # budget 권장값 산출 (P90 × 1.5 안전 마진)
    recommended_budget = int(stats["p90"] * 1.5)

    output = {
        "step": "step7_e5_token_measurement",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "stats": stats,
        "initial_budget": INITIAL_BUDGET,
        "recommended_budget": recommended_budget,
        "budget_decision_required": True,
        "decision_guide": {
            "if_recommended_lower_than_initial": "budget 하향. E5 전용 budget 분리 검토.",
            "if_recommended_higher_than_initial": "budget 상향. E1과 통합 budget 검토.",
            "safe_zone": "max utilization 70~85% 권장 (E5는 fixture 다양성 우선이라 50%여도 OK).",
        },
        "i4_monitoring": {
            "context": "Part 1 v2 I4 — analysis_summary 200자 truncate 효과 측정",
            "recommendation": (
                "max utilization 30% 미만이면 200자→300자 상향 가능. "
                "70% 초과면 200자→100자 압축 검토."
            ),
        },
    }

    output_path = Path("docs/portfolio/coach/slice2/step7_e5_token_measurement.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[Saved] {output_path}")
    print(f"  fixture count: {len(results)}")
    print(f"  token range:   {stats['min']} ~ {stats['max']}")
    print(f"  P90 tokens:    {stats['p90']}")
    print(f"  recommended budget: {recommended_budget}")
    print(f"  vs initial:    {recommended_budget} {'<' if recommended_budget < INITIAL_BUDGET else '>'} {INITIAL_BUDGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 7.3.2 실행

```bash
python -m scripts.validation.measure_e5_tokens
```

### 7.3.3 budget 결정 (수동, ~5분)

산출물 검토 후 다음 결정:

| 상황                           | 결정                                                                |
| ------------------------------ | ------------------------------------------------------------------- |
| recommended_budget < 2,000     | E5 budget을 2,000으로 하향. 코드 상수 `E5_TOKEN_BUDGET = 2000` 신설 |
| recommended_budget 2,000~3,500 | E5 budget = 3,500. E1(5,000)과 분리                                 |
| recommended_budget > 3,500     | E1과 통합 budget 5,000 유지. \_format_analysis_summary 압축 검토    |

I4 모니터링 결과(analysis_summary 200자 utilization):

- max utilization < 30% → 200자 유지 (압축 불필요)
- 30%~70% → 모니터링 지속 (현 상태 OK)
- > 70% → 100자 압축 결정 (Phase 2 또는 Slice 3에서)

## 7.4 검증 판정

| #   | 판정                  | 임계                             | 자동/수동 |
| --- | --------------------- | -------------------------------- | --------- |
| 1   | 7 fixture 모두 측정   | 7/7                              | 자동      |
| 2   | budget 결정 기록      | recommended_budget 명시          | 수동      |
| 3   | I4 모니터링 결정 기록 | analysis_summary 200자 유지/압축 | 수동      |
| 4   | 회귀                  | 76 passed                        | 자동      |

## 7.5 산출물

- `scripts/validation/measure_e5_tokens.py` (신규, ~80줄)
- `docs/portfolio/coach/slice2/step7_e5_token_measurement.json` (실행 산출물)

## 7.6 비용 가드

- LLM 호출: 0회 (오프라인 token counting은 SDK 호출이지만 generation 비용 없음)
- 누적: 18 / 50

---

# Step 8 — 2-way 회고 (Q1.C 적용 — gemini 제외)

## 8.1 목표

7 fixture × 2 model (haiku/sonnet) = 14 호출로 모델 비교 회고. lexicographic + efficiency + fallback 산식으로 winner 결정.

**Slice 1 Part 2 패턴 mirror, 차원만 변경**:

- naturalness/insight → intent_match/no_extra_changes
- 9-way → 2-way (gemini 진단 결과 정당화)

## 8.2 매트릭스 결정 근거 (Q1.C)

```
┌──────────────────────┬───────┬────────┐
│       fixture        │ haiku │ sonnet │
├──────────────────────┼───────┼────────┤
│ clear_decrease       │  ✓    │  ✓     │
│ clear_multi          │  ✓    │  ✓     │
│ unclear_amount       │  ✓    │  ✓     │
│ no_intent_question   │  ✓    │  ✓     │
│ no_intent_chitchat   │  ✓    │  ✓     │
│ remove               │  ✓    │  ✓     │
│ large                │  ✓    │  ✓     │
└──────────────────────┴───────┴────────┘
                         7      7        = 14 calls
```

gemini 제외 근거:

- Slice 1 Step 8에서 gemini 9/9 폴백 (사실상 sonnet 데이터로 채워짐)
- Part 1 Step 0 진단 결과 (PASS/WAIT 어느 쪽이든 본 슬라이스에서 데이터 가치 낮음)
- 비용 마진 확보 (14/50 → 32/50, 18 calls 안전 마진)

## 8.3 평가 차원 정의 (수동 1~5, N1.C 인라인 가이드)

### 8.3.1 intent_match (1~5)

사용자 명령의 의도를 LLM이 얼마나 정확히 매칭했는가:

| 점수 | 정의                                                               |
| ---- | ------------------------------------------------------------------ |
| 5    | 모든 종목 + 액션 정확. 누락 없음                                   |
| 4    | 핵심 종목 + 액션 정확. 사소한 누락 (예: target_weight null 미처리) |
| 3    | 일부 종목 누락 또는 추가 변경 있으나 핵심 의도 OK                  |
| 2    | 절반 이상 누락 또는 잘못된 액션 매칭                               |
| 1    | 의도 완전 빗나감 (예: decrease 요청을 increase로 처리)             |

### 8.3.2 no_extra_changes (1~5)

사용자가 명시 안 한 종목/액션을 LLM이 임의 추가하지 않았는가:

| 점수 | 정의                                    |
| ---- | --------------------------------------- |
| 5    | 추가 변경 없음. 사용자 명시 종목만 처리 |
| 4    | 1개 종목 추가 변경 (사소함)             |
| 3    | 2~3개 종목 추가 변경                    |
| 2    | 4개 종목 추가 변경                      |
| 1    | 5개 이상 추가 변경 (의도 왜곡 수준)     |

### 8.3.3 trade-off 인지 (N2 — raw 값 보존)

두 차원이 trade-off일 가능성:

- LLM이 안전하게 적게 추출 → intent_match ↓, no_extra_changes ↑
- LLM이 적극적으로 추론 → intent_match ↑, no_extra_changes ↓

**처리 룰 (N2.B 동등 가중)**:

- efficiency = sqrt(intent_match × no_extra_changes) — Slice 1 sqrt(× 곱) 패턴
- 동률 발생 시 raw 값 보존만 하고 winner 결정에 영향 없음
- 동률 빈도 30% 초과 시 Slice 3에서 가중치 룰 재검토 신호

## 8.4 작업 단계

### 8.4.1 스크립트 신설 (run)

`scripts/validation/run_step8_e5_2way.py`:

```python
"""Step 8 — E5 2-way 회고 (haiku + sonnet, gemini 제외).

7 fixture × 2 model = 14 calls.
산출물: docs/portfolio/coach/slice2/step8_2way_e5_raw.json
사용자 manual 평가 입력 필요 (N1.A — JSON 직접 편집).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.validation._setup import init_django

init_django()

from portfolio.llm.client import (
    LLMClient,
    ANTHROPIC_HAIKU_MODEL,
    ANTHROPIC_SONNET_MODEL,
)
from portfolio.schemas.llm import E5Request
from portfolio.services.e5_adjustment_parser import (
    build_e5_prompt, parse_e5_response,
)
from portfolio.tests.fixtures.sample_adjustment_context import ALL_FIXTURES


PROVIDERS = [
    {"label": "haiku", "provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    {"label": "sonnet", "provider": "anthropic", "model": ANTHROPIC_SONNET_MODEL},
]


# 평가 가이드 (산출물에 인라인 — N1.C)
EVALUATION_GUIDE = {
    "intent_match": {
        "5": "모든 종목 + 액션 정확. 누락 없음.",
        "4": "핵심 정확. 사소한 누락 (예: target_weight null 미처리).",
        "3": "일부 누락 또는 추가 변경 있으나 핵심 의도 OK.",
        "2": "절반 이상 누락 또는 잘못된 액션.",
        "1": "의도 완전 빗나감.",
    },
    "no_extra_changes": {
        "5": "추가 변경 없음.",
        "4": "1개 종목 추가 변경 (사소함).",
        "3": "2~3개 종목 추가 변경.",
        "2": "4개 종목 추가 변경.",
        "1": "5개 이상 추가 변경 (의도 왜곡 수준).",
    },
}


def main() -> int:
    client = LLMClient()
    results = []

    for fixture_name, getter in ALL_FIXTURES.items():
        fixture = getter()
        request = E5Request(
            analysis_context=fixture["analysis_context"],
            user_command=fixture["user_command"],
        )
        prompt = build_e5_prompt(request)

        for prov in PROVIDERS:
            try:
                resp = client.complete(
                    prompt=prompt,
                    provider=prov["provider"],
                    model=prov["model"],
                )
                try:
                    parsed = parse_e5_response(resp.text)
                    schema_pass = True
                    schema_error = None
                    parsed_dict = parsed.model_dump()
                except Exception as e:
                    parsed = None
                    schema_pass = False
                    schema_error = f"{type(e).__name__}: {str(e)[:200]}"
                    parsed_dict = None

                results.append({
                    "fixture": fixture_name,
                    "model_label": prov["label"],
                    "raw_content": resp.text,
                    "parsed": parsed_dict,
                    "metadata": resp.metadata_dict(),
                    "judgments": {
                        "schema_pass": schema_pass,
                        "schema_error": schema_error,
                        "intent_match_manual": None,    # 수동 평가 입력 필요
                        "no_extra_changes_manual": None,  # 수동 평가 입력 필요
                    },
                    "expected": fixture.get("expected", {}),
                })
            except Exception as e:
                results.append({
                    "fixture": fixture_name,
                    "model_label": prov["label"],
                    "error": f"{type(e).__name__}: {str(e)[:300]}",
                    "judgments": {
                        "schema_pass": False,
                        "schema_error": str(e)[:200],
                        "intent_match_manual": None,
                        "no_extra_changes_manual": None,
                    },
                })

    # 비용 합계
    total_cost = sum(
        r.get("metadata", {}).get("cost_usd", 0)
        for r in results
    )
    fallback_count = sum(
        1 for r in results
        if r.get("metadata", {}).get("fallback_from") is not None
    )

    output = {
        "step": "step8_2way_e5_raw",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "matrix_size": {
            "fixtures": len(ALL_FIXTURES),
            "models": len(PROVIDERS),
            "total_calls": len(results),
        },
        "providers": [{"label": p["label"], "model": p["model"]} for p in PROVIDERS],
        "results": results,
        "summary": {
            "total_calls": len(results),
            "total_cost_usd": round(total_cost, 4),
            "fallback_count": fallback_count,
            "schema_pass_count": sum(1 for r in results if r["judgments"]["schema_pass"]),
        },
        "evaluation_guide": EVALUATION_GUIDE,
        "manual_eval_required": [
            "results[].judgments.intent_match_manual (1~5 정수)",
            "results[].judgments.no_extra_changes_manual (1~5 정수)",
        ],
    }

    output_path = Path("docs/portfolio/coach/slice2/step8_2way_e5_raw.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[Saved] {output_path}")
    print(f"  total calls: {len(results)}")
    print(f"  total cost:  ${total_cost:.4f}")
    print(f"  fallback:    {fallback_count}/{len(results)}")
    print()
    print("⚠️  다음 필드를 수동 입력 후 score_step8_e5.py 실행:")
    print("    - results[].judgments.intent_match_manual (1~5)")
    print("    - results[].judgments.no_extra_changes_manual (1~5)")
    print("    가이드: output['evaluation_guide'] 참조")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 8.4.2 실행

```bash
python -m scripts.validation.run_step8_e5_2way
```

### 8.4.3 수동 평가 (N1.A 적용 — 14건 × 2차원 = 28회 입력)

산출물 JSON 열어 각 result의 `judgments.intent_match_manual` 및 `no_extra_changes_manual` 직접 편집:

```bash
# 평가 가이드 확인
jq '.evaluation_guide' docs/portfolio/coach/slice2/step8_2way_e5_raw.json

# 평가 입력
vim docs/portfolio/coach/slice2/step8_2way_e5_raw.json
# results[0].judgments.intent_match_manual: null → 5 (예시)
# results[0].judgments.no_extra_changes_manual: null → 4 (예시)
# ... 14건 모두
```

예상 작업 시간: 14건 × 2분 = ~28분.

### 8.4.4 score 스크립트 신설 (Q5.C — score_step8_e5.py)

`scripts/validation/score_step8_e5.py`:

```python
"""Step 8 — E5 회고 점수 산출.

Slice 1 score_step8.py 패턴 mirror, 차원만 변경.
Step 9에서 score_step8.py와 일반화 통합 예정.

산식 (N2.B 동등 가중):
- Lexicographic 1차 필터: schema=True ∧ intent_match≥3 ∧ no_extra_changes≥3
- Efficiency: sqrt(intent_match × no_extra_changes)
- Fallback weights: schema/intent_match/no_extra/cost/lat = 0.25/0.25/0.25/0.15/0.10
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


THRESHOLDS = {
    "intent_match_min": 3,
    "no_extra_changes_min": 3,
    "cost_usd_max": 0.020,
    "latency_ms_max": 5000,
}

# Fallback 가중 (Slice 1 패턴 mirror)
FALLBACK_WEIGHTS = {
    "schema": 0.25,
    "intent_match": 0.25,
    "no_extra_changes": 0.25,
    "cost": 0.15,
    "latency": 0.10,
}


def lexicographic_pass(judgments: dict, metadata: dict) -> tuple[bool, str]:
    """1차 필터. 통과 여부 + 실패 원인."""
    if not judgments.get("schema_pass"):
        return False, "schema_fail"
    intent = judgments.get("intent_match_manual")
    if intent is None:
        return False, "intent_match_manual_missing"
    if intent < THRESHOLDS["intent_match_min"]:
        return False, f"intent_match<{THRESHOLDS['intent_match_min']}"
    no_extra = judgments.get("no_extra_changes_manual")
    if no_extra is None:
        return False, "no_extra_changes_manual_missing"
    if no_extra < THRESHOLDS["no_extra_changes_min"]:
        return False, f"no_extra_changes<{THRESHOLDS['no_extra_changes_min']}"
    cost = metadata.get("cost_usd", float("inf"))
    if cost > THRESHOLDS["cost_usd_max"]:
        return False, f"cost>{THRESHOLDS['cost_usd_max']}"
    latency = metadata.get("latency_ms", float("inf"))
    if latency > THRESHOLDS["latency_ms_max"]:
        return False, f"latency>{THRESHOLDS['latency_ms_max']}"
    return True, "pass"


def efficiency_score(judgments: dict) -> float:
    """N2.B — sqrt(intent_match × no_extra_changes)."""
    intent = judgments.get("intent_match_manual") or 0
    no_extra = judgments.get("no_extra_changes_manual") or 0
    return math.sqrt(intent * no_extra)


def fallback_score(judgments: dict, metadata: dict) -> float:
    """가중 합산. lexicographic 통과 안 한 후보 비교용."""
    schema = 1.0 if judgments.get("schema_pass") else 0.0
    intent = ((judgments.get("intent_match_manual") or 0) - 1) / 4  # 1~5 → 0~1
    no_extra = ((judgments.get("no_extra_changes_manual") or 0) - 1) / 4
    cost_norm = max(0, 1 - (metadata.get("cost_usd", 0) / THRESHOLDS["cost_usd_max"]))
    lat_norm = max(0, 1 - (metadata.get("latency_ms", 0) / THRESHOLDS["latency_ms_max"]))
    return (
        FALLBACK_WEIGHTS["schema"] * schema
        + FALLBACK_WEIGHTS["intent_match"] * intent
        + FALLBACK_WEIGHTS["no_extra_changes"] * no_extra
        + FALLBACK_WEIGHTS["cost"] * cost_norm
        + FALLBACK_WEIGHTS["latency"] * lat_norm
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="docs/portfolio/coach/slice2/step8_2way_e5_raw.json",
    )
    parser.add_argument(
        "--output",
        default="docs/portfolio/coach/slice2/step8_2way_e5_scored.json",
    )
    args = parser.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))

    # 모델별 집계
    by_model = defaultdict(list)
    tradeoff_cases = []

    for r in raw["results"]:
        if "error" in r:
            continue
        passed, reason = lexicographic_pass(r["judgments"], r["metadata"])
        eff = efficiency_score(r["judgments"])
        fb = fallback_score(r["judgments"], r["metadata"])
        scored = {
            "fixture": r["fixture"],
            "model_label": r["model_label"],
            "lex_pass": passed,
            "lex_fail_reason": reason if not passed else None,
            "efficiency": round(eff, 4),
            "fallback": round(fb, 4),
            "raw_judgments": r["judgments"],
            "raw_metadata": {
                "cost_usd": r["metadata"].get("cost_usd"),
                "latency_ms": r["metadata"].get("latency_ms"),
                "fallback_from": r["metadata"].get("fallback_from"),
            },
        }
        by_model[r["model_label"]].append(scored)

        # N2 trade-off 모니터링
        intent = r["judgments"].get("intent_match_manual")
        no_extra = r["judgments"].get("no_extra_changes_manual")
        if intent is not None and no_extra is not None:
            if abs(intent - no_extra) >= 2:
                tradeoff_cases.append({
                    "fixture": r["fixture"],
                    "model_label": r["model_label"],
                    "intent_match": intent,
                    "no_extra_changes": no_extra,
                    "diff": intent - no_extra,
                })

    # 모델별 평균
    model_summary = {}
    for label, scored_list in by_model.items():
        passed_list = [s for s in scored_list if s["lex_pass"]]
        model_summary[label] = {
            "lex_pass_rate": round(len(passed_list) / len(scored_list), 4),
            "label_means": {
                "intent_match": round(
                    sum(s["raw_judgments"].get("intent_match_manual") or 0 for s in scored_list)
                    / len(scored_list), 4,
                ),
                "no_extra_changes": round(
                    sum(s["raw_judgments"].get("no_extra_changes_manual") or 0 for s in scored_list)
                    / len(scored_list), 4,
                ),
            },
            "efficiency_mean": round(
                sum(s["efficiency"] for s in scored_list) / len(scored_list), 4,
            ),
            "fallback_mean": round(
                sum(s["fallback"] for s in scored_list) / len(scored_list), 4,
            ),
            "cost_total": round(
                sum(s["raw_metadata"].get("cost_usd") or 0 for s in scored_list), 4,
            ),
        }

    # winner 결정
    # 1차: lex_pass_rate 높은 쪽
    # 동률: efficiency_mean 높은 쪽
    # 동률: fallback_mean 높은 쪽
    sorted_models = sorted(
        model_summary.items(),
        key=lambda kv: (
            -kv[1]["lex_pass_rate"],
            -kv[1]["efficiency_mean"],
            -kv[1]["fallback_mean"],
        ),
    )
    winner_label = sorted_models[0][0]
    use_fallback = sorted_models[0][1]["lex_pass_rate"] < 0.5

    # trade-off 통계
    tradeoff_freq = len(tradeoff_cases) / len(raw["results"]) if raw["results"] else 0

    output = {
        "step": "step8_2way_e5_scored",
        "scored_at": "2026-04-30",  # datetime.now(timezone.utc).isoformat() 권장
        "thresholds": THRESHOLDS,
        "fallback_weights": FALLBACK_WEIGHTS,
        "by_fixture_model": {
            label: scored_list for label, scored_list in by_model.items()
        },
        "model_summary": model_summary,
        "winner": winner_label,
        "use_fallback": use_fallback,
        "tradeoff_analysis": {
            "context": "N2.B — 동등 가중. raw 값 보존만, winner 결정에 영향 없음.",
            "tradeoff_cases": tradeoff_cases,
            "tradeoff_frequency": round(tradeoff_freq, 4),
            "monitoring_threshold": 0.30,
            "alert": tradeoff_freq > 0.30,
            "note": "30% 초과 시 Slice 3에서 가중치 룰 재검토 신호.",
        },
        "evaluation_dimensions": ["intent_match", "no_extra_changes"],
        "_meta_for_step9_generalization": {
            "context": "Step 9 score_step8 일반화 작업 시 입력 키",
            "dim1_key": "intent_match_manual",
            "dim2_key": "no_extra_changes_manual",
            "weight": 0.5,  # 동등
        },
    }

    Path(args.output).write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[Saved] {args.output}")
    print(f"  winner: {winner_label}")
    print(f"  use_fallback: {use_fallback}")
    print(f"  tradeoff_freq: {tradeoff_freq:.4f} ({'⚠️ ALERT' if tradeoff_freq > 0.30 else 'OK'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 8.4.5 실행

```bash
python -m scripts.validation.score_step8_e5
```

### 8.4.6 validation_report_slice2.md 작성 (수동, ~30분)

`docs/portfolio/coach/slice2/validation_report_slice2.md`:

```markdown
# Validation Report — Slice 2 (E5)

> 작성일: 2026-04-30
> 진입점: E5 (조정 파싱)
> 범위: Step 6 ~ Step 9

## 1. Step 6 결과

- fixture: clear_decrease
- provider: haiku
- 4개 판정: ...
- 비용: $...
- 결정: PASS / FAIL

## 2. Step 7 토큰 측정

- 7 fixture 토큰 분포: ...
- recommended_budget: ...
- I4 모니터링: analysis_summary 200자 utilization ...
- 결정: ...

## 3. Step 8 회고 (2-way)

### 3.1 매트릭스

- 14 calls (haiku 7 + sonnet 7)
- gemini 제외 근거: ...

### 3.2 모델별 결과

| 모델   | lex_pass_rate | label_means(intent) | label_means(no_extra) | efficiency_mean | cost_total |
| ------ | ------------- | ------------------- | --------------------- | --------------- | ---------- |
| haiku  | ...           | ...                 | ...                   | ...             | ...        |
| sonnet | ...           | ...                 | ...                   | ...             | ...        |

### 3.3 winner

- ...

### 3.4 trade-off 분석 (N2)

- frequency: ...
- alert: True/False
- 결정: ...

## 4. Step 9 리팩토링 결과

- 적용 항목: ...
- 이연 항목: ...

## 5. 누적 비용

- 총 호출: ...
- 총 비용: $...

## 6. Slice 3 백로그

- ...
```

## 8.5 검증 판정

| #   | 판정                               | 임계                | 자동/수동 |
| --- | ---------------------------------- | ------------------- | --------- |
| 1   | 14 calls 실행 완료                 | 14/14 (오류 0)      | 자동      |
| 2   | 수동 평가 입력 (intent + no_extra) | 28/28 필드          | 수동      |
| 3   | score 스크립트 정상 실행           | winner 결정         | 자동      |
| 4   | trade-off frequency                | < 0.30 (alert 없음) | 자동      |
| 5   | validation_report 작성             | 6 섹션 모두         | 수동      |

## 8.6 롤백 / 실패 시 처리

**케이스 A. 일부 호출 실패 (Anthropic API 오류)**:

- error 필드 있는 result만 재실행 (호출 1~3회 추가)

**케이스 B. lex_pass_rate < 50% (양쪽 모델 모두)**:

- 프롬프트 설계 결함 신호. Step 6 baseline은 통과했으나 다양한 fixture에서 실패
- 원인 분석 후 프롬프트 보강 + Step 8 재실행 (호출 14회 추가 → 누적 위험)
- 또는 fallback 산식 사용 (use_fallback=True)

**케이스 C. trade-off frequency > 30%**:

- alert만 표시. winner 결정에는 영향 없음 (N2.B)
- Slice 3 백로그 추가: 가중치 룰 재검토

## 8.7 산출물

- `scripts/validation/run_step8_e5_2way.py` (신규, ~150줄)
- `scripts/validation/score_step8_e5.py` (신규, ~200줄)
- `docs/portfolio/coach/slice2/step8_2way_e5_raw.json` (실행 산출물)
- `docs/portfolio/coach/slice2/step8_2way_e5_scored.json` (점수 산출물)
- `docs/portfolio/coach/slice2/validation_report_slice2.md` (보고서)

## 8.8 비용 가드

- LLM 호출: 14회 (haiku 7 + sonnet 7)
- 예상 비용: 7 × ~$0.0042 + 7 × ~$0.0156 ≈ $0.139
- 누적: 32 / 50 (재시도 포함 시 ~35)

---

# Step 9 — 30분 리팩토링 슬롯 (Q5.C 적용 — score 일반화 우선)

## 9.1 목표

Slice 1 + Slice 2 누적 부채 중 PriorityScore 높은 항목을 30분 한도 안에서 처리. 회귀 76 passed 유지가 핵심 KPI.

## 9.2 백로그 우선순위 (PriorityScore 기반)

| 출처                | 항목                                         | PriorityScore | 예상 시간             | 처리                 |
| ------------------- | -------------------------------------------- | ------------- | --------------------- | -------------------- |
| Slice 2 신규        | score_step8.py E1/E5 차원 일반화 (Q5.C 핵심) | **4.0**       | 30분                  | **본 Step에서 처리** |
| Slice 2 신규        | \_E5MockLLMClient 통합 (N3)                  | 3.0           | (Step 0.5에서 처리됨) | 완료                 |
| Slice 2 신규        | PROVIDER_KWARGS services 공유 모듈           | 2.0           | 20분                  | Slice 3 백로그       |
| Slice 2 신규        | build_e5_prompt 헬퍼 분리                    | 2.0           | 15분                  | Slice 3 백로그       |
| Slice 1 Deferred #7 | Step 8 CSV 출력 옵션                         | 1.0           | 10분                  | Slice 3 백로그       |
| Slice 1 Deferred #8 | Mock LLMClient mode dict 매핑                | 1.0           | 10분                  | Slice 3 백로그       |

## 9.3 작업 단계 — score 일반화 (PriorityScore 4.0)

### 9.3.1 설계 — 일반화된 score_step8.py

```python
# scripts/validation/score_step8.py (일반화 버전)

DIMENSION_LOOKUP = {
    "e1": {
        "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
        "dim2": {"key": "insight", "manual_field": "insight_manual"},
        "weight": 0.5,
    },
    "e5": {
        "dim1": {"key": "intent_match", "manual_field": "intent_match_manual"},
        "dim2": {"key": "no_extra_changes", "manual_field": "no_extra_changes_manual"},
        "weight": 0.5,
    },
    # Slice 3 진입 시: "e2": {...} 추가
}


def lexicographic_pass(judgments, metadata, entrypoint: str):
    config = DIMENSION_LOOKUP[entrypoint]
    dim1_field = config["dim1"]["manual_field"]
    dim2_field = config["dim2"]["manual_field"]
    # ... 기존 로직, 키 이름만 매개변수화
```

### 9.3.2 작업 절차

```bash
# 1. Slice 1 score 회귀 baseline 저장
python -m scripts.validation.score_step8 \
    --input docs/portfolio/coach/slice1/step8_3way_raw.json \
    --output /tmp/slice1_baseline.json
sha256sum /tmp/slice1_baseline.json

# 2. score_step8.py 일반화 작업 (15분)
# - DIMENSION_LOOKUP 추가
# - --entrypoint 인자 추가 (default e1)
# - 키 이름 매개변수화

# 3. Slice 1 회귀 검증
python -m scripts.validation.score_step8 \
    --input docs/portfolio/coach/slice1/step8_3way_raw.json \
    --output /tmp/slice1_after.json \
    --entrypoint e1
diff <(jq -S 'del(.scored_at)' /tmp/slice1_baseline.json) \
     <(jq -S 'del(.scored_at)' /tmp/slice1_after.json)
# 예상: 차이 없음 (회귀 완전 보장)

# 4. score_step8_e5.py를 score_step8.py --entrypoint e5로 대체
python -m scripts.validation.score_step8 \
    --input docs/portfolio/coach/slice2/step8_2way_e5_raw.json \
    --output docs/portfolio/coach/slice2/step8_2way_e5_scored.json \
    --entrypoint e5
# 예상: 동일 결과 (score_step8_e5.py와 동일)

# 5. score_step8_e5.py deprecation 표시 (즉시 삭제는 위험)
echo '"""DEPRECATED — use score_step8.py --entrypoint e5"""' \
    | cat - scripts/validation/score_step8_e5.py > /tmp/deprecated.py \
    && mv /tmp/deprecated.py scripts/validation/score_step8_e5.py

# 6. 회귀
pytest portfolio/tests/ -q
# 예상: 76 passed
```

## 9.4 검증 판정

| #   | 판정                           | 임계           | 자동 |
| --- | ------------------------------ | -------------- | ---- |
| 1   | DIMENSION_LOOKUP 추가 (e1, e5) | 2 entrypoint   | 자동 |
| 2   | Slice 1 회귀 동일 결과         | diff 차이 없음 | 자동 |
| 3   | Slice 2 회귀 동일 결과         | diff 차이 없음 | 자동 |
| 4   | 30분 한도 준수                 | 실제 ≤ 32분    | 수동 |
| 5   | 회귀                           | 76 passed 유지 | 자동 |

## 9.5 한도 초과 시 처리 (Q5.C 단점 보완)

30분 안에 일반화 작업 완료 못 하면:

- 즉시 중단. score_step8.py 변경 사항 git stash 또는 revert
- score_step8_e5.py는 그대로 유지 (Step 8 산출물에 영향 없음)
- Slice 3 Step 0 백로그에 "score_step8 일반화 — Slice 2 Step 9에서 미완료" 추가

## 9.6 산출물

- `scripts/validation/score_step8.py` (확장 — 일반화)
- `scripts/validation/score_step8_e5.py` (deprecation 표시)
- `docs/portfolio/coach/slice2/refactor_backlog_slice2.md` (Slice 3 이연 항목 명시)

## 9.7 비용 가드

- LLM 호출: 0회
- 누적: 32~35 / 50

---

# Slice 2 종결 작업 (Q7.A 적용)

## S.1 비용 가드 reset

Slice 2 종료 보고서(validation_report_slice2.md)에 누적 비용 명시 후 Slice 3 진입 시 reset:

```python
# 환경 변수 또는 LLMClient 상태 reset
# 구현 방식은 Slice 1 종결 시 결정한 패턴 따름

# 예: env 분리
# .env.slice2 → .env.slice3 (LLM_BUDGET_MAX_CALLS=50으로 새로 시작)
# 또는 카운터 직접 초기화
```

## S.2 누적 보고

- 총 호출: ~35/50 (Part 1 17 + Part 2 ~18)
- 총 비용: ~$0.27 (Part 1 ~$0.13 + Part 2 ~$0.14)

## S.3 Slice 3 백로그 갱신

`docs/portfolio/coach/slice2/refactor_backlog_slice2.md`:

```markdown
# Slice 2 Refactor Backlog (Slice 3 이연)

| #   | 항목                                                    | PriorityScore | 출처                | 예상 시간 |
| --- | ------------------------------------------------------- | ------------- | ------------------- | --------- |
| 1   | PROVIDER_KWARGS services 공유 모듈                      | 2.0           | Slice 2 신규        | 20분      |
| 2   | build_e5_prompt 헬퍼 분리                               | 2.0           | Slice 2 신규        | 15분      |
| 3   | Step 8 CSV 출력 옵션                                    | 1.0           | Slice 1 Deferred #7 | 10분      |
| 4   | Mock LLMClient mode dict 매핑                           | 1.0           | Slice 1 Deferred #8 | 10분      |
| 5   | score_step8 일반화 미완료 (있다면)                      | 4.0           | Slice 2 Step 9      | 30분      |
| 6   | I4 — analysis_summary 200자 압축 (utilization > 70% 시) | 조건부        | Slice 2 Step 7      | 5분       |
| 7   | trade-off 가중치 룰 (frequency > 30% 시)                | 조건부        | Slice 2 Step 8      | 30분      |

## Slice 1 미해결 (재확인)

- 자동 평가 LLM-as-judge (Phase 2 후보)
- garp_large fixture 토큰 효과 측정 (E2 시점)
```

---

# Part 2 종결 체크리스트

Step 6 ~ Step 9 완료 직전 본인 확인:

- [ ] Step 0.4: Slice 1 산출물 5개 → slice1/, gemini_diagnosis.md → slice2/. 회귀 73 passed 유지
- [ ] Step 0.5: MockLLMClient text_strategy 통합. \_E5MockLLMClient 제거. 회귀 76 passed
- [ ] Step 6: clear_decrease × haiku 1회. schema_pass + intent_match≥3 + cost ≤ $0.020 + latency ≤ 5,000ms
- [ ] Step 7: 7 fixture 토큰 측정. budget 결정 + I4 모니터링 결정 기록
- [ ] Step 8: 14 calls (gemini 제외). 28건 manual 평가 입력. winner 결정
- [ ] Step 9: score_step8 일반화 완료 또는 한도 초과 시 백로그 이연
- [ ] validation_report_slice2.md 6 섹션 작성
- [ ] refactor_backlog_slice2.md 작성
- [ ] 누적 LLM 호출: ~35/50 (70%)
- [ ] 누적 비용: ~$0.27
- [ ] 회귀: 76 passed 유지
- [ ] Slice 종료 시 비용 가드 reset 메모

---

# 부록 A — 결정 사항 단일 표

| Q   | 결정                                         | 적용 위치              |
| --- | -------------------------------------------- | ---------------------- |
| Q1  | 7 fixture × 2 model = 14 calls (gemini 제외) | Step 8                 |
| Q3  | Step 6 provider = haiku                      | Step 6                 |
| Q4  | intent_match ≥ 3 ∧ no_extra_changes ≥ 3      | score_step8_e5         |
| Q5  | 신설 score_step8_e5.py + Step 9 일반화       | Step 8 + Step 9        |
| Q6  | docs/portfolio/coach/slice1/, slice2/ 분리   | Step 0.4               |
| Q7  | Slice 2 종료 시 비용 가드 reset              | Slice 종결             |
| N1  | JSON 직접 편집 + evaluation_guide 인라인     | Step 6 + Step 8 산출물 |
| N2  | 동등 가중 sqrt(곱) + tradeoff_analysis 보존  | score_step8_e5         |
| N3  | Step 0.5에서 사전 통합 + Slice 1/2 회귀 검증 | Step 0.5               |

# 부록 B — Part 2 신규 파일 목록

| 파일                                                          | 종류                        | 줄 수 (추정) |
| ------------------------------------------------------------- | --------------------------- | ------------ |
| `scripts/validation/run_step6_e5_smoke.py`                    | 실 호출 1회                 | ~130         |
| `scripts/validation/measure_e5_tokens.py`                     | 토큰 측정                   | ~80          |
| `scripts/validation/run_step8_e5_2way.py`                     | 14 calls                    | ~150         |
| `scripts/validation/score_step8_e5.py`                        | 점수 산출 (Step 9에서 통합) | ~200         |
| `scripts/validation/score_step8.py`                           | (확장) 일반화               | ~250         |
| `portfolio/llm/mocks.py`                                      | (확장) text_strategy        | ~100         |
| `portfolio/tests/test_mocks.py`                               | (확장) 단위 테스트          | ~50          |
| `docs/portfolio/coach/slice2/step6_smoke_e5_output.json`      | 실행 산출물                 | —            |
| `docs/portfolio/coach/slice2/step7_e5_token_measurement.json` | 측정 산출물                 | —            |
| `docs/portfolio/coach/slice2/step8_2way_e5_raw.json`          | 실행 산출물                 | —            |
| `docs/portfolio/coach/slice2/step8_2way_e5_scored.json`       | 점수 산출물                 | —            |
| `docs/portfolio/coach/slice2/validation_report_slice2.md`     | 6 섹션 보고서               | ~150         |
| `docs/portfolio/coach/slice2/refactor_backlog_slice2.md`      | Slice 3 백로그              | ~50          |

총 신규 코드: ~860줄 + 산출물 5건 + 보고서 2건.

# 부록 C — 회귀 카운트 진행 표

| 단계                                        | 추가 테스트 | 누적 |
| ------------------------------------------- | ----------- | ---- |
| Part 1 종결 baseline                        | —           | 73   |
| Step 0.4 (Slice 1 산출물 이동)              | 0           | 73   |
| Step 0.5 (Mock 통합 + text_strategy 테스트) | +3          | 76   |
| Step 6 (실 호출, 산출물만)                  | 0           | 76   |
| Step 7 (오프라인 측정, 산출물만)            | 0           | 76   |
| Step 8 (실 호출, 산출물만)                  | 0           | 76   |
| Step 9 (리팩토링, 회귀 유지가 핵심)         | 0           | 76   |

> Part 2는 회귀 추가가 거의 없음. **Step 0.5 통합과 Step 9 일반화에서 회귀 유지가 핵심 KPI**.

# 부록 D — v2 갱신 최소화 체크리스트

본 지시서 작성 시점에 다음을 미리 챙김으로써 v2 갱신 사유 차단:

- [x] **Q1~Q7 + N1~N3 모든 결정 본문 반영** (사후 변경 없음)
- [x] **score_step8_e5.py 차원 키 이름**: `intent_match_manual`, `no_extra_changes_manual` (raw json 필드와 정확히 일치 — 오타 함정 회피)
- [x] **manual 평가 입력 안 한 경우 에러**: `lexicographic_pass`에서 `_missing` 사유 반환 + 가이드 참조
- [x] **reparse_metadata 필드 패턴**: Slice 1과 동일 구조 유지 (역추적 용이)
- [x] **evaluation_guide 인라인**: 산출물 JSON 자체에 평가 기준 포함 (사용자가 별도 문서 참조 불필요)
- [x] **trade-off raw 값 보존**: tradeoff_analysis 섹션 — Slice 3 가중치 결정 자료
- [x] **\_meta_for_step9_generalization**: Step 9 일반화 작업 시 입력 키 명시 — 코드 변경 시 헷갈림 방지
- [x] **Q6 디렉토리 분리에 따른 코드 경로 수정**: Step 0.4에서 검색 후 일괄 수정 (누락 위험 차단)
- [x] **N3.C 충돌 위험**: Step 0.5에서 Slice 1 + Slice 2 회귀 모두 검증 (Mock 통합 후)
- [x] **Step 9 한도 초과 안전판**: 30분 안에 일반화 미완료 시 즉시 중단 + revert + Slice 3 이연 (옵션 C 단점 명시 보완)

위 10개 항목을 본문에 모두 반영함으로써 Slice 1 Part 1 v1→v2 발생한 8건 패턴(Mock 패치, validator, CSV/dict, sleep, 미사용 변수, fixture 일치 등)이 본 슬라이스에서 재발할 가능성 차단.

---

# 진행 트리거

위 체크리스트 모두 통과 시 다음 슬라이스 진입:

> "Slice 3 시작. Step 0 비용 가드 reset 확인 + 부록 B Slice 3 백로그 검토부터."

Slice 3 진입점은 메모리(E1+GARP=Slice 1, E5=Slice 2 후) 다음 자연 순서로 결정 — E5의 후속인 E6 (조정 후 비교 해설) 또는 Tier 2 다음 진입점 E2 (진단 카드 4요소). 결정은 Slice 2 종료 회고 시점에.
