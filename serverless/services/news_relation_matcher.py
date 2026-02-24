"""
News Relation Matcher Service (Phase 6)

뉴스 제목/요약에서 관계 키워드 패턴 매칭으로 StockRelationship 자동 생성.
기존 Marketaux 뉴스(NewsArticle + NewsEntity) 활용, 추가 비용 $0.

주요 기능:
1. 뉴스 제목/요약에서 관계 키워드 패턴 매칭
2. 매칭된 회사명을 SymbolMatcher로 티커 변환
3. StockRelationship 생성 (source_provider='news')
4. CO_MENTIONED 관계의 context.mention_count 증가

Usage:
    from serverless.services.news_relation_matcher import NewsRelationMatcher

    matcher = NewsRelationMatcher()
    result = matcher.process_recent_news(hours=24)
    # {"processed": 50, "relations_created": 12, "co_mentions_updated": 8}
"""
import logging
import re
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

from django.db.models import F
from django.utils import timezone

from serverless.models import StockRelationship
from serverless.services.symbol_matcher import SymbolMatcher

logger = logging.getLogger(__name__)


# 관계 키워드 패턴 (영문 뉴스 기준)
# 각 패턴에서 named group 'source'와 'target'은 회사명/티커
RELATION_PATTERNS: Dict[str, List[re.Pattern]] = {
    'SUPPLIED_BY': [
        re.compile(
            r'(?P<target>[\w\s.&]+?)\s+(?:supplier|supplies|supplying)\s+(?:to\s+)?(?P<source>[\w\s.&]+)',
            re.IGNORECASE,
        ),
        re.compile(
            r'(?P<source>[\w\s.&]+?)\s+(?:relies on|depends on|sources from)\s+(?P<target>[\w\s.&]+)',
            re.IGNORECASE,
        ),
    ],
    'CUSTOMER_OF': [
        re.compile(
            r'(?P<source>[\w\s.&]+?)\s+(?:customer|client|buyer)\s+(?:of\s+)?(?P<target>[\w\s.&]+)',
            re.IGNORECASE,
        ),
        re.compile(
            r'(?P<target>[\w\s.&]+?)\s+(?:sells to|provides to)\s+(?P<source>[\w\s.&]+)',
            re.IGNORECASE,
        ),
    ],
    'PARTNER_OF': [
        re.compile(
            r'(?P<source>[\w\s.&]+?)\s+(?:partners? with|teamed up with|collaborat\w+ with)\s+(?P<target>[\w\s.&]+)',
            re.IGNORECASE,
        ),
        re.compile(
            r'(?P<source>[\w\s.&]+?)\s+and\s+(?P<target>[\w\s.&]+?)\s+(?:announce|form|sign)\s+(?:a\s+)?(?:partnership|collaboration|alliance|joint venture)',
            re.IGNORECASE,
        ),
    ],
    'ACQUIRED': [
        re.compile(
            r'(?P<source>[\w\s.&]+?)\s+(?:acquires?|bought|purchasing|to acquire|to buy)\s+(?P<target>[\w\s.&]+)',
            re.IGNORECASE,
        ),
        re.compile(
            r'(?P<target>[\w\s.&]+?)\s+(?:acquired by|bought by|sold to)\s+(?P<source>[\w\s.&]+)',
            re.IGNORECASE,
        ),
    ],
    'INVESTED_IN': [
        re.compile(
            r'(?P<source>[\w\s.&]+?)\s+(?:invests? in|backs|funds)\s+(?P<target>[\w\s.&]+)',
            re.IGNORECASE,
        ),
    ],
}

# 너무 짧거나 일반적인 단어는 회사명으로 취급하지 않음
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'has',
    'have', 'had', 'be', 'been', 'its', 'it', 'that', 'this', 'their',
    'stock', 'shares', 'market', 'company', 'inc', 'corp', 'ltd',
}


