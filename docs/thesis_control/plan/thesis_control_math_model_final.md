# Thesis Control — 수학 모델링 최종 확정

> 버전: 2.3.2 FINAL  
> 작성일: 2026-03-06  
> 원칙: 1인 MVP, 자동화 최우선, 수학이 핵심 / LLM은 보조

---

## 0. 버전 이력

### v2.3.1 → v2.3.2 변경 사항 (테두리 잠금)

| #   | 변경                                                                        | 영향 범위        |
| --- | --------------------------------------------------------------------------- | ---------------- |
| 1   | Validation 순서: **stale을 jump보다 먼저** (null→min/max→finite→stale→jump) | Stage 0          |
| 2   | **`latest_reading_value` = last validated reading** 명시                    | Stage 0 정의     |
| 3   | **`math.isfinite` 체크** 추가 (NaN/inf 방어)                                | Stage 0          |
| 4   | **`mad_floor`** 추가: mad≈0일 때 중립 반환                                  | Stage 1          |
| 5   | **inactive(None)의 의미** 명문화                                            | 스냅샷/학습 정의 |

### 이전 버전 이력

| 버전   | 주요 변경                                                                                                               |
| ------ | ----------------------------------------------------------------------------------------------------------------------- |
| v2.0   | Layer A~E → 3-Stage Pipeline 압축                                                                                       |
| v2.1   | Robust Z(MAD), Data Validation, Extreme Vol, 수동 오버라이드, 중복 경고, 리마인더, Phase 2 상관 할인, Phase 3 Online LR |
| v2.2   | extreme_jump=skip, min_valid_value, asof 기준, ε/window/decay 모델 필드, thesis bias, LR 추천만, ordered list           |
| v2.3   | max_change_pct 지표별, stale 72h, bias total≥5, universe 고정, W_j_suggested 적용 위치 확정                             |
| v2.3.1 | max_valid_value, 금리/RSI 권장값 수정, None→0.0 확정, effective_window                                                  |

---

## 1. 최종 확정 모델: 3-Stage Pipeline

```
[Data Validation]      [Stage 1]              [Stage 2]              [Stage 3]
데이터 검증            지표 → 점수            전제 점수 집계          가설 상태 판정
━━━━━━━━━━━━━         ━━━━━━━━━━━━          ━━━━━━━━━━━━          ━━━━━━━━━━━━━
null/finite/stale  →   Robust Z + Decay   →   가중평균           →   Rule-Based
min/max_valid          [-1, 1] 점수화         + 중복 경고(P+T)       상태 전환
max_change_pct         지표별 ε/window/λ      + 최약고리 경고        + 리마인더
asof (72h)             effective_window
                       mad_floor 보호
```

---

## 2. Stage 0: Data Validation Layer

### 2.1 Validation 규칙

> **v2.3.2 변경:** 순서 확정 (stale→jump), isfinite 추가, latest_reading_value 정의 명확화.

```python
import math

def validate_reading(indicator, raw_value, asof: datetime, fetched_at: datetime = None) -> tuple[bool, str]:
    """
    데이터 유효성 검증. (is_valid, reason) 반환.

    asof: 이 값이 실제로 대표하는 시각. None이면 fetched_at으로 대체.
    fetched_at: API 호출 시각. asof가 None인 데이터 소스의 fallback.

    검증 순서 (v2.3.2 확정):
      1. null       — 값 자체가 없음
      2. non_finite — NaN/inf (API 오류)
      3. min/max    — 범위 벗어남 (API 오류)
      4. stale      — 데이터가 오래됨 (★ jump보다 먼저. stale로 jump 비교하면 무의미)
      5. jump       — 전일 대비 급변 (정상 데이터끼리만 비교)
    """
    # 1. null
    if raw_value is None:
        return False, 'null_value'

    # 2. NaN/inf (v2.3.2)
    if not math.isfinite(raw_value):
        return False, 'non_finite'

    # 3. 범위 체크
    if indicator.min_valid_value is not None and raw_value < indicator.min_valid_value:
        return False, 'below_minimum'
    if indicator.max_valid_value is not None and raw_value > indicator.max_valid_value:
        return False, 'above_maximum'

    # 4. 신선도 (72시간) — ★ jump보다 먼저
    # asof가 None이면 fetched_at을 대체 사용 (데이터 소스가 asof를 못 줄 때)
    effective_asof = asof or fetched_at
    if effective_asof and (now() - effective_asof).total_seconds() > 259200:
        return False, 'stale_data'

    # 5. 전일 대비 급변 — stale이 아닌 정상 데이터끼리만 비교
    prev = indicator.latest_validated_value  # v2.3.2: last validated reading
    if prev is not None and prev != 0:
        threshold = indicator.max_change_pct or 0.5
        change_pct = abs((raw_value - prev) / prev)
        if change_pct > threshold:
            if indicator.allow_extreme_jump:
                return True, 'extreme_jump_allowed'
            return False, 'extreme_jump'

    return True, 'ok'
```

### 2.2 `latest_validated_value` 정의 (v2.3.2 확정)

```
┌──────────────────────────────────────────────────────────────────────┐
│  latest_validated_value = 마지막으로 validation을 통과한 reading의 값  │
│                                                                      │
│  통과 기준: validation_status가 'ok' 또는 'extreme_jump_allowed'      │
│                                                                      │
│  skip된 값(null, below_minimum, above_maximum, non_finite,           │
│  extreme_jump, stale_data)은 prev로 인정하지 않음.                    │
│                                                                      │
│  이유: skip된 값이 prev가 되면 다음 validation의 jump 비교가 꼬임.   │
│  예: 오류값 0 → skip → 다음날 정상값 100 → change_pct=∞ → false jump │
└──────────────────────────────────────────────────────────────────────┘
```

**구현:**

```python
# ThesisIndicator에 필드가 아닌 프로퍼티로 구현 (DB 필드 추가 불필요)
@property
def latest_validated_value(self):
    """마지막으로 validation 통과한 reading의 value"""
    reading = self.readings.filter(
        validation_status__in=['ok', 'extreme_jump_allowed']
    ).order_by('-asof').first()
    return reading.value if reading else None
```

