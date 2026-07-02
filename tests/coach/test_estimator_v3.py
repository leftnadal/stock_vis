"""Slice 10 Step 0 §2 — estimator v3 단위 테스트 (cost 카테고리).

KPI:
- input_tokens 실측 PASS (mock client)
- output_tokens v2 호환
- cache hit/miss 동작
- API 실패 시 v2 fallback
- backward-compat 100%

슬라이스 ④ #3: 직접 Anthropic 주입(set_client) 제거 → 코어 count_tokens 경유.
mock seam = `anthropic.Anthropic` 패치(코어 provider가 생성) + `_resolve_api_key`(키 해소).
"""

from __future__ import annotations

import contextlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from apps.portfolio.measure import estimator_v3 as e3


@pytest.fixture(autouse=True)
def _reset_state():
    """각 테스트 전 cache 초기화 → 격리 보장."""
    e3.reset_cache()
    yield
    e3.reset_cache()


def _make_mock_client(input_tokens: int = 123, raise_exc: Exception | None = None) -> MagicMock:
    client = MagicMock()
    if raise_exc:
        client.messages.count_tokens.side_effect = raise_exc
    else:
        client.messages.count_tokens.return_value = SimpleNamespace(input_tokens=input_tokens)
    return client


@contextlib.contextmanager
def _use_client(client):
    """슬라이스 ④ seam: 코어 provider가 생성하는 anthropic.Anthropic을 mock으로 치환 + 키 해소.

    (구 e3.set_client 주입 대체 — 코어 count_tokens가 소유하는 client를 가로챈다.)
    """
    with patch("anthropic.Anthropic", return_value=client), patch(
        "packages.shared.llm.providers.anthropic._resolve_api_key",
        return_value="fake-key",
    ):
        yield


def test_estimate_input_tokens_uses_api():
    """count_tokens API 응답을 input_tokens로 반환."""
    with _use_client(_make_mock_client(input_tokens=456)):
        result = e3.estimate_input_tokens([{"role": "user", "content": "hi"}], system="sys")
    assert result == 456


def test_cache_hit_avoids_duplicate_api_call():
    """동일 (messages, system, model) → 두 번째 호출은 cache hit (API 미호출)."""
    client = _make_mock_client(input_tokens=42)
    msgs = [{"role": "user", "content": "동일"}]
    with _use_client(client):
        e3.estimate_input_tokens(msgs, system="s")
        e3.estimate_input_tokens(msgs, system="s")
    assert client.messages.count_tokens.call_count == 1
    assert e3.cache_stats()["size"] == 1


def test_cache_miss_for_different_inputs():
    """다른 messages → cache miss → API 두 번 호출."""
    client = _make_mock_client(input_tokens=10)
    with _use_client(client):
        e3.estimate_input_tokens([{"role": "user", "content": "A"}], system="s")
        e3.estimate_input_tokens([{"role": "user", "content": "B"}], system="s")
    assert client.messages.count_tokens.call_count == 2
    assert e3.cache_stats()["size"] == 2


def test_api_failure_falls_back_to_v2(caplog):
    """API exception → v2 char/3 fallback + warn log."""
    msgs = [{"role": "user", "content": "안녕하세요 한국어 텍스트입니다"}]
    with _use_client(_make_mock_client(raise_exc=RuntimeError("rate limit"))):
        with caplog.at_level("WARNING"):
            result = e3.estimate_input_tokens(msgs, system=None)
    assert result > 0  # fallback이 0이 아닌 값 반환
    assert any("fallback to v2" in r.message for r in caplog.records)


def test_estimate_output_tokens_global_fallback():
    """None/0 → 0. 진입점 미지정 → GLOBAL_OUTPUT_FIT OLS 적용 (Slice 13 신모델).

    구모델은 int(250 × 0.7584) = 189이었으나, 신모델 OLS는
    int(a + b × chars). 계수가 다르므로 정확한 동등은 아니지만 reasonable 범위 확인.
    """
    assert e3.estimate_output_tokens(None) == 0
    assert e3.estimate_output_tokens(0) == 0
    a, b = e3.GLOBAL_OUTPUT_FIT
    expected = int(a + b * 250)
    assert e3.estimate_output_tokens(250) == expected


