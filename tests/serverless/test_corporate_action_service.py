"""
Corporate Action Service 테스트
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from serverless.services.corporate_action_service import CorporateActionService


@pytest.fixture
def service():
    """CorporateActionService 인스턴스"""
    return CorporateActionService()


@pytest.fixture
def mock_yfinance():
    """yfinance 모킹"""
    with patch('serverless.services.corporate_action_service.yf') as mock_yf:
        yield mock_yf


class TestCorporateActionService:
    """Corporate Action Service 테스트"""

    def test_should_check_positive_threshold(self, service):
        """±50% 이상일 때 체크 필요"""
        assert service.should_check(50.0) is True
        assert service.should_check(100.0) is True
        assert service.should_check(-50.0) is True
        assert service.should_check(-100.0) is True

    def test_should_check_below_threshold(self, service):
        """50% 미만일 때 체크 불필요"""
        assert service.should_check(49.9) is False
        assert service.should_check(30.0) is False
        assert service.should_check(-49.9) is False
        assert service.should_check(0.0) is False

    @patch('serverless.services.corporate_action_service.CorporateActionService._check_splits')
    @patch('serverless.services.corporate_action_service.CorporateActionService._check_dividends')
    def test_check_actions_split_found(self, mock_div, mock_split, service):
        """주식분할 감지"""
        target_date = date(2026, 1, 20)
        mock_split.return_value = {
            'date': target_date,
            'action_type': 'split',
            'ratio': Decimal('0.5'),
            'dividend_amount': None,
            'display_text': '2:1 분할',
        }
        mock_div.return_value = None

        with patch.object(service, 'yf') as mock_yf:
            mock_ticker = Mock()
            mock_ticker.splits = Mock()
            mock_ticker.dividends = Mock()
            mock_yf.Ticker.return_value = mock_ticker

            result = service.check_actions('AAPL', target_date)

        assert result is not None
        assert result['action_type'] == 'split'
        assert result['display_text'] == '2:1 분할'
        mock_split.assert_called_once()
        mock_div.assert_not_called()  # 분할 발견 시 배당 체크 안 함

    @patch('serverless.services.corporate_action_service.CorporateActionService._check_splits')
    @patch('serverless.services.corporate_action_service.CorporateActionService._check_dividends')
    def test_check_actions_dividend_found(self, mock_div, mock_split, service):
        """배당 감지"""
        target_date = date(2026, 1, 20)
        mock_split.return_value = None
        mock_div.return_value = {
            'date': target_date,
            'action_type': 'dividend',
            'ratio': None,
            'dividend_amount': Decimal('5.00'),
            'display_text': '특별배당 $5.00 (5.5%)',
        }

        with patch.object(service, 'yf') as mock_yf:
            mock_ticker = Mock()
            mock_ticker.splits = Mock()
            mock_ticker.dividends = Mock()
            mock_yf.Ticker.return_value = mock_ticker

            result = service.check_actions('AAPL', target_date)

        assert result is not None
        assert result['action_type'] == 'dividend'
        assert result['dividend_amount'] == Decimal('5.00')
        mock_split.assert_called_once()
        mock_div.assert_called_once()

    def test_check_splits_forward_split(self, service):
        """정분할 감지 (ratio > 1)"""
        target_date = date(2026, 1, 20)

        # Mock splits (pandas Series)
        # yfinance ratio > 1 → 정분할
        mock_splits = MagicMock()
        mock_splits.__len__.return_value = 1
        mock_splits.items.return_value = [
            (Mock(date=Mock(return_value=target_date)), 4.0)  # 1:4 정분할
        ]

        result = service._check_splits(mock_splits, target_date)

        assert result is not None
        assert result['action_type'] == 'split'
        assert result['display_text'] == '1:4 분할'
        assert result['ratio'] == Decimal('4.0')

    def test_check_splits_reverse_split(self, service):
        """역분할 감지 (ratio < 1)"""
        target_date = date(2026, 1, 20)

        # Mock splits
        # yfinance ratio < 1 → 역분할
        mock_splits = MagicMock()
        mock_splits.__len__.return_value = 1
        mock_splits.items.return_value = [
            (Mock(date=Mock(return_value=target_date)), 0.0357)  # 28:1 역분할
        ]

        result = service._check_splits(mock_splits, target_date)

        assert result is not None
        assert result['action_type'] == 'reverse_split'
        assert result['display_text'] == '28:1 역분할'
        assert result['ratio'] == Decimal('0.0357')

    def test_check_splits_outside_lookback(self, service):
        """LOOKBACK_DAYS 범위 밖의 분할은 무시"""
        target_date = date(2026, 1, 20)
        old_date = target_date - timedelta(days=10)  # 7일 초과

        mock_splits = MagicMock()
        mock_splits.__len__.return_value = 1
        mock_splits.items.return_value = [
            (Mock(date=Mock(return_value=old_date)), 2.0)
        ]

        result = service._check_splits(mock_splits, target_date)

        assert result is None

    def test_check_dividends_special_dividend(self, service):
        """특별배당 감지 (5% 이상)"""
        target_date = date(2026, 1, 20)

        # Mock dividends
        mock_dividends = MagicMock()
        mock_dividends.__len__.return_value = 1
        mock_dividends.items.return_value = [
            (Mock(date=Mock(return_value=target_date)), 5.0)  # $5 배당
        ]

        # Mock ticker with price
        mock_ticker = Mock()
        mock_ticker.fast_info.last_price = 90.0  # 5/90 = 5.55%

        result = service._check_dividends(mock_dividends, target_date, mock_ticker)

        assert result is not None
        assert result['action_type'] == 'dividend'
        assert result['dividend_amount'] == Decimal('5.0')
        assert '5.0' in result['display_text']

    def test_check_dividends_below_threshold(self, service):
        """일반 배당 (5% 미만) 무시"""
        target_date = date(2026, 1, 20)

        mock_dividends = MagicMock()
        mock_dividends.__len__.return_value = 1
        mock_dividends.items.return_value = [
            (Mock(date=Mock(return_value=target_date)), 1.0)  # $1 배당
        ]

        mock_ticker = Mock()
        mock_ticker.fast_info.last_price = 100.0  # 1/100 = 1%

        result = service._check_dividends(mock_dividends, target_date, mock_ticker)

        assert result is None

    @pytest.mark.django_db
    def test_save_action(self, service):
        """Corporate Action 저장"""
        action_data = {
            'date': date(2026, 1, 20),
            'action_type': 'reverse_split',
            'ratio': Decimal('28.0'),
            'dividend_amount': None,
            'display_text': '1:28 역분할',
        }

        action = service.save_action('GRI', action_data)

        assert action.symbol == 'GRI'
        assert action.action_type == 'reverse_split'
        assert action.display_text == '1:28 역분할'
        assert action.source == 'yfinance'

    def test_check_actions_unavailable(self, service):
        """yfinance 없을 때 None 반환"""
        service._available = False

        result = service.check_actions('AAPL', date(2026, 1, 20))

        assert result is None

    def test_check_actions_exception(self, service):
        """예외 발생 시 None 반환"""
        with patch.object(service, 'yf') as mock_yf:
            mock_yf.Ticker.side_effect = Exception("Network error")

            result = service.check_actions('AAPL', date(2026, 1, 20))

        assert result is None
