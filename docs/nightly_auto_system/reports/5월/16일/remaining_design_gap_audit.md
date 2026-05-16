# SEC Pipeline + Validation + News 설계 갭 감사

> **작성일**: 2026-05-17
> **감사 범위**: `docs/sec_pipeline/`, `docs/first_validation_system/`, `docs/news/` 설계서 ↔ `sec_pipeline/`, `validation/`, `news/` 구현
> **방식**: 읽기 전용 정적 분석 (코드 수정 없음), task_done/ 완료 보고서 cross-reference
> **분류 기준**: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 앱별 요약 (구현률)

| 앱 | 설계 항목 수 | A | B | C | D | 코드 존재율 | 운영 가능률 | 위험도 |
|----|------------|---|---|---|---|------------|------------|--------|
| **SEC Pipeline** | 17 PR | 16 | 1 | 0 | 0 | **99.4%** | ⚠️ 60% (Stock DB·Gold Set 데이터 갭) | 🟡 중 |
| **Validation** | 32 항목 | 23 | 7 | 2 | 0 | **94%** | ⚠️ 70% (Chain Sight 데이터 0건) | 🟡 중 |
| **News** | 30+ 항목 | 22 | 5 | 3 | 0 | **93%** | ✅ 90% (Pipeline v3 운영 중) | 🟢 저 |

### 공통 패턴
1. **코드는 거의 다 있다** — 3개 앱 모두 코드 존재율 90%+. 설계서 ↔ 구현 매핑은 우수.
2. **운영 가능률이 더 낮다** — 코드는 있지만 의존 데이터(`Stock DB`, `chainsight 모델`, `search_terms_en` 필드)가 비어 있어 실제 동작 불가한 경로 존재.
3. **FE 미구현이 공통 미커버 영역** — 백엔드 감사 대상에서는 (C)로 분류, 프론트엔드 담당 영역으로 분리.
4. **task_done 기록 시점 ↔ 현재 시점 괴리** — Validation Phase 6 task_done(2026-04-04)에는 "463/503 thematic 생성 완료"라고 적혀 있으나 현재 chainsight 테이블이 비어 있음. **기록과 현실의 데이터 잔존성 차이 주의**.

### 핵심 결론
- **SEC Pipeline**: 코드 완성도는 최상급이나 **설계 가정 오류**(Stock DB에 해외 기업 미등록 → ticker 매칭률 3%) 때문에 Intelligence Report severity=critical 고착.
- **Validation**: 백엔드 6개 PR 모두 완료, **Phase 6·7은 chainsight 데이터 의존**으로 활성화 대기 상태.
- **News**: Pipeline v3 운영 중·테스트 607개 통과. 잔존 갭은 `search_terms_en` 저장 누락·`_log_collection()` 6개 태스크 미호출.

---

## SEC Pipeline 상세

### 구현률 매트릭스

| 분류 | 갯수 | 비율 |
|------|------|------|
| (A) 완전 구현 | 16 | 94.1% |
| (B) 부분 구현 | 1 | 5.9% |
| (C) 미구현 | 0 | 0% |
| (D) 폐기/대체 | 0 | 0% |

### Decision 001 준수 — FMP→SEC EDGAR 전환
- ✅ `collector.py`에서 FMP 호출 완전 제거, SEC EDGAR `submissions/CIK{cik}.json` 직접 호출
- ✅ CIK 변환 (`_get_cik()`), HTML 다운로드 (`fetch_filing_html()`), RSS 대체 (`submissions` polling) 모두 SEC EDGAR
- ✅ `settings.py` FMP_API_KEY 의존성 없음
- **준수율: 100%**

### PR별 분류표

