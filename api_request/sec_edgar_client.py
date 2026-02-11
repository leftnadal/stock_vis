"""
SEC EDGAR API Client

SEC EDGAR (Electronic Data Gathering, Analysis, and Retrieval) provides:
- Free access to all public SEC filings
- Rate limit: 10 requests/second
- User-Agent header required
- No API key needed

Main use case for Stock-Vis:
- Download 10-K annual reports for supply chain analysis
- Extract customer/supplier relationships from Item 1A (Risk Factors)

References:
- API Docs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- 10-K Item 1A contains business risks including customer concentration disclosure
"""
import requests
import logging
import time
import re
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from bs4 import BeautifulSoup

from django.conf import settings


logger = logging.getLogger(__name__)


class SECEdgarError(Exception):
    """SEC EDGAR API Error"""
    pass


@dataclass
class Filing10K:
    """10-K Filing metadata"""
    accession_number: str
    filing_date: date
    report_date: date
    primary_document: str
    cik: str
    company_name: str
    form_type: str = "10-K"


class SECEdgarClient:
    """
    SEC EDGAR API Client

    Main use case: Download 10-K filings for supply chain analysis

    Usage:
        client = SECEdgarClient()

        # Get CIK for ticker
        cik = client.get_cik('AAPL')

        # Get recent 10-K filings
        filings = client.get_10k_filings(cik, limit=3)

        # Download 10-K text
        text = client.download_10k_text(filings[0])
    """

    BASE_URL = "https://data.sec.gov"
    WWW_URL = "https://www.sec.gov"  # For company_tickers.json
    SUBMISSIONS_URL = "https://data.sec.gov/submissions"
    FILINGS_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
    ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"

    # Rate limit: 10 requests/second
    RATE_LIMIT_INTERVAL = 0.1  # 100ms between requests

    # SEC requires a User-Agent header
    USER_AGENT = "Stock-Vis/1.0 (contact@stockvis.com)"

    def __init__(self):
        """Initialize SEC EDGAR client"""
        self._last_request_time = 0
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/json',
        })

        # CIK cache (ticker -> CIK)
        self._cik_cache: Dict[str, str] = {}

        logger.info("SEC EDGAR client initialized")

    def _rate_limit(self):
        """Enforce rate limit: 10 requests/second"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_INTERVAL:
            sleep_time = self.RATE_LIMIT_INTERVAL - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _make_request(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> requests.Response:
        """
        Make HTTP request with rate limiting

        Args:
            url: Request URL
            params: Query parameters
            headers: Additional headers
            timeout: Request timeout in seconds

        Returns:
            Response object

        Raises:
            SECEdgarError: On request failure
        """
        self._rate_limit()

        try:
            logger.debug(f"SEC EDGAR request: {url}")

            response = self._session.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout
            )

            if response.status_code == 404:
                raise SECEdgarError(f"Resource not found: {url}")
            elif response.status_code == 429:
                # Rate limited - wait and retry
                logger.warning("SEC EDGAR rate limited, waiting 1 second...")
                time.sleep(1)
                return self._make_request(url, params, headers, timeout)
            elif response.status_code >= 400:
                raise SECEdgarError(
                    f"SEC EDGAR error {response.status_code}: {response.text[:200]}"
                )

            return response

        except requests.exceptions.Timeout:
            logger.error(f"SEC EDGAR request timeout: {url}")
            raise SECEdgarError(f"Request timeout: {url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC EDGAR request failed: {e}")
            raise SECEdgarError(f"Request failed: {e}")

    def get_cik(self, ticker: str) -> Optional[str]:
        """
        Get CIK (Central Index Key) for a ticker symbol

        SEC uses CIK as the primary identifier for companies.
        CIK is a 10-digit number (zero-padded).

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            10-digit CIK string or None if not found

        Example:
            cik = client.get_cik('AAPL')  # Returns '0000320193'
        """
        ticker = ticker.upper()

        # Check cache
        if ticker in self._cik_cache:
            return self._cik_cache[ticker]

        try:
            # SEC provides a company tickers JSON file
            url = f"{self.WWW_URL}/files/company_tickers.json"
            response = self._make_request(url)
            data = response.json()

            # Search for ticker
            for key, company in data.items():
                if company.get('ticker', '').upper() == ticker:
                    cik = str(company.get('cik_str', '')).zfill(10)
                    self._cik_cache[ticker] = cik
                    logger.info(f"Found CIK for {ticker}: {cik}")
                    return cik

            logger.warning(f"CIK not found for ticker: {ticker}")
            return None

        except SECEdgarError:
            raise
        except Exception as e:
            logger.error(f"Error getting CIK for {ticker}: {e}")
            raise SECEdgarError(f"Failed to get CIK: {e}")

    def get_company_info(self, cik: str) -> Dict[str, Any]:
        """
        Get company information from SEC

        Args:
            cik: 10-digit CIK string

        Returns:
            Company info including name, tickers, exchanges, SIC code
        """
        cik = cik.zfill(10)

        try:
            url = f"{self.SUBMISSIONS_URL}/CIK{cik}.json"
            response = self._make_request(url)
            return response.json()

        except SECEdgarError:
            raise
        except Exception as e:
            logger.error(f"Error getting company info for CIK {cik}: {e}")
            raise SECEdgarError(f"Failed to get company info: {e}")

    def get_10k_filings(self, cik: str, limit: int = 3) -> List[Filing10K]:
        """
        Get list of 10-K filings for a company

        Args:
            cik: 10-digit CIK string
            limit: Maximum number of filings to return

        Returns:
            List of Filing10K objects (most recent first)
        """
        cik = cik.zfill(10)

        try:
            company_data = self.get_company_info(cik)

            company_name = company_data.get('name', 'Unknown')
            filings_data = company_data.get('filings', {}).get('recent', {})

            # Extract filing arrays
            forms = filings_data.get('form', [])
            accession_numbers = filings_data.get('accessionNumber', [])
            filing_dates = filings_data.get('filingDate', [])
            report_dates = filings_data.get('reportDate', [])
            primary_documents = filings_data.get('primaryDocument', [])

            filings = []

            for i, form in enumerate(forms):
                # Look for 10-K and 10-K/A (amended)
                if form in ('10-K', '10-K/A'):
                    try:
                        filing = Filing10K(
                            accession_number=accession_numbers[i].replace('-', ''),
                            filing_date=datetime.strptime(
                                filing_dates[i], '%Y-%m-%d'
                            ).date(),
                            report_date=datetime.strptime(
                                report_dates[i], '%Y-%m-%d'
                            ).date() if report_dates[i] else None,
                            primary_document=primary_documents[i],
                            cik=cik,
                            company_name=company_name,
                            form_type=form
                        )
                        filings.append(filing)

                        if len(filings) >= limit:
                            break

                    except (IndexError, ValueError) as e:
                        logger.warning(f"Error parsing filing {i}: {e}")
                        continue

            logger.info(f"Found {len(filings)} 10-K filings for CIK {cik}")
            return filings

        except SECEdgarError:
            raise
        except Exception as e:
            logger.error(f"Error getting 10-K filings for CIK {cik}: {e}")
            raise SECEdgarError(f"Failed to get 10-K filings: {e}")

    def download_10k_text(self, filing: Filing10K) -> str:
        """
        Download 10-K filing text content

        Args:
            filing: Filing10K object

        Returns:
            Plain text content of the 10-K filing

        Note:
            SEC 10-K files can be very large (10MB+).
            This method converts HTML to plain text.
        """
        try:
            # Construct filing URL
            # Format: /Archives/edgar/data/{cik}/{accession}/{document}
            url = (
                f"{self.ARCHIVES_URL}/{filing.cik}/"
                f"{filing.accession_number}/{filing.primary_document}"
            )

            logger.info(f"Downloading 10-K: {url}")

            response = self._make_request(url, timeout=120)

            # Convert HTML to text
            if filing.primary_document.endswith('.htm') or \
               filing.primary_document.endswith('.html'):
                text = self._html_to_text(response.text)
            else:
                text = response.text

            logger.info(
                f"Downloaded 10-K for {filing.company_name}: "
                f"{len(text)} characters"
            )

            return text

        except SECEdgarError:
            raise
        except Exception as e:
            logger.error(f"Error downloading 10-K: {e}")
            raise SECEdgarError(f"Failed to download 10-K: {e}")

    def _html_to_text(self, html: str) -> str:
        """
        Convert HTML to plain text

        Args:
            html: HTML content

        Returns:
            Plain text with preserved structure
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style', 'meta', 'link']):
                element.decompose()

            # Get text
            text = soup.get_text(separator='\n', strip=True)

            # Clean up multiple newlines
            text = re.sub(r'\n{3,}', '\n\n', text)

            # Clean up multiple spaces
            text = re.sub(r' {2,}', ' ', text)

            return text

        except Exception as e:
            logger.warning(f"HTML parsing failed, returning raw text: {e}")
            # Fallback: strip HTML tags with regex
            text = re.sub(r'<[^>]+>', '', html)
            return text

    def get_10k_for_symbol(self, symbol: str, limit: int = 1) -> List[Filing10K]:
        """
        Convenience method: Get 10-K filings for a ticker symbol

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of filings

        Returns:
            List of Filing10K objects
        """
        cik = self.get_cik(symbol)
        if not cik:
            return []

        return self.get_10k_filings(cik, limit=limit)

    def download_latest_10k(self, symbol: str) -> Optional[str]:
        """
        Convenience method: Download latest 10-K for a ticker

        Args:
            symbol: Stock ticker symbol

        Returns:
            10-K text content or None if not found
        """
        filings = self.get_10k_for_symbol(symbol, limit=1)
        if not filings:
            logger.warning(f"No 10-K found for {symbol}")
            return None

        return self.download_10k_text(filings[0])

    def extract_item_1a(self, text: str) -> str:
        """
        Extract Item 1A (Risk Factors) section from 10-K text

        Item 1A typically contains:
        - Customer concentration risks (major customers disclosed)
        - Supplier dependency risks (key suppliers disclosed)
        - Competitive landscape

        Args:
            text: Full 10-K text

        Returns:
            Item 1A section text
        """
        # Item 1A patterns - SEC filings vary in format
        # More flexible patterns to handle various 10-K formats
        patterns = [
            # Pattern 1: "Item 1A. Risk Factors" ... "Item 1B"
            r'Item\s*1A\.?\s+Risk\s*Factors(.*?)(?=Item\s*1B)',
            # Pattern 2: "Item 1A. Risk Factors" ... "Item 1C"
            r'Item\s*1A\.?\s+Risk\s*Factors(.*?)(?=Item\s*1C)',
            # Pattern 3: "Item 1A. Risk Factors" ... "Item 2"
            r'Item\s*1A\.?\s+Risk\s*Factors(.*?)(?=Item\s*2)',
            # Pattern 4: "RISK FACTORS" section
            r'(?:^|\n)\s*RISK\s*FACTORS\s*\n(.*?)(?=\n\s*(?:ITEM|UNRESOLVED|PROPERTIES))',
            # Pattern 5: Just "Risk Factors" heading
            r'Risk\s*Factors\s*\n(.*?)(?=Unresolved\s*Staff|Cybersecurity|Properties)',
        ]

        for i, pattern in enumerate(patterns):
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                item_1a = match.group(1).strip()
                if len(item_1a) > 1000:  # Ensure we got meaningful content
                    logger.info(f"Extracted Item 1A using pattern {i+1}: {len(item_1a)} characters")
                    return item_1a

        # Fallback: return first 100,000 characters (likely contains Item 1A)
        logger.warning("Could not locate Item 1A section, using first 100k chars")
        return text[:100000]

    def search_for_customer_info(self, text: str) -> str:
        """
        Search for customer concentration disclosure sections

        Many 10-Ks have specific sections like:
        - "Concentration of Credit Risk"
        - "Major Customers"
        - "Customer Concentration"

        Args:
            text: Full 10-K or Item 1A text

        Returns:
            Relevant section text
        """
        patterns = [
            r'(?:customer\s*concentration|concentration\s*of\s*credit\s*risk|major\s*customer|significant\s*customer)',
        ]

        sections = []

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Extract surrounding context (2000 chars before and after)
                start = max(0, match.start() - 500)
                end = min(len(text), match.end() + 2000)
                section = text[start:end]
                sections.append(section)

        return '\n\n---\n\n'.join(sections) if sections else text[:50000]
