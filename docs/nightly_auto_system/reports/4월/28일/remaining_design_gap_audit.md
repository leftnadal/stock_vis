# SEC Pipeline + Validation + News 설계 갭 감사

> **감사일**: 2026-04-29 (read-only audit)
> **대상**: `docs/sec_pipeline/` vs `sec_pipeline/`, `docs/first_validation_system/` vs `validation/`, `docs/news/` vs `news/`
> **방법**: 설계서 명세 ↔ 구현 파일·모델·뷰·태스크 cross-reference + `task_done/` 보고서 대조

---

## 앱별 요약 (구현률)

| 앱 | 설계서 | 구현률 | 분류 | 한 줄 평 |
|----|--------|--------|------|----------|
| **sec_pipeline** | base_design + 17 PR detail | **약 95%** | 거의 전체 (A) | 17 PR 모두 `task_done/` 기록, Beat 등록 1건만 보류 |
| **validation** | validation_design v1.4 + peer v2 + Phase 6/7 | **약 85%** | 부분 구현 (B) | 핵심 흐름 완성, `IndustryClassification.handling_mode`/`ValidationAICache`/Thesis 연동 미반영 |
| **news (모니터링)** | news_pipeline_monitoring v1.1 (Phase A/B/C) | **약 90%** | 거의 전체 (A) | Phase A/B/C 백엔드·프론트 완성, Beat 등록(`check_pipeline_alerts` 스케줄)만 인프라 영역 |
| **news (키워드 상세)** | news_keyword_detail v1 + bottomsheet v2 | **100%** | 완전 구현 (A) | API/프롬프트(`search_terms_en`)/BottomSheet 모두 반영 |

> **분류 기준** — A: 설계서 핵심 산출물 전체 구현, B: 핵심은 구현됐지만 명세 일부(필드/뷰/플로우) 누락, C: 미착수, D: 폐기/대체

---

## SEC Pipeline 상세

> 설계서: `docs/sec_pipeline/decisions/001_*.md` + `docs/sec_pipeline/task_done/sec_pr_1~17_*.md` (17 PR)
> 구현: `sec_pipeline/` (16 파일 + 8 모델 + 4 management commands + fixtures + templates)

### 분류

**(A) 완전 구현 — 17 PR 전부 task_done 기록 존재**

| PR | 설계 요구 | 구현 위치 | 검증 |
|----|----------|-----------|------|
| PR-1 | 8개 모델 + migration | `sec_pipeline/models.py` (RawDocumentStore, SupplyChainEvidence, BusinessModelSnapshot, BusinessModelEvidence, FilingProcessLog, CompanyAlias, UnmatchedCompanyQueue, PipelineIntelligenceReport) | ✅ 모델 8개 모두 존재. `db_table` 명도 설계서와 일치. `neo4j_dirty` 패턴 준수. |
| PR-2 | SECFilingCollector (메타+HTML+섹션) | `collector.py` | ✅ 임포트 성공 (tasks.py가 호출) |
| PR-3 | Track A LLM 추출기 | `extractor.py`, `validator_track_a.py`, `prompts.py` | ✅ |
| PR-4 | Celery `collect_and_extract` + `extract_from_document` 분리 | `tasks.py` line 23, 149 | ✅ 분리 패턴 준수, `_log_stage`로 6 stage 로깅 |
| PR-5 | Gold Set | `fixtures/gold_set.json` + `gold_set_schema.py` + `evaluate_gold_set` 명령 | ✅ |
| PR-6 | Phase 1 배치 (15종목) | task_done 결과: 14/15 성공 (JNJ만 검증 실패) | ✅ |
| PR-7 | TickerMatcher (alias→exact→fuzzy) | `ticker_matcher.py` + `seed_company_aliases` 명령 | ✅ |
| PR-8 | Admin + signals (post_save 갱신, alias 자동 등록) | `admin.py`, `signals.py` | ✅ |
| PR-9 | Neo4j sync (DELETE+CREATE dynamic type) | `tasks.py:sync_dirty_to_neo4j` (line 338) — `KNOWN_TYPES` 6종 + `f-string` rel_type | ✅ DECISIONS.md 원칙 7 준수 (`MERGE` 금지, dynamic type) |
| PR-10 | merger.py + DQS | `merger.py` | ✅ |
| PR-11~13 | Phase 2 Track B (BusinessModelSnapshot 5필드) | `validator_track_b.py`, `keywords_track_b.py` | ✅ |
| PR-14 | Admin 대시보드 + quality_checks 7종 | `views.py:sec_pipeline_dashboard` + `quality_checks.py` + `templates/admin/sec_pipeline/dashboard.html` | ✅ |
| PR-15 | On-demand + check_new_filings | `on_demand.py:get_or_collect_filing` + `tasks.py:check_new_filings` (line 465) | ✅ FilingDataView가 200/202 분기 |
| PR-16 | Intelligence 5차원 분석 | `intelligence.py:PipelineIntelligenceReporter` | ✅ |
| PR-17 | E2E `run_batch_and_report` chord 패턴 | `tasks.py:run_batch_and_report` (line 509) — chain 대신 순차 실행 (1인 개발 단순성) | ✅ task_done이 `chord 대신 순차 실행`이라고 명시 — 의도된 변형 |

