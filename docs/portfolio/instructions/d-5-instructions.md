# D-5 Instructions: E4 Conversation Q&A Prompt

> **세션**: D-5
> **목적**: LLM 진입점 E4 (사용자와의 대화 Q&A) 프롬프트 작성 — **가장 복잡**
> **전제 세션**: D-4 완료
> **대상 에이전트**: Claude Code
> **버전**: v1.0 (2026-04-20)

---

## 0. 에이전트가 먼저 읽을 것

**필수 참조**:
1. `docs/portfolio/design/coach-llm-design-v1.md` — §3-4 E4 상세, §4 전체 Tier 구조, §5 대화 기능 설계, §8 PV3
2. `docs/portfolio/implementation/schemas/llm_outputs.py` — `ConversationResponse` 스키마
3. `docs/portfolio/implementation/models.py` — `ChatSession`, `Message` 모델 (D-0a)
4. `docs/portfolio/implementation/schemas/analysis_context.py` — `AnalysisContext` 풀 스키마

**선택 참조**:
5. `docs/portfolio/design/return-tracking-design-v1.md` — §4-3 수익률 사용 규칙, §5-3 시간 차원 규칙

---

## 1. 목표

E4는 **유일하게 Tier 1~3 모두 주입되는 진입점**. 사용자 자연어 질문 → 맥락 있는 응답.

### 1-1. 진입점 특성

| 항목 | E4의 특징 |
|---|---|
| 트리거 | 사용자가 채팅 입력 |
| Tier 0 | 포함 (Tier 0 시스템 프롬프트) |
| Tier 1 | 포함 (최근 10~15턴 대화 이력) |
| Tier 2 | 포함 (세션 요약, 대화 길어지면) |
| Tier 2.5 | **전체 포함** (Wallet 정보 전체) |
| Tier 3 | 포함 (사용자 프로필, 있으면) |
| 출력 | `ConversationResponse` (자연어 + 조정 의도 감지) |

### 1-2. 산출물

```
implementation/prompts/e4/
├── __init__.py
├── instructions.py              (E4 지시문 — Q&A + 의도 분류)
├── examples.py                  (few-shot 3개, 다양한 질문 유형)
├── input_builder.py             (AnalysisContext 전체 직렬화)
├── tier1_builder.py             (ChatSession.messages → Tier 1 메시지 배열)
├── tier2_builder.py             (Tier 2 세션 요약 주입 조건)
├── tier3_builder.py             (UserProfile → Tier 3 블록)
└── e4_builder.py                (조립)
```

### 1-3. 출력 이원화

E4의 출력은 **자연어 응답 + 의도 감지 플래그**:
```json
{
  "response_text": "자연어 응답 (사용자가 볼 것)",
  "has_adjustment_intent": true|false,
  "adjustment_parse_hint": ""
}
```

`has_adjustment_intent=true`면 백엔드가 E5(조정 파싱)를 트리거.

---

## 2. 사전 조건

- [x] D-4 완료 (모든 진입점 공통 구조 확립)

---

## 3. 단계별 작업 명세

### Step 1: `instructions.py` — E4 지시문

**핵심 원칙**:
- Tier 1 대화 이력을 활용한 맥락 있는 응답
- Tier 3 프로필을 **톤 조정에만** 활용 (직접 인용 금지)
- Wallet vs Portfolio 엄격 구분 (PV3)
- 사용자 메시지에서 조정 의도 감지

