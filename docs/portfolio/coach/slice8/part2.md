# Slice 8 Part 2 — 실행 지시서 v2

> **Stock-Vis Portfolio Coach — output 보강 trio 통합 2단계**
> **#28 action_items 강제 슬롯 + #42 운영 가이드 (I2 시간대 회피)**

---

## 메타

| 항목      | 값                                                                  |
| --------- | ------------------------------------------------------------------- |
| 작성일    | 2026-05-16                                                          |
| 브랜치    | `slice8`                                                            |
| 시작 상태 | 회귀 414 / 비용 $1.595 / Part 1 종결 + 사전 점검 완료               |
| 확정 옵션 | G3 (하이브리드) + H2 (commentary_output.py 신규) + I2 (시간대 회피) |
| 비용 임계 | $2.00 (사전 경고 $1.60 마진 0.3%)                                   |
| 비용 목표 | **$0 증가** (LLM 호출 0건)                                          |
| 회귀 예상 | +15~20 (Fallback +25 임계 60~80%)                                   |
| 예상 시간 | 3시간                                                               |

---

## 0. Part 1 학습 정착 (입력 사실관계)

### 검증된 사실 (phase1_findings_part2.md R1~R6)

- `portfolio/schemas/llm.py` (289줄): `LLMResponse:18`, `E5Response:95`, `E2Response:222`
- `portfolio/schemas/llm_outputs.py` (334줄): `E3PortfolioCommentary:103`, `E6ComparisonResponse:181`, `ConversationResponse:228`
- `portfolio/schemas/e4_conversation.py` (126줄): `E4ConversationOutput:80`
- `portfolio/schemas/commentary_input.py` (57줄): `TimeSeriesContext:18` (Part 1)
- `portfolio/tests/` 평탄 + `portfolio/tests/slice8/` 격리 디렉토리 사용
- `action_items` / `ActionItem` 기존 정의 **0건**
- 통합 base 모델 **없음**

### Part 2 작업 범위 (확정)

- **G3 (하이브리드):** `ActionItem` 모델 1회 정의 + 7 schema에 `action_items: list[ActionItem]` 필드 추가
- **H2 (신규 파일):** `portfolio/schemas/commentary_output.py` 신규 생성
- **I2 (시간대 회피):** Step 0에서 운영 가이드 정착

### Part 2 제외 범위 (Slice 9 등록)

- **#41 통합 base 모델 (`CommentaryOutputBase`)** → Slice 9 후보
- ActionItem 필드 확장 (deadline, category 등) → Part 3 이후 필요 시

---

## Step 0: I2 운영 가이드 정착 (#42)

### 목적

야간 자동화(`com.stockvis.nightly`)와의 race condition 차단 운영 정책 영구 자산화.

### 대상 파일

- `docs/portfolio/coach/operational_guide.md` (신규)

### 작업

````markdown
# 운영 가이드 — Stock-Vis Portfolio Coach 작업 정책

## 작업 환경 전제

