# Thesis Control Phase 3: 대시보드 리디자인 — 구현 계획서

> 버전: 1.0 FINAL
> 작성일: 2026-03-18
> 용도: Claude Code 구현 참고 문서
> 원칙: 내부 점수 숨기고 실제 값 보여주기 / 수학이 핵심, LLM은 보조 / 1인 개발자 유지보수 최적화

---

## 0. 배경 및 핵심 결정사항

### 0.1 왜 리디자인하는가

Phase 2까지 구현된 대시보드가 달 위상(MoonPhase), 화살표 각도(0-180°), 내부 점수(-1~1) 같은 추상적 시각화에 의존하고 있다. 사용자가 매일 아는 숫자(환율 1,380원, VIX 18.5pt)가 아니라 앱 내부 계산값을 보여주고 있어서 매일 비슷한 화면이 되고, 투자 의사결정에 실질적 도움이 안 됨.

### 0.2 핵심 원칙

1. **UI에 보이는 모든 숫자 = 사용자가 아는 실세계 값** (환율, 지수, 금리 등)
2. **내부 점수(score, degree) = AI 추천 알고리즘 전용**, UI에서 완전히 숨김
3. **차트 기본 숨김**, 토글 버튼으로 표시 (모바일 퍼포먼스 고려)
4. **기존 수학 엔진(Stage 0-3) 변경 없음** — UI 레이어만 교체

### 0.3 리뷰에서 확정된 변경사항 (원안 대비)

| #   | 원안                                             | 변경                                                     | 이유                                     |
| --- | ------------------------------------------------ | -------------------------------------------------------- | ---------------------------------------- |
| 1   | `_infer_unit()` 하드코딩                         | `ThesisIndicator.display_unit` 모델 필드 추가 + fallback | 지표 증가 시 함수 수정 제거              |
| 2   | `CombinedNormalizedChart` (정규화 점수 오버레이) | **삭제** — 미니차트만 유지                               | "내부 점수 숨기기" 원칙 충돌 + 공수 절감 |
| 3   | Zustand 스토어 (chartVisible, chartPeriod)       | **useState로 대체**                                      | 2개 상태에 전역 스토어 과잉              |
| 4   | `dashboardV2()` / `useDashboardV2()` 별도 메서드 | **기존 메서드 타입 업그레이드**                          | V1/V2 혼란 방지                          |
| 5   | `NotableChange` 내부 점수 기반                   | **실제 값 + alert 이벤트 기반으로 재정의**               | 원칙 일관성                              |
| 6   | `ai_summary` 백엔드 파이프라인 PR-7~8에 포함     | **PR-8은 mock 전용, 실제 파이프라인은 PR-10(별도)**      | scope 분리                               |

---

## 1. 확정된 대시보드 구조

```
┌─────────────────────────────────┐
│ ← 관제실            RefreshCw  │  DashboardPageHeader (유지)
├─────────────────────────────────┤
│ 가설 제목 + 배지 + N일째 관제  │  DashboardHeader (유지)
├─────────────────────────────────┤
│ 🤖 AI 분석                     │  AISummarySection (NEW)
│ "지난 7일간 NVIDIA 주가는..."  │  ※ PR-8은 mock, 실제 생성은 PR-10
├─────────────────────────────────┤
│ ⚡ 오늘의 변화 (2건)            │  NotableChangesSection (NEW)
│ • 외국인 순매수 추이  급변 ↑   │  alert_engine 이벤트 재활용
│ • 원/달러 환율       변화 ↓   │
├─────────────────────────────────┤
│ 지표 (3개)          ⚙️  설정    │
│ ┌──────────┐ ┌──────────┐      │
│ │외국인순매수│ │원/달러환율│      │  RealValueIndicatorCard (NEW)
│ │ 1.2조원   │ │ 1,380원  │      │
│ │ +22.4%    │ │ +1.1%    │      │
│ │ 지지      │ │ 반박     │      │
│ └──────────┘ └──────────┘      │
│ ┌──────────┐                   │
│ │VIX       │                   │
│ │ 18.5pt   │                   │
│ │ +1.6%    │                   │
│ │ 중립     │                   │
│ └──────────┘                   │
├─────────────────────────────────┤
│       [📊 차트 보기]            │  ChartToggleButton (NEW)
├─────────────────────────────────┤  ← 토글 시 아래 표시
│ [7D] [14D] [30D]               │  PeriodSelector (NEW)
│                                │
│ ── 외국인 순매수 추이 (원) ──  │  IndividualMiniCharts (NEW)
│ ┌───────────────────────────┐  │  지표별 독립 미니차트
│ │ Y: 실제 단위 (자동 스케일)│  │  raw_value 시계열
│ └───────────────────────────┘  │
│ ── 원/달러 환율 (원) ────────  │
│ ┌───────────────────────────┐  │
│ │                           │  │
│ └───────────────────────────┘  │
├─────────────────────────────────┤
│       [가설 마감하기]           │  Footer (유지)
└─────────────────────────────────┘
```

**원안 대비 제거된 것:**

- `OverallMoon` (달 위상) → 삭제
- `CombinedNormalizedChart` (정규화 오버레이) → 삭제 (원칙 충돌)
- Zustand `dashboardStore.ts` → `useState`로 대체

---

## 2. 삭제/대체 대상

