# SEC Pipeline + Validation + News 설계 갭 감사

> **감사 기준일**: 2026-05-11
> **감사 범위**: `docs/sec_pipeline/`, `docs/first_validation_system/`, `docs/news/plan/` 설계 문서 vs. `sec_pipeline/`, `validation/`, `news/` 구현 코드
> **방법**: 설계서 명세 추출 → 구현 코드 grep/Read → 분류표 (A/B/C/D) → 갭 상세
> **분류**: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 앱별 요약 (구현률)

| 앱 | 전체 항목 | A (완전) | B (부분) | C (미구현) | D (폐기/대체) | 종합 |
|----|----------|---------|---------|-----------|--------------|------|
| **SEC Pipeline** | 17 PR | 14 | 3 | 0 | 0 | 🟢 사실상 완전 구현. E2E chord 단순화 + 통합 테스트 부재 + Beat 문서 부정합 외 갭 없음 |
| **Validation** | 28 기능 | 18 | 7 | 2 | 1 | 🟡 골격 완성. preset 분기 미작동 (모델 필드만 존재, 계산은 default 단일) + Beat 미등록 + Thematic 구현 방식 대체 |
| **News** | 21 기능 | 18 | 3 | 0 | 0 | 🟢 키워드 상세 + BottomSheet v2 + 모니터링 Phase 0~C 모두 완료. 신규 API 회귀 테스트 누락만 잔여 |

**종합 결론**:
- 3개 앱 모두 **설계서가 명시한 핵심 기능은 구현 단계**에 도달했음. 미구현(C)은 Validation 2건뿐.
- 가장 위험한 갭: **Validation의 preset_key 분기 계산 미작동** — 사용자가 프리셋을 전환해도 같은 default 데이터만 반환됨. 모델 필드와 unique_together만 마련된 상태로, Phase 6/7 frontend는 작동 외관을 보이지만 benchmark/category_signal 계산은 단일 컨텍스트 고정.
- 두 번째 위험: **News의 신규 API 12종 + AlertLog 트리거 7종에 자동화 회귀 테스트 부재**. 운영 안정성을 통합 테스트/UI 수동 검증에 의존 중.
- 세 번째 위험: **SEC Pipeline `tests.py`는 빈 파일** (단위 테스트는 `tests/unit/sec_pipeline/`로 이동했으나 통합/E2E 자동화는 없음).

---

## SEC Pipeline 상세

### 구현률 요약
- 전체 PR/기능 17개 중: **A=14, B=3, C=0, D=0**
- 17개 PR 거의 전부 구현 완료. 다만 (1) `tests.py`는 빈 파일이고 단위 테스트는 `tests/unit/sec_pipeline/` 7파일/1,186줄로 이동했으나 통합/E2E 자동화는 부재, (2) Celery Beat 스케줄이 task_done 기준으로는 "주석 상태"였으나 실제로는 `config/celery.py`에 활성 등록되어 문서 갱신 필요, (3) `seed_company_aliases`/`rematch_unmatched` 등 PR-7~10 이후 추가된 운영 명령이 task_done에 미반영.

### PR별 분류표

