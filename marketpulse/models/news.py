"""
Market Pulse v2 뉴스 모델 (PR-A2)

- MarketPulseNews: 6 카테고리(MACRO/GEOPOLITICS/SECTOR/INDEX/MAG7/SMART_MONEY)
- NewsViewLog: 24h 내 동일 user에 동일 news 중복 노출 방지

D5 (노출 영구/미노출 90일 TTL) 정책 적용. TTL purge는 PR-O에서 처리.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class MarketPulseNews(models.Model):
    class Category(models.TextChoices):
        MACRO = 'MACRO', 'Macro'
        GEOPOLITICS = 'GEOPOLITICS', 'Geopolitics'
        SECTOR = 'SECTOR', 'Sector'
        INDEX = 'INDEX', 'Index'
        MAG7 = 'MAG7', 'Magnificent 7'
        SMART_MONEY = 'SMART_MONEY', 'Smart Money'

    class Source(models.TextChoices):
        FMP_GENERAL = 'FMP_GENERAL', 'FMP General News'
        FMP_STOCK = 'FMP_STOCK', 'FMP Stock News'
        MARKETAUX = 'MARKETAUX', 'Marketaux'

    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    source = models.CharField(max_length=20, choices=Source.choices, db_index=True)

    title = models.CharField(max_length=500)
    summary = models.TextField(blank=True, default='')
    url = models.URLField(max_length=1024)
    url_hash = models.CharField(
        max_length=64, unique=True, help_text='URL의 SHA256 해시 (중복 제거)',
    )

    image_url = models.URLField(max_length=1024, blank=True, default='')
    publisher = models.CharField(max_length=200, blank=True, default='')

    matched_symbols = models.JSONField(default=list, blank=True)
    matched_keywords = models.JSONField(default=list, blank=True)

    is_exposed = models.BooleanField(default=False, db_index=True)
    first_exposed_at = models.DateTimeField(null=True, blank=True)

    published_at = models.DateTimeField(db_index=True)
    fetched_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mp_news'
        verbose_name = 'Market Pulse News'
        verbose_name_plural = 'Market Pulse News'
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['published_at', 'is_exposed'], name='mp_news_ttl_idx'),
            models.Index(fields=['category', '-published_at'], name='mp_news_cat_pub_idx'),
        ]

    def __str__(self) -> str:
        return f'[{self.category}] {self.title[:80]}'

    def mark_exposed(self) -> None:
        if not self.is_exposed:
            self.is_exposed = True
            self.first_exposed_at = timezone.now()
            self.save(update_fields=['is_exposed', 'first_exposed_at', 'updated_at'])


class NewsViewLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mp_news_views',
    )
    news = models.ForeignKey(
        MarketPulseNews,
        on_delete=models.CASCADE,
        related_name='view_logs',
    )

    viewed_date = models.DateField(db_index=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mp_news_view_log'
        verbose_name = 'News View Log'
        verbose_name_plural = 'News View Logs'
        unique_together = [('user', 'news', 'viewed_date')]
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['user', 'viewed_date'], name='mp_nvl_user_date_idx'),
        ]

    def __str__(self) -> str:
        return f'user={self.user_id} news={self.news_id} @ {self.viewed_date}'
