"""
USPTO PatentsView API Client

USPTO PatentsView provides free, queryable API for US patent data.
No API key required.

Main use case for Stock-Vis:
- Find patents by company (assignee)
- Discover patent citation links between companies
- Identify patent disputes from litigation data

References:
- API Docs: https://patentsview.org/apis/api-endpoints
- No authentication required
- Rate limit: be reasonable (1 req/sec recommended)

Usage:
    client = USPTOClient()
    patents = client.get_patents_by_assignee('NVIDIA Corporation', years=5)
    citations = client.get_patent_citations('US11234567')
"""
import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class USPTOError(Exception):
    """USPTO API Error"""
    pass


class USPTOClient:
    BASE_URL = "https://api.patentsview.org/patents/query"
    RATE_LIMIT_INTERVAL = 1.0  # 1 second between requests

    # Company name to ticker mapping (for resolving assignees)
    COMPANY_ASSIGNEE_MAP = {
        'AAPL': ['Apple Inc.', 'Apple Computer'],
        'MSFT': ['Microsoft Corporation', 'Microsoft Technology Licensing'],
        'GOOGL': ['Google LLC', 'Google Inc.', 'Alphabet Inc.'],
        'AMZN': ['Amazon Technologies', 'Amazon.com'],
        'META': ['Meta Platforms', 'Facebook Inc.', 'Facebook Technologies'],
        'NVDA': ['NVIDIA Corporation'],
        'AMD': ['Advanced Micro Devices'],
        'INTC': ['Intel Corporation'],
        'QCOM': ['Qualcomm Incorporated', 'Qualcomm Technologies'],
        'TSLA': ['Tesla Inc.', 'Tesla Motors'],
        'IBM': ['International Business Machines'],
        'ORCL': ['Oracle Corporation', 'Oracle International'],
        'CRM': ['Salesforce Inc.', 'Salesforce.com'],
        'CSCO': ['Cisco Technology', 'Cisco Systems'],
        'ADBE': ['Adobe Inc.', 'Adobe Systems'],
        'AVGO': ['Broadcom Inc.', 'Broadcom Corporation'],
        'TXN': ['Texas Instruments'],
        'MU': ['Micron Technology'],
        'LRCX': ['Lam Research'],
        'AMAT': ['Applied Materials'],
        'KLAC': ['KLA Corporation'],
        'SNPS': ['Synopsys'],
        'CDNS': ['Cadence Design Systems'],
        'ARM': ['Arm Limited', 'ARM Holdings'],
        'TSM': ['Taiwan Semiconductor Manufacturing'],
        'SAMSUNG': ['Samsung Electronics'],
        'NOC': ['Northrop Grumman', 'Northrop Grumman Systems'],
        'LMT': ['Lockheed Martin'],
        'BA': ['The Boeing Company', 'Boeing Company'],
        'RTX': ['Raytheon Technologies', 'United Technologies'],
        'GD': ['General Dynamics'],
        'PFE': ['Pfizer Inc.'],
        'JNJ': ['Johnson & Johnson'],
        'ABBV': ['AbbVie Inc.'],
        'MRK': ['Merck & Co.', 'Merck Sharp & Dohme'],
        'LLY': ['Eli Lilly and Company'],
        'GILD': ['Gilead Sciences'],
        'AMGN': ['Amgen Inc.'],
        'BMY': ['Bristol-Myers Squibb'],
        'V': ['Visa Inc.', 'Visa International'],
        'MA': ['Mastercard Incorporated', 'Mastercard International'],
        'JPM': ['JPMorgan Chase', 'JP Morgan'],
        'BAC': ['Bank of America'],
        'GS': ['Goldman Sachs'],
        'MS': ['Morgan Stanley'],
        'C': ['Citigroup Inc.', 'Citibank'],
        'WFC': ['Wells Fargo'],
        'AXP': ['American Express'],
        'BLK': ['BlackRock Inc.'],
        'SCHW': ['Charles Schwab', 'The Charles Schwab Corporation'],
        'F': ['Ford Motor Company', 'Ford Global Technologies'],
        'GM': ['General Motors', 'GM Global Technology Operations'],
        'TM': ['Toyota Motor', 'Toyota Jidosha Kabushiki Kaisha'],
        'HMC': ['Honda Motor'],
        'RIVN': ['Rivian Automotive', 'Rivian IP Holdings'],
        'LCID': ['Lucid Motors', 'Atieva Inc.'],
        'NIO': ['NIO Inc.', 'NextEV'],
    }

    # Reverse map: assignee name -> ticker
    _assignee_to_symbol: Dict[str, str] = {}

    def __init__(self):
        self._last_request_time = 0
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
        })
        # Build reverse map
        for symbol, names in self.COMPANY_ASSIGNEE_MAP.items():
            for name in names:
                self._assignee_to_symbol[name.lower()] = symbol

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_INTERVAL:
            time.sleep(self.RATE_LIMIT_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _make_request(self, query: Dict, fields: List[str], options: Dict = None) -> Dict:
        """Make POST request to PatentsView API

        Args:
            query: Query criteria (e.g., {"assignee_organization": "Apple Inc."})
            fields: List of fields to return
            options: Optional pagination/sorting options

        Returns:
            API response dict

        Raises:
            USPTOError: If request fails
        """
        self._rate_limit()
        payload = {"q": query, "f": fields}
        if options:
            payload["o"] = options

        try:
            logger.debug(f"USPTO API request: {payload}")
            response = self._session.post(self.BASE_URL, json=payload, timeout=30)

            if response.status_code != 200:
                error_msg = f"USPTO API error {response.status_code}: {response.text[:200]}"
                logger.error(error_msg)
                raise USPTOError(error_msg)

            data = response.json()
            logger.debug(f"USPTO API response: {data.get('count', 0)} results")
            return data

        except requests.exceptions.Timeout:
            raise USPTOError("USPTO API request timed out")
        except requests.exceptions.RequestException as e:
            raise USPTOError(f"USPTO request failed: {e}")
        except ValueError as e:
            raise USPTOError(f"Invalid JSON response from USPTO API: {e}")

    def get_patents_by_assignee(
        self,
        company_name: str,
        years: int = 5,
        limit: int = 100
    ) -> List[Dict]:
        """Get patents for a company

        Args:
            company_name: Company/assignee name (e.g., "Apple Inc.")
            years: Look back N years from today
            limit: Max patents to return (default 100)

        Returns:
            List of patent dicts with:
                - patent_number: str
                - patent_title: str
                - patent_date: str (YYYY-MM-DD)
                - patent_abstract: str
                - assignees: List[Dict] with assignee_organization
        """
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=years * 365)

        query = {
            "_and": [
                {"assignee_organization": company_name},
                {"_gte": {"patent_date": start_date.isoformat()}},
                {"_lte": {"patent_date": end_date.isoformat()}}
            ]
        }

        fields = [
            "patent_number",
            "patent_title",
            "patent_date",
            "patent_abstract",
            "assignees"
        ]

        options = {
            "per_page": min(limit, 1000),  # API max is 10000, we use 1000
            "sort": [{"patent_date": "desc"}]
        }

        try:
            response = self._make_request(query, fields, options)
            patents = response.get("patents", [])

            logger.info(
                f"Retrieved {len(patents)} patents for '{company_name}' "
                f"from {start_date} to {end_date}"
            )

            return patents[:limit]  # Ensure we don't exceed limit

        except USPTOError as e:
            logger.error(f"Failed to get patents for '{company_name}': {e}")
            return []

    def get_patent_citations(self, patent_number: str) -> Dict:
        """Get citations for a specific patent

        Args:
            patent_number: Patent number (with or without "US" prefix)

        Returns:
            {
                'patent_number': str,
                'cited_patents': List[Dict],  # Patents this one cites (backward citations)
                'citing_patents': List[Dict]  # Patents that cite this one (forward citations)
            }
        """
        # Normalize patent number (remove "US" prefix if present)
        clean_number = patent_number.replace("US", "").replace("us", "").strip()

        # First get the patent with its cited patents
        query = {"patent_number": clean_number}
        fields = [
            "patent_number",
            "patent_title",
            "patent_date",
            "cited_patents"
        ]

        try:
            response = self._make_request(query, fields)
            patents = response.get("patents", [])

            if not patents:
                logger.warning(f"Patent {patent_number} not found")
                return {
                    "patent_number": patent_number,
                    "cited_patents": [],
                    "citing_patents": []
                }

            patent = patents[0]
            cited_patents = patent.get("cited_patents", [])

            # Now find patents that cite this one (forward citations)
            # This requires querying with cited_patent_number
            citing_query = {"cited_patent_number": clean_number}
            citing_fields = [
                "patent_number",
                "patent_title",
                "patent_date",
                "assignees"
            ]
            citing_options = {"per_page": 100}

            citing_response = self._make_request(citing_query, citing_fields, citing_options)
            citing_patents = citing_response.get("patents", [])

            logger.info(
                f"Patent {patent_number}: {len(cited_patents)} cited, "
                f"{len(citing_patents)} citing"
            )

            return {
                "patent_number": patent_number,
                "cited_patents": cited_patents,
                "citing_patents": citing_patents
            }

        except USPTOError as e:
            logger.error(f"Failed to get citations for patent {patent_number}: {e}")
            return {
                "patent_number": patent_number,
                "cited_patents": [],
                "citing_patents": []
            }

    def get_patents_for_symbol(
        self,
        symbol: str,
        years: int = 5,
        limit: int = 100
    ) -> List[Dict]:
        """Convenience: get patents by ticker symbol

        Args:
            symbol: Stock ticker (e.g., "AAPL")
            years: Look back N years
            limit: Max patents to return

        Returns:
            List of patent dicts
        """
        symbol = symbol.upper()
        assignee_names = self.COMPANY_ASSIGNEE_MAP.get(symbol)

        if not assignee_names:
            logger.warning(f"No assignee mapping found for symbol {symbol}")
            return []

        # Try primary assignee name first
        primary_name = assignee_names[0]
        patents = self.get_patents_by_assignee(primary_name, years, limit)

        # If no results and multiple names exist, try alternatives
        if not patents and len(assignee_names) > 1:
            for alt_name in assignee_names[1:]:
                patents = self.get_patents_by_assignee(alt_name, years, limit)
                if patents:
                    break

        return patents

    def find_citation_links(
        self,
        source_symbol: str,
        target_symbols: List[str]
    ) -> List[Dict]:
        """Find patent citation links between companies

        Check if source company's patents cite target companies' patents or vice versa.
        This discovers technology dependencies and innovation relationships.

        Args:
            source_symbol: Source company ticker (e.g., "NVDA")
            target_symbols: List of target company tickers (e.g., ["AMD", "INTC"])

        Returns:
            List of citation links:
            [{
                'source': str,  # Source ticker
                'target': str,  # Target ticker
                'citing_patent': str,  # Patent number that cites
                'cited_patent': str,  # Patent number being cited
                'direction': 'forward' | 'backward',  # forward: source cites target, backward: target cites source
                'citing_date': str,  # Date of citing patent
                'cited_date': str  # Date of cited patent
            }]
        """
        links = []

        # Get source company's patents (recent ones)
        source_patents = self.get_patents_for_symbol(source_symbol, years=3, limit=50)

        if not source_patents:
            logger.warning(f"No patents found for source symbol {source_symbol}")
            return links

        # Build target company patent numbers set
        target_patent_numbers = set()
        target_patent_map = {}  # patent_number -> symbol

        for target_symbol in target_symbols:
            target_patents = self.get_patents_for_symbol(target_symbol, years=5, limit=100)
            for patent in target_patents:
                patent_num = patent.get("patent_number")
                if patent_num:
                    target_patent_numbers.add(patent_num)
                    target_patent_map[patent_num] = target_symbol

        logger.info(
            f"Finding citation links: {source_symbol} ({len(source_patents)} patents) "
            f"vs {len(target_patent_numbers)} target patents"
        )

        # Check each source patent's citations
        for source_patent in source_patents:
            source_num = source_patent.get("patent_number")
            source_date = source_patent.get("patent_date")

            if not source_num:
                continue

            # Get citations for this patent
            citations = self.get_patent_citations(source_num)

            # Check backward citations (source cites target)
            for cited in citations.get("cited_patents", []):
                cited_num = cited.get("patent_number")
                if cited_num in target_patent_numbers:
                    links.append({
                        "source": source_symbol,
                        "target": target_patent_map[cited_num],
                        "citing_patent": source_num,
                        "cited_patent": cited_num,
                        "direction": "forward",
                        "citing_date": source_date,
                        "cited_date": cited.get("patent_date")
                    })

            # Check forward citations (target cites source)
            for citing in citations.get("citing_patents", []):
                citing_num = citing.get("patent_number")
                if citing_num in target_patent_numbers:
                    links.append({
                        "source": source_symbol,
                        "target": target_patent_map[citing_num],
                        "citing_patent": citing_num,
                        "cited_patent": source_num,
                        "direction": "backward",
                        "citing_date": citing.get("patent_date"),
                        "cited_date": source_date
                    })

        logger.info(f"Found {len(links)} citation links between {source_symbol} and targets")
        return links

    def _resolve_assignee_to_symbol(self, assignee_name: str) -> Optional[str]:
        """Resolve assignee organization name to ticker symbol

        Args:
            assignee_name: Organization name from patent data

        Returns:
            Ticker symbol or None if not found
        """
        if not assignee_name:
            return None

        assignee_lower = assignee_name.lower()

        # Exact match
        if assignee_lower in self._assignee_to_symbol:
            return self._assignee_to_symbol[assignee_lower]

        # Fuzzy match (check if any known assignee is substring)
        for known_name, symbol in self._assignee_to_symbol.items():
            if known_name in assignee_lower or assignee_lower in known_name:
                return symbol

        return None

    def get_assignee_names_for_symbol(self, symbol: str) -> List[str]:
        """Get all known assignee names for a ticker symbol

        Args:
            symbol: Stock ticker

        Returns:
            List of assignee organization names
        """
        return self.COMPANY_ASSIGNEE_MAP.get(symbol.upper(), [])
