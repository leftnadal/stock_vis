# D-0b Instructions: Pydantic Schemas for Tier 2.5 Analysis Context

> **세션**: D-0b
> **목적**: Coach LLM의 Tier 2.5(현재 분석 컨텍스트) Pydantic 스키마 완성
> **전제 세션**: D-0a 완료 (Wallet/Portfolio 모델 확정)
> **대상 에이전트**: Claude Code
> **버전**: v1.0 (2026-04-20)

---

## 0. 에이전트가 먼저 읽을 것

**필수 참조**:
1. `docs/portfolio/design/coach-llm-design-v1.md` — §4-5 Tier 2.5 스키마 구조 (가장 중요)
2. `docs/portfolio/design/return-tracking-design-v1.md` — §3-1 ReturnBreakdown, §4~5 시간 차원
3. `docs/portfolio/design/wallet-portfolio-architecture-v1.md` — §3 데이터 모델 (필드 참조)
4. `docs/portfolio/implementation/models.py` — D-0a 결과물 (Wallet, Portfolio 등 신규 모델)

---

## 1. 목표

LLM 진입점 E1~E6에 전달할 **Tier 2.5 컨텍스트의 Pydantic 스키마**를 완성한다.

### 1-1. 완료 시점의 산출물

신규 파일: `docs/portfolio/implementation/schemas/__init__.py` + 7개 모듈

```
implementation/
├── models.py                 (D-0a 결과)
├── schemas/                  ★ NEW
│   ├── __init__.py
│   ├── holding.py            (HoldingSummary)
│   ├── metric_result.py      (MetricResult, StrengthWeakness)
│   ├── diagnostic.py         (DiagnosticCard)
│   ├── return_breakdown.py   (ReturnBreakdown, ContributionItem, CategoryBreakdown)
│   ├── analysis_context.py   (AnalysisContext 최상위)
│   ├── user_profile.py       (UserProfile - Tier 3)
│   └── llm_outputs.py        (E1~E6 출력 스키마)
└── metrics/definitions/ ...
```

### 1-2. 이 지시서 범위

- Pydantic v2 문법 사용
- Tier 2.5의 입력 스키마 + E1~E6 출력 스키마
- 직렬화/역직렬화 헬퍼 포함 (`.model_dump()`, `.model_validate()`)

### 1-3. 제외 범위

- Tier 0/1/2/3 스키마 (각각 별도 세션에서)
- LLM 호출 로직 (D-1 이후)
- 실제 데이터 채우기 (ReturnCalculator 구현은 별도)

---

## 2. 사전 조건

- [x] D-0a 완료: Wallet, WalletHolding, Portfolio, WalletSnapshot, AnalysisRun, ChatSession, Message, Decision 모델 생성됨
- [x] Pydantic v2 설치 환경 (`pydantic>=2.0`)
- [x] Python 3.10+ (`|` 타입 힌트, `StrEnum` 사용 가능)

---

## 3. 작업 스코프

### 3-1. In Scope

- Pydantic v2 모델 정의 (BaseModel, Field, ConfigDict)
- Decimal 처리 (`from decimal import Decimal`)
- datetime ISO 직렬화
- Enum 정의 (ScopeType, Severity, StructuralOrSingle 등)
- Forward reference 해결 (CategoryBreakdown 재귀 구조)
- 각 스키마에 예시 JSON 주석 포함

### 3-2. Out of Scope

- 스키마 → Django 모델 변환 로직 (별도 유틸 파일)
- JSON Schema export (Pydantic이 자동 제공, 별도 코드 불필요)
- 테스트 코드 (별도 세션)

---

## 4. 단계별 작업 명세

### Step 1: `schemas/__init__.py` 생성

**내용**: 7개 모듈의 주요 클래스 re-export

