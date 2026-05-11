# Thesis Control — 통합 구현 로드맵

> Thesis Control 수학 모델(v2.3.2) + 특허 차별화 기능 통합  
> 원칙: Phase 1에서 기본 구성 전부 갖추기 → 이후 정교화

---

## 0. 두 설계의 통합 구조

### 수학 모델 (v2.3.2) = "관제 엔진"

```
Stage 0 → Stage 1 → Stage 2 → Stage 3
Validation   Scoring   Aggregation   State/Alert
```

매일 자동 실행. 가설의 현재 상태를 수학으로 계산.

### 특허 기능 = "학습 + 개인화 레이어"

```
[이벤트 수집] → [유효성 학습] → [DNA 프로파일] → [개인화 추천]
HypothesisEvent   ValidityScore   InvestorDNA      SmartRecommender
```

시간이 지날수록 강해지는 지능. 관제 엔진 위에 얹어지는 구조.

### 통합 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  사용자 행동                                                 │
│  가설 생성 / 전제 추가 / 지표 선택 / AI 수락·거절 / 마감     │
└──────────┬──────────────────────────────────────────────────┘
           │ HypothesisEvent (단일 이벤트 스트림)
           ▼
┌──────────────────────┐    ┌──────────────────────┐
│  관제 엔진 (v2.3.2)  │    │  학습/개인화 레이어   │
│                      │    │                      │
│  Stage 0: Validation │    │  ① 이벤트 기록       │
│  Stage 1: Scoring    │◄──►│  ② 유효성 학습       │
│  Stage 2: Aggregation│    │  ③ DNA 프로파일      │
│  Stage 3: State      │    │  ④ 개인화 추천       │
│                      │    │                      │
│  매일 자동 (Celery)  │    │  마감 시 / 배치      │
└──────────────────────┘    └──────────────────────┘
           │                           │
           ▼                           ▼
    화살표/알림/상태              지표 추천/DNA 인사이트
    (사용자에게 보이는 것)         (AI 제안 개인화)
```

---

## 1. Phase 1 (MVP) — 기본 구성 전부 갖추기

> 목표: "전부 있되, 전부 심플하게"  
> 기간: 기존 Thesis Control MVP + 2~3주 추가

### 1.1 관제 엔진 (v2.3.2 그대로)

이미 확정된 내용. 변경 없음.

| 항목    | 내용                                                                           |
| ------- | ------------------------------------------------------------------------------ |
| Stage 0 | Data Validation (순서 확정, isfinite, asof/72h, min/max_valid, max_change_pct) |
| Stage 1 | Robust Z(MAD) + Decay, 지표별 params, effective_window, MAD_FLOOR              |
| Stage 2 | 가중평균 + 최약고리 + 불일치 + 카테고리 중복 (premise+thesis, total≥5)         |
| Stage 3 | Rule-based 상태 + 마감 리마인더 + data_coverage 보류                           |
| 스냅샷  | asof_date + universe 고정 + ordered list + None→0.0                            |

### 1.2 이벤트 수집 (Day 1부터)

> 학습의 원료. Phase 1에서는 **기록만 하고 활용은 안 함.**  
> 하지만 이걸 안 모으면 Phase 2~3이 안 되므로 MVP부터 반드시 포함.

```python
class HypothesisEvent(models.Model):
    """사용자의 모든 가설 관련 행동을 기록하는 단일 이벤트 스트림."""
    id = UUIDField(primary_key=True, default=uuid4)
    user = ForeignKey(User, on_delete=CASCADE)
    thesis = ForeignKey(Thesis, on_delete=CASCADE, null=True)

    event_type = CharField(max_length=30, choices=[
        # 가설 생성
        ('thesis_created',      '가설 생성'),
        ('thesis_closed',       '가설 마감'),
        # 전제
        ('premise_added',       '전제 추가'),
        ('premise_modified',    '전제 수정'),
        ('premise_removed',     '전제 제거'),
        # 지표
        ('indicator_added',     '지표 추가'),
        ('indicator_removed',   '지표 제거'),
        # AI 상호작용
        ('ai_suggestion_shown', 'AI 제안 표시'),
        ('ai_suggestion_accepted', 'AI 제안 수락'),
        ('ai_suggestion_rejected', 'AI 제안 거절'),
        # 마감 판정
        ('outcome_correct',     '적중 판정'),
        ('outcome_incorrect',   '미적중 판정'),
        ('outcome_neutral',     '중립 판정'),
    ])

    event_data = JSONField(default=dict)
    # 예: thesis_created → {thesis_type, direction, entry_source}
    #     premise_added → {premise_id, content, extraction_level, category}
    #     indicator_added → {indicator_id, indicator_type, support_direction, source: 'ai'|'user'}
    #     ai_suggestion_rejected → {suggestion_type, suggestion_content, reason(optional)}
    #     outcome_correct → {outcome_return, duration_days}

    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['thesis', 'event_type']),
            models.Index(fields=['event_type', '-created_at']),
        ]