**참고 템플릿**:
```python
E4_INSTRUCTIONS = """
# Task: Conversational Q&A (E4)

The user will send a message. You will respond based on:
- Tier 0: System rules (identity, terminology, style) — already in system prompt
- Tier 1: Recent conversation history — provided below as messages
- Tier 2: Session summary — provided if conversation is long
- Tier 2.5: Current analysis context (portfolio + wallet) — provided as JSON
- Tier 3: User profile — provided if available

## Output
Return valid JSON:
{
  "response_text": "<Natural Korean response to the user>",
  "has_adjustment_intent": <true|false>,
  "adjustment_parse_hint": "<empty string OR raw hint for E5 parsing>"
}

`response_text` is what the user sees. Keep natural conversational tone.

## Adjustment Intent Detection

Set `has_adjustment_intent = true` if the user is asking to change the analysis
(threshold, tier, stock exclusion, comparison group). Examples:
- "ROIC 기준을 20%로 올려서 다시 봐줘" → true
- "NVDA는 PEG 평가에서 빼줘" → true
- "섹터 대신 유니버스 기준으로 보여줘" → true

Set it to `false` for pure questions:
- "왜 INTC가 약점으로 나왔어?" → false
- "ROIC가 뭐야?" → false
- "내 포트폴리오 수익률이 어떻게 돼?" → false

When true, also:
- In `response_text`, acknowledge the intent briefly but do NOT apply yet.
  (E5 will parse, then a UI confirmation card will appear)
- In `adjustment_parse_hint`, put the user's raw message or a cleaned version
  for E5 to parse.

Example when true:
{
  "response_text": "ROIC 기준을 조정하시려는 것 같네요. 잠시만요, 조정 내용을 정리해드릴게요...",
  "has_adjustment_intent": true,
  "adjustment_parse_hint": "ROIC 기준을 20%로 상향, 성장 지표를 더 중시"
}

## Q&A Guidelines

### Use Tier 2.5 as primary source
- When user asks about numbers, percentiles, or specific metrics, reference
  the provided analysis_target_portfolio data.
- Do NOT invent or generalize from market knowledge.

### Wallet vs Portfolio (CRITICAL - PV3)
- When user says "내 포트폴리오" / "my portfolio" → refers to
  analysis_target_portfolio
- When user says "내 자산 지갑" / "전체 보유" → refers to wallet_all_holdings
- If ambiguous, assume analysis_target_portfolio (consultant metaphor)

### Wallet background use
- Reference `wallet_background.return_breakdown` only when:
  - User explicitly asks about wallet/total
  - Comparing portfolio vs wallet adds clarity
- Do NOT proactively discuss excluded holdings.

### Return breakdown time dimension (RV4-b)
- Default: use `.current` values
- When user asks "얼마나 달라졌어?", "이전 분석 대비" → use `at_save_time` and
  `delta_since_save`
- When mentioning numbers, clarify time point if saved-analysis is relevant.

### Tier 3 UserProfile use
- DO NOT quote the profile directly ("당신은 공격적 성향이시네요" - 금지)
- DO let it adjust tone:
  - aggressive → "리스크는 관리 가능한 수준" over "리스크에 주의하세요"
  - conservative → acknowledge risks more explicitly
- DO let it adjust focus:
  - preferred_presets에 GARP 있음 → GARP 맥락 설명 추가 OK

### Tier 1 history use
- If user references previous turn ("아까 말한 그 종목"), resolve from recent messages.
- If history contradicts current analysis, prefer current analysis (T2.5).

## Rules
- Korean honorific form default
- No buy/sell direct recommendations
- If user asks for recommendations, redirect: "구조적 관점에서 주목할 점은..."
- Conditional language for interpretations
"""
```

### Step 2: `examples.py` — Few-shot 예시 3개

**시나리오 다양성** (반드시 포함):

**예시 1** — 지표 질문 (has_adjustment_intent=false):
```python
EXAMPLE_1 = {
    "scenario": "사용자가 특정 지표의 약점 원인 질문",
    "user_message": "왜 INTC가 약점으로 나왔어?",
    "expected_output": {
        "response_text": "INTC는 Buffett 프리셋의 Core 지표인 ROIC 기준에서 업종 하위 35%에 위치하며, 5년 지속성도 통과율 40%에 그칩니다. Buffett 관점의 '꾸준한 자본수익'이라는 핵심 기준에서 벗어나 있어 약점으로 분류되었습니다. 다만 최근 1년 CAPEX 증가로 인한 일시적 효과일 수 있어, 향후 2~3분기 관찰이 필요할 수 있습니다.",
        "has_adjustment_intent": False,
        "adjustment_parse_hint": ""
    }
}
```

**예시 2** — 조정 요청 (has_adjustment_intent=true):
```python
EXAMPLE_2 = {
    "scenario": "사용자가 ROIC 임계값 상향 요청",
    "user_message": "나는 Buffett보다 좀 더 성장 요소를 보고 싶은데, ROIC 임계값을 20%로 올리고 성장 지표 가중치를 높여봐",
    "expected_output": {
        "response_text": "ROIC 기준을 더 높이고 성장 지표를 강조하시려는 거군요. 조정 내용을 정리해서 확인 카드로 보여드릴게요. 실행하시면 이번 분석에만 적용됩니다.",
        "has_adjustment_intent": True,
        "adjustment_parse_hint": "ROIC 임계값 15%에서 20%로 상향. 성장 지표 (revenue_growth_yoy, eps_growth_yoy) 가중치 상향"
    }
}
```

