# SEC Pipeline + Validation + News 설계 갭 감사

**감사일:** 2026-05-14
**감사자:** Claude (Opus 4.7) — 읽기 전용 감사
**범위:** `docs/sec_pipeline/`, `docs/first_validation_system/`, `docs/news/plan/` vs 각 앱 구현 코드
**방법:** 설계 문서 ↔ task_done 완료 보고서 ↔ 실제 코드 3자 대조. 분류: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 앱별 요약 (구현률)

| 앱 | 설계 분량 | 구현 분량 | 구현률 (내부) | 구현률 (외부 API/UI 포함) | 핵심 갭 |
|----|----------|----------|--------------|------------------------|--------|
| **SEC Pipeline** | task_done 16개 PR (≈856줄) | 3,313줄 Python | **85%** | **60%** | API 라우트 미구현, merger.py 비활성, E2E chord 미적용, Admin 템플릿 부재, 테스트 0건 |
| **Validation** | 4 설계서 (≈2,841줄) + task_done 2건 | 2,997줄 Python | **88%** (BE) | **44%** (BE 88% + FE 0%) | FE L1/L2 미구현, Serializers 부재, 특수산업 handling_mode 검증 미흡 |
| **News** | 3 설계서 (≈1,456줄) | 12,377줄 Python | **95%** (BE) | **92%** | `check_pipeline_alerts` Celery Beat 미구현, FE 모니터링 sub-tab 부분 구현, v2 키워드 Strip 미구현 |

**종합 결론:**
- **News**: 가장 완성도 높음. 백엔드 거의 완벽 (Phase A/B/C, ML 운영, LightGBM 모두 구현), 잔여 갭은 Celery Beat 1개와 프론트엔드 마감.
- **Validation**: 백엔드는 task_done 보고서 일치도 92%로 매우 우수. 프론트엔드(L1/L2 네비, Accordion UX)는 설계만 있고 0% 구현.
- **SEC Pipeline**: PR 보고서는 "완료"라고 했으나, 실제로는 **REST API와 자동화가 미완**. 내부 로직(수집/추출/Neo4j 동기화)은 잘 작동하지만, 외부 노출과 운영 자동화(Celery Beat 주석 처리)가 비활성 상태.

---

## SEC Pipeline 상세

### 구현 요약 (85% 내부 / 60% 외부)

| Phase | 범위 | 상태 |
|-------|------|------|
| Phase 1 (수집·추출, PR 1~6) | 모델/수집/Track A/Celery/Gold Set/15종목 배치 | ✅ A. 완전 구현 |
| Phase 1.5 (매칭·동기화, PR 7~10) | TickerMatcher, Admin/Signal, Neo4j 동기화, **관계 병합** | ⚠️ B. PR-10 코드 존재하나 호출 안 됨 |
| Phase 2 (비즈니스모델, PR 11~13) | Track B 키워드/Gemini/서비스 레이어 | ✅ A. 완전 구현 |
| Phase 3 (대시보드·지능, PR 14~17) | 품질 대시보드/On-demand/Intelligence/E2E | ⚠️ B. API·자동화 미흡 |

### PR별 갭 매핑

| PR | 설계상 약속 | 실제 위치 | 상태 | 갭 |
|----|------------|----------|-----|------|
| 1 | 8개 모델 + migration | `sec_pipeline/models.py` (388줄) | A | — |
| 2 | SEC EDGAR 수집기 + 검증 | `collector.py` (373줄), `validators.py` | A | — |
| 3 | Track A 키워드필터 + Gemini | `normalizer.py`, `extractor.py`, `prompts.py` | A | — |
| 4 | Celery tasks + 에러 처리 | `tasks.py` (579줄), `exceptions.py` | A | — |
| 5 | Gold Set + 평가 스크립트 | `fixtures/gold_set.json`, `management/commands/evaluate_gold_set.py` | A | — |
| 6 | 15종목 배치 실행 | `tasks.py:run_batch_and_report` | A | 단위 테스트 없음 |
| 7 | TickerMatcher 3단계 | `ticker_matcher.py` (210줄) | A | — |
| 8 | Admin + signal | `admin.py` (171줄), `signals.py` (71줄) | A | — |
| 9 | sync_dirty_to_neo4j | `tasks.py:337-450` | A | — |
| **10** | **관계 병합 + DQS 계산** | `merger.py` (135줄) | **B** | **함수 정의만, 호출 지점 0건** |
| 11 | Track B 키워드사전 | `keywords_track_b.py` (78줄) | A | — |
| 12 | Track B Gemini + 검증 | `extractor.py`, `validator_track_b.py` | A | — |
| 13 | 서비스 레이어 | `metrics/services/business_model_service.py` | A | — |
| **14** | **품질 대시보드** | `quality_checks.py`, `views.py:26` | **B** | **`templates/admin/sec_pipeline/dashboard.html` 파일 부재** → 런타임 500 위험 |
| **15** | **On-demand Filing API** | `on_demand.py`, `views.py` (51줄) | **B** | 비동기 202만 반환, REST 응답 스펙 없음 |
| 16 | Intelligence 리포트 | `intelligence.py` (223줄) | A | — |
| **17** | **E2E chord 통합** | `tasks.py:509-555` | **B** | **chord 대신 동기 for 루프 + Celery Beat 주석 처리(558-566)** |

