import re

from rest_framework import serializers

from apps.chain_sight.models import PathAction, SavedPath


class PathActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PathAction
        fields = ["id", "action_type", "metadata", "created_at"]


class SavedPathListSerializer(serializers.ModelSerializer):
    latest_headline = serializers.SerializerMethodField()
    path_length = serializers.SerializerMethodField()

    class Meta:
        model = SavedPath
        fields = [
            "id",
            "summary_path",
            "path_signature",
            "status",
            "latest_headline",
            "recheck_count",
            "path_length",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_latest_headline(self, obj) -> str:
        if obj.why_now_snapshot and isinstance(obj.why_now_snapshot, dict):
            return obj.why_now_snapshot.get("headline", "")
        return ""

    def get_path_length(self, obj) -> int:
        return len(obj.path_nodes) if obj.path_nodes else 0


class SavedPathDetailSerializer(serializers.ModelSerializer):
    actions = PathActionSerializer(many=True, read_only=True)

    class Meta:
        model = SavedPath
        fields = [
            "id",
            "path_nodes",
            "summary_path",
            "path_signature",
            "edge_snapshot",
            "why_now_snapshot",
            "source_center",
            "source_slot",
            "status",
            "recheck_count",
            "created_at",
            "updated_at",
            "actions",
        ]
        read_only_fields = [
            "id",
            "summary_path",
            "path_signature",
            "edge_snapshot",
            "why_now_snapshot",
            "status",
            "recheck_count",
            "created_at",
            "updated_at",
            "actions",
        ]


class SavedPathCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedPath
        fields = ["path_nodes", "source_center", "source_slot"]

    def validate_path_nodes(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("path_nodes는 리스트여야 합니다.")
        if len(value) < 2:
            raise serializers.ValidationError("경로는 최소 2개 노드 필요.")
        if len(value) > 10:
            raise serializers.ValidationError("경로는 최대 10개 노드까지.")
        for ticker in value:
            if not isinstance(ticker, str) or not re.match(r"^[A-Za-z]{1,5}$", ticker):
                raise serializers.ValidationError(f"유효하지 않은 ticker: {ticker}")
        if len(set(value)) != len(value):
            raise serializers.ValidationError("경로 내 중복 ticker 불가.")
        return [t.upper() for t in value]
