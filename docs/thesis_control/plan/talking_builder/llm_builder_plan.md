# LLM 기반 대화형 가설 빌더 전환 계획서

> 작성일: 2026-03-19
> 담당: @frontend / @backend 협업
> 상태: 계획 단계 (미착수)

---

## 1. 현재 구조 분석

### 1-1. 백엔드 위자드 패턴 (`thesis/services/thesis_builder.py`)

현재 빌더는 **고정된 6단계 위자드** 방식이다.

```
step 1: direction 선택 (DIRECTION_CHOICES — bullish / bearish / neutral)
step 2: reason 선택 (REASON_CHOICES — 8개 고정 버튼, multi select)
step 3: timeframe 선택 (TIMEFRAME_CHOICES — 5개 고정 버튼)
step 4: magnitude 선택 (MAGNITUDE_CHOICES — 4개 고정 버튼)
step 5: preview 확인 (confirm / modify)
step 6: 생성 완료 (Thesis + ThesisPremise + ThesisIndicator 저장)
```

`process_response()` 함수가 `entry_source` (news / free_input) 에 따라 두 경로로 분기하지만, 두 경로 모두 동일한 고정 선택지 집합을 순서대로 제공한다. `conversation_state` 는 단순히 `step` 숫자와 `collected` dict를 JSON으로 직렬화하여 프론트엔드에 에코(echo)한다. 서버 측에서 대화 히스토리를 저장하지 않는다.

**고정 선택지 상수**

| 상수 | 항목 수 | 설명 |
|------|---------|------|
| `DIRECTION_CHOICES` | 3 | bullish / bearish / neutral |
| `REASON_CHOICES` | 9 | 8개 카테고리 + custom |
| `TIMEFRAME_CHOICES` | 5 | short / medium / half / year / skip |
| `MAGNITUDE_CHOICES` | 4 | mild / moderate / severe / skip |

### 1-2. Gemini 사용 방식 — `_parse_free_input()` (line 401-456)

free_input 경로의 step 1에서 **자유 텍스트 → 구조화 파싱** 용도로만 Gemini를 호출한다.

```python
# 현재 Gemini 역할: 텍스트 파싱 한 번
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt,  # 사용자 입력 한 줄 + JSON 스키마 지시
    config=config,    # temperature=0.3, thinking_budget=0
)
```

출력은 `title / direction / target / target_type / thesis_type / premises` 필드를 가진 JSON 한 조각이다. 파싱 실패 시 `_fallback_parse()` (키워드 매칭)로 대체한다.

Gemini는 **대화를 주도하지 않는다.** 단지 입력값을 구조화하는 변환기 역할만 한다.

### 1-3. 프론트엔드 Mock 구조 (`frontend/lib/thesis/mock.ts`)

`USE_MOCK=true`이면 백엔드를 전혀 호출하지 않고, 프론트엔드의 두 개의 고정 step map을 순서대로 소비한다.

```typescript
// free_input 경로 mock 순서 (step 숫자 → 응답 객체)
export const MOCK_FREE_STEP_MAP: Record<number, ConversationResponse> = {
  2: MOCK_FREE_CONFIRM_STEP,     // Gemini 파싱 결과 확인
  3: MOCK_REASON_STEP,           // 이유 선택 (multi)
  4: MOCK_TIMEFRAME_STEP,        // 시점 선택
  5: MOCK_MAGNITUDE_STEP,        // 강도 선택
  6: MOCK_PREVIEW_STEP,          // 미리보기
  7: MOCK_CONVERSATION_DONE,     // 완료
}
```

모든 응답은 컴파일 타임에 하드코딩된 KOSPI 하락 시나리오를 가리킨다. 사용자 입력에 관계없이 동일한 흐름이 재생된다.

### 1-4. 한계점 정리

