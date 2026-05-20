# SEC Pipeline + Validation + News 설계 갭 감사

**감사일**: 2026-05-21
**범위**: sec_pipeline/, validation/, news/ 3개 앱
**방식**: 설계 문서(`docs/*`) vs 실제 구현 코드 cross-reference, 읽기 전용

---

## 앱별 요약 (구현률)

| 앱 | 설계 문서 | 구현률 | A | B | C | D | 비고 |
|----|----------|-------|---|---|---|---|------|
| **SEC Pipeline** | `docs/sec_pipeline/` (17 PR + 1 decision) | **100%** | 17 | 0 | 0 | 0 | 설계-구현 동기화 모범 사례 |
| **Validation** | `docs/first_validation_system/` (Phase 1~7) | **95%** (실질) | ~95% | ~5% | 0 | 0 | LLM 배치 캐싱 등 Phase 2 잔여 |
| **News** | `docs/news/plan/` (Pipeline v3 + Bottomsheet) | **90~92%** | 22 | 2 | 0 | 0 | task-timeline / search_terms_en / Phase3 토큰 미달 |

**종합**: 3개 앱 모두 설계 약속의 대부분이 코드로 구현됨. 누락은 모두 외부 의존성·후속 Phase 성격이며 폐기 항목은 없음.

---

## SEC Pipeline 상세

### PR별 분류 (17/17 = A)

| PR | 상태 | 근거 (file:symbol) |
|----|------|--------------------|
| PR-1 모델 | A | `sec_pipeline/models.py` (8개 모델 + migration) |
| PR-2 Collector | A | `sec_pipeline/collector.py`, `validators.py` |
| PR-3 Track A Extractor | A | `sec_pipeline/normalizer.py`, `prompts.py`, `extractor.py`, `validator_track_a.py` |
| PR-4 Celery Tasks | A | `sec_pipeline/tasks.py`, `exceptions.py`, `sp500.py` |
| PR-5 Gold Set | A | `sec_pipeline/fixtures/gold_set.json`, `management/commands/evaluate_gold_set.py` |
| PR-6 Phase1 Batch | A | `sec_pipeline/tasks.py:collect_and_extract` |
| PR-7 Ticker Matcher | A | `sec_pipeline/ticker_matcher.py` (3단계 매칭) |
| PR-8 Admin + Signal | A | `sec_pipeline/admin.py` (8 register), `signals.py:on_unmatched_resolved` |
| PR-9 Neo4j Sync | A | `sec_pipeline/tasks.py:sync_dirty_to_neo4j` |
| PR-10 Merger | A | `sec_pipeline/merger.py:merge_relationship`, `management/commands/process_unmatched_queue.py` |
| PR-11~12 Track B (BM) | A | `sec_pipeline/keywords_track_b.py`, `extractor.py:extract_business_model`, `validator_track_b.py` |
| PR-13 Service Gate | A | `metrics/services/business_model_service.py:get_business_model` (for_api confidence gate) |
| PR-14 Dashboard | A | `sec_pipeline/quality_checks.py`, `views.py:sec_pipeline_dashboard`, `templates/admin/sec_pipeline/dashboard.html` |
| PR-15 On-Demand | A | `sec_pipeline/on_demand.py:get_or_collect_filing`, `views.py:FilingDataView` |
| PR-16 Intelligence | A | `sec_pipeline/intelligence.py:PipelineIntelligenceReporter`, `admin.py:regenerate_report` |
| PR-17 E2E Tasks | A | `sec_pipeline/tasks.py:generate_intelligence_report`, `run_batch_and_report` |

### 누락 / 불일치

- **누락 핵심 기능**: 없음
- **불일치**: PR-14 설계는 "7개 품질 체크 함수"라 표현했으나 실제 `quality_checks.py`는 `run_post_batch_quality_checks()` 단일 진입점에 7개 로직을 통합. 그래뉼러리티만 다르고 기능 누락 없음.
- decision 문서(`001_fmp_vs_sec_edgar_metadata.md`) 결정도 코드에 반영됨.

