# Slice 4 Part 1 — E6 (조정 후 비교 해설) 진입점 구현 지시서

> 작성일: 2026-05-07
> 진입점: **E6** (조정 후 비교 해설, E5 흐름 통합)
> 범위: **Part 1 = Step 0 ~ Step 5** (CostGuard reset / schema / service / view / Mock test / fixture)
> Part 2 (Step 6 ~ Step 9): Part 1 실행 완료 후 별도 작성
> 회귀 baseline: 123 passed (Slice 3 종결)
> 누적 비용 협의: ~$0.41 / 광의: ~$0.49

---

# §0. 참조 문서

본 지시서를 실행하기 전에 다음 참조 문서를 확인하세요. 코드/구조 정보는 모두 이 문서들에서 인용됩니다.

| 우선순위 | 참조 문서                                                    | 사용 목적                                                                |
| -------- | ------------------------------------------------------------ | ------------------------------------------------------------------------ |
| 1        | `docs/portfolio/coach/slice4_decisions.md`                   | Slice 4 결정 보존 (진입점 / 매트릭스 / Step 9 슬롯 / 누적 결정)          |
| 2        | `docs/portfolio/PORTFOLIO_OVERALL_ANALYSIS.md`               | 종합 재분석 (인프라 누적, 가설 정착 현황)                                |
| 3        | `docs/portfolio/coach/slice4_prep_data.md`                   | Slice 4 사전 데이터 (코드 인용 6건, 회귀 카운트, fixture 그룹 차이)      |
| 4        | `docs/portfolio/instructions/slice-2-part-1-instructions.md` | E5 schema/service/view 패턴 (E6은 E5 결과를 입력으로 받음)               |
| 5        | `docs/portfolio/instructions/slice-3-part-1-instructions.md` | E2 글쓰기 진입점 패턴 (E6도 글쓰기 차원, 직접 mirror)                    |
| 6        | `portfolio/prompts/e6/`                                      | D-7 prompt 스켈레톤 (Slice 4 Step 1·2 작업의 직접 입력)                  |
| 7        | `portfolio/schemas/llm_outputs.py`                           | 진입점별 출력 schemas (E6 schema 추가 위치)                              |
| 8        | `portfolio/schemas/llm.py`                                   | LLMResponse / E1·E5·E2 Request·Response (E6Request·E6Response 추가 위치) |
| 9        | `portfolio/services/e2_diagnostic_card.py`                   | E2 service 패턴 (E6 service 작성 시 직접 mirror — 글쓰기 진입점 동일)    |
| 10       | `portfolio/llm/cost_guard.py`                                | CostGuard 싱글톤 (Step 0에서 `reset_for_slice("slice4")` 호출)           |
| 11       | `portfolio/llm/token_budgets.py`                             | ENTRYPOINT_TOKEN_BUDGETS dict (Step 7에서 e6 추가 — Part 2 범위)         |
| 12       | `portfolio/tests/fixtures/sample_adjustment_context.py`      | E5 fixture (Step 5에서 `clear_*` 3개 재활용)                             |

---

# §1. 목표

## 1.1 작업 단위 정의

E6 진입점 (조정 후 비교 해설)을 Slice 1·2·3 패턴 그대로 mirror하여 Step 0~5까지 구현. E5 결과 + 원본 AnalysisContext를 입력으로 받아 비교 해설 자연어를 출력하는 완전한 pipeline 구축.

## 1.2 정량 목표

| 항목               | 목표                                                  |
| ------------------ | ----------------------------------------------------- |
| 회귀 카운트        | 123 → **170 ± 5** (Slice 3 +47 패턴 mirror)           |
| Step 0~5 신규 코드 | ~600~750줄 (schema / service / view / fixture / test) |
| Mock 통합 테스트   | 5 케이스 (Slice 1 패턴 mirror)                        |
| Hybrid fixture     | 7개 (e5_baseline 3 재활용 + e6_focused 4 신규)        |
| LLM 호출           | 0회 (Mock만 사용 — Part 1 범위)                       |
| CostGuard reset    | 1회 (`slice_id="slice4"`)                             |
| 작업 시간 추정     | Claude Code 50~70분                                   |

## 1.3 정성 목표

- **글쓰기 가설 4번째 외삽 검증 준비**: haiku default 적용 (Slice 1·2·3 정착 가설)
- **E5→E6 흐름 통합**: Slice 2 E5 fixture 직접 재활용 → Phase 1 product 시연 가치 확보
- **분석 엔진 의존성 회피**: 조정 후 AnalysisContext _재계산 로직 미구현_. E5 adjustments + 원본 context를 그대로 LLM에 전달, 비교 해설은 LLM이 수행 (Phase 2에서 재계산 엔진 별도 슬라이스로 분리)
- **D4 가이드 적용**: 모든 산출물에 `_json_default` + round-trip 검증 (Part 2 범위 포함, Part 1에서 사전 준비)

---

# §2. 사전 조건

## 2.1 환경 점검 (Step 0 진입 직전)

```bash
# git 상태 확인
git branch --show-current
# 예상: feature/chainsight-graph-v2

git status
# 예상: clean (Slice 3 종결 직후 commit 상태)

# 회귀 baseline
pytest portfolio/tests/ -q 2>&1 | tail -3
# 예상: 123 passed in ~Xs

# CostGuard 초기 상태
python -c "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); django.setup(); from portfolio.llm.cost_guard import CostGuard; import json; print(json.dumps(CostGuard.get_instance().status(), ensure_ascii=False, indent=2))"
# 예상: slice_id="default", call_count=0, max_calls=50
```

## 2.2 디렉토리 사전 점검

```bash
ls portfolio/prompts/e6/
# 예상: D-7 스켈레톤 파일들 (input_builder.py, instructions.py, examples.py 등)

grep -n "class.*E6\|class.*Comparison" portfolio/schemas/llm_outputs.py
# 예상: E6 관련 schema 미정의 (스켈레톤 상태) — Slice 4 Step 1에서 정의

grep -n "E6\|run_e6" portfolio/services/
# 예상: 매칭 없음 (E6 service 미존재) — Slice 4 Step 2에서 신규 작성
```

## 2.3 인프라 의존성 (Slice 3 산출물 활용)

| 의존 모듈                                                    | 활용 방식                                   | 검증 방법                                                                             |
| ------------------------------------------------------------ | ------------------------------------------- | ------------------------------------------------------------------------------------- |
| `portfolio.llm.cost_guard.CostGuard`                         | Step 0에서 `reset_for_slice("slice4")` 호출 | Step 0 종료 시 `status()`에서 `slice_id="slice4"` 확인                                |
| `portfolio.services._llm_kwargs.PROVIDER_KWARGS`             | E6 service에서 그대로 import                | `from portfolio.services._llm_kwargs import PROVIDER_KWARGS, resolve_provider_kwargs` |
| `portfolio.services._prompt_helpers.format_holdings_summary` | E6 prompt 작성 시 holdings 포맷팅           | E5 흐름 입력이라 holdings는 원본 + 조정 후 두 가지 포맷팅 필요                        |
| `portfolio.llm.parsers.parse_json_response`                  | E6Response Pydantic 검증                    | 마크다운 펜스 사후 제거 + Pydantic 검증 표준 패턴                                     |
| `portfolio.llm.client.LLMClient`                             | E6 service 의존성 주입                      | 테스트에서 Mock으로 대체 가능 (text_strategy 패턴)                                    |
| `portfolio.tests.fixtures.sample_adjustment_context`         | Step 5 fixture 재활용                       | `clear_*` 3개 직접 import 후 E5 결과(adjustments) 추가                                |

## 2.4 작업 차단 조건 (Block conditions)

다음 중 하나라도 해당하면 작업 중단하고 사용자에게 에스컬레이션:

| 차단 조건                                                        | 확인 방법                                                                 | 에스컬레이션 시점   |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------- | ------------------- |
| 회귀 baseline 불일치 (123 ≠ 실측)                                | `pytest --collect-only`                                                   | Step 0 진입 전      |
| `portfolio/prompts/e6/` 디렉토리 부재                            | `ls` 결과 빈 디렉토리                                                     | Step 0 진입 후 즉시 |
| Slice 2 fixture 인터페이스 변경 (`sample_adjustment_context.py`) | `grep "def clear_" portfolio/tests/fixtures/sample_adjustment_context.py` | Step 5 진입 시      |
| CostGuard `reset_for_slice` 시그니처 변경                        | `slice4_prep_data.md §3.1` 인용과 비교                                    | Step 0 진입 후 즉시 |
| 디스크 권한 또는 .env 누락 (LLM 호출 차단되는 경우)              | Part 1은 Mock만 사용 — 차단 영향 없음                                     | Part 2에서 처리     |

---

# §3. 스코프

## 3.1 IN scope (Part 1)

| Step   | 작업                                                        | 산출물                                                                             | 신규 코드 |
| ------ | ----------------------------------------------------------- | ---------------------------------------------------------------------------------- | --------- |
| Step 0 | 환경 점검 + CostGuard reset                                 | (작업 로그만)                                                                      | 0줄       |
| Step 1 | E6 schema 정의 (Request / Response / 부속)                  | `portfolio/schemas/llm.py` 확장 + `portfolio/schemas/llm_outputs.py` 확장          | ~80줄     |
| Step 2 | E6 service 구현 (run_e6 + prompt builder + parser)          | `portfolio/services/e6_comparison.py` 신규                                         | ~150줄    |
| Step 3 | View + URL 라우팅                                           | `portfolio/views.py` 확장 + `portfolio/urls.py` 확장                               | ~40줄     |
| Step 4 | Mock LLM 통합 테스트 5 케이스                               | `portfolio/tests/test_e6_service.py` 신규 + `portfolio/tests/test_e6_view.py` 신규 | ~250줄    |
| Step 5 | Hybrid 7 fixture (e5_baseline 3 재활용 + e6_focused 4 신규) | `portfolio/tests/fixtures/sample_comparison_context.py` 신규                       | ~200줄    |

