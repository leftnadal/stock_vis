"""
이벤트 보드 / 랭킹 API (CS-RD2).

새 파일 — 기존 api/views.py 절대 수정 금지.
권한·스로틀: 기존 views.py 와 동일하게 DRF 기본값 사용(미지정).
"""

import logging
from datetime import date

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chain_sight.models import StockAttentionScore
from apps.chain_sight.serializers.event_board import (
    EventBoardItemSerializer,
    EventRankingItemSerializer,
)
from apps.chain_sight.services.attention_service import (
    get_event_board,
    get_event_ranking,
)

logger = logging.getLogger(__name__)


def _latest_attention_date() -> date | None:
    """StockAttentionScore에 저장된 가장 최신 날짜 반환."""
    from django.db.models import Max

    result = StockAttentionScore.objects.aggregate(max_date=Max("date"))
    return result.get("max_date")


def _parse_date(date_str: str) -> date | None:
    """쿼리 파라미터 date 문자열 파싱. 실패 시 None."""
    try:
        return date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return None


@extend_schema(
    tags=["Chain Sight"],
    parameters=[
        OpenApiParameter(
            name="date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="조회 날짜 (YYYY-MM-DD). 기본값: 최신 스냅샷 날짜.",
            required=False,
        )
    ],
    responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
)
class EventBoardView(APIView):
    """
    GET /api/v1/chainsight/events/

    theme_tags 기반 이벤트 그룹 목록 (평균 관심도 내림차순).
    멤버 < 3 그룹 제외.
    """

    def get(self, request):
        date_param = request.query_params.get("date")
        target_date = _parse_date(date_param) if date_param else _latest_attention_date()

        if not target_date:
            return Response(
                {"error": "관심도 데이터가 없습니다. compute_attention_scores를 먼저 실행하세요."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 지정된 날짜에 데이터 있는지 확인
        if not StockAttentionScore.objects.filter(date=target_date).exists():
            return Response(
                {"error": f"{target_date} 날짜의 관심도 데이터가 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        board = get_event_board(target_date)
        serializer = EventBoardItemSerializer(board, many=True)
        return Response(
            {
                "date": str(target_date),
                "count": len(board),
                "events": serializer.data,
            }
        )


@extend_schema(
    tags=["Chain Sight"],
    parameters=[
        OpenApiParameter(
            name="date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="조회 날짜 (YYYY-MM-DD). 기본값: 최신 스냅샷 날짜.",
            required=False,
        )
    ],
    responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
)
class EventRankingView(APIView):
    """
    GET /api/v1/chainsight/events/<theme>/stocks/

    테마 소속 종목 score 내림차순 랭킹.
    없는 테마: 404.
    """

    def get(self, request, theme: str):
        date_param = request.query_params.get("date")
        target_date = _parse_date(date_param) if date_param else _latest_attention_date()

        if not target_date:
            return Response(
                {"error": "관심도 데이터가 없습니다. compute_attention_scores를 먼저 실행하세요."},
                status=status.HTTP_404_NOT_FOUND,
            )

        ranking = get_event_ranking(theme, target_date)

        if not ranking:
            return Response(
                {"error": f"테마 '{theme}'에 해당하는 종목이 없거나 관심도 데이터가 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EventRankingItemSerializer(ranking, many=True)
        return Response(
            {
                "theme": theme,
                "date": str(target_date),
                "count": len(ranking),
                "stocks": serializer.data,
            }
        )