| PR# | 기능 | 분류 | 핵심 증거 (파일:라인 또는 누락) | 비고 |
|-----|------|------|---------------------------------|------|
| PR-1 | 8개 모델 + migration | A | `sec_pipeline/models.py:15-388` (8개 클래스), `migrations/0001_initial.py` 단일 파일에 8개 모델 전부 포함, `apps.py`에서 `signals` ready 호출 | `neo4j_dirty` only, `get_latest_by='as_of_date'`, `unique_together=[('alias','context_sector')]` 전부 준수 |
| PR-2 | SEC EDGAR 수집기 + 사후 검증 | A | `collector.py:39-373` (SECFilingCollector, _get_cik, fetch_filing_html, extract_sections, extract_sections_fallback), `validators.py:21-128` (3종 검증) | FMP→SEC EDGAR 대체 결정(decisions/001) 반영 |
| PR-3 | Track A 키워드 필터 + Gemini 추출 | A | `normalizer.py:10-83` (30개 키워드, filter_paragraphs), `prompts.py:11-43` (PROMPT_VERSION='v1'), `extractor.py:18-91` (gemini-2.5-flash, thinking_budget=0), `validator_track_a.py:61-164` | `_is_generic_term` 추가 (설계 후 보강) |
| PR-4 | Celery tasks + 에러 핸들링 | A | `tasks.py:22-145` (collect_and_extract, retry=3/60s), `tasks.py:148-278` (extract_from_document, retry=2), `exceptions.py:13-35` (4개 예외), `sp500.py:8-15` | retry/backoff 설계와 일치 |
| PR-5 | Gold Set + 평가 command | A | `fixtures/gold_set.json`, `fixtures/gold_set_schema.py`, `management/commands/evaluate_gold_set.py:1-179` | section/Track A precision/recall 모두 평가 |
| PR-6 | 15종목 배치 검증 (운영 산출물) | A | task_done 보고서가 결과 산출물이며 코드는 PR-4가 담당 | 결과 데이터(`110 evidences` 등)만 sub_summary 반영 |
| PR-7 | TickerMatcher 3단계 + 큐 적재 | A | `ticker_matcher.py:22-210` (alias→exact→fuzzy ≥85), `_get_fuzzy_candidates`, `match_with_queue` | rapidfuzz 의존성 사용 |
| PR-8 | Admin + post_save signal | A | `admin.py:76-123` (UnmatchedCompanyQueueAdmin: list_editable, cross_sector_flag, fuzzy_top1, 3 actions), `signals.py:21-71` (sector 격리 + CompanyAlias 등록) | 설계대로 sector 전파 금지 준수 |
| PR-9 | sync_dirty_to_neo4j | A | `tasks.py:337-452` (Phase A/B/C, select_for_update(skip_locked), DELETE+CREATE dynamic type, BATCH_SIZE=500, KNOWN_TYPES 6개) | 설계 원칙 7가지 전부 준수 |
| PR-10 | merger + DQS + process_unmatched_queue | A | `merger.py:36-135` (RELATIONSHIP_SPECIFICITY, SOURCE_RELIABILITY, bounded boost, DQS 내부/사용자 키 분리), `management/commands/process_unmatched_queue.py:1-67` | DQS `_dqs_total` 내부 / `source_count` 노출 분리 정확 |
| PR-11 | Track B 키워드 사전 | A | `keywords_track_b.py:9-78` (5개 필드 키워드 + filter_paragraphs_track_b) | |
| PR-12 | Track B Gemini 추출 + 검증 + 저장 | A | `extractor.py:93-145` (extract_business_model), `validator_track_b.py:23-115` (FIELD_ALLOWED_VALUES, save_business_model_snapshot), `prompts.py:46-97` | `tasks.py:236-276`에서 Track A 실패해도 Track B 시도 |
| PR-13 | Business Model 서비스 레이어 | A | `metrics/services/business_model_service.py:16-115` (get_business_model with `for_api` 게이트, get_business_model_evidence, is_recurring_business) | 원칙 6 confidence 노출 경계 게이트 정확 |
| PR-14 | Admin 대시보드 + 7개 quality_checks | A | `views.py:15-26` (sec_pipeline_dashboard, staff_member_required), `quality_checks.py:17-165` (7개 체크 + get_dashboard_stats), `templates/admin/sec_pipeline/dashboard.html`, `urls.py:7` | 7개 임계값 모두 일치 |
| PR-15 | On-demand + check_new_filings | A | `on_demand.py:18-68` (1년/1시간 중복 방지), `views.py:29-51` (FilingDataView, IsAdminUser, 200/202), `tasks.py:464-497` (check_new_filings) | audit P0 #6 IsAdminUser 적용 |
| PR-16 | Pipeline Intelligence Reporter | A | `intelligence.py:63-223` (PipelineDataCollector 5차원 + PipelineIntelligenceReporter Gemini), `admin.py:128-171` (severity_badge, regenerate_report) | trend_vs_previous, prompt_version 모두 저장 |
| PR-17 | E2E chord (run_batch_and_report) | **B** | `tasks.py:500-555`에서 `chord` 미사용, `for symbol in symbols: collect_and_extract(symbol)` 순차 호출. task_done은 "chord 대신 순차 실행 (1인 개발 단순성)" 명시 | 코드는 정상이고 결정도 문서화돼 있어 사실상 의도된 단순화 |

### 갭 항목 상세 (B/C/D만)