### 2.3 Validation 실패 시 처리

```python
VALIDATION_ACTIONS = {
    'null_value':             'skip',
    'non_finite':             'skip',   # v2.3.2
    'below_minimum':          'skip',
    'above_maximum':          'skip',
    'stale_data':             'skip',
    'extreme_jump':           'skip',
    'extreme_jump_allowed':   'save',
}
```

### 2.4 max_change_pct + min/max_valid_value 권장값

| 지표 유형      | max_change_pct | min_valid | max_valid | 근거                      |
| -------------- | -------------- | --------- | --------- | ------------------------- |
| 개별종목 주가  | 0.5            | 0         | null      | 상한가/하한가             |
| 지수 (KOSPI)   | 0.15           | 0         | null      | 서킷브레이커              |
| VIX            | 0.5            | 5         | 90        | 5미만/90초과는 오류       |
| 금리 (%)       | 0.08           | 0         | 30        | 8%면 24bp 변화 감지       |
| 환율 (원/달러) | 0.1            | 800       | 2000      | 범위 밖은 오류            |
| RSI            | null (off)     | 0         | 100       | 범위 고정, 급변은 시그널  |
| MACD           | null (off)     | null      | null      | isfinite로 NaN/inf만 방어 |
| 감성 점수      | 0.5            | -1        | 1         | -1~1 범위                 |

### 2.5 Stale Data 알림

```python
def check_stale_indicators(thesis):
    for ind in thesis.active_indicators:
        latest = ind.readings.filter(
            validation_status__in=['ok', 'extreme_jump_allowed']
        ).order_by('-asof').first()
        if latest and (now() - latest.asof).total_seconds() > 259200:
            create_alert(thesis=thesis, type='stale_data', severity='low',
                         message=f'"{ind.name}" 데이터가 72시간째 업데이트되지 않았어요')
```

### 2.6 extreme_jump vs extreme_volatility 구분 (정의 확정)

```
┌──────────────────────────────────────────────────────────────────────┐
│  extreme_jump (Stage 0 — Data Validation)                           │
│  ─────────────────────────────────────                              │
│  목적: 데이터 품질/이상치 방어                                       │
│  동작: 저장 자체를 막음 (skip). 값이 DB에 안 들어감.                │
│  기준: max_change_pct 초과 (전일 대비 변화율)                       │
│  의미: "이 값은 진짜인지 의심스럽다"                                │
│                                                                      │
│  extreme_volatility (Stage 1 — Indicator Scoring)                   │
│  ─────────────────────────────────────────                          │
│  목적: 정상 데이터이지만 사건급 변동 알림                            │
│  동작: 저장은 함. 점수도 정상 계산(-1~1). 별도 경고만 생성.         │
│  기준: |z_raw| >= 5.0 (Robust Z-score 기준)                         │
│  의미: "이 값은 진짜인데, 시장에서 뭔가 크게 터졌다"               │
│                                                                      │
│  핵심 차이: jump는 "가짜 데이터 차단", vol은 "진짜 사건 알림"       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Stage 1: 지표 → 점수 (Indicator Scoring)

### 3.1 핵심 공식: Robust Z-score + Exponential Decay

```
z_i = (x_i - median_N) / (1.4826 × MAD_N + ε)    ... Robust Z-score

s_decayed = Σ(w_k × z_k) / Σ(w_k)                 ... Decay 가중 평균
            where w_k = λ^(t_now - t_k)

s = clip(s_decayed, -3, 3) / 3                     ... [-1, 1]로 정규화
```

### 3.2 파라미터

```python
EPSILON_DEFAULTS = {
    'market_data': 0.01, 'macro': 0.5, 'sentiment': 0.01,
    'technical': 1.0, 'fundamental': 0.01, 'custom': 0.01,
}

def get_scoring_params(indicator) -> dict:
    return {
        'epsilon': indicator.epsilon or EPSILON_DEFAULTS.get(indicator.indicator_type, 0.01),
        'window': indicator.window or 20,
        'decay': indicator.decay or 0.95,
    }
```

### 3.3 MAD Floor 보호 (v2.3.2)

> **v2.3.2 추가:** mad가 사실상 0이면 z-score가 과폭발. 전역 floor로 방어.

```python
MAD_FLOOR = 1e-9  # 전역 상수. 이 미만이면 "변동 없음"으로 처리.
```

**동작:**

- `mad < MAD_FLOOR`이면 score=0.0(중립), label='변동 없음' 반환
- 이유: 거의 고정된 값의 지표(예: 고정금리 기간)에서 미세한 차이로 z=1000이 나오는 걸 방지
- epsilon이 있어도 `mad≈0 + 작은 epsilon`이면 z가 과도하게 커질 수 있음
- MAD_FLOOR는 "이 지표는 지금 움직이지 않고 있다"는 판정

### 3.4 Extreme Volatility / 방향 반영 / 수동 오버라이드

```python
def check_extreme_volatility(z_raw, indicator):
    if abs(z_raw) >= 5.0:
        return {'flag': 'extreme_volatility', 'severity': 'critical',
                'z_raw': z_raw,
                'message': f'⚡ {indicator.name}에서 극단적 변동 감지 (z={z_raw:.1f}σ)'}
    return None

# support_direction
if indicator.support_direction == 'negative':
    s = -s

# 오버라이드
def score_indicator_with_override(indicator, readings, dates):
    if indicator.is_paused:
        return {'score': 0.0, 'degree': 90, 'label': '일시정지됨',
                'color': '#9CA3AF', 'is_paused': True}
    if indicator.override_score is not None:
        if indicator.override_at and (now() - indicator.override_at).days > 7:
            indicator.override_score = None
            indicator.save()
        else:
            s = indicator.override_score
            degree = 90 - (s * 90)
            label, color = _degree_to_label_color(degree)
            return {'score': s, 'degree': degree, 'label': label,
                    'color': color, 'is_override': True}
    params = get_scoring_params(indicator)
    return score_indicator(readings, dates, indicator.support_direction, **params)
