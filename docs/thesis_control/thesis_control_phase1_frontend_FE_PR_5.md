# FE-PR-5: 관제실 대시보드 — 구현 계획 (v2)

> 버전: v2
> 작성일: 2026-03-14
> 변경 이력: v1 → v2 피드백 반영 (유지보수·보안·UX 보강)
> 범위: `app/thesis/[thesisId]/page.tsx` 전면 교체 + 대시보드 컴포넌트 5개 + 유틸 3개 + DashboardResponse 타입 교정
> 전제조건: FE-PR-4 머지 완료
> 목표: 가설 관제실 대시보드. "숫자가 아니라 분위기를 먼저 느끼게" — 달(Moon Phase) + 화살표(Arrow) + 최근 변화.
> 참조: `thesis_control_design.md` (섹션 3), `thesis-control.md`, FE-PR-4 계획서

---

## v1 → v2 변경 요약

| #   | 변경 항목                     | 변경 내용                                                 | 이유                                                               |
| --- | ----------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------ |
| C1  | `DashboardPageHeader` 신규    | 로딩/에러/정상 3곳의 헤더 JSX 중복 제거 → 단일 컴포넌트   | 한 곳만 수정하면 되도록                                            |
| C2  | `scoreToBadgeState` 유틸      | 인라인 삼항 중첩 → `utils.ts` 함수 추출                   | 가독성 + Phase 2 재사용 + 백엔드 `current_state` 추가 시 교체 용이 |
| C3  | `sanitizeHexColor` 유틸       | 백엔드 color 값 검증 + fallback                           | CSS injection 방어, 히트맵에서도 재사용                            |
| C4  | Mock `enabled` 조건 수정      | `enabled: !USE_MOCK && !!thesisId`                        | 불필요한 404 네트워크 노이즈 제거                                  |
| C5  | 그리드 반응형 통일            | 조건문 분기 → `grid-cols-2 sm:grid-cols-3` 고정           | 모바일 320px 3열 가독성 문제 해결                                  |
| C6  | `overall_delta` optional 필드 | `DashboardThesis`에 `overall_delta?: number \| null` 선언 | 백엔드 추가 시 즉시 활용 가능 (프론트 타입 선행)                   |
| C7  | `TREND_CONFIG` 위치 변경      | `DashboardIndicatorCard` 내부 → `constants.ts`            | Phase 2 히트맵·알림에서 재사용                                     |
| C8  | Trend 텍스트 개선             | "강화" → "강화 중 (전일 대비 ↑)"                          | degree 숫자 없이 변화 방향 전달 (리테일 투자자 타겟)               |
| C9  | 파일 수 변경                  | 9개 → 11개 (DashboardPageHeader, constants.ts 추가)       | —                                                                  |

---

## 0. PR-4 완료 자산 & 백엔드 API 발견사항

### 0.1 PR-4에서 물려받는 자산

| 자산                                      | 사용 위치                                        |
| ----------------------------------------- | ------------------------------------------------ |
| `ArrowIndicator` (common/)                | 지표 카드 화살표 (degree → 색상/방향)            |
| `MoonPhase` (common/)                     | 전체 흐름 달 시각화 (score → 충만도)             |
| `ThesisBadge` (common/)                   | 가설 상태 뱃지 (state → 아이콘+라벨+색상)        |
| `IndicatorCard` (common/)                 | 지표 카드 기본형 ← **PR-5에서 대체 (아래 설명)** |
| `ThesisDashboardSkeleton` (skeleton/)     | 로딩 스켈레톤                                    |
| `useDashboard` (queries.ts)               | 대시보드 데이터 페칭 hook                        |
| `QUERY_KEYS.dashboard` (queries.ts)       | 캐시 키                                          |
| `thesisApi.dashboard` (api.ts)            | GET 호출                                         |
| `degreeToColor/Label/Arrow` (utils.ts)    | 화살표 색상/라벨 매핑                            |
| `scoreToPhaseMeta` (utils.ts)             | 달 위상 라벨                                     |
| `stateToDisplay` (utils.ts)               | 상태 → 색상+아이콘+라벨                          |
| `relativeTime` (utils.ts)                 | 상대 시간 포맷                                   |
| `daysWatching` (utils.ts)                 | 생성 후 경과 일수                                |
| `sonner toast` (layout.tsx)               | 에러 알림                                        |
| `TYPE_LABELS/DIRECTION_LABELS` (types.ts) | 지표 타입/방향 한글 라벨                         |
| Layout Route Group (PR-4)                 | `[thesisId]/page.tsx`는 공유 헤더 밖 → 자체 헤더 |

### 0.2 백엔드 API 발견사항 (Critical)

#### 0.2.1 DashboardResponse 타입 불일치

**프론트엔드 현재 (`types.ts`)**:

```ts
export interface DashboardResponse {
	thesis: Thesis;
	premises: (ThesisPremise & { indicators: ThesisIndicator[] })[];
	recent_alerts: ThesisAlert[];
	moon_phase: { phase: string; label: string };
	overall_score: number;
}
```

**백엔드 실제 (`DashboardView.get()`)**:

```json
{
	"thesis": {
		"id": "uuid",
		"title": "string",
		"direction": "bullish|bearish|neutral",
		"status": "setting_up|active|closed|paused",
		"days_active": 32,
		"overall_score": 0.45,
		"overall_label": "조금씩 밝아지고 있어요",
		"overall_phase": "waxing",
		"recent_change": "외국인 순매도 3일째 지속 중"
	},
	"indicators": [
		{
			"id": "uuid",
			"name": "외국인 순매수 추이",
			"arrow_degree": 35.2,
			"score": 0.65,
			"color": "#60A5FA",
			"label": "지지하는 편",
			"previous_degree": 40.0,
			"trend": "strengthening",
			"premise_name": "외국인 매도세 전환",
			"is_extreme_vol": false
		}
	],
	"heatmap": {
		"rows": 1,
		"cols": 3,
		"cells": [{ "name": "외국인 순매수", "color": "#60A5FA", "degree": 35.2 }]
	}
}
```

→ **5가지 핵심 차이**:

| #   | 현재 프론트엔드                                | 백엔드 실제                                                   | 영향                             |
| --- | ---------------------------------------------- | ------------------------------------------------------------- | -------------------------------- |
| 1   | `thesis: Thesis` (전체 모델)                   | 축약된 thesis 객체 (8개 필드만)                               | `DashboardThesis` 별도 타입 필요 |
| 2   | `premises: (ThesisPremise & { indicators })[]` | **없음** — indicators가 플랫 배열, `premise_name` 문자열 포함 | premise 그룹핑은 프론트에서 처리 |
| 3   | `recent_alerts: ThesisAlert[]`                 | **없음** — alerts는 별도 API                                  | 대시보드에서 별도 호출 or 미포함 |
| 4   | `moon_phase: { phase, label }`                 | `thesis.overall_phase` + `thesis.overall_label`               | 중첩 구조 아님, thesis 내부      |
| 5   | `overall_score: number` (최상위)               | `thesis.overall_score`                                        | thesis 내부                      |

