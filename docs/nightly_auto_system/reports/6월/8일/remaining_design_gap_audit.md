# SEC Pipeline + Validation + News 설계 갭 감사

> **감사일**: 2026-06-08 (야간 자동화)
> **범위**: 읽기 전용. 코드 수정 없음.
> **방법**: 설계서(`docs/*`) + 완료 보고서(`task_done/`) vs 실제 구현 소스 cross-reference. 파일:라인 근거 기반.

---

## ⚠️ 사전 발견: monorepo 리팩토링으로 소스 위치 이동

지시서가 명시한 `sec_pipeline/`, `validation/`, `news/` (프로젝트 루트)는 **git 미추적 빈 껍데기**(`__pycache__`/`management`/`migrations` 잔재만 잔존)다. 실제 소스는 monorepo 리팩토링(commit `57fcc55` "PR8a-1: mv ... -> services/", `ddca3bd` "PR8a-2: mv news -> services/news")으로 **`services/` 하위로 이동**했다.

| 지시서 경로 | 실제 소스 경로 |
|---|---|
| `sec_pipeline/` | `services/sec_pipeline/` |
| `validation/` | `services/validation/` |
| `news/` | `services/news/` |
| (PR13) `metrics/services/` | `packages/shared/metrics/services/` |

→ 루트의 빈 디렉토리 3개는 리팩토링 잔재(cleanup 누락). 기능 갭 아님이나 정리 대상. 본 감사의 모든 분류는 `services/*` 실소스 기준이다.

---

## 앱별 요약 (구현률)

| 앱 | (A) 완전 | (B) 부분 | (C) 미구현 | (D) 폐기/대체 | 총 항목 | 구현률 | 보고서↔코드 신뢰도 |
|----|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **SEC Pipeline** | 18 | 1 | 0 | 2 | 21 | **~86%** | 높음 (불일치 0건, 코드가 보고서를 앞섬) |
| **Validation** | 8 | 2 | 1 | 0 | 11 | **~73%** | 중간 (설계서↔코드 방식 불일치 1건) |
| **News** | 18 | 2 | 0 | 2 | 22 | **~82%** | 높음 (대체 2건 모두 개선/명시적 보존) |

**공통 결론**: 세 앱 모두 INSTALLED_APPS·URL·Celery Beat·migration 등록이 정상 연결됨. "완료 보고했는데 코드 없음" 형태의 위험 불일치는 **0건**. 잔존 부채는 (1) Validation thematic의 설계서↔구현 방식 차이, (2) 데이터 채움 종속 기능(Phase7, Gold Set 라벨), (3) 모니터링/API 레이어 테스트 공백에 집중된다.

---

## SEC Pipeline 상세

### 구현률 요약

| 분류 | 개수 | 비중 |
|------|:---:|:---:|
| (A) 완전 구현 | 18 | ~86% |
| (B) 부분 구현 | 1 | ~5% |
| (C) 미구현 | 0 | 0% |
| (D) 폐기/대체 | 2 | ~9% |

총 21개 항목(17 PR + 부속). **task_done 17개 PR 보고서가 주장한 모든 기능이 실소스로 존재**하며, 보고서-코드 불일치(완료 주장인데 코드 없음/스텁)는 **0건**. 오히려 보고서보다 구현이 앞서간 항목 다수.

### 항목별 분류 표

