# SEC Pipeline + Validation + News 설계 갭 감사

> **감사 일자**: 2026-06-02 (야간 자동화)
> **유형**: 읽기 전용 (코드 수정 없음)
> **방법**: 설계 문서(`docs/`) ↔ 실제 구현(`services/`) 대조 + `task_done/` 완료 보고서 cross-reference
> **분류 기준**: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 0. 사전 발견 사항 — 디렉토리 리모델링 (중요)

감사 착수 시 **3개 앱 모두 top-level → `services/` 하위로 이동**된 것을 확인했다 (서비스 리모델링, `docs/architecture/data_architecture_remodeling_0326/`).

| 과거 경로 (구버전) | 현재 경로 (실제 구현) | top-level 잔존물 |
|---|---|---|
| `sec_pipeline/` | `services/sec_pipeline/` | `.pyc`만 남음 (git 미추적) |
| `validation/` | `services/validation/` | `.pyc`만 남음 (git 미추적) |
| `news/` (단독 앱 없었음) | `services/news/` | 디스크에 없음 |

- top-level `sec_pipeline/`, `validation/` 디렉토리에는 `__pycache__`만 잔존 → **삭제 대상 (정리 부채)**.
- 공유 메트릭 모델은 `packages/shared/metrics/`로 분리됨 (`MetricDefinition`, `CompanyMetricSnapshot`, `PeerListCache` 등).
- News의 일부 기능은 `apps/market_pulse/`에도 존재(`news_aggregator.py`, `anomaly/news_pairing.py`)하나, 이는 **Market Pulse 전용 별도 뉴스**로 본 감사 대상(`services/news/`)과 무관.

---

## 1. 앱별 요약 (구현률)

| 앱 | 구현 위치 | 구현률 | A | B | C | D | 핵심 갭 |
|---|---|---|---|---|---|---|---|
| **SEC Pipeline** | `services/sec_pipeline/` | **~97%** | 36 | 1 | 0 | 1 | Celery Beat 스케줄 비활성(주석 처리) |
| **Validation** | `services/validation/` (+`packages/shared/metrics/`) | **~88%** | 28 | 3 | 1 | 0 | `peer_info.confidence` 필드값 혼동(계약 위반) |
| **News** | `services/news/` | **~93%** | 90+ | 1 | 0 | 0 | Phase 3 심층분석 LLM 토큰 추적 미포함(설계상 Phase B 범위) |

> 종합: 3개 앱 모두 **설계 핵심 기능은 완성**. 미구현(C)은 거의 없고, 대부분 갭은 **운영 설정(Beat 활성화) / API 계약-구현 필드 불일치 / 설계 자체가 범위를 제한한 항목**에 집중.

---

## 2. SEC Pipeline 상세

### 2.1 구현률: ~97% (37개 컴포넌트 중 36 완전 구현)

설계 문서 17개 PR(`docs/sec_pipeline/task_done/sec_pr_1~17`) + base/pr_detail 설계서 + 결정 문서(001) 대비, **17개 PR 전부 핵심 기능 구현 확인**.

### 2.2 PR별 분류표

