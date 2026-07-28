"""SectorGraphView 예외 견고성 (⑳-E S4).

Neo4j 연결/쿼리 실패(동결)를 500 누출 대신 503으로 정규화 →
프론트가 isError 로 구분해 "섹터 관계망 이용 불가" 명시 렌더.
"""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from apps.chain_sight.graph.exceptions import GraphConnectionError, GraphQueryError


@pytest.fixture
def auth_client(db, django_user_model):
    u = django_user_model.objects.create_user(username="sector_u", password="x")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.parametrize("exc", [GraphQueryError, GraphConnectionError])
@patch("apps.chain_sight.api.views.get_graph_repository")
def test_sector_graph_neo4j_failure_returns_503_not_500(mock_get_repo, exc, auth_client):
    """Neo4j 다운(GraphQueryError·GraphConnectionError) → 503(서비스 불가), 500 누출 금지."""
    mock_repo = MagicMock()
    mock_repo.run_query.side_effect = exc("Couldn't connect to localhost:7687")
    mock_get_repo.return_value = mock_repo

    resp = auth_client.get("/api/v1/chainsight/sector/Technology/graph/")

    assert resp.status_code == 503, f"{exc.__name__} 미포착 → {resp.status_code} 누출"
    body = resp.json()
    assert body.get("code") == "graph_unavailable"
