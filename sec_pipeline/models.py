"""
SEC EDGAR 파이프라인 모델 — 8개 모델 (Phase 1~3)

Track A: Supply Chain 관계 추출
Track B: Business Model 분류
"""

from django.db import models


# ──────────────────────────────────────────────
# 1. RawDocumentStore — SEC filing 원문 저장
# ──────────────────────────────────────────────

class RawDocumentStore(models.Model):
    """SEC 10-K filing 원문 + 추출된 섹션 저장."""

    STATUS_CHOICES = [
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ]

    symbol = models.ForeignKey(
        'stocks.Stock', on_delete=models.CASCADE,
        related_name='sec_filings', db_column='symbol_id',
    )
    accession_no = models.CharField(max_length=30, unique=True)
    filing_date = models.DateField()
    fiscal_year = models.IntegerField()
    final_link = models.URLField(max_length=500)

    # 섹션 텍스트 (추출 결과)
    item_1_text = models.TextField(blank=True, default='')
    item_1a_text = models.TextField(blank=True, default='')
    item_7_text = models.TextField(blank=True, default='')

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='success')
    extraction_method = models.CharField(
        max_length=20, default='regex',
        help_text='regex / edgartools_fallback',
    )
    warnings = models.JSONField(default=list, blank=True)
    collected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sec_raw_document_store'
        ordering = ['-filing_date']
        indexes = [
            models.Index(fields=['symbol', '-filing_date']),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.fiscal_year} ({self.accession_no})"


# ──────────────────────────────────────────────
# 2. SupplyChainEvidence — Track A 추출 결과
# ──────────────────────────────────────────────

class SupplyChainEvidence(models.Model):
    """10-K에서 추출된 supply chain 관계 (Track A)."""

    RELATIONSHIP_CHOICES = [
        ('SUPPLIES_TO', 'Supplies To'),
        ('CUSTOMER_OF', 'Customer Of'),
        ('PARTNER_WITH', 'Partner With'),
        ('DEPENDS_ON', 'Depends On'),
        ('COMPETES_WITH', 'Competes With'),
    ]
    CONFIDENCE_GRADE_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    source_document = models.ForeignKey(
        RawDocumentStore, on_delete=models.CASCADE,
        related_name='supply_chain_evidences',
    )
    source_company = models.ForeignKey(
        'stocks.Stock', on_delete=models.CASCADE,
        related_name='sec_supply_chain_as_source', db_column='source_symbol_id',
    )
    target_company = models.ForeignKey(
        'stocks.Stock', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sec_supply_chain_as_target', db_column='target_symbol_id',
    )
    target_company_name = models.CharField(max_length=200)
    relationship_type = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    evidence_text = models.TextField()

    # confidence: 내부 전용 숫자 (API 노출 금지 — 원칙 6)
    system_confidence = models.FloatField(default=0.0)
    # grade: 사용자 facing
    confidence_grade = models.CharField(max_length=10, choices=CONFIDENCE_GRADE_CHOICES, default='low')

    # Neo4j 동기화 (synced_to_neo4j 필드 금지 — neo4j_dirty만 사용)
    neo4j_dirty = models.BooleanField(default=True)
    neo4j_synced_at = models.DateTimeField(null=True, blank=True)

    prompt_version = models.CharField(max_length=10, default='v1')
    extracted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sec_supply_chain_evidence'
        indexes = [
            models.Index(fields=['source_company', 'relationship_type']),
            models.Index(fields=['target_company']),
            models.Index(fields=['neo4j_dirty']),
        ]

    def __str__(self):
        return f"{self.source_company_id} → {self.target_company_name} ({self.relationship_type})"


# ──────────────────────────────────────────────
# 3. BusinessModelSnapshot — Track B 분류 결과
# ──────────────────────────────────────────────

