# Thesis Dashboard — 분기 지표 표시 + 다분기 추이 시각화

## 1. Context: 왜 이 변경이 필요한가

### 현재 문제

가설 대시보드에서 분기 지표(EPS, 매출성장률, FCF 등)가 **"--"**로 표시됩니다.

```
매출성장률 (YoY)    --    --    중립
EPS 추이           --    --    중립
뉴스 센티먼트       --    --    중립
```

**원인 체인:**
1. `data_source='metrics'`가 `DATA_SOURCE_FETCHERS`에 등록되지 않음 → fetcher 없음 → `(None, None)` 반환
2. `ThesisIndicator.data_source` choices에 `'metrics'` 없음 (DB에는 저장되지만 파이프라인에서 무시)
3. EOD pipeline의 `_fetch_fmp_value()`는 `get_quote()`(일간 시세)만 호출, 분기 재무지표 미지원
4. `IndicatorReading`이 0건 → 대시보드 `latest_reading` = None → `raw_value` = null → "--"
5. 분기 데이터의 QoQ/YoY 비교 로직 없음

### 사용자 요구
- **마지막으로 확인된 값 + 날짜** 표시 (예: "12.3% (2025 Q3)")
- **이전 분기/연도 대비 변화** (예: "Q2 8.1% → Q3 12.3%, +4.2%p")
- **다분기 추이** (최근 4분기를 시각적으로 볼 수 있는 미니 차트)

### 이미 사용 가능한 데이터
- `IncomeStatement`, `BalanceSheet`, `CashFlowStatement` 모델에 `period_type='quarterly'`, `fiscal_quarter` 필드로 분기 데이터 이미 저장됨
- `validation/services/metric_calculator.py`에 33개 지표 계산 공식 구현 완료 (현재 연간만 사용)
- `CompanyMetricLatest`에 최신값 + 추세(improving/flat/deteriorating) 캐시 있음 (연간)

---

## 2. 검증된 기술 사실 (코드 확인 결과)

### IndicatorReading.asof는 DateTimeField
- `unique_together = ['indicator', 'asof']` — **datetime 단위** (날짜+시간)
- FMP fetcher: `asof = timezone.now()` (시분초 포함)
- FRED fetcher: `timezone.make_aware(datetime.strptime(...))` (자정 00:00:00)
- **date truncation 없음** — 같은 날 여러 번 실행하면 시간이 다르면 중복 레코드 생성 가능

### MetricCalculator 시그니처
```python
def _calculate_all_metrics(self, inc, bal, cf, prev_inc, prev_bal, prev_cf, prev_bal_3y, stock) -> dict
# 입력: 모델 인스턴스 직접 전달 (IncomeStatement, BalanceSheet, CashFlowStatement)
# 반환: {metric_code: (value, value_status, exclusion_reason)}
```

### prior year 필요 지표 (분기 적용 시 주의)
| metric_code | 필요 데이터 | 분기 호환 |
|---|---|---|
| `revenue_growth_yoy` | prev_inc (전년) | ✅ 전년 동기 분기 필요 |
| `operating_income_growth` | prev_inc | ✅ 전년 동기 |
| `fcf_growth_yoy` | prev_cf | ✅ 전년 동기 |
| `interest_coverage` | prev_inc | ⚠️ 분기 단위 이자비용 없을 수 있음 |
| `inventory_vs_sales_growth` | prev_bal, prev_inc | ✅ 전년 동기 |
| `dilution_3y_cum` | prev_bal_3y (3년 전) | ❌ 분기에서 3년 전 분기 찾기 어려움 |
| `cash_from_ops_trend` | N/A | ❌ 미구현 (하드코딩 missing) |
| `sbc_to_revenue` | N/A | ❌ 미구현 (SBC 필드 없음) |
| `buyback_offsets_sbc` | N/A | ❌ 미구현 |

