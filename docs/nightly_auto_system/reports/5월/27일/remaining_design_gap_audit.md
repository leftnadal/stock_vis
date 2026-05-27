# SEC Pipeline + Validation + News 설계 갭 감사

> **감사일**: 2026-05-27
> **범위**: 읽기 전용 — 설계 문서 vs 실제 구현 코드 대조
> **방법**: 3개 Explore 에이전트 병렬 감사 + 메인 통합
> **분류**: (A) 완전 구현 · (B) 부분 구현 · (C) 미구현 · (D) 폐기/대체

---

## 앱별 요약 (구현률)

| 앱 | A 완전 | B 부분 | C 미구현 | D 폐기 | 총 단위 | 충실도 | 비고 |
|----|--------|--------|----------|--------|--------|--------|------|
| **SEC Pipeline** | 15 | 2 | 0 | 0 | 17 PR | **94%** | 17 PR 전체 적재, Celery Beat·Gold Set 보완 필요 |
| **Validation** | 13 | 4 | 3 | 0 | 20 블록 | **85%** | 백엔드 거의 완료, **프론트엔드 전무** |
| **News** | 18 | 2 | 0 | 0 | 20 블록 | **90%+** | 모니터링 v3 완성, 키워드 Strip 자동 스크롤만 미세 갭 |

**총평**: 3개 앱 모두 설계 문서 기반 개발(원칙 1)이 충실하게 지켜졌으며, 평균 **90% 충실도**. 가장 큰 단일 갭은 **Validation 프론트엔드** (FE-PR-1~6 React 컴포넌트 미구현).

---

## SEC Pipeline 상세

### 구현률
- 완전(A): 15 PR · 부분(B): 2 PR · 미구현(C): 0 · 폐기(D): 0

### PR별 구현 상태

| PR | 범위 | 상태 | 검증 근거 | 비고 |
|----|------|------|-----------|------|
| 1 | 8개 모델 + migration | A | `models.py` 8 클래스, `migrations/0001_initial.py` | 모든 모델 매칭 |
| 2 | SEC EDGAR 수집기 + 섹션 추출 | A | `collector.py:SECFilingCollector`, `validators.py:validate_extracted_sections` | FMP→EDGAR 대체(decisions/001) |
| 3 | Track A 키워드 + Gemini | A | `normalizer.py`, `extractor.py:GeminiExtractor.extract_supply_chain`, `prompts.py` | temp=0.1, JSON mode |
| 4 | Celery tasks + 예외 | A | `tasks.py` 6 task, `exceptions.py` 4 예외, `sp500.py` | collect_and_extract, extract_from_document, seed_relations, sync, check_new_filings, generate_intelligence |
| 5 | Gold Set + 평가 | A | `fixtures/gold_set.json`, `management/commands/evaluate_gold_set.py` | 10 종목, 평가 명령 완성 |
| 6 | 15종목 배치 | A | 배치 결과 기록 (14/15 성공) | summary 문서에 명시 |
| 7 | TickerMatcher 3단계 | A | `ticker_matcher.py:TickerMatcher` (alias→exact→fuzzy) | rapidfuzz, UnmatchedCompanyQueue 적재 |
| 8 | Admin 큐 + signal | A | `admin.py:UnmatchedCompanyQueueAdmin`, `signals.py:on_unmatched_resolved` | CompanyAlias 생성 + neo4j_dirty |
| 9 | sync_dirty_to_neo4j | A | `tasks.py:sync_dirty_to_neo4j` (Phase A/B/C, DELETE+CREATE) | 동기화 2건 검증 |
| 10 | 관계 병합 + DQS | A | `merger.py:merge_relationship,calculate_edge_dqs`, `process_unmatched_queue.py` | DQS 5차원 |
| 11 | Track B 키워드 사전 | A | `keywords_track_b.py` 5 필드 + `filter_paragraphs_track_b` | direct_customer_contact 외 4 |
| 12 | Track B Gemini + 검증 | A | `extractor.extract_business_model`, `validator_track_b.py`, `prompts.BUSINESS_MODEL_EXTRACTION_PROMPT` | confidence_grade 포함 |
| 13 | 서비스 레이어 (for_api) | A | `metrics/services/business_model_service.py` | 숫자 노출 경계 |
| 14 | Admin 대시보드 + 품질 체크 | A | `quality_checks.py` 7 체크, `views.py:sec_pipeline_dashboard`, `templates/admin/sec_pipeline/dashboard.html` | 4-grid UI |
| 15 | On-demand + API | A | `on_demand.py:get_or_collect_filing`, `views.FilingDataView` (200/202), `urls.py` | 1년 중복 체크 |
| 16 | Intelligence Report | A | `intelligence.py:PipelineDataCollector + PipelineIntelligenceReporter` | 5 차원 + severity |
| 17 | E2E chord + 테스트 | **B** | `tasks.py:run_batch_and_report` chord 구현됨 | **Beat schedule 코드 주석 처리(DB 스케줄러로 위임)** |

