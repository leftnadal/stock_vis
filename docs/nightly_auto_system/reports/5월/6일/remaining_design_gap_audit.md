# SEC Pipeline + Validation + News 설계 갭 감사

**작성일**: 2026-05-07
**범위**: 읽기 전용 감사 (코드 수정 없음)
**대상**:
- `docs/sec_pipeline/` vs `sec_pipeline/`
- `docs/first_validation_system/` vs `validation/`
- `docs/news/` vs `news/`

---

## 앱별 요약 (구현률)

| 앱 | 설계 단위 | 완전(A) | 부분(B) | 미구현(C) | 폐기(D) | 구현률 |
|----|-----------|---------|---------|-----------|---------|--------|
| **SEC Pipeline** | 17 PR | 16 | 1 | 0 | 0 | **94.1%** |
| **Validation** | 7 Phase | 7 | 0 | 0 | 0 | **100%** (BatchJobRun 모델만 미생성) |
| **News (Pipeline v3)** | 6 컴포넌트 + 10+ API | 모든 코어 ✅ | LightGBM 배포 미확인 | 0 | 0 | **~95%** |

**한 줄 요약**:
- SEC Pipeline: 코드는 완성, **Celery Beat 스케줄이 주석 처리되어 자동화 미가동**.
- Validation: Phase 1~7 전 단계 완전 구현. `BatchJobRun` 모델만 설계상 누락.
- News: 6단계 Pipeline + Phase A/B/C API 모두 구현. 다만 **CLAUDE.md "테스트 607개" 주장 vs 실제 ~390개**, LightGBM 실제 배포 흔적 불명확.

---

## SEC Pipeline 상세

### 입력 자료
- `docs/sec_pipeline/decisions/001_fmp_vs_sec_edgar_metadata.md` (1건)
- `docs/sec_pipeline/task_done/` (PR 1~17 + complete summary, 총 16건)
- 구현: `sec_pipeline/` (models, collector, extractor, intelligence, merger, normalizer, ticker_matcher, on_demand, sp500, validator_track_a/b, keywords_track_b, quality_checks, prompts, tasks, signals, urls, views, management/, migrations/, fixtures/, tests.py)

### PR별 매핑

| PR | 제목 | 분류 | 근거 | 비고 |
|----|------|------|------|------|
| SEC-PR-1 | 모델 + migration | A | `models.py` 8개 모델 + `0001_initial` | ✓ |
| SEC-PR-2 | SEC EDGAR 수집기 | A | `collector.py` SECFilingCollector | ✓ |
| SEC-PR-3 | Track A 추출 | A | `normalizer.py` + `extractor.py` + `validator_track_a.py` | ✓ |
| SEC-PR-4 | Celery + 예외 | A | `tasks.py` 9개 함수, `exceptions.py` 4개 클래스 | ✓ |
| SEC-PR-5 | Gold Set | A | `fixtures/` + `evaluate_gold_set.py` 관리 명령 | ✓ |
| SEC-PR-6 | Phase 1 배치 | A | 15종목 완료, evidence 110건 | 운영 데이터 존재 |
| SEC-PR-7 | TickerMatcher | A | `ticker_matcher.py` 3단계 매칭 | 매칭률 2/66은 데이터 이슈 |
| SEC-PR-8 | Admin + signal | A | `admin.py` 8개 Admin, `signals.py` | ✓ |
| SEC-PR-9 | Neo4j sync | A | `sync_dirty_to_neo4j` DELETE+CREATE 패턴 | dirty flag 채택 |
| SEC-PR-10 | 관계 병합 | A | `merger.py` + `process_unmatched_queue.py` | ✓ |
| SEC-PR-11 | Track B 키워드 | A | `keywords_track_b.py` 5개 필드 | ✓ |
| SEC-PR-12 | Track B Gemini | A | `extract_business_model()` + `validator_track_b.py` | ✓ |
| SEC-PR-13 | 서비스 레이어 | A | `metrics/services/business_model_service.py` for_api 게이트 | 숫자 노출 경계 ✓ |
| SEC-PR-14 | 대시보드 | A | `quality_checks.py` + templates + urls | ✓ |
| SEC-PR-15 | On-demand | A | `on_demand.py` + `FilingDataView` (`filing/<symbol>/`) | ✓ |
| SEC-PR-16 | Intelligence | A | `intelligence.py` 5차원 분석 | ✓ |
| SEC-PR-17 | E2E + Beat | **B** | `generate_intelligence_report` 구현 ✓, **`config/celery.py` CELERY_BEAT_SCHEDULE 주석** ⚠ | **자동화 미가동** |

