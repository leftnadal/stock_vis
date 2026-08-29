import datetime as _dt
import decimal as _decimal
import os
import time

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
from django.db import transaction

from .models import DailyPrice, Stock, WeeklyPrice

logger = get_task_logger(__name__)


def chunks(lst, n):
    """리스트를 n개씩 묶어서 반환하는 헬퍼 함수"""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


@shared_task
def aggregate_weekly_prices(target_week_end=None):
    """
    DailyPrice → WeeklyPrice DB 집계 (API 호출 없음)

    이미 수집된 DailyPrice 데이터를 ISO 주차 기준으로 WeeklyPrice로 변환.
    Beat 스케줄: 토요일 01:00 (금요일 EOD 동기화 이후)

    Args:
        target_week_end: 대상 주 금요일 날짜 (YYYY-MM-DD 문자열, 기본: 직전 금요일)
    """
    from collections import defaultdict
    from datetime import date, timedelta

    from django.db.models import Avg, Max, Min, Sum

    from .models import SP500Constituent

    try:
        today = date.today()

        if target_week_end:
            week_end = date.fromisoformat(target_week_end)
        else:
            # 직전 금요일 계산
            days_since_friday = (today.weekday() - 4) % 7
            if days_since_friday == 0 and today.weekday() != 4:
                days_since_friday = 7
            week_end = today - timedelta(days=days_since_friday)

        # 해당 주 월~금 범위
        week_start = week_end - timedelta(days=4)

        logger.info(f"Aggregating weekly prices for {week_start} ~ {week_end}")

        # S&P 500 활성 종목 기준
        sp500_symbols = list(
            SP500Constituent.objects.filter(is_active=True).values_list(
                "symbol", flat=True
            )
        )

        if not sp500_symbols:
            return {
                "week_end": str(week_end),
                "symbols_aggregated": 0,
                "created": 0,
                "updated": 0,
            }

        # 해당 주간의 모든 DailyPrice 조회
        daily_prices = DailyPrice.objects.filter(
            stock__symbol__in=sp500_symbols,
            date__gte=week_start,
            date__lte=week_end,
        ).select_related("stock")

        # 종목별 그룹화
        symbol_prices = defaultdict(list)
        for dp in daily_prices:
            symbol_prices[dp.stock_id].append(dp)

        created = 0
        updated = 0

        for symbol, prices in symbol_prices.items():
            if not prices:
                continue

            prices_sorted = sorted(prices, key=lambda x: x.date)

            first_day = prices_sorted[0]
            last_day = prices_sorted[-1]

            defaults = {
                "open_price": first_day.open_price,
                "high_price": max(p.high_price for p in prices_sorted),
                "low_price": min(p.low_price for p in prices_sorted),
                "close_price": last_day.close_price,
                "volume": sum(p.volume for p in prices_sorted),
                "week_start_date": first_day.date,
                "week_end_date": last_day.date,
                "average_volume": sum(p.volume for p in prices_sorted)
                // len(prices_sorted),
            }

            try:
                stock = Stock.objects.get(symbol=symbol)
            except Stock.DoesNotExist:
                logger.warning(f"Stock {symbol} not found, skipping")
                continue

            _, was_created = WeeklyPrice.objects.update_or_create(
                stock=stock,
                date=last_day.date,
                defaults=defaults,
            )

            if was_created:
                created += 1
            else:
                updated += 1

        result = {
            "week_end": str(week_end),
            "symbols_aggregated": created + updated,
            "created": created,
            "updated": updated,
        }
        logger.info(f"Weekly aggregation complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Weekly aggregation failed: {e}")
        return f"Error: {e}"


@shared_task
def sync_sp500_financials(batch_size=101):
    """
    S&P 500 재무제표 순환 배치 업데이트 (FMP Provider 사용)

    S&P 500 전체를 5거래일에 1회전 완료.
    재무제표 없는 종목 우선 → 오래된 순 정렬 → 상위 batch_size 선택.

    Beat 스케줄: 평일 20:00 (EOD 동기화 이후)

    Args:
        batch_size: 1일 처리 종목 수 (기본: 101, 5일에 ~503개 커버)
    """
    from datetime import datetime

    from django.db.models import Max

    from .models import BalanceSheet, SP500Constituent

    try:
        all_symbols = list(
            SP500Constituent.objects.filter(is_active=True).values_list(
                "symbol", flat=True
            )
        )

        # DOTSYM 옵션 1: dot 심볼(BRK.B·BF.B) 포함. FMP hyphen 변환은 FMPClient 경계 처리
        # → 유니버스 dot 제외 폐지(Bug #23 은 변환 계층이 해소).
        sp500_symbols = all_symbols

        if not sp500_symbols:
            return {"scheduled": 0, "total_sp500": 0, "oldest_update": None}

        # 각 심볼의 마지막 재무제표 업데이트 시각 조회
        last_updates = (
            BalanceSheet.objects.filter(stock__symbol__in=sp500_symbols)
            .values("stock__symbol")
            .annotate(last_update=Max("created_at"))
        )
        update_map = {row["stock__symbol"]: row["last_update"] for row in last_updates}

        # 재무제표 없는 종목 우선, 그 다음 오래된 순
        never_updated = [s for s in sp500_symbols if s not in update_map]
        has_data = sorted(
            [s for s in sp500_symbols if s in update_map],
            key=lambda s: update_map[s],
        )
        priority_list = never_updated + has_data

        batch = priority_list[:batch_size]

        for i, symbol in enumerate(batch):
            # FMP rate limit 보호: 7초 간격 (태스크 실행 ~6초, 동시 실행 방지)
            # 101개 × 7초 = ~12분 소요
            update_financials_with_provider.apply_async(
                args=[symbol],
                countdown=i * 7,
            )

        oldest_update = str(update_map[has_data[0]]) if has_data else None

        result = {
            "scheduled": len(batch),
            "total_sp500": len(sp500_symbols),
            "never_updated": len(never_updated),
            "oldest_update": oldest_update,
        }
        logger.info(f"S&P 500 financials sync scheduled: {result}")
        return result

    except Exception as e:
        logger.error(f"S&P 500 financials sync failed: {e}")
        return f"Error: {e}"


