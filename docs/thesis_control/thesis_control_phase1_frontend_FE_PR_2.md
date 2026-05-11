# FE-PR-2: 첫 화면 — 가설 목록 + 오늘의 변화 + 진입점 — 구현 계획 (v2.1)

> 버전: v2.1 (v2 최종 점검 반영)
> 작성일: 2026-03-11
> 범위: `app/thesis/page.tsx` 실제 구현 + 목록 카드 + 진입점 + PR-1 리뷰 반영
> 전제조건: FE-PR-1 머지 완료
> 목표: 설계 문서 2.2 첫 화면 구현. 사용자가 가설 통제실에 진입했을 때 보는 첫 화면.

---

## 0. PR-1 리뷰 반영 사항 (이 PR에서 함께 처리)

PR-1 완료 보고서의 전문가 리뷰 중 FE-PR-2 범위에서 처리해야 할 항목들.

### 0.1 즉시 반영 (기술 부채 해소)

| #   | 출처 | 이슈                               | 변경 내용                                                                                                                          | 대상 파일                     |
| --- | ---- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| R1  | U9   | ThesisBadge 이모지 → lucide 아이콘 | 📈→`TrendingUp`, 📉→`TrendingDown`, →→`Minus` + 상태별 아이콘 교체                                                                 | `ThesisBadge.tsx`             |
| R2  | U8   | ThesisBadge gray 3개 상태 동일     | warming_up: `text-gray-400 bg-gray-800`, expired: `text-amber-400 bg-amber-900/30`, closed_neutral: `text-gray-500 bg-gray-800/50` | `utils.ts` → `stateToDisplay` |
| R3  | U4   | 헤더 sticky 미적용                 | `sticky top-0 z-10 bg-gray-950/95 backdrop-blur-sm`                                                                                | `layout.tsx`                  |
| R4  | U1   | 중립 회색 대비 부족                | `#9CA3AF` → `#D1D5DB`                                                                                                              | `utils.ts` → `degreeToColor`  |
| R5  | U2   | 강한 반박 빨강 대비 부족           | `#DC2626` → `#EF4444`                                                                                                              | `utils.ts` → `degreeToColor`  |

### 0.2 용어 개선 (투자 도메인 리뷰 반영)

| 현재          | 변경             | 적용 위치                              |
| ------------- | ---------------- | -------------------------------------- |
| "관제 중"     | "추적 중"        | `stateToDisplay`, page.tsx 섹션 타이틀 |
| "강화 추세"   | "지지 신호 증가" | `stateToDisplay`                       |
| "약화 추세"   | "반박 신호 증가" | `stateToDisplay`                       |
| "가설 통제실" | 유지 (브랜드명)  | —                                      |

> "전제"→"근거", "중립 마감"→"미확정"은 FE-PR-3, FE-PR-6에서 각각 적용.

---

## 0.3 v1→v2 변경 이력

| #   | v1 이슈                                                         | v2 변경                                                  | 이유                     |
| --- | --------------------------------------------------------------- | -------------------------------------------------------- | ------------------------ |
| M1  | Mock 모드에서도 실제 query 호출 → 401/에러 콘솔 노이즈          | `enabled: !USE_MOCK` 옵션으로 네트워크 요청 차단         | 디버깅 혼란 방지         |
| M2  | EntryPointGrid 5개 중 3개 "준비 중" → 미완성 인상               | 활성 2개 + 준비 중 1개로 축소. 나머지 비렌더링           | 첫인상 완성도            |
| M3  | ThesisListCard에 보조 정보 없음                                 | target + 추적 일수를 한 줄에 표시                        | 투자자 즉시 판단         |
| M4  | "어젯밤 특별한 변화는 없었어요" → 시간 필터 없이 시간 문구 사용 | "새로운 변화가 아직 없어요."로 변경                      | 데이터 조건과 문구 일치  |
| M5  | 임시 Toast 주석 TODO 수준                                       | 왜 임시인지 + 교체 대상까지 코드 주석에 명시             | 2주 뒤 자기 이해         |
| M6  | stateToDisplay icon 필드가 `string` 타입                        | `ThesisStateIconKey` union type 도입                     | 오타 런타임 폭발 방지    |
| M7  | relativeTime이 TodayChangeCard 내부 함수                        | `lib/thesis/utils.ts`로 분리                             | 알림목록/대시보드 재사용 |
| M8  | activeTheses 정렬 없이 순서대로 나열                            | current_state 우선순위 정렬 (critical → weakening → ...) | 중요한 가설 먼저         |

## 0.4 v2→v2.1 변경 이력

| #   | v2 이슈                                    | v2.1 변경                                                             | 이유                                                                 |
| --- | ------------------------------------------ | --------------------------------------------------------------------- | -------------------------------------------------------------------- |
| P1  | ThesisListCard에서 target을 무조건 출력    | null/undefined/빈문자열 안전 처리. target 없으면 추적 일수만 표시     | 백엔드 연동 시 빈 target → `null · 23일째` 표시 방지                 |
| P2  | useAlerts 시그니처 하위 호환 주의가 서술적 | 프롬프트 주의사항에 "기존 호출부 시그니처를 절대 변경하지 말 것" 명시 | Claude Code가 기존 호출부까지 수정하는 사고 방지                     |
| P3  | relativeTime에 미래 시간 방어 없음         | `diff < 0`이면 `방금 전` 반환                                         | 서버 시계 차이/timezone 변환 문제로 음수 diff 발생 시 이상한 값 방지 |
| P4  | sortThesesByPriority 동순위 시 순서 불안정 | 2차 정렬: `created_at` 최신순                                         | 동일 priority 가설이 여러 개일 때 목록 순서가 일관되게 유지          |
| P5  | sortThesesByPriority 매 렌더링마다 재실행  | `useMemo`로 감싸서 activeTheses 변경 시에만 재정렬                    | 가설 수십 개일 때 불필요한 재정렬 방지                               |
| P6  | 가설/알림 목록이 시맨틱하지 않은 div 나열  | `div` → `ul`/`li`로 변경                                              | 스크린 리더 접근성 + SEO 시맨틱 HTML 준수                            |
| P7  | relativeTime이 페이지 체류 시 갱신 안 됨   | 기술 부채로 문서화 (구현은 FE-PR-6에서)                               | 현재 PR 범위 밖이지만 인지 필요                                      |

---

## 1. 파일 목록 (총 10개)

### 신규 생성 (4개)