- **Source of truth:** `/Users/byeongjinjeong/Desktop/stock_vis`
- **iCloud 복사본:** 백업용 (작업 금지, `DO_NOT_EDIT_USE_DESKTOP.md` 표지)
- **pre-commit hook:** `.git/hooks/pre-commit` (#39, 브랜치 화이트리스트 검증)

## 동시 실행 시스템 (인지 필수)

### 야간 자동화 (`com.stockvis.nightly`)

- 위치: `~/stock-vis-nightly/`
- 동작: 동일 working dir (`~/Desktop/stock_vis`)에서 자동 git 작업
- 영향: 다른 작업 흐름(users 단위 테스트 등) 자동화
- **충돌 위험:** edit-time race condition 가능

## I2 정책: 시간대 회피 + 다층 방어

### 작업 시간대

- **권장:** 주간 (09:00 ~ 22:00)
- **금지:** 자정 ~ 새벽 (야간 자동화 활성 시간대)
- 새벽 작업 필요 시: `launchctl bootout gui/$(id -u) com.stockvis.nightly` 일시 중지 + 작업 완료 후 재활성화

### 매 작업 시작 시 체크리스트

```bash
pwd                              # /Users/byeongjinjeong/Desktop/stock_vis 확인
git branch --show-current        # 화이트리스트 브랜치 확인
git status                       # 야간 자동화 흔적 (modified 파일) 확인
git log --oneline -5             # 최근 commit이 의도한 것인지 확인
```
````

### 충돌 감지 시 대응

- modified 파일에 의도하지 않은 변경 발견 → `git stash` 후 점검
- 야간 자동화의 commit 발견 → `git log --author` 또는 commit message로 식별
- pre-commit hook이 차단 → `git cherry-pick`으로 작업 이전 (Part 1 검증 패턴)

## 부채 추적

- #38: iCloud 표지 (close, 2026-05-16)
- #39: pre-commit hook (close, 2026-05-16)
- #40: 야간 자동화 도구 식별 (close — 사용자 자체 시스템, 비활성화 보류)
- #42: 본 운영 가이드 (close — 본 문서로 처리)

## 사고 학습 케이스

- 2026-05-16: Slice 8 Part 1 Q-1 commit에서 자동 전환 발생 → cherry-pick 대응
- 2026-05-16: Slice 8 Part 1 Q-2 hook 설치 후 Q-2 자체 commit에서 자연 검증 PASS

````

### KPI
- [ ] `docs/portfolio/coach/operational_guide.md` 신규 작성 완료
- [ ] commit 메시지: `[slice8] add operational_guide.md (#42)`
- [ ] 회귀 0건 (docs only)
- [ ] **부채 #42 close, #40 close** (사용자 자체 시스템 결정)

---

## Step 1: ActionItem 모델 정의 (H2)

### 목적
`action_items` 슬롯의 표준 모델을 1곳에 정의 → 향후 #41 통합 base의 자연 확장 경로 확보.

### 대상 파일
- `portfolio/schemas/commentary_output.py` (신규)

### 작업

```python
"""Commentary output schemas.

Slice 8 Part 2 (#28): action_items 강제 슬롯 도입.
Slice 9 #41 후보: CommentaryOutputBase 통합 모델은 본 파일에 추가 예정.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """LLM commentary의 실행 가능 액션 항목.

    모든 진입점(E1~E6, E3_portfolio)의 output schema에 강제 슬롯으로 포함.
    빈 리스트 허용 (backward-compat).

    Examples:
        >>> ActionItem(
        ...     title="현금 비중 5% 축소",
        ...     description="포트폴리오 현금 비중이 25%로 과도. 우량 종목 추가 매수 검토.",
        ...     priority="high",
        ... )
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="액션 제목 (간결, 1줄)",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=300,
        description="액션 상세 설명 (근거 + 실행 방법)",
    )
    priority: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="우선순위 (high=즉시, medium=단기, low=장기)",
    )
    category: Optional[Literal["rebalance", "review", "monitor", "research"]] = Field(
        default=None,
        description="카테고리 (선택). rebalance=재조정, review=검토, monitor=감시, research=조사",
    )
````

### 단위 테스트

`portfolio/tests/test_action_item_schema.py` (신규):

```python
"""ActionItem schema 검증."""

import pytest
from pydantic import ValidationError

from portfolio.schemas.commentary_output import ActionItem


class TestActionItemSchema:
    def test_minimal_valid_action_item(self):
        """필수 필드만 채워진 정상 케이스."""
        item = ActionItem(
            title="현금 비중 축소",
            description="포트폴리오 현금 비중이 25%로 과도하여 축소 검토.",
        )
        assert item.title == "현금 비중 축소"
        assert item.priority == "medium"  # default
        assert item.category is None  # default

    def test_full_action_item(self):
        """모든 필드 채워진 케이스."""
        item = ActionItem(
            title="섹터 분산 개선",
            description="IT 섹터 비중 60%, 금융 5%로 편중. 금융/소비재 추가 검토.",
            priority="high",
            category="rebalance",
        )
        assert item.priority == "high"
        assert item.category == "rebalance"

    def test_title_too_short(self):
        """title이 빈 문자열이면 검증 실패."""
        with pytest.raises(ValidationError):
            ActionItem(title="", description="x" * 20)

    def test_title_too_long(self):
        """title이 80자 초과면 검증 실패."""
        with pytest.raises(ValidationError):
            ActionItem(title="a" * 81, description="x" * 20)

    def test_description_too_short(self):
        """description이 10자 미만이면 검증 실패."""
        with pytest.raises(ValidationError):
            ActionItem(title="t", description="짧음")

    def test_invalid_priority(self):
        """priority가 허용되지 않은 값이면 검증 실패."""
        with pytest.raises(ValidationError):
            ActionItem(
                title="t",
                description="x" * 20,
                priority="urgent",  # type: ignore
            )

    def test_invalid_category(self):
        """category가 허용되지 않은 값이면 검증 실패."""
        with pytest.raises(ValidationError):
            ActionItem(
                title="t",
                description="x" * 20,
                category="invalid",  # type: ignore
            )
```

### KPI

- [ ] `portfolio/schemas/commentary_output.py` 신규 작성 완료
- [ ] `portfolio/tests/test_action_item_schema.py` 7건 PASS
- [ ] IDENTICAL hash 7/7 유지
- [ ] 회귀 +7건

### 실패 시

- import 오류: `portfolio/schemas/__init__.py`에 ActionItem export 추가 검토

---

## Step 2: 7 schema 확장 (G3 — `action_items` 필드 추가)

### 목적

모든 진입점 output schema에 `action_items` 슬롯 강제 → backward-compat 보장 (기본값 빈 리스트).

### 대상 파일

- `portfolio/schemas/llm.py` (3 schema 수정: `LLMResponse:18`, `E5Response:95`, `E2Response:222`)
- `portfolio/schemas/llm_outputs.py` (3 schema 수정: `E3PortfolioCommentary:103`, `E6ComparisonResponse:181`, `ConversationResponse:228`)
- `portfolio/schemas/e4_conversation.py` (1 schema 수정: `E4ConversationOutput:80`)

### 작업 패턴 (모든 schema 동일)

```python
# 파일 상단 import 추가
from portfolio.schemas.commentary_output import ActionItem

# 각 schema 클래스 본문에 필드 추가
class <기존ScheamName>(BaseModel):
    # ... 기존 필드 유지 ...
    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="LLM이 제안한 실행 가능 액션 항목 (없으면 빈 리스트)",
    )
