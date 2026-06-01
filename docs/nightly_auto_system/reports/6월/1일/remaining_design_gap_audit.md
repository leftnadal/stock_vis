# SEC Pipeline + Validation + News 설계 갭 감사

> 작성일: 2026-06-01 · 읽기 전용 감사(코드 무수정) · 병렬 에이전트 3종 fan-out 결과 통합
> 대상: `docs/sec_pipeline/` vs `services/sec_pipeline/`, `docs/first_validation_system/` vs `services/validation/`, `docs/news/` vs `services/news/`
> 분류: **(A) 완전 구현 · (B) 부분 구현 · (C) 미구현 · (D) 폐기/대체**

---

## 0. 전제 — 서비스 리모델링으로 인한 경로 이동

세 앱 모두 "서비스 리모델링"으로 **`services/<app>/` 하위로 이동**했다. 루트의 `sec_pipeline/`, `validation/`은 `management/`·`migrations/`·`__pycache__`만 남은 **빈 잔존 디렉토리**이며 실제 코드는 `services/` 하위에 있다 (`news/`는 루트에 아예 없음).

- 앱 label은 유지(`apps.py`에서 `name="services.<app>"`, `label="<app>"`) → DB 테이블명/migration 영향 없음
- 공유 모델은 `packages/shared/<app>/`로 이동 (예: `packages/shared/metrics/models/`, `packages/shared/stocks/models/`)
- `task_done` 보고서들은 모두 **구 경로(루트)** 를 가정하므로 경로 표기가 현재와 불일치 — 단 기능 자체 영향은 없음
- `chain_sight`는 아직 `apps/` 네임스페이스에 잔존 → 앱별 이동 단계가 다름(추정)

---

## 1. 앱별 요약 (구현률)

| 앱 | A | B | C | D | 설계 대비 구현률 | 한 줄 결론 |
|----|---|---|---|---|----------------|-----------|
| **SEC Pipeline** | 18 | 1 | 0 | 3 | **≈ 82% A / 미구현 0%** | 설계 **초과 달성**. 갭은 전부 "운영 개선이 문서에 역반영 안 됨" |
| **Validation** | 11 | 5 | 1 | 1 | **≈ 61% A** | 백엔드 거의 완성, 단 **멀티 프리셋이 데이터로 계산 안 됨(C급)** + FE 범위 밖 |
| **News** | 14 | 1 | 0 | 1 | **≈ 95%** | 설계 3문서 전건 구현. **실제 구현이 설계서보다 앞서감** |

**종합 판정**: 세 앱 모두 **기능 결손(C)은 사실상 없거나 1건**이다. 진짜 갭은 두 종류로 수렴한다.
1. **문서 부채** (SEC·News): 코드가 task_done/설계서보다 앞서 있고, 문서가 갱신되지 않음 → 문서 동기화만 필요
2. **데이터 파이프라인 갭** (Validation): UI/모델/엔진은 있으나 **배치가 프리셋별 데이터를 생성하지 않아 기능이 무력화** → 실제 코드 작업 필요

---

## 2. SEC Pipeline 상세

### 2.1 구현률 요약
총 22개 PR/기능 단위 — **A 18 (≈82%) · B 1 · C 0 · D 3**. 17개 PR 설계의 모든 약속 산출물(모델/파일/함수/태스크/command/API)이 실제 코드에 존재. 미구현 0건.

### 2.2 PR/기능별 판정 테이블

