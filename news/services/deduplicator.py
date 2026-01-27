"""
뉴스 중복 제거 서비스

URL 정규화 및 해시 기반 중복 제거
"""

import hashlib
import logging
from typing import List, Set
from difflib import SequenceMatcher

from ..providers.base import RawNewsArticle

logger = logging.getLogger(__name__)


class NewsDeduplicator:
    """뉴스 중복 제거 서비스"""

    def __init__(self, title_similarity_threshold: float = 0.85):
        """
        Args:
            title_similarity_threshold: 제목 유사도 임계값 (0.0 ~ 1.0)
        """
        self.title_similarity_threshold = title_similarity_threshold

    def deduplicate(self, articles: List[RawNewsArticle]) -> List[RawNewsArticle]:
        """
        뉴스 리스트에서 중복 제거

        1. URL 해시 기반 중복 제거
        2. 제목 유사도 기반 중복 제거

        Args:
            articles: 뉴스 리스트

        Returns:
            List[RawNewsArticle]: 중복 제거된 뉴스 리스트
        """
        if not articles:
            return []

        # 1단계: URL 해시 기반 중복 제거
        url_deduped = self._deduplicate_by_url(articles)

        # 2단계: 제목 유사도 기반 중복 제거
        final_deduped = self._deduplicate_by_title_similarity(url_deduped)

        removed_count = len(articles) - len(final_deduped)
        logger.info(f"Deduplication: {len(articles)} -> {len(final_deduped)} ({removed_count} removed)")

        return final_deduped

    def _deduplicate_by_url(self, articles: List[RawNewsArticle]) -> List[RawNewsArticle]:
        """
        URL 해시 기반 중복 제거

        Args:
            articles: 뉴스 리스트

        Returns:
            List[RawNewsArticle]: 중복 제거된 뉴스 리스트
        """
        seen_hashes: Set[str] = set()
        unique_articles = []

        for article in articles:
            url_hash = self._calculate_url_hash(article.url)

            if url_hash not in seen_hashes:
                seen_hashes.add(url_hash)
                unique_articles.append(article)
            else:
                logger.debug(f"Duplicate URL found: {article.url}")

        return unique_articles

    def _deduplicate_by_title_similarity(
        self,
        articles: List[RawNewsArticle]
    ) -> List[RawNewsArticle]:
        """
        제목 유사도 기반 중복 제거

        같은 뉴스가 여러 출처에서 나올 경우,
        URL은 다르지만 제목이 매우 유사한 경우 중복으로 간주

        Args:
            articles: 뉴스 리스트

        Returns:
            List[RawNewsArticle]: 중복 제거된 뉴스 리스트
        """
        unique_articles = []

        for article in articles:
            is_duplicate = False

            for existing in unique_articles:
                similarity = self._calculate_title_similarity(
                    article.title,
                    existing.title
                )

                if similarity >= self.title_similarity_threshold:
                    logger.debug(
                        f"Similar title found (similarity: {similarity:.2f}): "
                        f"'{article.title}' vs '{existing.title}'"
                    )
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_articles.append(article)

        return unique_articles

    def _calculate_url_hash(self, url: str) -> str:
        """
        URL 해시 계산

        Args:
            url: URL

        Returns:
            str: SHA256 해시
        """
        normalized_url = url.lower().strip()
        return hashlib.sha256(normalized_url.encode()).hexdigest()

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        제목 유사도 계산 (Sequence Matcher 사용)

        Args:
            title1: 제목 1
            title2: 제목 2

        Returns:
            float: 유사도 (0.0 ~ 1.0)
        """
        # 대소문자 무시, 공백 정규화
        t1 = ' '.join(title1.lower().split())
        t2 = ' '.join(title2.lower().split())

        return SequenceMatcher(None, t1, t2).ratio()
