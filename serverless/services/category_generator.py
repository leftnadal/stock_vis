"""
CategoryGenerator - AI 카테고리 생성 서비스

개별 종목에 대해 AI가 관계 카테고리를 생성합니다.

Tier 시스템:
- Tier 0: DB 쿼리 기반 (경쟁사, 동일 산업, 뉴스 동시언급)
- Tier 1: AI 산업 맥락 (EUV 기술 생태계, CUDA 플랫폼 등)
- Tier 2: AI 뉴스 기반 (반독점 규제 관련, AI 투자 수혜 등)

Usage:
    generator = CategoryGenerator()
    result = generator.get_categories('NVDA')
    # result = {
    #     "symbol": "NVDA",
    #     "categories": [
    #         {"id": "peer", "name": "경쟁사", "tier": 0, "count": 5, "icon": "⚔️"},
    #         {"id": "ai_ecosystem", "name": "AI 반도체 생태계", "tier": 1, "count": 8, "icon": "🧠"}
    #     ]
    # }
"""
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import date, timedelta

from django.core.cache import cache
from django.utils import timezone

from serverless.models import CategoryCache
from serverless.services.relationship_service import RelationshipService
from serverless.services.fmp_client import FMPClient, FMPAPIError


logger = logging.getLogger(__name__)


# 카테고리 아이콘 매핑
CATEGORY_ICONS = {
    'peer': '⚔️',
    'same_industry': '🏭',
    'co_mentioned': '📰',
    'sector_leaders': '👑',
    'supply_chain': '🔗',
    'ai_ecosystem': '🧠',
    'ev_ecosystem': '🔋',
    'fintech_ecosystem': '💳',
    'cloud_ecosystem': '☁️',
    'biotech_ecosystem': '🧬',
    'default': '📊',
}


