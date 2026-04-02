# Decision 003: API 접근 테스트 결과

> **테스트 일시**: 2026-04-02
> **실행자**: Claude Code (CS-0-0 2단계)

## 테스트 결과

| # | 엔드포인트 | 상태코드 | 결과 | 영향 |
|---|-----------|---------|------|------|
| 1 | FMP Stock Peers (`/stable/stock-peers`) | **200** | ✅ 접근 가능 | DC-1에서 Finnhub + FMP 양쪽 Peers 병합 → PEER_OF 품질 향상 |
| 2 | Finnhub Supply Chain (`/stock/supply-chain`) | **403** | ❌ 접근 불가 | 6-Phase 전략 유지: DC-3 수동 시드 → DC-4 Gemini → DC-6 유료($200/월) |
| 3 | Finnhub ETF Holdings (`/etf/holdings`) | **403** | ❌ 접근 불가 | DC-2에서 CSV 다운로드 방식 또는 2단 구조 필요 |
| 4 | Finnhub Insider Transactions (`/stock/insider-transactions`) | **200** | ✅ 접근 가능 | CS-2-1에서 InsiderSignal 계산 구현 가능 |
| 5 | FMP Revenue Segmentation (`/stable/revenue-product-segmentation`) | **200** | ✅ 접근 가능 | CS-2-1에서 SensitivityProfile 구현 가능 (segment 데이터 기반) |

## 의사결정

### DC-1 Peer 수집 방식
- **Finnhub Peers + FMP Stock Peers 양쪽 병합**
- FMP에서 company name, price, market_cap까지 제공 → 노드 속성 강화
- 양쪽 모두 나오는 peer → confidence 상승

### DC-2 ETF Holdings 방식
- **운용사 CSV 다운로드** (Finnhub 403이므로)
- 로드맵 옵션 B 채택: iShares/SPDR/ARK/Global X 공식 CSV URL
- 상위 30개만 OpenFIGI 매핑 (필요 시)

### CS-2-1 Tier A 계산 범위
- GrowthStage: ✅ 확정 (metrics/ 데이터로 즉시 가능)
- CapitalDNA: ✅ 확정 (CF + BS 데이터로 즉시 가능)
- SensitivityProfile: ✅ **확정** (FMP Revenue Segmentation 200 → segment 데이터 확보 가능)
- InsiderSignal: ✅ **확정** (Finnhub Insider Transactions 200 → insider 데이터 확보 가능)

→ **Tier A 4개 전부 구현 가능!** (v1.1에서 2개만 확정이었으나 업그레이드)

### DC-6 필요 여부
- **유지** — Finnhub Supply Chain은 403 (Premium/Pro 필요)
- DC-3 수동 시드 + DC-4 Gemini로 대체하되, 수익화 후 Finnhub Premium 검토

## 응답 샘플

### FMP Stock Peers (AAPL)
```json
[{"symbol": "GOOGL", "companyName": "Alphabet Inc.", "price": 297.39, "mktCap": 3597526905834}, ...]
```

### Finnhub Insider Transactions (AAPL)
```json
{"data": [{"change": -60208, "filingDate": "2026-03-17", "name": "Newstead Jennifer", "share": 240832, "symbol": "AAPL", "transactionCode": "S-Sale"}, ...]}
```

### FMP Revenue Segmentation (AAPL)
```json
[{"symbol": "AAPL", "fiscalYear": 2025, "data": {"Mac": 33708000000, "Service": 109158000000, "iPad": 33416000000, "iPhone": 213418000000, "Wearables, Home and Accessories": 26597000000}}]
```
