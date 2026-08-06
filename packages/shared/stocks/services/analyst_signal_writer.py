"""SFI-I1 Part 2 — AnalystSignalSnapshot writer (D-I1-4 / D-I1-2).

가격·의견 forward 신호 4종(price target 컨센서스·grades 분포·grades 추세·ratings)을
FMP 래퍼로 수집 → AnalystSignalSnapshot append(시계열 정본) + Stock.analyst_* 최신 미러.

★ estimates 무접촉(chain_sight.EstimateSnapshot 정본, 이중 수집 금지).
★ forward_pe 미러 제외(FORWARD-PE-DEFER — estimates 의존).
"""
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

from packages.shared.stocks.models import AnalystSignalSnapshot, DailyPrice, Stock

logger = logging.getLogger(__name__)


def _spot_price(symbol: str) -> Optional[Decimal]:
    """발화 시점 spot = 최신 DailyPrice.close (SFI-I3, D-I3-1b).

    FMP 페이로드에 spot성 값이 없어(STEP0 #2) DB 로컬 최신 종가로 경량 조회한다.
    부재 시 None — 발화 자체를 막지 않는다(append 비차단). insert 시 1회 동봉만.
    """
    return (
        DailyPrice.objects.filter(stock__symbol=symbol.upper())
        .order_by("-date")
        .values_list("close_price", flat=True)
        .first()
    )


def _dec(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fetch_signals(client, symbol: str) -> dict:
    """4 엔드포인트 조회 → 정규화 payload. 각 신호는 부재 시 None/[]."""
    ratings = client.get_ratings_snapshot(symbol) or {}
    pt = client.get_price_target_consensus(symbol) or {}
    grades = client.get_grades_consensus(symbol) or {}
    hist = client.get_grades_historical(symbol) or []
    return {"ratings": ratings, "pt": pt, "grades": grades, "hist": hist}


def _is_empty(sig: dict) -> bool:
    return not (sig["ratings"] or sig["pt"] or sig["grades"] or sig["hist"])


def _mirror_stock(symbol: str, snap: AnalystSignalSnapshot) -> bool:
    """Stock 행 존재 시에만 유령필드 미러(analyst_target_price + rating*5). forward_pe 제외."""
    updated = Stock.objects.filter(symbol=symbol.upper()).update(
        analyst_target_price=snap.target_consensus,
        analyst_rating_strong_buy=snap.grade_strong_buy,
        analyst_rating_buy=snap.grade_buy,
        analyst_rating_hold=snap.grade_hold,
        analyst_rating_sell=snap.grade_sell,
        analyst_rating_strong_sell=snap.grade_strong_sell,
    )
    return updated > 0


def capture_symbol(client, symbol: str, mirror: bool = True) -> dict:
    """한 종목 forward 신호를 AnalystSignalSnapshot에 append(+미러).

    반환 = {symbol, created(0|1), mirrored(bool)}. 신호 전무 시 created=0(행 생성 안 함).
    """
    symbol = symbol.upper()
    sig = _fetch_signals(client, symbol)
    if _is_empty(sig):
        return {"symbol": symbol, "created": 0, "mirrored": False}

    pt, grades, ratings = sig["pt"], sig["grades"], sig["ratings"]
    snap = AnalystSignalSnapshot.objects.create(
        symbol=symbol,
        source="fmp",
        target_consensus=_dec(pt.get("targetConsensus")),
        target_high=_dec(pt.get("targetHigh")),
        target_low=_dec(pt.get("targetLow")),
        target_median=_dec(pt.get("targetMedian")),
        grade_strong_buy=_int(grades.get("strongBuy")),
        grade_buy=_int(grades.get("buy")),
        grade_hold=_int(grades.get("hold")),
        grade_sell=_int(grades.get("sell")),
        grade_strong_sell=_int(grades.get("strongSell")),
        grade_consensus=grades.get("consensus") or "",
        grades_historical=sig["hist"] or [],
        rating=ratings.get("rating") or "",
        overall_score=_int(ratings.get("overallScore")),
        spot_at_capture=_spot_price(symbol),
    )
    mirrored = _mirror_stock(symbol, snap) if mirror else False
    return {"symbol": symbol, "created": 1, "mirrored": mirrored}


def capture_symbols(client, symbols: Iterable[str]) -> dict:
    """유니버스 배치 수집 — 심볼별 격리(1종목 데이터 실패가 전체 중단 안 함).

    카운터 소진(FMPRateLimitError)은 **터미널** → 즉시 중단(더 두드리지 않음), halted 플래그.
    반환 = {captured, failed, skipped, halted_rate_limit, errors:{symbol:msg}}.
    """
    from packages.shared.api_request.providers.fmp.client import FMPRateLimitError

    captured = failed = skipped = 0
    halted = False
    errors: dict[str, str] = {}
    for raw in symbols:
        symbol = (raw or "").upper()
        if not symbol:
            continue
        try:
            res = capture_symbol(client, symbol)
            if res["created"]:
                captured += 1
            else:
                skipped += 1
        except FMPRateLimitError as e:
            # 일일/분 한도 소진 = 터미널. 남은 심볼 중단(재시도 무의미).
            halted = True
            errors[symbol] = f"rate-limit halt: {e}"
            logger.warning("AnalystSignal 카운터 소진 — %s에서 중단", symbol)
            break
        except Exception as e:  # noqa: BLE001 — 심볼별 격리(전체 중단 금지)
            failed += 1
            errors[symbol] = str(e)
            logger.warning("AnalystSignal 수집 실패 %s: %s", symbol, e)
    return {
        "captured": captured,
        "failed": failed,
        "skipped": skipped,
        "halted_rate_limit": halted,
        "errors": errors,
    }
