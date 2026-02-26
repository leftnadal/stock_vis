"""
EOD Signal Calculator (Step 2)

S&P 500 전체 종목에 대해 벡터 연산으로 14개 시그널을 계산합니다.

규칙:
- for-loop 금지, pandas 벡터 연산만 사용
- df.iterrows(), df.apply(custom_func) 절대 금지
- NaN 전파 방지: 개별 지표에 NaN 시 해당 지표만 null
- high == low → body_ratio = 0.5
- avg_volume_20d == 0 → vol_ratio 스킵 (NaN 처리)
"""

import time
import functools
import logging
from datetime import date, timedelta

import numpy as np
import pandas as pd

from stocks.models import DailyPrice, SP500Constituent, Stock

logger = logging.getLogger(__name__)

THRESHOLDS = {
    'normal': {
        'P2_change_pct': 5.0,
        'P3_gap_ratio': 1.03,
        'P4_body_pct': 3.0,
        'P7_bounce_pct': 3.0,
        'V1_vol_ratio': 2.0,
    },
    'high_vol': {
        'P2_change_pct': 7.0,
        'P3_gap_ratio': 1.05,
        'P4_body_pct': 5.0,
        'P7_bounce_pct': 5.0,
        'V1_vol_ratio': 3.0,
    },
}


