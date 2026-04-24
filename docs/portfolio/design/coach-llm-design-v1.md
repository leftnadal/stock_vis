# Stock-Vis Coach LLM Design

> **문서 버전**: v1.0 (2026-04-20)
> **작성 배경**: 세션 D 결정 사항 중 Coach LLM 아키텍처 영역
> **관련 문서**:
> - `preset-design-v3.1.md` (Coach 철학, 역할 경계 — 기존 유지)
> - `wallet-portfolio-architecture-v1.md` (Wallet/Portfolio 개념 — 이 문서의 전제)
> - `return-tracking-design-v1.md` (수익률 breakdown — Tier 2.5에 포함되는 데이터)
> - `metric-dictionary-v1.2.md` (57개 지표 사전)

---

## 1. Coach 정체성과 역할 경계

`preset-design-v3.1.md` §1-3의 역할 경계 **유지**. 이 문서는 그 위에 LLM 아키텍처를 얹는 것.

### 1-1. Coach가 하는 것

- 포트폴리오의 구조적 진단 (프리셋 관점)
- 지표별 강약점 설명
- 비교 기준 대비 위치 해석
- 사용자 질문에 대한 설명 응답
- 레벨 1 조정 요청 이해 및 실행 (세션 범위)

### 1-2. Coach가 하지 않는 것

- "이 종목을 사라/팔아라" 직접 추천
- 가격 예측
- 외부 정보 검색 (MVP 범위 외)
- 영구 프리셋 커스터마이징 (레벨 2/3은 Phase 2+)

### 1-3. 컨설턴트 비유의 일관성

`wallet-portfolio-architecture-v1.md` §1-2의 컨설턴트 비유 유지:
- 사용자가 **"이 종목들만 봐주세요"**라고 제시한 Portfolio만 분석
- Wallet 전체는 **배경 맥락**으로만 참조 (W2.5)
- 제시하지 않은 종목에 대한 추천/평가 자제

---

## 2. MVP 기능 범위

### 2-1. 결정 요약

| 결정 | 내용 |
|---|---|
| A2 | 대화형 Q&A + 레벨 1 조정 |
| 레벨 1 조정 | 현재 분석에만 적용, 저장 없음 (세션 스코프) |
| B3 | 4-Tier 계층적 요약 (retrieval 없음) |
| C1 | 수동 저장 시점 기준 사후 분석 |
| D3 | raw 대화 저장 + 구조화 Decision 추출 (하이브리드) |

### 2-2. MVP 진입점 E1~E6

MVP에 포함되는 6개 LLM 진입점. E7~E9는 Phase 2.

| # | 이름 | 트리거 | 자동 / 수동 |
|---|---|---|---|
| E1 | 한 줄 진단 | 분석 실행 완료 | 자동 |
| E2 | 진단 카드 (약점 3개) | 분석 실행 완료 | 자동 |
| E3 | 지표별 한 줄 코멘트 | 분석 실행 완료 | 자동 |
| E4 | 대화 Q&A | 사용자 메시지 | 수동 |
| E5 | 의도 분류 + 조정 파싱 | 사용자 메시지 (조정 의도) | 수동 (E4의 서브 루틴) |
| E6 | 조정 후 해설 | 조정된 분석 실행 완료 | 자동 |

---

## 3. LLM 진입점 상세 설계

### 3-1. E1: 한 줄 진단

**용도**: 포트폴리오 전체에 대한 2~3문장 요약.

**트리거**: AnalysisRun 완료 직후.

**입력 (Tier 2.5 JSON의 일부)**:
```json
{
  "analysis_target_portfolio": {
    "name": "Tech 성장주",
    "preset_id": "garp",
    "holding_count": 5,
    "core_metric_summary": {...},
    "strengths": [...],
    "weaknesses": [...]
  },
  "wallet_background": {
    "total_holdings_count": 12,
    "sector_distribution": {...}
  }
}
```

**출력 (Pydantic)**:
```python
class OneLineDiagnosis(BaseModel):
    headline: str    # 25~40자 한 줄 진단
    summary: str     # 2~3 문장 요약
```

**예시**:
```json
{
  "headline": "퀄리티는 견조하나 밸류에이션 부담",
  "summary": "GARP 관점에서 당신의 Tech 성장주 포트폴리오는 ROIC와 성장성은 상위권이지만, 3개 종목의 PEG가 2.5 이상으로 밸류에이션 부담이 뚜렷합니다. 향후 성장 둔화 시 조정 리스크를 주시할 필요가 있습니다."
}
```

