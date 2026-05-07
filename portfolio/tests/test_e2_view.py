"""E2 view 통합 테스트 (Slice 3 Step 3 + Step 4)."""

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
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.5},
                {"ticker": "GOOGL", "weight": 0.3},
                {"ticker": "AAPL", "weight": 0.2},
            ],
            "analysis_summary": {"one_line_diagnosis": "GARP 적합도 양호."},
            "metrics": {"P/E": 22.5, "ROE": 0.18},
        },
    }


# ============================================================
# Step 3 — 기본 view 동작
# ============================================================


@pytest.mark.django_db
def test_e2_view_normal(django_client, valid_request_body):
    """정상 호출 — service에서 dict 반환 → 200."""
    mock_result = {
        "response": {
            "card": {
                "summary": "GARP 적합도 양호. 균형 잡힌 포트폴리오 분석.",
                "strengths": ["P/E 22.5 적정 수준", "ROE 18% 우수한 수익성"],
                "weaknesses": ["배당수익률 1.2% 다소 낮음"],
                "actions": ["분기별 ROE 모니터링 권장"],
            },
            "preset_id": "garp",
        },
        "metadata": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "latency_ms": 1500,
            "input_tokens": 800,
            "output_tokens": 200,
            "cost_usd": 0.005,
            "fallback_from": None,
        },
    }
    with patch("portfolio.views.run_e2", return_value=mock_result):
        resp = django_client.post(
            "/api/coach/e2/diagnostic-card/?provider=haiku",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data and "metadata" in data
    assert data["response"]["card"]["summary"]
    assert data["response"]["preset_id"] == "garp"


@pytest.mark.django_db
def test_e2_view_invalid_provider(django_client, valid_request_body):
    resp = django_client.post(
        "/api/coach/e2/diagnostic-card/?provider=invalid",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_provider"


@pytest.mark.django_db
def test_e2_view_invalid_body(django_client):
    resp = django_client.post(
        "/api/coach/e2/diagnostic-card/",
        data="not json",
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_request"


# ============================================================
# Step 4 — Mock LLMClient 폴백/에러 시나리오 (Slice 2 패턴 mirror)
# ============================================================


def _build_e2_mock(mode: str) -> MockLLMClient:
    """E2 진입점 Mock factory — text_strategy='e2'."""
    return MockLLMClient(mode=mode, text_strategy="e2")


@pytest.mark.django_db
def test_e2_view_rate_limit_first_fallback(django_client, valid_request_body):
    """Gemini RateLimit → Anthropic 폴백 → 200, fallback_from=gemini."""
    mock = _build_e2_mock(mode="rate_limit_first")
    with patch(
        "portfolio.services.e2_diagnostic_card.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e2/diagnostic-card/?provider=gemini",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 200
    metadata = resp.json()["metadata"]
    assert metadata["provider"] == "anthropic"
    assert metadata["fallback_from"] == "gemini"


@pytest.mark.django_db
def test_e2_view_timeout_first_fallback(django_client, valid_request_body):
    """Gemini Timeout → Anthropic 폴백 → 200."""
    mock = _build_e2_mock(mode="timeout_first")
    with patch(
        "portfolio.services.e2_diagnostic_card.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e2/diagnostic-card/?provider=gemini",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 200
    metadata = resp.json()["metadata"]
    assert metadata["fallback_from"] == "gemini"


@pytest.mark.django_db
def test_e2_view_auth_error_no_fallback(django_client, valid_request_body):
    """AuthError는 폴백 트리거 아님 → 500."""
    mock = _build_e2_mock(mode="auth_error")
    with patch(
        "portfolio.services.e2_diagnostic_card.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e2/diagnostic-card/?provider=gemini",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 500


@pytest.mark.django_db
def test_e2_view_budget_exceeded(django_client, valid_request_body):
    """비용 가드 발동 → 429."""
    mock = _build_e2_mock(mode="budget_exceeded")
    with patch(
        "portfolio.services.e2_diagnostic_card.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e2/diagnostic-card/?provider=haiku",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 429
    assert resp.json()["error"] == "budget_exceeded"
