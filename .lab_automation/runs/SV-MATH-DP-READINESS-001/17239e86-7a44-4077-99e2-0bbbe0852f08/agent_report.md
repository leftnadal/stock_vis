# DailyPrice Readiness Probe v0.1

- Job: `SV-MATH-DP-READINESS-001`
- Run: `17239e86-7a44-4077-99e2-0bbbe0852f08`
- Status: `partial`
- Database: `unavailable` (postgresql://localhost:5432/stock_vis)
- Read-only transaction verified: `no`
- Extraction version: `git:16a627df7db3406563e71342351745816c92af47+probe-sha256:064c8f3078e589f1e44e3ad0d59dc93c0da9ccb124d24024de53454dbb595dbb`

This is a data-readiness inventory only. No predictive-validity, tradability, or production-readiness claim is made.

## Representative basket

| Symbol | Observation | Stock | Sector / Industry | DailyPrice rows | Date range | Weekday proxy gaps | Anomaly flags | Selection |
|---|---|---:|---|---:|---|---:|---:|---|
| SPY | not_observed | not observed | not observed / not observed | not observed | not observed → not observed | not observed | not observed | deferred (database_probe_unavailable) |
| AAPL | not_observed | not observed | not observed / not observed | not observed | not observed → not observed | not observed | not observed | deferred (database_probe_unavailable) |
| JPM | not_observed | not observed | not observed / not observed | not observed | not observed → not observed | not observed | not observed | deferred (database_probe_unavailable) |
| XOM | not_observed | not observed | not observed / not observed | not observed | not observed → not observed | not observed | not observed | deferred (database_probe_unavailable) |
| WMT | not_observed | not observed | not observed / not observed | not observed | not observed → not observed | not observed | not observed | deferred (database_probe_unavailable) |
| UNH | not_observed | not observed | not observed / not observed | not observed | not observed → not observed | not observed | not observed | deferred (database_probe_unavailable) |

The missing-session metric is a weekday proxy, not an exchange-calendar business-day result.

## Adversarial candidate discovery

| Failure mode | Status | Candidates | Limitation |
|---|---|---|---|
| recorded_repeated_split | not_run | none observed | Database access failed before live rows or deployed schema could be observed. |
| recorded_large_or_reverse_split | not_run | none observed | Database access failed before live rows or deployed schema could be observed. |
| dividend_history | not_run | none observed | Database access failed before live rows or deployed schema could be observed. |
| ipo_or_short_history | not_run | none observed | Database access failed before live rows or deployed schema could be observed. |
| long_missing_period_or_suspension | not_run | none observed | Database access failed before live rows or deployed schema could be observed. |
| ohlcv_integrity | not_run | none observed | Database access failed before live rows or deployed schema could be observed. |
| ticker_change | not_run | none observed | Database access failed before live rows or deployed schema could be observed. |
| merger_or_acquisition | not_run | none observed | Database access failed before live rows or deployed schema could be observed. |
| spin_off | not_run | none observed | Database access failed before live rows or deployed schema could be observed. |
| delisting_or_terminal_return | not_run | none observed | Database access failed before live rows or deployed schema could be observed. |

## Data Eligibility decisions

| Declared use | Eligibility | Availability | Point-in-time | Missing requirements |
|---|---|---|---:|---|
| exploratory | prohibited_for_declared_use | unknown | no | observed_database_snapshot, point_in_time_reconstructability, sufficient_availability_confidence, content_fingerprint, daily_price_provider_provenance, price_adjustment_semantics, revision_lineage, entity_resolution_version |
| confirmatory | prohibited_for_declared_use | unknown | no | observed_database_snapshot, point_in_time_reconstructability, sufficient_availability_confidence, content_fingerprint, daily_price_provider_provenance, price_adjustment_semantics, revision_lineage, entity_resolution_version |
| replication | prohibited_for_declared_use | unknown | no | observed_database_snapshot, point_in_time_reconstructability, sufficient_availability_confidence, content_fingerprint, daily_price_provider_provenance, price_adjustment_semantics, revision_lineage, entity_resolution_version, replication_independence_evidence |

## Data Gap / Opportunity proposals

| ID | Priority | Proposal |
|---|---|---|
| DG-DP-ACCESS-001 | Required | Read-only production snapshot access for readiness execution |
| DG-DP-EXPORT-001 | Required | Sealed and reconstructable DailyPrice research export |
| DG-DP-AVAILABLE-AT-001 | Required | Market-session availability timestamp contract |
| DG-DP-PROVENANCE-001 | Required | Row-level DailyPrice provider ancestry |
| DG-DP-ADJUSTMENT-001 | Required | Raw, split-adjusted, and total-return price contract |
| DG-DP-DIVIDEND-001 | Required | Complete point-in-time dividend and total-return history |
| DG-DP-REVISION-001 | High Value | DailyPrice correction and vintage lineage |
| DG-DP-ENTITY-001 | High Value | Point-in-time ticker and entity lifecycle |
| DG-DP-TERMINAL-RETURN-001 | High Value | Delisting and terminal-return history |
| DG-DP-CALENDAR-001 | High Value | Versioned exchange-session calendar |

## Failures
- `database_connection` / `OperationalError`: connection to server at "localhost" (::1), port 5432 failed: Operation not permitted
	Is the server running on that host and accepting TCP/IP connections?
connection to server at "localhost" (127.0.0.1), port 5432 failed: Operation not permitted
	Is the server running on that host and accepting TCP/IP connections?
 Consequence: No live schema or DailyPrice rows were observed.

## Uncertainty
- `live_database_state_unknown`: Row counts, coverage, anomalies, deployed migrations, and adversarial candidates are unobserved.
- `repository_schema_is_not_live_schema`: Model and migration inspection supports gap proposals but cannot prove deployed schema or data contents.
- `history_threshold_not_precommitted`: No sufficient-history threshold was invented before observing the readiness distribution.

## Decision

Final basket inclusion remains deferred wherever evidence is missing. Confirmatory and replication use remain blocked unless their complete use-specific contracts are evidenced.

## Authority and implementation

All four required authority references were read in full:

- `math_lab/00_foundation/foundation_ko.md`
- `math_lab/01_operating_system/operating_model_ko.md`
- `math_lab/02_methodology/research_methodology_ko.md`
- `math_lab/05_validation/daily_price_validation_basket_v0_1_ko.md`

Implemented artifacts:

- `math_lab/runtime/daily_price_readiness.py`: guarded queries, representative and adversarial inventories, eligibility and gap decisions, serializers
- `math_lab/runtime/daily_price_probe.py`: read-only repeatable-read PostgreSQL runner and CLI
- `math_lab/runtime/test_daily_price_readiness.py`: unit, SQLite query-only integration, and fake PostgreSQL session tests
- `math_lab/05_validation/daily_price_readiness_probe_v0_1_ko.md`: durable Korean readiness decision record

The SQL guard allows one `SELECT` or `WITH ... SELECT` statement only. The runner requests `default_transaction_read_only=on`, explicitly starts `REPEATABLE READ READ ONLY`, and verifies both server settings before any data query. This run failed before a connection was established, so server-side read-only state is correctly recorded as unverified.

## Validation

- `python -m pytest math_lab/runtime/test_data_eligibility.py math_lab/runtime/test_daily_price_readiness.py -q` → 35 tests passed after the final wording/schema-label correction.
- `python -m compileall -q math_lab/runtime` → passed before the final correction and is rerun in final validation.
- Independent focused review found no remaining Critical or Important regression. Its 55-candidate stress check retained each of five missingness dimensions' top ten and was invariant to reversed input order.

Tests cover write-SQL rejection, read-only verification ordering, rollback/cleanup, partial-query evidence retention, schema-presence versus semantic-readiness separation, zero versus negative volume, weekday-proxy limitations, deterministic adversarial ranking, and artifact serialization. Passing these tests does not establish live DailyPrice readiness.

## Unsuccessful attempts retained

1. `pg_isready` against `localhost:5432` returned no response.
2. An initial Django diagnostic could not initialize because this job environment had no `SECRET_KEY`.
3. A retry with a test-only secret reached PostgreSQL connection setup but was denied by the sandbox with `Operation not permitted`.
4. The final CLI repeated the guarded connection attempt, serialized the `OperationalError`, wrote all required artifacts, and returned exit code 2.

No credentials or database rows were exposed. A connection-enabled rerun is required before representative coverage, deployed schema, anomaly counts, or adversarial candidates can be measured.
