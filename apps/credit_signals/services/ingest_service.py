"""
FRED 관측치 수집·적재 서비스 (PR §3·§4).

upsert 규약 (§3):
  - 최초 (series_id, date) → insert, ingested_at=now, revised_at=null
  - 기존 존재 + value 동일 → no-op (ingested_at 유지)
  - 기존 존재 + value 상이(revise) → value 갱신 + revised_at=now, ingested_at 유지

FRED가 과거값을 revise하는 경우가 있으므로 update_or_create가 아니라
값 비교 후 조건부 update로 처리한다. 값 비교는 4자리로 quantize해
저장 정밀도(decimal_places=4)와 raw 값의 미세 차이가 매 수집마다 허위
revise를 유발하지 않게 한다 (멱등성 보장).
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from ..constants import FRED_SERIES, INGEST_WINDOW_DAYS
from ..models import MacroSeriesHistory

logger = logging.getLogger(__name__)

_QUANT = Decimal("0.0001")  # decimal_places=4 정합


def _parse_value(raw) -> Decimal | None:
    """FRED value 문자열을 Decimal(4자리)로 변환. 결측('.'/빈값)은 None."""
    if raw is None:
        return None
    s = str(raw).strip()
    if s in ("", "."):
        return None
    try:
        return Decimal(s).quantize(_QUANT)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _parse_date(raw) -> date | None:
    if isinstance(raw, date):
        return raw
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def upsert_observations(series_id: str, observations: list) -> dict:
    """
    관측치 리스트를 원장에 upsert. (created, updated, skipped) 카운트 반환.

    삭제는 절대 하지 않는다 (§10 영구 누적 원칙).
    """
    created = updated = skipped = 0
    for obs in observations:
        value = _parse_value(obs.get("value"))
        obs_date = _parse_date(obs.get("date"))
        if value is None or obs_date is None:
            skipped += 1
            continue

        existing = MacroSeriesHistory.objects.filter(
            series_id=series_id, date=obs_date
        ).first()
        if existing is None:
            MacroSeriesHistory.objects.create(
                series_id=series_id, date=obs_date, value=value
            )
            created += 1
        elif existing.value != value:
            existing.value = value
            existing.revised_at = timezone.now()
            existing.save(update_fields=["value", "revised_at"])
            updated += 1
        # value 동일 → no-op (ingested_at 유지)

    return {"created": created, "updated": updated, "skipped": skipped}


def ingest_series(client, series_id: str, observation_start: str = None,
                  observation_end: str = None, limit: int = 100) -> dict:
    """단일 시리즈를 FRED에서 조회해 upsert."""
    observations = client.get_series_observations(
        series_id,
        observation_start=observation_start,
        observation_end=observation_end,
        limit=limit,
        sort_order="desc",
    )
    return upsert_observations(series_id, observations)


def ingest_recent(client, days: int = INGEST_WINDOW_DAYS, today: date = None) -> dict:
    """
    FRED_SERIES 전체를 최근 `days` 창으로 조회해 upsert (일별 증분).
    시리즈별 결과 dict를 합쳐 반환.
    """
    end = today or date.today()
    start = end - timedelta(days=days)
    summary = {}
    for series_id in FRED_SERIES:
        try:
            summary[series_id] = ingest_series(
                client,
                series_id,
                observation_start=start.isoformat(),
                observation_end=end.isoformat(),
                # 창보다 넉넉히 (재시도 결측 흡수)
                limit=days + 10,
            )
        except Exception as exc:  # noqa: BLE001 — 한 시리즈 실패가 나머지를 막지 않도록
            logger.warning("FRED ingest 실패 series=%s: %s", series_id, exc)
            summary[series_id] = {"error": str(exc)}
    return summary
