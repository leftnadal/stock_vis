"""E3 view 통합 테스트 (Slice 5 Step 4).

기본 view 5건:
  - normal (Mock service 반환)
  - invalid_provider
  - invalid_body (json parse error)
  - validation_error (preset_id 누락 등 — E3Request validator)
  - method_not_allowed (GET → 405)

Mock LLMClient 4건:
  - rate_limit_first → fallback (200, fallback_from=gemini)
  - timeout_first    → fallback
  - auth_error       → 500 (no fallback)
  - budget_exceeded  → 429
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from django.test import Client

from portfolio.llm.mocks import MockLLMClient
from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_tech,
)


@pytest.fixture
def django_client():
    return Client()


@pytest.fixture
def valid_request_body() -> dict:
    """garp_tech AnalysisContext.model_dump() → E3Request body."""
    ctx = get_context_garp_tech()
    return {"analysis_context": ctx.model_dump(mode="json")}


# ============================================================
# 기본 view 동작 (5)
# ============================================================


@pytest.mark.django_db
def test_e3_view_normal(django_client, valid_request_body):
    """정상 호출 — service에서 dict 반환 → 200."""
    mock_result = {
        "response": {
            "comments": [
                {
                    "metric_id": "roic",
                    "one_liner": "ROIC가 동종 업계 대비 양호한 수준입니다.",
                },
            ]
        },
        "metadata": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "latency_ms": 1500,
            "input_tokens": 800,
            "output_tokens": 200,
            "cost_usd": 0.002,
            "fallback_from": None,
        },
    }
    with patch("portfolio.views.run_e3", return_value=mock_result):
        resp = django_client.post(
            "/api/coach/e3/metric-comment/?provider=haiku",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data and "metadata" in data
    assert data["response"]["comments"][0]["metric_id"] == "roic"


@pytest.mark.django_db
def test_e3_view_invalid_provider(django_client, valid_request_body):
    resp = django_client.post(
        "/api/coach/e3/metric-comment/?provider=not_a_provider",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_provider"


@pytest.mark.django_db
def test_e3_view_invalid_body(django_client):
    resp = django_client.post(
        "/api/coach/e3/metric-comment/",
        data="not json",
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_request"


@pytest.mark.django_db
def test_e3_view_validation_error_extra_field(django_client, valid_request_body):
    """E3Request extra='forbid' — 정의되지 않은 필드 → 400."""
    payload = {**valid_request_body, "unknown_key": "hack"}
    resp = django_client.post(
        "/api/coach/e3/metric-comment/",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_request"


@pytest.mark.django_db
def test_e3_view_get_not_allowed(django_client):
    resp = django_client.get("/api/coach/e3/metric-comment/")
    assert resp.status_code == 405


# ============================================================
# Mock LLMClient — fallback / error 시나리오 (4)
# ============================================================


def _build_e3_mock(mode: str) -> MockLLMClient:
    """E3 Mock factory — text_strategy='e3'으로 고정."""
    return MockLLMClient(mode=mode, text_strategy="e3")


@pytest.mark.django_db
def test_e3_view_rate_limit_first_fallback(django_client, valid_request_body):
    """Gemini RateLimit → Anthropic 폴백 → 200, fallback_from=gemini."""
    mock = _build_e3_mock(mode="rate_limit_first")
    with patch(
        "portfolio.services.e3_metric_comment.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e3/metric-comment/?provider=gemini",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 200
    metadata = resp.json()["metadata"]
    assert metadata["provider"] == "anthropic"
    assert metadata["fallback_from"] == "gemini"


@pytest.mark.django_db
def test_e3_view_timeout_first_fallback(django_client, valid_request_body):
    """Gemini Timeout → Anthropic 폴백 → 200."""
    mock = _build_e3_mock(mode="timeout_first")
    with patch(
        "portfolio.services.e3_metric_comment.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e3/metric-comment/?provider=gemini",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 200
    metadata = resp.json()["metadata"]
    assert metadata["provider"] == "anthropic"
    assert metadata["fallback_from"] == "gemini"


@pytest.mark.django_db
def test_e3_view_auth_error_no_fallback(django_client, valid_request_body):
    """AuthError는 폴백 트리거 아님 → 500."""
    mock = _build_e3_mock(mode="auth_error")
    with patch(
        "portfolio.services.e3_metric_comment.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e3/metric-comment/?provider=gemini",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 500


@pytest.mark.django_db
def test_e3_view_budget_exceeded(django_client, valid_request_body):
    """비용 가드 발동 → 429."""
    mock = _build_e3_mock(mode="budget_exceeded")
    with patch(
        "portfolio.services.e3_metric_comment.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e3/metric-comment/?provider=haiku",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 429
    assert resp.json()["error"] == "budget_exceeded"
