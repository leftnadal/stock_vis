from django.contrib import admin
from .models import MetricDefinition, BatchJobRun, CompanyMetricSnapshot, PeerListCache


@admin.register(MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    list_display = ['metric_code', 'display_name', 'category', 'unit', 'is_core_mvp']
    list_filter = ['category', 'is_core_mvp']
    search_fields = ['metric_code', 'display_name']


@admin.register(BatchJobRun)
class BatchJobRunAdmin(admin.ModelAdmin):
    list_display = ['job_name', 'status', 'started_at', 'total_symbols', 'success_count', 'failure_count']
    list_filter = ['status', 'job_name']


@admin.register(CompanyMetricSnapshot)
class CompanyMetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'fiscal_year', 'metric_code', 'metric_value', 'quality_flag']
    list_filter = ['quality_flag', 'fiscal_year', 'metric_code']
    search_fields = ['symbol__symbol']


@admin.register(PeerListCache)
class PeerListCacheAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'peer_count', 'use_industry_fallback', 'updated_at']
    list_filter = ['use_industry_fallback']
