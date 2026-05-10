# Thesis Control 설계 갭 감사

> 작성일: 2026-05-11
> 범위: `docs/thesis_control/` 전체 설계 문서 ↔ `thesis/` (백엔드) + `frontend/components/thesis/` + `frontend/app/thesis/` 코드
> 모드: 읽기 전용 (코드/문서 수정 없음)

---

## 요약 (Phase별 구현률)

| Phase | 영역 | 구현률 | 상태 |
|-------|------|--------|------|
| **수학 엔진 v2.3.2** (Stage 0~3) | Backend | 95% | (A) 완전 구현. 상관 할인/Adaptive Decay/Sustained Extreme만 미구현 |
| **Phase 1 MVP** (모델·스코어링·Celery·이벤트수집·ValidityRecord·InvestorDNA) | Backend | 100% | (A) 완전 구현 |
| **Phase 1 FE-PR-1~6** (라우팅·목록·빌더·지표설정·대시보드·알림+마감) | Frontend | 100% | (A) 완전 구현 — Phase 2 완료 보고서로 종결 |
| **Phase 2 — 모니터링 강화** (히트맵/그래프뷰·뉴스 센티먼트·[근거]·내러티브) | Backend+FE | 30% | (B) 부분 구현. 히트맵 데이터만 백엔드에 존재, FE 미사용 |
| **Phase 2 — 개인화 시작** (ValidityScore 집계·DNA 슬라이더·역제안) | Backend+FE | 5% | (C) 미구현. 모델 골격만 |
| **Phase 3 (원안) — FE-PR-7~11** (대시보드 탭/히트맵/히스토리/아카이브/DNA) | Frontend | 0% | (D) 폐기. `phase3_frontend_redesign.md`로 재정의 |
| **Phase 3 (재설계) — PR-7~10** (실제값 카드·AI분석·NotableChanges·미니차트·AI 파이프라인) | Backend+FE | 100% | (A) 완전 구현. PR-9는 형태 변형(통합 IndicatorRow) 적용 |
| **Phase 3 (로드맵) — 커뮤니티/Cold Start** (인기·템플릿·Chain Sight 연동·합성에이전트·Online LR·Neo4j·복기) | Backend+FE | 0% | (C) 미구현 |
| **Phase 4 — 벡터 스코어링** (DNA 16d·유효성 6d·코사인 유사도·반대 가설) | All | 0% | (C) 미구현 — 미착수 |
| **빌더 재설계 (talking_builder v4)** | Backend+FE | 80% | (A/B) Phase A-MVP, A-Hardening, B 대부분 구현. NEWS_SUGGESTIONS_ENABLED까지 활성. C 단계는 미구현 |

---

## 설계 문서 인벤토리

### `docs/thesis_control/` 루트
| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `thesis_control_user_experience.md` | 435 | 일반 UX 가이드 |
| `thesis_control_phase1_frontend_FE_PR_1.md` | 1254 | FE-PR-1 라우팅+공통 |
| `thesis_control_phase1_frontend_FE_PR_2.md` | 1171 | FE-PR-2 목록 |
| `thesis_control_phase1_frontend_FE_PR_3.md` | 1901 | FE-PR-3 대화형 빌더 |
| `thesis_control_phase1_frontend_FE_PR_4.md` | 1515 | FE-PR-4 지표 설정 |
| `thesis_control_phase1_frontend_FE_PR_5.md` | 1171 | FE-PR-5 대시보드 + (PR-6 알림+마감) |
| `thesis_control_phase1_frontend_prompts.md` | 1106 | FE 프롬프트 모음 |
| `thesis_control_phase1_prompts.md` | 1243 | BE 프롬프트 모음 |

### `docs/thesis_control/plan/`
| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `thesis_control_design.md` | 1370 | **설계 v1.0** — 모델/API/UX 단일 소스 |
| `thesis_control_implementation_guide.md` | 286 | Phase 1~4 통합 구현 순서 |
| `thesis_control_integrated_roadmap.md` | 660 | 수학 모델 + 특허 기능 4 Phase |
| `thesis_control_math_model_final.md` | 1153 | v2.3.2 수학 엔진 사양 |
| `thesis_control_phase3_frontend_redesign.md` | 1095 | **Phase 3 대시보드 리디자인 (재정의)** |

