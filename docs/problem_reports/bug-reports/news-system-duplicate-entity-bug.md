# 뉴스 시스템 중복 Entity 버그 리포트

## 문제 요약
모든 종목(TSLA, AAPL, GOOGL, IREN 등)에서 동일한 뉴스가 표시되는 심각한 버그가 발견되었습니다.

**발견 일자**: 2025-12-08
**심각도**: 🔴 Critical
**영향 범위**: 전체 뉴스 시스템

---

## 근본 원인 분석

### 1. Finnhub Provider - 잘못된 Entity 매핑 (finnhub.py:171-213)

**문제 코드**:
```python
def _parse_article(self, item: Dict, symbol: str = None, category: str = 'general'):
    entities = []
    if symbol:
        entities.append({
            'symbol': symbol.upper(),  # ❌ 요청한 종목을 무조건 추가
            ...
        })
```

**문제점**:
- API 요청 시 전달한 `symbol` 파라미터를 entity로 저장
- Finnhub API 응답의 `related` 필드를 무시
- 예: TSLA 뉴스를 조회하면, 실제로는 NVDA 관련 뉴스인데 TSLA entity가 붙음

**Finnhub API 응답 구조**:
```json
{
  "headline": "Nvidia announces new AI chip",
  "related": "NVDA",  // 실제 관련 종목
  "summary": "...",
  "datetime": 1605543180
}
```

### 2. Aggregator - 기존 뉴스에 Entity 중복 추가 (aggregator.py:158-192)

**문제 코드**:
```python
def _save_articles(self, articles):
    for raw_article in articles:
        article, created = self._save_article(raw_article)

        if created:
            saved_count += 1
        elif article:
            updated_count += 1
        else:
            skipped_count += 1
            continue

        self._save_entities(article, raw_article.entities)  # ❌ 항상 실행
```

**문제점**:
- 새 뉴스(`created=True`)뿐만 아니라 기존 뉴스(`created=False`)에도 entity를 추가
- 같은 뉴스 기사를 여러 종목에서 조회할 때마다 새로운 entity가 계속 추가됨
- 예: "Nvidia AI chip" 뉴스가 TSLA, AAPL, GOOGL 조회 시마다 각각 entity로 추가

**데이터베이스 상태 예시**:
```
NewsArticle: "Nvidia announces new AI chip"
├─ NewsEntity: NVDA (원본)
├─ NewsEntity: TSLA (잘못 추가됨)
├─ NewsEntity: AAPL (잘못 추가됨)
└─ NewsEntity: GOOGL (잘못 추가됨)
```

### 3. NULL 값 처리 문제 (aggregator.py:270)

**문제 코드**:
```python
'exchange': entity_data.get('exchange', ''),  # ❌ None이 그대로 전달됨
```

**문제점**:
- Marketaux API가 `exchange=None` 반환 시
- `get('exchange', '')` 호출해도 None이 반환됨 (dict에 key가 있으면 기본값 사용 안함)
- DB `NOT NULL` 제약조건 위반으로 IntegrityError 발생

---

## 적용된 수정

### 1. Finnhub Provider 수정 (finnhub.py:201-213)

```python
def _parse_article(self, item: Dict, symbol: str = None, category: str = 'general'):
    entities = []

    # ✅ API가 반환한 실제 관련 종목만 사용
    related = item.get('related', '')
    if related:
        related_symbol = related.upper()
        entities.append({
            'symbol': related_symbol,
            'entity_name': '',
            'entity_type': 'equity',
            'source': 'finnhub',
            'match_score': Decimal('1.00000')
        })

    return RawNewsArticle(
        ...
        entities=entities,
        ...
    )
```

**변경점**:
- 요청 파라미터 `symbol` 대신 응답의 `related` 필드 사용
- API가 제공하는 실제 관련 종목만 entity로 저장

### 2. Aggregator 수정 (aggregator.py:177-186)

```python
def _save_articles(self, articles):
    for raw_article in articles:
        article, created = self._save_article(raw_article)

        if created:
            saved_count += 1
            # ✅ 새 뉴스인 경우에만 entity 저장
            self._save_entities(article, raw_article.entities)
        elif article:
            updated_count += 1
            # ✅ 기존 뉴스는 entity 추가하지 않음
        else:
            skipped_count += 1
            continue
```

