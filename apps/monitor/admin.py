from django.contrib import admin

from apps.monitor.models import Claim, Monitor


@admin.register(Monitor)
class MonitorAdmin(admin.ModelAdmin):
    list_display = ("name", "scope", "target_ref", "status", "user", "updated_at")
    list_filter = ("scope", "status")
    search_fields = ("name", "target_ref")


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("assertion", "monitor", "status", "outcome", "deadline", "created_at")
    list_filter = ("status", "outcome")
