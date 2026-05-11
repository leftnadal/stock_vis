# PR-1: metrics 앱 생성 — MetricDefinition + BatchJobRun

## 참고 문서

- 반드시 먼저 `docs/architecture/claude-code-reference-doc.md` 읽기
- 기존 모델 참고: `stocks/models.py`의 Stock 모델 (PK = symbol CharField)

## 작업 범위

1. `metrics/` Django 앱 생성
2. MetricDefinition 모델 생성
3. BatchJobRun 모델 생성
4. MetricDefinition 시드 데이터 management command 생성
5. admin 등록

## 주의사항

- 기존 코드 수정 없음
- settings.py의 INSTALLED_APPS에 `metrics` 추가
- 모든 모델에 `created_at` 필드 포함

---

## 1. 앱 생성

```bash
python manage.py startapp metrics
```

파일 구조:

```
metrics/
├── __init__.py
├── admin.py
├── apps.py
├── models/
│   ├── __init__.py
│   ├── metric_definition.py
│   └── batch_job.py
├── management/
│   └── commands/
│       └── seed_metric_definitions.py
└── migrations/
```

## 2. MetricDefinition 모델

참고 문서의 "5. MetricDefinition 전체 지표 사전 (34개)" 섹션 참조.

```python
# metrics/models/metric_definition.py

from django.db import models


class MetricDefinition(models.Model):
    """
    지표 메타데이터 사전.
    모든 CompanyMetricSnapshot의 metric_code가 이 테이블을 FK 참조.
    """
    CATEGORY_CHOICES = [
        ('profitability', 'Profitability'),
        ('growth', 'Growth'),
        ('financial_structure', 'Financial Structure'),
        ('cash_flow_quality', 'Cash Flow Quality'),
        ('operational_efficiency', 'Operational Efficiency'),
        ('dilution_shareholder', 'Dilution & Shareholder'),
        ('valuation', 'Valuation'),
    ]

    UNIT_CHOICES = [
        ('ratio', 'Ratio'),
        ('days', 'Days'),
        ('pct', 'Percentage'),
        ('years', 'Years'),
        ('flag', 'Boolean Flag'),
    ]

    metric_code = models.CharField(max_length=50, primary_key=True)
    display_name = models.CharField(max_length=100)
    display_name_en = models.CharField(max_length=100)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    higher_is_better = models.BooleanField()
    is_core_mvp = models.BooleanField(default=True)
    is_benchmarkable = models.BooleanField(default=True)

    # 계산 정보
    formula_description = models.TextField(blank=True)
    source_apis = models.JSONField(default=list)
    source_fields = models.JSONField(default=list)
    fallback_formula = models.TextField(blank=True)

    # 신호등 임계값
    green_threshold = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    red_threshold = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    threshold_direction = models.CharField(
        max_length=10, default='above',
        choices=[('above', 'Above'), ('below', 'Below')]
    )

    # 관리
    sort_order = models.IntegerField(default=0)
    formula_version = models.IntegerField(default=1)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'metrics_metric_definition'
        ordering = ['category', 'sort_order']

    def __str__(self):
        return f"{self.metric_code}: {self.display_name}"
```

## 3. BatchJobRun 모델

```python
# metrics/models/batch_job.py

from django.db import models


class BatchJobRun(models.Model):
    """
    배치 파이프라인 실행 이력.
    metrics, validation, chainsight 모든 배치에서 공용.
    """
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('success', 'Success'),
        ('partial_failure', 'Partial Failure'),
        ('failed', 'Failed'),
    ]

    job_name = models.CharField(max_length=100, db_index=True)
    job_type = models.CharField(
        max_length=50, default='scheduled',
        choices=[
            ('scheduled', 'Scheduled'),
            ('manual', 'Manual'),
            ('retry', 'Retry'),
        ]
    )

    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    total_symbols = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    failure_count = models.IntegerField(default=0)
    skip_count = models.IntegerField(default=0)

    failure_details = models.JSONField(default=list)
    pipeline_step = models.CharField(max_length=50, blank=True)
    depends_on_job_id = models.BigIntegerField(null=True, blank=True)
    triggered_by = models.CharField(max_length=50, default='celery_beat')
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'metrics_batch_job_run'
        indexes = [
            models.Index(fields=['job_name', '-started_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.job_name} [{self.status}] {self.started_at}"
```

## 4. seed_metric_definitions management command

참고 문서의 "5. MetricDefinition 전체 지표 사전 (34개)" 테이블 데이터를 시드하는 커맨드.

34개 지표 전부 생성. `update_or_create`로 멱등성 보장.

각 지표의 `source_apis`, `source_fields`는 참고 문서의 "6. CompanyMetricSnapshot 필드 계산 소스 매핑" 섹션 참조.

```bash
python manage.py seed_metric_definitions
```

## 5. admin.py

```python
from django.contrib import admin
from .models import MetricDefinition, BatchJobRun

@admin.register(MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    list_display = ['metric_code', 'display_name', 'category', 'unit', 'is_core_mvp']
    list_filter = ['category', 'is_core_mvp']
    search_fields = ['metric_code', 'display_name']

@admin.register(BatchJobRun)
class BatchJobRunAdmin(admin.ModelAdmin):
    list_display = ['job_name', 'status', 'started_at', 'total_symbols', 'success_count', 'failure_count']
    list_filter = ['status', 'job_name']
```

## 6. 검증

```bash
python manage.py makemigrations metrics
python manage.py migrate
python manage.py seed_metric_definitions
# admin에서 34개 지표 확인
```

## 완료 기준

- [ ] metrics 앱 생성 완료
- [ ] MetricDefinition 모델 + 마이그레이션 완료
- [ ] BatchJobRun 모델 + 마이그레이션 완료
- [ ] 34개 지표 시드 데이터 생성 완료
- [ ] admin 페이지에서 확인 가능
- [ ] 기존 코드 영향 없음
