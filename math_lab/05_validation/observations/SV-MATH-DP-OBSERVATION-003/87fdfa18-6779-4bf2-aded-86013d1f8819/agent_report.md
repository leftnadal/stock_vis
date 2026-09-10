# DailyPrice Readiness Probe v0.3

- Job: `SV-MATH-DP-OBSERVATION-003`
- Run: `87fdfa18-6779-4bf2-aded-86013d1f8819`
- Status: `partial`
- Database: `available` (postgresql://localhost:5432/stock_vis)
- Read-only transaction verified: `yes`
- Extraction version: `c9bd21effbf0f3b3c728bed97e64f5aca330304c`
- Inventory / diagnostic permission: `permitted_read_only` (not research-input permission)

This is a data-readiness inventory only. No predictive-validity, tradability, or production-readiness claim is made.
Observed nonfatal content and exploratory eligibility do not establish research input sufficiency or permission.

## Representative basket

| Symbol | Observation | Stock | Sector / Industry | DailyPrice rows | Date range | Weekday proxy gaps | Anomaly flags | Selection |
|---|---|---:|---|---:|---|---:|---:|---|
| SPY | observed | yes | ETF / Index Fund | 158 | 2025-10-20 → 2026-06-15 | 13 | 0 | eligible_for_distribution_review (history_sufficiency_threshold_not_precommitted) |
| AAPL | observed | yes | TECHNOLOGY / Consumer Electronics | 796 | 2023-07-10 → 2026-09-09 | 32 | 0 | eligible_for_distribution_review (history_sufficiency_threshold_not_precommitted) |
| JPM | observed | yes | Financial Services / Banks - Diversified | 796 | 2023-07-10 → 2026-09-09 | 32 | 0 | eligible_for_distribution_review (history_sufficiency_threshold_not_precommitted) |
| XOM | observed | yes | Energy / Oil & Gas Integrated | 796 | 2023-07-10 → 2026-09-09 | 32 | 0 | eligible_for_distribution_review (history_sufficiency_threshold_not_precommitted) |
| WMT | observed | yes | Consumer Defensive / not observed | 796 | 2023-07-10 → 2026-09-09 | 32 | 0 | deferred (sector_or_industry_missing) |
| UNH | observed | yes | Healthcare / Medical - Healthcare Plans | 796 | 2023-07-10 → 2026-09-09 | 32 | 0 | eligible_for_distribution_review (history_sufficiency_threshold_not_precommitted) |

The missing-session metric is a weekday proxy, not an exchange-calendar business-day result.

## Adversarial candidate discovery

| Failure mode | Status | Candidates | Limitation |
|---|---|---|---|
| recorded_repeated_split | completed_recorded_events_only | NVDA, AAPL, GOOGL, TSLA | Absence from StockSplit does not establish that no split occurred. Recorded events may share a single provider ancestry. |
| recorded_large_or_reverse_split | completed_recorded_events_only | GOOGL, NVDA, AAPL, TSLA | Price discontinuities around split dates were not classified by this readiness probe. |
| dividend_history | completed_with_operational_event_window | SATA, BMNP, MSIF, AMIVF, BOWFF, FCMGF, FRMUF, ITUB, MAIN, TBCRF | CalendarEvent is not demonstrated to be a complete historical dividend ledger. |
| ipo_or_short_history | completed_with_short_history_proxy | BF.B, BRK.B, GEVG, IREG, OKLL, PAL, SMR, XE, WBA, IPG | Short coverage cannot be classified as IPO history without point-in-time listing metadata. |
| long_missing_period_or_suspension | completed_with_weekday_proxy | A, SPY, RDDT, WBA, AAPL, IONQ, IPG, VMRK, ABBV, FI, IREN, ABNB, BK, K, TLN, DAY, ABT, MMC, AAP, ACGL, HOLX, ACN, SATS, ABBNY, ADBE, CTRA, ABCB, ADI, CAG, ABSI, ADM, CPB | The proxy includes exchange holidays and cannot distinguish suspensions from ingestion gaps. |
| ohlcv_integrity | completed | HKHC, SKYT, CTRA, WBA | Passing structural bounds does not establish correct prices or adjustment semantics. |
| ticker_change | not_assessable | none observed | No supported point-in-time entity/corporate-action ledger was found; current symbols cannot establish historical identity events. |
| merger_or_acquisition | not_assessable | none observed | No supported point-in-time entity/corporate-action ledger was found; current symbols cannot establish historical identity events. |
| spin_off | not_assessable | none observed | No supported point-in-time entity/corporate-action ledger was found; current symbols cannot establish historical identity events. |
| delisting_or_terminal_return | not_assessable | none observed | No supported point-in-time entity/corporate-action ledger was found; current symbols cannot establish historical identity events. |

## Data Eligibility decisions

| Declared use | Eligibility (not permission) | Observed content | Input sufficiency | Research input permitted | Permitted symbols | Availability | Point-in-time | Missing requirements |
|---|---|---|---|---|---|---|---:|---|
| exploratory | exploratory_only | nonfatal_observed | unassessed | no | none | unknown | no | point_in_time_reconstructability, sufficient_availability_confidence, content_fingerprint, sealed_data_view_fingerprint, daily_price_provider_provenance, price_adjustment_semantics, revision_lineage, entity_resolution_version |
| confirmatory | prohibited_for_declared_use | nonfatal_observed | unassessed | no | none | unknown | no | point_in_time_reconstructability, sufficient_availability_confidence, content_fingerprint, sealed_data_view_fingerprint, daily_price_provider_provenance, price_adjustment_semantics, revision_lineage, entity_resolution_version |
| replication | prohibited_for_declared_use | nonfatal_observed | unassessed | no | none | unknown | no | point_in_time_reconstructability, sufficient_availability_confidence, content_fingerprint, sealed_data_view_fingerprint, daily_price_provider_provenance, price_adjustment_semantics, revision_lineage, entity_resolution_version, replication_independence_evidence |

## Data Gap / Opportunity proposals

| ID | Priority | Proposal |
|---|---|---|
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
- No probe execution failure was recorded.

## Uncertainty
- `weekday_gap_is_not_exchange_calendar_gap`: Weekday absence includes exchange holidays and is only a proxy; it cannot establish missing trading sessions or suspensions.
- `history_threshold_not_precommitted`: The authority basket intentionally defers a sufficient-history threshold until the readiness distribution is observed.

## Decision

Final basket inclusion remains deferred wherever evidence is missing. Confirmatory and replication use remain blocked unless their complete use-specific contracts are evidenced.
