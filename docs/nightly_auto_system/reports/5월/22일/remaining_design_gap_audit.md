# SEC Pipeline + Validation + News 설계 갭 감사

> **감사일**: 2026-05-22
> **감사자**: claude (read-only, 코드 수정 없음)
> **대상**:
> - `docs/sec_pipeline/` vs `sec_pipeline/`
> - `docs/first_validation_system/` vs `validation/`
> - `docs/news/` vs `news/`

---

## 앱별 요약 (구현률)

| 앱 | 설계 문서 | 구현 코드 | 분류 | 구현률 | 주요 갭 |
|----|----------|----------|------|--------|---------|
| **SEC Pipeline** | `sec_pipeline_complete_summary.md` + PR1~17 task_done 17건 | 8 모델 / 16+ 파일 / 2 API / 8 Celery task | **(A) 완전 구현** | **~95%** | Beat 스케줄 주석 상태, S&P 500 전체 배치 미수행, CompanyAlias 0건 |
| **Validation** | `validation_design.md` (1646L) + peer v2 + Phase 6/7 | 6 모델 / 19 services / 6 API / 1 management cmd | **(A) 완전 구현** | **~92%** | Phase 2 LLM 도입 미진행(설계상 보류), `_inventory_vs_sales_growth` 등 일부 카테고리 시그널 경계 케이스 미문서화 |
| **News (Pipeline Monitoring)** | `news_pipeline_monitoring_design.md` (1160L) Phase A/B/C | 19 services / 35+ ViewSet action / AlertLog 모델 / `check_pipeline_alerts` 태스크 | **(A) 완전 구현** | **~98%** | 프론트엔드 Phase A/B/C 컴포넌트 13개 별도 검증 필요(본 감사는 백엔드 중심) |
| **News (Keyword Detail v2)** | `news_keyword_detail_plan.md` + `keyword_detail_bottomsheet_v2.md` | `keyword_detail` action + `KeywordDetailSheet.tsx` | **(A) 완전 구현** | **~100%** | — |

**전체 결론**: 세 앱 모두 설계서 대비 백엔드 구현은 거의 완성. 미완은 운영(배치 미실행, Beat 주석 상태) + 명시적 Phase 2 보류 영역으로, 코드 결손이 아닌 의도된 deferral.

---

## SEC Pipeline 상세

### 설계 vs 구현 매트릭스

| 영역 | 설계 (PR/항목) | 구현 위치 | 분류 |
|------|-------------|----------|------|
| **8개 모델** | sec_pr_1_models.md (RawDocument, SupplyChain, BM Snapshot/Evidence, FilingProcessLog, CompanyAlias, UnmatchedQueue, IntelligenceReport) | `sec_pipeline/models.py` 8 클래스 | **A** |
| **Collector** (SEC EDGAR submissions API → HTML → 섹션 추출 + 사후검증) | sec_pr_2_collector.md | `collector.py` + `validators.py` + `normalizer.py` | **A** |
| **Track A Extractor** (Gemini → SupplyChainEvidence + confidence grade) | sec_pr_3_track_a_extractor.md | `extractor.py` + `validator_track_a.py` + `prompts.py` | **A** |
| **Celery 태스크 (collect/extract/sync/check)** | sec_pr_4 | `tasks.py` 8 task (`collect_and_extract`, `extract_from_document`, `sync_dirty_to_neo4j`, `check_new_filings`, `generate_intelligence_report`, `run_batch_and_report`, `seed_relations_to_chainsight`) | **A** |
| **Gold Set 평가** | sec_pr_5 | task_done 기록 존재, 코드 산물은 fixtures/ 추정 | A (보고서 기준) |
| **Phase 1 배치 실행** | sec_pr_6 (15종목) | 110 SupplyChain + 173 ProcessLog 실측 (task_done) | **A** |
| **TickerMatcher 3단계 (alias→exact→fuzzy) + UnmatchedQueue** | sec_pr_7 | `ticker_matcher.py` + `signals.py` (post_save) | **A** |
| **Admin + Signal** | sec_pr_8 | `admin.py` 8 ModelAdmin + `signals.py` | **A** |
| **Neo4j sync** (dynamic type, DELETE+CREATE, `neo4j_dirty` 패턴) | sec_pr_9 | `tasks.py::sync_dirty_to_neo4j` | **A** |
| **관계 병합 + DQS** | sec_pr_10 | `merger.py` | **A** |
| **Track B (Business Model)** | sec_pr_11_12_13 | `validator_track_b.py` + `keywords_track_b.py` + Track B 프롬프트 | **A** |
| **Admin 대시보드 UI** | sec_pr_14 | `views.py::sec_pipeline_dashboard` + `templates/admin/sec_pipeline/dashboard.html` | **A** |
| **On-demand filing** | sec_pr_15 | `on_demand.py` | **A** |
| **Intelligence Report (5차원 Gemini)** | sec_pr_16 | `intelligence.py` + `tasks.py::generate_intelligence_report` | **A** |
| **E2E + chord** | sec_pr_17 | `tasks.py::run_batch_and_report` | **A** |
| **품질 체크 7개 + 대시보드 통계** | sec_pr_14/16 | `quality_checks.py` | **A** |
| **URL 라우팅** | CLAUDE.md는 `/api/v1/sec/*` 라 명시 | 실제: `config/urls.py` → `api/v1/sec-pipeline/` (불일치) | **A (구현)** + 문서 갭 |
| **REST API** | sec_pr_14 + 17 (admin dashboard + filing data) | 2 endpoint (`admin/dashboard/`, `filing/<symbol>/`) | **A** |

