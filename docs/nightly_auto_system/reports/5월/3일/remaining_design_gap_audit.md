# SEC Pipeline + Validation + News 설계 갭 감사

**감사 일자**: 2026-05-04
**감사자**: Claude Opus 4.7 (병렬 read-only 리서치 에이전트 3종)
**대상 브랜치**: `portfolio`
**감사 범위**: read-only — 코드 수정 없음

---

## 앱별 요약 (구현률)

| 앱 | 약속 산출물 | (A) 완전 | (B) 부분 | (C) 미구현 | (D) 폐기/대체 | 종합 평가 |
|----|-------------|---------|---------|------------|----------------|-----------|
| **SEC Pipeline** | ~78개 | ~73 (94%) | ~4 (5%) | ~1 (1%) | 1 (FMP→SEC EDGAR, DECISION-001) | 17 PR 거의 완전 이행. 미세 갭은 운영 자동화(Beat) + 테스트 부재. |
| **Validation** | 13개 | 11 (~85%) | 1 (~7%) | 1 (~8%, Phase 2 보류) | 1 (Thematic 입력 변경) | Phase 1~7 핵심 산출물 모두 동작. 엔드포인트 명칭/문서 갭 존재. |
| **News** | 35개 | 31 (~89%) | 3 (~9%) | 1 (~3%, 외부 알림 채널) | 0 | 설계 문서 3건 거의 완전 이행. 신규 API 테스트 부재가 본질적 갭. |

**전체 구현률**: 약 91% 완전 구현, 7% 부분/대체, 2% 미구현(대부분 의도된 보류).

**공통 갭 패턴 (3개 앱 횡단)**:
1. **신규 API 테스트 누락** — SEC Pipeline `tests.py` 빈 파일, News Phase A/B/C 모니터링 API 테스트 부재, Validation API 통합 테스트 미확인.
2. **CLAUDE.md/설계서 ↔ 실제 구현 명칭 드리프트** — SEC `/api/v1/sec/*` vs `/api/v1/sec-pipeline/*`, Validation `peer-filter/` vs `llm-filter/`, News 테스트 "607개" vs 실제 600개.
3. **운영 자동화 미완** — SEC Beat 스케줄 주석 상태, News AlertLog 외부 채널(Slack/이메일) 미구현, 운영 정리 태스크(`cleanup_old_collection_logs`) 미완.

---

## SEC Pipeline 상세

### 구현률 요약

- 전체 약속 산출물: **약 78개** (PR-1~17 보고서 항목 합산: 모델 8 + collector/validator/normalizer/extractor/prompts/exceptions/sp500 7 + tasks 6 + ticker_matcher/signals/merger/quality_checks/intelligence/on_demand 6 + admin 8개 모델 + views 2 + urls 2 + management cmd 3 + fixtures 2 + service 1 + 부속 ~33)
- (A) 완전 구현: **약 73개 (94%)**
- (B) 부분 구현: **약 4개 (5%)**
- (C) 미구현: **약 1개 (1%)**
- (D) 폐기/대체: **1개** (FMP → SEC EDGAR, `decisions/001_fmp_vs_sec_edgar_metadata.md`로 추적)

### PR별 매트릭스

