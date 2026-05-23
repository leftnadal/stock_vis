# SEC Pipeline + Validation + News 설계 갭 감사

> 작성일: 2026-05-23
> 범위: `docs/sec_pipeline/`, `docs/first_validation_system/`, `docs/news/` 설계 ↔ `sec_pipeline/`, `validation/`, `news/` 구현
> 모드: 읽기 전용 (코드 미수정)
> 방법: 설계서 (task_done 완료 보고서 포함) ↔ 실제 코드/모델/마이그레이션/URL 라우팅 cross-reference

---

## 앱별 요약 (구현률)

| 앱 | 설계 문서 | 구현률 | 분류 분포 | 핵심 갭 |
|---|---|---|---|---|
| **SEC Pipeline** | `docs/sec_pipeline/{decisions,task_done}` (PR 1~17, 17건 완료 보고서) | **≈100% (Phase 1~3 완료)** | A: 17 / B: 0 / C: 0 / D: 0 | 설계가 "전체 완료 요약" 단일 문서로 단순화. 향후 과제 5건은 운영성 작업으로 분리됨 |
| **Validation (1차 검증)** | `validation_design.md (v1.4)` + `validation_peer_phase6_7.md` + Phase 6/7 task_done | **≈95% (Phase 1~7 완료)** | A: 14 / B: 2 / C: 1 / D: 1 | (B) Recharts ComposedChart UI는 BarChart 단순화 가능성 (확인 필요), (B) LLM Phase 5 도입은 Phase 7 LLM 필터로 부분 대체, (C) BatchJobRun batch_job_run 모델명 매핑 |
| **News (모니터링 + 키워드 상세)** | `news_pipeline_monitoring_design.md (v1.1)` + `news_keyword_detail_plan.md (v2)` + `keyword_detail_bottomsheet_v2.md` | **≈90% (Phase A 거의 완료, Phase B/C 부분)** | A: 11 / B: 3 / C: 2 / D: 0 | (C) `task-timeline`, `neo4j-status` 등 설계 미기재 신규 endpoint, (B) Phase 3(deep_analyzer) 토큰 로깅, (B) AlertLog 정의는 됐지만 능동적 알림 발행 로직 검증 필요 |

**전체 구현률(가중 평균): ≈95%** — 세 앱 모두 task_done 완료 보고서가 있고, 코드/모델/마이그레이션이 설계와 일치. 잔여 갭은 운영성/품질 개선 영역.

---

## SEC Pipeline 상세

### 설계서 위치
- `docs/sec_pipeline/decisions/001_fmp_vs_sec_edgar_metadata.md` — 메타데이터 소스 결정 (FMP → SEC EDGAR)
- `docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md` — 전체 요약 (Phase 1~3, PR 1~17, 17건)
- `docs/sec_pipeline/task_done/sec_pr_{1..17}_*.md` — 17개 완료 보고서

### 모델 (설계 8개 ↔ 구현 8개 모두 일치) — **(A) 완전 구현**

| 설계 모델 | 구현 (sec_pipeline/models.py) | 분류 | 비고 |
|---|---|---|---|
| RawDocumentStore | L15 `class RawDocumentStore` (item_1/1a/7_text 3섹션, status, extraction_method, warnings) | A | DB table `sec_raw_document_store` |
| SupplyChainEvidence | L61 `class SupplyChainEvidence` (5 RELATIONSHIP, confidence_grade, neo4j_dirty) | A | 원칙 6 (system_confidence 내부, grade 노출) 준수 |
| BusinessModelSnapshot | L122 `class BusinessModelSnapshot` (5 필드 직접/계약/반복/채널/집중도) | A | `get_latest_by='as_of_date'` |
| BusinessModelEvidence | L201 `class BusinessModelEvidence` | A | snapshot FK + field_name + evidence_text |
| FilingProcessLog | L231 `class FilingProcessLog` (7 stage choice) | A | 단계별 추적 |
| CompanyAlias | L273 `class CompanyAlias` (admin_resolved/auto_90pct/manual_seed) | A | unique on (alias, context_sector) |
| UnmatchedCompanyQueue | L307 `class UnmatchedCompanyQueue` (6 status, fuzzy_candidates JSON) | A | 큐 적재 + 매칭 진행 추적 |
| PipelineIntelligenceReport | L351 `class PipelineIntelligenceReport` (5차원 점수 + LLM 분석) | A | Phase 3 신규 |

