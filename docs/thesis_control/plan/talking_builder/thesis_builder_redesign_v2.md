# THESIS_CONTROL 가설 빌더 재설계 — 상세 설계 계획서 v2

> 작성일: 2026-03-19
> 개정: v2 — 1인 개발 현실 기준 재설계
> 상태: 설계 확정 → 구현 대기
> 선행 조건: Phase 3 대시보드 PR (FE-PR-7~11) 완료 후 착수

---

## 1. 설계 철학

### 핵심 전환 (유지)

```
AS-IS: "AI가 묻고, 사용자가 답한다" (위자드형)
TO-BE: "사용자가 의견을 던지고, AI가 설계하고, 사용자가 승인한다" (제안형)
```

### 원칙

| 원칙                   | 설명                                              |
| ---------------------- | ------------------------------------------------- |
| One-shot Proposal      | 사용자 한 줄 입력 → AI가 가설 전체를 한 번에 제안 |
| Explainable Auto-setup | 자동 설정된 모든 항목에 "왜" 한 줄 이유 노출      |
| Graceful Fallback      | LLM 실패 시 기존 위자드로 자동 전환               |
| Effortless Flow        | 사용하면서 투자 분석 프레임을 자연스럽게 학습     |

### v2 추가 원칙 — 1인 개발 생존 규칙

| 원칙                    | 설명                                                      |
| ----------------------- | --------------------------------------------------------- |
| Smallest Shippable Unit | Phase A-MVP는 2-3일 내 배포 가능한 범위로 제한            |
| Feature Flag First      | 모든 맥락 소스와 고급 기능은 플래그 뒤에 격리             |
| Validate Before Trust   | LLM 출력은 항상 normalize → validate → merge 3단계를 거침 |
| State Simplicity        | ConversationState는 typed model, 명시적 상태 전이         |
| Observable by Default   | 핵심 이벤트는 초기부터 로그, 나중에 분석                  |

---

## 2. MVP 범위 정의

### 포함 (Phase A-MVP)

- LLM one-shot proposal (Gemini 1회 호출)
- Indicator DB context 주입 (PK 포함)
- 프리셋 선택 (단기/중기/장기)
- confirm → Thesis/Premise/Indicator 저장
- wizard fallback (LLM 실패 시)
- LLM 응답 normalize/validate 레이어
- 최소 이벤트 로깅
- feature flag 기반 on/off

### 제외 (feature flag OFF / 후속 Phase)

| 항목                        | 제외 이유                   | 목표 Phase |
| --------------------------- | --------------------------- | ---------- |
| Chain Sight Neo4j 맥락      | 데이터 종속, 별도 검증 필요 | Phase B    |
| EOD Screening 맥락          | 성능 검증 필요              | Phase B    |
| News Pipeline 맥락          | 파이프라인 안정화 후        | Phase B    |
| 멀티턴 수정 대화            | state 복잡도 급증           | Phase B    |
| Target 변경 (수정 중)       | 상태 초기화 로직 복잡       | Phase B    |
| MiniDashboardPreview 고도화 | 대시보드 PR 완료 후         | Phase C    |
| 스트리밍 응답 (SSE)         | 체감 개선 대비 공수 큼      | Phase C    |
| Guided Suggestion 템플릿    | 사용자 패턴 축적 후         | Phase C    |
| 과거 가설 패턴 맥락         | 데이터 축적 필요            | Phase C    |

---

## 3. 전체 아키텍처

### 요청 흐름도

```
사용자 입력: "삼성전자 2분기에 반등할 것 같아요"
                    │
                    ▼
            ┌─── views.py ───┐
            │  mode 분기       │
            │  llm / wizard    │
            └───────┬──────────┘
                    │ mode='llm'
                    ▼
           맥락 수집 (feature flag 제어)
           ┌───────────────────────┐
           │ [ON]  Indicator DB    │ ← MVP
           │ [OFF] Chain Sight     │ ← Phase B
           │ [OFF] EOD Signals     │ ← Phase B
           │ [OFF] News Pipeline   │ ← Phase B
           └───────────┬───────────┘
                       ▼
              Prompt Builder (모듈화)
              build_base() + build_type_guide()
              + build_indicator_block()
                       │
                       ▼
              Gemini 2.5 Flash 호출
              (Structured Output → JSON)
                       │
                       ▼
           ┌─── LLM 응답 후처리 ───┐
           │  1. normalize          │ ← v2 신규
           │  2. validate           │ ← v2 신규
           │  3. merge to state     │
           │  4. indicator match    │
           └───────────┬───────────┘
                       ▼
              프론트엔드 응답 반환
```

### 턴(Turn) 구조 — MVP 기본 경로

```
[Turn 1] 사용자 자유 입력
         → Indicator DB 맥락 + Gemini One-shot
         → normalize → validate → merge
         → 가설 초안 + 지표 + why
         → Gemini 호출: 1회

[Turn 2] 사용자 프리셋 선택 (단기/중기/장기)
         → 서버 직접 매핑 (Gemini 호출 없음)
         → 확인 메시지

[Turn 3] 사용자 "이대로 등록해요"
         → validate collected → _create_thesis_from_llm()
         → DB 저장 + 초기 스냅샷
         → Gemini 호출: 0회

총 Gemini 호출: 1회
```

---

## 4. 백엔드 상세 설계

### 4-1. ConversationState — Typed Model 기반

