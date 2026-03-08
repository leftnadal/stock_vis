"""
Provider별 sentiment 스케일 정규화

각 Provider의 sentiment 범위를 -1.0 ~ 1.0으로 통일합니다.
"""


class SentimentNormalizer:
    """Provider별 sentiment 스케일을 -1.0 ~ 1.0으로 통일"""

    @staticmethod
    def normalize(score, provider: str) -> float | None:
        """
        Provider별 sentiment 점수 정규화

        Args:
            score: 원본 sentiment 점수
            provider: Provider 이름 (alpha_vantage, marketaux, fmp, finnhub)

        Returns:
            정규화된 점수 (-1.0 ~ 1.0) 또는 None
        """
        if score is None:
            return None
        try:
            score = float(score)
        except (TypeError, ValueError):
            return None

        # Alpha Vantage: 이미 -1 ~ 1 범위
        # Marketaux: 이미 -1 ~ 1 범위
        # FMP: 확인 필요하나 대체로 -1 ~ 1
        # 모든 provider에 대해 clamp 적용
        return max(-1.0, min(1.0, score))