#### 0.2.2 Indicator 필드명 차이

| 프론트 현재            | 백엔드 대시보드 API | 비고                                       |
| ---------------------- | ------------------- | ------------------------------------------ |
| `current_arrow_degree` | `arrow_degree`      | 대시보드 전용 필드명                       |
| `current_label`        | `label`             | 같은 의미                                  |
| `current_color`        | `color`             | 같은 의미                                  |
| `current_score`        | `score`             | 같은 의미                                  |
| (없음)                 | `previous_degree`   | 트렌드 계산용 이전 각도                    |
| (없음)                 | `trend`             | 'stable' \| 'strengthening' \| 'weakening' |
| (없음)                 | `premise_name`      | premise.content[:50]                       |
| (없음)                 | `is_extreme_vol`    | \|z_raw\| >= 5.0 극단변동                  |

→ 기존 `ThesisIndicator`와 다른 **별도 타입 `DashboardIndicator` 필요**.

#### 0.2.3 Heatmap 데이터 구조

```ts
{
	rows: number; // 행 수
	cols: number; // 열 수 (보통 3)
	cells: {
		name: string; // 지표명 (최대 10자)
		color: string; // hex 색상
		degree: number; // 0~180
	}
	[];
}
```

→ PR-5 스코프: **카드뷰만 구현**. 히트맵 데이터는 타입만 정의, 렌더링은 Phase 2.

---

### 0.3 Arrow / Score / Phase 계산 체계 정리

#### Score → Degree 변환 (백엔드)

```
degree = 90 - (score * 90)
score=1.0 → 0° (강한 지지)
score=0.0 → 90° (중립)
score=-1.0 → 180° (강한 반박)
```

#### Degree → Color (5단계, utils.ts와 일치)

| Degree  | Color   | 의미      |
| ------- | ------- | --------- |
| 0~35    | #2563EB | 강한 지지 |
| 36~71   | #60A5FA | 지지      |
| 72~107  | #D1D5DB | 중립      |
| 108~143 | #FB923C | 약화      |
| 144~180 | #EF4444 | 강한 반박 |

#### Score → Moon Phase (5단계, utils.ts와 일치)

| Score  | Phase     | Label                    |
| ------ | --------- | ------------------------ |
| > 0.6  | full_moon | 가설이 빛나고 있어요     |
| > 0.2  | waxing    | 조금씩 밝아지고 있어요   |
| > -0.2 | half_moon | 반반이에요               |
| > -0.6 | waning    | 조금씩 어두워지고 있어요 |
| ≤ -0.6 | new_moon  | 가설이 힘을 잃고 있어요  |

#### Trend 판정 (백엔드)

```
delta = arrow_degree - previous_degree
|delta| ≤ 10 → 'stable'
delta < -10 → 'strengthening' (각도 감소 = 더 지지)
delta > 10 → 'weakening' (각도 증가 = 더 반박)
```

#### 특수 라벨 (백엔드에서 이미 적용)

- `is_paused=True` → label='일시정지됨', color='#9CA3AF'
- override 설정 → label='... (수동)'
- 데이터 부족 → label='데이터 부족', color='#9CA3AF'
- MAD < 1e-9 → label='변동 없음', color='#9CA3AF'

→ 프론트에서 추가 변환 불필요. 백엔드가 보내준 `color`, `label`을 그대로 사용.
단, `sanitizeHexColor`로 hex 형식 검증 후 사용 (v2 추가).

---

## 0.4 설계 결정 (1인 개발자 관점)

| #   | 결정                                                                   | 이유                                                                                                                                                                            |
| --- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | **카드뷰만 구현** (히트맵/그래프는 Phase 2)                            | 설계 문서에서도 "카드뷰만"으로 Phase 1 스코프 확정. 뷰 전환 탭 UI는 미구현.                                                                                                     |
| D2  | `DashboardResponse` 타입을 백엔드 실제 응답에 맞춰 교정                | 현재 타입은 설계 초안 기반. 실제 API와 5가지 불일치. PR-1~4에서 `useDashboard`를 호출하는 곳 없으므로 파손 위험 0.                                                              |
| D3  | `DashboardIndicator` 별도 타입 정의                                    | 기존 `ThesisIndicator`와 필드명이 다름 (arrow_degree vs current_arrow_degree). 타입 혼용 방지.                                                                                  |
| D4  | `IndicatorCard` (common/) 미사용 → `DashboardIndicatorCard` 신규 생성  | 기존 IndicatorCard는 `ThesisIndicator` 타입 의존 + `button` 래퍼 + `onClick`. 대시보드는 정보성 카드 + trend 표시 + premise_name 필요. 강제 호환보다 신규 생성이 유지보수 유리. |
| D5  | 최근 알림(recent_alerts) 미표시 → 대시보드 하단에 "최근 변화" 텍스트만 | 백엔드가 `recent_change` 문자열을 thesis 객체에 포함. 별도 Alert API 호출 없이 1줄 표시. 알림 상세는 `/thesis/alerts` (PR-6).                                                   |
| D6  | Premise 그룹핑 미구현 — 플랫 리스트                                    | 백엔드가 indicators를 플랫 배열로 반환 (premise_name 포함). 설계 문서에도 카드뷰는 개별 지표 중심. 그룹핑은 Phase 2.                                                            |
| D7  | `refetchInterval` 미적용 — 탭 복귀 시 자동 갱신만                      | `useDashboard`에 `refetchOnWindowFocus: true` 이미 설정. 실시간 폴링은 서버 부담. 사용자가 직접 새로고침 가능.                                                                  |
| D8  | Mock 모드에서 `useDashboard` **호출 차단**                             | **v2 변경**: `enabled: !USE_MOCK && !!thesisId`. 불필요한 404 네트워크 노이즈 제거.                                                                                             |
| D9  | 헤더에 "지표 설정" 바로가기 버튼                                       | 대시보드에서 지표를 수정하고 싶을 때 `/thesis/{id}/indicators`로 빠르게 이동. **v2 변경**: 지표 섹션 헤더 옆으로 위치 이동 (컨텍스트 근접).                                     |
| D10 | **v2 추가**: 공통 헤더 컴포넌트 추출 (`DashboardPageHeader`)           | 로딩/에러/정상 3곳의 헤더 JSX 중복 제거. 수정 시 1곳만 변경.                                                                                                                    |
| D11 | **v2 추가**: 백엔드 color 값 검증 (`sanitizeHexColor`)                 | CSS injection 방어. 백엔드 데이터를 '남의 데이터'로 가정하는 방어적 프로그래밍.                                                                                                 |
| D12 | **v2 추가**: 그리드 반응형 통일 (`grid-cols-2 sm:grid-cols-3`)         | 모바일 320px에서 3열은 카드당 ~90px로 가독성 불량. 조건문 분기 대신 breakpoint 통일.                                                                                            |

