# 001: FMP vs SEC EDGAR 메타데이터 소스

> **결정일**: 2026-04-04

## 배경

설계서(base_design.md)에서 FMP API를 10-K filing 메타데이터 소스로 지정했으나,
FMP Starter 플랜($22/월)에서 `sec-filings` 엔드포인트가 미지원.

- `/stable/sec-filings`: 404
- `/api/v3/sec_filings/{symbol}`: 403 (상위 플랜 필요)

## 결정

**SEC EDGAR submissions API 직접 사용** (무료)

- `company_tickers.json` → Ticker → CIK 변환
- `submissions/CIK{cik}.json` → 10-K 메타데이터 (accession_no, filing_date, primary_document)
- `Archives/edgar/data/{cik}/{accession}/{document}` → HTML 다운로드

## 근거

1. base_design.md 2.3 역할 분담 표에 "submissions JSON polling" 대안 명시
2. 기존 코드베이스에 `api_request/sec_edgar_client.py` 동일 패턴 존재
3. 추가 비용 없음 (무료)
4. Rate limit 10 req/sec으로 충분

## 영향

- FMP API key 의존성 제거 (SEC Pipeline에서)
- collector.py가 SEC EDGAR만 호출
- Phase 3의 `check_new_filings_via_fmp()` (SEC-PR-15)도 SEC EDGAR RSS로 대체 필요
