"""
User Interest CRUD 테스트

UserInterestListCreateView, UserInterestDeleteView 커버
- GET /api/v1/users/interests/   : 관심사 목록 조회 (본인 것만)
- POST /api/v1/users/interests/  : 관심사 bulk 추가 (중복 무시)
- DELETE /api/v1/users/interests/{pk}/ : 관심사 삭제
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import UserInterest

User = get_user_model()


# ===== Fixtures =====

@pytest.fixture
@pytest.mark.django_db
def api_client():
    """토큰 없는 기본 API Client"""
    return APIClient()


@pytest.fixture
@pytest.mark.django_db
def test_user(db):
    """테스트 사용자 생성"""
    return User.objects.create_user(
        username='interest_testuser',
        password='testpass123',
        email='interest_test@example.com',
    )


@pytest.fixture
@pytest.mark.django_db
def other_user(db):
    """다른 사용자 (권한 테스트용)"""
    return User.objects.create_user(
        username='interest_otheruser',
        password='testpass123',
        email='interest_other@example.com',
    )


@pytest.fixture
@pytest.mark.django_db
def auth_client(test_user):
    """JWT 인증된 API Client"""
    client = APIClient()
    refresh = RefreshToken.for_user(test_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


@pytest.fixture
@pytest.mark.django_db
def ai_semiconductor_interest(test_user):
    """AI 반도체 테마 관심사 (사전 생성)"""
    return UserInterest.objects.create(
        user=test_user,
        interest_type='theme',
        value='ai_semiconductor',
        display_name='AI & 반도체',
    )


@pytest.fixture
@pytest.mark.django_db
def tech_sector_interest(test_user):
    """Technology 섹터 관심사 (사전 생성)"""
    return UserInterest.objects.create(
        user=test_user,
        interest_type='sector',
        value='Technology',
        display_name='Technology',
    )


# ===== UserInterest 모델 테스트 =====

@pytest.mark.django_db
class TestUserInterestModel:
    """UserInterest 모델 기본 동작 테스트"""

    def test_create_theme_interest(self, test_user):
        """
        Given: 사용자와 테마 정보
        When: UserInterest 생성
        Then: 정상 생성됨
        """
        interest = UserInterest.objects.create(
            user=test_user,
            interest_type='theme',
            value='ev_battery',
            display_name='전기차 & 배터리',
        )

        assert interest.id is not None
        assert interest.user == test_user
        assert interest.interest_type == 'theme'
        assert interest.value == 'ev_battery'
        assert interest.display_name == '전기차 & 배터리'
        assert interest.auto_category_id is None

    def test_create_sector_interest(self, test_user):
        """
        Given: 사용자와 섹터 정보
        When: UserInterest 생성
        Then: 정상 생성됨
        """
        interest = UserInterest.objects.create(
            user=test_user,
            interest_type='sector',
            value='Healthcare',
            display_name='Healthcare',
        )

        assert interest.interest_type == 'sector'
        assert interest.value == 'Healthcare'

    def test_unique_constraint_per_user(self, test_user, ai_semiconductor_interest):
        """
        Given: 이미 존재하는 (user, interest_type, value) 조합
        When: 동일 조합으로 재생성 시도
        Then: IntegrityError 발생
        """
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            UserInterest.objects.create(
                user=test_user,
                interest_type='theme',
                value='ai_semiconductor',
                display_name='중복 테스트',
            )

    def test_same_value_different_users_allowed(self, test_user, other_user):
        """
        Given: 두 사용자
        When: 같은 value로 각각 관심사 생성
        Then: 둘 다 정상 생성됨 (unique_together는 user 포함)
        """
        i1 = UserInterest.objects.create(
            user=test_user,
            interest_type='theme',
            value='cloud_saas',
            display_name='클라우드 & SaaS',
        )
        i2 = UserInterest.objects.create(
            user=other_user,
            interest_type='theme',
            value='cloud_saas',
            display_name='클라우드 & SaaS',
        )

        assert i1.id != i2.id

    def test_str_representation(self, test_user):
        """
        Given: UserInterest 인스턴스
        When: str() 호출
        Then: 사용자명과 display_name 포함
        """
        interest = UserInterest.objects.create(
            user=test_user,
            interest_type='theme',
            value='cybersecurity',
            display_name='사이버보안',
        )

        assert 'interest_testuser' in str(interest)
        assert '사이버보안' in str(interest)


# ===== GET /api/v1/users/interests/ =====

@pytest.mark.django_db
class TestUserInterestListView:
    """관심사 목록 조회 API 테스트"""

    def test_get_interests_empty(self, auth_client):
        """
        Given: 관심사가 없는 사용자
        When: GET /api/v1/users/interests/
        Then: 빈 리스트 반환
        """
        response = auth_client.get('/api/v1/users/interests/')

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_get_interests_returns_own_only(
        self, auth_client, test_user, other_user,
        ai_semiconductor_interest
    ):
        """
        Given: test_user 관심사 1개, other_user 관심사 1개
        When: test_user가 GET /api/v1/users/interests/
        Then: test_user 관심사만 1개 반환 (other_user 관심사 포함 안 됨)
        """
        UserInterest.objects.create(
            user=other_user,
            interest_type='theme',
            value='ev_battery',
            display_name='전기차 & 배터리',
        )

        response = auth_client.get('/api/v1/users/interests/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]['value'] == 'ai_semiconductor'

    def test_get_interests_response_fields(
        self, auth_client, ai_semiconductor_interest
    ):
        """
        Given: 관심사 1개
        When: GET /api/v1/users/interests/
        Then: 응답에 필수 필드 포함
        """
        response = auth_client.get('/api/v1/users/interests/')

        assert response.status_code == status.HTTP_200_OK
        item = response.json()[0]

        assert 'id' in item
        assert 'interest_type' in item
        assert 'value' in item
        assert 'display_name' in item
        assert 'created_at' in item

    def test_get_interests_unauthenticated(self, api_client):
        """
        Given: 인증 없는 클라이언트
        When: GET /api/v1/users/interests/
        Then: 401 Unauthorized
        """
        response = api_client.get('/api/v1/users/interests/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_interests_multiple(
        self, auth_client, ai_semiconductor_interest, tech_sector_interest
    ):
        """
        Given: 관심사 2개 (테마 + 섹터)
        When: GET /api/v1/users/interests/
        Then: 2개 반환
        """
        response = auth_client.get('/api/v1/users/interests/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        values = {item['value'] for item in data}
        assert 'ai_semiconductor' in values
        assert 'Technology' in values


# ===== POST /api/v1/users/interests/ =====

@pytest.mark.django_db
class TestUserInterestCreateView:
    """관심사 bulk 추가 API 테스트"""

    def test_create_interests_single(self, auth_client):
        """
        Given: 테마 1개 데이터
        When: POST /api/v1/users/interests/
        Then: 201 Created, created 1개
        """
        payload = {
            'interests': [
                {
                    'interest_type': 'theme',
                    'value': 'ai_semiconductor',
                    'display_name': 'AI & 반도체',
                }
            ]
        }
        response = auth_client.post(
            '/api/v1/users/interests/', payload, format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data['created']) == 1
        assert data['created'][0]['value'] == 'ai_semiconductor'
        assert data['total_interests'] == 1

    def test_create_interests_bulk(self, auth_client):
        """
        Given: 테마 1개 + 섹터 1개
        When: POST /api/v1/users/interests/
        Then: 201 Created, created 2개
        """
        payload = {
            'interests': [
                {
                    'interest_type': 'theme',
                    'value': 'ai_semiconductor',
                    'display_name': 'AI & 반도체',
                },
                {
                    'interest_type': 'sector',
                    'value': 'Technology',
                    'display_name': 'Technology',
                },
            ]
        }
        response = auth_client.post(
            '/api/v1/users/interests/', payload, format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data['created']) == 2
        assert data['total_interests'] == 2

    def test_create_interests_duplicate_skipped(
        self, auth_client, ai_semiconductor_interest
    ):
        """
        Given: 이미 존재하는 ai_semiconductor 관심사
        When: 동일 value로 POST
        Then: 200 OK, created 0개, skipped 1개
        """
        payload = {
            'interests': [
                {
                    'interest_type': 'theme',
                    'value': 'ai_semiconductor',
                    'display_name': 'AI & 반도체',
                }
            ]
        }
        response = auth_client.post(
            '/api/v1/users/interests/', payload, format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data['created']) == 0
        assert len(data['skipped']) == 1
        assert 'ai_semiconductor' in data['skipped']

    def test_create_interests_partial_duplicate(
        self, auth_client, ai_semiconductor_interest
    ):
        """
        Given: ai_semiconductor 기존 존재, ev_battery 신규
        When: 두 개 동시 POST
        Then: 201 Created, created 1개 (ev_battery), skipped 1개 (ai_semiconductor)
        """
        payload = {
            'interests': [
                {
                    'interest_type': 'theme',
                    'value': 'ai_semiconductor',
                    'display_name': 'AI & 반도체',
                },
                {
                    'interest_type': 'theme',
                    'value': 'ev_battery',
                    'display_name': '전기차 & 배터리',
                },
            ]
        }
        response = auth_client.post(
            '/api/v1/users/interests/', payload, format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data['created']) == 1
        assert data['created'][0]['value'] == 'ev_battery'
        assert len(data['skipped']) == 1
        assert 'ai_semiconductor' in data['skipped']
        assert data['total_interests'] == 2  # 기존 1 + 신규 1

    def test_create_interests_response_fields(self, auth_client):
        """
        Given: 유효한 관심사 데이터
        When: POST /api/v1/users/interests/
        Then: created 항목에 필수 필드 포함
        """
        payload = {
            'interests': [
                {
                    'interest_type': 'theme',
                    'value': 'cloud_saas',
                    'display_name': '클라우드 & SaaS',
                }
            ]
        }
        response = auth_client.post(
            '/api/v1/users/interests/', payload, format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        created_item = response.json()['created'][0]

        assert 'id' in created_item
        assert 'interest_type' in created_item
        assert 'value' in created_item
        assert 'display_name' in created_item

    def test_create_interests_invalid_payload_missing_field(self, auth_client):
        """
        Given: interests 필드 없는 페이로드
        When: POST /api/v1/users/interests/
        Then: 400 Bad Request
        """
        payload = {'wrong_field': []}
        response = auth_client.post(
            '/api/v1/users/interests/', payload, format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_interests_empty_list(self, auth_client):
        """
        Given: interests 빈 리스트
        When: POST /api/v1/users/interests/
        Then: 400 Bad Request
        """
        payload = {'interests': []}
        response = auth_client.post(
            '/api/v1/users/interests/', payload, format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_interests_item_missing_value_skipped(self, auth_client):
        """
        Given: value 없는 항목과 유효한 항목 혼재
        When: POST /api/v1/users/interests/
        Then: 유효한 항목만 생성됨 (value 없는 항목은 skip)
        """
        payload = {
            'interests': [
                {
                    'interest_type': 'theme',
                    'value': '',          # 빈 value -> skip 처리
                    'display_name': '빈값',
                },
                {
                    'interest_type': 'theme',
                    'value': 'cybersecurity',
                    'display_name': '사이버보안',
                },
            ]
        }
        response = auth_client.post(
            '/api/v1/users/interests/', payload, format='json'
        )

        # 유효한 항목 1개만 생성됨
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data['created']) == 1
        assert data['created'][0]['value'] == 'cybersecurity'

    def test_create_interests_unauthenticated(self, api_client):
        """
        Given: 인증 없는 클라이언트
        When: POST /api/v1/users/interests/
        Then: 401 Unauthorized
        """
        payload = {
            'interests': [
                {'interest_type': 'theme', 'value': 'ai_semiconductor', 'display_name': 'AI'}
            ]
        }
        response = api_client.post(
            '/api/v1/users/interests/', payload, format='json'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_interests_persisted_in_db(self, auth_client, test_user):
        """
        Given: 유효한 관심사 데이터
        When: POST /api/v1/users/interests/
        Then: DB에 실제로 저장됨
        """
        payload = {
            'interests': [
                {
                    'interest_type': 'theme',
                    'value': 'gaming_metaverse',
                    'display_name': '게임 & 메타버스',
                }
            ]
        }
        auth_client.post('/api/v1/users/interests/', payload, format='json')

        assert UserInterest.objects.filter(
            user=test_user,
            interest_type='theme',
            value='gaming_metaverse',
        ).exists()


# ===== DELETE /api/v1/users/interests/{pk}/ =====

@pytest.mark.django_db
class TestUserInterestDeleteView:
    """관심사 삭제 API 테스트"""

    def test_delete_own_interest(self, auth_client, ai_semiconductor_interest):
        """
        Given: 본인 관심사
        When: DELETE /api/v1/users/interests/{pk}/
        Then: 204 No Content, DB에서 삭제됨
        """
        pk = ai_semiconductor_interest.id

        response = auth_client.delete(f'/api/v1/users/interests/{pk}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UserInterest.objects.filter(id=pk).exists()

    def test_delete_other_user_interest_returns_404(
        self, auth_client, other_user
    ):
        """
        Given: other_user의 관심사
        When: test_user(auth_client)가 DELETE 시도
        Then: 404 Not Found (다른 사용자 관심사에 접근 불가)
        """
        other_interest = UserInterest.objects.create(
            user=other_user,
            interest_type='theme',
            value='ai_semiconductor',
            display_name='AI & 반도체',
        )

        response = auth_client.delete(f'/api/v1/users/interests/{other_interest.id}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        # DB에 그대로 남아 있음
        assert UserInterest.objects.filter(id=other_interest.id).exists()

    def test_delete_nonexistent_interest_returns_404(self, auth_client):
        """
        Given: 존재하지 않는 pk
        When: DELETE /api/v1/users/interests/99999/
        Then: 404 Not Found
        """
        response = auth_client.delete('/api/v1/users/interests/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_interest_unauthenticated(
        self, api_client, ai_semiconductor_interest
    ):
        """
        Given: 인증 없는 클라이언트
        When: DELETE /api/v1/users/interests/{pk}/
        Then: 401 Unauthorized
        """
        response = api_client.delete(
            f'/api/v1/users/interests/{ai_semiconductor_interest.id}/'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # DB에 그대로 남아 있음
        assert UserInterest.objects.filter(id=ai_semiconductor_interest.id).exists()

    def test_delete_sector_interest(self, auth_client, tech_sector_interest):
        """
        Given: 섹터 타입 관심사
        When: DELETE
        Then: 204 No Content
        """
        pk = tech_sector_interest.id

        response = auth_client.delete(f'/api/v1/users/interests/{pk}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UserInterest.objects.filter(id=pk).exists()

    def test_delete_does_not_affect_other_interests(
        self, auth_client, ai_semiconductor_interest, tech_sector_interest
    ):
        """
        Given: 관심사 2개
        When: 1개 삭제
        Then: 나머지 1개는 유지됨
        """
        auth_client.delete(f'/api/v1/users/interests/{ai_semiconductor_interest.id}/')

        assert not UserInterest.objects.filter(id=ai_semiconductor_interest.id).exists()
        assert UserInterest.objects.filter(id=tech_sector_interest.id).exists()


# ===== 마커 설정 =====
pytestmark = pytest.mark.django_db
