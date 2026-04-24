# D-8 Instructions: Integration Validation & End-to-End Scenario Test

> **세션**: D-8 (세션 D 마무리)
> **목적**: D-0a~D-7의 모든 산출물이 일관되게 동작하는지 검증 + 대표 시나리오 end-to-end 실행
> **전제 세션**: D-0a ~ D-7 모두 완료
> **대상 에이전트**: Claude Code
> **버전**: v1.0 (2026-04-20)

---

## 0. 에이전트가 먼저 읽을 것

**필수 참조** (모두):
1. `docs/portfolio/INDEX.md` — 전체 결정 목록
2. `docs/portfolio/design/coach-llm-design-v1.md` — §3 진입점 전체, §8 PV3 검증 기준
3. `docs/portfolio/design/wallet-portfolio-architecture-v1.md` — 데이터 모델 일관성 체크
4. `docs/portfolio/design/return-tracking-design-v1.md` — 수익률 계산 일관성
5. 모든 이전 지시서 (D-0a ~ D-7) — 개별 완료 기준 참조
6. 모든 이전 완료 보고 — 판단 포인트 메모 통합 리뷰

---

## 1. 목표

D-0a ~ D-7이 만든 각 조각을 **유기적으로 연결해 동작 검증**.

### 1-1. 검증 범위

**A. 정적 검증 (코드 구조)**
- 모든 모듈 import 가능
- 모든 스키마 Pydantic 유효
- 프리셋-지표 매핑 정합성
- 버전 번들 일관성

**B. 조립 검증 (프롬프트 생성)**
- E1~E6 각각의 `build_*_prompt()` 함수가 AnalysisContext 받아 정상 생성
- 토큰 예산 범위 내
- PV3 용어 일관성

**C. 시나리오 검증 (end-to-end)**
- 실제 LLM 호출 없이 **dry-run**
- 모의 AnalysisContext로 각 진입점 호출 → 출력 JSON 구조 파싱
- 시나리오 플로우: 분석 실행 → E1~E3 → 사용자 질문 → E4 → 조정 요청 → E5 → E6

**D. 정합성 검증 (의사결정 이력)**
- 1회 세션이 ChatSession + Message + Decision 모델에 올바르게 저장되는지

### 1-2. 산출물

```
implementation/
├── tests/                             ★ NEW
│   ├── __init__.py
│   ├── fixtures/                      (모의 데이터)
│   │   ├── __init__.py
│   │   ├── sample_wallet.py           (Wallet, WalletHolding 픽스처)
│   │   ├── sample_analysis_context.py (AnalysisContext 3종)
│   │   └── sample_user_profile.py
│   ├── test_static_integrity.py       (A. 정적 검증)
│   ├── test_prompt_assembly.py        (B. 조립 검증)
│   ├── test_scenario_e2e.py           (C. 시나리오 검증)
│   └── test_session_lifecycle.py      (D. 정합성 검증)
├── validation_report.md               ★ NEW (검증 결과 자동 생성)
```

---

## 2. 사전 조건

- [x] D-0a~D-7 모두 완료
- [x] `models.py`, `schemas/`, `prompts/tier0/`, `prompts/e1~e6/` 모두 존재
- [x] `pytest` 설치

---

## 3. 단계별 작업 명세

### Step 1: Fixtures 작성

#### `fixtures/sample_wallet.py`

현실적 Wallet + WalletHolding 세트 3종 (다양한 포트폴리오 구성):
- **Fixture A**: Tech 집중형 (NVDA, MSFT, AAPL, GOOGL, AMZN 5종목)
- **Fixture B**: 배당 중심 (JNJ, PG, KO, PEP, WMT 5종목)
- **Fixture C**: 혼합형 (Tech 3 + Healthcare 2 + Consumer 2 = 7종목)

```python
def get_fixture_wallet_tech_focused() -> Wallet:
    """
    Returns an in-memory Wallet with 5 Tech holdings.
    Does NOT touch DB.
    """
    ...
```

#### `fixtures/sample_analysis_context.py`

각 Fixture wallet에 대해 AnalysisContext 3종:
- **Context 1**: Fixture A × GARP 프리셋 → PEG 약점 시나리오
- **Context 2**: Fixture B × Dividend Growth 프리셋 → 배당 지속성 강점 시나리오
- **Context 3**: Fixture C × Multi-Factor 프리셋 → 복합 팩터 시나리오

각 Context는 현실적 MetricResult, StrengthWeakness, DiagnosticCard, ReturnBreakdown 데이터 포함.

**중요**: 실제 계산 없이 **수동으로 채운 모의 데이터**. 실제 퍼센타일 계산은 별도 세션.

### Step 2: `test_static_integrity.py`

