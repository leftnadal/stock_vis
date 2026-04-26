# SEC Pipeline + Validation + News 설계 갭 감사

- **감사일**: 2026-04-27
- **모드**: 읽기 전용 (코드 수정 없음)
- **대상**: `sec_pipeline/`, `validation/`, `news/` 백엔드 3개 앱
- **기준**: `docs/sec_pipeline/`, `docs/first_validation_system/`, `docs/news/plan/` 설계 문서 + `task_done/` 완료 보고서 cross-reference

---

## 앱별 요약 (구현률)

| 앱 | 핵심 산출물 | 구현률(추정) | 분류 분포 | 종합 |
|----|------------|------------|----------|------|
| **SEC Pipeline** | 17 PR (Phase 1~3 Track A/B + E2E) | **약 95%** | A: 17 / B: 3개 영역 / C: 1 / D: 0 | 코어 로직 완전, **REST API 노출만 미흡** |
| **Validation** | BE-PR 1~6 + Phase 6/7 | **약 90~95%** | A: 6/6 PR + 7/7 Phase / B: 0 / C: 0 / D: Phase 6 알고리즘 1건 대체 | 설계 범위 일부 초과 구현, Theme_tags → GrowthStage×CapitalDNA 대체 |
| **News** | v3 파이프라인 + 모니터링 + Keyword Detail | **약 85%** | A: 백엔드 대부분 / B: 알림 (모델·로직 O, API X) / C: BottomSheet v2 프론트, 알림 조회 API / D: 0 | 백엔드 거의 완료, **알림 API + 프론트 BottomSheet v2 미구현** |

> **공통 패턴**: 백엔드 코어/모델/Celery 태스크는 설계대로 구축되어 있으나, "**REST API 노출 마무리**"와 "**관리자 가시성 UI**"가 일관된 갭으로 남아 있음.

---

## SEC Pipeline 상세

### 전체 구현률: 17/17 PR 코어 구현 (95%)

#### PR별 매트릭스

| PR | 제목 | 설계 산출물 | 구현 파일 | 상태 |
|----|------|-------------|----------|------|
| 1 | Models | 8개 모델 + FK | `models.py` (388줄) | A |
| 2 | SEC Collector | 메타+HTML+섹션추출 | `collector.py` (373줄) | A |
| 3 | Track A 추출기 | Gemini 공급망 | `extractor.py` (145줄) | A |
| 4 | Celery Task | 수집/추출/검증 조율 | `tasks.py` (579줄) | A |
| 5 | Gold Set 검증 | 정확도 측정 | `management/commands/evaluate_gold_set.py` | A |
| 6 | Phase 1 배치 | 15종목 E2E | `quality_checks.py` (165줄) | A |
| 7 | Ticker 매칭 | 3단계 alias→exact→fuzzy | `ticker_matcher.py` (210줄) | A |
| 8 | Admin + Signal | UnmatchedQueue 관리 | `admin.py` (171줄) + `signals.py` (71줄) | A |
| 9 | Neo4j 동기화 | DELETE+CREATE 동적타입 | `tasks.py::sync_dirty_to_neo4j` | A |
| 10 | Merger + 관계병합 | DQS 계산 | `merger.py` (135줄) | A |
| 11~13 | Phase 2 Track B | LLM 사업모델 | `validator_track_b.py` + `keywords_track_b.py` + `prompts.py` | A |
| 14 | Admin 대시보드 | 7개 품질체크 + UI | `views.py` (46줄) + `quality_checks.py` | A |
| 15 | On-demand 수집 | 신규 filing 트리거 | `on_demand.py` (68줄) | A |
| 16 | Intelligence 리포터 | 5차원 + Gemini | `intelligence.py` (223줄) | A |
| 17 | E2E Chord | Phase 1~3 통합 | `tasks.py::run_batch_and_report` | A |

#### 주요 갭

