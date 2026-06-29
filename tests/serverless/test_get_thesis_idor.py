"""
get_thesis IDOR-read 수정 테스트 (전수조사 SEAM-DEBT #1).

InvestmentThesis는 is_public/share_code 공유 기능을 가진다.
→ 비공개 테제는 소유자만, 공개 테제는 누구나(공유 보존).
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from services.serverless.models import InvestmentThesis

User = get_user_model()


def _url(thesis_id):
    return f"/api/v1/serverless/thesis/{thesis_id}"


def _mk_thesis(owner, is_public=False):
    return InvestmentThesis.objects.create(
        user=owner,
        title="비밀 투자 논리",
        summary="요약",
        is_public=is_public,
    )


@pytest.mark.django_db
class TestGetThesisIDOR:
    def setup_method(self):
        self.owner = User.objects.create_user(username="owner", password="x")
        self.other = User.objects.create_user(username="other", password="x")
        self.client = APIClient()

    def test_owner_reads_own_private_thesis(self):
        thesis = _mk_thesis(self.owner, is_public=False)
        self.client.force_authenticate(self.owner)
        resp = self.client.get(_url(thesis.id))
        assert resp.status_code == 200
        assert resp.data["title"] == "비밀 투자 논리"

    def test_non_owner_gets_404_on_private(self):
        """IDOR 차단: 타인의 비공개 테제 → 404(존재 비노출)."""
        thesis = _mk_thesis(self.owner, is_public=False)
        self.client.force_authenticate(self.other)
        resp = self.client.get(_url(thesis.id))
        assert resp.status_code == 404

    def test_anonymous_gets_404_on_private(self):
        thesis = _mk_thesis(self.owner, is_public=False)
        resp = self.client.get(_url(thesis.id))  # 미인증
        assert resp.status_code == 404

    def test_public_thesis_readable_by_anyone(self):
        """공유 보존: 공개 테제는 타인/미인증도 조회 가능."""
        thesis = _mk_thesis(self.owner, is_public=True)
        resp = self.client.get(_url(thesis.id))  # 미인증
        assert resp.status_code == 200
