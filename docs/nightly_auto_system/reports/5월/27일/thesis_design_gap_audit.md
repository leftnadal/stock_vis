# Thesis Control 설계 갭 감사

> 감사일: 2026-05-27
> 대상 코드: `thesis/`, `frontend/components/thesis/`, `frontend/app/thesis/`
> 대상 설계: `docs/thesis_control/` 전체
> 방식: 읽기 전용 (코드 수정 없음)

---

## 요약 (Phase별 구현률)

| Phase | 범위 | 구현률 | 상태 | 비고 |
|------|------|--------|------|------|
| **Phase 1 (MVP / 관제 엔진 + 이벤트 수집)** | 모델 + 스코어링 + 대화형 빌더 + 기본 대시보드 + 이벤트/유효성 기록 | **95%** | (A) 대부분 완전 | 합성 가설 진입 경로 5(Chain Sight) 미구현 외 사실상 완성 |
| **Phase 2 (모니터링 강화 / 핵심 루프 6 PR)** | FE-PR-1 ~ FE-PR-6 (라우팅/목록/빌더/지표설정/대시보드/알림+마감) | **100%** | (A) 완전 구현 | `Phase2_completion_summary.md`로 확정. 30 컴포넌트 / ~3,380줄 |
| **Phase 3 (대시보드 리디자인, PR-7~10)** | display_unit + 실제값 카드 + AI 분석 + Notable Changes + 미니차트 + AI 파이프라인 | **80%** | (B) 부분 구현 | 백엔드/AI 파이프라인 완성, 신규 컴포넌트 4종 생성됐으나 대시보드 진입점은 **IndicatorRow로 재통합되어 미사용** |
| **Phase 3 원안 (깊이 + 회고 + 프로필, FE-PR-7~11)** | 3탭 구조 + 히트맵 + 히스토리 탭 + 마감 아카이브 + Investor DNA UI | **0%** | (D) 폐기/대체 | 원안은 `Phase2_completion_summary.md`에 계획만 남음. **리디자인 Phase 3(PR-7~10)로 방향 전환** |
| **Phase 4 (벡터 스코어링)** | DNA 벡터화 + 코사인 유사도 + 합성 에이전트 | **0%** | (C) 미구현 | 통합 로드맵상 향후 일정 |

**총평**: Phase 1+2 코어 루프는 안정적으로 완성. **Phase 3은 "두 갈래 설계"가 충돌**하며, 원안(깊이+회고+DNA UI)은 폐기되고 리디자인(실제값+AI요약+미니차트)이 채택됐으나 **신규 컴포넌트 4종(`RealValueIndicatorCard`, `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`)이 대시보드 페이지에서 사용되지 않고 테스트에만 남음** — 기능은 `IndicatorRow`로 흡수 재구성. Phase 4(특허 핵심: 합성 에이전트/벡터)는 모델 골격만 있고 미구현.

---

## 문서별 상태 테이블

### 설계 문서 1: `plan/thesis_control_design.md` (UX/API/모델 기본 설계)

