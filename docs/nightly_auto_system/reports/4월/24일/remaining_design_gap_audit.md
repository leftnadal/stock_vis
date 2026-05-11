# SEC Pipeline + Validation + News 설계 갭 감사

> **작성일**: 2026-04-24
> **감사 범위**: `docs/sec_pipeline/` vs `sec_pipeline/`, `docs/first_validation_system/` vs `validation/`, `docs/news/` vs `news/`
> **방식**: 읽기 전용 정적 분석 (코드 수정 없음). task_done/ 완료 보고서 cross-reference.
> **분류 기준**: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 앱별 요약 (구현률)

| 앱 | 총 항목 | A 완전 | B 부분 | C 미구현 | D 폐기/대체 | 가중 구현률 | 종합 평가 |
|----|--------|-------|--------|---------|------------|-----------|---------|
| **SEC Pipeline** | 40 | 33 (82.5%) | 6 (15%) | 1 (2.5%) | 0 | **≈ 92%** | 코어 기능 프로덕션 가능, 자동화·테스트 미흡 |
| **Validation** | 25 | 18 (72%) | 5 (20%) | 1 (4%) | 1 (4%) | **≈ 84%** | 6종 프리셋 모두 동작, 설계-구현 정렬 일부 어긋남 |
| **News** | 18 | 8 (44%) | 4 (22%) | 6 (34%) | 0 | **≈ 56%** | Pipeline v3 백엔드 완성, 프론트엔드 모니터링 UI 미착수 |

**핵심 결론**:
- SEC Pipeline은 17개 task_done 보고서 신뢰도 95%, 즉시 운영 진입 가능 수준.
- Validation은 동작은 우수하나 **Phase 6 Thematic 설계 변경**이 문서에 반영되지 않은 상태(설계 문서 정합성 결함).
- News는 **백엔드 완성 → 프론트엔드 미착수** 비대칭이 가장 큰 리스크. Phase 0 선행 작업(`_log_collection()` 커버리지)도 불완전.

---

## SEC Pipeline 상세

### 1. 설계 문서 인벤토리

**결정 문서 (1개)**
- `decisions/001_fmp_vs_sec_edgar_metadata.md` — FMP Starter 미지원 → SEC EDGAR 직접 호출 결정

**완료 보고서 (17개)**
- `sec_pr_1_models.md` ~ `sec_pr_17_e2e.md` (PR 단위 추적)
- `sec_pipeline_complete_summary.md` — 전체 요약 (8 모델, 16 파일)

### 2. 항목별 매핑 (요약 — 전체 40개 중 핵심 추출)