```

**Phase 1 구현:**

- 가설 CRUD API, 대화형 빌더, 지표 매칭 등 기존 코드에서 이벤트 생성 코드 삽입
- `HypothesisEvent.objects.create(user=user, thesis=thesis, event_type='...', event_data={...})`
- 이건 기존 비즈니스 로직에 1줄씩 추가하는 수준

### 1.3 유효성 기록 (기본형)

> Phase 1에서는 **기록만.** 점수 계산은 Phase 2에서 활성화.

```python
class ValidityRecord(models.Model):
    """가설 마감 시 각 지표의 유효성을 기록."""
    id = UUIDField(primary_key=True, default=uuid4)

    # 어떤 조합인지
    thesis_type = CharField(max_length=30)       # macro, sector, event, ...
    indicator_data_key = CharField(max_length=50) # vix, foreign_net_buy, rsi, ...
    market_regime = CharField(max_length=20)      # normal, elevated, high_vol

    # 유효성 판정 (2×2 매트릭스)
    indicator_aligned = BooleanField()   # 지표가 가설 방향으로 움직였는가
    thesis_correct = BooleanField()      # 가설이 적중했는가

    # 점수 (매트릭스 기반)
    # aligned=True  + correct=True  → +0.3  (지표가 맞게 움직이고 가설도 적중)
    # aligned=True  + correct=False → -0.2  (지표가 맞게 움직였는데 가설은 미적중)
    # aligned=False + correct=True  → -0.15 (지표가 반대로 움직였는데 가설은 적중)
    # aligned=False + correct=False → +0.05 (지표가 반대로 움직이고 가설도 미적중)
    score = FloatField()

    # 메타
    thesis = ForeignKey(Thesis, on_delete=CASCADE)
    indicator = ForeignKey(ThesisIndicator, on_delete=CASCADE)
    recorded_at = DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['thesis_type', 'indicator_data_key', 'market_regime']),
        ]
