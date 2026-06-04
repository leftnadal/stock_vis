# SEC Pipeline + Validation + News 설계 갭 감사

> **유형**: 읽기 전용 감사 (코드 미수정)
> **일자**: 2026-06-04 야간 자동화
> **대상**: `docs/sec_pipeline/` vs `services/sec_pipeline/`, `docs/first_validation_system/` vs `services/validation/`, `docs/news/` + `docs/news_intelligence_plan/` vs `services/news/`
> **분류 체계**: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## ⚠️ 사전 발견: 앱 위치 재구성 (서비스 리모델링)

세 앱 모두 **루트(`/sec_pipeline/`, `/validation/`)에는 `.pyc` 잔재만 남고 실제 소스는 `services/`로 이전**되었다. `news/`는 루트에 아예 없다.

| 표기(CLAUDE.md) | 실제 위치 | INSTALLED_APPS |
|----------------|----------|----------------|
| `sec_pipeline/` | `services/sec_pipeline/` | `config/settings.py:205` (`PR8a-1 이동`) |
| `validation/` | `services/validation/` | `config/settings.py:203` (`PR8a-1 이동`) |
| `news/` | `services/news/` | `config/settings.py:196` (`PR8a-2 이동`) |

- 루트의 `sec_pipeline/`·`validation/` 디렉토리는 **`__pycache__`만 포함한 stale 잔재** → 정리 대상(저위험 부채).
- 기능은 동일, 패키지 경로만 리팩터링. task_done 보고서들의 import 경로(`sec_pipeline/`, `metrics/services/`, `stocks.models`)는 모두 구버전 표기로, 실제는 `services.*`, `packages.shared.*`.

---

## 앱별 요약 (구현률)

| 앱 | A 완전 | B 부분 | C 미구현 | D 폐기/대체 | 대략 구현률 | 핵심 갭 |
|----|:---:|:---:|:---:|:---:|:---:|--------|
| **SEC Pipeline** | 24 | 2 | 0 | 1 | **~89% (A)** | 자동화 테스트 부재 / 문서가 구현보다 뒤처짐 |
| **Validation** | 12 | 6 | 2 | 2 | **~55% (A)** | 프리셋 배치 미트리거 + read-path preset_key 필터 누락 |
| **News** | 33 | 4 | 0 | 1 | **~87% (A)** | 모니터링·키워드상세 레이어 **테스트 0건** |

**총평**:
- **SEC Pipeline · News**는 설계 산출물 대비 거의 완전 구현. 미구현(C) 기능은 없음.
- **Validation**은 핵심 백엔드 파이프라인(배치 Task 1-6, 지표·벤치마크·시그널, rule-based API 3종)은 견고하나, **Phase 2~3 프리셋 시스템이 "정의는 됐으나 운영에 연결 안 된" 상태**가 가장 큰 갭.
- 세 앱 공통으로 **신규 레이어의 테스트 커버리지 부재**가 반복 패턴 (SEC `tests.py` 빈 스텁, News 모니터링 0건).
- 사전 가설 "News 모니터링은 설계만 있고 미구현" → **틀림**. Phase A/B/C 백엔드 13개 API + 프론트 12개 컴포넌트 전부 구현됨.

---

## SEC Pipeline 상세

### 구현률
**27개 컴포넌트 중 A 24 / B 2 / C 0 / D 1 (~89% 완전 구현)**. 17개 PR 완료 보고서가 주장한 산출물이 거의 전부 실제 코드에 존재하며, 일부는 **보고서보다 더 진전된 상태**.

### 컴포넌트별 분류 (핵심)

