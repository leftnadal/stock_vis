# SEC Pipeline + Validation + News 설계 갭 감사

> **생성일**: 2026-05-30
> **범위**: `docs/sec_pipeline/` vs `sec_pipeline/`, `docs/first_validation_system/` vs `validation/`, `docs/news/plan/` vs `news/`
> **성격**: 읽기 전용 감사. 코드 수정 없음.
> **분류 기준**: (A) 완전 구현 · (B) 부분 구현 · (C) 미구현 · (D) 폐기/대체

---

## 앱별 요약 (구현률)

| 앱 | 설계 소스 | 구현률 (A/B/C/D) | 핵심 결론 |
|----|-----------|------------------|-----------|
| **SEC Pipeline** | task_done 17개 PR + complete_summary + decisions 1건 | **A ~97% / B ~3% / C 0% / D 0%** | 내부 파이프라인은 설계 충실도 매우 높음. 단, **공개 REST API 표면이 2개로 매우 얇음**(대시보드+filing). 추출 데이터는 대부분 admin/내부 서비스로만 노출 |
| **Validation** | design + peer_system + phase6_7 + task_done 2개 | **A ~89% / B ~11% / C 0% / D 0%** | 6종 프리셋·Compute-on-Read·Phase6 thematic·Phase7 LLM 필터 전부 구현. 미흡 4건은 UI 고지/극단값 로직 등 비핵심 |
| **News (plan/ 3문서 범위)** | keyword_detail + bottomsheet_v2 + monitoring | **A ~97% / B ~3% / C 0% / D 0%** | 키워드 상세 API + 모니터링 Phase A/B/C 백엔드 전부 구현. bottomsheet_v2의 FE 컴포넌트는 본 감사 범위 밖(미검증) |

> **주의**: 위 % 는 각 설계 문서/완료보고서가 **주장한 기능 항목 대비** 코드 존재 여부 기준이다. "설계서가 다루지 않은 미래 범위"는 분모에 없다. 특히 SEC는 완료보고서 자체가 내부 파이프라인 중심이라 점수가 높게 나오지만, **외부 소비 가능한 API는 빈약**하다는 점을 별도로 강조한다(아래 SEC 상세 ⚠️ 참조).

---

## SEC Pipeline 상세

**설계 소스**: `docs/sec_pipeline/task_done/` 17개 PR 완료보고서 + `sec_pipeline_complete_summary.md` + `decisions/001_fmp_vs_sec_edgar_metadata.md`
**구현**: `sec_pipeline/` (24개 모듈)

### PR 단위 매핑