| 기존 컴포넌트                   | 처리                                                    |
| ------------------------------- | ------------------------------------------------------- |
| `OverallMoon.tsx`               | 삭제 (달 위상 제거)                                     |
| `DashboardIndicatorCard.tsx`    | → `RealValueIndicatorCard.tsx`로 대체                   |
| `RecentChange.tsx`              | → `NotableChangesSection.tsx`로 대체                    |
| `MoonPhase.tsx` (common)        | 다른 곳에서도 미사용이면 삭제 — **import 검색 후 결정** |
| `scoreToPhaseMeta()` (utils.ts) | 삭제 (OverallMoon 전용)                                 |

**유지:**

- `DashboardPageHeader` — 그대로 유지
- `DashboardHeader` — 그대로 유지 (ThesisBadge + scoreToBadgeState 사용)
- `ThesisBadge` (common) — 유지
- `scoreToBadgeState()` (utils.ts) — 유지
- `sanitizeHexColor()` (utils.ts) — 유지
- `TREND_CONFIG` (constants.ts) — NotableChangesSection에서 방향 아이콘 재사용

---

## 3. PR 구성 (3+1개)

```
PR-7 (백엔드) ← 즉시 시작
    │
PR-8 (카드+AI분석) ← PR-7 이후 (타입이 백엔드 응답에 의존)
    │                  ※ Mock 모드로 병렬 개발 가능
PR-9 (차트+정리) ← PR-8 이후
    │
PR-10 (AI 파이프라인) ← 별도 독립 (Celery task + LLM 호출)
```

**Note:** PR-8은 Mock 모드로 PR-7 없이도 개발 가능. 순서는 논리적 의존이지 절대적 블로커는 아님.

---

## 4. PR-7: 백엔드 확장 (~80줄)

### 4-1. ThesisIndicator 모델 변경 (thesis/models/indicator.py)

```python
# 신규 필드 추가
display_unit = models.CharField(
    max_length=10, default='',
    help_text="UI 표시 단위: '$', '원', '%', 'pt', '' 등. 지표 생성 시 설정."
)
```

- 마이그레이션 생성 필요: `python manage.py makemigrations thesis`
- 기존 지표에 대한 데이터 마이그레이션: `_infer_unit()` 결과로 일괄 세팅

### 4-2. DashboardView 확장 (thesis/views/monitoring_views.py)

indicator 루프 내 추가 (기존 line 41-78 사이):

```python
# raw_value 추출 (latest validated reading)
latest_reading = indicator.readings.filter(
    validation_status__in=['ok', 'extreme_jump_allowed']
).order_by('-asof').first()

prev_reading = indicator.readings.filter(
    validation_status__in=['ok', 'extreme_jump_allowed']
).order_by('-asof')[1:2].first() if latest_reading else None

raw_value = latest_reading.raw_value if latest_reading else None
previous_raw_value = prev_reading.raw_value if prev_reading else None

change_pct = None
if raw_value is not None and previous_raw_value and previous_raw_value != 0:
    change_pct = round(((raw_value - previous_raw_value) / abs(previous_raw_value)) * 100, 2)

# display_unit 우선, fallback으로 _infer_unit
raw_value_unit = indicator.display_unit or _infer_unit(indicator)
```

indicators_data dict에 4개 필드 추가:

```python
'raw_value': raw_value,
'raw_value_unit': raw_value_unit,
'previous_raw_value': previous_raw_value,
'change_pct': change_pct,
```

thesis 응답에 2개 필드 추가:

```python
'ai_summary': latest_snapshot.ai_summary if latest_snapshot else '',
'notable_changes': (latest_snapshot.notable_changes or [])[:5] if latest_snapshot else [],
```

### 4-3. \_infer_unit() fallback 함수 (같은 파일 하단)

> 이 함수는 **마이그레이션용 fallback**으로만 사용. 새 지표는 display_unit 필드에서 직접 읽음.

```python
def _infer_unit(indicator):
    """data_params + indicator_type으로 단위 추론. display_unit이 비어있을 때만 사용."""
    params = indicator.data_params or {}
    series_id = params.get('series_id', '')

    if series_id in ('FEDFUNDS', 'DGS10', 'DGS2'):
        return '%'
    if indicator.indicator_type == 'sentiment':
        return ''

    symbol = params.get('symbol', '').upper()
    if 'KRW' in symbol or 'USDKRW' in symbol:
        return '원'
    if symbol.startswith('^'):
        return 'pt'

    if indicator.data_source == 'fmp':
        return '$'
    return ''
```

### 4-4. IndicatorReadingsView 추가 (thesis/views/monitoring_views.py)

```python
class IndicatorReadingsView(APIView):
    """GET /{thesis_id}/indicators/{indicator_id}/readings/?days=14"""
    permission_classes = [IsAuthenticated]

    def get(self, request, thesis_id, indicator_id):
        thesis = get_object_or_404(Thesis, id=thesis_id, user=request.user)
        indicator = get_object_or_404(
            thesis.indicators, id=indicator_id
        )
        days = min(int(request.query_params.get('days', 14)), 90)
        cutoff = timezone.now() - timedelta(days=days)

        readings = list(
            indicator.readings.filter(
                validation_status__in=['ok', 'extreme_jump_allowed'],
                asof__gte=cutoff,
            ).order_by('asof').values('asof', 'value', 'raw_value')
        )

        return Response({
            'indicator_id': str(indicator.id),
            'indicator_name': indicator.name,
            'support_direction': indicator.support_direction,
            'unit': indicator.display_unit or _infer_unit(indicator),
            'readings': readings,
            'count': len(readings),
        })
```

### 4-5. URL 등록 (thesis/urls.py)

```python
path(
    '<uuid:thesis_id>/indicators/<uuid:indicator_id>/readings/',
    IndicatorReadingsView.as_view(),
    name='indicator-readings',
),
```

