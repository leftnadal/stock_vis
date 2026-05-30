# SEC Pipeline + Validation + News 설계 갭 감사

> 작성일: 2026-05-31 · 모드: **읽기 전용** (코드 수정 없음)
> 대상: `docs/sec_pipeline/` vs `sec_pipeline/`, `docs/first_validation_system/` vs `validation/`, `docs/news/` vs `news/`
> 방법: 설계 문서 + `task_done/` 완료 보고서 cross-reference → 병렬 코드 대조 → 핵심 주장 직접 재검증

---

## 검증 주의사항 (중요)

병렬 분석 중 하위 에이전트들이 **각 앱의 `tasks.py`만 보고 `config/celery.py`를 읽지 않아** Celery Beat 등록·마이그레이션 관련 오판 4건이 발생했습니다. 본 보고서는 아래 항목을 **직접 재검증하여 정정**한 최종본입니다.

| 에이전트 초기 주장 | 재검증 결과 | 근거 |
|---|---|---|
| Validation: `PeerPreset`/`UserPeerPreference` 마이그레이션 0005 **누락** | ❌ 틀림 — **0004에 포함됨** | `validation/migrations/0004_alter_categorysignal_unique_together_and_more.py` 내 `CreateModel name='PeerPreset'`, `name='UserPeerPreference'` |
| Validation: Celery Beat에 `run_weekly_validation_batch` **미등록** | ❌ 틀림 — **등록됨** | `config/celery.py:774` |
| SEC: `sync_dirty_to_neo4j`/`check_new_filings` Beat **주석/비활성** | ❌ 틀림 — **등록됨** (tasks.py:567 주석은 참고용, 실제 등록은 config) | `config/celery.py:785, 799` |
| News: `check_pipeline_alerts` Celery 태스크 **미구현(@infra 대기)** | ❌ 틀림 — **구현+등록됨** | `news/tasks.py:1104` + `config/celery.py:429` |

→ 위 4건 정정으로 실제 구현률은 에이전트 초기 추정치보다 **높습니다.**

---

## 앱별 요약 (구현률)

| 앱 | 완전(A) | 부분(B) | 미구현(C) | 폐기/대체(D) | 구현률(추정) | 비고 |
|----|:---:|:---:|:---:|:---:|:---:|----|
| **SEC Pipeline** | 49 | 1 | 0 | 0 | **~98%** | PR1~17 전 산출물 존재, Beat까지 등록 |
| **Validation** | 53 | 3 | 0 | 0 | **~95%** | Phase 1~7 완성, 마이그레이션·Beat 정상 |
| **News (v3 plan 3종)** | 27 | 4 | 0 | 1 | **~92%** | 백엔드 거의 완결, FE 세부·BottomSheet v2가 변수 |
| **합계** | 129 | 8 | 0 | 1 | **~95%** | **미구현(C) 0건** — 세 영역 모두 설계 의도 거의 전량 반영 |

**총평**: 세 앱 모두 **미구현(C) 0건**. 갭은 (1) 백엔드 코드는 있으나 FE UI 세부 검증 불가(읽기 전용 한계), (2) 설계 대비 일부 로직 간소화(B), (3) 설계 변경에 따른 라벨/명칭 불일치(문서 정합성)에 집중됩니다. **기능적 결함(코드 부재)은 발견되지 않았습니다.**

---

## SEC Pipeline 상세

### 구현률: A 49 / B 1 / C 0 / D 0 (~98%)

설계 문서: `decisions/001_fmp_vs_sec_edgar_metadata.md` + `task_done/sec_pr_1~17.md` + `sec_pipeline_complete_summary.md`

### PR별 Cross-Reference (PR1~17)