| PR/기능 | 분류 | 근거 (파일:라인 / 부재) | 보고서 일치 |
|---|:---:|---|---|
| PR1 8개 모델 + migration | A | `services/sec_pipeline/models.py:15-431` (8개 모델), `migrations/0001_initial.py`. `neo4j_dirty`(:112), `get_latest_by='as_of_date'`(:215), unique_together(:331) | ✅ |
| PR2 EDGAR collector + 섹션추출 + 검증 | A | `collector.py:39-374` (메타→HTML→3단계추출→fallback), `validators.py:21-126` | ✅ |
| PR3 Track A 키워드필터 + Gemini | A | `normalizer.py`, `prompts.py:8`, `extractor.py:35-95`, `validator_track_a.py:97-205` | ✅ |
| PR4 Celery tasks + 에러핸들링 | A | `tasks.py:22-163`, `:166-335`, `exceptions.py:13-40` (5 예외 클래스), `sp500.py:8` | ✅ |
| PR5 Gold Set + 평가 스크립트 | **B** | `fixtures/gold_set.json`(10종목), `fixtures/gold_set_schema.py`, `management/commands/evaluate_gold_set.py` — 인프라 완성, **라벨 데이터 미완**(NVDA만 완전 라벨, Precision 8.5%) | ✅(보고서가 라벨 부족 자인) |
| PR6 Phase1 배치 + 검증 | **D** | 1회성 운영 배치 보고서 — 코드 산출물 아님. 실행 엔진은 PR17 `run_batch_and_report`로 흡수 | ✅(성격상 정상) |
| PR7 TickerMatcher 3단계 | A | `ticker_matcher.py:90-287` (alias→exact→fuzzy→queue). 초과구현: `BLOCKED_NAMES`(:26-87). ⚠️ fuzzy threshold 코드 80(:234) vs docstring 85 미세 불일치 | ✅ + 초과 |
| PR8 Admin 큐뷰 + post_save signal | A | `admin.py:100-152`, `signals.py:21-75`, `apps.py:9-10` (ready→signals) | ✅ |
| PR9 sync_dirty_to_neo4j | A | `tasks.py:397-531` (2-Phase + select_for_update(skip_locked) + DELETE/CREATE) | ✅ |
| PR10 merger + 미매칭 큐 command | A | `merger.py:36-139` (merge + calculate_edge_dqs), `management/commands/process_unmatched_queue.py` | ✅ |
| PR11 Track B 키워드사전 | A | `keywords_track_b.py` (5 필드 + filter_paragraphs_track_b) | ✅ |
| PR12 Track B Gemini 추출+검증+저장 | A | `prompts.py:9`, `extractor.py:97-152`, `validator_track_b.py:23-122`, `tasks.py:272-335` | ✅ |
| PR13 서비스 레이어 (for_api 게이트) | A | `packages/shared/metrics/services/business_model_service.py:16-112` (for_api :50-53). 경로만 monorepo 이동 | ✅ |
| PR14 Admin 대시보드 + quality_checks | A | `quality_checks.py:17-164` (7 체크), `views.py:15-26`, `urls.py:8`, `templates/admin/sec_pipeline/dashboard.html` | ✅ |
| PR15 On-demand 수집 + 신규filing 감지 | A | `on_demand.py:18-70`, `views.py:29-55`(IsAdminUser), `tasks.py:543-576`(check_new_filings) | ✅ |
| PR16 Intelligence Reporter | A | `intelligence.py:63-238` (5차원 + Gemini), `admin.py:158-227` | ✅ |
| PR17 E2E 통합 | A | `tasks.py:579-635` (순차 Phase1~3 + 리포트). 보고서대로 chord 대신 순차 | ✅ |
| INSTALLED_APPS 등록 | A | `config/settings.py:205` `'services.sec_pipeline'` | ✅ |
| config/urls.py 연결 | A | `config/urls.py:45` `api/v1/sec-pipeline/` | ✅ |
| Celery Beat (3개) | A | `config/celery.py:783-802` — **3개 활성** (sync-dirty 5분 / check-new-filings 매월 / seed-relations 매일 12시) | ⚠️ 보고서는 "주석"으로 박제 → 실제 활성 |
| seed_relations_to_chainsight 브리지 | A | `tasks.py:338-394` + Beat `:791-795`. SEC→chain_sight.RelationConfidence 변환 | 보고서 미기재(사후 추가) |

### 주요 갭 / 불일치