```

### 3.5 화살표 각도/색상/라벨

```python
degree = 90 - (s × 90)

COLOR_MAP = [
    (0,   36,  '#2563EB', '강하게 지지'),
    (36,  72,  '#60A5FA', '지지하는 편'),
    (72,  108, '#9CA3AF', '중립'),
    (108, 144, '#FB923C', '약화하는 편'),
    (144, 180, '#DC2626', '강하게 반박'),
]
```

### 3.6 구현 (Python)

```python
import numpy as np
from datetime import date

MAD_FLOOR = 1e-9  # v2.3.2

def score_indicator(readings: list[float],
                    dates: list[date],
                    support_direction: str,
                    epsilon: float = 0.01,
                    window: int = 20,
                    decay: float = 0.95) -> dict:
    """지표 원시값 → Robust Z → 점수(-1~1) + 화살표(0°~180°)"""

    effective_window = min(window, len(readings))

    if effective_window < 5:
        return {'score': 0.0, 'degree': 90, 'label': '데이터 부족',
                'color': '#9CA3AF', 'is_sufficient': False}

    arr = np.array(readings[-effective_window:])
    dt = dates[-effective_window:]

    # Robust Z-score (MAD)
    med = np.median(arr)
    mad = np.median(np.abs(arr - med))

    # v2.3.2: MAD Floor — 거의 안 움직이는 지표 보호
    if mad < MAD_FLOOR:
        return {'score': 0.0, 'degree': 90, 'label': '변동 없음',
                'color': '#9CA3AF', 'is_sufficient': True,
                'z_raw': 0.0, 'robust_sigma': float(epsilon),
                'extreme_volatility': False, 'effective_window': effective_window}

    robust_sigma = 1.4826 * mad + epsilon
    z_scores = (arr - med) / robust_sigma

    # Extreme Vol (clip 전)
    z_raw = float(z_scores[-1])
    extreme_flag = abs(z_raw) >= 5.0

    # Decay-weighted average
    today = dt[-1]
    weights = np.array([decay ** (today - d).days for d in dt])
    s_decayed = np.average(z_scores, weights=weights)

    # Clip & normalize
    s = np.clip(s_decayed, -3, 3) / 3

    if support_direction == 'negative':
        s = -s

    degree = 90 - (s * 90)
    label, color = _degree_to_label_color(degree)

    return {
        'score': round(float(s), 4),
        'degree': round(float(degree), 1),
        'label': label,
        'color': color,
        'z_raw': round(z_raw, 4),
        'robust_sigma': round(float(robust_sigma), 4),
        'extreme_volatility': extreme_flag,
        'is_sufficient': True,
        'effective_window': effective_window,
    }
```

### 3.7 설계 근거

| 선택                   | 선택 이유                                  |
| ---------------------- | ------------------------------------------ |
| **Robust Z (MAD)**     | Fat-tail 방어                              |
| Exponential Decay      | 칼만필터보다 10배 간단                     |
| Clip ±3σ               | 3σ 밖은 Extreme Vol로 별도 처리            |
| 지표별 ε/window/decay  | VIX≠금리≠환율                              |
| 지표별 max_change_pct  | 금리 8% vs 주가 50%                        |
| min/max_valid_value    | API 오류 양방향 방어                       |
| effective_window       | 데이터 < window 시 안전 처리               |
| **MAD_FLOOR** (v2.3.2) | 고정값 지표에서 z 과폭발 방지              |
| **isfinite** (v2.3.2)  | NaN/inf가 numpy 계산 전체를 죽이는 것 방지 |

---

## 4. Stage 2: 전제 점수 집계 (Premise Aggregation)

### 4.1 전제별 / 가설 전체 점수

```
P_j = Σ(w_ij × s_i) / Σ(w_ij)     (MVP: w_ij = 1.0)
T   = Σ(W_j × P_j) / Σ(W_j)
```

| extraction_level | W_j |
| ---------------- | --- |
| explicit         | 1.0 |
| implicit         | 0.8 |
| ai_suggested     | 0.6 |

### 4.2 보조 경고 1: 카테고리 중복 (premise + thesis)

```python
TYPE_LABELS = {
    'market_data': '시장 데이터', 'macro': '거시경제',
    'sentiment': '뉴스 심리', 'technical': '기술적 분석',
    'fundamental': '기본적 분석', 'custom': '사용자 정의',
}

def check_indicator_diversity_premise(premise):
    types = [ind.indicator_type for ind in premise.active_indicators]
    duplicates = {t: c for t, c in Counter(types).items() if c >= 2}
    if duplicates:
        dup_names = [f'{TYPE_LABELS.get(t,t)} {c}개' for t, c in duplicates.items()]
        return {'type': 'indicator_overlap', 'scope': 'premise', 'severity': 'info',
                'message': f'같은 유형의 지표가 겹쳐요 ({", ".join(dup_names)}).'}
    return None

def check_indicator_diversity_thesis(thesis):
    all_types = [ind.indicator_type for p in thesis.active_premises for ind in p.active_indicators]
    total = len(all_types)
    if total < 5:
        return None
    dominant = {t: c for t, c in Counter(all_types).items() if c / total >= 0.6}
    if dominant:
        t, c = next(iter(dominant.items()))
        return {'type': 'indicator_bias', 'scope': 'thesis', 'severity': 'info',
                'message': f'전체 지표 {total}개 중 {TYPE_LABELS.get(t,t)}가 {c}개예요.'}
    return None
```

### 4.3 보조 경고 2: 최약고리 / 4.4 보조 경고 3: 불일치

```python
weakest = min(P_j for j in active_premises)
if weakest < -0.5:
    alert("⚠️ '{premise}'이(가) 강하게 반박되고 있어요")

if max(scores) - min(scores) > 1.2:
    alert("⚠️ 전제들이 서로 다른 방향을 가리키고 있어요")
