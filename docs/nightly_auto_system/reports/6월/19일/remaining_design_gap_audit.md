# SEC Pipeline + Validation + News 설계 갭 감사

> **감사 유형**: 읽기 전용 (코드 무수정)
> **감사 일자**: 2026-06-20
> **대상 프로젝트**: `/Users/byeongjinjeong/Desktop/stock_vis`
> **방법론**: 설계 문서(`docs/*`) + 완료보고서(`task_done/*`) vs 실제 구현 코드 대조. 병렬 Explore 에이전트 3종(앱별) 증거 수집 후 종합.
> **분류 기준**: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 앱별 요약 (구현률)

| 앱 | 설계/완료보고서 위치 | 구현 위치 | A | B | C | D | 종합 구현률 | 핵심 갭 |
|----|--------------------|----------|---|---|---|---|-----------|---------|
| **SEC Pipeline** | `docs/sec_pipeline/task_done/` (PR1~17 + summary) | `services/sec_pipeline/` | 17 | 0 | 0 | 0 | **~100%** (17/17 PR) | 갭 없음. Celery Beat만 의도적 주석 |
| **Validation** | `docs/first_validation_system/` (design + peer + PR prompts + task_done×2) | `services/validation/` + `frontend/components/validation/` | 65 | 7 | 7 | 0 | **~91%** (72/79 요소) | Phase 7 LLM 필터 실행 엔진·Thesis 연동·FE edge case |
| **News (모니터링+키워드상세)** | `docs/news/plan/` (3종, **task_done 부재**) | `services/news/` + `frontend/components/(admin/)news/` | 31 | 3 | 1 | 0 | **~89%** (31/35 요소) | Phase C 자동 알림 감지 엔진(Celery) 미구현 |

**전체 한줄 결론**: SEC Pipeline은 설계 대비 완결(100%), News는 저장소·API·UI까지 완비됐으나 알림 *자동 감지 엔진* 한 칸만 비어 있고, Validation은 코어·프리셋은 완성됐으나 Phase 6~7 고급 기능이 외부 데이터(Chain Sight) 의존 + Thesis 연동 미완으로 가장 큰 부채를 안고 있다.

> ⚠️ **신뢰도 주의**: 각 앱 감사는 병렬 Explore 에이전트가 코드 발췌·grep 기반으로 판정했다. "추정" 표기 항목과 "미확인" 항목은 직접 라인 확정이 안 된 것이므로, 후속 조치 전 해당 파일 직접 확인 권장. 특히 Validation의 B/C 다수는 프론트엔드 라우팅·반응형 분기 "미확인"에 기반한 보수적 추정이다.

---

## SEC Pipeline 상세

### 구현률 요약
- (A) 완전 구현: **17 / 17 PR (100%)** · (B) 0 · (C) 0 · (D) 0
- 17개 PR이 약속한 모델·수집기·추출기·Celery·Neo4j·Admin·Intelligence·E2E가 모두 `services/sec_pipeline/`에 실재. 설계-코드 일치도 매우 높음. 추가 구현(테스트 24파일, 관리 커맨드 3종)으로 오히려 설계를 상회.

