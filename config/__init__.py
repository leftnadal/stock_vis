# macOS fork safety — 가능한 가장 이른 시점에 설정
import os
import platform
if platform.system() == 'Darwin':
    os.environ.setdefault('OBJC_DISABLE_INITIALIZE_FORK_SAFETY', 'YES')

# Celery 앱을 Django가 시작될 때 자동으로 로드
from .celery import app as celery_app

__all__ = ('celery_app',)
