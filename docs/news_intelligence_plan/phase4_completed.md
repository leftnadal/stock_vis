# Phase 4: ML 학습 + Shadow Mode + 프론트엔드 (✅ 완료)

## 기간
Week 7-10

## 목표
축적된 ML Label 데이터로 첫 모델 학습, Shadow Mode로 수동 가중치와 병렬 비교.
프론트엔드에 ML 모델 상태 카드 추가.

## 구현 내용

### 1. ML Weight Optimizer — `news/services/ml_weight_optimizer.py`

**MLWeightOptimizer** 클래스:

**Feature 추출** (`extract_features`):
- f1: source_credibility (소스 신뢰도 사전)
- f2: entity_count (rule_tickers + rule_sectors 수, 0~1 정규화)
- f3: sentiment_magnitude (|sentiment_score|, 없으면 0.3)
- f4: recency proxy (발행 시간대: 시장시간 1.0, 전후 0.7, 야간 0.4)
- f5: keyword_relevance (rule_sectors 수 / 3, 0~1)

**학습 데이터 준비** (`prepare_training_data`):
- Company News만 사용 (entities 있는 뉴스)
- Rolling Window 8주
- 최소 200개 학습 데이터 필요
- ml_label_24h, ml_label_important, ml_label_confidence 필드 사용

**모델 학습** (`train_model`):
- Logistic Regression (scikit-learn)
- `class_weight='balanced'` (클래스 불균형 보정)
- `sample_weight=ml_label_confidence`
- Time-Series Split 3-fold (시간순, 랜덤 셔플 금지)
- 전체 데이터로 최종 모델 학습
- 계수 정규화 → Engine C β₁~β₅ 가중치로 변환

**Safety Gate 3단계** (`safety_gate_check`):
| Tier | 조건 | 설명 |
|------|------|------|
| 1 | F1 >= 0.55 | 기본 성능 임계값 |
| 2 | Precision >= 0.50 | False positive 통제 |
| 3 | 이전 모델 대비 F1 하락 <= 10%p | 성능 저하 방지 |

**Weight Smoothing** (`smooth_weights`):
- `0.7 × new_weights + 0.3 × previous_weights`
- 합계 1.0으로 재정규화
- 급격한 가중치 변동 방지

**Shadow Mode 비교** (`generate_shadow_comparison`):
- 최근 N일 뉴스에 ML 가중치 vs 수동 가중치 적용
- 상위 15% 선별 결과 비교
- agreement_rate, overlap, only_manual, only_ml 계산

**모델 배포** (`deploy_model`):
- Shadow → Deployed 상태 전환
- Safety Gate 통과 필수
- 이전 Deployed 모델 자동 rolled_back

**상태 조회** (`get_current_status`):
- 최신 모델 정보, 배포 모델 정보
- 최근 4주 성능 추이
- 학습 가능 데이터 수

### 2. Celery 태스크 — `news/tasks.py`

| 태스크 | 스케줄 | 설명 |
|--------|--------|------|
| `train_importance_model` | 일요일 03:00 EST | 주간 학습 파이프라인 (30분 타임아웃) |
| `generate_shadow_report` | 일요일 03:30 EST | Shadow Mode 비교 리포트 (5분 타임아웃) |

### 3. Celery Beat 스케줄 — `config/celery.py`
- `train-importance-model`: 일요일 03:00, expires 2시간
- `generate-shadow-report`: 일요일 03:30, days=7, expires 1시간

### 4. API 엔드포인트 — `news/api/views.py`

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/v1/news/ml-status/` | ML 모델 현재 상태 (최신/배포 모델, 성능 추이, 데이터 수) |
| `GET /api/v1/news/ml-shadow-report/` | Shadow Mode 비교 리포트 (ML vs 수동 선별 결과) |

### 5. 서비스 등록 — `news/services/__init__.py`
- `MLWeightOptimizer` 추가

### 6. 의존성 — `pyproject.toml`
- `scikit-learn` 추가 (Logistic Regression)

### 7. 프론트엔드

**타입** — `frontend/types/news.ts`:
- `MLStatusResponse`, `MLShadowReportResponse`, `NewsEventsResponse` 등 추가

**서비스** — `frontend/services/newsService.ts`:
- `getMLStatus()`, `getMLShadowReport()`, `getNewsEvents()` 추가

**훅** — `frontend/hooks/useNews.ts`:
- `useMLStatus()`, `useMLShadowReport()`, `useNewsEvents()` 추가

**컴포넌트** — `frontend/components/news/MLModelStatusCard.tsx`:
- ML 모델 현재 상태 카드
- 학습 데이터 현황 (labeled/min_required)
- 최신 모델 F1/Safety Gate 상태
- 배포 모델 가중치 바 차트
- 최근 학습 이력 리스트

**페이지** — `frontend/app/news/page.tsx`:
- 인증 사용자 레이아웃 3-column (키워드 + 인사이트 + ML 상태)

## 테스트 — `tests/news/test_ml_weight_optimizer.py`
- **61개 테스트** 전체 통과
- 테스트 범위:
  - Feature Extraction (12개)
  - Time-Series Split (5개)
  - Model Training (6개)
  - Safety Gate (6개)
  - Weight Smoothing (3개)
  - Shadow Comparison (3개)
  - Prepare Training Data (3개)
  - Training Pipeline (4개)
  - Model Deployment (5개)
  - Get Status (3개)
  - Version Generation (1개)
  - Celery Tasks (3개)
  - API Endpoints (3개)
  - Beat Schedule (4개)

## 검증 결과
- 61개 신규 테스트 통과
- 전체 뉴스 테스트 490개 통과 (기존 429 + 신규 61)
- API 엔드포인트 정상 응답:
  - `/api/v1/news/ml-status/` → 200
  - `/api/v1/news/ml-shadow-report/` → 200

## 운영 규칙

### Shadow Mode 운영 (Week 7-10)
1. 매주 일요일 03:00 EST에 자동 학습
2. Safety Gate 통과 여부와 관계없이 기록만 (차단 안 함)
3. 03:30 EST에 비교 리포트 자동 생성
4. 수동 가중치로 계속 운영

### Production Mode 진입 조건 (Week 11+)
1. 4주 연속 Safety Gate 통과 (F1 > 0.55)
2. Shadow 비교에서 agreement_rate > 0.70
3. `deploy_model(model_id)` 호출로 수동 배포
