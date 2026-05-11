# FE-PR-4: 지표 설정 — 구현 계획 (v2)

> 버전: v2 (리뷰 반영)
> 작성일: 2026-03-13
> 범위: Layout Route Group 분리 + `app/thesis/[thesisId]/indicators/page.tsx` 전면 교체 + 지표 CRUD + AI 추천
> 전제조건: FE-PR-3 머지 완료
> 목표: 가설에 지표를 추가/삭제/토글하는 설정 페이지. AI 자동 추천(`?auto=true`)과 수동 추가 모두 지원.
> 참조: `thesis_control_design.md` (섹션 5.2), `thesis_control_phase1_frontend_FE_PR_3.md`
>
> ### v1 → v2 변경 요약
>
> | 이슈 | 심각도 | 결정 | 변경 |
> |------|--------|------|------|
> | Layout 충돌 (이중 헤더) | P0 | 수용 | Route Group 분리 + layout.tsx 분할 |
> | Mock 토글/삭제 미반영 | P1 | 수용 | `useState(MOCK_INDICATORS)` 로컬 상태 |
> | 중복 지표 방지 | P1 | 수용 | `addedNames` 기존 지표로 초기화 |
> | RecommendCard 방향 뱃지 | P2 | 수용 | `DIRECTION_LABELS` 추가 |
> | TYPE_LABELS 중복 | P3 | 수용 | 공유 상수 `INDICATOR_LABELS` 추출 |
> | Semantic HTML | P3 | 수용 | `ul/li` 적용 |
> | is_paused vs is_active | 부채 | 기록 | 기술 부채 섹션에 추가 |

---

## 0. PR-3 완료 자산 & 백엔드 API 발견사항

### 0.1 PR-3에서 물려받는 자산

| 자산                                         | 사용 위치             |
| -------------------------------------------- | --------------------- |
| `BottomSheet` (components/thesis/builder/)   | 지표 추가 시트 래퍼   |
| `ArrowIndicator` (components/thesis/common/) | 지표 카드 화살표 표시 |
| `sonner toast` (layout.tsx)                  | 에러/성공 알림        |
| `useThesis` (queries.ts)                     | 가설 제목/방향 표시   |
| `useIndicators` (queries.ts)                 | 지표 목록 조회        |
| `authAxios` (lib/api/authAxios.ts)           | JWT 인증 API 호출     |

### 0.2 백엔드 API 발견사항 (Critical)

#### 0.2.1 `autoRecommend` URL 불일치

**프론트엔드 현재 (`api.ts`)**:

```ts
autoRecommend: (thesisId: string) =>
	POST<ThesisIndicator[]>(`/thesis/${thesisId}/indicators/auto-recommend/`, {});
```

**백엔드 실제 (`ThesisIndicatorViewSet.auto`)**:

```python
@action(detail=False, methods=['post'])
def auto(self, request, thesis_id=None):
    # URL: POST /thesis/{thesis_id}/indicators/auto/
    # Response: { "indicators": [...], "count": N }
```

→ 3가지 불일치:

1. URL: `auto-recommend/` → `auto/`
2. 응답 타입: `ThesisIndicator[]` → `{ indicators: RecommendedIndicator[], count: number }`
3. 요청 본문: `{}` → `{ premise_id?: string }`

#### 0.2.2 `ThesisIndicator` 타입 불완전

현재 `types.ts`:

```ts
export interface ThesisIndicator {
	id: string;
	name: string;
	indicator_type: IndicatorType;
	support_direction: SupportDirection;
	current_arrow_degree: number; // 0 ~ 180
	current_label: string;
	current_color: string; // hex
	is_active: boolean;
	premise: string | null;
}
```

백엔드 `ThesisIndicatorSerializer` 반환 필드 (누락분):

```
data_source: string             // 'fmp' | 'fred' | 'news_sentiment' | 'manual' | 'custom'
data_params: Record<string, string | number>
weight: number                  // default 1.0
is_paused: boolean              // default false
current_score: number | null
current_degree: number | null   // ← 이것이 degree. current_arrow_degree 아님
override_score: number | null
window: number                  // read-only, default 60
decay: number                   // read-only, default 0.95
epsilon: number                 // read-only, default 0.0001
created_at: string              // ISO 8601
```

→ `ThesisIndicator` 인터페이스에 `data_source`, `data_params`, `weight`, `is_paused`, `current_score`, `created_at` 추가.
→ `current_arrow_degree` → `current_degree`로 필드명 확인 필요 (PR-1 ArrowIndicator와 호환성 확인).

**주의**: `current_arrow_degree`는 PR-1에서 프론트엔드가 정의한 이름. 백엔드 실제 필드명은 `current_degree`. dashboard API에서 `arrow_degree`로 변환하는지 확인 필요. PR-4에서는 `current_degree`를 사용하되, 기존 `current_arrow_degree` alias를 유지하여 PR-1 ArrowIndicator와의 호환성 보장.

#### 0.2.3 `is_ai_recommended` 플래그

백엔드 `perform_create`에서:

```python
is_ai = self.request.data.get('is_ai_recommended', False)
event_type = 'ai_suggestion_accepted' if is_ai else 'indicator_added'
```

→ AI 추천으로 추가할 때 `is_ai_recommended: true`를 요청 본문에 포함해야 올바른 이벤트 기록.

---

### 0.3 AI 추천 알고리즘 (indicator_matcher.py)

#### 1단계: 키워드 룰 매칭 (11개 룰셋, 즉시 응답)

| #   | 키워드                  | 추천 지표                     | data_source    |
| --- | ----------------------- | ----------------------------- | -------------- |
| 1   | 외국인, 순매수, foreign | 외국인 순매수 추이            | fmp            |
| 2   | 금리, 연준, FOMC, fed   | 미국 기준금리, 미국 10년 국채 | fred           |
| 3   | VIX, 공포, 변동성       | VIX (공포지수)                | fmp            |
| 4   | 환율, 달러, USD, KRW    | 원/달러 환율                  | fmp            |
| 5   | RSI, MACD, 기술적       | RSI (14일)                    | fmp            |
| 6   | 센티먼트, 심리, 뉴스    | 뉴스 센티먼트                 | news_sentiment |
| 7   | 실적, EPS, 매출         | EPS 추이                      | fmp            |
| 8   | 기관, 연기금            | 기관 순매수 추이              | fmp            |
| 9   | S&P, 나스닥, 다우       | S&P 500                       | fmp            |
| 10  | 코스피, KOSPI           | KOSPI 지수                    | fmp            |
| 11  | 선거, 정치, 정책        | VIX + KOSPI                   | fmp            |

#### 2단계: Gemini 2.5 Flash fallback (키워드 매칭 0건 시)

- 모델: `gemini-2.5-flash`, temperature 0.3, max_output_tokens 2000
- 3~5개 추천, JSON 배열 반환
- **소요 시간**: 2~5초 (네트워크 + 추론)
- 동기 API 사용 (Celery에서도 안전)

#### 응답 구조 (공통)

```ts
{
	name: string; // '외국인 순매수 추이'
	data_source: string; // 'fmp' | 'fred' | 'news_sentiment' | 'manual'
	data_params: object; // { metric: 'foreign_net_buy' }
	indicator_type: string; // 'market_data' | 'macro' | 'technical' | 'sentiment' | 'custom'
	support_direction: string; // 'positive' | 'negative'
	reason: string; // '외국인 투자자의 매매 동향은...'
}
```

---

## 0.4 설계 결정 (1인 개발자 관점)

