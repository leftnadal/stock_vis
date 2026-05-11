# Thesis Control — Phase 1 Claude Code 실행 프롬프트

> **참조 문서 위치:** `docs/thesis_control/`
>
> - `thesis_control_design.md` — UX/API/모델 설계
> - `thesis_control_math_model_final.md` — 수학 모델 v2.3.2
> - `thesis_control_integrated_roadmap.md` — 통합 로드맵 (특허 모델)
> - `thesis_control_implementation_guide.md` — 구현 순서 가이드
>
> **PR 분리 원칙:** 각 PR은 독립적으로 실행 가능해야 함. 이전 PR이 머지된 상태에서 다음 PR 시작.

---

## PR-1: Django 앱 뼈대 + 전체 모델 + Admin

> **범위:** Week 1~2 전체  
> **목표:** DB 스키마가 완성된 상태. 스코어링 엔진 없이 모델만.

---

### 📋 프롬프트

```
docs/thesis_control/thesis_control_design.md (섹션 4.1~4.2),
docs/thesis_control/thesis_control_math_model_final.md (Section 9),
docs/thesis_control/thesis_control_integrated_roadmap.md (섹션 1.2~1.4)
를 읽고, thesis/ Django 앱을 생성하고 전체 모델을 구현해줘.

─────────────────────────────────────────────
[1] 앱 구조 생성
─────────────────────────────────────────────

아래 구조로 thesis/ 앱을 생성해:

thesis/
├── models/
│   ├── __init__.py          # 모든 모델 re-export
│   ├── thesis.py
│   ├── indicator.py
│   ├── monitoring.py
│   ├── community.py
│   └── learning.py          # 특허 모델 (신규)
├── services/                # 빈 디렉토리 (PR-2에서 채움)
│   └── __init__.py
├── tasks/                   # 빈 디렉토리 (PR-4에서 채움)
│   └── __init__.py
├── views/                   # 빈 디렉토리 (PR-3에서 채움)
│   └── __init__.py
├── serializers/             # 빈 디렉토리 (PR-3에서 채움)
│   └── __init__.py
├── migrations/
│   └── __init__.py
├── admin.py
├── apps.py
└── urls.py                  # urlpatterns = [] 빈 상태

config/settings.py의 INSTALLED_APPS에 'thesis' 추가.

─────────────────────────────────────────────
[2] thesis/models/thesis.py
─────────────────────────────────────────────

설계 문서 4.2의 Thesis 모델을 기준으로 구현하되,
수학 모델 Section 9에 명시된 v2.3.2 추가 필드를 반드시 포함해:

class Thesis(models.Model):
  # 설계 문서 4.2 기준 필드 전부 포함:
  # id(UUID PK), user(FK), title, description, direction, target,
  # target_type, expected_timeframe, expected_magnitude,
  # target_date_start, target_date_end, thesis_type, entry_source,
  # source_news(FK→news.NewsArticle, null), copied_from(FK→self, null),
  # status(setting_up/active/closed/paused), current_state(warming_up/
  # active/strengthening/weakening/critical/expired/needs_review/paused),
  # current_score(Float, null), created_at, updated_at, closed_at(null),
  # outcome(null/correct/incorrect/neutral), outcome_note

  # v2.3.2 추가 필드 (수학 모델 Section 9):
  # premise_universe_ids(JSONField, default=list) — 스냅샷 고정용
  # indicator_universe_ids(JSONField, default=list) — 스냅샷 고정용

  class Meta:
    indexes = [
      Index(fields=['user', '-created_at']),
      Index(fields=['user', 'status']),
      Index(fields=['status', '-created_at']),
    ]

class ThesisPremise(models.Model):
  # id(UUID PK), thesis(FK), content(TextField), category(CharField)
  # choices: macro/sector/company/technical/sentiment/custom
  # weight(Float, default=1.0), is_active(Bool, default=True)
  # order(Int, default=0), created_at

  # v2.3.2 추가 필드:
  # is_paused(Bool, default=False) — 이 전제만 일시정지

─────────────────────────────────────────────
[3] thesis/models/indicator.py
─────────────────────────────────────────────

class ThesisIndicator(models.Model):
  # 설계 문서 4.2 기준:
  # id(UUID PK), thesis(FK), premise(FK→ThesisPremise, null, blank)
  # name, indicator_type(market_data/macro/technical/sentiment/custom)
  # data_source(CharField: fmp/fred/news_sentiment/manual/custom)
  # data_params(JSONField) — {"symbol": "^VIX"} 등 API 호출 파라미터
  # support_direction(positive/negative) — 오르면 가설에 유리/불리
  # weight(Float, default=1.0), is_active(Bool, default=True)
  # current_score(Float, null), current_degree(Float, null)
  # current_color(CharField, null), current_label(CharField, null)
  # created_at

  # v2.3.2 추가 필드 (수학 모델 Section 9):
  # epsilon(Float, default=0.0001)    — Robust Z 분모 보호
  # window(Int, default=60)           — 히스토리 윈도우 (일)
  # decay(Float, default=0.95)        — 지수 감쇠 λ
  # min_valid_value(Float, null)      — 범위 하한 (VIX: 5)
  # max_valid_value(Float, null)      — 범위 상한 (VIX: 90)
  # max_change_pct(Float, null)       — 전일 대비 최대 허용 변화율
  # allow_extreme_jump(Bool, default=False)  — 급변 허용 여부
  # is_paused(Bool, default=False)    — 일시정지
  # override_score(Float, null)       — 수동 오버라이드 점수

  @property
  def latest_validated_value(self):
    """마지막으로 validation 통과한 reading의 value (수학 모델 Section 2.2)"""
    reading = self.readings.filter(
      validation_status__in=['ok', 'extreme_jump_allowed']
    ).order_by('-asof').first()
    return reading.value if reading else None

  class Meta:
    indexes = [
      Index(fields=['thesis', 'is_active']),
    ]

class IndicatorReading(models.Model):
  # id(UUID PK), indicator(FK→ThesisIndicator)
  # value(Float), raw_value(Float)  — raw는 원본, value는 검증 통과한 값
  # asof(DateTimeField) — 이 값이 실제로 대표하는 시각

  # v2.3.2 추가 필드 (수학 모델 Section 9):
  # validation_status(CharField)
  #   choices: ok/null_value/non_finite/below_minimum/above_maximum/
  #            stale_data/extreme_jump/extreme_jump_allowed
  # fetched_at(DateTimeField, auto_now_add=True)

  class Meta:
    unique_together = ['indicator', 'asof']   # 수학 모델 12.2
    indexes = [
      Index(fields=['indicator', '-asof']),
    ]
    ordering = ['-asof']

─────────────────────────────────────────────
[4] thesis/models/monitoring.py
─────────────────────────────────────────────

class ThesisSnapshot(models.Model):
  # id(UUID PK), thesis(FK)

  # v2.3.2 추가 필드 (수학 모델 Section 9):
  # asof_date(DateField) — 스냅샷이 대표하는 날짜 (created_at과 별도)
  # data_coverage(Float, default=1.0) — 유효 지표 비율 (0~1)
  # universe_snapshot(JSONField, default=dict)
  #   — {indicator_id: score_or_None} (universe 고정, 비활성=None)
  # ordered_indicator_ids(JSONField, default=list) — 순서 고정

  # 기존 필드:
  # date(DateField), overall_score(Float), state(CharField)
  # premise_scores(JSONField) — {premise_id: score}
  # indicator_degrees(JSONField) — {indicator_id: degree}
  # notable_changes(JSONField, default=list)
  # ai_summary(TextField, blank=True)

  class Meta:
    unique_together = ['thesis', 'asof_date']  # 수학 모델 12.2
    ordering = ['-asof_date']

class ThesisAlert(models.Model):
  # 설계 문서 4.2 기준에서 확장:
  # id(UUID PK), thesis(FK), indicator(FK→ThesisIndicator, null, blank)
  # alert_type(CharField, 수학 모델 12.4 기준)
  #   choices: direction_flip/sharp_move/extreme_volatility/weakest_link/
  #            premise_divergence/stale_data/indicator_overlap/
  #            indicator_bias/state_change/milestone/needs_review
  # severity(CharField): low/medium/high/critical

  # v2.3.2 추가 필드 (수학 모델 Section 9):
  # target_id(CharField, blank=True)  — throttling 기준 대상 ID
  # cooldown_hours(Int, default=24)   — throttling 쿨다운

  # 기존 필드:
  # title(CharField), message(TextField)
  # is_read(Bool, default=False), is_pushed(Bool, default=False)
  # created_at(DateTimeField, auto_now_add=True)

  class Meta:
    indexes = [
      Index(fields=['thesis', 'alert_type', 'target_id', '-created_at']),
      Index(fields=['thesis', 'is_read']),
    ]
    ordering = ['-created_at']

─────────────────────────────────────────────
[5] thesis/models/community.py
─────────────────────────────────────────────

설계 문서 4.2의 ThesisFollow, PopularThesisCache 그대로 구현.
변경 없음.

─────────────────────────────────────────────
[6] thesis/models/learning.py  (신규 — 특허 모델)
─────────────────────────────────────────────

통합 로드맵 섹션 1.2~1.4를 그대로 구현:

1) HypothesisEvent — 사용자 행동 이벤트 스트림
   - 통합 로드맵 1.2의 전체 코드 그대로
   - event_type choices 13개 전부 포함
   - 인덱스 3개 전부 포함

2) ValidityRecord — 가설 마감 시 지표 유효성 기록
   - 통합 로드맵 1.3의 전체 코드 그대로
   - 2×2 매트릭스 score 필드 포함
   - 인덱스 1개 포함

3) InvestorDNA — 사용자 투자 성향 프로파일
   - 통합 로드맵 1.4의 전체 코드 그대로
   - Phase 1 기본 통계 필드 전부 포함
   - Phase 2 미리 생성 필드(personalization_weight 등) 포함
   - updated_at(DateTimeField, auto_now=True) 추가

─────────────────────────────────────────────
[7] thesis/models/__init__.py
─────────────────────────────────────────────

모든 모델 re-export:
from .thesis import Thesis, ThesisPremise
from .indicator import ThesisIndicator, IndicatorReading
from .monitoring import ThesisSnapshot, ThesisAlert
from .community import ThesisFollow, PopularThesisCache
from .learning import HypothesisEvent, ValidityRecord, InvestorDNA

─────────────────────────────────────────────
[8] thesis/admin.py
─────────────────────────────────────────────

모든 모델을 admin에 등록. 각 모델별 기본 ModelAdmin 설정:

- Thesis: list_display=['title','user','status','current_state','created_at']
          list_filter=['status','current_state','thesis_type','direction']
          search_fields=['title','user__email']

- ThesisPremise: list_display=['thesis','content','category','weight','is_active']

- ThesisIndicator: list_display=['thesis','name','indicator_type','support_direction',
                                  'current_score','is_active']
                   list_filter=['indicator_type','data_source','is_active']

- IndicatorReading: list_display=['indicator','value','asof','validation_status']
                    list_filter=['validation_status']
                    date_hierarchy='asof'

- ThesisSnapshot: list_display=['thesis','asof_date','overall_score','state','data_coverage']
                  date_hierarchy='asof_date'

- ThesisAlert: list_display=['thesis','alert_type','severity','is_read','is_pushed','created_at']
               list_filter=['alert_type','severity','is_read','is_pushed']

- HypothesisEvent: list_display=['user','thesis','event_type','created_at']
                   list_filter=['event_type']
                   date_hierarchy='created_at'

- ValidityRecord: list_display=['thesis','indicator','thesis_type',
                                 'indicator_aligned','thesis_correct','score']

- InvestorDNA: list_display=['user','total_theses','correct_count','updated_at']

ThesisFollow, PopularThesisCache도 기본 등록.

─────────────────────────────────────────────
[9] 마이그레이션
─────────────────────────────────────────────

python manage.py makemigrations thesis
python manage.py migrate

마이그레이션 파일에서 수동으로 아래 인덱스들이 포함됐는지 확인:
- IndicatorReading: unique_together ['indicator', 'asof']
- ThesisSnapshot: unique_together ['thesis', 'asof_date']
- ThesisAlert: index on (thesis, alert_type, target_id, created_at)
- HypothesisEvent: 3개 인덱스 (user+created_at, thesis+event_type, event_type+created_at)

─────────────────────────────────────────────
[주의사항]
─────────────────────────────────────────────
- services/, tasks/, views/, serializers/ 는 이번 PR에서 내용 없이 생성만
- news.NewsArticle FK는 null=True, blank=True로 설정 (news 앱이 없을 수도 있음)
- 모든 UUID 필드는 import uuid; uuid.uuid4 사용
- from django.utils import timezone 사용 (now() 대신)
```