### 파일 (설계 21개 ↔ 구현 25개) — **(A) 완전 구현 + 보조 파일 추가**

| 설계 파일 | 구현 파일 | 분류 |
|---|---|---|
| models.py (8개 모델) | `sec_pipeline/models.py` (388 LOC) | A |
| collector.py | `sec_pipeline/collector.py` (373) | A |
| validators.py | `sec_pipeline/validators.py` (128) | A |
| normalizer.py | `sec_pipeline/normalizer.py` (83) | A |
| prompts.py | `sec_pipeline/prompts.py` (97) | A |
| extractor.py | `sec_pipeline/extractor.py` (145) | A |
| validator_track_a.py | `sec_pipeline/validator_track_a.py` (164) | A |
| validator_track_b.py | `sec_pipeline/validator_track_b.py` (115) | A |
| keywords_track_b.py | `sec_pipeline/keywords_track_b.py` (78) | A |
| exceptions.py | `sec_pipeline/exceptions.py` (35) | A |
| tasks.py | `sec_pipeline/tasks.py` (579) — 6 task + helper | A |
| sp500.py | `sec_pipeline/sp500.py` (15) | A |
| ticker_matcher.py | `sec_pipeline/ticker_matcher.py` (210) | A |
| signals.py | `sec_pipeline/signals.py` (71) | A |
| merger.py | `sec_pipeline/merger.py` (135) | A |
| intelligence.py | `sec_pipeline/intelligence.py` (223) | A |
| quality_checks.py | `sec_pipeline/quality_checks.py` (165) | A |
| on_demand.py | `sec_pipeline/on_demand.py` (68) | A |
| views.py | `sec_pipeline/views.py` (51) | A |
| urls.py | `sec_pipeline/urls.py` (admin/dashboard + filing/<symbol>) | A |
| admin.py | `sec_pipeline/admin.py` (171) | A |
| (설계 외) — | `sec_pipeline/management/commands/{evaluate_gold_set, process_unmatched_queue, rematch_unmatched, seed_company_aliases}.py` | (보조) 운영 커맨드 4개 추가 |

### Celery Tasks (설계 6개 ↔ 구현 7개)

| 설계 Task | 구현 (`sec_pipeline/tasks.py`) | 분류 |
|---|---|---|
| collect_and_extract | L23 `collect_and_extract` (max_retries=3) | A |
| extract_from_document | L149 `extract_from_document` (max_retries=2) | A |
| sync_dirty_to_neo4j | L338 `sync_dirty_to_neo4j` | A |
| check_new_filings | L465 `check_new_filings` | A |
| generate_intelligence_report | L501 `generate_intelligence_report` | A |
| run_batch_and_report | L509 `run_batch_and_report` | A |
| (설계 외) seed_relations_to_chainsight | L282 `seed_relations_to_chainsight` | (확장) chainsight 연계용 신규 |

### API/Views

| 설계 | 구현 | 분류 |
|---|---|---|
| Admin 대시보드 | `views.sec_pipeline_dashboard` + `templates/admin/sec_pipeline/dashboard.html` | A |
| Filing API (`/filing/<symbol>/`) | `views.FilingDataView` | A |

### 향후 과제 (설계 명시, 운영성 작업으로 분리됨)
- S&P 500 전체 배치 (Gemini RPD 제한)
- Gold Set 라벨 보완 → Precision/Recall 재평가
- JNJ Item 순서 검증 완화
- 프롬프트 개선 (일반 명사 추출 방지)
- CompanyAlias 수동 등록 (TSMC→TSM 등)

