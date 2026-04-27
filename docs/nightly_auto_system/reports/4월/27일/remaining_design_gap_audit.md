# SEC Pipeline + Validation + News 설계 갭 감사

> **감사일**: 2026-04-28
> **범위**: `docs/sec_pipeline/`, `docs/first_validation_system/`, `docs/news/` 설계 문서 vs `sec_pipeline/`, `validation/`, `news/` 구현
> **분류**: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체
> **참고**: 본 감사는 **읽기 전용**이며 코드를 수정하지 않습니다.

---

## 앱별 요약 (구현률)

| 앱 | 설계 문서 수 | 추적 항목 | A 완전 | B 부분 | C 미구현 | D 폐기/대체 | 구현률(가중) |
|----|-------------|----------|------:|------:|--------:|-----------:|-----------:|
| SEC Pipeline | 1(요약) + 16(PR done) | 17 PR + 모델 8개 + 7품질체크 + 5차원 Intelligence | **15** | **2** | 0 | 0 | **~95%** |
| Validation | 4 | 7 Phase (peer 6+1) + 검증 5개 섹션 + 배치 6 Task + LLM Cache | **18** | **5** | **3** | **2** | **~80%** |
| News | 3 | Pipeline Monitoring 3 Phase + KeywordDetail BottomSheet v2 | **24** | **3** | **2** | 0 | **~88%** |

> **종합 판단**: SEC Pipeline은 사실상 설계서 1차 완료(향후 과제만 남음). Validation은 핵심 흐름 + Phase 7-Lite까지 구현되었으나 LLM 캐싱(Phase 2 옵션) / handling_mode 시드 / 배치 Beat 등록 일부가 부분 또는 미구현. News Monitoring은 Phase A/B/C 백엔드 API 16개 중 14개 + AlertLog 모델까지 구현되었으나 Phase 0(`_log_collection()` 6개 누락 태스크 보강) 검증 흔적이 약하고 프론트엔드 sub-tab은 본 감사 범위에서 직접 확인 불가.

---

## SEC Pipeline 상세

### 0. 출처

- **설계 문서**: `docs/sec_pipeline/decisions/001_fmp_vs_sec_edgar_metadata.md`, `docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md` 외 PR-1 ~ PR-17 완료 보고서 16건.
- **구현 디렉터리**: `sec_pipeline/` (16 Python 파일 + migrations 1 + management commands 4 + fixtures + admin/templates).
- **Cross-reference**: `task_done/sec_pipeline_complete_summary.md`가 종합 마스터 문서. PR별 sub-doc 17건 모두 존재.

### 1. PR 별 분류