### 4-6. import 추가

```python
# monitoring_views.py 상단
from datetime import timedelta
from thesis.models import ThesisIndicator  # 기존 Thesis, ThesisAlert에 추가

# urls.py
from thesis.views import IndicatorReadingsView  # 기존 import에 추가
```

### 4-7. 데이터 마이그레이션 스크립트

```python
# thesis/migrations/XXXX_populate_display_unit.py
# RunPython으로 기존 지표의 display_unit을 _infer_unit() 결과로 채우기
def populate_display_unit(apps, schema_editor):
    ThesisIndicator = apps.get_model('thesis', 'ThesisIndicator')
    for ind in ThesisIndicator.objects.filter(display_unit=''):
        # _infer_unit 로직 인라인 (apps 모델에선 메서드 접근 불가)
        params = ind.data_params or {}
        series_id = params.get('series_id', '')
        unit = ''
        if series_id in ('FEDFUNDS', 'DGS10', 'DGS2'):
            unit = '%'
        elif ind.indicator_type == 'sentiment':
            unit = ''
        else:
            symbol = params.get('symbol', '').upper()
            if 'KRW' in symbol or 'USDKRW' in symbol:
                unit = '원'
            elif symbol.startswith('^'):
                unit = 'pt'
            elif ind.data_source == 'fmp':
                unit = '$'
        if unit:
            ind.display_unit = unit
            ind.save(update_fields=['display_unit'])
```

### PR-7 파일 요약

| #   | 파일                                            | 액션   | 변경량                      |
| --- | ----------------------------------------------- | ------ | --------------------------- |
| 1   | thesis/models/indicator.py                      | MODIFY | +3줄 (display_unit 필드)    |
| 2   | thesis/views/monitoring_views.py                | MODIFY | +60줄                       |
| 3   | thesis/urls.py                                  | MODIFY | +4줄                        |
| 4   | thesis/migrations/XXXX_add_display_unit.py      | NEW    | ~5줄 (자동 생성)            |
| 5   | thesis/migrations/XXXX_populate_display_unit.py | NEW    | ~25줄 (데이터 마이그레이션) |

### PR-7 검증

```bash
python manage.py makemigrations thesis
python manage.py migrate
python manage.py shell  # 직접 API 호출 테스트
pytest tests/unit/thesis/  # 기존 테스트 통과
```

- 기존 대시보드 응답과 하위 호환 확인 (새 필드는 추가만)
- IndicatorReadingsView 수동 테스트

---

## 5. PR-8: 프론트엔드 — 실제 값 카드 + AI 분석 (~350줄)

### 5-1. 타입 수정 (frontend/lib/thesis/types.ts)

> `DashboardIndicatorV2` / `DashboardThesisV2` 별도 타입 대신, **기존 타입을 확장**.

```typescript
// ═══ Phase 3: Dashboard 리디자인 — 실제 값 확장 ═══

// 기존 DashboardIndicator에 필드 추가 (백엔드가 하위호환)
// DashboardIndicator interface 내부에 아래 필드 추가:
//   raw_value: number | null
//   raw_value_unit: string          // '$', '원', '%', 'pt', ''
//   previous_raw_value: number | null
//   change_pct: number | null

// 기존 DashboardThesis에 필드 추가:
//   ai_summary: string
//   notable_changes: NotableChange[]

/** alert_engine 이벤트 기반 변화 기록 */
export interface NotableChange {
	indicator_id: string;
	indicator_name: string;
	change_type: "sharp_move" | "direction_flip" | "threshold_cross" | "streak";
	description: string; // "3일 연속 상승 → 하락 전환"
	raw_value_before: number | null;
	raw_value_after: number | null;
	change_pct: number | null;
	severity: "info" | "warning";
}

/** 차트용 시계열 포인트 */
export interface IndicatorReadingPoint {
	asof: string;
	value: number | null; // 정규화 점수 (향후 사용)
	raw_value: number | null; // 실제 값 (미니차트용)
}

/** Readings API 응답 */
export interface IndicatorReadingsResponse {
	indicator_id: string;
	indicator_name: string;
	support_direction: SupportDirection;
	unit: string;
	readings: IndicatorReadingPoint[];
	count: number;
}

/** 차트 기간 타입 */
export type ChartPeriod = 7 | 14 | 30;
```

~35줄 추가 (기존 interface 확장 + 신규 타입).

**주의사항:**

- `DashboardResponseV2` 별도 타입을 만들지 **않는다**. 기존 `DashboardResponse` 타입을 그대로 사용.
- `DashboardIndicator`와 `DashboardThesis` interface에 optional 필드로 추가하거나, 기존 필드를 확장.

### 5-2. API 메서드 추가 (frontend/lib/thesis/api.ts)

```typescript
// thesisApi 객체에 추가 (기존 dashboard 메서드는 그대로 유지 — 타입만 확장됨)
indicatorReadings: (thesisId: string, indicatorId: string, days: number = 14) =>
  GET<IndicatorReadingsResponse>(
    `/thesis/${thesisId}/indicators/${indicatorId}/readings/?days=${days}`
  ),
```

~3줄 추가.

**주의사항:**

- `dashboardV2()` 별도 메서드를 만들지 **않는다**.
- 기존 `dashboard()` 메서드가 그대로 동작 (백엔드가 하위호환이므로 새 필드가 자동으로 포함됨).

### 5-3. 쿼리 훅 수정 (frontend/lib/thesis/queries.ts)

```typescript
// QUERY_KEYS에 추가
readings: (thesisId: string, indicatorId: string, days: number) =>
  ['thesis', thesisId, 'indicators', indicatorId, 'readings', days] as const,
```

