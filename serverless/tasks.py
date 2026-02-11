"""
Market Movers Celery 태스크

매일 오전 7:30에 자동으로 Market Movers 데이터를 동기화합니다.
"""
import logging
from celery import shared_task
from django.utils import timezone

from serverless.services.data_sync import MarketMoversSync
from serverless.services.fmp_client import FMPAPIError


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60 * 5,  # 5분 후 재시도
)
def sync_daily_market_movers(self, target_date=None):
    """
    일일 Market Movers 동기화 태스크

    Args:
        target_date: 대상 날짜 (문자열, 기본값: 오늘)

    Returns:
        dict: {'gainers': int, 'losers': int, 'actives': int, 'errors': int}

    Usage:
        # 수동 실행
        from serverless.tasks import sync_daily_market_movers
        result = sync_daily_market_movers.delay()

        # 특정 날짜
        result = sync_daily_market_movers.delay(target_date='2025-01-01')
    """
    try:
        # 날짜 변환
        if target_date:
            from datetime import datetime
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()

        logger.info(f"🚀 Celery Task 시작: sync_daily_market_movers (date={target_date})")

        # 동기화 실행
        sync = MarketMoversSync()
        result = sync.sync_daily_movers(target_date=target_date)

        logger.info(f"✅ Celery Task 완료: {result}")
        return result

    except FMPAPIError as exc:
        # FMP API 에러 - 재시도
        logger.error(f"❌ FMP API 에러: {exc}")
        raise self.retry(exc=exc)

    except Exception as exc:
        # 기타 에러
        logger.exception(f"❌ 예상치 못한 에러: {exc}")
        raise


@shared_task
def manual_sync_market_movers(date_str: str = None):
    """
    수동 동기화 태스크 (관리자 도구용)

    Args:
        date_str: 날짜 문자열 (YYYY-MM-DD)

    Returns:
        dict: 동기화 결과
    """
    logger.info(f"📋 수동 동기화 요청: {date_str or 'today'}")
    return sync_daily_market_movers.delay(target_date=date_str)


# ============================================================
# Market Movers 키워드 생성 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=2,
    soft_time_limit=300,  # 5분 소프트 타임아웃
    time_limit=360,  # 6분 하드 타임아웃
)
def collect_keyword_data(self, movers_date: str, mover_type: str = 'gainers'):
    """
    키워드 생성용 데이터 수집 (병렬)

    Args:
        movers_date: Market Movers 날짜 (YYYY-MM-DD)
        mover_type: 'gainers', 'losers', 'actives'

    Returns:
        {
            'date': '2026-01-07',
            'mover_type': 'gainers',
            'successful': ['AAPL', 'MSFT', ...],
            'failed': [('GOOGL', 'error'), ...],
            'cache_hits': 5,
            'api_calls': 15,
            'duration_ms': 240000
        }
    """
    from datetime import datetime
    from serverless.models import MarketMover
    from serverless.services.keyword_data_collector import KeywordDataCollector

    try:
        # 날짜 변환
        target_date = datetime.strptime(movers_date, '%Y-%m-%d').date()

        logger.info("keyword_data_collection_task", extra={
            "status": "started",
            "date": movers_date,
            "mover_type": mover_type,
        })

        # MarketMover에서 종목 리스트 조회
        movers = MarketMover.objects.filter(
            date=target_date,
            mover_type=mover_type
        ).order_by('rank')[:20]  # TOP 20

        symbols = [m.symbol for m in movers]

        if not symbols:
            logger.warning(f"No movers found for {movers_date} ({mover_type})")
            return {
                'date': movers_date,
                'mover_type': mover_type,
                'successful': [],
                'failed': [],
                'cache_hits': 0,
                'api_calls': 0,
                'duration_ms': 0,
            }

        # 데이터 수집 (병렬)
        collector = KeywordDataCollector()
        result = collector.collect_batch(symbols, target_date)

        logger.info("keyword_data_collection_task", extra={
            "status": "completed",
            "successful": len(result['successful']),
            "failed": len(result['failed']),
            "cache_hits": result['cache_hits'],
            "api_calls": result['api_calls'],
            "duration_ms": result['duration_ms'],
        })

        return {
            'date': movers_date,
            'mover_type': mover_type,
            'successful': result['successful'],
            'failed': result['failed'],
            'cache_hits': result['cache_hits'],
            'api_calls': result['api_calls'],
            'duration_ms': result['duration_ms'],
        }

    except Exception as exc:
        logger.exception(f"❌ 키워드 데이터 수집 실패: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=1,
)
def generate_keywords_batch(self, collection_result: dict):
    """
    키워드 배치 생성 (LLM 호출)

    Args:
        collection_result: collect_keyword_data의 결과

    Returns:
        {
            'date': '2026-01-07',
            'keywords': {
                'AAPL': [...],
                'MSFT': [...]
            },
            'llm_tokens': {
                'input': 7200,
                'output': 6000,
                'cost_usd': 0.009
            }
        }
    """
    from serverless.services.keyword_service import KeywordGenerationService
    from datetime import datetime

    try:
        date_str = collection_result['date']
        mover_type = collection_result.get('mover_type', 'gainers')
        successful_symbols = collection_result['successful']

        if not successful_symbols:
            logger.warning("No successful symbols to generate keywords")
            return {
                'date': date_str,
                'keywords': {},
                'llm_tokens': {'input': 0, 'output': 0, 'cost_usd': 0.0}
            }

        logger.info("keyword_generation_task", extra={
            "status": "started",
            "date": date_str,
            "num_stocks": len(successful_symbols),
        })

        # 날짜 변환
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # LLM 키워드 생성 (배치)
        # Note: 현재는 기본 정보만 사용, 향후 contexts 활용 예정
        service = KeywordGenerationService()
        keywords_result = service.batch_generate(
            date=target_date,
            mover_type=mover_type,
            limit=len(successful_symbols)
        )

        # batch_generate는 {'success', 'failed', 'skipped'} 반환하고 직접 DB 저장
        logger.info("keyword_generation_task", extra={
            "status": "completed",
            "success": keywords_result['success'],
            "failed": keywords_result['failed'],
            "skipped": keywords_result['skipped'],
        })

        return {
            'date': date_str,
            'mover_type': mover_type,
            'success': keywords_result['success'],
            'failed': keywords_result['failed'],
            'skipped': keywords_result['skipped'],
        }

    except Exception as exc:
        logger.exception(f"❌ 키워드 생성 실패: {exc}")
        raise self.retry(exc=exc)


