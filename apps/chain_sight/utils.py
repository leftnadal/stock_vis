"""
Chain Sight 유틸리티 함수
"""

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

NYSE_TZ = ZoneInfo("America/New_York")

_self_loop_logger = logging.getLogger(__name__)


def skip_self_loop(symbol_a, symbol_b, relation_type="", source="", logger=None):
    """자기루프(symbol_a == symbol_b) 쌍이면 구조화 경고 로그 후 True 반환.

    호출부는 ``if skip_self_loop(...): continue`` 로 배선한다.

    CoMentionEdge/RelationConfidence 의 ``SelfLoopError`` 와 동일한 a≠b 불변식을
    강제하되, 상류 배치 루프에서는 예외가 배치 전체를 중단시키므로 raise 대신
    skip+log 를 쓴다. 모델 ``save()`` 가드는 최종 방어선으로 유지되며, 이 헬퍼는
    배치가 SelfLoopError 로 크래시하지 않고 자기루프 쌍만 건너뛰도록 한다
    (MIG-BUNDLE-1 A-1: 8-K/관계 배치 상류 가드).
    """
    if symbol_a != symbol_b:
        return False
    (logger or _self_loop_logger).warning(
        "self_loop_skipped source=%s symbol=%s relation_type=%s",
        source or "?",
        symbol_a,
        relation_type or "?",
    )
    return True


def get_market_date() -> date:
    """
    미국장 EOD 기준 시장 날짜 반환.

    시스템 TZ가 아닌 America/New_York 기준 현재 날짜를 사용하여
    KST/UTC 환경에서도 NYSE 거래일과 키가 일관되도록 한다.
    주말이면 직전 금요일을 반환한다. (공휴일은 간략 처리 — 주말만 보정)
    """
    today = datetime.now(NYSE_TZ).date()
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