### `docs/thesis_control/plan/talking_builder/`
| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `llm_builder_plan.md` | 563 | 초기 LLM 빌더 설계 |
| `quarterly_indicator_dashboard_plan.md` | 424 | 분기 지표 대시보드 |
| `thesis_builder_redesign_v2.md` | 1110 | 빌더 v2 재설계 |
| `redesign_build_plan/00_total_plan.md` | 525 | **빌더 v4 총괄** |
| `redesign_build_plan/01_phase_a_mvp.md` | 287 | Phase A-MVP PR-1~3 |
| `redesign_build_plan/02_phase_a_hardening.md` | 118 | A-Hardening PR-4~7 |
| `redesign_build_plan/03_phase_b_keywords.md` | 299 | Phase B PR-8~12 |
| `redesign_build_plan/04_phase_c_advanced.md` | 144 | Phase C 미정 |
| `redesign_build_plan/05_summary.md` | 100 | 요약 |

### `docs/thesis_control/frontend/task_done/`
| 파일 | 완료일 | 상태 |
|------|--------|------|
| `FE-PR-1_routing_common_components.md` | 2026-03-11 | 완료 |
| `FE-PR-2_thesis_list_page.md` | 2026-03-11 | 완료 |
| `FE-PR-3_plan_review_v3.md` | 2026-03-12 | 완료 |
| `FE-PR-3_builder_implementation.md` | 2026-03-13 | 완료 |
| `FE-PR-4_indicator_setup.md` | 2026-03-13 | 완료 |
| `FE-PR-5_dashboard.md` | 2026-03-14 | 완료 |
| `FE-PR-6_alerts_close_qa.md` | 2026-03-14 | 완료 |
| `Phase2_completion_summary.md` | 2026-03-16 | 완료 |

### `docs/thesis_control/work_done/`
| 파일 | 역할 |
|------|------|
| `phase_a_llm_builder.md` | LLM 빌더 작업 결과 |

---

## 문서별 상태 테이블

### A. 핵심 설계 문서

| 설계 문서 | 핵심 요구 | 코드 매핑 | 상태 |
|----------|----------|----------|------|
| `plan/thesis_control_design.md` 4.1 — 모델 디렉토리 구조 | thesis/models/{thesis,indicator,monitoring,community} | `thesis/models/{thesis,indicator,monitoring,community,learning,keyword}.py` 모두 존재 | (A) 완전 구현 + 확장 |
| `plan/thesis_control_design.md` 4.2 — Thesis 필드 | direction/target/expected_*/thesis_type/entry_source/status/overall_score | 모든 필드 존재 (thesis.py L7~140). **차이: status enum이 설계엔 6종(closed_correct/incorrect/neutral 분리)인데 코드는 4종(closed 단일) + outcome 별도 필드** | (B) 부분 구현 — outcome 분리 채택 |
| `plan/thesis_control_design.md` 4.2 — ThesisPremise | extraction_level(explicit/implicit/ai_suggested), current_score, explanation | extraction_level 필드 **없음**, explanation 필드 **없음** (코드: category, weight, is_paused만) | (B) 부분 구현 |
| `plan/thesis_control_design.md` 4.2 — ThesisIndicator | support_direction, current_arrow_degree, rationale, context_explanation | support_direction OK, current_degree OK, rationale **없음 (recommendation_reason로 대체)**, context_explanation **없음** | (B) 부분 구현 |
| `plan/thesis_control_design.md` 4.2 — ThesisAlert alert_type | indicator_change/threshold_cross/news_event/target_date/daily_summary | 코드는 더 세분화: direction_flip, sharp_move, extreme_volatility, weakest_link, premise_divergence, stale_data, indicator_overlap, indicator_bias, state_change, milestone, needs_review | (D) 폐기/대체 — 수학 모델 v2.3.2 alert 분류 채택 |
| `plan/thesis_control_design.md` 4.2 — community 모델 | ThesisFollow, PopularThesisCache | `thesis/models/community.py` 정의됨 | (A) 모델만 |
| `plan/thesis_control_design.md` 4.4 — Neo4j 가설 관계 그래프 | (Thesis)-[HAS_PREMISE/SIMILAR_TO/OPPOSITE_OF]-> 등 | thesis/ 어디에도 Neo4j import/노드 생성 코드 없음 | (C) 미구현 |
| `plan/thesis_control_design.md` 5.3 — Celery 8태스크 | update_indicator_readings/calculate_arrow_degrees/create_daily_snapshots/check_thesis_alerts/scan_thesis_news/update_popular_thesis_cache/prepare_daily_issues/generate_thesis_summaries | EOD 3태스크 통합(`update_indicator_readings`/`calculate_scores`/`create_snapshots_and_alerts`) + `generate_thesis_summaries` 4종 구현. **scan_thesis_news/update_popular_thesis_cache/prepare_daily_issues 미구현** | (B) 부분 구현 (4/8 ≈ 통합 형태로) |
| `plan/thesis_control_design.md` 6.1 — API 엔드포인트 | thesis CRUD/conversation/premises/indicators/dashboard/snapshots/summary/alerts/daily-issues/popular/templates | thesis CRUD/conversation(start,respond,news-issues,suggest)/premises/indicators(+auto)/dashboard/alerts/(close)/readings 까지 구현. **snapshots, summary 단독 엔드포인트 없음, daily-issues는 conversation/news-issues로 통합, popular/templates 완전 미구현** | (B) 부분 구현 (≈70%) |
| `plan/thesis_control_design.md` 7 Phase 1 | 가설 CRUD + 대화형 + 카드뷰 + 일별 update | 모두 구현 | (A) 완료 |
| `plan/thesis_control_design.md` 7 Phase 2 | 히트맵/그래프뷰/스냅샷 히스토리/변화감지/AI 요약/[근거]/뉴스 센티먼트/오늘 이슈 | 히트맵 데이터만 백엔드 존재(FE 미사용), 변화감지+AI 요약(`generate_thesis_summaries`)+오늘이슈(news-issues) 구현. **그래프뷰/스냅샷 히스토리/[근거]/뉴스 센티먼트 지표 미구현** | (B) ≈40% |
| `plan/thesis_control_design.md` 7 Phase 3 | 인기/따라하기/템플릿/Chain Sight 연동/마감 복기/Neo4j 그래프/아카이브 | **전부 미구현** | (C) 0% |
| `plan/thesis_control_design.md` 7 Phase 4 | 투자 지식 그래프 확장/유사상황 검색/추천 학습/연결 자동 발견/반대 가설 자동 생성 | **전부 미구현** | (C) 0% |