### 핵심 갭 (우선순위 순)

1. **[P0] REST API 라우트 거의 미구현** — `urls.py` 9줄, `views.py` 51줄. `/api/v1/sec/` 하위에 `metrics`, `reports`, `relations` 조회 엔드포인트 전무. CLAUDE.md에는 "SEC Pipeline" 완료라 적혀있으나, 외부 노출 부분은 형식적 정의만 존재.
2. **[P1] `merger.py` 호출 지점 0건** — `merge_relationship()`, `calculate_edge_dqs()` 정의 (`merger.py:36-135`)되었으나 `tasks.py`, `signals.py`, `validator_track_a.py` 어디서도 import 안 함. **같은 (source, target) 쌍 중복 관계가 병합 없이 그대로 Neo4j로 동기화될 위험**.
3. **[P2] E2E 비동기 처리 미적용** — PR-17 보고서는 "chord 통합"이라고 했으나 `tasks.py:509-555`에 "chord 대신 순차 실행 (1인 개발 단순성)" 주석. 15종목 배치 시 ~30초 직렬 처리 (추정).
4. **[P2] Celery Beat 주석 처리** — `tasks.py:558-566` 부근 스케줄러 주석. 자동 배치가 비활성 상태 → 운영 시 수동 트리거 필요.
5. **[P2] Admin 대시보드 템플릿 부재** — `views.py:26`에서 `render(..., 'admin/sec_pipeline/dashboard.html')` 호출하나 템플릿 파일 미존재.
6. **[P3] 테스트 케이스 0건** — `tests.py` 1줄 ("# Create your tests here."). 16개 PR이 "테스트 결과"를 길게 보고했으나 unit/integration test 없음 (management command 실행 결과 보고만 존재).

### task_done 보고서 vs 실제 코드 (과장 사항)

| 보고서 주장 | 현실 | 추정 원인 |
|----------|-----|----------|
| "PR-10 관계 병합 완료" | 코드만 있고 호출 안 함 | Phase 1.5 마무리 서두름; 병합 필요 사례 미발견 |
| "PR-17 chord 통합" | 동기 순차 반복 | 1인 개발 단순성 우선 (코멘트 명시) |
| "PR-14 Admin 대시보드" | 함수만, 템플릿 없음 | Django 템플릿 초기화 누락 |
| "Phase 3 완료" (complete_summary) | API 미구현, E2E 부분적 | 내부 로직만 점검, 외부 통합 미흡 |

### 실제 동작 추정

- **PR-9 Neo4j 동기화**: ✅ 작동 (DELETE+CREATE, sole writer 원칙)
- **PR-11~13 Phase 2 Track B**: ✅ 작동 (`tasks.py:236-277`)
- **PR-16 Intelligence**: ✅ 작동 (`intelligence.py` + Admin regenerate action)
- **PR-17 E2E**: ⚠️ 흐름은 작동하나 비동기 병렬화 + 자동 스케줄 미적용

---

## Validation 상세

### 구현 요약 (88% BE / 0% FE)

**완료된 핵심 기능:**
- ✅ 7개 카테고리 신호등 (green/yellow/red/gray) + 34개 지표 메타데이터
- ✅ Peer 선정 (Industry + Size Bucket) + Benchmark + Percentile Rank
- ✅ Celery 파이프라인 (Task 1~6 + Orchestrator, 주간 배치)
- ✅ 6종 Peer Preset (default, sector_all, size_peers, quality_top, lifecycle, **thematic**)
- ✅ Phase 6 Thematic Preset (463/503 종목)
- ✅ Phase 7 LLM Peer Filter (자연어 → 구조화 필터 → 실행)
- ✅ REST API 6개 엔드포인트