1. **REST API 부족 (B)** — `urls.py`가 9줄, `FilingDataView` 1개만 노출. CLAUDE.md `/api/v1/sec/*` 다중 엔드포인트 암시와 불일치. **수집 상태/품질 체크/Intelligence 리포트** 조회 API가 없어 어드민 HTML UI 외에 외부 접근 경로 없음.
2. **마이그레이션 단일화 (B)** — `0001_initial.py`만 존재. Phase 2~3 모델 추가(BusinessModelSnapshot 등)가 0001에 통합되어 있는지 확인 필요. 향후 모델 변경 시 마이그레이션 누락 위험.
3. **CompanyAlias 자동 등록 미흡 (B)** — PR-7~8에서 자동 등록 메커니즘 약속, 실제로는 `UnmatchedCompanyQueue` 등록만 자동화되고 alias 자체는 수동 처리(`process_unmatched_queue`, `seed_company_aliases` 커맨드).
4. **Beat 스케줄 비활성화 (의심)** — `sync-sec-dirty-neo4j` 자동 스케줄이 주석 처리되어 있을 가능성. 별도 `beat_schedule_audit_*.md`와 cross-check 필요.

#### 검증 의심 영역

- `views.py`(46줄)에 대시보드 데이터 조회 API 없음 → 대시보드는 Admin HTML UI 한정
- JNJ 섹션 검증 실패 후 재검증 로직 미구현 (PR-6의 14/15 성공을 기준으로 마무리)
- 서비스 레이어 불일치: `metrics/services/business_model_service.py` (for_api 게이트)는 존재하나 `SupplyChainEvidence` 노출 서비스 없음

---

## Validation 상세

### 전체 구현률: 약 90~95% (BE-PR 1~6 + Phase 6/7 모두 A)

#### Phase별 매트릭스

| Phase | 핵심 산출물 | 구현 파일 | 상태 |
|-------|-------------|----------|------|
| 1 | 모델 + 지표 정의 | `models/` 5개 + `migrations/0001` | A |
| 2 | PeerPreset + 자동 프리셋 | `models/peer_preset.py` + `services/preset_generator.py` | A |
| 3 | quality_top + lifecycle | `preset_generator._generate_quality/_lifecycle` | A |
| 4 | UserPeerPreference + 커스텀 | `models/peer_preset.py` + `services/custom_benchmark_engine.py` | A |
| 5 | 카테고리 신호등 + 해석 | `services/category_signal_calculator.py` + `interpretation.py` | A |
| 6 | Thematic 프리셋 (LLM) | `preset_generator._generate_thematic` | A (D 일부) |
| 7 | LLM 대화형 필터 | `services/llm_peer_filter.py` + `LLMPeerFilterView` | A |

#### 모델 매핑

| 설계 모델 | 실제 모델 | 상태 |
|----------|----------|------|
| PeerPreset | `models/peer_preset.py` | A (preset_key, display_name, logic_summary, confidence_score) |
| UserPeerPreference | `models/peer_preset.py` | A (mode=preset/custom, custom_peers 배열) |
| CompanyBenchmarkDelta | `models/benchmark_delta.py` | A (preset_key 추가, 마이그 0004) |
| CategorySignal | `models/category_score.py` | A (signal=green/yellow/red/gray) |
| CompanyMetricLatest | `models/metric_latest.py` | A (trend_label, signal, warning_flag) |
| ValidationNewsSummary | `models/news_summary.py` | A |

#### API 엔드포인트 매핑 (모두 A)

| 설계 경로 | 실제 View |
|----------|-----------|
| `/api/v1/validation/{symbol}/summary/` | `ValidationSummaryView` |
| `/api/v1/validation/{symbol}/metrics/` | `ValidationMetricsView` |
| `/api/v1/validation/{symbol}/leader-comparison/` | `LeaderComparisonView` |
| `/api/v1/validation/{symbol}/presets/` | `PresetListView` |
| `/api/v1/validation/{symbol}/peer-preference/` | `PeerPreferenceView` (POST/DELETE) |
| `/api/v1/validation/{symbol}/llm-filter/` | `LLMPeerFilterView` |

#### Celery Task 완성도 (모두 A)

| Task | 함수 | BE-PR |
|------|------|-------|
| Task 1 (FMP 수집) | `fetch_annual_financials` | BE-PR-3 |
| Task 2 (지표 계산) | `calculate_derived_metrics` | BE-PR-3 |
| Task 3 (Peer + Benchmark) | `calculate_benchmarks` | BE-PR-4 |
| Task 3.5 (상대지표) | `calculate_relative_metrics` | BE-PR-4 |
| Task 4 (신호등) | `calculate_category_signals` | BE-PR-5 |
| Task 5 (Peer 캐시) | `update_peer_list_caches` | BE-PR-5 |
| Task 6 (로그) | `log_batch_run` | BE-PR-5 |
| Orchestrator | `run_weekly_validation_batch` | BE-PR-5 |

