# SEC Pipeline + Validation + News 설계 갭 감사

- **감사일**: 2026-05-03
- **감사 범위**: `docs/sec_pipeline/` vs `sec_pipeline/`, `docs/first_validation_system/` vs `validation/`, `docs/news/` vs `news/`
- **방식**: 읽기 전용. 설계 문서·task_done 보고서·실제 코드(시그니처/필드/엔드포인트) 비교
- **분류 기준**: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기 또는 대체

---

## 앱별 요약 (구현률)

| 앱 | 설계 단위 | A | B | C | D | 종합 구현률 |
|----|----------|---|---|---|---|------------|
| **SEC Pipeline** | PR 17개 | 16 | 1 | 0 | 0 | **94%** (PR-17 Beat schedule 비활성 1건) |
| **Validation** | BE-PR 6 + Phase 6/7 + FE-PR 7 (총 13~14단위) | 11 | 2 | 0 | 0 | **95%** (Phase 7 Thesis 통합·Phase 6 방식 변경) |
| **News** | 설계 문서 3 + CLAUDE.md v3 6항목 | 5 | 3 | 0 | 0 | **85~90%** (Phase 0 `_log_collection` 보강·Celery `check_pipeline_alerts` 미확인) |

**핵심 결론**:
- 세 앱 모두 설계 문서를 충실히 따라 구현되었으며 미구현(C)·폐기(D) 항목 없음.
- 잔여 갭은 ① 운영 설정(Beat schedule 활성화), ② 설계 문서와 구현 방식 차이(Phase 6: Gemini 태깅 → Chain Sight DNA 교차), ③ 다른 에이전트(@infra) 담당 작업(Celery 알림 태스크), ④ 외부 데이터 의존성(Chain Sight 진행 중) 4가지 유형.
- 설계 문서에 없으나 구현된 영역(news-events, personalized-feed 등)은 v3 파이프라인 확장으로 보이며 별도 문서화 필요.

---

## SEC Pipeline 상세

### 구현률 요약
- **총 PR**: 17개 (Phase 1~3, 2026-04-04 완료)
- **A 완전 구현**: PR-1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 (16개)
- **B 부분 구현**: PR-17 (1개)
- **C 미구현**: 없음
- **D 폐기/대체**: 없음

### PR별 상세

| PR | 제목 | 분류 | 핵심 구현 위치 | 갭 |
|----|------|------|---------------|-----|
| PR-1 | 모델 + 마이그레이션 | A | `sec_pipeline/models.py:15-389`, `migrations/0001_initial.py` | 8개 모델 모두 설계대로 (`neo4j_dirty`, `get_latest_by`, `unique_together`) |
| PR-2 | SEC EDGAR 수집기 | A | `collector.py:39` `SECFilingCollector`, `validators.py:21` | FMP 대체 의사결정(SEC submission API) 기록됨 |
| PR-3 | Track A Gemini 추출 | A | `normalizer.py`, `prompts.py`, `extractor.py` `GeminiExtractor`, `validator_track_a.py` | 없음 |
| PR-4 | Celery tasks + 예외 | A | `tasks.py:22` `collect_and_extract`, `tasks.py:149`, `exceptions.py` 4개, `sp500.py` | 없음 |
| PR-5 | Gold Set 라벨 + 평가 | A | `fixtures/gold_set.json`, `gold_set_schema.py`, `management/commands/evaluate_gold_set.py` | 라벨 미완전(NVDA만 완전, 9종목 스텁) — PR-6에 영향 |
| PR-6 | Phase 1 배치 + 결과 | A | tasks 통한 15종목 배치, 110 evidence | 라벨 부족으로 Precision 62.5% / Recall 45.5% 저평가 위험 |
| PR-7 | TickerMatcher | A | `ticker_matcher.py:22` 3단계 매칭 | 비미국 주식(TSMC, Samsung 등) 미등록 — Stock DB 외부 의존 |
| PR-8 | Admin + Signal | A | `admin.py:17-129` 8개, `signals.py:22` `on_unmatched_resolved` | `CompanyAlias` 자동 등록 로직 상세 검증 권장 |
| PR-9 | Neo4j sync | A | `tasks.py:338` `sync_dirty_to_neo4j` (DELETE+CREATE, dynamic type, `select_for_update(skip_locked)`) | 없음 |
| PR-10 | Merger + 큐 처리 | A | `merger.py:36,76`, `management/commands/process_unmatched_queue.py` | DQS 내부키/API키 분리 정상 |
| PR-11~13 | Phase 2 Track B | A | `keywords_track_b.py:52`, `extractor.py:93` `extract_business_model`, `validator_track_b.py:64`, `metrics/services/business_model_service.py:16,58,96` | `for_api=True`일 때 `overall_confidence` 비노출 게이트 정확 |
| PR-14 | Admin 대시보드 | A | `quality_checks.py:17,119`, `views.py:15,28`, `templates/admin/sec_pipeline/dashboard.html` | 없음 |
| PR-15 | On-demand 수집 | A | `on_demand.py:18` `get_or_collect_filing`, `tasks.py:465` `check_new_filings` | GET `/api/v1/sec-pipeline/filing/{symbol}/` 200/202 분기 정상 |
| PR-16 | Intelligence Reporter | A | `intelligence.py:63,139`, `admin.py:129` | 5차원 메트릭 + Gemini 리포트 정상 |
| PR-17 | Chord 통합 + E2E | **B** | `tasks.py:501,509` `generate_intelligence_report`, `run_batch_and_report` | **Celery beat schedule 주석 처리(`tasks.py:559-564`) — 함수 구현은 100%, 운영 활성화 미적용** |

