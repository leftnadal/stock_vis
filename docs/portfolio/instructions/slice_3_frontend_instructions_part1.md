# Slice 3 — Part 1 작업 지시서 (Step 0~5)

> 작성일: 2026-05-07
> 대상: Stock-Vis Portfolio Coach 슬라이스 3 전반부
> 진입점: **E2 (진단 카드 4요소, D-3 정의)**
> 작업 종류: **글쓰기** (E1과 동일 카테고리, E5 추출과 다름)
> 전제: Slice 2 Part 2 완료, 회귀 76 passed, 누적 호출 32/50 (Step 8 1차 손실 14 별도)
> 브랜치: portfolio
> 누적 LLM 호출: 0 / 50 (Slice 3 진입 시 Reset 적용 — D3.C)

---

## 결정 사항 (최종 확정 9건)

본 지시서는 다음 9개 결정을 모두 반영하여 작성됨.

| Q         | 결정                                                                        | 영향 위치               |
| --------- | --------------------------------------------------------------------------- | ----------------------- |
| Q1        | **진입점 = E2 (진단 카드 4요소)**                                           | 슬라이스 전체           |
| Q3        | **평가 차원 = schema + naturalness + insight + completeness(자동)**         | Step 8 score            |
| Q4 (수정) | **fixture = garp 3개 (Slice 1 재활용) + 신규 4개 = 7개 하이브리드**         | Step 5                  |
| Q5        | **비용 가드 reset 적용 (코드 구현)**                                        | Step 0                  |
| Q6        | **score_step8 일반화 — DIMENSION_LOOKUP[e2] 직접 추가 (delegation 불필요)** | Step 9                  |
| Q7        | **completeness만 자동, LLM-as-judge는 Phase 2**                             | Step 1 schema validator |
| **D2**    | **default provider = haiku (글쓰기 작업)**                                  | Step 6                  |
| **D3**    | **Reset 코드 구현 — CostGuard.reset_slice() 신설**                          | Step 0.5                |
| **A1**    | **Step 8 매트릭스 7×2=14**                                                  | Step 8                  |
| **A2**    | **Step 9 슬롯 = #5 단독, #3+#4는 Step 2 흡수**                              | Step 2 + Step 9         |
| **A3**    | **score 산식 = e1 그대로 + completeness 자동 보강**                         | Step 8 score            |

### Slice 2 결과 매개변수 (상속)

| 매개변수             | 값                                | 영향                                                                  |
| -------------------- | --------------------------------- | --------------------------------------------------------------------- |
| SLICE2_WINNER        | sonnet (추출 작업)                | Slice 3은 글쓰기 → haiku default 정당                                 |
| SLICE2_BUDGET        | 2,000 (E5 token budget)           | E2 budget baseline (Step 7 측정 후 결정)                              |
| SLICE2_TRADEOFF_FREQ | 0.0                               | 가중치 룰 변경 불필요                                                 |
| SLICE2_GENERALIZED   | partial (delegation 방식)         | E2 산식이 e1과 동일 → DIMENSION_LOOKUP 직접 추가로 통합               |
| SLICE2_RESET_APPLIED | false (정책만, 코드 없음)         | Step 0.5에서 코드 구현                                                |
| SLICE2_HAIKU_COST    | $0.0097                           | E2 비용 추정 baseline                                                 |
| SLICE2_SONNET_COST   | $0.0308 (3.17×)                   | Step 8 비용 산정                                                      |
| 1차 손실 원인        | fixture set 필드 JSON 직렬화 실패 | **D4 회피 가이드 — 모든 run 스크립트에 \_json_default 핸들러 의무화** |

---

## 0. 사전 검증

### 0.1 Slice 2 완료 확인

```bash
git rev-parse --abbrev-ref HEAD
# 예상: portfolio

pytest portfolio/tests/ -q
# 예상: 76 passed (Slice 2 종결 baseline)

ls docs/portfolio/coach/slice2/
# 예상: step6_smoke_e5_output.json, step7_e5_token_measurement.json,
#       step8_2way_e5_raw.json, step8_2way_e5_scored.json,
#       validation_report_slice2.md, refactor_backlog_slice2.md, gemini_diagnosis.md
```

### 0.2 환경 사전 검증 (D4 회피 가이드 검증)

```bash
# Slice 1 fixture 무결성 (Slice 3 fixture 일부 재활용)
python -c "
from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_tech, get_context_garp_misfit, get_context_garp_large,
)
print('garp_tech holdings:', len(get_context_garp_tech().analysis_target_portfolio.holdings_summary))
print('garp_misfit holdings:', len(get_context_garp_misfit().analysis_target_portfolio.holdings_summary))
print('garp_large holdings:', len(get_context_garp_large().analysis_target_portfolio.holdings_summary))
"
# 예상: 5 / 5 / 15

# E5 service 인터페이스 (E2 service 작성 시 패턴 참조)
python -c "
from portfolio.services.e5_adjustment_parser import (
    run_e5, build_e5_prompt, PROVIDER_KWARGS,
)
print('PROVIDER_KWARGS:', list(PROVIDER_KWARGS.keys()))
"

# Mock LLMClient text_strategy 등록 상태 확인
python -c "
from portfolio.llm.mocks import MockLLMClient, _MOCK_TEXT_STRATEGIES
print('strategies:', list(_MOCK_TEXT_STRATEGIES.keys()))
"
# 예상: ['e1', 'e5'] (Slice 3 Step 0.6에서 'e2' 추가 예정)

# DIMENSION_LOOKUP 등록 상태
python -c "
from scripts.validation.score_step8 import DIMENSION_LOOKUP
print('entrypoints:', list(DIMENSION_LOOKUP.keys()))
"
# 예상: ['e1', 'e5'] (Slice 3 Step 9에서 'e2' 추가 예정)
```

### 0.3 비용 가드 예산 분배 (Reset 후 50 calls 신규 할당)

| Step                              | 호출 수 | 누적   | 안전 마진 |
| --------------------------------- | ------- | ------ | --------- |
| Slice 3 진입 (Reset 후)           | —       | 0      | 50        |
| Step 0.5 (CostGuard 구현, 호출 0) | 0       | 0      | 50        |
| Step 6 (실 haiku 1회)             | 1       | 1      | 49        |
| Step 7 (오프라인 측정)            | 0       | 1      | 49        |
| Step 8 (7 fixture × 2 model)      | 14      | 15     | 35        |
| Step 8 재시도 예비                | ~3      | ~18    | ~32       |
| Step 9 (리팩토링)                 | 0       | ~18    | ~32       |
| 회귀/디버깅 예비                  | 0~5     | ~18~23 | ~27~32    |

최대 18~23 / 50 (36~46%). 매우 안전한 마진.

---

### 0.4 산출물 디렉토리 신설 (Slice 2 패턴 mirror)

```bash
mkdir -p docs/portfolio/coach/slice3
```

산출물 5건 예상 위치:

```
docs/portfolio/coach/slice3/
├── step6_smoke_e2_output.json
├── step7_e2_token_measurement.json
├── step8_2way_e2_raw.json
├── step8_2way_e2_scored.json
├── validation_report_slice3.md
└── refactor_backlog_slice3.md
```

---

### 0.5 CostGuard 코드 구현 (D3.C 적용 — ~10분)

**목표**: `validation_report_slice2.md §6.3`에서 결정된 Slice 단위 비용 가드 정책을 코드로 구현. 매 슬라이스마다 수동 리셋하지 않도록 자동화.

#### 0.5.1 CostGuard 모듈 신설

`portfolio/llm/cost_guard.py`:

```python
"""LLM 비용 가드. Slice 단위 호출 카운트 + 비용 추적.

Slice 진입 시 reset_slice()로 카운터 0으로 초기화.
record_call()로 매 호출 누적.
exceeded() 또는 데코레이터로 한도 초과 시 LLMBudgetExceededError 발생.

사용 예:
    from portfolio.llm.cost_guard import CostGuard

    guard = CostGuard.get_instance()
    guard.reset_slice("slice3", max_calls=50)
    guard.record_call(cost_usd=0.005, model="claude-haiku-4-5")
    print(guard.status())
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from portfolio.llm.exceptions import LLMBudgetExceededError

logger = logging.getLogger(__name__)


@dataclass
class CallRecord:
    """단일 호출 기록."""
    cost_usd: float
    model: str
    timestamp: str  # ISO format


@dataclass
class CostGuard:
    """싱글톤 패턴. 슬라이스 단위 비용 가드."""
    slice_id: str = "default"
    max_calls: int = 50
    call_count: int = 0
    total_cost_usd: float = 0.0
    records: list[CallRecord] = field(default_factory=list)
    started_at: Optional[str] = None

    _instance: "Optional[CostGuard]" = None
    _lock: "Lock" = Lock()

    @classmethod
    def get_instance(cls) -> "CostGuard":
        """싱글톤 인스턴스 반환."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def reset_slice(self, slice_id: str, max_calls: int = 50) -> None:
        """슬라이스 진입 시 카운터 reset.

        Args:
            slice_id: 슬라이스 식별자 (예: "slice3", "slice4")
            max_calls: 본 슬라이스의 최대 호출 한도 (default 50)
        """
        self.slice_id = slice_id
        self.max_calls = max_calls
        self.call_count = 0
        self.total_cost_usd = 0.0
        self.records = []
        self.started_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "CostGuard reset for slice=%s, max_calls=%d", slice_id, max_calls
        )

    def record_call(self, cost_usd: float, model: str) -> None:
        """매 LLM 호출 후 누적 기록.

        Raises:
            LLMBudgetExceededError: 한도 초과 시
        """
        if self.call_count >= self.max_calls:
            raise LLMBudgetExceededError(
                f"Slice {self.slice_id} budget exceeded: "
                f"{self.call_count}/{self.max_calls} calls"
            )
        self.call_count += 1
        self.total_cost_usd += cost_usd
        self.records.append(CallRecord(
            cost_usd=cost_usd,
            model=model,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

    def exceeded(self) -> bool:
        """한도 초과 여부."""
        return self.call_count >= self.max_calls

    def status(self) -> dict:
        """현재 상태 dict 반환."""
        return {
            "slice_id": self.slice_id,
            "call_count": self.call_count,
            "max_calls": self.max_calls,
            "remaining": max(0, self.max_calls - self.call_count),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "started_at": self.started_at,
            "records_count": len(self.records),
        }
```

#### 0.5.2 LLMClient 통합

`portfolio/llm/client.py`의 `complete` 메서드에 record_call 추가 (또는 데코레이터):

```python
# portfolio/llm/client.py (확장)

from portfolio.llm.cost_guard import CostGuard


class LLMClient:
    def complete(self, prompt: str, ..., model: Optional[str] = None) -> LLMResponse:
        guard = CostGuard.get_instance()
        # 호출 전 한도 검증
        if guard.exceeded():
            raise LLMBudgetExceededError(
                f"Budget exceeded before call: {guard.status()}"
            )

        # 기존 호출 로직
        resp = ...  # SDK 호출

        # 호출 후 누적 기록
        guard.record_call(cost_usd=resp.cost_usd, model=resp.model)
        return resp
```

#### 0.5.3 단위 테스트

`portfolio/tests/test_cost_guard.py` 신설:

```python
import pytest
from portfolio.llm.cost_guard import CostGuard
from portfolio.llm.exceptions import LLMBudgetExceededError


@pytest.fixture(autouse=True)
def reset_guard():
    """매 테스트 전 깨끗한 상태."""
    guard = CostGuard.get_instance()
    guard.reset_slice("test_slice", max_calls=50)
    yield
    guard.reset_slice("test_slice", max_calls=50)


def test_initial_state():
    guard = CostGuard.get_instance()
    assert guard.call_count == 0
    assert guard.max_calls == 50


def test_record_call_increments():
    guard = CostGuard.get_instance()
    guard.record_call(cost_usd=0.005, model="claude-haiku-4-5")
    assert guard.call_count == 1
    assert guard.total_cost_usd == 0.005


def test_reset_slice_clears():
    guard = CostGuard.get_instance()
    guard.record_call(cost_usd=0.01, model="haiku")
    guard.reset_slice("new_slice", max_calls=30)
    assert guard.call_count == 0
    assert guard.max_calls == 30
    assert guard.slice_id == "new_slice"


def test_budget_exceeded_raises():
    guard = CostGuard.get_instance()
    guard.reset_slice("test", max_calls=2)
    guard.record_call(cost_usd=0.01, model="haiku")
    guard.record_call(cost_usd=0.01, model="haiku")
    with pytest.raises(LLMBudgetExceededError):
        guard.record_call(cost_usd=0.01, model="haiku")


def test_status_dict():
    guard = CostGuard.get_instance()
    status = guard.status()
    assert "call_count" in status
    assert "remaining" in status
```

#### 0.5.4 Slice 3 reset 명시적 호출

`scripts/validation/_setup.py` 또는 진입 스크립트에서 호출:

```python
# scripts/validation/_setup.py에 추가
from portfolio.llm.cost_guard import CostGuard


def init_django():
    # ... 기존 Django setup
    pass


def reset_for_slice(slice_id: str = "slice3", max_calls: int = 50):
    """슬라이스 진입 시 호출. 비용 가드 초기화."""
    guard = CostGuard.get_instance()
    guard.reset_slice(slice_id, max_calls)
    return guard
```

Slice 3 모든 run*step\**\*.py 스크립트 상단에:

```python
from scripts.validation._setup import init_django, reset_for_slice

init_django()
reset_for_slice("slice3", max_calls=50)  # 멱등 — 여러 번 호출해도 안전
```

> **참고**: reset_for_slice은 멱등이므로 Slice 3 내 여러 스크립트가 호출해도 누적 카운트가 유지됨 (단, 첫 호출에서만 reset). 이를 위해 두 번째 호출부터는 slice_id가 동일하면 reset 스킵하도록 보강 가능 (다음 변형):

```python
def reset_for_slice(slice_id: str, max_calls: int = 50):
    guard = CostGuard.get_instance()
    if guard.slice_id != slice_id:
        # 첫 진입 또는 슬라이스 전환
        guard.reset_slice(slice_id, max_calls)
    return guard
```

### 0.5 검증 판정

| #   | 판정                              | 임계                       | 자동 |
| --- | --------------------------------- | -------------------------- | ---- |
| 1   | CostGuard 모듈 import 가능        | python -c 통과             | 자동 |
| 2   | LLMClient 통합 (record_call 호출) | 단위 테스트                | 자동 |
| 3   | reset_for_slice 멱등성            | 두 번 호출해도 카운트 유지 | 자동 |
| 4   | 단위 테스트 통과                  | 5/5                        | 자동 |
| 5   | 회귀                              | 76 + 5 = 81 passed         | 자동 |

### 0.5 산출물

- `portfolio/llm/cost_guard.py` (신규, ~100줄)
- `portfolio/llm/client.py` (확장, +10줄)
- `scripts/validation/_setup.py` (확장, +10줄)
- `portfolio/tests/test_cost_guard.py` (신규, ~70줄)

### 0.5 비용 가드

- LLM 호출: 0회
- 누적: 0 / 50

---

### 0.6 Mock LLMClient text_strategy "e2" 추가 (Slice 2 패턴 mirror)

**목표**: Slice 2에서 도입된 `MockLLMClient(text_strategy="e2")` 인터페이스에 E2용 응답 텍스트 등록.

#### 0.6.1 mocks.py 확장

`portfolio/llm/mocks.py`에 추가:

```python
def _mock_text_e2(prompt: str) -> str:
    """E2: DiagnosticCard 4요소 JSON. 기본 mock 응답.

    실제 테스트에서는 fixture별로 더 정교한 응답 필요 — _build_e2_mock()로 오버라이드 가능.
    """
    return (
        '{'
        '"summary":"GARP 적합도 양호. 핵심 지표 균형.",'
        '"strengths":["P/E 12.5 적정","ROE 18.2% 양호","부채비율 35% 안정"],'
        '"weaknesses":["배당수익률 1.2% 낮음","현금흐름 변동성 존재"],'
        '"actions":["분기별 ROE 모니터링","경쟁사 대비 P/E 추적"]'
        '}'
    )


# _MOCK_TEXT_STRATEGIES dict에 추가
_MOCK_TEXT_STRATEGIES = {
    "e1": _mock_text_e1,
    "e5": _mock_text_e5,
    "e2": _mock_text_e2,  # v2 신규
}
```

#### 0.6.2 단위 테스트 추가

`portfolio/tests/test_mocks.py`에 추가:

```python
def test_mock_text_strategy_e2_explicit():
    """e2 strategy 선택 시 DiagnosticCard JSON."""
    mock = MockLLMClient(text_strategy="e2")
    resp = mock.complete(prompt="test")
    assert "summary" in resp.text
    assert "strengths" in resp.text
    assert "weaknesses" in resp.text
    assert "actions" in resp.text
```

### 0.6 검증 판정

| #   | 판정                               | 임계               | 자동 |
| --- | ---------------------------------- | ------------------ | ---- |
| 1   | \_MOCK_TEXT_STRATEGIES에 "e2" 등록 | 자동 검증          | 자동 |
| 2   | 단위 테스트 통과                   | 1/1                | 자동 |
| 3   | 회귀                               | 81 + 1 = 82 passed | 자동 |

### 0.6 산출물

- `portfolio/llm/mocks.py` (확장, +15줄)
- `portfolio/tests/test_mocks.py` (확장, +10줄)

### 0.6 비용 가드

- LLM 호출: 0회
- 누적: 0 / 50

---

# Step 1 — E2 Pydantic 스키마 (DiagnosticCard 4요소)

## 1.1 목표

E2 진입점의 입력/출력 Pydantic 스키마 신설. **completeness 자동 측정**(Q3.C)을 model_validator로 통합 → schema 통과 자체가 completeness 보장.

## 1.2 사전 조건

D-3 산출물 검토:

```bash
grep -rn "D-3\|진단 카드\|diagnostic_card\|DiagnosticCard" docs/portfolio/coach/ portfolio/schemas/ 2>/dev/null
```

D-3에 E2 스키마 정의가 있으면 import 재사용. 없으면 본 Step에서 신설 (가정).

## 1.3 작업 단계

### 1.3.1 schema 정의

`portfolio/schemas/llm.py`에 추가 (또는 별도 파일):

```python
from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class DiagnosticCard(BaseModel):
    """E2 출력: 진단 카드 4요소.

    completeness 자동 측정:
    - 4개 필드 모두 존재 + 최소 길이 충족 → schema 통과
    - 따라서 schema_pass = completeness_auto = True

    필드별 최소 길이는 Step 7 토큰 측정 후 조정 가능.
    """
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(
        ..., min_length=20, max_length=500,
        description="포트폴리오 요약 (1~2문장).",
    )
    strengths: list[str] = Field(
        ..., min_length=1, max_length=5,
        description="강점 항목 1~5개. 각 항목 10자 이상.",
    )
    weaknesses: list[str] = Field(
        ..., min_length=1, max_length=5,
        description="약점 항목 1~5개. 각 항목 10자 이상.",
    )
    actions: list[str] = Field(
        ..., min_length=1, max_length=5,
        description="제안 액션 1~5개. 각 항목 10자 이상.",
    )

    @model_validator(mode="after")
    def check_item_min_length(self):
        """리스트 항목 최소 길이 — completeness 자동 측정 보강."""
        for field_name in ("strengths", "weaknesses", "actions"):
            items = getattr(self, field_name)
            for i, item in enumerate(items):
                if len(item) < 10:
                    raise ValueError(
                        f"{field_name}[{i}] is too short: {len(item)} chars (min 10)"
                    )
        return self


class E2Request(BaseModel):
    """E2 입력: AnalysisContext (Tier 1 분석 결과)."""
    model_config = ConfigDict(extra="forbid")

    analysis_context: dict  # AnalysisContext (preset_id, holdings, metrics 등)
    session_id: Optional[str] = None


class E2Response(BaseModel):
    """E2 응답 wrapper. DiagnosticCard 본체 + 메타."""
    model_config = ConfigDict(extra="forbid")

    card: DiagnosticCard
    preset_id: str = Field(..., description="입력 preset 식별 (garp, buffett 등)")
```

### 1.3.2 import 경로 통합

`portfolio/schemas/__init__.py`:

```python
from portfolio.schemas.llm import (
    LLMResponse,
    E5Request, E5Response, AdjustmentItem,  # Slice 2
    E2Request, E2Response, DiagnosticCard,  # Slice 3
)
```

### 1.3.3 단위 테스트 추가

`portfolio/tests/test_schemas.py`에 추가:

```python
def test_diagnostic_card_valid():
    card = DiagnosticCard(
        summary="GARP 적합도 양호. 균형 잡힌 포트폴리오.",
        strengths=["P/E 12.5 적정 수준", "ROE 18% 우수"],
        weaknesses=["배당수익률 1.2% 다소 낮음"],
        actions=["분기별 ROE 모니터링 권장"],
    )
    assert card.summary.startswith("GARP")


def test_diagnostic_card_extra_field_rejected():
    with pytest.raises(ValidationError):
        DiagnosticCard(
            summary="..." * 10,
            strengths=["a" * 20],
            weaknesses=["a" * 20],
            actions=["a" * 20],
            extra_field="rejected",  # extra=forbid
        )


def test_diagnostic_card_short_summary_rejected():
    with pytest.raises(ValidationError, match="String should have at least 20"):
        DiagnosticCard(
            summary="짧음",  # < 20 chars
            strengths=["a" * 20],
            weaknesses=["a" * 20],
            actions=["a" * 20],
        )


def test_diagnostic_card_empty_list_rejected():
    """strengths/weaknesses/actions 빈 리스트 거절."""
    with pytest.raises(ValidationError, match="at least 1"):
        DiagnosticCard(
            summary="포트폴리오 요약 텍스트입니다." * 2,
            strengths=[],  # 빈 리스트
            weaknesses=["a" * 20],
            actions=["a" * 20],
        )


def test_diagnostic_card_short_item_rejected():
    """리스트 항목 10자 미만 거절 (completeness 자동 측정)."""
    with pytest.raises(ValidationError, match="too short"):
        DiagnosticCard(
            summary="포트폴리오 요약 텍스트입니다 충분히 길다 정말로 길다.",
            strengths=["짧음"],  # < 10 chars
            weaknesses=["a" * 20],
            actions=["a" * 20],
        )


def test_diagnostic_card_too_many_items_rejected():
    """리스트 항목 6개 이상 거절."""
    with pytest.raises(ValidationError, match="at most 5"):
        DiagnosticCard(
            summary="요약 텍스트 충분히 긴 길이로 작성합니다.",
            strengths=["item " + "x" * 15] * 6,  # 6개
            weaknesses=["a" * 20],
            actions=["a" * 20],
        )
```

## 1.4 검증 판정

| #   | 판정                                           | 임계               | 자동 |
| --- | ---------------------------------------------- | ------------------ | ---- |
| 1   | DiagnosticCard / E2Request / E2Response import | python -c 통과     | 자동 |
| 2   | extra=forbid 동작                              | 1 테스트           | 자동 |
| 3   | min/max 길이 검증                              | 4 테스트           | 자동 |
| 4   | model_validator (item min_length)              | 1 테스트           | 자동 |
| 5   | 회귀                                           | 82 + 6 = 88 passed | 자동 |

```bash
pytest portfolio/tests/test_schemas.py -v -k diagnostic
pytest portfolio/tests/ -q
```

## 1.5 산출물

- `portfolio/schemas/llm.py` (확장, +60줄)
- `portfolio/schemas/__init__.py` (export 추가)
- `portfolio/tests/test_schemas.py` (확장, +80줄)

