# News Intelligence Pipeline 모니터링 대시보드 설계서

- **버전**: v1.1 DRAFT (리뷰 피드백 8건 반영)
- **작성일**: 2026-03-19
- **작성자**: @backend
- **상태**: 설계 단계 (구현 전)

---

## 목차

1. [배경 및 목표](#1-배경-및-목표)
2. [현재 자산 분석](#2-현재-자산-분석)
3. [Phase A — 기존 데이터 노출 (백엔드)](#3-phase-a--기존-데이터-노출-백엔드)
4. [Phase A — 프론트엔드 대시보드](#4-phase-a--프론트엔드-대시보드)
5. [Phase B — 파이프라인 헬스 체크 (심화)](#5-phase-b--파이프라인-헬스-체크-심화)
6. [Phase C — 능동적 모니터링 (알림)](#6-phase-c--능동적-모니터링-알림)
7. [파일 변경 계획](#7-파일-변경-계획)
8. [구현 순서 및 의존성](#8-구현-순서-및-의존성)
9. [리스크 및 고려사항](#9-리스크-및-고려사항)
10. [절대 하지 말 것](#10-절대-하지-말-것)
11. [선행 작업: _log_collection() 커버리지 보강](#11-선행-작업-_log_collection-커버리지-보강)

---

## v1.1 변경 이력 (리뷰 피드백 반영)

| # | 피드백 | 반영 위치 |
|---|--------|----------|
| 1 | pipeline-health status 판정 — Phase별 `expected_interval_hours` + 평일/주말 구분 | §3.2 전면 개정 |
| 2 | `_log_collection()` 커버리지 — 선행 작업으로 격상, §10 예외 처리 | §11 신규, §10 수정 |
| 3 | pipeline-health 캐시 — `?force_refresh=true` 캐시 우회 옵션 | §3.2 캐시 정책 |
| 4 | llm-usage API — Phase 3 토큰 미추적 한계 명시, UI에서 경고 표시 | §3.4, §4.2 섹션 5 |
| 5 | NewsTab 비대화 — sub-tab 방식 확정 | §4.1 전면 개정 |
| 6 | ML Rollback — 2단계 플로우 (preview → confirm) | §5.3 전면 개정 |
| 7 | AlertLog trigger_type — TextChoices 정규화 | §6.3 모델 수정 |
| 8 | 기타: TruncDate 확정, KST 기준 날짜, 수집량 급감 평일 평균 비교 | §3.1, §3.2, §6.1 |

---

## §1. 배경 및 목표

### 현재 파이프라인 6단계 구조

News Intelligence Pipeline v3는 다음 단계로 구성되어 있다:

| Phase | 태스크 | 스케줄 | 역할 |
|-------|--------|--------|------|
| 1 | `collect_daily_news`, `collect_market_news`, `collect_category_news`, FMP/AV 배치 | 2회~5회/일 | 뉴스 수집 (Finnhub/Marketaux/FMP/AV) |
| 2 | `classify_news_batch` | 매 2시간 (평일) | Engine A/B/C — 종목 매칭, 섹터 분류, importance_score 계산 |
| 3 | `analyze_news_deep` | 매 2시간 (평일) | Gemini 2.5 Flash LLM 심층 분석 (Tier A/B/C) |
| 4 | `collect_ml_labels`, `sync_news_to_neo4j` | 매일 19:00 / 매 2시간 | ML Label 수집 + Neo4j 동기화 |
| 5 | `train_importance_model`, `generate_shadow_report`, `check_auto_deploy` | 매주 일요일 새벽 | ML 학습 + Shadow Mode + 자동 배포 |
| 6 | `train_lightgbm_model`, `generate_weekly_ml_report`, `monitor_ml_performance` | 매주 일요일 새벽 | LightGBM 전환 + 주간 리포트 + 하락 감지 |

### 문제 상황

- `NewsCollectionLog`, `MLModelHistory` 등 모델에 운영 데이터가 지속적으로 쌓이고 있다.
- `ml-status`, `ml-weekly-report`, `ml-shadow-report`, `ml-lightgbm-readiness` API가 이미 존재한다.
- **하지만 관리자가 이를 한눈에 볼 수 있는 UI가 없다.**
- 현재 `NewsTab`은 기사 수집량, 소스 분포, 키워드 이력, 감성 요약만 보여준다.
- 파이프라인 장애, ML 성능 하락, LLM 에러 폭증 등 이상 상황을 발견하려면 DB를 직접 조회해야 한다.

### 목표

- 관리자가 파이프라인 6단계의 건강 상태를 한눈에 파악한다.
- 이상 징후(에러 급증, ML F1 하락, Neo4j 연결 실패) 발생 시 즉시 인지하고 대응한다.
- 기존 파이프라인 로직은 전혀 변경하지 않는다. 모니터링 레이어만 추가한다.

---

## §2. 현재 자산 분석

### 이미 있는 모델/데이터

| 모델 | 주요 필드 | 용도 |
|------|-----------|------|
| `NewsCollectionLog` | `task_name`, `provider`, `executed_at`, `symbols_tried`, `articles_new`, `articles_dup`, `api_calls`, `errors`, `duration_sec` | 수집 태스크 실행 결과 로그 |
| `MLModelHistory` | `model_version`, `algorithm`, `training_samples`, `feature_count`, `f1_score`, `precision`, `recall`, `accuracy`, `weights`, `smoothed_weights`, `feature_importance`, `training_config`, `safety_gate_passed`, `safety_gate_details`, `deployment_status`, `deployed_at`, `shadow_comparison`, `trained_at` | ML 모델 학습 이력 |
| `DailyNewsKeyword` | `date`, `keywords`, `total_news_count`, `sources`, `status`, `llm_model`, `generation_time_ms`, `prompt_tokens`, `completion_tokens`, `error_message` | 일별 키워드 추출 + LLM 토큰 사용량 |
| `NewsCollectionCategory` | `name`, `category_type`, `value`, `is_active`, `priority`, `last_collected_at`, `last_article_count`, `last_symbol_count`, `total_collections`, `last_error` | 카테고리별 수집 통계 |
| `NewsArticle` | `importance_score`, `llm_analyzed`, `llm_analysis`, `ml_label_24h`, `ml_label_important` | 분류/LLM 분석 결과 |

### 이미 있는 API

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `GET /api/v1/news/ml-status/` | GET | ML 모델 현재 상태 (latest, deployed, labeled_data_count) |
| `GET /api/v1/news/ml-weekly-report/` | GET | 주간 ML 성능 리포트 (period, model_status, performance_trend, llm_accuracy, data_stats, recommendations) |
| `GET /api/v1/news/ml-shadow-report/` | GET | Shadow Mode 비교 리포트 |
| `GET /api/v1/news/ml-lightgbm-readiness/` | GET | LightGBM 전환 준비 상태 |
| `GET /api/v1/news/daily-keywords/` | GET | 일별 키워드 + 토큰 사용량 |

### 이미 있는 서비스 함수

| 함수 | 위치 | 역할 |
|------|------|------|
| `MLProductionManager.generate_weekly_report()` | `news/services/ml_production_manager.py` | 주간 리포트 생성 (f1_trend, llm_accuracy, data_stats, recommendations 포함) |
| `MLProductionManager.detect_consecutive_decline()` | 동일 | 3주 연속 F1 하락 감지 |
| `MLProductionManager.rollback_model()` | 동일 | 배포 모델 롤백 |
| `MLWeightOptimizer.get_current_status()` | `news/services/ml_weight_optimizer.py` | ML 상태 조회 |
| `MLWeightOptimizer.check_lightgbm_readiness()` | 동일 | LightGBM 전환 조건 확인 |

### 이미 있는 프론트엔드

- `/admin` 페이지: `AdminTabNav` + 6개 탭 (`overview`, `stocks`, `screener`, `market-pulse`, `news`, `system`)
- `NewsTab` (`frontend/components/admin/NewsTab.tsx`): 기사 수집량, 소스 분포, 키워드 이력, 감성 분석, 카테고리 관리자
- `useAdminNews` hook: `adminService.getNewsStatus()` 호출, `staleTime: 30_000`
- 공용 컴포넌트: `SummaryCard`, `StatusBadge`, `TaskLogViewer`, `IssueList`, `ActionButton`
- `AdminTab` 타입: `'overview' | 'stocks' | 'screener' | 'market-pulse' | 'news' | 'system'`

### 빠진 것 (이번 설계 범위)

| 누락 항목 | 중요도 |
|-----------|--------|
| `GET /api/v1/news/collection-logs/` API — NewsCollectionLog 노출 | 높음 |
| `GET /api/v1/news/pipeline-health/` API — 6 Phase 통합 상태 | 높음 |
| `GET /api/v1/news/ml-trend/` API — ML F1 추이 (MLModelHistory 기반) | 중간 |
| `GET /api/v1/news/llm-usage/` API — LLM 토큰 비용 추적 | 중간 |
| 프론트엔드 Pipeline 모니터링 대시보드 (NewsTab 내 섹션 추가) | 높음 |
| AlertLog 모델 + 인앱 알림 시스템 | 낮음 (Phase C) |

---

## §3. Phase A — 기존 데이터 노출 (백엔드)

> 목적: 이미 DB에 있는 데이터를 API로 노출한다. 비즈니스 로직 변경 없음.

### §3.1 CollectionLog API

**엔드포인트**: `GET /api/v1/news/collection-logs/`

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `days` | int | 7 | 조회 기간 (최대 30) |
| `provider` | str | (전체) | `finnhub`, `marketaux`, `fmp`, `alpha_vantage` 필터 |
| `task_name` | str | (전체) | 태스크 이름 필터 |

**응답 구조**:

```json
{
  "period_days": 7,
  "total_records": 148,
  "logs": [
    {
      "id": 1042,
      "task_name": "collect_sp500_news_fmp_batch",
      "provider": "fmp",
      "executed_at": "2026-03-19T06:15:32Z",
      "symbols_tried": 84,
      "articles_new": 312,
      "articles_dup": 88,
      "api_calls": 0,
      "errors": 2,
      "duration_sec": 127.4
    }
  ],
  "aggregated": {
    "by_provider": {
      "fmp": {
        "total_runs": 35,
        "total_new": 4820,
        "total_dup": 1240,
        "total_errors": 12,
        "avg_duration_sec": 134.2,
        "success_rate": 0.966
      },
      "finnhub": {
        "total_runs": 14,
        "total_new": 890,
        "total_dup": 310,
        "total_errors": 1,
        "avg_duration_sec": 72.1,
        "success_rate": 0.929
      },
      "marketaux": {
        "total_runs": 14,
        "total_new": 145,
        "total_dup": 38,
        "total_errors": 0,
        "avg_duration_sec": 18.5,
        "success_rate": 1.0
      },
      "alpha_vantage": {
        "total_runs": 14,
        "total_new": 220,
        "total_dup": 90,
        "total_errors": 3,
        "avg_duration_sec": 45.8,
        "success_rate": 0.786
      }
    },
    "daily_summary": [
      {
        "date": "2026-03-19",
        "total_new": 1024,
        "total_dup": 287,
        "total_errors": 4,
        "runs": 22
      }
    ]
  }
}
```

**구현 위치**: `news/api/views.py` — `NewsViewSet`에 `@action` 추가

```python
@action(detail=False, methods=['get'], url_path='collection-logs')
def collection_logs(self, request):
    ...
```

**필요한 쿼리**:
- `NewsCollectionLog.objects.filter(executed_at__gte=cutoff)` — 기간 필터
- `.values('provider').annotate(total_runs=Count('id'), ...)` — provider별 집계
- `TruncDate('executed_at')` 사용한 일별 집계 (`.extra()` 사용 금지 — deprecated 방향)

**날짜 기준**: `days=1`은 "최근 24시간"이 아니라 **KST 자정 기준 오늘**을 의미한다. 서버 시간이 UTC일 경우 `KST_MIDNIGHT = now_kst.replace(hour=0, minute=0, second=0)` 으로 cutoff를 계산한다. 일별 집계도 KST 기준 날짜로 `TruncDate` + `tzinfo=KST` 적용.

**캐시**: 5분 (`cache.set(cache_key, data, 300)`)

---

### §3.2 Pipeline Health API

**엔드포인트**: `GET /api/v1/news/pipeline-health/`

파이프라인 6 Phase의 마지막 실행 시각과 상태를 한 번에 반환한다. 관리자가 어느 Phase가 마지막으로 실행됐는지, 오류가 있었는지 확인하는 용도다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `force_refresh` | bool | false | `true`이면 캐시 우회. 장애 디버깅 시 사용 |

#### Phase별 expected_interval 및 status 판정

각 Phase의 스케줄이 다르므로, **status 판정 기준을 Phase별로 개별 정의**한다. 응답에 `expected_interval_hours`를 포함하여 프론트엔드에서도 독립적으로 판단 가능하게 한다.

| Phase | expected_interval_hours | 평일 전용 | stale 기준 | 비고 |
|-------|------------------------|-----------|-----------|------|
| 1 (수집) | 12 | No (매일) | 12h 초과 | collect_daily_news 2회/일 |
| 2 (분류) | 3 | **Yes** | 3h 초과 (평일), 주말 면제 | 매 2시간 (평일만) |
| 3 (LLM 분석) | 3 | **Yes** | 3h 초과 (평일), 주말 면제 | 매 2시간 (평일만) |
| 4 (ML Label + Neo4j) | 26 | No | label: 26h, neo4j: 3h | label은 1일 1회, neo4j는 2시간 |
| 5 (ML 학습) | 192 (8일) | No | 8일 초과 | 주간 태스크 (일요일) |
| 6 (LightGBM) | 192 (8일) | No | 8일 초과 | 주간 태스크 (일요일) |

**평일/주말 판정 로직** (Phase 2, 3):

```python
from datetime import datetime
import pytz

KST = pytz.timezone('Asia/Seoul')

def is_weekend_kst() -> bool:
    """KST 기준 토요일(5) 또는 일요일(6)인지 판정"""
    return datetime.now(KST).weekday() >= 5

def determine_phase_status(phase: int, last_run: datetime, error_rate: float) -> str:
    config = PHASE_CONFIG[phase]
    hours_since = (now - last_run).total_seconds() / 3600

    # 평일 전용 태스크의 주말 면제
    if config['weekday_only'] and is_weekend_kst():
        # 금요일 마지막 실행 기준: 최대 ~60h (금 18시 → 월 06시)
        if hours_since <= 62:
            return 'ok' if error_rate < 0.1 else 'warning'
        return 'stale'  # 금요일에도 실행 안 됐으면 stale

    if hours_since > config['expected_interval_hours']:
        return 'stale'
    if error_rate > 0.3:
        return 'error'
    if error_rate > 0.1:
        return 'warning'
    return 'ok'
```

**PHASE_CONFIG 상수**:

```python
PHASE_CONFIG = {
    1: {'expected_interval_hours': 12, 'weekday_only': False, 'name': '뉴스 수집'},
    2: {'expected_interval_hours': 3,  'weekday_only': True,  'name': '뉴스 분류 (Engine A/B/C)'},
    3: {'expected_interval_hours': 3,  'weekday_only': True,  'name': 'LLM 심층 분석'},
    4: {'expected_interval_hours': 26, 'weekday_only': False, 'name': 'ML Label + Neo4j 동기화'},
    5: {'expected_interval_hours': 192, 'weekday_only': False, 'name': 'ML 학습 + Shadow Mode'},
    6: {'expected_interval_hours': 192, 'weekday_only': False, 'name': 'LightGBM + 주간 리포트'},
}
```

**응답 구조**:

```json
{
  "generated_at": "2026-03-19T14:30:00Z",
  "is_weekend_kst": false,
  "phases": [
    {
      "phase": 1,
      "name": "뉴스 수집",
      "expected_interval_hours": 12,
      "weekday_only": false,
      "last_run": "2026-03-19T14:15:00Z",
      "hours_since_last_run": 0.25,
      "status": "ok",
      "recent_errors": 2,
      "recent_new": 1024,
      "providers_active": ["fmp", "finnhub", "marketaux", "alpha_vantage"]
    },
    {
      "phase": 2,
      "name": "뉴스 분류 (Engine A/B/C)",
      "expected_interval_hours": 3,
      "weekday_only": true,
      "last_run": "2026-03-19T14:15:00Z",
      "hours_since_last_run": 0.25,
      "status": "ok",
      "classified_today": 842,
      "errors_today": 3
    },
    {
      "phase": 3,
      "name": "LLM 심층 분석",
      "expected_interval_hours": 3,
      "weekday_only": true,
      "last_run": "2026-03-19T14:30:00Z",
      "hours_since_last_run": 0.0,
      "status": "ok",
      "analyzed_today": 127,
      "errors_today": 1,
      "pending": 14
    },
    {
      "phase": 4,
      "name": "ML Label + Neo4j 동기화",
      "expected_interval_hours": 26,
      "weekday_only": false,
      "last_label_run": "2026-03-18T19:05:00Z",
      "last_neo4j_run": "2026-03-19T14:45:00Z",
      "hours_since_last_run": 19.4,
      "status": "ok",
      "labeled_total": 8420,
      "neo4j_available": true
    },
    {
      "phase": 5,
      "name": "ML 학습 + Shadow Mode",
      "expected_interval_hours": 192,
      "weekday_only": false,
      "last_run": "2026-03-16T03:15:00Z",
      "hours_since_last_run": 83.25,
      "status": "ok",
      "deployed_version": "lr_v1_20260316_1",
      "deployed_f1": 0.681,
      "deployment_status": "deployed"
    },
    {
      "phase": 6,
      "name": "LightGBM + 주간 리포트",
      "expected_interval_hours": 192,
      "weekday_only": false,
      "last_run": "2026-03-16T04:30:00Z",
      "hours_since_last_run": 82.0,
      "status": "ok",
      "lightgbm_ready": false,
      "lightgbm_conditions": {
        "data_sufficient": false,
        "lr_stagnation": true,
        "feature_stability": true
      }
    }
  ],
  "ml_summary": {
    "deployed_version": "lr_v1_20260316_1",
    "deployed_f1": 0.681,
    "deployment_status": "deployed",
    "labeled_data_count": 8420,
    "ready_for_training": true
  },
  "llm_summary": {
    "total_analyzed_today": 127,
    "prompt_tokens_today": 48200,
    "completion_tokens_today": 12300,
    "error_rate_today": 0.008
  }
}
```

**status 값 정의** (Phase별 차등 적용):
- `"ok"`: `expected_interval_hours` 내 실행 완료 + 에러율 < 10%
- `"warning"`: 기간 내 실행 완료, 에러율 10~30%
- `"error"`: 에러율 > 30% 또는 실행 자체 없음 (기간 내)
- `"stale"`: 마지막 실행이 `expected_interval_hours` 초과
- **평일 전용 태스크 주말 면제**: Phase 2/3은 토/일(KST)에 `expected_interval_hours` 대신 62시간(금 18시→월 08시)까지 ok 유지

**구현 위치**: `news/api/views.py` — `NewsViewSet`에 `@action` 추가

**캐시 정책**:
- 기본: 5분 캐시
- `?force_refresh=true`: 캐시 우회 (장애 디버깅 시 최신 데이터 즉시 확인용)
- 구현: `if not request.query_params.get('force_refresh'): cached = cache.get(key); if cached: return cached`

---

### §3.3 ML Trend API

**엔드포인트**: `GET /api/v1/news/ml-trend/`

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `weeks` | int | 12 | 조회 기간 (최대 52) |

`MLModelHistory`를 기반으로 주간 F1/Precision/Recall 추이와 Feature Importance 변화를 반환한다.

**응답 구조**:

```json
{
  "weeks": 12,
  "history": [
    {
      "model_version": "lr_v1_20260113_1",
      "trained_at": "2026-01-13T03:15:00Z",
      "algorithm": "logistic_regression",
      "f1_score": 0.612,
      "precision": 0.634,
      "recall": 0.591,
      "accuracy": 0.678,
      "training_samples": 4200,
      "safety_gate_passed": true,
      "deployment_status": "rolled_back"
    },
    {
      "model_version": "lr_v1_20260316_1",
      "trained_at": "2026-03-16T03:15:00Z",
      "algorithm": "logistic_regression",
      "f1_score": 0.681,
      "precision": 0.703,
      "recall": 0.661,
      "accuracy": 0.724,
      "training_samples": 8420,
      "safety_gate_passed": true,
      "deployment_status": "deployed"
    }
  ],
  "latest_feature_importance": {
    "source_credibility": 0.182,
    "entity_count": 0.241,
    "sentiment_magnitude": 0.198,
    "recency": 0.213,
    "keyword_relevance": 0.166
  },
  "trend_summary": {
    "f1_direction": "improving",
    "f1_change_total": 0.069,
    "avg_f1": 0.648,
    "consecutive_decline": false
  }
}
```

**구현 위치**: `news/api/views.py` — `NewsViewSet`에 `@action` 추가

**캐시**: 1시간

---

### §3.4 LLM Usage API

**엔드포인트**: `GET /api/v1/news/llm-usage/`

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `days` | int | 30 | 조회 기간 |

`DailyNewsKeyword`의 `prompt_tokens`/`completion_tokens` + `NewsArticle.llm_analyzed`를 집계한다.

> **중요 제한사항**: `NewsDeepAnalyzer`(Phase 3)의 LLM 호출은 현재 토큰 수를 저장하지 않는다. Phase 3이 전체 LLM 비용의 대부분을 차지할 것으로 예상되므로, 이 API는 **키워드 추출 비용만 반영하며 심층 분석 비용은 미포함**이다. Phase B에서 `NewsDeepAnalyzer`에 토큰 로깅을 추가한 뒤 통합 API로 확장한다. Phase A에서는 이 한계를 API 응답과 프론트엔드 UI 양쪽에 명확히 표시한다.

**응답 구조**:

```json
{
  "period_days": 30,
  "keyword_extraction": {
    "daily": [
      {
        "date": "2026-03-19",
        "status": "completed",
        "prompt_tokens": 12400,
        "completion_tokens": 3200,
        "total_tokens": 15600,
        "generation_time_ms": 4820,
        "total_news_analyzed": 312
      }
    ],
    "totals": {
      "prompt_tokens": 348000,
      "completion_tokens": 89000,
      "total_tokens": 437000,
      "success_days": 28,
      "failed_days": 2,
      "avg_generation_time_ms": 5100
    }
  },
  "deep_analysis": {
    "total_analyzed": 3840,
    "today_analyzed": 127,
    "pending_today": 14,
    "tier_breakdown": {
      "A": 2140,
      "B": 1420,
      "C": 280
    },
    "coverage_warning": "키워드 추출 토큰만 집계됨. Phase 3 심층 분석(전체 LLM 비용의 대부분)은 미포함 — Phase B에서 추가 예정"
  }
}
```

**구현 위치**: `news/api/views.py` — `NewsViewSet`에 `@action` 추가

**캐시**: 1시간

---

## §4. Phase A — 프론트엔드 대시보드

### §4.1 페이지 구조 — Sub-tab 방식 확정

현재 `/admin` 페이지는 `AdminTabNav` + 탭 6개 구조를 가진다. `NewsTab`이 이미 `id: 'news'`로 존재한다. 별도 페이지를 만드는 것보다 **기존 NewsTab 내에 sub-tab을 추가**하는 방식을 택한다.

이유:
- `AdminTab` 타입을 변경하지 않아도 된다.
- 기존 `useAdminNews` hook의 확장으로 데이터를 가져올 수 있다.
- 관리자는 이미 "뉴스" 탭에서 관련 정보를 기대한다.
- **10개 섹션이 한 탭에 들어가면 스크롤이 과도하므로**, sub-tab으로 분리하여 독립된 뷰로 동작하게 한다.

**구조: NewsTab 내부 sub-tab 2개**

```
NewsTab
├── [sub-tab] 뉴스 현황              ← 기존 5개 섹션 (변경 없음)
│   ├── Article Stats (SummaryCard x4)
│   ├── Source Distribution
│   ├── Keyword History
│   ├── Sentiment 요약
│   └── NewsCollectionCategory Manager
│
└── [sub-tab] 파이프라인              ← 신규 5개 섹션
    ├── Pipeline Status Bar
    ├── Collection Stats (KST 오늘)
    ├── ML Model Card + F1 추이
    ├── Recent Errors
    └── LLM Usage Summary
```

**sub-tab 구현**:

```typescript
type NewsSubTab = 'overview' | 'pipeline'

// NewsTab 내부에서 useState로 관리
const [subTab, setSubTab] = useState<NewsSubTab>('overview')
```

- sub-tab 전환은 `useState` (URL 변경 없음, 탭 내부 상태)
- 기본값 `'overview'` — 기존 동작 유지
- pipeline sub-tab 선택 시에만 `useNewsPipeline()` hook 활성화 (불필요한 API 호출 방지)

### §4.2 섹션 레이아웃

#### 섹션 1: Pipeline Status Bar

6개 Phase 아이콘 + 마지막 실행 시각 + 상태 배지. `GET /api/v1/news/pipeline-health/` 사용.

```
[ Phase 1: 수집 ✅ ] [ Phase 2: 분류 ✅ ] [ Phase 3: LLM ✅ ]
[ Phase 4: ML Label ✅ ] [ Phase 5: 모델 ✅ ] [ Phase 6: LightGBM ⚠️ ]
마지막 업데이트: 2026-03-19 14:30
```

상태 색상:
- `ok` → 초록 (`text-green-600`)
- `warning` → 노란 (`text-yellow-600`)
- `error` → 빨간 (`text-red-600`)
- `stale` → 회색 (`text-gray-400`)

#### 섹션 2: Collection Stats (KST 오늘)

provider별 수집 현황 테이블. `GET /api/v1/news/collection-logs/?days=1` 사용 (KST 자정 기준 오늘 데이터).

```
Provider    | New Articles | Dup | Errors | Runs | Avg Duration
fmp         | 1,024        | 287 | 4      | 5    | 134s
finnhub     | 312          | 89  | 0      | 2    | 72s
marketaux   | 48           | 12  | 0      | 2    | 18s
alpha_vantage | 88         | 31  | 2      | 2    | 46s
```

#### 섹션 3: ML Model Card

현재 배포 모델 정보 + 최근 12주 F1 추이 라인차트. `GET /api/v1/news/ml-trend/` 사용.

```
[Deployed] lr_v1_20260316_1
F1: 0.681  Precision: 0.703  Recall: 0.661
Training Samples: 8,420  Algorithm: Logistic Regression
Deployed: 2026-03-16 04:05

--- F1 Score 추이 (12주) ---
0.70 |          ●
0.65 |      ● ●   ●
0.60 | ●  ●
0.55 +--+--+--+--+--+
     W1 W2 W3 ... W12
```

차트 라이브러리: `recharts` v3.3.0이 이미 `package.json`에 포함되어 있다 (Thesis Control Phase 3에서 추가). 그대로 사용.

#### 섹션 4: Recent Errors

최근 에러 목록. `GET /api/v1/news/collection-logs/?days=3` + errors > 0 필터링.

```
[FMP] collect_sp500_news_fmp_batch — 2026-03-19 06:15 — errors: 3 (symbols: 84)
[AV] collect_av_single_symbol — 2026-03-18 14:30 — errors: 2 (symbols: 1)
```

아코디언 형태로 접을 수 있다. `IssueList` 공용 컴포넌트 재사용 가능.

#### 섹션 5: LLM Usage Summary

`GET /api/v1/news/llm-usage/?days=7` 기반. 최근 7일 토큰 사용량 요약 카드.

**경고 배너 필수 표시**: 카드 상단에 `text-yellow-600` 배경으로 다음 문구를 항상 표시한다:

```
⚠ 키워드 추출 비용만 반영됩니다. Phase 3 심층 분석 비용(전체의 대부분)은 미포함입니다.
```

```
키워드 추출 (7일)
  총 토큰: 437,000 (prompt: 348,000 / completion: 89,000)
  성공일: 7 / 7  평균 생성시간: 5,100ms

LLM 심층 분석 (오늘) — 건수만 표시, 토큰 미추적
  분석 완료: 127건  대기: 14건
  Tier A: 89 / Tier B: 32 / Tier C: 6
```

### §4.3 컴포넌트 목록

신규 생성 파일:

| 파일 경로 | 역할 |
|----------|------|
| `frontend/components/admin/news/PipelineStatusBar.tsx` | 6개 Phase 상태 표시 |
| `frontend/components/admin/news/CollectionStatsTable.tsx` | provider별 24h 수집 통계 테이블 |
| `frontend/components/admin/news/MLModelCard.tsx` | 현재 배포 모델 정보 카드 |
| `frontend/components/admin/news/MLTrendChart.tsx` | F1 추이 라인차트 |
| `frontend/components/admin/news/RecentErrorsList.tsx` | 최근 에러 목록 아코디언 |
| `frontend/components/admin/news/LLMUsageSummary.tsx` | LLM 토큰 사용량 요약 |

신규 hooks:

| 파일 경로 | 역할 |
|----------|------|
| `frontend/hooks/useNewsPipeline.ts` | pipeline-health, collection-logs, ml-trend, llm-usage 조회 |

신규 서비스:

| 파일 경로 | 역할 |
|----------|------|
| `frontend/services/newsPipelineService.ts` | 위 4개 API 클라이언트 함수 |

수정 파일:

| 파일 경로 | 변경 내용 |
|----------|----------|
| `frontend/components/admin/NewsTab.tsx` | sub-tab 구조 추가 (`'overview' \| 'pipeline'`) + pipeline 섹션 5개 |

---

## §5. Phase B — 파이프라인 헬스 체크 (심화)

> Phase A 완료 후 구현. 더 깊은 시각화와 관리 기능 추가.

### §5.1 Task Timeline (24시간 간트 차트)

`NewsCollectionLog`의 `executed_at` + `duration_sec` 기반으로 24시간 간트 차트를 렌더링한다.

- x축: 시간 (0~24h)
- y축: 태스크 이름
- 막대 색상: 성공(초록), 에러 포함(노란), 실패(빨간)
- 해상도: 15분 단위 버킷

신규 API: `GET /api/v1/news/task-timeline/?hours=24`

```json
{
  "hours": 24,
  "timeline": [
    {
      "task_name": "collect_sp500_news_fmp_batch",
      "provider": "fmp",
      "start": "2026-03-19T06:15:00Z",
      "end": "2026-03-19T06:17:07Z",
      "duration_sec": 127.4,
      "articles_new": 312,
      "errors": 0,
      "status": "ok"
    }
  ]
}
```

### §5.2 Neo4j 동기화 상태

`NewsNeo4jSyncService.is_available()` + 동기화 통계.

신규 API: `GET /api/v1/news/neo4j-status/`

```json
{
  "available": true,
  "last_sync": "2026-03-19T14:45:00Z",
  "synced_today": 127,
  "pending_sync": 14,
  "cleanup_last_run": "2026-03-19T04:00:00Z"
}
```

### §5.3 ML 모델 비교 뷰 + 롤백 2단계 플로우

Shadow vs Deployed 상세 비교. `MLModelHistory.shadow_comparison` 필드 활용.

#### ML Rollback — 2단계 안전 플로우

운영 모델을 되돌리는 위험한 액션이므로, **preview → confirm 2단계**로 구성한다.

**Step 1: 롤백 영향 미리보기**

`GET /api/v1/news/ml-rollback-preview/`

```json
{
  "current_deployed": {
    "model_version": "lr_v1_20260316_1",
    "algorithm": "logistic_regression",
    "f1_score": 0.681,
    "deployed_at": "2026-03-16T04:05:00Z",
    "smoothed_weights": {
      "source_credibility": 0.15,
      "entity_count": 0.22,
      "sentiment_magnitude": 0.19,
      "recency": 0.24,
      "keyword_relevance": 0.20
    }
  },
  "rollback_target": "DEFAULT_WEIGHTS (수동 가중치)",
  "default_weights": {
    "source_credibility": 0.15,
    "entity_count": 0.20,
    "sentiment_magnitude": 0.20,
    "recency": 0.25,
    "keyword_relevance": 0.20
  },
  "impact_warning": "롤백 시 Engine C가 학습된 가중치 대신 기본 가중치를 사용합니다. 다음 일요일 학습까지 수동 가중치로 분류됩니다."
}
```

**Step 2: 롤백 실행 (confirm 필수)**

`POST /api/v1/news/ml-rollback/`

```json
// Request:
{
  "confirm": true
}

// Response (성공):
{
  "status": "rolled_back",
  "rolled_back_version": "lr_v1_20260316_1",
  "fallback": "manual_weights",
  "rolled_back_at": "2026-03-19T15:30:00Z"
}

// Response (confirm 누락):
// 400 Bad Request
{
  "error": "롤백을 실행하려면 {\"confirm\": true}를 전송하세요."
}
```

구현: `confirm=True` 검증 후 `MLProductionManager.rollback_model()` 호출.

**프론트엔드 UX 플로우**:
1. "롤백" 버튼 클릭 → `GET /ml-rollback-preview/` 호출
2. 모달에 현재 모델 vs 롤백 대상 비교 + 경고 메시지 표시
3. "확인" 클릭 → `POST /ml-rollback/` 실행
4. 결과 표시 + pipeline-health 자동 새로고침

Feature Importance 히트맵: `MLModelHistory.feature_importance` JSON 필드를 5개 특성(source_credibility, entity_count, sentiment_magnitude, recency, keyword_relevance) × 최근 N주 히트맵으로 시각화.

---

## §6. Phase C — 능동적 모니터링 (알림)

> Phase B 완료 후 구현. 이상 징후 자동 감지 + 알림.

### §6.1 알림 트리거 정의

| 트리거 | 조건 | 심각도 |
|--------|------|--------|
| 태스크 연속 실패 | 동일 `task_name` 최근 3회 연속 `errors > 0` | HIGH |
| ML F1 급락 | 최신 모델 F1 - 이전 모델 F1 > 0.05p 하락 | HIGH |
| 키워드 추출 실패 | `DailyNewsKeyword.status == 'failed'` | MEDIUM |
| LLM 에러율 급등 | `analyze_news_deep` 기준 `errors / (analyzed + errors) > 0.2` 이상 | MEDIUM |
| Neo4j 연결 실패 | `sync_news_to_neo4j` 결과 `neo4j_unavailable: true` | HIGH |
| 수집량 급감 | **최근 5 평일 평균** 대비 `articles_new` 50% 이상 감소 (주말/공휴일 오탐 방지) | MEDIUM |
| 미분류 뉴스 누적 | `importance_score is null` 기사가 500건 초과 | LOW |

트리거 체크 주기: Celery Beat 30분마다 `check_pipeline_alerts` 태스크 (Phase C 신규 추가, @infra 협업 필요).

### §6.2 알림 채널

| 채널 | 구현 방법 | 우선순위 |
|------|-----------|---------|
| 인앱 알림 | `AlertLog` DB 저장 → API 폴링 | Phase C 필수 |
| Slack webhook | `settings.SLACK_WEBHOOK_URL` 환경변수 | 선택 |
| 이메일 | Django `send_mail` | 선택 |

인앱 알림: 관리자 페이지 상단에 미해결 알림 배지 표시. `/admin` 페이지 진입 시 `GET /api/v1/news/alerts/?resolved=false` 호출.

### §6.3 AlertLog 모델

Phase C에서 신규 생성할 모델:

```python
class AlertLog(models.Model):
    class Severity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    class TriggerType(models.TextChoices):
        CONSECUTIVE_TASK_FAILURE = 'consecutive_task_failure', '태스크 연속 실패'
        ML_F1_DECLINE = 'ml_f1_decline', 'ML F1 급락'
        KEYWORD_EXTRACTION_FAILURE = 'keyword_extraction_failure', '키워드 추출 실패'
        LLM_ERROR_SPIKE = 'llm_error_spike', 'LLM 에러율 급등'
        NEO4J_UNAVAILABLE = 'neo4j_unavailable', 'Neo4j 연결 실패'
        COLLECTION_DROP = 'collection_drop', '수집량 급감'
        UNCLASSIFIED_BACKLOG = 'unclassified_backlog', '미분류 뉴스 누적'

    trigger_type = models.CharField(max_length=50, choices=TriggerType.choices)

    severity = models.CharField(max_length=10, choices=Severity.choices)
    message = models.TextField()
    context = models.JSONField(null=True, blank=True)
    # 예: {"task_name": "collect_sp500_news_fmp_batch", "error_count": 3}

    is_resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'news_alert_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_resolved', '-created_at']),
            models.Index(fields=['trigger_type', '-created_at']),
        ]
```

**API**:
- `GET /api/v1/news/alerts/` — 알림 목록 (`?resolved=false`, `?severity=high`)
- `POST /api/v1/news/alerts/{id}/resolve/` — 알림 해결 처리

---

## §7. 파일 변경 계획

### Phase 0 (선행 작업)

| # | 파일 | 액션 | 예상 줄 |
|---|------|------|---------|
| 1 | `news/tasks.py` | MODIFY — 누락 태스크에 `_log_collection()` 호출 추가 (§11 참조) | +30줄 |

### Phase A (백엔드)

| # | 파일 | 액션 | 예상 줄 |
|---|------|------|---------|
| 1 | `news/api/views.py` | MODIFY — `collection_logs`, `pipeline_health`, `ml_trend`, `llm_usage` action 추가 | +200줄 |
| 2 | `news/api/urls.py` | 현재 `DefaultRouter` 사용 중 → ViewSet action으로 자동 등록, 변경 없음 | 0줄 |

### Phase A (프론트엔드)

| # | 파일 | 액션 | 예상 줄 |
|---|------|------|---------|
| 1 | `frontend/services/newsPipelineService.ts` | NEW | ~60줄 |
| 2 | `frontend/hooks/useNewsPipeline.ts` | NEW | ~80줄 |
| 3 | `frontend/components/admin/news/PipelineStatusBar.tsx` | NEW | ~80줄 |
| 4 | `frontend/components/admin/news/CollectionStatsTable.tsx` | NEW | ~70줄 |
| 5 | `frontend/components/admin/news/MLModelCard.tsx` | NEW | ~90줄 |
| 6 | `frontend/components/admin/news/MLTrendChart.tsx` | NEW | ~100줄 |
| 7 | `frontend/components/admin/news/RecentErrorsList.tsx` | NEW | ~70줄 |
| 8 | `frontend/components/admin/news/LLMUsageSummary.tsx` | NEW | ~60줄 |
| 9 | `frontend/components/admin/NewsTab.tsx` | MODIFY — sub-tab 구조 추가 (`overview` / `pipeline`) | +40줄 |
| 10 | `frontend/components/admin/news/NewsPipelineSubTab.tsx` | NEW — pipeline sub-tab 컨테이너 (5개 섹션 조합) | ~80줄 |

### Phase B (백엔드)

| # | 파일 | 액션 | 예상 줄 |
|---|------|------|---------|
| 1 | `news/api/views.py` | MODIFY — `task_timeline`, `neo4j_status`, `ml_rollback_preview`, `ml_rollback` action 추가 | +130줄 |

### Phase B (프론트엔드)

| # | 파일 | 액션 | 예상 줄 |
|---|------|------|---------|
| 1 | `frontend/components/admin/news/TaskTimelineChart.tsx` | NEW | ~120줄 |
| 2 | `frontend/components/admin/news/Neo4jStatusCard.tsx` | NEW | ~60줄 |
| 3 | `frontend/components/admin/news/MLCompareView.tsx` | NEW | ~150줄 |
| 4 | `frontend/hooks/useNewsPipeline.ts` | MODIFY — task_timeline, neo4j_status 추가 | +40줄 |

### Phase C (백엔드)

| # | 파일 | 액션 | 예상 줄 |
|---|------|------|---------|
| 1 | `news/models.py` | MODIFY — `AlertLog` 모델 추가 | +50줄 |
| 2 | `news/api/views.py` | MODIFY — `alerts`, `alerts_resolve` action 추가 | +60줄 |
| 3 | `news/admin.py` | MODIFY — `AlertLogAdmin` 추가 | +25줄 |
| 4 | `news/migrations/` | NEW — AlertLog 마이그레이션 | ~30줄 |

> Phase C의 `check_pipeline_alerts` Celery 태스크 및 Beat 스케줄 추가는 @infra 담당.

### Phase C (프론트엔드)

| # | 파일 | 액션 | 예상 줄 |
|---|------|------|---------|
| 1 | `frontend/components/admin/news/AlertBadge.tsx` | NEW | ~40줄 |
| 2 | `frontend/components/admin/news/AlertList.tsx` | NEW | ~80줄 |
| 3 | `frontend/app/admin/page.tsx` | MODIFY — 상단 알림 배지 추가 | +15줄 |

---

## §8. 구현 순서 및 의존성

```
Phase 0 (선행) — _log_collection() 커버리지 보강 (§11 참조)
    |
    | 로깅 보강 완료 후
    v
Phase A-BE (백엔드 API 4개: collection-logs, pipeline-health, ml-trend, llm-usage)
    |
    | 백엔드 API 완료 후
    v
Phase A-FE (프론트엔드: 서비스/훅/컴포넌트 6개 + NewsTab sub-tab 추가)
    |
    | 프론트엔드 기본 대시보드 완료 후
    v
Phase B-BE (task-timeline, neo4j-status, ml-rollback-preview, ml-rollback)
    |
    v
Phase B-FE (Task Timeline 차트, Neo4j 상태, ML 비교 뷰 + 롤백 2단계 모달)
    |
    v
Phase C-BE (AlertLog 모델 + API)
    |
    | @infra: check_pipeline_alerts 태스크 추가 필요
    v
Phase C-FE (알림 배지, 알림 목록)
```

**Phase 0 선행 작업**: `_log_collection()` 누락 태스크 보강. 약 0.5일 작업.
**Phase A 완료 목표**: 4개 API + 프론트엔드 sub-tab 대시보드. 약 2~3일 작업.

---

## §9. 리스크 및 고려사항

### 데이터 보존 및 성능

- **`NewsCollectionLog` 무한 증가**: 현재 보존 기간 없음. Phase A 구현 시 `collection-logs` API에서 `days` 파라미터 최대값 30으로 제한. 추후 `cleanup_old_collection_logs` 태스크 추가 권고 (90일 이후 삭제).
- **집계 쿼리 성능**: `collection-logs` API의 `by_provider` 집계는 `GROUP BY` + `COUNT`/`SUM` 쿼리. 기간이 길면 느릴 수 있다. `NewsCollectionLog` 테이블에 `(provider, executed_at)` 인덱스가 이미 존재하므로 7일 기준은 허용 범위 내. 30일 이상 요청은 캐시 TTL을 길게 설정(30분).
- **`pipeline_health` 응답 조립**: `NewsArticle`, `MLModelHistory`, `DailyNewsKeyword` 등 여러 테이블을 조회한다. 최대 5~6회 쿼리. 캐시 5분.

### 인증

- 모든 신규 API는 `IsAuthenticated` + `is_staff` 체크. `AllowAny`로 열면 안 된다.
- 현재 `NewsViewSet`의 기존 action들이 기본적으로 `IsAuthenticated` 또는 `AllowAny`를 섞어 쓰고 있다. 모니터링 API는 명시적으로 `permission_classes=[IsAdminUser]` 적용.
- `from rest_framework.permissions import IsAdminUser` 사용.

### 모바일 대응

- `PipelineStatusBar`: 6개 Phase 카드를 `grid-cols-2 sm:grid-cols-3 lg:grid-cols-6`으로 배치.
- `CollectionStatsTable`: `overflow-x-auto` 필수.
- `MLTrendChart`: 차트 가로 스크롤 or 7일/12주 토글.

### 차트 라이브러리

- `recharts` v3.3.0이 이미 `package.json`에 포함되어 있다 (Thesis Control Phase 3에서 추가).
- `MLTrendChart`, `TaskTimelineChart` 모두 recharts로 구현한다.

### `_log_collection()` 호출 현황 — Phase 0 선행 작업으로 해결

~~`tasks.py`의 `_log_collection()` 헬퍼는 현재 일부 태스크에서만 호출된다.~~ → **§11 선행 작업으로 해결**. Phase A 착수 전에 누락 태스크에 `_log_collection()` 호출을 추가하여 대시보드 데이터의 신뢰성을 확보한다. 상세는 §11 참조.

---

## §10. 절대 하지 말 것

- **기존 파이프라인 로직 변경 금지**: `news/services/news_classifier.py`, `news/services/news_deep_analyzer.py`, `news/services/ml_weight_optimizer.py`, `news/services/ml_production_manager.py` 수정 금지. 이번 작업은 순수 모니터링 레이어 추가다.
- **Celery Beat 스케줄 변경 금지**: `config/celery.py`의 기존 스케줄을 건드리지 않는다. Phase C의 `check_pipeline_alerts` 태스크 추가는 @infra에게 요청한다.
- **ML 모델 로직 변경 금지**: `MLModelHistory` 필드 추가도 하지 않는다. 현재 필드로 충분히 모니터링 가능하다.
- **일반 사용자 노출 금지**: 모든 신규 API에 `IsAdminUser` permission 적용. `AllowAny`로 열 경우 보안 위반.
- **기존 `NewsTab` 구조 파괴 금지**: 기존 5개 섹션(Article Stats, Source Distribution, Keyword History, Sentiment, CategoryManager)은 그대로 유지. 하단에 신규 섹션을 추가하는 방식만 허용.
- **`news/tasks.py` 내 태스크 비즈니스 로직 변경 금지**: 수집/분류/분석 로직은 건드리지 않는다. **단, `_log_collection()` 호출 추가는 예외** — 이는 비즈니스 로직 변경이 아니라 관측성(observability) 보강이므로 §11 선행 작업으로 허용한다.

---

## 부록: 기존 API 엔드포인트 정리 (참고)

현재 `GET /api/v1/news/` 하위에 존재하는 관련 엔드포인트:

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/v1/news/ml-status/` | ML 모델 상태 (기존) |
| `GET /api/v1/news/ml-weekly-report/` | 주간 ML 리포트 (기존) |
| `GET /api/v1/news/ml-shadow-report/` | Shadow 비교 리포트 (기존) |
| `GET /api/v1/news/ml-lightgbm-readiness/` | LightGBM 전환 준비 상태 (기존) |
| `GET /api/v1/news/daily-keywords/` | 일별 키워드 + 토큰 사용량 (기존) |
| `GET /api/v1/news/collection-logs/` | 수집 로그 집계 (신규, Phase A) |
| `GET /api/v1/news/pipeline-health/` | 파이프라인 통합 상태 (신규, Phase A) |
| `GET /api/v1/news/ml-trend/` | ML F1 추이 (신규, Phase A) |
| `GET /api/v1/news/llm-usage/` | LLM 토큰 사용량 (신규, Phase A) |
| `GET /api/v1/news/task-timeline/` | 태스크 타임라인 (신규, Phase B) |
| `GET /api/v1/news/neo4j-status/` | Neo4j 동기화 상태 (신규, Phase B) |
| `GET /api/v1/news/ml-rollback-preview/` | ML 롤백 영향 미리보기 (신규, Phase B) |
| `POST /api/v1/news/ml-rollback/` | ML 모델 롤백 실행 — `{"confirm": true}` 필수 (신규, Phase B) |
| `GET /api/v1/news/alerts/` | 파이프라인 알림 목록 (신규, Phase C) |
| `POST /api/v1/news/alerts/{id}/resolve/` | 알림 해결 처리 (신규, Phase C) |

> 모든 신규 엔드포인트는 `IsAdminUser` permission 적용 필요.

---

## §11. 선행 작업: `_log_collection()` 커버리지 보강

> **Phase A 착수 전 필수**. 대시보드 데이터 신뢰성의 전제 조건.

### 문제

현재 `_log_collection()` 헬퍼는 다음 4개 태스크에서만 호출된다:
- `collect_sp500_news_fmp_batch`
- `collect_press_releases_fmp`
- `collect_general_news_fmp`
- `collect_av_single_symbol`

**호출하지 않는 주요 태스크**:
- `collect_daily_news` (Finnhub/Marketaux — Phase 1 핵심)
- `collect_market_news` (General News)
- `collect_category_news` (카테고리별 수집)
- `classify_news_batch` (Phase 2)
- `analyze_news_deep` (Phase 3)
- `sync_news_to_neo4j` (Phase 4)

이 상태에서 `collection-logs` API를 만들면 FMP/AV 중심으로 편향된 통계가 나오고, `pipeline-health` Phase 1의 `recent_new` 수치가 실제보다 적게 표시된다.

### 해결

누락된 태스크에 `_log_collection()` 호출을 추가한다. **비즈니스 로직(수집/분류/분석 알고리즘)은 전혀 변경하지 않으며**, 태스크 함수 끝에 로깅 호출만 삽입한다.

### 변경 대상

| 태스크 | provider 값 | 추가 위치 |
|--------|------------|----------|
| `collect_daily_news` | `'finnhub'` / `'marketaux'` (루프 내 provider별) | 각 provider 수집 완료 후 |
| `collect_market_news` | `'fmp'` | 함수 끝 |
| `collect_category_news` | category의 provider에 따라 | 함수 끝 |
| `classify_news_batch` | `'classifier'` (provider 대신 engine 명시) | 함수 끝 |
| `analyze_news_deep` | `'gemini'` (LLM provider 명시) | 함수 끝 |
| `sync_news_to_neo4j` | `'neo4j'` | 함수 끝 |

### 추가 패턴 예시

```python
# collect_daily_news 내부, finnhub 수집 완료 후:
_log_collection(
    task_name='collect_daily_news',
    provider='finnhub',
    symbols_tried=len(symbols),
    articles_new=new_count,
    articles_dup=dup_count,
    errors=error_count,
    duration_sec=elapsed,
)
```

```python
# classify_news_batch 끝:
_log_collection(
    task_name='classify_news_batch',
    provider='classifier',
    symbols_tried=0,
    articles_new=classified_count,
    articles_dup=0,
    errors=error_count,
    duration_sec=elapsed,
)
```

### 예상 변경량

| 파일 | 변경 | 줄 수 |
|------|------|-------|
| `news/tasks.py` | 6개 태스크에 `_log_collection()` 호출 추가 | +30줄 |

### 원칙

- `_log_collection()` 헬퍼의 시그니처/로직은 변경하지 않는다.
- 태스크의 수집/분류/분석 로직은 변경하지 않는다.
- 기존에 이미 호출하는 4개 태스크는 건드리지 않는다.
- 에러 시에도 로깅이 누락되지 않도록 `try/finally` 패턴 적용:

```python
@shared_task(...)
def some_task():
    new_count = dup_count = error_count = 0
    start = time.time()
    try:
        # ... 기존 로직 ...
    finally:
        _log_collection(
            task_name='some_task',
            provider='...',
            symbols_tried=...,
            articles_new=new_count,
            articles_dup=dup_count,
            errors=error_count,
            duration_sec=time.time() - start,
        )
```
