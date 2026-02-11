# Chain Sight Phase 5: Gemini LLM 관계 추출 상세 설계

## 1. 개요

### 1.1 목표
뉴스/SEC 보고서에서 Gemini 2.5 Flash를 활용하여 복잡한 기업 간 관계를 자동 추출하고, 기존 Regex 기반 Phase 4 Supply Chain Parser를 보강합니다.

### 1.2 추출할 관계 타입

| 관계 타입 | 설명 | 트리거 예시 | 우선순위 |
|----------|------|------------|---------|
| `ACQUIRED` | 인수/합병 | "NVDA acquired Mellanox for $6.9B" | P0 |
| `INVESTED_IN` | 투자 관계 | "SoftBank invested $1B in ARM" | P0 |
| `PARTNER_OF` | 파트너십 | "AAPL partnered with Goldman Sachs" | P0 |
| `SPIN_OFF` | 분사 | "eBay spun off PayPal" | P1 |
| `SUED_BY` | 소송 관계 | "Epic Games sued Apple" | P1 |
| `SUPPLIED_BY` | 공급망 (보강) | "TSMC to build chips for NVIDIA" | P0 |
| `CUSTOMER_OF` | 고객 관계 (보강) | "Microsoft is Apple's largest customer" | P0 |

### 1.3 예상 비용
- **월간 비용**: ~$5 (버퍼 포함)
- Gemini 2.5 Flash: $0.075/1M input, $0.30/1M output
- 일일 뉴스 처리: ~10개 (Pre-filter 후)
- SEC 10-K 처리: 월 1회 상위 100개 종목

---

## 2. 아키텍처 설계

### 2.1 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Sources                                 │
├───────────────┬───────────────┬──────────────────────────────────┤
│ NewsArticle   │ SEC 10-K      │ SEC 8-K (향후)                   │
│ (Marketaux)   │ (Item 1A)     │ (Material Events)                │
└───────┬───────┴───────┬───────┴────────────────────┬─────────────┘
        │               │                             │
        ▼               ▼                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              RelationExtractionService                          │
│  ┌──────────────────┐  ┌──────────────────────────────────┐    │
│  │ Regex Filters    │  │ LLM Extractor (Gemini 2.5 Flash) │    │
│  │ (Pre-filter)     │  │                                   │    │
│  └────────┬─────────┘  │  - 관계 추출 프롬프트            │    │
│           │            │  - JSON 구조화 출력               │    │
│           │            │  - 신뢰도 계산                    │    │
│           ▼            └──────────────┬───────────────────┘    │
│   ┌──────────────────┐                │                         │
│   │ Candidate Filter │ ◄──────────────┘                         │
│   │ - 중복 제거      │                                          │
│   │ - 심볼 매칭      │                                          │
│   │ - 신뢰도 필터    │                                          │
│   └────────┬─────────┘                                          │
└────────────┼────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LLMExtractedRelation Model                     │
│  - source_symbol, target_symbol, relation_type                  │
│  - confidence, evidence, llm_model, extracted_at                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│               PostgreSQL + Neo4j Sync                           │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │ StockRelationship   │  │ Neo4jChainSightService          │  │
│  │ (PostgreSQL)        │  │ (Graph DB)                      │  │
│  └─────────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 처리 플로우

```
1. 뉴스 수집 (기존 Marketaux 파이프라인)
   └─> NewsArticle 저장

2. 관계 추출 후보 선별 (Regex Pre-filter)
   └─> 관계 키워드 포함 뉴스만 LLM으로 전송
   └─> 비용 절감 (전체 뉴스의 ~20%만 LLM 호출)

3. Gemini LLM 관계 추출
   └─> 구조화된 JSON 출력
   └─> 심볼 매칭 (Stock DB)
   └─> 신뢰도 계산

4. 중복 제거 및 저장
   └─> LLMExtractedRelation 모델 저장
   └─> StockRelationship 업데이트
   └─> Neo4j 그래프 동기화

5. TTL 관리
   └─> 30일 후 LLMExtractedRelation 만료
   └─> StockRelationship은 유지 (last_verified_at 갱신)
```

---

## 3. 데이터 모델

### 3.1 신규 모델: `LLMExtractedRelation`