**총 신규 코드: ~720줄**.

## 3.2 OUT of scope (Part 2 또는 Phase 2)

| 항목                                                                  | 위임 시점             |
| --------------------------------------------------------------------- | --------------------- |
| Step 6 — 실제 LLM 호출 1회 (smoke test)                               | Part 2                |
| Step 7 — 토큰 측정 + e6 budget 결정 + `token_budgets.py`에 e6 추가    | Part 2                |
| Step 8 — 2-way 회고 14 calls (haiku 7 + sonnet 7)                     | Part 2                |
| Step 9 — score 산식 통합 (#2 백로그, e1/e2/e6 main() 통일, 30분 한도) | Part 2                |
| `validation_report_slice4.md` 6 섹션 작성                             | Part 2                |
| **조정 후 AnalysisContext 재계산 로직** (분석 엔진 확장)              | **Phase 2**           |
| E3 (지표 코멘트) preset 외삽 검증                                     | Slice 5/6 (사전 등록) |
| LLM-as-judge 평가 차원                                                | Phase 2 (Slice 5+)    |

## 3.3 명시적 비-스코프 (Negative scope)

다음 항목은 본 슬라이스에서 _의도적으로_ 다루지 않습니다. Claude Code가 임의로 추가하면 안 됨:

- **Frontend 통합**: API 응답 형식만 정의, 실제 UI 연동은 Phase 2
- **여러 preset 동시 검증**: Slice 4는 GARP 단일 preset만. 다른 preset은 Slice 5/6 사전 등록 항목
- **E6 schema에 numeric 정량 필드 (예: risk_score_delta, return_score_delta) 추가**: 이는 분석 엔진 재계산 의존이므로 Phase 2. Slice 4는 자연어 비교 해설만
- **AnalysisContext schema 변경**: E6은 입력으로 받기만 하므로 schema 변경 불필요. 변경 시 Slice 1/2/3 회귀 영향 ↑

---

# §4. 단계별 작업

## Step 0 — 환경 점검 + CostGuard reset (5분)

### 4.0.1 git 상태 확인

```bash
git branch --show-current
git status
git log --oneline -3
```

기대 결과:

- branch = `feature/chainsight-graph-v2` (Slice 1·2·3 동일 branch)
- status = clean
- 마지막 commit이 Slice 3 종결 산출물

차이 발견 시: 사용자에게 에스컬레이션 (특히 다른 branch에 있거나 uncommitted 변경 있을 때).

### 4.0.2 회귀 baseline 확인

```bash
pytest portfolio/tests/ -q --no-header 2>&1 | tail -5
```

기대: `123 passed in <Xs>`.

차이 발견 시: 차이 카운트 + 어떤 테스트가 추가/실패했는지 보고하고 사용자 에스컬레이션. 임의 수정 금지.

### 4.0.3 CostGuard reset (Slice 4 진입)

```python
# scripts/validation/_setup.py 의 reset_for_slice 호출 패턴
from scripts.validation._setup import init_django, reset_for_slice

init_django()
guard = reset_for_slice("slice4", max_calls=50)

import json
print(json.dumps(guard.status(), ensure_ascii=False, indent=2))
```

기대 출력:

```json
{
	"slice_id": "slice4",
	"call_count": 0,
	"max_calls": 50,
	"remaining": 50,
	"total_cost_usd": 0.0,
	"started_at": "<ISO timestamp>",
	"records_count": 0
}
```

검증 포인트:

- `slice_id`가 정확히 `"slice4"`
- `started_at`이 `null`이 아닌 ISO timestamp (`reset_slice` 호출됨을 확인)
- `call_count == 0`, `total_cost_usd == 0.0`

### 4.0.4 prompts/e6/ 디렉토리 인벤토리

```bash
ls -la portfolio/prompts/e6/
wc -l portfolio/prompts/e6/*.py 2>/dev/null
```

기대: D-7 스켈레톤 파일들 존재. 각 파일 줄 수 보고.

스켈레톤이 비어 있으면 Step 1·2 작업 시 prompt 디자인 부담 ↑ — 진입점 결정에 영향. **단, 작업 차단 조건은 아님** (D-7 스켈레톤 활용 가능 여부만 확인).

### 4.0.5 Step 0 완료 보고

다음 형식으로 사용자에게 보고:

```
## Step 0 완료 보고

- git branch: <확인된 값>
- git status: clean / dirty (구체 명시)
- 회귀 baseline: 123 passed (일치 / 불일치)
- CostGuard 상태:
  - slice_id: slice4
  - started_at: <ISO timestamp>
- prompts/e6/ 인벤토리:
  - <파일명>: <줄 수>
  - ...

이상 없으면 Step 1 진입.
```

---

## Step 1 — E6 schema 정의 (10~15분)

### 4.1.1 D-7 prompt 스켈레톤 분석

`portfolio/prompts/e6/` 디렉토리의 파일들을 읽어 다음 항목 추출:

- `input_builder.py`: E6 입력 구조 (어떤 필드를 받는가)
- `instructions.py` 또는 prompt 본문 파일: 출력 형식 명세 (JSON 구조 / 자연어 / 비중)
- `examples.py`: 예시 출력 (있다면)

D-7 스켈레톤 분석 결과를 다음 표로 보고:

| 분석 항목 | 추출 결과                                   |
| --------- | ------------------------------------------- |
| 입력 필드 | (예: analysis_context + adjustments + ...)  |
| 출력 필드 | (예: comparison_summary, before_state, ...) |
| 출력 형식 | JSON / 자연어 / 혼합                        |
| 예시 유무 | 있음 / 없음                                 |

### 4.1.2 E6 schema 1차 설계 (권장 + 조정 권한)

본 지시서가 제시하는 1차 권장 schema. **D-7 스켈레톤이 다른 구조를 명시하면 Claude Code가 조정 권한 행사** — 단, §6 판단 범위 내에서.

**E6Request** (입력 schema):

```python
# portfolio/schemas/llm.py 에 추가

from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class E6Request(BaseModel):
    """E6 (조정 후 비교 해설) 입력.

    E5(조정 파싱) 결과와 원본 분석 컨텍스트를 함께 받아 비교 해설을 생성한다.
    """

    model_config = ConfigDict(extra="forbid")

    analysis_context: dict[str, Any] = Field(
        ...,
        description="원본 AnalysisContext (조정 *전* 상태)",
    )
    adjustments: list["AdjustmentItem"] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="E5 결과 — 사용자가 적용하려는 조정 명령 리스트",
    )
    user_intent: str | None = Field(
        default=None,
        max_length=500,
        description="원본 사용자 발화 (예: '테슬라 줄이고 마이크로소프트 늘려줘'). E5 단계의 raw input 보존용. None이면 prompt에서 생략.",
    )


# 주의: AdjustmentItem 은 portfolio/schemas/llm.py 에 이미 정의되어 있음.
# Slice 2에서 작성한 모델 그대로 재활용.
```

**E6Response** (출력 schema):

```python
# portfolio/schemas/llm_outputs.py 에 추가

from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class E6KeyChange(BaseModel):
    """비교 해설의 개별 변경 사항 한 항목."""

    model_config = ConfigDict(extra="forbid")

    aspect: Literal["allocation", "risk", "expected_return", "diversification", "other"] = Field(
        ...,
        description="변경 차원 (5종).",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=300,
        description="변경 사항 자연어 서술 (한 문장).",
    )


class E6ComparisonResponse(BaseModel):
    """E6 (조정 후 비교 해설) 출력.

    핵심 원칙:
    - 정량 *재계산 없음*. 자연어 비교 해설만 (분석 엔진 의존 회피).
    - 변경 전/후 상태는 *원본 + adjustments*를 LLM이 자체 추론하여 자연어로 묘사.
    """

    model_config = ConfigDict(extra="forbid")

    headline: str = Field(
        ...,
        min_length=10,
        max_length=120,
        description="비교 한 줄 요약 (E1 mirror 패턴, 사용자가 첫 줄에 보는 결과).",
    )
    before_summary: str = Field(
        ...,
        min_length=20,
        max_length=400,
        description="조정 전 포트폴리오 핵심 특징 자연어 요약.",
    )
    after_summary: str = Field(
        ...,
        min_length=20,
        max_length=400,
        description="조정 후 예상 포트폴리오 핵심 특징 자연어 요약.",
    )
    key_changes: list[E6KeyChange] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="주요 변경 사항 (1~5개).",
    )
    risk_assessment: str = Field(
        ...,
        min_length=20,
        max_length=300,
        description="위험 변화 해설 (예: 집중도, 변동성, 섹터 편중).",
    )
    closing_remarks: str = Field(
        ...,
        min_length=10,
        max_length=300,
        description="마무리 해설. 추가 고려사항이나 사용자 결정 보조 문구.",
    )
```

### 4.1.3 schema 추가 위치 + 회귀 영향

| 파일                               | 변경 종류                                      | 추가 줄 수 | 회귀 영향                   |
| ---------------------------------- | ---------------------------------------------- | ---------- | --------------------------- |
| `portfolio/schemas/llm.py`         | E6Request 클래스 추가                          | ~30줄      | 기존 schema 변경 0 (추가만) |
| `portfolio/schemas/llm_outputs.py` | E6KeyChange + E6ComparisonResponse 클래스 추가 | ~50줄      | 기존 schema 변경 0 (추가만) |

기존 schema(AdjustmentItem, AnalysisContext 등)에 _어떤 변경도 가하지 마세요_. 변경 시 Slice 1/2/3 회귀 영향 ↑.

### 4.1.4 schema 단위 테스트 (Step 1 회귀 추가)

`portfolio/tests/test_e6_schema.py` 신규 작성. 5 케이스 권장:

```python
import pytest
from pydantic import ValidationError

from portfolio.schemas.llm import E6Request, AdjustmentItem
from portfolio.schemas.llm_outputs import E6ComparisonResponse, E6KeyChange


def test_e6_request_minimal_valid():
    """최소 필드 충족 시 유효."""
    req = E6Request(
        analysis_context={"preset_id": "garp", "holdings": []},
        adjustments=[
            AdjustmentItem(action="reduce", target="TSLA", target_weight=0.10)
        ],
    )
    assert req.user_intent is None


def test_e6_request_empty_adjustments_invalid():
    """adjustments 빈 리스트는 invalid."""
    with pytest.raises(ValidationError):
        E6Request(
            analysis_context={"preset_id": "garp"},
            adjustments=[],
        )


def test_e6_request_extra_field_forbidden():
    """extra='forbid' 동작 확인."""
    with pytest.raises(ValidationError):
        E6Request(
            analysis_context={"preset_id": "garp"},
            adjustments=[
                AdjustmentItem(action="reduce", target="TSLA", target_weight=0.10)
            ],
            unknown_field="hack",  # invalid
        )


def test_e6_response_valid():
    """E6ComparisonResponse 정상 생성."""
    resp = E6ComparisonResponse(
        headline="원본 대비 위험은 낮아지고 성장 노출은 유지됩니다.",
        before_summary="기술주 집중도 70%, 변동성 높은 구성.",
        after_summary="기술주 집중도 55%로 완화, 디펜시브 종목 추가.",
        key_changes=[
            E6KeyChange(aspect="allocation", description="테슬라 비중 20%→10% 축소."),
            E6KeyChange(aspect="risk", description="집중도 위험 완화."),
        ],
        risk_assessment="포트폴리오 변동성이 약간 낮아질 것으로 예상됩니다.",
        closing_remarks="수익률 상한선은 일부 양보될 수 있으나 안정성 향상.",
    )
    assert len(resp.key_changes) == 2


def test_e6_keychange_aspect_literal_invalid():
    """aspect 는 Literal 5종에 한정."""
    with pytest.raises(ValidationError):
        E6KeyChange(aspect="invalid_aspect", description="..." * 5)
```

### 4.1.5 Step 1 검증

```bash
pytest portfolio/tests/test_e6_schema.py -v
# 예상: 5 passed

pytest portfolio/tests/ -q --no-header 2>&1 | tail -3
# 예상: 128 passed (123 + 5)
```

### 4.1.6 Step 1 완료 보고

```
## Step 1 완료 보고

- E6Request 필드: analysis_context / adjustments / user_intent
- E6ComparisonResponse 필드: headline / before_summary / after_summary / key_changes / risk_assessment / closing_remarks
- E6KeyChange aspect Literal: allocation / risk / expected_return / diversification / other
- D-7 스켈레톤 차이: <D-7과 다르게 조정한 사항 명시 — 없으면 "1차 권장 그대로 적용">
- 회귀: 123 → 128 passed (+5)
- 다음 step 진입 가능: Y/N
```

---

## Step 2 — E6 service 구현 (15~20분)

### 4.2.1 신규 파일 생성

`portfolio/services/e6_comparison.py` 신규 작성. **E2 service (`e2_diagnostic_card.py`) 패턴 직접 mirror** — 글쓰기 진입점 동일 구조이므로 인터페이스 차이만 반영.

```python
"""E6 (조정 후 비교 해설) entry function.

Slice 4 신규. E5 결과(adjustments)와 원본 AnalysisContext를 입력으로 받아
비교 해설 자연어를 생성한다.

핵심 원칙:
- 정량 *재계산 없음*. LLM이 자체 추론하여 자연어 비교만 수행.
- 분석 엔진 의존성 회피 (Phase 2에서 재계산 엔진 별도 슬라이스로 추가 예정).
"""

from __future__ import annotations

from typing import Any, Literal

from portfolio.llm.client import LLMClient
from portfolio.llm.parsers import parse_json_response
from portfolio.schemas.llm import E6Request
from portfolio.schemas.llm_outputs import E6ComparisonResponse
from portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel
from portfolio.services._prompt_helpers import (
    format_holdings_summary,
    format_analysis_summary,
)


# E5 → E6 어댑터 helper
def _format_adjustments_block(adjustments: list[dict[str, Any]]) -> str:
    """AdjustmentItem 리스트 → prompt에 들어갈 자연어 블록.

    예:
      - 테슬라(TSLA): 비중 20% → 10% 축소
      - 마이크로소프트(MSFT): 신규 진입, 비중 15% 추가
    """
    lines: list[str] = []
    for adj in adjustments:
        action = adj.get("action") or "?"
        target = adj.get("target") or "?"
        weight = adj.get("target_weight")
        weight_str = f"{weight:.0%}" if isinstance(weight, (int, float)) else "?"
        verb = {
            "reduce": "축소",
            "increase": "증가",
            "add": "신규 진입",
            "remove": "제외",
        }.get(action, action)
        lines.append(f"- {target}: {verb}, 목표 비중 {weight_str}")
    return "\n".join(lines) if lines else "- (조정 사항 없음)"


def build_e6_prompt(request: E6Request) -> str:
    """E6 prompt 작성. D-7 스켈레톤(prompts/e6/)을 활용 가능.

    프롬프트 구조:
    1. 역할 정의 (포트폴리오 비교 코치)
    2. 원본 포트폴리오 요약 (holdings + 분석 요약)
    3. 조정 명령 리스트
    4. 출력 형식 명세 (JSON, E6ComparisonResponse schema)
    """
    ctx = request.analysis_context
    holdings = ctx.get("holdings", []) or []
    holdings_str = format_holdings_summary(holdings) if holdings else "(보유 종목 없음)"
    analysis_one_liner = format_analysis_summary(ctx, max_chars=200)
    adjustments_dump = [adj.model_dump() for adj in request.adjustments]
    adjustments_block = _format_adjustments_block(adjustments_dump)
    user_intent_block = (
        f"\n사용자 발화: \"{request.user_intent}\""
        if request.user_intent
        else ""
    )

    prompt = f"""당신은 포트폴리오 코치입니다. 사용자가 원본 포트폴리오에 다음 조정을 적용하려 합니다.
당신의 역할은 *정량 재계산 없이* 변경 전후를 자연어로 비교하고 해설하는 것입니다.

[원본 포트폴리오]
보유: {holdings_str}
요약: {analysis_one_liner}

[조정 명령]
{adjustments_block}{user_intent_block}

[출력 요구]
다음 JSON 형식으로만 응답하세요. 다른 텍스트 금지.

{{
  "headline": "비교 한 줄 요약 (10~120자)",
  "before_summary": "조정 전 포트폴리오 핵심 특징 (20~400자)",
  "after_summary": "조정 후 예상 포트폴리오 핵심 특징 (20~400자)",
  "key_changes": [
    {{"aspect": "allocation|risk|expected_return|diversification|other", "description": "변경 사항 한 문장 (10~300자)"}}
    // 1~5개
  ],
  "risk_assessment": "위험 변화 해설 (20~300자)",
  "closing_remarks": "마무리 해설 (10~300자)"
}}
"""
    return prompt


def parse_e6_response(text: str) -> E6ComparisonResponse:
    """LLM raw text → E6ComparisonResponse.

    parse_json_response 가 마크다운 펜스 사후 제거 + Pydantic 검증을 처리.
    """
    return parse_json_response(text, schema=E6ComparisonResponse)


def run_e6(
    request: E6Request,
    *,
    provider: ProviderLabel = "haiku",  # default — 글쓰기 가설 (Slice 1·2·3 정착)
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """E6 entry function.

    Args:
        request: E6Request — analysis_context + adjustments + (선택) user_intent.
        provider: label (default haiku — Slice 1·2·3 글쓰기 가설 정착).
        client: LLMClient 의존성 주입 (테스트 모킹용).

    Returns:
        dict: {"response": E6ComparisonResponse.model_dump(), "metadata": {...}}
    """
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. "
            f"Valid: {sorted(PROVIDER_KWARGS)}"
        )

    prompt = build_e6_prompt(request)

    if client is None:
        client = LLMClient()
    raw = client.complete(prompt=prompt, **PROVIDER_KWARGS[provider])

    parsed = parse_e6_response(raw.text)
    return {
        "response": parsed.model_dump(),
        "metadata": raw.metadata_dict(),
    }
```

### 4.2.2 service 단위 테스트는 Step 4에서

service의 단위 테스트는 Step 4의 통합 테스트에 흡수. Step 2 종료 시점에는 module import + smoke 호출만 검증.

### 4.2.3 Step 2 검증

```bash
# import 검증
python -c "from portfolio.services.e6_comparison import run_e6, build_e6_prompt, parse_e6_response; print('OK')"

# 회귀 영향 (service 추가가 기존 import chain 깨지 않는지)
pytest portfolio/tests/ -q --no-header 2>&1 | tail -3
# 예상: 128 passed (Step 1과 동일)
```

### 4.2.4 Step 2 완료 보고

```
## Step 2 완료 보고

- 신규 파일: portfolio/services/e6_comparison.py (~150줄)
- 함수 시그니처:
  - run_e6(request: E6Request, *, provider: ProviderLabel = "haiku", client: LLMClient | None = None) -> dict
  - build_e6_prompt(request: E6Request) -> str
  - parse_e6_response(text: str) -> E6ComparisonResponse
  - _format_adjustments_block(adjustments: list[dict]) -> str
- E2 service mirror 비율: ~80% (인터페이스 동일, prompt 본문만 E6 특화)
- 회귀: 128 passed 유지 (import chain 정상)
- 다음 step 진입 가능: Y/N
```

---

## Step 3 — View + URL 라우팅 (5~10분)

### 4.3.1 View 함수 추가

`portfolio/views.py`에 다음 함수 추가:

```python
# portfolio/views.py 에 추가

import json
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pydantic import ValidationError

from portfolio.schemas.llm import E6Request
from portfolio.services.e6_comparison import run_e6


@csrf_exempt
@require_http_methods(["POST"])
def coach_e6_comparison(request: HttpRequest) -> JsonResponse:
    """E6 (조정 후 비교 해설) HTTP entry.

    POST body 형식:
    {
        "analysis_context": {...},
        "adjustments": [...],
        "user_intent": "..."  // optional
    }

    Response:
    {
        "ok": true,
        "data": {"response": {...}, "metadata": {...}}
    }

    Error response:
    {"ok": false, "error": "...", "code": "validation_error" | "llm_error" | "internal"}
    """
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError as exc:
        return JsonResponse(
            {"ok": False, "error": f"invalid JSON: {exc}", "code": "validation_error"},
            status=400,
        )

    try:
        e6_request = E6Request.model_validate(payload)
    except ValidationError as exc:
        return JsonResponse(
            {"ok": False, "error": exc.errors(), "code": "validation_error"},
            status=400,
        )

    # provider override (선택, query string으로 받음)
    provider = request.GET.get("provider", "haiku")
    if provider not in ("haiku", "sonnet", "anthropic", "gemini"):
        return JsonResponse(
            {"ok": False, "error": f"unknown provider: {provider}", "code": "validation_error"},
            status=400,
        )

    try:
        result = run_e6(e6_request, provider=provider)
    except Exception as exc:
        # LLMError + 기타 예외 (Slice 1 패턴)
        return JsonResponse(
            {"ok": False, "error": str(exc), "code": "llm_error"},
            status=500,
        )

    return JsonResponse({"ok": True, "data": result}, status=200)
```

### 4.3.2 URL 라우팅 추가

`portfolio/urls.py`에 다음 path 추가:

```python
# portfolio/urls.py — urlpatterns 리스트에 추가

from portfolio.views import (
    coach_e1_garp,                    # Slice 1
    coach_e2_diagnostic_card,         # Slice 3
    coach_e5_adjustment,              # Slice 2
    coach_e6_comparison,              # Slice 4 (신규)
)

urlpatterns = [
    # ... 기존 path ...
    path("coach/e6/comparison/", coach_e6_comparison, name="coach_e6_comparison"),
]
```

### 4.3.3 View 단위 테스트는 Step 4에서

view의 통합 테스트는 Step 4에서 함께 처리.

### 4.3.4 Step 3 검증

```bash
# URL routing 검증
python manage.py show_urls 2>&1 | grep e6
# 예상: /coach/e6/comparison/

# 회귀
pytest portfolio/tests/ -q --no-header 2>&1 | tail -3
# 예상: 128 passed
```

### 4.3.5 Step 3 완료 보고

```
## Step 3 완료 보고

- 추가된 view: coach_e6_comparison (POST)
- 추가된 URL: /coach/e6/comparison/
- 입력 검증: JSON parse + Pydantic E6Request.model_validate
- provider override: query string (?provider=haiku|sonnet|anthropic|gemini)
- 에러 응답 형식: {"ok": false, "error": "...", "code": "validation_error" | "llm_error" | "internal"}
- 회귀: 128 passed 유지
- 다음 step 진입 가능: Y/N
```

---

## Step 4 — Mock LLM 통합 테스트 5 케이스 (15~20분)

### 4.4.1 Mock 등록 (text_strategy 패턴)

`portfolio/llm/mocks.py`에 e6 응답 생성 등록 (Slice 1·2·3 패턴 mirror):

````python
# portfolio/llm/mocks.py 의 text_strategy 등록 부분에 추가

def _e6_mock_text(_prompt: str, **_kw) -> str:
    """E6 (조정 후 비교 해설) Mock 응답.

    프롬프트 분석 없이 고정 형식 JSON 반환. 테스트 중 LLM 호출 비결정성 제거 목적.
    """
    return """```json
{
  "headline": "기술주 집중도 완화 + 디펜시브 보강으로 위험 균형 개선",
  "before_summary": "기술주 비중 70%, 단일 섹터 집중 위험 높음. 변동성 높은 성장주 위주.",
  "after_summary": "기술주 55%로 축소, 디펜시브 15% 추가. 변동성 대비 안정성 개선 예상.",
  "key_changes": [
    {"aspect": "allocation", "description": "테슬라 비중 20% → 10%로 축소"},
    {"aspect": "diversification", "description": "헬스케어 섹터 신규 진입 15%"},
    {"aspect": "risk", "description": "단일 섹터 집중도 위험 완화"}
  ],
  "risk_assessment": "포트폴리오 변동성이 다소 낮아지고 하방 리스크가 완화될 것으로 예상됩니다.",
  "closing_remarks": "수익률 상한선은 일부 양보될 수 있으나 장기 안정성 측면에서 합리적인 조정입니다."
}
```"""


# text_strategy 등록 (기존 dict에 추가)
_TEXT_STRATEGY: dict[str, Callable] = {
    # ... 기존 e1, e5, e2 등록 ...
    "e6": _e6_mock_text,
}
````

### 4.4.2 Service 단위 테스트 (5 케이스)

`portfolio/tests/test_e6_service.py` 신규:

````python
"""E6 service 단위 테스트.

Slice 1·2·3 패턴 mirror — 5 케이스: 정상 / RateLimit fallback / Timeout fallback /
Auth no-fallback / Budget guard.
"""

import pytest
from unittest.mock import patch, MagicMock

from portfolio.llm.client import LLMClient, LLMResponse
from portfolio.llm.exceptions import (
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthError,
    LLMBudgetError,
)
from portfolio.llm.mocks import MockLLMClient
from portfolio.schemas.llm import E6Request, AdjustmentItem
from portfolio.services.e6_comparison import run_e6


@pytest.fixture
def sample_e6_request() -> E6Request:
    return E6Request(
        analysis_context={
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.30},
                {"ticker": "TSLA", "weight": 0.20},
                {"ticker": "NVDA", "weight": 0.50},
            ],
            "analysis_summary": {"one_line_diagnosis": "기술주 집중 + 변동성 높음"},
        },
        adjustments=[
            AdjustmentItem(action="reduce", target="TSLA", target_weight=0.10),
            AdjustmentItem(action="add", target="JNJ", target_weight=0.15),
        ],
    )