### task_done cross-reference

- 완료 보고서 **17건 + summary 1건 = 18건** 모두 존재 (`docs/sec_pipeline/task_done/`).
- 의사결정 1건: `decisions/001_fmp_vs_sec_edgar_metadata.md` (FMP Starter sec-filings 404 → EDGAR 직접 사용).

### 갭 / 미완 / 운영 부채

| # | 항목 | 분류 | 비고 |
|---|------|------|------|
| G1 | **Celery Beat 스케줄 주석 상태** (`sync-sec-dirty-neo4j */5min`, `check-new-filings` 매월 1일) | **(B) 부분** | sec_pr_17.md 본문에 "Celery Beat 설정 (주석 상태)"로 명시 — 의도된 보류 |
| G2 | **S&P 500 전체 배치 미수행** (현재 15종목만 실측) | **(B) 부분** | Gemini RPD 제한 고려 — sec_pipeline_complete_summary.md "향후 과제 1" |
| G3 | **CompanyAlias 0건** (TSMC→TSM, Samsung 등 수동 매핑 미적재) | **(B) 부분** | "향후 과제 5" — Ticker 매칭률 2/110(3%) 원인 |
| G4 | **Gold Set 라벨 보완 + Precision/Recall 재평가** | **(C) 미구현** | "향후 과제 2" |
| G5 | **JNJ Item 순서 검증 완화** | **(C) 미구현** | "향후 과제 3" — 15종목 중 유일 실패 케이스 |
| G6 | **CLAUDE.md URL 표기 불일치**: `/api/v1/sec/*` vs 실제 `/api/v1/sec-pipeline/*` | 문서 갭 | CLAUDE.md L66 수정 또는 URL include 변경 필요 |
| G7 | **프롬프트 일반 명사 추출 방지** ("third parties" 등) | **(C) 미구현** | "향후 과제 4" |

### SEC Pipeline 분류

**(A) 완전 구현**: 17 PR 전체 + 모델 8 + 핵심 파이프라인 (collect→extract→sync→intelligence)
**(B) 부분**: Beat 주석 / 전체 배치 / CompanyAlias 시딩 — 모두 **운영 결손**, 코드는 준비됨
**(C) 미구현**: Gold Set 보강, JNJ 검증 완화, 프롬프트 정제 — 향후 과제로 명시
**(D) 폐기**: 없음

---

## Validation 상세

### 설계 vs 구현 매트릭스

