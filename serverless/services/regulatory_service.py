"""
Regulatory Service - 규제 공유 관계 탐지

같은 규제 리스크를 공유하는 종목 그룹을 자동 발견합니다.
예: 반독점 (GOOGL, META, AMZN), FDA (바이오텍), 중국 제재 (NVDA, AMD)

Sources:
1. 뉴스 키워드 스캔
2. SEC 8-K 공시 분석 (Item 8.01 등)
3. Gemini LLM 그룹 추출

Usage:
    service = RegulatoryService()
    result = service.scan_regulatory_news(hours=168)
    # {"categories_found": 3, "relationships_created": 15, "groups": [...]}
"""
import logging
import re
import json
import time
from typing import List, Dict, Optional, Set, Tuple
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


# 규제 카테고리 정의
REGULATORY_CATEGORIES = {
    'antitrust': {
        'name': '반독점',
        'keywords': ['antitrust', 'monopoly', 'FTC', 'DOJ antitrust', 'anti-competitive',
                     'merger blocked', 'antitrust lawsuit', 'market dominance'],
    },
    'fda': {
        'name': 'FDA',
        'keywords': ['FDA approval', 'clinical trial', 'Phase III', 'FDA rejection',
                     'drug approval', 'NDA filing', 'FDA warning', 'biosimilar'],
    },
    'china_tariff': {
        'name': '중국 제재',
        'keywords': ['China tariff', 'export control', 'entity list', 'China ban',
                     'trade war', 'CHIPS Act', 'semiconductor export', 'Huawei'],
    },
    'data_privacy': {
        'name': '데이터 프라이버시',
        'keywords': ['GDPR', 'data breach', 'CCPA', 'privacy violation',
                     'data protection', 'privacy fine', 'consent decree'],
    },
    'financial_regulation': {
        'name': '금융 규제',
        'keywords': ['Basel', 'stress test', 'Dodd-Frank', 'SEC investigation',
                     'bank regulation', 'capital requirement', 'FDIC'],
    },
    'environmental': {
        'name': '환경 규제',
        'keywords': ['EPA', 'emissions', 'carbon tax', 'climate regulation',
                     'environmental fine', 'pollution', 'ESG mandate'],
    },
    'crypto_regulation': {
        'name': '암호화폐 규제',
        'keywords': ['SEC crypto', 'Bitcoin ETF', 'stablecoin regulation',
                     'crypto exchange', 'digital asset', 'CFTC'],
    },
    'ai_regulation': {
        'name': 'AI 규제',
        'keywords': ['AI regulation', 'AI safety', 'EU AI Act', 'AI governance',
                     'algorithmic bias', 'AI ethics', 'deepfake regulation'],
    },
}