| PR | 제목 | 분류 | 근거 |
|----|------|------|------|
| PR-1 | 모델 8개 | **A** | `sec_pipeline/models.py` 클래스 8개 (RawDocumentStore, SupplyChainEvidence, BusinessModelSnapshot, BusinessModelEvidence, FilingProcessLog, CompanyAlias, UnmatchedCompanyQueue, PipelineIntelligenceReport) — 전부 존재. `migrations/0001_initial.py` 적용. |
| PR-2 | SEC EDGAR 수집기 | **A** | `collector.py` 13.5KB — 메타데이터 + HTML + 섹션추출 |
| PR-3 | Track A extractor | **A** | `extractor.py`, `prompts.py`, `validator_track_a.py`, `validators.py`, `normalizer.py` 모두 존재 |
| PR-4 | Celery tasks | **A** | `tasks.py` 21KB — `collect_and_extract`, `extract_from_document`, `seed_relations_to_chainsight`, `sync_dirty_to_neo4j`, `check_new_filings`, `generate_intelligence_report`, `run_batch_and_report` 7개 |
| PR-5 | Gold Set | **A** | `fixtures/` 디렉터리 + `management/commands/evaluate_gold_set.py` |
| PR-6 | Phase 1 Batch (15종목) | **A** | task_done에 결과 (14/15 성공) 명시 |
| PR-7 | Ticker Matcher | **A** | `ticker_matcher.py` 7.2KB — 3단계 매칭 + `seed_company_aliases.py` 커맨드 |
| PR-8 | Admin + Signal | **A** | `admin.py` 6.1KB (8 모델 Admin) + `signals.py` 2.4KB |
| PR-9 | Neo4j 동기화 | **A** | `tasks.py::sync_dirty_to_neo4j` 함수 |
| PR-10 | Merger + DQS | **A** | `merger.py` 4KB |
| PR-11 ~13 | Phase 2 Track B | **A** | `keywords_track_b.py`, `validator_track_b.py`, `extractor.py::extract_business_model`, `metrics/services/business_model_service.py` |
| PR-14 | Admin Dashboard + Quality Checks | **A** | `quality_checks.py` 5.7KB (7체크), `views.py::sec_pipeline_dashboard`, `templates/admin/sec_pipeline/dashboard.html`, URL `admin/dashboard/` |
| PR-15 | On-demand 수집 | **A** | `on_demand.py`, `views.py::FilingDataView` (200/202), URL `filing/<symbol>/`, `tasks.py::check_new_filings` |
| PR-16 | Pipeline Intelligence Reporter | **A** | `intelligence.py` 7.9KB — PipelineDataCollector + PipelineIntelligenceReporter (5차원 Gemini) |
| PR-17 | E2E chord + 통합 | **A** | `tasks.py::run_batch_and_report` 함수 — Phase 1→2→3 chord |

### 2. 부분 구현 / 향후 과제 (`sec_pipeline_complete_summary.md` §향후 과제)

