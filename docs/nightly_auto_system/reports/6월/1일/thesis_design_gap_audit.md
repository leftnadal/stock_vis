# Thesis Control 설계 갭 감사

> 감사일: 2026-06-01
> 감사 대상: `docs/thesis_control/` 설계서 ↔ `thesis/` (백엔드) + `frontend/components/thesis/` + `frontend/app/thesis/` (프론트엔드)
> 감사 기준 커밋: `e92991e`
> 모드: **읽기 전용** (코드 수정 없음)

---

## 0. 핵심 결론 (TL;DR)

1. **Phase 1 (관제 엔진 + 이벤트/유효성/DNA 기록)은 백엔드 완전 구현**. HypothesisEvent·ValidityRecord·InvestorDNA 3종 모델 + 실제 비즈니스 로직 삽입(13곳 이벤트 기록 + 마감 시 유효성/DNA 갱신)까지 모두 동작.
2. **Phase 2 (유효성 활성화 + DNA 슬라이더 + 정교화)는 백엔드 전면 미구현**. `ValidityScore` 모델, 집계 태스크, `indicator_matcher`의 DNA personalization / contrarian nudge / validity_boost 로직이 전혀 없음. `personalization_weight` 필드만 미사용 상태로 선재(先在).
3. **Phase 3 (합성 에이전트 + Online LR)는 백엔드 전면 미구현**. `SyntheticBootstrapper`, `ValidityRecord.is_synthetic`, `ThesisWeightLearner` 모두 부재.
4. **"Phase 3 프론트엔드"는 설계가 두 갈래로 갈라졌고, 나중 안(리디자인)이 채택됨**:
   - 원안 `FE-PR-7~11`(탭 구조 + 히트맵 + 히스토리 + 마감 아카이브 + DNA 프로필) → **폐기/대체 (D)**. 해당 라우트·컴포넌트 전무.
   - 리디자인 `phase3_frontend_redesign.md`의 `PR-7~10`(실제 값 카드 + AI 분석 + 미니차트) → **부분 구현 (B)**.
5. **리디자인 PR-8/PR-9 컴포넌트 4종이 "고아(orphan)" 상태**: `RealValueIndicatorCard`, `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts` 파일은 존재하나 **어디에서도 import되지 않음**. 실제 대시보드(`app/thesis/[thesisId]/page.tsx`, 138줄)는 `IndicatorRow` 기반으로 재진화했고 차트 토글/미니차트 기능은 메인 화면에 미연결.

---

## 1. 요약 — Phase별 구현률

| Phase | 영역 | 설계 출처 | 구현률 | 분류 |
|-------|------|-----------|--------|------|
| **Phase 1** | 관제 엔진 (Stage 0~3) | `integrated_roadmap §1.1` | ~100% | **A** |
| **Phase 1** | 이벤트 수집 (HypothesisEvent) | `integrated_roadmap §1.2` | ~100% | **A** |
| **Phase 1** | 유효성 기록 (ValidityRecord) | `integrated_roadmap §1.3` | ~95% (regime 고정) | **A/B** |
| **Phase 1** | DNA 골격 (InvestorDNA) | `integrated_roadmap §1.4` | ~95% (UI 미노출) | **A/B** |
| **Phase 2** | ValidityScore 집계 + 활성화 | `integrated_roadmap §2.1~2.2` | 0% | **C** |
| **Phase 2** | DNA 슬라이더 + 역제안 | `integrated_roadmap §2.3~2.4` | 0% | **C** |
| **Phase 2** | 정교화(상관할인/Adaptive/센티먼트) | `integrated_roadmap §2.5` | 0% | **C** |
| **Phase 3 (BE)** | 합성 에이전트 부트스트래핑 | `integrated_roadmap §3.1` | 0% | **C** |
| **Phase 3 (BE)** | Online Logistic Regression | `integrated_roadmap §3.2~3.3` | 0% | **C** |
| **Phase 3 (FE) 원안** | FE-PR-7~11 (탭/히트맵/DNA) | `Phase2_completion_summary §8` | 0% | **D** (대체됨) |
| **Phase 3 (FE) 리디자인** | PR-7 백엔드(display_unit/raw_value) | `phase3_frontend_redesign §4` | ~100% | **A** |
| **Phase 3 (FE) 리디자인** | PR-8 실제값 카드 + AI 분석 | `phase3_frontend_redesign §5` | ~50% (고아 컴포넌트) | **B** |
| **Phase 3 (FE) 리디자인** | PR-9 미니차트 + 기간 선택 | `phase3_frontend_redesign §6` | ~30% (미연결) | **B** |
| **Phase 3 (FE) 리디자인** | PR-10 AI 파이프라인(Celery) | `phase3_frontend_redesign §7` | ~100% | **A** |
| **Phase 4** | 벡터 스코어링 | `integrated_roadmap §4` | 0% | **C** (미착수, 정상) |