1. **위험 불일치 0건.** 17 PR 전부 실소스로 존재, 동작 흐름 연결, 스텁/TODO/NotImplementedError 0건 (`exceptions.py`의 `pass`는 예외 클래스 본문으로 정상).
2. **역방향 갭(코드가 보고서를 앞섬, 긍정적):** ① Beat 3개가 보고서엔 "주석"이나 실제 활성. ② `seed_relations_to_chainsight`는 17 PR 보고서에 없는 사후 통합. ③ management command 4종 추가(`rematch_unmatched`/`reprocess_unmatched_queue`/`seed_company_aliases` 등). ④ `BLOCKED_NAMES` 블록리스트.
3. **FMP 레거시 네이밍 잔존(명명 부채):** decision 001(FMP→SEC EDGAR 대체)은 코드 완전 반영됐으나 명칭만 잔존 — `STAGE_CHOICES`의 `'fmp_metadata'`(`models.py:266`), `FMPApiError`(`exceptions.py:19`). 동작은 SEC EDGAR, FMP 미호출.
4. **PR15 "FMP RSS" 폐기(D):** `check_new_filings`(`tasks.py:543-576`)는 RSS 대신 SEC EDGAR submissions API 폴링. decision 001 예고대로.
5. **부분 구현 1건(B) = PR5 Gold Set:** 평가 인프라 완성, 라벨 데이터 미완. 코드 결함 아닌 라벨링 작업 미완.
6. **미세 불일치:** TickerMatcher fuzzy threshold 코드 80(`ticker_matcher.py:234`) vs `match()` docstring/보고서 "≥85%".

### 등록/라우팅 상태

| 항목 | 상태 | 근거 |
|---|:---:|---|
| INSTALLED_APPS | ✅ | `config/settings.py:205` `'services.sec_pipeline'` (apps.py label=`sec_pipeline`) |
| config/urls.py | ✅ | `:45` `api/v1/sec-pipeline/` → dashboard + filing API |
| Celery 큐 라우팅 | ✅ | `config/celery.py:60` sync_dirty_to_neo4j → `neo4j` 큐 |
| Celery Beat | ✅ 활성(보고서는 주석) | `config/celery.py:784/791/798` |
| signals 등록 | ✅ | `apps.py:9-10` ready() |

---

## Validation 상세

### 구현률 요약

| 분류 | 개수 | 비중 |
|------|:---:|:---:|
| (A) 완전 구현 | 8 | ~73% |
| (B) 부분 구현 | 2 | ~18% |
| (C) 미구현 | 1 | ~9% |
| (D) 폐기/대체 | 0 (우회 1건) | — |

11개 핵심 축 기준. 등록·라우팅 정상.

### 항목별 분류 표

| 기능 | 분류 | 근거 (파일:라인 / 부재) | 보고서 일치 |
|---|:---:|---|---|
| Peer 프리셋 6종 | A | `services/validation/services/preset_generator.py:42-62` (6개 `_generate_*` 호출) | ✅(phase6) |
| Compute-on-Read 엔진 | A | `custom_benchmark_engine.py:30-171` (벌크쿼리 + numpy in-memory + Redis TTL 3600) | — |
| LLM 대화형 필터 | A | `llm_peer_filter.py:56-90` (Gemini sync `genai.Client`, 버그8 준수), `:93-276` | ✅ |
| 커스텀 Peer (UserPeerPreference) | A | `models/peer_preset.py` + `views.py:572-619`(POST/DELETE) + `:89-103` | — |
| Phase6 thematic (테마 peer) | A | `preset_generator.py:425-524` `_generate_thematic` (GrowthStage×CapitalDNA 교차) | ⚠️ **설계서↔코드 방식 불일치** ↓ |
| Phase7 LLM filter (뷰) | A | `views.py:622-692` LLMPeerFilterView + `api/urls.py:34-38` | ✅ |
| 벤치마크 델타 계산 (Task3) | A | `benchmark_calculator.py:235-324` (peer median/p25/p75 + percentile_rank) | — |
| 카테고리 시그널/점수 (Task4) | A | `category_signal_calculator.py:172-245` (균등평균 + green/yellow/red/gray) | — |
| 지표계산 metric + relative | A | `metric_calculator.py`(33지표 + value_status), `relative_metrics.py` | — |
| 해석 (interpretation) | **B** | `interpretation.py:46-93` rule-based 구현. `data_freshness`→`calculated_at` 대체, LLM 해석 미구현(설계상 Phase2 보류라 정상) | — |
| 뉴스 요약 (ValidationNewsSummary) | **C** | `models/news_summary.py` 모델만 존재. populate 태스크/뷰/시리얼라이저 **부재** | 설계서에 뉴스요약 PR 없음(계획 외 추가 모델) |