| 기능 (PR) | 분류 | 근거 | task_done |
|-----------|------|------|-----------|
| PR-1 모델 8개 + migration | A | `models.py` 8개 모델 전부 + `migrations/0001_initial.py`(21KB). 제약(`neo4j_dirty` L112, `get_latest_by='as_of_date'` L215, `unique_together` L331) 충족 | 일치 |
| PR-2 SEC EDGAR 수집기 + 검증 | A | `collector.py` `SECFilingCollector`(get_filing_metadata/_get_cik/fetch_filing_html/extract_sections 3단계+fallback), `validators.py` | 일치 |
| PR-3 Track A 키워드필터 + Gemini | A | `normalizer.py`/`prompts.py`(v1)/`extractor.py`(gemini-2.5-flash,temp=0.1,thinking_budget=0)/`validator_track_a.py` | 일치 |
| PR-4 Celery tasks + 예외 | A | `tasks.py` collect_and_extract(retries=3)/extract_from_document, `exceptions.py` 5클래스, `sp500.py` | 일치 |
| PR-5 Gold Set + 평가 | A | `fixtures/gold_set_schema.py`+`gold_set.json`(10종목), `management/commands/evaluate_gold_set.py` | 일치 |
| PR-6 Phase 1 배치 | A | 런타임 검증 PR(코드 산출물 없음), 배치 인프라는 PR-17 `run_batch_and_report` | 일치 |
| PR-7 TickerMatcher | **B** | 3단계 매칭 존재하나 **fuzzy threshold 불일치**: doc "≥85%" → 실제 `_match_fuzzy(threshold=80)` L234 | **수치 불일치** |
| PR-8 Admin + signal | A | `admin.py` 8개 register, `signals.py` on_unmatched_resolved, `apps.py ready()` | 일치 |
| PR-9 sync_dirty_to_neo4j | A | `tasks.py:397` 2-Phase, select_for_update(skip_locked), KNOWN_TYPES 6종 | 일치 |
| PR-10 merger + 큐 command | A | `merger.py`(DQS 내부/사용자 분리), `process_unmatched_queue.py`(fuzzy≥0.90) | 일치 |
| PR-11~13 Track B + 서비스 | A | `keywords_track_b.py`/`prompts.py`/`validator_track_b.py`, tasks.py L272~333, 서비스는 `packages/shared/metrics/services/` 이동 | 일치(경로 이동) |
| PR-14 대시보드 + quality | A | `quality_checks.py`(7체크+stats), `views.py sec_pipeline_dashboard`, `templates/admin/sec_pipeline/dashboard.html` | 일치 |
| PR-15 on-demand + check_new_filings | A | `on_demand.py get_or_collect_filing`, `views.py FilingDataView`(200/202), `tasks.py check_new_filings` | 일치(+IsAdminUser) |
| PR-16 Intelligence | A | `intelligence.py` PipelineDataCollector(5차원)+Reporter(Gemini) | 일치 |
| PR-17 chord + E2E | A | `tasks.py:579/588` generate_intelligence_report + run_batch_and_report(Phase1→2→3) | 일치 |
| 의사결정 001 FMP→SEC EDGAR | D | collector가 SEC EDGAR만 호출, FMP 의존 제거. `decisions/001` 문서화 | 일치(계획된 대체) |
| **Celery Beat 등록** | D | task_done은 "주석 상태"라 했으나 `config/celery.py:783~802`에 **실제 등록**(sync */5분, check 매월1일, seed 매일12시) | **doc보다 진전** |
| **seed_relations_to_chainsight** | D | `tasks.py:338` 신규 task + beat 등록. SEC→Chain Sight `RelationConfidence` 연동. 어떤 task_done에도 없음 | **문서 없음** |
| **BLOCKED_NAMES 블록리스트** | D | `ticker_matcher.py:26~87`(2026-05-26, ~50개 비상장/직군/일반명사 차단) | **문서 없음** |
| **추가 management commands 3개** | D | `seed_company_aliases`/`rematch_unmatched`/`reprocess_unmatched_queue` | **문서 없음** |
| **audit P0 보안 패치** | D | `views.py FilingDataView IsAdminUser` L35, seed task "synced_to_neo4j 제거" | **문서 없음** |
| API 라우팅 prefix | **B** | CLAUDE.md `/api/v1/sec/*` vs 실제 `config/urls.py:45` `/api/v1/sec-pipeline/` | task_done 일치/CLAUDE.md 오기 |

