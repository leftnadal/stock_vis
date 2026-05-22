# Thesis Control 설계 갭 감사

> 작성일: 2026-05-22
> 대상: `docs/thesis_control/` 설계 vs `thesis/` 백엔드 + `frontend/components/thesis/` + `frontend/app/thesis/` 실구현
> 모드: 읽기 전용 (코드 변경 없음)

---

## 요약 (Phase별 구현률)

| Phase | 범위 | 상태 | 구현률 |
|---|---|---|---|
| **Phase 1 — 관제 엔진 v2.3.2** | Stage 0~3, 스냅샷, Celery 3태스크, API | (A) 완전 구현 | ~95% |
| **Phase 1 — 이벤트/유효성/DNA 기록** | HypothesisEvent / ValidityRecord / InvestorDNA 모델 + hook | (A) 완전 구현 (UI 미활용) | ~90% |
| **Phase 2 — 유효성 활성화 + DNA 슬라이더** | ValidityScore 집계, 추천 가중치, 슬라이더, 역제안, 상관할인 | (C) 미구현 | 0% |
| **Phase 3 (수학모델) — 합성 에이전트 + Online LR** | SyntheticBootstrapper, ThesisWeightLearner, 블렌딩 | (C) 미구현 | 0% |
| **Phase 3 (Frontend Redesign) — PR-7~10** | display_unit / IndicatorReadings API / AISummary / NotableChanges / 미니차트 / generate_thesis_summaries | (A) 완전 구현 (변형 정착) | ~95% |
| **Phase 3 (Frontend Roadmap) — FE-PR-7~11** | 대시보드 3탭, 히트맵, 히스토리 탭, 마감 아카이브, DNA 프로필 화면 | (C) 미구현 | 0% |
| **Phase 4 — 벡터 스코어링** | DNA/유효성 벡터화, 코사인 유사도 추천 | (C) 미구현 | 0% |

**총평**:
- 관제 엔진(수학모델)과 Phase 1 데이터 수집 인프라(이벤트/유효성/DNA)는 모두 구축. 다만 InvestorDNA·ValidityRecord는 **기록만 되고 어디서도 읽히지 않음** (사실상 dead write).
- Phase 3 대시보드 리디자인(PR-7~10)은 원안과 다른 형태로 **변형 정착** — `IndicatorRow.tsx`가 카드/차트 통합형으로 흡수했고, 원안의 `RealValueIndicatorCard`/`ChartToggleButton`/`PeriodSelector`/`IndividualMiniCharts`는 모두 존재하지만 `app/thesis/[thesisId]/page.tsx`에서는 미사용 ⇒ (D) **폐기/대체** 가능성 있음.
- `Phase2_completion_summary.md`가 예고한 Phase 3 프론트엔드 로드맵(FE-PR-7~11: 3탭/히트맵/히스토리/아카이브/DNA)은 **전혀 착수되지 않음**. 설계서와 구현 사이 가장 큰 갭.

---

## 문서별 상태 테이블

