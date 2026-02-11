"""
테마 매칭 서비스

ETF Holdings 및 키워드 기반 테마 매칭을 수행합니다.

Tier A (high): ETF Holdings 확인 → 팩트
Tier B (medium): 키워드 매칭 → 추정
Tier B+ (medium-high): 다중 근거 승격 → 강화된 추정

비용: $0 (추가 API 호출 없음)
"""
import logging
import re
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Set, Tuple

from django.db.models import Count, Q
from django.utils import timezone

from serverless.models import (
    ETFHolding,
    ETFProfile,
    StockRelationship,
    ThemeMatch,
)


logger = logging.getLogger(__name__)


# 테마별 키워드 정의
THEME_KEYWORDS = {
    # 섹터 테마 (Tier 1)
    'technology': {
        'keywords': ['technology', 'software', 'hardware', 'IT', 'tech', 'digital'],
        'name': '기술',
        'icon': '💻',
    },
    'healthcare': {
        'keywords': ['healthcare', 'pharma', 'biotech', 'medical', 'drug', 'hospital'],
        'name': '헬스케어',
        'icon': '🏥',
    },
    'financials': {
        'keywords': ['bank', 'financial', 'insurance', 'investment', 'capital'],
        'name': '금융',
        'icon': '🏦',
    },
    'energy': {
        'keywords': ['oil', 'gas', 'energy', 'petroleum', 'drilling'],
        'name': '에너지',
        'icon': '⛽',
    },
    'industrials': {
        'keywords': ['industrial', 'manufacturing', 'aerospace', 'defense', 'machinery'],
        'name': '산업재',
        'icon': '🏭',
    },
    'communication': {
        'keywords': ['telecom', 'media', 'entertainment', 'streaming', 'communication'],
        'name': '통신',
        'icon': '📡',
    },
    'consumer_discretionary': {
        'keywords': ['retail', 'consumer', 'luxury', 'apparel', 'restaurant', 'hotel'],
        'name': '경기소비재',
        'icon': '🛍️',
    },
    'consumer_staples': {
        'keywords': ['food', 'beverage', 'household', 'personal', 'grocery'],
        'name': '필수소비재',
        'icon': '🛒',
    },
    'utilities': {
        'keywords': ['utility', 'electric', 'water', 'gas utility', 'power'],
        'name': '유틸리티',
        'icon': '💡',
    },
    'real_estate': {
        'keywords': ['real estate', 'REIT', 'property', 'mortgage'],
        'name': '부동산',
        'icon': '🏢',
    },
    'materials': {
        'keywords': ['materials', 'chemical', 'mining', 'steel', 'metals'],
        'name': '소재',
        'icon': '⚗️',
    },

    # 니치 테마 (Tier 2)
    'semiconductor': {
        'keywords': [
            'semiconductor', 'chip', 'wafer', 'fab', 'foundry',
            'GPU', 'CPU', 'memory', 'NAND', 'DRAM', 'silicon'
        ],
        'name': '반도체',
        'icon': '🔌',
    },
    'innovation': {
        'keywords': [
            'innovation', 'disruptive', 'autonomous', 'AI', 'machine learning',
            'blockchain', 'fintech', 'genomics'
        ],
        'name': '혁신 기술',
        'icon': '🚀',
    },
    'genomics': {
        'keywords': [
            'genomics', 'gene', 'DNA', 'CRISPR', 'cell therapy',
            'biotech', 'precision medicine', 'molecular'
        ],
        'name': '유전체학',
        'icon': '🧬',
    },
    'robotics_ai': {
        'keywords': [
            'robot', 'robotics', 'automation', 'AI', 'artificial intelligence',
            'machine learning', 'deep learning', 'neural'
        ],
        'name': '로봇/AI',
        'icon': '🤖',
    },
    'solar': {
        'keywords': [
            'solar', 'photovoltaic', 'renewable', 'clean energy',
            'inverter', 'panel'
        ],
        'name': '태양광',
        'icon': '☀️',
    },
    'cybersecurity': {
        'keywords': [
            'cybersecurity', 'security', 'firewall', 'encryption',
            'identity', 'authentication', 'zero trust'
        ],
        'name': '사이버보안',
        'icon': '🔐',
    },
    'lithium_battery': {
        'keywords': [
            'lithium', 'battery', 'EV', 'electric vehicle', 'charging',
            'cathode', 'anode', 'solid state'
        ],
        'name': '리튬/배터리',
        'icon': '🔋',
    },
    'clean_energy': {
        'keywords': [
            'clean energy', 'renewable', 'wind', 'solar', 'hydro',
            'green', 'sustainable', 'carbon neutral'
        ],
        'name': '클린에너지',
        'icon': '🌱',
    },
    'china_internet': {
        'keywords': [
            'china', 'chinese', 'alibaba', 'tencent', 'baidu',
            'jd', 'pinduoduo', 'meituan'
        ],
        'name': '중국 인터넷',
        'icon': '🇨🇳',
    },
    'igaming': {
        'keywords': [
            'gaming', 'casino', 'betting', 'gambling', 'sports betting',
            'igaming', 'fantasy sports'
        ],
        'name': '온라인 게이밍',
        'icon': '🎰',
    },
}