### 2.3 주요 갭
- **(B) Fuzzy threshold 85→80 완화** — `ticker_matcher.py:234`. PR-7 보고서 "≥85%"와 수치 불일치. `match()`(L139)가 threshold 미전달 → 80 적용. 의도적 완화 가능성 있으나 문서 미반영.
- **(B) API prefix CLAUDE.md 오기** — 실제·task_done 모두 `/api/v1/sec-pipeline/`인데 CLAUDE.md 앱 표만 `/api/v1/sec/*`.
- **(C) 미구현 0건.**
- **(D, 전부 "문서에 역반영 안 된 운영 개선")**: Beat 실활성화 / seed_relations_to_chainsight(Chain Sight 온톨로지 연결 — 중요) / BLOCKED_NAMES / management commands 3종 / audit P0 패치.

### 2.4 비고
- 서비스 레이어 PR-13 산출물 실경로: `packages/shared/metrics/services/business_model_service.py` (task_done은 `metrics/services/`로 표기). `for_api` 게이트가 `overall_confidence` 노출 차단 — 설계대로.
- sync 태스크는 `config/celery.py:60`에서 `neo4j` 큐로 라우팅(CLAUDE.md neo4j 전용 워커 패턴 준수).
- **결론: 설계 대비 코드 결손 0. 실제 기능은 설계를 초과 달성. 필요한 것은 문서 갱신뿐.**

---

## 3. Validation 상세

### 3.1 구현률 요약
총 18개 기능 단위 — **A 11 (≈61%) · B 5 · C 1 · D 1**. 백엔드(BE-PR-1~6 + Peer Phase 1~7)는 거의 완전 구현. 단 **두 가지 큰 갭**: (1) 멀티 프리셋이 배치 데이터로 계산되지 않음(C급), (2) 프론트엔드 전체가 본 감사 경로(`services/validation/`) 밖.

### 3.2 Phase/기능별 판정 테이블

| 기능 | 분류 | 근거 | task_done |
|------|------|------|-----------|
| BE-PR-1 DB 모델(9종) | A | `models/`(BenchmarkDelta/CategorySignal/MetricLatest/PeerPreset/UserPeerPreference) + `packages/shared/metrics/models/`(MetricDefinition/Snapshot/PeerListCache/BatchJobRun) | 기반 |
| value_status/exclusion_reason | A | `packages/shared/metrics/models/metric_snapshot.py:45,56` | — |
| benchmark_basis/confidence | A | `models/benchmark_delta.py:37-56` (구 `benchmark_type` 잔존) | — |
| size_bucket/peer_tier | A | `packages/shared/metrics/models/benchmark.py:41,52` | — |
| IndustryClassification handling_mode | A | `category_signal_calculator.py:107` | — |
| BE-PR-2 시드(34지표+special) | A | `seed_validation_data.py` 34 METRIC_UPDATES + SPECIAL_KEYWORDS(Bank/Insurance/REIT/Utility) | — |
| BE-PR-3 Task 1~2 | **B** | `tasks.py:24-54`+fetcher/calculator. **Task1이 "FMP 수집"→"가용성 확인(check_and_fetch)"으로 축소** | — |
| BE-PR-4 Task 3~3.5(Peer+Benchmark) | A | `benchmark_calculator.py`(select_peers/assign_size_bucket)+`relative_metrics.py` | — |
| BE-PR-5 Task 4~6+오케스트레이터 | A | `category_signal_calculator.py`+`tasks.py:90-178` chain(1→2→3→3.5→4→5→6) | — |
| BE-PR-6 API 3종+Serializer | A | `api/views.py` Summary/Metrics/LeaderComparison+`interpretation.py` | — |
| config/urls.py 라우팅 | A | `config/urls.py:43` `api/v1/validation/` | — |
| Peer Phase 1 default | A | `preset_generator._generate_default` | — |
| Peer Phase 2~3 | A | `preset_generator.py` 5메서드+`_calc_confidence` | peer_system 일치 |
| Peer Phase 4~5(custom Compute-on-Read+Redis) | A | `custom_benchmark_engine.py`(Redis TTL 3600)+views custom 분기 | — |
| **멀티 프리셋 배치 계산** | **C** | 모델엔 `preset_key` 필드 있으나 calculator들이 **preset_key 쓰기 0건**, `PresetGenerator`가 `tasks.py`에 **미연동(0건)**. 프리셋 전환해도 default delta 조회 | **§1/§6 행렬 미충족** |
| Peer Phase 6 thematic | D | task_done "Gemini 사업모델 태깅"→ 실제 **GrowthStage×CapitalDNA 교차로 대체**(LLM 미사용) | 보고서와 일치(대체안 채택) |
| Peer Phase 7 LLM 대화형 필터 | A | `llm_peer_filter.py`(parse_filter_with_llm sync+execute)+`LLMPeerFilterView`+`llm-filter/` | 일치 |
| **프론트엔드(섹션9, FE-PR-1~7)** | **C(범위 외)** | `services/validation/` 하위에 FE 없음. `frontend/` 별도 디렉토리(감사 범위 밖) → 미판정 | — |

