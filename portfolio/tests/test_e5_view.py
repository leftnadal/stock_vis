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
# Mock의 mode가 LLMClient의 동작 시뮬레이션 (fallback / error / budget).
# ============================================================

# ⓐ Slice 1 LLMResponse 스키마는 schema 통과 가능한 OneLineDiagnosis JSON을 반환.
# ⓑ E5는 다른 schema(E5Response). Mock의 _MOCK_TEXT는 OneLineDiagnosis JSON이라
#    service.parse_json_response(E5Response, ...) 호출 시 ValidationError 발생.
# ⓒ 본 테스트는 Mock의 응답을 E5Response schema로 통과시키도록 별도 Mock 클래스 사용.


def _e5_mock_text() -> str:
    """E5Response schema 통과 가능한 결정론적 JSON."""
    return (
        '{"adjustments":[{"ticker":"TSLA","action":"decrease",'
        '"delta_weight":-0.05,"target_weight":null,'
        '"reason_quote":"TSLA 줄여줘"}],'
        '"confidence":4,"ambiguity_notes":null,'
        '"no_actionable_intent":false}'
    )


class _E5MockLLMClient(MockLLMClient):
    """E5 schema에 맞는 텍스트 반환하는 Mock."""

    def _mock_response(self, provider, fallback_from):  # type: ignore[override]
        from portfolio.schemas.llm import LLMResponse

        return LLMResponse(
            text=_e5_mock_text(),
            provider=provider,
            model=f"mock-{provider}",
            latency_ms=100,
            input_tokens=500,
            output_tokens=50,
            cost_usd=0.001,
            fallback_from=fallback_from,
        )


@pytest.mark.django_db
def test_e5_view_rate_limit_first_fallback(django_client, valid_request_body):
    """Gemini RateLimit → Anthropic 폴백 → 200, fallback_from=gemini."""
    mock = _E5MockLLMClient(mode="rate_limit_first")
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
    mock = _E5MockLLMClient(mode="timeout_first")
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
    mock = _E5MockLLMClient(mode="auth_error")
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
    mock = _E5MockLLMClient(mode="budget_exceeded")
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
