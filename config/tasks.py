"""
Celery 에러 모니터링 태스크

- send_celery_error_digest: 일일 에러 요약 이메일 발송
- cleanup_old_task_results: TaskResult 정리 (SUCCESS 30일, FAILURE 90일)
"""
import logging
import re
from collections import defaultdict
from datetime import timedelta

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

    today = timezone.now().strftime('%Y-%m-%d')
    subject = f'[Stock-Vis] Celery 에러 일일 요약 ({today})'

    body_lines = [
        f'신규 에러: {new_failure_count}건 / 재시도: {retry_count}건',
        '',
    ]

    if new_errors:
        body_lines.append('태스크별 요약:')
        for task_name in sorted(new_errors.keys()):
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
        for task_name in sorted(ignored_errors.keys()):
            exc_counts = ignored_errors[task_name]
            for exc_class, count in exc_counts.items():
                body_lines.append(f'  {task_name} -- {exc_class}: {count}회')
        body_lines.append('')

    body = '\n'.join(body_lines)
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
