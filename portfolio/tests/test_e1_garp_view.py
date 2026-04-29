"""
E1+GARP view 통합 테스트 (5케이스, slice 1 §7).

LLMClient를 MockLLMClient로 patch하여 결정론적 동작 검증.
실제 외부 API 호출 없음.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import Client

from portfolio.llm.mocks import MockLLMClient


@pytest.fixture
def django_client() -> Client:
    return Client()


# ============================================================
# Case 1: 정상 호출 → 200
# ============================================================
@pytest.mark.django_db
def test_e1_garp_normal_call(django_client):
    """Gemini 정상 호출 → 200, OneLineDiagnosis schema 통과, fallback_from is None."""
    mock = MockLLMClient(mode="normal")
    with patch("portfolio.services.e1_garp.LLMClient", return_value=mock):
        response = django_client.get("/api/coach/e1/garp/?provider=gemini")

    assert response.status_code == 200
    data = response.json()

    assert "diagnosis" in data
    assert "llm_metadata" in data
    # OneLineDiagnosis 스키마 통과 확인 (필드명 + 타입)
    assert isinstance(data["diagnosis"]["headline"], str)
    assert isinstance(data["diagnosis"]["summary"], str)
    assert 10 <= len(data["diagnosis"]["headline"]) <= 60
    assert 30 <= len(data["diagnosis"]["summary"]) <= 500

    metadata = data["llm_metadata"]
    assert metadata["provider"] == "gemini"
    assert metadata["fallback_from"] is None
    assert metadata["latency_ms"] >= 0
    assert metadata["input_tokens"] > 0
    assert metadata["output_tokens"] > 0
    assert metadata["cost_usd"] >= 0


# ============================================================
# Case 2: RateLimit → Anthropic 폴백 → 200
# ============================================================
@pytest.mark.django_db
def test_e1_garp_rate_limit_fallback(django_client):
    """Gemini RateLimit → Anthropic 폴백 성공, fallback_from='gemini'."""
    mock = MockLLMClient(mode="rate_limit_first")
    with patch("portfolio.services.e1_garp.LLMClient", return_value=mock):
        response = django_client.get("/api/coach/e1/garp/?provider=gemini")

    assert response.status_code == 200
    metadata = response.json()["llm_metadata"]
    assert metadata["provider"] == "anthropic"
    assert metadata["fallback_from"] == "gemini"


# ============================================================
# Case 3: Timeout → Anthropic 폴백 → 200
# ============================================================
@pytest.mark.django_db
def test_e1_garp_timeout_fallback(django_client):
    """Gemini Timeout → Anthropic 폴백 성공, fallback_from='gemini'."""
    mock = MockLLMClient(mode="timeout_first")
    with patch("portfolio.services.e1_garp.LLMClient", return_value=mock):
        response = django_client.get("/api/coach/e1/garp/?provider=gemini")

    assert response.status_code == 200
    metadata = response.json()["llm_metadata"]
    assert metadata["provider"] == "anthropic"
    assert metadata["fallback_from"] == "gemini"


# ============================================================
# Case 4: AuthError → 폴백 안 함 → 500
# ============================================================
@pytest.mark.django_db
def test_e1_garp_auth_error_no_fallback(django_client):
    """AuthError는 폴백 트리거 아님 → 500 응답."""
    mock = MockLLMClient(mode="auth_error")
    with patch("portfolio.services.e1_garp.LLMClient", return_value=mock):
        response = django_client.get("/api/coach/e1/garp/?provider=gemini")

    assert response.status_code == 500
    body = response.json()
    assert "error" in body


# ============================================================
# Case 5: 비용 가드 발동 → 503
# ============================================================
@pytest.mark.django_db
def test_e1_garp_budget_exceeded(django_client):
    """비용 가드 임계 도달 → 503 응답."""
    mock = MockLLMClient(mode="budget_exceeded")
    with patch("portfolio.services.e1_garp.LLMClient", return_value=mock):
        response = django_client.get("/api/coach/e1/garp/?provider=gemini")

    assert response.status_code == 503
    body = response.json()
    assert "error" in body