```

**Phase 1 구현:**

- 가설 마감(close) 시점에 각 지표에 대해 ValidityRecord 1건씩 생성
- `indicator_aligned`: 마감 시점 지표 score > 0이면 True
- `thesis_correct`: 사용자가 선택한 outcome에서 결정
- `score`: 2×2 매트릭스에서 즉시 결정 (복잡한 로직 없음)

### 1.4 DNA 프로파일 (최소 골격)

> Phase 1에서는 **이벤트에서 자동 집계되는 기본 통계만.**  
> 슬라이더/역제안은 Phase 2.

```python
class InvestorDNA(models.Model):
    """사용자의 투자 사고방식 프로파일. 이벤트 로그에서 자동 구축."""
    user = OneToOneField(User, on_delete=CASCADE, primary_key=True)

    # Phase 1: 기본 통계 (이벤트 집계)
    total_theses = IntegerField(default=0)
    closed_theses = IntegerField(default=0)
    correct_count = IntegerField(default=0)
    incorrect_count = IntegerField(default=0)

    # 전제 카테고리 분포 (하향식/상향식 판단 근거)
    premise_category_counts = JSONField(default=dict)
    # {"macro": 12, "sector": 8, "company": 15, "technical": 3}

    # 지표 유형 선호도
    indicator_type_counts = JSONField(default=dict)
    # {"market_data": 20, "macro": 15, "sentiment": 5, ...}

    # AI 제안 수락률
    ai_suggestions_shown = IntegerField(default=0)
    ai_suggestions_accepted = IntegerField(default=0)

    # Phase 2에서 활성화될 필드 (미리 생성만)
    personalization_weight = FloatField(default=0.5)  # DNA 적합도 슬라이더 (0~1)

    updated_at = DateTimeField(auto_now=True)

    @property
    def accuracy_rate(self):
        total = self.correct_count + self.incorrect_count
        return self.correct_count / total if total > 0 else None

    @property
    def ai_accept_rate(self):
        return self.ai_suggestions_accepted / self.ai_suggestions_shown \
            if self.ai_suggestions_shown > 0 else None

    @property
    def top_down_ratio(self):
        """하향식 사고 비율. macro+sector 비중."""
        total = sum(self.premise_category_counts.values()) or 1
        top_down = self.premise_category_counts.get('macro', 0) + \
                   self.premise_category_counts.get('sector', 0)
        return top_down / total
```

**Phase 1 구현:**

- 가설 마감 시 InvestorDNA 자동 갱신 (Celery 또는 signal)
- `premise_category_counts`: 전제의 카테고리 분류는 indicator_matcher의 키워드 룰 재활용
- `indicator_type_counts`: 이미 indicator_type 필드가 있으므로 Count만
- UI에서는 아직 활용 안 함 (데이터 축적만)

### 1.5 Phase 1 구현 순서

```
Week 1-2: 관제 엔진 (기존 Thesis Control MVP)
  ├── Django 모델 + 마이그레이션
  ├── scoring/ 서비스 (Stage 0~3)
  ├── Celery 3 태스크
  └── 기본 API

Week 3: 이벤트 수집 + 유효성 기록
  ├── HypothesisEvent 모델 + 인덱스
  ├── 기존 API에 이벤트 기록 코드 삽입 (1줄씩)
  ├── ValidityRecord 모델
  ├── 가설 마감 시 ValidityRecord 생성 로직
  └── InvestorDNA 모델 + 마감 시 갱신 signal

Week 4: 테스트 + 안정화
  ├── 유닛테스트 (v2.3.2 목록 + 이벤트/유효성 테스트)
  └── 통합 테스트 (가설 생성→모니터링→마감→이벤트/유효성 기록 확인)
```

---

## 2. Phase 2 — DNA 슬라이더 + 유효성 활성화

> 목표: 축적된 데이터로 개인화 시작  
> 전제조건: 가설 마감 10건+ 축적  
> 기간: 4~6주

### 2.1 유효성 점수 집계 활성화

Phase 1에서 쌓인 ValidityRecord를 집계하여 **ValidityScore 테이블**로 요약.

```python
class ValidityScore(models.Model):
    """(thesis_type, indicator, regime) 조합별 유효성 점수.
    ValidityRecord를 집계한 결과."""

    thesis_type = CharField(max_length=30)
    indicator_data_key = CharField(max_length=50)
    market_regime = CharField(max_length=20)

    # 집계 결과
    cumulative_score = FloatField(default=0.0)     # ValidityRecord.score 누적합
    sample_count = IntegerField(default=0)          # 기록 건수
    confidence = CharField(max_length=10, default='low')  # low(<5), medium(5-15), high(15+)

    # 점진적 활성화
    is_active = BooleanField(default=False)  # sample_count >= 5일 때 자동 True

    updated_at = DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['thesis_type', 'indicator_data_key', 'market_regime']