---

## PR-2: 스코어링 엔진 (services/)

> **범위:** Week 2~3  
> **전제조건:** PR-1 머지 완료  
> **목표:** Stage 0~3 파이프라인 + 알림 엔진 + 스냅샷 빌더 완성. 순수 Python 로직, DB 읽기만.

---

### 📋 프롬프트

```
docs/thesis_control/thesis_control_math_model_final.md 전체를 읽고,
thesis/services/ 아래에 스코어링 엔진 7개 파일을 구현해줘.

─────────────────────────────────────────────
구현할 파일 목록
─────────────────────────────────────────────

thesis/services/
├── data_validator.py      # Stage 0: Data Validation
├── indicator_scorer.py    # Stage 1: Robust Z + Decay
├── premise_aggregator.py  # Stage 2: 가중평균 + 경고
├── thesis_state_machine.py # Stage 3: 상태 결정
├── alert_engine.py        # 알림 생성 + throttling
├── arrow_calculator.py    # degree/color/label 변환
└── snapshot_builder.py    # 스냅샷 생성

─────────────────────────────────────────────
[1] data_validator.py — Stage 0
─────────────────────────────────────────────

수학 모델 Section 2 전체를 그대로 구현.

def validate_reading(indicator, raw_value, asof, fetched_at=None) -> tuple[bool, str]:
  """
  검증 순서 (v2.3.2 확정):
  1. null → 'null_value'
  2. math.isfinite → 'non_finite'
  3. min_valid_value / max_valid_value → 'below_minimum' / 'above_maximum'
  4. stale (72h) → 'stale_data'   ★ jump보다 먼저
  5. extreme_jump → 'extreme_jump' or 'extreme_jump_allowed'
  """
  import math
  from django.utils import timezone

  # 수학 모델 Section 2.1의 코드를 정확히 따를 것
  # asof가 None이면 fetched_at을 fallback으로 사용
  # STALE_THRESHOLD = 72 * 3600 초 (259200)

VALIDATION_ACTIONS = {
  'null_value': 'skip',
  'non_finite': 'skip',
  'below_minimum': 'skip',
  'above_maximum': 'skip',
  'stale_data': 'skip',
  'extreme_jump': 'skip',
  'extreme_jump_allowed': 'save',
  'ok': 'save',
}

─────────────────────────────────────────────
[2] indicator_scorer.py — Stage 1
─────────────────────────────────────────────

수학 모델 Section 3 전체를 구현.

def score_indicator(indicator, as_of_date=None) -> dict:
  """
  반환: {
    'score': float,          # -1.0 ~ 1.0 (support_direction 반영 후)
    'raw_z': float,          # Robust Z 원본
    'is_extreme_vol': bool,  # |z_clipped| >= 3 기준
    'effective_window': int, # 실제 사용된 window 크기
    'is_neutral_mad': bool,  # MAD_FLOOR 발동 여부
  }
  """

  구현 요구사항 (수학 모델 Section 3):
  1. IndicatorReading에서 validation_status IN ['ok','extreme_jump_allowed'] 조건으로만 조회
  2. effective_window = min(indicator.window, 실제 데이터 수)
  3. Decay 가중치: w_t = decay^(days_gap) 로 계산 (최신일수록 높음)
  4. Weighted Median으로 중앙값(mu_w) 계산
  5. MAD = weighted_median(|x - mu_w|)
  6. MAD_FLOOR 적용: mad < epsilon 이면 neutral(0.0) 반환
  7. Robust Z = (latest_value - mu_w) / (1.4826 * mad)
  8. Clip: z_clipped = clip(z, -3, 3)
  9. score = z_clipped / 3 (→ -1~1 범위)
  10. Extreme Vol: |z_clipped| >= 3 → is_extreme_vol = True
  11. support_direction='negative'이면 score 부호 반전
  12. is_paused=True 또는 override_score 있으면 그 값 사용

─────────────────────────────────────────────
[3] premise_aggregator.py — Stage 2
─────────────────────────────────────────────

수학 모델 Section 4 전체를 구현.

def aggregate_premise(premise, indicator_scores: dict) -> dict:
  """
  indicator_scores: {indicator_id: score_or_None}
  반환: {
    'score': float,
    'weakest_link': Optional[dict],   # 최약고리 경고
    'divergence': bool,               # 불일치 경고
    'category_overlap': bool,         # 카테고리 중복 경고 (전제 레벨)
  }
  """

def aggregate_thesis(thesis, premise_scores: dict, indicator_scores: dict) -> dict:
  """
  반환: {
    'overall_score': float,
    'premise_scores': dict,
    'weakest_link': Optional[dict],
    'divergence_count': int,
    'thesis_bias_warning': bool,       # total 지표 수 >= 5일 때만
    'category_overlap_count': int,     # 논문 레벨 카테고리 중복
  }
  """

  구현 요구사항 (수학 모델 Section 4):
  1. inactive 지표(is_active=False 또는 is_paused=True)는 None으로 처리
  2. None 점수는 0.0으로 대체하여 가중평균 계산 (수학 모델 12.1: None→0.0 확정)
  3. 최약고리: 지표 중 score < -0.5인 것이 1개 이상이고 overall > 0 → 경고
  4. 불일치: 전제 내 지표들 중 양수/음수 혼재 비율 >= 0.3 → 경고
  5. Thesis Bias: 총 지표 수 >= 5일 때만 활성화 (수학 모델 Section 4, total≥5 조건)

─────────────────────────────────────────────
[4] thesis_state_machine.py — Stage 3
─────────────────────────────────────────────

수학 모델 Section 5 전체를 구현.

def determine_state(thesis, overall_score: float, prev_score: float,
                    data_coverage: float, days_active: int,
                    score_history: list[float]) -> dict:
  """
  반환: {
    'state': str,            # warming_up/active/strengthening/weakening/
                              # critical/expired/needs_review/paused
    'state_changed': bool,
    'reminder_needed': bool,
  }
  """

  구현 요구사항 (수학 모델 Section 5):
  1. data_coverage < 0.6 → 상태 전환 보류 ('active' 유지)
  2. days_active < 5 → 'warming_up'
  3. thesis.is_paused → 'paused' (Thesis 모델에 is_paused 필드 없으면 status='paused' 체크)
  4. overall_score <= -0.7 → 'critical'
  5. target_date_end 지났으면 → 'expired'
  6. days_active >= 90 → 'needs_review'
  7. 5일 연속 score 증가 추세 → 'strengthening'
  8. 5일 연속 score 감소 추세 → 'weakening'
  9. 그 외 → 'active'
  10. 일일 score 변화 >= 0.3 → 'critical' 후보 (수학 모델 12.7 기준)

─────────────────────────────────────────────
[5] alert_engine.py — 알림 생성 + throttling
─────────────────────────────────────────────

수학 모델 Section 12.4 전체를 구현.

COOLDOWN_HOURS = {
  'direction_flip': 24,
  'sharp_move': 24,
  'extreme_volatility': 6,
  'weakest_link': 24,
  'premise_divergence': 24,
  'stale_data': 9999,
  'indicator_overlap': 9999,
  'indicator_bias': 9999,
  'state_change': 24,
  'milestone': 9999,
  'needs_review': 720,
}

USER_VISIBLE_ALERTS = {
  'push_email': ['extreme_volatility', 'direction_flip', 'sharp_move',
                  'weakest_link', 'critical', 'expired', 'needs_review'],
  'feed_only': ['state_change', 'milestone', 'indicator_overlap',
                 'indicator_bias', 'premise_divergence', 'stale_data'],
}

def should_send_alert(thesis, alert_type: str, target_id: str,
                      cooldown_hours: int) -> bool:
  """ThesisAlert에서 cooldown 체크. 수학 모델 12.4 코드 그대로."""

def create_alert_if_needed(thesis, alert_type: str, title: str,
                           message: str, indicator=None,
                           target_id: str = '') -> Optional[ThesisAlert]:
  """throttling 통과 시에만 ThesisAlert 생성. 반환: 생성된 alert or None"""

def check_and_create_alerts(thesis, scoring_result: dict,
                             prev_snapshot=None) -> list[ThesisAlert]:
  """
  scoring_result로부터 발생할 알림 전체 처리.
  체크 항목:
  - extreme_volatility: scoring_result['extreme_vol_indicators']가 있을 때
  - direction_flip: 이전 스냅샷 대비 degree 방향 전환한 지표
  - sharp_move: |score 변화| >= 0.4
  - weakest_link: scoring_result['weakest_link'] 있을 때
  - premise_divergence: scoring_result['divergence_count'] > 0
  - stale_data: check_stale_indicators() 결과 (수학 모델 Section 2.5)
  - state_change: thesis.current_state != new_state
  - needs_review: days_active >= 90
  """

def check_stale_indicators(thesis) -> list[ThesisIndicator]:
  """72시간 이상 validated reading이 없는 지표 목록 반환"""

─────────────────────────────────────────────
[6] arrow_calculator.py
─────────────────────────────────────────────

수학 모델에서 score → 화살표 시각화 변환.
설계 문서 Section 5.4도 참조.

def score_to_degree(score: float) -> float:
  """score(-1~1) → degree(0~180). score=1→0°, score=0→90°, score=-1→180°"""
  return 90 - (score * 90)

def degree_to_color(degree: float) -> str:
  """
  0~45   → 'strong_red'   (강한 지지)
  45~75  → 'red'          (지지)
  75~105 → 'gray'         (중립)
  105~135→ 'blue'         (약화)
  135~180→ 'strong_blue'  (강한 반박)
  """

def degree_to_label(degree: float) -> str:
  """
  0~30   → '강하게 지지'
  30~60  → '지지하는 중'
  60~80  → '살짝 지지'
  80~100 → '중립'
  100~120→ '살짝 약화'
  120~150→ '약화 중'
  150~180→ '강하게 반박'
  """

def calculate_indicator_arrow(indicator) -> dict:
  """
  ThesisIndicator 하나에 대한 전체 화살표 계산.
  indicator_scorer.score_indicator() 호출 후 변환.
  반환: {score, degree, color, label, is_extreme_vol}
  """

─────────────────────────────────────────────
[7] snapshot_builder.py
─────────────────────────────────────────────

수학 모델 Section 9 전체를 구현.

def build_snapshot(thesis, as_of_date=None) -> ThesisSnapshot:
  """
  구현 요구사항 (수학 모델 Section 9):
  1. as_of_date가 None이면 오늘 날짜 사용
  2. Universe 고정: thesis.indicator_universe_ids 사용
     - 비어있으면 현재 활성 지표 ID 목록으로 초기화 후 저장
  3. universe 내 각 지표에 대해:
     - is_active=True → indicator_scorer로 score 계산
     - is_active=False 또는 is_paused=True → None (비활성, 학습 제외)
  4. None→0.0 대체는 aggregate_thesis()에서만 (스냅샷 자체는 None 보존)
  5. data_coverage = 유효 score가 있는 지표 수 / universe 전체 수
  6. ThesisSnapshot.unique_together = ['thesis', 'asof_date'] 충돌 시 update
  7. notable_changes: 이전 스냅샷 대비 |score 변화| >= 0.3인 지표 목록
  반환: 저장된 ThesisSnapshot 인스턴스
  """

─────────────────────────────────────────────
[주의사항]
─────────────────────────────────────────────
- 모든 서비스 함수는 순수 함수 또는 최소 DB 의존 (읽기만)
  단, create_alert_if_needed / build_snapshot은 DB write 허용
- 외부 API 호출 없음. IndicatorReading에서 읽는 것만.
- import 경로는 from thesis.models import ... 사용
- 각 파일 상단에 간단한 docstring으로 "수학 모델 v2.3.2, Section X 구현" 명시
```

