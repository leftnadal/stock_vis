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

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from portfolio.api.serializers import (
    E1RequestSerializer,
    E1ResponseSerializer,
    E2RequestSerializer,
    E2ResponseSerializer,
    E3RequestSerializer,
    E3ResponseSerializer,
    E4RequestSerializer,
    E4ResponseSerializer,
    E5RequestSerializer,
    E5ResponseSerializer,
    E6RequestSerializer,
    E6ResponseSerializer,
)
from portfolio.llm.exceptions import LLMBudgetExceededError, LLMError
from portfolio.services.coach.e1_service import run_e1_coach
from portfolio.services.coach.e2_service import run_e2_coach
from portfolio.services.coach.e3_service import run_e3_coach
from portfolio.services.coach.e4_service import run_e4_coach
from portfolio.services.coach.e5_service import run_e5_coach
from portfolio.services.coach.e6_service import run_e6_coach

logger = logging.getLogger(__name__)


_VALID_PROVIDERS = ("haiku", "sonnet", "anthropic")


@extend_schema(
    request=E1RequestSerializer,
    responses={200: E1ResponseSerializer},
    tags=["coach"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])  # Slice 16 Step 0-B #70: AllowAny → IsAuthenticated 전환
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


@extend_schema(
    request=E2RequestSerializer,
    responses={200: E2ResponseSerializer},
    tags=["coach"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])  # Slice 16 Step 0-B #70: 6 view 통일
