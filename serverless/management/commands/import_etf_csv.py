"""
ETF Holdings CSV 수동 임포트 커맨드

Usage:
    python manage.py import_etf_csv ARKK /path/to/ARKK_HOLDINGS.csv
    python manage.py import_etf_csv SOXX /path/to/SOXX_holdings.csv --parser ishares
"""
import csv
import os
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from serverless.models import ETFProfile, ETFHolding
from serverless.services.etf_csv_downloader import ETFCSVDownloader


class Command(BaseCommand):
    help = 'ETF Holdings CSV 파일을 수동으로 임포트합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            'etf_symbol',
            type=str,
            help='ETF 심볼 (예: ARKK, SOXX, XLK)'
        )
        parser.add_argument(
            'csv_path',
            type=str,
            help='CSV 파일 경로'
        )
        parser.add_argument(
            '--parser',
            type=str,
            default='auto',
            choices=['auto', 'ark', 'ishares', 'spdr', 'generic'],
            help='CSV 파서 타입 (기본: auto)'
        )

    def handle(self, *args, **options):
        etf_symbol = options['etf_symbol'].upper()
        csv_path = options['csv_path']
        parser_type = options['parser']

        # 파일 존재 확인
        if not os.path.exists(csv_path):
            raise CommandError(f'파일을 찾을 수 없습니다: {csv_path}')

        # ETFProfile 확인/생성
        try:
            profile = ETFProfile.objects.get(symbol=etf_symbol)
            self.stdout.write(f'ETF 프로필 발견: {profile.name}')
        except ETFProfile.DoesNotExist:
            # 프로필 없으면 기본값으로 생성
            self.stdout.write(self.style.WARNING(f'ETF 프로필 없음, 새로 생성합니다: {etf_symbol}'))
            profile = ETFProfile.objects.create(
                symbol=etf_symbol,
                name=f'{etf_symbol} ETF',
                tier='theme',
                theme_id=etf_symbol.lower(),
                parser_type=parser_type if parser_type != 'auto' else 'generic'
            )

        # 파서 타입 자동 감지
        if parser_type == 'auto':
            parser_type = self._detect_parser_type(csv_path, profile)
            self.stdout.write(f'파서 타입 감지: {parser_type}')

        # CSV 읽기
        with open(csv_path, 'rb') as f:
            content = f.read()

        # 파싱
        downloader = ETFCSVDownloader()
        try:
            holdings = downloader._parse_csv(content, parser_type, etf_symbol)
        except Exception as e:
            raise CommandError(f'CSV 파싱 실패: {e}')

        if not holdings:
            raise CommandError('파싱된 Holdings가 없습니다. 파서 타입을 확인하세요.')

        self.stdout.write(f'파싱된 Holdings: {len(holdings)}개')

        # 미리보기
        self.stdout.write('\n상위 5개 종목:')
        for h in holdings[:5]:
            self.stdout.write(f"  {h['rank']:2}. {h['symbol']:6} - {h['weight']:.2f}%")

        # 저장 확인
        confirm = input('\n저장하시겠습니까? (y/n): ')
        if confirm.lower() != 'y':
            self.stdout.write(self.style.WARNING('취소되었습니다.'))
            return

        # DB 저장
        today = date.today()

        # 기존 데이터 삭제
        deleted, _ = ETFHolding.objects.filter(etf=profile, snapshot_date=today).delete()
        if deleted:
            self.stdout.write(f'기존 데이터 {deleted}개 삭제')

        # 새 데이터 저장
        holding_objects = []
        for h in holdings:
            holding_objects.append(ETFHolding(
                etf=profile,
                stock_symbol=h['symbol'],
                weight_percent=Decimal(str(h['weight'])),
                shares=h.get('shares'),
                market_value=Decimal(str(h['market_value'])) if h.get('market_value') else None,
                rank=h['rank'],
                snapshot_date=today,
            ))

        ETFHolding.objects.bulk_create(holding_objects)

        # 프로필 업데이트
        from django.utils import timezone
        import hashlib
        profile.last_updated = timezone.now()
        profile.last_row_count = len(holdings)
        profile.last_hash = hashlib.sha256(content).hexdigest()
        profile.last_error = ''
        profile.save()

        self.stdout.write(self.style.SUCCESS(
            f'\n{etf_symbol}: {len(holdings)}개 Holdings 임포트 완료!'
        ))

        # ThemeMatch 갱신 안내
        self.stdout.write('\n테마 매칭을 갱신하려면:')
        self.stdout.write('  python manage.py shell -c "from serverless.services.theme_matching_service import ThemeMatchingService; ThemeMatchingService().refresh_all_matches()"')

    def _detect_parser_type(self, csv_path: str, profile: ETFProfile) -> str:
        """CSV 내용으로 파서 타입 감지"""
        # 프로필에 설정된 파서 사용
        if profile.parser_type and profile.parser_type != 'generic':
            return profile.parser_type

        # 파일 내용으로 추론
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_lines = f.read(2000).lower()

        if 'ark' in first_lines or 'fund,company,ticker' in first_lines:
            return 'ark'
        elif 'ishares' in first_lines or 'weight (%)' in first_lines:
            return 'ishares'
        elif 'spdr' in first_lines or 'ssga' in first_lines:
            return 'spdr'
        else:
            return 'generic'