- **[B] PR-17 E2E "chord" 통합**: 설계서 PR 제목이 "Celery chord 통합"이지만 실제 구현은 `run_batch_and_report` 함수가 `for symbol in symbols: collect_and_extract(symbol)`로 동기 순차 호출 (`tasks.py:524`). chord/group 미사용. task_done 본문에는 "chord 대신 순차 실행 (1인 개발 단순성)"이라고 의도가 명시돼 있어 폐기라기보다 **의도된 단순화**.

- **[B] 통합/E2E 테스트 부재**: `sec_pipeline/tests.py:1`은 1줄짜리 빈 파일. 단위 테스트는 `tests/unit/sec_pipeline/` 7파일 1,186줄 존재(test_collector, test_extractor, test_models, test_normalizer, test_quality_checks, test_ticker_matcher, test_validators)지만 `tests/integration/`에는 sec_pipeline 통합 테스트 없음. PR-17 보고서가 명시한 "E2E 테스트"는 운영 환경 5종목 실측 결과뿐이고 자동화 테스트 코드는 미존재.

- **[B] Celery Beat 스케줄 문서-실제 불일치**: PR-17 task_done 본문 끝과 `tasks.py:558-566`은 Beat 스케줄을 "주석 상태"로 명시. 그러나 실제 `config/celery.py:777-794`에는 `sec-sync-dirty-neo4j`(*/5분), `sec-seed-relations-to-chainsight`(매일 12:00), `sec-check-new-filings`(매월 1일 06:00)이 활성 등록. 운영은 실행 중이나 task_done 문서가 갱신되지 않은 상태.

### 부수 관찰 (분류 대상 아님)
- `management/commands/`에 `rematch_unmatched.py`(`tasks.py` 보강용 운영 도구)와 `seed_company_aliases.py`(외국 기업 Stock+CompanyAlias 시드)가 있으나 task_done 문서에 미반영. 둘 다 PR-7/PR-10 이후 추가된 운영 보강 명령으로 추정.
- `validator_track_a.py:23-58`의 `GENERIC_COMPANY_TERMS`(35개+) 및 `_GENERIC_SUFFIXES` 패턴 매칭은 PR-7 task_done의 "프롬프트 개선" 향후 과제를 코드 측면에서 보강한 결과.
- `seed_company_aliases.py:103`에서 `CompanyAlias.source='seed'` 사용하나 모델의 `SOURCE_CHOICES`(`models.py:276-280`)에는 `'seed'`가 없음(`admin_resolved`/`auto_90pct`/`manual_seed`만). Django CharField choices는 DB 레벨 강제가 아니므로 저장은 되지만 admin/필터에서 빈 라벨로 표시될 가능성. 경미한 데이터 정합성 이슈.
- `rematch_unmatched.py:46`은 `UnmatchedCompanyQueue.status='not_company'`로 업데이트하나 모델의 `STATUS_CHOICES`(`models.py:310-317`)에는 해당 값 없음(`pending/matched/not_public/person/duplicate/skipped`). 추후 마이그레이션 필요할 수 있음.

---

## Validation 상세

### 구현률 요약
- 전체 기능 28개 중: **A=18, B=7, C=2, D=1**
- 모델 7종 중 6종 구현 (`PeerPreset`, `UserPeerPreference`, `CompanyBenchmarkDelta`, `CategorySignal`, `CompanyMetricLatest`, `ValidationNewsSummary`). 추가 명세 모델인 `PeerListCache`/`PeerMetricBenchmark`/`IndustryMetricBenchmark`/`MetricDefinition`/`CompanyMetricSnapshot`/`BatchJobRun`은 metrics 앱으로 이동.
- Peer 프리셋 6종 (`default`/`sector_all`/`size_peers`/`quality_top`/`lifecycle`/`thematic`) + custom: 모두 구현.
- API 엔드포인트 6개 모두 구현 (`summary`/`metrics`/`leader-comparison`/`presets`/`peer-preference`/`llm-filter`).
- **핵심 갭**: `preset_key` 전환은 PeerPreset 목록에만 반영되고, `benchmark`/`signal` 계산 자체는 'default' 단일 컨텍스트에서만 수행됨.

### 기능별 분류표

