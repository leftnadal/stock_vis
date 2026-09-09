"""Positive-side observation is neither sufficiency nor research permission."""

import json

import pytest

from math_lab.runtime.daily_price_readiness import (
    build_unavailable_artifacts, run_readiness_probe, write_artifacts,
)
from math_lab.runtime.test_daily_price_readiness import _context, _fixture_session
from math_lab.runtime.test_daily_price_boundaries import _mutate_fixture


@pytest.mark.parametrize("rows", [0, 1, 3, 30])
def test_row_count_does_not_establish_sufficiency_or_permission(rows, tmp_path):
    session = _fixture_session()
    inserts = "".join(
        "INSERT INTO stocks_daily_price "
        "(stock_id,currency,date,open_price,high_price,low_price,close_price,volume) "
        f"VALUES ('AAPL','USD','2026-08-{day:02d}',100,110,90,105,100);"
        for day in range(1, rows + 1)
    )
    _mutate_fixture(session, "DELETE FROM stocks_daily_price;" + inserts)
    artifacts = run_readiness_probe(session, _context())
    result = artifacts.result
    aapl = next(x for x in result["findings"]["representative_basket"] if x["symbol"] == "AAPL")
    assert aapl["daily_price_row_count"] == rows
    assert aapl["observed_content_status"] == (
        "nonfatal_observed" if rows else "no_price_rows_observed"
    )
    assert aapl["research_input_sufficiency"] == "unassessed"
    assert result["inventory_permission"]["status"] == "permitted_read_only"
    for decision in result["findings"]["data_eligibility_decisions"]:
        assert decision["research_input_sufficiency"] == "unassessed"
        assert decision["research_input_permitted"] is False
        assert decision["permitted_symbols"] == []
        assert "research_input_sufficiency_unassessed" in decision["reasons"]
        assert "usable_for_exploration_but_not_confirmation" not in decision["reasons"]
        assert decision["eligibility"] == (
            "exploratory_only" if rows and decision["intended_use"] == "exploratory"
            else "prohibited_for_declared_use"
        )
    write_artifacts(artifacts, result_path=tmp_path / "result.json",
                    data_gaps_path=tmp_path / "gaps.json", report_path=tmp_path / "report.md")
    assert json.loads((tmp_path / "result.json").read_text()) == result
    report = (tmp_path / "report.md").read_text()
    assert "Eligibility (not permission)" in report
    assert "unassessed" in report


def test_late_failure_preserves_observed_content_without_assessing_sufficiency():
    delegate = _fixture_session()
    _mutate_fixture(delegate, "UPDATE stocks_daily_price SET open_price=105,close_price=105 WHERE id=3;")

    class Failing:
        vendor = delegate.vendor
        read_only_verified = True
        read_only_evidence = delegate.read_only_evidence

        def fetch_all(self, statement, params=()):
            if "FROM stocks_stock AS s" in statement:
                raise TimeoutError("synthetic late failure")
            return delegate.fetch_all(statement, params)

    result = run_readiness_probe(Failing(), _context()).result
    assert result["probe"]["database_status"] == "query_failed"
    for decision in result["findings"]["data_eligibility_decisions"]:
        assert decision["observed_content_status"] == "nonfatal_observed"
        assert decision["research_input_sufficiency"] == "unassessed"
        assert decision["research_input_permitted"] is False
        assert decision["eligibility"] == "prohibited_for_declared_use"
        assert "incomplete_snapshot" in decision["reasons"]


def test_unobserved_content_is_not_a_negative_quality_observation():
    result = build_unavailable_artifacts(
        _context(), error_type="OperationalError", error_message="unavailable"
    ).result
    for row in result["findings"]["representative_basket"]:
        assert row["observed_content_status"] == "not_observed"
        assert row["research_input_sufficiency"] == "unassessed"
    for decision in result["findings"]["data_eligibility_decisions"]:
        assert decision["observed_content_status"] == "not_observed"
        assert not decision["research_input_permitted"]