---

## PR-3: API + 대화형 빌더

> **범위:** Week 3~4  
> **전제조건:** PR-1, PR-2 머지 완료  
> **목표:** 가설 CRUD, 전제/지표 CRUD, 대화형 빌더, 관제실 대시보드 API 완성

---

### 📋 프롬프트

```
docs/thesis_control/thesis_control_design.md (섹션 2.3, 5.2, 6.1~6.2)를 읽고,
thesis/ 앱의 API 레이어를 구현해줘.

LLM 호출에는 Gemini 2.5 Flash를 사용해.
기존 프로젝트에 Gemini 연동 유틸이 있으면 그걸 재사용하고,
없으면 google-generativeai SDK 기준으로 구현해.

─────────────────────────────────────────────
[1] thesis/services/indicator_matcher.py
─────────────────────────────────────────────

설계 문서 5.2를 기반으로 구현.

def match_indicators_for_premise(premise_text: str, thesis: Thesis,
                                  user=None) -> list[dict]:
  """
  전제 텍스트 → 지표 추천 목록 반환.
  전략:
  1. 키워드 룰 매칭 (먼저, 빠름):
     - "외국인" → data_source='fmp', indicator_type='market_data'
     - "금리", "연준" → data_source='fred', indicator_type='macro'
     - "VIX", "공포" → VIX 지표
     - "환율", "달러" → USD/KRW
     - "RSI", "MACD", "기술" → indicator_type='technical'
     - "센티먼트", "여론", "뉴스" → indicator_type='sentiment'
  2. 키워드 룰로 못 매칭되면 Gemini 2.5 Flash fallback:
     - 프롬프트: "투자 전제: '{premise_text}'. 이 전제를 측정할 수 있는
       금융 지표 3~5개를 JSON 배열로 추천해줘. 각 항목: name, data_source,
       data_params, indicator_type, support_direction, reason"
     - JSON 파싱 실패 시 빈 리스트 반환 (에러 전파 없음)
  반환: [{'name': str, 'data_source': str, 'data_params': dict,
          'indicator_type': str, 'support_direction': str, 'reason': str}, ...]
  """

─────────────────────────────────────────────
[2] thesis/services/thesis_builder.py
─────────────────────────────────────────────

설계 문서 2.3 경로 1(오늘 이슈), 경로 2(내 생각)만 구현.
대화형 플로우: 단계별 상태 머신.

ConversationState를 dataclass 또는 dict로 관리:
{
  'entry_source': 'news' | 'free_input',
  'step': int,                    # 현재 단계
  'collected': dict,              # 수집된 데이터
  'source_news_id': Optional[str],
}

def start_conversation(entry_source: str, source_news_id=None,
                       user=None) -> dict:
  """
  대화 시작. 첫 번째 메시지와 버튼 선택지 반환.
  entry_source='news' → 뉴스 카드 선택 후 방향 질문 단계로
  entry_source='free_input' → "어떤 가설을 세울까요?" 부터
  반환 형식: 설계 문서 6.2 "대화 응답" JSON 형식 그대로
  """

def process_response(conversation_state: dict, user_input: str | list,
                     user=None) -> dict:
  """
  사용자 선택/입력 처리 → 다음 단계 메시지 반환.
  단계 진행:
  경로 1 (news):
    step 1: 뉴스 → 방향 선택 (상승/하락/중립)
    step 2: 방향 → "왜 그렇게 생각하세요?" (전제 선택, multi)
    step 3: 전제 → "언제쯤 예상하세요?" (timeframe, 선택/건너뜀)
    step 4: timeframe → "강도는?" (선택/건너뜀)
    step 5: 최종 → Gemini로 thesis 구조화 + indicator 추천
    step 6: 확인 → Thesis 생성 → {'thesis_id': ..., 'done': True}

  경로 2 (free_input):
    step 1: 자유 입력 → Gemini로 가설 파싱 (target, direction 추출)
    step 2: 파싱 결과 확인 (맞으면 다음, 틀리면 수정)
    step 3: "왜 그렇게 생각하세요?" (전제 선택/직접입력)
    step 4~6: 경로 1의 step 3~6과 동일

  step 5에서 Gemini 호출:
  - 수집된 데이터로 Thesis 필드 추출
  - 각 전제에 대해 indicator_matcher.match_indicators_for_premise() 호출
  - 추천 지표 목록도 응답에 포함

  conversation_state는 Redis에 저장 (키: 'thesis_conv:{user_id}:{conv_id}')
  없으면 메모리(dict) fallback도 OK (MVP)
  """

─────────────────────────────────────────────
[3] thesis/serializers/__init__.py + 각 serializer
─────────────────────────────────────────────

thesis/serializers/thesis_serializers.py:
- ThesisListSerializer (list용, 핵심 필드만)
- ThesisDetailSerializer (상세용, 전제/지표 포함)
- ThesisCreateSerializer (생성용, 필수 필드)

thesis/serializers/indicator_serializers.py:
- ThesisIndicatorSerializer
- IndicatorReadingSerializer

thesis/serializers/monitoring_serializers.py:
- ThesisSnapshotSerializer
- ThesisAlertSerializer

thesis/serializers/conversation_serializers.py:
- ConversationStartSerializer (request)
- ConversationResponseSerializer (request)

─────────────────────────────────────────────
[4] thesis/views/ + ViewSet 구현
─────────────────────────────────────────────

thesis/views/thesis_views.py:
class ThesisViewSet(ModelViewSet):
  """
  list   → GET /              내 가설 목록 (status 필터 지원)
  create → POST /             가설 직접 생성 (대화형 아닌 경우)
  retrieve → GET /{id}/       가설 상세
  partial_update → PATCH /{id}/ 가설 수정
  close  → POST /{id}/close/  가설 마감
    - outcome 필수 (correct/incorrect/neutral)
    - ValidityRecord 생성 (통합 로드맵 1.3)
    - InvestorDNA 갱신 (통합 로드맵 1.4, signal or 직접)
    - HypothesisEvent('thesis_closed', 'outcome_correct/incorrect/neutral') 기록
  """

class ThesisPremiseViewSet(ModelViewSet):
  """
  부모: thesis/{thesis_id}/premises/
  list, create, partial_update, destroy
  - create 시 HypothesisEvent('premise_added') 기록
  - destroy 시 HypothesisEvent('premise_removed') 기록
  """

class ThesisIndicatorViewSet(ModelViewSet):
  """
  부모: thesis/{thesis_id}/indicators/
  list, create, partial_update, destroy
  + auto_recommend: POST /indicators/auto/
    - premise_id를 받아 indicator_matcher.match_indicators_for_premise() 호출
    - HypothesisEvent('ai_suggestion_shown') 기록
  - create 시 source 체크: AI 추천 수락이면 HypothesisEvent('ai_suggestion_accepted')
  - destroy 시 HypothesisEvent('indicator_removed') 기록
  """

thesis/views/conversation_views.py:
class ConversationView(APIView):
  """
  POST /conversation/start/   → thesis_builder.start_conversation()
  POST /conversation/respond/ → thesis_builder.process_response()
  """

thesis/views/monitoring_views.py:
class DashboardView(APIView):
  """
  GET /{thesis_id}/dashboard/
  반환: 설계 문서 6.2의 관제실 대시보드 JSON 형식 그대로
  - thesis 기본 정보
  - indicators: 각 지표의 현재 arrow_degree, color, label, trend
  - heatmap: cells 배열
  - Phase 1에서는 카드뷰용 데이터만 (히트맵 기본 포함, 그래프는 Phase 2)
  """

class AlertListView(APIView):
  """
  GET /alerts/           내 알림 목록 (미읽음 우선, 최대 50개)
  PATCH /alerts/{aid}/read/  읽음 처리
  """

─────────────────────────────────────────────
[5] thesis/urls.py
─────────────────────────────────────────────

router = DefaultRouter()
router.register('', ThesisViewSet, basename='thesis')
router.register(r'(?P<thesis_id>[^/.]+)/premises', ThesisPremiseViewSet, basename='premise')
router.register(r'(?P<thesis_id>[^/.]+)/indicators', ThesisIndicatorViewSet, basename='indicator')

urlpatterns = [
  path('', include(router.urls)),
  path('conversation/start/', ConversationView.as_view({'post': 'start'})),
  path('conversation/respond/', ConversationView.as_view({'post': 'respond'})),
  path('<uuid:thesis_id>/dashboard/', DashboardView.as_view()),
  path('alerts/', AlertListView.as_view()),
  path('alerts/<uuid:aid>/read/', AlertReadView.as_view()),
]

config/urls.py에 path('api/v1/thesis/', include('thesis.urls')) 추가.

─────────────────────────────────────────────
[주의사항]
─────────────────────────────────────────────
- 모든 API는 JWT 인증 필수 (기존 프로젝트 인증 방식 그대로)
- thesis owner 체크: thesis.user == request.user (403 반환)
- Gemini 호출 실패 시 에러 전파 말고 graceful fallback (빈 리스트/기본값)
- HypothesisEvent.objects.create()는 try-except로 감싸서 API 실패 방지
- DashboardView는 snapshot_builder나 indicator_scorer를 직접 호출해서
  실시간으로 계산 (캐싱은 Phase 2)
```