#### 주요 갭 / 변경 사항

1. **Phase 6 알고리즘 변경 (D 부분 대체)** — 설계서는 `CompanyNarrativeTag.theme_tags` 기반 LLM 사업모델 태깅을 명시했으나, 실제는 **GrowthStage × CapitalDNA 교차 조합**(ChainSight 모델)으로 대체. 원인은 theme_tags 파이프라인 미완성. 결과 463/503 종목 커버, 기능 동등.
2. **Phase 7 범위 확장 (A 초과)** — 설계 5개 시나리오 → 실제 6개 필터 범주(Growth Stage, Capital Type, Rate Sensitivity, Forex Sensitivity, Regulation, Insider Signal) + 31개 메트릭. ChainSight 통합 필터 추가.
3. **마이그레이션 정규화 (양호)** — `0001` 초기 → `0002` 컬럼 → `0003` preset_key → `0004` unique_together 정규화. 점진적 변경 이력 명확.
4. **미연동 항목**: Thesis Control 직접 연동은 미포함 (설계상 선택 사항).

**기술 부채**: 거의 없음. 백엔드 완성도 가장 높은 앱.

---

## News 상세

### 전체 구현률: 약 85% (백엔드 거의 완료, 알림 가시성 + 프론트 일부 미구현)

#### 파이프라인 단계별 매트릭스

| 단계 | 설계 컴포넌트 | 구현 파일 | 상태 |
|------|--------------|----------|------|
| 1. 수집 | 4 Provider (Finnhub/FMP/Marketaux/AV) | `providers/*.py` + `services/market_feed.py` | A |
| 2. 정규화/중복제거 | Deduplicator + Sentiment 정규화 | `deduplicator.py` + `sentiment_normalizer.py` | A |
| 3. 분류/분석 | Engine A/B/C + LLM 심층분석 | `news_classifier.py` + `news_deep_analyzer.py` | A |
| 4. 키워드 추출 | Gemini 일일 키워드 + search_terms_en | `keyword_extractor.py` | A |
| 5. ML 학습 | LabelCollector + WeightOptimizer + LightGBM | `ml_label_collector.py` + `ml_weight_optimizer.py` + `ml_production_manager.py` | A |
| 6. Neo4j 동기화 | 이벤트 저장 + 그래프 | `news_neo4j_sync.py` | A |
| 7. 종목 인사이트 | 개인화 피드 + 추천 | `personalized_feed.py` + `stock_recommender.py` + `stock_insights.py` | A |
| 8. Aggregation | 종합 서빙 | `aggregator.py` + `circuit_breaker.py` | A |

#### 마이그레이션 매핑

| 마이그 | 모델/변경 | 설계 매핑 |
|-------|----------|---------|
| 0001 | NewsArticle, NewsEntity, EntityHighlight, SentimentHistory | 초기 ✓ |
| 0002 | DailyNewsKeyword | Phase 2 키워드 ✓ |
| 0003 | NewsCollectionCategory | sector/sub_sector/custom 카테고리 ✓ |
| 0004 | NewsCollectionLog, MLModelHistory | v3 파이프라인 + ML 추적 ✓ |
| 0005 | 다중 Provider 확장 | FMP/AV 수집 로깅 ✓ |
| **0006** | **AlertLog** (7개 trigger_type) | **모니터링 Phase C** ✓ |

#### 모니터링 설계 갭 (Phase A/B/C)

- **Phase A — 기존 데이터 노출 (A 완전)**: `/api/v1/news/ml-status/`, `/ml-weekly-report/`, `/ml-shadow-report/`, `/ml-lightgbm-readiness/` 모두 구현. **추가 구현**: `pipeline-health` (6 Phase 통합 + 평일/주말 구분), `llm_usage`, `neo4j_status`.
- **Phase B — 헬스 체크 심화 (A)**: `NewsCollectionLog` 기반 Phase별 통계, `error_rate`, `hours_since_last_run`, `weekday_only` 처리 모두 구현.
- **Phase C — 능동 모니터링 (B 부분 구현)**:
  - ✅ `AlertLog` 모델 + `tasks.py::check_pipeline_alerts()` 정기 체크 태스크 존재
  - ✅ trigger_type 7종 (CONSECUTIVE_TASK_FAILURE, ML_F1_DECLINE, KEYWORD_EXTRACTION_FAILURE, LLM_ERROR_SPIKE, NEO4J_UNAVAILABLE, COLLECTION_DROP, UNCLASSIFIED_BACKLOG) 모두 구현
  - ❌ **AlertLog 조회 REST API 없음** (admin에만 등록 → 외부/프론트 가시성 0)