---

## 1. 파일 목록 (총 11개)

### 신규 생성 (6개)

```
frontend/
├── components/thesis/dashboard/
│   ├── DashboardPageHeader.tsx      # [1] 공통 헤더 (뒤로가기 + 타이틀 + 새로고침)   ← v2 추가
│   ├── DashboardHeader.tsx          # [2] 가설 제목 + 상태 뱃지 + 경과일
│   ├── OverallMoon.tsx              # [3] 달 위상 + 해석 라벨 + 전체 점수
│   ├── DashboardIndicatorCard.tsx   # [4] 지표 카드 (화살표 + trend + premise_name)
│   └── RecentChange.tsx             # [5] 최근 변화 텍스트 섹션
└── lib/thesis/
    └── constants.ts                 # [6] TREND_CONFIG 등 대시보드 상수               ← v2 추가
```

### 기존 파일 수정 (5개)

```
frontend/
├── lib/thesis/
│   ├── types.ts                    # [7] DashboardResponse 교정 + 신규 타입 4개
│   ├── utils.ts                    # [8] scoreToBadgeState + sanitizeHexColor 추가   ← v2 추가
│   └── mock.ts                     # [9] MOCK_DASHBOARD 추가
└── app/thesis/
    └── [thesisId]/
        └── page.tsx                # [10] 전면 교체
```

### 기존 파일 수정 (queries.ts — 최소 변경)

```
frontend/
└── lib/thesis/
    └── queries.ts                  # [11] useDashboard enabled 조건 수정             ← v2 추가
```

---

## 2. 각 파일 상세 명세

---

### [7] `lib/thesis/types.ts` — 수정

```ts
// ── 기존 DashboardResponse 교체 ──

// 대시보드 전용 thesis (백엔드가 축약해서 반환)
export interface DashboardThesis {
	id: string;
	title: string;
	direction: Direction;
	status: ThesisStatus;
	days_active: number;
	overall_score: number; // -1.0 ~ 1.0
	overall_label: string; // '가설이 빛나고 있어요' 등
	overall_phase: string; // 'full_moon' | 'waxing' | 'half_moon' | 'waning' | 'new_moon'
	recent_change: string; // 최신 변화 텍스트 (1줄)
	overall_delta?: number | null; // v2 추가: 전일 대비 전체 점수 변화 (백엔드 추가 시 활용)
}

// 대시보드 전용 indicator (ThesisIndicator와 필드명 다름)
export interface DashboardIndicator {
	id: string;
	name: string;
	arrow_degree: number; // 0~180 (소수점 1자리)
	score: number; // -1.0 ~ 1.0
	color: string; // hex
	label: string; // '지지하는 편' 등 (특수 라벨 포함)
	previous_degree: number | null; // 이전 각도 (trend 계산용)
	trend: "stable" | "strengthening" | "weakening";
	premise_name: string; // premise.content[:50]
	is_extreme_vol: boolean; // |z_raw| >= 5.0
}

// 히트맵 셀
export interface HeatmapCell {
	name: string; // 지표명 (최대 10자)
	color: string; // hex
	degree: number; // 0~180
}

// 히트맵 데이터
export interface HeatmapData {
	rows: number;
	cols: number;
	cells: HeatmapCell[];
}

// 교정된 DashboardResponse (백엔드 실제 응답)
export interface DashboardResponse {
	thesis: DashboardThesis;
	indicators: DashboardIndicator[];
	heatmap: HeatmapData;
}
```

**하위 호환**: 기존 `DashboardResponse`를 참조하는 곳은 `useDashboard` hook과 `thesisApi.dashboard`뿐이며, 둘 다 PR-5에서 교체하므로 파손 없음. 기존 `premises`, `recent_alerts`, `moon_phase`, `overall_score` 필드 삭제.

---

### [8] `lib/thesis/utils.ts` — 수정 (v2 추가)

기존 유틸 유지. 아래 2개 함수 추가.

```ts
import type { ThesisState, ThesisStatus } from "./types";

// ── v2 추가: score → ThesisBadge 상태 유추 ──
// 기술 부채: 백엔드에 current_state 필드 추가 시 이 함수만 교체
export function scoreToBadgeState(
	score: number,
	status: ThesisStatus,
): ThesisState {
	if (status !== "active") return "active";
	if (score > 0.2) return "strengthening";
	if (score < -0.2) return "weakening";
	return "active";
}

// ── v2 추가: hex color 검증 ──
// 백엔드 응답의 color 필드를 인라인 style에 주입하기 전 검증.
// 유효하지 않으면 fallback(회색) 반환.
const HEX_COLOR_RE = /^#[0-9A-Fa-f]{6}$/;

export function sanitizeHexColor(color: string, fallback = "#9CA3AF"): string {
	return HEX_COLOR_RE.test(color) ? color : fallback;
}
```

---

### [6] `lib/thesis/constants.ts` — 신규 (v2 추가)

대시보드에서 사용하는 상수. Phase 2 히트맵·알림 화면에서도 재사용.

```ts
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { LucideIcon } from "lucide-react";

// ── Trend 설정 ──
export interface TrendMeta {
	icon: LucideIcon;
	label: string; // 한글 라벨 (카드 내)
	labelWithDelta: string; // 전일 대비 방향 포함 라벨
	className: string; // Tailwind 색상 클래스
}

export const TREND_CONFIG: Record<
	"strengthening" | "weakening" | "stable",
	TrendMeta
> = {
	strengthening: {
		icon: TrendingUp,
		label: "강화",
		labelWithDelta: "강화 중 (전일 대비 ↑)",
		className: "text-green-400",
	},
	weakening: {
		icon: TrendingDown,
		label: "약화",
		labelWithDelta: "약화 중 (전일 대비 ↓)",
		className: "text-orange-400",
	},
	stable: {
		icon: Minus,
		label: "유지",
		labelWithDelta: "유지 중",
		className: "text-gray-500",
	},
} as const;
```

**설계 포인트**:

- `label`: 간결한 단어 (공간 부족 시)
- `labelWithDelta`: degree 숫자 없이 한글 + 방향 화살표로 변화 전달 (리테일 투자자 타겟)
- `previous_degree`가 null(첫 계산)이면 `label` 사용, 있으면 `labelWithDelta` 사용

---

### [9] `lib/thesis/mock.ts` — 수정

기존 Mock 유지. 대시보드용 Mock 데이터 추가.