class BusinessModelSnapshot(models.Model):
    """10-K에서 추출된 비즈니스 모델 5개 필드 (Track B)."""

    FIELD_CHOICES = [
        ('direct', 'Direct'),
        ('indirect', 'Indirect'),
        ('hybrid', 'Hybrid'),
        ('unknown', 'Unknown'),
    ]
    CONTRACT_CHOICES = [
        ('subscription', 'Subscription'),
        ('one_time', 'One-time'),
        ('hybrid', 'Hybrid'),
        ('unknown', 'Unknown'),
    ]
    RECURRING_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('unknown', 'Unknown'),
    ]
    CHANNEL_CHOICES = [
        ('high_dependency', 'High Dependency'),
        ('moderate', 'Moderate'),
        ('low_dependency', 'Low Dependency'),
        ('unknown', 'Unknown'),
    ]
    CONCENTRATION_CHOICES = [
        ('concentrated', 'Concentrated'),
        ('diversified', 'Diversified'),
        ('unknown', 'Unknown'),
    ]
    CONFIDENCE_GRADE_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    symbol = models.ForeignKey(
        'stocks.Stock', on_delete=models.CASCADE,
        related_name='business_model_snapshots', db_column='symbol_id',
    )
    source_document = models.ForeignKey(
        RawDocumentStore, on_delete=models.CASCADE,
        related_name='business_model_snapshots',
    )
    as_of_date = models.DateField(help_text='filing_date 기준')

    # 5개 분류 필드
    direct_customer_contact = models.CharField(max_length=20, choices=FIELD_CHOICES, default='unknown')
    contract_model = models.CharField(max_length=20, choices=CONTRACT_CHOICES, default='unknown')
    recurring_revenue_signal = models.CharField(max_length=20, choices=RECURRING_CHOICES, default='unknown')
    channel_dependency = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='unknown')
    customer_concentration = models.CharField(max_length=20, choices=CONCENTRATION_CHOICES, default='unknown')

    # confidence: 내부 전용 (원칙 6)
    overall_confidence = models.FloatField(default=0.0)
    confidence_grade = models.CharField(max_length=10, choices=CONFIDENCE_GRADE_CHOICES, default='low')

    prompt_version = models.CharField(max_length=10, default='v1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sec_business_model_snapshot'
        # get_latest_by는 as_of_date (created_at 아님)
        get_latest_by = 'as_of_date'
        ordering = ['-as_of_date']
        indexes = [
            models.Index(fields=['symbol', '-as_of_date']),
        ]

    def __str__(self):
        return f"{self.symbol_id} BM ({self.as_of_date})"


# ──────────────────────────────────────────────
# 4. BusinessModelEvidence — Track B 근거 문장
# ──────────────────────────────────────────────

class BusinessModelEvidence(models.Model):
    """BusinessModelSnapshot 각 필드의 근거 문장."""

    FIELD_NAME_CHOICES = [
        ('direct_customer_contact', 'Direct Customer Contact'),
        ('contract_model', 'Contract Model'),
        ('recurring_revenue_signal', 'Recurring Revenue Signal'),
        ('channel_dependency', 'Channel Dependency'),
        ('customer_concentration', 'Customer Concentration'),
    ]

    snapshot = models.ForeignKey(
        BusinessModelSnapshot, on_delete=models.CASCADE,
        related_name='evidences',
    )
    field_name = models.CharField(max_length=30, choices=FIELD_NAME_CHOICES)
    evidence_text = models.TextField()
    confidence = models.FloatField(default=0.0)

    class Meta:
        db_table = 'sec_business_model_evidence'

    def __str__(self):
        return f"{self.snapshot} — {self.field_name}"


# ──────────────────────────────────────────────
# 5. FilingProcessLog — 파이프라인 실행 로그
# ──────────────────────────────────────────────

class FilingProcessLog(models.Model):
    """SEC 파이프라인 각 단계 실행 로그."""

    STAGE_CHOICES = [
        ('fmp_metadata', 'FMP Metadata'),
        ('sec_fetch', 'SEC Fetch'),
        ('section_extract', 'Section Extract'),
        ('track_a_extract', 'Track A Extract'),
        ('track_b_extract', 'Track B Extract'),
        ('ticker_match', 'Ticker Match'),
        ('neo4j_sync', 'Neo4j Sync'),
    ]
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
        ('skipped', 'Skipped'),
    ]

    symbol = models.CharField(max_length=20)
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    detail = models.TextField(blank=True, default='')
    duration_seconds = models.FloatField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sec_filing_process_log'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['symbol', 'stage', '-started_at']),
        ]

    def __str__(self):
        return f"{self.symbol} {self.stage} → {self.status}"


