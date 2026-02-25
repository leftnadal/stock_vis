# Phase 5: ML Production Mode (✅ 완료)

## 기간
Week 11-12

## 목표
Shadow Mode 4주 검증 후 ML 가중치를 실제 운영에 적용. 자동 배포, LLM 정확도 측정, 주간 리포트.

## 구현 내용

### 1. ML Production Manager — `news/services/ml_production_manager.py`

**MLProductionManager** 클래스:

**자동 배포** (`check_auto_deploy`):
- 최근 4주 연속 Safety Gate 통과 (F1 >= 0.55) 확인
- Shadow 비교 agreement_rate >= 0.70 확인
- 조건 충족 시 최신 Shadow 모델을 자동 배포
- 이전 deployed 모델은 rolled_back으로 전환
- deployed_at 자동 기록

**LLM 정확도 측정** (`measure_llm_accuracy`):
- LLM 예측 방향(bullish/bearish/neutral) vs 실제 주가 변동 비교
- direction_accuracy: 방향 일치율
- importance_accuracy: 중요도 판정 일치율
- 최대 200건 측정, 상세 20건 sample_details 포함

**주간 성능 리포트** (`generate_weekly_report`):
- 모델 상태 (배포/최신 버전, F1)
- 성능 추이 (improving/stable/declining)
- LLM 정확도 (direction/importance)
- 데이터 통계 (총 labeled, 이번 주 신규)
- 추천 사항 자동 생성

**롤백** (`rollback_model`):
- deployed 모델 → rolled_back 전환
- 수동 가중치(DEFAULT_WEIGHTS)로 자동 복귀

**배포 가중치 조회** (`get_deployed_weights`):
- deployed 상태의 smoothed_weights 반환
- 없으면 None (수동 가중치 사용)

### 2. Engine C ML 가중치 자동 통합 — `news/services/news_classifier.py`

**변경 사항**:
- `NewsClassifier.__init__`에서 `_load_deployed_weights()` 호출
- deployed ML 모델이 있으면 해당 가중치를 Engine C에 자동 적용
- 없거나 오류 시 `DEFAULT_WEIGHTS`로 폴백
- 명시적 weights 전달 시 해당 값 우선 사용

### 3. Celery 태스크 — `news/tasks.py`

| 태스크 | 스케줄 | 설명 |
|--------|--------|------|
| `check_auto_deploy` | 일요일 04:00 EST | 자동 배포 조건 확인 + 실행 (5분 타임아웃) |
| `generate_weekly_ml_report` | 일요일 04:15 EST | 주간 ML 성능 리포트 (10분 타임아웃) |

### 4. Celery Beat 스케줄 — `config/celery.py`
- `check-auto-deploy`: 일요일 04:00, expires 1시간
- `generate-weekly-ml-report`: 일요일 04:15, expires 1시간

### 5. API 엔드포인트 — `news/api/views.py`

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/v1/news/ml-weekly-report/` | 주간 ML 성능 리포트 (1시간 캐시) |

### 6. 서비스 등록 — `news/services/__init__.py`
- `MLProductionManager` 추가

### 7. 프론트엔드

**타입** — `frontend/types/news.ts`:
- `MLWeeklyReportResponse` 추가

**서비스** — `frontend/services/newsService.ts`:
- `getMLWeeklyReport()` 추가

**훅** — `frontend/hooks/useNews.ts`:
- `useMLWeeklyReport()` 추가

## 테스트 — `tests/news/test_ml_production_manager.py`
- **56개 테스트** 전체 통과
- 테스트 범위:
  - Auto Deploy Check (11개)
  - LLM Accuracy (7개)
  - Weekly Report (6개)
  - Rollback (4개)
  - Get Deployed Weights (4개)
  - Engine Integration (4개)
  - Celery Tasks (5개)
  - API Endpoints (4개)
  - Beat Schedule (11개)

## 검증 결과
- 56개 신규 테스트 통과
- 전체 뉴스 테스트 587개 통과 (기존 490 + Phase 5 신규 56 + Phase 6 신규 41)
- API 엔드포인트 정상 응답: `/api/v1/news/ml-weekly-report/` → 200

## 운영 흐름 (일요일)
```
03:00  train_importance_model       (LR 학습)
03:30  generate_shadow_report       (Shadow 비교)
04:00  check_auto_deploy            (4주 연속 통과 시 자동 배포)
04:15  generate_weekly_ml_report    (주간 리포트)
```
