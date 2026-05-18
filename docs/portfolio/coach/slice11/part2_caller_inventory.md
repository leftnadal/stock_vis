# Slice 11 Part 2 Step 1 — 호출자 인벤토리 (KPI 1)

## 결과 요약

- **호출자 수**: 4건 (모두 `ActionItem` 단일 import)
- **임계**: ≤ 5 → **in-place 진행** (Fallback B2 미발동)
- **기존 `commentary_output.py` 라인 수**: 47
- **호출자 갱신 필요량**: **0건** (ActionItem 정의를 신규 schema 모듈 안에 보존하면 모든 호출자가 그대로 동작)

## 호출자 목록

| # | 파일                                                       | import 형태                                                     |
| - | ---------------------------------------------------------- | --------------------------------------------------------------- |
| 1 | `portfolio/schemas/llm.py:17`                              | `from portfolio.schemas.commentary_output import ActionItem`    |
| 2 | `portfolio/schemas/e4_conversation.py:17`                  | `from portfolio.schemas.commentary_output import ActionItem`    |
| 3 | `portfolio/tests/test_action_item_schema.py:6`             | `from portfolio.schemas.commentary_output import ActionItem`    |
| 4 | `portfolio/tests/test_schema_action_items_backward_compat.py:5` | `from portfolio.schemas.commentary_output import ActionItem` |

## 인벤토리 명령

```bash
grep -rn "from portfolio.schemas.commentary_output\|import portfolio.schemas.commentary_output" \
  portfolio/ tests/ --include="*.py"
# → 4건, 모두 ActionItem 단일 import
```

## Fallback 트리거 판정

| Fallback 조건                  | 발동 여부 |
| ------------------------------ | --------- |
| 호출자 6개 이상 (B2 alias)     | **미발동** (4 < 6) |
| ActionItem 정의/필드 변경 필요 | **미발동** (기존 정의 그대로 흡수) |

## 기존 `commentary_output.py` 전체 dump (참고용)

```python
"""Commentary output schemas.

Slice 8 Part 2 (#28): action_items 강제 슬롯 도입.
Slice 9 #41 후보: CommentaryOutputBase 통합 모델은 본 파일에 추가 예정.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """LLM commentary의 실행 가능 액션 항목.

    모든 진입점(E1~E6, E3_portfolio)의 output schema에 강제 슬롯으로 포함.
    빈 리스트 허용 (backward-compat).
    """

    title: str = Field(..., min_length=1, max_length=80, ...)
    description: str = Field(..., min_length=10, max_length=300, ...)
    priority: Literal["high", "medium", "low"] = Field(default="medium", ...)
    category: Optional[Literal["rebalance", "review", "monitor", "research"]] = Field(
        default=None, ...
    )
```

## 결론

- **in-place 리팩토링 진행**.
- ActionItem 정의는 **변경 없이** 신규 통합 모듈 안에 그대로 보존 (`from portfolio.schemas.commentary_output import ActionItem`은 계속 동작).
- 호출자 갱신은 **0건**.
- **#41 close 조건 4건 중 "호출자 갱신 완료 (legacy import 0)"는 자동 충족** (기존 import 경로 보존).