```

**Celery 태스크 추가:** 주 1회 ValidityRecord → ValidityScore 집계

### 2.2 지표 추천에 유효성 점수 반영

```python
# indicator_matcher.py 개선
def match_indicators(thesis, premises):
    candidates = get_keyword_matched_candidates(premises)  # 기존 룰 기반

    # Phase 2: 유효성 점수로 후보 정렬
    regime = get_current_market_regime()
    for candidate in candidates:
        validity = ValidityScore.objects.filter(
            thesis_type=thesis.thesis_type,
            indicator_data_key=candidate.data_key,
            market_regime=regime,
            is_active=True
        ).first()

        if validity:
            candidate.validity_boost = validity.cumulative_score / validity.sample_count
            candidate.confidence = validity.confidence
        else:
            candidate.validity_boost = 0
            candidate.confidence = 'none'

    # 유효성 높은 지표를 core, 낮은 것을 reference로 분류
    candidates.sort(key=lambda c: c.validity_boost, reverse=True)
    return classify_tiers(candidates)  # core / reference / low_impact
```

### 2.3 DNA 적합도 슬라이더

```python
# DNA 슬라이더 로직
def apply_dna_personalization(candidates, user_dna, personalization_weight):
    """
    personalization_weight: 0.0 (탐색 모드) ~ 1.0 (몰입 모드)
    기본값: 0.5
    """
    for candidate in candidates:
        # 사용자의 지표 유형 선호도와의 매칭
        type_preference = user_dna.indicator_type_counts.get(candidate.indicator_type, 0)
        total_indicators = sum(user_dna.indicator_type_counts.values()) or 1
        personal_fit = type_preference / total_indicators

        # 블렌딩
        objective = candidate.validity_boost
        blended = (personalization_weight * personal_fit * objective) + \
                  ((1 - personalization_weight) * objective)
        candidate.final_score = blended

    return sorted(candidates, key=lambda c: c.final_score, reverse=True)
```

### 2.4 역제안 (Contrarian Nudge)

```python
def add_contrarian_nudge(candidates, user_dna, thesis):
    """사용자가 잘 안 쓰는 유형의 지표를 1개 끼워넣기."""
    used_types = set(user_dna.indicator_type_counts.keys())
    all_types = {'market_data', 'macro', 'sentiment', 'technical', 'fundamental'}
    underused = all_types - used_types

    # 안 쓰는 유형이 있으면 그 유형에서 유효성 높은 지표 1개 추천
    if underused:
        nudge_type = underused.pop()
        nudge_candidate = find_best_validity_indicator(
            thesis.thesis_type, nudge_type, get_current_regime()
        )
        if nudge_candidate:
            nudge_candidate.is_nudge = True
            nudge_candidate.nudge_reason = f"평소 {TYPE_LABELS[nudge_type]}를 잘 안 쓰시는데, 이 지표가 유효할 수 있어요"
            candidates.append(nudge_candidate)

    return candidates
```

### 2.5 Phase 2 추가 항목 (v2.3.2에서 예정된 것)

| 항목                  | 내용                      |
| --------------------- | ------------------------- |
| 상관계수 자동 할인    | 60일 \|ρ\|≥0.9 → 1/√k     |
| Adaptive Decay/Window | 변동성 높으면 λ↓, window↓ |
| Sustained Extreme     | s_decayed≥3 (clip전)      |
| 뉴스 센티먼트         | LLM→Stage 1 입력          |

---

## 3. Phase 3 — 합성 에이전트 + 자동학습

> 목표: Cold start 해결 + 가중치 자동학습  
> 전제조건: Phase 2 안정화 + ValidityScore 데이터  
> 기간: 6~8주

### 3.1 합성 에이전트 부트스트래핑

> **특허 핵심 차별점.** 선행기술에서 발견되지 않은 완전히 새로운 접근.

```python
"""
LLM이 다양한 투자자 페르소나를 시뮬레이션하여
과거 시장 데이터 기반 합성 가설을 생성하고,
실제 시장 결과와 대조하여 유효성 학습 시스템을 사전학습(pre-training).
"""

SYNTHETIC_PERSONAS = [
    {"name": "가치투자_하향식_보수적", "thesis_types": ["macro", "sector"],
     "premise_style": "top_down", "risk": "conservative"},
    {"name": "모멘텀_상향식_공격적", "thesis_types": ["company", "event"],
     "premise_style": "bottom_up", "risk": "aggressive"},
    {"name": "배당_매크로_균형적", "thesis_types": ["macro"],
     "premise_style": "mixed", "risk": "moderate"},
    # ... 20~30개 페르소나
]