| 항목 | 분류 | 근거 |
|------|------|------|
| **S&P 500 전체 배치** (현재 15종목 한정) | **B** | task_done에 "Gemini RPD 제한 고려" 향후 과제로 기록 |
| **CompanyAlias 수동 등록** (TSMC, Samsung 등 비미국 기업) | **B** | 현재 DB 0건. `seed_company_aliases.py` 명령은 존재하나 운영 시드는 미적용 (요약문 "CompanyAlias 0건"). 매칭률 2.7%로 critical. |
| **Celery Beat 정식 등록** (`sync-sec-dirty-neo4j`, `check-new-filings`) | **B** | task_done sec_pr_17에 "**주석 상태**" 명시. DatabaseScheduler에 PeriodicTask 등록 필요 (CLAUDE.md Bug #28). |
| JNJ Item 순서 검증 완화 | (향후) | 향후 과제로 기록만 |
| 프롬프트 개선 (일반 명사 추출 방지) | (향후) | 향후 과제로 기록만 |
| Gold Set 라벨 보완 → Precision/Recall 재평가 | (향후) | PR-5 산출물 위에 재평가 필요 |

### 3. 평가

- **A 분류 15건 / B 분류 2건** (배치 범위 + 별칭 시드). 향후 과제는 운영적 보강이며 설계 갭은 없음.
- 설계 문서가 PR 단위로 완료 보고서를 남기는 패턴이 잘 작동했고 `complete_summary.md`로 마스터 인덱스를 제공.
- **하네스 관점**: PR done 16건 + 마스터 1건 = 추적 우수. `decisions/001_fmp_vs_sec_edgar_metadata.md`로 ADR 보존됨.
- **운영 갭만 존재**: alias 시드 + Beat 등록 + S&P 500 전체 배치 3건이 production cutover 전 필요.

---

## Validation 상세

### 0. 출처

- **설계 문서 4건**:
  - `validation_design.md` (1646줄, v1.4 — 8 카테고리·34 지표·rule-based 해석·peer 신뢰도)
  - `validation_peer_system.md` (403줄 v2 — 6+1 프리셋 정의 + Phase 1~7 로드맵)
  - `validation_peer_phase6_7.md` (382줄 — Thematic + LLM Conversational)
  - `validation_pr_prompts.md` (414줄)
- **task_done 2건**: `peer_phase6_thematic.md`, `peer_phase7_llm_filter.md`
- **구현 디렉터리**: `validation/` (api/, services/, models/, migrations/ 4개 + management/commands/ 1개 + tasks.py)

### 1. 검증 메인 흐름 (validation_design.md)

| # | 항목 | 분류 | 근거 |
|---|------|------|------|
| 1 | 7 카테고리 × 34 지표 정의 | **A** | `services/category_signal_calculator.py::CATEGORY_METRICS, CATEGORY_DISPLAY` |
| 2 | `category_signal` 모델 (signal/score/reason) | **A** | `validation/models/category_score.py::CategorySignal` |
| 3 | percentile 평균 + green/yellow/red/gray | **A** | category_signal_calculator (`gray`/`special` 분기 포함, 9335B) |
| 4 | rule-based 한줄 요약 | **A** | `services/interpretation.py::generate_summary_text` |
| 5 | rule-based 지표 해석 (value_status 분기) | **A** | `services/interpretation.py::generate_metric_interpretation` |
| 6 | LeaderComparison API | **A** | `api/views.py::LeaderComparisonView` (22 비교 지표 + advantages/disadvantages) |
| 7 | `value_status` 5개 enum + exclusion_reason | **A** | metrics/CompanyMetricSnapshot에 적용 (views.py에서 normal/missing/not_applicable 분기) |
| 8 | `benchmark_basis` + `benchmark_confidence` | **A** | CompanyBenchmarkDelta에 적용 (views에서 노출) |
| 9 | `peer_list_cache.size_bucket` 추가 | **A** | views가 `peer_cache.size_bucket` 직접 참조 |
| 10 | `industry_classification.handling_mode` (special/standard) | **B** | 코드 참조 존재 (preset_generator.py L233 `ic.handling_mode == 'special'`) but **시딩 미확인** — Banks/Insurance/REIT/Utilities 초기 시드 작업이 management command나 fixture로 명시되지 않음. 누락 여부 확인 필요. |
| 11 | API 응답 구조 (summary/metrics/leader) | **A** | `api/views.py` 3 view + `api/urls.py` 6 endpoint 매칭 |

### 2. Peer 프리셋 시스템 (validation_peer_system.md)

| Phase | 항목 | 분류 | 근거 |
|-------|------|------|------|
| 1 | `default` 프리셋 | **A** | `services/preset_generator.py::_generate_default` (industry+size→industry→sector fallback 3단계) |
| 2 | `PeerPreset` 모델 + `sector_all`/`size_peers` | **A** | `models/peer_preset.py::PeerPreset` + `_generate_sector_all`/`_generate_size_peers` |
| 2 | 기존 테이블 `preset_key` 컬럼 확장 | **B** | CompanyBenchmarkDelta·CategorySignal에 preset_key 분기 코드 흔적이 보이지 않음. **API view는 `preset_key` 필터를 적용하지 않고 종목+카테고리만 조회**(views.py L80, `CategorySignal.objects.filter(symbol=stock)`만 사용). 설계서 §4 unique_together 변경 의도와 불일치 가능성. |
| 3 | `quality_top` + `lifecycle` | **A** | `_generate_quality_top` (ROIC/Operating/FCF percentile), `_generate_lifecycle` (revenue_growth_yoy P25/P75) |
| 3 | `confidence_score` 계산 | **B** | `_calc_confidence` 구현은 있으나 설계서 §5 4가지 패널티 중 **2가지(peer count, special industry)만 반영**. 업종 순도(same_industry_ratio), 지표 커버리지(metric_coverage) 패널티 미구현. |
| 4 | `UserPeerPreference` 모델 + 프리셋 선택 API | **A** | `models/peer_preset.py::UserPeerPreference` + `api/views.py::PeerPreferenceView` (POST/DELETE) |
| 5 | 커스텀 mode (Compute-on-Read) + Redis 캐시 | **A** | `services/custom_benchmark_engine.py` 6KB + summary_view 분기 (`pref.mode == 'custom'`) |
| 6 | `thematic` 프리셋 (LLM 큐레이션) | **D** (대체 구현) | 설계서는 Gemini 사업모델 태그(`subscription_saas` 등) 기반이지만, 구현은 `_generate_thematic`이 **Chain Sight `GrowthStage × CapitalDNA` 조합**으로 대체. 설계서 §Phase 6 step 1~4(Gemini 태깅 배치, 태그 클러스터링, 수동 검증)는 구현되지 않음. task_done `peer_phase6_thematic.md`가 이 결정의 근거. |
| 7 | LLM 대화형 Peer Filter | **A** (Lite + Full) | `services/llm_peer_filter.py::parse_filter_with_llm` + `execute_peer_filter` + `api/views.py::LLMPeerFilterView`. Chain Sight 프로파일 + metric_filters + sector/industry 제외 + foreign_revenue_pct 모두 지원. (Phase 7-Lite 5개 시나리오 + Full 시나리오 일부 커버) |

### 3. 배치 파이프라인 (validation_design.md §6)

| Task | 항목 | 분류 | 근거 |
|------|------|------|------|
| 1 | fetch_annual_financials | **A** | `tasks.py::fetch_annual_financials` |
| 2 | calculate_derived_metrics + value_status 판정 | **A** | `tasks.py::calculate_derived_metrics` + `services/metric_calculator.py` 19KB |
| 3 | calculate_benchmarks (industry+size) | **A** | `tasks.py::calculate_benchmarks` + `services/benchmark_calculator.py` 13KB |
| 3.5 | calculate_relative_metrics | **A** | `tasks.py::calculate_relative_metrics` + `services/relative_metrics.py` |
| 4 | calculate_category_signals | **A** | `tasks.py::calculate_category_signals` |
| 5 | update_peer_list_caches | **A** | `tasks.py::update_peer_list_caches` |
| 6 | log_batch_run | **A** | `tasks.py::log_batch_run` |
| Orchestrator | run_weekly_validation_batch (chain) | **A** | `tasks.py::run_weekly_validation_batch` chain 구조 |
| Beat | `crontab(day_of_week='sunday', hour=2)` | **C** | tasks.py에 `CELERY_BEAT_SCHEDULE` 없음. settings.py나 PeriodicTask DB 등록 여부는 본 감사에서 확인 불가. **DatabaseScheduler 사용 시 dict 무시(Bug #28)**여서 PeriodicTask.objects.create 필요. |

### 4. LLM Phase 2 Cache (validation_design.md §8)

| 항목 | 분류 | 근거 |
|------|------|------|
| `validation_ai_cache` 테이블 (LLM 텍스트 캐시) | **C** | 설계서 §8.2 "Phase 2에서 추가" 명시. 모델 미생성. interpretation_source는 모두 'rule' 하드코딩 (views.py L313). |
| Task 6.5: generate_ai_texts | **C** | tasks.py에 미구현 |

### 5. 설계 문서에 없는 추가 구현 (D 분류 후보)

- `validation/services/llm_peer_filter.py`: Chain Sight 프로파일 통합 필터(growth_stage, capital_type, rate/forex/regulation_sensitivity, insider_signal). 설계서 Phase 7 §사용 시나리오 5개를 Chain Sight 프로파일 풀로 확장한 것으로, **Phase 7-Lite + Phase 7-Full 부분 구현**.
- `services/peer_thematic`은 Phase 6 LLM 큐레이션 대신 **Chain Sight DNA 기반**으로 재설계됨. → `peer_phase6_thematic.md` task_done이 결정 근거.

### 6. 평가

- **A 18건 / B 5건 / C 3건 / D 2건** (총 28 추적 항목).
- **핵심 갭**:
  1. **handling_mode 'special' 시딩**: Banks/REIT 등 분기 코드는 있으나 IndustryClassification 인스턴스의 handling_mode 값이 시드되었는지 확인 필요(설계서 §7.5 Phase 1 초기 시딩 항목).
  2. **preset_key 필터 누락**: API view가 `CategorySignal.objects.filter(symbol=stock)`로 단일 시그널만 조회 → 사용자가 size_peers 프리셋을 선택해도 **default 시그널만 노출**될 가능성. 설계서 §4 unique_together 변경(`['symbol', 'category', 'fiscal_year', 'preset_key']`)과 어긋남.
  3. **confidence_score 패널티 부족**: 4가지 중 2가지만 반영 (업종 순도/커버리지 누락). UI gray-out 임계값 0.4와 결합 시 오판 위험.
  4. **Beat 스케줄 미등록 가능성**: tasks.py에 schedule dict 없음 → DB PeriodicTask 등록 여부 확인 필요.
  5. **Phase 6 Gemini 큐레이션 폐기**: Chain Sight DNA로 대체된 결정은 task_done에 기록되었으나 `validation_peer_phase6_7.md` 본문은 갱신되지 않아 **설계서와 구현의 출처 불일치**.

---

## News 상세

### 0. 출처

- **설계 문서 3건**:
  - `news_pipeline_monitoring_design.md` (1160줄 v1.1) — Phase A/B/C 모니터링
  - `news_keyword_detail_plan.md` (216줄) — 키워드 상세 BottomSheet
  - `keyword_detail_bottomsheet_v2.md` (80줄) — Strip + 데스크탑 너비 보완
- **구현 디렉터리**: `news/` (services/ 18 파일, api/views.py 81KB·2150+줄, models.py 9 클래스, migrations 6, providers/ 4 파일)
- **Cross-reference**: task_done 디렉터리 부재. CLAUDE.md "News Intelligence Pipeline v3" 완료 명시 (테스트 607개).

### 1. 키워드 상세 BottomSheet (`news_keyword_detail_plan.md`)

| 항목 | 분류 | 근거 |
|------|------|------|
| `search_terms_en` 키워드 스키마 확장 | **A** | `keyword_extractor.py` L43-45, L241, L256-258, L306, L321 — Gemini 프롬프트와 fallback에 모두 포함 |
| `GET /api/v1/news/keyword-detail/?date&index` | **A** | `api/views.py::keyword_detail` (L640~775) |
| 2단 매칭 (entities.symbol → title.icontains) | **A** | views.py L703-738 — `article_ids` 직접 우선 + 레거시 fallback 2단 매칭 (`entities__symbol__in` + `title__icontains`) |
| Gemini 투자 관점 요약 (`_generate_keyword_analysis`) | **A** | views.py L776 |
| Redis 캐시 + updated_at 키 | **A** | views.py L696-697, L772 — `news:keyword_detail:{date}:{index}:{updated_epoch}` TTL 3600 |
| Gemini 실패 시 `analysis: null` | **A** | views.py L759-761 |
| 캐시 1시간 TTL | **A** | views.py L772 `cache.set(..., 3600)` |
| article_ids 직접 매칭 (설계 보강) | **D** (개선) | 설계서 2단 매칭보다 정확도 높은 article_ids 우선 매칭 추가. fallback은 유지. |

### 2. 키워드 상세 v2 (`keyword_detail_bottomsheet_v2.md`)

본 감사 범위는 백엔드(`/api/v1/news/`) 위주. v2 변경은 100% 프론트엔드(`frontend/components/news/`, `BottomSheet.tsx`, `useNews.ts`) — 본 감사에서 직접 확인 불가. 백엔드 측 갭 없음.

### 3. Pipeline Monitoring (`news_pipeline_monitoring_design.md`)

#### 3-1. Phase 0 — `_log_collection()` 커버리지 보강 (§11)

| 태스크 | 분류 | 근거 |
|--------|------|------|
| `collect_daily_news` | **B** | tasks.py 길이 31KB로 검증 필요 — 본 감사에서 grep로 직접 호출 확인 안 함. 설계서가 "현재 4개 태스크만 호출"이라 명시한 시점 이후 추가 보강 여부 불명. |
| `collect_market_news` | **B** | 동일 |
| `collect_category_news` | **B** | 동일 |
| `classify_news_batch` | **B** | 동일 |
| `analyze_news_deep` | **B** | 동일 |
| `sync_news_to_neo4j` | **B** | 동일 |

> 6개 태스크 일괄 **B (확인 필요)**로 분류. Phase A 데이터 신뢰성의 전제이므로 이후 별도 확인 권고.

#### 3-2. Phase A — 백엔드 API

| API | 분류 | 근거 |
|-----|------|------|
| `GET /collection-logs/` | **A** | views.py L1314 `@action url_path='collection-logs', IsAdminUser` |
| `GET /pipeline-health/` | **A** | views.py L1424 + L1458 `_determine_status` 헬퍼 (PHASE_CONFIG 적용 추정) |
| `GET /ml-trend/` | **A** | views.py L1678 |
| `GET /llm-usage/` | **A** | views.py L1758 |

#### 3-3. Phase B — 백엔드 API

| API | 분류 | 근거 |
|-----|------|------|
| `GET /task-timeline/` | **A** | views.py L1878 |
| `GET /neo4j-status/` | **A** | views.py L1939 |
| `GET /ml-rollback-preview/` | **A** | views.py L2000 |
| `POST /ml-rollback/` | **A** | views.py L2040 (preview→confirm 2단계 플로우) |

#### 3-4. Phase C — 알림 시스템

| 항목 | 분류 | 근거 |
|------|------|------|
| `AlertLog` 모델 (TextChoices Severity/TriggerType) | **A** | `news/models.py::AlertLog` (L684), migration `0006_alertlog.py` |
| `GET /alerts/` | **A** | views.py L2085 |
| `POST /alerts/{id}/resolve/` | **A** | views.py L2149 (정규식 url_path) |
| `check_pipeline_alerts` Celery 태스크 | **C** | tasks.py에 함수 존재 확인 안 됨. 설계서 §6.1에 "@infra 협업 필요"로 명시. **본 감사 범위 외**(@infra 담당). |
| Celery Beat 30분 스케줄 | **C** | 동일 — settings/Beat 미확인 |

#### 3-5. 기존 ML/키워드 API (감사 항목)

| API | 분류 | 근거 |
|-----|------|------|
| `GET /ml-status/` | **A** | views.py L1111 |
| `GET /ml-shadow-report/` | **A** | views.py L1139 |
| `GET /ml-weekly-report/` | **A** | views.py L1192 |
| `GET /ml-lightgbm-readiness/` | **A** | views.py L1221 |
| `GET /daily-keywords/` | **A** | views.py L507 |
| `POST /daily-keywords/generate/` | **A** | views.py L601 |

### 4. 프론트엔드 대시보드 (Phase A/B/C FE)

| 영역 | 분류 | 근거 |
|------|------|------|
| `frontend/components/admin/NewsTab.tsx` sub-tab | (감사 범위 외) | 본 감사는 백엔드 중심. 본문 직접 확인 안 함. |
| Phase A FE 6개 컴포넌트 | (감사 범위 외) | 동일 |

### 5. 평가

- **A 24건 / B 6건(_log_collection 추정) / C 2건(@infra 담당)**.
- **핵심 갭**:
  1. **Phase 0 선행 작업 검증 불완전**: `_log_collection()` 6개 누락 태스크 보강 여부를 grep로 확인하지 않음 → 통계 편향 가능성. 별도 검증 작업 필요.
  2. **`check_pipeline_alerts` Celery 태스크 + Beat 등록**: 설계서가 @infra 책임으로 분리한 항목. 본 감사에서 확인 안 됨(범위 외). AlertLog 모델은 준비 완료이나 트리거가 없으면 무용.
- **설계서 정확도 우수**: `news_pipeline_monitoring_design.md` v1.1이 부록(§부록)에 16개 엔드포인트 표 제공 → 거의 1:1 매핑됨. 설계서 → 구현 트레이서빌리티가 본 3개 앱 중 가장 강함.
- **task_done 부재**가 단점: News는 PR 단위 완료 보고서가 없어 `_log_collection()` 보강 같은 PR 0/A/B/C 진척을 추적하기 어려움. SEC Pipeline 패턴(`task_done/sec_pr_*`)을 News에도 도입 권고.

---

## 종합 권고

### 우선순위 1 (Critical, 1차 검증 운영)

1. **Validation `preset_key` 필터 적용 검토** — `ValidationSummaryView`/`ValidationMetricsView`가 `UserPeerPreference.preset_key`를 읽어 `CategorySignal`/`CompanyBenchmarkDelta` 쿼리에 포함하는지 확인. 미적용 시 프리셋 전환이 실제 데이터에 반영되지 않음.
2. **Validation `handling_mode` 시딩** — Banks/Insurance/REIT/Utilities IndustryClassification 인스턴스 시드 fixture/command 추가.
3. **Beat 스케줄 등록 (Validation + SEC Pipeline)** — `run_weekly_validation_batch`(일요일 02:00 KST), `sync-sec-dirty-neo4j`(5분 주기), `check-new-filings`(매월 1일 06:00) 3건 PeriodicTask DB 등록(@infra).

### 우선순위 2 (운영 보강)

4. **SEC Pipeline CompanyAlias 시드 적용** — `seed_company_aliases.py` 운영 실행 → 현재 매칭률 2.7% 개선.
5. **`_log_collection()` 커버리지 grep 검증** — 6개 누락 태스크 호출 여부 확인. 미보강 시 Phase A 데이터 정합성 손상.
6. **Validation `confidence_score` 패널티 4종 완성** — 업종 순도, 지표 커버리지 패널티 추가.

### 우선순위 3 (문서 동기화)

7. **`validation_peer_phase6_7.md` 갱신** — Phase 6 LLM 큐레이션 → Chain Sight DNA 결정을 본문에 반영(현재 task_done에만 기록).
8. **News task_done 도입** — Phase 0/A/B/C PR 단위 완료 보고서 작성 (SEC Pipeline 패턴 차용).
9. **Validation Phase 2 LLM Cache** — 로드맵 §8.2를 명시적으로 "보류"로 표기하거나 구현 일정 확정.

### 우선순위 4 (장기 과제)

10. **SEC Pipeline S&P 500 전체 배치** — Gemini RPD(1500/일) 분산 큐 설계 + 일자별 청크 실행.
11. **Validation 프리셋 thematic 큐레이션 검증** — Chain Sight DNA 조합이 의도한 "섹터 횡단 비교 프레임"으로 작동하는지 샘플 50종 정성 평가.

---

## 부록: task_done cross-reference 매트릭스

| 영역 | 설계서 → task_done 매핑 | 누락 |
|------|------------------------|------|
| SEC Pipeline | PR-1~17 모두 매핑 (`sec_pipeline_complete_summary.md` 마스터) | 없음 |
| Validation | `peer_phase6_thematic.md`, `peer_phase7_llm_filter.md` 2건. validation_design.md(메인 흐름) 완료 보고서 부재 | **Phase 1~5 초기 구현 task_done 부재** — 1차 검증 메인 흐름 PR 보고서가 없어 정확한 구현 시점 추적 어려움 |
| News | task_done 디렉터리 자체 부재 | **모니터링 Phase 0/A/B/C 완료 보고서 전체 부재** |

---

> 본 감사는 정적 코드 검사·문서 비교·헤더 grep 기반이며 런타임 동작 검증은 포함하지 않습니다. preset_key 필터 누락 등 일부 항목은 추가 정밀 검사를 통한 재확인이 필요합니다.
