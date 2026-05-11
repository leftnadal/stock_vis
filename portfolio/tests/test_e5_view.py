"""
Slice 2 Step 3 + Step 4 — E5 view 통합 테스트.

Step 3 (3 케이스):
  - normal (Mock service 반환)
  - invalid_provider
  - invalid_body (json parse error)

Step 4 (4 케이스, Mock LLMClient):
  - rate_limit_first → fallback (LLMClient 실제 폴백 메커니즘)
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


@pytest.fixture
def django_client():
    return Client()


@pytest.fixture
def valid_request_body() -> dict:
    return {
        "analysis_context": {
            "holdings": [
                {"ticker": "TSLA", "weight": 0.5},
                {"ticker": "MSFT", "weight": 0.3},
                {"ticker": "NVDA", "weight": 0.2},
            ],
            "analysis_summary": {"one_line_diagnosis": "test"},
        },
        "user_command": "TSLA 줄여줘",
    }


# ============================================================
# Step 3 — 기본 view 동작
# ============================================================


@pytest.mark.django_db
def test_e5_view_normal(django_client, valid_request_body):
    """정상 호출 — service에서 dict 반환 → 200."""
    mock_result = {
        "response": {
            "adjustments": [
                {
                    "ticker": "TSLA",
                    "action": "decrease",
                    "delta_weight": -0.05,
                    "target_weight": None,
                    "reason_quote": "TSLA 줄여줘",
                }
            ],
            "confidence": 4,
            "ambiguity_notes": None,
            "no_actionable_intent": False,
        },
        "metadata": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "latency_ms": 1200,
            "input_tokens": 500,
            "output_tokens": 100,
            "cost_usd": 0.001,
            "fallback_from": None,
        },
    }
    with patch(
        "portfolio.views.run_e5", return_value=mock_result
    ):
        resp = django_client.post(
            "/api/coach/e5/adjustment/?provider=haiku",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data and "metadata" in data
    assert data["response"]["adjustments"][0]["ticker"] == "TSLA"


@pytest.mark.django_db
def test_e5_view_invalid_provider(django_client, valid_request_body):
    resp = django_client.post(
        "/api/coach/e5/adjustment/?provider=invalid",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_provider"


@pytest.mark.django_db
def test_e5_view_invalid_body(django_client):
    resp = django_client.post(
        "/api/coach/e5/adjustment/",
        data="not json",
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_request"


# ============================================================
# Step 4 — Mock LLMClient 폴백/에러 시나리오
#
# Slice 1 e1_garp_view 테스트와 동일한 패턴: service의 LLMClient를 patch.
# Slice 2 Step 0.5: text_strategy="e5"로 E5Response schema JSON 응답.
# ============================================================


def _build_e5_mock(mode: str) -> MockLLMClient:
    """E5 진입점 Mock factory — text_strategy='e5'로 고정."""
    return MockLLMClient(mode=mode, text_strategy="e5")


@pytest.mark.django_db
def test_e5_view_rate_limit_first_fallback(django_client, valid_request_body):
    """Gemini RateLimit → Anthropic 폴백 → 200, fallback_from=gemini."""
    mock = _build_e5_mock(mode="rate_limit_first")
    with patch(
        "portfolio.services.e5_adjustment_parser.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e5/adjustment/?provider=gemini",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 200
    metadata = resp.json()["metadata"]
    assert metadata["provider"] == "anthropic"
    assert metadata["fallback_from"] == "gemini"


@pytest.mark.django_db
def test_e5_view_timeout_first_fallback(django_client, valid_request_body):
    """Gemini Timeout → Anthropic 폴백 → 200."""
    mock = _build_e5_mock(mode="timeout_first")
    with patch(
        "portfolio.services.e5_adjustment_parser.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e5/adjustment/?provider=gemini",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 200
    metadata = resp.json()["metadata"]
    assert metadata["provider"] == "anthropic"
    assert metadata["fallback_from"] == "gemini"


@pytest.mark.django_db
def test_e5_view_auth_error_no_fallback(django_client, valid_request_body):
    """AuthError는 폴백 트리거 아님 → 500."""
    mock = _build_e5_mock(mode="auth_error")
    with patch(
        "portfolio.services.e5_adjustment_parser.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e5/adjustment/?provider=gemini",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 500


@pytest.mark.django_db
def test_e5_view_budget_exceeded(django_client, valid_request_body):
    """비용 가드 발동 → 429."""
    mock = _build_e5_mock(mode="budget_exceeded")
    with patch(
        "portfolio.services.e5_adjustment_parser.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e5/adjustment/?provider=haiku",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 429
    assert resp.json()["error"] == "budget_exceeded"
