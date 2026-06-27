"""
EventGroup 역할별 비대칭 leadership 컴퓨트 (벤치마크 정책 C) — additive 새 경로.

기존 compute_leadership_scores(theme_tags 경로)·attach_leadership·기존 행과 **완전 별개**.
옛 함수/행 변경·삭제 없음. 수식(α/β·capture·trend_quality·LOO)은 leadership_service
원함수를 그대로 호출 — **피어셋(벤치마크) 구성만 역할별로 분기**한다:

  - 코어 종목 → 벤치마크 = 코어 LOO(자기 제외 코어 등가중 평균).
  - 위성 종목 → 벤치마크 = 코어 평균(전체 코어 등가중 평균, 자기 제외 없음 — 위성은 코어 아님).

키 분리(레거시 행 불변 보장):
  - theme = 'eg:{slug}'  (레거시 theme=sector명과 절대 충돌 안 함 → 기존 unique_together 그대로 안전)
  - benchmark_kind ∈ {'core_loo','sat_coremean'}  (레거시=NULL)

윈도/날짜 정합: 옛 경로와 **동일한** _load_price_series·_window_closes·passes_obs_gate를
재사용 → 같은 입력, 피어셋만 다름(공정 diff). 라이브 미배선 — 어떤 소비자도 새 행을 안 읽음.

엣지케이스:
  - 코어 1~2개 → 코어 LOO 자기제외 후 <2 → 코어 종목 α/β·capture NULL(trend_quality는 산출).
  - 코어 0개(kept엔 없어야) → ValueError(HALT 신호).
  - 위성만 있고 코어 정족수 미달 → 위성 벤치마크 None → 위성 α/β·capture NULL.
"""

import logging
from datetime import date

import numpy as np

from apps.chain_sight.models.leadership import StockLeadershipScore
from apps.chain_sight.services import event_group_reader as reader
from apps.chain_sight.services.leadership_compute import (
    _load_price_series,
    _window_closes,
)
from apps.chain_sight.services.leadership_service import (
    MIN_THEME_MEMBERS,
    WINDOWS,
    capture_ratios,
    daily_returns,
    passes_obs_gate,
    theme_alpha_beta,
    trend_quality,
)

logger = logging.getLogger(__name__)

EG_THEME_PREFIX = "eg:"
KIND_CORE = "core_loo"
KIND_SAT = "sat_coremean"
_MAX_WINDOW = max(WINDOWS)


def eg_theme_key(slug: str) -> str:
    """EventGroup slug → 레거시와 분리된 theme 키."""
    return f"{EG_THEME_PREFIX}{slug}"


_EG_LEADERSHIP_FIELDS = (
    "trend_quality", "theme_alpha", "theme_beta",
    "up_capture", "down_capture", "capture_spread",
)


def attach_leadership_eg(
    ranking: list[dict],
    slug: str,
    as_of_date,
    window: int,
) -> list[dict]:
    """
    드릴다운 랭킹에 EventGroup C leadership(theme='eg:{slug}')을 조인(symbol 기준).

    **재계산 없음** — prod에 적재된 benchmark_kind 행을 *읽기*만. 코어(core_loo)·
    위성(sat_coremean) 모두 eg:{slug} 행에 있어 그룹과 정합 표시.
    데이터 미존재 종목은 지표 None(키 노출), is_fallback=False. M1 필드 불변.

    옛 attach_leadership(theme_tags 경로)과 완전 별개 — 그 함수/행 불변.
    """
    eg_theme = eg_theme_key(slug)
    rows = StockLeadershipScore.objects.filter(
        theme=eg_theme, as_of_date=as_of_date, window=window,
        stock_id__in=[r["symbol"] for r in ranking],
    ).values(
        "stock_id", "trend_quality", "theme_alpha", "theme_beta",
        "up_capture", "down_capture", "capture_spread", "is_fallback",
    )
    by_symbol = {r["stock_id"]: r for r in rows}

    for item in ranking:
        lead = by_symbol.get(item["symbol"])
        if lead:
            for f in _EG_LEADERSHIP_FIELDS:
                item[f] = lead[f]
            item["is_fallback"] = lead["is_fallback"]
        else:
            for f in _EG_LEADERSHIP_FIELDS:
                item[f] = None
            item["is_fallback"] = False
    return ranking


def _member_returns(symbols, price_by_symbol, window) -> dict[str, list[float]]:
    """게이트 통과 멤버의 {symbol: 일수익률}. 옛 경로 member_returns 산정과 동일."""
    out: dict[str, list[float]] = {}
    for sym in symbols:
        series = price_by_symbol.get(sym)
        if not series:
            continue
        closes = _window_closes(series, window)
        if closes is None or len(closes) < 2:
            continue
        rets = daily_returns(closes)
        if not passes_obs_gate(len(rets), window):
            continue
        out[sym] = rets
    return out


def _core_loo_benchmark(core_rets, target_sym, obs_count) -> list[float] | None:
    """코어 자기제외 등가중 평균(길이 obs_count 일치 멤버만). 자기제외 후 <2면 None."""
    others = [
        r for s, r in core_rets.items()
        if s != target_sym and len(r) == obs_count
    ]
    if len(others) < MIN_THEME_MEMBERS - 1:  # 자기 제외 후 >= 2 필요(옛 LOO 게이트와 동일)
        return None
    return np.asarray(others, dtype=float).mean(axis=0).tolist()