```

---

## 5. Stage 3: 가설 상태 판정 (Thesis State Machine)

### 5.1 상태 정의

```python
THESIS_STATES = {
    'warming_up':       '데이터 수집 중',
    'active':           '활성 관제 중',
    'strengthening':    '가설 강화 추세',
    'weakening':        '가설 약화 추세',
    'critical':         '주의 필요',
    'needs_review':     '점검 필요',
    'expired':          '기간 만료',
    'closed_correct':   '사용자 마감 (적중)',
    'closed_incorrect': '사용자 마감 (미적중)',
    'closed_neutral':   '사용자 마감 (중립)',
}
```

### 5.2 상태 전환 규칙

```python
def determine_thesis_state(thesis, snapshots, data_coverage: float = 1.0):
    """
    data_coverage < 0.6이면 상태를 변경하지 않음 (현상 유지).
    점수는 계산되지만 "신뢰도 낮음"으로 취급.
    """
    if thesis.status.startswith('closed'):       return thesis.status

    # data_coverage가 낮으면 상태 변경 보류 (현상 유지)
    if data_coverage < 0.6:
        return thesis.status  # 기존 상태 그대로

    days = (now() - thesis.created_at).days
    if days < 5:                                 return 'warming_up'
    if thesis.expected_timeframe and now() > thesis.expected_timeframe:
        return 'expired'
    if not thesis.expected_timeframe and days > 90:
        if not thesis.last_review_reminded_at or \
           (now() - thesis.last_review_reminded_at).days > 30:
            return 'needs_review'

    recent = [s.overall_score for s in snapshots[-5:]]
    if len(recent) < 3:                          return 'active'
    current, trend = recent[-1], recent[-1] - recent[0]
    if len(recent) >= 2 and abs(recent[-1] - recent[-2]) > 0.3:  return 'critical'
    if trend > 0.15:                             return 'strengthening'
    if trend < -0.15:                            return 'weakening'
    if current < -0.6:                           return 'critical'
    return 'active'
```

### 5.3 마감 리마인더 / 5.4 Moon Phase

```python
REVIEW_ALERT = {
    'type': 'needs_review', 'severity': 'low',
    'message': '이 가설을 세운 지 90일이 지났어요. 아직 지켜보시나요?',
    'actions': ['연장할래요 (+90일)', '마감할래요', '계속 볼게요'],
}

def score_to_phase(score):
    if score > 0.6:   return {'phase': 'full_moon', 'label': '가설이 빛나고 있어요', 'icon': '🌕'}
    elif score > 0.2: return {'phase': 'waxing',    'label': '조금씩 밝아지고 있어요', 'icon': '🌔'}
    elif score > -0.2:return {'phase': 'half_moon', 'label': '반반이에요',             'icon': '🌓'}
    elif score > -0.6:return {'phase': 'waning',    'label': '조금씩 어두워지고 있어요','icon': '🌒'}
    else:             return {'phase': 'new_moon',  'label': '가설이 힘을 잃고 있어요', 'icon': '🌑'}
```

---

## 6. 알림(Alert) 생성 규칙

```python
ALERT_RULES = [
    # Stage 0
    {'type': 'stale_data',          'severity': 'low',      'condition': 'asof 기준 72시간 미갱신'},
    # Stage 1
    {'type': 'extreme_volatility',  'severity': 'critical', 'condition': '|z_raw| >= 5.0'},
    {'type': 'direction_flip',      'severity': 'high',     'condition': '어제 지지↔오늘 반박'},
    {'type': 'sharp_move',          'severity': 'high',     'condition': '|Δs| > 0.4 (1일)'},
    # Stage 2
    {'type': 'indicator_overlap',   'severity': 'info',     'condition': 'premise 내 같은 type 2+'},
    {'type': 'indicator_bias',      'severity': 'info',     'condition': 'thesis 한 type 60%+ (total≥5)'},
    {'type': 'weakest_link',        'severity': 'medium',   'condition': 'min(P_j) < -0.5'},
    {'type': 'premise_divergence',  'severity': 'medium',   'condition': 'max-min > 1.2'},
    # Stage 3
    {'type': 'state_change',        'severity': 'low',      'condition': 'status 변경'},
    {'type': 'milestone',           'severity': 'low',      'condition': 'overall ±0.5 첫 돌파'},
    {'type': 'needs_review',        'severity': 'low',      'condition': '기간 미설정 + 90일'},
]
```

---

## 7. 전체 데이터 흐름 (Celery 태스크)

```
[18:00 ET] update_indicator_readings
           │  1. fetch (asof 포함)
           │  2. Stage 0: validate (v2.3.2 순서: null→finite→min/max→stale→jump)
           │     - prev = latest_validated_value (last ok/allowed만)
           │  3. 유효 → Reading 생성, 무효 → skip
           │  4. stale 72h 체크
           ▼
[18:15 ET] calculate_scores
           │  Stage 1: Robust Z + Decay (effective_window, mad_floor 보호)
           │  Extreme Vol + Override 체크
           │  Stage 2: 가중평균 + 경고 (premise/thesis bias total≥5)
           │  → DB 업데이트
           ▼
[18:30 ET] create_snapshots_and_alerts
           │  Stage 3: 상태 판정 + needs_review
           │  ★ data_coverage 계산 → <0.6이면 상태 변경/알림 보류
           │  Snapshot (asof_date 기준, universe 고정, ordered list)
           │  ★ None = inactive("그날 안 썼다"), 학습 시 0.0(중립)
           │  Alert 생성 (throttling 적용)
           │  → Thesis.status 업데이트 (coverage≥0.6일 때만)
           ▼