| 컴포넌트 | 설계출처 | 실제파일 | 분류 | 근거 |
|---------|---------|---------|------|------|
| 8개 Django 모델 | PR-1 | `models.py` | **A** | RawDocumentStore/SupplyChainEvidence/BusinessModelSnapshot/BusinessModelEvidence/FilingProcessLog/CompanyAlias/UnmatchedCompanyQueue/PipelineIntelligenceReport (migration 0001에 8/8) |
| SEC EDGAR 수집기 | PR-2 | `collector.py` | **A** | get_filing_metadata / fetch_filing_html / extract_sections(+fallback) |
| Track A (공급망 추출) | PR-3 | `normalizer.py`+`extractor.py:35`+`validator_track_a.py` | **A** | SUPPLY_CHAIN_KEYWORDS 필터 → Gemini extract_supply_chain → 검증·저장 + GENERIC_COMPANY_TERMS 필터 |
| Track B (사업모델 추출) | PR-11~13 | `keywords_track_b.py`+`extractor.py:97`+`validator_track_b.py` | **A** | BM_KEYWORDS 5필드 → extract_business_model → save_business_model_snapshot (PR-4 시점 `pass`였으나 채워짐) |
| TickerMatcher 3단계 | PR-7 | `ticker_matcher.py:90` | **A** | alias→exact→fuzzy + match_with_queue + BLOCKED_NAMES 블록리스트(2026-05-26 추가) |
| Neo4j sync (2-Phase) | PR-9 | `tasks.py:397` | **A** | select_for_update(skip_locked) + dynamic relation type, `neo4j` 큐 라우팅 |
| Merger + DQS | PR-10 | `merger.py` | **A** | merge_relationship + calculate_edge_dqs |
| Intelligence Reporter | PR-16 | `intelligence.py` | **A** | PipelineDataCollector 5차원 + Reporter |
| on_demand 수집 + API | PR-15 | `on_demand.py:18`+`views.py:29` | **A** | get_or_collect_filing(1년/1시간 가드) + FilingDataView(200/202, IsAdminUser) |
| Quality checks 7개 + 대시보드 | PR-14 | `quality_checks.py`+`views.py:15` | **A** | run_post_batch_quality_checks + admin 대시보드 템플릿 |
| **tests.py** | PR-17 (E2E) | `tests.py` | **B** | **빈 스텁** (`# Create your tests here.` 1줄) — 자동화 테스트 0건 |
| Gold Set 평가 | PR-5 | `fixtures/gold_set.json`+`evaluate_gold_set` | **B** | 10종목 fixture 존재하나 실제 라벨된 관계는 NVDA 위주 (보고서가 인정한 라벨 부족) |
| **Celery Beat 스케줄** | PR-17 | `config/celery.py:783-802` | **D→실질 A** | 보고서는 "주석 상태"라 기재했으나 **실제 활성화됨** (sec-sync-dirty-neo4j 5분, sec-check-new-filings 매월 1일) |

### 주요 갭/불일치
- **자동화 테스트 부재**: `services/sec_pipeline/tests.py`는 빈 스텁. PR-17이 "E2E 테스트"를 주장하나 재현 가능한 테스트 코드는 0건 (보고서는 shell 수동 실행 결과 기록일 뿐).
- **문서가 구현보다 뒤처짐 (stale doc)**:
  - Celery Beat: 보고서 "주석" vs 실제 "활성".
  - 설계 문서에 없는 추가 구현: `seed_relations_to_chainsight` task(SEC→Chain Sight 연동), management command 3종(rematch/reprocess/seed_company_aliases), BLOCKED_NAMES.
- **API prefix 표기 오류**: CLAUDE.md는 `/api/v1/sec/*`로 표기하나 실제는 **`/api/v1/sec-pipeline/`** (`config/urls.py:45`).

### API 라우팅
- ✅ 정상 연결. `config/urls.py:45` → `api/v1/sec-pipeline/` → `services.sec_pipeline.urls`
  - `GET /api/v1/sec-pipeline/filing/<symbol>/` (IsAdminUser)
  - `/api/v1/sec-pipeline/admin/dashboard/` (staff)

**결론**: 미구현(C) 0건. 유일한 실질 갭은 (1) 자동화 테스트 부재, (2) 일부 문서가 구현보다 뒤처짐. 운영 단계에서 오히려 설계를 초과하는 추가 구현 다수.

---

## Validation 상세

### 구현률
**22개 컴포넌트 중 A 12 / B 6 / C 2 / D 2 (~55% 완전 구현)**. 핵심 파이프라인은 견고하나 갭이 **Phase 2 프리셋의 운영 연결**에 집중.

### 컴포넌트별 분류 (핵심)

