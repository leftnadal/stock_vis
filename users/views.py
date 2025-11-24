import logging
import threading

from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum, F

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import ParseError, NotFound

from .serializers import (
    UserSerializer,
    PrivateUserSerializer,
    PortfolioSerializer,
    PortfolioDetailSerializer,
    PortfolioCreateUpdateSerializer,
    PortfolioSummarySerializer
)
from stocks.models import Stock
from .models import User, Portfolio

logger = logging.getLogger(__name__)


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

    def get(self, request, symbol):
        """주식 데이터 상태 조회"""
        from users.utils import get_stock_data_status

        status_data = get_stock_data_status(symbol)
        return Response(status_data)