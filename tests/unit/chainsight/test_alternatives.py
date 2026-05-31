import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.chain_sight.models import PathAction, SavedPath
from apps.chain_sight.services.alternatives_service import find_alternatives

User = get_user_model()


@pytest.fixture
def user(db):
    # security audit P0 #2 (2026-05-19): WatchlistViewSet IsAuthenticated 강제.
    return User.objects.create_user(
        username=f'alt_{uuid.uuid4().hex[:8]}', password='test1234'
    )


@pytest.fixture
def client(user):
    api = APIClient()
    api.force_authenticate(user=user)
    return api


@pytest.mark.django_db
@patch('apps.chain_sight.services.alternatives_service.get_graph_repository')
def test_find_alternatives_middle_node(mock_get_repo):
    mock_repo = MagicMock()
    mock_repo.run_query.side_effect = [
        [{'rel_type': 'SUPPLIES_TO', 'truth_score': 85, 'status': 'confirmed'}],
        [{'rel_type': 'COMPETES_WITH', 'truth_score': 60, 'status': 'probable'}],
        [{'ticker': 'KLAC', 'name': 'KLA', 'sector': 'Tech', 'industry': 'Semi',
          'heat_score': 0.6, 'overlap': 2,
          'rel_before': {'rel_type': 'SUPPLIES_TO', 'truth_score': 80, 'status': 'probable'},
          'rel_after': {'rel_type': 'COMPETES_WITH', 'truth_score': 55, 'status': 'probable'}}],
    ]
    mock_get_repo.return_value = mock_repo

    result = find_alternatives(
        path_nodes=['NVDA', 'TSM', 'AMAT', 'LRCX'],
        target_ticker='AMAT', limit=10,
    )
    assert result['target_ticker'] == 'AMAT'
    assert result['neighbor_constraints']['before']['ticker'] == 'TSM'
    assert result['neighbor_constraints']['after']['ticker'] == 'LRCX'
    assert len(result['alternatives']) == 1
    assert result['alternatives'][0]['overlap_count'] == 2


@pytest.mark.django_db
@patch('apps.chain_sight.services.alternatives_service.get_graph_repository')
def test_find_alternatives_start_node(mock_get_repo):
    mock_repo = MagicMock()
    mock_repo.run_query.side_effect = [
        [{'rel_type': 'SUPPLIES_TO', 'truth_score': 85, 'status': 'confirmed'}],
        [{'ticker': 'AAPL', 'name': 'Apple', 'sector': 'Tech', 'industry': 'Consumer',
          'heat_score': 0.5, 'truth_score': 80, 'status': 'probable'}],
    ]
    mock_get_repo.return_value = mock_repo

    result = find_alternatives(path_nodes=['NVDA', 'TSM'], target_ticker='NVDA', limit=10)
    assert result['neighbor_constraints']['before'] is None
    assert result['neighbor_constraints']['after']['ticker'] == 'TSM'
    assert len(result['alternatives']) == 1
    assert result['alternatives'][0]['overlap_count'] == 1


def test_find_alternatives_target_not_in_path():
    with pytest.raises(ValueError):
        find_alternatives(path_nodes=['A', 'B', 'C'], target_ticker='XYZ')


@pytest.mark.django_db
@patch('apps.chain_sight.views.watchlist_views.find_alternatives')
def test_alternatives_api_success(mock_find, client, user):
    path = SavedPath.objects.create(user=user, path_nodes=['NVDA', 'TSM', 'AMAT', 'LRCX'])
    mock_find.return_value = {
        'target_ticker': 'AMAT',
        'neighbor_constraints': {
            'before': {'ticker': 'TSM', 'relation_type': 'SUPPLIES_TO'},
            'after': {'ticker': 'LRCX', 'relation_type': 'COMPETES_WITH'},
        },
        'alternatives': [{'ticker': 'KLAC', 'name': 'KLA', 'sector': 'Tech',
                          'industry': 'Semi', 'overlap_count': 2}],
        'total_found': 1,
    }
    r = client.post(
        f'/api/v1/chainsight/watchlist/{path.id}/alternatives/',
        {'target_ticker': 'AMAT'}, format='json',
    )
    assert r.status_code == 200
    assert r.data['target_ticker'] == 'AMAT'
    actions = path.actions.filter(action_type='alternatives')
    assert actions.count() == 1
    assert actions.first().metadata['target_ticker'] == 'AMAT'


@pytest.mark.django_db
def test_alternatives_missing_target(client, user):
    path = SavedPath.objects.create(user=user, path_nodes=['A', 'B'])
    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/alternatives/', {}, format='json')
    assert r.status_code == 400


@pytest.mark.django_db
def test_alternatives_target_not_in_path(client, user):
    path = SavedPath.objects.create(user=user, path_nodes=['A', 'B'])
    r = client.post(
        f'/api/v1/chainsight/watchlist/{path.id}/alternatives/',
        {'target_ticker': 'XYZ'}, format='json',
    )
    assert r.status_code == 400