stateless 에코 패턴은 유지하되, dict 대신 Pydantic model로 타입 안전성을 확보한다.
프론트엔드와 주고받을 때는 `.model_dump()` / `model_validate()`로 직렬화.

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class BuilderMode(str, Enum):
    LLM = 'llm'
    WIZARD = 'wizard'


class BuilderPhase(str, Enum):
    """명시적 상태 전이 — 현재 빌더가 어느 단계인지"""
    PROPOSAL = 'proposal'       # Turn 1: one-shot 제안 대기/완료
    PRESET = 'preset'           # Turn 2: 프리셋 선택 대기
    CONFIRM = 'confirm'         # Turn 3: 최종 확인 대기
    COMPLETE = 'complete'       # 등록 완료
    FALLBACK = 'fallback'       # wizard 모드로 전환됨


class PremiseData(BaseModel):
    title: str
    description: str = ''
    recommended_indicators: list[dict] = Field(default_factory=list)


class CollectedData(BaseModel):
    direction: Optional[str] = None       # bullish / bearish / neutral
    target: Optional[str] = None
    target_type: Optional[str] = None     # stock / etf / index / sector
    thesis_type: list[str] = Field(default_factory=list)  # ['earnings', 'chain']
    premises: list[PremiseData] = Field(default_factory=list)
    timeframe: Optional[str] = None
    magnitude: Optional[str] = None
    sensitivity: Optional[str] = None


class ConversationState(BaseModel):
    conv_id: str
    entry_source: str = 'free_input'
    mode: BuilderMode = BuilderMode.LLM
    phase: BuilderPhase = BuilderPhase.PROPOSAL
    history: list[dict] = Field(default_factory=list)  # [{role, content}]
    collected: CollectedData = Field(default_factory=CollectedData)
    turn_count: int = 0
    source_news_id: Optional[str] = None

    class Config:
        use_enum_values = True
```

**상태 전이 규칙 (State Machine)**

```
PROPOSAL → PRESET      (one-shot 성공, confidence != low)
PROPOSAL → PROPOSAL    (confidence: low → 질문 모드, 재시도)
PROPOSAL → FALLBACK    (Gemini 실패)
PRESET   → CONFIRM     (프리셋 선택 완료)
CONFIRM  → COMPLETE    (사용자 확인, DB 저장)
CONFIRM  → PROPOSAL    (MVP 범위: "다시 만들어줘" → 초기화 후 재시작)
FALLBACK → (기존 wizard 로직)

MVP에서 금지되는 전이:
CONFIRM → PRESET (프리셋 재선택 → MVP에서 미지원, "다시 만들어줘"로 대체)
```

### 4-2. thesis_type 표현

```python
# 내부 저장: list[str]
thesis_type: list[str] = ['earnings', 'chain']

# DB 저장 (MVP): JSON 문자열 → 향후 ArrayField 전환 용이
# Django model:
thesis_type_json = models.JSONField(default=list)

# 외부 표시용:
def render_thesis_type(types: list[str]) -> str:
    labels = {
        'earnings': '실적/펀더멘털',
        'flow': '수급/모멘텀',
        'macro': '매크로/정책',
        'chain': '산업체인',
        'event': '이벤트',
    }
    return ' + '.join(labels.get(t, t) for t in types)
    # "실적/펀더멘털 + 산업체인"

# 유효성 검증:
VALID_THESIS_TYPES = {'earnings', 'flow', 'macro', 'chain', 'event'}
```

### 4-3. Prompt Builder — 모듈화

```python
# thesis/services/prompt_builder.py

def build_system_prompt(
    state: ConversationState,
    feature_flags: dict,
) -> str:
    """모듈화된 프롬프트 빌더. feature flag에 따라 블록 조합."""

    blocks = [
        build_base_instruction(),       # 항상 포함
        build_type_guide_block(),        # 항상 포함
    ]

    if feature_flags.get('INDICATOR_CONTEXT_ENABLED'):
        blocks.append(build_indicator_block())

    if feature_flags.get('CHAIN_CONTEXT_ENABLED'):
        chain_ctx = get_chain_sight_context(state.collected.target)
        if chain_ctx:
            blocks.append(build_chain_block(chain_ctx))

    if feature_flags.get('EOD_CONTEXT_ENABLED'):
        eod_ctx = get_eod_signals(state.collected.target)
        if eod_ctx:
            blocks.append(build_eod_block(eod_ctx))

    if feature_flags.get('NEWS_CONTEXT_ENABLED'):
        news_ctx = get_recent_news(state.collected.target)
        if news_ctx:
            blocks.append(build_news_block(news_ctx))

    return "\n\n".join(blocks)
```

**각 블록 함수 (MVP에서 사용하는 것만 구현)**

```python
def build_base_instruction() -> str:
    return """당신은 한국 개인투자자가 투자 가설을 세울 수 있도록 돕는 전문 어시스턴트입니다.

## 역할
사용자의 짧은 의견을 받아서, 완성된 투자 가설 초안을 즉시 제안합니다.
질문을 하나씩 던지지 마세요. 첫 턴에서 완전한 구조를 만들어 제안하세요.

## 출력 규칙
1. 가설 전체를 제안 (direction, target, premises, thesis_type).
2. 모호해도 맥락을 추론하여 대상 자산까지 특정.
3. premises 2~4개, 각 premise에 추천 지표 + why 한 줄.
4. 한국어, 친근한 존댓말.
5. 불확실하면 선택지로 제시.
6. 맥락 버튼 3-4개."""


