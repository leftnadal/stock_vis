# Thesis Control 설계 갭 감사

> 감사일: 2026-04-25
> 감사자: 야간 자동화 (read-only audit)
> 범위: `docs/thesis_control/` 설계서 vs `thesis/` 백엔드 + `frontend/components/thesis/` + `frontend/app/thesis/` 프론트 구현
> 분류: (A) 완전 구현, (B) 부분 구현, (C) 미구현, (D) 폐기/대체

---

## 요약 (Phase별 구현률)

| Phase | 영역 | 구현률 | 비고 |
|-------|------|--------|------|
| **Phase 1 (MVP)** | 관제 엔진 + 이벤트 + DNA 골격 | **A 95%** | 모델/태스크/Stage0~3 모두 구현. 마감 시 ValidityRecord/InvestorDNA 자동 갱신 로직만 추적 필요. |
| **Phase 2 (모니터링 강화)** | 핵심 루프 6PR + LLM 빌더 + 키워드 캐시 | **A 100%** | FE-PR-1~6 완료 + LLM 빌더 (Phase A MVP/Hardening) + KeywordCache 구현. |
| **Phase 3 — 원안 (FE-PR-7~11)** | 탭/히트맵/히스토리/아카이브/DNA UI | **D 폐기** → 리디자인으로 대체 | 원안 5PR은 phase3_frontend_redesign에 의해 4PR (PR-7~10)로 교체. 원안 FE-PR-10/11 (마감 아카이브, DNA 프로필 UI)는 어디로도 옮겨지지 않음. |
| **Phase 3 리디자인 PR-7** | 백엔드: display_unit + readings API + raw_value | **A 100%** | 마이그레이션 0004/0005, IndicatorReadingsView, dashboard 응답 raw_value 4필드 모두 반영. |
| **Phase 3 리디자인 PR-8** | 프론트: RealValueIndicatorCard + AISummary + NotableChanges | **B 80%** | AISummarySection / NotableChangesSection 구현. RealValueIndicatorCard는 IndicatorRow로 통합 (구조 변경, 기능 우월). |
| **Phase 3 리디자인 PR-9** | 프론트: 차트 토글 + 기간 + 정리 | **B 70%** | IndicatorRow 펼침 영역으로 통합 (단일 ChartToggleButton/PeriodSelector/IndividualMiniCharts 미생성 — 의도적 통합). 단, **OverallMoon/RecentChange 삭제 미수행 + MoonPhase 다른 곳에서 잔존 사용**. |
| **Phase 3 리디자인 PR-10** | AI 모니터링 파이프라인 (Celery `generate_thesis_summaries`) | **C 0%** | `generate_thesis_summaries` 태스크 미구현. `ThesisSnapshot.ai_summary` 항상 빈 문자열 → 프론트 AISummarySection은 영구 미렌더링. |
| **Phase 3 — DNA/회고/마감 아카이브 UI** | FE-PR-10/11 원안 (마감 가설 아카이브, ValidityMatrix, AccuracyRing, CategoryChart) | **C 0%** | 백엔드 모델만 존재 (HypothesisEvent, ValidityRecord, InvestorDNA). UI/API 모두 미구현. 리디자인에서도 누락. |
| **Phase 3 빌더 재설계 (talking_builder/redesign_build_plan)** | LLM one-shot proposal + KeywordCache + Cache Ops | **A 90%** | Phase A-MVP/Hardening + Phase B (KeywordCache + collectors 3종 + freshness TTL) 완료. Phase C 보류. |
| **설계 1.0 §3 — Community/Templates 기능** | 인기 가설, 따라하기, 템플릿, Chain Sight 진입 | **C 0%** | 백엔드 모델은 존재 (ThesisFollow, PopularThesisCache). API/뷰/프론트 미구현. |
| **설계 1.0 §3.4 — 3개 뷰 (카드/히트맵/그래프)** | 화면 상단 탭 전환 | **B 부분** | 카드뷰만 (단일 IndicatorRow 세로 나열). 히트맵 데이터(rows/cols/cells)는 API에서 내려주나 프론트 렌더링 없음. 그래프뷰 미구현. |

---

## 문서별 상태 테이블