### 주요 갭 / 불일치

1. **★ Phase6 thematic: 원설계서 vs 구현 방식 불일치 (강조).** `validation_peer_phase6_7.md` 원설계는 thematic을 **Gemini LLM 사업모델 태깅 → `CompanyNarrativeTag.theme_tags` 클러스터링**(FILTER 프롬프트 포함)으로 명시. 실제 구현(`preset_generator.py:425-524`)은 **LLM을 전혀 쓰지 않고** `CompanyGrowthStage.stage × CompanyCapitalDNA.capital_type` 교집합 규칙 기반(`generation_method='curated'`로 저장). → **task_done 보고서(`peer_phase6_thematic.md`)는 DNA 교차 방식을 정확히 기술 → 보고서↔코드 일치**하나 **원설계서와는 다름**. (설계 진화로 해석 가능하나 설계서 미갱신.)
2. **Phase7 데이터 의존성 미충족(설계서 자체 경고).** `llm_peer_filter.py:196-214`의 `foreign_revenue_pct` 필터는 `CompanySensitivityProfile`, R&D 필터는 `CompanyCapitalDNA`에 의존. 설계서 309-364줄이 "이 모델들 0건 → 블로킹" 경고, phase7 task_done도 "해외매출+R&D 시나리오 0개" 자인. 코드 완성(A)이나 실효성은 chainsight 데이터 채움에 종속.
3. **metric_code 명칭 치환(주의):** 설계서 §4의 `shareholder_yield`/`buyback_yield`/`ocf_trend_3y` → 구현 `net_shareholder_yield`/`buyback_offsets_sbc`/`cash_from_ops_trend`(`category_signal_calculator.py:38-59`). 34개 카운트 유지되나 `buyback_offsets_sbc`는 단순 yield가 아닌 SBC 상쇄율 — FE 카탈로그 동기화 주의.
4. **Task1 설계 우회:** 설계서 6.1/BE-PR-3은 Task1이 FMP를 직접 호출해 재무 수집한다고 명시. 실제 `financial_fetcher.py:25-66`은 **수집하지 않고** 기존 DB(IncomeStatement 등) 존재 여부만 확인. 재무 데이터가 타 파이프라인에서 선적재돼야 동작.
5. **ValidationNewsSummary 미완(C):** 모델(0002 migration)·admin만 존재. 채우는 배치·노출 API 없음.
6. **summary API `confidence` 시맨틱:** `views.py:131` `"confidence": peer_cache.benchmark_basis` — confidence 자리에 basis 문자열(industry_size 등). 설계 5.2는 high/medium/low 기대 (경미한 계약 불일치).

**PR 목록(validation_pr_prompts.md):** BE-PR-1/2/4/5/6 ✅, **BE-PR-3 ⚠️ 부분**(Task1 FMP 수집→DB 체크 대체). 추가 구현(PR 외): PresetListView/PeerPreferenceView/LLMPeerFilterView/CustomBenchmarkEngine/PresetGenerator — Phase2~7 설계 기반 전부 구현. **API 뷰 단위 테스트 부재**(서비스 계층 위주, `tests/unit/validation/` 12파일).

### 등록/라우팅 상태

| 항목 | 상태 | 근거 |
|---|:---:|---|
| INSTALLED_APPS | ✅ | `config/settings.py:203` `'services.validation'` |
| config/urls.py | ✅ | `:43` `api/v1/validation/` |
| api/urls.py | ✅ | 6 엔드포인트(summary/metrics/leader-comparison/presets/peer-preference/llm-filter) `urls.py:12-39` |
| Celery Beat | ✅ | `config/celery.py:773-777` `validation-weekly-batch` 토요일 05:00 (설계는 일요일 02:00 — 조정됨). ⚠️ 버그28(DatabaseScheduler dict 무시) DB 반영 여부 별도 확인 권장 |

---

## News 상세

### 구현률 요약

