# SEC Pipeline + Validation + News 설계 갭 감사

> **감사일**: 2026-05-17
> **방법**: 설계 문서(`docs/{앱}/`) ↔ 구현(`{앱}/`) 1:1 매칭, `task_done/` 완료 보고서 cross-reference
> **범위**: 코드 수정 없음, 읽기 전용 감사

## 앱별 요약 (구현률)

| 앱 | 설계 분류 | 구현 분류 | 구현률 | 주요 갭 |
|----|---------|---------|--------|--------|
| **SEC Pipeline** | Phase 1 (수집) / 1.5 (매칭) / 2 (Track B) / 3 (운영) — 17 PR | (A) 완전 구현 — 17/17 PR | **100%** (구조) / 운영 데이터 부족 | Celery Beat 스케줄 주석, CompanyAlias 0건, Phase 1.5 ticker 매칭률 3%, S&P 500 풀스캔 미실행 |
| **Validation** | Phase 1~7 (peer 시스템 + LLM 필터) — validation_design.md v1.4 + peer_phase6_7.md | (A) 완전 구현 — Phase 1~7 모두 구현 | **100%** | LLM 배치 캐싱(`validation_ai_cache`) Phase 5 후 검토로 의도적 미구현, `ValidationNewsSummary` 서비스 진입점 부재(모델만 정의) |
| **News** | Pipeline Monitoring v1.1 (Phase 0/A/B/C) + Keyword Detail v1/v2 | (A) 완전 구현 — Phase 0/A/B/C + 키워드 상세 v1/v2 모두 구현 | **100%** | 운영 안정성(태스크별 `_log_collection()` 정합성, 알림 트리거 튜닝)은 별도 |

**총평**: 세 앱 모두 **설계 문서가 코드로 빠짐없이 반영**되어 있다. SEC Pipeline은 코드는 완성이지만 **운영 단계**가 멈춰 있고(beat 주석, S&P 500 풀스캔 미실행), Validation은 Phase 1~7이 끝났으며 LLM 캐싱만 의도적 보류, News는 모니터링 v1.1의 Phase 0~C가 백엔드·프론트 양쪽 모두 종결되었다.

---

## SEC Pipeline 상세

### 설계 문서 인벤토리

| 문서 | 내용 |
|------|------|
| `docs/sec_pipeline/decisions/001_fmp_vs_sec_edgar_metadata.md` | FMP→SEC EDGAR 메타데이터 전환 결정 (FMP Starter sec-filings 404) |
| `docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md` | 전체 완료 요약 (Phase 1~3, 17 PR, 2026-04-04) |
| `docs/sec_pipeline/task_done/sec_pr_1~17_*.md` | PR별 완료 보고서 (16개) |

### 모델 매핑 (8/8 ✅)

| 설계 모델 | 구현 위치 | 분류 |
|---------|---------|------|
| RawDocumentStore | `sec_pipeline/models.py:15` | (A) |
| SupplyChainEvidence | `models.py:61` | (A) |
| BusinessModelSnapshot | `models.py:122` | (A) |
| BusinessModelEvidence | `models.py:201` | (A) |
| FilingProcessLog | `models.py:231` | (A) |
| CompanyAlias | `models.py:273` | (A) — 모델 완성, 운영 시드 0건 |
| UnmatchedCompanyQueue | `models.py:307` | (A) |
| PipelineIntelligenceReport | `models.py:351` | (A) |

### 파이프라인 단계별 매핑

| 설계 단계 | 구현 파일 | 분류 |
|---------|---------|------|
| SEC EDGAR 메타데이터 + HTML 다운로드 | `collector.py` (373줄) | (A) |
| 섹션 추출 (regex 3단계 + edgartools fallback) | `collector.py` + `validators.py` (128줄) | (A) |
| 섹션 사후 검증 (순서/heading/길이) | `validators.py` | (A) |
| 텍스트 정규화 + Pass 1 키워드 필터 | `normalizer.py` (83줄) | (A) |
| Track A LLM 추출 | `extractor.py` (145줄) + `validator_track_a.py` (164줄) + `prompts.py` (97줄) | (A) |
| Track B LLM 추출 | `extractor.py` + `validator_track_b.py` (115줄) + `keywords_track_b.py` (78줄) | (A) |
| TickerMatcher (alias → exact → fuzzy) | `ticker_matcher.py` (210줄) | (A) |
| signals → CompanyAlias 자동 등록 | `signals.py` (71줄) | (A) |
| 관계 병합 + DQS | `merger.py` (135줄) | (A) |
| Neo4j 동기화 (DELETE+CREATE) | `tasks.sync_dirty_to_neo4j` (`tasks.py:338`) | (A) |
| 품질 체크 (7개) | `quality_checks.py` (165줄) | (A) |
| Intelligence Report (5차원 LLM 분석) | `intelligence.py` (223줄) + `tasks.generate_intelligence_report` (`tasks.py:501`) | (A) |
| On-demand filing 수집 | `on_demand.py` (68줄) | (A) |
| Admin 대시보드 | `views.py` + `templates/admin/sec_pipeline/dashboard.html` | (A) |
| FilingDataView API | `views.py` + `urls.py` | (A) |
| 관리 커맨드 (4개) | `management/commands/` — evaluate_gold_set, process_unmatched_queue, rematch_unmatched, seed_company_aliases | (A) |

