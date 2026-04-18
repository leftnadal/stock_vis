# 003: API 접근 테스트 결과

> **테스트일**: 2026-04-18
> **FMP Plan**: Starter
> **Finnhub Plan**: Free

## 테스트 결과

| # | 테스트 | 엔드포인트 | 결과 | 영향 |
|---|--------|-----------|------|------|
| 1 | FMP Stock Peers | `/stable/stock-peers?symbol=AAPL` | **200 ✅** | DC-1 peer 보강 가능 (FMP + Finnhub 병행) |
| 2 | Finnhub Supply Chain | `/stock/supply-chain?symbol=AAPL` | **403 ❌** | Premium 전용. 6-Phase SEC 파이프라인 유지 |
| 3 | Finnhub ETF Holdings | `/etf/holdings?symbol=SPY` | **403 ❌** | Premium 전용. CSV/SPDR XLSX 방식 유지 |
| 4 | Finnhub Insider Transactions | `/stock/insider-transactions?symbol=AAPL` | **200 ✅** | CS-2-1 InsiderSignal 구현 가능 |
| 5 | FMP Revenue Segmentation | `/stable/revenue-product-segmentation?symbol=AAPL` | **200 ✅** | CS-2-1 RevenueStructure/SensitivityProfile 구현 가능 |

## 응답 샘플

### 1. FMP Stock Peers (200)
```json
[{"symbol":"GOOGL","companyName":"Alphabet Inc.","price":341.68,"mktCap":4133303126056}, ...]
```
- 배열 형태, symbol + companyName + price + mktCap 포함
- DC-1에서 peer 목록 보강에 활용

### 2. Finnhub Supply Chain (403)
```json
{"error":"You don't have access to this resource."}
```
- Premium 구독 필요
- SEC 10-K 파이프라인으로 SUPPLIES_TO/CUSTOMER_OF 관계 추출 유지

### 3. Finnhub ETF Holdings (403)
```json
{"error":"You don't have access to this resource."}
```
- Premium 구독 필요
- 기존 SPDR XLSX 파싱 방식 유지

### 4. Finnhub Insider Transactions (200)
```json
{"data":[{"change":-331,"filingDate":"2026-04-17","name":"Borders Ben","share":2312,"symbol":"AAPL","transactionCode":"M",...}]}
```
- 최근 insider 거래 데이터 정상 반환
- CS-2-1 InsiderSignal 모델에 연동 가능

### 5. FMP Revenue Segmentation (200)
```json
[{"symbol":"AAPL","fiscalYear":2025,"data":{"Mac":33708000000,"Service":109158000000,...}}]
```
- 제품/서비스별 매출 구조 반환
- CS-2-1 RevenueStructure 모델에 연동 가능

## 의사결정

| 항목 | 결정 |
|------|------|
| Finnhub Supply Chain | 403 → SEC 10-K 파이프라인 유지 (이미 구현됨) |
| Finnhub ETF Holdings | 403 → SPDR XLSX 방식 유지 |
| DC-1 Peer 보강 | FMP `/stable/stock-peers` 200 → 기존 Finnhub + FMP 병행 |
| CS-2-1 구현 가능 여부 | InsiderSignal + RevenueStructure 모두 API 접근 가능 ✅ |