```python
"""
Stock-Vis Pydantic Schemas for LLM Tier 2.5 Context.

Usage:
    from portfolio.schemas import AnalysisContext, ReturnBreakdown
"""

from .holding import HoldingSummary
from .metric_result import MetricResult, StrengthWeakness, MetricTier
from .diagnostic import DiagnosticCard, Severity, StructuralOrSingle
from .return_breakdown import (
    ReturnBreakdown, ReturnBreakdownWithTime,
    ContributionItem, CategoryBreakdown, ScopeType,
)
from .analysis_context import (
    AnalysisContext,
    AnalysisTargetPortfolioContext,
    WalletBackgroundContext,
)
from .user_profile import UserProfile
from .llm_outputs import (
    OneLineDiagnosis,          # E1
    DiagnosticCards,           # E2
    MetricComment, MetricComments,  # E3
    ConversationResponse,      # E4
    AdjustmentOverride, AdjustmentIntent,  # E5
    AdjustmentComparison,      # E6
)

__all__ = [
    "HoldingSummary",
    "MetricResult", "StrengthWeakness", "MetricTier",
    "DiagnosticCard", "Severity", "StructuralOrSingle",
    "ReturnBreakdown", "ReturnBreakdownWithTime",
    "ContributionItem", "CategoryBreakdown", "ScopeType",
    "AnalysisContext",
    "AnalysisTargetPortfolioContext",
    "WalletBackgroundContext",
    "UserProfile",
    "OneLineDiagnosis", "DiagnosticCards",
    "MetricComment", "MetricComments",
    "ConversationResponse",
    "AdjustmentOverride", "AdjustmentIntent",
    "AdjustmentComparison",
]
```

### Step 2: `schemas/holding.py` 작성

**클래스**: `HoldingSummary`

**필드**:
- `holding_id`: `str` (UUID)
- `stock_symbol`: `str`
- `stock_name`: `str`
- `sector`: `str | None`
- `industry`: `str | None`
- `shares`: `Decimal`
- `weight`: `Decimal` (0~1, 포트폴리오 내 비중)
- `market_value`: `Decimal`
- `unrealized_return`: `Decimal` (-1~∞)
- `investment_thesis`: `str | None`

**설계 근거**: coach-llm-design-v1.md §4-5 Tier 2.5 구조 중 `holdings_summary` 항목

### Step 3: `schemas/metric_result.py` 작성

**클래스 3개**: `MetricTier` (StrEnum), `MetricResult`, `StrengthWeakness`

**MetricTier**:
```python
class MetricTier(StrEnum):
    CORE = "core"
    SUPPORTING = "supporting"
    CONTEXT = "context"
```

**MetricResult**:
- `metric_id`: `str`
- `metric_display_name`: `str`
- `tier`: `MetricTier`
- `value`: `Decimal | None`
- `percentile`: `Decimal | None` (0~1, 전체 유니버스/섹터 내 위치)
- `percentile_scope`: `str` ("universe" | "sector" | "industry")
- `level_tag`: `str` ("excellent" | "good" | "moderate" | "weak" | "critical")
- `threshold_applied`: `Decimal | None`
- `passed_threshold`: `bool | None`

**StrengthWeakness**:
- `metric_id`: `str`
- `metric_display_name`: `str`
- `level_tag`: `str`
- `rank_within_portfolio`: `int` (1부터 시작)
- `reason_hint`: `str` (예: "상위 5% 달성", "임계값 미달")

### Step 4: `schemas/diagnostic.py` 작성

**클래스 3개**: `Severity` (StrEnum), `StructuralOrSingle` (StrEnum), `DiagnosticCard`

**Severity**:
```python
class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

**StructuralOrSingle**:
```python
class StructuralOrSingle(StrEnum):
    STRUCTURAL = "structural"
    SINGLE_OUTLIER = "single_outlier"
```

**DiagnosticCard** (coach-llm-design-v1.md §3-2의 4요소):
- `weakness_metric_id`: `str`
- `what_is_wrong`: `str` (팩트 진술, 1~2문장)
- `comparison_basis`: `str` (비교 기준 명시, 1문장)
- `why_it_matters`: `str` (프리셋 철학 연결, 1~2문장)
- `caveat_or_exception`: `str` (예외/트레이드오프, 1문장)
- `severity`: `Severity`
- `structural_or_single`: `StructuralOrSingle`

### Step 5: `schemas/return_breakdown.py` 작성

**설계 근거**: return-tracking-design-v1.md §3-1

**클래스 5개**: `ScopeType` (StrEnum), `ContributionItem`, `CategoryBreakdown`, `ReturnBreakdown`, `ReturnBreakdownWithTime`

**ScopeType**:
```python
class ScopeType(StrEnum):
    PORTFOLIO = "portfolio"
    WALLET = "wallet"