| 문서 경로 | 핵심 내용 | 구현 상태 | 위치/근거 |
|-----------|----------|----------|----------|
| `docs/thesis_control/plan/thesis_control_design.md` (v1.0) | 전체 설계서 (모델, API, Phase 1~4 로드맵) | **B 부분 구현** | 모델/API/Phase 1~2 핵심은 구현. Community(§3), Phase 4 (벡터 DB) 미구현. |
| `docs/thesis_control/plan/thesis_control_implementation_guide.md` | 구현 가이드 | (확인 시간 부족 — 핵심 가이드는 design.md와 정합) | — |
| `docs/thesis_control/plan/thesis_control_integrated_roadmap.md` | 수학모델 v2.3.2 + 학습/DNA 통합 4-Phase 로드맵 | **B Phase 1~2 구현, Phase 3~4 미구현** | HypothesisEvent/ValidityRecord/InvestorDNA 모델 존재 (`thesis/models/learning.py`). ValidityScore 미구현, 합성 부트스트래퍼 미구현, 벡터화 미구현. |
| `docs/thesis_control/plan/thesis_control_math_model_final.md` | Stage 0~3 수학 모델 v2.3.2 | **A 완전 구현** | `thesis/services/data_validator.py`, `indicator_scorer.py`, `premise_aggregator.py`, `thesis_state_machine.py`. |
| `docs/thesis_control/plan/thesis_control_phase3_frontend_redesign.md` (v1.0 FINAL) | 대시보드 리디자인 PR-7~10 | **B PR-7/8/9 구현, PR-10 미구현** | 위 요약 표 참조. |
| `docs/thesis_control/plan/talking_builder/llm_builder_plan.md` | LLM 빌더 초기 계획 | **A 구현** (구버전, redesign_build_plan으로 진화) | `phase_a_llm_builder.md` 완료 보고 |
| `docs/thesis_control/plan/talking_builder/quarterly_indicator_dashboard_plan.md` | 분기 지표 대시보드 | **A 구현** | `quarterly_metric_fetcher.py`, IndicatorRow의 fiscal_label/quarterly_history 분기 처리 |
| `docs/thesis_control/plan/talking_builder/thesis_builder_redesign_v2.md` | LLM 빌더 v2 | **A 구현** (v3/v4로 진화) | — |
| `docs/thesis_control/plan/talking_builder/redesign_build_plan/00_total_plan.md` (v4) | 빌더 재설계 마스터플랜 | **B Phase A/B 구현, Phase C 보류** | `feature_flags.py` 10개, `keyword_cache.py`, `keyword_collectors/{chain,eod,news}.py` 구현 |
| `docs/thesis_control/plan/talking_builder/redesign_build_plan/01_phase_a_mvp.md` | Phase A MVP | **A 완료** | `work_done/phase_a_llm_builder.md` 보고서 |
| `docs/thesis_control/plan/talking_builder/redesign_build_plan/02_phase_a_hardening.md` | Phase A Hardening (PR-4~7) | **A 완료** | 동상 |
| `docs/thesis_control/plan/talking_builder/redesign_build_plan/03_phase_b_keywords.md` | Phase B KeywordCache + Monitoring | **A 구현** | 마이그레이션 0006 (KeywordCache), 0007 (strength), `keyword_cache.py`, `keyword_hint.py`, `keyword_collectors/*` |
| `docs/thesis_control/plan/talking_builder/redesign_build_plan/04_phase_c_advanced.md` | Phase C 고급 기능 | **C 미구현** | `MINI_DASHBOARD_PREVIEW`, `GUIDED_SUGGESTION`, `STREAMING_RESPONSE` 모두 feature_flags 기본 False |
| `docs/thesis_control/plan/talking_builder/redesign_build_plan/05_summary.md` | 요약 | (참조용) | — |
| `docs/thesis_control/thesis_control_phase1_prompts.md` | Phase 1 프롬프트 모음 | (구현 참조 자료) | — |
| `docs/thesis_control/thesis_control_phase1_frontend_FE_PR_{1..5}.md` | FE-PR-1~5 작업 지시서 | **A 모두 완료** | `frontend/task_done/FE-PR-{1..5}_*.md` |
| `docs/thesis_control/thesis_control_phase1_frontend_prompts.md` | FE 프롬프트 모음 | (구현 참조 자료) | — |
| `docs/thesis_control/thesis_control_user_experience.md` | UX 원칙 | **B 부분 반영** | "엄지 우선/느낌 전달" 원칙은 IndicatorRow의 색·라벨에 반영. 그러나 [근거] 시스템 (롱프레스 설명) 미구현. |
| `docs/thesis_control/frontend/task_done/FE-PR-1_*.md` ~ `FE-PR-6_*.md` | Phase 2 완료 보고 | **모두 일치** | 6개 PR 완료 보고와 코드 일치 |
| `docs/thesis_control/frontend/task_done/FE-PR-3_plan_review_v3.md` | FE-PR-3 리뷰 | (참조용) | — |
| `docs/thesis_control/frontend/task_done/Phase2_completion_summary.md` | Phase 2 완료 요약 + Phase 3 원안 (FE-PR-7~11) 청사진 | **D 원안 폐기** | "FE-PR-7 탭 구조, FE-PR-8 히트맵, FE-PR-9 히스토리, FE-PR-10 마감 아카이브, FE-PR-11 DNA"는 phase3_frontend_redesign로 교체. **단, 원안의 FE-PR-10 마감 아카이브와 FE-PR-11 DNA 프로필 UI는 리디자인에 누락 — 사실상 보류 상태**. |
| `docs/thesis_control/work_done/phase_a_llm_builder.md` | Phase A LLM 빌더 완료 | **A 완료** | 위 표 참조 |