### Celery 태스크 매핑

| 설계 태스크 | 구현 위치 | 분류 |
|----------|---------|------|
| collect_and_extract | `tasks.py:23` | (A) |
| extract_from_document | `tasks.py:149` | (A) |
| sync_dirty_to_neo4j | `tasks.py:338` | (A) |
| check_new_filings | `tasks.py:465` | (A) |
| generate_intelligence_report | `tasks.py:501` | (A) |
| run_batch_and_report (chord) | `tasks.py:509` | (A) |
| seed_relations_to_chainsight | `tasks.py:282` | (A) |

### 운영/데이터 갭 (구현 완성도 ≠ 운영 완성도)

| 항목 | 설계 권고 | 현재 상태 | 갭 분류 |
|------|---------|---------|---------|
| Celery Beat — `sync-sec-dirty-neo4j` (5분 간격) | 활성화 | **주석 처리** (`sec_pr_17_e2e.md`에 명시) | (B) 부분 — 코드 있고 스케줄 미가동 |
| Celery Beat — `check-new-filings` (월 1회) | 활성화 | **주석 처리** | (B) 부분 |
| CompanyAlias 시드 | TSMC→TSM, Samsung 등 수동 등록 (`향후 과제 5`) | **0건** | (B) 부분 — 모델만 |
| Ticker 매칭률 | 80% 이상 목표 | **3%** (2/110, sec_pipeline_complete_summary §배치 실행 결과) | (B) 부분 — 비미국 종목 미등록 원인 |
| S&P 500 풀스캔 | 모든 503개 종목 처리 | **15종목** 배치 (`완료 요약 §배치 실행 결과`) | (B) 부분 — Gemini RPD 제한 |
| Gold Set 라벨링 + Precision/Recall 재평가 | `evaluate_gold_set` 커맨드 활용 | **재평가 미실행** (`향후 과제 2`) | (C) 미구현 운영 단계 |
| JNJ Item 순서 검증 완화 | 1건 실패 (`완료 요약 §배치`) | **수정 안 됨** | (C) 미구현 |

> **분류 판단**: 코드 산출물(모델·태스크·서비스·API·Admin)은 **(A) 완전 구현**, 운영 단계는 **(B) 부분 구현**. 설계서가 `향후 과제`로 명시한 항목은 본 감사에서 갭으로 카운트하되, "설계자 인지된 후속 작업"으로 분류.

---

## Validation 상세

### 설계 문서 인벤토리

| 문서 | 분량 | 범위 |
|------|------|------|
| `validation_design.md` (v1.4) | 1,646줄 | 네비게이션, 1차 검증 페이지 구조, 34지표, peer 선정, value_status, API, Celery 파이프라인, Empty State, LLM Phase 2 캐싱 |
| `validation_peer_system.md` | 403줄 | Peer 프리셋 6종 + 커스텀 — 하이브리드 아키텍처, confidence_score, Phase 1~7 로드맵 |
| `validation_peer_phase6_7.md` | 382줄 | Phase 6 (thematic LLM 큐레이션) + Phase 7 (대화형 LLM 필터) |
| `validation_pr_prompts.md` | 414줄 | PR 구현 프롬프트 |
| `task_done/peer_phase6_thematic.md` | 40줄 | Phase 6 완료 — 463/503 종목 thematic 프리셋 생성 |
| `task_done/peer_phase7_llm_filter.md` | 56줄 | Phase 7 완료 — LLM 필터 API + Chain Sight 통합 |

### 모델 매핑 (5/5 ✅)