| 기능/PR | 분류 | 근거(파일:라인) | 비고 |
|---------|------|----------------|------|
| PR-1 모델 정의 (8개) | A | `models.py:1-389` | FK/메타데이터 설계대로 |
| PR-2 SEC EDGAR 수집기 | A | `collector.py` | 메타데이터+HTML+섹션 추출+fallback |
| PR-2 섹션 검증 | A | `validators.py` | 순서/heading/길이 3단계 |
| PR-3 정규화 + 키워드 필터 | A | `normalizer.py` | 30개 키워드 사전 |
| PR-3 Track A Gemini 추출 | A | `extractor.py`, `prompts.py:11-43` | JSON mode + confidence |
| PR-3 Track A 검증 | A | `validator_track_a.py` | 제네릭 용어 필터 + grade |
| PR-4 Celery 기본 task | A | `tasks.py:22-145` | collect_and_extract 5단계 |
| PR-4 extract_from_document | A | `tasks.py:148-278` | Track A/B 분리 실패 처리 |
| PR-4 예외 + S&P500 | A | `exceptions.py:1-36`, `sp500.py` | 재시도 정책 포함 |
| PR-5 Gold Set 평가 | A | `management/commands/evaluate_gold_set.py`, `fixtures/gold_set.json` | |
| PR-6 배치 실행 | A | `tasks.py:524-531` | 종목별 반복 |
| PR-7 Ticker 3단계 매칭 | A | `ticker_matcher.py` | alias→exact→fuzzy + BLOCKED_NAMES |
| PR-7 미매칭 큐 적재 | A | `tasks.py:206-210` | match_with_queue() |
| PR-8 Admin + Signal | A | `admin.py`, `signals.py:1-72` | post_save로 alias 자동 등록 |
| PR-9 Neo4j Sync | A | `tasks.py:337-452` | DELETE+CREATE, dynamic type |
| PR-10 관계 병합 + 큐 처리 | A | `merger.py`, `management/commands/process_unmatched_queue.py` | DQS 계산 |
| PR-11 Track B 키워드 | A | `keywords_track_b.py` | 5개 필드별 사전 |
| PR-12 Track B 추출+검증 | A | `extractor.py`, `validator_track_b.py`, `tasks.py:236-277` | business_model snapshot |
| PR-13 서비스 레이어 | A | `metrics/services/business_model_service.py` (서브에이전트 보고) | confidence 게이트. **※ sec_pipeline 외부(metrics 앱)에 위치 — 경로 재확인 권장** |
| PR-14 품질 체크 + 대시보드 | A | `quality_checks.py`, `views.py:15-26`, `urls.py:7` | get_dashboard_stats + 템플릿 |
| PR-15 On-demand 수집 + API | A | `on_demand.py:1-69`, `views.py:29-51`, `urls.py:8` | FilingDataView 200/202 |
| PR-15 check_new_filings task | A | `tasks.py:464-497` | S&P500 신규 감지 |
| PR-16 Intelligence 수집+리포트 | A | `intelligence.py`, `prompts.py` | 5차원 메트릭 + Gemini |
| PR-16 Intelligence Admin | A | `admin.py` | severity_badge, regenerate |
| PR-17 generate_intelligence_report | A | `tasks.py:500-505` | |
| PR-17 run_batch_and_report (3-phase) | A | `tasks.py:508-550+` | 수집→후처리→intelligence |
| **PR-17 Celery Beat 스케줄** | **B** | `tasks.py` 내 주석 | **스케줄이 주석 상태 — config에서 미활성. 버그 #28(Beat drift)과 연관, DB 등록 필요** |

### ⚠️ 공개 API 표면 갭 (감사관 추가 관찰)

서브에이전트는 PR 완료보고서 기준 97% A를 산정했으나, **실제 외부 노출 API는 2개뿐**이다:

| 등록된 엔드포인트 | 근거 | 성격 |
|-------------------|------|------|
| `GET /api/v1/sec-pipeline/admin/dashboard/` | `urls.py:7`, `config/urls.py:46` | 운영 대시보드(HTML) |
| `GET /api/v1/sec-pipeline/filing/<symbol>/` | `urls.py:8` | on-demand 수집 트리거 |

- **CLAUDE.md 문서 불일치**: CLAUDE.md는 `/api/v1/sec/*`로 표기하나 실제 prefix는 **`/api/v1/sec-pipeline/`** (`config/urls.py:46`). → **문서 정정 필요**.
- 추출된 Supply Chain / Business Model 데이터를 **프런트엔드가 직접 조회할 공개 REST API는 부재**. 데이터는 Neo4j sync, admin, `metrics` 서비스 게이트를 통해서만 소비된다. 완료보고서 범위에선 "의도된 설계"이나, **서비스 소비 관점에서는 (B) 부분 노출**로 봐야 한다.

**SEC Pipeline 구현률: 내부 파이프라인 A ~97% / B ~3%(Beat 스케줄). 단, 외부 API 노출은 의도적으로 얇음 — 데이터 소비 API 신설은 별도 과제.**

---

## Validation 상세

**설계 소스**: `validation_design.md`, `validation_peer_system.md`, `validation_peer_phase6_7.md`, `task_done/peer_phase6_thematic.md`, `task_done/peer_phase7_llm_filter.md`
**구현**: `validation/` (models 5 + services 9 + api)

### 기능 단위 매핑 (완전 구현 핵심)