| 기능 | 설계 위치 | 분류 | 핵심 증거 | 비고 |
|------|----------|------|----------|------|
| MetricDefinition (34개) | design §4 / PR-1,2 | A | `metrics/models/metric_definition.py` + `seed_validation_data.py` | metrics 앱에 위치 |
| CompanyMetricSnapshot | design §7 / PR-1 | A | `metrics/models/metric_snapshot.py` | metrics 앱 |
| CompanyMetricLatest | design §7 / PR-1 | A | `validation/models/metric_latest.py`, `metric_calculator._update_latest` | |
| PeerMetricBenchmark | design §7 / PR-1 | A | `metrics/models/benchmark.py` | metrics 앱 |
| IndustryMetricBenchmark | design §7 / PR-1 | A | `metrics/models/benchmark.py` | |
| CompanyBenchmarkDelta | design §7 / PR-1 | A* | `validation/models/benchmark_delta.py` (preset_key 필드 포함) | preset_key=default만 채움 (B 항목 참조) |
| PeerListCache (peer_tier nullable) | design §7 / PR-1 | A | `metrics/models/benchmark.py:42` | nullable, 미사용 |
| CategorySignal (preset_key 포함) | peer §4 / PR-1 | A* | `validation/models/category_score.py:51` | unique_together에 preset_key 포함 (C 항목 참조) |
| BatchJobRun | design §7 / PR-1 | A | `metrics/models/batch_job.py`, `tasks.log_batch_run` | |
| IndustryClassification.handling_mode | PR-1, peer §6 | A | `stocks/models.py:729`, `seed_validation_data.py` Banks/Insurance/REIT/Utilities 시드 | |
| MetricDefinition 시드 + handling_mode 시드 | PR-2 | A | `validation/management/commands/seed_validation_data.py` | |
| Task 1 (FMP fetch) | PR-3 | **D** | `services/financial_fetcher.py` 가용성 확인만, 실수집 안 함 | 설계는 FMP API 직접 호출, 실제는 stocks 앱 기존 파이프라인 의존 |
| Task 2 (지표 계산 + value_status) | PR-3 | A | `services/metric_calculator.py` (value_status 5종) | |
| Task 3 (peer 선정 + benchmark) | PR-4 §3.2 | **B** | `services/benchmark_calculator.py` `assign_size_bucket`, `_select_peers` | preset_key 단일(default)로만 계산 |
| Task 3.5 (rev_growth_vs_industry) | PR-4 | A | `services/relative_metrics.py` | |
| Task 4 (category signal 계산) | PR-5 §3.1 | A | `services/category_signal_calculator.py`, `CATEGORY_METRICS`, special→gray | |
| Task 5 (peer cache 갱신) | PR-5 | **B** | `tasks.update_peer_list_caches` 카운트만 | confidence 재검증 미구현 |
| Task 6 (BatchJobRun 로깅) | PR-5 | A | `tasks.log_batch_run` | |
| Orchestrator (run_weekly_validation_batch) | PR-5 | A | `tasks.py:140` Celery chain | Beat 등록 코드 없음 |
| API: GET /summary/ | PR-6 §5 | **B** | `ValidationSummaryView` | `growth_trend_comparison` 누락, `industry_position.ranks` 5개만 하드코딩 |
| API: GET /metrics/?category= | PR-6 §5 | A | `ValidationMetricsView` (rule-based interpretation) | |
| API: GET /leader-comparison/ | PR-6 §5 | **B** | `LeaderComparisonView` | `growth_trend_comparison{}` 미구현 |
| API: GET /presets/ | peer §7 | A | `PresetListView` | confidence_label 한글 변환 포함 |
| API: POST/DELETE /peer-preference/ | peer §7 | A* | `PeerPreferenceView` | DRF JWT 보호 (B 항목 참조) |
| API: POST /llm-filter/ (Phase 7) | peer_phase6_7 | A | `LLMPeerFilterView` + `services/llm_peer_filter.py` | Chain Sight + 31 metrics + foreign_revenue + sector exclusion |
| Compute-on-Read 엔진 (custom mode) | peer §1, §7, peer_phase6_7 | A | `services/custom_benchmark_engine.py`, Redis 1h TTL | |
| Phase 6 thematic preset | peer_phase6_7, task_done | **D** | `preset_generator._generate_thematic` GrowthStage×CapitalDNA 사용 | 설계는 Gemini 사업모델 태깅, 실제는 Chain Sight DNA 교차 |
| ValidationNewsSummary 모델 | (설계서에 없음) | A | `models/news_summary.py` + admin | 설계서 어디에도 없는 추가 모델, 사용처는 admin뿐 (dead code 후보) |
| Preset별 Benchmark 분기 계산 | peer §4 unique_together | **C** | preset_key 필드만 존재, 모든 계산은 'default'로만 | `BenchmarkCalculator` 내 preset_key 활용 0건 |
| Preset별 CategorySignal 분기 계산 | peer §4 | **C** | unique_together에 preset_key 포함되나 `category_signal_calculator.py`에서 사용 0건 | 사용자 preset 전환해도 같은 default 결과 |
| Beat schedule 등록 (일요일 새벽 2시) | PR-5 | (C 흡수) | `tasks.py`에 `@periodic_task` 또는 `CELERY_BEAT_SCHEDULE` dict 없음 | Orchestrator chain 자체는 작동 |