```ts
import type { ..., DashboardResponse } from './types'

// ── Mock 대시보드 ──
export const MOCK_DASHBOARD: DashboardResponse = {
  thesis: {
    id: 'mock-1',
    title: 'AI 반도체 수요 증가로 NVIDIA 상승 지속',
    direction: 'bullish',
    status: 'active',
    days_active: 32,
    overall_score: 0.45,
    overall_label: '조금씩 밝아지고 있어요',
    overall_phase: 'waxing',
    recent_change: '외국인 순매수가 3일 연속 증가하며 강한 지지 신호를 보이고 있어요.',
    overall_delta: null,  // v2: 백엔드 미지원 시 null
  },
  indicators: [
    {
      id: 'dash-ind-1',
      name: '외국인 순매수 추이',
      arrow_degree: 35.2,
      score: 0.65,
      color: '#60A5FA',
      label: '지지하는 편',
      previous_degree: 42.0,
      trend: 'strengthening',
      premise_name: 'AI 반도체 수급 개선',
      is_extreme_vol: false,
    },
    {
      id: 'dash-ind-2',
      name: '원/달러 환율',
      arrow_degree: 110.5,
      score: -0.3,
      color: '#FB923C',
      label: '약화하는 편',
      previous_degree: 105.0,
      trend: 'weakening',
      premise_name: '글로벌 달러 강세',
      is_extreme_vol: false,
    },
    {
      id: 'dash-ind-3',
      name: 'VIX (공포지수)',
      arrow_degree: 88.0,
      score: 0.02,
      color: '#D1D5DB',
      label: '중립',
      previous_degree: 90.0,
      trend: 'stable',
      premise_name: '시장 심리',
      is_extreme_vol: false,
    },
  ],
  heatmap: {
    rows: 1,
    cols: 3,
    cells: [
      { name: '외국인 순매수', color: '#60A5FA', degree: 35.2 },
      { name: '원/달러 환율', color: '#FB923C', degree: 110.5 },
      { name: 'VIX', color: '#D1D5DB', degree: 88.0 },
    ],
  },
}
```

**설계 포인트**:

- 고정 데이터만 사용 (Date.now() 금지 — 버그 #24)
- indicators 3개: 지지(35°)/약화(110°)/중립(88°) — 색상 분기 검증
- trend 3종 모두 포함: strengthening/weakening/stable
- `premise_name` 다양한 값 → 그룹핑 테스트 가능성 확보
- `is_extreme_vol: false` — 극단변동 카드 미표시 (별도 시나리오)
- `overall_delta: null` — 백엔드 미지원 상태 시뮬레이션

---

### [11] `lib/thesis/queries.ts` — 최소 수정 (v2 추가)

```ts
// 기존 useDashboard hook에서 enabled 조건만 수정

export function useDashboard(thesisId: string) {
	return useQuery({
		queryKey: QUERY_KEYS.dashboard(thesisId),
		queryFn: () => thesisApi.dashboard(thesisId),
		enabled: !USE_MOCK && !!thesisId, // v2 변경: Mock 모드 시 API 미호출
		// ... 나머지 옵션 유지
	});
}
```

**변경 이유**: Mock 모드에서 thesisId='mock-1'로 실제 API 호출 → 404 → 네트워크 탭 오염. `!USE_MOCK` 조건 추가로 깨끗한 디버깅 환경 확보.

---

### [1] `components/thesis/dashboard/DashboardPageHeader.tsx` — 신규 (v2 추가)

로딩/에러/정상 3곳에서 공통으로 사용하는 페이지 상단 바.

```tsx
"use client";

import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";

interface Props {
	isLoading?: boolean;
	onRefresh?: () => void;
	showRefresh?: boolean;
}

export function DashboardPageHeader({
	isLoading = false,
	onRefresh,
	showRefresh = false,
}: Props) {
	return (
		<div className='flex items-center gap-3 py-3 mb-4'>
			<Link
				href='/thesis'
				className='p-1 text-gray-400 hover:text-white transition-colors'>
				<ArrowLeft size={20} />
			</Link>
			<span className='text-white text-base font-medium flex-1'>관제실</span>
			{showRefresh && onRefresh && (
				<button
					onClick={onRefresh}
					disabled={isLoading}
					className='p-1 text-gray-500 hover:text-gray-300 transition-colors'
					aria-label='새로고침'>
					<RefreshCw
						size={16}
						className={isLoading ? "animate-spin" : ""}
					/>
				</button>
			)}
		</div>
	);
}
```

**설계 포인트**:

- 로딩/에러 상태에서는 `showRefresh={false}`로 새로고침 버튼 숨김
- 정상 상태에서만 `showRefresh={true}` + `onRefresh={refetch}`
- 헤더 수정 시 1곳만 변경하면 3곳 모두 반영

---

### [2] `components/thesis/dashboard/DashboardHeader.tsx` — 신규

가설 제목, 상태 뱃지, 경과일 표시.

```tsx
"use client";

import { ThesisBadge } from "@/components/thesis/common/ThesisBadge";
import { scoreToBadgeState } from "@/lib/thesis/utils";
import type { DashboardThesis } from "@/lib/thesis/types";

interface Props {
	thesis: DashboardThesis;
}

export function DashboardHeader({ thesis }: Props) {
	const badgeState = scoreToBadgeState(thesis.overall_score, thesis.status);

	return (
		<div className='text-center space-y-3'>
			<h2 className='text-white text-lg font-bold px-4'>{thesis.title}</h2>
			<div className='flex items-center justify-center gap-3'>
				<ThesisBadge
					state={badgeState}
					direction={thesis.direction}
				/>
				<span className='text-gray-500 text-xs'>
					{thesis.days_active}일째 관제 중
				</span>
			</div>
		</div>
	);
}
```

**v2 변경**:

- 인라인 삼항 중첩 → `scoreToBadgeState(score, status)` 유틸 호출
- "지표 설정" 링크 제거 → 지표 섹션 헤더 옆으로 이동 (D9 변경)

---

### [3] `components/thesis/dashboard/OverallMoon.tsx` — 신규

달 위상 + 해석 라벨 + 전체 점수 표시.

```tsx
"use client";

import { MoonPhase } from "@/components/thesis/common/MoonPhase";
import type { DashboardThesis } from "@/lib/thesis/types";

interface Props {
	thesis: DashboardThesis;
}

export function OverallMoon({ thesis }: Props) {
	return (
		<div className='flex flex-col items-center gap-3 py-4'>
			<MoonPhase
				score={thesis.overall_score}
				size='lg'
			/>
			<p className='text-gray-300 text-sm font-medium'>
				{thesis.overall_label}
			</p>
			<p className='text-gray-600 text-xs'>
				종합 점수: {thesis.overall_score > 0 ? "+" : ""}
				{thesis.overall_score.toFixed(2)}
			</p>
		</div>
	);
}
```

**설계 포인트**:

- `MoonPhase` 컴포넌트 직접 재사용 (PR-1)
- `overall_label`은 백엔드가 계산한 한글 라벨 그대로 표시
- 점수는 소수점 2자리 + 부호 표시 (디버깅/파워유저용 보조 정보)
- Glow 효과는 Phase 2 백로그 (Tailwind 커스텀 유틸리티 등록 필요)

---

### [4] `components/thesis/dashboard/DashboardIndicatorCard.tsx` — 신규

대시보드 전용 지표 카드.

```tsx
"use client";

import { ArrowIndicator } from "@/components/thesis/common/ArrowIndicator";
import { AlertTriangle } from "lucide-react";
import { TREND_CONFIG } from "@/lib/thesis/constants";
import { sanitizeHexColor } from "@/lib/thesis/utils";
import type { DashboardIndicator } from "@/lib/thesis/types";

interface Props {
	indicator: DashboardIndicator;
}

export function DashboardIndicatorCard({ indicator }: Props) {
	const trend = TREND_CONFIG[indicator.trend];
	const TrendIcon = trend.icon;
	const safeColor = sanitizeHexColor(indicator.color);

	// v2: previous_degree 있으면 방향 포함 라벨, 없으면 간결 라벨
	const trendLabel =
		indicator.previous_degree !== null ? trend.labelWithDelta : trend.label;

	return (
		<div className='bg-gray-900 border border-gray-700 rounded-xl p-4'>
			<div className='flex flex-col items-center gap-2'>
				{/* 화살표 */}
				<ArrowIndicator
					degree={indicator.arrow_degree}
					size='lg'
				/>

				{/* 지표명 */}
				<p className='text-white text-sm font-medium truncate w-full text-center'>
					{indicator.name}
				</p>

				{/* 라벨 (백엔드 계산값, hex 검증 후 사용) */}
				<span
					className='text-xs'
					style={{ color: safeColor }}>
					{indicator.label}
				</span>

				{/* 트렌드 */}
				<div className={`flex items-center gap-1 ${trend.className}`}>
					<TrendIcon size={12} />
					<span className='text-[10px]'>{trendLabel}</span>
				</div>

				{/* 극단 변동 경고 */}
				{indicator.is_extreme_vol && (
					<div className='flex items-center gap-1 text-red-400'>
						<AlertTriangle size={10} />
						<span className='text-[10px]'>급변동</span>
					</div>
				)}
			</div>

			{/* 전제 */}
			{indicator.premise_name && (
				<p className='text-[10px] text-gray-600 text-center mt-2 truncate'>
					{indicator.premise_name}
				</p>
			)}
		</div>
	);
}
```

**v2 변경**:

- `TREND_CONFIG` → `constants.ts`에서 import (재사용성)
- `sanitizeHexColor(indicator.color)` 적용 (보안)
- `trendLabel`: `previous_degree` 유무에 따라 간결/상세 라벨 분기 (UX)

---

### [5] `components/thesis/dashboard/RecentChange.tsx` — 신규

최근 변화 텍스트 섹션.

```tsx
"use client";

import { Activity } from "lucide-react";

interface Props {
	text: string | null;
}

export function RecentChange({ text }: Props) {
	if (!text) return null;

	return (
		<div className='bg-gray-900 border border-gray-800 rounded-xl p-4'>
			<div className='flex items-start gap-3'>
				<Activity
					size={16}
					className='text-blue-400 flex-shrink-0 mt-0.5'
				/>
				<div>
					<p className='text-gray-500 text-xs font-medium mb-1'>최근 변화</p>
					{/* 순수 텍스트만 표시. dangerouslySetInnerHTML 사용 금지. */}
					<p className='text-gray-300 text-sm leading-relaxed'>{text}</p>
				</div>
			</div>
		</div>
	);
}
```

**설계 포인트**:

- `text`가 null이면 렌더링하지 않음 (초기 데이터 없는 경우)
- `Activity` 아이콘: 변화/움직임 시각적 표현
- 단순 텍스트 표시 (별도 Alert API 호출 없음 — D5)
- v2: "순수 텍스트만" 주석 명시 (미래의 dangerouslySetInnerHTML 유혹 방지)

---

### [10] `app/thesis/[thesisId]/page.tsx` — 전면 교체

```tsx
"use client";

import { useParams } from "next/navigation";
import { Settings } from "lucide-react";
import Link from "next/link";
import { useDashboard } from "@/lib/thesis/queries";
import { USE_MOCK, MOCK_DASHBOARD } from "@/lib/thesis/mock";
import { ThesisDashboardSkeleton } from "@/components/thesis/skeleton/ThesisSkeleton";
import { DashboardPageHeader } from "@/components/thesis/dashboard/DashboardPageHeader";
import { DashboardHeader } from "@/components/thesis/dashboard/DashboardHeader";
import { OverallMoon } from "@/components/thesis/dashboard/OverallMoon";
import { DashboardIndicatorCard } from "@/components/thesis/dashboard/DashboardIndicatorCard";
import { RecentChange } from "@/components/thesis/dashboard/RecentChange";

export default function ThesisDashboardPage() {
	const params = useParams();
	const thesisId = params.thesisId as string;

	const {
		data: dashboard,
		isLoading,
		isError,
		refetch,
	} = useDashboard(thesisId);

	const data = USE_MOCK ? MOCK_DASHBOARD : dashboard;

	// ── 로딩 ──
	if (isLoading && !USE_MOCK) {
		return (
			<div className='max-w-lg mx-auto px-4 pt-4 pb-20'>
				<DashboardPageHeader />
				<ThesisDashboardSkeleton />
			</div>
		);
	}

	// ── 에러 ──
	if ((isError || !data) && !USE_MOCK) {
		return (
			<div className='max-w-lg mx-auto px-4 pt-4 pb-20'>
				<DashboardPageHeader />
				<div className='text-center py-20'>
					<p className='text-gray-400 text-sm mb-3'>
						대시보드를 불러오지 못했어요
					</p>
					<button
						onClick={() => refetch()}
						className='inline-flex items-center gap-2 text-blue-400 text-sm
                       hover:text-blue-300 transition-colors'>
						새로고침
					</button>
				</div>
			</div>
		);
	}

	if (!data) return null;

	return (
		<div className='max-w-lg mx-auto px-4 pt-4 pb-20'>
			{/* 공통 헤더 — 정상 상태에서만 새로고침 버튼 표시 */}
			<DashboardPageHeader
				showRefresh
				isLoading={isLoading}
				onRefresh={() => refetch()}
			/>

			<div className='space-y-6'>
				{/* 가설 정보 */}
				<DashboardHeader thesis={data.thesis} />

				{/* 달 위상 */}
				<OverallMoon thesis={data.thesis} />

				{/* 지표 그리드 */}
				<section>
					<div className='flex items-center justify-between mb-3'>
						<h3 className='text-gray-400 text-sm font-medium'>
							지표 ({data.indicators.length}개)
						</h3>
						{/* v2: 지표 설정 링크를 지표 섹션 헤더 옆으로 이동 */}
						<Link
							href={`/thesis/${thesisId}/indicators`}
							className='inline-flex items-center gap-1 text-gray-500 text-xs
                         hover:text-gray-300 transition-colors'>
							<Settings size={12} />
							설정
						</Link>
					</div>

					{data.indicators.length === 0 ? (
						<div className='text-center py-8 border border-dashed border-gray-700 rounded-xl'>
							<p className='text-gray-500 text-sm'>아직 지표가 없어요</p>
							<Link
								href={`/thesis/${thesisId}/indicators`}
								className='text-blue-400 text-xs hover:underline mt-1 inline-block'>
								지표 추가하기
							</Link>
						</div>
					) : (
						<div className='grid grid-cols-2 sm:grid-cols-3 gap-3'>
							{data.indicators.map((ind) => (
								<DashboardIndicatorCard
									key={ind.id}
									indicator={ind}
								/>
							))}
						</div>
					)}
				</section>

				{/* 최근 변화 */}
				<RecentChange text={data.thesis.recent_change} />

				{/* 하단 액션 */}
				<div className='space-y-2 pt-2'>
					<Link
						href={`/thesis/${thesisId}/close`}
						className='block w-full py-3 border border-gray-700 text-gray-400 text-sm
                       text-center rounded-xl hover:border-gray-500 transition-colors'>
						가설 마감하기
					</Link>
				</div>
			</div>
		</div>
	);
}
```

**v2 핵심 변경**:

1. **`DashboardPageHeader` 사용**: 로딩/에러/정상 3곳 모두 동일 컴포넌트. 조건부 props로 새로고침 표시 제어.

2. **`useRouter` 제거**: 사용하지 않는 import 삭제.

3. **그리드 반응형**: `grid-cols-2 sm:grid-cols-3` 고정. 지표 개수별 조건문 분기 제거.

4. **"지표 설정" 위치 변경**: `DashboardHeader` 내부 → 지표 섹션 `<h3>` 옆. 컨텍스트 근접 배치.

5. **에러 화면 새로고침**: 별도 RefreshCw 아이콘 제거 → 텍스트 버튼으로 단순화 (헤더의 RefreshCw와 중복 방지).

6. 나머지 유지: `max-w-lg mx-auto`, `ThesisDashboardSkeleton`, Mock 분기, 하단 마감 링크.

---

## 3. 의존성 그래프

```
lib/thesis/types.ts (수정: DashboardResponse 교정, DashboardThesis+overall_delta, DashboardIndicator, HeatmapData)
    │
    ├→ lib/thesis/utils.ts (수정: scoreToBadgeState + sanitizeHexColor 추가)  ← v2
    │
    ├→ lib/thesis/constants.ts (신규: TREND_CONFIG)                          ← v2
    │
    ├→ lib/thesis/mock.ts (수정: MOCK_DASHBOARD 추가)
    │
    └→ lib/thesis/queries.ts (수정: useDashboard enabled 조건)               ← v2

components/thesis/common/ArrowIndicator.tsx (PR-1, 변경 없음)
components/thesis/common/MoonPhase.tsx (PR-1, 변경 없음)
components/thesis/common/ThesisBadge.tsx (PR-1, 변경 없음)
components/thesis/skeleton/ThesisSkeleton.tsx (PR-1, 변경 없음)
    │
    └→ components/thesis/dashboard/ (신규)
        ├── DashboardPageHeader.tsx → (독립)                                 ← v2
        ├── DashboardHeader.tsx → ThesisBadge, scoreToBadgeState, DashboardThesis
        ├── OverallMoon.tsx → MoonPhase, DashboardThesis
        ├── DashboardIndicatorCard.tsx → ArrowIndicator, TREND_CONFIG, sanitizeHexColor, DashboardIndicator
        └── RecentChange.tsx → (독립)

app/thesis/[thesisId]/page.tsx (전면 교체 — 모든 dashboard 컴포넌트 + queries + mock)
```

---

## 4. 구현 순서

```
Phase A (독립, 병렬):
  ├─ lib/thesis/types.ts: DashboardResponse 교정 + 5개 신규 타입 (overall_delta 포함)
  ├─ lib/thesis/utils.ts: scoreToBadgeState + sanitizeHexColor 추가
  ├─ lib/thesis/constants.ts: TREND_CONFIG 신규
  └─ mkdir components/thesis/dashboard/

Phase B (Phase A 의존, 병렬):
  ├─ lib/thesis/mock.ts: MOCK_DASHBOARD 추가
  ├─ lib/thesis/queries.ts: useDashboard enabled 조건 수정
  ├─ components/thesis/dashboard/DashboardPageHeader.tsx
  ├─ components/thesis/dashboard/DashboardHeader.tsx
  ├─ components/thesis/dashboard/OverallMoon.tsx
  ├─ components/thesis/dashboard/DashboardIndicatorCard.tsx
  └─ components/thesis/dashboard/RecentChange.tsx

Phase C (Phase B 의존):
  └─ app/thesis/[thesisId]/page.tsx 전면 교체

Phase D (Phase C 의존):
  └─ tsc --noEmit + npm run build 검증
```

---

## 5. 검증 체크리스트

### 5.1 빌드 검증

| 검증 항목            | 명령어                                                | 기대 결과 |
| -------------------- | ----------------------------------------------------- | --------- |
| TypeScript 타입 체크 | `tsc --noEmit`                                        | 에러 0개  |
| Next.js 빌드         | `npm run build`                                       | 성공      |
| 기존 기능 회귀       | `/thesis` 목록, `/thesis/new`, `/thesis/*/indicators` | 정상 동작 |

### 5.2 Mock 검증

| 시나리오             | 기대 동작                                                                                          |
| -------------------- | -------------------------------------------------------------------------------------------------- |
| `/thesis/mock-1`     | 대시보드 정상 표시 (가설 제목 + 달 + 3개 지표 + 최근 변화)                                         |
| 네트워크 탭          | **404 요청 0건** (Mock 모드에서 API 미호출 — v2 확인)                                              |
| 달(Moon Phase)       | 점수 0.45 → waxing 위상, 충만도 72%                                                                |
| 지표 카드 3개        | **2열(모바일) / 3열(sm+)** 그리드, 각각 다른 색상 (파랑/주황/회색)                                 |
| 트렌드 표시          | strengthening → "강화 중 (전일 대비 ↑)" / weakening → "약화 중 (전일 대비 ↓)" / stable → "유지 중" |
| "설정" 링크          | 지표 섹션 헤더 옆에 위치, `/thesis/mock-1/indicators`로 이동                                       |
| "가설 마감하기" 링크 | `/thesis/mock-1/close`로 이동                                                                      |
| 새로고침 버튼        | 정상 상태에서만 표시. 클릭 시 `refetch()` 실행                                                     |
| 뒤로가기 화살표      | `/thesis`로 이동                                                                                   |

### 5.3 UI 검증

| 시나리오                 | 기대 동작                                                                                     |
| ------------------------ | --------------------------------------------------------------------------------------------- |
| 지표 0개                 | 점선 빈 상태 + "지표 추가하기" 링크                                                           |
| 지표 1개                 | 2열 그리드 (1개만 채워짐)                                                                     |
| 지표 2개                 | 2열 그리드 (가득 참)                                                                          |
| 지표 3개                 | 2열(모바일) / 3열(sm+)                                                                        |
| 지표 4개+                | 자연 줄바꿈                                                                                   |
| `is_extreme_vol=true`    | 빨간 경고 "급변동" 표시                                                                       |
| `recent_change` 비어있음 | 최근 변화 섹션 미표시                                                                         |
| 로딩 상태                | `DashboardPageHeader` (새로고침 없음) + `ThesisDashboardSkeleton` 표시                        |
| 에러 상태                | `DashboardPageHeader` (새로고침 없음) + "대시보드를 불러오지 못했어요" + 새로고침 텍스트 버튼 |
| 유효하지 않은 color 값   | fallback #9CA3AF(회색) 적용 — **v2 추가**                                                     |

### 5.4 접근성 검증

| 항목           | 기대                                    |
| -------------- | --------------------------------------- |
| 새로고침 버튼  | `aria-label="새로고침"`                 |
| ArrowIndicator | `role="img"` + `aria-label` (기존 구현) |
| 다크 테마      | bg-white, text-black 0개                |

---

## 6. 에러 처리 매트릭스

| #   | 시나리오                | 처리 방식                                                  | 사용자 메시지                  |
| --- | ----------------------- | ---------------------------------------------------------- | ------------------------------ |
| E1  | 대시보드 로딩 실패      | 인라인 에러 + 새로고침 버튼                                | "대시보드를 불러오지 못했어요" |
| E2  | 가설 404                | `useDashboard` error → 에러 화면                           | "대시보드를 불러오지 못했어요" |
| E3  | Mock 모드               | `useDashboard` **미호출** (v2), `MOCK_DASHBOARD` 상수 반환 | —                              |
| E4  | 지표 0개                | 빈 상태 UI + 지표 추가 링크                                | "아직 지표가 없어요"           |
| E5  | recent_change 비어있음  | `RecentChange` 미렌더링                                    | —                              |
| E6  | 유효하지 않은 hex color | `sanitizeHexColor` → fallback #9CA3AF                      | — (시각적 fallback)            |

---

## 7. 서버 리소스 관리

| 항목                     | 전략                                 | 이유                                             |
| ------------------------ | ------------------------------------ | ------------------------------------------------ |
| `useDashboard` staleTime | 기존 5분 유지 (글로벌 QueryProvider) | 대시보드 데이터는 일배치. 실시간 갱신 불필요     |
| refetchOnWindowFocus     | `true` (기존 설정)                   | 탭 복귀 시 자동 갱신. 사용자 주도                |
| 폴링                     | 없음 (D7)                            | 서버 부담. 수동 새로고침 제공                    |
| Alert API                | 미호출 (D5)                          | `recent_change` 텍스트만 사용. Alert 상세는 PR-6 |
| `useThesis`              | 미호출                               | `useDashboard`가 thesis 데이터 포함              |
| Mock 모드 API            | **미호출** (v2 — D8)                 | `enabled: !USE_MOCK` 조건으로 불필요한 404 방지  |

---

## 8. 리스크 및 완화

| #   | 리스크                                                        | 심각도 | 완화                                                                                                                            |
| --- | ------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------- |
| 1   | DashboardResponse 타입 교정 시 기존 코드 파손                 | 낮     | PR-1~4에서 `useDashboard`를 실제 호출하는 곳 없음. 유일한 사용처는 이 PR                                                        |
| 2   | `ThesisBadge`에 `current_state` 대신 `status` 전달            | 중     | **v2 완화**: `scoreToBadgeState` 유틸로 캡슐화. 교체 시 1곳만 수정                                                              |
| 3   | 백엔드 `direction` 값이 'long'/'short' vs 'bullish'/'bearish' | 중     | 백엔드 코드 확인 시 `direction` 필드는 모델에서 'bullish'/'bearish'/'neutral'. DashboardView에서 변환 없이 전달. 일치 확인 완료 |
| 4   | 지표 4개 이상일 때 그리드 가독성                              | 낮     | **v2 완화**: `grid-cols-2 sm:grid-cols-3` 반응형. 모바일에서 2열 유지                                                           |
| 5   | 백엔드 color 필드에 유효하지 않은 값                          | 낮     | **v2 완화**: `sanitizeHexColor` 검증 + fallback                                                                                 |
| 6   | `overall_delta` 필드 백엔드 미지원                            | 낮     | optional 필드 선언. `undefined`/`null` 시 무시. 프론트 타입만 선행                                                              |

---

## 9. 기술 부채

| 부채                                     | 영향                                        | 해소 시점                                                  |
| ---------------------------------------- | ------------------------------------------- | ---------------------------------------------------------- |
| `DashboardThesis`에 `current_state` 없음 | `scoreToBadgeState` 유틸로 간이 상태 유추   | 백엔드에 `current_state` 필드 추가 시 (유틸 함수 1곳 교체) |
| 히트맵 뷰 미구현                         | `HeatmapData` 타입만 정의, 렌더링 없음      | Phase 2                                                    |
| 그래프 뷰 미구현                         | 시간 흐름 시각화 없음                       | Phase 2 (ThesisSnapshot 활용)                              |
| Premise 그룹핑 미구현                    | `premise_name` 텍스트만 표시, 그룹 UI 없음  | Phase 2                                                    |
| `relativeTime` 정적                      | 페이지 체류 중 시간 미갱신                  | timeago 라이브러리 도입                                    |
| 수동 새로고침 의존                       | 자동 폴링 없음                              | Phase 2 (옵셔널 refetchInterval)                           |
| `IndicatorCard` (common/) 사용 안 함     | 대시보드 전용 `DashboardIndicatorCard` 사용 | 공통 카드로 통합 검토 (Phase 2)                            |
| OverallMoon Glow 효과 미적용             | score별 배경 발광 없음                      | Phase 2 (Tailwind 커스텀 `bg-gradient-radial` 등록 필요)   |
| Sticky Moon compact 모드 미적용          | 스크롤 시 달 상단 고정 없음                 | Phase 2 (지표 5개 이상 시 검토)                            |
| `overall_delta` 활용 미구현              | 타입만 선언, UI 미반영                      | 백엔드 추가 시 OverallMoon에서 활용                        |
| thesisId UUID 포맷 검증 없음             | 임의 문자열이 API에 전달될 수 있음          | `[thesisId]/layout.tsx`에서 공통 검증 (전체 라우트 적용)   |

---

## 10. 후속 PR 연결

| 이 PR에서 만든 것         | 사용하는 PR                                |
| ------------------------- | ------------------------------------------ |
| `DashboardPageHeader`     | PR-6에서 마감 화면 헤더 재사용             |
| `DashboardHeader`         | PR-6에서 마감 화면 헤더 재사용             |
| `DashboardIndicatorCard`  | Phase 2 히트맵 뷰에서 카드↔히트맵 전환     |
| `OverallMoon`             | Phase 2 그래프 뷰에서 상단 달 유지         |
| `RecentChange`            | PR-6 알림 목록에서 패턴 참조               |
| `DashboardResponse` 교정  | 이후 모든 대시보드 관련 작업에 정확한 타입 |
| `DashboardIndicator` 타입 | Phase 2 히트맵/그래프에서 재사용           |
| `MOCK_DASHBOARD`          | Phase 2 추가 뷰 개발 시 테스트 데이터      |
| `scoreToBadgeState` 유틸  | 대시보드 외 ThesisBadge 사용하는 모든 곳   |
| `sanitizeHexColor` 유틸   | Phase 2 히트맵 셀 렌더링                   |
| `TREND_CONFIG` 상수       | Phase 2 히트맵 카드, PR-6 알림 화면        |

---

## 11. Phase 2 백로그 (v2에서 정리)

피드백에서 논의되었으나 PR-5 스코프 밖으로 결정된 항목.

| #   | 항목                  | 설명                                        | 선행 조건                              |
| --- | --------------------- | ------------------------------------------- | -------------------------------------- |
| P1  | OverallMoon Glow 효과 | score 구간별 `bg-gradient-radial` 배경 발광 | Tailwind 커스텀 유틸리티 `@layer` 등록 |
| P2  | Delta 수치 표시       | degree 변화량 숫자 표시 (파워유저용)        | 상세 뷰 페이지 구현                    |
| P3  | 달 크기 애니메이션    | `overall_delta` 기반 달 커지기/작아지기     | 백엔드 `overall_delta` 필드 추가       |
| P4  | Sticky Moon compact   | 스크롤 시 달을 상단 고정 (compact 모드)     | 지표 5개 이상 시나리오 검증            |
| P5  | 히트맵 뷰             | `HeatmapData` 기반 색상 격자 렌더링         | 설계 문서 히트맵 섹션 확정             |
| P6  | 그래프 뷰             | 시간 흐름 시각화 (ThesisSnapshot)           | 백엔드 스냅샷 API 구현                 |
| P7  | Premise 그룹핑        | 지표를 premise별로 그룹핑하여 표시          | UX 설계 확정                           |
| P8  | 가설 일시정지         | 마감 외 일시정지 액션                       | 백엔드 status 전환 API                 |
| P9  | UUID 포맷 검증        | `[thesisId]/layout.tsx`에서 공통 검증       | 전체 라우트 영향 검토                  |
| P10 | 빈 상태 일러스트      | 지표 0개일 때 ArrowIndicator(90°) 회색 장식 | 디자인 확정                            |

---

## 12. Claude Code 실행 프롬프트

```
FE-PR-5 구현 계획서 v2(docs/thesis_control/thesis_control_phase1_frontend_FE_PR_5.md)를 읽고,
Thesis Control 관제실 대시보드를 구현해줘.

─────────────────────────────────────────────
[구현 순서]
─────────────────────────────────────────────

1단계: 타입 + 유틸 + 상수 + 디렉토리 생성
  - lib/thesis/types.ts:
    · 기존 DashboardResponse 삭제
    · DashboardThesis (overall_delta?: number | null 포함), DashboardIndicator, HeatmapCell, HeatmapData 신규 타입
    · DashboardResponse 재정의 (thesis + indicators + heatmap)
  - lib/thesis/utils.ts:
    · scoreToBadgeState(score, status) 함수 추가
    · sanitizeHexColor(color, fallback) 함수 추가
  - lib/thesis/constants.ts:
    · TREND_CONFIG (label + labelWithDelta + icon + className) 신규 생성
  - mkdir components/thesis/dashboard/

2단계: Mock 데이터 + queries 수정 + 컴포넌트 (병렬)
  - lib/thesis/mock.ts: MOCK_DASHBOARD 추가 (지표 3개, trend 3종, score 0.45, overall_delta: null)
  - lib/thesis/queries.ts: useDashboard enabled 조건에 !USE_MOCK 추가
  - components/thesis/dashboard/DashboardPageHeader.tsx (공통 헤더 — showRefresh/onRefresh/isLoading props)
  - components/thesis/dashboard/DashboardHeader.tsx (ThesisBadge + scoreToBadgeState + 경과일)
  - components/thesis/dashboard/OverallMoon.tsx (MoonPhase + 라벨 + 점수)
  - components/thesis/dashboard/DashboardIndicatorCard.tsx (ArrowIndicator + TREND_CONFIG + sanitizeHexColor + labelWithDelta 분기)
  - components/thesis/dashboard/RecentChange.tsx (Activity 아이콘 + 텍스트, dangerouslySetInnerHTML 금지 주석)

3단계: 페이지 교체
  - app/thesis/[thesisId]/page.tsx 전면 교체
    · DashboardPageHeader 사용 (로딩/에러/정상 공통)
    · Suspense 미사용 (useSearchParams 없음)
    · max-w-lg mx-auto 콘텐츠 레이아웃
    · Mock 모드: USE_MOCK ? MOCK_DASHBOARD : dashboard
    · 그리드: grid-cols-2 sm:grid-cols-3 (조건문 분기 없음)
    · "설정" 링크를 지표 섹션 헤더 옆에 배치
    · 하단: 가설 마감하기 링크

─────────────────────────────────────────────
[핵심 주의사항]
─────────────────────────────────────────────
- 다크 테마 전용. bg-white, text-black 사용 금지.
- DashboardResponse 타입은 백엔드 실제 응답에 맞춰 교정 (기존 타입은 설계 초안 기반).
- 백엔드 indicator 필드: arrow_degree (current_arrow_degree 아님), score, color, label, trend.
- moon_phase/overall_score는 thesis 객체 내부 (최상위 아님).
- recent_alerts는 별도 API — 대시보드에서 미호출. thesis.recent_change 텍스트만 사용.
- heatmap 데이터는 타입만 정의, 렌더링은 Phase 2.
- Mock 데이터에 Date.now() 사용 금지 (버그 #24).
- ThesisDashboardSkeleton은 직접 import (barrel 미포함).
- [thesisId]/page.tsx는 Route Group 밖 → 자체 헤더 필요 (DashboardPageHeader 사용).
- sanitizeHexColor로 인라인 style color 검증 후 사용.
- useDashboard enabled 조건에 !USE_MOCK 반드시 포함.
- TREND_CONFIG는 constants.ts에서 import (컴포넌트 내부 정의 금지).
- 구현 후 tsc --noEmit + npm run build 검증 필수.
```