### 기존 지표 data_source 확인
| ID | 지표 | data_source |
|---|---|---|
| 5 | EPS 추이 | **fmp** (get_quote로 조회) |
| 50 | PER | **fmp** |
| 55 | FCF | **fmp** |
| 57 | 영업이익률 | **fmp** |
| 58 | 매출성장률 (YoY) | **fmp** |
| 60~73 | 신규 재무 체질 지표 | **metrics** ✅ |

→ **기존 가설에서 id 5/50/55/57/58을 사용한 지표는 `data_source='fmp'`로 저장되어 있음.**
→ 이 지표들은 FMP `get_quote()`의 `eps`, `pe` 필드로 fetch 가능하지만, 분기 히스토리는 불가.
→ `data_source='metrics'` 지표(60~73)만 새 fetcher 대상.

### CompanyMetricLatest fallback 필드
- `latest_value`, `latest_fiscal_year`, `trend_label`, `trend_slope`, `signal`, `signal_reason`
- **quarterly 구분 없음** — 연간 값만 저장

---

## 3. 구현 계획

### Phase 1: Backend — Metrics Fetcher (BE-PR-1)

#### 1-1. ThesisIndicator model에 `'metrics'` data_source 등록

**파일:** `thesis/models/indicator.py` (line 36-44)

```python
DATA_SOURCE_CHOICES = [
    ('fmp', 'FMP'),
    ('fred', 'FRED'),
    ('news_sentiment', 'News Sentiment'),
    ('metrics', 'Metrics'),        # ← 추가
    ('manual', 'Manual'),
    ('custom', 'Custom'),
]
```

마이그레이션 생성.

#### 1-2. 분기 지표 조회 서비스 신규 생성

**파일:** `thesis/services/quarterly_metric_fetcher.py` (신규)

```python
def fetch_quarterly_metric(symbol: str, metric_code: str) -> dict | None:
    """
    단일 종목의 최신 분기 지표값 + 비교 + 4분기 히스토리.

    Returns:
        {
            'value': 0.123,
            'fiscal_year': 2025,
            'fiscal_quarter': 3,
            'reported_date': '2025-10-28',
            'prev_value': 0.081,
            'change_pct': 51.8,
            'comparison_type': 'qoq' | 'yoy',
            'quarterly_history': [
                {'fy': 2024, 'fq': 4, 'value': 0.052},
                {'fy': 2025, 'fq': 1, 'value': 0.063},
                {'fy': 2025, 'fq': 2, 'value': 0.081},
                {'fy': 2025, 'fq': 3, 'value': 0.123},
            ],
        }
    """
```

**QoQ vs YoY 비교 매핑:**
```python
# 기본 비교 방식 매핑
COMPARISON_TYPE_MAP = {
    # YoY (전년 동기 대비) — 계절성이 있는 지표
    'revenue_growth_yoy': 'yoy',
    'operating_income_growth': 'yoy',
    'fcf_growth_yoy': 'yoy',
    'gross_margin': 'yoy',
    'net_margin': 'yoy',
    'operating_margin': 'yoy',

    # QoQ (직전 분기 대비) — 추세 변화가 중요한 지표
    'roe': 'qoq',
    'roic': 'qoq',
    'current_ratio': 'qoq',
    'interest_coverage': 'qoq',
    'net_debt_to_ebitda': 'qoq',
    'fcf_margin': 'qoq',
    'ev_to_ebitda': 'qoq',
    'fcf_yield': 'qoq',
    'dso': 'qoq',
    'asset_turnover': 'qoq',
    'accruals_ratio': 'qoq',
    'net_shareholder_yield': 'qoq',
}
```

**YoY 비교 시 쿼리:**
```python
# 전년 동기: fiscal_year - 1, 같은 fiscal_quarter
prev_yoy = IncomeStatement.objects.filter(
    stock_id=symbol, period_type='quarterly',
    fiscal_year=latest_fy - 1, fiscal_quarter=latest_fq,
).first()
```

