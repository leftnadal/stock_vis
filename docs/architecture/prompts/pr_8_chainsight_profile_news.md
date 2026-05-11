# PR-8: CompanyRevenueStructure + CompanyChainProfile + ChainNewsEvent

## 참고 문서

- `docs/architecture/claude-code-reference-doc.md` — 섹션 7
- PR-6, PR-7 완료 전제: chainsight 앱에 6개 모델 존재

## 작업 범위

1. CompanyRevenueStructure 모델 (Tier B — 10-K 파싱 기반)
2. CompanyChainProfile 모델 (집약 테이블 → 그래프 DB 투영 원천)
3. ChainNewsEvent 모델 (Chain Sight 전용 뉴스 — 동시출현/파급 추적)
4. admin 등록
5. chainsight/models/**init**.py 최종 정리 (9개 모델 전체 export)

## 주의사항

- 기존 stocks.StockNews는 수정하지 않음
- ChainNewsEvent는 별도 뉴스 테이블 (Chain Sight 전용)
- CompanyChainProfile은 다른 모든 chainsight 모델의 요약
- ChainNewsEvent.duplicate_of_id는 self FK

---

## 1. CompanyRevenueStructure

SEC 10-K 파싱 + LLM 보조로 채워지는 매출 구조 데이터.

```python
# chainsight/models/revenue_structure.py

class CompanyRevenueStructure(models.Model):
    """매출 구조 (Revenue DNA). SEC 10-K 파싱 + LLM 보조."""

    EXTRACTION_METHOD_CHOICES = [
        ('fmp_api', 'FMP API'),
        ('10k_llm', '10-K LLM Parsing'),
        ('manual', 'Manual'),
    ]
    BUSINESS_MODEL_CHOICES = [
        ('b2b', 'B2B'), ('b2c', 'B2C'), ('mixed', 'Mixed'), ('unknown', 'Unknown'),
    ]
    CONCENTRATION_CHOICES = [
        ('high', 'High'), ('medium', 'Medium'), ('low', 'Low'),
    ]

    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='revenue_structure',
    )

    # 사업 부문별 매출
    segments = models.JSONField(
        default=list,
        help_text='[{"name":"iPhone","revenue_pct":52,"trend":"stable"}, ...]'
    )

    # 지역별 매출
    geographic_revenue = models.JSONField(
        default=list,
        help_text='[{"region":"Americas","pct":42}, ...]'
    )

    # 고객 집중도 (10-K 공시)
    major_customers = models.JSONField(
        default=list,
        help_text='[{"customer":"Apple","revenue_pct":22}, ...]'
    )
    customer_concentration_risk = models.CharField(
        max_length=10, blank=True, choices=CONCENTRATION_CHOICES
    )

    # B2B vs B2C
    business_model_type = models.CharField(
        max_length=20, blank=True, choices=BUSINESS_MODEL_CHOICES
    )

    # 원자재 의존도
    commodity_exposures = models.JSONField(
        default=list,
        help_text='[{"commodity":"lithium","exposure":"high","context":"battery"}, ...]'
    )

    # 파싱 메타
    source_filing = models.CharField(max_length=100, blank=True)
    extraction_method = models.CharField(
        max_length=20, blank=True, choices=EXTRACTION_METHOD_CHOICES
    )
    extraction_confidence = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True,
        help_text='0.0 ~ 1.0'
    )
    last_parsed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_revenue_structure'

    def __str__(self):
        return f"{self.symbol_id}: {len(self.segments)} segments"
```

## 2. CompanyChainProfile

위 모든 chainsight 모델의 요약. 그래프 DB 노드 속성 투영 원천.

```python
# chainsight/models/chain_profile.py

from django.contrib.postgres.fields import ArrayField

class CompanyChainProfile(models.Model):
    """
    Chain Sight 기업 프로파일 집약.
    모든 chainsight 테이블 + validation.CategoryScore에서 요약.
    그래프 DB 노드 속성으로 투영되는 원천 (AGE MVP, 추후 backend-swappable).
    """
    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='chain_profile',
    )

    # sensitivity 요약
    rate_sensitivity = models.CharField(max_length=10, blank=True)
    forex_sensitivity = models.CharField(max_length=10, blank=True)
    commodity_sensitivity = models.CharField(max_length=10, blank=True)
    regulation_type = models.CharField(max_length=50, blank=True)
    beta = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)

    # growth_stage 요약
    growth_stage = models.CharField(max_length=30, blank=True)
    revenue_cagr_3y = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    # capital_dna 요약
    capital_type = models.CharField(max_length=30, blank=True)
    net_cash_position = models.BigIntegerField(null=True, blank=True)

    # insider_signal 요약
    smart_money_signal = models.CharField(max_length=20, blank=True)

    # revenue_structure 요약
    top_segment = models.CharField(max_length=100, blank=True)
    top_segment_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    china_revenue_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    customer_concentration_risk = models.CharField(max_length=10, blank=True)
    business_model_type = models.CharField(max_length=20, blank=True)

    # narrative 요약
    primary_narrative = models.CharField(max_length=100, blank=True)
    theme_tags = ArrayField(
        models.CharField(max_length=50),
        default=list, blank=True,
    )
    narrative_sentiment = models.CharField(max_length=10, blank=True)

    # validation score 요약
    score_profitability = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    score_growth = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    score_financial_structure = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    overall_grade = models.CharField(max_length=5, blank=True)

    # 메타
    profile_completeness = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True,
        help_text='0.0~1.0 채워진 필드 비율'
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_chain_profile'

    def __str__(self):
        return f"{self.symbol_id}: {self.growth_stage} / {self.overall_grade}"
```

## 3. ChainNewsEvent

Chain Sight 전용 뉴스. 기존 stocks.StockNews와 별도.

```python
# chainsight/models/news_event.py

from django.contrib.postgres.fields import ArrayField

class ChainNewsEvent(models.Model):
    """
    Chain Sight 전용 뉴스 이벤트.
    기존 stocks.StockNews와 별도 — 동시출현, 파급 시간차 추적용.
    """
    SOURCE_CHOICES = [
        ('marketaux', 'MarketAux'),
        ('finnhub', 'Finnhub'),
        ('eodhd', 'EODHD'),
    ]
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'), ('neutral', 'Neutral'), ('negative', 'Negative'),
    ]
    IMPORTANCE_CHOICES = [
        ('high', 'High'), ('medium', 'Medium'), ('low', 'Low'),
    ]

    symbol = models.ForeignKey(
        'stocks.Stock', on_delete=models.PROTECT,
        to_field='symbol', db_column='symbol',
        related_name='chain_news_events',
    )

    # 원본
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    source_id = models.CharField(max_length=255)
    title = models.TextField()
    summary = models.TextField(blank=True)
    url = models.TextField(blank=True)
    published_at = models.DateTimeField(db_index=True)

    # 감성
    sentiment_score = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    sentiment_label = models.CharField(max_length=10, blank=True, choices=SENTIMENT_CHOICES)

    # 이벤트 태깅
    event_type = models.CharField(max_length=50, blank=True)
    event_importance = models.CharField(max_length=10, blank=True, choices=IMPORTANCE_CHOICES)

    # Chain Sight 전용: 동시출현
    co_mentioned_symbols = ArrayField(
        models.CharField(max_length=10),
        default=list, blank=True,
        help_text='이 기사에서 함께 언급된 다른 종목들'
    )

    # 중복 처리
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='duplicates',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chainsight_news_event'
        unique_together = ['source', 'source_id']
        indexes = [
            models.Index(fields=['symbol', '-published_at']),
            models.Index(fields=['symbol', 'event_type']),
            models.Index(fields=['-published_at']),
        ]

    def __str__(self):
        return f"{self.symbol_id} [{self.source}] {self.title[:50]}"
```

## 4. chainsight/models/**init**.py 최종

```python
from .sensitivity import CompanySensitivityProfile
from .growth_stage import CompanyGrowthStage
from .capital_dna import CompanyCapitalDNA
from .insider_signal import CompanyInsiderSignal
from .narrative_tag import CompanyNarrativeTag
from .event_reaction import CompanyEventReaction
from .revenue_structure import CompanyRevenueStructure
from .chain_profile import CompanyChainProfile
from .news_event import ChainNewsEvent

__all__ = [
    'CompanySensitivityProfile',
    'CompanyGrowthStage',
    'CompanyCapitalDNA',
    'CompanyInsiderSignal',
    'CompanyNarrativeTag',
    'CompanyEventReaction',
    'CompanyRevenueStructure',
    'CompanyChainProfile',
    'ChainNewsEvent',
]
```

## 완료 기준

- [ ] CompanyRevenueStructure 모델 + 마이그레이션
- [ ] CompanyChainProfile 모델 + 마이그레이션
- [ ] ChainNewsEvent 모델 + 마이그레이션 (self FK, ArrayField 확인)
- [ ] admin 등록 (3개)
- [ ] chainsight/models/**init**.py에 9개 모델 전체 export
- [ ] 기존 stocks.StockNews 수정 없음 확인
