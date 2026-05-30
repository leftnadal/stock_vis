"""Slice 13 Part 3 — POST /api/v1/coach/e3/ contract test (E2 패턴 복제).

핵심 검증:
  - 정상 요청 → 200 + E3Output 스키마 부합
  - 필수 필드 누락 → 400 (Pydantic 에러 평탄화)
  - service 예외 → 500 + 스택트레이스 노출 없음
  - LLM은 mock (Part 3 real 호출 0)

★ contract test 본질: API 응답이 E3Output 계약을 지키는가 — 회귀 보호.
★ preset_id / metrics 는 본 endpoint에 노출하지 않는다 (#66 분리).
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_raw

E3_ENDPOINT = "/api/v1/coach/e3/"


# Slice 16 Step 0-B #70: api_client fixture는 conftest.py로 이전 — IsAuthenticated 통과.
@pytest.fixture
def e3_request_body() -> dict:
    """portfolio_a2 fixture에서 E3 요청 body 추출 (base + specific 평탄화)."""
    fixture = load_portfolio_a2_raw()
    return {
        "portfolio_id": fixture["portfolio_id"],
        "fetched_at": fixture["fetched_at"],
        "preset": fixture["preset"],
        "holdings": fixture["holdings"],
        **fixture["inputs"]["e3"],  # concentration_metrics
    }


@pytest.fixture
def mock_llm_response_e3():
    """run_e3_coach가 반환할 mock 결과 dict (E3Output 계약 부합)."""
    return {
        "output": {
            "summary": "포트폴리오 HHI 0.21, top3 65% — 중도 집중.",
            "key_observations": [
                "HHI 0.21 (균등 분산 0.10 대비 2배)",
                "최상위 종목 25% — 단일 노출 위험",
            ],
            "confidence": "medium",
            "action_items": [],
            "risk_flags": ["max_position_weight_over_20pct"],
        },
        "llm_metadata": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "latency_ms": 1080,
            "input_tokens": 720,
            "output_tokens": 160,
            "cost_usd": 0.0010,
            "fallback_from": None,
        },
    }


# ============================================================
# 정상 경로
# ============================================================


def test_post_e3_returns_200_with_valid_request(
    api_client, e3_request_body, mock_llm_response_e3
):
    """POST /api/v1/coach/e3/ 정상 요청 → 200 + E3Output 계약 부합."""
    with patch(
        "portfolio.api.views.run_e3_coach", return_value=mock_llm_response_e3
    ) as mock_run:
        response = api_client.post(
            E3_ENDPOINT, data=e3_request_body, format="json"
        )

    assert response.status_code == 200, response.data
    assert mock_run.call_count == 1
    # ★ preset_id/metrics 미전달 확인 (endpoint 표면 비노출 보증)
    call_kwargs = mock_run.call_args.kwargs
    assert "preset_id" not in call_kwargs or call_kwargs.get("preset_id") is None
    assert "metrics" not in call_kwargs or call_kwargs.get("metrics") is None

    data = response.json()
    assert "output" in data
    assert "llm_metadata" in data
    output = data["output"]
    assert isinstance(output["summary"], str) and output["summary"]
    assert isinstance(output["key_observations"], list)
    assert output["confidence"] in ("high", "medium", "low")
    # E3 특화 필드
    assert "action_items" in output
    assert "risk_flags" in output


def test_post_e3_response_passes_e3output_validation(
    api_client, e3_request_body, mock_llm_response_e3
):
    """★ contract test 핵심 — 응답 dict가 다시 E3Output(Pydantic)으로 검증 가능."""
    from portfolio.schemas.commentary_output import E3Output

    with patch(
        "portfolio.api.views.run_e3_coach", return_value=mock_llm_response_e3
    ):
        response = api_client.post(
            E3_ENDPOINT, data=e3_request_body, format="json"
        )

    output_dict = response.json()["output"]
    revalidated = E3Output(**output_dict)
    assert revalidated.summary == mock_llm_response_e3["output"]["summary"]


# ============================================================
# 검증 실패 (400)
# ============================================================


def test_post_e3_missing_required_field_returns_400(api_client, e3_request_body):
    """필수 필드 (`concentration_metrics`) 누락 → 400."""
    body = dict(e3_request_body)
    del body["concentration_metrics"]
    response = api_client.post(E3_ENDPOINT, data=body, format="json")
    assert response.status_code == 400
    data = response.json()
    assert any("concentration_metrics" in k for k in data) or "concentration_metrics" in str(data)


def test_post_e3_invalid_type_returns_400(api_client, e3_request_body):
    """잘못된 타입 (holdings를 str으로) → 400."""
    body = dict(e3_request_body)
    body["holdings"] = "not_a_list"
    response = api_client.post(E3_ENDPOINT, data=body, format="json")
    assert response.status_code == 400


def test_post_e3_non_dict_body_returns_400(api_client):
    """JSON object가 아닌 body → 400."""
    response = api_client.post(
        E3_ENDPOINT,
        data=json.dumps([1, 2, 3]),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_post_e3_invalid_provider_returns_400(api_client, e3_request_body):
    """미등록 provider query param → 400."""
    response = api_client.post(
        f"{E3_ENDPOINT}?provider=invalid_provider",
        data=e3_request_body,
        format="json",
    )
    assert response.status_code == 400
    assert "Invalid provider" in str(response.json())


# ============================================================
# Service 예외 (500, 502, 429)
# ============================================================


def test_post_e3_service_exception_returns_500_no_stacktrace(
    api_client, e3_request_body
):
    """run_e3_coach가 일반 예외 → 500 + 스택트레이스 노출 금지."""
    with patch(
        "portfolio.api.views.run_e3_coach",
        side_effect=RuntimeError("internal database error with secret /tmp/qrs"),
    ):
        response = api_client.post(
            E3_ENDPOINT, data=e3_request_body, format="json"
        )

    assert response.status_code == 500
    body_str = json.dumps(response.json())
    assert "secret" not in body_str
    assert "/tmp/qrs" not in body_str
    assert "Internal server error" in body_str


def test_post_e3_llm_budget_exceeded_returns_429(api_client, e3_request_body):
    """LLMBudgetExceededError → 429."""
    from portfolio.llm.exceptions import LLMBudgetExceededError

    with patch(
        "portfolio.api.views.run_e3_coach",
        side_effect=LLMBudgetExceededError(scope="slice", count=51, limit=50),
    ):
        response = api_client.post(
            E3_ENDPOINT, data=e3_request_body, format="json"
        )

    assert response.status_code == 429


def test_post_e3_llm_error_returns_502(api_client, e3_request_body):
    """기타 LLMError → 502."""
    from portfolio.llm.exceptions import LLMRateLimitError

    with patch(
        "portfolio.api.views.run_e3_coach",
        side_effect=LLMRateLimitError("upstream rate limit"),
    ):
        response = api_client.post(
            E3_ENDPOINT, data=e3_request_body, format="json"
        )

    assert response.status_code == 502


# ============================================================
# Schema drift 안전망
# ============================================================


def test_post_e3_service_returns_drifted_output_caught_by_serializer(
    api_client, e3_request_body, mock_llm_response_e3
):
    """★ service 응답이 E3Output 계약을 깨면 serializer가 잡아낸다."""
    drifted = dict(mock_llm_response_e3)
    drifted["output"] = dict(drifted["output"], confidence="unknown_value")
    with patch(
        "portfolio.api.views.run_e3_coach", return_value=drifted
    ):
        response = api_client.post(
            E3_ENDPOINT, data=e3_request_body, format="json"
        )
    assert response.status_code in (400, 500)
