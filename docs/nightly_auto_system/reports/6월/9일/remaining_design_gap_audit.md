# SEC Pipeline + Validation + News 설계 갭 감사

> 생성일: 2026-06-09 · 읽기 전용 감사 (코드 수정 없음)
> 대상: `docs/sec_pipeline/` vs `services/sec_pipeline/`, `docs/first_validation_system/` vs `services/validation/`, `docs/news/` vs `services/news/`
> 분석 방법: 설계 문서(task_done 완료 보고서 포함) ↔ 실제 소스코드 cross-reference, 라우팅/INSTALLED_APPS/Beat 배선 검증

---

## ⚠️ 사전 발견: 앱 위치 (모노레포 마이그레이션)

3개 앱 모두 **루트가 아닌 `services/` 하위**에 실제 구현이 존재한다.

- 커밋 `57fcc55` (monorepo PR8a-1): `mv rag_analysis + validation + sec_pipeline -> services/`
- 커밋 `ddca3bd` (monorepo PR8a-2): `mv news -> services/news` (git mv R100)
- 루트 `/sec_pipeline/`, `/validation/`은 **stale `__pycache__` 잔재**(소스 `.py` 없음, git 미추적). 루트 `/news/`는 디렉토리 자체가 없음.
- 모든 task_done 보고서는 옛 경로(`sec_pipeline/...`)로 기술되어 있으나 실제 코드·`apps.py` label·import는 `services.*`로 정합. 감사는 `services/` 기준으로 수행함.

---

## 앱별 요약 (구현률)

| 앱 | (A) 완전 | (B) 부분 | (C) 미구현 | (D) 폐기/대체 | 합계 | A 비율 | 종합 판정 |
|----|---------|---------|-----------|--------------|------|--------|----------|
| **SEC Pipeline** | 24 | 2 | 0 | 1 | 27 | 88.9% | 🟢 정합성 매우 높음 — 유령 완료 0건 |
| **Validation** | 13 | 6 | 2 | 1 | 22 | 59.0% | 🔴 **프리셋 시스템 표시상만 동작** (핵심 갭) |
| **News** | 26 | 2 | 0 | 0 | 28 | 92.9% | 🟢 완성 — 문서 메타데이터만 stale |

**배선(라우팅/등록) 검증 결과: 3개 앱 모두 정상**
- `config/urls.py`: sec-pipeline(`:45`), validation(`:43`), news(`:38`) 전부 include 연결
- `config/settings.py`: `services.sec_pipeline`(`:205`), `services.validation`(`:203`), `services.news`(`:196`) 전부 INSTALLED_APPS 등록
- `config/celery.py`: 3개 앱 모두 Beat 스케줄 활성 등록

**핵심 요지**
- SEC Pipeline·News는 "보고서대로 실제 코드가 존재하는가"에서 합격 — 오히려 **구현이 문서보다 더 진행**되어 있고 문서가 역반영을 못 따라간 방향의 갭.
- Validation만 **설계 명세의 핵심 메커니즘(프리셋별 벤치마크 분기)이 미완**이라 실질 기능 갭이 존재. 사용자가 프리셋 탭을 바꿔도 신호등·벤치마크 숫자가 변하지 않는다.

---

## SEC Pipeline 상세

> 검증 범위: `docs/sec_pipeline/task_done/` 17개 PR 보고서 + `decisions/001` vs `services/sec_pipeline/` 실제 소스. 모든 근거는 실제 파일 확인.

### 구현률 요약

| 분류 | 개수 | 비율 |
|------|------|------|
| (A) 완전 구현 | 24 | 88.9% |
| (B) 부분 구현 | 2 | 7.4% |
| (C) 미구현 | 0 | 0% |
| (D) 폐기/대체 | 1 | 3.7% |
| **합계** | **27** | 100% |

**총평**: task_done 17개 PR이 약속한 컴포넌트가 코드·라우팅·Beat에 거의 전부 존재. 보고만 하고 미구현인 유령 컴포넌트 **0건**. 갭의 성격은 "구현 없음"이 아니라 "구현이 보고서보다 더 진행됐는데 문서 미반영".

### 컴포넌트별 표