@shared_task
def bulk_sync_sp500_financials():
    """
    S&P 500 재무제표 초기 대량 동기화 (수동 실행 전용)

    Beat 스케줄에 등록하지 않음. DB에 재무제표가 없는 종목을 모두 업데이트.
    countdown으로 2초 간격 분산 → FMP 분당 300 제한 내 안전하게 처리.

    수동 호출:
        from packages.shared.stocks.tasks import bulk_sync_sp500_financials
        bulk_sync_sp500_financials.delay()
    """
    from .models import BalanceSheet, SP500Constituent

    try:
        # DOTSYM 옵션 1: dot 심볼(BRK.B·BF.B) 포함. FMP hyphen 변환은 FMPClient 경계 처리.
        sp500_symbols = list(
            SP500Constituent.objects.filter(is_active=True).values_list(
                "symbol", flat=True
            )
        )

        # 재무제표가 있는 종목 집합
        has_financials = set(
            BalanceSheet.objects.filter(stock__symbol__in=sp500_symbols)
            .values_list("stock__symbol", flat=True)
            .distinct()
        )

        missing = [s for s in sp500_symbols if s not in has_financials]

        for idx, symbol in enumerate(missing):
            update_financials_with_provider.apply_async(
                args=[symbol],
                countdown=idx * 2,  # 2초 간격으로 분산
            )

        result = {
            "total_sp500": len(sp500_symbols),
            "already_have_data": len(has_financials),
            "total_missing": len(missing),
            "scheduled": len(missing),
        }
        logger.info(f"Bulk S&P 500 financials sync scheduled: {result}")
        return result

    except Exception as e:
        logger.error(f"Bulk S&P 500 financials sync failed: {e}")
        return f"Error: {e}"


# 테스트 태스크
@shared_task
def add_numbers(x, y):
    """간단한 테스트 태스크"""
    result = x + y
    logger.info(f"Add task: {x} + {y} = {result}")
    return result


@shared_task
def test_redis_connection():
    """Redis 연결 테스트"""
    try:
        cache.set("test_key", "test_value", 10)
        value = cache.get("test_key")
        logger.info(f"Redis test: stored and retrieved '{value}'")
        return f"Redis working: {value}"
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return f"Redis error: {e}"


# ============================================================
# StockService 기반 태스크 (Provider 추상화 사용)
# ============================================================