**부가 구현(설계서엔 없는 보너스)**

- `seed_relations_to_chainsight` (`tasks.py:282`): 매칭된 `SupplyChainEvidence` → `chainsight.RelationConfidence` 시드. CUSTOMER_OF→SUPPLIES_TO 방향 정규화. Chain Sight 통합용.

### (B) 부분 구현

해당 없음.

### (C) 미구현 — 1건

| 항목 | 위치 | 설명 |
|------|------|------|
| **Celery Beat 등록** | `tasks.py` line 559~566 (주석 상태) | 설계서엔 명시 안 됐으나 PR-9/PR-15 운영 자동화의 전제. `sync-sec-dirty-neo4j` (`*/5min`)와 `check-new-filings` (`day=1`) 두 항목이 dict 주석으로만 존재. CLAUDE.md 버그 #28(Beat schedule drift) 케이스 — DatabaseScheduler에 `PeriodicTask.objects.create(...)`로 등록 필요. **@infra 영역**으로 추정. |

### (D) 폐기/대체

해당 없음.

### task_done cross-reference

`docs/sec_pipeline/task_done/`의 **15건** + 종합 요약 1건이 실제 PR 17개를 모두 커버 (PR-11~13은 `sec_pr_11_12_13_phase2.md` 통합 보고서). `sec_pipeline_complete_summary.md`(2026-04-04)가 8개 모델 카운트(15/110/173/0/60/5/25/2)까지 명시 — 실제 DB와 일치 검증된 상태로 기록됨.

### 향후 과제 (설계서가 직접 명시)

설계서 `sec_pipeline_complete_summary.md` line 107-113:
1. S&P 500 전체 배치 (Gemini RPD)
2. Gold Set 라벨 보완 → P/R 재평가
3. JNJ Item 순서 검증 완화
4. 프롬프트 개선 ("third parties" 일반명사)
5. CompanyAlias 수동 등록 (TSMC→TSM, Samsung 등) — 현재 0건

---

## Validation 상세

> 설계서: `validation_design.md` (v1.4, 1646줄), `validation_peer_system.md` (Peer v2, 6 프리셋), `validation_peer_phase6_7.md` (Thematic + LLM Filter), `validation_pr_prompts.md`
> 구현: `validation/` (api/ + models/ + services/ 11개 + tasks.py + 4 migrations)

### 분류

#### (A) 완전 구현

| 영역 | 설계 요구 | 구현 |
|------|----------|------|
| **REST API 6개** | summary / metrics / leader-comparison / presets / peer-preference / llm-filter | `validation/api/views.py` + `urls.py` 모두 등록 (line 7~14) |
| **Peer 프리셋 6종 + custom** | default, sector_all, size_peers, quality_top, lifecycle, thematic, custom | `services/preset_generator.py` (`_generate_thematic` 등), task_done 결과 2,282 프리셋 생성 |
| **Compute-on-Read 커스텀** | UserPeerPreference + Redis TTL 1h | `models/peer_preset.py:UserPeerPreference` + `services/custom_benchmark_engine.py` |
| **6단계 배치 파이프라인** | Task 1~6 (chain) | `validation/tasks.py` Task 1~6 + `run_weekly_validation_batch` |
| **value_status 5단계** | normal/missing/not_applicable/unstable/low_confidence | `metrics/models/metric_snapshot.py` (`MetricCalculator` 판정) |
| **benchmark_basis + confidence** | industry_size/industry/sector + high/medium/low | `validation/migrations/0003` — 추가됨 |
| **CategorySignal** (이름 변경) | category_score → category_signal | `models/category_score.py` 안에 `CategorySignal` 클래스 (파일명만 옛 이름 유지) + migration 0002 |
| **frontend Recharts ComposedChart** | Bar+Scatter+ErrorBar | `frontend/components/validation/MetricBarChart.tsx`, MetricCard, PeerContextBar 등 9개 컴포넌트 |
| **Phase 6 Thematic** | LLM 큐레이션 | `_generate_thematic` 메서드 (peer_phase6_thematic.md) |
| **Phase 7 LLM 필터** | 자연어→구조화→실행 | `services/llm_peer_filter.py` + `LLMPeerFilterView` (peer_phase7_llm_filter.md) |
| **rule-based 해석 텍스트** | summary/metric/leader 3종 | `services/interpretation.py` |

