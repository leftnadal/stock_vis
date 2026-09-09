"""Command-line entry point for the DailyPrice read-only readiness probe."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Mapping, Sequence

from math_lab.runtime.error_redaction import redact_error_message

from math_lab.runtime.daily_price_readiness import (
    ProbeContext,
    ReadOnlySqlViolation,
    build_unavailable_artifacts,
    run_readiness_probe,
    validate_read_only_sql,
    write_artifacts,
)


DEFAULT_JOB_ID = "SV-MATH-DP-READINESS-001"


def postgres_connection_kwargs(
    environment: Mapping[str, str],
) -> dict[str, Any]:
    """Build psycopg connection arguments without logging their secret values."""

    return {
        "dbname": environment.get("DB_NAME")
        or environment.get("PGDATABASE")
        or "stock_vis",
        "user": environment.get("DB_USER")
        or environment.get("PGUSER")
        or getpass.getuser(),
        "password": environment.get("DB_PASSWORD")
        or environment.get("PGPASSWORD")
        or "",
        "host": environment.get("DB_HOST")
        or environment.get("PGHOST")
        or "localhost",
        "port": environment.get("DB_PORT")
        or environment.get("PGPORT")
        or "5432",
        "connect_timeout": int(environment.get("DB_CONNECT_TIMEOUT", "10")),
        "application_name": "stockvis_math_lab_daily_price_readiness",
        "options": (
            "-c default_transaction_read_only=on "
            "-c statement_timeout=30000 "
            "-c lock_timeout=2000"
        ),
    }


def database_target_from_environment(environment: Mapping[str, str]) -> str:
    """Return a credential-free endpoint label suitable for persisted artifacts."""

    kwargs = postgres_connection_kwargs(environment)
    host = str(kwargs["host"])
    if host.startswith("/"):
        return f"postgresql+unix://{host}/{kwargs['dbname']}"
    return f"postgresql://{host}:{kwargs['port']}/{kwargs['dbname']}"


class PostgresReadOnlySession:
    """A PostgreSQL transaction with both client and server read-only guards."""

    vendor = "postgresql"

    def __init__(
        self,
        connection_kwargs: Mapping[str, Any],
        *,
        connector: Callable[..., Any] | None = None,
    ) -> None:
        self._connection_kwargs = dict(connection_kwargs)
        self._connector = connector
        self._connection: Any = None
        self._cursor: Any = None
        self.read_only_verified = False
        self.read_only_evidence: dict[str, Any] = {
            "transaction_read_only": False,
            "client_sql_guard": True,
            "rollback_on_exit": True,
            "default_transaction_read_only_requested": True,
        }

    def __enter__(self) -> "PostgresReadOnlySession":
        connector = self._connector
        if connector is None:
            import psycopg2

            connector = psycopg2.connect
        try:
            self._connection = connector(**self._connection_kwargs)
            self._connection.set_session(
                isolation_level="REPEATABLE READ",
                readonly=True,
                autocommit=False,
            )
            self._cursor = self._connection.cursor()
            self._cursor.execute(
                "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
            )
            self._cursor.execute("SHOW transaction_read_only")
            observed = str(self._cursor.fetchone()[0]).lower()
            if observed not in {"on", "true", "1"}:
                raise ReadOnlySqlViolation(
                    "server did not confirm transaction_read_only=on"
                )
            self.read_only_verified = True
            self.read_only_evidence["transaction_read_only"] = True
            self._cursor.execute("SHOW transaction_isolation")
            isolation = str(self._cursor.fetchone()[0]).lower()
            if isolation != "repeatable read":
                raise ReadOnlySqlViolation(
                    "server did not confirm transaction_isolation=repeatable read"
                )
            self.read_only_evidence["transaction_isolation"] = isolation
            return self
        except Exception:
            self._cleanup(suppress_errors=True)
            raise

    def fetch_all(
        self, statement: str, params: Sequence[Any] = ()
    ) -> list[dict[str, Any]]:
        if not self.read_only_verified or self._cursor is None:
            raise ReadOnlySqlViolation(
                "probe SELECT attempted before transaction_read_only verification"
            )
        validate_read_only_sql(statement)
        postgres_statement = statement.replace("?", "%s")
        self._cursor.execute(postgres_statement, tuple(params))
        names = [
            description.name
            if hasattr(description, "name")
            else description[0]
            for description in self._cursor.description
        ]
        return [dict(zip(names, row, strict=True)) for row in self._cursor.fetchall()]

    def _cleanup(self, *, suppress_errors: bool = False) -> None:
        errors: list[Exception] = []
        connection = self._connection
        cursor = self._cursor
        if connection is not None:
            try:
                connection.rollback()
            except Exception as exc:
                errors.append(exc)
            if cursor is not None:
                try:
                    cursor.close()
                except Exception as exc:
                    errors.append(exc)
            try:
                connection.close()
            except Exception as exc:
                errors.append(exc)
        self._cursor = None
        self._connection = None
        self.read_only_verified = False
        if errors and not suppress_errors:
            raise errors[0]

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._cleanup(suppress_errors=exc is not None)


def _git_extraction_version() -> str:
    digest = hashlib.sha256()
    for path in sorted(
        (
            Path(__file__),
            Path(__file__).with_name("daily_price_readiness.py"),
            Path(__file__).with_name("data_eligibility.py"),
            Path(__file__).with_name("error_redaction.py"),
        ),
        key=lambda item: item.name,
    ):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    source_suffix = f"+probe-sha256:{digest.hexdigest()}"
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return f"git:{completed.stdout.strip()}{source_suffix}"
    except (OSError, subprocess.SubprocessError):
        return f"source:daily-price-readiness-result/0.2{source_suffix}"


def _aware_datetime(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--observed-at must include a timezone offset")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Probe StockVis DailyPrice readiness in a server-enforced read-only "
            "PostgreSQL transaction."
        )
    )
    parser.add_argument("--job-id", default=DEFAULT_JOB_ID)
    parser.add_argument(
        "--run-id", default=os.environ.get("LAB_AUTOMATION_RUN_ID", "manual")
    )
    parser.add_argument("--observed-at")
    parser.add_argument("--extraction-version", default=_git_extraction_version())
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--data-gaps-json", type=Path, required=True)
    parser.add_argument("--report-md", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    environment = dict(os.environ)
    context = ProbeContext(
        job_id=args.job_id,
        run_id=args.run_id,
        observed_at=_aware_datetime(args.observed_at),
        extraction_version=args.extraction_version,
        database_target=database_target_from_environment(environment),
    )
    connection_established = False
    artifacts = None
    try:
        with PostgresReadOnlySession(
            postgres_connection_kwargs(environment)
        ) as session:
            connection_established = True
            artifacts = run_readiness_probe(session, context)
        exit_code = (
            0 if artifacts.result["probe"]["database_status"] == "available" else 2
        )
    except Exception as exc:
        message = redact_error_message(str(exc), environment)
        if artifacts is not None and connection_established:
            artifacts.result["status"] = "partial"
            artifacts.result["probe"][
                "database_status"
            ] = "cleanup_failed_after_probe"
            artifacts.result["failures"].append(
                {
                    "stage": "database_cleanup",
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "message": message,
                    "consequence": (
                        "Completed probe findings were retained; connection cleanup "
                        "reported an error after the read-only queries finished."
                    ),
                }
            )
            artifacts.result["uncertainties"].append(
                {
                    "code": "database_cleanup_failure",
                    "detail": (
                        "The connection implementation attempted rollback and close; "
                        "operator logs should confirm resource cleanup."
                    ),
                }
            )
        else:
            artifacts = build_unavailable_artifacts(
                context,
                error_type=type(exc).__name__,
                error_message=message,
                failure_stage=(
                    "database_query"
                    if connection_established
                    else "database_connection"
                ),
            )
        exit_code = 2
    write_artifacts(
        artifacts,
        result_path=args.result_json,
        data_gaps_path=args.data_gaps_json,
        report_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "status": artifacts.result["status"],
                "database_status": artifacts.result["probe"]["database_status"],
                "result_json": str(args.result_json),
                "data_gaps_json": str(args.data_gaps_json),
                "report_md": str(args.report_md),
            },
            sort_keys=True,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
