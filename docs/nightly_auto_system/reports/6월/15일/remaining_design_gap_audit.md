# SEC Pipeline + Validation + News 설계 갭 감사

> 생성: 2026-06-15 야간 자동 감사 | **읽기 전용 — 코드 미변경**
> 방법: `docs/` 설계서·`task_done/` 완료보고서 vs `services/` 실제 구현 cross-check (Explore 에이전트 3병렬)
> 분류 기준: **(A)** 완전 구현 · **(B)** 부분 구현 · **(C)** 미구현 · **(D)** 폐기/대체

---

## 0. 구조 사전 발견 (전 앱 공통)

세 앱 모두 **루트 디렉토리(`sec_pipeline/`, `validation/`, `news/`)는 `__pycache__`만 남은 레거시**이고, 실제 코드는 **`services/` 하위로 이동**되어 있다.

| 설계서가 가리키는 앱 | 레거시(루트) | 실제 구현 |
|---|---|---|
| SEC Pipeline | `sec_pipeline/` (pycache만) | `services/sec_pipeline/` |
| Validation | `validation/` (pycache만) | `services/validation/` |
| News | (루트 디렉토리 없음) | `services/news/` |

→ **앱 이전 자체는 분류 (D) 폐기/대체**(서비스 레이어 통합 리모델링). 갭이 아니라 설계 변경. 단, 설계서·CLAUDE.md의 경로 표기가 구버전(`sec_pipeline/*`)으로 남아 있어 **문서 경로 갱신 부채**가 존재한다.

---

## 1. 앱별 요약 (구현률)

| 앱 | 백엔드 | 프론트 | 테스트 | 종합 구현률 | 핵심 갭 |
|----|--------|--------|--------|-------------|---------|
| **SEC Pipeline** | 95% (A18/B2) | (Admin 대시보드만, 일반 FE 해당 없음) | 분산 unit test 존재, 앱내 `tests.py` 빈 파일 | **~95%** | Celery Beat 주석 처리(자동 스케줄 OFF) · Ticker 매칭률 3%(데이터/프롬프트 품질) · Gold Set 라벨 부족 |
| **Validation** | ~95% (백엔드 거의 완전) | **0% (전부 미구현)** | **0% (`tests.py` 빈 파일)** | **~75%** | 프론트엔드 FE-PR-1~7 전무 · 특수산업 대체지표 미완 · LLM필터의 Chain Sight 데이터 의존성 미검증 |
| **News** | Phase A 100% / Phase B·C API 미구현 | Phase A 완전, Phase B·C는 UI 스켈레톤만 | `tests.py` 존재(Phase B·C 미커버) | **~70~75%** | Phase B API 4종 미구현 · Phase C(알림) 모델만 존재, API·Celery 태스크 없음 |

> **공통 패턴**: 세 앱 모두 **백엔드 코어는 완성도가 높으나, (a) 자동화 스케줄/알림 같은 "운영 연결부", (b) 프론트엔드, (c) 테스트**가 후순위로 밀려 갭이 집중됨. 특히 **"UI 컴포넌트는 만들었으나 뒷단 API가 없는"** 패턴(Validation FE 전무 / News Phase B·C)이 반복적으로 관찰됨.

---

## 2. SEC Pipeline 상세

### 구현률: A 18 / B 2 / C 0 / D 1 → **~95%**

17개 PR(SEC-PR-1~17) 기준 대부분 완전 구현. 코드는 견고하나 **운영 데이터 품질·자동화**에서 갭.

### PR별 상태

| PR | 제목 | 분류 | 근거 |
|----|------|------|------|
| 1 | Django 앱 + 8개 모델 + migration | **A** | `services/sec_pipeline/models.py:15-299` + `migrations/0001_initial.py` |
| 2 | SEC EDGAR 수집기 + 섹션추출 | **A** | `collector.py:39-200+` (FMP→SEC EDGAR 대체) |
| 3 | Track A 키워드필터 + Gemini | **A** | `extractor.py: extract_supply_chain()` + `validator_track_a.py` |
| 4 | Celery tasks + 에러핸들링 | **A** | `tasks.py:22-369` (retry/backoff) |
| 5 | Gold Set + 평가 | **B** | `fixtures/gold_set.json` 존재하나 라벨 부족(NVDA만 완전) → Precision 8.5%(목표 70%) |
| 6 | Phase 1 배치 | **A** | 15종목 배치 완료. JNJ만 Item순서 검증 실패(실패율 6.7%) |
| 7 | Ticker 매칭(3단계) | **B** | `ticker_matcher.py:90-287` 코드는 A급이나 매칭률 3%(66 evidence 중 2) — 일반명사·비미국주식 |
| 8 | Admin 큐 + post_save signal | **A** | `signals.py: on_unmatched_resolved()` + `admin.py` |
| 9 | sync_dirty_to_neo4j | **A** | `tasks.py:398-540` (DELETE+CREATE, sole writer, dirty flag) |
| 10 | 관계 병합 + DQS | **A** | `merger.py:36-73` (RELATIONSHIP_SPECIFICITY + DQS) |
| 11~13 | Track B(키워드/Gemini/서비스) | **A** | `keywords_track_b.py`, `extractor.py: extract_business_model()`, `validator_track_b.py` |
| 14 | Admin 대시보드 + 품질체크 7종 | **A** | `views.py: sec_pipeline_dashboard()` + `quality_checks.py:17-110+` |
| 15 | On-demand API | **A** | `views.py: FilingDataView` + `on_demand.py` (200/202, IsAdminUser) |
| 16 | Intelligence Report 5차원 | **A** | `intelligence.py: PipelineIntelligenceReporter.generate_report()` |
| 17 | Celery chord + E2E | **B** | `tasks.py: run_batch_and_report()` 구현되었으나 **Beat 스케줄 주석 처리** (`tasks.py:638-646`) |
| — | FMP vs SEC EDGAR 결정 | **D** | `docs/sec_pipeline/decisions/001_*.md` — FMP Starter 미지원으로 SEC EDGAR 직접호출 대체. 의사결정 문서화됨(추적 가능) |

### 주의/누락 항목

1. **(B) Celery Beat 비활성** — `sync-sec-dirty-neo4j`, `check-new-filings` 모두 주석. 배치는 **수동 트리거만 가능**. SEC-PR-17 보고서는 Beat 설정을 약속했으나 코드는 OFF. (※ CLAUDE.md 버그 #28 "Beat schedule drift" 맥락과 연결 — DatabaseScheduler면 dict 무시됨)
2. **(B) Ticker 매칭률 3%** — 코드 결함 아님. 추출 프롬프트가 일반명사("third parties", "OEMs") 흡수 + TSMC/Samsung 등 비미국주식 미등록. 프롬프트 개선 + CompanyAlias 수동 등록 필요.
3. **(B) Gold Set 라벨 부족** — Precision 8.5%(목표 ≥70%). S&P500 배치 후 추가 라벨링 전제.
4. **(낮음) JNJ 특수문서** — Item 1 ≥ Item 1A 위치 역전 케이스 처리 로직 없음. `validators.py` 순서검증 완화 필요.
5. **테스트** — `services/sec_pipeline/tests.py` 빈 파일이나 `tests/unit/sec_pipeline/`에 24개 파일 존재(collector/extractor/validator/ticker_matcher/quality_checks). 커버리지는 실재.

### 결론
SEC Pipeline은 **설계 약속 거의 전건 구현**. 남은 것은 코드가 아니라 **① 자동 스케줄 활성화, ② 추출 프롬프트 품질, ③ Gold Set 라벨링**이라는 운영·데이터 과제.

---

## 3. Validation 상세

### 구현률: 백엔드 ~95% / 프론트 0% / 테스트 0% → **종합 ~75%**

백엔드(모델·배치·API·6 프리셋·LLM필터)는 거의 완전. **프론트엔드 전체 미구현**이 최대 갭.

### 기능별 상태

| 영역 | 기능 | 분류 | 근거 |
|------|------|------|------|
| 모델 | CompanyBenchmarkDelta / CategorySignal / PeerPreset / UserPeerPreference | **A** | `services/validation/models/*.py` (preset_key 확장 포함) |
| 배치 | Task 1~6 + Orchestrator chain | **A**(Task5만 **B**) | `tasks.py:23-178` — Task5(`update_peer_list_caches`)는 Task3에서 이미 갱신, 검증만 수행 |
| API | summary / metrics / leader-comparison / presets / peer-preference(POST·DELETE) / llm-filter | **A** | `api/views.py:63-692` (7개 엔드포인트 전건) |
| 프리셋 6종 | default / sector_all / size_peers / quality_top / lifecycle / thematic | **A** | `services/preset_generator.py:89-524` (thematic = GrowthStage×CapitalDNA, 463/503 종목) |
| 해석 | rule-based summary / metric / leader | **A** | `services/interpretation.py:12-128` |
| Compute-on-Read | CustomBenchmarkEngine(Redis 캐시) | **A** | `services/custom_benchmark_engine.py` |
| LLM 필터(Phase7) | 파서 + 실행엔진 | **A** | `services/llm_peer_filter.py:56-240` (Gemini Flash, Chain Sight 프로파일 필터 6+종) |
| 특수산업 | 금융/REIT 대체지표 | **B** | `category_signal_calculator.py:100-109` — `handling_mode='special'` 감지·gray 처리만. Efficiency Ratio 등 **대체 분석 미구현** |
| 마이그레이션 | 0001~0004 | **A** | preset_key 추가 + unique_together 변경 반영 |
| **프론트엔드** | FE-PR-1~7 (네비/신호등카드/지표차트/모바일Accordion/산업위치·대장주UI/Empty States) | **C** | 설계서(`validation_pr_prompts.md`)만 존재, **React/TS 코드 전무** |
| 테스트 | 배치·API 단위 테스트 | **C** | `services/validation/tests.py` 빈 파일 |
| 레거시 | 루트 `validation/` | **D** | `__pycache__`만, services로 이동 완료 |

### 주의/누락 항목

1. **(C) 프론트엔드 전면 미구현** — 최대 갭. 백엔드 7개 API는 준비됐으나 소비하는 UI 없음. FE-PR-1~7 설계만 존재.
2. **(B) 특수산업 대체지표** — 금융/REIT를 `special`로 판별하고 gray-out만 함. 설계가 약속한 대체 지표(Efficiency Ratio, ROIC 대체) 미산출.
3. **(검증 필요) LLM필터 ↔ Chain Sight 데이터 의존성** — `llm_peer_filter.py:107-113`이 `CompanyGrowthStage/CapitalDNA/SensitivityProfile`를 import. **Chain Sight 모델이 비어 있으면 필터 무동작**. 데이터 파이프라인 상태 미검증.
4. **(검증 필요) `seed_validation_data` 시딩** — `handling_mode='special'`(Banks/Insurance/REIT/Utilities) 시딩 command 존재 여부 미확정.
5. **고지문 미연동** — "과거 차트도 현재 peer 기준 계산" / "데이터 기준일" 표시. API에 데이터는 있으나 FE 미구현이라 노출 안 됨.

### task_done 대조
- `peer_phase6_thematic.md`(463/503 종목, 총 2,282 프리셋) ↔ `preset_generator.py:425-524` **로직 일치(~95%)**. 실제 DB 카운트는 읽기전용이라 미확인.
- `peer_phase7_llm_filter.md`(필터 종류·테스트 결과) ↔ `llm_peer_filter.py` **로직 일치(~98%)**. Gemini API 키 설정 전제.

### 결론
Validation은 **"머리(백엔드)는 완성, 몸(프론트)이 없는"** 상태. 백엔드 신뢰성은 높으나 **사용자에게 노출되는 경로가 0**이고, 테스트 부재로 배치 안정성 미검증.

---

## 4. News 상세

### 구현률: Phase A 100% / Phase B·C 미완 → **종합 ~70~75%**

### 기능별 상태

| Phase | 기능 | 분류 | 근거 |
|-------|------|------|------|
| **Intelligence Pipeline v3** | 수집(P1)/규칙엔진(P2)/LLM심층(P3)/ML라벨+Neo4j(P4)/ML학습+Shadow(P5)/LightGBM(P6) | **A** | `tasks.py`, `services/news_classifier.py`, `news_deep_analyzer.py`, `ml_label_collector.py`, `news_neo4j_sync.py`, `ml_production_manager.py`, `ml_weight_optimizer.py` |
| **Provider** | Finnhub/Marketaux/FMP/AlphaVantage + 카테고리(sector/sub_sector/custom) | **A** | `providers/*.py` + `NewsCollectionCategory` 모델 |
| **Keyword Detail** | API + 모델확장 + 2단매칭 + Gemini분석 + 캐시 | **A** | `api/views.py:676-852` (`GET /news/keyword-detail/`) |
| **Keyword Detail FE** | KeywordDetailSheet(BottomSheet v2) / DailyKeywordCard | **A** | `frontend/components/news/*.tsx` |
| **AI 뉴스 브리핑(Cold Start)** | reason필드 / MarketFeedService / market-feed API / 3단 Fallback / FE카드 | **A** | `keyword_extractor.py`, `market_feed.py`, `api/views.py:957-997`, `AINewsBriefingCard.tsx` |
| **모니터링 Phase A** | collection-logs / pipeline-health / ml-trend / llm-usage (4 API) | **A** | `api/views.py:1405-2080` (IsAdminUser, 캐시, KST) |
| **모니터링 Phase A FE** | PipelineStatusBar / CollectionStatsTable / MLModelCard / MLTrendChart / RecentErrorsList / LLMUsageSummary / NewsPipelineSubTab | **A** | `frontend/components/admin/news/*.tsx` |
| **모니터링 Phase B API** | task-timeline / neo4j-status / ml-rollback-preview / ml-rollback | **C** | `api/views.py` 검색결과 없음 |
| **모니터링 Phase B FE** | TaskTimelineChart / Neo4jStatusCard / MLCompareView | **B** | 컴포넌트는 존재하나 **뒷단 API 부재로 무동작** |
| **알림 Phase C 모델** | AlertLog (+ migration 0006) | **A** | `models.py` (TriggerType/Severity) + `migrations/0006_alertlog.py` |
| **알림 Phase C API/태스크** | alerts(GET) / alerts/{id}/resolve(POST) / check_pipeline_alerts | **C** | `api/views.py`·`tasks.py` 검색결과 없음 |
| **알림 Phase C FE** | AlertBadge / AlertList | **B** | UI만 존재, 데이터 미지원 |
| 지원서비스 | Aggregator/Deduplicator/SentimentNormalizer/StockInsights/InterestOptions | **A** | `services/*.py` |
| PersonalizedFeed | 관심사 기반 피드 | **B** | `personalized_feed.py:151` — UserInterest 모델/CRUD 미확정 |

### 주의/누락 항목

1. **(C) Phase B API 4종 전무** — `task-timeline / neo4j-status / ml-rollback-preview / ml-rollback`. **FE 컴포넌트는 완성**되어 있어 "UI는 보이나 ML 롤백·타임라인 무동작" 상태.
2. **(C) Phase C 알림 API·Celery 미구현** — `AlertLog` 모델·migration은 있으나 `alerts` CRUD API·`check_pipeline_alerts` 자동감지 태스크 없음 → **파이프라인 이상 자동 감지 불가**.
3. **(B) UserInterest 모델 미확정** — PersonalizedFeed가 의존. users 앱 확인 필요.
4. **(positive) `_log_collection()` 누락 우려는 해소** — collect/classify/analyze/sync/ml_labels 전 태스크에 로깅 호출 확인됨 → Phase A 대시보드 데이터 신뢰성 확보.

### task_done/완료선언 대조
- Phase A(4 API + Pipeline v3 P1~6) **완전 일치**.
- **Phase B·C는 설계서(`news_pipeline_monitoring_design.md`)가 약속했으나 백엔드 미구현** — UI 스켈레톤만 남아 "완료처럼 보이는" 함정.

### 결론
News는 **사용자 대면 기능(브리핑·키워드상세) + 코어 파이프라인은 완전 가동**. 갭은 **관리자용 고급 모니터링(Phase B)과 자동 알림(Phase C)** — 둘 다 FE는 있고 BE가 비어 있어 **"보이지만 안 되는" 위험**이 큼.

---

## 5. 종합 우선순위 (감사자 권고 — 정보 제공용, 실행 아님)

| 우선 | 앱 | 항목 | 성격 |
|------|----|------|------|
| P0 | News | Phase B/C 백엔드 API + `check_pipeline_alerts` 태스크 — **UI가 이미 있어 깨진 것처럼 보임** | 미구현 메우기 |
| P0 | Validation | FE-PR-1~7 — 백엔드 7 API가 소비처 없이 방치 | 미구현 메우기 |
| P1 | SEC | Celery Beat 활성화(동기화 5분 / 신규filing 월1회) | 자동화 연결 |
| P1 | SEC | 추출 프롬프트 개선(일반명사 필터) + CompanyAlias 시딩 → 매칭률 | 데이터 품질 |
| P2 | Validation | 특수산업 대체지표 + Chain Sight 데이터 의존성 검증 | 정합성 |
| P2 | 전 앱 | `services/*/tests.py` 테스트 작성(현재 대부분 빈 파일) | 검증 |
| P3 | 전 앱 | CLAUDE.md·설계서의 구버전 경로(`sec_pipeline/*` 등) → `services/*` 갱신 | 문서 부채 |

### 횡단 관찰 (반복 안티패턴)
> **"프론트 컴포넌트는 만들었는데 백엔드 API가 없다"** — Validation FE 전무(반대 방향), News Phase B·C(UI만 존재). 양쪽 모두 **계약(contract) 선행 없이 한쪽만 구현**되어 갭이 발생. `contracts/` 스펙 선작성 후 양단 동기화(Contract-Driven Development) 원칙이 이 영역에서 지켜지지 않았음.

---

*감사 종료. 본 보고서는 읽기 전용 산출물이며 어떤 코드도 변경하지 않았다.*
