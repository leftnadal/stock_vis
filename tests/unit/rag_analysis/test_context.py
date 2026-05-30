"""
DateAwareContextFormatter 단위 테스트

DataBasket/BasketItem을 Mock으로 대체하여 DB 의존성 없이 테스트합니다.
"""

from datetime import date
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from rag_analysis.models import BasketItem
from rag_analysis.services.context import DateAwareContextFormatter


def _make_mock_basket(name='Test Basket', description='', items=None):
    """Mock DataBasket 생성"""
    basket = MagicMock()
    basket.name = name
    basket.description = description
    mock_items = MagicMock()
    mock_items.count.return_value = len(items) if items else 0
    mock_items.select_related.return_value = mock_items
    mock_items.all.return_value = items or []
    basket.items = mock_items
    return basket


def _make_mock_item(
    item_type,
    title,
    reference_id='AAPL',
    subtitle='',
    snapshot_date=None,
    data_snapshot=None,
):
    """Mock BasketItem 생성"""
    item = MagicMock()
    item.item_type = item_type
    item.title = title
    item.reference_id = reference_id
    item.subtitle = subtitle
    item.snapshot_date = snapshot_date or date(2026, 4, 14)
    item.data_snapshot = data_snapshot or {}
    item.get_item_type_display.return_value = 'Custom'
    return item


class TestFormatHeader:
    """헤더 포맷팅"""

    def test_header_includes_basket_name(self):
        basket = _make_mock_basket(name='My Analysis')
        fmt = DateAwareContextFormatter(basket)
        header = fmt._format_header()
        assert 'My Analysis' in header

    def test_header_includes_items_count(self):
        items = [_make_mock_item(BasketItem.ItemType.STOCK, 'Apple')]
        basket = _make_mock_basket(items=items)
        fmt = DateAwareContextFormatter(basket)
        header = fmt._format_header()
        assert '1개' in header

    def test_header_includes_description_when_present(self):
        basket = _make_mock_basket(description='포트폴리오 분석')
        fmt = DateAwareContextFormatter(basket)
        header = fmt._format_header()
        assert '포트폴리오 분석' in header

    def test_header_omits_description_when_empty(self):
        basket = _make_mock_basket(description='')
        fmt = DateAwareContextFormatter(basket)
        header = fmt._format_header()
        assert '설명' not in header


class TestFormatStockItem:
    """종목 아이템 포맷팅"""

    def test_stock_basic_fields(self):
        item = _make_mock_item(
            BasketItem.ItemType.STOCK,
            'Apple Inc.',
            reference_id='AAPL',
            data_snapshot={'price': 175.50, 'change_percent': 2.3},
        )
        basket = _make_mock_basket(items=[item])
        fmt = DateAwareContextFormatter(basket)
        result = fmt._format_stock_item(1, item)
        assert 'Apple Inc.' in result
        assert 'AAPL' in result
        assert '$175.50' in result
        assert '+2.30%' in result

    def test_stock_negative_change(self):
        item = _make_mock_item(
            BasketItem.ItemType.STOCK,
            'Tesla',
            data_snapshot={'price': 200.0, 'change_percent': -3.5},
        )
        basket = _make_mock_basket()
        fmt = DateAwareContextFormatter(basket)
        result = fmt._format_stock_item(1, item)
        assert '-3.50%' in result

    def test_stock_with_technical_indicators(self):
        item = _make_mock_item(
            BasketItem.ItemType.STOCK,
            'NVDA',
            data_snapshot={
                'price': 900.0,
                'rsi': 72.5,
                'ma_50': 850.0,
                'ma_200': 700.0,
            },
        )
        basket = _make_mock_basket()
        fmt = DateAwareContextFormatter(basket)
        result = fmt._format_stock_item(1, item)
        assert 'RSI: 72.50' in result
        assert 'MA50=850.00' in result
        assert 'MA200=700.00' in result


class TestFormatNewsItem:
    """뉴스 아이템 포맷팅"""

    def test_news_basic(self):
        item = _make_mock_item(
            BasketItem.ItemType.NEWS,
            'Fed Raises Rates',
            subtitle='Reuters',
            data_snapshot={'summary': 'The Fed raised rates by 25bps.', 'sentiment': 'negative'},
        )
        basket = _make_mock_basket()
        fmt = DateAwareContextFormatter(basket)
        result = fmt._format_news_item(1, item)
        assert 'Fed Raises Rates' in result
        assert 'Reuters' in result
        assert 'The Fed raised rates' in result
        assert 'negative' in result

    def test_news_with_related_symbols(self):
        item = _make_mock_item(
            BasketItem.ItemType.NEWS,
            'Tech Earnings',
            data_snapshot={'related_symbols': ['AAPL', 'MSFT', 'GOOGL']},
        )
        basket = _make_mock_basket()
        fmt = DateAwareContextFormatter(basket)
        result = fmt._format_news_item(1, item)
        assert 'AAPL, MSFT, GOOGL' in result


class TestFormatFinancialItem:
    """재무제표 아이템 포맷팅"""

    def test_financial_with_income_statement(self):
        item = _make_mock_item(
            BasketItem.ItemType.FINANCIAL,
            'AAPL Q4 2024',
            reference_id='AAPL',
            subtitle='Q4 2024',
            data_snapshot={
                'revenue': 94836000000,
                'net_income': 23636000000,
                'eps': 1.46,
            },
        )
        basket = _make_mock_basket()
        fmt = DateAwareContextFormatter(basket)
        result = fmt._format_financial_item(1, item)
        assert '매출: $94,836,000,000' in result
        assert '순이익: $23,636,000,000' in result
        assert 'EPS: $1.46' in result
        assert 'Q4 2024' in result


class TestFormatMacroItem:
    """거시경제 아이템 포맷팅"""

    def test_macro_with_value_and_change(self):
        item = _make_mock_item(
            BasketItem.ItemType.MACRO,
            'CPI',
            data_snapshot={
                'value': 3.2,
                'unit': '%',
                'previous_value': 3.1,
                'change': 0.10,
            },
        )
        basket = _make_mock_basket()
        fmt = DateAwareContextFormatter(basket)
        result = fmt._format_macro_item(1, item)
        assert 'CPI' in result
        assert '3.2%' in result
        assert '3.1%' in result
        assert '+0.10' in result


class TestFormatGenericItem:
    """알 수 없는 타입의 기본 포맷팅"""

    def test_generic_shows_snapshot_keys(self):
        item = _make_mock_item(
            'unknown_type',
            'Custom Data',
            data_snapshot={'foo': 'bar', 'baz': 42},
        )
        basket = _make_mock_basket()
        fmt = DateAwareContextFormatter(basket)
        result = fmt._format_generic_item(1, item)
        assert 'Custom Data' in result
        assert 'foo: bar' in result
        assert 'baz: 42' in result


class TestFormatFull:
    """전체 format() 통합"""

    def test_empty_basket(self):
        basket = _make_mock_basket(items=[])
        fmt = DateAwareContextFormatter(basket)
        result = fmt.format()
        assert '아이템이 없습니다' in result

    def test_multiple_items(self):
        items = [
            _make_mock_item(BasketItem.ItemType.STOCK, 'Apple', data_snapshot={'price': 175.0}),
            _make_mock_item(BasketItem.ItemType.NEWS, 'Headline', data_snapshot={'summary': 'x'}),
        ]
        basket = _make_mock_basket(name='Mixed', items=items)
        fmt = DateAwareContextFormatter(basket)
        result = fmt.format()
        assert 'Mixed' in result
        assert '2개' in result
        assert 'Apple' in result
        assert 'Headline' in result
