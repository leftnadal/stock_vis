"""Read-only DailyPrice readiness probing for the Math Lab.

This module owns the database-independent probe and report contract.  Database
connections are supplied by a session that has already proved that its current
transaction is read-only; the probe additionally refuses any non-SELECT SQL.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence
import hashlib
import json
import re

from math_lab.runtime.error_redaction import (
    redact_error_message,
    redact_persisted_errors,
)

from math_lab.runtime.data_eligibility import (
    AvailabilityConfidence,
    DataViewContract,
    Eligibility,
    IntendedUse,
    evaluate_data_view,
)


class ReadOnlySqlViolation(ValueError):
    """Raised before a query that is not demonstrably read-only can execute."""


_FORBIDDEN_SQL = re.compile(
    r"\b(?:ALTER|ANALYZE|CALL|COPY|CREATE|DELETE|DO|DROP|EXECUTE|GRANT|INSERT|"
    r"LOCK|MERGE|REINDEX|REPLACE|REVOKE|SET|TRUNCATE|UPDATE|VACUUM)\b",
    re.IGNORECASE,
)


def validate_read_only_sql(statement: str) -> None:
    """Reject anything except one SELECT or a read-only CTE ending in SELECT.

    The probe only owns fixed queries, so a conservative lexical guard is an
    appropriate second line of defence behind a database-enforced read-only
    transaction.  Comments and multiple statements are intentionally refused.
    """

    normalized = statement.strip()
    if not normalized:
        raise ReadOnlySqlViolation("empty SQL is not an allowed probe query")
    if "--" in normalized or "/*" in normalized or "*/" in normalized:
        raise ReadOnlySqlViolation("SQL comments are not allowed in probe queries")
    if ";" in normalized.rstrip(";"):
        raise ReadOnlySqlViolation("multiple SQL statements are not allowed")
    normalized = normalized.rstrip(";").strip()
    first_word = normalized.split(None, 1)[0].upper()
    if first_word not in {"SELECT", "WITH"}:
        raise ReadOnlySqlViolation("probe queries must start with SELECT or WITH")
    forbidden = _FORBIDDEN_SQL.search(normalized)
    if forbidden:
        raise ReadOnlySqlViolation(
            f"forbidden SQL verb in probe query: {forbidden.group(0).upper()}"
        )


REPRESENTATIVE_BASKET = ("SPY", "AAPL", "JPM", "XOM", "WMT", "UNH")

AUTHORITY_REFERENCES = (
    "math_lab/00_foundation/foundation_ko.md",
    "math_lab/01_operating_system/operating_model_ko.md",
    "math_lab/02_methodology/research_methodology_ko.md",
    "math_lab/05_validation/daily_price_validation_basket_v0_1_ko.md",
)


class ReadOnlySession(Protocol):
    """Minimal boundary implemented by a database-enforced read-only session."""

    vendor: str
    read_only_verified: bool
    read_only_evidence: Mapping[str, Any]

    def fetch_all(
        self, statement: str, params: Sequence[Any] = ()
    ) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class ProbeContext:
    job_id: str
    run_id: str
    observed_at: datetime
    extraction_version: str
    database_target: str

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if not self.extraction_version:
            raise ValueError("extraction_version is required")


@dataclass(frozen=True)
class ReadinessArtifacts:
    result: dict[str, Any]
    data_gaps: list[dict[str, Any]]


_REQUIRED_TABLE_COLUMNS: dict[str, frozenset[str]] = {
    "stocks_stock": frozenset({"symbol", "sector", "industry", "currency"}),
    "stocks_daily_price": frozenset(
        {
            "stock_id",
            "currency",
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "created_at",
        }
    ),
}

_SCHEMA_TABLES_OF_INTEREST = tuple(
    sorted(
        {
            *_REQUIRED_TABLE_COLUMNS,
            "stocks_stock_split",
            "shared_calendar_event",
            "stocks_dividend",
            "stocks_dividend_history",
            "stocks_symbol_history",
            "stocks_entity_lifecycle",
            "stocks_corporate_action",
            "stocks_delisting",
            "stocks_terminal_return",
            "stocks_exchange_session",
            "market_exchange_session",
        }
    )
)

REPOSITORY_SCHEMA_EVIDENCE: dict[str, set[str]] = {
    "stocks_stock": {
        "symbol",
        "asset_type",
        "exchange",
        "sector",
        "industry",
        "currency",
        "created_at",
    },
    "stocks_daily_price": {
        "id",
        "stock_id",
        "currency",
        "date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "created_at",
    },
    "stocks_stock_split": {
        "id",
        "stock_id",
        "date",
        "numerator",
        "denominator",
        "split_type",
        "source",
        "created_at",
    },
    "shared_calendar_event": {
        "id",
        "event_type",
        "symbol",
        "event_date",
        "dividend_amount",
        "source",
        "first_seen_at",
        "last_seen_at",
        "fmp_last_updated",
    },
}


def _placeholders(size: int) -> str:
    return ", ".join("?" for _ in range(size))


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _number(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _load_schema(session: ReadOnlySession) -> dict[str, set[str]]:
    placeholders = _placeholders(len(_SCHEMA_TABLES_OF_INTEREST))
    if session.vendor == "sqlite":
        statement = f"""
            SELECT m.name AS table_name, p.name AS column_name
            FROM sqlite_master AS m
            JOIN pragma_table_info(m.name) AS p
            WHERE m.type IN ('table', 'view')
              AND m.name IN ({placeholders})
            ORDER BY m.name, p.cid
        """
    else:
        statement = f"""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name IN ({placeholders})
            ORDER BY table_name, ordinal_position
        """
    schema: dict[str, set[str]] = defaultdict(set)
    for row in session.fetch_all(statement, _SCHEMA_TABLES_OF_INTEREST):
        schema[str(row["table_name"])].add(str(row["column_name"]))
    return dict(schema)


def _metadata_rows(
    session: ReadOnlySession, schema: Mapping[str, set[str]]
) -> dict[str, dict[str, Any]]:
    columns = schema.get("stocks_stock", set())
    optional = ("asset_type", "exchange", "created_at")
    selections = ["symbol", "sector", "industry", "currency"]
    selections.extend(
        column if column in columns else f"NULL AS {column}" for column in optional
    )
    statement = (
        f"SELECT {', '.join(selections)} FROM stocks_stock "
        f"WHERE symbol IN ({_placeholders(len(REPRESENTATIVE_BASKET))})"
    )
    return {
        str(row["symbol"]): row
        for row in session.fetch_all(statement, REPRESENTATIVE_BASKET)
    }


def _daily_rows(session: ReadOnlySession) -> dict[str, list[dict[str, Any]]]:
    statement = f"""
        SELECT stock_id AS symbol, currency, date,
               open_price, high_price, low_price, close_price, volume, created_at
        FROM stocks_daily_price
        WHERE stock_id IN ({_placeholders(len(REPRESENTATIVE_BASKET))})
        ORDER BY stock_id, date
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in session.fetch_all(statement, REPRESENTATIVE_BASKET):
        grouped[str(row["symbol"])].append(row)
    return dict(grouped)


def _split_summaries(
    session: ReadOnlySession, schema: Mapping[str, set[str]]
) -> dict[str, dict[str, Any]] | None:
    required = {"stock_id", "date", "numerator", "denominator"}
    if not required.issubset(schema.get("stocks_stock_split", set())):
        return None
    statement = f"""
        SELECT stock_id AS symbol, COUNT(*) AS event_count,
               MIN(date) AS first_event_date, MAX(date) AS last_event_date
        FROM stocks_stock_split
        WHERE stock_id IN ({_placeholders(len(REPRESENTATIVE_BASKET))})
        GROUP BY stock_id
    """
    return {
        str(row["symbol"]): row
        for row in session.fetch_all(statement, REPRESENTATIVE_BASKET)
    }


def _dividend_summaries(
    session: ReadOnlySession, schema: Mapping[str, set[str]]
) -> dict[str, dict[str, Any]] | None:
    required = {"event_type", "symbol", "event_date"}
    if not required.issubset(schema.get("shared_calendar_event", set())):
        return None
    statement = f"""
        SELECT symbol, COUNT(*) AS event_count,
               MIN(event_date) AS first_event_date,
               MAX(event_date) AS last_event_date
        FROM shared_calendar_event
        WHERE event_type = ?
          AND symbol IN ({_placeholders(len(REPRESENTATIVE_BASKET))})
        GROUP BY symbol
    """
    params = ("DIVIDEND", *REPRESENTATIVE_BASKET)
    return {str(row["symbol"]): row for row in session.fetch_all(statement, params)}