@shared_task
def save_keywords(generation_result: dict):
    """
    키워드 생성 완료 처리

    Note: batch_generate가 이미 DB에 저장하므로,
          이 태스크는 Redis 캐시 정리만 수행합니다.

    Args:
        generation_result: generate_keywords_batch의 결과

    Returns:
        {
            'date': '2026-01-07',
            'mover_type': 'gainers',
            'success': 18,
            'failed': 2,
            'skipped': 0
        }
    """
    from serverless.services.keyword_data_collector import KeywordDataCollector
    from serverless.models import StockKeyword

    try:
        date_str = generation_result['date']
        mover_type = generation_result.get('mover_type', 'gainers')

        logger.info("keyword_save_task", extra={
            "status": "started",
            "date": date_str,
            "mover_type": mover_type,
        })

        # Redis 캐시 삭제 (생성 완료된 종목)
        from datetime import datetime
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        completed_symbols = StockKeyword.objects.filter(
            date=target_date,
            status='completed'
        ).values_list('symbol', flat=True)

        collector = KeywordDataCollector()
        for symbol in completed_symbols:
            collector.delete_cached_context(date_str, symbol)

        logger.info("keyword_save_task", extra={
            "status": "completed",
            "cache_cleared": len(completed_symbols),
        })

        return {
            'date': date_str,
            'mover_type': mover_type,
            'success': generation_result.get('success', 0),
            'failed': generation_result.get('failed', 0),
            'skipped': generation_result.get('skipped', 0),
            'cache_cleared': len(completed_symbols),
        }

    except Exception as exc:
        logger.exception(f"❌ 키워드 저장 완료 처리 실패: {exc}")
        raise


