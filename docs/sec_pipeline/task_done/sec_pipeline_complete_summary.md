# SEC Pipeline 전체 완료 요약

> **기간**: 2026-04-04 (1일)
> **범위**: Phase 1~3, 17 PR 전체

---

## 아키텍처

```
SEC EDGAR submissions API → 10-K 메타데이터
  ↓
SEC EDGAR Archives → HTML 원문 다운로드
  ↓
섹션 추출 (regex 3단계 + edgartools fallback)
  ↓
사후 검증 (순서/heading/길이)
  ↓
RawDocumentStore (PostgreSQL)
  ├── Track A: 키워드 필터 → Gemini 2.5 Flash → SupplyChainEvidence
  └── Track B: 키워드 필터 → Gemini 2.5 Flash → BusinessModelSnapshot
  ↓
TickerMatcher (alias → exact → fuzzy) → UnmatchedCompanyQueue
  ↓
sync_dirty_to_neo4j (DELETE + CREATE dynamic type)
  ↓
Quality Checks → Intelligence Report (Gemini 5차원 분석)
```

## 모델 (8개)

| 모델 | 테이블 | 건수 | Phase |
|------|--------|------|-------|
| RawDocumentStore | sec_raw_document_store | 15 | 1 |
| SupplyChainEvidence | sec_supply_chain_evidence | 110 | 1 |
| FilingProcessLog | sec_filing_process_log | 173 | 1 |
| CompanyAlias | sec_company_alias | 0 | 1.5 |
| UnmatchedCompanyQueue | sec_unmatched_company_queue | 60 | 1.5 |
| BusinessModelSnapshot | sec_business_model_snapshot | 5 | 2 |
| BusinessModelEvidence | sec_business_model_evidence | 25 | 2 |
| PipelineIntelligenceReport | sec_pipeline_intelligence_report | 2 | 3 |

## 파일 목록

### sec_pipeline/ 앱 (16 파일)

| 파일 | 역할 | Phase |
|------|------|-------|
| models.py | 8개 모델 | 1 |
| collector.py | SEC EDGAR 수집기 (메타데이터 + HTML + 섹션추출) | 1 |
| validators.py | 섹션 사후 검증 (순서/heading/길이) | 1 |
| normalizer.py | 텍스트 정규화 + Pass 1 키워드 필터 | 1 |
| prompts.py | Track A/B LLM 프롬프트 | 1, 2 |
| extractor.py | GeminiExtractor (Track A + Track B) | 1, 2 |
| validator_track_a.py | Track A 검증 + confidence grade + DB 저장 | 1 |
| validator_track_b.py | Track B 검증 + DB 저장 | 2 |
| keywords_track_b.py | Track B 5개 필드 키워드 사전 | 2 |
| exceptions.py | 4개 예외 클래스 | 1 |
| tasks.py | Celery tasks (collect, extract, sync, check, batch, intelligence) | 1, 1.5, 3 |
| sp500.py | S&P 500 심볼 유틸리티 | 1 |
| ticker_matcher.py | 3단계 매칭 + 큐 적재 | 1.5 |
| signals.py | post_save → evidence 업데이트 + CompanyAlias 등록 | 1.5 |
| merger.py | 관계 병합 + DQS 계산 | 1.5 |
| intelligence.py | PipelineDataCollector + PipelineIntelligenceReporter | 3 |
| quality_checks.py | 7개 품질 체크 + 대시보드 통계 | 3 |
| on_demand.py | On-demand filing 수집 | 3 |
| views.py | Admin 대시보드 + FilingDataView API | 3 |
| urls.py | dashboard + filing API | 3 |
| admin.py | 8개 모델 Admin (큐 관리, Intelligence Report) | 1.5, 3 |

### 기타

| 파일 | 역할 |
|------|------|
| metrics/services/business_model_service.py | BM 서비스 레이어 (for_api 게이트) |
| templates/admin/sec_pipeline/dashboard.html | Admin 대시보드 UI |
| config/settings.py | INSTALLED_APPS 추가 |
| config/urls.py | sec-pipeline URL include |

## 설계 원칙 준수 확인

| 원칙 | 준수 | 비고 |
|------|------|------|
| 원칙 1 — 문서 기반 개발 | ✅ | base_design + pr_detail 기반 |
| 원칙 2 — 작업 완료 기록 | ✅ | task_done 15건 |
| 원칙 3 — 매니저 파악 가능 | ✅ | 데이터 흐름도, 스키마, API 예시 |
| 원칙 4 — 1인 개발 | ✅ | Django 모놀리스, 최소 추상화 |
| 원칙 5 — 간접 참조 | ✅ | metrics/services/ 서비스 레이어 |
| 원칙 6 — 숫자 노출 경계 | ✅ | for_api, confidence_grade |
| 원칙 7 — Neo4j 통일 | ✅ | dynamic type, DELETE+CREATE |

## 의사결정

| 번호 | 결정 | 근거 |
|------|------|------|
| 001 | FMP → SEC EDGAR 메타데이터 | FMP Starter 플랜 sec-filings 404 |

## 배치 실행 결과 (15종목)

- 수집 성공: 14/15 (93.3%), JNJ만 Item 순서 검증 실패
- Track A: 110개 관계, 타입 분포 균형 (PARTNER_WITH 21, CUSTOMER_OF 19, DEPENDS_ON 19)
- Track B: 5개 BM Snapshot (NVDA: hybrid/hybrid/medium/high_dep/diversified)
- Ticker 매칭: 2/110 (3%) — 비미국 주식 미등록이 주 원인
- Neo4j 동기화: 2건 (NVDA→MU, PG→WMT)
- Intelligence Report: severity=critical (매칭률 기반)

## 향후 과제

1. S&P 500 전체 배치 (Gemini RPD 제한 고려)
2. Gold Set 라벨 보완 → Precision/Recall 재평가
3. JNJ Item 순서 검증 완화
4. 프롬프트 개선: 일반 명사("third parties") 추출 방지
5. CompanyAlias 수동 등록 (TSMC→TSM, Samsung 등)