#### (B) 부분 구현 — 명세와 차이

| # | 설계 명세 | 실제 구현 | Gap 요약 |
|---|----------|----------|----------|
| B-1 | `IndustryClassification` 모델 + `handling_mode` (special: 금융/REIT/유틸리티) | **모델 자체 미생성** (`metrics/` grep: 매치 없음) | 특수 산업 게이트가 빠짐. handling_mode='special' → 카테고리 gray + 고지문 로직이 코드 어디에도 없음. 설계서 §3.1, §7.5, §10 Empty State Case 5에서 명시. |
| B-2 | Phase 6 thematic = `CompanyNarrativeTag.theme_tags` 클러스터링 (Gemini 503회 호출, 사업모델 태그 풀) | **GrowthStage × CapitalDNA 교차 조합으로 구현됨** | task_done이 명시적으로 차이 기록 ("같은 stage+capital_type"). 설계서의 LLM 사업모델 태깅 파이프라인과는 완전 다름. peer_phase6_7.md §"Phase 6~7은 Chain Sight 데이터 파이프라인이 선행" 판단에 따라 우회한 것으로 보이나 설계서 본문은 갱신 안 됨. |
| B-3 | Phase 7 → Thesis Control 연동 (`Thesis.peer_preset_key`, `peer_filter_query`, `peer_filter_result` 필드 추가) | **thesis 모델에 매치 없음** (`grep -r "peer_preset_key" thesis/` → 0건) | API는 작동하나 Thesis 빌더/관제실에서 LLM 필터 결과를 저장할 곳 없음. 설계서 §"Thesis Control 연동" 미수행. |
| B-4 | `peer_list_cache.peer_tier` (Phase 2용 nullable 필드) | (PeerListCache에 미확인) | Phase 2 확장용 placeholder가 누락됐을 가능성. 설계서 §7.4. |
| B-5 | 프론트 `CategorySidebar` Sticky 사이드바 (스크롤 위치 하이라이트) | `CategorySidebar.tsx` 존재 — 동작 검증은 별도 (UI 동작 확인 필요) | 구조는 있으나 Sticky 동작/IntersectionObserver 적용 여부는 코드 외 검증 필요 |

#### (C) 미구현

| 항목 | 출처 | 설명 |
|------|------|------|
| **`ValidationAICache`** | 설계서 §8.2 (Phase 2 LLM 도입 시) | Phase 1 rule-based만 사용 — 의도된 미구현. **현재 단계에서 미구현은 정상**, Phase 5에서 결정. |
| **FMP 5년 이력 반환 사전 테스트** | 설계서 §10 Phase 2 체크리스트 | task_done에 "FMP Starter 5년 반환 테스트" 결과가 없음 — 테스트는 됐을 수 있으나 문서화 누락. |
| **모바일 Accordion (1개씩 펼침)** | 설계서 §2.2 | 9개 컴포넌트 존재하나 Accordion 동작 단위테스트 부재 (`__tests__/validation/`에 SignalSummaryCard/PeerContextBar/MetricCard 3건만) |
| **Empty State 5종 분기** | 설계서 §10 line 1538~1577 | 코드 분기 일부 존재(404, no_data) — Case 4 (S&P 500 외)만 명시적, Case 1~3/5는 부분적 |

#### (D) 폐기/대체

| 항목 | 변경 사유 |
|------|----------|
| Phase 6 LLM 큐레이션 | Chain Sight `theme_tags` 데이터 부재로 GrowthStage×CapitalDNA로 대체 (peer_phase6_7.md §"판단: Chain Sight 완성 후" 결정) — 설계서 본문 갱신 필요 |

### task_done cross-reference

| task_done 파일 | 다루는 PR/Phase |
|----------------|-----------------|
| `peer_phase6_thematic.md` (2026-04-04) | Phase 6 — DNA 교차 방식 채택 명시 |
| `peer_phase7_llm_filter.md` (2026-04-04) | Phase 7 — LLM 필터 + chain sight + metrics 9개 필터 |

