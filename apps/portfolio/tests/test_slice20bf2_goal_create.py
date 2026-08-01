"""Slice 20b-f2 — 목표(UserGoal) 생성 POST 엔드포인트 (GOAL-CREATE-UI).

POST advisory/knobs/ 생성(중복 409) + PATCH 엄격 유지(회귀, upsert 금지). DECISIONS D-f2-1.
D0 가산 — 기존 GET/PATCH·필드 무변경.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.portfolio.models_my import UserGoal

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="bf2", password="x")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _url():
    return reverse("portfolio_api:advisory_knobs")


# ── 생성 성공 ──


@pytest.mark.django_db
def test_goal_create_success(client, user):
    r = client.post(
        _url(),
        {"target_return_pct": "20", "horizon_months": 12, "risk_tolerance": "moderate"},
        format="json",
    )
    assert r.status_code == 201, r.content
    g = UserGoal.objects.get(user=user)
    assert g.target_return_pct == Decimal("20")
    assert g.horizon_months == 12
    assert g.risk_tolerance == "moderate"
    # 손잡이 5종 기본값(보수)
    assert g.aggressiveness_offset == 0
    assert g.concentration_limit == 30


@pytest.mark.django_db
def test_goal_create_default_risk(client, user):
    r = client.post(_url(), {"target_return_pct": "15", "horizon_months": 24}, format="json")
    assert r.status_code == 201, r.content
    assert UserGoal.objects.get(user=user).risk_tolerance == "moderate"


# ── 중복 409 (생성 단일 경로) ──


@pytest.mark.django_db
def test_goal_create_duplicate_409(client, user):
    UserGoal.objects.create(user=user, target_return_pct=Decimal("10"), horizon_months=12)
    r = client.post(_url(), {"target_return_pct": "20", "horizon_months": 6}, format="json")
    assert r.status_code == 409, r.content
    # 기존 목표 무변경(upsert 아님)
    g = UserGoal.objects.get(user=user)
    assert g.target_return_pct == Decimal("10")
    assert g.horizon_months == 12


# ── 검증 실패 400 ──


@pytest.mark.django_db
def test_goal_create_missing_horizon_400(client):
    r = client.post(_url(), {"target_return_pct": "20"}, format="json")
    assert r.status_code == 400, r.content


@pytest.mark.django_db
def test_goal_create_invalid_knob_400(client, user):
    # 손잡이 범위 밖(aggressiveness_offset 99 > 7) → full_clean 400, 목표 미생성
    r = client.post(
        _url(),
        {"target_return_pct": "20", "horizon_months": 12, "aggressiveness_offset": 99},
        format="json",
    )
    assert r.status_code == 400, r.content
    assert not UserGoal.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_goal_create_requires_auth():
    anon = APIClient()
    r = anon.post(_url(), {"target_return_pct": "20", "horizon_months": 12}, format="json")
    assert r.status_code in (401, 403)


# ── PATCH 엄격 유지 (회귀, D-f2-1) ──


@pytest.mark.django_db
def test_patch_no_goal_still_400_no_upsert(client, user):
    r = client.patch(_url(), {"aggressiveness_offset": 3}, format="json")
    assert r.status_code == 400
    # PATCH는 생성하지 않는다
    assert not UserGoal.objects.filter(user=user).exists()
