"""Stock 노드 벌크 로드. python manage.py load_stocks_to_neo4j"""

from django.core.management.base import BaseCommand

from apps.chain_sight.graph import get_graph_repository
from apps.chain_sight.services import get_stock_data_for_neo4j, load_stocks_to_neo4j
from packages.shared.stocks.models import Stock


class Command(BaseCommand):
    help = "PostgreSQL Stock → Neo4j :Stock 노드 벌크 로드"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        repo = get_graph_repository()
        if not repo.health_check():
            self.stderr.write(self.style.ERROR("Neo4j 연결 실패"))
            return

        qs = Stock.objects.all()
        if options["limit"]:
            qs = qs[: options["limit"]]

        before = repo.node_count("Stock")
        self.stdout.write(f"현재 Neo4j :Stock: {before}개, 로드 대상: {qs.count()}개")

        if options["dry_run"]:
            nodes = get_stock_data_for_neo4j(qs)
            for n in nodes[:5]:
                self.stdout.write(
                    f"  {n.get('ticker')} — {n.get('name')} ({n.get('sector')})"
                )
            return

        result = load_stocks_to_neo4j(qs)
        self.stdout.write(
            f"성공: {result['loaded']}, 실패: {result['errors']}, Neo4j 합계: {result['neo4j_total']}"
        )
        self.stdout.write(self.style.SUCCESS("Stock 노드 로드 완료"))