## 1.6 비용 가드

- LLM 호출: 0회
- 누적: 0 / 50

---

# Step 2 — services/e2_diagnostic_card.py 신설 + 백로그 #3, #4 자연 흡수 (A2.C)

## 2.1 목표

E2 비즈니스 로직을 service 레이어로 작성한다. **A2.C 적용**: Slice 2 백로그 #3 (PROVIDER*KWARGS 공유 모듈) + #4 (build*\*\_prompt 헬퍼 분리)를 본 Step에서 자연 흡수.

## 2.2 사전 조건

- Step 1 완료 (E2Request, E2Response, DiagnosticCard 사용 가능)
- LLMClient + CostGuard 통합 (Step 0.5 완료)
- parsers.py의 `parse_json_response` 재사용

## 2.3 작업 단계

### 2.3.1 PROVIDER_KWARGS 공유 모듈 신설 (#3 흡수)

`portfolio/services/_llm_kwargs.py` 신설:

```python
"""LLMClient 호출 시 사용하는 provider kwargs 공유 모듈.

Slice 2 백로그 #3 — e1_garp.py와 e5_adjustment_parser.py 중복 제거.
모든 진입점 service에서 import.
"""
from __future__ import annotations

from portfolio.llm.client import (
    ANTHROPIC_HAIKU_MODEL,
    ANTHROPIC_SONNET_MODEL,
    GEMINI_MODEL,
)


PROVIDER_KWARGS = {
    "haiku": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    "sonnet": {"provider": "anthropic", "model": ANTHROPIC_SONNET_MODEL},
    "gemini": {"provider": "gemini", "model": GEMINI_MODEL},
}


def resolve_provider_kwargs(label: str) -> dict:
    """Provider label → LLMClient kwargs 변환.

    Args:
        label: "haiku" | "sonnet" | "gemini"

    Raises:
        ValueError: 미등록 label
    """
    if label not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {label}. "
            f"Available: {list(PROVIDER_KWARGS.keys())}"
        )
    return PROVIDER_KWARGS[label]
```

### 2.3.2 기존 service 정리 (#3 적용)

`portfolio/services/e1_garp.py` + `portfolio/services/e5_adjustment_parser.py` 양쪽에서 중복 PROVIDER_KWARGS 정의 제거:

```python
# 기존:
# PROVIDER_KWARGS = {"haiku": {...}, ...}

# 수정 후:
from portfolio.services._llm_kwargs import PROVIDER_KWARGS, resolve_provider_kwargs
```

회귀 88 passed 유지 검증 필수 (양쪽 service 동작 동일성 보장).

### 2.3.3 prompt builder 헬퍼 분리 (#4 흡수)

`portfolio/services/_prompt_helpers.py` 신설:

```python
"""Prompt builder 공통 헬퍼.

Slice 2 백로그 #4 — _format_analysis_summary 등 진입점 무관 헬퍼 분리.
"""
from __future__ import annotations

from typing import Any


def format_holdings_summary(holdings: list[dict]) -> str:
    """Holdings 리스트 → 'TICKER(weight%)' 컴마 구분 문자열.

    예: "MSFT(30%), TSLA(20%), NVDA(50%)"
    """
    return ", ".join(
        f"{h['ticker']}({h['weight']:.0%})" for h in holdings
    )


def format_analysis_summary(ctx: dict[str, Any], max_chars: int = 200) -> str:
    """AnalysisContext에서 한 줄 진단 요약 추출.

    Slice 2 I4 모니터링 — 200자 truncate 유지.
    Step 7 토큰 측정 후 조정 가능.
    """
    summary = ctx.get("analysis_summary", {})
    one_line = summary.get("one_line_diagnosis", "분석 결과 없음")
    return one_line[:max_chars]


def format_metrics_table(metrics: dict[str, Any]) -> str:
    """주요 지표를 표 형식 문자열로. E2 specific.

    예:
        | Metric | Value |
        |---|---|
        | P/E | 12.5 |
        | ROE | 18.2% |
    """
    if not metrics:
        return "(지표 데이터 없음)"
    lines = ["| Metric | Value |", "|---|---|"]
    for key, value in metrics.items():
        if isinstance(value, float):
            lines.append(f"| {key} | {value:.2f} |")
        else:
            lines.append(f"| {key} | {value} |")
    return "\n".join(lines)
```

기존 `e5_adjustment_parser.py`에서 `_format_analysis_summary` 사용 부분을 `format_analysis_summary` import로 변경 (회귀 검증 필수).

### 2.3.4 e2_diagnostic_card.py 신설

`portfolio/services/e2_diagnostic_card.py`:

```python
"""E2 진입점 비즈니스 로직: AnalysisContext → DiagnosticCard 4요소."""
from __future__ import annotations

from typing import Any

from portfolio.llm.client import LLMClient
from portfolio.parsers import parse_json_response
from portfolio.schemas.llm import E2Request, E2Response, DiagnosticCard
from portfolio.services._llm_kwargs import resolve_provider_kwargs
from portfolio.services._prompt_helpers import (
    format_holdings_summary,
    format_analysis_summary,
    format_metrics_table,
)


def build_e2_prompt(request: E2Request) -> str:
    """E2 프롬프트 조립.

    프롬프트 설계 원칙:
    - schema 강제: JSON 형식만, 마크다운 펜스 금지, extra 키 금지
    - 4요소 균형: summary / strengths / weaknesses / actions 모두 채움
    - completeness 강조: 각 리스트 항목 10자 이상
    - 자연스러움: 한국어 자연스러운 톤 (E1 패턴 mirror)
    - 통찰성: 단순 수치 나열이 아닌 의미 있는 해석
    """
    ctx = request.analysis_context
    holdings = ctx.get("holdings", [])
    holdings_str = format_holdings_summary(holdings)
    analysis_str = format_analysis_summary(ctx)
    metrics_str = format_metrics_table(ctx.get("metrics", {}))
    preset_id = ctx.get("preset_id", "unknown")

    return f"""당신은 한국 개인 투자자를 위한 포트폴리오 분석 전문가입니다.

## 프리셋
{preset_id}

## 현재 포트폴리오
{holdings_str}

## 분석 요약
{analysis_str}

## 주요 지표
{metrics_str}

## 작업
위 분석을 바탕으로 진단 카드 4요소를 다음 JSON schema로 생성하세요. JSON 객체만 반환하며, 마크다운 코드 펜스나 추가 설명을 절대 포함하지 마세요.

{{
  "summary": "포트폴리오 요약 1~2문장 (20자 이상)",
  "strengths": ["강점 1 (10자 이상)", "강점 2", ...],
  "weaknesses": ["약점 1 (10자 이상)", "약점 2", ...],
  "actions": ["제안 액션 1 (10자 이상)", "제안 액션 2", ...]
}}

## 규칙
1. 각 리스트는 1~5개 항목, 각 항목 10자 이상.
2. 자연스러운 한국어. 단순 수치 나열 금지 — 의미 있는 해석 포함.
3. summary는 핵심을 1~2문장으로 압축.
4. strengths/weaknesses는 분석 데이터 근거 명확.
5. actions는 실행 가능하고 구체적이어야 함.
6. 매수/매도 추천 금지 — 구조적 진단만.
"""


def parse_e2_response(raw_content: str, preset_id: str = "unknown") -> E2Response:
    """LLM raw 응답 → E2Response Pydantic 객체."""
    data = parse_json_response(raw_content)
    card = DiagnosticCard.model_validate(data)
    return E2Response(card=card, preset_id=preset_id)


def run_e2(request: E2Request, *, provider: str = "haiku") -> dict[str, Any]:
    """E2 진입점 entry function.

    Default provider = haiku (D2.B — 글쓰기 작업).

    Returns:
        {
            "response": E2Response (model_dump),
            "metadata": LLMResponse metadata,
        }
    """
    prompt = build_e2_prompt(request)
    kwargs = resolve_provider_kwargs(provider)
    client = LLMClient()
    raw = client.complete(prompt=prompt, **kwargs)
    preset_id = request.analysis_context.get("preset_id", "unknown")
    parsed = parse_e2_response(raw.text, preset_id=preset_id)
    return {
        "response": parsed.model_dump(),
        "metadata": raw.metadata_dict(),
    }
```

