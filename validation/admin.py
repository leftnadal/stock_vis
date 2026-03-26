from django.contrib import admin
from .models import (
    CompanyMetricLatest, CompanyBenchmarkDelta,
    CategoryScore, ValidationNewsSummary,
)


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


@admin.register(CategoryScore)
class CategoryScoreAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'category', 'signal', 'score', 'grade']
    list_filter = ['category', 'signal']
    search_fields = ['symbol__symbol']


@admin.register(ValidationNewsSummary)
class ValidationNewsSummaryAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'event_count_30d', 'avg_sentiment_30d', 'sentiment_trend', 'has_regulatory_risk']
    list_filter = ['sentiment_trend', 'has_regulatory_risk', 'has_exec_change', 'has_guidance_cut']
    search_fields = ['symbol__symbol']
