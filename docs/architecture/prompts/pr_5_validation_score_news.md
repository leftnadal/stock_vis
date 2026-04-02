# PR-5: CategoryScore + ValidationNewsSummary 모델

## 참고 문서

- `docs/architecture/claude-code-reference-doc.md`
- PR-4 완료 전제: validation 앱 존재

## 작업 범위

1. CategoryScore 모델 생성 (Snowflake 시각화용, nullable optional)
2. ValidationNewsSummary 모델 생성
3. admin 등록

---

## 1. CategoryScore 모델

7개 카테고리별 종합 점수. MVP에서는 signal 중심, score/grade는 nullable optional.

```python
# validation/models/category_score.py

from django.db import models


class CategoryScore(models.Model):
    """카테고리별 종합 점수. MVP에서는 signal card 중심, 점수는 optional."""
    CATEGORY_CHOICES = [
        ('profitability', 'Profitability'),
        ('growth', 'Growth'),
        ('financial_structure', 'Financial Structure'),
        ('cash_flow_quality', 'Cash Flow Quality'),
        ('operational_efficiency', 'Operational Efficiency'),
        ('dilution_shareholder', 'Dilution & Shareholder'),
        ('valuation', 'Valuation'),
    ]

    symbol = models.ForeignKey(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', db_column='symbol',
        related_name='category_scores',
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)

    # MVP 핵심: signal card
    signal = models.CharField(
        max_length=10, blank=True,
        choices=[('green', 'Green'), ('yellow', 'Yellow'), ('red', 'Red')]
    )
    signal_reason = models.CharField(max_length=200, blank=True)

    # Optional (Phase 2)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=5, blank=True)  # "A+", "A", "B+", ...
    rank_in_industry = models.IntegerField(null=True, blank=True)
    total_in_industry = models.IntegerField(null=True, blank=True)

    contributing_metrics = models.JSONField(
        default=list,
        help_text='[{"metric": "roe", "value": 0.25, "signal": "green"}, ...]'
    )

    score_1y_ago = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    score_change = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'validation_category_score'
        unique_together = ['symbol', 'category']
        indexes = [
            models.Index(fields=['symbol']),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.category}: [{self.signal}] {self.score}"
```

## 2. ValidationNewsSummary 모델

1차 검증 화면의 뉴스 섹션용 집계 캐시.

```python
# validation/models/news_summary.py

from django.db import models


class ValidationNewsSummary(models.Model):
    """1차 검증용 뉴스 감성/이벤트 집계 캐시."""
    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='validation_news_summary',
    )

    event_count_30d = models.IntegerField(default=0)
    event_count_90d = models.IntegerField(default=0)

    avg_sentiment_30d = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    sentiment_trend = models.CharField(
        max_length=20, blank=True,
        choices=[
            ('improving', 'Improving'),
            ('stable', 'Stable'),
            ('deteriorating', 'Deteriorating'),
        ]
    )

    dominant_event_type = models.CharField(max_length=50, blank=True)
    high_importance_count = models.IntegerField(default=0)

    has_regulatory_risk = models.BooleanField(default=False)
    has_exec_change = models.BooleanField(default=False)
    has_guidance_cut = models.BooleanField(default=False)

    recent_highlights = models.JSONField(
        default=list,
        help_text='[{"title": "...", "sentiment": 0.7, "event_type": "earnings", "date": "..."}, ...]'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'validation_news_summary'

    def __str__(self):
        return f"{self.symbol_id}: {self.event_count_30d} events (30d)"
```

## 완료 기준

- [ ] CategoryScore 모델 생성 (score/grade nullable 확인)
- [ ] ValidationNewsSummary 모델 생성
- [ ] admin 등록
- [ ] validation 앱 models/**init**.py에 4개 모델 전부 export
