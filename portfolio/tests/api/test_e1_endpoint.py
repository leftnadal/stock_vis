"""Slice 13 Part 1 — POST /api/v1/coach/e1/ contract test (Part 1.5 v1 도입).

핵심 검증:
  - 정상 요청 → 200 + E1Output 스키마 부합
  - 필수 필드 누락 → 400 (Pydantic 에러 평탄화)
  - service 예외 → 500 + 스택트레이스 노출 없음
  - LLM은 mock (Part 1 real 호출 0)

★ contract test 본질: API 응답이 OutputBase/E1Output 계약을 지키는가 — 회귀 보호.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from portfolio.schemas.llm import LLMResponse
from portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_raw


# Slice 13 Part 1.5: v1 버전 세그먼트 도입. 향후 경로 변경 시 본 상수만 갱신.
E1_ENDPOINT = "/api/v1/coach/e1/"


# Slice 16 Step 0-B #70: api_client fixture는 conftest.py로 이전 — IsAuthenticated 통과.
@pytest.fixture
def e1_request_body() -> dict:
    """portfolio_a2 fixture에서 E1 요청 body 추출 (base + specific 평탄화)."""
    fixture = load_portfolio_a2_raw()
    return {
        "portfolio_id": fixture["portfolio_id"],
        "fetched_at": fixture["fetched_at"],
        "preset": fixture["preset"],
        "holdings": fixture["holdings"],
        **fixture["inputs"]["e1"],  # garp_metrics 등 E1-specific
    }


@pytest.fixture
def mock_llm_response_e1():
    """run_e1_coach가 반환할 mock 결과 dict (E1Output 계약 부합)."""
    return {
        "output": {
            "summary": "포트폴리오 GARP 진단: 평균 합리적 밸류에이션.",
            "key_observations": [
                "전체 PEG 중앙값 1.3 — GARP 임계 1.5 이하",
                "성장 종목 비중 60%",
            ],
            "confidence": "medium",
            "action_items": [],
            "risk_flags": [],
            "metrics_table": "",
        },
        "llm_metadata": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "latency_ms": 1234,
            "input_tokens": 800,
            "output_tokens": 200,
            "cost_usd": 0.0014,
            "fallback_from": None,
        },
    }


# ============================================================
# 정상 경로
# ============================================================


def test_post_e1_returns_200_with_valid_request(
    api_client, e1_request_body, mock_llm_response_e1
):
    """POST /api/v1/coach/e1/ 정상 요청 → 200 + E1Output 계약 부합."""
    with patch(
        "portfolio.api.views.run_e1_coach", return_value=mock_llm_response_e1
    ) as mock_run:
        response = api_client.post(
            E1_ENDPOINT, data=e1_request_body, format="json"
        )

    assert response.status_code == 200, response.data
    # service 1회만 호출됨 (mock)
    assert mock_run.call_count == 1

    # 응답 계약 검증
    data = response.json()
    assert "output" in data
    assert "llm_metadata" in data
    # E1Output 필수 필드 (CommentaryOutputBase 기반)
    output = data["output"]
    assert isinstance(output["summary"], str) and output["summary"]
    assert isinstance(output["key_observations"], list)
    assert output["confidence"] in ("high", "medium", "low")
    # E1 특화 필드
    assert "action_items" in output
    assert "risk_flags" in output


def test_post_e1_response_passes_e1output_validation(
    api_client, e1_request_body, mock_llm_response_e1
):
    """★ contract test 핵심 — 응답 dict가 다시 E1Output(Pydantic)으로 검증 가능."""
    from portfolio.schemas.commentary_output import E1Output

    with patch(
        "portfolio.api.views.run_e1_coach", return_value=mock_llm_response_e1
    ):
        response = api_client.post(
            E1_ENDPOINT, data=e1_request_body, format="json"
        )

    # 응답 output을 E1Output으로 역검증 — 계약 보장
    output_dict = response.json()["output"]
    revalidated = E1Output(**output_dict)
    assert revalidated.summary == mock_llm_response_e1["output"]["summary"]


# ============================================================
# 검증 실패 (400)
# ============================================================


def test_post_e1_missing_required_field_returns_400(api_client, e1_request_body):
    """필수 필드 (`garp_metrics`) 누락 → 400."""
    body = dict(e1_request_body)
    del body["garp_metrics"]
    response = api_client.post(E1_ENDPOINT, data=body, format="json")
    assert response.status_code == 400
    # Pydantic 에러가 응답에 포함되어야 함
    data = response.json()
    assert any("garp_metrics" in k for k in data) or "garp_metrics" in str(data)


def test_post_e1_invalid_type_returns_400(api_client, e1_request_body):
    """잘못된 타입 (holdings를 str으로) → 400."""
    body = dict(e1_request_body)
    body["holdings"] = "not_a_list"
    response = api_client.post(E1_ENDPOINT, data=body, format="json")
    assert response.status_code == 400


def test_post_e1_non_dict_body_returns_400(api_client):
    """JSON object가 아닌 body → 400."""
    response = api_client.post(
        E1_ENDPOINT,
        data=json.dumps([1, 2, 3]),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_post_e1_invalid_provider_returns_400(api_client, e1_request_body):
    """미등록 provider query param → 400."""
    response = api_client.post(
        f"{E1_ENDPOINT}?provider=invalid_provider",
        data=e1_request_body,
        format="json",
    )
    assert response.status_code == 400
    assert "Invalid provider" in str(response.json())


# ============================================================
# Service 예외 (500, 502, 429)
# ============================================================


def test_post_e1_service_exception_returns_500_no_stacktrace(
    api_client, e1_request_body
):
    """run_e1_coach가 일반 예외 → 500 + 스택트레이스 노출 금지."""
    with patch(
        "portfolio.api.views.run_e1_coach",
        side_effect=RuntimeError("internal database error with secret /tmp/abc"),
    ):
        response = api_client.post(
            E1_ENDPOINT, data=e1_request_body, format="json"
        )

    assert response.status_code == 500
    body_str = json.dumps(response.json())
    # 내부 에러 메시지가 응답에 노출되면 안 됨
    assert "secret" not in body_str
    assert "/tmp/abc" not in body_str
    assert "Internal server error" in body_str


def test_post_e1_llm_budget_exceeded_returns_429(api_client, e1_request_body):
    """LLMBudgetExceededError → 429."""
    from portfolio.llm.exceptions import LLMBudgetExceededError

    with patch(
        "portfolio.api.views.run_e1_coach",
        side_effect=LLMBudgetExceededError(scope="slice", count=51, limit=50),
    ):
        response = api_client.post(
            E1_ENDPOINT, data=e1_request_body, format="json"
        )

    assert response.status_code == 429


def test_post_e1_llm_error_returns_502(api_client, e1_request_body):
    """기타 LLMError → 502."""
    from portfolio.llm.exceptions import LLMRateLimitError

    with patch(
        "portfolio.api.views.run_e1_coach",
        side_effect=LLMRateLimitError("upstream rate limit"),
    ):
        response = api_client.post(
            E1_ENDPOINT, data=e1_request_body, format="json"
        )

    assert response.status_code == 502


# ============================================================
# Schema drift 안전망
# ============================================================


def test_post_e1_service_returns_drifted_output_caught_by_serializer(
    api_client, e1_request_body, mock_llm_response_e1
):
    """★ service 응답이 E1Output 계약을 깨면 serializer가 잡아낸다.

    예: confidence 필드를 알 수 없는 값으로 변형 → 500 + 계약 위반 신호.
    """
    drifted = dict(mock_llm_response_e1)
    drifted["output"] = dict(drifted["output"], confidence="unknown_value")
    with patch(
        "portfolio.api.views.run_e1_coach", return_value=drifted
    ):
        response = api_client.post(
            E1_ENDPOINT, data=e1_request_body, format="json"
        )
    # serializer to_representation은 view 응답 단계에서 raise → DRF가 500 변환
    assert response.status_code in (400, 500)