| PR | 제목 | 분류 | 비고 |
|----|------|------|------|
| PR-1 | Django 앱 + 8개 모델 | A | `models.py`에 `RawDocumentStore`, `SupplyChainEvidence`, `BusinessModelSnapshot`, `BusinessModelEvidence`, `FilingProcessLog`, `CompanyAlias`, `UnmatchedCompanyQueue`, `PipelineIntelligenceReport` 모두 존재. `migrations/0001_initial.py` 단일. |
| PR-2 | SEC EDGAR 수집기 | A | `collector.py: SECFilingCollector` (`get_filing_metadata`, `fetch_filing_html`, `extract_sections`, `extract_sections_fallback`, `collect`) + `validators.validate_extracted_sections`. ToC 제거 + 다중 후보 + edgartools fallback. |
| PR-3 | Track A 키워드 + Gemini 추출 | A | `normalizer.py` (`normalize_section_all`, `filter_paragraphs`, ~35개 키워드), `prompts.PROMPT_VERSION='v1'`, `extractor.GeminiExtractor.extract_supply_chain` (gemini-2.5-flash, JSON, temp=0.1, thinking_budget=0), `validator_track_a` 전체. |
| PR-4 | Celery tasks + 예외 | A | `exceptions.py` 5개(`FilingCollectionError` 베이스 추가). `tasks.collect_and_extract`(retries=3), `extract_from_document`(retries=2), `_log_stage`. `sp500.get_sp500_symbols`. |
| PR-5 | Gold Set + 평가 | A | `fixtures/gold_set.json`(2.7KB, 10종목), `gold_set_schema.py`, `management/commands/evaluate_gold_set.py`(179줄). |
| PR-6 | Phase 1 배치 검증 | A | 운영 결과 보고서. `RawDocumentStore`/`SupplyChainEvidence` 카운트로 검증. |
| PR-7 | TickerMatcher + 큐 | **B** | `TickerMatcher.match`(alias→exact→fuzzy), `match_with_queue`. **임계값 갭**: 보고서 85% vs 코드 `_match_fuzzy(threshold=80)`. `rapidfuzz.token_sort_ratio` 사용. |
| PR-8 | Admin 큐 + signal | A | `admin.py` 8개 모델 + `UnmatchedCompanyQueueAdmin`(액션: `mark_not_public`, `mark_person`, `auto_resolve_top_candidate`). `signals.on_unmatched_resolved` post_save. `apps.ready()`에서 import. |
| PR-9 | sync_dirty_to_neo4j | A | Phase A(`select_for_update skip_locked`, 500건) → Phase B(DELETE+CREATE 동적 type, KNOWN_TYPES 6개+RELATED_TO) → Phase C(`neo4j_dirty=False`+`neo4j_synced_at`). |
| PR-10 | merger + 큐 처리 cmd | A | `merger.merge_relationship` (RELATIONSHIP_SPECIFICITY 점수, bounded boosting `existing+(1-existing)*new*0.3`, max 0.99, facets 5개), `calculate_edge_dqs`. `process_unmatched_queue.py`(67줄). |
| PR-11 | Track B 키워드 사전 | A | `keywords_track_b.BM_KEYWORDS` 5필드 + `filter_paragraphs_track_b`. |
| PR-12 | Track B Gemini + 검증 + 저장 | A | `prompts.PROMPT_VERSION_TRACK_B`, `extract_business_model`, `validator_track_b.save_business_model_snapshot` (BM Snapshot+Evidence). `extract_from_document`에서 Track A 실패해도 Track B 시도. |
| PR-13 | 서비스 레이어 (for_api) | A | `metrics/services/business_model_service.py` 위치 일치. `get_business_model`/`get_evidence`/`is_recurring` 약속 — 시그니처 직접 미열람. |
| PR-14 | Admin 대시보드 + 7 quality 체크 | A | `quality_checks.run_post_batch_quality_checks` 7개(임계값 모두 일치) + `get_dashboard_stats`. `views.sec_pipeline_dashboard` (`staff_member_required`), `urls.py admin/dashboard/`, `templates/admin/sec_pipeline/dashboard.html`. |
| PR-15 | On-demand + check_new_filings | A | `on_demand.get_or_collect_filing` (1년/1시간 중복 방지). `views.FilingDataView` 200/202. `urls.py filing/<str:symbol>/`. `tasks.check_new_filings` (FMP RSS 대신 SEC EDGAR submissions). |
| PR-16 | Pipeline Intelligence | A | `intelligence.PipelineDataCollector.collect`(5차원), `PipelineIntelligenceReporter.generate_report` (Gemini Flash, severity, dimension_scores, trend_vs_previous), `PIPELINE_INTELLIGENCE_PROMPT`. `PipelineIntelligenceReportAdmin`(severity_badge, regenerate_report). |
| PR-17 | E2E 통합 | **B** | `run_batch_and_report` 존재하나 Celery `chord` 대신 **순차 실행**. 보고서가 명시적으로 "1인 개발 단순성"으로 chord 대체를 인정. |