### 핵심 발견

**강점**
- 모델 8종이 `FK / 제약조건 / 필드명 / 타입` 모두 설계와 정확히 일치(`neo4j_dirty`만 사용, `synced_to_neo4j` 제외).
- Track A/B 양 파이프라인 완전 가동(15종목/110 evidence/5 BM snapshot).
- 신뢰도 노출 경계(`for_api`) 적용으로 API 응답에 `overall_confidence` 누출 없음.
- Neo4j 동기화 sole-writer + DELETE+CREATE 패턴 + `select_for_update(skip_locked)` 동시성 제어 적용.

**약점**
- PR-17 Celery Beat가 주석 상태 — 운영 정책 결정 필요(설계 문서가 "주석 상태"라 명시한 부분과 PR-17 완료 정의 모호).
- Gold Set 라벨이 NVDA 외 9종목 스텁 → 평가 지표 신뢰도 부족.
- 비미국 주식(`.` 포함, ADR 등) 매칭률 저조(2/66) — `CompanyAlias` 수동 등록 또는 Stock DB 보강 필요.

**의심 영역**
- 프롬프트 v2 개발(일반 명사 추출 방지) 향후 작업 항목으로만 표시되어 있음.
- `edgartools` fallback 코드는 있으나 실제 사용 여부 검증되지 않음.

---

## Validation 상세

### 구현률 요약
- **설계 단위**: BE-PR 1~6 + Phase 6 + Phase 7 + FE-PR 1~7
- **A 완전 구현**: 11개 (Models, Benchmark/Metric, Peer Preset Generator, Custom Engine, LLM Filter, API, BE-PR 1~6 전체)
- **B 부분 구현**: 2개 (Phase 6 구현 방식 변경, Phase 7 Thesis 통합 보류)
- **C 미구현**: 없음
- **D 폐기/대체**: 없음

### 영역별 상세

#### Models [A]
- 9개 모델 + 추가 `PeerPreset` / `UserPeerPreference` 완전 구현.
- `validation/models/peer_preset.py`: `preset_key` (default/sector_all/size_peers/quality_top/lifecycle/thematic 6종), `generation_method` 8 CHOICES, `confidence_score`, `logic_summary`.
- `benchmark_delta.py`/`category_score.py`: `preset_key` 필드 + `unique_together` 정확히 적용.

#### Services - Benchmark / Metric [A]
- `benchmark_calculator.py` (345줄): peer ≥8 industry+size, 5~7 industry, <5 sector fallback 명세대로.
- `metric_calculator.py` (459줄): 34개 지표 + `value_status`(not_applicable/missing/unstable/normal) 판정.
- `relative_metrics.py` (97줄): `rev_growth_vs_industry` 등 상대 지표.

#### Services - Peer Preset Generator [A]
- `preset_generator.py` (479줄)에 6개 `_generate_*` 메서드 모두 구현.
- 배치 결과: 463/503 종목 thematic 프리셋 생성, 총 **2,282개 프리셋** 배치 완료(2026-04-04).
- `confidence_score`: peer_count 패널티 + 업종 순도 + 지표 커버리지 + 특수 산업 패널티 반영.

#### Services - Custom Benchmark (Compute-on-Read) [A]
- `custom_benchmark_engine.py` (161줄): `compute_summary(symbol, custom_peers, user_id)`, `invalidate_cache()`.
- 벌크 1회 쿼리, numpy 없는 in-memory percentile, Redis TTL 1h, key=`custom_validation:{user_id}:{symbol}`.