```python
class LLMExtractedRelation(models.Model):
    """
    LLM이 추출한 기업 간 관계 (Phase 5)

    뉴스/SEC 문서에서 Gemini로 추출한 관계를 저장합니다.
    """
    RELATION_TYPES = [
        ('ACQUIRED', '인수/합병'),
        ('INVESTED_IN', '투자'),
        ('PARTNER_OF', '파트너십'),
        ('SPIN_OFF', '분사'),
        ('SUED_BY', '소송'),
        ('SUPPLIED_BY', '공급'),
        ('CUSTOMER_OF', '고객'),
    ]

    CONFIDENCE_LEVELS = [
        ('high', 'High'),        # LLM 확신도 0.9+
        ('medium', 'Medium'),    # LLM 확신도 0.7-0.9
        ('low', 'Low'),          # LLM 확신도 0.5-0.7
    ]

    SOURCE_TYPES = [
        ('news', '뉴스'),
        ('sec_10k', 'SEC 10-K'),
        ('sec_8k', 'SEC 8-K'),
    ]

    # 관계 정보
    source_symbol = models.CharField(max_length=10, db_index=True)
    target_symbol = models.CharField(max_length=10, db_index=True)
    relation_type = models.CharField(max_length=20, choices=RELATION_TYPES)

    # 추출 컨텍스트
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    source_id = models.CharField(max_length=100)  # 뉴스 UUID 또는 SEC accession number
    evidence = models.TextField()  # 추출 근거 문장
    context = models.JSONField(default=dict)  # 추가 컨텍스트 (금액, 날짜 등)

    # LLM 메타데이터
    confidence = models.CharField(max_length=10, choices=CONFIDENCE_LEVELS)
    llm_confidence_score = models.DecimalField(max_digits=4, decimal_places=3)
    llm_model = models.CharField(max_length=50, default='gemini-2.5-flash')
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    extraction_time_ms = models.IntegerField(null=True, blank=True)

    # 검증 상태
    is_verified = models.BooleanField(default=False)
    is_synced_to_graph = models.BooleanField(default=False)

    # TTL
    expires_at = models.DateTimeField(db_index=True)
    extracted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'serverless_llm_extracted_relation'
        unique_together = [['source_symbol', 'target_symbol', 'relation_type', 'source_id']]
```

### 3.2 StockRelationship 확장

```python
# 신규 관계 타입 추가
RELATIONSHIP_TYPES = [
    # 기존
    ('PEER_OF', '경쟁사'),
    ('SAME_INDUSTRY', '동일 산업'),
    ('CO_MENTIONED', '뉴스 동시언급'),
    ('HAS_THEME', '테마 공유'),
    ('SUPPLIED_BY', '공급사'),
    ('CUSTOMER_OF', '고객사'),
    # Phase 5 신규
    ('ACQUIRED', '인수/합병'),
    ('INVESTED_IN', '투자'),
    ('PARTNER_OF', '파트너십'),
    ('SPIN_OFF', '분사'),
    ('SUED_BY', '소송'),
]

# 신규 소스 프로바이더
SOURCE_PROVIDERS = [
    # 기존
    ('finnhub', 'Finnhub Peers API'),
    ('fmp', 'FMP Company Profile'),
    ('news', 'NewsEntity Co-mention'),
    ('sec_10k', 'SEC 10-K'),
    # Phase 5 신규
    ('llm_news', 'LLM News Extraction'),
    ('llm_sec', 'LLM SEC Extraction'),
]
```

---

## 4. 비용 최적화 전략

### 4.1 Pre-filter (Regex 기반)

LLM 호출 전 관계 키워드가 포함된 텍스트만 선별합니다.

```python
RELATION_KEYWORDS = {
    'en': [
        # ACQUIRED
        r'\b(acquire[ds]?|acquisition|merger|merged|bought|takeover)\b',
        # INVESTED_IN
        r'\b(invest(?:ed|ment|s)?|fund(?:ed|ing)?|stake|equity)\b',
        # PARTNER_OF
        r'\b(partner(?:ship|ed)?|collaborat(?:e|ion|ed)|joint venture|alliance)\b',
        # SPIN_OFF
        r'\b(spin[\s-]?off|spinoff|spun off|divest(?:ed|iture)?)\b',
        # SUED_BY
        r'\b(su(?:e[ds]?|ing)|lawsuit|litigation|legal action|antitrust)\b',
        # SUPPLIED_BY / CUSTOMER_OF
        r'\b(supplier?|supplies?|customer|client|vendor|contract)\b',
    ],
    'ko': [
        r'(인수|합병|매각|투자|파트너|제휴|협력|분사|소송|공급|고객)',
    ]
}
```

### 4.2 배치 처리

```python
BATCH_SIZE = 5  # 뉴스 5개를 하나의 요청으로

# 예상 토큰
# - 시스템 프롬프트: ~500 토큰
# - 뉴스 5개 (평균 500토큰/개): ~2,500 토큰
# - 출력 (관계 5개): ~500 토큰
# - 총: ~3,500 토큰/배치
```

