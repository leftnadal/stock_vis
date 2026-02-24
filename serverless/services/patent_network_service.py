"""
Patent Network Service

USPTO API 기반 기업 간 특허 인용/분쟁 관계 빌더.

특허 인용: Company A의 특허가 Company B의 특허를 인용 → PATENT_CITED
특허 분쟁: 뉴스에서 특허 소송/분쟁 감지 → PATENT_DISPUTE

Usage:
    service = PatentNetworkService()
    result = service.build_patent_network(symbols=['AAPL', 'MSFT', 'GOOGL', 'QCOM'])
"""
import logging
import re
import time
from typing import List, Dict, Optional, Set
from datetime import timedelta
from itertools import combinations

from django.utils import timezone
from django.db import IntegrityError

from serverless.services.uspto_client import USPTOClient, USPTOError, COMPANY_ASSIGNEE_MAP
from serverless.models import StockRelationship
from news.models import NewsEntity

logger = logging.getLogger(__name__)


# 특허 분쟁 키워드
PATENT_DISPUTE_KEYWORDS = [
    'patent infringement', 'patent lawsuit', 'patent litigation',
    'patent dispute', 'patent troll', 'patent settlement',
    'ITC ruling', 'royalty payment', 'licensing agreement',
    'patent injunction', 'patent violation', 'intellectual property lawsuit',
]