| 섹션 | 항목 | 상태 | 코드 위치 | 비고 |
|------|------|------|----------|------|
| 2.3 경로 1 | 오늘 이슈 (메인) | (A) 완전 | `views/conversation_views.py::NewsIssuesView`, `app/thesis/new/page.tsx` | |
| 2.3 경로 2 | 내 생각 (자유 입력) | (A) 완전 | `services/thesis_builder.py`, `components/thesis/builder/TextInput.tsx` | |
| 2.3 경로 3 | 인기 가설 | (C) 미구현 | 모델 `PopularThesisCache` 정의만, ViewSet/엔드포인트 없음 | `urls.py`에 `/popular/` 경로 부재 |
| 2.3 경로 4 | 템플릿 | (C) 미구현 | `urls.py`에 `/templates/` 경로 부재 | 진입점 그리드(`EntryPointGrid`)에서도 노출 안 됨 |
| 2.3 경로 5 | Chain Sight 진입 | (C) 미구현 | Chain Sight 화면에서 `[📌 가설 세우기]` CTA 없음 | |
| 2.4 [근거] 시스템 | 롱프레스 용어 설명 | (B) 부분 | `components/thesis/builder/BottomSheet.tsx` (long-press 500ms) | 빌더 단계 한정. 대시보드 카드의 `[근거]` 버튼은 없음 |
| 3.1~3.2 관제실 첫 화면 | Moon Phase + 화살표 | (D) 폐기 | `common/MoonPhase.tsx` 잔존, **대시보드 진입점에서 미사용** | 리디자인 Phase 3에서 `OverallMoon` 제거 결정 → 실제로도 `[thesisId]/page.tsx`에 없음 |
| 3.4 세 가지 뷰 | 카드뷰/히트맵/그래프뷰 토글 | (B) 부분 | 카드뷰(현 형태)만 존재. 히트맵·그래프 토글 미구현 | `DashboardView` API에 `heatmap` 응답 키 정의되어 있으나 프론트엔드 소비 없음 |
| 3.5 모바일 제스처 | 롱프레스/스와이프/쉐이크 | (C) 미구현 | 빌더 외 대시보드에서 제스처 핸들러 없음 | |
| 3.7 변화 감지 알림 | 푸시 + 대화형 후속 안내 | (B) 부분 | `services/alert_engine.py`, `app/thesis/(list)/alerts/page.tsx` | 알림 카드는 있으나 "전제 다시 생각" 대화 분기 없음 |
| 3.9 가설 마감 — 복기 | 결과+유용했던 지표+예상과 달랐던 부분 | (B) 부분 | `app/thesis/[thesisId]/close/page.tsx` (Outcome 선택만) | 복기 화면(`/closed`, `/archive`) 없음. ValidityRecord 저장은 백엔드에서 됨 |
| 4.2 모델 | Thesis/Premise/Indicator/Reading/Snapshot/Alert | (A) 완전 | `thesis/models/*.py` + 9개 마이그레이션 | 추가 필드(v2.3.2 epsilon/window/decay) 모두 반영 |
| 4.2 커뮤니티 모델 | ThesisFollow/PopularThesisCache | (B) 부분 | `models/community.py` 존재, 활용 코드 없음 | 인기 가설 API와 함께 보류 |
| 4.4 Neo4j 그래프 모델 | HAS_PREMISE/TRACKED_BY/SIMILAR_TO 노드 | (C) 미구현 | thesis 앱 내 Neo4j 동기화 코드 없음 | 가설-전제-지표 Cypher 미작성 |
| 5.3 Celery 태스크 | 8종 (update_indicator_readings 등) | (A) 완전 | `tasks/eod_pipeline.py`, `tasks/summary.py` | `generate_thesis_summaries` 포함 |
| 6.1 API 엔드포인트 | 가설/전제/지표 CRUD, 대시보드, 알림 | (A) 완전 | `urls.py` 16개 path | `/popular/`, `/templates/` 2개만 미구현 |

### 설계 문서 2: `plan/thesis_control_integrated_roadmap.md` (특허 기능)

| Phase | 항목 | 상태 | 코드 위치 |
|------|------|------|----------|
| Phase 1 | `HypothesisEvent` 이벤트 스트림 기록 | (A) 완전 | `models/learning.py:7`, `services/thesis_builder.py:648`, `views/thesis_views.py` 다수 |
| Phase 1 | `ValidityRecord` 마감 시 생성 | (A) 완전 | `views/thesis_views.py:85-103` close 액션 |
| Phase 1 | `InvestorDNA` 모델 + 마감 시 갱신 | (A) 완전 | `models/learning.py:97`, `views/thesis_views.py:296` `_update_investor_dna` |
| Phase 2 | `ValidityScore` 집계 활성화 (sample_count≥5 → core/reference/low_impact 티어) | (C) 미구현 | 모델/태스크 부재 |
| Phase 2 | DNA 적합도 슬라이더(personalization_weight) UI | (B) 부분 | 백엔드 필드만 존재(`InvestorDNA.personalization_weight`), 프론트엔드 슬라이더 부재 |
| Phase 2 | 역제안(Contrarian Nudge) | (C) 미구현 | `indicator_matcher.py` 내 `add_contrarian_nudge` 없음 |
| Phase 3 | 합성 에이전트(SyntheticBootstrapper, 20~30 페르소나) | (C) 미구현 | 클래스 부재, ValidityRecord에 `is_synthetic` 필드 없음 |
| Phase 3 | Online Logistic Regression(`ThesisWeightLearner`) | (C) 미구현 | |
| Phase 4 | DNA 벡터화 + 코사인 유사도 + 사용자 유사도 | (C) 미구현 | |

