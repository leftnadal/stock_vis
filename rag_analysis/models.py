from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from .constants import MAX_BASKET_UNITS, DEFAULT_DATA_UNITS

User = get_user_model()


class DataBasket(models.Model):
    """사용자의 분석 데이터 바구니"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="baskets"
    )
    name = models.CharField(max_length=100, default="My Basket")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 바구니 제한
    MAX_ITEMS = 15
    MAX_UNITS = MAX_BASKET_UNITS

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Data Basket"
        verbose_name_plural = "Data Baskets"

    def __str__(self):
        return f"{self.user.username}s {self.name}"

    def can_add_item(self) -> bool:
        """아이템 추가 가능 여부"""
        return self.items.count() < self.MAX_ITEMS

    @property
    def items_count(self) -> int:
        return self.items.count()

    @property
    def current_units(self) -> int:
        """현재 사용 중인 용량"""
        result = self.items.aggregate(total=models.Sum('data_units'))['total']
        return result or 0

    @property
    def remaining_units(self) -> int:
        """남은 용량"""
        return self.MAX_UNITS - self.current_units

    def can_add_units(self, units: int) -> bool:
        """해당 용량 추가 가능 여부"""
        return self.remaining_units >= units


class BasketItem(models.Model):
    """바구니에 담긴 개별 아이템"""

    class ItemType(models.TextChoices):
        # 기본 타입
        STOCK = "stock", "종목"
        NEWS = "news", "뉴스"
        FINANCIAL = "financial", "재무제표"
        MACRO = "macro", "거시경제"
        # 세분화된 타입 (용량 시스템용)
        OVERVIEW = "overview", "기본 정보"
        PRICE = "price", "주가 데이터"
        FINANCIAL_SUMMARY = "financial_summary", "재무제표 (요약)"
        FINANCIAL_FULL = "financial_full", "재무제표 (전체)"
        INDICATOR = "indicator", "기술적 지표"

    basket = models.ForeignKey(
        DataBasket,
        on_delete=models.CASCADE,
        related_name="items"
    )
    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices
    )

    # 참조 ID (종목코드, 뉴스ID 등)
    reference_id = models.CharField(max_length=100)

    # 표시용 메타데이터
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)

    # 데이터 용량
    data_units = models.PositiveIntegerField(
        default=DEFAULT_DATA_UNITS,
        help_text="데이터 용량 (units)"
    )

    # 데이터 스냅샷 (JSON)
    # 담을 당시의 데이터를 저장 (날짜 기준 명시를 위해)
    data_snapshot = models.JSONField(default=dict, blank=True)
    snapshot_date = models.DateField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Basket Item"
        verbose_name_plural = "Basket Items"
        # 같은 바구니에 같은 아이템 중복 방지
        unique_together = ["basket", "item_type", "reference_id"]

    def __str__(self):
        return f"{self.get_item_type_display()}: {self.title}"

    def clean(self):
        """바구니 아이템 개수 제한 검증"""
        if self.basket_id and not self.pk:  # 새 아이템인 경우
            if not self.basket.can_add_item():
                raise ValidationError(
                    f"바구니에는 최대 {DataBasket.MAX_ITEMS}개의 "
                    f"아이템만 담을 수 있습니다."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class AnalysisSession(models.Model):
    """분석 세션 (대화 컨텍스트 유지)"""

    class Status(models.TextChoices):
        ACTIVE = "active", "활성"
        COMPLETED = "completed", "완료"
        ERROR = "error", "오류"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="analysis_sessions"
    )
    basket = models.ForeignKey(
        DataBasket,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sessions"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    # 세션 메타데이터
    title = models.CharField(max_length=200, blank=True)

    # 탐험 경로 기록
    exploration_path = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Analysis Session"
        verbose_name_plural = "Analysis Sessions"

    def __str__(self):
        return f"Session {self.id} - {self.user.username}"

    def add_exploration(self, entity_type: str, entity_id: str, reason: str):
        """탐험 경로 추가"""
        self.exploration_path.append({
            "type": entity_type,
            "id": entity_id,
            "reason": reason,
            "timestamp": timezone.now().isoformat()
        })
        self.save(update_fields=["exploration_path", "updated_at"])


class AnalysisMessage(models.Model):
    """분석 세션 내 메시지"""

    class Role(models.TextChoices):
        USER = "user", "사용자"
        ASSISTANT = "assistant", "어시스턴트"
        SYSTEM = "system", "시스템"

    session = models.ForeignKey(
        AnalysisSession,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices
    )
    content = models.TextField()

    # LLM 제안 (JSON)
    suggestions = models.JSONField(default=list)

    # 토큰 사용량 추적
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Analysis Message"
        verbose_name_plural = "Analysis Messages"

    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}..."


class UsageLog(models.Model):
    """
    LLM 사용량 및 비용 추적 로그

    비용 모니터링, 예산 관리, 사용 패턴 분석에 사용됩니다.
    """

    class ModelType(models.TextChoices):
        # Claude 모델
        CLAUDE_SONNET = "claude-sonnet", "Claude Sonnet"
        CLAUDE_HAIKU = "claude-haiku", "Claude Haiku"
        CLAUDE_OPUS = "claude-opus", "Claude Opus"
        # Gemini 모델
        GEMINI_FLASH = "gemini-flash", "Gemini Flash"
        GEMINI_PRO = "gemini-pro", "Gemini Pro"
        # 기타
        OTHER = "other", "Other"

    class RequestType(models.TextChoices):
        ANALYSIS = "analysis", "분석"
        ENTITY_EXTRACTION = "entity_extraction", "엔티티 추출"
        COMPRESSION = "compression", "압축"
        EMBEDDING = "embedding", "임베딩"
        OTHER = "other", "기타"

    # 관계
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="usage_logs",
        null=True,
        blank=True
    )
    session = models.ForeignKey(
        AnalysisSession,
        on_delete=models.SET_NULL,
        related_name="usage_logs",
        null=True,
        blank=True
    )
    message = models.ForeignKey(
        AnalysisMessage,
        on_delete=models.SET_NULL,
        related_name="usage_logs",
        null=True,
        blank=True
    )

    # 모델 정보
    model = models.CharField(
        max_length=50,
        choices=ModelType.choices,
        default=ModelType.GEMINI_FLASH
    )
    model_version = models.CharField(
        max_length=100,
        blank=True,
        help_text="정확한 모델 버전 (예: gemini-2.5-flash-preview-05-20)"
    )

    # 요청 타입
    request_type = models.CharField(
        max_length=30,
        choices=RequestType.choices,
        default=RequestType.ANALYSIS
    )

    # 토큰 사용량
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    # 비용 (USD)
    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
        help_text="비용 (USD)"
    )

    # 캐시 정보
    cached = models.BooleanField(
        default=False,
        help_text="캐시 히트 여부"
    )
    cache_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="캐시 히트 시 캐시 ID"
    )

    # 성능 정보
    latency_ms = models.PositiveIntegerField(
        default=0,
        help_text="응답 시간 (밀리초)"
    )

    # 메타데이터
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="추가 메타데이터 (엔티티, 압축률 등)"
    )

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Usage Log"
        verbose_name_plural = "Usage Logs"
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['model', 'created_at']),
            models.Index(fields=['request_type', 'created_at']),
            models.Index(fields=['cached', 'created_at']),
        ]

    def __str__(self):
        return f"{self.model} - {self.total_tokens} tokens - ${self.cost_usd}"

    @classmethod
    def get_user_daily_cost(cls, user, date=None) -> float:
        """사용자의 일일 비용 조회"""
        from django.db.models import Sum
        from datetime import date as date_type

        if date is None:
            date = timezone.now().date()

        result = cls.objects.filter(
            user=user,
            created_at__date=date
        ).aggregate(total=Sum('cost_usd'))

        return float(result['total'] or 0)

    @classmethod
    def get_user_monthly_cost(cls, user, year=None, month=None) -> float:
        """사용자의 월간 비용 조회"""
        from django.db.models import Sum

        if year is None or month is None:
            now = timezone.now()
            year = now.year
            month = now.month

        result = cls.objects.filter(
            user=user,
            created_at__year=year,
            created_at__month=month
        ).aggregate(total=Sum('cost_usd'))

        return float(result['total'] or 0)

    @classmethod
    def get_cache_hit_rate(cls, hours: int = 24) -> float:
        """캐시 히트율 계산"""
        from datetime import timedelta

        since = timezone.now() - timedelta(hours=hours)
        total = cls.objects.filter(
            created_at__gte=since,
            request_type=cls.RequestType.ANALYSIS
        ).count()

        if total == 0:
            return 0.0

        cached = cls.objects.filter(
            created_at__gte=since,
            request_type=cls.RequestType.ANALYSIS,
            cached=True
        ).count()

        return cached / total

    @classmethod
    def get_usage_stats(cls, user=None, hours: int = 24) -> dict:
        """사용량 통계 조회"""
        from django.db.models import Sum, Avg, Count
        from datetime import timedelta

        since = timezone.now() - timedelta(hours=hours)
        queryset = cls.objects.filter(created_at__gte=since)

        if user:
            queryset = queryset.filter(user=user)

        stats = queryset.aggregate(
            total_requests=Count('id'),
            total_input_tokens=Sum('input_tokens'),
            total_output_tokens=Sum('output_tokens'),
            total_cost=Sum('cost_usd'),
            avg_latency=Avg('latency_ms'),
            cache_hits=Count('id', filter=models.Q(cached=True))
        )

        total_requests = stats['total_requests'] or 0
        cache_hits = stats['cache_hits'] or 0

        return {
            'period_hours': hours,
            'total_requests': total_requests,
            'total_input_tokens': stats['total_input_tokens'] or 0,
            'total_output_tokens': stats['total_output_tokens'] or 0,
            'total_cost_usd': float(stats['total_cost'] or 0),
            'avg_latency_ms': float(stats['avg_latency'] or 0),
            'cache_hits': cache_hits,
            'cache_hit_rate': cache_hits / total_requests if total_requests > 0 else 0
        }
