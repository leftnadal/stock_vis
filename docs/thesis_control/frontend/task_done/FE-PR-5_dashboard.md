# FE-PR-5: 관제실 대시보드 — 완료 보고서

> 완료일: 2026-03-14
> 브랜치: `feat/eod-dashboard-and-improvements`
> 설계 문서: `docs/thesis_control/thesis_control_phase1_frontend_FE_PR_5.md` (v2)

---

## 1. 구현 완료 파일 목록 (11개)

### 신규 생성 (6개)

| # | 파일 | 역할 | 줄 수 |
|---|------|------|-------|
| 1 | `components/thesis/dashboard/DashboardPageHeader.tsx` | 페이지 헤더 (뒤로가기 + "관제실" + 새로고침) | 41 |
| 2 | `components/thesis/dashboard/DashboardHeader.tsx` | 가설 정보 (제목 + ThesisBadge + 추적 일수) | 25 |
| 3 | `components/thesis/dashboard/OverallMoon.tsx` | 전체 점수 달 위상 시각화 (MoonPhase lg) | 24 |
| 4 | `components/thesis/dashboard/DashboardIndicatorCard.tsx` | 개별 지표 카드 (화살표 + 트렌드 + 전제) | 61 |
| 5 | `components/thesis/dashboard/RecentChange.tsx` | 최근 변화 내러티브 텍스트 | 26 |
| 6 | `lib/thesis/constants.ts` | `TREND_CONFIG` (트렌드 아이콘/라벨/색상) | 34 |

### 기존 파일 수정 (4개)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 7 | `lib/thesis/types.ts` | `DashboardThesis`, `DashboardIndicator`, `HeatmapCell`, `HeatmapData`, `DashboardResponse` 타입 추가, `overall_delta` optional 필드 |
| 8 | `lib/thesis/utils.ts` | `scoreToPhaseMeta()`, `scoreToBadgeState()`, `sanitizeHexColor()` 3개 유틸 추가 |
| 9 | `lib/thesis/queries.ts` | `useDashboard(thesisId)` 훅 추가, `enabled: !USE_MOCK && !!thesisId` 조건 |
| 10 | `lib/thesis/mock.ts` | `MOCK_DASHBOARD: DashboardResponse` 추가 (thesis + indicators 3개 + heatmap) |

### 전면 교체 (1개)

| # | 파일 | 변경 내용 | 줄 수 |
|---|------|----------|-------|
| 11 | `app/thesis/[thesisId]/page.tsx` | placeholder → 대시보드 전체 구현 | 128 |

---

## 2. 설계 철학: "숫자가 아니라 분위기를 먼저 느끼게"

대시보드는 정량 데이터를 감성적 시각화로 변환하는 데 초점:

```
overall_score (숫자)  →  MoonPhase (달 위상)  →  "조금씩 밝아지고 있어요" (자연어 라벨)
arrow_degree (각도)   →  ArrowIndicator (화살표)  →  색상 + 트렌드 배지
```

---

## 3. 컴포넌트 설계 상세

### 3.1 대시보드 페이지 구조

```
[thesisId]/page.tsx
├── DashboardPageHeader       ← 뒤로가기 + "관제실" + RefreshCw
├── DashboardHeader           ← 가설 제목 + ThesisBadge + "N일째 관제 중"
├── OverallMoon               ← MoonPhase (lg) + overall_label + score
├── DashboardIndicatorCard[]  ← grid-cols-2 sm:grid-cols-3
├── RecentChange              ← Activity 아이콘 + 내러티브 텍스트
└── Footer                    ← "지표 설정" + "가설 마감" 버튼
```

### 3.2 DashboardPageHeader

| 영역 | 내용 |
|------|------|
| 좌측 | ArrowLeft → `/thesis` 이동 |
| 중앙 | "관제실" |
| 우측 | RefreshCw (showRefresh=true 시, isLoading 시 spin 애니메이션) |

`DashboardPageHeader` 컴포넌트 추출로 로딩/에러/정상 3곳의 헤더 JSX 중복 제거.

### 3.3 OverallMoon

- `MoonPhase` 컴포넌트 (size="lg") 재사용
- `scoreToPhaseMeta(score)` → phase + label 계산
- 점수 표시: `+0.45` / `-0.30` 형식 (부호 명시)

### 3.4 DashboardIndicatorCard

