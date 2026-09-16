"""
관측일 → 대상일(as_of) 매핑 — 주간 마감 종가 컨센서스의 귀속 주 판정.

문제(D-DSS-ANCHOR-SEMANTICS): 주간 스케줄 산출물이 **실행일**을 앵커로 기록하면,
실행이 밀리는 순간 원장이 조용히 거짓말을 한다. 2026-09-12(토) EstimateSnapshot은
2026-09-11(금) 마감 컨센서스를 담고 있으나 앵커는 09-12로 기록됐다
(원인 = celery-beat 크래시루프 09-12 02:23~12:31 KST, D-BEAT-PORT-EXHAUSTION).

본 모듈은 **읽는 쪽**의 순수 함수만 제공한다. 적재 경로는 무접촉(DSS-ASOF-1 §3).

의존: 표준 라이브러리만. `apps` import 0 (packages/shared 경계 규약).

한계(잔여 등재 DSS-ASOF-CAL):
  주간 마감을 **금요일 고정**으로 본다. 미국장 휴장 주(예: Good Friday)에는 실제 주간
  마감이 목요일이므로 본 함수는 그 주를 정확히 라벨하지 못한다. 거래일 캘린더는 현재
  `apps/credit_signals/trading_calendar.py`에만 있고 `packages/shared`에 없어
  (shared 승격 = 범위 확대·경계 리스크) 이번 범위에서 의존하지 않는다.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

FRIDAY = 4  # date.weekday(): 월=0 … 금=4
WEEKLY_CLOSE_TIME_ET = time(16, 0)  # 미국장 정규장 마감


def as_of_week(observed_at_et: datetime) -> date:
    """
    관측 시각이 **어느 주의 주간 마감 종가 컨센서스**를 담고 있는지 돌려준다.

    규칙 = 관측 시각(ET) 기준 **가장 최근에 완료된 주간 마감**:
      - 금요일 16:00 ET 이후          → 그 금요일
      - 금요일 16:00 ET 이전(장중)     → 직전 금요일
      - 토·일·월~목(catch-up)         → 직전 금요일

    tz-aware datetime은 ET로 변환하고, naive datetime은 이미 ET로 간주한다.
    """
    if not isinstance(observed_at_et, datetime):
        raise TypeError("as_of_week()는 datetime을 받는다 (date 아님)")

    et = observed_at_et.astimezone(ET) if observed_at_et.tzinfo else observed_at_et

    # 관측일 이하의 가장 가까운 금요일
    back = (et.weekday() - FRIDAY) % 7
    friday = et.date() - timedelta(days=back)

    # 그 금요일이 관측일 당일인데 아직 마감 전이면, 그 주 마감은 미완료 → 직전 주
    if back == 0 and et.time() < WEEKLY_CLOSE_TIME_ET:
        friday -= timedelta(days=7)

    return friday


# ────────────────────────── 앵커 as_of 계약 검증 (D-ASOF-POPULATION) ──────────────────────────
#
# 검증 모집단 = "동결 목록에 없는 모든 앵커". health_check `_BOUNDARY_KNOWN_VIOLATIONS`와 동형.
#
# 🔴 동결 목록에 항목을 추가하는 것은 **사람의 결정**이지 테스트를 통과시키는 수단이 아니다.
#    as_of_week 규칙은 자동 주간 발화에만 적용 가능하다. 사람이 만든 소급/임시 적재는 실행 시각이
#    데이터 내용과 무관하므로 관측시각 기반 추론이 **원리적으로 불가능**하다 — 그것이 동결 사유다.
#
# 키 = (모델 레이블, 앵커). 값 = 동결 근거 1줄.
ANCHOR_EXEMPTIONS: dict[tuple[str, date], str] = {
    # ── 2026-08-16 일괄백필 3건: 사람이 만든 소급 적재 (created_at 08-15 21:01 ET 동일) ──
    ("SymbolDemandSignal", date(2026, 7, 24)):
        "2026-08-16 일괄백필 — 실행시각이 데이터 내용과 무관(소급 적재)",
    ("SymbolDemandSignal", date(2026, 7, 31)):
        "2026-08-16 일괄백필 — 실행시각이 데이터 내용과 무관(소급 적재)",
    ("SymbolDemandSignal", date(2026, 8, 7)):
        "2026-08-16 일괄백필 — 실행시각이 데이터 내용과 무관(소급 적재)",
    # ── 임시수집 1건: 수요일 수집이라 주간 마감 라벨이 아니다 ──
    ("EstimateSnapshot", date(2026, 7, 29)):
        "2026-07-29(수) 임시수집 — 주간 마감일이 아님(앵커 쪽이 주간 라벨이 아니다)",
    # ── (§3 백필 집행 후) 2026-09-11 항목을 여기에 추가한다. 집행 전에는 넣지 않는다. ──
}


def is_anchor_exempt(model_label: str, anchor: date) -> bool:
    """해당 (모델, 앵커)가 동결 목록에 있는가."""
    return (model_label, anchor) in ANCHOR_EXEMPTIONS


def find_anchor_violations(
    model_label: str, rows: "Iterable[tuple[date, datetime]]"
) -> list[tuple[date, datetime, date]]:
    """
    동결 목록 제외 후 `as_of_week(관측시각) != 앵커`인 행을 돌려준다.

    rows = (앵커, 그 앵커의 최초 관측시각) 튜플들. 반환 = (앵커, 관측시각, 산출된 as_of).
    빈 리스트 = 계약 준수.
    """
    out = []
    for anchor, observed_at in rows:
        if is_anchor_exempt(model_label, anchor):
            continue
        got = as_of_week(observed_at)
        if got != anchor:
            out.append((anchor, observed_at, got))
    return out