| 구분 | 현재 문제 |
|------|---------|
| 고정 질문 순서 | direction → reasons → timeframe → magnitude 순서가 항상 동일. 사용자가 "금리 인상으로 반도체 주가 하락"을 입력해도 동일 경로 |
| 맥락 없는 선택지 | REASON_CHOICES는 KOSPI 하락 상황에 맞춘 8개 항목. "테슬라 상승 베팅" 상황에는 어울리지 않음 |
| 사용자 의도 괴리 | 자유 텍스트 입력 → 파싱 → 다시 버튼 선택 흐름은 사용자가 기대하는 "AI와 대화" 경험이 아님 |
| 대화 히스토리 없음 | 각 요청은 stateless. LLM이 이전 맥락을 모름 |
| 대화 품질 | LLM이 맥락 기반 후속 질문을 생성하지 않음 |

---

## 2. 목표 설계 — LLM 대화형 빌더

### 2-1. 핵심 원칙

1. **LLM이 질문을 생성한다.** 사용자가 입력한 내용을 분석하여 부족한 정보(방향, 근거, 시점 등)를 자연어로 질문한다.
2. **자유 텍스트가 1급 시민이다.** 사용자가 버튼을 누르지 않고 채팅처럼 답변해도 흐름이 이어진다.
3. **빠른 선택 버튼은 보조 수단이다.** LLM이 답변을 생성할 때 맥락에 맞는 선택지를 함께 제안한다 (3-4개). 버튼을 누르면 해당 텍스트가 자유 텍스트로 전송된 것처럼 처리한다.
4. **결과는 기존 파이프라인을 재사용한다.** `_create_thesis()` 로직은 그대로 유지하고, LLM 대화의 마지막에 동일한 `Thesis + ThesisPremise + ThesisIndicator` 구조를 생성한다.

### 2-2. 대화 흐름 예시 (한국어, 한국 투자자 관점)

#### 시나리오 A: 반도체 섹터 상승 베팅

```
사용자: 삼성전자 2분기에 반등할 것 같아요

AI: 반등할 것 같다는 생각이 드는 주요 이유가 있나요?
    HBM 수요가 본격화될 것 같아서인지, 아니면 밸류에이션이 너무 많이 빠져서인지 궁금해요.

    [HBM/AI 수요 기대] [밸류에이션 저평가] [외국인 매수 복귀] [직접 입력...]

사용자: HBM 수요가 본격화될 것 같아서요

AI: 알겠어요. HBM 수요 확인을 위해 어떤 신호를 주로 보실 건가요?
    SK하이닉스 수주 공시나 엔비디아 실적 가이던스 같은 걸 보실 것 같아서요.

    [엔비디아 실적 가이던스] [SK하이닉스 수주] [반도체 수출 통계] [직접 입력...]

사용자: 엔비디아 가이던스랑 수출 통계 같이 볼게요

AI: 2분기 반등이라면 대략 언제쯤을 생각하고 계신가요?

    [4월 이내] [5-6월 중] [2분기 말] [모르겠어요]

사용자: 5월에서 6월 사이

AI: 정리해봤어요.

    가설: 삼성전자 2분기 반등
    방향: 상승 (bullish)
    기간: 2025년 5-6월
    근거:
     - HBM/AI 수요 본격화 기대
     - 엔비디아 실적 가이던스 확인
     - 반도체 수출 통계 모니터링

    AI 추천 지표: 엔비디아 매출 가이던스, 한국 반도체 수출 YoY, HBM ASP 추이

    이대로 가설을 등록할까요?

    [네, 등록해요] [수정할게요]
```

#### 시나리오 B: 매크로 리스크 하락 베팅

```
사용자: 미 연준이 생각보다 금리를 오래 유지할 것 같아서 나스닥이 힘들 것 같아

AI: 고금리 장기화가 나스닥에 압박을 줄 것이라는 가설이군요.
    어느 정도의 조정을 예상하시나요?

    [5% 이내 소폭 조정] [10% 이상 의미 있는 조정] [구조적 약세장] [모르겠어요]

사용자: 10% 이상은 될 것 같아요

AI: 언제쯤 가장 강한 압박이 올 것 같으세요?

    [1개월 이내] [2-3개월] [하반기] [연말]

사용자: 하반기에 본격화될 것 같아요

AI: 나스닥 고금리 압박 외에 추가로 걱정되는 게 있나요?
    달러 강세나 기업 실적 부진 같은 이유도 있나요?

    [달러 강세] [기업 이익 감소] [없어요, 이게 전부예요]

사용자: 달러 강세도 문제고 빅테크 실적이 걱정돼요

AI: 정리해봤어요.

    가설: 나스닥 하반기 조정 (10%+)
    방향: 하락 (bearish)
    기간: 2025년 하반기
    근거:
     - 고금리 장기화로 밸류에이션 부담
     - 달러 강세로 해외 매출 압박
     - 빅테크 실적 부진 우려

    AI 추천 지표: 연준 FOMC 점도표, DXY 달러 인덱스, 빅테크 EPS 컨센서스

    이대로 가설을 등록할까요?
```

