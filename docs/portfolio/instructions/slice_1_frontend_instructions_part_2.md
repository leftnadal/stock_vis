# Slice 1 — Part 2 작업 지시서 (Step 6~9)

> 작성일: 2026-04-29
> 대상: Stock-Vis Portfolio Coach 슬라이스 1 후반부 (검증 + 회고 + 리팩토링)
> 전제: `slice-1-frontend-instructions.md` (Part 1, Step 1~5) 완료, 27 passed
> 브랜치: portfolio
> 누적 LLM 호출: 0 / 50 (비용 가드 한도)

---

## 0. 사전 검증

### 0.1 Part 1 완료 확인 (실행 전 필수)

```bash
# 회귀 테스트 27/27 통과 확인
pytest portfolio/tests/ -q
# 예상: 27 passed in X.Xs

# 환경 변수 활성 검증
python -c "from django.conf import settings; \
  print('GEMINI:', bool(settings.GEMINI_API_KEY)); \
  print('ANTHROPIC:', bool(settings.ANTHROPIC_API_KEY))"
# 예상: GEMINI: True / ANTHROPIC: True
```

위 두 검증이 모두 통과하지 않으면 Part 1으로 되돌아가 회귀 원인 해결 후 진입.

### 0.2 Part 2 결정 사항 (대화 확정)

| Q   | 결정                                                             | 근거                                                         |
| --- | ---------------------------------------------------------------- | ------------------------------------------------------------ |
| Q1  | Step 6 검증 fixture: **garp_tech**                               | 정상 경로 우선 검증, 톤·결측은 Step 8에서 자동 커버          |
| Q2  | garp_large fixture 종목 수: **15**                               | 토큰 예산 70~85% 구간 (μ+1σ 안전 마진), MVP 사용자 상한 정합 |
| Q3  | 3-way 평가 산식: **Lexicographic 필터 + 효율 비교 + B fallback** | Lexicographic preference 의사결정 이론, 기하평균 효율 점수   |
| Q4  | validation_report.md 구조: **6섹션**                             | 자동 생성과 수동 작성 분리, 회귀 비교 가능                   |

### 0.3 비용 가드 예산 분배 (총 50회 한도)

| Step             | 호출 수                 | 누적  | 안전 마진 |
| ---------------- | ----------------------- | ----- | --------- |
| Step 6           | 1                       | 1     | 49        |
| Step 7           | 0 (오프라인 토큰 측정)  | 1     | 49        |
| Step 8           | 9 (3 fixture × 3 model) | 10    | 40        |
| Step 8 재시도    | 0~3                     | 10~13 | 37~40     |
| Step 9           | 0 (오프라인 리팩토링)   | 10~13 | 37~40     |
| 회귀/디버깅 예비 | 0~5                     | 10~18 | 32~40     |

`LLM_BUDGET_MAX_CALLS=50` env 변경 없음. 누적 호출은 `portfolio/llm/client.py`의 카운터로 추적.

---

# Step 6 — 실제 Gemini Flash 1회 호출 검증

## 6.1 목표

`garp_tech` fixture를 사용해 실제 Gemini Flash API를 1회 호출하고, 4개 판정 기준을 모두 통과하는지 검증한다. **정상 경로(happy path)의 end-to-end 작동 확인**이 목적이며, 톤·결측·일반화 검증은 Step 8에서 다룬다.

## 6.2 사전 조건

- Part 1 Step 1~5 완료 (27 passed)
- `garp_tech` fixture 정상 로드 확인:
  ```bash
  python -c "from portfolio.tests.fixtures.sample_analysis_context import get_context_garp_tech; \
    ctx = get_context_garp_tech(); \
    print(f'holdings={len(ctx[\"holdings\"])}, metrics_keys={len(ctx[\"metrics\"])}')"
  # 예상: holdings=5, metrics_keys=5 (또는 metric_id 단위 53)
  ```
- Gemini API key 활성 확인:
  ```bash
  curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY" \
    | python -c "import sys, json; d=json.load(sys.stdin); print('OK', len(d.get('models',[])))"
  # 예상: OK XX
  ```

## 6.3 작업 단계

### 6.3.1 검증 스크립트 디렉토리 신설

```bash
mkdir -p scripts/validation
touch scripts/validation/__init__.py
```

### 6.3.2 `scripts/validation/run_step6_smoke.py` 신설

