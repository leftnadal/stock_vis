"""
Neo4j 온톨로지 스키마 초기화 커맨드.

사용법:
  python manage.py init_neo4j_schema           # 스키마 적용
  python manage.py init_neo4j_schema --verify   # 적용 후 검증
  python manage.py init_neo4j_schema --check    # 검증만
  python manage.py init_neo4j_schema --reset    # 삭제 후 재적용
"""

from django.core.management.base import BaseCommand

from apps.chain_sight.graph import get_graph_repository
from apps.chain_sight.graph.schema import (
    CONSTRAINTS,
    INDEXES,
    initialize_schema,
    verify_schema,
)


class Command(BaseCommand):
    help = "Neo4j 온톨로지 스키마(constraint + index) 초기화"

    def add_arguments(self, parser):
        parser.add_argument("--verify", action="store_true", help="스키마 적용 후 검증")
        parser.add_argument("--check", action="store_true", help="현재 상태만 확인")
        parser.add_argument("--reset", action="store_true", help="삭제 후 재생성")

    def handle(self, *args, **options):
        repo = get_graph_repository()

        if not repo.health_check():
            self.stderr.write(
                self.style.ERROR("Neo4j 연결 실패. 서버 상태를 확인하세요.")
            )
            return
        self.stdout.write(self.style.SUCCESS("Neo4j 연결 OK"))

        if options["check"]:
            self._print_verification(repo)
            return

        if options["reset"]:
            self.stdout.write(self.style.WARNING("기존 constraint/index 삭제 중..."))
            for c in CONSTRAINTS:
                try:
                    repo.run_query(f"DROP CONSTRAINT {c['name']} IF EXISTS")
                except Exception:
                    pass
            for idx in INDEXES:
                try:
                    repo.run_query(f"DROP INDEX {idx['name']} IF EXISTS")
                except Exception:
                    pass

        self.stdout.write("스키마 적용 시작...")
        result = initialize_schema(repo)
        self.stdout.write(
            f"  Constraints: {result['constraints_applied']}/{len(CONSTRAINTS)}"
        )
        self.stdout.write(f"  Indexes: {result['indexes_applied']}/{len(INDEXES)}")

        if result["errors"]:
            for err in result["errors"]:
                self.stderr.write(self.style.ERROR(f"  {err}"))
        else:
            self.stdout.write(self.style.SUCCESS("스키마 적용 완료"))

        if options["verify"]:
            self._print_verification(repo)

    def _print_verification(self, repo):
        self.stdout.write("스키마 검증...")
        status = verify_schema(repo)
        for label, data in [
            ("Constraints", status["constraints"]),
            ("Indexes", status["indexes"]),
        ]:
            self.stdout.write(f"  {label} ({len(data['found'])}/{data['expected']}):")
            for name in data["found"]:
                self.stdout.write(self.style.SUCCESS(f"    {name}"))
            for name in data["missing"]:
                self.stderr.write(self.style.ERROR(f"    {name} (MISSING)"))
        if not status["constraints"]["missing"] and not status["indexes"]["missing"]:
            self.stdout.write(self.style.SUCCESS("스키마 검증 통과"))