**검증 항목**:

```python
import pytest
from decimal import Decimal


def test_all_modules_importable():
    """모든 핵심 모듈이 import 에러 없이 로드되는지."""
    from portfolio import models, schemas
    from portfolio.schemas import (
        AnalysisContext, OneLineDiagnosis, DiagnosticCards,
        MetricComments, ConversationResponse, AdjustmentIntent,
        AdjustmentComparison, UserProfile,
    )
    from portfolio.prompts.tier0 import build_tier0
    from portfolio.prompts.e1 import build_e1_prompt
    from portfolio.prompts.e2 import build_e2_prompt
    from portfolio.prompts.e3 import build_e3_prompt
    from portfolio.prompts.e4 import build_e4_prompt
    from portfolio.prompts.e5 import build_e5_prompt
    from portfolio.prompts.e6 import build_e6_prompt


def test_preset_metric_consistency():
    """PRESET_METRICS에 참조된 모든 metric_id가 METRICS에 존재."""
    from portfolio.metrics.definitions.metrics import METRICS
    from portfolio.metrics.definitions.preset_metrics import PRESET_METRICS

    all_metric_ids = set(METRICS.keys())
    for preset_id, entries in PRESET_METRICS.items():
        for entry in entries:
            assert entry["metric_id"] in all_metric_ids, (
                f"{preset_id} references unknown metric {entry['metric_id']}"
            )


def test_metric_count():
    """지표 수가 설계서와 일치."""
    from portfolio.metrics.definitions.metrics import METRICS, get_metrics_by_type
    assert len(METRICS) == 57
    assert len(get_metrics_by_type("stock_level")) == 39
    assert len(get_metrics_by_type("portfolio_level")) == 13
    assert len(get_metrics_by_type("composite")) == 5


def test_preset_count():
    """프리셋 수."""
    from portfolio.metrics.definitions.presets import PRESETS
    assert len(PRESETS) == 12


def test_version_bundle():
    """버전 번들 정합성."""
    from portfolio.metrics.definitions.versions import CURRENT_VERSIONS
    assert CURRENT_VERSIONS["metric_version"] == "1.2"
    assert "preset_version" in CURRENT_VERSIONS
    assert "prompt_version" in CURRENT_VERSIONS
```

### Step 3: `test_prompt_assembly.py`

**검증 항목**:

```python
from portfolio.tests.fixtures import sample_analysis_context, sample_user_profile


def test_tier0_pv3_terminology_present():
    """Tier 0 system prompt에 PV3 용어 정의 블록 존재."""
    from portfolio.prompts.tier0 import build_tier0
    prompt = build_tier0()
    assert "analysis_target_portfolio" in prompt
    assert "wallet_all_holdings" in prompt
    assert "excluded_from_this_portfolio" in prompt


def test_tier0_token_budget():
    """Tier 0 토큰 예산 5000-9000 chars."""
    from portfolio.prompts.tier0 import build_tier0
    prompt = build_tier0()
    assert 5000 <= len(prompt) <= 9000


def test_e1_assembly():
    context = sample_analysis_context.get_context_garp_tech()
    from portfolio.prompts.e1 import build_e1_prompt
    system, user = build_e1_prompt(context)
    assert len(system) > 0
    assert len(user) > 0
    # E1은 Wallet 최소 주입
    assert "wallet_all_holdings" in system  # 정의는 있어야 함 (Tier 0)
    assert "return_breakdown" not in user  # E1 input에 return_breakdown 상세 없음


def test_e4_assembly_all_tiers():
    """E4는 Tier 1~3 전체 포함."""
    from portfolio.prompts.e4 import build_e4_prompt
    # Mock ChatSession과 UserProfile
    context = sample_analysis_context.get_context_garp_tech()
    session = mock_chat_session_with_5_turns()
    profile = sample_user_profile.get_aggressive_tech_profile()

    prompt = build_e4_prompt(context, session, profile, "테스트 질문")
    assert "system" in prompt
    assert "messages" in prompt
    assert len(prompt["messages"]) >= 1
    assert prompt["messages"][-1]["role"] == "user"
    assert prompt["messages"][-1]["content"] == "테스트 질문"


def test_e5_no_tier1_or_wallet():
    """E5는 Tier 1~3 미포함."""
    from portfolio.prompts.e5 import build_e5_prompt
    system, user = build_e5_prompt("ROIC 20%로", "buffett_quality_value")
    # Tier 0에는 있어야 하지만 Tier 3 블록은 없어야 함
    assert "Investment style" not in system
    assert "conversation history" not in system.lower()


def test_all_entry_points_return_valid_strings():
    """모든 진입점이 빈 문자열/None 없이 반환."""
    context = sample_analysis_context.get_context_garp_tech()

    from portfolio.prompts.e1 import build_e1_prompt
    from portfolio.prompts.e2 import build_e2_prompt
    from portfolio.prompts.e3 import build_e3_prompt

    for builder in [build_e1_prompt, build_e2_prompt, build_e3_prompt]:
        system, user = builder(context)
        assert system and len(system) > 100
        assert user and len(user) > 100
```