def build_type_guide_block() -> str:
    return """## 가설 타입 분류
입력을 분석하여 적합한 타입을 판단하세요. 복합 가능 (예: ["earnings", "chain"]).

**earnings** — 실적, 마진, 수주, 가이던스
**flow** — 외국인 매수, 공매도, 거래량
**macro** — 금리, 환율, CPI, 정책
**chain** — 공급망 파급, capex, 출하량
**event** — FDA 승인, 실적발표, 신제품"""


def build_indicator_block() -> str:
    """DB에서 활성 지표 목록을 카테고리별 + PK 포함으로 생성"""
    indicators = Indicator.objects.filter(
        is_active=True
    ).values('id', 'name', 'category').order_by('category', 'name')

    by_cat = defaultdict(list)
    for ind in indicators:
        by_cat[ind['category']].append(f"{ind['name']}(id:{ind['id']})")

    lines = [f"- {cat}: {', '.join(names)}" for cat, names in by_cat.items()]

    return f"""## 추천 가능 지표 목록 (이 목록 우선 추천)
{chr(10).join(lines)}

지표 추천 시:
- 목록에 있으면 indicator_db_id에 id 숫자 포함.
- 목록에 없으면 indicator_db_id: null."""
```

### 4-4. Gemini Structured Output 스키마

```python
GEMINI_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "buttons": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                },
                "required": ["id", "label"],
            },
        },
        "collected_update": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
                "target": {"type": "string"},
                "target_type": {"type": "string", "enum": ["stock", "etf", "index", "sector"]},
                "thesis_type": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["earnings", "flow", "macro", "chain", "event"]},
                },
                "premises": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "recommended_indicators": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "indicator_db_id": {"type": "integer", "nullable": True},
                                        "why": {"type": "string"},
                                        "signal_type": {"type": "string", "enum": ["leading", "coincident", "lagging"]},
                                    },
                                    "required": ["name", "why"],
                                },
                            },
                        },
                        "required": ["title", "recommended_indicators"],
                    },
                },
            },
        },
        "is_complete": {"type": "boolean"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "selection_mode": {"type": "string", "enum": ["single", "multi"]},
    },
    "required": ["message", "buttons", "is_complete", "confidence"],
}
```

### 4-5. LLM 응답 후처리 — Normalize / Validate / Merge

LLM 출력을 곧바로 신뢰하지 않는다. 반드시 3단계를 거친다.

```python
# thesis/services/llm_postprocess.py

from dataclasses import dataclass


@dataclass
class PostProcessResult:
    """후처리 결과"""
    collected_update: dict         # 정규화된 업데이트
    warnings: list[str]            # 비치명적 문제 (로그용)
    errors: list[str]              # 치명적 문제 (fallback 트리거)
    indicator_matches: list[dict]  # 매칭된 지표 목록


# ─── Step 1: Normalize ───

def normalize_llm_output(raw: dict) -> dict:
    """
    LLM 출력의 흔들림을 잡는다.
    - direction 소문자 통일
    - thesis_type: 문자열이면 리스트로 변환, "earnings+chain" → ["earnings", "chain"]
    - target_type enum 정규화
    - premise title 앞뒤 공백 제거 + 중복 제거
    - indicator name 앞뒤 공백 제거
    """
    update = raw.get('collected_update', {})
    if not update:
        return raw

    # direction 정규화
    if d := update.get('direction'):
        update['direction'] = d.strip().lower()

    # thesis_type: 문자열 → 리스트
    tt = update.get('thesis_type', [])
    if isinstance(tt, str):
        tt = [t.strip() for t in tt.replace('+', ',').split(',')]
    update['thesis_type'] = [t for t in tt if t in VALID_THESIS_TYPES]

    # target_type 정규화
    VALID_TARGET_TYPES = {'stock', 'etf', 'index', 'sector', 'commodity', 'crypto'}
    if tt := update.get('target_type'):
        update['target_type'] = tt.strip().lower() if tt.strip().lower() in VALID_TARGET_TYPES else 'stock'

    # premises 정규화
    seen_titles = set()
    clean_premises = []
    for p in update.get('premises', []):
        title = p.get('title', '').strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        # indicator name 정규화
        for ind in p.get('recommended_indicators', []):
            ind['name'] = ind.get('name', '').strip()
            ind['why'] = ind.get('why', '').strip()
        p['title'] = title
        clean_premises.append(p)
    update['premises'] = clean_premises

    raw['collected_update'] = update
    return raw


# ─── Step 2: Validate ───

