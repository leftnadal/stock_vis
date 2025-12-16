"""
DateAwareContextFormatter - 날짜 기반 컨텍스트 포맷터

BasketItem의 데이터 스냅샷을 LLM이 이해할 수 있는 형식으로 변환합니다.
모든 수치 데이터에 snapshot_date를 명시하여 시점 혼동을 방지합니다.
"""

from datetime import date
from typing import Dict, Any
from ..models import DataBasket, BasketItem


class DateAwareContextFormatter:
    """
    DataBasket의 아이템들을 날짜 정보가 포함된 컨텍스트로 변환

    핵심 원칙:
    - 모든 수치에는 기준일(snapshot_date) 명시
    - 아이템 타입별로 다른 포맷팅 전략 적용
    - LLM이 날짜를 혼동하지 않도록 명시적 표현
    """

    def __init__(self, basket: DataBasket):
        self.basket = basket
        self.today = date.today()

    def format(self) -> str:
        """
        전체 컨텍스트 생성

        Returns:
            str: LLM에 전달할 컨텍스트 문자열
        """
        sections = [
            self._format_header(),
            self._format_items(),
        ]

        return "\n\n".join(filter(None, sections))

    def _format_header(self) -> str:
        """헤더 섹션: 분석 기준일, 바구니 메타데이터"""
        items_count = self.basket.items.count()

        header = f"""=== 분석 데이터 바구니 ===
분석 기준일: {self.today.strftime('%Y년 %m월 %d일')}
바구니명: {self.basket.name}
총 아이템 수: {items_count}개"""

        if self.basket.description:
            header += f"\n설명: {self.basket.description}"

        return header

    def _format_items(self) -> str:
        """모든 아이템 포맷팅"""
        items = self.basket.items.select_related().all()

        if not items:
            return "⚠️ 바구니에 아이템이 없습니다."

        formatted_items = []
        for idx, item in enumerate(items, 1):
            formatted_item = self._format_single_item(idx, item)
            formatted_items.append(formatted_item)

        return "\n\n".join(formatted_items)

    def _format_single_item(self, idx: int, item: BasketItem) -> str:
        """개별 아이템 포맷팅 (타입별 분기)"""
        formatter_map = {
            BasketItem.ItemType.STOCK: self._format_stock_item,
            BasketItem.ItemType.NEWS: self._format_news_item,
            BasketItem.ItemType.FINANCIAL: self._format_financial_item,
            BasketItem.ItemType.MACRO: self._format_macro_item,
        }

        formatter = formatter_map.get(item.item_type)
        if not formatter:
            return self._format_generic_item(idx, item)

        return formatter(idx, item)

    def _format_stock_item(self, idx: int, item: BasketItem) -> str:
        """종목 데이터 포맷팅"""
        snapshot = item.data_snapshot
        snapshot_date_str = item.snapshot_date.strftime('%Y-%m-%d')

        lines = [
            f"[{idx}] 종목: {item.title}",
            f"심볼: {item.reference_id}",
            f"데이터 기준일: {snapshot_date_str}",
        ]

        if item.subtitle:
            lines.append(f"부제: {item.subtitle}")

        # 주가 정보
        if 'price' in snapshot:
            lines.append(f"주가: ${snapshot['price']:.2f} (기준: {snapshot_date_str})")

        if 'change_percent' in snapshot:
            change = snapshot['change_percent']
            sign = '+' if change > 0 else ''
            lines.append(f"변동: {sign}{change:.2f}%")

        # 시가총액
        if 'market_cap' in snapshot:
            market_cap = snapshot['market_cap']
            lines.append(f"시가총액: ${market_cap:,.0f}")

        # 거래량
        if 'volume' in snapshot:
            volume = snapshot['volume']
            lines.append(f"거래량: {volume:,} (기준: {snapshot_date_str})")

        # 기술적 지표
        if 'rsi' in snapshot:
            lines.append(f"RSI: {snapshot['rsi']:.2f} (기준: {snapshot_date_str})")

        if 'ma_50' in snapshot and 'ma_200' in snapshot:
            lines.append(f"이동평균: MA50={snapshot['ma_50']:.2f}, MA200={snapshot['ma_200']:.2f}")

        return "\n".join(lines)

    def _format_news_item(self, idx: int, item: BasketItem) -> str:
        """뉴스 데이터 포맷팅"""
        snapshot = item.data_snapshot
        snapshot_date_str = item.snapshot_date.strftime('%Y-%m-%d')

        lines = [
            f"[{idx}] 뉴스: {item.title}",
            f"발행일: {snapshot_date_str}",
        ]

        if item.subtitle:
            lines.append(f"출처: {item.subtitle}")

        if 'summary' in snapshot:
            lines.append(f"요약: {snapshot['summary']}")

        if 'sentiment' in snapshot:
            sentiment = snapshot['sentiment']
            lines.append(f"감성 분석: {sentiment}")

        if 'related_symbols' in snapshot:
            symbols = ', '.join(snapshot['related_symbols'])
            lines.append(f"관련 종목: {symbols}")

        return "\n".join(lines)

    def _format_financial_item(self, idx: int, item: BasketItem) -> str:
        """재무제표 데이터 포맷팅"""
        snapshot = item.data_snapshot
        snapshot_date_str = item.snapshot_date.strftime('%Y-%m-%d')

        lines = [
            f"[{idx}] 재무제표: {item.title}",
            f"기업: {item.reference_id}",
            f"데이터 수집일: {snapshot_date_str}",
        ]

        if item.subtitle:
            lines.append(f"기간: {item.subtitle}")

        # 손익계산서
        if 'revenue' in snapshot:
            lines.append(f"매출: ${snapshot['revenue']:,.0f}")

        if 'net_income' in snapshot:
            lines.append(f"순이익: ${snapshot['net_income']:,.0f}")

        if 'eps' in snapshot:
            lines.append(f"EPS: ${snapshot['eps']:.2f}")

        # 재무상태표
        if 'total_assets' in snapshot:
            lines.append(f"총자산: ${snapshot['total_assets']:,.0f}")

        if 'total_liabilities' in snapshot:
            lines.append(f"총부채: ${snapshot['total_liabilities']:,.0f}")

        if 'total_equity' in snapshot:
            lines.append(f"자본총계: ${snapshot['total_equity']:,.0f}")

        # 현금흐름
        if 'operating_cash_flow' in snapshot:
            lines.append(f"영업현금흐름: ${snapshot['operating_cash_flow']:,.0f}")

        if 'free_cash_flow' in snapshot:
            lines.append(f"잉여현금흐름: ${snapshot['free_cash_flow']:,.0f}")

        lines.append(f"(모든 재무 수치 기준: {snapshot_date_str})")

        return "\n".join(lines)

    def _format_macro_item(self, idx: int, item: BasketItem) -> str:
        """거시경제 데이터 포맷팅"""
        snapshot = item.data_snapshot
        snapshot_date_str = item.snapshot_date.strftime('%Y-%m-%d')

        lines = [
            f"[{idx}] 거시경제 지표: {item.title}",
            f"데이터 기준일: {snapshot_date_str}",
        ]

        if item.subtitle:
            lines.append(f"설명: {item.subtitle}")

        # 지표값
        if 'value' in snapshot:
            value = snapshot['value']
            unit = snapshot.get('unit', '')
            lines.append(f"현재값: {value}{unit} (기준: {snapshot_date_str})")

        if 'previous_value' in snapshot:
            prev = snapshot['previous_value']
            unit = snapshot.get('unit', '')
            lines.append(f"이전값: {prev}{unit}")

        if 'change' in snapshot:
            change = snapshot['change']
            lines.append(f"변화: {change:+.2f}")

        # 추가 컨텍스트
        if 'description' in snapshot:
            lines.append(f"상세: {snapshot['description']}")

        return "\n".join(lines)

    def _format_generic_item(self, idx: int, item: BasketItem) -> str:
        """기본 포맷팅 (타입 미지정 또는 미래 타입)"""
        snapshot_date_str = item.snapshot_date.strftime('%Y-%m-%d')

        lines = [
            f"[{idx}] {item.get_item_type_display()}: {item.title}",
            f"참조 ID: {item.reference_id}",
            f"데이터 기준일: {snapshot_date_str}",
        ]

        if item.subtitle:
            lines.append(f"부가 정보: {item.subtitle}")

        # 스냅샷 데이터를 간단히 표시
        if item.data_snapshot:
            lines.append("데이터 스냅샷:")
            for key, value in item.data_snapshot.items():
                lines.append(f"  - {key}: {value}")

        return "\n".join(lines)