def test_e6_normal_flow(sample_e6_request):
    """정상 흐름: Mock client + haiku → JSON parse → E6ComparisonResponse."""
    mock_client = MockLLMClient(strategy="e6")
    result = run_e6(sample_e6_request, provider="haiku", client=mock_client)
    assert "response" in result and "metadata" in result
    assert result["response"]["headline"]
    assert len(result["response"]["key_changes"]) >= 1
    assert result["metadata"]["provider"] in ("anthropic", "haiku")


def test_e6_ratelimit_fallback(sample_e6_request):
    """RateLimit 발생 시 LLMClient가 fallback (Slice 1 패턴 mirror)."""
    # primary call → RateLimit, fallback call → 정상
    primary_mock = MagicMock(side_effect=LLMRateLimitError("rate limit"))
    fallback_response = LLMResponse(
        text='```json\n{"headline":"...","before_summary":"' + 'a' * 30 + '","after_summary":"' + 'a' * 30 + '","key_changes":[{"aspect":"allocation","description":"' + 'a' * 30 + '"}],"risk_assessment":"' + 'a' * 30 + '","closing_remarks":"' + 'a' * 30 + '"}\n```',
        provider="anthropic",
        model="claude-haiku-4-5",
        latency_ms=100,
        input_tokens=500,
        output_tokens=300,
        cost_usd=0.001,
        fallback_from="gemini",
    )

    with patch.object(LLMClient, "complete", side_effect=[
        LLMRateLimitError("rate limit"),
        fallback_response,
    ]):
        # fallback 동작은 LLMClient 내부에서 처리 — service는 결과만 받음
        client = LLMClient()
        # 실제로는 LLMClient가 한 번의 complete 호출 안에서 fallback 시도하므로
        # patch 형태는 LLMClient 내부 _call_provider 단을 mock해야 함.
        # Slice 1 test_e1_service.py 의 fallback 테스트 패턴 직접 참조.
        # 본 테스트는 그 패턴을 mirror하여 작성. (구체 patch target은 LLMClient 구현에 따름)
    # NOTE: 본 테스트의 정확한 patch target은 portfolio/tests/test_e1_service.py 의
    # test_ratelimit_fallback 케이스와 동일 패턴으로 작성. Slice 1 인프라 그대로 활용.


