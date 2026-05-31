"""E6 (조정 후 비교 해설) fixture — Slice 4 Step 5.

Hybrid 7 패턴 — Slice 1·3 mirror:
  - e5_baseline 그룹 (3개): Slice 2 sample_adjustment_context 의 expected adjustments를
    AdjustmentItem으로 풀어 E6Request 형태로 변환.
  - e6_focused 그룹 (4개): 비중 재조정 / 디펜시브 추가 / 부진 종목 제외 / 다중 차원 동시.

사용처:
  - Slice 4 Step 4 통합 테스트 보조
  - Slice 4 Part 2 Step 8 회고 (haiku 7 + sonnet 7 = 14 calls)

Slice 2 fixture 함수명 매핑 (지시서 §5.3 케이스 D — 함수명 정정):
  - 지시서 가정 `clear_reduce_tesla` → 실제 `get_e5_fixture_clear_decrease`
  - 지시서 가정 `clear_add_microsoft` → 실제 `get_e5_fixture_clear_multi`
  - 지시서 가정 `clear_remove_nvidia` → 실제 `get_e5_fixture_remove`
"""

from __future__ import annotations

from typing import Any

from portfolio.tests.fixtures.sample_adjustment_context import (
    get_e5_fixture_clear_decrease,
    get_e5_fixture_clear_multi,
    get_e5_fixture_remove,
)

# fixture 그룹 메타 (Step 8 회고 그룹 비교용)
FIXTURE_GROUPS: dict[str, list[str]] = {
    "e5_baseline": [
        "e5_baseline_decrease",
        "e5_baseline_multi",
        "e5_baseline_remove",
    ],
    "e6_focused": [
        "e6_focused_weight_rebalance",
        "e6_focused_add_defensive",
        "e6_focused_remove_underperformer",
        "e6_focused_multi_aspect",
    ],
}


# ============================================================
# baseline 그룹 — Slice 2 E5 fixture 재활용 + adjustments 풀어 넣기
# ============================================================


def get_e6_fixture_e5_baseline_decrease() -> dict[str, Any]:
    """Slice 2 clear_decrease 재활용 (TSLA decrease 단일)."""
    base = get_e5_fixture_clear_decrease()
    return {
        "fixture_group": "e5_baseline",
        "fixture_id": "e5_baseline_decrease",
        "analysis_context": base["analysis_context"],
        "adjustments": [
            {
                "ticker": "TSLA",
                "action": "decrease",
                "delta_weight": -0.05,
                "target_weight": None,
                "reason_quote": "TSLA 비중 좀 줄여줘",
            }
        ],
        "user_intent": base["user_command"],
    }


def get_e6_fixture_e5_baseline_multi() -> dict[str, Any]:
    """Slice 2 clear_multi 재활용 (TSLA decrease + NVDA increase)."""
    base = get_e5_fixture_clear_multi()
    return {
        "fixture_group": "e5_baseline",
        "fixture_id": "e5_baseline_multi",
        "analysis_context": base["analysis_context"],
        "adjustments": [
            {
                "ticker": "TSLA",
                "action": "decrease",
                "delta_weight": -0.05,
                "target_weight": None,
                "reason_quote": "TSLA는 줄이고",
            },
            {
                "ticker": "NVDA",
                "action": "increase",
                "delta_weight": 0.05,
                "target_weight": None,
                "reason_quote": "NVDA는 좀 늘려줘",
            },
        ],
        "user_intent": base["user_command"],
    }


def get_e6_fixture_e5_baseline_remove() -> dict[str, Any]:
    """Slice 2 remove 재활용 (PLTR 제외)."""
    base = get_e5_fixture_remove()
    return {
        "fixture_group": "e5_baseline",
        "fixture_id": "e5_baseline_remove",
        "analysis_context": base["analysis_context"],
        "adjustments": [
            {
                "ticker": "PLTR",
                "action": "remove",
                "delta_weight": None,
                "target_weight": 0.0,
                "reason_quote": "PLTR은 빼버릴게",
            }
        ],
        "user_intent": base["user_command"],
    }


# ============================================================
# focused 그룹 — Slice 4 신규 (E6 비교 해설 차원에 특화)
# ============================================================


def get_e6_fixture_focused_weight_rebalance() -> dict[str, Any]:
    """비중 재조정만 — 종목 추가/제외 없음."""
    return {
        "fixture_group": "e6_focused",
        "fixture_id": "e6_focused_weight_rebalance",
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.40},
                {"ticker": "GOOGL", "weight": 0.30},
                {"ticker": "AAPL", "weight": 0.30},
            ],
            "analysis_summary": {
                "one_line_diagnosis": "GARP, 빅테크 균등 분산 — 안정적이나 모멘텀 부족",
                "preset_id": "garp",
            },
        },
        "adjustments": [
            {
                "ticker": "AAPL",
                "action": "decrease",
                "delta_weight": -0.10,
                "target_weight": 0.20,
                "reason_quote": "애플 줄이고",
            },
            {
                "ticker": "GOOGL",
                "action": "increase",
                "delta_weight": 0.10,
                "target_weight": 0.40,
                "reason_quote": "구글 늘려",
            },
        ],
        "user_intent": "애플 줄이고 구글 늘려",
    }


