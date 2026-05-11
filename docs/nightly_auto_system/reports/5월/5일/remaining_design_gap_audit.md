# SEC Pipeline + Validation + News 설계 갭 감사

> 작성일: 2026-05-06
> 범위: `sec_pipeline/`, `validation/`, `news/` 3개 앱
> 방법: 설계 문서(`docs/<app>/`) 와 실제 구현 디렉토리 cross-reference, `task_done/` 보고서 대조
> 모드: 읽기 전용 (코드 수정 없음)

---

## 앱별 요약 (구현률)

| 앱 | 설계 문서 | 구현률 (개략) | A 완전 | B 부분 | C 미구현 | D 폐기/대체 | 핵심 미구현 항목 |
|----|----------|--------------|--------|--------|----------|-------------|------------------|
| **sec_pipeline** | `docs/sec_pipeline/` (PR1~17 + decisions 1) | **~98%** | 17개 PR 전부 | 0 | 0 | 0 | Beat 활성화·RSS 대체(운영 항목) |
| **validation** | `docs/first_validation_system/` (BE-PR1~6 + Phase 6/7) | **~95%** | BE-PR3~6, Phase 6/7 | BE-PR1, BE-PR2 (모델 분산) | 0 | 0 | DB 모델 일부가 metrics 앱으로 이동 |
| **news** | `docs/news/plan/` (3개 문서) + CLAUDE.md "Pipeline v3" | **백엔드 100% / 프론트 0%** | 백엔드 13 API + v3 엔진 7개 | 0 | 프론트 대시보드 14개 + 키워드 BottomSheet 4개 | 0 | 모니터링 대시보드 FE, 키워드 시트 FE |

**전체 결론**:
- 백엔드 도메인 로직은 세 앱 모두 설계 충실도 95% 이상.
- **News 모니터링 대시보드 프론트엔드**가 가장 큰 미해결 갭 (백엔드 API 완비, FE 미착수).
- SEC Pipeline은 Celery Beat 등록과 SEC EDGAR RSS 대체만 운영 단계 작업으로 남음.

---

## SEC Pipeline 상세

### 설계 vs 구현 PR 매핑 (17개)

| PR | 설계 핵심 | 구현 위치 | 상태 |
|----|---------|---------|------|
| 1 | 8개 Django 모델 + migration | `sec_pipeline/models.py`, `migrations/0001_initial.py` | A |
| 2 | SEC EDGAR 수집기 + 섹션 추출 + 검증 | `collector.py` + `validators.py` | A |
| 3 | Track A: 키워드 필터 + Gemini 추출 | `normalizer.py` + `extractor.py` + `validator_track_a.py` | A |
| 4 | Celery tasks (6개) + 에러 핸들링 | `tasks.py` | A |
| 5 | Gold Set 라벨링 + 평가 | `fixtures/gold_set.json` + `management/commands/evaluate_gold_set.py` | A |
| 6 | S&P 500 배치 실행 | `tasks.py::run_batch_and_report` | A |
| 7 | 3단계 TickerMatcher + 큐 적재 | `ticker_matcher.py::TickerMatcher` | A |
| 8 | Admin 큐 뷰 + post_save signal | `admin.py` + `signals.py` | A |
| 9 | sync_dirty_to_neo4j (DELETE+CREATE) | `tasks.py::sync_dirty_to_neo4j` | A |
| 10 | 관계 병합 + DQS 계산 | `merger.py` + `management/commands/process_unmatched_queue.py` | A |
| 11~13 | Track B: BM 분류 + 서비스 레이어 | `keywords_track_b.py` + `extractor.extract_business_model` + `metrics/services/business_model_service.py` | A |
| 14 | Admin 대시보드 + 7개 품질 체크 | `quality_checks.py` + `views.py` + `urls.py` | A |
| 15 | On-demand 수집 + 신규 filing 감지 | `on_demand.py` + `views.py::FilingDataView` | A |
| 16 | Intelligence Report (5차원 분석) | `intelligence.py::PipelineIntelligenceReporter` + `models.py::PipelineIntelligenceReport` | A |
| 17 | E2E chord + Celery Beat | `tasks.py::run_batch_and_report` (chord 구현, Beat 미활성) | B |

