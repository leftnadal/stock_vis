"""
관심도 M1 엔진 서비스 (CS-RD2).

score = 0.50 × vol_z_norm + 0.30 × volatility_pct + 0.20 × return_pct) × 100

ADV_FLOOR: 652종 ADV(close×volume 20일평균) p5, 측정일 2026-06-15 (CS-RD2 STEP0).
미만 종목은 is_low_liquidity=True — 점수는 정상 계산·저장 (제외 아님).
"""

import logging
from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Max

from apps.chain_sight.models import CompanyChainProfile, StockAttentionScore
from packages.shared.stocks.models import DailyPrice, Stock

logger = logging.getLogger(__name__)

# ── 상수 ──────────────────────────────────────────────────────────────────────
M1_WEIGHTS = {"volume": 0.50, "volatility": 0.30, "return": 0.20}

# USD. = 652종 ADV(close*volume 20일평균) p5, 측정 2026-06-15 (CS-RD2 STEP0).
# 미만 종목은 is_low_liquidity=True — 제외 아님.
ADV_FLOOR = 45_799_011


# ── 점수 계산 ─────────────────────────────────────────────────────────────────

def compute_attention_scores(target_date: date) -> int:
    """
    target_date 기준 전체 유니버스 M1 점수 계산 후 upsert.

    Returns:
        처리된 종목 수(int).
    """
    # 1. 벌크 로드: 최근 21영업일 DailyPrice (N+1 금지)
    cutoff = target_date - timedelta(days=40)  # 영업일 21개 확보 여유(주말/공휴일)
    rows = list(
        DailyPrice.objects.filter(
            date__gte=cutoff,
            date__lte=target_date,
        ).values("stock_id", "date", "close_price", "high_price", "low_price", "volume")
        .order_by("stock_id", "date")
    )
    if not rows:
        logger.warning("compute_attention_scores: DailyPrice 데이터 없음 (target=%s)", target_date)
        return 0

    # 2. 종목별 그룹핑
    by_symbol: dict[str, list] = defaultdict(list)
    for r in rows:
        by_symbol[r["stock_id"]].append(r)

    # 3. 종목별 당일 지표 계산
    records = []  # (symbol, volume_z, intraday_vol, raw_return, adv)

    for symbol, hist in by_symbol.items():
        # date 오름차순 정렬 (이미 order_by로 정렬됐지만 안전하게)
        hist_sorted = sorted(hist, key=lambda x: x["date"])

        # target_date 당일 행 확인
        today_rows = [r for r in hist_sorted if r["date"] == target_date]
        if not today_rows:
            continue
        today = today_rows[0]

        # 이전 20일 (당일 제외)
        prev_rows = [r for r in hist_sorted if r["date"] < target_date]
        if len(prev_rows) < 20:
            # 20일 미만 → 스킵
            continue

        # 최근 20일만 사용
        window = prev_rows[-20:]

        # volume_z
        vols = [float(r["volume"]) for r in window]
        avg_vol = sum(vols) / len(vols)
        variance = sum((v - avg_vol) ** 2 for v in vols) / len(vols)
        std_vol = variance ** 0.5
        today_vol = float(today["volume"])
        volume_z = (today_vol - avg_vol) / std_vol if std_vol > 0 else 0.0

        # intraday_vol = (high - low) / close
        close = float(today["close_price"])
        high = float(today["high_price"])
        low = float(today["low_price"])
        intraday_vol = (high - low) / close if close > 0 else 0.0

        # raw_return = close / prev_close - 1
        prev_close = float(window[-1]["close_price"])
        raw_return = (close / prev_close - 1) if prev_close > 0 else 0.0

        # ADV = 20일 close×volume 평균
        adv = sum(float(r["close_price"]) * float(r["volume"]) for r in window) / len(window)

        records.append({
            "symbol": symbol,
            "volume_z": volume_z,
            "intraday_vol": intraday_vol,
            "raw_return": raw_return,
            "adv": adv,
        })

    if not records:
        logger.warning("compute_attention_scores: 유효 종목 0개 (target=%s)", target_date)
        return 0

    # 4. Cross-sectional 백분위 (정렬 기반, scipy 불필요)
    n = len(records)

    # volatility_pct: intraday_vol 순위/모수
    sorted_by_vol = sorted(records, key=lambda x: x["intraday_vol"])
    vol_rank = {r["symbol"]: i for i, r in enumerate(sorted_by_vol)}

    # return_pct: |raw_return| 순위/모수
    sorted_by_ret = sorted(records, key=lambda x: abs(x["raw_return"]))
    ret_rank = {r["symbol"]: i for i, r in enumerate(sorted_by_ret)}

    # 5. score 계산 + StockAttentionScore 객체 생성
    objs = []
    for rec in records:
        sym = rec["symbol"]
        vz = rec["volume_z"]
        vz_clipped = max(-3.0, min(3.0, vz))
        vol_norm = (vz_clipped + 3.0) / 6.0  # 0~1

        vol_pct = vol_rank[sym] / (n - 1) if n > 1 else 0.0
        ret_pct = ret_rank[sym] / (n - 1) if n > 1 else 0.0

        raw_score = (
            M1_WEIGHTS["volume"] * vol_norm
            + M1_WEIGHTS["volatility"] * vol_pct
            + M1_WEIGHTS["return"] * ret_pct
        ) * 100
        score = round(raw_score, 1)

        is_low_liq = rec["adv"] < ADV_FLOOR

        objs.append(
            StockAttentionScore(
                symbol_id=sym,
                date=target_date,
                score=score,
                volume_z=round(vz, 6),
                volatility_pct=round(vol_pct, 6),
                return_pct=round(ret_pct, 6),
                raw_return=round(rec["raw_return"], 6),
                is_low_liquidity=is_low_liq,
            )
        )

    # 6. bulk upsert (멱등)
    StockAttentionScore.objects.bulk_create(
        objs,
        update_conflicts=True,
        unique_fields=["symbol", "date"],
        update_fields=["score", "volume_z", "volatility_pct", "return_pct", "raw_return", "is_low_liquidity"],
    )

    logger.info(
        "compute_attention_scores: target=%s, processed=%d, low_liquidity=%d",
        target_date,
        len(objs),
        sum(1 for o in objs if o.is_low_liquidity),
    )
    return len(objs)