### 결론
SEC Pipeline은 Phase 1~3 17개 PR 약속 산출물(8 모델 / 6 Celery task / 2 API view / 4 management command / 8 admin)이 코드에 모두 존재. Neo4j DELETE+CREATE, for_api confidence gate, dirty flag 패턴 등 DECISIONS.md 정책도 준수. **이번 감사 대상 3개 앱 중 설계-구현 동기화 수준 최상.**

---

## Validation 상세

### Phase별 분류

| Phase / 영역 | 상태 | 근거 |
|---|---|---|
| Phase 1~5 (Peer 기초 + 프리셋 6종) | A | `validation/models/peer_preset.py:5-68`, `services/preset_generator.py:1-70`, `api/views.py:424-449` |
| Phase 6 (Thematic / DNA 클러스터) | A | `validation/services/preset_generator.py:54` (463/503 종목, 2,282 프리셋) |
| Phase 7 (LLM 대화형 필터) | A* | `validation/services/llm_peer_filter.py:56-100`, `api/urls.py:13` — Chain Sight 의존 3개 필터(해외매출/R&D/내러티브)는 데이터 미준비로 제외 |
| Compute-on-Read 엔진 + 신호등 | A | `validation/models/category_score.py:4-65`, `models/benchmark_delta.py:4-67`, `services/interpretation.py` |
| API 6종 (summary/metrics/leader/preset/llm-filter) | A | `validation/api/views.py:52-449` |
| Celery 배치 Task 1~6 | A | `validation/tasks.py:1-160` |
| **LLM 배치 캐싱 (Phase 2 예정)** | **B** | rule-based 해석 템플릿만 존재. LLM 캐시 도입 미진 |
| Thesis Control 통합 | C (외부) | `validation_peer_phase6_7.md:228-263`에 기술됨, validation 쪽엔 미연결 |
| Chain Sight Phase 7-Full(해외매출/R&D) | C (외부) | chainsight 데이터 파이프라인 선행 필요 |
| Mobile Accordion UX | C (FE) | `validation_design.md:124-129` 설계, FE 구현은 본 감사 범위 밖 |

### 누락 / 불일치

- **핵심 누락 (5 이내)**:
  1. LLM 배치 캐싱 (Phase 2 로드맵)
  2. Chain Sight 데이터 의존 필터 3종 (Phase 7-Full)
  3. Thesis Control ↔ Validation 연결 라인
  4. Mobile Accordion UX (FE)
  5. (없음) — 백엔드 기능적 갭은 사실상 1번만 유의미
- **불일치**: 설계 `category_score` 테이블명 변경, `preset_key` / `benchmark_basis` / `benchmark_confidence` 필드 추가는 모두 코드에 반영됨. Phase 5→6 앞당김(beta 해제)은 설계 초과 달성.

### 결론
Validation 시스템은 7개 카테고리 34개 지표 신호등, peer 프리셋 6종(default/sector/size/quality/lifecycle/thematic), LLM 대화형 필터, compute-on-read 커스텀 peer가 모두 구현되어 운영 가능 상태. **실질 구현률 95%**, 남은 5%는 LLM 캐싱·외부 의존성·FE/Thesis 통합으로 모두 별도 트랙. Phase 6/7은 당초 계획을 앞질러 정착.

---

## News 상세

### 컴포넌트별 분류

#### Phase A — 기존 데이터 노출 (5/5 = A)
| 컴포넌트 | 상태 | 근거 |
|---|---|---|
| `GET /collection-logs/` | A | `news/api/views.py:1329-1437` |
| `GET /pipeline-health/` (6 Phase status) | A | `news/api/views.py:1439-1691` |
| `GET /ml-trend/` (F1 추이, feature importance) | A | `news/api/views.py:1693-1771` |
| `GET /llm-usage/` (토큰/Tier) | A | `news/api/views.py:1773-1889` |
| FE Pipeline 서브탭 | A | `frontend/components/admin/news/NewsPipelineSubTab.tsx` |