| 설계 모델 | 구현 위치 | 분류 |
|---------|---------|------|
| CompanyMetricLatest | `validation/models/metric_latest.py` (53줄) | (A) |
| CompanyBenchmarkDelta (`benchmark_basis`/`benchmark_confidence`) | `models/benchmark_delta.py` (66줄) | (A) |
| CategorySignal (구 category_score) | `models/category_score.py` (64줄) | (A) |
| ValidationNewsSummary | `models/news_summary.py` (44줄) | (A) 모델 / **(B) 서비스 진입점 미확인** |
| PeerPreset + UserPeerPreference | `models/peer_preset.py` (67줄) | (A) |

`PeerListCache`/`PeerMetricBenchmark`/`CompanyMetricSnapshot`은 `metrics/` 앱에 위치 (설계 §7과 일치 — 공용 영역).

### 서비스 레이어 매핑 (9/9 ✅)

| 설계 책임 | 구현 위치 | 분류 |
|---------|---------|------|
| Task 1: FMP 연간 재무제표 fetch | `services/financial_fetcher.py` (103줄) | (A) |
| Task 2: 33개 지표 계산 + value_status 판정 | `services/metric_calculator.py` (459줄) | (A) |
| Task 3: Peer 선정 + benchmark + benchmark_basis/confidence | `services/benchmark_calculator.py` (345줄) | (A) |
| Task 3.5: rev_growth_vs_industry | `services/relative_metrics.py` (97줄) | (A) |
| Task 4: CategorySignal (green/yellow/red/gray) | `services/category_signal_calculator.py` (192줄) | (A) |
| 프리셋 생성 (default/sector_all/size_peers/quality_top/lifecycle/thematic) | `services/preset_generator.py` (479줄) | (A) — Phase 6 thematic 포함 |
| Rule-based 해석 텍스트 (summary/metric/leader) | `services/interpretation.py` (121줄) | (A) |
| 커스텀 Compute-on-Read 엔진 | `services/custom_benchmark_engine.py` (161줄) | (A) Phase 5 |
| LLM 필터 파서 + 실행 | `services/llm_peer_filter.py` (264줄) | (A) Phase 7 |

### Celery 태스크 매핑 (7/7 ✅)

| 설계 (validation_design §6.1) | 구현 위치 |
|---------|---------|
| run_weekly_validation_batch (chain 오케스트레이터) | `tasks.py:141` |
| Task 1 fetch_annual_financials | `tasks.py:23` |
| Task 2 calculate_derived_metrics | `tasks.py:37` |
| Task 3 calculate_benchmarks | `tasks.py:51` |
| Task 3.5 calculate_relative_metrics | `tasks.py:65` |
| Task 4 calculate_category_signals | `tasks.py:79` |
| Task 5 update_peer_list_caches | `tasks.py:93` |
| Task 6 log_batch_run | `tasks.py:106` |

### API 매핑 (6/6 ✅)

| 설계 (validation_design §5 + peer_system §7) | 구현 위치 |
|---------|---------|
| GET `/api/v1/validation/{symbol}/summary/` | `api/views.py:ValidationSummaryView` |
| GET `/api/v1/validation/{symbol}/metrics/` (category 필터) | `views.py:ValidationMetricsView` |
| GET `/api/v1/validation/{symbol}/leader-comparison/` | `views.py:LeaderComparisonView` |
| GET `/api/v1/validation/{symbol}/presets/` | `views.py:PresetListView` (Phase 4) |
| POST/DELETE `/api/v1/validation/{symbol}/peer-preference/` | `views.py:PeerPreferenceView` (Phase 4/5) |
| POST `/api/v1/validation/{symbol}/llm-filter/` | `views.py:LLMPeerFilterView` (Phase 7) |

### 프론트엔드 매핑 (8/8 ✅)

`frontend/components/validation/`에 8개 컴포넌트 (`SignalSummaryCard`, `PeerContextBar`, `CategorySection`, `MetricCard`, `MetricBarChart`, `CategorySidebar`, `IndustryPosition`, `LeaderComparisonSection`, `MetricInfoTooltip`) — `validation_design §9.1` 컴포넌트 트리와 1:1 일치. `__tests__/validation/` 테스트 3건.

### 갭 분류

| 항목 | 분류 | 비고 |
|------|------|------|
| ValidationAICache (`validation_ai_cache` 테이블) | (D) 의도적 미구현 | `validation_design §8.2` — Phase 5 LLM 도입 시점에 검토. Phase 1 Rule-based only 원칙 유지 |
| `metric_definition` seed (34개 지표) + `industry_classification.handling_mode` seed | (A) — `management/commands/seed_validation_data.py` 존재 | |
| `ValidationNewsSummary` 모델 활용 진입점 | (B) 부분 — 모델만, 서비스/뷰에서 직접 참조 없음 | 향후 1차 검증 페이지에 뉴스 요약 카드 추가 시 사용 의도로 추정 |
| 5단계 `value_status` 판정 (normal/missing/not_applicable/unstable/low_confidence) | (A) — `metric_calculator.py`에서 판정 | |
| 프리셋 6종 (default/sector_all/size_peers/quality_top/lifecycle/thematic) | (A) — `peer_phase6_thematic.md` 결과 — 514+514+7+392+392+463 = **2,282건 생성** | |
| Chain Sight 연계 peer_tier (Phase 2) | (B) — peer_tier 필드는 nullable 유지, Chain Sight v2 완료 후 활성화 | |