> **분류 범례**: (A) 완전 구현 / (B) 부분 구현 / (C) 미구현 / (D) 폐기·대체

---

## 2. 문서별 상태 테이블

| 설계 문서 | 정의 내용 | 구현 대조 결과 | 분류 |
|-----------|----------|----------------|------|
| `plan/thesis_control_design.md` | 원래 설계(컨셉, 플로우, 모델 4.2, API 6) | 모델·관제 엔진·API 기본 골격 구현됨 | A |
| `plan/thesis_control_integrated_roadmap.md` §1 | Phase 1 (MVP) | **완전 구현** (모델 3종 + 비즈니스 삽입) | A |
| `plan/thesis_control_integrated_roadmap.md` §2 | Phase 2 (유효성 활성화 + DNA 슬라이더) | **미구현** | C |
| `plan/thesis_control_integrated_roadmap.md` §3 | Phase 3 (합성 에이전트 + Online LR) | **미구현** | C |
| `plan/thesis_control_integrated_roadmap.md` §4 | Phase 4 (벡터 스코어링) | 미착수 (로드맵상 정상) | C |
| `plan/thesis_control_phase3_frontend_redesign.md` | 대시보드 리디자인 PR-7~10 | **부분 구현** (BE 완, FE 컴포넌트 고아) | B |
| `frontend/task_done/Phase2_completion_summary.md` §8 | 원안 FE-PR-7~11 (탭/히트맵/DNA) | **폐기/대체** (라우트·컴포넌트 전무) | D |
| `frontend/task_done/FE-PR-1~6_*.md` | Phase 2 프론트 핵심 루프 | 완료 보고와 코드 일치 확인 | A |
| `plan/talking_builder/*` | LLM 빌더 (Phase A~C) | 별도 트랙, 본 감사 범위 외 (빌더 동작 중) | — |

---

## 3. Phase별 상세 근거

### 3.1 Phase 1 백엔드 — 완전 구현 (A)

**관제 엔진 (Stage 0~3)** — `thesis/services/` 내 전 단계 존재:
- Stage 0 Validation: `data_validator.py`
- Stage 1 Scoring: `indicator_scorer.py`
- Stage 2 Aggregation: `premise_aggregator.py`
- Stage 3 State/Alert: `thesis_state_machine.py`, `alert_engine.py`, `arrow_calculator.py`
- 스냅샷: `snapshot_builder.py`

**이벤트 수집** — `HypothesisEvent` 모델(`models/learning.py:7`) + 실제 삽입 확인:
- `views/thesis_views.py`: 8곳 (`:62, :114, :127, :173, :187, :222, :237, :266`)
- `services/thesis_builder.py`: 5곳 (`:659, :671, :681, :735, :1203`)
- → 설계 §1.2의 "기존 비즈니스 로직에 1줄씩 삽입" 원칙 충실히 이행됨.

**유효성 기록** — `ValidityRecord`(`models/learning.py:55`) + 마감 시 생성(`views/thesis_views.py:93~108`):
- `_compute_validity_score(indicator_aligned, thesis_correct)`로 2×2 매트릭스 점수 산출 ✓
- `indicator_aligned = (indicator.current_score or 0) > 0` ✓ (설계와 일치)

**DNA 골격** — `InvestorDNA`(`models/learning.py:97`) + 마감 시 갱신(`_update_investor_dna`, `views/thesis_views.py:302`):
- `accuracy_rate`, `ai_accept_rate`, `top_down_ratio` 프로퍼티 설계와 동일 ✓

**부분 갭 (A→B 경계)**:
- `ValidityRecord.market_regime`가 마감 시 **`'normal'` 하드코딩**(`thesis_views.py:102`). 설계는 `get_regime_at()` 기반 동적 판정을 의도했으나 Phase 1 한계로 고정. (설계 §1.3 주석 "Phase 1: 고정"과 일치 — 의도된 단순화)
- `InvestorDNA`는 데이터 축적만 하고 **UI 노출 0** (설계 §1.4 "UI에서는 아직 활용 안 함"과 일치 — 의도된 보류).