### 4.3 비용 추정

```
일일 처리량:
- Marketaux 뉴스: ~50개/일
- Pre-filter 통과: ~10개/일 (20%)
- 배치 수: 2개/일 (5개씩)

뉴스 월간 비용:
- LLM 호출: 60개/월 (30일 × 2배치)
- 토큰: ~210,000/월
- 예상 비용: ~$0.07/월

SEC 10-K 처리 (월 1회):
- 상위 100개 종목 × Item 1A (~20,000 토큰)
- 토큰: ~2M/월
- 예상 비용: ~$3.15/월

총 예상 비용: ~$3.22/월 (버퍼 포함 ~$5/월)
```

---

## 5. 프롬프트 설계

### 5.1 시스템 프롬프트 (영어)

```
You are an expert financial analyst specializing in corporate relationship extraction.

## Task
Extract corporate relationships from the given news article or SEC filing text.

## Relationship Types
- ACQUIRED: Company A acquired/merged with Company B
- INVESTED_IN: Company A invested in Company B
- PARTNER_OF: Partnership, collaboration, joint venture
- SPIN_OFF: Company A spun off from Company B
- SUED_BY: Legal dispute between companies
- SUPPLIED_BY: Company A supplies to Company B
- CUSTOMER_OF: Company A is a customer of Company B

## Rules
1. Only extract relationships with EXPLICITLY mentioned company names
2. Both companies must be identifiable (ticker symbols preferred)
3. Do NOT infer relationships not stated in the text
4. Confidence score 0.0-1.0 based on clarity of the statement
5. Extract the exact sentence as evidence

## Output Format (JSON)
{
  "relationships": [
    {
      "source": "NVDA",
      "source_name": "NVIDIA Corporation",
      "target": "MLNX",
      "target_name": "Mellanox Technologies",
      "type": "ACQUIRED",
      "confidence": 0.95,
      "evidence": "NVIDIA acquired Mellanox for $6.9 billion.",
      "context": {
        "amount": "$6.9 billion",
        "date": "2020-04-27"
      }
    }
  ]
}

## Important
- Return ONLY valid JSON (no markdown, no explanation)
- If no relationships found, return {"relationships": []}
- Maximum 5 relationships per text
```

---

## 6. 서비스 구현

### 6.1 주요 서비스 클래스

```
serverless/services/
├── llm_relation_extractor.py       # LLM 관계 추출 서비스 (신규)
├── relation_extraction_prompts.py  # 프롬프트 빌더/파서 (신규)
├── relation_pre_filter.py          # Regex Pre-filter (신규)
├── symbol_matcher.py               # 회사명-티커 매칭 (신규)
└── neo4j_chain_sight_service.py    # 기존 (확장)
```

### 6.2 LLMRelationExtractor

```python
class LLMRelationExtractor:
    """Gemini LLM 기반 관계 추출 서비스"""

    MODEL = "gemini-2.5-flash"
    MAX_TOKENS = 2000
    TEMPERATURE = 0.3
    BATCH_SIZE = 5

    def extract_from_news(self, news: NewsArticle) -> List[LLMExtractedRelation]:
        """단일 뉴스에서 관계 추출"""

    def extract_from_10k(self, text: str, symbol: str) -> List[LLMExtractedRelation]:
        """SEC 10-K에서 관계 추출 (Phase 4 보강)"""

    def extract_batch(self, news_list: List[NewsArticle]) -> Dict[str, Any]:
        """배치 관계 추출"""
```

---

## 7. Celery 태스크

### 7.1 신규 태스크

```python
@shared_task
def extract_relations_from_news_batch(news_ids: List[str]):
    """뉴스 배치에서 관계 추출"""

@shared_task
def extract_relations_from_10k(symbol: str):
    """SEC 10-K에서 관계 추출 (Phase 4 보강)"""

@shared_task
def sync_llm_relations_to_graph():
    """미동기화 LLM 관계를 Neo4j로 동기화"""

@shared_task
def cleanup_expired_llm_relations():
    """만료된 LLMExtractedRelation 정리"""
```

### 7.2 Celery Beat 스케줄

```python
CELERY_BEAT_SCHEDULE = {
    'extract-relations-from-daily-news': {
        'task': 'serverless.tasks.process_daily_news_relations',
        'schedule': crontab(hour=23, minute=0),  # 23:00 EST
    },
    'sync-llm-relations-to-graph': {
        'task': 'serverless.tasks.sync_llm_relations_to_graph',
        'schedule': crontab(hour=2, minute=0),  # 02:00 EST
    },
    'cleanup-expired-llm-relations': {
        'task': 'serverless.tasks.cleanup_expired_llm_relations',
        'schedule': crontab(hour=3, minute=0),  # 03:00 EST
    },
}
```

