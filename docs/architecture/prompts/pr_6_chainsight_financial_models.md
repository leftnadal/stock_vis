# PR-6: chainsight 앱 생성 — SensitivityProfile + GrowthStage + CapitalDNA

## 참고 문서

- `docs/architecture/claude-code-reference-doc.md` — 섹션 7(Chain Sight 기업 데이터 정의)
- PR-1~3 완료 전제: metrics 앱의 CompanyMetricSnapshot 존재

## 작업 범위

1. chainsight/ Django 앱 생성
2. CompanySensitivityProfile 모델
3. CompanyGrowthStage 모델
4. CompanyCapitalDNA 모델
5. admin 등록

## 주의사항

- 이 3개 모델은 전부 Tier A (정량, 재무제표 기반 자동 계산 가능)
- metrics.CompanyMetricSnapshot에서 원값을 가져와 해석 레이어를 씌운 것
- 기존 코드 수정 없음

---

## 1. 앱 생성

```
chainsight/
├── __init__.py
├── admin.py
├── apps.py
├── models/
│   ├── __init__.py
│   ├── sensitivity.py
│   ├── growth_stage.py
│   ├── capital_dna.py
│   ├── insider_signal.py      ← PR-7
│   ├── narrative_tag.py       ← PR-7
│   ├── event_reaction.py      ← PR-7
│   ├── revenue_structure.py   ← PR-8
│   ├── chain_profile.py       ← PR-8
│   └── news_event.py          ← PR-8
└── migrations/
```

settings.py INSTALLED_APPS에 `chainsight` 추가.

## 2. CompanySensitivityProfile

참고 문서 섹션 7의 CompanySensitivityProfile 필드 그대로 구현.

핵심: 금리/환율/규제 이벤트에 대한 기업별 노출도.

```python
# chainsight/models/sensitivity.py

class CompanySensitivityProfile(models.Model):
    """이벤트(금리, 환율, 규제)에 대한 기업별 민감도 프로파일."""

    RISK_LEVEL_CHOICES = [('high', 'High'), ('medium', 'Medium'), ('low', 'Low')]
    REGULATION_CHOICES = [
        ('fda', 'FDA/Healthcare'),
        ('financial', 'Financial'),
        ('environmental', 'Environmental'),
        ('telecom', 'Telecom'),
        ('none', 'None'),
    ]

    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='sensitivity_profile',
    )

    # 금리 민감도
    debt_to_equity = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    net_debt = models.BigIntegerField(null=True, blank=True)
    interest_coverage = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    debt_maturity_risk = models.CharField(max_length=10, blank=True, choices=RISK_LEVEL_CHOICES)
    rate_sensitivity = models.CharField(
        max_length=10, blank=True, choices=RISK_LEVEL_CHOICES,
        help_text='종합 금리 민감도 (debt_to_equity + interest_coverage + maturity 기반)'
    )

    # 환율 민감도
    foreign_revenue_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    primary_currency_exposure = models.CharField(max_length=10, blank=True)
    forex_sensitivity = models.CharField(
        max_length=10, blank=True, choices=RISK_LEVEL_CHOICES,
        help_text='종합 환율 민감도 (foreign_revenue_pct 기반)'
    )

    # 시장 민감도
    beta = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    beta_sector_adj = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)

    # 원자재 민감도 (Tier B에서 채움, 초기에는 blank)
    commodity_sensitivity = models.CharField(
        max_length=10, blank=True, choices=RISK_LEVEL_CHOICES,
        help_text='종합 원자재 민감도 (revenue_structure.commodity_exposures 기반)'
    )

    # 규제 민감도
    sector = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    is_regulated_industry = models.BooleanField(default=False)
    regulation_type = models.CharField(max_length=50, blank=True, choices=REGULATION_CHOICES)

    data_source = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_sensitivity_profile'

    def __str__(self):
        return f"{self.symbol_id}: rate={self.debt_maturity_risk} beta={self.beta}"
```

## 3. CompanyGrowthStage

참고 문서 섹션 7의 CompanyGrowthStage 필드 그대로 구현.

```python
# chainsight/models/growth_stage.py

class CompanyGrowthStage(models.Model):
    """기업 생애주기 위치. 같은 이벤트에 대한 반응이 스테이지에 따라 다름."""

    STAGE_CHOICES = [
        ('early_growth', 'Early Growth'),
        ('accelerating', 'Accelerating'),
        ('mature', 'Mature'),
        ('cash_cow', 'Cash Cow'),
        ('turnaround', 'Turnaround'),
        ('declining', 'Declining'),
    ]
    CONFIDENCE_CHOICES = [('high', 'High'), ('medium', 'Medium'), ('low', 'Low')]

    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='growth_stage',
    )

    stage = models.CharField(max_length=30, choices=STAGE_CHOICES, default='mature')

    revenue_cagr_3y = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    revenue_cagr_5y = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    revenue_acceleration = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    net_income_positive_years = models.IntegerField(default=0)
    net_income_turned_positive = models.BooleanField(default=False)

    fcf_trend = models.CharField(
        max_length=20, blank=True,
        choices=[('growing', 'Growing'), ('stable', 'Stable'), ('declining', 'Declining')]
    )
    fcf_positive_years = models.IntegerField(default=0)

    dividend_started = models.BooleanField(default=False)
    dividend_years = models.IntegerField(default=0)

    confidence = models.CharField(max_length=10, default='medium', choices=CONFIDENCE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_growth_stage'

    def __str__(self):
        return f"{self.symbol_id}: {self.stage} (confidence={self.confidence})"
```

## 4. CompanyCapitalDNA

```python
# chainsight/models/capital_dna.py

class CompanyCapitalDNA(models.Model):
    """자본 배분 성향. 경영진이 돈을 어떻게 쓰는가."""

    CAPITAL_TYPE_CHOICES = [
        ('heavy_investor', 'Heavy Investor'),
        ('balanced', 'Balanced'),
        ('shareholder_first', 'Shareholder First'),
        ('cash_hoarder', 'Cash Hoarder'),
        ('aggressive_growth', 'Aggressive Growth'),
        ('unknown', 'Unknown'),
    ]
    TREND_CHOICES = [
        ('increasing', 'Increasing'),
        ('stable', 'Stable'),
        ('decreasing', 'Decreasing'),
    ]

    symbol = models.OneToOneField(
        'stocks.Stock', on_delete=models.CASCADE,
        to_field='symbol', primary_key=True,
        related_name='capital_dna',
    )

    rd_to_revenue = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    rd_trend = models.CharField(max_length=20, blank=True, choices=TREND_CHOICES)

    capex_to_revenue = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    capex_trend = models.CharField(
        max_length=20, blank=True,
        choices=[('expanding', 'Expanding'), ('stable', 'Stable'), ('harvesting', 'Harvesting')]
    )

    dividend_payout = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    buyback_yield = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    total_shareholder_return_pct = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    net_cash_position = models.BigIntegerField(null=True, blank=True)
    cash_to_market_cap = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    capital_type = models.CharField(max_length=30, blank=True, choices=CAPITAL_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chainsight_capital_dna'

    def __str__(self):
        return f"{self.symbol_id}: {self.capital_type}"
```

## 완료 기준

- [ ] chainsight 앱 생성
- [ ] CompanySensitivityProfile 모델 + 마이그레이션
- [ ] CompanyGrowthStage 모델 + 마이그레이션
- [ ] CompanyCapitalDNA 모델 + 마이그레이션
- [ ] admin 등록 (3개 모델)
- [ ] chainsight/models/**init**.py에 3개 모델 export
