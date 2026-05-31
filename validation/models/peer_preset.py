from django.contrib.postgres.fields import ArrayField
from django.db import models


class PeerPreset(models.Model):
    """
    종목당 2~6개 peer 비교 프리셋.
    배치에서 자동 생성. 각 프리셋은 서로 다른 분석 질문에 답함.
    """

    GENERATION_METHOD_CHOICES = [
        ("auto_industry", "업종 자동"),
        ("auto_sector", "섹터 자동"),
        ("auto_size", "규모 자동"),
        ("auto_quality", "품질 자동"),
        ("auto_lifecycle", "성장단계 자동"),
        ("curated", "큐레이션"),
    ]

    symbol = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        to_field="symbol",
        db_column="symbol",
        related_name="peer_presets",
    )
    preset_key = models.CharField(max_length=30)
    display_name = models.CharField(max_length=50)
    logic_summary = models.CharField(max_length=200)
    peer_symbols = ArrayField(models.CharField(max_length=10), default=list)
    peer_count = models.IntegerField(default=0)
    generation_method = models.CharField(
        max_length=20, choices=GENERATION_METHOD_CHOICES
    )
    confidence_score = models.FloatField(default=1.0)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["symbol", "preset_key"]
        db_table = "validation_peer_preset"

    def __str__(self):
        return f"{self.symbol_id} [{self.preset_key}] {self.peer_count} peers"


class UserPeerPreference(models.Model):
    """
    사용자별 peer 프리셋 선택 또는 커스텀 peer 설정.
    User 영역 — Stock 테이블과 완전 분리.
    """

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="peer_preferences"
    )
    symbol = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        to_field="symbol",
        db_column="symbol",
    )
    mode = models.CharField(
        max_length=10,
        default="preset",
        choices=[("preset", "프리셋"), ("custom", "커스텀")],
    )
    preset_key = models.CharField(max_length=30, default="default")
    custom_peers = ArrayField(models.CharField(max_length=10), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "symbol"]
        db_table = "validation_user_peer_preference"

    def __str__(self):
        return f"{self.user_id} {self.symbol_id}: {self.mode}/{self.preset_key}"