### 3-2. E2: 진단 카드 (약점 3개)

**용도**: 주요 약점 3개에 대한 4요소 상세 카드.

**트리거**: AnalysisRun 완료 직후.

**입력**: 약점 3개 각각의 지표 결과 + 프리셋 철학 + 비교 기준.

**출력 (Pydantic)**:
```python
class DiagnosticCard(BaseModel):
    weakness_metric_id: str
    what_is_wrong: str       # 팩트 진술
    comparison_basis: str    # 비교 기준 명시
    why_it_matters: str      # 프리셋 철학 연결
    caveat_or_exception: str # 예외/트레이드오프
    severity: str            # "high" | "medium" | "low"
    structural_or_single: str # "structural" | "single_outlier"

class DiagnosticCards(BaseModel):
    cards: list[DiagnosticCard]  # 최대 3개
```

**문체 원칙** (preset-design-v3.1.md §7-3 유지):
- 단정형이 아닌 조건형/설명형
- 단일 종목 이상치 vs 구조적 약점 구분
- 판단이 아닌 정보 제공

### 3-3. E3: 지표별 한 줄 코멘트

**용도**: Core + Supporting 지표 각각에 대한 1~2문장 코멘트.

**트리거**: AnalysisRun 완료 직후.

**입력**: 지표 단위 결과 (퍼센타일, 종목별 분포, 프리셋 철학).

**출력**:
```python
class MetricComment(BaseModel):
    metric_id: str
    one_liner: str  # 1~2 문장 코멘트

class MetricComments(BaseModel):
    comments: list[MetricComment]
```

**예시**:
```json
{
  "metric_id": "roic",
  "one_liner": "5개 종목 중 3개가 업종 상위 25% 이내. 다만 INTC의 ROIC가 하락 추세에 있어 주시 필요."
}
```

### 3-4. E4: 대화 Q&A

**용도**: 사용자 질문에 대한 응답.

**트리거**: 사용자가 채팅 입력.

**입력 (Tier 0~3 전체)**:
```json
{
  "system_prompt": "...",           // Tier 0
  "conversation_history": [...],     // Tier 1
  "session_summary": "...",          // Tier 2 (필요 시)
  "current_analysis_context": {...}, // Tier 2.5
  "user_profile": {...},             // Tier 3
  "current_user_message": "..."
}
```

**출력**:
```python
class ConversationResponse(BaseModel):
    response_text: str              # 자연어 응답
    has_adjustment_intent: bool     # 조정 의도 감지 여부
    adjustment_parse_hint: str = "" # 있으면 E5로 넘김
```

**처리 흐름**:
1. 사용자 메시지 수신
2. 의도 분류 (질문 / 조정 요청 / 잡담)
3. 질문이면 → 직접 응답
4. 조정 요청이면 → E5로 라우팅 후 확인 카드 생성

### 3-5. E5: 의도 분류 + 조정 파싱

**용도**: 사용자의 자연어 조정 요청을 구조화된 overrides JSON으로 변환.

**트리거**: E4에서 조정 의도 감지 시.

**입력**:
```json
{
  "user_message": "ROIC 기준 20%로 올리고 성장 지표 더 보게 해줘",
  "current_preset": {...},
  "current_metrics_list": [...]
}
```

**출력**:
```python
class AdjustmentOverride(BaseModel):
    intent_type: str  # "threshold_change" | "tier_change" | "exclude_stock" | "change_comparison_group" | "unknown"
    description_for_user: str  # 확인 카드에 표시할 자연어 설명
    overrides: dict   # 구조화된 조정 내용 (intent_type별 다름)
    confidence: float # 0~1, 파싱 확신도

class AdjustmentIntent(BaseModel):
    detected_overrides: list[AdjustmentOverride]
    needs_clarification: bool
    clarification_question: str = ""
```

**예시 overrides**:
```python
# threshold_change
{
    "intent_type": "threshold_change",
    "overrides": {"metric_id": "roic", "new_threshold": 0.20},
    "description_for_user": "ROIC 임계값을 15%에서 20%로 상향"
}

# tier_change
{
    "intent_type": "tier_change",
    "overrides": {"metric_id": "revenue_growth_yoy", "from_tier": "context", "to_tier": "supporting"},
    "description_for_user": "매출 성장률을 Context → Supporting으로 승격"
}

# exclude_stock
{
    "intent_type": "exclude_stock",
    "overrides": {"stock_symbol": "NVDA", "exclude_from_metric": "peg_ratio"},
    "description_for_user": "NVDA를 PEG 평가에서 제외 (이번 분석 한정)"
}
```

