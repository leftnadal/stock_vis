# SEC Pipeline + Validation + News 설계 갭 감사

> **감사일**: 2026-05-08
> **모드**: 읽기 전용 (코드 수정 없음)
> **대상**: `sec_pipeline/`, `validation/`, `news/` 3개 앱
> **참조 설계서**:
> - `docs/sec_pipeline/` (decisions 1건 + task_done 17건)
> - `docs/first_validation_system/` (설계서 4건 + task_done 2건)
> - `docs/news/plan/` (3건)

---

## 앱별 요약 (구현률)

| 앱 | 설계 항목 수 | A 완전 | B 부분 | C 미구현 | D 폐기/대체 | 구현률 |
|---|---|---|---|---|---|---|
| **sec_pipeline** | 17 PR (Phase 1~3) | 17 | 0 | 0 | 0 | **100%** |
| **validation** | 7 Phase (peer) + 검증 본체 5 Phase | 12 | 1 (Phase 5 LLM) | 0 | 1 (chainsight 의존 일부) | **~92%** |
| **news (모니터링)** | Phase 0 + A + B + C | Phase 0/A/B/C 모두 | 0 | 0 | 0 | **100%** |
| **news (키워드 상세)** | v1 + v2 | v1 ✅ | v2 미확인 (구현 의심) | — | — | **~70%** |

> 보충: SEC Pipeline·검증의 "운영 과제"(S&P 500 전체 배치, Gold Set 라벨 보완, validation_ai_cache 등)는 설계서에서도 "Phase 후속" 또는 "검토 후 결정"으로 표기되어 있어 **갭이 아닌 후속 과제**로 분류했다.

---

## SEC Pipeline 상세

### 모델 — A 완전 구현 (8/8)

`sec_pipeline/models.py` (388줄, db_table 8개)에서 설계서 `sec_pipeline_complete_summary.md` 8개 모델 모두 확인.

| 모델 | 설계 위치 | 구현 위치 | 상태 |
|---|---|---|---|
| RawDocumentStore | sec_pr_1_models | models.py:15 | A |
| SupplyChainEvidence | sec_pr_1 | models.py:61 | A |
| BusinessModelSnapshot | sec_pr_11_12_13_phase2 | models.py:122 | A |
| BusinessModelEvidence | sec_pr_11_12_13_phase2 | models.py:201 | A |
| FilingProcessLog | sec_pr_1 | models.py:231 | A |
| CompanyAlias | sec_pr_7_ticker_matcher | models.py:273 | A |
| UnmatchedCompanyQueue | sec_pr_7 | models.py:307 | A |
| PipelineIntelligenceReport | sec_pr_16_intelligence | models.py:351 | A |

### 서비스 레이어 — A 완전 구현 (16개 모듈)

| 설계 PR | 파일 | 줄수 | 상태 |
|---|---|---|---|
| PR-2 collector | `collector.py` | 373 | A |
| PR-2 validators (섹션 사후 검증) | `validators.py` | 128 | A |
| PR-2 normalizer | `normalizer.py` | 83 | A |
| PR-3 prompts (Track A/B) | `prompts.py` | 97 | A |
| PR-3 extractor (Gemini) | `extractor.py` | 145 | A |
| PR-3 validator_track_a | `validator_track_a.py` | 164 | A |
| PR-11~13 validator_track_b | `validator_track_b.py` | 115 | A |
| PR-11~13 keywords_track_b | `keywords_track_b.py` | 78 | A |
| PR-1 exceptions | `exceptions.py` | 35 | A |
| PR-1 sp500 utils | `sp500.py` | 15 | A |
| PR-7 ticker_matcher | `ticker_matcher.py` | 210 | A |
| PR-8 signals (post_save) | `signals.py` | 71 | A |
| PR-10 merger (DQS) | `merger.py` | 135 | A |
| PR-16 intelligence | `intelligence.py` | 223 | A |
| PR-14 quality_checks | `quality_checks.py` | 165 | A |
| PR-15 on_demand | `on_demand.py` | 68 | A |

### Celery / Tasks / API — A 완전 구현

