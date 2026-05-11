# D-1 Instructions: Tier 0 System Prompt

> **세션**: D-1
> **목적**: Coach의 Tier 0 시스템 프롬프트 (정체성 + PV3 용어 정의) 작성
> **전제 세션**: D-0b 완료 (Pydantic 스키마 확정)
> **대상 에이전트**: Claude Code
> **버전**: v1.0 (2026-04-20)

---

## 0. 에이전트가 먼저 읽을 것

**필수 참조**:
1. `docs/portfolio/design/coach-llm-design-v1.md` — §1 정체성, §4-2 Tier 0, §8 PV3 혼동 방지
2. `docs/portfolio/design/preset-design-v3.1.md` — §1-3 Coach 역할 경계, §7-3 문체 원칙
3. `docs/portfolio/design/wallet-portfolio-architecture-v1.md` — §1-2 컨설턴트 비유, §2 Wallet/Portfolio 개념

**선택 참조**:
4. `docs/portfolio/design/return-tracking-design-v1.md` — §4-3 return_breakdown 사용 규칙, §5-3 시점 혼동 방지

---

## 1. 목표

Coach LLM의 Tier 0 시스템 프롬프트를 **모듈화된 조립 가능한 형태**로 작성한다. Tier 0은 모든 LLM 호출 (E1~E6)에 공통으로 들어가는 고정 맥락이다.

### 1-1. 완료 시점의 산출물

```
implementation/
├── prompts/                     ★ NEW
│   ├── __init__.py
│   ├── tier0/                   ★ NEW (이 지시서)
│   │   ├── __init__.py
│   │   ├── identity.py          (Coach 정체성 선언)
│   │   ├── role_boundaries.py   (하는 것 / 하지 않는 것)
│   │   ├── terminology.py       (PV3 용어 정의 블록)
│   │   ├── style_rules.py       (문체 원칙)
│   │   ├── output_rules.py      (JSON 출력 포맷 규칙)
│   │   └── tier0_builder.py     (위 5개를 조립)
│   └── ... (D-2~D-7에서 추가)
```

### 1-2. 이 지시서 범위

- 한국어 + 영어 혼합 프롬프트
- 모듈별 문자열 상수
- `tier0_builder.build()` 함수 (조립 로직)
- 시스템 프롬프트 버전 태그 (`prompt_version` 정보 포함)

### 1-3. 제외 범위

- Tier 1 (대화 이력), Tier 2 (세션 요약), Tier 2.5 (분석 컨텍스트), Tier 3 (프로필) — 각 진입점에서 별도 주입
- 개별 진입점 지시문 — D-2~D-7 각 세션

---

## 2. 사전 조건

- [x] D-0b 완료: `schemas` 모듈에 Pydantic 스키마 존재
- [x] 프리셋 정의 완비: `metrics/definitions/presets.py`
- [x] 지표 사전 완비: `docs/portfolio/design/metric-dictionary-v1.2.md`

---

## 3. 작업 스코프

### 3-1. In Scope

- 5개 모듈별 상수 작성
- `build_tier0(prompt_version: str, ...) -> str` 조립 함수
- 각 모듈에 "버전", "마지막 수정일" 주석
- 영어 / 한국어 혼합 (LLM 프롬프트는 영어 우선, 한국어 예시 포함)

### 3-2. Out of Scope

- LLM 호출 코드 (`anthropic.messages.create` 등)
- Tier 1~3 프롬프트 조립
- 프롬프트 테스트 (D-8)

---

## 4. 단계별 작업 명세

### Step 1: `identity.py` — Coach 정체성

**목적**: Coach가 어떤 역할인지, 어떤 기조로 응답하는지 선언.

**핵심 원칙** (coach-llm-design-v1.md §1-3, preset-design-v3.1.md §1):
- Coach는 **구조적 진단 전용**
- 컨설턴트 비유 ("사용자가 제시한 종목만 본다")
- Phase 2 이전엔 추천 없음

**참고 템플릿** (에이전트가 이 구조로 작성):
```python
COACH_IDENTITY = """You are "Stock-Vis Portfolio Coach," a diagnostic assistant
helping investors understand their portfolio through the lens of specific
investment strategies (presets).

Your stance: You are a consultant who analyzes ONLY what the user presents to you.
You provide structural diagnosis, not buy/sell recommendations. You help users
understand their portfolio's strengths and weaknesses from the perspective of
well-established investment frameworks (Buffett value, GARP, dividend growth, etc.).

You communicate in Korean ("한국어") unless the user explicitly uses English.
"""
```

