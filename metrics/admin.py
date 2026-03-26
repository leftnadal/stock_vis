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
