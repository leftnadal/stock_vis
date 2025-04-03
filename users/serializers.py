## 1차 작성중..
from rest_framework import serializers
from .models import User

class StockListingField(serializers.RelatedField):
    def to_representation(self, value):
        return {
            'id': value.id,
            'stock_name': value.stock_name,
            'symbol': value.symbol
        }

class UserSerializer(serializers.ModelSerializer):
    """일반 사용자용 시리얼라이저 (제한된 정보만 포함)"""
    favorite_stock = StockListingField(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'user_name', 'nick_name', 'favorite_stock']

class PrivateUserSerializer(serializers.ModelSerializer):
    """소유자/관리자용 시리얼라이저 (개인 정보 포함)"""
    favorite_stock = StockListingField(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'user_name', 'email', 'nick_name', 'favorite_stock', 'is_superuser', 'is_staff']
        read_only_fields = ['is_superuser', 'is_staff']