```python
"""
Step 6: garp_tech fixture로 실제 Gemini Flash 1회 호출 검증.

판정 4개:
  1. Schema 통과: Pydantic E1Response validation
  2. 한국어 자연스러움: 수동 평가 (1-5), 후처리 단계
  3. 비용: cost_usd <= $0.001
  4. 지연: latency_ms <= 5000

Usage:
    python -m scripts.validation.run_step6_smoke
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockvis.settings")
django.setup()

from portfolio.llm.client import LLMClient
from portfolio.services.e1_garp import build_e1_garp_prompt, parse_e1_response
from portfolio.tests.fixtures.sample_analysis_context import get_context_garp_tech

THRESHOLDS = {
    "cost_usd_max": 0.001,
    "latency_ms_max": 5000,
}


def main() -> int:
    print("=" * 60)
    print("Step 6 Smoke Test — Gemini Flash + garp_tech")
    print(f"Run at: {datetime.utcnow().isoformat()}Z")
    print("=" * 60)

    ctx = get_context_garp_tech()
    prompt = build_e1_garp_prompt(ctx)

    client = LLMClient(provider="gemini")
    raw = client.invoke(prompt=prompt)

    # Judgment 1: Schema 통과
    try:
        parsed = parse_e1_response(raw.content)
        schema_pass = True
        schema_error = None
    except Exception as e:
        parsed = None
        schema_pass = False
        schema_error = str(e)

    # Judgment 3: 비용
    cost_pass = raw.cost_usd <= THRESHOLDS["cost_usd_max"]

    # Judgment 4: 지연
    latency_pass = raw.latency_ms <= THRESHOLDS["latency_ms_max"]

    output_path = Path("portfolio/docs/step6_smoke_output.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "provider": raw.provider,
                    "model": raw.model,
                    "fixture": "garp_tech",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "input_tokens": raw.input_tokens,
                    "output_tokens": raw.output_tokens,
                    "latency_ms": raw.latency_ms,
                    "cost_usd": raw.cost_usd,
                    "fallback_from": raw.fallback_from,
                },
                "raw_content": raw.content,
                "parsed": parsed.model_dump() if parsed else None,
                "judgments": {
                    "schema_pass": schema_pass,
                    "schema_error": schema_error,
                    "cost_pass": cost_pass,
                    "latency_pass": latency_pass,
                    "naturalness": "MANUAL_REVIEW_PENDING",
                },
                "thresholds": THRESHOLDS,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\n[Output] {output_path}")
    print("\nJudgments:")
    print(f"  1. Schema 통과:        {'✓' if schema_pass else '✗ ' + (schema_error or '')}")
    print(f"  2. 한국어 자연스러움:    수동 평가 → step6_smoke_output.json 확인")
    print(
        f"  3. 비용:               {'✓' if cost_pass else '✗'} "
        f"(${raw.cost_usd:.6f} / ${THRESHOLDS['cost_usd_max']:.4f})"
    )
    print(
        f"  4. 지연:               {'✓' if latency_pass else '✗'} "
        f"({raw.latency_ms}ms / {THRESHOLDS['latency_ms_max']}ms)"
    )

    if not (schema_pass and cost_pass and latency_pass):
        print("\n[RESULT] FAIL — 자동 판정 미통과. 6.5 롤백 절차 참조.")
        return 1

    print("\n[RESULT] 자동 판정 PASS. 한국어 자연스러움 수동 평가 후 Step 7 진입.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 6.3.3 실행

```bash
python -m scripts.validation.run_step6_smoke
```

### 6.3.4 한국어 자연스러움 수동 평가 (Judgment 2)

`portfolio/docs/step6_smoke_output.json`을 열어 `raw_content` 또는 `parsed` 필드를 확인.

평가 기준 (1~5):

| 점수 | 의미                                             |
| ---- | ------------------------------------------------ |
| 5    | 한국 투자자 글로 봐도 손색 없음. 어순/조사 자연. |
| 4    | 자연스럽지만 한두 군데 어색.                     |
| 3    | 의미 전달은 되지만 외국어 직역체 느낌.           |
| 2    | 어색해서 이해에 부담.                            |
| 1    | 한국어로 보기 어려움.                            |

**판정 통과 기준**: ≥ 3.

평가 결과를 `step6_smoke_output.json`의 `judgments.naturalness` 필드에 직접 수정 (예: `"naturalness": 4`).

## 6.4 검증 판정 (4개 종합)

| #   | 판정              | 임계                     | 자동/수동 |
| --- | ----------------- | ------------------------ | --------- |
| 1   | Schema 통과       | Pydantic validation = OK | 자동      |
| 2   | 한국어 자연스러움 | ≥ 3 / 5                  | 수동      |
| 3   | 비용              | ≤ $0.001                 | 자동      |
| 4   | 지연              | ≤ 5000ms                 | 자동      |

**4개 모두 통과 시**: Step 7 진입.
**1개라도 미통과 시**: 6.5 롤백 절차.

## 6.5 롤백 / 실패 시 처리

### 케이스 A: Schema 미통과

- 원인 후보: 프롬프트의 응답 형식 지시 부족, Gemini 출력 형식 불일치 (마크다운 펜스, 추가 텍스트 등).
- 조치:
  - `portfolio/services/e1_garp.py`의 `build_e1_garp_prompt`에 "JSON 객체만 반환, 마크다운 펜스 금지, 추가 설명 금지" 명시.
  - `parse_e1_response`에서 `json ... ` 펜스 제거 전처리 추가 가능.
  - 재실행 1회 (누적 2회).
- 1회 재시도 후 실패 시 → Part 1 회귀.

### 케이스 B: 한국어 자연스러움 < 3

- 원인 후보: 프롬프트의 페르소나/톤 지시 부족.
- 조치:
  - 프롬프트 system message에 "한국 개인 투자자에게 친근한 한국어로 답변. 영어 직역 금지" 명시.
  - 임시 통과 처리 가능 (Step 8 회고에서 재평가하고 그때 결정).

### 케이스 C: 비용 > $0.001

- 원인 후보: 프롬프트 너무 김, 출력 토큰 제한 없음.
- 조치:
  - `max_tokens=1024` (또는 less) LLMClient에 명시.
  - 프롬프트 내 메트릭 정보 압축 (예: percentile만 전달, raw value는 생략).
  - 재측정 후 실패 시 → Step 7 token 사이징 단계에서 본격 검토.

### 케이스 D: 지연 > 5000ms

- 원인 후보: Gemini API 일시 지연, 네트워크.
- 조치: 30분 후 재실행. 3회 측정 평균이 5000ms 초과 시 환경 문제로 판정 보류, validation report에 기록.

## 6.6 산출물

- `scripts/validation/__init__.py` (신규, 빈 파일)
- `scripts/validation/run_step6_smoke.py` (신규, ~110줄)
- `portfolio/docs/step6_smoke_output.json` (실행 산출물, manual review 필드 포함)
- 자동 판정 통과 + 자연스러움 ≥ 3 → Step 7 진입 신호

## 6.7 비용 가드

- LLM 호출: 1회 (재시도 포함 최대 2회)
- 누적: 1~2 / 50

---

# Step 7 — garp_large fixture (종목 15개) + 토큰 예산 검증

## 7.1 목표

종목 15개 규모의 `garp_large` fixture를 추가하고, D-8 검증에서 정해진 진입점별 토큰 예산을 초과하지 않는지 **오프라인 측정으로** 검증한다. 실제 LLM 호출 없음 (Gemini count_tokens 메서드는 무료).

## 7.2 사전 조건

- Step 6 통과
- D-8 토큰 예산 정의 확인:
  ```bash
  grep -A 5 -E "(token_budget|TOKEN_BUDGET)" portfolio/docs/validation_report.md
  ```

해당 값이 명시 안 됐으면 D-0b/D-8 산출물에서 추출. 본 지시서는 다음 추정값 사용 (실제 값과 다르면 수정 후 재측정):

```python
TOKEN_BUDGETS = {
    "E1_input": 8000,
    "E1_output": 1500,
    "E2_input": 6000,
    "E2_output": 1200,
    "E3_input": 5000,
    "E3_output": 1000,
    "E6_input": 7000,
    "E6_output": 1500,
}
```

## 7.3 작업 단계

### 7.3.1 garp_large fixture 추가

`portfolio/tests/fixtures/sample_analysis_context.py`에 함수 추가:

```python
def get_context_garp_large() -> dict:
    """
    GARP 프리셋용 large fixture. 종목 15개.

    사이징 근거 (퀀트 공학):
    - 종목 수 15는 개인 투자자 분산 한도(10~20)의 중앙값.
    - input 토큰 추정: 메트릭 53개 × 종목당 ~150토큰 ≈ 5,200~6,000.
    - E1_input budget 8000의 65~75% 점유 (정보 비율 최대화 구간 70~85% 내).
    - μ+1σ 안전 마진 (분산 고려 시 일시적 80% 가능, 95% 미달).

    종목 분포 (lexicographic + 진단 카드 다양성 동시 충족):
    - 5개 GARP 정합 (PEG 0.8~1.3, ROIC > 12%, EPS growth > 10%) → 강점 카드
    - 5개 부분 적합 (지표 일부 통과) → 보완 제안
    - 5개 부정합 (PEG > 2.0 또는 ROIC < 8%) → 약점 카드 또는 제외 제안
    """
    holdings = [
        # GARP 정합 5종목 (가중치 합 0.37)
        {"ticker": "MSFT", "weight": 0.10, "asset_type": "stock"},
        {"ticker": "GOOGL", "weight": 0.08, "asset_type": "stock"},
        {"ticker": "V", "weight": 0.07, "asset_type": "stock"},
        {"ticker": "MA", "weight": 0.06, "asset_type": "stock"},
        {"ticker": "ADBE", "weight": 0.06, "asset_type": "stock"},
        # 부분 적합 5종목 (가중치 합 0.34)
        {"ticker": "AAPL", "weight": 0.08, "asset_type": "stock"},
        {"ticker": "AMZN", "weight": 0.07, "asset_type": "stock"},
        {"ticker": "META", "weight": 0.06, "asset_type": "stock"},
        {"ticker": "AVGO", "weight": 0.06, "asset_type": "stock"},
        {"ticker": "NVDA", "weight": 0.07, "asset_type": "stock"},
        # 부정합 5종목 (가중치 합 0.29)
        {"ticker": "TSLA", "weight": 0.05, "asset_type": "stock"},
        {"ticker": "NFLX", "weight": 0.05, "asset_type": "stock"},
        {"ticker": "CRM", "weight": 0.06, "asset_type": "stock"},
        {"ticker": "PLTR", "weight": 0.06, "asset_type": "stock"},
        {"ticker": "SHOP", "weight": 0.07, "asset_type": "stock"},
    ]
    # 가중치 합 검증: 0.37 + 0.34 + 0.29 = 1.00

    # 메트릭 채우기 가이드:
    # - get_context_garp_tech()의 메트릭 구조 그대로 따름
    # - 위 분포에 맞게 PEG, ROIC, EPS_growth 의도적으로 차별화
    # - 다른 50개 메트릭은 ticker별 plausible 값 (기존 fixture에서 복사 + jitter 가능)
    # - percentile은 0~100 정수, level은 1~5 (5단계)
    metrics = _build_garp_large_metrics(holdings)

    return {
        "preset_id": "garp",
        "preset_version": "v1.0",
        "metric_version": "v1.0",
        "scoring_version": "v1.0",
        "prompt_version": "v1.0",
        "universe_version": "v1.0",
        "holdings": holdings,
        "metrics": metrics,
        "diagnostic_metadata": {
            "industry_classifications": _build_industry_map(holdings),
            "comparison_meta": {"universe": "S&P 500 + sector peers"},
        },
    }


