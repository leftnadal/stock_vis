# Phase 4: ML 학습 + Shadow Mode + 프론트엔드 (📋 계획)

## 기간
Week 7-10

## 목표
축적된 ML Label 데이터로 첫 모델 학습, Shadow Mode로 수동 가중치와 병렬 비교.
프론트엔드에 NewsEvent 타임라인 컴포넌트 추가.

## 구현 항목

### 1. ML Weight Optimizer — `news/services/ml_weight_optimizer.py`
- **Phase 1: Logistic Regression**
  - Company News 데이터만 사용 (순환 의존 방지)
  - label_confidence → sample_weight
  - Time-Series Split 검증 (시간순, 랜덤 셔플 금지)
  - Rolling Window 6~8주
  - Smoothing (0.7 × 새 가중치 + 0.3 × 이전 가중치)

### 2. Safety Gate 3단계
1. F1 Score > 0.55
2. 기존 대비 -10%p 이내 하락
3. 가중치 변동 ±50% 이내

### 3. Shadow Mode (Week 7-10)
- 매주 학습 실행, Safety Gate 판정하되 **차단 안 함**
- ML 가중치와 수동 가중치 병렬 기록
- 비교 리포트: "ML 선별 vs 수동 선별" 차이 분석
- MLModelHistory.shadow_comparison에 결과 저장

### 4. Celery 태스크
- `train_importance_model`: 일요일 03:00
- `monitor_ml_performance`: 일요일 03:30

### 5. 프론트엔드
- NewsEvent 타임라인 컴포넌트
- Chain Sight에 뉴스 영향 관계 표시

## 의존성
- `scikit-learn` 패키지 추가 (pyproject.toml)
- 3,000건+ ML Label 축적 필요 (Phase 2에서 시작된 수집)
- 4주 연속 F1 > 0.55 달성 시 → Phase 5 진입
