from django.contrib import admin

from .models import (
    HypothesisEvent,
    IndicatorReading,
    InvestorDNA,
    PopularThesisCache,
    Thesis,
    ThesisAlert,
    ThesisFollow,
    ThesisIndicator,
    ThesisPremise,
    ThesisSnapshot,
    ValidityRecord,
)


@admin.register(Thesis)
class ThesisAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'status', 'current_state', 'created_at']
    list_filter = ['status', 'current_state', 'thesis_type', 'direction']
    search_fields = ['title', 'user__email']


@admin.register(ThesisPremise)
class ThesisPremiseAdmin(admin.ModelAdmin):
    list_display = ['thesis', 'content', 'category', 'weight', 'is_active']


@admin.register(ThesisIndicator)
class ThesisIndicatorAdmin(admin.ModelAdmin):
    list_display = [
        'thesis', 'name', 'indicator_type', 'support_direction',
        'current_score', 'is_active',
    ]
    list_filter = ['indicator_type', 'data_source', 'is_active']


@admin.register(IndicatorReading)
class IndicatorReadingAdmin(admin.ModelAdmin):
    list_display = ['indicator', 'value', 'asof', 'validation_status']
    list_filter = ['validation_status']
    date_hierarchy = 'asof'


@admin.register(ThesisSnapshot)
class ThesisSnapshotAdmin(admin.ModelAdmin):
    list_display = ['thesis', 'asof_date', 'overall_score', 'state', 'data_coverage']
    date_hierarchy = 'asof_date'


@admin.register(ThesisAlert)
class ThesisAlertAdmin(admin.ModelAdmin):
    list_display = [
        'thesis', 'alert_type', 'severity', 'is_read', 'is_pushed', 'created_at',
    ]
    list_filter = ['alert_type', 'severity', 'is_read', 'is_pushed']


@admin.register(HypothesisEvent)
class HypothesisEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'thesis', 'event_type', 'created_at']
    list_filter = ['event_type']
    date_hierarchy = 'created_at'


@admin.register(ValidityRecord)
class ValidityRecordAdmin(admin.ModelAdmin):
    list_display = [
        'thesis', 'indicator', 'thesis_type',
        'indicator_aligned', 'thesis_correct', 'score',
    ]


@admin.register(InvestorDNA)
class InvestorDNAAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_theses', 'correct_count', 'updated_at']


@admin.register(ThesisFollow)
class ThesisFollowAdmin(admin.ModelAdmin):
    list_display = ['user', 'original_thesis', 'user_thesis', 'created_at']


@admin.register(PopularThesisCache)
class PopularThesisCacheAdmin(admin.ModelAdmin):
    list_display = ['thesis', 'follower_count', 'support_ratio', 'rank', 'cached_at']