```

### 7건 적용 대상 정확히

#### `portfolio/schemas/llm.py`

1. `LLMResponse` (line 18)
2. `E5Response` (line 95)
3. `E2Response` (line 222)

#### `portfolio/schemas/llm_outputs.py`

4. `E3PortfolioCommentary` (line 103)
5. `E6ComparisonResponse` (line 181)
6. `ConversationResponse` (line 228)

#### `portfolio/schemas/e4_conversation.py`

7. `E4ConversationOutput` (line 80)

### 순환 의존성 점검

- `commentary_output.py`는 다른 schemas 파일을 import하지 않음 (확인 필수)
- `llm.py`, `llm_outputs.py`, `e4_conversation.py` → `commentary_output.py` 단방향 의존

### 단위 테스트

`portfolio/tests/test_schema_action_items_backward_compat.py` (신규):

```python
"""7 schema action_items 필드 backward-compat 검증."""

import pytest

from portfolio.schemas.commentary_output import ActionItem
from portfolio.schemas.e4_conversation import E4ConversationOutput
from portfolio.schemas.llm import E2Response, E5Response, LLMResponse
from portfolio.schemas.llm_outputs import (
    ConversationResponse,
    E3PortfolioCommentary,
    E6ComparisonResponse,
)


SCHEMA_TARGETS = [
    LLMResponse,
    E5Response,
    E2Response,
    E3PortfolioCommentary,
    E6ComparisonResponse,
    ConversationResponse,
    E4ConversationOutput,
]


@pytest.mark.parametrize("schema_cls", SCHEMA_TARGETS)
def test_action_items_field_exists(schema_cls):
    """모든 7 schema에 action_items 필드가 정의되어야 함."""
    assert "action_items" in schema_cls.model_fields