| 설계 문서 | 핵심 산출물 | 실구현 위치 | 상태 |
|---|---|---|---|
| `plan/thesis_control_integrated_roadmap.md` §1.2 | `HypothesisEvent` 모델 | `thesis/models/learning.py:7-55` | (A) 완전 — 13개 event_type 모두, indexes 일치 |
| 동 §1.3 | `ValidityRecord` 모델 + 2×2 매트릭스 점수 | `thesis/models/learning.py:57-94`, 점수 계산 `thesis/views/thesis_views.py:270-286` | (A) 완전 — 매트릭스 (+0.3/-0.2/-0.15/+0.05) 일치 |
| 동 §1.4 | `InvestorDNA` 모델 + 기본 집계 | `thesis/models/learning.py:97-152`, 집계 `thesis_views.py:295-336` | (A) 완전 — `accuracy_rate`/`ai_accept_rate`/`top_down_ratio` property 포함 |
| 동 §1 hook 삽입 | 가설 생성/마감/전제·지표 추가/AI 제안 표시·수락 시 이벤트 기록 | `thesis_views.py:55,107,120,166,180,215,230,257`, `services/thesis_builder.py:648,660,670,724,1184` | (A) 완전 — 모든 트리거 포인트에 `HypothesisEvent.objects.create` 삽입 |
| 동 §2 (Phase 2) | `ValidityScore` 테이블, 주1회 집계 Celery, indicator_matcher 유효성 가중치 | `grep ValidityScore` → migration 0001만 매치(테이블만 존재 가능성), 서비스 0건 | (C) 미구현 — `indicator_matcher.py` 단순 키워드만, validity_boost/confidence/is_active 로직 없음 |
| 동 §2.3 | DNA 슬라이더 (`personalization_weight`) | 필드는 `learning.py:124`에 존재하나 어디서도 read 안 됨 | (B) 모델만 — 로직 0% |
| 동 §2.4 | Contrarian Nudge 역제안 | 없음 | (C) 미구현 |
| 동 §2.5 | 60일 상관계수 자동 할인, Adaptive Decay/Window, Sustained Extreme, 뉴스 센티먼트 → Stage 1 입력 | 없음 (`thesis/services` 검색 결과 0건) | (C) 미구현 — 단, `_fetch_news_sentiment_value`(`tasks/eod_pipeline.py:197`)는 별개 단순 fetcher |
| 동 §3.1 | `SyntheticBootstrapper` + 20~30개 페르소나 | 없음 | (C) 미구현 |
| 동 §3.2 | `ThesisWeightLearner` (Online Logistic Regression) | 없음 | (C) 미구현 |
| 동 §3.3 | 합성/실제 데이터 블렌딩 (`is_synthetic` 필드 + 비중 자동 감소) | `ValidityRecord`에 `is_synthetic` 필드 없음 | (C) 미구현 |
| 동 §4 | 벡터화 (16d DNA + 6d Validity, 코사인 유사도) | 없음 | (C) 미구현 |
| `plan/thesis_control_phase3_frontend_redesign.md` PR-7 | `ThesisIndicator.display_unit` 필드 + `_infer_unit` fallback + `IndicatorReadingsView` | `thesis/models/indicator.py` (마이그레이션 `0004_add_display_unit.py`, `0005_populate_display_unit.py` 확인), `monitoring_views.py:264 IndicatorReadingsView`, `_infer_unit:346`, URL `urls.py:30-34` | (A) 완전 구현 |
| 동 PR-8 | `AISummarySection.tsx` / `NotableChangesSection.tsx` / `RealValueIndicatorCard.tsx` + `formatRawValue`/`formatChangePct`/`supportLabel` | `frontend/components/thesis/dashboard/*.tsx`, `lib/thesis/utils.ts` | (A) 컴포넌트 + 유틸 완전 — 단 `RealValueIndicatorCard`는 page.tsx에서 미참조 (테스트만 사용) |
| 동 PR-9 | `ChartToggleButton` / `PeriodSelector` / `IndividualMiniCharts` + readings 쿼리 + OverallMoon 삭제 | 컴포넌트 3종 존재, `OverallMoon`/`DashboardIndicatorCard`/`RecentChange` 모두 삭제 확인 | (D) **폐기/대체** — 컴포넌트는 만들었으나 `page.tsx`는 사용 안 함. `IndicatorRow.tsx`가 카드+토글+차트(`1M/1Y/3Y/5Y`) 통합형으로 흡수. 원안의 7D/14D/30D PeriodSelector는 미사용 |
| 동 PR-10 | `generate_thesis_summaries` Celery + alert_engine 이벤트를 NotableChange로 변환 | `thesis/tasks/summary.py:87 generate_thesis_summaries`, Gemini 호출 `:55`, snapshot 빌더 `services/snapshot_builder.py` | (A) 완전 구현 |
| `frontend/task_done/Phase2_completion_summary.md` §8 — FE-PR-7 (3탭) | 대시보드 탭(관제/상세/히스토리) + 전제 CRUD | `app/thesis/[thesisId]/page.tsx`는 단일 페이지, 탭 구조 0건 | (C) 미구현 |
| 동 FE-PR-8 (히트맵) | Finviz 스타일 히트맵 + weight/direction 편집 | `lib/thesis/types.ts:150,157`에 히트맵 셀/데이터 **타입만** 정의, 컴포넌트 없음, API 없음 | (B) 타입만 |
| 동 FE-PR-9 (히스토리) | recharts 라인 차트 + 스냅샷 타임라인 | `ThesisSnapshot` 모델은 존재(`models/monitoring.py`), 그러나 시계열 API/페이지 없음 | (C) 미구현 |
| 동 FE-PR-10 (마감 아카이브) | 마감 가설 목록 + ValidityMatrix 시각화 | `frontend/app/thesis/(list)/`는 active만, archive route 없음 | (C) 미구현 |
| 동 FE-PR-11 (투자자 DNA 프로필) | AccuracyRing + CategoryChart + DNA 통계 페이지 | `InvestorDNA` 모델 read API 0건, 화면 0건 | (C) 미구현 |
| `plan/thesis_control_design.md` §community | `ThesisFollow`/`PopularThesisCache` | `thesis/models/community.py` 존재 | (B) 모델만 — 서비스/엔드포인트 미발견 (별도 확인 필요) |