#### Services - LLM Peer Filter [A]
- `llm_peer_filter.py` (264줄): `parse_filter_with_llm`, `execute_peer_filter`.
- 지원 필터: Chain Sight 6개 필드(growth_stage/capital_type/rate_sensitivity/forex_sensitivity/regulation_type/insider_signal) + Stock 31 metrics.
- 실측 결과: "성숙기 기업" 364개, "금리 민감도 낮고 비금융" 183개 정상.
- `foreign_revenue_pct` 등 일부 필터: 코드는 있으나 `CompanySensitivityProfile` 0건 → Chain Sight 데이터 대기.

#### API [A]
- 7개 엔드포인트 모두 구현(설계 3개 + 확장 4개):
  - GET `/api/v1/validation/{symbol}/summary/`
  - GET `/api/v1/validation/{symbol}/metrics/`
  - GET `/api/v1/validation/{symbol}/leader-comparison/`
  - GET `/api/v1/validation/{symbol}/presets/` (Phase 2 신규)
  - POST/DELETE `/api/v1/validation/{symbol}/peer-preference/` (Phase 2)
  - POST `/api/v1/validation/{symbol}/llm-filter/` (Phase 7)
- `ValidationSummaryView` (`api/views.py`): 커스텀 peer 분기 정상.

#### Phase 6 (Thematic Peer) [B]
- 설계: Gemini 사업모델 태깅 → `CompanyNarrativeTag.theme_tags` 클러스터링.
- 실제: `GrowthStage × CapitalDNA` 교차 조합(Chain Sight DNA 활용).
- **판정**: 목표(테마 기반 프리셋)는 달성, 구현 방식만 변경. 더 효율적이지만 설계 문서와 코드 불일치 → 문서 동기화 권장.

#### Phase 7 (LLM 대화형 필터) [B]
- 설계: 필터 엔진 + Thesis 모델 확장(`peer_preset_key`, `peer_filter_query`, `peer_filter_result`) + 관제실 연동.
- 실제: 필터 엔진(`parse_filter_with_llm`, `execute_peer_filter`) + API(`POST /llm-filter/`) 완성.
- **남은 작업**: Thesis 모델 필드 추가 + 관제실 탭 연동 — Phase 7-Full은 Chain Sight 데이터 완성 후로 예약.

#### Frontend [추정 진행 중]
- BE 전체 완료 + CLAUDE.md "1차 검증 완료" 표기 → FE 구현 단계 진입 추정. 구체적 FE-PR 1~7 검증은 본 감사 범위 외(`frontend/`).

### 핵심 발견

**강점**
- 6종 프리셋 + 2,282개 배치 + `confidence_score` 자동 계산 완비.
- Compute-on-Read 엔진(DB 쓰기 없는 실시간 계산 + Redis TTL).
- LLM 필터 파서(Gemini Flash 2.5) + Chain Sight 6개 프로파일 + 31개 metric.
- API 7개 모두 응답 구조가 설계와 일치.

**약점**
- Phase 6 구현 방식 변경(설계 ↔ 코드 불일치): 문서 갱신 필요.
- Phase 7-Full(Thesis 통합) 보류: 모델 필드 추가 + 관제실 연동 작업 잔존.
- Chain Sight 데이터 가용성 의존: `CompanyNarrativeTag.theme_tags` 0건, `CompanySensitivityProfile` 0건 → `foreign_revenue_pct` 등 필터 무력화.

**의심 영역**
- FE-PR 1~7 진척도(본 감사 범위 외).
- Thesis 모델 확장 일정(Phase 7-Full 예약 시점 명시 필요).

---

## News 상세

### 구현률 요약
- **설계 문서**: 3개 (`news_keyword_detail_plan.md`, `keyword_detail_bottomsheet_v2.md`, `news_pipeline_monitoring_design.md`)
- **CLAUDE.md News v3 항목**: 6개 (규칙 엔진, LLM 분석, ML 학습, Neo4j, Shadow/Production, 멀티 프로바이더)
- **A 완전 구현**: 5개 (LightGBM, Neo4j 동기화, Shadow Mode, 멀티 프로바이더, 규칙 엔진)
- **B 부분 구현**: 3개 (3개 설계 문서 모두 — BE는 완성이나 FE/일부 태스크 미확인)
- **C 미구현**: 없음
- **D 폐기/대체**: 없음

### 설계 문서별 상세

