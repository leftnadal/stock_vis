"""Slice 13 Part 1 — DRF coach API views.

설계 원칙 (지시서 §2):
  - 기존 `portfolio/views.py` 순수 Django view는 한 줄도 수정 금지.
  - 새 경로 `/api/coach/e1/` (POST)에 DRF endpoint 추가만 한다.
  - LLM service 호출 시 Step 0a kwarg(preset_id/metrics)는 Part 1에서 전달 안 함 — 기존 동작 동일.

에러 처리:
  - 검증 실패 → 400 (serializer 측에서 자동 발생)
  - service 예외 → 500 + 표준 에러 형식 (스택트레이스 노출 금지)
"""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from portfolio.api.serializers import E1RequestSerializer, E1ResponseSerializer
from portfolio.llm.exceptions import LLMBudgetExceededError, LLMError
from portfolio.services.coach.e1_service import run_e1_coach

logger = logging.getLogger(__name__)


_VALID_PROVIDERS = ("haiku", "sonnet", "anthropic")


@api_view(["POST"])
@permission_classes([AllowAny])  # 기존 순수 view 동작 미러 (audit P0 #5: 명시적 AllowAny)
def coach_e1(request: Request) -> Response:
    """POST /api/coach/e1/

    Body (JSON): `CommentaryInputE1` schema 필드 (portfolio_id, fetched_at,
    preset, holdings, garp_metrics 등).
    Query: provider=haiku (기본) | sonnet | anthropic.

    응답:
      - 200: `{output: E1Output, llm_metadata: {...}}`
      - 400: 요청 검증 실패 (Pydantic 에러 평탄화)
      - 500: service 예외 (스택트레이스 노출 금지)
    """
    provider = request.query_params.get("provider", "haiku")
    if provider not in _VALID_PROVIDERS:
        return Response(
            {"error": f"Invalid provider: {provider!r}. Must be one of {list(_VALID_PROVIDERS)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    req_serializer = E1RequestSerializer(data=request.data)
    req_serializer.is_valid(raise_exception=True)
    input_data = req_serializer.validated_data  # CommentaryInputE1 instance

    try:
        result = run_e1_coach(input_data, provider=provider)
    except LLMBudgetExceededError as exc:
        logger.warning("E1 endpoint LLM budget exceeded: %s", exc)
        return Response(
            {"error": "LLM budget exceeded", "scope": exc.scope},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    except LLMError as exc:
        logger.exception("E1 endpoint LLM error")
        return Response(
            {"error": "LLM call failed", "type": type(exc).__name__},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception:
        logger.exception("E1 endpoint unexpected error")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    resp_serializer = E1ResponseSerializer(result)
    return Response(resp_serializer.data, status=status.HTTP_200_OK)
