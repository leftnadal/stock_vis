# D-2 Instructions: E1 One-Line Diagnosis Prompt

> **세션**: D-2
> **목적**: LLM 진입점 E1 (한 줄 진단) 프롬프트 작성
> **전제 세션**: D-1 완료 (Tier 0 시스템 프롬프트 확정)
> **대상 에이전트**: Claude Code
> **버전**: v1.0 (2026-04-20)

---

## 0. 에이전트가 먼저 읽을 것

**필수 참조**:
1. `docs/portfolio/design/coach-llm-design-v1.md` — §3-1 E1 상세, §8-4 진입점별 Wallet 맥락 주입 정도
2. `docs/portfolio/implementation/schemas/llm_outputs.py` — `OneLineDiagnosis` 출력 스키마 (D-0b 결과)
3. `docs/portfolio/implementation/prompts/tier0/` — Tier 0 모듈 (D-1 결과)

**선택 참조**:
4. `docs/portfolio/design/preset-design-v3.1.md` — §7-3 문체 원칙

---

## 1. 목표

E1 진입점: 분석 완료 직후 생성되는 **한 줄 진단 + 2~3문장 요약**.

### 1-1. 산출물

```
implementation/prompts/
├── tier0/ (D-1)
└── e1/                          ★ NEW
    ├── __init__.py
    ├── instructions.py          (E1 지시문)
    ├── examples.py              (few-shot 예시 2~3개)
    ├── input_builder.py         (AnalysisContext → 간소화된 입력 JSON)
    └── e1_builder.py            (최종 프롬프트 조립)
```

### 1-2. 진입점 특성 (§3-1, §8-4)

- **트리거**: AnalysisRun 완료 직후 자동 호출
- **입력**: Tier 0 + 간소화된 AnalysisContext (Wallet 정보는 최소만)
- **출력**: `OneLineDiagnosis` (headline + summary)
- **Wallet 주입**: **최소** (total_holdings_count만)
- **Tier 1, 2, 3**: 불필요 (분석 직후라 대화 이력 없음, 사용자 프로필도 영향 미미)

---

## 2. 사전 조건

- [x] D-1 완료: `build_tier0()` 사용 가능
- [x] D-0b 완료: `OneLineDiagnosis` 스키마 존재
- [x] `AnalysisContext` Pydantic 모델 존재

---

## 3. 단계별 작업 명세

### Step 1: `instructions.py` — E1 지시문

**목적**: Tier 0 뒤에 붙을 E1 전용 지시.

**작성 원칙**:
- 영어 지시문 + 한국어 출력 요구
- headline 25~40자 제약 명시
- summary 2~3문장 제약 명시
- 프리셋 렌즈 일관성 강조

**참고 템플릿**:
```python
E1_INSTRUCTIONS = """
# Task: Generate One-Line Diagnosis (E1)

You will produce a concise diagnostic summary for the user's portfolio,
based on the analysis results provided below.

## Output
Return valid JSON matching this schema:
{
  "headline": "<25-40 character Korean diagnostic headline>",
  "summary": "<2-3 sentence Korean summary>"
}

## Content Guidelines

### headline (한 줄 진단)
- 25-40 Korean characters
- Capture the PRIMARY tension or feature of the portfolio through the
  active preset's lens
- Use "A하나 B하다" or "A이지만 B" pattern when trade-offs exist
- Examples:
  - "퀄리티는 견조하나 밸류에이션 부담"
  - "성장성 우수, 집중도 리스크 주의"
  - "배당 안정적, 성장 모멘텀 제한적"

### summary (2-3 sentence explanation)
- Expand the headline with ONE specific strength + ONE specific weakness
- Reference at least one concrete metric or comparison basis
- Tie back to the preset's philosophy
- Avoid buy/sell language

## Rules
- The preset lens is fixed. Do not suggest switching presets.
- Do not recommend specific actions.
- Base claims on provided data, not general market knowledge.
"""
```

### Step 2: `examples.py` — Few-shot 예시

**목적**: LLM이 출력 형식·톤을 정확히 파악하도록 2~3개 예시 제공.

