from lab_automation.contracts import (
    ApprovalRecord,
    ApprovalStatus,
    CandidateRevision,
    Lab,
    PromotionStage,
    can_promote,
)


def approval(stage, sha="abc123", status=ApprovalStatus.APPROVED):
    return ApprovalRecord(
        job_id="SV-JOB-1",
        stage=stage,
        revision_sha=sha,
        status=status,
        approved_by="ceo",
    )


def test_push_approval_applies_only_to_exact_sha():
    record = approval(PromotionStage.PUSH)
    assert can_promote(PromotionStage.PUSH, record, "abc123")
    assert not can_promote(PromotionStage.PUSH, record, "def456")


def test_push_approval_does_not_authorize_merge():
    record = approval(PromotionStage.PUSH)
    assert not can_promote(PromotionStage.MERGE, record, "abc123")


def test_merge_approval_does_not_authorize_deploy():
    record = approval(PromotionStage.MERGE)
    assert not can_promote(PromotionStage.DEPLOY, record, "abc123")


def test_rejected_approval_cannot_promote():
    record = approval(PromotionStage.PUSH, status=ApprovalStatus.REJECTED)
    assert not can_promote(PromotionStage.PUSH, record, "abc123")


def test_candidate_revision_is_lab_agnostic():
    revision = CandidateRevision(
        job_id="SV-JOB-1",
        revision_sha="abc123",
        test_summary="8 passed",
        changed_paths=("math_lab/runtime/data_eligibility.py",),
        risk_summary="low",
        result_manifest_path="lab_automation/runs/SV-JOB-1/result.yaml",
    )
    assert revision.revision_sha == "abc123"
    assert Lab.MATH.value == "math_lab"
