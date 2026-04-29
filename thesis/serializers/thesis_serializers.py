from rest_framework import serializers

from thesis.models import Thesis, ThesisPremise


class ThesisPremiseInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThesisPremise
        fields = ['id', 'content', 'category', 'weight', 'is_active', 'is_paused', 'order']


class ThesisListSerializer(serializers.ModelSerializer):
    days_active = serializers.SerializerMethodField()

    class Meta:
        model = Thesis
        fields = [
            'id', 'title', 'direction', 'target', 'target_type',
            'status', 'current_state', 'current_score',
            'thesis_type', 'entry_source', 'days_active',
            'created_at', 'updated_at',
        ]

    def get_days_active(self, obj) -> int:
        from django.utils import timezone
        return (timezone.now() - obj.created_at).days


class ThesisDetailSerializer(serializers.ModelSerializer):
    premises = ThesisPremiseInlineSerializer(many=True, read_only=True)
    days_active = serializers.SerializerMethodField()
    indicator_count = serializers.SerializerMethodField()

    class Meta:
        model = Thesis
        fields = [
            'id', 'title', 'description', 'direction', 'target', 'target_type',
            'expected_timeframe', 'expected_magnitude',
            'target_date_start', 'target_date_end',
            'thesis_type', 'entry_source',
            'status', 'current_state', 'current_score',
            'outcome', 'outcome_note',
            'premises', 'indicator_count', 'days_active',
            'created_at', 'updated_at', 'closed_at',
        ]
        read_only_fields = [
            'id', 'status', 'current_state', 'current_score',
            'outcome', 'outcome_note', 'closed_at',
            'created_at', 'updated_at',
        ]

    def get_days_active(self, obj) -> int:
        from django.utils import timezone
        return (timezone.now() - obj.created_at).days

    def get_indicator_count(self, obj) -> int:
        return obj.indicators.filter(is_active=True).count()


class ThesisCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thesis
        fields = [
            'title', 'description', 'direction', 'target', 'target_type',
            'expected_timeframe', 'expected_magnitude',
            'target_date_start', 'target_date_end',
            'thesis_type', 'entry_source',
        ]

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['status'] = 'active'
        return super().create(validated_data)


class ThesisPremiseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThesisPremise
        fields = [
            'id', 'content', 'category', 'weight',
            'is_active', 'is_paused', 'order', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