def test_e6_timeout_fallback(sample_e6_request):
    """Timeout 발생 시 fallback (Slice 1 패턴 mirror)."""
    # 동일하게 Slice 1 test_e1_service.py 패턴 mirror.
    pass  # 실제 구현은 LLMClient mock target 결정 후 작성


def test_e6_auth_error_no_fallback(sample_e6_request):
    """Auth 오류는 fallback 안 함 — 즉시 raise."""
    with patch.object(LLMClient, "complete", side_effect=LLMAuthError("invalid api key")):
        with pytest.raises(LLMAuthError):
            run_e6(sample_e6_request, provider="haiku")


def test_e6_budget_guard_trigger(sample_e6_request):
    """CostGuard 한도 초과 시 LLMBudgetError raise."""
    with patch.object(LLMClient, "complete", side_effect=LLMBudgetError("budget exceeded")):
        with pytest.raises(LLMBudgetError):
            run_e6(sample_e6_request, provider="haiku")


def test_e6_unknown_provider_raises(sample_e6_request):
    """Unknown provider label → ValueError."""
    with pytest.raises(ValueError, match="Unknown provider label"):
        run_e6(sample_e6_request, provider="unknown_provider")
````

### 4.4.3 View 통합 테스트

`portfolio/tests/test_e6_view.py` 신규:

```python
"""E6 view 통합 테스트."""

import json
import pytest
from django.test import Client
from django.urls import reverse

from portfolio.llm.mocks import MockLLMClient
from portfolio.services import e6_comparison


@pytest.fixture
def sample_payload() -> dict:
    return {
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.30},
                {"ticker": "TSLA", "weight": 0.20},
                {"ticker": "NVDA", "weight": 0.50},
            ],
            "analysis_summary": {"one_line_diagnosis": "기술주 집중"},
        },
        "adjustments": [
            {"action": "reduce", "target": "TSLA", "target_weight": 0.10},
            {"action": "add", "target": "JNJ", "target_weight": 0.15},
        ],
        "user_intent": "테슬라 줄이고 존슨앤존슨 추가",
    }


@pytest.mark.django_db
def test_e6_view_normal(client: Client, sample_payload, monkeypatch):
    """View 정상 흐름: 200 + ok=True + data 키 존재."""
    # service 레벨에서 Mock client 주입
    def fake_run_e6(request, *, provider="haiku", client=None):
        if client is None:
            client = MockLLMClient(strategy="e6")
        # 실제 run_e6 호출 (Mock client로)
        return e6_comparison.run_e6(request, provider=provider, client=client)
    monkeypatch.setattr(e6_comparison, "run_e6", fake_run_e6)

    response = client.post(
        "/coach/e6/comparison/",
        data=json.dumps(sample_payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "data" in body
    assert "response" in body["data"]
    assert "metadata" in body["data"]


@pytest.mark.django_db
def test_e6_view_invalid_json(client: Client):
    """잘못된 JSON → 400."""
    response = client.post(
        "/coach/e6/comparison/",
        data="not a json",
        content_type="application/json",
    )
    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["code"] == "validation_error"


@pytest.mark.django_db
def test_e6_view_validation_error(client: Client):
    """adjustments 빈 리스트 → 400 (Pydantic validation)."""
    payload = {
        "analysis_context": {"preset_id": "garp"},
        "adjustments": [],  # invalid
    }
    response = client.post(
        "/coach/e6/comparison/",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["code"] == "validation_error"


@pytest.mark.django_db
def test_e6_view_unknown_provider(client: Client, sample_payload):
    """unknown provider → 400."""
    response = client.post(
        "/coach/e6/comparison/?provider=unknown",
        data=json.dumps(sample_payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False


@pytest.mark.django_db
def test_e6_view_get_method_not_allowed(client: Client):
    """GET → 405."""
    response = client.get("/coach/e6/comparison/")
    assert response.status_code == 405
```

### 4.4.4 fallback / timeout 케이스의 정확한 patch target

위 `test_e6_ratelimit_fallback` / `test_e6_timeout_fallback`은 **`portfolio/tests/test_e1_service.py`의 동일 케이스를 직접 참조하여 같은 패턴으로 작성**할 것. LLMClient 내부 `_call_provider` 또는 그에 상응하는 메서드를 patch하는 방식. Slice 1·2·3에서 검증된 패턴을 그대로 mirror.

만약 Slice 1 인프라에서 정확한 patch target을 찾기 어려우면, 본 두 케이스는 **잠시 보류** (Slice 1 코드 인용 후 적용). 대신 다음 3 케이스(normal / auth / budget)와 view 5 케이스 = 8 테스트로 Step 4 회귀 +8 확보.

### 4.4.5 Step 4 검증

```bash
pytest portfolio/tests/test_e6_service.py portfolio/tests/test_e6_view.py -v
# 예상: 8~10 passed (fallback 2 케이스 보류 시 8, 적용 시 10)

pytest portfolio/tests/ -q --no-header 2>&1 | tail -3
# 예상: 136~138 passed (128 + 8~10)
```

### 4.4.6 Step 4 완료 보고

```
## Step 4 완료 보고

- Mock 전략 등록: e6 → _e6_mock_text 함수
- Service 테스트: <N>개 (normal / fallback ratelimit / fallback timeout / auth no-fallback / budget guard / unknown provider)
- View 테스트: 5개 (normal / invalid_json / validation_error / unknown_provider / method_not_allowed)
- fallback 케이스 적용 여부: 적용 / 보류(이유: ___)
- 회귀: 128 → <136~138> passed (+<8~10>)
- 다음 step 진입 가능: Y/N
```

---

## Step 5 — Hybrid 7 fixture 작성 (15~20분)

### 4.5.1 fixture 신규 파일

`portfolio/tests/fixtures/sample_comparison_context.py` 신규 작성. **Slice 2 `sample_adjustment_context.py`의 `clear_*` 3개 직접 import + E5 결과(adjustments) 추가** + e6_focused 4개 신규 작성.

```python
"""E6 (조정 후 비교 해설) fixture.

Hybrid 7 패턴 — Slice 1·3 mirror:
  - e5_baseline 3개 (Slice 2 sample_adjustment_context의 clear_* 재활용 + adjustments 추가)
  - e6_focused 4개 (비중 변경 / 종목 추가 / 종목 제거 / 다중 조정)

사용처:
  - Slice 4 Step 4 통합 테스트
  - Slice 4 Part 2 Step 8 회고 (haiku 7 + sonnet 7 = 14 calls)
"""

from typing import Any

# Slice 2 인프라 재활용
from portfolio.tests.fixtures.sample_adjustment_context import (
    clear_reduce_tesla,
    clear_add_microsoft,
    clear_remove_nvidia,
)


# ============================================================
# baseline 그룹 (3개) — Slice 2 E5 fixture 재활용
# ============================================================

def e5_baseline_reduce() -> dict[str, Any]:
    """Slice 2 clear_reduce_tesla 재활용.

    원본 E5 입력에 *adjustments 결과를 추가*하여 E6Request 형태로 변환.
    """
    base = clear_reduce_tesla()
    return {
        "analysis_context": base["analysis_context"],
        "adjustments": [
            {"action": "reduce", "target": "TSLA", "target_weight": 0.10}
        ],
        "user_intent": base.get("user_intent"),
        "_group": "e5_baseline",
        "_fixture_id": "e5_baseline_reduce",
    }


def e5_baseline_add() -> dict[str, Any]:
    """Slice 2 clear_add_microsoft 재활용."""
    base = clear_add_microsoft()
    return {
        "analysis_context": base["analysis_context"],
        "adjustments": [
            {"action": "add", "target": "MSFT", "target_weight": 0.15}
        ],
        "user_intent": base.get("user_intent"),
        "_group": "e5_baseline",
        "_fixture_id": "e5_baseline_add",
    }


def e5_baseline_remove() -> dict[str, Any]:
    """Slice 2 clear_remove_nvidia 재활용."""
    base = clear_remove_nvidia()
    return {
        "analysis_context": base["analysis_context"],
        "adjustments": [
            {"action": "remove", "target": "NVDA", "target_weight": 0.0}
        ],
        "user_intent": base.get("user_intent"),
        "_group": "e5_baseline",
        "_fixture_id": "e5_baseline_remove",
    }


# ============================================================
# focused 그룹 (4개) — Slice 4 신규
# E6 비교 해설 차원에 특화 — 4가지 주요 시나리오
# ============================================================

def e6_focused_weight_rebalance() -> dict[str, Any]:
    """비중 재조정만 — 종목 추가/제외 없음."""
    return {
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.40},
                {"ticker": "GOOGL", "weight": 0.30},
                {"ticker": "AAPL", "weight": 0.30},
            ],
            "analysis_summary": {
                "one_line_diagnosis": "GARP 프리셋, 빅테크 균등 분산 — 안정적이나 성장 모멘텀 부족"
            },
        },
        "adjustments": [
            {"action": "reduce", "target": "AAPL", "target_weight": 0.20},
            {"action": "increase", "target": "GOOGL", "target_weight": 0.40},
        ],
        "user_intent": "애플 줄이고 구글 늘려",
        "_group": "e6_focused",
        "_fixture_id": "e6_focused_weight_rebalance",
    }


def e6_focused_add_defensive() -> dict[str, Any]:
    """디펜시브 종목 신규 진입 (집중도 위험 완화 시나리오)."""
    return {
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "TSLA", "weight": 0.30},
                {"ticker": "NVDA", "weight": 0.40},
                {"ticker": "AMD", "weight": 0.30},
            ],
            "analysis_summary": {
                "one_line_diagnosis": "기술주 집중 100% — 단일 섹터 위험 매우 높음"
            },
        },
        "adjustments": [
            {"action": "reduce", "target": "TSLA", "target_weight": 0.20},
            {"action": "reduce", "target": "NVDA", "target_weight": 0.30},
            {"action": "add", "target": "JNJ", "target_weight": 0.15},
            {"action": "add", "target": "PG", "target_weight": 0.05},
        ],
        "user_intent": "기술주 비중 좀 줄이고 디펜시브 추가해줘",
        "_group": "e6_focused",
        "_fixture_id": "e6_focused_add_defensive",
    }


def e6_focused_remove_underperformer() -> dict[str, Any]:
    """부진 종목 제외."""
    return {
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.25},
                {"ticker": "AMZN", "weight": 0.25},
                {"ticker": "META", "weight": 0.25},
                {"ticker": "PYPL", "weight": 0.25},
            ],
            "analysis_summary": {
                "one_line_diagnosis": "GARP 균등 분산, PYPL이 최근 약세"
            },
        },
        "adjustments": [
            {"action": "remove", "target": "PYPL", "target_weight": 0.0},
            {"action": "increase", "target": "MSFT", "target_weight": 0.35},
            {"action": "increase", "target": "AMZN", "target_weight": 0.40},
        ],
        "user_intent": "페이팔 빼고 마이크로소프트랑 아마존 늘려",
        "_group": "e6_focused",
        "_fixture_id": "e6_focused_remove_underperformer",
    }


def e6_focused_multi_aspect() -> dict[str, Any]:
    """다중 차원 동시 조정 — 가장 복잡한 시나리오 (할당+추가+제외+위험 동시)."""
    return {
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "TSLA", "weight": 0.20},
                {"ticker": "NVDA", "weight": 0.20},
                {"ticker": "MSFT", "weight": 0.20},
                {"ticker": "GOOGL", "weight": 0.20},
                {"ticker": "AAPL", "weight": 0.20},
            ],
            "analysis_summary": {
                "one_line_diagnosis": "빅테크 균등 5개 — 분산이나 섹터는 단일"
            },
        },
        "adjustments": [
            {"action": "remove", "target": "TSLA", "target_weight": 0.0},
            {"action": "reduce", "target": "NVDA", "target_weight": 0.10},
            {"action": "increase", "target": "MSFT", "target_weight": 0.25},
            {"action": "add", "target": "BRK.B", "target_weight": 0.20},
            {"action": "add", "target": "JPM", "target_weight": 0.10},
        ],
        "user_intent": "테슬라 빼고 엔비디아 좀 줄이고, MSFT 늘리면서 버크셔랑 JPM 추가해",
        "_group": "e6_focused",
        "_fixture_id": "e6_focused_multi_aspect",
    }


# ============================================================
# 헬퍼 — 전체 fixture 리스트
# ============================================================

ALL_FIXTURES = [
    e5_baseline_reduce,
    e5_baseline_add,
    e5_baseline_remove,
    e6_focused_weight_rebalance,
    e6_focused_add_defensive,
    e6_focused_remove_underperformer,
    e6_focused_multi_aspect,
]


def get_all_fixtures() -> list[dict[str, Any]]:
    """모든 fixture 인스턴스화하여 반환."""
    return [fn() for fn in ALL_FIXTURES]


def get_baseline_fixtures() -> list[dict[str, Any]]:
    return [fn() for fn in ALL_FIXTURES if "baseline" in fn.__name__ or fn.__name__.startswith("e5_baseline")]


def get_focused_fixtures() -> list[dict[str, Any]]:
    return [fn() for fn in ALL_FIXTURES if fn.__name__.startswith("e6_focused")]
```

