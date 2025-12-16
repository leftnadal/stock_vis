from django.apps import AppConfig


class RagAnalysisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rag_analysis'
    verbose_name = 'RAG Analysis'

    def ready(self):
        # Signal 등록
        import rag_analysis.signals  # noqa

        # Neo4j driver cleanup 등록
        from django.core.signals import request_finished
        from .services.neo4j_driver import close_neo4j_driver

        # Django shutdown 시 Neo4j driver 종료
        # Note: request_finished는 매 요청마다 호출되므로 실제로는
        # Django 종료 시에만 close하도록 별도 처리 필요
        # 현재는 placeholder로 등록만 함
        import atexit
        atexit.register(close_neo4j_driver)
