"""
CSV URL 자동 복구 서비스

ETF CSV URL이 404를 반환할 때 자동으로 최신 URL을 찾아 업데이트합니다.

전략:
1. 운용사 Holdings 페이지 HTML 가져오기
2. 패턴 매칭 (Regex) - 비용 $0, 빠름
3. LLM 분석 (Gemini Flash) - 패턴 매칭 실패 시 폴백
4. URL 검증 및 업데이트
"""
import logging
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from django.conf import settings
from django.utils import timezone

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from serverless.models import ETFProfile


logger = logging.getLogger(__name__)


# 운용사별 Holdings 페이지 및 CSV 패턴 설정
FUND_MANAGER_CONFIG = {
    'spdr': {
        'name': 'State Street SPDR',
        'base_url': 'https://www.ssga.com',
        'holdings_page_template': 'https://www.ssga.com/us/en/intermediary/etfs/funds/{symbol}',
        'csv_patterns': [
            # XLSX 패턴 (최신)
            r'href=["\']([^"\']*holdings[^"\']*\.xlsx)["\']',
            r'href=["\']([^"\']*{symbol}[^"\']*holdings[^"\']*\.xlsx)["\']',
            # CSV 패턴
            r'href=["\']([^"\']*holdings[^"\']*\.csv)["\']',
            r'href=["\']([^"\']*{symbol}[^"\']*holdings[^"\']*\.csv)["\']',
            # 다운로드 링크 패턴
            r'data-download-url=["\']([^"\']*holdings[^"\']*)["\']',
        ],
        'content_type_check': ['text/csv', 'application/csv', 'application/vnd.openxmlformats'],
    },
    'ishares': {
        'name': 'iShares (BlackRock)',
        'base_url': 'https://www.ishares.com',
        'holdings_page_template': 'https://www.ishares.com/us/products/{product_id}',
        'product_id_map': {
            'SOXX': '239705',
            'ICLN': '239738',
            'IWM': '239710',
            'IVV': '239726',
        },
        'csv_patterns': [
            # Ajax CSV 다운로드 패턴
            r'([^"\']*\.ajax\?fileType=csv[^"\']*)',
            r'href=["\']([^"\']*fileType=csv[^"\']*)["\']',
            # 직접 CSV 링크
            r'href=["\']([^"\']*holdings\.csv[^"\']*)["\']',
            r'href=["\']([^"\']*_holdings[^"\']*\.csv)["\']',
        ],
        'content_type_check': ['text/csv', 'application/csv', 'text/plain'],
    },
    'ark': {
        'name': 'ARK Invest',
        'base_url': 'https://ark-funds.com',
        'holdings_page_template': 'https://ark-funds.com/funds/{fund_code}/',
        'fund_code_map': {
            'ARKK': 'arkk',
            'ARKG': 'arkg',
            'ARKW': 'arkw',
            'ARKF': 'arkf',
            'ARKQ': 'arkq',
        },
        'csv_patterns': [
            # ARK CSV 패턴
            r'href=["\']([^"\']*ARK[^"\']*HOLDINGS\.csv)["\']',
            r'href=["\']([^"\']*funds-etf-csv[^"\']*\.csv)["\']',
            r'href=["\']([^"\']*{symbol}[^"\']*\.csv)["\']',
            # 다운로드 버튼
            r'data-csv-url=["\']([^"\']+)["\']',
        ],
        'content_type_check': ['text/csv', 'application/csv'],
    },
    'globalx': {
        'name': 'Global X',
        'base_url': 'https://www.globalxetfs.com',
        'holdings_page_template': 'https://www.globalxetfs.com/funds/{symbol}/',
        'csv_patterns': [
            r'href=["\']([^"\']*holdings[^"\']*\.csv)["\']',
            r'href=["\']([^"\']*download[^"\']*holdings[^"\']*)["\']',
            r'data-holdings-url=["\']([^"\']+)["\']',
        ],
        'content_type_check': ['text/csv', 'application/csv'],
    },
    'invesco': {
        'name': 'Invesco',
        'base_url': 'https://www.invesco.com',
        'holdings_page_template': 'https://www.invesco.com/us/financial-products/etfs/holdings/main/holdings/0?audienceType=Investor&action=download&ticker={symbol}',
        'csv_patterns': [
            r'href=["\']([^"\']*holdings[^"\']*download[^"\']*)["\']',
            r'href=["\']([^"\']*action=download[^"\']*)["\']',
        ],
        'content_type_check': ['text/csv', 'application/csv'],
    },
}


