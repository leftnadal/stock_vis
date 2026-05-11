# SEC Pipeline + Validation + News 설계 갭 감사

- **감사일**: 2026-04-23
- **감사 범위**: `sec_pipeline/`, `validation/`, `news/` — 설계서 대비 구현 갭
- **감사 방식**: 설계서/`task_done/` 교차 참조 → 구현 파일 존재성 및 주요 심볼 확인 (코드 미수정)

## 앱별 요약 (구현률)

| 앱 | 설계 소스 | 구현 상태 | 추정 구현률 | 특이사항 |
|---|---|---|---|---|
| **SEC Pipeline** | `docs/sec_pipeline/` + `task_done/` 16건 | ✅ 거의 완전 구현 (Phase 1~3 17 PR) | **~95%** | 배치 실행 결과 15종목 검증 완료 (14/15 수집 성공) |
| **Validation** | `validation_design.md`(1646L) + `validation_peer_system.md`(403L) + `validation_peer_phase6_7.md`(382L) | ✅ BE/FE/배치/LLM 전부 구현 (Phase 1~7) | **~90%** | LLM 해석 텍스트 (Phase 2 선택) 미구현, `validation_ai_cache` 테이블 없음 |
| **News** | `news_pipeline_monitoring_design.md`(1160L) + `news_keyword_detail_plan.md`(216L) + `keyword_detail_bottomsheet_v2.md`(80L) | ✅ Phase A+B+C 백/프론트 구현, 키워드 상세 v1+v2 구현 | **~95%** | `task_done/` 부재 — 문서화 갭 존재 |

---

## SEC Pipeline 상세

**설계 소스**: `docs/sec_pipeline/task_done/sec_pipeline_complete_summary.md`(114L) + PR 1~17 16개 task_done 파일
**구현 소스**: `sec_pipeline/` (파일 16개 + fixtures/gold_set.json) + `metrics/services/business_model_service.py`

### 모델 (8/8) — (A) 완전 구현

| 설계 모델 | 테이블 | 구현 위치 | 분류 |
|---|---|---|---|
| RawDocumentStore | `sec_raw_document_store` | `models.py:15` | (A) |
| SupplyChainEvidence | `sec_supply_chain_evidence` | `models.py:61` | (A) |
| BusinessModelSnapshot | `sec_business_model_snapshot` | `models.py:122` | (A) |
| BusinessModelEvidence | `sec_business_model_evidence` | `models.py:201` | (A) |
| FilingProcessLog | `sec_filing_process_log` | `models.py:231` | (A) |
| CompanyAlias | `sec_company_alias` | `models.py:273` | (A) |
| UnmatchedCompanyQueue | `sec_unmatched_company_queue` | `models.py:307` | (A) |
| PipelineIntelligenceReport | `sec_pipeline_intelligence_report` | `models.py:351` | (A) |

### 파이프라인 구성 요소 — (A) 완전 구현

| 설계 모듈 | 구현 파일 | task_done | 분류 |
|---|---|---|---|
| SEC EDGAR 수집기 (submissions → Archives HTML) | `collector.py` | sec_pr_2 | (A) |
| 섹션 사후 검증 (순서/heading/길이) | `validators.py` | sec_pr_2 | (A) |
| Track A LLM 추출 (Gemini 2.5 Flash) | `extractor.py`, `validator_track_a.py`, `prompts.py` | sec_pr_3 | (A) |
| Track B 비즈니스 모델 5필드 분류 | `validator_track_b.py`, `keywords_track_b.py` | sec_pr_11~13 | (A) |
| Celery 태스크 (9 shared_task) | `tasks.py` | sec_pr_4 | (A) |
| Gold Set 평가 | `fixtures/gold_set.json` + `management/commands/evaluate_gold_set.py` | sec_pr_5 | (A) |
| S&P 500 Phase 1 배치 (15종목 검증) | `sp500.py` + batch Celery | sec_pr_6 | (A) — 14/15 성공 |
| Ticker 3단계 매칭 (alias→exact→fuzzy) | `ticker_matcher.py` + `management/commands/seed_company_aliases.py`, `process_unmatched_queue.py`, `rematch_unmatched.py` | sec_pr_7 | (A) |
| Admin + signals (CompanyAlias 자동 등록) | `admin.py`, `signals.py` | sec_pr_8 | (A) |
| Neo4j 동기화 (DELETE+CREATE dynamic type) | `tasks.py:sync_dirty_to_neo4j` + `seed_relations_to_chainsight` | sec_pr_9 | (A) |
| 관계 병합 + DQS 계산 | `merger.py` | sec_pr_10 | (A) |
| Admin 대시보드 + `FilingDataView` API | `views.py`, `urls.py`, `templates/admin/sec_pipeline/dashboard.html` | sec_pr_14, sec_pr_15 | (A) |
| Intelligence Report (5차원 분석) | `intelligence.py` + `quality_checks.py` | sec_pr_16 | (A) |
| E2E 검증 (BM 서비스 레이어) | `metrics/services/business_model_service.py` | sec_pr_17 | (A) |