| PR | 약속 산출물 | 실제 위치 | 분류 |
|----|----|----|:--:|
| PR1 | 8개 모델 + migration | `sec_pipeline/models.py` (RawDocumentStore, SupplyChainEvidence, BusinessModelSnapshot, BusinessModelEvidence, FilingProcessLog, CompanyAlias, UnmatchedCompanyQueue, PipelineIntelligenceReport) | A |
| PR2 | SECFilingCollector + 사후검증 | `collector.py:SECFilingCollector`, `validators.py:validate_extracted_sections` | A |
| PR3 | normalizer + Track A 추출/검증 | `normalizer.py`, `prompts.py:SUPPLY_CHAIN_EXTRACTION_PROMPT`, `extractor.py:GeminiExtractor.extract_supply_chain`, `validator_track_a.py` | A |
| PR4 | 예외 4종 + collect/extract task + sp500 | `exceptions.py`, `tasks.py:collect_and_extract/extract_from_document`, `sp500.py` | A |
| PR5 | Gold Set + 평가 커맨드 | `fixtures/gold_set.json`, `fixtures/gold_set_schema.py`, `management/commands/evaluate_gold_set.py` | A |
| PR6 | 15종목 배치 | `tasks.py:run_batch_and_report` | A |
| PR7 | TickerMatcher 3단계 + rapidfuzz | `ticker_matcher.py:TickerMatcher` (alias→exact→fuzzy, BLOCKED_NAMES) | A |
| PR8 | Admin 8종 + unmatched signal | `admin.py`, `signals.py:on_unmatched_resolved` | A |
| PR9 | Neo4j dirty 동기화 | `tasks.py:sync_dirty_to_neo4j` (Phase A/B/C, DELETE+CREATE) | A |
| PR10 | merge/DQS + unmatched 커맨드 | `merger.py:merge_relationship/calculate_edge_dqs`, `management/commands/process_unmatched_queue.py` | A |
| PR11 | Track B 키워드 필터 | `keywords_track_b.py:BM_KEYWORDS/filter_paragraphs_track_b` | A |
| PR12 | Track B 추출/검증 | `prompts.py:BUSINESS_MODEL_EXTRACTION_PROMPT`, `extractor.py:extract_business_model`, `validator_track_b.py` | A |
| PR13 | BM 서비스 레이어(for_api 게이트) | `packages/shared/metrics/services/business_model_service.py` (get_business_model/get_business_model_evidence/is_recurring_business) | A |
| PR14 | 품질체크 7종 + 대시보드 | `quality_checks.py`, `views.py:sec_pipeline_dashboard`, `templates/admin/sec_pipeline/dashboard.html` | A |
| PR15 | on-demand + FilingDataView | `on_demand.py:get_or_collect_filing`, `views.py:FilingDataView`, `tasks.py:check_new_filings`, `urls.py` | A |
| PR16 | Intelligence 리포터 | `intelligence.py:PipelineDataCollector/PipelineIntelligenceReporter`, `admin.py:PipelineIntelligenceReportAdmin` | A |
| PR17 | E2E task + Beat | `tasks.py:generate_intelligence_report/run_batch_and_report` + **`config/celery.py:785,799` Beat 등록** | A |

### Track별 상태

- **Track A (공급망)**: 16/16 컴포넌트 **완전 구현**. 수집→섹션추출→Pass1 필터→LLM→검증→DB→ticker 매칭→unmatched 큐→Neo4j 동기화 전 단계 존재.
- **Track B (사업모델)**: 10/10 컴포넌트 **완전 구현**. 5개 필드(direct_customer_contact, contract_model, recurring_revenue_signal, channel_dependency, customer_concentration) 추출·검증·서비스 게이트 완비.

### 갭 (B/문서 정합성)

| # | 항목 | 위치 | 성격 |
|---|----|----|----|
| 1 | **Beat 스케줄 주석 블록** — tasks.py 말미에 참고용 주석이 남아 있으나 실제 등록은 `config/celery.py`에서 수행됨. 혼동 소지(문서 중복). | `sec_pipeline/tasks.py:567` | B (정리 권장, 기능 영향 없음) |
| 2 | **`fmp_metadata` 라벨 잔존** — 의사결정 001에서 FMP→SEC EDGAR로 메타데이터 소스 대체했으나 `FilingProcessLog.STAGE_CHOICES`·로그 단계명이 여전히 `fmp_metadata`. | `models.py` STAGE_CHOICES, `tasks.py` `_log_stage()` | 문서 정합성 (DB값 호환 위해 의도적 유지 가능, 기능 무관) |
| 3 | task_done 미기재 커맨드 — `rematch_unmatched.py`, `reprocess_unmatched_queue.py`, `seed_company_aliases.py`가 구현되었으나 PR 보고서에 미수록. | `management/commands/` | 문서 누락(구현은 존재) |

> **SEC Pipeline은 설계 대비 사실상 전량 구현**. 잔여는 주석 정리·라벨 정합성 수준.

---

## Validation 상세

### 구현률: A 53 / B 3 / C 0 / D 0 (~95%)

설계 문서: `validation_design.md`, `validation_peer_system.md`, `validation_peer_phase6_7.md`, `validation_pr_prompts.md` + `task_done/peer_phase6_thematic.md`, `task_done/peer_phase7_llm_filter.md`

### Phase별 Cross-Reference