### 2.3.5 단위 테스트 추가

`portfolio/tests/test_e2_service.py` 신설:

````python
import pytest
from portfolio.schemas.llm import E2Request, E2Response, DiagnosticCard
from portfolio.services.e2_diagnostic_card import (
    build_e2_prompt,
    parse_e2_response,
)


def _sample_request() -> E2Request:
    return E2Request(
        analysis_context={
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.4},
                {"ticker": "GOOGL", "weight": 0.3},
                {"ticker": "AAPL", "weight": 0.3},
            ],
            "analysis_summary": {
                "one_line_diagnosis": "GARP 적합도 양호. 안정적 균형.",
            },
            "metrics": {
                "P/E": 22.5,
                "ROE": 0.18,
                "Debt/Equity": 0.35,
            },
        },
    )


def test_build_prompt_contains_holdings():
    prompt = build_e2_prompt(_sample_request())
    assert "MSFT" in prompt
    assert "GOOGL" in prompt
    assert "garp" in prompt


def test_build_prompt_contains_4_elements_directive():
    prompt = build_e2_prompt(_sample_request())
    assert "summary" in prompt
    assert "strengths" in prompt
    assert "weaknesses" in prompt
    assert "actions" in prompt


def test_build_prompt_contains_metrics_table():
    prompt = build_e2_prompt(_sample_request())
    assert "P/E" in prompt
    assert "ROE" in prompt


def test_parse_e2_response_valid():
    raw = """{
        "summary": "GARP 적합도 우수. 균형 잡힌 포트폴리오.",
        "strengths": ["P/E 22.5 적정", "ROE 18% 양호"],
        "weaknesses": ["기술주 비중 다소 높음"],
        "actions": ["분기별 ROE 모니터링 권장"]
    }"""
    parsed = parse_e2_response(raw, preset_id="garp")
    assert isinstance(parsed, E2Response)
    assert parsed.card.summary.startswith("GARP")
    assert len(parsed.card.strengths) == 2
    assert parsed.preset_id == "garp"


def test_parse_e2_response_with_markdown_fence():
    raw = """```json
{"summary":"포트폴리오 요약 충분한 길이","strengths":["강점 항목 충분히 길다"],"weaknesses":["약점 항목 충분히 길다"],"actions":["액션 항목 충분히 길다"]}
```"""
    parsed = parse_e2_response(raw)
    assert parsed.card.summary.startswith("포트폴리오")


def test_parse_e2_response_completeness_violation():
    """리스트 항목 10자 미만 → ValidationError (completeness 자동 측정)."""
    raw = """{"summary":"요약 텍스트 충분한 길이로 작성","strengths":["짧음"],"weaknesses":["약점 적당한 길이"],"actions":["액션 적당한 길이"]}"""
    with pytest.raises(Exception):  # ValidationError
        parse_e2_response(raw)
````

## 2.4 검증 판정

