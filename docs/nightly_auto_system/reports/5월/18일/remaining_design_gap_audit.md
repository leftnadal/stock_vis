# SEC Pipeline + Validation + News 설계 갭 감사

> 감사일: 2026-05-18
> 범위: docs/sec_pipeline/, docs/first_validation_system/, docs/news/plan/ ↔ sec_pipeline/, validation/, news/
> 분류 기준: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체
> 검증 방식: 파일 실존 + 식별자 grep (코드 수정 없음, 추측 배제)

---

## 앱별 요약 (구현률)

| 앱 | 설계 단위 수 | A 완료 | B 부분 | C 미구현 | D 폐기/대체 | 구현률 |
|----|-------------|--------|--------|----------|------------|--------|
| **SEC Pipeline** | 17 PR + 의사결정 1건 | 17 | 0 | 0 | 2 (FMP 미지원 대체) | **100%** |
| **Validation** | Phase 1~7 + 5 REST API + 배치 | 18 | 1 (thematic) | 1 (Thesis 연동) | 3 (자본집약/Top10/유저투표) | **95%** |
| **News** | 3 설계 문서 + Phase A·B·C | 26 | 2 (`_log_collection` 커버리지, `check_pipeline_alerts` 운영) | 0 | 0 | **85%** |

전체 가중 평균: **~93%** (3개 앱 모두 핵심 아키텍처는 완성, 외부 데이터 의존성과 자동화 트리거 일부만 보강 대상).

---

## SEC Pipeline 상세

### PR별 분류 (17/17 완료)

| PR | 명칭 | 분류 | 핵심 산출물 |
|----|------|------|------------|
| 1 | Django 앱 + 8개 모델 | (A) | RawDocumentStore, SupplyChainEvidence, FilingProcessLog, CompanyAlias, UnmatchedCompanyQueue, BusinessModelSnapshot/Evidence, PipelineIntelligenceReport |
| 2 | SEC EDGAR 수집기 + 섹션 검증 | (A) | SECFilingCollector, validators.validate_extracted_sections |
| 3 | Track A 추출 (공급망) | (A) | normalizer, GeminiExtractor.extract_supply_chain, validator_track_a.save_supply_chain_evidences |
| 4 | Celery tasks + 에러 처리 | (A) | collect_and_extract, _log_stage, 4개 예외 클래스, get_sp500_symbols |
| 5 | Gold Set + 평가 command | (A) | GoldSetEntry/SupplyChainRelation, fixtures/gold_set.json (10종목), evaluate_gold_set |
| 6 | Phase 1 배치 (15종목) | (A) | tasks.py 배치 루프 |
| 7 | TickerMatcher + 큐 적재 | (A) | 3단계 매칭(alias→exact→fuzzy) |
| 8 | Admin UI + signal | (A) | 8개 ModelAdmin, on_unmatched_resolved signal, apps.ready() |
| 9 | Neo4j 동기화 (DELETE+CREATE) | (A) | sync_dirty_to_neo4j, select_for_update(skip_locked) |
| 10 | 관계 병합 + DQS | (A) | merger.merge_relationship, calculate_edge_dqs, process_unmatched_queue cmd |
| 11 | Track B 키워드 사전 | (A) | keywords_track_b.filter_paragraphs_track_b |
| 12 | Track B LLM 추출 | (A) | GeminiExtractor.extract_business_model, BUSINESS_MODEL_EXTRACTION_PROMPT |
| 13 | 서비스 레이어 (for_api 경계) | (A) | metrics/services/business_model_service (get_business_model, is_recurring_business) |
| 14 | Admin 대시보드 + 품질 체크 | (A) | sec_pipeline_dashboard view, quality_checks 7종 |
| 15 | On-demand 수집 + new filing | (A) | get_or_collect_filing, FilingDataView (200/202) |
| 16 | Intelligence Reporter | (A) | PipelineDataCollector, PipelineIntelligenceReporter |
| 17 | Celery chord + E2E | (A) | run_batch_and_report 3-Phase orchestration |