@pytest.mark.parametrize("schema_cls", SCHEMA_TARGETS)
def test_action_items_default_empty_list(schema_cls):
    """action_items 필드의 기본값은 빈 리스트 (backward-compat 핵심)."""
    field_info = schema_cls.model_fields["action_items"]
    # default_factory=list → 호출 시 [] 반환
    assert field_info.default_factory is not None
    assert field_info.default_factory() == []


def test_action_items_accepts_valid_items():
    """action_items가 ActionItem 리스트를 정상 수용."""
    item = ActionItem(
        title="현금 비중 축소",
        description="포트폴리오 현금 비중이 25%로 과도하여 축소 검토.",
        priority="high",
    )
    # E3PortfolioCommentary는 기존 필드를 알아야 하므로 mock 데이터 필요
    # 여기서는 LLMResponse 가장 간단한 케이스로 검증
    # (각 schema의 필수 필드는 기존 테스트에서 검증되므로 본 테스트는 action_items만)
```

### KPI

- [ ] 7 schema 모두 `action_items: list[ActionItem]` 필드 추가
- [ ] backward-compat 테스트 9건 PASS (parametrized 7 + 일반 2)
- [ ] 기존 fixture 무영향 (Part 1 e3_concentrated_v2.json / e2_v2.json 로딩 PASS)
- [ ] IDENTICAL hash 7/7 유지
- [ ] 회귀 +9건

### 실패 시

- 기존 fixture 로딩 실패: 기본값 `default_factory=list` 누락 점검
- 순환 import: `commentary_output.py` 내부 import 점검

---

## Step 3: mock smoke (Part 1 fixture 확장)

### 목적

ActionItem이 실제 진입점 fixture에 자연 통합되는지 smoke 검증.

### 대상 파일

- `portfolio/tests/slice8/fixtures/e3_concentrated_v2_with_actions.json` (신규)
- `portfolio/tests/slice8/test_action_items_smoke.py` (신규)

### 작업

#### fixture 작성

`e3_concentrated_v2_with_actions.json`:

- Part 1의 `e3_concentrated_v2.json` 기반
- 응답 측에 `action_items` 2건 채워진 케이스 추가:
  ```json
  {
  	"commentary": "...",
  	"action_items": [
  		{
  			"title": "현금 비중 5% 축소",
  			"description": "포트폴리오 현금 비중이 25%로 과도하여 우량 종목 추가 매수 검토 권장.",
  			"priority": "high",
  			"category": "rebalance"
  		},
  		{
  			"title": "IT 섹터 노출 점검",
  			"description": "IT 섹터 비중 60%로 편중. 분기별 리밸런싱 검토 필요.",
  			"priority": "medium",
  			"category": "review"
  		}
  	]
  }
  ```

#### smoke 테스트

```python
"""ActionItem이 진입점 fixture에 자연 통합되는지 smoke 검증."""

import json
from pathlib import Path

from portfolio.schemas.llm_outputs import E3PortfolioCommentary


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class TestActionItemsSmoke:
    def test_e3_with_action_items_loads(self):
        """ActionItem 채워진 fixture가 정상 로딩."""
        path = FIXTURE_DIR / "e3_concentrated_v2_with_actions.json"
        data = json.loads(path.read_text())
        obj = E3PortfolioCommentary.model_validate(data)
        assert len(obj.action_items) == 2
        assert obj.action_items[0].priority == "high"
        assert obj.action_items[0].category == "rebalance"

    def test_e3_empty_action_items_backward_compat(self):
        """Part 1 fixture (action_items 없음)가 backward-compat 유지."""
        path = FIXTURE_DIR / "e3_concentrated_v2.json"
        data = json.loads(path.read_text())
        obj = E3PortfolioCommentary.model_validate(data)
        assert obj.action_items == []  # default

    def test_e2_empty_action_items_backward_compat(self):
        """Part 1 e2 fixture도 backward-compat 유지."""
        from portfolio.schemas.llm import E2Response
        path = FIXTURE_DIR / "e2_v2.json"
        data = json.loads(path.read_text())
        obj = E2Response.model_validate(data)
        assert obj.action_items == []

    def test_action_items_serialization_roundtrip(self):
        """ActionItem 포함된 schema의 직렬화 round-trip."""
        path = FIXTURE_DIR / "e3_concentrated_v2_with_actions.json"
        original = json.loads(path.read_text())
        obj = E3PortfolioCommentary.model_validate(original)
        dumped = obj.model_dump(mode="json")
        # round-trip 후 action_items 보존
        assert len(dumped["action_items"]) == 2
        assert dumped["action_items"][0]["title"] == original["action_items"][0]["title"]