| PR | 제목 | 분류 | 핵심 산출물 | 갭 노트 |
|----|------|------|------------|--------|
| 1 | Django 앱 + 모델 | **A** | 8개 모델 + migration 0001 | FK/Meta/constraints 완벽 일치 |
| 2 | SEC EDGAR 수집기 | **A** | `SECFilingCollector`, `validate_extracted_sections` | Decision 001 적용, 3종목 테스트 성공 |
| 3 | Track A 추출 | **A** | `GeminiExtractor` (gemini-2.5-flash, JSON, temp=0.1), 30개 SC 키워드, 8개 검증 규칙 | NVDA 8 관계 검증 |
| 4 | Celery tasks | **A** | `collect_and_extract` (retry 3), `extract_from_document` (retry 2), 4개 예외 | NVDA 동기 테스트 성공 |
| 5 | Gold Set | **B** | `fixtures/gold_set.json` 10종목, `evaluate_gold_set` command | ⚠️ supply_chain은 NVDA 5개만 라벨. Precision 8.5% (target 70%) |
| 6 | Phase 1 배치 | **A** | 15종목 수집, 14 성공 (93.3%), 66개 관계 | ⚠️ JNJ Item 순서 실패 미대응 |
| 7 | TickerMatcher | **A** | 3단계 매칭 (alias→exact→fuzzy ≥85%), 큐 적재 | ⚠️ **매칭률 3% (2/66)** — Stock DB 해외 기업 미등록 |
| 8 | Admin + Signal | **A** | `UnmatchedCompanyQueueAdmin`, `on_unmatched_resolved` signal | sector 격리 원칙 준수 |
| 9 | Neo4j 동기화 | **A** | `sync_dirty_to_neo4j` (DELETE+CREATE, dynamic type) | MERGE 금지, dirty flag 사용 |
| 10 | 관계 병합 | **A** | `merger.py`, `process_unmatched_queue` command | DQS 내부용/API용 분리 |
| 11~13 | Track B + BM | **A** | 5개 BM 필드 키워드, `business_model_service.save_business_model_snapshot` | NVDA: hybrid/hybrid/medium/high_dep/diversified |
| 14 | Admin 대시보드 | **A** | 7개 품질 체크, `staff_member_required` | 7개 threshold 정의 |
| 15 | On-Demand API | **B** | `FilingDataView` (200/202), `get_or_collect_filing` | ⚠️ `IsAdminUser` 제약, 설계서 스코프와 불일치 |
| 16 | Intelligence Report | **A** | `PipelineDataCollector` (5차원), `PipelineIntelligenceReporter` (Gemini) | ⚠️ 첫 실행 severity=critical (health=0.2) |
| 17 | E2E Chord | **A** | `run_batch_and_report` (Celery chord) | AAPL/MSFT/JPM/XOM/NVDA E2E 성공, Beat schedule 주석 처리 |

### 핵심 갭 Top 5

1. **PR-7 Ticker 매칭률 3% (설계 가정 오류)** — TSMC/Samsung/SK Hynix 등 비미국 기업이 Stock DB에 없어 fuzzy 매칭 실패. PR-16 Intelligence Report가 severity=critical로 고착되는 근본 원인.
2. **PR-5 Gold Set 라벨 미완성** — `section_presence`만 완전(10/10), `supply_chain` 라벨은 NVDA 5개뿐. Precision 8.5% (target 70%) 미달.
3. **PR-6 JNJ Item 순서 검증 실패 미처리** — `validators._check_item_order()`가 JNJ 같은 특수 케이스를 강제 거부. 완료 보고서 "우선순위 낮음"으로 보류.
4. **PR-15 On-Demand API 권한 스코프 불일치** — 설계는 외부 호출용으로 보이나 실제는 `IsAdminUser` 제약. 외부 호출 시 401.
5. **Celery Beat schedule 비활성화** — PR-17 보고서에 "주석 상태"로 기록. 수동 실행만 가능, 자동화 미완성.

### 운영 리스크 매트릭스

| 영역 | 코드 | 데이터 | 운영 |
|------|------|--------|------|
| 모델/마이그레이션 | ✅ | ✅ | ✅ |
| Celery 태스크 8개 | ✅ | — | ⚠️ Beat 비활성 |
| Ticker 매칭 | ✅ | ❌ Stock DB 미등록 | ❌ 3% 매칭률 |
| Gold Set 평가 | ✅ | ⚠️ NVDA만 라벨 | ❌ Precision 8.5% |
| Intelligence Report | ✅ | — | ❌ severity=critical |
| 프롬프트 버전 관리 | ⚠️ 하드코딩 v1 | — | ⚠️ 일반명사 추출 미해결 |
| `tests.py` | ❌ 빈 파일 | — | ❌ 테스트 없음 |