### 3.2 Phase 2 백엔드 — 미구현 (C)

| 설계 항목 | 검색 결과 |
|-----------|----------|
| `ValidityScore` 모델 | `grep "ValidityScore" thesis/` → **0건**. `models/__init__.py` 미등록 |
| ValidityRecord→ValidityScore 집계 Celery 태스크 | 부재 (`tasks/`에 `eod_pipeline.py`, `summary.py`만 존재) |
| `indicator_matcher`의 `validity_boost` / 티어 분류 | `grep "validity\|nudge\|dna\|personaliz" indicator_matcher.py` → **0건** |
| DNA 적합도 슬라이더 (`apply_dna_personalization`) | 부재. `personalization_weight` 필드만 미사용 상태로 존재 |
| 역제안 (`add_contrarian_nudge`) | 부재 |
| 상관계수 자동 할인 / Adaptive Decay / Sustained Extreme | `thesis/services/` 내 부재 |
| 뉴스 센티먼트 → Stage 1 입력 | 부재 (`keyword_collectors/news.py`는 키워드 수집용, Stage 1 입력 아님) |

### 3.3 Phase 3 백엔드 — 미구현 (C)

| 설계 항목 | 검색 결과 |
|-----------|----------|
| `SyntheticBootstrapper` / 페르소나 시뮬레이션 | `grep "Synthetic\|Bootstrapper"` → **0건** |
| `ValidityRecord.is_synthetic` 필드 | **0건** (마이그레이션 0001~0009 중 부재) |
| `ThesisWeightLearner` / Online Logistic Regression | `grep "WeightLearner\|LogisticRegression\|get_suggested_weights"` → **0건** |
| 합성/실제 블렌딩 (`aggregate_validity_scores`) | 부재 (ValidityScore 자체 부재로 선결 불가) |

---

## 4. Phase 3 미구현 항목 상세

> 사용자가 "Phase 3 (깊이 + 회고 + 프로필)"로 지목한 영역은 **두 개의 상충하는 설계**가 존재한다. 시간순으로 원안(FE-PR-7~11)이 먼저 작성되고, 이후 리디자인(PR-7~10)으로 방향이 전환되었다. 실제 코드는 리디자인 방향을 따른다.

### 4.1 원안 FE-PR-7~11 (Phase2_completion_summary §8) — 전면 폐기/대체 (D)

| PR | 설계 핵심 | 구현 상태 | 근거 |
|----|----------|----------|------|
| FE-PR-7 | 대시보드 3탭(관제/상세/히스토리) + 전제 CRUD | **미구현** | `app/thesis/[thesisId]/` 하위에 탭 라우트 없음. `TabBar`/`DetailTab` 컴포넌트 0건 |
| FE-PR-8 | Finviz 히트맵 + weight/direction 편집 | **미구현** | `grep "Heatmap\|히트맵"` → 0건 |
| FE-PR-9 | 히스토리 탭 (recharts 라인 + 스냅샷 타임라인) | **미구현** | `HistoryTab` 컴포넌트·라우트 0건 |
| FE-PR-10 | 마감 아카이브 + ValidityMatrix | **미구현** | `grep "ValidityMatrix\|Archive"` → 0건. 마감 아카이브 라우트 없음 |
| FE-PR-11 | 투자자 DNA 프로필 (AccuracyRing + CategoryChart) | **미구현** | `grep "DNAProfile\|AccuracyRing\|CategoryChart"` → 0건. DNA 프로필 화면 부재 |

→ **InvestorDNA가 백엔드에 축적되고 있으나 이를 소비하는 프론트 화면(FE-PR-11)이 전혀 없다.** Phase 1에서 "데이터만 축적"이라는 설계 의도와 일치하나, 특허 청구항(독립항 1: 투자 DNA 프로파일)의 사용자 노출 부분은 미실현 상태.

### 4.2 리디자인 PR-7~10 (phase3_frontend_redesign.md) — 부분 구현 (B)