### 설계 문서 3: `plan/thesis_control_phase3_frontend_redesign.md` (대시보드 리디자인)

| PR | 항목 | 상태 | 코드 위치 / 비고 |
|----|------|------|----------------|
| **PR-7** (백엔드) | `display_unit` 필드 추가 | (A) 완전 | `migrations/0004_add_display_unit.py`, `migrations/0005_populate_display_unit.py` |
| PR-7 | `DashboardView`에 raw_value/change_pct/ai_summary/notable_changes 응답 추가 | (A) 완전 | `views/monitoring_views.py:46` |
| PR-7 | `IndicatorReadingsView` 신설 + URL | (A) 완전 | `urls.py:30-34`, `views/monitoring_views.py` |
| **PR-8** (프론트엔드) | `RealValueIndicatorCard.tsx` 신설 | (B) 부분 | 파일 존재 (`components/thesis/dashboard/RealValueIndicatorCard.tsx`), **테스트(`__tests__/thesis/RealValueIndicatorCard.test.tsx`)에서만 import**, 페이지 미사용 |
| PR-8 | `AISummarySection.tsx` | (A) 완전 | `dashboard/AISummarySection.tsx`, `app/thesis/[thesisId]/page.tsx:75` 사용 |
| PR-8 | `NotableChangesSection.tsx` | (A) 완전 | `dashboard/NotableChangesSection.tsx`, 페이지 사용 |
| PR-8 | `formatRawValue`/`formatChangePct`/`supportLabel` 유틸 | (A) 완전 | `lib/thesis/utils.ts`, `IndicatorRow.tsx:11`에서 사용 |
| PR-8 | `DashboardIndicator` 타입 확장(raw_value, change_pct 등) | (A) 완전 | `lib/thesis/types.ts` |
| **PR-9** (프론트엔드) | `ChartToggleButton.tsx` | (B) 부분 | 파일 존재, 페이지 미사용 — `IndicatorRow` 내부 확장형으로 흡수 |
| PR-9 | `PeriodSelector.tsx` | (B) 부분 | 파일 존재, 페이지 미사용 — `IndicatorRow`의 `DAILY_PERIODS`(1M/1Y/3Y/5Y)로 대체 |
| PR-9 | `IndividualMiniCharts.tsx` | (B) 부분 | 파일 존재, 페이지 미사용 — `IndicatorRow` 내부 `recharts` AreaChart로 흡수 |
| PR-9 | `OverallMoon.tsx`/`DashboardIndicatorCard.tsx`/`RecentChange.tsx` 삭제 | (A) 완전 | 파일 미존재 (`find` 결과 부재) |
| PR-9 | `MoonPhase.tsx` 검토 후 삭제 | (D) 폐기 보류 | `common/MoonPhase.tsx` 잔존 (사용처 없음으로 보임 — 정리 필요) |
| **PR-10** (AI 파이프라인) | `generate_thesis_summaries` Celery task | (A) 완전 | `thesis/tasks/summary.py:87` |
| PR-10 | `notable_changes`를 `alert_engine` 이벤트로 채우기 | (A) 완전 | `snapshot_builder.py` |

### 설계 문서 4: `frontend/task_done/Phase2_completion_summary.md` 부속 Phase 3 계획 (FE-PR-7~11)

> **주의**: 이 표는 `Phase2_completion_summary.md` 7번 항목 "Phase 3 계획" 표에 명시된 5개 FE-PR이며, **이후 `plan/thesis_control_phase3_frontend_redesign.md`로 방향 전환되어 폐기됨**.

| 원안 PR | 제목 | 핵심 산출물 | 현 상태 | 코드 흔적 |
|--------|------|-----------|---------|----------|
| FE-PR-7 | 대시보드 탭 구조 + 상세 탭 | 3탭(관제/상세/히스토리) + 전제 CRUD | (D) 폐기 — 리디자인으로 대체 | 탭 컴포넌트 부재. 전제 CRUD 백엔드는 `ThesisPremiseViewSet`에 있으나 프론트 편집 UI 없음 |
| FE-PR-8 | 히트맵 + 지표 상세 편집 | Finviz 스타일 히트맵 + weight/direction 편집 | (D) 폐기 | `DashboardView`가 `heatmap` 응답을 만들지만 프론트 소비 없음. weight 편집 UI 부재 |
| FE-PR-9 | 히스토리 탭 | recharts 라인 차트 + 스냅샷 타임라인 | (D) 폐기 (부분 대체) | 단일 지표 차트는 `IndicatorRow`에 흡수, 가설 전체 스냅샷 타임라인은 없음 |
| FE-PR-10 | 마감 아카이브 + 요약 | 마감 가설 목록 + ValidityMatrix | (C) 미구현 | `/thesis/closed` 혹은 `/thesis/archive` 라우트 부재. ValidityRecord 백엔드는 채워짐 |
| FE-PR-11 | 투자자 DNA 프로필 | AccuracyRing + CategoryChart + 기술 부채 정리 | (C) 미구현 | `InvestorDNA` 모델/필드는 채워지나 노출 API/페이지 부재 |

