import sqlite3
import json
from datetime import datetime, timezone

import pytest
import math_lab.runtime.daily_price_probe as probe_module

from math_lab.runtime.daily_price_readiness import (
    ProbeContext,
    ReadOnlySqlViolation,
    build_unavailable_artifacts,
    render_markdown_report,
    run_readiness_probe,
    validate_read_only_sql,
    write_artifacts,
)
from math_lab.runtime.daily_price_probe import (
    PostgresReadOnlySession,
    _git_extraction_version,
    database_target_from_environment,
    postgres_connection_kwargs,
    redact_error_message,
)


class SQLiteReadOnlyFixtureSession:
    """Real SQL fixture with SQLite's engine-level query-only switch enabled."""

    vendor = "sqlite"
    read_only_verified = True
    read_only_evidence = {
        "transaction_read_only": True,
        "client_sql_guard": True,
        "rollback_on_exit": True,
    }

    def __init__(self, connection):
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA query_only = ON")

    def fetch_all(self, statement, params=()):
        validate_read_only_sql(statement)
        cursor = self.connection.execute(statement, params)
        return [dict(row) for row in cursor.fetchall()]


def _fixture_session():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE stocks_stock (
            symbol TEXT PRIMARY KEY,
            asset_type TEXT,
            exchange TEXT,
            sector TEXT,
            industry TEXT,
            currency TEXT,
            created_at TEXT
        );
        CREATE TABLE stocks_daily_price (
            id INTEGER PRIMARY KEY,
            stock_id TEXT,
            currency TEXT,
            date TEXT,
            open_price NUMERIC,
            high_price NUMERIC,
            low_price NUMERIC,
            close_price NUMERIC,
            volume INTEGER,
            created_at TEXT
        );
        CREATE TABLE stocks_stock_split (
            id INTEGER PRIMARY KEY,
            stock_id TEXT,
            date TEXT,
            numerator NUMERIC,
            denominator NUMERIC,
            split_type TEXT,
            source TEXT,
            created_at TEXT
        );
        CREATE TABLE shared_calendar_event (
            id INTEGER PRIMARY KEY,
            event_type TEXT,
            symbol TEXT,
            event_date TEXT,
            dividend_amount NUMERIC,
            source TEXT,
            first_seen_at TEXT,
            last_seen_at TEXT,
            fmp_last_updated TEXT
        );
        """
    )
    connection.executemany(
        "INSERT INTO stocks_stock VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("AAPL", "Common Stock", "NASDAQ", "Technology", "Hardware", "USD", "2024-01-01T00:00:00Z"),
            ("JPM", "Common Stock", "NYSE", "Financial Services", "Banks", "USD", "2024-01-01T00:00:00Z"),
            ("TINY", "Common Stock", "NASDAQ", "Industrials", "Tools", "USD", "2026-09-01T00:00:00Z"),
        ],
    )
    connection.executemany(
        "INSERT INTO stocks_daily_price VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (1, "AAPL", "USD", "2026-09-01", 100, 110, 95, 105, 1000, "2026-09-01T22:00:00Z"),
            (2, "AAPL", "USD", "2026-09-02", 105, 112, 101, 110, 1100, "2026-09-02T22:00:00Z"),
            (3, "AAPL", "USD", "2026-09-04", 0, 109, 99, 111, 1200, "2026-09-04T22:00:00Z"),
            (4, "TINY", "USD", "2026-09-04", 10, 11, 9, 10, 100, "2026-09-04T22:00:00Z"),
        ],
    )
    connection.executemany(
        "INSERT INTO stocks_stock_split VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (1, "AAPL", "2020-08-31", 4, 1, "forward", "fmp", "2026-08-01T00:00:00Z"),
            (2, "AAPL", "2014-06-09", 7, 1, "forward", "fmp", "2026-08-01T00:00:00Z"),
        ],
    )
    connection.execute(
        "INSERT INTO shared_calendar_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, "DIVIDEND", "AAPL", "2026-08-10", 0.25, "fmp", "2026-08-01T00:00:00Z", "2026-08-02T00:00:00Z", None),
    )
    connection.commit()
    return SQLiteReadOnlyFixtureSession(connection)


def _context():
    return ProbeContext(
        job_id="SV-MATH-DP-READINESS-001",
        run_id="test-run",
        observed_at=datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc),
        extraction_version="git:test",
        database_target="sqlite:test-fixture",
    )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE stocks_daily_price SET close_price = 0",
        "WITH removed AS (DELETE FROM stocks_daily_price RETURNING id) SELECT * FROM removed",
        "SELECT 1; DROP TABLE stocks_daily_price",
    ],
)
def test_sql_guard_rejects_statements_that_could_mutate_the_database(statement):
    """Removing a forbidden verb check must expose a write-capable probe query."""

    with pytest.raises(ReadOnlySqlViolation):
        validate_read_only_sql(statement)


def test_sql_guard_accepts_a_single_select_with_read_only_ctes():
    """Rejecting safe CTEs would prevent bounded read-only discovery queries."""

    validate_read_only_sql(
        "WITH coverage AS (SELECT stock_id FROM stocks_daily_price) "
        "SELECT stock_id FROM coverage"
    )


def test_representative_probe_preserves_missing_assets_and_profiles_observed_rows():
    """Dropping zero-row candidates would hide readiness failures and bias selection."""

    artifacts = run_readiness_probe(_fixture_session(), _context())
    by_symbol = {
        row["symbol"]: row
        for row in artifacts.result["findings"]["representative_basket"]
    }

    assert list(by_symbol) == ["SPY", "AAPL", "JPM", "XOM", "WMT", "UNH"]
    assert by_symbol["SPY"]["stock_exists"] is False
    assert by_symbol["SPY"]["selection_status"] == "deferred"
    assert "stock_metadata_not_found" in by_symbol["SPY"]["reason_codes"]
    assert by_symbol["JPM"]["stock_exists"] is True
    assert by_symbol["JPM"]["daily_price_row_count"] == 0
    assert "daily_price_rows_absent" in by_symbol["JPM"]["reason_codes"]

    aapl = by_symbol["AAPL"]
    assert aapl["daily_price_row_count"] == 3
    assert aapl["min_date"] == "2026-09-01"
    assert aapl["max_date"] == "2026-09-04"
    assert aapl["weekday_gap_proxy"] == {
        "expected_weekdays": 4,
        "observed_weekdays": 3,
        "missing_weekdays": 1,
        "missing_ratio": 0.25,
        "weekend_observations": 0,
        "calendar_contract": "weekday_proxy_not_exchange_calendar",
    }
    assert aapl["anomalies"] == {
        "nonpositive_ohlc_rows": 1,
        "zero_volume_rows": 0,
        "negative_volume_rows": 0,
        "ohlc_bounds_violation_rows": 1,
    }
    assert aapl["stock_split_count"] == 2
    assert aapl["dividend_event_count"] == 1
    assert aapl["selection_status"] == "deferred"
    assert "fatal_ohlcv_anomaly_observed" in aapl["reason_codes"]


def test_successful_probe_does_not_call_weekdays_exchange_business_days():
    """A weekday-only calculation must retain its holiday/calendar limitation."""

    artifacts = run_readiness_probe(_fixture_session(), _context())

    assert any(
        item["code"] == "weekday_gap_is_not_exchange_calendar_gap"
        for item in artifacts.result["uncertainties"]
    )


def test_adversarial_candidates_are_discovered_from_failure_modes():
    """Hard-coding famous tickers must not replace failure-mode-first discovery."""

    artifacts = run_readiness_probe(_fixture_session(), _context())
    discovery = {
        item["failure_mode"]: item
        for item in artifacts.result["findings"]["adversarial_candidate_discovery"]
    }

    repeated = discovery["recorded_repeated_split"]
    assert repeated["status"] == "completed_recorded_events_only"
    assert repeated["candidates"][0]["symbol"] == "AAPL"
    assert repeated["candidates"][0]["event_count"] == 2
    assert repeated["candidates"][0]["daily_price_coverage"] == {
        "row_count": 3,
        "min_date": "2026-09-01",
        "max_date": "2026-09-04",
    }
    assert repeated["candidates"][0]["events_inside_price_range"] == 0
    assert repeated["candidates"][0]["events_outside_price_range"] == 2
    assert repeated["candidates"][0]["candidate_status"] == (
        "deferred_event_outside_price_coverage"
    )

    dividend = discovery["dividend_history"]["candidates"][0]
    assert dividend["symbol"] == "AAPL"
    assert dividend["events_inside_price_range"] == 0
    assert dividend["candidate_status"] == (
        "deferred_event_outside_price_coverage"
    )

    short_history = discovery["ipo_or_short_history"]
    assert short_history["status"] == "completed_with_short_history_proxy"
    assert [row["symbol"] for row in short_history["candidates"][:2]] == [
        "JPM",
        "TINY",
    ]
    assert short_history["candidates"][0]["daily_price_row_count"] == 0

    gaps = discovery["long_missing_period_or_suspension"]
    assert gaps["status"] == "completed_with_weekday_proxy"
    assert gaps["candidates"][0]["symbol"] == "AAPL"
    assert gaps["candidates"][0]["missing_weekday_proxy_count"] == 1

    assert discovery["ticker_change"]["status"] == "not_assessable"
    assert discovery["merger_or_acquisition"]["status"] == "not_assessable"
    assert discovery["spin_off"]["status"] == "not_assessable"
    assert discovery["delisting_or_terminal_return"]["status"] == "not_assessable"


def test_zero_volume_is_inventoried_without_being_silently_treated_as_clean():
    """Removing the zero-volume branch must expose suspended/stale candidates."""

    session = _fixture_session()
    session.connection.execute("PRAGMA query_only = OFF")
    session.connection.execute(
        "UPDATE stocks_daily_price SET volume = 0 WHERE stock_id = 'TINY'"
    )
    session.connection.commit()
    session.connection.execute("PRAGMA query_only = ON")

    artifacts = run_readiness_probe(session, _context())
    integrity = next(
        item
        for item in artifacts.result["findings"]["adversarial_candidate_discovery"]
        if item["failure_mode"] == "ohlcv_integrity"
    )
    tiny = next(row for row in integrity["candidates"] if row["symbol"] == "TINY")

    assert tiny["zero_volume_rows"] == 1
    assert tiny["negative_volume_rows"] == 0


def test_weekend_rows_do_not_hide_missing_weekdays_and_long_gaps_are_reported():
    """Subtracting all rows from weekdays would let weekend rows cancel real gaps."""

    session = _fixture_session()
    session.connection.execute("PRAGMA query_only = OFF")
    session.connection.execute(
        "INSERT INTO stocks_daily_price VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            5,
            "AAPL",
            "USD",
            "2026-09-05",
            111,
            114,
            110,
            113,
            900,
            "2026-09-05T22:00:00Z",
        ),
    )
    session.connection.commit()
    session.connection.execute("PRAGMA query_only = ON")

    artifacts = run_readiness_probe(session, _context())
    discovery = next(
        item
        for item in artifacts.result["findings"]["adversarial_candidate_discovery"]
        if item["failure_mode"] == "long_missing_period_or_suspension"
    )
    aapl = next(row for row in discovery["candidates"] if row["symbol"] == "AAPL")

    assert aapl["daily_price_row_count"] == 4
    assert aapl["observed_weekday_count"] == 3
    assert aapl["weekend_observation_count"] == 1
    assert aapl["missing_weekday_proxy_count"] == 1
    assert aapl["max_internal_calendar_gap_days"] == 2
    assert aapl["stale_tail_calendar_days"] == 3
    assert "max_internal_calendar_gap_days" in aapl["selection_ranks"]


def test_weekend_only_history_keeps_anomaly_without_crashing_ratio_ranking():
    """An undefined weekday ratio must remain sortable and preserve weekend evidence."""

    session = _fixture_session()
    session.connection.execute("PRAGMA query_only = OFF")
    session.connection.execute(
        "UPDATE stocks_daily_price SET date = '2026-09-05' WHERE stock_id = 'TINY'"
    )
    session.connection.commit()
    session.connection.execute("PRAGMA query_only = ON")

    artifacts = run_readiness_probe(session, _context())
    discovery = next(
        item
        for item in artifacts.result["findings"]["adversarial_candidate_discovery"]
        if item["failure_mode"] == "long_missing_period_or_suspension"
    )
    tiny = next(row for row in discovery["candidates"] if row["symbol"] == "TINY")

    assert artifacts.result["probe"]["database_status"] == "available"
    assert tiny["missing_ratio"] is None
    assert tiny["weekend_observation_count"] == 1
    assert tiny["selection_ranks"]["weekend_observation_count"] == 1


def test_stale_tail_ranking_surfaces_candidate_beyond_missing_ratio_top_ten():
    """A stale asset must survive even when more than ten assets have larger gap ratios."""

    session = _fixture_session()
    session.connection.execute("PRAGMA query_only = OFF")
    extra_stocks = [
        (
            f"GAP{index:02d}",
            "Common Stock",
            "NYSE",
            "Industrials",
            "Tools",
            "USD",
            "2024-01-01T00:00:00Z",
        )
        for index in range(11)
    ]
    extra_stocks.append(
        (
            "STALE",
            "Common Stock",
            "NYSE",
            "Industrials",
            "Tools",
            "USD",
            "2020-01-01T00:00:00Z",
        )
    )
    session.connection.executemany(
        "INSERT INTO stocks_stock VALUES (?, ?, ?, ?, ?, ?, ?)", extra_stocks
    )
    price_rows = []
    next_id = 10
    for index in range(11):
        symbol = f"GAP{index:02d}"
        for observed_date in ("2026-09-01", "2026-09-03"):
            price_rows.append(
                (
                    next_id,
                    symbol,
                    "USD",
                    observed_date,
                    10,
                    11,
                    9,
                    10,
                    100,
                    f"{observed_date}T22:00:00Z",
                )
            )
            next_id += 1
    price_rows.append(
        (
            next_id,
            "STALE",
            "USD",
            "2020-01-06",
            10,
            11,
            9,
            10,
            100,
            "2020-01-06T22:00:00Z",
        )
    )
    session.connection.executemany(
        "INSERT INTO stocks_daily_price VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        price_rows,
    )
    session.connection.commit()
    session.connection.execute("PRAGMA query_only = ON")

    artifacts = run_readiness_probe(session, _context())
    discovery = next(
        item
        for item in artifacts.result["findings"]["adversarial_candidate_discovery"]
        if item["failure_mode"] == "long_missing_period_or_suspension"
    )
    stale = next(row for row in discovery["candidates"] if row["symbol"] == "STALE")

    assert stale["missing_weekday_proxy_count"] == 0
    assert stale["selection_ranks"]["stale_tail_calendar_days"] == 1
    assert "stale_tail_calendar_days" in discovery["ranking_dimensions"]


def test_absent_optional_event_tables_are_not_reported_as_zero_events():
    """Schema absence and a queried empty event table are different evidence states."""

    session = _fixture_session()
    session.connection.execute("PRAGMA query_only = OFF")
    session.connection.execute("DROP TABLE stocks_stock_split")
    session.connection.execute("DROP TABLE shared_calendar_event")
    session.connection.commit()
    session.connection.execute("PRAGMA query_only = ON")

    artifacts = run_readiness_probe(session, _context())
    aapl = next(
        row
        for row in artifacts.result["findings"]["representative_basket"]
        if row["symbol"] == "AAPL"
    )
    discovery = {
        item["failure_mode"]: item
        for item in artifacts.result["findings"]["adversarial_candidate_discovery"]
    }

    assert aapl["stock_split_observation_status"] == "not_assessable"
    assert aapl["stock_split_count"] is None
    assert aapl["dividend_observation_status"] == "not_assessable"
    assert aapl["dividend_event_count"] is None
    assert discovery["recorded_repeated_split"]["status"] == "not_assessable"
    assert discovery["dividend_history"]["status"] == "not_assessable"


def test_current_daily_price_contract_is_only_exploratory_for_observed_fixture():
    """A fingerprint alone must not mask absent availability and provenance evidence."""

    session = _fixture_session()
    # F1 now excludes known fatal assets. Make this provenance-focused fixture
    # nonfatal; the original dirty fixture is covered by boundary regressions.
    session.connection.execute("PRAGMA query_only = OFF")
    session.connection.execute(
        "UPDATE stocks_daily_price SET open_price=105, close_price=105 WHERE id=3"
    )
    session.connection.commit()
    session.connection.execute("PRAGMA query_only = ON")
    artifacts = run_readiness_probe(session, _context())
    decisions = {
        row["intended_use"]: row
        for row in artifacts.result["findings"]["data_eligibility_decisions"]
    }

    assert decisions["exploratory"]["eligibility"] == "exploratory_only"
    assert (
        decisions["confirmatory"]["eligibility"]
        == "prohibited_for_declared_use"
    )
    assert (
        decisions["replication"]["eligibility"]
        == "prohibited_for_declared_use"
    )
    assert decisions["confirmatory"]["availability_confidence"] == "unknown"
    assert decisions["confirmatory"]["point_in_time_reconstructable"] is False
    assert decisions["confirmatory"]["content_fingerprint"] is None
    assert decisions["confirmatory"]["probe_result_fingerprint"].startswith("sha256:")
    assert decisions["confirmatory"]["content_fingerprint_scope"] == (
        "missing_full_data_view_fingerprint"
    )
    assert {
        "point_in_time_reconstructability",
        "sufficient_availability_confidence",
        "daily_price_provider_provenance",
        "price_adjustment_semantics",
        "revision_lineage",
        "entity_resolution_version",
        "sealed_data_view_fingerprint",
    }.issubset(decisions["confirmatory"]["missing_requirements"])
    assert "replication_independence_evidence" in decisions["replication"][
        "missing_requirements"
    ]


def test_schema_columns_alone_do_not_prove_point_in_time_or_provenance_semantics():
    """An empty or semantically invalid column must not upgrade eligibility."""

    session = _fixture_session()
    session.connection.execute("PRAGMA query_only = OFF")
    session.connection.execute("ALTER TABLE stocks_daily_price ADD COLUMN available_at TEXT")
    session.connection.execute("ALTER TABLE stocks_daily_price ADD COLUMN source TEXT")
    session.connection.execute("ALTER TABLE stocks_daily_price ADD COLUMN is_adjusted INTEGER")
    session.connection.execute("ALTER TABLE stocks_daily_price ADD COLUMN revision_id TEXT")
    session.connection.execute(
        "CREATE TABLE stocks_symbol_history (symbol TEXT, effective_at TEXT)"
    )
    session.connection.commit()
    session.connection.execute("PRAGMA query_only = ON")

    artifacts = run_readiness_probe(session, _context())
    decisions = {
        row["intended_use"]: row
        for row in artifacts.result["findings"]["data_eligibility_decisions"]
    }

    assert decisions["confirmatory"]["availability_confidence"] == "unknown"
    assert decisions["confirmatory"]["point_in_time_reconstructable"] is False
    assert decisions["confirmatory"]["entity_resolution_version"] is None
    assert decisions["confirmatory"]["eligibility"] == "prohibited_for_declared_use"
    assert "semantic_evidence_not_validated" in decisions["confirmatory"]["reasons"]


def test_schema_inventory_is_limited_to_readiness_tables():
    """Unrelated application schemas must not leak into readiness artifacts."""

    session = _fixture_session()
    session.connection.execute("PRAGMA query_only = OFF")
    session.connection.execute("CREATE TABLE unrelated_secret (secret TEXT)")
    session.connection.commit()
    session.connection.execute("PRAGMA query_only = ON")

    artifacts = run_readiness_probe(session, _context())

    assert "unrelated_secret" not in artifacts.result["findings"][
        "schema_capabilities"
    ]


def test_material_missing_requirements_become_structured_data_gap_proposals():
    """Returning only prose limitations would make recurring platform gaps unrouteable."""

    artifacts = run_readiness_probe(_fixture_session(), _context())
    gaps = {gap["gap_id"]: gap for gap in artifacts.data_gaps}

    expected = {
        "DG-DP-AVAILABLE-AT-001",
        "DG-DP-PROVENANCE-001",
        "DG-DP-ADJUSTMENT-001",
        "DG-DP-DIVIDEND-001",
        "DG-DP-REVISION-001",
        "DG-DP-ENTITY-001",
        "DG-DP-TERMINAL-RETURN-001",
        "DG-DP-CALENDAR-001",
        "DG-DP-EXPORT-001",
    }
    assert expected.issubset(gaps)
    assert artifacts.result["data_gap_ids"] == [
        gap["gap_id"] for gap in artifacts.data_gaps
    ]

    methodology_fields = {
        "research_need",
        "requested_data_or_transformation",
        "current_limitation",
        "change_class",
        "frequency",
        "history",
        "universe",
        "reusability",
        "expected_cost",
        "alternatives",
        "priority",
        "lead_recommendation",
    }
    for gap in artifacts.data_gaps:
        assert methodology_fields.issubset(gap)
        assert set(gap["expected_cost"]) == {
            "api",
            "storage",
            "compute",
            "engineering",
        }
        assert gap["blocked_eligibility"] == (
            "all use while the snapshot is unobserved; confirmatory and replication "
            "use after observation"
        )
        assert gap["lead_recommendation"].startswith(
            "Prohibit use of an unobserved snapshot; after observation, keep affected "
            "research exploratory-only until this gap closes."
        )


def test_repository_schema_evidence_uses_literal_field_labels():
    """A date or created_at field must not be mislabeled as proven PIT semantics."""

    artifacts = build_unavailable_artifacts(
        _context(),
        error_type="OperationalError",
        error_message="connection blocked by restricted network policy",
    )
    presence = artifacts.result["findings"]["repository_schema_evidence"][
        "schema_presence_from_code"
    ]

    assert presence["date_field_present"] is True
    assert presence["created_at_field_present"] is True
    assert "effective_time_column_present" not in presence
    assert "recorded_at_column_present" not in presence


def test_database_failure_preserves_candidates_and_prohibits_unobserved_views():
    """A connection failure must not become empty output or fixture-backed evidence."""

    artifacts = build_unavailable_artifacts(
        _context(),
        error_type="OperationalError",
        error_message="connection blocked by restricted network policy",
    )
    rows = artifacts.result["findings"]["representative_basket"]
    decisions = artifacts.result["findings"]["data_eligibility_decisions"]

    assert artifacts.result["status"] == "partial"
    assert artifacts.result["probe"]["database_status"] == "unavailable"
    assert artifacts.result["probe"]["read_only_verified"] is False
    assert [row["symbol"] for row in rows] == [
        "SPY",
        "AAPL",
        "JPM",
        "XOM",
        "WMT",
        "UNH",
    ]
    assert all(row["observation_status"] == "not_observed" for row in rows)
    assert all(row["daily_price_row_count"] is None for row in rows)
    assert all(row["anomalies"] is None for row in rows)
    assert all(
        decision["eligibility"] == "prohibited_for_declared_use"
        for decision in decisions
    )
    assert all(decision["content_fingerprint"] is None for decision in decisions)
    assert artifacts.result["failures"] == [
        {
            "stage": "database_connection",
            "status": "failed",
            "error_type": "OperationalError",
            "message": "connection blocked by restricted network policy",
            "consequence": "No live schema or DailyPrice rows were observed.",
        }
    ]
    assert artifacts.data_gaps[0]["gap_id"] == "DG-DP-ACCESS-001"


def test_late_query_failure_retains_completed_representative_observations():
    """A failed universe query must not rewrite earlier live evidence as unobserved."""

    delegate = _fixture_session()

    class FailingAdversarialSession:
        vendor = delegate.vendor
        read_only_verified = delegate.read_only_verified
        read_only_evidence = delegate.read_only_evidence

        def fetch_all(self, statement, params=()):
            if "FROM stocks_stock AS s" in statement:
                raise TimeoutError("full-universe aggregate timed out")
            return delegate.fetch_all(statement, params)

    artifacts = run_readiness_probe(FailingAdversarialSession(), _context())
    by_symbol = {
        row["symbol"]: row
        for row in artifacts.result["findings"]["representative_basket"]
    }

    assert artifacts.result["probe"]["database_status"] == "query_failed"
    assert artifacts.result["probe"]["read_only_verified"] is True
    assert by_symbol["AAPL"]["observation_status"] == "observed"
    assert by_symbol["AAPL"]["daily_price_row_count"] == 3
    assert all(
        item["status"] == "not_run_due_query_failure"
        for item in artifacts.result["findings"]["adversarial_candidate_discovery"]
    )
    assert artifacts.result["failures"][0]["stage"] == (
        "adversarial_candidate_discovery"
    )
    assert artifacts.result["failures"][0]["error_type"] == "TimeoutError"
    assert artifacts.data_gaps[0]["gap_id"] == "DG-DP-QUERY-001"


def test_markdown_and_json_artifacts_retain_failure_and_decisions(tmp_path):
    """Malformed or empty artifacts would make the readiness result non-auditable."""

    artifacts = build_unavailable_artifacts(
        _context(),
        error_type="OperationalError",
        error_message="connection unavailable",
    )
    result_path = tmp_path / "result.json"
    gaps_path = tmp_path / "data_gaps.json"
    report_path = tmp_path / "agent_report.md"

    write_artifacts(
        artifacts,
        result_path=result_path,
        data_gaps_path=gaps_path,
        report_path=report_path,
    )

    parsed_result = json.loads(result_path.read_text(encoding="utf-8"))
    parsed_gaps = json.loads(gaps_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")
    assert parsed_result["findings"]["representative_basket"]
    assert parsed_gaps[0]["gap_id"] == "DG-DP-ACCESS-001"
    assert "connection unavailable" in report
    assert "prohibited_for_declared_use" in report
    for symbol in ("SPY", "AAPL", "JPM", "XOM", "WMT", "UNH"):
        assert f"| {symbol} |" in report


def test_markdown_renderer_scopes_successful_fixture_as_non_confirmatory():
    """A successful inventory must not be described as predictive validation."""

    artifacts = run_readiness_probe(_fixture_session(), _context())
    report = render_markdown_report(artifacts)

    assert "No predictive-validity, tradability, or production-readiness claim" in report
    assert "weekday proxy" in report.lower()


class _FakeCursor:
    def __init__(self, events, readonly="on", isolation="repeatable read"):
        self.events = events
        self.readonly = readonly
        self.isolation = isolation
        self.last_statement = None
        self.description = []

    def execute(self, statement, params=()):
        self.last_statement = statement
        self.events.append(("execute", statement, tuple(params)))
        if statement.startswith("SELECT"):
            self.description = [("symbol",)]

    def fetchone(self):
        if self.last_statement == "SHOW transaction_isolation":
            return (self.isolation,)
        return (self.readonly,)

    def fetchall(self):
        return [("AAPL",)]

    def close(self):
        self.events.append(("cursor_close",))


class _FakeConnection:
    def __init__(self, readonly="on", isolation="repeatable read"):
        self.events = []
        self.cursor_instance = _FakeCursor(
            self.events, readonly=readonly, isolation=isolation
        )

    def set_session(self, **kwargs):
        self.events.append(("set_session", kwargs))

    def cursor(self):
        self.events.append(("cursor",))
        return self.cursor_instance

    def rollback(self):
        self.events.append(("rollback",))

    def close(self):
        self.events.append(("connection_close",))


def test_postgres_cleanup_closes_connection_even_when_cursor_close_fails():
    """A cursor cleanup error must not leak the underlying database connection."""

    connection = _FakeConnection()

    def broken_cursor_close():
        connection.events.append(("cursor_close",))
        raise RuntimeError("cursor close failed")

    connection.cursor_instance.close = broken_cursor_close
    session = PostgresReadOnlySession(
        {"dbname": "stock_vis"}, connector=lambda **_: connection
    )

    with pytest.raises(RuntimeError, match="cursor close failed"):
        with session:
            pass
    assert ("connection_close",) in connection.events


def test_postgres_session_verifies_server_read_only_before_first_select():
    """Moving the verification after probe SQL would reopen an accidental write window."""

    connection = _FakeConnection()
    received_kwargs = []

    def connect(**kwargs):
        received_kwargs.append(kwargs)
        return connection

    with PostgresReadOnlySession(
        {"dbname": "stock_vis"}, connector=connect
    ) as session:
        assert session.read_only_verified is True
        assert session.fetch_all("SELECT symbol FROM stocks_stock WHERE symbol = ?", ("AAPL",)) == [
            {"symbol": "AAPL"}
        ]

    assert received_kwargs == [{"dbname": "stock_vis"}]
    assert connection.events[:6] == [
        (
            "set_session",
            {
                "isolation_level": "REPEATABLE READ",
                "readonly": True,
                "autocommit": False,
            },
        ),
        ("cursor",),
        (
            "execute",
            "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
            (),
        ),
        ("execute", "SHOW transaction_read_only", ()),
        ("execute", "SHOW transaction_isolation", ()),
        (
            "execute",
            "SELECT symbol FROM stocks_stock WHERE symbol = %s",
            ("AAPL",),
        ),
    ]
    assert session.read_only_evidence["transaction_isolation"] == "repeatable read"
    assert connection.events[-3:] == [
        ("rollback",),
        ("cursor_close",),
        ("connection_close",),
    ]


def test_postgres_session_refuses_server_that_does_not_confirm_read_only():
    """A client flag without server confirmation must never authorize probe SELECTs."""

    connection = _FakeConnection(readonly="off")

    with pytest.raises(ReadOnlySqlViolation, match="transaction_read_only"):
        with PostgresReadOnlySession(
            {"dbname": "stock_vis"}, connector=lambda **_: connection
        ):
            raise AssertionError("unreachable")
    assert ("rollback",) in connection.events
    assert ("connection_close",) in connection.events


def test_database_connection_configuration_is_read_only_and_redacted():
    """Credentials must not leak through result metadata or captured errors."""

    environment = {
        "DB_HOST": "db.internal",
        "DB_PORT": "5544",
        "DB_USER": "probe_reader",
        "DB_PASSWORD": "top-secret-password",
    }
    kwargs = postgres_connection_kwargs(environment)

    assert kwargs["dbname"] == "stock_vis"
    assert kwargs["user"] == "probe_reader"
    assert kwargs["password"] == "top-secret-password"
    assert "default_transaction_read_only=on" in kwargs["options"]
    assert database_target_from_environment(environment) == (
        "postgresql://db.internal:5544/stock_vis"
    )
    assert "top-secret-password" not in database_target_from_environment(environment)
    assert redact_error_message(
        "authentication failed for top-secret-password", environment
    ) == "authentication failed for [REDACTED]"


def test_extraction_version_fingerprints_uncommitted_probe_source():
    """Using HEAD alone would misidentify worktree code that produced an artifact."""

    version = _git_extraction_version()

    assert "+probe-sha256:" in version
    assert len(version.rsplit(":", 1)[1]) == 64


def test_cli_retains_probe_findings_when_connection_cleanup_reports_failure(
    tmp_path, monkeypatch
):
    """A late close error must not replace completed live findings with placeholders."""

    fixture = _fixture_session()

    class CleanupFailingSession:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return fixture

        def __exit__(self, *_args):
            raise RuntimeError("connection close failed after probe")

    monkeypatch.setattr(probe_module, "PostgresReadOnlySession", CleanupFailingSession)
    result_path = tmp_path / "result.json"
    gaps_path = tmp_path / "gaps.json"
    report_path = tmp_path / "report.md"

    exit_code = probe_module.main(
        [
            "--run-id",
            "cleanup-test",
            "--observed-at",
            "2026-09-08T12:00:00+00:00",
            "--result-json",
            str(result_path),
            "--data-gaps-json",
            str(gaps_path),
            "--report-md",
            str(report_path),
        ]
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    aapl = next(
        row for row in result["findings"]["representative_basket"]
        if row["symbol"] == "AAPL"
    )

    assert exit_code == 2
    assert result["probe"]["database_status"] == "cleanup_failed_after_probe"
    assert aapl["daily_price_row_count"] == 3
    assert result["failures"][-1]["stage"] == "database_cleanup"