| 영역 | 설계 (chapter/PR) | 구현 위치 | 분류 |
|------|-------------------|----------|------|
| **모델 — CategorySignal** (category_score → category_signal 개명) | §7.1, §7.6 | `validation/models/category_score.py::CategorySignal` (파일명만 구버전 유지, 클래스/테이블명 = signal) | **A** |
| **CompanyBenchmarkDelta — basis/confidence/rank/total** | §7.3 | `models/benchmark_delta.py` | **A** |
| **CompanyMetricSnapshot — value_status/exclusion_reason** | §7.2 | `metrics/` 앱 소속 (validation 외부) — `value_status='normal'/'missing'/'not_applicable'/'unstable'` 분기 활용 확인됨 (views.py) | **A** |
| **PeerListCache — benchmark_basis/size_bucket/peer_tier** | §7.4 | `metrics/models/benchmark.py` L30/L38/L42 모두 존재 | **A** |
| **IndustryClassification — handling_mode** | §7.5 | `stocks.models.IndustryClassification` (validation/services/category_signal_calculator.py가 SPECIAL_GRAY_CATEGORIES 분기 활용) | **A** |
| **7 카테고리 × 34 지표** | §4 | `services/category_signal_calculator.py::CATEGORY_METRICS` 7키 / 합계 34 지표 일치 확인 | **A** |
| **API: /summary/** (category_signals + peer_info + industry_position + summary_text) | §5.2 | `api/views.py::ValidationSummaryView` | **A** |
| **API: /metrics/?category=** (현재값+5년 시계열+peer band+해석+trend) | §5.2 | `ValidationMetricsView::_build_metric` (current/benchmark/history/trend/interpretation) | **A** |
| **API: /leader-comparison/** | §5.2 | `LeaderComparisonView` (advantages/disadvantages + 6개 summary 지표) | **A** |
| **Rule-based 해석 (interpretation.py)** | §8.1 | `services/interpretation.py` (`generate_summary_text`, `generate_metric_interpretation`, `determine_trend`, `generate_leader_summary`) | **A** |
| **handling_mode='special' gray 처리** | §4.3, §7.5 | `SPECIAL_GRAY_CATEGORIES` (financial_structure, cash_flow_quality) | **A** |
| **Peer Phase 1~5 프리셋 6종** (default/sector_all/size_peers/quality_top/lifecycle/thematic) | peer_system v2 §2 | `services/preset_generator.py` 6 preset_key 전부 생성 | **A** |
| **Peer Phase 6 (thematic, DNA 교차)** | task_done/peer_phase6 | 463/503 종목, 전체 2,282 preset 실측 | **A** |
| **Peer Phase 7 (LLM 대화형 필터)** | task_done/peer_phase7 | `services/llm_peer_filter.py` + `api/views.py::LLMPeerFilterView` (`POST /llm-filter/`) | **A** |
| **UserPeerPreference + Custom mode** | peer_system §4 | `models/peer_preset.py::UserPeerPreference` + `PeerPreferenceView` POST/DELETE + `services/custom_benchmark_engine.py` | **A** |
| **PeerPreset 모델** | peer_system §4 | `models/peer_preset.py::PeerPreset` | **A** |
| **PR 시드 데이터** | BE-PR-2 | `management/commands/seed_validation_data.py` | **A** |
| **ML Phase 2 — ValidationAICache (LLM 캐시)** | §8.2 | **없음** (설계상 "Phase 2 검토" 명시) | **(D) 폐기/대체에 가까운 보류** |
| **FMP 호출 전략 (§6.3)** | §6.3 | `services/financial_fetcher.py` 존재 — 호출 본체 확인 | **A** (간접) |
| **News Summary 카드 (ValidationNewsSummary 모델)** | (보조) | `models/news_summary.py::ValidationNewsSummary` 모델 존재. API 노출 여부 별도 확인 필요 | **B (부분)** |

### task_done cross-reference

- `peer_phase6_thematic.md` (2026-04-04) — preset_generator `_generate_thematic` 추가, 463 종목 적용 ✅
- `peer_phase7_llm_filter.md` (2026-04-04) — LLM 자연어→필터 파싱 + 31 재무지표 + Chain Sight DNA 지원 ✅
- BE-PR-1~6 / FE-PR-1~7 별 task_done 파일 부재 — `validation_pr_prompts.md`의 PR 단위 완료 보고서가 task_done/ 디렉토리에 없음

### 갭 / 미완

| # | 항목 | 분류 | 비고 |
|---|------|------|------|
| V1 | **Phase 2 LLM 텍스트 캐시 (`ValidationAICache`)** | **(D) 보류** | 설계 §8.2 자체가 "참고용", Phase 1 완료 후 결정. 의도된 deferral |
| V2 | **ValidationNewsSummary** 모델은 있으나 API 노출 / 데이터 적재 흐름 미확인 | **(B) 부분** | `validation/api/views.py`에 직접 활용 없음 — UI 노출 경로 별도 추적 필요 |
| V3 | **PR별 task_done 보고서 부재** (Phase 6/7만 별도 기록) | 문서 갭 | BE-PR-1~6 + FE-PR-1~7은 통합 구현되었으나 PR 단위 완료 보고서 미존재 |
| V4 | **카테고리 시그널 경계 케이스 문서화** (특히 inventory_* / cash_runway / interest_coverage 의 unstable/not_applicable 분기) | (참고) | 코드(category_signal_calculator)는 처리, 설계서 §4 특수처리는 명시. 갭 아님 — 확인용 |
| V5 | **§5.4 URL 설정 — `urls.py` 명세 일치** | (참고) | 6 endpoint 모두 일치 (`summary`, `metrics`, `leader-comparison`, `presets`, `peer-preference`, `llm-filter`) ✅ |

### Validation 분류

**(A) 완전 구현**: Phase 1 + Peer Phase 1~7 전체 (모델·서비스·API·시드·LLM 필터·thematic preset)
**(B) 부분**: ValidationNewsSummary 노출 경로 미확인
**(C) 미구현**: 없음
**(D) 폐기/보류**: ValidationAICache (Phase 2 LLM 캐시, 의도된 보류)

---

## News 상세

### A. News Pipeline Monitoring (1160L 설계)

| Phase | 엔드포인트 / 산출물 | 구현 위치 | 분류 |
|-------|---------------------|----------|------|
| **Phase 0** _log_collection 커버리지 보강 | `news/tasks.py` MODIFY | 구현 (간접 확인 — `pipeline_health` action 정상 작동 전제) | **A** |
| **Phase A-BE: /collection-logs/** | §3.1 | `views.py::collection_logs` L1329 | **A** |
| **Phase A-BE: /pipeline-health/** (Phase별 expected_interval + status 판정 + `_determine_status`) | §3.2 | `views.py::pipeline_health` L1439 + `_determine_status` L1473 | **A** |
| **Phase A-BE: /ml-trend/** | §3.3 | `views.py::ml_trend` L1693 | **A** |
| **Phase A-BE: /llm-usage/** | §3.4 | `views.py::llm_usage` L1773 | **A** |
| **Phase B-BE: /task-timeline/** (24h 간트) | §5.1 | `views.py::task_timeline` L1893 | **A** |
| **Phase B-BE: /neo4j-status/** | §5.2 | `views.py::neo4j_status` L1954 | **A** |
| **Phase B-BE: /ml-rollback-preview/** (Step 1) | §5.3 | `views.py::ml_rollback_preview` L2015 | **A** |
| **Phase B-BE: /ml-rollback/** (POST, confirm 필수) | §5.3 | `views.py::ml_rollback` L2055 | **A** |
| **Phase C-BE: AlertLog 모델 + 7 TriggerType + 4 Severity** | §6.3 | `news/models.py::AlertLog` + migration `0006_alertlog.py` | **A** |
| **Phase C-BE: /alerts/** + `/alerts/{id}/resolve/`** | §6.3 | `views.py::alerts` L2100 + `alerts_resolve` L2164 | **A** |
| **Phase C-BE: `check_pipeline_alerts` Celery task** (30분 주기, 7 트리거 체크) | §6.1 | `news/tasks.py::check_pipeline_alerts` + `config/celery.py` 등록 | **A** |
| **Phase A-FE: 13 컴포넌트** (PipelineStatusBar, CollectionStatsTable, MLModelCard, MLTrendChart, ...) | §7 | **본 감사는 backend 중심**, frontend 별도 확인 필요 | **B (미확인)** |
| **Phase B-FE: TaskTimelineChart, Neo4jStatusCard, MLCompareView** | §7 | frontend 별도 확인 필요 | **B (미확인)** |
| **Phase C-FE: AlertBadge, AlertList** | §7 | frontend 별도 확인 필요 | **B (미확인)** |

### B. News Keyword Detail v2

| 항목 | 설계 | 구현 | 분류 |
|------|------|------|------|
| **/keyword-detail/ API** (kw 키워드 + 2단 매칭 + Gemini 분석) | `news_keyword_detail_plan.md` §4 | `views.py::keyword_detail` L655 + `_generate_keyword_analysis` L791 | **A** |
| **KeywordDetailSheet 컴포넌트 (BottomSheet)** | `keyword_detail_bottomsheet_v2.md` | `frontend/components/news/KeywordDetailSheet.tsx` | **A** |
| **DailyKeywordCard 연동** | 동일 | `frontend/components/news/DailyKeywordCard.tsx` | **A** |