@shared_task(bind=True, max_retries=3)
def update_stock_with_provider(self, symbol, use_fallback=True):
    """
    Provider 추상화를 사용한 주식 데이터 업데이트

    StockService를 통해 Feature Flag에 따라 Alpha Vantage 또는 FMP 사용.
    Fallback 기능으로 주 provider 실패 시 대체 provider 자동 사용.

    Args:
        symbol: 주식 심볼
        use_fallback: Fallback 사용 여부 (기본: True)

    Returns:
        결과 문자열
    """
    try:
        from packages.shared.api_request.stock_service import get_stock_service

        service = get_stock_service()
        symbol = symbol.upper().strip()

        results = {
            "symbol": symbol,
            "stock_data": False,
            "prices": False,
            "financials": False,
        }

        # 1. 주식 기본 정보 업데이트
        try:
            logger.info(f"[Provider] Updating stock data for {symbol}")
            stock = service.update_stock_data(symbol)
            results["stock_data"] = True
            logger.info(f"[Provider] Stock data updated for {symbol}")
            time.sleep(1)  # FMP rate limiting (0.2초면 충분하지만 안전 마진)
        except Exception as e:
            logger.error(f"[Provider] Failed to update stock data for {symbol}: {e}")

        # 2. 가격 데이터 업데이트
        try:
            logger.info(f"[Provider] Updating prices for {symbol}")
            price_result = service.update_historical_prices(symbol, days=730)
            results["prices"] = True
            logger.info(f"[Provider] Prices updated for {symbol}: {price_result}")
            time.sleep(1)
        except Exception as e:
            logger.error(f"[Provider] Failed to update prices for {symbol}: {e}")

        # 3. 재무제표 업데이트
        try:
            logger.info(f"[Provider] Updating financial statements for {symbol}")
            financial_result = service.update_financial_statements(symbol)
            results["financials"] = True
            logger.info(
                f"[Provider] Financials updated for {symbol}: {financial_result}"
            )
        except Exception as e:
            logger.error(f"[Provider] Failed to update financials for {symbol}: {e}")

        # 캐시 무효화
        cache.delete(f"stock_quote_{symbol}")
        cache.delete(f"overview_{symbol}")
        cache.delete(f"chart_{symbol}_daily_1d")

        success_count = sum(1 for v in results.values() if v is True)
        return f"[Provider] Success: {success_count}/3 for {symbol}"

    except Exception as e:
        logger.error(f"[Provider] Task failed for {symbol}: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task
def update_realtime_with_provider(symbols=None):
    """
    Provider를 사용한 실시간 가격 업데이트

    Args:
        symbols: 업데이트할 심볼 리스트 (없으면 포트폴리오 종목)

    Returns:
        결과 문자열
    """
    try:
        from packages.shared.api_request.stock_service import get_stock_service

        if not symbols:
            from packages.shared.users.models import Portfolio

            symbols = list(
                Portfolio.objects.values_list("stock__symbol", flat=True).distinct()[
                    :10
                ]
            )

        if not symbols:
            return "[Provider] No symbols to update"

        service = get_stock_service()

        stats = {"updated": 0, "cached": 0, "errors": 0}

        for symbol in symbols:
            try:
                result = service.update_previous_close(symbol, force=False)

                if result["status"] == "cached":
                    stats["cached"] += 1
                    logger.info(f"[Provider] Cached: {symbol}")
                elif result["status"] == "updated":
                    stats["updated"] += 1
                    logger.info(
                        f"[Provider] Updated: {symbol} @ ${result.get('price', 0):.2f}"
                    )
                    cache.delete(f"stock_quote_{symbol}")
                    if stats["updated"] < len(symbols):
                        time.sleep(1)
                else:
                    stats["errors"] += 1
                    logger.error(
                        f"[Provider] Error: {symbol} - {result.get('message')}"
                    )

            except Exception as e:
                stats["errors"] += 1
                logger.error(f"[Provider] Exception for {symbol}: {e}")

        return f"[Provider] Updated: {stats['updated']}, Cached: {stats['cached']}, Errors: {stats['errors']}"

    except Exception as e:
        logger.error(f"[Provider] Task failed: {e}")
        return f"[Provider] Error: {e}"


# ============================================================
# S&P 500 동기화 태스크
# ============================================================


@shared_task(bind=True, max_retries=3)
def sync_sp500_constituents(self):
    """
    S&P 500 구성 종목 동기화 (월 1회)

    FMP API에서 최신 S&P 500 구성 종목을 가져와 DB에 저장.
    없어진 종목은 is_active=False로 변경.
    """
    try:
        from packages.shared.stocks.services.sp500_service import SP500Service

        service = SP500Service()
        result = service.sync_constituents()

        logger.info(f"S&P 500 구성 종목 동기화 완료: {result}")
        return result

    except Exception as e:
        logger.error(f"S&P 500 구성 종목 동기화 실패: {e}")
        raise self.retry(exc=e, countdown=300 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3, soft_time_limit=1800, time_limit=1860)
def sync_sp500_eod_prices(self, target_date=None):
    """
    S&P 500 전종목 EOD 가격 동기화 (매일 장 마감 후)

    Args:
        target_date: 대상 날짜 (YYYY-MM-DD 문자열, 기본: 오늘)
    """
    try:
        from datetime import date as date_type

        from packages.shared.stocks.services.sp500_eod_service import SP500EODService

        target = None
        if target_date:
            target = date_type.fromisoformat(target_date)

        service = SP500EODService()
        result = service.sync_eod_prices(target_date=target)

        logger.info(f"S&P 500 EOD 동기화 완료: {result}")
        return result

    except Exception as e:
        logger.error(f"S&P 500 EOD 동기화 실패: {e}")
        raise self.retry(exc=e, countdown=300 * (self.request.retries + 1))


@shared_task(
    name="update-sp500-change-percent",
    max_retries=2,
    soft_time_limit=120,
    time_limit=150,
)
def update_sp500_change_percent():
    """
    DailyPrice 최신 2일에서 Stock.change_percent를 일괄 계산.
    FMP API 호출 없음 — 이미 동기화된 DailyPrice 데이터 활용.
    sync_sp500_eod_prices() 직후 실행.
    """
    from packages.shared.stocks.models import DailyPrice, Stock

    latest_dates = list(
        DailyPrice.objects.order_by("-date")
        .values_list("date", flat=True)
        .distinct()[:2]
    )
    if len(latest_dates) < 2:
        logger.warning("update_sp500_change_percent: 최신 2일 데이터 부족")
        return 0

    today, prev = latest_dates[0], latest_dates[1]

    # 전일 종가 map (bulk query 1회)
    prev_map = dict(
        DailyPrice.objects.filter(date=prev).values_list("stock_id", "close_price")
    )

    # 오늘 종가 + 거래량 (bulk query 1회, list()로 메모리에 로드)
    today_data = list(
        DailyPrice.objects.filter(date=today).values_list(
            "stock_id", "close_price", "volume"
        )
    )

    # stock_id → Stock 인스턴스 bulk 조회 (1 query)
    stock_ids = [row[0] for row in today_data]
    stock_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=stock_ids)}

    stocks_to_update = []
    for stock_id, close_price, volume in today_data:
        prev_close = prev_map.get(stock_id)
        if not prev_close or prev_close == 0:
            continue
        stock = stock_map.get(stock_id)
        if not stock:
            continue
        pct = (float(close_price) - float(prev_close)) / float(prev_close) * 100
        stock.change_percent = f"{pct:+.2f}%"
        stock.real_time_price = close_price
        stock.volume = volume
        stocks_to_update.append(stock)

    if stocks_to_update:
        Stock.objects.bulk_update(
            stocks_to_update,
            ["change_percent", "real_time_price", "volume"],
            batch_size=100,
        )

    logger.info(
        f"update_sp500_change_percent: {len(stocks_to_update)} stocks updated (date={today})"
    )
    return len(stocks_to_update)