def get_e6_fixture_focused_add_defensive() -> dict[str, Any]:
    """디펜시브 종목 신규 진입 (집중도 위험 완화 시나리오)."""
    return {
        "fixture_group": "e6_focused",
        "fixture_id": "e6_focused_add_defensive",
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "TSLA", "weight": 0.30},
                {"ticker": "NVDA", "weight": 0.40},
                {"ticker": "AMD", "weight": 0.30},
            ],
            "analysis_summary": {
                "one_line_diagnosis": "기술주 집중 100% — 단일 섹터 위험 매우 높음",
                "preset_id": "garp",
            },
        },
        "adjustments": [
            {
                "ticker": "TSLA",
                "action": "decrease",
                "delta_weight": -0.10,
                "target_weight": 0.20,
                "reason_quote": "기술주 비중 좀 줄이고",
            },
            {
                "ticker": "NVDA",
                "action": "decrease",
                "delta_weight": -0.10,
                "target_weight": 0.30,
                "reason_quote": "기술주 비중 좀 줄이고",
            },
            {
                "ticker": "JNJ",
                "action": "add",
                "delta_weight": None,
                "target_weight": 0.15,
                "reason_quote": "디펜시브 추가해줘",
            },
            {
                "ticker": "PG",
                "action": "add",
                "delta_weight": None,
                "target_weight": 0.05,
                "reason_quote": "디펜시브 추가해줘",
            },
        ],
        "user_intent": "기술주 비중 좀 줄이고 디펜시브 추가해줘",
    }


def get_e6_fixture_focused_remove_underperformer() -> dict[str, Any]:
    """부진 종목 제외 후 잔여 비중 재할당."""
    return {
        "fixture_group": "e6_focused",
        "fixture_id": "e6_focused_remove_underperformer",
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.25},
                {"ticker": "AMZN", "weight": 0.25},
                {"ticker": "META", "weight": 0.25},
                {"ticker": "PYPL", "weight": 0.25},
            ],
            "analysis_summary": {
                "one_line_diagnosis": "GARP 균등 분산, PYPL 최근 약세",
                "preset_id": "garp",
            },
        },
        "adjustments": [
            {
                "ticker": "PYPL",
                "action": "remove",
                "delta_weight": None,
                "target_weight": 0.0,
                "reason_quote": "페이팔 빼고",
            },
            {
                "ticker": "MSFT",
                "action": "increase",
                "delta_weight": 0.10,
                "target_weight": 0.35,
                "reason_quote": "마이크로소프트 늘려",
            },
            {
                "ticker": "AMZN",
                "action": "increase",
                "delta_weight": 0.15,
                "target_weight": 0.40,
                "reason_quote": "아마존 늘려",
            },
        ],
        "user_intent": "페이팔 빼고 마이크로소프트랑 아마존 늘려",
    }


def get_e6_fixture_focused_multi_aspect() -> dict[str, Any]:
    """다중 차원 동시 조정 — 가장 복잡한 시나리오 (제거 + 축소 + 확대 + 신규 진입)."""
    return {
        "fixture_group": "e6_focused",
        "fixture_id": "e6_focused_multi_aspect",
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
                "one_line_diagnosis": "빅테크 균등 5개 — 분산이나 섹터 단일",
                "preset_id": "garp",
            },
        },
        "adjustments": [
            {
                "ticker": "TSLA",
                "action": "remove",
                "delta_weight": None,
                "target_weight": 0.0,
                "reason_quote": "테슬라 빼고",
            },
            {
                "ticker": "NVDA",
                "action": "decrease",
                "delta_weight": -0.10,
                "target_weight": 0.10,
                "reason_quote": "엔비디아 좀 줄이고",
            },
            {
                "ticker": "MSFT",
                "action": "increase",
                "delta_weight": 0.05,
                "target_weight": 0.25,
                "reason_quote": "MSFT 늘리면서",
            },
            {
                "ticker": "BRK.B",
                "action": "add",
                "delta_weight": None,
                "target_weight": 0.20,
                "reason_quote": "버크셔 추가해",
            },
            {
                "ticker": "JPM",
                "action": "add",
                "delta_weight": None,
                "target_weight": 0.10,
                "reason_quote": "JPM 추가해",
            },
        ],
        "user_intent": (
            "테슬라 빼고 엔비디아 좀 줄이고, MSFT 늘리면서 버크셔랑 JPM 추가해"
        ),
    }


# ============================================================
# 헬퍼 — 전체 fixture 리스트
# ============================================================


ALL_FIXTURES: dict[str, Any] = {
    "e5_baseline_decrease": get_e6_fixture_e5_baseline_decrease,
    "e5_baseline_multi": get_e6_fixture_e5_baseline_multi,
    "e5_baseline_remove": get_e6_fixture_e5_baseline_remove,
    "e6_focused_weight_rebalance": get_e6_fixture_focused_weight_rebalance,
    "e6_focused_add_defensive": get_e6_fixture_focused_add_defensive,
    "e6_focused_remove_underperformer": get_e6_fixture_focused_remove_underperformer,
    "e6_focused_multi_aspect": get_e6_fixture_focused_multi_aspect,
}


def get_all_fixtures() -> list[dict[str, Any]]:
    return [fn() for fn in ALL_FIXTURES.values()]


def get_baseline_fixtures() -> list[dict[str, Any]]:
    return [fn() for name, fn in ALL_FIXTURES.items() if name.startswith("e5_baseline")]


def get_focused_fixtures() -> list[dict[str, Any]]:
    return [fn() for name, fn in ALL_FIXTURES.items() if name.startswith("e6_focused")]