### 3-6. E6: 조정 후 해설

**용도**: 조정된 분석 재실행 후, 원본 대비 변화 해설.

**트리거**: 조정된 AnalysisRun 완료.

**입력**:
```json
{
  "original_analysis": {...},
  "adjusted_analysis": {...},
  "applied_overrides": [...]
}
```

**출력**:
```python
class AdjustmentComparison(BaseModel):
    key_changes: list[str]        # 주요 변화 포인트 3~5개
    summary: str                  # 전체 요약
    implication_for_user: str     # 사용자에게 의미
```

**예시**:
```json
{
  "key_changes": [
    "강점 구성 변화: ROIC 중심 → ROIC + 성장 지속성 중심",
    "LLY, MSFT가 새 강점으로 부각",
    "INTC는 여전히 약점이며 오히려 두드러짐"
  ],
  "summary": "ROIC 기준을 올리고 성장을 중시하자, 퀄리티 + 성장 복합 종목이 부각됩니다.",
  "implication_for_user": "현재 포트폴리오는 Buffett보다 Quality Growth 프리셋에 더 가까울 수 있습니다. Quality Growth 프리셋으로도 한 번 분석해보시는 것을 추천합니다."
}
```

---

## 4. 컨텍스트 전략 B3 (4-Tier)

### 4-1. Tier 구조 전체 개요

```
┌─ Tier 0: System Prompt (영구 고정) ─────┐
│ - Coach 정체성                         │
│ - 역할 경계                            │
│ - 용어 정의 (PV3)                      │
│ - 문체 원칙                            │
│ - 출력 포맷 규칙                       │
└────────────────────────────────────────┘
              ↓
┌─ Tier 1: Current Conversation ────────┐
│ - 최근 10~15턴 대화 원본               │
│ - 사용자 메시지 + Coach 응답            │
└────────────────────────────────────────┘
              ↓
┌─ Tier 2: Session Summary ─────────────┐
│ - 현재 세션의 이전 대화 요약            │
│ - 10턴 이상 쌓이면 LLM 요약 생성        │
│ - 요약 후 Tier 1에서 제거              │
└────────────────────────────────────────┘
              ↓
┌─ Tier 2.5: Current Analysis Context ──┐
│ - 분석 중인 Portfolio 결과             │
│ - 진단 카드, 강점/약점, 지표별 결과    │
│ - Wallet 배경 메타데이터                │
│ - 수익률 breakdown (RV1-b, RV4-b)      │
│ - (Phase 2 슬롯: Watchlist, Thesis 등)  │
└────────────────────────────────────────┘
              ↓
┌─ Tier 3: User Profile ────────────────┐
│ - 사용자 성향, 프리셋 선호, 과거 패턴  │
│ - D3 Decision 집계로 생성              │
│ - 주기적 업데이트                       │
└────────────────────────────────────────┘
```

### 4-2. Tier 0: System Prompt

**내용**:
- Coach 정체성 선언
- 역할 경계 (preset-design-v3.1.md §1-3)
- **용어 정의 블록 (PV3)** — §7 상세
- 문체 원칙 (preset-design-v3.1.md §7-3)
- 출력 포맷 규칙 (JSON 스키마별)

**변경 빈도**: 낮음. 변경 시 `prompt_version` bump.

**토큰 추정**: 1,500~2,000 토큰.

### 4-3. Tier 1: Current Conversation

**내용**: 최근 10~15턴 대화 원본.

**포맷**:
```json
[
  {"role": "user", "content": "..."},
  {"role": "assistant", "content": "..."},
  ...
]
```

**관리 규칙**:
- 15턴 초과 시 가장 오래된 5턴을 Tier 2로 요약 이동
- 토큰 효율 고려 (턴당 평균 200 토큰 가정 시 최대 3,000 토큰)

### 4-4. Tier 2: Session Summary

**내용**: 현재 세션의 이전 대화 요약.

**생성 시점**:
- Tier 1이 15턴을 넘을 때 (임계값)
- 세션 종료 시 최종 요약

