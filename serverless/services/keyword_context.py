"""
Market Movers 키워드 생성 컨텍스트 빌더

토큰 최적화 및 컨텍스트 구성 전략
"""

from typing import Dict, Any, List, Optional
from datetime import date
from decimal import Decimal

from ..models import MarketMover


class KeywordContextBuilder:
    """
    키워드 생성용 컨텍스트 빌더

    토큰 최적화 전략:
    1. 배치 처리 (20개 종목) vs 개별 처리 비교
    2. 필수 필드만 포함 (불필요한 데이터 제거)
    3. 수치 포맷 최적화 (소수점 2자리)
    """

    # 토큰 추정 (1 char ≈ 0.4 tokens in Korean)
    CHAR_TO_TOKEN_RATIO = 0.4

    @staticmethod
    def build_compact_context(mover: MarketMover) -> Dict[str, Any]:
        """
        압축된 컨텍스트 생성 (토큰 절약)

        Args:
            mover: MarketMover 인스턴스

        Returns:
            dict: 최소한의 필수 데이터만 포함
        """
        context = {
            'symbol': mover.symbol,
            'name': mover.company_name,
            'type': mover.mover_type,
            'price': float(mover.price) if mover.price else None,
            'chg': float(mover.change_percent) if mover.change_percent else None,
            'vol': int(mover.volume) if mover.volume else None,
        }

        # 지표 (필수)
        indicators = {}
        if mover.rvol:
            indicators['rvol'] = float(mover.rvol)
        if mover.trend_strength is not None:
            indicators['trend'] = float(mover.trend_strength)
        if mover.sector_alpha is not None:
            indicators['alpha'] = float(mover.sector_alpha)
        if mover.etf_sync_rate is not None:
            indicators['sync'] = float(mover.etf_sync_rate)
        if mover.volatility_pct is not None:
            indicators['vol_pct'] = int(mover.volatility_pct)

        if indicators:
            context['ind'] = indicators

        # 섹터 (선택)
        if mover.sector:
            context['sector'] = mover.sector

        return context

    @staticmethod
    def build_full_context(mover: MarketMover) -> Dict[str, Any]:
        """
        전체 컨텍스트 생성 (상세 분석용)

        Args:
            mover: MarketMover 인스턴스

        Returns:
            dict: 모든 필드 포함
        """
        context = {
            'symbol': mover.symbol,
            'company_name': mover.company_name,
            'mover_type': mover.mover_type,
            'rank': mover.rank,
            'price': float(mover.price) if mover.price else None,
            'change_percent': float(mover.change_percent) if mover.change_percent else None,
            'volume': int(mover.volume) if mover.volume else None,
        }

        # OHLC (선택)
        if mover.open_price and mover.high and mover.low:
            context['ohlc'] = {
                'open': float(mover.open_price),
                'high': float(mover.high),
                'low': float(mover.low),
            }

        # 섹터/산업
        if mover.sector:
            context['sector'] = mover.sector
        if mover.industry:
            context['industry'] = mover.industry

        # 지표
        indicators = {}
        if mover.rvol:
            indicators['rvol'] = float(mover.rvol)
        if mover.trend_strength is not None:
            indicators['trend_strength'] = float(mover.trend_strength)
        if mover.sector_alpha is not None:
            indicators['sector_alpha'] = float(mover.sector_alpha)
        if mover.etf_sync_rate is not None:
            indicators['etf_sync_rate'] = float(mover.etf_sync_rate)
        if mover.volatility_pct is not None:
            indicators['volatility_pct'] = int(mover.volatility_pct)

        if indicators:
            context['indicators'] = indicators

        return context

    @staticmethod
    def estimate_context_tokens(
        context: Dict[str, Any],
        include_prompt: bool = False
    ) -> int:
        """
        컨텍스트 토큰 추정

        Args:
            context: 컨텍스트 딕셔너리
            include_prompt: 프롬프트 토큰 포함 여부

        Returns:
            int: 추정 토큰 수
        """
        import json

        # JSON 문자열 변환
        context_str = json.dumps(context, ensure_ascii=False)

        # 토큰 추정 (1 char ≈ 0.4 tokens)
        context_tokens = int(len(context_str) * KeywordContextBuilder.CHAR_TO_TOKEN_RATIO)

        if include_prompt:
            # 시스템 프롬프트: 약 1000 토큰
            # 사용자 프롬프트 헤더: 약 200 토큰
            prompt_tokens = 1200
            return context_tokens + prompt_tokens

        return context_tokens

    @staticmethod
    def compare_batch_vs_individual(
        num_stocks: int,
        avg_tokens_per_stock: int = 300
    ) -> Dict[str, Any]:
        """
        배치 처리 vs 개별 처리 비용 비교

        Args:
            num_stocks: 종목 수
            avg_tokens_per_stock: 종목당 평균 토큰 수

        Returns:
            dict: 비교 결과
        """
        # 배치 처리
        # - 시스템 프롬프트 1회: 1000 토큰
        # - 배치 헤더: 200 토큰
        # - 종목 데이터: num_stocks * avg_tokens_per_stock
        # - 출력: num_stocks * 300 토큰
        batch_input = 1000 + 200 + (num_stocks * avg_tokens_per_stock)
        batch_output = num_stocks * 300
        batch_total = batch_input + batch_output

        # 개별 처리
        # - 시스템 프롬프트 * num_stocks: 1000 * num_stocks
        # - 종목 데이터 * num_stocks: 300 * num_stocks
        # - 출력 * num_stocks: 300 * num_stocks
        individual_input = (1000 + avg_tokens_per_stock) * num_stocks
        individual_output = 300 * num_stocks
        individual_total = individual_input + individual_output

        # 비용 계산 (Gemini 2.5 Flash)
        INPUT_COST_PER_1M = 0.30
        OUTPUT_COST_PER_1M = 1.20

        batch_cost = (
            (batch_input / 1_000_000) * INPUT_COST_PER_1M +
            (batch_output / 1_000_000) * OUTPUT_COST_PER_1M
        )

        individual_cost = (
            (individual_input / 1_000_000) * INPUT_COST_PER_1M +
            (individual_output / 1_000_000) * OUTPUT_COST_PER_1M
        )

        savings = individual_cost - batch_cost
        savings_percent = (savings / individual_cost) * 100 if individual_cost > 0 else 0

        return {
            'num_stocks': num_stocks,
            'batch': {
                'input_tokens': batch_input,
                'output_tokens': batch_output,
                'total_tokens': batch_total,
                'cost_usd': round(batch_cost, 6),
            },
            'individual': {
                'input_tokens': individual_input,
                'output_tokens': individual_output,
                'total_tokens': individual_total,
                'cost_usd': round(individual_cost, 6),
            },
            'savings': {
                'tokens': individual_total - batch_total,
                'cost_usd': round(savings, 6),
                'percent': round(savings_percent, 2),
            },
            'recommendation': 'batch' if num_stocks >= 5 else 'individual'
        }


