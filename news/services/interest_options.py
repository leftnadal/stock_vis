"""
Interest Options Service - 사용자 관심사 선택지 제공

사전 정의 테마 + SP500 GICS 섹터를 조합하여 관심사 옵션을 제공합니다.
"""

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# 사전 정의 테마 (category_generator.py THEME_KEYWORDS 기반)
PREDEFINED_THEMES = [
    {
        'value': 'ai_semiconductor',
        'display_name': 'AI & 반도체',
        'keywords': ['AI', 'semiconductor', 'GPU', 'chip'],
        'symbols': ['NVDA', 'AMD', 'INTC', 'AVGO', 'QCOM'],
    },
    {
        'value': 'ev_battery',
        'display_name': '전기차 & 배터리',
        'keywords': ['EV', 'electric vehicle', 'battery', 'charging'],
        'symbols': ['TSLA', 'RIVN', 'NIO', 'LI', 'XPEV'],
    },
    {
        'value': 'cloud_saas',
        'display_name': '클라우드 & SaaS',
        'keywords': ['cloud', 'SaaS', 'AWS', 'Azure'],
        'symbols': ['AMZN', 'MSFT', 'GOOGL', 'CRM', 'SNOW'],
    },
    {
        'value': 'biotech_pharma',
        'display_name': '바이오 & 제약',
        'keywords': ['biotech', 'pharma', 'FDA', 'drug'],
        'symbols': ['JNJ', 'PFE', 'ABBV', 'MRK', 'LLY'],
    },
    {
        'value': 'fintech_payment',
        'display_name': '핀테크 & 결제',
        'keywords': ['fintech', 'payment', 'digital banking'],
        'symbols': ['V', 'MA', 'PYPL', 'SQ', 'COIN'],
    },
    {
        'value': 'clean_energy',
        'display_name': '클린에너지',
        'keywords': ['solar', 'wind', 'renewable', 'clean energy'],
        'symbols': ['ENPH', 'SEDG', 'FSLR', 'NEE', 'PLUG'],
    },
    {
        'value': 'gaming_metaverse',
        'display_name': '게임 & 메타버스',
        'keywords': ['gaming', 'metaverse', 'VR', 'AR'],
        'symbols': ['RBLX', 'U', 'EA', 'TTWO', 'META'],
    },
    {
        'value': 'cybersecurity',
        'display_name': '사이버보안',
        'keywords': ['cybersecurity', 'security', 'firewall'],
        'symbols': ['CRWD', 'PANW', 'ZS', 'FTNT', 'S'],
    },
]


class InterestOptionsService:
    """관심사 선택지 제공 서비스"""

    CACHE_KEY = 'interest_options'
    CACHE_TTL = 3600  # 1시간

    def get_options(self) -> dict:
        """테마 + 섹터 옵션 반환"""
        cached = cache.get(self.CACHE_KEY)
        if cached:
            return cached

        themes = [
            {
                'interest_type': 'theme',
                'value': t['value'],
                'display_name': t['display_name'],
                'sample_symbols': t['symbols'][:3],
            }
            for t in PREDEFINED_THEMES
        ]

        sectors = self._get_sector_options()

        result = {
            'themes': themes,
            'sectors': sectors,
        }

        cache.set(self.CACHE_KEY, result, self.CACHE_TTL)
        return result

    def _get_sector_options(self) -> list:
        """SP500Constituent의 distinct sector 조회"""
        try:
            from stocks.models import SP500Constituent
            sectors = (
                SP500Constituent.objects
                .filter(is_active=True)
                .values_list('sector', flat=True)
                .distinct()
                .order_by('sector')
            )
            return [
                {
                    'interest_type': 'sector',
                    'value': s,
                    'display_name': s,
                    'sample_symbols': list(
                        SP500Constituent.objects
                        .filter(sector=s, is_active=True)
                        .values_list('symbol', flat=True)[:3]
                    ),
                }
                for s in sectors if s
            ]
        except Exception as e:
            logger.debug(f"SP500Constituent not available: {e}")
            return []

    @staticmethod
    def get_theme_symbols(value: str) -> list:
        """테마 value로 관련 심볼 조회"""
        for t in PREDEFINED_THEMES:
            if t['value'] == value:
                return t['symbols']
        return []