### 4.5.2 Slice 2 fixture 인터페이스 검증 (사전 점검)

Step 5 작업 시작 직전:

```bash
grep -n "def clear_" portfolio/tests/fixtures/sample_adjustment_context.py
```

기대: `clear_reduce_tesla`, `clear_add_microsoft`, `clear_remove_nvidia` 함수 존재.

만약 Slice 2 fixture 함수명이 다르면(예: `clear_*_intent`처럼 다른 패턴) → fixture import 시 함수명 정정. **함수명 정정만 허용** — fixture 본문 변경 금지.

### 4.5.3 fixture 단위 테스트 (Step 5 회귀 추가)

`portfolio/tests/test_e6_fixtures.py` 신규:

```python
"""E6 fixture 단위 테스트."""

import pytest

from portfolio.schemas.llm import E6Request
from portfolio.tests.fixtures.sample_comparison_context import (
    ALL_FIXTURES,
    get_all_fixtures,
    get_baseline_fixtures,
    get_focused_fixtures,
)


def test_all_fixtures_count():
    """7개 fixture 정의."""
    assert len(ALL_FIXTURES) == 7


def test_baseline_count():
    """baseline 그룹 3개."""
    baseline = get_baseline_fixtures()
    assert len(baseline) == 3
    for fx in baseline:
        assert fx["_group"] == "e5_baseline"


def test_focused_count():
    """focused 그룹 4개."""
    focused = get_focused_fixtures()
    assert len(focused) == 4
    for fx in focused:
        assert fx["_group"] == "e6_focused"


@pytest.mark.parametrize("fixture_fn", ALL_FIXTURES)
def test_fixture_satisfies_e6_request_schema(fixture_fn):
    """모든 fixture는 E6Request schema를 만족."""
    fx = fixture_fn()
    # _group, _fixture_id 등 메타 필드 제거 후 E6Request 검증
    payload = {
        "analysis_context": fx["analysis_context"],
        "adjustments": fx["adjustments"],
    }
    if fx.get("user_intent"):
        payload["user_intent"] = fx["user_intent"]
    req = E6Request.model_validate(payload)
    assert len(req.adjustments) >= 1


def test_fixture_ids_unique():
    """fixture_id 중복 없음."""
    ids = [fn()["_fixture_id"] for fn in ALL_FIXTURES]
    assert len(set(ids)) == len(ids)


def test_focused_multi_aspect_complexity():
    """e6_focused_multi_aspect은 5개 이상 adjustment."""
    from portfolio.tests.fixtures.sample_comparison_context import (
        e6_focused_multi_aspect,
    )
    fx = e6_focused_multi_aspect()
    assert len(fx["adjustments"]) >= 5
```

### 4.5.4 Step 5 검증

```bash
pytest portfolio/tests/test_e6_fixtures.py -v
# 예상: ~12 passed (parametrize 7 + 일반 5)

pytest portfolio/tests/ -q --no-header 2>&1 | tail -3
# 예상: 148~155 passed (Step 4 종결 + 12)
```

### 4.5.5 Step 5 완료 보고

```
## Step 5 완료 보고

- 신규 파일: portfolio/tests/fixtures/sample_comparison_context.py (~200줄)
- baseline 그룹 (Slice 2 재활용): e5_baseline_reduce / e5_baseline_add / e5_baseline_remove
- focused 그룹 (신규): e6_focused_weight_rebalance / e6_focused_add_defensive / e6_focused_remove_underperformer / e6_focused_multi_aspect
- Slice 2 import 함수: clear_reduce_tesla / clear_add_microsoft / clear_remove_nvidia
- (Slice 2 함수명 정정 발생 여부): 발생 / 미발생 (정정한 경우 원본 → 정정 매핑 명시)
- fixture 단위 테스트: 12개 (parametrize 7 + 일반 5)
- 회귀: <Step 4 종결 카운트> → <Step 5 종결 카운트> passed (+12)
- Part 1 종결 회귀 카운트: <최종>
```

---

# §5. 검증 지점

## 5.1 단계별 회귀 카운트 진행 표 (예상)

| 단계                  | 추가 테스트 | 누적        | 비고                                           |
| --------------------- | ----------- | ----------- | ---------------------------------------------- |
| Slice 3 종결 baseline | —           | 123         |                                                |
| Step 0 (환경 점검)    | 0           | 123         | reset_for_slice 호출만                         |
| Step 1 (schema)       | +5          | 128         | E6Request / E6ComparisonResponse / E6KeyChange |
| Step 2 (service)      | 0           | 128         | 단위 테스트는 Step 4에 흡수                    |
| Step 3 (view + url)   | 0           | 128         | view 테스트는 Step 4에 흡수                    |
| Step 4 (Mock test)    | +8~10       | 136~138     | service 5~6 + view 5                           |
| Step 5 (fixture)      | +12         | **148~150** | parametrize 7 + 일반 5                         |

**Part 1 종결 예상 회귀: 148~150 passed** (Slice 3 +25~27 패턴).

> Slice 3에서 Part 1 종결 시점 회귀 +24 (76→100 추정), Part 2 종결 +23 (100→123). Slice 4도 Part 1 종결 +25, Part 2 종결 +20 패턴 예상 → 최종 ~170.

## 5.2 검증 판정 표

| #   | 검증 항목                                | 임계                                               | 자동/수동 |
| --- | ---------------------------------------- | -------------------------------------------------- | --------- |
| 1   | git branch / status 정상                 | branch=feature/chainsight-graph-v2 + clean         | 자동      |
| 2   | 회귀 baseline 일치                       | 123 passed                                         | 자동      |
| 3   | CostGuard reset 동작                     | slice_id="slice4"                                  | 자동      |
| 4   | E6Request / E6ComparisonResponse 검증    | 5 schema 테스트 통과                               | 자동      |
| 5   | service module import 성공               | `from portfolio.services.e6_comparison import ...` | 자동      |
| 6   | URL 라우팅 등록                          | `/coach/e6/comparison/`                            | 자동      |
| 7   | Mock 통합 테스트                         | 8~10 통과                                          | 자동      |
| 8   | hybrid 7 fixture 검증                    | 12 통과                                            | 자동      |
| 9   | Slice 1/2/3 회귀 영향 0                  | 123 → 148~150 (감소 없음)                          | 자동      |
| 10  | 신규 코드량                              | ~600~750줄                                         | 수동      |
| 11  | E2 service mirror 비율                   | ~80% (인터페이스 동일)                             | 수동      |
| 12  | Slice 2 fixture 함수명 정정 발생 시 보고 | (해당 시)                                          | 수동      |

## 5.3 롤백 / 실패 시 처리

각 Step 종료 시점 git commit 권장 (rollback 단위). Step 단위 commit 메시지 패턴:

```
slice4 step<N>: <짧은 요약>

- 추가/변경 사항 1
- 추가/변경 사항 2
- 회귀: <before> → <after> passed
```

**케이스 A. Step 1에서 schema 검증 실패**: D-7 스켈레톤과 본 지시서 1차 권장의 차이가 클 때 발생. Claude Code는 D-7 스켈레톤 우선 + 본 지시서를 참고로 처리. 차이 보고 후 사용자 에스컬레이션 → 사용자 결정에 따라 schema 조정.

