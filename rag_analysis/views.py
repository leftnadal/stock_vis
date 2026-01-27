import logging
import json
import uuid
import asyncio
from datetime import datetime
from typing import Generator

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import StreamingHttpResponse
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.renderers import BaseRenderer

from .models import DataBasket, BasketItem, AnalysisSession, AnalysisMessage
from .serializers import (
    DataBasketSerializer,
    BasketItemSerializer,
    AnalysisSessionSerializer,
    AnalysisMessageSerializer,
)

logger = logging.getLogger(__name__)


# ============ Helper Functions ============

def create_success_response(data, meta=None):
    """성공 응답 생성"""
    response = {
        "success": True,
        "data": data,
        "meta": meta or {
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }
    }
    return response


def create_error_response(code, message, meta=None):
    """에러 응답 생성"""
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        },
        "meta": meta or {
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }
    }
    return response


# ============ DataBasket Views ============

class DataBasketListCreateView(APIView):
    """
    GET: 사용자의 DataBasket 목록 조회
    POST: 새로운 DataBasket 생성
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """사용자의 DataBasket 목록 조회"""
        baskets = DataBasket.objects.filter(user=request.user).prefetch_related('items')
        serializer = DataBasketSerializer(baskets, many=True)
        return Response(create_success_response(serializer.data))

    def post(self, request):
        """새로운 DataBasket 생성"""
        serializer = DataBasketSerializer(data=request.data)
        if serializer.is_valid():
            basket = serializer.save(user=request.user)
            return Response(
                create_success_response(DataBasketSerializer(basket).data),
                status=status.HTTP_201_CREATED
            )
        return Response(
            create_error_response("INVALID_INPUT", str(serializer.errors)),
            status=status.HTTP_400_BAD_REQUEST
        )


class DataBasketDetailView(APIView):
    """
    GET: DataBasket 상세 조회
    PATCH: DataBasket 수정
    DELETE: DataBasket 삭제
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        """DataBasket 객체 가져오기"""
        try:
            return DataBasket.objects.prefetch_related('items').get(pk=pk, user=user)
        except DataBasket.DoesNotExist:
            raise NotFound(_("DataBasket not found"))

    def get(self, request, pk):
        """DataBasket 상세 조회"""
        basket = self.get_object(pk, request.user)
        serializer = DataBasketSerializer(basket)
        return Response(create_success_response(serializer.data))

    def patch(self, request, pk):
        """DataBasket 수정"""
        basket = self.get_object(pk, request.user)
        serializer = DataBasketSerializer(basket, data=request.data, partial=True)
        if serializer.is_valid():
            basket = serializer.save()
            return Response(create_success_response(DataBasketSerializer(basket).data))
        return Response(
            create_error_response("INVALID_INPUT", str(serializer.errors)),
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        """DataBasket 삭제"""
        basket = self.get_object(pk, request.user)
        basket.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DataBasketAddItemView(APIView):
    """
    POST: DataBasket에 아이템 추가
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """DataBasket에 아이템 추가 (트랜잭션 보호)"""
        with transaction.atomic():
            # DataBasket 확인 및 락 획득
            try:
                basket = DataBasket.objects.select_for_update().get(pk=pk, user=request.user)
            except DataBasket.DoesNotExist:
                raise NotFound(_("DataBasket not found"))

            # 아이템 개수 제한 확인
            if not basket.can_add_item():
                return Response(
                    create_error_response(
                        "BASKET_FULL",
                        f"바구니에는 최대 {DataBasket.MAX_ITEMS}개의 아이템만 담을 수 있습니다."
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 아이템 생성
            serializer = BasketItemSerializer(data=request.data)
            if serializer.is_valid():
                try:
                    item = serializer.save(basket=basket)
                    return Response(
                        create_success_response(BasketItemSerializer(item).data),
                        status=status.HTTP_201_CREATED
                    )
                except Exception as e:
                    # unique_together 제약 위반 (중복 아이템)
                    if "unique" in str(e).lower():
                        return Response(
                            create_error_response(
                                "DUPLICATE_ITEM",
                                "해당 아이템이 이미 바구니에 담겨 있습니다."
                            ),
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    raise

            return Response(
                create_error_response("INVALID_INPUT", str(serializer.errors)),
                status=status.HTTP_400_BAD_REQUEST
            )


class DataBasketRemoveItemView(APIView):
    """
    DELETE: DataBasket에서 아이템 제거
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, item_id):
        """DataBasket에서 아이템 제거"""
        # DataBasket 확인
        try:
            basket = DataBasket.objects.get(pk=pk, user=request.user)
        except DataBasket.DoesNotExist:
            raise NotFound(_("DataBasket not found"))

        # BasketItem 확인 및 삭제
        try:
            item = BasketItem.objects.get(pk=item_id, basket=basket)
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except BasketItem.DoesNotExist:
            raise NotFound(_("Item not found in this basket"))


