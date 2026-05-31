"""Slice 16 Step 0-B — coach endpoint 테스트 공통 fixture.

배경: #70 (Slice 15 closing 등록)에 따라 coach e1~e6 view를 IsAuthenticated로
전환했다. 6 endpoint 테스트 파일 모두에 동일한 인증 패턴이 필요해 conftest로 통합.

`api_client` fixture는 force_authenticate가 적용된 APIClient를 반환한다.
User는 DB에 저장하지 않은 in-memory instance — DRF force_authenticate는 객체만
attach하므로 DB 부담 0.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def coach_test_user():
    """force_authenticate에 사용할 가벼운 User 인스턴스.

    DB 저장 불요 — DRF force_authenticate는 객체 attach만 수행, 권한 검증은
    `request.user.is_authenticated`만 확인.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User(pk=1, username="coach-test-user")


@pytest.fixture
def api_client(coach_test_user):
    """6 coach endpoint 테스트 공통 — IsAuthenticated 통과한 APIClient."""
    client = APIClient()
    client.force_authenticate(user=coach_test_user)
    return client


@pytest.fixture
def anonymous_api_client():
    """미인증 APIClient — auth wall 검증 전용."""
    return APIClient()
