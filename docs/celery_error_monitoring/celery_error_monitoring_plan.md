# Celery 에러 모니터링 시스템

## Context

Celery Beat에 65+ 스케줄 태스크가 등록되어 있고, `django-db` 결과 백엔드로 TaskResult에 이미 2431건(FAILURE 62건)이 저장되어 있다.
그러나 에러를 정기적으로 확인할 수단이 없어 FRED 500 에러 같은 문제가 방치됨.

**목표**: 매일 Celery 에러를 자동 수집 → CLI로 즉시 확인 + Claude Code 프롬프트 생성 + 이메일 일일 요약 발송

## 구현 방식

기존 `django_celery_results.TaskResult` 테이블을 그대로 활용 (새 모델 없음).
Celery `task_failure` 시그널로 구조화 로그를 남기고, management command + 일일 digest 태스크로 확인.

## 수정 대상 파일

| 파일 | 변경 | 신규/수정 |
|------|------|----------|
| `config/celery.py` | task_failure/task_retry 시그널 핸들러 등록 + daily digest/cleanup 스케줄 추가 | 수정 |
| `config/settings.py` | 이메일 설정 + CELERY_IGNORED_ERRORS + CELERY_ERROR_RECIPIENTS | 수정 |
| `config/management/__init__.py` | 패키지 초기화 | 신규 |
| `config/management/commands/__init__.py` | 패키지 초기화 | 신규 |
| `config/management/commands/celery_errors.py` | CLI 에러 조회 명령어 | 신규 |
| `config/tasks.py` | 일일 에러 digest + TaskResult cleanup 태스크 | 신규 |

## 구현 순서

### Step 1: 설정 추가 (config/settings.py)

```python
# Email (콘솔 백엔드 기본, 프로덕션에서 SMTP로 교체)
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'stockvis@example.com')

# Celery 에러 알림 수신자
CELERY_ERROR_RECIPIENTS = [
    'goid545@naver.com',
    'jinie545@gmail.com',
]

# 반복 에러 무시 목록 (알림 피로 방지)
# digest에서 "Known Issues" 섹션으로 분리 표시
CELERY_IGNORED_ERRORS = [
    # 'rag_analysis.tasks.health_check_neo4j',  # AuraDB free tier 간헐적 끊김
]
```

### Step 2: Celery 시그널 핸들러 (config/celery.py)

`task_failure`, `task_retry` 시그널을 등록하여 구조화 로그만 남김.

> **설계 결정**: meta 업데이트 안 함. django-celery-results가 TaskResult를 저장하는 시점이
> `task_postrun`이라서, `task_failure` 시점에는 레코드가 아직 없어 `filter().update()`가
> 0 rows affected로 끝남. exception_class는 management command에서 traceback 마지막 줄
> 파싱으로 추출하므로 meta 없이도 `--format prompt` 기능 정상 동작.

```python
import logging
from celery.signals import task_failure, task_retry

logger = logging.getLogger('celery.error_monitor')

@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, **kw):
    logger.error(
        f"[TASK FAILURE] {sender.name} | task_id={task_id} | "
        f"{type(exception).__name__}: {str(exception)[:200]}"
    )

@task_retry.connect
def handle_task_retry(sender=None, request=None, reason=None, **kwargs):
    logger.warning(
        f"[TASK RETRY] {sender.name} | task_id={request.id} | "
        f"retries={request.retries} | reason={str(reason)[:200]}"
    )
```

### Step 3: Management Command (config/management/commands/celery_errors.py)

기존 `pipeline_status.py` 패턴을 따르는 CLI 명령어.

**사용법:**
```
python manage.py celery_errors                              # 오늘 에러 요약
python manage.py celery_errors --days 7                     # 최근 7일
python manage.py celery_errors --detail                     # traceback 포함 상세
python manage.py celery_errors --task news.tasks             # 특정 태스크 필터
python manage.py celery_errors --stats                      # 태스크별 성공/실패 통계
python manage.py celery_errors --format prompt              # Claude Code 프롬프트 출력
python manage.py celery_errors --send-email                 # 즉시 이메일 발송
python manage.py celery_errors --watch                      # 10초마다 새 에러 폴링 (실시간)
```

**핵심 기능:**

#### 기본 출력: 태스크명 + exception class 서브그룹

같은 태스크에서도 에러 유형별로 서브그룹 표시:
```
=== Celery Task Errors (최근 7일) ===
Total: 16 failures, 24 retries

news.tasks.collect_sp500_news_fmp_batch          12 failures
  ├─ FMPRateLimitError ···················· 8회
  └─ ConnectionTimeout ···················· 4회
macro.tasks.update_economic_indicators            3 failures
  └─ HTTPError ···························· 3회
rag_analysis.tasks.health_check_neo4j             1 failure   [IGNORED]
  └─ ServiceUnavailable ·················· 1회
```

#### --format prompt: Claude Code 프롬프팅용 출력