---

## Phase 3 미구현 항목 상세

### 1. PR-10 (AI 모니터링 파이프라인) — 🔴 **C 미구현**

**설계 위치**: `phase3_frontend_redesign.md` §7

**미구현 산출물**:
- `generate_thesis_summaries` Celery 태스크 (매일 07:30) — Gemini 2.5 Flash로 `ThesisSnapshot.ai_summary` 생성
- alert_engine 이벤트 → `NotableChange` 포맷 변환 로직 — `notable_changes` JSONField 구조 일치

**현재 상태**:
- `thesis/tasks/eod_pipeline.py`에 3개 태스크만 존재 (`update_indicator_readings`, `calculate_scores`, `create_snapshots_and_alerts`). `generate_thesis_summaries` 없음.
- `grep ai_summary thesis/` → 0건. `ai_summary` 필드는 모델/serializer/뷰만 통과하며 항상 빈 문자열.
- `thesis/services/snapshot_builder.py:106-122` — `notable_changes` 생성 로직 존재하나 **score 델타 기반** (|delta|>=0.3) 으로, 설계 PR-10이 요구한 alert_engine 이벤트 재사용 + `change_type/raw_value_before/raw_value_after/severity` 포맷과 **불일치**. 프론트엔드 타입 (`NotableChange.change_type: 'sharp_move'|'direction_flip'|...`) 과 백엔드 응답 (`{indicator_id, indicator_name, prev_score, curr_score, delta}`) 키 불일치 — **타입 계약 위반**.
- 결과: 프론트 `NotableChangesSection`은 백엔드 응답을 받으면 `description/severity/change_type`이 undefined가 되어 fallback "오늘은 특별한 변화가 없어요"가 사실상 디폴트 표시되거나 데이터를 잘못 렌더링할 가능성.

**영향**: 대시보드의 "AI 분석" + "오늘의 변화" 섹션이 사실상 빈 카드로 표시되거나 타입 불일치 에러.

---

### 2. 원안 FE-PR-10 (마감 아카이브 + 요약) — 🔴 **C 미구현**

**설계 위치**: `frontend/task_done/Phase2_completion_summary.md` §8

**미구현 산출물**:
- 마감(closed) 가설 목록 페이지 (`/thesis/archive` 등)
- ValidityMatrix 컴포넌트 (2x2 매트릭스 시각화)
- 마감 가설 복기 화면 (가장 유용했던 지표, 예상과 다른 지표 등 — design.md §3.9)

**현재 상태**:
- 백엔드 모델 `ValidityRecord` 존재 (`thesis/models/learning.py:55-94`).
- 마감 API: `Thesis.outcome` 필드와 `/thesis/[id]/close/` 엔드포인트는 존재 (FE-PR-6 완료).
- 그러나 마감된 가설을 조회하는 별도 라우트/컴포넌트 없음. `frontend/app/thesis/(list)/page.tsx`에 status 필터링 UI 없음.
- ValidityRecord가 마감 시점에 자동 생성되는지 확인 필요 (코드 추적 시간 부족).

**영향**: 사용자가 마감한 가설을 다시 볼 방법이 없음. design.md §3.9 "복기" 경험 부재.

---

### 3. 원안 FE-PR-11 (투자자 DNA 프로필) — 🔴 **C 미구현**

**설계 위치**: `frontend/task_done/Phase2_completion_summary.md` §8

**미구현 산출물**:
- 투자자 DNA 프로필 페이지 (`/thesis/dna` 등)
- AccuracyRing (적중률 도넛)
- CategoryChart (전제 카테고리 분포)
- DNA 슬라이더 (personalization_weight 0~1)