### B. 통합 로드맵 문서

| 설계 항목 | 코드 매핑 | 상태 |
|----------|----------|------|
| `integrated_roadmap.md` 1.2 HypothesisEvent 모델 | `thesis/models/learning.py` HypothesisEvent | (A) 완전 구현 |
| `integrated_roadmap.md` 1.3 ValidityRecord 모델 + 마감시 생성 | `thesis_views.py` close 액션이 자동 생성 | (A) 완전 구현 |
| `integrated_roadmap.md` 1.4 InvestorDNA 모델 + 마감시 자동 갱신 | `_update_investor_dna()` 호출 | (A) 완전 구현 |
| `integrated_roadmap.md` 2.1 ValidityScore 집계 (주1회 Celery) | 모델/태스크 미구현 | (C) 미구현 |
| `integrated_roadmap.md` 2.2 indicator_matcher에 유효성 반영 | `match_indicators_for_premise()`는 키워드 룰만 | (B) Phase 2 미반영 |
| `integrated_roadmap.md` 2.3 DNA 적합도 슬라이더 (personalization_weight) | 필드는 있으나 사용 코드 없음 | (B) 모델만 |
| `integrated_roadmap.md` 2.4 역제안 (Contrarian Nudge) | 미구현 | (C) 미구현 |
| `integrated_roadmap.md` 3.1 합성 에이전트 부트스트래핑 | 미구현 | (C) 미구현 |
| `integrated_roadmap.md` 3.2 Online Logistic Regression | 미구현 | (C) 미구현 |
| `integrated_roadmap.md` 3.3 합성/실제 블렌딩 | 미구현 | (C) 미구현 |
| `integrated_roadmap.md` 4 벡터 스코어링 | 미구현 | (C) 미구현 |

### C. 수학 모델 v2.3.2

