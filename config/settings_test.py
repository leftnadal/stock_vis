"""
Test-only Django settings.

운영 settings를 상속하되, 테스트 격리를 위한 필수 오버라이드만 적용한다.

핵심 격리 포인트:
- CACHES: 운영 Redis(DB=1)와 완전 분리된 LocMemCache 사용.
  tests/conftest.py의 `cache.clear()` autouse fixture가 운영 시드/시그널
  캐시를 날리던 사건(2026-04-24) 재발 방지.
- CELERY_TASK_ALWAYS_EAGER: 테스트에서 Celery 태스크가 브로커 없이 즉시 실행.
- 보안 env(SECRET_KEY/NEO4J_PASSWORD): 테스트 환경 기본값을 setdefault로 주입해
  settings.py의 운영 가드가 실수로 트리거되지 않게 한다.
  (load_dotenv는 기존 env를 덮어쓰지 않으므로 setdefault 충분)
"""
import os

os.environ.setdefault('DJANGO_DEBUG', 'True')
os.environ.setdefault('SECRET_KEY', 'test-secret-key-not-for-production-use-only')
os.environ.setdefault('NEO4J_PASSWORD', 'test-neo4j-password')
# 운영 Neo4j(`bolt://localhost:7687`) 인증 실패 WARN 노이즈 방지.
# 닫힌 포트로 강제하여 테스트가 운영 인스턴스에 도달조차 못하게 한다.
os.environ.setdefault('NEO4J_URI', 'bolt://127.0.0.1:1')

from .settings import *  # noqa: F401,F403,E402

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'stockvis-test-cache',
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
