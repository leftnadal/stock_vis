"""
주도주 지표 영속 서비스 (CS-M2 Slice 3).

compute_leadership_scores(as_of_date):
  백필된 DailyPrice 로드 → 테마 멤버십(CompanyChainProfile.theme_tags) →
  테마별 LOO 등가중 일수익률 → Slice1 코어 호출 → bulk upsert(update_conflicts).

M1 attention_service 패턴 따름. StockAttentionScore는 읽지도 쓰지도 않음(완전 별개).
룩어헤드 금지: as_of_date 이하 데이터만 로드. 윈도우는 as_of_date에서 역방향.
"""

import logging
from collections import defaultdict
from datetime import date, timedelta

import numpy as np

from apps.chain_sight.models import CompanyChainProfile, StockLeadershipScore
from apps.chain_sight.services.leadership_service import (
    MIN_THEME_MEMBERS,
    WINDOWS,
    capture_ratios,
    daily_returns,
    passes_obs_gate,
    theme_alpha_beta,
    trend_quality,
)
from packages.shared.stocks.models import DailyPrice

logger = logging.getLogger(__name__)

# 최장 윈도우(120) + 여유. 영업일 120개 확보 위해 달력일 buffer.
_MAX_WINDOW = max(WINDOWS)
_LOAD_BUFFER_DAYS = int(_MAX_WINDOW * 1.7) + 10


def _load_price_series(as_of_date: date) -> dict[str, list[dict]]:
    """
    as_of_date 이하 DailyPrice를 종목별 시간순 list로 로드(룩어헤드 차단).

    Returns:
        {symbol: [{"date","close_price"}...]} (오름차순).
    """
    cutoff = as_of_date - timedelta(days=_LOAD_BUFFER_DAYS)
    rows = (
        DailyPrice.objects.filter(date__gte=cutoff, date__lte=as_of_date)
        .values("stock_id", "date", "close_price")
        .order_by("stock_id", "date")
    )
    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_symbol[r["stock_id"]].append(r)
    return by_symbol


def _theme_membership() -> dict[str, list[str]]:
    """CompanyChainProfile.theme_tags → {theme: [symbol...]}."""
    profiles = CompanyChainProfile.objects.values("symbol_id", "theme_tags")
    members: dict[str, list[str]] = defaultdict(list)
    for p in profiles:
        for tag in (p["theme_tags"] or []):
            if tag:
                members[tag].append(p["symbol_id"])
    return members


def _window_closes(series: list[dict], window: int) -> list[float] | None:
    """
    시간순 series의 마지막 window+1개 종가 반환(수익률 window개 확보용).

    유효 관측(수익률)일이 게이트 미달이면 None.
    """
    if len(series) < 2:
        return None
    # 종가 window+1개(수익률 window개) 필요
    tail = series[-(window + 1):]
    closes = [float(r["close_price"]) for r in tail]
    return closes


def compute_leadership_scores(as_of_date: date) -> int:
    """
    as_of_date 기준 종목×테마×윈도우 4지표 산출 후 bulk upsert.

    Returns:
        upsert된 행 수.
    """
    price_by_symbol = _load_price_series(as_of_date)
    if not price_by_symbol:
        logger.warning("compute_leadership_scores: DailyPrice 없음 (as_of=%s)", as_of_date)
        return 0

    theme_members = _theme_membership()

    # 테마×윈도우별 멤버 일수익률 사전 계산(LOO 평균 재사용).
    # member_returns[theme][window][symbol] = [returns...]
    member_returns: dict[str, dict[int, dict[str, list[float]]]] = defaultdict(
        lambda: {w: {} for w in WINDOWS}
    )
    for theme, members in theme_members.items():
        for window in WINDOWS:
            for sym in members:
                series = price_by_symbol.get(sym)
                if not series:
                    continue
                closes = _window_closes(series, window)
                if closes is None or len(closes) < 2:
                    continue
                rets = daily_returns(closes)
                if not passes_obs_gate(len(rets), window):
                    continue
                member_returns[theme][window][sym] = rets

    objs: list[StockLeadershipScore] = []

    for theme, members in theme_members.items():
        for window in WINDOWS:
            window_member_rets = member_returns[theme][window]
            theme_has_quorum = len(window_member_rets) >= MIN_THEME_MEMBERS

            for sym in members:
                series = price_by_symbol.get(sym)
                if not series:
                    continue

                closes = _window_closes(series, window)
                if closes is None or len(closes) < 2:
                    continue
                rets = daily_returns(closes)
                obs_count = len(rets)

                # 120일 미달 → 120 윈도우 fallback 표시
                # (최장 윈도우인데 게이트 미달이면 fallback)
                is_fallback = (window == _MAX_WINDOW) and not passes_obs_gate(obs_count, window)

                gate_ok = passes_obs_gate(obs_count, window)

                # ── T2: 테마무관, 게이트만 충족하면 산출 ──
                tq_val = None
                if gate_ok:
                    tq = trend_quality(closes)
                    if tq is not None:
                        tq_val = tq["trend_quality"]

                # ── T3 + ②: LOO 테마평균 필요. 테마 정족수 + 자기 수익률 게이트 ──
                alpha = beta = up = down = spread = None
                if gate_ok and theme_has_quorum and sym in window_member_rets:
                    # 자기 제외 등가중 LOO 평균(동일 윈도우 멤버 수익률 사용)
                    others = [
                        r for s, r in window_member_rets.items()
                        if s != sym and len(r) == obs_count
                    ]
                    if len(others) >= MIN_THEME_MEMBERS - 1:
                        loo = np.asarray(others, dtype=float).mean(axis=0).tolist()

                        ab = theme_alpha_beta(rets, loo)
                        if ab is not None:
                            alpha = ab["theme_alpha"]
                            beta = ab["theme_beta"]

                        cap = capture_ratios(rets, loo)
                        if cap is not None:
                            up = cap["up_capture"]
                            down = cap["down_capture"]
                            spread = cap["capture_spread"]

                # 어떤 윈도우든 행 생성(게이트 미달이면 지표 NULL).
                objs.append(
                    StockLeadershipScore(
                        stock_id=sym,
                        theme=theme,
                        window=window,
                        as_of_date=as_of_date,
                        trend_quality=tq_val,
                        theme_alpha=alpha,
                        theme_beta=beta,
                        up_capture=up,
                        down_capture=down,
                        capture_spread=spread,
                        obs_count=obs_count,
                        is_fallback=is_fallback,
                    )
                )

    if not objs:
        logger.warning("compute_leadership_scores: 산출 행 0 (as_of=%s)", as_of_date)
        return 0

    StockLeadershipScore.objects.bulk_create(
        objs,
        update_conflicts=True,
        unique_fields=["stock", "theme", "window", "as_of_date"],
        update_fields=[
            "trend_quality", "theme_alpha", "theme_beta",
            "up_capture", "down_capture", "capture_spread",
            "obs_count", "is_fallback",
        ],
    )

    logger.info(
        "compute_leadership_scores: as_of=%s, rows=%d, themes=%d",
        as_of_date, len(objs), len(theme_members),
    )
    return len(objs)