```

**ContributionItem**:
- `name`: `str`
- `weight`: `Decimal`
- `return_rate`: `Decimal`
- `contribution_pp`: `Decimal`

**CategoryBreakdown** (재귀 구조):
- `name`: `str`
- `weight`: `Decimal`
- `return_rate`: `Decimal`
- `contribution_pp`: `Decimal`
- `children`: `list["CategoryBreakdown"]` (default_factory=list) — 하위 카테고리
- `holdings`: `list[ContributionItem]` (default_factory=list) — 리프 레벨 종목

**주의**: Pydantic v2에서 self-referential은 `model_rebuild()` 호출 필요할 수 있음.

**ReturnBreakdown**:
- `scope_type`: `ScopeType`
- `scope_id`: `str`
- `calculated_at`: `datetime` (ISO 8601 직렬화)
- `total_return`: `Decimal`
- `total_value`: `Decimal`
- `total_cost_basis`: `Decimal`
- `by_sector`: `list[CategoryBreakdown]`
- `top_contributors`: `list[ContributionItem]` (최대 5)
- `bottom_contributors`: `list[ContributionItem]` (최대 5)

**ReturnBreakdownWithTime** (RV4-b):
- `at_save_time`: `ReturnBreakdown | None` (Saved Analysis 아니면 None)
- `current`: `ReturnBreakdown`
- `delta_since_save`: `dict | None` — 저장 시점 대비 변화 (total_return_change_pp, period_days)

### Step 6: `schemas/analysis_context.py` 작성

**설계 근거**: coach-llm-design-v1.md §4-5 전체

**클래스 3개**: `AnalysisTargetPortfolioContext`, `WalletBackgroundContext`, `AnalysisContext`

**AnalysisTargetPortfolioContext**:
- `portfolio_id`: `str`
- `portfolio_name`: `str | None` (임시 그룹이면 None)
- `preset_id`: `str`
- `preset_name`: `str`
- `preset_category`: `str` ("value" | "growth" | "income" | "factor" | "special")
- `save_type`: `str` ("named" | "temporary")
- `holdings_summary`: `list[HoldingSummary]`
- `holding_count`: `int`
- `core_metric_results`: `list[MetricResult]`
- `supporting_metric_results`: `list[MetricResult]`
- `context_metric_results`: `list[MetricResult]`
- `strengths`: `list[StrengthWeakness]` (최대 3)
- `weaknesses`: `list[StrengthWeakness]` (최대 3)
- `diagnostic_cards`: `list[DiagnosticCard]` (최대 3)
- `return_breakdown`: `ReturnBreakdownWithTime`
- `overrides_applied`: `dict | None` (E5/E6에서 조정된 분석인 경우)

**WalletBackgroundContext**:
- `wallet_id`: `str`
- `total_holdings_count`: `int`
- `excluded_from_this_portfolio_count`: `int`
- `sector_distribution`: `dict[str, float]` (섹터명 → 비중)
- `industry_distribution`: `dict[str, float]`
- `total_value_estimate`: `str` ("high" | "mid" | "low")
- `return_breakdown`: `ReturnBreakdownWithTime`
- `historical_snapshots_available`: `int` (A1: WalletSnapshot 개수)
- `notable_recent_changes`: `list[str]` (자연어 변화 요약, 최대 5)

**AnalysisContext** (최상위):
- `analysis_target_portfolio`: `AnalysisTargetPortfolioContext`
- `wallet_background`: `WalletBackgroundContext`
- `watchlist_context`: `dict | None` (Phase 2 슬롯, MVP는 None)
- `monitoring_indicators_context`: `dict | None` (Phase 2)
- `thesis_notes_context`: `dict | None` (Phase 2)

**중요: PV3 필드명 일관성**:
- 반드시 `analysis_target_portfolio`, `wallet_background` 이름 사용 (LLM 프롬프트에서 이 이름으로 참조)
- 임의 변경 금지

### Step 7: `schemas/user_profile.py` 작성

**설계 근거**: coach-llm-design-v1.md §4-6, §7

**UserProfile**:
- `user_id`: `str`
- `last_updated`: `datetime | None` (신규 사용자는 None)
- `investment_style_summary`: `str` (자연어 1~2 문장)
- `preferred_presets`: `list[str]` (top 3 preset_id)
- `typical_portfolio_structure`: `dict` (예: `{"avg_holding_count": 8, "dominant_sectors": ["Tech"]}`)
- `decision_patterns`: `list[str]` (2~5개)
- `risk_appetite_indicator`: `str` ("aggressive" | "moderate" | "conservative" | "unknown")
- `sensitivities`: `list[str]` (2~5개)

**Empty 상태 표현**: 신규 사용자의 경우 `UserProfile(user_id=..., last_updated=None, investment_style_summary="", ...)` 형태로 모든 필드 default 값 또는 빈 리스트 허용.

### Step 8: `schemas/llm_outputs.py` 작성

각 진입점의 **출력** 스키마. 상세는 coach-llm-design-v1.md §3-1~§3-6 참조.

**OneLineDiagnosis** (E1):
- `headline`: `str` (25~40자)
- `summary`: `str` (2~3 문장)

**DiagnosticCards** (E2):
- `cards`: `list[DiagnosticCard]` (최대 3)

**MetricComment** + **MetricComments** (E3):
```python
class MetricComment(BaseModel):
    metric_id: str
    one_liner: str  # 1~2 문장