| # | 설계 항목 | 출처 | 분류 | 위치 / 누락 사항 |
|---|----------|------|------|---------------|
| 1 | 8개 Django 모델 (RawDocumentStore ~ PipelineIntelligenceReport) | sec_pr_1 | A | `sec_pipeline/models.py` |
| 2 | SEC EDGAR 메타데이터·HTML 수집기 | sec_pr_2 | A | `collector.py:72-150`, `get_filing_html()` |
| 3 | 3단계 섹션 추출 (regex → heading → edgartools fallback) | sec_pr_2 | A | `collector.py:extract_sections()` + `extract_sections_fallback()` |
| 4 | 사후 검증 (순서/heading/길이) | sec_pr_2 | A | `validators.py:validate_extracted_sections()` |
| 5 | Track A 키워드 필터(30개) + Gemini 추출 | sec_pr_3 | A | `normalizer.py:filter_paragraphs()`, `extractor.py:extract_supply_chain()` |
| 6 | Track A confidence_grade 산출/저장 | sec_pr_3 | A | `validator_track_a.py` |
| 7 | Celery tasks (collect_and_extract, extract_from_document) | sec_pr_4 | A | `tasks.py:23-280`, max_retries 3/2 + exp backoff |
| 8 | 4개 custom exception | sec_pr_4 | A | `exceptions.py` |
| 9 | FilingProcessLog 단계 로깅 | sec_pr_4 | A | `tasks.py:_log_stage()` |
| 10 | S&P 500 심볼 유틸 | sec_pr_4 | A | `sp500.py:get_sp500_symbols()` |
| 11 | Gold Set 라벨 데이터셋 | sec_pr_5 | A | `fixtures/` |
| 12 | Precision/Recall 평가 스크립트 | sec_pr_5 | **B** | 보고서는 "완료" 명시, 실제 동작 검증 안 됨. `management/commands/evaluate_gold_set.py` 존재 여부만 확인 |
| 13 | Phase 1 배치 실행 (15종목) | sec_pr_6 | A | `run_batch_and_report()` |
| 14 | 3단계 Ticker 매칭 (alias→exact→fuzzy) | sec_pr_7 | A | `ticker_matcher.py:TickerMatcher` |
| 15 | CompanyAlias / UnmatchedCompanyQueue Admin | sec_pr_8 | A | `admin.py` (auto_resolve action 포함) |
| 16 | post_save signal | sec_pr_8 | A | `signals.py` |
| 17 | Neo4j 동기화 (DELETE + CREATE, sole writer) | sec_pr_9 | A | merger/Neo4j sync 코드 |
| 18 | 관계 병합 + DQS 계산 | sec_pr_10 | A | `merger.py:merge_relationships()` |
| 19 | Track B Gemini 5필드 추출 + DB 저장 | sec_pr_11 | A | `extractor.py:extract_business_model()`, `validator_track_b.py` |
| 20 | 서비스 레이어 (for_api, 간접 참조) | sec_pr_11~13 | A | `metrics/services/business_model_service.py` |
| 21 | 7개 품질 체크 + Admin 대시보드 | sec_pr_14 | A | `quality_checks.py`, `templates/admin/sec_pipeline/dashboard.html` |
| 22 | On-demand 수집 API + 신규 filing 감지 | sec_pr_15 | A | `views.py:FilingDataView`, `urls.py:filing/<str:symbol>/`, `tasks.py:check_new_filings()` |
| 23 | Intelligence Report (5차원) | sec_pr_16 | A | `intelligence.py:PipelineIntelligenceReporter` |
| 24 | Celery chord E2E | sec_pr_17 | A | `tasks.py:run_batch_and_report()` |
| 25 | 통합 테스트 스위트 | (전반) | **C** | `sec_pipeline/tests.py`가 빈 파일 (1줄) — 회귀 검증 불가 |
| 26 | Celery Beat 스케줄 | (전반) | **B** | `sync-sec-dirty-neo4j`, `check-new-filings` 주석으로만 정의, `CELERY_BEAT_SCHEDULE` 미등록 |
| 27 | Migration 분할 | (전반) | **B** | Phase 1~3 모델이 `0001_initial.py` 단일 파일에 통합됨 (데이터 거버넌스 미흡) |
| 28 | 외부 공개 API 확장 | (전반) | **B** | 현재는 Admin + on-demand 1개. 대시보드/Intelligence 데이터 공개 API 없음 |

### 3. Top 5 갭

1. **테스트 전무** — 프로덕션 코드 ~3,300줄 vs 테스트 0줄. CI/CD·회귀 검증 인프라 부재. (영향: 중)
2. **Celery Beat 미등록** — 자동 동기화/신규 filing 감지가 수동 실행에만 의존. (영향: 높음 — 운영 필수)
3. **Migration 단일 파일** — Phase별 모델 추가 이력이 분리되지 않아 변경 추적 어려움. (영향: 낮음)
4. **API 노출 제한** — Admin 중심으로 다른 서비스(예: Frontend Chain Sight)가 Intelligence Report에 접근 불가. (영향: 중)
5. **평가 스크립트 검증 안 됨** — sec_pr_5가 "완료" 보고했으나 동작 확인 미실시. (영향: 낮음)

### 4. task_done 보고서 신뢰도: **95% (매우 높음)**

- 16/17 PR 보고서가 코드와 정확히 일치
- 부분 불일치 1건: sec_pr_5 평가 스크립트 (보고는 "완료", 실제는 코드만 존재·동작 미검증)
- 보고되지 않은 추가 구현: `management/commands/` 5개, `prompts.py` 추출 프롬프트 2개

### 5. 설계 원칙 준수 ✅
문서 기반 개발, 작업 단계별 기록(FilingProcessLog), 1인 개발 최적화(Django 모놀리스), 간접 참조(metrics/services), 숫자 노출 경계(system_confidence vs confidence_grade), Neo4j sole-writer 패턴 모두 준수.

---

## Validation 상세

### 1. 설계 문서 인벤토리

