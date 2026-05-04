# SEC Pipeline + Validation + News 설계 갭 감사

> **작성일**: 2026-05-05
> **방식**: 읽기 전용 — 코드 수정 없음
> **대상**:
> - `docs/sec_pipeline/` ↔ `sec_pipeline/`
> - `docs/first_validation_system/` ↔ `validation/`
> - `docs/news/` ↔ `news/`
> **분류 기준**:
> - **(A) 완전 구현** — 설계서의 핵심 항목이 코드/모델/API에 모두 반영됨
> - **(B) 부분 구현** — 일부 누락·약식 구현·후속 Phase 보류 명시
> - **(C) 미구현** — 설계서에 정의됐으나 코드 부재
> - **(D) 폐기/대체** — 설계서와 다른 결정으로 의도적 변경

---

## 앱별 요약 (구현률)

| 앱 | 핵심 항목 수 | A 완전 | B 부분 | C 미구현 | D 폐기/대체 | 구현률 (A+D) |
|---|---:|---:|---:|---:|---:|---:|
| sec_pipeline | 11 | 9 | 1 | 1 | 1 (FMP→SEC) | **91%** |
| validation | 14 | 12 | 2 | 0 | 0 | **86%** |
| news (모니터링) | 13 | 11 | 1 | 1 | 0 | **85%** |
| news (키워드 상세) | 4 | 4 | 0 | 0 | 0 | **100%** |

> 구현률은 "A + D" / 전체. 부분 구현(B)과 미구현(C)은 분자에서 제외.

### 핵심 결론

1. **SEC Pipeline (Phase 1~3, 17 PR)** — 설계서 17 PR이 모두 task_done에 기록됨. 단 `decisions/001`로 FMP 메타데이터 → SEC EDGAR로 의도적 대체. Celery Beat 등록은 **주석 상태**(`tasks.py:558-566`)로 자동 실행 미연동(B).
2. **Validation Phase 1~5 + Phase 6~7** — Phase 1~7까지 task_done이 있으며 Peer Phase 6 thematic + Phase 7 LLM filter API 모두 구현됨. 다만 Phase 6 설계서가 "LLM 사업모델 태깅 → theme_tags"였으나 실제 구현은 **Chain Sight DNA(GrowthStage × CapitalDNA) 교차 클러스터링**으로 대체(D 사례, 의도적). 설계서의 LLM 태깅 + theme_tags는 미구현(C 후보).
3. **News 모니터링 대시보드 (Phase A/B/C)** — 백엔드 API 13개가 모두 `news/api/views.py`에 구현됨. Phase C `check_pipeline_alerts` 태스크도 등록(`tasks.py:1101`). 단 설계서 §11 선행 작업 `_log_collection()` 커버리지 보강은 적용 완료.
4. **News 키워드 상세** — `keyword_detail` action + `search_terms_en` 프롬프트 확장 모두 적용됨. v2(가로 스크롤 Strip)는 프론트엔드 작업이므로 본 감사 범위 외.

---

## SEC Pipeline 상세

### 설계 ↔ 구현 매핑

| # | 설계 항목 | 구현 위치 | 상태 |
|---|----------|----------|:---:|
| 1 | 8개 Django 모델 (RawDocumentStore ~ PipelineIntelligenceReport) | `sec_pipeline/models.py:15-388` | **A** |
| 2 | SEC EDGAR 수집기 (메타데이터+HTML+섹션추출) | `sec_pipeline/collector.py` (373줄) | **A** |
| 3 | 섹션 사후 검증 (순서/heading/길이) | `sec_pipeline/validators.py` (128줄) | **A** |
| 4 | Track A: Supply Chain 추출 + 검증 | `extractor.py`, `validator_track_a.py`, `prompts.py` | **A** |
| 5 | Track B: Business Model 5개 필드 분류 | `keywords_track_b.py`, `validator_track_b.py`, `prompts.py` | **A** |
| 6 | Ticker 매칭 (alias→exact→fuzzy) + 큐 적재 | `ticker_matcher.py` (210줄) + `signals.py` | **A** |
| 7 | Neo4j 동기화 (DELETE+CREATE dynamic type) | `tasks.py:337-452` `sync_dirty_to_neo4j` | **A** |
| 8 | Quality Checks 7개 + 대시보드 통계 | `quality_checks.py` (165줄), `views.py:14-25` | **A** |
| 9 | Pipeline Intelligence Report (5차원 + Gemini) | `intelligence.py` (223줄), `tasks.py:500-505` | **A** |
| 10 | On-demand filing API (200/202) | `views.py:28-46`, `on_demand.py`, `urls.py:8` | **A** |
| 11 | E2E chord (collect→sync→quality→intelligence) | `tasks.py:508-555` `run_batch_and_report` | **A** |