---

## PR-4: Celery 태스크 + 이벤트 수집 완성

> **범위:** Week 4~5  
> **전제조건:** PR-1~3 머지 완료  
> **목표:** 3개 EOD Celery 태스크 + 이벤트 수집 코드 삽입 + ValidityRecord/DNA 자동화

---

### 📋 프롬프트

```
docs/thesis_control/thesis_control_math_model_final.md (Section 7, 12.3, 12.7)과
docs/thesis_control/thesis_control_implementation_guide.md (Week 4~5)를 읽고,
thesis/tasks/ 아래에 Celery 태스크 3개를 구현하고
기존 API 코드에 이벤트 수집을 완성해줘.

─────────────────────────────────────────────
[1] thesis/tasks/eod_pipeline.py
─────────────────────────────────────────────

수학 모델 Section 7의 실행 순서대로 3개 태스크 구현.

@shared_task(bind=True, max_retries=3)
def update_indicator_readings(self):
  """
  실행: 매일 18:00 ET (장 마감 후)
  대상: status='active'인 모든 Thesis의 is_active=True 지표

  구현:
  1. active 가설 조회
  2. 각 지표의 data_source, data_params로 외부 API에서 최신 값 fetch
     - data_source='fmp' → FMP API (기존 fetch 유틸 재사용)
     - data_source='fred' → FRED API (기존 fetch 유틸 재사용)
     - data_source='manual' → skip
  3. data_validator.validate_reading() 호출
  4. validation_status='ok' or 'extreme_jump_allowed' → IndicatorReading upsert
     - upsert 기준: unique_together (indicator, asof)
     - 멱등성: 이미 존재하면 update (수학 모델 12.3)
  5. validation_status='skip' 계열 → IndicatorReading 저장하되
     value=None, validation_status=reason 으로 기록 (감사 추적용)

  완료 후 summary 로그 (수학 모델 12.7):
  logger.info(f"[EOD] fetch 완료: 성공={success}/{total}, "
              f"skip={{null={null_count}, stale={stale_count},
              jump={jump_count}, non_finite={nf_count},
              below_min={bmin_count}, above_max={bmax_count}}}")
  """

@shared_task(bind=True, max_retries=3)
def calculate_scores(self):
  """
  실행: 매일 18:15 ET (update_indicator_readings 완료 후)
  대상: status='active'인 모든 Thesis

  구현:
  1. 각 지표에 대해 indicator_scorer.score_indicator() 호출
  2. ThesisIndicator.current_score, current_degree, current_color,
     current_label 업데이트 (bulk_update 사용)
  3. Extreme Vol 지표 목록 수집
  4. Override 지표 카운트
  5. premise_aggregator.aggregate_thesis() 호출
  6. Thesis.current_score 업데이트

  완료 후 summary 로그:
  logger.info(f"[EOD] 스코어 계산: 지표={ind_count}, 전제={prem_count}, "
              f"extreme_vol={extreme_count}, override={override_count}")
  """

@shared_task(bind=True, max_retries=3)
def create_snapshots_and_alerts(self):
  """
  실행: 매일 18:30 ET
  대상: status='active'인 모든 Thesis

  구현:
  1. snapshot_builder.build_snapshot() 호출 → ThesisSnapshot 생성
  2. data_coverage 계산
  3. thesis_state_machine.determine_state() 호출
  4. state 변경 시 Thesis.current_state 업데이트
  5. alert_engine.check_and_create_alerts() 호출
     - 이전 스냅샷 조회 후 비교
     - throttling 적용하여 ThesisAlert 생성
  6. push/email 알림: USER_VISIBLE_ALERTS['push_email'] 타입만
     (실제 발송은 기존 notification 시스템 연결, 없으면 로그만)

  완료 후 summary 로그:
  logger.info(f"[EOD] 스냅샷={snap_count}, 알림 생성={alert_count} "
              f"(발송={sent_count}, throttled={throttled_count}), "
              f"coverage_low={low_coverage_count}, 실행시간={elapsed:.1f}s")
  """

─────────────────────────────────────────────
[2] config/celery_beat_schedule 업데이트
─────────────────────────────────────────────

config/settings.py 또는 config/celery.py의 CELERY_BEAT_SCHEDULE에 추가:

'thesis-update-readings': {
  'task': 'thesis.tasks.eod_pipeline.update_indicator_readings',
  'schedule': crontab(hour=18, minute=0),  # ET 기준
},
'thesis-calculate-scores': {
  'task': 'thesis.tasks.eod_pipeline.calculate_scores',
  'schedule': crontab(hour=18, minute=15),
},
'thesis-create-snapshots': {
  'task': 'thesis.tasks.eod_pipeline.create_snapshots_and_alerts',
  'schedule': crontab(hour=18, minute=30),
},

─────────────────────────────────────────────
[3] ValidityRecord 자동 생성 (가설 마감 시)
─────────────────────────────────────────────

PR-3에서 만든 ThesisViewSet.close() 액션을 수정:

def close(self, request, pk=None):
  thesis = self.get_object()
  outcome = request.data.get('outcome')  # correct/incorrect/neutral
  thesis_correct = (outcome == 'correct')

  # 각 활성 지표에 대해 ValidityRecord 생성 (통합 로드맵 1.3)
  for indicator in thesis.indicators.filter(is_active=True):
    indicator_aligned = (indicator.current_score or 0) > 0
    score = _compute_validity_score(indicator_aligned, thesis_correct)
    # score 계산: 2×2 매트릭스
    # aligned=True + correct=True → +0.3
    # aligned=True + correct=False → -0.2
    # aligned=False + correct=True → -0.15
    # aligned=False + correct=False → +0.05
    ValidityRecord.objects.create(
      thesis_type=thesis.thesis_type,
      indicator_data_key=_get_data_key(indicator),  # data_params에서 key 추출
      market_regime=_get_current_market_regime(),    # VIX 기준 (phase 1: 'normal' 고정)
      indicator_aligned=indicator_aligned,
      thesis_correct=thesis_correct,
      score=score,
      thesis=thesis,
      indicator=indicator,
    )

  # InvestorDNA 갱신 (통합 로드맵 1.4)
  _update_investor_dna(thesis.user, thesis, outcome)

  # HypothesisEvent 기록
  HypothesisEvent.objects.create(
    user=thesis.user, thesis=thesis,
    event_type='thesis_closed',
    event_data={'duration_days': (now().date()-thesis.created_at.date()).days}
  )
  outcome_event_map = {
    'correct': 'outcome_correct',
    'incorrect': 'outcome_incorrect',
    'neutral': 'outcome_neutral',
  }
  HypothesisEvent.objects.create(
    user=thesis.user, thesis=thesis,
    event_type=outcome_event_map[outcome],
    event_data={'outcome_return': request.data.get('outcome_return', None)}
  )

  thesis.status = 'closed'
  thesis.outcome = outcome
  thesis.closed_at = now()
  thesis.save()
  return Response({'status': 'closed'})

def _update_investor_dna(user, thesis, outcome):
  """InvestorDNA 집계 갱신. get_or_create 사용."""
  dna, _ = InvestorDNA.objects.get_or_create(user=user)
  dna.total_theses = Thesis.objects.filter(user=user).count()
  dna.closed_theses = Thesis.objects.filter(user=user, status='closed').count()
  dna.correct_count = HypothesisEvent.objects.filter(
    user=user, event_type='outcome_correct'
  ).count()
  dna.incorrect_count = HypothesisEvent.objects.filter(
    user=user, event_type='outcome_incorrect'
  ).count()
  # premise_category_counts 집계
  from django.db.models import Count
  cats = HypothesisEvent.objects.filter(
    user=user, event_type='premise_added'
  ).values_list('event_data__category', flat=True)
  dna.premise_category_counts = _count_dict(cats)
  # indicator_type_counts 집계
  types = HypothesisEvent.objects.filter(
    user=user, event_type='indicator_added'
  ).values_list('event_data__indicator_type', flat=True)
  dna.indicator_type_counts = _count_dict(types)
  # AI 수락률
  dna.ai_suggestions_shown = HypothesisEvent.objects.filter(
    user=user, event_type='ai_suggestion_shown'
  ).count()
  dna.ai_suggestions_accepted = HypothesisEvent.objects.filter(
    user=user, event_type='ai_suggestion_accepted'
  ).count()
  dna.save()

─────────────────────────────────────────────
[주의사항]
─────────────────────────────────────────────
- 각 태스크는 try-except로 개별 가설 실패 격리 (수학 모델 12.3)
  → 1개 가설 처리 실패가 전체 태스크 실패로 이어지지 않게
- 외부 API fetch 유틸은 기존 프로젝트 것을 재사용
  (없으면 data_source별 placeholder 함수로 남겨두기)
- market_regime은 Phase 1에서 항상 'normal' 고정 (Phase 2에서 VIX 연동)
- _get_data_key()는 data_params에서 symbol/series_id 등 핵심 키 추출
```