| 컴포넌트 | 설계출처 | 실제파일 | 분류 | 근거 |
|---------|---------|---------|------|------|
| 배치 Task 1-6 오케스트레이터 | design §6 | `tasks.py:158-178` | **A** | chain(Task1→2→3→3.5→4→5→6), Beat 일요일 2시(`celery.py:773`) |
| 지표 계산 + value_status | design §7.2 | `services/metric_calculator.py` | **A** | 33개 지표 + value_status 판정 |
| Peer 선정 (industry+size fallback) | design §3.2 | `services/benchmark_calculator.py` | **A** | assign_size_bucket / get_adjacent_buckets |
| 벤치마크 delta | design §3.3 | `benchmark_calculator.py`+`models/benchmark_delta.py` | **A** | CompanyBenchmarkDelta benchmark_basis/confidence |
| 카테고리 시그널 | design §3.1 | `services/category_signal_calculator.py` | **A** | percentile 균등평균, special→gray, 7카테고리×34지표 |
| rule-based 해석 3종 | design §3.x | `services/interpretation.py` | **A** | summary/metric/leader/trend |
| API summary/metrics/leader | design §5 | `api/views.py` | **A** | S&P500 게이트(422), no_data(404), 22지표 비교 |
| Compute-on-Read (커스텀 peer) | peer_system §1/§7 | `services/custom_benchmark_engine.py` | **A** | numpy percentile + Redis 캐시 TTL 1h, summary custom 분기 |
| 커스텀 peer / preference API | peer_system §7 | `api/views.py:572-619` | **A** | POST/DELETE peer-preference, UserPeerPreference |
| LLM 대화형 Peer 필터 (Phase 7) | phase6_7 | `services/llm_peer_filter.py`+`views.py:622` | **A** | Gemini Flash 동기호출(thinking_budget=0, 규칙 준수), POST /llm-filter/ |
| **Peer 프리셋 6종 정의** | peer_system §2/§3 | `services/preset_generator.py:41-524` | **B** | 6종 메서드 전부 구현 — **단 어떤 Celery Task/command도 호출 안 함** (production 트리거 부재) |
| **프리셋 선택 read-path** | peer_system §7 | `api/views.py` | **B** | 스키마에 preset_key 있으나 summary/metrics View가 **조회 시 preset_key 미필터**(`views.py:106,149,316`) → 프리셋 전환해도 default 반환 |
| confidence_score 계산 | peer_system §5 | `preset_generator.py:526-544` | **B** | peer수+특수산업 패널티만 — **업종순도·지표커버리지 패널티 미구현** |
| **Thematic 프리셋** | phase6 | `preset_generator.py:425-524` | **D** | 설계는 Gemini theme_tags 기반 → **GrowthStage×CapitalDNA 조합으로 대체**, LLM 태깅 미사용 |
| **news_summary** | 별도 PR-5 | `models/news_summary.py` | **C** | 모델·admin만 존재, **write 코드 0건** (dead model) |
| **Phase 5 LLM 해석 캐시** | design §8/§10 | — | **C(의도된 보류)** | Phase 1 rule-based only, 모든 응답 `_source='rule'` |
| **Phase 7 Thesis 연동** | phase6_7 | — | **D/미구현** | thesis 모델에 peer_preset_key/peer_filter_query 필드 추가 흔적 없음 |

### 주요 갭/불일치
- **🔴 프리셋 자동생성이 배치에 미연결 (최대 갭)**: `PresetGenerator`(6종 전부 구현)가 `tasks.py` chain·management command 어디에서도 호출 안 됨. grep상 production 참조는 자기 파일뿐(테스트만 호출). → **운영 DB에 default 외 프리셋이 자동 생성되지 않음**.
- **🔴 프리셋 전환 read-path 미연결**: `CompanyBenchmarkDelta`/`CategorySignal` 스키마에 preset_key가 있고 unique_together에도 포함되나, summary/metrics View가 조회 시 preset_key를 전혀 필터링하지 않음. → 사용자가 size_peers 선택해도 신호등은 default 데이터. **custom mode만** Compute-on-Read로 실제 전환됨.
- **`peer_info.confidence` 의미 오염**: summary 응답에서 `confidence = benchmark_basis`(`views.py:131`)로 'industry_size' 같은 문자열이 confidence 자리에 들어감 (설계는 high/medium/low 기대).
- **모델 파일명 잔재**: `category_score.py` 파일명 vs 내부 클래스 `CategorySignal` (테이블명 변경 반영 불완전).