### 의사결정 / 폐기 사례

- **D-1**: FMP `sec-filings` 미지원 → SEC EDGAR submissions API 직접 호출. `docs/sec_pipeline/decisions/001_fmp_vs_sec_edgar_metadata.md`에 명시. `collector.py`에서 SEC EDGAR만 호출. 의도적 대체로 분류.
- **B-1 (운영 갭)**: `tasks.py:558-566`의 Celery Beat 스케줄(`sync-sec-dirty-neo4j` 5분마다, `check-new-filings` 매월 1일 06시)은 **주석 처리만 되어 있고 DB/celery_beat_schedule 등록 부재**. CLAUDE.md `버그 #28 (Beat schedule drift)` 패턴과 일치 — DatabaseScheduler 사용 시 dict는 무시되므로 `PeriodicTask.objects.create(...)` 등록 필요. 설계서 SEC-PR-17(`task_done/sec_pr_17_e2e.md`)에서도 "주석 상태"로 기록되어 인지된 갭이지만 미해결.

### 데이터 검증 부재 항목 (운영 KPI)

| 설계서 KPI | 현황 |
|---|---|
| 매칭률 30% 목표 | 첫 배치 2.7%(critical) — 비미국 주식 미등록 원인 (intelligence report). `CompanyAlias` 0건 그대로. |
| S&P 500 전체 배치 | 15종목 데모만, 503종목 배치 미실행 (Gemini RPD 제한 회피) |
| Gold Set 라벨 보완 | `fixtures/gold_set.json` 존재. precision/recall 재평가 보고 부재 |
| JNJ Item 순서 검증 완화 | 설계서 향후 과제로 명시, 미수정 |

### 분류 합계

- A: 9 / B: 1 (Beat 미등록) / C: 1 (S&P 500 전체 배치 미실행) / D: 1 (FMP→SEC 대체)

---

## Validation 상세

### 설계 ↔ 구현 매핑

#### Phase 1 (BE-PR-1~10): 핵심 파이프라인

| # | 설계 항목 | 구현 위치 | 상태 |
|---|----------|----------|:---:|
| 1 | DB 모델 9종 (CompanyMetricSnapshot, PeerListCache, CategorySignal, CompanyBenchmarkDelta, IndustryClassification.handling_mode, …) | `validation/models/`, `metrics/models/` | **A** |
| 2 | MetricDefinition 34개 지표 + handling_mode 시드 | `validation/management/commands/` (existence 확인됨) | **A** |
| 3 | Celery 6 Task chain (Task 1~6) | `validation/tasks.py:22-160` | **A** |
| 4 | Peer 선정 (industry+size bucket → industry → sector fallback) | `services/benchmark_calculator.py` (345줄) | **A** |
| 5 | value_status 5단계 (normal/missing/not_applicable/unstable/low_confidence) | `services/metric_calculator.py` (459줄) | **A** |
| 6 | category_signal (gray 포함 4종) + 균등 가중 percentile 평균 | `services/category_signal_calculator.py` (192줄) | **A** |
| 7 | 3개 API: summary, metrics, leader-comparison | `api/views.py:52-418`, `api/urls.py:8-10` | **A** |
| 8 | rule-based 해석 텍스트 (한줄 요약 + 지표 해석 + 리더 요약) | `services/interpretation.py` (121줄) | **A** |
| 9 | Empty State (S&P 500 외, 데이터 미준비) | `api/views.py:62-85` | **A** |
| 10 | 카테고리별 lazy load (`?category=all|single`) | `api/views.py:182-196` | **A** |