### PR별 분류 표
| PR | 기능 | 분류 | 근거 파일경로 |
|----|------|------|--------------|
| PR-1 | 8개 모델 + migration | A | `services/sec_pipeline/models.py:15-430`, `migrations/0001_initial.py` |
| PR-2 | SEC EDGAR 수집기 + 섹션추출 | A | `services/sec_pipeline/collector.py:1-374`, `validators.py` |
| PR-3 | Track A (Gemini) + 키워드 필터 | A | `extractor.py:35`, `normalizer.py:63`, `validator_track_a.py` |
| PR-4 | Celery tasks (collect/extract) | A | `tasks.py:22-163`, `exceptions.py` |
| PR-5 | Gold Set + 평가 스크립트 | A | `fixtures/gold_set.json`, `evaluate_gold_set.py` |
| PR-6 | Phase 1 배치 (15종목) | A | `tests/unit/sec_pipeline/` (24 test files) |
| PR-7 | TickerMatcher 3단계 | A | `ticker_matcher.py:90` |
| PR-8 | Admin 모델 + signal | A | `admin.py:1-227`, `signals.py:21` |
| PR-9 | sync_dirty_to_neo4j | A | `tasks.py:398-531` |
| PR-10 | merger + process_unmatched | A | `merger.py`, `management/commands/process_unmatched_queue.py` |
| PR-11~13 | Track B + 서비스 레이어 | A | `keywords_track_b.py`, `validator_track_b.py`, `packages/shared/metrics/services/business_model_service.py` |
| PR-14 | Admin 대시보드 + 품질체크 | A | `views.py`, `quality_checks.py:17-116`, `templates/admin/sec_pipeline/dashboard.html` |
| PR-15 | On-demand 수집 + filing API | A | `on_demand.py:18`, `views.py:29-55`, `urls.py` |
| PR-16 | Intelligence Reporter (5차원) | A | `intelligence.py:63-237` |
| PR-17 | E2E batch + chord 통합 | A | `tasks.py:589-635` |

### 부분/미구현/대체 항목 상세
**없음.** 17개 PR 전부 완전 구현.

### task_done ↔ 코드 불일치 발견 사항
1. **Celery Beat 스케줄 — 설계: 나열 vs 코드: 주석 처리.** `tasks.py:638-646`에 Beat 등록이 주석 상태. 운영 활성화 전 단계로 *의도된* 상태이며 갭 미미.
2. **패키지 경로 — 설계 "sec_pipeline/" vs 실제 "services/sec_pipeline/".** 프로젝트 app 폴더 구조 차이일 뿐, 설계 의도 반영됨.
3. **성능 스케일 — 설계 S&P500 전체 vs 완료보고서 테스트 15종목.** `tasks.py:603 run_batch_and_report`가 `None`일 때 `get_sp500_symbols()` 호출 가능. 단계별 계획 준수, 갭 아님.
4. **Neo4j 동기화** — `tasks.py:459 get_graph_repository()` 통해 외부 모듈(`apps/chain_sight/graph`) 의존. DELETE+CREATE 패턴(MERGE 미사용) 설계 원칙 준수 확인.
5. **for_api 게이트(원칙 6)** — `business_model_service.py:16-54`에서 `for_api`로 confidence 노출 제어, 설계와 일치.
6. **(positive gap)** 설계 미언급 추가물: 테스트 24파일, 관리 커맨드 3종(`rematch_unmatched`, `reprocess_unmatched_queue`, `seed_company_aliases`).

> 외부 의존성 정리: `apps/chain_sight/graph`(Neo4j 저장소), `packages/shared/metrics/services`(Business Model), `packages/shared/stocks/models`(Stock).

---

## Validation 상세

### 구현률 요약
- (A) 65 · (B) 7 · (C) 7 · (D) 0 → **79개 요소 중 72개 구현(~91%)**
- Phase 1~5(코어 배치 파이프라인 + 6개 프리셋 + API + FE 컴포넌트)는 견고하게 완성. Phase 6(thematic)은 로직 완성·데이터는 Chain Sight 의존, Phase 7(LLM peer)은 파싱은 완전하나 실행 엔진·Thesis 연동·대화형 UI가 미완. FE edge case(모바일 Accordion, Empty States 5종, L1/L2 라우팅)는 "미확인" 기반 보수적 B/C.

