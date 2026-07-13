"""가설 마감 서비스·엔드포인트 검증 (MON-CLOSE-UI Phase 1 §6)."""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from apps.monitor.models import (
    Claim,
    ClaimIndicatorResult,
    ClosureSnapshot,
    Monitor,
    MonitorSnapshot,
)
from apps.monitor.services import closure

User = get_user_model()


# ── §4 propose_verdict 밴드 경계 ──────────────────────────────────────────


class TestProposeVerdict:
    def test_high_band_validated(self):
        assert closure.propose_verdict(0.333) == Claim.ProposedVerdict.VALIDATED
        assert closure.propose_verdict(1.0) == Claim.ProposedVerdict.VALIDATED

    def test_low_band_invalidated(self):
        assert closure.propose_verdict(-0.333) == Claim.ProposedVerdict.INVALIDATED
        assert closure.propose_verdict(-1.0) == Claim.ProposedVerdict.INVALIDATED

    def test_mid_band_partial(self):
        assert closure.propose_verdict(0.0) == Claim.ProposedVerdict.PARTIAL
        assert closure.propose_verdict(0.332) == Claim.ProposedVerdict.PARTIAL
        assert closure.propose_verdict(-0.332) == Claim.ProposedVerdict.PARTIAL

    def test_symmetric_boundaries(self):
        assert closure.VERDICT_HI == -closure.VERDICT_LO  # 대칭·무편향


# ── 픽스처 ──────────────────────────────────────────────────────────────


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="close_alice", password="pw12345")


@pytest.fixture
def monitor_with_indicators(alice):
    m = Monitor.objects.create(
        user=alice, scope="stock", target_ref="AAPL", name="애플", current_state="active"
    )
    i1 = m.indicators.create(name="지표1", indicator_type="market_data", source_key="eod_composite")
    i2 = m.indicators.create(name="지표2", indicator_type="market_data")
    MonitorSnapshot.objects.create(monitor=m, asof_date=date(2026, 7, 10), overall_score=0.5, state="active")
    claim = m.claims.create(assertion="애플 강세 지속")
    return m, claim, i1, i2


# ── close_claim 서비스 ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCloseClaim:
    def test_close_saves_verdict_and_snapshot(self, monitor_with_indicators, alice):
        m, claim, i1, i2 = monitor_with_indicators
        closed = closure.close_claim(
            claim, final_verdict=Claim.Outcome.VALIDATED,
            factor_tags=[Claim.FactorTag.TIMING], retro_memo="좋았다",
            indicator_results=[{"indicator_id": str(i1.id), "result": "hit"},
                               {"indicator_id": str(i2.id), "result": "miss"}],
            user=alice,
        )
        closed.refresh_from_db()
        assert closed.outcome == Claim.Outcome.VALIDATED
        assert closed.proposed_verdict == Claim.ProposedVerdict.VALIDATED  # score 0.5 ≥ 0.333
        assert closed.resolved_by_id == alice.id
        assert closed.resolved_at is not None
        assert closed.status == Claim.Status.RESOLVED
        assert closed.factor_tags == [Claim.FactorTag.TIMING]
        # 지표별 결과 2건
        assert ClaimIndicatorResult.objects.filter(claim=closed).count() == 2
        # 동결 스냅샷 1건, overall_score 동결
        snap = ClosureSnapshot.objects.get(claim=closed)
        assert snap.overall_score == 0.5
        assert "sparkline" in snap.payload and "indicators" in snap.payload

    def test_proposed_vs_final_delta(self, monitor_with_indicators, alice):
        # 제안 VALIDATED(0.5)인데 사용자가 PARTIAL로 확정 → 델타 보존
        m, claim, i1, i2 = monitor_with_indicators
        closed = closure.close_claim(claim, final_verdict=Claim.Outcome.PARTIAL, user=alice)
        assert closed.proposed_verdict == Claim.ProposedVerdict.VALIDATED
        assert closed.outcome == Claim.Outcome.PARTIAL

    def test_reclose_guard(self, monitor_with_indicators, alice):
        m, claim, i1, i2 = monitor_with_indicators
        closure.close_claim(claim, final_verdict=Claim.Outcome.VALIDATED, user=alice)
        with pytest.raises(closure.AlreadyClosedError):
            closure.close_claim(claim, final_verdict=Claim.Outcome.INVALIDATED, user=alice)

    def test_invalid_final_verdict_rejected(self, monitor_with_indicators, alice):
        m, claim, i1, i2 = monitor_with_indicators
        for bad in [Claim.Outcome.PENDING, Claim.Outcome.INCONCLUSIVE, "nonsense"]:
            with pytest.raises(closure.ClosureValidationError):
                closure.close_claim(claim, final_verdict=bad, user=alice)

    def test_foreign_indicator_rejected_and_rolled_back(self, monitor_with_indicators, alice):
        m, claim, i1, i2 = monitor_with_indicators
        # 다른 모니터의 지표
        other_m = Monitor.objects.create(user=alice, scope="stock", target_ref="MSFT", name="MS")
        other_i = other_m.indicators.create(name="x", indicator_type="market_data")
        with pytest.raises(closure.ClosureValidationError):
            closure.close_claim(
                claim, final_verdict=Claim.Outcome.VALIDATED,
                indicator_results=[{"indicator_id": str(other_i.id), "result": "hit"}], user=alice,
            )
        claim.refresh_from_db()
        # 원자성: 롤백되어 마감 안 됨
        assert claim.outcome == Claim.Outcome.PENDING
        assert ClosureSnapshot.objects.filter(claim=claim).count() == 0
        assert ClaimIndicatorResult.objects.filter(claim=claim).count() == 0

    def test_bad_factor_tag_rejected(self, monitor_with_indicators, alice):
        m, claim, i1, i2 = monitor_with_indicators
        with pytest.raises(closure.ClosureValidationError):
            closure.close_claim(claim, final_verdict=Claim.Outcome.VALIDATED,
                                factor_tags=["not_a_tag"], user=alice)


