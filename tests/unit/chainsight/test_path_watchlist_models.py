import pytest
from django.core.exceptions import ValidationError

from apps.chain_sight.models import PathAction, SavedPath


@pytest.mark.django_db
class TestSavedPathModel:

    def test_create_minimal(self):
        """최소 필드로 생성 가능"""
        path = SavedPath.objects.create(path_nodes=['NVDA', 'TSM'])
        assert path.status == SavedPath.Status.WATCHING
        assert path.recheck_count == 0
        assert path.user is None

    def test_full_data_roundtrip(self):
        """JSONField 저장/조회 round-trip"""
        edge_snapshot = [
            {'from': 'NVDA', 'to': 'TSM', 'type': 'SUPPLIES_TO',
             'truth_score': 85, 'status': 'confirmed'}
        ]
        why_now = {
            'headline': '장비 체인 relevance 상승',
            'signals': [{'type': 'heat_score_up', 'delta': 0.12}],
            'generated_at': '2026-04-16T07:30:00Z',
        }
        path = SavedPath.objects.create(
            path_nodes=['NVDA', 'TSM'],
            summary_path=['NVDA', 'TSM'],
            path_signature='공급망 중심 · Technology',
            edge_snapshot=edge_snapshot,
            why_now_snapshot=why_now,
            source_center='NVDA',
            source_slot='exploration_trail',
        )
        reloaded = SavedPath.objects.get(pk=path.pk)
        assert reloaded.edge_snapshot == edge_snapshot
        assert reloaded.why_now_snapshot['headline'] == '장비 체인 relevance 상승'

    def test_ordering_by_updated_at(self):
        """기본 정렬: -updated_at"""
        p1 = SavedPath.objects.create(path_nodes=['A', 'B'])
        p2 = SavedPath.objects.create(path_nodes=['C', 'D'])
        ordered = list(SavedPath.objects.all()[:2])
        assert ordered[0].pk == p2.pk
        assert ordered[1].pk == p1.pk

    def test_invalid_status_rejected(self):
        """유효하지 않은 status는 full_clean에서 거부"""
        path = SavedPath(path_nodes=['A', 'B'], status='invalid_status')
        with pytest.raises(ValidationError):
            path.full_clean()


@pytest.mark.django_db
class TestPathActionModel:

    def test_create_action(self):
        """PathAction 생성 + 관계"""
        path = SavedPath.objects.create(path_nodes=['NVDA', 'TSM'])
        action = PathAction.objects.create(
            saved_path=path,
            action_type=PathAction.ActionType.WATCH,
            metadata={'source_slot': 'exploration_trail'},
        )
        assert path.actions.count() == 1
        assert path.actions.first().action_type == 'watch'

    def test_cascade_delete(self):
        """SavedPath 삭제 시 PathAction도 삭제"""
        path = SavedPath.objects.create(path_nodes=['NVDA', 'TSM'])
        PathAction.objects.create(saved_path=path, action_type='watch')
        path_id = path.pk
        path.delete()
        assert PathAction.objects.filter(saved_path_id=path_id).count() == 0