### Phase별 상태
| Phase | 상태 |
|-------|------|
| Phase 1 (default 프리셋·배치·API) | 완료 (read-path preset_key 필터 누락) |
| Phase 2 (sector_all/size_peers) | **부분** — 생성기 O, 배치 트리거 X, read 필터 X |
| Phase 3 (quality_top/lifecycle + confidence) | **부분** — 생성 로직 O, confidence 일부, 배치 트리거 X |
| Phase 4 (UserPeerPreference + 선택 API) | 완료 |
| Phase 5 (커스텀 Compute-on-Read + Redis) | 완료 |
| Phase 6 (Thematic, LLM 큐레이션) | **대체** — GrowthStage×CapitalDNA 조합으로 변경 |
| Phase 7 (LLM 대화형 필터) | 완료 (Thesis 연동만 미구현) |
| 메인 design Phase 5 (LLM 해석 캐시) | **의도된 보류** — rule-based only |

### API 라우팅
- ✅ `config/urls.py:43` → `api/v1/validation/` → 6개 엔드포인트 활성 (summary/metrics/leader-comparison/presets/peer-preference/llm-filter).
- ⚠️ 경로명 불일치: phase6_7 설계는 `/peer-filter/`, 실제는 `/llm-filter/` (기능 동일).

---

## News 상세

### 구현률
**38개 컴포넌트 중 A 33 / B 4 / C 0 / D 1 (~87% 완전 구현)**. 설계 3건 + Intelligence Pipeline v3 6단계가 거의 전부 구현. **사전 가설("모니터링은 설계만") 반박됨**.

### 컴포넌트별 분류 (핵심)

| 컴포넌트 | 설계출처 | 실제파일 | 분류 | 근거 |
|---------|---------|---------|------|------|
| 규칙 엔진 (Engine A/B/C) | v3 Phase1 | `news_classifier.py`(440줄) | **A** | DEFAULT_WEIGHTS, `_load_deployed_weights` 폴백 |
| LLM 심층 분석 (Tier A/B/C) | v3 Phase2 | `news_deep_analyzer.py` | **A** | tasks.py:555 analyze_news_deep |
| ML Label 수집 | v3 Phase2 | `ml_label_collector.py` | **A** | tasks.py:603, test 92건 |
| ML 학습 (LR + LightGBM) | v3 Phase4/6 | `ml_weight_optimizer.py`(49KB) | **A** | tasks 733/941, test_lightgbm 41건 |
| ML Production + Shadow/Prod Mode | v3 Phase5 | `ml_production_manager.py:48-153` | **A** | check_auto_deploy, deployment_status shadow/deployed 전환 |
| Neo4j 뉴스 이벤트 | v3 Phase3 | `news_neo4j_sync.py`(37KB) | **A** | tasks.py:637 sync_news_to_neo4j(neo4j 큐, lazy import) |
| Multi-provider 수집 | overview | `providers/{finnhub,marketaux,fmp}.py` | **A** | aggregator 통합 |
| Circuit Breaker + Deduplicator | — | `circuit_breaker.py`+`deduplicator.py` | **A** | FMP 태스크 is_open() 게이트, URL해시+제목유사도 0.85 |
| keyword-detail API | keyword_detail §4 | `views.py:676-805` | **A(+개선)** | date+index 파싱, 캐시키, Gemini 요약 — **article_ids 직접조회 우선**(설계 2단매칭은 폴백으로 강등) |
| BottomSheet v1/v2 | bottomsheet_v2 | `KeywordDetailSheet.tsx`+`thesis/common/BottomSheet.tsx:38` | **A** | 가로 Strip pill, initialIndex+keywords[], max-w-2xl |
| **파이프라인 모니터링 Phase A** (collection-logs/pipeline-health/ml-trend/llm-usage) | monitoring §3 | `views.py:1411~2002` | **A** | 4개 API, PHASE_CONFIG 6개, IsAdminUser |
| **모니터링 Phase B** (task-timeline/neo4j-status/ml-rollback-preview·rollback) | monitoring §5 | `views.py:2134~2325` | **A** | 4개 API, confirm=true 2단계 |
| **모니터링 Phase C** (AlertLog + alerts/resolve + check_pipeline_alerts) | monitoring §6 | `models.py:553`+`views.py:2378`+`tasks.py:1179` | **A** | 7 TriggerType, Beat 등록(celery.py:429), `_create_alert_if_new` 중복방지 |
| FE 모니터링 12개 컴포넌트 | monitoring §4/5/6 | `frontend/components/admin/news/*` | **A** | PipelineStatusBar~AlertList 전부 존재 |
| **모니터링·알림 테스트** | 설계 검증 | `tests/news/` | **C** | pipeline-health/keyword-detail/collection-logs/ml-rollback/check_pipeline_alerts/AlertLog 테스트 **0건** |
| 종목 인사이트 | news-insights | `stock_insights.py`(837줄) | **A** | views.py:857 /insights/ |
| 개인화 피드 / Market Feed | v3 Phase A/B | `personalized_feed.py`+`market_feed.py` | **A** | views.py 1042/960 |
| **종목 추천 (recommender)** | news-insights 용어변경 | `stock_recommender.py`(314줄) | **D** | 용어변경표상 "추천→인사이트 대체" 대상이나 **잔존**(views.py:1338 recommendations action 살아있음) |