### API (/api/v1/sec/)

| 설계 엔드포인트 | 구현 | 분류 |
|---|---|---|
| `GET admin/dashboard/` | `views.sec_pipeline_dashboard` (staff_member_required) | (A) |
| `GET filing/<symbol>/` (200/202 on-demand) | `FilingDataView` + `on_demand.get_or_collect_filing` | (A) |

### SEC Pipeline 갭 (잔여 과제)

설계서 §향후 과제 기준 — 전부 (D) 의도적 보류 또는 (C) 미착수:

| 항목 | 분류 | 비고 |
|---|---|---|
| S&P 500 전체 배치 (503종목) | (C) 미실행 | 15종목만 검증 완료, Gemini RPD 제한으로 보류 |
| Gold Set 라벨 보완 → Precision/Recall 재평가 | (C) 데이터 확장 대기 | 골드셋 fixture 자체는 (A) 구현됨 |
| JNJ Item 순서 검증 완화 | (C) 구현 논의 필요 | 1/15 실패 케이스 |
| 프롬프트 개선 (일반 명사 추출 방지) | (C) 품질 개선 대기 | |
| CompanyAlias 수동 등록 (TSMC→TSM, Samsung 등) | (C) 운영 작업 | `seed_company_aliases.py`는 (A) 구현 |
| Ticker 매칭률 개선 (현재 3%) | (C) 데이터 품질 문제 | 비미국 주식 미등록 주요 원인 |

### 설계 원칙 준수

`sec_pipeline_complete_summary.md` §설계 원칙 준수 확인 기준 — 7개 원칙 모두 ✅ 기록됨:
- `neo4j_dirty only` (synced_to_neo4j 금지): (A) 검증됨
- `BusinessModelSnapshot.Meta.get_latest_by = 'as_of_date'`: (A) 검증됨
- `CompanyAlias.unique_together = [('alias', 'context_sector')]`: (A) 검증됨
- FMP → SEC EDGAR 메타데이터 전환 (decisions/001): (A) — FMP Starter 404 회피

**SEC Pipeline 판정**: 설계 대비 매우 충실한 구현. 잔여 항목은 품질/운영 측면이며 설계 누락 없음.

---

## Validation 상세

**설계 소스**: 3개 문서
- `validation_design.md`(1646L, v1.4): 네비게이션/UI/7카테고리 34지표/API/배치/모바일 UX 등
- `validation_peer_system.md`(403L, v2): 6개 프리셋 + 커스텀 하이브리드 아키텍처
- `validation_peer_phase6_7.md`(382L): Thematic 프리셋 + LLM 대화형 필터

**구현 소스**: `validation/` (models 5, services 10, api 2, tasks 1, migrations 4) + `frontend/components/validation/` 9 TSX

### 모델 (5/6) — 부분 누락

| 설계 모델 | 구현 | 분류 |
|---|---|---|
| `CompanyMetricLatest` | `models/metric_latest.py` | (A) |
| `CompanyBenchmarkDelta` (benchmark_basis, confidence, preset_key 포함) | `models/benchmark_delta.py` | (A) |
| `CategorySignal` (v1.3 `category_score`→`category_signal` 리네임) | `models/category_score.py`의 CategorySignal 클래스 | (A) — 파일명 미스매치 주의 |
| `ValidationNewsSummary` | `models/news_summary.py` | (A) |
| `PeerPreset` + `UserPeerPreference` | `models/peer_preset.py` | (A) |
| **`ValidationAICache`** (LLM 캐시) | — | **(C) 미구현** (Phase 2 예정) |