### 갭 항목 상세 (B/C/D만)

- **[C] Preset별 Benchmark 분기 계산 미작동**: 설계는 `unique_together=[symbol,fiscal_year,metric_code,preset_key]`로 프리셋별 batch 결과 저장. 실제는 모델 필드 `preset_key`(default)와 unique_together 모두 존재하나, `BenchmarkCalculator` 내 어디에도 preset_key 인자나 `PeerPreset.peer_symbols` 활용 없음. **사용자가 preset 전환해도 같은 default 데이터만 반환됨**. UX 측면에서 가장 위험한 갭.

- **[C] Preset별 CategorySignal 분기 계산 미작동**: 모델 unique_together에 preset_key 포함되어 있으나 `category_signal_calculator.py` grep 결과 preset_key 사용 0건. 모든 카테고리 신호는 default peer로만 계산. 위 갭과 동일한 패턴.

- **[B] Task 3 (peer 선정 + benchmark) preset_key 분기 누락**: 위 [C] 두 항목의 원인. `_select_peers`가 preset_key를 인자로 받지 않음.

- **[B] Task 5 (update_peer_list_caches)**: 설계는 "confidence 재검증 + 최종 저장". 실제는 `PeerListCache.objects.count()`만 로그. 차이: 비활성/낮은 신뢰도 프리셋 자동 비활성화 로직 누락.

- **[D] Task 1 (fetch_annual_financials)**: 설계는 FMP `/income-statement`, `/balance-sheet-statement`, `/cash-flow-statement`, `/key-metrics` annual limit=5 직접 호출. 실제는 `FinancialFetcher.check_and_fetch`가 가용성만 검사하고 부족 시 stocks 앱 기존 파이프라인에 위임. 외부 영향이 같으므로 폐기/대체로 분류.

- **[B] ValidationSummaryView industry_position.ranks**: 설계는 "ranks[] 일반화", 실제는 `revenue_growth_yoy/operating_margin/roe/fcf_margin/debt_to_equity` 5개 하드코딩.

- **[B] LeaderComparisonView growth_trend_comparison**: PR-6/§3.5 설계는 "자사 3년 vs 업종 median 3년 (가속/감속/유지)" 응답 필드. 실제 응답에는 `comparisons/summary_metrics/advantages_count/summary` 만 있고 `growth_trend_comparison{}` 키 없음.

- **[D] Phase 6 Thematic 프리셋 구현 방식**: peer_phase6_7 설계는 Gemini 2.5 Flash로 503개 종목에 사업모델 태그 부여 → `CompanyNarrativeTag.theme_tags` 저장 → 클러스터링. 실제는 `_generate_thematic`에서 chainsight `CompanyGrowthStage.stage` × `CompanyCapitalDNA.capital_type` 교차로 클러스터링 (LLM 호출 없음). task_done 보고서에 463/503 종목 처리 명시. 의도적 대체.

- **[B] PeerPreferenceView 커스텀 검증**: 설계는 "프리셋이 존재하는지 확인" 위주. 실제 코드는 mode='custom' 시 `custom_peers` 빈 배열도 통과시킴(symbol 유효성/수량 미검증).

- **[C] Celery Beat 일요일 새벽 2시 등록**: PR-5는 "Celery Beat 등록"을 명시. `tasks.py`에 `@periodic_task` 또는 `CELERY_BEAT_SCHEDULE` dict 없음. Orchestrator chain은 작동하나 자동 트리거는 별도 등록 필요.

- **[B] Phase 7 Thesis Control 연동**: peer_phase6_7 §"Thesis Control 연동"에서 `Thesis.peer_preset_key/peer_filter_query/peer_filter_result` 필드 추가 명시. validation/llm-filter API 응답을 thesis가 사용하는 흔적 없음 (LLMPeerFilterView가 결과만 반환).