#### PR-7 백엔드 — 완전 구현 (A)
- `ThesisIndicator.display_unit` 필드: 마이그레이션 `0004_add_display_unit.py` + `0005_populate_display_unit.py` ✓
- `DashboardView` raw_value/change_pct 확장: `monitoring_views.py:94~112` ✓
- `_infer_unit()` fallback + RATIO_METRICS % 변환 로직 존재 ✓
- (단, `IndicatorReadingsView` 클래스 자체는 `monitoring_views.py`에서 별도 확인 필요 — readings API 연결은 미니차트 미연결로 인해 사용처 없음)

#### PR-8 실제값 카드 + AI 분석 — 부분 구현 (B)
| 컴포넌트 | 파일 존재 | page.tsx 연결 | 상태 |
|----------|:-------:|:------------:|------|
| `AISummarySection.tsx` | ✓ | ✓ (`page.tsx:12, :75`) | **연결됨 A** |
| `NotableChangesSection.tsx` | ✓ | ✓ (`page.tsx:13, :81`) | **연결됨 A** |
| `RealValueIndicatorCard.tsx` | ✓ | ✗ **미import** | **고아 B** |

→ 실제 대시보드는 `RealValueIndicatorCard` 대신 **`IndicatorRow`**(`page.tsx:11, :115`)를 사용. 카드형 → 행(row)형으로 UI가 재진화했고, 설계 문서의 핵심 산출물(`RealValueIndicatorCard`)이 죽은 코드로 남음.

#### PR-9 미니차트 + 기간 선택 — 부분 구현 (B)
| 컴포넌트 | 파일 존재 | import 사용처 | 상태 |
|----------|:-------:|:------------:|------|
| `ChartToggleButton.tsx` | ✓ | **0건** | **고아 B** |
| `PeriodSelector.tsx` | ✓ | **0건** | **고아 B** |
| `IndividualMiniCharts.tsx` | ✓ | **0건** | **고아 B** |

→ 차트 토글 / 기간 선택 / 지표별 미니차트 기능이 **컴포넌트로만 작성되고 메인 대시보드(`page.tsx`)에 미연결**. 설계 §6.7의 "카드 그리드 아래 차트 섹션 추가"가 실제 page.tsx(138줄)에 반영되지 않음.
→ 대신 `QuarterlySparkline.tsx`가 추가 도입됨(설계 외 산출물) — 분기 지표 스파크라인. 실제 차트 니즈는 이쪽으로 흡수된 것으로 추정.

#### PR-10 AI 파이프라인 (Celery) — 완전 구현 (A)
- `tasks/summary.py`: `generate_thesis_summaries` 태스크 ✓ (멱등 + force 옵션 + Gemini 2.5 Flash 동기 호출 `:65 genai_module.Client`)
- `snapshot_builder.py`: `notable_changes` 기록(`:108~160`, |score 변화| ≥ 0.3 기준) ✓
- → 설계 §7.1~7.2 충실 구현. (단, §7.2는 alert_engine 이벤트 재활용을 의도했으나 실제는 score 변화 임계 기반 — 구현 방식 차이는 있으나 기능 동등)

---

## 5. 우선순위별 갭 정리 (참고용 — 조치는 별도 결정)

| 우선도 | 갭 | 영향 |
|--------|-----|------|
| 🔴 높음 | **리디자인 PR-8/PR-9 고아 컴포넌트 4종** | 죽은 코드. 정리(삭제) 또는 연결 결정 필요. 유지보수 혼란 |
| 🟡 중간 | **InvestorDNA 소비 화면(FE-PR-11) 부재** | 특허 독립항 1의 사용자 노출 부분 미실현. 데이터만 축적 중 |
| 🟡 중간 | **Phase 2 백엔드 전면 미구현** | ValidityRecord 데이터는 쌓이나 ValidityScore 집계·활용 부재 → 학습 루프 미완성 |
| 🟢 낮음 | `ValidityRecord.market_regime` 'normal' 고정 | Phase 1 의도된 단순화. Phase 2에서 해소 예정 |
| 🟢 낮음 | Phase 3 BE(합성 에이전트/Online LR), Phase 4 | 로드맵상 후순위. 미착수 정상 |

---

## 6. 감사 메타

- **검증 방식**: 설계 문서 4종 정독 + `grep`/`ls`/파일 직접 대조 (모델·뷰·서비스·태스크·프론트 컴포넌트·라우트)
- **미확인 잔여**: `IndicatorReadingsView` 클래스 본문 / `monitoring_views.py` 전체 라인별 검증은 raw_value 확장 부분만 확인(미니차트 미연결로 우선도 낮음)
- **코드 변경**: 없음 (읽기 전용 감사)