**포맷**:
```json
{
  "session_id": "...",
  "summary_text": "사용자는 Tech 성장주 포트폴리오를 Buffett 프리셋으로 분석. INTC의 ROIC 하락에 대해 질문했고, GARP으로 프리셋 전환 요청 후 비교. 현재 ROIC 기준 상향 조정을 고려 중.",
  "key_decisions": ["preset_switched", "roic_threshold_considered"],
  "unresolved_questions": ["INTC 매도 여부 결정 전"]
}
```

**생성 진입점**: 별도 프롬프트로 LLM 호출 (여기서는 E7로 분류하지 않음, MVP의 보조 기능).

**토큰 추정**: 200~500 토큰.

### 4-5. Tier 2.5: Current Analysis Context

**내용**: 현재 분석 결과 + Wallet 배경 + (Phase 2 슬롯).

**전체 Pydantic 스키마**:
```python
class AnalysisTargetPortfolioContext(BaseModel):
    portfolio_id: str
    portfolio_name: str | None           # None이면 일회성
    preset_id: str
    preset_name: str
    holdings_summary: list[HoldingSummary]
    core_metric_results: list[MetricResult]
    supporting_metric_results: list[MetricResult]
    context_metric_results: list[MetricResult]
    strengths: list[StrengthWeakness]
    weaknesses: list[StrengthWeakness]
    diagnostic_cards: list[DiagnosticCard]
    return_breakdown: ReturnBreakdownWithTime  # RV4-b 구조

class WalletBackgroundContext(BaseModel):
    wallet_id: str
    total_holdings_count: int
    excluded_from_this_portfolio_count: int  # Wallet에 있지만 Portfolio에 없는 종목 수
    sector_distribution: dict[str, float]
    industry_distribution: dict[str, float]
    total_value_estimate: str  # "high" | "mid" | "low" bucket
    return_breakdown: ReturnBreakdownWithTime
    # A1 시계열 확장
    historical_snapshots_available: int
    notable_recent_changes: list[str]

class AnalysisContext(BaseModel):
    analysis_target_portfolio: AnalysisTargetPortfolioContext
    wallet_background: WalletBackgroundContext
    # Phase 2 확장 슬롯 (MVP는 비어있음)
    watchlist_context: dict | None = None
    monitoring_indicators_context: dict | None = None
    thesis_notes_context: dict | None = None
```

**토큰 추정**: 3,000~5,000 토큰 (분석 복잡도 따라).

### 4-6. Tier 3: User Profile

**내용**: 사용자의 장기 성향 요약.

**Pydantic 스키마**:
```python
class UserProfile(BaseModel):
    user_id: str
    last_updated: str
    investment_style_summary: str        # 자연어 요약 (예: "고성장 테크 선호, 집중 투자 성향")
    preferred_presets: list[str]         # 자주 사용한 프리셋 preset_id
    typical_portfolio_structure: dict    # 통상 holding_count, sector_distribution 등
    decision_patterns: list[str]         # D3 Decision에서 추출한 패턴
    risk_appetite_indicator: str         # "aggressive" | "moderate" | "conservative"
    sensitivities: list[str]             # "PEG에 덜 민감", "분산 투자 선호" 등 주목할 특징
```

**생성 방법** (§6 상세):
- 새 사용자는 Tier 3 비어 있음
- D3 Decision이 일정량 쌓이면 LLM이 UserProfile 생성
- 이후 주기적으로 (월 1회 또는 Decision 5건 추가 시) 재생성

**토큰 추정**: 300~600 토큰.

### 4-7. Tier 전체 토큰 합계 추정

| Tier | 최소 | 최대 |
|---|---|---|
| Tier 0 | 1,500 | 2,000 |
| Tier 1 | 0 (대화 없으면) | 3,000 |
| Tier 2 | 0 | 500 |
| Tier 2.5 | 3,000 | 5,000 |
| Tier 3 | 0 (신규 사용자) | 600 |
| **합계** | **4,500** | **11,100** |

Claude 3.5 Sonnet/Haiku, GPT-4o 등 모던 LLM의 컨텍스트 윈도우(128K~200K) 관점에서 여유 충분.

비용 관점: 입력 토큰 1만 토큰 × 호출당 비용. E4 대화 빈번한 경우 일일 비용 관리 필요.

---

## 5. 대화형 기능 설계

### 5-1. 레벨 1 조정 UX