@shared_task(rate_limit="6/m")
def update_financials_with_provider(symbol):
    """
    Provider를 사용한 재무제표 업데이트

    Args:
        symbol: 주식 심볼

    Returns:
        결과 문자열
    """
    try:
        from packages.shared.api_request.stock_service import get_stock_service

        service = get_stock_service()
        symbol = symbol.upper().strip()

        logger.info(f"[Provider] Updating financials for {symbol}")

        with transaction.atomic():
            result = service.update_financial_statements(symbol)

        logger.info(f"[Provider] Financials updated for {symbol}: {result}")
        return f"[Provider] Success: {symbol} - {result}"

    except Exception as e:
        logger.error(f"[Provider] Failed for {symbol}: {e}")


# ============================================================
# EOD Dashboard Pipeline 태스크
# ============================================================


@shared_task(bind=True, max_retries=2, soft_time_limit=600, time_limit=660)
def run_eod_pipeline(self, target_date=None):
    """
    EOD 시그널 파이프라인 전체 실행.
    idempotent — 같은 날짜로 재실행해도 안전 (bulk_create ON CONFLICT DO UPDATE).

    Args:
        target_date: 대상 날짜 (YYYY-MM-DD 문자열, 기본: 직전 거래일)
    """
    try:
        from datetime import date as date_type

        from packages.shared.stocks.services.eod_pipeline import EODPipeline

        target = None
        if target_date:
            target = date_type.fromisoformat(target_date)

        pipeline = EODPipeline()
        log = pipeline.run(target_date=target)

        logger.info(
            f"EOD Pipeline 완료: {log.date} [{log.status}] {log.total_duration_seconds:.1f}s"
        )
        return {
            "date": str(log.date),
            "status": log.status,
            "duration": log.total_duration_seconds,
            "run_id": str(log.run_id),
        }

    except Exception as e:
        logger.error(f"EOD Pipeline 태스크 실패: {e}")
        raise self.retry(exc=e, countdown=120 * (self.request.retries + 1))


@shared_task
def backfill_signal_accuracy(lookback_days=10):
    """
    시그널 정확도 소급 계산.
    과거 시그널의 1일/5일/20일 수익률을 업데이트.
    update_or_create로 멱등.

    Args:
        lookback_days: 소급 대상 일수 (기본: 10일)
    """
    from datetime import date as date_type
    from datetime import timedelta
    from decimal import Decimal

    from packages.shared.stocks.models import DailyPrice, EODSignal, SignalAccuracy

    target_dates = []
    today = date_type.today()

    for i in range(1, lookback_days + 1):
        d = today - timedelta(days=i)
        if d.weekday() < 5:  # 주말 제외
            target_dates.append(d)

    total_updated = 0

    for signal_date in target_dates:
        signals = EODSignal.objects.filter(date=signal_date).select_related("stock")

        for signal in signals:
            for sig in signal.signals:
                sig_id = sig.get("id", "")
                sig_value = sig.get("value", 0)

                # 이미 완전히 채워진 레코드는 스킵
                existing = SignalAccuracy.objects.filter(
                    stock=signal.stock,
                    signal_date=signal_date,
                    signal_tag=sig_id,
                ).first()

                if existing and existing.return_20d is not None:
                    continue

                # 수익률 계산
                returns = {}
                for days, field in [
                    (1, "return_1d"),
                    (5, "return_5d"),
                    (20, "return_20d"),
                ]:
                    future_date = signal_date + timedelta(days=days)
                    future_price = (
                        DailyPrice.objects.filter(
                            stock=signal.stock,
                            date__gte=future_date,
                        )
                        .order_by("date")
                        .first()
                    )

                    if future_price and signal.close_price:
                        ret = (
                            (
                                float(future_price.close_price)
                                - float(signal.close_price)
                            )
                            / float(signal.close_price)
                            * 100
                        )
                        returns[field] = round(ret, 2)

                if not returns:
                    continue

                # SPY 수익률 (excess 계산용)
                spy_returns = {}
                for days, field in [
                    (1, "excess_1d"),
                    (5, "excess_5d"),
                    (20, "excess_20d"),
                ]:
                    future_date = signal_date + timedelta(days=days)
                    spy_price_at_signal = DailyPrice.objects.filter(
                        stock_id="SPY", date=signal_date
                    ).first()
                    spy_price_future = (
                        DailyPrice.objects.filter(stock_id="SPY", date__gte=future_date)
                        .order_by("date")
                        .first()
                    )

                    ret_field = f"return_{days}d"
                    if (
                        spy_price_at_signal
                        and spy_price_future
                        and ret_field in returns
                    ):
                        spy_ret = (
                            (
                                float(spy_price_future.close_price)
                                - float(spy_price_at_signal.close_price)
                            )
                            / float(spy_price_at_signal.close_price)
                            * 100
                        )
                        spy_returns[field] = round(returns[ret_field] - spy_ret, 2)

                SignalAccuracy.objects.update_or_create(
                    stock=signal.stock,
                    signal_date=signal_date,
                    signal_tag=sig_id,
                    defaults={
                        "signal_value": float(sig_value) if sig_value else 0,
                        "close_at_signal": signal.close_price,
                        "market_cap": signal.market_cap,
                        "sector": signal.sector,
                        **returns,
                        **spy_returns,
                    },
                )
                total_updated += 1

    logger.info(f"Signal accuracy backfill 완료: {total_updated} records updated")
    return {"updated": total_updated, "dates_checked": len(target_dates)}