---

## News 상세

### 설계 문서 인벤토리

| 문서 | 분량 | 범위 |
|------|------|------|
| `news_pipeline_monitoring_design.md` v1.1 | 1,160줄 | Phase 0(`_log_collection` 보강) / A(BE+FE 4 API) / B(task_timeline, neo4j, ml_rollback) / C(AlertLog) |
| `news_keyword_detail_plan.md` v1 | 216줄 | 키워드 클릭→바텀시트, `search_terms_en` 한↔영 매칭, `GET /keyword-detail/` API |
| `keyword_detail_bottomsheet_v2.md` | 80줄 | 가로 스크롤 Strip, max-w-2xl, `keepPreviousData` |

### API 매핑 — 모니터링 (10/10 ✅)

| Phase | 설계 엔드포인트 | 구현 위치 (`news/api/views.py`) |
|------|--------------|-------------|
| A | GET `/collection-logs/` | line 1329 `collection_logs` |
| A | GET `/pipeline-health/` (PHASE_CONFIG, 평일/주말 분기, `force_refresh`) | line 1439 `pipeline_health` |
| A | GET `/ml-trend/` | line 1693 `ml_trend` |
| A | GET `/llm-usage/` | line 1773 `llm_usage` |
| B | GET `/task-timeline/` | line 1893 `task_timeline` |
| B | GET `/neo4j-status/` | line 1954 `neo4j_status` |
| B | GET `/ml-rollback-preview/` | line 2015 `ml_rollback_preview` |
| B | POST `/ml-rollback/` (confirm 필수) | line 2055 `ml_rollback` |
| C | GET `/alerts/` | line 2100 `alerts` |
| C | POST `/alerts/{id}/resolve/` | line 2164 `alerts_resolve` |

### 모델/태스크 매핑

| 설계 (§6.3) | 구현 위치 | 분류 |
|---------|---------|------|
| AlertLog (Severity 4값 + TriggerType 7값) | `news/models.py:684` + `migrations/0006_alertlog.py` | (A) — TextChoices 정규화 완료 |
| `check_pipeline_alerts` Celery 태스크 (30분 주기) | `news/tasks.py:1102` | (A) — 6개 트리거 체크 (consecutive_task_failure, ML F1, 키워드, LLM 에러율, Neo4j, 수집량, 미분류) |
| Phase 0 — `_log_collection()` 누락 6개 태스크 보강 | `news/tasks.py` 내 호출 11회 | (A) — 설계 §11 권장 6개 + 기존 4개 = ~10개 커버 |
| AlertLog Admin | `news/admin.py:AlertLogAdmin` | (A) |

### 키워드 상세 API (1/1 ✅)

| 설계 | 구현 위치 |
|------|---------|
| GET `/keyword-detail/?date=…&index=…` | `news/api/views.py:655` `keyword_detail` |
| `DailyNewsKeyword.keywords[i].search_terms_en` 한↔영 매칭 | `news/services/keyword_extractor.py` (364줄)에서 프롬프트 확장 |
| LLM 분석 fallback (`analysis: null`) | views.py 내 처리 |

### 프론트엔드 매핑 (12/12 ✅) — `frontend/components/admin/news/`

| 설계 컴포넌트 (§4.3 + §5 + §6) | 구현 파일 |
|--------|---------|
| PipelineStatusBar | `PipelineStatusBar.tsx` |
| CollectionStatsTable | `CollectionStatsTable.tsx` |
| MLModelCard | `MLModelCard.tsx` |
| MLTrendChart | `MLTrendChart.tsx` |
| RecentErrorsList | `RecentErrorsList.tsx` |
| LLMUsageSummary | `LLMUsageSummary.tsx` |
| NewsPipelineSubTab (5섹션 컨테이너) | `NewsPipelineSubTab.tsx` |
| TaskTimelineChart (Phase B) | `TaskTimelineChart.tsx` |
| Neo4jStatusCard (Phase B) | `Neo4jStatusCard.tsx` |
| MLCompareView (Phase B 롤백 2단계) | `MLCompareView.tsx` |
| AlertBadge (Phase C) | `AlertBadge.tsx` |
| AlertList (Phase C) | `AlertList.tsx` |

