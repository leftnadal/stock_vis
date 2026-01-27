"""
거시경제 데이터 Admin
"""
from django.contrib import admin
from .models import (
    EconomicIndicator,
    IndicatorValue,
    MarketIndex,
    MarketIndexPrice,
    EconomicEvent,
    SectorIndicatorRelation,
    IndicatorCorrelation,
)


@admin.register(EconomicIndicator)
class EconomicIndicatorAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'data_source', 'update_frequency', 'is_active']
    list_filter = ['category', 'data_source', 'update_frequency', 'is_active']
    search_fields = ['code', 'name', 'name_ko']
    ordering = ['display_order', 'code']


@admin.register(IndicatorValue)
class IndicatorValueAdmin(admin.ModelAdmin):
    list_display = ['indicator', 'date', 'value', 'is_preliminary']
    list_filter = ['indicator', 'is_preliminary']
    date_hierarchy = 'date'
    ordering = ['-date']


@admin.register(MarketIndex)
class MarketIndexAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'category', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['symbol', 'name']


@admin.register(MarketIndexPrice)
class MarketIndexPriceAdmin(admin.ModelAdmin):
    list_display = ['index', 'date', 'close', 'change_percent']
    list_filter = ['index']
    date_hierarchy = 'date'


@admin.register(EconomicEvent)
class EconomicEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_date', 'importance', 'country', 'actual_value']
    list_filter = ['importance', 'country', 'event_date']
    search_fields = ['title', 'title_ko']
    date_hierarchy = 'event_date'


@admin.register(SectorIndicatorRelation)
class SectorIndicatorRelationAdmin(admin.ModelAdmin):
    list_display = ['indicator', 'sector_name', 'impact_direction', 'impact_strength', 'condition_type']
    list_filter = ['impact_direction', 'impact_strength', 'condition_type']
    search_fields = ['sector_name', 'indicator__code']


@admin.register(IndicatorCorrelation)
class IndicatorCorrelationAdmin(admin.ModelAdmin):
    list_display = ['indicator_a', 'indicator_b', 'correlation_type', 'correlation_coefficient']
    list_filter = ['correlation_type']
