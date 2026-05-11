"""
SEC Pipeline LLM 프롬프트 정의.

Track A — Supply Chain 추출 (Phase 1)
Track B — Business Model 분류 (Phase 2)
"""

PROMPT_VERSION = 'v1'
PROMPT_VERSION_TRACK_B = 'v1'

SUPPLY_CHAIN_EXTRACTION_PROMPT = """You are a financial analyst extracting supply chain relationships from SEC 10-K filings.

**Company**: {symbol} ({company_name})

**Task**: Analyze the following paragraphs from the company's 10-K filing and extract all supply chain relationships mentioned.

For each relationship found, provide:
- `target_company_name`: The exact name of the other company mentioned (not abbreviations)
- `relationship_type`: One of: SUPPLIES_TO, CUSTOMER_OF, PARTNER_WITH, DEPENDS_ON, COMPETES_WITH
- `evidence_text`: The exact sentence or phrase from the text that supports this relationship (max 300 chars)
- `confidence`: Your confidence in this extraction (0.0 to 1.0)
- `direction`: "outbound" (source company provides to target) or "inbound" (target provides to source)

**Relationship type definitions**:
- SUPPLIES_TO: {symbol} supplies products/services to the target company
- CUSTOMER_OF: {symbol} buys from the target company (target is a supplier)
- PARTNER_WITH: Mutual partnership, joint venture, or strategic alliance
- DEPENDS_ON: {symbol} has a critical dependency on the target (e.g., sole source supplier)
- COMPETES_WITH: Direct competitor in the same market

**Rules**:
- Only extract relationships with specific, named companies (not generic terms like "our customers")
- Do not include relationships with {symbol} itself
- Do not include government agencies or regulatory bodies
- If unsure about the relationship type, use DEPENDS_ON
- Confidence should be >= 0.7 for clearly stated relationships, 0.4-0.7 for implied ones

**Paragraphs**:
{paragraphs}

Return a JSON object with a single key "relationships" containing an array of relationship objects.
If no relationships are found, return {{"relationships": []}}.
"""


BUSINESS_MODEL_EXTRACTION_PROMPT = """You are a financial analyst classifying business model characteristics from SEC 10-K filings.

**Company**: {symbol} ({company_name})

**Task**: Analyze the following paragraphs and classify the company's business model across 5 dimensions.

For each dimension, provide:
- `value`: Your classification (see options below)
- `evidence_text`: The key sentence supporting your classification (max 200 chars)
- `confidence`: Your confidence (0.0 to 1.0)

**Dimensions**:

1. `direct_customer_contact`: How does the company reach customers?
   - "direct": Primarily direct sales (own stores, website, sales team)
   - "indirect": Through distributors, resellers, OEMs
   - "hybrid": Both direct and indirect channels
   - "unknown": Cannot determine

2. `contract_model`: What is the primary revenue model?
   - "subscription": Recurring subscriptions, SaaS, maintenance
   - "one_time": One-time purchases, hardware, project-based
   - "hybrid": Mix of recurring and one-time
   - "unknown": Cannot determine

3. `recurring_revenue_signal`: How strong is the recurring revenue signal?
   - "high": Explicitly mentions ARR/MRR, high retention, low churn
   - "medium": Some recurring elements, backlog, deferred revenue
   - "low": Primarily one-time revenue
   - "unknown": Cannot determine

4. `channel_dependency`: How dependent on third-party channels?
   - "high_dependency": Heavily relies on distributors/resellers
   - "moderate": Some channel reliance but also direct
   - "low_dependency": Primarily direct, minimal channel dependence
   - "unknown": Cannot determine

5. `customer_concentration`: How concentrated is the customer base?
   - "concentrated": Top customers account for significant revenue (>10%)
   - "diversified": No single customer dominates, broad base
   - "unknown": Cannot determine

**Rules**:
- Use "unknown" only when genuinely unable to determine, not as a default
- Base your classification strictly on the text provided
- Confidence ≥ 0.8 for clearly stated characteristics, 0.5-0.8 for inferred

**Paragraphs**:
{paragraphs}

Return a JSON object with keys matching the 5 dimension names, each containing {{"value": str, "evidence_text": str, "confidence": float}}.
"""
