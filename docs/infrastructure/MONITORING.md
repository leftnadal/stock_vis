# Monitoring & Observability Guide

Stock-Vis 프로젝트의 모니터링 및 로깅 설정 가이드입니다.

---

## 모니터링 구성요소

| 구성요소 | 도구 | 용도 |
|---------|------|------|
| Celery 모니터링 | Flower | 태스크 상태, 큐 상태 |
| API 모니터링 | Django Logging | 요청/응답, 에러 |
| Provider 모니터링 | Custom Logging | API 호출, Fallback |
| 인프라 모니터링 | Docker Stats | 컨테이너 리소스 |

---

## 1. Flower (Celery 모니터링)

### 실행

```bash
# 로컬 실행
celery -A config flower --port=5555

# Docker 환경 (자동 시작)
docker-compose up flower
```

### 접속

- URL: http://localhost:5555
- 기능:
  - 실시간 태스크 상태
  - Worker 상태
  - 큐 길이
  - 태스크 히스토리

### 주요 메트릭

| 메트릭 | 설명 | 경고 기준 |
|--------|------|----------|
| Active Tasks | 실행 중인 태스크 수 | > 100 |
| Failed Tasks | 실패한 태스크 수 | > 10/hour |
| Queue Length | 대기 중인 태스크 수 | > 500 |
| Worker Memory | Worker 메모리 사용량 | > 1GB |

---

## 2. Provider 모니터링

### Admin API 엔드포인트

```bash
# Provider 상태 조회
GET /api/v1/admin/providers/status/

# Rate Limit 상태
GET /api/v1/admin/providers/rate-limits/

# 캐시 상태
GET /api/v1/admin/providers/cache/

# Provider 테스트
POST /api/v1/admin/providers/test/
{
    "provider": "alpha_vantage",
    "endpoint": "quote",
    "symbol": "AAPL"
}
```

### 응답 예시

```json
{
    "providers": {
        "alpha_vantage": {
            "status": "healthy",
            "last_call": "2025-12-08T10:30:00Z",
            "success_rate": 98.5,
            "avg_response_time": 1.2
        },
        "fmp": {
            "status": "healthy",
            "last_call": "2025-12-08T10:25:00Z",
            "success_rate": 99.1,
            "avg_response_time": 0.8
        }
    },
    "fallback_enabled": true,
    "fallback_count_today": 3
}
```

### 로그 위치

```bash
# Provider 관련 로그
tail -f stocks.log | grep "provider"

# Fallback 이벤트
tail -f stocks.log | grep "Fallback"
```

---

## 3. Django Logging 설정

### 현재 설정 (`config/settings.py`)

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'stocks.log',
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'api_request': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'stocks': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 로그 레벨 가이드

| 레벨 | 용도 |
|------|------|
| DEBUG | 개발 디버깅 |
| INFO | 정상 작업 기록 |
| WARNING | 잠재적 문제 |
| ERROR | 에러 발생 |
| CRITICAL | 심각한 장애 |

---

## 4. 헬스 체크

### Backend 헬스 체크

```bash
# Django 헬스 체크
curl http://localhost:8000/api/v1/health/

# 응답
{
    "status": "healthy",
    "database": "connected",
    "redis": "connected",
    "timestamp": "2025-12-08T10:30:00Z"
}
```

### Docker 헬스 체크

```yaml
# docker-compose.yml에 이미 설정됨
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
  interval: 10s
  timeout: 5s
  retries: 5
```

---

## 5. 알림 설정 (선택)

### Slack 알림 예시

```python
# stocks/tasks.py에 추가 가능

import requests

def send_slack_alert(message):
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if webhook_url:
        requests.post(webhook_url, json={'text': message})

# 사용 예시
@shared_task
def update_stock_with_provider(symbol):
    try:
        # ... 작업 수행
    except Exception as e:
        send_slack_alert(f"Provider 작업 실패: {symbol} - {str(e)}")
        raise
```

---

## 6. 모니터링 대시보드

### Flower 대시보드

- 실시간 태스크 모니터링
- Worker 상태 확인
- 태스크 재시도/취소

### Provider Admin 대시보드 (계획)

| 지표 | 설명 |
|------|------|
| API 호출 횟수 | Provider별 일일 호출 수 |
| Fallback 횟수 | 대체 Provider 사용 횟수 |
| 에러율 | Provider별 에러 비율 |
| 응답 시간 | 평균 응답 시간 |

---

## 7. 문제 해결

### 일반적인 문제

| 문제 | 원인 | 해결 |
|------|------|------|
| Rate Limit 에러 | API 호출 빈도 초과 | 12초 대기, Fallback 활성화 |
| Celery 태스크 실패 | Worker 다운 | Worker 재시작 |
| DB 연결 실패 | PostgreSQL 다운 | DB 상태 확인 |
| Redis 연결 실패 | Redis 다운 | Redis 재시작 |

### 디버깅 명령어

```bash
# Celery Worker 상태
celery -A config inspect active

# Redis 연결 확인
redis-cli ping

# PostgreSQL 연결 확인
psql -h localhost -U stockvis -c "SELECT 1;"

# Django 체크
python manage.py check

# Provider 설정 확인
python -c "from api_request.providers.factory import print_current_config; print_current_config()"
```

---

## 8. 운영 체크리스트

### 일일 체크

- [ ] Flower 대시보드 확인
- [ ] 실패한 태스크 확인
- [ ] 에러 로그 확인

### 주간 체크

- [ ] API 호출 통계 확인
- [ ] Fallback 빈도 확인
- [ ] 디스크 사용량 확인

### 월간 체크

- [ ] 로그 파일 정리
- [ ] API 키 유효성 확인
- [ ] 의존성 업데이트 검토
