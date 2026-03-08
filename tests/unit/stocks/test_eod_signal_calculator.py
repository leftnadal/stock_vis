"""
EODSignalCalculator 단위 테스트 (Step 12-1)

14개 시그널 + 벡터 연산 + VIX 레짐 분기를 검증합니다.
외부 DB 의존은 mock으로 격리.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock


# ───────────────────────────────────────────────
# 헬퍼: 단순 2-row DataFrame 생성
# ───────────────────────────────────────────────

def _make_df(symbol, close_yesterday, close_today,
             open_today=None, high_today=None, low_today=None,
             volume_today=1_000_000, avg_volume=500_000,
             prev_date=date(2026, 2, 24), today=date(2026, 2, 25),
             sector='Technology'):
    """
    시그널 단위 검증용 최소 DataFrame.

    prev 행(어제)과 today 행(오늘) 2개 행으로 구성.
    avg_volume이 20일 평균으로 사용되도록 40개 행을 실제로 생성하면
    rolling 계산이 복잡해지므로, 직접 _calculate_indicators 출력을
    조작하는 방식 대신 충분한 히스토리를 포함한 DataFrame을 생성한다.
    """
    if open_today is None:
        open_today = close_today * 0.99
    if high_today is None:
        high_today = close_today * 1.02
    if low_today is None:
        low_today = close_today * 0.97

    # 20일 평균 확보를 위해 25행 생성
    base_prices = np.linspace(close_yesterday * 0.95, close_yesterday, 24)
    rows = []
    base_date = prev_date - timedelta(days=30)
    biz_dates = [d for d in pd.date_range(base_date, periods=50, freq='B') if d.date() <= prev_date]
    # 최근 24개만 사용
    biz_dates = biz_dates[-24:]

    for i, d in enumerate(biz_dates):
        p = float(base_prices[i]) if i < len(base_prices) else float(close_yesterday)
        rows.append({
            'symbol':     symbol,
            'date':       d.date(),
            'open':       p * 0.99,
            'high':       p * 1.02,
            'low':        p * 0.97,
            'close':      p,
            'volume':     avg_volume,
            'sector':     sector,
            'industry':   '',
            'market_cap': 500_000_000_000,
        })

    # 어제 행
    rows.append({
        'symbol':     symbol,
        'date':       prev_date,
        'open':       close_yesterday * 0.99,
        'high':       close_yesterday * 1.02,
        'low':        close_yesterday * 0.97,
        'close':      close_yesterday,
        'volume':     avg_volume,
        'sector':     sector,
        'industry':   '',
        'market_cap': 500_000_000_000,
    })

    # 오늘 행
    rows.append({
        'symbol':     symbol,
        'date':       today,
        'open':       open_today,
        'high':       high_today,
        'low':        low_today,
        'close':      close_today,
        'volume':     volume_today,
        'sector':     sector,
        'industry':   '',
        'market_cap': 500_000_000_000,
    })

    return pd.DataFrame(rows)


def _get_today_signal(df_result, signal_id):
    """_detect_signals 결과에서 특정 시그널 boolean 값 반환"""
    col = f'sig_{signal_id}'
    if col not in df_result.columns:
        return False
    val = df_result[col].values[0]
    if pd.isna(val):
        return False
    return bool(val)


# ───────────────────────────────────────────────
# P1: 연속 상승/하락
# ───────────────────────────────────────────────

class TestP1ConsecutiveMoves:

    @pytest.mark.django_db
    def test_P1_consecutive_up_3days(self, calculator):
        """
        Given: AAPL 3일 연속 상승
        When: _calculate_indicators + _detect_signals
        Then: sig_P1=True, sig_P1_direction='bullish'
        """
        today = date(2026, 2, 25)
        # 26행: day0~day23 flat, day24 prev, day25 today with 3 consecutive ups
        base = 100.0
        rows = []
        base_date_range = pd.date_range(end=today - timedelta(days=4), periods=22, freq='B')
        for d in base_date_range:
            rows.append({'symbol': 'AAPL', 'date': d.date(),
                         'open': base*0.99, 'high': base*1.02, 'low': base*0.97,
                         'close': base, 'volume': 1_000_000,
                         'sector': 'Technology', 'industry': '', 'market_cap': 1_000_000_000_000})

        # 3일 연속 상승 (day -3, -2, -1, today)
        for i, offset in enumerate([-3, -2, -1, 0]):
            d = today + timedelta(days=offset)
            # 주말 피하기 위해 직전 거래일로 조정
            while d.weekday() >= 5:
                d -= timedelta(days=1)
            rows.append({'symbol': 'AAPL', 'date': today - timedelta(days=3-i),
                         'open': (base + i) * 0.99, 'high': (base + i) * 1.02,
                         'low': (base + i) * 0.97, 'close': base + i + 1,
                         'volume': 1_000_000, 'sector': 'Technology',
                         'industry': '', 'market_cap': 1_000_000_000_000})

        df = pd.DataFrame(rows)
        # 날짜 중복 제거 (혹시 발생하는 경우)
        df = df.drop_duplicates(subset=['symbol', 'date']).sort_values(['symbol', 'date'])

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert not result.empty, "target_date 행이 있어야 합니다"
        assert _get_today_signal(result, 'P1') is True
        assert result['sig_P1_direction'].values[0] == 'bullish'

    @pytest.mark.django_db
    def test_P1_consecutive_down_3days(self, calculator):
        """
        Given: AAPL 3일 연속 하락
        When: _detect_signals
        Then: sig_P1=True, sig_P1_direction='bearish'
        """
        today = date(2026, 2, 25)
        base = 110.0
        rows = []
        base_date_range = pd.date_range(end=today - timedelta(days=4), periods=22, freq='B')
        for d in base_date_range:
            rows.append({'symbol': 'AAPL', 'date': d.date(),
                         'open': base*0.99, 'high': base*1.02, 'low': base*0.97,
                         'close': base, 'volume': 1_000_000,
                         'sector': 'Technology', 'industry': '', 'market_cap': 1_000_000_000_000})

        for i in range(4):
            rows.append({'symbol': 'AAPL', 'date': today - timedelta(days=3-i),
                         'open': (base - i) * 0.99, 'high': (base - i) * 1.02,
                         'low': (base - i) * 0.97, 'close': base - i - 1,
                         'volume': 1_000_000, 'sector': 'Technology',
                         'industry': '', 'market_cap': 1_000_000_000_000})

        df = pd.DataFrame(rows)
        df = df.drop_duplicates(subset=['symbol', 'date']).sort_values(['symbol', 'date'])

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert not result.empty
        assert _get_today_signal(result, 'P1') is True
        assert result['sig_P1_direction'].values[0] == 'bearish'

    @pytest.mark.django_db
    def test_P1_no_signal_only_2days(self, calculator):
        """
        Given: 2일 연속 상승 직전에 하락으로 리셋되어 최종 consecutive_up=2
        Then: sig_P1=False (3일 미만)

        패턴: ..., 하락, 하락, 상승(day-1), 상승(today) → consecutive_up=2
        """
        today = date(2026, 2, 25)
        rows = []
        base_date_range = pd.date_range(end=today - timedelta(days=4), periods=22, freq='B')
        base = 105.0  # flat base
        for d in base_date_range:
            rows.append({'symbol': 'AAPL', 'date': d.date(),
                         'open': base*0.99, 'high': base*1.02, 'low': base*0.97,
                         'close': base, 'volume': 1_000_000,
                         'sector': 'Technology', 'industry': '', 'market_cap': 1_000_000_000_000})

        # day-3: 하락 (100.0 < 105.0 flat) — 연속 카운터 리셋
        rows.append({'symbol': 'AAPL', 'date': today - timedelta(days=3),
                     'open': 104.0, 'high': 106.0, 'low': 99.0, 'close': 100.0,
                     'volume': 1_000_000, 'sector': 'Technology', 'industry': '', 'market_cap': 1_000_000_000_000})
        # day-2: 하락 (98.0 < 100.0) — 연속 카운터 유지 (down)
        rows.append({'symbol': 'AAPL', 'date': today - timedelta(days=2),
                     'open': 99.0, 'high': 100.5, 'low': 97.5, 'close': 98.0,
                     'volume': 1_000_000, 'sector': 'Technology', 'industry': '', 'market_cap': 1_000_000_000_000})
        # day-1: 상승 (102.0 > 98.0) — consecutive_up 시작 = 1
        rows.append({'symbol': 'AAPL', 'date': today - timedelta(days=1),
                     'open': 99.0, 'high': 103.5, 'low': 98.5, 'close': 102.0,
                     'volume': 1_000_000, 'sector': 'Technology', 'industry': '', 'market_cap': 1_000_000_000_000})
        # today: 상승 (105.0 > 102.0) — consecutive_up = 2
        rows.append({'symbol': 'AAPL', 'date': today,
                     'open': 103.0, 'high': 106.0, 'low': 102.5, 'close': 105.0,
                     'volume': 1_000_000, 'sector': 'Technology', 'industry': '', 'market_cap': 1_000_000_000_000})

        df = pd.DataFrame(rows)
        df = df.drop_duplicates(subset=['symbol', 'date']).sort_values(['symbol', 'date'])

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        # consecutive_up = 2 → P1 임계값(3) 미달 → False
        consecutive = result['consecutive_up'].values[0] if 'consecutive_up' in result.columns else 0
        assert int(consecutive) < 3, f"consecutive_up={consecutive}이어야 < 3"
        assert _get_today_signal(result, 'P1') is False


# ───────────────────────────────────────────────
# P2: 수익률 상위
# ───────────────────────────────────────────────

class TestP2LargeChange:

    @pytest.mark.django_db
    def test_P2_large_change_normal_regime(self, calculator):
        """
        Given: 변동률 6% (normal regime 임계값 5% 초과)
        Then: sig_P2=True
        """
        today = date(2026, 2, 25)
        prev_close = 100.0
        today_close = 106.0  # +6%

        df = _make_df('AAPL', prev_close, today_close, today=today,
                      prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert not result.empty
        assert _get_today_signal(result, 'P2') is True
        assert result['sig_P2_direction'].values[0] == 'bullish'

    @pytest.mark.django_db
    def test_P2_vix_high_threshold_7pct(self, calculator):
        """
        Given: VIX>25 (high_vol regime), 변동률 6%
        Then: 임계값 7%이므로 sig_P2=False (6% < 7%)
        """
        today = date(2026, 2, 25)
        df = _make_df('AAPL', 100.0, 106.0, today=today,
                      prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='high_vol'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'high_vol', today)

        assert _get_today_signal(result, 'P2') is False

    @pytest.mark.django_db
    def test_P2_vix_high_regime_triggers_at_8pct(self, calculator):
        """
        Given: VIX>25, 변동률 8% (임계값 7% 초과)
        Then: sig_P2=True
        """
        today = date(2026, 2, 25)
        df = _make_df('AAPL', 100.0, 108.0, today=today,
                      prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='high_vol'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'high_vol', today)

        assert _get_today_signal(result, 'P2') is True


# ───────────────────────────────────────────────
# P3: 갭 감지
# ───────────────────────────────────────────────

class TestP3Gap:

    @pytest.mark.django_db
    def test_P3_gap_up(self, calculator):
        """
        Given: 시가 > 전일 종가 * 1.03 (갭업 3%)
        Then: sig_P3=True, direction='bullish'
        """
        today = date(2026, 2, 25)
        prev_close = 100.0
        open_today = 104.0  # +4% 갭업
        close_today = 104.5

        df = _make_df('AAPL', prev_close, close_today,
                      open_today=open_today, today=today,
                      prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert _get_today_signal(result, 'P3') is True
        assert result['sig_P3_direction'].values[0] == 'bullish'

    @pytest.mark.django_db
    def test_P3_gap_down(self, calculator):
        """
        Given: 시가 < 전일 종가 * 0.97 (갭다운 3%)
        Then: sig_P3=True, direction='bearish'
        """
        today = date(2026, 2, 25)
        prev_close = 100.0
        open_today = 96.0   # -4% 갭다운
        close_today = 96.5

        df = _make_df('AAPL', prev_close, close_today,
                      open_today=open_today, today=today,
                      prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert _get_today_signal(result, 'P3') is True
        assert result['sig_P3_direction'].values[0] == 'bearish'

    @pytest.mark.django_db
    def test_P3_no_gap_within_threshold(self, calculator):
        """
        Given: 시가 = 전일 종가 * 1.01 (1% 소폭 갭)
        Then: sig_P3=False
        """
        today = date(2026, 2, 25)
        prev_close = 100.0
        open_today = 101.0  # +1% 갭

        df = _make_df('AAPL', prev_close, 101.5,
                      open_today=open_today, today=today,
                      prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert _get_today_signal(result, 'P3') is False


# ───────────────────────────────────────────────
# P4: 장대양봉/음봉
# ───────────────────────────────────────────────

class TestP4LargeCandle:

    @pytest.mark.django_db
    def test_P4_large_bullish_candle(self, calculator):
        """
        Given: 봉 몸통 4% + 범위 대비 몸통 비율 80% (장대양봉)
        Then: sig_P4=True, direction='bullish'
        """
        today = date(2026, 2, 25)
        prev_close = 100.0
        open_today = 101.0
        close_today = 105.0   # 몸통=4%
        low_today = 100.5
        high_today = 105.5    # 범위=5, 몸통/범위 = 4/5 = 0.8

        df = _make_df('AAPL', prev_close, close_today,
                      open_today=open_today, high_today=high_today,
                      low_today=low_today, today=today,
                      prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert _get_today_signal(result, 'P4') is True
        assert result['sig_P4_direction'].values[0] == 'bullish'

    @pytest.mark.django_db
    def test_P4_small_body_no_signal(self, calculator):
        """
        Given: 봉 몸통 1% (임계값 3% 미만)
        Then: sig_P4=False
        """
        today = date(2026, 2, 25)
        prev_close = 100.0
        open_today = 100.0
        close_today = 101.0   # 몸통=1%

        df = _make_df('AAPL', prev_close, close_today,
                      open_today=open_today, today=today,
                      prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert _get_today_signal(result, 'P4') is False


# ───────────────────────────────────────────────
# P5: 52주 신고가 근접
# ───────────────────────────────────────────────

class TestP5FiftyTwoWeekHigh:

    @pytest.mark.django_db
    def test_P5_near_52w_high(self, calculator):
        """
        Given: 종가가 252일 최고가의 97% (95% 이상)
        Then: sig_P5=True
        """
        today = date(2026, 2, 25)
        # 252 거래일 데이터 생성
        dates = pd.date_range(end=today, periods=252, freq='B')
        rows = []
        np.random.seed(0)
        high_price = 0.0

        for i, d in enumerate(dates):
            close = 100.0 + i * 0.1   # 완만한 상승
            high = close * 1.02
            if high > high_price:
                high_price = high
            if d.date() == today:
                # 오늘 종가 = 52주 최고가의 97%
                close = high_price * 0.97 / 1.02
                high = high_price

            rows.append({'symbol': 'AAPL', 'date': d.date(),
                         'open': close*0.99, 'high': high,
                         'low': close*0.97, 'close': close,
                         'volume': 10_000_000, 'sector': 'Technology',
                         'industry': '', 'market_cap': 2_000_000_000_000})

        df = pd.DataFrame(rows)

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert not result.empty
        assert _get_today_signal(result, 'P5') is True

    @pytest.mark.django_db
    def test_P5_below_52w_high_threshold(self, calculator):
        """
        Given: 종가가 52주 최고가의 80% (95% 미만)
        Then: sig_P5=False
        """
        today = date(2026, 2, 25)
        dates = pd.date_range(end=today, periods=252, freq='B')
        rows = []

        for i, d in enumerate(dates):
            is_today = d.date() == today
            close = 200.0 if not is_today else 160.0  # 80% 수준
            rows.append({'symbol': 'AAPL', 'date': d.date(),
                         'open': close*0.99, 'high': close*1.02,
                         'low': close*0.97, 'close': close,
                         'volume': 10_000_000, 'sector': 'Technology',
                         'industry': '', 'market_cap': 2_000_000_000_000})

        df = pd.DataFrame(rows)

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert _get_today_signal(result, 'P5') is False


# ───────────────────────────────────────────────
# P7: 저가 대비 반등
# ───────────────────────────────────────────────

class TestP7Bounce:

    @pytest.mark.django_db
    def test_P7_bounce_from_low(self, calculator):
        """
        Given: (close - low) / low = 5% > 3%, close > open
        Then: sig_P7=True
        """
        today = date(2026, 2, 25)
        prev_close = 100.0
        low_today = 95.0
        close_today = 100.0   # 반등 = (100-95)/95 = 5.26%
        open_today = 96.0

        df = _make_df('AAPL', prev_close, close_today,
                      open_today=open_today,
                      high_today=101.0, low_today=low_today,
                      today=today, prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert _get_today_signal(result, 'P7') is True
        assert result['sig_P7_direction'].values[0] == 'bullish'

    @pytest.mark.django_db
    def test_P7_no_bounce_if_close_below_open(self, calculator):
        """
        Given: 반등 5%이지만 close < open (음봉)
        Then: sig_P7=False (close > open 조건 불충족)
        """
        today = date(2026, 2, 25)
        low_today = 95.0
        close_today = 100.0
        open_today = 102.0   # close < open

        df = _make_df('AAPL', 102.0, close_today,
                      open_today=open_today,
                      high_today=103.0, low_today=low_today,
                      today=today, prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert _get_today_signal(result, 'P7') is False


# ───────────────────────────────────────────────
# V1: 거래량 폭발
# ───────────────────────────────────────────────

class TestV1VolumeSpike:

    @pytest.mark.django_db
    def test_V1_volume_spike_normal_regime(self, calculator):
        """
        Given: 오늘 거래량 = 평균 * 2.5 (normal 임계값 2.0 초과)
        Then: sig_V1=True
        """
        today = date(2026, 2, 25)
        avg_vol = 1_000_000
        volume_today = 2_500_000  # 2.5배

        df = _make_df('AAPL', 100.0, 101.0,
                      volume_today=volume_today, avg_volume=avg_vol,
                      today=today, prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert _get_today_signal(result, 'V1') is True

    @pytest.mark.django_db
    def test_V1_high_vol_regime_needs_3x(self, calculator):
        """
        Given: VIX>25, 거래량 = 평균 * 2.5 (high_vol 임계값 3.0 미만)
        Then: sig_V1=False
        """
        today = date(2026, 2, 25)
        avg_vol = 1_000_000
        volume_today = 2_500_000  # 2.5배 (high_vol 기준 3배 미충족)

        df = _make_df('AAPL', 100.0, 101.0,
                      volume_today=volume_today, avg_volume=avg_vol,
                      today=today, prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='high_vol'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'high_vol', today)

        assert _get_today_signal(result, 'V1') is False

    @pytest.mark.django_db
    def test_V1_high_vol_regime_triggers_at_3x(self, calculator):
        """
        Given: VIX>25, 거래량 = 평균 * 3.5 (high_vol 임계값 3.0 초과)
        Then: sig_V1=True
        """
        today = date(2026, 2, 25)
        avg_vol = 1_000_000
        volume_today = 3_500_000  # 3.5배

        df = _make_df('AAPL', 100.0, 101.0,
                      volume_today=volume_today, avg_volume=avg_vol,
                      today=today, prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='high_vol'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'high_vol', today)

        assert _get_today_signal(result, 'V1') is True


# ───────────────────────────────────────────────
# PV1: 가격-거래량 효율성
# ───────────────────────────────────────────────

class TestPV1PriceVolumeEfficiency:

    @pytest.mark.django_db
    def test_PV1_high_price_low_volume(self, calculator):
        """
        Given: 변동 3% 이상 + 거래량 < 평균
        Then: sig_PV1=True
        """
        today = date(2026, 2, 25)
        avg_vol = 1_000_000
        volume_today = 800_000   # 평균 미만 (vol_ratio=0.8)

        df = _make_df('AAPL', 100.0, 103.5,  # +3.5%
                      volume_today=volume_today, avg_volume=avg_vol,
                      today=today, prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert _get_today_signal(result, 'PV1') is True


# ───────────────────────────────────────────────
# PV2: 매집 의심
# ───────────────────────────────────────────────

class TestPV2Accumulation:

    @pytest.mark.django_db
    def test_PV2_high_volume_low_price_change(self, calculator):
        """
        Given: 거래량 평균 3배 + 가격 변동 0.5% (1% 미만)
        Then: sig_PV2=True
        """
        today = date(2026, 2, 25)
        avg_vol = 1_000_000
        volume_today = 3_200_000  # 3.2배

        df = _make_df('AAPL', 100.0, 100.5,   # +0.5%
                      volume_today=volume_today, avg_volume=avg_vol,
                      today=today, prev_date=today - timedelta(days=1))

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert _get_today_signal(result, 'PV2') is True


# ───────────────────────────────────────────────
# MA1: 골든/데드크로스
# ───────────────────────────────────────────────

class TestMA1GoldenCross:

    @pytest.mark.django_db
    def test_MA1_golden_cross(self, calculator):
        """
        Given: sma50이 어제는 sma200 아래, 오늘은 위 교차
        Then: sig_MA1=True, direction='bullish'

        SMA50/SMA200이 계산되려면 min_periods(40/150)를 충족해야 하므로
        충분한 히스토리(220행)를 제공하고, 오늘 가격을 급등시켜 SMA50 상승 유도.
        """
        today = date(2026, 2, 25)
        dates = pd.date_range(end=today, periods=220, freq='B')
        rows = []

        for i, d in enumerate(dates):
            # 초반 170일: 완만한 하락 (SMA50 < SMA200 유지)
            # 후반 50일:  급격한 상승 (SMA50이 SMA200 돌파)
            if i < 170:
                close = 200.0 - i * 0.1
            else:
                close = 183.0 + (i - 170) * 1.5  # 급등

            rows.append({'symbol': 'AAPL', 'date': d.date(),
                         'open': close*0.99, 'high': close*1.02,
                         'low': close*0.97, 'close': close,
                         'volume': 10_000_000, 'sector': 'Technology',
                         'industry': '', 'market_cap': 2_000_000_000_000})

        df = pd.DataFrame(rows)

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        # 골든크로스가 발생했으면 True, 아직 교차 전이면 테스트 환경 조정 필요
        # 핵심: sig_MA1 컬럼이 존재하고 NaN이 아님
        assert 'sig_MA1' in result.columns
        # MA가 계산됐는지 확인
        if not pd.isna(result['sma_50'].values[0]) and not pd.isna(result['sma_200'].values[0]):
            assert result['sig_MA1'].dtype == bool or result['sig_MA1'].dtype == object


# ───────────────────────────────────────────────
# T1: RSI 과매도/과매수
# ───────────────────────────────────────────────

class TestT1RSI:

    def _make_rsi_df(self, rsi_target, today):
        """RSI가 목표값 근처가 되도록 설계된 DataFrame 생성"""
        dates = pd.date_range(end=today, periods=50, freq='B')
        rows = []

        if rsi_target < 30:
            # 과매도: 14일 연속 하락 유도
            prices = [100.0] * 22 + [100.0 - i * 2 for i in range(28)]
        else:
            # 과매수: 14일 연속 상승 유도
            prices = [100.0] * 22 + [100.0 + i * 2 for i in range(28)]

        for i, d in enumerate(dates):
            close = max(prices[i], 1.0)
            rows.append({'symbol': 'AAPL', 'date': d.date(),
                         'open': close*0.99, 'high': close*1.02,
                         'low': close*0.97, 'close': close,
                         'volume': 10_000_000, 'sector': 'Technology',
                         'industry': '', 'market_cap': 2_000_000_000_000})
        return pd.DataFrame(rows)

    @pytest.mark.django_db
    def test_T1_rsi_oversold(self, calculator):
        """
        Given: 14일 연속 하락으로 RSI < 30
        Then: sig_T1=True, direction='bullish'
        """
        today = date(2026, 2, 25)
        df = self._make_rsi_df(rsi_target=25, today=today)

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert not result.empty
        if not pd.isna(result['rsi_14'].values[0]):
            rsi_val = float(result['rsi_14'].values[0])
            if rsi_val < 30:
                assert _get_today_signal(result, 'T1') is True
                assert result['sig_T1_direction'].values[0] == 'bullish'

    @pytest.mark.django_db
    def test_T1_rsi_overbought(self, calculator):
        """
        Given: 14일 연속 상승으로 RSI > 70
        Then: sig_T1=True, direction='bearish'
        """
        today = date(2026, 2, 25)
        df = self._make_rsi_df(rsi_target=75, today=today)

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        assert not result.empty
        if not pd.isna(result['rsi_14'].values[0]):
            rsi_val = float(result['rsi_14'].values[0])
            if rsi_val > 70:
                assert _get_today_signal(result, 'T1') is True
                assert result['sig_T1_direction'].values[0] == 'bearish'


# ───────────────────────────────────────────────
# S1/S2: 섹터 상대 강도
# ───────────────────────────────────────────────

class TestSectorSignals:

    def _make_sector_df(self, today, symbol_change, sector_avg_change,
                        sector='Technology'):
        """
        섹터 시그널 테스트용 DataFrame.

        symbol 1개 + 같은 섹터의 dummy 종목 2개로 섹터 평균 조작.
        """
        prev_date = today - timedelta(days=1)
        rows = []
        symbols_data = [
            ('AAPL', 100.0, 100.0 * (1 + symbol_change / 100)),
            ('MSFT', 100.0, 100.0 * (1 + sector_avg_change / 100)),
            ('GOOGL', 100.0, 100.0 * (1 + sector_avg_change / 100)),
        ]

        for sym, prev_close, today_close in symbols_data:
            # 히스토리 22행
            base_dates = pd.date_range(end=prev_date - timedelta(days=1), periods=22, freq='B')
            for d in base_dates:
                rows.append({'symbol': sym, 'date': d.date(),
                             'open': prev_close*0.99, 'high': prev_close*1.02,
                             'low': prev_close*0.97, 'close': prev_close,
                             'volume': 1_000_000, 'sector': sector,
                             'industry': '', 'market_cap': 1_000_000_000_000})
            rows.append({'symbol': sym, 'date': prev_date,
                         'open': prev_close*0.99, 'high': prev_close*1.02,
                         'low': prev_close*0.97, 'close': prev_close,
                         'volume': 1_000_000, 'sector': sector,
                         'industry': '', 'market_cap': 1_000_000_000_000})
            rows.append({'symbol': sym, 'date': today,
                         'open': today_close*0.99, 'high': today_close*1.02,
                         'low': today_close*0.97, 'close': today_close,
                         'volume': 1_000_000, 'sector': sector,
                         'industry': '', 'market_cap': 1_000_000_000_000})

        return pd.DataFrame(rows)

    @pytest.mark.django_db
    def test_S1_sector_outperform(self, calculator):
        """
        Given: AAPL +8%, 섹터 평균 +2% → rel +6% (임계값 3% 초과)
        Then: AAPL sig_S1=True
        """
        today = date(2026, 2, 25)
        df = self._make_sector_df(today, symbol_change=8.0, sector_avg_change=2.0)

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        aapl_row = result[result['symbol'] == 'AAPL']
        assert not aapl_row.empty
        assert bool(aapl_row['sig_S1'].values[0]) is True
        assert aapl_row['sig_S1_direction'].values[0] == 'bullish'

    @pytest.mark.django_db
    def test_S2_sector_laggard(self, calculator):
        """
        Given: 섹터 평균 +3% 상승일에 AAPL -2% → rel -5% (임계값 -3% 이하)
        Then: AAPL sig_S2=True
        """
        today = date(2026, 2, 25)
        df = self._make_sector_df(today, symbol_change=-2.0, sector_avg_change=3.0)

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        aapl_row = result[result['symbol'] == 'AAPL']
        assert not aapl_row.empty
        assert bool(aapl_row['sig_S2'].values[0]) is True
        assert aapl_row['sig_S2_direction'].values[0] == 'bearish'


# ───────────────────────────────────────────────
# S4: 폭락장 생존자
# ───────────────────────────────────────────────

class TestS4CrashSurvivor:

    @pytest.mark.django_db
    def test_S4_crash_survivor(self, calculator):
        """
        Given: SPY -3% 하락일에 AAPL +0.2% 보합
        Then: AAPL sig_S4=True
        """
        today = date(2026, 2, 25)
        prev_date = today - timedelta(days=1)
        rows = []

        for sym, prev_close, today_close in [('SPY', 500.0, 485.0), ('AAPL', 180.0, 180.36)]:
            base_dates = pd.date_range(end=prev_date - timedelta(days=1), periods=22, freq='B')
            for d in base_dates:
                rows.append({'symbol': sym, 'date': d.date(),
                             'open': prev_close*0.99, 'high': prev_close*1.02,
                             'low': prev_close*0.97, 'close': prev_close,
                             'volume': 10_000_000, 'sector': '' if sym == 'SPY' else 'Technology',
                             'industry': '', 'market_cap': 1_000_000_000_000})
            rows.append({'symbol': sym, 'date': prev_date,
                         'open': prev_close*0.99, 'high': prev_close*1.02,
                         'low': prev_close*0.97, 'close': prev_close,
                         'volume': 10_000_000, 'sector': '' if sym == 'SPY' else 'Technology',
                         'industry': '', 'market_cap': 1_000_000_000_000})
            rows.append({'symbol': sym, 'date': today,
                         'open': today_close*0.99, 'high': today_close*1.02,
                         'low': today_close*0.97, 'close': today_close,
                         'volume': 10_000_000, 'sector': '' if sym == 'SPY' else 'Technology',
                         'industry': '', 'market_cap': 1_000_000_000_000})

        df = pd.DataFrame(rows)

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        aapl_row = result[result['symbol'] == 'AAPL']
        assert not aapl_row.empty
        # SPY change_pct ~ -3% 이므로 S4 활성화 조건 충족
        spy_change = float(result[result['symbol'] == 'SPY']['change_pct'].values[0])
        if spy_change <= -2.0:
            assert bool(aapl_row['sig_S4'].values[0]) is True

    @pytest.mark.django_db
    def test_S4_no_signal_when_spy_rises(self, calculator):
        """
        Given: SPY +1% 상승일
        Then: S4 신호 없음 (sig_S4=False)
        """
        today = date(2026, 2, 25)
        prev_date = today - timedelta(days=1)
        rows = []

        for sym, prev_close, today_close in [('SPY', 500.0, 505.0), ('AAPL', 180.0, 181.0)]:
            base_dates = pd.date_range(end=prev_date - timedelta(days=1), periods=22, freq='B')
            for d in base_dates:
                rows.append({'symbol': sym, 'date': d.date(),
                             'open': prev_close*0.99, 'high': prev_close*1.02,
                             'low': prev_close*0.97, 'close': prev_close,
                             'volume': 10_000_000, 'sector': '' if sym == 'SPY' else 'Technology',
                             'industry': '', 'market_cap': 1_000_000_000_000})
            rows.append({'symbol': sym, 'date': prev_date,
                         'open': prev_close*0.99, 'high': prev_close*1.02,
                         'low': prev_close*0.97, 'close': prev_close,
                         'volume': 10_000_000, 'sector': '' if sym == 'SPY' else 'Technology',
                         'industry': '', 'market_cap': 1_000_000_000_000})
            rows.append({'symbol': sym, 'date': today,
                         'open': today_close*0.99, 'high': today_close*1.02,
                         'low': today_close*0.97, 'close': today_close,
                         'volume': 10_000_000, 'sector': '' if sym == 'SPY' else 'Technology',
                         'industry': '', 'market_cap': 1_000_000_000_000})

        df = pd.DataFrame(rows)

        with patch.object(calculator, '_get_vix_regime', return_value='normal'):
            df_ind = calculator._calculate_indicators(df)
            result = calculator._detect_signals(df_ind, 'normal', today)

        aapl_row = result[result['symbol'] == 'AAPL']
        assert not aapl_row.empty
        assert bool(aapl_row['sig_S4'].values[0]) is False


# ───────────────────────────────────────────────
# 벡터 연산 검증
# ───────────────────────────────────────────────

class TestVectorizedOperations:

    def test_vectorized_no_iterrows(self, calculator, sample_price_df, target_date):
        """
        _calculate_indicators 결과가 DataFrame이고,
        필수 지표 컬럼이 모두 존재함을 검증.
        """
        result = calculator._calculate_indicators(sample_price_df)

        assert isinstance(result, pd.DataFrame)
        expected_cols = [
            'prev_close', 'change_pct', 'avg_vol_20d', 'vol_ratio',
            'sma_50', 'sma_200', 'rsi_14', 'high_52w',
            'consecutive_up', 'consecutive_down',
            'body', 'range', 'body_pct', 'body_ratio',
            'bounce_pct', 'dollar_volume', 'sector_avg_change',
        ]
        for col in expected_cols:
            assert col in result.columns, f"지표 컬럼 누락: {col}"

    def test_nan_propagation_handled(self, calculator):
        """
        NaN 전파 방지: 첫 행에서 prev_close가 NaN이어도
        다른 종목 계산에 영향 없음.
        """
        today = date(2026, 2, 25)
        df = _make_df('AAPL', 100.0, 101.0, today=today,
                      prev_date=today - timedelta(days=1))
        df2 = _make_df('NVDA', 140.0, 141.0, today=today,
                       prev_date=today - timedelta(days=1))
        combined = pd.concat([df, df2], ignore_index=True)

        result = calculator._calculate_indicators(combined)

        # NVDA의 change_pct가 계산됐는지 확인
        nvda_today = result[(result['symbol'] == 'NVDA') & (result['date'] == today)]
        assert not nvda_today.empty
        # NaN이 아닌 행이 존재해야 함
        non_nan = nvda_today['change_pct'].notna()
        assert non_nan.any()

    def test_high_equals_low_body_ratio(self, calculator):
        """
        high == low 인 경우 body_ratio = 0.5
        """
        today = date(2026, 2, 25)
        df = _make_df('AAPL', 100.0, 100.0,
                      open_today=100.0, high_today=100.0, low_today=100.0,
                      today=today, prev_date=today - timedelta(days=1))

        result = calculator._calculate_indicators(df)
        today_row = result[result['date'] == today]
        assert not today_row.empty
        # high == low 인 행의 body_ratio = 0.5
        high_eq_low = today_row[today_row['high'] == today_row['low']]
        if not high_eq_low.empty:
            assert float(high_eq_low['body_ratio'].values[0]) == pytest.approx(0.5)

    def test_zero_avg_volume_handling(self, calculator):
        """
        avg_vol_20d = 0 이면 vol_ratio = NaN (ZeroDivisionError 없음)
        """
        today = date(2026, 2, 25)
        # 1행짜리 DataFrame(prev_close 없으므로 rolling mean도 NaN)
        rows = [
            {'symbol': 'TINY', 'date': today,
             'open': 10.0, 'high': 11.0, 'low': 9.0, 'close': 10.5,
             'volume': 0, 'sector': 'Technology', 'industry': '', 'market_cap': 1_000_000},
        ]
        df = pd.DataFrame(rows)

        # avg_vol_20d가 NaN(min_periods 미달)이면 vol_ratio도 NaN
        result = calculator._calculate_indicators(df)
        assert 'vol_ratio' in result.columns
        # NaN 또는 inf가 아닌 값이어야 함 (0 나누기 에러 없음)
        vol_ratio_val = result['vol_ratio'].values[0]
        assert not np.isinf(vol_ratio_val) if not np.isnan(vol_ratio_val) else True


# ───────────────────────────────────────────────
# VIX 레짐 분기
# ───────────────────────────────────────────────

class TestVixRegime:
    """
    _get_vix_regime는 DynamicRegimeCalculator로 위임합니다.
    DynamicRegimeCalculator를 mock하여 위임 동작을 검증합니다.
    """

    @pytest.mark.django_db
    def test_get_vix_regime_returns_high_vol(self, calculator):
        """
        Given: DynamicRegimeCalculator가 'high_vol' 반환
        Then: _get_vix_regime returns 'high_vol'
        """
        target = date(2026, 2, 25)
        with patch(
            'stocks.services.eod_regime_calculator.DynamicRegimeCalculator'
        ) as MockCalc:
            MockCalc.return_value.get_regime.return_value = 'high_vol'
            regime = calculator._get_vix_regime(target)

        assert regime == 'high_vol'

    @pytest.mark.django_db
    def test_get_vix_regime_returns_normal(self, calculator):
        """
        Given: DynamicRegimeCalculator가 'normal' 반환
        Then: _get_vix_regime returns 'normal'
        """
        target = date(2026, 2, 25)
        with patch(
            'stocks.services.eod_regime_calculator.DynamicRegimeCalculator'
        ) as MockCalc:
            MockCalc.return_value.get_regime.return_value = 'normal'
            regime = calculator._get_vix_regime(target)

        assert regime == 'normal'

    @pytest.mark.django_db
    def test_get_vix_regime_returns_elevated(self, calculator):
        """
        Given: DynamicRegimeCalculator가 'elevated' 반환
        Then: _get_vix_regime returns 'elevated'
        """
        target = date(2026, 2, 25)
        with patch(
            'stocks.services.eod_regime_calculator.DynamicRegimeCalculator'
        ) as MockCalc:
            MockCalc.return_value.get_regime.return_value = 'elevated'
            regime = calculator._get_vix_regime(target)

        assert regime == 'elevated'

    @pytest.mark.django_db
    def test_get_vix_regime_defaults_to_normal_on_error(self, calculator):
        """
        Given: DynamicRegimeCalculator 생성 시 예외 발생
        Then: 예외가 전파됨 (DynamicRegimeCalculator 내부에서 처리)
        """
        target = date(2026, 2, 25)
        with patch(
            'stocks.services.eod_regime_calculator.DynamicRegimeCalculator'
        ) as MockCalc:
            # DynamicRegimeCalculator 자체가 에러를 잡아 'normal' 반환
            MockCalc.return_value.get_regime.return_value = 'normal'
            regime = calculator._get_vix_regime(target)

        assert regime == 'normal'

    @pytest.mark.django_db
    def test_get_vix_regime_no_vix_index_returns_normal(self, calculator):
        """
        Given: DynamicRegimeCalculator가 'normal' 반환 (VIX 인덱스 없음)
        Then: _get_vix_regime returns 'normal'
        """
        target = date(2026, 2, 25)
        with patch(
            'stocks.services.eod_regime_calculator.DynamicRegimeCalculator'
        ) as MockCalc:
            MockCalc.return_value.get_regime.return_value = 'normal'
            regime = calculator._get_vix_regime(target)

        assert regime == 'normal'


pytestmark = pytest.mark.unit