def validate_llm_output(normalized: dict) -> tuple[dict, list[str], list[str]]:
    """
    정규화된 출력의 논리적 정합성을 검증.
    returns: (validated_output, warnings, errors)
    """
    warnings = []
    errors = []
    update = normalized.get('collected_update', {})

    # direction 필수
    if not update.get('direction'):
        errors.append('direction missing')

    # target 필수
    if not update.get('target'):
        errors.append('target missing')

    # premises 최소 1개
    premises = update.get('premises', [])
    if len(premises) == 0:
        errors.append('no premises')

    # premises 최대 5개 (초과 시 자름)
    if len(premises) > 5:
        warnings.append(f'premises truncated: {len(premises)} → 5')
        update['premises'] = premises[:5]

    # 각 premise에 indicator 최소 1개 권장
    for p in update.get('premises', []):
        if not p.get('recommended_indicators'):
            warnings.append(f'premise "{p.get("title")}" has no indicators')

    # indicator_db_id 검증: id가 있는데 DB에 없으면 null로 교정
    for p in update.get('premises', []):
        for ind in p.get('recommended_indicators', []):
            db_id = ind.get('indicator_db_id')
            if db_id is not None:
                if not Indicator.objects.filter(id=db_id, is_active=True).exists():
                    warnings.append(f'indicator_db_id={db_id} not in DB, set to null')
                    ind['indicator_db_id'] = None

    # direction과 message 내용 불일치 감지 (간단한 휴리스틱)
    direction = update.get('direction', '')
    message = normalized.get('message', '')
    if direction == 'bullish' and any(kw in message for kw in ['하락', '약세', '리스크']):
        warnings.append('direction=bullish but message contains bearish keywords')
    if direction == 'bearish' and any(kw in message for kw in ['상승', '반등', '수혜']):
        warnings.append('direction=bearish but message contains bullish keywords')

    normalized['collected_update'] = update
    return normalized, warnings, errors


# ─── Step 3: Merge ───

def merge_to_collected(
    current: CollectedData,
    update: dict,
) -> CollectedData:
    """
    검증된 update를 현재 collected에 병합.
    MVP에서는 전체 교체 방식 (patch가 아님).
    Phase B에서 patch 방식으로 전환.
    """
    if d := update.get('direction'):
        current.direction = d
    if t := update.get('target'):
        current.target = t
    if tt := update.get('target_type'):
        current.target_type = tt
    if types := update.get('thesis_type'):
        current.thesis_type = types
    if premises := update.get('premises'):
        current.premises = [PremiseData(**p) for p in premises]
    return current
```

### 4-6. 핵심 엔진 — process_llm_turn()

```python
# thesis/services/thesis_builder.py

def process_llm_turn(
    state: ConversationState,
    user_input: str,
    user=None,
    feature_flags: dict = None,
) -> dict:
    """MVP 핵심 엔진. phase 기반 상태 전이."""

    flags = feature_flags or get_feature_flags()
    state.history.append({'role': 'user', 'content': user_input})
    state.turn_count += 1

    # ─── Phase 기반 분기 ───

    if state.phase == BuilderPhase.PRESET:
        preset_key = detect_preset(user_input)
        if preset_key:
            return handle_preset(state, preset_key)
        # 프리셋이 아닌 입력 → 질문으로 해석, 재안내
        return reprompt_preset(state)

    if state.phase == BuilderPhase.CONFIRM:
        if is_confirm_intent(user_input):
            return handle_confirm(state, user)
        # "다시 만들어줘" 등 → 초기화 후 재시작
        if is_restart_intent(user_input):
            state.phase = BuilderPhase.PROPOSAL
            state.collected = CollectedData()
            # 아래 PROPOSAL 로직으로 fall through

    if state.phase == BuilderPhase.PROPOSAL:
        return handle_proposal(state, user_input, flags)

    # FALLBACK, COMPLETE → 여기 도달하면 안 됨
    return error_response(state, "unexpected phase")


def handle_proposal(state, user_input, flags) -> dict:
    """One-shot proposal 생성"""

    # 1. 프롬프트 구성
    system_prompt = build_system_prompt(state, flags)

    # 2. Gemini 호출
    raw_response = call_gemini(system_prompt, state.history)
    if raw_response is None:
        return fallback_to_wizard(state, user_input)

    # 3. 후처리: normalize → validate → merge
    normalized = normalize_llm_output(raw_response)
    validated, warnings, errors = validate_llm_output(normalized)

    # 로그 (observability)
    log_event('proposal_generated', {
        'conv_id': state.conv_id,
        'confidence': validated.get('confidence'),
        'warnings': warnings,
        'errors': errors,
        'premise_count': len(validated.get('collected_update', {}).get('premises', [])),
    })

    # 치명적 에러 → fallback
    if errors:
        log_event('llm_parse_failed', {'conv_id': state.conv_id, 'errors': errors})
        return fallback_to_wizard(state, user_input)

    # 4. collected 병합
    update = validated.get('collected_update', {})
    state.collected = merge_to_collected(state.collected, update)

    # 5. 지표 매칭
    indicator_results = match_indicators(state.collected)

    # 6. 히스토리 추가
    state.history.append({'role': 'assistant', 'content': validated['message']})

    # 7. 상태 전이
    confidence = validated.get('confidence', 'medium')
    if confidence == 'low':
        state.phase = BuilderPhase.PROPOSAL   # 질문 모드 유지
    else:
        state.phase = BuilderPhase.PRESET     # 프리셋 선택으로 전이

    return {
        'message': validated['message'],
        'buttons': validated.get('buttons', []),
        'selection_mode': validated.get('selection_mode', 'single'),
        'conversation_state': state.model_dump(),
        'turn_count': state.turn_count,
        'is_complete': False,
        'confidence': confidence,
        'indicator_recommendations': indicator_results,
        'needs_preset': state.phase == BuilderPhase.PRESET,
    }