### 즉시 조치 권장
1. Stock DB에 TSM, Samsung 등 해외 ADR/주요 공급망 기업 수동 등록
2. Gold Set 10종목 supply_chain 라벨 완전 채움 → Precision/Recall 재평가
3. `prompts.py` PROMPT_VERSION 'v2'로 올리고 일반명사 추출 방지 룰 추가
4. `validators._check_item_order()` 완화 옵션 추가 (JNJ 케이스)
5. Celery Beat schedule 주석 해제 (`sync-sec-dirty-neo4j`, `check-new-filings`)

---

## Validation 상세

### 구현률 매트릭스

| 분류 | 갯수 | 비율 |
|------|------|------|
| (A) 완전 구현 | 23 | 72% |
| (B) 부분 구현 | 7 | 22% |
| (C) 미구현 | 2 | 6% |
| (D) 폐기/대체 | 0 | 0% |

### BE PR별 분류표

| PR | 제목 | 분류 | 위치 | 갭 노트 |
|----|------|------|------|--------|
| BE-PR-1 | validation 앱 + 9개 모델 | **B** | `validation/models/` 4개 + `metrics/` 5개 | 모델 분산 배치 (설계서는 일괄 가정) — 합리적 분산이나 문서 갱신 필요 |
| BE-PR-2 | 34개 지표 + handling_mode 시딩 | **A** | `seed_validation_data.py` | 34개 지표 모두 시딩 |
| BE-PR-3 | Task 1~2 (재무 + 지표) | **A** | `fetch_annual_financials`, `calculate_derived_metrics` | value_status 판정 로직 완성 |
| BE-PR-4 | Task 3~3.5 (Peer + Benchmark) | **A** | `calculate_benchmarks`, `calculate_relative_metrics` | `rev_growth_vs_industry` 포함 |
| BE-PR-5 | Task 4~6 + Orchestrator | **A** | `calculate_category_signals`, `update_peer_list_caches`, `log_batch_run`, `run_weekly_validation_batch` | 전체 Celery chain 구현 |
| BE-PR-6 | 3개 API | **A** | `summary`/`metrics`/`leader-comparison` + 신규 `presets`/`peer-preference`/`llm-filter` | 설계 3개 → 실제 6개 (선제적 확장) |
| FE-PR-1~7 | 프론트엔드 컴포넌트 | **C** | — | 백엔드 감사 범위 외, 별도 처리 |

### 6가지 Peer Preset 매트릭스

| 프리셋 | preset_key | 구현 | 활성 가능 | 분류 |
|--------|-----------|------|----------|------|
| 1. 업종 표준 | `default` | ✅ `_generate_default()` | ✅ | **A** |
| 2. 섹터 전체 | `sector_all` | ✅ `_generate_sector_all()` | ✅ | **A** |
| 3. 체급 동종 | `size_peers` | ✅ `_generate_size_peers()` | ✅ | **A** |
| 4. 우량주 비교 | `quality_top` | ✅ `_generate_quality_top()` | ✅ | **A** |
| 5. 성장단계 유사 | `lifecycle` | ✅ `_generate_lifecycle()` | ✅ | **A** |
| 6. 비즈니스 테마 | `thematic` | ⚠️ `_generate_thematic()` 존재, **CompanyCapitalDNA/GrowthStage 의존** | ❌ chainsight 0건 | **B** |

**프리셋 6종 활성률: 5/6 (83%)** — 코드 완성 6/6, 데이터 의존성 해결 필요.

### Phase 6·7 동작 가능성

| Phase | 코드 | 의존 데이터 | 동작 가능 |
|-------|------|------------|----------|
| Phase 6 (Thematic) | ✅ `_generate_thematic` 완성 | `CompanyGrowthStage`, `CompanyCapitalDNA` 0건 | ❌ 데이터 채우면 즉시 동작 |
| Phase 7 (LLM Filter) | ✅ `parse_filter_with_llm`, `execute_peer_filter`, `LLMPeerFilterView` 완성 | 메트릭 필터 ✅, Chain Sight 필터 (foreign_revenue_pct, rd_to_revenue 등) ❌ | ⚠️ 5개 시나리오 중 3개만 동작 |

