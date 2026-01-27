"""
Market Movers Processor 테스트
"""
import pytest
from decimal import Decimal
from django.utils import timezone

from serverless.processors import MarketMoversProcessor
from serverless.models import MarketMover, StockKeyword


@pytest.mark.django_db
class TestMarketMoversProcessor:
    """MarketMoversProcessor 단위 테스트"""

    @pytest.fixture
    def processor(self):
        """프로세서 인스턴스"""
        return MarketMoversProcessor()

    @pytest.fixture
    def sample_data(self):
        """샘플 데이터"""
        today = timezone.now().date()

        # MarketMover 생성
        mover1 = MarketMover.objects.create(
            date=today,
            mover_type='gainers',
            rank=1,
            symbol='NVDA',
            company_name='NVIDIA Corporation',
            price=Decimal('525.32'),
            change_percent=Decimal('8.45'),
            volume=52400000,
            sector='Technology',
            industry='Semiconductors',
            open_price=Decimal('500.00'),
            high=Decimal('530.00'),
            low=Decimal('498.00'),
            rvol=Decimal('2.34'),
            rvol_display='2.34x',
            trend_strength=Decimal('0.85'),
            trend_display='▲0.85',
            sector_alpha=Decimal('2.3'),
            etf_sync_rate=Decimal('0.82'),
            volatility_pct=78,
        )

        mover2 = MarketMover.objects.create(
            date=today,
            mover_type='gainers',
            rank=2,
            symbol='TSLA',
            company_name='Tesla Inc',
            price=Decimal('250.00'),
            change_percent=Decimal('5.20'),
            volume=38000000,
            sector='Consumer Cyclical',
            industry='Auto Manufacturers',
            rvol_display='1.8x',
            trend_display='▲0.65',
        )

        # StockKeyword 생성 (NVDA만)
        keyword1 = StockKeyword.objects.create(
            symbol='NVDA',
            company_name='NVIDIA Corporation',
            date=today,
            keywords=["AI 반도체 수요", "데이터센터 확장", "실적 서프라이즈"],
            status='completed',
            llm_model='gemini-2.5-flash',
        )

        return {
            'date': today,
            'movers': [mover1, mover2],
            'keywords': [keyword1],
        }

    def test_get_movers_with_keywords(self, processor, sample_data):
        """Market Movers + 키워드 조회 테스트"""
        # When: Processor 호출
        result = processor.get_movers_with_keywords(
            sample_data['date'],
            'gainers'
        )

        # Then: 2개 종목 반환
        assert len(result) == 2

        # NVDA 검증
        nvda = result[0]
        assert nvda['symbol'] == 'NVDA'
        assert nvda['company_name'] == 'NVIDIA Corporation'
        assert nvda['rank'] == 1
        assert nvda['price'] == 525.32
        assert nvda['change_percent'] == 8.45
        assert nvda['volume'] == 52400000
        assert nvda['sector'] == 'Technology'
        assert nvda['industry'] == 'Semiconductors'

        # OHLC 검증
        assert nvda['ohlc']['open'] == 500.00
        assert nvda['ohlc']['high'] == 530.00
        assert nvda['ohlc']['low'] == 498.00

        # 지표 검증
        assert nvda['indicators']['rvol'] == '2.34x'
        assert nvda['indicators']['trend'] == '▲0.85'
        assert nvda['indicators']['sector_alpha'] == '+2.3%'
        assert nvda['indicators']['etf_sync'] == '0.82'
        assert nvda['indicators']['volatility'] == 'P78'

        # 키워드 검증 ⭐
        assert len(nvda['keywords']) == 3
        assert "AI 반도체 수요" in nvda['keywords']

        # TSLA 검증 (키워드 없음)
        tsla = result[1]
        assert tsla['symbol'] == 'TSLA'
        assert tsla['keywords'] == []  # 키워드 없으면 빈 배열

    def test_get_keywords_map_n_plus_one_prevention(self, processor, sample_data):
        """N+1 쿼리 방지 테스트"""
        # When: 키워드 맵 조회
        symbols = ['NVDA', 'TSLA', 'AAPL']
        keywords_map = processor._get_keywords_map(symbols, sample_data['date'])

        # Then: 맵 구조 반환
        assert isinstance(keywords_map, dict)
        assert 'NVDA' in keywords_map
        assert len(keywords_map['NVDA']) == 3
        assert 'TSLA' not in keywords_map  # 키워드 없으면 맵에 없음

    def test_format_percentage(self, processor):
        """퍼센티지 포맷팅 테스트"""
        # 양수
        assert processor._format_percentage(Decimal('2.3')) == '+2.3%'

        # 음수
        assert processor._format_percentage(Decimal('-1.5')) == '-1.5%'

        # None
        assert processor._format_percentage(None) is None

        # 0
        assert processor._format_percentage(Decimal('0')) == '+0.0%'

    @pytest.mark.django_db
    def test_get_movers_empty_keywords(self, processor):
        """키워드 없는 경우 테스트"""
        today = timezone.now().date()

        # 키워드 없는 Mover만 생성
        MarketMover.objects.create(
            date=today,
            mover_type='losers',
            rank=1,
            symbol='XYZ',
            company_name='XYZ Corp',
            price=Decimal('100.00'),
            change_percent=Decimal('-5.00'),
            volume=1000000,
        )

        # When: 조회
        result = processor.get_movers_with_keywords(today, 'losers')

        # Then: 키워드 빈 배열
        assert len(result) == 1
        assert result[0]['keywords'] == []

    @pytest.mark.django_db
    def test_get_movers_no_data(self, processor):
        """데이터 없는 경우 테스트"""
        today = timezone.now().date()

        # When: 조회
        result = processor.get_movers_with_keywords(today, 'gainers')

        # Then: 빈 리스트
        assert result == []
