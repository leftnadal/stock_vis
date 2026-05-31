"""Slice 4 Step 9 — score_step8.py 통합 함수 단위 테스트 (백로그 #2).

_normalize_results / _build_lex_filter / _build_output_dict / DIMENSION_LOOKUP 검증.
"""

from __future__ import annotations

import pytest


def test_normalize_flat_passthrough():
    """flat 구조는 그대로 반환 (e1 baseline)."""
    from scripts.validation.score_step8 import _normalize_results

    results = [{"label": "haiku", "naturalness": 5, "insight": 4, "schema_pass": True}]
    out = _normalize_results(results, "flat")
    assert out == results


def test_normalize_nested_to_flat():
    """nested 구조 → flat 평탄화 (e2/e6 패턴)."""
    from scripts.validation.score_step8 import _normalize_results

    nested = [
        {
            "model_label": "haiku",
            "fixture": "f1",
            "fixture_group": "baseline",
            "judgments": {
                "naturalness_manual": 5,
                "insight_manual": 4,
                "completeness_auto": True,
                "schema_pass": True,
            },
            "metadata": {
                "cost_usd": 0.001,
                "latency_ms": 5000,
                "fallback_from": None,
            },
        }
    ]
    flat = _normalize_results(nested, "nested")
    assert len(flat) == 1
    assert flat[0]["label"] == "haiku"
    assert flat[0]["fixture"] == "f1"
    assert flat[0]["fixture_group"] == "baseline"
    assert flat[0]["naturalness"] == 5
    assert flat[0]["insight"] == 4
    assert flat[0]["completeness_auto"] is True
    assert flat[0]["cost_usd"] == 0.001
    assert flat[0]["latency_ms"] == 5000


def test_normalize_nested_with_error_entry():
    """nested error entry는 schema_pass=False로 평탄화."""
    from scripts.validation.score_step8 import _normalize_results

    nested = [
        {
            "model_label": "haiku",
            "fixture": "f_err",
            "fixture_group": "baseline",
            "error": "LLMTimeoutError: ...",
        }
    ]
    flat = _normalize_results(nested, "nested")
    assert flat[0]["schema_pass"] is False
    assert flat[0]["completeness_auto"] is False
    assert flat[0]["error"].startswith("LLMTimeoutError")


def test_normalize_unknown_structure_raises():
    """미등록 result_structure → ValueError."""
    from scripts.validation.score_step8 import _normalize_results

    with pytest.raises(ValueError, match="Unknown result_structure"):
        _normalize_results([], "unknown_format")


def test_lex_filter_no_additional_check():
    """additional_check=None → e1 베이스 (schema + nat>=3 + ins>=3)만."""
    from scripts.validation.score_step8 import _build_lex_filter

    f = _build_lex_filter(None)
    assert f({"schema_pass": True, "naturalness": 5, "insight": 4}) is True
    assert f({"schema_pass": True, "naturalness": 2, "insight": 4}) is False
    assert f({"schema_pass": False, "naturalness": 5, "insight": 4}) is False


def test_lex_filter_with_completeness_auto():
    """additional_check=completeness_auto → e2/e6 패턴."""
    from scripts.validation.score_step8 import _build_lex_filter

    f = _build_lex_filter("completeness_auto")
    assert (
        f(
            {
                "schema_pass": True,
                "naturalness": 5,
                "insight": 4,
                "completeness_auto": True,
            }
        )
        is True
    )
    assert (
        f(
            {
                "schema_pass": True,
                "naturalness": 5,
                "insight": 4,
                "completeness_auto": False,
            }
        )
        is False
    )


def test_build_output_dict_e1_format():
    """e1 출력 형식 — 4 키 (scored_at / thresholds 없음)."""
    from scripts.validation.score_step8 import _build_output_dict

    out = _build_output_dict(
        "e1",
        scored=[{"score": 30}],
        label_means={"haiku": 30.0},
        use_fallback=False,
        winner="haiku",
    )
    assert set(out.keys()) == {
        "scored_results",
        "label_means",
        "use_fallback",
        "winner",
    }
    assert "scored_at" not in out
    assert "thresholds" not in out


def test_build_output_dict_e2_e6_format():
    """e2/e6 출력 형식 — 6 키 (scored_at + thresholds 포함)."""
    from scripts.validation.score_step8 import _build_output_dict

    out_e2 = _build_output_dict(
        "e2",
        scored=[{"score": 30}],
        label_means={"haiku": 30.0},
        use_fallback=False,
        winner="haiku",
    )
    out_e6 = _build_output_dict(
        "e6",
        scored=[{"score": 30}],
        label_means={"haiku": 30.0},
        use_fallback=False,
        winner="haiku",
    )
    expected_keys = {
        "scored_at",
        "scored_results",
        "label_means",
        "use_fallback",
        "winner",
        "thresholds",
    }
    assert set(out_e2.keys()) == expected_keys
    assert set(out_e6.keys()) == expected_keys
    assert out_e2["thresholds"] == {
        "naturalness_min": 3,
        "insight_min": 3,
        "completeness_auto_required": True,
    }


def test_dimension_lookup_e6_registered():
    """Slice 4 — e6 entry 등록 + e2 패턴 mirror 확인."""
    from scripts.validation.score_step8 import DIMENSION_LOOKUP

    assert "e6" in DIMENSION_LOOKUP
    e6 = DIMENSION_LOOKUP["e6"]
    assert e6["dim1"]["key"] == "naturalness"
    assert e6["dim2"]["key"] == "insight"
    assert e6["model_label_field"] == "model_label"
    assert e6["result_structure"] == "nested"
    assert e6.get("additional_lex_check") == "completeness_auto"
    assert "slice4" in e6["default_raw"]


def test_main_unified_dispatch_e1_e2_e6_only():
    """_main_unified는 e1/e2/e6만 처리. e5는 main()에서 score_step8_e5 delegation."""
    from scripts.validation import score_step8

    # e1/e2/e6 모두 _main_unified 함수 존재
    assert callable(score_step8._main_unified)
    # _main_e2 deprecated alias 호환
    assert callable(score_step8._main_e2)