class DataBasketClearView(APIView):
    """
    DELETE: DataBasket 비우기 (모든 아이템 삭제)
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        """DataBasket의 모든 아이템 삭제"""
        # DataBasket 확인
        try:
            basket = DataBasket.objects.get(pk=pk, user=request.user)
        except DataBasket.DoesNotExist:
            raise NotFound(_("DataBasket not found"))

        # 모든 아이템 삭제
        deleted_count = basket.items.all().delete()[0]

        return Response(
            create_success_response({
                "message": f"{deleted_count}개의 아이템이 삭제되었습니다.",
                "deleted_count": deleted_count
            })
        )


class DataBasketAddStockDataView(APIView):
    """
    POST: DataBasket에 주식 데이터 추가 (데이터 타입 선택)

    Request Body:
        {
            "symbol": "AAPL",
            "data_types": ["overview", "price", "financial_summary"]
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """주식 데이터를 선택한 타입에 따라 바구니에 추가"""
        from .constants import DATA_UNITS, DEFAULT_DATA_UNITS
        from datetime import date

        with transaction.atomic():
            # DataBasket 확인 및 락 획득
            try:
                basket = DataBasket.objects.select_for_update().get(pk=pk, user=request.user)
            except DataBasket.DoesNotExist:
                raise NotFound(_("DataBasket not found"))

            # 요청 데이터 검증
            symbol = request.data.get('symbol', '').upper().strip()
            data_types = request.data.get('data_types', [])

            if not symbol:
                return Response(
                    create_error_response("INVALID_INPUT", "종목 심볼을 입력해주세요."),
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not data_types or not isinstance(data_types, list):
                return Response(
                    create_error_response("INVALID_INPUT", "데이터 타입을 선택해주세요."),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 총 필요 용량 계산
            total_units = sum(DATA_UNITS.get(dt, DEFAULT_DATA_UNITS) for dt in data_types)

            # 용량 체크
            if not basket.can_add_units(total_units):
                return Response(
                    create_error_response(
                        "CAPACITY_EXCEEDED",
                        f"바구니 용량이 부족합니다. 필요: {total_units}u, 남은 용량: {basket.remaining_units}u"
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 주식 정보 조회 (stocks 앱에서)
            stock_name = self._get_stock_name(symbol)

            # 각 데이터 타입별로 아이템 생성
            created_items = []
            today = date.today()

            for data_type in data_types:
                units = DATA_UNITS.get(data_type, DEFAULT_DATA_UNITS)

                # 데이터 스냅샷 생성
                data_snapshot = self._get_data_snapshot(symbol, data_type)

                # 타입별 제목 생성
                type_labels = {
                    'overview': '기본 정보',
                    'price': '주가 데이터',
                    'financial_summary': '재무제표 (요약)',
                    'financial_full': '재무제표 (전체)',
                    'indicator': '기술적 지표',
                    'news': '뉴스',
                    'macro': '거시경제',
                }

                title = f"{symbol} {type_labels.get(data_type, data_type)}"

                # 중복 체크 (같은 심볼+타입 조합)
                existing = BasketItem.objects.filter(
                    basket=basket,
                    reference_id=symbol,
                    item_type=data_type
                ).first()

                if existing:
                    # 기존 아이템 업데이트
                    existing.data_snapshot = data_snapshot
                    existing.snapshot_date = today
                    existing.save()
                    created_items.append(existing)
                else:
                    # 새 아이템 생성
                    item = BasketItem.objects.create(
                        basket=basket,
                        item_type=data_type,
                        reference_id=symbol,
                        title=title,
                        subtitle=stock_name,
                        data_snapshot=data_snapshot,
                        snapshot_date=today,
                        data_units=units
                    )
                    created_items.append(item)

            return Response(
                create_success_response({
                    "message": f"{symbol} 데이터가 바구니에 추가되었습니다.",
                    "items": BasketItemSerializer(created_items, many=True).data,
                    "total_units_added": total_units,
                    "basket_current_units": basket.current_units,
                    "basket_remaining_units": basket.remaining_units
                }),
                status=status.HTTP_201_CREATED
            )

    def _get_stock_name(self, symbol: str) -> str:
        """주식 이름 조회"""
        try:
            from stocks.models import Stock
            stock = Stock.objects.filter(symbol=symbol).first()
            return stock.stock_name if stock and stock.stock_name else symbol
        except Exception:
            return symbol

    def _get_data_snapshot(self, symbol: str, data_type: str) -> dict:
        """데이터 타입별 스냅샷 생성"""
        snapshot = {'symbol': symbol, 'data_type': data_type}

        try:
            if data_type == 'overview':
                from stocks.models import Stock
                stock = Stock.objects.filter(symbol=symbol).first()
                if stock:
                    snapshot.update({
                        'name': stock.stock_name or symbol,
                        'sector': stock.sector or '',
                        'industry': stock.industry or '',
                        'market_cap': float(stock.market_capitalization) if stock.market_capitalization else None,
                        'description': (stock.description or '')[:500],
                    })

            elif data_type == 'price':
                from stocks.models import DailyPrice
                latest = DailyPrice.objects.filter(stock__symbol=symbol).order_by('-date').first()
                if latest:
                    snapshot.update({
                        'price': float(latest.close),
                        'open': float(latest.open),
                        'high': float(latest.high),
                        'low': float(latest.low),
                        'volume': latest.volume,
                        'date': str(latest.date),
                    })

            elif data_type in ('financial_summary', 'financial_full'):
                from stocks.models import IncomeStatement, BalanceSheet
                income = IncomeStatement.objects.filter(
                    stock__symbol=symbol, period_type='annual'
                ).order_by('-fiscal_year').first()
                balance = BalanceSheet.objects.filter(
                    stock__symbol=symbol, period_type='annual'
                ).order_by('-fiscal_year').first()

                if income:
                    snapshot.update({
                        'revenue': float(income.total_revenue) if income.total_revenue else None,
                        'net_income': float(income.net_income) if income.net_income else None,
                        'fiscal_year': income.fiscal_year,
                    })
                if balance:
                    snapshot.update({
                        'total_assets': float(balance.total_assets) if balance.total_assets else None,
                        'total_liabilities': float(balance.total_liabilities) if balance.total_liabilities else None,
                    })

            elif data_type == 'indicator':
                # 기술적 지표는 별도 계산 필요 - 기본값 제공
                snapshot.update({
                    'note': '기술적 지표 데이터 (RSI, MACD 등)',
                })

        except Exception as e:
            logger.warning(f"Failed to fetch {data_type} data for {symbol}: {e}")
            snapshot['error'] = str(e)

        return snapshot


# ============ AnalysisSession Views ============

class AnalysisSessionListCreateView(APIView):
    """
    GET: 사용자의 AnalysisSession 목록 조회
    POST: 새로운 AnalysisSession 생성
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """사용자의 AnalysisSession 목록 조회"""
        sessions = AnalysisSession.objects.filter(user=request.user).prefetch_related('messages')
        serializer = AnalysisSessionSerializer(sessions, many=True)
        return Response(create_success_response(serializer.data))

    def post(self, request):
        """새로운 AnalysisSession 생성"""
        serializer = AnalysisSessionSerializer(data=request.data)
        if serializer.is_valid():
            # basket_id 검증 (해당 사용자의 basket인지 확인)
            basket = serializer.validated_data.get('basket')
            if basket and basket.user != request.user:
                return Response(
                    create_error_response(
                        "INVALID_INPUT",
                        "해당 DataBasket에 접근할 수 없습니다."
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )

            session = serializer.save(user=request.user)
            return Response(
                create_success_response(AnalysisSessionSerializer(session).data),
                status=status.HTTP_201_CREATED
            )
        return Response(
            create_error_response("INVALID_INPUT", str(serializer.errors)),
            status=status.HTTP_400_BAD_REQUEST
        )


class AnalysisSessionDetailView(APIView):
    """
    GET: AnalysisSession 상세 조회
    DELETE: AnalysisSession 삭제
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        """AnalysisSession 객체 가져오기"""
        try:
            return AnalysisSession.objects.prefetch_related('messages').get(pk=pk, user=user)
        except AnalysisSession.DoesNotExist:
            raise NotFound(_("AnalysisSession not found"))

    def get(self, request, pk):
        """AnalysisSession 상세 조회"""
        session = self.get_object(pk, request.user)
        serializer = AnalysisSessionSerializer(session)
        return Response(create_success_response(serializer.data))

    def delete(self, request, pk):
        """AnalysisSession 삭제"""
        session = self.get_object(pk, request.user)
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionMessagesView(APIView):
    """
    GET: AnalysisSession의 메시지 목록 조회
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """세션의 메시지 목록 조회"""
        try:
            session = AnalysisSession.objects.get(pk=pk, user=request.user)
        except AnalysisSession.DoesNotExist:
            raise NotFound(_("AnalysisSession not found"))

        messages = session.messages.all().order_by('created_at')
        serializer = AnalysisMessageSerializer(messages, many=True)
        return Response(create_success_response(serializer.data))


class EventStreamRenderer(BaseRenderer):
    """SSE 스트리밍을 위한 커스텀 렌더러"""
    media_type = 'text/event-stream'
    format = 'txt'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


from django.http import StreamingHttpResponse as DjangoStreamingHttpResponse
from asgiref.sync import async_to_sync


class ChatStreamView(APIView):
    """
    POST: SSE 스트리밍 채팅 엔드포인트

    Query Parameters:
        - pipeline: 파이프라인 버전 ('lite', 'v2', 'final', 기본값: 'lite')
            - lite: 기존 바구니 기반
            - v2: RAG 기반 (Entity Extraction + Hybrid Search + Reranking + Compression)
            - final: Phase 3 최적화 통합 (Semantic Cache + Complexity + Token Budget + Adaptive LLM)

    Note:
        - ASGI 환경에서 async_to_sync 사용하여 안전하게 비동기 코드 실행
        - asyncio.new_event_loop() 대신 asgiref 사용으로 이벤트 루프 충돌 방지
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [EventStreamRenderer]

    def post(self, request, pk):
        """SSE 스트리밍으로 LLM 응답 전송"""
        # Session 확인
        try:
            session = AnalysisSession.objects.select_related('basket').get(
                pk=pk, user=request.user
            )
        except AnalysisSession.DoesNotExist:
            return Response(
                create_error_response("SESSION_NOT_FOUND", "세션을 찾을 수 없습니다."),
                status=status.HTTP_404_NOT_FOUND
            )

        # 메시지 검증
        message = request.data.get('message', '').strip()
        if not message:
            return Response(
                create_error_response("INVALID_INPUT", "질문을 입력해주세요."),
                status=status.HTTP_400_BAD_REQUEST
            )

        # 파이프라인 버전 선택
        pipeline_version = request.query_params.get('pipeline', 'lite').lower()

        # async_to_sync를 사용하여 비동기 파이프라인 실행
        async def run_pipeline():
            """비동기 파이프라인 실행"""
            if pipeline_version == 'v2':
                # PipelineV2: RAG 기반
                from .services.pipeline_v2 import AnalysisPipelineV2
                pipeline = AnalysisPipelineV2(session)
                logger.info(f"Using PipelineV2 (RAG) for session {session.id}")
            elif pipeline_version == 'final':
                # PipelineFinal: 모든 최적화 통합 (Phase 3)
                from .services.pipeline import AnalysisPipelineFinal
                pipeline = AnalysisPipelineFinal(session)
                logger.info(f"Using PipelineFinal (Optimized) for session {session.id}")
            else:
                # PipelineLite: 기존 바구니 기반
                from .services.pipeline import AnalysisPipelineLite
                pipeline = AnalysisPipelineLite(session)
                logger.info(f"Using PipelineLite (Basket) for session {session.id}")

            events = []
            try:
                async for event in pipeline.analyze(message):
                    events.append(event)
            except Exception as e:
                logger.error(f"Pipeline error: {e}", exc_info=True)
                events.append({
                    'phase': 'error',
                    'error': {'code': 'PIPELINE_ERROR', 'message': str(e)}
                })
            return events

        # async_to_sync로 안전하게 비동기 코드 실행 (Daphne 이벤트 루프와 호환)
        try:
            events = async_to_sync(run_pipeline)()
        except Exception as e:
            logger.error(f"Pipeline execution error: {e}", exc_info=True)
            events = [{
                'phase': 'error',
                'error': {'code': 'STREAM_ERROR', 'message': str(e)}
            }]

        # 파이프라인 성공 시 바구니 비우기 (Lite 모드만)
        has_error = any(e.get('phase') == 'error' for e in events)
        basket_cleared = False
        if pipeline_version == 'lite' and not has_error and session.basket:
            # 바구니에 아이템이 있었을 때만 비우기
            items_count = session.basket.items.count()
            if items_count > 0:
                session.basket.items.all().delete()
                basket_cleared = True
                logger.info(f"Basket {session.basket.id} cleared after successful analysis ({items_count} items)")

        # 동기 제너레이터로 이벤트들을 SSE 형식으로 yield
        def event_generator():
            for event in events:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            # 바구니가 비워졌으면 추가 이벤트 전송
            if basket_cleared:
                yield f"data: {json.dumps({'phase': 'basket_cleared', 'message': '바구니가 비워졌습니다.'}, ensure_ascii=False)}\n\n"

        # StreamingHttpResponse 반환
        response = DjangoStreamingHttpResponse(
            event_generator(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        response['Connection'] = 'keep-alive'
        return response


# ============ Monitoring Views ============

class UsageStatsView(APIView):
    """
    GET: 사용량 통계 조회

    Query Parameters:
        - hours: 조회 기간 (시간, 기본값: 24)
        - user_only: 본인 데이터만 조회 (기본값: true)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """사용량 통계 조회"""
        hours = int(request.query_params.get('hours', 24))
        user_only = request.query_params.get('user_only', 'true').lower() == 'true'

        try:
            from .models import UsageLog

            if user_only:
                stats = UsageLog.get_usage_stats(request.user, hours)
            else:
                # 관리자만 전체 통계 조회 가능
                if not request.user.is_staff:
                    return Response(
                        create_error_response(
                            "PERMISSION_DENIED",
                            "전체 통계 조회 권한이 없습니다."
                        ),
                        status=status.HTTP_403_FORBIDDEN
                    )
                stats = UsageLog.get_usage_stats(None, hours)

            return Response(create_success_response(stats))

        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return Response(
                create_error_response("STATS_ERROR", str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CostSummaryView(APIView):
    """
    GET: 비용 요약 조회 (일일/월간)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """비용 요약 조회"""
        try:
            from .models import UsageLog
            from django.utils import timezone

            now = timezone.now()

            # 일일 비용
            daily_cost = UsageLog.get_user_daily_cost(request.user)

            # 월간 비용
            monthly_cost = UsageLog.get_user_monthly_cost(request.user)

            # 캐시 히트율
            cache_hit_rate = UsageLog.get_cache_hit_rate(hours=24)

            # 예산 정보
            from .services.cost_tracker import get_cost_tracker
            tracker = get_cost_tracker()

            return Response(create_success_response({
                'daily': {
                    'cost_usd': daily_cost,
                    'limit_usd': tracker.daily_limit,
                    'remaining_usd': max(0, tracker.daily_limit - daily_cost),
                    'usage_percent': (daily_cost / tracker.daily_limit * 100) if tracker.daily_limit > 0 else 0
                },
                'monthly': {
                    'cost_usd': monthly_cost,
                    'limit_usd': tracker.monthly_limit,
                    'remaining_usd': max(0, tracker.monthly_limit - monthly_cost),
                    'usage_percent': (monthly_cost / tracker.monthly_limit * 100) if tracker.monthly_limit > 0 else 0,
                    'year': now.year,
                    'month': now.month
                },
                'cache': {
                    'hit_rate_24h': cache_hit_rate,
                    'hit_rate_percent': cache_hit_rate * 100
                }
            }))

        except Exception as e:
            logger.error(f"Failed to get cost summary: {e}")
            return Response(
                create_error_response("COST_ERROR", str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CacheStatsView(APIView):
    """
    GET: 시맨틱 캐시 통계 조회
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """캐시 통계 조회"""
        try:
            from .services.semantic_cache_setup import get_cache_stats

            stats = get_cache_stats()

            return Response(create_success_response(stats))

        except ImportError:
            return Response(
                create_error_response(
                    "CACHE_UNAVAILABLE",
                    "시맨틱 캐시 서비스를 사용할 수 없습니다."
                ),
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return Response(
                create_error_response("CACHE_ERROR", str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UsageHistoryView(APIView):
    """
    GET: 사용량 히스토리 조회

    Query Parameters:
        - page: 페이지 번호 (기본값: 1)
        - page_size: 페이지 크기 (기본값: 20, 최대: 100)
        - hours: 조회 기간 (시간, 기본값: 168 = 7일)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """사용량 히스토리 조회"""
        from datetime import timedelta
        from django.core.paginator import Paginator

        try:
            from .models import UsageLog

            # 파라미터 파싱
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 20)), 100)
            hours = int(request.query_params.get('hours', 168))

            # 조회
            since = timezone.now() - timedelta(hours=hours)
            logs = UsageLog.objects.filter(
                user=request.user,
                created_at__gte=since
            ).order_by('-created_at')

            # 페이지네이션
            paginator = Paginator(logs, page_size)
            page_obj = paginator.get_page(page)

            # 직렬화
            data = []
            for log in page_obj:
                data.append({
                    'id': log.id,
                    'model': log.model,
                    'model_version': log.model_version,
                    'request_type': log.request_type,
                    'input_tokens': log.input_tokens,
                    'output_tokens': log.output_tokens,
                    'total_tokens': log.total_tokens,
                    'cost_usd': float(log.cost_usd),
                    'cached': log.cached,
                    'latency_ms': log.latency_ms,
                    'created_at': log.created_at.isoformat()
                })

            return Response(create_success_response({
                'results': data,
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                }
            }))

        except Exception as e:
            logger.error(f"Failed to get usage history: {e}")
            return Response(
                create_error_response("HISTORY_ERROR", str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModelPricingView(APIView):
    """
    GET: 모델별 가격 정보 조회
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """모델별 가격 정보 조회"""
        from .services.cost_tracker import get_cost_tracker

        tracker = get_cost_tracker()

        pricing_list = []
        for model_key, pricing in tracker.PRICING.items():
            if model_key == 'default':
                continue
            pricing_list.append({
                'model': model_key,
                'name': pricing['name'],
                'input_per_1m_tokens': pricing['input'],
                'output_per_1m_tokens': pricing['output'],
            })

        return Response(create_success_response({
            'pricing': pricing_list,
            'currency': 'USD',
            'unit': 'per 1M tokens',
            'last_updated': '2025-01'
        }))