| #   | 결정                                                   | 이유                                                                                                                |
| --- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| D1  | 전제(premise) 그룹핑 안 함 — 플랫 리스트               | 대시보드(PR-5)에서 premise별 그룹핑. 설정 페이지는 추가/삭제에 집중. 복잡도 ↓                                       |
| D2  | 방향 확인 배너 미구현 — PR-5로 이관                    | 대시보드에서 지표를 매일 보면서 확인이 자연스러움. 설정 단계에서는 과부하                                           |
| D3  | 수동 생성 폼 미구현 — AI 추천에서만 추가               | `data_source`, `data_params` 같은 기술적 필드를 사용자에게 노출하면 이탈률 급증. AI가 골라주고 사용자는 수락/거절만 |
| D4  | Optimistic update 미적용 — 단순 invalidate             | 1인 개발 유지보수 고려. 롤백 로직 복잡도 대비 UX 이득이 미미 (지표 목록 3~5개, 응답 < 300ms)                        |
| D5  | mutation hooks를 `indicatorMutations.ts`로 분리        | queries.ts에 query만, mutation 파일 분리가 유지보수 용이                                                            |
| D6  | PR-3 BottomSheet 재사용                                | 동일 컴포넌트. 의존성 추가 없음                                                                                     |
| D7  | auto-recommend 결과를 state에 보관, query cache 아님   | 추천은 일회성. cache에 넣으면 staleTime 관리 부담 + 불필요한 refetch                                                |
| D8  | ~~`indicator_type` 한글 라벨 매핑을 컴포넌트 내부 상수로~~ → `INDICATOR_LABELS` 공유 상수 추출 | ~~v1: 사용처가 PR-4/PR-5 뿐~~ → v2: PR-4 내 2곳(IndicatorSetupCard, RecommendCard)이므로 즉시 추출 |
| D9  | `?auto=true` 자동 추천은 useEffect로 1회만 실행        | StrictMode 이중 실행 방지: ref 플래그 사용                                                                          |
| D10 | **Route Group으로 Layout 분리** (v2 추가)              | thesis/layout.tsx가 모든 자식 라우트에 공유 헤더 적용 → new/, [thesisId]/* 풀스크린 페이지와 이중 헤더 충돌. `(list)` 그룹에만 공유 헤더 적용. |
| D11 | **Mock 모드에서 로컬 상태 관리** (v2 추가)             | `MOCK_INDICATORS` 상수 직접 참조 시 토글/삭제 UI 미반영. `useState(MOCK_INDICATORS)` 초기화로 해결. |
| D12 | **기존 지표로 addedNames 초기화** (v2 추가)            | 세션 추가만 추적 시 기존 지표와 동일 이름 추천 중복 추가 가능. 기존 indicators의 name으로 초기 Set 구성. |

---

## 1. 파일 목록 (총 14개)

### 신규 생성 (5개)

```
frontend/
├── components/thesis/indicators/
│   ├── IndicatorSetupCard.tsx       # [1] 저장된 지표 카드 (토글/삭제)
│   ├── RecommendCard.tsx            # [2] AI 추천 지표 카드 (추가 버튼 + 방향 뱃지)
│   └── AddIndicatorSheet.tsx        # [3] 지표 추가 바텀시트
├── lib/thesis/
│   └── indicatorMutations.ts        # [4] useMutation hooks (CRUD + 추천)
└── app/thesis/
    └── (list)/
        └── layout.tsx               # [10] 공유 헤더 Layout (기존 layout.tsx에서 분리)
```

### 기존 파일 수정 (7개)

```
frontend/
├── lib/thesis/
│   ├── types.ts                     # [5] ThesisIndicator 확장, RecommendedIndicator 등 신규 타입 + INDICATOR_LABELS 공유 상수
│   ├── api.ts                       # [6] autoRecommend URL 수정, addIndicator/removeIndicator/toggleIndicator 추가
│   ├── queries.ts                   # [7] QUERY_KEYS export (mutations에서 invalidate용)
│   └── mock.ts                      # [8] Mock 지표/추천 데이터
└── app/thesis/
    ├── layout.tsx                   # [11] Toaster만 남기고 공유 헤더 제거 (Route Group 분리)
    └── [thesisId]/
        └── indicators/page.tsx      # [9] 전면 교체
```

### 파일 이동 (2개, Route Group 분리)

```
frontend/app/thesis/
├── page.tsx        → (list)/page.tsx        # 목록 페이지 이동
└── alerts/         → (list)/alerts/         # 알림 페이지 이동
```

> **URL 변경 없음**: Next.js Route Group `(list)`은 URL에 영향 없음.
> `/thesis` → `(list)/page.tsx`, `/thesis/alerts` → `(list)/alerts/page.tsx`

---

## 2. 각 파일 상세 명세

---

### [5] `lib/thesis/types.ts` — 수정

```ts
// ── 공유 라벨 상수 (v2: D8 → 컴포넌트 외부 추출) ──
export const TYPE_LABELS: Record<string, string> = {
	market_data: '시장',
	macro: '매크로',
	sentiment: '심리',
	technical: '기술적',
	custom: '커스텀',
}

export const DIRECTION_LABELS: Record<string, { text: string; className: string }> = {
	positive: { text: '↑ 유리', className: 'text-blue-400 bg-blue-900/30' },
	negative: { text: '↑ 불리', className: 'text-orange-400 bg-orange-900/30' },
}

// ── 기존 ThesisIndicator 확장 ──
export interface ThesisIndicator {
	id: string;
	name: string;
	indicator_type: IndicatorType;
	support_direction: SupportDirection;
	current_arrow_degree: number; // 0 ~ 180 (프론트 alias, 백엔드: current_degree)
	current_label: string;
	current_color: string; // hex
	is_active: boolean;
	premise: string | null;
	// ── PR-4 추가 필드 ──
	data_source: string; // 'fmp' | 'fred' | 'news_sentiment' | 'manual' | 'custom'
	data_params: Record<string, string | number>;
	weight: number;
	is_paused: boolean;
	current_score: number | null;
	created_at: string; // ISO 8601
}

// ── 신규: AI 추천 결과 (아직 DB에 저장되지 않은 상태) ──
export interface RecommendedIndicator {
	name: string;
	data_source: string;
	data_params: Record<string, string | number>;
	indicator_type: string;
	support_direction: SupportDirection;
	reason: string;
}

// ── 신규: 지표 생성 요청 본문 ──
export interface IndicatorCreatePayload {
	name: string;
	indicator_type: string;
	data_source: string;
	data_params: Record<string, string | number>;
	support_direction: SupportDirection;
	weight?: number;
	premise?: string | null;
	is_ai_recommended?: boolean; // true면 'ai_suggestion_accepted' 이벤트 기록
}

// ── 신규: auto-recommend 응답 ──
export interface AutoRecommendResponse {
	indicators: RecommendedIndicator[];
	count: number;
}
```

**하위 호환**: `ThesisIndicator`에 필드 추가만 수행. 기존 PR-1 `IndicatorCard`는 추가 필드를 참조하지 않으므로 파손 없음.

**⚠️ 주의**: 백엔드 필드명은 `current_degree`이지만, 프론트에서 `current_arrow_degree`로 사용 중.

- PR-1 `ArrowIndicator`가 `degree` prop을 받음 → `indicator.current_arrow_degree` 전달.
- 백엔드 dashboard API에서 `arrow_degree`로 변환하는지 확인 필요.
- PR-4에서는 **기존 필드명 `current_arrow_degree` 유지**. 이름 변경은 PR-5 대시보드에서 일괄 처리.

---

### [6] `lib/thesis/api.ts` — 수정

```ts
import type {
  Thesis, ThesisAlert, ThesisIndicator,
  DashboardResponse, ConversationResponse,
  ConversationState, EntrySource,
  AutoRecommendResponse, IndicatorCreatePayload,
} from './types'

// ── 기존 autoRecommend 수정 ──
// 변경 1: URL: auto-recommend/ → auto/
// 변경 2: 반환 타입: ThesisIndicator[] → AutoRecommendResponse
// 변경 3: 요청 본문: {} → { premise_id?: string }
autoRecommend: (thesisId: string, premiseId?: string) =>
  POST<AutoRecommendResponse>(
    `/thesis/${thesisId}/indicators/auto/`,
    premiseId ? { premise_id: premiseId } : {},
  ),

// ── 신규: 지표 추가 ──
addIndicator: (thesisId: string, data: IndicatorCreatePayload) =>
  POST<ThesisIndicator>(`/thesis/${thesisId}/indicators/`, data),

// ── 신규: 지표 삭제 ──
removeIndicator: (thesisId: string, indicatorId: string) =>
  authAxios.delete(`/thesis/${thesisId}/indicators/${indicatorId}/`).then(() => undefined),

// ── 신규: 지표 활성/비활성 토글 ──
toggleIndicator: (thesisId: string, indicatorId: string, isActive: boolean) =>
  PATCH<ThesisIndicator>(
    `/thesis/${thesisId}/indicators/${indicatorId}/`,
    { is_active: isActive },
  ),
```

---

### [7] `lib/thesis/queries.ts` — 수정

```ts
// ── QUERY_KEYS를 export ──
// 기존: const QUERY_KEYS = { ... } (모듈 내부)
// 변경: export const QUERY_KEYS = { ... }
// 이유: indicatorMutations.ts에서 invalidateQueries 시 queryKey 참조 필요

export const QUERY_KEYS = {
	list: ["thesis", "list"] as const,
	detail: (id: string) => ["thesis", id] as const,
	dashboard: (id: string) => ["thesis", id, "dashboard"] as const,
	indicators: (id: string) => ["thesis", id, "indicators"] as const,
	alerts: (id?: string) => ["thesis", "alerts", id ?? "all"] as const,
	alertsCount: ["thesis", "alerts-count"] as const,
} as const;
```

---

### [4] `lib/thesis/indicatorMutations.ts` — 신규

```ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { thesisApi } from "./api";
import { QUERY_KEYS } from "./queries";
import type { IndicatorCreatePayload } from "./types";

export function useAddIndicator(thesisId: string) {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (data: IndicatorCreatePayload) =>
			thesisApi.addIndicator(thesisId, data),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: QUERY_KEYS.indicators(thesisId) });
		},
		onError: () => {
			toast.error("지표 추가에 실패했어요");
		},
	});
}

export function useRemoveIndicator(thesisId: string) {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (indicatorId: string) =>
			thesisApi.removeIndicator(thesisId, indicatorId),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: QUERY_KEYS.indicators(thesisId) });
		},
		onError: () => {
			toast.error("지표 삭제에 실패했어요");
		},
	});
}

export function useToggleIndicator(thesisId: string) {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({
			indicatorId,
			isActive,
		}: {
			indicatorId: string;
			isActive: boolean;
		}) => thesisApi.toggleIndicator(thesisId, indicatorId, isActive),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: QUERY_KEYS.indicators(thesisId) });
		},
		onError: () => {
			toast.error("변경에 실패했어요");
		},
	});
}
```

**설계 포인트**:

- `invalidateQueries`: 성공 시 지표 목록 재조회. optimistic update 대신 단순 재조회 (D4).
- `toast.error`: 실패 시 사용자 알림. layout.tsx의 `<Toaster />` 활용 (PR-3).
- auto-recommend는 mutation hook 없이 page.tsx에서 직접 `thesisApi.autoRecommend` 호출 → state에 보관 (D7).

---

### [8] `lib/thesis/mock.ts` — 수정

기존 Mock 유지. 지표 설정용 Mock 데이터 추가.

```ts
import type { ThesisIndicator, RecommendedIndicator } from "./types";

// ── Mock 저장된 지표 ──
export const MOCK_INDICATORS: ThesisIndicator[] = [
	{
		id: "ind-1",
		name: "외국인 순매수 추이",
		indicator_type: "market_data",
		data_source: "fmp",
		data_params: { metric: "foreign_net_buy" },
		support_direction: "positive",
		weight: 1.0,
		is_active: true,
		is_paused: false,
		current_arrow_degree: 35,
		current_label: "지지하는 편",
		current_color: "#60A5FA",
		current_score: 0.65,
		premise: null,
		created_at: "2026-03-13T10:00:00Z",
	},
	{
		id: "ind-2",
		name: "원/달러 환율",
		indicator_type: "macro",
		data_source: "fmp",
		data_params: { symbol: "USDKRW" },
		support_direction: "negative",
		weight: 1.0,
		is_active: true,
		is_paused: false,
		current_arrow_degree: 110,
		current_label: "약화하는 편",
		current_color: "#FB923C",
		current_score: -0.3,
		premise: null,
		created_at: "2026-03-13T10:00:00Z",
	},
	{
		id: "ind-3",
		name: "VIX (공포지수)",
		indicator_type: "macro",
		data_source: "fmp",
		data_params: { symbol: "^VIX" },
		support_direction: "negative",
		weight: 1.0,
		is_active: false,
		is_paused: false,
		current_arrow_degree: 90,
		current_label: "중립",
		current_color: "#D1D5DB",
		current_score: 0,
		premise: null,
		created_at: "2026-03-13T10:00:00Z",
	},
];

// ── Mock AI 추천 결과 ──
export const MOCK_RECOMMENDATIONS: RecommendedIndicator[] = [
	{
		name: "KOSPI 지수",
		data_source: "fmp",
		data_params: { symbol: "^KS11" },
		indicator_type: "market_data",
		support_direction: "positive",
		reason: "KOSPI 지수는 한국 시장 전체의 방향을 보여주는 대표 지표입니다.",
	},
	{
		name: "미국 기준금리 (Fed Funds Rate)",
		data_source: "fred",
		data_params: { series_id: "FEDFUNDS" },
		indicator_type: "macro",
		support_direction: "negative",
		reason: "기준금리 변동은 유동성과 할인율에 영향을 미칩니다.",
	},
	{
		name: "RSI (14일)",
		data_source: "fmp",
		data_params: { indicator: "RSI", period: 14 },
		indicator_type: "technical",
		support_direction: "positive",
		reason: "RSI는 단기 과매수/과매도 상태를 파악하는 기술적 지표입니다.",
	},
];
```

**설계 포인트**:

- 고정 데이터만 사용 (Date.now() 금지 — 버그 #24)
- `MOCK_INDICATORS`는 활성/비활성 혼합 (토글 테스트)
- `MOCK_RECOMMENDATIONS`는 기존 `MOCK_INDICATORS`와 겹치지 않는 지표 (중복 추가 테스트)
- Mock indicator에 `current_arrow_degree` 다양한 값 (35/110/90) → ArrowIndicator 색상 분기 검증

---

### [1] `components/thesis/indicators/IndicatorSetupCard.tsx` — 신규

저장된 지표를 보여주는 카드. 토글/삭제 기능 포함.

```tsx
"use client";

import { ArrowIndicator } from "@/components/thesis/common/ArrowIndicator";
import { Power, Trash2 } from "lucide-react";
import { TYPE_LABELS, DIRECTION_LABELS } from "@/lib/thesis/types";
import type { ThesisIndicator } from "@/lib/thesis/types";

interface Props {
	indicator: ThesisIndicator;
	onToggle: (indicatorId: string, isActive: boolean) => void;
	onRemove: (indicatorId: string) => void;
	isToggling?: boolean;
	isRemoving?: boolean;
}

export function IndicatorSetupCard({
	indicator,
	onToggle,
	onRemove,
	isToggling,
	isRemoving,
}: Props) {
	const typeLabel =
		TYPE_LABELS[indicator.indicator_type] ?? indicator.indicator_type;
	const dirLabel =
		DIRECTION_LABELS[indicator.support_direction] ?? DIRECTION_LABELS.positive;

	return (
		<div
			className={`bg-gray-900 border border-gray-700 rounded-xl p-4 transition-opacity
                     ${!indicator.is_active ? "opacity-50" : ""}`}>
			<div className='flex items-start gap-3'>
				{/* 화살표 */}
				<div className='flex-shrink-0 pt-0.5'>
					<ArrowIndicator
						degree={indicator.current_arrow_degree}
						size='sm'
					/>
				</div>

				{/* 내용 */}
				<div className='flex-1 min-w-0'>
					<p className='text-white text-sm font-medium truncate'>
						{indicator.name}
					</p>
					<div className='flex items-center gap-2 mt-1.5'>
						<span className='text-[10px] px-2 py-0.5 rounded-full text-gray-400 bg-gray-800'>
							{typeLabel}
						</span>
						<span
							className={`text-[10px] px-2 py-0.5 rounded-full ${dirLabel.className}`}>
							{dirLabel.text}
						</span>
						<span className='text-[10px] text-gray-600'>
							{indicator.data_source}
						</span>
					</div>
				</div>

				{/* 액션 버튼 */}
				<div className='flex items-center gap-1 flex-shrink-0'>
					<button
						onClick={() => onToggle(indicator.id, !indicator.is_active)}
						disabled={isToggling}
						className={`p-2 rounded-lg transition-colors
                       ${
													indicator.is_active
														? "text-blue-400 hover:bg-blue-900/30"
														: "text-gray-600 hover:bg-gray-800"
												}`}
						aria-label={indicator.is_active ? "비활성화" : "활성화"}>
						<Power size={16} />
					</button>
					<button
						onClick={() => onRemove(indicator.id)}
						disabled={isRemoving}
						className='p-2 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-900/20
                       transition-colors'
						aria-label='지표 삭제'>
						<Trash2 size={16} />
					</button>
				</div>
			</div>

			{/* 현재 라벨 */}
			{indicator.is_active && indicator.current_label && (
				<p className='text-[11px] text-gray-500 mt-2 ml-8'>
					현재: {indicator.current_label}
				</p>
			)}
		</div>
	);
}
```

**설계 포인트**:

- `ArrowIndicator` 재사용 (PR-1): degree → 색상/방향 자동 매핑
- `is_active=false`일 때 `opacity-50`으로 시각적 비활성화
- `TYPE_LABELS`, `DIRECTION_LABELS`: `types.ts` 공유 상수 import (v2: D8 수정)
  - "positive"는 "값이 오르면 가설에 유리" → "↑ 유리"
  - "negative"는 "값이 오르면 가설에 불리" → "↑ 불리"
- `isToggling`, `isRemoving`: mutation 진행 중 버튼 비활성화
- `truncate`: 긴 지표명 말줄임
- `min-h` 미지정: 내용에 따라 자연스럽게 높이 결정
- 삭제 확인 모달 없음 (D3: 단순함 우선. 실수 시 다시 추가)

---

### [2] `components/thesis/indicators/RecommendCard.tsx` — 신규

AI가 추천한 (아직 저장되지 않은) 지표 카드. "추가" 버튼 포함.

```tsx
"use client";