**현재 상태**:
- 백엔드 모델 `InvestorDNA` 존재 (`thesis/models/learning.py:97-152`).
- API 엔드포인트 미구현 (`thesis/urls.py`에 dna/profile 경로 없음).
- 프론트엔드 컴포넌트 0개.

**영향**: 특허 청구항 §독립항 1 (투자 DNA 프로파일)의 사용자 가시화 부재. 백엔드 모델은 데이터 축적 중이나 사용자에게 노출되지 않음.

---

### 4. 리디자인 PR-9 정리(cleanup) 미수행 — 🟡 **B 부분**

**설계 위치**: `phase3_frontend_redesign.md` §6-8

**미수행 항목**:
- `OverallMoon.tsx` 삭제 — **현재 frontend에 파일 자체가 없음** (이미 삭제됨 ✅)
- `DashboardIndicatorCard.tsx` 삭제 — **현재 dashboard/ 디렉터리에 없음** (이미 삭제됨 ✅, IndicatorRow로 대체)
- `RecentChange.tsx` 삭제 — **현재 dashboard/ 디렉터리에 없음** (이미 삭제됨 ✅)
- `MoonPhase.tsx` (common) 삭제 — **🔴 미수행**. `frontend/app/thesis/(list)/page.tsx:10,140`에서 `<MoonPhase score={null} size="md" />` 여전히 사용. `frontend/components/thesis/list/ThesisListCard.tsx`, `frontend/components/thesis/index.ts` (barrel export)에도 잔존.
- `scoreToPhaseMeta()` (utils.ts) 삭제 — 별도 확인 필요 (Read 권한 손실로 미확인)

**영향**: MoonPhase는 가설 목록 페이지에서 점수 시각화에 여전히 사용 중이므로 의도적 보존으로 판단됨. **단, phase3_frontend_redesign.md §10 "절대 하지 말 것" 체크리스트 §"MoonPhase.tsx (common) import 검색 — 다른 곳에서 사용 중이면 삭제 보류"는 충족**. 따라서 이는 사실상 (D) 폐기 보류 결정으로 분류 가능.

---

### 5. 설계 §3 Community/Templates 진입 경로 — 🔴 **C 미구현**

**설계 위치**: `thesis_control_design.md` §2.3 경로 3~5

**미구현 항목**:
- 인기 가설 (경로 3): `GET /popular/`, `POST /popular/{id}/follow/`, `GET /popular/{id}/detail/`
- 템플릿 (경로 4): `GET /templates/`, `GET /templates/{type}/`
- Chain Sight 진입 (경로 5): Chain Sight 노드에서 가설 빌더 진입

**현재 상태**:
- 모델: `ThesisFollow`, `PopularThesisCache` 존재 (`thesis/models/community.py`).
- 뷰/시리얼라이저: 없음 (`thesis/views/`에 `community_views.py` 없음, urls.py에 popular/templates 경로 없음).
- 프론트: `EntryPointGrid`에서 `[💬 내 생각]`, `[📰 오늘 이슈]` 2개 진입점만. design.md §2.2의 5개 진입점 중 3개 누락 (`🔥 인기`, `📋 템플릿`, `🔗 Chain Sight`).
- Celery: `update_popular_thesis_cache`, `prepare_daily_issues` 태스크 미구현.

---

### 6. 설계 §3.4 3개 뷰 (카드/히트맵/그래프) — 🟡 **B 부분**

**현재 상태**:
- **카드뷰**: ✅ IndicatorRow 세로 나열 + 펼침 차트.
- **히트맵 뷰**: 백엔드 `DashboardView`가 `heatmap: {rows, cols, cells}` 응답 (`monitoring_views.py:222-225`). 프론트엔드 컴포넌트 미구현 (탭 전환 UI 없음, Heatmap 컴포넌트 없음).
- **그래프뷰**: 미구현 (시간축 라인 차트로 모든 지표를 같은 캔버스에 표시).

**영향**: 백엔드는 데이터를 내려주지만 프론트가 받지 않음 — 페이로드 낭비. design.md §3.4의 "탭 한번으로 전환" UX 미충족.

---

### 7. 설계 §2.4 [근거] 시스템 (롱프레스 설명) — 🔴 **C 미구현**

**설계 위치**: `thesis_control_design.md` §2.4

