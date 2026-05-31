"""iron-trading daily-context 응답 빌더 (read-only).

read-only 원칙: 어떤 모델도 수정하지 않는다.
은닉 원칙: stock_vis 내부 ORM 객체를 그대로 반환하지 않고 dict로 매핑한다.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable

from django.db.models import Q

from packages.shared.stocks.models import (
    DailyPrice,
    EODDashboardSnapshot,
    EODSignal,
    PipelineLog,
    Stock,
)

from .market_pulse import build_market_pulse
from .signals import (
    OHLCVRow,
    assign_relative_strength_rank,
    compute_candidate_signals,
)

SCHEMA_VERSION = "1.0"
PROVIDER = "stock_vis"
MARKET_TZ = "America/New_York"
DEFAULT_UNIVERSE = "us_core"
DEFAULT_LIMIT = 30
MAX_LIMIT = 200
OHLCV_LOOKBACK_DAYS = 60
SNAPSHOT_MAX_AGE_MINUTES = 1440


class BadRequest(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class SnapshotBuilding(Exception):
    def __init__(self, message: str, retry_after_seconds: int = 300):
        super().__init__(message)
        self.message = message
        self.retry_after_seconds = retry_after_seconds


class SnapshotNotFound(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class QueryParams:
    trading_date: date
    universe: str
    limit: int


def parse_query(
    date_raw: str | None, universe_raw: str | None, limit_raw: str | None
) -> QueryParams:
    if not date_raw:
        raise BadRequest(
            "missing_date", "date query parameter is required (YYYY-MM-DD)."
        )
    try:
        trading_date = date.fromisoformat(date_raw)
    except ValueError:
        raise BadRequest("invalid_date", f"date must be YYYY-MM-DD, got {date_raw!r}.")

    universe = (universe_raw or DEFAULT_UNIVERSE).strip()
    if not universe:
        universe = DEFAULT_UNIVERSE
    # 1차 구현: us_core 외 미지원
    if universe != DEFAULT_UNIVERSE:
        raise BadRequest(
            "unsupported_universe",
            f"universe {universe!r} not supported. Only {DEFAULT_UNIVERSE!r} is available.",
        )

    limit = DEFAULT_LIMIT
    if limit_raw is not None:
        try:
            limit = int(limit_raw)
        except ValueError:
            raise BadRequest(
                "invalid_limit", f"limit must be an integer, got {limit_raw!r}."
            )
        if limit <= 0 or limit > MAX_LIMIT:
            raise BadRequest(
                "invalid_limit",
                f"limit must be 1..{MAX_LIMIT}, got {limit}.",
            )

    return QueryParams(trading_date=trading_date, universe=universe, limit=limit)


def _check_pipeline_state(trading_date: date) -> None:
    running = (
        PipelineLog.objects.filter(
            date=trading_date,
            status="running",
        )
        .order_by("-started_at")
        .first()
    )
    if running is not None:
        raise SnapshotBuilding(
            f"{trading_date.isoformat()} daily context snapshot is still building.",
        )


def _select_candidate_symbols(trading_date: date, limit: int) -> list[str]:
    """우선순위:
    1) trading_date의 EODSignal 중 미국 주식 (composite_score 내림차순) top-N
    2) (없으면) trading_date의 DailyPrice 중 미국 주식, 거래량 상위 top-N
    """
    eod_rows = (
        EODSignal.objects.filter(
            date=trading_date,
            stock__currency="USD",
        )
        .order_by("-composite_score", "-signal_count")
        .values_list("stock_id", flat=True)[:limit]
    )
    symbols = list(eod_rows)
    if symbols:
        return symbols

    price_rows = (
        DailyPrice.objects.filter(
            date=trading_date,
            stock__currency="USD",
        )
        .order_by("-volume")
        .values_list("stock_id", flat=True)[:limit]
    )
    return list(price_rows)


def _load_ohlcv_map(
    symbols: list[str], trading_date: date
) -> dict[str, list[OHLCVRow]]:
    if not symbols:
        return {}
    start = trading_date - timedelta(
        days=OHLCV_LOOKBACK_DAYS * 2
    )  # buffer for weekends/holidays
    qs = (
        DailyPrice.objects.filter(
            stock_id__in=symbols,
            date__lte=trading_date,
            date__gte=start,
        )
        .order_by("stock_id", "date")
        .values(
            "stock_id",
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        )
    )
    by_symbol: dict[str, list[OHLCVRow]] = {sym: [] for sym in symbols}
    for row in qs:
        by_symbol[row["stock_id"]].append(
            OHLCVRow(
                date=row["date"].isoformat(),
                open=row["open_price"],
                high=row["high_price"],
                low=row["low_price"],
                close=row["close_price"],
                volume=row["volume"],
            )
        )
    # 가장 최근 60 거래일만 유지
    for sym in by_symbol:
        if len(by_symbol[sym]) > OHLCV_LOOKBACK_DAYS:
            by_symbol[sym] = by_symbol[sym][-OHLCV_LOOKBACK_DAYS:]
    return by_symbol


def _load_eod_signal_map(
    symbols: list[str], trading_date: date
) -> dict[str, EODSignal]:
    if not symbols:
        return {}
    qs = EODSignal.objects.filter(stock_id__in=symbols, date=trading_date)
    return {row.stock_id: row for row in qs}


def _load_stock_map(symbols: list[str]) -> dict[str, Stock]:
    if not symbols:
        return {}
    return {s.symbol: s for s in Stock.objects.filter(symbol__in=symbols)}


def _load_narrative_tags(symbols: list[str]) -> dict[str, list[str]]:
    """Chain Sight narrative_tag.theme_tags 매핑. 앱 미존재/에러여도 안전하게 빈 dict."""
    if not symbols:
        return {}
    try:
        from apps.chain_sight.models.narrative_tag import CompanyNarrativeTag
    except Exception:
        return {}
    try:
        rows = CompanyNarrativeTag.objects.filter(symbol_id__in=symbols).values(
            "symbol_id",
            "theme_tags",
            "primary_narrative",
        )
    except Exception:
        return {}
    out: dict[str, list[str]] = {}
    for r in rows:
        tags = list(r.get("theme_tags") or [])
        if r.get("primary_narrative"):
            tags = [r["primary_narrative"], *tags]
        # 중복 제거 + 빈 문자열 제거
        seen = set()
        cleaned = []
        for t in tags:
            if not t or t in seen:
                continue
            seen.add(t)
            cleaned.append(t)
        out[r["symbol_id"]] = cleaned
    return out


def _scale_composite(score: float | None) -> str:
    if score is None:
        return "0.5000"
    # EODSignal.composite_score: -1.0 ~ +1.0 → 0.0~1.0로 정규화
    scaled = max(-1.0, min(1.0, float(score)))
    normalized = (scaled + 1.0) / 2.0
    return f"{Decimal(str(normalized)):.4f}"


def _build_thesis(signal_count: int, bullish: int, bearish: int, sector: str) -> str:
    if signal_count == 0:
        return f"{sector or '해당 섹터'} 후보. 활성 시그널이 없어 가격/거래량 지표 위주 평가."
    if bullish >= bearish:
        return (
            f"{sector or '해당 섹터'}: 상승 시그널 {bullish}개 / 하락 시그널 {bearish}개. "
            "추세·모멘텀·거래량 동반 평가 권장."
        )
    return (
        f"{sector or '해당 섹터'}: 하락 시그널 우위 ({bearish} vs {bullish}). "
        "신규 진입보다 리스크 모니터링 권장."
    )


def _risk_flags(
    stock: Stock | None, signal_row: EODSignal | None, trading_date: date
) -> list[str]:
    flags: list[str] = []
    if stock is not None:
        # 최근 분기 발표 후 약 90일이 지나면 다음 발표가 가까운 것으로 가정
        if stock.latest_quarter:
            days_since = (trading_date - stock.latest_quarter).days
            if 76 <= days_since <= 90 or days_since > 90:
                flags.append("earnings_within_14d")

    if signal_row is not None:
        if (
            signal_row.bearish_count > signal_row.bullish_count
            and signal_row.signal_count > 0
        ):
            flags.append("bearish_signal_majority")
        if signal_row.dollar_volume is not None and signal_row.dollar_volume < Decimal(
            "1000000"
        ):
            flags.append("low_liquidity")
    return flags


def _build_candidate(
    symbol: str,
    stock: Stock | None,
    signal_row: EODSignal | None,
    rows: list[OHLCVRow],
    tags: list[str],
    trading_date: date,
) -> dict:
    last_price = None
    if rows:
        last_price = f"{rows[-1].close:.4f}"
    elif signal_row is not None:
        last_price = f"{signal_row.close_price:.4f}"
    elif stock is not None and stock.real_time_price:
        last_price = f"{stock.real_time_price:.4f}"

    composite = signal_row.composite_score if signal_row else None
    score = _scale_composite(composite)
    signal_count = signal_row.signal_count if signal_row else 0
    bullish = signal_row.bullish_count if signal_row else 0
    bearish = signal_row.bearish_count if signal_row else 0
    sector = (
        signal_row.sector
        if signal_row and signal_row.sector
        else (stock.sector if stock else "")
    ) or ""

    sigs = compute_candidate_signals(rows)
    risk_flags = _risk_flags(stock, signal_row, trading_date)

    # tags: chainsight narrative 우선, 없으면 sector/industry로 fallback
    final_tags = list(tags)
    if not final_tags:
        if stock and stock.sector:
            final_tags.append(stock.sector)
        if stock and stock.industry and stock.industry not in final_tags:
            final_tags.append(stock.industry)

    return {
        "symbol": symbol,
        "company_name": stock.stock_name if stock else None,
        "exchange": stock.exchange if stock else None,
        "currency": "USD",
        "last_price": last_price,
        "score": score,
        "rank": None,  # caller assigns
        "thesis": _build_thesis(signal_count, bullish, bearish, sector),
        "signals": sigs,
        "risk_flags": risk_flags,
        "tags": final_tags,
        "ohlcv": [
            {
                "date": r.date,
                "open": f"{r.open:.4f}",
                "high": f"{r.high:.4f}",
                "low": f"{r.low:.4f}",
                "close": f"{r.close:.4f}",
                "volume": str(r.volume),
            }
            for r in rows
        ],
    }


def _build_chain_sight(symbols: list[str], tags_map: dict[str, list[str]]) -> dict:
    if not symbols or not tags_map:
        return {"summary": "", "themes": []}

    # theme → symbols 역인덱스
    theme_to_syms: dict[str, list[str]] = {}
    for sym in symbols:
        for t in tags_map.get(sym, []):
            theme_to_syms.setdefault(t, []).append(sym)
    if not theme_to_syms:
        return {"summary": "", "themes": []}

    # 상위 5개 테마 (구성 종목 수 내림차순)
    ranked = sorted(theme_to_syms.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:5]
    themes = [
        {
            "name": name,
            "tone": "neutral",
            "symbols": syms[:10],
            "summary": f"{name} 테마에 {len(syms)}개 후보가 포함되어 있습니다.",
        }
        for name, syms in ranked
    ]
    return {
        "summary": (
            f"상위 테마: " + ", ".join(t["name"] for t in themes) if themes else ""
        ),
        "themes": themes,
    }


def _build_freshness(
    trading_date: date, dashboard_snapshot: EODDashboardSnapshot | None
) -> dict:
    warnings: list[str] = []
    if dashboard_snapshot is None:
        # baked snapshot이 아직 없어도 raw EODSignal 기반으로 응답 가능 — partial로 표시
        as_of = datetime.combine(trading_date, datetime.min.time()).replace(
            hour=20,
            minute=5,
            tzinfo=timezone(timedelta(hours=-4)),
        )
        warnings.append("eod_dashboard_baked_snapshot_unavailable")
        status = "partial"
    else:
        as_of = dashboard_snapshot.generated_at
        status = "fresh"
        # 신선도 — generated_at이 오래되면 stale
        age_min = (
            (datetime.now(timezone.utc) - as_of).total_seconds() / 60.0
            if as_of.tzinfo
            else None
        )
        if age_min is not None and age_min > SNAPSHOT_MAX_AGE_MINUTES:
            status = "stale"
            warnings.append("snapshot_older_than_24h")

    return {
        "status": status,
        "as_of": as_of.isoformat(),
        "max_age_minutes": SNAPSHOT_MAX_AGE_MINUTES,
        "warnings": warnings,
    }


def _snapshot_id(
    trading_date: date,
    universe: str,
    candidate_count: int,
    dashboard: EODDashboardSnapshot | None,
) -> str:
    """결정적 id. 같은 (date, universe, candidate_set, baked-version)이면 같은 id."""
    parts = [
        PROVIDER,
        universe,
        trading_date.isoformat(),
        str(candidate_count),
    ]
    if dashboard is not None:
        parts.append(dashboard.generated_at.isoformat())
        parts.append(str(dashboard.total_signals))
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"stockvis-us-{trading_date.isoformat()}-{digest}"


def build_daily_context(params: QueryParams) -> dict:
    trading_date = params.trading_date

    _check_pipeline_state(trading_date)

    symbols = _select_candidate_symbols(trading_date, params.limit)

    # 데이터 자체가 없으면 404
    if not symbols:
        # 추가 안전망: 해당일 DailyPrice 자체가 없으면 404
        any_price = DailyPrice.objects.filter(date=trading_date).exists()
        any_signal = EODSignal.objects.filter(date=trading_date).exists()
        if not any_price and not any_signal:
            raise SnapshotNotFound(
                f"No data for trading_date {trading_date.isoformat()}.",
            )
        # 미국 주식 후보가 0개 — 빈 candidates로 응답하되 warning에 기록
        # (그래도 시장 단위 데이터는 줄 수 있음)

    ohlcv_map = _load_ohlcv_map(symbols, trading_date)
    eod_map = _load_eod_signal_map(symbols, trading_date)
    stock_map = _load_stock_map(symbols)
    tags_map = _load_narrative_tags(symbols)

    candidates: list[dict] = []
    for sym in symbols:
        rows = ohlcv_map.get(sym, [])
        if not rows:
            # OHLCV가 아예 없는 후보는 제외 (계약: ohlcv 필수)
            continue
        candidate = _build_candidate(
            sym,
            stock_map.get(sym),
            eod_map.get(sym),
            rows,
            tags_map.get(sym, []),
            trading_date,
        )
        candidates.append(candidate)

    # rank by score (높을수록 1번)
    candidates.sort(key=lambda c: Decimal(c["score"]), reverse=True)
    for idx, c in enumerate(candidates, start=1):
        c["rank"] = idx
    assign_relative_strength_rank(candidates)

    # market_pulse
    try:
        from apps.market_pulse.models.regime import RegimeSnapshot

        regime = (
            RegimeSnapshot.objects.filter(date__lte=trading_date)
            .order_by("-date")
            .first()
        )
    except Exception:
        regime = None
    market_pulse = build_market_pulse(regime, trading_date)

    # chain_sight
    chain_sight = _build_chain_sight(symbols, tags_map)

    # freshness
    dashboard = EODDashboardSnapshot.objects.filter(date=trading_date).first()
    freshness = _build_freshness(trading_date, dashboard)

    # 후보가 결국 비었으면 503 (결정보드 입력 미성립)
    if not candidates:
        raise SnapshotBuilding(
            f"{trading_date.isoformat()} candidates not yet available "
            "(US OHLCV missing for selected universe).",
        )

    snapshot_id = _snapshot_id(
        trading_date, params.universe, len(candidates), dashboard
    )

    captured_at = (
        dashboard.generated_at if dashboard is not None else datetime.now(timezone.utc)
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "provider": PROVIDER,
        "snapshot_id": snapshot_id,
        "trading_date": trading_date.isoformat(),
        "captured_at": captured_at.isoformat(),
        "market_timezone": MARKET_TZ,
        "universe": params.universe,
        "freshness": freshness,
        "market_pulse": market_pulse,
        "chain_sight": chain_sight,
        "candidates": candidates,
    }


def error_body(code: str, message: str, retry_after_seconds: int | None = None) -> dict:
    body = {
        "schema_version": SCHEMA_VERSION,
        "provider": PROVIDER,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if retry_after_seconds is not None:
        body["error"]["retry_after_seconds"] = retry_after_seconds
    return body