@shared_task(
    bind=True,
    max_retries=1,
    soft_time_limit=600,  # 10분 소프트 타임아웃
    time_limit=660,  # 11분 하드 타임아웃
)
def generate_screener_keywords_task(self, stocks: list):
    """
    스크리너 종목들의 키워드 생성

    Args:
        stocks: 종목 리스트
            [
                {"symbol": "AAPL", "company_name": "Apple Inc.", "sector": "Technology", "change_percent": 2.5},
                ...
            ]

    Returns:
        {
            'success': 18,
            'failed': 2,
            'results': {
                'AAPL': ['키워드1', '키워드2', '키워드3'],
                ...
            }
        }
    """
    from serverless.services.keyword_service import KeywordGenerationService
    from serverless.models import StockKeyword
    from datetime import timedelta

    try:
        logger.info(f"🚀 스크리너 키워드 생성 시작: {len(stocks)}개 종목")

        service = KeywordGenerationService()
        today = timezone.now().date()

        results = {'success': 0, 'failed': 0, 'results': {}}

        for stock in stocks:
            symbol = stock.get('symbol', '').upper()
            company_name = stock.get('company_name', symbol)
            sector = stock.get('sector')
            industry = stock.get('industry')
            change_percent = stock.get('change_percent', 0)

            if not symbol:
                continue

            # 이미 생성된 키워드 확인
            existing = StockKeyword.objects.filter(
                symbol=symbol,
                date=today,
                status='completed'
            ).first()

            if existing:
                results['results'][symbol] = existing.keywords
                results['success'] += 1
                logger.debug(f"  ⏭️ {symbol}: 이미 생성됨 (캐시 사용)")
                continue

            # 키워드 생성 (mover_type='screener'로 구분)
            result = service.generate_keyword(
                symbol=symbol,
                company_name=company_name,
                date=today,
                mover_type='screener',  # 스크리너 전용 타입
                change_percent=float(change_percent) if change_percent else 0,
                sector=sector,
                industry=industry
            )

            # DB 저장
            StockKeyword.objects.update_or_create(
                symbol=symbol,
                date=today,
                defaults={
                    'company_name': company_name,
                    'keywords': result['keywords'],
                    'status': result['status'],
                    'error_message': result['error_message'],
                    'llm_model': 'gemini-2.5-flash',
                    'generation_time_ms': result['metadata'].get('generation_time_ms'),
                    'prompt_tokens': result['metadata'].get('prompt_tokens'),
                    'completion_tokens': result['metadata'].get('completion_tokens'),
                    'expires_at': timezone.now() + timedelta(days=7),
                }
            )

            if result['status'] == 'completed':
                logger.info(f"  ✅ {symbol}: {result['keywords']}")
                results['results'][symbol] = result['keywords']
                results['success'] += 1
            else:
                logger.warning(f"  ⚠️ {symbol}: {result['error_message']}")
                results['results'][symbol] = result['keywords']  # fallback 키워드
                results['failed'] += 1

        logger.info(f"✅ 스크리너 키워드 생성 완료: success={results['success']}, failed={results['failed']}")

        return results

    except Exception as exc:
        logger.exception(f"❌ 스크리너 키워드 생성 실패: {exc}")
        raise self.retry(exc=exc)


@shared_task
def keyword_generation_pipeline(movers_date: str = None, mover_type: str = 'gainers'):
    """
    키워드 생성 파이프라인 (체이닝)

    Args:
        movers_date: 날짜 문자열 (YYYY-MM-DD, 기본값: 오늘)
        mover_type: 'gainers', 'losers', 'actives'

    Usage:
        from serverless.tasks import keyword_generation_pipeline
        result = keyword_generation_pipeline.delay()
    """
    from celery import chain

    if not movers_date:
        movers_date = timezone.now().strftime('%Y-%m-%d')

    logger.info(f"🚀 키워드 생성 파이프라인 시작: {movers_date} ({mover_type})")

    # 태스크 체인
    pipeline = chain(
        collect_keyword_data.si(movers_date, mover_type),
        generate_keywords_batch.s(),
        save_keywords.s(),
    )

    return pipeline.apply_async()