def _build_garp_large_metrics(holdings: list[dict]) -> dict:
    """
    Helper. 종목 15개 × 메트릭 53개 채움.
    PEG/ROIC/EPS_growth는 의도적 분포, 나머지는 plausible random.

    구현 시 결정 사항:
    - 정합 5종목: PEG ∈ [0.8, 1.3], ROIC ∈ [13, 25], EPS_growth ∈ [11, 25]
    - 부분 5종목: 위 3개 중 1~2개만 통과 범위, 나머지 borderline
    - 부정합 5종목: PEG > 2.0 OR ROIC < 8%
    - percentile은 raw value 분포에 맞춰 정수값 부여
    - level (1~5)은 percentile에서 자동 변환 (20/40/60/80 기준)
    """
    # 구현 상세는 본인 자유. 단, 분포가 위 의도를 따르도록 검증.
    raise NotImplementedError("구현 필요. metrics/preset_metrics.py의 GARP 지표 53개 모두 채움.")


def _build_industry_map(holdings: list[dict]) -> dict:
    """
    Helper. 종목별 산업 분류. FMP API 분류 그대로 또는 GICS 4단계.
    """
    # 예시:
    return {
        "MSFT": "Software", "GOOGL": "Internet", "V": "Financial Services",
        "MA": "Financial Services", "ADBE": "Software", "AAPL": "Consumer Electronics",
        "AMZN": "Internet", "META": "Internet", "AVGO": "Semiconductors",
        "NVDA": "Semiconductors", "TSLA": "Auto", "NFLX": "Media",
        "CRM": "Software", "PLTR": "Software", "SHOP": "Internet",
    }
