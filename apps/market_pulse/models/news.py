"""
뉴스 모델 (PR-A2).

소속: apps/market_pulse/models (app 레이어 Django models).
역할:
  - MarketPulseNews: 6 카테고리(MACRO·GEOPOLITICS·SECTOR·INDEX·MAG7·SMART_MONEY) 뉴스.
    matched_symbols·matched_keywords(JSON, schemas/news.py로 검증).
  - NewsViewLog: 24h 내 동일 user × 동일 news 중복 노출 방지.
TTL 정책: D5 — 노출(is_exposed=True) 영구 / 미노출 90일 만료. 정리는 tasks/finalize.py.
소비처: tasks/news.py·services/news_aggregator.py 적재, anomaly/news_pairing.py 페어링.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class MarketPulseNews(models.Model):
    class Category(models.TextChoices):
        MACRO = "MACRO", "Macro"
        GEOPOLITICS = "GEOPOLITICS", "Geopolitics"
        SECTOR = "SECTOR", "Sector"
        INDEX = "INDEX", "Index"
        MAG7 = "MAG7", "Magnificent 7"
        SMART_MONEY = "SMART_MONEY", "Smart Money"

    class Source(models.TextChoices):
        FMP_GENERAL = "FMP_GENERAL", "FMP General News"
        FMP_STOCK = "FMP_STOCK", "FMP Stock News"
        MARKETAUX = "MARKETAUX", "Marketaux"

    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    source = models.CharField(max_length=20, choices=Source.choices, db_index=True)

    title = models.CharField(max_length=500)
    summary = models.TextField(blank=True, default="")
    url = models.URLField(max_length=1024)
    url_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="URL의 SHA256 해시 (중복 제거)",
    )

    image_url = models.URLField(max_length=1024, blank=True, default="")
    publisher = models.CharField(max_length=200, blank=True, default="")

    # PR-A2 §3.2: Phase 2 LLM 한국어 번역 (현재는 빈 문자열)
    summary_ko = models.TextField(blank=True, default="")

    # PR-A2 §3.2: 엔티티 통합 필드 (matched_symbols/matched_keywords 대체)
    # 구조: {"tickers": [...], "sectors": [...], "topics": [...]}
    entities = models.JSONField(default=dict, blank=True)

    # PR-A2 §3.2: 분류·점수 메타 (PR-B fetcher가 채움. Phase 1은 default)
    category_confidence = models.FloatField(
        default=0.0, help_text="분류 신뢰도 0.0~1.0"
    )
    relevance_score = models.FloatField(default=0.0, help_text="관련도 0.0~1.0")
    sentiment_score = models.FloatField(
        null=True, blank=True, help_text="-1.0~1.0 (null=미분석)"
    )

    shown_on_layer0 = models.BooleanField(default=False, db_index=True)
    shown_at = models.DateTimeField(null=True, blank=True)
    # PR-A2 §3.2: anomaly 신호와 페어링 여부 (PR-D 페어러가 토글)
    paired_with_anomaly = models.BooleanField(default=False)

    # PR-A2 §3.2 D5 TTL 정책: 미노출 published_at + 90d, 노출 시 NULL(영구). PR-O purge task가 사용.
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    published_at = models.DateTimeField(db_index=True)
    fetched_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_news"
        verbose_name = "Market Pulse News"
        verbose_name_plural = "Market Pulse News"
        ordering = ["-published_at"]
        indexes = [
            models.Index(
                fields=["published_at", "shown_on_layer0"], name="mp_news_ttl_idx"
            ),
            models.Index(
                fields=["category", "-published_at"], name="mp_news_cat_pub_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.category}] {self.title[:80]}"

    def mark_exposed(self) -> None:
        """노출 시점 마킹 + D5 TTL 정책에 따라 expires_at NULL(영구)로 전환."""
        if not self.shown_on_layer0:
            self.shown_on_layer0 = True
            self.shown_at = timezone.now()
            self.expires_at = None  # PR-A2 §3.2 D5: shown_on_layer0=True 시점 영구 보존
            self.save(
                update_fields=[
                    "shown_on_layer0",
                    "shown_at",
                    "expires_at",
                    "updated_at",
                ]
            )


class NewsViewLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mp_news_views",
    )
    news = models.ForeignKey(
        MarketPulseNews,
        on_delete=models.CASCADE,
        related_name="view_logs",
    )

    viewed_date = models.DateField(db_index=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_news_view_log"
        verbose_name = "News View Log"
        verbose_name_plural = "News View Logs"
        unique_together = [("user", "news", "viewed_date")]
        ordering = ["-viewed_at"]
        indexes = [
            models.Index(fields=["user", "viewed_date"], name="mp_nvl_user_date_idx"),
        ]

    def __str__(self) -> str:
        return f"user={self.user_id} news={self.news_id} @ {self.viewed_date}"
