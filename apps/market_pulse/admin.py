"""
Django Admin 등록 (PR-A2).

소속: apps/market_pulse (app 레이어 root).
역할: 마켓 펄스 도메인 모델 8종(AnomalySignalLog·BriefingLog·MarketPulseNews·
  NewsViewLog·RegimeSnapshot·BreadthSnapshot·SectorFlowSnapshot·ConcentrationSnapshot)을
  Django Admin에 등록 — 운영자 점검·강제 갱신용.
"""

from django.contrib import admin

from apps.market_pulse.models.anomaly import AnomalySignalLog
from apps.market_pulse.models.briefing import BriefingLog
from apps.market_pulse.models.news import MarketPulseNews, NewsViewLog
from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.models.snapshot import (
    BreadthSnapshot,
    ConcentrationSnapshot,
    SectorFlowSnapshot,
)


@admin.register(MarketPulseNews)
class MarketPulseNewsAdmin(admin.ModelAdmin):
    list_display = ("category", "title", "publisher", "shown_on_layer0", "published_at")
    list_filter = ("category", "source", "shown_on_layer0")
    search_fields = ("title", "url")
    date_hierarchy = "published_at"


@admin.register(NewsViewLog)
class NewsViewLogAdmin(admin.ModelAdmin):
    list_display = ("user", "news", "viewed_date", "viewed_at")
    list_filter = ("viewed_date",)


@admin.register(RegimeSnapshot)
class RegimeSnapshotAdmin(admin.ModelAdmin):
    list_display = ("date", "regime", "status", "coverage", "is_finalized")
    list_filter = ("regime", "status", "is_finalized")


@admin.register(BreadthSnapshot)
class BreadthSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "universe",
        "advance_count",
        "decline_count",
        "ad_line",
        "is_finalized",
    )
    list_filter = ("universe", "is_finalized")


@admin.register(SectorFlowSnapshot)
class SectorFlowSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "market_index",
        "rel_strength",
        "rank_in_universe",
        "is_finalized",
    )
    list_filter = ("is_finalized",)


@admin.register(ConcentrationSnapshot)
class ConcentrationSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "universe",
        "top5_weight",
        "top10_weight",
        "hhi",
        "is_finalized",
    )
    list_filter = ("is_finalized",)


@admin.register(AnomalySignalLog)
class AnomalySignalLogAdmin(admin.ModelAdmin):
    list_display = ("rule_id", "mode", "triggered_at")
    list_filter = ("rule_id", "mode")


@admin.register(BriefingLog)
class BriefingLogAdmin(admin.ModelAdmin):
    list_display = ("date", "model_version", "status", "headline")
    list_filter = ("status", "model_version")
