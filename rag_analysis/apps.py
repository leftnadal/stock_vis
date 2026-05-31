from django.apps import AppConfig


class RagAnalysisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rag_analysis"
    verbose_name = "RAG Analysis"

    def ready(self):
        # Signal 등록
        import rag_analysis.signals  # noqa

        # Note: Neo4j driver cleanup은 Celery worker_shutdown 시그널로 처리
        # atexit는 fork 시 자식에 복사되어 SIGSEGV를 유발하므로 사용하지 않음
