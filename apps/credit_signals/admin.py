from django.contrib import admin

from .models import CreditSignalState, MacroSeriesHistory


@admin.register(MacroSeriesHistory)
class MacroSeriesHistoryAdmin(admin.ModelAdmin):
    list_display = ("series_id", "date", "value", "ingested_at", "revised_at")
    list_filter = ("series_id",)
    search_fields = ("series_id",)
    date_hierarchy = "date"


@admin.register(CreditSignalState)
class CreditSignalStateAdmin(admin.ModelAdmin):
    list_display = ("signal_key", "as_of", "value", "z_score", "grade", "updated_at")
    list_filter = ("grade",)
