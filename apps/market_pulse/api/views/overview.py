"""
Overview endpoint (PR-I) — 마켓 펄스 화면 메인 응답.

소속: apps/market_pulse/api/views (app 레이어 DRF Views).
역할: 4 카드(Regime/Breadth/Sector/Concentration) + 일일 브리핑 + i18n 라벨을 한 번에
  응답. serializers/overview.py에서 직렬화. cache.py 키로 캐시.
의존: models의 4 스냅샷·BriefingLog, macro MarketIndex/Price, packages.shared.stocks.
주의: 응답 구조는 contracts/marketpulse_v2_api_contract와 일치 유지.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.core.cache import cache
from django.utils import timezone as django_timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market_pulse.api import cache as cache_keys
from apps.market_pulse.api import status as api_status
from apps.market_pulse.api.serializers.overview import OverviewResponseSerializer
from apps.market_pulse.i18n.labels import resolve_regime_stance
from apps.market_pulse.models.anomaly import AnomalySignalLog
from apps.market_pulse.models.briefing import BriefingLog
from apps.market_pulse.models.news import MarketPulseNews
from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.models.snapshot import (
    BreadthSnapshot,
    ConcentrationSnapshot,
    SectorFlowSnapshot,
)
from apps.market_pulse.throttles import MarketPulseHourThrottle, MarketPulseUserThrottle
from macro.models.indicators import MarketIndex, MarketIndexPrice

logger = logging.getLogger(__name__)


def _ticker_bar() -> list[dict[str, Any]]:
    """PR-A1 (2026-04-29): GICS 11-sector + BENCHMARK로 그룹 확장.
    BENCHMARK 먼저, 그다음 GICS 11종을 symbol 정렬로 노출.
    """
    out = []
    today = django_timezone.localdate()
    sector_groups = (
        "BENCHMARK",
        "FINANCIALS",
        "TECH",
        "HEALTHCARE",
        "CONSUMER_DISC",
        "CONSUMER_STAPLES",
        "ENERGY",
        "INDUSTRIALS",
        "MATERIALS",
        "UTILITIES",
        "REAL_ESTATE",
        "COMMUNICATION",
    )
    for grp in sector_groups:
        for idx in MarketIndex.objects.filter(sector_group=grp).order_by("symbol"):
            rows = list(
                MarketIndexPrice.objects.filter(index=idx, date__lte=today)
                .order_by("-date")
                .values_list("date", "close")[:2]
            )
            last_close = float(rows[0][1]) if rows else None
            change_pct = None
            if len(rows) == 2 and rows[1][1] not in (None, 0):
                change_pct = float((rows[0][1] - rows[1][1]) / rows[1][1] * 100)
            out.append(
                {
                    "symbol": idx.symbol,
                    "last_close": last_close,
                    "change_pct": change_pct,
                    "sector_group": grp,
                }
            )
    return out


def _news_items(limit: int = 6):
    qs = MarketPulseNews.objects.order_by("-published_at")[:limit]
    return [
        {
            "id": n.pk,
            "category": n.category,
            "title": n.title,
            "summary": n.summary,
            "url": n.url,
            "publisher": n.publisher,
            "image_url": n.image_url,
            "published_at": n.published_at,
            "tickers": (n.entities or {}).get("tickers", []),
        }
        for n in qs
    ]


def _anomaly_section(cards) -> dict:
    today = django_timezone.localdate()
    latest = (
        AnomalySignalLog.objects.filter(triggered_at__date=today)
        .order_by("-triggered_at")
        .first()
    )
    if latest is None:
        return {
            "mode": AnomalySignalLog.Mode.CALM,
            "overview": "시장 정상 범위 — 발동 룰 없음.",
            "sector_highlight": "",
            "portfolio_action": "기존 포트폴리오 유지.",
            "fired": [],
        }
    same_cycle = AnomalySignalLog.objects.filter(
        triggered_at=latest.triggered_at,
        mode=latest.mode,
    )
    fired_payload = [
        {
            "rule_id": r.rule_id,
            "headline": r.headline,
            "threshold": r.threshold,
            "actual": float((r.inputs or {}).get("rule_actual") or 0),
            "paired_news_id": r.paired_news_id,
        }
        for r in same_cycle
    ]
    return {
        "mode": latest.mode,
        "overview": latest.body,
        "sector_highlight": "",
        "portfolio_action": "",
        "fired": fired_payload,
    }


def _regime_card():
    today = django_timezone.localdate()
    snap = RegimeSnapshot.objects.filter(date=today).first()
    if snap is None:
        return None
    # MP2-SURFACE: 국면별 판단 카피 부착(additive). status != OK면 fallback + stance_ok=False.
    stance_copy, stance_ok = resolve_regime_stance(snap.regime, snap.status)
    return {
        "regime": snap.regime,
        "status": snap.status,
        "coverage": float(snap.coverage),
        "headline": snap.headline,
        "fired_rules": snap.fired_rules or [],
        "transitioned": bool(
            snap.previous_regime and snap.previous_regime != snap.regime
        ),
        "stance_copy": stance_copy,
        "stance_ok": stance_ok,
    }


def _breadth_card():
    today = django_timezone.localdate()
    snap = BreadthSnapshot.objects.filter(date=today, universe="SPY").first()
    if snap is None:
        snap = BreadthSnapshot.objects.filter(universe="SPY").order_by("-date").first()
        if snap is None:
            return None
    return {
        "universe": snap.universe,
        "advance": snap.advance_count,
        "decline": snap.decline_count,
        "unchanged": snap.unchanged_count,
        "total": snap.total_count,
        "new_high_52w": snap.new_high_52w,
        "new_low_52w": snap.new_low_52w,
        "ad_line": snap.ad_line,
        "ad_line_change": snap.ad_line_change,
    }


def _sector_card():
    today = django_timezone.localdate()
    rows = list(
        SectorFlowSnapshot.objects.filter(date__lte=today).order_by(
            "-date", "rank_in_universe"
        )
    )
    if not rows:
        return None
    latest_date = rows[0].date
    latest_rows = sorted(
        [r for r in rows if r.date == latest_date],
        key=lambda r: r.rank_in_universe,
    )
    leaders = latest_rows[:3]
    laggards = latest_rows[-3:]
    return {
        "leaders": [
            {
                "symbol": r.market_index_id,
                "rel_strength": float(r.rel_strength),
                "rank": r.rank_in_universe,
                "momentum_1d": float(r.momentum_1d),
            }
            for r in leaders
        ],
        "laggards": [
            {
                "symbol": r.market_index_id,
                "rel_strength": float(r.rel_strength),
                "rank": r.rank_in_universe,
                "momentum_1d": float(r.momentum_1d),
            }
            for r in laggards
        ],
        "cross_dispersion": float(latest_rows[0].cross_dispersion),
        "rotation_index": float(latest_rows[0].rotation_index),
    }


def _concentration_card():
    snap = ConcentrationSnapshot.objects.order_by("-date").first()
    if snap is None:
        return None
    return {
        "universe": snap.universe,
        "top5_weight": float(snap.top5_weight),
        "top10_weight": float(snap.top10_weight),
        "hhi": float(snap.hhi),
        "top_holdings": snap.top_holdings or [],
    }


def _brief_card():
    log = BriefingLog.objects.order_by("-date").first()
    if log is None:
        return None
    return {
        "headline": log.headline,
        "content_preview": (log.body or "")[:240],
        "status": log.status,
        "model_version": log.model_version,
    }


def _translations_block():
    """Phase 1.5 S4 — 최신 TranslationLog 행을 translations envelope로.

    행 없음 → None(미생성). 행 있음 → senses(있는 카드 키만) + 메타.
    빈 senses({})와 None은 의도적으로 구분(FE fallback이 둘 다 '밴드만'으로 수렴하되,
    None=미생성 / {}=생성됐으나 0키를 응답에서 식별 가능하게 유지).
    cards 블록은 건드리지 않는다(동렬 추가).
    """
    from apps.market_pulse.models.translation import TranslationLog

    log = TranslationLog.objects.order_by("-date").first()
    if log is None:
        return None
    return {
        "senses": log.senses or {},
        "model_version": log.model_version,
        "generated_at": log.created_at,
        "status": log.status,
    }


def _data_finalized(cards) -> bool:
    today = django_timezone.localdate()
    snaps = [
        RegimeSnapshot.objects.filter(date=today).first(),
        BreadthSnapshot.objects.filter(date=today, universe="SPY").first(),
        ConcentrationSnapshot.objects.filter(date=today).first(),
    ]
    return all(s is not None and s.is_finalized for s in snaps if s)


def _build_payload() -> dict:
    cards = {
        "regime": _regime_card(),
        "breadth": _breadth_card(),
        "sector": _sector_card(),
        "concentration": _concentration_card(),
        "brief": _brief_card(),
    }
    has_required = cards["regime"] is not None and cards["breadth"] is not None
    has_failure = (
        cards["regime"] is not None
        and cards["regime"]["status"] == RegimeSnapshot.Status.FAILED
    )
    indicator_stale = False
    if cards["breadth"] is not None:
        snap = BreadthSnapshot.objects.filter(
            universe="SPY", date=django_timezone.localdate()
        ).first()
        if snap is None:
            indicator_stale = True

    status = api_status.derive_status(
        has_required_snapshots=has_required,
        any_indicator_stale=indicator_stale,
        has_failure=has_failure,
    )
    status_reason = ""
    if status == api_status.APIStatus.INSUFFICIENT_DATA:
        missing = [k for k, v in cards.items() if v is None]
        status_reason = f"missing snapshots: {', '.join(missing)}"

    return {
        "_meta": {
            "status": status,
            "status_reason": status_reason,
            "generated_at": django_timezone.now(),
            "latency_ms": 0,
            "data_finalized": _data_finalized(cards),
            "cache": "",
        },
        "ticker_bar": _ticker_bar(),
        "news": _news_items(),
        "anomaly": _anomaly_section(cards),
        "cards": cards,
        # S4: cards와 동렬 추가(cards 무변경). 미생성 시 null.
        "translations": _translations_block(),
    }


@extend_schema(
    summary="Layer 0 통합 응답",
    description="ticker_bar + news 6 + anomaly + 5 cards summary. 글로벌 5분 캐시.",
    tags=["Market Pulse v2"],
    responses={200: OverviewResponseSerializer},
)
class OverviewView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [MarketPulseUserThrottle, MarketPulseHourThrottle]

    def get(self, request, *args, **kwargs):
        started = time.time()
        key = cache_keys.overview_global_key()
        cached = cache.get(key)
        if cached is not None:
            cached["_meta"]["cache"] = "HIT"
            cached["_meta"]["latency_ms"] = int((time.time() - started) * 1000)
            return Response(cached)

        payload = _build_payload()
        payload["_meta"]["cache"] = "MISS"
        payload["_meta"]["latency_ms"] = int((time.time() - started) * 1000)
        cache.set(key, payload, timeout=cache_keys.GLOBAL_OVERVIEW_TTL_SEC)
        return Response(payload)
