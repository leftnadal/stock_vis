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


class MarketBreadth(models.Model):
    """
    시장 건강도 지표 (서버리스 전환 대상)

    상승/하락 비율, 신고가/신저가, 거래량 흐름을 통해
    "지금 시장이 좋은가?"를 한눈에 파악할 수 있는 지표.

    데이터 소스: FMP API (gainers/losers + market performance)
    """
    date = models.DateField(unique=True, db_index=True)

    # 상승/하락/보합 종목 수
    advancing_count = models.IntegerField(default=0, help_text="상승 종목 수")
    declining_count = models.IntegerField(default=0, help_text="하락 종목 수")
    unchanged_count = models.IntegerField(default=0, help_text="보합 종목 수")

    # 52주 신고가/신저가
    new_highs = models.IntegerField(default=0, help_text="52주 신고가 종목 수")
    new_lows = models.IntegerField(default=0, help_text="52주 신저가 종목 수")

    # 거래량 흐름
    up_volume = models.BigIntegerField(default=0, help_text="상승 종목 총 거래량")
    down_volume = models.BigIntegerField(default=0, help_text="하락 종목 총 거래량")

    # 계산된 비율
    advance_decline_ratio = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=1.0,
        help_text="상승/하락 비율 (advancing / declining)"
    )
    advance_decline_line = models.IntegerField(
        default=0,
        help_text="A/D Line (누적 상승-하락)"
    )

    # 시장 신호
    SIGNAL_CHOICES = [
        ('strong_bullish', '강한 상승'),
        ('bullish', '상승'),
        ('neutral', '중립'),
        ('bearish', '하락'),
        ('strong_bearish', '강한 하락'),
    ]
    breadth_signal = models.CharField(
        max_length=20,
        choices=SIGNAL_CHOICES,
        default='neutral',
        help_text="시장 건강도 신호"
    )

    # 추가 지표
    new_high_low_ratio = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="신고가/신저가 비율"
    )
    volume_ratio = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="상승종목 거래량 / 하락종목 거래량"
    )

    # 메타데이터
    data_source = models.CharField(max_length=50, default='fmp')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_market_breadth'
        ordering = ['-date']
        verbose_name = 'Market Breadth'
        verbose_name_plural = 'Market Breadths'

    def __str__(self):
        return f"{self.date} Breadth: {self.breadth_signal} (A/D: {self.advance_decline_ratio})"


class ScreenerPreset(models.Model):
    """
    스크리너 프리셋 (서버리스 전환 대상)

    시스템 프리셋(초보자/중급자용)과 사용자 정의 프리셋을 관리.
    """
    CATEGORY_CHOICES = [
        ('system', '시스템 프리셋'),
        ('beginner', '초보자용'),
        ('intermediate', '중급자용'),
        ('advanced', '고급자용'),
        ('custom', '사용자 정의'),
    ]

    PRESET_TYPE_CHOICES = [
        ('instant', 'Instant'),      # FMP 직접 지원 필터만 사용 → 즉시 실행
        ('enhanced', 'Enhanced'),    # 추가 API 호출 필요 (PE/ROE/EPS Growth 등)
    ]

    # 사용자 (null이면 시스템 프리셋)
    user = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='screener_presets'
    )

    # 기본 정보
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    description_ko = models.TextField(blank=True, help_text="한국어 설명")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='custom')
    preset_type = models.CharField(
        max_length=20,
        choices=PRESET_TYPE_CHOICES,
        default='instant',
        help_text="instant: FMP 직접 지원, enhanced: 추가 API 필요 (PE/ROE/EPS 등)"
    )
    icon = models.CharField(max_length=10, default='📊', help_text="이모지 아이콘")

    # 필터 조건 (JSON)
    filters_json = models.JSONField(
        default=dict,
        help_text="필터 조건 (예: {'pe_max': 20, 'roe_min': 15})"
    )

    # 정렬 조건
    sort_by = models.CharField(max_length=50, default='change_percent', help_text="정렬 기준")
    sort_order = models.CharField(max_length=10, default='desc', help_text="정렬 방향")

    # 공유 설정
    is_public = models.BooleanField(default=False, help_text="공개 프리셋 여부")
    share_code = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=True,
        help_text="공유 코드 (URL 인코딩용)"
    )

    # 통계
    use_count = models.IntegerField(default=0, help_text="사용 횟수")
    view_count = models.IntegerField(default=0, help_text="조회 횟수 (Phase 2.1)")
    last_used_at = models.DateTimeField(null=True, blank=True)

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_screener_preset'
        ordering = ['-use_count', 'name']
        indexes = [
            models.Index(fields=['category', '-use_count']),
            models.Index(fields=['user', '-use_count']),
            models.Index(fields=['share_code']),
            models.Index(fields=['is_public', '-view_count']),  # Phase 2.1: 트렌딩용
        ]

    def __str__(self):
        owner = self.user.email if self.user else 'System'
        return f"{self.icon} {self.name} ({owner})"