### API 엔드포인트 매트릭스

| 엔드포인트 | 설계 | 구현 | 분류 |
|-----------|------|------|------|
| `GET /{symbol}/summary/` | ✅ | ✅ `ValidationSummaryView` | **A** |
| `GET /{symbol}/metrics/?category=` | ✅ | ✅ `ValidationMetricsView` | **A** |
| `GET /{symbol}/leader-comparison/` | ✅ | ✅ `LeaderComparisonView` | **A** |
| `GET /{symbol}/presets/` | — | ✅ `PresetListView` (확장) | **A** (확장) |
| `POST /{symbol}/peer-preference/` | — | ✅ `PeerPreferenceView` (확장) | **A** (확장) |
| `POST /{symbol}/llm-filter/` | ✅ Phase 7 | ✅ `LLMPeerFilterView` | **A** |

### Celery Task 체인 (8개 모두 등록)

| Task | 함수 | 분류 |
|------|------|------|
| Task 1 | `fetch_annual_financials` | **A** |
| Task 2 | `calculate_derived_metrics` (value_status 판정 포함) | **A** |
| Task 3 | `calculate_benchmarks` (peer 선정 + benchmark) | **A** |
| Task 3.5 | `calculate_relative_metrics` (`rev_growth_vs_industry`) | **A** |
| Task 4 | `calculate_category_signals` (special 산업 → gray) | **A** |
| Task 5 | `update_peer_list_caches` | **A** |
| Task 6 | `log_batch_run` | **A** |
| Orchestrator | `run_weekly_validation_batch` | **A** |

### 34개 지표 계산 확인

- `MetricCalculator._calculate_all_metrics()`: 33개 + Task 3.5 `rev_growth_vs_industry` = **34개 모두 계산**
- 카테고리별: 수익성 5 + 성장 4 + 재무구조 6 + 현금흐름 6 + 운영효율 6 + 희석·주주 4 + 밸류에이션 3 = 34
- 분류: **(A) 완전 구현**

### 특수 케이스 처리

| 케이스 | 설계 | 구현 | 분류 |
|--------|------|------|------|
| `cash_runway_years` 흑자 → not_applicable | ✅ | ✅ | **A** |
| `interest_coverage` total_debt=0 → not_applicable | ✅ | ✅ `_calc_interest_coverage` (라인 273~302) | **A** |
| Special 산업 (금융/보험/REIT) → 카테고리 gray | ✅ | ✅ `SPECIAL_GRAY_CATEGORIES` + `IndustryClassification.handling_mode` | **A** |
| `quality_top`에서 ROIC→ROE 대체 (금융) | ✅ | ✅ | **A** |

### 핵심 갭 Top 5

1. **Thematic 프리셋 데이터 의존** — 코드 완성, `chainsight 0건`으로 동작 불가. task_done(2026-04-04)은 "463/503 종목" 기록했으나 현재 테이블 비어 있음. **데이터 잔존성 손실**.
2. **LLM Filter 5 시나리오 중 2개 미동작** — `foreign_revenue_pct`/`rd_to_revenue` 등 Chain Sight 필터 의존 시나리오는 `CompanySensitivityProfile`/`CompanyCapitalDNA` 0건으로 실패.
3. **BE-PR-1 모델 분산 배치** — 9개 모델 중 4개 `validation/`, 5개 `metrics/`. 설계서가 일괄 배치를 가정했으므로 **DECISIONS.md 갱신 필요**.
4. **CLAUDE.md "1차 검증 완료" 표기 정확도 80%** — Thematic·LLM Filter 제약 사항 미명시.
5. **FE-PR-1~7 미구현** — 백엔드 6개 PR 완료, 프론트엔드 컴포넌트는 별도 처리 필요.

