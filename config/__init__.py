# Celery 앱을 Django가 시작될 때 자동으로 로드
from .celery import app as celery_app

__all__ = ('celery_app',)