class ScreenerFilter(models.Model):
    """
    필터 정의 메타데이터 (서버리스 전환 대상)

    프론트엔드 필터 UI 렌더링 및 백엔드 필터 검증에 사용.
    50개 이상의 필터를 카테고리별로 관리.
    """
    CATEGORY_CHOICES = [
        ('price', '가격'),
        ('volume', '거래량'),
        ('fundamental', '펀더멘탈'),
        ('technical', '기술적'),
        ('dividend', '배당'),
        ('other', '기타'),
    ]

    OPERATOR_CHOICES = [
        ('range', '범위 (min-max)'),
        ('gte', '이상'),
        ('lte', '이하'),
        ('eq', '동일'),
        ('select', '선택'),
        ('multi_select', '다중 선택'),
        ('boolean', '참/거짓'),
    ]

    # 필터 ID (예: 'pe_ratio', 'market_cap')
    filter_id = models.CharField(max_length=50, primary_key=True)

    # 카테고리
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    # 표시 정보
    label = models.CharField(max_length=100, help_text="영문 라벨")
    label_ko = models.CharField(max_length=100, help_text="한국어 라벨")
    description = models.TextField(blank=True, help_text="필터 설명")
    description_ko = models.TextField(blank=True, help_text="한국어 설명")

    # 데이터 필드 매핑
    data_field = models.CharField(max_length=100, help_text="API/DB 필드명")
    api_param = models.CharField(max_length=100, blank=True, help_text="FMP API 파라미터명")

    # 연산자 타입
    operator_type = models.CharField(max_length=20, choices=OPERATOR_CHOICES, default='range')

    # 값 제약
    unit = models.CharField(max_length=20, blank=True, help_text="단위 (%, $, B 등)")
    min_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    max_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    default_min = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    default_max = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    step = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="증가 단위")

    # 선택 옵션 (select/multi_select 타입용)
    options = models.JSONField(
        default=list,
        blank=True,
        help_text="선택 옵션 리스트"
    )

    # KB 연동
    tooltip_key = models.CharField(max_length=50, blank=True, help_text="KB 문서 키")

    # 표시 순서 및 상태
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False, help_text="프리미엄 전용 필터")
    is_popular = models.BooleanField(default=False, help_text="인기 필터")

    # FMP API 지원 여부
    fmp_supported = models.BooleanField(default=True, help_text="FMP API에서 직접 지원")

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_screener_filter'
        ordering = ['category', 'display_order', 'label']

    def __str__(self):
        return f"[{self.category}] {self.label_ko} ({self.filter_id})"