```
frontend/
├── components/thesis/
│   └── list/
│       ├── ThesisListCard.tsx           # [1] 가설 카드 (목록 행)
│       ├── TodayChangeCard.tsx          # [2] 오늘의 변화 알림 카드
│       └── EntryPointGrid.tsx           # [3] 새 가설 진입점 버튼 그리드
└── lib/thesis/
    └── mock.ts                          # [4] Mock 데이터 (백엔드 미연동 개발용)
```

### 기존 파일 수정 (6개)

```
frontend/
├── app/thesis/
│   └── page.tsx                         # [5] skeleton → 실제 구현 교체
├── app/thesis/layout.tsx                # [6] sticky 헤더 적용 (R3)
├── components/thesis/common/
│   └── ThesisBadge.tsx                  # [7] 이모지→lucide 아이콘 (R1)
├── lib/thesis/
│   ├── utils.ts                         # [8] 색상·용어·relativeTime·정렬·icon타입
│   ├── types.ts                         # [9] ThesisStateIconKey 타입 추가
│   └── queries.ts                       # [10] useThesisList/useAlerts에 enabled 옵션 추가
```

---

## 2. 각 파일 상세 명세

---

### [9] `lib/thesis/types.ts` — 수정 (M6)

icon 키 타입 추가. 기존 타입에 영향 없는 export 추가만.

```ts
// ── 기존 타입들 유지 (Direction, ThesisStatus, ThesisState, ...) ──

// ── 신규: 상태 아이콘 키 (v2 M6) ──
// ThesisBadge에서 사용. lucide-react 컴포넌트와 1:1 매핑.
// 문자열 오타를 컴파일 타임에 잡기 위한 union type.
export type ThesisStateIconKey =
	| "loader"
	| "eye"
	| "trending_up"
	| "trending_down"
	| "alert_triangle"
	| "clock"
	| "timer"
	| "check_circle"
	| "x_circle"
	| "minus_circle";
```

---

### [10] `lib/thesis/queries.ts` — 수정 (M1)

useThesisList, useAlerts에 optional `options` 파라미터 추가. Mock 모드에서 `enabled: false`로 네트워크 요청 차단.

```ts
// useThesisList — options 파라미터 추가
export function useThesisList(options?: { enabled?: boolean }) {
	return useQuery<Thesis[]>({
		queryKey: ["thesis", "list"],
		queryFn: () => thesisApi.list(),
		...options,
	});
}

// useAlerts — 2번째 인자로 options 추가
export function useAlerts(thesisId?: string, options?: { enabled?: boolean }) {
	return useQuery<ThesisAlert[]>({
		queryKey: ["thesis", "alerts", thesisId ?? "all"],
		queryFn: () => thesisApi.listAlerts(thesisId),
		...options,
	});
}
```

> **하위 호환 (P2)**: 기존 호출부(`useThesisList()`, `useAlerts()`, `useAlerts(thesisId)`)는 **절대 수정하지 않는다**. options는 새 호출부에서만 사용.

> **확장 여지**: 이번 PR에서는 `{ enabled?: boolean }`만 사용하되, 추후 react-query 옵션 확장(`staleTime`, `select` 등) 가능성을 해치지 않도록 구현을 단순하게 유지한다. 확장이 필요해지는 시점(FE-PR-3~4)에 `Omit<UseQueryOptions, 'queryKey' | 'queryFn'>` 등으로 넓히면 변경 비용은 1줄.

---

### [8] `lib/thesis/utils.ts` — 수정 (R2, R4, R5, M6, M7, M8)

이 PR에서 가장 변경이 많은 파일. 핵심 변경 사항을 순서대로 기술.
P3(미래 시간 방어), P4(2차 정렬)는 각각 변경 3, 변경 4 내부에 포함.

#### 변경 1: degreeToColor 색상 수정 (R4, R5)

```ts
// 변경 전 → 변경 후
// 72~108: '#9CA3AF' → '#D1D5DB'   (R4: 대비 3.2:1 → 5:1)
// 144~180: '#DC2626' → '#EF4444'  (R5: 대비 3.8:1 → 5:1)
```

#### 변경 2: stateToDisplay 용어 + 색상 분리 + icon 타입 안전 (R2, M6)

```ts
import type { ThesisState, ThesisStateIconKey } from "./types";

// ── 상태 표시 정보 ──
interface StateDisplayInfo {
	label: string;
	colorClass: string;
	icon: ThesisStateIconKey; // ← string이 아닌 union type (M6)
}

export function stateToDisplay(state: ThesisState): StateDisplayInfo {
	const map: Record<ThesisState, StateDisplayInfo> = {
		warming_up: {
			label: "데이터 수집 중",
			colorClass: "text-gray-400 bg-gray-800 border-gray-700",
			icon: "loader",
		},
		active: {
			label: "추적 중",
			colorClass: "text-blue-400 bg-blue-900/30 border-blue-800",
			icon: "eye",
		},
		strengthening: {
			label: "지지 신호 증가",
			colorClass: "text-green-400 bg-green-900/30 border-green-800",
			icon: "trending_up",
		},
		weakening: {
			label: "반박 신호 증가",
			colorClass: "text-orange-400 bg-orange-900/30 border-orange-800",
			icon: "trending_down",
		},
		critical: {
			label: "주의 필요",
			colorClass: "text-red-400 bg-red-900/30 border-red-800",
			icon: "alert_triangle",
		},
		needs_review: {
			label: "점검 필요",
			colorClass: "text-yellow-400 bg-yellow-900/30 border-yellow-800",
			icon: "clock",
		},
		expired: {
			label: "기간 만료",
			colorClass: "text-amber-400 bg-amber-900/30 border-amber-800",
			icon: "timer",
		},
		closed_correct: {
			label: "적중",
			colorClass: "text-green-400 bg-green-900/30 border-green-800",
			icon: "check_circle",
		},
		closed_incorrect: {
			label: "빗나감",
			colorClass: "text-red-400 bg-red-900/30 border-red-800",
			icon: "x_circle",
		},
		closed_neutral: {
			label: "미확정",
			colorClass: "text-gray-500 bg-gray-800/50 border-gray-700",
			icon: "minus_circle",
		},
	};
	return map[state] ?? map.active;
}
```

**타입 안전 효과**: `icon: 'trending_UP'` 같은 오타를 `tsc`가 즉시 잡아줌.

#### 변경 3: relativeTime 유틸 분리 (M7)

TodayChangeCard 내부 함수에서 추출. 이후 알림 목록(FE-PR-6), 대시보드(FE-PR-5)에서 재사용.