**예시 3** — 비교 기준 전환 요청 (has_adjustment_intent=true):
```python
EXAMPLE_3 = {
    "scenario": "비교군을 섹터에서 유니버스로 변경",
    "user_message": "섹터 말고 전체 유니버스 기준으로 봐줘",
    "expected_output": {
        "response_text": "비교 기준을 섹터에서 S&P 500 유니버스 전체로 전환하시려는 거네요. 확인 카드로 정리해드릴게요.",
        "has_adjustment_intent": True,
        "adjustment_parse_hint": "comparison_group을 industry/sector에서 universe로 변경"
    }
}
```

**예시 데이터 구조** (각 예시는 대화 이력 + 분석 맥락 포함):
```python
EXAMPLE_1_FULL = {
    "scenario": "...",
    "tier25_snippet": { ... analysis_target_portfolio / wallet_background 요약 ... },
    "tier1_snippet": [ ... 최근 대화 몇 턴 ... ],
    "user_message": "...",
    "expected_output": { ... }
}
```

### Step 3: `input_builder.py` — Tier 2.5 전체 주입

```python
def build_e4_input_tier25(context: AnalysisContext) -> dict:
    """
    E4는 Tier 2.5 전체 포함 (E1~E3와 달리 Wallet 포함).
    Pydantic의 .model_dump() 사용.
    """
    return context.model_dump(mode="json")
```

### Step 4: `tier1_builder.py` — 대화 이력

```python
from portfolio.models import ChatSession, Message


def build_tier1_messages(session: ChatSession, max_turns: int = 15) -> list[dict]:
    """
    최근 max_turns 턴을 messages 배열로 변환.
    Anthropic/OpenAI messages 포맷.
    """
    messages = session.messages.order_by("-created_at")[:max_turns]
    messages = list(reversed(messages))  # 시간 오름차순

    return [
        {"role": m.role, "content": m.content}
        for m in messages
    ]
```

### Step 5: `tier2_builder.py` — 세션 요약 주입 조건

```python
def build_tier2_summary(session: ChatSession) -> str | None:
    """
    대화 길이가 임계값 (예: 10턴) 넘으면 세션 요약 생성/반환.

    MVP: session.session_summary 필드가 채워져 있으면 반환, 아니면 None.
    요약 생성 자체는 별도 배치 (E8에 준하는 기능 Phase 2).
    """
    if session.session_summary:
        return session.session_summary
    return None
```

### Step 6: `tier3_builder.py` — UserProfile 블록

```python
from portfolio.schemas import UserProfile


def build_tier3_block(profile: UserProfile | None) -> str | None:
    """
    UserProfile을 프롬프트에 삽입 가능한 텍스트 블록으로.
    신규 사용자(profile=None 또는 empty)면 None 반환.
    """
    if profile is None or not profile.investment_style_summary:
        return None

    return f"""
## User Profile (Use for tone/focus adjustment only, do not quote directly):

- Investment style: {profile.investment_style_summary}
- Preferred presets: {', '.join(profile.preferred_presets)}
- Risk appetite: {profile.risk_appetite_indicator}
- Notable patterns: {', '.join(profile.decision_patterns[:3])}
- Sensitivities: {', '.join(profile.sensitivities[:3])}
"""
```

### Step 7: `e4_builder.py` — 조립 (복잡)

