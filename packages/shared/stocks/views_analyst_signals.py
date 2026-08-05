"""SFI-I-2 — 애널리스트 시그널 스냅샷 조회 API (read-only, D-I2-1 공용).

GET 최신 AnalystSignalSnapshot 1건(4신호 + grades_historical + captured_at).
미수집 = null 계약(available:false, 200 — advisory read 관례 정합, FE "미설정" 폴백 친화).
I-3(자체 시계열)도 이 엔드포인트를 기간 조회로 확장 재사용.
"""
import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AnalystSignalSnapshot
from .serializers import AnalystSignalSnapshotSerializer

logger = logging.getLogger(__name__)


class AnalystSignalSnapshotView(APIView):
    """GET /api/v1/stocks/api/analyst-signals/<symbol>/ — 최신 스냅샷 1건."""

    permission_classes = [IsAuthenticated]

    def get(self, request, symbol):
        symbol = symbol.upper()
        # append 테이블 → captured_at 내림차순 최신 1건(동시각 tie는 id로 안정 판별).
        snap = (
            AnalystSignalSnapshot.objects.filter(symbol=symbol)
            .order_by("-captured_at", "-id")
            .first()
        )
        if snap is None:
            return Response({"available": False, "symbol": symbol})
        return Response(AnalystSignalSnapshotSerializer(snap).data)
