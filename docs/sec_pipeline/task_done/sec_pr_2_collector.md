# SEC-PR-2: SEC EDGAR 수집기 + 섹션 추출 + 사후 검증

> **완료일**: 2026-04-04

## 변경 사항

- 설계서 원안은 FMP sec-filings 엔드포인트 사용이었으나, **FMP Starter 플랜에서 미지원 (404/403)**
- SEC EDGAR submissions API (무료)로 대체 → `CIK{cik}.json`에서 10-K 메타데이터 직접 조회
- 의사결정 기록: `docs/sec_pipeline/decisions/001_fmp_vs_sec_edgar_metadata.md`

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `sec_pipeline/collector.py` | SECFilingCollector 클래스 (메타데이터 → HTML → 섹션 추출 → 검증) |
| `sec_pipeline/validators.py` | validate_extracted_sections (순서/heading/길이 3단계 검증) |

## 데이터 흐름

```
SEC EDGAR company_tickers.json → CIK 변환
  ↓
SEC EDGAR submissions/CIK{cik}.json → 10-K 메타데이터 (accession_no, filing_date, primary_document)
  ↓
SEC EDGAR Archives → HTML 원문 다운로드
  ↓
섹션 추출 (3단계: ToC제거 → 다중후보 → longest scoring)
  ↓
사후 검증 (순서 → heading → 길이)
  ↓ (실패 시)
edgartools fallback (선택적 의존성)
```

## 3종목 테스트 결과

| 종목 | Status | Item 1 | Item 1A | Item 7 | Warnings | Fallback |
|------|--------|--------|---------|--------|----------|----------|
| AAPL | success | 16,071 | 96,553 | 18,734 | 없음 | 미사용 |
| JPM | success | 123,048 | 961,557 | 996,841 | item_1a/item_7 길이 경고 | 미사용 |
| XOM | success | 5,635 | 298,908 | 88,355 | 없음 | 미사용 |

- 3종목 모두 regex 추출 성공, fallback 불필요
- JPM은 은행 특성상 Item 1A, 7이 매우 길어 WARN 발생 (제거 아닌 경고만)

## 다음 PR

→ SEC-PR-3: Pass 1 키워드 필터 + Pass 2 Gemini Flash (Track A)
