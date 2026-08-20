from django.contrib import admin

from apps.monitor.models import (
    Claim,
    ClaimEvidence,
    DecisionJournalEntry,
    Monitor,
    SwapHoldLog,
)


@admin.register(Monitor)
class MonitorAdmin(admin.ModelAdmin):
    list_display = ("name", "scope", "target_ref", "status", "user", "updated_at")
    list_filter = ("scope", "status")
    search_fields = ("name", "target_ref")


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("assertion", "monitor", "status", "outcome", "deadline", "created_at")
    list_filter = ("status", "outcome")


@admin.register(ClaimEvidence)
class ClaimEvidenceAdmin(admin.ModelAdmin):
    list_display = ("claim", "kind", "indicator", "operator", "threshold", "created_at")
    list_filter = ("kind",)


@admin.register(SwapHoldLog)
class SwapHoldLogAdmin(admin.ModelAdmin):
    list_display = ("claim", "candidate_ref", "held_at")
    list_filter = ("candidate_ref",)


@admin.register(DecisionJournalEntry)
class DecisionJournalEntryAdmin(admin.ModelAdmin):
    list_display = ("claim", "kind", "created_at")
    list_filter = ("kind",)