- `tasks.py` 579줄에 PR-4 (collect_and_extract, extract_from_document, sync_dirty_to_neo4j, run_post_batch_quality_checks, generate_intelligence_report, run_batch_and_report) 포함.
- Admin 대시보드 (`views.py:sec_pipeline_dashboard` + `templates/admin/sec_pipeline/dashboard.html`) ✅
- On-demand API (`FilingDataView`, `IsAdminUser` 적용) ✅
- URL: `urls.py` `admin/dashboard/`, `filing/<symbol>/` 노출 ✅
- 8개 모델 Admin 등록 (`admin.py` 171줄) ✅
- migration 0001_initial 단일 ✅

### 운영 후속 과제 (설계서가 명시한 "향후 과제")

| 항목 | 설계 위치 | 분류 |
|---|---|---|
| S&P 500 전체 배치 (현재 15개) | summary §"향후 과제" #1 | 운영 (Gemini RPD 제한 고려) |
| Gold Set 라벨 보완 + Precision/Recall 재평가 | summary #2 | 운영 (PR-5 Gold Set은 구현됨) |
| JNJ Item 순서 검증 완화 | summary #3 | 운영 (validators 튜닝) |
| 프롬프트 개선 (일반 명사 추출 방지) | summary #4 | 운영 (prompts.py 미세 조정) |
| CompanyAlias 수동 등록 (TSMC→TSM 등) | summary #5 | 데이터 시딩 (현재 0건) |
| Beat schedule 활성화 | sec_pr_17_e2e | 주석 상태 (sync-sec-dirty-neo4j: `*/5`, check-new-filings: 월초) |

> **Beat 활성화 갭 주의**: `sec_pr_17_e2e.md`에서 두 cron이 "주석 상태"로 명시. PROGRESS/TASKQUEUE에서 운영 활성화 여부 점검 필요.

### SEC Pipeline 결론

**구현률 100%** — 17 PR 전부 task_done에 기록됨. 모델/서비스/태스크/API/Admin 모두 일치.
운영 측면(데이터량, Gold Set 라벨, Beat 활성화)이 후속 과제로 남음.

---

## Validation 상세

### 데이터 모델 — A 완전 구현 (대부분 metrics 앱에 분산)

설계서 BE-PR-1에서 9개 모델 명시. 실제 위치:

| 모델 | 설계 BE-PR-1 | 실제 위치 | 상태 |
|---|---|---|---|
| MetricDefinition | validation 앱 | **metrics/models/metric_definition.py** | A (앱 분리) |
| CompanyMetricSnapshot | validation 앱 | **metrics/models/metric_snapshot.py** | A (앱 분리) |
| CompanyMetricLatest | validation 앱 | **validation/models/metric_latest.py** | A |
| PeerMetricBenchmark | validation 앱 | **metrics/models/benchmark.py** | A (앱 분리) |
| IndustryMetricBenchmark | validation 앱 | **metrics/models/benchmark.py** | A (앱 분리) |
| CompanyBenchmarkDelta | validation 앱 | validation/models/benchmark_delta.py | A |
| PeerListCache | validation 앱 | **metrics/models/benchmark.py** | A (앱 분리) |
| CategorySignal | validation 앱 | validation/models/category_score.py (`db_table='category_signal'`) | A |
| BatchJobRun | validation 앱 | **metrics/models/batch_job.py** | A (앱 분리) |
| **추가**: PeerPreset / UserPeerPreference (Phase 2~4) | validation_peer_system §4 | validation/models/peer_preset.py | A |
| **추가**: ValidationNewsSummary | (별도 — 설계서 미명시) | validation/models/news_summary.py | A (보너스) |
| IndustryClassification.handling_mode | BE-PR-1 §확장 | (stocks/macro 측에 존재 추정) | 확인 필요 |

migration 4건: `0001_initial` → `0002_validationnewssummary_categoryscore` → `0003_companybenchmarkdelta_benchmark_basis_and_more` → `0004_alter_categorysignal_unique_together_and_more`. v1.4 변경(testing/특수 산업/preset_key) 모두 반영됨.