class SyntheticBootstrapper:
    """과거 시장 데이터로 합성 가설을 생성하여 ValidityScore를 사전 채움."""

    def run(self, start_date, end_date, personas=SYNTHETIC_PERSONAS):
        for persona in personas:
            for date_point in get_monthly_snapshots(start_date, end_date):
                # 1. LLM이 해당 시점의 시장 상황 + 페르소나 성격으로 가설 생성
                thesis = self.generate_thesis(persona, date_point)

                # 2. LLM이 전제와 지표를 선택 (페르소나 성격 반영)
                premises, indicators = self.generate_premises_and_indicators(
                    persona, thesis, date_point
                )

                # 3. 실제 시장 데이터로 지표 움직임 확인
                for indicator in indicators:
                    actual_movement = get_actual_indicator_movement(
                        indicator.data_key, date_point, thesis.expected_timeframe
                    )
                    aligned = (actual_movement > 0) == (indicator.support_direction == 'positive')

                # 4. 실제 시장 결과로 가설 적중 여부 확인
                actual_return = get_actual_return(thesis.target, date_point, thesis.expected_timeframe)
                correct = (actual_return > 0) == (thesis.direction == 'bullish')

                # 5. ValidityRecord 생성 (합성 데이터 마킹)
                ValidityRecord.objects.create(
                    thesis_type=thesis.thesis_type,
                    indicator_data_key=indicator.data_key,
                    market_regime=get_regime_at(date_point),
                    indicator_aligned=aligned,
                    thesis_correct=correct,
                    score=VALIDITY_MATRIX[aligned][correct],
                    is_synthetic=True,  # 합성 데이터 구분
                )

        # 6. ValidityScore 재집계
        aggregate_validity_scores()
```

**핵심 가치:**

- 사용자 0명 상태에서 ValidityScore가 이미 의미있는 초기값을 가짐
- 다양한 페르소나가 같은 시장에서 다른 가설을 세우므로 커버리지가 넓음
- 실제 시장 데이터 기반이므로 점수가 현실적

### 3.2 Online Logistic Regression (v2.3.2에서 이미 확정)

```python
# 기존 v2.3.2 설계 그대로
class ThesisWeightLearner:
    """마감된 가설로 전제 가중치 학습. L2 = 가우시안 Prior."""
    # ... (v2.3.2 문서 참조)

    def get_suggested_weights(self):
        """W_j_suggested: 추천만. 운영 T에는 기본 W_j."""
        # ... (v2.3.2 문서 참조)
```

### 3.3 합성 데이터 + 실제 데이터 블렌딩

```python
def aggregate_validity_scores(blend_ratio=0.3):
    """
    합성 데이터와 실제 사용자 데이터의 블렌딩.

    blend_ratio: 합성 데이터 비중 (실제 데이터가 쌓이면 자동 감소)
    """
    for combo in get_all_combos():
        synthetic_records = ValidityRecord.objects.filter(
            thesis_type=combo.thesis_type,
            indicator_data_key=combo.indicator_key,
            market_regime=combo.regime,
            is_synthetic=True
        )
        real_records = ValidityRecord.objects.filter(
            thesis_type=combo.thesis_type,
            indicator_data_key=combo.indicator_key,
            market_regime=combo.regime,
            is_synthetic=False
        )

        # 실제 데이터가 많아지면 합성 비중 자동 감소
        real_count = real_records.count()
        effective_blend = blend_ratio * max(0, 1 - real_count / 50)
        # real_count=0 → blend=0.3, real_count=50+ → blend=0

        synthetic_avg = synthetic_records.aggregate(Avg('score'))['score__avg'] or 0
        real_avg = real_records.aggregate(Avg('score'))['score__avg'] or 0

        final_score = (effective_blend * synthetic_avg) + ((1 - effective_blend) * real_avg)

        ValidityScore.objects.update_or_create(
            thesis_type=combo.thesis_type,
            indicator_data_key=combo.indicator_key,
            market_regime=combo.regime,
            defaults={
                'cumulative_score': final_score,
                'sample_count': real_count,
                'is_active': real_count >= 5,
            }
        )