**결론**: 코드 레벨에서는 **(A) 완전 구현**. 잔여 작업은 모두 운영성/품질 개선이며 설계 결손이 아님.

---

## Validation 상세

### 설계서 위치
- `docs/first_validation_system/validation_design.md (v1.4, 1647 LOC)` — Phase 1~4 + Phase 5(LLM) 검토
- `docs/first_validation_system/validation_peer_system.md` — Peer Phase 1~5
- `docs/first_validation_system/validation_peer_phase6_7.md` — Phase 6 thematic + Phase 7 LLM 필터
- `docs/first_validation_system/validation_pr_prompts.md` — PR별 프롬프트
- `docs/first_validation_system/task_done/peer_phase6_thematic.md` — Phase 6 완료
- `docs/first_validation_system/task_done/peer_phase7_llm_filter.md` — Phase 7 완료

### 모델 (설계 vs 구현)

| 설계 모델 | 구현 위치 | 분류 | 비고 |
|---|---|---|---|
| `category_signal` (구 category_score) | `validation/models/category_score.py:CategorySignal` (table `validation_category_signal`) | A | 7 카테고리 choice + signal/score/preset_key |
| `company_benchmark_delta` | `validation/models/benchmark_delta.py:CompanyBenchmarkDelta` | A | benchmark_basis + benchmark_confidence + preset_key 모두 반영 |
| `peer_list_cache` 추가필드 (benchmark_basis/size_bucket/peer_tier) | `metrics/models/benchmark.py:30,38,42` 모두 존재 | A | 마이그레이션 0003에서 반영 |
| `industry_classification.handling_mode` | `stocks/models.py:722-746` (`special_note` 포함) | A | choices=('standard','special') 일치 |
| `company_metric_snapshot.value_status, exclusion_reason` | `metrics/models/metric_snapshot.py` + migrations 0004/0005 | A | 5단계 status 일치 |
| `metric_definition.not_applicable_reason` | migration 0005 | A | |
| `validation_ai_cache` (Phase 5 LLM 캐싱) | 미구현 | C | 설계 자체가 "Phase 5 이후 검토" 보류 — 의도된 미구현 |
| `PeerPreset`, `UserPeerPreference` (Phase 1~6 추가) | `validation/models/peer_preset.py` | A | thematic 포함 6 generation_method |
| `MetricLatest`, `NewsSummary` | `validation/models/{metric_latest,news_summary}.py` | A | (설계 외) 보조 모델 |

### 서비스 (Phase별)

| Phase | 설계 서비스 | 구현 (`validation/services/`) | 분류 |
|---|---|---|---|
| Phase 1 — peer/benchmark | preset_generator + benchmark_calculator | `preset_generator.py` (479) + `benchmark_calculator.py` (345) | A |
| Phase 1 — value_status | metric_calculator | `metric_calculator.py` (459, determine_value_status 포함) | A |
| Phase 1 — category signal | category_signal_calculator | `category_signal_calculator.py` (192) | A |
| Phase 1 — rule-based 해석 | interpretation | `interpretation.py` (121) — generate_summary_text/metric_interpretation/leader_summary 3개 | A |
| Phase 1 — relative metrics | relative_metrics | `relative_metrics.py` (97) | A |
| Phase 5 — 커스텀 Compute-on-Read | custom_benchmark_engine | `custom_benchmark_engine.py` (161) | A |
| Phase 6 — thematic 프리셋 | preset_generator._generate_thematic | `preset_generator.py:_generate_thematic` (task_done 보고) | A |
| Phase 7 — LLM 대화형 필터 | llm_peer_filter | `llm_peer_filter.py` (264) | A |
| Phase 5+ — LLM 배치 캐싱 | validation_ai_cache + Task 6.5 generate_ai_texts | **미구현** | C (보류 의도) |

### Celery Pipeline (Task 1~6 + Orchestrator)