| 분류 | 개수 | 비중 |
|------|:---:|:---:|
| (A) 완전 구현 | 18 | ~82% |
| (B) 부분 구현 | 2 | ~9% |
| (C) 미구현 | 0 | 0% |
| (D) 폐기/대체 | 2 | ~9% |

총 22개 항목. 설계서 3종 + Intelligence Pipeline v3 거의 완전 구현. 모니터링 설계(v1.1) Phase A/B/C 백엔드+프론트 전부 존재.

### 항목별 분류 표

| 기능 | 분류 | 근거 (파일:라인 / 부재) | 비고 |
|---|:---:|---|---|
| 키워드 상세 API (date+index) | A | `services/news/api/views.py:676-810` | 404/400 처리 |
| 키워드 `search_terms_en` Gemini 스키마 확장 | A | `keyword_extractor.py:268-285,338-339` | 프롬프트+파싱 반영 |
| 한국어 키워드→영문 기사 매칭 | **D**(개선 대체) | `views.py:740-774`, `keyword_extractor.py:154-162` | 런타임 2단 매칭 대신 생성 시점 `article_ids` 직접 저장. 2단 매칭은 레거시 fallback 보존 |
| Gemini 투자관점 요약(+실패시 null) | A | `views.py:788-852` `_generate_keyword_analysis` | 동기 `genai.Client`, thinking_budget=0 |
| 캐시 키 `updated_at` epoch 포함 | A | `views.py:731-733` | force 재생성 시 자동 miss |
| 바텀시트 v2 FE | A | `frontend/components/news/KeywordDetailSheet.tsx` | FE 컴포넌트 존재(상세 미검증) |
| CollectionLog API | A | `views.py:1405-1529` | KST TruncDate, by_provider/daily_summary, IsAdminUser |
| Pipeline Health API (6 Phase) | A | `views.py:1531-1903` | PHASE_CONFIG, weekday_only 62h 면제, force_refresh |
| ML Trend API | A | `views.py:1905-1994` | F1 추이 + feature_importance + consecutive_decline |
| LLM Usage API | A | `views.py:1996-2124` | keyword + deep_analysis tier_breakdown |
| `_log_collection()` Phase 0 보강 | A | `tasks.py:179,230,487,543,591,674` | 6 우선 태스크 호출 |
| Task Timeline API (Phase B) | A | `views.py:2128-2194` | hours 파라미터 |
| Neo4j Status API (Phase B) | A | `views.py:2196-2268` | available/last_sync/pending_sync |
| ML Rollback Preview/Execute (Phase B) | A | `views.py:2270-2368` | preview + confirm 필수 |
| AlertLog 모델 (Phase C) | A | `models.py:553-598`, `migrations/0006_alertlog.py` | TriggerType 7종 + Severity 4종 |
| Alerts API (목록 + resolve) | A | `views.py:2370-2493` | resolved/severity 필터 |
| AlertLogAdmin | A | `services/news/admin.py:206-207` | 등록됨 |
| check_pipeline_alerts (7 트리거) | A | `tasks.py:1179-1452` + Beat `celery.py:429` | 7 트리거 전부 |
| 모니터링 FE 컴포넌트 | A | `frontend/components/admin/news/` 12파일 | Phase A/B/C 전부 |
| LLM Usage Phase 3 토큰 추적 | **B** | `views.py:2074-2119` coverage_warning만 | 심층분석 토큰 미추적(설계 의도 한계, Phase B 확장 미완) |
| 모니터링/AlertLog 백엔드 테스트 | **B** | `tests/news/`에 pipeline/alert/collection_log/keyword_detail 테스트 **부재** | 코어(classifier/ml/neo4j) 테스트는 충실 |
| Stock Recommendations (구 추천) | **D**(레거시 보존) | `views.py:1337-1401` Deprecated 주석 | "추천 점수 제거" 방침 → `insights`(팩트 기반)로 대체 |

### services/news vs apps/market_pulse 중복·관계 분석

**중복 아님 — 이름만 겹치는 분리된 두 시스템.**