| 기능 | 분류 | 근거(파일:라인) | 비고 |
|------|------|-----------------|------|
| 모델 PeerPreset / UserPeerPreference | A | `models/peer_preset.py:1-68` | mode(preset/custom) 포함 |
| CompanyBenchmarkDelta preset_key 확장 | A | `models/benchmark_delta.py:26-41` | benchmark_basis/confidence + unique_together |
| CategorySignal preset_key 확장 | A | `models/category_score.py:51` | |
| API 6종 (summary/metrics/leader/presets/peer-preference/llm-filter) | A | `api/views.py:52-562`, `api/urls.py:1-14` | 전부 등록 + `/api/v1/validation/`(`config/urls.py:44`) |
| BenchmarkCalculator (peer 선정 3단 fallback) | A | `services/benchmark_calculator.py:46-106` | industry+size→industry→sector |
| PresetGenerator 6종 | A | `services/preset_generator.py:1-299` | default/sector_all/size_peers/quality_top/lifecycle/thematic |
| Phase 6 thematic (GrowthStage×CapitalDNA) | A | `preset_generator.py:54`; `task_done/peer_phase6_thematic.md` | 463/503 종목, 2,282 프리셋 |
| Phase 7 LLM 필터 (Gemini 2.5 Flash) | A | `services/llm_peer_filter.py:1-265` | 8개 필터 카테고리, JSON mode |
| CustomBenchmarkEngine (Compute-on-Read) | A | `services/custom_benchmark_engine.py:1-150` | Redis TTL 1h |
| CategorySignalCalculator | A | `services/category_signal_calculator.py:45-138` | percentile 평균 + gray 처리 |
| Rule-based 해석 (summary/metric) | A | `services/interpretation.py:12-90` | |
| MetricCalculator (지표 + value_status) | A | `services/metric_calculator.py:51-125` | normal/n/a/missing/unstable |
| Celery Task 1-6 chain | A | `tasks.py:22-120` | fetch→derive→benchmark→relative→signal→cache |
| 특수 산업(금융/REIT) gray 처리 | A | `category_signal_calculator.py:29-32,132-138` | handling_mode='special' |
| Migration 0003/0004 | A | `migrations/0003*`, `0004*` | preset_key + unique_together |
| seed_validation_data (지표 34 + 산업분류) | A | `management/commands/seed_validation_data.py` | |

### 부분 구현 (B) — 4건, 모두 비핵심

| 기능 | 분류 | 근거 | 갭 내용 |
|------|------|------|---------|
| Peer 시간 변동 한계 UI 고지 | B | `api/views.py:103-104` | 데이터 로직은 있으나 "과거 연도도 현재 peer 기준" 고지 필드/문구 미존재 |
| interest_coverage 극단 변동 감지 | B | `services/metric_calculator.py` | value_status='unstable' 분기만 존재, 부호반전·배수 판정 상세 로직 미확인 |
| 5년 차트 X축 동적 조정 | B | `api/views.py:265-267` | 최대 5년 로드만, 가용 연도 기반 동적 조정 명시 미흡 |
| 대장주=자기자신 시 2위 표시 | B | `api/views.py:149-161` | 2위 선택 로직은 있으나 "업종 2위" 표기 문구 미확인 |

**Validation 구현률: A ~89%(31/35) / B ~11%(4/35) / C 0 / D 0. 설계 핵심(프리셋·Compute-on-Read·thematic·LLM 필터) 전건 완성, 미흡은 UI 고지·극단값 로직 등 우선순위 낮은 항목.**

---

## News 상세

**설계 소스**: `docs/news/plan/` 3개 문서 (Intelligence Pipeline v3 본체가 아닌 plan/ 범위에 한정)
**구현**: `news/` (models + api + providers + services 17)

### ① news_keyword_detail_plan.md

