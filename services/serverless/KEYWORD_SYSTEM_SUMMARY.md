# Market Movers 키워드 생성 시스템 - 작업 요약

**작업 일시**: 2026-01-24
**담당 에이전트**: @rag-llm
**작업 범위**: LLM 프롬프트 및 응답 처리 로직 (tasks.py 제외)

---

## 작업 완료 내역

### 1. 프롬프트 시스템 (`keyword_prompts.py`)

**KeywordPromptBuilder**
- 5개 지표 해석 가이드 제공
- 한국어/영어 키워드 생성 지원
- 배치 프롬프트 (20개 종목 일괄 처리)
- 토큰 사용량 추정

**KeywordResponseParser**
- JSON 응답 파싱 및 유효성 검증
- 단일/배치 응답 처리
- 에러 핸들링

**핵심 기능**:
```python
# 시스템 프롬프트
system_prompt = builder.get_system_prompt()

# 배치 프롬프트 (20개 종목)
user_prompt = builder.build_batch_prompt(stocks)

# 토큰 추정
estimate = builder.estimate_tokens(num_stocks=20)
# {'input_tokens': 7200, 'output_tokens': 6000, 'total_tokens': 13200}
```

---

### 2. 키워드 생성 서비스 (`keyword_generator.py`)

**KeywordGeneratorService**
- Gemini 2.5 Flash 기반 LLM 호출
- 비동기 배치 처리 (20개 종목)
- 비용 추정 및 최적화
- Temperature: 0.3 (일관성)

**KeywordCacheService**
- 키워드 캐싱 인터페이스 (TODO: 구현)

**동기 래퍼**
- `generate_keywords_sync()`: Celery 태스크용

**핵심 기능**:
```python
# 배치 키워드 생성
service = KeywordGeneratorService(language='ko')
results = await service.generate_keywords_for_movers(
    mover_date=date(2026, 1, 24),
    mover_type='gainers',
    max_stocks=20
)

# 비용 추정
cost = service.estimate_batch_cost(num_stocks=20)
# {'total_cost_usd': 0.009360}
```

---

### 3. 컨텍스트 빌더 (`keyword_context.py`)

**KeywordContextBuilder**
- 압축된 컨텍스트 생성 (토큰 30% 절약)
- 배치 vs 개별 처리 비교
- 토큰 추정

**KeywordCompressor**
- 키워드 데이터 압축 (JSON 크기 40% 절약)
- 데이터베이스 저장 최적화

**핵심 기능**:
```python
# 배치 vs 개별 비교
comparison = KeywordContextBuilder.compare_batch_vs_individual(
    num_stocks=20
)
# 결과: 배치 처리 시 57% 비용 절약

# 키워드 압축
compressed = KeywordCompressor.compress_keywords(keywords)
```

---

### 4. 데이터베이스 모델 추가 (`models.py`)

**StockKeyword 모델**
```python
class StockKeyword(models.Model):
    symbol = models.CharField(max_length=10, db_index=True)
    company_name = models.CharField(max_length=255)
    date = models.DateField(db_index=True)

    keywords = models.JSONField(help_text="키워드 리스트 (3-5개)")

    llm_model = models.CharField(max_length=50, default="gemini-2.5-flash")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    expires_at = models.DateTimeField(db_index=True)  # 7일 TTL

    class Meta:
        unique_together = [['symbol', 'date']]
```

**특징**:
- FK 없이 symbol로 직접 매핑 (독립적 TTL 관리)
- 7일 자동 만료 (`expires_at`)
- 생성 상태 추적 (`status`)

---

### 5. 문서화

**KEYWORD_SYSTEM_README.md**
- 시스템 개요 및 아키텍처
- 사용법 (배치/단일 처리)
- 프롬프트 설계
- 토큰 최적화 전략
- 비용 분석 (연간 $10 미만)
- Celery 태스크 인터페이스 (@infra 참고용)

**keyword_example.py**
- 7가지 사용 예시
- 배치 생성, 단일 생성, 토큰 비교, DB 저장 등
- 일일 배치 시뮬레이션

---

## 토큰 최적화 성과

### 배치 처리 효과 (20개 종목)

| 방식 | 총 토큰 | 비용 | 절약률 |
|------|---------|------|--------|
| 개별 처리 | 26,000 | $0.0266 | - |
| 배치 처리 | 11,200 | $0.0094 | 57% |

### 일일 비용 (60개 종목)

- Gainers 20개 + Losers 20개 + Actives 20개
- 배치 3회: $0.0281/일
- **월간**: $0.84
- **연간**: $10.25

---

## 프롬프트 설계 핵심

### 1. 지표 해석 가이드 제공

```
RVOL: 2.0 이상 = 비정상적 관심도
Trend Strength: +0.7 이상 = 강한 상승
Sector Alpha: 양수 = 섹터 평균 초과
ETF Sync Rate: 0.8 이상 = 강한 동조
Volatility: 90 이상 = 매우 높은 변동성
```

### 2. Structured JSON 출력