병진 결정: 레벨 1만 MVP. 조정은 현재 분석에만 적용, 저장 없음.

**흐름**:
```
사용자: "ROIC 기준을 20%로 올려서 다시 봐줘"
  ↓
E4: 조정 의도 감지
  ↓
E5: 조정 파싱 → AdjustmentOverride 생성
  ↓
UI: 확인 카드 표시
┌─────────────────────────────────┐
│ 🔄 이번 분석에 아래 조정을 적용할까요? │
│                                   │
│ • ROIC 임계값: 15% → 20%          │
│                                   │
│ 참고: 이 조정은 이번 분석에만 적용됩니다. │
│                                   │
│ [실행]  [취소]                     │
└─────────────────────────────────┘
  ↓
사용자 "실행" 클릭
  ↓
새 AnalysisRun (overrides JSON 포함) 실행
  ↓
결과 표시 + E6: 조정 후 해설 자동 생성
  ↓
Coach 대화창에 비교 해설 출력
```

**저장 없음**:
- 조정은 `AnalysisRun.overrides_json`에 기록
- 다음 분석 실행 시 자동 초기화 (original preset 기준)
- 사용자가 "이 조정이 마음에 들어"라고 해도 MVP는 저장 불가

**Phase 2로 이연되는 것**:
- 레벨 2: 세션 스코프 조정 지속
- 레벨 3: 영구 커스텀 프리셋

### 5-2. 조정 범위 (결정 확인3)

다음 조정이 MVP에서 지원됨:

| 조정 유형 | 예시 |
|---|---|
| 프리셋 임계값 변경 | "ROIC 20%로" |
| 프리셋 tier 변경 | "성장 지표를 Supporting으로" |
| 특정 종목 제외 | "NVDA는 PEG 평가에서 빼줘" |
| 비교군 변경 | "섹터 대신 유니버스 기준으로" |

**E5 파싱의 불확실성 대응**:
- `confidence < 0.7`이면 확인 질문 ("ROIC 임계값 20%로 올리시려는 건가요, 아니면 20% 이상만 통과시키시려는 건가요?")
- 명확한 의도 확인 후 실행

### 5-3. 대화 저장 (결정 D3 raw)

모든 사용자 메시지 + Coach 응답은 `Message` 모델에 raw로 저장.

```python
class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey("ChatSession", on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=[("user", "User"), ("assistant", "Assistant")])
    content = models.TextField()
    metadata = models.JSONField(
        default=dict,
        help_text="예: 조정 요청 시 overrides_json, 진단 카드 생성 시 cards_json"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["session", "created_at"])]


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="chat_sessions")
    analysis_run = models.ForeignKey(
        AnalysisRun, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="chat_sessions",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    session_summary = models.TextField(
        blank=True,
        help_text="Tier 2 요약. 세션 종료 시 생성.",
    )

    class Meta:
        indexes = [
            models.Index(fields=["user", "-started_at"]),
            models.Index(fields=["analysis_run"]),
        ]
```

**세션 정의**: 하나의 AnalysisRun에 연결된 대화 = 하나의 ChatSession. 다른 Portfolio 열거나 새 분석 실행 시 새 세션.

### 5-4. 대화 지속성 (결정 확인5-a)

Saved Analysis 재방문 시 당시 대화도 함께 재현.

**DB 구조**:
- `ChatSession.analysis_run` FK로 결합
- Saved Analysis 열람 시 관련 ChatSession 로드

**UI**:
- 분석 결과 영역 + 대화 영역 함께 표시
- "이전 대화" 접어두기 가능

---

## 6. 의사결정 이력 (결정 D3)

### 6-1. 하이브리드 구조

- **raw**: 모든 대화 + 조정 이력 원본 (§5-3 Message 모델)
- **extracted**: 구조화된 Decision 추출 (LLM 배치)

### 6-2. Decision 모델