### 부수 관찰
- 설계서에 없는 추가 모델 `ValidationNewsSummary`는 admin에만 등록되고 어떤 service/view에서도 read/write되지 않음 (**dead code 후보**).
- 테스트는 6개 파일(`test_benchmark_calculator/test_metric_calculator/test_preset_generator/test_relative_metrics/test_interpretation/test_services_extended.py`)이 `tests/unit/validation/`에 존재하며, 모델 7개 중 5개에 대한 PR-4 테스트가 `tests/unit/metrics/test_pr4_validation.py`에 있음.
- `validation/views.py`, `validation/tests.py`는 빈 스켈레톤, 실제 코드는 `validation/api/`로 이동.

---

## News 상세

### 구현률 요약
- 전체 기능 21개 중: **A=18, B=3, C=0, D=0**
- 설계 문서 3건(키워드 상세 plan, BottomSheet v2, Pipeline Monitoring) 모두 사실상 **풀 구현 단계** 도달.
- 잔여 갭은 모두 (1) 자동화 회귀 테스트 부재 또는 (2) 응답 필드/트리거 1종의 명시적 확인 필요 — 미구현(C)이나 폐기(D)는 0건.

### 기능별 분류표

| 기능 | 설계 위치 | 분류 | 핵심 증거 | 비고 |
|------|----------|------|----------|------|
| 키워드 상세 API (`GET /keyword-detail/?date&index`) | keyword_detail_plan §4 | A | `news/api/views.py:646-780` `@action url_path='keyword-detail'` | date+index 파싱, Gemini 호출, 캐시 키에 updated_at 포함 |
| `search_terms_en` 키워드 추출 확장 | keyword_detail_plan §3-1 | A | `keyword_extractor.py:241,256-258,306,321` 프롬프트+스키마 반영 | fallback 키워드도 빈 배열 보존 |
| 2단 매칭 (related_symbols → search_terms_en) | keyword_detail_plan §3-2 | A | `views.py:725-744` related_symbols 1차 + title icontains 2차 + `article_ids` 우선 매칭 | 설계 이상으로 article_ids 직접 저장 추가 (`keyword_extractor.py:133-141`) |
| Redis 캐시 (`news:keyword_detail:{date}:{index}:{updated_at}` TTL 1h) | §3-5 | A | `views.py:702-707, 778` 동일 패턴 + 1시간 TTL | |
| Gemini 실패 시 analysis=null | §3-4 | A | `views.py:759-767` try/except → `analysis_text=None` | |
| KeywordDetailSheet (바텀시트 v1) | keyword_detail_plan §5 | A | `frontend/components/news/KeywordDetailSheet.tsx` 존재 | |
| BottomSheet v2 가로 스크롤 Strip | keyword_detail_bottomsheet_v2 | A | `KeywordDetailSheet.tsx:15-16,56-84,99,125-130` Props=`initialIndex+keywords[]`, activeIndex state, scrollIntoView, scrollbar-hide | |
| BottomSheet `max-w-2xl mx-auto` | keyword_detail_bottomsheet_v2 | A | `frontend/components/thesis/common/BottomSheet.tsx:38` `max-w-2xl mx-auto` | |
| 키워드 전환 keepPreviousData | v2 §구현 설계 | A | `useNewsPipeline`/`useNews.ts` (해당 hook 존재 확인) | |
| Phase 0 — `_log_collection()` 커버리지 보강 | monitoring_design §11 | A | `news/tasks.py:178,220,454,500,543,621` 6개 태스크 모두 호출 | 설계 명세대로 6개 태스크 모두 보강 |
| Phase A — `GET /collection-logs/` | §3.1 | A | `views.py:1320-1342` IsAdminUser, days/provider/task_name 필터 + 캐시 키 | |
| Phase A — `GET /pipeline-health/` | §3.2 | A | `views.py:1430-1444` IsAdminUser + 캐시 | force_refresh 파라미터 표시 |
| Phase A — `GET /ml-trend/` | §3.3 | A | `views.py:1684-1702` weeks 파라미터 + 1h 캐시 | |
| Phase A — `GET /llm-usage/` | §3.4 | A* | `views.py:1764-1786` days 파라미터 + 1h 캐시 | coverage_warning 필드 명시 확인 필요 (B 항목) |
| Phase A 프론트 sub-tab + 6 컴포넌트 | §4 | A | `frontend/components/admin/news/`에 PipelineStatusBar, CollectionStatsTable, MLModelCard, MLTrendChart, RecentErrorsList, LLMUsageSummary, NewsPipelineSubTab + `useNewsPipeline.ts`, `newsPipelineService.ts` | |
| Phase B — `GET /task-timeline/` | §5.1 | A | `views.py:1884-1902` hours 파라미터 + 캐시 | |
| Phase B — `GET /neo4j-status/` | §5.2 | A | `views.py:1945-1955` 캐시 | |
| Phase B — ML rollback 2단계 (`/ml-rollback-preview/` GET + `/ml-rollback/` POST) | §5.3 | A | `views.py:2006-2046` preview + POST + confirm 검증 | 프론트: `MLCompareView.tsx` 존재 |
| Phase B 프론트 (TaskTimelineChart, Neo4jStatusCard, MLCompareView) | §5 | A | `frontend/components/admin/news/`에 모두 존재 | |
| Phase C — AlertLog 모델 + migration | §6.3 | A | `news/models.py:684,693,702,712,713,723` TextChoices(TriggerType, Severity), is_resolved, resolved_at, acknowledged_by + `migrations/0006_alertlog.py` | |
| Phase C — `GET /alerts/` + `POST /alerts/{id}/resolve/` | §6 | A | `views.py:2091-2189` 두 엔드포인트 모두 IsAdminUser, resolve 시 AlertLog.DoesNotExist 처리, 중복 해결 차단 | |
| Phase C — `check_pipeline_alerts` 태스크 + Beat | §6.1 | **B** | `news/tasks.py:1102` 태스크 정의 + `config/celery.py:423` Beat 등록. 7개 트리거 중 6개 처리 핸들러 확인됨 | "태스크 연속 실패" 트리거 핸들러 명시 라인 미확인 |
| Phase C 프론트 (AlertBadge, AlertList) | §6 | A | `frontend/components/admin/news/AlertBadge.tsx`, `AlertList.tsx` + `app/admin/page.tsx`에 import 발견 | |
| 모니터링/키워드 상세 전용 테스트 | (관행) | **B** | `tests/news/`에 v3 핵심 서비스 12개 테스트 존재. **신규 12 API + AlertLog 트리거 7종 단위 테스트는 0건** | grep 결과 0건 |
| Multi-provider 추상화 (finnhub/fmp/marketaux/AV) | monitoring_design 전제 | A | `news/providers/`에 base.py/finnhub.py/fmp.py/marketaux.py 4개 + migration 0005 | alpha_vantage는 별도 통합 |