#### Phase 4~5: Peer 프리셋 + 커스텀 (Compute-on-Read)

| # | 설계 항목 | 구현 위치 | 상태 |
|---|----------|----------|:---:|
| 11 | 6종 프리셋 (default, sector_all, size_peers, quality_top, lifecycle, thematic) | `services/preset_generator.py` (479줄) | **A** |
| 12 | UserPeerPreference (preset/custom mode) + 커스텀 Compute-on-Read 엔진 | `models/peer_preset.py`, `services/custom_benchmark_engine.py` | **A** |
| 13 | API: presets, peer-preference (POST/DELETE) | `api/views.py:421-492`, `urls.py:11-12` | **A** |

#### Phase 6 (Thematic): 사업모델 LLM 태깅 → 클러스터링

| 설계서 (validation_peer_phase6_7.md) | 실제 구현 | 분류 |
|---|---|:---:|
| Step 1: Gemini 사업모델 태깅 → `CompanyNarrativeTag.theme_tags` (subscription_saas, platform_marketplace, …) | **CompanyNarrativeTag 미사용** | **C** (해당 단계) |
| Step 2: 같은 태그 그룹핑 → 5개+ 그룹만 활성 | **GrowthStage × CapitalDNA 교차 클러스터링**으로 대체 | **D** (대체) |
| Step 3: PeerPreset(`thematic`) 생성 | 463/503 종목, 2,282건 — `task_done/peer_phase6_thematic.md` | **A** (결과만) |

> Phase 6 설계서는 LLM 사업모델 태깅 → theme_tags가 1차였으나, `task_done/peer_phase6_thematic.md`에서 "GrowthStage × CapitalDNA 교차 조합 → 섹터 횡단 DNA 유사 클러스터"로 의사결정 변경. Chain Sight DNA가 선행 채워졌고 LLM 비용 회피 가능. **결과는 동일한 thematic preset key**라 사용자 영향은 없음. → **D(의도적 대체)** + 부분적 C(설계서 LLM 태깅 단계 미실행).

#### Phase 7: LLM 대화형 Peer 조정

| # | 설계 항목 | 구현 위치 | 상태 |
|---|----------|----------|:---:|
| 14 | POST `/llm-filter/` (자연어 → 구조화 필터 → 결과) | `api/views.py:495-558`, `services/llm_peer_filter.py` (264줄) | **A** |

> Phase 7은 설계서에서 `peer-filter/` 엔드포인트로 명시되었으나 실제 구현은 `llm-filter/`로 path만 변경. 동작 동일. 분류상 A.

### 부분 구현 / 갭

- **B-1**: 설계서 §3.3 차트 구현 가이드(MetricBarChart Recharts ComposedChart + ErrorBar)는 프론트엔드 영역이므로 본 감사 범위 외이지만, 백엔드 응답에 `peer_p25/p75/median` 모두 포함되어 클라이언트 측 구현은 가능.
- **B-2**: 설계서 §8.2 Phase 2 LLM 캐싱 (`validation_ai_cache` 테이블, company_summary/metric_interpretation/leader_analysis)은 **명시적 보류**. 현재 모든 텍스트는 rule-based(`interpretation.py`)로 생성. 설계서가 "Phase 1 결과 확인 후 결정"이라고 했으므로 보류 자체가 의도된 상태. C로 분류하지 않고 B(부분).

### 분류 합계

- A: 12 / B: 2 (LLM 캐싱 보류, Phase 6 LLM 태깅 회피) / C: 0 / D: 0
- 단, Phase 6 LLM 태깅 단계만 따로 보면 D(대체)로 별도 카운트 가능