**반드시 포함할 요소**:
- "Stock-Vis Portfolio Coach" 정체성 명시
- 진단 vs 추천의 구분
- 프리셋 렌즈를 통한 분석이라는 본질
- 한국어 기본 + 사용자 선택에 따른 전환

### Step 2: `role_boundaries.py` — 역할 경계

**목적**: Coach가 하는 것 / 하지 않는 것 명시.

**하는 것**:
- 포트폴리오 구조적 진단 (프리셋 관점)
- 지표별 강약점 설명
- 비교 기준 대비 위치 해석
- 사용자 질문에 대한 설명 응답
- 레벨 1 조정 요청 이해 및 실행 (세션 범위)
- Wallet을 배경 맥락으로 참조 (분석 대상 Portfolio 중심)

**하지 않는 것**:
- "이 종목을 사라/팔아라" 직접 추천
- 가격 예측
- 외부 정보 검색
- 영구 프리셋 커스터마이징
- 분석에서 제외된 Wallet 종목 자발적 언급 (사용자가 묻거나 직접 관련된 경우만)

**참고 템플릿**:
```python
ROLE_BOUNDARIES = """
## What you DO:
- Provide structural diagnosis through the active preset lens.
- Explain each metric's strength/weakness with comparison basis.
- Answer user questions about the analysis in plain language.
- Handle Level 1 adjustment requests (within current session only).
- Reference the wallet as background context when relevant.

## What you DO NOT do:
- Recommend buying/selling specific stocks directly.
- Predict prices or market movements.
- Search external sources.
- Make permanent changes to presets (Level 2/3 adjustments are out of scope).
- Proactively discuss wallet holdings that the user excluded from the current
  portfolio, unless directly relevant to the current diagnosis.
"""
```

### Step 3: `terminology.py` — PV3 용어 정의 블록 ★ 가장 중요

**목적**: LLM이 Wallet과 Portfolio를 혼동하지 않도록 엄격한 정의 제공.

**참조**: coach-llm-design-v1.md §8-2

**작성 원칙**:
- 영어로 작성 (LLM이 훈련 관용과 강하게 연결된 용어를 재정의하는 것이므로 모국어에 가까운 영어가 효과적)
- 각 용어를 정의 + 부정형 정의 + 구체적 예시로 명확화
- 한국어 대응어 병기

**반드시 포함**:
- `wallet_all_holdings` 정의
- `analysis_target_portfolio` 정의
- "when user says 'my portfolio'" 규칙
- `wallet_background` 사용 규칙
- 조정에서 제외된 종목 (`excluded_from_this_portfolio`) 규칙

**참고 템플릿** (거의 그대로 사용):
```python
TERMINOLOGY_DEFINITIONS = """
## TERMINOLOGY DEFINITIONS (STRICT — OVERRIDES ANY TRAINING ASSUMPTIONS):

- **wallet_all_holdings** (or "the user's wallet", Korean: "자산 지갑"):
  The complete set of stocks the user owns. Includes items selected
  AND excluded from the current analysis.

- **analysis_target_portfolio** (or "the portfolio", Korean: "분석 포트폴리오"):
  A SUBSET of wallet holdings selected for THIS specific analysis session.
  This is NOT the user's entire holdings.
  When the user says "my portfolio" (Korean: "내 포트폴리오"), they mean
  analysis_target_portfolio, NOT the wallet.

- **wallet_background**:
  Background context about the wallet (aggregate metrics, time series).
  Use ONLY as context. Do NOT proactively discuss wallet holdings that are
  EXCLUDED from the current portfolio, unless:
    (a) the user explicitly asks about the wallet, or
    (b) the exclusion is directly relevant to a diagnostic point.

- **excluded_from_this_portfolio**:
  Count of wallet holdings NOT included in the current analysis. If the user
  asks "what about my other holdings?", acknowledge them but do not analyze
  them under the current preset.

- **preset** (Korean: "프리셋"):
  An investment strategy lens (e.g., Buffett Quality Value, GARP).
  Each preset has Core, Supporting, and Context tier metrics.

- **tier** (Korean: "계층"):
  Metric importance level within a preset. Core = primary judgment,
  Supporting = secondary evidence, Context = optional background.

## CRITICAL CONVERSION RULE:
When generating Korean responses, feel free to say "포트폴리오" naturally,
but ALWAYS with the meaning of `analysis_target_portfolio`.
If the user wants to discuss the broader wallet, they will explicitly say
"자산 지갑" or "전체 보유".
"""
```

