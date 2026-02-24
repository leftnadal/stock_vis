"""
ChainSightStockService - 개별 종목 Chain Sight 메인 서비스

개별 주식 페이지에서 AI 가이드와 함께하는 주식 탐험 기능.
카테고리 생성, 관련 종목 조회, AI 인사이트 제공.

Neo4j 우선 사용, PostgreSQL fallback.

Usage:
    service = ChainSightStockService()

    # 카테고리 조회
    categories = service.get_categories('NVDA')

    # 카테고리별 종목 조회
    stocks = service.get_category_stocks('NVDA', 'peer')
"""
import logging
import time
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from django.core.cache import cache

from serverless.services.category_generator import CategoryGenerator
from serverless.services.relationship_service import RelationshipService
from serverless.services.fmp_client import FMPClient, FMPAPIError
from serverless.models import StockRelationship, ThemeMatch, ETFHolding

if TYPE_CHECKING:
    from serverless.services.neo4j_chain_sight_service import Neo4jChainSightService


logger = logging.getLogger(__name__)


class ChainSightStockService:
    """
    개별 종목 Chain Sight 메인 서비스

    핵심 기능:
    1. 카테고리 조회 (AI 제안)
    2. 카테고리별 관련 종목 조회 (Neo4j 우선, PostgreSQL fallback)
    3. AI 인사이트 제공
    4. Cold Start 처리 (관계 데이터 자동 동기화)
    """

    CACHE_TTL = 300  # 5분

    def __init__(self):
        self.category_generator = CategoryGenerator()
        self.relationship_service = RelationshipService()
        self.fmp_client = FMPClient()
        self._neo4j_service: Optional['Neo4jChainSightService'] = None

    def _get_neo4j_service(self) -> Optional['Neo4jChainSightService']:
        """Neo4j 서비스 lazy 초기화"""
        if self._neo4j_service is None:
            try:
                from serverless.services.neo4j_chain_sight_service import Neo4jChainSightService
                self._neo4j_service = Neo4jChainSightService()
            except Exception as e:
                logger.warning(f"Neo4j 서비스 초기화 실패: {e}")
                return None
        return self._neo4j_service if self._neo4j_service.is_available() else None

    def get_categories(self, symbol: str) -> Dict[str, Any]:
        """
        종목의 카테고리 조회

        Cold Start 처리: 관계 데이터가 없으면 자동 동기화

        Args:
            symbol: 종목 심볼

        Returns:
            {
                "symbol": "NVDA",
                "company_name": "NVIDIA Corporation",
                "categories": [
                    {"id": "peer", "name": "경쟁사", "tier": 0, "count": 5, ...},
                    {"id": "ai_ecosystem", "name": "AI 생태계", "tier": 1, "count": "?", ...}
                ],
                "is_cold_start": false,
                "generation_time_ms": 150
            }
        """
        symbol = symbol.upper()
        logger.info(f"Chain Sight 카테고리 조회: {symbol}")

        start_time = time.time()

        # Cold Start 체크 및 처리
        is_cold_start = not self.relationship_service.has_relationships(symbol)
        if is_cold_start:
            logger.info(f"Cold Start 감지, 관계 동기화 중: {symbol}")
            self.category_generator.ensure_relationships(symbol)

        # 카테고리 생성
        result = self.category_generator.get_categories(symbol)
        result['is_cold_start'] = is_cold_start

        total_time = int((time.time() - start_time) * 1000)
        logger.info(f"Chain Sight 카테고리 완료: {symbol} -> {len(result['categories'])}개 ({total_time}ms)")

        return result

    def get_category_stocks(
        self,
        symbol: str,
        category_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        특정 카테고리의 관련 종목 조회

        Args:
            symbol: 원본 종목 심볼
            category_id: 카테고리 ID (peer, same_industry, co_mentioned, ai_ecosystem 등)
            limit: 최대 반환 개수

        Returns:
            {
                "symbol": "NVDA",
                "category": {"id": "peer", "name": "경쟁사", ...},
                "stocks": [
                    {
                        "symbol": "AMD",
                        "company_name": "Advanced Micro Devices",
                        "strength": 0.85,
                        "current_price": 125.50,
                        "change_percent": 2.3,
                        "market_cap": 200000000000,
                        "sector": "Technology"
                    }
                ],
                "ai_insights": "AMD는 NVIDIA의 주요 GPU 경쟁사로...",
                "follow_up_questions": ["GPU 시장 점유율 비교가 궁금하신가요?"]
            }
        """
        symbol = symbol.upper()
        logger.info(f"Chain Sight 카테고리 종목 조회: {symbol} / {category_id}")

        start_time = time.time()

        # 캐시 확인
        cache_key = f'chain_sight:stocks:{symbol}:{category_id}:{limit}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 HIT: {cache_key}")
            return cached

        # 카테고리 정보 조회
        categories_result = self.category_generator.get_categories(symbol)
        category = next(
            (c for c in categories_result.get('categories', []) if c['id'] == category_id),
            None
        )

        if not category:
            return {
                "symbol": symbol,
                "category": {"id": category_id, "name": category_id},
                "stocks": [],
                "error": f"카테고리를 찾을 수 없습니다: {category_id}"
            }

        # 카테고리 타입에 따른 종목 조회
        rel_type = category.get('relationship_type')
        if rel_type == 'ETF_PEER':
            # ETF 동반 종목: ETFHolding 모델에서 조회
            stocks = self._get_etf_peer_stocks(symbol, limit)
        elif rel_type == 'HAS_THEME':
            # 테마 종목: ThemeMatch 모델에서 조회
            stocks = self._get_theme_stocks(
                symbol, category.get('theme_id', ''), limit
            )
        elif rel_type:
            # Tier 0: DB 기반 (PEER_OF, SAME_INDUSTRY, CO_MENTIONED)
            stocks = self._get_relationship_stocks(
                symbol,
                rel_type,
                limit
            )
        elif category.get('is_dynamic'):
            # Tier 1/2: 동적 조회 (테마, 섹터 리더 등)
            stocks = self._get_dynamic_stocks(
                symbol,
                category_id,
                category,
                limit
            )
        else:
            stocks = []

        # AI 인사이트 생성
        ai_insights = self._generate_insights(symbol, category, stocks)
        follow_up_questions = self._generate_follow_up_questions(symbol, category)

        computation_time = int((time.time() - start_time) * 1000)

        result = {
            "symbol": symbol,
            "category": category,
            "stocks": stocks,
            "ai_insights": ai_insights,
            "follow_up_questions": follow_up_questions,
            "computation_time_ms": computation_time
        }

        # 캐시 저장
        cache.set(cache_key, result, self.CACHE_TTL)

        logger.info(f"Chain Sight 종목 조회 완료: {symbol}/{category_id} -> {len(stocks)}개 ({computation_time}ms)")

        return result

    def _get_relationship_stocks(
        self,
        symbol: str,
        relationship_type: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        관계 타입 기반 종목 조회 (Tier 0)

        Neo4j 우선 사용, PostgreSQL fallback.
        """
        # Neo4j 우선 시도
        neo4j_service = self._get_neo4j_service()
        if neo4j_service:
            stocks = self._get_relationship_stocks_from_neo4j(
                neo4j_service, symbol, relationship_type, limit
            )
            if stocks:
                logger.debug(f"Neo4j에서 {len(stocks)}개 종목 조회: {symbol}/{relationship_type}")
                return stocks
            logger.debug(f"Neo4j 결과 없음, PostgreSQL fallback: {symbol}/{relationship_type}")

        # PostgreSQL fallback
        return self._get_relationship_stocks_from_postgres(symbol, relationship_type, limit)

    def _get_relationship_stocks_from_neo4j(
        self,
        neo4j_service: 'Neo4jChainSightService',
        symbol: str,
        relationship_type: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Neo4j에서 관계 기반 종목 조회"""
        try:
            related = neo4j_service.get_related_stocks(
                symbol=symbol,
                rel_type=relationship_type,
                limit=limit
            )

            if not related:
                return []

            stocks = []
            for rel in related:
                target_symbol = rel['symbol']

                # 실시간 가격 정보 조회 (FMP Quote API)
                current_price = None
                change_percent = None
                market_cap = rel.get('market_cap')  # Neo4j에서 먼저 시도

                try:
                    quote = self.fmp_client.get_quote(target_symbol)
                    current_price = quote.get('price')
                    change_percent = quote.get('changePercentage')  # 's' 없음
                    # Neo4j에 market_cap 없으면 quote에서 가져옴
                    if not market_cap:
                        market_cap = quote.get('marketCap')
                except Exception as e:
                    logger.debug(f"Quote 조회 실패 {target_symbol}: {e}")

                stocks.append({
                    "symbol": target_symbol,
                    "company_name": rel.get('name', target_symbol),
                    "strength": rel.get('weight', 0.5),
                    "current_price": current_price,
                    "change_percent": change_percent,
                    "market_cap": market_cap,
                    "sector": rel.get('sector'),
                    "industry": rel.get('industry'),
                    "relationship_context": rel.get('context', {}),
                    "data_source": "neo4j",
                    "tags": self._get_stock_tags(symbol, target_symbol),
                })

            return stocks

        except Exception as e:
            logger.warning(f"Neo4j 종목 조회 실패 {symbol}/{relationship_type}: {e}")
            return []

    def _get_relationship_stocks_from_postgres(
        self,
        symbol: str,
        relationship_type: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """PostgreSQL에서 관계 기반 종목 조회 (fallback)"""
        relationships = self.relationship_service.get_relationships(
            symbol,
            relationship_type=relationship_type,
            limit=limit
        )

        stocks = []
        for rel in relationships:
            target_symbol = rel['target_symbol']

            # 종목 프로필 조회
            profile = self.relationship_service.get_target_profile(target_symbol)
            if not profile:
                continue

            stocks.append({
                "symbol": target_symbol,
                "company_name": profile.get('company_name', target_symbol),
                "strength": rel['strength'],
                "current_price": profile.get('price'),
                "change_percent": profile.get('changes_percentage'),
                "market_cap": profile.get('market_cap'),
                "sector": profile.get('sector'),
                "industry": profile.get('industry'),
                "relationship_context": rel.get('context', {}),
                "data_source": "postgres",
                "tags": self._get_stock_tags(symbol, target_symbol),
            })

        return stocks

    def _get_etf_peer_stocks(
        self,
        symbol: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """ETF 동반 종목 조회 (ETFHolding 모델 기반)"""
        from serverless.services.theme_matching_service import get_theme_matching_service

        try:
            theme_service = get_theme_matching_service()
            peers = theme_service.get_etf_peers(symbol, limit=limit)
        except Exception as e:
            logger.warning(f"ETF peers 조회 실패: {e}")
            return []

        stocks = []
        for peer in peers:
            target_symbol = peer['symbol']
            profile = self.relationship_service.get_target_profile(target_symbol)
            if not profile:
                continue

            stocks.append({
                "symbol": target_symbol,
                "company_name": profile.get('company_name', target_symbol),
                "strength": min(1.0, peer.get('total_weight', 0) / 20.0),
                "current_price": profile.get('price'),
                "change_percent": profile.get('changes_percentage'),
                "market_cap": profile.get('market_cap'),
                "sector": profile.get('sector'),
                "industry": profile.get('industry'),
                "relationship_context": {
                    "etfs_in_common": peer.get('etfs_in_common', []),
                    "reason": peer.get('reason', ''),
                },
                "data_source": "postgres",
                "tags": [
                    {
                        "type": "ETF_PEER",
                        "label": "ETF 동반",
                        "detail": peer.get('reason', ''),
                    }
                ] + self._get_stock_tags(symbol, target_symbol),
            })

        return stocks

    def _get_theme_stocks(
        self,
        symbol: str,
        theme_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """테마 종목 조회 (ThemeMatch 모델 기반)"""
        # 같은 테마의 종목들을 조회 (자기 자신 제외)
        theme_matches = ThemeMatch.objects.filter(
            theme_id=theme_id,
            confidence__in=['high', 'medium-high']
        ).exclude(
            stock_symbol=symbol
        ).order_by('-confidence', 'stock_symbol')[:limit]

        stocks = []
        for match in theme_matches:
            target_symbol = match.stock_symbol
            profile = self.relationship_service.get_target_profile(target_symbol)
            if not profile:
                continue

            detail = ''
            if match.etf_symbol and match.weight_in_etf:
                detail = f"{match.etf_symbol} {match.weight_in_etf}%"

            stocks.append({
                "symbol": target_symbol,
                "company_name": profile.get('company_name', target_symbol),
                "strength": 0.8 if match.confidence == 'high' else 0.6,
                "current_price": profile.get('price'),
                "change_percent": profile.get('changes_percentage'),
                "market_cap": profile.get('market_cap'),
                "sector": profile.get('sector'),
                "industry": profile.get('industry'),
                "relationship_context": {
                    "theme_id": theme_id,
                    "confidence": match.confidence,
                    "source": match.source,
                },
                "data_source": "postgres",
                "tags": [
                    {
                        "type": "THEME",
                        "label": theme_id,
                        "confidence": match.confidence,
                        "detail": detail,
                    }
                ] + self._get_stock_tags(symbol, target_symbol),
            })

        return stocks

    def _get_dynamic_stocks(
        self,
        symbol: str,
        category_id: str,
        category: Dict,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        동적 카테고리 종목 조회 (Tier 1/2)
        """
        stocks = []

        try:
            if category_id == 'sector_leaders':
                # 섹터 리더 조회
                sector = category.get('sector')
                if sector:
                    sector_stocks = self.fmp_client.get_sector_stocks(sector, limit=limit + 1)
                    for stock in sector_stocks:
                        if stock.get('symbol') != symbol:
                            stocks.append(self._format_fmp_stock(stock))
                            if len(stocks) >= limit:
                                break

            elif category_id.endswith('_ecosystem'):
                # 테마 생태계 조회 (현재는 동일 산업 기반)
                # 향후 FMP Sector/Industry 데이터로 확장
                profile = self.fmp_client.get_company_profile(symbol)
                industry = profile.get('industry')

                if industry:
                    industry_stocks = self.fmp_client.get_industry_stocks(industry, limit=limit + 1)
                    for stock in industry_stocks:
                        if stock.get('symbol') != symbol:
                            stocks.append(self._format_fmp_stock(stock))
                            if len(stocks) >= limit:
                                break

        except FMPAPIError as e:
            logger.warning(f"동적 종목 조회 실패: {e}")

        return stocks

    def _get_stock_tags(self, source_symbol: str, target_symbol: str) -> List[Dict]:
        """source와 target 간 모든 관계 + 테마를 태그로 수집"""
        tags = []

        # 1. StockRelationship에서 모든 관계 타입
        rels = StockRelationship.objects.filter(
            source_symbol=source_symbol, target_symbol=target_symbol
        )
        for rel in rels:
            tag: Dict[str, Any] = {
                "type": rel.relationship_type,
                "label": rel.get_relationship_type_display(),
            }
            ctx = rel.context or {}
            if rel.relationship_type == 'CO_MENTIONED' and ctx.get('mention_count'):
                tag["detail"] = f"뉴스 {ctx['mention_count']}건"
            elif rel.relationship_type in ('SUPPLIED_BY', 'CUSTOMER_OF') and ctx.get('revenue_percent'):
                tag["detail"] = f"매출 {ctx['revenue_percent']}%"
            elif rel.relationship_type == 'ACQUIRED' and ctx.get('deal_value'):
                tag["detail"] = ctx['deal_value']
            elif rel.relationship_type == 'HELD_BY_SAME_FUND' and ctx.get('shared_count'):
                tag["detail"] = f"공유 펀드 {ctx['shared_count']}개"
            elif rel.relationship_type == 'SAME_REGULATION' and ctx.get('category_name'):
                tag["detail"] = ctx['category_name']
            elif rel.relationship_type == 'PATENT_CITED' and ctx.get('citation_count'):
                tag["detail"] = f"인용 {ctx['citation_count']}건"
            tags.append(tag)

            # Phase 6: 관계 키워드 태그 추가
            if ctx.get('keywords'):
                for keyword in ctx['keywords'][:3]:
                    tags.append({
                        "type": "KEYWORD",
                        "label": keyword,
                    })

        # 2. ThemeMatch에서 테마 태그 (high/medium-high만)
        themes = ThemeMatch.objects.filter(
            stock_symbol=target_symbol,
            confidence__in=['high', 'medium-high']
        ).order_by('-confidence')[:5]
        for theme in themes:
            tag = {
                "type": "THEME",
                "label": theme.theme_id,
                "confidence": theme.confidence,
            }
            if theme.etf_symbol and theme.weight_in_etf:
                tag["detail"] = f"{theme.etf_symbol} {theme.weight_in_etf}%"
            tags.append(tag)

        return tags

    def _format_fmp_stock(self, stock: Dict) -> Dict[str, Any]:
        """FMP 종목 데이터 포맷팅"""
        return {
            "symbol": stock.get('symbol'),
            "company_name": stock.get('companyName', stock.get('name')),
            "strength": 0.5,  # 동적 조회는 기본 강도
            "current_price": stock.get('price'),
            "change_percent": stock.get('changesPercentage'),
            "market_cap": stock.get('marketCap'),
            "sector": stock.get('sector'),
            "industry": stock.get('industry'),
            "tags": [],
        }

    def _generate_insights(
        self,
        symbol: str,
        category: Dict,
        stocks: List[Dict]
    ) -> str:
        """
        AI 인사이트 생성 (현재는 규칙 기반, 향후 LLM 연동)
        """
        category_name = category.get('name', category.get('id', ''))
        stock_count = len(stocks)

        if stock_count == 0:
            return f"{symbol}의 {category_name} 데이터를 찾을 수 없습니다."

        # 상위 3개 종목 이름
        top_names = [s.get('company_name', s.get('symbol', ''))[:20] for s in stocks[:3]]

        # 평균 변동률
        changes = [s.get('change_percent', 0) for s in stocks if s.get('change_percent') is not None]
        avg_change = sum(changes) / len(changes) if changes else 0

        trend = "상승" if avg_change > 0 else "하락" if avg_change < 0 else "보합"

        insights = (
            f"{symbol}의 {category_name} 카테고리에서 {stock_count}개 종목을 발견했습니다. "
            f"{', '.join(top_names)} 등이 포함되며, "
            f"오늘 평균 {abs(avg_change):.1f}% {trend}세를 보이고 있습니다."
        )

        return insights

    def _generate_follow_up_questions(
        self,
        symbol: str,
        category: Dict
    ) -> List[str]:
        """
        후속 질문 생성
        """
        category_id = category.get('id', '')
        category_name = category.get('name', '')

        questions = []

        if category_id == 'peer':
            questions = [
                f"{symbol}와 경쟁사들의 밸류에이션 비교가 궁금하신가요?",
                f"{symbol}의 시장 점유율 추이를 확인해 볼까요?",
            ]
        elif category_id == 'same_industry':
            questions = [
                f"이 산업의 성장 전망이 궁금하신가요?",
                f"산업 내 소형주/중형주도 확인해 볼까요?",
            ]
        elif category_id == 'co_mentioned':
            questions = [
                f"최근 관련 뉴스의 감성 분석이 궁금하신가요?",
                f"어떤 이슈로 함께 언급되는지 확인해 볼까요?",
            ]
        elif 'ecosystem' in category_id:
            questions = [
                f"{category_name} 내 다른 투자 기회를 찾아볼까요?",
                f"이 생태계의 핵심 트렌드가 궁금하신가요?",
            ]
        else:
            questions = [
                f"{category_name} 관련 더 많은 종목을 보여드릴까요?",
            ]

        return questions[:2]  # 최대 2개

    def trigger_sync(self, symbol: str, sync_neo4j: bool = True) -> Dict[str, int]:
        """
        종목 관계 동기화 트리거 (PostgreSQL + Neo4j)

        Args:
            symbol: 종목 심볼
            sync_neo4j: Neo4j 동기화 여부 (기본값: True)

        Returns:
            {
                'peer_count': 10,
                'industry_count': 15,
                'co_mentioned_count': 5,
                'neo4j_synced': 25,
                'neo4j_failed': 0
            }
        """
        symbol = symbol.upper()

        # PostgreSQL 동기화
        result = self.relationship_service.sync_all(symbol)

        # Neo4j 동기화 (옵션)
        if sync_neo4j:
            try:
                from serverless.services.neo4j_chain_sight_service import Neo4jChainSightService

                neo4j_service = Neo4jChainSightService()
                if neo4j_service.is_available():
                    neo4j_result = neo4j_service.sync_from_postgres(symbol)
                    result['neo4j_synced'] = neo4j_result.get('synced', 0)
                    result['neo4j_failed'] = neo4j_result.get('failed', 0)
                    logger.info(f"Neo4j 동기화 완료: {symbol} -> {neo4j_result}")
                else:
                    logger.debug(f"Neo4j 사용 불가, PostgreSQL만 동기화됨: {symbol}")
            except Exception as e:
                logger.warning(f"Neo4j 동기화 실패 (PostgreSQL은 성공): {e}")
                result['neo4j_synced'] = 0
                result['neo4j_failed'] = -1  # 에러 표시

        return result