~5줄 추가.

**주의사항:**

- `useDashboardV2()` 별도 훅을 만들지 **않는다**.
- 기존 `useDashboard()` 훅을 그대로 사용. 반환 타입이 자연스럽게 확장된 타입을 사용.
- readings 훅은 PR-9에서 추가.

### 5-4. 유틸 함수 추가 (frontend/lib/thesis/utils.ts)

```typescript
/** raw_value를 단위에 맞게 포맷 (KR 타겟 전용 포매팅) */
export function formatRawValue(value: number | null, unit: string): string {
	if (value == null) return "--";
	const abs = Math.abs(value);
	if (abs >= 1e12) {
		const v = (value / 1e12).toFixed(1);
		return unit === "$" ? `$${v}T` : `${v}조${unit}`;
	}
	if (abs >= 1e8) {
		const v = (value / 1e8).toFixed(1);
		return unit === "$" ? `$${v}B` : `${v}억${unit}`;
	}
	const formatted =
		abs >= 100
			? value.toLocaleString("ko-KR", { maximumFractionDigits: 1 })
			: value.toFixed(2);
	if (unit === "$") return `$${formatted}`;
	if (unit === "%") return `${formatted}%`;
	return unit ? `${formatted}${unit}` : formatted;
}

/** 변동률 포맷 */
export function formatChangePct(pct: number | null): {
	text: string;
	colorClass: string;
} {
	if (pct == null) return { text: "--", colorClass: "text-gray-500" };
	const sign = pct >= 0 ? "+" : "";
	return {
		text: `${sign}${pct.toFixed(1)}%`,
		colorClass:
			pct > 0 ? "text-green-400" : pct < 0 ? "text-red-400" : "text-gray-400",
	};
}

/** support_direction에 따른 지지/반박 판정 (score 기반 — 내부 사용, UI에는 라벨만 표시) */
export function supportLabel(score: number): {
	text: string;
	colorClass: string;
} {
	if (score > 0.2) return { text: "지지", colorClass: "text-blue-400" };
	if (score < -0.2) return { text: "반박", colorClass: "text-orange-400" };
	return { text: "중립", colorClass: "text-gray-400" };
}
```

~35줄 추가.

### 5-5. Mock 데이터 업데이트 (frontend/lib/thesis/mock.ts)

기존 `MOCK_DASHBOARD`를 확장:

```typescript
// thesis 객체에 추가:
ai_summary: '지난 7일간 외국인 순매수가 감소 추세를 보이고 있어요. 원/달러 환율은 소폭 상승했지만 VIX는 안정적이에요. 전체적으로 가설을 약하게 지지하는 흐름이에요.',
notable_changes: [
  {
    indicator_id: 'dash-ind-1',
    indicator_name: '외국인 순매수 추이',
    change_type: 'sharp_move' as const,
    description: '전일 대비 급변 (+22.4%)',
    raw_value_before: 9.8e11,
    raw_value_after: 1.2e12,
    change_pct: 22.4,
    severity: 'warning' as const,
  },
  {
    indicator_id: 'dash-ind-2',
    indicator_name: '원/달러 환율',
    change_type: 'direction_flip' as const,
    description: '하락 추세에서 상승 전환',
    raw_value_before: 1365,
    raw_value_after: 1380,
    change_pct: 1.1,
    severity: 'info' as const,
  },
],

// 각 indicator 객체에 추가:
// indicator 1 (외국인 순매수):
raw_value: 1.2e12,
raw_value_unit: '원',
previous_raw_value: 9.8e11,
change_pct: 22.4,

// indicator 2 (원/달러 환율):
raw_value: 1380,
raw_value_unit: '원',
previous_raw_value: 1365,
change_pct: 1.1,

// indicator 3 (VIX):
raw_value: 18.5,
raw_value_unit: 'pt',
previous_raw_value: 18.2,
change_pct: 1.6,
```

~80줄 변경/추가.

### 5-6. NEW: RealValueIndicatorCard.tsx

경로: `frontend/components/thesis/dashboard/RealValueIndicatorCard.tsx`

```
┌────────────────────┐
│ 외국인 순매수 추이  │  name (text-sm, truncate)
│ 1.2조원            │  raw_value (text-2xl, font-bold)
│ +22.4%             │  change_pct (text-sm, colored)
│ ● 지지             │  support badge (dot + label)
│ AI 반도체 수급 개선 │  premise_name (text-xs, gray-500)
└────────────────────┘
```

**Props:**

```typescript
interface RealValueIndicatorCardProps {
	indicator: DashboardIndicator; // 확장된 기존 타입
}
```

**구현 포인트:**

- `formatRawValue(indicator.raw_value, indicator.raw_value_unit)` for main value
- `formatChangePct(indicator.change_pct)` for delta display
- `supportLabel(indicator.score)` for 지지/반박/중립 badge
- 카드 스타일: `bg-gray-900 border border-gray-700 rounded-xl p-4`
- `raw_value`가 null이면 `'--'` 표시
- premise_name이 없으면 해당 줄 미렌더링

~55줄.

### 5-7. NEW: AISummarySection.tsx

경로: `frontend/components/thesis/dashboard/AISummarySection.tsx`

**Props:**

```typescript
interface AISummarySectionProps {
	summary: string;
}
```

**구현 포인트:**