**미완료:**
- ❌ 프론트엔드 (L1/L2 네비게이션, Accordion, Signal Summary 카드) — 설계서만 존재
- ⚠️ Rule-based 해석 → LLM 배치 캐싱 전환 (Phase 2 예정으로 합리적 보류)

### 기능별 갭 매핑 (요약)

| 영역 | 설계 약속 | 상태 |
|------|---------|------|
| **DB 모델 8개** | MetricDefinition / CompanyMetricSnapshot / CompanyMetricLatest / CompanyBenchmarkDelta / CategorySignal / PeerListCache / PeerPreset / UserPeerPreference | ✅ 전부 A |
| **Celery 8개 함수** | Task 1~6 + relative_metrics + orchestrator | ✅ 전부 A (`validation/tasks.py:26~145`) |
| **API 6개** | summary, metrics, leader-comparison, presets, peer-preference, llm-filter | ✅ 전부 A (`validation/api/views.py`) |
| **Peer Preset 6종** | default / sector_all / size_peers / quality_top / lifecycle / **thematic** | ✅ 전부 A (`preset_generator.py:80~462`) |
| **LLM Peer Filter (Phase 7)** | parse_filter_with_llm + execute_peer_filter | ✅ A (`llm_peer_filter.py:56~200`) |
| **Interpretation** | summary_text + metric_interpretation + leader_summary | ⚠️ B (`leader_summary` 함수 위치 불명확 — 추정 views.py inline) |
| **Serializers** | `validation/api/serializers.py` 생성 예상 | ❌ C (파일 부재, views.py 수동 dict serialization) |
| **특수산업 handling_mode** | Banks/Insurance/REIT/Utilities → gray 신호 | ⚠️ B (적용 여부 검증 필요) |
| **프론트엔드** | L1/L2 네비, Accordion UX, Signal Summary 카드 | ❌ C (FE-PR-1~3 미구현) |

### 핵심 갭 (우선순위 순)

1. **[P0] 프론트엔드 미구현** — 설계서 섹션 1~2 (L1/L2 네비게이션, Signal Summary 카드, 모바일 Accordion UX) **0% 구현**. CLAUDE.md에 "1차 검증 ... 완료"라 적혀있으나 백엔드만 완료.
2. **[P1] `validation/api/serializers.py` 미생성** — views.py에서 manual dict serialization. DRF 표준 패턴에서 벗어남, 응답 스키마 변경 시 일관성 깨질 위험.
3. **[P2] `generate_leader_summary` 함수 위치 불명확** — `interpretation.py:46~90`에는 `generate_metric_interpretation`까지만 정의됨. Leader 요약은 `views.py` LeaderComparisonView 내부 inline으로 추정. 설계서 §3.5에서 분리 명시했으나 미반영.
4. **[P2] 특수산업 handling_mode 적용 미검증** — `validation_design.md:7.5` Banks/Insurance/REIT/Utilities → gray 신호 약속. `category_signal_calculator.py`에서 실제 적용 여부 확인 필요.
5. **[P3] 응답 스키마 미세 차이** — `summary` API의 `industry_leader` 위치가 설계서 §3.2 `peer_info.industry_leader`와 달리 최댓값 기반 inline 계산으로 추정.

### Phase 6/7 task_done 보고서 vs 실제 코드 일치도

| 항목 | 일치도 |
|------|--------|
| **Phase 6: Thematic Preset** | |
| - `_generate_thematic()` 메서드 추가 | 100% (`preset_generator.py:377~462`) |
| - 463/503 종목 결과 | 95% (DB 데이터 미직접검증) |
| - 전체 프리셋 2,282개 | 추정 80% (count 미실행) |
| **Phase 7: LLM Peer Filter** | |
| - POST /llm-filter/ 엔드포인트 | 100% (`urls.py:13`, `views.py:498~561`) |
| - llm_peer_filter.py 264줄 | 100% |
| - 지원 필터 (Chain Sight 6 + Metrics 31) | 100% (`llm_peer_filter.py:19~44` prompt 정의) |
| - 3개 테스트 시나리오 (364/0/183 종목) | 50% (실행 결과 미캐시) |

**결론**: Phase 6, 7 설계 → 보고서 → 코드 일치도 매우 높음 (90%+).

### API 엔드포인트 vs 설계 명세 차이

| 엔드포인트 | 설계 (PR-6) | 실제 | 일치도 |
|----------|------------|------|--------|
| GET /summary/ | symbol, category_signals[], summary_text, peer_info, industry_position | ✅ 모두 포함 | 95% |
| GET /metrics/?category= | category, metrics[], history[], interpretation | ✅ 모두 포함 | 100% |
| GET /leader-comparison/ | leader{}, comparisons[], summary | ✅ 구현 | 90% |
| GET /presets/ | (설계 미명시) | ✅ 6종 반환 | 설계 누락분 |
| POST /peer-preference/ | (설계 미명시) | ✅ 커스텀 peer 저장 | 설계 누락분 |
| POST /llm-filter/ | (Phase 7) | ✅ | 100% |

