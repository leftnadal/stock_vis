from django.contrib import admin

from .models import (
    ChainNewsEvent,
    CompanyCapitalDNA,
    CompanyChainProfile,
    CompanyEventReaction,
    CompanyGrowthStage,
    CompanyInsiderSignal,
    CompanyNarrativeTag,
    CompanyRevenueStructure,
    CompanySensitivityProfile,
    PathAction,
    SavedPath,
)


@admin.register(CompanySensitivityProfile)
class CompanySensitivityProfileAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'rate_sensitivity', 'forex_sensitivity', 'commodity_sensitivity', 'beta']
    list_filter = ['rate_sensitivity', 'forex_sensitivity', 'is_regulated_industry']
    search_fields = ['symbol__symbol']


@admin.register(CompanyGrowthStage)
class CompanyGrowthStageAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'stage', 'revenue_cagr_3y', 'fcf_trend', 'confidence']
    list_filter = ['stage', 'confidence', 'fcf_trend']
    search_fields = ['symbol__symbol']


@admin.register(CompanyCapitalDNA)
class CompanyCapitalDNAAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'capital_type', 'rd_to_revenue', 'capex_to_revenue', 'buyback_yield']
    list_filter = ['capital_type', 'rd_trend', 'capex_trend']
    search_fields = ['symbol__symbol']


@admin.register(CompanyInsiderSignal)
class CompanyInsiderSignalAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'insider_signal', 'smart_money_signal', 'institutional_ownership_pct', 'short_interest_pct']
    list_filter = ['insider_signal', 'smart_money_signal', 'top_holder_action']
    search_fields = ['symbol__symbol']


@admin.register(CompanyNarrativeTag)
class CompanyNarrativeTagAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'primary_narrative', 'narrative_sentiment', 'analyst_consensus', 'generated_by']
    list_filter = ['narrative_sentiment', 'analyst_consensus', 'generated_by']
    search_fields = ['symbol__symbol', 'primary_narrative']


@admin.register(CompanyEventReaction)
class CompanyEventReactionAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'event_type', 'sample_count', 'avg_return_1d', 'reaction_grade', 'confidence']
    list_filter = ['reaction_grade', 'confidence', 'event_type']
    search_fields = ['symbol__symbol', 'event_type']


@admin.register(CompanyRevenueStructure)
class CompanyRevenueStructureAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'business_model_type', 'customer_concentration_risk', 'extraction_method']
    list_filter = ['business_model_type', 'customer_concentration_risk', 'extraction_method']
    search_fields = ['symbol__symbol']


@admin.register(CompanyChainProfile)
class CompanyChainProfileAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'growth_stage', 'capital_type', 'overall_grade', 'profile_completeness']
    list_filter = ['growth_stage', 'capital_type', 'overall_grade']
    search_fields = ['symbol__symbol']


@admin.register(ChainNewsEvent)
class ChainNewsEventAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'source', 'title', 'sentiment_label', 'event_type', 'published_at']
    list_filter = ['source', 'sentiment_label', 'event_importance', 'is_duplicate']
    search_fields = ['symbol__symbol', 'title']


@admin.register(SavedPath)
class SavedPathAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'path_signature',
                    'recheck_count', 'updated_at')
    list_filter = ('status', 'updated_at')
    search_fields = ('path_signature', 'source_center')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)


@admin.register(PathAction)
class PathActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'saved_path', 'action_type', 'created_at')
    list_filter = ('action_type', 'created_at')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
