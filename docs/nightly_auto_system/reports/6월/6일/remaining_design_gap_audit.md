# SEC Pipeline + Validation + News 설계 갭 감사

> **작성일**: 2026-06-07
> **유형**: 읽기 전용 감사 (코드 수정 없음)
> **방법**: `docs/` 설계서 + `task_done/` 완료 보고서 vs `services/` 실제 구현 cross-reference
> **분류 기준**: (A) 완전 구현 · (B) 부분 구현 · (C) 미구현 · (D) 폐기/대체

> **중요 — 디렉토리 구조 주의**: 서비스 리모델링으로 실제 구현은 모두 `services/{app}/` 하위에 있다.
> 최상위 `sec_pipeline/`, `validation/`은 빈 스텁(파일 0개)이며, `news/`는 최상위에 존재하지 않는다.
> 본 감사는 **`services/sec_pipeline/`, `services/validation/`, `services/news/`** 를 대상으로 한다.

---

## 앱별 요약 (구현률)

| 앱 | 설계서 | 백엔드 구현률 | 종합 판정 | 핵심 갭 |
|----|--------|--------------|----------|---------|
| **SEC Pipeline** | Phase 1~3 (17 PR) | **~98%** | 🟢 사실상 완료 | 운영성 후속 과제만 잔존 (코드 갭 없음) |
| **Validation** | 메인 + Peer Phase 1~7 | **~88%** | 🟡 부분 갭 | 지표 3개 미구현 · Phase 7 Thesis 연동 미구현 · thematic 대체 구현 |
| **News** | 모니터링 + 콜드스타트 + 키워드상세 + Intelligence v3 | **~95%** (백엔드) | 🟢 백엔드 완료 | 프론트엔드 대시보드는 본 감사 범위 밖 (별도 확인) |

> **공통 주의**: News·Validation 설계서는 백엔드 + 프론트엔드를 함께 명세한다.
> 본 감사는 `services/*` **백엔드만** 검증했다. `frontend/` 컴포넌트 구현 여부는 별도 감사가 필요하다.

---

## SEC Pipeline 상세

### 설계서 vs 구현 매핑

설계서: `docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md` (Phase 1~3, 17 PR).
완료 보고서 17건(`sec_pr_1`~`sec_pr_17`)이 모두 존재하며, 실제 코드와 **거의 1:1로 일치**한다.

| 영역 | 설계 항목 | 구현 위치 | 분류 |
|------|----------|----------|------|
| 데이터 모델 (8개) | RawDocumentStore, SupplyChainEvidence, BusinessModelSnapshot, BusinessModelEvidence, FilingProcessLog, CompanyAlias, UnmatchedCompanyQueue, PipelineIntelligenceReport | `models.py` | **A** |
| SEC 수집 | EDGAR 메타데이터 + HTML + 섹션추출(regex 3단계 + edgartools fallback) | `collector.py` | **A** |
| 섹션 사후검증 | 순서/heading/길이 (FAIL/WARN) | `validators.py` | **A** |
| Track A (공급망) | Gemini 추출 → 검증(제네릭 필터 30개) → confidence_grade → 저장 | `extractor.py`, `validator_track_a.py`, `normalizer.py` | **A** |
| Track B (사업모델) | 5개 필드 분류 → 검증 → snapshot 저장 | `validator_track_b.py`, `keywords_track_b.py` | **A** |
| Ticker 매칭 | alias→exact→fuzzy(80%) + UnmatchedQueue(블록리스트 62개) | `ticker_matcher.py` | **A** |
| 관계 병합/DQS | RELATIONSHIP_SPECIFICITY + SOURCE_RELIABILITY + DQS | `merger.py` | **A** |
| Neo4j 동기화 | sync_dirty_to_neo4j (2-Phase, sole writer, DELETE+CREATE dynamic type) | `tasks.py` | **A** |
| Pipeline Intelligence | 5차원 수집 + Gemini LLM 리포트 + severity | `intelligence.py` | **A** |
| 품질 체크 | 7개 알림 + 대시보드 통계 | `quality_checks.py` | **A** |
| On-demand 수집 | 비-S&P500 1년 이내 확인 + 트리거 | `on_demand.py` | **A** |
| Celery 태스크 (7개) | collect/extract/seed/sync/check/intelligence/batch | `tasks.py` | **A** |
| Django Signal | UnmatchedQueue resolved → evidence 업데이트 + alias 등록 | `signals.py` | **A** |
| Admin (8개 모델) | 큐 관리(list_editable + 3 action), Intelligence Report | `admin.py` | **A** |
| API | Admin 대시보드 + On-demand filing(202) | `views.py`, `urls.py` | **A** |
| 서비스 레이어 | for_api 게이트 (원칙 6, confidence 노출 차단) | `metrics/services/business_model_service.py` | **A** |

