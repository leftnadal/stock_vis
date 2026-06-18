"""
setup_marketpulse_beat — Celery Beat 등록(DB) 단일 진입점, 멱등 (Bug #28 패턴).

소속: apps/market_pulse/management/commands (app 레이어 운영 커맨드).
역할: 마켓 펄스 v2의 모든 Celery task에 대해 django_celery_beat의 PeriodicTask·
  CrontabSchedule을 DB에 idempotent 등록. config/settings.py의
  CELERY_BEAT_SCHEDULER='django_celery_beat.schedulers:DatabaseScheduler' 환경에서
  유일한 진실의 소스(config/celery.py dict는 dev 회피용).
주의: 본 커맨드는 task 신규 등록·schedule 갱신만 처리. 옛 task 경로 잔재가 있을 때는
  `sync_beat_schedule --apply`로 reconcile 필요(Bug #28).
사용: `python manage.py setup_marketpulse_beat` (멱등) / `--disable`로 비활성화.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask

logger = logging.getLogger(__name__)


SCHEDULES: list[dict[str, Any]] = [
    {
        "name": "mp_fetch_news_hourly",
        "task": "apps.market_pulse.tasks.news.mp_fetch_news_hourly",
        "crontab": {
            "minute": "5",
            "hour": "*",
            "day_of_week": "*",
            "day_of_month": "*",
            "month_of_year": "*",
        },
        "description": "Market Pulse v2 — 6 카테고리 뉴스 수집",
        "kwargs": {},
    },
    {
        "name": "mp_calc_breadth_5min",
        "task": "apps.market_pulse.tasks.breadth.mp_calc_breadth_5min",
        "crontab": {
            "minute": "*/5",
            "hour": "9-16",
            "day_of_week": "1-5",
            "day_of_month": "*",
            "month_of_year": "*",
        },
        "description": "Market Pulse v2 — SPY breadth 5분 주기",
        "kwargs": {"universe": "SPY"},
    },
    {
        "name": "mp_calc_concentration_daily",
        "task": "apps.market_pulse.tasks.concentration.mp_calc_concentration_daily",
        "crontab": {
            "minute": "15",
            "hour": "17",
            "day_of_week": "1-5",
            "day_of_month": "*",
            "month_of_year": "*",
        },
        "description": "Market Pulse v2 — SPY top5/top10/HHI 일일",
        "kwargs": {"etf_symbol": "SPY"},
    },
    {
        "name": "mp_calc_sector_5min",
        "task": "apps.market_pulse.tasks.sector_flow.mp_calc_sector_5min",
        "crontab": {
            "minute": "*/5",
            "hour": "9-16",
            "day_of_week": "1-5",
            "day_of_month": "*",
            "month_of_year": "*",
        },
        "description": "Market Pulse v2 — 11 섹터 long-format S02~S06",
        "kwargs": {},
    },
    {
        "name": "mp_detect_anomaly_5min",
        "task": "apps.market_pulse.tasks.anomaly.mp_detect_anomaly_5min",
        "crontab": {
            "minute": "*/5",
            "hour": "9-16",
            "day_of_week": "1-5",
            "day_of_month": "*",
            "month_of_year": "*",
        },
        "description": "Market Pulse v2 — 4 Core 룰 평가",
        "kwargs": {},
    },
    {
        "name": "mp_generate_brief_daily",
        "task": "apps.market_pulse.tasks.briefing.mp_generate_brief_daily",
        "crontab": {
            "minute": "15",
            "hour": "17",
            "day_of_week": "1-5",
            "day_of_month": "*",
            "month_of_year": "*",
        },
        "description": "Market Pulse v2 — Card E LLM 브리핑 (Gemini 2.5 Flash 동기)",
        "kwargs": {},
    },
    {
        "name": "mp_finalize_daily",
        "task": "apps.market_pulse.tasks.finalize.mp_finalize_daily",
        "crontab": {
            "minute": "30",
            "hour": "16",
            "day_of_week": "1-5",
            "day_of_month": "*",
            "month_of_year": "*",
        },
        "description": "Market Pulse v2 — 4 스냅샷 finalize + 캐시 invalidate",
        "kwargs": {},
    },
    {
        "name": "mp_purge_news_daily",
        "task": "apps.market_pulse.tasks.finalize.mp_purge_news_daily",
        "crontab": {
            "minute": "0",
            "hour": "14",
            "day_of_week": "*",
            "day_of_month": "*",
            "month_of_year": "*",
        },
        "description": "Market Pulse v2 — 90일 초과 뉴스 정리",
        "kwargs": {},
    },
    {
        "name": "mp_purge_news_view_log_daily",
        "task": "apps.market_pulse.tasks.finalize.mp_purge_news_view_log_daily",
        "crontab": {
            "minute": "5",
            "hour": "14",
            "day_of_week": "*",
            "day_of_month": "*",
            "month_of_year": "*",
        },
        "description": "Market Pulse v2 — 24h+ NewsViewLog 정리",
        "kwargs": {},
    },
    {
        "name": "mp_calc_regime_15min",
        "task": "apps.market_pulse.tasks.regime.mp_calc_regime_15min",
        "crontab": {
            "minute": "*/15",
            "hour": "*",
            "day_of_week": "*",
            "day_of_month": "*",
            "month_of_year": "*",
        },
        "description": "Market Pulse v2 — 14 지표 + 5단계 Regime Classifier",
        "kwargs": {},
    },
    {
        # NY 17:35 = KST 06:35 (DST). mp_calc_concentration_daily(17:15) 직후, brief(17:15는 동일 분리, 다른 시각)
        # 다음 사이클 mp_calc_regime_15min에서 최신 VIX3M/MOVE 즉시 반영.
        "name": "mp_sync_yahoo_indicators_daily",
        "task": "apps.market_pulse.tasks.sync_indicators.mp_sync_yahoo_indicators_daily",
        "crontab": {
            "minute": "35",
            "hour": "17",
            "day_of_week": "1-5",
            "day_of_month": "*",
            "month_of_year": "*",
        },
        "description": "Market Pulse v2 — Yahoo Finance VIX3M/MOVE 일별 동기화 (FRED 미지원 보완)",
        "kwargs": {"period": "3mo"},
    },
    {
        # NY 17:40 = KST 06:40 (DST). yahoo sync(17:35) 직후 → 다음 mp_calc_regime_15min에
        # 최신 FRED 7종 즉시 반영. MP-DATA-MACRO-COVERAGE: 수동 의존 7종(NFCI군·HY pair·T10Y3M)
        # 재귀 자동화 → stale→null 회귀 차단. ⚠️ Bug #28: 본 SCHEDULES는 DB 직접 등록 방식이라
        # 배포 시마다 `setup_marketpulse_beat` 재실행 필요(beat dict는 DatabaseScheduler가 무시).
        "name": "mp_sync_fred_indicators_daily",
        "task": "apps.market_pulse.tasks.sync_indicators.mp_sync_fred_indicators_daily",
        "crontab": {
            "minute": "40",
            "hour": "17",
            "day_of_week": "1-5",
            "day_of_month": "*",
            "month_of_year": "*",
        },
        "description": "Market Pulse v2 — FRED 7종(NFCI군·HY pair·T10Y3M) 재귀 동기화 (MP-DATA-MACRO-COVERAGE, 수동 의존 해소)",
        "kwargs": {"limit": 100},
    },
]


class Command(BaseCommand):
    help = "Market Pulse v2 Celery Beat PeriodicTask DB 등록 (멱등)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--disable", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        disable = options["disable"]

        if disable:
            return self._disable(dry_run=dry_run)

        created_n = updated_n = 0
        for entry in SCHEDULES:
            if dry_run:
                self.stdout.write(
                    f"[dry-run] would upsert PeriodicTask({entry['name']})"
                )
                continue
            crontab, _ = CrontabSchedule.objects.get_or_create(**entry["crontab"])
            obj, created = PeriodicTask.objects.update_or_create(
                name=entry["name"],
                defaults={
                    "task": entry["task"],
                    "crontab": crontab,
                    "interval": None,
                    "kwargs": json.dumps(entry.get("kwargs") or {}),
                    "description": entry.get("description", ""),
                    "enabled": True,
                },
            )
            if created:
                created_n += 1
                self.stdout.write(self.style.SUCCESS(f"[created] {obj.name}"))
            else:
                updated_n += 1
                self.stdout.write(self.style.WARNING(f"[updated] {obj.name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. created={created_n} updated={updated_n} dry_run={dry_run}"
            )
        )

    def _disable(self, *, dry_run: bool) -> None:
        names = [entry["name"] for entry in SCHEDULES]
        qs = PeriodicTask.objects.filter(name__in=names)
        if dry_run:
            for t in qs:
                self.stdout.write(f"[dry-run] would disable {t.name}")
            return
        n = qs.update(enabled=False)
        self.stdout.write(self.style.WARNING(f"Disabled {n} task(s)"))