### Step 4: `test_scenario_e2e.py`

**end-to-end 시나리오 1: 분석 실행 → 대화 → 조정**

```python
def test_scenario_analyze_question_adjust_compare():
    """
    Scenario:
    1. 사용자가 Tech 포트폴리오로 GARP 분석 실행
    2. E1 + E2 + E3 자동 생성
    3. 사용자 질문: "왜 NVDA가 약점?"
    4. E4 응답
    5. 사용자 조정 요청: "ROIC 20%로 올려봐"
    6. E5 파싱 → override 구조화
    7. 조정 분석 재실행 (mock)
    8. E6 비교 해설
    """
    from portfolio.prompts.e1 import build_e1_prompt
    from portfolio.prompts.e2 import build_e2_prompt
    from portfolio.prompts.e3 import build_e3_prompt
    from portfolio.prompts.e4 import build_e4_prompt
    from portfolio.prompts.e5 import build_e5_prompt
    from portfolio.prompts.e6 import build_e6_prompt

    context = sample_analysis_context.get_context_garp_tech()

    # Step 1: E1~E3 (분석 직후)
    e1_system, e1_user = build_e1_prompt(context)
    assert e1_user  # 성공

    e2_system, e2_user = build_e2_prompt(context)
    assert e2_user

    e3_system, e3_user = build_e3_prompt(context)
    assert e3_user

    # Step 2: E4 (사용자 질문)
    session = mock_empty_session_with_analysis_link(context)
    e4 = build_e4_prompt(context, session, None, "왜 NVDA가 약점이야?")
    assert e4["system"]
    assert e4["messages"][-1]["content"] == "왜 NVDA가 약점이야?"

    # Step 3: 조정 요청 (E4에서 has_adjustment_intent=true 가정)
    e4_adjust = build_e4_prompt(
        context, session, None,
        "ROIC 기준을 20%로 올려서 다시 봐줘"
    )

    # Step 4: E5 파싱
    e5_system, e5_user = build_e5_prompt(
        user_hint="ROIC 기준을 20%로 상향",
        current_preset_id="garp",
    )
    assert "threshold_change" in e5_user  # E5 지시문에 intent_type 포함

    # Step 5: E6 비교 (mock된 조정 결과)
    adjusted_context = sample_analysis_context.get_context_garp_tech_with_roic_20()
    e6_system, e6_user = build_e6_prompt(
        original_context=context,
        adjusted_context=adjusted_context,
        applied_overrides=[{
            "intent_type": "threshold_change",
            "overrides": {"metric_id": "roic", "old_threshold": 0.15, "new_threshold": 0.20}
        }]
    )
    assert e6_user
```

### Step 5: `test_session_lifecycle.py`

**Django DB 사용. pytest-django 권장.**

```python
import pytest
from decimal import Decimal


@pytest.mark.django_db
def test_full_session_lifecycle():
    """
    1. Wallet 생성
    2. WalletHolding 5개 추가
    3. Portfolio 생성 (3개 선택)
    4. AnalysisRun 실행 (mock, is_finalized=False)
    5. ChatSession 생성, Message 3턴 추가
    6. AnalysisRun 완료 (is_finalized=True)
    7. Decision 1개 추출 (mock 수동)
    8. StoredAnalysis 생성
    9. WalletSnapshot 자동 생성 확인
    """
    from portfolio.models import (
        Wallet, WalletHolding, Portfolio, AnalysisRun,
        ChatSession, Message, Decision, StoredAnalysis, WalletSnapshot,
    )
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = User.objects.create_user(username="test")
    wallet = Wallet.objects.create(user=user, name="Test Wallet")
    # ... (생략, 실제 구현 시 상세)

    # 검증
    assert wallet.holdings.count() == 5
    assert Portfolio.objects.filter(wallet=wallet).count() == 1
    assert ChatSession.objects.filter(user=user).count() == 1
    assert Message.objects.filter(session__user=user).count() == 3
    # Saved Analysis 저장 시 WalletSnapshot 자동 생성
    # assert WalletSnapshot.objects.filter(wallet=wallet).count() >= 1


@pytest.mark.django_db
def test_portfolio_effective_holdings_after_sell():
    """
    H3 정책 검증:
    - Portfolio에 3개 holding 선택됨
    - Wallet에서 1개 매도
    - Portfolio.effective_holdings()는 2개만 반환
    """
    # ...
    # holding_c.delete()  # 매도 시뮬레이션
    # assert portfolio.effective_holdings().count() == 2
```

### Step 6: `validation_report.md` 자동 생성

```python
def generate_validation_report():
    """
    pytest 결과 + 주요 메트릭 요약을 markdown 리포트로.
    """
    report = """# D-8 Validation Report

## Test Results
- Static integrity: {static_pass}/{static_total}
- Prompt assembly: {assembly_pass}/{assembly_total}
- E2E scenarios: {e2e_pass}/{e2e_total}
- Session lifecycle: {lifecycle_pass}/{lifecycle_total}

## Token Budget Summary
- Tier 0: ~{tier0_tokens} tokens
- E1 full prompt: ~{e1_tokens} tokens
- E2 full prompt: ~{e2_tokens} tokens
- E3 full prompt: ~{e3_tokens} tokens
- E4 full prompt: ~{e4_tokens} tokens (largest)
- E5 full prompt: ~{e5_tokens} tokens
- E6 full prompt: ~{e6_tokens} tokens

## PV3 Consistency Check
- Tier 0 terminology block: [OK/FAIL]
- All entry points use analysis_target_portfolio / wallet_background: [OK/FAIL]

## Detected Issues
- [list any issues found]

## Recommendation
- MVP ready for LLM integration testing: YES/NO
- Blockers (if any): [...]
"""
```

---

## 4. 검증 통과 기준 (D-8 완료 조건)

### 4-1. 모든 테스트 통과

- [ ] `pytest` 전체 실행 시 모든 테스트 pass
- [ ] 누락된 케이스나 skip된 테스트 없음

### 4-2. 토큰 예산 범위 내

| 진입점 | 예상 범위 | 실제 측정값 | 합격? |
|---|---|---|---|
| Tier 0 | 5,000~9,000 chars | | |
| E1 | 3,000~4,500 토큰 | | |
| E2 | 5,000~8,000 토큰 | | |
| E3 | 3,500~5,000 토큰 | | |
| E4 | 8,000~12,000 토큰 | | |
| E5 | 2,500~4,000 토큰 | | |
| E6 | 4,500~6,500 토큰 | | |

### 4-3. PV3 용어 일관성

- 모든 출력 JSON에 올바른 필드명 (`analysis_target_portfolio`, `wallet_background` 등)
- 금지 필드명 사용 없음

### 4-4. 시나리오 flow 정합성

- 사용자 질문 → E4 응답 → 조정 요청 → E5 파싱 → E6 비교 전체 chain 정상 동작

---

## 5. 에이전트 판단 허용 범위

### 5-1. 허용
- fixture 데이터의 구체적 수치
- pytest 세부 assertion 추가
- validation_report.md 포맷 세부

### 5-2. 금지
- 설계 문서 내용 변경 ("테스트 편의를 위해")
- 프롬프트 구조 변경
- 결정 사항 번복

### 5-3. 판단 어려운 경우
- 토큰 예산 초과 시 먼저 원인 분석 → 설계 수정이 필요하면 사용자 보고
- 테스트 중 발견된 설계 모순 → 반드시 사용자 보고

---

## 6. 산출물

**신규 파일**:
- `implementation/tests/__init__.py`
- `implementation/tests/fixtures/*` (4개)
- `implementation/tests/test_*.py` (4개)
- `implementation/validation_report.md` (자동 생성)

**총 예상**: 800~1,500줄 (테스트 코드 + fixtures)

---

## 7. 완료 보고 포맷

```markdown
# D-8 완료 보고 (세션 D 전체 종료)

## 테스트 결과 요약
- Total tests: N
- Passed: M
- Failed: K (if any, list)

## 토큰 예산 실측

(표 채우기)

## 발견된 이슈
- [이슈 1]: [설명]
- [이슈 2]: [설명]

(없으면 "없음")

## MVP 준비 상태
- [✓/✗] 구조 완성도
- [✓/✗] 프롬프트 조립 정상
- [✓/✗] 시나리오 chain 동작
- [✓/✗] DB 모델 정합성

## 다음 단계 권장

### 즉시 가능
- LLM 실제 호출 테스트 (API 키 주입 필요)
- 백엔드 API 엔드포인트 설계

### 남은 작업 (세션 D 외)
- 퍼센타일 실제 계산 로직 (ReturnCalculator + 프리셋 스코어링)
- API 엔드포인트 설계
- 프론트엔드 연동
- 비교군 정책 상세화 (산업 분류 fallback)
- Tier 2 세션 요약 자동 생성

## validation_report.md
(경로: implementation/validation_report.md)
```

---

## 8. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판 |