**케이스 B. Step 2에서 prompt builder 의존성 부재**: `_prompt_helpers.format_holdings_summary` 등이 E5 fixture의 holdings 형식과 호환되지 않을 때. → 어댑터 함수를 service 내부에 추가 (외부 helper 변경 금지).

**케이스 C. Step 4에서 fallback 케이스 patch target 불명확**: Slice 1 `test_e1_service.py` 인용해 동일 패턴 적용. 해결 안 되면 fallback 2 케이스 보류 + Step 4 종결 회귀 +8로 진입 (정상 / auth / budget / view 5).

**케이스 D. Step 5에서 Slice 2 fixture 함수명 불일치**: 함수명만 정정 (본문 변경 금지). 정정 매핑 보고.

**케이스 E. 회귀 카운트 감소 (Slice 1·2·3 영향)**: 즉시 중단. 변경 사항 git revert. 사용자 에스컬레이션. 임의 수정 금지.

---

# §6. 판단 허용 / 금지 범위 (Claude Code 자율성 경계)

## 6.1 허용 (Claude Code 판단 권한 행사 가능)

| 영역                                                         | 권한                                         | 사용 시 보고            |
| ------------------------------------------------------------ | -------------------------------------------- | ----------------------- |
| Schema 필드 이름 / 타입 미세 조정 (D-7 스켈레톤 정합성 우선) | ✅                                           | Step 1 보고에 차이 명시 |
| prompt 본문 자연어 표현 / 한국어 어조                        | ✅                                           | 보고 불요               |
| Mock 응답 자연어 본문 (JSON 구조는 schema 준수)              | ✅                                           | 보고 불요               |
| 테스트 fixture 헬퍼 함수 추가 (예: 메타 필드 제거 헬퍼)      | ✅                                           | 보고 불요               |
| 코드 스타일 (black/ruff 자동 포맷)                           | ✅                                           | 보고 불요               |
| import 순서 (isort 자동)                                     | ✅                                           | 보고 불요               |
| logger 추가 (debug 용이성)                                   | ✅ (`logging.getLogger(__name__)` 표준 패턴) | 보고 불요               |
| 케이스 C·D 발생 시 fallback 케이스 보류 / 함수명 정정        | ✅                                           | 보고 필수               |

## 6.2 금지 (사용자 에스컬레이션 필수)

| 영역                                                            | 사유                    |
| --------------------------------------------------------------- | ----------------------- |
| AnalysisContext schema 변경                                     | Slice 1/2/3 회귀 영향 ↑ |
| AdjustmentItem schema 변경                                      | Slice 2 회귀 영향       |
| `portfolio/llm/` 하위 모듈 _공개 인터페이스_ 변경               | Slice 1·2·3 회귀 영향   |
| `portfolio/services/_llm_kwargs.py` / `_prompt_helpers.py` 변경 | Slice 1·2·3 회귀 영향   |
| Slice 2 fixture 함수 _본문_ 수정 (함수명 정정만 허용)           | Slice 2 회귀 영향       |
| 회귀 카운트 감소를 일으키는 모든 변경                           | baseline 보존           |
| Step 6~9 영역 침범 (실 LLM 호출 / token 측정 / 산식 통합)       | Part 1 스코프 위반      |
| 분석 엔진 재계산 로직 추가 (조정 후 AnalysisContext)            | Phase 2 스코프          |
| 본 지시서가 명시한 산출물 외 추가 파일 생성                     | 스코프 위반             |
| `requirements.txt` / `pyproject.toml` 의존성 추가               | 환경 변경               |
| `.env` 변경                                                     | 환경 변경               |

## 6.3 균형 모드 명시

본 지시서는 **균형 모드** (Slice 1·2·3와 동일):

- 구조 (디렉토리, 모듈 분리, 함수 시그니처) = **처방**
- 구현 세부 (변수명, 자연어 본문, prompt 어조, logger 위치) = **위임**

---

# §7. 산출물

## 7.1 신규 / 수정 파일 목록

| 파일                                                    | 종류                                           | 줄 수 | Step   |
| ------------------------------------------------------- | ---------------------------------------------- | ----- | ------ |
| `portfolio/schemas/llm.py`                              | 수정 (E6Request 추가)                          | +30   | Step 1 |
| `portfolio/schemas/llm_outputs.py`                      | 수정 (E6KeyChange + E6ComparisonResponse 추가) | +50   | Step 1 |
| `portfolio/services/e6_comparison.py`                   | 신규                                           | ~150  | Step 2 |
| `portfolio/views.py`                                    | 수정 (coach_e6_comparison 추가)                | +30   | Step 3 |
| `portfolio/urls.py`                                     | 수정 (path 추가)                               | +5    | Step 3 |
| `portfolio/llm/mocks.py`                                | 수정 (e6 strategy 등록)                        | +25   | Step 4 |
| `portfolio/tests/test_e6_schema.py`                     | 신규                                           | ~80   | Step 1 |
| `portfolio/tests/test_e6_service.py`                    | 신규                                           | ~150  | Step 4 |
| `portfolio/tests/test_e6_view.py`                       | 신규                                           | ~100  | Step 4 |
| `portfolio/tests/test_e6_fixtures.py`                   | 신규                                           | ~70   | Step 5 |
| `portfolio/tests/fixtures/sample_comparison_context.py` | 신규                                           | ~200  | Step 5 |

**총 신규 코드: ~720줄, 신규 파일 6개, 수정 파일 5개**.

## 7.2 산출물 검증 명령

Step 5 종결 시점:

```bash
# 1. 회귀 카운트
pytest portfolio/tests/ -q --no-header 2>&1 | tail -3
# 예상: 148~150 passed

# 2. E6 진입점 단독 회귀
pytest portfolio/tests/test_e6_*.py -v
# 예상: 25~27 passed (schema 5 + service 8~10 + view 5 + fixture 12)

# 3. Slice 1/2/3 회귀 보존 확인
pytest portfolio/tests/test_e1_*.py portfolio/tests/test_e2_*.py portfolio/tests/test_e5_*.py -v
# 예상: Slice 1·2·3 회귀 카운트 그대로 유지

# 4. import chain 정상
python -c "
from portfolio.schemas.llm import E6Request
from portfolio.schemas.llm_outputs import E6ComparisonResponse, E6KeyChange
from portfolio.services.e6_comparison import run_e6, build_e6_prompt, parse_e6_response
from portfolio.views import coach_e6_comparison
from portfolio.tests.fixtures.sample_comparison_context import ALL_FIXTURES, get_all_fixtures
print('OK')
"

# 5. URL 라우팅 등록
python manage.py show_urls 2>&1 | grep e6
# 예상: /coach/e6/comparison/
```

## 7.3 git commit 권장 단위

Part 1 진입 후 6개 commit 권장:

```
1. slice4 step0: env check + cost guard reset (slice4 진입)
2. slice4 step1: E6 schema (E6Request / E6ComparisonResponse / E6KeyChange) + 5 schema tests
3. slice4 step2: E6 service (run_e6 + build_e6_prompt + parse_e6_response)
4. slice4 step3: E6 view + URL routing
5. slice4 step4: E6 Mock integration tests (service 5~6 + view 5)
6. slice4 step5: E6 hybrid 7 fixtures (e5_baseline 3 + e6_focused 4) + 12 fixture tests
```

각 commit 메시지에 회귀 before/after 명시.

---

# §8. 완료 보고 포맷

Part 1 종결 시점 사용자에게 다음 형식으로 보고:

```
# Slice 4 Part 1 완료 보고

## §A. 환경 정합성
- git branch: <확인>
- git status: clean
- 회귀 baseline 진입 시: 123 passed
- 회귀 Part 1 종결: <최종 카운트> passed (+<증가>)
- CostGuard 종결 상태: slice_id="slice4", call_count=0, max_calls=50, total_cost_usd=0.0

## §B. Step별 진척
| Step | 산출물 | 회귀 변화 | 시간 |
|---|---|---|---|
| 0 | 환경 점검 + reset | 0 | <분> |
| 1 | E6 schema + 5 tests | +5 | <분> |
| 2 | E6 service | 0 | <분> |
| 3 | View + URL | 0 | <분> |
| 4 | Mock tests | +<8~10> | <분> |
| 5 | Hybrid 7 fixture + 12 tests | +12 | <분> |

## §C. 신규 / 수정 파일
- <목록 + 줄 수>

## §D. D-7 스켈레톤 활용 결과
- 입력 필드 차이: <명시>
- 출력 필드 차이: <명시>
- 자연어 / JSON 형식 차이: <명시>

## §E. Slice 2 fixture 재활용 결과
- 재활용 함수: clear_reduce_tesla / clear_add_microsoft / clear_remove_nvidia
- 함수명 정정 발생 여부: 발생 / 미발생
- (정정 시) 매핑: <원본 → 정정>

## §F. 케이스 A~E 발생 여부
- 케이스 A (D-7 schema 차이): 해당 / 없음
- 케이스 B (helper 의존성): 해당 / 없음
- 케이스 C (fallback patch target): 해당 / 없음
- 케이스 D (fixture 함수명): 해당 / 없음
- 케이스 E (회귀 감소): **반드시 "없음"** (해당 시 즉시 에스컬레이션 했어야 함)

## §G. Part 2 (Step 6~9) 진입 준비 사항
- token_budgets.py 에 e6 추가 위치 확인: ENTRYPOINT_TOKEN_BUDGETS dict 의 라인 <번호>
- score_step8.py DIMENSION_LOOKUP 확장 위치 확인: 라인 <번호>
- E6 prompt 토큰 추정 (offline): 입력 평균 ~<N> 토큰, 출력 평균 ~<N> 토큰

## §H. Slice 4 Part 1 KPI
- [ ] 회귀: 148~150 passed (목표 ±2)
- [ ] CostGuard reset 동작 검증
- [ ] hybrid 7 fixture 작성 (baseline 3 + focused 4)
- [ ] Mock test 5+ 케이스
- [ ] E2 service mirror 비율 ~80%
- [ ] Slice 1·2·3 회귀 보존 (감소 없음)
- [ ] D4 가이드 준비 (Part 2 산출물에 _json_default + round-trip 적용 예정)

## §I. Part 2 진입 결정 자료
- LLM 호출 마진 (CostGuard): 50/50 (Step 6 1 + Step 8 14 + 재시도 ~3 = ~18 예상)
- E6 default provider 결정 검증 시점: Step 8 (haiku 7 + sonnet 7 회고)
- Step 9 슬롯 작업: #2 score 산식 통합 (e1/e2/e6 main() 통일, 30분 한도)
- 회고 후 winner 결정 (글쓰기 가설 4번째 검증)
```