# ============================================================
# Market Breadth (시장 건강도) 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60 * 5,  # 5분 후 재시도
)
def calculate_daily_market_breadth(self, target_date: str = None):
    """
    일일 Market Breadth 계산 태스크

    장 마감 후 (16:30 ET) 실행되어 시장 건강도를 계산합니다.

    Args:
        target_date: 대상 날짜 (YYYY-MM-DD, 기본값: 오늘)

    Returns:
        {
            'date': '2026-01-27',
            'signal': 'bullish',
            'advance_decline_ratio': 1.5
        }

    Usage:
        from serverless.tasks import calculate_daily_market_breadth
        result = calculate_daily_market_breadth.delay()
    """
    from serverless.services.market_breadth_service import MarketBreadthService
    from serverless.services.fmp_client import FMPAPIError
    from datetime import datetime

    try:
        if target_date:
            date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            date_obj = timezone.now().date()

        logger.info(f"🚀 Market Breadth 계산 시작: {date_obj}")

        service = MarketBreadthService()
        breadth = service.calculate_daily_breadth(date_obj)

        if breadth:
            result = {
                'date': breadth.date.isoformat(),
                'signal': breadth.breadth_signal,
                'advance_decline_ratio': float(breadth.advance_decline_ratio),
                'advancing_count': breadth.advancing_count,
                'declining_count': breadth.declining_count,
            }
            logger.info(f"✅ Market Breadth 계산 완료: {result['signal']}")
            return result
        else:
            logger.warning("Market Breadth 계산 결과 없음")
            return {'date': date_obj.isoformat(), 'error': 'No data'}

    except FMPAPIError as exc:
        logger.error(f"❌ FMP API 에러: {exc}")
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.exception(f"❌ Market Breadth 계산 실패: {exc}")
        raise


# ============================================================
# Sector Heatmap (섹터 히트맵) 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60 * 5,  # 5분 후 재시도
)
def calculate_daily_sector_heatmap(self, target_date: str = None):
    """
    일일 섹터 히트맵 계산 태스크

    장 마감 후 (16:35 ET) 실행되어 11개 섹터 성과를 계산합니다.

    Args:
        target_date: 대상 날짜 (YYYY-MM-DD, 기본값: 오늘)

    Returns:
        {
            'date': '2026-01-27',
            'sectors_calculated': 11,
            'best_sector': 'Technology',
            'worst_sector': 'Energy'
        }

    Usage:
        from serverless.tasks import calculate_daily_sector_heatmap
        result = calculate_daily_sector_heatmap.delay()
    """
    from serverless.services.sector_heatmap_service import SectorHeatmapService
    from serverless.services.fmp_client import FMPAPIError
    from datetime import datetime

    try:
        if target_date:
            date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            date_obj = timezone.now().date()

        logger.info(f"🚀 섹터 히트맵 계산 시작: {date_obj}")

        service = SectorHeatmapService()
        sectors = service.calculate_sector_performance(date_obj)

        if sectors:
            # 성과순 정렬
            sorted_sectors = sorted(sectors, key=lambda x: float(x['return_pct']), reverse=True)
            result = {
                'date': date_obj.isoformat(),
                'sectors_calculated': len(sectors),
                'best_sector': sorted_sectors[0]['sector'] if sorted_sectors else None,
                'worst_sector': sorted_sectors[-1]['sector'] if sorted_sectors else None,
            }
            logger.info(f"✅ 섹터 히트맵 계산 완료: {len(sectors)}개 섹터")
            return result
        else:
            logger.warning("섹터 히트맵 계산 결과 없음")
            return {'date': date_obj.isoformat(), 'error': 'No data'}

    except FMPAPIError as exc:
        logger.error(f"❌ FMP API 에러: {exc}")
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.exception(f"❌ 섹터 히트맵 계산 실패: {exc}")
        raise


