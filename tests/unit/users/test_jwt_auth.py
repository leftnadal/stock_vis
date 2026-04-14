"""
JWT 인증 테스트

회원가입, 로그인, 로그아웃, 토큰 검증, 비밀번호 변경, 프로필 관련 테스트
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

pytestmark = pytest.mark.unit


class TestJWTSignUp:
    """JWT 회원가입 테스트"""

    @pytest.mark.django_db
    def test_signup_success(self, api_client):
        """
        Given: 유효한 회원가입 정보
        When: POST /api/v1/users/jwt/signup/
        Then: 201 Created + 토큰 발급
        """
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'securepass123',
            'password2': 'securepass123',
            'nick_name': '새유저',
        }

        response = api_client.post('/api/v1/users/jwt/signup/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']
        assert 'refresh' in response.data['tokens']
        assert response.data['user']['username'] == 'newuser'
        assert User.objects.filter(username='newuser').exists()

    @pytest.mark.django_db
    def test_signup_missing_fields(self, api_client):
        """
        Given: 필수 필드 누락
        When: POST /api/v1/users/jwt/signup/
        Then: 400 Bad Request
        """
        data = {'username': 'incomplete'}

        response = api_client.post('/api/v1/users/jwt/signup/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    @pytest.mark.django_db
    def test_signup_password_mismatch(self, api_client):
        """
        Given: 비밀번호 확인 불일치
        When: POST /api/v1/users/jwt/signup/
        Then: 400 Bad Request
        """
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'pass1234',
            'password2': 'different',
        }

        response = api_client.post('/api/v1/users/jwt/signup/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '일치' in response.data['error']

    @pytest.mark.django_db
    def test_signup_duplicate_username(self, api_client, authenticated_user):
        """
        Given: 이미 존재하는 username
        When: POST /api/v1/users/jwt/signup/
        Then: 400 Bad Request
        """
        data = {
            'username': 'testuser',  # authenticated_user의 username
            'email': 'unique@example.com',
            'password': 'pass1234',
            'password2': 'pass1234',
        }

        response = api_client.post('/api/v1/users/jwt/signup/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '사용자명' in response.data['error']

    @pytest.mark.django_db
    def test_signup_duplicate_email(self, api_client, authenticated_user):
        """
        Given: 이미 등록된 이메일
        When: POST /api/v1/users/jwt/signup/
        Then: 400 Bad Request
        """
        data = {
            'username': 'uniqueuser',
            'email': 'test@example.com',  # authenticated_user의 email
            'password': 'pass1234',
            'password2': 'pass1234',
        }

        response = api_client.post('/api/v1/users/jwt/signup/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '이메일' in response.data['error']


class TestJWTLogin:
    """JWT 로그인 테스트"""

    @pytest.mark.django_db
    def test_login_success(self, api_client, authenticated_user):
        """
        Given: 유효한 로그인 정보
        When: POST /api/v1/users/jwt/login/
        Then: 200 OK + access/refresh 토큰 발급
        """
        data = {
            'username': 'testuser',
            'password': 'testpass123',
        }

        response = api_client.post('/api/v1/users/jwt/login/', data)

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert response.data['user']['username'] == 'testuser'

    @pytest.mark.django_db
    def test_login_wrong_password(self, api_client, authenticated_user):
        """
        Given: 잘못된 비밀번호
        When: POST /api/v1/users/jwt/login/
        Then: 401 Unauthorized
        """
        data = {
            'username': 'testuser',
            'password': 'wrongpassword',
        }

        response = api_client.post('/api/v1/users/jwt/login/', data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_login_nonexistent_user(self, api_client):
        """
        Given: 존재하지 않는 사용자
        When: POST /api/v1/users/jwt/login/
        Then: 401 Unauthorized
        """
        data = {
            'username': 'nobody',
            'password': 'pass1234',
        }

        response = api_client.post('/api/v1/users/jwt/login/', data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestJWTLogout:
    """JWT 로그아웃 (토큰 블랙리스트) 테스트"""

    @pytest.mark.django_db
    def test_logout_success(self, api_client, authenticated_user):
        """
        Given: 유효한 refresh 토큰
        When: POST /api/v1/users/jwt/logout/
        Then: 200 OK + 토큰 블랙리스트 등록
        """
        api_client.force_authenticate(user=authenticated_user)
        refresh = RefreshToken.for_user(authenticated_user)

        response = api_client.post(
            '/api/v1/users/jwt/logout/',
            {'refresh': str(refresh)},
        )

        assert response.status_code == status.HTTP_200_OK
        assert '로그아웃' in response.data['message']

    @pytest.mark.django_db
    def test_logout_missing_token(self, api_client, authenticated_user):
        """
        Given: refresh 토큰 누락
        When: POST /api/v1/users/jwt/logout/
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.post('/api/v1/users/jwt/logout/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_logout_unauthenticated(self, api_client):
        """
        Given: 인증되지 않은 사용자
        When: POST /api/v1/users/jwt/logout/
        Then: 401 Unauthorized
        """
        response = api_client.post('/api/v1/users/jwt/logout/', {'refresh': 'fake'})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_logout_invalid_token(self, api_client, authenticated_user):
        """
        Given: 유효하지 않은 refresh 토큰
        When: POST /api/v1/users/jwt/logout/
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.post(
            '/api/v1/users/jwt/logout/',
            {'refresh': 'invalid-token-string'},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestJWTTokenRefresh:
    """JWT 토큰 갱신 테스트"""

    @pytest.mark.django_db
    def test_token_refresh_success(self, api_client, authenticated_user):
        """
        Given: 유효한 refresh 토큰
        When: POST /api/v1/users/jwt/refresh/
        Then: 200 OK + 새 access 토큰 발급
        """
        refresh = RefreshToken.for_user(authenticated_user)

        response = api_client.post(
            '/api/v1/users/jwt/refresh/',
            {'refresh': str(refresh)},
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    @pytest.mark.django_db
    def test_token_refresh_invalid(self, api_client):
        """
        Given: 유효하지 않은 refresh 토큰
        When: POST /api/v1/users/jwt/refresh/
        Then: 401 Unauthorized
        """
        response = api_client.post(
            '/api/v1/users/jwt/refresh/',
            {'refresh': 'invalid-refresh-token'},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_token_refresh_blacklisted(self, api_client, authenticated_user):
        """
        Given: 블랙리스트에 등록된 refresh 토큰
        When: POST /api/v1/users/jwt/refresh/
        Then: 401 Unauthorized
        """
        refresh = RefreshToken.for_user(authenticated_user)
        refresh.blacklist()

        response = api_client.post(
            '/api/v1/users/jwt/refresh/',
            {'refresh': str(refresh)},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestJWTVerify:
    """JWT 토큰 검증 및 사용자 정보 반환 테스트"""

    @pytest.mark.django_db
    def test_verify_authenticated(self, api_client, authenticated_user):
        """
        Given: 인증된 사용자
        When: GET /api/v1/users/jwt/verify/
        Then: 200 OK + 사용자 정보 반환
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/jwt/verify/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['user']['email'] == 'test@example.com'
        assert response.data['user']['nick_name'] == '테스트유저'

    @pytest.mark.django_db
    def test_verify_unauthenticated(self, api_client):
        """
        Given: 인증되지 않은 사용자
        When: GET /api/v1/users/jwt/verify/
        Then: 401 Unauthorized
        """
        response = api_client.get('/api/v1/users/jwt/verify/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestChangePassword:
    """JWT 비밀번호 변경 테스트"""

    @pytest.mark.django_db
    def test_change_password_success(self, api_client, authenticated_user):
        """
        Given: 올바른 현재 비밀번호 + 새 비밀번호
        When: PUT /api/v1/users/jwt/change-password/
        Then: 200 OK + 새 토큰 발급
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'old_password': 'testpass123',
            'new_password': 'newpass456',
            'new_password2': 'newpass456',
        }

        response = api_client.put('/api/v1/users/jwt/change-password/', data)

        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data

        # 새 비밀번호로 로그인 확인
        authenticated_user.refresh_from_db()
        assert authenticated_user.check_password('newpass456')

    @pytest.mark.django_db
    def test_change_password_wrong_old(self, api_client, authenticated_user):
        """
        Given: 잘못된 현재 비밀번호
        When: PUT /api/v1/users/jwt/change-password/
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'old_password': 'wrongpassword',
            'new_password': 'newpass456',
            'new_password2': 'newpass456',
        }

        response = api_client.put('/api/v1/users/jwt/change-password/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_change_password_mismatch(self, api_client, authenticated_user):
        """
        Given: 새 비밀번호 확인 불일치
        When: PUT /api/v1/users/jwt/change-password/
        Then: 400 Bad Request
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {
            'old_password': 'testpass123',
            'new_password': 'newpass456',
            'new_password2': 'different789',
        }

        response = api_client.put('/api/v1/users/jwt/change-password/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_change_password_unauthenticated(self, api_client):
        """
        Given: 인증되지 않은 사용자
        When: PUT /api/v1/users/jwt/change-password/
        Then: 401 Unauthorized
        """
        data = {
            'old_password': 'old',
            'new_password': 'new',
            'new_password2': 'new',
        }

        response = api_client.put('/api/v1/users/jwt/change-password/', data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProfileUpdate:
    """프로필 조회/수정 테스트"""

    @pytest.mark.django_db
    def test_profile_get(self, api_client, authenticated_user):
        """
        Given: 인증된 사용자
        When: GET /api/v1/users/jwt/profile/
        Then: 200 OK + 프로필 정보 반환
        """
        api_client.force_authenticate(user=authenticated_user)

        response = api_client.get('/api/v1/users/jwt/profile/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == 'test@example.com'
        assert response.data['nick_name'] == '테스트유저'

    @pytest.mark.django_db
    def test_profile_update(self, api_client, authenticated_user):
        """
        Given: 인증된 사용자와 수정할 프로필 정보
        When: PUT /api/v1/users/jwt/profile/
        Then: 200 OK + 프로필 업데이트됨
        """
        api_client.force_authenticate(user=authenticated_user)

        data = {'nick_name': '수정된닉네임'}

        response = api_client.put('/api/v1/users/jwt/profile/', data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['user']['nick_name'] == '수정된닉네임'

        authenticated_user.refresh_from_db()
        assert authenticated_user.nick_name == '수정된닉네임'

    @pytest.mark.django_db
    def test_profile_unauthenticated(self, api_client):
        """
        Given: 인증되지 않은 사용자
        When: GET /api/v1/users/jwt/profile/
        Then: 401 Unauthorized
        """
        response = api_client.get('/api/v1/users/jwt/profile/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