### 갭 / 폐기

- **갭**: 없음. 17 PR 모두 코드/마이그레이션/템플릿/픽스처 실존 확인.
- **폐기·대체 (D)**:
  - FMP `sec-filings` API → SEC EDGAR submissions API로 대체 (FMP Starter 미지원, 의사결정 문서화됨).
  - `check_new_filings_via_fmp()` 명명 → `check_new_filings()` (SEC EDGAR RSS 기반).

---

## Validation 상세

### Phase/컴포넌트 분류

| Phase | 항목 | 분류 | 근거 |
|-------|------|------|------|
| 1 | default 프리셋 (업종 표준) | (A) | services/preset_generator._generate_default |
| 2 | sector_all, size_peers 프리셋 + PeerPreset 모델 + preset_key 확장 | (A) | models/peer_preset.py, benchmark_delta.py L53, category_score.py L51 |
| 3 | quality_top, lifecycle 프리셋 + confidence_score | (A) | preset_generator._generate_quality_top/_lifecycle, _calc_confidence (L464~475) |
| 4 | UserPeerPreference + 프리셋 선택/목록 API | (A) | api/views.py L424~487 (PresetListView, PeerPreferenceView) |
| 5 | CustomBenchmarkEngine + Redis 캐시 | (A) | services/custom_benchmark_engine.py (TTL 1h, user_id 격리) |
| 6 | thematic 프리셋 | **(B)** | GrowthStage×CapitalDNA 교차곱만 구현 (463/503). 원래 설계의 LLM 사업모델 큐레이션 미적용 |
| 6 | LLM 사업모델 태깅(NarrativeTag) | (D) | Chain Sight 파이프라인 선행 필요로 배제 |
| 7 | LLM 필터 파서 + 실행 엔진 + API | (A) | services/llm_peer_filter.py (Gemini Flash JSON), api/views.py L498~545 |
| 7 | Thesis Control 연동 (peer_preset_key/peer_filter_*) | **(C)** | thesis/models.py 필드/마이그레이션 부재, validation_peer_phase6_7.md §8 스키마만 존재 |
| 공통 | Summary/Metrics/LeaderComparison View | (A) | api/views.py L52~423 |
| 공통 | Celery 주간 배치 (Task 1~5) | (A) | tasks.py run_weekly_validation_batch |

### 갭 요약

1. **Chain Sight 데이터 의존성 (Blocker)** — `CompanyNarrativeTag`, `CompanySensitivityProfile.foreign_revenue_pct`, `CompanyCapitalDNA.rd_to_revenue` 모두 0건. 결과로 Phase 7 LLM 필터의 "해외매출 50%+", "R&D 매출 10%+" 시나리오 동작 불가.
2. **Thesis 모델 필드 미추가** — `peer_preset_key`, `peer_filter_query`, `peer_filter_result` 필드 부재. 가설 빌더/관제실 연동 차단.
3. **thematic 프리셋 제한 구현** — 진정한 사업모델 테마 클러스터링이 아닌 DNA 유사도 수준.

### 폐기·대체 (D)

| 항목 | 사유 |
|------|------|
| 자본집약도 독립 프리셋 | quality_top 변형으로 흡수 |
| 시총 Top 10 프리셋 | 사업모델 혼재 위험 → 내부 후보 생성기로 강등 |
| 사용자 투표 기반 프리셋 | 별도 로드맵 (데이터 부족) |
| LLM 사업모델 큐레이션 | GrowthStage×CapitalDNA 대체 (임시) |

---

## News 상세

### 설계 문서별 분류

