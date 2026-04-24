# D-4 Instructions: E3 Per-Metric One-Liner Prompt

> **세션**: D-4
> **목적**: LLM 진입점 E3 (Core + Supporting 지표 각각에 대한 1~2문장 코멘트) 프롬프트 작성
> **전제 세션**: D-3 완료
> **대상 에이전트**: Claude Code
> **버전**: v1.0 (2026-04-20)

---

## 0. 에이전트가 먼저 읽을 것

**필수 참조**:
1. `docs/portfolio/design/coach-llm-design-v1.md` — §3-3 E3 상세
2. `docs/portfolio/implementation/schemas/llm_outputs.py` — `MetricComment`, `MetricComments`
3. `docs/portfolio/design/metric-dictionary-v1.2.md` — 지표 정의 및 해석 가이드
4. `docs/portfolio/design/preset-design-v3.1.md` — 프리셋별 지표 철학

---

## 1. 목표

활성 프리셋의 Core + Supporting 지표 각각에 **1~2문장 코멘트**를 생성.

### 1-1. 특성

- **Context tier 지표는 MVP에서 포함하지 않음** (토큰 효율)
- 지표당 1~2문장
- 지표의 값, 비교 위치, 프리셋에서의 의미를 간결하게

### 1-2. 산출물

```
implementation/prompts/e3/
├── __init__.py
├── instructions.py
├── examples.py            (3~5개 지표별 예시)
├── input_builder.py
└── e3_builder.py
```

### 1-3. 진입점 특성 (§8-4)

- **트리거**: 분석 완료 직후 or UI에서 지표 상세 표시 시
- **Wallet 주입**: **포함 안 함**
- **Tier 1~3**: 불필요

**중요**: E3는 Wallet 정보가 전혀 없어야 함 (PV5 스타일). 지표 자체에만 집중.

---

## 2. 사전 조건

- [x] D-3 완료

---

## 3. 단계별 작업 명세

### Step 1: `instructions.py`

**참고 템플릿**:
```python
E3_INSTRUCTIONS = """
# Task: Generate Per-Metric Commentary (E3)

For each metric in the input, generate a concise 1-2 sentence Korean commentary.

## Output
Return valid JSON matching:
{
  "comments": [
    {
      "metric_id": "...",
      "one_liner": "<1-2 Korean sentences>"
    },
    ...
  ]
}

## Content Guidelines per Comment

Each one_liner should:
1. State the observation (value, percentile, pass/fail) first
2. If room remains, add a concise interpretation tied to the preset

Structure patterns:
- "[값/등급 팩트]. [프리셋 맥락 해석]."
- "[종목별 분포 특징]. [주목할 점 혹은 예외]."

Length:
- 1 sentence if the metric is clearly pass or clearly fail
- 2 sentences if there's notable nuance (mixed within portfolio, etc.)

Style:
- Use conditional language for interpretation
- Reference the preset's tier (Core/Supporting) briefly when it clarifies importance
- AVOID: "추천합니다", "사야 합니다"
- PREFER: "주목할 만합니다", "이 프리셋에서는 ___한 의미입니다"

## Rules
- Generate EXACTLY one comment per input metric
- Keep ordering same as input
- Skip Context-tier metrics (they are not in input)
"""
```

### Step 2: `examples.py`

**예시 3개 (다른 프리셋, 다른 지표 수준)**:

**예시 1** — Buffett Quality Value, Core "ROIC" (strong):
```python
EXAMPLE_1_INPUT = """
{
  "preset_id": "buffett_quality_value",
  "preset_name": "Buffett Quality Value",
  "metrics": [
    {
      "metric_id": "roic",
      "metric_display_name": "ROIC",
      "tier": "core",
      "value": 0.18,
      "percentile": 0.92,
      "percentile_scope": "industry",
      "level_tag": "excellent",
      "per_holding_excerpt": "5종목 중 4개가 상위 15% 이내"
    }
  ]
}
"""

EXAMPLE_1_OUTPUT = """
{
  "comments": [
    {
      "metric_id": "roic",
      "one_liner": "ROIC가 업종 상위 8%에 위치하며, 5개 종목 중 4개가 상위 15% 이내입니다. Buffett 관점의 Core 지표인 '지속적 자본 수익'을 견조히 충족하는 구성입니다."
    }
  ]
}
"""
```

