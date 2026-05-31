from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.chain_sight.models import PathAction, SavedPath


@pytest.fixture
def auth_user(db):
    """audit P0 #5: 테스트용 인증 사용자 (SavedPath 생성 시 user 지정에 사용)."""
    import uuid

    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username=f'test_{uuid.uuid4().hex[:8]}',
        password='test1234',
    )


@pytest.fixture
def client(auth_user):
    """audit P0 #5: 인증된 client (auth_user로 force_authenticate)."""
    api_client = APIClient()
    api_client.force_authenticate(user=auth_user)
    return api_client


@pytest.mark.django_db
@patch(
    'apps.chain_sight.views.watchlist_views.build_edge_snapshot',
    return_value=[
        {'from': 'NVDA', 'to': 'TSM', 'type': 'SUPPLIES_TO',
         'truth_score': 85, 'status': 'confirmed'}
    ]
)
def test_watch_success(mock_edge, client):
    response = client.post('/api/v1/chainsight/watchlist/', {
        'path_nodes': ['NVDA', 'TSM'],
        'source_center': 'NVDA',
        'source_slot': 'exploration_trail',
    }, format='json')
    assert response.status_code == 201
    assert response.data['path_nodes'] == ['NVDA', 'TSM']
    assert len(response.data['edge_snapshot']) == 1
    assert response.data['path_signature']
    assert response.data['status'] == 'watching'
    assert len(response.data['actions']) == 1
    assert response.data['actions'][0]['action_type'] == 'watch'


@pytest.mark.django_db
def test_watch_validation_too_few(client):
    r = client.post('/api/v1/chainsight/watchlist/',
                     {'path_nodes': ['NVDA']}, format='json')
    assert r.status_code == 400


@pytest.mark.django_db
def test_watch_validation_duplicate(client):
    r = client.post('/api/v1/chainsight/watchlist/',
                     {'path_nodes': ['NVDA', 'NVDA']}, format='json')
    assert r.status_code == 400


@pytest.mark.django_db
def test_watch_validation_empty(client):
    r = client.post('/api/v1/chainsight/watchlist/', {}, format='json')
    assert r.status_code == 400


@pytest.mark.django_db
def test_list_filter_by_status(client, auth_user):
    SavedPath.objects.create(path_nodes=['A', 'B'], status='watching', user=auth_user)
    SavedPath.objects.create(path_nodes=['C', 'D'], status='archived', user=auth_user)
    SavedPath.objects.create(path_nodes=['E', 'F'], status='resolved', user=auth_user)
    r = client.get('/api/v1/chainsight/watchlist/?status=watching,archived')
    assert r.status_code == 200
    assert len(r.data) == 2


@pytest.mark.django_db
def test_list_default_ordering(client, auth_user):
    p1 = SavedPath.objects.create(path_nodes=['A', 'B'], user=auth_user)
    p2 = SavedPath.objects.create(path_nodes=['C', 'D'], user=auth_user)
    r = client.get('/api/v1/chainsight/watchlist/')
    assert str(r.data[0]['id']) == str(p2.id)
    assert str(r.data[1]['id']) == str(p1.id)


@pytest.mark.django_db
def test_retrieve_with_actions(client, auth_user):
    path = SavedPath.objects.create(path_nodes=['A', 'B'], user=auth_user)
    PathAction.objects.create(saved_path=path, action_type='watch')
    PathAction.objects.create(saved_path=path, action_type='recheck')
    r = client.get(f'/api/v1/chainsight/watchlist/{path.id}/')
    assert r.status_code == 200
    assert len(r.data['actions']) == 2


@pytest.mark.django_db
def test_archive_action(client, auth_user):
    path = SavedPath.objects.create(path_nodes=['A', 'B'], status='watching', user=auth_user)
    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/archive/')
    assert r.status_code == 200
    assert r.data['status'] == 'archived'
    path.refresh_from_db()
    assert path.status == 'archived'


@pytest.mark.django_db
def test_archive_already_archived(client, auth_user):
    path = SavedPath.objects.create(path_nodes=['A', 'B'], status='archived', user=auth_user)
    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/archive/')
    assert r.status_code == 400


@pytest.mark.django_db
def test_resolve_action(client, auth_user):
    path = SavedPath.objects.create(path_nodes=['A', 'B'], status='watching', user=auth_user)
    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/resolve/')
    assert r.status_code == 200
    assert r.data['status'] == 'resolved'


@pytest.mark.django_db
def test_delete(client, auth_user):
    path = SavedPath.objects.create(path_nodes=['A', 'B'], user=auth_user)
    r = client.delete(f'/api/v1/chainsight/watchlist/{path.id}/')
    assert r.status_code == 204
    assert not SavedPath.objects.filter(id=path.id).exists()
