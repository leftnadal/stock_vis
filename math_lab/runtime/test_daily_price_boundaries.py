"""CEO-approved F1/F2 counterexamples; no live database or real credentials."""

import json

import pytest

from math_lab.runtime import daily_price_probe as cli
from math_lab.runtime.daily_price_readiness import (
    build_unavailable_artifacts,
    render_markdown_report,
    run_readiness_probe,
    write_artifacts,
)
from math_lab.runtime.error_redaction import redact_error_message
from math_lab.runtime.test_daily_price_readiness import _context, _fixture_session


def _mutate_fixture(session, sql):
    session.connection.execute("PRAGMA query_only=OFF")
    session.connection.executescript(sql)
    session.connection.commit()
    session.connection.execute("PRAGMA query_only=ON")


def _decision(result, use="exploratory"):
    return next(
        row for row in result["findings"]["data_eligibility_decisions"]
        if row["intended_use"] == use
    )


def _assert_no_generic_allowed(value):
    if isinstance(value, dict):
        assert "allowed" not in value
        for item in value.values():
            _assert_no_generic_allowed(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_generic_allowed(item)


@pytest.mark.parametrize("sql", [
    "DELETE FROM stocks_daily_price;",
    # Every representative gets prices and metadata so all six are fatal,
    # rather than conflating fatal issues with absent stocks.
    """
    INSERT OR IGNORE INTO stocks_stock (symbol,sector,industry,currency)
      VALUES ('SPY','ETF','Benchmark','USD'),('XOM','Energy','Oil','USD'),
             ('WMT','Consumer','Retail','USD'),('UNH','Healthcare','Health','USD');
    INSERT INTO stocks_daily_price
      (stock_id,currency,date,open_price,high_price,low_price,close_price,volume)
      SELECT symbol,'USD','2026-09-04',-1,-1,-2,-1,100 FROM stocks_stock;
    """,
])
def test_empty_or_all_fatal_input_does_not_block_diagnosis_but_blocks_research(sql):
    session = _fixture_session()
    _mutate_fixture(session, sql)
    result = run_readiness_probe(session, _context()).result
    assert result["schema_version"] == "daily-price-readiness-result/0.3"
    assert result["inventory_permission"]["status"] == "permitted_read_only"
    assert not result["inventory_permission"]["implies_research_input_eligibility"]
    rows = result["findings"]["representative_basket"]
    assert all(row["selection_status"] == "deferred" for row in rows)
    if not sql.startswith("DELETE"):
        assert all("fatal_ohlcv_anomaly_observed" in row["reason_codes"] for row in rows)
    for use in ("exploratory", "confirmatory", "replication"):
        decision = _decision(result, use)
        assert decision["eligibility"] == "prohibited_for_declared_use"
        assert decision["research_input_permitted"] is False
        assert decision["permitted_symbols"] == []
        assert "no_nonfatal_representative_price_content_observed" in decision["reasons"]
    _assert_no_generic_allowed(result)


def test_original_dirty_fixture_is_no_longer_implicitly_usable():
    result = run_readiness_probe(_fixture_session(), _context()).result
    assert _decision(result)["research_input_permitted"] is False
    assert result["findings"]["representative_basket"][1]["daily_price_row_count"] == 3


def test_nonfatal_fixture_retains_observations_without_input_permission():
    session = _fixture_session()
    _mutate_fixture(session, "UPDATE stocks_daily_price SET open_price=105, close_price=105 WHERE id=3;")
    artifacts = run_readiness_probe(session, _context())
    result = artifacts.result
    decision = _decision(result)
    assert decision["eligibility"] == "exploratory_only"
    assert decision["research_input_permitted"] is False
    assert decision["research_input_sufficiency"] == "unassessed"
    assert decision["observed_content_status"] == "nonfatal_observed"
    assert decision["permitted_symbols"] == []
    assert decision["observed_nonfatal_symbols"] == ["AAPL"]
    assert len(decision["excluded_symbols"]) == 5
    assert decision["content_fingerprint"] is None
    for use in ("confirmatory", "replication"):
        assert not _decision(result, use)["research_input_permitted"]
        assert _decision(result, use)["permitted_symbols"] == []
    report = render_markdown_report(artifacts)
    assert "not research-input permission" in report
    assert "Permitted symbols" in report
    _assert_no_generic_allowed(result)


def test_mixed_basket_retains_nonfatal_observations_without_row_threshold():
    session = _fixture_session()
    _mutate_fixture(session, """
      INSERT INTO stocks_daily_price
        (stock_id,currency,date,open_price,high_price,low_price,close_price,volume)
        VALUES ('JPM','USD','2026-09-04',100,110,90,105,100);
    """)
    result = run_readiness_probe(session, _context()).result
    decision = _decision(result)
    assert decision["permitted_symbols"] == []
    assert decision["observed_nonfatal_symbols"] == ["JPM"]
    assert decision["observed_content_status"] == "mixed_observed"
    assert decision["research_input_sufficiency"] == "unassessed"
    assert decision["research_input_permitted"] is False
    jpm = result["findings"]["representative_basket"][2]
    assert jpm["observed_content_status"] == "nonfatal_observed"
    assert jpm["research_input_sufficiency"] == "unassessed"
    assert next(x for x in decision["excluded_symbols"] if x["symbol"] == "AAPL")[
        "reasons"
    ] == ["fatal_ohlcv_anomaly_observed"]
    assert decision["input_scope"] == "listed_representative_symbols_only"
    assert result["findings"]["representative_basket"][2]["daily_price_row_count"] == 1


def test_unavailable_snapshot_establishes_neither_permission_nor_eligibility():
    result = build_unavailable_artifacts(
        _context(), error_type="OperationalError", error_message="offline"
    ).result
    assert result["inventory_permission"]["status"] == "not_established"
    assert not _decision(result)["research_input_permitted"]
    _assert_no_generic_allowed(result)


@pytest.mark.parametrize("failure_stage", ["connect", "query", "cleanup"])
def test_cli_all_error_paths_redact_synthetic_secrets_in_json_and_markdown(
    tmp_path, monkeypatch, failure_stage
):
    secret = "synthetic-only-credential-4198"
    monkeypatch.setenv("DB_PASSWORD", secret)
    message = f"database operation failed: {secret}"
    delegate = _fixture_session()

    class BrokenQuery:
        vendor = delegate.vendor
        read_only_verified = True
        read_only_evidence = delegate.read_only_evidence

        def fetch_all(self, *_args, **_kwargs):
            raise RuntimeError(message)

    class Session:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            if failure_stage == "connect":
                raise RuntimeError(message)
            return BrokenQuery() if failure_stage == "query" else delegate

        def __exit__(self, *_args):
            if failure_stage == "cleanup":
                raise RuntimeError(message)

    monkeypatch.setattr(cli, "PostgresReadOnlySession", Session)
    result_path, gaps_path, report_path = [tmp_path / x for x in ("result.json", "gaps.json", "report.md")]
    rc = cli.main([
        "--job-id", "synthetic-boundary-test", "--run-id", "synthetic-only",
        "--result-json", str(result_path), "--data-gaps-json", str(gaps_path),
        "--report-md", str(report_path),
    ])
    assert rc == 2
    for path in (result_path, gaps_path, report_path):
        assert secret not in path.read_text()
    assert "[REDACTED]" in result_path.read_text()
    assert "[REDACTED]" in report_path.read_text()
    result = json.loads(result_path.read_text())
    assert result["failures"]
    assert result["inventory_permission"]["status"] == (
        "not_established" if failure_stage == "connect" else "permitted_read_only"
    )


def test_final_serialization_redacts_late_errors_without_mutating_source_artifacts(tmp_path, monkeypatch):
    secret = "synthetic-late-secret-8192"
    monkeypatch.setenv("PGPASSWORD", secret)
    artifacts = build_unavailable_artifacts(_context(), error_type="Error", error_message="offline")
    artifacts.result["failures"].append({
        "stage": "late", "error_type": "Error", "message": secret,
        "consequence": f"nested synthetic detail {secret}",
    })
    artifacts.data_gaps[0]["errors"] = [{"message": secret}]
    write_artifacts(
        artifacts, result_path=tmp_path / "result.json",
        data_gaps_path=tmp_path / "gaps.json", report_path=tmp_path / "report.md",
    )
    for path in tmp_path.iterdir():
        assert secret not in path.read_text()
    assert secret not in render_markdown_report(artifacts)
    assert artifacts.result["failures"][-1]["message"] == secret


def test_common_redactor_handles_credentials_without_environment_lookup():
    text = 'password="synthetic spaced secret" postgresql://test:synthetic-uri-secret@localhost/db'
    redacted = redact_error_message(text, {})
    assert "synthetic" not in redacted
    assert "localhost/db" in redacted