| 영역 | 내용 |
|------|------|
| 상단 | ArrowIndicator (arrow_degree) + 색상 (sanitizeHexColor 검증) |
| 중단 | 지표명 (truncate) + label |
| 하단 | 트렌드 배지 (TREND_CONFIG) + premise_name |

**트렌드 라벨 분기**:
- `previous_degree` 존재 시: "강화 중 (전일 대비 ↑)" 상세 라벨
- `previous_degree` null 시: "강화", "약화", "유지" 단축 라벨

**극단 변동성 표시**: `is_extreme_vol=true` 시 경고 아이콘 (|z_raw| >= 5.0)

### 3.5 RecentChange

- `thesis.recent_change` null 체크 → null이면 미렌더링
- Activity 아이콘 + "최근 변화" 라벨 + 내러티브 텍스트

---

## 4. TREND_CONFIG 상수

```ts
// constants.ts
export const TREND_CONFIG: Record<string, TrendMeta> = {
  strengthening: {
    icon: TrendingUp,
    label: '강화',
    labelWithDelta: '강화 중 (전일 대비 ↑)',
    className: 'text-green-400',
  },
  weakening: {
    icon: TrendingDown,
    label: '약화',
    labelWithDelta: '약화 중 (전일 대비 ↓)',
    className: 'text-orange-400',
  },
  stable: {
    icon: Minus,
    label: '유지',
    labelWithDelta: '유지 (변화 없음)',
    className: 'text-gray-400',
  },
}
```

Phase 2 히트맵, 알림에서도 재사용 가능하도록 `constants.ts`로 추출.

---

## 5. 유틸 함수 상세

### 5.1 scoreToPhaseMeta

| score 범위 | phase | label |
|-----------|-------|-------|
| > 0.6 | full_moon | 가설이 빛나고 있어요 |
| > 0.2 | waxing | 조금씩 밝아지고 있어요 |
| > -0.2 | half_moon | 반반이에요 |
| > -0.6 | waning | 조금씩 어두워지고 있어요 |
| ≤ -0.6 | new_moon | 가설이 힘을 잃고 있어요 |

### 5.2 scoreToBadgeState

대시보드에서는 `current_state`가 아닌 `overall_score`로 ThesisBadge 상태를 유추:

```ts
export function scoreToBadgeState(score: number, status: ThesisStatus): ThesisState {
  if (status !== 'active') return 'active'
  if (score > 0.2) return 'strengthening'
  if (score < -0.2) return 'weakening'
  return 'active'
}
```

기술 부채: 백엔드에 `current_state` 필드 추가 시 이 함수만 교체.

### 5.3 sanitizeHexColor

```ts
const HEX_COLOR_RE = /^#[0-9A-Fa-f]{6}$/
export function sanitizeHexColor(color: string, fallback = '#9CA3AF'): string {
  return HEX_COLOR_RE.test(color) ? color : fallback
}
```

백엔드 color 값 검증 + CSS injection 방어.

---

## 6. 타입 정의 상세

### DashboardThesis

| 필드 | 타입 | 설명 |
|------|------|------|
| id | string | thesis id |
| title | string | 가설 제목 |
| direction | Direction | bullish/bearish/neutral |
| status | ThesisStatus | active/closed 등 |
| days_active | number | 추적 일수 |
| overall_score | number | -1.0 ~ 1.0 |
| overall_label | string | 자연어 요약 |
| overall_phase | string | 달 위상 키 |
| recent_change | string | 최신 변화 텍스트 |
| overall_delta? | number \| null | 전일 대비 변화 (백엔드 추가 시 활용) |

### DashboardIndicator

| 필드 | 타입 | 설명 |
|------|------|------|
| id | string | indicator id |
| name | string | 지표명 |
| arrow_degree | number | 0~180 (소수점 1자리) |
| score | number | -1.0 ~ 1.0 |
| color | string | hex 색상 |
| label | string | "지지하는 편" 등 |
| previous_degree | number \| null | 이전 각도 (trend 계산용) |
| trend | string | stable/strengthening/weakening |
| premise_name | string | 전제 요약 (50자) |
| is_extreme_vol | boolean | |z_raw| >= 5.0 |

---

## 7. Mock 대시보드 데이터