### 기능/Phase별 분류 표 (요약)
| 영역 | 분류 | 근거 |
|------|------|------|
| 모델 9테이블 / 34지표 시드 | A | `services/validation/models/*.py`, `management/commands/seed_validation_data.py` |
| 배치 Task 1~6 + 오케스트레이터 | A | `tasks.py:23-178`, `services/financial_fetcher.py`·`metric_calculator.py`·`benchmark_calculator.py`·`relative_metrics.py`·`category_signal_calculator.py` |
| API 6종 (Summary/Metrics/Leader/Preset/Preference/LLM) | A | `api/views.py:63-150+`, `api/urls.py` |
| rule-based 해석 3함수 | A | `services/interpretation.py` |
| 프리셋 6종 (default/sector_all/size/quality_top/lifecycle/thematic) | A | `services/preset_generator.py:89-499` |
| 커스텀 peer Compute-on-Read | A | `services/custom_benchmark_engine.py` |
| LLM 필터 파싱(parse_filter_with_llm) | A | `services/llm_peer_filter.py:56-90` |
| FE 컴포넌트(SignalSummaryCard/PeerContextBar/MetricCard/MetricBarChart/CategorySection/IndustryPosition/LeaderComparison) | A | `frontend/components/validation/*.tsx` |
| L1/L2 네비게이션 재설계 | **B** | 컴포넌트 존재, 라우팅/탭 상태 미확인 |
| 모바일 Accordion | **B** | 반응형 breakpoint 분기 완전성 미확인 |
| Empty States 5케이스 | **B** | 기본 에러 처리만, 5케이스별 UI 미확인 |
| Redis 캐싱(커스텀 결과, TTL 1h) | **B** | `custom_benchmark_engine.py`에서 Redis 사용 미확인(추정) |
| Phase 6 Chain Sight 데이터 의존 | **B** | 로직은 완전, 데이터 채우기 chain_sight 의존 |
| execute_peer_filter 필터 타입 | **B** | Metric 필터 완전, Chain Sight 속성 필터 부분/폴백 추정 |
| thematic "(beta)" UI 표시 | **C** | `is_active=False` FE 처리 미확인 |
| Thesis Control 연동(Phase 7) | **C** | thesis 모델 필드/API 연동 미확인 |
| 대화형 LLM 필터 UI(Phase 7) | **C** | FE 대화형 UI 미확인 |
| 과거 peer 이력 관리 | **C** | 설계도 "1인 개발 감당 불가" 명시, UI 고지만 |
| handling_mode='special' gray 표시 | **C** | 시드 존재, API 응답 gray 신호 미확인 |
| 성장 추세 비교(자사 vs 업종 median) | **C** | LeaderComparisonView 구현 미확인 |
| 밸류에이션 "보조" 접힘 표시 | **C** | FE 마크업 미확인 |

### 부분/미구현/대체 항목 상세
- **B1 L1/L2 네비게이션**: query param 방식(`?tab=validation`) 계획, 라우팅·탭 상태 관리 구조 미검증.
- **B2 모바일 Accordion**: 모바일 1개씩 펼침 / 데스크톱 전체 펼침 분기 완전성 미확인.
- **B3 Empty States**: 배치 미실행/부분데이터/개별null/S&P500외/특수산업 5케이스별 UI 미확인.
- **B4 Redis 캐싱**: 설계 §6 "Redis TTL 1h", 코드상 Redis 미확인 → 메모리/DB 캐싱 대체 추정.
- **B5 Phase 6 데이터 의존**: `CompanyGrowthStage`/`CompanyCapitalDNA` 참조하나 실제 레코드 채우기는 chain_sight. 완료보고서는 "463/503 종목 thematic 프리셋 생성" 성공 보고.
- **B6 execute_peer_filter**: `parse_filter_with_llm` 완전, 실행 엔진은 `MetricSnapshot` 필터 중심 — `foreign_revenue_pct`·`rd_to_revenue` 등 Chain Sight 속성 필터 부분/폴백 추정.

### task_done ↔ 코드 불일치 발견 사항
1. **peer_phase6_thematic.md** (2026-04-04): "463/503 종목 생성, 전체 2,282 프리셋" ↔ `preset_generator.py:425-499` `_generate_thematic()` 완전 구현으로 **일치**. 표현 차이만(보고서 "비즈니스 DNA" vs 코드 주석 "Chain Sight 기반").
2. **peer_phase7_llm_filter.md** (2026-04-04): "지원 필터 11항목" ↔ 파싱 프롬프트는 전체 정의(`llm_peer_filter.py:19-53`)하나 실행 엔진은 Metric 중심 → **부분 불일치**. 보고서 자체도 "metric 데이터 한계로 0개 결과" 자인.
3. **5년 차트 peer band**: 설계 §3.2 "현재 시점 peer로 과거도 계산 + UI 고지" ↔ 과거 peer 이력 관리 코드 미확인. 설계가 한계를 명시한 부분.
4. **마이그레이션 번호**: PR prompts 순서(BE-PR-1~6)와 실제 migration 0001~0004 번호 불일치하나 대략 순서 준수.
5. **category_score → category_signal 리네임**: 설계 §7.1 변경 ↔ 클래스 `CategorySignal`, `db_table="validation_category_signal"` **일치**.