def coach_e2(request: Request) -> Response:
    """POST /api/v1/coach/e2/

    Body: `CommentaryInputE2` schema 필드 (portfolio_id, fetched_at, preset,
    holdings, portfolio_return_1y, sector_allocation).
    Query: provider=haiku (기본) | sonnet | anthropic.

    응답: `{output: E2Output, llm_metadata: {...}}`
    Slice 13 Part 2 신규 — E1 view 동형.
    """
    provider = request.query_params.get("provider", "haiku")
    if provider not in _VALID_PROVIDERS:
        return Response(
            {"error": f"Invalid provider: {provider!r}. Must be one of {list(_VALID_PROVIDERS)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    req_serializer = E2RequestSerializer(data=request.data)
    req_serializer.is_valid(raise_exception=True)
    input_data = req_serializer.validated_data  # CommentaryInputE2 instance

    try:
        result = run_e2_coach(input_data, provider=provider)
    except LLMBudgetExceededError as exc:
        logger.warning("E2 endpoint LLM budget exceeded: %s", exc)
        return Response(
            {"error": "LLM budget exceeded", "scope": exc.scope},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    except LLMError as exc:
        logger.exception("E2 endpoint LLM error")
        return Response(
            {"error": "LLM call failed", "type": type(exc).__name__},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception:
        logger.exception("E2 endpoint unexpected error")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    resp_serializer = E2ResponseSerializer(result)
    return Response(resp_serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    request=E3RequestSerializer,
    responses={200: E3ResponseSerializer},
    tags=["coach"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])  # Slice 16 Step 0-B #70: 6 view 통일
def coach_e3(request: Request) -> Response:
    """POST /api/v1/coach/e3/

    Body: `CommentaryInputE3` schema 필드 (portfolio_id, fetched_at, preset,
    holdings, concentration_metrics).
    Query: provider=haiku (기본) | sonnet | anthropic.

    응답: `{output: E3Output, llm_metadata: {...}}`
    Slice 13 Part 3 신규 — E2 view 동형.

    ★ preset_id / metrics kwarg는 본 endpoint에서 노출하지 않는다 (#66 분리).
      → run_e3_coach 호출 시 기본값(None) 사용 — 기존 동작 유지.
    """
    provider = request.query_params.get("provider", "haiku")
    if provider not in _VALID_PROVIDERS:
        return Response(
            {"error": f"Invalid provider: {provider!r}. Must be one of {list(_VALID_PROVIDERS)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    req_serializer = E3RequestSerializer(data=request.data)
    req_serializer.is_valid(raise_exception=True)
    input_data = req_serializer.validated_data  # CommentaryInputE3 instance

    try:
        result = run_e3_coach(input_data, provider=provider)
    except LLMBudgetExceededError as exc:
        logger.warning("E3 endpoint LLM budget exceeded: %s", exc)
        return Response(
            {"error": "LLM budget exceeded", "scope": exc.scope},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    except LLMError as exc:
        logger.exception("E3 endpoint LLM error")
        return Response(
            {"error": "LLM call failed", "type": type(exc).__name__},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception:
        logger.exception("E3 endpoint unexpected error")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    resp_serializer = E3ResponseSerializer(result)
    return Response(resp_serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    request=E5RequestSerializer,
    responses={200: E5ResponseSerializer},
    tags=["coach"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])  # Slice 16 Step 0-B #70: 6 view 통일
def coach_e5(request: Request) -> Response:
    """POST /api/v1/coach/e5/

    Body: `CommentaryInputE5` schema 필드 (portfolio_id, fetched_at, preset,
    holdings, extraction_targets, time_series_context?).
    Query: provider=haiku (기본) | sonnet | anthropic.

    Slice 13 Part 4 신규 — E3 view 동형. preset_id/metrics kwarg 미전달.
    """
    provider = request.query_params.get("provider", "haiku")
    if provider not in _VALID_PROVIDERS:
        return Response(
            {"error": f"Invalid provider: {provider!r}. Must be one of {list(_VALID_PROVIDERS)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    req_serializer = E5RequestSerializer(data=request.data)
    req_serializer.is_valid(raise_exception=True)
    input_data = req_serializer.validated_data  # CommentaryInputE5 instance

    try:
        result = run_e5_coach(input_data, provider=provider)
    except LLMBudgetExceededError as exc:
        logger.warning("E5 endpoint LLM budget exceeded: %s", exc)
        return Response(
            {"error": "LLM budget exceeded", "scope": exc.scope},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    except LLMError as exc:
        logger.exception("E5 endpoint LLM error")
        return Response(
            {"error": "LLM call failed", "type": type(exc).__name__},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception:
        logger.exception("E5 endpoint unexpected error")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    resp_serializer = E5ResponseSerializer(result)
    return Response(resp_serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    request=E6RequestSerializer,
    responses={200: E6ResponseSerializer},
    tags=["coach"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])  # Slice 16 Step 0-B #70: 6 view 통일
def coach_e6(request: Request) -> Response:
    """POST /api/v1/coach/e6/

    Body: `CommentaryInputE6` schema 필드 (portfolio_id, fetched_at, preset,
    holdings, analysis_results).
    Query: provider=haiku (기본) | sonnet | anthropic.

    Slice 13 Part 4 신규 — E3 view 동형. preset_id/metrics kwarg 미전달.
    """
    provider = request.query_params.get("provider", "haiku")
    if provider not in _VALID_PROVIDERS:
        return Response(
            {"error": f"Invalid provider: {provider!r}. Must be one of {list(_VALID_PROVIDERS)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    req_serializer = E6RequestSerializer(data=request.data)
    req_serializer.is_valid(raise_exception=True)
    input_data = req_serializer.validated_data  # CommentaryInputE6 instance

    try:
        result = run_e6_coach(input_data, provider=provider)
    except LLMBudgetExceededError as exc:
        logger.warning("E6 endpoint LLM budget exceeded: %s", exc)
        return Response(
            {"error": "LLM budget exceeded", "scope": exc.scope},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    except LLMError as exc:
        logger.exception("E6 endpoint LLM error")
        return Response(
            {"error": "LLM call failed", "type": type(exc).__name__},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception:
        logger.exception("E6 endpoint unexpected error")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    resp_serializer = E6ResponseSerializer(result)
    return Response(resp_serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    request=E4RequestSerializer,
    responses={200: E4ResponseSerializer},
    tags=["coach"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])  # Slice 16 Step 0-B #70: 6 view 통일
def coach_e4(request: Request) -> Response:
    """POST /api/v1/coach/e4/

    Body: `CommentaryInputE4` schema 필드 (portfolio_id, fetched_at, preset,
    holdings, user_question, conversation_history).
    Query: provider=haiku (기본) | sonnet | anthropic.

    Slice 13 Part 5 신규 — 마지막 진입점, 다른 endpoint 동형.
    ★ run_e4_coach는 preset_id/metrics kwarg를 받지 않음 → 전달하지 않는다.
    """
    provider = request.query_params.get("provider", "haiku")
    if provider not in _VALID_PROVIDERS:
        return Response(
            {"error": f"Invalid provider: {provider!r}. Must be one of {list(_VALID_PROVIDERS)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    req_serializer = E4RequestSerializer(data=request.data)
    req_serializer.is_valid(raise_exception=True)
    input_data = req_serializer.validated_data  # CommentaryInputE4 instance

    try:
        result = run_e4_coach(input_data, provider=provider)
    except LLMBudgetExceededError as exc:
        logger.warning("E4 endpoint LLM budget exceeded: %s", exc)
        return Response(
            {"error": "LLM budget exceeded", "scope": exc.scope},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    except LLMError as exc:
        logger.exception("E4 endpoint LLM error")
        return Response(
            {"error": "LLM call failed", "type": type(exc).__name__},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception:
        logger.exception("E4 endpoint unexpected error")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    resp_serializer = E4ResponseSerializer(result)
    return Response(resp_serializer.data, status=status.HTTP_200_OK)
