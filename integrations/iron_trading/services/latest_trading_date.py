"""iron-trading latest-trading-date 해석기 (read-only, 방안 B).

daily-context로 200을 보장하는 "지금 조회 가능한 최신 미국장 거래일"을 산출한다.

방안 B (dry-check 검증):
    후보일을 내림차순으로 순회하며 (1) pipeline `running`이면 skip, (2) 그 날짜가
    실제로 후보 + OHLCV ≥ 1을 내는지 read-only로 dry-check 한다. 단순 최댓값을
    신뢰하지 않고, daily-context의 200 게이트와 **동일한 판정**(후보 존재 + OHLCV
    존재)을 기존 함수 재사용으로 가볍게 흉내 내어 라운드트립 200을 구조로 보장한다.

read-only 원칙: 어떤 모델도 수정하지 않는다. pipeline 실행·snapshot 생성 없음.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from packages.shared.stocks.models import EODSignal, PipelineLog

from .daily_context import (
    DEFAULT_LIMIT,
    DEFAULT_UNIVERSE,
    MARKET_TZ,
    PROVIDER,
    SCHEMA_VERSION,
    _load_ohlcv_map,
    _select_candidate_symbols,
)

SUPPORTED_UNIVERSES = {DEFAULT_UNIVERSE}  # 1차: us_core 만
SELECTION_POLICY = "latest_daily_context_available"
SCAN_LIMIT = 20  # 최악 순회 비용 유계 (정상 상태에선 첫 날짜가 즉시 통과)


class UnsupportedUniverse(Exception):
    def __init__(self, universe: str):
        super().__init__(universe)
        self.universe = universe
        self.message = (
            f"universe {universe!r} not supported. "
            f"Only {DEFAULT_UNIVERSE!r} is available."
        )


class LatestDateNotFound(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class LatestDateBuilding(Exception):
    def __init__(self, message: str, retry_after_seconds: int = 300):
        super().__init__(message)
        self.message = message
        self.retry_after_seconds = retry_after_seconds


@dataclass
class LatestDateParams:
    universe: str


def parse_query(universe_raw: str | None) -> LatestDateParams:
    universe = (universe_raw or DEFAULT_UNIVERSE).strip() or DEFAULT_UNIVERSE
    if universe not in SUPPORTED_UNIVERSES:
        raise UnsupportedUniverse(universe)
    return LatestDateParams(universe=universe)


def resolve_latest_trading_date(
    universe: str = DEFAULT_UNIVERSE,
    limit: int = DEFAULT_LIMIT,
    scan_limit: int = SCAN_LIMIT,
) -> date:
    """daily-context 200을 보장하는 최신 거래일을 read-only로 산출.

    raise:
        UnsupportedUniverse -> 400
        LatestDateBuilding  -> 503 (직전 완료일도 없고 현재 생성 중일 때만)
        LatestDateNotFound  -> 404
    """
    if universe not in SUPPORTED_UNIVERSES:
        raise UnsupportedUniverse(universe)

    # 후보일 집합 (read-only): EODSignal(USD) distinct date, 내림차순
    dates = list(
        EODSignal.objects.filter(stock__currency="USD")
        .values_list("date", flat=True)
        .distinct()
        .order_by("-date")[:scan_limit]
    )
    if not dates:
        raise LatestDateNotFound("No US trading dates available.")

    building_seen = False
    for d in dates:
        # building이면 skip (M3)
        if PipelineLog.objects.filter(date=d, status="running").exists():
            building_seen = True
            continue

        # dry-check: daily-context 200 게이트와 동일 판정 — 후보 존재 + OHLCV 존재.
        # 기존 함수 재사용. pipeline 실행·DB 쓰기 0.
        candidates = _select_candidate_symbols(d, limit)
        if not candidates:
            continue
        ohlcv = _load_ohlcv_map(candidates, d)
        # _load_ohlcv_map은 모든 심볼을 빈 리스트로 초기화하므로 'in'이 아니라
        # 비어있지 않은 rows 존재를 본다 (daily-context의 `if not rows: continue`와 일치).
        if any(ohlcv.get(sym) for sym in candidates):
            return d

    # 200 가능 날짜를 못 찾음
    if building_seen:
        raise LatestDateBuilding(
            "Latest trading date pipeline is building and no prior "
            "daily-context-available date was found."
        )
    raise LatestDateNotFound("No daily-context-available trading date found.")


def build_latest_trading_date(params: LatestDateParams) -> dict:
    """성공 응답 본문 (200). 신규 생성 없음 — snapshot_id 빈 문자열, freshness unknown."""
    from datetime import datetime, timezone

    trading_date = resolve_latest_trading_date(universe=params.universe)
    date_iso = trading_date.isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": PROVIDER,
        "universe": params.universe,
        "market_timezone": MARKET_TZ,
        "latest_trading_date": date_iso,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "selection_policy": SELECTION_POLICY,
        "daily_context": {
            "available": True,
            "url": (
                f"/api/v1/iron-trading/daily-context"
                f"?date={date_iso}&universe={params.universe}&limit={DEFAULT_LIMIT}"
            ),
            "snapshot_id": "",
            "freshness_status": "unknown",
            "warnings": [],
        },
    }
