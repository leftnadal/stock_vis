"""
관계 발견 모델 (로드맵 CS-2)

CoMentionEdge: 뉴스 동시출현 쌍 (DC-5에서 축적)
PriceCoMovement: 주가 동조 분석 (CS-2-3에서 계산)
RelationConfidence v2.1: 관계 신뢰도 종합 (CS-2-4에서 판정)
"""

from django.db import models


class SelfLoopError(ValueError):
    """자기루프(symbol_a == symbol_b) 관계 생성 시도 — a≠b 앱 가드 위반.

    ⑳-3 REVIEW-P2 Part Q: 자기 자신에 대한 관계는 무의미하다. DB CheckConstraint
    승격은 마이그레이션을 동반하므로 보류(TASKQUEUE), 그 전까지 앱 레벨 가드로 신규 생성을 차단한다.
    """


class CoMentionEdge(models.Model):
    """뉴스 동시출현 쌍."""

    symbol_a = models.CharField(max_length=10, db_index=True)
    symbol_b = models.CharField(max_length=10, db_index=True)
    co_mention_count = models.IntegerField(default=0)
    last_co_mention_date = models.DateField(null=True, blank=True)
    first_co_mention_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chainsight_co_mention_edge"
        unique_together = ["symbol_a", "symbol_b"]
        indexes = [
            models.Index(fields=["symbol_a"]),
            models.Index(fields=["symbol_b"]),
            models.Index(fields=["-co_mention_count"]),
        ]

    def __str__(self):
        return f"{self.symbol_a} ↔ {self.symbol_b}: {self.co_mention_count}회"


class PriceCoMovement(models.Model):
    """주가 동조 분석. 90일 rolling correlation."""

    PERIOD_CHOICES = [
        ("30d", "30일"),
        ("90d", "90일"),
        ("180d", "180일"),
    ]

    symbol_a = models.CharField(max_length=10, db_index=True)
    symbol_b = models.CharField(max_length=10, db_index=True)
    correlation = models.DecimalField(max_digits=5, decimal_places=4)
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default="90d")
    calculated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chainsight_price_co_movement"
        unique_together = ["symbol_a", "symbol_b", "period"]
        indexes = [
            models.Index(fields=["symbol_a"]),
            models.Index(fields=["-correlation"]),
        ]

    def __str__(self):
        return f"{self.symbol_a} ↔ {self.symbol_b}: {self.correlation} ({self.period})"