- Bot 아이콘 (lucide `Bot`) + "AI 분석" 헤더 + ai_summary 텍스트
- `summary`가 falsy(null/empty/undefined)이면 **컴포넌트 자체를 렌더링하지 않음** (`if (!summary) return null`)
- 스타일: `bg-gray-900/50 border border-gray-800 rounded-xl p-4`
- 텍스트: `text-sm text-gray-300 leading-relaxed`

~25줄.

### 5-8. NEW: NotableChangesSection.tsx

경로: `frontend/components/thesis/dashboard/NotableChangesSection.tsx`

**Props:**

```typescript
interface NotableChangesSectionProps {
	changes: NotableChange[];
	fallbackText?: string; // 빈 배열일 때 표시할 텍스트
}
```

**구현 포인트:**

- Activity 아이콘 (lucide `Activity`) + "오늘의 변화 (N건)" 헤더
- 각 변화: `indicator_name` + severity에 따른 아이콘 + `description`
- `TREND_CONFIG` 재활용하여 방향 아이콘 표시 (기존 코드 참고)
- `severity === 'warning'` → 주황색 강조, `'info'` → 기본 회색
- 빈 배열이면 fallbackText 또는 "오늘은 특별한 변화가 없어요" 표시
- 스타일: `bg-gray-900/50 border border-gray-800 rounded-xl p-4`

~40줄.

### 5-9. MODIFY: app/thesis/[thesisId]/page.tsx

**변경 내용:**

1. `OverallMoon` import 및 사용 제거
2. `DashboardIndicatorCard` → `RealValueIndicatorCard` 교체
3. `RecentChange` → `NotableChangesSection` + `AISummarySection` 교체
4. Mock 데이터 참조가 확장된 타입 사용 (mock.ts에서 처리됨)
5. 차트 관련 state 변수 추가 (PR-9에서 사용할 준비):

```typescript
// PR-8에서는 선언만, 실제 차트 UI는 PR-9에서 추가
const [chartVisible, setChartVisible] = useState(false);
const [chartPeriod, setChartPeriod] = useState<ChartPeriod>(14);
```

**주의사항:**

- `useDashboard()` 훅 이름 그대로 유지 (V2 분리 안 함)
- `useDashboardV2()` 호출로 변경하지 않음

~140줄 구조 변경.

### PR-8 파일 요약

| #   | 파일                                                   | 액션   | 줄 수  |
| --- | ------------------------------------------------------ | ------ | ------ |
| 1   | frontend/lib/thesis/types.ts                           | MODIFY | +35줄  |
| 2   | frontend/lib/thesis/api.ts                             | MODIFY | +3줄   |
| 3   | frontend/lib/thesis/queries.ts                         | MODIFY | +5줄   |
| 4   | frontend/lib/thesis/utils.ts                           | MODIFY | +35줄  |
| 5   | frontend/lib/thesis/mock.ts                            | MODIFY | +80줄  |
| 6   | components/thesis/dashboard/RealValueIndicatorCard.tsx | NEW    | ~55줄  |
| 7   | components/thesis/dashboard/AISummarySection.tsx       | NEW    | ~25줄  |
| 8   | components/thesis/dashboard/NotableChangesSection.tsx  | NEW    | ~40줄  |
| 9   | app/thesis/[thesisId]/page.tsx                         | MODIFY | ~140줄 |

### PR-8 검증

```bash
npx tsc --noEmit  # 타입 에러 0건
```

- Mock 모드: 카드에 실제 값 표시 확인 (1.2조원, 1,380원, 18.5pt)
- AI 분석 섹션 텍스트 렌더링 확인
- AI 분석 빈 문자열 → 섹션 미렌더링 확인
- 오늘의 변화 2건 표시 확인
- 기존 다른 페이지 (목록, 빌더, 지표설정, 알림, 마감) 정상 동작 확인

---

## 6. PR-9: 프론트엔드 — 미니차트 + 기간 선택 + 정리 (~300줄)

> 원안 대비 ~100줄 절감: CombinedNormalizedChart 삭제 + Zustand 제거

### 6-1. NEW: ChartToggleButton.tsx

경로: `frontend/components/thesis/dashboard/ChartToggleButton.tsx`

**Props:**

```typescript
interface ChartToggleButtonProps {
	visible: boolean;
	onToggle: () => void;
}
```

**구현 포인트:**

- 아이콘: `BarChart3` (lucide) + 텍스트 토글
- `visible ? '차트 숨기기' : '📊 차트 보기'`
- 스타일: `w-full py-3 text-center text-sm text-gray-400 border border-gray-700 rounded-xl`
- 부모 page.tsx에서 `useState`로 관리하는 `chartVisible`을 props로 받음

~20줄.

### 6-2. NEW: PeriodSelector.tsx

경로: `frontend/components/thesis/dashboard/PeriodSelector.tsx`

**Props:**

```typescript
interface PeriodSelectorProps {
	period: ChartPeriod;
	onChange: (p: ChartPeriod) => void;
}
```

**구현 포인트:**

- 3버튼 pill: `7D | 14D | 30D`
- constants.ts의 `PERIOD_OPTIONS` 사용
- 선택된 버튼: `bg-blue-600 text-white`, 미선택: `bg-gray-800 text-gray-400`
- `flex gap-2` 레이아웃

~30줄.

### 6-3. 차트 색상 상수 (frontend/lib/thesis/constants.ts)

```typescript
export const CHART_COLORS = [
	"#60A5FA",
	"#F97316",
	"#A78BFA",
	"#34D399",
	"#F472B6",
	"#FBBF24",
	"#818CF8",
	"#2DD4BF",
] as const;

export const PERIOD_OPTIONS: { value: ChartPeriod; label: string }[] = [
	{ value: 7, label: "7D" },
	{ value: 14, label: "14D" },
	{ value: 30, label: "30D" },
];
```

