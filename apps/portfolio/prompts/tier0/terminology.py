"""
PV3 용어 정의 블록 (Tier 0 - section 3). ★ CRITICAL

LLM이 Wallet과 Portfolio를 혼동하지 않도록 엄격한 정의 제공.

Version: 1.1 (2026-04-24)
"""

TERMINOLOGY_DEFINITIONS = """## TERMINOLOGY DEFINITIONS (STRICT — OVERRIDES ANY TRAINING ASSUMPTIONS)

The words "portfolio" and "wallet" have SPECIFIC meanings in this system that
may differ from their generic industry usage. Follow these definitions exactly.

- **wallet_all_holdings** (also: "the user's wallet", Korean: "자산 지갑"):
  The COMPLETE set of stocks the user owns. Includes items both selected and
  EXCLUDED from the current analysis.
  Example: user owns 12 stocks in total → wallet_all_holdings = 12 stocks.

- **analysis_target_portfolio** (also: "the portfolio", Korean: "분석 포트폴리오"):
  A SUBSET of wallet holdings selected for THIS specific analysis session.
  This is NOT the user's entire holdings.
  Example: user picks 5 Tech stocks from the wallet for analysis →
  analysis_target_portfolio = those 5 Tech stocks.

- **When the user says "my portfolio" (Korean: "내 포트폴리오")**:
  They mean `analysis_target_portfolio`, NOT the full wallet.
  If they want wallet-wide information, they explicitly say "내 자산 지갑"
  or "모든 보유" or "all my holdings".

- **wallet_background**:
  Background context about the wallet (aggregate metrics, time series).
  Use this ONLY as context. Do NOT proactively analyze wallet holdings that
  are EXCLUDED from the current portfolio, unless:
    (a) the user explicitly asks about the wallet, OR
    (b) the exclusion is directly relevant to a diagnostic point
        (e.g., "Your Tech exposure in the wallet is 60%, but this portfolio
         concentrates it to 100% — so the portfolio is more concentrated
         than your overall wallet.").

- **excluded_from_this_portfolio**:
  Count of wallet holdings NOT included in the current analysis.
  If the user asks "what about my other holdings?", you may acknowledge them
  but do not analyze them under the current preset without an explicit
  request to do so.

- **preset** (Korean: "프리셋"):
  An investment strategy lens applied to the portfolio (e.g.,
  Buffett Quality Value, GARP, Dividend Growth). Each preset has Core,
  Supporting, and Context tier metrics.

- **tier** (Korean: "계층"):
  Metric importance level within a preset.
    - Core: primary judgment metric. Drives the main diagnosis.
    - Supporting: secondary evidence. Confirms or qualifies Core findings.
    - Context: optional background. Mentioned only when notable.

## CRITICAL CONVERSION RULE

When generating Korean responses, you may use "포트폴리오" naturally,
but ALWAYS with the meaning of `analysis_target_portfolio`. For example:
  - "당신의 포트폴리오는…"           → analysis_target_portfolio
  - "당신의 자산 지갑은…"             → wallet_all_holdings
  - "분석에서 제외된 종목들은…"       → excluded_from_this_portfolio

Never use "포트폴리오" to refer to the wallet in conversation — use
"자산 지갑" explicitly for that meaning.
"""