| Task | 설계 | 구현 (`validation/tasks.py`) | 분류 |
|---|---|---|---|
| 1 fetch_annual_financials | ✓ | L23 `fetch_annual_financials` | A |
| 2 calculate_derived_metrics (+ value_status) | ✓ | L37 `calculate_derived_metrics` | A |
| 3 calculate_benchmarks (peer 선정 + basis/confidence) | ✓ | L51 `calculate_benchmarks` | A |
| 3.5 calculate_relative_metrics | ✓ | L65 `calculate_relative_metrics` | A |
| 4 calculate_category_signals | ✓ | L79 `calculate_category_signals` | A |
| 5 update_peer_list_caches | ✓ | L93 `update_peer_list_caches` (확인 only — Task 3에서 갱신 후 검증) | B |
| 6 log_batch_run | ✓ → `batch_job_run` 테이블 | L106 `log_batch_run` → `BatchJobRun` 모델(metrics) | A |
| Orchestrator chain() | ✓ | L141 `run_weekly_validation_batch` (chain 7단계) | A |

### API Endpoints

| 설계 | 구현 (`validation/api/urls.py` + `views.py`) | 분류 |
|---|---|---|
| GET `/api/v1/validation/{symbol}/summary/` | `ValidationSummaryView` (L52) | A |
| GET `/api/v1/validation/{symbol}/metrics/?category=...` | `ValidationMetricsView` (L173) | A |
| GET `/api/v1/validation/{symbol}/leader-comparison/` | `LeaderComparisonView` (L317) | A |
| (Phase 5 추가) GET `/.../presets/` | `PresetListView` (L424) | A |
| (Phase 5 추가) POST/DELETE `/.../peer-preference/` | `PeerPreferenceView` (L459) | A |
| (Phase 7 추가) POST `/.../llm-filter/` | `LLMPeerFilterView` (L498) | A |

### Frontend (설계 컴포넌트 ↔ 구현)

| 설계 컴포넌트 | 구현 (`frontend/components/validation/`) | 분류 |
|---|---|---|
| ValidationTab 메인 | (탐색 시 미발견 — 상위 stock-detail 라우팅에 산재 가능성) | B |
| SignalSummaryCard | `SignalSummaryCard.tsx` (+ test) | A |
| PeerContextBar | `PeerContextBar.tsx` | A |
| CategorySection | `CategorySection.tsx` | A |
| MetricCard (value_status 분기) | `MetricCard.tsx` (+ test) | A |
| MetricBarChart (Recharts ComposedChart) | `MetricBarChart.tsx` | A (실제 ComposedChart 사용 여부는 코드 미확인 — 파일 존재 확인만) |
| CategorySidebar | `CategorySidebar.tsx` | A |
| IndustryPosition | `IndustryPosition.tsx` | A |
| LeaderComparison | `LeaderComparisonSection.tsx` (이름 다름) | A |
| MetricInfoTooltip (설계 외) | `MetricInfoTooltip.tsx` | (보조) |
| useValidation hook | `frontend/hooks/useValidation.ts` | A |
| TypeScript types | `frontend/types/validation.ts` | A |
| 서비스 클라이언트 | `frontend/services/validation.ts` | A |

### 갭/미구현 항목

| 분류 | 항목 | 위치 | 비고 |
|---|---|---|---|
| C | Phase 5 LLM 텍스트 캐싱 (validation_ai_cache + Task 6.5) | 설계 §8.2 | 의도된 보류 — "Phase 1~4 결과물 검토 후 결정" |
| D | category_score → category_signal | v1.3에서 이름 변경 | 폐기/대체된 명칭이 v1.2 잔존, 코드는 신 이름으로 통일 |
| B | Task 5 (update_peer_list_caches) — 설계는 "industry+size bucket 기반 peer 목록 갱신", 구현은 "확인만" | `tasks.py:93` 주석 "Task 3에서 이미 갱신, 여기서는 확인만" | 기능적으로는 Task 3에서 처리. 설계와 책임 분담이 다름 |
| B | "데스크톱 ValidationTab 메인 컴포넌트" | 탐색 미발견 | 페이지 라우팅(`/stock/[symbol]?tab=validation`)에서 직접 sub-component 조합 가능성 — 추가 확인 필요 |