import { Plus, Check, Sparkles } from "lucide-react";
import { TYPE_LABELS, DIRECTION_LABELS } from "@/lib/thesis/types";
import type { RecommendedIndicator } from "@/lib/thesis/types";

interface Props {
	indicator: RecommendedIndicator;
	onAdd: () => void;
	added: boolean;
	isAdding?: boolean;
}

export function RecommendCard({ indicator, onAdd, added, isAdding }: Props) {
	const typeLabel =
		TYPE_LABELS[indicator.indicator_type] ?? indicator.indicator_type;
	const dirLabel =
		DIRECTION_LABELS[indicator.support_direction] ?? DIRECTION_LABELS.positive;

	return (
		<div className='bg-gray-900 border border-gray-700 rounded-xl p-4'>
			<div className='flex items-start gap-3'>
				{/* AI 마크 */}
				<div className='flex-shrink-0 pt-0.5'>
					<Sparkles
						size={16}
						className='text-purple-400'
					/>
				</div>

				{/* 내용 */}
				<div className='flex-1 min-w-0'>
					<p className='text-white text-sm font-medium'>{indicator.name}</p>
					<div className='flex items-center gap-2 mt-1'>
						<span className='text-[10px] px-2 py-0.5 rounded-full text-gray-400 bg-gray-800'>
							{typeLabel}
						</span>
						{/* v2: 방향 뱃지 추가 */}
						<span
							className={`text-[10px] px-2 py-0.5 rounded-full ${dirLabel.className}`}>
							{dirLabel.text}
						</span>
						<span className='text-[10px] text-gray-600'>
							{indicator.data_source}
						</span>
					</div>
					<p className='text-xs text-gray-500 mt-2 leading-relaxed'>
						{indicator.reason}
					</p>
				</div>

				{/* 추가 버튼 */}
				<button
					onClick={onAdd}
					disabled={added || isAdding}
					className={`flex-shrink-0 p-2.5 rounded-xl transition-all
                     ${
												added
													? "bg-green-900/30 text-green-400"
													: isAdding
														? "bg-gray-800 text-gray-600"
														: "bg-blue-600 text-white active:scale-[0.95]"
											}`}
					aria-label={added ? "추가됨" : "지표 추가"}>
					{added ? <Check size={16} /> : <Plus size={16} />}
				</button>
			</div>
		</div>
	);
}
```

**설계 포인트**:

- `Sparkles` 아이콘: AI 추천 시각적 구분
- `reason` 텍스트: 사용자가 왜 이 지표인지 이해할 수 있도록
- `DIRECTION_LABELS` 뱃지 (v2): 추가 전 방향(positive/negative) 확인 가능
- `added=true`: 체크 아이콘 + 녹색 배경 (재클릭 방지)
- `isAdding`: mutation 진행 중 비활성화

---

### [3] `components/thesis/indicators/AddIndicatorSheet.tsx` — 신규

바텀시트 안에서 AI 추천 목록을 표시. BottomSheet (PR-3) 재사용.

```tsx
"use client";

