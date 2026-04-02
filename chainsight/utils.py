"""
Chain Sight 유틸리티 함수
"""


def normalize_pair(symbol_a: str, symbol_b: str) -> tuple[str, str]:
    """
    undirected 관계의 사전순 정규화.
    PEER_OF, COMPETES_WITH, CO_MENTIONED, PRICE_CORRELATED에 사용.
    항상 symbol_a < symbol_b를 보장한다.
    """
    if symbol_a <= symbol_b:
        return symbol_a, symbol_b
    return symbol_b, symbol_a