# ──────────────────────────────────────────────
# 6. CompanyAlias — Ticker 별칭 테이블
# ──────────────────────────────────────────────

class CompanyAlias(models.Model):
    """LLM 추출 회사명 → Ticker 매핑 별칭."""

    SOURCE_CHOICES = [
        ('admin_resolved', 'Admin Resolved'),
        ('auto_90pct', 'Auto 90%+'),
        ('manual_seed', 'Manual Seed'),
    ]

    alias = models.CharField(max_length=200)
    ticker = models.CharField(max_length=20)
    context_sector = models.CharField(max_length=100, blank=True, default='')
    context_country = models.CharField(
        max_length=50, blank=True, default='',
        help_text='참고용 메타데이터 (unique key에 포함하지 않음)',
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual_seed')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sec_company_alias'
        # context_country는 unique key에 포함하지 않음
        unique_together = [('alias', 'context_sector')]
        verbose_name_plural = 'Company aliases'

    def __str__(self):
        sector_label = f" [{self.context_sector}]" if self.context_sector else ""
        return f"{self.alias} → {self.ticker}{sector_label}"


# ──────────────────────────────────────────────
# 7. UnmatchedCompanyQueue — Ticker 미매칭 큐
# ──────────────────────────────────────────────

class UnmatchedCompanyQueue(models.Model):
    """LLM이 추출했지만 Ticker 매칭 실패한 회사명 큐."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('matched', 'Matched'),
        ('not_public', 'Not Public'),
        ('person', 'Person'),
        ('duplicate', 'Duplicate'),
        ('skipped', 'Skipped'),
    ]

    raw_company_name = models.CharField(max_length=200)
    source_symbol = models.CharField(max_length=20)
    occurrence_count = models.IntegerField(default=1)
    source_sectors = models.JSONField(
        default=list, blank=True,
        help_text='이 이름이 나온 sector 목록 (2개+면 동명이의 경고)',
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    fuzzy_candidates = models.JSONField(
        default=list, blank=True,
        help_text='[{"ticker":"TSM","name":"...","score":0.82}, ...]',
    )
    resolved_ticker = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sec_unmatched_company_queue'
        ordering = ['-occurrence_count']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['raw_company_name']),
        ]

    def __str__(self):
        return f"{self.raw_company_name} ({self.status}, x{self.occurrence_count})"


# ──────────────────────────────────────────────
# 8. PipelineIntelligenceReport — LLM 품질 리포트 (Phase 3)
# ──────────────────────────────────────────────

class PipelineIntelligenceReport(models.Model):
    """LLM이 생성한 파이프라인 품질 분석 리포트."""

    SEVERITY_CHOICES = [
        ('healthy', 'Healthy'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    report_date = models.DateField()
    hours_back = models.IntegerField(default=24)

    # 5차원 점수 (내부 운영용 — Admin에서만 노출)
    collection_score = models.FloatField(default=0.0)
    extraction_score = models.FloatField(default=0.0)
    matching_score = models.FloatField(default=0.0)
    sync_score = models.FloatField(default=0.0)
    quality_score = models.FloatField(default=0.0)
    health_score = models.FloatField(default=0.0, help_text='5차원 가중 평균')

    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='healthy')

    # LLM 분석 결과
    summary = models.TextField(blank=True, default='')
    cross_insights = models.TextField(blank=True, default='')
    recommended_actions = models.JSONField(default=list, blank=True)
    trend_vs_previous = models.JSONField(default=dict, blank=True)

    prompt_version = models.CharField(max_length=10, default='v1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sec_pipeline_intelligence_report'
        ordering = ['-report_date']
        get_latest_by = 'report_date'

    def __str__(self):
        return f"Report {self.report_date} ({self.severity})"
