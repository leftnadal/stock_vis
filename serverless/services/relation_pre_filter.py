"""
Relation Pre-Filter Service (Phase 5)

LLM 호출 전 뉴스/문서 필터링으로 비용 80% 절감.
Regex 기반 키워드 매칭으로 관계 추출 가능성이 높은 문서만 선별.

관계 타입별 키워드 패턴:
- ACQUIRED: acquire, acquisition, buy, purchase, merge
- INVESTED_IN: invest, stake, fund, back
- PARTNER_OF: partner, collaborate, alliance, joint venture
- SPIN_OFF: spin off, spinoff, separate, divest
- SUED_BY: sue, lawsuit, litigation, legal action

Usage:
    from serverless.services.relation_pre_filter import RelationPreFilter

    pre_filter = RelationPreFilter()

    # 뉴스 헤드라인 필터링
    if pre_filter.is_relation_candidate("Microsoft acquires Activision"):
        # LLM 호출
        pass

    # 배치 필터링
    candidates = pre_filter.filter_batch(news_list)

    # 관계 타입 힌트 추출
    hints = pre_filter.get_relation_hints("Apple partners with Goldman Sachs")
    # ['PARTNER_OF']
"""
import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PreFilterResult:
    """사전 필터링 결과"""
    is_candidate: bool
    relation_hints: List[str]  # 가능한 관계 타입 리스트
    company_mentions: List[str]  # 감지된 회사명 후보
    confidence: float  # 필터 신뢰도 (0.0 ~ 1.0)
    matched_patterns: List[str]  # 매칭된 패턴 목록