#### Keyword Detail (BottomSheet v2) 갭

| 항목 | 설계 | 구현 | 상태 |
|------|------|------|------|
| `keyword_detail` API | ✓ | ✓ (views.py 641~774줄, date+index 파라미터) | A |
| `search_terms_en` 필드 | ✓ | ✓ (Gemini 호출 시 추가, JSON 저장) | A |
| 2단 매칭 (entities → fallback ICONTAINS) | ✓ | ✓ | A |
| Gemini 투자 관점 요약 | ✓ | ✓ (`_generate_keyword_analysis()`, 실패 시 null) | A |
| Redis 캐싱 (1시간 TTL) | ✓ | ✓ (`news:keyword_detail:{date}:{index}:{updated_epoch}`) | A |
| **BottomSheet v2 (가로 스크롤 Strip)** | ✓ | ❌ 프론트 미구현 (백엔드는 keywords 배열 반환 준비 완료) | C |

#### API 엔드포인트 매핑

| 설계 경로 | 구현 |
|----------|------|
| `/api/v1/news/stock/{symbol}` | ✓ `stock_news` |
| `/api/v1/news/keyword-detail/?date=&index=` | ✓ `keyword_detail` |
| `/api/v1/news/daily-keywords/` | ✓ `daily_keywords` |
| `/api/v1/news/generate-daily-keywords/` | ✓ (force 파라미터) |
| `/api/v1/news/ml-status/`, `/ml-weekly-report/`, `/ml-shadow-report/`, `/ml-lightgbm-readiness/` | ✓ |
| `/api/v1/news/pipeline-health/` | ✓ (설계서 명시 없음, 추가 구현) |
| **알림 조회 API** | ❌ 미구현 (C) |

#### 주요 갭 정리

| 항목 | 분류 | 비고 |
|------|------|------|
| AlertLog 조회 API | C | 백엔드 모델·로직 모두 있음. 엔드포인트 추가만 필요 |
| 관리자 모니터링 대시보드(프론트) | C | Phase C 가시화 미흡 |
| BottomSheet v2 (가로 스크롤 Strip) | C | 백엔드 데이터 준비 완료, 프론트만 미구현 |
| 폐기/대체 산출물 | — | 없음. CLAUDE.md "v3 완료"와 일치 |

---

## 종합 권장 후속 작업 (참고용)

> 본 보고서는 갭 진단 전용이며, 후속 PR은 별도 결정. 아래는 우선순위 신호로만 활용.

1. **SEC Pipeline**: REST API 마무리 (수집 상태/품질 체크/Intelligence 리포트 조회 엔드포인트 추가) — 어드민 HTML 외 외부 접근 경로 부재가 가장 큰 갭
2. **News**: `AlertLog` 조회 API 1개 + 관리자 대시보드 프론트 작업 — 백엔드 자산이 가시화되지 못하는 상태
3. **News**: BottomSheet v2 가로 스크롤 Strip 프론트 구현 — 백엔드 준비 완료
4. **Validation**: Phase 6 theme_tags 파이프라인 완성 시 GrowthStage×CapitalDNA에서 LLM 태깅으로 회귀 가능 여부 검토
5. **SEC Pipeline**: `0001_initial.py` 단일 마이그레이션 검증 — 향후 변경 시 누락 주의

---

**감사 메타**

- 분석 방법: 설계 문서(`docs/sec_pipeline/`, `docs/first_validation_system/`, `docs/news/plan/`) + `task_done/` 완료 보고서 + 실제 코드 디렉토리/파일 cross-reference
- 코드 수정 0건 (읽기 전용)
- 라인 수 기준: SEC 2,936줄 / Validation 200줄(앱 직속) + services 9개 / News 2,317줄(앱 직속) + services 17개