| 축 | `services/news` | `apps/market_pulse` (news_*) |
|---|---|---|
| 모델 | `NewsArticle` + `NewsEntity` (심볼 엔티티) | `MarketPulseNews` (6 매크로 카테고리) + `NewsViewLog` |
| 분류기 | `NewsClassifier` Engine A/B/C (종목/섹터/importance) | regex/키워드 6 카테고리(`services/news_classifier.py`) |
| 목적 | 종목 인사이트 + LLM 심층 + ML + Neo4j 이벤트 | 이상신호↔뉴스 페어링(`anomaly/news_pairing.py` → `AnomalySignalLog.paired_news`) |
| URL | `/api/v1/news/` | `/api/v2/market-pulse/`, `/api/v1/macro/` |

두 시스템 간 import 의존성 없음. **대체 아닌 용도 분리 병행.** 근거: `apps/market_pulse/models/news.py:1-10` 독스트링이 페어링 소비처 명시.

### 주요 갭 / 불일치

1. **(B) LLM Usage Phase 3 토큰 미추적** — 설계 §3.4가 의도한 한계. `NewsDeepAnalyzer`는 토큰 미저장(설계 §10 "분석기 수정 금지" 준수). coverage_warning만 구현.
2. **(B) 모니터링 레이어 테스트 공백** — pipeline-health/collection-logs/ml-trend/llm-usage/AlertLog/keyword-detail/check_pipeline_alerts 테스트 전무. 코어(classifier/ml_*/neo4j) 테스트는 충실하나 모니터링 설계가 추가한 13 API + AlertLog 미검증.
3. **`pending_sync` 추정 휴리스틱** — neo4j-status가 전용 `neo4j_synced` 필드 부재로 `updated_at > last_sync` 추정(`views.py:2241-2249`, 코드 주석에 명시). 부정확 가능.
4. **설계 개선점(갭 아님):** 키워드 상세가 런타임 2단 매칭 대신 `article_ids` 사전 저장 — 정확도/성능 우위.

### 등록/라우팅 상태

| 항목 | 상태 | 근거 |
|---|:---:|---|
| INSTALLED_APPS | ✅ | `config/settings.py:196` `'services.news'` |
| URL 라우팅 | ✅ | `config/urls.py:38` `api/v1/news/` → DefaultRouter NewsViewSet @action 자동등록 |
| Celery Beat | ✅ | `config/celery.py:429` 전 태스크 + check_pipeline_alerts, neo4j 큐 라우팅(:52-53) |
| 마이그레이션 | ✅ | `0001`~`0006_alertlog` 전부 |
| market_pulse 분리 | ✅ | `settings.py:207` 별도 등록, URL 충돌 없음 |

---

## 종합 권고 (읽기 전용 — 후속 작업 후보)

| 우선 | 항목 | 대상 | 성격 |
|:---:|---|---|---|
| 中 | 루트 빈 디렉토리 정리 (`sec_pipeline/`·`validation/`·`news/`) | 전체 | monorepo cleanup 잔재 |
| 中 | Validation thematic 원설계서(`validation_peer_phase6_7.md`) 갱신 — LLM 큐레이션→DNA 교차로 실구현 반영 | docs | 설계서↔코드 정합 |
| 中 | News 모니터링 레이어 + Validation API 뷰 단위 테스트 보강 | tests | 테스트 공백 |
| 低 | Validation `ValidationNewsSummary` 채우는 배치/API 구현 or 모델 폐기 결정 | validation | C 항목 정리 |
| 低 | Validation Phase7·SEC Gold Set 데이터 채움(chainsight 의존 / 라벨링) | data | 실효성 종속 |
| 低 | SEC FMP 레거시 네이밍 정리, fuzzy threshold 80↔85 문서 정합 | sec_pipeline | 명명/문서 부채 |
| 低 | Validation summary API `confidence` 시맨틱(basis→high/medium/low) | validation | 경미한 계약 불일치 |

**핵심 메시지**: 세 앱 모두 설계 대비 높은 구현 완성도(73~86%)에 등록·라우팅 정상 연결. "보고했는데 없음" 위험 불일치 0건. 남은 갭은 **데이터 채움 종속**(Phase7/Gold Set)과 **테스트 공백**, 그리고 **Validation thematic 설계서 미갱신** 1건이 가장 주목할 항목이다.