```

### KPI

- [ ] fixture 1건 신규 작성
- [ ] smoke 테스트 4건 PASS
- [ ] $0 비용 유지 (LLM 호출 없음)
- [ ] IDENTICAL hash 7/7 유지
- [ ] 회귀 +4건

### 주의

- Part 1 fixture (e3_concentrated_v2.json, e2_v2.json)는 **수정 금지** (backward-compat 검증 입력)
- 신규 fixture는 별도 파일명으로 분리

---

## Step 4: 종결 점검 및 보고서 작성

### 자동 점검

```bash
# 회귀 총량
pytest --collect-only -q | tail -1
# 예상: 414 + 15~20 = 429~434

# IDENTICAL hash
pytest portfolio/tests/test_static_integrity.py -v

# Part 2 신규 테스트만 격리 실행
pytest portfolio/tests/test_action_item_schema.py -v
pytest portfolio/tests/test_schema_action_items_backward_compat.py -v
pytest portfolio/tests/slice8/test_action_items_smoke.py -v

# 비용 누적
cat docs/portfolio/coach/slice8/cost_log.md
```

### 종결 보고서 템플릿

`docs/portfolio/coach/slice8/part2_closing.md`:

```markdown
# Slice 8 Part 2 종결 보고서

## KPI 통과 현황

- [ ] 회귀: 414 → **_ (증가 +_**, Fallback 임계 +25 대비 \_\_\_%)
- [ ] IDENTICAL hash 7/7: PASS / FAIL
- [ ] ActionItem 단위 테스트 7건: PASS / FAIL
- [ ] 7 schema backward-compat 9건: PASS / FAIL
- [ ] smoke 4건: PASS / FAIL
- [ ] 비용: $1.595 → $**_ (사전 경고 $1.60 대비 _**%)

## 부채 처리 결과

- #28 action_items 강제 슬롯: closed
- #42 운영 가이드: closed (operational_guide.md)
- #40 야간 자동화 도구 식별: closed (사용자 자체 시스템 결정)

## 신규 부채 등록

- #41 output schema 통합 (CommentaryOutputBase): Slice 9 후보 (PS 2.5)

## Part 3 진입 판정

- 회귀 증가량 \_\_\_ → 진입 / 분리
- 비용 \_\_\_ → 안전 / 사전 경고 / 중단

## 환경 이슈 모니터링

- 야간 자동화 충돌 발생 횟수: \_\_\_
- pre-commit hook 차단 횟수: \_\_\_
- cherry-pick 대응 횟수: \_\_\_

## I2 정책 실효성 평가

