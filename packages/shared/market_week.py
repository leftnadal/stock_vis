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
