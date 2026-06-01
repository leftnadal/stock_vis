"""
Thesis Control EOD Pipeline — 3 Celery Tasks (수학 모델 v2.3.2, Section 7)

실행 순서:
  [18:00 ET] update_indicator_readings  — 외부 API 데이터 fetch + validation
  [18:15 ET] calculate_scores           — Robust Z + Decay 스코어 계산
  [18:30 ET] create_snapshots_and_alerts — 스냅샷 생성 + 상태 판정 + 알림
"""

import logging
import time
from datetime import date

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# 데이터 소스별 fetch 함수
# ──────────────────────────────────────────────────────────

def _apply_value_postprocess(raw_value, params):
    """
    audit P0 #11 / common-bugs #14 — data_params의 후처리 메타데이터 적용.

    - inverse=True: 1 / value (예: PER = 1 / earningsYieldTTM)
    - scale_multiplier=N: value * N (예: ROE 0.15 → 15.0%)

    raw_value가 None이거나 0(역수 케이스)이면 None 반환.
    """
    if raw_value is None:
        return None
    if params.get('inverse'):
        if raw_value == 0:
            return None
        raw_value = 1.0 / raw_value
    multiplier = params.get('scale_multiplier')
    if multiplier:
        raw_value = raw_value * float(multiplier)
    return raw_value


def _fetch_fmp_ttm_or_growth(client, indicator, symbol, params):
    """
    audit P0 #11 — TTM metric (earningsYieldTTM/returnOnEquityTTM/...) 또는
    /stable/financial-growth (growthRevenue 등) 분기.

    Returns: (raw_value, asof) 또는 (None, None)
    """
    metric = params.get('metric', '')
    endpoint_hint = params.get('endpoint')

    # /stable/financial-growth (예: growthRevenue, growthNetIncome)
    if endpoint_hint == 'financial-growth':
        try:
            data = client._make_request('/stable/financial-growth', {'symbol': symbol})
            if not data or not isinstance(data, list) or not data[0]:
                return None, None
            return data[0].get(metric), timezone.now()
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[{indicator.name}] FMP financial-growth 예외: {exc}")
            return None, None

    # /stable/key-metrics-ttm (TTM suffix가 metric에 있을 때)
    if metric.endswith('TTM'):
        try:
            data = client._make_request('/stable/key-metrics-ttm', {'symbol': symbol})
            if not data or not isinstance(data, list) or not data[0]:
                return None, None
            return data[0].get(metric), timezone.now()
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[{indicator.name}] FMP key-metrics-ttm 예외: {exc}")
            return None, None

    return None, None


def _fetch_fmp_value(indicator):
    """FMP API에서 지표 값 fetch. data_params의 symbol/metric으로 조회.

    audit P0 #11: data_params에 endpoint/inverse/scale_multiplier 메타가 있으면
    /stable/key-metrics-ttm 또는 /stable/financial-growth로 분기 + 후처리 적용.
    """
    from packages.shared.api_request.providers.fmp.client import (
        FMPClient,
        FMPClientError,
        FMPPremiumError,
    )

    params = indicator.data_params or {}
    symbol = params.get('symbol')
    metric = params.get('metric', 'price')  # price, pe, roe, beta 등

    # symbol이 없으면 indicator의 thesis target에서 fallback (펀더멘털 케이스).
    if not symbol:
        thesis = getattr(indicator, 'thesis', None)
        symbol = getattr(thesis, 'target', '') if thesis else ''
        symbol = (symbol or '').upper()
    if not symbol:
        logger.warning(f"[{indicator.name}] FMP: symbol 없음")
        return None, None

    try:
        api_key = getattr(settings, 'FMP_API_KEY', None)
        if not api_key:
            logger.error("[FMP] API 키 미설정")
            return None, None

        client = FMPClient(api_key=api_key)

        # 분기 1: TTM metric 또는 financial-growth endpoint
        if metric.endswith('TTM') or params.get('endpoint') == 'financial-growth':
            raw_value, asof = _fetch_fmp_ttm_or_growth(client, indicator, symbol, params)
            if raw_value is not None:
                raw_value = float(raw_value)
            return _apply_value_postprocess(raw_value, params), asof

        # 분기 2: /stable/quote (기본)
        quote = client.get_quote(symbol)
        if not quote:
            logger.warning(f"[{indicator.name}] FMP: {symbol} 데이터 없음")
            return None, None

        # metric에 따른 값 추출
        value_map = {
            'price': 'price',
            'change_percent': 'changesPercentage',
            'volume': 'volume',
            'pe': 'pe',
            'eps': 'eps',
            'market_cap': 'marketCap',
            'previous_close': 'previousClose',
            'day_high': 'dayHigh',
            'day_low': 'dayLow',
        }
        field = value_map.get(metric, metric)
        raw_value = quote.get(field)
        if raw_value is not None:
            raw_value = float(raw_value)

        return _apply_value_postprocess(raw_value, params), timezone.now()

    except FMPPremiumError:
        logger.warning(f"[{indicator.name}] FMP 프리미엄 심볼: {symbol}")
        return None, None
    except FMPClientError as e:
        logger.error(f"[{indicator.name}] FMP 에러: {e}")
        return None, None
    except Exception as e:
        logger.error(f"[{indicator.name}] FMP 예외: {e}")
        return None, None


