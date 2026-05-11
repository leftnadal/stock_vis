# Slice 3 — Part 2 작업 지시서 (Step 6~9)

> 작성일: 2026-05-07
> 대상: Stock-Vis Portfolio Coach 슬라이스 3 후반부
> 진입점: E2 (Slice 3 Part 1 산출물 활용)
> 전제: Slice 3 Part 1 (Step 0~5) 완료, 회귀 119 passed, 누적 호출 0/50 (Reset 적용)
> 브랜치: portfolio
> 누적 LLM 호출: 0 / 50 (Slice 3 Reset 적용 시점)

---

## 결정 사항 상속 (Part 1과 동일)

| 결정                             | 영향                                                      |
| -------------------------------- | --------------------------------------------------------- |
| D2 default provider = haiku      | Step 6                                                    |
| A1.B 매트릭스 7×2=14             | Step 8                                                    |
| A2.C #5 단독 슬롯                | Step 9 (#3, #4는 Part 1 Step 2 흡수 완료)                 |
| A3.A e1 산식 + completeness 자동 | Step 8 score                                              |
| Q3.C completeness 자동 측정      | Step 1 model_validator로 통과 보장                        |
| D4 회피 가이드                   | 모든 run 스크립트에 \_json_default + round-trip 검증 의무 |

---

## 0. 사전 검증

### 0.1 Part 1 완료 확인

```bash
git rev-parse --abbrev-ref HEAD
# 예상: portfolio

pytest portfolio/tests/ -q
# 예상: 119 passed (Part 1 종결 baseline)

# Part 1 산출물 무결성
python -c "
from portfolio.tests.fixtures.sample_diagnostic_context import (
    ALL_FIXTURES, FIXTURE_GROUPS,
)
print(f'fixtures: {len(ALL_FIXTURES)}')
print(f'baseline group: {FIXTURE_GROUPS[\"slice1_baseline\"]}')
print(f'focused group: {FIXTURE_GROUPS[\"e2_focused\"]}')
"
# 예상: 7 / [garp_tech, garp_misfit, garp_large] / [4개 신규]

python -c "
from portfolio.services.e2_diagnostic_card import (
    run_e2, build_e2_prompt, parse_e2_response,
)
from portfolio.services._llm_kwargs import resolve_provider_kwargs
print('haiku kwargs:', resolve_provider_kwargs('haiku'))
"

# CostGuard 상태
python -c "
from portfolio.llm.cost_guard import CostGuard
g = CostGuard.get_instance()
print('status:', g.status())
"
# 예상: slice_id가 'slice3' 또는 'default'. Step 6 진입 시 'slice3'로 reset.
```

### 0.2 비용 가드 예산 (Part 1과 동일)

| Step                         | 호출 수 | 누적 | 안전 마진 |
| ---------------------------- | ------- | ---- | --------- |
| Part 1 종결                  | —       | 0    | 50        |
| Step 6 (실 haiku 1회)        | 1       | 1    | 49        |
| Step 7 (오프라인 측정)       | 0       | 1    | 49        |
| Step 8 (7 fixture × 2 model) | 14      | 15   | 35        |
| Step 8 재시도 예비           | ~3      | ~18  | ~32       |
| Step 9 (리팩토링)            | 0       | ~18  | ~32       |

최대 18~23 / 50 (36~46%).

---

# Step 6 — 실 haiku 1회 호출 (D2.B 적용)

## 6.1 목표

E2 진입점의 첫 실제 LLM 호출. **garp_tech fixture (Slice 1 baseline 그룹)** 로 baseline 측정. **default provider = haiku** (D2.B — 글쓰기 작업).

**판정 차원 (Slice 1 E1과 동일 — 글쓰기 작업)**:

- schema 통과 (DiagnosticCard Pydantic, completeness 자동 통과 포함)
- naturalness (수동 1~5)
- insight (수동 1~5)
- 비용 ≤ $0.020
- 지연 ≤ 5,000ms

## 6.2 fixture 결정 근거

`garp_tech` 선택:

- Slice 1 baseline 그룹의 첫 fixture — Slice 1 E1 결과와 직접 비교 baseline
- FIT 케이스 (가장 명확) — Slice 1과 동일 fixture로 진입점 차이만 측정
- E2 출력 변동성이 가장 낮을 것으로 예상

## 6.3 작업 단계

### 6.3.1 스크립트 신설 (D4 회피 가이드 적용)

`scripts/validation/run_step6_e2_smoke.py`:

```python
"""Step 6 — E2 진입점 실 haiku 1회 호출 (smoke test).

Slice 3 Part 2의 baseline 측정.
garp_tech fixture × haiku provider × 1회 호출.

D4 회피 가이드:
- _json_default 핸들러 사용
- 산출물 disk write 후 read-back round-trip 검증
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, date
from decimal import Decimal
from pathlib import Path

from scripts.validation._setup import init_django, reset_for_slice

init_django()
reset_for_slice("slice3", max_calls=50)

from portfolio.llm.client import LLMClient
from portfolio.schemas.llm import E2Request
from portfolio.services._llm_kwargs import resolve_provider_kwargs
from portfolio.services.e2_diagnostic_card import (
    build_e2_prompt, parse_e2_response,
)
from portfolio.tests.fixtures.sample_diagnostic_context import ALL_FIXTURES


THRESHOLDS = {
    "cost_usd_max": 0.020,
    "latency_ms_max": 5000,
}


# D4 회피 가이드
def _json_default(obj):
    """JSON 직렬화 안전망."""
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not JSON serializable")


def _safe_write(path: Path, data: dict) -> None:
    """Write + read-back round-trip 검증 (D4 가이드)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, ensure_ascii=False, indent=2, default=_json_default)
    path.write_text(serialized, encoding="utf-8")
    # Round-trip 검증
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded is not None, "Round-trip read returned None"
    print(f"  [round-trip OK] {path}")


def main() -> int:
    fixture = ALL_FIXTURES["garp_tech"]()
    request = E2Request(analysis_context=fixture["analysis_context"])
    prompt = build_e2_prompt(request)

    client = LLMClient()
    kwargs = resolve_provider_kwargs("haiku")
    resp = client.complete(prompt=prompt, **kwargs)

    # schema 검증 (completeness 자동 측정 포함)
    try:
        parsed = parse_e2_response(
            resp.text, preset_id=request.analysis_context.get("preset_id", "garp"),
        )
        schema_pass = True
        schema_error = None
        parsed_dict = parsed.model_dump()
        completeness_auto = True  # schema 통과 = completeness 통과
    except Exception as e:
        parsed = None
        schema_pass = False
        schema_error = f"{type(e).__name__}: {str(e)[:200]}"
        parsed_dict = None
        completeness_auto = False

    # 임계 판정
    cost_pass = resp.cost_usd <= THRESHOLDS["cost_usd_max"]
    latency_pass = resp.latency_ms <= THRESHOLDS["latency_ms_max"]

    # 평가 가이드 (인라인 — Slice 2 N1.C 패턴)
    eval_guide = {
        "naturalness": {
            "5": "한국어 자연스러움 우수, 단순 수치 나열 없음",
            "4": "자연스러우나 일부 어색 표현",
            "3": "이해 가능하나 약간 기계적",
            "2": "어색 표현 다수",
            "1": "이해 어려움 / 비문법적",
        },
        "insight": {
            "5": "지표 너머 의미 있는 해석. 비자명한 패턴 발견",
            "4": "기본 해석 + 일부 통찰",
            "3": "지표 표면 해석만",
            "2": "단순 수치 나열에 가까움",
            "1": "분석 깊이 부재",
        },
    }

    output = {
        "step": "step6_e2_smoke",
        "fixture": "garp_tech",
        "fixture_group": fixture["fixture_group"],
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "request": {
            "preset_id": request.analysis_context.get("preset_id"),
            "holdings_count": len(request.analysis_context.get("holdings", [])),
        },
        "raw_content": resp.text,
        "parsed": parsed_dict,
        "metadata": resp.metadata_dict(),
        "judgments": {
            "schema_pass": schema_pass,
            "schema_error": schema_error,
            "completeness_auto": completeness_auto,
            "cost_pass": cost_pass,
            "latency_pass": latency_pass,
            "naturalness_manual": None,
            "insight_manual": None,
        },
        "thresholds": THRESHOLDS,
        "evaluation_guide": eval_guide,
        "status_summary": {
            "schema_pass": schema_pass,
            "completeness_auto": completeness_auto,
            "cost_pass": cost_pass,
            "latency_pass": latency_pass,
            "manual_eval_required": ["naturalness_manual", "insight_manual"],
        },
        "cost_guard_status": __import__(
            "portfolio.llm.cost_guard", fromlist=["CostGuard"]
        ).CostGuard.get_instance().status(),
    }

    output_path = Path("docs/portfolio/coach/slice3/step6_smoke_e2_output.json")
    _safe_write(output_path, output)

    print(f"[Saved] {output_path}")
    print(f"  schema_pass:       {schema_pass}")
    print(f"  completeness_auto: {completeness_auto}")
    print(f"  cost_pass:         {cost_pass} (${resp.cost_usd:.5f} / ${THRESHOLDS['cost_usd_max']:.4f})")
    print(f"  latency_pass:      {latency_pass} ({resp.latency_ms}ms)")
    print(f"  fallback_from:     {resp.fallback_from}")
    print()
    print("⚠️  naturalness_manual + insight_manual 필드를 1~5로 직접 입력 필요.")
    print(f"    파일: {output_path}")
    return 0 if (schema_pass and cost_pass and latency_pass) else 1


if __name__ == "__main__":
    sys.exit(main())
```

### 6.3.2 실행

```bash
python -m scripts.validation.run_step6_e2_smoke
```

### 6.3.3 수동 평가

```bash
# 평가 가이드 확인
jq '.evaluation_guide' docs/portfolio/coach/slice3/step6_smoke_e2_output.json

# 평가 입력 (judgments 필드 직접 편집)
vim docs/portfolio/coach/slice3/step6_smoke_e2_output.json
# "naturalness_manual": null → 4 (예시)
# "insight_manual": null → 5 (예시)
```

## 6.4 검증 판정

| #   | 판정               | 임계               | 자동/수동 |
| --- | ------------------ | ------------------ | --------- |
| 1   | schema_pass        | true               | 자동      |
| 2   | completeness_auto  | true               | 자동      |
| 3   | naturalness_manual | 정수 1~5 (≥3 권장) | 수동      |
| 4   | insight_manual     | 정수 1~5 (≥3 권장) | 수동      |
| 5   | cost_pass          | ≤ $0.020           | 자동      |
| 6   | latency_pass       | ≤ 5,000ms          | 자동      |
| 7   | round-trip 검증    | OK                 | 자동      |
| 8   | CostGuard 누적     | 1/50               | 자동      |

## 6.5 롤백 / 실패 시 처리

(Slice 2 Step 6 패턴 동일 — 케이스 A~D)

추가 케이스 (Slice 3 신규):

- **케이스 E. completeness_auto=false (schema 통과인데 자동 측정 실패)**: schema와 completeness 자동 측정 룰 불일치. model_validator 재검토 신호.

## 6.6 산출물

- `scripts/validation/run_step6_e2_smoke.py` (신규, ~140줄)
- `docs/portfolio/coach/slice3/step6_smoke_e2_output.json` (실행 산출물)

## 6.7 비용 가드

- LLM 호출: 1회 (haiku)
- 예상 비용: ~$0.005
- 누적: 1 / 50

---

# Step 7 — E2 토큰 측정 (오프라인)

## 7.1 목표

E2 prompt의 입력/출력 토큰 분포 측정. 다음을 확정:

1. E2 budget 임계
2. analysis_summary 200자 효과 (I4 모니터링 — Slice 2 이연)
3. Step 8 14 calls 비용 예측
4. **fixture 그룹별 토큰 분포** (baseline vs focused) — A1.B 채택 효과 측정

## 7.2 budget 가정

E1 baseline (Slice 1): ~3,700 tokens, budget 5,000.
E5 (Slice 2): ~900 tokens, budget 2,000.
E2 예상: E1과 유사한 글쓰기 작업이므로 2,500~3,500 tokens 예상.

## 7.3 작업 단계

### 7.3.1 스크립트 신설

`scripts/validation/measure_e2_tokens.py`:

