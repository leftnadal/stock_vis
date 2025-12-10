# FMP Migration Test Strategy - Quick Reference

## 빠른 시작 가이드

### 테스트 실행 (로컬)

```bash
# 전체 테스트
poetry run pytest

# Unit 테스트만
poetry run pytest -m unit

# 커버리지와 함께
poetry run pytest --cov=API_request --cov-report=html

# 특정 Provider 테스트
poetry run pytest tests/unit/providers/fmp/
```

---

## 테스트 계층 구조

```
tests/
├── unit/                    # 단위 테스트 (빠름, 외부 의존성 없음)
│   ├── providers/
│   │   ├── fmp/
│   │   │   ├── test_fmp_client.py      # HTTP 요청
│   │   │   ├── test_fmp_processor.py   # 데이터 변환
│   │   │   └── test_fmp_provider.py    # Provider 구현
│   │   └── alphavantage/
│   ├── test_provider_factory.py        # Feature Flag
│   └── test_data_validation.py         # 검증 로직
│
├── integration/             # 통합 테스트 (DB, Cache)
│   ├── test_cached_provider.py         # 캐싱 동작
│   ├── test_stock_service.py           # Service + Provider + DB
│   └── test_provider_consistency.py    # AV vs FMP 일관성
│
├── e2e/                     # 종단 간 테스트 (전체 시스템)
│   └── test_stock_data_flow.py         # 사용자 시나리오
│
├── scenarios/               # 시나리오 테스트
│   ├── test_happy_path.py              # 정상 케이스
│   ├── test_error_cases.py             # 에러 케이스
│   ├── test_fallback_cases.py          # Fallback 동작
│   └── test_feature_flag_migration.py  # 점진적 전환
│
├── fixtures/                # 테스트 데이터
│   ├── fmp/
│   │   ├── quote_AAPL.json
│   │   ├── profile_AAPL.json
│   │   └── balance_sheet_AAPL.json
│   └── alphavantage/
│
└── conftest.py              # pytest 공통 fixture
```

---

## 커버리지 목표

| 계층 | 목표 | 우선순위 |
|-----|------|---------|
| Provider 인터페이스 | 100% | 높음 |
| FMP Client | 90% | 높음 |
| FMP Processor | 95% | 높음 |
| Provider Factory | 100% | 높음 |
| StockService | 85% | 높음 |
| **전체** | **80%+** | |

---

## 핵심 테스트 시나리오

### 1. Unit Tests (빠른 피드백)

```python
# FMP Client 테스트
def test_get_quote_success(mock_get, client):
    """실시간 주가 조회 성공"""
    mock_response.json.return_value = [{"symbol": "AAPL", "price": 150.25}]
    result = client.get_quote('AAPL')
    assert result[0]['symbol'] == 'AAPL'

# Processor 테스트
def test_process_quote_valid_data(processor):
    """데이터 변환 검증"""
    raw_data = [{"symbol": "AAPL", "price": 150.25}]
    result = processor.process_quote(raw_data)
    assert result['real_time_price'] == Decimal('150.25')
```

### 2. Integration Tests (시스템 통합)

```python
# Service + Provider + DB
@pytest.mark.django_db
def test_update_stock_data_creates_new_stock(mocker):
    """새 종목 생성 플로우"""
    mock_provider.get_company_profile.return_value = {...}
    stock = service.update_stock_data('AAPL')
    assert Stock.objects.filter(symbol='AAPL').exists()

# 캐싱 동작
def test_cache_hit_on_second_call(provider, mocker):
    """두 번째 호출 시 캐시 적중"""
    result1 = provider.get_quote('AAPL')
    result2 = provider.get_quote('AAPL')
    mock_client.assert_called_once()  # API 한 번만 호출
```

### 3. Provider Consistency (데이터 일관성)

```python
def test_quote_consistency(av_provider, fmp_provider):
    """Alpha Vantage vs FMP 데이터 일치"""
    av_result = av_provider.get_quote('AAPL')
    fmp_result = fmp_provider.get_quote('AAPL')

    # 가격 차이 1% 이내
    assert abs(av_result['price'] - fmp_result['price']) < av_result['price'] * 0.01
```

---

## Mock 전략

### 1. pytest-mock 사용 (Unit Tests)

```python
@pytest.fixture
def mock_fmp_client(mocker):
    """FMP Client Mock"""
    mock = mocker.MagicMock()
    mock.get_quote.return_value = [{"symbol": "AAPL", "price": 150.25}]
    return mock
```

### 2. pytest-vcr 사용 (Integration Tests)

```python
@vcr.use_cassette('tests/fixtures/vcr_cassettes/fmp_quote_AAPL.yaml')
def test_get_quote_real_api(client):
    """실제 API 호출 녹화/재생"""
    result = client.get_quote('AAPL')
    assert result[0]['symbol'] == 'AAPL'
```