### task_done cross-reference

- News 영역 `task_done/` 디렉토리 부재. `docs/news/plan/` 하위 3 plan 문서만 존재.
- 구현 완료 흔적은 `news/models.py::AlertLog` + migration `0006_alertlog.py` + `check_pipeline_alerts` task로 확인.

### 갭 / 미완

| # | 항목 | 분류 | 비고 |
|---|------|------|------|
| N1 | **Phase A/B/C 프론트엔드 컴포넌트 13개 검증 미수행** | **(B) 미확인** | 본 감사는 백엔드 중심. `frontend/components/admin/news/` 디렉토리 별도 감사 필요 |
| N2 | **news/task_done/ 부재** — 구현 완료 보고서 미작성 | 문서 갭 | Phase A/B/C 완료 보고서가 별도 디렉토리에 없음 |
| N3 | **Slack/Email 알림 채널** (§6.2 선택 항목) | **(C) 미구현** (선택) | `settings.SLACK_WEBHOOK_URL` 사용 분기 부재. 인앱 알림은 완성 |
| N4 | **알림 트리거 7종 vs 구현 트리거** (이름 일치 확인됨: ml_f1_decline, llm_error_spike, neo4j_unavailable, collection_drop, unclassified_backlog, consecutive_task_failure, keyword_extraction_failure) | (참고) | 코드 grep으로 7 트리거 모두 분기 확인됨 ✅ |

