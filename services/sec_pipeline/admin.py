"""
SEC-PR-8: Django Admin — 모든 SEC Pipeline 모델 + 미매칭 큐 관리.
"""

from django.contrib import admin

from .models import (
    BusinessModelEvidence,
    BusinessModelSnapshot,
    CompanyAlias,
    FilingProcessLog,
    PipelineIntelligenceReport,
    RawDocumentStore,
    SupplyChainEvidence,
    UnmatchedCompanyQueue,
)

# ── RawDocumentStore ──


@admin.register(RawDocumentStore)
class RawDocumentStoreAdmin(admin.ModelAdmin):
    list_display = [
        "symbol",
        "fiscal_year",
        "filing_date",
        "status",
        "extraction_method",
    ]
    list_filter = ["status", "extraction_method"]
    search_fields = ["symbol__symbol", "accession_no"]
    readonly_fields = ["collected_at"]


# ── SupplyChainEvidence ──


@admin.register(SupplyChainEvidence)
class SupplyChainEvidenceAdmin(admin.ModelAdmin):
    list_display = [
        "source_company",
        "target_company_name",
        "relationship_type",
        "confidence_grade",
        "target_company",
        "neo4j_dirty",
    ]
    list_filter = ["relationship_type", "confidence_grade", "neo4j_dirty"]
    search_fields = ["source_company__symbol", "target_company_name"]
    readonly_fields = ["extracted_at", "system_confidence"]


# ── BusinessModelSnapshot / Evidence ──


@admin.register(BusinessModelSnapshot)
class BusinessModelSnapshotAdmin(admin.ModelAdmin):
    list_display = [
        "symbol",
        "as_of_date",
        "direct_customer_contact",
        "contract_model",
        "recurring_revenue_signal",
        "confidence_grade",
    ]
    list_filter = ["confidence_grade", "direct_customer_contact", "contract_model"]
    search_fields = ["symbol__symbol"]


@admin.register(BusinessModelEvidence)
class BusinessModelEvidenceAdmin(admin.ModelAdmin):
    list_display = ["snapshot", "field_name", "confidence"]
    list_filter = ["field_name"]


# ── FilingProcessLog ──


@admin.register(FilingProcessLog)
class FilingProcessLogAdmin(admin.ModelAdmin):
    list_display = ["symbol", "stage", "status", "duration_seconds", "started_at"]
    list_filter = ["stage", "status"]
    search_fields = ["symbol"]
    readonly_fields = ["started_at"]


# ── CompanyAlias ──


@admin.register(CompanyAlias)
class CompanyAliasAdmin(admin.ModelAdmin):
    list_display = ["alias", "ticker", "context_sector", "source", "created_at"]
    list_filter = ["source", "context_sector"]
    search_fields = ["alias", "ticker"]


# ── UnmatchedCompanyQueue — 핵심 관리 뷰 ──


@admin.register(UnmatchedCompanyQueue)
class UnmatchedCompanyQueueAdmin(admin.ModelAdmin):
    list_display = [
        "raw_company_name",
        "source_symbol",
        "occurrence_count",
        "cross_sector_flag",
        "status",
        "fuzzy_top1",
        "resolved_ticker",
    ]
    list_editable = ["status", "resolved_ticker"]
    list_filter = ["status"]
    search_fields = ["raw_company_name", "source_symbol"]
    ordering = ["-occurrence_count"]
    list_per_page = 50

    actions = ["mark_not_public", "mark_person", "auto_resolve_top_candidate"]

    @admin.display(description="Cross-Sector", boolean=False)
    def cross_sector_flag(self, obj):
        sectors = obj.source_sectors or []
        if len(sectors) >= 2:
            return f"⚠️ {len(sectors)}"
        return ""

    @admin.display(description="Fuzzy Top 1")
    def fuzzy_top1(self, obj):
        candidates = obj.fuzzy_candidates or []
        if candidates:
            top = candidates[0]
            return f"{top.get('ticker', '?')} ({top.get('score', 0):.0%})"
        return "-"

    @admin.action(description="Mark as Not Public")
    def mark_not_public(self, request, queryset):
        queryset.update(status="not_public")

    @admin.action(description="Mark as Person")
    def mark_person(self, request, queryset):
        queryset.update(status="person")

    @admin.action(description="Auto-resolve top candidate (≥90%)")
    def auto_resolve_top_candidate(self, request, queryset):
        resolved = 0
        for entry in queryset.filter(status="pending"):
            candidates = entry.fuzzy_candidates or []
            if candidates and candidates[0].get("score", 0) >= 0.90:
                entry.resolved_ticker = candidates[0]["ticker"]
                entry.status = "matched"
                entry.save(update_fields=["resolved_ticker", "status"])
                resolved += 1
        self.message_user(request, f"{resolved}건 자동 매칭 완료")


# ── PipelineIntelligenceReport (Phase 3) ──


@admin.register(PipelineIntelligenceReport)
class PipelineIntelligenceReportAdmin(admin.ModelAdmin):
    list_display = [
        "report_date",
        "severity_badge",
        "health_score_bar",
        "collection_score",
        "extraction_score",
        "matching_score",
        "created_at",
    ]
    list_filter = ["severity"]
    readonly_fields = ["created_at"]
    fieldsets = [
        (
            "Overview",
            {
                "fields": ("report_date", "hours_back", "severity", "health_score"),
            },
        ),
        (
            "5-Dimension Scores",
            {
                "fields": (
                    "collection_score",
                    "extraction_score",
                    "matching_score",
                    "sync_score",
                    "quality_score",
                ),
            },
        ),
        (
            "LLM Analysis",
            {
                "fields": ("summary", "cross_insights", "recommended_actions"),
            },
        ),
        (
            "Trend",
            {
                "fields": ("trend_vs_previous",),
            },
        ),
        (
            "Meta",
            {
                "fields": ("prompt_version", "created_at"),
            },
        ),
    ]
    actions = ["regenerate_report"]

    @admin.display(description="Severity")
    def severity_badge(self, obj):
        colors = {"healthy": "🟢", "warning": "🟡", "critical": "🔴"}
        return f"{colors.get(obj.severity, '⚪')} {obj.severity}"

    @admin.display(description="Health")
    def health_score_bar(self, obj):
        pct = int(obj.health_score * 100)
        return f"{pct}%"

    @admin.action(description="Regenerate Intelligence Report")
    def regenerate_report(self, request, queryset):
        from .intelligence import PipelineIntelligenceReporter

        reporter = PipelineIntelligenceReporter()
        result = reporter.generate_report(hours_back=24)
        self.message_user(request, f"Report generated: {result}")
