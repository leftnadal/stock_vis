"""가격 구간축 (zone) 순수 판정 (TIMING-P1, D-TIMING-DECISIONS-5 ③-B).

Claim 가격 파라미터(entry/target/stop) 대비 현재 종가의 위치를 5구간으로 사상.
state_machine(신호축)과 **별개의 축** — 여기서 상태기·달위상을 건드리지 않는다.
가격 필드가 하나라도 없으면 None(구 가설 = zone 없음).
"""
from decimal import Decimal

from apps.monitor.models import Claim

# 접근 버퍼: 진입가 위 이 비율까지는 아직 "접근"(진입 여지). 상수(D-TIMING-DECISIONS-5 ③-B).
APPROACH_BUFFER = Decimal("0.03")

PriceZone = Claim.PriceZone


def resolve_zone(close, entry, target, stop):
    """현재 종가 → PriceZone. 가격 파라미터가 하나라도 None이면 None.

    경계(모두 종가 close 기준):
      close ≤ stop                     → EXITED (이탈)
      stop < close ≤ entry             → ENTRY (진입 구간)
      entry < close ≤ entry×(1+버퍼)   → APPROACH (접근)
      버퍼 초과 ~ target 미만           → WAITING (관망)
      close ≥ target                    → OVERHEATED (과열)
    """
    if close is None or entry is None or target is None or stop is None:
        return None

    close = Decimal(str(close))
    entry = Decimal(str(entry))
    target = Decimal(str(target))
    stop = Decimal(str(stop))

    if close <= stop:
        return PriceZone.EXITED
    if close <= entry:
        return PriceZone.ENTRY
    if close <= entry * (Decimal("1") + APPROACH_BUFFER):
        return PriceZone.APPROACH
    if close >= target:
        return PriceZone.OVERHEATED
    return PriceZone.WAITING


# 즉시 알림 대상 구간(도달 시점에 행동 필요) vs 다이제스트 대상.
IMMEDIATE_ALERT_ZONES = frozenset({PriceZone.ENTRY, PriceZone.EXITED})
DIGEST_ALERT_ZONES = frozenset({PriceZone.APPROACH, PriceZone.WAITING, PriceZone.OVERHEATED})


def is_immediate_zone_alert(to_zone):
    """→ENTRY, →EXITED = 즉시 알림. 관망↔접근·과열 = 다이제스트."""
    return to_zone in IMMEDIATE_ALERT_ZONES