def _weekday_gap_profile(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "expected_weekdays": 0,
            "observed_weekdays": 0,
            "missing_weekdays": 0,
            "missing_ratio": None,
            "weekend_observations": 0,
            "calendar_contract": "weekday_proxy_not_exchange_calendar",
        }
    observed_dates = {_as_date(row["date"]) for row in rows}
    start = min(observed_dates)
    end = max(observed_dates)
    expected = 0
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            expected += 1
        cursor += timedelta(days=1)
    observed_weekdays = sum(day.weekday() < 5 for day in observed_dates)
    weekend_observations = len(observed_dates) - observed_weekdays
    missing = max(0, expected - observed_weekdays)
    return {
        "expected_weekdays": expected,
        "observed_weekdays": observed_weekdays,
        "missing_weekdays": missing,
        "missing_ratio": round(missing / expected, 6) if expected else None,
        "weekend_observations": weekend_observations,
        "calendar_contract": "weekday_proxy_not_exchange_calendar",
    }


def _expected_weekdays(start: date, end: date) -> int:
    count = 0
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            count += 1
        cursor += timedelta(days=1)
    return count


def _anomaly_profile(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    nonpositive = 0
    zero_volume = 0
    negative_volume = 0
    invalid_bounds = 0
    for row in rows:
        open_price = _number(row["open_price"])
        high_price = _number(row["high_price"])
        low_price = _number(row["low_price"])
        close_price = _number(row["close_price"])
        volume = _number(row["volume"])
        if min(open_price, high_price, low_price, close_price) <= 0:
            nonpositive += 1
        if volume == 0:
            zero_volume += 1
        if volume < 0:
            negative_volume += 1
        if (
            high_price < low_price
            or open_price < low_price
            or open_price > high_price
            or close_price < low_price
            or close_price > high_price
        ):
            invalid_bounds += 1
    return {
        "nonpositive_ohlc_rows": nonpositive,
        "zero_volume_rows": zero_volume,
        "negative_volume_rows": negative_volume,
        "ohlc_bounds_violation_rows": invalid_bounds,
    }


def _representative_rows(
    metadata: Mapping[str, Mapping[str, Any]],
    prices: Mapping[str, Sequence[Mapping[str, Any]]],
    splits: Mapping[str, Mapping[str, Any]] | None,
    dividends: Mapping[str, Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    splits_assessable = splits is not None
    dividends_assessable = dividends is not None
    output: list[dict[str, Any]] = []
    for symbol in REPRESENTATIVE_BASKET:
        stock = metadata.get(symbol)
        rows = list(prices.get(symbol, ()))
        anomaly = _anomaly_profile(rows)
        reason_codes: list[str] = []
        if stock is None:
            reason_codes.append("stock_metadata_not_found")
        else:
            if not stock.get("sector") or not stock.get("industry"):
                reason_codes.append("sector_or_industry_missing")
            if not rows:
                reason_codes.append("daily_price_rows_absent")
            if (
                anomaly["nonpositive_ohlc_rows"]
                or anomaly["negative_volume_rows"]
                or anomaly["ohlc_bounds_violation_rows"]
            ):
                reason_codes.append("fatal_ohlcv_anomaly_observed")
            elif anomaly["zero_volume_rows"]:
                reason_codes.append("zero_volume_rows_require_policy_review")
        if not reason_codes:
            selection_status = "eligible_for_distribution_review"
            reason_codes.append("history_sufficiency_threshold_not_precommitted")
        else:
            selection_status = "deferred"

        split = (splits or {}).get(symbol, {})
        dividend = (dividends or {}).get(symbol, {})
        recorded_values = [_iso(row.get("created_at")) for row in rows]
        recorded_values = [value for value in recorded_values if value is not None]
        currencies = sorted(
            {str(row["currency"]) for row in rows if row.get("currency") is not None}
        )
        output.append(
            {
                "symbol": symbol,
                "observation_status": "observed",
                "stock_exists": stock is not None,
                "asset_type": stock.get("asset_type") if stock else None,
                "exchange": stock.get("exchange") if stock else None,
                "sector": stock.get("sector") if stock else None,
                "industry": stock.get("industry") if stock else None,
                "stock_currency": stock.get("currency") if stock else None,
                "stock_created_at": _iso(stock.get("created_at")) if stock else None,
                "daily_price_row_count": len(rows),
                "min_date": _iso(rows[0]["date"]) if rows else None,
                "max_date": _iso(rows[-1]["date"]) if rows else None,
                "daily_price_recorded_at_min": min(recorded_values)
                if recorded_values
                else None,
                "daily_price_recorded_at_max": max(recorded_values)
                if recorded_values
                else None,
                "daily_price_currencies": currencies,
                "currency_mismatch_row_count": sum(
                    stock is not None
                    and row.get("currency") is not None
                    and row["currency"] != stock.get("currency")
                    for row in rows
                ),
                "weekday_gap_proxy": _weekday_gap_profile(rows),
                "anomalies": anomaly,
                "stock_split_observation_status": (
                    "observed" if splits_assessable else "not_assessable"
                ),
                "stock_split_count": (
                    int(split.get("event_count") or 0)
                    if splits_assessable
                    else None
                ),
                "stock_split_first_date": _iso(split.get("first_event_date")),
                "stock_split_last_date": _iso(split.get("last_event_date")),
                "dividend_observation_status": (
                    "observed" if dividends_assessable else "not_assessable"
                ),
                "dividend_event_count": (
                    int(dividend.get("event_count") or 0)
                    if dividends_assessable
                    else None
                ),
                "dividend_event_first_date": _iso(dividend.get("first_event_date")),
                "dividend_event_last_date": _iso(dividend.get("last_event_date")),
                "selection_status": selection_status,
                "reason_codes": reason_codes,
            }
        )
    for row in output:
        row["observed_content_status"] = _observed_content_status(row)
        row["research_input_sufficiency"] = "unassessed"
    return output


def _universe_price_summaries(
    session: ReadOnlySession,
) -> list[dict[str, Any]]:
    if session.vendor == "sqlite":
        weekday_condition = "CAST(strftime('%w', dp.date) AS INTEGER) BETWEEN 1 AND 5"
    else:
        weekday_condition = "EXTRACT(ISODOW FROM dp.date) BETWEEN 1 AND 5"
    statement = f"""
        SELECT s.symbol,
               COUNT(dp.id) AS daily_price_row_count,
               COUNT(DISTINCT CASE WHEN dp.id IS NOT NULL AND
                    {weekday_condition} THEN dp.date ELSE NULL END)
                    AS observed_weekday_count,
               SUM(CASE WHEN dp.id IS NOT NULL AND NOT ({weekday_condition})
                   THEN 1 ELSE 0 END) AS weekend_observation_count,
               MIN(dp.date) AS min_date,
               MAX(dp.date) AS max_date,
               SUM(CASE WHEN dp.id IS NOT NULL AND
                    (dp.open_price <= 0 OR dp.high_price <= 0 OR
                     dp.low_price <= 0 OR dp.close_price <= 0)
                   THEN 1 ELSE 0 END) AS nonpositive_ohlc_rows,
               SUM(CASE WHEN dp.id IS NOT NULL AND dp.volume < 0
                   THEN 1 ELSE 0 END) AS negative_volume_rows,
               SUM(CASE WHEN dp.id IS NOT NULL AND dp.volume = 0
                   THEN 1 ELSE 0 END) AS zero_volume_rows,
               SUM(CASE WHEN dp.id IS NOT NULL AND
                    (dp.high_price < dp.low_price OR
                     dp.open_price < dp.low_price OR
                     dp.open_price > dp.high_price OR
                     dp.close_price < dp.low_price OR
                     dp.close_price > dp.high_price)
                   THEN 1 ELSE 0 END) AS ohlc_bounds_violation_rows
        FROM stocks_stock AS s
        LEFT JOIN stocks_daily_price AS dp ON dp.stock_id = s.symbol
        GROUP BY s.symbol
        ORDER BY s.symbol
    """
    return session.fetch_all(statement)


def _universe_internal_gap_summaries(
    session: ReadOnlySession,
) -> dict[str, int]:
    if session.vendor == "sqlite":
        difference = "CAST(julianday(date) - julianday(previous_date) AS INTEGER)"
    else:
        difference = "date - previous_date"
    statement = f"""
        WITH ordered_dates AS (
            SELECT stock_id AS symbol, date,
                   LAG(date) OVER (PARTITION BY stock_id ORDER BY date)
                       AS previous_date
            FROM stocks_daily_price
        ), date_gaps AS (
            SELECT symbol, {difference} AS calendar_gap_days
            FROM ordered_dates
            WHERE previous_date IS NOT NULL
        )
        SELECT symbol, MAX(calendar_gap_days) AS max_internal_calendar_gap_days
        FROM date_gaps
        GROUP BY symbol
    """
    return {
        str(row["symbol"]): int(row["max_internal_calendar_gap_days"] or 0)
        for row in session.fetch_all(statement)
    }


def _split_event_rows(
    session: ReadOnlySession, schema: Mapping[str, set[str]]
) -> list[dict[str, Any]]:
    required = {"stock_id", "date", "numerator", "denominator"}
    columns = schema.get("stocks_stock_split", set())
    if not required.issubset(columns):
        return []
    source_selection = "source" if "source" in columns else "NULL AS source"
    statement = f"""
        SELECT stock_id AS symbol, date, numerator, denominator,
               {source_selection}
        FROM stocks_stock_split
        ORDER BY stock_id, date
    """
    return session.fetch_all(statement)


def _all_dividend_summaries(
    session: ReadOnlySession, schema: Mapping[str, set[str]]
) -> list[dict[str, Any]]:
    required = {"event_type", "symbol", "event_date"}
    if not required.issubset(schema.get("shared_calendar_event", set())):
        return []
    statement = """
        SELECT symbol, event_date
        FROM shared_calendar_event
        WHERE event_type = ?
        ORDER BY symbol, event_date
    """
    return session.fetch_all(statement, ("DIVIDEND",))


def _event_price_coverage(
    price_summary: Mapping[str, Any] | None,
    event_dates: Sequence[Any],
) -> dict[str, Any]:
    row_count = int(price_summary.get("daily_price_row_count") or 0) if price_summary else 0
    minimum = _as_date(price_summary["min_date"]) if price_summary and price_summary.get("min_date") else None
    maximum = _as_date(price_summary["max_date"]) if price_summary and price_summary.get("max_date") else None
    normalized_events = [_as_date(value) for value in event_dates]
    inside = (
        sum(minimum <= event <= maximum for event in normalized_events)
        if minimum is not None and maximum is not None
        else 0
    )
    outside = len(normalized_events) - inside
    if row_count == 0 or minimum is None or maximum is None:
        status = "deferred_no_daily_price_coverage"
    elif outside:
        status = "deferred_event_outside_price_coverage"
    else:
        status = "ready_for_event_window_review"
    return {
        "daily_price_coverage": {
            "row_count": row_count,
            "min_date": _iso(minimum),
            "max_date": _iso(maximum),
        },
        "events_inside_price_range": inside,
        "events_outside_price_range": outside,
        "candidate_status": status,
    }


def _rank_missing_period_candidates(
    candidates: Sequence[Mapping[str, Any]], *, per_dimension_limit: int = 10
) -> list[dict[str, Any]]:
    """Return a deterministic union so each independent failure signature survives."""

    dimensions = (
        ("missing_weekday_ratio", "missing_ratio", lambda value: value is not None and value > 0),
        ("missing_weekday_proxy_count", "missing_weekday_proxy_count", lambda value: value > 0),
        ("max_internal_calendar_gap_days", "max_internal_calendar_gap_days", lambda value: value > 1),
        ("stale_tail_calendar_days", "stale_tail_calendar_days", lambda value: value > 0),
        ("weekend_observation_count", "weekend_observation_count", lambda value: value > 0),
    )
    selected: dict[str, dict[str, Any]] = {}
    for rank_name, value_name, include in dimensions:
        eligible = [row for row in candidates if include(row.get(value_name))]
        ranked = sorted(
            eligible,
            key=lambda row: (-row[value_name], str(row["symbol"])),
        )[:per_dimension_limit]
        for rank, row in enumerate(ranked, start=1):
            symbol = str(row["symbol"])
            selected.setdefault(
                symbol,
                {**dict(row), "selection_ranks": {}},
            )["selection_ranks"][rank_name] = rank
    return sorted(
        selected.values(),
        key=lambda row: (
            min(row["selection_ranks"].values()),
            -len(row["selection_ranks"]),
            row["symbol"],
        ),
    )


def _discover_adversarial_candidates(
    session: ReadOnlySession,
    schema: Mapping[str, set[str]],
    context: ProbeContext,
) -> list[dict[str, Any]]:
    universe = _universe_price_summaries(session)
    internal_gaps = _universe_internal_gap_summaries(session)
    price_by_symbol = {str(row["symbol"]): row for row in universe}
    split_events = _split_event_rows(session, schema)
    grouped_splits: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for event in split_events:
        grouped_splits[str(event["symbol"])].append(event)

    split_candidates: list[dict[str, Any]] = []
    for symbol, events in grouped_splits.items():
        ratios: list[Decimal] = []
        invalid_ratio_rows = 0
        sources: set[str] = set()
        for event in events:
            denominator = _number(event.get("denominator"))
            numerator = _number(event.get("numerator"))
            if denominator <= 0 or numerator <= 0:
                invalid_ratio_rows += 1
            else:
                ratios.append(numerator / denominator)
            if event.get("source"):
                sources.add(str(event["source"]))
        factors = [max(ratio, Decimal("1") / ratio) for ratio in ratios]
        split_candidates.append(
            {
                "symbol": symbol,
                "event_count": len(events),
                "first_event_date": min(_iso(row["date"]) for row in events),
                "last_event_date": max(_iso(row["date"]) for row in events),
                "maximum_adjustment_factor": float(max(factors)) if factors else None,
                "invalid_ratio_rows": invalid_ratio_rows,
                "sources": sorted(sources),
                **_event_price_coverage(
                    price_by_symbol.get(symbol), [row["date"] for row in events]
                ),
            }
        )
    repeated_splits = sorted(
        (row for row in split_candidates if row["event_count"] >= 2),
        key=lambda row: (-row["event_count"], row["symbol"]),
    )[:10]
    large_splits = sorted(
        split_candidates,
        key=lambda row: (
            -(row["maximum_adjustment_factor"] or 0),
            -row["event_count"],
            row["symbol"],
        ),
    )[:10]

    short_history = sorted(
        (
            {
                "symbol": str(row["symbol"]),
                "daily_price_row_count": int(row["daily_price_row_count"] or 0),
                "min_date": _iso(row["min_date"]),
                "max_date": _iso(row["max_date"]),
            }
            for row in universe
        ),
        key=lambda row: (
            row["daily_price_row_count"],
            row["min_date"] or "9999-12-31",
            row["symbol"],
        ),
    )[:10]

    weekday_gap_candidates: list[dict[str, Any]] = []
    integrity_candidates: list[dict[str, Any]] = []
    for row in universe:
        row_count = int(row["daily_price_row_count"] or 0)
        if row.get("min_date") is not None and row.get("max_date") is not None:
            maximum_date = _as_date(row["max_date"])
            expected = _expected_weekdays(
                _as_date(row["min_date"]), maximum_date
            )
            observed_weekdays = int(row["observed_weekday_count"] or 0)
            weekend_observations = int(row["weekend_observation_count"] or 0)
            missing = max(0, expected - observed_weekdays)
            symbol = str(row["symbol"])
            weekday_gap_candidates.append(
                {
                    "symbol": symbol,
                    "daily_price_row_count": row_count,
                    "observed_weekday_count": observed_weekdays,
                    "weekend_observation_count": weekend_observations,
                    "min_date": _iso(row["min_date"]),
                    "max_date": _iso(row["max_date"]),
                    "expected_weekday_proxy_count": expected,
                    "missing_weekday_proxy_count": missing,
                    "missing_ratio": round(missing / expected, 6)
                    if expected
                    else None,
                    "max_internal_calendar_gap_days": internal_gaps.get(symbol, 0),
                    "stale_tail_calendar_days": max(
                        0,
                        (
                            context.observed_at.astimezone(timezone.utc).date()
                            - maximum_date
                        ).days,
                    ),
                }
            )
        anomaly = {
            "nonpositive_ohlc_rows": int(row["nonpositive_ohlc_rows"] or 0),
            "zero_volume_rows": int(row["zero_volume_rows"] or 0),
            "negative_volume_rows": int(row["negative_volume_rows"] or 0),
            "ohlc_bounds_violation_rows": int(
                row["ohlc_bounds_violation_rows"] or 0
            ),
        }
        if any(anomaly.values()):
            integrity_candidates.append(
                {
                    "symbol": str(row["symbol"]),
                    **anomaly,
                    "total_flag_count": sum(anomaly.values()),
                }
            )
    ranked_missing_periods = _rank_missing_period_candidates(
        weekday_gap_candidates
    )
    integrity_candidates.sort(
        key=lambda row: (-row["total_flag_count"], row["symbol"])
    )

    dividend_table_present = {
        "event_type",
        "symbol",
        "event_date",
    }.issubset(schema.get("shared_calendar_event", set()))
    split_table_ready = {
        "stock_id",
        "date",
        "numerator",
        "denominator",
    }.issubset(schema.get("stocks_stock_split", set()))
    grouped_dividends: dict[str, list[Any]] = defaultdict(list)
    for row in _all_dividend_summaries(session, schema):
        grouped_dividends[str(row["symbol"])].append(row["event_date"])
    dividends = sorted(
        (
            {
                "symbol": symbol,
                "event_count": len(event_dates),
                "first_event_date": min(_iso(value) for value in event_dates),
                "last_event_date": max(_iso(value) for value in event_dates),
                **_event_price_coverage(
                    price_by_symbol.get(symbol), event_dates
                ),
            }
            for symbol, event_dates in grouped_dividends.items()
        ),
        key=lambda row: (-row["event_count"], row["symbol"]),
    )[:10]

    lifecycle_limitation = (
        "No supported point-in-time entity/corporate-action ledger was found; "
        "current symbols cannot establish historical identity events."
    )
    return [
        {
            "failure_mode": "recorded_repeated_split",
            "status": "completed_recorded_events_only"
            if split_table_ready
            else "not_assessable",
            "selection_method": "rank StockSplit event count; require count >= 2",
            "candidates": repeated_splits,
            "limitations": [
                "Absence from StockSplit does not establish that no split occurred.",
                "Recorded events may share a single provider ancestry.",
            ],
        },
        {
            "failure_mode": "recorded_large_or_reverse_split",
            "status": "completed_recorded_events_only"
            if split_table_ready
            else "not_assessable",
            "selection_method": "rank maximum numerator:denominator adjustment factor",
            "candidates": large_splits,
            "limitations": [
                "Price discontinuities around split dates were not classified by this readiness probe."
            ],
        },
        {
            "failure_mode": "dividend_history",
            "status": "completed_with_operational_event_window"
            if dividend_table_present
            else "not_assessable",
            "selection_method": "rank DIVIDEND CalendarEvent count",
            "candidates": dividends,
            "limitations": [
                "CalendarEvent is not demonstrated to be a complete historical dividend ledger."
            ],
        },
        {
            "failure_mode": "ipo_or_short_history",
            "status": "completed_with_short_history_proxy",
            "selection_method": "rank DailyPrice row count ascending, retaining zero-row stocks",
            "candidates": short_history,
            "limitations": [
                "Short coverage cannot be classified as IPO history without point-in-time listing metadata."
            ],
        },
        {
            "failure_mode": "long_missing_period_or_suspension",
            "status": "completed_with_weekday_proxy",
            "selection_method": (
                "deterministic union of the top 10 candidates per independent "
                "missing-weekday, internal-gap, stale-tail, and weekend dimension"
            ),
            "ranking_dimensions": [
                "missing_weekday_ratio",
                "missing_weekday_proxy_count",
                "max_internal_calendar_gap_days",
                "stale_tail_calendar_days",
                "weekend_observation_count",
            ],
            "candidates": ranked_missing_periods,
            "limitations": [
                "The proxy includes exchange holidays and cannot distinguish suspensions from ingestion gaps."
            ],
        },
        {
            "failure_mode": "ohlcv_integrity",
            "status": "completed",
            "selection_method": "rank nonpositive prices, negative volume, and OHLC bound violations",
            "candidates": integrity_candidates[:10],
            "limitations": [
                "Passing structural bounds does not establish correct prices or adjustment semantics."
            ],
        },
        *[
            {
                "failure_mode": mode,
                "status": "not_assessable",
                "selection_method": "requires point-in-time lifecycle evidence",
                "candidates": [],
                "limitations": [lifecycle_limitation],
            }
            for mode in (
                "ticker_change",
                "merger_or_acquisition",
                "spin_off",
                "delisting_or_terminal_return",
            )
        ],
    ]


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _content_fingerprint(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def _daily_price_schema_presence(schema: Mapping[str, set[str]]) -> dict[str, bool]:
    columns = schema.get("stocks_daily_price", set())
    table_names = set(schema)
    return {
        "date_field_present": "date" in columns,
        "created_at_field_present": "created_at" in columns,
        "available_at_column_present": "available_at" in columns,
        "provider_column_present": bool({"provider", "source"} & columns),
        "adjustment_semantics_column_present": bool(
            {"adjustment_type", "is_adjusted", "adjusted_close"} & columns
        ),
        "revision_lineage_column_present": bool(
            {"revision_id", "superseded_at", "valid_from", "valid_to"} & columns
        ),
        "historical_dividend_table_present": bool(
            {"stocks_dividend", "stocks_dividend_history"} & table_names
        ),
        "entity_lifecycle_table_present": bool(
            {
                "stocks_symbol_history",
                "stocks_entity_lifecycle",
                "stocks_corporate_action",
            }
            & table_names
        ),
        "terminal_return_table_present": bool(
            {"stocks_delisting", "stocks_terminal_return"} & table_names
        ),
        "exchange_calendar_table_present": bool(
            {"stocks_exchange_session", "market_exchange_session"} & table_names
        ),
    }


def _inventory_permission(read_only_verified: bool) -> dict[str, Any]:
    return {
        "scope": "inventory_diagnostic_only",
        "status": "permitted_read_only" if read_only_verified else "not_established",
        "basis": "existing_authorized_access_and_verified_read_only_session",
        "grants_database_privileges": False,
        "implies_research_input_eligibility": False,
    }


def _observed_content_status(row: Mapping[str, Any]) -> str:
    """Describe the existing diagnostic evidence, never its research sufficiency."""
    if row.get("observation_status") != "observed":
        return "not_observed"
    if not row.get("daily_price_row_count"):
        return "no_price_rows_observed"
    if "fatal_ohlcv_anomaly_observed" in row.get("reason_codes", ()):
        return "fatal_observed"
    return "nonfatal_observed"


def _content_summary(representative: Sequence[Mapping[str, Any]]) -> str:
    statuses = {_observed_content_status(row) for row in representative}
    if {"fatal_observed", "nonfatal_observed"}.issubset(statuses):
        return "mixed_observed"
    for status in ("fatal_observed", "nonfatal_observed", "no_price_rows_observed"):
        if status in statuses:
            return status
    return "not_observed"


def _observed_content_scope(
    representative: Sequence[Mapping[str, Any]],
) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    """Separate observed nonfatal content from missing/fatal observations.

    These lists are diagnostic facts, not permitted inputs or a final basket.
    History, row-count, missingness and basket sufficiency remain unassessed.
    """
    nonfatal: list[str] = []
    excluded: list[dict[str, Any]] = []
    for row in representative:
        reasons = []
        if row.get("observation_status") != "observed":
            reasons.append("asset_not_observed")
        if not row.get("stock_exists"):
            reasons.append("stock_metadata_not_found")
        if not row.get("daily_price_row_count"):
            reasons.append("daily_price_rows_absent")
        if "fatal_ohlcv_anomaly_observed" in row.get("reason_codes", ()):
            reasons.append("fatal_ohlcv_anomaly_observed")
        if reasons:
            excluded.append({"symbol": row["symbol"], "reasons": reasons})
        else:
            nonfatal.append(str(row["symbol"]))
    blocking = [] if nonfatal else ["no_nonfatal_representative_price_content_observed"]
    return nonfatal, excluded, blocking


def _eligibility_decisions(
    schema: Mapping[str, set[str]],
    context: ProbeContext,
    fingerprint: str,
    representative: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    # Column names are discovery evidence, not proof of semantics, population,
    # completeness, or historical reconstructability.  This probe has no
    # validated provenance manifest, so every semantic claim stays unknown.
    point_in_time = False
    availability = AvailabilityConfidence.UNKNOWN
    nonfatal_symbols, excluded_symbols, blocking = _observed_content_scope(representative)
    common_missing = [
        "sealed_data_view_fingerprint",
        "daily_price_provider_provenance",
        "price_adjustment_semantics",
        "revision_lineage",
        "entity_resolution_version",
    ]

    output: list[dict[str, Any]] = []
    for intended_use in IntendedUse:
        view = DataViewContract(
            data_view_id=f"stockvis.daily_price:{context.run_id}:{intended_use.value}",
            source_system="stock_vis.postgresql",
            intended_use=intended_use,
            availability_confidence=availability,
            point_in_time_reconstructable=point_in_time,
            content_fingerprint=None,
            extraction_version=context.extraction_version,
            universe_version="daily_price_validation_basket_v0.1",
            entity_resolution_version=None,
            revision_lineage_available=False,
            notes=(
                "readiness_probe_not_predictive_validation",
                "schema_presence_is_not_semantic_evidence",
            ),
        )
        base = evaluate_data_view(view)
        missing = list(base.missing_requirements)
        missing.extend(item for item in common_missing if item not in missing)
        if intended_use is IntendedUse.REPLICATION:
            missing.append("replication_independence_evidence")
        reasons = [reason for reason in base.reasons
                   if reason != "usable_for_exploration_but_not_confirmation"]
        reasons.extend(blocking)
        if common_missing:
            reasons.append("daily_price_use_specific_contract_incomplete")
        reasons.append("semantic_evidence_not_validated")
        reasons.append("research_input_sufficiency_unassessed")
        if intended_use is IntendedUse.REPLICATION:
            reasons.append("replication_independence_unassessed")

        eligibility = base.eligibility
        if missing:
            eligibility = (
                Eligibility.EXPLORATORY_ONLY
                if intended_use is IntendedUse.EXPLORATORY
                else Eligibility.PROHIBITED
            )
        if blocking:
            eligibility = Eligibility.PROHIBITED
            reasons = [
                reason for reason in reasons
                if reason != "usable_for_exploration_but_not_confirmation"
            ]
            missing.append("nonfatal_representative_price_content")
        output.append(
            {
                "data_view_id": view.data_view_id,
                "decision_scope": "daily_price_price_return_research",
                "intended_use": intended_use.value,
                "availability_confidence": availability.value,
                "point_in_time_reconstructable": point_in_time,
                "content_fingerprint": None,
                "probe_result_fingerprint": fingerprint,
                "content_fingerprint_scope": "missing_full_data_view_fingerprint",
                "extraction_version": context.extraction_version,
                "universe_version": view.universe_version,
                "entity_resolution_version": view.entity_resolution_version,
                "revision_lineage_available": False,
                "eligibility": eligibility.value,
                "research_input_permitted": False,
                "research_input_sufficiency": "unassessed",
                "observed_content_status": _content_summary(representative),
                "eligibility_scope": "declared_use_contract_only_not_sufficiency_or_authorization",
                "input_scope": "listed_representative_symbols_only",
                "permitted_symbols": [],
                "observed_nonfatal_symbols": nonfatal_symbols,
                "excluded_symbols": excluded_symbols,
                "reasons": reasons,
                "missing_requirements": missing,
                "claim_restriction": (
                    "Eligibility is a declared-use restriction, not research-input permission. "
                    "Nonfatal observations do not establish sufficiency; "
                    "no research input, experiment, or final basket is authorized. "
                    "No predictive, total-return, historical-universe, "
                    "confirmatory, or production-readiness claim."
                ),
            }
        )
    return output


def _gap(
    *,
    gap_id: str,
    title: str,
    research_need: str,
    requested: str,
    limitation: str,
    change_class: str,
    priority: str,
    history: str,
    alternatives: Sequence[str],
    acceptance_criteria: Sequence[str],
) -> dict[str, Any]:
    return {
        "gap_id": gap_id,
        "title": title,
        "proposal_type": "data_gap_or_opportunity",
        "research_need": research_need,
        "requested_data_or_transformation": requested,
        "current_limitation": limitation,
        "blocked_eligibility": (
            "all use while the snapshot is unobserved; confirmatory and replication "
            "use after observation"
        ),
        "change_class": change_class,
        "frequency": "daily for price/session data; event-time for corporate actions",
        "history": history,
        "universe": "all StockVis-tracked assets, retaining inactive and zero-row entities",
        "reusability": (
            "Reusable across single-asset, cross-sectional, corporate-action, "
            "and market-system Math Lab cases."
        ),
        "expected_cost": {
            "api": "unknown pending provider/licensing evaluation",
            "storage": "unknown pending retained-vintage design",
            "compute": "low-to-medium for incremental validation",
            "engineering": "requires scoped design and pilot estimate",
        },
        "alternatives": list(alternatives),
        "priority": priority,
        "lead_recommendation": (
            "Prohibit use of an unobserved snapshot; after observation, keep affected "
            "research exploratory-only until this gap closes. Pilot an additive "
            "read-only research export before proposing production schema changes."
        ),
        "acceptance_criteria": list(acceptance_criteria),
        "evidence": {
            "source": "readiness probe schema inventory",
            "live_data_completeness": "not established by column presence",
        },
        "uncertainty": [
            "Provider capability, license, engineering effort, and historical coverage remain unassessed."
        ],
        "decision_authority": (
            "Delegated for a small reversible pilot; escalate material purchase, "
            "large backfill, licensing risk, or production schema change."
        ),
        "reconsideration_trigger": "rerun after an immutable sample export passes adversarial checks",
    }


def _data_gap_proposals(schema: Mapping[str, set[str]]) -> list[dict[str, Any]]:
    schema_presence = _daily_price_schema_presence(schema)
    semantic_evidence_validated = {
        name: False
        for name in (
            "available_at",
            "provider_provenance",
            "adjustment_semantics",
            "historical_dividend_ledger",
            "revision_lineage",
            "entity_lifecycle",
            "terminal_return",
            "exchange_calendar",
        )
    }
    proposals: list[dict[str, Any]] = [
        _gap(
            gap_id="DG-DP-EXPORT-001",
            title="Sealed and reconstructable DailyPrice research export",
            research_need="Bind material experiments to the complete rows they consumed, not only readiness aggregates.",
            requested="Create a bounded immutable export manifest with query/version, cutoff, row-level content hash, schema, and artifact digest.",
            limitation="The readiness fingerprint covers aggregate findings and cannot reconstruct the full experimental Data View.",
            change_class="transformation",
            priority="Required",
            history="per material experiment snapshot, with retained manifest and content-addressed artifact",
            alternatives=("Keep work exploratory and attach the exact bounded extract to each run.",),
            acceptance_criteria=(
                "the full consumed row set reproduces from the manifest",
                "any row/value/schema change produces a different content fingerprint",
            ),
        )
    ]
    if not semantic_evidence_validated["available_at"]:
        proposals.append(
            _gap(
                gap_id="DG-DP-AVAILABLE-AT-001",
                title="Market-session availability timestamp contract",
                research_need="Prevent close/session timing leakage in historical research.",
                requested="Add or reconstruct source available_at with exchange timezone and session rule.",
                limitation="DailyPrice.date is effective time and created_at is ingestion time; neither proves when a bar became usable.",
                change_class="provenance_improvement",
                priority="Required",
                history="full retained DailyPrice history",
                alternatives=("Use a conservative next-session lag for exploratory work.",),
                acceptance_criteria=(
                    "effective_time, available_at, and recorded_at are separately exported",
                    "DST, early-close, and after-close cases pass timing tests",
                ),
            )
        )
    if not semantic_evidence_validated["provider_provenance"]:
        proposals.append(
            _gap(
                gap_id="DG-DP-PROVENANCE-001",
                title="Row-level DailyPrice provider ancestry",
                research_need="Identify which source and ingestion path produced every OHLCV row.",
                requested="Retain provider, provider record key/version, extraction run, and source payload fingerprint.",
                limitation="DailyPrice has no provider/source column and update paths can share or change ancestry silently.",
                change_class="provenance_improvement",
                priority="Required",
                history="full history including backfills and overwritten overlaps",
                alternatives=("Seal provider-specific research exports outside the production schema.",),
                acceptance_criteria=(
                    "every exported row resolves to one declared source ancestry",
                    "shared ancestry is visible during replication evaluation",
                ),
            )
        )
    if not semantic_evidence_validated["adjustment_semantics"]:
        proposals.append(
            _gap(
                gap_id="DG-DP-ADJUSTMENT-001",
                title="Raw, split-adjusted, and total-return price contract",
                research_need="Compute returns without silently mixing corporate-action conventions.",
                requested="Version raw OHLC, split factors, adjusted price transformation, and total-return reinvestment convention.",
                limitation="The stored close has no adjustment flag; repository ingestion text says adjClose is not used, but rows cannot prove semantics.",
                change_class="transformation",
                priority="Required",
                history="full history across all recorded corporate actions",
                alternatives=("Restrict exploration to explicitly raw price levels and event-window diagnostics.",),
                acceptance_criteria=(
                    "split dates reconcile to versioned adjustment factors",
                    "raw and adjusted series remain separately reproducible",
                ),
            )
        )
    if not semantic_evidence_validated["historical_dividend_ledger"]:
        proposals.append(
            _gap(
                gap_id="DG-DP-DIVIDEND-001",
                title="Complete point-in-time dividend and total-return history",
                research_need="Evaluate dividend-sensitive assets and total-return targets.",
                requested="Backfill ex-date, record date, payment date, amount, currency, source vintage, and correction lineage.",
                limitation="CalendarEvent is an operational window and is not evidence of complete historical dividends.",
                change_class="backfill",
                priority="Required",
                history="maximum provider history with completeness metrics by asset",
                alternatives=("Exclude total-return claims and label dividend checks unassessed.",),
                acceptance_criteria=(
                    "coverage and missingness are quantified against an independent event sample",
                    "reinvestment convention is versioned and reproducible",
                ),
            )
        )
    if not semantic_evidence_validated["revision_lineage"]:
        proposals.append(
            _gap(
                gap_id="DG-DP-REVISION-001",
                title="DailyPrice correction and vintage lineage",
                research_need="Reconstruct what values were stored and available for past experiments.",
                requested="Retain immutable vintages or before/after revisions with supersession reason and time.",
                limitation="Conflict updates can replace OHLCV without retaining the previous value or update timestamp.",
                change_class="provenance_improvement",
                priority="High Value",
                history="all future updates plus a measured re-extraction sample",
                alternatives=("Use sealed exports and periodically diff their fingerprints.",),
                acceptance_criteria=(
                    "a prior research snapshot can be reconstructed exactly",
                    "correction rate and affected rows are measurable",
                ),
            )
        )
    if not semantic_evidence_validated["entity_lifecycle"]:
        proposals.append(
            _gap(
                gap_id="DG-DP-ENTITY-001",
                title="Point-in-time ticker and entity lifecycle",
                research_need="Avoid ticker reuse, successor, merger, and spin-off identity errors.",
                requested="Add stable entity IDs and dated symbol/share-class/merger/spin-off successor edges.",
                limitation="Current symbol primary keys and current metadata cannot reconstruct historical identity.",
                change_class="new_collection",
                priority="High Value",
                history="full available entity history including inactive securities",
                alternatives=("Restrict scope to assets and dates manually verified for identity continuity.",),
                acceptance_criteria=(
                    "ticker changes and reused symbols resolve by effective date",
                    "merger and spin-off continuity has explicit policy tests",
                ),
            )
        )
    if not semantic_evidence_validated["terminal_return"]:
        proposals.append(
            _gap(
                gap_id="DG-DP-TERMINAL-RETURN-001",
                title="Delisting and terminal-return history",
                research_need="Measure survivorship-safe returns and terminal outcomes.",
                requested="Collect delisting date, reason, cash/stock consideration, terminal price/return, and source vintage.",
                limitation="No supported ledger distinguishes a stale tail from suspension, acquisition, or delisting.",
                change_class="new_collection",
                priority="High Value",
                history="full historical universe including inactive and acquired assets",
                alternatives=("Prohibit survivorship-sensitive confirmation and report stale tails separately.",),
                acceptance_criteria=(
                    "inactive assets remain in frozen universe denominators",
                    "terminal-return cases reconcile to event terms",
                ),
            )
        )
    if not semantic_evidence_validated["exchange_calendar"]:
        proposals.append(
            _gap(
                gap_id="DG-DP-CALENDAR-001",
                title="Versioned exchange-session calendar",
                research_need="Separate holidays and early closes from missing bars or suspensions.",
                requested="Provide versioned sessions by exchange, timezone, close time, holiday, and early-close status.",
                limitation="The current probe can calculate only a weekday proxy, not true missing business sessions.",
                change_class="transformation",
                priority="High Value",
                history="all DailyPrice coverage dates",
                alternatives=("Keep the weekday metric explicitly labeled as a non-authoritative proxy.",),
                acceptance_criteria=(
                    "known holidays and early closes are not flagged as gaps",
                    "exchange mapping and calendar version are present in each export",
                ),
            )
        )
    for proposal in proposals:
        proposal["evidence"]["schema_presence_only"] = schema_presence
        proposal["evidence"]["semantic_evidence_validated"] = False
    return proposals


def _unobserved_representative_rows() -> list[dict[str, Any]]:
    return [
        {
            "symbol": symbol,
            "observation_status": "not_observed",
            "observed_content_status": "not_observed",
            "research_input_sufficiency": "unassessed",
            "stock_exists": None,
            "asset_type": None,
            "exchange": None,
            "sector": None,
            "industry": None,
            "stock_currency": None,
            "stock_created_at": None,
            "daily_price_row_count": None,
            "min_date": None,
            "max_date": None,
            "daily_price_recorded_at_min": None,
            "daily_price_recorded_at_max": None,
            "daily_price_currencies": None,
            "currency_mismatch_row_count": None,
            "weekday_gap_proxy": None,
            "anomalies": None,
            "stock_split_observation_status": "not_observed",
            "stock_split_count": None,
            "stock_split_first_date": None,
            "stock_split_last_date": None,
            "dividend_observation_status": "not_observed",
            "dividend_event_count": None,
            "dividend_event_first_date": None,
            "dividend_event_last_date": None,
            "selection_status": "deferred",
            "reason_codes": ["database_probe_unavailable"],
        }
        for symbol in REPRESENTATIVE_BASKET
    ]


def _unavailable_decisions(
    context: ProbeContext,
    representative: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    missing = [
        "observed_database_snapshot",
        "point_in_time_reconstructability",
        "sufficient_availability_confidence",
        "content_fingerprint",
        "daily_price_provider_provenance",
        "price_adjustment_semantics",
        "revision_lineage",
        "entity_resolution_version",
    ]
    output: list[dict[str, Any]] = []
    for intended_use in IntendedUse:
        use_missing = list(missing)
        if intended_use is IntendedUse.REPLICATION:
            use_missing.append("replication_independence_evidence")
        output.append(
            {
                "data_view_id": f"stockvis.daily_price:{context.run_id}:{intended_use.value}",
                "decision_scope": "daily_price_price_return_research",
                "decision_source": "readiness_adapter_precondition",
                "intended_use": intended_use.value,
                "availability_confidence": AvailabilityConfidence.UNKNOWN.value,
                "point_in_time_reconstructable": False,
            "content_fingerprint": None,
                "probe_result_fingerprint": None,
                "content_fingerprint_scope": "not_available",
                "extraction_version": context.extraction_version,
                "universe_version": "daily_price_validation_basket_v0.1",
                "entity_resolution_version": None,
                "revision_lineage_available": False,
                "eligibility": Eligibility.PROHIBITED.value,
                "research_input_permitted": False,
                "research_input_sufficiency": "unassessed",
                "observed_content_status": _content_summary(representative),
                "eligibility_scope": "declared_use_contract_only_not_sufficiency_or_authorization",
                "input_scope": "listed_representative_symbols_only",
                "permitted_symbols": [],
                "observed_nonfatal_symbols": _observed_content_scope(representative)[0],
                "excluded_symbols": _observed_content_scope(representative)[1],
                "reasons": [
                    "incomplete_snapshot" if representative else "database_snapshot_not_observed",
                    "research_input_sufficiency_unassessed",
                ],
                "missing_requirements": use_missing,
                "claim_restriction": "Research input is not permitted; snapshot evidence is incomplete and sufficiency remains unassessed.",
            }
        )
    return output


def _unavailable_adversarial_discovery(
    *,
    status: str = "not_run",
    limitation: str = (
        "Database access failed before live rows or deployed schema could be observed."
    ),
) -> list[dict[str, Any]]:
    return [
        {
            "failure_mode": mode,
            "status": status,
            "selection_method": method,
            "candidates": [],
            "limitations": [limitation],
        }
        for mode, method in (
            ("recorded_repeated_split", "rank StockSplit event count"),
            ("recorded_large_or_reverse_split", "rank split adjustment factor"),
            ("dividend_history", "rank historical dividend events"),
            ("ipo_or_short_history", "rank DailyPrice coverage ascending"),
            (
                "long_missing_period_or_suspension",
                "rank exchange-session coverage gaps",
            ),
            ("ohlcv_integrity", "rank structural OHLCV anomaly counts"),
            ("ticker_change", "resolve point-in-time symbol lifecycle"),
            ("merger_or_acquisition", "resolve acquisition lifecycle events"),
            ("spin_off", "resolve spin-off lifecycle events"),
            (
                "delisting_or_terminal_return",
                "resolve delisting and terminal-return events",
            ),
        )
    ]


def _access_gap() -> dict[str, Any]:
    proposal = _gap(
        gap_id="DG-DP-ACCESS-001",
        title="Read-only production snapshot access for readiness execution",
        research_need="Observe deployed DailyPrice coverage and failure modes without write authority.",
        requested="Provide a runner-reachable PostgreSQL endpoint and SELECT-only role or operator-run sealed export.",
        limitation="The restricted execution environment could not establish a database connection, so no live row or migration state was observed.",
        change_class="provenance_improvement",
        priority="Required",
        history="one current snapshot first; repeatable dated snapshots thereafter",
        alternatives=(
            "Run the committed probe from an authorized host and return its immutable artifacts.",
            "Provide a sealed read-only export with schema and extraction metadata.",
        ),
        acceptance_criteria=(
            "transaction_read_only is verified on before the first probe SELECT",
            "all six representative rows and every adversarial failure mode have terminal statuses",
            "snapshot content fingerprint and extraction cutoff are recorded",
        ),
    )
    proposal["frequency"] = "on readiness rerun and after material schema/source changes"
    proposal["universe"] = "declared representative basket plus full candidate universe aggregates"
    proposal["expected_cost"] = {
        "api": "none if direct read-only DB access is approved",
        "storage": "low for aggregate artifacts or bounded sealed export",
        "compute": "low for indexed aggregates; validate on production scale",
        "engineering": "low-to-medium environment and role configuration",
    }
    return proposal


def _query_gap(stage: str, error_type: str) -> dict[str, Any]:
    proposal = _gap(
        gap_id="DG-DP-QUERY-001",
        title="Complete bounded readiness query on the deployed snapshot",
        research_need="Reach a terminal status for every representative and adversarial check in one consistent snapshot.",
        requested="Diagnose the failed query stage, bound its cost, and rerun the same extraction version in repeatable-read mode.",
        limitation=f"The {stage} stage failed with {error_type}; later checks were not executed.",
        change_class="transformation",
        priority="Required",
        history="same snapshot/cutoff as the failed readiness run where possible",
        alternatives=(
            "Run an equivalent operator-reviewed SELECT and return a sealed result.",
            "Reduce only the candidate output limit while preserving the frozen denominator.",
        ),
        acceptance_criteria=(
            "the stage completes within the declared statement timeout",
            "completed earlier stages remain byte-for-byte reproducible",
            "no denominator or failed candidate is silently dropped",
        ),
    )
    proposal["frequency"] = "once per failed extraction version, then on material query/schema changes"
    return proposal


def _query_failure_artifacts(
    *,
    session: ReadOnlySession,
    context: ProbeContext,
    stage: str,
    error: Exception,
    schema: Mapping[str, set[str]] | None,
    representative: list[dict[str, Any]] | None,
) -> ReadinessArtifacts:
    observed_schema = dict(schema or {})
    data_gaps = [
        _query_gap(stage, type(error).__name__),
        *_data_gap_proposals(observed_schema or REPOSITORY_SCHEMA_EVIDENCE),
    ]
    adversarial = _unavailable_adversarial_discovery(
        status="not_run_due_query_failure",
        limitation=(
            f"The {stage} stage failed; candidates from unfinished queries were not inferred."
        ),
    )
    representative_rows = representative or _unobserved_representative_rows()
    representative_observed = representative is not None
    result = {
        "schema_version": "daily-price-readiness-result/0.3",
        "job_id": context.job_id,
        "run_id": context.run_id,
        "status": "partial",
        "generated_at": context.observed_at.astimezone(timezone.utc).isoformat(),
        "inventory_permission": _inventory_permission(session.read_only_verified),
        "authority_references": list(AUTHORITY_REFERENCES),
        "probe": {
            "database_status": "query_failed",
            "database_target": context.database_target,
            "read_only_requested": True,
            "read_only_verified": True,
            "read_only_evidence": dict(session.read_only_evidence),
            "extraction_version": context.extraction_version,
            "calendar_contract": (
                "weekday_proxy_not_exchange_calendar"
                if representative_observed
                else "not_executed"
            ),
            "readiness_result_fingerprint": None,
        },
        "findings": {
            "summary": {
                "representative_candidate_count": len(REPRESENTATIVE_BASKET),
                "representative_candidates_observed": (
                    len(REPRESENTATIVE_BASKET) if representative_observed else 0
                ),
                "representative_candidates_deferred": sum(
                    row["selection_status"] == "deferred"
                    for row in representative_rows
                ),
                "adversarial_failure_modes_assessed": 0,
                "adversarial_failure_modes_not_run": len(adversarial),
                "confirmatory_safe": False,
                "overall_decision": "retain_completed_evidence_and_defer_incomplete_stages",
            },
            "representative_basket": representative_rows,
            "adversarial_candidate_discovery": adversarial,
            "data_eligibility_decisions": _unavailable_decisions(context, representative_rows),
            "schema_capabilities": {
                table: sorted(columns)
                for table, columns in sorted(observed_schema.items())
            },
            "daily_price_schema_presence": (
                _daily_price_schema_presence(observed_schema)
                if observed_schema
                else {
                    key: "not_observed"
                    for key in _daily_price_schema_presence(REPOSITORY_SCHEMA_EVIDENCE)
                }
            ),
        },
        "failures": [
            {
                "stage": stage,
                "status": "failed",
                "error_type": type(error).__name__,
                "message": redact_error_message(str(error)),
                "consequence": (
                    "Completed earlier stages were retained; unfinished findings "
                    "were marked not run and cannot support eligibility."
                ),
            }
        ],
        "uncertainties": [
            {
                "code": "incomplete_consistent_snapshot",
                "detail": "No complete readiness result fingerprint was created from the failed staged run.",
            },
            {
                "code": "partial_evidence_scope",
                "detail": (
                    "Only stages explicitly marked observed are evidence; later "
                    "candidate lists remain unknown."
                ),
            },
        ],
        "data_gap_ids": [gap["gap_id"] for gap in data_gaps],
    }
    return ReadinessArtifacts(result=result, data_gaps=data_gaps)


def build_unavailable_artifacts(
    context: ProbeContext,
    *,
    error_type: str,
    error_message: str,
    failure_stage: str = "database_connection",
) -> ReadinessArtifacts:
    """Return complete, explicit artifacts when no database snapshot was observed."""

    data_gaps = [_access_gap(), *_data_gap_proposals(REPOSITORY_SCHEMA_EVIDENCE)]
    for gap in data_gaps[1:]:
        gap["evidence"] = {
            "source": (
                "repository models/migrations: packages/shared/stocks/models.py and "
                "packages/shared/stocks/migrations"
            ),
            "live_schema_status": "unverified_due_database_connection_failure",
        }
    adversarial = _unavailable_adversarial_discovery()
    result = {
        "schema_version": "daily-price-readiness-result/0.3",
        "job_id": context.job_id,
        "run_id": context.run_id,
        "status": "partial",
        "generated_at": context.observed_at.astimezone(timezone.utc).isoformat(),
        "inventory_permission": _inventory_permission(False),
        "authority_references": list(AUTHORITY_REFERENCES),
        "probe": {
            "database_status": "unavailable",
            "database_target": context.database_target,
            "read_only_requested": True,
            "read_only_verified": False,
            "read_only_evidence": {
                "connection_established": False,
                "transaction_read_only": "not_observed",
                "client_sql_guard": True,
                "rollback_on_exit": True,
            },
            "extraction_version": context.extraction_version,
            "calendar_contract": "not_executed",
        },
        "findings": {
            "summary": {
                "representative_candidate_count": len(REPRESENTATIVE_BASKET),
                "representative_candidates_observed": 0,
                "representative_candidates_deferred": len(REPRESENTATIVE_BASKET),
                "adversarial_failure_modes_assessed": 0,
                "adversarial_failure_modes_not_run": len(adversarial),
                "confirmatory_safe": False,
                "overall_decision": "defer_final_basket_and_prohibit_data_use",
            },
            "representative_basket": _unobserved_representative_rows(),
            "adversarial_candidate_discovery": adversarial,
            "data_eligibility_decisions": _unavailable_decisions(context),
            "schema_capabilities": {},
            "daily_price_schema_presence": {
                key: "live_schema_unverified"
                for key in _daily_price_schema_presence(REPOSITORY_SCHEMA_EVIDENCE)
            },
            "repository_schema_evidence": {
                "observation_status": "repository_code_only_live_schema_unverified",
                "tables": {
                    table: sorted(columns)
                    for table, columns in sorted(REPOSITORY_SCHEMA_EVIDENCE.items())
                },
                "schema_presence_from_code": _daily_price_schema_presence(
                    REPOSITORY_SCHEMA_EVIDENCE
                ),
            },
        },
        "failures": [
            {
                "stage": failure_stage,
                "status": "failed",
                "error_type": error_type,
                "message": redact_error_message(error_message),
                "consequence": "No live schema or DailyPrice rows were observed.",
            }
        ],
        "uncertainties": [
            {
                "code": "live_database_state_unknown",
                "detail": "Row counts, coverage, anomalies, deployed migrations, and adversarial candidates are unobserved.",
            },
            {
                "code": "repository_schema_is_not_live_schema",
                "detail": "Model and migration inspection supports gap proposals but cannot prove deployed schema or data contents.",
            },
            {
                "code": "history_threshold_not_precommitted",
                "detail": "No sufficient-history threshold was invented before observing the readiness distribution.",
            },
        ],
        "data_gap_ids": [gap["gap_id"] for gap in data_gaps],
    }
    return ReadinessArtifacts(result=result, data_gaps=data_gaps)


def _display(value: Any) -> str:
    if value is None:
        return "not observed"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown_report(artifacts: ReadinessArtifacts) -> str:
    """Render the machine result as a concise human audit report."""

    result = redact_persisted_errors(artifacts.result)
    probe = result["probe"]
    findings = result["findings"]
    lines = [
        "# DailyPrice Readiness Probe v0.3",
        "",
        f"- Job: `{result['job_id']}`",
        f"- Run: `{result['run_id']}`",
        f"- Status: `{result['status']}`",
        f"- Database: `{probe['database_status']}` ({_display(probe['database_target'])})",
        f"- Read-only transaction verified: `{_display(probe['read_only_verified'])}`",
        f"- Extraction version: `{probe['extraction_version']}`",
        f"- Inventory / diagnostic permission: `{result['inventory_permission']['status']}` (not research-input permission)",
        "",
        "This is a data-readiness inventory only. No predictive-validity, tradability, or production-readiness claim is made.",
        "Observed nonfatal content and exploratory eligibility do not establish research input sufficiency or permission.",
        "",
        "## Representative basket",
        "",
        "| Symbol | Observation | Stock | Sector / Industry | DailyPrice rows | Date range | Weekday proxy gaps | Anomaly flags | Selection |",
        "|---|---|---:|---|---:|---|---:|---:|---|",
    ]
    for row in findings["representative_basket"]:
        weekday = row.get("weekday_gap_proxy")
        anomalies = row.get("anomalies")
        anomaly_total = sum(anomalies.values()) if anomalies is not None else None
        observation = row.get(
            "observation_status",
            "observed" if row.get("stock_exists") is not None else "not observed",
        )
        lines.append(
            "| {symbol} | {observation} | {stock} | {sector} / {industry} | {rows} | {minimum} → {maximum} | {gaps} | {anomalies} | {selection} ({reasons}) |".format(
                symbol=_display(row["symbol"]),
                observation=_display(observation),
                stock=_display(row.get("stock_exists")),
                sector=_display(row.get("sector")),
                industry=_display(row.get("industry")),
                rows=_display(row.get("daily_price_row_count")),
                minimum=_display(row.get("min_date")),
                maximum=_display(row.get("max_date")),
                gaps=_display(weekday.get("missing_weekdays") if weekday else None),
                anomalies=_display(anomaly_total),
                selection=_display(row.get("selection_status")),
                reasons=", ".join(row.get("reason_codes", [])),
            )
        )
    lines.extend(
        [
            "",
            "The missing-session metric is a weekday proxy, not an exchange-calendar business-day result.",
            "",
            "## Adversarial candidate discovery",
            "",
            "| Failure mode | Status | Candidates | Limitation |",
            "|---|---|---|---|",
        ]
    )
    for item in findings["adversarial_candidate_discovery"]:
        candidates = ", ".join(
            str(candidate.get("symbol")) for candidate in item.get("candidates", [])
        ) or "none observed"
        lines.append(
            f"| {_display(item['failure_mode'])} | {_display(item['status'])} | "
            f"{_display(candidates)} | {_display(' '.join(item.get('limitations', [])))} |"
        )
    lines.extend(
        [
            "",
            "## Data Eligibility decisions",
            "",
            "| Declared use | Eligibility (not permission) | Observed content | Input sufficiency | Research input permitted | Permitted symbols | Availability | Point-in-time | Missing requirements |",
            "|---|---|---|---|---|---|---|---:|---|",
        ]
    )
    for decision in findings["data_eligibility_decisions"]:
        lines.append(
            f"| {_display(decision['intended_use'])} | {_display(decision['eligibility'])} | "
            f"{_display(decision['observed_content_status'])} | "
            f"{_display(decision['research_input_sufficiency'])} | "
            f"{_display(decision['research_input_permitted'])} | "
            f"{_display(', '.join(decision['permitted_symbols']) or 'none')} | "
            f"{_display(decision['availability_confidence'])} | "
            f"{_display(decision['point_in_time_reconstructable'])} | "
            f"{_display(', '.join(decision['missing_requirements']))} |"
        )
    lines.extend(
        [
            "",
            "## Data Gap / Opportunity proposals",
            "",
            "| ID | Priority | Proposal |",
            "|---|---|---|",
        ]
    )
    for gap in artifacts.data_gaps:
        lines.append(
            f"| {_display(gap['gap_id'])} | {_display(gap['priority'])} | {_display(gap['title'])} |"
        )
    lines.extend(["", "## Failures"])
    if result["failures"]:
        for failure in result["failures"]:
            lines.append(
                f"- `{failure['stage']}` / `{failure['error_type']}`: {failure['message']} "
                f"Consequence: {failure['consequence']}"
            )
    else:
        lines.append("- No probe execution failure was recorded.")
    lines.extend(["", "## Uncertainty"])
    for uncertainty in result["uncertainties"]:
        lines.append(f"- `{uncertainty['code']}`: {uncertainty['detail']}")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "Final basket inclusion remains deferred wherever evidence is missing. Confirmatory and replication use remain blocked unless their complete use-specific contracts are evidenced.",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    artifacts: ReadinessArtifacts,
    *,
    result_path: Path,
    data_gaps_path: Path,
    report_path: Path,
) -> None:
    """Write the three required artifacts as UTF-8 with deterministic JSON keys."""

    # Final common boundary also covers failures appended after probe return.
    artifacts = ReadinessArtifacts(
        result=redact_persisted_errors(artifacts.result),
        data_gaps=redact_persisted_errors(artifacts.data_gaps),
    )
    for path in (result_path, data_gaps_path, report_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(
            artifacts.result,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )
    data_gaps_path.write_text(
        json.dumps(
            artifacts.data_gaps,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
    )
    report_path.write_text(render_markdown_report(artifacts), encoding="utf-8")


def run_readiness_probe(
    session: ReadOnlySession, context: ProbeContext
) -> ReadinessArtifacts:
    """Inspect the declared basket without changing database state."""

    if not session.read_only_verified:
        raise ReadOnlySqlViolation(
            "database transaction did not prove transaction_read_only=on"
        )
    try:
        schema = _load_schema(session)
    except Exception as exc:
        return _query_failure_artifacts(
            session=session,
            context=context,
            stage="schema_inventory",
            error=exc,
            schema=None,
            representative=None,
        )
    missing_schema = {
        table: sorted(required - schema.get(table, set()))
        for table, required in _REQUIRED_TABLE_COLUMNS.items()
        if not required.issubset(schema.get(table, set()))
    }
    if missing_schema:
        error = RuntimeError(f"required DailyPrice schema is missing: {missing_schema}")
        return _query_failure_artifacts(
            session=session,
            context=context,
            stage="required_schema_validation",
            error=error,
            schema=schema,
            representative=None,
        )

    try:
        representative = _representative_rows(
            _metadata_rows(session, schema),
            _daily_rows(session),
            _split_summaries(session, schema),
            _dividend_summaries(session, schema),
        )
    except Exception as exc:
        return _query_failure_artifacts(
            session=session,
            context=context,
            stage="representative_basket",
            error=exc,
            schema=schema,
            representative=None,
        )
    try:
        adversarial = _discover_adversarial_candidates(session, schema, context)
    except Exception as exc:
        return _query_failure_artifacts(
            session=session,
            context=context,
            stage="adversarial_candidate_discovery",
            error=exc,
            schema=schema,
            representative=representative,
        )
    fingerprint = _content_fingerprint(
        {
            "schema": {table: sorted(columns) for table, columns in sorted(schema.items())},
            "representative_basket": representative,
            "adversarial_candidate_discovery": adversarial,
        }
    )
    eligibility = _eligibility_decisions(schema, context, fingerprint, representative)
    data_gaps = _data_gap_proposals(schema)
    result = {
        "schema_version": "daily-price-readiness-result/0.3",
        "job_id": context.job_id,
        "run_id": context.run_id,
        "status": "partial",
        "generated_at": context.observed_at.astimezone(timezone.utc).isoformat(),
        "inventory_permission": _inventory_permission(session.read_only_verified),
        "authority_references": list(AUTHORITY_REFERENCES),
        "probe": {
            "database_status": "available",
            "database_target": context.database_target,
            "read_only_requested": True,
            "read_only_verified": True,
            "read_only_evidence": dict(session.read_only_evidence),
            "extraction_version": context.extraction_version,
            "calendar_contract": "weekday_proxy_not_exchange_calendar",
            "readiness_result_fingerprint": fingerprint,
        },
        "findings": {
            "summary": {
                "representative_candidate_count": len(REPRESENTATIVE_BASKET),
                "representative_stock_rows_found": sum(
                    row["stock_exists"] for row in representative
                ),
                "representative_candidates_deferred": sum(
                    row["selection_status"] == "deferred" for row in representative
                ),
                "adversarial_failure_modes_assessed": sum(
                    item["status"] != "not_assessable" for item in adversarial
                ),
                "adversarial_failure_modes_not_assessable": sum(
                    item["status"] == "not_assessable" for item in adversarial
                ),
                "confirmatory_safe": False,
            },
            "representative_basket": representative,
            "adversarial_candidate_discovery": adversarial,
            "data_eligibility_decisions": eligibility,
            "schema_capabilities": {
                table: sorted(columns) for table, columns in sorted(schema.items())
            },
            "daily_price_schema_presence": _daily_price_schema_presence(schema),
        },
        "failures": [],
        "uncertainties": [
            {
                "code": "weekday_gap_is_not_exchange_calendar_gap",
                "detail": (
                    "Weekday absence includes exchange holidays and is only a proxy; "
                    "it cannot establish missing trading sessions or suspensions."
                ),
            },
            {
                "code": "history_threshold_not_precommitted",
                "detail": (
                    "The authority basket intentionally defers a sufficient-history "
                    "threshold until the readiness distribution is observed."
                ),
            },
        ],
        "data_gap_ids": [gap["gap_id"] for gap in data_gaps],
    }
    return ReadinessArtifacts(result=result, data_gaps=data_gaps)