class KeywordCompressor:
    """
    키워드 데이터 압축기

    데이터베이스 저장 시 토큰 절약 및 응답 속도 향상
    """

    @staticmethod
    def compress_keywords(keywords: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        키워드 리스트 압축

        Args:
            keywords: [{'text', 'category', 'confidence'}, ...]

        Returns:
            list: 압축된 키워드 리스트
        """
        compressed = []

        for kw in keywords:
            # 필수 필드만 유지
            compressed_kw = {
                't': kw['text'],  # text
                'c': kw['category'],  # category
            }

            # confidence가 0.8이 아닌 경우만 포함
            if kw.get('confidence', 0.8) != 0.8:
                compressed_kw['cf'] = kw['confidence']

            compressed.append(compressed_kw)

        return compressed

    @staticmethod
    def decompress_keywords(compressed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        압축된 키워드 리스트 복원

        Args:
            compressed: 압축된 키워드 리스트

        Returns:
            list: 원본 형식 키워드 리스트
        """
        keywords = []

        for ckw in compressed:
            keyword = {
                'text': ckw.get('t', ''),
                'category': ckw.get('c', ''),
                'confidence': ckw.get('cf', 0.8),
            }
            keywords.append(keyword)

        return keywords

    @staticmethod
    def estimate_compression_ratio(
        original: List[Dict[str, Any]]
    ) -> float:
        """
        압축률 추정

        Args:
            original: 원본 키워드 리스트

        Returns:
            float: 압축률 (0.0 ~ 1.0, 낮을수록 압축 효과 높음)
        """
        import json

        original_size = len(json.dumps(original, ensure_ascii=False))

        compressed = KeywordCompressor.compress_keywords(original)
        compressed_size = len(json.dumps(compressed, ensure_ascii=False))

        if original_size == 0:
            return 1.0

        return compressed_size / original_size


# 사용 예시
if __name__ == "__main__":
    # 배치 vs 개별 비교
    comparison = KeywordContextBuilder.compare_batch_vs_individual(
        num_stocks=20
    )

    print("=== 배치 vs 개별 처리 비용 비교 (20개 종목) ===")
    print(f"배치 처리:")
    print(f"  - 토큰: {comparison['batch']['total_tokens']:,}")
    print(f"  - 비용: ${comparison['batch']['cost_usd']:.6f}")
    print()
    print(f"개별 처리:")
    print(f"  - 토큰: {comparison['individual']['total_tokens']:,}")
    print(f"  - 비용: ${comparison['individual']['cost_usd']:.6f}")
    print()
    print(f"절약:")
    print(f"  - 토큰: {comparison['savings']['tokens']:,}")
    print(f"  - 비용: ${comparison['savings']['cost_usd']:.6f} ({comparison['savings']['percent']:.1f}%)")
    print()
    print(f"권장: {comparison['recommendation']}")