```

### 4-7. 지표 매칭 — PK 우선 2단계

```python
def match_indicators(collected: CollectedData) -> list[dict]:
    """PK 직접 매칭 → 문자열 fallback 2단계"""
    results = []
    for premise in collected.premises:
        for ind in premise.recommended_indicators:
            matched_indicator = None
            method = 'unmatched'

            # 1순위: PK
            db_id = ind.get('indicator_db_id')
            if db_id:
                try:
                    matched_indicator = Indicator.objects.get(id=db_id, is_active=True)
                    method = 'pk_direct'
                except Indicator.DoesNotExist:
                    pass

            # 2순위: 문자열
            if not matched_indicator:
                matched_indicator = match_indicators_for_premise(
                    premise_text=premise.title,
                    indicator_hint=ind.get('name', ''),
                    target=collected.target,
                )
                if matched_indicator:
                    method = 'name_similarity'

            results.append({
                'premise_title': premise.title,
                'indicator': {'id': matched_indicator.id, 'name': matched_indicator.name} if matched_indicator else None,
                'indicator_name': ind.get('name'),
                'why': ind.get('why', ''),
                'signal_type': ind.get('signal_type', 'coincident'),
                'auto_matched': matched_indicator is not None,
                'match_method': method,
            })
    return results
```

### 4-8. 프리셋 / 확인 / Fallback

```python
MONITORING_PRESETS = {
    'short':  {'label': '⚡ 단기 트레이딩', 'timeframe': 'short',  'magnitude': 'moderate', 'sensitivity': 'high'},
    'medium': {'label': '📈 중기 투자',     'timeframe': 'medium', 'magnitude': 'moderate', 'sensitivity': 'medium'},
    'long':   {'label': '🔭 장기 전망',     'timeframe': 'long',   'magnitude': 'severe',   'sensitivity': 'low'},
}


def handle_preset(state, preset_key):
    preset = MONITORING_PRESETS[preset_key]
    state.collected.timeframe = preset['timeframe']
    state.collected.magnitude = preset['magnitude']
    state.collected.sensitivity = preset['sensitivity']
    state.phase = BuilderPhase.CONFIRM

    log_event('preset_selected', {'conv_id': state.conv_id, 'preset': preset_key})

    return {
        'message': build_confirm_message(state.collected, preset),
        'buttons': [
            {'id': 'confirm', 'label': '이대로 등록해요'},
            {'id': 'restart', 'label': '다시 만들어줘'},
        ],
        'conversation_state': state.model_dump(),
        'phase': 'confirm',
    }


def handle_confirm(state, user):
    validation = validate_collected_for_save(state.collected)
    if not validation['is_valid']:
        return ask_missing_fields(state, validation['missing'])

    result = create_thesis_from_llm(state.collected, user)
    state.phase = BuilderPhase.COMPLETE

    log_event('thesis_created', {
        'conv_id': state.conv_id,
        'thesis_id': result['thesis_id'],
        'premise_count': result['premise_count'],
        'indicator_count': result['indicator_count'],
    })

    return {
        'message': '가설이 등록되었습니다!',
        'buttons': [
            {'id': 'view_dashboard', 'label': '대시보드에서 보기'},
            {'id': 'create_another', 'label': '새 가설 만들기'},
        ],
        'conversation_state': state.model_dump(),
        'is_complete': True,
        'created_thesis': result,
    }


def fallback_to_wizard(state, user_input):
    state.mode = BuilderMode.WIZARD
    state.phase = BuilderPhase.FALLBACK
    log_event('fallback_triggered', {'conv_id': state.conv_id})
    return {
        'message': 'AI 대화 기능에 일시적 문제가 있어요. 단계별 방식으로 진행해도 괜찮으시겠어요?',
        'buttons': [
            {'id': 'wizard_continue', 'label': '단계별로 진행'},
            {'id': 'retry', 'label': '다시 시도'},
        ],
        'conversation_state': state.model_dump(),
    }
```

### 4-9. Edit Flow 범위 제한 (MVP)

MVP에서 수정 가능/불가 범위를 명시적으로 정의한다.

| 항목                | MVP                                       | Phase B                 |
| ------------------- | ----------------------------------------- | ----------------------- |
| premise 문구 수정   | ❌ ("다시 만들어줘"로 대체)               | ✅ 멀티턴 수정          |
| indicator 추가/제거 | ❌ (등록 후 대시보드에서)                 | ✅ 대화 중 수정         |
| preset 변경         | ✅ (CONFIRM → "다시 만들어줘" → PROPOSAL) | ✅                      |
| target 변경         | ❌ (재시작만 허용)                        | ✅ 상태 초기화 + 재추론 |
| direction 변경      | ❌ (재시작만 허용)                        | ✅                      |
| thesis_type 변경    | ❌                                        | ✅                      |

**설계 근거**: MVP에서 "수정"은 "재시작"으로 대체한다. 이유는 partial edit의 상태 관리 복잡도가 전체 기능의 50% 이상을 차지하기 때문이다. "다시 만들어줘" 한 마디로 PROPOSAL 초기화하는 것이 훨씬 단순하고 에러 가능성이 낮다.

### 4-10. views.py

```python
@api_view(['POST'])
def builder_start(request):
    state = ConversationState(
        conv_id=str(uuid.uuid4()),
        entry_source=request.data.get('entry_source', 'free_input'),
        source_news_id=request.data.get('source_news_id'),
    )
    log_event('builder_started', {'conv_id': state.conv_id})
    return Response(
        process_llm_turn(state, request.data['user_input'], request.user)
    )