**변경점**:
- `created=True`인 경우에만 `_save_entities()` 호출
- 기존 뉴스에는 entity를 추가하지 않아 중복 방지

### 3. NULL 값 처리 수정 (aggregator.py:270)

```python
'exchange': entity_data.get('exchange') or '',  # ✅ None을 빈 문자열로 변환
```

**변경점**:
- `or ''` 연산자로 None을 빈 문자열로 변환
- DB NOT NULL 제약조건 만족

---

## 검증 방법

### 1. 단위 테스트

```python
def test_finnhub_parse_article_uses_related_field():
    """Finnhub parser가 related 필드를 사용하는지 확인"""
    provider = FinnhubNewsProvider(api_key="test")

    item = {
        'headline': 'Nvidia AI chip',
        'related': 'NVDA',
        'summary': '...',
        'datetime': 1605543180
    }

    # TSLA로 요청했지만 related 필드(NVDA)를 사용해야 함
    article = provider._parse_article(item, symbol='TSLA')

    assert len(article.entities) == 1
    assert article.entities[0]['symbol'] == 'NVDA'  # TSLA가 아님


def test_aggregator_no_duplicate_entities():
    """기존 뉴스에 entity가 중복 추가되지 않는지 확인"""
    service = NewsAggregatorService()

    # 첫 번째 저장 (NVDA)
    raw_article = RawNewsArticle(
        url='https://example.com/nvda-news',
        title='Nvidia AI chip',
        entities=[{'symbol': 'NVDA', ...}],
        ...
    )
    service._save_articles([raw_article])

    # 두 번째 저장 시도 (같은 URL, 다른 entity)
    raw_article.entities = [{'symbol': 'TSLA', ...}]
    service._save_articles([raw_article])

    # Entity는 1개만 있어야 함
    article = NewsArticle.objects.get(url='https://example.com/nvda-news')
    assert article.entities.count() == 1
    assert article.entities.first().symbol == 'NVDA'
```

### 2. 통합 테스트

```bash
# 여러 종목 뉴스 수집
python manage.py shell
>>> from news.services import NewsAggregatorService
>>> service = NewsAggregatorService()
>>> service.fetch_and_save_company_news('TSLA', days=7)
>>> service.fetch_and_save_company_news('AAPL', days=7)
>>> service.fetch_and_save_company_news('GOOGL', days=7)

# 각 종목별 뉴스가 다른지 확인
>>> from news.models import NewsArticle
>>> tsla_news = NewsArticle.objects.filter(entities__symbol='TSLA')
>>> aapl_news = NewsArticle.objects.filter(entities__symbol='AAPL')
>>>
>>> # 교집합이 없거나 매우 적어야 함
>>> common = tsla_news & aapl_news
>>> assert common.count() < tsla_news.count() * 0.1  # 10% 미만
```

### 3. API 테스트

```bash
# TSLA 뉴스 조회
curl http://localhost:8000/api/v1/news/stock/TSLA/?refresh=true

# AAPL 뉴스 조회
curl http://localhost:8000/api/v1/news/stock/AAPL/?refresh=true

# 결과 비교 - 뉴스 제목이 달라야 함
```

---

## 영향 범위

### 직접 영향
- `news/providers/finnhub.py`: Entity 매핑 로직
- `news/services/aggregator.py`: Entity 저장 로직
- `news/models.py`: NewsEntity M:N 관계

### 간접 영향
- `news/api/views.py`: 종목별 뉴스 조회 결과
- Frontend: 종목 상세 페이지 뉴스 탭
- 캐시: `news:stock:{symbol}` 캐시 무효화 필요

---

## 데이터 정리 작업

기존에 잘못 저장된 entity를 정리해야 합니다:

```python
# 관리자 스크립트 (management command)
from django.core.management.base import BaseCommand
from news.models import NewsEntity, NewsArticle

class Command(BaseCommand):
    help = '잘못된 NewsEntity 정리'

    def handle(self, *args, **options):
        # 중복 entity 삭제 로직
        for article in NewsArticle.objects.all():
            entities = article.entities.all()

            if entities.count() > 3:  # 비정상적으로 많은 entity
                # Finnhub/Marketaux에서 실제로 제공한 entity만 유지
                valid_entities = entities.filter(
                    source__in=['finnhub', 'marketaux']
                )[:1]

                # 나머지 삭제
                invalid_entities = entities.exclude(
                    id__in=valid_entities.values_list('id', flat=True)
                )
                invalid_count = invalid_entities.count()
                invalid_entities.delete()

                self.stdout.write(
                    f"Article {article.id}: {invalid_count} entities removed"
                )
```