### 3.3 주요 갭
- **[C — 최우선] 멀티 프리셋이 "선택 UI만 있고 데이터가 없음"**
  - 설계 `validation_peer_system.md §1·§6`은 "프리셋별 BenchmarkDelta/CategorySignal 배치 계산" 전제. 모델은 반영(`benchmark_delta.py:80`/`category_score.py:64`에 `preset_key`).
  - 그러나 `benchmark_calculator.py`/`category_signal_calculator.py`가 `preset_key`를 **전혀 안 씀** → 항상 `default`만 생성.
  - `PresetGenerator.generate_for_symbols`는 존재하나 `tasks.py` 주간 체인에 **미연결** → 프리셋 생성 자체가 배치 자동화 밖(수동 추정).
  - `ValidationSummaryView`/`MetricsView`도 `preset_key` 필터 없이 항상 default 조회 → **preset 모드 전환 시 숫자가 안 바뀜**(custom 모드만 실제 재계산). `peer_system.md §11`의 "프리셋 전환 <50ms" 가치 무력화.
- **[B] BE-PR-3 Task1 범위 축소** — "FMP 5년 수집+snapshot 저장"이 "가용성 확인(ready/missing)"으로 대체. 설계 §6.3 FMP 호출 전략 본 배치 미수행.
- **[B] benchmark_delta 필드 중복** — 신규 `benchmark_basis`/`benchmark_confidence`(v1.3)와 구 `benchmark_type` 공존(마이그레이션 클린업 부채).
- **[B] Phase 6/7 데이터 의존성 미충족** — `peer_phase6_7.md`가 경고한 대로 CapitalDNA/SensitivityProfile/NarrativeTag 데이터 0건. 코드는 완성이나 **실데이터 커버리지 제한**(Phase7 필터가 해외매출+R&D 조건 시 0건 반환).
- **[B] ValidationNewsSummary 모델만 존재** — `models/news_summary.py`+migration은 있으나 채우는 task/API 부재(tasks.py 6태스크에 뉴스 집계 없음) → **모델만 미완**(추정).

