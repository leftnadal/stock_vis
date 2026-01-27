from django.db import models


class MarketMover(models.Model):
    """
    Market Movers 데이터 (상승/하락/거래량 TOP 종목)

    Phase 1: RVOL, Trend Strength
    Phase 2: Sector Alpha, ETF Sync Rate, Volatility Percentile
    """
    MOVER_TYPE_CHOICES = [
        ('gainers', 'Gainers'),
        ('losers', 'Losers'),
        ('actives', 'Actives'),
    ]

    date = models.DateField(db_index=True)
    mover_type = models.CharField(max_length=10, choices=MOVER_TYPE_CHOICES)
    rank = models.IntegerField()
    symbol = models.CharField(max_length=10, db_index=True)
    company_name = models.CharField(max_length=255)

    # 가격 정보
    price = models.DecimalField(max_digits=12, decimal_places=2)
    change_percent = models.DecimalField(max_digits=8, decimal_places=2)
    volume = models.BigIntegerField()

    # 섹터/산업 정보
    sector = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    industry = models.CharField(max_length=100, null=True, blank=True)

    # OHLC
    open_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    high = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    low = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Phase 1 지표
    rvol = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Relative Volume: 당일 거래량 / 20일 평균"
    )
    rvol_display = models.CharField(max_length=20, null=True, blank=True)

    trend_strength = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="장중 추세 강도: (종가-시가) / (고가-저가)"
    )
    trend_display = models.CharField(max_length=20, null=True, blank=True)

    # Phase 2 지표 (나중에 추가)
    sector_alpha = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="섹터 대비 초과수익"
    )
    etf_sync_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="ETF 동행률"
    )
    volatility_pct = models.IntegerField(
        null=True,
        blank=True,
        help_text="변동성 백분위 (0-100)"
    )

    # Corporate Action 정보
    has_corporate_action = models.BooleanField(
        default=False,
        help_text="기업 이벤트(분할/배당) 존재 여부"
    )
    corporate_action_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="이벤트 타입 (split, reverse_split, dividend)"
    )
    corporate_action_display = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="이벤트 표시 텍스트 (예: '1:28 역분할')"
    )

    # 메타데이터
    data_quality = models.JSONField(
        default=dict,
        help_text="데이터 품질 정보 (has_20d_volume, has_ohlc 등)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_market_mover'
        unique_together = [['date', 'mover_type', 'symbol']]
        ordering = ['date', 'mover_type', 'rank']
        indexes = [
            models.Index(fields=['date', 'mover_type']),
            models.Index(fields=['symbol', 'date']),
        ]

    def __str__(self):
        return f"{self.date} {self.mover_type} #{self.rank} {self.symbol}"


class SectorETFMapping(models.Model):
    """섹터-ETF 매핑 (Phase 2 섹터 알파 계산용)"""
    sector = models.CharField(max_length=50, unique=True)
    etf_symbol = models.CharField(max_length=10)
    sector_name = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'serverless_sector_etf_mapping'
        ordering = ['sector']

    def __str__(self):
        return f"{self.sector_name} → {self.etf_symbol}"


class StockSectorInfo(models.Model):
    """종목 섹터 정보 (Phase 2용)"""
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    sector = models.CharField(max_length=50, db_index=True)
    industry = models.CharField(max_length=100, null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_stock_sector_info'
        ordering = ['symbol']

    def __str__(self):
        return f"{self.symbol} ({self.sector})"


class VolatilityBaseline(models.Model):
    """변동성 백분위 기준 데이터 (Phase 2용)"""
    symbol = models.CharField(max_length=10, db_index=True)
    date = models.DateField()

    # 20일 히스토리 기반 변동성 백분위
    volatility = models.DecimalField(max_digits=8, decimal_places=4)
    percentile = models.IntegerField(help_text="0-100 백분위")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'serverless_volatility_baseline'
        unique_together = [['symbol', 'date']]
        ordering = ['symbol', '-date']

    def __str__(self):
        return f"{self.symbol} {self.date} P{self.percentile}"


class StockKeyword(models.Model):
    """
    Market Movers 종목별 AI 생성 키워드

    LLM이 생성한 3-5개의 핵심 키워드를 저장합니다.
    일일 배치로 생성되며, TTL은 7일입니다.

    Note: FK 없이 symbol로 직접 매핑 (독립적 TTL 관리)
    """

    # 종목 정보 (FK 없이 symbol로 직접 매핑)
    symbol = models.CharField(max_length=10, db_index=True)
    company_name = models.CharField(max_length=255)

    # 생성 일자
    date = models.DateField(db_index=True)

    # 키워드 리스트 (3-5개)
    keywords = models.JSONField(
        help_text="LLM 생성 키워드 리스트 (3-5개)",
        default=list
    )
    # 예시: ["AI 반도체 수요", "데이터센터 확장", "실적 서프라이즈"]

    # 메타데이터
    llm_model = models.CharField(
        max_length=50,
        default="gemini-2.5-flash",
        help_text="사용된 LLM 모델"
    )
    generation_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="키워드 생성 소요 시간 (밀리초)"
    )
    prompt_tokens = models.IntegerField(
        null=True,
        blank=True,
        help_text="입력 토큰 수"
    )
    completion_tokens = models.IntegerField(
        null=True,
        blank=True,
        help_text="출력 토큰 수"
    )

    # 생성 상태
    STATUS_CHOICES = [
        ('pending', 'Pending'),      # 생성 대기
        ('processing', 'Processing'), # 생성 중
        ('completed', 'Completed'),   # 성공
        ('failed', 'Failed'),         # 실패
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="실패 시 에러 메시지"
    )

    # TTL 관리
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="키워드 만료 시점 (생성일 + 7일)"
    )

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_stock_keyword'
        unique_together = [['symbol', 'date']]
        ordering = ['-date', 'symbol']
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['symbol', '-date']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.symbol} ({self.date}): {len(self.keywords)}개 키워드"

    def save(self, *args, **kwargs):
        """expires_at 자동 설정"""
        if not self.expires_at:
            from datetime import timedelta
            from django.utils import timezone
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)


class CorporateAction(models.Model):
    """
    기업 이벤트 (주식분할, 역분할, 배당 등) 기록

    가격 변동 ±50% 이상 시 yfinance로 자동 감지합니다.
    """

    ACTION_TYPES = [
        ('reverse_split', '역주식분할'),
        ('split', '주식분할'),
        ('spinoff', '분사'),
        ('dividend', '특별배당'),
    ]

    symbol = models.CharField(max_length=10, db_index=True)
    date = models.DateField(db_index=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    ratio = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="분할/역분할 비율"
    )
    dividend_amount = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="배당금 (USD)"
    )
    display_text = models.CharField(
        max_length=50,
        help_text="표시 텍스트 (예: '1:28 역분할')"
    )
    source = models.CharField(max_length=20, default='yfinance')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'serverless_corporate_action'
        unique_together = [['symbol', 'date', 'action_type']]
        ordering = ['-date', 'symbol']
        indexes = [
            models.Index(fields=['symbol', 'date']),
        ]

    def __str__(self):
        return f"{self.symbol} ({self.date}): {self.display_text}"
