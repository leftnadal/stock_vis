# SEC-PR-17: Celery chord 통합 + E2E 테스트

> **완료일**: 2026-04-04

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `sec_pipeline/tasks.py` | generate_intelligence_report, run_batch_and_report 추가 |

## run_batch_and_report 흐름

```
Phase 1: 종목별 collect_and_extract → extract_from_document (순차)
Phase 2: sync_dirty_to_neo4j → run_post_batch_quality_checks
Phase 3: generate_intelligence_report
```

## E2E 테스트 결과 (AAPL, MSFT, JPM, XOM, NVDA)

```
Total: 5, Success: 5, Failed: 0
Sync: 0 (이미 동기화됨)
Alerts: 2 (매칭률, 섹션검증)
Report: ID=2, severity=critical, health=0.2
```

## 전체 DB 현황

| 모델 | 건수 |
|------|------|
| RawDocumentStore | 15 |
| SupplyChainEvidence | 110 |
| BusinessModelSnapshot | 5 |
| BusinessModelEvidence | 25 |
| FilingProcessLog | 173 |
| CompanyAlias | 0 |
| UnmatchedCompanyQueue | 60 |
| PipelineIntelligenceReport | 2 |

## Celery Beat 설정 (주석 상태)

```python
'sync-sec-dirty-neo4j': crontab(minute='*/5')
'check-new-filings': crontab(day_of_month='1', hour='6')
```

---

## SEC Pipeline 전체 완료 (Phase 1~3, 17 PR)

| Phase | PR | 상태 |
|-------|-----|------|
| Phase 1 | SEC-PR-1~6 | ✅ |
| Phase 1.5 | SEC-PR-7~10 | ✅ |
| Phase 2 | SEC-PR-11~13 | ✅ |
| Phase 3 | SEC-PR-14~17 | ✅ |

### 핵심 산출물
- **8개 Django 모델** + migration
- **SEC EDGAR 수집기** (무료, FMP 대체)
- **Gemini 2.5 Flash** Track A (Supply Chain) + Track B (Business Model) 추출
- **3단계 Ticker 매칭** (alias → exact → fuzzy) + Admin 큐
- **Neo4j 동기화** (DELETE + CREATE dynamic type, sole writer)
- **서비스 레이어** (for_api confidence 노출 경계)
- **Admin 대시보드** + 7개 품질 체크
- **On-demand 수집** + 신규 filing 감지
- **LLM Intelligence Report** (5차원 분석)
- **E2E chord** (배치 → sync → quality → intelligence)