---

# §9. 변경 이력

## 9.1 본 지시서 변경 이력

| 일자       | 버전 | 변경 사항                                                            |
| ---------- | ---- | -------------------------------------------------------------------- |
| 2026-05-07 | v1.0 | 초안 작성. Slice 4 결정 (E6 진입점 + hybrid 7 + Step 9 #2 통합) 반영 |

## 9.2 Slice 4 결정 변경 이력

| 일자                | 결정                                                                                | 근거                                                              |
| ------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 2026-05-07 (사전)   | Slice 4 진입점 = E3 (지표 코멘트)                                                   | 가중합 4.10 vs 4.00 (E6 + 의존성검증) — 메모리 슬라이스 순서 준수 |
| 2026-05-07 (재검토) | Slice 4 진입점 = **E6** (조정 후 비교 해설)                                         | 사용자 결정 — 클로드 코드 §10.1 권장(E5 흐름 통합 가치) 채택      |
| 2026-05-07          | Q1 (매트릭스 범위) = E3 한정 결정으로 자동 폐기 → 옵션 A' (hybrid 7 fixture)        | 진입점 변경에 따른 자동 변환. 종합 분석 §10.1 Q3 권장 그대로      |
| 2026-05-07          | Q2 (Step 9 슬롯) = #2 score 산식 통합 (e1/e2/e3 → e1/e2/e6)                         | 자동 변환. 글쓰기 진입점 동일, PS 3.0 동일                        |
| 2026-05-07          | Slice 5/6 사전 등록: E3 preset 외삽 검증 (insight 차원 그룹차 0.67~0.83 위험)       | E3 진입점 보존 — Slice 4 단점 보완                                |
| 2026-05-07          | Slice 5 진입점 후보 1순위: E6 → 변경 (Slice 4가 E6 흡수). Slice 5 후보는 E3 또는 E4 | Slice 4 = E6 확정에 따른 자동 갱신                                |

---

# 부록 A — Slice 4 종결 결정 표 (Part 1 시점)

| 항목                   | 값                                                                      |
| ---------------------- | ----------------------------------------------------------------------- |
| 진입점                 | **E6** (조정 후 비교 해설)                                              |
| Default provider       | **haiku** (글쓰기 가설 4번째 외삽 검증)                                 |
| Fixture 전략           | hybrid 7 (e5_baseline 3 재활용 + e6_focused 4 신규)                     |
| 평가 차원              | naturalness / insight (manual) + completeness (자동)                    |
| Step 8 매트릭스        | 7×2=14 (haiku 7 + sonnet 7)                                             |
| Step 9 슬롯 작업       | **#2 score 산식 통합** (e1/e2/e6 main() 통일, e5 delegation 유지, 30분) |
| Step 8 winner          | (Part 2 종결 후 기재)                                                   |
| fixture 그룹 비교 결과 | (Part 2 종결 후 기재)                                                   |
| 누적 호출 (Slice 4)    | (Part 2 종결 후 기재)                                                   |
| 누적 비용 (Slice 4)    | (Part 2 종결 후 기재)                                                   |
| Slice 5 진입 결정      | Slice 4 종결 회고 시                                                    |

---

# 부록 B — Slice 4 백로그 처리 계획

## B.1 Slice 3 이연 9건의 Slice 4 처리

| #   | 항목                                | PS  | Slice 4 처리                                              |
| --- | ----------------------------------- | --- | --------------------------------------------------------- |
| 2   | score 산식 통합 (e1+e2+e3→e1+e2+e6) | 3.0 | **Slice 4 Step 9 슬롯 (Part 2)**                          |
| 5   | TOKEN_BUDGET LLMClient 통합 (잔여)  | 2.0 | Slice 5 이연                                              |
| 6   | Step 8 CSV 옵션                     | 1.0 | Slice 5 이연                                              |
| 7   | Mock mode dict 매핑                 | 1.0 | Slice 5 이연                                              |
| 8   | LLMClient entrypoint 인자           | 2.5 | Slice 5 이연                                              |
| 9   | latency 임계 16,000ms 상향          | 2.0 | Slice 4 Part 2 Step 6 (smoke test 진입 시점에 처리, ~5분) |
| 10  | E2 keyword_match 룰 보완            | 1.5 | Slice 5 이연 (E2 한정)                                    |
| 11  | metrics_table 일반화                | 1.5 | Slice 5 이연 (E3 진입 시 처리)                            |

## B.2 Slice 4 신규 백로그 (Part 1 산출 예정)

`docs/portfolio/coach/slice4/refactor_backlog_slice4.md` (Part 2 종결 시 작성):

- E6 prompt 토큰 측정 결과 → e6 budget 결정
- E6 fallback 정책 검증 (RateLimit / Timeout 케이스가 실 호출에서 발생했는지)
- Slice 5/6 진입점 결정 (E3 preset 외삽 검증 우선 vs E4 대화 Q&A 우선)

---

# 부록 C — 회귀 카운트 진행 표

| 단계                                              | 추가 테스트 | 누적        | 비고                                           |
| ------------------------------------------------- | ----------- | ----------- | ---------------------------------------------- |
| Slice 3 종결                                      | —           | 123         | baseline                                       |
| Step 0 (환경 점검)                                | 0           | 123         |                                                |
| Step 1 (schema + 5 tests)                         | +5          | 128         | E6Request / E6ComparisonResponse / E6KeyChange |
| Step 2 (service)                                  | 0           | 128         | 단위 테스트는 Step 4에 흡수                    |
| Step 3 (view + url)                               | 0           | 128         | view 테스트는 Step 4에 흡수                    |
| Step 4 (Mock test)                                | +8~10       | 136~138     | service 5~6 + view 5                           |
| Step 5 (hybrid 7 + 12 tests)                      | +12         | **148~150** | Part 1 종결                                    |
| Part 2 Step 6 (smoke 산출물만)                    | 0           | 148~150     |                                                |
| Part 2 Step 7 (token 측정, e6 budget 단위 테스트) | +3          | 151~153     |                                                |
| Part 2 Step 8 (회고 산출물만)                     | 0           | 151~153     |                                                |
| Part 2 Step 9 (#2 score 통합 단위 테스트)         | +5~10       | **156~163** | Slice 4 종결 예상                              |

> Part 2 회귀 추가는 Step 7 token_budgets +3, Step 9 score 산식 통합 +5~10 (e6 추가 + e1/e2/e6 통일 검증). 핵심 KPI는 Slice 1/2/3/4 회귀 모두 보존.

---

# 부록 D — 의존성 회피 명시 (분석 엔진)

E6의 의도적 비-스코프 항목:

1. **조정 후 AnalysisContext 재계산**: 사용자가 `reduce TSLA`를 명령했을 때 새로운 weight / 재계산된 metric 결과를 _수치적으로_ 산출하는 작업. 본 슬라이스에서 _수행하지 않음_.
2. **E6의 출력은 자연어 비교 해설**만 — LLM이 *원본 + adjustments*를 입력으로 받아 "조정 후 어떻게 될지를 자연어로 추론"하는 형태.
3. Phase 2에서 분석 엔진 슬라이스가 추가되면 재계산된 AfterContext가 E6 입력에 포함될 수 있음 → schema 확장 필요. 이는 별도 슬라이스로 처리.

이 의존성 회피 결정은 Slice 4 진입점 = E6 채택을 가능하게 한 핵심 설계 결정이며, 본 지시서에서 일관되게 적용된다.

---

# 부록 E — Slice 1·2·3 패턴 mirror 비율

| 항목                                                 | E6 (Slice 4) mirror 대상     | mirror 비율                              |
| ---------------------------------------------------- | ---------------------------- | ---------------------------------------- |
| Schema 추가 위치                                     | E1 (llm.py + llm_outputs.py) | 100%                                     |
| Service 인터페이스 (run*\*, build*_*prompt, parse*_) | E2 (글쓰기 진입점 동일)      | 100%                                     |
| View 인터페이스 (csrf_exempt + POST + JSON 응답)     | E1, E2, E5                   | 100%                                     |
| Mock 통합 테스트 5 케이스                            | Slice 1 (E1)                 | 100% (fallback patch target은 직접 인용) |
| Hybrid fixture 패턴 (baseline + focused)             | Slice 3 (E2)                 | 100% (baseline 3 / focused 4 비율 동일)  |
| token_budgets.py 등록                                | Slice 3 신규 패턴            | Part 2 적용 예정                         |
| DIMENSION_LOOKUP 등록                                | Slice 1·2·3 진화             | Part 2 적용 예정 (Step 9)                |

전체 mirror 비율: **~85%** (Part 1 한정). Part 2는 Step 9 score 산식 통합으로 mirror 비율 추가 ↑.
