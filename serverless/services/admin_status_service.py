"""
Admin Dashboard Status Service

관리자 대시보드를 위한 데이터 집계 서비스.
여러 앱의 모델을 import하여 시스템 상태를 한눈에 파악합니다.
"""
import logging
from datetime import date, timedelta
from django.utils import timezone
from django.db import connection
from django.db.models import Count, Max, Avg
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ========================================
# 거래일 판정 헬퍼
# ========================================

US_MARKET_HOLIDAYS_2026 = {
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # MLK Day
    date(2026, 2, 16),  # Presidents' Day
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 7, 3),   # Independence Day (observed)
    date(2026, 9, 7),   # Labor Day
    date(2026, 11, 26), # Thanksgiving
    date(2026, 12, 25), # Christmas
}


def is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in US_MARKET_HOLIDAYS_2026


def last_trading_day(before: date = None) -> date:
    """
    데이터가 존재할 수 있는 가장 최근 거래일을 반환한다.

    미국 장 마감(ET 16:00 ≈ UTC 21:00) 이전이면
    오늘 데이터가 아직 확정되지 않았으므로 전 거래일을 반환한다.
    """
    from datetime import datetime, timezone as dt_tz

    now_utc = datetime.now(dt_tz.utc)
    # UTC 기준 날짜 사용 (로컬 시간대와 UTC 날짜 불일치 방지)
    d = before or now_utc.date()

    # before 인자 없이 호출된 경우에만 시간 보정 적용
    if before is None:
        # UTC 21:00 = ET 16:00 (장 마감). 여유 1시간 → UTC 22:00 이전이면 오늘 데이터 미확정
        if now_utc.hour < 22 and is_trading_day(d):
            d -= timedelta(days=1)

    if not is_trading_day(d):
        d -= timedelta(days=1)
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d