### 핵심 갭 (Top 5)

1. **`tests.py` 사실상 비어있음** — 26 bytes(`# Create your tests here.`만). 17 PR을 가진 앱치고 자동화 테스트 전무. 운영 검증은 `evaluate_gold_set` cmd + 수동 Celery로 갈음. **회귀 위험 큼.**
2. **Celery Beat 스케줄 주석 상태** — `tasks.py` 562~566줄 주석. PR-17 보고서도 인정. `sync_dirty_to_neo4j`(매 5분) / `check_new_filings`(매월 1일) 둘 다 자동 실행 안 됨 → 운영 시 수동 트리거 필요.
3. **`seed_relations_to_chainsight` task PR 외부 추가** — `tasks.py`에 존재하지만 PR-1~17 어디에도 명시되지 않음 (분류 D 또는 추가). chainsight 통합은 PR 추적 외에서 추가됨.
4. **`rematch_unmatched.py`, `seed_company_aliases.py`** — task_done에 명시되지 않음 (PR-10은 `process_unmatched_queue.py`만 약속). 후속 운영 도구로 추가됨 (mtime 4월 14일).
5. **`_match_fuzzy` 임계값 불일치** — 보고서 "≥85%" vs 코드 `threshold=80`. 실제 매칭에서 더 관대 → 정확도 영향 가능.

### URL/API 엔드포인트

- `urls.py`(app_name='sec_pipeline')에 등록된 라우트 **2개**:
  - `admin/dashboard/` → `views.sec_pipeline_dashboard`
  - `filing/<str:symbol>/` → `views.FilingDataView`
- `config/urls.py:40`: `path('api/v1/sec-pipeline/', include("sec_pipeline.urls"))` 마운트 → 실제 외부 URL은 `/api/v1/sec-pipeline/...`
- **CLAUDE.md `/api/v1/sec/*` 와 불일치** — 문서 갱신 필요 (또는 라우팅 변경).

### Track A vs Track B 상태

- **Track A (Supply Chain)**: 완전 구현. `normalizer.filter_paragraphs` → `extract_supply_chain` → `validator_track_a.save_supply_chain_evidences` → `ticker_matcher` → `sync_dirty_to_neo4j`. 110건 evidence.
- **Track B (Business Model)**: 완전 구현. `keywords_track_b.filter_paragraphs_track_b` → `extract_business_model` → `validator_track_b.save_business_model_snapshot`. Track A 실패에도 Track B 분리 보장. 5건 snapshot.

### 단계별 구현 상태

- **Phase 1 (배치)**: 완전 구현. PR-1~6. 15종목 배치 검증(93.3% 성공).
- **Phase 1.5 (Ticker/Neo4j sync)**: 완전 구현. PR-7~10. 매칭률 3% (비미국 주식 미등록이 본질적 한계).
- **Phase 2 (Track B + 서비스)**: 완전 구현. PR-11~13.
- **On-demand (PR-15)**: 완전 구현.
- **Intelligence (PR-16)**: 완전 구현.
- **E2E (PR-17)**: 부분 구현(B). chord 대신 순차.

### 마이그레이션 / 테스트 / Fixture

