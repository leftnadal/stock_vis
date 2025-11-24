import os
from celery import Celery
from celery.schedules import crontab

# Django 설정 모듈을 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Celery 앱 생성
app = Celery('stock_vis')

# Django 설정 파일에서 Celery 설정 가져오기
app.config_from_object('django.conf:settings', namespace='CELERY')

# Django 앱에서 태스크 자동 발견
app.autodiscover_tasks()

# 정기 태스크 스케줄 설정
app.conf.beat_schedule = {
    # 실시간 주가 업데이트 (시장 개장 시간, 5분마다)
    'update-realtime-prices': {
        'task': 'stocks.tasks.update_realtime_prices',
        'schedule': crontab(minute='*/5', hour='9-16', day_of_week='1-5'),
        'kwargs': {'priority': 'high'}
    },

    # 일일 종가 업데이트 (시장 마감 후)
    'update-daily-prices': {
        'task': 'stocks.tasks.update_daily_prices',
        'schedule': crontab(hour=17, minute=0, day_of_week='1-5'),
    },

    # 주간 데이터 업데이트 (주말)
    'update-weekly-prices': {
        'task': 'stocks.tasks.update_weekly_prices',
        'schedule': crontab(hour=0, minute=0, day_of_week=6),
    },

    # 재무제표 업데이트 (월 1일)
    'update-financial-statements': {
        'task': 'stocks.tasks.update_financial_statements',
        'schedule': crontab(hour=2, minute=0, day_of_month=1),
    },

    # 포트폴리오 가치 계산 (시장 개장 시간, 10분마다)
    'calculate-portfolio-values': {
        'task': 'users.tasks.calculate_portfolio_values',
        'schedule': crontab(minute='*/10', hour='9-16', day_of_week='1-5'),
    },
}

# 테스트 태스크 (선택적)
@app.task(bind=True)
def debug_task(self):
    """Celery 동작 확인용 테스트 태스크"""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'