# ── 모델 제약 ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestClosureModels:
    def test_claim_indicator_result_unique(self, monitor_with_indicators, alice):
        m, claim, i1, i2 = monitor_with_indicators
        ClaimIndicatorResult.objects.create(claim=claim, indicator=i1, result="hit")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ClaimIndicatorResult.objects.create(claim=claim, indicator=i1, result="miss")

    def test_closure_snapshot_one_per_claim(self, monitor_with_indicators, alice):
        m, claim, i1, i2 = monitor_with_indicators
        ClosureSnapshot.objects.create(claim=claim, overall_score=0.5, payload={})
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ClosureSnapshot.objects.create(claim=claim, overall_score=0.3, payload={})


# ── 엔드포인트 (owner-scoping + 409) ───────────────────────────────────────


@pytest.mark.django_db
class TestCloseAPI:
    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_close_preview(self, monitor_with_indicators, alice):
        m, claim, i1, i2 = monitor_with_indicators
        resp = self._client(alice).get(f"/api/v1/monitor/claims/{claim.id}/close-preview/")
        assert resp.status_code == 200
        assert resp.data["proposed_verdict"] == "validated"  # score 0.5
        assert resp.data["overall_score"] == 0.5
        assert len(resp.data["indicators"]) == 2

    def test_close_endpoint(self, monitor_with_indicators, alice):
        m, claim, i1, i2 = monitor_with_indicators
        resp = self._client(alice).post(
            f"/api/v1/monitor/claims/{claim.id}/close/",
            {"final_verdict": "partial", "factor_tags": ["luck"],
             "indicator_results": [{"indicator_id": str(i1.id), "result": "hit"}]},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        assert resp.data["outcome"] == "partial"
        assert resp.data["proposed_verdict"] == "validated"

    def test_reclose_409(self, monitor_with_indicators, alice):
        m, claim, i1, i2 = monitor_with_indicators
        c = self._client(alice)
        c.post(f"/api/v1/monitor/claims/{claim.id}/close/", {"final_verdict": "validated"}, format="json")
        resp = c.post(f"/api/v1/monitor/claims/{claim.id}/close/", {"final_verdict": "invalidated"}, format="json")
        assert resp.status_code == 409

    def test_close_other_user_404(self, monitor_with_indicators, alice):
        m, claim, i1, i2 = monitor_with_indicators
        bob = User.objects.create_user(username="close_bob", password="pw12345")
        resp = self._client(bob).post(
            f"/api/v1/monitor/claims/{claim.id}/close/", {"final_verdict": "validated"}, format="json"
        )
        assert resp.status_code == 404  # owner 스코프 격리
