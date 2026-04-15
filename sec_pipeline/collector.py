"""
SEC-PR-2: SEC EDGAR 수집기 + 섹션 추출

Step 1: SEC EDGAR submissions API → 10-K filing 메타데이터
Step 2: SEC EDGAR → HTML 원문 다운로드
Step 3: 섹션 추출 (regex 3단계) → fallback (edgartools)
Step 4: 사후 검증 → RawDocumentStore 저장

Note: FMP sec-filings 엔드포인트 Starter 플랜 미지원 → SEC EDGAR 직접 조회.
"""

import logging
import re
import time
import warnings
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from .validators import validate_extracted_sections

logger = logging.getLogger(__name__)

# SEC EDGAR User-Agent (필수)
SEC_HEADERS = {
    'User-Agent': 'Stock-Vis stockvis@example.com',
    'Accept-Encoding': 'gzip, deflate',
}

SEC_SUBMISSIONS_URL = 'https://data.sec.gov/submissions'
SEC_ARCHIVES_URL = 'https://www.sec.gov/Archives/edgar/data'
SEC_TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'


class SECFilingCollector:
    """SEC EDGAR 메타데이터 → HTML → 섹션 추출 통합 수집기."""

    # CIK 캐시 (클래스 레벨)
    _cik_cache: dict = {}

    # 섹션 헤딩 패턴 — 금융 변형 포함
    SECTION_PATTERNS = {
        'item_1': [
            r'(?:Item|ITEM)\s*1[\.\s:\-—]+',
            r'(?:Item|ITEM)\s*1\b(?!\d|A)',
            r'(?:Description\s+of\s+Business)',
            r'(?:General\s+Development\s+of\s+Business)',
            r'(?:Business\s+Overview)',
        ],
        'item_1a': [
            r'(?:Item|ITEM)\s*1A[\.\s:\-—]+',
            r'(?:Item|ITEM)\s*1A\b',
            r'(?:Risk\s+Factors)',
        ],
        'item_7': [
            r'(?:Item|ITEM)\s*7[\.\s:\-—]+',
            r'(?:Item|ITEM)\s*7\b(?!\d|A)',
            r"(?:Management['']?s?\s+Discussion\s+and\s+Analysis)",
            r'(?:MD\s*&\s*A)',
        ],
        'item_8': [
            r'(?:Item|ITEM)\s*8[\.\s:\-—]+',
            r'(?:Item|ITEM)\s*8\b',
            r'(?:Financial\s+Statements\s+and\s+Supplementary)',
        ],
    }

    def get_filing_metadata(self, symbol: str) -> Optional[dict]:
        """SEC EDGAR submissions API에서 최신 10-K filing 메타데이터 조회."""
        symbol = symbol.upper()

        # Step 1: Ticker → CIK 변환
        cik = self._get_cik(symbol)
        if not cik:
            logger.warning(f"CIK not found for {symbol}")
            return None

        # Step 2: submissions JSON에서 10-K 찾기
        time.sleep(0.12)  # SEC rate limit
        try:
            url = f"{SEC_SUBMISSIONS_URL}/CIK{cik}.json"
            resp = requests.get(url, headers=SEC_HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC submissions API error for {symbol}: {e}")
            raise

        filings_data = data.get('filings', {}).get('recent', {})
        forms = filings_data.get('form', [])
        accession_numbers = filings_data.get('accessionNumber', [])
        filing_dates = filings_data.get('filingDate', [])
        primary_documents = filings_data.get('primaryDocument', [])

        for i, form in enumerate(forms):
            if form in ('10-K', '10-K/A'):
                accession_no = accession_numbers[i]
                accession_clean = accession_no.replace('-', '')
                filing_date = filing_dates[i]
                primary_doc = primary_documents[i]

                final_link = (
                    f"{SEC_ARCHIVES_URL}/{cik.lstrip('0')}"
                    f"/{accession_clean}/{primary_doc}"
                )

                # fiscal year: filing date 기준
                fiscal_year = self._fiscal_year_from_date(filing_date)

                return {
                    'symbol': symbol,
                    'accession_no': accession_no,
                    'filing_date': filing_date,
                    'fiscal_year': fiscal_year,
                    'final_link': final_link,
                }

        logger.warning(f"No 10-K filing found for {symbol}")
        return None

    def _get_cik(self, symbol: str) -> Optional[str]:
        """Ticker → CIK (10자리 zero-padded)."""
        if symbol in self._cik_cache:
            return self._cik_cache[symbol]

        time.sleep(0.12)
        try:
            resp = requests.get(SEC_TICKERS_URL, headers=SEC_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for entry in data.values():
                if entry.get('ticker', '').upper() == symbol:
                    cik = str(entry['cik_str']).zfill(10)
                    self._cik_cache[symbol] = cik
                    return cik
        except Exception as e:
            logger.error(f"CIK lookup failed for {symbol}: {e}")
        return None

    def fetch_filing_html(self, final_link: str) -> Optional[str]:
        """SEC EDGAR에서 10-K HTML 원문 다운로드."""
        if not final_link:
            return None

        # SEC rate limit 준수 (10 req/sec → 0.12초 sleep)
        time.sleep(0.12)

        try:
            resp = requests.get(final_link, headers=SEC_HEADERS, timeout=60)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC EDGAR fetch error: {e}")
            raise

    def extract_sections(self, html: str) -> dict:
        """
        HTML에서 Item 1, 1A, 7 섹션 추출.

        3단계 전략:
        1. ToC(Table of Contents) 제거
        2. 각 섹션별 다중 후보 수집
        3. 가장 긴 후보 선택 (longest scoring)
        """
        # Step 1: HTML → plain text + ToC 제거
        text = self._html_to_text(html)
        text = self._remove_toc(text)

        sections = {}
        section_keys = ['item_1', 'item_1a', 'item_7']

        # Step 2: 각 섹션별 후보 수집
        for key in section_keys:
            candidates = self._find_section_candidates(text, key)
            if candidates:
                # Step 3: 가장 긴 후보 선택
                best = max(candidates, key=len)
                sections[key] = best.strip()
            else:
                sections[key] = ''

        return sections

    def extract_sections_fallback(self, symbol: str) -> Optional[dict]:
        """edgartools fallback (선택적 의존성)."""
        try:
            import edgartools as edgar

            company = edgar.Company(symbol)
            filing = company.get_filings(form='10-K').latest(1)
            if not filing:
                return None

            doc = filing.document
            sections = {}

            for key, item_no in [('item_1', '1'), ('item_1a', '1A'), ('item_7', '7')]:
                try:
                    section = doc[f'Item {item_no}']
                    sections[key] = str(section) if section else ''
                except (KeyError, AttributeError):
                    sections[key] = ''

            return sections
        except ImportError:
            logger.debug("edgartools not installed, fallback unavailable")
            return None
        except Exception as e:
            logger.warning(f"edgartools fallback failed for {symbol}: {e}")
            return None

    def collect(self, symbol: str) -> dict:
        """
        통합 수집 파이프라인.

        Returns:
            {
                'symbol': str,
                'accession_no': str,
                'filing_date': str,
                'fiscal_year': int,
                'final_link': str,
                'sections': {'item_1': str, 'item_1a': str, 'item_7': str},
                'status': 'success' | 'partial' | 'failed',
                'extraction_method': 'regex' | 'edgartools_fallback',
                'warnings': list[str],
            }
        """
        symbol = symbol.upper()

        # Step 1: SEC EDGAR 메타데이터
        metadata = self.get_filing_metadata(symbol)
        if not metadata:
            return self._fail_result(symbol, 'No filing metadata from SEC EDGAR')

        # Step 2: SEC HTML 다운로드
        html = self.fetch_filing_html(metadata['final_link'])
        if not html:
            return self._fail_result(symbol, 'Failed to fetch SEC HTML', metadata)

        # Step 3: 섹션 추출
        sections = self.extract_sections(html)
        extraction_method = 'regex'

        # Step 4: 사후 검증
        full_text = self._html_to_text(html)
        validated_sections, warnings = validate_extracted_sections(sections, full_text)

        # 검증 실패 (FAIL: prefix) → fallback 시도
        has_fail = any(w.startswith('FAIL:') for w in warnings)
        if has_fail:
            logger.info(f"{symbol}: validation failed, trying fallback")
            fallback_sections = self.extract_sections_fallback(symbol)
            if fallback_sections:
                # fallback 결과도 검증
                fb_validated, fb_warnings = validate_extracted_sections(
                    fallback_sections, full_text
                )
                fb_has_fail = any(w.startswith('FAIL:') for w in fb_warnings)
                if not fb_has_fail:
                    validated_sections = fb_validated
                    warnings = fb_warnings
                    extraction_method = 'edgartools_fallback'
                    logger.info(f"{symbol}: fallback succeeded")
                else:
                    logger.warning(f"{symbol}: fallback also failed validation")

        # 상태 결정
        non_empty = sum(1 for k in ['item_1', 'item_1a', 'item_7']
                        if validated_sections.get(k))
        if non_empty == 0:
            status = 'failed'
        elif non_empty < 3 or any(w.startswith('FAIL:') for w in warnings):
            status = 'partial'
        else:
            status = 'success'

        return {
            'symbol': symbol,
            'accession_no': metadata['accession_no'],
            'filing_date': metadata['filing_date'],
            'fiscal_year': metadata['fiscal_year'],
            'final_link': metadata['final_link'],
            'sections': validated_sections,
            'status': status,
            'extraction_method': extraction_method,
            'warnings': warnings,
        }

    # ── Private helpers ──

    def _html_to_text(self, html: str) -> str:
        """HTML → plain text 변환."""
        soup = BeautifulSoup(html, 'lxml')

        # script, style 태그 제거
        for tag in soup(['script', 'style']):
            tag.decompose()

        text = soup.get_text(separator='\n')
        # 연속 공백/빈줄 정리
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def _remove_toc(self, text: str) -> str:
        """Table of Contents 섹션 제거."""
        toc_patterns = [
            r'(?i)TABLE\s+OF\s+CONTENTS.*?(?=Item\s*1[\.\s])',
            r'(?i)INDEX.*?(?=Item\s*1[\.\s])',
        ]
        for pat in toc_patterns:
            text = re.sub(pat, '', text, flags=re.DOTALL, count=1)
        return text

    def _find_section_candidates(self, text: str, section_key: str) -> list:
        """섹션 헤딩 패턴으로 후보 텍스트 블록 수집."""
        patterns = self.SECTION_PATTERNS[section_key]

        # 다음 섹션 시작점을 종료 마커로 사용
        next_section_map = {
            'item_1': 'item_1a',
            'item_1a': 'item_7',
            'item_7': 'item_8',
        }
        next_key = next_section_map.get(section_key)
        end_patterns = self.SECTION_PATTERNS.get(next_key, []) if next_key else []

        candidates = []
        for pat in patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                start = match.start()  # heading 포함 (사후 검증용)
                # 종료 지점 찾기
                end = len(text)
                for end_pat in end_patterns:
                    end_match = re.search(end_pat, text[start:], re.IGNORECASE)
                    if end_match:
                        end = min(end, start + end_match.start())

                # 너무 짧은 후보 제외 (< 200자)
                candidate = text[start:end]
                if len(candidate) >= 200:
                    candidates.append(candidate)

        return candidates

    def _fiscal_year_from_date(self, filing_date: str) -> int:
        """filing_date(YYYY-MM-DD)에서 fiscal year 추출."""
        try:
            dt = datetime.strptime(filing_date, '%Y-%m-%d')
            # 10-K는 보통 전년도 실적 → 1~3월 filing이면 전년
            return dt.year - 1 if dt.month <= 3 else dt.year
        except (ValueError, TypeError):
            return 0

    def _fail_result(self, symbol: str, reason: str, metadata: dict = None) -> dict:
        """실패 결과 생성."""
        return {
            'symbol': symbol,
            'accession_no': metadata.get('accession_no', '') if metadata else '',
            'filing_date': metadata.get('filing_date', '') if metadata else '',
            'fiscal_year': metadata.get('fiscal_year', 0) if metadata else 0,
            'final_link': metadata.get('final_link', '') if metadata else '',
            'sections': {'item_1': '', 'item_1a': '', 'item_7': ''},
            'status': 'failed',
            'extraction_method': 'regex',
            'warnings': [f'FAIL: {reason}'],
        }
