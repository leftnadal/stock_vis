# PR-7: CompanyInsiderSignal + CompanyNarrativeTag + CompanyEventReaction

## 참고 문서

- `docs/architecture/claude-code-reference-doc.md` — 섹션 7
- PR-6 완료 전제: chainsight 앱 존재

## 작업 범위

1. CompanyInsiderSignal 모델 (Tier A — Finnhub API 기반)
2. CompanyNarrativeTag 모델 (Tier B — 뉴스 + LLM 태깅)
3. CompanyEventReaction 모델 (Tier B — 뉴스 + 주가 교차분석)
4. admin 등록

## 주의사항

- 기존 코드 수정 없음
- CompanyEventReaction은 symbol + event_type 복합 unique
- CompanyNarrativeTag.theme_tags는 PostgreSQL ArrayField 사용

---

## 1. CompanyInsiderSignal

참고 문서 섹션 7의 필드 그대로 구현. `from django.contrib.postgres.fields import ArrayField` 필요 시 사용.

```python
# chainsight/models/insider_signal.py

class CompanyInsiderSignal(models.Model):
    """내부자/기관 행동 신호. Finnhub Form 4 + 13F 기반."""

    INSIDER_SIGNAL_CHOICES = [
        ('strong_buy', 'Strong Buy'), ('buy', 'Buy'),
        ('neutral', 'Neutral'),
        ('sell', 'Sell'), ('strong_sell', 'Strong Sell'),
    ]
    HOLDER_ACTION_CHOICES = [
        ('accumulating', 'Accumulating'),
        ('stable', 'Stable'),
        ('distributing', 'Distributing'),
    ]
    CHANGE_CHOICES = [
        ('increasing', 'Increasing'),
        ('stable', 'Stable'),
        ('decreasing', 'Decreasing'),
    ]
    SMART_MONEY_CHOICES = [
        ('bullish', 'Bullish'), ('neutral', 'Neutral'), ('bearish', 'Bearish'),
    ]

    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='insider_signal',
    )

    # 내부자 매매
    insider_buy_count_90d = models.IntegerField(default=0)
    insider_sell_count_90d = models.IntegerField(default=0)
    insider_net_amount_90d = models.BigIntegerField(null=True, blank=True)
    insider_signal = models.CharField(max_length=20, blank=True, choices=INSIDER_SIGNAL_CHOICES)

    # 기관
    institutional_ownership_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    institutional_change_qoq = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    top_holder_action = models.CharField(max_length=20, blank=True, choices=HOLDER_ACTION_CHOICES)

    # 공매도
    short_interest_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    short_interest_change = models.CharField(max_length=20, blank=True, choices=CHANGE_CHOICES)
    days_to_cover = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # 종합
    smart_money_signal = models.CharField(max_length=20, blank=True, choices=SMART_MONEY_CHOICES)

    data_freshness = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_insider_signal'

    def __str__(self):
        return f"{self.symbol_id}: smart_money={self.smart_money_signal}"
```

## 2. CompanyNarrativeTag

```python
# chainsight/models/narrative_tag.py

from django.contrib.postgres.fields import ArrayField

class CompanyNarrativeTag(models.Model):
    """뉴스 기반 내러티브/테마 태그. LLM 배치 태깅 또는 rule-based."""

    STRENGTH_CHOICES = [('strong', 'Strong'), ('moderate', 'Moderate'), ('weak', 'Weak')]
    SENTIMENT_CHOICES = [('positive', 'Positive'), ('mixed', 'Mixed'), ('negative', 'Negative')]
    GENERATED_BY_CHOICES = [
        ('llm_batch', 'LLM Batch'), ('rule_based', 'Rule Based'), ('manual', 'Manual'),
    ]
    CONSENSUS_CHOICES = [
        ('strong_buy', 'Strong Buy'), ('buy', 'Buy'), ('hold', 'Hold'),
        ('sell', 'Sell'), ('strong_sell', 'Strong Sell'),
    ]
    REVISION_CHOICES = [
        ('upgrading', 'Upgrading'), ('stable', 'Stable'), ('downgrading', 'Downgrading'),
    ]

    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='narrative_tag',
    )

    primary_narrative = models.CharField(max_length=100, blank=True)
    secondary_narrative = models.CharField(max_length=100, blank=True)
    narrative_strength = models.CharField(max_length=10, blank=True, choices=STRENGTH_CHOICES)
    narrative_sentiment = models.CharField(max_length=10, blank=True, choices=SENTIMENT_CHOICES)

    theme_tags = ArrayField(
        models.CharField(max_length=50),
        default=list, blank=True,
        help_text='["ai_infrastructure", "china_risk"]'
    )

    avg_sentiment_30d = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    sentiment_trend = models.CharField(
        max_length=20, blank=True,
        choices=[('improving', 'Improving'), ('stable', 'Stable'), ('deteriorating', 'Deteriorating')]
    )
    news_frequency_30d = models.IntegerField(default=0)

    analyst_consensus = models.CharField(max_length=20, blank=True, choices=CONSENSUS_CHOICES)
    analyst_target_vs_price = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    analyst_revision_trend = models.CharField(max_length=20, blank=True, choices=REVISION_CHOICES)

    generated_by = models.CharField(max_length=20, blank=True, choices=GENERATED_BY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_narrative_tag'

    def __str__(self):
        return f"{self.symbol_id}: {self.primary_narrative}"
```

## 3. CompanyEventReaction

```python
# chainsight/models/event_reaction.py

class CompanyEventReaction(models.Model):
    """이벤트 유형별 주가 반응 통계. 뉴스 + 주가 교차분석."""

    REACTION_GRADE_CHOICES = [
        ('high_negative', 'High Negative'),
        ('moderate_negative', 'Moderate Negative'),
        ('neutral', 'Neutral'),
        ('moderate_positive', 'Moderate Positive'),
        ('high_positive', 'High Positive'),
    ]
    CONFIDENCE_CHOICES = [('high', 'High'), ('medium', 'Medium'), ('low', 'Low')]

    symbol = models.ForeignKey(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', db_column='symbol',
        related_name='event_reactions',
    )
    event_type = models.CharField(
        max_length=50, db_index=True,
        help_text='"rate_hike", "china_tariff", "tech_selloff" 등'
    )

    sample_count = models.IntegerField(default=0)
    avg_return_1d = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    avg_return_5d = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    hit_rate_negative = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_abnormal_return = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    reaction_grade = models.CharField(max_length=20, blank=True, choices=REACTION_GRADE_CHOICES)
    confidence = models.CharField(max_length=10, default='low', choices=CONFIDENCE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_event_reaction'
        unique_together = ['symbol', 'event_type']
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['symbol']),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.event_type}: {self.reaction_grade}"
```

## 완료 기준

- [ ] CompanyInsiderSignal 모델 + 마이그레이션
- [ ] CompanyNarrativeTag 모델 + 마이그레이션 (ArrayField 확인)
- [ ] CompanyEventReaction 모델 + 마이그레이션
- [ ] admin 등록 (3개)
- [ ] chainsight/models/**init**.py에 6개 모델 export (PR-6 3개 + 본 PR 3개)
