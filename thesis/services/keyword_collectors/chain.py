"""Chain Keyword Collector: Neo4j 관계 → ContextKeyword 변환 (Phase B, PR-10)

템플릿 기반 — Neo4j 관계 타입별 키워드 생성. 추가 LLM 호출 없음.
"""

import logging

from thesis.services.builder_events import log_event
from thesis.services.keyword_cache import ContextKeyword, save_keywords

logger = logging.getLogger(__name__)

# 관계 타입 → ContextKeyword 템플릿
CHAIN_TEMPLATES = {
    'SUPPLIES_TO': lambda t, r: ContextKeyword(f"{r} 공급 관계", 'chain', 'theme'),
    'SUPPLIED_BY': lambda t, r: ContextKeyword(f"{r} 공급받는 관계", 'chain', 'theme'),
    'CUSTOMER_OF': lambda t, r: ContextKeyword(f"{r} 고객 관계", 'chain', 'theme'),
    'PEER_OF': lambda t, r: ContextKeyword(f"{r} 경쟁 구도", 'chain', 'risk'),
    'COMPETES_WITH': lambda t, r: ContextKeyword(f"{r} 경쟁 구도", 'chain', 'risk'),
    'HAS_THEME': lambda t, r: ContextKeyword(f"{r} 테마 연관", 'chain', 'theme'),
    'CO_MENTIONED': lambda t, r: ContextKeyword(f"{r} 뉴스 동시 언급", 'chain', 'theme'),
    'PARTNER_OF': lambda t, r: ContextKeyword(f"{r} 파트너십", 'chain', 'support'),
    'HELD_BY_SAME_FUND': lambda t, r: ContextKeyword(f"{r} ETF 공동 편입", 'chain', 'support'),
    'SAME_INDUSTRY': lambda t, r: ContextKeyword(f"{r} 동종 업종", 'chain', 'theme'),
}


def extract_chain_keywords(target: str) -> list[ContextKeyword]:
    """
    Neo4j에서 target 종목의 관계를 조회하여 키워드로 변환.
    Neo4j 미연결 시 빈 리스트 반환 (silent degrade).
    """
    try:
        from serverless.services.neo4j_chain_sight_service import Neo4jChainSightService
    except ImportError:
        logger.info("Neo4j service not available")
        return []

    service = Neo4jChainSightService()
    if not service.is_available():
        return []

    # target → symbol
    symbol = _resolve_symbol(target)
    if not symbol:
        return []

    relations = service.get_related_stocks(symbol=symbol, limit=10)
    if not relations:
        return []

    keywords = []
    seen_texts = set()
    for rel in relations:
        rel_type = rel.get('relationship_type', '')
        related_name = rel.get('name', rel.get('symbol', ''))

        template_fn = CHAIN_TEMPLATES.get(rel_type)
        if template_fn and related_name:
            kw = template_fn(target, related_name)
            if kw.text not in seen_texts:
                keywords.append(kw)
                seen_texts.add(kw.text)

    return keywords[:5]


def _resolve_symbol(target: str) -> str | None:
    """종목명 → symbol 변환."""
    from packages.shared.stocks.models import Stock
    stock = Stock.objects.filter(symbol__iexact=target).first()
    if stock:
        return stock.symbol
    stock = Stock.objects.filter(name__icontains=target).first()
    if stock:
        return stock.symbol
    return None


def collect_chain_keywords(target: str):
    """Chain 키워드 추출 + KeywordCache 저장."""
    try:
        keywords = extract_chain_keywords(target)
        save_keywords(target, 'chain', keywords)
        log_event('keyword_extracted', {
            'source': 'chain',
            'target': target,
            'count': len(keywords),
        })
    except Exception as e:
        log_event('keyword_extraction_failed', {
            'source': 'chain',
            'target': target,
            'error': str(e),
        })
        logger.exception(f"Chain keyword extraction failed for {target}: {e}")