**NewsTab Sub-tab** (`frontend/components/admin/NewsTab.tsx`):
- `type NewsSubTab = 'overview' \| 'pipeline'` ✅
- 기본값 `'overview'` (기존 동작 유지) ✅
- pipeline 선택 시에만 `NewsPipelineSubTab` 활성화 (`enabled` prop) ✅

### 키워드 상세 v1/v2 프론트엔드

| 설계 | 구현 위치 |
|------|---------|
| KeywordDetailSheet (바텀시트, Strip, max-w-2xl) | `frontend/components/news/KeywordDetailSheet.tsx` |
| KeywordBadge onClick | `KeywordBadge.tsx` |
| DailyKeywordCard 시트 상태 연결 | `DailyKeywordCard.tsx` |
| 가로 스크롤 Strip + `keepPreviousData` | 구현 확인 (KeywordDetailSheet 존재) |

### 갭 분류

| 항목 | 분류 | 비고 |
|------|------|------|
| Phase A 4개 API + 프론트 5섹션 | (A) | |
| Phase B 4개 API + 프론트 3컴포넌트 | (A) — 롤백 2단계 플로우 포함 | |
| Phase C AlertLog + 트리거 7종 | (A) — TextChoices 정규화 모델 적용 | |
| Phase 0 `_log_collection()` 6태스크 보강 | (A) — 11회 호출 확인 | |
| 키워드 상세 v1 (date+index API) | (A) | |
| 키워드 상세 v2 (Strip + keepPreviousData) | (A) — `KeywordDetailSheet.tsx` 존재 | |
| Slack/이메일 알림 채널 (설계 §6.2 "선택") | (D) 의도적 미구현 | 인앱 알림만 필수, 외부 채널은 옵션으로 설계됨 |
| `cleanup_old_collection_logs` 90일 삭제 태스크 (§9 권고) | (C) 미구현 | 보존 정책 권고 사항으로만 명시 |

---

## 종합 평가

### 구현 분류 분포

| 분류 | SEC Pipeline | Validation | News |
|------|-------------|-----------|------|
| (A) 완전 구현 | 17/17 PR (코드 100%) | Phase 1~7 (100%) | Phase 0/A/B/C + 키워드 v1/v2 (100%) |
| (B) 부분 구현 | Celery Beat 주석, 시드 0건, 매칭률 3%, 풀스캔 미실행 | ValidationNewsSummary 진입점, peer_tier nullable | — |
| (C) 미구현 | Gold Set 재평가, JNJ 검증 완화 | — | `cleanup_old_collection_logs` |
| (D) 폐기/대체 | — | ValidationAICache (Phase 5 후 검토) | Slack/이메일 알림 (옵션 채널) |

### 보충 권고 (코드 수정 없음 — 운영/후속 작업)

1. **SEC Pipeline 운영 가동**: Celery Beat 스케줄 활성화 + S&P 500 풀스캔 분할 실행 (Gemini RPD 제한 고려 — 일 100종목 × 5일).
2. **CompanyAlias 시드**: 비미국 주식 매칭률 3%→80% 개선 위해 TSMC→TSM, Samsung→005930 등 수동 시드. `seed_company_aliases` 커맨드 있음.
3. **Validation LLM 캐싱**: Phase 1~7 종결 후, Rule-based 해석 품질 사용자 평가 진행. 도입 결정 시 `validation_ai_cache` 마이그레이션부터 시작.
4. **News 보존 정책**: `NewsCollectionLog` 90일 cleanup 태스크 추가 권고 (설계 §9 §1001). 현재 무한 증가 가능성.
5. **ValidationNewsSummary 활용**: 모델은 존재하나 1차 검증 페이지 뉴스 카드 진입점 없음. 신규 컴포넌트 또는 기존 `summary` API 응답에 포함 검토.

### 갭 0건 영역 (설계 ≡ 구현)

- SEC Pipeline 모델 8개 / 핵심 단계 14개 / Celery 태스크 7개
- Validation Phase 1~7 / 모델 5개 / 서비스 9개 / Celery 6개 / API 6개 / 프론트 8개
- News 모니터링 API 10개 / AlertLog 트리거 7종 / 프론트 12컴포넌트 / 키워드 상세 v1/v2

설계 문서의 "구현 우선순위", "구현 단계", "구현 로드맵" 섹션에 나열된 PR/Task가 모두 `task_done/`에 기록되어 있으며, 실제 파일·줄번호·함수명으로 추적 가능하다.