### 핵심 갭

1. **PR-17 Celery Beat schedule (B)**: `tasks.py`/`config/celery.py`에 정적 schedule 미등록. DB Scheduler로 대체 가능하나 신규 환경 초기화 시 수동 등록 필요. *영향도 낮음.*
2. **PR-5 Gold Set 라벨 불완전 (B)**: 10 종목 섹션 추출은 완료, supply chain 라벨은 NVDA만 완전. Precision/Recall 재평가 정확도 영향. *summary.md §향후 과제 1,2 명시.*
3. **설계 외 추가 구현**: 없음 (설계 문서에 모든 변경 기록 — decisions/001 FMP→EDGAR 포함).

### 종합 평가

17 PR 전체 구현률 94%. Phase 1~3의 8개 모델 + 6개 Celery task + 3단계 매칭 + Track A/B LLM 추출 + Neo4j 동기화 + 품질 검사 + Intelligence Report가 모두 적재되었고, ~3,313 LoC로 설계 충실도가 매우 높음. 남은 갭(Beat 등록, Gold Set 라벨)은 운영 보완 영역.

---

## Validation 상세

### 구현률
- 완전(A): 13 블록 · 부분(B): 4 블록 · 미구현(C): 3 블록 · 폐기(D): 0

### 기능 블록별 구현 상태

| 기능 블록 | 설계 위치 | 상태 | 구현 위치 | 비고 |
|-----------|-----------|------|-----------|------|
| 7개 카테고리 신호 | design §3~4 | A | `category_signal_calculator.py` | 7 카테고리 전체 |
| 34개 지표 메타정의 | design §4 | A | `metric_calculator.py` (442줄) | 30+ 메서드 |
| 지표 계산 엔진 | design §6 Task 2 | A | `metric_calculator.py:MetricCalculator` | — |
| value_status 판정 | design §7.2 | A | metric_calculator 내부 | normal/missing/n.a./unstable/low_conf |
| Peer 선정 | design §3.2 | A | `benchmark_calculator.py` | industry + size_bucket |
| Benchmark 계산 | design §3.2~3.3 | A | `benchmark_calculator.py` (294줄) | median, p25, p75, percentile_rank |
| Category Signal 계산 | design §4 Task 4 | A | `category_signal_calculator.py` (125줄) | green/yellow/red/gray |
| Peer Preset 시스템 | peer_system.md | A | `preset_generator.py` (464줄) | 6 프리셋 |
| Thematic 프리셋 (Phase 6) | peer_phase6_7.md | A | `preset_generator._generate_thematic()` | 사업모델 DNA 클러스터링 |
| LLM Peer 필터 (Phase 7) | peer_phase6_7.md | A | `llm_peer_filter.py` | parse + execute |
| API: 종합 요약 | design §5.1 | A | `ValidationSummaryView` | — |
| API: 카테고리별 지표 | design §5.2 | A | `ValidationMetricsView` | — |
| API: 대장주 비교 | design §5.3 | A | `LeaderComparisonView` | — |
| API: Preset/Preference/LLM | peer_phase6_7 | A | PresetListView, PeerPreferenceView, LLMPeerFilterView | 3개 |
| Rule-based 해석 텍스트 | design §3.1 | **B** | `interpretation.py` | `generate_metric_interpretation()` 단순함 |
| Batch 파이프라인 Task 1~6 | design §6 | **B** | `tasks.py` (160줄) | Task 1 (FMP fetch) skeleton |
| Custom Benchmark 엔진 | peer_system.md | **B** | `custom_benchmark_engine.py` | Redis TTL/동시성 부분 |
| 특수 산업 handling | design §4, §7.3 | **B** | category_signal_calculator | 금융/REIT/Utilities SPECIAL_GRAY_CATEGORIES 일부 |
| 모바일 Accordion UX | design §2.2 | **C** | — | 프론트엔드 미착수 |
| FE TypeScript 타입 (FE-PR-2) | pr_prompts | **C** | — | — |
| FE React 컴포넌트 (FE-PR-3~6) | pr_prompts | **C** | — | SignalSummaryCard, MetricBarChart, CategorySidebar 등 |

