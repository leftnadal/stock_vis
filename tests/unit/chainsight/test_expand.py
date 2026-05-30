import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from chainsight.models import PathAction, SavedPath
from chainsight.services.expand_service import (
    _compute_expansion_score,
    find_expansion_candidates,
)

User = get_user_model()


@pytest.fixture
def user(db):
    # security audit P0 #2 (2026-05-19): WatchlistViewSet IsAuthenticated 강제.
    return User.objects.create_user(
        username=f'exp_{uuid.uuid4().hex[:8]}', password='test1234'
    )


@pytest.fixture
def client(user):
    api = APIClient()
    api.force_authenticate(user=user)
    return api


def test_expansion_score_truth_weight():
    high = _compute_expansion_score(truth_score=85, heat_score=0.5, rel_type='PEER_OF', relation_count=1)
    low = _compute_expansion_score(truth_score=35, heat_score=0.5, rel_type='PEER_OF', relation_count=1)
    assert high > low


def test_expansion_score_relation_priority():
    supply = _compute_expansion_score(truth_score=60, heat_score=0.5, rel_type='SUPPLIES_TO', relation_count=1)
    peer = _compute_expansion_score(truth_score=60, heat_score=0.5, rel_type='PEER_OF', relation_count=1)
    assert supply > peer


@pytest.mark.django_db
@patch('chainsight.services.expand_service.get_graph_repository')
def test_find_candidates_mock(mock_get_repo):
    mock_repo = MagicMock()
    mock_repo.run_query.return_value = [
        {
            'ticker': 'AMAT', 'name': 'Applied Materials',
            'sector': 'Technology', 'heat_score': 0.7,
            'primary_relation': {
                'rel_type': 'SUPPLIES_TO', 'truth_score': 85,
                'status': 'confirmed', 'basis_summary': '공시 확인',
            },
            'relation_count': 2,
        },
    ]
    mock_get_repo.return_value = mock_repo

    result = find_expansion_candidates(
        source_ticker='ASML', excluded_tickers=['NVDA', 'TSM', 'ASML'], limit=10,
    )
    assert result['source_ticker'] == 'ASML'
    assert len(result['candidates']) == 1
    assert result['candidates'][0]['ticker'] == 'AMAT'
    assert '_score' not in result['candidates'][0]


@pytest.mark.django_db
@patch('chainsight.views.watchlist_views.find_expansion_candidates')
def test_expand_api_success(mock_find, client, user):
    path = SavedPath.objects.create(user=user, path_nodes=['NVDA', 'TSM', 'ASML'])
    mock_find.return_value = {
        'source_ticker': 'ASML',
        'candidates': [{'ticker': 'AMAT', 'name': 'AMAT', 'sector': 'Tech'}],
        'total_found': 5,
    }
    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/expand/')
    assert r.status_code == 200
    assert r.data['source_ticker'] == 'ASML'
    actions = path.actions.filter(action_type='expand')
    assert actions.count() == 1
    assert actions.first().metadata['target_ticker'] == 'ASML'


@pytest.mark.django_db
def test_expand_invalid_target(client, user):
    path = SavedPath.objects.create(user=user, path_nodes=['NVDA', 'TSM'])
    r = client.post(
        f'/api/v1/chainsight/watchlist/{path.id}/expand/',
        {'target_ticker': 'UNKNOWN'}, format='json',
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_expand_archived_rejected(client, user):
    path = SavedPath.objects.create(user=user, path_nodes=['A', 'B'], status='archived')
    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/expand/')
    assert r.status_code == 400
