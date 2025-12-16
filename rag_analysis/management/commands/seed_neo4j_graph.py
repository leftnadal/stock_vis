"""
Management Command: Seed Neo4j Graph with Stock Data

Usage:
    python manage.py seed_neo4j_graph
    python manage.py seed_neo4j_graph --clear  # 기존 데이터 삭제 후 시작
    python manage.py seed_neo4j_graph --limit 100  # 100개만 처리

Features:
    1. 인덱스 생성
    2. Stock 모델에서 데이터 로드
    3. Sector 노드/관계 생성
    4. 예시 관계 생성 (공급망, 경쟁사)
"""

import logging
from django.core.management.base import BaseCommand
from django.db import connection
from stocks.models import Stock
from rag_analysis.services.neo4j_driver import get_neo4j_driver

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Seed Neo4j graph database with stock relationships'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing graph data before seeding'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of stocks to process (0 = all)'
        )
        parser.add_argument(
            '--create-examples',
            action='store_true',
            help='Create example relationships (SUPPLIES, COMPETES_WITH)'
        )

    def handle(self, *args, **options):
        driver = get_neo4j_driver()

        if driver is None:
            self.stdout.write(
                self.style.ERROR('Neo4j connection failed. Cannot seed graph.')
            )
            return

        self.stdout.write(
            self.style.SUCCESS('Connected to Neo4j successfully')
        )

        try:
            # 1. Clear existing data if requested
            if options['clear']:
                self._clear_graph(driver)

            # 2. Create indexes
            self._create_indexes(driver)

            # 3. Load stocks from database
            limit = options['limit']
            stocks = Stock.objects.all()
            if limit > 0:
                stocks = stocks[:limit]

            self.stdout.write(f'Processing {stocks.count()} stocks...')

            # 4. Create stock nodes
            self._create_stock_nodes(driver, stocks)

            # 5. Create sector relationships
            self._create_sector_relationships(driver, stocks)

            # 6. Create example relationships
            if options['create_examples']:
                self._create_example_relationships(driver)

            # 7. Print statistics
            self._print_statistics(driver)

            self.stdout.write(
                self.style.SUCCESS('Graph seeding completed successfully')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error seeding graph: {e}')
            )
            logger.error(f"Graph seeding error: {e}", exc_info=True)

    def _clear_graph(self, driver):
        """
        모든 노드와 관계 삭제
        """
        self.stdout.write('Clearing existing graph data...')

        with driver.session() as session:
            # 모든 노드 삭제 (관계도 함께 삭제됨)
            result = session.run("MATCH (n) DETACH DELETE n")
            self.stdout.write(
                self.style.WARNING('Graph data cleared')
            )

    def _create_indexes(self, driver):
        """
        인덱스 생성 (성능 최적화)
        """
        self.stdout.write('Creating indexes...')

        with driver.session() as session:
            # Stock.symbol 인덱스
            session.run(
                "CREATE INDEX stock_symbol IF NOT EXISTS "
                "FOR (s:Stock) ON (s.symbol)"
            )

            # Sector.name 인덱스
            session.run(
                "CREATE INDEX sector_name IF NOT EXISTS "
                "FOR (s:Sector) ON (s.name)"
            )

            self.stdout.write(
                self.style.SUCCESS('Indexes created')
            )

    def _create_stock_nodes(self, driver, stocks):
        """
        Stock 노드 생성
        """
        self.stdout.write('Creating stock nodes...')

        batch_size = 100
        total = 0

        with driver.session() as session:
            batch = []

            for stock in stocks:
                batch.append({
                    'symbol': stock.symbol,
                    'name': stock.stock_name or stock.symbol,
                    'sector': stock.sector,
                    'industry': stock.industry,
                    'market_cap': float(stock.market_capitalization) if stock.market_capitalization else None,
                    'exchange': stock.exchange,
                })

                # 배치 실행
                if len(batch) >= batch_size:
                    self._execute_stock_batch(session, batch)
                    total += len(batch)
                    self.stdout.write(f'  Created {total} stock nodes...')
                    batch = []

            # 남은 배치 처리
            if batch:
                self._execute_stock_batch(session, batch)
                total += len(batch)

        self.stdout.write(
            self.style.SUCCESS(f'Created {total} stock nodes')
        )

    def _execute_stock_batch(self, session, batch):
        """
        Stock 노드 배치 생성
        """
        query = """
        UNWIND $batch AS row
        MERGE (s:Stock {symbol: row.symbol})
        SET s.name = row.name,
            s.sector = row.sector,
            s.industry = row.industry,
            s.market_cap = row.market_cap,
            s.exchange = row.exchange,
            s.updated_at = datetime()
        """

        session.run(query, batch=batch)

    def _create_sector_relationships(self, driver, stocks):
        """
        Stock -> Sector 관계 생성
        """
        self.stdout.write('Creating sector relationships...')

        with driver.session() as session:
            # 섹터별로 그룹화
            sectors = {}
            for stock in stocks:
                if stock.sector:
                    if stock.sector not in sectors:
                        sectors[stock.sector] = []
                    sectors[stock.sector].append(stock.symbol)

            # 섹터 노드 및 관계 생성
            for sector, symbols in sectors.items():
                batch = [{'symbol': symbol} for symbol in symbols]

                query = """
                MERGE (sector:Sector {name: $sector})
                WITH sector
                UNWIND $batch AS row
                MATCH (s:Stock {symbol: row.symbol})
                MERGE (s)-[:BELONGS_TO]->(sector)
                """

                session.run(query, sector=sector, batch=batch)

        self.stdout.write(
            self.style.SUCCESS(f'Created {len(sectors)} sector relationships')
        )

    def _create_example_relationships(self, driver):
        """
        예시 관계 생성 (SUPPLIES, COMPETES_WITH)

        Note:
            - 실제 데이터는 별도 분석/크롤링으로 채워야 함
            - 여기서는 테크 섹터 주요 종목들만 예시로 생성
        """
        self.stdout.write('Creating example relationships...')

        with driver.session() as session:
            # 공급망 관계 예시
            supply_chain_examples = [
                ('NVDA', 'TSLA', 0.75),  # NVIDIA supplies chips to Tesla
                ('NVDA', 'MSFT', 0.65),  # NVIDIA supplies GPUs to Microsoft
                ('AAPL', 'TSMC', 0.90),  # Apple chips manufactured by TSMC
                ('AMD', 'MSFT', 0.60),   # AMD supplies processors to Microsoft
            ]

            for supplier, buyer, strength in supply_chain_examples:
                try:
                    session.run(
                        """
                        MATCH (supplier:Stock {symbol: $supplier})
                        MATCH (buyer:Stock {symbol: $buyer})
                        MERGE (supplier)-[r:SUPPLIES]->(buyer)
                        SET r.strength = $strength
                        """,
                        supplier=supplier,
                        buyer=buyer,
                        strength=strength
                    )
                except Exception as e:
                    logger.warning(f"Could not create supply chain {supplier}->{buyer}: {e}")

            # 경쟁 관계 예시
            competitor_examples = [
                ('AAPL', 'MSFT', 0.70),  # Apple vs Microsoft
                ('AAPL', 'GOOGL', 0.65), # Apple vs Google
                ('NVDA', 'AMD', 0.85),   # NVIDIA vs AMD
                ('TSLA', 'F', 0.60),     # Tesla vs Ford
                ('META', 'GOOGL', 0.75), # Meta vs Google
            ]

            for stock1, stock2, overlap in competitor_examples:
                try:
                    session.run(
                        """
                        MATCH (s1:Stock {symbol: $stock1})
                        MATCH (s2:Stock {symbol: $stock2})
                        MERGE (s1)-[r:COMPETES_WITH]-(s2)
                        SET r.overlap_score = $overlap
                        """,
                        stock1=stock1,
                        stock2=stock2,
                        overlap=overlap
                    )
                except Exception as e:
                    logger.warning(f"Could not create competitor {stock1}-{stock2}: {e}")

        self.stdout.write(
            self.style.SUCCESS('Example relationships created')
        )

    def _print_statistics(self, driver):
        """
        그래프 통계 출력
        """
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Graph Statistics:')
        self.stdout.write('='*50)

        with driver.session() as session:
            # 노드 개수
            stock_count = session.run(
                "MATCH (s:Stock) RETURN count(s) AS count"
            ).single()['count']

            sector_count = session.run(
                "MATCH (s:Sector) RETURN count(s) AS count"
            ).single()['count']

            # 관계 개수
            belongs_to_count = session.run(
                "MATCH ()-[r:BELONGS_TO]->() RETURN count(r) AS count"
            ).single()['count']

            supplies_count = session.run(
                "MATCH ()-[r:SUPPLIES]->() RETURN count(r) AS count"
            ).single()['count']

            competes_count = session.run(
                "MATCH ()-[r:COMPETES_WITH]-() RETURN count(r) AS count"
            ).single()['count']

        self.stdout.write(f'Stock nodes: {stock_count}')
        self.stdout.write(f'Sector nodes: {sector_count}')
        self.stdout.write(f'BELONGS_TO relationships: {belongs_to_count}')
        self.stdout.write(f'SUPPLIES relationships: {supplies_count}')
        self.stdout.write(f'COMPETES_WITH relationships: {competes_count}')
        self.stdout.write('='*50 + '\n')
