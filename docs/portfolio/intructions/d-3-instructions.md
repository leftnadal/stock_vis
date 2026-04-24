# D-3 Instructions: E2 Diagnostic Cards Prompt

> **세션**: D-3
> **목적**: LLM 진입점 E2 (약점 3개에 대한 4요소 진단 카드) 프롬프트 작성
> **전제 세션**: D-2 완료 (E1 구조 검증)
> **대상 에이전트**: Claude Code
> **버전**: v1.0 (2026-04-20)

---

## 0. 에이전트가 먼저 읽을 것

**필수 참조**:
1. `docs/portfolio/design/coach-llm-design-v1.md` — §3-2 E2 상세 + 4요소 구조
2. `docs/portfolio/design/preset-design-v3.1.md` — §7-3 문체 원칙 (단정형 회피, 구조적 vs 단일 이상치 구분)
3. `docs/portfolio/implementation/schemas/diagnostic.py` — `DiagnosticCard` 스키마 (D-0b)
4. `docs/portfolio/implementation/schemas/llm_outputs.py` — `DiagnosticCards` 최종 출력 스키마
5. `docs/portfolio/design/metric-dictionary-v1.2.md` — 지표 배경 지식

---

## 1. 목표

약점 3개 각각에 대해 구조화된 4요소 진단 카드를 생성.

### 1-1. 4요소 구조 (DiagnosticCard)

1. `what_is_wrong` — 팩트 진술 (1~2문장)
2. `comparison_basis` — 비교 기준 명시 (1문장)
3. `why_it_matters` — 프리셋 철학 연결 (1~2문장)
4. `caveat_or_exception` — 예외/트레이드오프 (1문장)

추가 메타:
- `severity` (high/medium/low)
- `structural_or_single` (structural/single_outlier)

### 1-2. 산출물

```
implementation/prompts/e2/
├── __init__.py
├── instructions.py        (4요소 작성 가이드)
├── examples.py            (few-shot 3개, 다양한 severity)
├── input_builder.py       (약점별 상세 정보 추출)
└── e2_builder.py          (조립)
```

### 1-3. 진입점 특성 (§8-4)

- **트리거**: AnalysisRun 완료 직후
- **Wallet 주입**: **최소** (excluded 여부 정도만)
- **Tier 1~3**: 불필요

---

## 2. 사전 조건

- [x] D-2 완료 (E1 구조를 템플릿으로 활용)
- [x] `DiagnosticCard`, `DiagnosticCards` 스키마 존재

---

## 3. 단계별 작업 명세

### Step 1: `instructions.py` — E2 지시문

**핵심 내용**:

**참고 템플릿**:
```python
E2_INSTRUCTIONS = """
# Task: Generate Diagnostic Cards (E2)

Generate up to 3 diagnostic cards, one for each of the top weaknesses in the
analysis target portfolio.

## Output
Return valid JSON matching:
{
  "cards": [
    {
      "weakness_metric_id": "...",
      "what_is_wrong": "...",
      "comparison_basis": "...",
      "why_it_matters": "...",
      "caveat_or_exception": "...",
      "severity": "high" | "medium" | "low",
      "structural_or_single": "structural" | "single_outlier"
    },
    ...
  ]
}

## Four-Element Structure (CRITICAL)

Each card has EXACTLY four narrative elements. Use them in order.

### 1. what_is_wrong (팩트 진술)
- State WHAT is observed, not WHY.
- 1-2 Korean sentences.
- Use specific numbers when available (percentiles, ratios, counts).
- Examples:
  - "5개 종목의 평균 PEG가 2.8로, 프리셋 가이드라인 (PEG < 1.5) 대비 크게 높습니다."
  - "ROIC 5년 평균이 12%로, 업종 하위 35% 구간에 위치합니다."

### 2. comparison_basis (비교 기준 명시)
- Make the benchmark EXPLICIT.
- 1 sentence.
- State WHICH universe/industry/sector the comparison is against.
- Examples:
  - "비교 기준: GICS Semiconductors 산업 87개 종목."
  - "비교 기준: S&P 500 전체 유니버스."
  - "비교 기준: 프리셋 정의 임계값 (PEG < 1.5)."

### 3. why_it_matters (프리셋 철학 연결)
- Connect to the PRESET's philosophy, not to generic wisdom.
- 1-2 Korean sentences.
- Start with "[프리셋명] 관점에서는..." pattern when appropriate.
- Examples:
  - "GARP 관점에서는 성장 둔화 시 높은 PEG는 급격한 밸류에이션 조정으로 이어질 수 있어, 핵심 리스크입니다."
  - "Buffett 관점에서는 지속적인 ROIC는 '경제적 해자'의 대표 지표로, 이 기준이 흔들리면 퀄리티 전제가 약해집니다."

### 4. caveat_or_exception (예외/트레이드오프)
- Acknowledge NUANCE. Prevent over-generalization.
- 1 sentence.
- Common patterns:
  - Single outlier skews average
  - Time horizon matters
  - Different preset would interpret differently
- Examples:
  - "단, NVDA 한 종목의 PEG 4.2가 평균을 끌어올린 측면도 있어 구조적 이슈는 아닐 수 있습니다."
  - "단, 최근 1년 CAPEX 증가로 인한 일시적 효과일 수 있어 향후 2~3분기 관찰이 필요합니다."

## Severity Assignment
- `high`: Core tier metric, level_tag="critical" or "weak" on ≥50% of holdings
- `medium`: Core/Supporting tier, level_tag="weak" on 30-50% or "moderate" on most
- `low`: Supporting tier, or marginal weakness

## Structural vs Single Outlier
- `single_outlier`: Metric average skewed by 1 holding (e.g., NVDA's PEG in an otherwise healthy portfolio)
- `structural`: Most/all holdings in the portfolio exhibit the weakness

## Rules
- DO NOT recommend actions ("사야 한다", "팔아야 한다").
- DO NOT switch presets mid-analysis.
- DO use conditional language ("-수 있습니다", "-가능성이 있습니다").
- DO keep each element within the specified length.
"""
```

