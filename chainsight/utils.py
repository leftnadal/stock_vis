"""
Chain Sight 유틸리티 함수
"""

from datetime import date, timedelta


def get_market_date() -> date:
    """
    미국장 EOD 기준 시장 날짜 반환.
    주말이면 직전 금요일을 반환한다.
    (공휴일은 간략 처리 — 주말만 보정)
    """
    today = date.today()
    weekday = today.weekday()  # 0=Mon ... 6=Sun
    if weekday == 5:  # Saturday
        return today - timedelta(days=1)
    if weekday == 6:  # Sunday
        return today - timedelta(days=2)
    return today


def normalize_pair(symbol_a: str, symbol_b: str) -> tuple[str, str]:
    """
    undirected 관계의 사전순 정규화.
    PEER_OF, COMPETES_WITH, CO_MENTIONED, PRICE_CORRELATED에 사용.
    항상 symbol_a < symbol_b를 보장한다.
    """
    if symbol_a <= symbol_b:
        return symbol_a, symbol_b
    return symbol_b, symbol_a
