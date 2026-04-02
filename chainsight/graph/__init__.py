from __future__ import annotations

_repository = None


def get_graph_repository():
    """
    GraphRepository 싱글턴 팩토리.
    PID 기반 driver 재생성은 Neo4jGraphRepository 내부에서 처리.
    """
    global _repository
    if _repository is None:
        from django.conf import settings
        from .repository import Neo4jGraphRepository
        _repository = Neo4jGraphRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
        )
    return _repository
