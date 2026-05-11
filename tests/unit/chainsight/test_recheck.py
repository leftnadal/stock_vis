import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from rest_framework.test import APIClient

from chainsight.models import SavedPath, PathAction
from chainsight.services.recheck_service import (
    run_recheck,
    _classify_edge_change,
    _build_headline,
    _decide_suggestion,
    RecheckResult,
)


@pytest.fixture
def client():
    return APIClient()


# --- _classify_edge_change ---


def test_classify_strengthened_by_status():
    assert _classify_edge_change(
        {'status': 'weak', 'truth_score': 35},
        {'status': 'probable', 'truth_score': 60}
    ) == 'strengthened'


def test_classify_weakened_by_status():
    assert _classify_edge_change(
        {'status': 'confirmed', 'truth_score': 85},
        {'status': 'probable', 'truth_score': 60}
    ) == 'weakened'


def test_classify_broken():
    assert _classify_edge_change(
        {'status': 'confirmed', 'truth_score': 85},
        {'status': 'stale', 'truth_score': None}
    ) == 'broken'


def test_classify_unchanged():
    assert _classify_edge_change(
        {'status': 'probable', 'truth_score': 60},
        {'status': 'probable', 'truth_score': 61}
    ) == 'unchanged'


def test_classify_score_delta_strengthened():
    assert _classify_edge_change(
        {'status': 'probable', 'truth_score': 55},
        {'status': 'probable', 'truth_score': 70}
    ) == 'strengthened'


# --- _build_headline ---


def test_headline_all_unchanged():
    r = RecheckResult(unchanged=[{}, {}, {}])
    assert '큰 변화 없음' in _build_headline(r)


def test_headline_strengthened_only():
    r = RecheckResult(strengthened=[{}, {}])
    assert '2개 구간 강화' in _build_headline(r)


def test_headline_broken():
    r = RecheckResult(broken_edges=[{}])
    assert '끊김' in _build_headline(r)


def test_headline_mixed():
    r = RecheckResult(strengthened=[{}, {}], weakened=[{}])
    h = _build_headline(r)
    assert '↑' in h or '강화' in h


# --- _decide_suggestion ---


@pytest.mark.django_db
def test_suggestion_all_broken():
    path = SavedPath.objects.create(path_nodes=['A', 'B'])
    r = RecheckResult(broken_edges=[{}, {}])
    action, _ = _decide_suggestion(r, path)
    assert action == 'resolve'


@pytest.mark.django_db
def test_suggestion_some_broken():
    path = SavedPath.objects.create(path_nodes=['A', 'B', 'C'])
    r = RecheckResult(broken_edges=[{'from': 'A', 'to': 'B'}], unchanged=[{}])
    action, _ = _decide_suggestion(r, path)
    assert action == 'alternatives'


@pytest.mark.django_db
def test_suggestion_strengthened():
    path = SavedPath.objects.create(path_nodes=['A', 'B'])
    r = RecheckResult(strengthened=[{}, {}])
    action, _ = _decide_suggestion(r, path)
    assert action == 'expand'


@pytest.mark.django_db
def test_suggestion_repeated_weak_archive():
    path = SavedPath.objects.create(path_nodes=['A', 'B'], recheck_count=3)
    r = RecheckResult(weakened=[{}])
    action, _ = _decide_suggestion(r, path)
    assert action == 'archive'


# --- run_recheck integration ---


@pytest.mark.django_db
@patch('chainsight.services.recheck_service._fetch_current_snapshot')
def test_run_recheck_basic_flow(mock_fetch):
    old_snapshot = [{'from': 'NVDA', 'to': 'TSM', 'type': 'SUPPLIES_TO', 'truth_score': 60, 'status': 'probable'}]
    new_snapshot = [{'from': 'NVDA', 'to': 'TSM', 'type': 'SUPPLIES_TO', 'truth_score': 85, 'status': 'confirmed'}]
    mock_fetch.return_value = new_snapshot

    path = SavedPath.objects.create(
        path_nodes=['NVDA', 'TSM'],
        edge_snapshot=old_snapshot,
        why_now_snapshot={'headline': '초기', 'signals': []},
    )
    result = run_recheck(path)

    assert len(result.strengthened) == 1
    assert result.path_intact is True
    assert result.suggested_action == 'expand'
    assert '강화' in result.headline

    path.refresh_from_db()
    assert path.edge_snapshot == new_snapshot
    assert path.recheck_count == 1
    assert path.actions.filter(action_type='recheck').count() == 1


@pytest.mark.django_db
@patch('chainsight.services.recheck_service._fetch_current_snapshot')
def test_watching_to_active_transition(mock_fetch):
    mock_fetch.return_value = [{'from': 'A', 'to': 'B', 'type': 'PEER_OF', 'truth_score': 60, 'status': 'probable'}]
    path = SavedPath.objects.create(
        path_nodes=['A', 'B'],
        edge_snapshot=[{'from': 'A', 'to': 'B', 'type': 'PEER_OF', 'truth_score': 60, 'status': 'probable'}],
        recheck_count=1,
    )
    SavedPath.objects.filter(pk=path.pk).update(created_at=timezone.now() - timedelta(hours=25))
    path.refresh_from_db()

    run_recheck(path)
    path.refresh_from_db()
    assert path.status == 'active'
    assert path.recheck_count == 2


@pytest.mark.django_db
@patch('chainsight.services.recheck_service._fetch_current_snapshot')
def test_no_transition_if_too_soon(mock_fetch):
    mock_fetch.return_value = [{'from': 'A', 'to': 'B', 'type': 'PEER_OF', 'truth_score': 60, 'status': 'probable'}]
    path = SavedPath.objects.create(
        path_nodes=['A', 'B'],
        edge_snapshot=[{'from': 'A', 'to': 'B', 'type': 'PEER_OF', 'truth_score': 60, 'status': 'probable'}],
        recheck_count=1,
    )
    run_recheck(path)
    path.refresh_from_db()
    assert path.status == 'watching'


# --- API tests ---


@pytest.mark.django_db
def test_recheck_api_archived_rejected(client):
    path = SavedPath.objects.create(path_nodes=['A', 'B'], status='archived')
    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/recheck/')
    assert r.status_code == 400


@pytest.mark.django_db
@patch('chainsight.services.recheck_service._fetch_current_snapshot')
def test_recheck_api_full_response(mock_fetch, client):
    mock_fetch.return_value = [{'from': 'A', 'to': 'B', 'type': 'PEER_OF', 'truth_score': 85, 'status': 'confirmed'}]
    path = SavedPath.objects.create(
        path_nodes=['A', 'B'],
        edge_snapshot=[{'from': 'A', 'to': 'B', 'type': 'PEER_OF', 'truth_score': 60, 'status': 'probable'}],
    )
    r = client.post(f'/api/v1/chainsight/watchlist/{path.id}/recheck/')
    assert r.status_code == 200
    for f in ['headline', 'strengthened', 'weakened', 'unchanged', 'broken_edges',
              'path_intact', 'suggested_action', 'suggested_reason', 'updated_why_now',
              'status', 'recheck_count']:
        assert f in r.data
    assert r.data['recheck_count'] == 1