```python
"""Step 7 — E2 prompt 토큰 측정.

7개 fixture별 input prompt 토큰 분포 + fixture 그룹 비교.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, date
from decimal import Decimal
from pathlib import Path

from scripts.validation._setup import init_django, reset_for_slice

init_django()
reset_for_slice("slice3", max_calls=50)

from portfolio.schemas.llm import E2Request
from portfolio.services.e2_diagnostic_card import build_e2_prompt
from portfolio.tests.fixtures.sample_diagnostic_context import (
    ALL_FIXTURES, FIXTURE_GROUPS,
)


def count_tokens(text: str) -> int:
    """Anthropic SDK token counting."""
    from anthropic import Anthropic
    client = Anthropic()
    resp = client.messages.count_tokens(
        model="claude-haiku-4-5",
        messages=[{"role": "user", "content": text}],
    )
    return resp.input_tokens


INITIAL_BUDGET = 5000  # E1과 동일 가정


def _json_default(obj):
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not JSON serializable")


def main() -> int:
    results = []

    for name, getter in ALL_FIXTURES.items():
        fixture = getter()
        request = E2Request(analysis_context=fixture["analysis_context"])
        prompt = build_e2_prompt(request)
        token_count = count_tokens(prompt)

        results.append({
            "fixture": name,
            "fixture_group": fixture["fixture_group"],
            "prompt_chars": len(prompt),
            "input_tokens": token_count,
            "budget": INITIAL_BUDGET,
            "utilization": round(token_count / INITIAL_BUDGET, 4),
            "holdings_count": len(fixture["analysis_context"].get("holdings", [])),
        })

    # 통계 — 전체
    tokens_all = [r["input_tokens"] for r in results]
    stats_all = {
        "min": min(tokens_all),
        "max": max(tokens_all),
        "mean": round(sum(tokens_all) / len(tokens_all), 1),
        "p50": sorted(tokens_all)[len(tokens_all) // 2],
        "p90": sorted(tokens_all)[int(len(tokens_all) * 0.9)],
    }

    # 그룹별 통계
    group_stats = {}
    for group_name, group_fixtures in FIXTURE_GROUPS.items():
        group_tokens = [
            r["input_tokens"] for r in results if r["fixture"] in group_fixtures
        ]
        group_stats[group_name] = {
            "min": min(group_tokens),
            "max": max(group_tokens),
            "mean": round(sum(group_tokens) / len(group_tokens), 1),
            "fixture_count": len(group_tokens),
        }

    recommended_budget = int(stats_all["p90"] * 1.5)

    output = {
        "step": "step7_e2_token_measurement",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "stats_all": stats_all,
        "stats_by_group": group_stats,
        "initial_budget": INITIAL_BUDGET,
        "recommended_budget": recommended_budget,
        "decision_guide": {
            "if_recommended_lower_than_initial": "budget 하향. E2_TOKEN_BUDGET 상수 신설 검토 (Step 9 백로그 #5와 결합).",
            "if_recommended_higher_than_initial": "budget 상향. analysis_summary 압축 또는 metrics 표 압축 검토.",
            "safe_zone": "max utilization 70~85% 권장.",
        },
        "i4_monitoring": {
            "context": "Slice 2 I4 — analysis_summary 200자 truncate 효과. Slice 3에서도 동일 헬퍼 사용.",
            "max_utilization_observed": max(r["utilization"] for r in results),
            "recommendation": "max < 30% → 200자 유지 OK. > 70% → 100자 압축 검토.",
        },
        "group_comparison_note": (
            "baseline (garp 3개) vs focused (e2 신규 4개) 토큰 차이는 "
            "fixture 다양성이 비용에 미치는 영향 측정. 큰 차이 없으면 hybrid 결정 정당."
        ),
    }

    output_path = Path("docs/portfolio/coach/slice3/step7_e2_token_measurement.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    # Round-trip 검증
    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert loaded["stats_all"]["max"] == stats_all["max"]

    print(f"[Saved] {output_path}")
    print(f"  fixtures:           {len(results)}")
    print(f"  token range (all):  {stats_all['min']} ~ {stats_all['max']}")
    print(f"  P90:                {stats_all['p90']}")
    print(f"  recommended budget: {recommended_budget}")
    print(f"  baseline group mean: {group_stats['slice1_baseline']['mean']}")
    print(f"  focused group mean:  {group_stats['e2_focused']['mean']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 7.3.2 실행

```bash
python -m scripts.validation.measure_e2_tokens
```

### 7.3.3 budget 결정 (수동)

| 상황                | 결정                                                       |
| ------------------- | ---------------------------------------------------------- |
| recommended < 2,500 | E2_TOKEN_BUDGET 상수 도입 (2,500). Step 9 백로그 #5와 결합 |
| 2,500~4,000         | E2 budget = 4,000. E1과 분리 또는 통합 결정                |
| > 4,000             | E1 budget 5,000 유지. E2 prompt 압축 검토                  |

I4 모니터링 (analysis_summary 200자 utilization):

- max < 30% → 200자 유지
- 30%~70% → 모니터링 지속
- > 70% → 100자 압축 검토 (Slice 4 작업)

그룹 비교 분석 (Q4 수정 검증):

- baseline mean ≈ focused mean → hybrid 정당화 (큰 차이 없음)
- baseline mean << focused mean → focused fixture가 비용 부담 큼 → 다음 슬라이스 fixture 설계 시 주의

## 7.4 검증 판정

| #   | 판정             | 임계                          | 자동/수동 |
| --- | ---------------- | ----------------------------- | --------- |
| 1   | 7 fixture 측정   | 7/7                           | 자동      |
| 2   | 그룹별 통계 산출 | 2 그룹                        | 자동      |
| 3   | budget 결정 기록 | recommended_budget 명시       | 수동      |
| 4   | I4 모니터링 결정 | 200자 유지/압축               | 수동      |
| 5   | round-trip 검증  | OK                            | 자동      |
| 6   | 회귀             | 119 passed (테스트 추가 없음) | 자동      |

## 7.5 산출물

- `scripts/validation/measure_e2_tokens.py` (신규, ~120줄)
- `docs/portfolio/coach/slice3/step7_e2_token_measurement.json` (실행 산출물)

## 7.6 비용 가드

- LLM 호출: 0회
- 누적: 1 / 50

---

# Step 8 — 2-way 회고 (A1.B 매트릭스 7×2=14)

## 8.1 목표

7 fixture × 2 model (haiku/sonnet) = 14 호출로 모델 비교. **fixture 그룹별 비교 분석 필수** (hybrid 결정 검증).

## 8.2 매트릭스 (A1.B + Q4 수정)

```
┌─────────────────────────┬───────┬────────┐
│         fixture         │ haiku │ sonnet │
├─────────────────────────┼───────┼────────┤
│ slice1_baseline group:  │       │        │
│ garp_tech               │  ✓    │  ✓     │
│ garp_misfit             │  ✓    │  ✓     │
│ garp_large              │  ✓    │  ✓     │
├─────────────────────────┼───────┼────────┤
│ e2_focused group:       │       │        │
│ e2_clear_strengths      │  ✓    │  ✓     │
│ e2_clear_weaknesses     │  ✓    │  ✓     │
│ e2_balanced             │  ✓    │  ✓     │
│ e2_extreme_risk         │  ✓    │  ✓     │
└─────────────────────────┴───────┴────────┘
                            7      7        = 14 calls
