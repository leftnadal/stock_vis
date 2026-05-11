# PR-2: CompanyMetricSnapshot + PeerListCache 모델

## 참고 문서

- `docs/architecture/claude-code-reference-doc.md` — 섹션 3(컨벤션), 섹션 6(계산 소스 매핑)
- PR-1 완료 전제: MetricDefinition 모델 존재

## 작업 범위

1. CompanyMetricSnapshot 모델 생성
2. PeerListCache 모델 생성
3. admin 등록

## 주의사항

- 기존 코드 수정 없음
- CompanyMetricSnapshot.metric_code는 MetricDefinition FK
- CompanyMetricSnapshot.symbol은 stocks.Stock FK (to_field='symbol')

---

## 1. CompanyMetricSnapshot 모델

종목 × 연도 × 지표별 계산 원값 저장. 1차 검증과 Chain Sight 공통 원천.

```python
# metrics/models/metric_snapshot.py

from django.db import models


class CompanyMetricSnapshot(models.Model):
    """
    종목별 연도별 지표 계산값.
    기존 BalanceSheet + IncomeStatement + CashFlowStatement에서 파생.
    """
    symbol = models.ForeignKey(
        'stocks.Stock',
        on_delete=models.PROTECT,
        to_field='symbol',
        db_column='symbol',
        related_name='metric_snapshots',
    )
    fiscal_year = models.IntegerField(db_index=True)
    metric_code = models.ForeignKey(
        'metrics.MetricDefinition',
        on_delete=models.CASCADE,
        db_column='metric_code',
        related_name='snapshots',
    )

    metric_value = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )

    # 데이터 품질
    is_fallback_used = models.BooleanField(default=False)
    fallback_reason = models.CharField(max_length=200, blank=True)
    quality_flag = models.CharField(
        max_length=20, default='ok',
        choices=[
            ('ok', 'OK'),
            ('insufficient_data', 'Insufficient Data'),
            ('null_denominator', 'Null Denominator'),
            ('stale', 'Stale Data'),
            ('fallback', 'Fallback Used'),
        ]
    )

    # 원천 추적
    source_detail = models.JSONField(
        default=dict,
        help_text='{"apis": [...], "fields": [...], "formula_version": 1}'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'metrics_company_metric_snapshot'
        unique_together = ['symbol', 'fiscal_year', 'metric_code']
        indexes = [
            models.Index(fields=['symbol', 'metric_code']),
            models.Index(fields=['symbol', 'fiscal_year']),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.fiscal_year} {self.metric_code_id}: {self.metric_value}"
```

## 2. PeerListCache 모델

종목별 peer 목록 캐시. 월 1회 갱신.

```python
# metrics/models/benchmark.py (이 파일에 벤치마크 관련 모델 모음)

from django.contrib.postgres.fields import ArrayField

class PeerListCache(models.Model):
    """
    종목별 peer 목록 캐시.
    FMP stock-peers API 결과 저장.
    """
    symbol = models.OneToOneField(
        'stocks.Stock',
        on_delete=models.CASCADE,
        to_field='symbol',
        primary_key=True,
        related_name='peer_cache',
    )
    peer_symbols = ArrayField(
        models.CharField(max_length=10),
        default=list, blank=True,
        help_text='["MSFT", "GOOGL", "META"]'
    )
    peer_count = models.IntegerField(default=0)

    use_industry_fallback = models.BooleanField(default=False)
    fallback_reason = models.CharField(max_length=200, blank=True)

    source = models.CharField(max_length=20, default='fmp_peers')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'metrics_peer_list_cache'

    def __str__(self):
        return f"{self.symbol_id}: {self.peer_count} peers"
```

## 3. models/**init**.py 업데이트

```python
from .metric_definition import MetricDefinition
from .batch_job import BatchJobRun
from .metric_snapshot import CompanyMetricSnapshot
from .benchmark import PeerListCache
```

## 4. admin 추가

```python
@admin.register(CompanyMetricSnapshot)
class CompanyMetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'fiscal_year', 'metric_code', 'metric_value', 'quality_flag']
    list_filter = ['quality_flag', 'fiscal_year', 'metric_code']
    search_fields = ['symbol__symbol']

@admin.register(PeerListCache)
class PeerListCacheAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'peer_count', 'use_industry_fallback', 'updated_at']
    list_filter = ['use_industry_fallback']
```

## 검증

```bash
python manage.py makemigrations metrics
python manage.py migrate
# admin에서 모델 확인
```

## 완료 기준

- [ ] CompanyMetricSnapshot 모델 생성 완료
- [ ] PeerListCache 모델 생성 완료
- [ ] FK 관계 정상 (Stock, MetricDefinition)
- [ ] unique_together 제약 확인
- [ ] 기존 코드 영향 없음