---

## Phase 3 미구현 항목 상세

### A. 수학모델 Phase 3 (합성 에이전트 + Online LR) — 0%

설계서 `thesis_control_integrated_roadmap.md` §3 의 청구항(특허 차별점) 전반이 미착수.

| 미구현 항목 | 설계 위치 | 영향 |
|---|---|---|
| `SyntheticBootstrapper` 클래스 | §3.1 | 사용자 0명일 때 ValidityScore 초기값 부재 → Phase 2 추천도 기능 안 함 |
| 20~30개 투자자 페르소나 정의 (`SYNTHETIC_PERSONAS`) | §3.1 | LLM 시뮬레이션 부재 |
| 과거 시장 데이터 기반 합성 가설 생성 함수 (`generate_thesis`, `generate_premises_and_indicators`) | §3.1 | — |
| `ValidityRecord.is_synthetic` 필드 | §3.3 | 합성/실제 데이터 구분 불가 — 모델 마이그레이션 필요 |
| `aggregate_validity_scores(blend_ratio=0.3)` 블렌딩 | §3.3 | 자동 비중 감소 로직 부재 |
| `ThesisWeightLearner` (Online Logistic Regression, L2 prior) | §3.2 | 전제 가중치 자동학습 부재 → `W_j_suggested` 추천 못 함 |
| `get_actual_indicator_movement` / `get_actual_return` 헬퍼 | §3.1 | 실제 시장 데이터 대조 모듈 부재 |

> **선행조건 미충족**: Phase 2(`ValidityScore` 집계, 추천 가중치 반영, DNA 슬라이더, 상관할인, Adaptive Decay/Window) 자체가 0%이므로 Phase 3 진입 불가. 사실상 Phase 1 데이터 수집(이벤트/매트릭스 기록)만 유지 중이고 Phase 2로 가는 다리(ValidityScore 집계 태스크)가 없음.

### B. 프론트엔드 Phase 3 로드맵 FE-PR-7~11 — 0%

`Phase2_completion_summary.md` §8 이 예고했으나 어느 PR도 착수되지 않았음 (`task_done/`에 FE-PR-7~11 보고서 0개).

| PR | 산출물 | 현재 상태 |
|---|---|---|
| **FE-PR-7** | 대시보드 3탭 (관제/상세/히스토리) + 전제 CRUD UI | `page.tsx`는 단일 스크롤. 탭 라우팅·컴포넌트 0건. 전제 CRUD 화면 0건 |
| **FE-PR-8** | Finviz 스타일 히트맵 + 지표 weight/direction 편집 | `lib/thesis/types.ts:150,157`에 `HeatmapCell`/`HeatmapData` **타입만** 존재, 컴포넌트/API/페이지 모두 없음. 백엔드 dashboard API에 heatmap payload 없음 |
| **FE-PR-9** | recharts 라인 차트 + 스냅샷 타임라인 (히스토리 탭) | `ThesisSnapshot`은 매일 생성되나 시계열 조회 API/페이지 없음. `IndicatorRow` 내부 미니차트는 readings 기반이라 별개 |
| **FE-PR-10** | 마감 아카이브 목록 + ValidityMatrix 시각화 | `Thesis.status='closed'` 필터 페이지 없음, ValidityRecord 조회 API/시각화 0건 |
| **FE-PR-11** | 투자자 DNA 프로필 화면 (AccuracyRing + CategoryChart) | `InvestorDNA` 데이터를 노출하는 GET 엔드포인트 없음. 화면 0건. DNA 모델은 매 마감 시 갱신되지만 **사용자가 볼 방법이 전혀 없음** |

### C. 대시보드 리디자인 변형 정착 (Phase 3 PR-8/PR-9의 (D) 케이스)

설계서 `thesis_control_phase3_frontend_redesign.md`가 명시한 컴포넌트들은 **모두 작성되었지만**, 메인 페이지에서 채택되지 않고 다른 패턴이 정착함.