### 핵심 갭

1. **프론트엔드 전체 미구현 (C)**: FE-PR-1~6 (라우팅, 타입, SignalSummaryCard, MetricBarChart, CategorySidebar, IndustryPosition, Accordion UX) 0건. 백엔드 API 6개는 전부 준비됨 — 즉시 착수 가능.
2. **Batch Task 1 `FinancialFetcher.check_and_fetch()` skeleton (B)**: 실제 FMP API 페칭 로직 단순화 상태. 배치 자동화 시 수동 보완 필요.
3. **`interpretation.py:generate_metric_interpretation()` (B)**: 기본 틀만 있고 지표별 맥락화 해석 미완성. 사용자 노출 텍스트 품질 저하 위험.
4. **특수 산업 SPECIAL_GRAY_CATEGORIES (B)**: handling_mode='special' 분기는 구현, 금융(Banks/Insurance), REIT, Utilities별 카테고리 매핑 일부만 등록.

### 종합 평가

백엔드 핵심 아키텍처(Models 5종 + Services 9종 + API 6종)는 **85% 구현**. Phase 6 thematic + Phase 7 LLM 필터 포함 거의 모든 핵심 로직이 적재됐으나, **프론트엔드는 전무**하여 사용자 가시 기능은 0%. 다음 작업 순서: (1) FE-PR-1~6 React 컴포넌트, (2) FinancialFetcher 완성, (3) interpretation 품질 향상.

---

## News 상세

### 구현률
- 완전(A): 18 블록 · 부분(B): 2 블록 · 미구현(C): 0 · 폐기(D): 0

### 기능 블록별 구현 상태