---

## PR-5: 테스트 + 안정화

> **범위:** Week 5~6  
> **전제조건:** PR-1~4 머지 완료  
> **목표:** 수학 모델 12.6의 필수 테스트 25개 + 통합 테스트 + 운영 점검

---

### 📋 프롬프트

```
docs/thesis_control/thesis_control_math_model_final.md (Section 12.6)를 읽고,
thesis/tests/ 아래에 유닛 테스트와 통합 테스트를 작성해줘.

─────────────────────────────────────────────
[1] thesis/tests/test_data_validator.py
─────────────────────────────────────────────

수학 모델 12.6의 Stage 0 테스트 전부 구현:

class TestValidateReading(TestCase):
  def setUp(self):
    # ThesisIndicator mock/fixture 생성
    # min_valid_value=5, max_valid_value=90, max_change_pct=0.5 설정

  def test_validate_null_returns_false(self):
    is_valid, reason = validate_reading(indicator, None, now())
    self.assertFalse(is_valid)
    self.assertEqual(reason, 'null_value')

  def test_validate_non_finite_nan_inf(self):
    for val in [float('nan'), float('inf'), float('-inf')]:
      is_valid, reason = validate_reading(indicator, val, now())
      self.assertFalse(is_valid)
      self.assertEqual(reason, 'non_finite')

  def test_validate_below_minimum(self):
    is_valid, reason = validate_reading(indicator, 4.9, now())
    self.assertFalse(is_valid)
    self.assertEqual(reason, 'below_minimum')

  def test_validate_above_maximum(self):
    is_valid, reason = validate_reading(indicator, 90.1, now())
    self.assertFalse(is_valid)
    self.assertEqual(reason, 'above_maximum')

  def test_validate_stale_72h(self):
    stale_asof = now() - timedelta(hours=73)
    is_valid, reason = validate_reading(indicator, 20.0, stale_asof)
    self.assertFalse(is_valid)
    self.assertEqual(reason, 'stale_data')

  def test_stale_checked_before_jump(self):
    # stale + 급변이 동시에 → stale이 먼저 잡혀야 함
    stale_asof = now() - timedelta(hours=73)
    # 이전 값 30, 현재 값 100 (급변)
    # 하지만 stale이 먼저이므로 reason='stale_data'
    ...

  def test_validate_extreme_jump_skip_vs_allowed(self):
    # allow_extreme_jump=False → 'extreme_jump' (skip)
    # allow_extreme_jump=True → 'extreme_jump_allowed' (save)
    ...

  def test_latest_validated_value_skips_invalid_readings(self):
    # null, stale, jump 등으로 skip된 reading은 latest_validated_value에서 제외
    ...

─────────────────────────────────────────────
[2] thesis/tests/test_indicator_scorer.py
─────────────────────────────────────────────

class TestIndicatorScorer(TestCase):
  def test_mad_floor_returns_neutral(self):
    # 모든 readings가 동일한 값 → MAD≈0 → score=0.0, is_neutral_mad=True

  def test_support_direction_flip(self):
    # support_direction='negative'이면 score 부호 반전

  def test_decay_weights_by_date_gap(self):
    # 최근 reading이 오래된 것보다 더 높은 가중치를 가져야 함

  def test_effective_window_shorter_than_param(self):
    # 데이터가 window보다 적으면 effective_window = 실제 데이터 수

  def test_extreme_volatility_flag_at_z5(self):
    # |Robust Z| >= 3 (clip 전) → is_extreme_vol=True

─────────────────────────────────────────────
[3] thesis/tests/test_premise_aggregator.py
─────────────────────────────────────────────

class TestPremiseAggregator(TestCase):
  def test_weakest_link_trigger(self):
    # 지표 중 score=-0.6 있고 overall > 0 → weakest_link 경고

  def test_divergence_trigger(self):
    # 양수/음수 혼재 비율 >= 0.3 → divergence=True

  def test_thesis_bias_skips_below_5_indicators(self):
    # 지표 수 4개 → thesis_bias_warning=False
    # 지표 수 5개 → 활성화

─────────────────────────────────────────────
[4] thesis/tests/test_state_machine.py
─────────────────────────────────────────────

class TestThesisStateMachine(TestCase):
  def test_warming_up_under_5_days(self):
    result = determine_state(..., days_active=3, ...)
    self.assertEqual(result['state'], 'warming_up')

  def test_critical_on_daily_change_03(self):
    # score 변화 >= 0.3 → 'critical'

  def test_strengthening_on_5day_trend(self):
    # 5일 연속 score 증가 → 'strengthening'

  def test_needs_review_at_90_days(self):
    result = determine_state(..., days_active=90, ...)
    self.assertEqual(result['state'], 'needs_review')

─────────────────────────────────────────────
[5] thesis/tests/test_snapshot_builder.py
─────────────────────────────────────────────

class TestSnapshotBuilder(TestCase):
  def test_snapshot_universe_preserves_dimension(self):
    # universe 고정 후 지표 추가해도 스냅샷 차원 유지

  def test_snapshot_inactive_is_none(self):
    # is_active=False 지표 → universe_snapshot에서 None

  def test_snapshot_asof_date_not_created_at(self):
    # asof_date가 오늘 날짜 (created_at이 아님)

  def test_snapshot_data_coverage_below_06_blocks_state_change(self):
    # data_coverage < 0.6 → state_machine에서 상태 전환 보류

─────────────────────────────────────────────
[6] thesis/tests/test_alert_engine.py
─────────────────────────────────────────────

class TestAlertEngine(TestCase):
  def test_alert_throttling_blocks_duplicate(self):
    # 동일 type + 동일 target_id → cooldown 내 재생성 차단

  def test_alert_state_change_only_push_for_critical(self):
    # state_change='strengthening' → feed_only (push 안 함)
    # state_change='critical' → push/email 발송

─────────────────────────────────────────────
[7] thesis/tests/test_integration.py
─────────────────────────────────────────────

class TestThesisFullCycle(TestCase):
  """가설 생성 → 모니터링 → 마감 → 이벤트/유효성 기록 확인"""

  def test_full_cycle(self):
    # 1. 유저 생성
    # 2. Thesis 생성 (API POST /api/v1/thesis/)
    # 3. ThesisPremise 추가
    # 4. ThesisIndicator 추가 (with IndicatorReading 3개)
    # 5. calculate_scores 태스크 직접 호출
    # 6. build_snapshot() 호출
    # 7. Thesis.close() 호출 (outcome='correct')
    # 검증:
    # - ThesisSnapshot이 생성됐는지
    # - ValidityRecord가 각 지표별 1건씩 생성됐는지
    # - InvestorDNA가 갱신됐는지 (correct_count=1)
    # - HypothesisEvent가 thesis_closed + outcome_correct 2건 있는지

─────────────────────────────────────────────
[8] 안정화 점검 체크리스트 확인
─────────────────────────────────────────────

아래 항목들을 직접 코드에서 검증하고 문제 있으면 수정:

1. IndicatorReading unique_together ['indicator', 'asof'] → 마이그레이션에 있는지
2. ThesisSnapshot unique_together ['thesis', 'asof_date'] → 마이그레이션에 있는지
3. ThesisAlert throttling: should_send_alert() 함수가 target_id 기반으로 동작하는지
4. HypothesisEvent.objects.create()가 try-except로 감싸져 있는지 (API 실패 방지)
5. Celery 태스크의 개별 가설 실패 격리 (루프 내 try-except)
6. 수학 모델 12.7 summary 로그가 3개 태스크 모두에 있는지

─────────────────────────────────────────────
[주의사항]
─────────────────────────────────────────────
- 테스트에서 외부 API 호출은 unittest.mock.patch로 mock 처리
- Celery 태스크 테스트는 CELERY_TASK_ALWAYS_EAGER=True 설정
- TestCase는 django.test.TestCase 사용 (트랜잭션 롤백)
- 픽스처보다 setUp()에서 직접 객체 생성 권장 (유연성)
- 테스트 실행: python manage.py test thesis --verbosity=2
```

