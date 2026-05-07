"""E6 view 통합 테스트 (Slice 4 Step 4).

Step 3 (3 케이스):
  - normal (Mock service 반환)
  - invalid_provider
  - invalid_body (json parse error)
  - validation_error (Pydantic — adjustments 빈 리스트)
  - method not allowed (GET → 405)

Step 4 Mock LLMClient (4 케이스):
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


@pytest.fixture
def django_client():
    return Client()


@pytest.fixture
def valid_request_body() -> dict:
    return {
        "analysis_context": {
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.30},
                {"ticker": "TSLA", "weight": 0.20},
                {"ticker": "NVDA", "weight": 0.50},
            ],
            "analysis_summary": {"one_line_diagnosis": "기술주 집중"},
        },
        "adjustments": [
            {
                "ticker": "TSLA",
                "action": "decrease",
                "delta_weight": -0.10,
                "target_weight": None,
                "reason_quote": "TSLA 줄여줘",
            },
            {
                "ticker": "JNJ",
                "action": "add",
                "delta_weight": None,
                "target_weight": 0.15,
                "reason_quote": "존슨앤존슨 추가",
            },
        ],
        "user_intent": "테슬라 줄이고 존슨앤존슨 추가",
    }


# ============================================================
# 기본 view 동작
# ============================================================


@pytest.mark.django_db
def test_e6_view_normal(django_client, valid_request_body):
    """정상 호출 — service에서 dict 반환 → 200."""
    mock_result = {
        "response": {
            "headline": "기술주 집중도 완화로 위험 균형 개선",
            "before_summary": "기술주 비중 70%로 집중 위험 높음 — 변동성 큰 구성.",
            "after_summary": "기술주 55%로 축소 + 디펜시브 15% 추가로 균형 개선.",
            "key_changes": [
                {"aspect": "allocation", "description": "테슬라 비중 20% → 10% 축소"},
            ],
            "risk_assessment": "포트폴리오 변동성이 다소 낮아질 것으로 예상됩니다.",
            "closing_remarks": "수익률 상한선 일부 양보 가능성 존재.",
        },
        "metadata": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "latency_ms": 1500,
            "input_tokens": 600,
            "output_tokens": 400,
            "cost_usd": 0.003,
            "fallback_from": None,
        },
    }
    with patch("portfolio.views.run_e6", return_value=mock_result):
        resp = django_client.post(
            "/api/coach/e6/comparison/?provider=haiku",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data and "metadata" in data
    assert data["response"]["key_changes"][0]["aspect"] == "allocation"


@pytest.mark.django_db
def test_e6_view_invalid_provider(django_client, valid_request_body):
    resp = django_client.post(
        "/api/coach/e6/comparison/?provider=not_a_provider",
        data=json.dumps(valid_request_body),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_provider"


@pytest.mark.django_db
def test_e6_view_invalid_body(django_client):
    resp = django_client.post(
        "/api/coach/e6/comparison/",
        data="not json",
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_request"


@pytest.mark.django_db
def test_e6_view_validation_error_empty_adjustments(django_client):
    """Pydantic — adjustments 빈 리스트 → 400 invalid_request."""
    payload = {
        "analysis_context": {"preset_id": "garp"},
        "adjustments": [],
    }
    resp = django_client.post(
        "/api/coach/e6/comparison/",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_request"


@pytest.mark.django_db
def test_e6_view_get_not_allowed(django_client):
    resp = django_client.get("/api/coach/e6/comparison/")
    assert resp.status_code == 405


# ============================================================
# Mock LLMClient — fallback / error 시나리오
# ============================================================


def _build_e6_mock(mode: str) -> MockLLMClient:
    """E6 진입점 Mock factory — text_strategy='e6'으로 고정."""
    return MockLLMClient(mode=mode, text_strategy="e6")


@pytest.mark.django_db
def test_e6_view_rate_limit_first_fallback(django_client, valid_request_body):
    """Gemini RateLimit → Anthropic 폴백 → 200, fallback_from=gemini."""
    mock = _build_e6_mock(mode="rate_limit_first")
    with patch(
        "portfolio.services.e6_comparison.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e6/comparison/?provider=gemini",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 200
    metadata = resp.json()["metadata"]
    assert metadata["provider"] == "anthropic"
    assert metadata["fallback_from"] == "gemini"


@pytest.mark.django_db
def test_e6_view_timeout_first_fallback(django_client, valid_request_body):
    """Gemini Timeout → Anthropic 폴백 → 200."""
    mock = _build_e6_mock(mode="timeout_first")
    with patch(
        "portfolio.services.e6_comparison.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e6/comparison/?provider=gemini",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 200
    metadata = resp.json()["metadata"]
    assert metadata["provider"] == "anthropic"
    assert metadata["fallback_from"] == "gemini"


@pytest.mark.django_db
def test_e6_view_auth_error_no_fallback(django_client, valid_request_body):
    """AuthError는 폴백 트리거 아님 → 500."""
    mock = _build_e6_mock(mode="auth_error")
    with patch(
        "portfolio.services.e6_comparison.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e6/comparison/?provider=gemini",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 500


@pytest.mark.django_db
def test_e6_view_budget_exceeded(django_client, valid_request_body):
    """비용 가드 발동 → 429."""
    mock = _build_e6_mock(mode="budget_exceeded")
    with patch(
        "portfolio.services.e6_comparison.LLMClient",
        return_value=mock,
    ):
        resp = django_client.post(
            "/api/coach/e6/comparison/?provider=haiku",
            data=json.dumps(valid_request_body),
            content_type="application/json",
        )
    assert resp.status_code == 429
    assert resp.json()["error"] == "budget_exceeded"