class AdminStatusService:
    """관리자 대시보드 상태 집계 서비스"""

    # ========================================
    # 1) 개요 탭
    # ========================================
    @staticmethod
    def get_overview_summary() -> dict:
        from stocks.models import Stock, DailyPrice, SP500Constituent
        from serverless.models import (
            MarketMover, StockKeyword, MarketBreadth,
        )
        from news.models import NewsArticle, DailyNewsKeyword

        last_td = last_trading_day()
        now = timezone.now()
        last_24h = now - timedelta(hours=24)

        # 종목 수
        total_stocks = Stock.objects.count()
        sp500_active = SP500Constituent.objects.filter(is_active=True).count()
        with_todays_price = DailyPrice.objects.filter(
            date=last_td
        ).values('stock').distinct().count()
        coverage_pct = round(
            (with_todays_price / sp500_active * 100) if sp500_active > 0 else 0, 1
        )

        # Celery 24시간 통계
        tasks_24h = _get_task_stats_24h(last_24h)

        # 데이터 신선도
        data_freshness = {
            'last_trading_day': last_td.isoformat(),
            'is_today_trading_day': is_trading_day(date.today()),
            'movers': MarketMover.objects.filter(date=last_td).exists(),
            'keywords': StockKeyword.objects.filter(
                date=last_td, status='completed'
            ).exists(),
            'breadth': MarketBreadth.objects.filter(date=last_td).exists(),
            'news_keywords': DailyNewsKeyword.objects.filter(
                date=last_td, status='completed'
            ).exists(),
        }

        # 뉴스 통계
        articles_24h = NewsArticle.objects.filter(
            created_at__gte=last_24h
        ).count()

        # 이슈 감지
        issues = AdminStatusService.detect_issues()

        return {
            'summary': {
                'stocks': {
                    'total': total_stocks,
                    'sp500_active': sp500_active,
                    'with_todays_price': with_todays_price,
                    'coverage_pct': coverage_pct,
                },
                'tasks_24h': tasks_24h,
                'data_freshness': data_freshness,
                'news': {'articles_24h': articles_24h},
            },
            'issues': issues,
        }

    # ========================================
    # 2) 문제 자동 감지 (10개 규칙)
    # ========================================
    @staticmethod
    def detect_issues() -> list:
        from stocks.models import DailyPrice, SP500Constituent
        from serverless.models import (
            MarketMover, StockKeyword, MarketBreadth,
            SectorPerformance, ETFProfile, LLMExtractedRelation,
        )
        from news.models import DailyNewsKeyword

        issues = []
        last_td = last_trading_day()
        now = timezone.now()

        # 1. SP500 가격 누락 >10개
        try:
            sp500_symbols = set(
                SP500Constituent.objects.filter(is_active=True)
                .values_list('symbol', flat=True)
            )
            price_symbols = set(
                DailyPrice.objects.filter(date=last_td)
                .values_list('stock_id', flat=True)
            )
            missing = sp500_symbols - price_symbols
            if len(missing) > 10:
                issues.append({
                    'severity': 'error',
                    'category': 'stocks',
                    'title': f'SP500 가격 누락 {len(missing)}개',
                    'detail': f'{last_td} 기준 {len(missing)}개 종목 가격 미수집',
                    'symbols': sorted(list(missing))[:20],
                })
        except Exception as e:
            logger.warning(f"Issue detect #1 error: {e}")

        # 2. MarketMover 0건
        try:
            mover_count = MarketMover.objects.filter(date=last_td).count()
            if mover_count == 0:
                issues.append({
                    'severity': 'error',
                    'category': 'market_pulse',
                    'title': 'MarketMover 0건',
                    'detail': f'{last_td} Market Movers 데이터 없음',
                })
            # 3. MarketMover 불완전 <30건
            elif mover_count < 30:
                issues.append({
                    'severity': 'warning',
                    'category': 'market_pulse',
                    'title': f'MarketMover 불완전 ({mover_count}건)',
                    'detail': f'{last_td} Market Movers {mover_count}건 (기대: 60건)',
                })
        except Exception as e:
            logger.warning(f"Issue detect #2-3 error: {e}")

        # 4. 키워드 생성 실패 >5건
        try:
            failed_keywords = StockKeyword.objects.filter(
                date=last_td, status='failed'
            ).count()
            if failed_keywords > 5:
                issues.append({
                    'severity': 'warning',
                    'category': 'market_pulse',
                    'title': f'키워드 생성 실패 {failed_keywords}건',
                    'detail': f'{last_td} AI 키워드 생성 실패 {failed_keywords}건',
                })
        except Exception as e:
            logger.warning(f"Issue detect #4 error: {e}")

        # 5. MarketBreadth 미생성
        try:
            if not MarketBreadth.objects.filter(date=last_td).exists():
                issues.append({
                    'severity': 'warning',
                    'category': 'screener',
                    'title': 'MarketBreadth 미생성',
                    'detail': f'{last_td} 시장 건강도 데이터 없음',
                })
        except Exception as e:
            logger.warning(f"Issue detect #5 error: {e}")

        # 6. SectorPerformance <11개
        try:
            sector_count = SectorPerformance.objects.filter(date=last_td).count()
            if sector_count < 11:
                issues.append({
                    'severity': 'warning',
                    'category': 'screener',
                    'title': f'SectorPerformance {sector_count}/11',
                    'detail': f'{last_td} 섹터 성과 {sector_count}/11개 섹터만 수집',
                })
        except Exception as e:
            logger.warning(f"Issue detect #6 error: {e}")

        # 7. ETF 수집 오류
        try:
            etf_errors = ETFProfile.objects.filter(
                is_active=True
            ).exclude(last_error='').count()
            if etf_errors > 0:
                issues.append({
                    'severity': 'warning',
                    'category': 'chain_sight',
                    'title': f'ETF 수집 오류 {etf_errors}개',
                    'detail': f'활성 ETF 중 {etf_errors}개에 수집 오류 존재',
                })
        except Exception as e:
            logger.warning(f"Issue detect #7 error: {e}")

        # 8. 뉴스 키워드 미생성
        try:
            if not DailyNewsKeyword.objects.filter(
                date=last_td, status='completed'
            ).exists():
                issues.append({
                    'severity': 'warning',
                    'category': 'news',
                    'title': '뉴스 키워드 미생성',
                    'detail': f'{last_td} 일별 뉴스 키워드 미생성',
                })
        except Exception as e:
            logger.warning(f"Issue detect #8 error: {e}")

        # 9. Celery 반복 실패 (6h 내 3회+)
        try:
            from django_celery_results.models import TaskResult
            six_hours_ago = now - timedelta(hours=6)
            repeated_failures = (
                TaskResult.objects.filter(
                    date_done__gte=six_hours_ago,
                    status='FAILURE',
                )
                .values('task_name')
                .annotate(count=Count('id'))
                .filter(count__gte=3)
            )
            for item in repeated_failures:
                issues.append({
                    'severity': 'error',
                    'category': 'system',
                    'title': f'반복 실패: {item["task_name"]}',
                    'detail': f'6시간 내 {item["count"]}회 실패',
                })
        except Exception as e:
            logger.warning(f"Issue detect #9 error: {e}")

        # 10. 만료 LLM 관계 >100건
        try:
            expired_count = LLMExtractedRelation.objects.filter(
                expires_at__lt=now
            ).count()
            if expired_count > 100:
                issues.append({
                    'severity': 'info',
                    'category': 'chain_sight',
                    'title': f'만료 LLM 관계 {expired_count}건',
                    'detail': f'만료된 LLM 추출 관계 {expired_count}건 정리 필요',
                })
        except Exception as e:
            logger.warning(f"Issue detect #10 error: {e}")

        # severity 순 정렬: error > warning > info
        severity_order = {'error': 0, 'warning': 1, 'info': 2}
        issues.sort(key=lambda x: severity_order.get(x['severity'], 3))

        # suggested_action 매핑
        for issue in issues:
            issue['suggested_action'] = _suggest_action(issue)

        return issues

    # ========================================
    # 3) 주식 탭
    # ========================================
    @staticmethod
    def get_stocks_status() -> dict:
        from stocks.models import (
            Stock, DailyPrice, WeeklyPrice,
            BalanceSheet, IncomeStatement, CashFlowStatement,
            SP500Constituent,
        )

        last_td = last_trading_day()

        # SP500
        sp500_active = SP500Constituent.objects.filter(is_active=True).count()
        sp500_latest = SP500Constituent.objects.filter(
            is_active=True
        ).aggregate(latest=Max('updated_at'))

        # DailyPrice
        daily_agg = DailyPrice.objects.aggregate(
            latest_date=Max('date'),
            total_records=Count('id'),
            distinct_stocks=Count('stock', distinct=True),
        )
        # 누락 종목
        sp500_symbols = set(
            SP500Constituent.objects.filter(is_active=True)
            .values_list('symbol', flat=True)
        )
        price_symbols = set(
            DailyPrice.objects.filter(date=last_td)
            .values_list('stock_id', flat=True)
        )
        missing_symbols = sorted(list(sp500_symbols - price_symbols))

        # WeeklyPrice
        weekly_agg = WeeklyPrice.objects.aggregate(
            latest_date=Max('date'),
            total_records=Count('id'),
        )

        # 재무제표
        balance_agg = BalanceSheet.objects.aggregate(
            latest_date=Max('reported_date'),
            total_records=Count('id'),
            distinct_stocks=Count('stock', distinct=True),
        )
        income_agg = IncomeStatement.objects.aggregate(
            latest_date=Max('reported_date'),
            total_records=Count('id'),
            distinct_stocks=Count('stock', distinct=True),
        )
        cashflow_agg = CashFlowStatement.objects.aggregate(
            latest_date=Max('reported_date'),
            total_records=Count('id'),
            distinct_stocks=Count('stock', distinct=True),
        )

        # 신선도 판정
        daily_latest = daily_agg.get('latest_date')
        weekly_latest = weekly_agg.get('latest_date')
        balance_latest = balance_agg.get('latest_date')
        income_latest = income_agg.get('latest_date')
        cashflow_latest = cashflow_agg.get('latest_date')

        today = date.today()
        # 재무제표는 90일(분기) 이내면 정상
        financial_stale_threshold = today - timedelta(days=90)

        return {
            'last_trading_day': last_td.isoformat(),
            'sp500': {
                'active_count': sp500_active,
                'latest_update': _serialize_datetime(sp500_latest.get('latest')),
            },
            'daily_price': {
                'latest_date': _serialize_date(daily_latest),
                'is_fresh': daily_latest == last_td if daily_latest else False,
                'total_records': daily_agg.get('total_records', 0),
                'distinct_stocks': daily_agg.get('distinct_stocks', 0),
                'coverage': len(price_symbols),
                'missing_count': len(missing_symbols),
                'missing_symbols': missing_symbols[:30],
            },
            'weekly_price': {
                'latest_date': _serialize_date(weekly_latest),
                'is_fresh': (
                    weekly_latest >= today - timedelta(days=7)
                    if weekly_latest else False
                ),
                'total_records': weekly_agg.get('total_records', 0),
            },
            'balance_sheet': {
                'latest_date': _serialize_date(balance_latest),
                'is_fresh': (
                    balance_latest >= financial_stale_threshold
                    if balance_latest else False
                ),
                'total_records': balance_agg.get('total_records', 0),
                'distinct_stocks': balance_agg.get('distinct_stocks', 0),
            },
            'income_statement': {
                'latest_date': _serialize_date(income_latest),
                'is_fresh': (
                    income_latest >= financial_stale_threshold
                    if income_latest else False
                ),
                'total_records': income_agg.get('total_records', 0),
                'distinct_stocks': income_agg.get('distinct_stocks', 0),
            },
            'cash_flow': {
                'latest_date': _serialize_date(cashflow_latest),
                'is_fresh': (
                    cashflow_latest >= financial_stale_threshold
                    if cashflow_latest else False
                ),
                'total_records': cashflow_agg.get('total_records', 0),
                'distinct_stocks': cashflow_agg.get('distinct_stocks', 0),
            },
        }

    # ========================================
    # 4) 스크리너 탭
    # ========================================
    @staticmethod
    def get_screener_status() -> dict:
        from serverless.models import (
            MarketBreadth, SectorPerformance,
            ScreenerAlert, AlertHistory,
        )

        last_td = last_trading_day()

        # Market Breadth
        breadth_today = MarketBreadth.objects.filter(date=last_td).first()
        breadth_history = list(
            MarketBreadth.objects.order_by('-date')[:7].values(
                'date', 'breadth_signal', 'advance_decline_ratio',
                'advancing_count', 'declining_count',
            )
        )

        # Sector Performance
        sector_count = SectorPerformance.objects.filter(date=last_td).count()

        # Alerts
        active_alerts = ScreenerAlert.objects.filter(is_active=True).count()
        recent_alerts = list(
            AlertHistory.objects.order_by('-triggered_at')[:10].values(
                'id', 'alert__name', 'triggered_at', 'matched_count',
                'status', 'read_at',
            )
        )

        return {
            'breadth': {
                'today': {
                    'date': last_td.isoformat(),
                    'signal': breadth_today.breadth_signal if breadth_today else None,
                    'advance_decline_ratio': str(breadth_today.advance_decline_ratio) if breadth_today else None,
                    'exists': breadth_today is not None,
                },
                'history': _serialize_queryvalues(breadth_history),
            },
            'sector_performance': {
                'count': sector_count,
                'expected': 11,
                'complete': sector_count >= 11,
            },
            'alerts': {
                'active_count': active_alerts,
                'recent_history': _serialize_queryvalues(recent_alerts),
            },
        }

    # ========================================
    # 5) Market Pulse 탭
    # ========================================
    @staticmethod
    def get_market_pulse_status() -> dict:
        from serverless.models import MarketMover, StockKeyword

        last_td = last_trading_day()

        # Market Movers by type
        mover_stats = list(
            MarketMover.objects.filter(date=last_td)
            .values('mover_type')
            .annotate(count=Count('id'))
        )

        # Keywords
        keyword_stats = list(
            StockKeyword.objects.filter(date=last_td)
            .values('status')
            .annotate(count=Count('id'))
        )

        # Cache checks (실제 macro 서비스가 사용하는 키와 일치)
        fear_greed_cached = cache.get('macro:fear_greed_index') is not None
        market_pulse_cached = cache.get('macro:market_pulse_full') is not None

        # Economic Indicators (from analysis app)
        try:
            from analysis.models import EconomicIndicator
            economic_total = EconomicIndicator.objects.count()
        except Exception:
            economic_total = 0

        return {
            'movers': {
                'date': last_td.isoformat(),
                'by_type': {s['mover_type']: s['count'] for s in mover_stats},
                'total': sum(s['count'] for s in mover_stats),
            },
            'keywords': {
                'date': last_td.isoformat(),
                'by_status': {s['status']: s['count'] for s in keyword_stats},
            },
            'cache': {
                'fear_greed': fear_greed_cached,
                'market_pulse': market_pulse_cached,
            },
            'economic_indicators': {
                'total': economic_total,
            },
        }

    # ========================================
    # 6) 뉴스 탭
    # ========================================
    @staticmethod
    def get_news_status() -> dict:
        from news.models import (
            NewsArticle, DailyNewsKeyword,
            SentimentHistory, NewsEntity,
            NewsCollectionCategory,
        )

        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        # 기사 통계
        total_articles = NewsArticle.objects.count()
        articles_24h = NewsArticle.objects.filter(created_at__gte=last_24h).count()
        articles_7d = NewsArticle.objects.filter(created_at__gte=last_7d).count()

        # 소스 분포 (7일)
        source_distribution = list(
            NewsArticle.objects.filter(created_at__gte=last_7d)
            .values('source')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # 키워드 이력 (7일)
        keyword_history = list(
            DailyNewsKeyword.objects.order_by('-date')[:7].values(
                'date', 'status', 'total_news_count',
            )
        )

        # 감성 분석
        seven_days_ago = (now - timedelta(days=7)).date()
        sentiment_avg = SentimentHistory.objects.filter(
            date__gte=seven_days_ago
        ).aggregate(avg=Avg('avg_sentiment'))

        # 종목 커버리지
        entity_coverage = NewsEntity.objects.filter(
            news__created_at__gte=last_7d
        ).values('symbol').distinct().count()

        # 카테고리 통계
        categories_total = NewsCollectionCategory.objects.count()
        categories_active = NewsCollectionCategory.objects.filter(is_active=True).count()
        by_priority = {}
        for p in ('high', 'medium', 'low'):
            by_priority[p] = NewsCollectionCategory.objects.filter(
                is_active=True, priority=p
            ).count()

        latest_cat = (
            NewsCollectionCategory.objects
            .filter(last_collected_at__isnull=False)
            .order_by('-last_collected_at')
            .first()
        )
        latest_collection = None
        if latest_cat:
            latest_collection = {
                'name': latest_cat.name,
                'collected_at': latest_cat.last_collected_at.isoformat(),
                'article_count': latest_cat.last_article_count,
            }

        return {
            'articles': {
                'total': total_articles,
                'last_24h': articles_24h,
                'last_7d': articles_7d,
            },
            'source_distribution': source_distribution,
            'keyword_history': _serialize_queryvalues(keyword_history),
            'sentiment': {
                'avg_7d': str(sentiment_avg.get('avg')) if sentiment_avg.get('avg') else None,
                'coverage_symbols': entity_coverage,
            },
            'categories': {
                'active': categories_active,
                'total': categories_total,
                'by_priority': by_priority,
                'latest_collection': latest_collection,
            },
        }

    # ========================================
    # 7) 시스템 탭
    # ========================================
    @staticmethod
    def get_system_status() -> dict:
        now = timezone.now()
        last_24h = now - timedelta(hours=24)

        # Celery 태스크 요약
        task_summary = _get_task_summary_24h(last_24h)

        # 최근 실패
        recent_failures = _get_recent_failures(last_24h)

        # Rate Limits
        rate_limits = _get_rate_limits()

        # Cache Stats
        cache_stats = _get_cache_stats()

        # DB 테이블 크기
        db_table_sizes = _get_db_table_sizes()

        # 태스크별 최근 실행 현황
        latest_task_runs = _get_latest_task_runs()

        return {
            'task_summary': task_summary,
            'latest_task_runs': latest_task_runs,
            'recent_failures': recent_failures,
            'rate_limits': rate_limits,
            'cache_stats': cache_stats,
            'db_table_sizes': db_table_sizes,
        }

    @staticmethod
    def get_task_logs(task_name: str = None, task_status: str = None,
                      hours: int = 24, limit: int = 50) -> list:
        try:
            from django_celery_results.models import TaskResult

            cutoff = timezone.now() - timedelta(hours=hours)
            qs = TaskResult.objects.filter(date_done__gte=cutoff)

            if task_name:
                qs = qs.filter(task_name__icontains=task_name)
            if task_status:
                qs = qs.filter(status=task_status)

            qs = qs.order_by('-date_done')[:limit]

            return [
                {
                    'id': str(t.id),
                    'task_id': t.task_id,
                    'task_name': t.task_name or '',
                    'status': t.status,
                    'date_done': t.date_done.isoformat() if t.date_done else None,
                    'worker': t.worker or '',
                    'traceback': t.traceback or '' if t.status == 'FAILURE' else '',
                    'result': str(t.result)[:500] if t.result else '',
                }
                for t in qs
            ]
        except Exception as e:
            logger.error(f"Task logs error: {e}")
            return []


# ========================================
# 헬퍼 함수
# ========================================

def _suggest_action(issue: dict) -> str | None:
    """이슈에 대한 자동 수정 액션을 매핑한다."""
    ISSUE_ACTION_MAP = {
        ('stocks', '가격 누락'): 'sync_eod_prices',
        ('market_pulse', 'MarketMover 0건'): 'sync_movers',
        ('market_pulse', 'MarketMover 불완전'): 'sync_movers',
        ('market_pulse', '키워드 생성 실패'): 'generate_keywords',
        ('screener', 'MarketBreadth'): 'sync_breadth',
        ('screener', 'SectorPerformance'): 'sync_heatmap',
        ('chain_sight', 'ETF 수집 오류'): 'sync_etf_holdings',
        ('news', '뉴스 키워드'): 'extract_news_keywords',
    }
    for (cat, title_kw), action in ISSUE_ACTION_MAP.items():
        if issue.get('category') == cat and title_kw in issue.get('title', ''):
            return action
    return None


def _get_task_stats_24h(last_24h) -> dict:
    try:
        from django_celery_results.models import TaskResult
        qs = TaskResult.objects.filter(date_done__gte=last_24h)
        total = qs.count()
        success = qs.filter(status='SUCCESS').count()
        failure = qs.filter(status='FAILURE').count()
        return {
            'total': total,
            'success': success,
            'failure': failure,
            'success_rate': round(
                (success / total * 100) if total > 0 else 0, 1
            ),
        }
    except Exception as e:
        logger.warning(f"Task stats error: {e}")
        return {'total': 0, 'success': 0, 'failure': 0, 'success_rate': 0}


def _get_task_summary_24h(last_24h) -> list:
    try:
        from django_celery_results.models import TaskResult
        return list(
            TaskResult.objects.filter(date_done__gte=last_24h)
            .values('task_name', 'status')
            .annotate(count=Count('id'))
            .order_by('task_name', 'status')
        )
    except Exception as e:
        logger.warning(f"Task summary error: {e}")
        return []


def _get_latest_task_runs() -> list:
    """각 태스크의 최근 실행 현황을 반환한다."""
    try:
        from django_celery_results.models import TaskResult
        from django.db.models import Subquery, OuterRef

        # 태스크별 가장 최근 실행 ID
        latest_ids = (
            TaskResult.objects
            .filter(task_name=OuterRef('task_name'))
            .order_by('-date_done')
            .values('id')[:1]
        )
        latest_runs = (
            TaskResult.objects
            .filter(id__in=Subquery(
                TaskResult.objects
                .values('task_name')
                .annotate(latest_id=Subquery(latest_ids))
                .values('latest_id')
            ))
            .order_by('-date_done')
        )

        results = []
        seen = set()
        for t in latest_runs:
            if t.task_name in seen:
                continue
            seen.add(t.task_name)
            results.append({
                'task_name': t.task_name or '',
                'status': t.status,
                'date_done': t.date_done.isoformat() if t.date_done else None,
                'result': str(t.result)[:300] if t.result else '',
            })
        # task_name 기준 정렬
        results.sort(key=lambda x: x['task_name'])
        return results
    except Exception as e:
        logger.warning(f"Latest task runs error: {e}")
        return []


def _get_recent_failures(last_24h) -> list:
    try:
        from django_celery_results.models import TaskResult
        failures = (
            TaskResult.objects.filter(
                date_done__gte=last_24h, status='FAILURE'
            )
            .order_by('-date_done')[:20]
        )
        return [
            {
                'task_name': f.task_name or '',
                'date_done': f.date_done.isoformat() if f.date_done else None,
                'worker': f.worker or '',
                'traceback': f.traceback or '',
            }
            for f in failures
        ]
    except Exception as e:
        logger.warning(f"Recent failures error: {e}")
        return []


def _get_rate_limits() -> dict:
    try:
        from api_request.rate_limiter import get_all_rate_limit_status
        return get_all_rate_limit_status()
    except Exception as e:
        logger.warning(f"Rate limits error: {e}")
        return {}


def _get_cache_stats() -> dict:
    try:
        from api_request.cache.decorators import CacheStats
        return CacheStats.get_stats()
    except Exception as e:
        logger.warning(f"Cache stats error: {e}")
        return {}


def _get_db_table_sizes() -> list:
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT relname, n_live_tup "
                "FROM pg_stat_user_tables "
                "ORDER BY n_live_tup DESC LIMIT 30"
            )
            return [
                {'table': row[0], 'row_count': row[1]}
                for row in cursor.fetchall()
            ]
    except Exception as e:
        logger.warning(f"DB table sizes error: {e}")
        return []


def _serialize_date(d) -> str | None:
    if d is None:
        return None
    return d.isoformat()


def _serialize_datetime(dt) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _serialize_queryvalues(items: list) -> list:
    """QuerySet.values() 결과의 date/datetime 필드를 직렬화"""
    result = []
    for item in items:
        row = {}
        for k, v in item.items():
            if hasattr(v, 'isoformat'):
                row[k] = v.isoformat()
            elif hasattr(v, '__str__') and not isinstance(v, (str, int, float, bool, type(None))):
                row[k] = str(v)
            else:
                row[k] = v
        result.append(row)
    return result
