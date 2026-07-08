"""
credit_signals Celery 태스크 (PR §4).

  - ingest_fred_daily_task        FRED 6종 최근 창 조회 → upsert → compute 체이닝
  - compute_credit_signals_task   원장에서 z/grade 계산 → CreditSignalState upsert
  - check_credit_ingest_succeeded verify: 미 영업일 최신 데이터 존재 확인, 결측 시 ERROR 로그

모든 태스크는 최상단 CREDIT_SIGNALS_ENABLED flag guard (기본 false, Decision ⑨-C 패턴).
flag-off이면 no-op. ingest→compute 체이닝은 sec_pipeline in-code .delay() 패턴 동형.
"""
import logging
from datetime import date

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .constants import FRED_SERIES, INGEST_STALE_DAYS, INGEST_WINDOW_DAYS
from .models import MacroSeriesHistory

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return bool(getattr(settings, "CREDIT_SIGNALS_ENABLED", False))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_fred_daily_task(self):
    """FRED 6종을 최근 창으로 수집·upsert 후 compute 태스크 체이닝."""
    if not _enabled():
        logger.info("credit_signals flag-off — skip ingest")
        return {"enabled": False}

    from packages.shared.api_request.fred_client import FREDClient
    from .services.ingest_service import ingest_recent

    try:
        client = FREDClient()
        summary = ingest_recent(client, days=INGEST_WINDOW_DAYS)
    except Exception as exc:  # 예상치 못한 오류만 재시도 (rate limit/일시 장애)
        logger.warning("credit_signals ingest 오류 — 재시도: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    # ingest 성공 → compute 체이닝 (Decision ⑨-C, flag guard 포함)
    compute_credit_signals_task.delay()
    logger.info("credit_signals ingest 완료: %s", summary)
    return {"enabled": True, "summary": summary}


@shared_task
def compute_credit_signals_task():
    """원장에서 6개 signal_key의 z/grade를 계산해 CreditSignalState upsert."""
    if not _enabled():
        logger.info("credit_signals flag-off — skip compute")
        return {"enabled": False}

    from .services.signal_service import compute_all_signals

    results = compute_all_signals()
    logger.info("credit_signals compute 완료: %s", results)
    return {"enabled": True, "results": results}


def _find_stale_series(today: date) -> dict:
    """
    각 시리즈의 최신 관측일이 INGEST_STALE_DAYS보다 오래됐거나 결측이면 반환.
    { series_id: latest_date_or_None } (결측/stale만 담김).
    """
    stale = {}
    for series_id in FRED_SERIES:
        latest = (
            MacroSeriesHistory.objects.filter(series_id=series_id)
            .order_by("-date")
            .values_list("date", flat=True)
            .first()
        )
        if latest is None or (today - latest).days > INGEST_STALE_DAYS:
            stale[series_id] = latest
    return stale


@shared_task
def check_credit_ingest_succeeded():
    """
    verify: 미국 영업일 기준 최신 데이터 존재를 확인, 결측 시 ERROR 로그.
    주말(토/일)은 정상 통과 (FRED 미발행).
    """
    if not _enabled():
        logger.info("credit_signals flag-off — skip verify")
        return {"enabled": False}

    today = timezone.localdate()
    if today.weekday() >= 5:  # 5=토, 6=일
        logger.info("credit_signals verify: 주말 — 통과")
        return {"enabled": True, "skipped": "weekend"}

    stale = _find_stale_series(today)
    if stale:
        logger.error(
            "credit_signals ingest verify FAILED — %d개 시리즈 결측/stale "
            "(최신 관측 > %d일 경과): %s",
            len(stale),
            INGEST_STALE_DAYS,
            {k: (v.isoformat() if v else None) for k, v in stale.items()},
        )
        return {"enabled": True, "ok": False, "stale": list(stale.keys())}

    logger.info("credit_signals verify OK — 6종 최신")
    return {"enabled": True, "ok": True}