# ============================================================
# 한글 기업 개요 생성 태스크
# ============================================================


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 5,
    soft_time_limit=30,
    time_limit=60,
)
def generate_korean_overview(self, symbol: str, force: bool = False):
    """
    단일 종목 한글 개요 생성 태스크

    Usage:
        generate_korean_overview.delay('AAPL')
    """
    try:
        from packages.shared.stocks.services.korean_overview_service import (
            KoreanOverviewService,
        )

        service = KoreanOverviewService()
        overview = service.generate_for_stock(symbol, force=force)

        return {
            "symbol": symbol,
            "status": "success",
            "generated_at": str(overview.generated_at),
        }
    except Exception as exc:
        logger.exception(f"generate_korean_overview failed for {symbol}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=1,
    soft_time_limit=7200,  # 2시간
    time_limit=7260,
)
def bulk_generate_korean_overviews(self, batch_size: int = 50, force: bool = False):
    """
    S&P 500 한글 개요 배치 생성 태스크

    월 1회 실행. batch_size 단위로 처리.

    Usage:
        bulk_generate_korean_overviews.delay()
        bulk_generate_korean_overviews.delay(force=True)  # 전체 재생성
    """
    try:
        from packages.shared.stocks.services.korean_overview_service import (
            KoreanOverviewService,
        )

        service = KoreanOverviewService()
        result = service.batch_generate(force=force)

        logger.info(f"bulk_generate_korean_overviews completed: {result}")
        return result
    except Exception as exc:
        logger.exception(f"bulk_generate_korean_overviews failed: {exc}")
        raise self.retry(exc=exc)


# ============================================================
# EVT 트랙 — 이벤트 캘린더 수집 (설계 앵커 docs/design/event_calendar_design.md §3)
# 성분 4개(earnings 선행 45×2 청킹 / dividends 90 / splits 90 / earnings 트레일링 10),
# 성분별 try/except 격리. dry_run=True: fetch·정규화·would-be 카운터만(DB 쓰기 0).
# D-EVT-SCOPE-U: 전량 저장(유니버스 필터 없음) → apps 모델 무의존(shared 경계 유지).
# ============================================================

# 청킹 규약(§3-2): earnings 선행 90일 = 45일 2청크. 갭·중복 없음.
_EARNINGS_CHUNK_DAYS = 45
_FORWARD_DAYS = 90
_TRAILING_DAYS = 10


def _chunk_windows(d0, total_days, chunk_days):
    """[d0, d0+total_days) 를 chunk_days 단위로 분할. 갭·중복 없는 (from, to) 날짜쌍 목록.

    예: d0, total=90, chunk=45 → [(d0, d0+44), (d0+45, d0+89)]. to는 inclusive.
    """
    windows = []
    offset = 0
    while offset < total_days:
        w_from = d0 + _dt.timedelta(days=offset)
        span = min(chunk_days, total_days - offset)
        w_to = d0 + _dt.timedelta(days=offset + span - 1)
        windows.append((w_from, w_to))
        offset += span
    return windows


# 필드 용량 가드(D-EVT-ROBUST-1). |value| ≥ max_abs = 정수부 자릿수 초과 → 오버플로.
# eps DecimalField(12,4)→10^8 · revenue(20,2)→10^18 · dividend(12,6)→10^6 · split(15,6)→10^9.
_EPS_MAX_ABS = 10 ** 8
_REVENUE_MAX_ABS = 10 ** 18
_DIVIDEND_MAX_ABS = 10 ** 6
_SPLIT_MAX_ABS = 10 ** 9


