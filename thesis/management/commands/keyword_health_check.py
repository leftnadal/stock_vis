"""Daily Keyword Health Check: source별 갱신 상태 + stale 경고 (Phase C-1)"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Max, Count
from django.utils import timezone

from thesis.models import KeywordCache
from thesis.services.keyword_cache import SOURCE_TTL


# source별 경고 기준
ALERT_THRESHOLDS = {
    'chain': timedelta(hours=48),
    'eod': timedelta(hours=24),
    'news': timedelta(hours=24),
}


class Command(BaseCommand):
    help = 'KeywordCache 일일 건강 체크 — source별 갱신 상태 + stale 경고'

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(f'\n=== Keyword Health Check ({now.strftime("%Y-%m-%d %H:%M")}) ===\n')

        has_warning = False

        for source in ('chain', 'eod', 'news'):
            ttl = SOURCE_TTL.get(source, timedelta(hours=24))
            alert_threshold = ALERT_THRESHOLDS.get(source, timedelta(hours=24))
            cutoff_fresh = now - ttl
            cutoff_alert = now - alert_threshold

            # 전체 통계
            total = KeywordCache.objects.filter(source=source).count()
            fresh = KeywordCache.objects.filter(source=source, updated_at__gte=cutoff_fresh).count()
            stale = total - fresh

            # 최신 갱신 시각
            latest = KeywordCache.objects.filter(source=source).aggregate(
                latest=Max('updated_at')
            )['latest']

            # target별 통계
            targets_total = KeywordCache.objects.filter(source=source).values('target').distinct().count()
            targets_fresh = (
                KeywordCache.objects.filter(source=source, updated_at__gte=cutoff_fresh)
                .values('target').distinct().count()
            )

            # 출력
            self.stdout.write(f'--- {source} ---')
            self.stdout.write(f'  총 키워드: {total}개 (fresh: {fresh}, stale: {stale})')
            self.stdout.write(f'  타겟 수: {targets_total}개 (fresh: {targets_fresh})')

            if latest:
                age = now - latest
                hours = age.total_seconds() / 3600
                self.stdout.write(f'  최신 갱신: {hours:.1f}시간 전')

                if latest < cutoff_alert:
                    level = '🔴' if source == 'eod' else '⚠️'
                    self.stdout.write(self.style.ERROR(
                        f'  {level} {alert_threshold.total_seconds()/3600:.0f}시간+ 갱신 없음!'
                    ))
                    has_warning = True
            else:
                self.stdout.write(self.style.WARNING('  (데이터 없음)'))

            # stale target 상위 5개
            if stale > 0:
                stale_targets = (
                    KeywordCache.objects.filter(source=source, updated_at__lt=cutoff_fresh)
                    .values('target')
                    .annotate(count=Count('id'), latest=Max('updated_at'))
                    .order_by('latest')[:5]
                )
                if stale_targets:
                    self.stdout.write(f'  stale 상위:')
                    for t in stale_targets:
                        age = (now - t['latest']).total_seconds() / 3600
                        self.stdout.write(f'    {t["target"]} ({t["count"]}개, {age:.0f}h 전)')

            self.stdout.write('')

        if not has_warning:
            self.stdout.write(self.style.SUCCESS('모든 source 정상'))
        self.stdout.write('')