### Step 2: `examples.py` — Few-shot 예시 3개

**에이전트 작업 지침**:
- 예시 3개는 **반드시 서로 다른 severity** 분포 보이기 (high 1개, medium 1개, low 1개)
- 예시 3개 중 최소 1개는 **single_outlier** 포함
- 각 예시는 다른 프리셋 사용

**예시 1 템플릿 (high severity, structural)**:
```python
EXAMPLE_1 = {
    "scenario": "GARP + Tech portfolio with broad valuation concern",
    "input": """
{
  "analysis_target_portfolio": {
    "portfolio_name": "Tech 성장주",
    "preset_id": "garp",
    "preset_name": "GARP",
    "preset_category": "growth",
    "holding_count": 5,
    "weaknesses_detail": [
      {
        "metric_id": "peg_ratio",
        "metric_display_name": "PEG 비율",
        "tier": "core",
        "avg_value": 2.8,
        "per_holding": [
          {"symbol": "NVDA", "value": 4.2, "level_tag": "critical"},
          {"symbol": "MSFT", "value": 2.5, "level_tag": "weak"},
          {"symbol": "AAPL", "value": 2.7, "level_tag": "weak"},
          {"symbol": "AMD",  "value": 2.4, "level_tag": "weak"},
          {"symbol": "GOOGL","value": 2.1, "level_tag": "moderate"}
        ],
        "percentile_scope": "industry",
        "threshold_applied": 1.5,
        "passed_threshold_count": 0,
        "industry_median": 1.8
      }
    ]
  }
}
""",
    "output": """
{
  "cards": [
    {
      "weakness_metric_id": "peg_ratio",
      "what_is_wrong": "5개 종목 모두 PEG가 2.0 이상이며, 포트폴리오 평균 PEG는 2.8입니다. 프리셋 통과 기준 (PEG < 1.5)을 만족하는 종목이 없습니다.",
      "comparison_basis": "비교 기준: GICS Software/Semiconductors 산업의 업종 중앙값 (PEG 1.8) + 프리셋 임계값 (PEG < 1.5).",
      "why_it_matters": "GARP 관점에서 성장 대비 높은 밸류에이션은 성장 둔화 시 급격한 조정 리스크로 직결됩니다. 현재 수준은 '합리적 가격'이라는 프리셋 핵심 가정을 벗어난 상태입니다.",
      "caveat_or_exception": "단, NVDA 한 종목의 PEG 4.2가 평균을 크게 끌어올린 측면이 있어, NVDA 제외 시 평균은 2.4로 다소 완화됩니다.",
      "severity": "high",
      "structural_or_single": "structural"
    }
  ]
}
"""
}
```

**예시 2 템플릿 (medium, single_outlier)**:
- Scenario: Dividend Growth 포트폴리오에서 1개 종목만 배당 삭감

**예시 3 템플릿 (low, structural context)**:
- Scenario: Buffett Quality Value 포트폴리오에서 Context tier 지표 하나의 애매함

**에이전트는 각 시나리오를 설계 문서의 preset 정의 + metric dictionary 참조해서 현실적으로 작성**.

### Step 3: `input_builder.py` — 약점 상세 추출