class SectorPerformance(models.Model):
    """
    섹터별 일일 성과 (히트맵용, 서버리스 전환 대상)

    11개 섹터의 일일 성과를 저장하여 히트맵 시각화에 사용.
    """
    SECTOR_CHOICES = [
        ('Technology', '기술'),
        ('Healthcare', '헬스케어'),
        ('Financial Services', '금융'),
        ('Consumer Cyclical', '경기소비재'),
        ('Industrials', '산업재'),
        ('Energy', '에너지'),
        ('Communication Services', '통신'),
        ('Real Estate', '부동산'),
        ('Utilities', '유틸리티'),
        ('Basic Materials', '소재'),
        ('Consumer Defensive', '필수소비재'),
    ]

    date = models.DateField(db_index=True)
    sector = models.CharField(max_length=50, choices=SECTOR_CHOICES)

    # 성과 지표
    return_pct = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        help_text="일일 수익률 (%)"
    )
    market_cap = models.BigIntegerField(help_text="섹터 총 시가총액")
    stock_count = models.IntegerField(help_text="섹터 내 종목 수")

    # ETF 정보
    etf_symbol = models.CharField(max_length=10, help_text="대표 ETF")
    etf_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    etf_change_pct = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)

    # Top Movers
    top_gainers = models.JSONField(default=list, help_text="상위 상승 종목 (symbol, name, change_pct)")
    top_losers = models.JSONField(default=list, help_text="상위 하락 종목 (symbol, name, change_pct)")

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'serverless_sector_performance'
        unique_together = [['date', 'sector']]
        ordering = ['-date', 'sector']
        indexes = [
            models.Index(fields=['date', '-return_pct']),
        ]

    def __str__(self):
        sign = '+' if self.return_pct >= 0 else ''
        return f"{self.date} {self.sector}: {sign}{self.return_pct}%"


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


# ========================================
# Screener Alert System (Phase 1)
# ========================================

class ScreenerAlert(models.Model):
    """
    스크리너 알림 설정

    사용자가 설정한 조건에 맞는 종목이 발견되면 알림을 발송합니다.
    프리셋 기반 또는 커스텀 필터 기반으로 설정 가능합니다.
    """
    ALERT_TYPE_CHOICES = [
        ('filter_match', '필터 조건 충족'),
        ('price_target', '목표가 도달'),
        ('volume_spike', '거래량 급증'),
        ('ai_signal', 'AI 신호'),
        ('new_high', '신고가'),
        ('new_low', '신저가'),
    ]

    # 사용자 (필수)
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='screener_alerts'
    )

    # 알림 설정
    name = models.CharField(max_length=100, help_text="알림 이름")
    description = models.TextField(blank=True, help_text="알림 설명")

    # 프리셋 기반 또는 커스텀 필터
    preset = models.ForeignKey(
        'ScreenerPreset',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='alerts',
        help_text="프리셋 기반 알림 (null이면 커스텀 필터)"
    )
    filters_json = models.JSONField(
        default=dict,
        help_text="커스텀 필터 조건 (프리셋 없을 때 사용)"
    )

    # 알림 타입 및 조건
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPE_CHOICES,
        default='filter_match'
    )
    target_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="필터 매칭 종목 수 임계값 (예: 10개 이상이면 알림)"
    )
    target_symbols = models.JSONField(
        default=list,
        blank=True,
        help_text="특정 종목 모니터링 (price_target용)"
    )

    # 알림 상태
    is_active = models.BooleanField(default=True, help_text="알림 활성화 여부")
    cooldown_hours = models.IntegerField(
        default=24,
        help_text="동일 조건 재알림 대기 시간 (시간)"
    )

    # 알림 이력
    last_triggered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="마지막 알림 발송 시간"
    )
    trigger_count = models.IntegerField(default=0, help_text="총 알림 발송 횟수")

    # 알림 채널 (향후 확장용)
    notify_in_app = models.BooleanField(default=True, help_text="인앱 알림")
    notify_email = models.BooleanField(default=False, help_text="이메일 알림")
    notify_push = models.BooleanField(default=False, help_text="푸시 알림 (PWA)")

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_screener_alert'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['is_active', '-created_at']),
        ]

    def __str__(self):
        status = "활성" if self.is_active else "비활성"
        return f"[{status}] {self.name} ({self.user.email})"

    def get_effective_filters(self):
        """
        실제 적용될 필터 반환 (프리셋 또는 커스텀)
        """
        if self.preset:
            return self.preset.filters_json
        return self.filters_json

    def can_trigger(self):
        """
        쿨다운 체크 - 알림 발송 가능 여부
        """
        if not self.is_active:
            return False
        if not self.last_triggered_at:
            return True

        from django.utils import timezone
        from datetime import timedelta

        cooldown_end = self.last_triggered_at + timedelta(hours=self.cooldown_hours)
        return timezone.now() >= cooldown_end


