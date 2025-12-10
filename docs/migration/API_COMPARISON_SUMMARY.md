# FMP vs Alpha Vantage - Quick Reference Summary

## Quick Decision Matrix

### Use Alpha Vantage For:
- ✅ Real-time stock quotes (faster due to NASDAQ official status)
- ✅ Technical indicators (RSI, MACD, Bollinger Bands - 20+ indicators)
- ✅ Intraday historical data (better free tier history)
- ✅ When price < $100 (more precise with technical data)

### Use FMP For:
- ✅ Balance sheets (SEC-sourced, more authoritative)
- ✅ Income statements (better field completeness)
- ✅ Cash flow statements (more detailed breakdowns)
- ✅ Company profiles (richer metadata: CEO, ISIN, CUSIP, website)
- ✅ Insider trading data (future feature, free tier includes)

---

## At-a-Glance Comparison

| Feature | Alpha Vantage | FMP | Recommendation |
|---------|---------------|-----|-----------------|
| Real-time Quotes | ⭐⭐⭐ | ⭐⭐ | Use **AV** (NASDAQ official) |
| Financial Statements | ⭐⭐ | ⭐⭐⭐ | Use **FMP** (SEC-sourced) |
| Technical Indicators | ⭐⭐⭐ | ❌ | Use **AV** (exclusive) |
| Daily Quota | 500 calls | 250 calls | **AV** (2x more) |
| Per-Minute Limit | 5 calls/min | No limit (4 parallel/sec) | **FMP** (more flexible) |
| Free Tier Intraday | ✅ Full | ⚠️ Limited | **AV** (better history) |
| Response Format | String numbers | JSON numbers | **FMP** (cleaner) |
| SEC Filing Data | ❌ | ✅ | **FMP** (unique) |
| Insider Trading | ❌ | ✅ | **FMP** (premium feature) |

---

## Recommended Implementation Strategy

### HYBRID APPROACH (Cost: $0/month, Effort: 40-60 hours)

```
Stock-Vis API Architecture
─────────────────────────

Frontend
   ↓
Abstraction Layer (new)
   ├──→ Alpha Vantage Service
   │    └─→ Quotes, Indicators, Intraday
   │
   └──→ FMP Service (new)
        └─→ Financials, Profiles, Insider Data

Database
```

**Daily Budget**:
- Alpha Vantage: 500 calls (stay well below with 60 calls for 10 stocks)
- FMP: 250 calls (stay well below with 60 calls for 10 stocks)

**Zero cost increase** - both services used within free tier limits!

---

## Implementation Phases

### Phase 1: Discovery (Complete ✅)
- [x] FMP API documentation reviewed
- [x] Endpoint mapping completed
- [x] Rate limits analyzed
- [x] Response formats compared

### Phase 2: FMP Service Layer (40-60 hours)
- Create `API_request/fmp_client.py` (mirror of alphavantage_client.py)
- Create `API_request/fmp_processor.py` (handle numeric JSON format)
- Create `API_request/fmp_service.py` (transaction management)
- Create test suite for FMP integration

### Phase 3: Abstraction & Hybrid Logic (20-30 hours)
- Create `API_request/hybrid_service.py` or `stock_data_provider.py`
- Update `stocks/views.py` to use hybrid service
- Implement fallback logic (use AV if FMP fails)
- Add API usage monitoring

### Phase 4: Validation & Deployment (10-15 hours)
- Integration tests (data consistency between APIs)
- Performance benchmarks
- Error handling & rate limit monitoring
- Production rollout with monitoring

---

## Data Field Quick Reference

### Quote Response Mapping
```
Alpha Vantage          FMP
─────────────          ───
symbol        ↔        symbol
price         ↔        price
change        ↔        change
changePercent ↔        changePercentage  ⚠️ Name differs
volume        ↔        volume
timestamp     ↔        timestamp
─                      name (NEW)
─                      dayLow, dayHigh (NEW)
─                      yearLow, yearHigh (NEW)
─                      marketCap (NEW)
─                      priceAvg50, priceAvg200 (NEW)
```

### Financial Statement Mapping
```
Alpha Vantage          FMP
─────────────          ───
String: "123456789"    Number: 123456789
camelCase dates        ISO 8601 dates
Nested structure       Flat/Array structure
Limited fields         Comprehensive fields
─                      More detail on expenses
─                      Asset breakdown detail
─                      Cash flow categories
```

---

## Cost-Benefit Analysis

