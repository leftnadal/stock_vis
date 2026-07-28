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


# "익절 접근" 표시 재구간화 임계 (D-HOLD-DECISIONS 부속) — close ≥ target×(1-이 값)이면 익절 접근.
# 저장 zone(resolve_zone) 무관 — hold 표시 전용.
NEAR_TARGET_BUFFER = Decimal("0.03")

# 즉시 알림 대상 구간 — 모드별(D-HOLD-DECISIONS 부속, 소비처만 모드 인지).
# new_entry: →ENTRY(진입 도달)·→EXITED(이탈). hold: →OVERHEATED(목표 도달)·→EXITED(손절 이탈).
IMMEDIATE_ALERT_ZONES = frozenset({PriceZone.ENTRY, PriceZone.EXITED})  # new_entry(하위호환 기본)
IMMEDIATE_ALERT_ZONES_HOLD = frozenset({PriceZone.OVERHEATED, PriceZone.EXITED})
DIGEST_ALERT_ZONES = frozenset({PriceZone.APPROACH, PriceZone.WAITING, PriceZone.OVERHEATED})


def is_immediate_zone_alert(to_zone, mode=None):
    """즉시 알림 대상 zone인가. mode='hold'면 목표 도달/이탈 즉시(진입 억제), 그 외 진입/이탈 즉시."""
    if mode == Claim.ScenarioType.HOLD:
        return to_zone in IMMEDIATE_ALERT_ZONES_HOLD
    return to_zone in IMMEDIATE_ALERT_ZONES


def zone_anchor(claim):
    """zone 계산의 중심 앵커 — hold면 매입가(확정), 그 외 진입가(제안). resolve_zone entry 인자로 치환.

    (D-HOLD-DECISIONS 2) resolve_zone 수학 불변 — 앵커만 모드별로 선택.
    """
    if claim.scenario_type == Claim.ScenarioType.HOLD:
        return claim.purchase_price
    return claim.entry_price
