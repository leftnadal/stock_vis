import uuid

from django.conf import settings
from django.db import models


class HypothesisEvent(models.Model):
    """사용자의 모든 가설 관련 행동을 기록하는 단일 이벤트 스트림."""

    EVENT_TYPE_CHOICES = [
        ('thesis_created', '가설 생성'),
        ('thesis_closed', '가설 마감'),
        ('premise_added', '전제 추가'),
        ('premise_modified', '전제 수정'),
        ('premise_removed', '전제 제거'),
        ('indicator_added', '지표 추가'),
        ('indicator_removed', '지표 제거'),
        ('ai_suggestion_shown', 'AI 제안 표시'),
        ('ai_suggestion_accepted', 'AI 제안 수락'),
        ('ai_suggestion_rejected', 'AI 제안 거절'),
        ('outcome_correct', '적중 판정'),
        ('outcome_incorrect', '미적중 판정'),
        ('outcome_neutral', '중립 판정'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hypothesis_events',
    )
    thesis = models.ForeignKey(
        'thesis.Thesis',
        on_delete=models.CASCADE,
        null=True,
        related_name='events',
    )

    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    event_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['thesis', 'event_type']),
            models.Index(fields=['event_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user} - {self.get_event_type_display()} @ {self.created_at}"


class ValidityRecord(models.Model):
    """가설 마감 시 각 지표의 유효성을 기록."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    thesis_type = models.CharField(max_length=30)
    indicator_data_key = models.CharField(max_length=50)
    market_regime = models.CharField(max_length=20)

    # 유효성 판정 (2x2 매트릭스)
    indicator_aligned = models.BooleanField()
    thesis_correct = models.BooleanField()

    # 매트릭스 기반 점수
    score = models.FloatField()

    # 메타
    thesis = models.ForeignKey(
        'thesis.Thesis',
        on_delete=models.CASCADE,
        related_name='validity_records',
    )
    indicator = models.ForeignKey(
        'thesis.ThesisIndicator',
        on_delete=models.CASCADE,
        related_name='validity_records',
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['thesis_type', 'indicator_data_key', 'market_regime']),
        ]

    def __str__(self):
        return (
            f"{self.thesis_type}/{self.indicator_data_key} "
            f"aligned={self.indicator_aligned} correct={self.thesis_correct} "
            f"score={self.score}"
        )


class InvestorDNA(models.Model):
    """사용자의 투자 사고방식 프로파일. 이벤트 로그에서 자동 구축."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='investor_dna',
    )

    # Phase 1: 기본 통계 (이벤트 집계)
    total_theses = models.IntegerField(default=0)
    closed_theses = models.IntegerField(default=0)
    correct_count = models.IntegerField(default=0)
    incorrect_count = models.IntegerField(default=0)

    # 전제 카테고리 분포
    premise_category_counts = models.JSONField(default=dict)

    # 지표 유형 선호도
    indicator_type_counts = models.JSONField(default=dict)

    # AI 제안 수락률
    ai_suggestions_shown = models.IntegerField(default=0)
    ai_suggestions_accepted = models.IntegerField(default=0)

    # Phase 2 미리 생성 필드
    personalization_weight = models.FloatField(default=0.5)

    updated_at = models.DateTimeField(auto_now=True)

    @property
    def accuracy_rate(self):
        total = self.correct_count + self.incorrect_count
        return self.correct_count / total if total > 0 else None

    @property
    def ai_accept_rate(self):
        return (
            self.ai_suggestions_accepted / self.ai_suggestions_shown
            if self.ai_suggestions_shown > 0
            else None
        )

    @property
    def top_down_ratio(self):
        """하향식 사고 비율. macro+sector 비중."""
        total = sum(self.premise_category_counts.values()) or 1
        top_down = (
            self.premise_category_counts.get('macro', 0)
            + self.premise_category_counts.get('sector', 0)
        )
        return top_down / total

    def __str__(self):
        return f"DNA: {self.user} (theses={self.total_theses})"