~12줄 추가.

### 6-4. 쿼리 훅 추가 (frontend/lib/thesis/queries.ts)

```typescript
import { useQueries } from "@tanstack/react-query";

export function useAllIndicatorReadings(
	thesisId: string,
	indicatorIds: string[],
	days: ChartPeriod,
) {
	return useQueries({
		queries: indicatorIds.map((id) => ({
			queryKey: QUERY_KEYS.readings(thesisId, id, days),
			queryFn: () => thesisApi.indicatorReadings(thesisId, id, days),
			enabled: !USE_MOCK && !!thesisId && indicatorIds.length > 0,
			staleTime: 1000 * 60 * 30,
		})),
	});
}
```

~15줄 추가.

### 6-5. NEW: IndividualMiniCharts.tsx (~90줄)

경로: `frontend/components/thesis/dashboard/IndividualMiniCharts.tsx`

**역할:** 지표별 독립 미니차트 (raw_value 시계열).

**Props:**

```typescript
interface IndividualMiniChartsProps {
	thesisId: string;
	indicators: DashboardIndicator[];
	period: ChartPeriod;
}
```

**구조:** 지표 배열을 map하여 각각 렌더링:

```
── {indicator_name} ({unit}) ──
┌─────────────────────────────┐
│ AreaChart, height=100px     │
│ Y: auto domain, real units  │
│ X: dates                    │
└─────────────────────────────┘
```

**recharts 구성 (per indicator):**

- `ResponsiveContainer` (width="100%", height={100})
- `AreaChart` with gradient fill (indicator color → transparent)
- `XAxis` (date, `format(parseISO(d), 'MM/dd')`, minimal ticks)
- `YAxis` (auto domain, `tickFormatter → formatRawValue`)
- `Tooltip`: 날짜 + 실제 값 + 단위
- Dark theme: `CartesianGrid stroke="#374151"`, `XAxis/YAxis stroke="#6B7280"`

**데이터 흐름:**

1. `useAllIndicatorReadings()` 또는 Mock에서 readings 가져오기
2. Mock 모드: `MOCK_READINGS[indicator.id]` 사용
3. 실제 모드: 각 indicator별 readings API 호출

**기존 패턴 참고:** `frontend/components/charts/StockPriceChart.tsx`
(recharts ResponsiveContainer + LineChart + AreaChart 사용 방식 동일)

### 6-6. Mock readings 데이터 추가 (frontend/lib/thesis/mock.ts)

```typescript
function generateMockReadings(
	base: number,
	vol: number,
	days: number,
): IndicatorReadingPoint[] {
	const points: IndicatorReadingPoint[] = [];
	const now = new Date();
	for (let i = days; i >= 0; i--) {
		const date = new Date(now);
		date.setDate(date.getDate() - i);
		const noise = (Math.random() - 0.5) * 2 * vol;
		const trend = ((days - i) / days) * vol * 0.3; // slight uptrend
		points.push({
			asof: date.toISOString(),
			value: Math.random() * 2 - 1, // random normalized score
			raw_value: base + noise + trend,
		});
	}
	return points;
}

export const MOCK_READINGS: Record<string, IndicatorReadingsResponse> = {
	"dash-ind-1": {
		indicator_id: "dash-ind-1",
		indicator_name: "외국인 순매수 추이",
		support_direction: "positive",
		unit: "원",
		readings: generateMockReadings(1e12, 1e11, 30),
		count: 31,
	},
	"dash-ind-2": {
		indicator_id: "dash-ind-2",
		indicator_name: "원/달러 환율",
		support_direction: "negative",
		unit: "원",
		readings: generateMockReadings(1365, 15, 30),
		count: 31,
	},
	"dash-ind-3": {
		indicator_id: "dash-ind-3",
		indicator_name: "VIX (공포지수)",
		support_direction: "positive",
		unit: "pt",
		readings: generateMockReadings(17.5, 2, 30),
		count: 31,
	},
};
```

~40줄 추가.

### 6-7. MODIFY: app/thesis/[thesisId]/page.tsx — 차트 섹션 추가

카드 그리드 아래에 추가:

```tsx
{
	/* 차트 토글 */
}
<ChartToggleButton
	visible={chartVisible}
	onToggle={() => setChartVisible((v) => !v)}
/>;

{
	/* 차트 영역 (토글 시 표시) */
}
{
	chartVisible && (
		<div className='space-y-4'>
			<PeriodSelector
				period={chartPeriod}
				onChange={setChartPeriod}
			/>
			<IndividualMiniCharts
				thesisId={thesisId}
				indicators={data.indicators}
				period={chartPeriod}
			/>
		</div>
	);
}
```

~25줄 추가.

### 6-8. 정리: 삭제 대상

| 파일                                                     | 이유                              |
| -------------------------------------------------------- | --------------------------------- |
| `components/thesis/dashboard/OverallMoon.tsx`            | 대시보드에서 제거, 다른 곳 미사용 |
| `components/thesis/dashboard/DashboardIndicatorCard.tsx` | RealValueIndicatorCard로 교체     |
| `components/thesis/dashboard/RecentChange.tsx`           | NotableChangesSection으로 교체    |

**삭제 전 확인사항:**

```bash
# 각 파일이 다른 곳에서 import되지 않는지 확인
grep -r "OverallMoon" frontend/ --include="*.tsx" --include="*.ts"
grep -r "DashboardIndicatorCard" frontend/ --include="*.tsx" --include="*.ts"
grep -r "RecentChange" frontend/ --include="*.tsx" --include="*.ts"
grep -r "MoonPhase" frontend/ --include="*.tsx" --include="*.ts"
```