[18:45 ET] 완료.
```

---

## 8. Phase별 진화 계획

### Phase 1 (MVP)

| 항목    | 내용                                                                                        |
| ------- | ------------------------------------------------------------------------------------------- |
| Stage 0 | Validation (순서 확정, isfinite, asof/72h, min/max_valid, max_change_pct, latest_validated) |
| Stage 1 | Robust Z + Decay, 지표별 params, effective_window, MAD_FLOOR                                |
| Stage 1 | Extreme Volatility + 수동 오버라이드                                                        |
| Stage 2 | 균등 가중평균 + 최약고리 + 불일치 + 중복 (premise+thesis, total≥5)                          |
| Stage 3 | Rule-based 상태 + 마감 리마인더 + **data_coverage 보류 규칙**                               |
| 스냅샷  | **asof_date 기준** + universe 고정 + ordered list + None→0.0 + data_coverage                |
| LLM     | 없음. 순수 수학                                                                             |

### Phase 2 (사용자 피드백 후)

| 항목                  | 내용                      |
| --------------------- | ------------------------- |
| 사용자 가중치         | (0.5, 1.0, 2.0)           |
| 상관계수 자동 할인    | 60일 \|ρ\|≥0.9 → 1/√k     |
| Adaptive Decay/Window | 변동성 높으면 λ↓, window↓ |
| Sustained Extreme     | s_decayed≥3 (clip전)      |
| 뉴스 센티먼트         | LLM→Stage 1 입력          |

### Phase 3 (마감 라벨 30건+)

| 항목                       | 내용                          |
| -------------------------- | ----------------------------- |
| Online Logistic Regression | correct/incorrect 학습        |
| **W_j_suggested (추천만)** | 운영 T에는 기본 W_j만         |
| 자동 적용                  | 100건+ & Safety Gate & opt-in |

```
┌─────────────────────────────────────────────────────────────────┐
│  운영 점수 (T):    기본 W_j만 사용 (1.0 / 0.8 / 0.6)          │
│  W_j_suggested:    UI "추천" 표시 전용                          │
│  자동 적용:        라벨 100건+ AND Safety Gate AND opt-in       │
└─────────────────────────────────────────────────────────────────┘
```

```python
class ThesisWeightLearner:
    def __init__(self, n, lr=0.01, l2=0.1):
        self.beta = np.zeros(n + 1)
        self.lr, self.l2 = lr, l2
    def predict(self, x):
        return 1.0 / (1.0 + np.exp(-(self.beta[0] + self.beta[1:] @ x)))
    def update(self, x, y):
        e = self.predict(x) - y
        self.beta[0] -= self.lr * e
        self.beta[1:] -= self.lr * (e * x + self.l2 * self.beta[1:])
    def get_suggested_weights(self):
        r = self.beta[1:]
        w = np.exp(r) / np.exp(r).sum() * len(r)
        return np.clip(w, 0.3, 3.0)

def should_deploy(old, new, val):
    if max(abs(n-o) for n,o in zip(new, old)) > 2.0: return False
    if evaluate(new, val) < evaluate(old, val) - 0.1: return False
    return True
```

### Phase 4 (장기)

| 항목         | 내용        |
| ------------ | ----------- |
| Change Point | ruptures    |
| 칼만 필터    | Stage 1     |
| MI           | 비선형 관계 |

---

## 9. 모델 필드 정의 (v2.3.2 확정)

### ThesisIndicator

```python
# 계산 파라미터
epsilon = FloatField(null=True, blank=True)
window = IntegerField(null=True, blank=True)
decay = FloatField(null=True, blank=True)

# Data Validation
min_valid_value = FloatField(null=True, blank=True)
max_valid_value = FloatField(null=True, blank=True)
max_change_pct = FloatField(null=True, blank=True)
allow_extreme_jump = BooleanField(default=False)

# 수동 오버라이드
is_paused = BooleanField(default=False)
override_score = FloatField(null=True, blank=True)
override_reason = CharField(max_length=200, blank=True)
override_at = DateTimeField(null=True, blank=True)

# v2.3.2: latest_validated_value는 프로퍼티(DB 필드 아님)
@property
def latest_validated_value(self):
    r = self.readings.filter(
        validation_status__in=['ok', 'extreme_jump_allowed']
    ).order_by('-asof').first()
    return r.value if r else None
```

### IndicatorReading

```python
asof = DateTimeField()
is_validated = BooleanField(default=True)
validation_status = CharField(max_length=25, default='ok')
# choices: ok, null_value, non_finite, below_minimum, above_maximum,
#          extreme_jump, extreme_jump_allowed, stale_data

class Meta:
    # 멱등성 보장: 동일 시점 데이터 중복 방지 (Section 12.1, 12.3)
    constraints = [
        models.UniqueConstraint(fields=['indicator', 'asof'], name='unique_reading_per_asof')
    ]
```

### Thesis

```python
last_review_reminded_at = DateTimeField(null=True, blank=True)
premise_universe_ids = JSONField(default=list)
indicator_universe_ids = JSONField(default=list)
```

### ThesisSnapshot

```python
premise_id_order = JSONField(default=list)
premise_scores = JSONField(default=list)       # 비활성→None
indicator_id_order = JSONField(default=list)
indicator_scores = JSONField(default=list)     # 비활성→None
overall_score_snapshot = FloatField(default=0.0)
days_active = IntegerField(default=0)

# 운영 정책 확정 필드
asof_date = DateField()                        # 이 스냅샷이 대표하는 거래일 (created_at이 아닌 EOD 기준)
data_coverage = FloatField(default=1.0)        # valid_count / expected_count (0.0~1.0)

class Meta:
    constraints = [
        models.UniqueConstraint(fields=['thesis', 'asof_date'], name='unique_snapshot_per_day')
    ]
```

### ThesisAlert (throttling 지원 필드 추가)

```python
# 기존 필드 (thesis_control_design.md 참조)
# id, thesis, type, severity, message, is_read, created_at

