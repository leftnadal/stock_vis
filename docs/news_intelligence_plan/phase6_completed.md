# Phase 6: ML Phase 2 — LightGBM (✅ 완료)

## 기간
Month 3+

## 목표
LightGBM으로 Gradient Boosting 전환. 확장 Feature, General News 포함, A/B 테스트.

## 전환 조건 (3가지 모두 충족 시 자동 실행)
1. 데이터 10,000건+ (label 포함)
2. LR 정확도 3주 연속 정체 (<1%p 개선)
3. 확장 feature 데이터 수집 안정화 (sector coverage >= 50%)

## 구현 내용

### 1. 확장 Feature (⑥~⑩) — `news/services/ml_weight_optimizer.py`

**`extract_extended_features(article)`** → 10개 feature 반환:

| # | Feature | 설명 | 범위 |
|---|---------|------|------|
| ① | source_credibility | 소스 신뢰도 | 0~1 |
| ② | entity_count | 종목/섹터 매칭 수 | 0~1 |
| ③ | sentiment_magnitude | 감성 강도 | 0~1 |
| ④ | recency | 시의성 | 0~1 |
| ⑤ | keyword_relevance | 키워드 관련성 | 0~1 |
| ⑥ | publish_hour | 발행 시각 (0~23 정규화) | 0~1 |
| ⑦ | weekday | 요일 (0=월~6=일 정규화) | 0~1 |
| ⑧ | sector_volatility | 섹터 변동성 proxy | 0~1 |
| ⑨ | earnings_proximity | 실적 발표 근접도 | 0~1 |
| ⑩ | topic_saturation | 주제 포화도 | 0~1 |

**섹터 변동성 분류**:
- High (0.8): Technology, Cryptocurrency, Biotechnology, Energy, Semiconductors, Cannabis
- Low (0.3): Utilities, Consumer Staples, Healthcare, Real Estate
- Default (0.5): 기타

**실적 시즌 근접도**:
- 0.9: 1/4/7/10월 10일 이후 (실적 시즌)
- 0.7: 1/4/7/10월 1~9일
- 0.6: 2/5/8/11월 1~10일 (실적 시즌 직후)
- 0.3: 나머지

### 2. 확장 학습 데이터 — `prepare_extended_training_data()`
- Company News + General News (ml_label_confidence >= 0.8)
- 10개 feature 추출
- include_general 플래그로 General News 포함/제외 제어

### 3. LightGBM 모델 — `train_lightgbm()`
- LGBMClassifier (binary classification)
- `is_unbalance=True` (클래스 불균형 보정)
- `num_leaves=15`, `max_depth=4` (과적합 방지)
- `subsample=0.8`, `colsample_bytree=0.8`
- Time-Series Split 검증
- Feature Importance 리포트 자동 생성
- Engine C 가중치: 기존 5개 feature만 정규화하여 추출

### 4. A/B 테스트 — `ab_test()`
- 동일 데이터에서 LR vs LightGBM 비교
- LR: 5-feature (기존), LightGBM: 10-feature (확장)
- 판정 기준: F1 차이 > 0.02 → 해당 모델 승
- 결과: winner, f1_diff, recommendation

### 5. 전환 조건 체크 — `check_lightgbm_readiness()`

| 조건 | 기준 | 설명 |
|------|------|------|
| data_sufficient | labeled >= 10,000 | 충분한 학습 데이터 |
| lr_stagnation | F1 범위 < 1%p (3주) | LR 정확도 정체 |
| feature_stability | sector coverage >= 50% | 확장 feature 안정화 |

### 6. LightGBM 파이프라인 — `run_lightgbm_pipeline()`
1. 전환 조건 확인 (미충족 시 `not_ready` 반환)
2. 확장 데이터 준비 (10 features, General News 포함)
3. LightGBM 학습 + Time-Series CV
4. A/B 테스트 (LR 대비)
5. Safety Gate 3단계 검증
6. Weight Smoothing
7. MLModelHistory 저장 (`algorithm='lightgbm'`, `feature_count=10`)

### 7. 의존성 — `pyproject.toml`
- `lightgbm` 추가

### 8. Celery 태스크 — `news/tasks.py`

| 태스크 | 스케줄 | 설명 |
|--------|--------|------|
| `train_lightgbm_model` | 일요일 04:30 EST | LightGBM 학습 (조건 충족 시만, 30분 타임아웃) |

### 9. Celery Beat 스케줄 — `config/celery.py`
- `train-lightgbm-model`: 일요일 04:30, expires 2시간

### 10. API 엔드포인트 — `news/api/views.py`

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/v1/news/ml-lightgbm-readiness/` | LightGBM 전환 준비 상태 |

### 11. 모델 버전 규칙
- LR: `lr_v1_{YYYYMMDD}_{N}` (예: lr_v1_20260225_1)
- LightGBM: `lgbm_v2_{YYYYMMDD}_{N}` (예: lgbm_v2_20260225_1)

### 12. 프론트엔드

**타입** — `frontend/types/news.ts`:
- `LightGBMReadinessResponse` 추가

**서비스** — `frontend/services/newsService.ts`:
- `getLightGBMReadiness()` 추가

**훅** — `frontend/hooks/useNews.ts`:
- `useLightGBMReadiness()` 추가

## 테스트 — `tests/news/test_lightgbm.py`
- **41개 테스트** 전체 통과
- 테스트 범위:
  - Extended Features (12개)
  - Extended Training Data (5개)
  - LightGBM Training (5개)
  - A/B Test (5개)
  - LightGBM Readiness (6개)
  - LightGBM Pipeline (4개)
  - Version Generation (4개)

## 검증 결과
- 41개 신규 테스트 통과
- 전체 뉴스 테스트 587개 통과
- API 엔드포인트 정상 응답: `/api/v1/news/ml-lightgbm-readiness/` → 200

## 운영 흐름 (일요일 전체)
```
03:00  train_importance_model       (LR 학습)
03:30  generate_shadow_report       (Shadow 비교)
04:00  check_auto_deploy            (자동 배포 체크)
04:15  generate_weekly_ml_report    (주간 리포트)
04:30  train_lightgbm_model         (LightGBM 학습, 조건 충족 시)
```