**utils.ts 정리:**

- `scoreToPhaseMeta()` 삭제 가능 (OverallMoon 전용)
- `scoreToBadgeState()` 유지 (DashboardHeader의 ThesisBadge에서 사용)

### PR-9 파일 요약

| #   | 파일                                                   | 액션   | 줄 수                  |
| --- | ------------------------------------------------------ | ------ | ---------------------- |
| 1   | components/thesis/dashboard/ChartToggleButton.tsx      | NEW    | ~20줄                  |
| 2   | components/thesis/dashboard/PeriodSelector.tsx         | NEW    | ~30줄                  |
| 3   | components/thesis/dashboard/IndividualMiniCharts.tsx   | NEW    | ~90줄                  |
| 4   | frontend/lib/thesis/queries.ts                         | MODIFY | +15줄                  |
| 5   | frontend/lib/thesis/constants.ts                       | MODIFY | +12줄                  |
| 6   | frontend/lib/thesis/mock.ts                            | MODIFY | +40줄                  |
| 7   | frontend/lib/thesis/utils.ts                           | MODIFY | -scoreToPhaseMeta 삭제 |
| 8   | app/thesis/[thesisId]/page.tsx                         | MODIFY | +25줄                  |
| 9   | components/thesis/dashboard/OverallMoon.tsx            | DELETE |                        |
| 10  | components/thesis/dashboard/DashboardIndicatorCard.tsx | DELETE |                        |
| 11  | components/thesis/dashboard/RecentChange.tsx           | DELETE |                        |

### PR-9 검증

```bash
npx tsc --noEmit  # 타입 에러 0건
npm run build     # 빌드 성공
```

- Mock 모드: 차트 토글 ↔ 숨김/표시 확인
- Mock 모드: 기간 전환 (7D/14D/30D) 확인
- IndividualMiniCharts: 3개 독립 차트 + 실제 단위 Y축 확인
- 모바일 반응형: `max-w-lg` 내 차트 스크롤 확인
- 삭제된 컴포넌트가 다른 곳에서 import되지 않는지 확인
- 기존 페이지 전부 정상 동작 확인

---

## 7. PR-10: AI 모니터링 파이프라인 (별도 — 향후)

> PR-7~9와 독립적. 프론트엔드 리디자인 완료 후 또는 병렬 진행.

### 7-1. ai_summary 생성 파이프라인

**Celery Task:** `generate_thesis_summaries` (매일 07:30, 설계 문서 5.3에 이미 정의)

**입력 (수학 엔진이 이미 계산한 것):**

- 각 지표의 score 변화 (전일 대비, 7일 추세)
- Stage 3 상태 (strengthening, weakening, critical 등)
- 경고 플래그 (weakest_link, divergence, extreme_vol)
- data_coverage

**입력 (외부 컨텍스트 — 이미 있는 인프라):**

- `news/` 앱의 DailyNewsKeyword (오늘의 시장 키워드)
- 가설의 전제(premise) 텍스트
- 지표의 raw_value 변화

**출력:** 2-3문장의 상황 요약 → `ThesisSnapshot.ai_summary`에 저장

**LLM 호출:**

- 모델: Gemini 2.5 Flash
- 변화가 있는 가설만 생성 (비용 절감)
- prompt에 수학 엔진 결과를 구조화해서 전달, "사용자가 이해할 수 있는 언어로 번역하라"는 지시

### 7-2. notable_changes 연동

**데이터 소스:** 기존 `alert_engine.py`가 감지하는 이벤트 재활용

**구현:**

- `create_snapshots_and_alerts` Celery task에서 alert 생성 시, 동시에 `ThesisSnapshot.notable_changes` JSONField에도 기록
- 새로운 감지 로직 불필요 — 기존 alert 이벤트(direction_flip, sharp_move, extreme_volatility 등)를 `NotableChange` 포맷으로 변환만

```python
# snapshot_builder.py 내에서
notable = []
for alert in today_alerts:
    if alert.alert_type in ('direction_flip', 'sharp_move', 'extreme_volatility'):
        indicator = alert.indicator
        latest = indicator.readings.filter(
            validation_status__in=['ok', 'extreme_jump_allowed']
        ).order_by('-asof')[:2]
        notable.append({
            'indicator_id': str(indicator.id),
            'indicator_name': indicator.name,
            'change_type': alert.alert_type,
            'description': alert.message,
            'raw_value_before': latest[1].raw_value if len(latest) > 1 else None,
            'raw_value_after': latest[0].raw_value if latest else None,
            'change_pct': ...,  # 계산
            'severity': 'warning' if alert.alert_type == 'extreme_volatility' else 'info',
        })
snapshot.notable_changes = notable
```

### 7-3. 향후 확장: 주간 건강 검진 (Weekly Health Check)

> Phase 2 이후, 데이터 축적 후 구현

트리거: 주 1회, active 가설 중 14일 이상 경과한 것

검진 항목:

1. **지표 커버리지 체크** — indicator_matcher.py 재활용
2. **지표 유효성 조기 경고** — ValidityScore 활용 (Phase 2+)
3. **전제 재검토 제안** — 전제의 시간적 맥락을 LLM이 판단
4. **상관관계 알림** — Layer C Rolling Pearson 결과 활용

---

## 8. 재사용하는 기존 코드

