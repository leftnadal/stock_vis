"""
SEC-PR-4: S&P 500 심볼 목록 유틸리티.
"""

from packages.shared.stocks.models import SP500Constituent


def get_sp500_symbols() -> list:
    """활성 S&P 500 종목 심볼 리스트."""
    return list(
        SP500Constituent.objects.filter(is_active=True)
        .values_list("symbol", flat=True)
        .order_by("symbol")
    )
