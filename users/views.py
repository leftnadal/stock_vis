import logging
import threading

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import Sum, F
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator, EmptyPage

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import ParseError, NotFound, ValidationError
from rest_framework.throttling import UserRateThrottle

from .serializers import (
    UserSerializer,
    PrivateUserSerializer,
    PortfolioSerializer,
    PortfolioDetailSerializer,
    PortfolioCreateUpdateSerializer,
    PortfolioSummarySerializer,
    WatchlistSerializer,
    WatchlistDetailSerializer,
    WatchlistCreateUpdateSerializer,
    WatchlistItemSerializer,
    WatchlistItemCreateSerializer,
    WatchlistItemUpdateSerializer
)
from stocks.models import Stock
from .models import User, Portfolio, Watchlist, WatchlistItem, UserInterest
from .cache_utils import WatchlistCache, watchlist_cached_api

logger = logging.getLogger(__name__)


# Rate Limiting 설정
class WatchlistRateThrottle(UserRateThrottle):
    """Watchlist API 전용 Rate Throttle (100회/시간)"""
    rate = '100/hour'


# 현재 로그인한 사용자 정보 조회 및 수정
class Me(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """현재 로그인한 사용자 정보를 반환합니다."""
        user = request.user
        serializer = PrivateUserSerializer(user)
        return Response(serializer.data)

    def _update_user(self, request):
        """사용자 정보 업데이트 공통 로직"""
        user = request.user
        serializer = PrivateUserSerializer(
            user,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            user = serializer.save()
            serializer = PrivateUserSerializer(user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """현재 로그인한 사용자 정보를 부분 업데이트합니다."""
        return self._update_user(request)

    def patch(self, request):
        """현재 로그인한 사용자 정보를 부분 업데이트합니다. (PATCH 메서드)"""
        return self._update_user(request)


# 사용자 목록 조회 (관리자용) 및 회원 가입
class Users(APIView):
    """
    GET: 관리자 전용 사용자 목록 조회
    POST: 회원 가입
    """
    def get_permissions(self):
        # GET 요청은 관리자 전용으로 제한
        if self.request.method.lower() == 'get':
            return [IsAdminUser()]
        return []

    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        password = request.data.get("password")
        if not password:
            raise ParseError("Password is required")
        
        serializer = PrivateUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(password)
            user.save()
            serializer = PrivateUserSerializer(user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 특정 사용자 정보 조회
class PublicUser(APIView):
    def get(self, request, user_name):
        try:
            user = User.objects.get(username=user_name)
        except User.DoesNotExist:
            raise NotFound
        serializer = UserSerializer(user)
        return Response(serializer.data)


# 비밀번호 변경
class ChangePassword(APIView):
    """현재 비밀번호를 확인 후 새 비밀번호로 변경합니다."""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        
        if not old_password or not new_password:
            raise ParseError("Both old and new passwords are required")
        
        if user.check_password(old_password):
            user.set_password(new_password)
            user.save()
            return Response(status=status.HTTP_200_OK)
        else:
            raise ParseError("Current password is incorrect")


# 로그인
class LogIn(APIView):
    """사용자 인증 및 세션 생성을 통해 로그인합니다."""
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        
        if not username or not password:
            raise ParseError("Username and password are required")
        
        user = authenticate(
            request,
            username=username,
            password=password,
        )
        
        if user:
            login(request, user)
            return Response(
                {"ok": "Welcome!", "user": PrivateUserSerializer(user).data}, 
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Wrong username or password"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )


# 로그아웃
class LogOut(APIView):
    """세션 종료를 통해 로그아웃합니다."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"ok": "You have been logged out"})


# 즐겨찾기 주식 목록 조회
class UserFavorites(APIView):  
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        favorite_stocks = user.favorite_stock.all()
        from stocks.serializers import StockSerializer
        serializer = StockSerializer(favorite_stocks, many=True)
        return Response(serializer.data)


# 즐겨찾기 추가
class AddFavorite(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, stock_id):
        """특정 주식을 즐겨찾기에 추가합니다."""
        user = request.user
        
        try:
            stock = Stock.objects.get(id=stock_id)
        except Stock.DoesNotExist:
            raise NotFound("Stock not found")
        
        if stock in user.favorite_stock.all():
            return Response(
                {"message": "This stock is already in your favorites"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.favorite_stock.add(stock)
        
        from stocks.serializers import StockSerializer
        return Response({
            "message": "Stock added to favorites",
            "stock": StockSerializer(stock).data
        })


# 즐겨찾기 제거
class RemoveFavorite(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, stock_id):
        """특정 주식을 즐겨찾기에서 제거합니다."""
        user = request.user
        
        try:
            stock = Stock.objects.get(id=stock_id)
        except Stock.DoesNotExist:
            raise NotFound("Stock not found")
        
        if stock not in user.favorite_stock.all():
            return Response(
                {"message": "This stock is not in your favorites"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.favorite_stock.remove(stock)

        return Response({
            "message": "Stock removed from favorites"
        })


# 포트폴리오 목록 조회 및 생성
class PortfolioListCreateView(APIView):
    """
    GET: 사용자의 포트폴리오 목록 조회
    POST: 새로운 포트폴리오 항목 추가
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """사용자의 포트폴리오 목록 조회"""
        portfolios = Portfolio.objects.filter(user=request.user).select_related('stock')
        serializer = PortfolioSerializer(portfolios, many=True)
        return Response(serializer.data)

    def post(self, request):
        """새로운 포트폴리오 항목 추가 및 주식 데이터 백그라운드 수집"""
        logger.info(f"Portfolio creation request: {request.data}")

        serializer = PortfolioCreateUpdateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            portfolio = serializer.save()
            symbol = portfolio.stock.symbol

            # 백그라운드에서 데이터 수집 시작
            from users.utils import fetch_stock_data_background

            def background_fetch():
                try:
                    logger.info(f"Starting background data fetch for {symbol}")
                    fetch_stock_data_background(symbol)
                    logger.info(f"Completed background data fetch for {symbol}")
                except Exception as e:
                    logger.error(f"Background fetch error for {symbol}: {e}")

            # 백그라운드 스레드로 데이터 수집 시작
            thread = threading.Thread(target=background_fetch, daemon=True)
            thread.start()

            # 즉시 응답 반환
            return Response(
                PortfolioSerializer(portfolio).data,
                status=status.HTTP_201_CREATED
            )

        logger.error(f"Validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 포트폴리오 상세 조회, 수정, 삭제
class PortfolioDetailView(APIView):
    """
    GET: 특정 포트폴리오 항목 조회
    PUT: 포트폴리오 항목 수정
    DELETE: 포트폴리오 항목 삭제
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        """포트폴리오 객체 가져오기"""
        try:
            return Portfolio.objects.get(pk=pk, user=user)
        except Portfolio.DoesNotExist:
            raise NotFound("Portfolio not found")

    def get(self, request, pk):
        """특정 포트폴리오 항목 조회"""
        portfolio = self.get_object(pk, request.user)
        serializer = PortfolioSerializer(portfolio)
        return Response(serializer.data)

    def put(self, request, pk):
        """포트폴리오 항목 수정"""
        portfolio = self.get_object(pk, request.user)
        serializer = PortfolioCreateUpdateSerializer(
            portfolio,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            portfolio = serializer.save()
            return Response(PortfolioSerializer(portfolio).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """포트폴리오 항목 삭제"""
        portfolio = self.get_object(pk, request.user)
        portfolio.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# 포트폴리오 요약 정보
class PortfolioSummaryView(APIView):
    """
    사용자 포트폴리오의 전체 요약 정보 제공
    - 총 보유 종목 수
    - 총 평가 금액
    - 총 수익/손실
    - 수익률
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """포트폴리오 요약 정보 조회"""
        portfolios = Portfolio.objects.filter(user=request.user).select_related('stock')

        if not portfolios.exists():
            return Response({
                'total_stocks': 0,
                'total_value': 0,
                'total_cost': 0,
                'total_profit_loss': 0,
                'total_profit_loss_percentage': 0,
                'is_profitable': True
            })

        # 총 계산
        total_value = 0
        total_cost = 0

        for portfolio in portfolios:
            total_value += portfolio.total_value
            total_cost += portfolio.total_cost

        total_profit_loss = total_value - total_cost
        total_profit_loss_percentage = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

        summary = {
            'total_stocks': portfolios.count(),
            'total_value': total_value,
            'total_cost': total_cost,
            'total_profit_loss': total_profit_loss,
            'total_profit_loss_percentage': total_profit_loss_percentage,
            'is_profitable': total_profit_loss >= 0
        }

        serializer = PortfolioSummarySerializer(summary)
        return Response(serializer.data)


# 포트폴리오 상세 테이블 뷰
class PortfolioDetailTableView(APIView):
    """
    포트폴리오 상세 테이블 뷰를 위한 엔드포인트
    모든 분석 지표를 포함한 상세 데이터 제공
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """포트폴리오 상세 테이블 데이터 조회"""
        portfolios = Portfolio.objects.filter(
            user=request.user
        ).select_related('stock')

        # 전체 포트폴리오 가치 계산 (비중 계산용)
        total_portfolio_value = sum(p.total_value for p in portfolios)

        # serializer에 context 전달
        serializer = PortfolioDetailSerializer(
            portfolios,
            many=True,
            context={'total_portfolio_value': total_portfolio_value}
        )

        # 요약 통계 추가
        total_cost = sum(p.total_cost for p in portfolios)
        total_profit_loss = total_portfolio_value - total_cost
        total_profit_loss_percentage = ((total_portfolio_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

        return Response({
            'portfolios': serializer.data,
            'summary': {
                'total_stocks': portfolios.count(),
                'total_value': total_portfolio_value,
                'total_cost': total_cost,
                'total_profit_loss': total_profit_loss,
                'total_profit_loss_percentage': total_profit_loss_percentage,
                'is_profitable': total_profit_loss >= 0
            }
        })

    def patch(self, request, pk=None):
        """목표가/손절가 등 빠른 수정을 위한 엔드포인트"""
        if not pk:
            return Response(
                {"error": "Portfolio ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            portfolio = Portfolio.objects.get(pk=pk, user=request.user)
        except Portfolio.DoesNotExist:
            raise NotFound("Portfolio not found")

        # 목표가/손절가만 업데이트 허용
        allowed_fields = ['target_price', 'stop_loss_price', 'notes']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = PortfolioCreateUpdateSerializer(
            portfolio,
            data=update_data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            portfolio = serializer.save()
            # 전체 포트폴리오 가치 재계산
            total_portfolio_value = Portfolio.objects.filter(
                user=request.user
            ).aggregate(
                total=Sum(F('quantity') * F('stock__real_time_price'))
            )['total'] or 0

            detail_serializer = PortfolioDetailSerializer(
                portfolio,
                context={'total_portfolio_value': float(total_portfolio_value)}
            )
            return Response(detail_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 심볼로 포트폴리오 조회
class PortfolioBySymbolView(APIView):
    """
    특정 주식 심볼에 대한 포트폴리오 정보 조회
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, symbol):
        """심볼로 포트폴리오 조회"""
        try:
            portfolio = Portfolio.objects.get(
                user=request.user,
                stock__symbol=symbol.upper()
            )
            serializer = PortfolioSerializer(portfolio)
            return Response(serializer.data)
        except Portfolio.DoesNotExist:
            raise NotFound(f"No portfolio found for symbol {symbol}")


# 포트폴리오 주식 데이터 갱신
class RefreshPortfolioDataView(APIView):
    """
    포트폴리오에 있는 주식들의 데이터를 수동으로 갱신
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """포트폴리오의 모든 주식 데이터를 갱신"""
        from users.utils import update_portfolio_stock_data

        try:
            results = update_portfolio_stock_data(request.user.id)

            return Response({
                'message': 'Portfolio data refresh initiated',
                'results': results
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to refresh portfolio data: {e}")
            return Response({
                'error': 'Failed to refresh portfolio data',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 단일 주식 데이터 갱신
class RefreshStockDataView(APIView):
    """
    특정 주식의 데이터를 수동으로 갱신
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, symbol):
        """특정 주식 데이터를 갱신"""
        from users.utils import fetch_stock_data_sync

        # 사용자가 해당 주식을 보유하고 있는지 확인
        portfolio = Portfolio.objects.filter(
            user=request.user,
            stock__symbol=symbol.upper()
        ).first()

        if not portfolio:
            return Response({
                'error': 'Stock not found in your portfolio'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            result = fetch_stock_data_sync(symbol)

            if result['success']:
                return Response({
                    'message': f'Successfully refreshed data for {symbol}',
                    'data': result['data']
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': f'Partially refreshed data for {symbol}',
                    'data': result['data'],
                    'errors': result['errors']
                }, status=status.HTTP_207_MULTI_STATUS)

        except Exception as e:
            logger.error(f"Failed to refresh stock data for {symbol}: {e}")
            return Response({
                'error': f'Failed to refresh data for {symbol}',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 주식 데이터 수집 상태 확인
class StockDataStatusView(APIView):
    """
    특정 주식의 데이터 수집 상태를 확인합니다.
    프론트엔드에서 폴링으로 호출하여 로딩 상태를 업데이트합니다.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, symbol):
        """주식 데이터 상태 조회"""
        from users.utils import get_stock_data_status

        status_data = get_stock_data_status(symbol)
        return Response(status_data)


# ============ Watchlist Views ============

class WatchlistListCreateView(APIView):
    """
    GET: Watchlist 목록 조회 (캐싱 적용, 페이지네이션)
    POST: 새로운 Watchlist 생성 (캐시 무효화)
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [WatchlistRateThrottle]

    @watchlist_cached_api(cache_type='list', timeout=300)
    def get(self, request):
        """사용자의 Watchlist 목록 조회 (페이지네이션 적용)"""
        watchlists = Watchlist.objects.filter(user=request.user).order_by('-updated_at')

        # 페이지네이션 파라미터 추출
        page_number = request.query_params.get('page', 1)
        page_size = int(request.query_params.get('page_size', 20))

        # 페이지 크기 제한 (최대 100개)
        if page_size > 100:
            page_size = 100

        # 페이지네이션 적용
        paginator = Paginator(watchlists, page_size)
        try:
            page_obj = paginator.page(page_number)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        serializer = WatchlistSerializer(page_obj.object_list, many=True)

        return Response({
            'results': serializer.data,
            'pagination': {
                'count': paginator.count,
                'page': page_obj.number,
                'page_size': page_size,
                'num_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })

    def post(self, request):
        """새로운 Watchlist 생성 (캐시 무효화)"""
        serializer = WatchlistCreateUpdateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            watchlist = serializer.save()

            # 캐시 무효화 - Watchlist 목록 캐시 삭제
            WatchlistCache.invalidate_watchlist_list(request.user.id)

            return Response(WatchlistSerializer(watchlist).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WatchlistDetailView(APIView):
    """
    GET: Watchlist 상세 조회 (종목 리스트 포함)
    PATCH: Watchlist 수정
    DELETE: Watchlist 삭제
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [WatchlistRateThrottle]

    def get_object(self, pk, user):
        """Watchlist 객체 가져오기"""
        try:
            return Watchlist.objects.prefetch_related('items__stock').get(pk=pk, user=user)
        except Watchlist.DoesNotExist:
            raise NotFound(_("Watchlist not found"))

    def get(self, request, pk):
        """Watchlist 상세 조회"""
        watchlist = self.get_object(pk, request.user)
        serializer = WatchlistDetailSerializer(watchlist)
        return Response(serializer.data)

    def patch(self, request, pk):
        """Watchlist 수정"""
        watchlist = self.get_object(pk, request.user)
        serializer = WatchlistCreateUpdateSerializer(
            watchlist,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            watchlist = serializer.save()
            return Response(WatchlistSerializer(watchlist).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Watchlist 삭제 (캐시 무효화)"""
        watchlist = self.get_object(pk, request.user)
        watchlist.delete()

        # 캐시 무효화 - Watchlist 목록과 해당 Watchlist 종목 데이터 캐시 삭제
        WatchlistCache.invalidate_watchlist_list(request.user.id)
        WatchlistCache.invalidate_watchlist_stocks(request.user.id, pk)

        return Response(status=status.HTTP_204_NO_CONTENT)


class WatchlistItemAddView(APIView):
    """
    POST: Watchlist에 종목 추가 (캐시 무효화, 트랜잭션 보호)
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [WatchlistRateThrottle]

    def post(self, request, pk):
        """Watchlist에 종목 추가 (트랜잭션 보호)"""
        with transaction.atomic():
            # Watchlist 확인 및 락 획득
            try:
                watchlist = Watchlist.objects.select_for_update().get(pk=pk, user=request.user)
            except Watchlist.DoesNotExist:
                raise NotFound(_("Watchlist not found"))

            # 종목 추가
            serializer = WatchlistItemCreateSerializer(data=request.data)
            if serializer.is_valid():
                stock = serializer.validated_data['stock']

                # 이미 해당 종목이 리스트에 있는지 확인
                if WatchlistItem.objects.filter(watchlist=watchlist, stock=stock).exists():
                    return Response(
                        {"error": _(f"'{stock.symbol}' stock is already in this watchlist")},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # WatchlistItem 생성
                item = WatchlistItem.objects.create(
                    watchlist=watchlist,
                    stock=stock,
                    target_entry_price=serializer.validated_data.get('target_entry_price'),
                    notes=serializer.validated_data.get('notes', ''),
                    position_order=serializer.validated_data.get('position_order', 0)
                )

                # 캐시 무효화 - 종목 데이터 캐시 삭제
                WatchlistCache.invalidate_watchlist_stocks(request.user.id, pk)

                return Response(WatchlistItemSerializer(item).data, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WatchlistItemRemoveView(APIView):
    """
    DELETE: Watchlist에서 종목 제거 (캐시 무효화)
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [WatchlistRateThrottle]

    def delete(self, request, pk, symbol):
        """Watchlist에서 종목 제거 (캐시 무효화)"""
        # Watchlist 확인
        try:
            watchlist = Watchlist.objects.get(pk=pk, user=request.user)
        except Watchlist.DoesNotExist:
            raise NotFound(_("Watchlist not found"))

        # WatchlistItem 확인 및 삭제
        try:
            item = WatchlistItem.objects.get(watchlist=watchlist, stock__symbol=symbol.upper())
            item.delete()

            # 캐시 무효화 - 종목 데이터 캐시 삭제
            WatchlistCache.invalidate_watchlist_stocks(request.user.id, pk)

            return Response(status=status.HTTP_204_NO_CONTENT)
        except WatchlistItem.DoesNotExist:
            raise NotFound(_(f"Stock {symbol} not found in this watchlist"))


class WatchlistItemUpdateView(APIView):
    """
    PATCH: Watchlist 종목 설정 수정 (목표가, 메모 등, 캐시 무효화)
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [WatchlistRateThrottle]

    def patch(self, request, pk, symbol):
        """Watchlist 종목 설정 수정 (캐시 무효화)"""
        # Watchlist 확인
        try:
            watchlist = Watchlist.objects.get(pk=pk, user=request.user)
        except Watchlist.DoesNotExist:
            raise NotFound(_("Watchlist not found"))

        # WatchlistItem 확인
        try:
            item = WatchlistItem.objects.select_related('stock').get(
                watchlist=watchlist,
                stock__symbol=symbol.upper()
            )
        except WatchlistItem.DoesNotExist:
            raise NotFound(_(f"Stock {symbol} not found in this watchlist"))

        # 수정
        serializer = WatchlistItemUpdateSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            item = serializer.save()

            # 캐시 무효화 - 종목 데이터 캐시 삭제
            WatchlistCache.invalidate_watchlist_stocks(request.user.id, pk)

            return Response(WatchlistItemSerializer(item).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WatchlistStocksView(APIView):
    """
    GET: Watchlist의 종목 상세 조회 (실시간 가격 포함, 캐싱 적용, 페이지네이션)
    - 캐싱 TTL: 60초 (실시간 가격 포함)
    - 캐시 키: user_id + watchlist_id
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [WatchlistRateThrottle]

    @watchlist_cached_api(cache_type='stocks', timeout=60)
    def get(self, request, pk):
        """Watchlist 종목 상세 조회 (페이지네이션 적용)"""
        # Watchlist 확인
        try:
            watchlist = Watchlist.objects.get(pk=pk, user=request.user)
        except Watchlist.DoesNotExist:
            raise NotFound(_("Watchlist not found"))

        # 종목 조회 (N+1 쿼리 방지)
        items = WatchlistItem.objects.filter(watchlist=watchlist).select_related('stock').order_by('position_order', '-added_at')

        # 페이지네이션 파라미터 추출
        page_number = request.query_params.get('page', 1)
        page_size = int(request.query_params.get('page_size', 20))

        # 페이지 크기 제한 (최대 100개)
        if page_size > 100:
            page_size = 100

        # 페이지네이션 적용
        paginator = Paginator(items, page_size)
        try:
            page_obj = paginator.page(page_number)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        serializer = WatchlistItemSerializer(page_obj.object_list, many=True)

        return Response({
            'results': serializer.data,
            'pagination': {
                'count': paginator.count,
                'page': page_obj.number,
                'page_size': page_size,
                'num_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })


class WatchlistBulkAddView(APIView):
    """
    POST: Watchlist에 여러 종목 한 번에 추가 (트랜잭션 보호)
    Request Body: {"symbols": ["AAPL", "MSFT", "GOOGL"], "target_entry_price": 150.00, "notes": ""}
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [WatchlistRateThrottle]

    def post(self, request, pk):
        """여러 종목을 한 번에 추가"""
        symbols = request.data.get('symbols', [])
        if not symbols or not isinstance(symbols, list):
            raise ValidationError(_("'symbols' field is required and must be a list"))

        target_entry_price = request.data.get('target_entry_price')
        notes = request.data.get('notes', '')
        position_order = request.data.get('position_order', 0)

        with transaction.atomic():
            # Watchlist 확인 및 락 획득
            try:
                watchlist = Watchlist.objects.select_for_update().get(pk=pk, user=request.user)
            except Watchlist.DoesNotExist:
                raise NotFound(_("Watchlist not found"))

            added = []
            skipped = []
            errors = []

            for symbol in symbols:
                try:
                    # 종목 조회
                    stock = Stock.objects.get(symbol=symbol.upper())

                    # 중복 확인
                    if WatchlistItem.objects.filter(watchlist=watchlist, stock=stock).exists():
                        skipped.append(symbol)
                        continue

                    # WatchlistItem 생성
                    item = WatchlistItem.objects.create(
                        watchlist=watchlist,
                        stock=stock,
                        target_entry_price=target_entry_price,
                        notes=notes,
                        position_order=position_order
                    )
                    added.append(WatchlistItemSerializer(item).data)

                except Stock.DoesNotExist:
                    errors.append({'symbol': symbol, 'error': _('Stock not found')})
                except Exception as e:
                    errors.append({'symbol': symbol, 'error': str(e)})

            # 캐시 무효화
            WatchlistCache.invalidate_watchlist_stocks(request.user.id, pk)

            return Response({
                'added': added,
                'skipped': skipped,
                'errors': errors,
                'summary': {
                    'total': len(symbols),
                    'added_count': len(added),
                    'skipped_count': len(skipped),
                    'error_count': len(errors)
                }
            }, status=status.HTTP_201_CREATED if added else status.HTTP_200_OK)


class WatchlistBulkRemoveView(APIView):
    """
    POST: Watchlist에서 여러 종목 한 번에 제거 (트랜잭션 보호)
    Request Body: {"symbols": ["AAPL", "MSFT", "GOOGL"]}
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [WatchlistRateThrottle]

    def post(self, request, pk):
        """여러 종목을 한 번에 제거"""
        symbols = request.data.get('symbols', [])
        if not symbols or not isinstance(symbols, list):
            raise ValidationError(_("'symbols' field is required and must be a list"))

        with transaction.atomic():
            # Watchlist 확인
            try:
                watchlist = Watchlist.objects.get(pk=pk, user=request.user)
            except Watchlist.DoesNotExist:
                raise NotFound(_("Watchlist not found"))

            removed = []
            not_found = []

            for symbol in symbols:
                try:
                    item = WatchlistItem.objects.get(watchlist=watchlist, stock__symbol=symbol.upper())
                    item.delete()
                    removed.append(symbol)
                except WatchlistItem.DoesNotExist:
                    not_found.append(symbol)

            # 캐시 무효화
            WatchlistCache.invalidate_watchlist_stocks(request.user.id, pk)

            return Response({
                'removed': removed,
                'not_found': not_found,
                'summary': {
                    'total': len(symbols),
                    'removed_count': len(removed),
                    'not_found_count': len(not_found)
                }
            }, status=status.HTTP_200_OK)


class UserInterestListCreateView(APIView):
    """
    GET: 사용자 관심사 목록 조회
    POST: 관심사 bulk 추가 (중복 무시)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        interests = UserInterest.objects.filter(user=request.user).order_by('-created_at')
        data = [
            {
                'id': i.id,
                'interest_type': i.interest_type,
                'value': i.value,
                'display_name': i.display_name,
                'auto_category_id': i.auto_category_id,
                'created_at': i.created_at.isoformat(),
            }
            for i in interests
        ]
        return Response(data)

    def post(self, request):
        """
        Request Body:
        {
            "interests": [
                {"interest_type": "theme", "value": "ai_semiconductor", "display_name": "AI & 반도체"},
                {"interest_type": "sector", "value": "Technology", "display_name": "Technology"}
            ]
        }
        """
        from news.models import NewsCollectionCategory

        interests_data = request.data.get('interests', [])
        if not interests_data or not isinstance(interests_data, list):
            raise ValidationError("'interests' 필드가 필요합니다 (리스트)")

        created = []
        skipped = []

        for item in interests_data:
            interest_type = item.get('interest_type')
            value = item.get('value')
            display_name = item.get('display_name', value)

            if not interest_type or not value:
                continue

            interest, was_created = UserInterest.objects.get_or_create(
                user=request.user,
                interest_type=interest_type,
                value=value,
                defaults={'display_name': display_name},
            )

            if was_created:
                # NewsCollectionCategory 자동 연결
                self._link_category(interest)
                created.append({
                    'id': interest.id,
                    'interest_type': interest.interest_type,
                    'value': interest.value,
                    'display_name': interest.display_name,
                    'auto_category_id': interest.auto_category_id,
                })
            else:
                skipped.append(value)

        return Response({
            'created': created,
            'skipped': skipped,
            'total_interests': UserInterest.objects.filter(user=request.user).count(),
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def _link_category(self, interest):
        """관심사에 맞는 NewsCollectionCategory 자동 연결"""
        from news.models import NewsCollectionCategory

        try:
            if interest.interest_type == 'sector':
                cat, _ = NewsCollectionCategory.objects.get_or_create(
                    name=interest.display_name,
                    category_type='sector',
                    defaults={
                        'value': interest.value,
                        'is_active': True,
                        'priority': 'medium',
                    },
                )
                interest.auto_category_id = cat.id
                interest.save(update_fields=['auto_category_id'])

            elif interest.interest_type == 'theme':
                from news.services.interest_options import InterestOptionsService
                symbols = InterestOptionsService.get_theme_symbols(interest.value)
                if symbols:
                    cat, _ = NewsCollectionCategory.objects.get_or_create(
                        name=interest.display_name,
                        category_type='custom',
                        defaults={
                            'value': ','.join(symbols),
                            'is_active': True,
                            'priority': 'medium',
                        },
                    )
                    interest.auto_category_id = cat.id
                    interest.save(update_fields=['auto_category_id'])
        except Exception as e:
            logger.warning(f"Failed to link category for interest {interest}: {e}")


class UserInterestDeleteView(APIView):
    """DELETE: 특정 관심사 삭제"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            interest = UserInterest.objects.get(pk=pk, user=request.user)
            interest.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except UserInterest.DoesNotExist:
            raise NotFound("Interest not found")