| 컴포넌트 | 설계 출처(PR#) | 분류 | 근거(파일:라인 / 사유) |
|---|---|---|---|
| 8개 Django 모델 | PR-1 | A | `models.py:15-431` — RawDocumentStore/SupplyChainEvidence/BusinessModelSnapshot/BusinessModelEvidence/FilingProcessLog/CompanyAlias/UnmatchedCompanyQueue/PipelineIntelligenceReport |
| migration 0001_initial | PR-1 | A | `migrations/0001_initial.py` — 8개 모델 전부, 단일 migration |
| INSTALLED_APPS 등록 | PR-1 | A | `config/settings.py:205` `'services.sec_pipeline'` |
| 모델 제약(neo4j_dirty, get_latest_by, unique_together) | PR-1 | A | `models.py:112,215,331` |
| SECFilingCollector (메타→HTML→섹션) | PR-2 | A | `collector.py:39-374` — SEC EDGAR submissions API + Archives + regex 3단 |
| FMP→SEC EDGAR 메타데이터 대체 | decisions/001, PR-2 | D | `collector.py:9,34-36` — FMP 미사용, SEC EDGAR로 의도된 대체 |
| validate_extracted_sections | PR-2 | A | `validators.py:21-126` |
| edgartools fallback | PR-2 | B | `collector.py:189-215` — ImportError 시 None. PyPI 모듈명 불일치로 사실상 미작동(선택적 의존성) |
| normalizer (Pass 1 키워드 필터) | PR-3 | A | `normalizer.py:10-113` — 키워드 40개(보고서 "30개"보다 확장) |
| prompts (Track A/B) | PR-3, PR-12 | A | `prompts.py:8-46` — PROMPT_VERSION='v1' |
| GeminiExtractor (Track A+B) | PR-3, PR-12 | A | `extractor.py:18-152` — genai.Client 동기, thinking_budget=0 |
| validator_track_a | PR-3 | A | `validator_track_a.py:97-205` — GENERIC_COMPANY_TERMS 필터 + grade + bulk_create |
| Celery tasks (collect/extract) | PR-4 | A | `tasks.py:22-335` — max_retries 3/2 + _log_stage |
| exceptions 4개 | PR-4 | A | `exceptions.py:13-40` |
| sp500 유틸 | PR-4 | A | `sp500.py:8-14` |
| Gold Set (schema+json+command) | PR-5 | A | `fixtures/gold_set_schema.py`, `fixtures/gold_set.json`, `commands/evaluate_gold_set.py` |
| Phase 1 배치 (15종목) | PR-6 | A | `tasks.py:588 run_batch_and_report` |
| TickerMatcher (3단계 매칭) | PR-7 | A | `ticker_matcher.py:90-286` — alias→exact→fuzzy + 큐 |
| rapidfuzz 의존성 | PR-7 | A | `ticker_matcher.py:15` |
| Admin 8개 모델 + 큐 뷰 | PR-8 | A | `admin.py:21-227` |
| post_save signal | PR-8 | A | `signals.py:21-74` + `apps.py:9-10 ready()` |
| sync_dirty_to_neo4j | PR-9 | A | `tasks.py:397-531` — 2-Phase select_for_update skip_locked + DELETE+CREATE |
| merger (병합 + DQS) | PR-10 | A | `merger.py:36-139` |
| process_unmatched_queue command | PR-10 | A | `commands/process_unmatched_queue.py:13-72` — fuzzy≥0.90 + --dry-run |
| keywords_track_b (5필드 사전) | PR-11 | A | `keywords_track_b.py:9-135` |
| validator_track_b | PR-12 | A | `validator_track_b.py:23-122` |
| extract_from_document Track B | PR-12 | A | `tasks.py:272-333` |
| business_model_service (for_api 게이트) | PR-13 | A | `packages/shared/metrics/services/business_model_service.py:16-112` (리모델링 이동) |
| quality_checks (7개 체크 + 통계) | PR-14 | A | `quality_checks.py:17-164` |
| dashboard view + URL + template | PR-14 | A | `views.py:15-26`, `urls.py:8`, `templates/admin/sec_pipeline/dashboard.html` |
| config/urls.py include | PR-14 | A | `config/urls.py:45` |
| on_demand 수집 + FilingDataView | PR-15 | A | `on_demand.py:18-70`, `views.py:29-55` (IsAdminUser, 200/202) |
| check_new_filings | PR-15 | B | `tasks.py:543-576` — 동작하나 설계상 "SEC EDGAR RSS 대체" 미이행. submissions API 전수 폴링(비효율) |
| intelligence (5차원 + LLM 리포트) | PR-16 | A | `intelligence.py:63-238` |
| PipelineIntelligenceReportAdmin | PR-16 | A | `admin.py:158-227` |
| generate_intelligence_report + run_batch_and_report (E2E) | PR-17 | A | `tasks.py:579-635` |
| Celery Beat 스케줄 | PR-17 | A | `config/celery.py:784-802` — 실제 활성(보고서는 "주석 상태"라 했으나 더 진행됨) |

### 주요 갭 (C/D) 상세

**C(미구현) 항목 없음.** task_done가 약속한 모든 파일·클래스·함수가 실재.

**D-1: FMP → SEC EDGAR 메타데이터 대체 (의도된 폐기)**
decisions/001·PR-2가 명시한 정상 대체(FMP Starter의 sec-filings 404/403 → SEC EDGAR submissions API 무료). 잔재: `exceptions.py:19 FMPApiError`(미사용), `models.py:266 stage choice "fmp_metadata"`, `tasks.py:40 _log_stage(..., "fmp_metadata", ...)` — SEC 호출인데 라벨이 fmp로 남아 오해 소지(기능 무해).

### task_done 보고서 ↔ 실제 코드 불일치 (모두 "코드가 문서보다 앞섬" 방향)

1. **Beat 스케줄**: PR-17 보고서·`tasks.py:638-646` 주석은 "주석 상태"라 하나 실제 `config/celery.py:784-802`에 3개 작업 활성(sec-sync-dirty-neo4j */5, sec-check-new-filings 월1일, **sec-seed-relations-to-chainsight 매일 12시**).
2. **`seed_relations_to_chainsight` task** (`tasks.py:338-394`): 17개 PR 어디에도 없는 미문서화 통합 레이어(SupplyChainEvidence→chain_sight RelationConfidence, CUSTOMER_OF→SUPPLIES_TO 방향 정규화).
3. **TickerMatcher BLOCKED_NAMES** (`ticker_matcher.py:26-87`, 2026-05-26): 0순위 차단 블록리스트, PR-7 미기술. fuzzy threshold도 보고서 "≥85%" vs 실제 `:234 threshold=80`.
4. **business_model_service 경로**: summary는 `metrics/services/`라 하나 실제 `packages/shared/metrics/services/`(서비스 리모델링).
5. **미문서화 commands 3개**: `rematch_unmatched.py`, `reprocess_unmatched_queue.py`, `seed_company_aliases.py` (운영 중 추가).
6. **check_new_filings 방식 불일치** (B 분류 근거): decisions/001:32 "RSS 대체 필요" vs 실제 submissions API per-symbol 전수 폴링.

### 결론
감사 대상 중 **정합성이 가장 높은 모듈**. 실질 약점은 (1) edgartools fallback 사실상 미작동, (2) check_new_filings RSS 미사용 비효율, (3) FMP 네이밍 잔재 — 모두 경미. **권고: 문서 역반영(Beat 활성화, chainsight 연결 task, 블록리스트, 추가 commands)을 complete_summary.md에 갱신.**

---

## Validation 상세

> 검증 범위: `validation_design.md`(79KB) + `validation_peer_system.md` + `validation_peer_phase6_7.md` + `validation_pr_prompts.md` + task_done 2건 vs `services/validation/`.

### 구현률 요약

| 분류 | 개수 | 비율 |
|------|------|------|
| (A) 완전 구현 | 13 | 59% |
| (B) 부분 구현 | 6 | 27% |
| (C) 미구현 | 2 | 9% |
| (D) 폐기/대체 | 1 | 5% |
| **합계** | **22** | 100% |

**배선 검증(정상)**: `config/urls.py:43` include, `config/settings.py:203` 등록, `config/celery.py:773-774` validation-weekly-batch Beat, 6개 엔드포인트 전부 `api/urls.py:12-39` 등록.

### Phase별/기능별 표

| 기능 | 설계 출처 | 분류 | 근거(파일:라인 / 사유) |
|------|----------|------|------------------------|
| DB 모델 9종 | design §7, BE-PR-1 | A | `models/` 전체 — preset_key/unique_together 설계대로 |
| 34개 지표 + handling_mode 시드 | design §4, BE-PR-2 | A | `commands/seed_validation_data.py:75-154` |
| Task 1 FMP 수집 | design §6, BE-PR-3 | B | `tasks.py:24-37` → "원값 저장"이 "가용성 확인(check_and_fetch)"으로 축소 |
| Task 2 지표 계산 + value_status | design §6/§7.2, BE-PR-3 | A | `tasks.py:41-54` → MetricCalculator |
| Task 3 Peer 선정 (industry+size, 3단 fallback) | design §3.2, BE-PR-4 | A | `benchmark_calculator.py:155,32,44` |
| Task 3 Benchmark (p25/median/p75 + percentile_rank) | design §6, BE-PR-4 | A | `benchmark_calculator.py:235-324` numpy |
| Task 3.5 상대 지표 | design §6, BE-PR-4 | A | `tasks.py:75-86` → RelativeMetricCalculator |
| Task 4 Category Signal (percentile 평균 + gray) | design §3.1, BE-PR-5 | A | `category_signal_calculator.py:172-245,64-67` |
| Task 5/6 (cache 재검증 / batch 로깅) | design §6, BE-PR-5 | A | `tasks.py:109-155` |
| 오케스트레이터 chain (1→2→3→3.5→4→5→6) | design §6.1, BE-PR-5 | A | `tasks.py:158-178` celery chain |
| Rule-based 해석 3종 | design §3.1/3.3/3.5, BE-PR-6 | A | `interpretation.py:12,46,108,96` |
| API: summary/metrics/leader-comparison | design §5, BE-PR-6 | A | `views.py:63,223,404` |
| Compute-on-Read 엔진 (커스텀 peer + Redis) | peer_system §1/§5, Phase 5 | A | `custom_benchmark_engine.py:30-174` numpy + cache.set(TTL 3600), summary `:93-103` |
| 6종 프리셋 생성기 | peer_system §2-3 | A | `preset_generator.py` default/sector_all/size_peers/quality_top/lifecycle/thematic |
| LLM 대화형 필터 (Phase 7) | peer_phase6_7 | A | `llm_peer_filter.py:56,93`, `views.py:622 LLMPeerFilterView`, url `:34` |
| 프리셋 목록/선택 API | peer_system §7, Phase 4 | A | `views.py:531 PresetListView`, `:572 PeerPreferenceView` |
| **프리셋별 benchmark 배치 (preset_key 분기)** | peer_system §1/§6 | **C** | `benchmark_calculator.py:304` upsert에 **preset_key 인자 없음** → 모든 row가 default |
| **프리셋 전환 시 summary/metrics 반영** | peer_system §7, UI §8 | **C** | summary `views.py:106,149,316` 조회에 **preset_key 필터 부재** → 프리셋 바꿔도 신호등/벤치마크 불변 |
| Phase 6 thematic = LLM 사업모델 태깅 | peer_phase6_7 §Phase6 | **D** | 설계는 Gemini theme_tags. 실제는 Chain Sight `GrowthStage × CapitalDNA` 교차로 대체(`preset_generator.py:425`). task_done가 대체 박제 |
| 프리셋 생성 배치 통합 | peer_system §9 | B | `generate_for_symbols` 존재하나 주간 chain 미포함, command 없음 → 수동 의존 |
| Thesis Control 연동 (peer_filter 필드 + 탭) | peer_phase6_7 §Thesis | C | `thesis/models/thesis.py`에 peer_preset_key/peer_filter_query/result **부재** |

### 주요 갭 (C/D) 상세 — 🔴 우선 처리 대상

**[C-1, 가장 심각] 프리셋 시스템이 "표시상만" 동작 — 실제 benchmark는 항상 default**
설계(peer_system §1)의 핵심은 "프리셋별로 배치가 CompanyBenchmarkDelta/CategorySignal을 preset_key 분기 저장 → 조회 시 preset_key 필터로 즉시 전환(<50ms)". 그러나:
- 배치(`benchmark_calculator.py:304-321`)는 단일 default peer 집합으로만 delta 계산, `preset_key` 미사용 → 모든 row = `'default'`.
- 조회 뷰(`views.py:106,149,316`)도 `preset_key` 필터 없음.
- **결과**: 6종 프리셋을 보여주고 선택 저장은 되나(`is_selected`만 변경), summary/metrics가 반환하는 신호등·percentile·차트는 **어떤 프리셋을 골라도 동일**. sector_all/size_peers/quality_top/lifecycle/thematic의 peer_symbols는 생성되나 그 peer 기준 benchmark가 DB에 없어 화면 반영 불가. 모델 스키마(unique_together에 preset_key)는 준비됐으나 write/read 경로 미완. **유일하게 default와 다른 결과를 내는 경로는 custom mode(Compute-on-Read)뿐.**

**[C-2] Thesis Control Phase 7 연동 전무**
설계는 Thesis 모델에 `peer_preset_key/peer_filter_query/peer_filter_result` 추가 + 관제실 "Peer 비교" 탭 약속. `thesis/models/thesis.py`에 필드 없고 연동 코드 없음. LLM 필터는 독립 엔드포인트로만 존재.

**[C-3] 프리셋 생성기 배치 자동화 누락**
`PresetGenerator`는 구현됐으나 주간 chain(`tasks.py:167-175`) 미포함 + management command 없음 → 자동 파이프라인에 안 묶임, 수동 실행 의존.

**[D-1] Phase 6 thematic 방식 대체**
설계는 Gemini LLM 사업모델 태깅(`theme_tags`)이었으나 실제는 Chain Sight `GrowthStage × CapitalDNA` 조합 섹터 횡단 클러스터링(`preset_generator.py:425-524`). task_done/peer_phase6_thematic.md가 의도적 대체 박제(463/503 종목). 목적은 충족하나 설계 메커니즘과 불일치 → 대체로 분류.

### 추가 관찰
- Phase 2 LLM 캐시(`validation_ai_cache`): design §8.2 "Phase 2 검토" 명시 보류 → 갭 아님.
- `metrics`/`leader-comparison` 뷰도 preset 무시(`views.py:316,437,464`) — C-1과 동일 근원.
- summary `peer_info.confidence`: 설계는 high/medium/low(§3.2)이나 구현은 `benchmark_basis` 문자열 그대로 대입(`views.py:131-132`) — 값 의미 불일치(경미 버그).

### 결론
Validation은 **개별 컴포넌트는 거의 다 구현됐으나 "프리셋별 벤치마크 분기"라는 시스템의 핵심 가치 사슬이 끊겨 있다**. 사용자 체감상 프리셋 6종이 무의미(custom mode 제외). 우선순위: **C-1(배치 preset_key 분기 + 조회 필터) → C-3(배치 자동화) → C-2(Thesis 연동)**.

---

## News 상세

> 검증 범위: `docs/news/plan/` 3개 문서(news_keyword_detail_plan / keyword_detail_bottomsheet_v2 / news_pipeline_monitoring_design) vs `services/news/` + `frontend/`. 기능 28개 기준.

### 구현률 요약

| 분류 | 개수 | 비율 |
|------|------|------|
| (A) 완전 구현 | 26 | 92.9% |
| (B) 부분 구현 | 2 | 7.1% |
| (C) 미구현 | 0 | 0% |
| (D) 폐기/대체 | 0 | 0% |
| **합계** | **28** | 100% |

**핵심 발견**: `news_pipeline_monitoring_design.md`는 문서 헤더가 **"상태: 설계 단계 (구현 전)"**로 표기됐으나, 실제로는 Phase A/B/C 전체가 백엔드 14개 엔드포인트 + AlertLog 모델 + Celery 태스크 + Beat + 프론트엔드 12개 컴포넌트까지 **완전 구현**. **문서 메타데이터만 stale.**

### 설계문서별/기능별 표

#### 1) news_keyword_detail_plan.md

| 기능 | 분류 | 근거(파일:라인) |
|------|------|------------------|
| `GET /api/v1/news/keyword-detail/?date&index` API | A | `services/news/api/views.py:676-810` |
| date+index 기반 조회 | A | `views.py:692-723` |
| Gemini 투자 관점 요약(동기) | A | `views.py:812-852` (genai.Client sync) |
| 2단 매칭 (related_symbols + search_terms_en 보조) | A | `views.py:747-774` (레거시 fallback) |
| search_terms_en 스키마 확장 | A | `keyword_extractor.py:283-285,338-339` |
| Gemini 실패 시 analysis: null | A | `views.py:794-797` |
| 캐시 키 updated_at epoch + TTL 1h | A | `views.py:731-733,808` |
| 에러 처리(404/400/빈배열) | A | `views.py:712-723` |
| FE: KeywordDetailResponse 타입 + getKeywordDetail | A | `frontend/services/newsService.ts:234` |
| FE: KeywordDetailSheet 바텀시트 | A | `frontend/components/news/KeywordDetailSheet.tsx` |
| FE: KeywordBadge + DailyKeywordCard 연동 | A | `frontend/components/news/DailyKeywordCard.tsx:157-162` |

**초과 구현**: 설계는 실시간 2단 매칭만 명시했으나 구현은 `keyword_extractor.py:154-162`에서 키워드 생성 시 `source_indices→article_ids`를 미리 저장해 직접 조회(primary)하고, 레거시만 2단 fallback. 정확도·비용 개선.

#### 2) keyword_detail_bottomsheet_v2.md

| 기능 | 분류 | 근거 |
|------|------|------|
| BottomSheet max-w-2xl(672px) | A | `frontend/components/thesis/common/BottomSheet.tsx:38` |
| Props 변경(initialIndex + keywords) | A | `KeywordDetailSheet.tsx:15-16,56-57` |
| activeIndex 상태 + Strip 탭 전환 | A | `KeywordDetailSheet.tsx:59,130` |
| 가로 스크롤 Strip | A | `KeywordDetailSheet.tsx:125` |
| active pill ring-2 | A | `KeywordDetailSheet.tsx:34,38,42` |
| scrollIntoView 자동 center | A | `KeywordDetailSheet.tsx:77-84` |
| keepPreviousData | A | `frontend/hooks/useNews.ts:3,145` |
| DailyKeywordCard props 전달 | A | `DailyKeywordCard.tsx:161-162` |

#### 3) news_pipeline_monitoring_design.md (문서 상태 "구현 전" → 실제 완성)

| 기능 | 설계 | 분류 | 근거 |
|------|------|------|------|
| Phase 0: _log_collection() 6개 태스크 | §11 | A | `tasks.py:179,230,487,543,591,674` |
| GET /collection-logs/ | §3.1 | A | `views.py:1405-1529` |
| GET /pipeline-health/ (6 Phase + 주말 면제) | §3.2 | A | `views.py:1531-1903` |
| GET /ml-trend/ | §3.3 | A | `views.py:1905-1994` |
| GET /llm-usage/ | §3.4 | A | `views.py:1996-2124` |
| IsAdminUser permission 전 API | §9 | A | `views.py:1409,1535,1909,2000,2132,...` |
| GET /task-timeline/ (Phase B) | §5.1 | A | `views.py:2128-2194` |
| GET /neo4j-status/ (Phase B) | §5.2 | A | `views.py:2196-2268` |
| GET /ml-rollback-preview/ | §5.3 | A | `views.py:2270-2317` |
| POST /ml-rollback/ | §5.3 | A | `views.py:2319-2368` |
| AlertLog 모델 | §6.3 | A | `models.py:553-598` (db_table·indexes 설계 동일) |
| GET /alerts/ + POST /alerts/{id}/resolve/ | §6 | A | `views.py:2370-2493` |
| check_pipeline_alerts 태스크(7 트리거) | §6.1 | A | `tasks.py:1178-1307+` |
| Beat 스케줄 등록 | §6 | A | `config/celery.py:428-429` |
| news/admin.py AlertLogAdmin | §7 PhaseC | A | `services/news/admin.py:206-207` |
| FE: 모니터링 컴포넌트(PipelineStatusBar 등 6) | §4.3 | A | `frontend/components/admin/news/` |
| FE Phase B(TaskTimelineChart 등 3) | §5 | A | `frontend/components/admin/news/` |
| FE Phase C(AlertBadge/AlertList + page 통합) | §6 | A | `frontend/app/admin/page.tsx:14,64` |
| NewsTab sub-tab(overview/pipeline) | §4.1 | A | `frontend/components/admin/NewsTab.tsx:8-17,188-198` |
| useNewsPipeline hook + service | §4.3 | A | `frontend/hooks/useNewsPipeline.ts`, `services/newsPipelineService.ts` |
| 모니터링 API 테스트 커버리지 | §7 | **B** | `tests/news/`에 monitoring/keyword-detail/alert 테스트 0건 |
| LLM 토큰 추적 — Phase 3 deep analysis | §3.4/§5 | **B** | 설계도 "Phase B 예정"으로 보류, 구현은 건수만 집계(`views.py:2074-2099`), 토큰 미추적 |

### 주요 갭 (C/D) 상세
**미구현(C)·폐기(D) 없음.** 핵심 검증 대상 `news_pipeline_monitoring_design.md`가 문서상 "설계 단계"지만 백엔드 14개 엔드포인트 + AlertLog + Celery + Beat + 프론트엔드 12개 컴포넌트까지 완성. **문서 메타만 stale.**

부분 구현(B) 2건:
1. **모니터링/키워드상세 API 테스트 부재** — `tests/news/`에 600개 테스트(Intelligence v3: classifier/deep_analyzer/ml_*/neo4j/lightgbm 커버, CLAUDE.md "607개" 부합)가 있으나 `pipeline_health`/`collection_logs`/`keyword_detail`/`check_pipeline_alerts`/`AlertLog`/`ml_trend`/`llm_usage`/`task_timeline`/`neo4j_status`/`ml_rollback` **어느 것도 테스트 없음**. 구현 완전하나 회귀 안전망 부재.
2. **LLM 토큰 추적 Phase 3 미포함** — 설계 §3.4가 인정한 한계, 구현도 의도대로 키워드 토큰만 집계 + coverage_warning(`views.py:2116-2119`). "전체 LLM 비용" 미집계 → Phase B 확장 미완.

### Frontend 화면
- **키워드 상세 바텀시트: 완전 구현** — `KeywordDetailSheet.tsx`가 v2 스펙(Strip 가로 스크롤, active ring, scrollIntoView, max-w-2xl, keepPreviousData) 전부 반영.
- **파이프라인 모니터링 대시보드: 완전 구현** — `NewsTab.tsx`가 overview/pipeline sub-tab + `NewsPipelineSubTab`로 5섹션 + Phase B/C 조합, admin page 상단 AlertBadge 통합.

### 결론
News는 **3개 설계 문서 전부 완성**. 유일한 부채는 (1) 모니터링 신규 API 회귀 테스트 부재, (2) 전체 LLM 비용 집계 미완(설계가 인정한 한계). **권고: `news_pipeline_monitoring_design.md` 헤더 "상태"를 "구현 완료"로 갱신 + 모니터링 API 테스트 추가.**

---

## 종합 권고 (우선순위)

| 순위 | 앱 | 항목 | 성격 | 비고 |
|------|----|------|------|------|
| 🔴 1 | Validation | C-1: 프리셋별 benchmark 배치 분기(`preset_key`) + 조회 필터 | 기능 갭 | 프리셋 6종이 custom 외엔 무의미 |
| 🟠 2 | Validation | C-3: 프리셋 생성기 주간 chain/command 통합 | 자동화 누락 | C-1 선결 후 |
| 🟠 3 | Validation | C-2: Thesis Control Phase 7 연동(필드+탭) | 미구현 | 별도 스프린트 |
| 🟡 4 | News | 모니터링 신규 API 회귀 테스트 추가 | 안전망 | 구현은 완성 |
| 🟢 5 | News | `news_pipeline_monitoring_design.md` 상태 표기 갱신 | 문서 | 1줄 수정 |
| 🟢 6 | SEC Pipeline | complete_summary.md에 Beat 활성화/chainsight task/블록리스트/추가 commands 역반영 | 문서 | 코드가 앞섬 |
| ⚪ 7 | SEC Pipeline | check_new_filings RSS 전환(비효율 개선) | 최적화 | 선택 |

**한 줄 요약**: SEC Pipeline·News는 "다 만들었는데 문서가 못 따라온" 상태(역반영 필요), Validation만 "거의 다 만들었는데 핵심 사슬 한 곳이 끊겨" 프리셋 기능이 표시상만 동작 — **실질 작업이 필요한 유일한 진짜 갭은 Validation C-1**.