# ============================================================
# Screener Alert Check 태스크 (Phase 1)
# ============================================================

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 2,  # 2분 후 재시도
    soft_time_limit=300,  # 5분 소프트 타임아웃
    time_limit=360,  # 6분 하드 타임아웃
)
def check_screener_alerts(self):
    """
    활성 스크리너 알림 체크

    15분마다 실행되어 활성화된 알림 조건을 검사하고,
    조건 충족 시 알림을 발송합니다.

    Returns:
        {
            'checked': 10,
            'triggered': 3,
            'skipped_cooldown': 2,
            'errors': 0
        }

    Usage:
        from serverless.tasks import check_screener_alerts
        result = check_screener_alerts.delay()
    """
    from serverless.models import ScreenerAlert, AlertHistory
    from serverless.services.filter_engine import FilterEngine
    from datetime import timedelta

    try:
        logger.info("🔔 스크리너 알림 체크 시작")

        # 활성 알림 조회 (쿨다운 체크)
        active_alerts = ScreenerAlert.objects.filter(
            is_active=True
        ).select_related('preset', 'user')

        result = {
            'checked': 0,
            'triggered': 0,
            'skipped_cooldown': 0,
            'errors': 0,
        }

        engine = FilterEngine()

        for alert in active_alerts:
            result['checked'] += 1

            try:
                # 쿨다운 체크
                if not alert.can_trigger():
                    result['skipped_cooldown'] += 1
                    logger.debug(f"  ⏭️ {alert.name}: 쿨다운 중")
                    continue

                # 필터 가져오기
                filters = alert.get_effective_filters()

                # 필터 적용 (count만 조회)
                filter_result = engine.apply_filters(
                    filters_dict=filters,
                    limit=20,  # 최대 20개만 조회
                    offset=0,
                    sort_by='marketCap',
                    sort_order='desc'
                )

                matched_count = filter_result.get('count', 0)
                matched_stocks = filter_result.get('results', [])[:10]

                # 조건 충족 체크
                should_trigger = False

                if alert.alert_type == 'filter_match':
                    target_count = alert.target_count or 1
                    should_trigger = matched_count >= target_count

                # TODO: 다른 alert_type 처리
                # - price_target: 특정 종목 목표가 도달
                # - volume_spike: RVOL 임계값 초과
                # - new_high/new_low: 52주 신고가/신저가

                if should_trigger:
                    # 알림 이력 생성
                    AlertHistory.objects.create(
                        alert=alert,
                        matched_count=matched_count,
                        matched_symbols=[s.get('symbol') for s in matched_stocks],
                        snapshot={
                            'filters': filters,
                            'alert_type': alert.alert_type,
                            'target_count': alert.target_count,
                        },
                        status='sent',
                    )

                    # 알림 상태 업데이트
                    alert.last_triggered_at = timezone.now()
                    alert.trigger_count += 1
                    alert.save(update_fields=['last_triggered_at', 'trigger_count'])

                    result['triggered'] += 1
                    logger.info(f"  ✅ {alert.name}: 알림 발송 (매칭 {matched_count}개)")

                    # TODO: 실제 알림 발송
                    # - notify_in_app: WebSocket 메시지
                    # - notify_email: 이메일 발송
                    # - notify_push: PWA 푸시 알림

            except Exception as e:
                result['errors'] += 1
                logger.exception(f"  ❌ {alert.name}: 에러 - {e}")

                # 에러 이력 기록
                AlertHistory.objects.create(
                    alert=alert,
                    matched_count=0,
                    matched_symbols=[],
                    snapshot={'error': str(e)},
                    status='failed',
                    error_message=str(e),
                )

        logger.info(f"✅ 스크리너 알림 체크 완료: {result}")
        return result

    except Exception as exc:
        logger.exception(f"❌ 스크리너 알림 체크 실패: {exc}")
        raise self.retry(exc=exc)


