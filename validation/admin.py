from django.contrib import admin
from .models import CompanyMetricLatest, CompanyBenchmarkDelta


@admin.register(CompanyMetricLatest)
class CompanyMetricLatestAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'metric_code', 'latest_value', 'signal', 'trend_label', 'warning_flag']
    list_filter = ['signal', 'trend_label', 'warning_flag']
    search_fields = ['symbol__symbol']


@admin.register(CompanyBenchmarkDelta)
class CompanyBenchmarkDeltaAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'fiscal_year', 'metric_code', 'company_value', 'benchmark_median', 'relative_signal']
    list_filter = ['benchmark_type', 'relative_signal', 'benchmark_confidence', 'fiscal_year']
    search_fields = ['symbol__symbol']
