from rest_framework import serializers
from .models import DataBasket, BasketItem, AnalysisSession, AnalysisMessage


class BasketItemSerializer(serializers.ModelSerializer):
    """바구니 아이템 시리얼라이저"""

    item_type_display = serializers.CharField(
        source="get_item_type_display",
        read_only=True
    )

    class Meta:
        model = BasketItem
        fields = [
            "id", "item_type", "item_type_display",
            "reference_id", "title", "subtitle",
            "data_units",
            "data_snapshot", "snapshot_date", "created_at"
        ]
        read_only_fields = ["snapshot_date", "created_at"]


class DataBasketSerializer(serializers.ModelSerializer):
    """데이터 바구니 시리얼라이저"""

    items = BasketItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    can_add_item = serializers.SerializerMethodField()

    # 용량 관련 필드
    current_units = serializers.IntegerField(read_only=True)
    remaining_units = serializers.IntegerField(read_only=True)
    max_units = serializers.SerializerMethodField()

    class Meta:
        model = DataBasket
        fields = [
            "id", "name", "description",
            "items", "items_count", "can_add_item",
            "current_units", "remaining_units", "max_units",
            "created_at", "updated_at"
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_can_add_item(self, obj) -> bool:
        return obj.can_add_item()

    def get_max_units(self, obj) -> int:
        return obj.MAX_UNITS


class AnalysisMessageSerializer(serializers.ModelSerializer):
    """분석 메시지 시리얼라이저"""

    class Meta:
        model = AnalysisMessage
        fields = [
            "id", "role", "content", "suggestions",
            "input_tokens", "output_tokens", "created_at"
        ]
        read_only_fields = ["created_at"]


class AnalysisSessionSerializer(serializers.ModelSerializer):
    """분석 세션 시리얼라이저"""

    messages = AnalysisMessageSerializer(many=True, read_only=True)
    basket = DataBasketSerializer(read_only=True)
    basket_id = serializers.PrimaryKeyRelatedField(
        queryset=DataBasket.objects.all(),
        source="basket",
        write_only=True
    )

    class Meta:
        model = AnalysisSession
        fields = [
            "id", "basket", "basket_id", "status", "title",
            "exploration_path", "messages",
            "created_at", "updated_at"
        ]
        read_only_fields = ["status", "exploration_path", "created_at", "updated_at"]