def _fetch_fred_value(indicator):
    """FRED API에서 지표 값 fetch. data_params의 series_id로 조회."""
    from macro.services.fred_client import FREDClient

    params = indicator.data_params or {}
    series_id = params.get('series_id')

    if not series_id:
        logger.warning(f"[{indicator.name}] FRED: series_id 없음")
        return None, None

    try:
        fred_key = getattr(settings, 'FRED_API_KEY', None)
        if not fred_key:
            logger.error("[FRED] API 키 미설정")
            return None, None

        client = FREDClient(api_key=fred_key)
        result = client.get_latest_value(series_id)

        if not result or result.get('value') is None:
            logger.warning(f"[{indicator.name}] FRED: {series_id} 데이터 없음")
            return None, None

        raw_value = float(result['value'])
        # FRED는 date 문자열 반환 — timezone aware datetime으로 변환
        from datetime import datetime
        date_str = result.get('date', '')
        if date_str:
            asof = timezone.make_aware(
                datetime.strptime(date_str, '%Y-%m-%d')
            )
        else:
            asof = timezone.now()

        return raw_value, asof

    except Exception as e:
        logger.error(f"[{indicator.name}] FRED 예외: {e}")
        return None, None


def _fetch_news_sentiment_value(indicator):
    """뉴스 감성 점수 fetch. data_params의 symbol로 조회."""
    from services.news.models import NewsArticle

    params = indicator.data_params or {}
    symbol = params.get('symbol')

    if not symbol:
        logger.warning(f"[{indicator.name}] 뉴스 감성: symbol 없음")
        return None, None

    try:
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=48)
        articles = NewsArticle.objects.filter(
            entities__symbol=symbol.upper(),
            published_at__gte=cutoff,
            sentiment_score__isnull=False,
        ).values_list('sentiment_score', flat=True)

        if not articles:
            return None, None

        avg_sentiment = float(sum(articles)) / len(articles)
        return avg_sentiment, timezone.now()

    except Exception as e:
        logger.error(f"[{indicator.name}] 뉴스 감성 예외: {e}")
        return None, None


def _fetch_metrics_value(indicator):
    """분기 재무 지표 fetch. data_params의 metric_code로 조회."""
    from thesis.services.quarterly_metric_fetcher import fetch_quarterly_metric

    params = indicator.data_params or {}
    metric_code = params.get('metric_code')
    symbol = params.get('symbol') or getattr(indicator.thesis, 'target', '').upper()

    if not metric_code or not symbol:
        logger.warning(f"[{indicator.name}] metrics: metric_code 또는 symbol 없음")
        return None, None

    try:
        result = fetch_quarterly_metric(symbol, metric_code)
        if not result or result['value'] is None:
            return None, None

        return result['value'], timezone.now().replace(hour=18, minute=0, second=0, microsecond=0)
    except Exception as e:
        logger.error(f"[{indicator.name}] metrics 예외: {e}")
        return None, None


DATA_SOURCE_FETCHERS = {
    'fmp': _fetch_fmp_value,
    'fred': _fetch_fred_value,
    'news_sentiment': _fetch_news_sentiment_value,
    'metrics': _fetch_metrics_value,
}