**함수**:
```python
def build_e2_input(context: AnalysisContext) -> dict:
    """
    E2는 '약점'의 상세를 필요로 함:
    - 각 약점 metric의 종목별 값
    - 비교 기준 (percentile_scope, threshold)
    - 업종/유니버스 중앙값 (있으면)
    """
    p = context.analysis_target_portfolio

    # 약점을 weakness_detail로 확장
    weaknesses_detail = []
    for weakness in p.weaknesses:  # 최대 3개
        # metric_id로 core/supporting/context 결과에서 찾아 상세 정보 추출
        detail = _find_metric_detail(
            metric_id=weakness.metric_id,
            core=p.core_metric_results,
            supporting=p.supporting_metric_results,
            context=p.context_metric_results,
        )
        weaknesses_detail.append({
            "metric_id": weakness.metric_id,
            "metric_display_name": weakness.metric_display_name,
            "tier": detail.tier,
            "value": detail.value,
            "percentile": detail.percentile,
            "percentile_scope": detail.percentile_scope,
            "level_tag": detail.level_tag,
            "threshold_applied": detail.threshold_applied,
            "passed_threshold": detail.passed_threshold,
            # 추가: 종목별 분포 (백엔드에서 제공 가정)
            # "per_holding": [...]
        })

    return {
        "analysis_target_portfolio": {
            "portfolio_name": p.portfolio_name,
            "preset_id": p.preset_id,
            "preset_name": p.preset_name,
            "preset_category": p.preset_category,
            "holding_count": p.holding_count,
            "weaknesses_detail": weaknesses_detail,
            # holdings_summary는 metric_id별 단일 종목 이상치 판단에 필요
            "holdings_summary_light": [
                {"symbol": h.stock_symbol, "sector": h.sector, "weight": float(h.weight)}
                for h in p.holdings_summary
            ],
        },
        "wallet_background": {
            "excluded_from_this_portfolio_count": context.wallet_background.excluded_from_this_portfolio_count,
        },
    }


def _find_metric_detail(metric_id, core, supporting, context):
    """Core/Supporting/Context 리스트에서 metric_id로 MetricResult 찾기."""
    for mr in core + supporting + context:
        if mr.metric_id == metric_id:
            return mr
    raise ValueError(f"Metric {metric_id} not found")
```

**중요**: E2는 **per-holding 값 배열**이 중요. 백엔드에서 이 데이터를 제공한다고 가정. 없으면 weakness에 집계값만 포함.

### Step 4: `e2_builder.py` — 조립

```python
from portfolio.prompts.tier0 import build_tier0
from .instructions import E2_INSTRUCTIONS
from .examples import FEW_SHOT_EXAMPLES
from .input_builder import build_e2_input


def build_e2_prompt(context: AnalysisContext, prompt_version: str = "1.1") -> tuple[str, str]:
    system_prompt = build_tier0(prompt_version=prompt_version)

    parts = [E2_INSTRUCTIONS]

    parts.append("## Examples\n")
    for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
        parts.append(f"### Example {i}: {example['scenario']}\n")
        parts.append(f"Input:\n{example['input']}\n")
        parts.append(f"Output:\n{example['output']}\n")

    input_data = build_e2_input(context)
    parts.append("## Now generate diagnostic cards for this portfolio:\n")
    parts.append(f"Input:\n{json.dumps(input_data, ensure_ascii=False, indent=2, default=str)}\n")
    parts.append("Output:\n")

    return system_prompt, "\n".join(parts)
```

### Step 5: `__init__.py`

Re-export.

---

## 4. 검증 지점

### 4-1. 카드 개수

각 예시 output에서 `cards` 배열 길이가 약점 수와 일치해야 함.

### 4-2. 4요소 완전성

각 카드는 정확히 4개 텍스트 요소 + severity + structural_or_single 모두 존재.

### 4-3. Severity 분포

예시 3개 중 severity 다양성 있는지:
```python
severities = set()
for ex in FEW_SHOT_EXAMPLES:
    data = json.loads(ex["output"])
    for card in data["cards"]:
        severities.add(card["severity"])
assert len(severities) >= 2, "Severity not diverse in examples"
```

### 4-4. Structural/Single 균형

예시들에 최소 1개 single_outlier 포함.

### 4-5. 토큰 예산

E2는 E1보다 큼 (예시 3개 + per-holding 데이터). 예상 **5,000~8,000 토큰**.

---

## 5. 에이전트 판단 허용 범위

### 5-1. 허용
- 예시 시나리오 선택
- 지시문 한국어 예시 추가
- per_holding 배열 구조의 세부

### 5-2. 금지
- 4요소 중 하나 생략
- severity 범주 변경
- "추천한다" 같은 action 언어 허용

### 5-3. 판단 어려운 경우
- per_holding 데이터 소스 확인 필요 시 사용자 보고
- severity 판정 기준 구체화 필요 시 사용자 보고

---

## 6. 산출물

**신규 파일 (5개)**: `prompts/e2/*`

**예상 줄 수**: 400~600줄 (예시 텍스트가 많음)

---

## 7. 완료 보고 포맷

```markdown
# D-3 완료 보고

## 생성 파일 (5개)
- prompts/e2/*

## Few-shot 예시
- 예시 1: [preset, severity]
- 예시 2: [preset, severity]
- 예시 3: [preset, severity]

## 크기
- System + User 예상 토큰: ~K

## 검증 결과
- [✓] 4요소 완전성
- [✓] Severity 분포
- [✓] Single/structural 균형

## 판단 포인트

## 다음 세션 준비
- D-4: E3 지표별 한 줄 코멘트
```

---

## 8. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판 |