| 설계 항목 | 코드 매핑 | 상태 |
|----------|----------|------|
| Stage 0 Validation | `services/data_validator.py` (90줄) + `IndicatorReading.validation_status` | (A) 완전 구현 |
| Stage 1 Robust Z + Decay | `services/indicator_scorer.py` (191줄) | (A) 완전 구현 |
| Stage 2 가중평균 + 최약고리 + 불일치 + 카테고리 중복 | `services/premise_aggregator.py` (205줄) | (A) 완전 구현 |
| Stage 3 Rule-based 상태 + 마감 리마인더 + data_coverage 보류 | `services/thesis_state_machine.py` (152줄) | (A) 완전 구현 |
| Snapshot (asof_date + universe + ordered list) | `services/snapshot_builder.py` (183줄) + `ThesisSnapshot.universe_snapshot/ordered_indicator_ids` | (A) 완전 구현 |
| Alert throttling (target_id + cooldown_hours) | `ThesisAlert.target_id/cooldown_hours` 필드 + `services/alert_engine.py` (272줄) | (A) 완전 구현 |
| Phase 2 — 상관계수 자동 할인 (60일 \|ρ\|≥0.9 → 1/√k) | premise_aggregator 내 미구현 | (C) 미구현 |
| Phase 2 — Adaptive Decay/Window | indicator_scorer 내 미구현 | (C) 미구현 |
| Phase 2 — Sustained Extreme (s_decayed≥3) | alert_engine 내 미구현 | (C) 미구현 |
| Phase 2 — 뉴스 센티먼트 → Stage 1 입력 | 미구현 | (C) 미구현 |

### D. Phase 3 대시보드 리디자인 (`phase3_frontend_redesign.md`)

| PR | 핵심 산출물 | 코드 매핑 | 상태 |
|----|------------|----------|------|
| PR-7 백엔드 | `display_unit` 필드 + `raw_value/previous_raw_value/change_pct` 응답 + `IndicatorReadingsView` | 마이그레이션 0004/0005, `monitoring_views.py` DashboardView/IndicatorReadingsView 확장, urls.py readings 라우트 | (A) 완전 구현 |
| PR-8 카드+AI분석 | `RealValueIndicatorCard.tsx`, `AISummarySection.tsx`, `NotableChangesSection.tsx` | 3개 모두 존재 (`frontend/components/thesis/dashboard/`) | (A) 완전 구현 |
| PR-9 미니차트 + 기간 선택 + 정리 | `ChartToggleButton`, `PeriodSelector`, `IndividualMiniCharts`; OverallMoon/DashboardIndicatorCard/RecentChange 삭제 | 3개 컴포넌트 존재. **다만 `[thesisId]/page.tsx`는 ChartToggleButton/PeriodSelector/IndividualMiniCharts를 직접 사용하지 않고 `IndicatorRow.tsx`(274줄, ChevronDown 인라인 토글)로 통합**. OverallMoon/DashboardIndicatorCard/RecentChange는 폴더에서 사라짐 (삭제됨) | (B) 형태 변경 — 분리된 컴포넌트 대신 IndicatorRow 인라인 패턴 채택, 결과적 UX는 동일/우월 |
| PR-10 AI 파이프라인 | `generate_thesis_summaries` Celery + `notable_changes` JSONField 채움 | `tasks/summary.py` + `config/celery.py` beat schedule 등록 | (A) 완전 구현 |

### E. 빌더 재설계 v4 (`talking_builder/redesign_build_plan/`)

