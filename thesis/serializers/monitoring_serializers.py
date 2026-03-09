from rest_framework import serializers

from thesis.models import ThesisSnapshot, ThesisAlert


class ThesisSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThesisSnapshot
        fields = [
            'id', 'asof_date', 'data_coverage',
            'overall_score', 'state',
            'premise_scores', 'indicator_degrees',
            'notable_changes', 'ai_summary',
        ]


class ThesisAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThesisAlert
        fields = [
            'id', 'alert_type', 'severity',
            'title', 'message',
            'is_read', 'is_pushed',
            'indicator', 'created_at',
        ]
