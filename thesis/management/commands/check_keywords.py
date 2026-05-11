"""check_keywords: 종목별 키워드 상태 확인 (Phase B)"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from thesis.models import KeywordCache
from thesis.services.keyword_cache import SOURCE_TTL


class Command(BaseCommand):
    help = '종목별 KeywordCache 상태 확인'

    def add_arguments(self, parser):
        parser.add_argument('target', type=str, help='종목명 (예: 삼성전자)')

    def handle(self, *args, **options):
        target = options['target']
        now = timezone.now()

        self.stdout.write(f'\n=== KeywordCache: "{target}" ===\n')

        total = 0
        for source in ('chain', 'eod', 'news'):
            ttl = SOURCE_TTL.get(source, timedelta(hours=24))
            cutoff = now - ttl

            keywords = KeywordCache.objects.filter(
                target=target,
                source=source,
            ).order_by('-updated_at')

            fresh = [kw for kw in keywords if kw.updated_at >= cutoff]
            stale = [kw for kw in keywords if kw.updated_at < cutoff]

            self.stdout.write(f'--- {source} ({len(fresh)}개 fresh, {len(stale)}개 stale) ---')

            if fresh:
                for kw in fresh:
                    age = now - kw.updated_at
                    hours = age.total_seconds() / 3600
                    self.stdout.write(
                        f'  [{kw.role:<8}] {kw.text} (갱신: {hours:.1f}시간 전)'
                    )
            elif stale:
                self.stdout.write(self.style.WARNING(
                    f'  (stale — {len(stale)}개 TTL 초과)'
                ))
            else:
                self.stdout.write('  (없음)')

            total += len(fresh)
            self.stdout.write('')

        if total == 0:
            self.stdout.write(self.style.WARNING(
                f'"{target}"에 대한 유효 키워드가 없습니다.'
            ))
        self.stdout.write('')