# ============================================================
# Chain Sight Stock (개별 종목 관계 동기화) 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,  # 1분 후 재시도
    soft_time_limit=120,  # 2분 소프트 타임아웃
    time_limit=150,  # 2.5분 하드 타임아웃
)
def sync_stock_relationships(self, symbol: str):
    """
    단일 종목 관계 동기화 태스크

    Chain Sight 탭에서 Cold Start 시 호출됩니다.

    Args:
        symbol: 종목 심볼

    Returns:
        {
            'symbol': 'NVDA',
            'peer_count': 15,
            'industry_count': 20,
            'co_mentioned_count': 5
        }

    Usage:
        from serverless.tasks import sync_stock_relationships
        result = sync_stock_relationships.delay('NVDA')
    """
    from serverless.services.relationship_service import RelationshipService

    try:
        symbol = symbol.upper()
        logger.info(f"🔗 Chain Sight 관계 동기화 시작: {symbol}")

        service = RelationshipService()
        results = service.sync_all(symbol)

        total = sum(results.values())
        logger.info(f"✅ Chain Sight 관계 동기화 완료: {symbol} -> {total}개 관계")

        return {
            'symbol': symbol,
            **results
        }

    except Exception as exc:
        logger.exception(f"❌ Chain Sight 관계 동기화 실패: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=1,
    soft_time_limit=600,  # 10분 소프트 타임아웃
    time_limit=660,  # 11분 하드 타임아웃
)
def batch_sync_stock_relationships(self, symbols: list = None):
    """
    배치 관계 동기화 태스크

    Market Movers 종목들의 관계를 일괄 동기화합니다.
    매일 05:00 EST에 실행됩니다.

    Args:
        symbols: 종목 심볼 리스트 (None이면 최근 7일 Market Movers)

    Returns:
        {
            'total_symbols': 50,
            'success': 48,
            'failed': 2,
            'total_relationships': 1500
        }

    Usage:
        from serverless.tasks import batch_sync_stock_relationships
        result = batch_sync_stock_relationships.delay()
        result = batch_sync_stock_relationships.delay(['AAPL', 'MSFT', 'NVDA'])
    """
    from serverless.services.relationship_service import RelationshipService
    from serverless.models import MarketMover
    from datetime import timedelta

    try:
        logger.info("🔗 Chain Sight 배치 동기화 시작")

        # 심볼 리스트 결정
        if not symbols:
            # 최근 7일 Market Movers에서 추출
            cutoff = timezone.now().date() - timedelta(days=7)
            symbols = list(
                MarketMover.objects.filter(date__gte=cutoff)
                .values_list('symbol', flat=True)
                .distinct()
            )

        if not symbols:
            logger.warning("동기화할 종목 없음")
            return {
                'total_symbols': 0,
                'success': 0,
                'failed': 0,
                'total_relationships': 0
            }

        logger.info(f"  대상 종목: {len(symbols)}개")

        service = RelationshipService()
        success = 0
        failed = 0
        total_relationships = 0

        for symbol in symbols:
            try:
                results = service.sync_all(symbol)
                total = sum(results.values())
                total_relationships += total
                success += 1
                logger.debug(f"  ✅ {symbol}: {total}개 관계")
            except Exception as e:
                failed += 1
                logger.warning(f"  ❌ {symbol}: {e}")

        result = {
            'total_symbols': len(symbols),
            'success': success,
            'failed': failed,
            'total_relationships': total_relationships
        }

        logger.info(f"✅ Chain Sight 배치 동기화 완료: {result}")
        return result

    except Exception as exc:
        logger.exception(f"❌ Chain Sight 배치 동기화 실패: {exc}")
        raise self.retry(exc=exc)


@shared_task
def cleanup_expired_category_cache():
    """
    만료된 카테고리 캐시 정리

    매일 06:00 EST에 실행됩니다.

    Returns:
        {'deleted': 100}
    """
    from serverless.models import CategoryCache

    try:
        logger.info("🧹 만료된 카테고리 캐시 정리 시작")

        deleted_count, _ = CategoryCache.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()

        logger.info(f"✅ 카테고리 캐시 정리 완료: {deleted_count}개 삭제")
        return {'deleted': deleted_count}

    except Exception as exc:
        logger.exception(f"❌ 카테고리 캐시 정리 실패: {exc}")
        raise


# ============================================================
# ETF Holdings 자동 수집 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=1,
    soft_time_limit=600,  # 10분 소프트 타임아웃
    time_limit=660,  # 11분 하드 타임아웃
)
def sync_etf_holdings(self, send_failure_email: bool = True):
    """
    ETF Holdings 자동 수집 태스크

    매주 월요일 06:00 EST에 실행됩니다.
    수집 실패한 ETF 목록을 이메일로 알림합니다.

    Args:
        send_failure_email: 실패 알림 이메일 발송 여부

    Returns:
        {
            'total': 21,
            'success': 15,
            'failed': 6,
            'total_holdings': 701,
            'failed_etfs': ['ARKK', 'ARKG', ...]
        }

    Usage:
        from serverless.tasks import sync_etf_holdings
        result = sync_etf_holdings.delay()
    """
    from serverless.services.etf_csv_downloader import ETFCSVDownloader
    from serverless.services.theme_matching_service import ThemeMatchingService
    from serverless.models import ETFProfile, ETFHolding

    try:
        logger.info("📊 ETF Holdings 자동 수집 시작")

        # 모든 해시 클리어 (변경 감지를 위해)
        ETFProfile.objects.all().update(last_hash='')

        downloader = ETFCSVDownloader(auto_resolve_url=True, max_retries=2)

        success_list = []
        failed_list = []

        for profile in ETFProfile.objects.filter(is_active=True).order_by('tier', 'symbol'):
            try:
                holdings = downloader.download_holdings(profile.symbol)
                success_list.append({
                    'symbol': profile.symbol,
                    'name': profile.name,
                    'tier': profile.tier,
                    'count': len(holdings)
                })
                logger.info(f"  ✅ {profile.symbol}: {len(holdings)}개")
            except Exception as e:
                error_msg = str(e)[:100]
                failed_list.append({
                    'symbol': profile.symbol,
                    'name': profile.name,
                    'tier': profile.tier,
                    'error': error_msg
                })
                logger.warning(f"  ❌ {profile.symbol}: {error_msg}")

        # 테마 매칭 갱신
        if success_list:
            try:
                theme_service = ThemeMatchingService()
                theme_result = theme_service.refresh_all_matches()
                logger.info(f"  🏷️ 테마 매칭 갱신: {theme_result}")
            except Exception as e:
                logger.warning(f"  ⚠️ 테마 매칭 갱신 실패: {e}")

        total_holdings = ETFHolding.objects.count()

        result = {
            'total': len(success_list) + len(failed_list),
            'success': len(success_list),
            'failed': len(failed_list),
            'total_holdings': total_holdings,
            'success_etfs': [s['symbol'] for s in success_list],
            'failed_etfs': [f['symbol'] for f in failed_list],
        }

        logger.info(f"✅ ETF Holdings 수집 완료: 성공 {result['success']} / 실패 {result['failed']}")

        # 실패 알림 이메일 발송
        if send_failure_email and failed_list:
            send_etf_sync_failure_email.delay(failed_list, success_list)

        return result

    except Exception as exc:
        logger.exception(f"❌ ETF Holdings 수집 실패: {exc}")
        raise self.retry(exc=exc)