| Phase | 설계 산출물 | 구현 | 분류 |
|----|----|----|:--:|
| 1 | 기본 모델 + 3 API + 배치(Task1~6) | `models/`, `api/views.py`(Summary/Metrics/LeaderComparison), `tasks.py` | A |
| 2 | PeerPreset + default/sector_all/size_peers | `models/peer_preset.py`, `services/preset_generator.py` | A |
| 3 | quality_top/lifecycle + confidence_score | `preset_generator.py:_generate_*` | A |
| 4 | UserPeerPreference + 선택 API(POST/DELETE) | `models/peer_preset.py:UserPeerPreference`, `api/views.py:PeerPreferenceView` | A |
| 5 | CustomBenchmarkEngine + Compute-on-Read + Redis | `services/custom_benchmark_engine.py` | A |
| 6 | thematic 프리셋(GrowthStage×CapitalDNA) | `preset_generator.py:_generate_thematic`, 463/503 종목 생성 기록 | A |
| 7 | LLM 대화형 필터(parse+execute) | `services/llm_peer_filter.py`, `api/views.py:LLMPeerFilterView` | A |

### API 엔드포인트 설계 vs 구현

| 설계 엔드포인트 | 구현 클래스 | 위치 | 분류 |
|----|----|----|:--:|
| `GET /validation/{symbol}/summary/` | `ValidationSummaryView` | views.py:59 | A |
| `GET /validation/{symbol}/metrics/?category=` | `ValidationMetricsView` | views.py:182 | A |
| `GET /validation/{symbol}/leader-comparison/` | `LeaderComparisonView` | views.py:326 | A |
| `GET /validation/{symbol}/presets/` (Phase4 추가) | `PresetListView` | views.py:433 | A |
| `POST/DELETE /validation/{symbol}/peer-preference/` | `PeerPreferenceView` | views.py:468 | A |
| `POST /validation/{symbol}/llm-filter/` | `LLMPeerFilterView` | views.py:507 | A |

→ 설계 명시 3개 + Phase 4~7 확장 4개 = **7개 전부 구현**.

### 모델·마이그레이션 검증 (정정)

- `PeerPreset`, `UserPeerPreference` → **`migrations/0004`에 정상 CreateModel** (에이전트 "0005 누락" 주장은 오판).
- 9개 모델(validation 3 + shared 6) 전부 설계 명세 충족.
- `run_weekly_validation_batch` → **`config/celery.py:774` Beat 등록** (에이전트 "미등록" 주장은 오판).

### 갭 (B)

| # | 항목 | 위치 | 성격 |
|---|----|----|----|
| 1 | **interpretation 규칙 엔진 간소화** — 설계(§3.1/3.3/3.5)의 신호등 조합·산업 특수케이스 텍스트가 단순 템플릿 수준. | `services/interpretation.py` | B (품질 개선 여지) |
| 2 | **LeaderComparison 상세 16개 미노출** — 설계는 요약 6 + 상세 16(펼치기)인데 요약 6개만 응답. | `api/views.py:LEADER_SUMMARY_METRICS` (53~56) | B (기능 일부 축소) |
| 3 | **Task5 `update_peer_list_caches` 역할 축소** — 설계는 confidence 재검증+갱신, 실제는 확인만(갱신은 Task3에서 선행). | `tasks.py:95` | B (중복 제거형 간소화, 결과 동일) |

> **Validation은 Phase 1~7 전 구간 구현 완료**. 마이그레이션·Beat 정상. 갭은 해석 텍스트 품질과 리더비교 상세 노출 범위.

---

## News 상세

### 구현률: A 27 / B 4 / C 0 / D 1 (~92%)

설계 문서: `plan/news_keyword_detail_plan.md`, `plan/keyword_detail_bottomsheet_v2.md`, `plan/news_pipeline_monitoring_design.md`
(주의: News는 `task_done/` 폴더 없음 — plan 3종의 실구현 여부가 핵심 질문)

### 설계 문서별 Cross-Reference

| 설계 문서 | 핵심 약속 | 구현 상태 | 분류 |
|----|----|----|:--:|
| **news_keyword_detail_plan.md** | 키워드 상세 API + Gemini 분석 + search_terms_en + article_ids + 캐시 | `views.py:662 keyword-detail`, `_generate_keyword_analysis()`(views.py:798), `keyword_extractor.py:43/137`, 캐시키 updated_at epoch(views.py:719) | A (100%) |
| **keyword_detail_bottomsheet_v2.md** | 가로 스크롤 Strip + max-w-2xl + active 탭 + scrollIntoView | FE 컴포넌트 `KeywordDetailSheet.tsx` **존재**하나 Strip/너비/센터링 세부 구현은 읽기전용 한계로 미검증 | B (50%) |
| **news_pipeline_monitoring_design.md** | Phase A/B/C 모니터링 대시보드 | 백엔드 거의 완결, FE 세부 일부 미검증 | A (~90%) |

### 모니터링 설계 API 대조 (news_pipeline_monitoring_design.md)