# throttling용 (Section 12.4 참조)
target_id = CharField(max_length=36, blank=True)  # 대상 indicator/premise의 UUID. thesis 레벨이면 빈 문자열.
cooldown_hours = IntegerField(default=24)          # COOLDOWN_HOURS에서 자동 설정
```

### Snapshot: inactive(None)의 의미 (v2.3.2 확정)

```
┌──────────────────────────────────────────────────────────────────────┐
│  snapshot.premise_scores 또는 indicator_scores에서 None의 의미:      │
│                                                                      │
│  None = "관측 불가/비활성".                                          │
│  즉, "그날은 그 전제/지표를 사용하지 않았다."                        │
│                                                                      │
│  ≠ "전제가 반박되었다" (반박은 음수 점수로 표현)                     │
│  ≠ "데이터 오류" (오류는 validation에서 이미 skip됨)                 │
│                                                                      │
│  학습 시 처리: None → 0.0 (중립)                                    │
│  이유: LR에서 "관측되지 않은 전제는 적중에 영향이 없다."            │
│  이 규칙은 모든 학습 파이프라인에서 동일하게 적용한다.               │
└──────────────────────────────────────────────────────────────────────┘
```

### Snapshot: asof_date + data_coverage 운영 정책 (확정)

```
┌──────────────────────────────────────────────────────────────────────┐
│  asof_date 정책:                                                     │
│                                                                      │
│  스냅샷의 날짜 기준은 created_at이 아닌 "asof_date(EOD 기준일)".    │
│  태스크가 새벽 1시에 돌아도, asof_date는 "어제"로 고정됨.           │
│  unique constraint: (thesis_id, asof_date).                          │
│  → 동일 거래일에 태스크 재실행 시 upsert로 안전.                    │
│                                                                      │
│  구현:                                                               │
│    asof_date = 그날 fetch된 reading들 중 가장 최근 asof의 date()    │
│    또는 명시적으로 US시장 기준 "오늘 거래일"을 계산                   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  data_coverage 정책:                                                 │
│                                                                      │
│  data_coverage = valid_indicator_count / total_active_indicator_count │
│                                                                      │
│  coverage >= 0.6:                                                    │
│    정상. 점수 계산 + 상태 판정 + 알림 모두 동작.                    │
│                                                                      │
│  coverage < 0.6:                                                     │
│    점수는 valid한 지표만으로 계산하되:                               │
│    - thesis.status 변경하지 않음 (현상 유지)                        │
│    - state_change/milestone 알림 보류                                │
│    - "데이터 부족" 알림만 low로 발송                                 │
│    - snapshot.data_coverage에 기록 (나중에 리플레이 시 필터 가능)    │
│                                                                      │
│  이유: 지표 10개 중 3개만 valid인데 T를 계산하면 사용자 신뢰 상실.  │
│  점수 자체는 나오지만 "신뢰도 낮음" 상태로 취급.                    │
└──────────────────────────────────────────────────────────────────────┘
```

### 파일 구조

```
thesis/services/
├── scoring/
│   ├── __init__.py
│   ├── data_validator.py       ← Stage 0 (순서 확정, isfinite, latest_validated)
│   ├── indicator_scorer.py     ← Stage 1 (Robust Z, MAD_FLOOR, effective_window)
│   ├── premise_aggregator.py   ← Stage 2
│   └── thesis_state_machine.py ← Stage 3
├── alert_engine.py
├── arrow_calculator.py
├── snapshot_builder.py         ← universe 고정 + ordered list
└── weight_learner.py           ← Phase 3 (파일만)
```

### 함수 목록

```python
# Stage 0
data_validator.validate_reading(indicator, raw_value, asof, fetched_at=None) -> (bool, str)
data_validator.check_stale_indicators(thesis) -> list[Alert]

# Stage 1
indicator_scorer.get_scoring_params(indicator) -> dict
indicator_scorer.score_indicator(readings, dates, direction, ε, window, decay) -> dict
indicator_scorer.score_indicator_with_override(indicator, readings, dates) -> dict
indicator_scorer.check_extreme_volatility(z_raw, indicator) -> Optional[dict]

# Stage 2
premise_aggregator.aggregate_premise(scores, weights) -> float
premise_aggregator.aggregate_thesis(premise_scores, weights) -> float
premise_aggregator.check_indicator_diversity_premise(premise) -> Optional[dict]
premise_aggregator.check_indicator_diversity_thesis(thesis) -> Optional[dict]
premise_aggregator.check_weakest_link(scores) -> Optional[Alert]
premise_aggregator.check_divergence(scores) -> Optional[Alert]

# Stage 3
thesis_state_machine.determine_state(thesis, snapshots, data_coverage) -> str
thesis_state_machine.score_to_phase(score) -> dict

# 스냅샷
snapshot_builder.build_snapshot_vectors(thesis, trading_date) -> dict
snapshot_builder.calculate_data_coverage(thesis) -> float

# 공통
arrow_calculator.score_to_degree(score) -> float
arrow_calculator.degree_to_color(degree) -> str
arrow_calculator.degree_to_label(degree) -> str
```

### Celery 태스크 (3개)

```python
@shared_task
def update_indicator_readings():
    """18:00 ET - Stage 0(순서 확정, latest_validated) + Reading"""

@shared_task
def calculate_scores():
    """18:15 ET - Stage 1(MAD_FLOOR, effective_window) + Stage 2"""

@shared_task
def create_snapshots_and_alerts():
    """18:30 ET - Stage 3 + Snapshot(asof_date, data_coverage, universe) + Alert(throttling)"""