| PR | 항목 | 설계 출처 | 분류 | 근거 |
|---|---|---|---|---|
| PR-1 | 8개 Django 모델 | sec_pr_1_models.md | **A** | `models.py` — FK·unique 제약 일치 |
| PR-2 | SEC EDGAR Collector | sec_pr_2_collector.md | **A** | `collector.py` — 3개 추출 메서드 |
| PR-2 | Section Validators (3단) | sec_pr_2 | **A** | `validators.py` |
| PR-3 | Normalizer + 50+ 키워드 | sec_pr_3_track_a_extractor.md | **A** | `normalizer.py` |
| PR-3 | Gemini Extractor | sec_pr_3 | **A** | `extractor.py` — 2.5-flash, temp 0.1, lazy init |
| PR-3 | Track A Validator | sec_pr_3 | **A** | `validator_track_a.py` — generic term 필터 |
| PR-3 | Prompts (버전 추적) | sec_pr_3 | **A** | `prompts.py` — PROMPT_VERSION |
| PR-4 | Exceptions (4종) | sec_pr_4_celery_tasks.md | **A** | `exceptions.py` — retry 정책 |
| PR-4 | Celery Tasks | sec_pr_4 | **A** | `tasks.py` — collect_and_extract 등 |
| PR-5 | Gold Set (10종목) | sec_pr_5_gold_set.md | **A** | `fixtures/gold_set.json` + `evaluate_gold_set` |
| PR-6 | 배치 실행 (15종목) | sec_pr_6_phase1_batch.md | **A** | 14/15 성공(93.3%) 보고와 모델 일치 |
| PR-7 | TickerMatcher (3단) | sec_pr_7_ticker_matcher.md | **A** | `ticker_matcher.py` — rapidfuzz |
| PR-8 | Admin Queue UI + Signal | sec_pr_8_admin_signal.md | **A** | `admin.py` + `signals.py` |
| PR-9 | Neo4j Sync (dirty flag) | sec_pr_9_neo4j_sync.md | **A** | `tasks.sync_dirty_to_neo4j` DELETE+CREATE |
| PR-10 | Merger 로직 | sec_pr_10_merger.md | **A** | `merger.py` — RELATIONSHIP_SPECIFICITY, DQS |
| PR-11~13 | Track B (사업모델) | sec_pr_11_12_13_phase2.md | **A** | `keywords_track_b.py`, `validator_track_b.py`, 서비스 게이트 |
| PR-14 | 품질 대시보드 (7 checks) | sec_pr_14_dashboard.md | **A** | `quality_checks.py` + `views.py` + 템플릿 존재 |
| PR-15 | On-Demand API | sec_pr_15_on_demand.md | **A** | `on_demand.py` + FilingDataView (200/202) |
| PR-16 | Intelligence Report | sec_pr_16_intelligence.md | **A** | `intelligence.py` — 5차원 + Gemini |
| PR-17 | E2E 배치 워크플로우 | sec_pr_17_e2e.md | **A** | `tasks.run_batch_and_report` (chord) |

### 2.3 주목할 갭/불일치

1. **[B] Celery Beat 스케줄 비활성** — `tasks.py` 말미에 `sync-sec-dirty-neo4j`(`*/5분`), `check-new-filings`(매월 1일) Beat 설정이 **주석 처리**됨. 태스크 로직 자체는 완성. **단, CLAUDE.md 버그 #28(DatabaseScheduler 사용 시 config dict 무시)에 비추어, 활성화 시 dict가 아닌 `PeriodicTask.objects.create()`로 DB 등록 필요** — 주석을 그대로 해제하면 동작하지 않을 위험.
2. **[D] FMP → SEC EDGAR 메타데이터 대체** — `decisions/001_fmp_vs_sec_edgar_metadata.md`에 문서화된 의도적 변경. FMP Starter 플랜에 `sec-filings` 엔드포인트 부재(404/403) → SEC EDGAR submissions API(무료)로 대체. **설계보다 개선된 결과, 정상 처리.**
3. **[Enhancement] 설계 초과 구현** — `GENERIC_COMPANY_TERMS`(45+ 용어, `validator_track_a.py:26-65`), 추가 management command 3종(`rematch_unmatched`, `reprocess_unmatched_queue`, `seed_company_aliases`). 설계 명세를 초과.

### 2.4 task_done ↔ 구현 cross-reference
- `sec_pr_6`(배치 93.3%), `sec_pr_14`(7 checks), `sec_pr_16`(5차원 intelligence) **모두 보고서 주장과 실제 코드 일치**. 허위 완료 보고 없음.

---

## 3. Validation 상세

### 3.1 구현률: ~88% (Phase 1~7 전부 구현, 단 계약 불일치 3건)

설계서(`validation_design.md`, `validation_peer_system.md`, `validation_peer_phase6_7.md`) + contracts(`validation-api.yaml`) + task_done(phase6/7) 대조.

### 3.2 기능 영역별 분류표

