from django.contrib.postgres.fields import ArrayField
from django.db import models


class ChainNewsEvent(models.Model):
    """
    Chain Sight 전용 뉴스 이벤트.
    기존 stocks.StockNews와 별도 — 동시출현, 파급 시간차 추적용.
    """

    SOURCE_CHOICES = [
        ("marketaux", "MarketAux"),
        ("finnhub", "Finnhub"),
        ("eodhd", "EODHD"),
    ]
    SENTIMENT_CHOICES = [
        ("positive", "Positive"),
        ("neutral", "Neutral"),
        ("negative", "Negative"),
    ]
    IMPORTANCE_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]

    symbol = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.PROTECT,
        to_field="symbol",
        db_column="symbol",
        related_name="chain_news_events",
    )

    # 원본
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    source_id = models.CharField(max_length=255)
    title = models.TextField()
    summary = models.TextField(blank=True)
    url = models.TextField(blank=True)
    published_at = models.DateTimeField(db_index=True)

    # 감성
    sentiment_score = models.DecimalField(
        max_digits=4, decimal_places=3, null=True, blank=True
    )
    sentiment_label = models.CharField(
        max_length=10, blank=True, choices=SENTIMENT_CHOICES
    )

    # 이벤트 태깅
    event_type = models.CharField(max_length=50, blank=True)
    event_importance = models.CharField(
        max_length=10, blank=True, choices=IMPORTANCE_CHOICES
    )

    # Chain Sight 전용: 동시출현
    co_mentioned_symbols = ArrayField(
        models.CharField(max_length=10),
        default=list,
        blank=True,
        help_text="이 기사에서 함께 언급된 다른 종목들",
    )

    # 중복 처리
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicates",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chainsight_news_event"
        unique_together = ["source", "source_id"]
        indexes = [
            models.Index(fields=["symbol", "-published_at"]),
            models.Index(fields=["symbol", "event_type"]),
            models.Index(fields=["-published_at"]),
        ]

    def __str__(self):
        return f"{self.symbol_id} [{self.source}] {self.title[:50]}"