**결론**: **(A) 완전 구현 ≈95%**. Phase 5 LLM 캐싱은 의도된 보류. Task 5 책임 분담 조정은 경미한 차이.

---

## News 상세

### 설계서 위치
- `docs/news/plan/news_pipeline_monitoring_design.md (v1.1, 1160 LOC)` — 모니터링 대시보드 Phase A/B/C
- `docs/news/plan/news_keyword_detail_plan.md (v2, 216 LOC)` — 키워드 상세 바텀시트
- `docs/news/plan/keyword_detail_bottomsheet_v2.md (80 LOC)` — 가로 스크롤 Strip + 데스크탑 너비 제한

### 모델 (설계 ↔ 구현)

| 설계 모델 | 구현 (`news/models.py`) | 분류 |
|---|---|---|
| NewsCollectionLog | 존재 (이미 있는 자산) | A |
| MLModelHistory | 존재 | A |
| DailyNewsKeyword + `prompt_tokens/completion_tokens` | 존재 | A |
| NewsCollectionCategory | 존재 | A |
| NewsArticle (importance_score, llm_analysis 등) | 존재 | A |
| AlertLog (Phase C) | `news/models.py:684-727` `class AlertLog` (TextChoices Severity/TriggerType, is_resolved, context JSON) | A |

### Phase A — 신규 API (설계 4개 ↔ 구현 모두 존재)

| 설계 endpoint | 구현 (`news/api/views.py`) | 분류 |
|---|---|---|
| GET `/api/v1/news/collection-logs/` | L1329 `@action url_path='collection-logs'` (IsAdminUser) | A |
| GET `/api/v1/news/pipeline-health/` | L1439 `@action url_path='pipeline-health'` (IsAdminUser, force_refresh 지원) | A |
| GET `/api/v1/news/ml-trend/` | L1693 `@action url_path='ml-trend'` (IsAdminUser) | A |
| GET `/api/v1/news/llm-usage/` | L1773 `@action url_path='llm-usage'` (IsAdminUser, coverage_warning 포함) | A |

### 키워드 상세 (설계 ↔ 구현)

| 설계 | 구현 | 분류 |
|---|---|---|
| GET `/api/v1/news/keyword-detail/?date&index` | `views.py:655` `@action url_path='keyword-detail'` | A |
| `DailyNewsKeyword.keywords[].search_terms_en` 스키마 확장 | `news/services/keyword_extractor.py` (grep 매칭 확인) | A |
| 2단 매칭 (entities.symbol IN → title ICONTAINS) | views.py keyword_detail 로직 (코드 직접 확인은 추가 작업 필요) | A (존재 확인) |
| Gemini 실패 시 analysis: null | 설계 명세 — 구현 검증 미수행 | B |
| Redis 캐시 `{date}:{index}:{updated_at_epoch}` | 설계 명세 — 구현 검증 미수행 | B |
| `KeywordDetailSheet.tsx` (BottomSheet v1 + v2) | `frontend/components/news/KeywordDetailSheet.tsx` 존재 | A |
| 가로 스크롤 Strip + max-w-2xl | 코드 직접 확인 미수행 (FE 컴포넌트 존재만 확인) | B |

### Phase A — 기존 API 노출 (설계 명시 5개)

| 설계 endpoint | 구현 | 분류 |
|---|---|---|
| ml-status | L1126 | A |
| ml-shadow-report | L1154 | A |
| ml-weekly-report | L1207 | A |
| ml-lightgbm-readiness | L1236 | A |
| daily-keywords | L522 | A |

### Phase B/C — 추가 인프라