```

**중요**: `_build_garp_large_metrics`의 실제 구현은 기존 `get_context_garp_tech()`의 메트릭 구조를 보고 따라가면 됨. 53개 지표 모두 채우기. metric_id가 `preset_metrics.py`의 GARP 지표 목록과 일치하는지 검증.

### 7.3.2 토큰 측정 스크립트 신설

`scripts/validation/measure_tokens.py` 신설:

```python
"""
Step 7: 3개 fixture의 토큰 사용량 측정 (오프라인).

D-8 토큰 예산 (E1) 대비 below range 검증.

Usage:
    python -m scripts.validation.measure_tokens
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockvis.settings")
django.setup()

import google.generativeai as genai
from django.conf import settings

from portfolio.services.e1_garp import build_e1_garp_prompt
from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_large,
    get_context_garp_misfit,
    get_context_garp_tech,
)

# D-8에서 정해진 budget. 실제 값으로 교체.
TOKEN_BUDGETS = {
    "E1_input": 8000,
}


def count_tokens(prompt: str) -> int:
    """Gemini 토크나이저. tiktoken 대비 정확도 우선 (실제 호출 모델과 동일)."""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    return model.count_tokens(prompt).total_tokens


def main() -> int:
    print("=" * 60)
    print("Step 7 — Fixture 토큰 사용량 측정")
    print("=" * 60)

    fixtures = {
        "garp_tech": get_context_garp_tech(),
        "garp_misfit": get_context_garp_misfit(),
        "garp_large": get_context_garp_large(),
    }

    rows = []
    budget = TOKEN_BUDGETS["E1_input"]
    for name, ctx in fixtures.items():
        prompt = build_e1_garp_prompt(ctx)
        tokens = count_tokens(prompt)
        utilization = tokens / budget
        # garp_large만 70~85% 안전 구간 검증
        if name == "garp_large":
            in_safe_range = 0.70 <= utilization <= 0.85
        else:
            in_safe_range = utilization <= 0.85
        rows.append(
            {
                "fixture": name,
                "input_tokens": tokens,
                "budget": budget,
                "utilization_pct": round(utilization * 100, 1),
                "in_safe_range": in_safe_range,
            }
        )

    print(f"\n{'Fixture':<14} {'Tokens':>8} {'Budget':>8} {'Util':>8} {'Safe':>6}")
    for r in rows:
        mark = "✓" if r["in_safe_range"] else "✗"
        print(
            f"{r['fixture']:<14} {r['input_tokens']:>8} {r['budget']:>8} "
            f"{r['utilization_pct']:>7.1f}% {mark:>6}"
        )

    large_row = next(r for r in rows if r["fixture"] == "garp_large")
    if not large_row["in_safe_range"]:
        print(
            f"\n[FAIL] garp_large utilization {large_row['utilization_pct']}% "
            f"outside [70%, 85%]."
        )
        print("       Fixture 종목 수 또는 메트릭 정보를 조정 필요.")
        return 1

    print(
        f"\n[PASS] garp_large utilization {large_row['utilization_pct']}% within [70%, 85%]."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 7.3.3 fixture validation 테스트 추가

`portfolio/tests/test_fixtures_validation.py` 신설:

```python
import pytest

from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_large,
    get_context_garp_misfit,
    get_context_garp_tech,
)


@pytest.mark.parametrize(
    "loader",
    [get_context_garp_tech, get_context_garp_misfit, get_context_garp_large],
)
def test_fixture_weights_sum_to_one(loader):
    ctx = loader()
    total = sum(h["weight"] for h in ctx["holdings"])
    assert abs(total - 1.0) < 0.001, f"weights sum to {total}, expected 1.0"


@pytest.mark.parametrize(
    "loader,expected_n",
    [
        (get_context_garp_tech, 5),
        (get_context_garp_misfit, 5),
        (get_context_garp_large, 15),
    ],
)
def test_fixture_holdings_count(loader, expected_n):
    ctx = loader()
    assert len(ctx["holdings"]) == expected_n


def test_garp_large_metrics_completeness():
    """53개 지표 × 15종목 모두 채움. None 비율 < 5%."""
    ctx = get_context_garp_large()
    none_count = 0
    total_count = 0
    for ticker_metrics in ctx["metrics"].values():
        for value in ticker_metrics.values():
            total_count += 1
            if value is None:
                none_count += 1
    assert total_count > 0, "metrics empty"
    none_ratio = none_count / total_count
    assert none_ratio < 0.05, f"None ratio {none_ratio:.1%} >= 5%"


def test_garp_large_distribution():
    """5/5/5 분포 (정합/부분/부정합) 검증."""
    ctx = get_context_garp_large()
    fit_count = partial_count = misfit_count = 0
    for ticker, m in ctx["metrics"].items():
        peg = m.get("PEG_ratio")
        roic = m.get("ROIC")
        eps_g = m.get("EPS_growth_3y")
        if peg is None or roic is None or eps_g is None:
            continue
        is_fit = 0.8 <= peg <= 1.3 and roic > 12 and eps_g > 10
        is_misfit = peg > 2.0 or roic < 8
        if is_fit:
            fit_count += 1
        elif is_misfit:
            misfit_count += 1
        else:
            partial_count += 1
    assert fit_count == 5, f"fit_count={fit_count}, expected 5"
    assert misfit_count == 5, f"misfit_count={misfit_count}, expected 5"
    assert partial_count == 5, f"partial_count={partial_count}, expected 5"
```

### 7.3.4 실행

```bash
# 토큰 측정
python -m scripts.validation.measure_tokens
# 예상:
#   Fixture        Tokens   Budget     Util   Safe
#   garp_tech        2100     8000    26.3%      ✓
#   garp_misfit      2050     8000    25.6%      ✓
#   garp_large       5900     8000    73.8%      ✓
#   [PASS] garp_large utilization 73.8% within [70%, 85%].

# Fixture validation 테스트
pytest portfolio/tests/test_fixtures_validation.py -v
# 예상: 8 passed (3 fixtures × 2 + 2)

# 전체 회귀
pytest portfolio/tests/ -q
# 예상: 35 passed (27 + 8)
```

## 7.4 검증 판정

| #   | 판정                                | 임계                   | 자동                  |
| --- | ----------------------------------- | ---------------------- | --------------------- |
| 1   | garp_large input tokens             | budget의 70~85%        | 자동 (measure_tokens) |
| 2   | garp_tech, garp_misfit input tokens | ≤ budget의 85%         | 자동 (measure_tokens) |
| 3   | weight 합 = 1.0                     | abs(sum - 1.0) < 0.001 | 자동 (test)           |
| 4   | metrics None 비율                   | < 5%                   | 자동 (test)           |
| 5   | 5/5/5 분포                          | exact match            | 자동 (test)           |
| 6   | 회귀 테스트                         | 35/35 passed           | 자동                  |

## 7.5 롤백 / 실패 시 처리

### 케이스 A: garp_large utilization < 70%

- 종목 수 부족 또는 메트릭 표현 압축이 과해서 token 적음. stress 의미 약함.
- 조치: 메트릭 표현 풍부화 (raw value + percentile + level 모두 포함) 또는 종목 1~2개 추가 (15→17). 재측정.

### 케이스 B: garp_large utilization > 85%

- 토큰 폭주.
- 조치: 메트릭 표현 압축 (percentile만) 또는 종목 1~2개 감소 (15→13). 재측정.

### 케이스 C: weight 합 ≠ 1.0

- 단순 산술 실수. test가 자동 잡음.
- 조치: weight 재계산 후 fixture 수정.

### 케이스 D: 5/5/5 분포 검증 실패

- 메트릭 채우기에서 조건 분포 누락.
- 조치: `_build_garp_large_metrics` 재작성 후 재실행.

### 케이스 E: D-8 토큰 budget 값 불확실

- 본 지시서 추정값(E1_input=8000) 사용 중.
- 조치: D-8 산출물 재확인 후 정확한 값으로 `TOKEN_BUDGETS` 갱신, 재측정. 추정값과 ±10% 이내면 결과는 통상 동일.

## 7.6 산출물

- `portfolio/tests/fixtures/sample_analysis_context.py`에 `get_context_garp_large()` 추가
- `scripts/validation/measure_tokens.py` 신규 (~70줄)
- `portfolio/tests/test_fixtures_validation.py` 신규 (~70줄)
- 누적 테스트: 27 + 8 = 35 passed

## 7.7 비용 가드

- LLM 호출: 0회 (Gemini count_tokens 무료)
- 누적: 1~2 / 50

---

# Step 8 — 3-way 회고 (9회 호출 + Lexicographic Scoring + Validation Report)

## 8.1 목표

3 fixture × 3 model = 9회 실제 LLM 호출을 수행하고, Lexicographic preference + 효율 비교 + B fallback 산식으로 모델 우열을 정량 판정한다. 결과를 `validation_report_slice1.md`에 6섹션 구조로 기록한다.

## 8.2 사전 조건

- Step 6, 7 통과 (35 passed)
- 3개 모델 API key 활성:
  - Gemini Flash (`GEMINI_API_KEY`)
  - Claude Sonnet 4.5 (`ANTHROPIC_API_KEY`)
  - Claude Haiku 4.5 (`ANTHROPIC_API_KEY` 동일)
- LLMClient에 3 provider 모두 분기 구현 확인:
  ```bash
  grep -E "(gemini|sonnet|haiku)" portfolio/llm/client.py
  ```
  세 모델 식별자가 모두 등장해야 함. 하나라도 누락 시 LLMClient 갱신이 **Step 8 진입 전 필수 조건** (Step 9 리팩토링 슬롯이 아님).

권장 모델 매핑 (LLMClient 내부):

```python
PROVIDER_MODELS = {
    "gemini": "gemini-2.0-flash-exp",
    "sonnet": "claude-sonnet-4-5",
    "haiku": "claude-haiku-4-5",
}
```

## 8.3 작업 단계

### 8.3.1 9회 호출 스크립트 신설

`scripts/validation/run_step8_3way.py` 신설:

```python
"""
Step 8: 3 fixture × 3 model = 9회 호출. raw 결과를 step8_3way_raw.json에 저장.

수동 평가 (naturalness, insight) 후 score_step8.py 실행.

Usage:
    python -m scripts.validation.run_step8_3way
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockvis.settings")
django.setup()

from portfolio.llm.client import LLMClient
from portfolio.services.e1_garp import build_e1_garp_prompt, parse_e1_response
from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_large,
    get_context_garp_misfit,
    get_context_garp_tech,
)

FIXTURES = {
    "garp_tech": get_context_garp_tech,
    "garp_misfit": get_context_garp_misfit,
    "garp_large": get_context_garp_large,
}
PROVIDERS = ["gemini", "sonnet", "haiku"]


def call_one(provider: str, fixture_name: str, ctx_fn) -> dict:
    ctx = ctx_fn()
    prompt = build_e1_garp_prompt(ctx)
    client = LLMClient(provider=provider)
    try:
        raw = client.invoke(prompt=prompt)
        try:
            parsed = parse_e1_response(raw.content)
            schema_pass = True
            schema_error = None
        except Exception as e:
            parsed = None
            schema_pass = False
            schema_error = str(e)
        return {
            "provider": provider,
            "model": raw.model,
            "fixture": fixture_name,
            "input_tokens": raw.input_tokens,
            "output_tokens": raw.output_tokens,
            "latency_ms": raw.latency_ms,
            "cost_usd": raw.cost_usd,
            "fallback_from": raw.fallback_from,
            "raw_content": raw.content,
            "parsed": parsed.model_dump() if parsed else None,
            "schema_pass": schema_pass,
            "schema_error": schema_error,
            "naturalness": None,  # 수동 평가
            "insight": None,  # 수동 평가
            "error": None,
        }
    except Exception as e:
        return {
            "provider": provider,
            "fixture": fixture_name,
            "error": str(e),
            "schema_pass": False,
            "naturalness": None,
            "insight": None,
        }