### 3.4 비고
- **Summary peer_info confidence 오용(경미)** — `views.py:131` `"confidence": peer_cache.benchmark_basis`. 설계 5.2는 high/medium/low 기대 → FE 표기 깨질 수 있음(추정).
- **카테고리/지표 키 명명 불일치** — 설계 `cash_flow`→코드 `cash_flow_quality`, `ocf_trend_3y`→`cash_from_ops_trend`, `buyback_yield`→`buyback_offsets_sbc`, `shareholder_yield`→`net_shareholder_yield`. 34개 카운트는 일치.
- **프론트엔드는 본 감사 경로 밖** — MEMORY.md상 "1차 검증 완료"라 `frontend/`에 구현 가능성 높음. 정확한 FE 갭은 `frontend/` 별도 감사 권장.
- **권장 후속**: (1) `tasks.py`에 PresetGenerator Task 추가 + calculator를 preset 루프로 확장(C 해소), (2) Summary/Metrics 뷰에 preset_key 필터 주입, (3) 구 `benchmark_type` 마이그레이션 제거.

---

## 4. News 상세

### 4.1 구현률 요약
총 16건(설계 3문서 기준) — **A 14 (≈95%) · B 1 · C 0 · D 1**. 모니터링 설계서가 Phase A/B/C로 단계 구분했으나 **세 단계 모두 백엔드+프론트 전부 구현** — 설계서("Phase B/C는 추후")보다 실제 구현이 앞서 있다.

### 4.2 기능별 판정 테이블

| 기능 | 분류 | 근거 |
|------|------|------|
| **키워드 상세 API**(`keyword-detail`) | A | `api/views.py:676` keyword_detail action. date+index, 404/400, `analysis:null` 폴백, Gemini 동기(`_generate_keyword_analysis` L812), `updated_at` epoch 캐시키(L733) |
| `search_terms_en` 스키마 확장 | A | `keyword_extractor.py:268,283-285,338` 프롬프트+파싱 |
| 2단 기사 매칭 | A | views.py:756-772 — `related_symbols` 우선 + `search_terms_en` title icontains. +`article_ids` 직접조회(L740-746)가 설계보다 정확 |
| Redis 캐시+index 안정성 | A | `news:keyword_detail:{date}:{index}:{updated_epoch}`(L733), TTL 1h(L808) |
| **BottomSheet v1** | A | `frontend/components/news/KeywordDetailSheet.tsx`, `DailyKeywordCard.tsx`, `KeywordBadge.tsx` |
| **BottomSheet v2 가로 스크롤 Strip** | A | activeIndex(L59)/scrollIntoView(L77)/Strip pill(L106-151)/좌우 버튼/initialIndex+keywords props |
| v2 `max-w-2xl` 데스크탑 너비 | A | `frontend/components/thesis/common/BottomSheet.tsx:38` |
| v2 keepPreviousData | A | KeywordDetailSheet:99 |
| **Phase 0 `_log_collection()` 커버리지** | A | tasks.py 6개 Phase 태스크 전부 호출(L179/230/487/543/591/674) |
| **Phase A-BE 4개 모니터링 API** | A | collection_logs(L1411,KST)/pipeline_health(L1537,6단계+주말62h)/ml_trend(L1911)/llm_usage(L2002). 전부 IsAdminUser |
| **Phase A-FE 대시보드+sub-tab** | A | NewsTab.tsx(overview/pipeline)+NewsPipelineSubTab+6 컴포넌트 |
| **Phase B-BE timeline/neo4j/ml-rollback** | A | task_timeline(L2134)/neo4j_status(L2202)/ml_rollback_preview(L2276)/ml_rollback(L2325, confirm:true 필수) |
| **Phase B-FE 차트/비교** | A | TaskTimelineChart/Neo4jStatusCard/MLCompareView |
| **Phase C-BE AlertLog 모델+API** | A | models.py:553 AlertLog(7종 TextChoices, db_table news_alert_logs, 인덱스2)+migration 0006+alerts(L2378)/alerts_resolve(L2453) |
| **Phase C check_pipeline_alerts+Beat** | A | tasks.py:1179(7트리거+중복방지)+`config/celery.py:428` 30분 crontab |
| **Phase C-FE 알림 배지** | A | AlertBadge/AlertList + `frontend/app/admin/page.tsx:14,64` |
| `recommendations` API(레거시) | D | views.py:1337 "Deprecated", 팩트 기반 `insights`(L857)로 대체. 3설계서와 무관 |

