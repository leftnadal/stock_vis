"""
InstitutionalHoldingsService - SEC 13F 기관 보유 현황 수집 및 관계 생성

SEC 13F 분기별 보고서에서 대형 기관투자자의 주식 보유 현황을 수집하고,
"같은 펀드가 보유한 종목" 관계(HELD_BY_SAME_FUND)를 생성합니다.

Core Features:
1. 주요 기관투자자 50+ 기관의 13F 파일링 수집
2. CUSIP → Ticker 매핑
3. InstitutionalHolding 모델 저장
4. 동일 펀드 보유 관계 생성 (StockRelationship)

Usage:
    service = InstitutionalHoldingsService()

    # 모든 기관 동기화
    result = service.sync_all_institutions()

    # 단일 기관 동기화
    result = service.sync_institution('0001067983', 'Berkshire Hathaway')

    # 관계 생성
    count = service.generate_held_by_same_fund(min_shared_institutions=3)

    # 조회
    holdings = service.get_institution_holdings('0001067983')
    holders = service.get_stock_institutional_holders('AAPL')
    peers = service.get_same_fund_peers('AAPL', limit=20)
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from decimal import Decimal
from collections import defaultdict

from django.db import transaction
from django.db.models import Count, Q

from serverless.models import StockRelationship

logger = logging.getLogger(__name__)


class InstitutionalHoldingsService:
    """
    SEC 13F 기관 보유 현황 수집 및 관계 생성

    주요 기관투자자 50+ 기관의 13F 파일링을 수집하고,
    동일 펀드 보유 관계를 생성합니다.
    """

    # 주요 기관투자자 CIK 목록 (50개)
    KEY_INSTITUTIONS = {
        # Mega Holders
        '0001067983': 'Berkshire Hathaway',
        '0001364742': 'BlackRock',
        '0001166559': 'Vanguard Group',
        '0001035674': 'State Street',

        # Banks & Asset Managers
        '0001061768': 'Goldman Sachs',
        '0001067701': 'JPMorgan Chase',
        '0001045810': 'Morgan Stanley',
        '0001009207': 'Fidelity Management',
        '0000913760': 'Wellington Management',
        '0000930413': 'Geode Capital Management',
        '0001397545': 'Northern Trust',
        '0001336528': 'Bridgewater Associates',
        '0001079114': 'Capital Research Global Investors',
        '0001336601': 'T. Rowe Price',
        '0001040273': 'AQR Capital Management',

        # Hedge Funds (Top Tier)
        '0001649339': 'Citadel Advisors',
        '0001167483': 'Two Sigma Investments',
        '0001159159': 'DE Shaw',
        '0001568820': 'Millennium Management',
        '0001350694': 'ARK Investment Management',
        '0001037389': 'Renaissance Technologies',
        '0001535392': 'Point72',
        '0001536637': 'Tiger Global',
        '0001418814': 'Coatue Management',
        '0001510710': 'Pershing Square',
        '0001603466': 'Third Point',
        '0001336326': 'Elliott Management',
        '0000908743': 'Soros Fund Management',
        '0001595082': 'Viking Global',
        '0001067059': 'Appaloosa Management',

        # Growth/Tech Focused
        '0001040693': 'Baillie Gifford',
        '0001364839': 'SoftBank',
        '0001656456': 'Tiger Cub (Lone Pine)',
        '0001336977': 'Greenlight Capital',
        '0001096752': 'Maverick Capital',

        # Value Investors
        '0001336528': 'Baupost Group',
        '0001061768': 'ValueAct Capital',
        '0001336489': 'Mason Capital Management',

        # ETF Issuers
        '0001364742': 'iShares (BlackRock)',
        '0001166559': 'Vanguard',
        '0000908668': 'Invesco',
        '0001020569': 'Charles Schwab',

        # International
        '0001364742': 'PIMCO',
        '0001061768': 'UBS',
        '0001364839': 'Nomura',
        '0001336601': 'Allianz',

        # Specialty
        '0001336977': 'Icahn Enterprises',
        '0001510710': 'Ackman (Pershing Square)',
        '0001336326': 'Paul Singer (Elliott)',
        '0000908743': 'Soros',
        '0001067983': 'Buffett (Berkshire)',
    }

    def __init__(self):
        """Initialize service with SEC client and CUSIP mapper"""
        try:
            from api_request.sec_edgar_client import SECEdgarClient
            self.sec_client = SECEdgarClient()
        except ImportError:
            logger.warning("SECEdgarClient not available, 13F sync will fail")
            self.sec_client = None

        try:
            from serverless.services.cusip_mapper import CUSIPMapper
            self.cusip_mapper = CUSIPMapper()
        except ImportError:
            logger.warning("CUSIPMapper not available, CUSIP mapping will fail")
            self.cusip_mapper = None

    def sync_all_institutions(self) -> Dict[str, Any]:
        """
        모든 주요 기관의 13F 보유 현황 동기화

        Returns:
            {
                'total_institutions': 50,
                'success': 45,
                'failed': 5,
                'total_holdings': 12000
            }
        """
        if not self.sec_client:
            logger.error("SEC client not available")
            return {'total_institutions': 0, 'success': 0, 'failed': 0, 'total_holdings': 0}

        logger.info(f"전체 기관 동기화 시작: {len(self.KEY_INSTITUTIONS)}개")

        total_institutions = len(self.KEY_INSTITUTIONS)
        success = 0
        failed = 0
        total_holdings = 0

        for cik, name in self.KEY_INSTITUTIONS.items():
            try:
                result = self.sync_institution(cik, name)
                if result.get('holdings_count', 0) > 0:
                    success += 1
                    total_holdings += result['holdings_count']
                else:
                    failed += 1
                    logger.warning(f"기관 동기화 실패 (데이터 없음): {name}")
            except Exception as e:
                failed += 1
                logger.error(f"기관 동기화 에러 {name}: {e}")
                continue

        result = {
            'total_institutions': total_institutions,
            'success': success,
            'failed': failed,
            'total_holdings': total_holdings
        }

        logger.info(
            f"전체 기관 동기화 완료: {success}/{total_institutions} 성공, "
            f"{total_holdings}개 보유 종목"
        )

        return result

    def sync_institution(self, cik: str, name: str) -> Dict[str, Any]:
        """
        단일 기관 13F 보유 현황 동기화

        Process:
        1. Get latest 13F filing
        2. Download holdings XML/JSON
        3. Map CUSIPs to tickers
        4. Save/update InstitutionalHolding records
        5. Calculate shares_change from previous filing

        Args:
            cik: SEC CIK (10자리)
            name: 기관명

        Returns:
            {
                'institution': 'Berkshire Hathaway',
                'filing_date': '2025-11-14',
                'holdings_count': 45,
                'mapped': 42,
                'unmapped': 3
            }
        """
        if not self.sec_client or not self.cusip_mapper:
            logger.error("Required services not available")
            return {'institution': name, 'holdings_count': 0, 'mapped': 0, 'unmapped': 0}

        logger.info(f"기관 동기화 시작: {name} (CIK: {cik})")

        try:
            # Check if InstitutionalHolding model exists
            try:
                from serverless.models import InstitutionalHolding
            except ImportError:
                logger.error("InstitutionalHolding model not available yet")
                return {'institution': name, 'holdings_count': 0, 'mapped': 0, 'unmapped': 0}

            # Get latest 13F filing
            filings = self.sec_client.get_13f_filings(cik, limit=1)

            if not filings:
                logger.warning(f"13F 파일링 없음: {name}")
                return {'institution': name, 'holdings_count': 0, 'mapped': 0, 'unmapped': 0}

            latest_filing = filings[0]
            logger.info(
                f"최신 13F 파일링: {name} - {latest_filing.filing_date} "
                f"(Report: {latest_filing.report_date})"
            )

            # Download holdings
            holdings = self.sec_client.download_13f_holdings(latest_filing)

            if not holdings:
                logger.warning(f"13F 보유 종목 없음: {name}")
                return {
                    'institution': name,
                    'filing_date': str(latest_filing.filing_date),
                    'holdings_count': 0,
                    'mapped': 0,
                    'unmapped': 0
                }

            # Get previous filing for comparison (shares_change)
            previous_holdings = {}
            try:
                prev_filings = self.sec_client.get_13f_filings(cik, limit=2)
                if len(prev_filings) > 1:
                    prev_holdings_list = self.sec_client.download_13f_holdings(prev_filings[1])
                    previous_holdings = {
                        h.get('cusip'): h.get('shares', 0)
                        for h in prev_holdings_list
                    }
            except Exception as e:
                logger.debug(f"이전 파일링 조회 실패 (무시): {e}")

            # Map CUSIPs to tickers and save
            mapped_count = 0
            unmapped_count = 0
            saved_holdings = []

            with transaction.atomic():
                for holding in holdings:
                    cusip = holding.get('cusip')
                    if not cusip:
                        unmapped_count += 1
                        continue

                    # Map CUSIP to ticker
                    ticker = self.cusip_mapper.cusip_to_ticker(cusip)
                    if not ticker:
                        unmapped_count += 1
                        logger.debug(f"CUSIP 매핑 실패: {cusip}")
                        continue

                    mapped_count += 1

                    # Calculate shares change
                    current_shares = holding.get('shares', 0)
                    prev_shares = previous_holdings.get(cusip, 0)
                    shares_change = current_shares - prev_shares if prev_shares > 0 else None

                    # Determine position change
                    position_change = None
                    if shares_change is not None:
                        if shares_change > 0:
                            position_change = 'increased'
                        elif shares_change < 0:
                            position_change = 'decreased'
                        else:
                            position_change = 'unchanged'
                    elif prev_shares == 0 and current_shares > 0:
                        position_change = 'new'

                    # Create or update holding
                    holding_obj, created = InstitutionalHolding.objects.update_or_create(
                        institution_cik=cik,
                        stock_symbol=ticker.upper(),
                        report_date=latest_filing.report_date,
                        defaults={
                            'institution_name': name,
                            'filing_date': latest_filing.filing_date,
                            'accession_number': latest_filing.accession_number,
                            'shares': current_shares,
                            'value_thousands': holding.get('value', 0),
                            'shares_change': shares_change,
                            'position_change': position_change,
                        }
                    )

                    saved_holdings.append(holding_obj)

                    if created:
                        logger.debug(f"새 보유 종목: {name} -> {ticker} ({current_shares:,} shares)")

            result = {
                'institution': name,
                'filing_date': str(latest_filing.filing_date),
                'holdings_count': len(saved_holdings),
                'mapped': mapped_count,
                'unmapped': unmapped_count
            }

            logger.info(
                f"기관 동기화 완료: {name} -> {mapped_count}개 매핑 성공, "
                f"{unmapped_count}개 실패"
            )

            return result

        except Exception as e:
            logger.error(f"기관 동기화 에러 {name}: {e}")
            raise

    def generate_held_by_same_fund(self, min_shared_institutions: int = 3) -> int:
        """
        '동일 펀드 보유' 관계 생성

        Algorithm:
        1. Get latest report_date across all institutions
        2. For each pair of stocks held by >= min_shared_institutions
        3. Calculate strength = shared_count / total_institutions_holding_either
        4. Create/update StockRelationship(relationship_type='HELD_BY_SAME_FUND')
        5. Store context: {"shared_institutions": [...], "shared_count": N}

        Args:
            min_shared_institutions: 최소 공통 기관 수 (기본 3)

        Returns:
            생성된 관계 수
        """
        try:
            from serverless.models import InstitutionalHolding
        except ImportError:
            logger.error("InstitutionalHolding model not available")
            return 0

        logger.info(f"동일 펀드 보유 관계 생성 시작 (min: {min_shared_institutions})")

        # Get latest report date
        latest_holding = InstitutionalHolding.objects.order_by('-report_date').first()
        if not latest_holding:
            logger.warning("보유 현황 데이터 없음")
            return 0

        latest_report_date = latest_holding.report_date
        logger.info(f"최신 보고 날짜: {latest_report_date}")

        # Build holdings map: {symbol: set(institution_ciks)}
        holdings_map = defaultdict(set)

        holdings_qs = InstitutionalHolding.objects.filter(
            report_date=latest_report_date
        ).values('stock_symbol', 'institution_cik', 'institution_name')

        institution_names = {}  # CIK -> Name mapping

        for holding in holdings_qs:
            symbol = holding['stock_symbol']
            cik = holding['institution_cik']
            name = holding['institution_name']

            holdings_map[symbol].add(cik)
            institution_names[cik] = name

        logger.info(f"종목 수: {len(holdings_map)}")

        # Find pairs with shared institutions
        symbols = list(holdings_map.keys())
        relationship_count = 0

        for i, symbol_a in enumerate(symbols):
            institutions_a = holdings_map[symbol_a]

            for symbol_b in symbols[i + 1:]:
                institutions_b = holdings_map[symbol_b]

                # Find shared institutions
                shared = institutions_a & institutions_b
                shared_count = len(shared)

                if shared_count < min_shared_institutions:
                    continue

                # Calculate strength
                total_institutions = len(institutions_a | institutions_b)
                strength = Decimal(str(shared_count / total_institutions))

                # Get institution names for context
                shared_institution_names = [
                    institution_names.get(cik, cik) for cik in list(shared)[:10]
                ]

                # Create relationship (bidirectional)
                for source, target in [(symbol_a, symbol_b), (symbol_b, symbol_a)]:
                    StockRelationship.objects.update_or_create(
                        source_symbol=source,
                        target_symbol=target,
                        relationship_type='HELD_BY_SAME_FUND',
                        defaults={
                            'strength': strength,
                            'source_provider': 'sec_13f',
                            'context': {
                                'shared_institutions': shared_institution_names,
                                'shared_count': shared_count,
                                'total_institutions': total_institutions,
                                'report_date': str(latest_report_date),
                            }
                        }
                    )

                relationship_count += 1

                if relationship_count % 100 == 0:
                    logger.debug(f"관계 생성 중: {relationship_count}개...")

        logger.info(f"동일 펀드 보유 관계 생성 완료: {relationship_count}개")
        return relationship_count

    def get_institution_holdings(self, cik: str) -> List[Dict[str, Any]]:
        """
        특정 기관의 현재 보유 현황 조회

        Args:
            cik: SEC CIK

        Returns:
            List of holdings with stock info
        """
        try:
            from serverless.models import InstitutionalHolding
        except ImportError:
            logger.error("InstitutionalHolding model not available")
            return []

        # Get latest report date for this institution
        latest = InstitutionalHolding.objects.filter(
            institution_cik=cik
        ).order_by('-report_date').first()

        if not latest:
            return []

        holdings = InstitutionalHolding.objects.filter(
            institution_cik=cik,
            report_date=latest.report_date
        ).order_by('-value_thousands')

        return [
            {
                'symbol': h.stock_symbol,
                'shares': h.shares,
                'value_thousands': h.value_thousands,
                'shares_change': h.shares_change,
                'position_change': h.position_change,
                'report_date': str(h.report_date),
            }
            for h in holdings
        ]

    def get_stock_institutional_holders(self, symbol: str) -> List[Dict[str, Any]]:
        """
        특정 종목의 기관 보유 현황 조회

        Args:
            symbol: 종목 심볼

        Returns:
            List of institutional holders
        """
        try:
            from serverless.models import InstitutionalHolding
        except ImportError:
            logger.error("InstitutionalHolding model not available")
            return []

        symbol = symbol.upper()

        # Get latest report date
        latest = InstitutionalHolding.objects.filter(
            stock_symbol=symbol
        ).order_by('-report_date').first()

        if not latest:
            return []

        holdings = InstitutionalHolding.objects.filter(
            stock_symbol=symbol,
            report_date=latest.report_date
        ).order_by('-value_thousands')

        return [
            {
                'institution_name': h.institution_name,
                'institution_cik': h.institution_cik,
                'shares': h.shares,
                'value_thousands': h.value_thousands,
                'shares_change': h.shares_change,
                'position_change': h.position_change,
                'filing_date': str(h.filing_date),
                'report_date': str(h.report_date),
            }
            for h in holdings
        ]

    def get_same_fund_peers(self, symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        같은 펀드가 보유한 종목 목록

        StockRelationship(HELD_BY_SAME_FUND) 조회

        Args:
            symbol: 종목 심볼
            limit: 최대 반환 개수

        Returns:
            List of peer stocks with shared institution info
        """
        symbol = symbol.upper()

        relationships = StockRelationship.objects.filter(
            source_symbol=symbol,
            relationship_type='HELD_BY_SAME_FUND'
        ).order_by('-strength')[:limit]

        return [
            {
                'symbol': rel.target_symbol,
                'strength': float(rel.strength),
                'shared_institutions': rel.context.get('shared_institutions', []),
                'shared_count': rel.context.get('shared_count', 0),
                'total_institutions': rel.context.get('total_institutions', 0),
                'report_date': rel.context.get('report_date'),
            }
            for rel in relationships
        ]