> Phase 1~5 (peer 프리셋 v2 6개) 자체에 대한 개별 task_done은 별도 위치(추정: 이전 reports 또는 PROGRESS.md)에 산재. 설계서 `validation_pr_prompts.md`의 PR 단위 결과 보고서가 한 곳에 모이지 않은 점은 문서화 갭.

### 핵심 갭 우선순위

1. **B-1 (handling_mode)** — 금융/REIT 종목에서 잘못된 신호등 표시될 위험. CLAUDE.md `common-bugs`에 등록 권장.
2. **B-3 (Thesis 연동)** — Phase 7 가치 절반 손실. 가설 빌더에서 LLM 필터 결과를 다시 만들어야 함.
3. **B-2 (thematic 방식 deviation)** — 의도된 deviation이지만 설계서 v1.5로 갱신해야 신규 합류자 혼란 방지.

---

## News 상세

> 설계서:
>  - `news_pipeline_monitoring_design.md` v1.1 (Phase A/B/C, 1160줄)
>  - `news_keyword_detail_plan.md` (216줄, v1)
>  - `keyword_detail_bottomsheet_v2.md` (80줄, Strip + 너비 제한)
> 구현: `news/` (api/views.py 2183줄 + models.py 727줄 + services 17개 + providers 4개 + tasks.py 1433줄 + 6 migrations)

### 분류

#### (A) 완전 구현

##### Pipeline Monitoring Phase A (백엔드 4 + 프론트 6 + sub-tab)

| API | 설계 요구 | 구현 |
|-----|----------|------|
| `GET /collection-logs/` | provider별 + 일별 집계 | `news/api/views.py:1314` (`@action url_path='collection-logs'`) |
| `GET /pipeline-health/` | 6 Phase status + ml/llm summary + `?force_refresh` | `views.py:1424` |
| `GET /ml-trend/` | F1/Precision/Recall + feature_importance | `views.py:1678` |
| `GET /llm-usage/` | 키워드 + 분석 (분석은 토큰 미추적 경고) | `views.py:1758` |

| 프론트 | 구현 |
|--------|------|
| `frontend/services/newsPipelineService.ts` | ✅ |
| `frontend/hooks/useNewsPipeline.ts` | ✅ |
| `PipelineStatusBar.tsx`, `CollectionStatsTable.tsx`, `MLModelCard.tsx`, `MLTrendChart.tsx`, `RecentErrorsList.tsx`, `LLMUsageSummary.tsx`, `NewsPipelineSubTab.tsx` | ✅ 모두 존재 |

##### Pipeline Monitoring Phase B

| API | 구현 |
|-----|------|
| `GET /task-timeline/` | `views.py:1878` |
| `GET /neo4j-status/` | `views.py:1939` |
| `GET /ml-rollback-preview/` | `views.py:2000` |
| `POST /ml-rollback/` (confirm 필수) | `views.py:2040` |

| 프론트 | 구현 |
|--------|------|
| `TaskTimelineChart.tsx`, `Neo4jStatusCard.tsx`, `MLCompareView.tsx` | ✅ |

##### Pipeline Monitoring Phase C

| 항목 | 구현 |
|------|------|
| `AlertLog` 모델 (`Severity` + `TriggerType` 7종 enum) | `news/models.py:684`, migration `0006_alertlog.py` |
| `GET /alerts/`, `POST /alerts/{id}/resolve/` | `views.py:2085, 2149` |
| `check_pipeline_alerts` Celery 태스크 (7종 트리거 처리) | `news/tasks.py:1102` 이하 — consecutive_task_failure / ml_f1_decline / keyword_extraction_failure / llm_error_spike / neo4j_unavailable / collection_drop / unclassified_backlog 모두 분기 처리 |
| 프론트 `AlertBadge.tsx`, `AlertList.tsx` | ✅ |

##### Phase 0 선행 — `_log_collection()` 커버리지 보강

설계서가 누락 태스크에 `_log_collection()` 호출 추가를 요구 (§11). 실제 호출 11개 + 정의 1개 — 9개 태스크에서 호출 (collect_daily_news, collect_market_news, collect_category_news, classify_news_batch, analyze_news_deep, sync_news_to_neo4j, collect_sp500_news_fmp_batch, collect_press_releases_fmp, collect_general_news_fmp). ✅

##### Keyword Detail (BottomSheet v1 + v2)