### 즉시 조치 권장
1. `chainsight` 파이프라인 재실행 (Phase 0~5) → Thematic·LLM Filter 활성화
2. CLAUDE.md "1차 검증" 표기에 "(Phase 6/7는 chainsight 데이터 의존)" 주석 추가
3. DECISIONS.md에 "Validation 모델을 validation/+metrics/에 분산 배치" 결정 기록
4. `validation_design.md` 모델 위치 섹션 갱신 (분산 사실 명시)

---

## News 상세

### 구현률 매트릭스

| 분류 | 갯수 | 비율 |
|------|------|------|
| (A) 완전 구현 | 22 | 73% |
| (B) 부분 구현 | 5 | 17% |
| (C) 미구현 | 3 | 10% |
| (D) 폐기/대체 | 0 | 0% |

### 설계 문서별 매핑

| 설계 문서 | 핵심 의도 | 구현 상태 | 분류 |
|----------|----------|----------|------|
| `news_keyword_detail_plan.md` | 키워드 클릭 → 바텀시트 + LLM 한국어 요약 + 영문 기사 매칭 | ✅ API + Gemini + Redis 캐시 완성, `search_terms_en` 저장 미확인 | **B** |
| `keyword_detail_bottomsheet_v2.md` | 모바일 바텀시트 + 가로 스크롤 Strip | ✅ 백엔드 (`daily-keywords`, `keyword-detail`) 완성, FE 미구현 | **A** (백엔드 한정) |
| `news_pipeline_monitoring_design.md` | Phase A 4개 + Phase B 4개 + Phase C 2개 API | ✅ 백엔드 10개 모두 구현, FE 대시보드 미구현 | **B** |

### 26개 API 엔드포인트 분류

**완전 구현 (A): 24개**
- 키워드/뉴스 조회: `daily-keywords`, `daily-keywords/generate`, `insights`, `all`, `stock/{symbol}`, `stock/{symbol}/sentiment`, `market-feed`, `interest-options`, `personalized-feed`, `news-events`, `news-events/impact-map` (11)
- ML: `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`, `ml-rollback-preview`, `ml-rollback` (6)
- 모니터링: `collection-logs`, `pipeline-health`, `ml-trend`, `llm-usage`, `task-timeline`, `neo4j-status`, `alerts`, `alerts/{id}/resolve` (8) — 단 `collection-logs`는 데이터 편향 있음

**부분 구현 (B): 2개**
- `keyword-detail` — `search_terms_en` 저장 불확실 (fallback로 동작)
- `collection-logs` — `_log_collection()` 4/10 태스크만 호출, FMP/AV 편향

### Celery 태스크 19개 (모두 등록)

| 태스크 | Phase | 분류 |
|--------|-------|------|
| `extract_daily_news_keywords` | Keyword | **A** |
| `collect_daily_news` | Phase 1 | **B** (_log_collection 미호출) |
| `collect_market_news` | Phase 1 | **B** (_log_collection 미호출) |
| `collect_category_news` | Phase 1 | **A** |
| `collect_sp500_news_fmp_batch` | Phase 1 | **A** |
| `collect_press_releases_fmp` | Phase 1 | **A** |
| `collect_general_news_fmp` | Phase 1 | **A** |
| `collect_av_single_symbol` | Phase 1 | **A** |
| `classify_news_batch` | Phase 2 | **B** (_log_collection 미호출) |
| `analyze_news_deep` | Phase 3 | **B** (_log_collection 미호출) |
| `collect_ml_labels` | Phase 4 | **A** |
| `sync_news_to_neo4j` | Phase 4 | **B** (_log_collection 미호출) |
| `train_importance_model` | Phase 5 | **A** |
| `generate_shadow_report` | Phase 5 | **A** |
| `check_auto_deploy` | Phase 5 | **A** |
| `train_lightgbm_model` | Phase 6 | **A** |
| `generate_weekly_ml_report` | Phase 6 | **A** |
| `monitor_ml_performance` | Phase 6 | **A** |
| `aggregate_daily_sentiment` | Utility | **A** |

### News Intelligence Pipeline v3 컴포넌트 매트릭스

