# SEC-PR-4: Celery tasks + 에러 핸들링

> **완료일**: 2026-04-04

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `sec_pipeline/exceptions.py` | 4개 예외 (FMPApiError, SECFetchError, SectionExtractionError, LLMExtractionError) |
| `sec_pipeline/tasks.py` | collect_and_extract + extract_from_document + _log_stage |
| `sec_pipeline/sp500.py` | get_sp500_symbols() 유틸리티 |

## Task 구조

```
collect_and_extract(symbol)     ← max_retries=3
  Step 1: SEC EDGAR 메타데이터
  Step 2: SEC HTML 다운로드
  Step 3: 섹션 추출+검증 → fallback
  Step 4: RawDocumentStore 저장 (update_or_create)
  Step 5: extract_from_document.delay()
          ↓
extract_from_document(doc_id, symbol)   ← max_retries=2
  Track A: supply chain 추출+저장
  Track B: pass (Phase 2)
```

## 에러 핸들링

| 예외 | retry | backoff |
|------|-------|---------|
| 메타데이터 실패 | 3 | 60s × 2^n |
| SEC HTML 실패 | 5 | 10s × 2^n |
| 섹션 추출 실패 | 1 | 5s (fallback 후) |
| LLM 추출 실패 | 2 | (Track A 실패해도 Track B 시도) |

## 테스트 결과 (NVDA 동기 실행)

```
collect_and_extract: symbol=NVDA, doc_id=1, status=success, created=True
extract_from_document: Track A raw=8, validated=8

FilingProcessLog (8건):
  fmp_metadata → success (accession=0001045810-26-000021)
  sec_fetch → success (1,967,816 bytes)
  section_extract → success (3/3 sections, regex)
  track_a_extract → success (raw=8, validated=8)
```

DB 확인:
- RawDocumentStore: 1건 (NVDA 2025)
- SupplyChainEvidence: 8건 (TSMC, Samsung, SK Hynix, Micron 등)
- 전부 neo4j_dirty=True (Phase 1.5에서 동기화)

## 다음 PR

→ SEC-PR-5: Gold Set 라벨링 + 평가 스크립트