```

---

## 4. Phase 4 — 벡터 기반 스코어링

> 목표: 스칼라 → 다차원 벡터. 유사도 기반 추천.  
> 전제조건: Phase 3 안정화 + 충분한 데이터 축적  
> 기간: 8~12주 (고도화 단계)

### 4.1 DNA 프로파일 벡터화

```python
# 스칼라 딕셔너리 → 고정 차원 벡터
def build_dna_vector(user_dna) -> np.ndarray:
    """16차원 DNA 벡터 생성."""
    total_premises = sum(user_dna.premise_category_counts.values()) or 1
    total_indicators = sum(user_dna.indicator_type_counts.values()) or 1

    return np.array([
        # 전제 카테고리 (4d)
        user_dna.premise_category_counts.get('macro', 0) / total_premises,
        user_dna.premise_category_counts.get('sector', 0) / total_premises,
        user_dna.premise_category_counts.get('company', 0) / total_premises,
        user_dna.premise_category_counts.get('technical', 0) / total_premises,
        # 사고방식 (2d)
        user_dna.top_down_ratio,
        1 - user_dna.top_down_ratio,
        # 지표 유형 선호 (5d)
        user_dna.indicator_type_counts.get('market_data', 0) / total_indicators,
        user_dna.indicator_type_counts.get('macro', 0) / total_indicators,
        user_dna.indicator_type_counts.get('sentiment', 0) / total_indicators,
        user_dna.indicator_type_counts.get('technical', 0) / total_indicators,
        user_dna.indicator_type_counts.get('fundamental', 0) / total_indicators,
        # AI 수락률 (1d)
        user_dna.ai_accept_rate or 0.5,
        # 적중률 by thesis_type (4d) — Phase 3 이후 채워짐
        0.5, 0.5, 0.5, 0.5,
    ])
```

### 4.2 유효성 벡터화

```python
# 스칼라 score → 6차원 벡터
class ValidityVector:
    """지표의 다면적 유효성."""
    directional_accuracy: float   # 방향 맞춤 비율
    magnitude_sensitivity: float  # 변화 크기 민감도
    timing_relevance: float       # 선행/동행/후행 특성
    regime_stability: float       # 시장 국면 간 안정성
    user_consensus: float         # 여러 사용자 간 일관성
    decay_rate: float             # 시간 경과 유효성 감소 속도
```

### 4.3 코사인 유사도 기반 추천

```python
def recommend_with_vectors(thesis_type, user_dna_vector, market_regime):
    for candidate in get_all_indicators():
        validity_vec = get_validity_vector(thesis_type, candidate, market_regime)
        personal_fit = cosine_similarity(user_dna_vector, candidate.affinity_vector)

        # thesis_type별 가중치 프로파일
        if thesis_type == "macro":
            weight = [0.3, 0.2, 0.1, 0.3, 0.1, 0.0]  # regime_stability 중시
        elif thesis_type == "event":
            weight = [0.2, 0.3, 0.3, 0.0, 0.1, 0.1]  # timing 중시

        objective_score = np.dot(validity_vec, weight)

        pw = user_dna.personalization_weight
        final = (pw * personal_fit * objective_score) + ((1 - pw) * objective_score)
        candidate.final_score = final
```

### 4.4 사용자 유사도 (향후)

```python
# "나와 비슷한 투자자"의 성공 패턴 참고
def find_similar_investors(user_dna_vector, top_k=5):
    all_dna_vectors = load_all_dna_vectors()
    similarities = cosine_similarity(user_dna_vector, all_dna_vectors)
    return top_k_indices(similarities, k=top_k)