| 항목 | 구현 |
|------|------|
| `keyword_extractor.py`에 `search_terms_en` 프롬프트 확장 | `news/services/keyword_extractor.py` line 43~45, 241, 256~258, 306, 321 — 8개 매치 |
| `GET /keyword-detail/` API | `news/api/views.py:640` (`@action url_path='keyword-detail'`) |
| 프론트 `KeywordDetailSheet.tsx` | `frontend/components/news/KeywordDetailSheet.tsx` ✅ |
| BottomSheet v2 (max-w-2xl + 가로 스크롤 Strip) | 설계 명세 충족 여부는 코드 내부 확인 필요 (UI 동작 검증) — 컴포넌트 존재 확인됨 |

#### (B) 부분 구현

| # | 설계 명세 | 실제 구현 | Gap |
|---|----------|----------|-----|
| B-1 | `check_pipeline_alerts` Celery Beat 30분 주기 등록 | 태스크 함수는 있으나 Beat 등록 위치 미확인 (`@infra` 영역) | 모델·로직·API 다 있어도 Beat 미등록이면 알림이 안 뜸. CLAUDE.md `common-bugs` #28과 동일 패턴. |
| B-2 | LLM Usage `deep_analysis.coverage_warning` (Phase 3 토큰 미집계) | 응답에 경고 문구 포함 여부 — 코드 분기는 있으나 UI 노란 배너 표시는 별도 검증 필요 | 설계서 §3.4가 "API와 UI 양쪽에 명시" 요구 |

#### (C) 미구현

| 항목 | 출처 | 비고 |
|------|------|------|
| **Slack webhook 알림** | 설계서 §6.2 | "선택" 표시 — Phase C에서 옵션. 환경변수 `SLACK_WEBHOOK_URL` 사용 여부 미확인. |
| **이메일 알림** | 설계서 §6.2 | "선택" 표시 — 필수 아님. |
| **Phase B `NewsDeepAnalyzer` 토큰 로깅 추가** | 설계서 §3.4 마지막 줄 ("Phase B에서 통합 API로 확장") | 설계서가 명시한 후속 작업. 현재 미구현. |

#### (D) 폐기/대체

해당 없음.

### task_done cross-reference

`docs/news/`에는 task_done 디렉토리가 없음. 모니터링/키워드 상세 작업의 완료 보고서는 별도 위치(예: PROGRESS.md, 상위 레포트)에 산재. 설계서 v1.1과 구현 결과의 직접 매핑 문서가 부재한 것이 문서화 갭.

### 핵심 갭 우선순위

1. **B-1 (Beat 등록)** — `check_pipeline_alerts` 자동 실행 보장 확인 필요. 미등록 시 Phase C 가치 0.
2. **C-3 (Phase 3 토큰 로깅)** — LLM 비용의 대부분이 deep_analysis인데 추적 불가 — 설계서가 직접 후속 작업으로 지정.

---

## 종합 결론

### 구현 완성도

```
sec_pipeline:  ████████████████████ 95%  (Beat 등록만 잔존)
validation:    █████████████████░░░ 85%  (handling_mode, Thesis 연동 미반영)
news (모니터링): ██████████████████░░ 90%  (Beat 등록, Phase 3 토큰)
news (키워드):  ████████████████████ 100%
```

### 이번 세션에 즉시 후속 가능한 작업

1. **validation/IndustryClassification 모델 + handling_mode 필드 추가** (설계서 §7.5 명시) — migration + Task 4 분기 + UI 고지문
2. **thesis 모델에 peer_filter_query/peer_filter_result 필드 추가** (Phase 7 연동 완성) — nullable 필드 추가, 기존 Thesis 영향 없음
3. **Beat 등록 4건** (sec_pipeline 2건 + news `check_pipeline_alerts` 1건 + 가능 시 validation weekly batch) — `PeriodicTask.objects.create(...)` 또는 `seed_*` 명령 추가

### 문서 갱신 필요

- `validation_peer_phase6_7.md` v1.1 → 실제 구현이 GrowthStage×CapitalDNA 방식으로 갈음됐음을 본문에 반영
- `docs/news/` 하위 `task_done/` 디렉토리 생성 + 모니터링 Phase A/B/C 완료 보고서 작성 (현재 산재)
- `validation_pr_prompts.md` PR별 task_done 결과 보고서 → 일괄 정리

### 검증 한계

- 본 감사는 **파일 존재 + 모델/뷰 등록 + 함수 시그니처** 수준의 정적 점검. UI 동작(BottomSheet v2 Strip, Sticky 사이드바, Accordion)은 별도 브라우저 검증 필요.
- 실제 Beat 스케줄(`PeriodicTask`) DB 등록 상태는 운영 DB 조회 필요 — 코드만으로는 판정 불가.