class RelationPreFilter:
    """
    LLM 호출 전 관계 추출 후보 필터링

    핵심 기능:
    1. Regex 패턴으로 관계 키워드 감지
    2. 회사명 후보 추출 (SymbolMatcher 입력용)
    3. 관계 타입 힌트 제공 (LLM 프롬프트 최적화)
    4. 비용 절감 (~80% LLM 호출 감소)
    """

    # 관계 타입별 키워드 패턴
    RELATION_PATTERNS = {
        'ACQUIRED': [
            r'\b(acquir(?:e[sd]?|ing)|acquisition|bought|purchas(?:e[sd]?|ing)|tak(?:e[sn]?|ing)\s+over)\b',
            r'\b(merg(?:e[sd]?|ing|er)|consolidat(?:e[sd]?|ing))\b',
            r'\b(buy(?:s|ing)?|buyout)\b(?=.*\b(company|firm|business|stake)\b)',
        ],
        'INVESTED_IN': [
            r'\b(invest(?:s|ed|ing|ment)?|stake|funding|fund(?:s|ed|ing)?)\b',
            r'\b(back(?:s|ed|ing)?|financ(?:e[sd]?|ing))\b(?=.*\b(startup|company|venture)\b)',
            r'\b(rais(?:e[sd]?|ing)|secur(?:e[sd]?|ing))\b.*\$[\d.]+\s*[BMK]',
            r'\$[\d.]+\s*[BMK].*\b(round|series|funding)\b',
        ],
        'PARTNER_OF': [
            r'\b(partner(?:s|ed|ing|ship)?|collaborat(?:e[sd]?|ing|ion))\b',
            r'\b(alliance|joint\s+venture|JV|team(?:s|ed|ing)?\s+up)\b',
            r'\b(deal|agreement|contract)\b.*\b(sign(?:s|ed)?|enter(?:s|ed)?)\b',
            r'\b(expand(?:s|ed|ing)?|extend(?:s|ed|ing)?)\b.*\b(partnership|relationship)\b',
        ],
        'SPIN_OFF': [
            r'\b(spin(?:s|ning)?\s*off|spinoff|spun\s+off)\b',
            r'\b(separat(?:e[sd]?|ing)|divest(?:s|ed|ing|iture)?)\b',
            r'\b(carve(?:s|d)?\s*out|split(?:s|ting)?)\b.*\b(business|unit|division)\b',
            r'\b(IPO|initial\s+public\s+offering)\b.*\b(subsidiary|unit)\b',
        ],
        'SUED_BY': [
            r'\b(su(?:e[sd]?|ing)|lawsuit|litigation|legal\s+action)\b',
            r'\b(fil(?:e[sd]?|ing))\b.*\b(suit|complaint|claim)\b',
            r'\b(antitrust|patent\s+infringement|copyright|trademark)\b.*\b(case|suit)\b',
            r'\b(settlement|verdict|ruling)\b.*\b(court|judge|jury)\b',
        ],
    }

    # 회사명 후보 패턴 (대문자로 시작하는 2-4 단어)
    COMPANY_NAME_PATTERNS = [
        # "Apple Inc.", "Microsoft Corp", "Alphabet Inc"
        r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\s+(?:Inc\.?|Corp\.?|Co\.?|Ltd\.?|LLC|LP|PLC)\b',
        # "Amazon", "Google", "Meta" (단일 대문자 단어, 문맥에 따라)
        r'\b([A-Z][a-zA-Z]{2,})\b(?=.*\b(?:said|announced|reported|disclosed)\b)',
        # 티커 심볼 형식 "(AAPL)", "(MSFT)"
        r'\(([A-Z]{1,5})\)',
        # "the tech giant", "the e-commerce company" 패턴 앞의 회사명
        r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b(?=.*\b(?:the\s+)?(?:tech\s+)?(?:giant|company|firm|corporation)\b)',
    ]

    # 필터링에서 제외할 일반 단어
    EXCLUDED_WORDS = {
        'The', 'This', 'That', 'These', 'Those', 'However', 'Moreover',
        'Furthermore', 'Additionally', 'Meanwhile', 'Nevertheless',
        'According', 'Based', 'Following', 'During', 'After', 'Before',
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December',
        'Today', 'Yesterday', 'Tomorrow', 'Week', 'Month', 'Year',
        'New', 'York', 'Wall', 'Street', 'Silicon', 'Valley',
        'CEO', 'CFO', 'COO', 'CTO', 'President', 'Chairman',
        'Reuters', 'Bloomberg', 'CNBC', 'CNN', 'BBC', 'Forbes',
    }

    def __init__(self):
        # 패턴 컴파일 (성능 최적화)
        self._compiled_relation_patterns = {}
        for rel_type, patterns in self.RELATION_PATTERNS.items():
            self._compiled_relation_patterns[rel_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

        self._compiled_company_patterns = [
            re.compile(p) for p in self.COMPANY_NAME_PATTERNS
        ]

        logger.info("RelationPreFilter initialized")

    def is_relation_candidate(self, text: str) -> bool:
        """
        텍스트가 관계 추출 후보인지 판단

        Args:
            text: 뉴스 헤드라인 또는 본문

        Returns:
            True if 관계 키워드 포함
        """
        if not text or len(text) < 20:
            return False

        for rel_type, patterns in self._compiled_relation_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    return True

        return False

    def get_relation_hints(self, text: str) -> List[str]:
        """
        텍스트에서 가능한 관계 타입 힌트 추출

        Args:
            text: 뉴스 헤드라인 또는 본문

        Returns:
            가능한 관계 타입 리스트 (예: ['ACQUIRED', 'PARTNER_OF'])
        """
        hints = []

        for rel_type, patterns in self._compiled_relation_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    if rel_type not in hints:
                        hints.append(rel_type)
                    break

        return hints

    def extract_company_mentions(self, text: str) -> List[str]:
        """
        텍스트에서 회사명 후보 추출

        Args:
            text: 뉴스 헤드라인 또는 본문

        Returns:
            회사명 후보 리스트 (중복 제거, 정렬)
        """
        mentions: Set[str] = set()

        for pattern in self._compiled_company_patterns:
            for match in pattern.finditer(text):
                company = match.group(1).strip()

                # 제외 단어 필터링
                if company in self.EXCLUDED_WORDS:
                    continue

                # 너무 짧은 단어 필터링 (2글자 이하)
                if len(company) <= 2:
                    continue

                mentions.add(company)

        return sorted(mentions)

    def analyze(self, text: str) -> PreFilterResult:
        """
        텍스트 종합 분석

        Args:
            text: 뉴스 헤드라인 또는 본문

        Returns:
            PreFilterResult with all analysis results
        """
        relation_hints = self.get_relation_hints(text)
        company_mentions = self.extract_company_mentions(text)
        matched_patterns = self._get_matched_patterns(text)

        is_candidate = len(relation_hints) > 0 and len(company_mentions) >= 2

        # 신뢰도 계산
        confidence = self._calculate_confidence(
            relation_hints, company_mentions, matched_patterns
        )

        return PreFilterResult(
            is_candidate=is_candidate,
            relation_hints=relation_hints,
            company_mentions=company_mentions,
            confidence=confidence,
            matched_patterns=matched_patterns,
        )

    def filter_batch(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = 'headline',
        min_confidence: float = 0.3
    ) -> List[Tuple[Dict[str, Any], PreFilterResult]]:
        """
        문서 배치 필터링

        Args:
            documents: 문서 리스트 (뉴스 등)
            text_field: 분석할 텍스트 필드명
            min_confidence: 최소 신뢰도 임계값

        Returns:
            (문서, 분석결과) 튜플 리스트 (후보만)
        """
        candidates = []

        for doc in documents:
            text = doc.get(text_field, '')
            if not text:
                continue

            result = self.analyze(text)

            if result.is_candidate and result.confidence >= min_confidence:
                candidates.append((doc, result))

        if documents:
            logger.info(
                f"Pre-filter: {len(candidates)}/{len(documents)} candidates "
                f"({len(candidates)/len(documents)*100:.1f}% pass rate)"
            )
        else:
            logger.info("Pre-filter: 0 documents to filter")

        return candidates

    def _get_matched_patterns(self, text: str) -> List[str]:
        """매칭된 패턴 목록 반환"""
        matched = []

        for rel_type, patterns in self._compiled_relation_patterns.items():
            for i, pattern in enumerate(patterns):
                match = pattern.search(text)
                if match:
                    matched.append(f"{rel_type}[{i}]: {match.group()}")

        return matched

    def _calculate_confidence(
        self,
        relation_hints: List[str],
        company_mentions: List[str],
        matched_patterns: List[str]
    ) -> float:
        """필터 신뢰도 계산"""
        score = 0.0

        # 관계 타입 감지 수 (0.3점)
        if len(relation_hints) >= 1:
            score += 0.3
        if len(relation_hints) >= 2:
            score += 0.1  # 여러 관계 감지 시 보너스

        # 회사명 감지 수 (0.4점)
        if len(company_mentions) >= 2:
            score += 0.4
        elif len(company_mentions) == 1:
            score += 0.2

        # 패턴 매칭 수 (0.2점)
        if len(matched_patterns) >= 2:
            score += 0.2
        elif len(matched_patterns) == 1:
            score += 0.1

        return min(score, 1.0)


# 편의 함수
_pre_filter = None


def get_pre_filter() -> RelationPreFilter:
    """싱글톤 인스턴스 반환"""
    global _pre_filter
    if _pre_filter is None:
        _pre_filter = RelationPreFilter()
    return _pre_filter