@shared_task
def send_etf_sync_failure_email(failed_list: list, success_list: list):
    """
    ETF 수집 실패 알림 이메일 발송

    Args:
        failed_list: 실패한 ETF 리스트
        success_list: 성공한 ETF 리스트
    """
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        recipients = ['goid545@naver.com', 'jinie545@gmail.com']

        # 이메일 본문 생성
        subject = f"[Stock-Vis] ETF Holdings 수집 실패 알림 ({len(failed_list)}개)"

        body_lines = [
            "ETF Holdings 자동 수집 결과입니다.",
            "",
            f"📊 성공: {len(success_list)}개",
            f"❌ 실패: {len(failed_list)}개",
            "",
            "=" * 50,
            "실패 목록 (수동 수집 필요)",
            "=" * 50,
            "",
        ]

        for f in failed_list:
            body_lines.append(f"• {f['symbol']} ({f['name']})")
            body_lines.append(f"  - Tier: {f['tier']}")
            body_lines.append(f"  - 에러: {f['error']}")
            body_lines.append("")

        body_lines.extend([
            "=" * 50,
            "수동 수집 방법",
            "=" * 50,
            "",
            "1. 운용사 웹사이트에서 Holdings CSV 다운로드",
            "2. 서버에서 다음 명령 실행:",
            "",
            "   python manage.py import_etf_csv {SYMBOL} /path/to/holdings.csv",
            "",
            "운용사 다운로드 페이지:",
            "• ARK: https://ark-funds.com/funds/arkk/ (Download Holdings)",
            "• Invesco: https://www.invesco.com/us/financial-products/etfs/",
            "",
        ])

        body = "\n".join(body_lines)

        # 이메일 발송
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )

        logger.info(f"✉️ ETF 수집 실패 알림 이메일 발송 완료: {recipients}")
        return {'sent_to': recipients, 'failed_count': len(failed_list)}

    except Exception as e:
        logger.exception(f"❌ 이메일 발송 실패: {e}")
        # 이메일 실패해도 태스크는 성공으로 처리
        return {'error': str(e)}


