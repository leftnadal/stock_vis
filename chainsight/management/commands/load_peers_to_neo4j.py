"""Peer 관계 수집 + 로드. python manage.py load_peers_to_neo4j"""

from django.core.management.base import BaseCommand
from chainsight.graph import get_graph_repository
from chainsight.services import collect_all_peers, load_peers_to_neo4j


class Command(BaseCommand):
    help = "Finnhub/FMP Peer 수집 후 Neo4j PEER_OF 관계 로드"

    def add_arguments(self, parser):
        parser.add_argument("--use-fmp", action="store_true")
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        repo = get_graph_repository()
        if not repo.health_check():
            self.stderr.write(self.style.ERROR("Neo4j 연결 실패"))
            return

        symbols = [r["ticker"] for r in repo.run_query("MATCH (s:Stock) RETURN s.ticker AS ticker ORDER BY ticker")]
        if options["limit"]:
            symbols = symbols[:options["limit"]]

        self.stdout.write(f"대상: {len(symbols)}개, FMP: {'Yes' if options['use_fmp'] else 'No'}")
        est = len(symbols) * 1.2 / 60
        self.stdout.write(f"예상 소요: ~{est:.0f}분")

        collection = collect_all_peers(symbols, use_fmp=options["use_fmp"])
        stats = collection["stats"]
        self.stdout.write(f"수집: {stats['total_pairs']}개 pairs (Finnhub {stats['finnhub_success']}/{stats['symbols_processed']})")

        if options["dry_run"]:
            self.stdout.write("[DRY RUN] 로드 생략.")
            return

        result = load_peers_to_neo4j(collection["pairs"])
        self.stdout.write(f"로드: {result['loaded']}개, Neo4j PEER_OF: {result['neo4j_total']}개")
        self.stdout.write(self.style.SUCCESS("PEER_OF 로드 완료"))
