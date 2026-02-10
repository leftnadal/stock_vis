# Stock-Vis 테스트 가이드

## 테스트 구조

```
tests/
├── news/
│   ├── __init__.py
│   ├── test_news_entity_deduplication.py  # Entity 중복 방지 테스트
│   ├── test_providers.py                  # Provider 테스트 (예정)
│   └── test_aggregator.py                 # Aggregator 테스트 (예정)
├── stocks/
├── users/
└── conftest.py  # Pytest 설정
```

## 실행 방법

### 전체 테스트 실행

```bash
# pytest 설치
poetry add --dev pytest pytest-django pytest-cov

# 전체 테스트
pytest

# 커버리지와 함께
pytest --cov=news --cov-report=html
```

### 특정 테스트만 실행

```bash
# 뉴스 테스트만
pytest tests/news/

# Entity 중복 방지 테스트만
pytest tests/news/test_news_entity_deduplication.py

# 특정 테스트 클래스만
pytest tests/news/test_news_entity_deduplication.py::TestFinnhubEntityMapping

# 특정 테스트 함수만
pytest tests/news/test_news_entity_deduplication.py::TestFinnhubEntityMapping::test_parse_article_uses_related_field
```

### 테스트 옵션

```bash
# 상세 출력
pytest -v

# 실패한 테스트만 재실행
pytest --lf

# 특정 마커만 실행
pytest -m "django_db"

# 병렬 실행
pytest -n auto
```

## 중요 테스트 케이스

### 1. 뉴스 Entity 중복 방지

**파일**: `tests/news/test_news_entity_deduplication.py`

**목적**: 모든 종목에 동일한 뉴스가 표시되는 버그 재발 방지

**핵심 테스트**:

1. `test_parse_article_uses_related_field`
   - Finnhub API 응답의 `related` 필드 사용 확인
   - 요청 파라미터 `symbol` 무시 확인

2. `test_no_duplicate_entities_on_multiple_saves`
   - 같은 뉴스를 여러 번 저장해도 entity 중복 없음
   - M:N 관계 중복 방지 검증

3. `test_existing_article_entity_unchanged`
   - 기존 뉴스의 entity는 변경되지 않음
   - 데이터 무결성 확인

4. `test_multiple_symbol_fetches_no_cross_contamination`
   - 여러 종목 뉴스 수집 시 교차 오염 없음
   - 통합 테스트

**실행**:
```bash
pytest tests/news/test_news_entity_deduplication.py -v
```

### 2. API Provider 테스트 (예정)

**파일**: `tests/news/test_providers.py`

**테스트 항목**:
- Rate limiting 준수
- API 응답 파싱 정확성
- 에러 핸들링
- NULL 값 처리

### 3. Aggregator 테스트 (예정)

**파일**: `tests/news/test_aggregator.py`

**테스트 항목**:
- 중복 제거 로직
- 트랜잭션 처리
- 배치 저장 성능

## 테스트 작성 규칙

### 1. 테스트 이름 규칙

```python
def test_{component}_{action}_{expected_result}():
    """
    명확한 docstring 작성
    """
    pass

# 좋은 예
def test_parse_article_uses_related_field():
    """API 응답의 related 필드를 사용해야 함"""
    pass

# 나쁜 예
def test_parse():
    pass
```

### 2. Given-When-Then 패턴

```python
def test_example():
    """테스트 설명"""
    # Given: 초기 상태 설정
    provider = FinnhubNewsProvider(api_key="test")
    item = {'headline': '...', 'related': 'AAPL'}

    # When: 테스트 대상 실행
    article = provider._parse_article(item, symbol='TSLA')

    # Then: 결과 검증
    assert article.entities[0]['symbol'] == 'AAPL'
```

### 3. Fixture 활용

```python
@pytest.fixture
def provider():
    """재사용 가능한 Provider 인스턴스"""
    return FinnhubNewsProvider(api_key="test_key")

def test_something(provider):
    # provider fixture 사용
    result = provider.fetch_company_news('AAPL', ...)
```

### 4. Mock 사용

```python
@patch('news.providers.finnhub.requests.get')
def test_api_call(mock_get):
    """외부 API 호출 Mock"""
    mock_get.return_value.json.return_value = [...]
    mock_get.return_value.status_code = 200

    # 테스트 실행
```

## Django 테스트 설정

### pytest.ini

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_tests.py
addopts = --strict-markers --tb=short
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    django_db: marks tests that need database access
```

### conftest.py

```python
import pytest
from django.conf import settings

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """모든 테스트에 DB 접근 허용"""
    pass

@pytest.fixture
def api_client():
    """Django REST Framework API 클라이언트"""
    from rest_framework.test import APIClient
    return APIClient()
```

## CI/CD 통합

### GitHub Actions 예시

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        pip install poetry
        poetry install

    - name: Run tests
      run: |
        poetry run pytest --cov=. --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

## 커버리지 목표

| 모듈 | 목표 커버리지 | 현재 상태 |
|-----|-------------|----------|
| news/providers/ | 80% | ⏳ 진행 중 |
| news/services/ | 80% | ⏳ 진행 중 |
| news/models.py | 70% | ⏳ 진행 중 |
| news/api/views.py | 70% | ⏳ 진행 중 |

## 테스트 체크리스트

새 기능 추가 시:

- [ ] 단위 테스트 작성
- [ ] 통합 테스트 작성
- [ ] Edge case 테스트
- [ ] 에러 핸들링 테스트
- [ ] Mock을 통한 외부 의존성 격리
- [ ] 테스트 문서화 (docstring)
- [ ] CI/CD 파이프라인 통과 확인

버그 수정 시:

- [ ] 버그 재현 테스트 작성
- [ ] 수정 후 테스트 통과 확인
- [ ] 회귀 테스트 추가
- [ ] 관련 문서 업데이트

## 참고 자료

- [Pytest 공식 문서](https://docs.pytest.org/)
- [Django Testing](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [Bug Report: 뉴스 Entity 중복](bug-reports/news-system-duplicate-entity-bug.md)