class AlertHistory(models.Model):
    """
    알림 발송 이력

    스크리너 알림이 발송될 때마다 기록됩니다.
    """
    alert = models.ForeignKey(
        ScreenerAlert,
        on_delete=models.CASCADE,
        related_name='history'
    )

    # 발송 정보
    triggered_at = models.DateTimeField(auto_now_add=True)

    # 매칭 결과
    matched_count = models.IntegerField(help_text="매칭된 종목 수")
    matched_symbols = models.JSONField(
        default=list,
        help_text="매칭된 종목 리스트 (최대 10개)"
    )
    snapshot = models.JSONField(
        default=dict,
        help_text="알림 시점 필터 조건 스냅샷"
    )

    # 발송 상태
    STATUS_CHOICES = [
        ('sent', '발송 완료'),
        ('failed', '발송 실패'),
        ('skipped', '쿨다운으로 스킵'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    error_message = models.TextField(blank=True, help_text="실패 시 에러 메시지")

    # 사용자 확인
    read_at = models.DateTimeField(null=True, blank=True, help_text="사용자 확인 시간")
    dismissed = models.BooleanField(default=False, help_text="알림 해제 여부")

    class Meta:
        db_table = 'serverless_alert_history'
        ordering = ['-triggered_at']
        indexes = [
            models.Index(fields=['alert', '-triggered_at']),
            models.Index(fields=['triggered_at']),
        ]

    def __str__(self):
        return f"{self.alert.name} @ {self.triggered_at.strftime('%Y-%m-%d %H:%M')}"


class InvestmentThesis(models.Model):
    """
    투자 테제 (Phase 2 - Chain Sight DNA)

    스크리너 결과에서 AI가 생성한 투자 테제를 저장합니다.
    """
    # 사용자
    user = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='investment_theses'
    )

    # 테제 기본 정보
    title = models.CharField(max_length=200, help_text="투자 테제 제목")
    summary = models.TextField(help_text="투자 테제 요약 (1-2문장)")

    # 필터 기반
    filters_snapshot = models.JSONField(
        default=dict,
        help_text="테제 생성 시 적용된 필터"
    )
    preset_ids = models.JSONField(
        default=list,
        help_text="사용된 프리셋 IDs"
    )

    # 테제 내용
    key_metrics = models.JSONField(
        default=list,
        help_text="핵심 지표 (예: ['PER < 15', 'ROE > 20%'])"
    )
    top_picks = models.JSONField(
        default=list,
        help_text="추천 종목 (최대 5개)"
    )
    risks = models.JSONField(
        default=list,
        help_text="리스크 요인"
    )
    rationale = models.TextField(blank=True, help_text="투자 근거 상세")

    # AI 메타데이터
    llm_model = models.CharField(max_length=50, default='gemini-2.5-flash')
    generation_time_ms = models.IntegerField(null=True, blank=True)

    # 공유 설정
    is_public = models.BooleanField(default=False)
    share_code = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=True
    )

    # 통계
    view_count = models.IntegerField(default=0)
    save_count = models.IntegerField(default=0)

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_investment_thesis'
        ordering = ['-created_at']
        verbose_name_plural = 'Investment Theses'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_public', '-view_count']),
            models.Index(fields=['share_code']),
        ]

    def __str__(self):
        owner = self.user.email if self.user else 'Anonymous'
        return f"{self.title} ({owner})"


# ========================================
# Chain Sight Stock (개별 종목 연관 탐험)
# ========================================