실행:
```bash
python manage.py cleanup_news_entities
```

---

## 재발 방지 대책

### 1. 코드 레벨

```python
# Provider 추상 클래스에 검증 추가
class BaseNewsProvider:
    def validate_entities(self, entities: List[Dict]) -> bool:
        """Entity 데이터 검증"""
        for entity in entities:
            # 필수 필드 체크
            if not entity.get('symbol'):
                logger.warning(f"Entity missing symbol: {entity}")
                return False

            # source 필드 필수
            if not entity.get('source'):
                logger.warning(f"Entity missing source: {entity}")
                return False

        return True
```

### 2. 테스트 강화

```python
# tests/news/test_providers.py
class FinnhubProviderTestCase(TestCase):
    """Finnhub Provider 테스트"""

    def test_parse_article_always_uses_api_response_data(self):
        """파라미터가 아닌 API 응답 데이터만 사용"""
        # 요청 symbol과 응답 related가 다른 경우
        ...

    def test_parse_article_no_entity_if_no_related_field(self):
        """related 필드 없으면 entity 없어야 함"""
        ...

# tests/news/test_aggregator.py
class AggregatorTestCase(TestCase):
    """Aggregator 테스트"""

    def test_no_duplicate_entities_on_multiple_fetches(self):
        """여러 번 조회해도 entity 중복 없음"""
        ...

    def test_existing_article_entity_unchanged(self):
        """기존 뉴스의 entity는 변경되지 않음"""
        ...
```

### 3. 모니터링

```python
# 이상 탐지 로직
def detect_entity_anomalies():
    """비정상적인 entity 관계 탐지"""
    from news.models import NewsArticle

    # 1. Entity가 5개 이상인 뉴스
    excessive_entities = NewsArticle.objects.annotate(
        entity_count=Count('entities')
    ).filter(entity_count__gte=5)

    if excessive_entities.exists():
        logger.warning(
            f"{excessive_entities.count()} articles with 5+ entities"
        )

    # 2. 같은 뉴스가 10개 이상 종목에 연결
    widespread_news = NewsArticle.objects.annotate(
        entity_count=Count('entities')
    ).filter(entity_count__gte=10)

    if widespread_news.exists():
        logger.warning(
            f"{widespread_news.count()} articles linked to 10+ symbols"
        )
```

---

## 교훈 (Lessons Learned)

### 1. API 응답 데이터 우선 원칙
- 요청 파라미터가 아닌 **API 응답에서 제공한 실제 데이터를 사용**해야 함
- 예: Finnhub `related` 필드, Marketaux `entities` 배열

### 2. M:N 관계 저장 시 중복 체크
- `update_or_create()`만으로 중복 방지가 불충분
- **새 레코드 생성 시에만 관계 추가**하는 로직 필요

### 3. NULL 값 처리 주의
- `dict.get(key, default)`는 key가 존재하고 값이 None이면 default를 사용하지 않음
- `or` 연산자로 명시적 변환 필요: `get(key) or default`

### 4. 외부 API 통합 체크리스트
- [ ] API 응답 구조 정확히 파악
- [ ] 요청 파라미터 vs 응답 데이터 구분
- [ ] NULL/빈 값 처리 로직
- [ ] 중복 저장 방지 로직
- [ ] 단위/통합 테스트 작성
- [ ] 이상 탐지 모니터링

---

## 관련 파일

- `news/providers/finnhub.py` (Line 171-231)
- `news/providers/marketaux.py` (Entity 파싱)
- `news/services/aggregator.py` (Line 158-294)
- `news/models.py` (NewsArticle, NewsEntity)
- `news/api/views.py` (종목별 뉴스 조회)

---

## 참고 문서

- Finnhub API Docs: https://finnhub.io/docs/api/company-news
- Django M:N Relations: https://docs.djangoproject.com/en/5.0/topics/db/examples/many_to_many/
- Alpha Vantage API Best Practices (유사 케이스)