import { BottomSheet } from "@/components/thesis/builder/BottomSheet";
import { RecommendCard } from "./RecommendCard";
import type { RecommendedIndicator } from "@/lib/thesis/types";

interface Props {
	isOpen: boolean;
	onClose: () => void;
	recommendations: RecommendedIndicator[];
	isLoading: boolean;
	addedNames: Set<string>;
	onAdd: (rec: RecommendedIndicator) => void;
	onAddAll: () => void;
	addingName: string | null;
}

export function AddIndicatorSheet({
	isOpen,
	onClose,
	recommendations,
	isLoading,
	addedNames,
	onAdd,
	onAddAll,
	addingName,
}: Props) {
	const allAdded =
		recommendations.length > 0 &&
		recommendations.every((r) => addedNames.has(r.name));

	return (
		<BottomSheet
			isOpen={isOpen}
			onClose={onClose}
			title='AI 추천 지표'>
			{isLoading ? (
				<div className='flex flex-col items-center gap-3 py-8'>
					<div className='flex gap-1.5'>
						<span className='w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:0ms]' />
						<span className='w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:200ms]' />
						<span className='w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:400ms]' />
					</div>
					<p className='text-sm text-gray-400'>AI가 지표를 고르는 중...</p>
				</div>
			) : recommendations.length === 0 ? (
				<div className='text-center py-8'>
					<p className='text-sm text-gray-400'>추천할 지표가 없어요.</p>
					<p className='text-xs text-gray-600 mt-1'>
						전제를 수정하면 더 나은 추천을 받을 수 있어요.
					</p>
				</div>
			) : (
				{/* v2: semantic HTML — ul/li */}
				<ul className='space-y-3 list-none'>
					{recommendations.map((rec) => (
						<li key={rec.name}>
							<RecommendCard
								indicator={rec}
								onAdd={() => onAdd(rec)}
								added={addedNames.has(rec.name)}
								isAdding={addingName === rec.name}
							/>
						</li>
					))}

					{/* 전체 추가 버튼 */}
					{!allAdded && (
						<button
							onClick={onAddAll}
							className='w-full py-3 border border-blue-600 text-blue-400 text-sm
                         rounded-xl active:scale-[0.98] transition-transform mt-2'>
							전체 추가 (
							{recommendations.filter((r) => !addedNames.has(r.name)).length}개)
						</button>
					)}

					{allAdded && (
						<button
							onClick={onClose}
							className='w-full py-3 bg-blue-600 text-white text-sm font-medium
                         rounded-xl active:scale-[0.98] transition-transform mt-2'>
							완료
						</button>
					)}
				</div>
			)}
		</BottomSheet>
	);
}
```

**설계 포인트**:

- `BottomSheet` 래핑 (PR-3): ESC, 오버레이 닫기 자동 지원
- 로딩 상태: purple dots (AI 느낌) + "AI가 지표를 고르는 중..."
- 빈 결과: 안내 메시지 + 전제 수정 권유
- `전체 추가`: 아직 추가하지 않은 추천만 카운트
- `allAdded`: 전부 추가됨 → "완료" 버튼으로 전환
- `addingName`: 현재 추가 중인 지표명으로 로딩 표시 (동시 다중 추가 방지)

---

### [9] `app/thesis/[thesisId]/indicators/page.tsx` — 전면 교체

이 파일이 PR-4의 핵심. `?auto=true` 자동 추천 플로우 + 수동 관리.

```tsx
"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft, Plus, Sparkles } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { thesisApi } from "@/lib/thesis/api";
import { useThesis, useIndicators } from "@/lib/thesis/queries";
import {
	useAddIndicator,
	useRemoveIndicator,
	useToggleIndicator,
} from "@/lib/thesis/indicatorMutations";
import {
	USE_MOCK,
	MOCK_INDICATORS,
	MOCK_RECOMMENDATIONS,
} from "@/lib/thesis/mock";
import type {
	RecommendedIndicator,
	IndicatorCreatePayload,
} from "@/lib/thesis/types";
import { IndicatorSetupCard } from "@/components/thesis/indicators/IndicatorSetupCard";
import { AddIndicatorSheet } from "@/components/thesis/indicators/AddIndicatorSheet";