class RelationConfidence(models.Model):
    """관계 신뢰도 종합 v2.1. confirmed 관계만 Neo4j 엣지로 동기화 (CS-3-2)."""

    RELATION_TYPE_CHOICES = [
        ("PEER_OF", "Peer"),
        ("SUPPLIES_TO", "Supplies To"),
        ("CO_MENTIONED", "Co-mentioned"),
        ("PRICE_CORRELATED", "Price Correlated"),
        ("HAS_THEME", "Has Theme"),
        ("COMPETES_WITH", "Competes With"),
        ("HELD_BY_SAME_FUND", "Held by Same Fund"),
        # additive 정합(⑰): DB에 이미 존재하는 값(PARTNER_WITH 54행·DEPENDS_ON 41행)에
        # 라벨 부여 — choices는 검증/표시용이라 컬럼 DDL 무변경(sqlmigrate no-op).
        ("PARTNER_WITH", "Partner With"),
        ("DEPENDS_ON", "Depends On"),
        # CS-P2-8K: 8-K item 2.01(인수/합병/스핀오프) 관계. choices는 검증/표시용 →
        # 컬럼 DDL 무변경(sqlmigrate no-op, additive). 병진 승인 08-13.
        ("ACQUIRED", "Acquired"),
    ]
    RELATION_CATEGORY_CHOICES = [
        ("truth", "Truth"),
        ("market", "Market"),
    ]
    DIRECTION_CHOICES = [
        ("a→b", "A to B"),
        ("b→a", "B to A"),
        ("both", "Undirected"),
    ]
    RELATION_STATUS_CHOICES = [
        ("hidden", "Hidden"),
        ("weak", "Weak"),
        ("probable", "Probable"),
        ("confirmed", "Confirmed"),
        ("stale", "Stale"),
    ]

    # 식별
    symbol_a = models.CharField(max_length=10, db_index=True)
    symbol_b = models.CharField(max_length=10, db_index=True)
    relation_type = models.CharField(max_length=30, choices=RELATION_TYPE_CHOICES)
    relation_category = models.CharField(
        max_length=10, choices=RELATION_CATEGORY_CHOICES, default="truth"
    )
    canonical_direction = models.CharField(
        max_length=5, choices=DIRECTION_CHOICES, default="both"
    )

    # 상태 (5단계)
    relation_status = models.CharField(
        max_length=12, choices=RELATION_STATUS_CHOICES, default="hidden"
    )

    # 점수 (3단)
    truth_score = models.FloatField(default=0)
    market_score = models.FloatField(null=True, blank=True)
    # deprecated: per-row 무의미(한 행은 truth/market 중 하나만 가짐). 쌍 단위
    # relevance는 RelationPairSnapshot(relevance_opp/relevance_risk) 사용. 제거 마이그레이션 보류.
    investment_relevance = models.FloatField(null=True, blank=True)

    # 증거
    evidence_tier_best = models.IntegerField(default=3)
    evidence_count_total = models.IntegerField(default=0)
    evidence_count_independent = models.IntegerField(default=0)
    evidence_sources = models.JSONField(default=dict, blank=True)

    # 빠른 필터용 bool 7개
    has_peer_source = models.BooleanField(default=False)
    has_industry_source = models.BooleanField(default=False)
    has_supply_chain_source = models.BooleanField(default=False)
    has_news_source = models.BooleanField(default=False)
    has_price_source = models.BooleanField(default=False)
    has_etf_source = models.BooleanField(default=False)
    has_llm_source = models.BooleanField(default=False)

    # 설명
    relation_basis_summary = models.TextField(blank=True, default="")

    # 시간
    first_observed_at = models.DateTimeField(auto_now_add=True)
    last_observed_at = models.DateTimeField(auto_now=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    stale_threshold_days = models.IntegerField(default=90)

    # 상태 전이 추적 (시드 선정용)
    previous_status = models.CharField(
        max_length=12,
        choices=RELATION_STATUS_CHOICES,
        blank=True,
        default="",
        help_text="직전 상태. 시드 선정 시 relation_upgrade/downgrade 판단용.",
    )

    # 상향 학습 루프 (upward learning — 설계 relation_confidence_upward_loop.md, D1 additive)
    evidence_streak = models.IntegerField(
        default=0, help_text="연속 재확인 틱 수. 하향/무증거 시 0 리셋. B의 streak≥N 판정."
    )
    last_upgraded_at = models.DateTimeField(null=True, blank=True, help_text="상향 전이 witness.")
    last_downgraded_at = models.DateTimeField(null=True, blank=True, help_text="하향 전이 witness.")
    last_computed_at = models.DateTimeField(
        null=True, blank=True, help_text="궤적 점 계산 시각(기존 드리프트 해소, upsert 감사용)."
    )
    fastpath_triggered_at = models.DateTimeField(
        null=True, blank=True, help_text="C fast-path 발동 감사(오상향 추적)."
    )

    # 동기화 (audit P0 #9 — neo4j_dirty 단일 소스. synced_to_neo4j 제거 2026-04-29)
    neo4j_dirty = models.BooleanField(
        default=True,
        db_index=True,
        help_text="True이면 Neo4j 동기화 필요. save() 시 자동 True.",
    )
    neo4j_synced_at = models.DateTimeField(null=True, blank=True)
    score_version = models.CharField(max_length=10, default="2.1")

    # CS-P1A Slice2 (additive): 계층 분류 — 근거/유사/제외/보류.
    # DECISIONS D-CS-REDESIGN-BEFORE-BASELINE 매핑표 기준. 순수 데이터 필드(읽는 API·화면 없음).
    SERVING_LAYER_CHOICES = [
        ("evidence", "Evidence"),   # SEC 4종·CO_MENTIONED — 근거 계층(출처 문장·문서 지목)
        ("context", "Context"),     # PEER_OF·PRICE_CORRELATED — 유사 계층("관계 아님")
        ("excluded", "Excluded"),   # 서빙 제외
        ("pending", "Pending"),     # 미분류(default)
    ]
    serving_layer = models.CharField(
        max_length=10,
        choices=SERVING_LAYER_CHOICES,
        default="pending",
        db_index=True,
        help_text="계층 분류(CS-P1A Slice2). 매핑표: SEC4종·CO_MENTIONED=evidence / "
        "PEER_OF·PRICE_CORRELATED=context / PEER(2건)=pending.",
    )

    # ⑳-3 S2-B: 관계 도메인 태깅(자동-C 파이프라인). 전부 additive nullable.
    # 승인본(relation_domain)은 검수 승인만이 쓴다(Phase 2). 초안·검증만 파이프라인이 기록.
    DOMAIN_REVIEW_CHOICES = [
        ("pending", "Pending"),      # 검수 대기(게이트 미통과 or 타입 변경 제안)
        ("approved", "Approved"),    # 사람 검수 승인
        ("auto", "Auto"),            # 임계 자동승인(DOMAIN_AUTO_APPROVE=True일 때만)
        ("rejected", "Rejected"),    # 검수 반려
    ]
    relation_domain = models.CharField(
        max_length=80, null=True, blank=True,
        help_text="승인된 도메인 태그(제품/시장). 검수 승인만 기록(Phase 2).",
    )
    relation_domain_draft = models.CharField(
        max_length=80, null=True, blank=True,
        help_text="LLM 초안 도메인 태그. 파이프라인이 기록, 승인 전.",
    )
    domain_review_status = models.CharField(
        max_length=10, choices=DOMAIN_REVIEW_CHOICES, null=True, blank=True,
        help_text="도메인 초안 검수 상태. 게이트 판정 결과.",
    )
    domain_machine_check = models.JSONField(
        null=True, blank=True,
        help_text="기계검증 결과(항목별 pass/fail + type_match + LLM confidence).",
    )

    # CS-P1B (additive): 연결 강도 = 초과수익 동조성. evidence 계층 쌍에만 계산·기록.
    # 순수 데이터 필드(읽는 API·화면 없음). 기존 PriceCoMovement(원수익·Neo4j)와 독립.
    sync_strength = models.FloatField(
        null=True, blank=True, db_index=True,
        help_text="초과수익(일간수익−SPY수익) Pearson 상관. evidence 계층 강도(CS-P1B). null=미계산/관측부족.",
    )
    sync_window_days = models.IntegerField(
        null=True, blank=True,
        help_text="sync_strength 계산 윈도우(거래일). 관행 90.",
    )
    sync_computed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="sync_strength 계산 시각(감사용).",
    )

    class Meta:
        db_table = "chainsight_relation_confidence"
        unique_together = ["symbol_a", "symbol_b", "relation_type"]
        indexes = [
            models.Index(fields=["relation_status"]),
            models.Index(fields=["relation_type"]),
            models.Index(fields=["neo4j_dirty"]),
        ]

    def save(self, *args, **kwargs):
        # ⑳-3 REVIEW-P2 Part Q: a≠b 앱 레벨 가드. 신규 생성만 차단(기존 self-loop
        # 레코드 갱신·soft-drop은 통과 — 소급 삭제 아님). DB constraint 승격은 TASKQUEUE.
        if self._state.adding and self.symbol_a == self.symbol_b:
            raise SelfLoopError(
                f"자기루프 관계 생성 차단: {self.symbol_a}=={self.symbol_b} "
                f"[{self.relation_type}]. symbol_a≠symbol_b 필수."
            )
        # 상태 전이 추적: DB에서 기존 상태 읽어서 previous_status에 보존
        if self.pk:
            try:
                old = (
                    RelationConfidence.objects.filter(pk=self.pk)
                    .values_list("relation_status", flat=True)
                    .first()
                )
                if old and old != self.relation_status:
                    self.previous_status = old
            except Exception:
                pass
        # neo4j_dirty 자동 세팅 (bulk_update에서는 save() 미호출되므로 수동 관리 필요)
        self.neo4j_dirty = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.symbol_a} → {self.symbol_b} [{self.relation_type}]: {self.relation_status}"
