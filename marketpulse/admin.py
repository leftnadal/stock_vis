"""Market Pulse v2 admin (PR-A2)."""
from django.contrib import admin

from marketpulse.models.anomaly import AnomalySignalLog
from marketpulse.models.briefing import BriefingLog
from marketpulse.models.news import MarketPulseNews, NewsViewLog
from marketpulse.models.regime import RegimeSnapshot
from marketpulse.models.snapshot import (
    BreadthSnapshot,
    ConcentrationSnapshot,
    SectorFlowSnapshot,
)


@admin.register(MarketPulseNews)
class MarketPulseNewsAdmin(admin.ModelAdmin):
    list_display = ('category', 'title', 'publisher', 'shown_on_layer0', 'published_at')
    list_filter = ('category', 'source', 'shown_on_layer0')
    search_fields = ('title', 'url')
    date_hierarchy = 'published_at'


@admin.register(NewsViewLog)
class NewsViewLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'news', 'viewed_date', 'viewed_at')
    list_filter = ('viewed_date',)


@admin.register(RegimeSnapshot)
class RegimeSnapshotAdmin(admin.ModelAdmin):
    list_display = ('date', 'regime', 'status', 'coverage', 'is_finalized')
    list_filter = ('regime', 'status', 'is_finalized')


@admin.register(BreadthSnapshot)
class BreadthSnapshotAdmin(admin.ModelAdmin):
    list_display = ('date', 'universe', 'advance_count', 'decline_count', 'ad_line', 'is_finalized')
    list_filter = ('universe', 'is_finalized')


@admin.register(SectorFlowSnapshot)
class SectorFlowSnapshotAdmin(admin.ModelAdmin):
    list_display = ('date', 'market_index', 'rel_strength', 'rank_in_universe', 'is_finalized')
    list_filter = ('is_finalized',)


@admin.register(ConcentrationSnapshot)
class ConcentrationSnapshotAdmin(admin.ModelAdmin):
    list_display = ('date', 'universe', 'top5_weight', 'top10_weight', 'hhi', 'is_finalized')
    list_filter = ('is_finalized',)


@admin.register(AnomalySignalLog)
class AnomalySignalLogAdmin(admin.ModelAdmin):
    list_display = ('rule_id', 'mode', 'triggered_at')
    list_filter = ('rule_id', 'mode')


@admin.register(BriefingLog)
class BriefingLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'model_version', 'status', 'headline')
    list_filter = ('status', 'model_version')