### decisions/ 결정사항 준수
- **001 FMP vs SEC EDGAR 메타데이터**: SEC EDGAR submissions API 직접 호출, FMP 미사용 → **준수**.

### 갭 상세
| 항목 | 영향 | 권장 조치 |
|------|------|----------|
| Celery Beat 미활성 (PR-17) | `tasks.py`에 스케줄 명시는 있으나 코드/DB 등록 단계에서 주석 상태 → 자동 실행 안 됨 | `PeriodicTask.objects.create(...)` 로 DB 등록 (CLAUDE.md 버그 #28 패턴) |
| SEC RSS 대체 미적용 (PR-15) | `check_new_filings`가 S&P 500 심볼 반복 방식 → SEC EDGAR RSS 도입 시 호출 수 절감 가능 | 운영 단계 최적화 (현 방식도 동작) |
| neo4j_dirty 패턴 | `synced_to_neo4j` 필드 없이 dirty 플래그로 통일 | DECISIONS.md 패턴 준수 확인됨 |

### task_done 보고 vs 코드 일치
- `sec_pipeline_complete_summary.md` 와 PR 1~17 보고서가 모두 실제 파일/심볼 위치와 일치.
- 신뢰도 노출 경계(`for_api` 게이트, confidence_grade 등급화, `system_confidence` 내부 전용)가 Track B 서비스 레이어에서 구현 확인.

---

## Validation 상세

### 설계 vs 구현 PR/Phase 매핑

| PR/Phase | 설계 핵심 | 구현 위치 | 상태 |
|----------|---------|---------|------|
| BE-PR-1 | 9개 모델 + 마이그레이션 | `validation/models/`: peer_preset, category_score, metric_latest, benchmark_delta, news_summary (5개) + metrics 앱(MetricDefinition·CompanyMetricSnapshot·PeerMetricBenchmark) | B |
| BE-PR-2 | 34개 메트릭 + handling_mode 시드 | metrics 앱 시드 (validation 외부) | B |
| BE-PR-3 | FMP 수집 + 33개 지표 + value_status | `services/financial_fetcher.py`, `metric_calculator.py` | A |
| BE-PR-4 | Peer 선정 + Benchmark + size_bucket | `services/benchmark_calculator.py`, `relative_metrics.py` | A |
| BE-PR-5 | CategorySignal + 오케스트레이터 + special 산업 처리 | `services/category_signal_calculator.py`, `tasks.py` | A |
| BE-PR-6 | API 3개 (`/summary/`, `/metrics/`, `/leader-comparison/`) | `api/views.py` 6개 엔드포인트 (3개 추가) + `api/urls.py` | A+ |
| Phase 6 | 6종 프리셋 + Thematic 교차 조합 | `services/preset_generator.py::_generate_thematic` | A |
| Phase 7 | LLM 자연어 → 구조화 필터 → 실행 | `services/llm_peer_filter.py`, `api/views.py::LLMPeerFilterView` | A |

### 설계 키워드 매칭
| 설계 키워드 | 구현 위치 | 일치 |
|------------|---------|------|
| green≥65 / yellow≥35 / red<35 | `category_signal_calculator.py` | ✓ |
| value_status: normal/missing/not_applicable/unstable | `metric_calculator.py` | ✓ |
| handling_mode='special' → gray | `category_signal_calculator.py:125` | ✓ |
| Peer fallback: industry_size→industry→sector | `benchmark_calculator._select_peers` | ✓ |
| Confidence: high≥15 / medium 8~14 / low<8 / limited<4 | `benchmark_calculator._determine_confidence` | ✓ |
| size_bucket: mega/large/mid/small | `benchmark_calculator.assign_size_bucket` | ✓ |
| rev_growth_vs_industry | `relative_metrics.py` | ✓ |
| 6종 프리셋 (default/sector/size/quality/lifecycle/thematic) | `preset_generator.py` 6개 메서드 | ✓ |
| Gemini-2.5-Flash JSON 모드 필터 파싱 | `llm_peer_filter.parse_filter_with_llm` | ✓ |

### 추가 구현 (설계 초과)
- `/presets/`, `/peer-preference/`, `/llm-filter/` 3개 엔드포인트가 설계 명세 외 추가됨.
- API 단계에서 rule-based 해석 (`interpretation.py::generate_summary_text/metric_interpretation/leader_summary`) — Compute-on-Read 보강.

### 갭 상세
| 항목 | 영향 | 권장 조치 |
|------|------|----------|
| **DB 모델 분산** (BE-PR-1) | MetricDefinition·CompanyMetricSnapshot·PeerMetricBenchmark가 metrics 앱에 위치 → import 경로 복잡, 앱 경계 모호 | DECISIONS.md에 "metrics ↔ validation 분리 결정" 명문화 권장 |
| **시드 데이터 검증** (BE-PR-2) | 34개 메트릭 + handling_mode 실제 row 존재 여부 미확인 (metrics 앱 command 추정) | management command 위치/실행 주체 명시 필요 |
| **preset_key 명명** | 설계는 'thematic', 구현 GENERATION_METHOD_CHOICES는 'curated' (기능 일치하나 라벨 차이) | 라벨 통일 또는 매핑 주석 추가 |

### task_done 보고 vs 코드 일치
- `peer_phase6_thematic.md`: 463/503 종목, 2,282개 thematic 프리셋 → `preset_generator._generate_thematic` 동작 확인.
- `peer_phase7_llm_filter.md`: 12+ 필터 항목, parse + execute 분리 → `FILTER_PARSING_PROMPT` + `execute_peer_filter` 일치.

---

## News 상세

### 설계 문서 1: keyword_detail_bottomsheet_v2.md (FE UX)
| 설계 항목 | 구현 위치 | 상태 |
|----------|---------|------|
| BottomSheet `max-w-2xl` 데스크탑 너비 제한 | frontend/ (본 감사 범위 외) | C (FE) |
| 키워드 Strip 가로 스크롤 UI | frontend/ | C (FE) |
| `keepPreviousData` 캐시 패턴 | frontend/ | C (FE) |
| KeywordDetailSheet Props 구조 변경 | frontend/ | C (FE) |
| `scrollbar-hide` CSS | frontend/globals.css | C (FE) |

### 설계 문서 2: news_keyword_detail_plan.md (API + Gemini)
| 설계 항목 | 구현 위치 | 상태 |
|----------|---------|------|
| `GET /api/v1/news/keyword-detail/?date=&index=` | `news/api/views.py:640-775` | A |
| DailyNewsKeyword.keywords[] 확장 (`search_terms_en`) | `news/models.py:391-490` | A |
| Gemini 투자 관점 분석 호출 | `services/keyword_extractor.py::_generate_analysis` | A |
| 기사 검색 2단 매칭 (symbol → title) | `views.py::keyword_detail` | A |
| Redis 캐시 (1시간 TTL, `updated_at_epoch` 키 포함) | `views.py::keyword_detail` | A |
| Gemini 실패 처리 (분석 null) | `views.py::keyword_detail` | A |

### 설계 문서 3: news_pipeline_monitoring_design.md (관리자 대시보드)
| Phase | 설계 항목 | 백엔드 위치 | FE | 상태 |
|-------|---------|-----------|-----|------|
| 0 (선행) | 6개 태스크 `_log_collection()` 호출 보강 | `tasks.py` (확인 필요) | — | B (BE 부분) |
| A | `GET /collection-logs/` | `views.py:1314-1423` | 미구현 | A(BE) / C(FE) |
| A | `GET /pipeline-health/` (6 Phase) | `views.py:1424-1677` | 미구현 | A(BE) / C(FE) |
| A | `GET /ml-trend/` (F1 추이) | `views.py:1678-1757` | 미구현 | A(BE) / C(FE) |
| A | `GET /llm-usage/` (토큰 추적) | `views.py:1758-1877` | 미구현 | A(BE) / C(FE) |
| B | `GET /task-timeline/` (간트) | `views.py:1878-1938` | 미구현 | A(BE) / C(FE) |
| B | `GET /neo4j-status/` | `views.py:1939-1999` | 미구현 | A(BE) / C(FE) |
| B | `GET /ml-rollback-preview/` + `POST /ml-rollback/` | `views.py:2000-2084` | 미구현 | A(BE) / C(FE) |
| C | `GET/POST /alerts/` (+ resolve) | `views.py:2085-2184` | 미구현 | A(BE) / C(FE) |
| FE | NewsTab sub-tab (overview / pipeline) | — | 미구현 | C |
| FE | PipelineStatusBar (6 Phase 아이콘) | — | 미구현 | C |
| FE | CollectionStatsTable (provider 24h) | — | 미구현 | C |
| FE | MLModelCard + MLTrendChart (recharts) | — | 미구현 | C |
| FE | RecentErrorsList (아코디언) | — | 미구현 | C |
| FE | LLMUsageSummary (경고 배너) | — | 미구현 | C |

### News Intelligence Pipeline v3 핵심 기능
| 기능 | 서비스 | 파일 | 상태 |
|------|------|------|------|
| 규칙 엔진 (종목 매칭 + 섹터) | NewsClassifier | `services/news_classifier.py:89-336` | A |
| LLM 심층 분석 | NewsDeepAnalyzer | `services/news_deep_analyzer.py` | A |
| ML 학습 (Logistic Regression) | MLWeightOptimizer | `services/ml_weight_optimizer.py:544-693` | A |
| Neo4j 뉴스 이벤트 동기화 | NewsNeo4jSyncService | `services/news_neo4j_sync.py:77-536` | A |
| Shadow Mode (신 모델 검증) | MLWeightOptimizer | `services/ml_weight_optimizer.py:448-543` | A |
| Production Mode 배포 | MLWeightOptimizer + MLProductionManager | `services/ml_weight_optimizer.py:694-745` + `ml_production_manager.py` | A |
| LightGBM 고급 ML | MLWeightOptimizer | `services/ml_weight_optimizer.py:963-1145` | A |

### 갭 상세 (우선순위 순)
| 우선순위 | 항목 | 영향 | 권장 조치 |
|---------|------|------|----------|
| **P0** | 모니터링 대시보드 프론트엔드 0% | 관리자가 파이프라인 상태를 볼 UI 없음 (BE API 9개는 모두 응답 가능) | NewsTab sub-tab + 6개 컴포넌트 신규 구현 (FE-PR 단위 분할 권장) |
| P1 | Phase 0 `_log_collection()` 호출 보강 검증 | 6개 태스크에 일관된 로깅이 안 들어가 있으면 `pipeline-health` 데이터 신뢰도 하락 | `tasks.py` 6개 함수에서 로깅 호출 누락 여부 grep |
| P2 | 키워드 BottomSheet v2 FE | 사용자 키워드 상세 UX 미완 (API는 100% 제공 중) | FE 컴포넌트 구현 (`KeywordDetailSheet`, Strip, `scrollbar-hide`) |

---

## 종합 권장 후속 작업

1. **News 모니터링 대시보드 FE 구현** — 백엔드 9개 API 완비 상태이므로 즉시 착수 가능. `docs/news/plan/news_pipeline_monitoring_design.md` 에 FE 컴포넌트 명세가 이미 있음.
2. **News 키워드 BottomSheet v2 FE** — `keyword_detail_bottomsheet_v2.md` 명세 그대로 구현.
3. **SEC Pipeline Beat 활성화** — `tasks.py` 주석 해제 → DatabaseScheduler에 `PeriodicTask.objects.create(...)` 등록 (common-bugs.md #28 패턴).
4. **Validation 모델 분산 결정 명문화** — `DECISIONS.md`에 "metrics 앱 vs validation 앱 모델 경계" 결정 추가 + `validation/models/__init__.py` import 경로 주석 보강.
5. **Validation 시드 데이터 위치 명시** — 34개 메트릭 + handling_mode 시드 management command가 어느 앱에 있는지 명문화.

---

> 본 감사는 읽기 전용으로 진행되었으며, 코드 변경 없음. 후속 작업은 별도 PR/태스크로 분기 권장.
