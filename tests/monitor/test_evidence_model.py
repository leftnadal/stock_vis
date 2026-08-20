"""ClaimEvidence 모델 검증 (RECON-SWAP-0813 PART 1)."""
import pytest
from django.core.exceptions import ValidationError

from apps.monitor.models import Claim, ClaimEvidence


@pytest.fixture
def claim(monitor):
    return Claim.objects.create(monitor=monitor, assertion="애플 강세 지속")


@pytest.mark.django_db
class TestClaimEvidenceModel:
    def test_auto_kind_full_construct(self, claim, make_indicator):
        ind = make_indicator(name="12-1 모멘텀")
        ev = ClaimEvidence.objects.create(
            claim=claim,
            kind=ClaimEvidence.Kind.AUTO,
            indicator=ind,
            operator=ClaimEvidence.Operator.GTE,
            threshold=0.3,
            grace_days=10,
        )
        ev.full_clean()  # 통과해야 함
        assert ev.kind == ClaimEvidence.Kind.AUTO
        assert ev.indicator_id == ind.id
        assert ev.grace_days == 10
        assert claim.evidences.count() == 1

    def test_manual_kind_full_construct(self, claim):
        ev = ClaimEvidence.objects.create(
            claim=claim,
            kind=ClaimEvidence.Kind.MANUAL,
            description="AI 인프라 테마 열기 지속",
            recheck_period_days=90,
        )
        ev.full_clean()  # 통과해야 함
        assert ev.kind == ClaimEvidence.Kind.MANUAL
        assert ev.recheck_period_days == 90
        assert claim.evidences.count() == 1

    def test_auto_missing_indicator_raises(self, claim):
        ev = ClaimEvidence(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            operator=ClaimEvidence.Operator.GTE, threshold=0.3,
        )
        with pytest.raises(ValidationError):
            ev.clean()

    def test_auto_missing_operator_raises(self, claim, make_indicator):
        ind = make_indicator()
        ev = ClaimEvidence(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, threshold=0.3,
        )
        with pytest.raises(ValidationError):
            ev.clean()

    def test_auto_missing_threshold_raises(self, claim, make_indicator):
        ind = make_indicator()
        ev = ClaimEvidence(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE,
        )
        with pytest.raises(ValidationError):
            ev.clean()

    def test_manual_missing_description_raises(self, claim):
        ev = ClaimEvidence(claim=claim, kind=ClaimEvidence.Kind.MANUAL)
        with pytest.raises(ValidationError):
            ev.clean()

    def test_indicator_delete_sets_null_preserves_evidence(self, claim, make_indicator):
        # SET_NULL 관례(Claim.resolved_by와 동일) — 지표 삭제 후에도 근거 행 보존.
        ind = make_indicator()
        ev = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE, threshold=0.3,
        )
        ind.delete()
        ev.refresh_from_db()
        assert ev.indicator_id is None

    def test_claim_delete_cascades_evidence(self, claim):
        ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.MANUAL, description="근거"
        )
        claim.delete()
        assert ClaimEvidence.objects.count() == 0