export default function ThesisIndicatorsPage() {
	return (
		<Suspense fallback={<IndicatorsLoading />}>
			<IndicatorsContent />
		</Suspense>
	);
}

function IndicatorsLoading() {
	return (
		<div className='flex flex-col h-[calc(100dvh-env(safe-area-inset-top))] bg-gray-950'>
			<div className='flex items-center gap-3 px-4 py-3 border-b border-gray-800'>
				<div className='p-1 text-gray-400'>
					<ArrowLeft size={20} />
				</div>
				<h1 className='text-white text-base font-medium flex-1'>지표 설정</h1>
			</div>
			<div className='flex-1 flex items-center justify-center'>
				<div className='animate-pulse text-gray-600 text-sm'>
					불러오는 중...
				</div>
			</div>
		</div>
	);
}

function IndicatorsContent() {
	const params = useParams();
	const searchParams = useSearchParams();
	const router = useRouter();
	const thesisId = params.thesisId as string;
	const isAutoMode = searchParams.get("auto") === "true";

	// ── 데이터 조회 ──
	const { data: thesis } = useThesis(thesisId);
	const {
		data: indicators,
		isLoading: isLoadingIndicators,
		error: indicatorsError,
		refetch: refetchIndicators,
	} = useIndicators(thesisId);

	// ── Mutations ──
	const addMutation = useAddIndicator(thesisId);
	const removeMutation = useRemoveIndicator(thesisId);
	const toggleMutation = useToggleIndicator(thesisId);

	// ── Mock 로컬 상태 (v2: D11 — 토글/삭제 즉시 반영) ──
	const [mockIndicators, setMockIndicators] = useState(MOCK_INDICATORS);

	// ── AI 추천 상태 (query cache 아님) ──
	const [recommendations, setRecommendations] = useState<
		RecommendedIndicator[]
	>([]);
	const [isRecommending, setIsRecommending] = useState(false);
	const [addedNames, setAddedNames] = useState<Set<string>>(new Set());
	const [addingName, setAddingName] = useState<string | null>(null);
	const [sheetOpen, setSheetOpen] = useState(false);

	// ── v2: D12 — 기존 지표로 addedNames 초기화 (중복 추가 방지) ──
	const displayIndicators = USE_MOCK ? mockIndicators : (indicators ?? []);
	useEffect(() => {
		if (displayIndicators.length > 0) {
			setAddedNames(prev => {
				const next = new Set(prev);
				displayIndicators.forEach(ind => next.add(ind.name));
				return next;
			});
		}
	}, [displayIndicators.length]); // eslint-disable-line react-hooks/exhaustive-deps

	// ── ?auto=true: 마운트 시 자동 추천 (1회만, StrictMode 방지) ──
	const autoFetchedRef = useRef(false);
	useEffect(() => {
		if (isAutoMode && !autoFetchedRef.current) {
			autoFetchedRef.current = true;
			fetchRecommendations();
		}
	}, [isAutoMode]); // eslint-disable-line react-hooks/exhaustive-deps

	// ── AI 추천 호출 ──
	async function fetchRecommendations() {
		setIsRecommending(true);
		setSheetOpen(true);

		if (USE_MOCK) {
			setTimeout(() => {
				setRecommendations(MOCK_RECOMMENDATIONS);
				setIsRecommending(false);
			}, 1500);
			return;
		}

		try {
			const response = await thesisApi.autoRecommend(thesisId);
			setRecommendations(response.indicators);
		} catch {
			toast.error("AI 추천에 실패했어요");
			setRecommendations([]);
		} finally {
			setIsRecommending(false);
		}
	}

	// ── 추천 지표 추가 (개별) ──
	async function handleAddRecommended(rec: RecommendedIndicator) {
		if (addedNames.has(rec.name)) return;
		setAddingName(rec.name);

		const payload: IndicatorCreatePayload = {
			name: rec.name,
			indicator_type: rec.indicator_type,
			data_source: rec.data_source,
			data_params: rec.data_params,
			support_direction: rec.support_direction,
			is_ai_recommended: true,
		};

		if (USE_MOCK) {
			// Mock: 실제 API 호출 없이 UI만 업데이트
			setTimeout(() => {
				setAddedNames((prev) => new Set(prev).add(rec.name));
				setAddingName(null);
				toast.success(`${rec.name} 추가됨`);
			}, 300);
			return;
		}

		try {
			await addMutation.mutateAsync(payload);
			setAddedNames((prev) => new Set(prev).add(rec.name));
			toast.success(`${rec.name} 추가됨`);
		} catch {
			// onError in mutation handles toast
		} finally {
			setAddingName(null);
		}
	}

	// ── 추천 전체 추가 ──
	async function handleAddAll() {
		const remaining = recommendations.filter((r) => !addedNames.has(r.name));
		for (const rec of remaining) {
			await handleAddRecommended(rec);
		}
	}

	// ── 기존 지표 토글 (v2: D11 — Mock 로컬 상태 반영) ──
	function handleToggle(indicatorId: string, isActive: boolean) {
		if (USE_MOCK) {
			setMockIndicators(prev =>
				prev.map(ind =>
					ind.id === indicatorId ? { ...ind, is_active: isActive } : ind
				)
			);
			toast.success(isActive ? "지표 활성화됨" : "지표 비활성화됨");
			return;
		}
		toggleMutation.mutate({ indicatorId, isActive });
	}

	// ── 기존 지표 삭제 (v2: D11 — Mock 로컬 상태 반영) ──
	function handleRemove(indicatorId: string) {
		if (USE_MOCK) {
			setMockIndicators(prev => prev.filter(ind => ind.id !== indicatorId));
			toast.success("지표 삭제됨");
			return;
		}
		removeMutation.mutate(indicatorId);
	}

	// ── 네비게이션 ──
	function handleStartMonitoring() {
		if (USE_MOCK || !thesisId) {
			router.push("/thesis");
			return;
		}
		router.push(`/thesis/${thesisId}`);
	}

	// ── 표시할 지표 목록 (v2: 상단에서 정의 완료) ──
	// const displayIndicators는 이미 Mock/API 분기 + addedNames 초기화 위에서 선언됨

	return (
		<div className='flex flex-col h-[calc(100dvh-env(safe-area-inset-top))] bg-gray-950'>
			{/* 헤더 */}
			<div className='flex items-center gap-3 px-4 py-3 border-b border-gray-800'>
				<Link
					href='/thesis'
					className='p-1 text-gray-400 hover:text-white'>
					<ArrowLeft size={20} />
				</Link>
				<h1 className='text-white text-base font-medium flex-1'>지표 설정</h1>
			</div>

			{/* 메인 콘텐츠 */}
			<div className='flex-1 overflow-y-auto px-4 pt-4 pb-4'>
				{/* 가설 정보 */}
				{thesis && (
					<div className='mb-6'>
						<p className='text-gray-500 text-xs mb-1'>가설</p>
						<p className='text-white text-lg font-medium'>
							{thesis.title}
							<span className='ml-2 text-sm'>
								{thesis.direction === "bullish"
									? "📈"
									: thesis.direction === "bearish"
										? "📉"
										: "➡️"}
							</span>
						</p>
					</div>
				)}

				{/* 지표 목록 */}
				<div className='mb-4'>
					<div className='flex items-center justify-between mb-3'>
						<p className='text-gray-400 text-sm font-medium'>
							현재 지표 ({displayIndicators.length}개)
						</p>
					</div>

					{isLoadingIndicators && !USE_MOCK ? (
						<div className='space-y-3'>
							{[1, 2, 3].map((i) => (
								<div
									key={i}
									className='bg-gray-900 border border-gray-700 rounded-xl p-4 animate-pulse'>
									<div className='h-4 bg-gray-800 rounded w-2/3 mb-2' />
									<div className='h-3 bg-gray-800 rounded w-1/3' />
								</div>
							))}
						</div>
					) : indicatorsError && !USE_MOCK ? (
						<div className='text-center py-8'>
							<p className='text-gray-400 text-sm mb-3'>
								지표를 불러오지 못했어요
							</p>
							<button
								onClick={() => refetchIndicators()}
								className='text-blue-400 text-sm hover:underline'>
								다시 시도
							</button>
						</div>
					) : displayIndicators.length === 0 ? (
						<div className='text-center py-8 border border-dashed border-gray-700 rounded-xl'>
							<p className='text-gray-500 text-sm'>아직 지표가 없어요</p>
							<p className='text-gray-600 text-xs mt-1'>
								AI 추천으로 지표를 추가해보세요
							</p>
						</div>
					) : (
						{/* v2: semantic HTML — ul/li */}
						<ul className='space-y-3 list-none'>
							{displayIndicators.map((ind) => (
								<li key={ind.id}>
									<IndicatorSetupCard
										indicator={ind}
										onToggle={handleToggle}
										onRemove={handleRemove}
										isToggling={toggleMutation.isPending}
										isRemoving={removeMutation.isPending}
									/>
								</li>
							))}
						</ul>
					)}
				</div>

				{/* AI 추천 버튼 */}
				<button
					onClick={fetchRecommendations}
					disabled={isRecommending}
					className='w-full flex items-center justify-center gap-2 py-3.5
                     border border-dashed border-gray-600 rounded-xl
                     text-gray-300 text-sm hover:border-gray-500
                     transition-colors active:scale-[0.98]'>
					<Sparkles
						size={16}
						className='text-purple-400'
					/>
					AI 추천으로 추가
				</button>
			</div>

			{/* 하단 CTA */}
			<div className='flex-shrink-0 border-t border-gray-800 bg-gray-950 px-4 py-4 space-y-2'>
				<button
					onClick={handleStartMonitoring}
					disabled={displayIndicators.length === 0 && !USE_MOCK}
					className={`w-full py-4 text-sm font-medium rounded-xl
                     active:scale-[0.98] transition-transform
                     ${
												displayIndicators.length > 0 || USE_MOCK
													? "bg-blue-600 text-white"
													: "bg-gray-800 text-gray-600 cursor-not-allowed"
											}`}>
					관제 시작하기 →
				</button>
				<Link
					href='/thesis'
					className='block w-full py-2 text-gray-500 text-sm text-center'>
					돌아가기
				</Link>
			</div>

			{/* 추천 바텀시트 */}
			<AddIndicatorSheet
				isOpen={sheetOpen}
				onClose={() => setSheetOpen(false)}
				recommendations={recommendations}
				isLoading={isRecommending}
				addedNames={addedNames}
				onAdd={handleAddRecommended}
				onAddAll={handleAddAll}
				addingName={addingName}
			/>
		</div>
	);
}
```

**핵심 설계 포인트**:

1. **Suspense 래핑**: `useSearchParams`가 Suspense boundary 필요 (PR-3 빌드 에러 교훈).

2. **`?auto=true` 자동 추천 (D9)**: `useRef` 플래그로 StrictMode 이중 실행 방지. 마운트 즉시 `fetchRecommendations()` 호출 → 바텀시트 자동 열림.

3. **Mock 모드 분기 (v2 수정)**: `USE_MOCK`일 때 `useState(MOCK_INDICATORS)` 로컬 상태 사용. 토글/삭제가 `setMockIndicators`를 통해 즉시 UI 반영. 기존 "toast만 표시" 방식에서 실제 상태 변경으로 개선.

4. **서버 리소스 관리**:
   - 추천 결과를 `state`에 보관 (query cache 아님 — D7)
   - `useIndicators` staleTime 5분 유지 (기존 설정)
   - 폴링 없음 (설정 페이지는 사용자 주도)
   - `autoRecommend` 반복 호출 가능하지만, 이전 결과를 state에 유지하므로 불필요한 재호출 자연 방지

5. **에러 처리**: 목록 로딩 실패 → "다시 시도" 버튼. mutation 실패 → toast. 추천 실패 → toast + 빈 결과.

6. **네비게이션**: "관제 시작하기" → `/thesis/{id}` (대시보드, PR-5). 지표 0개면 비활성화.

---

### [11] `app/thesis/layout.tsx` — 수정 (v2: D10)

기존 공유 헤더를 제거하고 Toaster만 남김.

```tsx
import { Toaster } from 'sonner'

