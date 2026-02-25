"""
뉴스 앱 Django Admin 설정
"""

from django.contrib import admin
from .models import NewsArticle, NewsEntity, EntityHighlight, SentimentHistory, MLModelHistory


class NewsEntityInline(admin.TabularInline):
    """뉴스 기사의 연결된 엔티티 인라인"""
    model = NewsEntity
    extra = 0
    fields = ['symbol', 'entity_name', 'entity_type', 'sentiment_score', 'source']
    readonly_fields = ['source']


class EntityHighlightInline(admin.TabularInline):
    """엔티티의 하이라이트 인라인"""
    model = EntityHighlight
    extra = 0
    fields = ['highlight_text', 'sentiment', 'location']


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    """뉴스 기사 관리"""
    list_display = ['title', 'source', 'published_at', 'sentiment_score', 'category', 'importance_score', 'llm_analyzed']
    list_filter = ['category', 'sentiment_source', 'is_press_release', 'source', 'published_at', 'llm_analyzed', 'ml_label_important']
    search_fields = ['title', 'summary', 'source']
    readonly_fields = ['id', 'url_hash', 'created_at', 'updated_at', 'importance_score', 'rule_tickers', 'rule_sectors', 'llm_analyzed', 'ml_label_24h', 'ml_label_important', 'ml_label_confidence', 'ml_label_updated_at']
    date_hierarchy = 'published_at'
    inlines = [NewsEntityInline]

    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'url', 'url_hash', 'title', 'summary', 'image_url')
        }),
        ('출처 및 분류', {
            'fields': ('source', 'published_at', 'language', 'category', 'is_press_release')
        }),
        ('Provider IDs', {
            'fields': ('finnhub_id', 'marketaux_uuid'),
            'classes': ('collapse',)
        }),
        ('감성 분석', {
            'fields': ('sentiment_score', 'sentiment_source')
        }),
        ('Intelligence Pipeline v3', {
            'fields': ('importance_score', 'rule_tickers', 'rule_sectors', 'llm_analyzed', 'llm_analysis'),
            'classes': ('collapse',)
        }),
        ('ML Labels', {
            'fields': ('ml_label_24h', 'ml_label_important', 'ml_label_confidence', 'ml_label_updated_at'),
            'classes': ('collapse',)
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(NewsEntity)
class NewsEntityAdmin(admin.ModelAdmin):
    """뉴스-종목 연결 관리"""
    list_display = ['symbol', 'entity_name', 'entity_type', 'sentiment_score', 'source', 'news_published_at']
    list_filter = ['entity_type', 'source', 'exchange', 'country']
    search_fields = ['symbol', 'entity_name', 'industry']
    readonly_fields = ['source']
    inlines = [EntityHighlightInline]

    def news_published_at(self, obj):
        return obj.news.published_at
    news_published_at.short_description = 'Published At'
    news_published_at.admin_order_field = 'news__published_at'


@admin.register(EntityHighlight)
class EntityHighlightAdmin(admin.ModelAdmin):
    """엔티티 하이라이트 관리"""
    list_display = ['news_entity', 'highlight_text_short', 'sentiment', 'location']
    list_filter = ['location', 'sentiment']
    search_fields = ['highlight_text', 'news_entity__symbol']

    def highlight_text_short(self, obj):
        return obj.highlight_text[:100] + '...' if len(obj.highlight_text) > 100 else obj.highlight_text
    highlight_text_short.short_description = 'Highlight Text'


@admin.register(SentimentHistory)
class SentimentHistoryAdmin(admin.ModelAdmin):
    """일별 감성 집계 관리"""
    list_display = ['symbol', 'date', 'avg_sentiment', 'news_count', 'positive_count', 'negative_count', 'neutral_count']
    list_filter = ['date', 'avg_sentiment']
    search_fields = ['symbol']
    date_hierarchy = 'date'

    readonly_fields = ['symbol', 'date', 'avg_sentiment', 'news_count', 'positive_count', 'negative_count', 'neutral_count']

    def has_add_permission(self, request):
        """집계 데이터는 수동 추가 불가"""
        return False

    def has_delete_permission(self, request, obj=None):
        """집계 데이터는 삭제 불가"""
        return False


@admin.register(MLModelHistory)
class MLModelHistoryAdmin(admin.ModelAdmin):
    """ML 모델 학습 이력 관리"""
    list_display = ['model_version', 'algorithm', 'f1_score', 'training_samples', 'deployment_status', 'safety_gate_passed', 'trained_at']
    list_filter = ['deployment_status', 'algorithm', 'safety_gate_passed']
    readonly_fields = ['trained_at']

    fieldsets = (
        ('모델 정보', {
            'fields': ('model_version', 'algorithm', 'training_samples', 'feature_count', 'trained_at')
        }),
        ('성능 지표', {
            'fields': ('f1_score', 'precision', 'recall', 'accuracy')
        }),
        ('가중치', {
            'fields': ('weights', 'smoothed_weights', 'feature_importance', 'training_config'),
            'classes': ('collapse',)
        }),
        ('Safety Gate', {
            'fields': ('safety_gate_passed', 'safety_gate_details')
        }),
        ('배포', {
            'fields': ('deployment_status', 'deployed_at', 'shadow_comparison'),
            'classes': ('collapse',)
        }),
    )
