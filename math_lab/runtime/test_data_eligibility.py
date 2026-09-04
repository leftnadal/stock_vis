from math_lab.runtime.data_eligibility import (
    AvailabilityConfidence,
    DataViewContract,
    Eligibility,
    IntendedUse,
    evaluate_data_view,
)


def view(**overrides):
    values = dict(
        data_view_id="dv-1",
        source_system="stock_vis",
        intended_use=IntendedUse.CONFIRMATORY,
        availability_confidence=AvailabilityConfidence.EXACT,
        point_in_time_reconstructable=True,
        content_fingerprint="sha256:abc",
        extraction_version="git:123",
        revision_lineage_available=True,
    )
    values.update(overrides)
    return DataViewContract(**values)


def test_clean_confirmatory_view_is_safe():
    decision = evaluate_data_view(view())
    assert decision.eligibility is Eligibility.CONFIRMATORY_SAFE
    assert decision.allowed


def test_unknown_availability_blocks_confirmation():
    decision = evaluate_data_view(
        view(availability_confidence=AvailabilityConfidence.UNKNOWN)
    )
    assert decision.eligibility is Eligibility.PROHIBITED
    assert "sufficient_availability_confidence" in decision.missing_requirements


def test_weak_provenance_can_remain_exploratory():
    decision = evaluate_data_view(
        view(
            intended_use=IntendedUse.EXPLORATORY,
            availability_confidence=AvailabilityConfidence.UNKNOWN,
            point_in_time_reconstructable=False,
            content_fingerprint=None,
            extraction_version=None,
        )
    )
    assert decision.eligibility is Eligibility.EXPLORATORY_ONLY
    assert decision.allowed


def test_future_information_is_never_allowed():
    decision = evaluate_data_view(
        view(intended_use=IntendedUse.EXPLORATORY, future_information_known=True)
    )
    assert decision.eligibility is Eligibility.PROHIBITED
    assert not decision.allowed


def test_known_contamination_is_never_allowed():
    decision = evaluate_data_view(view(known_contamination=True))
    assert decision.eligibility is Eligibility.PROHIBITED


def test_reconstructed_availability_can_support_confirmation():
    decision = evaluate_data_view(
        view(availability_confidence=AvailabilityConfidence.RECONSTRUCTED)
    )
    assert decision.eligibility is Eligibility.CONFIRMATORY_SAFE


def test_missing_fingerprint_blocks_confirmation():
    decision = evaluate_data_view(view(content_fingerprint=None))
    assert decision.eligibility is Eligibility.PROHIBITED
    assert "content_fingerprint" in decision.missing_requirements


def test_missing_extraction_version_blocks_confirmation():
    decision = evaluate_data_view(view(extraction_version=None))
    assert decision.eligibility is Eligibility.PROHIBITED
    assert "extraction_version" in decision.missing_requirements
