from rest_framework import serializers


class ConversationStartSerializer(serializers.Serializer):
    entry_source = serializers.ChoiceField(
        choices=['news', 'free_input', 'popular', 'template', 'chainsight'],
    )
    source_news_id = serializers.UUIDField(required=False, allow_null=True)


class SuggestionRequestSerializer(serializers.Serializer):
    source_news_id = serializers.UUIDField()
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    summary = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')
    sentiment = serializers.ChoiceField(
        choices=['positive', 'negative', 'neutral'],
        required=False,
        default='neutral',
    )


class ConversationResponseSerializer(serializers.Serializer):
    conversation_state = serializers.DictField()
    user_input = serializers.JSONField()

    def validate_user_input(self, value):
        """user_input 크기 제한 (프롬프트 인젝션/DoS 방지)."""
        if isinstance(value, str) and len(value) > 1000:
            raise serializers.ValidationError('입력은 1000자를 초과할 수 없습니다.')
        if isinstance(value, list) and len(value) > 20:
            raise serializers.ValidationError('선택 항목은 20개를 초과할 수 없습니다.')
        return value