| 설계 컴포넌트 | 파일 존재 | page.tsx 사용 여부 | 실제 채택된 대체물 |
|---|---|---|---|
| `RealValueIndicatorCard.tsx` | ✅ | ❌ (테스트만) | `IndicatorRow.tsx` (카드+토글+차트 통합) |
| `ChartToggleButton.tsx` | ✅ | ❌ | `IndicatorRow` 내부 `<ChevronDown>` 토글 |
| `PeriodSelector.tsx` (7D/14D/30D) | ✅ | ❌ | `IndicatorRow` 내부 `DAILY_PERIODS` (1M/1Y/3Y/5Y) |
| `IndividualMiniCharts.tsx` | ✅ | ❌ | `IndicatorRow` 내부 `AreaChart` (지표마다 1개) |
| `AISummarySection.tsx` | ✅ | ✅ 채택 | — |
| `NotableChangesSection.tsx` | ✅ | ✅ 채택 | — |

**시사점**:
- 설계 PR-9가 가정한 "토글 시 모든 지표의 미니차트를 한 영역에서" 패턴 대신, "지표 카드 각각에 인라인 토글 차트" 패턴이 정착.
- 분기 지표(`is_quarterly`)와 일간 지표를 한 카드에서 처리하기 위한 변형 — 설계서가 분기 지표 케이스(`QuarterlySparkline`)를 다루지 않았기 때문으로 추정.
- 따라서 PR-9 4개 컴포넌트는 **사실상 dead code**. 삭제 또는 명시적으로 "참조 구현" 표시 필요.

### D. 사용되지 않는 Phase 1 산출물

이벤트/유효성/DNA는 잘 기록되지만 **읽는 곳이 없음**:

- `HypothesisEvent`: 13종 이벤트가 정확히 기록됨. 그러나 InvestorDNA 집계 외 read 없음. `event_data`의 풍부한 분석값(suggestion_type, extraction_level 등)이 휘발됨.
- `ValidityRecord`: 마감 시 지표마다 1건씩 생성. 그러나 집계(`ValidityScore`)도 없고 추천에서 read도 안 함. 특허 청구항 2번의 "사용자 판정 포함 학습 루프" 핵심이 작동하지 않음.
- `InvestorDNA`: 매 마감마다 정확히 갱신. 그러나 GET 엔드포인트, 화면, 추천 가중치 반영 모두 없음.

> **즉시 가치 회수 가능한 작업**: 최소한의 GET API와 간단한 통계 화면만 만들어도 Phase 1 데이터가 사용자에게 노출됨. Phase 2/3 알고리즘 없이도 "총 N건 마감, 적중률 X%, 상향식 vs 하향식 비율" 등 표시 가능.

---

## 권장 후속 작업 (우선순위)

1. **(즉시)** PR-9 dead component 4종 정리 — 삭제 vs 메인 page.tsx 적용 결정 필요.
2. **(즉시)** Phase 1 데이터 노출 — `GET /thesis/dna/`, `GET /thesis/{id}/validity/` 최소 엔드포인트만이라도. FE-PR-11 진입 전 데이터 확인.
3. **(중기)** FE-PR-7 (3탭 구조) — 단일 페이지 한계 + 향후 FE-PR-8~11 컨테이너 역할.
4. **(중기)** Phase 2 `ValidityScore` 집계 태스크 — 마감 10건+ 축적 후 작동, 지금이라도 만들어 두면 자동 활성화.
5. **(장기)** Phase 3 특허 항목 — `SyntheticBootstrapper`는 Cold start 해결 핵심, Phase 2 안정화 이전엔 ROI 불명.

---

## 부록: 검증에 사용된 grep 결과 요약

- `HypothesisEvent.objects.create` 호출: `thesis_views.py` 6건 + `services/thesis_builder.py` 5건
- `ValidityRecord.objects.create`: `thesis_views.py:92` 1건 (마감 시점)
- `InvestorDNA.objects.get_or_create`: `thesis_views.py:297` 1건 (`_update_investor_dna`)
- `ValidityScore`/`SyntheticBootstrapper`/`ThesisWeightLearner` 코드 매치: 0건 (migration `0001_initial.py`의 모델/주석만)
- Dashboard `page.tsx`가 import하는 컴포넌트: `DashboardPageHeader`, `DashboardHeader`, `IndicatorRow`, `AISummarySection`, `NotableChangesSection` (5개)
- 삭제 확인 완료: `OverallMoon.tsx`, `DashboardIndicatorCard.tsx`, `RecentChange.tsx` (없음)
- Phase 3 컴포넌트 작성됐으나 page.tsx 미참조: `RealValueIndicatorCard`, `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`