| #   | 판정                                              | 임계               | 자동 |
| --- | ------------------------------------------------- | ------------------ | ---- |
| 1   | \_llm_kwargs.py 모듈 import (#3 흡수)             | 자동               | 자동 |
| 2   | \_prompt_helpers.py 모듈 import (#4 흡수)         | 자동               | 자동 |
| 3   | e1_garp.py + e5_adjustment_parser.py 정리 후 회귀 | Slice 1+2 회귀 0   | 자동 |
| 4   | build_e2_prompt 단위 테스트                       | 3/3                | 자동 |
| 5   | parse_e2_response 단위 테스트                     | 3/3                | 자동 |
| 6   | 회귀                                              | 88 + 6 = 94 passed | 자동 |

## 2.5 산출물

- `portfolio/services/_llm_kwargs.py` (신규, ~30줄, #3 흡수)
- `portfolio/services/_prompt_helpers.py` (신규, ~50줄, #4 흡수)
- `portfolio/services/e1_garp.py` (정리, +import)
- `portfolio/services/e5_adjustment_parser.py` (정리, +import)
- `portfolio/services/e2_diagnostic_card.py` (신규, ~120줄)
- `portfolio/tests/test_e2_service.py` (신규, ~80줄)

## 2.6 비용 가드

- LLM 호출: 0회
- 누적: 0 / 50

---

# Step 3 — Django view + URL 라우팅

## 3.1 목표

E2 진입점을 HTTP endpoint로 노출. 입력이 작으므로 GET도 가능하지만 POST로 통일 (Slice 1, 2 패턴 일관).

## 3.2 작업 단계

### 3.2.1 view 추가

`portfolio/views.py`에 추가:

```python
@csrf_exempt
@require_http_methods(["POST"])
def e2_diagnostic_card_view(request: HttpRequest) -> JsonResponse:
    """E2: AnalysisContext → DiagnosticCard 4요소.

    Request body (JSON):
        {
            "analysis_context": {...},
            "session_id": "..." (optional)
        }
    Query params:
        provider: haiku (default) | sonnet | gemini
    """
    from portfolio.schemas.llm import E2Request
    from portfolio.services.e2_diagnostic_card import run_e2
    from portfolio.llm.exceptions import LLMBudgetExceededError

    try:
        body = json.loads(request.body)
        e2_req = E2Request.model_validate(body)
    except (json.JSONDecodeError, Exception) as e:
        return JsonResponse(
            {"error": "invalid_request", "detail": str(e)[:300]}, status=400,
        )

    provider = request.GET.get("provider", "haiku")  # D2.B — 글쓰기 default
    if provider not in {"haiku", "sonnet", "gemini"}:
        return JsonResponse(
            {"error": "invalid_provider", "allowed": ["haiku", "sonnet", "gemini"]},
            status=400,
        )

    try:
        result = run_e2(e2_req, provider=provider)
    except LLMBudgetExceededError as e:
        return JsonResponse(
            {"error": "budget_exceeded", "detail": str(e)}, status=429,
        )
    except Exception as e:
        return JsonResponse(
            {"error": "llm_invocation_failed", "detail": str(e)[:300]}, status=500,
        )

    return JsonResponse(result, status=200, json_dumps_params={"ensure_ascii": False})
```

### 3.2.2 URL 라우팅

`portfolio/urls.py`:

```python
urlpatterns = [
    path("api/coach/e1/garp/", e1_garp_view, name="e1_garp"),
    path("api/coach/e5/adjustment/", e5_adjustment_parser_view, name="e5_adjustment"),
    path("api/coach/e2/diagnostic-card/", e2_diagnostic_card_view, name="e2_diagnostic_card"),
]
```

### 3.2.3 통합 테스트

`portfolio/tests/test_e2_view.py` 신설:

```python
import json
import pytest
from django.test import Client
from unittest.mock import patch


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def valid_request_body():
    return {
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [{"ticker": "MSFT", "weight": 0.5}],
            "analysis_summary": {"one_line_diagnosis": "test"},
            "metrics": {"P/E": 20},
        },
    }


@patch("portfolio.services.e2_diagnostic_card.run_e2")
def test_e2_view_normal(mock_run, client, valid_request_body):
    mock_run.return_value = {
        "response": {
            "card": {
                "summary": "테스트 요약 충분한 길이입니다.",
                "strengths": ["P/E 20 적정 수준입니다"],
                "weaknesses": ["배당수익률 낮음 다소 약점"],
                "actions": ["분기별 모니터링 권장 합니다"],
            },
            "preset_id": "garp",
        },
        "metadata": {
            "provider": "anthropic", "model": "haiku",
            "cost_usd": 0.005, "latency_ms": 1500,
            "input_tokens": 800, "output_tokens": 200,
            "fallback_from": None,
        },
    }
    resp = client.post(
        "/portfolio/api/coach/e2/diagnostic-card/?provider=haiku",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"]["card"]["summary"]
    assert data["response"]["preset_id"] == "garp"


def test_e2_view_invalid_provider(client, valid_request_body):
    resp = client.post(
        "/portfolio/api/coach/e2/diagnostic-card/?provider=invalid",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_e2_view_invalid_body(client):
    resp = client.post(
        "/portfolio/api/coach/e2/diagnostic-card/",
        data="not json",
        content_type="application/json",
    )
    assert resp.status_code == 400
```

## 3.3 검증 판정

| #   | 판정             | 임계               | 자동 |
| --- | ---------------- | ------------------ | ---- |
| 1   | view 통합 테스트 | 3/3                | 자동 |
| 2   | URL routing      | reverse 가능       | 자동 |
| 3   | 회귀             | 94 + 3 = 97 passed | 자동 |

## 3.4 산출물

- `portfolio/views.py` (확장)
- `portfolio/urls.py` (확장)
- `portfolio/tests/test_e2_view.py` (신규, ~80줄)

## 3.5 비용 가드

- LLM 호출: 0회
- 누적: 0 / 50

---

# Step 4 — Mock LLM client 통합 테스트 (Slice 2 패턴 mirror)

## 4.1 목표

LLMClient의 4개 시나리오 (rate_limit_first / timeout_first / auth_error / budget_exceeded)를 E2 view 위에 mirror. **Step 0.6에서 등록한 text_strategy="e2" 활용**.

## 4.2 작업 단계

`portfolio/tests/test_e2_view.py`에 추가:

```python
from portfolio.llm.exceptions import (
    LLMRateLimitError, LLMTimeoutError, LLMAuthError, LLMBudgetExceededError,
)
from portfolio.llm.mocks import MockLLMClient


def _make_e2_fallback_response(provider: str = "anthropic", model: str = "haiku"):
    """E2 fallback 응답 객체 생성."""
    return type("R", (), {
        "text": (
            '{"summary":"테스트 요약 충분한 길이로 작성합니다.",'
            '"strengths":["테스트 강점 항목 1번"],'
            '"weaknesses":["테스트 약점 항목 1번"],'
            '"actions":["테스트 액션 항목 1번"]}'
        ),
        "provider": provider,
        "model": model,
        "input_tokens": 800,
        "output_tokens": 200,
        "latency_ms": 1500,
        "cost_usd": 0.005,
        "fallback_from": "gemini",
        "metadata_dict": lambda self=None: {
            "provider": provider, "model": model,
            "cost_usd": 0.005, "latency_ms": 1500,
            "input_tokens": 800, "output_tokens": 200,
            "fallback_from": "gemini",
        },
    })()


@patch("portfolio.services.e2_diagnostic_card.LLMClient")
def test_e2_view_rate_limit_first_fallback(mock_client_cls, client, valid_request_body):
    """gemini RateLimit → anthropic 자동 폴백."""
    mock_instance = type("M", (), {
        "complete": lambda self, **kw: _raise_or_return(
            kw, [LLMRateLimitError("rate")], [_make_e2_fallback_response()]
        ),
    })()
    mock_client_cls.return_value = mock_instance
    resp = client.post(
        "/portfolio/api/coach/e2/diagnostic-card/?provider=gemini",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 200


@patch("portfolio.services.e2_diagnostic_card.LLMClient")
def test_e2_view_timeout_first_fallback(mock_client_cls, client, valid_request_body):
    """primary Timeout → fallback 성공."""
    mock_instance = type("M", (), {
        "complete": lambda self, **kw: _raise_or_return(
            kw, [LLMTimeoutError("timeout")], [_make_e2_fallback_response()]
        ),
    })()
    mock_client_cls.return_value = mock_instance
    resp = client.post(
        "/portfolio/api/coach/e2/diagnostic-card/?provider=gemini",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 200


@patch("portfolio.services.e2_diagnostic_card.LLMClient")
def test_e2_view_auth_error_no_fallback(mock_client_cls, client, valid_request_body):
    """auth_error 폴백 안 함 → 500."""
    mock_instance = type("M", (), {
        "complete": lambda self, **kw: (_ for _ in ()).throw(LLMAuthError("invalid key")),
    })()
    mock_client_cls.return_value = mock_instance
    resp = client.post(
        "/portfolio/api/coach/e2/diagnostic-card/?provider=gemini",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 500


@patch("portfolio.services.e2_diagnostic_card.LLMClient")
def test_e2_view_budget_exceeded(mock_client_cls, client, valid_request_body):
    """budget exceeded → 429."""
    mock_instance = type("M", (), {
        "complete": lambda self, **kw: (_ for _ in ()).throw(LLMBudgetExceededError("limit")),
    })()
    mock_client_cls.return_value = mock_instance
    resp = client.post(
        "/portfolio/api/coach/e2/diagnostic-card/",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 429


def _raise_or_return(kwargs, primary_responses, fallback_responses):
    """Mock helper — primary 예외 시 fallback 시도."""
    # 실제 구현은 Slice 2 build_mock_llm_client 패턴 활용.
    # 여기서는 단순화 표현. 실제 작성 시 Slice 2 패턴 그대로 import.
    pass
```

> **참고**: 위 mock 패턴은 Slice 2의 `build_mock_llm_client` 헬퍼 활용 권장. Slice 2 통합 시점에 etiquette 헬퍼 사용 가능 (mocks.py에 `MockLLMClient(mode=...)` 인터페이스 있음).

## 4.3 검증 판정

| #   | 판정              | 임계                | 자동 |
| --- | ----------------- | ------------------- | ---- |
| 1   | 4개 시나리오 통과 | 4/4                 | 자동 |
| 2   | 회귀              | 97 + 4 = 101 passed | 자동 |

## 4.4 산출물

- `portfolio/tests/test_e2_view.py` (확장, +4 테스트)

## 4.5 비용 가드

- LLM 호출: 0회 (Mock만)
- 누적: 0 / 50

---

# Step 5 — fixture 하이브리드 설계 (Q4 수정 + 옵션 2)

## 5.1 목표

E2 입력은 AnalysisContext만 (E5와 달리 자연어 명령 없음). **하이브리드 fixture 7개 설계** (garp 3 재활용 + 신규 4):

| #   | fixture             | 출처           | 의도                                    |
| --- | ------------------- | -------------- | --------------------------------------- |
| 1   | garp_tech           | Slice 1 재활용 | Slice 1 비교 baseline (FIT 케이스)      |
| 2   | garp_misfit         | Slice 1 재활용 | Slice 1 비교 baseline (MISFIT 케이스)   |
| 3   | garp_large          | Slice 1 재활용 | Slice 1 비교 baseline (대규모 holdings) |
| 4   | e2_clear_strengths  | 신규           | 강점만 명확 — completeness 측정         |
| 5   | e2_clear_weaknesses | 신규           | 약점만 명확 — completeness 측정         |
| 6   | e2_balanced         | 신규           | 4요소 균형 — naturalness 측정           |
| 7   | e2_extreme_risk     | 신규           | 리스크 부각 — insight 측정              |

## 5.2 작업 단계

### 5.2.1 fixture 신설

`portfolio/tests/fixtures/sample_diagnostic_context.py` 신설:

```python
"""E2 진입점 fixture: AnalysisContext (DiagnosticCard 입력)."""
from __future__ import annotations

from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_tech,
    get_context_garp_misfit,
    get_context_garp_large,
)


# fixture 그룹 메타 (Step 8 회고에서 그룹 비교 분석)
FIXTURE_GROUPS = {
    "slice1_baseline": ["garp_tech", "garp_misfit", "garp_large"],
    "e2_focused": [
        "e2_clear_strengths",
        "e2_clear_weaknesses",
        "e2_balanced",
        "e2_extreme_risk",
    ],
}


def _wrap_for_e2(garp_ctx, preset_id: str = "garp") -> dict:
    """garp fixture를 E2 입력 형태로 래핑."""
    return {
        "preset_id": preset_id,
        "holdings": garp_ctx["holdings"],
        "metrics": garp_ctx.get("metrics", {}),
        "analysis_summary": {
            "one_line_diagnosis": "GARP 적합도 분석 결과 텍스트.",
            "preset_id": preset_id,
        },
        "preset_version": garp_ctx.get("preset_version", "v1.0"),
    }


# === Slice 1 baseline 그룹 (3개 재활용) ===

def get_e2_fixture_garp_tech() -> dict:
    return {
        "fixture_group": "slice1_baseline",
        "analysis_context": _wrap_for_e2(get_context_garp_tech()),
        "expected": {
            "strengths_min": 1,
            "weaknesses_min": 1,
            "actions_min": 1,
            "summary_keywords_any": ["GARP", "적합", "기술"],
        },
    }


def get_e2_fixture_garp_misfit() -> dict:
    return {
        "fixture_group": "slice1_baseline",
        "analysis_context": _wrap_for_e2(get_context_garp_misfit()),
        "expected": {
            "strengths_min": 1,
            "weaknesses_min": 2,  # misfit은 약점 더 많이 기대
            "actions_min": 2,
            "summary_keywords_any": ["부적합", "MISFIT", "재검토"],
        },
    }


def get_e2_fixture_garp_large() -> dict:
    return {
        "fixture_group": "slice1_baseline",
        "analysis_context": _wrap_for_e2(get_context_garp_large()),
        "expected": {
            "strengths_min": 1,
            "weaknesses_min": 1,
            "actions_min": 1,
            "summary_keywords_any": ["다각화", "분산", "포트폴리오"],
        },
    }


# === E2 specific 그룹 (4개 신규) ===

def get_e2_fixture_clear_strengths() -> dict:
    """강점만 명확한 케이스. weaknesses/actions LLM이 합리적으로 채워야 함."""
    return {
        "fixture_group": "e2_focused",
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "AAPL", "weight": 0.4},
                {"ticker": "MSFT", "weight": 0.6},
            ],
            "metrics": {
                "P/E": 18.5,
                "ROE": 0.32,  # 높음
                "EarningsGrowth": 0.22,  # 높음
                "Debt/Equity": 0.15,  # 낮음
            },
            "analysis_summary": {
                "one_line_diagnosis": "ROE 32%, 성장률 22%, 부채비율 15% — 모든 지표 우수.",
                "preset_id": "garp",
            },
        },
        "expected": {
            "strengths_min": 2,  # 강점 명확하므로 2개 이상 기대
            "weaknesses_min": 1,
            "actions_min": 1,
            "summary_keywords_any": ["우수", "양호", "강점"],
        },
    }


def get_e2_fixture_clear_weaknesses() -> dict:
    """약점만 명확한 케이스."""
    return {
        "fixture_group": "e2_focused",
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "TSLA", "weight": 0.5},
                {"ticker": "PLTR", "weight": 0.5},
            ],
            "metrics": {
                "P/E": 95,  # 매우 높음
                "ROE": 0.05,  # 낮음
                "EarningsGrowth": -0.10,  # 음수
                "Debt/Equity": 0.85,  # 높음
            },
            "analysis_summary": {
                "one_line_diagnosis": "P/E 95, ROE 5%, 성장률 -10%, 부채비율 85% — 다중 약점.",
                "preset_id": "garp",
            },
        },
        "expected": {
            "strengths_min": 1,
            "weaknesses_min": 2,  # 약점 명확하므로 2개 이상 기대
            "actions_min": 2,
            "summary_keywords_any": ["부적합", "위험", "약점"],
        },
    }


def get_e2_fixture_balanced() -> dict:
    """4요소 균형 — naturalness 평가용."""
    return {
        "fixture_group": "e2_focused",
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.25},
                {"ticker": "JNJ", "weight": 0.25},
                {"ticker": "V", "weight": 0.25},
                {"ticker": "PG", "weight": 0.25},
            ],
            "metrics": {
                "P/E": 22,
                "ROE": 0.18,
                "EarningsGrowth": 0.12,
                "Debt/Equity": 0.40,
            },
            "analysis_summary": {
                "one_line_diagnosis": "균형 잡힌 포트폴리오. 각 지표 평균 수준.",
                "preset_id": "garp",
            },
        },
        "expected": {
            "strengths_min": 1,
            "weaknesses_min": 1,
            "actions_min": 1,
            "summary_keywords_any": ["균형", "안정", "적정"],
        },
    }


def get_e2_fixture_extreme_risk() -> dict:
    """리스크 요소 부각 — insight 평가용. 표면 지표는 양호하나 깊이 있는 분석 필요."""
    return {
        "fixture_group": "e2_focused",
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "META", "weight": 0.7},  # 단일 종목 70% — 집중 위험
                {"ticker": "AMZN", "weight": 0.3},
            ],
            "metrics": {
                "P/E": 25,
                "ROE": 0.20,
                "EarningsGrowth": 0.15,
                "Debt/Equity": 0.30,
                "Concentration": 0.70,  # 집중 위험 지표
            },
            "analysis_summary": {
                "one_line_diagnosis": "지표는 양호하나 단일 종목 70% — 집중 위험 우려.",
                "preset_id": "garp",
            },
        },
        "expected": {
            "strengths_min": 1,
            "weaknesses_min": 1,
            "actions_min": 1,
            "summary_keywords_any": ["집중", "위험", "분산"],  # insight 측정 — LLM이 집중 위험 인식?
        },
    }


ALL_FIXTURES = {
    "garp_tech": get_e2_fixture_garp_tech,
    "garp_misfit": get_e2_fixture_garp_misfit,
    "garp_large": get_e2_fixture_garp_large,
    "e2_clear_strengths": get_e2_fixture_clear_strengths,
    "e2_clear_weaknesses": get_e2_fixture_clear_weaknesses,
    "e2_balanced": get_e2_fixture_balanced,
    "e2_extreme_risk": get_e2_fixture_extreme_risk,
}
```

### 5.2.2 fixture 검증 테스트

`portfolio/tests/test_e2_fixtures.py` 신설:

```python
import pytest

from portfolio.schemas.llm import E2Request
from portfolio.tests.fixtures.sample_diagnostic_context import (
    ALL_FIXTURES, FIXTURE_GROUPS,
)


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_e2_fixture_valid_request(fixture_name):
    """각 fixture가 E2Request로 검증 통과."""
    fixture = ALL_FIXTURES[fixture_name]()
    req = E2Request(analysis_context=fixture["analysis_context"])
    assert "holdings" in req.analysis_context
    assert "preset_id" in req.analysis_context


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_e2_fixture_has_expected(fixture_name):
    """각 fixture에 expected + fixture_group 존재."""
    fixture = ALL_FIXTURES[fixture_name]()
    assert "expected" in fixture
    assert "fixture_group" in fixture
    assert fixture["fixture_group"] in FIXTURE_GROUPS


def test_e2_fixture_count():
    """7개 fixture (3 baseline + 4 focused)."""
    assert len(ALL_FIXTURES) == 7


def test_fixture_groups_completeness():
    """FIXTURE_GROUPS의 모든 fixture가 ALL_FIXTURES에 존재."""
    all_grouped = set()
    for group_fixtures in FIXTURE_GROUPS.values():
        all_grouped.update(group_fixtures)
    assert all_grouped == set(ALL_FIXTURES.keys())


def test_baseline_group_count():
    """Slice 1 baseline 그룹 = 3개."""
    assert len(FIXTURE_GROUPS["slice1_baseline"]) == 3


def test_focused_group_count():
    """E2 focused 그룹 = 4개."""
    assert len(FIXTURE_GROUPS["e2_focused"]) == 4
```

## 5.3 검증 판정

| #   | 판정                                | 임계                                | 자동 |
| --- | ----------------------------------- | ----------------------------------- | ---- |
| 1   | 7개 fixture 모두 Pydantic 검증 통과 | 7/7                                 | 자동 |
| 2   | expected + fixture_group 필드 존재  | 7/7                                 | 자동 |
| 3   | 카운트 검증 (7, 3+4)                | 통과                                | 자동 |
| 4   | FIXTURE_GROUPS 일관성               | 통과                                | 자동 |
| 5   | 회귀                                | 101 + (7+7+1+1+1+1=18) = 119 passed | 자동 |

## 5.4 산출물

- `portfolio/tests/fixtures/sample_diagnostic_context.py` (신규, ~220줄)
- `portfolio/tests/test_e2_fixtures.py` (신규, ~50줄)

## 5.5 비용 가드

- LLM 호출: 0회
- 누적: 0 / 50

---

# Part 1 종결 체크리스트

Step 0 ~ Step 5 완료 직전 본인 확인:

- [ ] **Step 0.4**: docs/portfolio/coach/slice3/ 디렉토리 신설
- [ ] **Step 0.5 (D3.C)**: CostGuard 모듈 + LLMClient 통합 + 단위 테스트 5개. 회귀 76 → 81
- [ ] **Step 0.6**: text_strategy "e2" 등록 + 단위 테스트 1개. 회귀 81 → 82
- [ ] **Step 1**: DiagnosticCard schema + completeness model_validator + 단위 테스트 6개. 회귀 82 → 88
- [ ] **Step 2 (#3, #4 흡수)**: \_llm_kwargs.py + \_prompt_helpers.py + e2_diagnostic_card.py. e1/e5 정리 후 회귀 0. 단위 테스트 6개. 회귀 88 → 94
- [ ] **Step 3**: view + URL + 통합 테스트 3개. 회귀 94 → 97
- [ ] **Step 4**: Mock 4 시나리오. 회귀 97 → 101
- [ ] **Step 5 (Q4 수정)**: hybrid fixture 7개 (3 baseline + 4 focused). FIXTURE_GROUPS 메타. 회귀 101 → **119**
- [ ] 누적 LLM 호출: 0 / 50 (Reset 적용 — 모두 Mock)
- [ ] 누적 비용: $0
- [ ] 백로그 #3, #4 처리 완료 (Step 2 흡수)
- [ ] D4 가이드 명시 (run 스크립트는 Step 6/7/8에서 \_json_default 핸들러 의무)

# Part 2 진입 조건

위 체크리스트 모두 통과 시 Part 2 (Step 6~9) 지시서로 진입.

> "Slice 3 Part 2 시작. Step 6 실제 haiku 호출 검증부터."

Part 2 (별도 파일 slice3_part2.md):

- Step 6: garp_tech × haiku × 1회
- Step 7: 7 fixture 토큰 측정
- Step 8: 14 calls (7×2) + group 비교 분석
- Step 9: #5 E5_TOKEN_BUDGET 상수 + 입력 가드레일 (30분 슬롯)

---

# 부록 A — 결정 사항 단일 표

| Q         | 결정                                                           | 적용 위치              |
| --------- | -------------------------------------------------------------- | ---------------------- |
| Q1        | 진입점 = E2 (진단 카드 4요소)                                  | 슬라이스 전체          |
| Q3        | 평가 차원 = schema + naturalness + insight + completeness 자동 | Step 1 schema          |
| Q4 (수정) | hybrid fixture (3 baseline + 4 focused)                        | Step 5                 |
| Q5        | reset 코드 구현 (CostGuard)                                    | Step 0.5               |
| Q6        | DIMENSION_LOOKUP[e2] 직접 추가                                 | Step 9 (Part 2)        |
| Q7        | completeness 자동, LLM-as-judge Phase 2                        | Step 1 model_validator |
| D2        | default provider = haiku                                       | Step 6 (Part 2)        |
| D3        | reset 코드 구현 — CostGuard.reset_slice()                      | Step 0.5               |
| A1        | Step 8 매트릭스 7×2=14                                         | Step 8 (Part 2)        |
| A2        | #5 단독 + #3,#4 Step 2 흡수                                    | Step 2 + Step 9        |
| A3        | e1 산식 + completeness 자동                                    | Step 8 (Part 2) score  |

# 부록 B — Part 1 신규 파일 목록

| 파일                                                    | 종류                    | 줄 수 (추정) | 백로그 흡수 |
| ------------------------------------------------------- | ----------------------- | ------------ | ----------- |
| `portfolio/llm/cost_guard.py`                           | CostGuard 모듈          | ~100         | D3.C        |
| `portfolio/llm/client.py`                               | (확장) record_call 통합 | +10          | D3.C        |
| `scripts/validation/_setup.py`                          | (확장) reset_for_slice  | +10          | D3.C        |
| `portfolio/tests/test_cost_guard.py`                    | 단위 테스트             | ~70          | D3.C        |
| `portfolio/llm/mocks.py`                                | (확장) "e2" strategy    | +15          | —           |
| `portfolio/tests/test_mocks.py`                         | (확장) e2 테스트        | +10          | —           |
| `portfolio/schemas/llm.py`                              | (확장) DiagnosticCard   | +60          | —           |
| `portfolio/tests/test_schemas.py`                       | (확장) DiagnosticCard   | +80          | —           |
| `portfolio/services/_llm_kwargs.py`                     | 공유 모듈               | ~30          | **#3**      |
| `portfolio/services/_prompt_helpers.py`                 | 공유 헬퍼               | ~50          | **#4**      |
| `portfolio/services/e1_garp.py`                         | (정리)                  | +import      | #3, #4      |
| `portfolio/services/e5_adjustment_parser.py`            | (정리)                  | +import      | #3, #4      |
| `portfolio/services/e2_diagnostic_card.py`              | E2 service              | ~120         | —           |
| `portfolio/tests/test_e2_service.py`                    | 단위 테스트             | ~80          | —           |
| `portfolio/views.py`                                    | (확장) e2 view          | +40          | —           |
| `portfolio/urls.py`                                     | (확장) e2 URL           | +5           | —           |
| `portfolio/tests/test_e2_view.py`                       | view 통합 테스트        | ~150         | —           |
| `portfolio/tests/fixtures/sample_diagnostic_context.py` | hybrid fixture          | ~220         | —           |
| `portfolio/tests/test_e2_fixtures.py`                   | fixture 검증            | ~50          | —           |

총 신규 코드: ~1,100줄.

# 부록 C — 회귀 카운트 진행 표

| 단계                          | 추가 테스트      | 누적    |
| ----------------------------- | ---------------- | ------- |
| Slice 2 종결 baseline         | —                | 76      |
| Step 0.5 (CostGuard)          | +5               | 81      |
| Step 0.6 (e2 mock)            | +1               | 82      |
| Step 1 (schema)               | +6               | 88      |
| Step 2 (service + #3,#4 정리) | +6 (회귀 0 유지) | 94      |
| Step 3 (view)                 | +3               | 97      |
| Step 4 (Mock 4 시나리오)      | +4               | 101     |
| Step 5 (fixture)              | +18              | **119** |

# 부록 D — D4 회피 가이드 (Slice 2 1차 손실 재발 방지)

본 슬라이스 모든 run*step\**\*.py 스크립트에서 다음 패턴 의무:

```python
# 모든 run 스크립트 상단에 _json_default 핸들러 정의
def _json_default(obj):
    """JSON 직렬화 안전망 — set, Decimal, datetime 처리."""
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not JSON serializable")


# json.dumps 호출 시 default 핸들러 사용
output_path.write_text(
    json.dumps(output, ensure_ascii=False, indent=2, default=_json_default),
    encoding="utf-8",
)
```

또는 fixture에서 비-JSON-native 타입 금지:

- `expected_tickers: set` → `expected_tickers: list[str]` 변경
- `expected_actions: set` → `expected_actions: list[str]` 변경

본 Slice 3 fixture는 `expected` dict 안에 list만 사용 (set 미사용) — 안전.

추가 안전망: Step 6 smoke 시점에 산출물을 disk에 write 후 read-back으로 round-trip 검증:

```python
# write 후 즉시 read-back 검증
output_path.write_text(json.dumps(output, ...))
loaded = json.loads(output_path.read_text())
assert loaded == output  # round-trip 검증
```

이 검증으로 Step 6 1회 호출 시점에 직렬화 문제 발견 → Step 8 14회 손실 차단.