### 잔존 갭 — 코드가 아니라 운영성 후속 과제

`sec_pipeline_complete_summary.md §향후 과제`에 명시된 5건은 **기능 미구현이 아니라 데이터/튜닝 작업**이다:

| # | 항목 | 분류 | 비고 |
|---|------|------|------|
| 1 | S&P 500 전체 배치 | 운영 | 코드 존재, Gemini RPD 제한으로 미실행 (15종목만 시험 배치) |
| 2 | Gold Set 라벨 보완 → Precision/Recall 재평가 | 운영/QA | `evaluate_gold_set` 커맨드 + fixture 존재 |
| 3 | JNJ Item 순서 검증 완화 | 튜닝 | validators.py 임계값 조정 사안 |
| 4 | 프롬프트 개선 (일반명사 추출 방지) | 튜닝 | `prompts.py` PROMPT_VERSION v1 |
| 5 | CompanyAlias 수동 등록 (TSMC→TSM 등) | 데이터 | 매칭률 2/110(3%)의 주원인 = 비미국 종목 미등록 |

> **시험 배치 실측치** (15종목): 수집 14/15(93%), Track A 110관계, Track B 5 snapshot, Ticker 매칭 2/110(3%), Neo4j 2건, Intelligence severity=critical(매칭률 기반).
> ⇒ 매칭률이 critical인 것은 **버그가 아니라 CompanyAlias 미등록 + 비미국 종목** 때문. 운영 데이터 채움으로 해소.

### SEC Pipeline 판정: 🟢 코드 완전 구현 (A). 미배포/미튜닝만 잔존.

---

## Validation 상세

### 설계서 구성
- `validation_design.md` (1646줄) — 메인 기능 (7 카테고리 × 34 지표, API, 배치, Phase 1~5)
- `validation_peer_system.md` (403줄) — Peer 프리셋 6종 + 커스텀 (Phase 1~7)
- `validation_peer_phase6_7.md` (382줄) — Thematic + LLM 대화형 + Thesis 연동
- 완료 보고서: `task_done/peer_phase6_thematic.md`, `task_done/peer_phase7_llm_filter.md`

### 핵심 기능 (메인 설계서 Phase 1~5)

| 영역 | 설계 항목 | 구현 위치 | 분류 |
|------|----------|----------|------|
| 모델 (5종) | CompanyBenchmarkDelta, CategorySignal, CompanyMetricLatest, ValidationNewsSummary, PeerPreset+UserPeerPreference | `models/` | **A** (단, 아래 News 요약 예외) |
| Peer 선정 | industry+size → industry → sector 3단계 fallback + confidence | `services/benchmark_calculator.py` | **A** |
| 7 카테고리 신호등 | green/yellow/red/gray + percentile 평균 + special 산업 gray | `services/category_signal_calculator.py` | **A** |
| 상대 지표 | rev_growth_vs_industry | `services/relative_metrics.py` | **A** |
| Rule-based 해석 | 요약/지표 해석/추세/리더 비교 (LLM 미사용) | `services/interpretation.py` | **A** |
| Compute-on-Read | 커스텀 peer 실시간 계산 + Redis 1h | `services/custom_benchmark_engine.py` | **A** |
| API (7개) | summary, metrics, leader-comparison, presets, peer-preference(POST/DELETE), llm-filter | `api/views.py`, `api/urls.py` | **A** |
| 배치 (7 태스크) | Task 1~6 + 오케스트레이터 (Celery Chain) | `tasks.py` | **A** |
| Seed | MetricDefinition 34개 + IndustryClassification special | `management/commands/seed_validation_data.py` | **A** |

### 34개 지표 — 부분 갭 (B)