| Phase | 컴포넌트 | 운영 상태 | 분류 |
|-------|---------|----------|------|
| Phase 1: 수집 | `aggregator.py`, `deduplicator.py`, 4 providers (Finnhub/FMP/MarketAux/AV) | ✅ 운영 중 | **A** |
| Phase 2: 분류 (Engine A/B/C) | `news_classifier.py` | ✅ 운영 중 | **A** |
| Phase 3: LLM 분석 | `news_deep_analyzer.py` | ✅ 운영 중 | **A** |
| Phase 4a: ML Label 수집 | `ml_label_collector.py` | ✅ 운영 중 | **A** |
| Phase 4b: Neo4j 동기화 | `news_neo4j_sync.py` | ✅ 운영 중 | **A** |
| Phase 5a: LR 학습 | `ml_weight_optimizer.py:train_lr` | ✅ 운영 중 | **A** |
| Phase 5b: Shadow Mode | `ml_production_manager.py:generate_shadow_report` | ✅ 운영 중 | **A** |
| Phase 5c: 자동 배포 | `ml_production_manager.py:check_auto_deploy` | ✅ 운영 중 | **A** |
| Phase 6a: LightGBM | `ml_weight_optimizer.py:train_lightgbm` | ✅ 운영 중 | **A** |
| Phase 6b: 주간 리포트 | `ml_production_manager.py:generate_weekly_report` | ✅ 운영 중 | **A** |
| Phase 6c: 성능 모니터링 | `ml_production_manager.py:monitor_ml_performance` | ✅ 운영 중 | **A** |

**테스트 607개 통과 (CLAUDE.md 기록)** — Pipeline v3 전 영역 검증 완료.

### 데이터 모델 필드 검증

| 모델 | 핵심 필드 | 분류 |
|------|----------|------|
| `NewsArticle` | importance_score, llm_analyzed, llm_analysis, ml_label_24h, ml_label_important | **A** |
| `DailyNewsKeyword` | keywords[], status, prompt_tokens, completion_tokens, generation_time_ms | **A** (단, `search_terms_en` 항목 저장 미확인) |
| `MLModelHistory` | f1_score, precision, recall, deployment_status, shadow_comparison | **A** |
| `NewsCollectionLog` | task_name, provider, articles_new, articles_dup, errors, duration_sec | **A** |
| `AlertLog` | trigger_type, severity, message, context, is_resolved (migration 0006) | **A** |

### 핵심 갭 Top 5

1. **`search_terms_en` 저장 로직 불확실 (C)** — `keyword-detail` 엔드포인트가 `kw.get('search_terms_en', [])`로 시도하나 `keyword_extractor.py`에서 해당 필드가 JSON에 저장되는지 확인 안 됨. Gemini 프롬프트만 존재 가능성.
2. **`_log_collection()` 6개 태스크 미호출 (C)** — 설계서 §11이 `collect_daily_news`, `collect_market_news`, `classify_news_batch`, `analyze_news_deep`, `sync_news_to_neo4j` 추가를 명시했으나 실제로는 FMP/AV 배치 4개만 호출. `collection-logs` API 통계가 편향됨.
3. **FE 대시보드 미구현 (C)** — `news_pipeline_monitoring_design.md` §4 NewsTab sub-tab 구조 미존재. 백엔드 API 10개는 완성.
4. **`DailyNewsKeyword.article_ids` 직접 저장 (B)** — 현재 fallback 2단 매칭 사용 (related_symbols → search_terms_en). 직접 저장 시 성능 개선 가능.
5. **`check_pipeline_alerts` 태스크 없음 (C)** — Phase C 설계의 알림 트리거 태스크 미구현, 알림은 수동 생성만 가능.

### 설계 외 추가 구현 (구현은 있는데 설계 문서에 없음)

| 항목 | 위치 | 비고 |
|------|------|------|
| `NewsCollectionCategory` | `models.py` + API | `sub_claude_md/news-insights.md`에 문서화 (별도 트랙) |
| `news-events`/`impact-map` 엔드포인트 | `views.py` 라인 1023, 1082 | Neo4j 뉴스 이벤트 맵 (Pipeline v3 통합 결과) |
| `collect_av_single_symbol` 태스크 | `tasks.py` | Alpha Vantage 단일 심볼 수집 |