class CSVURLResolverError(Exception):
    """CSV URL 복구 에러"""
    pass


class CSVURLResolver:
    """
    CSV URL 자동 복구 서비스

    404 에러 발생 시 운용사 웹사이트에서 최신 CSV URL을 찾아 업데이트합니다.

    Usage:
        resolver = CSVURLResolver()

        # 자동 복구 시도
        new_url = resolver.resolve_csv_url('XLK', 'spdr')

        # 복구 및 ETFProfile 업데이트
        success = resolver.resolve_and_update('XLK')
    """

    # LLM 설정
    LLM_MODEL = "gemini-2.5-flash"
    LLM_MAX_TOKENS = 1000
    LLM_TEMPERATURE = 0.1  # 정확한 URL 추출을 위해 낮은 temperature

    def __init__(self):
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

        # LLM 클라이언트 초기화 (선택적)
        self._llm_client = None
        if GENAI_AVAILABLE:
            api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None)
            if api_key:
                self._llm_client = genai.Client(api_key=api_key)

    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()

    def resolve_csv_url(
        self,
        etf_symbol: str,
        parser_type: str,
        current_url: Optional[str] = None
    ) -> Optional[str]:
        """
        ETF의 최신 CSV URL 찾기

        Args:
            etf_symbol: ETF 심볼 (예: XLK, SOXX)
            parser_type: 파서 타입 (spdr, ishares, ark, etc.)
            current_url: 현재 URL (참조용)

        Returns:
            새 CSV URL 또는 None
        """
        config = FUND_MANAGER_CONFIG.get(parser_type)
        if not config:
            logger.warning(f"{etf_symbol}: 지원하지 않는 파서 타입 - {parser_type}")
            return None

        # Holdings 페이지 URL 생성
        holdings_url = self._build_holdings_page_url(etf_symbol, parser_type, config)
        if not holdings_url:
            logger.warning(f"{etf_symbol}: Holdings 페이지 URL 생성 실패")
            return None

        logger.info(f"{etf_symbol}: Holdings 페이지 조회 - {holdings_url}")

        # HTML 가져오기
        html_content = self._fetch_html(holdings_url)
        if not html_content:
            logger.warning(f"{etf_symbol}: HTML 가져오기 실패")
            return None

        # 1단계: 패턴 매칭 시도
        csv_url = self._find_csv_url_by_pattern(
            html_content,
            etf_symbol,
            config
        )

        if csv_url:
            # URL 검증
            if self._validate_csv_url(csv_url, config):
                logger.info(f"{etf_symbol}: 패턴 매칭으로 URL 발견 - {csv_url}")
                return csv_url
            else:
                logger.warning(f"{etf_symbol}: 패턴 매칭 URL 검증 실패 - {csv_url}")

        # 2단계: LLM 분석 폴백
        if self._llm_client:
            csv_url = self._find_csv_url_by_llm(
                html_content,
                etf_symbol,
                parser_type,
                config
            )

            if csv_url:
                if self._validate_csv_url(csv_url, config):
                    logger.info(f"{etf_symbol}: LLM 분석으로 URL 발견 - {csv_url}")
                    return csv_url
                else:
                    logger.warning(f"{etf_symbol}: LLM 분석 URL 검증 실패 - {csv_url}")
        else:
            logger.info(f"{etf_symbol}: LLM 클라이언트 없음, 패턴 매칭만 시도")

        logger.warning(f"{etf_symbol}: CSV URL 복구 실패")
        return None

    def resolve_and_update(self, etf_symbol: str) -> Tuple[bool, Optional[str]]:
        """
        CSV URL 복구 및 ETFProfile 업데이트

        Args:
            etf_symbol: ETF 심볼

        Returns:
            (성공 여부, 새 URL 또는 에러 메시지)
        """
        try:
            profile = ETFProfile.objects.get(symbol=etf_symbol.upper())
        except ETFProfile.DoesNotExist:
            return False, f"ETF 프로필 없음: {etf_symbol}"

        new_url = self.resolve_csv_url(
            etf_symbol=profile.symbol,
            parser_type=profile.parser_type,
            current_url=profile.csv_url
        )

        if new_url:
            old_url = profile.csv_url
            profile.csv_url = new_url
            profile.last_error = f"URL 자동 복구됨 (이전: {old_url[:50]}...)"
            profile.save(update_fields=['csv_url', 'last_error'])

            logger.info(f"{etf_symbol}: CSV URL 업데이트 완료")
            return True, new_url

        return False, "URL 복구 실패"

    def _build_holdings_page_url(
        self,
        etf_symbol: str,
        parser_type: str,
        config: Dict
    ) -> Optional[str]:
        """운용사 Holdings 페이지 URL 생성"""
        template = config.get('holdings_page_template', '')

        if not template:
            return None

        # 심볼 변환
        symbol_lower = etf_symbol.lower()
        symbol_upper = etf_symbol.upper()

        # 특수 매핑 처리
        if parser_type == 'ishares':
            product_id = config.get('product_id_map', {}).get(symbol_upper)
            if product_id:
                return template.format(product_id=product_id)
            # product_id 없으면 일반 검색 페이지 사용
            return f"https://www.ishares.com/us/products/{symbol_upper}"

        elif parser_type == 'ark':
            fund_code = config.get('fund_code_map', {}).get(symbol_upper, symbol_lower)
            return template.format(fund_code=fund_code)

        # 일반 템플릿
        return template.format(
            symbol=symbol_upper,
            symbol_lower=symbol_lower
        )

    def _fetch_html(self, url: str) -> Optional[str]:
        """URL에서 HTML 가져오기"""
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as e:
            logger.warning(f"HTML 가져오기 실패 ({url}): {e}")
            return None

    def _find_csv_url_by_pattern(
        self,
        html: str,
        etf_symbol: str,
        config: Dict
    ) -> Optional[str]:
        """정규식 패턴으로 CSV URL 찾기"""
        base_url = config.get('base_url', '')
        patterns = config.get('csv_patterns', [])

        for pattern in patterns:
            # 심볼 치환
            pattern = pattern.replace('{symbol}', etf_symbol.upper())
            pattern = pattern.replace('{symbol_lower}', etf_symbol.lower())

            matches = re.findall(pattern, html, re.IGNORECASE)

            for match in matches:
                url = match

                # 상대 경로 처리
                if url.startswith('/'):
                    url = urljoin(base_url, url)
                elif not url.startswith('http'):
                    url = urljoin(base_url, '/' + url)

                # HTML 엔티티 디코딩
                url = url.replace('&amp;', '&')

                logger.debug(f"패턴 매칭 후보: {url}")
                return url

        return None

    def _find_csv_url_by_llm(
        self,
        html: str,
        etf_symbol: str,
        parser_type: str,
        config: Dict
    ) -> Optional[str]:
        """LLM으로 HTML 분석하여 CSV URL 찾기"""
        if not self._llm_client:
            return None

        # HTML 정리 (토큰 절약)
        cleaned_html = self._clean_html_for_llm(html)

        # 프롬프트 구성
        system_prompt = """당신은 웹페이지 HTML에서 CSV/XLSX 다운로드 링크를 찾는 전문가입니다.

규칙:
1. ETF Holdings 데이터를 다운로드할 수 있는 CSV 또는 XLSX 파일 링크를 찾으세요
2. href, data-url, data-download-url 등의 속성에서 URL을 찾으세요
3. 링크에 "holdings", "download", "csv", "xlsx" 등의 키워드가 포함된 것을 우선하세요
4. 정확히 하나의 URL만 반환하세요 (전체 URL, http로 시작)
5. URL을 찾을 수 없으면 "NOT_FOUND"만 반환하세요
6. 다른 설명 없이 URL만 반환하세요"""

        user_prompt = f"""다음 HTML에서 {etf_symbol} ETF의 Holdings CSV/XLSX 다운로드 링크를 찾아주세요.

운용사: {config.get('name', parser_type)}
기본 URL: {config.get('base_url', '')}

HTML (일부):
{cleaned_html[:8000]}

CSV/XLSX 다운로드 URL:"""

        try:
            response = self._llm_client.models.generate_content(
                model=self.LLM_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=self.LLM_MAX_TOKENS,
                    temperature=self.LLM_TEMPERATURE,
                )
            )

            result = response.text.strip()

            if result == "NOT_FOUND" or not result:
                return None

            # URL 추출 (응답에서 URL만 가져오기)
            url_match = re.search(r'https?://[^\s<>"\']+', result)
            if url_match:
                url = url_match.group(0)
                # HTML 엔티티 정리
                url = url.replace('&amp;', '&')
                return url

            return None

        except Exception as e:
            logger.warning(f"LLM 분석 실패: {e}")
            return None

    def _clean_html_for_llm(self, html: str) -> str:
        """LLM 분석을 위해 HTML 정리 (토큰 절약)"""
        # 스크립트, 스타일 제거
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # 주석 제거
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

        # 연속 공백 제거
        html = re.sub(r'\s+', ' ', html)

        # 다운로드/링크 관련 부분만 추출
        relevant_parts = []

        # a 태그 추출
        for match in re.finditer(r'<a[^>]*href[^>]*>.*?</a>', html, re.IGNORECASE | re.DOTALL):
            tag = match.group(0)
            if any(kw in tag.lower() for kw in ['csv', 'xlsx', 'download', 'holdings', 'export']):
                relevant_parts.append(tag)

        # data- 속성 추출
        for match in re.finditer(r'data-[^=]*=["\'][^"\']*(?:csv|xlsx|download|holdings)[^"\']*["\']', html, re.IGNORECASE):
            relevant_parts.append(match.group(0))

        if relevant_parts:
            return '\n'.join(relevant_parts)

        # 관련 부분 없으면 전체 HTML 반환 (truncated)
        return html

    def _validate_csv_url(self, url: str, config: Dict) -> bool:
        """CSV URL 유효성 검증"""
        try:
            # HEAD 요청으로 확인
            response = self.client.head(url, follow_redirects=True)

            # 상태 코드 확인
            if response.status_code != 200:
                logger.debug(f"URL 검증 실패 - 상태 코드: {response.status_code}")
                return False

            # Content-Type 확인 (선택적)
            content_type = response.headers.get('Content-Type', '')
            valid_types = config.get('content_type_check', [])

            if valid_types:
                if not any(vt in content_type.lower() for vt in valid_types):
                    # Content-Type이 다르더라도 파일 확장자가 맞으면 허용
                    if not any(url.lower().endswith(ext) for ext in ['.csv', '.xlsx', '.xls']):
                        logger.debug(f"URL 검증 실패 - Content-Type: {content_type}")
                        return False

            return True

        except Exception as e:
            logger.debug(f"URL 검증 실패 - 에러: {e}")
            return False

    def batch_resolve(self, etf_symbols: Optional[List[str]] = None) -> Dict[str, Dict]:
        """
        여러 ETF의 CSV URL 일괄 복구

        Args:
            etf_symbols: ETF 심볼 리스트 (None이면 404 에러 있는 모든 ETF)

        Returns:
            {
                'XLK': {'status': 'resolved', 'new_url': '...'},
                'SOXX': {'status': 'failed', 'error': '...'},
                ...
            }
        """
        if etf_symbols is None:
            # last_error에 다운로드 실패가 있는 ETF만
            profiles = ETFProfile.objects.filter(
                is_active=True,
                last_error__icontains='다운로드 실패'
            )
            etf_symbols = list(profiles.values_list('symbol', flat=True))

        results = {}
        for symbol in etf_symbols:
            success, result = self.resolve_and_update(symbol)
            results[symbol] = {
                'status': 'resolved' if success else 'failed',
                'new_url' if success else 'error': result
            }

        return results


# 싱글톤 인스턴스
_resolver_instance: Optional[CSVURLResolver] = None


def get_csv_url_resolver() -> CSVURLResolver:
    """CSVURLResolver 싱글톤 인스턴스 반환"""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = CSVURLResolver()
    return _resolver_instance