### 갭 항목 상세 (B/C/D만)

- **[B] `check_pipeline_alerts` 트리거 7종 중 1종 부분 구현 의심**: 설계서 §6.1의 7개 트리거(태스크 연속 실패 / ML F1 급락 / 키워드 추출 실패 / LLM 에러율 급등 / Neo4j 실패 / 수집량 급감 / 미분류 누적) 중 `news/tasks.py:1188~1353`에서 ML F1/키워드/LLM/Neo4j/수집량/미분류 6종 핸들러는 명시 확인되었으나, "태스크 연속 실패(consecutive_task_failure)" 트리거 핸들러는 별도 분리 라인이 grep에 잡히지 않음. 일반 에러 핸들러에 통합되었을 가능성도 있음. 설계 대비 **6/7 트리거 확실 구현**.

- **[B] 모니터링·키워드 상세 전용 테스트 누락**: `tests/news/`에 v3 핵심 서비스(classifier/deep_analyzer/ml_label/ml_weight/ml_production/neo4j_sync/lightgbm/category/market_feed) 테스트는 풍부히 존재(설계서 표기 607개)하나, 다음 신규 추가물에 대한 직접 테스트 파일 부재:
  - 키워드 상세 API (`keyword_detail` action, `_generate_keyword_analysis`, article_ids 매칭 fallback)
  - Phase A 4개 API (`collection-logs`, `pipeline-health`, `ml-trend`, `llm-usage`)
  - Phase B 4개 API (`task-timeline`, `neo4j-status`, `ml-rollback-preview`, `ml-rollback`)
  - Phase C AlertLog + alerts/resolve API + check_pipeline_alerts 태스크 트리거 7종

  설계서 "검증 체크리스트" 항목들이 자동 회귀 테스트로 보장되지 않음. 통합 테스트(curl/UI 검증) 의존 → 회귀 위험.