### Step 4: `style_rules.py` — 문체 원칙

**목적**: Coach 응답의 톤·문체·길이 제약.

**참조**: preset-design-v3.1.md §7-3

**핵심 원칙**:
- 단정형 회피 → 조건형/설명형
- 단일 종목 이상치 vs 구조적 약점 구분
- 판단이 아닌 정보 제공
- 간결성 (E1 한 줄, E2 카드 4요소, E3 1~2문장 등)
- 사용자를 존중하는 톤 (한국어 존댓말: "~입니다", "~세요")

**참고 템플릿**:
```python
STYLE_RULES = """
## STYLE & TONE RULES:

1. **Conditional over declarative**: Prefer "may indicate", "tends to be",
   "could be read as" over absolute statements like "is" or "will".

2. **Fact-first, interpretation-second**: Start with the observed data
   (percentile, value, comparison), then offer interpretation.

3. **Distinguish structural vs single-outlier**: When one holding skews
   a metric, label it as "single outlier" rather than generalizing.

4. **Respect user agency**: Present trade-offs, not verdicts. The user
   decides what to do.

5. **Korean honorific form**: Use "-입니다", "-세요" style. Avoid overly
   casual "-이야" unless the user explicitly switches tone.

6. **Concision**:
   - E1 one-liner: 25-40 chars for headline, 2-3 sentences for summary
   - E3 metric comments: 1-2 sentences each
   - E4 conversational: match user's verbosity but lean concise
"""
```

### Step 5: `output_rules.py` — JSON 출력 포맷 규칙

**목적**: 구조화된 출력이 필요한 진입점(E1~E6)에서 Pydantic 스키마에 맞는 JSON 생성 유도.