| Phase / PR | 핵심 산출물 | 코드 매핑 | 상태 |
|-----------|------------|----------|------|
| A-MVP PR-1 (백엔드 기반) | builder_state, prompt_builder, llm_postprocess, builder_events, feature_flags | `services/builder_state.py`(114), `prompt_builder.py`(991), `llm_postprocess.py`(217), `builder_events.py`(39), `feature_flags.py` 모두 존재 | (A) 완전 구현 |
| A-MVP PR-2 (백엔드 로직) | process_llm_turn, indicator_matcher PK, views mode 분기 | `thesis_builder.py`(2059줄) + `indicator_matcher.py`(338줄) + `conversation_views.py` mode 분기 | (A) 완전 구현 |
| A-MVP PR-3 (프론트엔드) | BuilderPhase, PresetSelector, IndicatorCard | `types.ts`에 BuilderPhase/ConversationState/SuggestResponse 정의, `components/thesis/PresetSelector.tsx` 존재, `components/thesis/IndicatorCard.tsx` 존재, `app/thesis/new/page.tsx`(1072줄) | (A) 완전 구현 |
| A-Hardening PR-4~7 (normalize 보강·fallback 안정화·로그 지표·FE 에러 바운더리) | builder_stats, FallbackReason | `management/commands/builder_stats.py` 존재, FallbackReason enum 존재 | (A) 대부분 구현 |
| B PR-8 KeywordCache 모델 + Admin + Cache Ops | `models/keyword.py` + KeywordCacheAdmin + save_keywords/collect_from_cache | `models/keyword.py`(46), `services/keyword_cache.py`(78), 마이그레이션 0006/0007, `management/commands/check_keywords.py` 존재 | (A) 완전 구현 |
| B PR-9 News Keyword Collector | `services/keyword_collectors/news.py` | 존재 | (A) 완전 구현 |
| B PR-10 EOD + Chain Collectors | `services/keyword_collectors/{eod,chain}.py` | 둘 다 존재 | (A) 완전 구현 |
| B PR-11 Keyword Hint 빌더 통합 | `services/keyword_hint.py` + prompt 통합 | `keyword_hint.py`(100) 존재 | (A) 완전 구현 |
| B PR-12 멀티턴 수정 대화 | MULTI_TURN_EDIT 플래그 | `feature_flags.py` MULTI_TURN_EDIT=False (모델만, 활성 안 됨) | (B) 골격만 |
| C 단계 (Health Report·keyword 고도화·스트리밍 등) | — | 미구현 | (C) 미구현 |
| 추가: NEWS_SUGGESTIONS_ENABLED | SuggestThesesView + SuggestionData | `conversation_views.py` SuggestThesesView 구현, feature_flags에 활성, FE에 ThesisSuggestion/SuggestResponse 타입 | (A) 완전 구현 (계획 외 확장) |

### F. Phase 1 FE-PR-1~6 (Phase 2 완료 보고서 기준)

| PR | 핵심 산출물 | 코드 매핑 | 상태 |
|----|------------|----------|------|
| FE-PR-1 라우팅 + 공통 | `lib/api/authAxios.ts`, `lib/thesis/{types,utils,api,queries}.ts`, common 5종 | `lib/thesis/`에 9개 모듈 + common 6 컴포넌트(ArrowIndicator/MoonPhase/IndicatorCard/ThesisBadge/AlertBell/BottomSheet) | (A) 완전 구현 |
| FE-PR-2 가설 목록 | ThesisListCard, EntryPointGrid, TodayChangeCard | 3개 모두 존재 | (A) 완전 구현 |
| FE-PR-3 대화형 빌더 | builder/ 7컴포넌트 + conversation.ts | builder/ 9컴포넌트(BottomSheet/ChatBubble/MultiSelectFooter/NewsSelector/OptionButton/PremiseCard/ProgressBar/SuggestionCard/TextInput) | (A) 완전 구현 + 확장 (NewsSelector/SuggestionCard 추가) |
| FE-PR-4 지표 설정 | IndicatorSetupCard, RecommendCard, AddIndicatorSheet | 3개 모두 존재 (`components/thesis/indicators/`) | (A) 완전 구현 |
| FE-PR-5 대시보드 (달 위상 + 화살표) | DashboardPageHeader, DashboardHeader, OverallMoon, DashboardIndicatorCard, RecentChange | OverallMoon/DashboardIndicatorCard/RecentChange는 **삭제됨** (PR-9 정리). DashboardPageHeader/DashboardHeader만 유지 | (D) 폐기/대체 — Phase 3 리디자인이 OverallMoon/카드/RecentChange를 RealValueIndicatorCard/AISummarySection/NotableChangesSection으로 교체 |
| FE-PR-6 알림 + 마감 | AlertFilterTabs/AlertCard/EmptyAlerts + OutcomeSelector/CloseConfirmDialog | 5개 모두 존재 | (A) 완전 구현 |

### G. Phase 1 BE 프롬프트 (`thesis_control_phase1_prompts.md`)

대부분 v2.3.2 수학 엔진 사양으로 수렴됨. (A) 수렴 완료.

### H. UX 일반 (`thesis_control_user_experience.md`, design 2.3 5경로)