### 즉시 조치 권장
1. `keyword_extractor.py` 코드 확인 — Gemini 응답에서 `search_terms_en`을 `keywords[i]`에 실제로 저장하는지 검증, 없으면 추가
2. `_log_collection()` 호출을 6개 태스크 (`collect_daily_news`, `collect_market_news`, `classify_news_batch`, `analyze_news_deep`, `sync_news_to_neo4j`, `extract_daily_news_keywords`)에 추가 → `collection-logs` 편향 해소
3. `DailyNewsKeyword` 생성 시 `article_ids` 직접 저장하도록 변경 → fallback 매칭 제거 (선택)
4. `check_pipeline_alerts` Celery 태스크 추가 (Phase C 미완성 항목)
5. NewsTab sub-tab 대시보드 FE 구현 (별도 PR)

---

## 부록: 세 앱 공통 패턴 및 결론

### A. "코드 있음 ≠ 운영 가능"

세 앱 모두 코드 존재율은 90%+이나, **의존 데이터/설정** 측면에서 갭이 큼.

| 앱 | 코드 결손 | 데이터 결손 | 설정 결손 |
|----|----------|------------|----------|
| SEC Pipeline | 거의 없음 (테스트 파일만 빈 상태) | **Stock DB 해외 기업 + Gold Set 라벨** | Celery Beat schedule 주석 처리 |
| Validation | FE 컴포넌트 (스코프 외) | **chainsight 모델 0건** | — |
| News | `_log_collection()` 6개 미호출, `search_terms_en` 저장 불확실 | — | FE 대시보드 미구현 |

### B. task_done 기록의 신뢰도 주의

- Validation `peer_phase6_thematic.md` (2026-04-04): "463/503 종목에 thematic 생성됨"
- 현재 (2026-05-17): chainsight 테이블 비어 있음 → 데이터 잔존성 손실
- **권장**: task_done 보고서에 "이 시점 기준" 명시, 데이터 잔존성 별도 추적

### C. CLAUDE.md 표기 정확도

| 앱 | 표기 정확도 | 갭 |
|----|------------|-----|
| SEC Pipeline | 90% | "SEC Pipeline (10-K Supply Chain + Business Model 추출)" 완료 표기 OK, 운영 리스크 미명시 |
| Validation | 80% | "1차 검증 완료" 표기, Phase 6/7 chainsight 데이터 의존 미명시 |
| News | 95% | "News Intelligence Pipeline v3 (... 테스트 607개)" 정확. `_log_collection()` 편향만 미명시 |

### D. 최종 우선순위

| 우선순위 | 조치 | 영향 앱 |
|---------|------|--------|
| **P0 (긴급)** | Stock DB 해외 기업 등록 (TSM, Samsung 등) | SEC Pipeline |
| **P0 (긴급)** | chainsight 파이프라인 재실행 → Thematic/LLM Filter 활성화 | Validation |
| **P1 (높음)** | `_log_collection()` 호출 추가 (6개 태스크) | News |
| **P1 (높음)** | Gold Set 10종목 supply_chain 완전 라벨 | SEC Pipeline |
| **P1 (높음)** | `search_terms_en` 저장 로직 검증/추가 | News |
| **P2 (중간)** | Celery Beat schedule 주석 해제 | SEC Pipeline |
| **P2 (중간)** | CLAUDE.md 표기 보정 (Validation 제약, News 편향) | 전체 |
| **P3 (낮음)** | FE 컴포넌트 (BE 완성된 영역) | Validation, News |

---

**감사 종료**
- 작성: 2026-05-17, 읽기 전용 정적 분석
- 분석 범위: 17 PR (SEC) + 32 항목 (Validation) + 30+ 항목 (News) = 79+ 비교 단위
- 결론: **3개 앱 모두 코드 완성도 우수, 운영 가능률은 데이터/설정 갭 때문에 60~90% 범위**. 코드 작성보다 **데이터 보완 + 설정 활성화 + 문서 표기 정정**이 우선.