| 기능 | 분류 | 근거(파일:라인) | 비고 |
|------|------|----------------|------|
| `GET /api/v1/news/keyword-detail/?date=&index=` | A | `api/views.py:655-789` | 설계대로 |
| DailyNewsKeyword 모델 (status/tokens 등) | A | `models.py:391-492` | |
| 기사 2단 매칭 (related_symbols + search_terms_en) | A | `views.py:718-754` | article_ids 우선 + fallback |
| search_terms_en 추출 | A | `services/keyword_extractor.py:241-246,306` | 프롬프트 + 파싱 |
| Gemini 투자 관점 요약 / 실패시 null | A | `views.py:791-827`, `768-776` | |
| 캐시(updated_at 포함) / 400·404 처리 | A | `views.py:682-712` | TTL 1h |
| FALLBACK_KEYWORDS의 search_terms_en | B | `keyword_extractor.py:43-45` | 레거시 키워드는 기본값만 보유 |

### ② keyword_detail_bottomsheet_v2.md

| 기능 | 분류 | 근거 | 비고 |
|------|------|------|------|
| keyword-detail API (BottomSheet 지원) | A | `api/views.py:655-789` | BE 요구사항 충족 |
| FE 컴포넌트(KeywordDetailSheet.tsx, PipelineStatusBar 등) | B | — | **본 감사 범위 밖(백엔드). FE 소스 미검증 → 별도 확인 필요** |

### ③ news_pipeline_monitoring_design.md

| Phase | 기능 | 분류 | 근거(파일:라인) |
|-------|------|------|----------------|
| A | `GET /collection-logs/` (필터+집계) | A | `views.py:1329-1437` |
| A | `GET /pipeline-health/` (6 Phase + weekend 면제) | A | `views.py:1439-1691` |
| A | `GET /ml-trend/` | A | `views.py:1693-1771` |
| A | `GET /llm-usage/` | A | `views.py:1773-1889` |
| B | `GET /task-timeline/` | A | `views.py:1893-1952` |
| B | `GET /neo4j-status/` | A | `views.py:1954-2013` |
| B | `GET /ml-rollback-preview/` + `POST /ml-rollback/` | A | `views.py:2015-2096` |
| C | `GET /alerts/` + `POST /alerts/{id}/resolve/` | A | `views.py:2100-2198` |
| C | AlertLog 모델 | A | `models.py:684-727` |
| 0 | `_log_collection` 6개 태스크 적용 | A | `tasks.py:178,220,454,500,543,621` |
| — | 모델 필드(NewsCollectionLog/MLModelHistory/DailyNewsKeyword) | A | `models.py:443-681` |

**News(plan/ 3문서) 구현률: A ~97% / B ~3% / C 0 / D 0. 키워드 상세 API + 모니터링 Phase A/B/C 백엔드 전건 완성. B 2건은 (1) FALLBACK 키워드 search_terms_en 기본값, (2) bottomsheet_v2 FE 컴포넌트(범위 밖).**

---

## 종합 권고 (읽기 전용 — 후속 과제 후보)

1. **CLAUDE.md 정정**: SEC API prefix `/api/v1/sec/*` → 실제 `/api/v1/sec-pipeline/` (`config/urls.py:46`).
2. **SEC 공개 데이터 API 신설 검토**: Supply Chain / Business Model 추출 결과를 FE가 조회할 REST 엔드포인트 부재(현재 admin/Neo4j/metrics 게이트만). 서비스 소비 시 필요.
3. **SEC Celery Beat 스케줄 활성화**: `tasks.py` 주석 상태 → DatabaseScheduler에 `PeriodicTask` 등록(버그 #28 패턴).
4. **Validation 미흡 4건**: UI 고지 필드(`historical_peer_note`), interest_coverage 극단값 판정, 차트 가용연도 노출, 대장주 2위 표기 — 모두 비핵심 UX.
5. **PR-13 위치 확인**: `business_model_service.py`가 `sec_pipeline/`이 아닌 `metrics/services/`에 있음(서브에이전트 보고). 앱 경계 의도 확인 권장.
6. **News bottomsheet_v2 FE 검증**: 본 감사는 백엔드 한정 — `frontend/`의 KeywordDetailSheet 등 별도 감사 필요.

---

*감사 방식: docs/ 설계·완료보고서 → 구현 파일(models/services/views/urls) cross-reference. 분류는 완료보고서 주장 대비 코드 존재·연결 여부 기준. 본 보고서는 코드를 수정하지 않았다.*