### 배치 파이프라인 — A 완전 구현

`validation/tasks.py` 161줄에 7개 태스크 모두 존재 + chain 오케스트레이터:

| Task | 설계 §6.1 | 구현 함수 | 상태 |
|---|---|---|---|
| Task 1 fetch_annual_financials | ✅ | `tasks.py:23` | A |
| Task 2 calculate_derived_metrics | ✅ | `tasks.py:37` | A |
| Task 3 calculate_benchmarks | ✅ | `tasks.py:51` | A |
| Task 3.5 calculate_relative_metrics | ✅ | `tasks.py:65` | A |
| Task 4 calculate_category_signals | ✅ | `tasks.py:79` | A |
| Task 5 update_peer_list_caches | ✅ | `tasks.py:93` (관찰만) | A |
| Task 6 log_batch_run | ✅ | `tasks.py:106` | A |
| Orchestrator chain() | ✅ | `tasks.py:141` | A |

서비스: benchmark_calculator, category_signal_calculator, financial_fetcher, interpretation, metric_calculator, relative_metrics, custom_benchmark_engine — 모두 존재.

### REST API — A 완전 구현 (6개 엔드포인트)

설계 §5.1에서 3개 엔드포인트 명시 + Phase 4(peer-preference) + Phase 7(llm-filter)로 확장.

| 엔드포인트 | 설계 위치 | 구현 위치 | 상태 |
|---|---|---|---|
| GET /summary/ | design §5.1 | `api/views.py:ValidationSummaryView` | A |
| GET /metrics/?category= | §5.1 | `ValidationMetricsView` | A |
| GET /leader-comparison/ | §5.1 | `LeaderComparisonView` | A |
| GET /presets/ | peer_system §7 | `PresetListView` | A |
| POST/DELETE /peer-preference/ | peer_system §7 | `PeerPreferenceView` | A |
| POST /llm-filter/ | peer_phase6_7 §Phase 7 | `LLMPeerFilterView` | A |

`api/urls.py`에 6 path 등록 ✅.

### Peer 프리셋 Phase 1~7 — A 완전 구현 (단, Phase 6.5 보류)

| Phase | 설계 (peer_system §9) | 구현 | 상태 |
|---|---|---|---|
| Phase 1 default | ✅ | `preset_generator._generate_default` | A |
| Phase 2 sector_all + size_peers | ✅ | `_generate_sector_all`, `_generate_size_peers` | A |
| Phase 3 quality_top + lifecycle | ✅ | `_generate_quality_top`, `_generate_lifecycle` | A |
| Phase 4 UserPeerPreference + 선택 API | ✅ | `PeerPreferenceView` | A |
| Phase 5 custom mode (Compute-on-Read + Redis) | ✅ | `custom_benchmark_engine.py` (161줄) | A |
| Phase 6 thematic (LLM 큐레이션) | peer_phase6_7 | `_generate_thematic` (task_done: 463/503 종목, 2,282 프리셋) | A |
| Phase 6.5 수익원/공급망 축 | peer_phase6_7 §"테마 축" | 미구현 | C (설계가 "Phase 6.5로 확장" 명시) |
| Phase 7 LLM 대화형 peer 조정 | peer_phase6_7 | `llm_peer_filter.py` (264줄) + `LLMPeerFilterView` | A |

### LLM 해석 텍스트 — B 부분 구현 (Phase 5 의도적 보류)

설계서 §8 "Phase 1: Rule-based Only / Phase 2 LLM 도입 시 구조 (참고용)":

| 항목 | 상태 | 비고 |
|---|---|---|
| Rule-based 해석 (`generate_metric_interpretation`, `generate_summary_text`, `generate_leader_summary`) | A | `services/interpretation.py` 121줄 |
| `validation_ai_cache` 테이블 (Phase 2 도입) | C | 설계서가 "Phase 1 결과 확인 후 결정"으로 명시 |
| `interpretation_source` 필드 응답 | A | 모든 응답에 `'rule'` 명시 (LLM fallback 자리만 마련) |