class PatentNetworkService:
    """특허 인용/분쟁 네트워크 빌더"""

    # 분석 대상 주요 기업 (특허 활동이 활발한 기업)
    DEFAULT_SYMBOLS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
        'NVDA', 'AMD', 'INTC', 'QCOM', 'AVGO',
        'TSLA', 'IBM', 'ORCL', 'CRM', 'CSCO',
        'ADBE', 'TXN', 'MU', 'LRCX', 'AMAT',
        'KLAC', 'SNPS', 'CDNS', 'ARM', 'TSM',
    ]

    def __init__(self):
        self._uspto_client = None

    def _get_uspto_client(self):
        """Lazy load USPTO client"""
        if self._uspto_client is None:
            self._uspto_client = USPTOClient()
        return self._uspto_client

    def build_patent_network(self, symbols: List[str] = None) -> Dict:
        """전체 특허 네트워크 빌드

        1. For each symbol, get recent patents
        2. For each pair of symbols, find citation links
        3. Also scan news for patent disputes
        4. Create PATENT_CITED and PATENT_DISPUTE relationships

        Args:
            symbols: List of stock symbols to analyze. Defaults to DEFAULT_SYMBOLS.

        Returns:
            {
                'symbols_processed': int,
                'citation_links': int,
                'dispute_links': int,
                'total_relationships': int,
                'errors': int
            }
        """
        if symbols is None:
            symbols = self.DEFAULT_SYMBOLS

        # Ensure uppercase
        symbols = [s.upper() for s in symbols]

        logger.info(f"Starting patent network build for {len(symbols)} symbols")

        result = {
            'symbols_processed': 0,
            'citation_links': 0,
            'dispute_links': 0,
            'total_relationships': 0,
            'errors': 0
        }

        try:
            # Step 1: Get patents for each symbol
            client = self._get_uspto_client()
            patents_by_symbol = {}

            for symbol in symbols:
                try:
                    patents = client.get_patents_for_symbol(symbol, years=5)
                    if patents:
                        # Extract patent numbers
                        patent_numbers = [p.get('patent_number') for p in patents if p.get('patent_number')]
                        patents_by_symbol[symbol] = patent_numbers
                        logger.info(f"Found {len(patent_numbers)} patents for {symbol}")
                    else:
                        logger.warning(f"No patents found for {symbol}")

                    result['symbols_processed'] += 1

                    # Rate limiting: USPTO API typically allows ~10 req/sec
                    time.sleep(0.15)

                except USPTOError as e:
                    logger.error(f"USPTO error for {symbol}: {e}")
                    result['errors'] += 1
                except Exception as e:
                    logger.error(f"Unexpected error processing {symbol}: {e}")
                    result['errors'] += 1

            # Step 2: Find citation links between symbol pairs
            all_citation_links = []

            for source_symbol, target_symbol in combinations(symbols, 2):
                # Only check if both have patents
                if source_symbol not in patents_by_symbol or target_symbol not in patents_by_symbol:
                    continue

                try:
                    # Check both directions (A cites B, B cites A)
                    target_patents = {target_symbol: patents_by_symbol[target_symbol]}
                    links_forward = self.find_citation_links(source_symbol, target_patents)

                    target_patents_reverse = {source_symbol: patents_by_symbol[source_symbol]}
                    links_backward = self.find_citation_links(target_symbol, target_patents_reverse)

                    all_citation_links.extend(links_forward)
                    all_citation_links.extend(links_backward)

                    if links_forward or links_backward:
                        logger.info(f"Found {len(links_forward)} citations {source_symbol}→{target_symbol}, "
                                    f"{len(links_backward)} citations {target_symbol}→{source_symbol}")

                    # Rate limiting
                    time.sleep(0.2)

                except USPTOError as e:
                    logger.error(f"Citation search error {source_symbol}-{target_symbol}: {e}")
                    result['errors'] += 1
                except Exception as e:
                    logger.error(f"Unexpected error in citation search: {e}")
                    result['errors'] += 1

            # Step 3: Create citation relationships
            citation_count = self._create_citation_relationships(all_citation_links)
            result['citation_links'] = citation_count

            # Step 4: Scan news for patent disputes
            try:
                disputes = self.scan_patent_disputes(hours=168)  # 1 week
                dispute_count = self._create_dispute_relationships(disputes)
                result['dispute_links'] = dispute_count
            except Exception as e:
                logger.error(f"Patent dispute scan error: {e}")
                result['errors'] += 1

            result['total_relationships'] = result['citation_links'] + result['dispute_links']

            logger.info(f"Patent network build complete: {result}")

        except Exception as e:
            logger.error(f"Fatal error in build_patent_network: {e}", exc_info=True)
            result['errors'] += 1

        return result

    def find_citation_links(self, source_symbol: str, target_patents: Dict[str, List]) -> List[Dict]:
        """Find patent citations between source and target companies

        Args:
            source_symbol: Source company ticker
            target_patents: Dict of {symbol: [patent_numbers]}

        Returns:
            List of citation link dicts with keys:
                - source: str
                - target: str
                - source_patent: str
                - cited_patent: str
                - citation_count: int (optional)
        """
        client = self._get_uspto_client()

        try:
            links = client.find_citation_links(source_symbol, target_patents)
            return links
        except USPTOError as e:
            logger.error(f"Citation search failed for {source_symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in find_citation_links: {e}")
            return []

    def scan_patent_disputes(self, hours: int = 168) -> List[Dict]:
        """Scan news for patent disputes

        1. Query NewsEntity for patent-related keywords
        2. Extract involved companies/symbols
        3. Return list of disputes

        Args:
            hours: How far back to scan news (default 7 days)

        Returns:
            [{'source': str, 'target': str, 'headline': str, 'date': str, 'evidence': str}]
        """
        cutoff = timezone.now() - timedelta(hours=hours)
        disputes = []

        # Build Q object for keyword search
        from django.db.models import Q

        query = Q()
        for keyword in PATENT_DISPUTE_KEYWORDS:
            query |= Q(headline__icontains=keyword) | Q(content__icontains=keyword)

        try:
            news_articles = NewsEntity.objects.filter(
                query,
                published_at__gte=cutoff
            ).order_by('-published_at')[:200]  # Limit to prevent overload

            logger.info(f"Found {news_articles.count()} patent-related news articles")

            for article in news_articles:
                # Extract symbols from article
                symbols = self._extract_patent_dispute_symbols(article.headline, article.content or '')

                # Need at least 2 companies for a dispute
                if len(symbols) < 2:
                    continue

                # Create dispute entries for all symbol pairs
                for source, target in combinations(symbols, 2):
                    disputes.append({
                        'source': source,
                        'target': target,
                        'headline': article.headline,
                        'date': article.published_at.isoformat(),
                        'evidence': self._extract_dispute_evidence(article.headline, article.content or '')
                    })

            logger.info(f"Extracted {len(disputes)} patent dispute relationships")

        except Exception as e:
            logger.error(f"Error scanning patent disputes: {e}", exc_info=True)

        return disputes

    def _extract_patent_dispute_symbols(self, headline: str, content: str = '') -> List[str]:
        """Extract company symbols from patent dispute news

        Strategy:
        1. Look for company names in COMPANY_ASSIGNEE_MAP
        2. Extract symbols that match
        3. Return unique list
        """
        text = (headline + ' ' + content).upper()
        found_symbols = set()

        # Iterate through all known companies
        for symbol, company_names in COMPANY_ASSIGNEE_MAP.items():
            for company_name in company_names:
                # Normalize company name for matching
                normalized = company_name.upper()

                # Check for exact or partial match
                if normalized in text or symbol in text:
                    found_symbols.add(symbol)
                    break

        return list(found_symbols)

    def _extract_dispute_evidence(self, headline: str, content: str) -> str:
        """Extract key evidence/context from dispute article"""
        text = headline + ' ' + (content[:500] if content else '')

        # Find first matching keyword
        for keyword in PATENT_DISPUTE_KEYWORDS:
            if keyword.lower() in text.lower():
                # Extract sentence containing keyword
                sentences = re.split(r'[.!?]', text)
                for sentence in sentences:
                    if keyword.lower() in sentence.lower():
                        return sentence.strip()[:200]

        # Fallback to headline
        return headline[:200]

    def _create_citation_relationships(self, links: List[Dict]) -> int:
        """Create PATENT_CITED relationships from citation links

        Args:
            links: List of citation link dicts

        Returns:
            Number of relationships created
        """
        created = 0

        for link in links:
            try:
                # Extract data
                source = link.get('source', '').upper()
                target = link.get('target', '').upper()
                source_patent = link.get('source_patent', '')
                cited_patent = link.get('cited_patent', '')

                if not (source and target and source_patent and cited_patent):
                    logger.warning(f"Incomplete citation link: {link}")
                    continue

                # Create relationship
                obj, is_created = StockRelationship.objects.update_or_create(
                    source_symbol=source,
                    target_symbol=target,
                    relationship_type='PATENT_CITED',
                    defaults={
                        'source_provider': 'uspto',
                        'context': {
                            'source_patent': source_patent,
                            'cited_patent': cited_patent,
                            'citation_count': link.get('citation_count', 1),
                        },
                        'strength': 0.85,  # High confidence for USPTO data
                    }
                )

                if is_created:
                    created += 1
                    logger.debug(f"Created PATENT_CITED: {source} → {target} ({source_patent} → {cited_patent})")

            except IntegrityError as e:
                logger.warning(f"Duplicate citation relationship: {link}")
            except Exception as e:
                logger.error(f"Error creating citation relationship: {e}")

        logger.info(f"Created {created} PATENT_CITED relationships")
        return created

    def _create_dispute_relationships(self, disputes: List[Dict]) -> int:
        """Create PATENT_DISPUTE relationships from news disputes

        Args:
            disputes: List of dispute dicts

        Returns:
            Number of relationships created
        """
        created = 0

        for dispute in disputes:
            try:
                source = dispute.get('source', '').upper()
                target = dispute.get('target', '').upper()
                headline = dispute.get('headline', '')
                evidence = dispute.get('evidence', '')
                date_str = dispute.get('date', '')

                if not (source and target and headline):
                    logger.warning(f"Incomplete dispute data: {dispute}")
                    continue

                # Create bidirectional relationships (disputes affect both parties)
                for src, tgt in [(source, target), (target, source)]:
                    obj, is_created = StockRelationship.objects.update_or_create(
                        source_symbol=src,
                        target_symbol=tgt,
                        relationship_type='PATENT_DISPUTE',
                        defaults={
                            'source_provider': 'uspto',
                            'context': {
                                'headline': headline,
                                'evidence': evidence,
                                'date': date_str,
                            },
                            'strength': 0.70,  # Medium confidence (news-based)
                        }
                    )

                    if is_created:
                        created += 1
                        logger.debug(f"Created PATENT_DISPUTE: {src} ↔ {tgt}")

            except IntegrityError as e:
                logger.warning(f"Duplicate dispute relationship: {dispute}")
            except Exception as e:
                logger.error(f"Error creating dispute relationship: {e}")

        logger.info(f"Created {created} PATENT_DISPUTE relationships")
        return created