```

## 8.3 평가 차원 정의 (A3.A — e1 산식 + completeness 자동)

### 8.3.1 naturalness (수동 1~5)

한국어 자연스러움. Slice 1 E1과 동일 정의:

| 점수 | 정의                                        |
| ---- | ------------------------------------------- |
| 5    | 한국어 자연스러움 우수, 단순 수치 나열 없음 |
| 4    | 자연스러우나 일부 어색 표현                 |
| 3    | 이해 가능하나 약간 기계적                   |
| 2    | 어색 표현 다수                              |
| 1    | 이해 어려움 / 비문법적                      |

### 8.3.2 insight (수동 1~5)

분석 깊이. Slice 1 E1과 동일 정의:

| 점수 | 정의                                         |
| ---- | -------------------------------------------- |
| 5    | 지표 너머 의미 있는 해석. 비자명한 패턴 발견 |
| 4    | 기본 해석 + 일부 통찰                        |
| 3    | 지표 표면 해석만                             |
| 2    | 단순 수치 나열에 가까움                      |
| 1    | 분석 깊이 부재                               |

### 8.3.3 completeness (자동, schema 통과 시 True)

DiagnosticCard schema 통과 = 4요소 모두 채움 + 각 항목 10자 이상 = completeness 통과.

### 8.3.4 fixture 그룹 비교 분석

Q4 수정(hybrid)의 정당성 검증:

- **baseline 그룹 (garp 3개)**: Slice 1 E1 결과와 직접 비교. 모델별 mean 비교
- **focused 그룹 (e2 신규 4개)**: E2 특화 시나리오. 4요소 각각의 fixture가 의도한 측정 대상 확인

## 8.4 작업 단계

### 8.4.1 run 스크립트 신설

`scripts/validation/run_step8_e2_2way.py`:

```python
"""Step 8 — E2 2-way 회고 (haiku + sonnet).

7 fixture × 2 model = 14 calls.
산출물: docs/portfolio/coach/slice3/step8_2way_e2_raw.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, date
from decimal import Decimal
from pathlib import Path

from scripts.validation._setup import init_django, reset_for_slice

init_django()
reset_for_slice("slice3", max_calls=50)

from portfolio.llm.client import LLMClient
from portfolio.schemas.llm import E2Request
from portfolio.services._llm_kwargs import resolve_provider_kwargs
from portfolio.services.e2_diagnostic_card import (
    build_e2_prompt, parse_e2_response,
)
from portfolio.tests.fixtures.sample_diagnostic_context import (
    ALL_FIXTURES, FIXTURE_GROUPS,
)


PROVIDERS = ["haiku", "sonnet"]


EVALUATION_GUIDE = {
    "naturalness": {
        "5": "한국어 자연스러움 우수, 단순 수치 나열 없음",
        "4": "자연스러우나 일부 어색 표현",
        "3": "이해 가능하나 약간 기계적",
        "2": "어색 표현 다수",
        "1": "이해 어려움 / 비문법적",
    },
    "insight": {
        "5": "지표 너머 의미 있는 해석. 비자명한 패턴 발견",
        "4": "기본 해석 + 일부 통찰",
        "3": "지표 표면 해석만",
        "2": "단순 수치 나열에 가까움",
        "1": "분석 깊이 부재",
    },
    "completeness_auto": "schema 통과 시 자동 True. 수동 평가 불필요.",
}


def _json_default(obj):
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not JSON serializable")


def main() -> int:
    client = LLMClient()
    results = []

    for fixture_name, getter in ALL_FIXTURES.items():
        fixture = getter()
        request = E2Request(analysis_context=fixture["analysis_context"])
        prompt = build_e2_prompt(request)

        for provider in PROVIDERS:
            try:
                kwargs = resolve_provider_kwargs(provider)
                resp = client.complete(prompt=prompt, **kwargs)

                try:
                    parsed = parse_e2_response(
                        resp.text,
                        preset_id=request.analysis_context.get("preset_id", "garp"),
                    )
                    schema_pass = True
                    schema_error = None
                    parsed_dict = parsed.model_dump()
                    completeness_auto = True
                except Exception as e:
                    parsed = None
                    schema_pass = False
                    schema_error = f"{type(e).__name__}: {str(e)[:200]}"
                    parsed_dict = None
                    completeness_auto = False

                results.append({
                    "fixture": fixture_name,
                    "fixture_group": fixture["fixture_group"],
                    "model_label": provider,
                    "raw_content": resp.text,
                    "parsed": parsed_dict,
                    "metadata": resp.metadata_dict(),
                    "judgments": {
                        "schema_pass": schema_pass,
                        "schema_error": schema_error,
                        "completeness_auto": completeness_auto,
                        "naturalness_manual": None,
                        "insight_manual": None,
                    },
                    "expected": fixture.get("expected", {}),
                })
            except Exception as e:
                results.append({
                    "fixture": fixture_name,
                    "fixture_group": fixture["fixture_group"],
                    "model_label": provider,
                    "error": f"{type(e).__name__}: {str(e)[:300]}",
                    "judgments": {
                        "schema_pass": False,
                        "schema_error": str(e)[:200],
                        "completeness_auto": False,
                        "naturalness_manual": None,
                        "insight_manual": None,
                    },
                })

    total_cost = sum(r.get("metadata", {}).get("cost_usd", 0) for r in results)
    fallback_count = sum(
        1 for r in results
        if r.get("metadata", {}).get("fallback_from") is not None
    )
    schema_pass_count = sum(1 for r in results if r["judgments"]["schema_pass"])

    output = {
        "step": "step8_2way_e2_raw",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "matrix_size": {
            "fixtures": len(ALL_FIXTURES),
            "models": len(PROVIDERS),
            "total_calls": len(results),
        },
        "providers": PROVIDERS,
        "fixture_groups": FIXTURE_GROUPS,
        "results": results,
        "summary": {
            "total_calls": len(results),
            "total_cost_usd": round(total_cost, 4),
            "fallback_count": fallback_count,
            "schema_pass_count": schema_pass_count,
        },
        "evaluation_guide": EVALUATION_GUIDE,
        "manual_eval_required": [
            "results[].judgments.naturalness_manual (1~5)",
            "results[].judgments.insight_manual (1~5)",
        ],
    }

    output_path = Path("docs/portfolio/coach/slice3/step8_2way_e2_raw.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(output, ensure_ascii=False, indent=2, default=_json_default)
    output_path.write_text(serialized, encoding="utf-8")

    # Round-trip 검증 (D4 가이드)
    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert loaded["summary"]["total_calls"] == len(results), "Round-trip failed"

    print(f"[Saved] {output_path}")
    print(f"  total calls:   {len(results)}")
    print(f"  total cost:    ${total_cost:.4f}")
    print(f"  schema_pass:   {schema_pass_count}/{len(results)}")
    print(f"  fallback:      {fallback_count}/{len(results)}")
    print()
    print("⚠️  수동 평가 필요 — 28건 (14 calls × 2 차원):")
    print("    - results[].judgments.naturalness_manual (1~5)")
    print("    - results[].judgments.insight_manual (1~5)")
    print(f"    가이드: output['evaluation_guide']")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 8.4.2 실행

```bash
python -m scripts.validation.run_step8_e2_2way
```

### 8.4.3 수동 평가 (14 calls × 2 차원 = 28건, ~56분)

```bash
jq '.evaluation_guide' docs/portfolio/coach/slice3/step8_2way_e2_raw.json
vim docs/portfolio/coach/slice3/step8_2way_e2_raw.json
# 14건의 results[].judgments.naturalness_manual + insight_manual 채움
```

### 8.4.4 score 산출 (A3.A — DIMENSION_LOOKUP[e2] 직접 추가)

**Q6 분기 — DIMENSION_LOOKUP[e2] 직접 추가** (delegation 불필요):

`scripts/validation/score_step8.py`에 추가 (Slice 2 Step 9 부분 일반화 결과 활용):

```python
DIMENSION_LOOKUP = {
    "e1": {  # Slice 1
        "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
        "dim2": {"key": "insight", "manual_field": "insight_manual"},
        "additional_lex_check": None,
        "weight": 0.5,
    },
    "e5": {  # Slice 2 (delegation 방식 — 산식 다름)
        "dim1": {"key": "intent_match", "manual_field": "intent_match_manual"},
        "dim2": {"key": "no_extra_changes", "manual_field": "no_extra_changes_manual"},
        "additional_lex_check": None,
        "delegate_to": "score_step8_e5",  # delegation 표시
        "weight": 0.5,
    },
    "e2": {  # Slice 3 신규 — e1 산식 그대로 + completeness 자동 보강
        "dim1": {"key": "naturalness", "manual_field": "naturalness_manual"},
        "dim2": {"key": "insight", "manual_field": "insight_manual"},
        "additional_lex_check": "completeness_auto",  # 1차 필터에 추가
        "weight": 0.5,
    },
}
```

`lexicographic_pass` 함수에 additional_lex_check 처리 추가:

```python
def lexicographic_pass(judgments, metadata, entrypoint: str):
    config = DIMENSION_LOOKUP[entrypoint]
    # delegation 처리 (e5 케이스)
    if "delegate_to" in config:
        # 별도 스크립트로 delegation
        ...

    # 기존 dim1, dim2 검증
    ...

    # additional_lex_check (e2의 completeness_auto)
    additional = config.get("additional_lex_check")
    if additional:
        if not judgments.get(additional):
            return False, f"{additional}_fail"

    return True, "pass"
```

### 8.4.5 score 실행

```bash
python -m scripts.validation.score_step8 \
    --input docs/portfolio/coach/slice3/step8_2way_e2_raw.json \
    --output docs/portfolio/coach/slice3/step8_2way_e2_scored.json \
    --entrypoint e2
```

### 8.4.6 그룹별 비교 분석 추가

`scripts/validation/analyze_e2_groups.py` 신설:

```python
"""Step 8 — fixture 그룹별 비교 분석 (Q4 hybrid 검증).