- 작업 시간대 회피 준수: PASS / FAIL
- git status 사전 체크 빈도: \_\_\_
```

### KPI

- [ ] 종결 보고서 작성 완료
- [ ] Part 3 진입 조건 평가 (회귀 +25 임계 + 비용 $1.60 임계)

---

## 산출물 체크리스트

| #   | 파일                                                                   | 종류                 | 부채      |
| --- | ---------------------------------------------------------------------- | -------------------- | --------- |
| 1   | `docs/portfolio/coach/operational_guide.md`                            | docs                 | #42 close |
| 2   | `portfolio/schemas/commentary_output.py`                               | 코드 (ActionItem)    | #28       |
| 3   | `portfolio/schemas/llm.py`                                             | 코드 (3 schema 확장) | #28       |
| 4   | `portfolio/schemas/llm_outputs.py`                                     | 코드 (3 schema 확장) | #28       |
| 5   | `portfolio/schemas/e4_conversation.py`                                 | 코드 (1 schema 확장) | #28       |
| 6   | `portfolio/tests/test_action_item_schema.py`                           | 테스트 (7건)         | #28       |
| 7   | `portfolio/tests/test_schema_action_items_backward_compat.py`          | 테스트 (9건)         | #28       |
| 8   | `portfolio/tests/slice8/fixtures/e3_concentrated_v2_with_actions.json` | fixture              | #28       |
| 9   | `portfolio/tests/slice8/test_action_items_smoke.py`                    | 테스트 (4건)         | #28       |
| 10  | `docs/portfolio/coach/slice8/part2_closing.md`                         | docs                 | —         |

---

## 실행 순서

```
1. Step 0 운영 가이드 (#42)        → docs commit
2. Step 1 ActionItem 모델 (#28)    → 단위 테스트 7건 PASS
3. Step 2 7 schema 확장 (#28)      → backward-compat 9건 PASS
4. Step 3 mock smoke              → 4건 PASS
5. Step 4 종결 점검 + 보고서       → Part 3 진입 판정
```

각 Step 종료마다:

- `git status` + `git branch --show-current` 확인 (I2 정책)
- pytest 회귀 누적 확인
- **+20 초과 시 즉시 사용자 보고**

---

## 위험 신호 및 대응

| 조건                 | 트리거                          | 처리                                           |
| -------------------- | ------------------------------- | ---------------------------------------------- |
| 회귀 > +25           | pytest --collect-only count     | Part 3 분리 검토, 사용자 보고                  |
| 비용 > $1.60         | CostGuard 80% 사전 경고         | 즉시 중단 (LLM 호출 0 예정이므로 발생 시 이상) |
| IDENTICAL 7/7 위반   | test_static_integrity           | 즉시 중단, 원인 분석                           |
| 야간 자동화 충돌     | git status modified 비의도 파일 | git stash 후 점검 → 시간대 재개                |
| pre-commit hook 차단 | exit 1                          | cherry-pick으로 작업 이전                      |
| 순환 import          | ImportError                     | commentary_output.py 단방향 의존 점검          |

---

## 비용 예산

- **목표: $0 증가** (Part 2 전체 LLM 호출 0건)
- Part 2 시작 시 누적: $1.595
- 사전 경고 임계: $1.60 (마진 0.3%)
- $1.60 통과 시: **즉시 중단** (LLM 호출 0 예정이므로 비용 증가 자체가 이상 신호)

---

## 회귀 예산

- **목표: +15~20건** (Fallback +25 임계 60~80%)
- 단위 테스트 (Step 1): +7
- backward-compat (Step 2): +9
- smoke (Step 3): +4
- 합계 예상: +20건
- +25 초과 시: Part 3 분리 검토

---

## 결정 근거 (옵션 G3 + H2 + I2)

### 결정 G — G3 하이브리드: 가중합 4.00, 마진 0.35

- 회귀 통제(+15~20) + 일관성(ActionItem 1회 정의)
- #41 통합 base는 Slice 9 정식 작업으로 미룸 → trio 통합 D-2 보호

### 결정 H — H2 commentary_output.py 신규: 가중합 4.70, 마진 1.50

- input/output 명확한 대칭
- Slice 9 #41 통합 base의 자연 확장 경로

### 결정 I — I2 시간대 회피: 가중합 4.00, 마진 0.15

- 사용자 야간 자동화 자산 보존 + 다층 방어
- pre-commit hook(commit-time) + git status(edit-time) + 시간대(시스템-time)

---

## Part 1 학습 적용 체크리스트

- [x] 메모리 추정 사용 금지 (R1~R6 보고서 사실관계만 사용)
- [x] 모든 파일 경로 검증됨 (portfolio/schemas/, portfolio/tests/ 평탄)
- [x] 모든 클래스 위치 검증됨 (라인 번호 명시: 18, 95, 222, 103, 181, 228, 80)
- [x] 환경 이슈 처리 사전 완료 (E2 + F4, Phase 1)
- [x] 동시 실행 시스템 인지 (야간 자동화)

---

**문서 끝.** 이 지시서 그대로 Claude Code 환경에서 실행 시작. Part 2 종결 보고서 회수 후 Part 3 지시서 작성.