**예시 2** — GARP, Core "PEG" (weak with outlier):
```python
EXAMPLE_2_OUTPUT = """
{
  "comments": [
    {
      "metric_id": "peg_ratio",
      "one_liner": "포트폴리오 평균 PEG가 2.8로 프리셋 기준(1.5)을 상회합니다. 단 NVDA 하나의 PEG 4.2가 평균을 끌어올린 측면이 있어, NVDA 제외 시 평균은 2.4로 다소 완화됩니다."
    }
  ]
}
"""
```

**예시 3** — Dividend Growth, Supporting "payout_ratio" (moderate):
```python
EXAMPLE_3_OUTPUT = """
{
  "comments": [
    {
      "metric_id": "payout_ratio",
      "one_liner": "배당성향이 평균 55%로 Dividend Growth 프리셋의 주목 구간(40~70%)에 있습니다. 배당 지속성은 합리적 수준이지만, 60% 초과 종목 2개는 경기 둔화 시 배당 삭감 리스크를 안고 있습니다."
    }
  ]
}
"""
```

### Step 3: `input_builder.py`

**함수**:
```python
def build_e3_input(context: AnalysisContext) -> dict:
    """
    E3: Core + Supporting 지표만. Context 지표 제외.
    Wallet 정보 완전 배제 (PV5 스타일).
    """
    p = context.analysis_target_portfolio

    metrics = []
    for mr in p.core_metric_results + p.supporting_metric_results:
        metrics.append({
            "metric_id": mr.metric_id,
            "metric_display_name": mr.metric_display_name,
            "tier": mr.tier.value,
            "value": float(mr.value) if mr.value is not None else None,
            "percentile": float(mr.percentile) if mr.percentile is not None else None,
            "percentile_scope": mr.percentile_scope,
            "level_tag": mr.level_tag,
            "threshold_applied": float(mr.threshold_applied) if mr.threshold_applied is not None else None,
            "passed_threshold": mr.passed_threshold,
        })

    return {
        "preset_id": p.preset_id,
        "preset_name": p.preset_name,
        "preset_category": p.preset_category,
        "metrics": metrics,
    }
```

**중요**: `wallet_background` 미포함.

### Step 4: `e3_builder.py`

기존 패턴 따름.

**주의**: 지표 수가 많을 수 있음 (Core 3~5 + Supporting 3~5 = 6~10개). 프롬프트가 길어짐.

### Step 5: `__init__.py`

---

## 4. 검증 지점

### 4-1. Wallet 배제

```python
input_data = build_e3_input(context)
assert "wallet_background" not in input_data
assert "wallet" not in str(input_data).lower() or "wallet" not in json.dumps(input_data).lower()
```

### 4-2. Core/Supporting만

```python
for m in input_data["metrics"]:
    assert m["tier"] in ["core", "supporting"], f"Context tier included: {m['metric_id']}"
```

### 4-3. 예시 코멘트 길이

각 예시의 `one_liner` 길이 50~250자 범위.

### 4-4. 토큰 예산

지표 10개 기준: **3,500~5,000 토큰** 예상.

---

## 5. 에이전트 판단 허용 범위

### 5-1. 허용
- 예시 선택, 지표별 해석 깊이 조정
- E1/E2와 중복되는 문구는 간결화

### 5-2. 금지
- Context tier 지표 포함
- Wallet 정보 주입
- one_liner 3문장 이상

---

## 6. 산출물

**신규 파일 (5개)**: `prompts/e3/*`

---

## 7. 완료 보고 포맷

```markdown
# D-4 완료 보고

## 생성 파일
- prompts/e3/*

## 검증
- [✓] Wallet 배제 확인
- [✓] Core/Supporting 제한

## 다음 세션
- D-5: E4 대화 Q&A (가장 복잡, Tier 1~3 모두 주입)
```

---

## 8. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판 |