```ts
// ── 상대 시간 포맷 ──
// 사용처: TodayChangeCard, 알림 목록(FE-PR-6), 대시보드(FE-PR-5)
export function relativeTime(dateStr: string): string {
	const diff = Date.now() - new Date(dateStr).getTime();
	// 미래 시간 방어 (P3): 서버 시계 차이/timezone 변환 문제로 음수 diff 가능
	if (diff < 0) return "방금 전";
	const minutes = Math.floor(diff / 60000);
	if (minutes < 1) return "방금 전";
	if (minutes < 60) return `${minutes}분 전`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}시간 전`;
	const days = Math.floor(hours / 24);
	if (days < 7) return `${days}일 전`;
	return new Date(dateStr).toLocaleDateString("ko-KR", {
		month: "short",
		day: "numeric",
	});
}
```

#### 변경 4: 가설 목록 정렬 유틸 (M8)

투자자가 중요한 가설을 먼저 볼 수 있도록 current_state 우선순위 기반 정렬.

```ts
// ── 가설 상태 우선순위 (낮을수록 먼저 표시) ──
// 투자자가 "지금 가장 봐야 할 가설"을 먼저 보도록 정렬.
// critical(즉시 대응) > needs_review(주의) > weakening(반박 증가) > strengthening(확인) > active/warming_up(안정)
const STATE_PRIORITY: Record<ThesisState, number> = {
	critical: 0,
	needs_review: 1,
	weakening: 2,
	strengthening: 3,
	active: 4,
	warming_up: 5,
	expired: 6,
	closed_correct: 7,
	closed_incorrect: 7,
	closed_neutral: 7,
};

export function sortThesesByPriority<
	T extends { current_state: ThesisState; created_at: string },
>(theses: T[]): T[] {
	return [...theses].sort(
		(a, b) =>
			(STATE_PRIORITY[a.current_state] ?? 99) -
				(STATE_PRIORITY[b.current_state] ?? 99) ||
			// 2차 정렬 (P4): 동순위 시 최신 생성순 — 목록 순서 안정성 보장
			new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
	);
}
```

**설계 포인트**:

- `Record<ThesisState, number>`로 모든 상태를 빠짐없이 커버 — 새 상태 추가 시 `tsc`가 누락 잡아줌
- 2차 정렬 `created_at` 최신순 (P4): 동순위 가설이 여러 개일 때 목록 순서가 일관되게 유지. `||` 연산자로 1차 정렬이 0(동순위)일 때만 2차 비교 실행
- 제네릭 `<T extends { current_state: ThesisState; created_at: string }>`로 Thesis 외 타입에도 재사용 가능
- 원본 배열 불변 (`[...theses].sort`)

---

### [7] `components/thesis/common/ThesisBadge.tsx` — 수정 (R1, M6)

이모지를 lucide-react 아이콘으로 교체. icon 키를 `ThesisStateIconKey` union type으로 타입 안전하게 매핑.

```tsx
"use client";

import { stateToDisplay } from "@/lib/thesis/utils";
import type {
	ThesisState,
	Direction,
	ThesisStateIconKey,
} from "@/lib/thesis/types";
import {
	TrendingUp,
	TrendingDown,
	Minus,
	Eye,
	Loader,
	AlertTriangle,
	Clock,
	Timer,
	CheckCircle,
	XCircle,
	MinusCircle,
} from "lucide-react";

// ── 상태 아이콘 맵: ThesisStateIconKey → lucide 컴포넌트 ──
// icon key와 컴포넌트의 1:1 매핑. key가 ThesisStateIconKey 타입이므로
// stateToDisplay에서 오타 반환 시 여기서도 타입 에러 발생.
const stateIconMap: Record<
	ThesisStateIconKey,
	React.ComponentType<{ size?: number }>
> = {
	loader: Loader,
	eye: Eye,
	trending_up: TrendingUp,
	trending_down: TrendingDown,
	alert_triangle: AlertTriangle,
	clock: Clock,
	timer: Timer,
	check_circle: CheckCircle,
	x_circle: XCircle,
	minus_circle: MinusCircle,
};

// ── 방향 아이콘 ──
const directionIconMap: Record<
	Direction,
	React.ComponentType<{ size?: number }>
> = {
	bullish: TrendingUp,
	bearish: TrendingDown,
	neutral: Minus,
};

interface Props {
	state: ThesisState;
	direction: Direction;
}

