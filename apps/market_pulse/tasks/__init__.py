"""
apps/market_pulse/tasks — Celery tasks 통합 re-export.

소속: apps/market_pulse (app 레이어 비동기 처리).
역할: 마켓 펄스 도메인의 Celery task 16종 단일 진입점.
Celery name 규칙: 모든 task는 `apps.market_pulse.tasks.<module>.<func>` 형태로 명명.
  monorepo PR4(2026-05-31) 이후 옛 `marketpulse.tasks.*` 경로는 폐기 — Beat DB의
  옛 경로가 남아 있을 경우 `sync_beat_schedule --apply` reconcile 필요(Bug #28).
스케줄링: Beat 등록은 `management/commands/setup_marketpulse_beat.py`가 단일 진입점
  (멱등). 직접 호출자 없음 — Beat에 의해서만 디스패치.
주의: Celery 안에서는 동기 API만 사용(Bug #8: async LLM/genai.Client 금지).
"""

from .anomaly import mp_detect_anomaly_5min
from .breadth import mp_calc_breadth_5min
from .briefing import mp_generate_brief_daily
from .concentration import mp_calc_concentration_daily
from .finalize import (
    mp_finalize_daily,
    mp_purge_news_daily,
    mp_purge_news_view_log_daily,
)
from .macro import (
    cleanup_old_data,
    refresh_market_pulse_cache,
    update_economic_calendar,
    update_economic_indicators,
    update_market_indices,
)
from .news import mp_fetch_news_hourly
from .regime import mp_calc_regime_15min
from .sector_flow import mp_calc_sector_5min
from .sync_indicators import mp_sync_yahoo_indicators_daily

__all__ = [
    "mp_fetch_news_hourly",
    "mp_calc_breadth_5min",
    "mp_calc_concentration_daily",
    "mp_calc_regime_15min",
    "mp_calc_sector_5min",
    "mp_detect_anomaly_5min",
    "mp_generate_brief_daily",
    "mp_finalize_daily",
    "mp_purge_news_daily",
    "mp_purge_news_view_log_daily",
    "mp_sync_yahoo_indicators_daily",
    "update_economic_indicators",
    "update_market_indices",
    "update_economic_calendar",
    "refresh_market_pulse_cache",
    "cleanup_old_data",
]
