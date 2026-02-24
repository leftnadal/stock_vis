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


@dataclass
class Filing13F:
    """13-F Filing metadata"""
    accession_number: str
    filing_date: date
    report_date: date
    info_table_document: str
    cik: str
    institution_name: str
    form_type: str = "13-F"


@dataclass
class Filing8K:
    """8-K Filing metadata"""
    accession_number: str
    filing_date: date
    items_reported: List[str]
    cik: str
    company_name: str
    form_type: str = "8-K"


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

    def get_13f_filings(self, cik: str, limit: int = 4) -> List[Filing13F]:
        """
        Get list of 13-F filings for an institution

        Similar to get_10k_filings but for 13-F form type.
        """
        cik = cik.zfill(10)
        try:
            company_data = self.get_company_info(cik)
            institution_name = company_data.get('name', 'Unknown')
            filings_data = company_data.get('filings', {}).get('recent', {})

            forms = filings_data.get('form', [])
            accession_numbers = filings_data.get('accessionNumber', [])
            filing_dates_raw = filings_data.get('filingDate', [])
            report_dates_raw = filings_data.get('reportDate', [])
            primary_documents = filings_data.get('primaryDocument', [])

            filings = []
            for i, form in enumerate(forms):
                if form in ('13-F', '13-F-HR', '13-F-HR/A'):
                    try:
                        # 13F info table is typically in a separate XML document
                        # The primary document is the cover page, we need the info table
                        filing = Filing13F(
                            accession_number=accession_numbers[i].replace('-', ''),
                            filing_date=datetime.strptime(filing_dates_raw[i], '%Y-%m-%d').date(),
                            report_date=datetime.strptime(report_dates_raw[i], '%Y-%m-%d').date() if report_dates_raw[i] else None,
                            info_table_document=primary_documents[i],
                            cik=cik,
                            institution_name=institution_name
                        )
                        filings.append(filing)
                        if len(filings) >= limit:
                            break
                    except (IndexError, ValueError) as e:
                        logger.warning(f"Error parsing 13F filing {i}: {e}")
                        continue

            logger.info(f"Found {len(filings)} 13-F filings for CIK {cik}")
            return filings
        except SECEdgarError:
            raise
        except Exception as e:
            logger.error(f"Error getting 13-F filings for CIK {cik}: {e}")
            raise SECEdgarError(f"Failed to get 13-F filings: {e}")

    def download_13f_holdings(self, filing: Filing13F) -> List[Dict]:
        """
        Download and parse 13-F holdings from info table

        Returns list of holdings: [{'cusip': str, 'name': str, 'shares': int, 'value': int, ...}]
        """
        try:
            # Get the filing index page to find the info table XML
            acc_formatted = f"{filing.accession_number[:10]}-{filing.accession_number[10:12]}-{filing.accession_number[12:]}"
            index_url = f"{self.ARCHIVES_URL}/{filing.cik}/{filing.accession_number}/"

            response = self._make_request(index_url)

            # Find the info table document (usually ends with .xml and contains 'infotable' or 'information')
            info_table_url = None

            # Try to find XML info table from the index page
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a'):
                href = link.get('href', '').lower()
                if ('infotable' in href or 'information' in href or 'holdings' in href) and href.endswith('.xml'):
                    info_table_url = f"{self.ARCHIVES_URL}/{filing.cik}/{filing.accession_number}/{link.get('href')}"
                    break

            if not info_table_url:
                # Fallback: try the primary document
                info_table_url = f"{self.ARCHIVES_URL}/{filing.cik}/{filing.accession_number}/{filing.info_table_document}"

            logger.info(f"Downloading 13F info table: {info_table_url}")
            response = self._make_request(info_table_url, timeout=60)

            return self._parse_13f_xml(response.text)

        except SECEdgarError:
            raise
        except Exception as e:
            logger.error(f"Error downloading 13F holdings: {e}")
            raise SECEdgarError(f"Failed to download 13F holdings: {e}")

    def _parse_13f_xml(self, xml_content: str) -> List[Dict]:
        """Parse 13-F info table XML"""
        try:
            soup = BeautifulSoup(xml_content, 'html.parser')
            holdings = []

            # 13F XML uses <infoTable> elements
            for entry in soup.find_all(['infotable', 'ns1:infotable', 'informationtable']):
                try:
                    # Extract fields - handle various XML formats
                    cusip = self._get_xml_text(entry, ['cusip', 'ns1:cusip'])
                    name = self._get_xml_text(entry, ['nameofissuer', 'ns1:nameofissuer', 'issuer'])
                    value = self._get_xml_text(entry, ['value', 'ns1:value'])
                    shares_tag = entry.find(['shrsorprnamt', 'ns1:shrsorprnamt', 'sharesOrPrincipalAmount'])
                    shares = '0'
                    if shares_tag:
                        shares = self._get_xml_text(shares_tag, ['sshprnamt', 'ns1:sshprnamt']) or '0'

                    if cusip:
                        holdings.append({
                            'cusip': cusip.strip(),
                            'name': (name or '').strip(),
                            'shares': int(re.sub(r'[^\d]', '', shares or '0') or '0'),
                            'value': int(re.sub(r'[^\d]', '', value or '0') or '0'),
                        })
                except Exception as e:
                    logger.debug(f"Error parsing 13F entry: {e}")
                    continue

            logger.info(f"Parsed {len(holdings)} holdings from 13F")
            return holdings

        except Exception as e:
            logger.error(f"Error parsing 13F XML: {e}")
            return []

    def _get_xml_text(self, element, tag_names: List[str]) -> Optional[str]:
        """Get text from XML element, trying multiple tag names"""
        for tag in tag_names:
            found = element.find(tag)
            if found and found.string:
                return found.string.strip()
        return None

    def get_8k_filings(self, cik: str, limit: int = 5) -> List[Filing8K]:
        """
        Get list of 8-K filings for a company
        """
        cik = cik.zfill(10)
        try:
            company_data = self.get_company_info(cik)
            company_name = company_data.get('name', 'Unknown')
            filings_data = company_data.get('filings', {}).get('recent', {})

            forms = filings_data.get('form', [])
            accession_numbers = filings_data.get('accessionNumber', [])
            filing_dates_raw = filings_data.get('filingDate', [])
            items_raw = filings_data.get('items', [])

            filings = []
            for i, form in enumerate(forms):
                if form in ('8-K', '8-K/A'):
                    try:
                        items = []
                        if i < len(items_raw) and items_raw[i]:
                            items = [item.strip() for item in items_raw[i].split(',') if item.strip()]

                        filing = Filing8K(
                            accession_number=accession_numbers[i].replace('-', ''),
                            filing_date=datetime.strptime(filing_dates_raw[i], '%Y-%m-%d').date(),
                            items_reported=items,
                            cik=cik,
                            company_name=company_name
                        )
                        filings.append(filing)
                        if len(filings) >= limit:
                            break
                    except (IndexError, ValueError) as e:
                        logger.warning(f"Error parsing 8-K filing {i}: {e}")
                        continue

            logger.info(f"Found {len(filings)} 8-K filings for CIK {cik}")
            return filings
        except SECEdgarError:
            raise
        except Exception as e:
            logger.error(f"Error getting 8-K filings: {e}")
            raise SECEdgarError(f"Failed to get 8-K filings: {e}")

    def download_8k_text(self, filing: Filing8K) -> str:
        """Download 8-K filing text content"""
        try:
            # Similar pattern to download_10k_text
            url = f"{self.ARCHIVES_URL}/{filing.cik}/{filing.accession_number}/"

            response = self._make_request(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find primary document (usually .htm)
            doc_url = None
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if href.endswith(('.htm', '.html')) and 'R' not in href:
                    doc_url = f"{self.ARCHIVES_URL}/{filing.cik}/{filing.accession_number}/{href}"
                    break

            if not doc_url:
                raise SECEdgarError(f"Could not find 8-K document for {filing.accession_number}")

            response = self._make_request(doc_url, timeout=60)
            return self._html_to_text(response.text)

        except SECEdgarError:
            raise
        except Exception as e:
            logger.error(f"Error downloading 8-K: {e}")
            raise SECEdgarError(f"Failed to download 8-K: {e}")
