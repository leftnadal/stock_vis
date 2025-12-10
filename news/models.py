"""
뉴스 데이터 모델

NewsArticle: 뉴스 기사 메타데이터
NewsEntity: 뉴스-종목 연결 (M:N)
EntityHighlight: 엔티티별 감성 하이라이트 (Marketaux 전용)
SentimentHistory: 일별 감성 분석 집계
"""

import hashlib
import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class NewsArticle(models.Model):
    """뉴스 기사 모델"""

    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('company', 'Company'),
        ('forex', 'Forex'),
        ('crypto', 'Crypto'),
        ('merger', 'Merger'),
    ]

    SENTIMENT_SOURCE_CHOICES = [
        ('marketaux', 'Marketaux'),
        ('computed', 'Computed'),
        ('none', 'None'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    url = models.URLField(
        max_length=2000,
        unique=True,
        help_text=_("원본 기사 URL")
    )
    url_hash = models.CharField(
        max_length=64,
        db_index=True,
        editable=False,
        help_text=_("URL SHA256 해시 (중복 체크용)")
    )
    title = models.CharField(
        max_length=500,
        help_text=_("기사 제목")
    )
    summary = models.TextField(
        blank=True,
        help_text=_("기사 요약")
    )
    image_url = models.URLField(
        max_length=2000,
        blank=True,
        help_text=_("대표 이미지 URL")
    )
    source = models.CharField(
        max_length=100,
        db_index=True,
        help_text=_("뉴스 출처")
    )
    published_at = models.DateTimeField(
        db_index=True,
        help_text=_("발행 일시")
    )
    language = models.CharField(
        max_length=5,
        default='en',
        help_text=_("언어 코드")
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='general',
        help_text=_("뉴스 카테고리")
    )

    # Provider IDs
    finnhub_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text=_("Finnhub 기사 ID")
    )
    marketaux_uuid = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Marketaux 기사 UUID")
    )

    # Sentiment Analysis
    sentiment_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
        db_index=True,
        validators=[
            MinValueValidator(Decimal('-1.000')),
            MaxValueValidator(Decimal('1.000'))
        ],
        help_text=_("감성 점수 (-1.000 ~ +1.000)")
    )
    sentiment_source = models.CharField(
        max_length=20,
        choices=SENTIMENT_SOURCE_CHOICES,
        default='none',
        help_text=_("감성 분석 출처")
    )

    is_press_release = models.BooleanField(
        default=False,
        help_text=_("보도 자료 여부")
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'news_articles'
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['-published_at', 'category']),
            models.Index(fields=['source', '-published_at']),
            models.Index(fields=['sentiment_score', '-published_at']),
        ]

    def save(self, *args, **kwargs):
        """URL 해시 자동 생성"""
        if not self.url_hash:
            normalized_url = self.url.lower().strip()
            self.url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title[:50]} ({self.source})"


class NewsEntity(models.Model):
    """뉴스-종목 연결 모델 (M:N)"""

    ENTITY_TYPE_CHOICES = [
        ('equity', 'Equity'),
        ('index', 'Index'),
        ('etf', 'ETF'),
        ('cryptocurrency', 'Cryptocurrency'),
        ('currency', 'Currency'),
        ('mutualfund', 'Mutual Fund'),
    ]

    news = models.ForeignKey(
        NewsArticle,
        on_delete=models.CASCADE,
        related_name='entities'
    )
    symbol = models.CharField(
        max_length=20,
        db_index=True,
        help_text=_("종목 심볼")
    )
    entity_name = models.CharField(
        max_length=200,
        help_text=_("엔티티 이름")
    )
    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPE_CHOICES,
        help_text=_("엔티티 타입")
    )
    exchange = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("거래소")
    )
    country = models.CharField(
        max_length=5,
        blank=True,
        help_text=_("국가 코드")
    )
    industry = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("산업 분류")
    )
    match_score = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        default=Decimal('1.00000'),
        validators=[
            MinValueValidator(Decimal('0.00000')),
            MaxValueValidator(Decimal('1.00000'))
        ],
        help_text=_("매칭 신뢰도")
    )
    sentiment_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
        db_index=True,
        validators=[
            MinValueValidator(Decimal('-1.000')),
            MaxValueValidator(Decimal('1.000'))
        ],
        help_text=_("엔티티별 감성 점수")
    )
    source = models.CharField(
        max_length=20,
        choices=[('finnhub', 'Finnhub'), ('marketaux', 'Marketaux')],
        help_text=_("데이터 소스")
    )

    class Meta:
        db_table = 'news_entities'
        unique_together = ['news', 'symbol']
        indexes = [
            models.Index(fields=['symbol', 'entity_type']),
            models.Index(fields=['sentiment_score']),
        ]

    def __str__(self):
        return f"{self.symbol} in {self.news.title[:30]}"


class EntityHighlight(models.Model):
    """엔티티별 감성 하이라이트 (Marketaux 전용)"""

    LOCATION_CHOICES = [
        ('title', 'Title'),
        ('main_text', 'Main Text'),
    ]

    news_entity = models.ForeignKey(
        NewsEntity,
        on_delete=models.CASCADE,
        related_name='highlights'
    )
    highlight_text = models.TextField(
        help_text=_("하이라이트 텍스트")
    )
    sentiment = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        validators=[
            MinValueValidator(Decimal('-1.000')),
            MaxValueValidator(Decimal('1.000'))
        ],
        help_text=_("하이라이트 감성 점수")
    )
    location = models.CharField(
        max_length=20,
        choices=LOCATION_CHOICES,
        help_text=_("하이라이트 위치")
    )

    class Meta:
        db_table = 'entity_highlights'
        ordering = ['-sentiment']

    def __str__(self):
        return f"{self.news_entity.symbol}: {self.highlight_text[:50]}"


class SentimentHistory(models.Model):
    """일별 감성 분석 집계"""

    symbol = models.CharField(
        max_length=20,
        db_index=True,
        help_text=_("종목 심볼")
    )
    date = models.DateField(
        db_index=True,
        help_text=_("집계 날짜")
    )
    avg_sentiment = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        validators=[
            MinValueValidator(Decimal('-1.000')),
            MaxValueValidator(Decimal('1.000'))
        ],
        help_text=_("평균 감성 점수")
    )
    news_count = models.PositiveIntegerField(
        help_text=_("뉴스 건수")
    )
    positive_count = models.PositiveIntegerField(
        default=0,
        help_text=_("긍정 뉴스 건수")
    )
    negative_count = models.PositiveIntegerField(
        default=0,
        help_text=_("부정 뉴스 건수")
    )
    neutral_count = models.PositiveIntegerField(
        default=0,
        help_text=_("중립 뉴스 건수")
    )

    class Meta:
        db_table = 'sentiment_history'
        unique_together = ['symbol', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['symbol', '-date']),
            models.Index(fields=['-date', 'avg_sentiment']),
        ]

    def __str__(self):
        return f"{self.symbol} on {self.date}: {self.avg_sentiment}"