```json
{
  "symbol": "AAPL",
  "keywords": [
    {"text": "폭발적 거래량", "category": "거래량", "confidence": 0.95},
    {"text": "강한 상승세", "category": "추세", "confidence": 0.90},
    {"text": "섹터 초과수익", "category": "섹터", "confidence": 0.85},
    {"text": "높은 변동성", "category": "변동성", "confidence": 0.80},
    {"text": "기술주 강세", "category": "특징", "confidence": 0.88}
  ],
  "summary": "폭발적 거래량과 강한 상승세를 보이는 기술주 강세 종목"
}
```

### 3. 5개 카테고리 균형

- 거래량, 추세, 섹터, 변동성, 특징
- 각 카테고리에서 최소 1개씩 키워드 선택

---

## 응답 파싱 전략

### 유효성 검증

1. **필수 필드**: `symbol`, `keywords`
2. **키워드 구조**: `text`, `category`, `confidence` (0.0~1.0)
3. **키워드 수**: 5-7개 권장
4. **카테고리 검증**: 5개 카테고리 중 선택

### 에러 핸들링

- JSON 파싱 실패 → None 반환
- 필수 필드 누락 → 해당 항목 스킵
- confidence 범위 초과 → 0.0~1.0 클램핑

---

## 캐싱 전략

### TTL 정책

- **StockKeyword**: 7일간 유지
- **expires_at**: 생성일 + 7일 (자동 설정)

### 캐시 플로우

```
요청 → StockKeyword 조회 (symbol + date)
    │
    ├─ 캐시 히트 → 반환
    │
    └─ 캐시 미스 → LLM 호출 → 저장 → 반환
```

### 만료 처리

```python
# Celery 태스크 (일일)
StockKeyword.objects.filter(
    expires_at__lt=timezone.now()
).delete()
```

---

## 다음 단계 (@infra 담당)

### 1. Celery 태스크 구현 (`serverless/tasks.py`)

```python
@shared_task
def generate_daily_keywords_batch():
    """
    일일 키워드 생성 태스크 (Gainers + Losers + Actives)
    """
    from datetime import date
    from .services.keyword_generator import generate_keywords_sync

    today = date.today()

    for mover_type in ['gainers', 'losers', 'actives']:
        results = generate_keywords_sync(
            mover_date=today,
            mover_type=mover_type,
            language='ko',
            max_stocks=20
        )

        # StockKeyword 모델에 저장
        for result in results:
            # ... 저장 로직
```

### 2. Celery Beat 스케줄 (`config/celery.py`)

```python
CELERY_BEAT_SCHEDULE = {
    'generate-market-movers-keywords': {
        'task': 'serverless.tasks.generate_daily_keywords_batch',
        'schedule': crontab(hour=8, minute=0),  # 매일 08:00 EST
        'options': {'expires': 3600}
    }
}
```

### 3. 만료 키워드 정리 태스크

```python
@shared_task
def cleanup_expired_keywords():
    """만료된 키워드 삭제"""
    from django.utils import timezone
    StockKeyword.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()
```

---

## 다음 단계 (@frontend 담당)

### API 엔드포인트 (선택)

```python
# GET /api/v1/serverless/keywords/<symbol>/
@api_view(['GET'])
def get_stock_keywords(request, symbol: str):
    keyword_obj = StockKeyword.objects.get(
        symbol=symbol.upper(),
        date=date.today(),
        status='completed'
    )
    return Response({
        'symbol': keyword_obj.symbol,
        'keywords': keyword_obj.keywords,
        'date': keyword_obj.date
    })
```

### UI 컴포넌트

```tsx
// MoverCard 컴포넌트에 키워드 배지 추가
<div className="keywords">
  {keywords.map(kw => (
    <Badge key={kw.text} variant="outline">
      {kw.text}
    </Badge>
  ))}
</div>
```

---

## 마이그레이션 필요

```bash
# StockKeyword 모델 추가
python manage.py makemigrations serverless
python manage.py migrate
```

---

## 테스트 실행 방법

```bash
# 예시 스크립트 실행 (Django 초기화 포함)
python serverless/services/keyword_example.py

# 특정 예시만 실행하려면 main() 함수 수정
```

---

## 참고 문서

- **상세 설명**: `serverless/services/KEYWORD_SYSTEM_README.md`
- **사용 예시**: `serverless/services/keyword_example.py`
- **RAG 시스템 참고**: `rag_analysis/services/llm_service.py`

---

## 비용 추정 요약

| 항목 | 값 |
|------|-----|
| 일일 비용 (60개 종목) | $0.028 |
| 월간 비용 (30일) | $0.84 |
| 연간 비용 (365일) | $10.25 |
| 배치 처리 절약률 | 57% |
| 토큰 압축률 | 30% |

---

## 협업 요청

| 에이전트 | 요청 사항 |
|---------|----------|
| @infra | Celery 태스크 구현 (일일 키워드 생성, 만료 정리) |
| @frontend | 키워드 UI 컴포넌트 (MoverCard 배지 추가) |
| @qa-architect | 시스템 리뷰 및 아키텍처 검토 |

---

**작업 완료**: 2026-01-24
**다음 작업**: @infra의 Celery 태스크 구현 대기 중