export function ThesisBadge({ state, direction }: Props) {
	const { label, colorClass, icon } = stateToDisplay(state);
	const StateIcon = stateIconMap[icon];
	const DirIcon = directionIconMap[direction];

	return (
		<span
			className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full
                      text-xs font-medium border ${colorClass}`}>
			<DirIcon size={12} />
			<StateIcon size={12} />
			{label}
		</span>
	);
}
```

**타입 안전 체인**: `stateToDisplay` → `ThesisStateIconKey` 반환 → `stateIconMap[icon]` 인덱싱. 어느 단계에서든 오타가 있으면 `tsc`가 잡음.

---

### [6] `app/thesis/layout.tsx` — 수정 (R3)

헤더 sticky 적용.

```diff
- <div className="flex items-center justify-between mb-6">
+ <div className="sticky top-0 z-10 bg-gray-950/95 backdrop-blur-sm
+                 flex items-center justify-between py-4 -mx-4 px-4 mb-2">
```

**주의**: `backdrop-blur-sm`은 iOS Safari 15+, Chrome 76+ 지원. 대상 유저(20~40대, 모바일) 커버리지 충분.

---

### [4] `lib/thesis/mock.ts` — 신규

백엔드 미연동 상태에서 UI 개발/검증용 Mock 데이터.

```ts
import type { Thesis, ThesisAlert } from "./types";

export const MOCK_THESES: Thesis[] = [
	{
		id: "mock-1",
		title: "AI 반도체 수요 증가로 NVIDIA 상승 지속",
		direction: "bullish",
		target: "NVDA",
		thesis_type: "sector_trend",
		status: "active",
		current_state: "strengthening",
		current_score: 0.72,
		overall_label: "지지 신호 증가",
		created_at: "2025-03-01T09:00:00Z",
		closed_at: null,
		expected_timeframe: "2025-06-01",
		ai_summary: null,
	},
	{
		id: "mock-2",
		title: "금리 인하 기대감으로 부동산 REITs 반등",
		direction: "bullish",
		target: "VNQ",
		thesis_type: "macro_event",
		status: "active",
		current_state: "active",
		current_score: 0.15,
		overall_label: "추적 중",
		created_at: "2025-03-05T09:00:00Z",
		closed_at: null,
		expected_timeframe: "2025-09-01",
		ai_summary: null,
	},
	{
		id: "mock-3",
		title: "중국 경기 둔화로 원자재 약세 전환",
		direction: "bearish",
		target: "DBC",
		thesis_type: "macro_event",
		status: "active",
		current_state: "critical",
		current_score: -0.65,
		overall_label: "주의 필요",
		created_at: "2025-02-15T09:00:00Z",
		closed_at: null,
		expected_timeframe: "2025-05-01",
		ai_summary: null,
	},
];

export const MOCK_ALERTS: ThesisAlert[] = [
	{
		id: "alert-1",
		thesis: "mock-1",
		alert_type: "indicator_shift",
		title: "NVIDIA 외국인 순매수 급증",
		message:
			"외국인 순매수가 5일 연속 증가하며 강한 지지 신호를 보이고 있어요.",
		is_read: false,
		created_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
	},
	{
		id: "alert-2",
		thesis: "mock-3",
		alert_type: "state_change",
		title: "원자재 가설 반박 신호 감지",
		message: "구리 선물 가격이 예상과 반대 방향으로 움직이고 있어요.",
		is_read: false,
		created_at: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
	},
	{
		id: "alert-3",
		thesis: "mock-2",
		alert_type: "indicator_shift",
		title: "REITs ETF 거래량 급증",
		message: "VNQ 거래량이 평소 대비 200% 증가했어요.",
		is_read: false,
		created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
	},
];

// ── Mock 활성화 플래그 ──
// 백엔드 연동 후 .env.local에서 NEXT_PUBLIC_USE_MOCK=false로 전환하거나 파일 자체를 제거.
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";
```

**v2 변경점**: mock-3의 `current_state`를 `weakening` → `critical`로 변경하여 정렬(M8) 검증이 쉽도록 조정. Mock 데이터가 3가지 다른 우선순위를 포함하므로 정렬 결과를 눈으로 확인 가능 (critical → strengthening → active 순).

---

### [1] `components/thesis/list/ThesisListCard.tsx` — 신규 (M3 반영)

가설 목록의 개별 행 카드. 투자자 보조 정보(target + 추적 일수)를 한 줄에 표시.

```tsx
"use client";

import Link from "next/link";
import type { Thesis } from "@/lib/thesis/types";
import { MoonPhase, ThesisBadge } from "@/components/thesis";
import { daysWatching } from "@/lib/thesis/utils";
import { ChevronRight } from "lucide-react";

interface Props {
	thesis: Thesis;
}

export function ThesisListCard({ thesis }: Props) {
	return (
		<Link
			href={`/thesis/${thesis.id}`}
			className='block bg-gray-900 border border-gray-800 rounded-xl p-4
                 active:scale-[0.98] transition-transform'>
			<div className='flex items-center gap-3'>
				{/* 달 위상 — 왼쪽 고정 */}
				<div className='flex-shrink-0'>
					<MoonPhase
						score={thesis.current_score}
						size='sm'
					/>
				</div>

				{/* 중앙 정보 */}
				<div className='flex-1 min-w-0'>
					<p className='text-white text-sm font-medium truncate'>
						{thesis.title}
					</p>
					<div className='flex items-center gap-2 mt-1.5'>
						<ThesisBadge
							state={thesis.current_state}
							direction={thesis.direction}
						/>
					</div>
					{/* ── 보조 정보: target + 추적 일수 (M3, P1) ── */}
					<p className='text-gray-500 text-xs mt-1'>
						{thesis.target?.trim() ? `${thesis.target.trim()} · ` : ""}
						{daysWatching(thesis.created_at)}일째 추적 중
					</p>
				</div>

				{/* 오른쪽 화살표 */}
				<ChevronRight
					size={16}
					className='text-gray-600 flex-shrink-0'
				/>
			</div>
		</Link>
	);
}
```

**설계 포인트 (v2.1)**:

- `target`을 보조 정보 첫 항목으로 배치 — 투자자가 "어떤 종목 가설인지"를 카드 스캔만으로 파악 가능
- `target` null-safe (P1): `thesis.target?.trim()` 으로 null, undefined, 빈문자열, 공백문자열까지 방어. 백엔드에서 `" "` 같은 값이 넘어와도 `· 23일째`가 뜨지 않음
- `NVDA · 23일째 추적 중` 형태로 간결하게 한 줄 유지
- `expected_timeframe`은 null일 수 있고 포맷팅 복잡도가 올라가므로 우선순위 A(target)로 확정
- 텍스트 과밀 방지: badge와 보조 정보 사이 `mt-1.5`로 시각 분리

---

### [2] `components/thesis/list/TodayChangeCard.tsx` — 신규 (M7 반영)

오늘의 변화 알림 카드. relativeTime은 utils에서 import.

```tsx
"use client";

import Link from "next/link";
import type { ThesisAlert } from "@/lib/thesis/types";
import { relativeTime } from "@/lib/thesis/utils";
import { Bell } from "lucide-react";

interface Props {
	alert: ThesisAlert;
}

export function TodayChangeCard({ alert }: Props) {
	return (
		<Link
			href={`/thesis/${alert.thesis}?highlight=${alert.id}`}
			className='block bg-gray-900 border border-gray-800 rounded-xl p-4
                 active:scale-[0.98] transition-transform'>
			<div className='flex items-start gap-3'>
				<div className='flex-shrink-0 mt-0.5'>
					<Bell
						size={16}
						className='text-yellow-400'
					/>
				</div>
				<div className='flex-1 min-w-0'>
					<p className='text-white text-sm font-medium'>{alert.title}</p>
					<p className='text-gray-400 text-xs mt-1 line-clamp-1'>
						{alert.message}
					</p>
				</div>
				<span className='text-gray-600 text-xs flex-shrink-0 whitespace-nowrap'>
					{relativeTime(alert.created_at)}
				</span>
			</div>
		</Link>
	);
}
```

**v2 변경점**: `relativeTime`을 컴포넌트 내부 함수 → `@/lib/thesis/utils` import로 변경 (M7). 컴포넌트는 순수 렌더링 책임만 유지.

---

### [3] `components/thesis/list/EntryPointGrid.tsx` — 신규 (M2, M5 반영)

활성 2개 + 준비 중 1개로 축소. 미완성 인상 최소화.

```tsx
"use client";

import { useRouter } from "next/navigation";
import { MessageSquare, Newspaper, Link2 } from "lucide-react";

// ── 진입점 정의 ──
// Phase 1에서 렌더링하는 항목만 이 배열에 포함.
// Phase 2에서 Flame(인기 가설), FileText(템플릿) 추가 시 이 배열에 항목을 추가하면 됨.
// enabled=false 항목은 최대 1개만 유지하여 첫인상 완성도를 보장.
interface EntryPoint {
	key: string;
	label: string;
	icon: React.ComponentType<{ size?: number; className?: string }>;
	source: string;
	enabled: boolean;
}

const VISIBLE_ENTRY_POINTS: EntryPoint[] = [
	{
		key: "free_text",
		label: "내 생각",
		icon: MessageSquare,
		source: "free_text",
		enabled: true,
	},
	{
		key: "news",
		label: "오늘 이슈",
		icon: Newspaper,
		source: "news",
		enabled: true,
	},
	{
		key: "chain_sight",
		label: "Chain Sight에서",
		icon: Link2,
		source: "chain_sight",
		enabled: false,
	},
];

// ── Phase 2에서 추가될 진입점 (현재 렌더링하지 않음) ──
// { key: 'popular',   label: '인기 가설', icon: Flame,    source: 'popular',  enabled: false },
// { key: 'template',  label: '템플릿',    icon: FileText, source: 'template', enabled: false },

export function EntryPointGrid() {
	const router = useRouter();

	const handleClick = (entry: EntryPoint) => {
		if (!entry.enabled) {
			showTemporaryToast("곧 열릴 기능이에요!");
			return;
		}
		router.push(`/thesis/new?entry=${entry.source}`);
	};

	return (
		<div className='grid grid-cols-2 gap-3'>
			{VISIBLE_ENTRY_POINTS.map((entry) => {
				const Icon = entry.icon;
				return (
					<button
						key={entry.key}
						onClick={() => handleClick(entry)}
						className={`flex items-center gap-3 bg-gray-900 border rounded-xl p-4
                       text-left transition-all active:scale-[0.97]
                       ${
													entry.enabled
														? "border-gray-700 hover:border-gray-600 text-white"
														: "border-gray-800 text-gray-500 opacity-60"
												}
                       ${entry.key === "chain_sight" ? "col-span-2" : ""}`}>
						<Icon
							size={20}
							className={entry.enabled ? "text-blue-400" : "text-gray-600"}
						/>
						<span className='text-sm font-medium'>{entry.label}</span>
						{!entry.enabled && (
							<span className='ml-auto text-[10px] text-gray-600 bg-gray-800 px-2 py-0.5 rounded-full'>
								준비 중
							</span>
						)}
					</button>
				);
			})}
		</div>
	);
}

// ══════════════════════════════════════════════════════════════════
// 임시 Toast — DOM 직접 조작 방식 (M5)
// ──────────────────────────────────────────────────────────────────
// 왜 임시인가:
//   현재 프로젝트에 글로벌 Toast 시스템이 없으므로, React 외부에서
//   DOM을 직접 생성/제거하는 방식으로 구현.
//   이 방식은 React 상태 관리 바깥이라 테스트·접근성·애니메이션 제어가 제한적.
//
// 교체 계획:
//   FE-PR-3(대화형 빌더)에서 Toast가 본격적으로 필요해지는 시점에
//   아래 후보 중 하나를 도입하고 이 함수를 제거할 것:
//   - sonner (4KB, 다크테마 기본 지원, 권장)
//   - react-hot-toast (5KB, 커뮤니티 넓음)
//   - shadcn/ui toast (이미 shadcn 의존성이 있다면 추가 비용 0)
//
// 제약 조건:
//   - 연속 클릭 시 중복 누적 방지 (기존 toast 제거 후 새로 생성)
//   - 2초 후 자연스럽게 제거
//   - 클라이언트 전용 ('use client' 컴포넌트 내부에서만 호출)
// ══════════════════════════════════════════════════════════════════
function showTemporaryToast(message: string) {
	if (typeof window === "undefined") return;

	// 중복 방지: 기존 toast가 있으면 제거
	const existing = document.getElementById("thesis-toast");
	if (existing) existing.remove();

	const toast = document.createElement("div");
	toast.id = "thesis-toast";
	toast.textContent = message;
	toast.className = [
		"fixed bottom-24 left-1/2 -translate-x-1/2 z-50",
		"bg-gray-800 text-white text-sm px-4 py-2 rounded-full",
		"shadow-lg animate-fadeIn",
	].join(" ");
	document.body.appendChild(toast);
	setTimeout(() => {
		if (toast.parentNode) toast.remove();
	}, 2000);
}
```

**v2 변경점**:

- 렌더링 항목 5개 → 3개로 축소 (M2). 활성 2개 + 준비 중 1개(Chain Sight)
- 인기 가설/템플릿은 주석으로만 Phase 2 확장 가이드 제공
- Toast 함수명을 `showToast` → `showTemporaryToast`로 변경하여 임시성 표현
- Toast 주석을 TODO 수준이 아닌 "왜 임시인지 + 교체 후보 + 제약 조건" 수준으로 상세화 (M5)
- `if (toast.parentNode)` 가드 추가로 이미 제거된 경우 대응

---

### [5] `app/thesis/page.tsx` — 전면 교체 (M1, M4, M8 반영)

PR-1의 skeleton placeholder를 실제 구현으로 교체.

```tsx
"use client";

import { useMemo } from "react";
import { useThesisList, useAlerts } from "@/lib/thesis/queries";
import { sortThesesByPriority } from "@/lib/thesis/utils";
import { ThesisListSkeleton } from "@/components/thesis/skeleton/ThesisSkeleton";
import { ThesisListCard } from "@/components/thesis/list/ThesisListCard";
import { TodayChangeCard } from "@/components/thesis/list/TodayChangeCard";
import { EntryPointGrid } from "@/components/thesis/list/EntryPointGrid";
import { MoonPhase } from "@/components/thesis";
import { RefreshCw } from "lucide-react";
import { USE_MOCK, MOCK_THESES, MOCK_ALERTS } from "@/lib/thesis/mock";

export default function ThesisPage() {
	return (
		<div className='space-y-8'>
			<ActiveThesesSection />
			<TodayChangesSection />
			<NewThesisSection />
		</div>
	);
}

// ═══ 섹션 1: 추적 중 가설 목록 ═══
function ActiveThesesSection() {
	// ── Mock 모드 분기 (M1) ──
	// USE_MOCK=true일 때 enabled:false로 실제 네트워크 요청 차단.
	// hook 호출 자체는 유지하여 Rules of Hooks 준수.
	const { data, isLoading, isError, refetch } = useThesisList({
		enabled: !USE_MOCK,
	});

	const theses = USE_MOCK ? MOCK_THESES : data;

	if (isLoading && !USE_MOCK) return <ThesisListSkeleton />;

	if (isError && !USE_MOCK) {
		return (
			<div className='text-center py-12'>
				<p className='text-gray-400 text-sm mb-3'>
					데이터를 불러오지 못했어요.
				</p>
				<button
					onClick={() => refetch()}
					className='inline-flex items-center gap-2 text-blue-400 text-sm
                     hover:text-blue-300 transition-colors'>
					<RefreshCw size={14} />
					새로고침
				</button>
			</div>
		);
	}

	const activeTheses = (theses ?? []).filter((t) => t.status === "active");

	// ── 상태 우선순위 정렬 (M8) ──
	// critical → needs_review → weakening → strengthening → active → warming_up
	// useMemo로 감싸서 theses 변경 시에만 정렬 재실행 (가설 수십 개일 때 불필요한 재정렬 방지)
	const sorted = useMemo(
		() => sortThesesByPriority(activeTheses),
		[activeTheses],
	);

	return (
		<section>
			<div className='flex items-center justify-between mb-3'>
				<h2 className='text-gray-300 text-sm font-medium'>
					추적 중
					{sorted.length > 0 && (
						<span className='ml-1.5 text-gray-500'>{sorted.length}</span>
					)}
				</h2>
			</div>

			{sorted.length === 0 ? (
				<EmptyTheses />
			) : (
				<ul className='space-y-3'>
					{sorted.map((thesis) => (
						<li key={thesis.id}>
							<ThesisListCard thesis={thesis} />
						</li>
					))}
				</ul>
			)}
		</section>
	);
}

// ═══ 섹션 2: 오늘의 변화 ═══
function TodayChangesSection() {
	const { data } = useAlerts(undefined, {
		enabled: !USE_MOCK,
	});

	const alerts = USE_MOCK ? MOCK_ALERTS : data;

	const unreadAlerts = (alerts ?? []).filter((a) => !a.is_read).slice(0, 3);

	return (
		<section>
			<h2 className='text-gray-300 text-sm font-medium mb-3'>오늘의 변화</h2>

			{unreadAlerts.length === 0 ? (
				// ── 시간 중립 문구 (M4) ──
				// created_at 기반 "오늘"/"지난밤" 필터링 미구현 상태이므로
				// 시간 해석이 포함된 문구("어젯밤") 대신 데이터 조건과 일치하는 중립 문구 사용.
				<p className='text-gray-600 text-sm py-4 text-center'>
					새로운 변화가 아직 없어요.
				</p>
			) : (
				<ul className='space-y-2'>
					{unreadAlerts.map((alert) => (
						<li key={alert.id}>
							<TodayChangeCard alert={alert} />
						</li>
					))}
				</ul>
			)}
		</section>
	);
}

// ═══ 섹션 3: 새 가설 진입점 ═══
function NewThesisSection() {
	return (
		<section>
			<h2 className='text-gray-300 text-sm font-medium mb-3'>새로운 가설</h2>
			<EntryPointGrid />
		</section>
	);
}

// ═══ 빈 상태 ═══
function EmptyTheses() {
	return (
		<div className='text-center py-12 bg-gray-900/50 rounded-xl border border-dashed border-gray-800'>
			<MoonPhase
				score={null}
				size='md'
			/>
			<p className='text-gray-400 text-sm mt-4'>
				아직 추적 중인 가설이 없어요.
			</p>
			<p className='text-gray-600 text-xs mt-1'>
				아래에서 첫 가설을 세워보세요!
			</p>
		</div>
	);
}
```

**v2 핵심 변경점**:

**M1 (Mock query 비활성화)**:
`useThesisList({ enabled: !USE_MOCK })` 형태로 옵션 전달. 이를 위해 `queries.ts`의 hook 시그니처도 수정이 필요함:

```ts
// queries.ts — useThesisList 시그니처 확장
export function useThesisList(options?: { enabled?: boolean }) {
	return useQuery<Thesis[]>({
		queryKey: ["thesis", "list"],
		queryFn: () => thesisApi.list(),
		...options, // enabled 등 외부 옵션 주입
	});
}

// queries.ts — useAlerts 시그니처 확장
export function useAlerts(thesisId?: string, options?: { enabled?: boolean }) {
	return useQuery<ThesisAlert[]>({
		queryKey: ["thesis", "alerts", thesisId ?? "all"],
		queryFn: () => thesisApi.listAlerts(thesisId),
		...options,
	});
}
```

> **하위 호환 (P2)**: 두 함수 모두 optional 파라미터 추가이므로 기존 호출부(`useThesisList()`, `useAlerts()`, `useAlerts(thesisId)`)는 **절대 수정하지 않는다**. 기존 호출부의 시그니처를 바꾸거나 인자를 추가하는 것은 금지. options는 새 호출부에서만 사용.

**M4 (시간 중립 문구)**: "어젯밤 특별한 변화는 없었어요" → "새로운 변화가 아직 없어요." + 주석으로 왜 이 문구인지 설명.

**M8 (정렬)**: `sortThesesByPriority(activeTheses)` 호출. Mock 데이터에 3가지 다른 priority가 있으므로 정렬 결과가 눈에 보임 (critical → strengthening → active).

---

## 3. 의존성 그래프

```
lib/thesis/types.ts (수정: ThesisStateIconKey 추가)
    |
    +-> lib/thesis/utils.ts (수정: R2,R4,R5,M6,M7,M8)
    |       |
    |       +-> components/thesis/common/ThesisBadge.tsx (수정: R1,M6)
    |       |       |
    |       |       +-> components/thesis/list/ThesisListCard.tsx (신규, M3)
    |       |
    |       +-> components/thesis/list/TodayChangeCard.tsx (신규, M7)
    |       |
    |       +-> app/thesis/page.tsx (전면 교체, M1,M4,M8)
    |
    +-> lib/thesis/queries.ts (수정: enabled 옵션 시그니처 추가)

lib/thesis/mock.ts (신규, types만 의존)
    |
    +-> app/thesis/page.tsx

components/thesis/list/EntryPointGrid.tsx (신규, 독립, M2,M5)

app/thesis/layout.tsx (수정: R3 sticky, 독립)
```

---

## 4. 구현 순서

```
Phase A (독립, 병렬):
  |- lib/thesis/types.ts 수정 (ThesisStateIconKey 추가)
  |- lib/thesis/mock.ts (신규, 독립)
  |- app/thesis/layout.tsx sticky 수정 (R3)

Phase B (Phase A 의존):
  |- lib/thesis/utils.ts 수정 (R2,R4,R5,M6,M7,M8 — types.ts 의존)
  |- lib/thesis/queries.ts 수정 (enabled 옵션 — types.ts 의존)

Phase C (Phase B 의존, 병렬):
  |- components/thesis/common/ThesisBadge.tsx 수정 (R1,M6 — utils+types 의존)
  |- components/thesis/list/TodayChangeCard.tsx (신규, M7 — utils 의존)
  |- components/thesis/list/EntryPointGrid.tsx (신규, M2,M5 — 독립)

Phase D (Phase C 의존):
  |- components/thesis/list/ThesisListCard.tsx (신규, M3 — ThesisBadge+MoonPhase 의존)

Phase E (Phase D 의존):
  |- app/thesis/page.tsx 전면 교체 (M1,M4,M8 — 모든 컴포넌트 + queries 의존)
```

총 작업량: ~400줄 신규 + ~70줄 수정. 예상 소요: Claude Code 1회 세션.

---

## 5. 검증 체크리스트

### 5.1 빌드 검증

| 검증 항목            | 명령어                       | 기대 결과                 |
| -------------------- | ---------------------------- | ------------------------- |
| TypeScript 타입 체크 | `tsc --noEmit`               | 에러 0개                  |
| Next.js 빌드         | `npm run build`              | 성공 + thesis 라우트 포함 |
| 기존 기능 회귀       | 로그인 → 대시보드 → 로그아웃 | 정상 동작                 |

### 5.2 Mock 검증 (M1)

| 시나리오                    | 기대 동작                                                   |
| --------------------------- | ----------------------------------------------------------- |
| `NEXT_PUBLIC_USE_MOCK=true` | 3개 가설 카드 렌더링 (critical → strengthening → active 순) |
| `NEXT_PUBLIC_USE_MOCK=true` | 3개 알림 카드 렌더링                                        |
| `NEXT_PUBLIC_USE_MOCK=true` | 브라우저 네트워크 탭에 thesis API 요청 0건                  |
| `NEXT_PUBLIC_USE_MOCK=true` | 콘솔에 401/에러 로그 0건                                    |

### 5.3 Non-Mock 검증

| 시나리오                                     | 기대 동작                              |
| -------------------------------------------- | -------------------------------------- |
| `NEXT_PUBLIC_USE_MOCK=false` + 백엔드 미연동 | 에러 UI ("데이터를 불러오지 못했어요") |
| `NEXT_PUBLIC_USE_MOCK=false` + 백엔드 연동   | 실제 데이터 렌더링                     |

### 5.4 UI 검증

| 시나리오                 | 기대 동작                                                               |
| ------------------------ | ----------------------------------------------------------------------- |
| 가설 카드                | target 표시됨 (e.g. "NVDA · 23일째 추적 중")                            |
| 가설 카드 (target 빈 값) | 추적 일수만 표시 ("23일째 추적 중"), `null ·` 이나 `undefined ·` 미노출 |
| 가설 0개                 | 빈 상태 UI (달 아이콘 + 안내 문구)                                      |
| 알림 0개                 | "새로운 변화가 아직 없어요." (시간 중립)                                |
| 가설 목록 순서           | critical 가설이 최상단                                                  |
| 진입점                   | 3개만 표시 (내 생각, 오늘 이슈, Chain Sight)                            |
| "Chain Sight에서" 클릭   | toast "곧 열릴 기능이에요!"                                             |
| toast 연속 클릭          | 중복 누적 없이 1개만 표시                                               |
| 스크롤                   | 헤더 sticky 유지                                                        |
| ThesisBadge              | lucide 아이콘, 상태별 색상 분리 확인                                    |
| 가설 카드 탭             | `/thesis/{id}` 이동 + scale 애니메이션                                  |
| 알림 카드 탭             | `/thesis/{id}?highlight={alertId}` 이동                                 |

### 5.5 타입 안전 검증 (M6)

| 시나리오                                    | 기대 동작                         |
| ------------------------------------------- | --------------------------------- |
| stateToDisplay에 icon: 'trending_UP' (오타) | `tsc` 컴파일 에러                 |
| stateIconMap에 없는 key 추가 시도           | `tsc` 컴파일 에러                 |
| ThesisStateIconKey에 새 키 추가 시 map 누락 | `tsc` 컴파일 에러 (Record 완전성) |

### 5.6 접근성 검증

| 항목                            | 기대                                       |
| ------------------------------- | ------------------------------------------ |
| 색상 대비 (중립 회색 `#D1D5DB`) | WCAG AA (5:1+)                             |
| 색상 대비 (강한 반박 `#EF4444`) | WCAG AA (5:1+)                             |
| 터치 타겟                       | 최소 44×44px (카드 전체 영역)              |
| 스크린 리더                     | Link 요소에 의미 있는 텍스트               |
| 시맨틱 HTML                     | 가설 목록·알림 목록이 `ul`/`li`로 마크업됨 |

---

## 6. 리스크 및 완화

| #   | 리스크                                                            | 심각도 | 완화                                                                                   |
| --- | ----------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------- |
| 1   | queries.ts 시그니처 변경 (enabled 옵션 추가)                      | 낮음   | optional 파라미터 추가이므로 기존 호출부 영향 없음                                     |
| 2   | stateToDisplay 반환 타입 변경 (icon: string → ThesisStateIconKey) | 낮음   | PR-1에서 icon 필드 미사용. 이번 PR에서 처음 사용                                       |
| 3   | Mock 데이터 실제 API 스키마 불일치                                | 중간   | Thesis 인터페이스 기준으로 mock 작성. 백엔드 PR-3 연동 시 비교 검증                    |
| 4   | 임시 Toast DOM 조작 → React hydration 불일치                      | 낮음   | 클라이언트 전용 컴포넌트('use client')이므로 hydration 이슈 없음                       |
| 5   | layout.tsx sticky + backdrop-blur 성능                            | 낮음   | 단일 요소, 모던 브라우저 GPU 가속. 체감 차이 없음                                      |
| 6   | useThesisList + useAlerts 동시 호출 → 미인증 시 2번 401           | 낮음   | Mock 모드에서는 enabled:false로 발생 안 함. Non-mock에서는 authAxios pendingQueue 처리 |
| 7   | sortThesesByPriority에 새 ThesisState 추가 시 priority 미정의     | 낮음   | `STATE_PRIORITY`가 `Record<ThesisState, number>`이므로 `tsc`가 누락 잡아줌             |

---

## 7. 기술 부채 (이번 PR 범위 밖)

| 부채                                                                  | 영향                                                               | 해소 시점                                                                       |
| --------------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| 임시 Toast (DOM 직접 조작)                                            | 테스트·접근성·애니메이션 제한                                      | FE-PR-3에서 sonner 등 toast 라이브러리 도입 시 교체                             |
| Mock 데이터 하드코딩                                                  | 백엔드 연동 후 제거 필요                                           | 백엔드 PR-3 완료 후 `USE_MOCK=false` + mock.ts 삭제                             |
| 클라이언트 필터링 (`status === 'active'`)                             | 전체 가설 fetch 후 필터 → 가설 수 증가 시 비효율                   | 백엔드에서 `?status=active` 쿼리 파라미터 지원 시 서버 필터링 전환              |
| ThesisBadge 이모지 → lucide (R1) 완료, 다른 공통 컴포넌트 이모지 잔존 | IndicatorCard 등 이모지 남아있음                                   | FE-PR-4~5에서 점진적 교체                                                       |
| relativeTime 로케일 하드코딩 ('ko-KR')                                | 다국어 대응 불가                                                   | 국제화 필요 시 i18n 유틸로 전환                                                 |
| relativeTime 실시간 갱신 누락                                         | 페이지 체류 시 "방금 전"이 계속 유지됨 (리렌더링 없으면 시간 멈춤) | FE-PR-6 알림 목록에서 `setInterval` 갱신 또는 `timeago` 류 라이브러리 도입 검토 |

---

## 8. 후속 PR 연결

| 이 PR에서 만든 것            | 사용하는 PR                                           |
| ---------------------------- | ----------------------------------------------------- |
| ThesisListCard               | FE-PR-2 전용 (재사용 없음)                            |
| TodayChangeCard              | FE-PR-6 알림 목록에서 유사 패턴 재활용 가능           |
| EntryPointGrid               | FE-PR-3 빌더에서 `entry` 쿼리 파라미터 수신 처리      |
| Mock 데이터                  | FE-PR-3~5에서 확장 가능 (DashboardResponse mock 추가) |
| 용어 변경 (stateToDisplay)   | 이후 모든 PR에서 자동 적용                            |
| lucide 아이콘 (ThesisBadge)  | 이후 모든 PR에서 자동 적용                            |
| ThesisStateIconKey           | FE-PR-5 대시보드에서 동일 타입 재사용                 |
| relativeTime                 | FE-PR-5 대시보드, FE-PR-6 알림 목록에서 재사용        |
| sortThesesByPriority         | FE-PR-5 대시보드 전제 정렬에 재사용 가능              |
| queries.ts enabled 옵션 패턴 | FE-PR-3~6에서 Mock 모드 동일 패턴 적용                |

---

## 9. Claude Code 실행 프롬프트

```
FE-PR-2 구현 계획서(docs/thesis_control/thesis_control_phase1_frontend_FE_PR_2.md) v2.1을 읽고,
Thesis Control 첫 화면을 구현해줘.

─────────────────────────────────────────────
[구현 순서]
─────────────────────────────────────────────

1단계: 타입 + 유틸 수정
  - lib/thesis/types.ts: ThesisStateIconKey union type 추가
  - lib/thesis/utils.ts:
    · degreeToColor 색상 수정 (#9CA3AF→#D1D5DB, #DC2626→#EF4444)
    · stateToDisplay 용어 변경 + icon 타입을 ThesisStateIconKey로 변경 + 색상 분리
    · relativeTime 유틸 함수 추가
    · sortThesesByPriority 정렬 유틸 추가 (STATE_PRIORITY 상수 맵)
  - lib/thesis/queries.ts: useThesisList, useAlerts에 options?: { enabled?: boolean } 파라미터 추가

2단계: PR-1 리뷰 반영 (기존 컴포넌트 수정)
  - components/thesis/common/ThesisBadge.tsx: 이모지→lucide 아이콘 + stateIconMap을 ThesisStateIconKey 기반으로
  - app/thesis/layout.tsx: 헤더 sticky 적용

3단계: 신규 파일 생성
  - lib/thesis/mock.ts: Mock 데이터 (USE_MOCK 환경변수 기반)
  - components/thesis/list/ThesisListCard.tsx (target + 추적일수 보조정보 포함)
  - components/thesis/list/TodayChangeCard.tsx (relativeTime은 utils에서 import)
  - components/thesis/list/EntryPointGrid.tsx (활성 2 + 준비중 1개만 렌더링, 임시 toast 상세 주석)

4단계: 페이지 교체
  - app/thesis/page.tsx:
    · useThesisList/useAlerts에 enabled:!USE_MOCK 전달
    · sortThesesByPriority를 useMemo로 감싸서 정렬 (activeTheses 변경 시에만 재실행)
    · 가설 목록과 알림 목록은 ul/li 시맨틱 태그로 렌더링
    · 빈 알림 문구 "새로운 변화가 아직 없어요."

─────────────────────────────────────────────
[핵심 주의사항]
─────────────────────────────────────────────
- 다크 테마 전용. bg-white, text-black 절대 사용하지 않음.
- ThesisStateIconKey와 stateIconMap의 key는 반드시 일치해야 함 (Record 완전성).
- queries.ts의 useThesisList, useAlerts에 options 파라미터를 추가할 때,
  기존 호출부(useThesisList(), useAlerts(), useAlerts(thesisId))의 시그니처를 절대 변경하지 말 것.
  options는 반드시 optional 2번째(또는 마지막) 인자로만 추가하고, 기존 코드는 한 글자도 건드리지 않는다.
- Mock 모드(USE_MOCK=true)에서 브라우저 네트워크 탭/콘솔에 API 요청·에러 0건이어야 함.
- 임시 Toast는 showTemporaryToast 함수명 + 상세 주석 블록 필수.
- EntryPointGrid는 VISIBLE_ENTRY_POINTS 3개만 렌더링. Phase 2 항목은 주석으로만.
- ThesisListCard의 target 표시는 thesis.target?.trim()으로 null/undefined/빈문자열/공백문자열까지 방어할 것.
  target이 falsy이거나 공백뿐이면 추적 일수만 표시. `null · 23일째`나 ` · 23일째`가 화면에 뜨면 안 됨.
- relativeTime 유틸에서 diff < 0 (미래 시간)이면 '방금 전' 반환하는 방어 코드 필수.
- sortThesesByPriority에서 동순위 시 created_at 최신순 2차 정렬 포함할 것.
- page.tsx의 sorted 변수는 useMemo로 감쌀 것. activeTheses가 바뀔 때만 정렬 재실행.
- 가설 목록과 알림 목록은 div가 아닌 ul/li로 렌더링 (시맨틱 HTML).
- 구현 후 tsc --noEmit + npm run build 검증 필수.
```