class StockRelationship(models.Model):
    """
    주식 간 관계 저장 (Chain Sight Stock용)

    개별 주식 페이지에서 사용되는 관계 데이터입니다.
    경쟁사, 동일 산업, 뉴스 동시언급 등 관계를 저장합니다.
    """
    RELATIONSHIP_TYPES = [
        ('PEER_OF', '경쟁사'),
        ('SAME_INDUSTRY', '동일 산업'),
        ('CO_MENTIONED', '뉴스 동시언급'),
        ('HAS_THEME', '테마 공유'),       # Phase 2
        ('SUPPLIED_BY', '공급사'),        # Phase 4
        ('CUSTOMER_OF', '고객사'),        # Phase 4
        # Phase 5: LLM 추출 관계
        ('ACQUIRED', '인수'),             # A acquired B
        ('INVESTED_IN', '투자'),          # A invested in B
        ('PARTNER_OF', '파트너'),         # A partnered with B
        ('SPIN_OFF', '분사'),             # A spun off B
        ('SUED_BY', '소송'),              # A sued by B
        # Phase 7: Institutional Holdings
        ('HELD_BY_SAME_FUND', '동일 펀드 보유'),
        # Phase 8: Regulatory + Patent
        ('SAME_REGULATION', '규제 공유'),
        ('PATENT_CITED', '특허 인용'),
        ('PATENT_DISPUTE', '특허 분쟁'),
    ]

    SOURCE_PROVIDERS = [
        ('finnhub', 'Finnhub Peers API'),
        ('fmp', 'FMP Company Profile'),
        ('news', 'NewsEntity Co-mention'),
        ('manual', 'Manual Entry'),
        ('ai', 'AI Generated'),
        ('llm_news', 'LLM News Extraction'),    # Phase 5
        ('llm_sec', 'LLM SEC Filing Extraction'),  # Phase 5
        ('sec_13f', 'SEC 13F Filing'),        # Phase 7
        ('sec_8k', 'SEC 8-K Filing'),          # Phase 8
        ('regulatory_llm', 'Regulatory LLM'),  # Phase 8
        ('uspto', 'USPTO PatentsView'),         # Phase 8
    ]

    source_symbol = models.CharField(max_length=10, db_index=True)
    target_symbol = models.CharField(max_length=10, db_index=True)
    relationship_type = models.CharField(max_length=20, choices=RELATIONSHIP_TYPES)
    strength = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        default=1.0,
        help_text="관계 강도 (0.0 ~ 1.0)"
    )
    source_provider = models.CharField(
        max_length=20,
        choices=SOURCE_PROVIDERS,
        default='manual'
    )
    context = models.JSONField(
        default=dict,
        help_text="관계 컨텍스트 (예: 뉴스 헤드라인, 산업 분류 등)"
    )
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_verified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_stock_relationship'
        unique_together = [['source_symbol', 'target_symbol', 'relationship_type']]
        indexes = [
            models.Index(fields=['source_symbol', 'relationship_type']),
            models.Index(fields=['target_symbol', 'relationship_type']),
            models.Index(fields=['source_symbol', '-strength']),
        ]

    def __str__(self):
        return f"{self.source_symbol} --{self.relationship_type}--> {self.target_symbol}"


class CategoryCache(models.Model):
    """
    AI 생성 카테고리 캐시 (Chain Sight Stock용)

    개별 종목에 대해 AI가 생성한 카테고리(경쟁사, AI 반도체 생태계 등)를 캐싱합니다.
    24시간 TTL로 관리됩니다.
    """
    symbol = models.CharField(max_length=10, db_index=True)
    date = models.DateField(db_index=True)
    categories = models.JSONField(
        default=list,
        help_text="카테고리 리스트 [{id, name, tier, count, description, icon}]"
    )
    # 예시: [
    #   {"id": "peer", "name": "경쟁사", "tier": 0, "count": 5, "icon": "⚔️"},
    #   {"id": "ai_ecosystem", "name": "AI 반도체 생태계", "tier": 1, "count": 8, "icon": "🧠"}
    # ]
    llm_model = models.CharField(max_length=50, default='gemini-2.5-flash')
    generation_time_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="캐시 만료 시점 (생성일 + 24시간)")

    class Meta:
        db_table = 'serverless_category_cache'
        unique_together = [['symbol', 'date']]
        indexes = [
            models.Index(fields=['symbol', 'date']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.symbol} ({self.date}): {len(self.categories)}개 카테고리"

    def save(self, *args, **kwargs):
        """expires_at 자동 설정"""
        if not self.expires_at:
            from datetime import timedelta
            from django.utils import timezone
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)