def _safe_decimal(value, max_abs, symbol, field, counter):
    """필드 용량 초과·비수치 값 → None(사실 보존: 행은 유지, 필드만 null). counter['nulled'] += 1 + 로그.

    FMP 이상치(예: ADTX epsEstimated=-2.2×10^11)를 원천 무해화. 정상 None/빈값은 카운트 안 함.
    """
    if value is None or value == "":
        return None
    try:
        d = _decimal.Decimal(str(value))
    except (_decimal.InvalidOperation, ValueError, TypeError):
        d = None
    if d is None or d.is_nan() or d.is_infinite() or abs(d) >= max_abs:
        counter["nulled"] += 1
        logger.warning(
            "collect_calendar_events 필드 null(용량초과/비수치) [%s %s=%r]", symbol, field, value,
        )
        return None
    return d


def _normalize_earnings(row):
    """FMP earnings-calendar 행 → CalendarEvent 필드. session 필드 없음(SURVEY-0) → UNKNOWN.

    반환 dict의 '_nulled' = 이 행에서 용량초과로 null 처리된 필드 수(성분 집계용).
    """
    from .models import CalendarEvent

    d = _parse_fmp_date(row.get("date"))
    if d is None or not row.get("symbol"):
        return None
    sym = str(row["symbol"]).upper()
    cnt = {"nulled": 0}
    eps_actual = _safe_decimal(row.get("epsActual"), _EPS_MAX_ABS, sym, "eps_actual", cnt)
    return {
        "event_type": CalendarEvent.EventType.EARNINGS,
        "symbol": sym,
        "event_date": d,
        "defaults": {
            "eps_estimated": _safe_decimal(row.get("epsEstimated"), _EPS_MAX_ABS, sym, "eps_estimated", cnt),
            "eps_actual": eps_actual,
            "revenue_estimated": _safe_decimal(row.get("revenueEstimated"), _REVENUE_MAX_ABS, sym, "revenue_estimated", cnt),
            "revenue_actual": _safe_decimal(row.get("revenueActual"), _REVENUE_MAX_ABS, sym, "revenue_actual", cnt),
            "session": CalendarEvent.Session.UNKNOWN,  # 응답에 세션/시각 필드 부재
            "source": "fmp",
        },
        "fmp_last_updated": row.get("lastUpdated"),
        "has_actual": eps_actual is not None,
        "_nulled": cnt["nulled"],
    }


def _normalize_dividend(row):
    from .models import CalendarEvent

    d = _parse_fmp_date(row.get("date"))
    if d is None or not row.get("symbol"):
        return None
    sym = str(row["symbol"]).upper()
    cnt = {"nulled": 0}
    return {
        "event_type": CalendarEvent.EventType.DIVIDEND,
        "symbol": sym,
        "event_date": d,  # ex-date
        "defaults": {
            "dividend_amount": _safe_decimal(row.get("dividend"), _DIVIDEND_MAX_ABS, sym, "dividend_amount", cnt),
            "payment_date": _parse_fmp_date(row.get("paymentDate")),
            "record_date": _parse_fmp_date(row.get("recordDate")),
            "frequency": row.get("frequency") or "",
            "source": "fmp",
        },
        "fmp_last_updated": None,
        "has_actual": False,
        "_nulled": cnt["nulled"],
    }


def _normalize_split(row):
    from .models import CalendarEvent

    d = _parse_fmp_date(row.get("date"))
    if d is None or not row.get("symbol"):
        return None
    sym = str(row["symbol"]).upper()
    cnt = {"nulled": 0}
    return {
        "event_type": CalendarEvent.EventType.SPLIT,
        "symbol": sym,
        "event_date": d,
        "defaults": {
            "split_numerator": _safe_decimal(row.get("numerator"), _SPLIT_MAX_ABS, sym, "split_numerator", cnt),
            "split_denominator": _safe_decimal(row.get("denominator"), _SPLIT_MAX_ABS, sym, "split_denominator", cnt),
            "source": "fmp",
        },
        "fmp_last_updated": None,
        "has_actual": False,
        "_nulled": cnt["nulled"],
    }


def _parse_fmp_date(value):
    if not value:
        return None
    try:
        return _dt.date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _persist_event(norm, dry_run):
    """정규화 1행 → 원장 upsert(비-dry_run). 반환: 'created'|'updated'|'occurred'|'would_write'.

    dry_run이면 DB 무접촉 — 'would_write'만 반환.
    """
    from .models import CalendarEvent

    if dry_run:
        return "would_write"

    defaults = dict(norm["defaults"])
    if norm.get("fmp_last_updated"):
        defaults["fmp_last_updated"] = _parse_fmp_datetime(norm["fmp_last_updated"])

    obj, created = CalendarEvent.record_observation(
        event_type=norm["event_type"],
        symbol=norm["symbol"],
        event_date=norm["event_date"],
        defaults=defaults,
    )
    # eps_actual null→값 전이 시 status=occurred (downgrade 없음).
    if (
        norm["event_type"] == CalendarEvent.EventType.EARNINGS
        and norm.get("has_actual")
        and obj.status != CalendarEvent.Status.OCCURRED
    ):
        obj.status = CalendarEvent.Status.OCCURRED
        obj.save(update_fields=["status"])
        return "occurred"
    return "created" if created else "updated"


