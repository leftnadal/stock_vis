"""Market Pulse v2 — Celery Beat 등록 (DB) 단일 진입점 (Bug #28 패턴, 멱등)."""
from __future__ import annotations

import json
import logging
from typing import Any

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask

logger = logging.getLogger(__name__)


SCHEDULES: list[dict[str, Any]] = [
    {
        'name': 'mp_fetch_news_hourly',
        'task': 'marketpulse.tasks.news.mp_fetch_news_hourly',
        'crontab': {'minute': '5', 'hour': '*', 'day_of_week': '*',
                    'day_of_month': '*', 'month_of_year': '*'},
        'description': 'Market Pulse v2 — 6 카테고리 뉴스 수집',
        'kwargs': {},
    },
    {
        'name': 'mp_calc_breadth_5min',
        'task': 'marketpulse.tasks.breadth.mp_calc_breadth_5min',
        'crontab': {'minute': '*/5', 'hour': '9-16', 'day_of_week': '1-5',
                    'day_of_month': '*', 'month_of_year': '*'},
        'description': 'Market Pulse v2 — SPY breadth 5분 주기',
        'kwargs': {'universe': 'SPY'},
    },
    {
        'name': 'mp_calc_concentration_daily',
        'task': 'marketpulse.tasks.concentration.mp_calc_concentration_daily',
        'crontab': {'minute': '15', 'hour': '17', 'day_of_week': '1-5',
                    'day_of_month': '*', 'month_of_year': '*'},
        'description': 'Market Pulse v2 — SPY top5/top10/HHI 일일',
        'kwargs': {'etf_symbol': 'SPY'},
    },
    {
        'name': 'mp_calc_sector_5min',
        'task': 'marketpulse.tasks.sector_flow.mp_calc_sector_5min',
        'crontab': {'minute': '*/5', 'hour': '9-16', 'day_of_week': '1-5',
                    'day_of_month': '*', 'month_of_year': '*'},
        'description': 'Market Pulse v2 — 11 섹터 long-format S02~S06',
        'kwargs': {},
    },
    {
        'name': 'mp_detect_anomaly_5min',
        'task': 'marketpulse.tasks.anomaly.mp_detect_anomaly_5min',
        'crontab': {'minute': '*/5', 'hour': '9-16', 'day_of_week': '1-5',
                    'day_of_month': '*', 'month_of_year': '*'},
        'description': 'Market Pulse v2 — 4 Core 룰 평가',
        'kwargs': {},
    },
    {
        'name': 'mp_generate_brief_daily',
        'task': 'marketpulse.tasks.briefing.mp_generate_brief_daily',
        'crontab': {'minute': '15', 'hour': '17', 'day_of_week': '1-5',
                    'day_of_month': '*', 'month_of_year': '*'},
        'description': 'Market Pulse v2 — Card E LLM 브리핑 (Gemini 2.5 Flash 동기)',
        'kwargs': {},
    },
    {
        'name': 'mp_finalize_daily',
        'task': 'marketpulse.tasks.finalize.mp_finalize_daily',
        'crontab': {'minute': '30', 'hour': '16', 'day_of_week': '1-5',
                    'day_of_month': '*', 'month_of_year': '*'},
        'description': 'Market Pulse v2 — 4 스냅샷 finalize + 캐시 invalidate',
        'kwargs': {},
    },
    {
        'name': 'mp_purge_news_daily',
        'task': 'marketpulse.tasks.finalize.mp_purge_news_daily',
        'crontab': {'minute': '0', 'hour': '14', 'day_of_week': '*',
                    'day_of_month': '*', 'month_of_year': '*'},
        'description': 'Market Pulse v2 — 90일 초과 뉴스 정리',
        'kwargs': {},
    },
    {
        'name': 'mp_purge_news_view_log_daily',
        'task': 'marketpulse.tasks.finalize.mp_purge_news_view_log_daily',
        'crontab': {'minute': '5', 'hour': '14', 'day_of_week': '*',
                    'day_of_month': '*', 'month_of_year': '*'},
        'description': 'Market Pulse v2 — 24h+ NewsViewLog 정리',
        'kwargs': {},
    },
    {
        'name': 'mp_calc_regime_15min',
        'task': 'marketpulse.tasks.regime.mp_calc_regime_15min',
        'crontab': {'minute': '*/15', 'hour': '*', 'day_of_week': '*',
                    'day_of_month': '*', 'month_of_year': '*'},
        'description': 'Market Pulse v2 — 14 지표 + 5단계 Regime Classifier',
        'kwargs': {},
    },
    {
        # NY 17:35 = KST 06:35 (DST). mp_calc_concentration_daily(17:15) 직후, brief(17:15는 동일 분리, 다른 시각)
        # 다음 사이클 mp_calc_regime_15min에서 최신 VIX3M/MOVE 즉시 반영.
        'name': 'mp_sync_yahoo_indicators_daily',
        'task': 'marketpulse.tasks.sync_indicators.mp_sync_yahoo_indicators_daily',
        'crontab': {'minute': '35', 'hour': '17', 'day_of_week': '1-5',
                    'day_of_month': '*', 'month_of_year': '*'},
        'description': 'Market Pulse v2 — Yahoo Finance VIX3M/MOVE 일별 동기화 (FRED 미지원 보완)',
        'kwargs': {'period': '3mo'},
    },
]


class Command(BaseCommand):
    help = 'Market Pulse v2 Celery Beat PeriodicTask DB 등록 (멱등).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--disable', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        disable = options['disable']

        if disable:
            return self._disable(dry_run=dry_run)

        created_n = updated_n = 0
        for entry in SCHEDULES:
            if dry_run:
                self.stdout.write(f'[dry-run] would upsert PeriodicTask({entry["name"]})')
                continue
            crontab, _ = CrontabSchedule.objects.get_or_create(**entry['crontab'])
            obj, created = PeriodicTask.objects.update_or_create(
                name=entry['name'],
                defaults={
                    'task': entry['task'],
                    'crontab': crontab,
                    'interval': None,
                    'kwargs': json.dumps(entry.get('kwargs') or {}),
                    'description': entry.get('description', ''),
                    'enabled': True,
                },
            )
            if created:
                created_n += 1
                self.stdout.write(self.style.SUCCESS(f'[created] {obj.name}'))
            else:
                updated_n += 1
                self.stdout.write(self.style.WARNING(f'[updated] {obj.name}'))

        self.stdout.write(self.style.SUCCESS(
            f'Done. created={created_n} updated={updated_n} dry_run={dry_run}'
        ))

    def _disable(self, *, dry_run: bool) -> None:
        names = [entry['name'] for entry in SCHEDULES]
        qs = PeriodicTask.objects.filter(name__in=names)
        if dry_run:
            for t in qs:
                self.stdout.write(f'[dry-run] would disable {t.name}')
            return
        n = qs.update(enabled=False)
        self.stdout.write(self.style.WARNING(f'Disabled {n} task(s)'))