# ========================================
# Chain Sight Phase 3: ETF Holdings
# ========================================

class ETFProfile(models.Model):
    """
    ETF 기본 정보

    운용사 CSV 직링크 기반 Holdings 수집용.
    Tier 1 (섹터 ETF): XLK, XLV 등 11개
    Tier 2 (테마 ETF): SOXX, ARKK 등 10+개
    """
    TIER_CHOICES = [
        ('sector', '섹터 ETF'),      # Tier 1: S&P 500 섹터 커버리지
        ('theme', '테마 ETF'),       # Tier 2: 중소형주 발견용
    ]

    PARSER_CHOICES = [
        ('spdr', 'State Street (SPDR)'),
        ('ishares', 'iShares (BlackRock)'),
        ('ark', 'ARK Invest'),
        ('invesco', 'Invesco'),
        ('vanguard', 'Vanguard'),
        ('generic', 'Generic CSV'),
    ]

    symbol = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=200)
    tier = models.CharField(max_length=10, choices=TIER_CHOICES)
    theme_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="테마 식별자 (예: semiconductor, ai, ev)"
    )

    # CSV 소스 정보
    csv_url = models.URLField(max_length=500, blank=True)
    parser_type = models.CharField(
        max_length=20,
        choices=PARSER_CHOICES,
        default='generic'
    )

    # 수집 상태
    last_updated = models.DateTimeField(null=True, blank=True)
    last_row_count = models.IntegerField(default=0)
    last_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="CSV 콘텐츠 해시 (변경 감지용)"
    )
    last_error = models.TextField(blank=True, help_text="마지막 수집 에러")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'serverless_etf_profile'
        ordering = ['tier', 'symbol']
        indexes = [
            models.Index(fields=['tier', 'is_active']),
            models.Index(fields=['theme_id']),
        ]

    def __str__(self):
        return f"[{self.tier}] {self.symbol}: {self.name}"


class ETFHolding(models.Model):
    """
    ETF 구성 종목

    운용사 CSV에서 파싱한 Holdings 데이터.
    전체 Holdings 저장 (상위 30개 제한 없음).
    """
    etf = models.ForeignKey(
        ETFProfile,
        on_delete=models.CASCADE,
        related_name='holdings'
    )
    stock_symbol = models.CharField(max_length=10, db_index=True)
    weight_percent = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        help_text="비중 (%)"
    )
    shares = models.BigIntegerField(null=True, blank=True, help_text="보유 주식 수")
    rank = models.IntegerField(help_text="비중 순위")
    market_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="시장 가치 (USD)"
    )
    snapshot_date = models.DateField()

    class Meta:
        db_table = 'serverless_etf_holding'
        unique_together = [['etf', 'stock_symbol', 'snapshot_date']]
        ordering = ['etf', 'rank']
        indexes = [
            models.Index(fields=['stock_symbol', 'snapshot_date']),
            models.Index(fields=['etf', 'rank']),
        ]

    def __str__(self):
        return f"{self.etf.symbol}: {self.stock_symbol} ({self.weight_percent}%)"


