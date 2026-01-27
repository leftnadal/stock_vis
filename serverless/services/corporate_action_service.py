"""
Corporate Action 감지 및 관리 서비스

가격 변동 ±50% 이상 시 주식분할, 역분할, 배당 등을 자동 감지합니다.
yfinance의 splits, dividends 데이터를 활용합니다.
"""
import logging
from datetime import date, timedelta
from typing import Dict, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class CorporateActionService:
    """
    Corporate Action 감지 및 관리 서비스

    Usage:
        service = CorporateActionService()
        if service.should_check(change_percent):
            action = service.check_actions(symbol, target_date)
            if action:
                saved = service.save_action(symbol, action)
    """

    CHANGE_THRESHOLD = 50.0  # ±50% 이상일 때만 체크
    LOOKBACK_DAYS = 7  # 최근 7일 이내 이벤트 체크

    def __init__(self):
        """초기화"""
        try:
            import yfinance as yf
            self.yf = yf
            self._available = True
        except ImportError:
            logger.warning("yfinance not installed. Corporate Action detection disabled.")
            self._available = False
            self.yf = None

    def should_check(self, change_percent: float) -> bool:
        """
        Corporate Action 체크가 필요한지 판단

        Args:
            change_percent: 가격 변동률 (%)

        Returns:
            True if |change_percent| >= 50.0
        """
        return abs(change_percent) >= self.CHANGE_THRESHOLD

    def check_actions(
        self,
        symbol: str,
        target_date: date
    ) -> Optional[Dict]:
        """
        Corporate Action 감지

        Args:
            symbol: 종목 심볼
            target_date: 대상 날짜

        Returns:
            {
                'date': date,
                'action_type': 'split' | 'reverse_split' | 'dividend' | 'spinoff',
                'ratio': Decimal (분할/역분할 비율),
                'dividend_amount': Decimal (배당금),
                'display_text': str (예: '1:28 역분할', '2:1 분할')
            }
            또는 None
        """
        if not self._available:
            return None

        try:
            ticker = self.yf.Ticker(symbol)

            # 1. 주식분할 체크
            split_action = self._check_splits(ticker.splits, target_date)
            if split_action:
                return split_action

            # 2. 배당 체크
            dividend_action = self._check_dividends(ticker.dividends, target_date, ticker)
            if dividend_action:
                return dividend_action

            return None

        except Exception as e:
            logger.warning(f"Corporate Action 체크 실패 ({symbol}): {e}")
            return None

    def _check_splits(self, splits, target_date: date) -> Optional[Dict]:
        """
        주식분할/역분할 체크

        Args:
            splits: yfinance splits 데이터
            target_date: 대상 날짜

        Returns:
            분할 정보 또는 None
        """
        if splits is None or len(splits) == 0:
            return None

        try:
            # LOOKBACK_DAYS 이내의 분할 이벤트 찾기
            start_date = target_date - timedelta(days=self.LOOKBACK_DAYS)
            end_date = target_date + timedelta(days=1)

            for split_date, ratio in splits.items():
                split_date_obj = split_date.date()

                if start_date <= split_date_obj <= end_date:
                    ratio_float = float(ratio)

                    # yfinance의 ratio는 "1주당 몇 주로 분할되는가"를 의미
                    # ratio > 1: 정분할 (예: 4.0 → 1:4 분할)
                    # ratio < 1: 역분할 (예: 0.0357 → 28:1 역분할)

                    if ratio_float > 1:
                        # 정분할
                        action_type = 'split'
                        display_text = f"1:{int(ratio_float)} 분할"
                    elif ratio_float < 1:
                        # 역분할
                        action_type = 'reverse_split'
                        reverse_ratio = int(1 / ratio_float)
                        display_text = f"{reverse_ratio}:1 역분할"
                    else:
                        continue

                    return {
                        'date': split_date_obj,
                        'action_type': action_type,
                        'ratio': Decimal(str(ratio_float)),
                        'dividend_amount': None,
                        'display_text': display_text,
                    }

            return None

        except Exception as e:
            logger.warning(f"Splits 체크 실패: {e}")
            return None

    def _check_dividends(
        self,
        dividends,
        target_date: date,
        ticker
    ) -> Optional[Dict]:
        """
        특별배당 체크

        Args:
            dividends: yfinance dividends 데이터
            target_date: 대상 날짜
            ticker: yfinance Ticker 객체

        Returns:
            배당 정보 또는 None
        """
        if dividends is None or len(dividends) == 0:
            return None

        try:
            # LOOKBACK_DAYS 이내의 배당 이벤트 찾기
            start_date = target_date - timedelta(days=self.LOOKBACK_DAYS)
            end_date = target_date + timedelta(days=1)

            for div_date, amount in dividends.items():
                div_date_obj = div_date.date()

                if start_date <= div_date_obj <= end_date:
                    # 현재 주가 조회
                    try:
                        current_price = ticker.fast_info.last_price
                        if current_price is None or current_price <= 0:
                            continue

                        # 배당 수익률 계산
                        dividend_yield = (float(amount) / float(current_price)) * 100

                        # 5% 이상일 때만 특별배당으로 간주
                        if dividend_yield >= 5.0:
                            return {
                                'date': div_date_obj,
                                'action_type': 'dividend',
                                'ratio': None,
                                'dividend_amount': Decimal(str(amount)),
                                'display_text': f"특별배당 ${amount:.2f} ({dividend_yield:.1f}%)",
                            }
                    except Exception as e:
                        logger.debug(f"배당 수익률 계산 실패: {e}")
                        continue

            return None

        except Exception as e:
            logger.warning(f"Dividends 체크 실패: {e}")
            return None

    def save_action(self, symbol: str, action_data: Dict):
        """
        Corporate Action 저장

        Args:
            symbol: 종목 심볼
            action_data: check_actions() 반환값

        Returns:
            CorporateAction 객체
        """
        from serverless.models import CorporateAction

        action, created = CorporateAction.objects.update_or_create(
            symbol=symbol.upper(),
            date=action_data['date'],
            action_type=action_data['action_type'],
            defaults={
                'ratio': action_data.get('ratio'),
                'dividend_amount': action_data.get('dividend_amount'),
                'display_text': action_data['display_text'],
                'source': 'yfinance',
            }
        )

        if created:
            logger.info(f"✅ Corporate Action 저장: {symbol} {action_data['display_text']}")

        return action
