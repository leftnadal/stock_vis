"""
Semantic Cache 설정 관리 명령어

Usage:
    # 인덱스 생성
    python manage.py setup_semantic_cache

    # 인덱스 삭제
    python manage.py setup_semantic_cache --drop

    # 만료 캐시 정리
    python manage.py setup_semantic_cache --cleanup

    # 캐시 통계 조회
    python manage.py setup_semantic_cache --stats

    # 캐시 워밍 실행
    python manage.py setup_semantic_cache --warm --limit 50
"""

from django.core.management.base import BaseCommand, CommandError

from rag_analysis.services.semantic_cache_setup import (
    setup_semantic_cache_index,
    cleanup_expired_cache,
    get_cache_stats,
    drop_semantic_cache_index
)
from rag_analysis.services.cache_warmer import CacheWarmer


class Command(BaseCommand):
    help = 'Neo4j Semantic Cache 설정 및 관리'

    def add_arguments(self, parser):
        parser.add_argument(
            '--drop',
            action='store_true',
            help='Semantic Cache 인덱스 및 데이터 삭제',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='만료된 캐시 노드 정리',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='캐시 통계 조회',
        )
        parser.add_argument(
            '--warm',
            action='store_true',
            help='캐시 워밍 실행',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='캐시 워밍 최대 수 (기본값: 50)',
        )

    def handle(self, *args, **options):
        if options['drop']:
            self._handle_drop()
        elif options['cleanup']:
            self._handle_cleanup()
        elif options['stats']:
            self._handle_stats()
        elif options['warm']:
            self._handle_warm(options['limit'])
        else:
            self._handle_setup()

    def _handle_setup(self):
        """인덱스 생성"""
        self.stdout.write('Neo4j Semantic Cache 인덱스 설정 중...')

        success = setup_semantic_cache_index()

        if success:
            self.stdout.write(self.style.SUCCESS(
                '✅ Semantic Cache 인덱스가 성공적으로 생성되었습니다.'
            ))
        else:
            raise CommandError(
                '❌ Semantic Cache 인덱스 생성에 실패했습니다. '
                'Neo4j 연결을 확인하세요.'
            )

    def _handle_drop(self):
        """인덱스 삭제"""
        self.stdout.write(self.style.WARNING(
            '⚠️  Semantic Cache 인덱스와 모든 캐시 데이터를 삭제합니다.'
        ))

        confirm = input('계속하시겠습니까? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write('취소되었습니다.')
            return

        success = drop_semantic_cache_index()

        if success:
            self.stdout.write(self.style.SUCCESS(
                '✅ Semantic Cache 인덱스가 삭제되었습니다.'
            ))
        else:
            raise CommandError(
                '❌ Semantic Cache 인덱스 삭제에 실패했습니다.'
            )

    def _handle_cleanup(self):
        """만료 캐시 정리"""
        self.stdout.write('만료된 캐시 노드 정리 중...')

        deleted_count = cleanup_expired_cache()

        self.stdout.write(self.style.SUCCESS(
            f'✅ {deleted_count}개의 만료된 캐시 노드가 삭제되었습니다.'
        ))

    def _handle_stats(self):
        """캐시 통계"""
        self.stdout.write('캐시 통계 조회 중...')

        stats = get_cache_stats()

        if stats.get('status') == 'unavailable':
            raise CommandError(
                '❌ Neo4j에 연결할 수 없습니다.'
            )

        if stats.get('status') == 'error':
            raise CommandError(
                f"❌ 에러 발생: {stats.get('error')}"
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('📊 Semantic Cache 통계'))
        self.stdout.write(f"  총 캐시 항목: {stats.get('total_entries', 0)}")
        self.stdout.write(f"  활성 항목: {stats.get('active_entries', 0)}")
        self.stdout.write(f"  만료 항목: {stats.get('expired_entries', 0)}")
        self.stdout.write(f"  평균 히트 수: {stats.get('avg_hit_count', 0):.1f}")
        self.stdout.write('')

    def _handle_warm(self, limit: int):
        """캐시 워밍"""
        import asyncio

        self.stdout.write(f'캐시 워밍 실행 중... (최대 {limit}개)')

        warmer = CacheWarmer()
        result = asyncio.run(warmer.warm_cache(limit=limit))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🔥 캐시 워밍 완료'))
        self.stdout.write(f"  워밍된 항목: {result.get('warmed_count', 0)}")
        self.stdout.write(f"  실패한 항목: {result.get('failed_count', 0)}")
        self.stdout.write(f"  건너뛴 항목: {result.get('skipped_count', 0)}")
        self.stdout.write(f"  소요 시간: {result.get('duration_seconds', 0):.1f}초")
        self.stdout.write('')