### 4.3 주요 갭
- **(B) LLM Usage — Phase 3 심층분석 토큰 미추적** — `llm-usage`(views.py:2002). **설계서 §3.4가 의도적으로 명시한 한계**. `NewsDeepAnalyzer`가 토큰 미저장 → 키워드 추출 토큰만 집계. 코드는 `coverage_warning`(L2116-2119)을 설계 문구대로 응답에 포함, FE `LLMUsageSummary.tsx`도 경고 배너 표시. 설계가 "Phase B에서 토큰 로깅 추가 후 통합"이라 했으나 deep_analysis 토큰 로깅 미추가(추정). → 설계 의도 범위 내 부분 구현.
- **(C) 미구현 0건.** 세 설계서 모든 명시 기능이 코드에 존재.
- **(D) `recommendations` API** — 감사 대상 외 별개 레거시. `news-insights.md`의 용어 변경(StockRecommendations→NewsHighlightedStocks) 방향으로 `insights` 대체. FE에 RecommendationCard/StockRecommendations 잔존(deprecated).

### 4.4 비고
- 설계 3문서는 **"키워드 상세 화면"+"파이프라인 모니터링"에 국한**. News Intelligence Pipeline v3 본체(규칙엔진/LLM/ML/Neo4j/Shadow·Production/LightGBM/멀티프로바이더)는 `sub_claude_md/news-insights.md` 기준으로만 범위 파악 — v3 본체는 "6단계 전체 완료, 테스트 607개"로 명시, 서비스 16개+모델 실재 확인. 본 4분류는 **3설계서 범위 한정**.
- **모니터링 설계서는 v1.1 DRAFT "구현 전" 상태로 작성됐으나 실제 코드는 Phase A/B/C 전 단계 완성** — "Phase B는 추후", "check_pipeline_alerts는 @infra"라던 미래형 항목까지 모두 구현 완료. 구현이 설계 갱신 없이 앞서나간 케이스.
- "기존 파이프라인 로직 변경 금지" 원칙 준수 확인 — 모니터링 API는 순수 읽기 레이어 + `_log_collection()` 추가(유일 허용 예외)만 들어감.
- **개선점**: 키워드 상세 API가 2단 매칭에 더해 `article_ids` 직접 조회(`keyword_extractor.py:154-162`, source_indices→article_ids 매핑) 우선 사용 → 한↔영 매칭 부정확성 원천 차단.

---

## 5. 종합 권고 (우선순위)

| 우선 | 앱 | 항목 | 성격 |
|------|----|----|------|
| **P1** | Validation | 멀티 프리셋 배치 계산 연결(PresetGenerator→tasks.py 체인 + calculator preset 루프 + 뷰 preset_key 필터) | **기능 갭 — 코드 작업** |
| P2 | Validation | 프론트엔드(FE-PR-1~7) 별도 감사 (`frontend/` 대상) | 범위 확장 |
| P3 | Validation | benchmark_type 구 필드 제거 + Summary confidence 필드 오용 수정 | 정리/버그 |
| P4 | SEC | task_done/CLAUDE.md 문서 동기화 (Beat 활성화·seed_relations·BLOCKED_NAMES·command 3종·API prefix·fuzzy 80) | **문서 부채** |
| P5 | News | 모니터링 설계서 v1.1 DRAFT → "구현 완료"로 상태 갱신 + deep_analysis 토큰 로깅 추가(B 해소) | 문서+소규모 코드 |

**총평**: 세 앱 모두 설계 대비 기능 결손은 거의 없다. SEC·News는 **구현이 문서를 앞서간 "문서 부채"** 가 본질이고, Validation만 **"UI/모델은 있으나 배치가 데이터를 안 만드는" 실질 기능 갭(멀티 프리셋)** 1건이 P1으로 남는다.