```

---

## 11. 설계 원칙

1. **수학이 핵심, LLM은 옵션**
   - Phase 1: LLM 0회. 비용 예측 가능. LLM 장애 시 정상 동작.

2. **자동화 최우선**
   - Celery 3개, 매일 자동. 사람 개입 0.

3. **방어적 설계**
   - Validation 순서 확정 (v2.3.2): stale 데이터로 jump 비교 방지.
   - latest_validated_value (v2.3.2): skip된 값이 prev 오염 방지.
   - isfinite (v2.3.2): NaN/inf 방어.
   - MAD_FLOOR (v2.3.2): 고정값 지표 과민반응 방지.
   - min/max_valid_value: API 오류 양방향 방어.
   - max_change_pct: 지표별 정상 변동폭 반영.
   - extreme_jump=skip: MAD 오염 차단.
   - stale 72h: 주말 false positive 방지.
   - Extreme Volatility: 극단값 별도 경고.
   - 카테고리 중복: premise + thesis(total≥5).
   - effective_window: 데이터 부족 안전 처리.
   - 수동 오버라이드: 특수 상황 대응.
   - 마감 리마인더: 좀비 가설 방지.
   - **data_coverage < 0.6 → 상태 변경/알림 보류**: 데이터 부족 시 사용자 신뢰 보호.
   - **asof_date 기준 스냅샷**: 태스크 실행 시각과 무관하게 거래일 기준 일관성.

4. **점진적 강화**
   - Phase 1→2→3→4. 완전 호환.

5. **학습 대비 설계**
   - universe 고정: dimension 일관성.
   - ordered list: numpy 즉시 변환.
   - None→0.0 확정 + **inactive 의미 명문화** (v2.3.2).
   - W_j_suggested: 운영 점수 분리, UI 추천 전용.

---

## 12. 구현/운영 가이드 (수학 설계 동결 후 실전 체크리스트)

> 수학 모델(Section 1~9)은 v2.3.2로 동결.  
> 이 섹션은 구현 시 참조할 실전 규칙으로, 코드/인프라/UX 레벨의 조언.

### 12.1 데이터 수집: asof 표준화 규칙

```
┌──────────────────────────────────────────────────────────────────────┐
│  asof 표준화 (커넥터 레벨에서 고정)                                  │
│                                                                      │
│  EOD(종가) 데이터:                                                   │
│    US equities → America/New_York 16:00                              │
│    KR equities → Asia/Seoul 15:30                                    │
│                                                                      │
│  매크로/이벤트:                                                      │
│    발표 시각 또는 스냅샷 시각을 asof로 사용                          │
│                                                                      │
│  fetched_at:                                                         │
│    오로지 로그/디버깅용. stale 판단은 asof(또는 fallback) 기준.      │
│                                                                      │
│  중복 방지:                                                          │
│    (indicator_id, asof) 조합에 unique constraint.                    │
│    동일 시점 데이터가 두 번 들어오면 update_or_create로 upsert.      │
└──────────────────────────────────────────────────────────────────────┘
```

### 12.2 DB 인덱스 (필수 6개)

구현 시 반드시 Django Meta.indexes에 추가:

```python
# IndicatorReading
indexes = [
    models.Index(fields=['indicator', '-asof']),                          # 최신 reading 조회
    models.Index(fields=['indicator', 'validation_status', '-asof']),     # latest_validated_value
]

# ThesisSnapshot
indexes = [
    models.Index(fields=['thesis', '-created_at']),                      # 최근 스냅샷 조회
]

# ThesisAlert
indexes = [
    models.Index(fields=['thesis', '-created_at']),                      # 최근 알림 조회
]

# ThesisIndicator
indexes = [
    models.Index(fields=['thesis', 'is_active']),                        # 활성 지표 필터
]

# ThesisPremise
indexes = [
    models.Index(fields=['thesis', 'is_active']),                        # 활성 전제 필터
]
```

### 12.3 배치 태스크 안정성

**멱등성 (idempotent) 규칙:**

```python
# IndicatorReading: (indicator_id, asof) upsert
reading, created = IndicatorReading.objects.update_or_create(
    indicator=indicator,
    asof=asof,
    defaults={'value': raw_value, 'validation_status': status, ...}
)

# ThesisSnapshot: (thesis_id, asof_date) 1일 1개 — created_at이 아닌 asof_date 기준
snapshot, created = ThesisSnapshot.objects.update_or_create(
    thesis=thesis,
    asof_date=trading_date,  # EOD 기준 거래일
    defaults={...}
)
```

**실패 격리:**

```python
# 지표 하나 실패가 전체 태스크를 죽이지 않음
for indicator in thesis.active_indicators:
    try:
        raw_value, asof = fetch_indicator_value(indicator)
        is_valid, reason = validate_reading(indicator, raw_value, asof, fetched_at)
        if is_valid:
            save_reading(indicator, raw_value, asof, reason)
        else:
            log_skip(indicator, reason)
    except Exception as e:
        logger.error(f"[{indicator.name}] fetch 실패: {e}")
        continue  # 다음 지표로
```

**백필 (management command):**

```python
# MVP에서는 수동 management command로 충분
# python manage.py backfill_readings --indicator_id=xxx --start=2026-01-01 --end=2026-03-01
# 동일한 validate → upsert 로직 사용. 스코어 재계산은 선택.
```

### 12.4 알림 Throttling (필수)

```
┌──────────────────────────────────────────────────────────────────────┐
│  알림 발송 규칙 (과다 알림 = 제품 사망)                              │
│                                                                      │
│  1. 동일 type + 동일 대상: 24시간에 최대 1번                        │
│     예: indicator_A의 direction_flip → 24h 내 재발동 시 무시         │
│                                                                      │
│  2. stale_data: 해소될 때까지 1번만 (재알림 없음)                   │
│                                                                      │
│  3. extreme_volatility: 6시간에 최대 1번                            │
│     (시장 급변일에 모든 지표에서 동시 발동 방지)                     │
│                                                                      │
│  4. state_change 사용자 알림: critical/expired/needs_review만        │
│     strengthening/weakening/active 전환은 앱 내 feed에서만 표시     │
│     (매일 왔다갔다하면 알림 피로)                                    │
│                                                                      │
│  구현: alert 생성 전 최근 동일 alert 존재 여부 체크                 │
│                                                                      │
│  def should_send_alert(thesis, alert_type, target_id, cooldown_hours):│
│      exists = ThesisAlert.objects.filter(                            │
│          thesis=thesis, type=alert_type, target_id=target_id,        │
│          created_at__gte=now() - timedelta(hours=cooldown_hours)     │
│      ).exists()                                                      │
│      return not exists                                               │
│                                                                      │
│  COOLDOWN_HOURS = {                                                  │
│      'direction_flip': 24,                                           │
│      'sharp_move': 24,                                               │
│      'extreme_volatility': 6,                                        │
│      'weakest_link': 24,                                             │
│      'premise_divergence': 24,                                       │
│      'stale_data': 9999,  # 해소 시까지                              │
│      'indicator_overlap': 9999,                                      │
│      'indicator_bias': 9999,                                         │
│      'state_change': 24,                                             │
│      'milestone': 9999,                                              │
│      'needs_review': 720,  # 30일                                    │
│  }                                                                   │
│                                                                      │
│  USER_VISIBLE_ALERTS = {                                             │
│      'push/email': ['extreme_volatility', 'direction_flip',         │
│                     'sharp_move', 'weakest_link', 'critical',        │
│                     'expired', 'needs_review'],                      │
│      'feed_only':  ['state_change', 'milestone', 'indicator_overlap',│
│                     'indicator_bias', 'premise_divergence',          │
│                     'stale_data'],                                    │
│  }                                                                   │
└──────────────────────────────────────────────────────────────────────┘
```

### 12.5 support_direction 실수 방지

```
┌──────────────────────────────────────────────────────────────────────┐
│  지표 생성/추천 시 사용자에게 반드시 확인:                           │
│                                                                      │
│  "이 지표(VIX)가 오르면 당신의 가설(KOSPI 하락)에..."               │
│     [유리해요 ✅]  [불리해요 ❌]                                     │
│                                                                      │
│  AI 자동 추천 시에도 support_direction 이유를 표시:                  │
│     "VIX는 공포 지수예요. 올라가면 시장 하락 가능성이 커지니까      │
│      '유리' 방향으로 설정했어요."                                    │
│                                                                      │
│  처음 7일: "방향이 맞나요?" 확인 배너 표시                          │
│  이유: 방향이 반대면 시스템이 "정확하게 틀림" — 가장 위험한 버그     │
└──────────────────────────────────────────────────────────────────────┘
```

### 12.6 유닛테스트 필수 목록 (10개)

```python
# 구현 시 이 10개는 반드시 작성