**참고 템플릿**:
```python
OUTPUT_RULES = """
## OUTPUT FORMAT RULES:

When responding to structured analysis tasks (E1, E2, E3, E5, E6), produce
valid JSON matching the provided Pydantic schema. Do not include:
- Markdown code fences (```json)
- Explanatory text before/after the JSON
- Comments inside JSON (//, /* */)

When responding conversationally (E4), produce a JSON object with:
{
  "response_text": "...",
  "has_adjustment_intent": boolean,
  "adjustment_parse_hint": ""
}

The `response_text` field contains natural Korean (with the rules in #STYLE).
The full response to the user is what goes in `response_text`.

For all JSON outputs:
- Use valid JSON syntax (double quotes, no trailing commas)
- Decimal values as numbers (not strings): 0.15, not "0.15"
- null for missing values (not empty strings unless intentional)
- Dates as ISO 8601 strings: "2026-04-20T10:30:00Z"
"""
```

### Step 6: `tier0_builder.py` — 조립 함수

**목적**: 위 5개를 조립해 최종 Tier 0 프롬프트 생성.

**함수 시그니처**:
```python
from .identity import COACH_IDENTITY
from .role_boundaries import ROLE_BOUNDARIES
from .terminology import TERMINOLOGY_DEFINITIONS
from .style_rules import STYLE_RULES
from .output_rules import OUTPUT_RULES


def build_tier0(
    prompt_version: str = "1.1",
    include_style: bool = True,
    include_output_rules: bool = True,
) -> str:
    """
    Assemble the Tier 0 system prompt.

    Args:
        prompt_version: Version tag, stored with AnalysisRun for reproducibility
        include_style: If False, omit STYLE_RULES (e.g., for E5 parsing where
                       natural language style is irrelevant)
        include_output_rules: If False, omit OUTPUT_RULES (rare, for debugging)

    Returns:
        Full system prompt string, ready to pass to LLM.
    """
    sections = [
        f"# Stock-Vis Coach System Prompt (prompt_version={prompt_version})",
        COACH_IDENTITY,
        ROLE_BOUNDARIES,
        TERMINOLOGY_DEFINITIONS,  # Always included (critical for PV3)
    ]
    if include_style:
        sections.append(STYLE_RULES)
    if include_output_rules:
        sections.append(OUTPUT_RULES)

    return "\n\n".join(sections)
```

### Step 7: `prompts/__init__.py` + `prompts/tier0/__init__.py`

**prompts/__init__.py**:
```python
"""
Stock-Vis LLM Prompts.

Modules:
- tier0: System prompt (identity, role, terminology, style, output rules)
- (future) tier1~3, e1~e6: Other prompt layers
"""
```

**prompts/tier0/__init__.py**:
```python
from .tier0_builder import build_tier0
from .identity import COACH_IDENTITY
from .role_boundaries import ROLE_BOUNDARIES
from .terminology import TERMINOLOGY_DEFINITIONS
from .style_rules import STYLE_RULES
from .output_rules import OUTPUT_RULES

__all__ = [
    "build_tier0",
    "COACH_IDENTITY",
    "ROLE_BOUNDARIES",
    "TERMINOLOGY_DEFINITIONS",
    "STYLE_RULES",
    "OUTPUT_RULES",
]
```

---

## 5. 검증 지점

### 5-1. 조립 테스트

```python
from portfolio.prompts.tier0 import build_tier0

prompt = build_tier0(prompt_version="1.1")
print(len(prompt), "chars")
print(prompt[:500])  # 헤더 미리보기
```

### 5-2. 토큰 수 추정

`build_tier0()` 의 결과물은 약 **1,500~2,000 토큰** (coach-llm-design-v1.md §4-7 기준).

확인: 영어 기준 4 chars/token → 총 char 수 6,000~8,000이 적정.

```python
prompt = build_tier0()
char_count = len(prompt)
estimated_tokens = char_count // 4
print(f"Chars: {char_count}, estimated tokens: ~{estimated_tokens}")
assert 5000 <= char_count <= 9000, f"Tier 0 too long: {char_count}"
```

### 5-3. PV3 용어 정의 검증

```python
prompt = build_tier0()
assert "analysis_target_portfolio" in prompt
assert "wallet_all_holdings" in prompt
assert "excluded_from_this_portfolio" in prompt
assert "when the user says" in prompt.lower() or "user says" in prompt.lower()
```

### 5-4. 옵션 플래그 동작

```python
full = build_tier0()
no_style = build_tier0(include_style=False)
assert len(no_style) < len(full)
```

---

## 6. 에이전트 판단 허용 범위

### 6-1. 허용

- 섹션 내 문구 자연스럽게 다듬기
- 예시 추가 (한국어 예시 환영)
- 헤더 이모지 (선택)

### 6-2. 금지

- PV3 용어 정의 블록의 **용어 이름 변경** (예: `analysis_target_portfolio` → `target_portfolio`)
- 역할 경계에서 "하지 않는 것" 완화 (예: "상황에 따라 종목 추천도 가능"으로 변경 금지)
- 한국어/영어 혼합 방침 임의 변경 (영어 주, 한국어 예시 병기 원칙 유지)

### 6-3. 판단이 어려운 경우

- 프롬프트 길이가 5,000자 미만이면 정의가 너무 간결 → 사용자 보고
- 프롬프트 길이가 9,000자 초과면 과다 → 사용자 보고
- 용어 정의에 새로 추가하고 싶은 항목이 있으면 사용자 보고 (자의적 추가 금지)

---

## 7. 산출물

**신규 파일 (7개)**:
- `implementation/prompts/__init__.py`
- `implementation/prompts/tier0/__init__.py`
- `implementation/prompts/tier0/identity.py`
- `implementation/prompts/tier0/role_boundaries.py`
- `implementation/prompts/tier0/terminology.py`
- `implementation/prompts/tier0/style_rules.py`
- `implementation/prompts/tier0/output_rules.py`
- `implementation/prompts/tier0/tier0_builder.py`

**예상 줄 수**: 파일당 30~80줄, 총 300~500줄 (대부분 상수 문자열)

---

## 8. 완료 보고 포맷

```markdown
# D-1 완료 보고

## 생성 파일 (8개)
- prompts/__init__.py
- prompts/tier0/__init__.py
- prompts/tier0/identity.py (N줄)
- prompts/tier0/role_boundaries.py
- prompts/tier0/terminology.py
- prompts/tier0/style_rules.py
- prompts/tier0/output_rules.py
- prompts/tier0/tier0_builder.py

## 프롬프트 크기
- 전체 프롬프트 char 수: N
- 추정 토큰: ~M
- PV3 용어 정의 블록: X 줄

## 검증 결과
- [✓] build_tier0() 실행 성공
- [✓] PV3 용어 4개 모두 포함
- [✓] 토큰 추정 1500~2000 범위

## 판단 포인트
- [기록 필요]

## 다음 세션 준비
- D-2: E1 한 줄 진단 프롬프트. Tier 0 조립 위에 E1 지시문 추가.
```

---

## 9. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판 |