---

## 실행 순서 요약

```
PR-1  Django 앱 + 모델 + Admin
  ↓ 머지
PR-2  스코어링 엔진 (services/)
  ↓ 머지
PR-3  API + 대화형 빌더
  ↓ 머지
PR-4  Celery 태스크 + 이벤트 수집
  ↓ 머지
PR-5  테스트 + 안정화
  ↓ 머지

Phase 1 완료 체크리스트:
✅ 가설 생성 (경로 1: 오늘 이슈, 경로 2: 내 생각)
✅ AI가 지표 3~5개 자동 추천
✅ 매일 18:00 ET 지표 자동 업데이트 (Robust Z + Decay)
✅ 화살표/색상/라벨로 가설 상태 표시 (카드뷰)
✅ 변화 감지 시 알림 (throttling 적용)
✅ 가설 마감 → 적중/미적중 판정
✅ 모든 행동이 HypothesisEvent로 기록
✅ 마감 시 ValidityRecord + InvestorDNA 자동 축적
✅ 25개 이상 유닛 테스트 통과
```

---

## 각 프롬프트 실행 팁

- **PR-1 실행 전:** `python manage.py showmigrations`로 기존 마이그레이션 상태 확인
- **PR-2 실행 전:** `thesis/models/` 임포트가 정상 동작하는지 `python manage.py shell`로 확인
- **PR-3 실행 전:** Gemini API 키가 환경변수에 있는지 확인 (`GOOGLE_API_KEY` or `GEMINI_API_KEY`)
- **PR-4 실행 전:** Celery worker가 `thesis.tasks` 앱을 인식하는지 확인
- **PR-5 실행:** `python manage.py test thesis -v 2 2>&1 | tee test_results.txt`