### Implementation Costs
- **Development**: 40-60 hours (~$1,500-2,500 if outsourced)
- **Testing**: 10-15 hours (~$300-600 if outsourced)
- **Deployment**: 5 hours (~$150-250 if outsourced)
- **Total**: ~70-80 hours (~$2,000-3,400)

### Ongoing Costs
- **Alpha Vantage**: Free (within 500 calls/day)
- **FMP**: Free (within 250 calls/day)
- **Total**: $0/month

### ROI/Benefits
1. **Better financial data accuracy** (SEC-sourced instead of aggregated)
2. **Reduced rate-limiting delays** (no 5/min strict limit from FMP)
3. **Extensibility** (foundation for SEC filings, insider trading)
4. **Redundancy** (if one API fails, fallback to other)
5. **Future-proof** (ready for advanced features)

**Payback Period**: Development cost recovered within 1-2 months of improved user experience.

---

## Decision Tree: Which API to Use?

```
Need real-time stock quote?
├─ YES → Use Alpha Vantage
│        (faster, NASDAQ official, better per-min limit)
└─ NO
    │
    Need financial statements?
    ├─ YES → Use FMP
    │        (SEC-sourced, more accurate, better detail)
    └─ NO
        │
        Need technical indicators?
        ├─ YES → Use Alpha Vantage
        │        (only provider with indicators)
        └─ NO
            │
            Need historical intraday?
            ├─ YES → Use Alpha Vantage
            │        (better free tier history)
            └─ NO
                │
                Need insider/SEC data?
                ├─ YES → Use FMP
                │        (exclusive data)
                └─ NO
                    Use Alpha Vantage (default, broader coverage)
```

---

## Quick Start for FMP

### 1. Sign Up (5 minutes)
```bash
# Go to FMP website
https://site.financialmodelingprep.com/developer/docs

# Sign up for free → Get API key automatically
# Add to .env
FMP_API_KEY=your_key_here
```

### 2. Test Basic Endpoints (15 minutes)
```bash
# Test quote endpoint
curl "https://financialmodelingprep.com/api/v3/quote/AAPL?apikey=YOUR_KEY"

# Test company profile
curl "https://financialmodelingprep.com/api/v3/profile/AAPL?apikey=YOUR_KEY"

# Test balance sheet
curl "https://financialmodelingprep.com/api/v3/balance-sheet-statement/AAPL?limit=5&apikey=YOUR_KEY"
```

### 3. Integration Steps (40-60 hours)
1. Create `API_request/fmp_client.py`
2. Create `API_request/fmp_processor.py`
3. Create `API_request/fmp_service.py`
4. Update `stocks/views.py` to use hybrid service
5. Add tests and monitoring

---

## Risk Assessment

### Low Risk ✅
- Both APIs are mature and stable
- Free tier is clearly documented
- Response formats are well-defined
- Hybrid approach has fallback logic

### Medium Risk ⚠️
- Rate limit monitoring needed (daily quota tracking)
- Field name differences require careful mapping
- FMP intraday limited on free tier (but AV fallback available)

### Mitigation Strategies
- Implement usage monitoring dashboard
- Comprehensive test suite for field mapping
- Fallback logic between providers
- Gradual rollout (start with financial statements only)

---

## FAQ

**Q: Should we migrate immediately?**
A: No. Consider hybrid approach instead - better value, zero cost increase.

**Q: Will this make the app faster?**
A: For financial data, yes (no per-min rate limit). For quotes, same speed but better resilience.

**Q: What if we hit FMP's 250 call limit?**
A: Stays within free tier for 10-20 stocks with smart caching.

**Q: Do we need to pay for FMP?**
A: No, both APIs stay within free tier limits in hybrid approach.

**Q: How long will implementation take?**
A: 40-60 hours development + 10-15 hours testing.

**Q: What about Korean stocks?**
A: Neither API supports KRX on free tier - separate Korean API needed.

---

## Next Steps

1. **This Week**: Sign up for FMP, validate quote endpoints
2. **Next Week**: Create FMP service layer following Alpha Vantage pattern
3. **Week 3**: Implement hybrid abstraction layer
4. **Week 4**: Testing and deployment

**Owner**: @backend + @investment-advisor
**Timeline**: 6-8 weeks for full implementation
**Priority**: Medium (nice-to-have, improves data quality)

---

## Document References

For detailed analysis, see:
- Main document: `docs/migration/api-mapping-table.md`
- Field mappings: See "Data Field Mapping Reference" section
- Implementation guide: See "Implementation Roadmap" section
- Cost analysis: See "Cost-Benefit Analysis" section

---

**Last Updated**: 2025-12-08
**Status**: Ready for Review by @backend and @investment-advisor