class MetricComments(BaseModel):
    comments: list[MetricComment]
```

**ConversationResponse** (E4):
- `response_text`: `str` (자연어 응답)
- `has_adjustment_intent`: `bool`
- `adjustment_parse_hint`: `str` (조정 의도 감지 시 E5로 넘길 raw 힌트)

**AdjustmentOverride** + **AdjustmentIntent** (E5):
```python
class AdjustmentIntentType(StrEnum):
    THRESHOLD_CHANGE = "threshold_change"
    TIER_CHANGE = "tier_change"
    EXCLUDE_STOCK = "exclude_stock"
    CHANGE_COMPARISON_GROUP = "change_comparison_group"
    UNKNOWN = "unknown"

class AdjustmentOverride(BaseModel):
    intent_type: AdjustmentIntentType
    description_for_user: str  # 확인 카드 표시용 한국어
    overrides: dict           # intent_type별 구조
    confidence: float         # 0~1

class AdjustmentIntent(BaseModel):
    detected_overrides: list[AdjustmentOverride]
    needs_clarification: bool
    clarification_question: str = ""
```

**AdjustmentComparison** (E6):
- `key_changes`: `list[str]` (3~5개)
- `summary`: `str`
- `implication_for_user`: `str`

### Step 9: 예시 JSON 주석 포함

각 스키마 클래스 하단에 사용 예시를 주석으로 포함:

```python
class OneLineDiagnosis(BaseModel):
    headline: str = Field(..., min_length=10, max_length=60)
    summary: str = Field(..., min_length=30, max_length=500)

    # Example:
    # {
    #   "headline": "퀄리티는 견조하나 밸류에이션 부담",
    #   "summary": "GARP 관점에서 당신의 Tech 성장주 포트폴리오는..."
    # }
