"""
Celery 에러 모니터링 Management Command

사용법:
    python manage.py celery_errors                              # 오늘 에러 요약
    python manage.py celery_errors --days 7                     # 최근 7일
    python manage.py celery_errors --detail                     # traceback 포함 상세
    python manage.py celery_errors --task news.tasks             # 특정 태스크 필터
    python manage.py celery_errors --stats                      # 태스크별 성공/실패 통계
    python manage.py celery_errors --format prompt              # Claude Code 프롬프트 출력
    python manage.py celery_errors --send-email                 # 즉시 이메일 발송
    python manage.py celery_errors --watch                      # 10초마다 새 에러 폴링
"""
import re
import time
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Celery 태스크 에러 조회 및 모니터링'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=1, help='조회 일수 (기본: 1)')
        parser.add_argument('--detail', action='store_true', help='traceback 포함 상세 출력')
        parser.add_argument('--task', type=str, help='태스크명 필터 (부분 매칭)')
        parser.add_argument('--stats', action='store_true', help='태스크별 성공/실패 통계')
        parser.add_argument('--format', type=str, choices=['default', 'prompt'], default='default',
                            help='출력 형식 (prompt: Claude Code용 마크다운)')
        parser.add_argument('--send-email', action='store_true', help='즉시 이메일 발송')
        parser.add_argument('--watch', action='store_true', help='10초마다 새 에러 폴링 (Ctrl+C로 종료)')

    def handle(self, *args, **options):
        if options['watch']:
            self._watch_mode(options)
        elif options['send_email']:
            self._send_email(options['days'])
        elif options['stats']:
            self._show_stats(options['days'], options.get('task'))
        elif options['format'] == 'prompt':
            self._show_prompt(options['days'], options.get('task'))
        else:
            self._show_errors(options['days'], options.get('task'), options['detail'])

    def _get_failures(self, days, task_filter=None):
        from django_celery_results.models import TaskResult

        since = timezone.now() - timedelta(days=days)
        qs = TaskResult.objects.filter(status='FAILURE', date_done__gte=since)
        if task_filter:
            qs = qs.filter(task_name__icontains=task_filter)
        return qs.order_by('-date_done')

    def _get_retries(self, days, task_filter=None):
        from django_celery_results.models import TaskResult

        since = timezone.now() - timedelta(days=days)
        qs = TaskResult.objects.filter(status='RETRY', date_done__gte=since)
        if task_filter:
            qs = qs.filter(task_name__icontains=task_filter)
        return qs

    def _parse_exception_class(self, traceback_text, result_text=None):
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
        # result JSON fallback (e.g. {"exc_type": "TimeLimitExceeded", ...})
        if result_text:
            try:
                import json
                data = json.loads(result_text)
                if isinstance(data, dict) and 'exc_type' in data:
                    return data['exc_type']
            except (json.JSONDecodeError, TypeError):
                pass
        return 'Unknown'

    def _group_by_task_and_exception(self, failures):
        """태스크명 + exception class 기준 그룹화"""
        groups = defaultdict(lambda: defaultdict(list))
        for f in failures:
            exc_class = self._parse_exception_class(f.traceback, f.result)
            groups[f.task_name][exc_class].append(f)
        return groups

    def _task_name_to_file(self, task_name):
        """task_name에서 파일 경로 추정 (예: news.tasks.collect_daily_news → news/tasks.py)"""
        parts = task_name.split('.')
        if len(parts) >= 2:
            return '/'.join(parts[:-1]) + '.py'
        return task_name

    def _is_ignored(self, task_name):
        ignored = getattr(settings, 'CELERY_IGNORED_ERRORS', [])
        return task_name in ignored

    def _show_errors(self, days, task_filter, detail):
        failures = self._get_failures(days, task_filter)
        retries = self._get_retries(days, task_filter)

        failure_count = failures.count()
        retry_count = retries.count()

        if failure_count == 0 and retry_count == 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n=== Celery Task Errors (최근 {days}일) === 에러 없음!'
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n=== Celery Task Errors (최근 {days}일) ==='
        ))
        self.stdout.write(f'Total: {failure_count} failures, {retry_count} retries\n')

        groups = self._group_by_task_and_exception(failures)

        for task_name in sorted(groups.keys()):
            exc_groups = groups[task_name]
            total = sum(len(items) for items in exc_groups.values())
            ignored_tag = self.style.WARNING(' [IGNORED]') if self._is_ignored(task_name) else ''

            self.stdout.write(
                f'{self.style.ERROR(task_name):<60} '
                f'{total} failure{"s" if total != 1 else ""}{ignored_tag}'
            )

            exc_items = sorted(exc_groups.items(), key=lambda x: -len(x[1]))
            for i, (exc_class, items) in enumerate(exc_items):
                is_last = (i == len(exc_items) - 1)
                prefix = '  \u2514\u2500 ' if is_last else '  \u251c\u2500 '
                count_str = f'{len(items)}\ud68c'
                self.stdout.write(f'{prefix}{exc_class} {"." * max(1, 40 - len(exc_class))} {count_str}')

            if detail:
                # 가장 최근 실패의 traceback 표시
                latest = exc_items[0][1][0]
                if latest.traceback:
                    self.stdout.write(self.style.WARNING('\n  Latest traceback:'))
                    for line in latest.traceback.strip().split('\n')[-10:]:
                        self.stdout.write(f'    {line}')
                if latest.task_args:
                    self.stdout.write(f'  Args: {latest.task_args[:200]}')
                if latest.task_kwargs:
                    self.stdout.write(f'  Kwargs: {latest.task_kwargs[:200]}')
                self.stdout.write('')

        self.stdout.write('')

    def _show_stats(self, days, task_filter):
        from django_celery_results.models import TaskResult
        from django.db.models import Count

        since = timezone.now() - timedelta(days=days)
        qs = TaskResult.objects.filter(date_done__gte=since)
        if task_filter:
            qs = qs.filter(task_name__icontains=task_filter)

        stats = qs.values('task_name', 'status').annotate(
            count=Count('id')
        ).order_by('task_name', 'status')

        task_stats = defaultdict(lambda: defaultdict(int))
        for row in stats:
            task_stats[row['task_name']][row['status']] = row['count']

        if not task_stats:
            self.stdout.write(self.style.WARNING(f'\n최근 {days}일간 실행된 태스크가 없습니다.'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n=== Celery Task Stats (최근 {days}일) ==='
        ))
        self.stdout.write(
            f'{"Task":<55} {"SUCCESS":>8} {"FAILURE":>8} {"RETRY":>7} {"Rate":>7}'
        )
        self.stdout.write('-' * 90)

        for task_name in sorted(task_stats.keys()):
            s = task_stats[task_name]
            success = s.get('SUCCESS', 0)
            failure = s.get('FAILURE', 0)
            retry = s.get('RETRY', 0)
            total = success + failure
            rate = f'{failure / total * 100:.1f}%' if total > 0 else '-'

            # 실패율에 따라 색상 적용
            if failure > 0:
                rate_style = self.style.ERROR(f'{rate:>7}')
            else:
                rate_style = self.style.SUCCESS(f'{rate:>7}')

            ignored = ' *' if self._is_ignored(task_name) else ''
            display_name = task_name[:53] + '..' if len(task_name) > 55 else task_name

            self.stdout.write(
                f'{display_name:<55} {success:>8} {failure:>8} {retry:>7} {rate_style}{ignored}'
            )

        self.stdout.write('')
        ignored_list = getattr(settings, 'CELERY_IGNORED_ERRORS', [])
        if ignored_list:
            self.stdout.write(self.style.WARNING(f'* CELERY_IGNORED_ERRORS에 등록된 태스크'))

    def _show_prompt(self, days, task_filter):
        failures = self._get_failures(days, task_filter)

        if not failures.exists():
            self.stdout.write('# 에러 없음\n\n최근 %d일간 Celery 에러가 없습니다.' % days)
            return

        groups = self._group_by_task_and_exception(failures)
        today = timezone.now().strftime('%Y-%m-%d')

        lines = [f'# Celery 에러 분석 요청 ({today}, 최근 {days}일)', '']

        for task_name in sorted(groups.keys()):
            if self._is_ignored(task_name):
                continue

            exc_groups = groups[task_name]
            total = sum(len(items) for items in exc_groups.values())
            file_path = self._task_name_to_file(task_name)

            lines.append(f'## Task: {task_name}')
            lines.append(f'- File: {file_path}')
            lines.append(f'- Failures ({days}d): {total}\ud68c')
            lines.append('- Error patterns:')

            for exc_class, items in sorted(exc_groups.items(), key=lambda x: -len(x[1])):
                pct = len(items) / total * 100
                lines.append(f'  - {exc_class}: {len(items)}\ud68c ({pct:.0f}%)')

            # 가장 최근 실패의 traceback
            all_items = []
            for items in exc_groups.values():
                all_items.extend(items)
            all_items.sort(key=lambda x: x.date_done, reverse=True)
            latest = all_items[0]

            if latest.traceback:
                tb_lines = latest.traceback.strip().split('\n')[-15:]
                lines.append('- Last traceback:')
                lines.append('  ```')
                for tb_line in tb_lines:
                    lines.append(f'  {tb_line}')
                lines.append('  ```')

            if latest.task_args:
                args_display = latest.task_args[:300]
                lines.append(f'- Task args: {args_display}')
            if latest.task_kwargs:
                kwargs_display = latest.task_kwargs[:300]
                lines.append(f'- Task kwargs: {kwargs_display}')

            lines.append('')

        lines.append('\uc704 \uc5d0\ub7ec\ub4e4\uc744 \ubd84\uc11d\ud558\uace0 \uc218\uc815 \ucf54\ub4dc\ub97c \uc81c\uc548\ud574\uc918.')

        self.stdout.write('\n'.join(lines))

    def _send_email(self, days):
        from config.tasks import send_celery_error_digest
        result = send_celery_error_digest(days=days)
        self.stdout.write(self.style.SUCCESS(f'\n이메일 발송 완료: {result}'))

    def _watch_mode(self, options):
        from django_celery_results.models import TaskResult

        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n=== Celery Error Watch Mode (10초 간격) ==='
        ))
        self.stdout.write('Ctrl+C로 종료\n')

        last_check = timezone.now()
        task_filter = options.get('task')

        try:
            while True:
                now = timezone.now()
                qs = TaskResult.objects.filter(
                    status='FAILURE', date_done__gt=last_check
                )
                if task_filter:
                    qs = qs.filter(task_name__icontains=task_filter)

                new_failures = list(qs.order_by('date_done'))

                if new_failures:
                    for f in new_failures:
                        exc_class = self._parse_exception_class(f.traceback, f.result)
                        timestamp = f.date_done.strftime('%H:%M:%S')
                        ignored = ' [IGNORED]' if self._is_ignored(f.task_name) else ''
                        self.stdout.write(
                            f'{self.style.ERROR("[FAILURE]")} '
                            f'{timestamp} {f.task_name} | '
                            f'{exc_class}: {(f.result or "")[:100]}{ignored}'
                        )

                last_check = now
                time.sleep(10)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nWatch mode 종료'))