### 핵심 갭

1. **Celery Beat 미활성화 (가장 큰 운영 갭)**
   - 설계: 매 시간 `check_new_filings`, 매일 `generate_intelligence_report` 자동 실행
   - 실제: 태스크 함수는 존재하지만 `config/celery.py`에서 Beat 스케줄 주석 처리
   - 영향: 신규 filing 자동 감지 + 정기 지능 리포트 생성 미수행
   - 조치: `config/celery.py` 활성화 (CLAUDE.md 버그 #28과 연관 — DatabaseScheduler 사용 시 dict 무시되므로 PeriodicTask DB 등록 필요)

2. **Ticker 매칭 성공률 3% (운영 데이터 이슈)**
   - 결과: 2/66 매칭, 비미국 주식 미등록 + CompanyAlias 0건
   - 조치: CompanyAlias 수동 시드 또는 stocks DB 확장

3. **API 라우팅 검증 필요**
   - `sec_pipeline/urls.py` 정의 ✓, `config/urls.py`의 include 경로(`/api/v1/sec/`) 별도 검증 권장

### 통계
- 모델: 8개 / Celery 태스크: 9개 / Admin 클래스: 8개 / 마이그레이션: 2개
- 운영 데이터: RawDoc 15, Evidence 110, BusinessModel 5, UnmatchedQueue 60

---

## Validation 상세

### 입력 자료
- `docs/first_validation_system/validation_design.md` (메인)
- `docs/first_validation_system/validation_peer_system.md`
- `docs/first_validation_system/validation_peer_phase6_7.md`
- `docs/first_validation_system/validation_pr_prompts.md`
- `docs/first_validation_system/task_done/peer_phase6_thematic.md`, `peer_phase7_llm_filter.md`
- 구현: `validation/` (models/, services/, api/, tasks.py, migrations/, management/)

### Phase별 매핑

| Phase | 목표 | 분류 | 근거 | 비고 |
|-------|------|------|------|------|
| Phase 1 | default 프리셋 + 배치 | A | `PeerPreset(preset_key='default')`, `BenchmarkCalculator.select_peers()` | ✓ |
| Phase 2 | sector_all, size_peers | A | `preset_generator.py`, PeerPreset 463개씩 | 총 2,282 프리셋 |
| Phase 3 | quality_top, lifecycle, confidence_score | A | `CategorySignal.score`, 신호등(green/yellow/red/gray) | ✓ |
| Phase 4 | UserPeerPreference + 프리셋 전환 API | A | `models.py`, `api/views.py` 5개 엔드포인트 | POST/DELETE ✓ |
| Phase 5 | 커스텀 모드 (Compute-on-Read) | A | `custom_benchmark_engine.py` + Redis (TTL 1h) | ✓ |
| Phase 6 | Thematic 프리셋 (LLM) | A | `_generate_thematic()` (GrowthStage×CapitalDNA), 463개 | ✓ |
| Phase 7 | LLM 대화형 필터 | A | `llm_peer_filter.py` + `LLMPeerFilterView` (POST `/llm-filter/`) | ✓ |

### 모델 (5개)
`CompanyMetricLatest`, `CompanyBenchmarkDelta`, `CategorySignal`, `PeerPreset`, `UserPeerPreference`

### 서비스 (9개)
`benchmark_calculator`, `category_signal_calculator`, `metric_calculator`, `financial_fetcher`, `custom_benchmark_engine`, `preset_generator`, `llm_peer_filter`, `relative_metrics`, `interpretation`

### API (6개 엔드포인트)
1. `GET /summary/`
2. `GET /metrics/?category=`
3. `GET /leader-comparison/`
4. `GET /presets/`
5. `POST/DELETE /peer-preference/`
6. `POST /llm-filter/`

### 핵심 갭

1. **`BatchJobRun` 모델 미생성 (경미)**
   - 설계: 배치 실행 로그용 DB 모델 정의
   - 실제: `tasks.py`에 기본 logging만, DB 모델 없음
   - 영향: 배치 실행 이력을 DB로 추적 불가 (현재는 로그 파일만)

2. **`MetricDefinition`, `CompanyMetricSnapshot`은 metrics 앱으로 분리됨 (정상)**
   - 설계 의도가 "validation 앱 단독"이었다면 분리는 의도적 수정으로 해석
   - CLAUDE.md에도 metrics 앱이 별도로 명시되어 있어 분리가 옳은 선택

### 마이그레이션
- 4개 (`0001_initial`, `0002_validation_news_summary_category_score`, `0003_benchmark_delta_extension`, `0004_category_signal_unique_together`) — 총 ~275줄

### CLAUDE.md 주장 검증
> "1차 검증 (Peer 비교, 프리셋, LLM 필터) 완료" — **검증 통과**

---

## News 상세

### 입력 자료
- `docs/news/plan/news_pipeline_monitoring_design.md` (44KB 메인)
- `docs/news/plan/news_keyword_detail_plan.md`
- `docs/news/plan/keyword_detail_bottomsheet_v2.md`
- `task_done/` 디렉토리 없음 — CLAUDE.md "Pipeline v3 완료, 테스트 607개" 명시
- 구현: `news/` (models, providers, services, api, tasks, migrations)

### Pipeline v3 컴포넌트별 매핑

| 컴포넌트 | 분류 | 근거 | 비고 |
|---------|------|------|------|
| 규칙 엔진 (Engine A/B/C) | A | `services/news_classifier.py` (계산 + 종목 매칭 + 섹터) | Phase 2 |
| LLM 심층 분석 (Gemini) | A | `services/news_deep_analyzer.py` (Tier A/B/C) | Phase 3 |
| ML 학습 (Logistic Regression) | A | `services/ml_weight_optimizer.py` (f1_score 가중치) | Phase 5 |
| Neo4j 뉴스 이벤트 | A | `services/news_neo4j_sync.py` | Phase 4 |
| Shadow/Production Mode | A | `services/ml_production_manager.py` (shadow_comparison, safety_gate) | Phase 5 |
| LightGBM 전환 | **B** | `run_lightgbm_pipeline()` 메서드 + readiness 체크 존재, **실제 배포 흔적 미확인** | Phase 6 |

### 백엔드 API 매핑 (설계 vs 구현)

**Phase A — 4개 코어 API** (모두 ✅ 구현):
| API | 위치 |
|-----|------|
| `collection-logs` | `views.py:1314` |
| `pipeline-health` | `views.py:1424` |
| `ml-trend` | `views.py:1678` |
| `llm-usage` | `views.py:1758` |

**Phase B — 4개 고급 API** (모두 ✅ 구현):
| API | 위치 |
|-----|------|
| `task-timeline` | `views.py:1878` |
| `neo4j-status` | `views.py:1939` |
| `ml-rollback-preview` | `views.py:2000` |
| `ml-rollback` | `views.py:2040` |

**Phase C — 알림 시스템** (모두 ✅ 구현):
| API | 위치 |
|-----|------|
| `alerts` | `views.py:2085` |
| `alerts/{id}/resolve` | `views.py:2149` |

**기타 기존 API**: `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`

### 키워드 디테일 화면 (설계 vs 구현)

| 구성 | 분류 | 근거 |
|------|------|------|
| 백엔드 API | A | `keyword_detail()` @action (`views.py:640`) |
| 컴포넌트 | A | `KeywordDetailSheet.tsx` + `DailyKeywordCard.tsx` |
| 훅 | A | `useKeywordDetail()` in `useNews.ts` |
| 서비스 | A | `getKeywordDetail()` in `newsService.ts` |

### 데이터 모델 (9개)
`NewsArticle`, `NewsEntity`, `EntityHighlight`, `SentimentHistory`, `DailyNewsKeyword`, `MLModelHistory`, `NewsCollectionLog`, `NewsCollectionCategory`, `AlertLog`

### 통계
- Celery 태스크: 18개 (6단계 파이프라인)
- 마이그레이션: 6개 (`0006_alertlog.py` 포함)
- 코드 라인: 4,343줄 (models 727 + views 2,183 + tasks 1,433)

### 테스트 커버리지 검증

| 카테고리 | 파일 수 | 추정 케이스 |
|---------|---------|------------|
| `tests/news/` | 5 | ~150 |
| `tests/unit/news/` | 6 | ~120 |
| `tests/serverless/` (뉴스 카테고리) | 1 | ~40 |
| `tests/marketpulse/` (뉴스 연관) | 3 | ~80 |
| **합계** | **15** | **~390** |

⚠ **CLAUDE.md "테스트 607개" 주장 vs 실제 ~390개** — 마크다운에 오버스테이트 가능성. 실제 pytest 실행 카운트로 재확인 필요.

### 핵심 갭

1. **LightGBM 실제 배포 미확인 (B)**
   - 설계: Phase 6에서 LogReg → LightGBM 전환
   - 실제: `run_lightgbm_pipeline()` 메서드 + readiness 체크는 존재. 운영 환경 실제 배포 여부 불명
   - 조치: `ml-lightgbm-readiness` 엔드포인트 응답 + MLModelHistory 최신 레코드 확인 필요

2. **테스트 카운트 불일치 (경미)**
   - CLAUDE.md 607개 vs 실제 파일 추정 ~390개
   - 조치: `pytest --collect-only tests/` 실제 카운트로 CLAUDE.md 갱신

3. **`_log_collection()` 호출 누락 여부 (확인 필요)**
   - 설계서 §11이 "선행 작업: 6개 누락 태스크에 `_log_collection()` 추가" 언급
   - 실제 추가 여부는 본 감사 범위에서 미확인

---

## 종합 권장 조치 (우선순위 순)

| # | 우선순위 | 조치 | 영향 앱 |
|---|---------|------|---------|
| 1 | 🔴 High | `config/celery.py` Celery Beat 스케줄 활성화 (PR-17) | SEC Pipeline |
| 2 | 🟡 Med | `CompanyAlias` 시드 데이터 입력 (매칭률 3% → 개선) | SEC Pipeline |
| 3 | 🟡 Med | LightGBM 실제 배포 여부 검증 + 문서화 | News |
| 4 | 🟢 Low | `BatchJobRun` 모델 추가 (또는 설계서에서 폐기 처리) | Validation |
| 5 | 🟢 Low | CLAUDE.md 테스트 카운트 갱신 (607 → 실제값) | News |
| 6 | 🟢 Low | `/api/v1/sec/*` 라우팅 실제 검증 | SEC Pipeline |

---

## 결론

세 앱 모두 **설계서 대비 코드 구현은 거의 완성** 상태이며, 미구현(C) 항목은 없음. 부분 구현(B)으로 분류된 항목은 모두 **운영/배포 차원의 활성화 누락**(Celery Beat, LightGBM 배포)이지 코드 작성 미완료가 아님.

가장 즉각적 조치가 필요한 항목은 **SEC Pipeline의 Celery Beat 활성화**로, 이는 자동화된 신규 filing 감지 및 일일 리포트 생성을 가동하는 운영 작업.