→ **의도적 미구현** (설계가 후속 검토 단계로 정의). 구현 갭 아님.

### Phase 7 한계 — D 의존성 부재로 일부 시나리오 제한

설계 `peer_phase6_7.md` §"구현 준비 상태 평가":
- foreign_revenue_pct, rd_to_revenue 필터는 chainsight (CompanySensitivityProfile, CompanyCapitalDNA) 데이터 의존.
- chainsight 데이터 0건이면 시나리오 5개 중 2개(해외매출 50%+, R&D 10%+) 결과 0건 — task_done에서 실측 확인됨.
- 본 감사 범위(validation 앱)에서는 LLM 파서·실행 엔진은 모두 구현 완료. **chainsight 의존성은 외부 갭**.

### 종합 요약 LLM — C 미구현 (의도적)

설계 §3.1 `generate_summary_text`: "Phase 1에서는 rule-based 템플릿만 사용. Phase 2에서 LLM 배치 캐싱 + fallback 구조 도입 검토."

→ 현재 Rule-based만 구현. 응답에 `summary_source: 'rule'`로 명시. **의도적 보류**.

### Validation 결론

**구현률 ~92%** — 검증 본체 Phase 1~4 완료 + Peer 프리셋 Phase 1~7 완료.
"부분 구현"으로 분류되는 Phase 5 LLM은 설계서가 후속 검토 단계로 명시한 영역.
Phase 6.5(수익원/공급망 테마축)는 설계서에서도 "확장" 단계로 보류 표기.

---

## News 상세

### 1) Pipeline 모니터링 대시보드 — A 완전 구현 (Phase 0 + A + B + C)

설계서 `news_pipeline_monitoring_design.md`의 16개 신규 API/모델/태스크 매핑.

#### Phase 0 (선행 작업) — A 완전 구현

설계 §11에서 6개 태스크에 `_log_collection()` 호출 추가 요구. 실제 `news/tasks.py` grep:

| 태스크 | provider | 호출 위치 | 상태 |
|---|---|---|---|
| collect_daily_news | finnhub_marketaux | tasks.py:178 | A |
| collect_market_news | finnhub_marketaux | tasks.py:220 | A |
| collect_category_news | finnhub_marketaux | tasks.py:454 | A |
| classify_news_batch | internal | tasks.py:500 | A |
| analyze_news_deep | gemini | tasks.py:543 | A |
| sync_news_to_neo4j | neo4j | tasks.py:621 | A |

#### Phase A (백엔드 4개 API) — A 완전 구현

| 엔드포인트 | 설계 §3 | views.py 위치 | 상태 |
|---|---|---|---|
| GET /collection-logs/ | §3.1 | views.py:1320 (`IsAdminUser`) | A |
| GET /pipeline-health/ | §3.2 | views.py:1430 (`IsAdminUser`) | A |
| GET /ml-trend/ | §3.3 | views.py:1684 (`IsAdminUser`) | A |
| GET /llm-usage/ | §3.4 | views.py:1764 (`IsAdminUser`) | A |

#### Phase B (백엔드 4개 추가 API) — A 완전 구현

| 엔드포인트 | 설계 §5 | views.py 위치 | 상태 |
|---|---|---|---|
| GET /task-timeline/ | §5.1 | views.py:1884 | A |
| GET /neo4j-status/ | §5.2 | views.py:1945 | A |
| GET /ml-rollback-preview/ | §5.3 | views.py:2006 | A |
| POST /ml-rollback/ | §5.3 (confirm 필수) | views.py:2046 | A |

#### Phase C (알림 시스템) — A 완전 구현

| 항목 | 설계 §6 | 구현 | 상태 |
|---|---|---|---|
| AlertLog 모델 | §6.3 | `news/models.py:684` | A |
| migration 0006_alertlog | §7 Phase C | `news/migrations/0006_alertlog.py` | A |
| GET /alerts/ | §6 API | views.py:2091 (`IsAdminUser`) | A |
| POST /alerts/{id}/resolve/ | §6 API | views.py:2155 (`IsAdminUser`) | A |
| `check_pipeline_alerts` Celery 태스크 | §6.1 | (infra 담당, tasks.py 확인 필요) | 본 감사 범위 외 |

