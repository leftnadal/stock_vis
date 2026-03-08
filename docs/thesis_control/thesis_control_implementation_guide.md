# Thesis Control — 통합 구현 로드맵 (최종)

> 3개 문서를 하나의 구현 순서로 통합  
> - 설계 문서 (thesis_control_design.md): UX/API/모델  
> - 수학 모델 (v2.3.2): 스코어링 엔진  
> - 특허 기능: DNA/유효성/합성 에이전트/벡터  

---

## 문서 간 관계

```
┌─────────────────────────────────────────────────────────┐
│  설계 문서 (What)                                        │
│  "어떤 서비스를 만드는가"                                 │
│  UX 플로우, 대화형 빌더, 관제실 UI, API, 모델 구조       │
│                                                          │
│  ┌────────────────────┐  ┌────────────────────────────┐ │
│  │ 수학 모델 (How)     │  │ 특허 기능 (What+)          │ │
│  │ "어떻게 계산하는가"  │  │ "시간이 갈수록 뭐가 추가?" │ │
│  │                    │  │                            │ │
│  │ Stage 0~3 엔진     │  │ DNA 프로파일               │ │
│  │ Robust Z + Decay   │  │ 유효성 학습                │ │
│  │ 알림/Throttling    │  │ 합성 에이전트              │ │
│  │ Snapshot/Universe  │  │ 벡터 스코어링              │ │
│  └────────────────────┘  └────────────────────────────┘ │
│                                                          │
│  이 로드맵 (When)                                        │
│  "어떤 순서로 구현하는가"                                 │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 1: MVP — "기본 전부 갖추기" (Week 1~6)

> 가설을 세우고, 지표가 돌아가고, 알림이 오고, 데이터가 쌓이기 시작.

### Week 1~2: 뼈대 + 모델 + 관제 엔진

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| thesis/ 앱 생성 + Django 모델 | 설계 문서 4.1~4.2 | Thesis, ThesisPremise, ThesisIndicator, IndicatorReading, ThesisSnapshot, ThesisAlert, ThesisFollow, PopularThesisCache |
| **v2.3.2 추가 필드** 반영 | 수학 모델 Section 9 | epsilon, window, decay, min/max_valid_value, max_change_pct, allow_extreme_jump, is_paused, override_score, asof, validation_status, asof_date, data_coverage, premise/indicator_universe_ids |
| **특허 모델** 추가 | 통합 로드맵 1.2~1.4 | HypothesisEvent, ValidityRecord, InvestorDNA |
| 마이그레이션 + 인덱스 | 수학 모델 12.2 | 필수 인덱스 6개 + unique constraint 2개 |
| admin.py 등록 | 설계 문서 | 모든 모델 기본 ModelAdmin |

**이 시점의 모델 전체 목록:**

```
thesis/models/
├── thesis.py          # Thesis, ThesisPremise (설계 문서 + v2.3.2 필드)
├── indicator.py       # ThesisIndicator (+ v2.3.2 params/validation 필드)
│                      # IndicatorReading (+ asof, validation_status, unique)
├── monitoring.py      # ThesisSnapshot (+ asof_date, data_coverage, universe, ordered list)
│                      # ThesisAlert (+ target_id, cooldown_hours)
├── community.py       # ThesisFollow, PopularThesisCache
└── learning.py        # HypothesisEvent, ValidityRecord, InvestorDNA (특허)
```

### Week 2~3: 스코어링 엔진 (v2.3.2)

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| data_validator.py | 수학 모델 Stage 0 | validate_reading (순서 확정, isfinite, asof fallback, latest_validated) |
| indicator_scorer.py | 수학 모델 Stage 1 | score_indicator (Robust Z, MAD_FLOOR, effective_window, Extreme Vol) |
| premise_aggregator.py | 수학 모델 Stage 2 | aggregate (가중평균, 최약고리, 불일치, 카테고리 중복 premise+thesis) |
| thesis_state_machine.py | 수학 모델 Stage 3 | determine_state (Rule-based, data_coverage 보류, needs_review) |
| alert_engine.py | 수학 모델 Section 6 + 12.4 | 알림 생성 + throttling (COOLDOWN_HOURS, USER_VISIBLE_ALERTS) |
| arrow_calculator.py | 수학 모델 3.5~3.6 | degree/color/label 변환 |
| snapshot_builder.py | 수학 모델 Section 9 | universe 고정, ordered list, None→0.0, data_coverage |

### Week 3~4: API + 대화형 빌더

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| 가설 CRUD API | 설계 문서 6.1 | ThesisViewSet (list, create, retrieve, update, close) |
| 전제 CRUD API | 설계 문서 6.1 | ThesisPremiseViewSet |
| 지표 CRUD + 자동추천 API | 설계 문서 6.1 | ThesisIndicatorViewSet + auto_recommend |
| 대화형 가설 빌더 | 설계 문서 2.3 (경로 1, 2만) | thesis_builder.py + conversation API |
| indicator_matcher.py | 설계 문서 5.2 | 키워드 룰 매칭 + LLM fallback |
| 관제실 대시보드 API | 설계 문서 6.2 | GET /{id}/dashboard/ (카드뷰만) |
| 알림 API | 설계 문서 6.1 | GET /alerts/, PATCH /alerts/{aid}/read/ |

### Week 4~5: Celery 태스크 + 이벤트 수집

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| update_indicator_readings | 수학 모델 Section 7 + 12.3 | 18:00 ET. Stage 0 validation + upsert + stale 체크 |
| calculate_scores | 수학 모델 Section 7 | 18:15 ET. Stage 1→2 + Extreme Vol + Override |
| create_snapshots_and_alerts | 수학 모델 Section 7 | 18:30 ET. Stage 3 + snapshot(asof_date, coverage, universe) + alert(throttling) |
| **이벤트 기록 코드 삽입** | 통합 로드맵 1.2 | 기존 API에 HypothesisEvent.objects.create() 1줄씩 추가 |
| **ValidityRecord 생성** | 통합 로드맵 1.3 | 가설 마감(close) 시 각 지표의 2×2 매트릭스 점수 기록 |
| **InvestorDNA 갱신** | 통합 로드맵 1.4 | 마감 시 signal로 자동 집계 |

### Week 5~6: 테스트 + 안정화

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| 유닛테스트 20+개 | 수학 모델 12.6 | Stage 0~3 핵심 경로 + snapshot + alert throttling |
| 통합 테스트 | — | 가설 생성 → 모니터링 → 마감 → 이벤트/유효성 기록 확인 |
| 운영 로그 | 수학 모델 12.7 | Celery 태스크 summary 로그 |
| 운영 모니터링 데이터 수집 | 수학 모델 12.7 | fetch 성공률, validation skip 비율, stale 지표 수 |

### Phase 1 완료 시 상태

```
✅ 가설을 세울 수 있다 (경로 1: 오늘 이슈, 경로 2: 내 생각)
✅ AI가 지표 3~5개를 자동 추천한다
✅ 매일 18:00에 지표가 자동 업데이트된다 (Robust Z + Decay)
✅ 화살표/색상/라벨로 가설 상태가 보인다 (카드뷰)
✅ 변화 감지 시 알림이 온다 (throttling 적용)
✅ 가설 마감하면 적중/미적중 판정할 수 있다
✅ 모든 행동이 HypothesisEvent로 기록되고 있다 (학습 대비)
✅ 마감 시 ValidityRecord + InvestorDNA가 자동 축적된다
⬜ 아직 데이터가 부족해서 유효성 점수/DNA는 활용 안 함
```

---

## Phase 2: 모니터링 강화 + 개인화 시작 (Week 7~12)

> 풍부한 관제 경험 + 축적된 데이터로 개인화 시작

### Week 7~8: 뷰 확장 + 뉴스 연동

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| 히트맵 뷰 API | 설계 문서 3.4 | Finviz 스타일 색상 그리드 |
| 그래프 뷰 API | 설계 문서 3.4 | 시계열 선 그래프 (지지/중립/반박 Y축) |
| 스냅샷 히스토리 API | 설계 문서 6.1 | GET /{id}/snapshots/ |
| [근거] 설명 시스템 | 설계 문서 2.4 | LLM 생성 + Redis 캐싱 |
| AI 일일 요약 | 설계 문서 5.5 | 변화 있는 가설만 LLM 요약 생성 |
| 뉴스 센티먼트 지표 | 설계 문서 5.2 | news/ 앱 SentimentHistory 연동 → Stage 1 입력 |
| 내러티브 반감기 | 설계 문서 3.8 | DailyNewsKeyword 활용 → narrative_momentum 지표 |
| 오늘 이슈 API | 설계 문서 6.1 | GET /daily-issues/ |

### Week 9~10: 유효성 활성화 + DNA 슬라이더

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| ValidityScore 집계 | 통합 로드맵 2.1 | 주 1회 Celery 태스크. ValidityRecord → ValidityScore |
| 점진적 활성화 | 통합 로드맵 2.1 | sample_count ≥ 5 → is_active=True |
| 지표 추천에 유효성 반영 | 통합 로드맵 2.2 | indicator_matcher 개선. core/reference/low_impact 티어 |
| DNA 적합도 슬라이더 | 통합 로드맵 2.3 | personalization_weight (0~1) UI + 블렌딩 로직 |
| 역제안 (Contrarian Nudge) | 통합 로드맵 2.4 | 안 쓰는 유형 지표 1개 끼워넣기 |
| support_direction 확인 UX | 수학 모델 12.5 | "이 지표가 오르면 유리/불리?" 확인 |

### Week 11~12: 관제 고도화

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| 상관계수 자동 할인 | 수학 모델 Phase 2 | 60일 \|ρ\|≥0.9 → 1/√k |
| Adaptive Decay/Window | 수학 모델 Phase 2 | 변동성 높으면 λ↓, window↓ |
| Sustained Extreme | 수학 모델 Phase 2 | s_decayed≥3 (clip전) → alert subtype |
| 알림 고도화 | 수학 모델 12.4 | 사용자 반응 기반 빈도 조절 |

### Phase 2 완료 시 상태

```
✅ 카드/히트맵/그래프 3가지 뷰
✅ AI가 "왜 이 상태인지" 설명 ([근거])
✅ 뉴스 센티먼트 + 내러티브 반감기 지표
✅ 유효성 높은 지표를 우선 추천 (core/reference 티어)
✅ DNA 슬라이더로 개인화 강도 조절
✅ "평소 안 쓰는 유형" 역제안
✅ 상관 지표 자동 할인
⬜ 아직 유효성 데이터가 부족해서 추천 정밀도는 제한적
```

---

## Phase 3: 커뮤니티 + 지능 강화 (Week 13~20)

> Cold start 해결 + 자동 학습 + 커뮤니티

### Week 13~14: 커뮤니티 기능

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| 인기 가설 시스템 | 설계 문서 2.3 경로 3 | GET /popular/, PopularThesisCache |
| 가설 따라하기/수정 | 설계 문서 2.3 경로 3 | POST /popular/{id}/follow/ |
| 템플릿 시스템 | 설계 문서 2.3 경로 4 | GET /templates/, 이벤트형/추세형/비교형/괴리형 |
| Chain Sight 연동 | 설계 문서 2.3 경로 5 | 양방향 진입점 |

### Week 15~16: 합성 에이전트 부트스트래핑

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| 페르소나 정의 (20~30개) | 통합 로드맵 3.1 | SYNTHETIC_PERSONAS |
| 합성 가설 생성 파이프라인 | 통합 로드맵 3.1 | SyntheticBootstrapper (과거 2~3년 데이터) |
| 실제 결과 대조 + ValidityRecord 생성 | 통합 로드맵 3.1 | is_synthetic=True 마킹 |
| 합성/실제 블렌딩 | 통합 로드맵 3.3 | effective_blend = blend_ratio × (1 - real_count/50) |

### Week 17~18: 자동 학습

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| Online Logistic Regression | 수학 모델 Phase 3 + 통합 로드맵 3.2 | ThesisWeightLearner |
| W_j_suggested (추천만) | 수학 모델 Phase 3 | UI "AI가 이 가중치를 추천해요" |
| Safety Gate | 수학 모델 Phase 3 | should_deploy_weights() |
| 주간 재학습 Celery 태스크 | 수학 모델 Phase 3 | 일요일 새벽 |

### Week 19~20: 가설 복기 + 그래프

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| 가설 마감 복기 시스템 | 설계 문서 3.10 | 유용했던 지표, 예상과 달랐던 부분 |
| Neo4j 가설 관계 그래프 | 설계 문서 4.4 | SIMILAR_TO, OPPOSITE_OF, HAS_PREMISE 관계 |
| 가설 아카이브 | 설계 문서 Phase 3 | 학습 이력 UI |
| Phase 3 라벨 품질 가이드 적용 | 수학 모델 12.8 | 마감 UX에 적중 기준 한 줄 고정 |
| 전제 품질 가이드 적용 | 수학 모델 12.9 | 가설 생성 UX에 3요소 가이드 |

### Phase 3 완료 시 상태

```
✅ 인기 가설 구경/따라하기
✅ 템플릿으로 빠른 가설 생성
✅ Chain Sight ↔ Thesis Control 양방향 연동
✅ 합성 에이전트로 유효성 데이터 사전 채움 (Cold Start 해결)
✅ 자동 학습된 가중치 "추천"
✅ 가설 마감 후 복기 + 아카이브
✅ Neo4j 가설 관계 그래프
```

---

## Phase 4: 고도화 (Week 21+)

> 벡터 전환 + 지능화

| 작업 | 소스 문서 | 산출물 |
|------|----------|--------|
| DNA 벡터화 (16차원) | 통합 로드맵 4.1 | cosine similarity 기반 추천 |
| 유효성 벡터화 (6차원) | 통합 로드맵 4.2 | 다면적 지표 평가 |
| 사용자 유사도 | 통합 로드맵 4.4 | "나와 비슷한 투자자" |
| 반대 가설 자동 생성 | 설계 문서 Phase 4 | 확인 편향 방지 |
| 과거 유사 상황 검색 | 설계 문서 Phase 4 | 벡터 유사도 |
| Change Point Detection | 수학 모델 Phase 4 | ruptures |
| 칼만 필터 | 수학 모델 Phase 4 | Stage 1 노이즈 필터링 |

---

## 문서별 참조 가이드

구현 중 "이건 어디에 써있지?" 할 때:

| 궁금한 것 | 참조 문서 | 섹션 |
|----------|----------|------|
| 대화형 플로우 (버튼 선택지, 단계) | 설계 문서 | 2.3 |
| 관제실 UI (카드/히트맵/그래프) | 설계 문서 | 3.1~3.4 |
| 제스처/인터랙션 | 설계 문서 | 3.5 |
| 알림 메시지 문구 | 설계 문서 | 3.7 |
| API 엔드포인트 목록 | 설계 문서 | 6.1 |
| API 응답 JSON 형태 | 설계 문서 | 6.2 |
| Django 모델 기본 구조 | 설계 문서 | 4.2 |
| 모델 추가 필드 (v2.3.2) | 수학 모델 | Section 9 |
| Validation 규칙/순서 | 수학 모델 | Stage 0 (Section 2) |
| Robust Z 계산 코드 | 수학 모델 | Stage 1 (Section 3.6) |
| 가중평균/경고 로직 | 수학 모델 | Stage 2 (Section 4) |
| 상태 전환 규칙 | 수학 모델 | Stage 3 (Section 5) |
| 알림 throttling 규칙 | 수학 모델 | Section 12.4 |
| 인덱스/멱등성/실패격리 | 수학 모델 | Section 12.2~12.3 |
| 테스트 목록 | 수학 모델 | Section 12.6 |
| 운영 로그 형식 | 수학 모델 | Section 12.7 |
| HypothesisEvent 모델 | 통합 로드맵 | Section 1.2 |
| ValidityRecord/Score | 통합 로드맵 | Section 1.3, 2.1 |
| InvestorDNA 모델 | 통합 로드맵 | Section 1.4 |
| DNA 슬라이더/역제안 | 통합 로드맵 | Section 2.3~2.4 |
| 합성 에이전트 | 통합 로드맵 | Section 3.1 |
| Online LR | 수학 모델 Phase 3 + 통합 로드맵 3.2 |
| 벡터 스코어링 | 통합 로드맵 | Section 4 |
| 특허 청구항 매핑 | 통합 로드맵 | Section 6 |

---

## 프론트엔드 vs 백엔드 구현 분리

| Phase | 백엔드 (Django/Celery) | 프론트엔드 (Next.js) |
|-------|----------------------|---------------------|
| **1** | 모델+마이그레이션, 스코어링 엔진, CRUD API, 대화 API, Celery 3태스크, 이벤트 수집 | 대화형 빌더 UI, 관제실 카드뷰, 알림 표시 |
| **2** | 뉴스 연동, 유효성 집계, DNA 블렌딩, 상관 할인 | 히트맵/그래프 뷰, [근거] 팝업, DNA 슬라이더, 역제안 UI, 내러티브 카드 |
| **3** | 합성 에이전트 파이프라인, Online LR, Neo4j 관계 | 인기 가설 목록, 따라하기/수정, 템플릿 선택, Chain Sight 연동, 복기 UI |
| **4** | 벡터화 + 코사인 유사도 | 사용자 유사도 UI, 반대 가설 카드 |

**원칙:** 백엔드 API가 먼저. 프론트는 API가 안정된 후 붙이기. Phase 1에서 프론트는 최소한만.