#### 시나리오 C: 단 한 줄 입력 (정보 부족 → LLM이 적극 질문)

```
사용자: 원화 약세

AI: 원/달러 환율이 오를 것 같다는 뜻인가요?
    어떤 자산에 대한 가설인지 조금 더 알려주실 수 있어요?

    [수출주 수혜 (상승)] [수입 비용 증가 우려 (하락)] [환율 자체 추적]

사용자: 수출주 수혜 보려고요

AI: 수출주 중 가장 영향이 클 섹터를 생각하고 계신가요?

    [반도체/IT] [자동차] [조선] [화학]

사용자: 자동차요, 현대차

AI: 현대차 관련해서 원화 약세가 실적에 반영되는 시점을 언제쯤으로 보세요?

    [다음 분기 실적] [연간 가이던스] [즉각적 주가 반응]

...
```

---

## 3. 기술 아키텍처

### 3-1. Backend: `thesis_builder.py` 대화 엔진 재설계

#### ConversationState — 대화 히스토리 관리

현재 `state` dict는 `step`, `collected` 두 필드만 가진다. LLM 대화형으로 전환하면 **대화 히스토리**가 핵심 상태가 된다.

```python
# 신규 state 구조 (Python dict)
state = {
    'conv_id': str,                  # 기존 유지
    'entry_source': str,             # 기존 유지
    'mode': 'llm' | 'wizard',        # 신규: 대화 모드
    'history': [                     # 신규: 멀티턴 히스토리
        {'role': 'assistant', 'content': '...'},
        {'role': 'user', 'content': '...'},
        ...
    ],
    'collected': {                   # 기존 유지 (LLM이 채워나감)
        'direction': None,
        'target': None,
        'premises': [],
        'timeframe': None,
        'magnitude': None,
    },
    'turn_count': int,               # 신규: 몇 번 주고받았는지
    'is_complete': bool,             # 신규: 구조 추출 완료 여부
    'source_news_id': str | None,    # 기존 유지
}
```

`history`는 매 요청마다 프론트엔드에서 백엔드로 전송하고, 백엔드는 이것을 Gemini에 직접 전달한다. 서버가 별도 DB에 히스토리를 저장하지 않아도 된다 (stateless 유지). 이는 현재 `conversation_state` 에코(echo) 패턴과 동일하다.

#### LLM 프롬프트 설계

```
System Prompt:
  당신은 투자자가 투자 가설을 명확하게 세울 수 있도록 돕는 전문 어시스턴트입니다.
  목표는 다음 구조를 자연스러운 대화로 수집하는 것입니다:
    - direction: 상승(bullish) / 하락(bearish) / 중립(neutral)
    - target: 종목명, ETF, 지수, 섹터
    - premises: 가설의 근거 목록 (1~5개)
    - timeframe: 예상 시점 (선택)
    - magnitude: 예상 강도 (선택)

  규칙:
  1. 한 번에 하나의 짧은 질문만 합니다.
  2. 맥락에 맞는 빠른 선택지를 3-4개 제안합니다.
  3. collected 구조가 충분히 채워지면 요약 후 확인을 요청합니다.
  4. 한국어로 답변합니다.

User History:
  {conversation_history}

Structured Output:
  {
    "message": "AI 응답 텍스트",
    "buttons": [{"id": "...", "label": "..."}],
    "collected_update": {"direction": ..., "target": ..., "premises": ..., ...},
    "is_complete": bool,
    "selection_mode": "single" | "multi"
  }
```

#### Structured Output으로 가설 구조 추출