| 상태 | 개수 | 지표 | 사유 |
|------|------|------|------|
| 구현됨 | 31 | 대부분 | — |
| **미구현 (C)** | 2 | `sbc_to_revenue`, `buyback_offsets_sbc` | FMP에서 SBC(주식보상비용) 필드 미제공 |
| **스텁 (B)** | 1 | `cash_from_ops_trend` | 3년 CAGR 추세 미구현, "Phase 2 예정"으로 보류 |

### Peer Phase 6 — Thematic 프리셋: **대체 구현 (D)**

| 항목 | 설계 (`peer_phase6_7.md`) | 실제 구현 (`peer_phase6_thematic.md`) |
|------|--------------------------|--------------------------------------|
| 클러스터링 축 | **사업모델 태그** (subscription_saas, platform_marketplace 등) | **GrowthStage × CapitalDNA 교차** (Chain Sight DNA) |
| 데이터 소스 | `CompanyNarrativeTag.theme_tags` (Gemini 태깅 배치 신규) | `CompanyGrowthStage` × `CompanyCapitalDNA` (기존 Chain Sight) |
| Gemini 태깅 배치 | 설계됨 (503종목, ~34분) | **미구현** — DNA 교차로 대체하여 LLM 태깅 생략 |
| 결과 | — | 463/503 종목 생성, 전체 프리셋 2,282개 |

> **판정**: thematic 프리셋 자체는 **구현됨**. 그러나 설계가 전제한 `theme_tags` 기반 사업모델 태깅 파이프라인은 **만들지 않고**, 이미 채워진 Chain Sight DNA(stage×capital)로 **대체**했다.
> 배경: `peer_phase6_7.md §구현 준비 상태`에서 "CompanyNarrativeTag 0건 → 블로킹"으로 진단됐고, theme_tags 파이프라인 선행이 필요하다고 명시. 실제로는 그 선행 작업 대신 DNA 교차라는 더 가벼운 경로를 택함.
> ⇒ "사업모델 유사" 의도는 부분 충족(성장단계+자본구조 유사 ≈ 사업모델 유사 근사치). 진정한 사업모델 태깅(subscription/marketplace 등 축)은 **미구현**.

### Peer Phase 7 — LLM 대화형 필터: **부분 갭 (B) + 경로 불일치**

| 항목 | 설계 | 실제 | 분류 |
|------|------|------|------|
| LLM 파서 + 필터 실행 | `parse_filter_with_llm` + `execute_peer_filter` | 구현됨 (`services/llm_peer_filter.py`) | **A** |
| API 경로 | `POST /{symbol}/peer-filter/` | `POST /{symbol}/llm-filter/` | **경로 불일치** (기능 동일) |
| 서비스 파일명 | `peer_filter_parser.py` (설계) | `llm_peer_filter.py` (실제) | 명칭 불일치 |
| 응답 `preview` | category_signals + summary_text 미리보기 포함 | **peers 리스트만 반환** (preview 없음) | **B** (미리보기 미구현) |
| 지원 필터 | Chain Sight 6종 + Sensitivity + 31지표 + 제외 | 동일 구현 | **A** |
| Chain Sight 의존 시나리오 | foreign_revenue_pct, rd_to_revenue | 파싱은 되나 데이터 부족으로 결과 0건 (설계 §Phase 7-Lite 예측대로) | **B** (데이터 한계) |
| **Thesis Control 연동 (Step 5)** | `thesis.peer_preset_key`, `peer_filter_query`, `peer_filter_result` 필드 추가 + 가설 빌더/관제실 연결 | **미구현** — thesis 모델에 해당 필드 없음 (`thesis/models/thesis.py` 확인) | **C** |

### ValidationNewsSummary 모델 — **모델만 정의, 채움 로직 없음 (C)**

`models/news_summary.py`에 모델 + `admin.py` 등록은 있으나, **이 모델을 채우는 서비스/태스크가 services/ 어디에도 없다.**
(`grep ValidationNewsSummary` → migration + admin 만 매칭, calculator/task 없음)
⇒ 뉴스 감성 집계 → 검증 화면 통합 기능은 **스키마만 존재, 미작동**.

### LLM 해석 (메인 설계서 §8) — 의도적 보류 (D)

`validation_design.md §8`은 "Phase 1: Rule-based Only / Phase 2 LLM 도입 시 구조(참고용)"로 명시.
현재 `interpretation.py`는 전부 rule-based이며 LLM 해석은 **설계상 보류 상태**. (갭이 아니라 계획된 단계)