**QoQ 비교 시:** 직전 분기 (Q1→전년 Q4 처리 포함)

**분기 미지원 지표 목록 (calculator에서 skip):**
- `dilution_3y_cum` — 3년 전 분기 데이터 불가
- `cash_from_ops_trend` — 미구현
- `sbc_to_revenue` — SBC 필드 없음
- `buyback_offsets_sbc` — SBC 데이터 필요

→ 이 4개는 `fetch_quarterly_metric`에서 early return `None`

**calculator 호환:**
- `_calculate_all_metrics(inc, bal, cf, prev_inc, prev_bal, prev_cf, prev_bal_3y, stock)`는 모델 인스턴스를 직접 받음
- 분기 IncomeStatement 인스턴스도 동일한 필드를 가지므로 그대로 전달 가능
- `prev_inc` 등은 YoY면 전년 동기 분기, QoQ면 직전 분기로 전달
- `prev_bal_3y`는 `None` 전달 (dilution_3y_cum은 skip)

#### 1-3. EOD Pipeline에 metrics fetcher 등록

**파일:** `thesis/tasks/eod_pipeline.py`

```python
def _fetch_metrics_value(indicator):
    from thesis.services.quarterly_metric_fetcher import fetch_quarterly_metric

    metric_code = indicator.data_params.get('metric_code')
    symbol = indicator.data_params.get('symbol') or indicator.thesis.target.upper()

    if not metric_code or not symbol:
        return None, None

    result = fetch_quarterly_metric(symbol, metric_code)
    if not result or result['value'] is None:
        return None, None

    return result['value'], timezone.now()
```

**asof date truncation:**
```python
# IndicatorReading의 unique_together=(indicator, asof)가 datetime 단위.
# 매일 EOD 실행 시 시간이 달라 중복 레코드 방지를 위해 자정으로 truncate:
from django.utils import timezone
asof = timezone.now().replace(hour=18, minute=0, second=0, microsecond=0)
# 18:00 ET 고정 — EOD 실행 시각과 일치, 하루 1건 보장
```

→ 기존 FMP/FRED fetcher도 동일 패턴 적용 검토 (별도 PR)

**DATA_SOURCE_FETCHERS 등록:**
```python
DATA_SOURCE_FETCHERS = {
    'fmp': _fetch_fmp_value,
    'fred': _fetch_fred_value,
    'news_sentiment': _fetch_news_sentiment_value,
    'metrics': _fetch_metrics_value,
}
```

#### 1-4. 기존 fmp 지표 마이그레이션 검토

기존 가설의 id 5/50/55/57/58 지표는 `data_source='fmp'`로 저장되어 있어 새 metrics fetcher와 무관.
이 지표들은 FMP `get_quote()`로 TTM 값을 가져오므로 **현재 동작에 문제 없음**.
`data_source='metrics'`로 마이그레이션하지 않음 — 혼란 방지.

**다만:** 앞으로 새로 생성되는 가설에서 Gemini가 id 60~73(`metrics`)을 추천하도록 이미 프롬프트에 반영됨. 기존 가설은 그대로 유지.

#### 1-5. 단위 테스트

**파일:** `tests/unit/thesis/test_quarterly_metric_fetcher.py` (신규)

테스트 케이스:
```
1. 정상: 5분기 데이터 존재 → 최신값 + 4분기 히스토리 + change_pct 정상
2. 분기 데이터 1건만 → quarterly_history 1개, change_pct = None
3. 분기 데이터 0건 → CompanyMetricLatest 연간 fallback
4. CompanyMetricLatest도 없음 → None 반환
5. 교차 테이블 지표 (income + balance 필요) → 정상 계산
6. YoY 비교: 전년 동기 데이터 없을 때 → change_pct = None
7. QoQ 비교: Q1에서 전년 Q4 올바르게 참조
8. 분기 미지원 지표 (dilution_3y_cum 등) → None 반환
```

---

### Phase 2: Backend — Dashboard 응답 확장 (BE-PR-2)