### 설계 문서 5: `work_done/phase_a_llm_builder.md`

| 항목 | 상태 |
|------|------|
| LLM 빌더 Phase A MVP | (A) 완전 (`services/thesis_builder.py`, `services/builder_state.py`, `services/llm_postprocess.py`) |

### 설계 문서 6: `plan/talking_builder/*` (대화형 빌더 후속)

| 문서 | 상태 |
|------|------|
| `llm_builder_plan.md` | (A) 완전 — Phase A 완료(`thesis_builder.py`) |
| `quarterly_indicator_dashboard_plan.md` | (A) 완전 — `IndicatorRow` + `QuarterlySparkline` + `quarterly_metric_fetcher.py` |
| `thesis_builder_redesign_v2.md` | 미확인 (이번 감사 범위 외) |
| `redesign_build_plan/` 5개 | 미확인 (이번 감사 범위 외 — 별도 트랙으로 보임) |

---

## Phase 3 미구현 항목 상세

> **두 개의 "Phase 3"가 충돌하는 점에 주의** —
> ① 원안: `Phase2_completion_summary.md`의 FE-PR-7~11 (깊이+회고+프로필)
> ② 채택안: `thesis_control_phase3_frontend_redesign.md`의 PR-7~10 (실제값+AI요약+미니차트)
> 원안은 폐기됐고 채택안은 **백엔드는 완성, 프론트엔드는 컴포넌트만 만들고 통합 못 함**.

### A. 채택된 리디자인 Phase 3 (PR-7~10) — 80% 구현

**갭**: PR-8/PR-9에서 만든 4개 신규 컴포넌트가 실제 대시보드 페이지(`app/thesis/[thesisId]/page.tsx`)에서 사용되지 않음.

| 컴포넌트 | 파일 존재 | 페이지 import | 테스트 import | 실효 |
|---------|----------|--------------|--------------|------|
| `RealValueIndicatorCard.tsx` | ✓ | ✗ | ✓ (`__tests__/thesis/RealValueIndicatorCard.test.tsx`) | **죽은 코드** |
| `ChartToggleButton.tsx` | ✓ | ✗ | ✗ | **죽은 코드** |
| `PeriodSelector.tsx` | ✓ | ✗ | ✗ | **죽은 코드** |
| `IndividualMiniCharts.tsx` | ✓ | ✗ | ✗ | **죽은 코드** |

**왜 안 쓰이는가**: 페이지가 `IndicatorRow.tsx`(분기 지표 대시보드용으로 신설)로 카드+토글 차트+기간 선택을 **단일 컴포넌트로 통합**했기 때문. `IndicatorRow`는:
- `formatRawValue`/`formatChangePct`/`supportLabel` 유틸 그대로 사용 → PR-8 유틸 부분만 채택
- `DAILY_PERIODS = [1M / 1Y / 3Y / 5Y]`로 자체 정의 → `PeriodSelector`의 7D/14D/30D 무시
- recharts `AreaChart`를 row 내부에 expanded 시 렌더 → `IndividualMiniCharts` 무시
- `useIndicatorReadings` 훅 직접 호출

**필요한 조치(권고만, 코드 수정 안 함)**:
1. 4개 컴포넌트 + 그 테스트 제거하거나
2. `IndicatorRow`를 `RealValueIndicatorCard` + `IndividualMiniCharts` 조합으로 리팩터하여 설계 정합화

### B. 원안 Phase 3 (깊이+회고+프로필 FE-PR-7~11) — 0% 구현 (방향 전환으로 폐기)