| 파일 | 내용 |
|------|------|
| `validation_design.md` | Phase 1 시스템 설계 (7개 카테고리, 34개 지표, API, 배치, UI) |
| `validation_peer_system.md` | Peer 프리셋 6종 최종 설계서 |
| `validation_peer_phase6_7.md` | Phase 6 (thematic) + Phase 7 (LLM 대화형 필터) 상세 |
| `validation_pr_prompts.md` | BE-PR-1~6, FE-PR-1~7 작업 지시서 |
| `task_done/peer_phase6_thematic.md` | Phase 6 완료 보고 (463/503 종목 thematic 생성) |
| `task_done/peer_phase7_llm_filter.md` | Phase 7 완료 보고 (LLM 파서 + 필터 실행) |

### 2. 항목별 매핑 (25 항목)

| # | 설계 항목 | 출처 | 분류 | 위치 / 누락 |
|---|---------|------|------|---------|
| 1 | PeerPreset 모델 (6 preset_key) | peer_system.md §2 | A | `validation/models/peer_preset.py` |
| 2 | UserPeerPreference (preset/custom 모드) | peer_system.md §4 | A | `validation/models/peer_preset.py` |
| 3 | CompanyBenchmarkDelta + preset_key | design.md §5.2 | A | `validation/models/benchmark_delta.py` (unique_together 포함) |
| 4 | CategorySignal + preset_key | design.md §5.2 | A | `validation/models/category_score.py` (unique_together 포함) |
| 5 | preset 1: default | peer_system.md §3.1 | A | `services/preset_generator.py:_generate_default()` |
| 6 | preset 2: sector_all | peer_system.md §3.2 | A | `_generate_sector_all()` |
| 7 | preset 3: size_peers | peer_system.md §3.3 | A | `_generate_size_peers()` (mega/large만) |
| 8 | preset 4: quality_top | peer_system.md §3.4 | A | `_generate_quality_top()` (ROIC / Op Margin / FCF Margin 상위 20%) |
| 9 | preset 5: lifecycle | peer_system.md §3.5 | A | `_generate_lifecycle()` (Revenue CAGR percentile) |
| 10 | preset 6: thematic | phase6_7.md Phase 6 | **D** | `_generate_thematic()` 동작하나 **GrowthStage × CapitalDNA 조합으로 대체** (설계는 LLM 큐레이션) |
| 11 | confidence_score 계산 | peer_system.md §5 | A | `_calc_confidence()` |
| 12 | GET /summary/ | design.md §5 | A | `views.py:ValidationSummaryView` |
| 13 | GET /metrics/?category=all | design.md §5 | A | `views.py:ValidationMetricsView` |
| 14 | GET /leader-comparison/ | design.md §5 | A | `views.py:LeaderComparisonView` |
| 15 | GET /presets/ | peer_system.md §7 | A | `views.py:PresetListView` |
| 16 | POST /peer-preference/ | peer_system.md §7 | **B** | `PeerPreferenceView` 권한은 `IsAuthenticatedOrReadOnly` 설정. FE의 authAxios 적용 여부는 별건(common-bug #26 참고) |
| 17 | DELETE /peer-preference/ | peer_system.md §7 | A | `PeerPreferenceView` (default로 자동 리셋) |
| 18 | POST /llm-filter/ | phase6_7.md Phase 7 | A | `views.py:LLMPeerFilterView` |
| 19 | Compute-on-Read 엔진 | peer_system.md §8 | A | `services/custom_benchmark_engine.py:CustomBenchmarkEngine.compute_summary()` |
| 20 | LLM 필터 파서 (Gemini 2.5 Flash JSON) | phase6_7.md §Step 1 | A | `services/llm_peer_filter.py:parse_filter_with_llm()` |
| 21 | LLM 필터 실행 엔진 | phase6_7.md §Step 2 | **B** | `execute_peer_filter()` 구현되었으나 chainsight 데이터(SensitivityProfile, CompanyNarrativeTag)가 0건이라 일부 필터 결과 0건 |
| 22 | 커스텀 peer → Compute-on-Read 분기 | peer_system.md §8 | A | `views.py:ValidationSummaryView` (line 72-77) |
| 23 | Confidence 라벨링(high/medium/low) | peer_system.md §5 | **B** | `PresetListView` (line 441) — confidence_label 변환 있으나 표시 텍스트만, 임계값 노출 미흡 |
| 24 | Compute-on-Read Redis 캐시 (TTL 1h) | peer_system.md §1, phase6_7 | **C** | `custom_benchmark_engine.py`에서 캐시 로직 검색 미확인 — 매 요청마다 on-the-fly 계산 가능성 |
| 25 | Migration 0003/0004 (preset_key 추가) | BE-PR-4 | A | `migrations/0003_*.py`, `0004_*.py` |

### 3. Peer 프리셋 6종 점검표

| Preset | 설계 조건 | 구현 | 데이터 | 비고 |
|--------|---------|------|--------|------|
| default | 모든 종목 (industry+size) | ✅ | 503종 | OK |
| sector_all | 모든 종목 (sector 전체) | ✅ | 503종 | OK |
| size_peers | mega/large cap만 | ✅ | ~200종 | OK |
| quality_top | sector ≥ 25 + 수익성 상위 20% | ✅ | ~450종 | OK |
| lifecycle | sector ≥ 25 + Revenue CAGR percentile | ✅ | ~400종 | OK |
| thematic | (설계: LLM 큐레이션) → (구현: GrowthStage × CapitalDNA) | ✅ | 463종 | **설계 변경 미문서화** |

### 4. Top 5 갭

1. **Phase 6 Thematic 설계 변경 미문서화 (D)** — 설계는 "LLM 사업모델 태깅 + CompanyNarrativeTag.theme_tags", 구현은 "DNA 조합 자동화". task_done에는 인지된 변경이 명시되어 있으나 `validation_peer_system.md`가 갱신되지 않음. → **설계서 업데이트 권장**.
2. **Compute-on-Read Redis 캐시 부재 의심 (C)** — 설계는 TTL 1h Redis 캐시 명시, 코드에서 캐시 로직 미발견. 커스텀 peer 조회 성능 저하 가능. (`services/custom_benchmark_engine.py` 추가 검증 필요)
3. **Chain Sight 데이터 0건으로 LLM 필터 일부 시나리오 무효 (B)** — `foreign_revenue_pct`, `rd_to_revenue` 등 LLM이 파싱은 성공하지만 chainsight 모델 데이터 없어 필터 결과가 0건. Chain Sight v2 완성 후 재검증 필요.
4. **PeerPreferenceView 인증 일관성 (B)** — 백엔드 권한은 정상이나, common-bug #26(`selectPreset`을 raw fetch로 호출 → JWT 누락)이 FE 쪽에서 재발하지 않도록 모니터링 필요.
5. **PeerMetricBenchmark의 시점 정의 모호 (B)** — `ValidationMetricsView._build_metric()` (line 274-285)에서 fiscal_year별 peer band를 조회하지만, "현재 peer 구성 기준"인지 "과거 구성 기준"인지 코드/설계 모두 명시 부족.

### 5. task_done 보고서 신뢰도

| 보고서 | 신뢰도 | 비고 |
|--------|--------|------|
| `peer_phase6_thematic.md` | 🟡 60% | 동작은 완료. 단, 설계와 축이 다름(DNA 조합). 보고서 자체는 변경을 명시 |
| `peer_phase7_llm_filter.md` | 🟢 95% | 파서 + 필터 실행 모두 구현. chainsight 데이터 0건만 외부 의존 |

**종합**: 동작 관점에서는 진실에 가까우나, **설계 정합성 관점에서는 갭 존재** (특히 Phase 6).

---

## News 상세

### 1. 설계 문서 인벤토리

| # | 파일 | 줄수 | 주제 |
|---|------|-----|------|
| 1 | `plan/news_pipeline_monitoring_design.md` | 1,160 | 파이프라인 모니터링 대시보드 (Phase A/B/C) |
| 2 | `plan/news_keyword_detail_plan.md` | 217 | 키워드 상세보기 바텀시트 |
| 3 | `plan/keyword_detail_bottomsheet_v2.md` | 81 | 바텀시트 가로 스크롤/너비 제한 보강 |

> CLAUDE.md "완료" 라인은 News Intelligence Pipeline v3 (규칙 + LLM + ML + Neo4j + Shadow/Production + LightGBM, 테스트 607개)를 명시.

### 2. Intelligence Pipeline v3 단계별 점검

| 단계 | 설계 요소 | 분류 | 증거 |
|-----|---------|------|------|
| 1. 수집 | 4개 provider (Finnhub/Marketaux/FMP/AV) | A | `news/providers/` 4개 모듈, `collect_*` 태스크들 |
| 1b. 카테고리 | sector / sub_sector / custom + Beat | A | `NewsCollectionCategory` 모델 + `collect_category_news` |
| 2. 분류 | 규칙 엔진 A/B/C | A | `news_classifier.py` (~650줄) + `classify_news_batch` |
| 3. LLM 분석 | Gemini 2.5 Flash Tier A/B/C | A | `news_deep_analyzer.py` + `analyze_news_deep` |
| 4. ML Label | 라벨 수집 + Neo4j 동기화 | A | `ml_label_collector.py`, `sync_news_to_neo4j` |
| 5. ML 학습 | LR + Shadow Mode + 자동배포 | A | `ml_production_manager.py` + `train_importance_model`, `generate_shadow_report`, `check_auto_deploy` |
| 6. LightGBM | 전환 준비 + 주간 리포트 | A | `ml_weight_optimizer.py:check_lightgbm_readiness()` + `train_lightgbm_model`, `generate_weekly_ml_report` |

**Pipeline v3 백엔드 6단계 완전 구현 ✅** — 단, 모델 파일 저장 경로(`.pkl/.joblib`) 및 버전 관리 전략 문서화는 별도 점검 필요.

### 3. 항목별 매핑 (18 항목)

| # | 설계 항목 | 출처 | 분류 | 위치 / 상태 |
|---|---------|------|------|----------|
| 1 | 4 provider 수집 | §1 | A | `news/providers/` + `collect_*` 태스크 |
| 2 | 수집 카테고리 (sector/sub_sector/custom) | §1 | A | `NewsCollectionCategory` 모델 + 태스크 |
| 3 | 규칙 엔진 A/B/C | §1 | A | `news_classifier.py` |
| 4 | LLM 심층 분석 (Tier A/B/C) | §1 | A | `news_deep_analyzer.py` |
| 5 | ML 학습 (LR + LightGBM 준비) | §1 | A | `ml_production_manager.py`, `ml_weight_optimizer.py` |
| 6 | Shadow / Production Mode | §1 | A | `MLProductionManager.generate_shadow_report()`, `check_auto_deploy()` |
| 7 | Neo4j 뉴스 이벤트 동기화 | §1 | A | `news_neo4j_sync.py` + `sync_news_to_neo4j` (실 그래프 저장 결과 검증은 별도) |
| 8 | 모니터링 4 API (collection-logs / pipeline-health / ml-trend / llm-usage) | §3 | A | `news/api/views.py` actions |
| 9 | 키워드 상세보기 바텀시트 | `news_keyword_detail_plan.md` | B | 백엔드 `keyword_detail` action 구현, FE 미구현, `search_terms_en` 필드 미추가 |
| 10 | Task Timeline 차트 | §5.1 | B | 백엔드 `task_timeline` action만 구현 |
| 11 | Neo4j 상태 조회 | §5.2 | B | 백엔드 `neo4j_status` action만 구현 |
| 12 | ML 롤백 2단계 (preview + confirm) | §5.3 | B | 백엔드 `ml_rollback_preview` / `ml_rollback` actions만 구현 |
| 13 | 모니터링 UI 대시보드 (PipelineStatusBar 등 6컴포넌트) | §4 | C | 프론트엔드 미착수 |
| 14 | ML 롤백 2단계 모달 (FE) | §5.3 | C | 프론트엔드 미착수 |
| 15 | Task Timeline 차트 (FE) | §5.1 | C | 프론트엔드 미착수 |
| 16 | 파이프라인 알림 자동 감지 | §6 (Phase C) | C | `AlertLog` 모델/조회 API는 있으나 `check_pipeline_alerts` Celery 태스크 **부재** |
| 17 | `_log_collection()` 커버리지 (Phase 0) | §11 | C | 6/10 태스크만 호출 — Phase A 선행 작업 미완료 |
| 18 | NewsTab sub-tab 아키텍처 (overview/pipeline) + 훅·서비스 | §4.1~4.3 | C | 프론트엔드 미착수 |

### 4. Phase별 진척률

| Phase | 백엔드 | 프론트엔드 | 종합 |
|-------|-------|-----------|------|
| **Phase A** (모니터링 기본) | ✅ 100% (4 API) | ❌ 0% (6 컴포넌트 미생성) | 50% |
| **Phase B** (심화 기능) | ✅ 90% (4 API) | ❌ 0% (3 컴포넌트 + 모달) | 45% |
| **Phase C** (알림) | 🟡 50% (모델 + 조회 API만, `check_pipeline_alerts` 태스크 없음) | ❌ 0% (AlertBadge/AlertList 미구현) | 25% |

### 5. Top 5 갭

1. **프론트엔드 모니터링 대시보드 미착수 (C)** — 설계의 `NewsTab` sub-tab 구조 + 6개 컴포넌트(`PipelineStatusBar`, `CollectionStatsTable`, `MLModelCard`, `MLTrendChart`, `RecentErrorsList`, `LLMUsageSummary`) 모두 미생성. 백엔드 API는 완성되어 있으므로 즉시 구현 가능. (영향: 높음 — 운영 가시성 제로)
2. **`_log_collection()` 호출 커버리지 부족 (C, Phase 0 선행 작업)** — `collect_daily_news`, `collect_market_news`, `collect_category_news`, `classify_news_batch`, `analyze_news_deep`, `sync_news_to_neo4j` 등 6개 태스크에 로깅 미적용. 현재 `NewsCollectionLog`가 FMP/AV 편향. → `collection-logs` API 통계 신뢰도 저하. (`news/tasks.py:103, 189, 334, 469, 511, 588` 라인 보강 필요)
3. **`check_pipeline_alerts` Celery 태스크 부재 (C, Phase C)** — `AlertLog` 모델과 조회 API는 있으나 30분 주기 자동 감지 태스크 미구현. 이상 징후가 사람이 API를 호출해야만 발견되는 구조.
4. **Phase B 프론트엔드 (TaskTimelineChart / Neo4jStatusCard / MLCompareView / 롤백 2단계 모달) 전무 (C)** — 백엔드 `task_timeline`, `neo4j_status`, `ml_rollback_preview`, `ml_rollback` 4개 action은 모두 구현됨. FE만 붙이면 사용 가능.
5. **키워드 상세보기 FE 미구현 + `search_terms_en` 프롬프트 확장 안 됨 (B)** — 백엔드 `keyword_detail` action은 응답 완성되어 있으나, `DailyNewsKeyword.keywords`에 `search_terms_en` 추가가 안 됨(키워드 추출 프롬프트 확장 필요). 사용자가 키워드를 클릭해도 바텀시트가 뜨지 않음.

### 6. 특별 점검 사항

- 🔴 **Critical**: Phase 0 선행 작업(`_log_collection()` 보강)이 미완료 — 설계 §11이 "Phase A 착수 전 필수"로 명시
- 🟡 **Warning**: Neo4j 뉴스 이벤트 노드/엣지가 실제 그래프에 저장되는지 별도 검증 필요 (`news_neo4j_sync.py` 동작 결과 미확인)
- 🟡 **Warning**: LightGBM 모델 파일 저장 경로/버전 관리 전략 문서화 필요
- 🟢 **OK**: Celery Beat 6단계 스케줄이 `config/celery.py`에 정확히 반영됨

---

## 종합 권장 작업 (우선순위)

| 우선순위 | 앱 | 작업 | 난이도 |
|---------|----|----|------|
| P0 | News | `_log_collection()` 6개 태스크 보강 (Phase 0 선행) | 낮음 |
| P0 | SEC Pipeline | `CELERY_BEAT_SCHEDULE`에 `sync-sec-dirty-neo4j`, `check-new-filings` 등록 | 낮음 |
| P1 | News | 프론트엔드 Phase A 6컴포넌트 + NewsTab sub-tab 아키텍처 구현 | 중간 |
| P1 | News | `check_pipeline_alerts` Celery 태스크 + Beat 등록 | 낮음 |
| P1 | Validation | `validation_peer_system.md` Phase 6 섹션을 DNA 조합 방식으로 업데이트 (또는 LLM 큐레이션 재구현) | 낮음(문서) / 높음(재구현) |
| P2 | Validation | `custom_benchmark_engine.py` Redis 캐시 적용 검증 + 미구현 시 추가 | 중간 |
| P2 | News | Phase B 프론트엔드 4컴포넌트 + 롤백 2단계 모달 | 중간 |
| P2 | News | 키워드 추출 프롬프트에 `search_terms_en` 추가 + 바텀시트 FE 구현 | 중간 |
| P3 | SEC Pipeline | 핵심 통합 테스트 추가 (수집→추출→매칭→동기화 E2E) | 중간 |
| P3 | SEC Pipeline | Intelligence Report 공개 API 추가 (Admin 외부 노출) | 낮음 |

---

## 부록: 분류 기준 정의

- **(A) 완전 구현**: 설계대로 모델/서비스/API/태스크가 모두 코드에 존재하고 동작 가능
- **(B) 부분 구현**: 일부만 구현되거나, 외부 의존성·구성 누락으로 일부 시나리오에서 비정상
- **(C) 미구현**: 설계만 있고 코드 없음 (백엔드 또는 프론트엔드 전체)
- **(D) 폐기/대체**: 설계가 폐기되었거나 다른 방식으로 대체됨 — 문서 갱신 누락 시 정합성 결함으로 표기