**구조**:
```python
# 예시는 입력(간소화된 AnalysisContext) + 기대 출력 쌍

EXAMPLE_1_INPUT = """
{
  "analysis_target_portfolio": {
    "portfolio_name": "Tech 성장주",
    "preset_id": "garp",
    "preset_name": "GARP",
    "holding_count": 5,
    "strengths": [
      {"metric_id": "roic", "level_tag": "excellent", "reason_hint": "상위 8%"},
      {"metric_id": "eps_growth_yoy", "level_tag": "good", "reason_hint": "평균 22%"}
    ],
    "weaknesses": [
      {"metric_id": "peg_ratio", "level_tag": "weak", "reason_hint": "3종목 PEG 2.5+"},
      {"metric_id": "pe_ratio", "level_tag": "moderate", "reason_hint": "업종 대비 상단"}
    ]
  },
  "wallet_background": {
    "total_holdings_count": 12,
    "excluded_from_this_portfolio_count": 7
  }
}
"""

EXAMPLE_1_OUTPUT = """
{
  "headline": "성장성 견조하나 밸류에이션 부담",
  "summary": "GARP 관점에서 당신의 Tech 성장주 포트폴리오는 ROIC와 EPS 성장성이 업종 상위권에 있습니다. 다만 5개 종목 중 3개의 PEG가 2.5를 넘어, 성장 둔화 시 조정 리스크가 커질 수 있습니다."
}
"""

# 예시 2: 배당 프리셋 + 성장 둔화 케이스
EXAMPLE_2_INPUT = "..."
EXAMPLE_2_OUTPUT = "..."

# 예시 3 (선택): Concentrated Portfolio + 집중도 이슈
EXAMPLE_3_INPUT = "..."
EXAMPLE_3_OUTPUT = "..."


FEW_SHOT_EXAMPLES = [
    (EXAMPLE_1_INPUT, EXAMPLE_1_OUTPUT),
    (EXAMPLE_2_INPUT, EXAMPLE_2_OUTPUT),
    # EXAMPLE_3은 선택
]
```

**에이전트 작업**: 예시 2개는 반드시 작성. 세 번째는 선택.

**예시 작성 원칙**:
- 각 예시는 **다른 프리셋 카테고리** 사용 (value, growth, income 중 택)
- 각 예시의 headline은 트레이드오프 패턴을 다르게 표현
- 현실적 수치 (퍼센트, 개수) 사용

### Step 3: `input_builder.py` — AnalysisContext → 간소화 입력

**목적**: 풀 AnalysisContext에서 E1이 필요한 부분만 추출.

**함수 시그니처**:
```python
from portfolio.schemas import AnalysisContext


def build_e1_input(context: AnalysisContext) -> dict:
    """
    E1은 Wallet 정보 최소(§8-4) + Portfolio의 강약점/개요만 필요.

    Returns simplified dict for LLM input (serialized to JSON by caller).
    """
    p = context.analysis_target_portfolio
    w = context.wallet_background

    return {
        "analysis_target_portfolio": {
            "portfolio_name": p.portfolio_name,
            "preset_id": p.preset_id,
            "preset_name": p.preset_name,
            "preset_category": p.preset_category,
            "holding_count": p.holding_count,
            "strengths": [
                {
                    "metric_id": s.metric_id,
                    "metric_display_name": s.metric_display_name,
                    "level_tag": s.level_tag,
                    "reason_hint": s.reason_hint,
                }
                for s in p.strengths
            ],
            "weaknesses": [
                {
                    "metric_id": w_item.metric_id,
                    "metric_display_name": w_item.metric_display_name,
                    "level_tag": w_item.level_tag,
                    "reason_hint": w_item.reason_hint,
                }
                for w_item in p.weaknesses
            ],
            # 수익률 요약 (간단히 total만, breakdown은 미포함)
            "portfolio_return_total": float(p.return_breakdown.current.total_return),
        },
        "wallet_background": {
            "total_holdings_count": w.total_holdings_count,
            "excluded_from_this_portfolio_count": w.excluded_from_this_portfolio_count,
        },
    }
```

**중요**: E1은 토큰 효율이 중요하므로 **metric_results 전체, diagnostic_cards, holdings_summary 상세를 제외**.

### Step 4: `e1_builder.py` — 최종 프롬프트 조립

