##1차 작성중..
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import ParseError, NotFound

from .serializers import UserSerializer, PrivateUserSerializer
from stocks.models import Stock
from .models import User


# 현재 로그인한 사용자 정보 조회 및 수정
class Me(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """현재 로그인한 사용자 정보를 반환합니다."""
        user = request.user
        serializer = PrivateUserSerializer(user)
        return Response(serializer.data)

    def put(self, request):
        """현재 로그인한 사용자 정보를 부분 업데이트합니다."""
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
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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