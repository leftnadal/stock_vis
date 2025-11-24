from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from .serializers import UserSerializer, PrivateUserSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """커스텀 JWT 토큰 시리얼라이저 - 토큰에 추가 정보 포함"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # 토큰에 추가 정보 포함
        token['username'] = user.username
        token['email'] = user.email
        token['is_staff'] = user.is_staff

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # 응답에 사용자 정보 추가
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'nick_name': self.user.nick_name if hasattr(self.user, 'nick_name') else None,
        }

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """커스텀 로그인 뷰 - JWT 토큰 발급"""
    serializer_class = CustomTokenObtainPairSerializer


class JWTSignUpView(APIView):
    """JWT 기반 회원가입"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        회원가입 및 자동 로그인 (JWT 토큰 발급)
        """
        # 필수 필드 검증
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        password2 = request.data.get('password2')

        # 유효성 검사
        if not username or not email or not password:
            return Response(
                {'error': '모든 필수 필드를 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if password != password2:
            return Response(
                {'error': '비밀번호가 일치하지 않습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 사용자 중복 확인
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': '이미 존재하는 사용자명입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {'error': '이미 등록된 이메일입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 사용자 생성
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_name=request.data.get('user_name', ''),
                nick_name=request.data.get('nick_name', username),
            )

            # JWT 토큰 생성
            refresh = RefreshToken.for_user(user)

            return Response({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'nick_name': user.nick_name,
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'message': '회원가입이 완료되었습니다.'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'회원가입 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class JWTLogoutView(APIView):
    """JWT 로그아웃 - Refresh Token 블랙리스트 추가"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        로그아웃 - Refresh Token을 블랙리스트에 추가
        """
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token이 필요합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {'message': '로그아웃되었습니다.'},
                status=status.HTTP_200_OK
            )
        except TokenError:
            return Response(
                {'error': '유효하지 않은 토큰입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class JWTVerifyView(APIView):
    """JWT 토큰 검증 및 사용자 정보 반환"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        현재 인증된 사용자 정보 반환
        """
        user = request.user
        serializer = PrivateUserSerializer(user)
        return Response({
            'user': serializer.data,
            'message': '토큰이 유효합니다.'
        }, status=status.HTTP_200_OK)


class ChangePasswordJWTView(APIView):
    """JWT 인증 기반 비밀번호 변경"""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        """
        비밀번호 변경
        """
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        new_password2 = request.data.get('new_password2')

        if not old_password or not new_password:
            return Response(
                {'error': '현재 비밀번호와 새 비밀번호를 모두 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != new_password2:
            return Response(
                {'error': '새 비밀번호가 일치하지 않습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(old_password):
            return Response(
                {'error': '현재 비밀번호가 올바르지 않습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        # 새 토큰 발급 (비밀번호 변경 후 재로그인 방지)
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': '비밀번호가 성공적으로 변경되었습니다.',
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)


class ProfileUpdateView(APIView):
    """사용자 프로필 업데이트"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """현재 사용자 프로필 조회"""
        serializer = PrivateUserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        """사용자 프로필 업데이트"""
        serializer = PrivateUserSerializer(
            request.user,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response({
                'user': serializer.data,
                'message': '프로필이 업데이트되었습니다.'
            })

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )