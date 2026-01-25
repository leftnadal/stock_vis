"""
Serverless App Admin
"""
from django.contrib import admin
from serverless.models import MarketMover, SectorETFMapping, StockSectorInfo, VolatilityBaseline, StockKeyword


@admin.register(MarketMover)
class MarketMoverAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'mover_type', 'rank', 'symbol', 'company_name',
        'price', 'change_percent', 'rvol_display', 'trend_display'
    ]
    list_filter = ['date', 'mover_type']
    search_fields = ['symbol', 'company_name']
    ordering = ['-date', 'mover_type', 'rank']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('기본 정보', {
            'fields': ('date', 'mover_type', 'rank', 'symbol', 'company_name')
        }),
        ('가격 데이터', {
            'fields': ('price', 'change_percent', 'volume', 'open_price', 'high', 'low')
        }),
        ('Phase 1 지표', {
            'fields': ('rvol', 'rvol_display', 'trend_strength', 'trend_display')
        }),
        ('Phase 2 지표', {
            'fields': ('sector_alpha', 'etf_sync_rate', 'volatility_pct'),
            'classes': ('collapse',),
        }),
        ('메타데이터', {
            'fields': ('data_quality', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(SectorETFMapping)
class SectorETFMappingAdmin(admin.ModelAdmin):
    list_display = ['sector', 'sector_name', 'etf_symbol', 'created_at']
    search_fields = ['sector', 'sector_name', 'etf_symbol']
    ordering = ['sector']


@admin.register(StockSectorInfo)
class StockSectorInfoAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'sector', 'industry', 'updated_at']
    list_filter = ['sector']
    search_fields = ['symbol', 'sector', 'industry']
    ordering = ['symbol']


@admin.register(VolatilityBaseline)
class VolatilityBaselineAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'date', 'volatility', 'percentile', 'created_at']
    list_filter = ['date']
    search_fields = ['symbol']
    ordering = ['-date', 'symbol']


@admin.register(StockKeyword)
class StockKeywordAdmin(admin.ModelAdmin):
    list_display = [
        'symbol', 'date', 'status', 'keyword_count',
        'generation_time_ms', 'llm_model', 'created_at'
    ]
    list_filter = ['date', 'status', 'llm_model']
    search_fields = ['symbol', 'company_name']
    ordering = ['-date', 'symbol']
    readonly_fields = ['created_at', 'updated_at', 'expires_at']

    fieldsets = (
        ('종목 정보', {
            'fields': ('symbol', 'company_name', 'date')
        }),
        ('키워드', {
            'fields': ('keywords', 'status', 'error_message')
        }),
        ('메타데이터', {
            'fields': (
                'llm_model', 'generation_time_ms',
                'prompt_tokens', 'completion_tokens',
                'expires_at', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',),
        }),
    )

    def keyword_count(self, obj):
        """키워드 개수"""
        return len(obj.keywords) if obj.keywords else 0
    keyword_count.short_description = '키워드 수'
