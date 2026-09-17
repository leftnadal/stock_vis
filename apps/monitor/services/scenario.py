"""매수 시나리오 처리 — 가격 구간 전이 + 기한만료 제안 (TIMING-P1, D-TIMING-DECISIONS-5 ③④).

refresh 흐름의 evaluate **직후** additive 호출(신규 beat 없음, state_machine 무접촉).
가격 있는 active Claim마다: zone 산출 → last_price_zone 비교 → 전이 이벤트/entry_reached_at,
그리고 기한만료 제안(자동 마감 금지 — 제안만, 3-B). 반환 이벤트는 다이제스트가 소비.
"""
import logging

from django.utils import timezone

from apps.monitor.models import Claim
from apps.monitor.services.closure import (
    current_overall_score,
    is_expired_scenario,
    is_hold_deadline_passed,
    propose_verdict,
)
from apps.monitor.services.price_zone import (
    NEAR_STOP_BUFFER,
    NEAR_STOP_MULTIPLIER,
    NEAR_STOP_RECHECK_DAYS,
    is_immediate_zone_alert,
    is_near_stop,
    resolve_zone,
    zone_anchor,
)

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


# 변동성 산출 창(거래일). 손잡이 3종(price_zone)과 달리 계산 세부라 여기 둔다.
NEAR_STOP_WINDOW = 20


def near_stop_buffer(symbol, as_of=None):
    """손절 접근 밴드 = max(바닥값, 배수 × median|일간 변동률| 최근 20거래일).

    데이터 20행 미만이면 바닥값(NEAR_STOP_BUFFER) 반환 — 폴백.
    price_zone은 순수 유지(D-HOLD-DECISIONS 2 전제)라 DB 조회는 이 모듈에만 둔다.

    변동성 비례인 이유: 고정 밴드는 저변동 종목에서 너무 늦고(손절을 그냥 통과),
    고변동 종목에서 너무 잦다(매일 경고). 바닥값은 저변동 쪽 하한만 지킨다.
    """
    import statistics

    from packages.shared.stocks.models import DailyPrice

    q = DailyPrice.objects.filter(stock__symbol=symbol.upper())
    if as_of:
        q = q.filter(date__lte=as_of)
    rows = list(
        q.order_by("-date").values_list("close_price", flat=True)[: NEAR_STOP_WINDOW + 1]
    )
    if len(rows) < NEAR_STOP_WINDOW + 1:
        return NEAR_STOP_BUFFER

    closes = [float(c) for c in reversed(rows)]
    rets = [
        abs(cur - prev) / prev
        for prev, cur in zip(closes, closes[1:])
        if prev
    ]
    if len(rets) < NEAR_STOP_WINDOW:
        return NEAR_STOP_BUFFER
    return max(float(NEAR_STOP_BUFFER), NEAR_STOP_MULTIPLIER * statistics.median(rets))


def process_claim_scenario(claim, close, as_of):
    """Claim 하나의 zone 전이 + 기한만료 제안 처리. 반환 = 이벤트 dict 목록.

    상태 저장(last_price_zone·entry_reached_at·proposed_verdict)은 여기서 update_fields로만.
    """
    events = []
    update_fields = []
    mode = claim.scenario_type
    is_hold = mode == Claim.ScenarioType.HOLD

    # ── 가격 구간 전이 (앵커 = hold면 매입가, 그 외 진입가 — 수학 동일) ──
    zone = resolve_zone(close, zone_anchor(claim), claim.target_price, claim.stop_price)
    if zone is not None:
        prev = claim.last_price_zone

        # ENTRY 최초 도달 → entry_reached_at 1회 기록 (신규 매수 전용 — hold는 진입 개념 없음)
        if (
            not is_hold
            and zone == Claim.PriceZone.ENTRY
            and claim.entry_reached_at is None
        ):
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
                "immediate": is_immediate_zone_alert(zone, mode=mode),
                "close": close,
            })
            claim.last_price_zone = zone
            update_fields.append("last_price_zone")

    # ── 손절 접근 경고 (3-A) — zone 축과 별개. 1회 가드 + 밴드 이탈 시 해제 ──
    # hold 모드에서 매입가 아래는 전부 ENTRY 한 칸이라 zone 전이로는 손절 접근을 잡을 수 없다.
    # 손절선을 "넘은 뒤"(EXITED) 알리면 이미 늦으므로 넘기 전에 한 번 알린다.
    if claim.stop_price is not None and close is not None:
        buf = near_stop_buffer(claim.monitor.target_ref, as_of)
        near = is_near_stop(close, claim.stop_price, buf)
        notified = claim.near_stop_notified_at
        # 재발화 창: 밴드 안에 계속 머물면 N일마다 재확인. 메일 1회 실패가 영구 침묵이
        # 되지 않게 하는 유일한 이중화다 — near_stop은 인앱 표면(3-B)이 아직 없고,
        # claim.save()는 pipeline.py:154에서 먼저 커밋되므로 send_digest 실패를 모른다.
        # 비교는 UTC date끼리다: notified=timezone.now()(UTC), as_of=et_today()이고
        # beat는 22:45 UTC(=18:45 ET)에 도므로 두 날짜가 같은 날을 가리킨다.
        # localtime()으로 바꾸면 KST가 되어 하루 밀린다 — 바꾸지 말 것.
        is_recheck = bool(
            notified is not None
            and (as_of - notified.date()).days >= NEAR_STOP_RECHECK_DAYS
        )
        if near and (notified is None or is_recheck):
            stop_f = float(claim.stop_price)
            claim.near_stop_notified_at = timezone.now()
            update_fields.append("near_stop_notified_at")
            events.append({
                "type": "near_stop",
                "claim_id": str(claim.id),
                "monitor_name": claim.monitor.name,
                "target_ref": claim.monitor.target_ref,
                "close": close,
                "stop": stop_f,
                "to_stop_pct": (stop_f - close) / close * 100.0,
                "band_pct": float(buf) * 100.0,
                "recheck": is_recheck,
                "immediate": True,
            })
        elif not near and notified is not None:
            # 밴드 밖으로 회복(또는 이탈 확정) → 가드 해제. 재진입하면 다시 최초 발화한다.
            claim.near_stop_notified_at = None
            update_fields.append("near_stop_notified_at")

    # ── 기한만료 (자동 마감 금지 — 1회 알림 가드) ──
    if not is_hold:
        # 신규 매수: 진입 미도달 만료 → EXPIRED 제안 (기존 불변)
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
    else:
        # 보유 관리: 만료 = 알림 1회 + 기존 점수 밴드 제안 유지(EXPIRED 미설정, D-HOLD-DECISIONS 부속).
        # 가드 = proposed_verdict None→score-band 전이 1회.
        if is_hold_deadline_passed(claim, as_of) and claim.proposed_verdict is None:
            claim.proposed_verdict = propose_verdict(current_overall_score(claim.monitor))
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
