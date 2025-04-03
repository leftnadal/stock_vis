##1차 작성중
from rest_framework import serializers
from .models import EconomicIndicator

class EconomicIndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EconomicIndicator
        fields = '__all__'

class IndicatorHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EconomicIndicator
        fields = ['id', 'date', 'value', 'unit']