class ThemeMatch(models.Model):
    """
    테마 매칭 결과 (Tier A + Tier B)

    Tier A (confidence: high): ETF Holdings 기반 확정 테마
    Tier B (confidence: medium): 키워드 매칭 기반 추정 테마
    Tier B+ (confidence: medium-high): 다중 근거로 승격된 테마
    """
    CONFIDENCE_CHOICES = [
        ('high', 'High'),           # Tier A: ETF Holdings 확인
        ('medium-high', 'Medium-High'),  # Tier B 승격
        ('medium', 'Medium'),       # Tier B: 키워드 매칭
    ]

    SOURCE_CHOICES = [
        ('etf_holding', 'ETF Holdings'),
        ('keyword', 'Keyword Matching'),
        ('co_mentioned', 'Co-mentioned with Theme'),
        ('multi_etf', 'Multiple ETF Match'),
    ]

    stock_symbol = models.CharField(max_length=10, db_index=True)
    theme_id = models.CharField(max_length=50, db_index=True)
    confidence = models.CharField(
        max_length=20,
        choices=CONFIDENCE_CHOICES,
        default='medium'
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='keyword'
    )

    # Tier A 전용 필드
    etf_symbol = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Tier A: Holdings 출처 ETF"
    )
    weight_in_etf = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Tier A: ETF 내 비중 (%)"
    )

    # 근거 목록
    evidence = models.JSONField(
        default=list,
        help_text="매칭 근거 리스트"
    )
    # 예시: ["SOXX 상위 10위", "반도체 관련 키워드 다수", "NVDA와 뉴스 동시언급"]

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_theme_match'
        unique_together = [['stock_symbol', 'theme_id']]
        ordering = ['stock_symbol', 'theme_id']
        indexes = [
            models.Index(fields=['theme_id', 'confidence']),
            models.Index(fields=['stock_symbol', '-confidence']),
        ]

    def __str__(self):
        return f"{self.stock_symbol} → {self.theme_id} ({self.confidence})"


# ========================================
# Chain Sight Phase 5: LLM Relation Extraction
# ========================================

class LLMExtractedRelation(models.Model):
    """
    LLM이 추출한 기업 관계 (Phase 5)

    뉴스/SEC 공시에서 Gemini가 추출한 관계 데이터입니다.
    30일 TTL로 관리되며, StockRelationship으로 동기화됩니다.

    관계 타입:
    - ACQUIRED: 인수 (예: Microsoft acquired Activision)
    - INVESTED_IN: 투자 (예: SoftBank invested in Arm)
    - PARTNER_OF: 파트너십 (예: Apple partnered with Goldman Sachs)
    - SPIN_OFF: 분사 (예: GE spun off GE Healthcare)
    - SUED_BY: 소송 (예: Apple sued by Epic Games)
    """

    RELATION_TYPES = [
        ('ACQUIRED', '인수'),
        ('INVESTED_IN', '투자'),
        ('PARTNER_OF', '파트너'),
        ('SPIN_OFF', '분사'),
        ('SUED_BY', '소송'),
    ]

    SOURCE_TYPES = [
        ('news', '뉴스'),
        ('sec_10k', 'SEC 10-K'),
        ('sec_8k', 'SEC 8-K'),
        ('sec_13f', 'SEC 13-F'),
    ]

    CONFIDENCE_LEVELS = [
        ('high', 'High'),        # LLM 점수 0.8+ 또는 SEC 공시 확인
        ('medium', 'Medium'),    # LLM 점수 0.6-0.8
        ('low', 'Low'),          # LLM 점수 0.6 미만
    ]

    # 관계 당사자
    source_symbol = models.CharField(
        max_length=10,
        db_index=True,
        help_text="관계의 주체 (예: MSFT in 'MSFT acquired ATVI')"
    )
    target_symbol = models.CharField(
        max_length=10,
        db_index=True,
        help_text="관계의 대상 (예: ATVI in 'MSFT acquired ATVI')"
    )
    relation_type = models.CharField(
        max_length=20,
        choices=RELATION_TYPES,
        db_index=True
    )

    # 출처 정보
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPES,
        default='news'
    )
    source_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="뉴스 UUID 또는 SEC 파일링 ID"
    )
    source_url = models.URLField(
        null=True,
        blank=True,
        help_text="원본 소스 URL"
    )

    # 추출 컨텍스트
    evidence = models.TextField(
        help_text="관계를 증명하는 원문 발췌 (최대 500자)"
    )
    context = models.JSONField(
        default=dict,
        help_text="추가 컨텍스트 (금액, 날짜, 조건 등)"
    )
    # 예시: {"deal_value": "68.7B", "announced_date": "2022-01-18", "status": "completed"}

    # 신뢰도
    confidence = models.CharField(
        max_length=20,
        choices=CONFIDENCE_LEVELS,
        default='medium'
    )
    llm_confidence_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="LLM이 반환한 신뢰도 점수 (0.0 ~ 1.0)"
    )

    # LLM 메타데이터
    llm_model = models.CharField(
        max_length=50,
        default='gemini-2.5-flash'
    )
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    extraction_time_ms = models.IntegerField(null=True, blank=True)

    # 상태 관리
    is_verified = models.BooleanField(
        default=False,
        help_text="수동 검증 완료 여부"
    )
    is_synced_to_graph = models.BooleanField(
        default=False,
        db_index=True,
        help_text="StockRelationship/Neo4j 동기화 여부"
    )

    # 시간 관리
    extracted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="TTL 만료 시점 (기본 30일)"
    )

    class Meta:
        db_table = 'serverless_llm_extracted_relation'
        unique_together = [
            ['source_symbol', 'target_symbol', 'relation_type', 'source_id']
        ]
        ordering = ['-extracted_at']
        indexes = [
            models.Index(fields=['source_symbol', 'relation_type']),
            models.Index(fields=['target_symbol', 'relation_type']),
            models.Index(fields=['extracted_at']),
            models.Index(fields=['is_synced_to_graph', '-extracted_at']),
            models.Index(fields=['confidence', '-llm_confidence_score']),
        ]

    def __str__(self):
        return f"{self.source_symbol} --{self.relation_type}--> {self.target_symbol}"

    def save(self, *args, **kwargs):
        """expires_at 자동 설정 (30일 TTL)"""
        if not self.expires_at:
            from datetime import timedelta
            from django.utils import timezone
            self.expires_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        """만료 여부 확인"""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def days_until_expiry(self) -> int:
        """만료까지 남은 일수"""
        from django.utils import timezone
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)


