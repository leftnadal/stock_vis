"""
뉴스 수집 카테고리 Admin API 테스트

TestAdminNewsCategoryView:
- GET /categories/ — 목록 조회
- POST /categories/ — 카테고리 생성 (sector, sub_sector, custom)
- 검증 에러 케이스

TestAdminNewsCategoryDetailView:
- PUT /categories/<id>/ — 수정
- DELETE /categories/<id>/ — 삭제
- 404 에러

TestAdminNewsSectorOptionsView:
- GET /sector-options/ — 섹터 옵션 목록
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from news.models import NewsCollectionCategory

User = get_user_model()


@pytest.mark.django_db
class TestAdminNewsCategoryView:
    """Admin 뉴스 카테고리 API 테스트 (목록/생성)"""

    @pytest.fixture(autouse=True)
    def setup(self, admin_user):
        """API Client + 인증 설정"""
        self.client = APIClient()
        self.client.force_authenticate(user=admin_user)
        self.url = '/api/v1/serverless/admin/dashboard/news/categories/'

    @pytest.fixture(autouse=True)
    def setup_sp500_constituents(self):
        """SP500Constituent 테스트 데이터 생성"""
        from stocks.models import SP500Constituent

        SP500Constituent.objects.create(
            symbol='AAPL',
            company_name='Apple Inc.',
            sector='Technology',
            sub_sector='Consumer Electronics',
            is_active=True,
        )
        SP500Constituent.objects.create(
            symbol='MSFT',
            company_name='Microsoft Corporation',
            sector='Technology',
            sub_sector='Software',
            is_active=True,
        )
        SP500Constituent.objects.create(
            symbol='JNJ',
            company_name='Johnson & Johnson',
            sector='Healthcare',
            sub_sector='Pharmaceuticals',
            is_active=True,
        )

    def test_get_categories_list(self):
        """Given: 카테고리 2개 존재
        When: GET /categories/
        Then: 카테고리 목록 반환 + resolved_symbol_count 포함"""
        NewsCollectionCategory.objects.create(
            name='Tech Sector',
            category_type='sector',
            value='Technology',
            is_active=True,
            priority='high',
            max_symbols=20,
        )
        NewsCollectionCategory.objects.create(
            name='Custom List',
            category_type='custom',
            value='AAPL, TSLA',
            is_active=True,
        )

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert 'categories' in response.data
        assert len(response.data['categories']) == 2

        # 첫 번째 카테고리 검증
        cat1 = response.data['categories'][0]
        assert cat1['name'] == 'Tech Sector'
        assert cat1['category_type'] == 'sector'
        assert cat1['value'] == 'Technology'
        assert cat1['is_active'] is True
        assert cat1['priority'] == 'high'
        assert cat1['resolved_symbol_count'] == 2  # AAPL, MSFT
        assert cat1['resolved_symbols_preview'] == ['AAPL', 'MSFT']

    def test_get_categories_empty_list(self):
        """Given: 카테고리 없음
        When: GET /categories/
        Then: 빈 배열 반환"""
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['categories'] == []

    def test_post_create_sector_category(self):
        """Given: sector 타입 데이터
        When: POST /categories/
        Then: 201 + 카테고리 생성"""
        data = {
            'name': 'Tech Sector',
            'category_type': 'sector',
            'value': 'Technology',
            'is_active': True,
            'priority': 'high',
            'max_symbols': 20,
        }

        response = self.client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Tech Sector'
        assert response.data['category_type'] == 'sector'
        assert response.data['value'] == 'Technology'
        assert response.data['resolved_symbol_count'] == 2  # AAPL, MSFT
        assert NewsCollectionCategory.objects.count() == 1

    def test_post_create_sub_sector_category(self):
        """Given: sub_sector 타입 데이터
        When: POST /categories/
        Then: 201 + 카테고리 생성"""
        data = {
            'name': 'Pharma Sub-Sector',
            'category_type': 'sub_sector',
            'value': 'Pharmaceuticals',
            'priority': 'medium',
        }

        response = self.client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['category_type'] == 'sub_sector'
        assert response.data['value'] == 'Pharmaceuticals'
        assert response.data['resolved_symbol_count'] == 1  # JNJ

    def test_post_create_custom_category(self):
        """Given: custom 타입 데이터
        When: POST /categories/
        Then: 201 + 카테고리 생성"""
        data = {
            'name': 'Custom Watchlist',
            'category_type': 'custom',
            'value': 'AAPL, TSLA, GOOG',
            'priority': 'low',
        }

        response = self.client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['category_type'] == 'custom'
        assert response.data['resolved_symbol_count'] == 3
        assert 'AAPL' in response.data['resolved_symbols_preview']

    def test_post_missing_name(self):
        """Given: name 필드 누락
        When: POST /categories/
        Then: 400 에러"""
        data = {
            'category_type': 'sector',
            'value': 'Technology',
        }

        response = self.client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert '이름은 필수' in response.data['error']

    def test_post_missing_value(self):
        """Given: value 필드 누락
        When: POST /categories/
        Then: 400 에러"""
        data = {
            'name': 'Test',
            'category_type': 'sector',
        }

        response = self.client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '값은 필수' in response.data['error']

    def test_post_invalid_category_type(self):
        """Given: 유효하지 않은 category_type
        When: POST /categories/
        Then: 400 에러"""
        data = {
            'name': 'Test',
            'category_type': 'invalid_type',
            'value': 'Technology',
        }

        response = self.client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '유효하지 않은 카테고리 타입' in response.data['error']

    def test_post_invalid_priority(self):
        """Given: 유효하지 않은 priority
        When: POST /categories/
        Then: 400 에러"""
        data = {
            'name': 'Test',
            'category_type': 'custom',
            'value': 'AAPL',
            'priority': 'ultra_high',
        }

        response = self.client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '유효하지 않은 우선순위' in response.data['error']

    def test_post_nonexistent_sector(self):
        """Given: 존재하지 않는 섹터
        When: POST /categories/
        Then: 400 에러"""
        data = {
            'name': 'Invalid Sector',
            'category_type': 'sector',
            'value': 'NonexistentSector',
        }

        response = self.client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '존재하지 않는 섹터' in response.data['error']

    def test_post_nonexistent_sub_sector(self):
        """Given: 존재하지 않는 서브섹터
        When: POST /categories/
        Then: 400 에러"""
        data = {
            'name': 'Invalid Sub-Sector',
            'category_type': 'sub_sector',
            'value': 'NonexistentSubSector',
        }

        response = self.client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '존재하지 않는 서브섹터' in response.data['error']

    def test_post_invalid_symbol_format(self):
        """Given: custom 타입 + 잘못된 심볼 형식
        When: POST /categories/
        Then: 400 에러"""
        data = {
            'name': 'Invalid Symbols',
            'category_type': 'custom',
            'value': 'AAPL, @#$%, TSLA',  # 특수문자 포함
        }

        response = self.client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '심볼 형식이 올바르지 않습니다' in response.data['error']

    def test_post_empty_custom_symbols(self):
        """Given: custom 타입 + 빈 심볼 목록
        When: POST /categories/
        Then: 400 에러"""
        data = {
            'name': 'Empty Symbols',
            'category_type': 'custom',
            'value': ',,,',  # 빈 항목만
        }

        response = self.client.post(self.url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '최소 1개 심볼 필요' in response.data['error']

    def test_unauthorized_access(self):
        """Given: 비인증 사용자
        When: GET /categories/
        Then: 403 Forbidden"""
        client_unauth = APIClient()
        response = client_unauth.get(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_access_forbidden(self):
        """Given: 일반 사용자 (non-admin)
        When: GET /categories/
        Then: 403 Forbidden"""
        user = User.objects.create_user(
            username='regular_user',
            email='user@example.com',
            password='password',
        )
        client_user = APIClient()
        client_user.force_authenticate(user=user)

        response = client_user.get(self.url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAdminNewsCategoryDetailView:
    """Admin 뉴스 카테고리 상세 API 테스트 (수정/삭제)"""

    @pytest.fixture(autouse=True)
    def setup(self, admin_user):
        """API Client + 인증 설정"""
        self.client = APIClient()
        self.client.force_authenticate(user=admin_user)

    @pytest.fixture(autouse=True)
    def setup_sp500_constituents(self):
        """SP500Constituent 테스트 데이터 생성"""
        from stocks.models import SP500Constituent

        SP500Constituent.objects.create(
            symbol='AAPL',
            company_name='Apple Inc.',
            sector='Technology',
            sub_sector='Software',
            is_active=True,
        )
        SP500Constituent.objects.create(
            symbol='JNJ',
            company_name='Johnson & Johnson',
            sector='Healthcare',
            sub_sector='Pharmaceuticals',
            is_active=True,
        )

    def test_put_update_category(self):
        """Given: 카테고리 존재
        When: PUT /categories/<id>/ (이름 변경)
        Then: 200 + 수정 완료"""
        category = NewsCollectionCategory.objects.create(
            name='Old Name',
            category_type='custom',
            value='AAPL',
            priority='medium',
        )

        url = f'/api/v1/serverless/admin/dashboard/news/categories/{category.id}/'
        data = {'name': 'New Name', 'priority': 'high'}

        response = self.client.put(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'New Name'
        assert response.data['priority'] == 'high'

        category.refresh_from_db()
        assert category.name == 'New Name'
        assert category.priority == 'high'

    def test_put_update_category_type_and_value(self):
        """Given: custom 타입 카테고리
        When: PUT /categories/<id>/ (sector로 변경)
        Then: 200 + 검증 후 수정"""
        category = NewsCollectionCategory.objects.create(
            name='Custom Cat',
            category_type='custom',
            value='AAPL',
        )

        url = f'/api/v1/serverless/admin/dashboard/news/categories/{category.id}/'
        data = {
            'category_type': 'sector',
            'value': 'Technology',
        }

        response = self.client.put(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['category_type'] == 'sector'
        assert response.data['value'] == 'Technology'
        assert response.data['resolved_symbol_count'] == 1  # AAPL

    def test_put_update_with_invalid_priority(self):
        """Given: 카테고리 존재
        When: PUT /categories/<id>/ (invalid priority)
        Then: 400 에러"""
        category = NewsCollectionCategory.objects.create(
            name='Test',
            category_type='custom',
            value='AAPL',
        )

        url = f'/api/v1/serverless/admin/dashboard/news/categories/{category.id}/'
        data = {'priority': 'invalid'}

        response = self.client.put(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '유효하지 않은 우선순위' in response.data['error']

    def test_put_update_with_nonexistent_sector(self):
        """Given: 카테고리 존재
        When: PUT /categories/<id>/ (존재하지 않는 섹터)
        Then: 400 에러"""
        category = NewsCollectionCategory.objects.create(
            name='Test',
            category_type='custom',
            value='AAPL',
        )

        url = f'/api/v1/serverless/admin/dashboard/news/categories/{category.id}/'
        data = {
            'category_type': 'sector',
            'value': 'InvalidSector',
        }

        response = self.client.put(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '존재하지 않는 섹터' in response.data['error']

    def test_put_nonexistent_category(self):
        """Given: 존재하지 않는 category_id
        When: PUT /categories/999/
        Then: 404 에러"""
        url = '/api/v1/serverless/admin/dashboard/news/categories/999/'
        data = {'name': 'Test'}

        response = self.client.put(url, data, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert '카테고리를 찾을 수 없습니다' in response.data['error']

    def test_delete_category(self):
        """Given: 카테고리 존재
        When: DELETE /categories/<id>/
        Then: 204 + 삭제 완료"""
        category = NewsCollectionCategory.objects.create(
            name='To Delete',
            category_type='custom',
            value='AAPL',
        )

        url = f'/api/v1/serverless/admin/dashboard/news/categories/{category.id}/'
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert NewsCollectionCategory.objects.count() == 0

    def test_delete_nonexistent_category(self):
        """Given: 존재하지 않는 category_id
        When: DELETE /categories/999/
        Then: 404 에러"""
        url = '/api/v1/serverless/admin/dashboard/news/categories/999/'
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert '카테고리를 찾을 수 없습니다' in response.data['error']

    def test_non_admin_cannot_update(self):
        """Given: 일반 사용자
        When: PUT /categories/<id>/
        Then: 403 Forbidden"""
        category = NewsCollectionCategory.objects.create(
            name='Test',
            category_type='custom',
            value='AAPL',
        )

        user = User.objects.create_user(
            username='regular_user',
            email='user@example.com',
            password='password',
        )
        client_user = APIClient()
        client_user.force_authenticate(user=user)

        url = f'/api/v1/serverless/admin/dashboard/news/categories/{category.id}/'
        data = {'name': 'Hacked'}

        response = client_user.put(url, data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAdminNewsSectorOptionsView:
    """Admin 섹터 옵션 API 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self, admin_user):
        """API Client + 인증 설정"""
        self.client = APIClient()
        self.client.force_authenticate(user=admin_user)
        self.url = '/api/v1/serverless/admin/dashboard/news/sector-options/'

    @pytest.fixture(autouse=True)
    def setup_sp500_constituents(self):
        """SP500Constituent 테스트 데이터 생성"""
        from stocks.models import SP500Constituent

        SP500Constituent.objects.create(
            symbol='AAPL',
            company_name='Apple Inc.',
            sector='Technology',
            sub_sector='Consumer Electronics',
            is_active=True,
        )
        SP500Constituent.objects.create(
            symbol='MSFT',
            company_name='Microsoft Corporation',
            sector='Technology',
            sub_sector='Software',
            is_active=True,
        )
        SP500Constituent.objects.create(
            symbol='JNJ',
            company_name='Johnson & Johnson',
            sector='Healthcare',
            sub_sector='Pharmaceuticals',
            is_active=True,
        )
        SP500Constituent.objects.create(
            symbol='INACTIVE',
            company_name='Inactive Corp',
            sector='Technology',
            sub_sector='Software',
            is_active=False,  # 비활성
        )

    def test_get_sector_options(self):
        """Given: SP500Constituent 데이터 존재
        When: GET /sector-options/
        Then: 섹터 + 서브섹터 목록 반환 (활성만)"""
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert 'sectors' in response.data
        assert 'sub_sectors' in response.data

        # 섹터 검증 (Technology, Healthcare)
        sectors = response.data['sectors']
        assert len(sectors) == 2
        tech_sector = next(s for s in sectors if s['value'] == 'Technology')
        assert tech_sector['count'] == 2  # AAPL, MSFT (INACTIVE 제외)

        healthcare_sector = next(s for s in sectors if s['value'] == 'Healthcare')
        assert healthcare_sector['count'] == 1

        # 서브섹터 검증
        sub_sectors = response.data['sub_sectors']
        assert len(sub_sectors) == 3  # Consumer Electronics, Software, Pharmaceuticals
        software_sub = next(s for s in sub_sectors if s['value'] == 'Software')
        assert software_sub['sector'] == 'Technology'
        assert software_sub['count'] == 1  # MSFT만 (INACTIVE 제외)

    def test_get_sector_options_empty(self):
        """Given: SP500Constituent 없음
        When: GET /sector-options/
        Then: 빈 배열 반환"""
        from stocks.models import SP500Constituent
        SP500Constituent.objects.all().delete()

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['sectors'] == []
        assert response.data['sub_sectors'] == []

    def test_non_admin_forbidden(self):
        """Given: 일반 사용자
        When: GET /sector-options/
        Then: 403 Forbidden"""
        user = User.objects.create_user(
            username='regular_user',
            email='user@example.com',
            password='password',
        )
        client_user = APIClient()
        client_user.force_authenticate(user=user)

        response = client_user.get(self.url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