---

## News 상세

### 1) News 모니터링 대시보드 (`news_pipeline_monitoring_design.md` v1.1)

#### 설계 ↔ 구현 매핑

| Phase | # | 설계 항목 | 구현 위치 | 상태 |
|---|---|----------|----------|:---:|
| 0 | 1 | `_log_collection()` 커버리지 보강 (collect_daily_news, market, category, classifier, deep, neo4j 6태스크) | `news/tasks.py:178, 220, 454, 500, 543, 621` | **A** |
| A | 2 | `GET /collection-logs/` (provider별 + daily 집계, KST) | `views.py:1314-1422` | **A** |
| A | 3 | `GET /pipeline-health/` (6 Phase + force_refresh) | `views.py:1424-1676` (`_determine_status` 평일 전용 처리 포함) | **A** |
| A | 4 | `GET /ml-trend/` (12주 F1) | `views.py:1678-1756` | **A** |
| A | 5 | `GET /llm-usage/` (Phase 3 미추적 경고) | `views.py:1758-1876` | **A** |
| B | 6 | `GET /task-timeline/?hours=24` | `views.py:1878-1937` | **A** |
| B | 7 | `GET /neo4j-status/` | `views.py:1939-1998` | **A** |
| B | 8 | `GET /ml-rollback-preview/` | `views.py:2000-2038` | **A** |
| B | 9 | `POST /ml-rollback/` (`{"confirm":true}` 필수) | `views.py:2040-2083` | **A** |
| C | 10 | `AlertLog` 모델 (Severity TextChoices + 7 TriggerType) | `news/models.py:684-727` | **A** |
| C | 11 | `GET /alerts/` (resolved/severity 필터) | `views.py:2085-2147` | **A** |
| C | 12 | `POST /alerts/{id}/resolve/` | `views.py:2149+` | **A** |
| C | 13 | `check_pipeline_alerts` Celery 태스크 (30분 주기) | `news/tasks.py:1101-` | **A** (구현됨, Beat 등록 별도 확인 필요) |

> 설계서 §3 "이미 있는 API"로 분류된 ml-status / ml-weekly-report / ml-shadow-report / ml-lightgbm-readiness / daily-keywords는 본 감사 대상 외(이미 구현 전제).

#### 부분 구현

- **B-1**: 설계서 §10 "절대 하지 말 것"의 **`MLModelHistory` 필드 변경 금지**는 준수됨. 그러나 설계서 §3.4 "LLM 토큰 추적은 Phase B에서 NewsDeepAnalyzer에 토큰 로깅을 추가한 뒤 통합 API로 확장"은 **현재 미적용** (`/llm-usage/` 응답에 deep_analysis 토큰 미포함, "coverage_warning" 필드만 노출). Phase B 설계 의도대로 키워드 추출 토큰만 반영하므로 의도된 상태. C가 아닌 B로 분류.

#### 미구현

- **C-1**: 설계서 §6.2 Slack webhook + 이메일 알림 채널은 "선택"으로 명시되었으나 코드 부재. AlertLog DB만 적재됨. 설계서가 선택적이라고 표기하므로 C로 분류하되 우선순위 낮음.

### 2) 키워드 상세 (`news_keyword_detail_plan.md` v1)

| # | 설계 항목 | 구현 위치 | 상태 |
|---|----------|----------|:---:|
| 1 | `keyword_extractor.py`에 `search_terms_en` 프롬프트 확장 | `services/keyword_extractor.py:43-44, 241, 256-258, 306, 321` | **A** |
| 2 | `GET /keyword-detail/?date=&index=` API | `views.py:640-815` | **A** |
| 3 | Redis 캐시 키 `news:keyword_detail:{date}:{index}:{updated_at_epoch}` | `views.py:697` | **A** |
| 4 | Gemini 실패 시 `analysis: null` 반환 + 기사 목록 유지 | `views.py:_generate_keyword_analysis` (776+) | **A** |