```python
class Decision(models.Model):
    """
    사용자의 의사결정 이벤트.
    Chat 대화 또는 명시적 액션에서 LLM이 추출.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="decisions")
    decision_type = models.CharField(
        max_length=40,
        choices=[
            ("preset_adjustment", "Preset Adjustment (Level 1)"),
            ("preset_switch", "Preset Switch"),
            ("holding_change_intent", "Holding Change Intent"),
            ("thesis_note", "Thesis Note (Wallet Holding)"),
            ("portfolio_creation", "Portfolio (Analysis Group) Creation"),
            ("preference_signal", "Preference Signal (Subjective)"),
        ],
    )
    decision_at = models.DateTimeField()
    context_analysis_run = models.ForeignKey(
        AnalysisRun, on_delete=models.SET_NULL, null=True, blank=True,
    )
    rationale_text = models.TextField(
        help_text="사용자가 남긴 자연어 근거 또는 LLM이 대화에서 추출한 요약.",
    )
    structured_payload = models.JSONField(
        help_text=(
            "의사결정 유형별 구조화 데이터. "
            "예: preset_adjustment 이면 {metric_id, old_threshold, new_threshold}"
        ),
    )
    source_messages = models.JSONField(
        default=list,
        help_text="추출 출처 Message UUID 리스트.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-decision_at"]),
            models.Index(fields=["decision_type"]),
        ]
```

### 6-3. Decision 추출 배치

**트리거**: 세션 종료 시 + (선택) 주기 배치.

**로직**:
```python
def extract_decisions_from_session(session: ChatSession) -> list[Decision]:
    """
    세션 종료 시 호출.
    Message 로그를 LLM에 전달 → Decision 추출.
    """
    messages = session.messages.order_by("created_at")

    # LLM 프롬프트: "다음 대화에서 사용자의 의사결정 이벤트를 추출해주세요"
    # - 프리셋 조정, 프리셋 전환, 종목 추가/제거 의도, 사용자 취향 신호 등
    extracted = call_llm_for_decision_extraction(
        messages=messages,
        context_analysis=session.analysis_run,
    )

    # Decision 레코드 생성
    decisions = []
    for item in extracted:
        decision = Decision.objects.create(
            user=session.user,
            decision_type=item.decision_type,
            decision_at=item.decision_at,
            context_analysis_run=session.analysis_run,
            rationale_text=item.rationale,
            structured_payload=item.payload,
            source_messages=item.source_message_ids,
        )
        decisions.append(decision)

    return decisions
```

**비용 관리**:
- 세션에 의사결정 이벤트로 보이는 게 없으면 스킵 (heuristic으로 pre-filter)
- 세션당 1회 호출

---

## 7. 사용자 프로필 전략 (Tier 3 상세)

### 7-1. 프로필 생성 시점

- 신규 사용자: 프로필 없음. Tier 3은 빈 상태로 주입.
- Decision 10건 이상 누적 시 최초 프로필 생성
- 이후 Decision 5건 추가마다 또는 월 1회 재생성

### 7-2. 프로필 생성 프롬프트 (배치)

```
입력:
  - 사용자의 최근 Decision 레코드들
  - 과거 AnalysisRun 메타데이터 (preset, 날짜, 구성)
  - 기존 UserProfile (있으면)

출력 (JSON):
  - investment_style_summary: 자연어 1~2 문장
  - preferred_presets: top 3 preset_id
  - typical_portfolio_structure: 통상 holding_count, sector 분포
  - decision_patterns: 2~5개 패턴 (예: "약세장에서 방어적 조정 선호")
  - risk_appetite_indicator
  - sensitivities: 2~5개

프롬프트 톤: 관찰 중심, 단정 지양
```

### 7-3. 프로필 투명성

사용자에게 프로필을 볼 수 있는 UI 제공:

```
설정 > Coach가 이해한 나

투자 성향: 고성장 테크 선호, 집중 투자 경향
자주 쓰는 프리셋: Buffett Quality Value, GARP, Quality Growth
주목할 패턴:
  - PEG 지표에 덜 민감 (NVDA에 대한 일관된 보유 의지)
  - 대화 중 "확신" 키워드 빈번
  - 밸류에이션보다 성장·모멘텀 중시

[편집]  [초기화]
```

**이유**:
- 잘못된 프로필 고착화 방지 (사용자가 직접 수정 가능)
- 투명성으로 락인 + 신뢰 증가

### 7-4. Coach가 프로필을 사용하는 방식

Tier 3은 **응답 기조 설정**용. 직접 인용하지 않고 tone에만 반영.

시스템 프롬프트에 명시:
```
- Tier 3 UserProfile은 사용자의 성향을 파악하기 위한 배경입니다.
- "당신은 ___한 사람이시네요"처럼 프로필을 직접 인용하지 마세요.
- 대신 응답의 어조, 강조점, 제안 내용을 프로필에 맞춰 조정하세요.
- 예: risk_appetite="aggressive"면 "이 리스크는 관리 가능합니다"보다
  "이 리스크는 주목해야 합니다"로 톤 전환.
```

