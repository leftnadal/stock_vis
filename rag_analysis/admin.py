from django.contrib import admin
from .models import DataBasket, BasketItem, AnalysisSession, AnalysisMessage


@admin.register(DataBasket)
class DataBasketAdmin(admin.ModelAdmin):
    """DataBasket Admin"""
    list_display = ['id', 'name', 'user', 'items_count', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'user__username', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'name', 'description')
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def items_count(self, obj):
        """바구니 아이템 개수"""
        return obj.items_count
    items_count.short_description = '아이템 수'


@admin.register(BasketItem)
class BasketItemAdmin(admin.ModelAdmin):
    """BasketItem Admin"""
    list_display = ['id', 'title', 'item_type', 'basket', 'reference_id', 'snapshot_date', 'created_at']
    list_filter = ['item_type', 'snapshot_date', 'created_at']
    search_fields = ['title', 'subtitle', 'reference_id', 'basket__name']
    readonly_fields = ['snapshot_date', 'created_at']

    fieldsets = (
        ('기본 정보', {
            'fields': ('basket', 'item_type', 'reference_id')
        }),
        ('표시 정보', {
            'fields': ('title', 'subtitle')
        }),
        ('데이터 스냅샷', {
            'fields': ('data_snapshot', 'snapshot_date'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(AnalysisSession)
class AnalysisSessionAdmin(admin.ModelAdmin):
    """AnalysisSession Admin"""
    list_display = ['id', 'user', 'status', 'basket', 'title', 'messages_count', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['user__username', 'title', 'basket__name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'basket', 'status', 'title')
        }),
        ('탐험 경로', {
            'fields': ('exploration_path',),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def messages_count(self, obj):
        """메시지 개수"""
        return obj.messages.count()
    messages_count.short_description = '메시지 수'


@admin.register(AnalysisMessage)
class AnalysisMessageAdmin(admin.ModelAdmin):
    """AnalysisMessage Admin"""
    list_display = ['id', 'session', 'role', 'content_preview', 'input_tokens', 'output_tokens', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['session__id', 'content']
    readonly_fields = ['created_at']

    fieldsets = (
        ('기본 정보', {
            'fields': ('session', 'role', 'content')
        }),
        ('LLM 제안', {
            'fields': ('suggestions',),
            'classes': ('collapse',)
        }),
        ('토큰 사용량', {
            'fields': ('input_tokens', 'output_tokens')
        }),
        ('메타 정보', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def content_preview(self, obj):
        """메시지 미리보기"""
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = '내용'