### 3) 키워드 상세 BottomSheet v2 (`keyword_detail_bottomsheet_v2.md`)

> 본 문서는 프론트엔드 전용 (`frontend/components/news/KeywordDetailSheet.tsx` 등)으로 본 감사 범위 외. 본 보고서에서는 카운트하지 않음.

### 분류 합계 (모니터링 + 키워드 상세 17개)

- A: 15 / B: 1 / C: 1 / D: 0

---

## 횡단 리스크 및 권고

### 즉시 조치 필요 (운영 영향)

1. **SEC Pipeline Beat 미등록 (B-1)** — `tasks.py:558-566` 주석을 DB `PeerListCache`에 직접 등록 (`PeriodicTask.objects.create`). CLAUDE.md 버그 #28 패턴 적용. 미적용 시 dirty 적체 / 신규 filing 감지 미작동. → @infra 담당.

2. **CompanyAlias 0건 (SEC 매칭률 2.7%)** — TSMC→TSM, Samsung 등 비미국 alias 시드 미투입. `task_done/sec_pipeline_complete_summary.md` "향후 과제 5"로 인지됨. 매칭률이 목표 30%에 한참 미달. → @backend 시드 작업.

3. **News Slack/이메일 알림 채널 (C-1)** — AlertLog만 적재되고 채널 송출 없음. 야간 장애 발견 지연 가능성. 설계서가 "선택"으로 표기했으나 운영 단계에서 재평가 필요.

### 설계서 vs 구현 정합성 정리 권고

4. **Validation Phase 6 설계서 vs 구현 차이**: `validation_peer_phase6_7.md`는 LLM 사업모델 태깅 기반인데, 실제 구현은 Chain Sight DNA(GrowthStage × CapitalDNA) 기반. **설계서에 의사결정 노트(D-기록) 반영 권고** — `docs/first_validation_system/validation_peer_phase6_7.md` 상단에 "구현 시 Chain Sight DNA로 대체. theme_tags 태깅은 Phase 6.5로 보류" 라벨 추가.

5. **SEC Pipeline 의사결정 보존**: `decisions/001_fmp_vs_sec_edgar_metadata.md`처럼 단일 결정만 기록됨. 향후 Track B 프롬프트 변경, JNJ 검증 완화 등 결정도 같은 디렉토리에 누적 권고.

### 후속 검증 필요

6. **News `check_pipeline_alerts` Beat 등록 확인** — 코드는 있으나 `django_celery_beat.PeriodicTask`에 등록되었는지는 본 감사에서 확인 못 함. CLAUDE.md 버그 #28 적용 여부 점검 필요.

7. **Validation Phase 1 핵심 KPI 수집 부재** — 설계서가 명시한 Empty State Case 1~5의 실제 발생률, S&P 500 외 종목 접근 시도 비율 등 운영 데이터 없음. → @qa 모니터링 추가 권고.

---

## 부록: 핵심 산출물 카운트

### SEC Pipeline
- 모델 8개 / 서비스·유틸 모듈 16개 / Celery 태스크 6개 / API 엔드포인트 2개
- task_done 보고서 16건 (PR 1~17 + complete_summary)

### Validation
- 모델 5개 (validation/) + 의존 모델 (metrics/) / 서비스 9개 / Celery 태스크 7개 / API 엔드포인트 6개
- task_done 보고서 2건 (Phase 6 + Phase 7), 본 감사 시점 Phase 1~5 별도 task_done은 `docs/first_validation_system/`에 부재 (설계서 자체에 통합)

### News
- 모델 7개+ (NewsArticle, NewsEntity, …, MLModelHistory, NewsCollectionCategory, NewsCollectionLog, AlertLog) / 서비스 17개 / Celery 태스크 약 30개 / API 엔드포인트 27개+
- 본 감사 범위 모니터링 신규 API 13개 + 키워드 상세 1개 모두 구현 확인