# ── 집계·랭킹 ─────────────────────────────────────────────────────────────────

def get_event_board(target_date: date) -> list[dict]:
    """
    이벤트 그룹(theme_tags)별 집계.

    Returns:
        평균 관심도 내림차순 list[dict].
        모든 그룹 포함(멤버=1 포함). 소표본은 member_count로 노출 →
        프론트 저신뢰 표식. (CS-RD3: 그룹 커버리지 완전성 위해 멤버<3 필터 제거.
        상대지표는 quorum(MIN_THEME_MEMBERS=3) 미달 시 None → MetricCell이 "—" 렌더.)
    """
    # target_date 스냅샷 존재 확인
    scores_qs = StockAttentionScore.objects.filter(date=target_date).values(
        "symbol_id", "score", "raw_return", "is_low_liquidity"
    )
    score_map = {r["symbol_id"]: r for r in scores_qs}

    if not score_map:
        return []

    # theme_tags → symbol 매핑
    profiles = CompanyChainProfile.objects.filter(
        symbol_id__in=list(score_map.keys())
    ).values("symbol_id", "theme_tags")

    theme_members: dict[str, list[str]] = defaultdict(list)
    for p in profiles:
        for tag in (p["theme_tags"] or []):
            if tag:
                theme_members[tag].append(p["symbol_id"])

    result = []
    for theme, members in theme_members.items():
        member_scores = [score_map[m] for m in members if m in score_map]
        if not member_scores:
            continue

        avg_score = sum(r["score"] for r in member_scores) / len(member_scores)
        avg_return = sum(r["raw_return"] for r in member_scores) / len(member_scores)
        high_count = sum(1 for r in member_scores if r["score"] >= 70)
        low_count = sum(1 for r in member_scores if r["score"] <= 20)

        result.append({
            "theme": theme,
            "member_count": len(members),
            "avg_return": round(avg_return, 6),
            "avg_score": round(avg_score, 2),
            "high_attention_count": high_count,
            "low_attention_count": low_count,
        })

    result.sort(key=lambda x: x["avg_score"], reverse=True)
    return result


def get_event_ranking(theme: str, target_date: date) -> list[dict]:
    """
    특정 테마 소속 종목을 score 내림차순으로 반환.

    Args:
        theme: CompanyChainProfile.theme_tags 값
        target_date: 조회 날짜

    Returns:
        list[dict] — symbol, name, score, raw_return, volume_z, volatility_pct, is_low_liquidity
    """
    # theme 소속 종목
    profiles = CompanyChainProfile.objects.filter(
        theme_tags__contains=[theme]
    ).values("symbol_id")
    symbols = [p["symbol_id"] for p in profiles]

    if not symbols:
        return []

    # score 조회
    qs = (
        StockAttentionScore.objects.filter(date=target_date, symbol_id__in=symbols)
        .select_related("symbol")
        .order_by("-score")
        .values(
            "symbol_id",
            "symbol__stock_name",
            "score",
            "raw_return",
            "volume_z",
            "volatility_pct",
            "is_low_liquidity",
        )
    )

    return [
        {
            "symbol": r["symbol_id"],
            "name": r["symbol__stock_name"] or "",
            "score": r["score"],
            "raw_return": r["raw_return"],
            "volume_z": r["volume_z"],
            "volatility_pct": r["volatility_pct"],
            "is_low_liquidity": r["is_low_liquidity"],
        }
        for r in qs
    ]
