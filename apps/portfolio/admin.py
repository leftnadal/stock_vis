"""Portfolio admin — 병진 입력 지름길 (SLICE20A).

20b에서 wallet/watchlist/손잡이 입력 UI가 나오기 전까지, 1인 도그푸딩용 입력 경로를
Django admin으로 제공한다. 사용 루프: admin에 보유·현금·목표·관심 입력 → [지금 진단] → My 탭.

★ admin은 REST가 아니므로 UserGoal 손잡이 편집이 여기서 허용된다(§1 '손잡이 쓰기 금지'는
  REST PUT/PATCH 한정). 원장(PortfolioSnapshot·AdvisoryRun)은 읽기 전용 열람만.
"""

from __future__ import annotations

from django.contrib import admin

from apps.portfolio.models import Wallet, WalletHolding
from apps.portfolio.models_my import (
    AdvisoryRun,
    CashBalance,
    PortfolioSnapshot,
    UserGoal,
)
from packages.shared.users.models import WatchlistItem


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("name", "user")
    search_fields = ("name", "user__username")


@admin.register(WalletHolding)
class WalletHoldingAdmin(admin.ModelAdmin):
    list_display = ("stock", "wallet", "shares", "avg_cost", "first_bought_at", "acquisition_fx_rate")
    list_filter = ("stock__currency",)
    raw_id_fields = ("stock",)
    search_fields = ("stock__symbol", "wallet__name")


@admin.register(CashBalance)
class CashBalanceAdmin(admin.ModelAdmin):
    list_display = ("wallet", "currency", "amount")
    list_filter = ("currency",)


@admin.register(UserGoal)
class UserGoalAdmin(admin.ModelAdmin):
    list_display = (
        "user", "target_return_pct", "horizon_months",
        "aggressiveness_offset", "growth_boost",
        "diversification_weight", "concentration_limit", "exploration_ratio",
    )
    search_fields = ("user__username",)


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ("stock", "watchlist", "target_entry_price")
    raw_id_fields = ("stock",)
    search_fields = ("stock__symbol",)


# ---- 원장(읽기 전용 열람) ----


@admin.register(PortfolioSnapshot)
class PortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "total_krw", "price_as_of")
    list_filter = ("date",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AdvisoryRun)
class AdvisoryRunAdmin(admin.ModelAdmin):
    list_display = ("user", "run_at", "trigger", "snapshot")
    list_filter = ("trigger",)
    readonly_fields = ("id", "run_at", "output", "knobs_snapshot")