| Phase | 설계 엔드포인트 | 구현 위치 | 분류 |
|----|----|----|:--:|
| A | `GET /news/collection-logs/` | views.py:1338 | A |
| A | `GET /news/pipeline-health/` (6 Phase, KST 판정) | views.py:1448 | A |
| A | `GET /news/ml-trend/` | views.py:1702 | A |
| A | `GET /news/llm-usage/` (Phase3 미포함 경고) | views.py:1782 | A |
| B | `GET /news/task-timeline/` | views.py:1902 | A |
| B | `GET /news/neo4j-status/` | views.py:1963 | A |
| B | `GET /news/ml-rollback-preview/` | views.py:2024 | A |
| B | `POST /news/ml-rollback/` (confirm 검증) | views.py:2064 | A |
| C | `GET /news/alerts/` | views.py:2109 | A |
| C | `POST /news/alerts/{id}/resolve/` | views.py:2173 | A |
| C | `AlertLog` 모델(7 TriggerType) | models.py:685 | A |
| C | **`check_pipeline_alerts` Celery 태스크** | **news/tasks.py:1104 + config/celery.py:429 등록** (정정) | A |

→ 설계 명시 모니터링 API **전량 구현**, Phase C 알림 태스크까지 등록 완료.

### `_log_collection()` 커버리지

6개 핵심 태스크 호출 추가됨(`tasks.py:178/220/455/501/544/622`). 단 `classify_news_batch`의 provider 라벨이 설계 `'classifier'` → 구현 `'internal'`로 다름(B, 기능 무관).

### 갭 (B/D)

| # | 항목 | 위치 | 성격 |
|---|----|----|----|
| 1 | **BottomSheet v2 FE 세부 미검증** — 가로 스크롤 Strip, max-w-2xl, active 탭 스타일, scrollIntoView 센터링. 컴포넌트 파일은 존재. | `frontend/.../KeywordDetailSheet.tsx`, `BottomSheet.tsx` | B (읽기전용 한계로 결론 보류, FE 직접 확인 필요) |
| 2 | **Phase B ML Rollback UI 2단계 플로우** — 컴포넌트 `MLCompareView.tsx` 존재하나 모달 플로우/히트맵 구현 미검증. | `frontend/.../MLCompareView.tsx` | B |
| 3 | `classify_news_batch` provider 라벨 불일치(`classifier`→`internal`). | `news/tasks.py:501` | B (문서 정합성) |
| 4 | Pipeline Health "금요일 마지막 실행 기준 62h" 규칙 정확도 미정밀검증. | `views.py:1448~` | B (로직 존재, 경계값 확인 권장) |
| 5 | **Phase 3 LLM 토큰 추적 미반영** — `llm-usage`는 키워드 추출 토큰만 집계. **설계가 명시적으로 by-design 제외**(views.py:1890~ 경고 배너). | `views.py:1782` | **D (설계 의도된 대체/제외)** |

> **News 백엔드는 plan 3종 약속을 거의 전량 구현** (API 18, 모델 3 전부). 잔여 불확실성은 **프론트엔드 컴포넌트 내부 세부**로, 읽기 전용 제약상 "파일 존재"까지만 확인됨 — 실동작 검증은 FE 직접 점검 필요.

---

## 종합 결론 및 권고

### 핵심 발견

1. **미구현(C) 0건** — 세 앱 모두 설계 산출물의 **코드 부재가 없음**. CLAUDE.md의 "완료" 표기는 정확.
2. **Celery Beat·마이그레이션은 모두 정상** — 초기 병렬 분석의 오판 4건은 `config/celery.py` 미열람이 원인이었고, 재검증으로 전부 "등록/존재" 확인.
3. 잔여 갭은 세 부류로 수렴:
   - **(B) 로직 간소화**: Validation interpretation·LeaderComparison 상세, News Pipeline Health 경계값.
   - **(B) FE 세부 미검증**: News BottomSheet v2 / ML Rollback UI — 읽기 전용 한계.
   - **문서 정합성**: SEC `fmp_metadata` 라벨, News `classifier`/`internal` 라벨, task_done 미기재 커맨드.

### 권고 (코드 수정 아님, 후속 작업 제안)

| 우선순위 | 항목 | 담당 추정 |
|----|----|----|
| 중 | News BottomSheet v2 + ML Rollback UI **프론트엔드 실동작 검증** (본 감사 미해결 항목) | @frontend |
| 하 | Validation interpretation 규칙 엔진 강화 / LeaderComparison 상세 16개 노출 | @backend |
| 하 | SEC `fmp_metadata` 라벨 → `sec_metadata` 정합화 검토(DB 호환 고려) | @backend |
| 하 | SEC task_done에 누락 커맨드 3종 기록, tasks.py:567 참고 주석 정리 | @qa/@infra |

---

*본 보고서는 읽기 전용 감사이며 어떤 코드도 수정하지 않았습니다. 분류 근거는 파일:심볼 수준으로 적시했고, 자동 분석의 오판 4건은 직접 재검증하여 정정했습니다.*