> **종합 평가**: Phase 1~5 ≈95%, Phase 6 ≈85%(데이터 의존), Phase 7 ≈70%(실행 엔진·연동 미완), FE 고도화 ≈80%. 최대 부채는 (1) Chain Sight 데이터 파이프라인 미완으로 인한 고급 필터 선택적 작동, (2) Thesis Control 미연동, (3) FE 반응형/edge case, (4) Redis 캐싱 전략 미확인.

---

## News 상세

> ⚠️ **완료보고서 부재**: `docs/news/`에 `task_done`/summary 없음 — 설계 문서 3종(`plan/news_pipeline_monitoring_design.md`, `keyword_detail_bottomsheet_v2.md`, `news_keyword_detail_plan.md`)만 존재. 따라서 **코드 존재 여부로만 판정**(cross-ref 불가).

### 구현률 요약
- (A) 31 · (B) 3 · (C) 1 · (D) 0 → **35개 요소 중 31개 완전 구현(~89%)**
- Phase A(모니터링 대시보드 + 키워드 상세 바텀시트) ≈95%, Phase B(심화 모니터링) ≈80%, Phase C(알림)는 모델/API/UI 완비 but **자동 감지 엔진(Celery 태스크) 미구현**.

### 기능별 분류 표 (요약)
| 영역 | 기능 | 분류 | 근거 |
|------|------|------|------|
| Phase A BE | collection-logs / pipeline-health / ml-trend / llm-usage / keyword-detail API | A | `services/news/api/views.py:1410-1529 / 1536-1903 / 1910-1994 / 2001-2124 / 676-852` |
| Phase A FE | PipelineStatusBar·CollectionStatsTable·MLModelCard·MLTrendChart·RecentErrorsList·LLMUsageSummary·KeywordDetailSheet | A | `frontend/components/admin/news/*.tsx`, `components/news/KeywordDetailSheet.tsx` |
| Phase A 인프라 | NewsTab sub-tab·NewsPipelineSubTab·useNewsPipeline·newsPipelineService | A | `frontend/components/admin/NewsTab.tsx:10-17`, `hooks/useNewsPipeline.ts`, `services/newsPipelineService.ts` |
| Phase B BE | task-timeline / neo4j-status / ml-rollback-preview / ml-rollback API | A | `api/views.py:2133-2194 / 2201-2268 / 2275-2317 / 2324-2368` |
| Phase B FE | Neo4jStatusCard + hooks (timeline/neo4j/rollback) | A | `frontend/components/admin/news/Neo4jStatusCard.tsx`, `hooks/useNewsPipeline.ts:53-93` |
| Phase B FE | **TaskTimelineChart** | **B** | `TaskTimelineChart.tsx` — 시간축 막대만, 15분 버킷·병렬 y축 스택 미완 |
| Phase B FE | **MLCompareView** | **B** | `MLCompareView.tsx` — 기본 비교 OK, Feature Importance 히트맵 미구현 |
| Phase C BE | AlertLog 모델·alerts GET·alerts_resolve POST·migration | A | `models.py:553-599`, `api/views.py:2377-2493`, `migrations/0006_alertlog.py` |
| Phase C FE | AlertBadge·AlertList·useAlerts·useResolveAlert | A | `frontend/components/admin/news/Alert*.tsx`, `hooks/useNewsPipeline.ts:95-125` |
| Phase C 엔진 | **check_pipeline_alerts Celery 태스크** | **C** | 미구현. 설계 §6의 7트리거 자동 감지 + Beat 30분 주기 없음 |
| Phase 0 | _log_collection() 호출 보강 | A(부분) | `tasks.py:179,230,543,591,674…` — 단 `sync_news_to_neo4j` 호출 미확인 |
| 키워드 | search_terms_en 필드 | **B** | JSONField라 스키마 유연, `keyword_extractor` 프롬프트 추가 여부 미검증 |