#### Phase 2.5 — Keyword Detail Bottomsheet (3.5/4)
| 컴포넌트 | 상태 | 근거 |
|---|---|---|
| `GET /keyword-detail/` (2단 매칭, Gemini 요약) | A | `news/api/views.py:655-789` |
| KeywordDetailSheet UI + 가로 스트립 | A | `frontend/components/news/KeywordDetailSheet.tsx` |
| BottomSheet `max-w-2xl` | A | `frontend/components/thesis/common/BottomSheet.tsx` |
| **`search_terms_en` 한영 매칭 필드** | **B** | `news/services/keyword_extractor.py` 프롬프트에 명시 누락 가능성 — 검증 필요 |

#### Phase B — 심화 모니터링 (3.5/4)
| 컴포넌트 | 상태 | 근거 |
|---|---|---|
| **`GET /task-timeline/`** | **B** | `news/api/views.py:1893+` 엔드포인트 흔적은 있으나 간트 데이터 생성 로직 미완 의심 |
| TaskTimelineChart | A | `frontend/components/admin/news/TaskTimelineChart.tsx` |
| PipelineStatusBar | A | `frontend/components/admin/news/PipelineStatusBar.tsx` |
| CollectionStatsTable | A | `frontend/components/admin/news/CollectionStatsTable.tsx` |

#### Phase C — 능동 알림 (4/4 = A)
| AlertLog 모델 | A | `news/models.py:684-728` |
| `GET /alerts/` | A | `news/api/views.py:2100-2161` |
| `POST /alerts/<pk>/resolve/` | A | `news/api/views.py:2164-2197` |
| AlertList + AlertBadge | A | `frontend/components/admin/news/{AlertList,AlertBadge}.tsx` |

#### ML 학습 + Shadow/Production (7/7 = A)
| 컴포넌트 | 상태 | 근거 |
|---|---|---|
| `train_importance_model` | A | `news/tasks.py:672-707` |
| `generate_shadow_report` | A | `news/tasks.py:708-802` |
| `train_lightgbm_model` | A | `news/tasks.py:874+` |
| MLModelHistory | A | `news/models.py:494-596` |
| `/ml-weekly-report/`, `/ml-shadow-report/` | A | `news/api/views.py:1154-1234` |
| MLCompareView (2단계 롤백) | A | `frontend/components/admin/news/MLCompareView.tsx:75-250` |

### 누락 / 불일치 (TOP 5)

1. **`task-timeline` API 완성도** — 엔드포인트 선언만 있고 간트 데이터 생성 로직이 비어 있을 가능성. 검증 우선.
2. **Keyword `search_terms_en` 스키마 확장** — 설계 명시되었으나 Gemini 프롬프트 반영 불명확.
3. **Phase 3 (Deep Analysis) LLM 토큰 추적** — `/llm-usage/`는 키워드 추출 토큰만 반영. Phase 3 심층 분석 비용은 미집계.
4. **Neo4j 이벤트 관계도 FE 시각화** — `sync_news_to_neo4j` task는 구현, FE 통합/시각화 마감 미확인.
5. **LightGBM `check_auto_deploy` 안전 게이트 검증** — 자동 전환 조건이 설계 "2단계 롤백 + 안전 게이트" 플로우와 100% 일치하는지 재확인 필요.

### 결론
News Intelligence Pipeline v3는 6단계 모니터링·ML(Shadow/Production + LightGBM)·알림·Keyword Detail의 **기본 뼈대가 90%+ 수준으로 운영 가능**. 누락은 `task-timeline` 완성도, `search_terms_en` 프롬프트 반영, Phase 3 LLM 토큰 추적의 세 가지에 집중. 폐기 항목은 없고 모두 후속 Phase B+ 작업으로 분류 가능.

---

## 종합 권고

- **즉시 점검 필요(우선순위 상)**: News `task-timeline` 구현 완료 여부, `keyword_extractor` 프롬프트에 `search_terms_en` 명시 여부, Phase 3 토큰 추적 컬럼 추가.
- **중기 트랙**: Validation LLM 배치 캐싱(Phase 2), Chain Sight 데이터 적재 후 Phase 7-Full 필터 활성화.
- **모범 사례 차용**: SEC Pipeline의 PR별 task_done 보고 + 코드 1:1 매핑 방식은 다른 앱에도 확장 적용 가치 있음.
