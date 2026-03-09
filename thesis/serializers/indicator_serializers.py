from rest_framework import serializers

from thesis.models import ThesisIndicator, IndicatorReading

# data_params 허용 키 (API 파라미터 조작 방지)
ALLOWED_DATA_PARAM_KEYS = {
    'symbol', 'series_id', 'metric', 'indicator', 'period',
}
MAX_DATA_PARAMS_SIZE = 5  # 최대 키 개수


class ThesisIndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThesisIndicator
        fields = [
            'id', 'name', 'indicator_type', 'data_source', 'data_params',
            'support_direction', 'weight', 'is_active', 'is_paused',
            'current_score', 'current_degree', 'current_color', 'current_label',
            'premise', 'override_score',
            'window', 'decay', 'epsilon',
            'created_at',
        ]
        read_only_fields = [
            'id', 'current_score', 'current_degree',
            'current_color', 'current_label', 'created_at',
            'override_score', 'epsilon', 'decay', 'window',
        ]

    def validate_data_params(self, value):
        """data_params 키/값 검증."""
        if not isinstance(value, dict):
            raise serializers.ValidationError('data_params는 dict여야 합니다.')
        if len(value) > MAX_DATA_PARAMS_SIZE:
            raise serializers.ValidationError(f'data_params 키 최대 {MAX_DATA_PARAMS_SIZE}개.')
        unknown_keys = set(value.keys()) - ALLOWED_DATA_PARAM_KEYS
        if unknown_keys:
            raise serializers.ValidationError(f'허용되지 않은 키: {unknown_keys}')
        # 값은 문자열/숫자만 허용
        for k, v in value.items():
            if not isinstance(v, (str, int, float)):
                raise serializers.ValidationError(f'{k} 값은 문자열 또는 숫자여야 합니다.')
        return value


class IndicatorReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorReading
        fields = [
            'id', 'value', 'raw_value', 'asof',
            'validation_status', 'fetched_at',
        ]
        read_only_fields = ['id', 'fetched_at']
