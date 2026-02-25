# Phase 6: ML Phase 2 — LightGBM (📋 계획)

## 기간
Month 3+

## 전환 조건 (3가지 모두 충족 시)
1. 데이터 10,000건+ (label 포함)
2. Phase 1 정확도 3주 연속 정체 (<1%p 개선)
3. 확장 feature 데이터 수집 안정화

## 구현 항목

### 1. 확장 Feature (⑥~⑩)
- ⑥ publish_hour: 발행 시각
- ⑦ weekday: 요일
- ⑧ sector_volatility: 섹터 변동성
- ⑨ earnings_proximity: 실적 발표 근접도
- ⑩ topic_saturation: 주제 포화도

### 2. General News 학습 데이터 추가
- Engine A confidence ≥ 0.8인 General News만 점진 추가
- 순환 의존 해소 후 확장

### 3. Gradient Boosting 전환
- LightGBM 모델
- Feature Importance 리포트
- A/B 테스트: LR vs LightGBM

### 4. 연속 학습
- 매주 incremental 학습
- 모델 버전 관리

## 의존성
- `lightgbm` 패키지 추가 (pyproject.toml)
- Phase 5 정상 운영 상태
