"""
코어-위성 EventGroup (M2 v1.1 Phase 1 — jaccard co-mention 기반).

theme_tags(섹터형)를 대체하는 쉐도우 그룹 모델. Phase 1은 병행 적재만 —
기존 theme_tags 소비자(leadership/attention/보드/Neo4j)는 reader 전환 세션까지 그대로.

BOUNDARY-2: FK는 chain_sight → stocks.Stock 방향(합법). shared는 이 모델을 import하지 않음.
"""

from django.contrib.postgres.fields import ArrayField  # noqa: F401  (향후 확장 여지)
from django.db import models


class EventGroup(models.Model):
    """코어-위성 2층 이벤트 그룹. 코어=jaccard 연결요소, 위성=1-hop 확장."""

    SOURCE_CHOICES = [
        ("news_jaccard", "News Co-mention (Jaccard)"),
        ("llm", "LLM"),
        ("manual", "Manual"),
    ]

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default="news_jaccard"
    )
    confidence = models.FloatField(default=0.0, help_text="코어 멤버 평균 강도")
    window_days = models.IntegerField(default=21, help_text="co-mention half-life 윈도우(일)")
    cohesion = models.FloatField(
        null=True, blank=True, help_text="코어 멤버 수익률 pairwise 상관 평균(게이팅 기준)"
    )
    breadth = models.FloatField(null=True, blank=True, help_text="일별 방향 일치도")
    name_candidates = models.JSONField(
        default=dict, blank=True,
        help_text='코어 TF-IDF 이름 후보 {"n2":..,"n3":..,"terms":[..]} (N 미확정 — Phase 1)'
    )
    member_count = models.IntegerField(default=0)
    core_count = models.IntegerField(default=0)
    is_hidden = models.BooleanField(
        default=False, db_index=True,
        help_text="킬스위치/노이즈 게이팅(코어 cohesion<0.2 또는 산출불가 = 저신뢰 잡탕 후보)"
    )
    as_of_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chainsight_event_group"
        indexes = [models.Index(fields=["source", "is_hidden"])]

    def __str__(self):
        return f"{self.name} ({self.core_count}c/{self.member_count}m)"


class GroupMembership(models.Model):
    """EventGroup ↔ Stock 정규화. role=core|satellite + 다중신호 confidence + 근거."""

    ROLE_CHOICES = [("core", "Core"), ("satellite", "Satellite")]

    group = models.ForeignKey(
        EventGroup, on_delete=models.CASCADE, related_name="memberships"
    )
    symbol = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        to_field="symbol",
        db_column="symbol",
        related_name="event_group_memberships",
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="core")
    edge_confidence = models.FloatField(
        default=0.0, help_text="다중신호 confidence(jaccard 1-hop + 13F 가산 + 코어 연결수)"
    )
    anchor_symbol = models.CharField(
        max_length=10, blank=True, help_text="위성이 닿은 코어 멤버(코어는 공백)"
    )
    cohold_institutions = models.IntegerField(
        default=0, help_text="13F 공유 기관 수(✓N, 가산 신호)"
    )
    evidence = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chainsight_group_membership"
        unique_together = ["group", "symbol"]
        indexes = [models.Index(fields=["symbol", "role"])]

    def __str__(self):
        return f"{self.group_id}:{self.symbol_id}[{self.role}]"