class RegulatoryService:
    """규제 공유 관계 탐지 서비스"""

    def __init__(self):
        self._gemini_client = None

    def _get_gemini_client(self):
        """Lazy Gemini client initialization"""
        if self._gemini_client is None:
            try:
                from google import genai
                api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None)
                if api_key:
                    self._gemini_client = genai.Client(api_key=api_key)
                    logger.info("Gemini client initialized for regulatory service")
                else:
                    logger.warning("Gemini API key not found")
            except ImportError:
                logger.warning("google.genai not installed")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")

        return self._gemini_client

    def scan_regulatory_news(self, hours: int = 168) -> Dict:
        """
        뉴스에서 규제 키워드 스캔

        1. Query recent news from NewsEntity
        2. For each news, check headline+content against REGULATORY_CATEGORIES keywords
        3. If match found, extract affected symbols
        4. Group symbols by regulatory category
        5. Create SAME_REGULATION relationships for groups with >= 2 symbols

        Args:
            hours: 최근 N시간 내 뉴스 검색 (기본 7일)

        Returns:
            {
                "categories_found": 3,
                "relationships_created": 15,
                "groups": [
                    {
                        "category": "antitrust",
                        "category_name": "반독점",
                        "symbols": ["GOOGL", "META", "AMZN"],
                        "count": 3,
                        "evidence": ["headline 1", "headline 2"]
                    }
                ]
            }
        """
        try:
            from news.models import NewsArticle

            cutoff = timezone.now() - timedelta(hours=hours)
            articles = NewsArticle.objects.filter(
                published_at__gte=cutoff
            ).prefetch_related('entities').order_by('-published_at')

            logger.info(f"Scanning {articles.count()} news articles for regulatory keywords")

            # 카테고리별 종목 그룹
            category_groups: Dict[str, Set[str]] = {}
            category_evidence: Dict[str, List[str]] = {}

            for article in articles:
                text = f"{article.title} {article.summary or ''}"

                # 규제 카테고리 매칭
                matched_categories = self._match_news_to_categories(article.title, article.summary)

                if not matched_categories:
                    continue

                # 뉴스에서 종목 추출
                symbols = self._extract_symbols_from_news(article)

                if len(symbols) < 2:
                    # 단일 종목은 그룹 형성 불가
                    continue

                # 매칭된 카테고리별로 종목 추가
                for category in matched_categories:
                    if category not in category_groups:
                        category_groups[category] = set()
                        category_evidence[category] = []

                    category_groups[category].update(symbols)

                    # 증거 저장 (최대 3개)
                    if len(category_evidence[category]) < 3:
                        category_evidence[category].append(article.title[:200])

            # StockRelationship 생성
            total_relationships = 0
            groups = []

            for category, symbols in category_groups.items():
                if len(symbols) < 2:
                    continue

                symbols_list = sorted(list(symbols))
                evidence = category_evidence.get(category, [])

                # N개 종목 → N*(N-1)/2 관계 생성
                count = self.create_regulatory_relationships(
                    category=category,
                    symbols=symbols_list,
                    evidence='; '.join(evidence)
                )

                total_relationships += count

                groups.append({
                    'category': category,
                    'category_name': REGULATORY_CATEGORIES[category]['name'],
                    'symbols': symbols_list,
                    'count': len(symbols_list),
                    'evidence': evidence,
                })

                logger.info(
                    f"Regulatory group found: {category} with {len(symbols_list)} symbols"
                )

            result = {
                'categories_found': len(groups),
                'relationships_created': total_relationships,
                'groups': groups,
            }

            logger.info(f"Regulatory scan complete: {result}")
            return result

        except Exception as e:
            logger.error(f"Error scanning regulatory news: {e}", exc_info=True)
            return {
                'categories_found': 0,
                'relationships_created': 0,
                'groups': [],
                'error': str(e),
            }

    def scan_8k_filings(self, symbols: List[str] = None) -> List[Dict]:
        """
        8-K 공시에서 규제 정보 추출

        8-K Item 8.01 (Other Events)에 규제 관련 정보가 자주 등장합니다.

        Args:
            symbols: 검색할 종목 리스트 (None이면 스캔 안함)

        Returns:
            [
                {
                    "symbol": "NVDA",
                    "category": "china_tariff",
                    "evidence": "Export controls...",
                    "filing_date": "2024-01-15"
                }
            ]
        """
        if not symbols:
            logger.info("No symbols provided for 8-K scan")
            return []

        try:
            from api_request.sec_edgar_client import SECEdgarClient, SECEdgarError
        except ImportError:
            logger.warning("SEC EDGAR client not available")
            return []

        results = []
        client = SECEdgarClient()

        for symbol in symbols[:10]:  # Limit to 10 symbols to avoid rate limits
            try:
                # Get CIK
                cik = client.get_cik(symbol)
                if not cik:
                    continue

                # Get recent 8-K filings
                filings_data = self._get_8k_filings(client, cik, limit=3)

                for filing in filings_data:
                    # Download 8-K text
                    text = self._download_8k_text(client, filing)

                    if not text:
                        continue

                    # Scan for regulatory keywords
                    matched_categories = self._match_news_to_categories(text)

                    for category in matched_categories:
                        # Extract evidence (surrounding context)
                        evidence = self._extract_evidence(text, category)

                        results.append({
                            'symbol': symbol,
                            'category': category,
                            'evidence': evidence[:500],
                            'filing_date': filing.get('filing_date', ''),
                        })

                        logger.info(f"8-K regulatory match: {symbol} - {category}")

                # Rate limiting: 4 seconds between symbols
                time.sleep(4)

            except Exception as e:
                logger.warning(f"Error scanning 8-K for {symbol}: {e}")
                continue

        return results

    def _get_8k_filings(self, client, cik: str, limit: int = 3) -> List[Dict]:
        """Get recent 8-K filings metadata"""
        try:
            company_data = client.get_company_info(cik)
            filings_data = company_data.get('filings', {}).get('recent', {})

            forms = filings_data.get('form', [])
            accession_numbers = filings_data.get('accessionNumber', [])
            filing_dates = filings_data.get('filingDate', [])
            primary_documents = filings_data.get('primaryDocument', [])

            filings = []
            for i, form in enumerate(forms):
                if form in ('8-K', '8-K/A') and len(filings) < limit:
                    filings.append({
                        'accession_number': accession_numbers[i].replace('-', ''),
                        'filing_date': filing_dates[i],
                        'primary_document': primary_documents[i],
                        'cik': cik,
                    })

            return filings

        except Exception as e:
            logger.warning(f"Error getting 8-K filings for CIK {cik}: {e}")
            return []

    def _download_8k_text(self, client, filing: Dict) -> Optional[str]:
        """Download 8-K filing text"""
        try:
            url = (
                f"{client.ARCHIVES_URL}/{filing['cik']}/"
                f"{filing['accession_number']}/{filing['primary_document']}"
            )

            response = client._make_request(url, timeout=60)

            # Convert HTML to text
            if filing['primary_document'].endswith(('.htm', '.html')):
                text = client._html_to_text(response.text)
            else:
                text = response.text

            # Extract Item 8.01 if possible
            item_8_match = re.search(
                r'Item\s*8\.01\s*[:\.\-]?\s*(.{500,10000}?)(?=Item\s*9|SIGNATURES|$)',
                text,
                re.IGNORECASE | re.DOTALL
            )

            if item_8_match:
                return item_8_match.group(1)

            # Fallback: return first 10k characters
            return text[:10000]

        except Exception as e:
            logger.warning(f"Error downloading 8-K: {e}")
            return None

    def _extract_evidence(self, text: str, category: str) -> str:
        """Extract evidence text for a category match"""
        keywords = REGULATORY_CATEGORIES[category]['keywords']

        # Find first keyword match
        for keyword in keywords:
            match = re.search(
                re.escape(keyword),
                text,
                re.IGNORECASE
            )
            if match:
                # Extract 250 chars before and after
                start = max(0, match.start() - 250)
                end = min(len(text), match.end() + 250)
                return text[start:end].strip()

        return text[:500]

    def extract_regulatory_groups_llm(self, texts: List[Dict]) -> List[Dict]:
        """
        Gemini로 규제 그룹 추출

        When keyword matching is ambiguous, use LLM to classify.
        Uses sync API only (Bug #8).

        Args:
            texts: [{"text": "...", "symbol": "NVDA"}, ...]

        Returns:
            [
                {
                    "category": "china_tariff",
                    "symbols": ["NVDA", "AMD"],
                    "description": "China export controls"
                }
            ]
        """
        client = self._get_gemini_client()
        if not client:
            logger.warning("Gemini client not available for LLM extraction")
            return []

        # Build prompt
        text_snippets = "\n\n".join([
            f"Symbol: {item['symbol']}\nText: {item['text'][:500]}"
            for item in texts[:10]  # Limit to 10 for token budget
        ])

        prompt = f"""You are a financial analyst specializing in regulatory risk analysis.

Given the following news snippets and SEC filings, identify groups of stocks that share the same regulatory risk.

Regulatory categories:
- antitrust: Monopoly, FTC, DOJ, anti-competitive
- fda: Drug approval, clinical trials, FDA warnings
- china_tariff: Export controls, China ban, trade war
- data_privacy: GDPR, CCPA, data breach, privacy fines
- financial_regulation: Basel, stress test, SEC investigation
- environmental: EPA, emissions, carbon tax
- crypto_regulation: SEC crypto enforcement, stablecoin
- ai_regulation: AI safety, EU AI Act, algorithmic bias

Text snippets:
{text_snippets}

Return JSON array of regulatory groups:
[
  {{
    "category": "china_tariff",
    "symbols": ["NVDA", "AMD"],
    "description": "US-China semiconductor export controls"
  }}
]

Rules:
1. Only include groups with 2+ symbols
2. Only use categories from the list above
3. Be conservative - only group stocks with clear shared regulatory risk
4. Return empty array if no clear groups found
"""

        try:
            # Use sync API (Bug #8)
            response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt,
                config={
                    'temperature': 0.3,
                    'max_output_tokens': 2000,
                }
            )

            # Parse JSON response
            text = response.text.strip()

            # Extract JSON array
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in LLM response")
                return []

            groups = json.loads(json_match.group(0))

            logger.info(f"LLM extracted {len(groups)} regulatory groups")
            return groups

        except Exception as e:
            logger.error(f"Error in LLM extraction: {e}", exc_info=True)
            return []

        finally:
            # Rate limiting: 4 seconds between LLM calls
            time.sleep(4)

    def create_regulatory_relationships(
        self,
        category: str,
        symbols: List[str],
        evidence: str = ''
    ) -> int:
        """
        N개 종목 → N*(N-1)/2 SAME_REGULATION 관계 생성

        For each pair in symbols:
            StockRelationship.objects.update_or_create(
                source_symbol=s1,
                target_symbol=s2,
                relationship_type='SAME_REGULATION',
                defaults={
                    'strength': 0.7,
                    'source_provider': 'regulatory_llm',
                    'context': {
                        'category': category,
                        'category_name': REGULATORY_CATEGORIES[category]['name'],
                        'evidence': evidence
                    }
                }
            )

        Args:
            category: 규제 카테고리 ID
            symbols: 종목 심볼 리스트
            evidence: 증거 텍스트

        Returns:
            생성된 관계 수
        """
        try:
            from serverless.models import StockRelationship

            if category not in REGULATORY_CATEGORIES:
                logger.warning(f"Invalid category: {category}")
                return 0

            if len(symbols) < 2:
                return 0

            created_count = 0

            with transaction.atomic():
                # N*(N-1)/2 pairs
                for i in range(len(symbols)):
                    for j in range(i + 1, len(symbols)):
                        s1, s2 = sorted([symbols[i].upper(), symbols[j].upper()])

                        obj, created = StockRelationship.objects.update_or_create(
                            source_symbol=s1,
                            target_symbol=s2,
                            relationship_type='SAME_REGULATION',
                            defaults={
                                'strength': Decimal('0.70'),
                                'source_provider': 'regulatory_llm',
                                'context': {
                                    'category': category,
                                    'category_name': REGULATORY_CATEGORIES[category]['name'],
                                    'evidence': evidence[:500],
                                    'discovered_at': timezone.now().isoformat(),
                                }
                            }
                        )

                        if created:
                            created_count += 1
                            logger.debug(
                                f"SAME_REGULATION: {s1} <-> {s2} ({category})"
                            )

            logger.info(
                f"Created {created_count} SAME_REGULATION relationships for {category}"
            )
            return created_count

        except Exception as e:
            logger.error(f"Error creating regulatory relationships: {e}", exc_info=True)
            return 0

    def _match_news_to_categories(
        self,
        headline: str,
        content: str = ''
    ) -> List[str]:
        """
        뉴스 텍스트와 규제 카테고리 매칭

        Args:
            headline: 뉴스 제목
            content: 뉴스 본문 (선택)

        Returns:
            매칭된 카테고리 ID 리스트
        """
        text = f"{headline} {content}".lower()
        matched = []

        for category, config in REGULATORY_CATEGORIES.items():
            keywords = config['keywords']

            for keyword in keywords:
                if keyword.lower() in text:
                    matched.append(category)
                    break  # 한 번만 추가

        return matched

    def _extract_symbols_from_news(self, news) -> List[str]:
        """
        뉴스에서 종목 심볼 추출

        Args:
            news: NewsArticle 객체

        Returns:
            종목 심볼 리스트 (대문자)
        """
        symbols = []

        # NewsEntity에서 추출
        for entity in news.entities.filter(entity_type='equity'):
            symbols.append(entity.symbol.upper())

        return list(set(symbols))  # 중복 제거