---

## 8. LLM 혼동 방지 (PV3 + 부분 PV5)

### 8-1. 배경

`Wallet`과 `Portfolio`의 의미가 LLM 훈련 관용과 다름. LLM이 Portfolio를 "전체 보유"로 해석할 위험 존재.

### 8-2. PV3 방어 — 자기설명 필드명 + 정의 블록

**LLM 입력 JSON 필드명 규칙**:
- `analysis_target_portfolio`: 분석 대상 Portfolio (Wallet의 서브셋)
- `wallet_all_holdings`: Wallet 전체 (자산 지갑의 모든 종목)
- `wallet_background`: Wallet 배경 메타데이터 (집계 지표)
- `excluded_from_this_portfolio`: Wallet에 있지만 Portfolio에 없는 종목

**시스템 프롬프트 용어 정의 블록 (Tier 0)**:

```
TERMINOLOGY DEFINITIONS (STRICT - OVERRIDES ANY TRAINING ASSUMPTIONS):

- wallet_all_holdings (or "the user's wallet", "자산 지갑"):
  The complete set of stocks the user owns. Includes items selected
  AND excluded from current analysis.

- analysis_target_portfolio (or "the portfolio", "분석 포트폴리오"):
  A SUBSET of wallet holdings selected for THIS specific analysis session.
  NOT the user's entire holdings. 
  This is what "your portfolio" refers to in conversation with this user.

- When the user says "my portfolio" (in Korean "내 포트폴리오"),
  they mean analysis_target_portfolio, NOT the wallet.
  If they want wallet-wide information, they explicitly ask about
  "my wallet" or "all my holdings" ("내 자산 지갑", "모든 보유").

- wallet_background is BACKGROUND CONTEXT only.
  Do NOT proactively discuss wallet holdings excluded from the current
  portfolio unless:
    (a) user explicitly asks about the wallet, or
    (b) the exclusion is directly relevant to a diagnostic point.

- In conversation, feel free to use the Korean word "포트폴리오" naturally,
  but always with the meaning of analysis_target_portfolio.
```

### 8-3. PV3 자연어 출력 방식

Coach가 사용자에게 응답할 때:
- "당신의 포트폴리오는..." = `analysis_target_portfolio` 지칭 (자연스러움)
- "당신의 자산 지갑은..." = `wallet` 지칭 (명시적)
- "분석에서 제외된 종목들은..." = `excluded_from_this_portfolio` 지칭

### 8-4. MVP 진입점별 Wallet 맥락 주입 정도

| 진입점 | wallet_background 포함 |
|---|---|
| E1 (한 줄 진단) | 최소 (total_holdings_count만) |
| E2 (진단 카드) | 최소 (excluded 여부만) |
| E3 (지표 코멘트) | 포함 안 함 |
| E4 (대화) | 전체 (return_breakdown 포함) |
| E5 (조정 파싱) | 포함 안 함 |
| E6 (조정 해설) | 최소 |

E4만 wallet 전체 배경 사용. 다른 진입점은 Portfolio 중심으로 한정.

이 전략은 **PV5의 일부 적용**: 대부분 진입점은 Wallet 정보 없이 동작 → 구조적으로 혼동 가능성 제거.

---

## 9. Wallet 분석 범위 (W2.5 + A1)

### 9-1. MVP에서 지원되는 Wallet 분석

- **시나리오 A (시계열 변화)**: WalletSnapshot 기반
- **시나리오 B (배경 대조)**: `wallet_background` Tier 2.5 필드
- **시나리오 C (후보 추천)**: 제외 (Phase 2)

### 9-2. 시계열 활용 (시나리오 A, A1)

Tier 2.5의 `wallet_background`에 시계열 요약:
```json
{
  "wallet_background": {
    ...,
    "historical_snapshots_available": 4,
    "notable_recent_changes": [
      "Tech 비중 40% → 55% (last 3 months)",
      "ABC 신규 편입",
      "XYZ 매도"
    ]
  }
}
```

Coach의 활용:
- "Tech 비중이 최근 늘어나셨는데, 이번 Portfolio도 Tech 중심입니다. 집중도에 주의할 필요가 있습니다."

### 9-3. 배경 대조 (시나리오 B)

