# SEC-PR-1: Django 앱 + 모델 + migration

> **완료일**: 2026-04-04

## 생성된 테이블 (8개)

| # | 테이블명 | 모델 | Phase | 역할 |
|---|---------|------|-------|------|
| 1 | `sec_raw_document_store` | RawDocumentStore | 1 | SEC 10-K filing 원문 + 섹션 저장 |
| 2 | `sec_supply_chain_evidence` | SupplyChainEvidence | 1 | Track A 추출 결과 (supply chain 관계) |
| 3 | `sec_business_model_snapshot` | BusinessModelSnapshot | 2 | Track B 분류 결과 (5개 비즈니스 모델 필드) |
| 4 | `sec_business_model_evidence` | BusinessModelEvidence | 2 | Track B 각 필드 근거 문장 |
| 5 | `sec_filing_process_log` | FilingProcessLog | 1 | 파이프라인 각 단계 실행 로그 |
| 6 | `sec_company_alias` | CompanyAlias | 1.5 | Ticker 별칭 매핑 |
| 7 | `sec_unmatched_company_queue` | UnmatchedCompanyQueue | 1.5 | Ticker 미매칭 큐 |
| 8 | `sec_pipeline_intelligence_report` | PipelineIntelligenceReport | 3 | LLM 품질 분석 리포트 |

## FK 관계

```
RawDocumentStore.symbol → stocks.Stock (CASCADE)
SupplyChainEvidence.source_document → RawDocumentStore (CASCADE)
SupplyChainEvidence.source_company → stocks.Stock (CASCADE)
SupplyChainEvidence.target_company → stocks.Stock (SET_NULL, nullable)
BusinessModelSnapshot.symbol → stocks.Stock (CASCADE)
BusinessModelSnapshot.source_document → RawDocumentStore (CASCADE)
BusinessModelEvidence.snapshot → BusinessModelSnapshot (CASCADE)
```

## 변경된 파일

| 파일 | 변경 |
|------|------|
| `sec_pipeline/__init__.py` | 신규 (빈 파일) |
| `sec_pipeline/apps.py` | 신규 (SecPipelineConfig) |
| `sec_pipeline/models.py` | 신규 (8개 모델) |
| `sec_pipeline/admin.py` | 신규 (빈 파일, PR-8에서 채움) |
| `sec_pipeline/migrations/0001_initial.py` | 자동 생성 |
| `config/settings.py` | INSTALLED_APPS에 `sec_pipeline` 추가 |

## 설계 제약조건 검증

| 제약조건 | 결과 |
|---------|------|
| `neo4j_dirty` only (synced_to_neo4j 금지) | ✅ |
| `BusinessModelSnapshot.Meta.get_latest_by = 'as_of_date'` | ✅ |
| `CompanyAlias.unique_together = [('alias', 'context_sector')]` (country 제외) | ✅ |
| `UnmatchedCompanyQueue.source_sectors` JSONField(default=list) | ✅ |
| `PipelineIntelligenceReport` migration 포함 (Phase 3 사용) | ✅ |

## 테스트 결과

```
$ python manage.py showmigrations sec_pipeline
 [X] 0001_initial

$ python manage.py shell → from sec_pipeline.models import * → 8개 모델 전부 import 성공
```

## 다음 PR

→ SEC-PR-2: FMP 2-Step 수집기 + 섹션 추출 + 사후 검증