```
thesis: 32일 추적, score 0.45, waxing phase
indicators:
  ├── 외국인 순매수 추이: degree 35.2, score 0.65, strengthening
  ├── 원/달러 환율: degree 110.5, score -0.3, weakening
  └── VIX: degree 88.0, score 0.02, stable
heatmap: 1×3 (3셀)
```

---

## 8. 페이지 Flow

```
마운트
├── useDashboard(thesisId)  → DashboardResponse
├── isLoading               → DashboardPageHeader + 로딩 스켈레톤
├── isError                 → DashboardPageHeader + 에러 UI + 새로고침
├── Mock 모드               → MOCK_DASHBOARD 직접 사용
└── 정상
    ├── DashboardPageHeader (새로고침 버튼 표시)
    ├── DashboardHeader (제목 + 배지)
    ├── OverallMoon (달 위상)
    ├── DashboardIndicatorCard[] (grid)
    ├── RecentChange (내러티브)
    └── Footer
        ├── "지표 설정"    → /thesis/{id}/indicators
        └── "가설 마감"    → /thesis/{id}/close
```

---

## 9. 공통 컴포넌트 재사용

| 컴포넌트 | 원래 PR | 대시보드 사용 |
|---------|---------|-------------|
| MoonPhase | PR-1 | OverallMoon (size="lg") |
| ThesisBadge | PR-1, PR-2 리팩토링 | DashboardHeader (scoreToBadgeState 기반) |
| ArrowIndicator | PR-1 | DashboardIndicatorCard (arrow_degree) |

---

## 10. 설계 결정

| 결정 | 선택 | 근거 |
|------|------|------|
| DashboardPageHeader 추출 | 컴포넌트 분리 | 로딩/에러/정상 3곳 헤더 중복 제거 |
| scoreToBadgeState 유틸 | 함수 추출 | 인라인 삼항 중첩 제거, Phase 2 재사용 |
| sanitizeHexColor | 프론트 검증 | CSS injection 방어, 백엔드 무관 안전성 |
| overall_delta optional | 선행 타입 선언 | 백엔드 추가 시 프론트 즉시 활용 가능 |
| 그리드 반응형 | `grid-cols-2 sm:grid-cols-3` | 모바일 320px에서 3열 가독성 문제 해결 |
| TREND_CONFIG 위치 | `constants.ts` | 컴포넌트 내부 → 공유 파일로 추출 |

---

## 11. 기술 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| `tsc --noEmit` | 에러 0건 |
| `npm run build` | 성공, `/thesis/[thesisId]` 라우트 정상 |
| Mock 달 위상 표시 | waxing (score 0.45) 정상 |
| Mock 지표 카드 3개 | 화살표 + 트렌드 배지 + 색상 정상 |
| Mock 최근 변화 | 내러티브 텍스트 정상 렌더링 |
| "지표 설정" 링크 | `/thesis/mock-1/indicators`로 이동 |
| "가설 마감" 링크 | `/thesis/mock-1/close`로 이동 |

---

## 12. 기술 부채

| 부채 | 영향 | 해소 시점 |
|------|------|----------|
| scoreToBadgeState로 상태 유추 | 백엔드 current_state와 불일치 가능 | 백엔드 DashboardThesis에 current_state 추가 시 |
| overall_delta 미사용 | 전일 대비 변화 표시 불가 | 백엔드 구현 후 |
| 히트맵 시각화 미구현 | HeatmapData 타입만 존재 | Phase 3 |
| 실시간 갱신 없음 | 수동 새로고침만 가능 | WebSocket 또는 polling 도입 시 |

---

## 13. 후속 PR 연결

| 이 PR에서 만든 것 | 사용하는 PR |
|------------------|------------|
| DashboardPageHeader | PR-5 전용 |
| DashboardIndicatorCard | PR-5 전용 (Phase 3 히트맵에서 재설계) |
| TREND_CONFIG | Phase 3 히트맵, 알림에서 재사용 |
| scoreToPhaseMeta | 다른 페이지 달 위상 표시 시 재사용 |
| scoreToBadgeState | Phase 2 마무리에서 유지 (부채) |
| sanitizeHexColor | 모든 hex color 표시에서 재사용 |
| useDashboard | PR-6 마감 시 캐시 무효화 대상 |
| MOCK_DASHBOARD | PR-5 전용 |
| DashboardResponse 타입 | 백엔드 응답 구조 고정 |