# Stage 0 (Data Validation)
test_validate_null_returns_false()
test_validate_non_finite_nan_inf()
test_validate_below_minimum()
test_validate_above_maximum()
test_validate_stale_72h()
test_validate_extreme_jump_skip_vs_allowed()
test_latest_validated_value_skips_invalid_readings()

# Stage 1 (Indicator Scoring)
test_mad_floor_returns_neutral()
test_support_direction_flip()
test_decay_weights_by_date_gap()
test_effective_window_shorter_than_param()
test_extreme_volatility_flag_at_z5()

# Stage 2 (Premise Aggregation)
test_weakest_link_trigger()
test_divergence_trigger()
test_thesis_bias_skips_below_5_indicators()

# Stage 3 (State Machine)
test_warming_up_under_5_days()
test_critical_on_daily_change_03()
test_strengthening_on_5day_trend()
test_needs_review_at_90_days()

# Snapshot
test_snapshot_universe_preserves_dimension()
test_snapshot_inactive_is_none()
test_snapshot_asof_date_not_created_at()
test_snapshot_data_coverage_below_06_blocks_state_change()

# Alert
test_alert_throttling_blocks_duplicate()
test_alert_state_change_only_push_for_critical()
```

### 12.7 운영 모니터링 (로그 기반 6개 지표)

```python
# 각 Celery 태스크 종료 시 summary 로그 출력

# update_indicator_readings 완료 후:
logger.info(f"[EOD] fetch 완료: 성공={success}/{total}, "
            f"skip={{null={null_count}, stale={stale_count}, jump={jump_count}, "
            f"non_finite={nf_count}, below_min={bmin_count}, above_max={bmax_count}}}")

# calculate_scores 완료 후:
logger.info(f"[EOD] 스코어 계산: 지표={ind_count}, 전제={prem_count}, "
            f"extreme_vol={extreme_count}, override={override_count}")

# create_snapshots_and_alerts 완료 후:
logger.info(f"[EOD] 스냅샷={snap_count}, 알림 생성={alert_count} "
            f"(발송={sent_count}, throttled={throttled_count}), "
            f"coverage_low={low_coverage_count}, "
            f"실행시간={elapsed:.1f}s")
```

### 12.8 Phase 3 라벨 품질 가이드

```
┌──────────────────────────────────────────────────────────────────────┐
│  가설 마감 시 적중 판정 기준 (UX에서 한 줄로 고정):                 │
│                                                                      │
│  ✅ 적중(correct):                                                   │
│     "예상한 방향대로 의미있는 움직임이 있었다"                       │
│     예: "KOSPI 하락" 가설 → 실제 5% 이상 하락 발생                  │
│                                                                      │
│  ❌ 미적중(incorrect):                                               │
│     "예상과 반대 방향으로 움직였거나, 아무 일도 없었다"             │
│     예: "KOSPI 하락" 가설 → 오히려 상승 또는 횡보                    │
│                                                                      │
│  ➖ 중립(neutral): 학습에서 제외                                     │
│     "판단하기 어렵다 / 아직 진행 중이다"                            │
│                                                                      │
│  W_j_suggested 추천 시 해석 문구 예시:                               │
│     "최근 마감된 가설들에서, '{premise}' 전제의 점수가 높았던        │
│      가설이 더 자주 적중했어요. 이 전제의 가중치를 올려볼까요?"      │
└──────────────────────────────────────────────────────────────────────┘
```

### 12.9 전제 품질 가이드

```
┌──────────────────────────────────────────────────────────────────────┐
│  좋은 전제의 3요소 (가설 생성 UX에서 가이드):                       │
│                                                                      │
│  1. 관측 가능: 지표로 측정할 수 있는 것                              │
│     ✅ "외국인 순매도가 지속된다"                                    │
│     ❌ "시장 분위기가 안 좋다"                                       │
│                                                                      │
│  2. 방향 포함: 올라간다/내려간다/유지된다                            │
│     ✅ "VIX가 25 이상으로 상승한다"                                  │
│     ❌ "VIX가 변한다"                                                │
│                                                                      │
│  3. 기간 (가능하면): 언제까지                                        │
│     ✅ "3개월 내 기준금리가 인하된다"                                │
│     ○  기간 없어도 허용 (90일 리마인더가 대신 작동)                  │
└──────────────────────────────────────────────────────────────────────┘
```