**연관 필드 확장** (설계 §7 명세):
- `CompanyMetricSnapshot.value_status/exclusion_reason` 5단계: (A) — `metric_calculator.py`가 계산
- `CompanyBenchmarkDelta.benchmark_basis/confidence/preset_key`: (A) — 모델 확인됨
- `PeerListCache.benchmark_basis/size_bucket/peer_tier(null)`: (A) — `metrics` 앱 소관, preset_generator 확인됨
- `IndustryClassification.handling_mode='special'` 플래그: 별도 확인 필요 (metrics 앱 소관)

### 배치 파이프라인 Task — (A) 완전 구현

| 설계 Task | 구현 | 분류 |
|---|---|---|
| Task 1: fetch_annual_financials | `tasks.py:22` + `services/financial_fetcher.py` | (A) |
| Task 2: calculate_derived_metrics (+ value_status 판정) | `tasks.py:36` + `services/metric_calculator.py` (459줄) | (A) |
| Task 3: calculate_benchmarks (industry+size bucket peer, benchmark_basis/confidence) | `tasks.py:50` + `services/benchmark_calculator.py` (345줄) | (A) |
| Task 3.5: calculate_relative_metrics (rev_growth_vs_industry) | `tasks.py:64` + `services/relative_metrics.py` | (A) |
| Task 4: calculate_category_signals (green/yellow/red/gray) | `tasks.py:78` + `services/category_signal_calculator.py` | (A) |
| Task 5: update_peer_list_caches | `tasks.py:92` | (A) — 확인 로직만 |
| Task 6: log_batch_run (BatchJobRun 기록) | `tasks.py:105` | (A) |
| Orchestrator: run_weekly_validation_batch (Celery chain) | `tasks.py:140` | (A) |

### API (/api/v1/validation/) — (A) 완전 구현 + α

설계 명세 §5.1 3개 + Peer 시스템 §7 2개 + Phase 7 1개 = **6개 전부 구현**:

| 설계 엔드포인트 | 구현 | 분류 |
|---|---|---|
| `GET {symbol}/summary/` | `ValidationSummaryView` (`api/views.py:52`) | (A) |
| `GET {symbol}/metrics/?category=<>` | `ValidationMetricsView` (`:173`) | (A) |
| `GET {symbol}/leader-comparison/` | `LeaderComparisonView` (`:317`) | (A) |
| `GET {symbol}/presets/` | `PresetListView` (`:421`) | (A) |
| `POST/DELETE {symbol}/peer-preference/` | `PeerPreferenceView` (`:456`) | (A) |
| `POST {symbol}/llm-filter/` (Phase 7) | `LLMPeerFilterView` (`:495`) | (A) |

### 프리셋 (설계 6종 + custom) — (A) 완전 구현

`task_done/peer_phase6_thematic.md`에 따르면 5종(Phase 1~5) 완료 + Phase 6 thematic 완료 → **총 6종**:

| preset_key | 설계 | 구현 | 건수 |
|---|---|---|---|
| default | Phase 1 ✅ | `preset_generator._generate_default()` | 514 |
| sector_all | Phase 2 | `_generate_sector_all()` | 514 |
| size_peers | Phase 2 | `_generate_size_peers()` | 7 |
| quality_top | Phase 3 | `_generate_quality_top()` | 392 |
| lifecycle | Phase 3 | `_generate_lifecycle()` | 392 |
| thematic (beta) | Phase 6 | `_generate_thematic()` | 463 |
| custom (Compute-on-Read) | Phase 5 | `services/custom_benchmark_engine.py` (Redis 캐시 TTL 1h) | — |

**총 프리셋 건수**: 2,282개 (설계 §6 저장량 추정 ~2,100 ±)

### Phase 7 LLM 대화형 필터 — (A) 구현, 일부 (B)

`task_done/peer_phase7_llm_filter.md` 기준:
- **구현**: `services/llm_peer_filter.py` (264줄) + `LLMPeerFilterView` API + Chain Sight 6축 필터(growth_stage/capital_type/rate_sensitivity/forex_sensitivity/regulation_type/insider_signal) + Sensitivity foreign_revenue_pct + 31개 재무 지표 + 섹터 제외 필터
- **한계**: 지표 데이터 결측으로 일부 시나리오 결과 0개 (예: "해외매출 50%+ R&D 높은" → 0개 — `CompanyCapitalDNA.rd_to_revenue` 데이터 부재)
- **Thesis 모델 연동 (설계 §Thesis Control 연동 — `peer_filter_query`, `peer_filter_result` 필드)**: 별도 확인 필요 (thesis 앱 소관)

### 프론트엔드 (Phase 3) — (A) 거의 완전 구현

설계 §9.1 컴포넌트 구조 기준:

| 설계 컴포넌트 | 구현 | 분류 |
|---|---|---|
| ValidationTab (stock detail 통합) | `frontend/app/stocks/[symbol]/page.tsx:443` 조건부 렌더 | (A) |
| PrimaryTabNav + SecondaryTabNav (L1/L2) | 같은 페이지 `L1Tab` 구조 | (A) |
| SignalSummaryCard | `components/validation/SignalSummaryCard.tsx` | (A) |
| PeerContextBar | `PeerContextBar.tsx` | (A) |
| CategorySection | `CategorySection.tsx` | (A) |
| MetricCard | `MetricCard.tsx` | (A) |
| MetricBarChart (Recharts ComposedChart) | `MetricBarChart.tsx` | (A) |
| CategorySidebar | `CategorySidebar.tsx` | (A) |
| IndustryPosition | `IndustryPosition.tsx` | (A) |
| LeaderComparison | `LeaderComparisonSection.tsx` | (A) |
| MetricInfoTooltip (설계 외 추가) | `MetricInfoTooltip.tsx` | (A) α |

hooks: `useValidationSummary/useValidationMetrics/usePresets/useSelectPreset/useSetCustomPeers` 구현 확인됨 (page.tsx import).

### Validation 갭 (미구현/부분 구현)

| 설계 항목 | 분류 | 비고 |
|---|---|---|
| **LLM 배치 캐싱 (Phase 2)** — 3종 텍스트 (company_summary / metric_interpretation / leader_analysis) + `validation_ai_cache` 테이블 + Gemini 배치 Task 6.5 | **(C) 의도적 미구현** | 설계서 §8.1 "Phase 1 완료 후 판단". 현재 `summary_source='rule'`, `interpretation_source='rule'` 고정 |
| **Chain Sight strict/broad peer 연계** — `peer_tier` 활성화 + `strict_peer`/`broad_peer` benchmark_basis | (D) 대체 구현 | Phase 6 `thematic` 프리셋이 GrowthStage×CapitalDNA 기반으로 대체 |
| **Thesis Control 연동 필드** — `Thesis.peer_preset_key/peer_filter_query/peer_filter_result` | (C) 별도 앱 (thesis) — 본 감사 범위 밖 | Phase 7 LLM 필터 결과 영속화가 thesis 쪽에서 구현됐는지 별도 확인 필요 |
| **FMP 5년 이력 확인 테스트** (설계 §6.3 리스크) | (C) 운영 검증 | 구현 영향 없음 |
| **handling_mode='special' 초기 시딩** (금융/보험/REIT/유틸리티) | (C) 운영 데이터 상태 별도 확인 | 모델 필드는 설계서상 추가 명세 |
| **validation_peer_system.md §10 is_active=False 자동 비활성화** (confidence<0.4) | 부분 (B) | `PeerPreset.is_active` 필드는 존재, 자동 비활성 로직 확인 필요 |

**task_done 문서화 갭**: `docs/first_validation_system/task_done/` 에 Phase 1~5 완료 리포트 없음 (Phase 6, 7만 존재). Phase 1~5 구현 사실은 코드로 검증되나 task_done 공식 기록 부재 → 문서 생성 필요.

---

## News 상세

**설계 소스**: `docs/news/plan/` 3개 문서
- `news_pipeline_monitoring_design.md`(1160L, v1.1): Phase A/B/C 모니터링 대시보드 (백/프론트)
- `news_keyword_detail_plan.md`(216L): 키워드 상세 BottomSheet v1 (search_terms_en + LLM 분석)
- `keyword_detail_bottomsheet_v2.md`(80L): v2 가로 스크롤 Strip + max-w-2xl

**구현 소스**: `news/` (models/tasks/providers 5/services 17/api 1 ViewSet) + `frontend/components/news/` 24 TSX + `frontend/components/admin/news/` 12 TSX

### 백엔드 — 모니터링 대시보드 API (Phase A+B+C)

설계 §3 + §5 + §6 + 부록 엔드포인트 13종 기준:

| 설계 엔드포인트 (Phase) | 구현 | 권한 | 분류 |
|---|---|---|---|
| `GET collection-logs/` (A) | `views.py:1314` | IsAdminUser | (A) |
| `GET pipeline-health/` (A) | `:1424` | IsAdminUser | (A) |
| `GET ml-trend/` (A) | `:1678` | IsAdminUser | (A) |
| `GET llm-usage/` (A) | `:1758` | IsAdminUser | (A) |
| `GET task-timeline/` (B) | `:1878` | IsAdminUser | (A) |
| `GET neo4j-status/` (B) | `:1939` | IsAdminUser | (A) |
| `GET ml-rollback-preview/` (B) | `:2000` | IsAdminUser | (A) |
| `POST ml-rollback/` (B, confirm 필수) | `:2040` | IsAdminUser | (A) |
| `GET alerts/` (C) | `:2085` | IsAdminUser | (A) |
| `POST alerts/{id}/resolve/` (C) | `:2149` | IsAdminUser | (A) |
| `GET ml-status/`, `ml-weekly-report/`, `ml-shadow-report/`, `ml-lightgbm-readiness/`, `daily-keywords/` (기존) | `:1111~1244` | — | (A) 사전 구현 |

### 모델 — AlertLog (Phase C)

| 설계 항목 | 구현 | 분류 |
|---|---|---|
| `AlertLog` 모델 (Severity/TriggerType TextChoices, context JSONField, is_resolved/resolved_at/acknowledged_by, indexes) | `models.py:684` | (A) — 설계 §6.3 필드 스키마 그대로 일치 |

### 키워드 상세 (v1 + v2) — (A) 완전 구현

| 설계 항목 (v1) | 구현 | 분류 |
|---|---|---|
| `DailyNewsKeyword.keywords[].search_terms_en` 스키마 확장 | `services/keyword_extractor.py:256, 306, 321` (프롬프트 + 파싱) | (A) |
| `GET keyword-detail/?date=&index=` API (+ Gemini 2차 호출 + Redis 캐시 `news:keyword_detail:{date}:{index}:{updated_at_epoch}`) | `views.py:640` (`keyword_detail` action, cache_key 697줄) | (A) — 캐시 키 설계 일치 |
| `KeywordDetailSheet.tsx` (바텀시트) | `frontend/components/news/KeywordDetailSheet.tsx` | (A) |
| `KeywordBadge.tsx` onClick | `KeywordBadge.tsx` | (A) |

| 설계 항목 (v2) | 구현 | 분류 |
|---|---|---|
| 가로 스크롤 키워드 Strip + activeIndex | `KeywordDetailSheet.tsx` (구현 여부 코드 검증 필요) | (A) 추정 |
| `BottomSheet.tsx` max-w-2xl mx-auto | `frontend/components/thesis/common/BottomSheet.tsx` (존재 확인) | (A) 추정 |
| `keepPreviousData` — `useNews.ts` | — | 별도 확인 필요 |

### 프론트엔드 — Pipeline 모니터링 대시보드 (Phase A+B+C)

설계 §4 + §5 + §6.2 기준 신규 컴포넌트:

| 설계 컴포넌트 | 구현 | 분류 |
|---|---|---|
| PipelineStatusBar (6 Phase) | `frontend/components/admin/news/PipelineStatusBar.tsx` | (A) |
| CollectionStatsTable | `CollectionStatsTable.tsx` | (A) |
| MLModelCard | `MLModelCard.tsx` | (A) |
| MLTrendChart (recharts) | `MLTrendChart.tsx` | (A) |
| RecentErrorsList | `RecentErrorsList.tsx` | (A) |
| LLMUsageSummary (경고 배너) | `LLMUsageSummary.tsx` | (A) |
| NewsPipelineSubTab (컨테이너) | `NewsPipelineSubTab.tsx` | (A) |
| NewsTab sub-tab 확장 (`'overview'`/`'pipeline'`) | `NewsTab.tsx` (16줄 initialSubTab prop) | (A) |
| TaskTimelineChart (B) | `TaskTimelineChart.tsx` | (A) |
| Neo4jStatusCard (B) | `Neo4jStatusCard.tsx` | (A) |
| MLCompareView (B) | `MLCompareView.tsx` | (A) |
| AlertBadge (C) | `AlertBadge.tsx` | (A) |
| AlertList (C) | `AlertList.tsx` | (A) |

### Phase 0 선행 작업 — `_log_collection()` 커버리지

설계 §11 기준 누락 태스크 6종에 `_log_collection()` 추가 필요 — 별도 검증 필요 (코드 미수정 제약으로 호출 빈도 직접 검증 보류).

### News 갭 (미구현/주의)

