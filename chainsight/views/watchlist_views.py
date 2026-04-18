from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from chainsight.models import SavedPath, PathAction
from chainsight.serializers.path_watchlist import (
    SavedPathListSerializer,
    SavedPathDetailSerializer,
    SavedPathCreateSerializer,
)
from chainsight.services.path_service import (
    build_edge_snapshot,
    build_path_signature,
    build_initial_why_now,
    generate_summary_path,
)
from chainsight.services.recheck_service import run_recheck


class WatchlistViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = SavedPath.objects.all()
        user = self.request.user if self.request.user.is_authenticated else None
        if user:
            qs = qs.filter(user=user)
        else:
            qs = qs.filter(user__isnull=True)
        status_param = self.request.query_params.get('status')
        if status_param:
            statuses = [s.strip() for s in status_param.split(',')]
            qs = qs.filter(status__in=statuses)
        return qs.prefetch_related('actions')

    def get_serializer_class(self):
        if self.action == 'list':
            return SavedPathListSerializer
        if self.action == 'create':
            return SavedPathCreateSerializer
        return SavedPathDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        path_nodes = validated['path_nodes']

        edge_snapshot = build_edge_snapshot(path_nodes)
        path_signature = build_path_signature(path_nodes, edge_snapshot)
        why_now = build_initial_why_now(path_nodes, edge_snapshot)
        summary_path = generate_summary_path(path_nodes)

        user = request.user if request.user.is_authenticated else None

        saved_path = SavedPath.objects.create(
            user=user,
            path_nodes=path_nodes,
            summary_path=summary_path,
            path_signature=path_signature,
            edge_snapshot=edge_snapshot,
            why_now_snapshot=why_now,
            source_center=validated.get('source_center'),
            source_slot=validated.get('source_slot'),
            status=SavedPath.Status.WATCHING,
        )

        PathAction.objects.create(
            saved_path=saved_path,
            action_type=PathAction.ActionType.WATCH,
            metadata={
                'source_center': validated.get('source_center'),
                'source_slot': validated.get('source_slot'),
            }
        )

        response_serializer = SavedPathDetailSerializer(saved_path)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        saved_path = self.get_object()
        if saved_path.status == SavedPath.Status.ARCHIVED:
            return Response(
                {'detail': '이미 archived 상태입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        saved_path.status = SavedPath.Status.ARCHIVED
        saved_path.save(update_fields=['status', 'updated_at'])
        PathAction.objects.create(
            saved_path=saved_path,
            action_type=PathAction.ActionType.ARCHIVE,
        )
        return Response(SavedPathDetailSerializer(saved_path).data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        saved_path = self.get_object()
        if saved_path.status == SavedPath.Status.RESOLVED:
            return Response(
                {'detail': '이미 resolved 상태입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        saved_path.status = SavedPath.Status.RESOLVED
        saved_path.save(update_fields=['status', 'updated_at'])
        PathAction.objects.create(
            saved_path=saved_path,
            action_type=PathAction.ActionType.RESOLVE,
        )
        return Response(SavedPathDetailSerializer(saved_path).data)

    @action(detail=True, methods=['post'])
    def recheck(self, request, pk=None):
        saved_path = self.get_object()
        if saved_path.status in (SavedPath.Status.ARCHIVED, SavedPath.Status.RESOLVED):
            return Response(
                {'detail': f'{saved_path.status} 상태에서는 Recheck할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = run_recheck(saved_path)
        saved_path.refresh_from_db()
        return Response({
            'headline': result.headline,
            'strengthened': result.strengthened,
            'weakened': result.weakened,
            'unchanged': result.unchanged,
            'broken_edges': result.broken_edges,
            'path_intact': result.path_intact,
            'suggested_action': result.suggested_action,
            'suggested_reason': result.suggested_reason,
            'updated_why_now': result.updated_why_now,
            'status': saved_path.status,
            'recheck_count': saved_path.recheck_count,
        })
