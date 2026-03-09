from rest_framework import serializers


class ConversationStartSerializer(serializers.Serializer):
    entry_source = serializers.ChoiceField(
        choices=['news', 'free_input', 'popular', 'template', 'chainsight'],
    )
    source_news_id = serializers.UUIDField(required=False, allow_null=True)


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