def fetch_indicator_value(indicator):
    """data_source에 따라 적절한 fetcher 호출."""
    fetcher = DATA_SOURCE_FETCHERS.get(indicator.data_source)
    if not fetcher:
        # manual, custom 등 → skip
        return None, None
    return fetcher(indicator)


# ──────────────────────────────────────────────────────────
# Task 1: update_indicator_readings
# ──────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3)
def update_indicator_readings(self):
    """
    매일 18:00 ET 실행.
    active 가설의 활성 지표에 대해 외부 API에서 데이터 fetch + validation.
    멱등성: (indicator, asof) 기준 upsert (수학 모델 12.3).
    """
    from thesis.models import IndicatorReading, Thesis
    from thesis.services.data_validator import VALIDATION_ACTIONS, validate_reading

    active_theses = Thesis.objects.filter(status='active')
    total, success = 0, 0
    skip_counts = {
        'null_value': 0, 'stale_data': 0, 'extreme_jump': 0,
        'non_finite': 0, 'below_minimum': 0, 'above_maximum': 0,
    }
    error_count = 0

    for thesis in active_theses:
        try:
            indicators = thesis.indicators.filter(
                is_active=True, is_paused=False,
            ).exclude(data_source__in=['manual', 'custom'])
        except Exception as e:
            logger.error(f"[Thesis {thesis.id}] 지표 조회 실패: {e}")
            error_count += 1
            continue  # 다음 가설로 (실패 격리)

        for indicator in indicators:
            total += 1
            try:
                raw_value, asof = fetch_indicator_value(indicator)

                if raw_value is None or asof is None:
                    skip_counts['null_value'] += 1
                    # 감사 추적: null reading 기록
                    IndicatorReading.objects.update_or_create(
                        indicator=indicator,
                        asof=timezone.now(),
                        defaults={
                            'value': None,
                            'raw_value': None,
                            'validation_status': 'null_value',
                        },
                    )
                    continue

                is_valid, reason = validate_reading(indicator, raw_value, asof)

                action = VALIDATION_ACTIONS.get(reason, 'skip')

                if action == 'save':
                    # ok 또는 extreme_jump_allowed
                    IndicatorReading.objects.update_or_create(
                        indicator=indicator,
                        asof=asof,
                        defaults={
                            'value': raw_value,
                            'raw_value': raw_value,
                            'validation_status': reason,
                        },
                    )
                    success += 1
                else:
                    # skip 계열: 감사 추적용 기록 (value=None)
                    IndicatorReading.objects.update_or_create(
                        indicator=indicator,
                        asof=asof,
                        defaults={
                            'value': None,
                            'raw_value': raw_value,
                            'validation_status': reason,
                        },
                    )
                    if reason in skip_counts:
                        skip_counts[reason] += 1

            except Exception as e:
                logger.error(f"[{indicator.name}] fetch 실패: {e}")
                error_count += 1
                continue  # 다음 지표로 (실패 격리)

    logger.info(
        f"[EOD] fetch 완료: 성공={success}/{total}, "
        f"skip={{null={skip_counts['null_value']}, stale={skip_counts['stale_data']}, "
        f"jump={skip_counts['extreme_jump']}, non_finite={skip_counts['non_finite']}, "
        f"below_min={skip_counts['below_minimum']}, above_max={skip_counts['above_maximum']}}}, "
        f"error={error_count}"
    )

    return {
        'total': total,
        'success': success,
        'skip_counts': skip_counts,
        'error_count': error_count,
    }