---

## 8. API 엔드포인트

```python
# LLM 관계 추출 (Phase 5)
path('llm-relations/extract', views.trigger_relation_extraction),
path('llm-relations/stock/<str:symbol>', views.get_llm_relations),
path('llm-relations/stats', views.get_llm_relation_stats),
```

### 응답 예시

```json
{
    "symbol": "NVDA",
    "relations": [
        {
            "target_symbol": "MLNX",
            "target_name": "Mellanox Technologies",
            "relation_type": "ACQUIRED",
            "confidence": "high",
            "evidence": "NVIDIA acquired Mellanox for $6.9 billion in April 2020.",
            "context": {"amount": "$6.9 billion", "date": "2020-04"}
        }
    ],
    "total_count": 1
}
```

---

## 9. 구현 파일 목록

### 9.1 신규 파일

| 파일 | 역할 |
|-----|------|
| `serverless/services/llm_relation_extractor.py` | LLM 관계 추출 메인 서비스 |
| `serverless/services/relation_extraction_prompts.py` | 프롬프트 빌더/파서 |
| `serverless/services/relation_pre_filter.py` | Regex Pre-filter |
| `serverless/services/symbol_matcher.py` | 회사명-티커 매칭 |
| `serverless/migrations/00XX_llm_extracted_relation.py` | 마이그레이션 |
| `tests/serverless/test_llm_relation_extractor.py` | 단위 테스트 |
| `tests/serverless/test_relation_pre_filter.py` | Pre-filter 테스트 |
| `tests/serverless/test_symbol_matcher.py` | 매칭 테스트 |

### 9.2 수정 파일

| 파일 | 변경 내용 |
|-----|----------|
| `serverless/models.py` | `LLMExtractedRelation` 추가, `StockRelationship` 확장 |
| `serverless/tasks.py` | Celery 태스크 추가 |
| `serverless/urls.py` | API 엔드포인트 추가 |
| `serverless/views.py` | 뷰 추가 |
| `serverless/services/neo4j_chain_sight_service.py` | 관계 타입 확장 |
| `config/celery.py` | Beat 스케줄 추가 |

---

## 10. 구현 순서 (6주)

### Week 1: 기반 구축
- [ ] `LLMExtractedRelation` 모델 생성 및 마이그레이션
- [ ] `StockRelationship` 관계 타입 확장
- [ ] Neo4j 관계 타입 확장
- [ ] 테스트 데이터 준비

### Week 2: 핵심 서비스 구현
- [ ] `RelationPreFilter` 구현
- [ ] `SymbolMatcher` 구현
- [ ] `RelationExtractionPromptBuilder` 구현
- [ ] `RelationExtractionResponseParser` 구현

### Week 3: LLM 통합
- [ ] `LLMRelationExtractor` 메인 서비스 구현
- [ ] Gemini API 동기 호출 통합
- [ ] 배치 처리 로직 구현
- [ ] 에러 처리 및 재시도 로직

### Week 4: 파이프라인 구축
- [ ] Celery 태스크 구현
- [ ] Celery Beat 스케줄 설정
- [ ] PostgreSQL/Neo4j 동기화 로직
- [ ] API 엔드포인트 구현

### Week 5: 테스트 및 최적화
- [ ] 단위 테스트 작성 (목표: 90% 커버리지)
- [ ] 통합 테스트 작성
- [ ] 비용 모니터링 구현
- [ ] 성능 최적화

### Week 6: 문서화 및 배포
- [ ] 설계 문서 완성
- [ ] CLAUDE.md 업데이트
- [ ] 로드맵 업데이트
- [ ] 프로덕션 배포

---

## 11. 리스크 및 완화 전략

| 리스크 | 완화 전략 |
|--------|----------|
| LLM 비용 초과 | Pre-filter로 호출 수 제한, 월간 모니터링 |
| LLM 응답 불일치 | JSON 파싱 복구 로직, Fallback 처리 |
| Rate Limit | 지수 백오프, 배치 처리 |
| 잘못된 관계 추출 | confidence 필터, 수동 검증 플래그 |
| 심볼 매칭 실패 | 하드코딩 매핑 확장, Stock DB 조회 |

---

## 12. 성공 지표

| 지표 | 목표 |
|-----|------|
| 월간 비용 | < $5 |
| 관계 추출 정확도 | > 85% (high confidence) |
| Pre-filter 효율 | > 80% 비용 절감 |
| 일일 추출 관계 수 | ~10-20개 |
| Neo4j 동기화 성공률 | > 99% |
