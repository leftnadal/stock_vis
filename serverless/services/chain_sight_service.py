"""
Chain Sight DNA 서비스

스크리너 결과에서 연관 종목을 발견하는 시스템.
3가지 방식으로 관련 종목을 찾습니다:
1. 섹터 피어 (같은 섹터의 유사 종목)
2. 펀더멘탈 유사 (PER, ROE, 시가총액 유사)
3. AI 추천 (LLM 기반 관계 설명) - Optional
"""
import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal

from django.core.cache import cache

from serverless.services.fmp_client import FMPClient, FMPAPIError


logger = logging.getLogger(__name__)


class ChainSightService:
    """
    연관 종목 발견 시스템 - Chain Sight DNA

    스크리너 결과에서 관련 종목을 3가지 방식으로 찾음:
    1. 섹터 피어 (같은 섹터의 유사 종목)
    2. 펀더멘탈 유사 (PER, ROE, 시가총액 유사)
    3. AI 추천 (LLM 기반 관계 설명)

    Usage:
        service = ChainSightService()
        chains = service.find_related_chains(
            filtered_symbols=['AAPL', 'MSFT'],
            filters_applied={'pe_ratio_max': 20, 'roe_min': 15}
        )
    """

    # 펀더멘탈 유사도 허용 범위 (±50% - 더 넓은 범위로 다양한 종목 발견)
    FUNDAMENTAL_SIMILARITY_RANGE = 0.50

    # 최대 연관 종목 수 (각 카테고리별)
    MAX_CHAINS_PER_CATEGORY = 5

    # 캐시 TTL
    CACHE_TTL = 3600  # 1시간

    def __init__(self):
        self.fmp_client = FMPClient()

    def find_related_chains(
        self,
        filtered_symbols: List[str],
        filters_applied: Dict[str, Any],
        limit: int = 10,
        use_ai: bool = False
    ) -> Dict[str, Any]:
        """
        필터링된 종목들의 연관 종목 찾기

        Args:
            filtered_symbols: 스크리너 결과 종목 심볼 리스트
            filters_applied: 적용된 필터 조건
            limit: 각 카테고리별 최대 결과 수
            use_ai: AI 인사이트 생성 여부 (선택)

        Returns:
            {
                "sector_peers": [
                    {
                        "symbol": "MSFT",
                        "company_name": "Microsoft Corporation",
                        "reason": "동일 Technology 섹터 고ROE 기업",
                        "similarity": 0.85,
                        "metrics": {...}
                    }
                ],
                "fundamental_similar": [
                    {
                        "symbol": "GOOGL",
                        "company_name": "Alphabet Inc.",
                        "reason": "유사 PER/ROE 프로필",
                        "similarity": 0.72,
                        "metrics": {...}
                    }
                ],
                "ai_insights": "이 종목들은 AI 반도체 수요 증가의 수혜 기업입니다...",
                "chains_count": 10,
                "metadata": {
                    "original_count": 2,
                    "filters": {...},
                    "computation_time_ms": 150
                }
            }
        """
        import time
        start_time = time.time()

        logger.info(f"Chain Sight DNA 분석 시작: {len(filtered_symbols)}개 종목")

        # 캐시 확인
        cache_key = self._get_cache_key(filtered_symbols, filters_applied)
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 HIT: {cache_key}")
            return cached

        # 원본 종목들의 메트릭 수집
        original_stocks = self._fetch_stock_metrics(filtered_symbols)

        if not original_stocks:
            logger.warning("원본 종목 메트릭 조회 실패")
            return self._empty_result(filtered_symbols, filters_applied)

        # 1. 섹터 피어 찾기
        sector_peers = self._analyze_sector_peers(
            original_stocks=original_stocks,
            filters_applied=filters_applied,
            limit=min(limit, self.MAX_CHAINS_PER_CATEGORY)
        )

        # 섹터 피어 심볼 수집 (중복 제거용)
        sector_peer_symbols = set(peer['symbol'] for peer in sector_peers)

        # 2. 펀더멘탈 유사 종목 찾기 (섹터 피어와 중복 제거)
        fundamental_similar = self._find_fundamentally_similar(
            original_stocks=original_stocks,
            filters_applied=filters_applied,
            limit=min(limit, self.MAX_CHAINS_PER_CATEGORY),
            exclude_symbols=sector_peer_symbols
        )

        # 3. AI 인사이트 (옵션)
        ai_insights = None
        if use_ai:
            ai_insights = self._generate_ai_insights(
                original_stocks=original_stocks,
                sector_peers=sector_peers,
                fundamental_similar=fundamental_similar
            )

        # 결과 조합
        computation_time = int((time.time() - start_time) * 1000)

        result = {
            "sector_peers": sector_peers,
            "fundamental_similar": fundamental_similar,
            "ai_insights": ai_insights,
            "chains_count": len(sector_peers) + len(fundamental_similar),
            "metadata": {
                "original_count": len(filtered_symbols),
                "filters": filters_applied,
                "computation_time_ms": computation_time,
                "use_ai": use_ai
            }
        }

        # 캐시 저장
        cache.set(cache_key, result, self.CACHE_TTL)

        logger.info(
            f"✅ Chain Sight DNA 완료: "
            f"섹터 피어 {len(sector_peers)}개, "
            f"펀더멘탈 유사 {len(fundamental_similar)}개, "
            f"소요시간 {computation_time}ms"
        )

        return result

    # ========================================
    # Private Methods
    # ========================================

    def _fetch_stock_metrics(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        종목들의 메트릭 조회 (FMP API)

        Returns:
            [
                {
                    "symbol": "AAPL",
                    "companyName": "Apple Inc.",
                    "sector": "Technology",
                    "industry": "Consumer Electronics",
                    "marketCap": 3000000000000,
                    "pe": 25.5,
                    "roe": 150.0,
                    ...
                }
            ]
        """
        if not symbols:
            return []

        stocks = []

        for symbol in symbols:
            try:
                # FMP Profile API 사용 (섹터/산업 정보 포함)
                profile = self.fmp_client.get_company_profile(symbol.upper())

                if profile:
                    stocks.append(profile)

            except FMPAPIError as e:
                logger.warning(f"종목 메트릭 조회 실패 {symbol}: {e}")
                continue

        return stocks

    def _is_etf(self, stock: Dict) -> bool:
        """
        ETF 여부 확인

        Args:
            stock: 종목 데이터

        Returns:
            ETF이면 True
        """
        # FMP API에서 isEtf 필드 확인
        if stock.get('isEtf') is True:
            return True

        # isFund 필드도 확인
        if stock.get('isFund') is True:
            return True

        # 심볼 패턴으로 ETF 추정 (보조 수단)
        symbol = stock.get('symbol', '')
        etf_indicators = ['ETF', 'FUND', 'TRUST']
        company_name = stock.get('companyName', stock.get('name', '')).upper()

        for indicator in etf_indicators:
            if indicator in company_name:
                return True

        return False

    def _analyze_sector_peers(
        self,
        original_stocks: List[Dict],
        filters_applied: Dict,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        섹터 피어 분석

        같은 섹터에서 필터 조건에 맞지만 결과에 없는 종목을 찾습니다.

        Returns:
            [
                {
                    "symbol": "MSFT",
                    "company_name": "Microsoft Corporation",
                    "reason": "동일 Technology 섹터 고ROE 기업",
                    "similarity": 0.85,
                    "metrics": {
                        "sector": "Technology",
                        "pe": 28.0,
                        "roe": 45.0,
                        "market_cap": 2500000000000
                    }
                }
            ]
        """
        if not original_stocks:
            return []

        # 원본 종목들의 섹터 추출
        sectors = set(stock.get('sector') for stock in original_stocks if stock.get('sector'))

        if not sectors:
            logger.warning("섹터 정보 없음")
            return []

        # 원본 종목 심볼 (제외용)
        original_symbols = set(stock.get('symbol') for stock in original_stocks)

        # 각 섹터별로 종목 조회
        peers = []

        for sector in sectors:
            try:
                # FMP API: 섹터별 종목 조회
                # 참고: /stable/company-screener 엔드포인트 사용
                sector_stocks = self._fetch_sector_stocks(sector, filters_applied)

                for stock in sector_stocks:
                    # 원본 종목 제외
                    if stock.get('symbol') in original_symbols:
                        continue

                    # ETF 제외
                    if self._is_etf(stock):
                        continue

                    # 유사도 계산 (펀더멘탈 기반)
                    similarity = self._calculate_peer_similarity(stock, original_stocks)

                    peers.append({
                        "symbol": stock.get('symbol'),
                        "company_name": stock.get('companyName', stock.get('name')),
                        "reason": f"동일 {sector} 섹터 유사 기업",
                        "similarity": round(similarity, 2),
                        "metrics": {
                            "sector": stock.get('sector'),
                            "industry": stock.get('industry'),
                            "pe": stock.get('pe'),
                            "roe": stock.get('roe'),
                            "market_cap": stock.get('marketCap')
                        }
                    })

            except FMPAPIError as e:
                logger.warning(f"섹터 피어 조회 실패 {sector}: {e}")
                continue

        # 유사도 높은 순으로 정렬 후 limit 적용
        peers = sorted(peers, key=lambda x: x['similarity'], reverse=True)

        return peers[:limit]

    def _find_fundamentally_similar(
        self,
        original_stocks: List[Dict],
        filters_applied: Dict,
        limit: int,
        exclude_symbols: Optional[set] = None
    ) -> List[Dict[str, Any]]:
        """
        펀더멘탈 유사 종목 찾기

        평균 PER, ROE와 ±20% 범위 내 종목을 찾습니다.

        Args:
            original_stocks: 원본 종목 리스트
            filters_applied: 필터 조건
            limit: 최대 반환 수
            exclude_symbols: 제외할 심볼 셋 (섹터 피어와 중복 방지용)

        Returns:
            [
                {
                    "symbol": "GOOGL",
                    "company_name": "Alphabet Inc.",
                    "reason": "유사 PER/ROE 프로필",
                    "similarity": 0.72,
                    "metrics": {...}
                }
            ]
        """
        if not original_stocks:
            return []

        # 원본 종목들의 평균 펀더멘탈 계산
        avg_metrics = self._calculate_average_metrics(original_stocks)

        if not avg_metrics:
            logger.warning("평균 메트릭 계산 실패")
            return []

        # 원본 종목 심볼 (제외용)
        original_symbols = set(stock.get('symbol') for stock in original_stocks)

        # 섹터 피어 심볼도 제외
        if exclude_symbols:
            original_symbols = original_symbols | exclude_symbols

        # 원본 종목들의 섹터 추출 (다른 섹터에서 검색하기 위해)
        original_sectors = set(stock.get('sector') for stock in original_stocks if stock.get('sector'))

        # 유사 종목 조회 (다른 섹터에서 유사 펀더멘탈 찾기)
        similar_stocks = self._fetch_similar_stocks(
            avg_metrics,
            filters_applied,
            exclude_sectors=original_sectors  # 섹터 피어와 다른 섹터에서 검색
        )

        results = []

        for stock in similar_stocks:
            # 원본 종목 제외
            if stock.get('symbol') in original_symbols:
                continue

            # ETF 제외
            if self._is_etf(stock):
                continue

            # 펀더멘탈 유사도 계산
            similarity = self._calculate_fundamental_similarity(stock, avg_metrics)

            # 유사도 임계값 (0.3 이상 - 다른 섹터에서 유사 펀더멘탈 발견을 위해 낮춤)
            if similarity < 0.3:
                continue

            results.append({
                "symbol": stock.get('symbol'),
                "company_name": stock.get('companyName', stock.get('name')),
                "reason": f"유사 PER/ROE/시가총액 프로필 (유사도 {int(similarity * 100)}%)",
                "similarity": round(similarity, 2),
                "metrics": {
                    "sector": stock.get('sector'),
                    "pe": stock.get('pe'),
                    "roe": stock.get('roe'),
                    "market_cap": stock.get('marketCap'),
                    "profit_margin": stock.get('grossProfitMargin')
                }
            })

        # 유사도 높은 순으로 정렬 후 limit 적용
        results = sorted(results, key=lambda x: x['similarity'], reverse=True)

        return results[:limit]

    def _generate_ai_insights(
        self,
        original_stocks: List[Dict],
        sector_peers: List[Dict],
        fundamental_similar: List[Dict]
    ) -> Optional[str]:
        """
        AI 인사이트 생성 (LLM 기반)

        Note: 이 기능은 옵션입니다. LLM 호출 실패 시 None 반환.

        Returns:
            "이 종목들은 AI 반도체 수요 증가의 수혜 기업으로, 높은 ROE와 ..."
            또는 None
        """
        try:
            # TODO: Gemini LLM 호출 (serverless.services.keyword_generator_v2 참고)
            # 현재는 기본 메시지 반환

            sectors = set(stock.get('sector') for stock in original_stocks if stock.get('sector'))
            avg_pe = sum(stock.get('pe', 0) for stock in original_stocks) / len(original_stocks) if original_stocks else 0
            avg_roe = sum(stock.get('roe', 0) for stock in original_stocks) / len(original_stocks) if original_stocks else 0

            insights = (
                f"이 종목 그룹은 주로 {', '.join(sectors)} 섹터에 속하며, "
                f"평균 PER {avg_pe:.1f}, ROE {avg_roe:.1f}%로 "
                f"{'성장성' if avg_pe > 20 else '밸류'} 투자 성향을 보입니다. "
                f"연관 종목 {len(sector_peers) + len(fundamental_similar)}개가 유사한 특성을 공유합니다."
            )

            return insights

        except Exception as e:
            logger.warning(f"AI 인사이트 생성 실패: {e}")
            return None

    def _fetch_sector_stocks(
        self,
        sector: str,
        filters_applied: Dict
    ) -> List[Dict]:
        """
        특정 섹터의 종목 조회

        Args:
            sector: 섹터 이름 (예: "Technology")
            filters_applied: 필터 조건

        Returns:
            종목 리스트
        """
        try:
            # FMP API: /stable/company-screener
            params = {
                'sector': sector,
                'limit': 50,  # 섹터당 최대 50개
                'isEtf': 'false',  # ETF 제외
                'isFund': 'false',  # 펀드 제외
            }

            # 필터 조건 추가
            if 'market_cap_min' in filters_applied:
                params['marketCapMoreThan'] = filters_applied['market_cap_min']
            if 'market_cap_max' in filters_applied:
                params['marketCapLowerThan'] = filters_applied['market_cap_max']

            endpoint = '/stable/company-screener'
            data = self.fmp_client._make_request(endpoint, params)

            return data if isinstance(data, list) else []

        except FMPAPIError as e:
            logger.warning(f"섹터 종목 조회 실패 {sector}: {e}")
            return []

    def _fetch_similar_stocks(
        self,
        avg_metrics: Dict[str, float],
        filters_applied: Dict,
        exclude_sectors: Optional[set] = None
    ) -> List[Dict]:
        """
        평균 메트릭과 유사한 종목 조회

        Args:
            avg_metrics: 평균 펀더멘탈 메트릭
            filters_applied: 필터 조건
            exclude_sectors: 제외할 섹터 셋 (섹터 피어와 다른 종목을 찾기 위해)

        Returns:
            종목 리스트
        """
        all_results = []

        # 여러 시가총액 범위로 검색하여 다양한 종목 확보
        market_cap_ranges = []

        if avg_metrics.get('market_cap'):
            base_mc = avg_metrics['market_cap']
            # 범위 1: 평균 ±50%
            market_cap_ranges.append({
                'min': int(base_mc * 0.5),
                'max': int(base_mc * 1.5)
            })
            # 범위 2: 평균보다 작은 종목 (50% ~ 100%)
            market_cap_ranges.append({
                'min': int(base_mc * 0.3),
                'max': int(base_mc * 0.7)
            })
        else:
            # 기본 범위: 대형주 (100B ~ 500B)
            market_cap_ranges.append({
                'min': 10_000_000_000,  # 10B
                'max': 500_000_000_000  # 500B
            })

        for mc_range in market_cap_ranges:
            try:
                params = {
                    'limit': 50,
                    'isEtf': 'false',
                    'isFund': 'false',
                    'marketCapMoreThan': mc_range['min'],
                    'marketCapLowerThan': mc_range['max'],
                }

                endpoint = '/stable/company-screener'
                data = self.fmp_client._make_request(endpoint, params)

                if isinstance(data, list):
                    # 제외할 섹터 필터링 (다른 섹터에서 유사 펀더멘탈 찾기)
                    if exclude_sectors:
                        data = [
                            stock for stock in data
                            if stock.get('sector') not in exclude_sectors
                        ]
                    all_results.extend(data)

            except FMPAPIError as e:
                logger.warning(f"유사 종목 조회 실패: {e}")
                continue

        # 중복 제거
        seen_symbols = set()
        unique_results = []
        for stock in all_results:
            symbol = stock.get('symbol')
            if symbol and symbol not in seen_symbols:
                seen_symbols.add(symbol)
                unique_results.append(stock)

        return unique_results

    def _calculate_average_metrics(self, stocks: List[Dict]) -> Dict[str, float]:
        """
        종목들의 평균 펀더멘탈 계산

        Returns:
            {
                "market_cap": 2500000000000,
                "pe": 25.5,
                "roe": 35.0,
                "profit_margin": 20.0
            }
        """
        if not stocks:
            return {}

        metrics = {
            'market_cap': [],
            'pe': [],
            'roe': [],
            'profit_margin': []
        }

        for stock in stocks:
            if stock.get('marketCap'):
                metrics['market_cap'].append(float(stock['marketCap']))
            if stock.get('pe'):
                metrics['pe'].append(float(stock['pe']))
            if stock.get('roe'):
                metrics['roe'].append(float(stock['roe']))
            if stock.get('grossProfitMargin'):
                metrics['profit_margin'].append(float(stock['grossProfitMargin']))

        # 평균 계산
        avg = {}
        for key, values in metrics.items():
            if values:
                avg[key] = sum(values) / len(values)

        return avg

    def _calculate_peer_similarity(
        self,
        stock: Dict,
        original_stocks: List[Dict]
    ) -> float:
        """
        섹터 피어 유사도 계산

        Args:
            stock: 비교 대상 종목
            original_stocks: 원본 종목 리스트

        Returns:
            유사도 (0.0 ~ 1.0)
        """
        # 원본 종목들의 평균 메트릭
        avg_metrics = self._calculate_average_metrics(original_stocks)

        if not avg_metrics:
            return 0.5  # 기본값

        return self._calculate_fundamental_similarity(stock, avg_metrics)

    def _calculate_fundamental_similarity(
        self,
        stock: Dict,
        avg_metrics: Dict[str, float]
    ) -> float:
        """
        펀더멘탈 유사도 계산

        PER, ROE, 시가총액, 이익률을 비교하여 0.0 ~ 1.0 사이 값 반환

        Args:
            stock: 비교 대상 종목
            avg_metrics: 평균 메트릭

        Returns:
            유사도 (0.0 ~ 1.0)
        """
        similarities = []

        # PER 유사도
        if avg_metrics.get('pe') and stock.get('pe'):
            pe_diff = abs(float(stock['pe']) - avg_metrics['pe']) / avg_metrics['pe']
            pe_sim = max(0, 1 - pe_diff)
            similarities.append(pe_sim)

        # ROE 유사도
        if avg_metrics.get('roe') and stock.get('roe'):
            roe_diff = abs(float(stock['roe']) - avg_metrics['roe']) / avg_metrics['roe']
            roe_sim = max(0, 1 - roe_diff)
            similarities.append(roe_sim)

        # 시가총액 유사도
        if avg_metrics.get('market_cap') and stock.get('marketCap'):
            mc_diff = abs(float(stock['marketCap']) - avg_metrics['market_cap']) / avg_metrics['market_cap']
            mc_sim = max(0, 1 - mc_diff)
            similarities.append(mc_sim)

        # 이익률 유사도
        if avg_metrics.get('profit_margin') and stock.get('grossProfitMargin'):
            pm_diff = abs(float(stock['grossProfitMargin']) - avg_metrics['profit_margin']) / avg_metrics['profit_margin']
            pm_sim = max(0, 1 - pm_diff)
            similarities.append(pm_sim)

        # 평균 유사도
        if similarities:
            return sum(similarities) / len(similarities)

        return 0.5  # 기본값

    def _get_cache_key(
        self,
        symbols: List[str],
        filters: Dict
    ) -> str:
        """캐시 키 생성"""
        symbols_str = ','.join(sorted(symbols))
        filters_str = str(sorted(filters.items()))
        return f'chain_sight:{hash(symbols_str + filters_str)}'

    def _empty_result(
        self,
        filtered_symbols: List[str],
        filters_applied: Dict
    ) -> Dict[str, Any]:
        """빈 결과 반환"""
        return {
            "sector_peers": [],
            "fundamental_similar": [],
            "ai_insights": None,
            "chains_count": 0,
            "metadata": {
                "original_count": len(filtered_symbols),
                "filters": filters_applied,
                "computation_time_ms": 0,
                "use_ai": False,
                "error": "Failed to fetch stock metrics"
            }
        }
