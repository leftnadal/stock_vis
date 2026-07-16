"""매수 시나리오 처리 — 가격 구간 전이 + 기한만료 제안 (TIMING-P1, D-TIMING-DECISIONS-5 ③④).

refresh 흐름의 evaluate **직후** additive 호출(신규 beat 없음, state_machine 무접촉).
가격 있는 active Claim마다: zone 산출 → last_price_zone 비교 → 전이 이벤트/entry_reached_at,
그리고 기한만료 제안(자동 마감 금지 — 제안만, 3-B). 반환 이벤트는 다이제스트가 소비.
"""
import logging

from django.utils import timezone

from apps.monitor.models import Claim
from apps.monitor.services.closure import is_expired_scenario
from apps.monitor.services.price_zone import is_immediate_zone_alert, resolve_zone

logger = logging.getLogger(__name__)


def latest_close(symbol, as_of=None):
    """종목의 최신 종가(as_of 지정 시 그 이하 최근). EODSignal 우선, 없으면 DailyPrice."""
    from packages.shared.stocks.models import DailyPrice, EODSignal

    sym = symbol.upper()
    eq = EODSignal.objects.filter(stock__symbol=sym)
    if as_of:
        eq = eq.filter(date__lte=as_of)
    row = eq.order_by("-date").values_list("close_price", flat=True).first()
    if row is not None:
        return float(row)

    dq = DailyPrice.objects.filter(stock__symbol=sym)
    if as_of:
        dq = dq.filter(date__lte=as_of)
    row = dq.order_by("-date").values_list("close_price", flat=True).first()
    return float(row) if row is not None else None


def process_claim_scenario(claim, close, as_of):
    """Claim 하나의 zone 전이 + 기한만료 제안 처리. 반환 = 이벤트 dict 목록.

    상태 저장(last_price_zone·entry_reached_at·proposed_verdict)은 여기서 update_fields로만.
    """
    events = []
    update_fields = []

    # ── 가격 구간 전이 ──
    zone = resolve_zone(close, claim.entry_price, claim.target_price, claim.stop_price)
    if zone is not None:
        prev = claim.last_price_zone

        # ENTRY 최초 도달 → entry_reached_at 1회 기록
        if zone == Claim.PriceZone.ENTRY and claim.entry_reached_at is None:
            claim.entry_reached_at = timezone.now()
            update_fields.append("entry_reached_at")

        if prev != zone:
            events.append({
                "type": "zone",
                "claim_id": str(claim.id),
                "monitor_name": claim.monitor.name,
                "target_ref": claim.monitor.target_ref,
                "from_zone": prev,
                "to_zone": zone,
                "immediate": is_immediate_zone_alert(zone),
                "close": close,
            })
            claim.last_price_zone = zone
            update_fields.append("last_price_zone")

    # ── 기한만료 제안 (자동 마감 금지 — proposed_verdict 제안 + 1회 알림 가드) ──
    if is_expired_scenario(claim, as_of) and claim.proposed_verdict != Claim.ProposedVerdict.EXPIRED:
        claim.proposed_verdict = Claim.ProposedVerdict.EXPIRED
        update_fields.append("proposed_verdict")
        events.append({
            "type": "expiry",
            "claim_id": str(claim.id),
            "monitor_name": claim.monitor.name,
            "target_ref": claim.monitor.target_ref,
            "deadline": claim.deadline.isoformat() if claim.deadline else None,
            "immediate": True,
        })

    if update_fields:
        claim.save(update_fields=update_fields)
    return events


def process_monitor_scenarios(monitor, as_of=None):
    """모니터의 active Claim 전부 시나리오 처리. 반환 = 전 이벤트 목록(다이제스트 입력)."""
    as_of = as_of or timezone.localdate()
    close = latest_close(monitor.target_ref, as_of=as_of)

    events = []
    for claim in monitor.claims.filter(status=Claim.Status.ACTIVE):
        try:
            events.extend(process_claim_scenario(claim, close, as_of))
        except Exception:  # noqa: BLE001 — 배치 격리
            logger.exception("scenario 처리 실패: claim=%s", claim.id)
    return events