| 문서 | 핵심 기능 | 분류 | 근거 |
|------|---------|------|------|
| **keyword_detail_bottomsheet_v2.md** | Props 재설계, `max-w-2xl mx-auto`, 가로 Strip UI, `keepPreviousData` | (A) | KeywordDetailSheet.tsx L15~49, BottomSheet.tsx L38, useNews.ts L3/L145 |
| **news_keyword_detail_plan.md** | `/api/v1/news/keyword-detail/`, search_terms_en 확장, Gemini 실패 처리, 0건 처리, 타입/훅/서비스 | (A) | views.py L655 @action, keyword_extractor.py L43/L256~258, types/news.ts L134~140, hooks/useNews.ts L139~145, services/newsService.ts L234 |
| **news_pipeline_monitoring_design.md – Phase A** (collection-logs, pipeline-health, ml-trend, llm-usage + 6개 admin 컴포넌트) | (A) | views.py L1329/L1439/L1693/L1773, admin/news/{PipelineStatusBar, CollectionStatsTable, MLModelCard, MLTrendChart, RecentErrorsList, LLMUsageSummary}.tsx 전부 실존 |
| **news_pipeline_monitoring_design.md – Phase B** (task-timeline, neo4j-status, ml-rollback-preview, ml-rollback POST + 3개 컴포넌트) | (A) | views.py L1893/L1954/L2015/L2055, admin/news/{TaskTimelineChart, Neo4jStatusCard, MLCompareView}.tsx 전부 실존 |
| **news_pipeline_monitoring_design.md – Phase C** (AlertLog 모델, alerts GET/resolve POST, AlertBadge/AlertList) | (B) | models.py L684 AlertLog 정의, views.py L2100/L2164 action 정의, 프론트 컴포넌트 실존. 단 `check_pipeline_alerts` 자동 트리거 태스크 운영 여부 미확인 |

### 갭 요약

1. **Phase 0 `_log_collection()` 커버리지 부족** — 설계서 §11이 6개 태스크(collect_daily_news, collect_market_news, collect_category_news, classify_news_batch, analyze_news_deep, sync_news_to_neo4j)에 로깅 호출 추가를 권고했으나, 현재 4개(FMP/AV 중심)에만 적용된 흔적. 모니터링 통계 편향 가능.
2. **Phase C 자동 트리거** — `AlertLog` 모델·API는 완성. 그러나 30분 주기 Celery Beat에서 `check_pipeline_alerts` 태스크가 실제로 등록·실행 중인지 별도 확인 필요.
3. **`llm-usage` 응답 `coverage_warning`** — 미추적 토큰 경고 배너의 실제 렌더링 동작은 코드 리뷰 단계에서만 검증 가능 (파일 실존은 확인).

### 폐기·대체

- 없음. 설계 §10의 "절대 하지 말 것"(파이프라인 변경, ML 로직 변경, 일반 사용자 노출 등) 규칙 준수 (모든 모니터링 API에 IsAdminUser 적용).

---

## 종합 결론

- **SEC Pipeline**: 17 PR 100% 구현, 잔여 갭 없음. FMP 미지원 영역만 EDGAR로 합리적 대체.
- **Validation**: 핵심 아키텍처(프리셋 6종 + Compute-on-Read + LLM 필터) 완성. 잔여 작업 = ①Chain Sight 데이터 채우기 ②Thesis 모델 필드 + 마이그레이션 ③thematic 프리셋의 LLM 큐레이션 업그레이드.
- **News**: BottomSheet/Keyword Detail/모니터링 Phase A·B 완성, Phase C는 데이터/API 완성·자동화 트리거 운영 검증만 남음.

권장 후속 조치 (코드 수정 권한 회복 시):
1. `news/tasks.py` 전수 grep — `_log_collection()` 호출 누락 6 태스크 보강
2. `check_pipeline_alerts` 또는 동등 자동 트리거의 Beat 등록 여부 확인 (DatabaseScheduler 기준)
3. `thesis/models.py`에 `peer_preset_key`/`peer_filter_query`/`peer_filter_result` 필드 추가 + 마이그레이션
4. Chain Sight `CompanyNarrativeTag`/`SensitivityProfile`/`CapitalDNA` 데이터 백필 후 thematic 프리셋과 Phase 7 LLM 필터 시나리오 재활성