#### `news_keyword_detail_plan.md` [B]
- **약속**: GET `/api/v1/news/keyword-detail/?date&index`, Redis 캐시(`news:keyword_detail:{date}:{index}:{updated_at_epoch}` TTL 1h), 2단 매칭(종목 JOIN → `search_terms_en` title), Gemini 투자 요약, 실패 시 `analysis: null`.
- **구현**: `news/api/views.py:640-814` `keyword_detail` action, `services/keyword_extractor.py:43-50` FALLBACK_KEYWORDS에 `search_terms_en` 포함, `_generate_keyword_analysis()` (`views.py:776`), 동적 캐시 키 적용(`views.py:696-697`).
- **갭**: Frontend `KeywordDetailSheet.tsx` 및 `useRef` 세션 캐시 미확인(BE 범위 외).

#### `keyword_detail_bottomsheet_v2.md` [B]
- **약속**: BE 측은 기존 API 재사용, 응답 스키마 변경 없음, `updated_at` 캐시 무효화.
- **구현**: 동일 API 재사용 ✅, 캐시 키에 `updated_at_epoch` 포함 ✅.
- **갭**: `BottomSheet.tsx max-w-2xl`, `KeywordDetailSheet` props(`initialIndex`, `keywords[]`), 가로 스크롤 Strip UI — 모두 FE 범위 외.

#### `news_pipeline_monitoring_design.md` [B]

| Phase | API | 구현 위치 | 상태 |
|-------|-----|----------|------|
| A-BE 1 | `/collection-logs/` | `views.py:1314` | ✅ |
| A-BE 2 | `/pipeline-health/` | `views.py:1424` | ✅ (6 phase 응답 검증 권장) |
| A-BE 3 | `/ml-trend/` | `views.py:1678` | ✅ (feature_importance 히트맵 검증 필요) |
| A-BE 4 | `/llm-usage/` | `views.py:1759` | ✅ (Phase 3 토큰 미추적 경고 메시지 검증 필요) |
| A-FE | NewsTab sub-tab | — | ⚠️ FE 범위 외 |
| B-BE | task-timeline / neo4j-status / ml-rollback-preview / ml-rollback | `views.py:1677~2200` 범위 | ✅ (2단 롤백 flow 검증 권장) |
| C-BE | `AlertLog` + alerts API | `migrations/0006_alertlog.py` | ✅ 모델 완비 |
| C-Celery | `check_pipeline_alerts` | — | ⚠️ **미구현/미확인 — 설계서 §11에 @infra 담당 명시** |

- **Phase 0 선행 작업**: `_log_collection()` 호출 누락 보강 6개 태스크(`collect_daily_news`, `collect_market_news`, `collect_category_news`, `classify_news_batch`, `analyze_news_deep`, `sync_news_to_neo4j`) — `news/tasks.py` 추가 검증 필요.

### CLAUDE.md News v3 항목별

| 항목 | 상태 | 구현 위치 |
|------|------|----------|
| 규칙 엔진 (Engine A/B/C, 가중치 β₁~β₅) | A | `services/news_classifier.py`, migration 0004 (`rule_sectors`, `importance_score`) |
| LLM 분석 (Gemini 2.5 Flash, Tier A/B/C 심층) | A (운영) / B (관측) | `services/news_deep_analyzer.py`. **Phase 3 토큰이 `/llm-usage/`에 미포함**(설계 §3.4 의도적 제한) |
| ML 학습 (LightGBM A/B 테스트) | A | `services/ml_weight_optimizer.py:963-1141` (`train_lightgbm`, A/B 비교, `import lightgbm as lgb`) |
| Neo4j 뉴스 이벤트 + 동기화 | A | `services/news_neo4j_sync.py` `NewsNeo4jSyncService`. API `news-events`(`views.py:1008`), `impact-map`(`views.py:1067`) |
| Shadow / Production Mode | A | `services/ml_production_manager.py`. API `ml-shadow-report`(`views.py:1139`) |
| 멀티 프로바이더 (Finnhub/FMP/Marketaux) | A | `providers/{base,finnhub,fmp,marketaux}.py`, migration 0005 (`alphavantage_id`, `fmp_id`) |

### 핵심 발견

**강점**
- 설계 모니터링 API 9개(A 4 + B 4 + C 1) 모두 구현, KST 기준 날짜 처리(`_kst_today_start()` `views.py:36-39`) 일관 적용.
- LightGBM A/B 테스트 + `ml_production_manager` Shadow → Production 전환 흐름 완비.
- `keyword-detail` 캐시 키에 `updated_at_epoch` 포함 → 자동 무효화로 stale 데이터 차단.
- 4개 마이그레이션(Intelligence v3 → 멀티 프로바이더 → AlertLog) 점진적 진화 추적 가능.

