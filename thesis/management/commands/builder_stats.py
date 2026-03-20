"""Builder Stats: LLM 빌더 이벤트 로그 기반 핵심 지표 추출 (Phase A-Hardening)"""

import json
import re
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'LLM 빌더 이벤트 로그에서 핵심 지표 추출'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=7,
            help='최근 N일간의 로그 분석 (기본: 7)',
        )
        parser.add_argument(
            '--log-file', type=str, default='stocks.log',
            help='로그 파일 경로 (기본: stocks.log)',
        )

    def handle(self, *args, **options):
        days = options['days']
        log_file = options['log_file']
        cutoff = timezone.now() - timedelta(days=days)

        events = self._parse_log_file(log_file, cutoff)

        if not events:
            self.stdout.write(self.style.WARNING(
                f'최근 {days}일간 빌더 이벤트가 없습니다.\n'
                f'로그 파일: {log_file}'
            ))
            return

        self._print_stats(events, days)

    def _parse_log_file(self, log_file, cutoff):
        """로그 파일에서 빌더 이벤트 추출."""
        events = []
        builder_events = {
            'builder_started', 'proposal_generated', 'llm_parse_failed',
            'fallback_triggered', 'preset_selected', 'confirm_clicked',
            'thesis_created',
        }

        try:
            with open(log_file, 'r') as f:
                for line in f:
                    # JSON 이벤트 로그 추출
                    match = re.search(r'\{.*"event".*\}', line)
                    if not match:
                        continue
                    try:
                        evt = json.loads(match.group())
                    except json.JSONDecodeError:
                        continue

                    if evt.get('event') not in builder_events:
                        continue

                    # timestamp 필터링
                    ts = evt.get('timestamp', '')
                    if ts:
                        from django.utils.dateparse import parse_datetime
                        dt = parse_datetime(ts)
                        if dt and timezone.is_naive(dt):
                            dt = timezone.make_aware(dt)
                        if dt and dt < cutoff:
                            continue

                    events.append(evt)
        except FileNotFoundError:
            self.stdout.write(self.style.WARNING(f'로그 파일 없음: {log_file}'))

        return events

    def _print_stats(self, events, days):
        """이벤트 목록에서 통계 출력."""
        counts = {}
        for evt in events:
            name = evt.get('event', '')
            counts[name] = counts.get(name, 0) + 1

        started = counts.get('builder_started', 0)
        proposal = counts.get('proposal_generated', 0)
        parse_failed = counts.get('llm_parse_failed', 0)
        fallback = counts.get('fallback_triggered', 0)
        preset = counts.get('preset_selected', 0)
        confirm = counts.get('confirm_clicked', 0)
        created = counts.get('thesis_created', 0)

        # confidence 분류
        confidence_counts = {'high': 0, 'medium': 0, 'low': 0}
        turn_counts = []
        for evt in events:
            if evt.get('event') == 'proposal_generated':
                c = evt.get('data', {}).get('confidence', 'unknown')
                if c in confidence_counts:
                    confidence_counts[c] += 1
                tc = evt.get('data', {}).get('turn_count')
                if tc is not None:
                    turn_counts.append(tc)

        # fallback reason 분류
        fallback_reasons = {}
        for evt in events:
            if evt.get('event') == 'fallback_triggered':
                reason = evt.get('data', {}).get('reason', 'unknown')
                fallback_reasons[reason] = fallback_reasons.get(reason, 0) + 1

        # 출력
        self.stdout.write(f'\n=== Builder Stats (최근 {days}일) ===\n')
        self.stdout.write(f'builder_started:       {started}')
        self.stdout.write(f'proposal_generated:    {proposal}')
        for c in ('high', 'medium', 'low'):
            self.stdout.write(f'  - confidence {c}:   {confidence_counts[c]}')

        pct = lambda n, d: f'{n/d*100:.1f}%' if d else 'N/A'
        self.stdout.write(f'llm_parse_failed:      {parse_failed}  ({pct(parse_failed, started)})')
        self.stdout.write(f'fallback_triggered:    {fallback}  ({pct(fallback, started)})')
        for reason, cnt in sorted(fallback_reasons.items()):
            self.stdout.write(f'  - {reason}:     {cnt}')
        self.stdout.write(f'preset_selected:       {preset}')
        self.stdout.write(f'confirm_clicked:       {confirm}')
        self.stdout.write(f'thesis_created:        {created} (등록 완료율: {pct(created, started)})')

        if turn_counts:
            avg_tc = sum(turn_counts) / len(turn_counts)
            self.stdout.write(f'avg_turn_count:        {avg_tc:.1f}')

        # 경고
        self.stdout.write('')
        if started > 0:
            fb_rate = fallback / started * 100
            if fb_rate > 15:
                self.stdout.write(self.style.ERROR(
                    f'⚠️  fallback 비율 {fb_rate:.1f}% (기준: 15%) → 프롬프트/스키마 점검 필요'
                ))
            reg_rate = created / started * 100
            if reg_rate < 50:
                self.stdout.write(self.style.ERROR(
                    f'⚠️  등록 완료율 {reg_rate:.1f}% (기준: 50%) → UX/제안 품질 점검 필요'
                ))
        self.stdout.write('')
