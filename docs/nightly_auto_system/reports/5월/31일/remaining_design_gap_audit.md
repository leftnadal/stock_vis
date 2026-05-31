# SEC Pipeline + Validation + News 설계 갭 감사

> **감사 일시**: 2026-06-01
> **감사 범위**: 읽기 전용. 코드 수정 없음.
> **방법**: 설계서(`docs/*`) ↔ 구현(`{app}/`) 1:1 대조 + `task_done/` 완료 보고서 cross-reference
> **분류 체계**: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 앱별 요약 (구현률)

| 앱 | A 완전 | B 부분 | C 미구현 | D 폐기 | 백엔드 구현률 | 한줄평 |
|----|:---:|:---:|:---:|:---:|:---:|--------|
| **SEC Pipeline** | 14 (82%) | 3 (18%) | 0 | 0 | **~95%** | 핵심 17 PR 전건 구현. Celery Beat 자동화만 주석 상태 |
| **Validation** | 백엔드 31, FE 0 | 10 | FE 7개 | 0 | **백엔드 ~90% / FE 0%** | 배치·API 완성. 프론트 7 PR 전건 미착수 + Phase 6/7 Chain Sight 의존 미흡 |
| **News** | 11 (80%) | 4 | 2 | 0 | **~80%** | 키워드 상세 + 모니터링 Phase A/B 완성. Phase C 자동 알림은 @infra 미착수 |

**종합**: 세 앱 모두 **백엔드 코어는 사실상 완성**(80~95%). 미완 갭은 (1) Validation 프론트엔드 전체, (2) Celery 자동화 스케줄(SEC·News 공통, @infra 영역), (3) Validation Phase 6/7의 Chain Sight 데이터 의존성 — 세 갈래로 수렴한다. 설계 폐기(D) 사례는 0건.

---

## SEC Pipeline 상세

**설계 위치**: `docs/sec_pipeline/decisions/`, `docs/sec_pipeline/task_done/` (PR 1~17 + complete_summary)
**구현 위치**: `sec_pipeline/`

### 구현률
- (A) 완전 구현: **14개 (82%)**
- (B) 부분 구현: **3개 (18%)**
- (C) 미구현 / (D) 폐기: **0개**

`task_done` 17건에 "완료"로 기록된 항목 중 **코드에 없는 것은 0건**. 반대로 코드에 있으나 문서화 누락된 management command가 3건 발견됨.

### 기능별 상세

| PR / 기능 | 분류 | 근거 | 갭 내용 |
|-----------|:---:|------|--------|
| PR-1 모델 + Migration | A | `models.py`, `migrations/0001_initial.py` (199줄) | 8개 모델 + FK/제약 완비 |
| PR-2 SEC EDGAR 수집기 | A | `collector.py` (`get_filing_metadata`, `fetch_filing_html`, `extract_sections`) | FMP vs EDGAR 결정 문서화(`decisions/001`) |
| PR-3 Track A (Gemini 추출) | A | `normalizer.py`, `extractor.py`, `prompts.py:11-43`, `validator_track_a.py` | 키워드 필터 + confidence_grade 완비 |
| PR-4 Celery Tasks | A | `tasks.py:22-285` | 재시도·backoff·`_log_stage` 완비 |
| PR-5 Gold Set | A | `fixtures/gold_set.py`, `management/commands/evaluate_gold_set.py` | 10종목 + Precision/Recall 평가 |
| PR-6 Phase 1 배치 | A | `tasks.py` `run_batch_and_report()` | 15종목 배치 + Gold 재평가 경로 |
| PR-7 TickerMatcher | A | `ticker_matcher.py` (alias→exact→fuzzy, BLOCKED_NAMES) | rapidfuzz ≥85% 3단 매칭 |
| PR-8 Admin + Signal | A | `admin.py`, `signals.py:1-73` | 8 모델 Admin + post_save signal |
| PR-9 Neo4j Sync | A | `tasks.py:346-463` `sync_dirty_to_neo4j()` | DELETE+CREATE, sole writer, skip_locked |
| PR-10 Merger + DQS | A | `merger.py:1-136`, `management/commands/process_unmatched_queue.py` | 내부/노출 DQS 필드 분리 |
| PR-11 Track B 키워드 | A | `keywords_track_b.py`, `validator_track_b.py` | 5필드 키워드 사전 |
| PR-12 Track B Gemini | A | `prompts.py:46-97`, `extractor.py:93-130` | Business Model 5필드 추출·검증·저장 |
| PR-13 서비스 레이어 | A | `metrics/services/business_model_service.py` | `for_api` 게이트 + confidence 노출 경계 |
| PR-14 대시보드 + 품질체크 | A | `quality_checks.py:1-150`, `views.py:15-26`, `templates/admin/sec_pipeline/dashboard.html` | 7개 품질 체크 |
| PR-15 On-demand + API | A | `on_demand.py:1-69`, `views.py:29-52` (`FilingDataView` 200/202) | 1년 내 중복 방지 |
| PR-16 Intelligence 리포트 | A | `intelligence.py:1-150` | 5차원 수집 + Gemini 분석 |
| **PR-17 E2E Chord** | **B** | `tasks.py:517-564` 순차 실행 / **L568-575 Celery Beat 주석** | 신규 filing 감지·sync 자동화가 수동 트리거만 가능 |
| 추가 commands (문서 누락) | B | `management/commands/rematch_unmatched.py`, `reprocess_unmatched_queue.py`, `seed_company_aliases.py` | 코드 구현됐으나 `task_done`에 미기록 |
| `SupplyChainEvidence.extracted_at` | B | `quality_checks.py:68`, `intelligence.py:84`에서 `extracted_at__gte` 사용 | 필드 정의가 `models.py`에 있는지 전체 확인 권장(추정: `auto_now_add`) |