### Validation 판정: 🟡 핵심(Phase 1~5) 완전 구현. 갭 4건:
1. **(C)** 지표 2개 미구현 (SBC 데이터 부재) + **(B)** 1개 스텁
2. **(D)** Phase 6 thematic — theme_tags 사업모델 태깅 대신 DNA 교차로 대체
3. **(B/C)** Phase 7 — preview 미구현 + API 경로 불일치 + **Thesis 연동 전체 미구현(C)**
4. **(C)** ValidationNewsSummary — 모델만 존재, 집계 로직 없음

---

## News 상세

### 설계서 구성
- `docs/news/plan/news_pipeline_monitoring_design.md` (1160줄) — 모니터링 대시보드 Phase A/B/C
- `docs/news/plan/news_keyword_detail_plan.md` (216줄) + `keyword_detail_bottomsheet_v2.md` (80줄) — 키워드 상세 바텀시트
- `docs/features/news/AI_NEWS_BRIEFING_COLD_START_DESIGN.md` (496줄) — 콜드스타트 AI 브리핑 + 관심사
- `docs/features/news/NEWS-INFRASTRUCTURE-SETUP.md` (592줄) — Docker/Neo4j/env 인프라
- (+ CLAUDE.md 기재 Intelligence Pipeline v3)

### 1) 모니터링 대시보드 (`news_pipeline_monitoring_design.md`) — 백엔드 **완전 구현 (A)**

설계서 부록의 신규 엔드포인트 전부가 `services/news/api/views.py`에 **@action으로 구현됨**:

| 설계 엔드포인트 | Phase | 구현 (views.py 라인) | 분류 |
|----------------|-------|---------------------|------|
| `collection-logs/` | A | L1411 `collection_logs` | **A** |
| `pipeline-health/` | A | L1537 `pipeline_health` | **A** |
| `ml-trend/` | A | L1911 `ml_trend` | **A** |
| `llm-usage/` | A | L2002 `llm_usage` | **A** |
| `task-timeline/` | B | L2134 `task_timeline` | **A** |
| `neo4j-status/` | B | L2202 `neo4j_status` | **A** |
| `ml-rollback-preview/` | B | L2276 `ml_rollback_preview` | **A** |
| `ml-rollback/` (POST, confirm) | B | L2325 `ml_rollback` | **A** |
| `alerts/` | C | L2378 `alerts` | **A** |
| `alerts/{id}/resolve/` | C | L2453 `alerts_resolve` | **A** |
| AlertLog 모델 (7 trigger_type) | C | `models.py` + migration `0006_alertlog` | **A** |
| `check_pipeline_alerts` 태스크 (@infra) | C | `tasks.py` L1179 (7개 트리거 전부) | **A** |
| `_log_collection()` 커버리지 (§11 선행) | 0 | `tasks.py` L1461 (시그니처는 results dict 기반으로 변형) | **A** |

> ⇒ 설계서가 "구현 전(설계 단계)"으로 표기됐으나, **Phase A/B/C 백엔드가 전부 완성**되어 있다. 설계서 상태 표기가 stale.
> **프론트엔드 부분**(NewsTab sub-tab, PipelineStatusBar 등 컴포넌트 12개 + hooks/service)은 `frontend/` 영역 → 본 감사 범위 밖, **별도 확인 필요**.

### 2) 키워드 상세 (`news_keyword_detail_plan.md` + `_v2.md`) — 백엔드 **구현 (A)**

| 설계 항목 | 구현 | 분류 |
|----------|------|------|
| `keyword-detail/?date&index` API | `views.py` L677 `keyword_detail` | **A** |
| `search_terms_en` 프롬프트 확장 (한↔영 매칭) | `keyword_extractor.py` (프롬프트 L268/283 + 파싱 L338) | **A** |
| 2단 매칭 (related_symbols → search_terms_en) | keyword_detail action 내 구현 | **A** |
| 프론트 바텀시트(`KeywordDetailSheet`) + Strip UI(v2) | `frontend/` 영역 | 범위 밖 |

### 3) 콜드스타트 AI 브리핑 (`AI_NEWS_BRIEFING_COLD_START_DESIGN.md`) — 백엔드 **구현 (A)**