# ============================================================
# Supply Chain (Phase 4) 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 5,  # 5분 후 재시도
    soft_time_limit=300,  # 5분 소프트 타임아웃
    time_limit=360,  # 6분 하드 타임아웃
)
def sync_supply_chain_single(self, symbol: str):
    """
    단일 종목 공급망 동기화 태스크

    SEC 10-K에서 공급사/고객사 관계를 추출합니다.

    Args:
        symbol: 종목 심볼

    Returns:
        {
            'symbol': 'TSM',
            'status': 'success',
            'customer_count': 3,
            'supplier_count': 2
        }

    Usage:
        from serverless.tasks import sync_supply_chain_single
        result = sync_supply_chain_single.delay('TSM')
    """
    from serverless.services.supply_chain_service import SupplyChainService

    try:
        symbol = symbol.upper()
        logger.info(f"🔗 공급망 동기화 시작: {symbol}")

        service = SupplyChainService()
        result = service.sync_supply_chain(symbol)

        logger.info(
            f"✅ 공급망 동기화 완료: {symbol} - "
            f"고객 {result.get('customer_count', 0)}개, "
            f"공급사 {result.get('supplier_count', 0)}개"
        )

        return {
            'symbol': symbol,
            'status': result.get('status', 'unknown'),
            'customer_count': result.get('customer_count', 0),
            'supplier_count': result.get('supplier_count', 0),
            'processing_time_ms': result.get('processing_time_ms', 0)
        }

    except Exception as exc:
        logger.exception(f"❌ 공급망 동기화 실패: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=1,
    soft_time_limit=3600,  # 60분 소프트 타임아웃
    time_limit=3660,  # 61분 하드 타임아웃
)
def sync_supply_chain_batch(self, symbols: list = None):
    """
    배치 공급망 동기화 태스크

    S&P 500 종목들의 공급망 관계를 일괄 동기화합니다.
    매월 15일 03:00 EST에 실행됩니다.

    Args:
        symbols: 종목 심볼 리스트 (None이면 S&P 500 상위 100개)

    Returns:
        {
            'total': 100,
            'success': 85,
            'failed': 15,
            'total_customers': 250,
            'total_suppliers': 180
        }

    Usage:
        from serverless.tasks import sync_supply_chain_batch
        result = sync_supply_chain_batch.delay()
        result = sync_supply_chain_batch.delay(['TSM', 'NVDA', 'AAPL'])
    """
    from serverless.services.supply_chain_service import SupplyChainService
    from stocks.models import Stock

    try:
        logger.info("🔗 공급망 배치 동기화 시작")

        # 심볼 리스트 결정
        if not symbols:
            # 시가총액 상위 100개 종목
            symbols = list(
                Stock.objects.filter(
                    market_capitalization__isnull=False
                ).order_by('-market_capitalization')
                .values_list('symbol', flat=True)[:100]
            )

        if not symbols:
            logger.warning("동기화할 종목 없음")
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'total_customers': 0,
                'total_suppliers': 0
            }

        logger.info(f"  대상 종목: {len(symbols)}개")

        service = SupplyChainService()
        batch_result = service.sync_batch(symbols)

        # 통계 계산
        total_customers = sum(
            r.get('customer_count', 0)
            for r in batch_result.get('results', {}).values()
            if isinstance(r, dict)
        )
        total_suppliers = sum(
            r.get('supplier_count', 0)
            for r in batch_result.get('results', {}).values()
            if isinstance(r, dict)
        )

        result = {
            'total': batch_result.get('total', 0),
            'success': batch_result.get('success', 0),
            'failed': batch_result.get('failed', 0),
            'total_customers': total_customers,
            'total_suppliers': total_suppliers,
            'failed_symbols': batch_result.get('failed_symbols', [])
        }

        logger.info(f"✅ 공급망 배치 동기화 완료: {result}")
        return result

    except Exception as exc:
        logger.exception(f"❌ 공급망 배치 동기화 실패: {exc}")
        raise self.retry(exc=exc)


# ============================================================
# Celery Beat 스케줄 (config/celery.py에 등록 필요)
# ============================================================
#
# CELERY_BEAT_SCHEDULE 추가:
#
# 'check-screener-alerts': {
#     'task': 'serverless.tasks.check_screener_alerts',
#     'schedule': crontab(minute='*/15'),  # 15분마다 (시장 시간)
#     'options': {'expires': 600}  # 10분 후 만료
# },
# 'calculate-market-breadth': {
#     'task': 'serverless.tasks.calculate_daily_market_breadth',
#     'schedule': crontab(hour=16, minute=30),  # 장 마감 후 16:30 ET
#     'options': {'expires': 3600}
# },
# 'calculate-sector-heatmap': {
#     'task': 'serverless.tasks.calculate_daily_sector_heatmap',
#     'schedule': crontab(hour=16, minute=35),  # 16:35 ET
#     'options': {'expires': 3600}
# },
# 'batch-sync-stock-relationships': {
#     'task': 'serverless.tasks.batch_sync_stock_relationships',
#     'schedule': crontab(hour=5, minute=0),  # 매일 05:00 EST
#     'options': {'expires': 3600}
# },
# 'cleanup-expired-category-cache': {
#     'task': 'serverless.tasks.cleanup_expired_category_cache',
#     'schedule': crontab(hour=6, minute=0),  # 매일 06:00 EST
#     'options': {'expires': 600}
# },