### 주요 갭/불일치
- **🔴 모니터링·키워드상세 레이어 테스트 0건 (최대 갭)**: `tests/news/`의 600개 테스트는 전부 파이프라인 내부 서비스 대상. 설계에 명시된 신규 API 13종 + `check_pipeline_alerts` 태스크 + AlertLog 모델 테스트가 repo 전체에서 0건. **코드는 (A)지만 검증은 (C)**.
- **keyword-detail이 설계 초과 구현**: 설계 §3-2의 2단 매칭 대신 `article_ids` 직접 조회 우선 → 설계 문서 stale.
- **테스트 수 명세 불일치(경미)**: news-insights "607개" / FINAL_SUMMARY "587개" / 실제 카운트 "600개" — 문서 간 숫자 비동기화.

### 설계만 있고 미구현인 것
- **없음**. Phase A/B/C 전부 백엔드+프론트엔드 완료.
- 권고(필수 아님)였던 `cleanup_old_collection_logs`(90일 정리)만 미확인 — 갭 미분류.

### (D) 폐기/대체
- `stock_recommender.py` + `recommendations` action: news-insights 용어변경표가 "AI 추천 종목 → 뉴스 언급 종목"(StockRecommendations→NewsHighlightedStocks, 추천 점수 제거)을 명시. `stock_insights.py`(NewsBasedStockInsights)가 정식 대체이나 recommender는 완전 삭제 안 됨 → 잔존 코드.

### API 라우팅
- ✅ `config/urls.py:38` → `api/v1/news/` → DefaultRouter + NewsViewSet basename="news" → 모든 @action 자동 라우팅. 모니터링/롤백/알림 엔드포인트 `IsAdminUser` 적용(보안 요건 충족).

---

## 종합 권고 (우선순위)

| # | 앱 | 갭 | 심각도 | 권고 |
|---|----|----|:---:|------|
| 1 | Validation | 프리셋 6종 배치 미트리거 | 🔴 高 | `tasks.py` chain에 PresetGenerator 호출 단계 추가, 또는 별도 command |
| 2 | Validation | summary/metrics read-path preset_key 미필터 | 🔴 高 | View 조회 쿼리에 선택된 preset_key 필터 적용 (프리셋 전환 미작동 해소) |
| 3 | News | 모니터링·키워드상세 13개 API 테스트 0건 | 🟡 中 | pipeline-health/keyword-detail/check_pipeline_alerts/AlertLog 테스트 추가 |
| 4 | SEC | `tests.py` 빈 스텁 | 🟡 中 | E2E/단위 테스트 코드화 (현재 수동 shell 검증만) |
| 5 | Validation | `peer_info.confidence` = benchmark_basis 오염 | 🟡 中 | confidence를 high/medium/low로 매핑 |
| 6 | Validation | news_summary dead model | 🟢 低 | write 경로 구현 또는 모델 제거 결정 |
| 7 | 공통 | 루트 `/sec_pipeline/`·`/validation/` .pyc 잔재 | 🟢 低 | stale 디렉토리 정리 |
| 8 | 문서 | CLAUDE.md `/api/v1/sec/*` → 실제 `/api/v1/sec-pipeline/` | 🟢 低 | 표기 수정 |
| 9 | News | recommender 잔존 코드 | 🟢 低 | 용어변경 완수(삭제) 또는 보류 결정 명문화 |
| 10 | SEC | Beat/chainsight 연동 문서 stale | 🟢 低 | PR-17 보고서에 활성화 상태 반영 |

> **공통 패턴**: 세 앱 모두 "코드는 완성됐으나 (a) 운영 배치에 미연결[Validation], (b) 테스트로 검증 안 됨[SEC·News]"이 핵심 부채. 미구현(C)보다 **"구현됐으나 연결/검증 누락"**이 지배적.
