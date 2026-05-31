"""Security audit P0 #2 (2026-05-19) — IDOR 회귀 방지 테스트.

WatchlistViewSet은 IsAuthenticated 강제. 익명 요청은 401,
다른 사용자의 SavedPath는 보이지도/지워지지도 않아야 한다.
"""
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.chain_sight.models import SavedPath

User = get_user_model()


def _user(prefix: str):
    return User.objects.create_user(
        username=f'{prefix}_{uuid.uuid4().hex[:8]}',
        password='test1234',
    )


@pytest.mark.django_db
def test_watchlist_anonymous_request_is_unauthorized():
    """익명 요청은 401 — AllowAny 시절 200을 반환하던 회귀."""
    client = APIClient()
    assert client.get('/api/v1/chainsight/watchlist/').status_code == 401
    assert client.post('/api/v1/chainsight/watchlist/', {}, format='json').status_code == 401


@pytest.mark.django_db
def test_watchlist_user_cannot_see_other_users_paths():
    """user A의 SavedPath가 user B의 list에 노출되지 않아야 한다."""
    alice = _user('alice')
    bob = _user('bob')
    SavedPath.objects.create(path_nodes=['A', 'B'], user=alice, status='watching')

    client = APIClient()
    client.force_authenticate(user=bob)
    resp = client.get('/api/v1/chainsight/watchlist/')
    assert resp.status_code == 200
    assert resp.data == []


@pytest.mark.django_db
def test_watchlist_user_cannot_delete_other_users_path():
    """다른 사용자의 SavedPath DELETE는 404 (queryset에 없음)."""
    alice = _user('alice')
    bob = _user('bob')
    path = SavedPath.objects.create(path_nodes=['A', 'B'], user=alice, status='watching')

    client = APIClient()
    client.force_authenticate(user=bob)
    resp = client.delete(f'/api/v1/chainsight/watchlist/{path.id}/')
    assert resp.status_code == 404
    assert SavedPath.objects.filter(id=path.id).exists()
