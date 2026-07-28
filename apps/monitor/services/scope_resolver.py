"""ScopeResolver: (scope, target_ref) → 검증된 데이터 소스 참조.

P2 범위 = 종목(stock)만. 시장/섹터(P4)·테마(P5)·펀드(P6)는 후속 확장.
resolver 레지스트리(`_RESOLVERS`)에 scope별 함수를 등록하는 방식이라 확장이 격리된다.
"""
from dataclasses import dataclass

from django.core.exceptions import ObjectDoesNotExist


class ScopeResolutionError(ValueError):
    """해석 불가한 (scope, target_ref) — 미지원 scope 또는 존재하지 않는 대상."""


@dataclass(frozen=True)
class ResolvedTarget:
    scope: str
    target_ref: str  # 정규화된 참조 (종목은 대문자 심볼)
    label: str  # 표시명
    data_source: str  # 데이터 계층 키


def resolve(scope: str, target_ref: str) -> ResolvedTarget:
    """scope에 맞는 resolver로 target_ref를 검증·정규화한다."""
    resolver = _RESOLVERS.get(scope)
    if resolver is None:
        raise ScopeResolutionError(f"미지원 scope: {scope!r} (P2는 'stock'만 지원)")
    return resolver(target_ref)


def _resolve_stock(target_ref: str) -> ResolvedTarget:
    from packages.shared.stocks.models import Stock

    if not target_ref or not target_ref.strip():
        raise ScopeResolutionError("종목 심볼이 비어 있음")
    symbol = target_ref.strip().upper()
    try:
        stock = Stock.objects.get(symbol=symbol)
    except ObjectDoesNotExist:
        raise ScopeResolutionError(f"존재하지 않는 종목: {symbol}")
    return ResolvedTarget(
        scope="stock",
        target_ref=symbol,
        label=f"{stock.stock_name} ({symbol})",
        data_source="stocks.DailyPrice",
    )


_RESOLVERS = {
    "stock": _resolve_stock,
}
