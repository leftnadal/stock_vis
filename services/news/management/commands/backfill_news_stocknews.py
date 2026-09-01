"""
backfill_news_stocknews — NewsEntity → StockNews 물질화 백필 (NEWSFIX-SYNC-BE).

사용자 수동 실행용(Gate 4 — 배포 카드). 최근 window 일의 실뉴스를 StockNews로
물질화하고 건수를 보고한다. 멱등(창 단위 replace) — 재실행 안전.

사용:
    python manage.py backfill_news_stocknews             # dry-run (전/후 건수 계획만)
    python manage.py backfill_news_stocknews --apply     # 실제 물질화 수행
    python manage.py backfill_news_stocknews --apply --window-days 30
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "NewsEntity(+NewsArticle) → StockNews 물질화 백필(멱등). 기본 dry-run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="실제 물질화 수행. 기본은 dry-run(건수 계획만).",
        )
        parser.add_argument(
            "--window-days",
            type=int,
            default=30,
            help="물질화 창(일). 기본 30 = enricher 최장 창(symbol_30d) 커버.",
        )

    def handle(self, *args, **options):
        from datetime import timedelta

        from django.utils import timezone as djtz

        from packages.shared.stocks.models import StockNews
        from services.news.models import NewsEntity

        window_days = options["window_days"]
        apply_changes = options["apply"]

        now = djtz.now()
        cutoff = now - timedelta(days=window_days)

        before = StockNews.objects.count()
        window_existing = StockNews.objects.filter(
            published_at__gte=cutoff, published_at__lte=now
        ).count()
        candidates = (
            NewsEntity.objects.filter(
                news__published_at__gte=cutoff, news__published_at__lte=now
            )
            .exclude(symbol="")
            .count()
        )

        self.stdout.write(
            f"[backfill_news_stocknews] window={window_days}d cutoff={cutoff.isoformat()}"
        )
        self.stdout.write(
            f"  StockNews 현재 총 {before}행 (창 내 {window_existing}행) · "
            f"NewsEntity 창 내 후보 {candidates}건"
        )

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "dry-run: 아무것도 쓰지 않음. 실제 물질화는 --apply."
                )
            )
            return

        from services.news.services.stock_news_sync import (
            sync_news_entities_to_stock_news,
        )

        result = sync_news_entities_to_stock_news(window_days=window_days, now=now)
        after = StockNews.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"물질화 완료: deleted={result['deleted']} created={result['created']} "
                f"symbols={result['symbols']} · StockNews {before}→{after}행"
            )
        )
