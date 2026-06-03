# SEC Pipeline + Validation + News 설계 갭 감사

> **작성일**: 2026-06-04
> **유형**: 읽기 전용 감사 (코드 수정 없음)
> **대상**:
> - `docs/sec_pipeline/` ↔ `services/sec_pipeline/`
> - `docs/first_validation_system/` ↔ `services/validation/`
> - `docs/news/` ↔ `services/news/`
> **방법**: 설계/완료보고서 전수 독해 → 코드 대조 → task_done cross-reference → 핵심 갭 직접 검증

---

## 0. 사전 사실 (구조 이동 — 매우 중요)

감사 지시서의 경로 `sec_pipeline/`, `validation/`, `news/`는 **모노레포 마이그레이션으로 모두 이동 완료**. 최상위에 남은 디렉토리는 stale 잔재이며, **실제 소스는 전부 `services/` 하위에 있습니다.**

| 지시서 경로 | 실제 위치 | 최상위 잔재 상태 |
|------------|----------|----------------|
| `sec_pipeline/` | **`services/sec_pipeline/`** | `.pyc`만 남음 (소스 `git mv`로 이동, 잔재 미정리) |
| `validation/` | **`services/validation/`** | `.pyc`만 남음 (소스 이동) |
| `news/` | **`services/news/`** | 최상위 디렉토리 자체 부재 |

근거 git 커밋:
- `57fcc55` monorepo PR8a-1: `mv rag_analysis + validation + sec_pipeline -> services/`
- `ddca3bd` monorepo PR8a-2: `mv news -> services/news (git mv R100)`

라우팅 배선 (`config/urls.py`):
- `api/v1/news/` → `services.news.api.urls` (urls.py:38)
- `api/v1/validation/` → `services.validation.api.urls` (urls.py:43)
- `api/v1/sec-pipeline/` → `services.sec_pipeline.urls` (urls.py:45)

> ⚠️ **부수 발견(범위 밖 부채)**: 최상위 `sec_pipeline/`, `validation/`의 `.pyc`-only 잔재 디렉토리가 정리되지 않음. git 추적 대상이 아니므로 기능 영향은 없으나, 신규 작업자가 잘못된 경로를 감사/수정할 위험. **본 보고서는 코드 수정 금지 지시에 따라 정리하지 않고 보고만 함.**

---

## 1. 앱별 요약 (구현률)

| 앱 | 실제 위치 | A(완전) | B(부분) | C(미구현) | D(폐기/대체) | A+B 비율 | 핵심 진단 |
|----|----------|:------:|:------:|:------:|:------:|:------:|----------|
| **SEC Pipeline** | `services/sec_pipeline/` | 16 | 3 | 0 | 2 | **~90%** | 코드 완비. **문서가 코드보다 1.5개월 뒤처짐** (가장 큰 갭은 "문서 stale") |
| **Validation** | `services/validation/` | 9 | 7 | 1 | 2 | **~84%** | 코드 존재율 높으나 **프리셋 6종이 배치 미연결 → 런타임 default 1종만 동작** (치명적 단절) |
| **News** | `services/news/` | 24 | 3 | 1 | 0 | **~96%** | 모니터링 Phase A/B/C 전부 구현. **코드가 문서를 추월** (문서 "구현 전 DRAFT" 표기 stale) |

**전체 종합**: 세 앱 모두 설계 코드의 **물리적 존재율은 매우 높음(A+B 84~96%)**. 그러나 갭의 성격이 앱마다 다름:
- **SEC / News** = "문서 < 코드" (문서가 후속 구현을 못 따라감, 양성 불일치)
- **Validation** = "코드 존재 ≠ 동작" (코드는 있으나 배치 파이프라인에 연결되지 않아 핵심 기능이 런타임에서 무력화, **악성 불일치**)

> 🔴 **단일 최우선 리스크**: Validation의 **Peer 프리셋 시스템이 "허울"** — 설계의 핵심(해석 프레임 6종)이 실제로는 default 1종만 작동하며, 사용자가 프리셋을 전환해도 화면 데이터가 바뀌지 않음. (상세 §3.4)

---

## 2. SEC Pipeline 상세

> 대상: `services/sec_pipeline/` ↔ `docs/sec_pipeline/task_done/` 17개 PR 완료보고서 + `sec_pipeline_complete_summary.md` + `decisions/001_*`