class CategoryGenerator:
    """
    AI 카테고리 생성 서비스

    개별 종목에 대해 관계 카테고리를 생성합니다.
    Tier 0은 DB 기반, Tier 1/2는 AI 기반입니다.
    """

    MODEL = "gemini-2.5-flash"
    CACHE_TTL = 86400  # 24시간

    # 주요 테마 키워드 → 카테고리 매핑
    THEME_KEYWORDS = {
        'ai_ecosystem': ['AI', 'artificial intelligence', '인공지능', 'GPU', 'CUDA', 'tensor', 'machine learning'],
        'ev_ecosystem': ['EV', 'electric vehicle', '전기차', 'battery', '배터리', 'charging', 'autonomous'],
        'cloud_ecosystem': ['cloud', '클라우드', 'AWS', 'Azure', 'GCP', 'SaaS', 'infrastructure'],
        'fintech_ecosystem': ['fintech', 'payment', '결제', 'blockchain', 'crypto', 'digital banking'],
        'biotech_ecosystem': ['biotech', '바이오', 'pharma', 'drug', 'clinical trial', 'FDA'],
    }

    def __init__(self):
        self.relationship_service = RelationshipService()
        self.fmp_client = FMPClient()

    def get_categories(self, symbol: str) -> Dict[str, Any]:
        """
        종목의 카테고리 조회 (캐시 우선)

        Args:
            symbol: 종목 심볼

        Returns:
            {
                "symbol": "NVDA",
                "company_name": "NVIDIA Corporation",
                "categories": [
                    {"id": "peer", "name": "경쟁사", "tier": 0, "count": 5, "icon": "⚔️", "description": "..."},
                    ...
                ],
                "generation_time_ms": 150
            }
        """
        symbol = symbol.upper()
        today = date.today()

        # 1. Redis 캐시 확인
        cache_key = f'chain_sight:categories:{symbol}:{today}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 HIT: {cache_key}")
            return cached

        # 2. DB 캐시 확인
        db_cache = CategoryCache.objects.filter(
            symbol=symbol,
            date=today,
            expires_at__gt=timezone.now()
        ).first()

        if db_cache:
            result = {
                "symbol": symbol,
                "categories": db_cache.categories,
                "generation_time_ms": db_cache.generation_time_ms,
                "cached": True
            }
            cache.set(cache_key, result, self.CACHE_TTL)
            return result

        # 3. 새로 생성
        start_time = time.time()

        # 종목 프로필 조회
        try:
            profile = self.fmp_client.get_company_profile(symbol)
        except FMPAPIError:
            profile = {}

        company_name = profile.get('companyName', symbol)

        # Tier 0: DB 기반 카테고리 생성
        tier0_categories = self._build_tier0_categories(symbol)

        # Tier 1/2: AI 기반 카테고리 생성
        tier1_2_categories = self._build_ai_categories(symbol, profile, tier0_categories)

        # 결합
        all_categories = tier0_categories + tier1_2_categories

        generation_time_ms = int((time.time() - start_time) * 1000)

        # 결과 구성
        result = {
            "symbol": symbol,
            "company_name": company_name,
            "categories": all_categories,
            "generation_time_ms": generation_time_ms,
            "cached": False
        }

        # 4. 캐시 저장
        self._save_to_cache(symbol, today, all_categories, generation_time_ms)
        cache.set(cache_key, result, self.CACHE_TTL)

        logger.info(f"카테고리 생성 완료: {symbol} -> {len(all_categories)}개 ({generation_time_ms}ms)")

        return result

    def _build_tier0_categories(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Tier 0: DB 기반 카테고리 생성

        관계 데이터가 있는 경우에만 카테고리 생성
        """
        categories = []
        counts = self.relationship_service.get_relationship_counts(symbol)

        # 경쟁사 (PEER_OF)
        peer_count = counts.get('PEER_OF', 0)
        if peer_count > 0:
            categories.append({
                "id": "peer",
                "name": "경쟁사",
                "tier": 0,
                "count": peer_count,
                "icon": CATEGORY_ICONS['peer'],
                "description": f"{symbol}와 경쟁하는 동종업계 기업",
                "relationship_type": "PEER_OF"
            })

        # 동일 산업 (SAME_INDUSTRY)
        industry_count = counts.get('SAME_INDUSTRY', 0)
        if industry_count > 0:
            categories.append({
                "id": "same_industry",
                "name": "동일 산업",
                "tier": 0,
                "count": industry_count,
                "icon": CATEGORY_ICONS['same_industry'],
                "description": "같은 산업에 속한 기업",
                "relationship_type": "SAME_INDUSTRY"
            })

        # 뉴스 동시언급 (CO_MENTIONED)
        co_mentioned_count = counts.get('CO_MENTIONED', 0)
        if co_mentioned_count > 0:
            categories.append({
                "id": "co_mentioned",
                "name": "뉴스 연관",
                "tier": 0,
                "count": co_mentioned_count,
                "icon": CATEGORY_ICONS['co_mentioned'],
                "description": "최근 뉴스에서 함께 언급된 기업",
                "relationship_type": "CO_MENTIONED"
            })

        return categories

    def _build_ai_categories(
        self,
        symbol: str,
        profile: Dict,
        existing_categories: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Tier 1/2: AI 기반 카테고리 생성

        종목 프로필과 섹터/산업 정보를 기반으로 추가 카테고리 제안
        """
        categories = []

        sector = profile.get('sector', '')
        industry = profile.get('industry', '')
        description = profile.get('description', '')

        # 산업/섹터 기반 테마 카테고리 추론
        text_to_analyze = f"{sector} {industry} {description}".lower()

        for theme_id, keywords in self.THEME_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_to_analyze:
                    # 해당 테마 카테고리 추가
                    theme_name = self._get_theme_name(theme_id)
                    theme_desc = self._get_theme_description(theme_id, symbol)

                    # 중복 체크
                    if not any(c['id'] == theme_id for c in categories):
                        categories.append({
                            "id": theme_id,
                            "name": theme_name,
                            "tier": 1,
                            "count": "?",  # 아직 조회되지 않음
                            "icon": CATEGORY_ICONS.get(theme_id, CATEGORY_ICONS['default']),
                            "description": theme_desc,
                            "is_dynamic": True  # 동적으로 조회 필요
                        })
                    break

        # 섹터 리더 카테고리 (시가총액 상위)
        if profile.get('mktCap') and float(profile.get('mktCap', 0)) > 100_000_000_000:  # 100B 이상
            categories.append({
                "id": "sector_leaders",
                "name": f"{sector} 리더",
                "tier": 1,
                "count": "?",
                "icon": CATEGORY_ICONS['sector_leaders'],
                "description": f"{sector} 섹터의 시가총액 상위 기업",
                "is_dynamic": True,
                "sector": sector
            })

        return categories[:3]  # 최대 3개 AI 카테고리

    def _get_theme_name(self, theme_id: str) -> str:
        """테마 ID -> 한국어 이름"""
        names = {
            'ai_ecosystem': 'AI 생태계',
            'ev_ecosystem': 'EV 생태계',
            'cloud_ecosystem': '클라우드 생태계',
            'fintech_ecosystem': '핀테크 생태계',
            'biotech_ecosystem': '바이오테크 생태계',
            'sector_leaders': '섹터 리더',
        }
        return names.get(theme_id, theme_id)

    def _get_theme_description(self, theme_id: str, symbol: str) -> str:
        """테마 ID -> 설명"""
        descriptions = {
            'ai_ecosystem': f"{symbol}와 AI 기술로 연결된 기업들",
            'ev_ecosystem': f"{symbol}와 전기차 산업으로 연결된 기업들",
            'cloud_ecosystem': f"{symbol}와 클라우드 인프라로 연결된 기업들",
            'fintech_ecosystem': f"{symbol}와 금융 기술로 연결된 기업들",
            'biotech_ecosystem': f"{symbol}와 바이오/제약 기술로 연결된 기업들",
            'sector_leaders': f"{symbol}와 같은 섹터의 대표 기업들",
        }
        return descriptions.get(theme_id, f"{theme_id} 관련 기업들")

    def _save_to_cache(
        self,
        symbol: str,
        today: date,
        categories: List[Dict],
        generation_time_ms: int
    ) -> None:
        """DB 캐시 저장"""
        try:
            CategoryCache.objects.update_or_create(
                symbol=symbol,
                date=today,
                defaults={
                    'categories': categories,
                    'llm_model': self.MODEL,
                    'generation_time_ms': generation_time_ms,
                    'expires_at': timezone.now() + timedelta(hours=24)
                }
            )
        except Exception as e:
            logger.warning(f"카테고리 캐시 저장 실패: {e}")

    def ensure_relationships(self, symbol: str) -> bool:
        """
        종목의 관계 데이터가 없으면 동기화 트리거

        Returns:
            True if relationships exist or were synced
        """
        symbol = symbol.upper()

        if self.relationship_service.has_relationships(symbol):
            return True

        # 관계 데이터 동기화
        logger.info(f"관계 데이터 없음, 동기화 시작: {symbol}")
        results = self.relationship_service.sync_all(symbol)

        total = sum(results.values())
        logger.info(f"관계 동기화 완료: {symbol} -> {total}개")

        return total > 0