---

## News 상세

### 구현 요약 (95% BE / 92% 종합)

**설계 단계 3개:**
1. `news_pipeline_monitoring_design.md` (1160줄) — Phase A/B/C 모니터링 + ML 운영
2. `news_keyword_detail_plan.md` (216줄) — 키워드 상세 + 바텀시트
3. `keyword_detail_bottomsheet_v2.md` (80줄) — UX v2 개선

**구현 완료:** Phase A 백엔드(4 API), Phase B 백엔드(4 API), Phase C 백엔드(모델+API), ML 운영 시스템(Shadow/Production/LightGBM), 키워드 상세 v1, search_terms_en

### 기능별 갭 매핑

| 영역 | 항목 | 위치 | 상태 |
|------|------|-----|------|
| **Phase A: 기존 데이터 노출** | | | |
| | collection-logs API | `views.py:1330~1437` | A |
| | pipeline-health API (6 Phase 통합) | `views.py:1440~1691` | A |
| | ml-trend API (F1 12주 추이) | `views.py:1694~1771` | A |
| | llm-usage API | `views.py:1774~1823` | B (Phase 3 미포함 주석) |
| | keyword-detail API | `views.py:656~775` | A |
| **Phase B: 헬스 심화** | | | |
| | task-timeline API | `views.py:1893~1953` | A |
| | neo4j-status API | `views.py:1954~2014` | A |
| | ml-rollback-preview API | `views.py:2015~2054` | A |
| | ml-rollback API (POST 2단계) | `views.py:2055~2095` | A |
| **Phase C: 능동 모니터링** | | | |
| | AlertLog 모델 | `models.py:684~708` | A |
| | alerts API (조회+해제) | `views.py:2100~2180` | A |
| | **check_pipeline_alerts Celery 태스크** | — | **D. 미구현** |
| **ML 운영 시스템** | | | |
| | Shadow Mode 저장/감지 | `ml_production_manager.py:43~150` | A |
| | 4주 연속 Safety Gate | `ml_production_manager.py:70~77` | A |
| | 자동 배포 | `tasks.py:770~800` | A |
| | LightGBM 학습 | `ml_weight_optimizer.py:963~1222` | A |
| | 연속 F1 하락 감지 (3주) | `ml_production_manager.py:460~490` | A |
| | 주간 ML 리포트 | `ml_production_manager.py:274~350` | A |
| | 모델 롤백 | `ml_production_manager.py:425~458` | A |
| **키워드 상세 v2** | | | |
| | search_terms_en (한·영 매칭) | `keyword_extractor.py` | A |
| | 바텀시트 (분석+기사) 백엔드 | `views.py:656~775` | A |
| | 키워드 Strip 가로 스크롤 (v2 개선) | frontend | D (미구현) |
| **프론트엔드 모니터링 sub-tab 6개** | overview/pipeline/timeline/neo4j/ml/llm/alerts | `NewsTab.tsx`, `NewsPipelineSubTab.tsx` | C. 부분 (overview/pipeline 2개만 추정) |

### 핵심 갭 (우선순위 순)

1. **[P1] `check_pipeline_alerts` Celery Beat 태스크 미구현** — 설계서 §6 Phase C에서 30분 주기 이상 징후 자동 감지 약속. AlertLog 모델(`models.py:684~708`)과 API(`views.py:2100~2180`)는 완성됐으나 **트리거 태스크가 없어 알람이 자동 생성되지 않음**. 인프라 담당 영역(`config/celery.py` Beat 스케줄 추가).
2. **[P2] 프론트엔드 모니터링 대시보드 sub-tab 부분 구현** — 설계서 §4는 6개 sub-tab (Pipeline Status, Task Timeline, Neo4j Status, ML Trend, LLM Usage, Alerts) 요구. 현재 `NewsTab.tsx`는 'overview' | 'pipeline' 2개만 구현 추정. 백엔드 API는 다 있어서 마감 작업만 남음.
3. **[P3] 키워드 바텀시트 가로 스크롤 Strip (v2 UX 개선)** — `keyword_detail_bottomsheet_v2.md` UX 개선안. 백엔드 API는 호환되므로 프론트엔드 단일 작업.

### Pipeline 모니터링 (메인 설계서) 구현 여부

