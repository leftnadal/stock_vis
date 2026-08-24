"""Playbook API contract 테스트 (1.6-S1).

빈 test DB에서도 200 + 봉투 + 8체인(전 pending) 계약 유지(오판정 렌더 금지의 BE측 보증).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="pb", email="pb@e.com", password="pw")
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _url():
    return reverse("marketpulse_api_v2:playbook")


@pytest.mark.django_db
class TestPlaybookApi:
    def test_200_and_envelope(self, auth_client):
        resp = auth_client.get(_url())
        assert resp.status_code == 200
        body = resp.json()
        assert "_meta" in body and "data" in body

    def test_8_chains_and_summary_contract(self, auth_client):
        data = auth_client.get(_url()).json()["data"]
        assert len(data["chains"]) == 8
        for ch in data["chains"]:
            assert set(ch) >= {"id", "name", "narrative", "cadence", "lit_count", "total", "state", "data_as_of"}
            assert ch["state"] in {"dormant", "partial", "active", "pending"}
        assert set(data["summary"]) >= {"total", "total_lit", "top_chain"}

    def test_empty_db_all_pending_no_false_lit(self, auth_client):
        # 빈 DB = 신호 전 부재 → 전 체인 pending, 오점등 0(오판정 렌더 금지)
        data = auth_client.get(_url()).json()["data"]
        assert all(ch["state"] == "pending" for ch in data["chains"])
        assert data["summary"]["total_lit"] == 0

    def test_requires_auth(self):
        resp = APIClient().get(_url())
        assert resp.status_code in (401, 403)