class NewsRelationMatcher:
    """뉴스 제목/요약에서 관계 키워드 패턴 매칭"""

    def __init__(self):
        self.symbol_matcher = SymbolMatcher()

    def process_recent_news(self, hours: int = 24) -> Dict:
        """
        최근 N시간 내 뉴스에서 관계 키워드 추출

        Args:
            hours: 최근 N시간

        Returns:
            {"processed": 50, "relations_created": 12, "co_mentions_updated": 8}
        """
        from news.models import NewsArticle

        cutoff = timezone.now() - timedelta(hours=hours)
        articles = NewsArticle.objects.filter(
            published_at__gte=cutoff
        ).prefetch_related('entities').order_by('-published_at')

        processed = 0
        relations_created = 0
        co_mentions_updated = 0

        for article in articles:
            text = f"{article.title} {article.summary or ''}"

            # 1. 패턴 매칭으로 관계 추출
            extracted = self._extract_relations(text)
            for rel_type, source_name, target_name in extracted:
                source_symbol = self._resolve_symbol(source_name)
                target_symbol = self._resolve_symbol(target_name)

                if source_symbol and target_symbol and source_symbol != target_symbol:
                    created = self._create_or_update_relationship(
                        source_symbol, target_symbol, rel_type, article.title
                    )
                    if created:
                        relations_created += 1

            # 2. NewsEntity 기반 CO_MENTIONED 자동 업데이트
            entity_symbols = list(
                article.entities.filter(
                    entity_type='equity'
                ).values_list('symbol', flat=True).distinct()
            )
            co_mentions_updated += self._update_co_mentions(entity_symbols, article.title)

            processed += 1

        result = {
            'processed': processed,
            'relations_created': relations_created,
            'co_mentions_updated': co_mentions_updated,
        }
        logger.info(f"뉴스 관계 매칭 완료: {result}")
        return result

    def _extract_relations(self, text: str) -> List[Tuple[str, str, str]]:
        """텍스트에서 관계 패턴 매칭"""
        results = []

        for rel_type, patterns in RELATION_PATTERNS.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    source_name = match.group('source').strip()
                    target_name = match.group('target').strip()

                    # 너무 짧거나 stop word만 있는 경우 스킵
                    if not self._is_valid_name(source_name) or not self._is_valid_name(target_name):
                        continue

                    results.append((rel_type, source_name, target_name))

        return results

    def _is_valid_name(self, name: str) -> bool:
        """유효한 회사명인지 확인"""
        if len(name) < 2:
            return False
        words = name.lower().split()
        meaningful_words = [w for w in words if w not in STOP_WORDS]
        return len(meaningful_words) >= 1

    def _resolve_symbol(self, name: str) -> Optional[str]:
        """회사명 -> 티커 심볼 변환"""
        name = name.strip().rstrip('.,;:')
        if not name:
            return None

        # 이미 티커 형태인 경우 (대문자 1-5자)
        if re.match(r'^[A-Z]{1,5}$', name):
            return name

        return self.symbol_matcher.match(name)

    def _create_or_update_relationship(
        self,
        source_symbol: str,
        target_symbol: str,
        relationship_type: str,
        headline: str,
    ) -> bool:
        """관계 생성 또는 업데이트. 생성되면 True 반환."""
        obj, created = StockRelationship.objects.update_or_create(
            source_symbol=source_symbol,
            target_symbol=target_symbol,
            relationship_type=relationship_type,
            defaults={
                'source_provider': 'news',
                'strength': 0.7,
                'context': {
                    'headline': headline[:200],
                    'extracted_at': timezone.now().isoformat(),
                },
            },
        )
        if created:
            logger.debug(
                f"뉴스 관계 생성: {source_symbol} --{relationship_type}--> {target_symbol}"
            )
        return created

    def _update_co_mentions(self, symbols: List[str], headline: str) -> int:
        """
        동일 뉴스에 등장한 종목 쌍의 CO_MENTIONED 관계 업데이트.
        mention_count 증가.
        """
        if len(symbols) < 2:
            return 0

        updated = 0
        # 모든 (A, B) 쌍에 대해 정렬 후 단방향만 처리
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                s1, s2 = sorted([symbols[i].upper(), symbols[j].upper()])

                obj, created = StockRelationship.objects.get_or_create(
                    source_symbol=s1,
                    target_symbol=s2,
                    relationship_type='CO_MENTIONED',
                    defaults={
                        'source_provider': 'news',
                        'strength': 0.5,
                        'context': {
                            'mention_count': 1,
                            'last_headline': headline[:200],
                        },
                    },
                )
                if not created:
                    # mention_count 증가
                    ctx = obj.context or {}
                    ctx['mention_count'] = ctx.get('mention_count', 0) + 1
                    ctx['last_headline'] = headline[:200]
                    obj.context = ctx
                    # strength도 소폭 증가 (최대 1.0)
                    new_strength = min(float(obj.strength) + 0.02, 1.0)
                    obj.strength = new_strength
                    obj.save(update_fields=['context', 'strength', 'last_verified_at'])

                updated += 1

        return updated
