"""
SEC-PR-10: 미매칭 큐 일괄 처리.

fuzzy ≥ 0.90 자동 매칭.
Usage: python manage.py process_unmatched_queue
"""

from django.core.management.base import BaseCommand

from sec_pipeline.models import UnmatchedCompanyQueue


class Command(BaseCommand):
    help = '미매칭 큐 fuzzy ≥ 0.90 자동 매칭'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold', type=float, default=0.90,
            help='최소 fuzzy score (기본: 0.90)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='실제 매칭하지 않고 결과만 표시',
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        dry_run = options['dry_run']

        pending = UnmatchedCompanyQueue.objects.filter(status='pending')
        self.stdout.write(f'Pending entries: {pending.count()}')

        auto_matched = 0
        skipped = 0
        no_candidates = 0

        for entry in pending:
            candidates = entry.fuzzy_candidates or []
            if not candidates:
                no_candidates += 1
                continue

            top = candidates[0]
            score = top.get('score', 0)
            ticker = top.get('ticker', '')

            if score >= threshold:
                if dry_run:
                    self.stdout.write(
                        f'  [DRY] {entry.raw_company_name} → {ticker} '
                        f'(score={score:.0%}, x{entry.occurrence_count})'
                    )
                else:
                    entry.resolved_ticker = ticker
                    entry.status = 'matched'
                    entry.save(update_fields=['resolved_ticker', 'status'])
                    # post_save signal이 evidence 업데이트 + CompanyAlias 생성
                auto_matched += 1
            else:
                skipped += 1

        action = 'Would auto-match' if dry_run else 'Auto-matched'
        self.stdout.write(self.style.SUCCESS(
            f'\n{action}: {auto_matched}, '
            f'Below threshold: {skipped}, '
            f'No candidates: {no_candidates}'
        ))
