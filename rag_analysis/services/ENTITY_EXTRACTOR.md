# Entity Extractor

사용자 질문에서 핵심 엔티티(종목명, 지표, 개념)를 추출하여 검색 정확도를 높입니다.

## 개요

Entity Extractor는 RAG 파이프라인의 전처리 단계로, 사용자 질문을 분석하여 다음 엔티티를 추출합니다:

- **stocks**: 종목명/종목코드 (예: AAPL, 삼성전자, TSMC)
- **metrics**: 재무/투자 지표 (예: PER, 매출, 영업이익)
- **concepts**: 투자 개념 (예: 저평가, 성장주, 리스크)
- **timeframe**: 시간 범위 (예: 2024년, 최근 3개월, Q3)

## 구조

```
EntityExtractor (Claude Haiku 기반)
    ↓
ExtractedEntities (TypedDict)
    ↓
EntityNormalizer (정규화)
    ↓
Normalized Results (표준 형식)
```

## 사용법

### 1. 기본 사용

```python
from rag_analysis.services import EntityExtractor, EntityNormalizer

# 인스턴스 생성
extractor = EntityExtractor()
normalizer = EntityNormalizer()

# 엔티티 추출
question = "AAPL과 TSLA의 PER과 매출을 비교해줘"
entities = await extractor.extract(question)

print(entities['stocks'])    # ['AAPL', 'TSLA']
print(entities['metrics'])   # ['PER', '매출']

# 정규화
normalized_stocks = normalizer.normalize_stocks(entities['stocks'])
print(normalized_stocks)     # ['AAPL', 'TSLA']

normalized_metrics = normalizer.normalize_metrics(entities['metrics'])
print(normalized_metrics)    # ['pe_ratio', 'revenue']
```

### 2. 폴백 모드

API 키가 없거나 LLM 호출 실패 시 자동으로 규칙 기반 추출로 전환됩니다:

```python
# API 키 없이 사용 (폴백 모드)
extractor = EntityExtractor()  # ANTHROPIC_API_KEY 없음

# 규칙 기반으로 추출
entities = await extractor.extract("AAPL과 TSLA 비교")
# 대문자 패턴, 한글 종목명, 지표 키워드로 추출
```

### 3. 한글 종목명 처리

```python
# 한글 종목명 → 심볼 변환
entities = await extractor.extract("삼성전자의 실적은?")
print(entities['stocks'])  # ['삼성전자']

normalized = normalizer.normalize_stocks(entities['stocks'])
print(normalized)          # ['005930.KS']
```

### 4. 지표 정규화

```python
# 한글 지표 → 필드명 변환
entities = await extractor.extract("매출과 영업이익 분석")
print(entities['metrics'])  # ['매출', '영업이익']

normalized = normalizer.normalize_metrics(entities['metrics'])
print(normalized)           # ['revenue', 'operating_income']
```

## API 참고

### EntityExtractor

#### `async extract(question: str) -> ExtractedEntities`

사용자 질문에서 엔티티를 추출합니다.

**Parameters:**
- `question` (str): 사용자 질문

**Returns:**
- `ExtractedEntities`: TypedDict
  - `stocks` (list[str]): 종목명/코드
  - `metrics` (list[str]): 재무 지표
  - `concepts` (list[str]): 투자 개념
  - `timeframe` (str | None): 시간 범위

### EntityNormalizer

#### `normalize_stocks(stocks: list[str]) -> list[str]`

종목명을 표준 심볼로 정규화합니다.

**Parameters:**
- `stocks` (list[str]): 추출된 종목명

**Returns:**
- `list[str]`: 정규화된 심볼 (대문자, 중복 제거)

#### `normalize_metrics(metrics: list[str]) -> list[str]`

지표를 표준 필드명으로 정규화합니다.

**Parameters:**
- `metrics` (list[str]): 추출된 지표

**Returns:**
- `list[str]`: 정규화된 필드명 (snake_case, 중복 제거)

## 매핑 테이블

### 종목명 매핑 (STOCK_MAPPING)

| 한글 종목명 | 심볼 |
|------------|------|
| 삼성전자 | 005930.KS |
| 삼성SDI | 006400.KS |
| SK하이닉스 | 000660.KS |
| NAVER/네이버 | 035420.KS |
| 카카오 | 035720.KS |
| TSMC | TSM |
| 애플 | AAPL |
| 엔비디아 | NVDA |

### 지표 매핑 (METRIC_MAPPING)

| 한글 지표 | 필드명 |
|----------|--------|
| 실적 | revenue, earnings |
| 매출 | revenue |
| 영업이익 | operating_income |
| 순이익 | net_income |
| PER | pe_ratio |
| PBR | pb_ratio |
| ROE | return_on_equity |
| EPS | earnings_per_share |

## 폴백 로직

LLM 호출 실패 시 다음 규칙으로 추출합니다:

1. **종목 추출**:
   - 대문자 패턴: `\b[A-Z]{2,5}\b` (예: AAPL, TSLA)
   - 한글 종목명: 미리 정의된 목록 매칭

2. **지표 추출**:
   - 키워드 매칭: '매출', '영업이익', 'PER', 'PBR' 등

3. **제한사항**:
   - concepts와 timeframe은 추출하지 못함
   - 복잡한 질문은 정확도가 떨어질 수 있음

## 성능 고려사항

### 토큰 사용량

- 모델: `claude-3-5-haiku-20241022` (빠르고 저렴)
- 최대 토큰: 200 (응답)
- 평균 응답 시간: 0.5초 미만

### 캐싱 권장

동일 질문에 대해 반복 호출 시 캐싱을 고려하세요:

```python
# Redis 캐싱 예제
from django.core.cache import cache

cache_key = f"entities:{hash(question)}"
entities = cache.get(cache_key)

if not entities:
    entities = await extractor.extract(question)
    cache.set(cache_key, entities, timeout=3600)  # 1시간
```

## 테스트

```bash
# 단위 테스트 실행
python -m pytest rag_analysis/tests/test_entity_extractor.py -v

# 예제 실행
python example/entity_extractor_example.py
```

## 확장 방법

### 1. 종목 매핑 추가

```python
# entity_extractor.py의 EntityNormalizer.STOCK_MAPPING에 추가
STOCK_MAPPING = {
    '삼성전자': '005930.KS',
    '새로운종목': 'SYMBOL',  # 추가
    # ...
}
```

### 2. 지표 매핑 추가

```python
# EntityNormalizer.METRIC_MAPPING에 추가
METRIC_MAPPING = {
    '매출': ['revenue'],
    '새지표': ['new_field'],  # 추가
    # ...
}
```

### 3. 프롬프트 커스터마이징

```python
# EntityExtractor.EXTRACTION_PROMPT 수정
EXTRACTION_PROMPT = """
[커스텀 프롬프트]

질문: {question}
JSON:"""
```

## 에러 핸들링

```python
try:
    entities = await extractor.extract(question)
except Exception as e:
    logger.error(f"Entity extraction failed: {e}")
    # 폴백 사용 또는 기본값 반환
    entities = {
        'stocks': [],
        'metrics': [],
        'concepts': [],
        'timeframe': None
    }
```

## 참고

- Phase 2 Week 1 구현
- Claude Haiku API 문서: https://docs.anthropic.com/claude/docs/models-overview
- 관련 파일:
  - `rag_analysis/services/entity_extractor.py`
  - `rag_analysis/tests/test_entity_extractor.py`
  - `example/entity_extractor_example.py`
