# Thesis Control Phase 2 프론트엔드 — 완료 요약

> 완료일: 2026-03-16 (최종 커밋)
> 브랜치: `feat/eod-dashboard-and-improvements`
> 커밋: `ff0cb29`

---

## 1. Phase 2 목표

**핵심 루프 완성**: 목록 → 빌더 → 지표 설정 → 대시보드 → 알림 → 마감

---

## 2. PR 구성 및 완료 현황

| PR | 제목 | 파일 수 | 줄 수 | 완료일 | 보고서 |
|----|------|--------|-------|--------|--------|
| FE-PR-1 | 라우팅 + 공통 컴포넌트 | 18 | ~500 | 03-10 | `FE-PR-1_routing_common_components.md` |
| FE-PR-2 | 가설 목록 + 오늘의 변화 + 진입점 | 14 | ~600 | 03-11 | `FE-PR-2_thesis_list_page.md` |
| FE-PR-3 | 대화형 빌더 (6단계 플로우) | 9 | ~820 | 03-13 | `FE-PR-3_builder_implementation.md` |
| FE-PR-4 | 지표 설정 (AI 추천 + 토글/삭제) | 12 | ~460 | 03-13 | `FE-PR-4_indicator_setup.md` |
| FE-PR-5 | 관제실 대시보드 (달 위상 + 화살표) | 11 | ~400 | 03-14 | `FE-PR-5_dashboard.md` |
| FE-PR-6 | 알림 + 마감 + API 수정 + QA | 20 | ~600 | 03-14 | `FE-PR-6_alerts_close_qa.md` |
| **합계** | | **84** | **~3,380** | | |

---

## 3. 최종 코드베이스 통계

| 항목 | 수량 |
|------|------|
| 컴포넌트 | 30개 (common 5, dashboard 5, list 3, indicators 3, alerts 3, close 2, builder 7, skeleton 2) |
| 페이지 | 8개 라우트 (6개 page.tsx) |
| 유틸리티 모듈 | 9개 (types, api, queries, mutations, mock, utils, constants, conversation, indicatorMutations) |
| 전체 줄 수 | ~4,058줄 TypeScript/TSX |

---

## 4. 라우팅 구조 (최종)

```
/thesis                          ← 가설 목록 (route group: (list))
/thesis/new?entry={source}       ← 대화형 빌더 (6단계)
/thesis/alerts                   ← 알림 목록 (필터 3탭)
/thesis/[thesisId]               ← 관제실 대시보드
/thesis/[thesisId]/indicators    ← 지표 설정 (AI 추천)
/thesis/[thesisId]/close         ← 마감 (Outcome 선택)
```

**레이아웃 분리**:
- `thesis/layout.tsx`: Toaster + fadeIn 전용 (헤더 없음)
- `thesis/(list)/layout.tsx`: 목록 전용 헤더 + AlertBell

---

## 5. 기술 스택 & 아키텍처

### API 레이어
- `lib/api/client.ts` → `authAxios`: JWT 인터셉터 + 토큰 갱신 + 멀티탭 동기화
- `lib/thesis/api.ts`: thesis 전용 API 함수 (11개 엔드포인트)

### 서버 상태 관리
- TanStack Query v5: `useTheses()`, `useDashboard()`, `useIndicators()`, `useAlerts()`
- Query Key 패턴: `QUERY_KEYS.theses`, `QUERY_KEYS.dashboard(id)`, etc.
- `enabled: !USE_MOCK && !!id` 조건으로 Mock 모드 분기

### Mutation 훅
- `mutations.ts`: 통합 mutation (지표 3 + 알림 1 + 마감 1)
- `indicatorMutations.ts`: 지표 전용 (add/remove/toggle)
- 낙관적 업데이트 + invalidateQueries 조합

### Mock 모드
- `USE_MOCK = true` → API 호출 없이 고정 데이터로 전체 플로우 동작
- 모든 페이지/컴포넌트에서 Mock fallback 구현
- Mock 데이터: 가설 3개, 지표 3개, AI 추천 3개, 알림 4개, 대시보드 전체

---

## 6. 핵심 화면별 기능

### 가설 목록 (`/thesis`)
- `ThesisCard`: 달 위상 아이콘 + 점수 배지 + 방향 표시 + long-press 삭제
- `EntryPointGrid`: 뉴스 기반 / 자유 입력 진입점 2개
- `TodayChange`: 오늘의 변화 섹션 (알림 요약)

### 대화형 빌더 (`/thesis/new`)
- 6단계 가이드 대화 (AI 질문 → 사용자 응답)
- 단일/복수 선택 + 자유 텍스트 입력
- Long-press 설명 (500ms → BottomSheet)
- 에러 복구: `lastRequest` 기반 해당 단계 재시도
- 완료 후 3갈래 라우팅 (자동 지표/수동 지표/나중에)

### 지표 설정 (`/thesis/[id]/indicators`)
- `IndicatorSetupCard`: 활성/비활성 토글 + 삭제
- `AddIndicatorSheet`: AI 추천 바텀시트 (`/indicators/auto/`)
- `RecommendCard`: 추천 지표 카드 (Sparkles 아이콘 + 이유)

### 관제실 대시보드 (`/thesis/[id]`)
- `OverallMoon`: 전체 점수 달 위상 시각화 (lg)
- `DashboardIndicatorCard`: 화살표 degree + 트렌드 감지 (extreme volatility 경고)
- `RecentChange`: 최근 변화 내러티브 텍스트

### 알림 (`/thesis/alerts`)
- `AlertFilterTabs`: 전체/안읽은/읽은 3탭 필터
- `AlertCard`: severity 배지 (low/medium/high/critical) + 읽음 처리
- `EmptyAlerts`: 필터별 빈 상태 메시지 3종

### 마감 (`/thesis/[id]/close`)
- `OutcomeSelector`: 적중/빗나감/미확정 카드형 라디오
- `CloseConfirmDialog`: "되돌릴 수 없음" 경고 + 최종 확인

---

## 7. 부수 변경 (백엔드)

| 파일 | 변경 |
|------|------|
| `config/celery.py` | Celery 에러 모니터링 설정 |
| `config/settings.py` | 관련 설정 추가 |
| `config/tasks.py` | Celery 에러 모니터링 태스크 |
| `config/management/commands/celery_errors.py` | 에러 조회 관리 커맨드 |
| `thesis/serializers/monitoring_serializers.py` | 필드 수정 |

---

## 8. Phase 3 계획

Phase 2 핵심 루프 위에 **깊이 + 회고 + 프로필** 추가:

| PR | 제목 | 핵심 |
|----|------|------|
| FE-PR-7 | 대시보드 탭 구조 + 상세 탭 | 3탭 (관제/상세/히스토리) + 전제 CRUD |
| FE-PR-8 | 히트맵 + 지표 상세 편집 | Finviz 스타일 히트맵 + weight/direction 편집 |
| FE-PR-9 | 히스토리 탭 | recharts 라인 차트 + 스냅샷 타임라인 |
| FE-PR-10 | 마감 아카이브 + 요약 | 마감 가설 목록 + ValidityMatrix |
| FE-PR-11 | 투자자 DNA 프로필 | AccuracyRing + CategoryChart + 기술 부채 정리 |
