"""Tests for marketpulse.calculators.concentration."""
from __future__ import annotations

from decimal import Decimal

import pytest

from marketpulse.calculators import concentration as conc
from marketpulse.fetchers.fmp_weights import HoldingRow


def _h(symbol, weight, rank=0):
    return HoldingRow(symbol=symbol, name=symbol, weight=Decimal(str(weight)),
                      shares=None, rank=rank)


class TestComputeMetrics:
    def test_basic_top5_top10(self):
        holdings = [_h(f'T{i}', '0.05') for i in range(5)] + \
                   [_h(f'T{i}', '0.03') for i in range(5, 10)]
        m = conc.compute_metrics(holdings)
        assert m.top5_weight == Decimal('0.2500')
        assert m.top10_weight == Decimal('0.4000')

    def test_top5_le_top10_le_one(self):
        holdings = [_h(f'T{i}', '0.07') for i in range(20)]
        m = conc.compute_metrics(holdings)
        assert m.top10_weight <= Decimal('1.0')
        assert m.top5_weight <= m.top10_weight

    def test_normalization_when_sum_exceeds_1(self):
        holdings = [_h(f'T{i}', '0.10') for i in range(20)]
        m = conc.compute_metrics(holdings)
        assert m.top5_weight == Decimal('0.2500')
        assert m.top10_weight == Decimal('0.5000')

    def test_hhi_in_zero_one(self):
        holdings = [_h('A', '1.0')]
        m = conc.compute_metrics(holdings)
        assert m.hhi == Decimal('1.000000')

    def test_sorted_descending(self):
        holdings = [_h('SMALL', '0.02'), _h('BIG', '0.10'), _h('MID', '0.05')]
        m = conc.compute_metrics(holdings)
        assert m.top_holdings[0]['symbol'] == 'BIG'
        assert m.top_holdings[1]['symbol'] == 'MID'