- **migrations**: 1개 (`0001_initial.py`, 13.4KB). 8개 모델 모두 초기 마이그레이션. 추가 schema 변경 없음 → 모델 안정.
- **tests.py**: 1줄 placeholder. 자동 테스트 전무.
- **fixtures/**: `gold_set.json`(10종목 라벨) + `gold_set_schema.py`. NVDA만 완전 라벨(PR-6 알려진 갭).
- **management/commands**: 4개 (`evaluate_gold_set`, `process_unmatched_queue`, `seed_company_aliases`, `rematch_unmatched`). 후자 2개는 PR 외 추가.

---

## Validation 상세

### 구현률 요약

- 전체 약속 산출물: **13개** (모델 5, 서비스 8개 클래스/모듈, API 6 엔드포인트, Celery 7 태스크, 프리셋 6종, Compute-on-Read, LLM 필터, Thematic, 배치 chain)
- (A) 완전 구현: **11개 (~85%)**
- (B) 부분 구현: **1개 (~7%)** — 명칭/연동 미세 갭
- (C) 미구현: **1개 (~8%)** — `validation_ai_cache` LLM 캐시 (Phase 2 보류 명시)
- (D) 폐기/대체: **1개** — Thematic 입력을 Chain Sight DNA로 대체 (`task_done/peer_phase6_thematic.md`에 기록)

### 영역별 매트릭스

| 영역 | 설계 약속 | 구현 상태 | 분류 | 비고 |
|------|-----------|-----------|------|------|
| **Peer 프리셋 6종** | default / sector_all / size_peers / quality_top / lifecycle / thematic + custom | 6종 모두 + custom | **A** | `services/preset_generator.py` 6개 `_generate_*`. logic_summary, confidence_score, is_active 포함. peer_count 7~514건 (Phase 6 결과 2,282건). |
| **Compute-on-Read 엔진** | 커스텀 peer 실시간 benchmark + Redis TTL 1h | 구현 | **A** | `services/custom_benchmark_engine.py`(161줄). 벌크 1회 쿼리 + percentile + 7카테고리 신호 + 한줄 요약 + `invalidate_cache`. |
| **LLM 대화형 필터 (Phase 7)** | `POST /peer-filter/` (자연어→JSON→필터) | 구현 (단, 명칭은 `llm-filter/`) | **B** (명칭 갭) | `services/llm_peer_filter.py`(264줄). Gemini 2.5 Flash sync, JSON mime, thinking_budget=0. Chain Sight 6필드 + foreign_revenue + metric_filters + sector/industry 제외. Thesis 모델 필드 연동은 코드상 미확인. |
| **Thematic Peer (Phase 6)** | LLM Gemini로 theme_tags 클러스터링, `CompanyNarrativeTag.theme_tags` 기반 | **대체 구현**: GrowthStage × CapitalDNA 조합 | **D** (의도된 대체) | 463/503 종목 생성. 섹터 횡단 보너스 +0.1 confidence. theme_tags LLM 배치 미실행 (Chain Sight 데이터 대체, task_done에 명시). |
| **REST API** | summary/metrics/leader-comparison/presets/peer-preference/peer-filter | 6 라우트 + 명칭 1건 변경 | **A** | `api/urls.py` 6 path. `peer-filter/` → `llm-filter/` 명칭만 차이. `config/urls.py:38` 마운트. |
| **Celery 태스크 chain** | Task 1~6 + 3.5 (총 7) + `run_weekly_validation_batch` | 7개 + chain | **A** | `tasks.py`(160줄). 모두 `@shared_task(bind=True)` + retry/timeout. Beat(`crontab(day_of_week='sunday', hour=2)`)는 `config/celery.py` 별도 (검증 미수행). |
| **모델 확장 필드** | snapshot.value_status / delta.benchmark_basis,confidence / peer_list_cache.* / industry.handling_mode / category_signal | 모두 구현 | **A** | snapshot/peer_list_cache/industry는 metrics/stocks 앱에 위치. validation 자체는 5 모델 + preset_key 0004 마이그레이션. |
| **`validation_ai_cache`** | Phase 2 검토 | 미구현 (보류) | **C** | rule-based만. `summary_source: 'rule'` 하드코딩. |
| **`seed_validation_data.py`** | 시드 명령 | 구현 | **A** | `management/commands/seed_validation_data.py`. |

### 핵심 갭 (Top 5)

1. **API 엔드포인트 명칭 불일치** — 설계서(`validation_peer_phase6_7.md` Step 2): `POST /peer-filter/`. 구현: `POST /llm-filter/`. 프론트엔드 통합 시 contract 갭.
2. **Thematic 입력 전환 미반영** — 설계서는 Gemini 사업모델 태깅 → `CompanyNarrativeTag.theme_tags`였으나, 구현은 `CompanyGrowthStage` × `CompanyCapitalDNA` 조합. task_done엔 기록되어 있으나 설계서 본문엔 미반영. (DECISIONS.md 갱신 권고)
3. **Thesis Control 연동 미완** — 설계서 `validation_peer_phase6_7.md:255-263`의 `Thesis.peer_preset_key/peer_filter_query/peer_filter_result` 필드 + 가설 빌더/관제실 탭 통합은 validation 코드에서 확인 불가. (thesis 앱 별도 검사 필요)
4. **SP500 외 종목 처리** — `ValidationSummaryView`가 비-SP500에 `not_in_universe` 200 반환. custom peer로 비-SP500 포함 시 동작이 모호.
5. **`validation_ai_cache` 미존재** — 설계상 Phase 2 보류. `summary_source`/`interpretation_source`는 `'rule'` 고정 — Phase 2 진입 시 분기 필요.

### 모델 인벤토리 (5개)

| 클래스 | 파일 | 역할 |
|---|---|---|
| `CompanyMetricLatest` | `metric_latest.py` | 종목별 지표 최신값/추세/신호등 캐시 |
| `CompanyBenchmarkDelta` | `benchmark_delta.py` | 종목 vs peer/industry 비교 (preset_key 포함) |
| `CategorySignal` | `category_score.py` | 7카테고리 신호등 (preset_key, contributing_metrics JSON) |
| `ValidationNewsSummary` | `news_summary.py` | 1차 검증용 뉴스 감성/이벤트 집계 |
| `PeerPreset`, `UserPeerPreference` | `peer_preset.py` | 프리셋 메타 + 사용자 선택 |

`PeerListCache`, `IndustryClassification`, `CompanyMetricSnapshot`은 metrics/stocks 앱.

### 서비스 인벤토리 (9개)

- `benchmark_calculator.BenchmarkCalculator`(345줄) — `assign_size_bucket`, `_calculate_benchmarks_for_year`
- `category_signal_calculator.CategorySignalCalculator`(192줄) — `CATEGORY_METRICS` 7카테고리×34지표
- `custom_benchmark_engine.CustomBenchmarkEngine`(161줄) — Compute-on-Read + Redis 캐시
- `financial_fetcher.FinancialFetcher`(103줄) — 재무제표 가용성
- `interpretation`(121줄) — rule-based summary/interpretation
- `llm_peer_filter`(264줄) — `parse_filter_with_llm` + `execute_peer_filter`
- `metric_calculator.MetricCalculator`(459줄) — 33개 지표 + value_status 판정
- `preset_generator.PresetGenerator`(479줄) — 6종 프리셋 + `_calc_confidence`
- `relative_metrics.RelativeMetricCalculator`(97줄)

### URL/API 엔드포인트 (6개)

- `GET /api/v1/validation/<symbol>/summary/`
- `GET /api/v1/validation/<symbol>/metrics/?category=`
- `GET /api/v1/validation/<symbol>/leader-comparison/`
- `GET /api/v1/validation/<symbol>/presets/`
- `POST/DELETE /api/v1/validation/<symbol>/peer-preference/`
- `POST /api/v1/validation/<symbol>/llm-filter/` (설계서 명: `peer-filter/`)

### 테스트 / 마이그레이션

- **migrations**: 4개 (`0001_initial`, `0002_validationnewssummary_categoryscore`, `0003_companybenchmarkdelta_benchmark_basis_and_more`, `0004_alter_categorysignal_unique_together_and_more`). 0004에서 PeerPreset/UserPeerPreference 신규 + preset_key. **LLM 필터 관련 모델 마이그레이션 없음**(서비스 + API만).
- **테스트**: `tests/unit/validation/` 6개 파일, **154개** 함수 (test_benchmark_calculator 22, test_interpretation 26, test_metric_calculator 36, test_preset_generator 14, test_relative_metrics 8, test_services_extended 48). 서비스 단 단위 테스트 위주. **API 통합 테스트(views.py 6 엔드포인트), Celery chain E2E, `llm_peer_filter` 단위 테스트는 별도 파일 미확인** — `test_services_extended.py`에 일부 포함됐을 가능성. `validation/tests.py`는 1줄 placeholder.

---

## News 상세

### 구현률 요약

- 전체 약속 산출물: **35개**
- (A) 완전 구현: **31개 (≈89%)**
- (B) 부분 구현: **3개 (≈9%)**
- (C) 미구현: **1개 (≈3%)**
- (D) 폐기/대체: **0개**

### 설계 문서별 매트릭스

| 설계 문서 | 약속 산출물 | 구현 위치 | 분류 |
|-----------|------------|-----------|------|
| **keyword_detail_bottomsheet_v2** | `BottomSheet.tsx max-w-2xl mx-auto` | `frontend/components/thesis/common/BottomSheet.tsx` | A |
| ↳ | `KeywordDetailSheet` Props (`initialIndex` + `keywords[]`) + 가로 Strip + activeIndex + scrollIntoView | `frontend/components/news/KeywordDetailSheet.tsx` | A |
| ↳ | `DailyKeywordCard.tsx` props 변경 | `frontend/components/news/DailyKeywordCard.tsx` | A |
| ↳ | `useNews.ts keepPreviousData` (TanStack Query v5) | `frontend/hooks/useNews.ts` | A |
| **news_keyword_detail_plan** | `keyword_extractor.py search_terms_en` 프롬프트 확장 | `news/services/keyword_extractor.py:241,256-258,306` | A |
| ↳ | `GET /api/v1/news/keyword-detail/?date=&index=` API | `news/api/views.py:640-774` | A |
| ↳ | Redis 캐시(`updated_at` epoch, TTL 1h) | `views.py:696-698, 772` | A |
| ↳ | Gemini 실패 시 `analysis: null` | `views.py:759-761` | A |
| **news_pipeline_monitoring §11 Phase 0** | 누락 6 태스크에 `_log_collection()` | `tasks.py:178, 220, 454, 500, 543, 621` | A |
| **§3.1 Phase A** | `GET /collection-logs/` (`days`, `provider`, `task_name`, by_provider) | `views.py:1314` | A |
| **§3.2** | `GET /pipeline-health/` (PHASE_CONFIG 6단계, weekday_only, force_refresh) | `views.py:1424-1453` | A |
| **§3.3** | `GET /ml-trend/?weeks=` | `views.py:1678` | A |
| **§3.4** | `GET /llm-usage/?days=` (coverage_warning) | `views.py:1758` | A |
| **§4 Phase A FE** | sub-tab + 6 컴포넌트 + hook + service | `frontend/components/admin/news/{...}.tsx` 등 | A |
| **§5.1 Phase B** | `GET /task-timeline/?hours=24` + `TaskTimelineChart.tsx` | `views.py:1878` + FE | A |
| **§5.2 Phase B** | `GET /neo4j-status/` + `Neo4jStatusCard.tsx` | `views.py:1939` + FE | A |
| **§5.3 Phase B** | `GET /ml-rollback-preview/` + `POST /ml-rollback/` (confirm 검증) + `MLCompareView.tsx` | `views.py:2000, 2040` + FE | A |
| **§6 Phase C** | `AlertLog` 모델 (Severity/TriggerType TextChoices) | `models.py:684-727` | A |
| ↳ | `GET /alerts/` + `POST /alerts/<id>/resolve/` | `views.py:2085, 2149` | A |
| ↳ | `check_pipeline_alerts` Celery 태스크 | `tasks.py:1101-1102` | A |
| ↳ | `AlertBadge.tsx` + `AlertList.tsx` | `frontend/components/admin/news/` | A |
| ↳ | `news/admin.py`에 `AlertLogAdmin` | (미확인) | **B** |
| ↳ | Slack/이메일 알림 채널 (선택) | 코드 미확인 | **C** |
| ↳ | 마이그레이션 0006_alertlog | `news/migrations/0006_alertlog.py` | A |

### Intelligence Pipeline v3 매트릭스

| 컴포넌트 | 구현 위치 | 분류 |
|----------|-----------|------|
| 규칙 엔진 (Engine A/B/C) | `services/news_classifier.py`(14k) + `keyword_sector_map.py` + `NewsArticle.{importance_score, rule_sectors, rule_tickers}` | A |
| LLM 분석 (Gemini) | `services/news_deep_analyzer.py` + `tasks.analyze_news_deep` (Tier A/B/C) + `keyword_extractor.py` | A |
| ML 학습 (LightGBM) | `services/ml_weight_optimizer.py:963 train_lightgbm` + `tasks.train_lightgbm_model` | A |
| Neo4j 뉴스 이벤트 | `services/news_neo4j_sync.py`(37k) + `tasks.sync_news_to_neo4j` + `cleanup_expired_news_relationships` | A |
| Shadow/Production Mode | `MLModelHistory.deployment_status ∈ {shadow, deployed, rolled_back, failed}` + `services/ml_production_manager.py` + `tasks.{generate_shadow_report, check_auto_deploy, rollback_model}` | A |

### 핵심 갭 (Top 5)

1. **AlertLog Slack/이메일 송신 채널** (Phase C 선택사항) — DB 인앱 알림은 동작하나 외부 채널 송신 코드 미확인 (설계상 "선택").
2. **`AlertLogAdmin`** — 설계 §7 명시(+25줄). `admin.py`(5825 bytes)에서 명시적 확인 안 됨.
3. **테스트 갯수 불일치** — CLAUDE.md "607개" vs 실제 `tests/news/` 12 파일, 10,874줄, `def test_` **600개**. **Phase A/B/C 신규 API 테스트 파일 부재** (예: `test_pipeline_health.py`, `test_collection_logs.py`, `test_alerts.py`, `test_keyword_detail.py` 없음).
4. **`NewsCollectionLog` 보존 정책** — 설계 §9 "추후 `cleanup_old_collection_logs` 태스크 추가 권고" 미구현. tasks.py에 `cleanup_expired_news_relationships`(Neo4j용)와 `archive_old_articles`만 존재.
5. **수집량 급감 트리거 "5 평일 평균"** — 트리거 이름 `COLLECTION_DROP` enum 등록 확인. `check_pipeline_alerts` 내부 로직 정확성은 본 감사에서 미검증.

### 모델/서비스/프로바이더 인벤토리

- **models.py 9개**: `NewsArticle`, `NewsEntity`, `EntityHighlight`, `SentimentHistory`, `DailyNewsKeyword`, `MLModelHistory`, `NewsCollectionCategory`, `NewsCollectionLog`, `AlertLog`
- **services/ 17개**: `aggregator`, `circuit_breaker`, `deduplicator`, `interest_options`, `keyword_extractor`, `keyword_sector_map`, `market_feed`, `ml_label_collector`, `ml_production_manager`, `ml_weight_optimizer`, `news_classifier`, `news_deep_analyzer`, `news_neo4j_sync`, `personalized_feed`, `sentiment_normalizer`, `stock_insights`, `stock_recommender`
- **providers/ 4개**: `base`, `finnhub`, `marketaux`, `fmp` (NewsAPI 미사용, Alpha Vantage는 `tasks.py`에서 직접 호출 + `_log_collection('alpha_vantage', ...)`)
- **migrations/ 6개**: 0001~0006_alertlog (0004는 v3 핵심, 0006이 Phase C)

### URL/API 엔드포인트 (31개)

`urls.py`는 단일 `DefaultRouter().register(r'', NewsViewSet)` — 모든 라우트 `@action`으로 자동 등록.

- **기존**: `stock/<symbol>`, `stock/<symbol>/sentiment`, list/trending(5개 무명), `all`, `daily-keywords`, `daily-keywords/generate`
- **Plan v2**: `keyword-detail` ✓
- **시장**: `market-feed`, `interest-options`, `personalized-feed`, `news-events`, `news-events/impact-map`
- **ML 기존**: `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`
- **Phase A 모니터링**: `collection-logs`, `pipeline-health`, `ml-trend`, `llm-usage`
- **Phase B 모니터링**: `task-timeline`, `neo4j-status`, `ml-rollback-preview`, `ml-rollback` (POST)
- **Phase C 모니터링**: `alerts`, `alerts/<alert_pk>/resolve` (POST)

### Celery 태스크 / Beat 스케줄

- **22개 태스크** (`tasks.py` 1433줄). 카테고리별 수집(`collect_category_news`)이 `NewsCollectionCategory.resolve_symbols()`(models.py:638-660)로 sector/sub_sector/custom 3분기 처리. **A**.
- Beat 스케줄은 `config/celery.py` 영역으로 본 감사 범위 외.

### 테스트

- `news/tests.py`: 60 bytes (사실상 빈 파일)
- `tests/news/`: 12 파일, **10,874줄, `def test_` 600개** (CLAUDE.md "607개"와 7개 차이)
- **Phase A/B/C 모니터링 API + keyword-detail API 전용 테스트 파일 부재**. ML/Classifier/Deep Analyzer/Neo4j Sync/LightGBM 등 서비스 레이어 테스트는 풍부.

---

## 종합 권고

### 우선순위 1 — 즉시 조치
1. **CLAUDE.md URL prefix 통일** — `/api/v1/sec/*` → `/api/v1/sec-pipeline/*` (또는 라우팅 변경, 단 후자는 프론트엔드 영향).
2. **Validation `peer-filter/` ↔ `llm-filter/` 명칭 통일** — 설계서 또는 구현 어느 한쪽으로 일치.
3. **News 테스트 갯수 동기화** — CLAUDE.md "607개" → "600개" 정정.

### 우선순위 2 — 다음 스프린트
1. **SEC Pipeline 단위 테스트 추가** — 17 PR짜리 앱에 자동화 테스트 전무. Gold Set 평가 cmd만으로는 회귀 방지 불충분. 최소 `extractor`, `validator_track_a/b`, `merger` 핵심 로직.
2. **News 신규 API 테스트 추가** — Phase A/B/C 모니터링 API 8개 + keyword-detail API 1개 전용 테스트. 테스트 풍부도와 신규 API 테스트 부재의 비대칭이 위험 신호.
3. **SEC Beat 스케줄 활성화** — `sync_dirty_to_neo4j`(5분), `check_new_filings`(매월 1일) 주석 해제. 운영 자동화의 마지막 1km.
4. **Validation Thesis 연동 검증** — `Thesis.peer_preset_key/peer_filter_query/peer_filter_result` 필드 추가가 thesis 앱에 실제로 반영됐는지 별도 감사 필요.

### 우선순위 3 — 추후
1. **News AlertLog 외부 채널** (Slack/이메일) — 설계상 선택이나, Phase C 알림이 인앱에만 머무르면 야간 사고 대응 어려움.
2. **News `cleanup_old_collection_logs` 태스크** — `NewsCollectionLog` 무한 누적 방지.
3. **SEC `_match_fuzzy` 임계값 정합** — 보고서 85% vs 코드 80%. 어느 쪽이 정답인지 확정 후 통일.
4. **Validation `validation_ai_cache` Phase 2 진입 결정** — `summary_source: 'rule'` 하드코딩 분기 가능 시점 판단.
5. **DECISIONS.md ↔ task_done 동기화** — Validation Thematic 입력 변경처럼, task_done에만 기록되고 설계서/DECISIONS.md엔 미반영된 결정들 정리.

### 문서 갱신 권고

- `CLAUDE.md` § 자주 발생하는 버그: SEC URL prefix 불일치(신규 항목)
- `docs/sec_pipeline/` — `_match_fuzzy` 임계값, Beat 미활성, 추가된 management cmd 2개에 대한 보강 메모
- `docs/first_validation_system/validation_peer_phase6_7.md` — Thematic 입력 전환 본문 반영, `peer-filter/` ↔ `llm-filter/` 명칭 정합
- `docs/news/plan/news_pipeline_monitoring_design.md` § 9 — `cleanup_old_collection_logs` 미구현 표시

---

**감사 종료**.
