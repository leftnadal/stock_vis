# Stock-Vis Test Suite

FMP Migration을 위한 포괄적인 테스트 전략

## 디렉토리 구조

```
tests/
├── unit/                    # 단위 테스트 (빠름, 외부 의존성 없음)
│   ├── providers/
│   │   ├── fmp/            # FMP Provider 테스트
│   │   └── alphavantage/   # Alpha Vantage Provider 테스트
│   └── test_*.py
│
├── integration/             # 통합 테스트 (DB, Cache)
│   └── test_*.py
│
├── e2e/                     # 종단 간 테스트 (전체 시스템)
│   └── test_*.py
│
├── scenarios/               # 시나리오 테스트
│   ├── test_happy_path.py
│   ├── test_error_cases.py
│   └── test_fallback_cases.py
│
├── fixtures/                # 테스트 데이터
│   ├── fmp/                # FMP API 응답 샘플
│   └── alphavantage/       # Alpha Vantage 응답 샘플
│
├── validators/              # 데이터 검증 유틸리티
│   └── data_validator.py
│
└── conftest.py              # pytest 공통 fixture
```

## 빠른 시작

### 1. 의존성 설치

```bash
# Poetry로 테스트 의존성 설치
poetry add --group dev pytest pytest-django pytest-mock pytest-cov pytest-xdist

# VCR (API 응답 녹화/재생)
poetry add --group dev pytest-vcr

# 추가 도구
poetry add --group dev flake8 mypy black isort
```

### 2. 테스트 실행

```bash
# 전체 테스트
poetry run pytest

# Unit 테스트만 (빠름)
poetry run pytest -m unit

# 커버리지와 함께
poetry run pytest --cov=API_request --cov-report=html
open htmlcov/index.html

# 특정 파일
poetry run pytest tests/unit/providers/fmp/test_fmp_processor.py

# Verbose 모드
poetry run pytest -v

# 병렬 실행 (4개 워커)
poetry run pytest -n 4
```

### 3. 커버리지 확인

```bash
# 커버리지 측정 (80% 미만 시 실패)
poetry run pytest --cov=API_request --cov-report=term-missing --cov-fail-under=80

# HTML 리포트 생성
poetry run coverage html
```

## 테스트 작성 가이드

### Given-When-Then 패턴

```python
def test_process_quote_valid_data(self, processor):
    """
    Given: 유효한 FMP Quote 응답
    When: process_quote() 호출
    Then: Django 모델 호환 형식으로 변환
    """
    # Given
    raw_data = [{"symbol": "AAPL", "price": 150.25}]

    # When
    result = processor.process_quote(raw_data)

    # Then
    assert result['symbol'] == 'AAPL'
    assert result['real_time_price'] == Decimal('150.25')
```

### Fixtures 사용

```python
def test_with_fixtures(self, stock, sample_quote_data):
    """conftest.py의 fixture 활용"""
    # stock: DB에 저장된 Stock 인스턴스
    # sample_quote_data: 샘플 Quote 데이터
    pass
```

### Mock 사용

```python
def test_api_call_mocked(self, mocker):
    """pytest-mock으로 외부 API 호출 Mock"""
    mock_client = mocker.patch('API_request.providers.fmp.client.FMPClient')
    mock_client.get_quote.return_value = [{"symbol": "AAPL", "price": 150.25}]

    # 테스트 로직
    result = mock_client.get_quote('AAPL')
    assert result[0]['price'] == 150.25
```

## 마커 (Markers)

```python
# Unit 테스트
@pytest.mark.unit
def test_something():
    pass

# Integration 테스트 (DB 필요)
@pytest.mark.django_db
def test_database_integration():
    pass

# 느린 테스트 (API 호출)
@pytest.mark.slow
def test_real_api():
    pass

# Provider 일관성 테스트
@pytest.mark.provider_consistency
def test_av_vs_fmp():
    pass
```

### 마커로 실행

```bash
# Unit 테스트만
pytest -m unit

# Integration 테스트 제외
pytest -m "not integration"

# 느린 테스트 제외
pytest -m "not slow"
```

## CI/CD

GitHub Actions에서 자동 실행됩니다:

```yaml
# .github/workflows/test-fmp-migration.yml
- name: Run tests
  run: |
    poetry run pytest --cov=API_request --cov-report=xml
    poetry run coverage report --fail-under=80
```

## 커버리지 목표

| 계층 | 목표 |
|-----|------|
| Provider 인터페이스 | 100% |
| FMP Client | 90% |
| FMP Processor | 95% |
| Provider Factory | 100% |
| StockService | 85% |
| **전체** | **80%+** |

## 문제 해결

### 테스트 실패 시

```bash
# 상세 트레이스백
pytest --tb=long

# pdb 디버거
pytest --pdb

# 로그 출력
pytest -s

# 첫 실패 시 중단
pytest -x
```

### 느린 테스트

```bash
# 느린 테스트 Top 10
pytest --durations=10

# 병렬 실행
pytest -n auto
```

## 참고 자료

- **전체 테스트 전략**: `docs/migration/test-strategy.md`
- **요약 가이드**: `docs/migration/TEST-STRATEGY-SUMMARY.md`
- **아키텍처 설계**: `docs/migration/architecture-design.md`
- **pytest 공식 문서**: https://docs.pytest.org/

---

**작성자**: @qa-architect
**날짜**: 2025-12-08