### 2.1 구현률
A=16, B=3, C=0, D=2 (총 21 기능 단위, A+B ≈ 90%). **미구현(C) 항목 0건** — 설계가 주장한 모든 핵심 기능의 코드가 실재.

### 2.2 기능별 분류 표

| 기능 | 설계 출처 | 분류 | 근거 |
|------|----------|:--:|------|
| 8개 Django 모델 + migration | PR-1 | A | `models.py` 8개 모델, `migrations/0001_initial.py`. `neo4j_dirty`, `get_latest_by='as_of_date'`, `unique_together` 코드대로 |
| SEC EDGAR 수집기 (FMP 대체) | PR-2, decision 001 | A | `collector.py:72` `get_filing_metadata` (SEC submissions API), `_get_cik`, `fetch_filing_html`, `extract_sections` + edgartools 폴백 |
| 섹션 사후 검증 | PR-2 | A | `validators.py:21` `validate_extracted_sections` + `_check_item_order` |
| Track A 키워드 필터 + Gemini 추출 | PR-3 | A | `normalizer.py`(40 키워드), `extractor.py:35`, `validator_track_a.py` |
| Track A 검증 + confidence grade + 저장 | PR-3 | A | `validator_track_a.py:97` `validate_supply_chain_result`, `save_supply_chain_evidences` |
| Celery tasks (collect/extract) | PR-4 | A | `tasks.py:23` `collect_and_extract`, `:167` `extract_from_document` |
| 4개 예외 클래스 | PR-4 | A | `exceptions.py` (단 `FMPApiError`/`LLMExtractionError` dead code — §2.3 #7) |
| Gold Set + 평가 command | PR-5 | A | `fixtures/gold_set.json`(10종목), `management/commands/evaluate_gold_set.py` |
| Phase 1 배치 실행 | PR-6 | A | `tasks.py:589` `run_batch_and_report` |
| TickerMatcher 3단계 | PR-7 | A | `ticker_matcher.py:112` `match` (alias→exact→fuzzy), rapidfuzz |
| Admin 큐 뷰 + actions | PR-8 | A | `admin.py:100` `UnmatchedCompanyQueueAdmin` (3 actions) |
| post_save signal | PR-8 | A | `signals.py:21` `on_unmatched_resolved`, `apps.py` ready() |
| sync_dirty_to_neo4j | PR-9 | A | `tasks.py:397` 2-Phase + select_for_update(skip_locked) |
| merger + DQS | PR-10 | A | `merger.py` `merge_relationship`, `calculate_edge_dqs` |
| process_unmatched_queue command | PR-10 | A | `management/commands/process_unmatched_queue.py` |
| Track B (키워드/프롬프트/추출/검증/저장) | PR-11,12 | A | `keywords_track_b.py`, `prompts.py:46`, `validator_track_b.py`, `tasks.py:272` |
| BM 서비스 레이어 (for_api 게이트) | PR-13 | A | `packages/shared/metrics/services/business_model_service.py` |
| quality_checks 7개 + dashboard stats | PR-14 | A | `quality_checks.py` `run_post_batch_quality_checks`, `get_dashboard_stats` |
| Admin 대시보드 뷰 | PR-14 | **B** | `views.py:16` + 템플릿 존재. **단 `/api/v1/sec-pipeline/admin/dashboard/`로 매핑 — REST prefix 아래 HTML staff 뷰 혼재** (§2.3 #4) |
| On-demand 수집 + FilingDataView | PR-15 | **B** | `on_demand.py` + `views.py:29`. **200/202 응답 분기 부정확** (§2.3 #2) |
| check_new_filings | PR-15 | A | `tasks.py:543` (FMP RSS 대신 SEC EDGAR 폴링 — decision 001대로 대체) |
| Intelligence Reporter (5차원) | PR-16 | A | `intelligence.py` `PipelineIntelligenceReporter` + Admin |
| E2E chord 통합 | PR-17 | **D** | `run_batch_and_report`가 chord 아닌 **순차 실행** (주석에 "1인 개발 단순성" 명시) |
| Celery Beat 스케줄 | PR-17 | **D** | PR-17 문서는 "주석 상태"라 주장하나 **실제 `config/celery.py:783-802`에 3개 활성 등록** (문서 stale) |

### 2.3 task_done 주장 vs 실제 불일치

1. **PR-17 "Beat 주석 상태" → 실제 활성화됨.** `config/celery.py:783-802`에 `sec-sync-dirty-neo4j`(5분), `sec-check-new-filings`(매월 1일), `sec-seed-relations-to-chainsight`(매일 12시) 등록. 문서가 후속 작업 미반영.
2. **PR-15 "200/202 분기" → 부정확.** `on_demand.get_or_collect_filing`은 "1시간 내 중복" 시 `None`이 아닌 `{"status":"collecting"}` dict 반환(`on_demand.py:57-62`). `FilingDataView`(`views.py:42-55`)는 `None`일 때만 202를 주므로, **수집 진행 중인데 HTTP 200이 나가는** 케이스 존재.
3. **PR-15 "FMP RSS" → SEC EDGAR로 대체.** `check_new_filings`(`tasks.py:543`)는 SEC submissions 폴링. decision 001과 일치하나 PR-15 문서엔 변경 미반영.
4. **PR-14 대시보드 라우팅 위치 의심.** `@staff_member_required` HTML 템플릿 뷰가 `api/v1/sec-pipeline/` 아래 마운트되어 최종 `/api/v1/sec-pipeline/admin/dashboard/`. "Admin 대시보드" 명칭/성격과 마운트 위치 불일치.
5. **PR-17 "chord" 주장 → 순차 실행.** `run_batch_and_report`는 group/chord 없이 `collect_and_extract(symbol)` 동기 직접 호출(`.delay()` 아님).
6. **complete_summary 파일 목록 과소 기재.** management command 실제 5개(문서 암시 2개): `rematch_unmatched.py`, `reprocess_unmatched_queue.py`, `seed_company_aliases.py` 추가(2026-05-26 "C 옵션"). `ticker_matcher.py:26-87` `BLOCKED_NAMES` 블록리스트, `seed_relations_to_chainsight`(`tasks.py:338`)는 **어떤 task_done에도 없는 미문서화 후속 구현**.
7. **PR-4 예외 중 `FMPApiError`/`LLMExtractionError` dead code.** decision 001로 FMP 제거되며 `FMPApiError` raise 지점 소멸, `LLMExtractionError`도 미raise (extractor는 generic Exception).

### 2.4 주목할 갭/리스크 Top 5
1. **문서 동기화 부채 (최대 리스크)**: task_done 17건은 2026-04-04 스냅샷, 코드는 2026-05-26 "C 옵션"(블록리스트, 신규 command 3개, chainsight 시드 task, Beat 활성화)까지 진화. **문서=Phase 1~3 초기, 코드=운영 튜닝 이후**. 인수인계 시 task_done 신뢰 금지.
2. **Neo4j sync dynamic-type Cypher 인젝션 표면**: `tasks.py:472,489`에서 `rel_type`/`kt`를 f-string으로 Cypher 삽입. 현재는 enum 제한으로 안전하나, 신규 관계 타입 추가 시 화이트리스트 동기화 누락 시 위험.
3. **On-demand 응답 의미 깨짐**(#2): 수집 중 200 반환 → 소비자가 "준비됨"으로 오인 가능. `views.py`에서 `status=="collecting"` 시 202 분기 필요.
4. **배치가 단일 task 내 동기 순차**: `run_batch_and_report`(`time_limit=7260s`)가 S&P500 전체 순차 + SEC rate-limit sleep + Gemini RPM → 단일 task timeout/SIGKILL 위험. 설계 향후과제 "S&P500 전체 배치"가 현 구조로 비현실적.
5. **운영 품질 수치 목표 미달(문서가 인정)**: PR-6 기준 Ticker 매칭률 3%(2/66), Track A Precision 8.5%(target 70%), Intelligence health 0.2. 보강 코드(블록리스트/alias 시드/rematch)의 실효(개선치)는 미기록.

---

## 3. Validation 상세

> 대상: `services/validation/` ↔ `validation_design.md`(79KB) + `validation_peer_system.md` + `validation_peer_phase6_7.md` + `validation_pr_prompts.md` + task_done 2종

### 3.1 구현률
A=9, B=7, C=1, D=2 (총 19 기능, A+B ≈ 84%). **코드 존재율은 높으나 Peer 프리셋 default 외 5종이 배치 미연결로 런타임 무력화 → 실효 구현률은 체감상 훨씬 낮음.**

### 3.2 기능별 분류 표

| 기능 | 설계 출처 | 분류 | 근거 |
|------|----------|:--:|------|
| 데이터 모델 9개 + handling_mode | design §7, BE-PR-1 | A | `models/*.py` 전부, `metric_snapshot.py:45` value_status, `stocks/models.py:984` handling_mode |
| 지표 계산 엔진 (33개 + value_status) | design §6,§7.2 | **B** | `services/metric_calculator.py:174` — `cash_from_ops_trend`(:406 미구현), `sbc_to_revenue`/`buyback_offsets_sbc`(:241-242 영구 missing) |
| Compute-on-Read (커스텀) | peer_system §1,§7-2C | A | `services/custom_benchmark_engine.py` (벌크쿼리+numpy+Redis TTL 1h) |
| Peer 선정 (industry+size fallback) | design §3.2 | A | `services/benchmark_calculator.py:155` `_select_peers` 3단 fallback |
| Benchmark 계산 (median/p25/p75/percentile) | design §6 Task3 | A | `benchmark_calculator.py:235` |
| Category Signal/Score | design §3.1 | A | `services/category_signal_calculator.py:172` |
| **Peer 프리셋 6종 배치 계산** | peer_system §2,§9 | **C** | `services/preset_generator.py` 존재하나 **production 어디서도 미호출**(테스트만). `tasks.py:167` chain에 누락 |
| 커스텀 Peer (User 영역) | peer_system §4,§7 | A | `models/peer_preset.py:48` UserPeerPreference + `api/views.py:572` |
| LLM 대화형 필터 (Phase 7) | peer_phase6_7 | **B** | `services/llm_peer_filter.py` + `api/views.py:622`. chainsight 데이터 의존 |
| Phase 6 thematic | peer_phase6_7 §Phase6 | **D** | 설계는 LLM theme_tags 태깅, 구현은 GrowthStage×CapitalDNA 조합으로 **완전히 다른 알고리즘 대체**(`preset_generator.py:425`) |
| REST API (summary/metrics/leader) | design §5 | A | `api/views.py` 3개 + presets/preference/llm-filter 6개 |
| 해석/interpretation (rule-based) | design §3.1/3.3/3.5 | **B** | `services/interpretation.py` — trend 라벨 enum 불일치(§3.4 #5) |
| 배치 오케스트레이터 (chain Task1~6) | design §6.2 | **B** | `tasks.py:159` — preset 단계 누락 + Task1이 FMP 수집 아닌 "가용성 확인"만 |
| Celery Beat 등록 | design §6.2 | A | `config/celery.py:773` 토요일 05:00 (설계 일요일 02:00 — 의도적 변경) |
| 시드 데이터 (34지표 + special) | design §7, BE-PR-2 | A | `management/commands/seed_validation_data.py` |
| 프론트엔드 컴포넌트 | design §9 | A | `frontend/components/validation/` 9개 + 테스트 3개 |
| LLM ai_cache (Phase 2) | design §8.2 | **D** | `ValidationAICache` 모델 없음 (설계상 "검토" 단계 — 정상 보류) |
| value_status unstable(interest_coverage) | design §7.2 v1.4 | A | `metric_calculator.py:330` 부호반전+10배 판정 |

### 3.3 Phase별 구현 현황

**design v1.4 Phase:**
- Phase 1 (모델/마이그레이션/네비): **A**
- Phase 2 (배치+데이터): **B** — Task1이 실제 FMP 수집 안 함(`financial_fetcher.py`는 DB 존재 확인만), `cash_from_ops_trend` 미구현
- Phase 3 (프론트엔드): **A**
- Phase 4 (폴리시/Empty State): **B** — API no_data/not_in_universe 분기 있음(`views.py:78,107`), FE Empty State 5종 미확인
- Phase 5 (LLM ai_cache): **D** — 보류

**peer_system Phase (프리셋 7단계):**
- Phase 1 default: **A** (단 배치 미호출로 런타임 미생성)
- Phase 2 sector_all/size_peers: **C** (코드 有, 미호출)
- Phase 3 quality_top/lifecycle + confidence: **C** (코드 有, 미호출)
- Phase 4 UserPeerPreference: **A**
- Phase 5 custom Compute-on-Read: **A**
- Phase 6 thematic: **D** (DNA 조합 대체)
- Phase 7 LLM 대화형: **B** (chainsight 데이터 0건 의존)

### 3.4 task_done 주장 vs 실제 불일치

1. **🔴 프리셋이 배치 파이프라인에 미연결 (가장 심각)**: `peer_phase6_thematic.md`는 "463/503 종목 thematic, 전체 프리셋 2,282개" 주장. 그러나 `PresetGenerator.generate_for_symbols`는 **production 미호출**(호출처는 `tests/`뿐), `tasks.py:167` 주간 batch chain에 preset 생성 Task **부재**. → 2,282개는 일회성 수동 실행 추정, 주간 배치가 프리셋 갱신 안 함(peer 변동 시 stale).
2. **🔴 preset_key별 benchmark/signal 데이터 전혀 미계산**: migration 0003/0004로 `preset_key` 컬럼 추가됐으나, `BenchmarkCalculator`(`benchmark_calculator.py:304`)·`CategorySignalCalculator`(`category_signal_calculator.py:119`)의 `update_or_create`가 **preset_key를 절대 설정 안 함** → 전부 `"default"`로만 저장. 결과: default 외 5개 프리셋은 비교 데이터 0건. summary/metrics 뷰도 preset_key 필터 미적용(`views.py:106,149`) → **프리셋 전환이 실제 데이터를 안 바꿈.**
3. **thematic 알고리즘이 설계와 완전 상이**: 설계는 "Gemini theme_tags → CompanyNarrativeTag 클러스터링". 실제 `preset_generator.py:425 _generate_thematic`은 LLM 없이 `GrowthStage × CapitalDNA` 교집합, generation_method='curated' 박제.
4. **Phase 7 "완료" 주장 vs 데이터 미충족**: `peer_phase7_llm_filter.md`는 "완료" 선언하나, `peer_phase6_7.md:316`이 CompanySensitivityProfile/CapitalDNA 0건 블로킹 명시. task_done 자체에도 "해외매출 50%+ → 0개" 실패 기록.
5. **trend 라벨 enum 불일치**: `interpretation.determine_trend`(`interpretation.py:105`)는 `improving/declining/stable` 반환, 그러나 `CompanyMetricLatest.trend_label` choices(`metric_latest.py:30-32`)는 `improving/flat/deteriorating`. `declining`/`stable` 미존재.

### 3.5 주목할 갭/리스크 Top 5
1. **프리셋 시스템 전체가 "허울"**: PeerPreset 행은 과거 1회 수동 생성됐으나, 프리셋별 데이터 0건 + 배치 미갱신 + 뷰 미필터. 사용자가 프리셋 전환해도 항상 default 데이터. **설계 핵심(해석 프레임 6종)이 런타임 미작동.** → 배치 chain에 preset Task 추가 + calculator를 preset_key 루프로 재작성 + 뷰에 preset_key 필터 적용 필요.
2. **배치 Task1이 실제 FMP 수집 안 함**: `financial_fetcher.py`는 DB 존재 확인(`check_and_fetch`)만, 설계 BE-PR-3의 FMP 수집 미구현. 외부 stocks 파이프라인이 재무제표를 채워야만 동작 — 암묵적 외부 의존.
3. **지표 4개 영구 미구현/누락**: `cash_from_ops_trend`, `sbc_to_revenue`, `buyback_offsets_sbc`가 항상 missing → 현금흐름/희석 카테고리 signal 표본 축소.
4. **EV/EBITDA·percentile 단순화**: `_calc_ev_ebitda`(`metric_calculator.py:472`)가 EV를 market_cap으로 근사(debt/cash 미조정). 밸류에이션 정확도 저하.
5. **Phase 7 chainsight 의존 데이터 공백**: `execute_peer_filter`가 SensitivityProfile/CapitalDNA/GrowthStage/InsiderSignal 쿼리하나 0건 시 빈 집합 반환 → foreign_revenue_pct·rate_sensitivity 필터 사실상 항상 0건. "완료" 주장과 달리 실사용 불가.

---

## 4. News 상세

> 대상: `services/news/` ↔ `news_pipeline_monitoring_design.md`(44KB) + `news_keyword_detail_plan.md` + `keyword_detail_bottomsheet_v2.md`(FE)

### 4.1 구현률
A=24, B=3, C=1, D=0 (BE 기능 28개 기준, A+B ≈ 96%). **모니터링 Phase A/B/C 백엔드 전부 구현 — 코드가 문서를 추월.**

### 4.2 기능별 분류 표 (요약)

| 기능 | 설계 출처 | 분류 | 근거 |
|------|----------|:--:|------|
| 멀티 프로바이더 수집 (Finnhub/Marketaux/FMP/AV) | monitoring §1 | A | `providers/*.py`, `services/aggregator.py` |
| Circuit Breaker | v3 자산 | A | `services/circuit_breaker.py:14` |
| 중복 제거 | v3 자산 | A | `services/deduplicator.py:17` |
| News Classifier (Engine A/B/C) | monitoring §10 | A | `services/news_classifier.py:97,133` |
| Deep Analyzer (Gemini Tier A/B/C) | monitoring §1 Phase3 | A | `services/news_deep_analyzer.py:29` |
| ML 학습 파이프라인 v3 (LR + 안전게이트 + Shadow) | monitoring §2 | A | `ml_weight_optimizer.py`, `ml_production_manager.py`, `models.py:386` |
| LightGBM 전환 | monitoring §1 Phase6 | A | `tasks.py:941 train_lightgbm_model` |
| Neo4j sync | monitoring §5.2 | A | `services/news_neo4j_sync.py:69` |
| `_log_collection()` 커버리지 보강 (Phase0 선행) | monitoring §11 | A | `tasks.py` 6개 태스크 전부 추가 (:179,230,487,543,591,674) |
| `GET collection-logs/` | monitoring §3.1 | A | `api/views.py:1411` |
| `GET pipeline-health/` (6 Phase) | monitoring §3.2 | A | `api/views.py:1537` + PHASE_CONFIG:1560 |
| `GET ml-trend/` | monitoring §3.3 | A | `api/views.py:1911` |
| `GET llm-usage/` | monitoring §3.4 | A | `api/views.py:2002` (단 deep analysis 토큰 미추적 — §4.3 #5) |
| `GET task-timeline/` (Phase B) | monitoring §5.1 | A | `api/views.py:2134` |
| `GET neo4j-status/` (Phase B) | monitoring §5.2 | **B** | `api/views.py:2202` — pending_sync 추정치(§4.3 #2) |
| `GET ml-rollback-preview/` + `POST ml-rollback/` (Phase B) | monitoring §5.3 | A | `api/views.py:2276, 2325` |
| **AlertLog 모델 (Phase C)** | monitoring §6.3 | A | `models.py:553`, migration `0006_alertlog.py`, `admin.py:206` |
| **`check_pipeline_alerts` (7 트리거)** | monitoring §6.1 | A | `tasks.py:1179` (7개 전부: 1243/1257/1284/1309/1335/1414/1437) |
| **30분 Beat 스케줄** | monitoring §6.1 | A | `config/celery.py:428` `crontab(minute='*/30')` |
| `GET alerts/` + `POST alerts/{id}/resolve/` (Phase C) | monitoring §6.2 | A | `api/views.py:2378, 2453` |
| Slack/이메일 알림 채널 | monitoring §6.2 (선택) | **C** | Slack/send_mail 호출 0건 (인앱 AlertLog만) |
| 키워드 상세 `GET keyword-detail/` | keyword_detail §4 | A | `api/views.py:677` |
| `search_terms_en` 키워드 확장 | keyword_detail §3-1 | A | `keyword_extractor.py:283-285,338` |
| index 안정성 (`article_ids` 직접 저장) | keyword_detail §3-5 | A(개선) | `keyword_extractor.py:154-162` (설계 fallback 2단보다 상향 구현) |
| BottomSheet Strip UI | bottomsheet_v2 | — | FE 영역(범위 밖); BE 계약은 `keyword-detail` 단일 EP로 충족 |

### 4.3 설계 약속 vs 실제 불일치

1. **문서 상태 vs 실제 (양성 불일치)**: `news_pipeline_monitoring_design.md`는 표지에 "상태: 설계 단계(구현 전)", Phase C를 "@infra/나중에"로 미룸. 그러나 **실제 코드는 Phase A/B/C + Beat 전부 완료**. 문서 stale.
2. **neo4j-status `pending_sync`가 추정치**: `NewsArticle`에 `neo4j_synced` 전용 필드 부재로 "마지막 sync 이후 `llm_analyzed`+`updated_at` 갱신 건수"로 추정(`views.py:2241-2249`). 재동기화/업데이트 시 과대 집계 가능.
3. **`provider` 값이 설계와 다름**: 설계 §11은 `'finnhub'`/`'marketaux'` 개별 기록 약속, 실제는 단일 `"finnhub_marketaux"` 합산(`tasks.py:181`). `classify_news_batch`도 `'classifier'` 대신 `"internal"`(`tasks.py:544`). → `collection-logs`의 by_provider 집계에서 프로바이더 분리 불가.
4. **`pipeline-health` Phase1 provider 목록 오염**: 위 #3 결과로 `providers_active`에 `"finnhub_marketaux"`, `"internal"` 등 가짜 provider 혼입.
5. **LLM Usage `deep_analysis` 토큰 미추적**: `NewsDeepAnalyzer`가 토큰 미저장 → `llm-usage`는 키워드 추출 비용만 집계. 설계 §3.4가 약속한 "Phase B 통합 확장" 미이행 (단 `coverage_warning` 문구로 한계 정직하게 노출).

### 4.4 주목할 갭/리스크 Top 5
1. **provider 라벨 비정규화 (Top 리스크)**: `finnhub_marketaux`/`internal` 합산으로 collection-logs/pipeline-health의 프로바이더별 통계가 설계 의도와 어긋남 → 관리자가 Finnhub vs Marketaux 장애 구분 불가. `tasks.py:181,232,489,544` provider 인자 개별 분리 필요.
2. **`neo4j-status.pending_sync` 추정치**: 전용 플래그 부재로 과대/부정확 집계 → 운영자 "동기화 적체" 오판 가능. 정확성 필요 시 `NewsArticle.neo4j_synced(_at)` 필드 추가가 정석.
3. **Phase 3 LLM 비용 영구 사각지대**: 전체 LLM 비용 대부분(Deep Analysis)이 토큰 추적에서 누락, Phase B 통합도 미구현 → 비용 대시보드가 일부만 표시.
4. **AlertLog 알림이 인앱(DB)에만 머묾**: `check_pipeline_alerts`가 HIGH(Neo4j 다운, 태스크 연속 실패, ML F1 급락) 감지해도 Slack/이메일 push 없어 관리자가 /admin 열기 전엔 모름. 설계상 "선택"이나 운영 관점 HIGH 트리거엔 사실상 필수.
5. **설계 문서 stale로 인한 혼선**: monitoring 설계서가 "구현 전 DRAFT"로 남아 신규 작업자가 "Phase C 없다"고 오판 → 중복 구현/잘못된 핸드오프 위험. 문서를 "구현 완료"로 갱신 + #1~#3을 Known Issues로 명시 권장.

---

## 5. 종합 결론 및 권고

### 5.1 공통 패턴: "문서-코드 동기화 부채"
세 앱 모두 **코드가 설계 문서보다 앞서 있음**. task_done/design 문서는 특정 시점 스냅샷에 머물러 있고, 이후 후속 작업(SEC "C 옵션", News Phase C, Validation migration 0003/0004)이 문서에 반영되지 않음. → **문서 신뢰 시 잘못된 인수인계 위험**.

### 5.2 우선순위별 권고 (코드 수정은 별도 승인 필요 — 본 감사는 보고만)
| 우선 | 앱 | 항목 | 영향 |
|:--:|----|------|------|
| 🔴 P0 | Validation | 프리셋 batch 미연결 + preset_key 미설정 (§3.4 #1,#2) | 핵심 기능 런타임 무력화 |
| 🟠 P1 | SEC | On-demand 200/202 분기 수정 (§2.3 #2) | API 소비자 오인 |
| 🟠 P1 | News | provider 라벨 정규화 (§4.4 #1) | 모니터링 정확도 |
| 🟡 P2 | News | AlertLog HIGH 트리거 push 채널 (§4.4 #4) | 운영 가시성 |
| 🟡 P2 | 전체 | 설계/task_done 문서를 현 코드 상태로 갱신 | 인수인계 신뢰성 |
| ⚪ P3 | 전체 | 최상위 stale `.pyc` 디렉토리(`sec_pipeline/`, `validation/`) 정리 | 혼선 방지 |

### 5.3 양성 발견
- **News**: 설계가 "나중에"라 미룬 Phase C(AlertLog + 7트리거 + 30분 Beat)까지 완성 — 가장 성숙.
- **SEC**: 설계 핵심 21개 기능 미구현(C) 0건 — 배선 완전.
- **Validation keyword/index 안정성**: 설계 fallback보다 상향 구현(`article_ids` 직접 저장).

---

*본 보고서는 읽기 전용 감사이며 코드를 수정하지 않았습니다. P0~P3 권고 실행은 별도 승인이 필요합니다.*