**파일:** `thesis/views/monitoring_views.py`

#### 2-1. 응답 필드 추가

```python
'fiscal_label': str | null,           # "2025 Q3" 또는 "2024 FY"
'quarterly_history': list | null,     # [{fy, fq, value}, ...]
'is_quarterly': bool,
'comparison_type': str | null,        # "qoq" | "yoy"
```

#### 2-2. N+1 batch 조회 설계

```python
def prefetch_quarterly_data(
    indicators: list[ThesisIndicator]
) -> dict[tuple[str, str], dict]:
    """
    metrics 지표들의 분기 데이터를 batch로 조회.
    Returns: {(symbol, metric_code): quarterly_data_dict, ...}
    """
```

**내부 구현:**
1. indicators에서 `data_source='metrics'`인 것만 필터
2. unique symbols 추출 (중복 제거)
3. symbol별로 `IncomeStatement`, `BalanceSheet`, `CashFlowStatement`를 **한 번씩만** 조회 (최근 5분기)
4. 조회된 재무제표를 메모리 dict에 캐싱: `{symbol: {'inc': [...], 'bal': [...], 'cf': [...]}}`
5. 각 (symbol, metric_code) 조합에 대해 calculator 실행 → 결과 캐싱

**DashboardView 수정 흐름:**
```python
indicators = thesis.indicators.filter(is_active=True)
metrics_indicators = [i for i in indicators if i.data_source == 'metrics']
quarterly_cache = prefetch_quarterly_data(metrics_indicators)

for indicator in indicators:
    # ... 기존 로직 ...
    if indicator.data_source == 'metrics':
        symbol = indicator.data_params.get('symbol') or thesis.target.upper()
        metric_code = indicator.data_params.get('metric_code')
        qdata = quarterly_cache.get((symbol, metric_code))
        if qdata:
            raw_value = float(qdata['value'])
            change_pct = qdata.get('change_pct')
            fiscal_label = f"{qdata['fiscal_year']} Q{qdata['fiscal_quarter']}"
            quarterly_history = qdata['quarterly_history']
            is_quarterly = True
            comparison_type = qdata.get('comparison_type')
```

**예상 쿼리 수:** N개 지표 × 3 테이블 = 3N회 → S개 symbol × 3 테이블 = 3S회 (S ≤ N, 보통 1~3)

---

### Phase 3: Frontend — 분기 지표 표시 (FE-PR-1)

#### 3-1. 타입 확장

**파일:** `frontend/lib/thesis/types.ts`

```typescript
export interface QuarterlyPoint {
  fy: number
  fq: number
  value: number
}

export interface DashboardIndicator {
  // ... 기존 필드 ...
  fiscal_label: string | null
  quarterly_history: QuarterlyPoint[] | null
  is_quarterly: boolean
  comparison_type: 'qoq' | 'yoy' | null
}
```

#### 3-2. QuarterlySparkline 컴포넌트

**파일:** `frontend/components/thesis/dashboard/QuarterlySparkline.tsx` (신규)

- div 기반 4-bar 미니 차트 (Recharts 사용 안 함)
- 높이 40px, 최신 분기 강조 (blue-500)
- QoQ 상승=초록, 하락=빨강
- 호버 시 툴팁: "Q3 2025: 12.3%"

#### 3-3. RealValueIndicatorCard 수정

**파일:** `frontend/components/thesis/dashboard/RealValueIndicatorCard.tsx`

**조건 분기:**
```
if is_quarterly && quarterly_history:
    → fiscal_label ("2025 Q3") 표시
    → comparison_type에 따라 "QoQ +4.2%" 또는 "YoY +12.3%" 라벨
    → QuarterlySparkline 표시

elif is_quarterly && !quarterly_history:
    → fiscal_label ("2024 FY") 표시 (연간 fallback)
    → 변화율 라벨 "YoY" 고정
    → 스파크라인 숨김
    → fiscal_label 색상을 gray로 (시각적 구분)

else:
    → 기존 로직 (raw_value_asof 표시, 일간 데이터)
```