def profile_stage(func):
    """메서드 실행 시간 프로파일링 데코레이터. 30초 초과 시 WARNING 로그."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        if elapsed > 30:
            logger.warning(f"SLOW: {func.__name__} took {elapsed:.1f}s (>30s threshold)")
        else:
            logger.info(f"{func.__name__} completed in {elapsed:.1f}s")
        return result
    return wrapper


class EODSignalCalculator:
    """
    S&P 500 전 종목 EOD 시그널 계산기.

    DailyPrice에서 250일분 데이터를 bulk 로드한 뒤
    pandas 벡터 연산만으로 14개 시그널을 계산합니다.
    """

    def __init__(self):
        self.thresholds = THRESHOLDS

    @profile_stage
    def calculate_batch(self, target_date: date) -> pd.DataFrame:
        """
        S&P 500 전 종목의 250일 DailyPrice → DataFrame → 벡터 연산 → 시그널 DataFrame 반환.

        Args:
            target_date: 시그널 계산 대상 날짜

        Returns:
            target_date 행만 포함한 DataFrame (시그널 컬럼 포함)
        """
        df = self._load_price_data(target_date)
        if df.empty:
            logger.warning(f"[EODSignalCalculator] {target_date} 가격 데이터 없음")
            return pd.DataFrame()

        regime = self._get_vix_regime(target_date)
        logger.info(f"[EODSignalCalculator] VIX regime: {regime} (target_date={target_date})")

        df = self._calculate_indicators(df)
        result = self._detect_signals(df, regime, target_date)
        return result

    def _load_price_data(self, target_date: date) -> pd.DataFrame:
        """
        S&P500 종목의 250일 DailyPrice 데이터를 bulk 로드하여 long format DataFrame으로 반환.

        Columns: symbol, date, open, high, low, close, volume, sector, industry
        """
        symbols = list(
            SP500Constituent.objects.filter(is_active=True)
            .values_list('symbol', flat=True)
        )
        if not symbols:
            logger.warning("[EODSignalCalculator] 활성 S&P500 종목 없음")
            return pd.DataFrame()

        start_date = target_date - timedelta(days=365)  # 252 거래일 확보를 위해 365일 조회

        # sector/industry/market_cap 매핑
        stock_meta = Stock.objects.filter(symbol__in=symbols).values(
            'symbol', 'sector', 'industry', 'market_capitalization'
        )
        sector_map = {row['symbol']: row['sector'] or '' for row in stock_meta}
        industry_map = {row['symbol']: row['industry'] or '' for row in stock_meta}
        market_cap_map = {
            row['symbol']: int(row['market_capitalization']) if row['market_capitalization'] else None
            for row in stock_meta
        }

        rows = list(
            DailyPrice.objects.filter(
                stock__symbol__in=symbols,
                date__gte=start_date,
                date__lte=target_date,
            ).values_list(
                'stock__symbol',
                'date',
                'open_price',
                'high_price',
                'low_price',
                'close_price',
                'volume',
            )
        )

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=['symbol', 'date', 'open', 'high', 'low', 'close', 'volume'])

        # Decimal → float 변환
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col].astype(float)
        df['volume'] = df['volume'].astype(float)
        df['date'] = pd.to_datetime(df['date']).dt.date

        # sector / industry / market_cap 매핑
        df['sector'] = df['symbol'].map(sector_map).fillna('')
        df['industry'] = df['symbol'].map(industry_map).fillna('')
        df['market_cap'] = df['symbol'].map(market_cap_map)

        logger.info(f"[EODSignalCalculator] 로드 완료: {len(df)}행, {df['symbol'].nunique()}종목")
        return df

    def _get_vix_regime(self, target_date: date) -> str:
        """
        macro.MarketIndex에서 VIX 값을 조회하여 레짐 반환.

        Returns:
            'high_vol' if VIX > 25, else 'normal'
        """
        try:
            from macro.models import MarketIndexPrice, MarketIndex
            vix_index = MarketIndex.objects.filter(
                symbol__in=['VIX', '^VIX', 'VIXX'],
                category='volatility',
            ).first()
            if vix_index:
                price = (
                    MarketIndexPrice.objects.filter(
                        index=vix_index,
                        date__lte=target_date,
                    )
                    .order_by('-date')
                    .values_list('close', flat=True)
                    .first()
                )
                if price is not None and float(price) > 25:
                    return 'high_vol'
        except Exception as e:
            logger.warning(f"[EODSignalCalculator] VIX 조회 실패 (normal 기본값 사용): {e}")
        return 'normal'

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        groupby('symbol') 벡터 연산으로 모든 지표를 계산합니다.
        for-loop / iterrows / apply(custom_func) 금지.
        """
        df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
        g = df.groupby('symbol')

        # ── 기본 지표 ──────────────────────────────────────────────
        df['prev_close'] = g['close'].shift(1)
        df['change_pct'] = (
            (df['close'] - df['prev_close']) / df['prev_close'].replace(0, np.nan) * 100
        )

        # 20일 평균 거래량 (min_periods=10)
        df['avg_vol_20d'] = g['volume'].transform(
            lambda x: x.rolling(20, min_periods=10).mean()
        )
        # avg_vol_20d == 0 이면 NaN 처리
        df['vol_ratio'] = df['volume'] / df['avg_vol_20d'].replace(0, np.nan)

        # ── SMA ────────────────────────────────────────────────────
        df['sma_50'] = g['close'].transform(
            lambda x: x.rolling(50, min_periods=40).mean()
        )
        df['sma_200'] = g['close'].transform(
            lambda x: x.rolling(200, min_periods=150).mean()
        )
        df['prev_sma_50'] = g['sma_50'].shift(1)
        df['prev_sma_200'] = g['sma_200'].shift(1)

        # ── RSI (14) ────────────────────────────────────────────────
        delta = g['close'].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        df['avg_gain_14'] = gain.groupby(df['symbol']).transform(
            lambda x: x.rolling(14, min_periods=14).mean()
        )
        df['avg_loss_14'] = loss.groupby(df['symbol']).transform(
            lambda x: x.rolling(14, min_periods=14).mean()
        )
        rs = df['avg_gain_14'] / df['avg_loss_14'].replace(0, np.nan)
        df['rsi_14'] = 100 - (100 / (1 + rs))

        # ── 52주 최고가 ─────────────────────────────────────────────
        df['high_52w'] = g['high'].transform(
            lambda x: x.rolling(252, min_periods=200).max()
        )

        # ── 연속 상승/하락 (cumsum trick) ───────────────────────────
        df['up'] = (df['close'] > df['prev_close']).astype(int)
        df['down'] = (df['close'] < df['prev_close']).astype(int)

        # 연속 카운트: 그룹 내에서 값이 바뀌는 지점마다 reset
        def _count_consecutive(s: pd.Series) -> pd.Series:
            """값이 1인 구간의 연속 카운트. 0이면 0 유지."""
            reset = s.ne(s.shift()).cumsum()
            counts = s.groupby(reset).cumsum()
            return counts.where(s == 1, 0)

        df['consecutive_up'] = df.groupby('symbol')['up'].transform(_count_consecutive)
        df['consecutive_down'] = df.groupby('symbol')['down'].transform(_count_consecutive)

        # ── 봉 분석 ─────────────────────────────────────────────────
        df['body'] = (df['close'] - df['open']).abs()
        df['range'] = df['high'] - df['low']
        df['body_pct'] = df['body'] / df['prev_close'].replace(0, np.nan) * 100
        df['body_ratio'] = df['body'] / df['range'].replace(0, np.nan)
        # high == low 인 경우 body_ratio = 0.5
        df.loc[df['high'] == df['low'], 'body_ratio'] = 0.5

        # ── 저가 대비 반등률 ─────────────────────────────────────────
        df['bounce_pct'] = (
            (df['close'] - df['low']) / df['low'].replace(0, np.nan) * 100
        )

        # ── 달러 거래량 ──────────────────────────────────────────────
        df['dollar_volume'] = df['close'] * df['volume']

        # ── 섹터 평균 변동률 (relation signals) ──────────────────────
        df['sector_avg_change'] = df.groupby(['date', 'sector'])['change_pct'].transform('mean')

        return df

    def _detect_signals(self, df: pd.DataFrame, regime: str, target_date: date) -> pd.DataFrame:
        """
        target_date 행만 필터링하여 14개 시그널을 감지합니다.
        각 시그널은 sig_{ID}, sig_{ID}_value, sig_{ID}_direction 컬럼으로 저장.
        """
        today = df[df['date'] == target_date].copy()
        if today.empty:
            logger.warning(f"[EODSignalCalculator] {target_date} target_date 행 없음")
            return pd.DataFrame()

        t = self.thresholds[regime]

        spy_change = self._get_spy_change(df, target_date)

        # ── P1: 연속 상승/하락 (3일 이상) ───────────────────────────
        today['sig_P1'] = (today['consecutive_up'] >= 3) | (today['consecutive_down'] >= 3)
        today['sig_P1_value'] = np.where(
            today['consecutive_up'] >= 3,
            today['consecutive_up'],
            np.where(today['consecutive_down'] >= 3, -today['consecutive_down'], 0.0),
        )
        today['sig_P1_direction'] = np.where(
            today['consecutive_up'] >= 3, 'bullish',
            np.where(today['consecutive_down'] >= 3, 'bearish', ''),
        )

        # ── P2: 수익률 상위 ──────────────────────────────────────────
        today['sig_P2'] = today['change_pct'].abs() > t['P2_change_pct']
        today['sig_P2_value'] = today['change_pct']
        today['sig_P2_direction'] = np.where(today['change_pct'] > 0, 'bullish', 'bearish')

        # ── P3: 갭 감지 ──────────────────────────────────────────────
        gap_ratio = t['P3_gap_ratio']
        inverse_ratio = 2.0 - gap_ratio  # 0.97 or 0.95
        today['sig_P3_up'] = today['open'] > (today['prev_close'] * gap_ratio)
        today['sig_P3_down'] = today['open'] < (today['prev_close'] * inverse_ratio)
        today['sig_P3'] = today['sig_P3_up'] | today['sig_P3_down']
        today['sig_P3_value'] = (today['open'] - today['prev_close']) / today['prev_close'].replace(0, np.nan) * 100
        today['sig_P3_direction'] = np.where(
            today['sig_P3_up'], 'bullish',
            np.where(today['sig_P3_down'], 'bearish', ''),
        )

        # ── P4: 장대양봉/음봉 ────────────────────────────────────────
        today['sig_P4'] = (today['body_pct'] > t['P4_body_pct']) & (today['body_ratio'] > 0.6)
        today['sig_P4_value'] = today['body_pct']
        today['sig_P4_direction'] = np.where(
            today['close'] > today['open'], 'bullish', 'bearish'
        )
        # body_pct가 NaN이면 sig_P4도 False
        today.loc[today['body_pct'].isna(), 'sig_P4'] = False

        # ── P5: 52주 신고가 근접 ─────────────────────────────────────
        today['sig_P5'] = today['close'] >= (today['high_52w'] * 0.95)
        today['sig_P5_value'] = today['close'] / today['high_52w'].replace(0, np.nan) * 100
        today['sig_P5_direction'] = 'bullish'
        # high_52w가 NaN이면 False
        today.loc[today['high_52w'].isna(), 'sig_P5'] = False

        # ── P7: 저가 대비 반등률 ─────────────────────────────────────
        today['sig_P7'] = (
            (today['bounce_pct'] > t['P7_bounce_pct']) &
            (today['close'] > today['open'])
        )
        today['sig_P7_value'] = today['bounce_pct']
        today['sig_P7_direction'] = 'bullish'
        today.loc[today['bounce_pct'].isna(), 'sig_P7'] = False

        # ── V1: 거래량 폭발 ──────────────────────────────────────────
        today['sig_V1'] = today['vol_ratio'] >= t['V1_vol_ratio']
        today['sig_V1_value'] = today['vol_ratio']
        today['sig_V1_direction'] = 'neutral'
        today.loc[today['vol_ratio'].isna(), 'sig_V1'] = False

        # ── PV1: 가격-거래량 효율성 ──────────────────────────────────
        today['sig_PV1'] = (today['change_pct'].abs() > 2.0) & (today['vol_ratio'] < 1.0)
        today['sig_PV1_value'] = today['change_pct']
        today['sig_PV1_direction'] = np.where(today['change_pct'] > 0, 'bullish', 'bearish')
        today.loc[today['vol_ratio'].isna(), 'sig_PV1'] = False

        # ── PV2: 매집 의심 ───────────────────────────────────────────
        today['sig_PV2'] = (today['vol_ratio'] > 2.0) & (today['change_pct'].abs() < 1.0)
        today['sig_PV2_value'] = today['vol_ratio']
        today['sig_PV2_direction'] = 'neutral'
        today.loc[today['vol_ratio'].isna(), 'sig_PV2'] = False

        # ── MA1: 골든/데드크로스 ─────────────────────────────────────
        golden = (
            (today['sma_50'] > today['sma_200']) &
            (today['prev_sma_50'] <= today['prev_sma_200'])
        )
        dead = (
            (today['sma_50'] < today['sma_200']) &
            (today['prev_sma_50'] >= today['prev_sma_200'])
        )
        today['sig_MA1'] = golden | dead
        today['sig_MA1_value'] = today['sma_50'] - today['sma_200']
        today['sig_MA1_direction'] = np.where(golden, 'bullish', np.where(dead, 'bearish', ''))
        # SMA가 NaN이면 False
        ma_nan = today['sma_50'].isna() | today['sma_200'].isna() | today['prev_sma_50'].isna() | today['prev_sma_200'].isna()
        today.loc[ma_nan, 'sig_MA1'] = False

        # ── T1: RSI 과매도/과매수 ─────────────────────────────────────
        oversold = today['rsi_14'] < 30
        overbought = today['rsi_14'] > 70
        today['sig_T1'] = oversold | overbought
        today['sig_T1_value'] = today['rsi_14']
        today['sig_T1_direction'] = np.where(
            oversold, 'bullish',
            np.where(overbought, 'bearish', ''),
        )
        today.loc[today['rsi_14'].isna(), 'sig_T1'] = False

        # ── S1: 섹터 상대 강도 ───────────────────────────────────────
        today['rel_vs_sector'] = today['change_pct'] - today['sector_avg_change']
        today['sig_S1'] = today['rel_vs_sector'] >= 3.0
        today['sig_S1_value'] = today['rel_vs_sector']
        today['sig_S1_direction'] = 'bullish'
        today.loc[today['sector_avg_change'].isna(), 'sig_S1'] = False

        # ── S2: 섹터 소외주 (섹터 상승일, 혼자 하락) ─────────────────
        sector_rising = today['sector_avg_change'] > 0
        today['sig_S2'] = sector_rising & (today['rel_vs_sector'] <= -3.0)
        today['sig_S2_value'] = today['rel_vs_sector']
        today['sig_S2_direction'] = 'bearish'
        today.loc[today['sector_avg_change'].isna(), 'sig_S2'] = False

        # ── S4: 폭락장 생존자 ────────────────────────────────────────
        if spy_change <= -2.0:
            today['sig_S4'] = today['change_pct'] >= -0.5
            today['sig_S4_value'] = today['change_pct']
            today['sig_S4_direction'] = 'bullish'
        else:
            today['sig_S4'] = False
            today['sig_S4_value'] = today['change_pct']
            today['sig_S4_direction'] = ''

        return today.reset_index(drop=True)

    def _get_spy_change(self, df: pd.DataFrame, target_date: date) -> float:
        """
        SPY의 target_date 변동률 반환 (S4 시그널용).
        SPY가 없으면 0.0 반환.
        """
        spy_row = df[(df['symbol'] == 'SPY') & (df['date'] == target_date)]
        if spy_row.empty:
            return 0.0
        val = spy_row['change_pct'].values[0]
        if pd.isna(val):
            return 0.0
        return float(val)
