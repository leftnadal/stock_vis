"""
Graph Analysis Admin Interface
"""
from django.contrib import admin
from .models import (
    CorrelationMatrix,
    CorrelationEdge,
    CorrelationAnomaly,
    PriceCache,
    GraphMetadata,
)


@admin.register(CorrelationMatrix)
class CorrelationMatrixAdmin(admin.ModelAdmin):
    list_display = ('watchlist', 'date', 'stock_count', 'calculation_period', 'created_at')
    list_filter = ('date', 'calculation_period')
    search_fields = ('watchlist__name', 'watchlist__user__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'


@admin.register(CorrelationEdge)
class CorrelationEdgeAdmin(admin.ModelAdmin):
    list_display = ('stock_a', 'stock_b', 'correlation', 'correlation_change', 'is_anomaly', 'date')
    list_filter = ('is_anomaly', 'date')
    search_fields = ('stock_a__symbol', 'stock_b__symbol', 'watchlist__name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'date'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('stock_a', 'stock_b', 'watchlist')


@admin.register(CorrelationAnomaly)
class CorrelationAnomalyAdmin(admin.ModelAdmin):
    list_display = (
        'watchlist',
        'get_stock_pair',
        'anomaly_type',
        'change_magnitude',
        'alerted',
        'dismissed',
        'date'
    )
    list_filter = ('anomaly_type', 'alerted', 'dismissed', 'date')
    search_fields = ('watchlist__name', 'edge__stock_a__symbol', 'edge__stock_b__symbol')
    readonly_fields = ('created_at', 'updated_at', 'alert_sent_at')
    date_hierarchy = 'date'

    def get_stock_pair(self, obj):
        return f"{obj.edge.stock_a.symbol}-{obj.edge.stock_b.symbol}"
    get_stock_pair.short_description = 'Stock Pair'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'watchlist',
            'edge__stock_a',
            'edge__stock_b'
        )


@admin.register(PriceCache)
class PriceCacheAdmin(admin.ModelAdmin):
    list_display = ('stock', 'date', 'period_days', 'created_at', 'updated_at')
    list_filter = ('date', 'period_days')
    search_fields = ('stock__symbol', 'stock__name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('stock')


@admin.register(GraphMetadata)
class GraphMetadataAdmin(admin.ModelAdmin):
    list_display = (
        'watchlist',
        'date',
        'status',
        'stock_count',
        'edge_count',
        'anomaly_count',
        'calculation_time_ms'
    )
    list_filter = ('status', 'date')
    search_fields = ('watchlist__name', 'watchlist__user__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('watchlist')
