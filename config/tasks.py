"""
Celery 에러 모니터링 태스크

- send_celery_error_digest: 일일 에러 요약 이메일 발송
- cleanup_old_task_results: TaskResult 정리 (SUCCESS 30일, FAILURE 90일)
"""
import json
import logging
import re
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


def _parse_exception_class(traceback_text, result_text=None):
    """traceback 마지막 줄에서 exception class name 추출, 없으면 result JSON fallback"""
    if traceback_text:
        lines = traceback_text.strip().split('\n')
        last_line = lines[-1].strip()
        match = re.match(r'^([\w.]+(?:Error|Exception|Timeout|Failure|Warning))', last_line)
        if match:
            return match.group(1)
        if ':' in last_line:
            candidate = last_line.split(':')[0].strip()
            if candidate and not candidate.startswith(' '):
                return candidate
    if result_text:
        try:
            import json
            data = json.loads(result_text)
            if isinstance(data, dict) and 'exc_type' in data:
                return data['exc_type']
        except (json.JSONDecodeError, TypeError):
            pass
    return 'Unknown'


# C-1: digest 산출물 경로. DB 모델 신설 없이(마이그 0) 파일로 남긴다 —
# health_check 는 별도 프로세스라 캐시보다 파일이 확실하다.
CELERY_DIGEST_ARTIFACT = Path.home() / 'Library' / 'Logs' / 'stockvis' / 'celery_error_digest.json'


def _write_digest_artifact(payload):
    """요약 산출물을 파일로 남긴다. 저장 실패가 발송을 막지 않는다(로그만)."""
    try:
        CELERY_DIGEST_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        tmp = CELERY_DIGEST_ARTIFACT.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(CELERY_DIGEST_ARTIFACT)  # atomic
        logger.info('Celery error digest 산출물 저장: %s', CELERY_DIGEST_ARTIFACT)
    except Exception:
        logger.exception('Celery error digest 산출물 저장 실패 — 발송은 계속 진행')


def _task_sort_key(task_name):
    """정렬 키 — `task_name` 이 NULL 일 수 있다.

    워커에 등록되지 않은 태스크(NotRegistered)는 이름을 알 수 없어 TaskResult.task_name
    이 NULL 로 저장된다. 그 레코드가 섞이면 `sorted()` 가 str 과 None 을 비교하다
    TypeError 로 죽는다 — 실패를 알려줄 장치가 실패 때문에 죽는 구조(HEARTBEAT-1 B).
    None 은 빈 문자열로 취급해 맨 앞에 오게만 한다(그룹화·집계는 불변).
    """
    return task_name or ""


@shared_task
def send_celery_error_digest(days=1):
    """매일 에러 요약 이메일 발송"""
    from django_celery_results.models import TaskResult

    since = timezone.now() - timedelta(days=days)
    failures = TaskResult.objects.filter(
        status='FAILURE', date_done__gte=since
    ).order_by('-date_done')
    retries = TaskResult.objects.filter(
        status='RETRY', date_done__gte=since
    )

    failure_count = failures.count()
    retry_count = retries.count()

    if failure_count == 0:
        logger.info('Celery error digest: 에러 없음, 이메일 미발송')
        return 'No errors — email skipped'

    ignored_list = getattr(settings, 'CELERY_IGNORED_ERRORS', [])

    # 태스크명 + exception class 기준 그룹화
    groups = defaultdict(lambda: defaultdict(int))
    for f in failures:
        exc_class = _parse_exception_class(f.traceback, f.result)
        groups[f.task_name][exc_class] += 1

    # 신규 에러 / 무시 에러 분리
    new_errors = {}
    ignored_errors = {}
    for task_name, exc_counts in groups.items():
        if task_name in ignored_list:
            ignored_errors[task_name] = exc_counts
        else:
            new_errors[task_name] = exc_counts

    new_failure_count = sum(
        sum(counts.values()) for counts in new_errors.values()
    )
    ignored_failure_count = sum(
        sum(counts.values()) for counts in ignored_errors.values()
    )

    today = timezone.localtime().strftime('%Y-%m-%d')
    subject = f'[Stock-Vis] Celery 에러 일일 요약 ({today})'

    body_lines = [
        f'신규 에러: {new_failure_count}건 / 재시도: {retry_count}건',
        '',
    ]

    if new_errors:
        body_lines.append('태스크별 요약:')
        for task_name in sorted(new_errors.keys(), key=_task_sort_key):
            exc_counts = new_errors[task_name]
            total = sum(exc_counts.values())
            body_lines.append(
                f'  {task_name} -- {total} failure{"s" if total != 1 else ""}'
            )
            for exc_class, count in sorted(exc_counts.items(), key=lambda x: -x[1]):
                body_lines.append(f'    {exc_class}: {count}회')
        body_lines.append('')

    if ignored_errors:
        body_lines.append(
            f'Known Issues (무시됨): {ignored_failure_count}건'
        )
        for task_name in sorted(ignored_errors.keys(), key=_task_sort_key):
            exc_counts = ignored_errors[task_name]
            for exc_class, count in exc_counts.items():
                body_lines.append(f'  {task_name} -- {exc_class}: {count}회')
        body_lines.append('')

    body = '\n'.join(body_lines)

    # C-1(HEARTBEAT-1): 산출물을 발송과 분리한다. 발송이 실패해도 요약은 남아야 한다.
    # 이번 사고의 본질은 "장치가 없다"가 아니라 "알림 경로가 하나뿐이었고 그 하나가
    # 죽었다"였다 — 이메일이 죽으면 아무 소리도 나지 않았다. 여기서 먼저 저장하고,
    # health_check 가 그 파일을 읽어 이메일과 무관하게 실패 건수를 보여준다(C-2).
    digest_payload = {
        'generated_at': timezone.now().isoformat(),
        'window_days': days,
        'failure_count': failure_count,
        'new_failure_count': new_failure_count,
        'ignored_failure_count': ignored_failure_count,
        'retry_count': retry_count,
        'by_task': {
            (task_name or '(이름없음·NotRegistered)'): dict(exc_counts)
            for task_name, exc_counts in groups.items()
        },
        'body': body,
    }
    _write_digest_artifact(digest_payload)

    recipients = getattr(settings, 'CELERY_ERROR_RECIPIENTS', [])

    if not recipients:
        logger.warning('CELERY_ERROR_RECIPIENTS가 비어있어 이메일 미발송')
        return 'No recipients configured'

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
        logger.info(f'Celery error digest 발송: {failure_count} failures to {recipients}')
        return f'Sent: {failure_count} failures, {retry_count} retries'
    except Exception as e:
        logger.exception(f'Celery error digest 이메일 발송 실패: {e}')
        return f'Email failed: {e}'


@shared_task
def cleanup_old_task_results():
    """TaskResult 정리 -- SUCCESS 30일, FAILURE 90일"""
    from django_celery_results.models import TaskResult

    cutoff_success = timezone.now() - timedelta(days=30)
    cutoff_failure = timezone.now() - timedelta(days=90)

    deleted_success = TaskResult.objects.filter(
        status='SUCCESS', date_done__lt=cutoff_success
    ).delete()[0]

    deleted_failure = TaskResult.objects.filter(
        status__in=['FAILURE', 'RETRY'],
        date_done__lt=cutoff_failure
    ).delete()[0]

    logger.info(
        f'TaskResult cleanup: SUCCESS {deleted_success}건 삭제 (30일+), '
        f'FAILURE/RETRY {deleted_failure}건 삭제 (90일+)'
    )
    return {
        'deleted_success': deleted_success,
        'deleted_failure': deleted_failure,
    }