export default function ThesisLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-950 animate-fadeIn">
      {children}
      <Toaster position="bottom-center" theme="dark" />
    </div>
  )
}
```

**변경 내용**:

- `max-w-lg mx-auto px-4 pt-4 pb-20` 래퍼 제거
- 공유 헤더 (`가설 통제실` + ArrowLeft + AlertBell) 제거
- `<Toaster />`만 유지 (모든 하위 라우트에서 toast 사용)

---

### [10] `app/thesis/(list)/layout.tsx` — 신규 (v2: D10)

목록 페이지(`/thesis`, `/thesis/alerts`)에만 적용되는 공유 헤더 Layout.

```tsx
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { AlertBell } from '@/components/thesis/common/AlertBell'

export default function ThesisListLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-w-lg mx-auto px-4 pt-4 pb-20">
      <div className="sticky top-0 z-10 bg-gray-950/95 backdrop-blur-sm
                   flex items-center justify-between py-4 -mx-4 px-4 mb-2">
        <Link href="/" className="p-2 -ml-2 text-gray-400 hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-white text-lg font-bold">가설 통제실</h1>
        <AlertBell />
      </div>
      {children}
    </div>
  )
}
```

**설계 포인트**:

- 기존 `thesis/layout.tsx`의 공유 헤더를 그대로 이동
- Route Group `(list)`는 URL에 영향 없음: `/thesis` → `(list)/page.tsx`
- `new/`, `[thesisId]/` 등 풀스크린 페이지는 이 Layout 밖이므로 이중 헤더 없음
- **파일 이동 필요**: `app/thesis/page.tsx` → `app/thesis/(list)/page.tsx`, `app/thesis/alerts/` → `app/thesis/(list)/alerts/`

---

## 3. 의존성 그래프

```
lib/thesis/types.ts (수정: ThesisIndicator 확장, RecommendedIndicator, IndicatorCreatePayload, AutoRecommendResponse)
    │
    ├→ lib/thesis/api.ts (수정: autoRecommend URL/타입, addIndicator, removeIndicator, toggleIndicator)
    │
    ├→ lib/thesis/queries.ts (수정: QUERY_KEYS export)
    │
    ├→ lib/thesis/indicatorMutations.ts (신규: useAddIndicator, useRemoveIndicator, useToggleIndicator)
    │
    └→ lib/thesis/mock.ts (수정: MOCK_INDICATORS, MOCK_RECOMMENDATIONS)

components/thesis/common/ArrowIndicator.tsx (PR-1, 변경 없음)
    │
    └→ components/thesis/indicators/IndicatorSetupCard.tsx (신규)