Coach가 Portfolio 분석 중 Wallet 전체와 대조:
- "당신의 자산 지갑 전체 수익률은 +8%인데, 이 Tech 성장주 포트폴리오만 보면 +15%입니다. 다른 포지션이 성과를 희석하고 있습니다."

### 9-4. 제외된 시나리오 C

MVP에서는 Coach가 Wallet에서 자발적으로 Portfolio 후보를 추천하지 않음. 사용자가 직접 체크박스 UI에서 구성.

Phase 2에 도입 시:
- 새 진입점 E10 설계 필요
- Coach가 "이런 묶음을 분석해보시는 건 어때요?" 제안

---

## 10. 향후 확장 (Phase 2)

### 10-1. 추가 진입점

| # | 이름 | 용도 |
|---|---|---|
| E7 | 사후 비교 해설 | 시점 A/B Saved Analysis 비교 |
| E8 | 의사결정 추출 | 세션 종료 배치 (6-3에서 설명한 것의 공식화) |
| E9 | 프로필 생성/업데이트 | 주기 배치 (7-2에서 설명한 것의 공식화) |
| E10 | Portfolio 후보 추천 | Wallet 분석 시나리오 C |
| E11 | Watchlist 제안 | Watchlist 모델 도입 후 |
| E12 | 모니터링 지표 추천 | Thesis Control 통합 후 |

### 10-2. 조정 수준 확장

- 레벨 2: 세션 스코프 조정 지속
- 레벨 3: 영구 커스텀 프리셋 (`CustomPreset` 모델)

### 10-3. 컨텍스트 전략 확장

- B3 → B4: retrieval 추가 (pgvector)
- Tier 3 프로필 품질 개선 (주기 배치 → 실시간 업데이트)

---

## 11. 확정 결정 목록

이 문서에 반영된 결정:

| # | 결정 | 내용 |
|---|---|---|
| A2 | MVP 대화 깊이 | Q&A + 레벨 1 조정 |
| B3 | 컨텍스트 전략 | 4-Tier 계층적 요약 (retrieval 없음) |
| C1 | 사후분석 기준 시점 | 수동 저장 (C1) |
| D3 | 의사결정 이력 스키마 | raw + 구조화 추출 |
| 확인1 | 분석 실행 트리거 | 프리셋 선택 후 즉시 |
| 확인2 | 조정 UX | 확인 카드 → 실행 |
| 확인3 | 조정 범위 | 프리셋/종목/비교군 전부 |
| 확인4 | MVP 진입점 범위 | E1~E6 |
| 확인5 | 대화 지속성 | Saved Analysis에 대화 포함 재현 |
| PV3 | LLM 혼동 방지 | 정의 블록 + 자기설명 필드명 |
| (부분 PV5) | 진입점별 Wallet 정보 주입 | E1~E3, E5~E6은 최소, E4는 전체 |
| W2.5 | Wallet 분석 범위 | 시나리오 A+B (C는 Phase 2) |
| A1 | Wallet 시계열 구현 | WalletSnapshot (주기 배치 없음) |

---

## 12. 남은 작업 / 다음 세션 예정

### 12-1. 이번 문서화의 위치

세션 D의 결정 사항 문서화 완료. 실제 프롬프트 작성은 다음 세션들에 걸쳐 진행.

### 12-2. 다음 세션 로드맵

| 세션 | 작업 |
|---|---|
| D-0a | 데이터 모델 리팩토링 (Wallet/Portfolio/WalletSnapshot) |
| D-0b | Tier 2.5 Pydantic 스키마 완성 (Analysis Context 전체) |
| D-1 | Tier 0 시스템 프롬프트 (정체성 + 정의 블록) |
| D-2 | E1 한 줄 진단 프롬프트 |
| D-3 | E2 진단 카드 프롬프트 |
| D-4 | E3 지표 코멘트 프롬프트 |
| D-5 | E4 대화 Q&A 프롬프트 |
| D-6 | E5 조정 파싱 프롬프트 |
| D-7 | E6 조정 해설 프롬프트 |
| D-8 | 통합 검증 + 예시 시나리오 end-to-end 테스트 |

**총 예상**: 9세션. 필요 시 일부 통합 가능.

---

## 13. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판 — 세션 D Coach LLM 결정 전체 문서화. E1~E6 정의, 4-Tier 전략, D3 의사결정, PV3 혼동 방지 전략 반영. |