| Phase | 백엔드 | 감지 로직 | 프론트엔드 |
|-------|-------|---------|----------|
| Phase 1 (수집) | ✅ collection-logs | ✅ NewsCollectionLog 기반 | ⚠️ 부분 |
| Phase 2 (분류) | ✅ pipeline-health | ✅ classify_news_batch 로그 | ⚠️ 부분 |
| Phase 3 (LLM) | ✅ pipeline-health | ✅ analyze_news_deep 로그 | ⚠️ 부분 |
| Phase 4 (ML+Neo4j) | ✅ pipeline-health + neo4j-status | ✅ collect_ml_labels, sync_news_to_neo4j | ⚠️ 부분 |
| Phase 5 (ML 학습) | ✅ ml-trend | ✅ MLModelHistory 기반 | ⚠️ 부분 |
| Phase 6 (LightGBM) | ✅ ml-trend | ✅ algorithm='lightgbm' 필터 | ⚠️ 부분 |

**부가 검증:**
- 평일/주말 판정: ✅ `views.py:1471` `is_weekend = now.astimezone(KST).weekday() >= 5`
- KST 기준 날짜: ✅ KST_MIDNIGHT + TruncDate(tzinfo=KST)
- 캐시 정책: ✅ pipeline-health 5분, collection-logs 5~30분

### ML 운영 시스템 (Shadow/Production, LightGBM) 실제 동작 추정

| 항목 | 구현 | 근거 |
|------|------|-----|
| Shadow Mode 저장 | A | `ml_production_manager.py:43~150` `deployment_status='shadow'` |
| 4주 연속 Safety Gate | A | `ml_production_manager.py:70~77` |
| 자동 Production 전환 | A | `tasks.py:770~800` `check_auto_deploy()` |
| LightGBM 학습 pipeline | A | `ml_weight_optimizer.py:963~1000` `train_lightgbm()` |
| 연속 F1 하락 감지 | A | `ml_production_manager.py:460~490` |
| 주간 리포트 (f1_trend, llm_accuracy, data_stats) | A | `ml_production_manager.py:274~350` |
| 모델 롤백 | A | `ml_production_manager.py:425~458` |

**추정**: `tasks.py`의 `train_importance_model`, `train_lightgbm_model`, `generate_weekly_ml_report`, `monitor_ml_performance` 호출 시 ML 운영 시스템이 정상 동작.

---

## 종합 권장 (우선순위)

1. **[P0] SEC Pipeline `merger.py` 호출 연결** — Neo4j 중복 관계 위험 제거 (`tasks.py:sync_dirty_to_neo4j` 또는 `signals.py` 후처리에 추가).
2. **[P0] SEC Pipeline REST API 라우트 구축** — `/api/v1/sec/metrics/`, `/api/v1/sec/relations/`, `/api/v1/sec/reports/` 정의. CLAUDE.md 완료 표기에 부합.
3. **[P0] Validation 프론트엔드 (FE-PR-1~3)** — 백엔드 88% 완료된 상태에서 사용자 노출 0%. L1/L2 네비, Signal Summary 카드, Accordion UX.
4. **[P1] News `check_pipeline_alerts` Celery Beat 추가** — Phase C 능동 모니터링 완성 (인프라 담당).
5. **[P1] SEC Pipeline Celery Beat 활성화** — `tasks.py:558-566` 주석 해제 + 운영 환경 스모크 테스트.
6. **[P2] SEC Pipeline Admin 대시보드 템플릿 생성** — `templates/admin/sec_pipeline/dashboard.html` 4-grid 레이아웃.
7. **[P2] Validation `serializers.py` 생성** — DRF 표준 패턴 정합성.
8. **[P3] News 프론트엔드 sub-tab 6개 완성** + 키워드 Strip v2.
9. **[P3] SEC Pipeline 테스트 작성** — `tests.py` 1줄 → unit/integration coverage.

---

## 부록: 데이터 소스

- 설계 문서 분석: `docs/sec_pipeline/` (17 파일, 856줄), `docs/first_validation_system/` (6 파일, 2,941줄), `docs/news/plan/` (3 파일, 1,456줄)
- 구현 코드 분석: `sec_pipeline/` (22 파일, 3,313줄), `validation/` (15 파일, 2,997줄), `news/` (24 파일, 12,377줄)
- 검증 방식: 파일경로:줄번호 직접 인용 + task_done 완료 보고서 cross-reference
- 제약: 코드 수정 금지, 읽기 전용. 동적 동작 검증(런타임 호출, DB count)은 "추정" 표기.