```python
from portfolio.prompts.tier0 import build_tier0
from .instructions import E1_INSTRUCTIONS
from .examples import FEW_SHOT_EXAMPLES
from .input_builder import build_e1_input
from portfolio.schemas import AnalysisContext
import json


def build_e1_prompt(
    context: AnalysisContext,
    prompt_version: str = "1.1",
) -> tuple[str, str]:
    """
    Build E1 prompt.

    Returns:
        (system_prompt, user_message)

    Usage:
        system, user = build_e1_prompt(context)
        response = anthropic_client.messages.create(
            model="claude-*",
            system=system,
            messages=[{"role": "user", "content": user}],
            ...
        )
    """
    # System: Tier 0 only (E1 is analysis-result-driven, no conversation)
    system_prompt = build_tier0(prompt_version=prompt_version)

    # User message: Task instructions + examples + actual input
    parts = [E1_INSTRUCTIONS]

    # Few-shot examples
    parts.append("## Examples\n")
    for i, (example_input, example_output) in enumerate(FEW_SHOT_EXAMPLES, 1):
        parts.append(f"### Example {i}\n")
        parts.append(f"Input:\n{example_input}\n")
        parts.append(f"Output:\n{example_output}\n")

    # Actual input
    input_data = build_e1_input(context)
    parts.append("## Now analyze this portfolio:\n")
    parts.append(f"Input:\n{json.dumps(input_data, ensure_ascii=False, indent=2, default=str)}\n")
    parts.append("Output:\n")

    user_message = "\n".join(parts)

    return system_prompt, user_message
```

### Step 5: `__init__.py`

```python
from .e1_builder import build_e1_prompt
from .input_builder import build_e1_input

__all__ = ["build_e1_prompt", "build_e1_input"]
```

---

## 4. 검증 지점

### 4-1. 조립 테스트

```python
from portfolio.prompts.e1 import build_e1_prompt
from portfolio.schemas import AnalysisContext

# Mock AnalysisContext 생성
context = AnalysisContext(...)  # 테스트용 최소 필드만 채움

system, user = build_e1_prompt(context)
print("System:", len(system), "chars")
print("User:", len(user), "chars")
print("Total tokens (est):", (len(system) + len(user)) // 4)
```

### 4-2. 토큰 예산 검증

E1 총 토큰: Tier 0 (~1,800) + 지시문 + 예시 2개 + 실제 입력 = **3,000~4,500** 토큰 예상.

```python
assert (len(system) + len(user)) < 20000, "E1 prompt too long"
```

### 4-3. PV3 필드명 존재 확인

```python
input_data = build_e1_input(context)
assert "analysis_target_portfolio" in input_data
assert "wallet_background" in input_data
```

### 4-4. 예시 JSON 유효성

```python
import json
for inp, out in FEW_SHOT_EXAMPLES:
    json.loads(inp)
    json.loads(out)  # 둘 다 valid JSON
```

---

## 5. 에이전트 판단 허용 범위

### 5-1. 허용
- 예시 내용 선택 (프리셋, 구체 수치 등)
- input_builder의 세부 필드 구조 조정 (PV3 필드명은 유지)
- 지시문 문구 개선

### 5-2. 금지
- Wallet 정보 추가 주입 (최소 원칙 위반) — §8-4에 따라 total_holdings_count와 excluded count 외 추가 금지
- headline/summary 제약 완화
- few-shot 개수 0으로 축소

### 5-3. 판단이 어려운 경우
- 예시의 preset 조합이 어색하면 사용자 보고
- 수치 현실성 의심되면 사용자 보고

---

## 6. 산출물

**신규 파일 (5개)**:
- `prompts/e1/__init__.py`
- `prompts/e1/instructions.py`
- `prompts/e1/examples.py`
- `prompts/e1/input_builder.py`
- `prompts/e1/e1_builder.py`

**예상 줄 수**: 총 200~400줄

---

## 7. 완료 보고 포맷

```markdown
# D-2 완료 보고

## 생성 파일 (5개)
- prompts/e1/*

## 프롬프트 크기 (예상)
- System (Tier 0): N chars
- User (E1 full): M chars
- Total tokens estimate: ~K

## Few-shot 예시
- 예시 1: [preset] - [scenario]
- 예시 2: [preset] - [scenario]

## 검증 결과
- [✓] 조립 테스트 통과
- [✓] PV3 필드명 유지
- [✓] 예시 JSON 유효

## 판단 포인트
- [기록]

## 다음 세션 준비
- D-3: E2 진단 카드 프롬프트 (4요소 JSON, 복잡도 높음)
```

---

## 8. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판 |
