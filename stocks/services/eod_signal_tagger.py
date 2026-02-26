"""
EOD Signal Tagger (Step 3)

시그널 태깅 + 카드 빌더.
EODSignalCalculator가 반환한 DataFrame의 각 행을 인간이 읽을 수 있는
시그널 리스트(dict)로 변환합니다.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

SIGNAL_CATEGORIES = {
    'P1': 'momentum',
    'P2': 'momentum',
    'P3': 'momentum',
    'P4': 'momentum',
    'P5': 'breakout',
    'P7': 'reversal',
    'V1': 'volume',
    'PV1': 'volume',
    'PV2': 'volume',
    'MA1': 'technical',
    'T1': 'technical',
    'S1': 'relation',
    'S2': 'relation',
    'S4': 'relation',
}

CATEGORY_COLORS = {
    'momentum': '#F0883E',
    'volume': '#58A6FF',
    'breakout': '#3FB950',
    'reversal': '#A371F7',
    'relation': '#A371F7',
    'technical': '#8B949E',
}

CATEGORY_PRIORITY = ['relation', 'volume', 'momentum', 'breakout', 'reversal', 'technical']

SIGNAL_METADATA = {
    'P1': {'title': '연속 상승/하락', 'description_ko': 'N일 연속 상승 또는 하락'},
    'P2': {'title': '수익률 상위', 'description_ko': '하루 변동폭 5% 이상'},
    'P3': {'title': '갭 감지', 'description_ko': '장시작 시 3% 이상 갭'},
    'P4': {'title': '장대양봉/음봉', 'description_ko': '강한 추세의 캔들 패턴'},
    'P5': {'title': '52주 신고가 근접', 'description_ko': '52주 최고가의 95% 이상'},
    'P7': {'title': '저가 반등', 'description_ko': '장중 저가에서 3% 이상 반등'},
    'V1': {'title': '거래량 폭발', 'description_ko': '평소의 2배 이상 거래'},
    'PV1': {'title': '가격-거래량 효율성', 'description_ko': '적은 거래량으로 큰 가격 변동'},
    'PV2': {'title': '매집 의심', 'description_ko': '거래량 급증인데 가격 변동 미미'},
    'MA1': {'title': '골든/데드크로스', 'description_ko': 'SMA50과 SMA200 교차'},
    'T1': {'title': 'RSI 과매도/과매수', 'description_ko': 'RSI 30 이하 또는 70 이상'},
    'S1': {'title': '섹터 상대 강도', 'description_ko': '섹터 평균 대비 3%p 이상 상회'},
    'S2': {'title': '섹터 소외주', 'description_ko': '섹터 상승 시 혼자 하락'},
    'S4': {'title': '폭락장 생존자', 'description_ko': 'SPY 하락일에 보합/상승 유지'},
}

EDUCATION_TIPS = {
    'P1': {
        'tip': '연속 상승/하락은 추세의 강도를 보여줍니다',
        'risk': '추세 반전 시점을 놓칠 수 있으니 다른 지표와 함께 확인하세요',
    },
    'P2': {
        'tip': '큰 변동은 시장의 강한 반응을 의미합니다',
        'risk': '급등 후 조정이 올 수 있으므로 추격 매수에 주의하세요',
    },
    'P3': {
        'tip': '갭은 시간 외에 발생한 강한 이벤트를 반영합니다',
        'risk': '갭상승 후 되돌림이 빈번합니다. 진입 시점을 신중히 판단하세요',
    },
    'P4': {
        'tip': '장대봉은 해당 방향으로의 강한 의지를 보여줍니다',
        'risk': '단기 과열 신호일 수 있으니 거래량과 함께 확인하세요',
    },
    'P5': {
        'tip': '신고가 근접은 강한 상승 모멘텀을 의미합니다',
        'risk': '저항선 돌파 실패 시 조정이 올 수 있습니다',
    },
    'P7': {
        'tip': '장중 저가에서 반등은 매수세가 살아있다는 신호입니다',
        'risk': '일시적 반등일 수 있으므로 다음날 추세를 확인하세요',
    },
    'V1': {
        'tip': '거래량은 시장 관심의 크기를 보여줍니다',
        'risk': '단기 과열일 수 있으니 추격 매수에 주의하세요',
    },
    'PV1': {
        'tip': '적은 거래량으로 큰 변동은 정보 비대칭을 시사합니다',
        'risk': '유동성 부족 시 급격한 반전 가능성이 있습니다',
    },
    'PV2': {
        'tip': '거래량만 늘고 가격이 안 움직이면 기관 매집 가능성',
        'risk': '매집이 아닌 매도 물량 소화일 수도 있습니다',
    },
    'MA1': {
        'tip': '이동평균 교차는 중장기 추세 전환 신호입니다',
        'risk': '횡보장에서는 잦은 거짓 신호가 발생합니다',
    },
    'T1': {
        'tip': 'RSI 극단값은 과열/침체 구간을 알려줍니다',
        'risk': '강한 추세에서는 과매수/과매도가 오래 지속될 수 있습니다',
    },
    'S1': {
        'tip': '섹터보다 강한 종목은 개별 모멘텀이 있습니다',
        'risk': '섹터 전체가 하락 전환하면 함께 빠질 수 있습니다',
    },
    'S2': {
        'tip': '섹터 상승 시 소외된 종목은 개별 악재가 있을 수 있습니다',
        'risk': '저평가가 아닌 실적 악화 때문일 수 있으니 원인을 확인하세요',
    },
    'S4': {
        'tip': '시장 하락에도 버티는 종목은 방어력이 강합니다',
        'risk': '시장 반등 시 상대적으로 상승폭이 작을 수 있습니다',
    },
}

# 모든 지원 시그널 ID (순서 유지)
ALL_SIGNAL_IDS = ['P1', 'P2', 'P3', 'P4', 'P5', 'P7', 'V1', 'PV1', 'PV2', 'MA1', 'T1', 'S1', 'S2', 'S4']


class EODSignalTagger:
    """
    EODSignalCalculator가 반환한 DataFrame을 태깅하여
    프론트엔드에서 바로 소비할 수 있는 dict 리스트로 변환합니다.
    """

    def tag_signals(self, signals_df: pd.DataFrame) -> list[dict]:
        """
        DataFrame의 각 행을 시그널 리스트로 변환합니다.

        Args:
            signals_df: EODSignalCalculator.calculate_batch() 반환값

        Returns:
            [{
                'stock_id': 'NVDA',
                'signals': [...],
                'tag_details': {...},
                'signal_count': 3,
                'bullish_count': 2,
                'bearish_count': 0,
                'composite_score': 0.67,
                'close': 142.3,
                'change_pct': 5.2,
                'volume': 150000000,
                'dollar_volume': 21345000000,
                'sector': 'Technology',
                'industry': 'Semiconductors',
                'market_cap': 3500000000000,
            }, ...]
        """
        if signals_df.empty:
            return []

        results = []
        for _, row in signals_df.iterrows():
            signals = self._build_signal_list(row)
            tag_details = self._determine_primary_tag(signals)
            composite_score = self._calculate_composite_score(signals)
            bullish_count = sum(1 for s in signals if s['direction'] == 'bullish')
            bearish_count = sum(1 for s in signals if s['direction'] == 'bearish')

            market_cap_val = row.get('market_cap')
            if pd.isna(market_cap_val) if isinstance(market_cap_val, float) else market_cap_val is None:
                market_cap_val = None
            else:
                try:
                    market_cap_val = int(market_cap_val)
                except (ValueError, TypeError):
                    market_cap_val = None

            results.append({
                'stock_id': row['symbol'],
                'signals': signals,
                'tag_details': tag_details,
                'signal_count': len(signals),
                'bullish_count': bullish_count,
                'bearish_count': bearish_count,
                'composite_score': composite_score,
                'close': float(row['close']) if not pd.isna(row['close']) else 0.0,
                'change_pct': float(row['change_pct']) if not pd.isna(row.get('change_pct', float('nan'))) else 0.0,
                'volume': int(row['volume']) if not pd.isna(row['volume']) else 0,
                'dollar_volume': float(row.get('dollar_volume', 0.0)) if not pd.isna(row.get('dollar_volume', float('nan'))) else 0.0,
                'sector': str(row.get('sector', '')),
                'industry': str(row.get('industry', '')),
                'market_cap': market_cap_val,
            })

        logger.info(f"[EODSignalTagger] 태깅 완료: {len(results)}종목")
        return results

    def _build_signal_list(self, row: pd.Series) -> list[dict]:
        """
        단일 행에서 활성(True) 시그널을 추출하여 리스트로 반환합니다.
        """
        signals = []
        for sig_id in ALL_SIGNAL_IDS:
            col = f'sig_{sig_id}'
            if col not in row.index:
                continue
            is_active = row[col]
            # NaN 처리
            if pd.isna(is_active):
                continue
            if not bool(is_active):
                continue

            value_col = f'sig_{sig_id}_value'
            dir_col = f'sig_{sig_id}_direction'

            raw_value = row.get(value_col, 0.0)
            direction = row.get(dir_col, 'neutral') or 'neutral'

            value = float(raw_value) if (raw_value is not None and not pd.isna(raw_value)) else 0.0

            category = SIGNAL_CATEGORIES.get(sig_id, 'technical')
            label = self._generate_signal_label(sig_id, value, direction)

            signals.append({
                'id': sig_id,
                'category': category,
                'color': CATEGORY_COLORS.get(category, '#8B949E'),
                'title': SIGNAL_METADATA[sig_id]['title'],
                'description_ko': SIGNAL_METADATA[sig_id]['description_ko'],
                'direction': direction,
                'value': round(value, 4),
                'label': label,
                'education_tip': EDUCATION_TIPS[sig_id]['tip'],
                'education_risk': EDUCATION_TIPS[sig_id]['risk'],
            })

        return signals

    def _determine_primary_tag(self, signals: list[dict]) -> dict:
        """
        CATEGORY_PRIORITY 기준으로 primary 시그널과 sub_tags를 결정합니다.

        Returns:
            {"primary": "V1", "sub_tags": ["P2", "S1"]}
        """
        if not signals:
            return {'primary': None, 'sub_tags': []}

        # 카테고리 우선순위 맵
        priority_map = {cat: idx for idx, cat in enumerate(CATEGORY_PRIORITY)}

        # primary: 우선순위가 가장 높은 카테고리의 시그널 중 첫 번째
        sorted_signals = sorted(
            signals,
            key=lambda s: (priority_map.get(s['category'], 99),),
        )
        primary = sorted_signals[0]['id']
        sub_tags = [s['id'] for s in sorted_signals[1:]]

        return {'primary': primary, 'sub_tags': sub_tags}

    def _calculate_composite_score(self, signals: list[dict]) -> float:
        """
        bullish=+1, bearish=-1, neutral=0 평균으로 복합 점수를 계산합니다.
        범위: -1.0 ~ +1.0. 시그널이 없으면 0.0.
        """
        if not signals:
            return 0.0

        scores = []
        for s in signals:
            direction = s.get('direction', 'neutral')
            if direction == 'bullish':
                scores.append(1.0)
            elif direction == 'bearish':
                scores.append(-1.0)
            else:
                scores.append(0.0)

        return round(sum(scores) / len(scores), 4)

    def _generate_signal_label(self, signal_id: str, value: float, direction: str) -> str:
        """
        사람이 읽을 수 있는 한국어 레이블을 생성합니다.

        Examples:
            V1, value=3.8  → "거래량 3.8배"
            P1, value=5    → "5일 연속 상승"
            P1, value=-3   → "3일 연속 하락"
            P2, value=6.2  → "+6.2% 변동"
            P3, value=4.1  → "+4.1% 갭상승"
            MA1, bullish   → "골든크로스"
            T1, value=25   → "RSI 25 (과매도)"
            S1, value=5.2  → "섹터 대비 +5.2%p"
            S4             → "폭락장 생존"
        """
        if signal_id == 'P1':
            days = abs(int(value)) if value != 0 else 0
            if value > 0:
                return f"{days}일 연속 상승"
            elif value < 0:
                return f"{days}일 연속 하락"
            return "연속 변동"

        elif signal_id == 'P2':
            sign = '+' if value >= 0 else ''
            return f"{sign}{value:.1f}% 변동"

        elif signal_id == 'P3':
            if value >= 0:
                return f"+{value:.1f}% 갭상승"
            return f"{value:.1f}% 갭하락"

        elif signal_id == 'P4':
            if direction == 'bullish':
                return f"장대양봉 ({value:.1f}%)"
            return f"장대음봉 ({value:.1f}%)"

        elif signal_id == 'P5':
            return f"52주 고가 {value:.1f}%"

        elif signal_id == 'P7':
            return f"저가 대비 +{value:.1f}% 반등"

        elif signal_id == 'V1':
            return f"거래량 {value:.1f}배"

        elif signal_id == 'PV1':
            sign = '+' if value >= 0 else ''
            return f"가격{sign}{value:.1f}% / 거래량 소량"

        elif signal_id == 'PV2':
            return f"거래량 {value:.1f}배 (가격 보합)"

        elif signal_id == 'MA1':
            if direction == 'bullish':
                return "골든크로스"
            elif direction == 'bearish':
                return "데드크로스"
            return "이평선 교차"

        elif signal_id == 'T1':
            rsi_val = round(value, 1)
            if rsi_val < 30:
                return f"RSI {rsi_val} (과매도)"
            elif rsi_val > 70:
                return f"RSI {rsi_val} (과매수)"
            return f"RSI {rsi_val}"

        elif signal_id == 'S1':
            return f"섹터 대비 +{value:.1f}%p"

        elif signal_id == 'S2':
            return f"섹터 대비 {value:.1f}%p"

        elif signal_id == 'S4':
            return "폭락장 생존"

        return SIGNAL_METADATA.get(signal_id, {}).get('title', signal_id)