@api_view(['POST'])
def builder_respond(request):
    raw_state = request.data['conversation_state']
    state = ConversationState.model_validate(raw_state)

    if state.mode == BuilderMode.WIZARD:
        return Response(process_response(raw_state, request.data['user_input'], request.user))

    return Response(
        process_llm_turn(state, request.data['user_input'], request.user)
    )
```

---

## 5. 프론트엔드 설계

### 5-1. 타입 확장 (최소)

```typescript
// MVP에 필요한 타입만 정의

export type BuilderPhase =
	| "proposal"
	| "preset"
	| "confirm"
	| "complete"
	| "fallback";

export interface ConversationState {
	conv_id: string;
	mode: "llm" | "wizard";
	phase: BuilderPhase;
	turn_count: number;
	// 나머지는 서버에서 관리, FE는 그대로 에코
	[key: string]: unknown;
}

export interface ConversationResponse {
	message: string;
	buttons: { id: string; label: string }[];
	conversation_state: ConversationState;
	is_complete?: boolean;
	confidence?: "high" | "medium" | "low";
	indicator_recommendations?: IndicatorRecommendation[];
	needs_preset?: boolean;
	created_thesis?: { thesis_id: number; title: string; dashboard_url: string };
}

export interface IndicatorRecommendation {
	premise_title: string;
	indicator: { id: number; name: string } | null;
	indicator_name: string;
	why: string;
	signal_type: "leading" | "coincident" | "lagging";
	auto_matched: boolean;
}
```

### 5-2. 컴포넌트 구조 (MVP)

```
ThesisBuilder (page.tsx)
├── ChatArea                    # 대화 히스토리
│   ├── AiMessage               # AI 응답 버블
│   │   ├── MessageText         # 자연어 메시지
│   │   ├── IndicatorCards[]    # 지표+why 카드 (auto_matched 시각 표시)
│   │   └── ButtonGroup         # 맥락 버튼
│   └── UserMessage             # 사용자 버블
│
├── PresetSelector              # phase=preset 일 때만 표시
│   └── 3개 프리셋 카드 (단기/중기/장기)
│
├── TextInput                   # 항상 표시
│
└── TurnIndicator               # ● ○ ○ (phase 기반)
```

**Phase B에서 추가될 컴포넌트** (지금은 미구현):

- MiniDashboardPreview
- EditModePanel
- GuidedSuggestion

### 5-3. Mock 데이터

```typescript
// MVP: 시나리오 2개만
// 1. 기본 경로 (proposal → preset → confirm)
// 2. fallback 경로 (proposal 실패 → wizard)
```

---

## 6. Feature Flag 전략

```python
# thesis/feature_flags.py

FEATURE_FLAGS = {
    # ─── Core (MVP ON) ───
    'LLM_BUILDER_ENABLED': True,        # LLM 빌더 전체 on/off
    'INDICATOR_CONTEXT_ENABLED': True,   # Indicator DB 목록을 프롬프트에 주입

    # ─── Context Sources (MVP OFF) ───
    'CHAIN_CONTEXT_ENABLED': False,      # Chain Sight Neo4j 맥락
    'EOD_CONTEXT_ENABLED': False,        # EOD Screening 시그널
    'NEWS_CONTEXT_ENABLED': False,       # News Pipeline 요약

    # ─── UI Features (MVP OFF) ───
    'MINI_DASHBOARD_PREVIEW': False,     # 등록 후 미니 대시보드
    'GUIDED_SUGGESTION': False,          # confidence:low 연속 시 템플릿 제안
    'MULTI_TURN_EDIT': False,            # 멀티턴 수정 대화

    # ─── Experimental ───
    'STREAMING_RESPONSE': False,         # SSE 스트리밍
    'DIRECTION_CHAIN_FILTER': False,     # Chain Sight direction 기반 필터링
}


def get_feature_flags() -> dict:
    """
    MVP: 환경 변수 또는 Django settings에서 로드.
    향후: DB 기반 런타임 토글 전환 가능.
    """
    from django.conf import settings
    overrides = getattr(settings, 'THESIS_FEATURE_FLAGS', {})
    return {**FEATURE_FLAGS, **overrides}
```

**플래그 사용 패턴**:

```python
# 프롬프트 빌더에서
if flags.get('CHAIN_CONTEXT_ENABLED'):
    blocks.append(build_chain_block(chain_ctx))

# views.py에서
if not get_feature_flags()['LLM_BUILDER_ENABLED']:
    return Response(process_response(...))  # 기존 wizard
```

---

## 7. Observability / Logging 설계

### 7-1. 이벤트 정의

```python
# thesis/services/event_log.py

import logging
import json
from datetime import datetime

logger = logging.getLogger('thesis.builder')


def log_event(event_name: str, data: dict = None):
    """
    MVP: 구조화된 서버 로그.
    향후: BuilderEvent 모델로 DB 저장 전환 가능.
    """
    entry = {
        'event': event_name,
        'timestamp': datetime.utcnow().isoformat(),
        'data': data or {},
    }
    logger.info(json.dumps(entry, ensure_ascii=False))