baseline (garp 3) vs focused (e2 4)의 모델별 점수 차이 측정.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from scripts.validation._setup import init_django

init_django()


def main() -> int:
    scored = json.loads(Path(
        "docs/portfolio/coach/slice3/step8_2way_e2_scored.json"
    ).read_text(encoding="utf-8"))

    # 모델별 × 그룹별 집계
    by_model_group = defaultdict(lambda: defaultdict(list))
    for fixture_results in scored["by_fixture_model"].values():
        for r in fixture_results:
            group = r.get("fixture_group", "unknown")
            by_model_group[r["model_label"]][group].append({
                "naturalness": r["raw_judgments"].get("naturalness_manual") or 0,
                "insight": r["raw_judgments"].get("insight_manual") or 0,
                "efficiency": r["efficiency"],
            })

    # 비교
    comparison = {}
    for model in by_model_group:
        comparison[model] = {}
        for group in by_model_group[model]:
            items = by_model_group[model][group]
            comparison[model][group] = {
                "n": len(items),
                "naturalness_mean": round(
                    sum(i["naturalness"] for i in items) / len(items), 4
                ),
                "insight_mean": round(
                    sum(i["insight"] for i in items) / len(items), 4
                ),
                "efficiency_mean": round(
                    sum(i["efficiency"] for i in items) / len(items), 4
                ),
            }

    # Q4 hybrid 검증
    hybrid_validation = {
        "context": "baseline 그룹과 focused 그룹의 점수 차이로 hybrid 결정 정당화",
        "interpretation_guide": {
            "small_diff": "두 그룹 점수 유사 → hybrid 결정 정당. 단일 그룹 fixture로도 충분했을 가능성.",
            "baseline_higher": "baseline이 점수 높음 → garp fixture가 모델에 친숙. focused fixture는 도전적.",
            "focused_higher": "focused가 점수 높음 → E2 특화 fixture가 모델에 더 자연스러움.",
        },
    }

    output = {
        "step": "step8_e2_group_analysis",
        "comparison": comparison,
        "hybrid_validation": hybrid_validation,
    }

    output_path = Path("docs/portfolio/coach/slice3/step8_2way_e2_group_analysis.json")
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[Saved] {output_path}")
    for model, groups in comparison.items():
        print(f"\n{model}:")
        for group, stats in groups.items():
            print(f"  {group}: nat={stats['naturalness_mean']}, "
                  f"ins={stats['insight_mean']}, eff={stats['efficiency_mean']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

```bash
python -m scripts.validation.analyze_e2_groups
```

### 8.4.7 validation_report_slice3.md 작성 (수동, ~30분)

`docs/portfolio/coach/slice3/validation_report_slice3.md`:

```markdown
# Validation Report — Slice 3 (E2)

> 작성일: 2026-XX-XX
> 진입점: E2 (진단 카드 4요소)
> 범위: Step 6 ~ Step 9

## 1. Step 6 결과

- fixture: garp_tech (slice1_baseline group)
- provider: haiku (D2.B)
- 4개 판정: schema/completeness/naturalness/insight + cost/latency
- 결정: PASS / FAIL

## 2. Step 7 토큰 측정

- 7 fixture 토큰 분포: ...
- recommended_budget: ...
- I4 모니터링: ...
- **그룹 비교**: baseline mean vs focused mean

## 3. Step 8 회고 (2-way × 7 fixture)

### 3.1 매트릭스

- 14 calls (haiku 7 + sonnet 7)

### 3.2 모델별 결과

| 모델   | lex_pass_rate | naturalness | insight | efficiency | cost_total |
| ------ | ------------- | ----------- | ------- | ---------- | ---------- |
| haiku  | ...           | ...         | ...     | ...        | ...        |
| sonnet | ...           | ...         | ...     | ...        | ...        |

### 3.3 winner

- {{WINNER}}: haiku / sonnet
- 근거: ...

### 3.4 fixture 그룹 분석 (Q4 hybrid 검증)

- baseline group (garp 3): naturalness_mean=..., insight_mean=...
- focused group (e2 4): naturalness_mean=..., insight_mean=...
- 차이 해석: ...

### 3.5 Slice 1 직접 비교

- Slice 1 E1 winner: haiku
- Slice 3 E2 winner (baseline group only): {{WINNER}}
- 일관성 분석: ...

## 4. Step 9 리팩토링 결과

- #5 E5_TOKEN_BUDGET 상수 도입: 적용/이연
- #3, #4 (Step 2 흡수): 완료

## 5. 누적 비용

- 총 호출: ?/50
- 총 비용: $?

## 6. Slice 4 백로그

- ...
```

## 8.5 검증 판정

| #   | 판정                        | 임계                   | 자동/수동 |
| --- | --------------------------- | ---------------------- | --------- |
| 1   | 14 calls 실행 완료          | 14/14 (오류 0)         | 자동      |
| 2   | round-trip 검증 (D4 가이드) | OK                     | 자동      |
| 3   | 수동 평가 입력              | 28/28 필드             | 수동      |
| 4   | score 스크립트 정상 실행    | winner 결정            | 자동      |
| 5   | 그룹별 비교 분석            | comparison 산출        | 자동      |
| 6   | validation_report 작성      | 6 섹션 모두            | 수동      |
| 7   | CostGuard 누적              | 15/50 (재시도 포함 18) | 자동      |

## 8.6 롤백 / 실패 시 처리

(Slice 2 Step 8 패턴 동일 — 케이스 A~C)

추가 케이스 (Slice 3 신규):

- **케이스 D. 1차 손실 재발 (D4 위반)**: 이번 슬라이스에서는 \_json_default + round-trip 검증으로 차단됨. 발생 시 즉시 원인 분석 (set 외 다른 비-JSON 타입 추정) + 핸들러 추가.
- **케이스 E. fixture 그룹 점수 큰 차이**: hybrid 결정 재검토. Slice 4에서 fixture 전략 변경 신호.

## 8.7 산출물

- `scripts/validation/run_step8_e2_2way.py` (신규, ~180줄)
- `scripts/validation/analyze_e2_groups.py` (신규, ~80줄)
- `scripts/validation/score_step8.py` (확장, +DIMENSION_LOOKUP[e2])
- `docs/portfolio/coach/slice3/step8_2way_e2_raw.json` (실행 산출물)
- `docs/portfolio/coach/slice3/step8_2way_e2_scored.json` (점수 산출물)
- `docs/portfolio/coach/slice3/step8_2way_e2_group_analysis.json` (그룹 비교)
- `docs/portfolio/coach/slice3/validation_report_slice3.md` (보고서)

## 8.8 비용 가드

- LLM 호출: 14회 (haiku 7 + sonnet 7)
- 예상 비용: 7 × $0.005 + 7 × $0.0156 = $0.146
- 누적: 15 / 50 (재시도 포함 ~18)

---

# Step 9 — 30분 리팩토링 슬롯 (#5 단독, A2.C)

## 9.1 목표

Slice 2 백로그 #5 — **E5_TOKEN_BUDGET 상수 + LLMClient 입력 가드레일** (PriorityScore 2.0, 30분 슬롯).

E2 토큰 측정 결과(Step 7) 활용 가능 → Step 9에서 진입점별 budget 상수 통합 설계.

## 9.2 백로그 #5 상세

| 항목             | 내용                                                         |
| ---------------- | ------------------------------------------------------------ |
| Slice 2 백로그 # | #5                                                           |
| PriorityScore    | 2.0                                                          |
| 예상 시간        | 30분                                                         |
| 출처             | Slice 2 Step 7 결정 #1 — 코드 상수 미도입 (현재 출력 한도만) |
| 본 슬라이스 추가 | E2_TOKEN_BUDGET 동시 도입 (Step 7 결과 활용)                 |

## 9.3 작업 단계

### 9.3.1 진입점별 budget 상수 모듈 신설

`portfolio/llm/token_budgets.py` 신설:

```python
"""진입점별 LLM input token budget 상수.

Slice 2 백로그 #5 처리.
Step 7 토큰 측정 결과 기반 상수 정의.

Slice 단위로 budget 결정:
- Slice 1 (E1): Step 7 측정 → budget = 5,000
- Slice 2 (E5): Step 7 측정 → budget = 2,000
- Slice 3 (E2): Step 7 측정 → budget = (Slice 3 Step 7 recommended_budget)
"""
from __future__ import annotations

# 진입점별 input token budget
ENTRYPOINT_TOKEN_BUDGETS = {
    "e1": 5000,    # Slice 1 결정값
    "e5": 2000,    # Slice 2 Step 7 측정 결과 (P90×1.5=1134 → round-up 2000)
    "e2": 4000,    # Slice 3 Step 7 측정 결과로 갱신 (placeholder)
    # Slice 4 진입 시 e3/e4/e6 추가
}


def get_token_budget(entrypoint: str) -> int:
    """진입점별 budget 반환.

    Raises:
        ValueError: 미등록 진입점
    """
    if entrypoint not in ENTRYPOINT_TOKEN_BUDGETS:
        raise ValueError(
            f"Unknown entrypoint: {entrypoint}. "
            f"Available: {list(ENTRYPOINT_TOKEN_BUDGETS.keys())}"
        )
    return ENTRYPOINT_TOKEN_BUDGETS[entrypoint]
```

### 9.3.2 LLMClient 입력 가드레일 통합

`portfolio/llm/client.py`:

```python
from portfolio.llm.token_budgets import get_token_budget


class LLMClient:
    def complete(
        self,
        prompt: str,
        provider: str,
        model: str,
        entrypoint: Optional[str] = None,  # 신규 인자
    ) -> LLMResponse:
        # 입력 토큰 가드레일
        if entrypoint:
            budget = get_token_budget(entrypoint)
            estimated_tokens = self._estimate_tokens(prompt)
            if estimated_tokens > budget:
                raise LLMBudgetExceededError(
                    f"Input prompt {estimated_tokens} tokens > "
                    f"budget {budget} for entrypoint {entrypoint}"
                )

        # 기존 호출 로직
        ...

    def _estimate_tokens(self, prompt: str) -> int:
        """간단한 토큰 추정. 정확한 카운트는 SDK count_tokens 사용 가능."""
        # heuristic: 4 chars ≈ 1 token (영어/한국어 평균)
        return len(prompt) // 3  # 보수적
```

### 9.3.3 services 통합

`portfolio/services/e1_garp.py`, `e2_diagnostic_card.py`, `e5_adjustment_parser.py` 모두 다음 패턴으로 갱신:

```python
def run_e2(request, *, provider="haiku"):
    prompt = build_e2_prompt(request)
    kwargs = resolve_provider_kwargs(provider)
    client = LLMClient()
    raw = client.complete(prompt=prompt, entrypoint="e2", **kwargs)  # entrypoint 추가
    ...
```

### 9.3.4 단위 테스트

`portfolio/tests/test_token_budgets.py` 신설:

```python
import pytest
from portfolio.llm.token_budgets import (
    ENTRYPOINT_TOKEN_BUDGETS, get_token_budget,
)


def test_token_budgets_defined():
    """e1, e5, e2 budget 정의됨."""
    for ep in ("e1", "e5", "e2"):
        assert ep in ENTRYPOINT_TOKEN_BUDGETS
        assert ENTRYPOINT_TOKEN_BUDGETS[ep] > 0


def test_get_token_budget_known():
    assert get_token_budget("e1") == 5000
    assert get_token_budget("e5") == 2000


def test_get_token_budget_unknown():
    with pytest.raises(ValueError, match="Unknown entrypoint"):
        get_token_budget("e99_nonexistent")
```

### 9.3.5 회귀 검증 (#5 핵심 KPI)

```bash
# Slice 1, 2, 3 모두 회귀 통과
pytest portfolio/tests/ -q
# 예상: 119 + 3 = 122 passed

# Slice 1 score 재실행 동일 결과 (Slice 2 Step 9에서 검증한 패턴)
python -m scripts.validation.score_step8 \
    --input docs/portfolio/coach/slice1/step8_3way_raw.json \
    --output /tmp/slice1_after_step9.json \
    --entrypoint e1
diff <(jq -S 'del(.scored_at)' docs/portfolio/coach/slice1/step8_3way_scored.json) \
     <(jq -S 'del(.scored_at)' /tmp/slice1_after_step9.json)
# 예상: 차이 없음
```

## 9.4 한도 초과 시 처리 (A2.C 단점 보완)

30분 안에 #5 작업 미완료 시:

- 즉시 중단. token_budgets.py 변경 사항 git stash
- LLMClient 변경 사항 revert
- Slice 4 백로그 #1로 이연

## 9.5 검증 판정

| #   | 판정                         | 임계             | 자동 |
| --- | ---------------------------- | ---------------- | ---- |
| 1   | token_budgets.py 모듈 import | 자동             | 자동 |
| 2   | 단위 테스트 통과             | 3/3              | 자동 |
| 3   | services 갱신 후 회귀        | 119 → 122 passed | 자동 |
| 4   | Slice 1/2/3 산출물 회귀      | diff 차이 없음   | 자동 |
| 5   | 30분 한도 준수               | 실제 ≤ 32분      | 수동 |

## 9.6 산출물

- `portfolio/llm/token_budgets.py` (신규, ~50줄)
- `portfolio/llm/client.py` (확장, +20줄)
- `portfolio/services/e1_garp.py`, `e2_diagnostic_card.py`, `e5_adjustment_parser.py` (각각 +1줄)
- `portfolio/tests/test_token_budgets.py` (신규, ~30줄)
- `docs/portfolio/coach/slice3/refactor_backlog_slice3.md` (Slice 4 이연 항목)

## 9.7 비용 가드

- LLM 호출: 0회
- 누적: ~18 / 50

---

# Slice 3 종결 작업

## S.1 비용 가드 보고

```bash
python -c "
from portfolio.llm.cost_guard import CostGuard
g = CostGuard.get_instance()
import json
print(json.dumps(g.status(), ensure_ascii=False, indent=2))
"
```

## S.2 누적 보고

- 총 호출: ~18/50 (Slice 3)
- 총 비용: ~$0.16
- Slice 3 종료 시점 reset 다음 슬라이스 진입 직전.

## S.3 Slice 4 백로그 갱신

`docs/portfolio/coach/slice3/refactor_backlog_slice3.md`:

```markdown
# Slice 3 Refactor Backlog (Slice 4 이연)

## Slice 2에서 이연 + Slice 3 신규

| #   | 항목                                                    | PS     | 출처                | 예상 시간 |
| --- | ------------------------------------------------------- | ------ | ------------------- | --------- |
| 1   | score 산식 통합 (e1 동적 normalize + e5 정적, e2 추가)  | 3.0    | Slice 2 백로그 #2   | 60분      |
| 2   | Step 8 raw output CSV 옵션                              | 1.0    | Slice 1 Deferred #7 | 10분      |
| 3   | Mock LLMClient mode dict 매핑                           | 1.0    | Slice 1 Deferred #8 | 10분      |
| 4   | I4 — analysis_summary 200자 압축 (utilization > 70% 시) | 조건부 | Slice 2/3 모니터링  | 5분       |
| 5   | LLM-as-judge 도입 (Phase 2 → Slice 5 이후)              | 5.0    | Q7 Phase 2          | ~6시간    |

## Slice 3 신규 발견

| #   | 항목                                                                  | PS     | 출처                | 예상 시간 |
| --- | --------------------------------------------------------------------- | ------ | ------------------- | --------- |
| 6   | \_prompt_helpers.py 추가 헬퍼 (예: format_metrics_table 일반화)       | 1.5    | Step 2 작성 시 발견 | 15분      |
| 7   | DiagnosticCard 4요소 가중치 (현재 균등) — 사용자 피드백 후 가중 도입  | 조건부 | Phase 2             | 30분      |
| 8   | fixture 그룹 비교 자동 보고 — analyze_e2_groups를 score 산출물에 통합 | 2.0    | Step 8 작성 시 발견 | 20분      |

## Slice 1 미해결 (재확인)

- garp_large fixture 토큰 효과 측정 (E3 시점)
- gemini Flash paid tier 활성화 시 재비교
```

---

# Part 2 종결 체크리스트

Step 6 ~ Step 9 완료 직전 본인 확인:

- [ ] **Step 6 (D2.B + D4 가이드)**: garp_tech × haiku × 1회. schema_pass + completeness_auto + naturalness/insight ≥ 3 + cost ≤ $0.020. round-trip 검증 OK
- [ ] **Step 7**: 7 fixture 토큰 측정 + 그룹 비교 산출. budget 결정 + I4 모니터링
- [ ] **Step 8 (A1.B)**: 14 calls (haiku 7 + sonnet 7). schema_pass 100% (D4 가이드). 28건 manual 평가 입력. winner 결정
- [ ] **Step 8 그룹 분석 (Q4 검증)**: baseline vs focused 비교 산출. hybrid 결정 정당성 평가
- [ ] **Step 9 (#5, A2.C)**: token_budgets.py + LLMClient 입력 가드레일 + services 통합. 회귀 122 passed
- [ ] **validation_report_slice3.md** 6 섹션 작성 (Slice 1 직접 비교 포함)
- [ ] **refactor_backlog_slice3.md** 작성
- [ ] 누적 LLM 호출: ~18/50 (36%)
- [ ] 누적 비용: ~$0.16
- [ ] 회귀: 122 passed 유지
- [ ] CostGuard 자동 reset 패턴 검증 (Slice 4 진입 시 동작 확인)

---

# 부록 A — Slice 3 종결 결정 표

| 항목                   | 값                                                 |
| ---------------------- | -------------------------------------------------- |
| 진입점                 | E2                                                 |
| Default provider       | haiku                                              |
| Step 8 매트릭스        | 7×2=14 (hybrid fixture)                            |
| Step 9 슬롯 작업       | #5 token_budgets 상수 도입                         |
| 평가 차원              | naturalness/insight (manual) + completeness (자동) |
| Step 8 winner          | (실행 후 기재)                                     |
| fixture 그룹 비교 결과 | (실행 후 기재)                                     |
| 누적 호출              | (실행 후 기재)                                     |
| Slice 4 진입 결정      | Slice 3 종결 회고 시                               |

# 부록 B — Part 2 신규 파일 목록

| 파일                                                                                | 종류                        | 줄 수 |
| ----------------------------------------------------------------------------------- | --------------------------- | ----- |
| `scripts/validation/run_step6_e2_smoke.py`                                          | 실 호출 1회                 | ~140  |
| `scripts/validation/measure_e2_tokens.py`                                           | 토큰 측정 + 그룹 비교       | ~120  |
| `scripts/validation/run_step8_e2_2way.py`                                           | 14 calls                    | ~180  |
| `scripts/validation/analyze_e2_groups.py`                                           | 그룹 비교 분석              | ~80   |
| `scripts/validation/score_step8.py`                                                 | (확장) DIMENSION_LOOKUP[e2] | +30   |
| `portfolio/llm/token_budgets.py`                                                    | (신규) 백로그 #5            | ~50   |
| `portfolio/llm/client.py`                                                           | (확장) 입력 가드레일        | +20   |
| `portfolio/services/e1_garp.py`, `e2_diagnostic_card.py`, `e5_adjustment_parser.py` | (정리) entrypoint 인자      | +3    |
| `portfolio/tests/test_token_budgets.py`                                             | 단위 테스트                 | ~30   |
| `docs/portfolio/coach/slice3/step6_smoke_e2_output.json`                            | 산출물                      | —     |
| `docs/portfolio/coach/slice3/step7_e2_token_measurement.json`                       | 산출물                      | —     |
| `docs/portfolio/coach/slice3/step8_2way_e2_raw.json`                                | 산출물                      | —     |
| `docs/portfolio/coach/slice3/step8_2way_e2_scored.json`                             | 산출물                      | —     |
| `docs/portfolio/coach/slice3/step8_2way_e2_group_analysis.json`                     | 산출물                      | —     |
| `docs/portfolio/coach/slice3/validation_report_slice3.md`                           | 보고서                      | ~150  |
| `docs/portfolio/coach/slice3/refactor_backlog_slice3.md`                            | 백로그                      | ~50   |

총 신규 코드: ~650줄.

# 부록 C — 회귀 카운트 진행 표

| 단계                                  | 추가 테스트 | 누적    |
| ------------------------------------- | ----------- | ------- |
| Part 1 종결 baseline                  | —           | 119     |
| Step 6 (실 호출, 산출물만)            | 0           | 119     |
| Step 7 (오프라인 측정)                | 0           | 119     |
| Step 8 (실 호출, 산출물만)            | 0           | 119     |
| Step 9 (#5 token_budgets 단위 테스트) | +3          | **122** |

> Part 2 회귀 추가는 Step 9의 token_budgets 단위 테스트 3개만. 핵심 KPI는 Slice 1/2/3 회귀 유지.

# 부록 D — Slice 3 v2 갱신 최소화 체크리스트

본 지시서 작성 시 사전 반영:

- [x] Q4 hybrid 결정 명시 (3 baseline + 4 focused)
- [x] D4 회피 가이드 모든 run 스크립트에 \_json_default + round-trip 의무
- [x] CostGuard 멱등성 (reset_for_slice 두 번 호출해도 안전)
- [x] DIMENSION_LOOKUP[e2] 직접 추가 (delegation 불필요)
- [x] completeness 자동 측정 — additional_lex_check 패턴
- [x] fixture 그룹 메타 (FIXTURE_GROUPS) 산출물에 보존 — Q4 검증 자료
- [x] e2 score = e1 산식 그대로 + completeness 자동 추가만 (코드 절감)
- [x] entrypoint 인자 도입 (Step 9 #5) — 추후 슬라이스 자동 활용
- [x] Slice 4 백로그 명세 (PS 분포 + 신규 발견 항목)
- [x] Slice 1 직접 비교 섹션 (validation_report_slice3.md §3.5) — Q4 hybrid 정당화