# ──────────────────────────────────────────────────────────
# Task 2: calculate_scores
# ──────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3)
def calculate_scores(self):
    """
    매일 18:15 ET 실행.
    active 가설의 지표별 score 계산 + DB 업데이트.
    """
    from thesis.models import Thesis
    from thesis.services.arrow_calculator import (
        degree_to_color,
        degree_to_label,
        score_to_degree,
    )
    from thesis.services.indicator_scorer import score_indicator_from_model
    from thesis.services.premise_aggregator import aggregate_premise, aggregate_thesis

    active_theses = Thesis.objects.filter(status='active')
    ind_count, prem_count, extreme_count, override_count = 0, 0, 0, 0

    for thesis in active_theses:
        try:
            indicators = thesis.indicators.filter(is_active=True)
            indicator_scores = {}
            indicators_to_update = []

            for indicator in indicators:
                ind_count += 1
                try:
                    result = score_indicator_from_model(indicator)
                    score = result['score']
                    degree = score_to_degree(score)

                    indicator.current_score = score
                    indicator.current_degree = degree
                    indicator.current_color = degree_to_color(degree)
                    indicator.current_label = degree_to_label(degree)
                    indicators_to_update.append(indicator)

                    indicator_scores[str(indicator.id)] = score

                    if result.get('is_extreme_vol'):
                        extreme_count += 1
                    if result.get('is_override'):
                        override_count += 1

                except Exception as e:
                    logger.error(
                        f"[{indicator.name}] 스코어 계산 실패: {e}"
                    )
                    continue

            # bulk_update
            if indicators_to_update:
                from thesis.models import ThesisIndicator
                ThesisIndicator.objects.bulk_update(
                    indicators_to_update,
                    ['current_score', 'current_degree',
                     'current_color', 'current_label'],
                )

            # 전제별 점수 집계
            premise_scores = {}
            for premise in thesis.premises.filter(is_active=True, is_paused=False):
                prem_count += 1
                try:
                    result = aggregate_premise(premise, indicator_scores)
                    premise_scores[str(premise.id)] = result['score']
                except Exception as e:
                    logger.error(
                        f"[{premise.content[:30]}] 전제 집계 실패: {e}"
                    )

            # 가설 전체 점수 집계 + DB 업데이트
            thesis_result = aggregate_thesis(
                thesis, premise_scores, indicator_scores,
            )
            thesis.current_score = thesis_result['overall_score']
            thesis.save(update_fields=['current_score'])

        except Exception as e:
            logger.error(f"[Thesis {thesis.id}] 스코어 계산 실패: {e}")
            continue  # 다음 가설로 (실패 격리)

    logger.info(
        f"[EOD] 스코어 계산: 지표={ind_count}, 전제={prem_count}, "
        f"extreme_vol={extreme_count}, override={override_count}"
    )

    return {
        'ind_count': ind_count,
        'prem_count': prem_count,
        'extreme_count': extreme_count,
        'override_count': override_count,
    }


# ──────────────────────────────────────────────────────────
# Task 3: create_snapshots_and_alerts
# ──────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3)
def create_snapshots_and_alerts(self):
    """
    매일 18:30 ET 실행.
    active 가설에 대해 스냅샷 생성 + 상태 판정 + 알림 생성.
    """
    from thesis.models import Thesis
    from thesis.services.alert_engine import check_and_create_alerts
    from thesis.services.snapshot_builder import build_snapshot

    start_time = time.time()
    active_theses = Thesis.objects.filter(status='active')
    today = date.today()

    snap_count, alert_count, sent_count, throttled_count = 0, 0, 0, 0
    low_coverage_count = 0

    for thesis in active_theses:
        try:
            # build_snapshot returns (snapshot, scoring_result, prev_snapshot)
            snapshot, scoring_result, prev_snapshot = build_snapshot(
                thesis, as_of_date=today,
            )
            snap_count += 1

            # data_coverage 체크
            if scoring_result['data_coverage'] < 0.6:
                low_coverage_count += 1

            # 알림 생성
            alerts = check_and_create_alerts(
                thesis, scoring_result, prev_snapshot,
            )
            for alert in alerts:
                alert_count += 1
                if alert.is_pushed:
                    sent_count += 1
                    # 실제 push/email 발송은 기존 notification 시스템 연결
                    # Phase 1: 로그만 기록
                    logger.info(
                        f"[Alert Push] {thesis.id}: {alert.title}"
                    )

        except Exception as e:
            logger.error(f"[Thesis {thesis.id}] 스냅샷/알림 실패: {e}")
            continue  # 실패 격리

    elapsed = time.time() - start_time

    # throttled = 총 알림 시도 - 실제 생성 (정확한 추적은 check_and_create_alerts 내부에서 해야 하지만,
    # Phase 1에서는 생성된 것만 카운트)
    logger.info(
        f"[EOD] 스냅샷={snap_count}, 알림 생성={alert_count} "
        f"(발송={sent_count}, throttled={throttled_count}), "
        f"coverage_low={low_coverage_count}, 실행시간={elapsed:.1f}s"
    )

    return {
        'snap_count': snap_count,
        'alert_count': alert_count,
        'sent_count': sent_count,
        'low_coverage_count': low_coverage_count,
        'elapsed': round(elapsed, 1),
    }
