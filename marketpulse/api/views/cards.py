"""Market Pulse v2 — Card Detail endpoints (PR-J)."""
from __future__ import annotations

import time
from typing import Any

from django.core.cache import cache
from django.utils import timezone as django_timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marketpulse.api import cache as cache_keys
from marketpulse.models.briefing import BriefingLog
from marketpulse.models.regime import RegimeSnapshot
from marketpulse.models.snapshot import (
    BreadthSnapshot,
    ConcentrationSnapshot,
    SectorFlowSnapshot,
)
from marketpulse.throttles import (
    MarketPulseHourThrottle,
    MarketPulseLLMThrottle,
    MarketPulseUserThrottle,
)

VALID_CARDS = {'regime', 'breadth', 'sector', 'flow', 'brief'}


def _envelope(payload: dict, started: float, *, cache_state: str) -> dict:
    return {
        '_meta': {
            'generated_at': django_timezone.now().isoformat(),
            'latency_ms': int((time.time() - started) * 1000),
            'cache': cache_state,
        },
        'data': payload,
    }


@extend_schema(
    summary='Card detail (lazy load)',
    description='Layer 1 lazy load. brief는 30분 캐시, 그 외는 5분.',
    tags=['Market Pulse v2'],
    parameters=[
        OpenApiParameter(
            name='card_id',
            type=str,
            location=OpenApiParameter.PATH,
            enum=['regime', 'breadth', 'sector', 'flow', 'brief'],
        ),
    ],
    responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
)
class CardDetailView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [MarketPulseUserThrottle, MarketPulseHourThrottle]

    def get_throttles(self):
        card_id = (self.kwargs.get('card_id') or '').lower()
        throttles = [c() for c in self.throttle_classes]
        if card_id == 'brief':
            throttles.append(MarketPulseLLMThrottle())
        return throttles

    def get(self, request, card_id: str, *args, **kwargs):
        started = time.time()
        card_id = (card_id or '').lower()
        if card_id not in VALID_CARDS:
            return Response({'error': f'unknown card: {card_id}'}, status=404)

        key = cache_keys.card_detail_key(card_id, brief=(card_id == 'brief'))
        cached = cache.get(key)
        if cached is not None:
            return Response(_envelope(cached, started, cache_state='HIT'))

        payload = {
            'regime': _regime_detail,
            'breadth': _breadth_detail,
            'sector': _sector_detail,
            'flow': _flow_detail,
            'brief': _brief_detail,
        }[card_id]()

        ttl = cache_keys.card_detail_ttl(card_id)
        cache.set(key, payload, timeout=ttl)
        return Response(_envelope(payload, started, cache_state='MISS'))


def _regime_detail():
    today = django_timezone.localdate()
    snap = RegimeSnapshot.objects.filter(date=today).first()
    if snap is None:
        snap = RegimeSnapshot.objects.order_by('-date').first()
    if snap is None:
        return {'available': False}
    return {
        'available': True,
        'date': snap.date.isoformat(),
        'regime': snap.regime,
        'previous_regime': snap.previous_regime,
        'status': snap.status,
        'coverage': float(snap.coverage),
        'inputs': snap.inputs,
        'fired_rules': snap.fired_rules or [],
        'hysteresis_streak': snap.hysteresis_streak,
        'headline': snap.headline,
        'is_finalized': snap.is_finalized,
    }


def _breadth_detail():
    snap = BreadthSnapshot.objects.filter(universe='SPY').order_by('-date').first()
    if snap is None:
        return {'available': False}
    history = list(
        BreadthSnapshot.objects.filter(universe='SPY')
        .order_by('-date')[:30]
        .values('date', 'advance_count', 'decline_count', 'ad_line', 'ad_line_change')
    )
    history.reverse()
    return {
        'available': True,
        'universe': snap.universe,
        'date': snap.date.isoformat(),
        'advance': snap.advance_count,
        'decline': snap.decline_count,
        'unchanged': snap.unchanged_count,
        'total': snap.total_count,
        'new_high_52w': snap.new_high_52w,
        'new_low_52w': snap.new_low_52w,
        'ad_line': snap.ad_line,
        'ad_line_change': snap.ad_line_change,
        'history_30d': [
            {'date': h['date'].isoformat(),
             'advance': h['advance_count'], 'decline': h['decline_count'],
             'ad_line': h['ad_line'], 'ad_line_change': h['ad_line_change']}
            for h in history
        ],
    }


def _sector_detail():
    rows = list(SectorFlowSnapshot.objects.order_by('-date'))
    if not rows:
        return {'available': False}
    latest_date = rows[0].date
    latest = sorted([r for r in rows if r.date == latest_date], key=lambda r: r.rank_in_universe)
    return {
        'available': True,
        'date': latest_date.isoformat(),
        'sectors': [
            {
                'symbol': r.market_index_id,
                'rel_strength': float(r.rel_strength),
                'momentum_1d': float(r.momentum_1d),
                'momentum_5d': float(r.momentum_5d),
                'momentum_20d': float(r.momentum_20d),
                'flow_proxy': float(r.flow_proxy),
                'rank': r.rank_in_universe,
            }
            for r in latest
        ],
        'cross_dispersion': float(latest[0].cross_dispersion),
        'rotation_index': float(latest[0].rotation_index),
    }


def _flow_detail():
    snap = ConcentrationSnapshot.objects.order_by('-date').first()
    if snap is None:
        return {'available': False}
    history = list(
        ConcentrationSnapshot.objects.order_by('-date')[:30]
        .values('date', 'top5_weight', 'top10_weight', 'hhi')
    )
    history.reverse()
    return {
        'available': True,
        'date': snap.date.isoformat(),
        'universe': snap.universe,
        'top5_weight': float(snap.top5_weight),
        'top10_weight': float(snap.top10_weight),
        'hhi': float(snap.hhi),
        'top_holdings': snap.top_holdings or [],
        'history_30d': [
            {'date': h['date'].isoformat(),
             'top5': float(h['top5_weight']),
             'top10': float(h['top10_weight']),
             'hhi': float(h['hhi'])}
            for h in history
        ],
    }


def _brief_detail():
    log = BriefingLog.objects.order_by('-date').first()
    if log is None:
        return {'available': False}
    return {
        'available': True,
        'date': log.date.isoformat(),
        'model_version': log.model_version,
        'status': log.status,
        'headline': log.headline,
        'body': log.body,
        'body_sections': log.body_sections or [],
        'prompt_inputs': log.prompt_inputs,
        'tokens': {
            'prompt': log.prompt_tokens,
            'completion': log.completion_tokens,
            'latency_ms': log.latency_ms,
        },
    }
