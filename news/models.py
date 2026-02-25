"""
뉴스 데이터 모델

NewsArticle: 뉴스 기사 메타데이터
NewsEntity: 뉴스-종목 연결 (M:N)
EntityHighlight: 엔티티별 감성 하이라이트 (Marketaux 전용)
SentimentHistory: 일별 감성 분석 집계
DailyNewsKeyword: LLM 기반 일별 뉴스 키워드 (Phase 2)
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

    # ── News Intelligence Pipeline v3 ──
    importance_score = models.FloatField(
        null=True, blank=True, db_index=True,
        help_text=_("규칙 기반 중요도 점수 (Engine C)")
    )
    rule_sectors = models.JSONField(
        null=True, blank=True,
        help_text=_("규칙 엔진 추출 섹터 리스트")
    )
    rule_tickers = models.JSONField(
        null=True, blank=True,
        help_text=_("규칙 엔진 추출 티커 리스트")
    )
    llm_analyzed = models.BooleanField(
        default=False, db_index=True,
        help_text=_("LLM 심층 분석 완료 여부")
    )
    llm_analysis = models.JSONField(
        null=True, blank=True,
        help_text=_("LLM 심층 분석 결과 JSON")
    )

    # ML Label fields
    ml_label_24h = models.FloatField(
        null=True, blank=True,
        help_text=_("발행 후 다음 거래일 변동폭 (%)")
    )
    ml_label_important = models.BooleanField(
        null=True, blank=True,
        help_text=_("섹터별 threshold 적용 중요 뉴스 여부")
    )
    ml_label_confidence = models.FloatField(
        null=True, blank=True,
        help_text=_("Label 신뢰도 (0~1)")
    )
    ml_label_updated_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("ML Label 업데이트 시간")
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
            models.Index(fields=['importance_score', '-published_at']),
            models.Index(fields=['llm_analyzed', '-published_at']),
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


class DailyNewsKeyword(models.Model):
    """
    LLM 기반 일별 뉴스 키워드 (Phase 2)

    Gemini 2.5 Flash를 사용하여 당일 뉴스에서 핵심 키워드를 추출합니다.
    키워드에는 감성 분석과 관련 종목 정보가 포함됩니다.
    """

    KEYWORD_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    date = models.DateField(
        unique=True,
        db_index=True,
        help_text=_("키워드 추출 날짜")
    )
    keywords = models.JSONField(
        default=list,
        help_text=_("""
            키워드 리스트
            [{
                "text": "AI 반도체",
                "sentiment": "positive|negative|neutral",
                "related_symbols": ["NVDA", "AMD"],
                "importance": 0.95
            }]
        """)
    )
    total_news_count = models.PositiveIntegerField(
        default=0,
        help_text=_("분석에 사용된 뉴스 총 건수")
    )
    sources = models.JSONField(
        default=dict,
        help_text=_('소스별 뉴스 건수 {"finnhub": 45, "marketaux": 5}')
    )

    # LLM 메타데이터
    status = models.CharField(
        max_length=20,
        choices=KEYWORD_STATUS_CHOICES,
        default='pending',
        help_text=_("키워드 추출 상태")
    )
    llm_model = models.CharField(
        max_length=50,
        default='gemini-2.5-flash',
        help_text=_("사용된 LLM 모델")
    )
    generation_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("LLM 생성 시간 (밀리초)")
    )
    prompt_tokens = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("프롬프트 토큰 수")
    )
    completion_tokens = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("응답 토큰 수")
    )
    error_message = models.TextField(
        blank=True,
        help_text=_("실패 시 에러 메시지")
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_news_keywords'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['-date', 'status']),
        ]

    def __str__(self):
        return f"Keywords for {self.date}: {len(self.keywords)} keywords"

    @property
    def keyword_count(self):
        """키워드 수"""
        return len(self.keywords) if self.keywords else 0

    def get_top_keywords(self, limit=5):
        """중요도 순으로 상위 N개 키워드 반환"""
        if not self.keywords:
            return []
        sorted_keywords = sorted(
            self.keywords,
            key=lambda k: k.get('importance', 0),
            reverse=True
        )
        return sorted_keywords[:limit]


class MLModelHistory(models.Model):
    """ML 모델 학습 이력 (News Intelligence Pipeline v3)"""

    DEPLOYMENT_STATUS_CHOICES = [
        ('shadow', 'Shadow Mode'),
        ('deployed', 'Deployed'),
        ('rolled_back', 'Rolled Back'),
        ('failed', 'Failed'),
    ]

    id = models.AutoField(primary_key=True)
    trained_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("학습 완료 시각")
    )
    model_version = models.CharField(
        max_length=50,
        help_text=_("모델 버전 (예: lr_v1_week8)")
    )
    algorithm = models.CharField(
        max_length=50, default='logistic_regression',
        help_text=_("알고리즘 (logistic_regression, lightgbm)")
    )
    training_samples = models.PositiveIntegerField(
        help_text=_("학습 데이터 건수")
    )
    feature_count = models.PositiveIntegerField(
        default=5,
        help_text=_("feature 수")
    )

    # Performance metrics
    f1_score = models.FloatField(
        help_text=_("F1 Score")
    )
    precision = models.FloatField(
        null=True, blank=True,
        help_text=_("Precision")
    )
    recall = models.FloatField(
        null=True, blank=True,
        help_text=_("Recall")
    )
    accuracy = models.FloatField(
        null=True, blank=True,
        help_text=_("Accuracy")
    )

    # Weights & config
    weights = models.JSONField(
        null=True, blank=True,
        help_text=_("Engine C β₁~β₅ 가중치")
    )
    smoothed_weights = models.JSONField(
        null=True, blank=True,
        help_text=_("Smoothing 적용 후 가중치 (0.7×new + 0.3×prev)")
    )
    feature_importance = models.JSONField(
        null=True, blank=True,
        help_text=_("Feature importance 리포트")
    )
    training_config = models.JSONField(
        null=True, blank=True,
        help_text=_("학습 설정 (window, split 등)")
    )

    # Safety Gate
    safety_gate_passed = models.BooleanField(
        default=False,
        help_text=_("Safety Gate 통과 여부")
    )
    safety_gate_details = models.JSONField(
        null=True, blank=True,
        help_text=_("Safety Gate 상세 결과")
    )

    # Deployment
    deployment_status = models.CharField(
        max_length=20,
        choices=DEPLOYMENT_STATUS_CHOICES,
        default='shadow',
        help_text=_("배포 상태")
    )
    deployed_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("실적용 시각")
    )

    # Shadow mode comparison
    shadow_comparison = models.JSONField(
        null=True, blank=True,
        help_text=_("Shadow Mode: ML vs 수동 선별 비교 리포트")
    )

    class Meta:
        db_table = 'ml_model_history'
        ordering = ['-trained_at']
        indexes = [
            models.Index(fields=['-trained_at', 'deployment_status']),
        ]

    def __str__(self):
        return f"{self.model_version} (F1={self.f1_score:.3f}, {self.deployment_status})"


class NewsCollectionCategory(models.Model):
    """뉴스 수집 카테고리 (Admin 정의)"""

    CATEGORY_TYPE_CHOICES = [
        ('sector', 'Sector'),
        ('sub_sector', 'Sub-Sector'),
        ('custom', 'Custom'),
    ]
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPE_CHOICES)
    value = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True, db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    max_symbols = models.PositiveIntegerField(default=20)

    # 수집 통계
    last_collected_at = models.DateTimeField(null=True, blank=True)
    last_article_count = models.PositiveIntegerField(default=0)
    last_symbol_count = models.PositiveIntegerField(default=0)
    total_collections = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'news_collection_categories'
        ordering = ['priority', 'name']
        indexes = [models.Index(fields=['is_active', 'priority'])]

    def __str__(self):
        return f"{self.name} ({self.category_type}: {self.value[:30]})"

    def resolve_symbols(self) -> list[str]:
        """카테고리 타입에 따라 심볼 리스트 해석"""
        from stocks.models import SP500Constituent

        if self.category_type == 'sector':
            return list(
                SP500Constituent.objects.filter(
                    sector=self.value, is_active=True
                ).values_list('symbol', flat=True)[:self.max_symbols]
            )
        elif self.category_type == 'sub_sector':
            return list(
                SP500Constituent.objects.filter(
                    sub_sector=self.value, is_active=True
                ).values_list('symbol', flat=True)[:self.max_symbols]
            )
        elif self.category_type == 'custom':
            return [
                s.strip().upper()
                for s in self.value.split(',')
                if s.strip()
            ][:self.max_symbols]
        return []