def _core_mean_benchmark(core_rets, obs_count) -> list[float] | None:
    """전체 코어 등가중 평균(길이 obs_count 일치 멤버만). 코어 정족수<3이면 None."""
    members = [r for r in core_rets.values() if len(r) == obs_count]
    if len(members) < MIN_THEME_MEMBERS:
        return None
    return np.asarray(members, dtype=float).mean(axis=0).tolist()


def _build_row(sym, theme_key, window, as_of_date, closes, rets, gate_ok, benchmark, kind):
    """단일 (종목, 윈도우) 행 생성. 수식은 원함수 호출, 게이트/벤치마크 미달은 NULL."""
    tq_val = None
    if gate_ok:
        tq = trend_quality(closes)
        if tq is not None:
            tq_val = tq["trend_quality"]

    alpha = beta = up = down = spread = None
    if gate_ok and benchmark is not None:
        ab = theme_alpha_beta(rets, benchmark)
        if ab is not None:
            alpha = ab["theme_alpha"]
            beta = ab["theme_beta"]
        cap = capture_ratios(rets, benchmark)
        if cap is not None:
            up = cap["up_capture"]
            down = cap["down_capture"]
            spread = cap["capture_spread"]

    is_fallback = (window == _MAX_WINDOW) and not gate_ok
    return StockLeadershipScore(
        stock_id=sym,
        theme=theme_key,
        window=window,
        as_of_date=as_of_date,
        trend_quality=tq_val,
        theme_alpha=alpha,
        theme_beta=beta,
        up_capture=up,
        down_capture=down,
        capture_spread=spread,
        obs_count=len(rets),
        is_fallback=is_fallback,
        benchmark_kind=kind,
    )


def compute_eventgroup_leadership_scores(as_of_date: date) -> int:
    """
    kept EventGroup의 core/satellite 멤버에 대해 C 벤치마크로 leadership 재컴퓨트 후 upsert.

    옛 theme_tags 경로/행 무영향(theme='eg:{slug}' 키 분리). 라이브 미배선.

    Returns:
        upsert된 행 수.

    Raises:
        ValueError: kept 그룹에 코어 0개(HALT 신호).
    """
    price_by_symbol = _load_price_series(as_of_date)
    if not price_by_symbol:
        logger.warning("compute_eventgroup_leadership: DailyPrice 없음 (as_of=%s)", as_of_date)
        return 0

    groups = reader.get_kept_event_groups()  # kept만 + role 포함(게이팅 중앙집중)
    objs: list[StockLeadershipScore] = []

    for g in groups:
        slug = g["slug"]
        theme_key = eg_theme_key(slug)
        core_syms = [m["symbol"] for m in g["members"] if m["role"] == "core"]
        sat_syms = [m["symbol"] for m in g["members"] if m["role"] == "satellite"]

        if not core_syms:
            raise ValueError(
                f"EventGroup {slug}: 코어 0개 — kept 그룹에 코어가 없음(HALT 신호)"
            )

        for window in WINDOWS:
            core_rets = _member_returns(core_syms, price_by_symbol, window)

            # ── 코어 종목: 벤치마크 = 코어 LOO ──
            for sym in core_syms:
                series = price_by_symbol.get(sym)
                if not series:
                    continue
                closes = _window_closes(series, window)
                if closes is None or len(closes) < 2:
                    continue
                rets = daily_returns(closes)
                gate_ok = passes_obs_gate(len(rets), window)
                bench = (
                    _core_loo_benchmark(core_rets, sym, len(rets))
                    if (gate_ok and sym in core_rets) else None
                )
                objs.append(_build_row(
                    sym, theme_key, window, as_of_date,
                    closes, rets, gate_ok, bench, KIND_CORE,
                ))

            # ── 위성 종목: 벤치마크 = 전체 코어 평균 ──
            for sym in sat_syms:
                series = price_by_symbol.get(sym)
                if not series:
                    continue
                closes = _window_closes(series, window)
                if closes is None or len(closes) < 2:
                    continue
                rets = daily_returns(closes)
                gate_ok = passes_obs_gate(len(rets), window)
                bench = (
                    _core_mean_benchmark(core_rets, len(rets))
                    if gate_ok else None
                )
                objs.append(_build_row(
                    sym, theme_key, window, as_of_date,
                    closes, rets, gate_ok, bench, KIND_SAT,
                ))

    if not objs:
        logger.warning("compute_eventgroup_leadership: 산출 행 0 (as_of=%s)", as_of_date)
        return 0

    StockLeadershipScore.objects.bulk_create(
        objs,
        update_conflicts=True,
        unique_fields=["stock", "theme", "window", "as_of_date"],
        update_fields=[
            "trend_quality", "theme_alpha", "theme_beta",
            "up_capture", "down_capture", "capture_spread",
            "obs_count", "is_fallback", "benchmark_kind",
        ],
    )
    logger.info(
        "compute_eventgroup_leadership: as_of=%s, rows=%d, groups=%d",
        as_of_date, len(objs), len(groups),
    )
    return len(objs)
