"""ScopeResolver 테스트 (MON-P2, 종목 범위)."""
import pytest

from apps.monitor.services.scope_resolver import (
    ResolvedTarget,
    ScopeResolutionError,
    resolve,
)


@pytest.fixture
def aapl(db):
    from packages.shared.stocks.models import Stock

    return Stock.objects.create(symbol="AAPL", stock_name="Apple Inc.")


@pytest.mark.django_db
class TestResolveStock:
    def test_resolve_success(self, aapl):
        r = resolve("stock", "AAPL")
        assert isinstance(r, ResolvedTarget)
        assert r.scope == "stock"
        assert r.target_ref == "AAPL"
        assert "Apple" in r.label
        assert r.data_source == "stocks.DailyPrice"

    def test_normalizes_to_upper(self, aapl):
        r = resolve("stock", "  aapl ")
        assert r.target_ref == "AAPL"  # 대문자·trim 정규화 (코딩 규칙)

    def test_unknown_symbol_raises(self, db):
        with pytest.raises(ScopeResolutionError):
            resolve("stock", "NOTREAL")

    def test_empty_target_raises(self, db):
        with pytest.raises(ScopeResolutionError):
            resolve("stock", "   ")


class TestResolveUnsupported:
    def test_unsupported_scope_raises(self):
        # P2는 stock만 — 나머지는 명시적 실패 (P4~P6 확장 지점)
        for scope in ("market", "sector", "theme", "fund"):
            with pytest.raises(ScopeResolutionError):
                resolve(scope, "whatever")