Gemini의 Structured Output (JSON mode)를 사용하면 `re.search(r'\{.*\}')` 파싱 없이 안정적으로 결과를 받을 수 있다.

```python
from google.genai import types

schema = {
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
                "direction": {"type": "string"},
                "target": {"type": "string"},
                "premises": {"type": "array", "items": {"type": "string"}},
                "timeframe": {"type": "string"},
                "magnitude": {"type": "string"},
            },
        },
        "is_complete": {"type": "boolean"},
        "selection_mode": {"type": "string", "enum": ["single", "multi"]},
    },
    "required": ["message", "buttons", "is_complete"],
}

config = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=schema,
    temperature=0.7,
    max_output_tokens=1000,
    thinking_config=types.ThinkingConfig(thinking_budget=0),
)
```

#### 엔진 진입점 함수 (신규)

```python
def process_llm_turn(conversation_state: dict, user_input: str, user=None) -> dict:
    """
    멀티턴 LLM 대화 처리.
    - conversation_state에 history 포함
    - Gemini로 다음 메시지 + 선택지 + collected_update 생성
    - is_complete=True이면 _create_thesis() 호출
    """
```

#### 기존 `_create_thesis()` 재사용

LLM 대화의 마지막에 `collected` 구조가 기존 위자드와 동일한 형태로 채워지도록 설계하면, `_create_thesis()` 함수를 수정 없이 재사용할 수 있다.

```python
# 기존 코드 재사용 가능 범위
_resolve_reasons()          # 전제 리스트 변환 — 재사용 가능
_build_thesis_summary()     # 지표 추천 포함 요약 — 재사용 가능
_create_thesis()            # Thesis/Premise/Indicator 저장 — 재사용 가능
match_indicators_for_premise()  # 지표 매칭 — 재사용 가능
_fallback_parse()           # LLM 실패 시 폴백 — 재사용 가능
```

### 3-2. Frontend: 채팅 UI 컴포넌트

현재 `frontend/app/thesis/new/page.tsx`는 이미 채팅 버블 + 버튼 조합 UI를 가지고 있다. 변경 범위가 최소화된다.

#### 주요 변경 포인트

| 컴포넌트 | 현재 | 변경 후 |
|---------|------|--------|
| `ThesisBuilder` (page.tsx) | step 숫자 기반 분기 | history 배열 기반, turn_count 표시 |
| `ProgressBar` | step/totalSteps 고정 | 완료율(0-100%) 또는 숨김 |
| `TextInput` | free_input 경로에서만 표시 | 항상 표시 (버튼도 보조 역할) |
| `ConversationResponse` 타입 | `step`, `total_steps` 필수 | `turn_count`, `is_complete` 추가 |

#### 스트리밍 응답 (선택사항)

Gemini의 `stream=True` 옵션을 사용하면 응답이 실시간으로 타이핑되는 효과를 낼 수 있다. 단, 프론트엔드에서 SSE(Server-Sent Events) 또는 WebSocket 구현이 필요하다. Phase A/B에서는 단일 요청-응답으로 시작하고, Phase C에서 선택적으로 추가한다.

#### `ConversationResponse` 타입 확장 (신규 필드)

```typescript
export interface ConversationResponse {
  // 기존 필드 유지
  message: string
  buttons: ConversationButton[]
  selection_mode: 'single' | 'multi'
  conversation_state: ConversationState
  step: number          // 하위 호환성 유지
  total_steps: number

  // 신규 필드
  turn_count?: number   // 몇 번째 대화 턴인지
  is_complete?: boolean // true이면 preview 표시 단계
  input_type?: 'text'   // 항상 text 허용으로 변경
}
```

#### `ConversationState` 타입 확장

```typescript
export interface ConversationState {
  conv_id: string
  entry_source: EntrySource
  step: number
  collected: Record<string, unknown>
  source_news_id?: string

  // 신규: LLM 모드
  mode?: 'llm' | 'wizard'
  history?: Array<{ role: 'assistant' | 'user'; content: string }>
  turn_count?: number
  is_complete?: boolean
}
```

---

## 4. 구현 전략

### 4-1. 단계별 접근