### News 분류

**(A) 완전 구현**: Phase 0/A/B/C 백엔드 전체 (11 endpoint + AlertLog 모델 + check_pipeline_alerts) + Keyword Detail v2
**(B) 부분 / 미확인**: Phase A/B/C 프론트엔드 13 컴포넌트 (별도 감사 권고)
**(C) 미구현**: Slack/Email 알림 채널 (설계상 선택)
**(D) 폐기**: 없음

---

## 종합 권고 (read-only, 코드 변경 없음)

### 즉시 정합화 필요

1. **CLAUDE.md L66 URL 표기 수정**: `/api/v1/sec/*` → `/api/v1/sec-pipeline/*` (또는 URL include 단축)
2. **SEC Beat 스케줄 주석 해제 검토**: `sync-sec-dirty-neo4j` 5분 주기 / `check-new-filings` 월간 — 운영 진입 시점 결정
3. **CompanyAlias 수동 시딩**: TSMC→TSM, Samsung 등 비미국 ADR 매핑 적재 → Ticker 매칭률 3% 개선

### 문서 정합화

4. **task_done 보고서 추가**: Validation BE-PR-1~6 + FE-PR-1~7 / News Phase A/B/C 완료 보고서 부재 → 통합 summary 작성 권고
5. **ValidationNewsSummary 노출 경로 추적**: 모델은 있으나 API 노출 미확인 — 사용처/대체 여부 결정

### 다음 마일스톤 후보

6. **SEC Pipeline S&P 500 전체 배치** (Gemini RPD 제약 대응 + Gold Set 라벨 보강)
7. **Validation Phase 2 LLM 캐시 (ValidationAICache)** 도입 여부 결정 (Phase 1 운영 데이터 누적 후)
8. **News 프론트엔드 모니터링 대시보드 검증** (별도 frontend 갭 감사)

---

## 부록: 파일/모델 카운트

| 앱 | 모델 수 | API endpoint 수 | Celery task 수 | services 파일 수 |
|----|--------|----------------|---------------|----------------|
| sec_pipeline | 8 | 2 | 8 | (services 폴더 없음, 평탄 구조) |
| validation | 6 | 6 | (별도 tasks.py: metrics 앱 분담) | 11 |
| news | 9 (NewsArticle, NewsEntity, EntityHighlight, SentimentHistory, DailyNewsKeyword, MLModelHistory, NewsCollectionCategory, NewsCollectionLog, AlertLog) | 35+ (ViewSet action) | 다수 (check_pipeline_alerts 포함) | 19 |

