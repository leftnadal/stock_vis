"""Slice 16 Step 0-B — #70 auth wall 단언 (AllowAny → IsAuthenticated).

배경: Slice 15 closing에서 등록된 #70 (PS 2.0) — Slice 13 Part 1~5에서 6 view
모두 audit P0 #5에 따라 명시적 `[AllowAny]` 채택되어 있었고, Slice 15 P3-C 실
호출에서 JWT 없이 그대로 호출되어 LLM 1콜 발생($0.0053248)이 실증됨. 비인증
클라이언트가 LLM 비용을 끌어다 쓸 위험.

본 테스트는 Step 0-B의 전환 결과를 회귀 가드:
  - 미인증 호출 → 401 (각 EP)
  - 인증된 호출은 conftest 공통 fixture가 책임 (test_e[1-6]_endpoint.py)
"""

from __future__ import annotations

import pytest

_COACH_ENDPOINTS = [
    "/api/v1/coach/e1/",
    "/api/v1/coach/e2/",
    "/api/v1/coach/e3/",
    "/api/v1/coach/e4/",
    "/api/v1/coach/e5/",
    "/api/v1/coach/e6/",
]


@pytest.mark.parametrize("endpoint", _COACH_ENDPOINTS)
def test_coach_endpoint_blocks_anonymous_post(anonymous_api_client, endpoint):
    """미인증 POST → 401 — LLM 호출 진입 전 차단."""
    response = anonymous_api_client.post(
        endpoint,
        data={"any": "payload"},
        format="json",
    )
    assert response.status_code == 401, (
        f"{endpoint} 미인증 호출은 401이어야 함 — 실제={response.status_code}. "
        "AllowAny 잔존 가능성, #70 회귀 신호."
    )


# CORS preflight(OPTIONS) 검증은 본 테스트 범위 밖.
# 실제 브라우저 preflight는 django-cors-headers middleware가 view permission 전
# 단계에서 응답하므로 401에 영향받지 않는다. APIClient.options()는 middleware
# 통과 후 view permission까지 거쳐 401을 받는데, 이는 실 호환성 신호가 아님.
# Slice 15 Step 0-C 베이스라인 검증으로 CORS preflight 200 + ACAO 헤더 명시 확인됨.