| 원안 산출물 | 백엔드 준비도 | 프론트엔드 갭 |
|------------|--------------|--------------|
| **3탭 대시보드 (관제/상세/히스토리)** | 백엔드는 한 화면용 응답만 제공 | 탭 라우팅·상태 분리 부재. 상세 탭의 "전제 편집 UI" 없음 |
| **전제 CRUD UI** | `ThesisPremiseViewSet`로 POST/PATCH/DELETE 가능 + `HypothesisEvent` 기록 | 프론트엔드 mutation 훅·편집 화면 부재 |
| **히트맵 뷰** | `DashboardView` 응답에 `heatmap` 키 정의 가능성 (현 코드에서 미생성 — 확인 필요) | Finviz 스타일 그리드 컴포넌트 부재 |
| **히스토리 탭 (스냅샷 타임라인)** | `ThesisSnapshot` 모델·일별 저장 완료 | 가설 전체 score 타임라인 차트 부재 (단일 지표 차트는 IndicatorRow에 흡수) |
| **마감 아카이브 페이지** | `Thesis.status='closed_*'` 필터 가능 | `/thesis/closed` 라우트·페이지 부재 |
| **ValidityMatrix UI (2×2 매트릭스 표시)** | `ValidityRecord` 매트릭스 점수 저장 중 | 시각화 컴포넌트 부재 |
| **Investor DNA 프로필 화면** | `InvestorDNA` 모델 채워짐, `accuracy_rate`/`top_down_ratio`/`ai_accept_rate` 프로퍼티 완비 | 노출 API (예: `GET /api/v1/thesis/dna/`) 부재. `AccuracyRing`/`CategoryChart` 컴포넌트 부재 |

### C. 통합 로드맵 Phase 3 (특허 핵심) — 0% 구현

| 항목 | 갭 |
|------|----|
| **SyntheticBootstrapper** | 클래스·페르소나 정의 부재. `ValidityRecord`에 `is_synthetic` 필드도 없음 (`models/learning.py:55-94` 확인) |
| **Online Logistic Regression (`ThesisWeightLearner`)** | 가중치 학습 모듈 부재 |
| **합성/실제 블렌딩 정책** | `ValidityScore` 모델 자체가 없으므로 진입 불가 |

### D. Phase 4 (벡터 스코어링) — 0% 구현

- `InvestorDNA.dna_vector` 필드 없음
- `ValidityVector` 6차원 클래스 없음
- 코사인 유사도 기반 추천 미적용 (`indicator_matcher.py`는 룰 기반)

---

## 부가 발견 사항

1. **두 갈래 설계 문서가 같은 시점에 공존**: `Phase2_completion_summary.md`의 Phase 3 계획(원안)과 `thesis_control_phase3_frontend_redesign.md`의 PR-7~10(채택안)이 둘 다 살아 있어 **신규 작업자가 어느 쪽이 진행 중인지 파악하기 어려움**. 채택안 문서 상단에 "원안 폐기" 명시 권고.
2. **리디자인 컴포넌트의 사실상 폐기 상태가 문서에 반영 안 됨**: `RealValueIndicatorCard.tsx` 등 4종이 사용처 없는데, 테스트만 통과해서 CI는 그린 상태로 죽은 코드가 누적.
3. **`MoonPhase.tsx`(common) 잔존**: 리디자인에서 "다른 곳 미사용 시 삭제" 권고됐으나 `Grep` 결과 import 0건임에도 파일 존재.
4. **Neo4j 통합(설계 4.4)은 한 줄도 없음** — 가설-전제-지표 그래프는 백엔드 모델 관계만 PostgreSQL에 존재.
5. **진입 경로 5개 중 3개 미구현** (인기/템플릿/Chain Sight) — UX 다양성 측면에서 큰 갭. `models/community.py`의 `PopularThesisCache`도 dead model 상태.
6. **마감 복기 화면 부재**가 가장 가시적인 사용자 가치 갭: 데이터(`ValidityRecord`, `InvestorDNA`)는 쌓이고 있는데 보여줄 곳이 없음.

---

## 결론 한 줄

> Phase 1·2 코어는 안정, **Phase 3는 "두 설계 충돌 + 리디자인 컴포넌트 미통합" 이슈로 80% 표면 구현/40% 실효 구현**. 특허 핵심 기능(합성 에이전트/DNA UI/벡터)은 아직 모델 골격 단계.