```
Phase A (저위험, 1-2일)
  현재 위자드에 LLM 응답 가미
  — 기존 6단계 구조 유지
  — 각 단계의 고정 메시지를 Gemini가 맥락에 맞게 변형
  — 선택지는 여전히 고정 (REASON_CHOICES 등)
  — 예: "왜 그렇게 생각하세요?" 대신 "KOSPI에 대해 그런 판단을 하셨군요. 주된 이유가 뭔가요?"

Phase B (중위험, 3-5일)
  자유 대화 + 구조 추출
  — step 개념 제거, turn_count 도입
  — history 배열 도입 (stateless, 프론트엔드가 전달)
  — Gemini가 매 턴 collected_update 반환
  — 기존 위자드 fallback 유지 (LLM 실패 시 자동 전환)
  — 버튼은 Gemini가 맥락에 맞게 3-4개 생성

Phase C (고위험, 1주+)
  멀티턴 대화 + 지표 추천 통합
  — match_indicators_for_premise()를 대화 중간에 호출
  — "이 전제에는 외국인 순매수 지표가 잘 맞아요. 추가할까요?" 형태 대화
  — 스트리밍 응답 도입 (선택)
  — 완전한 LLM 주도 대화
```

### 4-2. 예상 작업량

| Phase | Backend | Frontend | 총 예상 |
|-------|---------|----------|--------|
| Phase A | 0.5일 | 0.5일 | 1일 |
| Phase B | 2일 | 1.5일 | 3.5일 |
| Phase C | 3일 | 2일 | 5일 |

Phase A와 Phase B는 독립적으로 배포 가능하다. Phase C는 Phase B 완료 후 진행한다.

### 4-3. 백엔드 API 변경 범위

현재 `/api/v1/thesis/builder/start/` 와 `/api/v1/thesis/builder/respond/` 두 엔드포인트가 있다. Phase B부터 respond 엔드포인트의 Request Body에 `history` 배열이 추가된다. 기존 위자드 클라이언트와의 하위 호환성은 `mode` 필드로 분기하여 유지한다.

```python
# views.py 예시
def respond(request):
    conversation_state = data['conversation_state']
    mode = conversation_state.get('mode', 'wizard')

    if mode == 'llm':
        return process_llm_turn(conversation_state, user_input, request.user)
    else:
        return process_response(conversation_state, user_input, request.user)
```

---

## 5. 리스크 및 고려사항

### 5-1. Gemini Free Tier 제한

- 현재: 15 RPM (분당 요청), 1500 RPD (일일 요청)
- LLM 대화형으로 전환 시 **가설 1개 생성에 평균 5-8 Gemini 호출**이 필요하다
- 현재 `_parse_free_input()` 1회 호출 대비 5-8배 증가
- 일일 1500 RPD 기준: 약 187-300개 가설 생성까지 수용 가능
- 프로덕션 규모가 커지면 Gemini Pro/Paid 전환 필요

### 5-2. 대화 품질 불확실성

- **Hallucination 리스크**: LLM이 존재하지 않는 지표나 잘못된 시황을 언급할 수 있음
  - 완화: system prompt에 "확실하지 않으면 질문으로 대신하라" 명시
- **구조 추출 실패**: `collected_update`가 부정확하게 채워질 수 있음
  - 완화: Structured Output (JSON mode) 사용, 필수 필드 validation
- **무한 대화**: 사용자가 계속 새로운 정보를 추가하면 종료 조건이 불명확함
  - 완화: `turn_count >= 10` 이면 강제 요약 단계 진입, "이 정도면 충분해요. 정리해드릴까요?" 제시

### 5-3. 기존 파이프라인 호환성

- `_create_thesis()`는 `collected` dict를 입력받는다. LLM 대화로 `collected`를 채우는 방식이 바뀌어도 저장 로직은 동일하다.
- Phase A에서 기존 위자드를 건드리지 않으므로 호환성 문제 없음
- Phase B부터 `mode` 플래그로 위자드/LLM 경로를 분기하므로 기존 클라이언트도 계속 동작

### 5-4. Fallback 전략