def test_estimate_output_tokens_per_entry_point():
    """진입점별 OLS fit 적용 — 8 EP × (a + b × chars) (Slice 13 신모델).

    구모델 단변량 ratio → 신모델 다변량 OLS로 교체됨. 진입점별 fit이 있으면
    그 계수가 사용되어야 한다.
    """
    chars = 1000
    for ep, (a, b) in e3.ENTRY_POINT_OUTPUT_FITS.items():
        result = e3.estimate_output_tokens(chars, entry_point=ep)
        # (EP, model) 셀이 등록되어 있으면 그게 우선 (default model이 etxending)
        ep_model_fit = e3.ENTRY_POINT_MODEL_OUTPUT_FITS.get(
            (ep, e3._model_short(e3.DEFAULT_MODEL))
        )
        if ep_model_fit is not None:
            expected = max(0, int(ep_model_fit[0] + ep_model_fit[1] * chars))
        else:
            expected = max(0, int(a + b * chars))
        assert result == expected, (
            f"{ep}: got {result}, expected {expected}"
        )


def test_estimate_output_tokens_unknown_ep_falls_back_to_global():
    """미등록 진입점 → GLOBAL_OUTPUT_FIT fallback (Slice 13 신모델)."""
    a, b = e3.GLOBAL_OUTPUT_FIT
    expected = max(0, int(a + b * 500))
    assert e3.estimate_output_tokens(500, entry_point="unknown") == expected
    assert e3.estimate_output_tokens(500, entry_point="e99") == expected


def test_estimate_output_tokens_six_entry_points_registered():
    """KPI 2: e1~e6 6개 진입점 ratio 등록 확인."""
    for ep in ("e1", "e2", "e3", "e4_conversation", "e5", "e6"):
        assert ep in e3.ENTRY_POINT_OUTPUT_RATIOS, f"{ep} 누락"


def test_legacy_estimate_tokens_wrapper():
    """backward-compat: dict {input_tokens, output_tokens, total} 반환.

    Slice 13: 신모델 OLS — entry_point 미지정 시 GLOBAL_OUTPUT_FIT.
    """
    with _use_client(_make_mock_client(input_tokens=80)):
        result = e3.estimate_tokens(
            [{"role": "user", "content": "x"}],
            system=None,
            expected_output_chars=125,
        )
    expected_out = e3.estimate_output_tokens(125)
    assert result == {
        "input_tokens": 80,
        "output_tokens": expected_out,
        "total": 80 + expected_out,
    }


def test_legacy_estimate_tokens_with_entry_point():
    """entry_point 지정 → 진입점별 OLS fit 적용 (Slice 13 신모델)."""
    with _use_client(_make_mock_client(input_tokens=100)):
        result = e3.estimate_tokens(
            [{"role": "user", "content": "x"}],
            system=None,
            expected_output_chars=500,
            entry_point="e6",
        )
    assert result["output_tokens"] == e3.estimate_output_tokens(500, entry_point="e6")


def test_reset_cache_clears_state():
    """reset_cache() → 캐시 비움 (slice 전환 시)."""
    with _use_client(_make_mock_client(input_tokens=1)):
        e3.estimate_input_tokens([{"role": "user", "content": "x"}], system=None)
    assert e3.cache_stats()["size"] == 1
    e3.reset_cache()
    assert e3.cache_stats()["size"] == 0


def test_cache_key_includes_model_and_system():
    """동일 messages지만 다른 model 또는 system → cache miss."""
    client = _make_mock_client(input_tokens=5)
    msgs = [{"role": "user", "content": "x"}]
    with _use_client(client):
        e3.estimate_input_tokens(msgs, system="s1", model="claude-haiku-4-5")
        e3.estimate_input_tokens(msgs, system="s2", model="claude-haiku-4-5")  # system 다름
        e3.estimate_input_tokens(msgs, system="s1", model="claude-sonnet-4-5")  # model 다름
    assert client.messages.count_tokens.call_count == 3
    assert e3.cache_stats()["size"] == 3