def _parse_fmp_datetime(value):
    from django.utils.dateparse import parse_datetime

    if not value:
        return None
    try:
        return parse_datetime(str(value)) or None
    except (ValueError, TypeError):
        return None


# 적응형 이분 가드(§3 캡 방어 원안 복원, D-EVT-CAP-1).
_BISECT_MAX_DEPTH = 4          # 재귀 최대 깊이
_BISECT_RUN_CALL_CAP = 12      # 런당 추가 콜 상한(성분 전체 공유)
_BISECT_MIN_SPAN_DAYS = 3      # 창 ≤3일에서도 절단이면 실패 마킹(밀도상 사실상 불능)


def _fetch_with_bisect(fetcher, w_from, w_to, budget, depth=0):
    """fetch → 절단(count≥4000)이면 창 이분 재귀. 서브창 병합은 upsert 멱등키가 흡수.

    guards(하드): 깊이 ≤ _BISECT_MAX_DEPTH · 런당 추가콜 ≤ _BISECT_RUN_CALL_CAP ·
    창 ≤ _BISECT_MIN_SPAN_DAYS 에서도 절단이면 실패 마킹(재귀 종료).
    반환: (rows, meta{bisect_depth, extra_calls, failed:[(from,to)...]}).
    """
    from packages.shared.api_request.providers.fmp.calendar_cap import detect_truncation

    rows = fetcher(w_from.isoformat(), w_to.isoformat())
    if not detect_truncation(w_from.isoformat(), w_to.isoformat(), rows):
        return rows, {"bisect_depth": depth, "extra_calls": 0, "failed": []}

    span_days = (w_to - w_from).days
    # 종료 가드: 깊이·최소창 초과 → 실패 마킹(더 못 쪼갬).
    if depth >= _BISECT_MAX_DEPTH or span_days <= _BISECT_MIN_SPAN_DAYS:
        logger.warning(
            "collect_calendar_events 이분 실패 마킹 [%s..%s] depth=%d span=%dd (캡 잔존)",
            w_from, w_to, depth, span_days,
        )
        return rows, {"bisect_depth": depth, "extra_calls": 0, "failed": [(w_from.isoformat(), w_to.isoformat())]}
    # 콜 예산 가드.
    if budget["extra"] < 2:
        logger.warning(
            "collect_calendar_events 이분 콜 상한 도달 [%s..%s] — 실패 마킹", w_from, w_to,
        )
        return rows, {"bisect_depth": depth, "extra_calls": 0, "failed": [(w_from.isoformat(), w_to.isoformat())], "budget_exhausted": True}

    mid = w_from + _dt.timedelta(days=span_days // 2)
    budget["extra"] -= 2
    left_rows, lmeta = _fetch_with_bisect(fetcher, w_from, mid, budget, depth + 1)
    right_rows, rmeta = _fetch_with_bisect(fetcher, mid + _dt.timedelta(days=1), w_to, budget, depth + 1)
    return left_rows + right_rows, {
        "bisect_depth": max(lmeta["bisect_depth"], rmeta["bisect_depth"]),
        "extra_calls": 2 + lmeta["extra_calls"] + rmeta["extra_calls"],
        "failed": lmeta["failed"] + rmeta["failed"],
    }


@shared_task(bind=True, max_retries=3, soft_time_limit=600, time_limit=660)
def collect_calendar_events(self, as_of=None, dry_run=False):
    """이벤트 캘린더 수집 (EVT 트랙). 성분별 격리 + 캡 감지 + 조건부 stale 스윕.

    as_of: ET 기준 기준일 문자열(YYYY-MM-DD). 기본 = UTC 오늘(기계 시계, #89).
    dry_run: True면 fetch·정규화·would-be 카운터까지, DB 쓰기 0.
    반환: 성분별 {fetched, written, truncated, ok} + stale_swept 요약 dict.
    """
    from django.conf import settings
    from django.db import transaction
    from django.utils import timezone

    from packages.shared.api_request.providers.fmp.client import FMPClient
    from .models import CalendarEvent

    run_start = timezone.now()  # UTC 앵커(#89). 재관측 last_seen_at >= run_start.
    d0 = _parse_fmp_date(as_of) or run_start.date()

    client = FMPClient(api_key=settings.FMP_API_KEY)
    result = {"as_of": d0.isoformat(), "dry_run": dry_run, "components": {}}
    # 이분 추가콜 예산 — 런 전체 공유(성분 간 합산).
    bisect_budget = {"extra": _BISECT_RUN_CALL_CAP}
    # 성분별 fetch 성공 여부 — stale 스윕 가드용(유형 단위).
    fetch_ok = {
        CalendarEvent.EventType.EARNINGS: True,
        CalendarEvent.EventType.DIVIDEND: True,
        CalendarEvent.EventType.SPLIT: True,
    }
    # 유형별 skip 누적 — skipped>0이면 그 유형 stale 스윕 생략(미persist 행 오탐 방지, A-2).
    type_skipped = {
        CalendarEvent.EventType.EARNINGS: 0,
        CalendarEvent.EventType.DIVIDEND: 0,
        CalendarEvent.EventType.SPLIT: 0,
    }

    def _run_component(name, fetcher, normalizer, etype, w_from, w_to):
        rec = {
            "fetched": 0, "written": 0, "skipped": 0, "nulled": 0,
            "truncated": False, "ok": True, "anomaly": False,
            "bisect_depth": 0, "extra_calls": 0, "failed_subwindows": [],
        }
        try:
            # 적응형 이분: 절단 시 창을 쪼개 재수집(§3 캡 방어, D-EVT-CAP-1).
            rows, meta = _fetch_with_bisect(fetcher, w_from, w_to, bisect_budget)
            rec["fetched"] = len(rows)
            rec["bisect_depth"] = meta["bisect_depth"]
            rec["extra_calls"] = meta["extra_calls"]
            rec["failed_subwindows"] = meta["failed"]
            # 이분 후에도 남은 실패 서브창이 있으면 truncated=True(소실 잔존 = 관찰/알림).
            rec["truncated"] = bool(meta["failed"])
            for row in rows:
                norm = normalizer(row)
                if norm is None:
                    continue
                rec["nulled"] += norm.pop("_nulled", 0)
                # 행-레벨 격리(A-2): 한 행 예외가 성분 전체를 잃지 않게. atomic으로 트랜잭션 오염 차단.
                try:
                    with transaction.atomic():
                        _persist_event(norm, dry_run)
                    rec["written"] += 1
                except Exception as row_exc:
                    rec["skipped"] += 1
                    type_skipped[etype] += 1
                    logger.warning(
                        "collect_calendar_events 행 skip [%s %s]: %s",
                        norm["symbol"], norm["event_date"], row_exc,
                    )
            # 이상 임계(A-3): nulled+skipped > max(50, 행수 1%) → 경고(스키마 drift 신호, HALT 아님).
            if rec["nulled"] + rec["skipped"] > max(50, rec["fetched"] // 100):
                rec["anomaly"] = True
                logger.warning(
                    "collect_calendar_events 이상 임계 초과 [%s] nulled=%d skipped=%d of fetched=%d",
                    name, rec["nulled"], rec["skipped"], rec["fetched"],
                )
        except Exception as exc:  # 성분 격리(fetch 단계)
            rec["ok"] = False
            fetch_ok[etype] = False
            logger.warning("collect_calendar_events 성분 실패 [%s]: %s", name, exc)
        result["components"][name] = rec
        return rec

    # 성분 1·2: earnings 선행 45×2 청킹
    fwd_windows = _chunk_windows(d0, _FORWARD_DAYS, _EARNINGS_CHUNK_DAYS)
    for i, (wf, wt) in enumerate(fwd_windows, start=1):
        r = _run_component(
            f"earnings_fwd_{i}", client.get_earnings_calendar, _normalize_earnings,
            CalendarEvent.EventType.EARNINGS, wf, wt,
        )
        if not r["ok"]:
            fetch_ok[CalendarEvent.EventType.EARNINGS] = False

    # 성분 3: dividends 90일 단일
    _run_component(
        "dividends", client.get_dividends_calendar, _normalize_dividend,
        CalendarEvent.EventType.DIVIDEND, d0, d0 + _dt.timedelta(days=_FORWARD_DAYS - 1),
    )
    # 성분 4: splits 90일 단일
    _run_component(
        "splits", client.get_splits_calendar, _normalize_split,
        CalendarEvent.EventType.SPLIT, d0, d0 + _dt.timedelta(days=_FORWARD_DAYS - 1),
    )
    # 성분 5: earnings 트레일링 10일 (actual 채움 → occurred 전이)
    _run_component(
        "earnings_trailing", client.get_earnings_calendar, _normalize_earnings,
        CalendarEvent.EventType.EARNINGS, d0 - _dt.timedelta(days=_TRAILING_DAYS), d0,
    )

    # stale 스윕(비-dry_run): 선행 창 scheduled 중 금회 미관측 → stale.
    # 가드(하드): 해당 유형 fetch 성공 AND skip 0 일 때만 스윕
    # (API 실패발 대량 오염 + 미persist 행 last_seen 미갱신 오탐 차단, A-2).
    swept = {}
    if not dry_run:
        fwd_end = d0 + _dt.timedelta(days=_FORWARD_DAYS - 1)
        for etype in (
            CalendarEvent.EventType.EARNINGS,
            CalendarEvent.EventType.DIVIDEND,
            CalendarEvent.EventType.SPLIT,
        ):
            if not fetch_ok[etype]:
                swept[etype] = "skipped(fetch_failed)"
                continue
            if type_skipped[etype] > 0:
                swept[etype] = f"skipped(rows_skipped={type_skipped[etype]})"
                continue
            n = CalendarEvent.objects.filter(
                event_type=etype,
                status=CalendarEvent.Status.SCHEDULED,
                event_date__gte=d0,
                event_date__lte=fwd_end,
                last_seen_at__lt=run_start,
            ).update(status=CalendarEvent.Status.STALE)
            swept[etype] = n
    result["stale_swept"] = swept

    logger.info("collect_calendar_events done: %s", result)
    return result