# 테마 ID → 대표 ETF 매핑
THEME_TO_ETF = {
    'technology': 'XLK',
    'healthcare': 'XLV',
    'financials': 'XLF',
    'energy': 'XLE',
    'industrials': 'XLI',
    'communication': 'XLC',
    'consumer_discretionary': 'XLY',
    'consumer_staples': 'XLP',
    'utilities': 'XLU',
    'real_estate': 'XLRE',
    'materials': 'XLB',
    'semiconductor': 'SOXX',
    'innovation': 'ARKK',
    'genomics': 'ARKG',
    'robotics_ai': 'BOTZ',
    'solar': 'TAN',
    'cybersecurity': 'HACK',
    'lithium_battery': 'LIT',
    'clean_energy': 'ICLN',
    'china_internet': 'KWEB',
    'igaming': 'BETZ',
}


class ThemeMatchingService:
    """
    테마 매칭 서비스

    ETF Holdings와 키워드 기반으로 종목-테마 매칭을 수행합니다.

    Usage:
        service = ThemeMatchingService()

        # Tier A 매칭 (ETF Holdings 기반)
        tier_a_matches = service.match_tier_a('NVDA')

        # Tier B 매칭 (키워드 기반)
        tier_b_matches = service.match_tier_b('NVDA', company_description="...")

        # 테마별 종목 조회
        stocks = service.get_theme_stocks('semiconductor', limit=20)

        # 종목의 모든 테마 조회
        themes = service.get_stock_themes('NVDA')
    """

    def match_tier_a(self, symbol: str) -> List[ThemeMatch]:
        """
        Tier A 매칭 (ETF Holdings 기반)

        ETF에 종목이 포함되어 있으면 confidence: high

        Args:
            symbol: 종목 심볼

        Returns:
            ThemeMatch 리스트
        """
        symbol = symbol.upper()
        matches = []

        # 해당 종목을 보유한 모든 ETF 조회
        holdings = ETFHolding.objects.filter(
            stock_symbol=symbol
        ).select_related('etf').order_by('etf__tier', '-weight_percent')

        for holding in holdings:
            etf = holding.etf
            theme_id = etf.theme_id

            # 기존 매치 확인 또는 생성
            match, created = ThemeMatch.objects.update_or_create(
                stock_symbol=symbol,
                theme_id=theme_id,
                defaults={
                    'confidence': 'high',
                    'source': 'etf_holding',
                    'etf_symbol': etf.symbol,
                    'weight_in_etf': holding.weight_percent,
                    'evidence': [
                        f"{etf.symbol} ({etf.name}) #{holding.rank}위",
                        f"비중 {holding.weight_percent}%"
                    ],
                }
            )
            matches.append(match)

        logger.info(f"{symbol}: Tier A 매칭 {len(matches)}개")
        return matches

    def match_tier_b(
        self,
        symbol: str,
        company_name: Optional[str] = None,
        company_description: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> List[ThemeMatch]:
        """
        Tier B 매칭 (키워드 기반)

        종목의 이름, 설명, 섹터, 산업에서 테마 키워드 매칭

        Args:
            symbol: 종목 심볼
            company_name: 회사명
            company_description: 회사 설명
            sector: 섹터
            industry: 산업

        Returns:
            ThemeMatch 리스트
        """
        symbol = symbol.upper()
        matches = []

        # 매칭용 텍스트 조합
        text_parts = []
        if company_name:
            text_parts.append(company_name)
        if company_description:
            text_parts.append(company_description)
        if sector:
            text_parts.append(sector)
        if industry:
            text_parts.append(industry)

        combined_text = ' '.join(text_parts).lower()

        # 이미 Tier A로 매칭된 테마 확인
        existing_tier_a = set(
            ThemeMatch.objects.filter(
                stock_symbol=symbol,
                confidence='high'
            ).values_list('theme_id', flat=True)
        )

        # 각 테마별 키워드 매칭
        for theme_id, theme_config in THEME_KEYWORDS.items():
            if theme_id in existing_tier_a:
                continue  # Tier A가 있으면 스킵

            matched_keywords = []
            for keyword in theme_config['keywords']:
                if keyword.lower() in combined_text:
                    matched_keywords.append(keyword)

            if matched_keywords:
                evidence = [f"키워드 매칭: {', '.join(matched_keywords[:3])}"]

                # 승격 체크 (Tier B → medium-high)
                confidence = self._check_promotion(symbol, theme_id, matched_keywords)

                match, created = ThemeMatch.objects.update_or_create(
                    stock_symbol=symbol,
                    theme_id=theme_id,
                    defaults={
                        'confidence': confidence,
                        'source': 'keyword',
                        'evidence': evidence,
                    }
                )
                matches.append(match)

        logger.info(f"{symbol}: Tier B 매칭 {len(matches)}개")
        return matches

    def _check_promotion(
        self,
        symbol: str,
        theme_id: str,
        matched_keywords: List[str]
    ) -> str:
        """
        Tier B → medium-high 승격 체크

        승격 조건:
        1. CO_MENTIONED에서 같은 테마 ETF와 반복 동시언급
        2. 같은 테마의 다른 종목들과 다중 PEER_OF 관계

        Args:
            symbol: 종목 심볼
            theme_id: 테마 ID
            matched_keywords: 매칭된 키워드 리스트

        Returns:
            'medium-high' 또는 'medium'
        """
        # 조건 1: ETF와 동시언급 체크
        etf_symbol = THEME_TO_ETF.get(theme_id)
        if etf_symbol:
            co_mentions = StockRelationship.objects.filter(
                Q(source_symbol=symbol, target_symbol=etf_symbol) |
                Q(source_symbol=etf_symbol, target_symbol=symbol),
                relationship_type='CO_MENTIONED'
            ).count()

            if co_mentions >= 2:
                logger.debug(f"{symbol}: ETF {etf_symbol}와 {co_mentions}회 동시언급 → 승격")
                return 'medium-high'

        # 조건 2: 같은 테마 종목들과 PEER_OF 관계
        theme_stocks = ThemeMatch.objects.filter(
            theme_id=theme_id,
            confidence='high'
        ).values_list('stock_symbol', flat=True)[:50]

        if theme_stocks:
            peer_count = StockRelationship.objects.filter(
                source_symbol=symbol,
                target_symbol__in=list(theme_stocks),
                relationship_type='PEER_OF'
            ).count()

            if peer_count >= 3:
                logger.debug(f"{symbol}: 같은 테마 {peer_count}개 종목과 PEER → 승격")
                return 'medium-high'

        return 'medium'

    def get_theme_stocks(
        self,
        theme_id: str,
        limit: int = 20,
        min_confidence: str = 'medium'
    ) -> List[Dict]:
        """
        테마별 종목 조회

        Args:
            theme_id: 테마 ID
            limit: 최대 반환 개수
            min_confidence: 최소 confidence 레벨

        Returns:
            [
                {
                    'symbol': 'NVDA',
                    'confidence': 'high',
                    'source': 'etf_holding',
                    'etf_symbol': 'SOXX',
                    'weight_in_etf': 8.5,
                    'evidence': [...]
                },
                ...
            ]
        """
        confidence_order = {'high': 0, 'medium-high': 1, 'medium': 2}

        # 최소 confidence 이상인 종목만 필터
        confidence_filter = []
        for conf, order in confidence_order.items():
            if order <= confidence_order.get(min_confidence, 2):
                confidence_filter.append(conf)

        matches = ThemeMatch.objects.filter(
            theme_id=theme_id,
            confidence__in=confidence_filter
        ).order_by('confidence', '-weight_in_etf')[:limit]

        return [
            {
                'symbol': m.stock_symbol,
                'confidence': m.confidence,
                'source': m.source,
                'etf_symbol': m.etf_symbol,
                'weight_in_etf': float(m.weight_in_etf) if m.weight_in_etf else None,
                'evidence': m.evidence,
            }
            for m in matches
        ]

    def get_stock_themes(self, symbol: str) -> List[Dict]:
        """
        종목의 모든 테마 조회

        Args:
            symbol: 종목 심볼

        Returns:
            [
                {
                    'theme_id': 'semiconductor',
                    'name': '반도체',
                    'icon': '🔌',
                    'confidence': 'high',
                    'etf_symbol': 'SOXX'
                },
                ...
            ]
        """
        matches = ThemeMatch.objects.filter(
            stock_symbol=symbol.upper()
        ).order_by('confidence')

        result = []
        for m in matches:
            theme_config = THEME_KEYWORDS.get(m.theme_id, {})
            result.append({
                'theme_id': m.theme_id,
                'name': theme_config.get('name', m.theme_id),
                'icon': theme_config.get('icon', '📊'),
                'confidence': m.confidence,
                'source': m.source,
                'etf_symbol': m.etf_symbol,
                'evidence': m.evidence,
            })

        return result

    def get_theme_info(self, theme_id: str) -> Optional[Dict]:
        """
        테마 정보 조회

        Args:
            theme_id: 테마 ID

        Returns:
            {
                'id': 'semiconductor',
                'name': '반도체',
                'icon': '🔌',
                'keywords': [...],
                'etf_symbol': 'SOXX',
                'stock_count': 45
            }
        """
        config = THEME_KEYWORDS.get(theme_id)
        if not config:
            return None

        stock_count = ThemeMatch.objects.filter(theme_id=theme_id).count()

        return {
            'id': theme_id,
            'name': config['name'],
            'icon': config['icon'],
            'keywords': config['keywords'],
            'etf_symbol': THEME_TO_ETF.get(theme_id),
            'stock_count': stock_count,
        }

    def get_all_themes(self) -> List[Dict]:
        """
        모든 테마 목록 조회

        Returns:
            테마 정보 리스트 (종목 수 내림차순)
        """
        # 테마별 종목 수 집계
        theme_counts = ThemeMatch.objects.values('theme_id').annotate(
            count=Count('stock_symbol')
        ).order_by('-count')

        count_map = {t['theme_id']: t['count'] for t in theme_counts}

        themes = []
        for theme_id, config in THEME_KEYWORDS.items():
            themes.append({
                'id': theme_id,
                'name': config['name'],
                'icon': config['icon'],
                'etf_symbol': THEME_TO_ETF.get(theme_id),
                'stock_count': count_map.get(theme_id, 0),
            })

        return sorted(themes, key=lambda x: x['stock_count'], reverse=True)

    def refresh_all_matches(self) -> Dict[str, int]:
        """
        전체 ThemeMatch 갱신 (ETF Holdings 기반)

        모든 ETF Holdings를 스캔하여 Tier A 매칭을 재생성합니다.

        Returns:
            {'created': 100, 'updated': 50, 'total': 150}
        """
        # 오늘 또는 가장 최근 snapshot
        latest_holdings = ETFHolding.objects.select_related('etf').order_by(
            'etf', '-snapshot_date', 'rank'
        )

        # ETF별 최신 holdings만 사용
        processed_etfs: Set[str] = set()
        created_count = 0
        updated_count = 0

        for holding in latest_holdings:
            etf_symbol = holding.etf.symbol
            if etf_symbol in processed_etfs:
                continue

            # 해당 ETF의 모든 holdings 처리
            etf_holdings = ETFHolding.objects.filter(
                etf=holding.etf,
                snapshot_date=holding.snapshot_date
            )

            for h in etf_holdings:
                match, created = ThemeMatch.objects.update_or_create(
                    stock_symbol=h.stock_symbol,
                    theme_id=holding.etf.theme_id,
                    defaults={
                        'confidence': 'high',
                        'source': 'etf_holding',
                        'etf_symbol': holding.etf.symbol,
                        'weight_in_etf': h.weight_percent,
                        'evidence': [
                            f"{holding.etf.symbol} #{h.rank}위 ({h.weight_percent}%)"
                        ],
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            processed_etfs.add(etf_symbol)

        total = created_count + updated_count
        logger.info(f"ThemeMatch 갱신 완료: 생성 {created_count}, 업데이트 {updated_count}, 총 {total}")

        return {
            'created': created_count,
            'updated': updated_count,
            'total': total,
        }

    def get_etf_peers(
        self,
        symbol: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        ETF 동반 종목 조회

        같은 ETF에 포함된 다른 종목들 반환

        Args:
            symbol: 기준 종목 심볼
            limit: 최대 반환 개수

        Returns:
            [
                {
                    'symbol': 'AMD',
                    'etfs_in_common': ['SOXX', 'XLK'],
                    'total_weight': 15.5,
                    'reason': 'SOXX, XLK 공통 보유'
                },
                ...
            ]
        """
        symbol = symbol.upper()

        # 해당 종목을 보유한 ETF 목록
        my_etfs = set(
            ETFHolding.objects.filter(
                stock_symbol=symbol
            ).values_list('etf__symbol', flat=True)
        )

        if not my_etfs:
            return []

        # 같은 ETF에 있는 다른 종목들 집계
        peer_holdings = ETFHolding.objects.filter(
            etf__symbol__in=my_etfs
        ).exclude(
            stock_symbol=symbol
        ).values('stock_symbol').annotate(
            etf_count=Count('etf__symbol', distinct=True),
            total_weight=Sum('weight_percent')
        ).order_by('-etf_count', '-total_weight')[:limit * 2]

        # 상세 정보 조합
        results = []
        for peer in peer_holdings[:limit]:
            peer_symbol = peer['stock_symbol']

            # 공통 ETF 목록
            common_etfs = list(
                ETFHolding.objects.filter(
                    stock_symbol=peer_symbol,
                    etf__symbol__in=my_etfs
                ).values_list('etf__symbol', flat=True)
            )

            results.append({
                'symbol': peer_symbol,
                'etfs_in_common': common_etfs,
                'total_weight': float(peer['total_weight']) if peer['total_weight'] else 0,
                'reason': f"{', '.join(common_etfs[:3])} 공통 보유",
            })

        return results


# Django ORM에서 Sum 사용을 위한 import 추가
from django.db.models import Sum


# 싱글톤 인스턴스
_theme_service_instance: Optional[ThemeMatchingService] = None


def get_theme_matching_service() -> ThemeMatchingService:
    """ThemeMatchingService 싱글톤 인스턴스 반환"""
    global _theme_service_instance
    if _theme_service_instance is None:
        _theme_service_instance = ThemeMatchingService()
    return _theme_service_instance
