"""Sector/Industry 노드 + BELONGS_TO 관계 로드. python manage.py load_sectors_to_neo4j"""

from django.core.management.base import BaseCommand

from chainsight.graph import get_graph_repository
from chainsight.services import load_sectors_to_neo4j


class Command(BaseCommand):
    help = "Sector/Industry 노드 생성 + BELONGS_TO 관계 로드"

    def handle(self, *args, **options):
        repo = get_graph_repository()
        if not repo.health_check():
            self.stderr.write(self.style.ERROR("Neo4j 연결 실패"))
            return

        stock_count = repo.node_count("Stock")
        if stock_count == 0:
            self.stderr.write(
                self.style.ERROR(":Stock 노드 없음. CS-1-1 먼저 실행하세요.")
            )
            return

        self.stdout.write(f"현재 :Stock: {stock_count}개")
        result = load_sectors_to_neo4j()

        self.stdout.write(
            f":Sector: {result['sectors_created']}, :Industry: {result['industries_created']}"
        )
        self.stdout.write(
            f"BELONGS_TO_SECTOR: {result['belongs_to_sector']}, BELONGS_TO_INDUSTRY: {result['belongs_to_industry']}"
        )
        if result["errors"]:
            for e in result["errors"]:
                self.stderr.write(self.style.ERROR(e))
        else:
            self.stdout.write(self.style.SUCCESS("Sector/Industry 로드 완료"))
