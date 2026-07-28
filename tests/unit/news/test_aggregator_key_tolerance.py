"""NewsAggregatorService API 키 의존 분리 회귀 (S5, NEWS-AGG-TEST-ENV).

과거: __init__ 이 settings.FINNHUB_API_KEY/MARKETAUX_API_KEY 로 provider 를 **무조건**
생성 → 키 부재 격리/CI 환경에서 ValueError("... API Key not found") 로 인스턴스화 실패.
이제 키 없으면 provider=None(경고 후 건너뜀), provider 주입도 가능.
"""
import pytest

from services.news.services.aggregator import NewsAggregatorService


@pytest.mark.django_db
def test_instantiates_without_any_keys(settings):
    """키가 모두 비어도 예외 없이 인스턴스화되고 provider 는 None."""
    settings.FINNHUB_API_KEY = ""
    settings.MARKETAUX_API_KEY = ""
    settings.FMP_API_KEY = None

    agg = NewsAggregatorService()  # ValueError 나면 회귀

    assert agg.finnhub is None
    assert agg.marketaux is None
    assert agg.fmp is None
    # 수집 무관 저장 경로는 여전히 사용 가능
    assert agg._save_articles([]) == (0, 0, 0)


@pytest.mark.django_db
def test_provider_injection_overrides_settings(settings):
    """주입한 provider 는 키 유무와 무관하게 그대로 사용된다."""
    settings.FINNHUB_API_KEY = ""
    settings.MARKETAUX_API_KEY = ""

    sentinel_fin = object()
    sentinel_mkx = object()
    agg = NewsAggregatorService(finnhub=sentinel_fin, marketaux=sentinel_mkx)

    assert agg.finnhub is sentinel_fin
    assert agg.marketaux is sentinel_mkx


@pytest.mark.django_db
def test_marketaux_built_when_key_present(settings):
    """MARKETAUX_API_KEY 가 있으면 provider 가 생성된다(기존 prod 경로 보존)."""
    settings.FINNHUB_API_KEY = ""
    settings.MARKETAUX_API_KEY = "test_marketaux_key"

    agg = NewsAggregatorService()

    assert agg.marketaux is not None
    assert agg.finnhub is None