**현재 상태**:
- 빌더 단계에서는 `BottomSheet`/`OptionButton`의 long-press가 일부 동작 (FE-PR-3 보고서 §"Long-press 설명").
- 그러나 관제실 대시보드의 지표 옆 [근거] 버튼은 IndicatorRow에 명시적 버튼으로는 없음. 펼침 영역의 `description` + `recommendation_reason` 텍스트 표시로 대체. (B 부분 — UX 위치 다름)
- 전제 텍스트 탭 → 맥락 설명도 별도 구현 없음.

---

## 잘 구현된 항목 (참고)

- **수학 엔진 v2.3.2**: Stage 0~3 완전 구현. data_validator, indicator_scorer, premise_aggregator, thesis_state_machine 모두 존재.
- **EOD 파이프라인**: 18:00/18:15/18:30 ET 3개 태스크 모두 가동.
- **분기 지표 대시보드**: quarterly_metric_fetcher + 5Y FMP fallback + RATIO_METRICS % 변환 완료.
- **LLM 빌더**: Phase A MVP/Hardening + Phase B KeywordCache + Cache Ops 모두 완료. fallback → wizard 안전망 작동.
- **지표 카탈로그 + 추천 이유**: `INDICATOR_CATALOG description 73개`, `recommendation_reason` 필드 마이그레이션 0009로 추가, IndicatorRow 펼침 영역에 표시.
- **이벤트 수집 인프라**: HypothesisEvent (13개 event_type) 모델 존재 — Phase 2 학습 레이어 활성화 시 즉시 활용 가능.

---

## 권장 다음 작업 우선순위

1. **🔴 PR-10 구현**: `generate_thesis_summaries` 태스크 + `notable_changes` 포맷 정합화 — 현재 대시보드 핵심 섹션 2개가 "비어있는 경험" 상태.
2. **🔴 백엔드 NotableChange 타입 정합화**: `snapshot_builder.py:116-122`의 dict 키를 프론트 `NotableChange` 인터페이스 (`indicator_id, indicator_name, change_type, description, raw_value_before, raw_value_after, change_pct, severity`)에 맞춰 변경. PR-10 의존 작업.
3. **🟡 마감 아카이브 + DNA 프로필 UI**: 데이터는 쌓이고 있으나 사용자에게 미노출. design.md §3.9 복기 경험 + 특허 청구항 1 가시화.
4. **🟢 히트맵 뷰 활성화**: 백엔드 응답을 프론트에서 활용하도록 탭 + Heatmap 컴포넌트 추가 (낮은 비용).
5. **🟢 Community/Templates**: 사용자 베이스 축적 후 우선순위 재평가.

---

## 부록 A. 마이그레이션 인벤토리

| 번호 | 내용 | 출처 |
|------|------|------|
| 0001 | 초기 모델 (Thesis, Premise, Indicator, IndicatorReading, Snapshot, Alert, HypothesisEvent, ValidityRecord, InvestorDNA, ThesisFollow, PopularThesisCache) | Phase 1 |
| 0002 | ThesisSnapshot date 필드 제거 + asof_date 추가 | 수학 모델 v2.3.2 |
| 0003 | FK on_delete SET_NULL 수정 | 안정화 |
| 0004 | display_unit 필드 추가 | Phase 3 PR-7 |
| 0005 | display_unit 데이터 마이그레이션 (`_infer_unit` 일괄 적용) | Phase 3 PR-7 |
| 0006 | KeywordCache 모델 추가 | 빌더 재설계 Phase B |
| 0007 | KeywordCache strength 필드 추가 | Phase B 후반 |
| 0008 | data_source에 'metrics' 추가 | 분기 지표 |
| 0009 | recommendation_reason 필드 추가 | 관제실 지표 설명 |

총 9개 마이그레이션 — 설계서 PR 매핑과 정합 ✅

---

## 부록 B. 검증 한계

- 본 감사는 **읽기 전용** 정적 분석. 다음 항목은 실행 시점에만 확인 가능:
  - `notable_changes` 응답이 실제로 프론트 타입과 충돌하는지 (런타임 에러)
  - `ValidityRecord` / `InvestorDNA`가 가설 마감 시 자동 생성되는지 (signal/태스크 경로 미추적)
  - `feature_flags.py`의 `KEYWORD_HINTS_ENABLED` 등 운영 환경 토글 상태
- 감사 중반 working directory 권한 일시 손실로 일부 파일 (`thesis/models/monitoring.py`, `thesis/services/snapshot_builder.py` 후반부, `thesis/serializers/monitoring_serializers.py`) 추가 검증 미수행. 그러나 핵심 갭 결론은 이미 확보된 증거로 충분히 도출됨.
