"""Tests for thesis.tasks.eod_pipeline._apply_value_postprocess and _fetch_fmp_ttm_or_growth (audit P0 #11)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from thesis.tasks.eod_pipeline import (
    _apply_value_postprocess,
    _fetch_fmp_ttm_or_growth,
    _fetch_fmp_value,
)


class TestApplyValuePostprocess:
    def test_none_passes_through(self):
        assert _apply_value_postprocess(None, {}) is None

    def test_no_metadata_returns_value(self):
        assert _apply_value_postprocess(15.0, {}) == 15.0

    def test_inverse_for_per(self):
        # earningsYieldTTM 0.04 → PER 25
        assert _apply_value_postprocess(0.04, {'inverse': True}) == pytest.approx(25.0)

    def test_inverse_zero_returns_none(self):
        assert _apply_value_postprocess(0.0, {'inverse': True}) is None

    def test_scale_multiplier_for_roe(self):
        # ROE 0.15 → 15.0%
        assert _apply_value_postprocess(0.15, {'scale_multiplier': 100}) == pytest.approx(15.0)

    def test_inverse_then_scale(self):
        # earningsYield 0.04 → PER 25 → ×1 (scale 없음)
        v = _apply_value_postprocess(0.04, {'inverse': True})
        assert v == pytest.approx(25.0)


@pytest.mark.django_db
class TestFetchFmpTtmOrGrowth:
    def _indicator(self, name='ind'):
        m = MagicMock()
        m.name = name
        return m

    def test_ttm_metric_returns_field(self):
        client = MagicMock()
        client._make_request.return_value = [{'returnOnEquityTTM': 0.18}]
        params = {'metric': 'returnOnEquityTTM'}
        v, asof = _fetch_fmp_ttm_or_growth(client, self._indicator(), 'AAPL', params)
        assert v == 0.18
        assert asof is not None
        client._make_request.assert_called_with('/stable/key-metrics-ttm', {'symbol': 'AAPL'})

    def test_financial_growth_endpoint(self):
        client = MagicMock()
        client._make_request.return_value = [{'growthRevenue': 0.12}]
        params = {'metric': 'growthRevenue', 'endpoint': 'financial-growth'}
        v, asof = _fetch_fmp_ttm_or_growth(client, self._indicator(), 'MSFT', params)
        assert v == 0.12
        client._make_request.assert_called_with('/stable/financial-growth', {'symbol': 'MSFT'})

    def test_empty_response_returns_none(self):
        client = MagicMock()
        client._make_request.return_value = []
        params = {'metric': 'returnOnEquityTTM'}
        v, asof = _fetch_fmp_ttm_or_growth(client, self._indicator(), 'AAPL', params)
        assert v is None and asof is None

    def test_non_ttm_non_growth_returns_none(self):
        client = MagicMock()
        params = {'metric': 'price'}  # 분기 대상 아님
        v, asof = _fetch_fmp_ttm_or_growth(client, self._indicator(), 'AAPL', params)
        assert v is None and asof is None
        client._make_request.assert_not_called()


@pytest.mark.django_db
class TestFetchFmpValueIntegration:
    def _indicator(self, *, data_params, target='AAPL'):
        ind = MagicMock()
        ind.name = 'test_ind'
        ind.data_params = data_params
        thesis = MagicMock()
        thesis.target = target
        ind.thesis = thesis
        return ind

    def test_per_uses_inverse(self, settings):
        settings.FMP_API_KEY = 'test'
        ind = self._indicator(
            data_params={'metric': 'earningsYieldTTM', 'inverse': True}
        )
        with patch('packages.shared.api_request.providers.fmp.client.FMPClient') as MockClient:
            instance = MockClient.return_value
            instance._make_request.return_value = [{'earningsYieldTTM': 0.04}]
            value, _ = _fetch_fmp_value(ind)
        assert value == pytest.approx(25.0)

    def test_roe_uses_scale_multiplier(self, settings):
        settings.FMP_API_KEY = 'test'
        ind = self._indicator(
            data_params={'metric': 'returnOnEquityTTM', 'scale_multiplier': 100}
        )
        with patch('packages.shared.api_request.providers.fmp.client.FMPClient') as MockClient:
            instance = MockClient.return_value
            instance._make_request.return_value = [{'returnOnEquityTTM': 0.18}]
            value, _ = _fetch_fmp_value(ind)
        assert value == pytest.approx(18.0)

    def test_growth_revenue_uses_endpoint(self, settings):
        settings.FMP_API_KEY = 'test'
        ind = self._indicator(
            data_params={
                'metric': 'growthRevenue',
                'endpoint': 'financial-growth',
                'scale_multiplier': 100,
            },
        )
        with patch('packages.shared.api_request.providers.fmp.client.FMPClient') as MockClient:
            instance = MockClient.return_value
            instance._make_request.return_value = [{'growthRevenue': 0.12}]
            value, _ = _fetch_fmp_value(ind)
        assert value == pytest.approx(12.0)