#### 3-4. IndividualMiniCharts에서 분기 지표 분리

**파일:** `frontend/components/thesis/dashboard/IndividualMiniCharts.tsx`

`is_quarterly === true` 지표는 일간 미니차트에서 제외.
QuarterlySparkline이 카드 내에서 역할 대신.

---

## 4. PR 순서

| PR | 범위 | 파일 |
|----|------|------|
| BE-PR-1 | metrics fetcher + model + 테스트 | `thesis/services/quarterly_metric_fetcher.py`(신규), `thesis/tasks/eod_pipeline.py`, `thesis/models/indicator.py`, migration, `tests/unit/thesis/test_quarterly_metric_fetcher.py`(신규) |
| BE-PR-2 | Dashboard 응답 확장 + batch 조회 | `thesis/views/monitoring_views.py` |
| FE-PR-1 | 타입 + QuarterlySparkline + 카드 + 차트 분리 | `frontend/lib/thesis/types.ts`, `frontend/components/thesis/dashboard/QuarterlySparkline.tsx`(신규), `frontend/components/thesis/dashboard/RealValueIndicatorCard.tsx`, `frontend/components/thesis/dashboard/IndividualMiniCharts.tsx` |

---

## 5. 검증 계획

```bash
# BE-PR-1 검증
# 1. 분기 재무제표 데이터 존재 확인
python manage.py shell -c "
from stocks.models import IncomeStatement
q = IncomeStatement.objects.filter(period_type='quarterly')
print(f'분기 데이터: {q.count()}건, 종목 수: {q.values(\"stock_id\").distinct().count()}')"

# 2. 단위 테스트 실행
python -m pytest tests/unit/thesis/test_quarterly_metric_fetcher.py -v

# 3. fetcher 직접 테스트
python manage.py shell -c "
from thesis.services.quarterly_metric_fetcher import fetch_quarterly_metric
r = fetch_quarterly_metric('AAPL', 'operating_margin')
print(r)"

# BE-PR-2 검증
# 4. Dashboard API 응답에 분기 데이터 포함 확인
curl -H 'Authorization: ...' /api/v1/thesis/{id}/dashboard/ | \
  python -m json.tool | grep -A5 'is_quarterly'

# FE-PR-1 검증
npx tsc --noEmit
# 브라우저: 대시보드에서 분기 지표가 값 + fiscal_label + 스파크라인으로 표시되는지 확인
# 브라우저: 일간 지표(NASDAQ, Gold 등)는 기존대로 날짜 표시 유지되는지 확인
# 브라우저: 연간 fallback 시 "2024 FY" + 스파크라인 숨김 + gray 라벨 확인
```

---

## 6. 엣지 케이스

| 상황 | 처리 |
|------|------|
| 분기 재무제표가 DB에 없음 | `CompanyMetricLatest`(연간) fallback → `fiscal_label: "2024 FY"`, `quarterly_history: null` |
| symbol이 data_params에 없음 | `thesis.target.upper()` fallback |
| metric_code가 income+balance 교차 필요 | 같은 (fiscal_year, fiscal_quarter) 기준 매칭 |
| 분기 데이터 1개만 존재 | `quarterly_history` 1개, `change_pct` = null |
| 매일 EOD 실행 시 같은 값 | `asof` 18:00 고정 → `unique_together`로 하루 1건 보장, `change_pct=0` |
| YoY 비교 시 전년 동기 없음 | `change_pct` = null, 라벨 "YoY --" 표시 |
| 분기 미지원 지표 (dilution_3y_cum 등) | `fetch_quarterly_metric` → None → 연간 fallback |
| 기존 fmp 지표 (id 5/50/55/57/58) | **마이그레이션 안 함** — FMP get_quote() TTM 값으로 기존대로 동작 |