### 3. Fixtures (E2E Tests)

```json
// tests/fixtures/fmp/quote_AAPL.json
[
  {
    "symbol": "AAPL",
    "price": 150.25,
    "change": 2.50,
    "changesPercentage": 1.69
  }
]
```

---

## 데이터 검증 기준

### 필수 필드 검증

```python
REQUIRED_FIELDS = {
    'quote': ['symbol', 'real_time_price', 'change', 'volume'],
    'company_profile': ['symbol', 'stock_name', 'sector', 'industry'],
    'balance_sheet': ['reported_date', 'total_assets', 'total_liabilities']
}
```

### 데이터 타입 검증

- Decimal: 가격, 금액 필드
- Integer: 거래량, 연도
- Date: 날짜 필드
- String: 심볼, 이름, 퍼센트

### 값 범위 검증

- 가격/거래량: 양수
- 퍼센트: -100% ~ +1000%
- 시가총액: 0 이상

---

## CI/CD 파이프라인

### GitHub Actions 워크플로우

```yaml
# .github/workflows/test-fmp-migration.yml

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run unit tests
        run: poetry run pytest tests/unit/ --cov=API_request

      - name: Run integration tests
        run: poetry run pytest tests/integration/

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### 로컬에서 CI와 동일하게 실행

```bash
# 1. 마이그레이션
poetry run python manage.py migrate --noinput

# 2. Linting
poetry run flake8 API_request/ stocks/ users/ tests/

# 3. Unit Tests
poetry run pytest tests/unit/ --cov=API_request --cov-report=xml

# 4. Integration Tests
poetry run pytest tests/integration/ --cov-append

# 5. 커버리지 확인 (80% 미만 시 실패)
poetry run coverage report --fail-under=80
```

---

## 테스트 디버깅

### 실패한 테스트만 재실행

```bash
poetry run pytest --lf
```

### Verbose 모드

```bash
poetry run pytest -vv
```

### pdb 디버거

```bash
poetry run pytest --pdb
```

### 느린 테스트 찾기

```bash
poetry run pytest --durations=10
```

---

## 다음 단계 (Phase별)

### Phase 1: 인프라 구축 (1주)
- [ ] `tests/` 디렉토리 구조 생성
- [ ] FMP API fixtures 수집 (VCR)
- [ ] pytest.ini, .coveragerc 설정
- [ ] conftest.py fixture 작성

### Phase 2: Unit Tests (1주)
- [ ] FMP Client 테스트
- [ ] FMP Processor 테스트
- [ ] Provider Factory 테스트
- [ ] DataValidator 테스트

### Phase 3: Integration Tests (1주)
- [ ] StockService 통합 테스트
- [ ] 캐싱 동작 테스트
- [ ] Provider 일관성 테스트

### Phase 4: CI/CD (1주)
- [ ] GitHub Actions 워크플로우
- [ ] Coverage 자동화
- [ ] Pre-commit hooks

---

## 체크리스트

### 테스트 작성 전
- [ ] fixture 데이터 준비
- [ ] Mock 전략 결정
- [ ] 검증 기준 정의

### 테스트 작성 중
- [ ] Given-When-Then 패턴 준수
- [ ] 명확한 테스트 이름
- [ ] 하나의 assertion에 하나의 개념

### 테스트 완료 후
- [ ] 커버리지 확인 (80%+)
- [ ] CI/CD 파이프라인 통과
- [ ] 코드 리뷰 요청

---

## 유용한 명령어 모음

```bash
# ===== 빠른 테스트 =====
pytest -m unit              # Unit 테스트만
pytest -m "not slow"        # 느린 테스트 제외
pytest -x                   # 첫 실패 시 중단

# ===== 커버리지 =====
pytest --cov=API_request --cov-report=html
open htmlcov/index.html

# ===== 디버깅 =====
pytest --pdb                # 실패 시 pdb
pytest -s                   # 로그 출력
pytest --tb=short           # 짧은 트레이스백

# ===== 성능 =====
pytest -n auto              # 병렬 실행
pytest --durations=10       # 느린 테스트 Top 10

# ===== CI 시뮬레이션 =====
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## 참고 자료

- **전체 문서**: `docs/migration/test-strategy.md`
- **아키텍처 설계**: `docs/migration/architecture-design.md`
- **API 매핑**: `docs/migration/api-mapping-table.md`
- **pytest 공식 문서**: https://docs.pytest.org/
- **pytest-django**: https://pytest-django.readthedocs.io/
- **pytest-vcr**: https://pytest-vcr.readthedocs.io/

---

**작성자**: @qa-architect
**날짜**: 2025-12-08