```
LLM API 실패 (네트워크, 타임아웃, 503)
  → 현재 위자드 모드로 자동 전환
  → 사용자에게: "AI 대화 기능에 일시적 문제가 있어요. 단계별 방식으로 진행해도 괜찮으시겠어요?"
  → [단계별로 진행] 버튼 제공

Structured Output 파싱 실패
  → _fallback_parse() (키워드 매칭) 적용
  → collected에 최소한의 정보만 채우고 다음 턴 진행

Turn count 초과 (>= 10턴)
  → 강제 요약 단계 진입
  → _build_thesis_summary()로 지금까지 수집된 정보로 미리보기 생성
```

### 5-5. 비용 추정

| 시나리오 | RPD 사용 | 월 비용 (Gemini Pro) |
|---------|---------|---------------------|
| Free Tier | 1500/일 | $0 (제한 범위 내) |
| 일 50명 × 5회 입력 | 250/일 | $0 (Free 범위 내) |
| 일 200명 × 7회 입력 | 1400/일 | $0 (Free 범위 내) |
| 일 500명 × 7회 입력 | 3500/일 | 유료 전환 필요 |

현재 서비스 규모(개인 프로젝트)에서는 Free Tier 한도 이내로 운영 가능하다.

---

## 6. 우선순위 판단

### 6-1. Phase 3 대시보드 리디자인과의 관계

현재 진행 중인 **Thesis Control Phase 3** (FE-PR-7~11: 대시보드 탭 구조, 전제 관리, 히트맵, 히스토리 차트, 마감 아카이브, 투자자 DNA)와 이 작업은 **완전히 독립적**이다.

- LLM 빌더는 `/thesis/new` 경로에 격리됨
- 대시보드는 `/thesis/:id` 경로에 격리됨
- 공유 컴포넌트(`ConversationState`, `ConversationResponse` 타입) 확장은 하위 호환 방식으로 가능

### 6-2. 권장 순서

```
1단계: Phase 3 FE-PR-7~11 완료 (대시보드 리디자인)
         ↓ 완료 후
2단계: Phase A (1일) — 위자드 메시지 LLM 변형 (저위험 워밍업)
         ↓
3단계: Phase B (3.5일) — 완전 대화형 전환 (핵심 작업)
         ↓ 안정화 후
4단계: Phase C (5일) — 스트리밍 + 지표 추천 통합
```

### 6-3. 독립 착수 가능 여부

Phase A는 대시보드 작업과 동시에 진행해도 충돌이 없다. 단, 팀원 리소스 분산을 피하기 위해 대시보드 완료 후 시작을 권장한다.

---

## 7. 체크리스트 (Phase B 기준)

### Backend
- [ ] `process_llm_turn()` 함수 구현
- [ ] System prompt + few-shot 예시 설계
- [ ] Structured Output 스키마 정의
- [ ] `collected_update` merge 로직
- [ ] Turn count 초과 시 강제 요약 로직
- [ ] Fallback (위자드 모드 전환) 구현
- [ ] `/api/v1/thesis/builder/respond/` 에 `mode` 분기 추가

### Frontend
- [ ] `ConversationState` 타입에 `history`, `mode`, `turn_count` 추가
- [ ] `TextInput`을 항상 표시 (버튼과 공존)
- [ ] `ProgressBar`를 `turn_count` 기반 완료율로 교체 또는 숨김
- [ ] Mock 업데이트 (LLM 모드 대화 시나리오 2-3개)
- [ ] `MOCK_FREE_STEP_MAP` 에 `history` 에코 추가

---

## 8. 참고 파일 목록

| 파일 | 역할 |
|------|------|
| `thesis/services/thesis_builder.py` | 현재 위자드 엔진 (전체 재설계 대상) |
| `thesis/views.py` | 빌더 API 진입점 (`mode` 분기 추가 예정) |
| `frontend/app/thesis/new/page.tsx` | 빌더 UI (TextInput 상시 표시로 변경 예정) |
| `frontend/lib/thesis/types.ts` | `ConversationState`, `ConversationResponse` 확장 예정 |
| `frontend/lib/thesis/mock.ts` | LLM 모드 Mock 시나리오 추가 예정 |
| `frontend/lib/thesis/conversation.ts` | `applyResponse()` — history merge 로직 추가 예정 |
