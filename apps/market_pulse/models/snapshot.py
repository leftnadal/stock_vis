"""Market Pulse v2 카드 스냅샷 모델 (PR-A3)"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class BreadthSnapshot(models.Model):
    class Universe(models.TextChoices):
        SPY = "SPY", "S&P 500 (SPY)"
        QQQ = "QQQ", "NASDAQ 100 (QQQ)"
        DIA = "DIA", "Dow Jones (DIA)"

    date = models.DateField(db_index=True)
    snapshot_time = models.DateTimeField(db_index=True)

    universe = models.CharField(
        max_length=10, choices=Universe.choices, default=Universe.SPY
    )

    advance_count = models.PositiveIntegerField(default=0)
    decline_count = models.PositiveIntegerField(default=0)
    unchanged_count = models.PositiveIntegerField(default=0)
    total_count = models.PositiveIntegerField(default=0)

    new_high_52w = models.PositiveIntegerField(default=0)
    new_low_52w = models.PositiveIntegerField(default=0)

    ad_line = models.IntegerField(default=0)
    ad_line_change = models.IntegerField(default=0)

    is_finalized = models.BooleanField(default=False, db_index=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_breadth_snapshot"
        verbose_name = "Breadth Snapshot"
        verbose_name_plural = "Breadth Snapshots"
        unique_together = [("date", "universe")]
        ordering = ["-date", "universe"]

    def __str__(self) -> str:
        return f"{self.date} [{self.universe}] AD={self.ad_line}"


class SectorFlowSnapshot(models.Model):
    date = models.DateField(db_index=True)
    snapshot_time = models.DateTimeField(db_index=True)

    market_index = models.ForeignKey(
        "macro.MarketIndex",
        on_delete=models.PROTECT,
        related_name="mp_sector_flows",
    )

    rel_strength = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal("0")
    )
    momentum_1d = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal("0")
    )
    momentum_5d = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal("0")
    )
    momentum_20d = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal("0")
    )

    flow_proxy = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )

    cross_dispersion = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal("0")
    )
    rotation_index = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal("0")
    )

    rank_in_universe = models.PositiveSmallIntegerField(default=0)

    is_finalized = models.BooleanField(default=False, db_index=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_sector_flow_snapshot"
        verbose_name = "Sector Flow Snapshot"
        verbose_name_plural = "Sector Flow Snapshots"
        unique_together = [("date", "market_index")]
        ordering = ["-date", "rank_in_universe"]
        indexes = [
            models.Index(fields=["date", "is_finalized"], name="mp_sf_date_fin_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.market_index_id} rel={self.rel_strength}"


class ConcentrationSnapshot(models.Model):
    date = models.DateField(db_index=True)
    snapshot_time = models.DateTimeField(db_index=True)
    universe = models.CharField(max_length=10, default="SPY")

    top5_weight = models.DecimalField(
        max_digits=6, decimal_places=4, default=Decimal("0")
    )
    top10_weight = models.DecimalField(
        max_digits=6, decimal_places=4, default=Decimal("0")
    )
    hhi = models.DecimalField(max_digits=8, decimal_places=6, default=Decimal("0"))

    top_holdings = models.JSONField(default=list, blank=True)

    is_finalized = models.BooleanField(default=False, db_index=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_concentration_snapshot"
        verbose_name = "Concentration Snapshot"
        verbose_name_plural = "Concentration Snapshots"
        unique_together = [("date", "universe")]
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.date} [{self.universe}] top10={self.top10_weight}"

    def clean(self) -> None:
        super().clean()
        if self.top5_weight > self.top10_weight:
            raise ValidationError(
                {"top5_weight": "top5_weight must be ≤ top10_weight."}
            )
        if self.top10_weight > Decimal("1.0"):
            raise ValidationError({"top10_weight": "top10_weight must be ≤ 1.0."})
        if self.hhi < Decimal("0") or self.hhi > Decimal("1.0"):
            raise ValidationError({"hhi": "hhi must be in [0, 1]."})