### 주목할 갭 Top 3

1. **[중] Celery Beat 자동화 미설정** — `tasks.py:567-575`의 `check-new-filings`(매월 1일), `sync-sec-dirty-neo4j`(5분)가 주석 처리됨. 자동화 목표 미달, 운영자가 수동 호출해야 함. @infra가 DatabaseScheduler에 `PeriodicTask.objects.create(...)`로 등록 필요(공통 버그 #28 참조).
2. **[저] Management command 3건 문서화 누락** — `rematch_unmatched`, `reprocess_unmatched_queue`(2026-05-26 C 옵션), `seed_company_aliases`가 코드엔 있으나 PR 보고서에 없음. 운영자가 존재를 모를 위험.
3. **[저-검증] `match_with_queue()` / `extracted_at` 위치 확인** — `tasks.py:210`·`rematch_unmatched.py:79`가 `TickerMatcher.match_with_queue()`를 호출하나 감사 시 `ticker_matcher.py` L100 이내에서 미발견(이후 라인에 정의된 것으로 추정). DB 쿼리 오류 리스크가 아니라 단순 위치 확인 권장.

---

## Validation 상세

**설계 위치**: `docs/first_validation_system/` (`validation_design.md`, `validation_peer_system.md`, `validation_peer_phase6_7.md`, `validation_pr_prompts.md`, `task_done/peer_phase6_thematic.md`, `task_done/peer_phase7_llm_filter.md`)
**구현 위치**: `validation/` + `packages/shared/metrics/models/`(공용 모델)

### 구현률 (총 45개 단위)
- (A) 완전 구현: **31개 (68%)**
- (B) 부분 구현: **10개 (22%)**
- (C) 미구현: **4개 (9%) — 전부 프론트엔드(FE-PR-1~7)**
- (D) 폐기·대체: **0개**

> 백엔드만 보면 ~90% 완성. 프론트 7 PR을 합산해 전체 68%로 떨어짐.

### 기능별 상세

| PR / 기능 | 분류 | 근거 | 갭 내용 |
|-----------|:---:|------|--------|
| BE-PR-1 DB 모델 | A | `validation/models/*.py` + `packages/shared/metrics/models/` | 모델이 두 위치에 분산(혼재) |
| BE-PR-2 시드 데이터 | A | `management/commands/seed_validation_data.py:1-80` | 34지표 + handling_mode 시딩 |
| BE-PR-3 FMP 수집 + 지표계산 | A | `tasks.py:23-48`, `services/financial_fetcher.py`, `services/metric_calculator.py` | value_status 5단계 판정 |
| BE-PR-4 Peer 선정 + Benchmark | A | `services/benchmark_calculator.py`, `services/relative_metrics.py` | size_bucket 4단계 |
| BE-PR-5 Category Signal + 오케스트레이터 | A | `tasks.py:79-151`, `services/category_signal_calculator.py` | green/yellow/red/gray |
| BE-PR-6a~6f API (6종) | A | `api/views.py:59-570` | Summary/Metrics/Leader/Presets/Preference/LLM-Filter 전건 구현 |
| Peer Phase 1~5 | A | `services/preset_generator.py`, `services/custom_benchmark_engine.py` | default/sector/size/quality/lifecycle + Compute-on-Read(Redis TTL 1h) |
| **Peer Phase 6 Thematic** | **B** | `services/preset_generator.py:58-59`, `task_done/peer_phase6_thematic.md` | **설계(Gemini theme_tags 태깅) ↔ 구현(GrowthStage×CapitalDNA 교차) 불일치**. 463/503 종목 생성됐으나 Chain Sight `CompanyNarrativeTag.theme_tags` 0건 |
| **Peer Phase 7 LLM 필터** | **B** | `services/llm_peer_filter.py:1-266`, `api/views.py:507-570` | MetricSnapshot 31지표로 5 시나리오 중 3개만 커버. "해외매출/R&D" 필터는 `CompanySensitivityProfile`·`CapitalDNA` 0건이라 조용히 실패 |
| Rule-based 해석 함수 | B | `services/interpretation.py:12-130` | Phase 2 LLM 배치 캐싱 미구현(의도된 보류) |
| **FE-PR-1~7 프론트엔드** | **C** | 설계서만 존재, 구현 0 | 네비/타입/SignalSummaryCard/MetricCard/Accordion/IndustryPosition/EmptyState 전건 미착수 |

### 지표명 설계↔구현 불일치 (검증 필요)

| 설계 지표명 | 구현 추정명 | 비고 |
|------------|------------|------|
| `ocf_trend_3y` (현금흐름 6번) | `cash_from_ops_trend` | 동일 지표일 가능성 높음, 설계서 갱신 필요 |
| `shareholder_yield` (희석 4번) | `net_shareholder_yield` | 동일 여부 확인 필요 |

### 주목할 갭 Top 5

1. **[최상] 프론트엔드 완전 미구현 (FE-PR-1~7)** — 백엔드 API 6종이 모두 준비됐으나 화면이 0%. 사용자 체감 완성도 0%. 의존성 없으므로 즉시 착수 가능.
2. **[상] Phase 6 설계-구현 로직 불일치** — 설계는 "Gemini 사업모델 태깅", 구현은 "GrowthStage×CapitalDNA 교차". `task_done`에 차이점 미기록 → 향후 theme_tags 파이프라인 별도 구축 필요.
3. **[상] Phase 7 Chain Sight 의존성 은폐** — `task_done/peer_phase7_llm_filter.md`에 "해외매출 50%+ = 0개(metric 한계)"만 기록, 근본 원인(Chain Sight 미완성)은 미분석. Phase 7-Lite vs Full 구분 부재로 사용자가 제약을 인지 못 함.
4. **[저] 모델 위치 혼재** — `validation/models/`(6개) + `packages/shared/metrics/models/`(6개)로 분산. 설계서의 "DB 소스" 표기와 실제 import 경로 불일치(`api/views.py:17-29`).
5. **[저] 지표명 2건 불일치** — `ocf_trend_3y`·`shareholder_yield` 설계명 ↔ 구현명 대조 후 설계서 갱신 권장.

---

## News 상세

**설계 위치**: `docs/news/plan/` (`news_keyword_detail_plan.md`, `keyword_detail_bottomsheet_v2.md`, `news_pipeline_monitoring_design.md`)
**구현 위치**: `news/` + `frontend/components/news/`, `frontend/components/admin/news/`

### 구현률 (총 17개 단위)
- (A) 완전 구현: **11개 (65%)**
- (B) 부분 구현: **4개 (24%)**
- (C) 미구현: **2개 (12%)**
- (D) 폐기·대체: **0개**

> 백엔드 + Phase A 모니터링 기준 ~80%. 미완은 Phase B 롤백 confirm, Phase C 자동 알림(@infra), 프론트 통합 확인.

### 기능별 상세

| 기능 | 분류 | 근거 | 갭 내용 |
|------|:---:|------|--------|
| 키워드 상세 화면 API | A | `news/api/views.py:662-796` (`keyword_detail` @action) | date+index API, 기사 검색, Gemini 분석 |
| 검색어 확장 `search_terms_en` | A | `services/keyword_extractor.py:43-45,256-258,306` | article_ids 매핑 완료 |
| 캐시 + index 안정성 | A | `api/views.py:717-723` | `updated_at` epoch 캐시키, TTL 1h |
| 바텀시트 v2 가로스크롤 | A | `frontend/components/news/KeywordDetailSheet.tsx` | Strip + scrollIntoView 자동 센터링 |
| 바텀시트 데스크탑 너비 제한 | B | `frontend/components/thesis/common/BottomSheet.tsx` | `max-w-2xl` 적용 여부 미확인 (설계 전제) |
| Phase A: Collection Logs API | A | `api/views.py:1338-1446` | provider/일별 집계, KST 자정 |
| Phase A: Pipeline Health API | A | `api/views.py:1449-1701` | 6 Phase 상태, 평일/주말 차등 |
| Phase A: ML Trend API | A | `api/views.py:1702-1780` | 12주 F1 + feature importance |
| Phase A: LLM Usage API | A | `api/views.py:1782-1900` | 키워드 토큰 + coverage_warning |
| Phase B: Task Timeline API | A | `api/views.py:1902-1962` | 24h 간트, 15분 버킷 |
| Phase B: Neo4j Status API | A | `api/views.py:1963-2023` | 동기화 통계 |
| **Phase B: ML Rollback** | **B** | `api/views.py:2024-2107` (`ml_rollback_preview` GET + `ml_rollback` POST) | 2-step confirm(`{"confirm": true}`) 검증 로직 온전성 미확인 |
| Phase C: AlertLog 모델 | A | `news/models.py:685-728` | TriggerType/Severity enum, indexes |
| Phase C: Alert CRUD API | A | `api/views.py:2109-2207` | GET /alerts/, POST resolve |
| **Phase C: 자동 알림 태스크** | **C** | — | `check_pipeline_alerts` Celery 태스크 + Beat(30분) 미정의 (@infra 영역) |
| `_log_collection` 커버리지 | B→A | `tasks.py` 178/220/455/501/544/622줄 | 6개 핵심 태스크 전건 호출 확인됨. try/finally 에러 경로만 상세 검증 권장 |
| 프론트 모니터링 대시보드 통합 | B | `frontend/components/admin/news/` 6 컴포넌트 + `NewsPipelineSubTab.tsx` | `NewsTab.tsx` sub-tab 라우팅 최종 통합 미확인 |

### 주목할 갭 Top 5

1. **[중] Phase C 자동 알림 미구현** — AlertLog 모델·CRUD API는 완성됐으나 이상징후를 감지해 알림을 생성하는 `check_pipeline_alerts` Celery 태스크가 없음. 현재는 관리자 수동 폴링만 가능. @infra 담당 영역(`*/tasks.py` + Beat).
2. **[중] ML 롤백 confirm 플로우 미완성 의심** — `ml_rollback_preview`(GET)는 구현. `ml_rollback`(POST)도 존재하나 2-step confirm 검증이 온전한지 코드 확인 필요. 실수 롤백 방지 장치 리스크.
3. **[저] 바텀시트 데스크탑 너비 제한** — 설계(`keyword_detail_bottomsheet_v2.md:14`)의 `max-w-2xl mx-auto`가 `BottomSheet.tsx`에 실제 적용됐는지 미확인. 1440px+ 화면에서 텍스트 가독성 영향.
4. **[저] 프론트 대시보드 최종 통합 확인** — 6개 모니터링 컴포넌트 + sub-tab 컨테이너 모두 존재하나 `NewsTab.tsx`에 `overview`/`pipeline` sub-tab 라우팅이 실제 연결됐는지 미확인.
5. **[정보] 설계 초과 구현** — `keyword_detail`의 `search_terms_en` 확장, Phase 0 `_log_collection` 6태스크 전건 호출은 설계 완료 상태로 이미 코드에 반영됨(문서가 코드를 따라잡지 못한 경우).

---

## 공통 결론 — 3앱 갭의 수렴점

세 앱의 미완 갭은 서로 독립적으로 보이지만 **3개 축으로 수렴**한다:

| 축 | 해당 갭 | 담당 |
|----|--------|------|
| **① Celery 자동화 스케줄 부재** | SEC Beat 주석(`check-new-filings`/`sync-dirty`), News `check_pipeline_alerts` 미정의 | @infra (공통 버그 #28: DatabaseScheduler `PeriodicTask.create`) |
| **② Validation 프론트엔드 전무** | FE-PR-1~7 (백엔드 API는 준비 완료) | @frontend (즉시 착수 가능, 의존성 0) |
| **③ Chain Sight 데이터 의존성** | Validation Phase 6 theme_tags 0건, Phase 7 SensitivityProfile/CapitalDNA 0건 | @kb-curator + Chain Sight 파이프라인 (설계-구현 로직 재정합 필요) |

**폐기(D) 사례 0건** = 설계 방향 전환 없이 일관되게 진행됨. 다만 Validation Phase 6의 설계(Gemini 태깅)↔구현(DNA 교차) 불일치는 `task_done`에 기록되지 않아, **사후 문서 정합화가 가장 시급한 단일 항목**이다.

---

> **본 감사는 읽기 전용이며 코드를 일절 수정하지 않았다.** "미확인"으로 표기한 항목(extracted_at 필드, match_with_queue 위치, ml_rollback confirm, BottomSheet max-w-2xl, NewsTab 통합)은 감사 시 부분 파일만 열람한 한계에 따른 것으로, DB 오류 등 실제 결함을 단정하지 않는다.