```python
from portfolio.prompts.tier0 import build_tier0
from .instructions import E4_INSTRUCTIONS
from .examples import FEW_SHOT_EXAMPLES
from .input_builder import build_e4_input_tier25
from .tier1_builder import build_tier1_messages
from .tier2_builder import build_tier2_summary
from .tier3_builder import build_tier3_block


def build_e4_prompt(
    context: AnalysisContext,
    session: ChatSession,
    user_profile: UserProfile | None,
    current_user_message: str,
    prompt_version: str = "1.1",
) -> dict:
    """
    Returns:
        {
            "system": <Tier 0 + Tier 3 + instructions>,
            "messages": [<Tier 1 message array> ... + current user message],
        }

    Structure designed for Anthropic messages API:
    - system: Tier 0 + static context (Tier 3, T2 summary, T2.5)
    - messages: Tier 1 conversation history (ends with current user message)
    """

    # === System portion (static context) ===
    system_parts = [build_tier0(prompt_version=prompt_version)]

    # Tier 3 (optional)
    tier3 = build_tier3_block(user_profile)
    if tier3:
        system_parts.append(tier3)

    # Tier 2 summary (optional)
    t2_summary = build_tier2_summary(session)
    if t2_summary:
        system_parts.append(f"## Previous session summary:\n{t2_summary}")

    # Tier 2.5 current analysis (always)
    t25 = build_e4_input_tier25(context)
    system_parts.append(
        f"## Current analysis context (Tier 2.5):\n"
        f"```json\n{json.dumps(t25, ensure_ascii=False, indent=2, default=str)}\n```"
    )

    # E4 task instructions
    system_parts.append(E4_INSTRUCTIONS)

    # Few-shot examples
    system_parts.append("## Examples\n")
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        system_parts.append(f"### Example {i}: {ex['scenario']}")
        system_parts.append(f"User: {ex['user_message']}")
        system_parts.append(f"Output: {json.dumps(ex['expected_output'], ensure_ascii=False)}")

    system = "\n\n".join(system_parts)

    # === Messages portion (Tier 1 + current) ===
    messages = build_tier1_messages(session, max_turns=15)
    messages.append({"role": "user", "content": current_user_message})

    return {
        "system": system,
        "messages": messages,
    }
```

### Step 8: `__init__.py`

---

## 4. 검증 지점

### 4-1. Tier 전체 조합 확인

```python
prompt = build_e4_prompt(context, session, profile, "test message")
assert "system" in prompt
assert "messages" in prompt
assert len(prompt["messages"]) >= 1
assert prompt["messages"][-1]["role"] == "user"
```

### 4-2. PV3 용어 존재

System에 `analysis_target_portfolio`, `wallet_all_holdings` 정의 블록 존재.

### 4-3. 신규 사용자 (profile=None) 처리

```python
prompt = build_e4_prompt(context, session, None, "hi")
# Tier 3 블록이 system에 없어야 함
assert "Investment style" not in prompt["system"]
```

### 4-4. 빈 세션 처리

대화 이력 0건인 경우 messages = [current_user_message 1개].

### 4-5. 토큰 예산

E4는 **가장 긴 프롬프트**. 예상 **8,000~12,000 토큰**.
```python
total_chars = len(prompt["system"]) + sum(len(m["content"]) for m in prompt["messages"])
assert total_chars < 50000, "E4 too long"
```

### 4-6. 조정 의도 감지 정확성

예시 3개에서 has_adjustment_intent 값이 시나리오와 일치.

---

## 5. 에이전트 판단 허용 범위

### 5-1. 허용
- 예시 시나리오 설계 (다양성만 유지)
- Tier 2 주입 조건 튜닝 (기본: session_summary 존재 시)
- Tier 3 포맷 세부

### 5-2. 금지
- Tier 2.5의 wallet_background 배제 (E4는 Wallet 포함이 원칙)
- Tier 3 직접 인용 허용
- has_adjustment_intent 기본값을 true로 설정

### 5-3. 판단 어려운 경우
- Tier 2 요약 생성 로직 필요 시 사용자 보고 (별도 세션에서 처리)
- 토큰 예산 초과 시 축약 전략 사용자 보고

---

## 6. 산출물

**신규 파일 (8개)**: `prompts/e4/*`

**예상 줄 수**: 500~800줄 (E4는 가장 큼)

---

## 7. 완료 보고 포맷

```markdown
# D-5 완료 보고

## 생성 파일 (8개)
- prompts/e4/*

## Tier 조립 구조
- System: Tier 0 + Tier 3 + Tier 2 summary + Tier 2.5 + instructions + examples
- Messages: Tier 1 history + current user message

## 크기
- System chars: N
- Messages chars: M
- Total tokens estimate: ~K

## Few-shot 예시
- 예시 1: [Q&A]
- 예시 2: [Adjustment intent]
- 예시 3: [Comparison change]

## 검증 결과
- [✓] PV3 용어 포함
- [✓] 신규 사용자 처리
- [✓] 빈 세션 처리
- [✓] 조정 의도 감지

## 판단 포인트

## 다음 세션 준비
- D-6: E5 조정 파싱 (has_adjustment_intent=true일 때 E4의 hint를 구조화 JSON으로)
```

---

## 8. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판 |