components/thesis/builder/BottomSheet.tsx (PR-3, 변경 없음)
    │
    └→ components/thesis/indicators/AddIndicatorSheet.tsx (신규)
         │
         └→ components/thesis/indicators/RecommendCard.tsx (신규)

app/thesis/[thesisId]/indicators/page.tsx (전면 교체 — 모든 indicator 컴포넌트 + mutations + mock)
```

---

## 4. 구현 순서

```
Phase 0 (Layout 분리 — 최우선, v2 추가):
  ├─ app/thesis/layout.tsx: Toaster만 남기고 공유 헤더 제거
  ├─ mkdir app/thesis/(list)/
  ├─ app/thesis/(list)/layout.tsx: 공유 헤더 신규 생성
  ├─ mv app/thesis/page.tsx → app/thesis/(list)/page.tsx
  └─ mv app/thesis/alerts/ → app/thesis/(list)/alerts/

Phase A (독립, 병렬):
  ├─ lib/thesis/types.ts: ThesisIndicator 확장 + 3개 신규 타입 + TYPE_LABELS/DIRECTION_LABELS 공유 상수
  ├─ lib/thesis/queries.ts: QUERY_KEYS export
  └─ mkdir components/thesis/indicators/

Phase B (Phase A 의존, 병렬):
  ├─ lib/thesis/api.ts: autoRecommend 수정 + 3개 메서드 추가
  ├─ lib/thesis/indicatorMutations.ts: 3개 mutation hooks
  ├─ lib/thesis/mock.ts: MOCK_INDICATORS + MOCK_RECOMMENDATIONS
  ├─ components/thesis/indicators/IndicatorSetupCard.tsx (TYPE_LABELS/DIRECTION_LABELS import)
  ├─ components/thesis/indicators/RecommendCard.tsx (TYPE_LABELS/DIRECTION_LABELS import + 방향 뱃지)
  └─ components/thesis/indicators/AddIndicatorSheet.tsx (semantic ul/li)

Phase C (Phase B 의존):
  └─ app/thesis/[thesisId]/indicators/page.tsx 전면 교체
      · useState(MOCK_INDICATORS) 로컬 상태
      · addedNames 기존 지표 초기화
      · semantic ul/li

Phase D (Phase C 의존):
  └─ tsc --noEmit + npm run build 검증
