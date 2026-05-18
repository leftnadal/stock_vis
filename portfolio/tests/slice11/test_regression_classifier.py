"""Slice 11 Step 0 §6 — 회귀 분류 룰 보강 (Slice 10 카테고리 재사용).

Slice 11 신규 작업의 변경 경로가 기존 카테고리(data-prep / cost / mixed)로 정확히
분류되는지 검증. 신규 카테고리 추가 없이 Slice 10 룰로 충분함을 확인.
"""

from __future__ import annotations

from portfolio.tests.helpers.regression_classifier import classify_regression


def test_output_estimator_changes_are_mixed():
    """output estimator 갱신: portfolio/measure/ + scripts/coach/ + tests/coach/ → mixed.

    portfolio/measure/는 cost 카테고리, scripts/coach/는 data-prep 카테고리.
    혼합 → 보수적으로 mixed (cost 기준 적용).
    """
    paths = [
        "portfolio/measure/estimator_v3.py",
        "scripts/coach/backtest_output_estimator.py",
        "tests/coach/test_estimator_v3.py",
    ]
    assert classify_regression(paths) == "mixed"


def test_messages_persistence_changes_are_mixed():
    """messages 보존 hook: portfolio/measure/ + tests/coach/ → mixed."""
    paths = [
        "portfolio/measure/message_dumper.py",
        "tests/coach/test_messages_persistence.py",
    ]
    assert classify_regression(paths) == "mixed"


def test_commentary_input_schema_changes_are_mixed():
    """Part 1: portfolio/schemas/ + fixtures/coach/ + tests/coach/ → mixed.

    schema 카테고리는 기존 cost (portfolio/schemas/) 룰 재사용. data-prep 테스트와
    혼합 시 mixed로 보수적 분류.
    """
    paths = [
        "portfolio/schemas/commentary_input.py",
        "portfolio/tests/fixtures/coach/portfolio_a2.json",
        "portfolio/tests/fixtures/coach/loaders.py",
        "tests/coach/test_commentary_input.py",
    ]
    assert classify_regression(paths) == "mixed"


def test_commentary_output_schema_changes_are_mixed():
    """Part 2: portfolio/schemas/commentary_output.py + tests/coach/ → mixed.

    Part 1과 동일 패턴 — cost (schemas/) + data-prep (tests/coach/) 혼합 → mixed.
    """
    paths = [
        "portfolio/schemas/commentary_output.py",
        "tests/coach/test_commentary_output.py",
    ]
    assert classify_regression(paths) == "mixed"
