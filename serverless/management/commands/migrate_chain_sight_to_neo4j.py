"""
Management Command: Migrate Chain Sight to Neo4j

PostgreSQL StockRelationship 데이터를 Neo4j 그래프 DB로 마이그레이션.

Usage:
    # 전체 마이그레이션
    python manage.py migrate_chain_sight_to_neo4j --all

    # 특정 종목만
    python manage.py migrate_chain_sight_to_neo4j --symbol NVDA

    # 기존 데이터 삭제 후 마이그레이션
    python manage.py migrate_chain_sight_to_neo4j --all --clear

    # 인덱스만 생성
    python manage.py migrate_chain_sight_to_neo4j --create-indexes

    # 통계 확인
    python manage.py migrate_chain_sight_to_neo4j --stats
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from serverless.models import StockRelationship
from serverless.services.neo4j_chain_sight_service import Neo4jChainSightService


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate Chain Sight data from PostgreSQL to Neo4j'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Migrate all relationships from PostgreSQL'
        )
        parser.add_argument(
            '--symbol',
            type=str,
            help='Migrate relationships for a specific symbol'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing Neo4j data before migration'
        )
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='Only create indexes, no data migration'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show Neo4j statistics only'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for bulk operations (default: 100)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate migration without writing to Neo4j'
        )

    def handle(self, *args, **options):
        service = Neo4jChainSightService()

        if not service.is_available():
            self.stdout.write(
                self.style.ERROR('Neo4j connection failed. Cannot proceed.')
            )
            self.stdout.write(
                self.style.WARNING(
                    'Check NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD in settings.'
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS('Connected to Neo4j successfully')
        )

        # Stats only
        if options['stats']:
            self._show_statistics(service)
            return

        # Create indexes only
        if options['create_indexes']:
            self._create_indexes(service)
            return

        # Clear if requested
        if options['clear']:
            self._clear_data(service)

        # Always create indexes before migration
        self._create_indexes(service)

        # Migration
        if options['all']:
            self._migrate_all(service, options)
        elif options['symbol']:
            self._migrate_symbol(service, options['symbol'], options)
        else:
            self.stdout.write(
                self.style.WARNING(
                    'No action specified. Use --all, --symbol, --create-indexes, or --stats'
                )
            )

    def _create_indexes(self, service):
        """인덱스 생성"""
        self.stdout.write('Creating indexes...')

        if service.create_indexes():
            self.stdout.write(
                self.style.SUCCESS('Indexes created successfully')
            )
        else:
            self.stdout.write(
                self.style.ERROR('Failed to create indexes')
            )

    def _clear_data(self, service):
        """Neo4j 데이터 삭제"""
        self.stdout.write(
            self.style.WARNING('Clearing existing Neo4j data...')
        )

        if service.clear_all():
            self.stdout.write(
                self.style.SUCCESS('Neo4j data cleared')
            )
        else:
            self.stdout.write(
                self.style.ERROR('Failed to clear Neo4j data')
            )

    def _migrate_all(self, service, options):
        """전체 마이그레이션"""
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        # 유니크 심볼 목록
        symbols = list(
            StockRelationship.objects.values_list(
                'source_symbol', flat=True
            ).distinct()
        )

        total_count = len(symbols)
        self.stdout.write(f'Found {total_count} unique symbols to migrate')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN: No data will be written to Neo4j')
            )

            # 관계 수 카운트만
            total_relationships = StockRelationship.objects.count()
            self.stdout.write(f'Total relationships to migrate: {total_relationships}')

            # 관계 타입별 카운트
            from django.db.models import Count
            type_counts = StockRelationship.objects.values(
                'relationship_type'
            ).annotate(count=Count('id'))

            self.stdout.write('\nRelationship types:')
            for item in type_counts:
                self.stdout.write(f"  {item['relationship_type']}: {item['count']}")

            return

        # 실제 마이그레이션
        total_synced = 0
        total_failed = 0
        start_time = timezone.now()

        for idx, symbol in enumerate(symbols, 1):
            result = service.sync_from_postgres(symbol)
            total_synced += result['synced']
            total_failed += result['failed']

            # 진행률 출력 (10개마다)
            if idx % 10 == 0 or idx == total_count:
                self.stdout.write(
                    f'Progress: {idx}/{total_count} symbols '
                    f'(synced: {total_synced}, failed: {total_failed})'
                )

        elapsed = (timezone.now() - start_time).total_seconds()

        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'Migration completed in {elapsed:.1f}s')
        )
        self.stdout.write(f'Symbols processed: {total_count}')
        self.stdout.write(f'Relationships synced: {total_synced}')
        self.stdout.write(f'Relationships failed: {total_failed}')
        self.stdout.write('='*50)

        # 통계 출력
        self._show_statistics(service)

    def _migrate_symbol(self, service, symbol, options):
        """단일 종목 마이그레이션"""
        symbol = symbol.upper()
        dry_run = options['dry_run']

        # 해당 종목의 관계 조회
        relationships = StockRelationship.objects.filter(source_symbol=symbol)
        rel_count = relationships.count()

        self.stdout.write(f'Migrating {symbol}: {rel_count} relationships')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN: No data will be written to Neo4j')
            )

            for rel in relationships[:10]:  # 처음 10개만 표시
                self.stdout.write(
                    f'  {rel.source_symbol} --{rel.relationship_type}--> '
                    f'{rel.target_symbol} (weight: {rel.strength})'
                )

            if rel_count > 10:
                self.stdout.write(f'  ... and {rel_count - 10} more')

            return

        # 실제 마이그레이션
        result = service.sync_from_postgres(symbol)

        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'Migration completed for {symbol}')
        )
        self.stdout.write(f'Synced: {result["synced"]}')
        self.stdout.write(f'Failed: {result["failed"]}')
        self.stdout.write('='*50)

    def _show_statistics(self, service):
        """통계 출력"""
        stats = service.get_statistics()

        if not stats:
            self.stdout.write(
                self.style.WARNING('No statistics available')
            )
            return

        self.stdout.write('\n' + '='*50)
        self.stdout.write('Neo4j Graph Statistics:')
        self.stdout.write('='*50)
        self.stdout.write(f'Stock nodes: {stats.get("stock_nodes", 0)}')
        self.stdout.write(f'Sector nodes: {stats.get("sector_nodes", 0)}')
        self.stdout.write(f'PEER_OF relationships: {stats.get("peer_of_relationships", 0)}')
        self.stdout.write(f'SAME_INDUSTRY relationships: {stats.get("same_industry_relationships", 0)}')
        self.stdout.write(f'CO_MENTIONED relationships: {stats.get("co_mentioned_relationships", 0)}')
        self.stdout.write('='*50 + '\n')

        # PostgreSQL 비교
        pg_count = StockRelationship.objects.count()
        neo4j_total = (
            stats.get("peer_of_relationships", 0) +
            stats.get("same_industry_relationships", 0) +
            stats.get("co_mentioned_relationships", 0)
        )

        self.stdout.write(f'PostgreSQL relationships: {pg_count}')
        self.stdout.write(f'Neo4j relationships: {neo4j_total}')

        if pg_count > 0:
            sync_rate = (neo4j_total / pg_count) * 100
            self.stdout.write(f'Sync rate: {sync_rate:.1f}%')