```

---

## 5. 검증 체크리스트

### 5.1 빌드 검증

| 검증 항목            | 명령어                             | 기대 결과 |
| -------------------- | ---------------------------------- | --------- |
| TypeScript 타입 체크 | `tsc --noEmit`                     | 에러 0개  |
| Next.js 빌드         | `npm run build`                    | 성공      |
| 기존 기능 회귀       | `/thesis` 목록, `/thesis/new` 빌더 | 정상 동작 |
| Route Group 라우팅 (v2) | `/thesis`, `/thesis/alerts` URL 변경 없음 | 정상 동작 |
| Layout 이중 헤더 (v2) | `/thesis/new`, `/thesis/*/indicators` | 자체 헤더만 표시, 공유 헤더 없음 |

### 5.2 Mock 검증

| 시나리오                              | 기대 동작                                    |
| ------------------------------------- | -------------------------------------------- |
| `/thesis/mock-1/indicators`           | 지표 3개 (활성 2, 비활성 1) 표시             |
| `/thesis/mock-1/indicators?auto=true` | 마운트 시 바텀시트 자동 열림 + 추천 3개 표시 |
| 추천 지표 "추가" 클릭                 | 체크 아이콘 전환 + toast "... 추가됨"        |
| "전체 추가" 클릭                      | 미추가 항목 순차 추가 + 완료 버튼 전환       |
| 지표 카드 전원 아이콘 클릭            | toast + **카드 opacity 즉시 변경** (v2)      |
| 지표 카드 삭제 아이콘 클릭            | toast + **카드 즉시 제거** (v2)              |
| 기존 지표와 동일 이름 추천            | **이미 추가됨 표시 (체크 아이콘)** (v2)      |
| "관제 시작하기" 클릭                  | `/thesis`로 이동 (Mock 모드)                 |
| "AI 추천으로 추가" 버튼 클릭          | 바텀시트 열림 + 1.5초 로딩 후 추천 표시      |

### 5.3 UI 검증

| 시나리오                   | 기대 동작                                       |
| -------------------------- | ----------------------------------------------- |
| 비활성 지표 카드           | opacity-50                                      |
| ArrowIndicator 색상        | degree 35→파랑, 110→주황, 90→회색               |
| support_direction 뱃지 (카드) | positive→"↑ 유리" 파랑, negative→"↑ 불리" 주황  |
| support_direction 뱃지 (추천, v2) | RecommendCard에도 동일 뱃지 표시          |
| 지표 0개                   | 점선 빈 상태 + "아직 지표가 없어요"             |
| 지표 0개 + "관제 시작하기" | 비활성화 (cursor-not-allowed)                   |
| 바텀시트 로딩              | 보라색 bounce dots + "AI가 지표를 고르는 중..." |
| 바텀시트 추천 0개          | "추천할 지표가 없어요"                          |
| ESC 키 / 오버레이 클릭     | 바텀시트 닫힘                                   |
| Semantic HTML (v2)         | 지표 목록/추천 목록이 `ul > li` 구조            |

### 5.4 접근성 검증

| 항목      | 기대                              |
| --------- | --------------------------------- |
| 전원 버튼 | aria-label="비활성화" / "활성화"  |
| 삭제 버튼 | aria-label="지표 삭제"            |
| 추가 버튼 | aria-label="지표 추가" / "추가됨" |
| 다크 테마 | bg-white, text-black 0개          |

---

## 6. 에러 처리 매트릭스

| #   | 시나리오            | 처리 방식                        | 사용자 메시지              |
| --- | ------------------- | -------------------------------- | -------------------------- |
| E1  | 지표 목록 로딩 실패 | 인라인 에러 + "다시 시도" 버튼   | "지표를 불러오지 못했어요" |
| E2  | 지표 추가 실패      | `toast.error` (mutation onError) | "지표 추가에 실패했어요"   |
| E3  | 지표 삭제 실패      | `toast.error` (mutation onError) | "지표 삭제에 실패했어요"   |
| E4  | 지표 토글 실패      | `toast.error` (mutation onError) | "변경에 실패했어요"        |
| E5  | AI 추천 실패        | `toast.error` + 빈 결과          | "AI 추천에 실패했어요"     |
| E6  | 가설 404            | `useThesis` error → 빈 상태 표시 | (제목 미표시)              |

---

## 7. 서버 리소스 관리

| 항목                      | 전략                       | 이유                                                                                  |
| ------------------------- | -------------------------- | ------------------------------------------------------------------------------------- |
| `useIndicators` staleTime | 기존 5분 유지              | 지표 목록은 자주 변경되지 않음                                                        |
| auto-recommend 결과       | `useState`에 보관          | 일회성. cache staleTime 관리 부담 제거                                                |
| Mutation 후               | `invalidateQueries` 1회    | optimistic 대신 단순 재조회. 복잡도 ↓                                                 |
| `useThesis`               | 기존 hook 재사용           | 추가 API 호출 없음                                                                    |
| 폴링                      | 없음                       | 설정 페이지는 사용자 주도                                                             |
| Gemini 호출               | 프론트에서 결과 state 유지 | 반복 호출 최소화 (버튼 재클릭 시 기존 결과 표시 대신 재호출 허용하되 자연스럽게 억제) |

---

## 8. 리스크 및 완화

| #   | 리스크                                                   | 심각도 | 완화                                                           |
| --- | -------------------------------------------------------- | ------ | -------------------------------------------------------------- |
| 1   | auto-recommend Gemini 지연 (2~5초)                       | 중     | purple dots 로딩 + "AI가 지표를 고르는 중..."                  |
| 2   | 추천 결과 0개                                            | 낮     | 안내 메시지 + 전제 수정 권유                                   |
| 3   | 동일 지표 중복 추가                                      | ~~낮~~ 해결 | v2: `addedNames`를 기존 지표 이름으로 초기화 (D12). 세션+기존 모두 추적 |
| 4   | Mock 모드에서 mutation 미동작                            | ~~낮~~ 해결 | v2: `useState(MOCK_INDICATORS)` 로컬 상태로 토글/삭제 즉시 반영 (D11) |
| 5   | `current_arrow_degree` vs `current_degree` 필드명 불일치 | 중     | PR-4에서 기존 이름 유지. PR-5 대시보드에서 일괄 정리           |
| 6   | `autoRecommend` URL 기존 코드 사용처                     | 낮     | PR-1~3에서 `autoRecommend` 호출 없음. 첫 사용처가 이 PR        |
| 7   | `handleAddAll` 순차 실행 시 N번 invalidate               | 낮     | 지표 3~5개. 총 RTT < 2초. 배치 API 없으므로 순차가 유일한 방법 |
| 8   | StrictMode에서 auto 추천 이중 실행                       | 중     | `useRef` 플래그 (`autoFetchedRef`)                             |
| 9   | Route Group 분리 시 기존 라우팅 파손 (v2 추가)           | 중     | Phase 0에서 먼저 처리 + build 검증. URL 변경 없음 확인         |

---

## 9. 기술 부채

| 부채                                 | 영향                        | 해소 시점                          |
| ------------------------------------ | --------------------------- | ---------------------------------- |
| 수동 지표 생성 폼 없음               | AI 추천에만 의존            | Phase 2 (고급 사용자 요구 시)      |
| 방향 확인 배너 미구현                | support_direction 오류 가능 | PR-5 대시보드에서 구현             |
| 전제별 그룹핑 없음                   | 플랫 리스트만 표시          | PR-5 대시보드에서 premise별 그룹핑 |
| 삭제 확인 모달 없음                  | 실수 삭제 가능              | Phase 2 (undo toast 또는 confirm)  |
| `current_arrow_degree` 필드명 불일치 | 백엔드와 네이밍 불일치      | PR-5에서 일괄 정리                 |
| `handleAddAll` 순차 실행             | N번 invalidate 비효율       | 백엔드 batch API 추가 시           |
| 지표 재정렬(reorder) 미구현          | 표시 순서 변경 불가         | Phase 2 (드래그 앤 드롭)           |
| `is_paused` vs `is_active` 미분리 (v2 추가) | 백엔드에 `is_active`(사용자 토글)과 `is_paused`(시스템/데이터소스 일시정지)가 별도 존재. PR-4는 `is_active`만 UI 노출. `is_paused=true`일 때 "데이터 수집 중단" 표시 필요 | PR-5 대시보드에서 `is_paused` 상태 배지 추가 |

---

## 10. 후속 PR 연결

| 이 PR에서 만든 것        | 사용하는 PR                               |
| ------------------------ | ----------------------------------------- |
| `IndicatorSetupCard`     | PR-5 대시보드에서 읽기 전용 모드로 재사용 |
| `RecommendCard`          | PR-5에서 "지표 더 추가" 시 재사용         |
| `AddIndicatorSheet`      | PR-5에서 대시보드 내 지표 추가 시 재사용  |
| `indicatorMutations.ts`  | PR-5 대시보드에서 토글/삭제 시 재사용     |
| `QUERY_KEYS` export      | PR-5/PR-6에서 invalidate 시 사용          |
| `autoRecommend` URL 수정 | 이후 모든 추천 호출에 정확한 엔드포인트   |
| `ThesisIndicator` 확장   | PR-5에서 data_source/data_params 표시     |

---

## 11. Claude Code 실행 프롬프트

```
FE-PR-4 구현 계획서(docs/thesis_control/thesis_control_phase1_frontend_FE_PR_4.md) v2를 읽고,
Thesis Control 지표 설정 페이지를 구현해줘.

─────────────────────────────────────────────
[구현 순서]
─────────────────────────────────────────────

0단계: Layout Route Group 분리 (P0, 최우선)
  - app/thesis/layout.tsx: Toaster만 남기고 공유 헤더 제거
  - app/thesis/(list)/layout.tsx: 공유 헤더 신규 생성
  - app/thesis/page.tsx → app/thesis/(list)/page.tsx 이동
  - app/thesis/alerts/ → app/thesis/(list)/alerts/ 이동
  - URL 변경 없음 확인 (Route Group은 URL에 영향 없음)

1단계: 타입 + API + queries 수정
  - lib/thesis/types.ts:
    · ThesisIndicator 확장 (data_source, data_params, weight, is_paused, current_score, created_at)
    · RecommendedIndicator, IndicatorCreatePayload, AutoRecommendResponse 신규 타입
    · TYPE_LABELS, DIRECTION_LABELS 공유 상수 추가
  - lib/thesis/api.ts: autoRecommend URL/시그니처 수정 (auto-recommend/ → auto/), addIndicator, removeIndicator, toggleIndicator 추가
  - lib/thesis/queries.ts: QUERY_KEYS를 export로 변경

2단계: Mutation hooks + Mock 데이터
  - lib/thesis/indicatorMutations.ts: useAddIndicator, useRemoveIndicator, useToggleIndicator
  - lib/thesis/mock.ts: MOCK_INDICATORS (3개), MOCK_RECOMMENDATIONS (3개)

3단계: 컴포넌트 (3개, 병렬 생성)
  - components/thesis/indicators/IndicatorSetupCard.tsx (ArrowIndicator 재사용 + 토글/삭제, TYPE_LABELS/DIRECTION_LABELS import)
  - components/thesis/indicators/RecommendCard.tsx (AI 추천 카드 + 추가 버튼 + 방향 뱃지, TYPE_LABELS/DIRECTION_LABELS import)
  - components/thesis/indicators/AddIndicatorSheet.tsx (BottomSheet 래핑 + 추천 목록, semantic ul/li)

4단계: 페이지 교체
  - app/thesis/[thesisId]/indicators/page.tsx 전면 교체
    · Suspense 래핑 (useSearchParams)
    · ?auto=true: 자동 추천 (useRef 플래그로 StrictMode 방지)
    · Mock 모드: useState(MOCK_INDICATORS) 로컬 상태 (토글/삭제 즉시 반영)
    · addedNames 기존 지표로 초기화 (중복 추가 방지)
    · useThesis + useIndicators + 3개 mutations
    · IndicatorSetupCard + AddIndicatorSheet 조합
    · 지표/추천 목록 semantic ul/li
    · 하단 CTA: "관제 시작하기" + "돌아가기"

─────────────────────────────────────────────
[핵심 주의사항]
─────────────────────────────────────────────
- 다크 테마 전용. bg-white, text-black 사용 금지.
- autoRecommend URL: `/thesis/${id}/indicators/auto/` (auto-recommend 아님).
- autoRecommend 응답: `{ indicators: [...], count: N }` (ThesisIndicator[] 아님).
- AI 추천 지표 추가 시 `is_ai_recommended: true` 포함 (백엔드 이벤트 기록).
- auto-recommend 결과는 state에 보관 (query cache 아님).
- Mock 데이터에 Date.now() 사용 금지 (버그 #24).
- Mock 모드: useState(MOCK_INDICATORS)로 초기화 → 토글/삭제가 로컬 상태 반영 (D11).
- addedNames: 기존 indicators의 name으로 초기 Set 구성 → 중복 추가 방지 (D12).
- `?auto=true` 자동 추천은 useRef 플래그로 1회만 실행 (StrictMode 방지).
- QUERY_KEYS를 export해야 indicatorMutations에서 import 가능.
- Suspense boundary 필수 (useSearchParams — PR-3 빌드 에러 교훈).
- `current_arrow_degree` 필드명 유지 (백엔드 current_degree와 불일치이나 PR-5에서 정리).
- TYPE_LABELS, DIRECTION_LABELS는 types.ts에서 import (컴포넌트 내 중복 정의 금지).
- RecommendCard에 방향 뱃지 포함 (사용자가 추가 전 direction 확인 가능).
- 지표 목록과 추천 목록에 semantic HTML (ul/li) 사용.
- Layout Route Group 분리 후 기존 라우팅 파손 없는지 build 검증 필수.
- 구현 후 tsc --noEmit + npm run build 검증 필수.
```