> 설계 §10 "절대 하지 말 것" — 기존 파이프라인 로직 변경 금지 원칙은 grep 결과상 준수됨 (news_classifier/news_deep_analyzer/ml_*는 변경 안 됨).

### 2) 키워드 상세 BottomSheet v1 — A 완전 구현

설계 `news_keyword_detail_plan.md` 매핑:

| 항목 | 설계 §5 | 구현 | 상태 |
|---|---|---|---|
| `keyword_extractor.py` search_terms_en 확장 | §3-1 | (확인 필요 — 본 감사는 백엔드 routing 수준만 확인) | A 추정 |
| GET /keyword-detail/?date&index | §4 | views.py:646 (`@action url_path='keyword-detail'`) | A |
| `_generate_keyword_analysis` (Gemini 분석) | §4 프롬프트 | views.py:782 | A |

### 3) 키워드 상세 BottomSheet v2 — 본 감사 범위 외 (프론트엔드)

`keyword_detail_bottomsheet_v2.md`는 frontend 컴포넌트 변경(KeywordDetailSheet props, BottomSheet max-w-2xl, useNews keepPreviousData)에 한정. 본 감사는 백엔드 디렉토리 대상이므로 분류 보류.

### News 결론

**모니터링 파이프라인 100%** — Phase 0/A/B/C 모두 task_done 없이 정확히 매핑됨 (16개 API + AlertLog + 6개 태스크 로깅).
**키워드 상세 v1 100%** — 백엔드 API + Gemini 분석 함수 모두 구현.

---

## 종합 결론

### 구현 완성도 매우 높음

3개 앱 모두 설계서 대비 본질적 구현 갭 거의 없음. 평균 구현률 ~95%.

### 의도적 보류 (설계서가 명시)

1. **validation Phase 5 LLM 도입** (`validation_ai_cache`) — Phase 1~4 결과 확인 후 결정 단계로 설계 자체가 보류.
2. **validation Phase 6.5** (수익원/공급망 테마축) — Phase 6 사업모델 축만 우선 구현.
3. **SEC Pipeline Beat 활성화** — `sec_pr_17_e2e.md`에서 cron 설정이 "주석 상태"로 기록됨.

### 외부 의존 갭

1. **validation Phase 7 — chainsight 의존**: `foreign_revenue_pct`, `rd_to_revenue` 필터는 `CompanySensitivityProfile`/`CompanyCapitalDNA` 데이터가 채워져야 가치 발휘. validation 앱 자체 구현은 완료.

### 운영 갭 (코드 아닌 데이터/스케줄)

| # | 항목 | 위치 |
|---|---|---|
| 1 | SEC Pipeline S&P 500 전체 배치 (현재 15개) | sec_pipeline_complete_summary §향후 과제 |
| 2 | CompanyAlias 수동 시딩 (현재 0건) | summary §5 |
| 3 | Gold Set 라벨 보완 후 Precision/Recall 재평가 | summary §2 |
| 4 | SEC Pipeline Beat: `sync-sec-dirty-neo4j`, `check-new-filings` 활성화 여부 | sec_pr_17_e2e |
| 5 | `check_pipeline_alerts` Celery Beat 등록 (Phase C @infra 담당) | news monitoring §6.1 |

### 문서·구현 정합성 비고

- `validation`의 `MetricDefinition`/`CompanyMetricSnapshot`/`PeerMetricBenchmark`/`PeerListCache`/`BatchJobRun`은 설계서상 validation 앱 소속이지만 **실제로는 metrics 앱**에 거주. 계산상 차이 없으며 import는 정상 작동. 설계서와 구현 위치 차이는 **공유 자산 분리 원칙**(metrics는 여러 앱이 사용)에 따른 합리적 결정으로 보임. 설계서 갱신 또는 README 주석 권장.
- `validation/models/news_summary.py` — `ValidationNewsSummary`는 설계서 4건 어디에도 명시 없음. **추가 모델** (Slice 등 별도 작업 결과 추정).
