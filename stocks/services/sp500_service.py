"""
S&P 500 구성 종목 동기화 서비스

FMP API에서 S&P 500 구성 종목을 가져와 DB에 저장/갱신합니다.
"""
import logging
from datetime import datetime
from typing import Dict, List

from django.db import transaction

from stocks.models import SP500Constituent
from serverless.services.fmp_client import FMPClient

logger = logging.getLogger(__name__)


class SP500Service:
    """S&P 500 구성 종목 관리 서비스"""

    def __init__(self):
        self.fmp_client = FMPClient()

    def sync_constituents(self) -> Dict[str, int]:
        """
        FMP에서 S&P 500 구성 종목을 가져와 DB에 동기화

        - 새 종목: create
        - 기존 종목: update
        - 없어진 종목: is_active=False

        Returns:
            {'created': int, 'updated': int, 'deactivated': int, 'total': int}
        """
        logger.info("S&P 500 구성 종목 동기화 시작")

        raw_constituents = self.fmp_client.get_sp500_constituents()

        if not raw_constituents:
            logger.error("FMP에서 S&P 500 구성 종목을 가져오지 못했습니다")
            return {'created': 0, 'updated': 0, 'deactivated': 0, 'total': 0}

        stats = {'created': 0, 'updated': 0, 'deactivated': 0, 'total': len(raw_constituents)}

        # FMP에서 가져온 심볼 목록
        fetched_symbols = set()

        with transaction.atomic():
            for item in raw_constituents:
                symbol = item.get('symbol', '').upper().strip()
                if not symbol:
                    continue

                fetched_symbols.add(symbol)

                # dateFirstAdded 파싱
                date_added = None
                date_str = item.get('dateFirstAdded', '')
                if date_str:
                    try:
                        date_added = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        pass

                defaults = {
                    'company_name': item.get('name', '')[:255],
                    'sector': item.get('sector', '')[:100],
                    'sub_sector': item.get('subSector', '')[:100],
                    'head_quarter': item.get('headQuarter', '')[:200],
                    'date_added': date_added,
                    'cik': item.get('cik', '')[:20],
                    'founded': item.get('founded', '')[:20],
                    'is_active': True,
                }

                obj, created = SP500Constituent.objects.update_or_create(
                    symbol=symbol,
                    defaults=defaults,
                )

                if created:
                    stats['created'] += 1
                else:
                    stats['updated'] += 1

            # 없어진 종목 비활성화
            deactivated = SP500Constituent.objects.filter(
                is_active=True
            ).exclude(
                symbol__in=fetched_symbols
            ).update(is_active=False)

            stats['deactivated'] = deactivated

        logger.info(
            f"S&P 500 동기화 완료: "
            f"created={stats['created']}, updated={stats['updated']}, "
            f"deactivated={stats['deactivated']}, total={stats['total']}"
        )
        return stats

    @staticmethod
    def get_active_symbols() -> List[str]:
        """활성 S&P 500 심볼 리스트 반환"""
        return list(
            SP500Constituent.objects.filter(is_active=True)
            .values_list('symbol', flat=True)
            .order_by('symbol')
        )

    @staticmethod
    def get_active_count() -> int:
        """활성 S&P 500 종목 수"""
        return SP500Constituent.objects.filter(is_active=True).count()