| 영역 | 항목 | 설계 출처 | 분류 | 근거 |
|---|---|---|---|---|
| 모델 | MetricDefinition (34지표) | design §7.1 | **A** | `packages/shared/metrics/models/metric_definition.py` |
| 모델 | CompanyMetricSnapshot (value_status) | design §7.2 | **A** | `metric_snapshot.py:44-61` — 5개 status |
| 모델 | CompanyBenchmarkDelta (preset_key) | design §7.3 | **A** | `benchmark_delta.py:73-80` — unique 제약 일치 |
| 모델 | CategorySignal (green/yellow/red/gray) | design §3.1 | **A** | `category_score.py:30-50` |
| 모델 | PeerListCache (basis/bucket/tier) | design §7.4 | **A** | `packages/shared/metrics/models/benchmark.py` |
| 모델 | PeerPreset (6 프리셋) | peer_system §2 | **A** | `peer_preset.py:5-46` |
| 모델 | UserPeerPreference | peer_system §3 | **A** | `peer_preset.py:48-79` |
| 배치 | Task 1~6 + Task 3.5 | design §6.1 | **A** | `tasks.py:23-150` |
| 배치 | Orchestrator chain / Beat | design §6.2 | **B** | chain 인라인 존재, **Beat 스케줄 미확인** |
| API | GET /summary/ | design §5.1 + yaml | **B** | `api/views.py:63-221` — **peer_info.confidence 필드값 불일치 (아래 갭#1)** |
| API | GET /metrics/?category | design §5.2 | **A** | `api/views.py:223-401` — 5년 history |
| API | GET /leader-comparison/ | design §5.1 | **B** | `api/views.py:404-528` — **growth_trend_comparison 세부 미확인** |
| API | GET /presets/ | peer_system §6 | **A** | `api/views.py:531-569` — confidence_label "높음/보통/낮음" 정상(`views.py:553-554`) |
| API | POST/DELETE /peer-preference/ | peer_system §6 | **A** | `api/views.py:572-619` |
| API | POST /llm-filter/ | phase6_7 P7 | **A** | `api/views.py:622-692` + `llm_peer_filter.py` |
| 해석 | summary/metric/leader text | design §3.1/3.3/3.5 | **A** | `interpretation.py` |
| 프리셋 | Phase 1~5 (default~custom) | peer_system §3 | **A** | `preset_generator.py`, `custom_benchmark_engine.py` |
| 프리셋 | Phase 6 thematic (DNA 교차) | task_done/peer_phase6 | **A** | `preset_generator.py:62` `_generate_thematic()` (463/503) |
| 프리셋 | Phase 7 LLM 필터 | task_done/peer_phase7 | **A** | `llm_peer_filter.py:56-91` parse + execute |
| 검증 | value_status 판정 세부 로직 | design §7.2 | **C** | `metric_calculator.py` 로직 미확인 (아래 갭#3) |

### 3.3 주목할 갭/불일치

1. **[B·계약 위반] `peer_info.confidence` 필드값 혼동 (직접 검증 확정)** — `contracts/validation-api.yaml`은 `peer_info.confidence`를 신뢰도 레이블("높음/보통/낮음")로 정의하나, `api/views.py:131`에서 `"confidence": peer_cache.benchmark_basis`로 **basis 문자열("industry_size" 등)을 할당**. 프론트엔드가 신뢰도 레이블을 기대하면 잘못된 값을 받음. 같은 파일 presets 엔드포인트(`views.py:553-554`)는 confidence_label을 올바르게 분기하므로 **summary 엔드포인트만의 국소 결함**. → **수정 권장: 계약(yaml)을 진실 소스로 두고 구현을 맞추거나, 별도 필드로 분리.**
2. **[C] `value_status` 판정 세부 로직 검증 불가** — 설계 §7.2의 규칙(`cash_runway_years`는 흑자기업 시 `not_applicable`, `interest_coverage` 극단 변동 시 `unstable`)이 `metric_calculator.py`에 실제 구현됐는지 본 감사에서 확인하지 못함. Task 2(`tasks.py:40-54`)는 MetricCalculator 호출만 노출. **후속 검증 필요 항목.**
3. **[B] 외부 데이터 의존 필터** — LLM 필터의 `foreign_revenue_pct`, `rd_to_revenue`는 `CompanySensitivityProfile`/`CapitalDNA`(Chain Sight) 테이블 의존. task_done에서도 "Chain Sight 완성 후"로 명시 → 데이터 충전 전까지 해당 필터 실질 미작동.

### 3.4 contracts ↔ 구현 대조 요약

| 엔드포인트 | 일치도 | 비고 |
|---|---|---|
| GET /summary/ | 95% | peer_info.confidence 필드값 혼동 |
| GET /metrics/ | 100% | history[] + peer band 완성 |
| GET /leader-comparison/ | 95% | growth_trend_comparison 세부 미확인 |
| GET /presets/ | 100% | confidence_label 정상 |
| POST /peer-preference/ | 100% | |
| POST /llm-filter/ | 100% | (단 외부 데이터 의존 필터 제외) |

### 3.5 task_done ↔ 구현 cross-reference
- phase6(thematic), phase7(LLM filter) **보고서 주장과 코드 일치**. 단 phase7의 일부 필터는 외부 테이블 의존성으로 실질 동작 제한(보고서에도 명시됨).

---

## 4. News 상세

### 4.1 구현률: ~93% (Phase 1~6 + 모니터링 Phase A/B/C 전부 구현, 미구현 0)

설계서(`docs/news/plan/` 3건 + `docs/news_intelligence_plan/` phase1~6 _planned/_completed) 대조. **`_planned` 약속 → `_completed` 주장 → 실제 코드 3중 대조 결과 일치.**

### 4.2 Phase별 분류표

| Phase | 항목 | 분류 | 근거 |
|---|---|---|---|
| 1 | 규칙 엔진 A/B/C | **A** | `services/news_classifier.py:178/255/264` |
| 1 | 모델 필드 (importance_score, rule_*, llm_analysis) | **A** | `models.py:104-135` |
| 1 | Keyword-Sector 매핑 + 퍼센타일 선별 | **A** | `keyword_sector_map.py`, `select_for_analysis():385` |
| 2a | LLM 심층 분석 (Gemini) | **A** | `news_deep_analyzer.py` + `analyze_news_deep` task:543 |
| 2b | ML Label 수집 | **A** | `ml_label_collector.py:93` + `collect_ml_labels`:591 |
| 3 | Neo4j 동기화 + 이벤트 API | **A** | `news_neo4j_sync.py` + `news_events` views |
| 4 | ML Weight Optimizer + Safety Gate 3단 + Shadow Mode | **A** | `ml_weight_optimizer.py:105` (61 테스트) |
| 5 | ML Production Manager (auto deploy/rollback/주간리포트) | **A** | `ml_production_manager.py:28` (56 테스트) |
| 6 | LightGBM (학습/A-B/전환조건/파이프라인) | **A** | `ml_weight_optimizer.py:1004/1122/1189/1263` (41 테스트) |
| 모니터링 A | collection_logs / pipeline_health / ml_trend / llm_usage | **A** | `api/views.py:1411/1537/1911/2002` |
| 모니터링 B | task_timeline / neo4j_status / ml_rollback(_preview) | **A** | `api/views.py:2134/2202/2276/2319` |
| 모니터링 C | AlertLog 모델 + Alert API | **A** | `models.py:553` + migration 0006 |
| Keyword Detail | keyword_detail API (date+index, Redis 캐시) | **A** | `api/views.py:677-811` |
| Phase 0 | `_log_collection()` 6개 태스크 호출 | **A** | 호출 10곳 확인(179/230/487/543/591/674/1015/1113/1148), 정의 1461 |

### 4.3 주목할 갭/불일치

1. **[B] Phase 3 심층분석 LLM 토큰 추적 미포함** — `llm_usage` API(`api/views.py:2002`)는 **키워드 추출 토큰만 집계**하고, NewsDeepAnalyzer(전체 LLM 비용의 대부분)의 토큰은 미포함. 코드 자체가 `coverage_warning`으로 명시. **이는 설계상 Phase A 범위 제한(Phase B 예정)으로, 결함이라기보다 미완성 로드맵 항목.** `news_deep_analyzer.py`에 토큰 수 저장 로직 부재.
2. **[보정·A] `_log_collection()` 커버리지** — 1차 에이전트 분석은 "미검증(B)"으로 분류했으나, **직접 검증 결과 호출 10곳 확인**되어 6개 핵심 태스크 모두 로깅 중. → **A로 보정.** pipeline_health API 통계 신뢰성 확보됨.
3. **[A] Keyword Detail article_ids 직접 저장** — 설계의 2단 매칭(symbol → search_terms_en title) fallback 대신, `article_ids` 직접 저장 후 조회로 최적화 구현(`views.py:740-756`). 레거시 호환 fallback도 유지. 설계 의도 충족 + 성능 개선.

### 4.4 _planned ↔ _completed ↔ 코드 3중 대조

| 문서 | _planned 약속 | 실제 코드 | 결과 |
|---|---|---|---|
| phase4 | NewsEvent 타임라인 FE | `NewsEventTimeline.tsx` | ✅ 일치 |
| phase5 | Engine C ML 가중치 자동 통합 | `_load_deployed_weights()` | ✅ 일치 |
| phase6 | LightGBM 3-tier 조건 체크 | `check_lightgbm_readiness()` | ✅ 일치 |
| phase6 | LightGBM 파이프라인 | `run_lightgbm_pipeline()` | ✅ 일치 |

- **프론트엔드 12개 컴포넌트** (PipelineStatusBar, MLModelCard, MLTrendChart, TaskTimelineChart, Neo4jStatusCard, MLCompareView, AlertBadge 등) 전부 존재.
- **테스트 587개 통과**(Phase 1~6), **마이그레이션 6개**(0001~0006) 완료.

---

## 5. 종합 결론 및 후속 권장

### 5.1 전체 평가
3개 앱 모두 **설계 핵심 기능 완성도 88~97%**로, 미구현(C) 항목은 사실상 없음. 잔여 갭은 (1) 운영 설정 미활성, (2) API 계약-구현 필드 불일치, (3) 설계가 스스로 범위를 제한한 항목에 집중.

### 5.2 우선순위별 후속 조치 (감사 권고 — 본 보고서는 코드 미수정)

| 우선순위 | 앱 | 항목 | 근거 |
|---|---|---|---|
| 🔴 P1 | Validation | `peer_info.confidence` 필드값 계약 위반 수정 | `api/views.py:131` — FE가 잘못된 값 수신 |
| 🟡 P2 | Validation | `value_status` 판정 로직(`metric_calculator.py`) 실재 검증 | design §7.2 규칙 구현 여부 미확인 |
| 🟡 P2 | SEC | Celery Beat 활성화 시 버그 #28(DatabaseScheduler) 회피 — `PeriodicTask.objects.create()` 사용 | `tasks.py` 주석 처리 + CLAUDE.md #28 |
| 🟢 P3 | 공통 | top-level `sec_pipeline/`·`validation/` `.pyc` 잔존 디렉토리 정리 | 리모델링 후 정리 부채 |
| 🟢 P3 | News | Phase 3 심층분석 LLM 토큰 추적(Phase B) 구현 | `llm_usage` coverage_warning |
| 🟢 P3 | Validation | LLM 필터 외부 데이터(`foreign_revenue_pct` 등) 충전 — Chain Sight 의존 | task_done 명시 |

### 5.3 신뢰성 메모
- **허위 완료 보고 없음**: SEC 16개 + Validation 2개 + News phase별 task_done 보고서 주장이 실제 코드와 대체로 일치.
- 본 감사에서 **미확인(C)으로 남긴 항목**(Validation `value_status` 로직, leader-comparison `growth_trend_comparison`)은 추측 분류를 피하고 후속 검증 대상으로 명시.