```

### 7-2. 이벤트 카탈로그

| 이벤트               | 시점                               | 포함 데이터                                        |
| -------------------- | ---------------------------------- | -------------------------------------------------- |
| `builder_started`    | builder_start API 진입             | conv_id, entry_source                              |
| `proposal_generated` | Gemini 응답 후처리 완료            | conv_id, confidence, warnings, premise_count       |
| `llm_parse_failed`   | normalize/validate에서 치명적 에러 | conv_id, errors                                    |
| `fallback_triggered` | wizard 모드 전환                   | conv_id, reason                                    |
| `preset_selected`    | 프리셋 선택 완료                   | conv_id, preset_key                                |
| `confirm_clicked`    | 등록 확인                          | conv_id                                            |
| `thesis_created`     | DB 저장 완료                       | conv_id, thesis_id, premise_count, indicator_count |
| `session_abandoned`  | 5분 내 후속 요청 없음              | conv_id, last_phase (배치 감지)                    |

### 7-3. 측정 가능한 지표 (로그 기반 추출)

| 지표                | 추출 방법                                               |
| ------------------- | ------------------------------------------------------- |
| 평균 턴 수          | `thesis_created` 시점의 turn_count 평균                 |
| 등록 완료율         | `thesis_created` / `builder_started`                    |
| fallback 비율       | `fallback_triggered` / `builder_started`                |
| auto_matched 비율   | `thesis_created`의 indicator_count 중 auto_matched 비율 |
| low confidence 비율 | `proposal_generated`에서 confidence=low 비율            |
| LLM 실패율          | `llm_parse_failed` / `builder_started`                  |

---

## 8. 단계별 구현 계획

### Phase A-MVP (2-3일)

**목표**: "삼성전자 반등" → 3턴 → 가설 등록 — 이것만 되면 배포.

| 영역     | 작업                                                                          | 예상             |
| -------- | ----------------------------------------------------------------------------- | ---------------- |
| Backend  | ConversationState Pydantic 모델                                               | 0.5h             |
| Backend  | build_base_instruction() + build_type_guide_block() + build_indicator_block() | 1h               |
| Backend  | call_gemini() + Structured Output 스키마                                      | 1h               |
| Backend  | normalize_llm_output() + validate_llm_output()                                | 1.5h             |
| Backend  | merge_to_collected()                                                          | 0.5h             |
| Backend  | match_indicators() (PK 우선)                                                  | 1h               |
| Backend  | handle_proposal() + handle_preset() + handle_confirm()                        | 2h               |
| Backend  | fallback_to_wizard()                                                          | 0.5h             |
| Backend  | views.py mode 분기                                                            | 0.5h             |
| Backend  | feature_flags.py + log_event()                                                | 0.5h             |
| Frontend | 타입 확장 + PresetSelector + IndicatorCard                                    | 3h               |
| Frontend | TextInput 상시 표시 + phase 기반 UI 분기                                      | 2h               |
| Frontend | Mock 데이터 (기본 + fallback)                                                 | 1h               |
| **합계** |                                                                               | **~15h (2-3일)** |

### Spike (착수 전 0.5일)

반드시 먼저 검증:

- [ ] Gemini Playground에서 Structured Output + Indicator DB 목록(id 포함) 테스트
- [ ] indicator_db_id 반환 정확도 측정
- [ ] 응답 시간 측정 (2초 이내 확인)

### Phase A-Hardening (2-3일)

배포 후 안정화:

- [ ] normalize/validate edge case 추가 (실 사용 로그 기반)
- [ ] Gemini 스키마 불일치 패턴 수집 → normalize 보강
- [ ] fallback 전환 안정성 검증 (LLM↔wizard 왕복 테스트)
- [ ] log_event 기반 지표 추출 스크립트
- [ ] 프론트엔드 에러 바운더리 강화
- [ ] ConversationState 직렬화/역직렬화 edge case
- [ ] Gemini Free Tier 한도 모니터링

### Phase B (3-5일, A-Hardening 완료 후)

- [ ] `CHAIN_CONTEXT_ENABLED` = True — Chain Sight 맥락 주입
- [ ] `EOD_CONTEXT_ENABLED` = True — EOD 시그널 주입
- [ ] `NEWS_CONTEXT_ENABLED` = True — 뉴스 요약 주입
- [ ] `MULTI_TURN_EDIT` = True — "근거 수정할게요" 멀티턴
- [ ] target 변경 시 상태 초기화 로직
- [ ] direction 기반 Chain Sight 필터링
- [ ] MiniDashboardPreview

### Phase C (사용자 피드백 축적 후)

- [ ] Guided Suggestion (confidence:low 연속 대응)
- [ ] Semantic Controls ("보수적으로 판단해줘")
- [ ] 스트리밍 응답 (SSE)
- [ ] 과거 가설 패턴 맥락
- [ ] Advanced Mode (전문가용 파라미터)

---

## 9. 리스크 및 완화

| 리스크                          | 확률 | 영향 | 완화                                                |
| ------------------------------- | ---- | ---- | --------------------------------------------------- |
| Gemini Structured Output 불일치 | 중   | 높   | normalize/validate 레이어 + fallback                |
| indicator_db_id 오매칭          | 중   | 중   | PK 조회 실패 → 문자열 fallback 2단계                |
| One-shot 품질 불안정            | 중   | 높   | confidence 필드 + Hardening에서 프롬프트 개선       |
| ConversationState 직렬화 오류   | 낮   | 높   | Pydantic model_validate + 에러 시 wizard fallback   |
| Gemini Free Tier RPD 초과       | 낮   | 중   | 기본 1회 호출, 모니터링                             |
| feature flag 꼬임               | 낮   | 중   | 플래그 조합 테스트, 독립성 보장                     |
| 프롬프트 토큰 초과              | 낮   | 중   | Indicator DB 목록 크기 모니터링, 필요 시 상위 N개만 |

---

## 10. 1인 개발자 유지보수 관점 총평

이 설계의 핵심은 **"작게 만들고, 안전하게 확장하는 구조"**다.

MVP는 Gemini 1회 호출 + Indicator DB 맥락 + 프리셋 + 저장. 이것만 동작하면 사용자 경험은 이미 기존 위자드 대비 근본적으로 달라진다. 나머지(Chain Sight, EOD, News, 멀티턴 수정)는 feature flag 뒤에서 하나씩 켜면 된다.

유지보수 부담이 가장 큰 지점은 **LLM 출력의 흔들림 대응**이다. normalize/validate 레이어를 초기부터 넣는 이유가 이것이다. Hardening 단계에서 실 사용 로그를 보면서 패턴을 잡아가면 안정성이 빠르게 올라간다.

상태 관리는 Pydantic + BuilderPhase enum으로 "어디서든 현재 상태를 알 수 있는 구조"를 만들었다. MVP에서 edit flow를 "다시 만들어줘"로 제한한 이유도 상태 복잡도 관리를 위해서다. Phase B에서 멀티턴 수정을 열 때도 phase 기반 전이 규칙 위에서 확장하면 된다.

---

## 부록 A. 지금 당장 / 나중에 구분표

| 지금 당장 (Phase A-MVP)                       | 나중에 미뤄도 되는 것         |
| --------------------------------------------- | ----------------------------- |
| Pydantic ConversationState                    | Chain Sight 맥락 주입         |
| build_base + type_guide + indicator_block     | EOD/News 맥락 주입            |
| Gemini Structured Output 호출                 | 멀티턴 수정 대화              |
| normalize → validate → merge 파이프라인       | target/direction 변경         |
| PK 우선 2단계 지표 매칭                       | MiniDashboardPreview          |
| 프리셋 3개 (단기/중기/장기)                   | Guided Suggestion 템플릿      |
| confirm → DB 저장 (기존 \_create_thesis 래핑) | 스트리밍 응답 (SSE)           |
| fallback → wizard 전환                        | 과거 가설 패턴 맥락           |
| feature_flags.py (기본 ON/OFF만)              | DB 기반 런타임 플래그 토글    |
| log_event() 서버 로그                         | 분석 대시보드 / 이벤트 테이블 |
| Mock 2개 (기본 + fallback)                    | 시나리오별 Mock 5개+          |
| IndicatorCard (why 표시)                      | Semantic Controls             |
| PresetSelector                                | Advanced Mode                 |
| phase 기반 상태 전이                          | patch 방식 collected 수정     |
| thesis_type: list[str] JSON 저장              | ArrayField 전환               |

## 부록 B. 1인 개발자 입장에서 가장 위험한 복잡도 포인트 5개

### 1. LLM 출력 흔들림 (위험도: ★★★★★)

Gemini가 매번 조금씩 다른 형태의 JSON을 반환한다. direction이 "Bullish"일 때도, "bullish"일 때도, "상승"일 때도 있다. thesis_type이 "earnings+chain"일 때도, ["earnings","chain"]일 때도 있다. normalize 레이어 없이 바로 저장하면 DB가 오염된다.

**대응**: normalize_llm_output()을 첫 주부터 넣고, Hardening에서 실 로그 보면서 패턴 추가.

### 2. ConversationState 직렬화 왕복 (위험도: ★★★★☆)

state가 프론트엔드 → 백엔드 → 프론트엔드를 매 턴마다 왕복한다. dict를 쓰면 "어디서 어떤 필드가 추가/누락되었는지" 추적이 불가능해진다. 특히 LLM 모드와 wizard 모드를 오가면서 state 구조가 달라지면 런타임 에러가 터진다.

**대응**: Pydantic model_validate()로 매 진입 시 검증. 실패하면 wizard fallback.

### 3. Edit Flow의 상태 폭발 (위험도: ★★★★☆)

"근거 바꿔줘" → "지표 빼줘" → "아니 다른 종목으로" → "다시 원래대로" — 이 흐름을 전부 지원하면 상태 조합이 기하급수적으로 늘어난다. 1인 개발에서 이 모든 edge case를 테스트하는 건 불가능에 가깝다.

**대응**: MVP에서 edit = "다시 만들어줘" (전체 재시작)로 제한. Phase B에서 제한적 patch 허용.

### 4. 맥락 소스 4개 동시 관리 (위험도: ★★★☆☆)

Chain Sight + EOD + News + Indicator DB를 동시에 프롬프트에 넣으면 토큰 관리, 에러 핸들링, 성능 모니터링이 4배가 된다. 하나가 느려지거나 실패하면 전체 응답이 영향받는다.

**대응**: feature flag로 하나씩 켜기. MVP는 Indicator DB만. Phase B에서 하나씩 추가하면서 실측.

### 5. Gemini Free Tier 한도 + 프롬프트 토큰 비용 (위험도: ★★☆☆☆)

1500 RPD에서 맥락 소스가 늘어날수록 input 토큰이 커지고, 비용 전환 시점이 앞당겨진다. 또한 긴 프롬프트는 Gemini 응답 품질에도 영향을 줄 수 있다.

**대응**: 맥락 블록별 토큰 크기 모니터링. Indicator DB 목록이 100개 넘으면 카테고리별 상위 N개만 포함.