| Phase | 설계 항목 | 구현 | 분류 |
|-------|----------|------|------|
| A | MarketFeedService + `market-feed/` API | `services/market_feed.py`, `views.py` L960 | **A** |
| A | NewsKeywordExtractor 프롬프트 확장 | `keyword_extractor.py` | **A** |
| B | UserInterest 모델 | `packages/shared/users/models.py` (users 앱으로 재배치) | **A** |
| B | InterestOptionsService + `interest-options/` API | `services/interest_options.py`, `views.py` L1004 | **A** |
| B | PersonalizedFeedService + `personalized-feed/` API | `services/personalized_feed.py`, `views.py` L1042 | **A** |
| B | Portfolio→Watchlist→Interest→MarketFeed fallback | `personalized_feed.py` (4단 폴백 확인) | **A** |
| C | Progressive Personalization | 설계상 "별도 이슈"로 분리 | 범위 밖/보류 |

### 4) 인프라 (`NEWS-INFRASTRUCTURE-SETUP.md`) — **구현 (A)**
Docker Compose, Neo4j 초기화, env 키, 검증 스크립트 — "완료된 작업" 문서이며 providers/(finnhub/fmp/marketaux) + circuit_breaker 등 코드로 뒷받침됨.

### 5) Intelligence Pipeline v3 (CLAUDE.md) — **완전 구현 (A)**
규칙엔진(Engine A/B/C) + LLM 심층분석(Tier A/B/C) + Neo4j 이벤트 동기화 + ML 가중치(LR→LightGBM) + Shadow/Production 자동배포 + 모니터링 — 전 단계 코드 존재. (`news_classifier`, `news_deep_analyzer`, `news_neo4j_sync`, `ml_weight_optimizer`, `ml_production_manager`)

### News 판정: 🟢 백엔드 전 설계서 구현 완료 (A).
- 유일한 백엔드 잔존: 콜드스타트 Phase C(Progressive Personalization)는 설계상 별도 이슈로 보류.
- **프론트엔드 구현 여부는 미검증** — 모니터링 대시보드 컴포넌트 12개 + 키워드 바텀시트 + AI브리핑 카드가 `frontend/`에 실제 존재하는지 별도 감사 권장.

---

## 종합 갭 목록 (우선순위)

| # | 앱 | 갭 | 분류 | 영향도 | 비고 |
|---|----|----|------|--------|------|
| 1 | Validation | Phase 7 Thesis Control 연동 (thesis 모델 peer 필드 + 가설빌더/관제실) | **C** | 중 | 설계 Step 5 전체 미구현 |
| 2 | Validation | ValidationNewsSummary 채움 로직 | **C** | 중 | 모델만 존재, 미작동 |
| 3 | Validation | Phase 6 thematic — 사업모델 theme_tags 태깅 파이프라인 | **D→C** | 저 | DNA 교차로 대체, 진정한 사업모델 축은 미구현 |
| 4 | Validation | 지표 `sbc_to_revenue`, `buyback_offsets_sbc` | **C** | 저 | FMP SBC 필드 부재 (외부 제약) |
| 5 | Validation | 지표 `cash_from_ops_trend` 3년 CAGR | **B** | 저 | 스텁, Phase 2 보류 |
| 6 | Validation | Phase 7 `peer-filter` API 경로/명칭 + preview 응답 | **B** | 저 | `/llm-filter/`로 동작 중, preview만 누락 |
| 7 | News | 프론트엔드 대시보드/바텀시트/브리핑 카드 | **미검증** | ? | 본 감사 범위 밖, 별도 확인 필요 |
| 8 | SEC | S&P500 전체 배치 + CompanyAlias 데이터 채움 | 운영 | 중 | 코드 완료, 미실행 (매칭률 3% 원인) |

---

## 감사 결론

- **SEC Pipeline**: 설계 대비 코드 갭 **없음**. 17 PR 전부 구현. 남은 건 배포·데이터·튜닝뿐. → 🟢
- **Validation**: 핵심 검증 엔진(Phase 1~5)은 완전. **Phase 6~7의 고급 기능에서 갭 집중** — Thesis 연동 미구현(C), 뉴스 요약 미작동(C), thematic 대체 구현(D), Phase 7 preview 누락(B). → 🟡
- **News**: 백엔드는 4개 설계서 + Intelligence v3까지 전부 구현 (설계서 "구현 전" 표기가 stale). **프론트엔드 별도 감사 권장**. → 🟢

> 본 보고서는 읽기 전용 분석이며 어떤 코드도 수정하지 않았다.