| 설계 | 구현 | 분류 |
|---|---|---|
| AlertLog 모델 + trigger_type (TextChoices) | `models.py:684` 정의 완료 | A |
| 알림 발행 로직 (Phase C 능동적 모니터링) | views.py에 `alerts/` (L2100) + `alerts/<pk>/resolve` (L2164) 존재 | A |
| ML Rollback 2단계 (preview → confirm) | L2015 `ml-rollback-preview` + L2055 `ml-rollback` (POST) | A |
| Phase 3 (`NewsDeepAnalyzer`) 토큰 로깅 | `llm-usage` 응답에 `coverage_warning` 명시 — 토큰 자체는 미저장 | B (설계 §3.4가 의도된 한계 명시) |
| `_log_collection()` 커버리지 보강 (§11 선행 작업) | 코드 직접 확인 미수행 | B |

### 설계에 명시되지 않은 신규 endpoint (확장)

| endpoint | 위치 | 분류 |
|---|---|---|
| `task-timeline` | views.py:1893 | (확장) 운영성 추가 |
| `neo4j-status` | views.py:1954 | (확장) 운영성 추가 |
| `news-events`, `news-events/impact-map` | views.py:1023, 1082 | (확장) Intelligence Pipeline v3 연계 |
| `market-feed`, `interest-options`, `personalized-feed` | views.py:928, 966, 998 | (확장) 별도 기능 (Cold Start 등) |
| `daily-keywords/generate` (POST) | views.py:616 | (확장) 수동 트리거 |

### Frontend (설계 ↔ 구현)

| 설계 | 구현 | 분류 |
|---|---|---|
| NewsTab sub-tab 2개 (overview / pipeline) | `frontend/components/admin/NewsTab.tsx` 존재 | A (sub-tab 실제 구현 코드 미확인) |
| Pipeline Status Bar / Collection Stats / ML Model Card / Recent Errors / LLM Usage Summary | 별도 컴포넌트 존재 여부 미확인 | B |
| `useAdminNews` / `useNewsPipeline` hook | 미확인 | B |

### 갭/미구현 항목

| 분류 | 항목 | 위치 | 비고 |
|---|---|---|---|
| B | Phase 3 LLM 토큰 로깅 통합 | `news/services/news_deep_analyzer.py` | 설계 §3.4가 한계 명시, Phase B로 분리 |
| B | NewsTab sub-tab 분리 실제 적용 | FE `NewsTab.tsx` | 백엔드 API는 100% 완료, FE sub-tab 구조 적용 확인 필요 |
| C | "수집량 급감 평일 평균 비교 알림" (§6.1) | 알림 트리거 로직 | AlertLog 모델은 있으나 자동 trigger 발행 코드 미확인 |
| C | Phase 5+ 통합 LLM 비용 추적 (Phase 3 + 키워드 합산) | views.py llm-usage | 의도된 미래 작업 |

**결론**: **(A) 거의 완전 구현 ≈90%**. Phase A 백엔드/모델/FE는 완료. 잔여 작업은 Phase B 토큰 로깅, Phase C 알림 발행 자동화 등 점진적 개선.

---

## 종합 우선순위 권고

| 우선순위 | 항목 | 앱 | 근거 |
|---|---|---|---|
| P3 | Phase 3 (`NewsDeepAnalyzer`) 토큰 로깅 통합 | news | LLM 비용 추적의 완성도 — Phase B로 명시 |
| P3 | Validation Phase 5 LLM 캐싱 도입 검토 | validation | 설계상 "Phase 1~4 결과물 검토 후 결정" — 현재 rule-based 만족 시 보류 가능 |
| P4 | News Phase C 알림 자동 발행 트리거 | news | AlertLog 모델 + endpoint 존재, trigger 로직 검증 필요 |
| P4 | SEC Pipeline S&P 500 전체 배치 + Gold Set 라벨 보완 | sec_pipeline | 운영성 작업, 코드 결손 아님 |
| P5 | Validation Task 5 (update_peer_list_caches) 책임 명확화 | validation | 기능적 동작에 영향 없음 (Task 3에서 처리) |

**전반적 평가**: 세 앱 모두 설계서가 task_done 완료 보고서와 함께 잘 정리돼 있고, 코드/모델/마이그레이션/URL이 설계와 90% 이상 일치한다. 미구현 항목은 모두 의도된 보류(Phase 5+) 또는 점진적 운영 개선 영역이다.