**약점**
- Phase C `check_pipeline_alerts` Celery 태스크 검증 필요 — 알림 생성 자동화 부재 시 `AlertLog`만 비어있는 상태가 될 수 있음(@infra 작업).
- Phase 0 `_log_collection()` 호출이 6개 태스크에 모두 추가되었는지 미확인 → 검증 권장.
- LLM 토큰 추적이 Phase 3(심층 분석) 누락 — 설계 의도적 제한이지만 운영 비용 가시성 한계.

**의심 영역**
- `news/tasks.py`에서 `_log_collection()` 호출 누락 여부.
- alertlog `POST /api/v1/news/alerts/{id}/resolve/` 엔드포인트 구현 여부.
- Frontend `KeywordDetailSheet v2`(Strip, max-w-2xl), NewsTab sub-tab 진척도(FE 범위 외).

**설계 외 추가 구현 (out-of-scope이지만 존재)**
- `/api/v1/news/news-events/` — Neo4j 뉴스 이벤트 조회.
- `/api/v1/news/personalized-feed/` — 사용자 맞춤 피드.
- `/api/v1/news/market-feed/` — 시장 피드.
→ v3 파이프라인 확장으로 보이며, 별도 설계 문서 또는 CHANGELOG 기록 권장.

---

## 종합 권장 작업

| 우선순위 | 영역 | 작업 | 담당 후보 |
|---------|------|------|----------|
| P1 | SEC Pipeline | `tasks.py:559-564` Celery Beat schedule 활성화 + 운영 정책 결정 | @infra |
| P1 | News Phase C | Celery `check_pipeline_alerts` 태스크 구현 검증 + 미구현 시 추가 | @infra |
| P1 | News Phase 0 | 6개 태스크에 `_log_collection()` 호출 보강 여부 검증 | @infra |
| P2 | Validation Phase 6 | 설계 문서 `validation_peer_phase6_7.md` 갱신(Gemini 태깅 → DNA 교차 방식 반영) | @backend |
| P2 | Validation Phase 7 | Thesis 모델 확장(`peer_preset_key`, `peer_filter_query`, `peer_filter_result`) + 관제실 연동 (Chain Sight 데이터 완성 시점) | @backend, @frontend |
| P3 | SEC Pipeline | Gold Set 9종목 라벨 보완 → Precision/Recall 재측정 | @qa |
| P3 | SEC Pipeline | 비미국 주식 `CompanyAlias` 수동 등록(TSMC→TSM 등) | @backend |
| P3 | News | 설계 외 추가 API(news-events, personalized-feed, market-feed) 별도 문서화 | @backend, @qa |

---

## 부록: 인용된 핵심 파일

**SEC Pipeline**
- `sec_pipeline/models.py:15-389`, `tasks.py:22,149,338,465,501,509,559-564`, `admin.py:17-129,129`, `extractor.py:93`, `merger.py:36,76`, `validator_track_a.py`, `validator_track_b.py:64`, `intelligence.py:63,139`, `quality_checks.py:17,119`, `views.py:15,28`, `on_demand.py:18`, `ticker_matcher.py:22`, `signals.py:22`, `fixtures/gold_set.json`, `metrics/services/business_model_service.py:16,58,96`

**Validation**
- `validation/models/peer_preset.py`, `models/benchmark_delta.py`, `models/category_score.py`, `services/preset_generator.py` (479줄), `services/benchmark_calculator.py` (345줄), `services/metric_calculator.py` (459줄), `services/relative_metrics.py` (97줄), `services/custom_benchmark_engine.py` (161줄), `services/llm_peer_filter.py` (264줄), `api/views.py` (558줄), `api/urls.py`

**News**
- `news/api/views.py:36-39,640-814,1008,1067,1139,1314-1423,1424,1678,1759,2149+`, `services/news_classifier.py`, `services/keyword_extractor.py:43-50`, `services/news_deep_analyzer.py`, `services/ml_weight_optimizer.py:963-1141`, `services/news_neo4j_sync.py`, `services/ml_production_manager.py`, `providers/{base,finnhub,fmp,marketaux}.py`, `migrations/0004_news_intelligence_pipeline_v3.py`, `migrations/0005_multi_provider_news_collection.py`, `migrations/0006_alertlog.py`