| 진입 경로 | 코드 매핑 | 상태 |
|----------|----------|------|
| 경로 1: 📰 오늘 이슈 | `NewsIssuesView` + `NewsSelector` + `SuggestThesesView` | (A) 구현 |
| 경로 2: 💬 내 생각 (자유 입력) | `entry_source='free_input'` + LLM 빌더 one-shot | (A) 구현 |
| 경로 3: 🔥 인기 가설 | `entry_source='popular'` (모델 enum만), API/UI 없음 | (C) 미구현 |
| 경로 4: 📋 템플릿 | `entry_source='template'` (모델 enum만), API/UI 없음 | (C) 미구현 |
| 경로 5: 🔗 Chain Sight | `entry_source='chainsight'` (모델 enum만), API/UI 없음 | (C) 미구현 |

---

## Phase 3 미구현 항목 상세

### 핵심 발견: 두 개의 "Phase 3" 계획 충돌 → 후자 채택

`Phase2_completion_summary.md` (2026-03-16, ff0cb29 커밋)에는 다음 FE-PR-7~11이 예고됨:

| PR | 제목 | 핵심 |
|----|------|------|
| FE-PR-7 | 대시보드 탭 구조 + 상세 탭 | 3탭 (관제/상세/히스토리) + 전제 CRUD |
| FE-PR-8 | 히트맵 + 지표 상세 편집 | Finviz 스타일 히트맵 + weight/direction 편집 |
| FE-PR-9 | 히스토리 탭 | recharts 라인 차트 + 스냅샷 타임라인 |
| FE-PR-10 | 마감 아카이브 + 요약 | 마감 가설 목록 + ValidityMatrix |
| FE-PR-11 | 투자자 DNA 프로필 | AccuracyRing + CategoryChart + 기술 부채 정리 |

이 5건은 **2026-03-18 작성된 `plan/thesis_control_phase3_frontend_redesign.md`로 폐기**되었다 (배경 0.1: "Phase 2까지 구현된 대시보드가 달 위상, 화살표 각도, 내부 점수 같은 추상적 시각화에 의존… 매일 비슷한 화면이 되고, 투자 의사결정에 실질적 도움이 안 됨"). 재정의된 PR-7~10은 **모두 구현 완료**된 상태다(위 D 표).

따라서 사용자 질문의 "Phase 3 (깊이 + 회고 + 프로필) 설계 vs 현재 구현 상태" 및 "FE-PR-7~11 설계 vs 실제 컴포넌트"는 다음과 같이 정리된다:

#### (D) 폐기 — 원안 FE-PR-7~11
원안의 5개 PR은 **착수되지 않았고** 재설계로 대체되었다. 코드베이스에 다음 흔적이 없다:
- 대시보드 탭 구조 (3탭 라우터/UI 없음). `[thesisId]/page.tsx`는 단일 페이지 구조.
- Finviz 히트맵 컴포넌트 없음 (백엔드 `heatmap` 응답 필드만 잔존, FE 미사용).
- 스냅샷 타임라인 차트 없음 (`/snapshots/` 엔드포인트도 없음).
- 마감 아카이브 라우트 없음 (마감된 가설 목록은 `/thesis/?status=closed` 쿼리는 가능하나 전용 UI 없음).
- ValidityMatrix UI 없음.
- 투자자 DNA 프로필 라우트/컴포넌트 없음 (백엔드 `InvestorDNA` 모델 + 자동 갱신은 존재하나, 노출 API 0건, FE 0건).

#### (A) 완전 구현 — 재정의 PR-7~10
- `display_unit` 필드 + `raw_value`/`previous_raw_value`/`change_pct` 응답 (PR-7)
- `RealValueIndicatorCard.tsx` (90줄), `AISummarySection.tsx` (34줄), `NotableChangesSection.tsx` (64줄) (PR-8)
- `ChartToggleButton.tsx` (23줄), `PeriodSelector.tsx` (29줄), `IndividualMiniCharts.tsx` (104줄), `QuarterlySparkline.tsx` (68줄) (PR-9 컴포넌트 존재)
- `generate_thesis_summaries` Celery task + Beat 등록 (PR-10)