```

---

## 5. 검증 지점

### 5-1. Import 테스트

```bash
python -c "
from portfolio.schemas import (
    AnalysisContext, ReturnBreakdown, DiagnosticCard,
    OneLineDiagnosis, DiagnosticCards, MetricComments,
    ConversationResponse, AdjustmentIntent, AdjustmentComparison,
    UserProfile, HoldingSummary, StrengthWeakness, MetricResult,
)
print('All imports OK')
"
```

### 5-2. 직렬화/역직렬화 왕복

예시 데이터로 `.model_dump()` → JSON → `.model_validate_json()` 왕복 테스트:

```python
example = AnalysisContext(...)  # 예시 채우기
json_str = example.model_dump_json()
restored = AnalysisContext.model_validate_json(json_str)
assert restored == example
```

### 5-3. Forward reference 해결 확인

`CategoryBreakdown`의 재귀 구조가 Pydantic v2에서 올바르게 동작해야 함:

```python
cb = CategoryBreakdown(
    name="Technology",
    weight=Decimal("0.6"),
    return_rate=Decimal("0.15"),
    contribution_pp=Decimal("0.09"),
    children=[
        CategoryBreakdown(
            name="Semiconductors",
            weight=Decimal("0.6"),
            return_rate=Decimal("0.22"),
            contribution_pp=Decimal("0.132"),
        )
    ]
)
```

### 5-4. PV3 필드명 검증

다음이 정확한지 확인:
- `AnalysisContext.analysis_target_portfolio` (O)
- `AnalysisContext.wallet_background` (O)

절대 사용 금지:
- `AnalysisContext.portfolio`
- `AnalysisContext.wallet`

---

## 6. 에이전트 판단 허용 범위

### 6-1. 허용

- Pydantic Field 상세 옵션 (min_length, max_length, description, examples)
- 주석 추가 (한국어 OK)
- import 순서, PEP 8 포맷

### 6-2. 금지

- 필드명 변경 (특히 PV3 필드명)
- 지시서 밖의 신규 클래스 추가
- `SwalletContext` 같이 클래스명 임의 변경
- `analysis_target_portfolio` → `target_portfolio` 단축

### 6-3. 판단이 어려운 경우

- Pydantic v1 vs v2 문법 충돌 시 **v2 우선**
- Optional 필드의 default 값 애매 시 `None` 우선
- Enum value 대소문자: 모두 **lowercase**

---

## 7. 산출물

**신규 파일**:
- `docs/portfolio/implementation/schemas/__init__.py`
- `docs/portfolio/implementation/schemas/holding.py`
- `docs/portfolio/implementation/schemas/metric_result.py`
- `docs/portfolio/implementation/schemas/diagnostic.py`
- `docs/portfolio/implementation/schemas/return_breakdown.py`
- `docs/portfolio/implementation/schemas/analysis_context.py`
- `docs/portfolio/implementation/schemas/user_profile.py`
- `docs/portfolio/implementation/schemas/llm_outputs.py`

**수정 파일**: 없음

**예상 줄 수**: 파일당 50~150줄, 총 600~1000줄

---

## 8. 완료 보고 포맷

```markdown
# D-0b 완료 보고

## 생성 파일 (8개)
- schemas/__init__.py (N줄)
- schemas/holding.py (N줄)
- ... (이하 모든 파일)

## 주요 스키마 클래스 개수
- Tier 2.5 입력: AnalysisContext, AnalysisTargetPortfolioContext, WalletBackgroundContext, HoldingSummary, MetricResult, StrengthWeakness, DiagnosticCard, ReturnBreakdown, CategoryBreakdown, ContributionItem, ReturnBreakdownWithTime (11개)
- E1~E6 출력: OneLineDiagnosis, DiagnosticCards, MetricComments, ConversationResponse, AdjustmentIntent, AdjustmentOverride, AdjustmentComparison (7개)
- Tier 3: UserProfile (1개)
- Enum: ScopeType, Severity, StructuralOrSingle, MetricTier, AdjustmentIntentType (5개)

## 검증 결과
- [✓] 모든 스키마 import 성공
- [✓] 직렬화 왕복 테스트 통과
- [✓] Forward reference 해결됨
- [✓] PV3 필드명 정확 (analysis_target_portfolio, wallet_background)

## 판단 포인트
- [기록 필요]

## 다음 세션 준비
- D-1: Tier 0 시스템 프롬프트 작성. 이 스키마를 시스템 프롬프트 내 JSON 예시로 사용.
```

---

## 9. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판 |
