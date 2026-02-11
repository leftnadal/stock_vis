"""
Supply Chain Parser - 10-K 텍스트에서 공급망 관계 추출

SEC 10-K 연차보고서의 Item 1A (Risk Factors) 섹션에서
고객/공급사 관계를 추출합니다.

주요 패턴:
1. 고객 집중도: "Apple accounted for 25% of our revenue"
2. 공급사 의존도: "We depend on TSMC for chip manufacturing"

Usage:
    parser = SupplyChainParser()
    relations = parser.parse_10k(text, 'TSM')

    for rel in relations:
        print(f"{rel.source_symbol} -> {rel.target_name} ({rel.relation_type})")
"""
import re
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from decimal import Decimal

from django.db.models import Q
from django.db.models.functions import Lower


logger = logging.getLogger(__name__)


@dataclass
class SupplyChainRelation:
    """공급망 관계 추출 결과"""
    source_symbol: str       # 분석 대상 종목 (10-K 발행사)
    target_name: str         # 추출된 회사명
    target_symbol: Optional[str]  # 매칭된 티커 (Stock DB 조회)
    relation_type: str       # 'customer' or 'supplier'
    confidence: str          # 'high', 'medium-high', 'medium'
    revenue_percent: Optional[float]  # 매출 비중 (있는 경우)
    evidence: str            # 원문 발췌

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'source_symbol': self.source_symbol,
            'target_name': self.target_name,
            'target_symbol': self.target_symbol,
            'relation_type': self.relation_type,
            'confidence': self.confidence,
            'revenue_percent': self.revenue_percent,
            'evidence': self.evidence,
        }