### 부분/미구현/대체 항목 상세
- **TaskTimelineChart (B)**: 설계 §5.1 간트(15분 버킷, 태스크별 y축 스택, 성공/에러/실패 색상) ↔ 실제는 단순 시간축 막대. **병렬 실행 시각화 핵심 미완**.
- **MLCompareView (B)**: 설계 §5.3 Feature Importance 히트맵(5특성×N주) ↔ 텍스트 테이블만. 시간 차원 변화 표현 불가.
- **check_pipeline_alerts (C)**: 설계 §6 7개 트리거(태스크 연속실패/ML F1급락/키워드추출실패/LLM에러율/Neo4j연결실패/수집량급감/미분류누적) 자동 감지 + Beat 30분 + AlertLog 자동 저장. **AlertLog는 저장소일 뿐, 감지 엔진 부재 → 현재 수동 생성/해결만 가능.** 설계서에 "@infra 협업 필요" 표기 → 인프라 담당 대기 상태 추정.
- **search_terms_en (B 추정)**: `models.py:317-327` `keywords` JSONField. 키 추가 여부는 추출기 로직 의존, 미검증.
- **sync_news_to_neo4j 로깅 (경미)**: Phase 0 보강 대상 중 해당 태스크 `_log_collection()` 호출만 확인 안 됨.

### 설계 ↔ 코드 불일치 / 완료보고서 부재 사항
- **완료보고서 전무**: `docs/news/`에 진행/완료 보고 없음 → 향후 추적성 부채.
- 다음 항목은 설계와 **정확히 일치** 확인됨(positive):
  - collection-logs 응답 구조(`views.py:1515-1523`), pipeline-health 평일/주말 62h 면제(`1596-1610`), llm-usage 경고 배너(`2116-2119` + `LLMUsageSummary.tsx`), ml-rollback 2단계(preview→confirm, `2276-2368`), AlertLog TriggerType 7종(`models.py:562-569`), KeywordDetailSheet v2 가로 스크롤 Strip(`KeywordDetailSheet.tsx:59-130`), KST 자정 기준 처리(`views.py:45-52, 1438-1441`).

---

## 부록: 종합 후속 권고 (감사 의견, 비강제)

| 우선순위 | 앱 | 항목 | 사유 |
|---------|----|----|------|
| 高 | News | `check_pipeline_alerts` Celery 태스크 구현(@infra) | 알림 저장소·UI는 완비, 감지 엔진만 비어 모니터링 가치 절반 미실현 |
| 高 | Validation | Phase 7 execute_peer_filter Chain Sight 속성 필터 + 데이터 파이프라인 | 보고서 자인 "metric 한계로 0개 결과" — 핵심 기능 실효성 문제 |
| 中 | Validation | Thesis Control 연동 / 대화형 LLM UI | Phase 7 설계 미완 잔여 |
| 中 | Validation | FE edge case(Empty States 5종·모바일 Accordion·L1/L2 라우팅) 직접 검증 | "미확인" 기반 보수적 B/C — 실제 상태 확정 필요 |
| 中 | News | TaskTimelineChart 간트 병렬화 / MLCompareView 히트맵 | Phase B 고급 시각화 완성도 |
| 低 | News | `docs/news/` 완료보고서 작성 | 추적성 부채 해소 |
| 低 | SEC | Celery Beat 운영 활성화 시점 결정 | 주석 → 활성화는 운영 판단 |

> 본 감사는 읽기 전용이며 코드를 일절 수정하지 않았다. B/"미확인"/"추정" 표기 항목은 후속 조치 전 해당 파일 직접 확인을 전제로 한다.
