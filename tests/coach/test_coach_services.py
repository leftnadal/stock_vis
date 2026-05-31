"""Slice 11 Part 4 — Coach service 단위 테스트 (7건, LLM 호출 없음).

테스트 항목:
1. run_e1_coach import (Part 3 자산 확인)
2. run_e2_coach import 성공
3. run_e3_coach import 성공
4. run_e4_coach import 성공
5. run_e5_coach import 성공
6. run_e6_coach import 성공
7. 6 service 함수 시그니처 일관성 (input_data, provider, client, max_tokens)
"""

from __future__ import annotations

import inspect

import pytest

from apps.portfolio.services.coach.e1_service import run_e1_coach
from apps.portfolio.services.coach.e2_service import run_e2_coach
from apps.portfolio.services.coach.e3_service import run_e3_coach
from apps.portfolio.services.coach.e4_service import run_e4_coach
from apps.portfolio.services.coach.e5_service import run_e5_coach
from apps.portfolio.services.coach.e6_service import run_e6_coach


def test_run_e1_coach_importable():
    assert callable(run_e1_coach)
    assert run_e1_coach.__name__ == "run_e1_coach"


def test_run_e2_coach_importable():
    assert callable(run_e2_coach)
    assert run_e2_coach.__name__ == "run_e2_coach"


def test_run_e3_coach_importable():
    assert callable(run_e3_coach)
    assert run_e3_coach.__name__ == "run_e3_coach"


def test_run_e4_coach_importable():
    assert callable(run_e4_coach)
    assert run_e4_coach.__name__ == "run_e4_coach"


def test_run_e5_coach_importable():
    assert callable(run_e5_coach)
    assert run_e5_coach.__name__ == "run_e5_coach"


def test_run_e6_coach_importable():
    assert callable(run_e6_coach)
    assert run_e6_coach.__name__ == "run_e6_coach"


def test_six_coach_services_signature_consistency():
    """E1~E6 모두 (input_data, provider, client, max_tokens) 시그니처 — 핵심 4개.

    Slice 12 Part 3에서 e3_service에 keyword-only `preset_id`, `metrics` 추가됨 (#59 E3 통합).
    핵심 positional 4개는 모든 service 일관 유지, e3는 추가 keyword-only만 허용.
    """
    services = [
        run_e1_coach,
        run_e2_coach,
        run_e3_coach,
        run_e4_coach,
        run_e5_coach,
        run_e6_coach,
    ]
    core_params = ["input_data", "provider", "client", "max_tokens"]
    for fn in services:
        sig = inspect.signature(fn)
        actual = list(sig.parameters.keys())
        # 첫 4개는 모든 service에서 동일
        assert actual[:4] == core_params, (
            f"{fn.__name__} core signature: {actual[:4]} != {core_params}"
        )
        # default 값 검증
        assert sig.parameters["provider"].default == "haiku"
        assert sig.parameters["client"].default is None
        assert sig.parameters["max_tokens"].default == 2000
        # 추가 파라미터가 있다면 keyword-only이어야 함 (Slice 12 Part 3 e3 패턴)
        for name in actual[4:]:
            assert sig.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY, (
                f"{fn.__name__}.{name} must be keyword-only"
            )
