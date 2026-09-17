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
# 🔴 동결 항목은 **사유코드를 갖는다.** 예외는 "테스트가 빨개서"가 아니라 아래 카테고리에
#    해당해서 들어간다. 사유코드 없이는 추가할 수 없고, **새 사유코드를 만드는 것은 디렉터 결정**이다.
#    어느 카테고리에도 맞지 않는 새 앵커는 여전히 진짜 신호다 — RED가 옳다.
#    (D-ASOF-EXEMPT-0912. 이 장치가 없으면 동결 목록이 테스트 무마용 쓰레기통이 된다.)
#
# as_of_week 규칙은 **자동 주간 발화**에만 적용 가능하다. 사람이 만든 소급/임시 적재는 실행
# 시각이 데이터 내용과 무관하므로 관측시각 기반 추론이 **원리적으로 불가능**하다.

#: 사람이 만든 소급 적재 — 실행시각이 데이터 내용과 무관(자동발화 아님).
EXEMPT_MANUAL_BACKFILL = "MANUAL_BACKFILL"
#: 사람이 만든 임시 관측 — 주간 마감일이 아님(자동발화 아님).
EXEMPT_MANUAL_ADHOC = "MANUAL_ADHOC"
#: 장애로 관측이 밀려 기록됐고, 사건 흔적 보존을 위해 삭제하지 않기로 디렉터가 결정한 앵커.
EXEMPT_INCIDENT_PRESERVED = "INCIDENT_PRESERVED"

EXEMPT_REASON_CODES = frozenset(
    {EXEMPT_MANUAL_BACKFILL, EXEMPT_MANUAL_ADHOC, EXEMPT_INCIDENT_PRESERVED}
)

#: 키 = (모델 레이블, 앵커). 값 = (사유코드, 근거 1줄).
ANCHOR_EXEMPTIONS: dict[tuple[str, date], tuple[str, str]] = {
    # ── 2026-08-16 일괄백필 3건 (created_at 08-15 21:01 ET 동일) ──
    ("SymbolDemandSignal", date(2026, 7, 24)): (
        EXEMPT_MANUAL_BACKFILL,
        "2026-08-16 일괄백필 — 사람이 만든 소급 적재",
    ),
    ("SymbolDemandSignal", date(2026, 7, 31)): (
        EXEMPT_MANUAL_BACKFILL,
        "2026-08-16 일괄백필 — 사람이 만든 소급 적재",
    ),
    ("SymbolDemandSignal", date(2026, 8, 7)): (
        EXEMPT_MANUAL_BACKFILL,
        "2026-08-16 일괄백필 — 사람이 만든 소급 적재",
    ),
    # ── 수요일 임시수집 1건 ──
    ("EstimateSnapshot", date(2026, 7, 29)): (
        EXEMPT_MANUAL_ADHOC,
        "2026-07-29(수) 임시 관측 — 주간 마감일이 아님(앵커 쪽이 주간 라벨이 아니다)",
    ),
    # ── 09-12 사건분 2건 (D-ASOF-EXEMPT-0912) ──
    # celery-beat 크래시루프(09-12 02:23~12:31 KST)로 09-11 발화가 소실되고 관측이 하루 밀려
    # 기록됐다. 사건 흔적 보존을 위해 삭제하지 않기로 디렉터가 결정했으므로(D-DSS-W11-RESCUE
    # §3-4) 위반이 영구 잔존한다 → 사유 분류하여 동결.
    ("EstimateSnapshot", date(2026, 9, 12)): (
        EXEMPT_INCIDENT_PRESERVED,
        "celery-beat 크래시루프로 09-11 발화 소실·관측 1일 지연 기록. 사건 흔적 보존(디렉터 결정)",
    ),
    ("SymbolDemandSignal", date(2026, 9, 12)): (
        EXEMPT_INCIDENT_PRESERVED,
        "celery-beat 크래시루프로 09-11 발화 소실·관측 1일 지연 기록. 사건 흔적 보존(디렉터 결정)",
    ),
    # ── 2026-09-11 백필분은 동결 불필요 ──
    # `backfill_snapshot_anchor`가 created_at을 원본(09-12 15:03 ET)으로 유지하므로
    # as_of_week(created_at) == 09-11 == anchor 로 규칙을 그대로 만족한다.
}


def exemption_reason(model_label: str, anchor: date) -> tuple[str, str] | None:
    """해당 (모델, 앵커)의 (사유코드, 근거). 동결이 아니면 None."""
    return ANCHOR_EXEMPTIONS.get((model_label, anchor))


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