```

---

## 5. 전체 로드맵 요약

```
Phase 1 (MVP)          Phase 2              Phase 3              Phase 4
━━━━━━━━━━━━          ━━━━━━━━━━          ━━━━━━━━━━          ━━━━━━━━━━
관제 엔진 (v2.3.2)    유효성 활성화         합성 에이전트         벡터 스코어링
이벤트 수집 시작       DNA 슬라이더          Online LR            DNA 벡터화
ValidityRecord 기록    역제안 넛지           블렌딩 정책          유효성 벡터화
InvestorDNA 골격       지표 추천 개선        Cold Start 해결      코사인 유사도
                      상관 할인/Adaptive                         사용자 유사도
                      뉴스 센티먼트

[Week 1-4]             [+4~6주]             [+6~8주]             [+8~12주]
기본 전부 갖춤         개인화 시작           지능 강화             고도화
```

### Phase별 특허 기능 매핑

| 특허 기능         | Phase 1                 | Phase 2                 | Phase 3            | Phase 4         |
| ----------------- | ----------------------- | ----------------------- | ------------------ | --------------- |
| **DNA 프로파일**  | 이벤트 기록 + 기본 통계 | ✅ 슬라이더 + 역제안    | 적중률별 강점/약점 | 벡터화 + 유사도 |
| **유효성 학습**   | ValidityRecord 기록     | ✅ ValidityScore 활성화 | Online LR 학습     | 벡터화 + 다면적 |
| **합성 에이전트** | —                       | —                       | ✅ 부트스트래핑    | 확장 페르소나   |
| **벡터 스코어링** | —                       | —                       | —                  | ✅ 전면 전환    |

### Phase별 모델 필드 추가

| Phase | 추가 모델                                    | 추가 필드                                                                              |
| ----- | -------------------------------------------- | -------------------------------------------------------------------------------------- |
| 1     | HypothesisEvent, ValidityRecord, InvestorDNA | event_type, event_data, premise_category_counts, indicator_type_counts, ai_accept_rate |
| 2     | ValidityScore                                | cumulative_score, sample_count, confidence, is_active                                  |
| 2     | InvestorDNA                                  | personalization_weight (이미 생성)                                                     |
| 3     | ValidityRecord                               | is_synthetic (합성 구분)                                                               |
| 4     | InvestorDNA                                  | dna_vector (JSONField → numpy)                                                         |
| 4     | ValidityScore                                | validity_vector (6d)                                                                   |

---

## 6. 특허 청구항과의 매핑

### 독립항 1: 투자 DNA 프로파일 (후보4)

| 청구 요소                          | Phase                        |
| ---------------------------------- | ---------------------------- |
| 이벤트 로그 기반 암묵적 프로파일링 | **Phase 1** (기록 시작)      |
| 하향식/상향식 비율 계산            | **Phase 1** (top_down_ratio) |
| AI 제안 수락률                     | **Phase 1** (ai_accept_rate) |
| 적합도 슬라이더 + 역제안           | **Phase 2**                  |
| 가설 유형별 적중률 강점/약점       | **Phase 3**                  |
| DNA 벡터화 + 유사도 추천           | **Phase 4**                  |

### 독립항 2: 적응형 유효성 학습 (후보1)

| 청구 요소                                   | Phase                              |
| ------------------------------------------- | ---------------------------------- |
| 2×2 매트릭스 점수                           | **Phase 1** (ValidityRecord.score) |
| thesis_type × indicator × regime 3차원 매핑 | **Phase 2** (ValidityScore)        |
| 점진적 활성화 (sample_count≥5)              | **Phase 2**                        |
| 사용자 판정 포함 학습 루프                  | **Phase 2**                        |
| core/reference/low_impact 티어 분류         | **Phase 2**                        |

### 독립항 3: 합성 에이전트 부트스트래핑 (신규)

| 청구 요소                                | Phase       |
| ---------------------------------------- | ----------- |
| 다양한 투자자 페르소나 시뮬레이션        | **Phase 3** |
| 과거 시장 데이터 기반 합성 가설 생성     | **Phase 3** |
| 실제 결과 대조 유효성 사전학습           | **Phase 3** |
| 합성/실제 데이터 블렌딩 (자동 비중 감소) | **Phase 3** |
