"""Slice 13 Part 2 — POST /api/v1/coach/e2/ contract test (E1 패턴 복제).

핵심 검증:
  - 정상 요청 → 200 + E2Output 스키마 부합
  - 필수 필드 누락 → 400 (Pydantic 에러 평탄화)
  - service 예외 → 500 + 스택트레이스 노출 없음
  - LLM은 mock (Part 2 real 호출 0)

★ contract test 본질: API 응답이 E2Output 계약을 지키는가 — 회귀 보호.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_raw

# Slice 13 Part 1.5 패턴 답습 — 경로는 모듈 상수.
E2_ENDPOINT = "/api/v1/coach/e2/"


# Slice 16 Step 0-B #70: api_client fixture는 conftest.py로 이전 — IsAuthenticated 통과.
@pytest.fixture
def e2_request_body() -> dict:
    """portfolio_a2 fixture에서 E2 요청 body 추출 (base + specific 평탄화)."""
    fixture = load_portfolio_a2_raw()
    return {
        "portfolio_id": fixture["portfolio_id"],
        "fetched_at": fixture["fetched_at"],
        "preset": fixture["preset"],
        "holdings": fixture["holdings"],
        **fixture["inputs"]["e2"],  # portfolio_return_1y, sector_allocation
    }


@pytest.fixture
def mock_llm_response_e2():
    """run_e2_coach가 반환할 mock 결과 dict (E2Output 계약 부합)."""
    return {
        "output": {
            "summary": "포트폴리오 1년 수익률 +12%, 섹터 편중 IT 60%.",
            "key_observations": [
                "IT 섹터 비중 60% — 단일 섹터 의존도 위험",
                "방어 섹터(소비재/헬스케어) 비중 미달",
            ],
            "confidence": "medium",
            "quoted_metrics": {"return_1y": 0.12, "it_weight": 0.6},
            "metrics_table": "",
        },
        "llm_metadata": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "latency_ms": 1100,
            "input_tokens": 750,
            "output_tokens": 180,
            "cost_usd": 0.0011,
            "fallback_from": None,
        },
    }


# ============================================================
# 정상 경로
# ============================================================


def test_post_e2_returns_200_with_valid_request(
    api_client, e2_request_body, mock_llm_response_e2
):
    """POST /api/v1/coach/e2/ 정상 요청 → 200 + E2Output 계약 부합."""
    with patch(
        "portfolio.api.views.run_e2_coach", return_value=mock_llm_response_e2
    ) as mock_run:
        response = api_client.post(
            E2_ENDPOINT, data=e2_request_body, format="json"
        )

    assert response.status_code == 200, response.data
    assert mock_run.call_count == 1

    data = response.json()
    assert "output" in data
    assert "llm_metadata" in data
    output = data["output"]
    assert isinstance(output["summary"], str) and output["summary"]
    assert isinstance(output["key_observations"], list)
    assert output["confidence"] in ("high", "medium", "low")
    # E2 특화 필드
    assert "quoted_metrics" in output


def test_post_e2_response_passes_e2output_validation(
    api_client, e2_request_body, mock_llm_response_e2
):
    """★ contract test 핵심 — 응답 dict가 다시 E2Output(Pydantic)으로 검증 가능."""
    from portfolio.schemas.commentary_output import E2Output

    with patch(
        "portfolio.api.views.run_e2_coach", return_value=mock_llm_response_e2
    ):
        response = api_client.post(
            E2_ENDPOINT, data=e2_request_body, format="json"
        )

    output_dict = response.json()["output"]
    revalidated = E2Output(**output_dict)
    assert revalidated.summary == mock_llm_response_e2["output"]["summary"]


# ============================================================
# 검증 실패 (400)
# ============================================================


def test_post_e2_missing_required_field_returns_400(api_client, e2_request_body):
    """필수 필드 (`portfolio_return_1y`) 누락 → 400."""
    body = dict(e2_request_body)
    del body["portfolio_return_1y"]
    response = api_client.post(E2_ENDPOINT, data=body, format="json")
    assert response.status_code == 400
    data = response.json()
    assert any("portfolio_return_1y" in k for k in data) or "portfolio_return_1y" in str(data)


def test_post_e2_invalid_type_returns_400(api_client, e2_request_body):
    """잘못된 타입 (holdings를 str으로) → 400."""
    body = dict(e2_request_body)
    body["holdings"] = "not_a_list"
    response = api_client.post(E2_ENDPOINT, data=body, format="json")
    assert response.status_code == 400


def test_post_e2_non_dict_body_returns_400(api_client):
    """JSON object가 아닌 body → 400."""
    response = api_client.post(
        E2_ENDPOINT,
        data=json.dumps([1, 2, 3]),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_post_e2_invalid_provider_returns_400(api_client, e2_request_body):
    """미등록 provider query param → 400."""
    response = api_client.post(
        f"{E2_ENDPOINT}?provider=invalid_provider",
        data=e2_request_body,
        format="json",
    )
    assert response.status_code == 400
    assert "Invalid provider" in str(response.json())


# ============================================================
# Service 예외 (500, 502, 429)
# ============================================================


def test_post_e2_service_exception_returns_500_no_stacktrace(
    api_client, e2_request_body
):
    """run_e2_coach가 일반 예외 → 500 + 스택트레이스 노출 금지."""
    with patch(
        "portfolio.api.views.run_e2_coach",
        side_effect=RuntimeError("internal database error with secret /tmp/xyz"),
    ):
        response = api_client.post(
            E2_ENDPOINT, data=e2_request_body, format="json"
        )

    assert response.status_code == 500
    body_str = json.dumps(response.json())
    assert "secret" not in body_str
    assert "/tmp/xyz" not in body_str
    assert "Internal server error" in body_str


def test_post_e2_llm_budget_exceeded_returns_429(api_client, e2_request_body):
    """LLMBudgetExceededError → 429."""
    from portfolio.llm.exceptions import LLMBudgetExceededError

    with patch(
        "portfolio.api.views.run_e2_coach",
        side_effect=LLMBudgetExceededError(scope="slice", count=51, limit=50),
    ):
        response = api_client.post(
            E2_ENDPOINT, data=e2_request_body, format="json"
        )

    assert response.status_code == 429


def test_post_e2_llm_error_returns_502(api_client, e2_request_body):
    """기타 LLMError → 502."""
    from portfolio.llm.exceptions import LLMRateLimitError

    with patch(
        "portfolio.api.views.run_e2_coach",
        side_effect=LLMRateLimitError("upstream rate limit"),
    ):
        response = api_client.post(
            E2_ENDPOINT, data=e2_request_body, format="json"
        )

    assert response.status_code == 502


# ============================================================
# Schema drift 안전망
# ============================================================


def test_post_e2_service_returns_drifted_output_caught_by_serializer(
    api_client, e2_request_body, mock_llm_response_e2
):
    """★ service 응답이 E2Output 계약을 깨면 serializer가 잡아낸다."""
    drifted = dict(mock_llm_response_e2)
    drifted["output"] = dict(drifted["output"], confidence="unknown_value")
    with patch(
        "portfolio.api.views.run_e2_coach", return_value=drifted
    ):
        response = api_client.post(
            E2_ENDPOINT, data=e2_request_body, format="json"
        )
    assert response.status_code in (400, 500)
