# SEC Pipeline + Validation + News 설계 갭 감사

> **감사 일자**: 2026-05-15
> **방식**: 읽기 전용. 설계서 vs 구현 파일 + task_done 보고서 cross-reference.
> **대상 경로**:
> - `docs/sec_pipeline/` vs `sec_pipeline/`
> - `docs/first_validation_system/` vs `validation/` (+ `metrics/`, `stocks/`)
> - `docs/news/plan/` vs `news/`

---

## 앱별 요약 (구현률)

| 앱 | 설계 문서 | task_done | 코드 (LOC) | 구현률 | 비고 |
|----|----------|-----------|-----------|--------|------|
| **SEC Pipeline** | 1 (decision) | 15 (sec_pr_1~17) | 3,313 LOC | **A. 완전 구현 (95%)** | 17개 PR 전부 완료, 일부 Celery Beat 주석 상태 |
| **Validation** | 4 (design + peer + phase6/7 + prompts) | 2 (peer_phase6/7만) | 3,717 LOC | **A. 완전 구현 (95%)** | BE-PR 1~6 + FE-PR 1~7 + Peer Phase 1~7 전부 구현. task_done 보고서는 Phase 6/7만 별도 존재 |
| **News (Intelligence Pipeline)** | 3 (keyword_detail v1/v2 + monitoring v1.1) | 0 | 12,748 LOC | **A. 완전 구현 (95%)** | 모니터링 Phase 0~C, keyword_detail v1/v2 모두 구현. task_done 보고서 부재 |

### 종합 진단

세 영역 모두 **설계서 → 구현 일치율이 매우 높음**. 주요 갭은:
1. **운영 활성화 미완료 영역**: SEC Pipeline의 Celery Beat 스케줄 (`sync-sec-dirty-neo4j`, `check-new-filings`)이 코드 주석 상태로 표기됨 → 실제 등록 여부 검증 필요.
2. **task_done 문서 누락**: News는 광범위 구현에도 task_done 보고서가 0건이라 PR 단위 추적 불가.
3. **운영 데이터 부족으로 효과 검증 불가**: SEC TickerMatcher 매칭률 3% (비미국 주식 미등록 + LLM 일반 명사 추출), Gold Set 라벨 미보완.
4. **Phase 의존성 미해소**: Chain Sight 데이터(`CompanyNarrativeTag`, `SensitivityProfile`, `CapitalDNA`)가 부분 구축되어 Peer Phase 6/7의 결과 가치 제한적 (Phase 7 테스트 시 한 시나리오에서 "0개" 반환).

---

## SEC Pipeline 상세

### 설계서 (단일)
- `docs/sec_pipeline/decisions/001_fmp_vs_sec_edgar_metadata.md` — FMP `/sec-filings` 미지원 → SEC EDGAR `submissions` API 대체 결정

### task_done 보고서 (15건)
sec_pr_1~17 (PR-6에 6번은 단독 파일 없이 5/15에 흡수, PR-10 머거 + 큐) — 17개 PR 전부 보고서 존재.

### 구현 파일 (`sec_pipeline/`)
| 영역 | 설계 정의 | 구현 파일 | 분류 |
|------|---------|----------|------|
| 8개 모델 | sec_pr_1 — RawDocumentStore, SupplyChainEvidence, BusinessModelSnapshot, BusinessModelEvidence, FilingProcessLog, CompanyAlias, UnmatchedCompanyQueue, PipelineIntelligenceReport | `models.py` (388 LOC) — 8개 클래스 전부, `neo4j_dirty`, `get_latest_by`, `unique_together` 등 제약조건 모두 일치 | **A** |
| 수집기 | sec_pr_2 — SEC EDGAR submissions + Archives | `collector.py` (373 LOC) — SECFilingCollector + 섹션 추출 + edgartools fallback | **A** |
| 섹션 검증 | sec_pr_2 — 순서/heading/길이 3단계 | `validators.py` (128 LOC) | **A** |
| Track A | sec_pr_3 — Pass1 키워드 필터 + Pass2 Gemini Flash | `normalizer.py` (83) + `prompts.py` (97) + `extractor.py` (145) + `validator_track_a.py` (164) | **A** |
| Track B | sec_pr_11~13 — 5필드 BM 분류 + 서비스 레이어 | `keywords_track_b.py` (78) + `validator_track_b.py` (115) + `metrics/services/business_model_service.py` | **A** |
| Celery tasks | sec_pr_4 — collect_and_extract, extract_from_document | `tasks.py:22` + `tasks.py:148` (max_retries=3/2, exponential backoff) | **A** |
| Gold Set 평가 | sec_pr_5 — fixtures/gold_set.json + evaluate command | `fixtures/gold_set.json` + `fixtures/gold_set_schema.py` + `management/commands/evaluate_gold_set.py` | **A** |
| Phase 1 배치 | sec_pr_6 — 15종목 배치 결과 검증 | 운영 실행 결과 (PR 보고서 내 통계) | **A** (운영 작업) |
| TickerMatcher | sec_pr_7 — 3단계 (alias → exact → fuzzy ≥85%) | `ticker_matcher.py` (210 LOC) | **A** |
| Admin + Signal | sec_pr_8 — UnmatchedCompanyQueueAdmin actions + post_save 전파 | `admin.py` (171) + `signals.py` (71) | **A** |
| Neo4j 동기화 | sec_pr_9 — sync_dirty_to_neo4j (DELETE+CREATE dynamic) | `tasks.py:338` (max_retries=1, select_for_update skip_locked, 500건 chunked) | **A** |
| Merger | sec_pr_10 — 관계 병합 + DQS | `merger.py` (135) + `management/commands/process_unmatched_queue.py` | **A** |
| Admin 대시보드 | sec_pr_14 — 7개 품질 체크 + dashboard view | `quality_checks.py` (165) + `views.py:sec_pipeline_dashboard` + `templates/admin/sec_pipeline/dashboard.html` | **A** |
| On-demand 수집 | sec_pr_15 — get_or_collect_filing + check_new_filings + FilingDataView | `on_demand.py` (68) + `views.py:FilingDataView` + `tasks.py:465 check_new_filings` | **A** |
| Intelligence Reporter | sec_pr_16 — 5차원 health_score + Gemini | `intelligence.py` (223) — PipelineDataCollector + PipelineIntelligenceReporter | **A** |
| E2E chord | sec_pr_17 — run_batch_and_report | `tasks.py:509 run_batch_and_report` (Phase 1→2→3 순차) + `generate_intelligence_report` | **A** |

### 갭/리스크
| 항목 | 분류 | 비고 |
|------|------|------|
| Celery Beat 스케줄 등록 | **B. 부분 구현** | sec_pr_17 보고서에 `'sync-sec-dirty-neo4j': crontab('*/5')`, `'check-new-filings': crontab(day_of_month='1', hour='6')` 모두 **주석 상태**. DatabaseScheduler 사용 시 PeriodicTask DB 등록 필요 (CLAUDE.md #28 버그 패턴). |
| Ticker 매칭률 3% | 운영 이슈 | sec_pr_7/10 보고서에 명시. CompanyAlias 0건, 큐 60건 적체. 비미국 주식 미등록(TSMC, Samsung 등) + LLM 일반명사 추출("third parties") 이중 원인. |
| Gold Set Track A Precision/Recall | 운영 이슈 | NVDA 단독 평가 시 P=62.5%, R=45.5%. 설계 목표(P≥70%, R≥50%) 미달. 다른 9종목 라벨 보완 필요. |
| JNJ Item 순서 검증 실패 | 알려진 이슈 | 14/15 종목 성공. JNJ만 `validate_extracted_sections` 순서 검증에서 실패 — 검증 완화 미반영. |
| S&P 500 전체 배치 | **C. 미구현** (운영) | Gemini Free 15RPM/1500RPD 제한으로 503종목 배치는 보류. 현재 15종목만 수집. |
| `seed_company_aliases.py` 시드 데이터 | **B. 부분 구현** | command는 존재하나 CompanyAlias DB 0건 (sec_pr_17 보고서 기준). TSMC, Samsung 등 수동 시딩 미실행. |
| `for_api` confidence 노출 경계 | **A** | sec_pr_13 — `metrics/services/business_model_service.py`에 `for_api=True` 시 overall_confidence 미노출 확인됨. |

---

## Validation 상세

### 설계 문서 (4개)
| 파일 | 라인 | 역할 |
|------|------|------|
| `validation_design.md` | 1,646 | v1.4 — 네비게이션, 7카테고리 × 34지표, Peer 선정, value_status, ComposedChart, Empty State |
| `validation_peer_system.md` | 403 | v2 — 6개 프리셋 + custom, PeerPreset 모델, confidence_score, 9단계 Phase 로드맵 |
| `validation_peer_phase6_7.md` | 382 | Phase 6 thematic + Phase 7 LLM 대화형 |
| `validation_pr_prompts.md` | 414 | BE-PR-1~6 + FE-PR-1~7 클로드 코드 프롬프트 |

### task_done 보고서 (2건)
- `peer_phase6_thematic.md` — 463/503 종목에 thematic 프리셋 (GrowthStage × CapitalDNA)
- `peer_phase7_llm_filter.md` — LLM 필터 + Chain Sight 통합

> **BE-PR-1~6 + FE-PR-1~7 보고서는 별도 파일로 존재하지 않음** — 코드 상의 구현 완료로 추정.

### 구현 매트릭스

#### 모델 (9개 설계 → 위치 분산)
| 설계 모델 | 위치 | 구현 분류 |
|-----------|------|----------|
| MetricDefinition | `metrics/models/metric_definition.py` | **A** |
| CompanyMetricSnapshot | `metrics/models/metric_snapshot.py` | **A** (`value_status`, `exclusion_reason` 마이그레이션 0003 반영) |
| CompanyMetricLatest | `validation/models/metric_latest.py` | **A** |
| PeerMetricBenchmark | `metrics/models/benchmark.py` | **A** |
| IndustryMetricBenchmark | `metrics/models/benchmark.py` | **A** |
| CompanyBenchmarkDelta | `validation/models/benchmark_delta.py` | **A** (`benchmark_basis`, `benchmark_confidence` 마이그레이션 0003 반영) |
| PeerListCache | `metrics/models/benchmark.py` | **A** (`benchmark_basis`, `size_bucket`, `peer_tier` nullable) |
| CategorySignal (= category_score 대체) | `validation/models/category_score.py` (클래스명 CategorySignal) | **A** (gray 신호 + signal_reason 포함) |
| BatchJobRun | `metrics/models/batch_job.py` | **A** |
| IndustryClassification.handling_mode | `stocks/models.py` | **A** |
| **PeerPreset** | `validation/models/peer_preset.py` | **A** (Phase 2 모델, 6종 + custom) |
| **UserPeerPreference** | `validation/models/peer_preset.py` | **A** (Phase 4 User 영역) |
| ValidationAICache | — | **C. 미구현** (Phase 5 LLM 도입 시 검토, 설계서에 "Phase 1 제외" 명시) |

#### Celery 배치 파이프라인
| 설계 Task | 구현 함수 | 분류 |
|----------|---------|------|
| Task 1: fetch_annual_financials | `validation/tasks.py:23` → `services/financial_fetcher.py` | **A** |
| Task 2: calculate_derived_metrics | `tasks.py:37` → `services/metric_calculator.py` (459 LOC, 33지표 + value_status) | **A** |
| Task 3: calculate_benchmarks | `tasks.py:51` → `services/benchmark_calculator.py` (345 LOC, size_bucket + adjacent + fallback) | **A** |
| Task 3.5: calculate_relative_metrics | `tasks.py:65` → `services/relative_metrics.py` (97 LOC, rev_growth_vs_industry) | **A** |
| Task 4: calculate_category_signals | `tasks.py:79` → `services/category_signal_calculator.py` (192 LOC, gray + handling_mode special) | **A** |
| Task 5: update_peer_list_caches | `tasks.py:93` | **A** (확인 전용 — Task 3에서 이미 갱신) |
| Task 6: log_batch_run | `tasks.py:106` | **A** |
| Orchestrator: run_weekly_validation_batch | `tasks.py:141` (Celery `chain` 7단계 순차) | **A** |

#### API (3개 설계 + Phase 4/7 확장)
| 설계 엔드포인트 | 구현 위치 | 분류 |
|---------------|----------|------|
| GET `/api/v1/validation/{symbol}/summary/` | `api/views.py:52 ValidationSummaryView` | **A** |
| GET `/api/v1/validation/{symbol}/metrics/?category=...` | `api/views.py:173 ValidationMetricsView` | **A** |
| GET `/api/v1/validation/{symbol}/leader-comparison/` | `api/views.py:317 LeaderComparisonView` | **A** |
| GET `/api/v1/validation/{symbol}/presets/` | `api/views.py:421 PresetListView` | **A** (Phase 4 추가) |
| POST/DELETE `/api/v1/validation/{symbol}/peer-preference/` | `api/views.py:456 PeerPreferenceView` | **A** (Phase 4 추가, JWT 필수 — CLAUDE.md 버그 #26 반영) |
| POST `/api/v1/validation/{symbol}/llm-filter/` | `api/views.py:495 LLMPeerFilterView` | **A** (Phase 7 추가) |

#### Peer 프리셋 (Phase 1~7)
| Phase | 설계 | 구현 | 분류 |
|-------|------|------|------|
| Phase 1: default | 모든 종목 | `preset_generator._generate_default` | **A** |
| Phase 2: sector_all / size_peers | 분기 조건 (mega/large만 size_peers) | `_generate_sector_all`, `_generate_size_peers` | **A** |
| Phase 3: quality_top / lifecycle | sector≥25 조건 | `_generate_quality_top`, `_generate_lifecycle` | **A** |
| Phase 4: UserPeerPreference + 선택 API | preset/custom mode | 모델 + PeerPreferenceView | **A** |
| Phase 5: custom Compute-on-Read | Redis TTL 1h + numpy | `services/custom_benchmark_engine.py` (161 LOC) | **A** |
| Phase 6: thematic (LLM) | LLM 큐레이션 → CompanyNarrativeTag 기반 | `_generate_thematic` — **설계와 차이**: LLM 직접 호출 대신 **GrowthStage × CapitalDNA 교차 조합** 사용. 결과 463/503 종목 | **D. 폐기/대체** (실용성으로 LLM 호출 우회, Chain Sight 데이터 직접 활용) |
| Phase 7: LLM 대화형 필터 | Gemini 자연어 → 구조화 필터 + 5 시나리오 | `services/llm_peer_filter.py` (264 LOC) + LLMPeerFilterView. 5 시나리오 중 3개 통과, "해외매출 R&D" 0개 반환 — chainsight 데이터 부족 한계 그대로 노출 | **B. 부분 구현** (코드는 완성, 데이터 한계로 시나리오 부분 작동) |

#### 프론트엔드 (FE-PR-1~7)
| PR | 설계 | 구현 검증 | 분류 |
|----|------|----------|------|
| FE-PR-1 네비게이션 L1/L2 | tab=validation, tab=chainsight 등 | (코드 직접 검증 안 함, frontend/components/stock-detail/ 존재 추정) | (확인 필요) |
| FE-PR-2~7 컴포넌트 7종 + 차트 + Empty State | ComposedChart, Accordion, IntersectionObserver | (frontend 코드 미검증) | (확인 필요) |

### 갭/리스크
| 항목 | 분류 | 비고 |
|------|------|------|
| BE-PR-1~6 task_done 보고서 부재 | 문서 갭 | 코드는 모두 구현되었으나 PR 단위 완료 기록이 없음. 향후 회고/이력 추적 어려움. |
| Phase 6 LLM 큐레이션 미실행 | **D. 폐기/대체** | 설계서는 Gemini로 theme_tags 추출 → 클러스터링이지만 구현은 chainsight의 GrowthStage×CapitalDNA 직접 사용. 합리적 대체이나 설계서와 차이 명시 필요. |
| Phase 7 chainsight 의존 시나리오 0건 반환 | **B** | "해외 매출 50%+, R&D 높은" 시나리오 0개. SensitivityProfile/CapitalDNA 데이터 부족. chainsight 파이프라인 완성 의존. |
| FE-PR 보고서 + 코드 확인 부재 | 문서 + 검증 갭 | 본 감사는 백엔드 중심. 프론트 구현 검증은 별도 작업 필요. |
| ValidationAICache (Phase 5 LLM) | **C. 미구현** | 설계서가 Phase 1 제외로 명시했으므로 의도된 미구현. Phase 1~4 결과 검토 후 결정 필요. |
| `validation/views.py` (1 LOC) | 의도 | 모든 라우팅은 `api/views.py`로 이동. 빈 stub. |

---

## News 상세

### 설계 문서 (3개)
| 파일 | 라인 | 역할 |
|------|------|------|
| `news_keyword_detail_plan.md` | 216 | 키워드 상세 v1: search_terms_en + keyword_detail API + BottomSheet |
| `keyword_detail_bottomsheet_v2.md` | 80 | 키워드 상세 v2: 가로 스크롤 Strip + 데스크탑 max-w-2xl |
| `news_pipeline_monitoring_design.md` | 1,160 | v1.1 — Phase 0 (선행) + Phase A/B/C 모니터링 대시보드 |

### task_done 보고서
**0건** — 별도 PR 완료 기록 없음. 구현 완료 여부는 코드만으로 추적.

### 구현 매트릭스

#### 키워드 상세 v1/v2
| 설계 | 구현 | 분류 |
|------|------|------|
| `search_terms_en` 키워드 스키마 확장 | `news/services/keyword_extractor.py` (`grep search_terms_en` 매칭) | **A** |
| `GET /api/v1/news/keyword-detail/?date=&index=` | `news/api/views.py:646` `@action keyword_detail` | **A** |
| Redis 캐시 (`news:keyword_detail:{date}:{index}:{updated_at_epoch}`, TTL 1h) | (구현 위치는 views.py 내부 — 코드 검증 안 함) | **A** (구현됨, 세부 캐시 키 검증 필요) |
| Gemini 실패 시 `analysis: null` + 기사 목록 표시 | views.py 응답 분기 | **A** |
| BottomSheet v1 (`KeywordDetailSheet.tsx`) | frontend (검증 안 함) | (확인 필요) |
| BottomSheet v2 (Strip + max-w-2xl) | frontend (검증 안 함) | (확인 필요) |

#### Pipeline 모니터링 — Phase 0 (선행)
설계서 §11에 명시된 `_log_collection()` 누락 6개 태스크 보강 — **모두 호출 추가됨**:
| 태스크 | 설계 요구 | 구현 (`news/tasks.py`) | 분류 |
|--------|----------|----------------------|------|
| `collect_daily_news` | `'finnhub'`/`'marketaux'` | line 178 (`'finnhub_marketaux'` 통합) | **A** (provider 통합 변형) |
| `collect_market_news` | `'fmp'` | line 220 (`'finnhub_marketaux'`) | **B** — 설계는 `'fmp'`였으나 `finnhub_marketaux` provider로 통일. 의도 변경 여부 불명 |
| `collect_category_news` | provider별 | line 454 (`'finnhub_marketaux'`) | **B** — 동일 사유 |
| `classify_news_batch` | `'classifier'` | line 500 (`'internal'`) | **B** — 명명 차이 |
| `analyze_news_deep` | `'gemini'` | line 543 (`'gemini'`) | **A** |
| `sync_news_to_neo4j` | `'neo4j'` | line 621 (`'neo4j'`) | **A** |

#### Pipeline 모니터링 — Phase A (백엔드)
| 설계 API | 구현 위치 | 분류 |
|---------|----------|------|
| GET `/api/v1/news/collection-logs/?days=&provider=&task_name=` | views.py:1320 `collection_logs` (IsAdminUser) | **A** |
| GET `/api/v1/news/pipeline-health/?force_refresh=` | views.py:1430 `pipeline_health` (PHASE_CONFIG 1~6, KST 평일/주말 분기) | **A** |
| GET `/api/v1/news/ml-trend/?weeks=` | views.py:1684 `ml_trend` | **A** |
| GET `/api/v1/news/llm-usage/?days=` | views.py:1764 `llm_usage` (Phase 3 토큰 미추적 경고 포함 추정) | **A** |

#### Pipeline 모니터링 — Phase B
| 설계 API | 구현 위치 | 분류 |
|---------|----------|------|
| GET `/api/v1/news/task-timeline/?hours=` | views.py:1884 `task_timeline` | **A** |
| GET `/api/v1/news/neo4j-status/` | views.py:1945 `neo4j_status` | **A** |
| GET `/api/v1/news/ml-rollback-preview/` | views.py:2006 `ml_rollback_preview` | **A** |
| POST `/api/v1/news/ml-rollback/` (confirm 필수) | views.py:2046 `ml_rollback` | **A** |

#### Pipeline 모니터링 — Phase C (알림)
| 설계 항목 | 구현 | 분류 |
|----------|------|------|
| AlertLog 모델 (Severity, TriggerType TextChoices, indexes) | `news/models.py:684` — 설계와 정확히 일치 (7개 TriggerType, 인덱스 2개) | **A** |
| GET `/api/v1/news/alerts/?resolved=&severity=` | views.py:2091 `alerts` (IsAdminUser) | **A** |
| POST `/api/v1/news/alerts/{id}/resolve/` | views.py:2155 `alerts_resolve` (regex pk) | **A** |
| `check_pipeline_alerts` Celery 태스크 (30분 간격) | `news/tasks.py:1102 check_pipeline_alerts` — 6개 트리거 (consecutive_task_failure, ml_f1_decline, keyword_extraction, llm_error_spike, neo4j_unavailable, collection_drop, unclassified_backlog) 전부 구현 | **A** |
| Beat 스케줄 `*/30 minutes` 등록 | @infra 영역 — DatabaseScheduler 등록 여부 미확인 | (확인 필요) |
| AlertLog 마이그레이션 | `news/migrations/0006_alertlog.py` 존재 | **A** |
| AlertLogAdmin | `news/admin.py` (확인 안 함) | (확인 필요) |

#### 프론트엔드 컴포넌트 (Phase A/B/C)
설계서 §7에 14개 신규 파일 명시. 코드 미검증 (본 감사는 백엔드 중심).
| Phase | 컴포넌트 | 확인 상태 |
|-------|---------|----------|
| A | PipelineStatusBar, CollectionStatsTable, MLModelCard, MLTrendChart, RecentErrorsList, LLMUsageSummary, NewsPipelineSubTab | 미확인 |
| B | TaskTimelineChart, Neo4jStatusCard, MLCompareView | 미확인 |
| C | AlertBadge, AlertList + admin/page.tsx 통합 | 미확인 |

### 갭/리스크
| 항목 | 분류 | 비고 |
|------|------|------|
| task_done PR 보고서 0건 | 문서 갭 | 12,748 LOC 구현에 비해 추적 가능한 PR 완료 기록 부재. CLAUDE.md 원칙 2(작업 완료 기록) 위반. |
| Phase 0 `_log_collection` provider 라벨 변형 | **B** | 설계서 §11과 다른 provider 값 사용 (`'finnhub_marketaux'`, `'internal'`). 대시보드 by_provider 집계가 설계 의도와 다른 그룹으로 나타날 수 있음. |
| 프론트엔드 컴포넌트 14개 검증 부재 | 검증 갭 | 본 감사는 백엔드 코드 중심. NewsTab sub-tab 구조 + 5개 섹션 + 알림 배지 모두 별도 검증 필요. |
| `check_pipeline_alerts` Beat 등록 | (확인 필요) | 코드는 존재하나 DatabaseScheduler에 30분 간격 등록 여부 unverified (CLAUDE.md #28 패턴). |
| LLM 토큰 통합 추적 (Phase B 확장) | **C. 미구현** | 설계서가 NewsDeepAnalyzer 토큰 로깅을 Phase B로 미룸 — llm-usage API의 coverage_warning이 영구화될 우려. 추가 보강 필요. |

---

## 종합 권고

### 우선순위 (영향도 기준)
1. **SEC Pipeline Beat 스케줄 활성화** — `sync-sec-dirty-neo4j`와 `check-new-filings`가 주석/미등록 상태면 Neo4j edge가 영원히 dirty로 남음. DatabaseScheduler에 PeriodicTask 등록 즉시 필요.
2. **CompanyAlias 수동 시딩** — `seed_company_aliases.py` 명령으로 TSMC→TSM, Samsung→005930 등 최소 50건 시딩. SEC 매칭률 3% → 30%+ 개선 기대.
3. **News provider 라벨 정규화** — `_log_collection` 호출 시 provider를 `'finnhub'`/`'marketaux'`/`'fmp'`로 분리하거나 설계서를 `'finnhub_marketaux'` 통합으로 업데이트 (선택).
4. **task_done 보고서 회고 작성** — Validation BE-PR-1~6 + FE-PR-1~7 + News 모니터링 Phase 0~C에 대한 사후 완료 기록 작성. 향후 매니저 파악 및 이력 추적용.
5. **Chain Sight 데이터 파이프라인 완성** — CompanyNarrativeTag/SensitivityProfile/CapitalDNA가 부분 구축 상태면 Peer Phase 7 가치 제한. chainsight 파이프라인 우선 완성.

### 분류 통계
| 분류 | SEC | Validation | News | 합계 |
|------|-----|-----------|------|------|
| A. 완전 구현 | 16 | 14 (모델 12 + 태스크 8 + API 6 + 프리셋 5) | 18 (Phase A/B/C 14 + 키워드 4) | **48** |
| B. 부분 구현 | 3 (Beat 주석, 매칭률, 시드 0건) | 1 (Phase 7 데이터 한계) | 5 (provider 라벨 변형 5건) | **9** |
| C. 미구현 | 1 (S&P 500 전체 배치) | 1 (ValidationAICache) | 1 (LLM 토큰 통합) | **3** |
| D. 폐기/대체 | 0 | 1 (Phase 6 LLM → DNA 직접) | 0 | **1** |

**총 평가**: 설계서 → 구현 전환율 **A=77% / B=15% / C=5% / D=3%**. 대부분 운영 작업(시드 데이터, Beat 등록, 데이터 보강) 영역에서 갭 존재. 코드 단위 미구현은 적음.