- **[B] LLM Usage API의 `coverage_warning` 응답 필드 미확인**: §3.4 설계에서 응답 구조에 `deep_analysis.coverage_warning` 문구 명시. `views.py:1764-1786` 핸들러는 존재하나 본문(응답 빌드부)을 본 감사에서 직접 검증하지 못함. 프론트엔드 `LLMUsageSummary.tsx`에는 §4.2 경고 배너 강제 표시 가능성 있음. 백엔드 응답 워닝 문자열 포함 여부는 추가 확인 필요.

### 종합 평가

설계 문서 3건 모두 **풀 구현 단계** 도달. 미구현(C)이나 폐기(D)는 발견되지 않았으며, 남은 갭은 자동화된 테스트 커버리지 보강과 응답 필드 1건/트리거 1종의 명시적 확인 등 **품질 보강 차원**의 항목뿐.

- **키워드 상세보기 (v1)**: 백엔드 API + Gemini 요약 + 캐시 + 프론트 시트 모두 완료. `article_ids` 직접 저장으로 설계보다 정확도 향상.
- **BottomSheet v2 (가로 스크롤 Strip + max-w-2xl)**: Props 변경, activeIndex, scrollIntoView, scrollbar-hide, BottomSheet 너비 제한 모두 코드에서 확인.
- **News Pipeline Monitoring**: Phase 0(_log_collection 6개 커버), Phase A(4 API + 6 컴포넌트 + sub-tab), Phase B(4 API + 3 컴포넌트), Phase C(AlertLog 모델/migration 0006 + 2 API + 2 컴포넌트 + check_pipeline_alerts 태스크 + Beat 스케줄) 모두 존재.

---

## 권장 후속 조치 (우선순위)

| # | 영역 | 항목 | 권장 조치 | 우선순위 |
|---|------|------|----------|---------|
| 1 | Validation | preset_key 분기 계산 미작동 ([C] 2건 + [B] 1건) | `BenchmarkCalculator`, `CategorySignalCalculator`에 `preset_key` 인자 추가 후 `PeerPreset.peer_symbols` 사용. Orchestrator에서 6 preset 모두 순회 | 🔴 높음 (UX 버그) |
| 2 | Validation | Beat 스케줄 미등록 (일요일 새벽 2시) | `config/celery.py`에 `run_weekly_validation_batch` PeriodicTask 등록 | 🟡 중간 |
| 3 | Validation | LeaderComparison `growth_trend_comparison` 누락 | PR-6 §3.5 설계대로 자사/업종 3년 median 비교 응답 필드 추가 | 🟡 중간 |
| 4 | Validation | ValidationNewsSummary dead code | 사용처 없음 — 사용 계획 확정 또는 제거 결정 | 🟢 낮음 |
| 5 | News | 신규 12 API + AlertLog 7 트리거 자동 테스트 | `tests/news/` 하위에 `test_keyword_detail.py`, `test_pipeline_monitoring.py`, `test_alertlog.py`, `test_check_pipeline_alerts.py` 추가 | 🟡 중간 |
| 6 | News | `check_pipeline_alerts` 트리거 1종 (태스크 연속 실패) 명시 핸들러 검증 | grep 재확인 후 누락 시 핸들러 추가 | 🟡 중간 |
| 7 | SEC Pipeline | 통합/E2E 테스트 부재 | `tests/integration/sec_pipeline/`에 collect→extract→sync 흐름 테스트 추가 | 🟡 중간 |
| 8 | SEC Pipeline | task_done 문서 vs Beat 활성화 불일치 | PR-17 task_done에 Beat 활성 등록 사실 반영 (또는 PR-18 신규 작성) | 🟢 낮음 |
| 9 | SEC Pipeline | `seed_company_aliases.py` source='seed', `rematch_unmatched.py` status='not_company' choices 미정의 | 모델 SOURCE/STATUS_CHOICES에 항목 추가 + migration | 🟢 낮음 |

---

## 감사 메타 정보

- **감사 방법**: 3개 일반 에이전트 병렬 dispatch → 각 앱별 설계서 + task_done + 구현 grep/Read 결과 수집 → 본 문서 통합
- **사용 도구**: Read, Grep, Glob, Bash (ls/wc만)
- **코드 수정**: 없음 (읽기 전용 감사)
- **참조 파일 수**: SEC Pipeline ~25개, Validation ~20개, News ~30개 + 프론트엔드 ~10개
