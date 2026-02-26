"""
EOD Pipeline 상태 조회 + 즉시 실행 Management Command

사용법:
    python manage.py pipeline_status                # 최근 7일 로그
    python manage.py pipeline_status --run           # 즉시 실행 (직전 거래일)
    python manage.py pipeline_status --run --date 2026-02-25  # 특정 날짜 실행
    python manage.py pipeline_status --quality       # ingest_quality 상세
"""
import json
from datetime import date, timedelta
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'EOD Pipeline 상태 조회 및 즉시 실행'

    def add_arguments(self, parser):
        parser.add_argument('--run', action='store_true', help='파이프라인 즉시 실행')
        parser.add_argument('--date', type=str, help='대상 날짜 (YYYY-MM-DD)')
        parser.add_argument('--quality', action='store_true', help='ingest_quality 상세 출력')
        parser.add_argument('--days', type=int, default=7, help='조회 일수 (기본: 7)')

    def handle(self, *args, **options):
        if options['run']:
            self._run_pipeline(options.get('date'))
        elif options['quality']:
            self._show_quality(options['days'])
        else:
            self._show_status(options['days'])

    def _run_pipeline(self, target_date_str):
        from stocks.services.eod_pipeline import EODPipeline

        target = None
        if target_date_str:
            target = date.fromisoformat(target_date_str)

        self.stdout.write(self.style.WARNING(f'파이프라인 실행 시작... (date={target or "auto"})'))

        pipeline = EODPipeline()
        log = pipeline.run(target_date=target)

        if log.status == 'success':
            self.stdout.write(self.style.SUCCESS(
                f'완료! date={log.date} | signals={log.stages.get("tag", {}).get("total_signals", 0)} | '
                f'duration={log.total_duration_seconds:.1f}s'
            ))
        elif log.status == 'partial':
            self.stdout.write(self.style.WARNING(
                f'부분 완료: date={log.date} | status={log.status} | '
                f'duration={log.total_duration_seconds:.1f}s'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f'실패: date={log.date} | error={log.error_message[:200]}'
            ))

    def _show_status(self, days):
        from stocks.models import PipelineLog

        logs = PipelineLog.objects.order_by('-date')[:days]

        if not logs:
            self.stdout.write(self.style.WARNING('파이프라인 실행 기록이 없습니다.'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== EOD Pipeline Status (최근 %d일) ===' % days))
        self.stdout.write(f'{"Date":<12} {"Status":<10} {"Duration":<10} {"Signals":<10} {"Run ID":<38}')
        self.stdout.write('-' * 80)

        for log in logs:
            signal_count = log.stages.get('tag', {}).get('total_signals', '-')
            status_style = {
                'success': self.style.SUCCESS,
                'failed': self.style.ERROR,
                'partial': self.style.WARNING,
                'running': self.style.NOTICE,
            }.get(log.status, str)

            self.stdout.write(
                f'{str(log.date):<12} '
                f'{status_style(log.status):<20} '
                f'{log.total_duration_seconds:>7.1f}s  '
                f'{str(signal_count):>8}  '
                f'{str(log.run_id):<38}'
            )

            if log.error_message:
                self.stdout.write(self.style.ERROR(f'  Error: {log.error_message[:100]}'))

    def _show_quality(self, days):
        from stocks.models import PipelineLog

        logs = PipelineLog.objects.filter(
            ingest_quality__isnull=False
        ).exclude(
            ingest_quality={}
        ).order_by('-date')[:days]

        if not logs:
            self.stdout.write(self.style.WARNING('품질 데이터가 없습니다.'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Ingest Quality (최근 %d일) ===' % days))

        for log in logs:
            q = log.ingest_quality
            self.stdout.write(f'\n{self.style.SUCCESS(str(log.date))}:')
            self.stdout.write(f'  수신 종목수: {q.get("total_received", "-")}')
            self.stdout.write(f'  전일 대비: {q.get("vs_prev_day_pct", "-")}%')
            self.stdout.write(f'  sector null: {q.get("sector_null_pct", "-")}%')
            self.stdout.write(f'  volume zero: {q.get("volume_zero_pct", "-")}%')
            self.stdout.write(f'  dollar_vol 필터: {q.get("dollar_vol_filtered", "-")}개')

            if q.get('degrade_mode'):
                self.stdout.write(self.style.ERROR(f'  DEGRADE MODE'))
                for w in q.get('warnings', []):
                    self.stdout.write(self.style.WARNING(f'    - {w}'))