#### (B) 형태 변경 — IndicatorRow 통합 패턴 채택
PR-9 설계는 카드 그리드 + 별도 ChartToggleButton/PeriodSelector/IndividualMiniCharts 시퀀스를 권장했지만, 실제 구현은 **`IndicatorRow.tsx` (274줄)**으로 카드+차트를 행 단위로 통합한 인라인 토글 패턴(ChevronDown 클릭 → 펼침 영역에 1M/1Y/3Y/5Y 기간 선택 + AreaChart + 분기 스파크라인)을 사용한다. 결과 UX는 설계 의도(차트 기본 숨김, 토글 표시)를 충족하되 분리된 컴포넌트 3종(ChartToggleButton/PeriodSelector/IndividualMiniCharts)은 페이지에서 직접 사용되지 않는다. 잔존 가능성: PR-9의 일부 빌딩 블록은 작성됐으나 최종 페이지 합성 단계에서 IndicatorRow로 단순화됨.

### Phase 3 (`integrated_roadmap.md` 기준)에서 누락된 항목

`integrated_roadmap.md` Section 3 "Phase 3 — 합성 에이전트 + 자동학습"과 `design.md` Section 7 Phase 3 "커뮤니티 + 고도화"를 합산한 누락 항목:

| 영역 | 항목 | 위치 |
|------|------|------|
| 커뮤니티 | 인기 가설 시스템 (`PopularThesisCache` Celery 갱신 + `/popular/` API) | (C) 미구현 |
| 커뮤니티 | 가설 따라하기 (`/popular/{id}/follow/`) | (C) 미구현 |
| 커뮤니티 | 템플릿 시스템 (`/templates/`, 이벤트형/추세형/비교형/괴리형 4종) | (C) 미구현 |
| 통합 | Chain Sight ↔ Thesis Control 양방향 진입점 | (C) 미구현 (모델 enum만) |
| 학습 | ValidityScore 집계 (주1회 Celery) | (C) 미구현 |
| 학습 | indicator_matcher에 유효성 점수 반영 (core/reference/low_impact 티어) | (C) 미구현 |
| 학습 | DNA 적합도 슬라이더 (personalization_weight) UI + 블렌딩 | (B) 모델만 |
| 학습 | 역제안 (Contrarian Nudge) | (C) 미구현 |
| 학습 | 합성 에이전트 부트스트래핑 (SyntheticBootstrapper, 페르소나 20~30개) | (C) 미구현 |
| 학습 | Online Logistic Regression (ThesisWeightLearner) | (C) 미구현 |
| 학습 | 합성/실제 데이터 블렌딩 (`is_synthetic` 필드) | (C) 미구현 (필드 없음) |
| 복기 | 가설 마감 복기 시스템 (유용했던 지표/예상과 달랐던 부분) | (C) 미구현 (close API는 outcome만 받음) |
| 복기 | 가설 아카이브 + 학습 이력 UI | (C) 미구현 |
| 그래프 | Neo4j 가설 관계 그래프 (`HAS_PREMISE`/`SIMILAR_TO`/`OPPOSITE_OF`) | (C) 미구현 |
| 모니터링 강화 | 히트맵 뷰 FE (백엔드 데이터 있음, FE 미사용) | (B) 백엔드만 |
| 모니터링 강화 | 그래프 뷰 (시계열 선 그래프 — 지지/중립/반박 Y축) | (C) 미구현 (개별 IndicatorRow 차트만 존재) |
| 모니터링 강화 | 스냅샷 히스토리 API (`GET /{id}/snapshots/`) | (C) 미구현 |
| 모니터링 강화 | [근거] 설명 시스템 + Redis 캐싱 | (C) 미구현 (`recommendation_reason` 단일 필드만) |
| 모니터링 강화 | 뉴스 센티먼트 지표 (Stage 1 입력) | (C) 미구현 |
| 모니터링 강화 | 내러티브 반감기 (`narrative_momentum` 지표) | (C) 미구현 |
| 모니터링 강화 | 상관계수 자동 할인 (60일 \|ρ\|≥0.9 → 1/√k) | (C) 미구현 |
| 모니터링 강화 | Adaptive Decay/Window | (C) 미구현 |
| 모니터링 강화 | Sustained Extreme alert | (C) 미구현 |

---

## 백엔드 코드베이스 요약