```markdown
# Celery 에러 분석 요청 (2026-03-14, 최근 7일)

## Task: news.tasks.collect_sp500_news_fmp_batch
- File: news/tasks.py
- Failures (7d): 12회
- Error patterns:
  - FMPRateLimitError: 8회 (67%)
  - ConnectionTimeout: 4회 (33%)
- Last traceback:
  Traceback (most recent call last):
    File "news/tasks.py", line 245, in collect_sp500_news_fmp_batch
    ...
  FMPRateLimitError: Rate limit exceeded
- Task args: ['AAPL', 'MSFT', ...] (최근 실패 시 인자)
- Retry history: 매회 2회 retry 후 실패

## Task: macro.tasks.update_economic_indicators
- File: macro/tasks.py
...

위 에러들을 분석하고 수정 코드를 제안해줘.
```

구현 세부:
- `task_name`에서 `app.tasks` → 파일 경로 매핑 (`news.tasks` → `news/tasks.py`)
- `TaskResult.traceback` 필드에서 마지막 traceback 추출
- `TaskResult.task_args`/`task_kwargs` 필드 활용 (TaskResult에 이미 저장됨)
- exception class name은 traceback 마지막 줄에서 파싱 (meta 불필요)

#### --watch 모드

```python
# 10초 간격 폴링, 새 에러만 표시 (last_check 이후)
while True:
    new_failures = TaskResult.objects.filter(
        status='FAILURE', date_done__gt=last_check
    )
    if new_failures.exists():
        # 출력
    last_check = now()
    time.sleep(10)
```

Ctrl+C로 종료. 디버깅 세션 중 터미널 하나 켜놓고 사용.

#### CELERY_IGNORED_ERRORS 처리

- 기본/--stats 출력: `[IGNORED]` 태그 표시, 카운트에는 포함하되 분리 섹션
- --format prompt: ignored 에러 제외 (수정 불필요하므로)
- digest 이메일: "Known Issues — 무시됨: N건" 별도 섹션

### Step 4: 일일 Digest + Cleanup 태스크 (config/tasks.py)

#### send_celery_error_digest

```python
@shared_task
def send_celery_error_digest():
    """매일 에러 요약 이메일 발송"""
    # 1. TaskResult에서 최근 24시간 FAILURE 조회
    # 2. task_name + exception_class 기준 그룹화
    # 3. CELERY_IGNORED_ERRORS 분리
    # 4. 신규 에러 0건이면 이메일 미발송 (알림 피로 방지)
    # 5. 에러 있으면 요약 이메일 발송
    #    - 수신자: settings.CELERY_ERROR_RECIPIENTS
    #    - 기존 send_etf_sync_failure_email 패턴 참조
```

이메일 본문 구조:
```
[Stock-Vis] Celery 에러 일일 요약 (2026-03-14)

신규 에러: 5건 / 재시도: 12건

태스크별 요약:
  news.tasks.collect_sp500_news_fmp_batch — 3 failures
    FMPRateLimitError: 2회 / ConnectionTimeout: 1회
  macro.tasks.update_economic_indicators — 2 failures
    HTTPError: 2회

Known Issues (무시됨): 1건
  rag_analysis.tasks.health_check_neo4j — ServiceUnavailable: 1회
```

#### cleanup_old_task_results

SUCCESS/FAILURE 분리 정리:
```python
@shared_task
def cleanup_old_task_results():
    """TaskResult 정리 — SUCCESS 30일, FAILURE 90일"""
    cutoff_success = now() - timedelta(days=30)
    cutoff_failure = now() - timedelta(days=90)

    deleted_success = TaskResult.objects.filter(
        status='SUCCESS', date_done__lt=cutoff_success
    ).delete()[0]
    deleted_failure = TaskResult.objects.filter(
        status__in=['FAILURE', 'RETRY'],
        date_done__lt=cutoff_failure
    ).delete()[0]
```

### Step 5: Beat 스케줄 등록 (config/celery.py)

```python
# Celery 에러 모니터링
# ============================================================

# 일일 에러 요약 이메일 (매일 07:00 EST, 전날 에러 집계)
'celery-error-digest': {
    'task': 'config.tasks.send_celery_error_digest',
    'schedule': crontab(hour=7, minute=0),
},

# TaskResult 정리 (매주 일요일 05:00 EST)
# SUCCESS: 30일 보관, FAILURE: 90일 보관
'cleanup-task-results': {
    'task': 'config.tasks.cleanup_old_task_results',
    'schedule': crontab(hour=5, minute=0, day_of_week=0),
},
```

## 검증 방법

1. **CLI 기본**: `python manage.py celery_errors --days 7` → 기존 62개 FAILURE 그룹화 표시
2. **CLI 통계**: `python manage.py celery_errors --stats` → 태스크별 성공/실패 비율
3. **CLI 프롬프트**: `python manage.py celery_errors --format prompt --days 7` → Claude Code에 바로 붙여넣기 가능한 마크다운 출력
4. **이메일**: `python manage.py celery_errors --send-email` → 콘솔 백엔드로 이메일 내용 출력
5. **Watch**: `python manage.py celery_errors --watch` → 실시간 폴링 확인 (Ctrl+C로 종료)
6. **시그널**: `celery -A config worker -l info` 실행 후 실패 태스크 트리거 → `[TASK FAILURE]` 로그 확인
7. **Ignored**: `CELERY_IGNORED_ERRORS`에 태스크 추가 후 digest에서 분리 표시 확인