def main() -> int:
    print("=" * 60)
    print("Step 8 — 3-way 회고 (9 calls)")
    print(f"Run at: {datetime.utcnow().isoformat()}Z")
    print("=" * 60)

    results = []
    call_idx = 0
    for fixture_name, ctx_fn in FIXTURES.items():
        for provider in PROVIDERS:
            call_idx += 1
            print(f"[{call_idx}/9] {provider} × {fixture_name} ...", end=" ", flush=True)
            r = call_one(provider, fixture_name, ctx_fn)
            results.append(r)
            if r.get("error"):
                print(f"ERROR: {r['error']}")
            else:
                print(f"OK ({r['latency_ms']}ms, ${r['cost_usd']:.5f})")

    output_path = Path("portfolio/docs/step8_3way_raw.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "total_calls": len(results),
                    "errors": sum(1 for r in results if r.get("error")),
                    "total_cost_usd": sum(r.get("cost_usd") or 0 for r in results),
                },
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\n[Saved] {output_path}")
    print("\n다음 단계: 9개 응답을 직접 보고 naturalness/insight 평가 (1~5).")
    print(f"수정 대상: {output_path}의 각 entry의 'naturalness', 'insight' 필드.")
    print("평가 완료 후: python -m scripts.validation.score_step8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 8.3.2 9회 호출 실행

```bash
python -m scripts.validation.run_step8_3way
```

비용 가드: 9회 + (rate limit/timeout 시 재시도) 0~3회 = 최대 12회. 누적 10~13/50.

### 8.3.3 수동 평가 (Naturalness + Insight)

`portfolio/docs/step8_3way_raw.json`을 열어 9개 entry의 `raw_content` (또는 `parsed`)를 보고 평가:

**Naturalness (한국어 자연스러움)**: 1~5

| 점수 | 의미                                 |
| ---- | ------------------------------------ |
| 5    | 한국 전문 투자자 글로 봐도 손색 없음 |
| 4    | 자연스럽지만 한두 군데 어색          |
| 3    | 의미 전달 OK, 직역체 약간            |
| 2    | 어색해서 이해에 부담                 |
| 1    | 한국어로 보기 어려움                 |

**Insight (진단 통찰성)**: 1~5 — 카드 4요소(무엇이/기준/왜 중요/예외) 충실도

| 점수 | 의미                                                |
| ---- | --------------------------------------------------- |
| 5    | 4요소 모두 충실. 사용자가 새로운 사실을 인지하게 됨 |
| 4    | 4요소 충실하나 1개가 일반론                         |
| 3    | 3개 충실, 1개 누락 또는 일반론                      |
| 2    | 2개 이상 누락. 카드 가치 약함                       |
| 1    | 형식만 충족, 내용 없음                              |

각 entry의 `naturalness`, `insight` 필드에 정수값(1~5)을 직접 입력 (현재 null).

### 8.3.4 점수 산출 스크립트 신설

`scripts/validation/score_step8.py` 신설:

```python
"""
Step 8 평가 점수 산출. step8_3way_raw.json의 수동 평가 완료 후 실행.

산식:
  1차 필터 (Lexicographic Hard Gate):
    PASS = (schema_pass = True) AND (naturalness >= 3) AND (insight >= 3)

  2차 비교 (PASS 통과 모델만, efficiency mode):
    EfficiencyScore = sqrt(naturalness * insight) / sqrt(cost_usd * latency_seconds)

  Fallback (모든 9회 1차 미통과 시, B fallback mode):
    Score = 0.25 * schema + 0.25 * naturalness_norm + 0.25 * insight_norm
          + 0.15 * cost_inv_norm + 0.10 * latency_inv_norm
    where:
      naturalness_norm = naturalness / 5
      insight_norm = insight / 5
      cost_inv_norm = (max_cost - cost) / (max_cost - min_cost) if max>min else 1.0
      latency_inv_norm = (max_lat - lat) / (max_lat - min_lat) if max>min else 1.0

가중치 근거 (퀀트 공학):
  - schema/자연스러움/통찰성 (사용자 가치 핵심): 각 0.25, 합 0.75
  - cost (운영 비용, 분산 작음): 0.15
  - latency (운영 비용, 분산 작음): 0.10
  - 사용자 가치 75% : 운영 비용 25% 비율은 MVP 단계 선호 반영

Usage:
    python -m scripts.validation.score_step8
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


def lexicographic_filter(r: dict) -> bool:
    return (
        r.get("schema_pass") is True
        and isinstance(r.get("naturalness"), (int, float))
        and r["naturalness"] >= 3
        and isinstance(r.get("insight"), (int, float))
        and r["insight"] >= 3
    )


def efficiency_score(r: dict) -> float:
    n = r["naturalness"]
    i = r["insight"]
    c = max(r.get("cost_usd") or 1e-6, 1e-6)
    l = max((r.get("latency_ms") or 1) / 1000.0, 1e-6)
    return math.sqrt(n * i) / math.sqrt(c * l)


def fallback_score(r: dict, all_results: list[dict]) -> float:
    schema = 1.0 if r.get("schema_pass") else 0.0
    n_norm = (r.get("naturalness") or 0) / 5.0
    i_norm = (r.get("insight") or 0) / 5.0

    costs = [x["cost_usd"] for x in all_results if x.get("cost_usd") is not None]
    latencies = [x["latency_ms"] for x in all_results if x.get("latency_ms") is not None]
    if not costs or not latencies:
        return 0.0
    max_c, min_c = max(costs), min(costs)
    max_l, min_l = max(latencies), min(latencies)
    cost_v = r.get("cost_usd")
    lat_v = r.get("latency_ms")
    if cost_v is None or lat_v is None:
        return 0.0
    cost_inv = (max_c - cost_v) / (max_c - min_c) if max_c > min_c else 1.0
    lat_inv = (max_l - lat_v) / (max_l - min_l) if max_l > min_l else 1.0
    return 0.25 * schema + 0.25 * n_norm + 0.25 * i_norm + 0.15 * cost_inv + 0.10 * lat_inv


def main() -> int:
    raw_path = Path("portfolio/docs/step8_3way_raw.json")
    if not raw_path.exists():
        print(f"[ERROR] {raw_path} 없음. run_step8_3way 먼저 실행.")
        return 1

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    results = raw["results"]

    # 수동 평가 누락 검증
    missing = [
        f"{r.get('provider')}×{r.get('fixture')}"
        for r in results
        if not r.get("error")
        and (r.get("naturalness") is None or r.get("insight") is None)
    ]
    if missing:
        print(f"[ERROR] 다음 entry의 수동 평가 미완료: {missing}")
        return 1

    passed = [r for r in results if lexicographic_filter(r)]
    failed = [r for r in results if not lexicographic_filter(r)]

    print("=" * 60)
    print("Step 8 Scoring Result")
    print("=" * 60)
    print(f"\n1차 필터 통과: {len(passed)} / {len(results)}")
    print(f"1차 필터 미통과: {len(failed)}")

    use_fallback = len(passed) == 0
    print(f"\nMode: {'FALLBACK (전체 미통과)' if use_fallback else 'EFFICIENCY'}")

    scored = []
    for r in results:
        if use_fallback:
            s = fallback_score(r, results)
            label = "fallback"
        elif lexicographic_filter(r):
            s = efficiency_score(r)
            label = "efficiency"
        else:
            s = None
            label = "filtered_out"
        scored.append({**r, "score": s, "score_type": label})

    model_scores = defaultdict(list)
    for r in scored:
        if r["score"] is not None:
            model_scores[r["provider"]].append(r["score"])
    model_means = {p: sum(v) / len(v) for p, v in model_scores.items() if v}

    print("\n=== Per Call ===")
    print(
        f"{'Fixture':<14} {'Provider':<10} {'Schema':>6} {'Nat':>4} {'Ins':>4} "
        f"{'Cost':>9} {'Lat(s)':>7} {'Score':>10} {'Type':<14}"
    )
    for r in scored:
        s_str = f"{r['score']:.2f}" if r["score"] is not None else "—"
        sch = "✓" if r.get("schema_pass") else "✗"
        cost = r.get("cost_usd") or 0
        lat_s = (r.get("latency_ms") or 0) / 1000
        print(
            f"{r.get('fixture',''):<14} {r.get('provider',''):<10} "
            f"{sch:>6} {r.get('naturalness') or '—':>4} {r.get('insight') or '—':>4} "
            f"${cost:>7.5f} {lat_s:>7.2f} {s_str:>10} {r['score_type']:<14}"
        )

    print("\n=== Per Provider (mean score) ===")
    for p, m in sorted(model_means.items(), key=lambda x: -x[1]):
        print(f"  {p:<10}: {m:.2f}  (n={len(model_scores[p])})")

    if model_means:
        winner = max(model_means.items(), key=lambda x: x[1])
        print(f"\n[WINNER] {winner[0]} (mean score {winner[1]:.2f})")

    output_path = Path("portfolio/docs/step8_3way_scored.json")
    output_path.write_text(
        json.dumps(
            {
                "scored_results": scored,
                "model_means": model_means,
                "use_fallback": use_fallback,
                "winner": (winner[0] if model_means else None),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n[Saved] {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 8.3.5 점수 산출 실행

```bash
python -m scripts.validation.score_step8
```

### 8.3.6 validation_report_slice1.md 작성

`portfolio/docs/validation_report_slice1.md` 신설. 6섹션 구조 그대로.

```markdown
# Validation Report — Slice 1

> 슬라이스: E1 + GARP + 종목 5/15
> 작성일: YYYY-MM-DD
> 브랜치: portfolio
> 이전 보고: portfolio/docs/validation_report.md (D-8까지)

## 1. Metadata

| 항목              | 값                                                                                                            |
| ----------------- | ------------------------------------------------------------------------------------------------------------- |
| Slice 범위        | E1 GARP, fixture 3종 (garp_tech / garp_misfit / garp_large), 모델 3종 (Gemini Flash / Sonnet 4.5 / Haiku 4.5) |
| 호출 시점 (UTC)   | step8_3way_raw.json metadata.timestamp 복사                                                                   |
| LLMClient git SHA | `git rev-parse HEAD` 결과                                                                                     |
| preset_version    | v1.0                                                                                                          |
| metric_version    | v1.0                                                                                                          |
| scoring_version   | v1.0                                                                                                          |
| prompt_version    | v1.0                                                                                                          |
| universe_version  | v1.0                                                                                                          |
| 누적 LLM 호출     | XX / 50                                                                                                       |
| 누적 비용 (USD)   | $X.XX                                                                                                         |

## 2. Call Log (자동 생성: step8_3way_raw.json 기반)

| #   | Fixture     | Provider | Model                | Input | Output | Latency(ms) | Cost(USD) | Fallback |
| --- | ----------- | -------- | -------------------- | ----- | ------ | ----------- | --------- | -------- |
| 1   | garp_tech   | gemini   | gemini-2.0-flash-exp | 2100  | 850    | 1820        | $0.00038  | —        |
| 2   | garp_tech   | sonnet   | claude-sonnet-4-5    | 2100  | 920    | 3450        | $0.01890  | —        |
| 3   | garp_tech   | haiku    | claude-haiku-4-5     | 2100  | 880    | 2100        | $0.00420  | —        |
| 4   | garp_misfit | gemini   | ...                  | ...   | ...    | ...         | ...       | ...      |
| ... |

## 3. Scoring (자동 생성: step8_3way_scored.json 기반)

### 3.1 1차 필터 (Lexicographic Hard Gate)

조건: `schema_pass = True AND naturalness ≥ 3 AND insight ≥ 3`

| Fixture     | gemini | sonnet | haiku |
| ----------- | ------ | ------ | ----- |
| garp_tech   | ✓/✗    | ✓/✗    | ✓/✗   |
| garp_misfit | ✓/✗    | ✓/✗    | ✓/✗   |
| garp_large  | ✓/✗    | ✓/✗    | ✓/✗   |

통과: X / 9. Mode: efficiency 또는 fallback.

### 3.2 2차 점수 (Efficiency or Fallback)

| Provider | mean score | n   | model_means           |
| -------- | ---------- | --- | --------------------- |
| gemini   | XX.XX      | 3   | (efficiency 시 큰 값) |
| sonnet   | XX.XX      | 3   |                       |
| haiku    | XX.XX      | 3   |                       |

Winner: **(gemini / sonnet / haiku)**

## 4. Dimension Analysis (수동 작성, 차원별 1~2 paragraph)

### 4.1 Schema 적합성

- 모델별 통과율과 실패 원인.
  - 예: Haiku가 JSON 마크다운 펜스 추가 경향, Gemini는 단일 객체로 직출력.
  - parse_e1_response의 전처리가 펜스 제거를 다루는지 확인.

### 4.2 한국어 자연스러움

- 모델별 평균 점수와 fixture별 변화.
- 어떤 톤이 한국 사용자 친화적인지.
- 예: Sonnet 4.5는 격식체 우세, Haiku는 친근하지만 한자어 과다, Gemini는 영어 직역체 일부.

### 4.3 진단 통찰성

- 카드 4요소(무엇이/기준/왜 중요/예외) 충실도.
- fixture별로 강점 카드 vs 약점 카드 vs 보완 제안 톤이 모델별로 어떻게 다른가.
- 예: garp_misfit에서 "프리셋 변경 제안" 완화 톤은 어느 모델이 가장 자연스러운가.

### 4.4 비용

- 9회 호출 비용 분포. 모델별 비용 비율 (대략 Gemini Flash : Haiku : Sonnet ≈ 1 : 5 : 50 추정).
- garp_large가 비용에 미치는 영향.

### 4.5 지연

- 모델별 latency 평균과 분산. 5초 임계 위반 케이스 여부.

## 5. Decision

### 5.1 Slice 2 진입 시 primary provider

- 채택: (winner)
- 변경 여부: 유지 / 변경
- 근거: mean score 차이, 비용 차이, 응답 품질 정성 평가.

### 5.2 Slice 2 진입 시 retain 사항

- LLMClient wrapper, services 분리, fixture 3종, scoring 스크립트 모두 유지.
- preset_metrics 변경 시 fixture validation test가 자동 회귀 잡음.

### 5.3 Slice 2 진입 시 change 사항

- 프롬프트 톤/스키마 조정 항목 (예: "한국어 직역체 완화" system message 강화).
- LLMClient의 fallback 트리거 조정 (필요 시).

### 5.4 Phase 2 보류 항목

- 자연스러움 평가 자동화 (LLM-as-judge).
- 통찰성 평가 자동화 (rule-based heuristic).
- 토큰 예산 한계 검증 (현재 종목 15개에서 더 큰 사이즈).

## 6. Cost Guard

| 항목                           | 값                                |
| ------------------------------ | --------------------------------- |
| Slice 1 누적 LLM 호출          | XX / 50                           |
| 누적 비용 (USD)                | $X.XX                             |
| Step 6 비용                    | $0.000XX                          |
| Step 8 비용                    | $X.XX (9 calls)                   |
| Step 8 재시도                  | $X.XX (XX calls)                  |
| 잔여 호출 한도                 | XX                                |
| Slice 2 진입 시 비용 가드 리셋 | 권장 (env 분리 또는 카운터 reset) |
```

## 8.4 검증 판정

| #   | 판정                              | 임계                                                        | 자동/수동 |
| --- | --------------------------------- | ----------------------------------------------------------- | --------- |
| 1   | 9회 호출 모두 응답                | error ≤ 1 (rate limit/timeout 1회 허용)                     | 자동      |
| 2   | 1차 필터 통과                     | 모든 fixture에서 최소 1개 모델 통과 또는 fallback mode 명시 | 자동      |
| 3   | validation_report_slice1.md 6섹션 | 6 sections present                                          | 수동      |
| 4   | 누적 비용 < $1.00                 | 자동                                                        | 자동      |

## 8.5 롤백 / 실패 시 처리

### 케이스 A: 9회 중 1~3회 error (rate limit/timeout)

- LLMClient의 1회 재시도 작동 확인 (Part 1에서 설계).
- `fallback_from` 메타가 채워졌는지 검증.
- 비용 가드 한도 내에서 재실행 가능.

### 케이스 B: 1차 필터 전체 미통과 (모든 9회 fail)

- Mode: fallback. 점수 산출은 가능하나 모델 우열 신뢰성 낮음.
- Decision 5.1에 "Slice 1 결과로 모델 결정 보류, Slice 2에서 재평가" 명시.
- 프롬프트의 schema 지시 / 카드 구조 지시가 명확한지 점검.

### 케이스 C: 한 fixture에서 3개 모델 모두 1차 미통과

- 해당 fixture 또는 프롬프트 자체 문제 시사.
- Dimension Analysis 4.3에서 원인 분석 후 Slice 2 변경 사항으로 기록.

### 케이스 D: 누적 비용 > $1.00

- 비용 가드 호출 수 미만이라도 비용 자체 예산 초과.
- 즉시 중단, Decision에 "Slice 2부터 비용 모니터링 강화" 기록.

### 케이스 E: 특정 모델만 일관되게 fail

- 해당 모델의 LLMClient 분기 로직 점검.
- Decision 5.3에 변경 사항으로 기록 (예: "Sonnet 4.5는 응답 형식 지시 강화 필요").

## 8.6 산출물

- `scripts/validation/run_step8_3way.py` (신규, ~120줄)
- `scripts/validation/score_step8.py` (신규, ~140줄)
- `portfolio/docs/step8_3way_raw.json` (실행 산출물)
- `portfolio/docs/step8_3way_scored.json` (실행 산출물)
- `portfolio/docs/validation_report_slice1.md` (신규, 6섹션)

## 8.7 비용 가드

- LLM 호출: 9회 + 재시도 가능 ~3회 = 최대 12회
- 누적: 10~14 / 50 (Step 6 포함)

---

# Step 9 — 30분 리팩토링 슬롯

## 9.1 목표

Slice 1에서 누적된 기술 부채(중복 코드, 가독성 저하, 안전성 약점)를 30분 한도 내에서 우선순위에 따라 정리한다. **30분 초과 항목은 Slice 2 백로그로 이관**.

## 9.2 사전 조건

- Step 8 완료, validation_report_slice1.md Decision 섹션 작성 완료.
- 30분 타이머 준비 (실제 타이머).

## 9.3 우선순위 결정 휴리스틱 (퀀트 공학 기반)

### 9.3.1 점수 산식 — Sharpe-like Ratio 변형

```
PriorityScore = (CostSaving × Frequency) / (RiskOfBreakage × TimeRequired)

CostSaving:     1~5 (다음 슬라이스에서 손이 갈 빈도. 5 = 자주)
Frequency:      1~5 (현재 코드의 호출/접근 빈도. 5 = 핫 경로)
RiskOfBreakage: 1~5 (회귀 테스트 깨질 위험. 5 = 위험 큼)
TimeRequired:   1~5 (분당 가중. 1 = ~5분, 5 = ~30분)
```

근거:

- 분자 = 미래 절감 효용 × 현재 영향 (정보 비율 분자)
- 분모 = 즉시 위험 × 시간 비용 (정보 비율 분모)
- 같은 시간 투자로 미래 ROI가 가장 큰 항목 우선
- Sharpe ratio의 (수익 / 위험) 구조와 동일

### 9.3.2 후보 항목 식별 (5분)

```bash
# 코드 중복
pip install --quiet pylint
pylint portfolio/ scripts/ --disable=all --enable=duplicate-code 2>&1 | head -50

# 함수 복잡도
pip install --quiet radon
radon cc portfolio/ scripts/ -a -s -nb

# TODO/FIXME
grep -rn "TODO\|FIXME\|XXX" portfolio/ scripts/ | head -20

# 테스트 커버리지 (Slice 1 baseline 확보)
pytest --cov=portfolio --cov-report=term-missing portfolio/tests/ 2>&1 | tail -30
```

### 9.3.3 후보 점수화 (5분)

`portfolio/docs/refactor_backlog_slice1.md` 신설:

```markdown
# Refactor Backlog — Slice 1

> 작성일: YYYY-MM-DD
> 산출일: 30분 슬롯 작업 후 갱신

## Candidates (PriorityScore 내림차순)

| #   | 항목                                                                                           | CostSaving | Frequency | RiskOfBreakage | TimeRequired | PriorityScore | Slice 1? |
| --- | ---------------------------------------------------------------------------------------------- | ---------- | --------- | -------------- | ------------ | ------------- | -------- |
| 1   | LLMClient의 cost 계산 함수가 provider별 분기 if-elif 8줄. provider→cost_per_1k 딕셔너리로 추출 | 4          | 5         | 1              | 1            | 20.0          | YES      |
| 2   | services/e1_garp.py의 build_prompt가 metric_id 53개를 인라인 string concat. 별도 helper로 분리 | 3          | 4         | 2              | 2            | 3.0           | YES      |
| 3   | tests의 fixture loader가 매번 dict copy. lru_cache 적용                                        | 1          | 3         | 1              | 1            | 3.0           | NO       |
| 4   | view에서 provider param validation이 manual if문. choices=PROVIDERS enum으로                   | 2          | 2         | 2              | 1            | 2.0           | NO       |
| 5   | LLM 호출 메타데이터(provider/model/latency/...)를 dict로 인자 전달. dataclass로 추출           | 3          | 3         | 3              | 3            | 1.0           | NO       |
| ... |

(실제 발견 항목으로 채움.)

PriorityScore 내림차순 정렬, 합산 TimeRequired ≤ 5 (30분 = 5단위) 까지 Slice 1 적용.
초과 항목은 "Slice 1?" = NO 표시 후 Slice 2 백로그.

## Applied in Slice 1

(작업 후 채움. 항목별 commit hash, 회귀 결과 기록.)

| #   | 항목                | Commit    | 회귀 결과    | 소요 시간 |
| --- | ------------------- | --------- | ------------ | --------- |
| 1   | LLMClient cost dict | `abc1234` | 35/35 passed | 7분       |
| ... |
```

### 9.3.4 작업 실행 (20분)

선정된 항목을 순서대로 적용. 각 항목 완료 시 `pytest portfolio/tests/ -q` 회귀 통과 확인 (필수).

회귀 깨지면 즉시 `git restore` 후 다음 항목으로 (해당 항목은 backlog에서 RiskOfBreakage = 5로 갱신, Slice 2 이관).

테스트 실행 시간 < 5초면 항목별로 매번 실행. 길면 (> 30초) 2~3 항목씩 묶음.

### 9.3.5 회귀 검증 (5분)

```bash
pytest portfolio/tests/ -v
# 예상: 35 passed (Slice 1 baseline)

pytest --cov=portfolio --cov-report=term portfolio/tests/ 2>&1 | tail -10
# 커버리지: Slice 1 시작 대비 -2%p 이내
```

## 9.4 검증 판정

| #   | 판정                            | 임계                               | 자동 |
| --- | ------------------------------- | ---------------------------------- | ---- |
| 1   | 회귀 테스트 모두 통과           | 35/35 passed                       | 자동 |
| 2   | 30분 타이머 준수                | 실제 ≤ 35분 (5분 tolerance)        | 수동 |
| 3   | refactor_backlog_slice1.md 작성 | 우선순위 표 + Slice 1 적용 결과 표 | 수동 |
| 4   | 커버리지 비저하                 | Slice 1 시작 대비 -2%p 이내        | 자동 |

## 9.5 롤백 / 실패 시 처리

### 케이스 A: 회귀 테스트 실패

- 즉시 `git restore`로 해당 항목 롤백.
- backlog 표에서 RiskOfBreakage = 5로 갱신, Slice 2 이관.

### 케이스 B: 30분 초과 임박

- 진행 중 항목은 완료까지만 진행 (회귀 통과 후 commit).
- 미시작 항목은 backlog "Slice 1?" = NO로 변경.
- 절대 30분 + 5분 tolerance를 넘지 않음 (퀀트 원칙: time budget 엄격 준수).

### 케이스 C: 후보 항목 없음

- 전반부 코드가 깨끗하다는 의미. backlog 표에 "후보 없음" 명시 후 Step 9 종료.
- Slice 2에서 다시 후보 식별.

## 9.6 산출물

- `portfolio/docs/refactor_backlog_slice1.md` (신규, 우선순위 표 + 적용 결과)
- 적용 리팩토링 commit (git log로 추적, 항목별 1 commit 권장)

## 9.7 비용 가드

- LLM 호출: 0회 (오프라인 작업)
- 누적: 10~14 / 50 (Step 8 누적 그대로)

---

# 종결 체크리스트

Slice 1 완료 직전 본인 확인:

- [ ] Step 6 자동 판정 4/4 + 한국어 자연스러움 ≥ 3 (수동)
- [ ] Step 7 garp_large fixture 종목 15, weight 합 1.0, utilization 70~85%
- [ ] Step 7 fixture validation 테스트 8/8 통과 (누적 35 passed)
- [ ] Step 8 9회 호출, error ≤ 1
- [ ] Step 8 step8_3way_raw.json의 모든 entry에 naturalness, insight 평가 입력
- [ ] Step 8 score_step8 실행 후 winner 모델 식별
- [ ] validation_report_slice1.md 6섹션 모두 채움
- [ ] Step 9 30분 한도 내 리팩토링, 회귀 통과
- [ ] refactor_backlog_slice1.md 작성, Slice 2 이관 항목 표시
- [ ] 누적 LLM 호출 ≤ 14 (예산 50의 28%)
- [ ] 누적 비용 ≤ $0.30
- [ ] git commit, push (원하는 시점)

# 비용 가드 누적 표

| Step      | 호출 | 누적 호출 | 비용 (USD) | 누적 비용  |
| --------- | ---- | --------- | ---------- | ---------- |
| 6         | 1    | 1         | $0.0003    | $0.0003    |
| 7         | 0    | 1         | $0.00      | $0.0003    |
| 8         | 9    | 10        | $0.10~0.20 | $0.10~0.20 |
| 8 재시도  | 0~3  | 10~13     | $0.05      | $0.15~0.25 |
| 9         | 0    | 10~13     | $0.00      | $0.15~0.25 |
| 회귀/예비 | 0~5  | 10~18     | $0.05      | $0.20~0.30 |

**최대 36% 점유 (50회 한도 대비)**. 충분한 안전 마진.

# Slice 2 진입 조건

종결 체크리스트 모두 통과 후 다음 한 줄로 시작:

> "슬라이스 2 시작하자. E5 진입점 코드 작성 들어가자."

전제: Slice 1 의사결정(primary provider 채택/변경, 프롬프트 톤 변경)이 메모리에 갱신됨.

---

# 부록 A — 결정 사항 단일 표 (재참조용)

| Q   | 결정                                                                  | 파일/위치                                             |
| --- | --------------------------------------------------------------------- | ----------------------------------------------------- |
| Q1  | Step 6 검증 fixture: garp_tech                                        | `scripts/validation/run_step6_smoke.py`               |
| Q2  | garp_large 종목 수: 15 (5 정합 + 5 부분 + 5 부정합)                   | `portfolio/tests/fixtures/sample_analysis_context.py` |
| Q3  | Lexicographic 필터 + 효율 비교 + B fallback                           | `scripts/validation/score_step8.py`                   |
| Q4  | validation_report 6섹션 (메타/콜로그/스코어링/차원해석/결정/비용가드) | `portfolio/docs/validation_report_slice1.md`          |

# 부록 B — 모든 신규 파일 목록 (Slice 1 Part 2)

| 파일                                                       | 종류                   | 줄 수(추정) |
| ---------------------------------------------------------- | ---------------------- | ----------- |
| `scripts/validation/__init__.py`                           | 빈 패키지 마커         | 0           |
| `scripts/validation/run_step6_smoke.py`                    | 검증 스크립트          | ~110        |
| `scripts/validation/measure_tokens.py`                     | 토큰 측정              | ~70         |
| `scripts/validation/run_step8_3way.py`                     | 3-way 호출             | ~120        |
| `scripts/validation/score_step8.py`                        | 점수 산출              | ~140        |
| `portfolio/tests/fixtures/sample_analysis_context.py` 추가 | get_context_garp_large | ~80         |
| `portfolio/tests/test_fixtures_validation.py`              | fixture 테스트         | ~70         |
| `portfolio/docs/step6_smoke_output.json`                   | 실행 산출물            | —           |
| `portfolio/docs/step8_3way_raw.json`                       | 실행 산출물            | —           |
| `portfolio/docs/step8_3way_scored.json`                    | 실행 산출물            | —           |
| `portfolio/docs/validation_report_slice1.md`               | 보고서                 | ~150        |
| `portfolio/docs/refactor_backlog_slice1.md`                | 리팩토링 백로그        | ~50         |

총 신규 코드: ~590줄. 보고서/JSON 별도.