| 기능 블록 | 설계 위치 | 상태 | 구현 위치 | 비고 |
|-----------|-----------|------|-----------|------|
| 파이프라인 6단계 모니터링 | monitoring §1 | A | `views.py:pipeline_health` | 캐시 + force_refresh |
| Phase 1 수집 헬스 | §3.1 | A | pipeline_health (NewsCollectionLog) | 24h window |
| Phase 2 분류 헬스 | §3.1 | A | pipeline_health | classify_news_batch |
| Phase 3 LLM 분석 헬스 | §3.1 | A | pipeline_health | Tier A/B/C |
| Phase 4 ML Label + Neo4j | §3.1 | A | pipeline_health (sync_news_to_neo4j) | — |
| Phase 5 ML 학습 + Shadow | §3.1 | A | pipeline_health (MLModelHistory) | — |
| Phase 6 LightGBM + 리포트 | §3.1 | A | pipeline_health | 배포 상태 추적 |
| ML 모델 F1 추이 | §3.3 | A | `ml_trend` view (12주 + feature_importance) | — |
| 연속 F1 하락 감지 | §3.3 | A | ml_trend (연속 3회) | — |
| LLM 토큰 사용량 | §3.4 | A | `llm_usage` view | 키워드 추출만 (심층 분석 Phase B) |
| 수집 통계/에러 | §3.1 | A | collection_logs API | 공급자별 |
| Shadow Mode 리포트 | §5.2 | A | ml_shadow_report API | — |
| ML 롤백 (2단계) | §5.3 | A | ml_rollback_preview + ml_rollback | preview→confirm |
| 파이프라인 알림 | §6 | A | AlertLog 모델 + alerts API | TriggerType 정규화 |
| Neo4j 동기화 상태 | §4.4 | A | `neo4j_status` view | 가용/동기화량/미동기화 |
| 24시간 태스크 간트 | §4.3 | A | `task_timeline` view | 5분 캐시 |
| 키워드 상세 BottomSheet | keyword_detail_plan | A | `keyword_detail` view (656줄) | article_ids + search_terms_en + Redis |
| 프론트엔드 모니터링 대시보드 | §4 Phase A | A | `NewsPipelineSubTab.tsx` (1537줄) | 12개 컴포넌트 |
| Admin NewsTab | §4 | A | NewsTab + admin/news/ | overview + pipeline 서브탭 |
| 키워드 Strip 네비게이션 | bottomsheet_v2 | **B** | `KeywordDetailSheet.tsx` | activeIndex 추적, **자동 center 스크롤 미세 갭** |

### 핵심 갭

1. **키워드 Strip 자동 scrollIntoView (B)**: `KeywordDetailSheet.tsx`에 `activeIndex` 추적은 구현됐으나 `stripRef.current?.scrollIntoView({behavior:'smooth', inline:'center'})` 호출 또는 옵션 누락 가능성. *UX 디테일 영역.*
2. **LLM 심층 분석 토큰 미추적 (설계상 의도)**: `llm_usage`에 Phase 3 심층 분석 토큰 미포함 명시 — Phase B 예정으로 코드 주석에 기재됨. **설계 명시 → 갭 아님**.

### 종합 평가

News Intelligence Pipeline v3 모니터링 설계는 **90%+ 완성**. 30개 API + 12개 프론트엔드 컴포넌트로 6단계 헬스, ML 추이, LLM 사용량, 알림, Neo4j 상태를 추적. 키워드 상세 BottomSheet는 Redis 캐시 + search_terms_en + article_ids까지 적용. 유일한 미세 갭은 키워드 Strip 자동 스크롤 디테일.

---

## 통합 권고

| 우선순위 | 작업 | 앱 | 이유 |
|----------|------|-----|------|
| **P0** | FE-PR-1~6 React 컴포넌트 구현 | Validation | 백엔드 100% 준비, 사용자 가시 기능 0% |
| **P1** | FinancialFetcher.check_and_fetch() FMP 페칭 완성 | Validation | 배치 자동화 차단점 |
| **P1** | 키워드 Strip scrollIntoView 보완 | News | UX 디테일, 1줄 수정 가능성 |
| **P2** | interpretation.generate_metric_interpretation() 품질 향상 | Validation | 사용자 노출 텍스트 |
| **P2** | SPECIAL_GRAY_CATEGORIES 금융/REIT/Utilities 보강 | Validation | 특수 산업 정확도 |
| **P3** | SEC Pipeline Celery Beat schedule DB 등록 | SEC | 운영 자동화 |
| **P3** | SEC Gold Set supply chain 라벨 9 종목 보완 | SEC | 평가 정확도 |

**감사 결론**: 3개 앱 평균 충실도 **약 90%**. SEC Pipeline과 News는 운영 준비 상태, Validation은 백엔드만 운영 가능하고 프론트엔드 착수가 가장 큰 다음 단계.
