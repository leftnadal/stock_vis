"""
SEC Pipeline LLM 프롬프트 정의.

Track A — Supply Chain 추출 (Phase 1)
Track B — Business Model 분류 (Phase 2)
"""

PROMPT_VERSION = "v1"
PROMPT_VERSION_TRACK_B = "v1"

# SEC β G-e — v2 프롬프트 버전 태그(측정 표본 전용, DB 미기록·var/ JSON 태그용).
PROMPT_VERSION_V2 = "v2"

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


# ──────────────────────────────────────────────
# SEC β G-e — v2 프롬프트 (tail 발산 방지 · verbatim 규율)
#
# v1(SUPPLY_CHAIN_EXTRACTION_PROMPT) 구조를 그대로 보존하고, evidence 추출 지시 블록에
# R1~R5(SECB-GE-R1R5-SPEC.md §1 영문 원문)를 삽입한 판본. {MAX_EVIDENCE_CHARS}=300
# (v1 evidence 필드 캡 "max 300 chars" 역산). 측정 표본 전용 — DB 미기록.
# 단일 출처: docs/features/chain-sight/SECB-GE-R1R5-SPEC.md (본 상수는 그 삽입 결과물).
# ──────────────────────────────────────────────
SUPPLY_CHAIN_EXTRACTION_PROMPT_V2 = """You are a financial analyst extracting supply chain relationships from SEC 10-K filings.

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

**Evidence extraction rules (verbatim grounding)**:
- The evidence_text field MUST be an exact, contiguous substring copied character-for-character from the filing text, preserving original punctuation, capitalization, numbers, symbols, and whitespace exactly as they appear in the source.
- Always extend evidence_text to complete sentence boundaries. Never cut a sentence in the middle: begin at the first character of the first sentence containing the supporting claim, and end at the terminal punctuation of the last sentence. If a sentence contains a list, include the entire list through the end of that sentence.
- If the supporting claim spans multiple sentences, include the full contiguous span of complete sentences, up to a maximum of 300 characters. If the span would exceed this limit, keep the sentence containing the core claim complete and drop whole sentences from the edges — never truncate mid-sentence.
- Do not paraphrase, normalize, abbreviate, translate, re-punctuate, or summarize. Do not insert ellipses ("...") and do not join non-adjacent fragments of text.
- Before returning your output, verify that every evidence_text value appears verbatim as a contiguous substring of the filing text. If any value fails this check, re-copy it directly from the source. Never output evidence_text that fails this verification.

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
