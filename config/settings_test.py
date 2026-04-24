"""
Test-only Django settings.

운영 settings를 상속하되, 테스트 격리를 위한 필수 오버라이드만 적용한다.

핵심 격리 포인트:
- CACHES: 운영 Redis(DB=1)와 완전 분리된 LocMemCache 사용.
  tests/conftest.py의 `cache.clear()` autouse fixture가 운영 시드/시그널
  캐시를 날리던 사건(2026-04-24) 재발 방지.
- CELERY_TASK_ALWAYS_EAGER: 테스트에서 Celery 태스크가 브로커 없이 즉시 실행.
"""

from .settings import *  # noqa: F401,F403


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'stockvis-test-cache',
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