| 영역 | 파일 수 | 총 줄 수 | 비고 |
|------|--------|---------|------|
| `thesis/models/` | 7 (incl. `__init__`) | 684 | thesis/indicator/monitoring/community/learning/keyword |
| `thesis/services/` | 17 | 5478 | 수학 엔진(7) + 빌더(7) + 키워드(3) |
| `thesis/views/` | 3 + `__init__` | 1095 | thesis_views(336)/conversation_views(380)/monitoring_views(364)/`__init__`(15) |
| `thesis/serializers/` | 4 + `__init__` | 226 | thesis/indicator/monitoring/conversation |
| `thesis/tasks/` | 2 + `__init__` | 682 | eod_pipeline(534) + summary(142) |
| `thesis/migrations/` | 9 | — | 0001~0009, display_unit/keyword/strength/metrics_data/recommendation_reason 포함 |
| `thesis/management/commands/` | 3 | — | builder_stats, keyword_health_check, check_keywords |
| `thesis/feature_flags.py` | 1 | 21 | LLM_BUILDER_ENABLED + 키워드 플래그 |

## 프론트엔드 코드베이스 요약

| 영역 | 파일 수 | 총 줄 수 | 비고 |
|------|--------|---------|------|
| `frontend/lib/thesis/` | 9 | 1829 | api/types/queries/mutations/utils/constants/conversation/mock/indicatorMutations |
| `frontend/components/thesis/` | 30+ | — | builder(9)/dashboard(10)/list(3)/alerts(3)/close(2)/common(6)/indicators(3)/skeleton(1) + 루트 3 |
| `frontend/app/thesis/` | 7 라우트 | ≈1981 | (list)/, (list)/alerts/, new/, [thesisId]/, [thesisId]/indicators/, [thesisId]/close/, layouts |

---

## 추가 관찰 (설계 외 확장)

| 항목 | 위치 | 설명 |
|------|------|------|
| 분기 지표 시스템 | `services/quarterly_metric_fetcher.py` (364줄), 마이그레이션 0008 | 설계엔 없는 분기 펀더멘털 fetcher (RATIO_METRICS % 변환 포함). `IndicatorRow`의 `is_quarterly`/`comparison_type`/`quarterly_history` 필드 사용. |
| News Suggestions API | `SuggestThesesView` + `feature_flags.py` `NEWS_SUGGESTIONS_ENABLED=True` | 뉴스 클릭 시 bullish/bearish 가설 2개 자동 제안. 빌더 v4 04_phase_c에 없는 추가 플로우. |
| FMP history fallback | `monitoring_views.py:_fetch_fmp_history` | DB readings가 부족하면 FMP `/historical-price-eod`로 fallback. 차트 5Y까지 지원. |
| 지표 카탈로그 description | `prompt_builder.py:get_indicator_description` | 카탈로그에서 지표 설명 자동 주입. 대시보드 펼침 영역에 표시. |

---

## 분류 카운트

- (A) 완전 구현: **18개 영역**
- (B) 부분 구현: **9개 영역**
- (C) 미구현: **23개 영역**
- (D) 폐기/대체: **4개 영역** (closed_correct/incorrect/neutral status, alert_type 분류, OverallMoon/DashboardIndicatorCard/RecentChange 패턴, 원안 FE-PR-7~11)

## 종합 결론

1. **수학 엔진(v2.3.2) + Phase 1 MVP + Phase 1 FE-PR-1~6 + Phase 3 재설계(PR-7~10) + 빌더 v4 Phase A/B**는 모두 완전 구현되어 있다.
2. **원안 FE-PR-7~11(탭/히트맵/히스토리/아카이브/DNA)은 폐기**되었고, 대신 대시보드 리디자인 PR-7~10이 채택되어 구현됐다. 단, "회고(복기)"와 "프로필(DNA)"이라는 사용자 가치는 어느 PR에도 들어가지 못한 상태로 남아 있다.
3. **Phase 2 모니터링 강화(히트맵/그래프뷰/스냅샷 히스토리/[근거]/뉴스 센티먼트/내러티브)와 Phase 2 개인화(ValidityScore/DNA 슬라이더/역제안), Phase 3 커뮤니티(인기/템플릿/Chain Sight 연동), Phase 3 자동학습(합성 에이전트/Online LR), Phase 3 복기/Neo4j**는 모두 미구현 상태다.
4. 정량적으로 본 진행도는 ≈ **수학+MVP 100% / Phase 2 모니터링 30% / Phase 2 개인화 5% / Phase 3 커뮤니티·복기·DNA·Neo4j 0% / Phase 4 0%**.