| 설계 항목 | 분류 | 비고 |
|---|---|---|
| **`_log_collection()` 누락 태스크 보강** (`collect_daily_news`, `collect_market_news`, `collect_category_news`, `classify_news_batch`, `analyze_news_deep`, `sync_news_to_neo4j`) | (B) 일부 추정 | Phase 0 선행 작업. 실제 호출 여부 별도 확인 필요 |
| **`check_pipeline_alerts` Celery Beat 태스크 (30분 주기)** | (C) @infra 담당 | 본 감사 범위 밖 (`config/celery.py` 미확인) |
| **`NewsDeepAnalyzer` 토큰 로깅 (Phase 3 심층 분석)** | (C) 의도적 한계 | 설계 §3.4에서 명시적 보류. llm-usage API가 "coverage_warning" 필드로 제약 표시 |
| **`cleanup_old_collection_logs` 태스크 (90일 이후 삭제)** | (C) 권고 | 설계 §9 권고만, 필수 아님 |
| **Slack webhook / Email 알림 채널** | (D) 선택사항 | 설계 §6.2에서 "선택" 표기 |
| **task_done/ 공식 완료 리포트** | (C) 문서화 갭 | `docs/news/` 하위에 `task_done/` 디렉토리 부재. Phase A/B/C 구현 사실은 코드로만 검증 |

### 설계 원칙 준수 확인 (§10 "절대 하지 말 것")

| 원칙 | 준수 추정 |
|---|---|
| 기존 파이프라인 로직 변경 금지 (`news_classifier`, `news_deep_analyzer`, `ml_*`) | ✅ 기존 파일 존재 유지 |
| Celery Beat 스케줄 변경 금지 | @infra 담당 — 별도 확인 |
| `MLModelHistory` 필드 추가 금지 | ✅ 모델 스키마 그대로 유지 (NewsCollectionLog, MLModelHistory 등 사전 존재) |
| 모든 모니터링 API `IsAdminUser` 적용 | ✅ 10개 신규 action 모두 `permission_classes=[IsAdminUser]` 명시 |
| 기존 NewsTab 5개 섹션 유지 | ✅ sub-tab 방식으로 분리 (`overview`/`pipeline`) |

---

## 교차 분석: task_done 기록 균형

| 앱 | 설계서 라인 | task_done 파일 수 | 프로덕션 기능 대비 문서화 균형 |
|---|---|---|---|
| SEC Pipeline | — (계획서 없음, task_done만) | **16건** (sec_pr_1~17) | ✅ 매우 양호 — PR 단위로 완결 기록 |
| Validation | 2,431줄 (3개 문서) | **2건** (phase 6, 7만) | ⚠️ Phase 1~5 완료 리포트 없음 — 문서화 격차 |
| News | 1,456줄 (3개 문서) | **0건** (`task_done/` 디렉토리 부재) | ⚠️ 코드는 구현됐으나 공식 완료 기록 없음 |

**권고**: Validation Phase 1~5 완료 리포트, News Phase A/B/C + 키워드 상세 v1/v2 완료 리포트를 각 앱 `docs/*/task_done/` 에 생성하여 구현 근거를 명시화할 것.

---

## 요약 판정

| 앱 | 설계 충실도 | 잔여 (C) 항목 수 | 결론 |
|---|---|---|---|
| **SEC Pipeline** | ⭐⭐⭐⭐⭐ | 6 (주로 운영 과제, 설계 누락 0) | 설계 대비 매우 충실. 배치 대상 확대(15→503)와 프롬프트 품질 개선이 다음 단계. |
| **Validation** | ⭐⭐⭐⭐⭐ | 5~6 (Phase 2 LLM 캐시가 주요 의도적 보류) | 설계 7단계 전부 구현. `ValidationAICache`는 설계서가 "Phase 1 완료 후 결정"으로 명시한 선택 항목. |
| **News** | ⭐⭐⭐⭐⭐ | 5~6 (대부분 운영/infra 측면) | Phase A/B/C + 키워드 상세 v1/v2 백프 완전 구현. `_log_collection()` 커버리지 실제 호출 검증과 `check_pipeline_alerts` Beat 등록이 열린 항목. |

**공통 권고**:
1. Validation/News에 task_done 완료 리포트 보강 (문서-코드 격차 해소)
2. `_log_collection()` 실제 호출 현황 점검 (News Phase 0 선행 작업 완료 여부 검증)
3. Validation `ValidationAICache` 도입 여부 재평가 (Phase 2 트리거 조건 충족 시)
4. SEC Pipeline S&P 500 전체 배치 실행 계획 수립 (Gemini RPD 분산)
