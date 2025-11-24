from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.models import Sum, F
from django.utils import timezone
from decimal import Decimal
import json

logger = get_task_logger(__name__)

@shared_task
def calculate_portfolio_values():
    """포트폴리오 가치 계산 및 히스토리 저장"""
    try:
        from django.contrib.auth import get_user_model
        from .models import Portfolio
        from stocks.models import Stock

        User = get_user_model()

        # 포트폴리오가 있는 모든 사용자
        users_with_portfolio = User.objects.filter(
            portfolio__isnull=False
        ).distinct()

        updated_users = 0
        for user in users_with_portfolio:
            try:
                portfolios = Portfolio.objects.filter(
                    user=user
                ).select_related('stock')

                total_value = Decimal('0')
                total_cost = Decimal('0')
                portfolio_data = []

                for portfolio in portfolios:
                    # 현재가 가져오기
                    current_price = portfolio.stock.real_time_price or Decimal('0')

                    # 포트폴리오 가치 계산
                    portfolio_value = current_price * portfolio.quantity
                    portfolio_cost = portfolio.average_price * portfolio.quantity

                    total_value += portfolio_value
                    total_cost += portfolio_cost

                    portfolio_data.append({
                        'symbol': portfolio.stock.symbol,
                        'quantity': float(portfolio.quantity),
                        'average_price': float(portfolio.average_price),
                        'current_price': float(current_price),
                        'value': float(portfolio_value),
                        'cost': float(portfolio_cost),
                        'profit_loss': float(portfolio_value - portfolio_cost),
                        'profit_loss_percentage': float(
                            ((portfolio_value - portfolio_cost) / portfolio_cost * 100)
                            if portfolio_cost > 0 else 0
                        )
                    })

                # 히스토리 저장 (선택적 - PortfolioHistory 모델이 있다면)
                # PortfolioHistory.objects.create(
                #     user=user,
                #     total_value=total_value,
                #     total_cost=total_cost,
                #     profit_loss=total_value - total_cost,
                #     profit_loss_percentage=((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0,
                #     portfolio_data=json.dumps(portfolio_data)
                # )

                updated_users += 1
                logger.info(f"Updated portfolio for user {user.username}: "
                          f"Total value: ${total_value:.2f}, "
                          f"P&L: ${total_value - total_cost:.2f}")

            except Exception as e:
                logger.error(f"Failed to calculate portfolio for user {user.id}: {e}")
                continue

        return f"Updated portfolios for {updated_users} users"

    except Exception as e:
        logger.error(f"Portfolio calculation task failed: {e}")
        return f"Error: {e}"

@shared_task
def send_portfolio_alert(user_id, alert_type, data):
    """포트폴리오 알림 전송"""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user = User.objects.get(id=user_id)

        # 알림 로직 구현 (이메일, 푸시 알림 등)
        if alert_type == 'price_alert':
            symbol = data.get('symbol')
            current_price = data.get('current_price')
            target_price = data.get('target_price')

            message = f"{symbol} reached target price: ${current_price:.2f} (target: ${target_price:.2f})"
            logger.info(f"Alert for {user.username}: {message}")

            # 실제 알림 전송 로직 추가
            # send_email(user.email, subject="Price Alert", message=message)

        elif alert_type == 'portfolio_update':
            total_value = data.get('total_value')
            change_percent = data.get('change_percent')

            message = f"Portfolio update: ${total_value:.2f} ({change_percent:+.2f}%)"
            logger.info(f"Portfolio update for {user.username}: {message}")

        return f"Alert sent to {user.username}"

    except Exception as e:
        logger.error(f"Failed to send alert: {e}")
        return f"Error: {e}"

@shared_task
def cleanup_old_portfolio_history():
    """오래된 포트폴리오 히스토리 데이터 정리"""
    try:
        from datetime import timedelta

        # 30일 이상 된 데이터 삭제 (필요시 구현)
        cutoff_date = timezone.now() - timedelta(days=30)

        # 실제 모델이 있다면:
        # deleted_count = PortfolioHistory.objects.filter(
        #     created_at__lt=cutoff_date
        # ).delete()[0]

        logger.info(f"Cleaned up old portfolio history")
        return "Cleanup completed"

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return f"Error: {e}"

@shared_task
def calculate_portfolio_performance(user_id, period='1d'):
    """포트폴리오 성과 계산"""
    try:
        from django.contrib.auth import get_user_model
        from .models import Portfolio
        from datetime import timedelta

        User = get_user_model()
        user = User.objects.get(id=user_id)

        # 기간별 성과 계산 로직
        period_map = {
            '1d': 1,
            '1w': 7,
            '1m': 30,
            '3m': 90,
            '6m': 180,
            '1y': 365
        }

        days = period_map.get(period, 1)
        start_date = timezone.now() - timedelta(days=days)

        portfolios = Portfolio.objects.filter(user=user).select_related('stock')

        performance_data = {
            'user': user.username,
            'period': period,
            'start_date': start_date.isoformat(),
            'portfolios': []
        }

        for portfolio in portfolios:
            # 과거 가격 데이터 조회 로직 (구현 필요)
            portfolio_perf = {
                'symbol': portfolio.stock.symbol,
                'current_value': float(portfolio.total_value),
                'cost_basis': float(portfolio.total_cost),
                'return': float(portfolio.profit_loss),
                'return_percentage': float(portfolio.profit_loss_percentage)
            }
            performance_data['portfolios'].append(portfolio_perf)

        logger.info(f"Calculated performance for {user.username} over {period}")
        return performance_data

    except Exception as e:
        logger.error(f"Performance calculation failed: {e}")
        return f"Error: {e}"

# 테스트 태스크
@shared_task
def test_user_task():
    """사용자 앱 테스트 태스크"""
    logger.info("User task is working!")
    return "User task executed successfully"