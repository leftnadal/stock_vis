# Strategy Analysis (전략 분석실)

> AI 기반 투자 전략 분석 및 백테스팅

## 📋 상태

**개발 예정 (Planned)**

이 페이지는 향후 개발 예정입니다.

---

## 계획 중인 기능

### 1. RAG 기반 AI 분석

현재 `rag_analysis/` 앱이 구현되어 있으며, 다음 기능을 제공합니다:

**Knowledge Basket (KB) 시스템**
- 투자 지식 저장소
- 종목별 분석 리포트
- 전략 패턴 학습

**파이프라인 (Phase 3 완료)**
- Semantic Cache: 유사 질문 캐싱
- Complexity Classifier: 질문 복잡도 분류
- Token Budget Manager: 토큰 예산 관리
- Adaptive LLM: 복잡도 기반 모델 선택
- Cost Tracker: 비용 추적

**API 엔드포인트:**
```bash
POST /api/v1/rag/analyze/                      # AI 분석 실행
GET  /api/v1/rag/monitoring/usage/?hours=24    # 사용량 통계
GET  /api/v1/rag/monitoring/cost/              # 비용 요약
GET  /api/v1/rag/monitoring/cache/             # 캐시 통계
```

**코드 위치:**
- Backend: `rag_analysis/`
- 파이프라인: `rag_analysis/pipeline_final.py`
- 모니터링: `rag_analysis/monitoring.py`

---

## 데이터베이스 스키마

### rag_analysis 앱 (현재 구현)

**DataBasket (지식 바구니)**
```python
class DataBasket(models.Model):
    BASKET_TYPES = [
        ('stock', 'Stock Analysis'),
        ('sector', 'Sector Analysis'),
        ('strategy', 'Strategy Analysis'),
    ]

    basket_id = models.CharField(max_length=50, unique=True, db_index=True)
    basket_type = models.CharField(max_length=20, choices=BASKET_TYPES)
    symbol = models.CharField(max_length=10, null=True, db_index=True)
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_items = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)

    class Meta:
        ordering = ['-updated_at']
```

**KnowledgeItem (지식 아이템)**
```python
class KnowledgeItem(models.Model):
    ITEM_TYPES = [
        ('fundamental', 'Fundamental Data'),
        ('technical', 'Technical Analysis'),
        ('news', 'News Article'),
        ('sentiment', 'Sentiment Analysis'),
        ('report', 'Analysis Report'),
    ]

    basket = models.ForeignKey(DataBasket, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    content = models.TextField()
    metadata = models.JSONField(default=dict)

    # 벡터 임베딩 (향후 Semantic Search용)
    embedding = models.JSONField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    token_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['basket', 'item_type']),
        ]
```

**QueryCache (쿼리 캐시 - Semantic Cache)**
```python
class QueryCache(models.Model):
    query_hash = models.CharField(max_length=64, unique=True, db_index=True)
    query_text = models.TextField()
    query_embedding = models.JSONField(null=True)

    # 응답
    response = models.TextField()
    basket_id = models.CharField(max_length=50, null=True)
    pipeline_version = models.CharField(max_length=20, default='final')

    # 메타데이터
    similarity_threshold = models.DecimalField(max_digits=3, decimal_places=2, default=0.85)
    hit_count = models.IntegerField(default=0)
    last_hit_at = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['query_hash']),
            models.Index(fields=['expires_at']),
        ]
```

**LLMUsageLog (비용 추적)**
```python
class LLMUsageLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    pipeline_version = models.CharField(max_length=20)
    complexity = models.CharField(max_length=20)  # simple, moderate, complex

    # 토큰 사용량
    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()
    total_tokens = models.IntegerField()

    # 비용 (USD)
    cost = models.DecimalField(max_digits=10, decimal_places=6)

    # 쿼리 정보
    query_text = models.TextField()
    basket_id = models.CharField(max_length=50, null=True)
    cache_hit = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['pipeline_version', 'complexity']),
        ]
```

### 모델 관계

```
DataBasket (1) ──────── (N) KnowledgeItem
     │
     │ (basket_id 참조)
     │
     └──────────────────── QueryCache
                             └─ basket_id (문자열 참조)

LLMUsageLog (독립)
     └─ basket_id (문자열 참조)
```

### 인덱스 전략

1. **Basket 조회**:
   - `DataBasket`: `basket_id` unique 인덱스
   - `DataBasket`: `symbol` 인덱스 (종목별 조회)

2. **KnowledgeItem 조회**:
   - `KnowledgeItem`: `(basket, item_type)` 복합 인덱스
   - 예: 특정 basket의 fundamental 데이터만 조회

3. **Semantic Cache**:
   - `QueryCache`: `query_hash` unique 인덱스 (빠른 캐시 조회)
   - `QueryCache`: `expires_at` 인덱스 (만료된 캐시 정리)

4. **비용 추적**:
   - `LLMUsageLog`: `timestamp` 역순 인덱스 (최신 로그 조회)
   - `LLMUsageLog`: `(pipeline_version, complexity)` 복합 인덱스 (통계)

---

### 2. 백테스팅 엔진 (개발 예정)

**목표:**
- 과거 데이터 기반 전략 검증
- 다양한 지표 조합 테스트
- 수익률/MDD/Sharpe Ratio 계산

**계획 중인 기능:**
- Market Movers 5개 지표 기반 전략 백테스팅
- 섹터 로테이션 전략 시뮬레이션
- 거시지표 기반 타이밍 전략

### 3. 전략 라이브러리 (개발 예정)

**목표:**
- 검증된 퀀트 전략 템플릿
- 커뮤니티 공유 전략
- 전략 성과 랭킹

---

## 투자 지식

### 백테스팅 주의사항

**1. 생존 편향 (Survivorship Bias)**
- 상장폐지 종목 제외 시 수익률 과대평가
- 전체 유니버스 데이터 필요

**2. 룩어헤드 바이어스 (Look-ahead Bias)**
- 미래 정보 사용 금지
- 실시간 거래 가능한 데이터만 사용

**3. 과최적화 (Over-fitting)**
- 과거에만 최적화된 전략
- Out-of-sample 검증 필수

**4. 거래비용**
- 수수료, 슬리피지 고려
- 유동성 제약 반영

### 전략 평가 지표

| 지표 | 의미 | 목표 |
|------|------|------|
| CAGR | 연평균 복리 수익률 | 15%+ |
| MDD | 최대 낙폭 | -20% 이내 |
| Sharpe Ratio | 위험 대비 수익 | 1.5 이상 |
| Win Rate | 승률 | 55%+ |
| Profit Factor | 총 이익 / 총 손실 | 1.5 이상 |

---

## 다음 단계

현재 RAG 분석 시스템이 구축되어 있으므로, 다음 단계로 진행할 수 있습니다:

1. **Frontend UI 개발**: 전략 분석 대시보드
2. **백테스팅 엔진**: Market Movers 지표 기반
3. **전략 템플릿**: 검증된 전략 라이브러리
4. **성과 추적**: 실전 투자 vs 백테스트 비교

자세한 내용은 개발 완료 후 업데이트됩니다.
