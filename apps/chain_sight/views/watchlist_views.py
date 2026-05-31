from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from chainsight.graph.exceptions import GraphConnectionError, GraphQueryError
from chainsight.models import PathAction, SavedPath
from chainsight.serializers.path_watchlist import (
    SavedPathCreateSerializer,
    SavedPathDetailSerializer,
    SavedPathListSerializer,
)
from chainsight.services.alternatives_service import find_alternatives
from chainsight.services.expand_service import find_expansion_candidates
from chainsight.services.path_service import (
    build_edge_snapshot,
    build_initial_why_now,
    build_path_signature,
    generate_summary_path,
)
from chainsight.services.recheck_service import run_recheck


class WatchlistUserThrottle(UserRateThrottle):
    rate = "30/minute"


class WatchlistViewSet(viewsets.ModelViewSet):
    # security audit P0 #2 (2026-05-19): AllowAny + user__isnull=True 풀이 IDOR 노출.
    # IsAuthenticated 강제하여 request.user 기준 격리.
    permission_classes = [IsAuthenticated]
    throttle_classes = [WatchlistUserThrottle]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = SavedPath.objects.filter(user=self.request.user)
        status_param = self.request.query_params.get("status")
        if status_param:
            statuses = [s.strip() for s in status_param.split(",")]
            qs = qs.filter(status__in=statuses)
        return qs.prefetch_related("actions")

    def get_serializer_class(self):
        if self.action == "list":
            return SavedPathListSerializer
        if self.action == "create":
            return SavedPathCreateSerializer
        return SavedPathDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        path_nodes = validated["path_nodes"]

        try:
            edge_snapshot = build_edge_snapshot(path_nodes)
        except (GraphConnectionError, GraphQueryError):
            edge_snapshot = []

        path_signature = build_path_signature(path_nodes, edge_snapshot)
        why_now = build_initial_why_now(path_nodes, edge_snapshot)
        summary_path = generate_summary_path(path_nodes)

        with transaction.atomic():
            saved_path = SavedPath.objects.create(
                user=request.user,
                path_nodes=path_nodes,
                summary_path=summary_path,
                path_signature=path_signature,
                edge_snapshot=edge_snapshot,
                why_now_snapshot=why_now,
                source_center=validated.get("source_center"),
                source_slot=validated.get("source_slot"),
                status=SavedPath.Status.WATCHING,
            )

            PathAction.objects.create(
                saved_path=saved_path,
                action_type=PathAction.ActionType.WATCH,
                metadata={
                    "source_center": validated.get("source_center"),
                    "source_slot": validated.get("source_slot"),
                },
            )

        response_serializer = SavedPathDetailSerializer(saved_path)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        saved_path = self.get_object()
        if saved_path.status == SavedPath.Status.ARCHIVED:
            return Response(
                {"detail": "이미 archived 상태입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            saved_path.status = SavedPath.Status.ARCHIVED
            saved_path.save(update_fields=["status", "updated_at"])
            PathAction.objects.create(
                saved_path=saved_path,
                action_type=PathAction.ActionType.ARCHIVE,
            )
        return Response(SavedPathDetailSerializer(saved_path).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        saved_path = self.get_object()
        if saved_path.status == SavedPath.Status.RESOLVED:
            return Response(
                {"detail": "이미 resolved 상태입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            saved_path.status = SavedPath.Status.RESOLVED
            saved_path.save(update_fields=["status", "updated_at"])
            PathAction.objects.create(
                saved_path=saved_path,
                action_type=PathAction.ActionType.RESOLVE,
            )
        return Response(SavedPathDetailSerializer(saved_path).data)

    @action(detail=True, methods=["post"])
    def recheck(self, request, pk=None):
        saved_path = self.get_object()
        if saved_path.status in (SavedPath.Status.ARCHIVED, SavedPath.Status.RESOLVED):
            return Response(
                {"detail": f"{saved_path.status} 상태에서는 Recheck할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = run_recheck(saved_path)
        except (GraphConnectionError, GraphQueryError):
            return Response(
                {"detail": "Neo4j 연결에 실패했습니다. 잠시 후 다시 시도해주세요."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        saved_path.refresh_from_db()
        return Response(
            {
                "headline": result.headline,
                "strengthened": result.strengthened,
                "weakened": result.weakened,
                "unchanged": result.unchanged,
                "broken_edges": result.broken_edges,
                "path_intact": result.path_intact,
                "suggested_action": result.suggested_action,
                "suggested_reason": result.suggested_reason,
                "updated_why_now": result.updated_why_now,
                "status": saved_path.status,
                "recheck_count": saved_path.recheck_count,
            }
        )

    @action(detail=True, methods=["post"])
    def expand(self, request, pk=None):
        saved_path = self.get_object()
        if saved_path.status in (SavedPath.Status.ARCHIVED, SavedPath.Status.RESOLVED):
            return Response(
                {"detail": f"{saved_path.status} 상태에서는 Expand할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        target = request.data.get("target_ticker")
        if not target:
            target = saved_path.path_nodes[-1]
        if target not in saved_path.path_nodes:
            return Response(
                {"detail": "target_ticker가 경로에 포함되지 않습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            limit = min(int(request.data.get("limit", 10)), 50)
        except (ValueError, TypeError):
            limit = 10
        try:
            result = find_expansion_candidates(
                source_ticker=target,
                excluded_tickers=saved_path.path_nodes,
                limit=limit,
            )
        except (GraphConnectionError, GraphQueryError):
            return Response(
                {"detail": "Neo4j 연결에 실패했습니다. 잠시 후 다시 시도해주세요."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        PathAction.objects.create(
            saved_path=saved_path,
            action_type=PathAction.ActionType.EXPAND,
            metadata={
                "target_ticker": target,
                "candidates_count": len(result["candidates"]),
                "top_candidates": [c["ticker"] for c in result["candidates"][:3]],
            },
        )
        return Response(result)

    @action(detail=True, methods=["post"])
    def alternatives(self, request, pk=None):
        saved_path = self.get_object()
        if saved_path.status in (SavedPath.Status.ARCHIVED, SavedPath.Status.RESOLVED):
            return Response(
                {"detail": f"{saved_path.status} 상태에서는 Alternatives 탐색 불가."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        target = request.data.get("target_ticker")
        if not target:
            return Response(
                {"detail": "target_ticker는 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if target not in saved_path.path_nodes:
            return Response(
                {"detail": "target_ticker가 경로에 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            limit = min(int(request.data.get("limit", 10)), 50)
        except (ValueError, TypeError):
            limit = 10
        try:
            result = find_alternatives(
                path_nodes=saved_path.path_nodes,
                target_ticker=target,
                limit=limit,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (GraphConnectionError, GraphQueryError):
            return Response(
                {"detail": "Neo4j 연결에 실패했습니다. 잠시 후 다시 시도해주세요."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        PathAction.objects.create(
            saved_path=saved_path,
            action_type=PathAction.ActionType.ALTERNATIVES,
            metadata={
                "target_ticker": target,
                "candidates_count": len(result["alternatives"]),
                "top_candidates": [c["ticker"] for c in result["alternatives"][:3]],
            },
        )
        return Response(result)