# ========================================
# Chain Sight Phase 7: Institutional Holdings
# ========================================

class InstitutionalHolding(models.Model):
    """
    SEC 13F 기관 보유 현황

    대형 기관투자자($100M+ AUM)의 분기별 주식 보유 현황을 저장합니다.
    SEC 13F 공시에서 자동 수집됩니다.
    """
    POSITION_CHANGE_CHOICES = [
        ('new', '신규 매수'),
        ('increased', '증가'),
        ('decreased', '감소'),
        ('sold_all', '전량 매도'),
        ('unchanged', '변동 없음'),
    ]

    institution_cik = models.CharField(max_length=20, db_index=True, help_text="기관 CIK (SEC 식별번호)")
    institution_name = models.CharField(max_length=300, help_text="기관명")
    filing_date = models.DateField(db_index=True, help_text="공시일")
    report_date = models.DateField(help_text="보고 기준일")
    accession_number = models.CharField(max_length=30, help_text="SEC 접수번호")
    stock_symbol = models.CharField(max_length=10, db_index=True, help_text="종목 심볼")
    shares = models.BigIntegerField(help_text="보유 주식 수")
    value_thousands = models.BigIntegerField(help_text="보유 가치 (천 달러)")
    shares_change = models.BigIntegerField(null=True, blank=True, help_text="전 분기 대비 주식 수 변동")
    position_change = models.CharField(
        max_length=20,
        choices=POSITION_CHANGE_CHOICES,
        null=True,
        blank=True,
        help_text="포지션 변화"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'serverless_institutional_holding'
        unique_together = [['institution_cik', 'stock_symbol', 'report_date']]
        ordering = ['-report_date', 'institution_name']
        indexes = [
            models.Index(fields=['institution_cik', '-report_date']),
            models.Index(fields=['stock_symbol', '-report_date']),
            models.Index(fields=['report_date', 'institution_cik']),
        ]

    def __str__(self):
        return f"{self.institution_name}: {self.stock_symbol} ({self.shares:,} shares)"


# ========================================
# Admin Dashboard Actions (감사 추적)
# ========================================

class AdminActionLog(models.Model):
    """관리자 액션 실행 이력 (감사 추적)"""
    action = models.CharField(max_length=50, db_index=True)
    label = models.CharField(max_length=100)
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    params = models.JSONField(default=dict, blank=True)
    task_id = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=20, default='dispatched')  # dispatched, success, failure
    result_summary = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'serverless_admin_action_log'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['-created_at', 'action'])]

    def __str__(self):
        return f"[{self.status}] {self.action} by {self.user} @ {self.created_at}"
