"""
키워드 → 섹터 매핑 사전 (News Intelligence Pipeline v3 - Engine B)

16개 카테고리의 키워드-섹터 매핑을 제공합니다.
뉴스 제목/본문에서 키워드를 매칭하여 관련 섹터를 추출합니다.
"""

# 키워드 → 섹터 매핑 사전
# key: 소문자 키워드, value: 섹터명
KEYWORD_SECTOR_MAP = {
    # ── Technology ──
    'semiconductor': 'Technology',
    'chip': 'Technology',
    'chipmaker': 'Technology',
    'ai': 'Technology',
    'artificial intelligence': 'Technology',
    'machine learning': 'Technology',
    'cloud computing': 'Technology',
    'cloud': 'Technology',
    'saas': 'Technology',
    'software': 'Technology',
    'cybersecurity': 'Technology',
    'data center': 'Technology',
    'gpu': 'Technology',
    'processor': 'Technology',
    'tech': 'Technology',
    'big tech': 'Technology',
    'faang': 'Technology',
    'magnificent seven': 'Technology',
    'mag 7': 'Technology',

    # ── Communication Services ──
    'social media': 'Communication Services',
    'streaming': 'Communication Services',
    'digital advertising': 'Communication Services',
    'ad revenue': 'Communication Services',
    'telecom': 'Communication Services',
    '5g': 'Communication Services',
    'broadband': 'Communication Services',
    'media': 'Communication Services',

    # ── Healthcare ──
    'pharma': 'Healthcare',
    'pharmaceutical': 'Healthcare',
    'biotech': 'Healthcare',
    'biotechnology': 'Healthcare',
    'fda': 'Healthcare',
    'drug': 'Healthcare',
    'vaccine': 'Healthcare',
    'clinical trial': 'Healthcare',
    'healthcare': 'Healthcare',
    'medical device': 'Healthcare',
    'hospital': 'Healthcare',
    'health insurance': 'Healthcare',
    'obesity drug': 'Healthcare',
    'glp-1': 'Healthcare',

    # ── Financials ──
    'bank': 'Financials',
    'banking': 'Financials',
    'interest rate': 'Financials',
    'loan': 'Financials',
    'credit': 'Financials',
    'mortgage': 'Financials',
    'insurance': 'Financials',
    'fintech': 'Financials',
    'investment bank': 'Financials',
    'asset management': 'Financials',
    'hedge fund': 'Financials',
    'ipo': 'Financials',

    # ── Consumer Discretionary ──
    'retail': 'Consumer Discretionary',
    'e-commerce': 'Consumer Discretionary',
    'ecommerce': 'Consumer Discretionary',
    'luxury': 'Consumer Discretionary',
    'consumer spending': 'Consumer Discretionary',
    'automotive': 'Consumer Discretionary',
    'electric vehicle': 'Consumer Discretionary',
    'ev': 'Consumer Discretionary',
    'housing': 'Consumer Discretionary',
    'homebuilder': 'Consumer Discretionary',
    'restaurant': 'Consumer Discretionary',
    'travel': 'Consumer Discretionary',
    'hotel': 'Consumer Discretionary',
    'airline': 'Consumer Discretionary',

    # ── Consumer Staples ──
    'grocery': 'Consumer Staples',
    'food': 'Consumer Staples',
    'beverage': 'Consumer Staples',
    'tobacco': 'Consumer Staples',
    'personal care': 'Consumer Staples',
    'household': 'Consumer Staples',
    'consumer staple': 'Consumer Staples',
    'packaged food': 'Consumer Staples',

    # ── Energy ──
    'oil': 'Energy',
    'crude oil': 'Energy',
    'natural gas': 'Energy',
    'opec': 'Energy',
    'petroleum': 'Energy',
    'drilling': 'Energy',
    'refinery': 'Energy',
    'energy': 'Energy',
    'pipeline': 'Energy',
    'lng': 'Energy',
    'shale': 'Energy',

    # ── Industrials ──
    'defense': 'Industrials',
    'aerospace': 'Industrials',
    'manufacturing': 'Industrials',
    'construction': 'Industrials',
    'logistics': 'Industrials',
    'shipping': 'Industrials',
    'freight': 'Industrials',
    'industrial': 'Industrials',
    'infrastructure': 'Industrials',
    'railroad': 'Industrials',

    # ── Materials ──
    'mining': 'Materials',
    'gold': 'Materials',
    'copper': 'Materials',
    'steel': 'Materials',
    'lithium': 'Materials',
    'rare earth': 'Materials',
    'chemical': 'Materials',
    'commodity': 'Materials',
    'aluminum': 'Materials',

    # ── Utilities ──
    'utility': 'Utilities',
    'utilities': 'Utilities',
    'nuclear': 'Utilities',
    'power grid': 'Utilities',
    'electricity': 'Utilities',
    'solar': 'Utilities',
    'wind energy': 'Utilities',
    'renewable': 'Utilities',
    'clean energy': 'Utilities',

    # ── Real Estate ──
    'reit': 'Real Estate',
    'real estate': 'Real Estate',
    'property': 'Real Estate',
    'commercial real estate': 'Real Estate',
    'office space': 'Real Estate',
    'data center reit': 'Real Estate',

    # ── Macro / Central Bank ──
    'fed': 'Macro',
    'federal reserve': 'Macro',
    'rate cut': 'Macro',
    'rate hike': 'Macro',
    'inflation': 'Macro',
    'cpi': 'Macro',
    'pce': 'Macro',
    'gdp': 'Macro',
    'employment': 'Macro',
    'jobs report': 'Macro',
    'nonfarm payroll': 'Macro',
    'unemployment': 'Macro',
    'treasury': 'Macro',
    'yield curve': 'Macro',
    'bond': 'Macro',
    'recession': 'Macro',
    'monetary policy': 'Macro',

    # ── Crypto ──
    'bitcoin': 'Crypto',
    'btc': 'Crypto',
    'ethereum': 'Crypto',
    'crypto': 'Crypto',
    'cryptocurrency': 'Crypto',
    'blockchain': 'Crypto',
    'defi': 'Crypto',
    'stablecoin': 'Crypto',
    'bitcoin etf': 'Crypto',

    # ── Geopolitical ──
    'tariff': 'Geopolitical',
    'trade war': 'Geopolitical',
    'sanction': 'Geopolitical',
    'geopolitical': 'Geopolitical',
    'china': 'Geopolitical',
    'taiwan': 'Geopolitical',
    'export control': 'Geopolitical',
    'trade restriction': 'Geopolitical',

    # ── Regulation ──
    'antitrust': 'Regulation',
    'regulation': 'Regulation',
    'sec': 'Regulation',
    'compliance': 'Regulation',
    'data privacy': 'Regulation',
    'ftc': 'Regulation',
    'doj': 'Regulation',

    # ── ESG ──
    'esg': 'ESG',
    'carbon': 'ESG',
    'sustainability': 'ESG',
    'climate': 'ESG',
    'green': 'ESG',
    'net zero': 'ESG',
    'emissions': 'ESG',
}

# 역방향: 섹터 → 키워드 리스트 (빠른 조회용)
SECTOR_KEYWORDS = {}
for keyword, sector in KEYWORD_SECTOR_MAP.items():
    SECTOR_KEYWORDS.setdefault(sector, []).append(keyword)


def match_sectors(text: str) -> list[str]:
    """
    텍스트에서 키워드 매칭으로 관련 섹터를 추출합니다.

    Args:
        text: 뉴스 제목 + 본문 텍스트

    Returns:
        매칭된 섹터 리스트 (중복 제거, 매칭 빈도 순)
    """
    if not text:
        return []

    text_lower = text.lower()
    sector_counts = {}

    for keyword, sector in KEYWORD_SECTOR_MAP.items():
        if keyword in text_lower:
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

    # 매칭 빈도 순으로 정렬
    sorted_sectors = sorted(
        sector_counts.keys(),
        key=lambda s: sector_counts[s],
        reverse=True
    )
    return sorted_sectors