| 코드                   | 위치                                    | 용도                                                              |
| ---------------------- | --------------------------------------- | ----------------------------------------------------------------- |
| `authAxios`            | `lib/api/client.ts`                     | API 호출                                                          |
| `ThesisBadge`          | `components/thesis/common/`             | DashboardHeader에서 유지                                          |
| `scoreToBadgeState()`  | `lib/thesis/utils.ts`                   | DashboardHeader에서 유지                                          |
| `sanitizeHexColor()`   | `lib/thesis/utils.ts`                   | 차트 색상 검증                                                    |
| `TREND_CONFIG`         | `lib/thesis/constants.ts`               | NotableChangesSection에서 방향 아이콘 재사용                      |
| `StockPriceChart 패턴` | `components/charts/StockPriceChart.tsx` | recharts 사용 패턴 참고 (ResponsiveContainer, LineChart, Tooltip) |
| `QUERY_KEYS 패턴`      | `lib/thesis/queries.ts`                 | readings 키 추가                                                  |
| `USE_MOCK && !!id`     | `lib/thesis/queries.ts`                 | query enabled 패턴 유지                                           |

---

## 9. 전체 규모 요약

| PR       | 신규     | 수정      | 삭제  | 예상 줄  | 범위             |
| -------- | -------- | --------- | ----- | -------- | ---------------- |
| PR-7     | 2        | 3         | 0     | ~80      | Backend          |
| PR-8     | 3        | 6         | 0     | ~350     | Frontend         |
| PR-9     | 3        | 4         | 3     | ~300     | Frontend         |
| PR-10    | 1~2      | 1~2       | 0     | ~100     | Backend (Celery) |
| **합계** | **9~10** | **14~15** | **3** | **~830** |                  |

원안 대비 ~40줄 절감 (CombinedNormalizedChart 120줄 삭제 - Zustand 15줄 삭제 + display_unit 마이그레이션 추가).

---

## 10. 주의사항 및 실수 방지 체크리스트

### 절대 하지 말 것

- [ ] `dashboardV2()` 또는 `useDashboardV2()` 별도 메서드/훅 생성하지 않기
- [ ] `DashboardResponseV2` 별도 응답 타입 생성하지 않기
- [ ] Zustand store 파일(`dashboardStore.ts`) 생성하지 않기
- [ ] `CombinedNormalizedChart` 컴포넌트 생성하지 않기
- [ ] 내부 점수(score, degree)를 UI에 직접 표시하지 않기 (supportLabel 라벨은 OK)

### 반드시 확인할 것

- [ ] `MoonPhase.tsx` (common) import 검색 — 다른 곳에서 사용 중이면 삭제 보류
- [ ] `scoreToPhaseMeta()` 삭제 전 다른 곳에서 사용 안 하는지 확인
- [ ] Mock 모드에서 모든 새 컴포넌트가 정상 렌더링되는지 확인
- [ ] `raw_value`가 null인 경우 `'--'` 표시 처리
- [ ] `ai_summary`가 빈 문자열인 경우 AISummarySection 미렌더링
- [ ] `notable_changes`가 빈 배열인 경우 fallback 텍스트 표시
- [ ] 기존 페이지(목록, 빌더, 지표설정, 알림, 마감) 회귀 테스트

### formatRawValue 엣지 케이스

- `null` → `'--'`
- `0` → `'0.00'` (또는 단위에 따라 `'$0.00'`, `'0.00%'`)
- 음수 → 마이너스 부호 포함 (예: `-1.2조원`)
- 매우 큰 수 → 조/억 단위 변환 (1e12 이상 → 조, 1e8 이상 → 억)
- 달러 단위 → T/B 변환 (1e12 이상 → $1.2T, 1e8 이상 → $1.2B)

---

## 11. 기존 아키텍처 참고

### ThesisSnapshot 모델 (이미 존재하는 필드)

```python
# thesis/models/monitoring.py — 설계 문서 4.2에서 정의
class ThesisSnapshot(models.Model):
    thesis = ForeignKey(Thesis, on_delete=CASCADE, related_name='snapshots')
    date = DateField()
    overall_score = FloatField()
    overall_label = CharField(max_length=50)
    indicator_scores = JSONField()    # {"indicator_uuid": {"score": 0.5, "arrow": 45, ...}}
    notable_changes = JSONField(default=list)  # ← PR-10에서 채움
    ai_summary = TextField(blank=True)         # ← PR-10에서 채움

    class Meta:
        unique_together = ['thesis', 'date']
```

→ `notable_changes`와 `ai_summary` 필드는 **이미 모델에 존재**. 별도 마이그레이션 불필요.
→ PR-8에서는 이 필드들이 비어있어도 정상 동작하도록 프론트엔드를 구현.

### 수학 엔진 파이프라인 (변경 없음)

```
Stage 0 (Data Validation) → Stage 1 (Robust Z + Decay) → Stage 2 (가중평균) → Stage 3 (상태 판정)
```

이 파이프라인은 Phase 3 리디자인에서 **일절 수정하지 않는다**.
Dashboard API에서 raw_value를 추가로 내려줄 뿐, 기존 score/degree 계산 흐름은 그대로.

### Celery Task 스케줄 (기존)

| Task                          | 시간     | 역할                              |
| ----------------------------- | -------- | --------------------------------- |
| `update_indicator_readings`   | 18:00 ET | 지표 값 업데이트                  |
| `calculate_scores`            | 18:15 ET | Stage 1→2 스코어 계산             |
| `create_snapshots_and_alerts` | 18:30 ET | 스냅샷 + 알림                     |
| `generate_thesis_summaries`   | 07:30    | AI 요약 생성 ← **PR-10에서 구현** |