class SupplyChainParser:
    """
    10-K 텍스트에서 공급망 관계 추출

    신뢰도 기준:
    - high: 매출 비중 10% 이상 명시
    - medium-high: "major", "significant", "key" 수식어 사용
    - medium: 단순 언급
    """

    # 회사명 패턴 (최대 5단어, 반드시 suffix 포함하거나 알려진 회사)
    # 더 제한적인 패턴: 대문자로 시작하는 1-5 단어 + 회사 suffix
    COMPANY_NAME_PATTERN = r'([A-Z][A-Za-z]+(?:\s+[A-Z]?[a-z]+){0,4})\s*(?:,?\s*(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?|Co\.?|L\.?P\.?))?'

    # 더 정확한 회사명 패턴 (suffix 필수)
    COMPANY_WITH_SUFFIX = r'([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,4})\s*,?\s*(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?|Co\.?)'

    # 고객 집중도 패턴
    CUSTOMER_PATTERNS = [
        # "Apple Inc. accounted for 25% of our revenue" (suffix 필수)
        (
            r'([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,4})\s*,?\s*'
            r'(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?)\s+'
            r'(?:accounted for|represented|comprised)\s+'
            r'(?:approximately\s+)?(\d{1,2})%',
            'high'
        ),
        # "Our largest customer is Apple Inc." (suffix 필수)
        (
            r'(?:largest|significant|major|biggest|key|primary|principal)\s+'
            r'customer[s]?\s+(?:is|are|include[s]?|was|were)\s+'
            r'([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,4})\s*,?\s*'
            r'(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?)',
            'medium-high'
        ),
        # "sales to Apple Inc. represented" (suffix 필수)
        (
            r'sales\s+to\s+'
            r'([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,4})\s*,?\s*'
            r'(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?)\s+'
            r'(?:represented|accounted)',
            'medium-high'
        ),
        # "X% of revenue from Apple Inc." (suffix 필수)
        (
            r'(\d{1,2})%\s+(?:of\s+)?(?:our\s+)?(?:total\s+)?(?:net\s+)?revenue[s]?\s+'
            r'(?:from|came from|was from|were from)\s+'
            r'([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,4})\s*,?\s*'
            r'(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?)',
            'high'
        ),
        # "our customer, Apple Inc.," (suffix 필수)
        (
            r'(?:our|a)\s+(?:major|key|significant|largest)\s+customer,?\s+'
            r'([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,4})\s*,?\s*'
            r'(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?)',
            'medium-high'
        ),
    ]

    # 공급사 의존도 패턴
    SUPPLIER_PATTERNS = [
        # "We depend on TSMC for chip manufacturing" (suffix 선택)
        (
            r'(?:we|the company)\s+depend[s]?\s+(?:heavily\s+)?on\s+'
            r'([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,4})'
            r'(?:\s*,?\s*(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?))?\s+'
            r'(?:for|as|to)',
            'medium-high'
        ),
        # "sole supplier is TSMC" (suffix 선택)
        (
            r'(?:sole|single|primary|key|main|principal)\s+supplier[s]?\s+'
            r'(?:is|are|include[s]?)\s+'
            r'([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,4})'
            r'(?:\s*,?\s*(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?))?',
            'medium-high'
        ),
        # "raw materials from TSMC" (suffix 선택)
        (
            r'(?:raw materials|components|parts|supplies|chips|wafers)\s+'
            r'(?:from|provided by|supplied by|manufactured by)\s+'
            r'([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,4})'
            r'(?:\s*,?\s*(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?))?',
            'medium'
        ),
        # "manufactured by TSMC" (suffix 선택)
        (
            r'(?:products?|chips?|wafers?|components?)\s+'
            r'(?:are|is)\s+(?:manufactured|produced|fabricated|made)\s+'
            r'(?:by|at)\s+'
            r'([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,4})'
            r'(?:\s*,?\s*(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?))?',
            'medium-high'
        ),
        # "rely on TSMC" (suffix 선택)
        (
            r'(?:we|the company)\s+rely\s+(?:primarily\s+|heavily\s+)?on\s+'
            r'([A-Z][A-Za-z]+(?:\s+[A-Z]?[A-Za-z]+){0,4})'
            r'(?:\s*,?\s*(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?))?\s+'
            r'(?:for|to|as)',
            'medium-high'
        ),
    ]

    # 회사명 정규화 패턴
    COMPANY_SUFFIXES = [
        r'\s*,?\s*Inc\.?$',
        r'\s*,?\s*Corp\.?$',
        r'\s*,?\s*Corporation$',
        r'\s*,?\s*Company$',
        r'\s*,?\s*LLC$',
        r'\s*,?\s*Ltd\.?$',
        r'\s*,?\s*L\.?P\.?$',
        r'\s*,?\s*Co\.?$',
    ]

    # 제외 패턴 (일반 명사, 너무 짧은 이름, 일반적 문구)
    EXCLUDE_PATTERNS = [
        r'^(?:The|A|An)\s',
        r'^(?:Our|We|They|Their|Its|His|Her)\s',
        r'^(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\s',
        r'^(?:No|None|Not|Any|All|Some|Many|Most|Each|Every)\s',
        r'^(?:This|That|These|Those|Such)\s',
        r'^(?:First|Second|Third|Last|Next|Previous)\s',
        r'^.{1,3}$',  # 3자 이하
        r'^.{60,}$',  # 60자 이상 (너무 긴 이름)
        r'(?:net\s+)?(?:sales|revenue|income|profit|loss)',  # 재무 용어
        r'(?:fiscal|quarter|annual|year)',  # 기간 용어
        r'(?:countries|regions|customers|suppliers|products)',  # 일반 명사
        r'(?:distribution|channel|segment|division)',  # 비즈니스 용어
        r'(?:through|during|within|between|among)',  # 전치사구
        r'(?:direct|indirect|international|domestic)',  # 형용사
    ]

    # 유효한 회사 이름에 포함되면 안 되는 단어들
    INVALID_WORDS = {
        'net', 'sales', 'revenue', 'income', 'profit', 'loss', 'fiscal',
        'quarter', 'annual', 'year', 'countries', 'regions', 'customers',
        'suppliers', 'products', 'distribution', 'channel', 'segment',
        'division', 'through', 'during', 'within', 'between', 'among',
        'direct', 'indirect', 'international', 'domestic', 'total',
        'approximately', 'percent', 'percentage', 'primarily', 'mainly',
        'individually', 'collectively', 'respectively', 'however', 'therefore',
    }

    def __init__(self):
        """Initialize parser"""
        self._company_name_cache: Dict[str, Optional[str]] = {}

    def parse_10k(self, text: str, source_symbol: str) -> List[SupplyChainRelation]:
        """
        10-K 텍스트에서 공급망 관계 추출

        Args:
            text: 10-K 텍스트 (전체 또는 Item 1A)
            source_symbol: 분석 대상 종목 심볼 (10-K 발행사)

        Returns:
            추출된 관계 리스트
        """
        source_symbol = source_symbol.upper()
        relations: List[SupplyChainRelation] = []

        # 고객 추출
        customer_relations = self._extract_customers(text, source_symbol)
        relations.extend(customer_relations)

        # 공급사 추출
        supplier_relations = self._extract_suppliers(text, source_symbol)
        relations.extend(supplier_relations)

        # 중복 제거
        relations = self._deduplicate_relations(relations)

        logger.info(
            f"Parsed 10-K for {source_symbol}: "
            f"{len(customer_relations)} customers, {len(supplier_relations)} suppliers"
        )

        return relations

    def _extract_customers(
        self,
        text: str,
        source_symbol: str
    ) -> List[SupplyChainRelation]:
        """고객 관계 추출"""
        relations = []

        for pattern, base_confidence in self.CUSTOMER_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    groups = match.groups()

                    # 패턴에 따라 회사명/퍼센트 추출
                    if len(groups) == 2:
                        if groups[0].isdigit() or (groups[0] and groups[0][0].isdigit()):
                            # (percent, company_name) 형식
                            revenue_percent = float(groups[0])
                            company_name = groups[1]
                        else:
                            # (company_name, percent) 형식
                            company_name = groups[0]
                            revenue_percent = float(groups[1]) if groups[1] else None
                    else:
                        company_name = groups[0]
                        revenue_percent = None

                    # 회사명 정규화
                    company_name = self._normalize_company_name(company_name)

                    if not company_name or not self._is_valid_company_name(company_name):
                        continue

                    # 신뢰도 결정
                    confidence = base_confidence
                    if revenue_percent and revenue_percent >= 10:
                        confidence = 'high'

                    # 티커 매칭
                    target_symbol = self.match_to_stock(company_name)

                    # 자기 자신 제외
                    if target_symbol and target_symbol.upper() == source_symbol:
                        continue

                    # 증거 문장 추출
                    evidence = self._extract_evidence(text, match)

                    relation = SupplyChainRelation(
                        source_symbol=source_symbol,
                        target_name=company_name,
                        target_symbol=target_symbol,
                        relation_type='customer',
                        confidence=confidence,
                        revenue_percent=revenue_percent,
                        evidence=evidence
                    )
                    relations.append(relation)

                except Exception as e:
                    logger.warning(f"Error parsing customer match: {e}")
                    continue

        return relations

    def _extract_suppliers(
        self,
        text: str,
        source_symbol: str
    ) -> List[SupplyChainRelation]:
        """공급사 관계 추출"""
        relations = []

        for pattern, base_confidence in self.SUPPLIER_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    company_name = match.group(1)

                    # 회사명 정규화
                    company_name = self._normalize_company_name(company_name)

                    if not company_name or not self._is_valid_company_name(company_name):
                        continue

                    # 티커 매칭
                    target_symbol = self.match_to_stock(company_name)

                    # 자기 자신 제외
                    if target_symbol and target_symbol.upper() == source_symbol:
                        continue

                    # 증거 문장 추출
                    evidence = self._extract_evidence(text, match)

                    relation = SupplyChainRelation(
                        source_symbol=source_symbol,
                        target_name=company_name,
                        target_symbol=target_symbol,
                        relation_type='supplier',
                        confidence=base_confidence,
                        revenue_percent=None,
                        evidence=evidence
                    )
                    relations.append(relation)

                except Exception as e:
                    logger.warning(f"Error parsing supplier match: {e}")
                    continue

        return relations

    # 회사명에서 제거할 접두어 단어들
    PREFIX_WORDS_TO_REMOVE = {
        'ITEM', 'FACTORS', 'RISK', 'RISKS', 'CUSTOMER', 'CUSTOMERS',
        'CONCENTRATION', 'SUPPLIER', 'SUPPLIERS', 'SUPPLY', 'CHAIN',
        'BUSINESS', 'COMPANY', 'CORPORATE', 'MANAGEMENT', 'DISCUSSION',
        'FINANCIAL', 'STATEMENTS', 'NOTES', 'PART', 'SECTION',
        '1', '1A', '1B', '2', '3', '4', '5', '6', '7', '8', '9', '10',
        'I', 'II', 'III', 'IV', 'V',  # 로마 숫자
    }

    # 회사명에서 제거할 접미어 (전치사 이후)
    SUFFIX_PATTERNS_TO_REMOVE = [
        r'\s+for\s+.*$',  # "ASML Holdings for EUV lithography" -> "ASML Holdings"
        r'\s+as\s+.*$',
        r'\s+to\s+.*$',
        r'\s+in\s+.*$',
        r'\s+at\s+.*$',
        r'\s+with\s+.*$',
        r'\s+from\s+.*$',
    ]

    def _normalize_company_name(self, name: str) -> str:
        """
        회사명 정규화

        1. 앞뒤 공백 제거
        2. 불필요한 접두어 제거 (ITEM, RISK, FACTORS 등)
        3. 불필요한 접미어 제거 (for ..., as ... 등)
        4. 쉼표 처리
        """
        if not name:
            return ""

        # 앞뒤 공백 제거
        name = name.strip()

        # 연속 공백 정리
        name = re.sub(r'\s+', ' ', name)

        # 접두어 단어 제거 (대문자 단어가 PREFIX_WORDS_TO_REMOVE에 있으면 제거)
        words = name.split()
        clean_words = []
        found_company_start = False

        for word in words:
            upper_word = word.upper().rstrip('.,;:')
            if upper_word in self.PREFIX_WORDS_TO_REMOVE and not found_company_start:
                continue  # 접두어 제거
            else:
                found_company_start = True
                clean_words.append(word)

        name = ' '.join(clean_words)

        # 접미어 패턴 제거 (전치사 이후 텍스트)
        for pattern in self.SUFFIX_PATTERNS_TO_REMOVE:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)

        # 쉼표 뒤 불필요한 텍스트 제거
        if ',' in name:
            parts = name.split(',')
            # "Apple, Inc." -> "Apple Inc."
            if len(parts) >= 2 and parts[1].strip() in ['Inc', 'Inc.', 'Corp', 'Corp.', 'LLC', 'Ltd', 'Ltd.']:
                name = parts[0].strip() + ' ' + parts[1].strip()
            else:
                name = parts[0].strip()

        return name.strip()

    def _is_valid_company_name(self, name: str) -> bool:
        """
        유효한 회사명인지 확인

        검증 기준:
        1. 최소 3자, 최대 60자
        2. 제외 패턴에 해당하지 않음
        3. 무효 단어 포함하지 않음
        4. 최소 1개의 대문자로 시작하는 단어 포함
        5. 단어 수가 1-6개
        """
        if not name or len(name) < 3 or len(name) > 60:
            return False

        # 제외 패턴 확인
        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, name, re.IGNORECASE):
                return False

        # 무효 단어 확인 (소문자 비교)
        name_words = name.lower().split()
        for word in name_words:
            # 접미사 제거 후 비교
            clean_word = re.sub(r'[,\.]$', '', word)
            if clean_word in self.INVALID_WORDS:
                return False

        # 단어 수 확인 (1-6개)
        if len(name_words) < 1 or len(name_words) > 6:
            return False

        # 최소 1개의 대문자로 시작하는 단어 확인
        has_proper_noun = any(word[0].isupper() for word in name.split() if word)
        if not has_proper_noun:
            return False

        return True

    def match_to_stock(self, company_name: str) -> Optional[str]:
        """
        회사명 → 티커 심볼 매칭 (Stock DB fuzzy search)

        Args:
            company_name: 회사명

        Returns:
            매칭된 티커 심볼 또는 None
        """
        if not company_name:
            return None

        # 캐시 확인
        cache_key = company_name.lower()
        if cache_key in self._company_name_cache:
            return self._company_name_cache[cache_key]

        try:
            from stocks.models import Stock

            # 회사명에서 suffix 제거
            search_name = company_name
            for suffix_pattern in self.COMPANY_SUFFIXES:
                search_name = re.sub(suffix_pattern, '', search_name, flags=re.IGNORECASE)
            search_name = search_name.strip()

            # 1. 정확한 이름 매칭
            stock = Stock.objects.filter(
                stock_name__iexact=company_name
            ).first()

            if stock:
                self._company_name_cache[cache_key] = stock.symbol
                return stock.symbol

            # 2. Suffix 제거 후 매칭
            stock = Stock.objects.filter(
                stock_name__iexact=search_name
            ).first()

            if stock:
                self._company_name_cache[cache_key] = stock.symbol
                return stock.symbol

            # 3. Contains 검색 (앞부분 일치)
            stock = Stock.objects.filter(
                stock_name__istartswith=search_name
            ).first()

            if stock:
                self._company_name_cache[cache_key] = stock.symbol
                return stock.symbol

            # 4. 유명 회사 하드코딩 매핑 (SEC 10-K에서 자주 등장)
            known_companies = {
                'apple': 'AAPL',
                'microsoft': 'MSFT',
                'google': 'GOOGL',
                'alphabet': 'GOOGL',
                'amazon': 'AMZN',
                'meta': 'META',
                'facebook': 'META',
                'nvidia': 'NVDA',
                'amd': 'AMD',
                'advanced micro devices': 'AMD',
                'intel': 'INTC',
                'tsmc': 'TSM',
                'taiwan semiconductor': 'TSM',
                'samsung': 'SSNLF',
                'samsung electronics': 'SSNLF',
                'qualcomm': 'QCOM',
                'broadcom': 'AVGO',
                'texas instruments': 'TXN',
                'micron': 'MU',
                'micron technology': 'MU',
                'western digital': 'WDC',
                'seagate': 'STX',
                'dell': 'DELL',
                'dell technologies': 'DELL',
                'hp': 'HPQ',
                'hewlett packard': 'HPQ',
                'cisco': 'CSCO',
                'oracle': 'ORCL',
                'ibm': 'IBM',
                'salesforce': 'CRM',
                'adobe': 'ADBE',
                'tesla': 'TSLA',
                'foxconn': 'HNHPF',
                'hon hai': 'HNHPF',
                'asml': 'ASML',
            }

            search_key = search_name.lower()
            if search_key in known_companies:
                symbol = known_companies[search_key]
                self._company_name_cache[cache_key] = symbol
                return symbol

            # 매칭 실패
            self._company_name_cache[cache_key] = None
            return None

        except Exception as e:
            logger.warning(f"Error matching company name '{company_name}': {e}")
            self._company_name_cache[cache_key] = None
            return None

    def _extract_evidence(self, text: str, match: re.Match) -> str:
        """매칭 주변 문맥 추출 (증거 문장)"""
        start = max(0, match.start() - 100)
        end = min(len(text), match.end() + 200)

        evidence = text[start:end].strip()

        # 문장 경계로 자르기
        # 앞쪽: 마침표 이후부터
        if start > 0:
            period_pos = evidence.find('. ')
            if period_pos > 0 and period_pos < len(evidence) // 2:
                evidence = evidence[period_pos + 2:]

        # 뒤쪽: 마침표까지
        last_period = evidence.rfind('.')
        if last_period > len(evidence) // 2:
            evidence = evidence[:last_period + 1]

        return evidence.strip()

    def _deduplicate_relations(
        self,
        relations: List[SupplyChainRelation]
    ) -> List[SupplyChainRelation]:
        """중복 관계 제거 (높은 신뢰도 유지)"""
        seen: Dict[Tuple[str, str, str], SupplyChainRelation] = {}
        confidence_order = {'high': 0, 'medium-high': 1, 'medium': 2}

        for rel in relations:
            key = (rel.source_symbol, rel.target_name.lower(), rel.relation_type)

            if key not in seen:
                seen[key] = rel
            else:
                # 더 높은 신뢰도로 교체
                existing = seen[key]
                if confidence_order.get(rel.confidence, 3) < confidence_order.get(existing.confidence, 3):
                    seen[key] = rel
                # 매출 비중이 있으면 교체
                elif rel.revenue_percent and not existing.revenue_percent:
                    seen[key] = rel

        return list(seen.values())

    def calculate_confidence(
        self,
        has_percent: bool,
        percent_value: Optional[float],
        has_qualifier: bool
    ) -> str:
        """
        신뢰도 계산

        Args:
            has_percent: 매출 비중 언급 여부
            percent_value: 매출 비중 값
            has_qualifier: major/significant 등 수식어 사용 여부

        Returns:
            'high', 'medium-high', or 'medium'
        """
        if has_percent and percent_value and percent_value >= 10:
            return 'high'
        elif has_qualifier or (has_percent and percent_value and percent_value >= 5):
            return 'medium-high'
        else:
            return 'medium'
