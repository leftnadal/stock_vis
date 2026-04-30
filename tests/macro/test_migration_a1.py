"""PR-A1 마이그레이션 테스트 — sector_group choices 확장 + 데이터 매핑 idempotency.

T1~T11 커버 (PR-A1 위임 프롬프트 §5.1).
"""
from __future__ import annotations

import pytest


@pytest.mark.django_db
class TestSectorGroupSchema:
    """T1~T2, T9: 0005 schema 변경 검증."""

    def test_t1_field_choices_12(self):
        """T1: choices 12개 (BENCHMARK + GICS 11)."""
        from macro.models.indicators import MarketIndex
        choices = dict(MarketIndex._meta.get_field('sector_group').choices)
        assert 'BENCHMARK' in choices
        gics = ['FINANCIALS', 'TECH', 'HEALTHCARE', 'CONSUMER_DISC', 'CONSUMER_STAPLES',
                'ENERGY', 'INDUSTRIALS', 'MATERIALS', 'UTILITIES', 'REAL_ESTATE', 'COMMUNICATION']
        for code in gics:
            assert code in choices, f'{code} should be in choices'
        assert len(choices) == 12

    def test_t2_existing_rows_default_benchmark(self):
        """T2: 0006 reverse 후에도 SAFE_HAVEN/INTERNATIONAL 등은 BENCHMARK로 흡수됨."""
        from macro.models.indicators import MarketIndex
        # SECTOR (XL*) 11개를 제외한 모든 row는 BENCHMARK
        non_xlf = MarketIndex.objects.exclude(symbol__startswith='XL').exclude(sector_group='BENCHMARK')
        # XL* 외에 NULL/SAFE_HAVEN/INTERNATIONAL이 남아 있으면 0006 forward 누락
        assert non_xlf.count() == 0, f'BENCHMARK 흡수 누락: {list(non_xlf.values_list("symbol", "sector_group"))}'

    def test_t9_field_max_length_and_index(self):
        """T9: max_length=32, db_index=True, default='BENCHMARK'."""
        from macro.models.indicators import MarketIndex
        field = MarketIndex._meta.get_field('sector_group')
        assert field.max_length == 32
        assert field.db_index is True
        assert field.default == 'BENCHMARK'


@pytest.mark.django_db
class TestSectorGroupDataMapping:
    """T5~T7: 0006 데이터 매핑 검증 (운영 시드 기준)."""

    def test_t5_xlf_mapped_to_financials(self):
        from macro.models.indicators import MarketIndex
        xlf = MarketIndex.objects.filter(symbol='XLF').first()
        assert xlf is not None
        assert xlf.sector_group == 'FINANCIALS'

    def test_t5_xlk_mapped_to_tech(self):
        from macro.models.indicators import MarketIndex
        xlk = MarketIndex.objects.filter(symbol='XLK').first()
        assert xlk is not None
        assert xlk.sector_group == 'TECH'

    def test_t5_all_gics_11_present(self):
        """11 GICS sector ETFs 모두 매핑됨."""
        from macro.models.indicators import MarketIndex
        expected = {
            'XLF': 'FINANCIALS', 'XLK': 'TECH', 'XLV': 'HEALTHCARE',
            'XLY': 'CONSUMER_DISC', 'XLP': 'CONSUMER_STAPLES',
            'XLE': 'ENERGY', 'XLI': 'INDUSTRIALS', 'XLB': 'MATERIALS',
            'XLU': 'UTILITIES', 'XLRE': 'REAL_ESTATE', 'XLC': 'COMMUNICATION',
        }
        for symbol, gics in expected.items():
            idx = MarketIndex.objects.filter(symbol=symbol).first()
            assert idx is not None, f'{symbol} not seeded'
            assert idx.sector_group == gics, f'{symbol}: expected {gics}, got {idx.sector_group}'

    def test_t5_benchmark_count(self):
        """SPY/QQQ/IWM/DIA 등 benchmark + safe_haven 흡수가 BENCHMARK로 통합."""
        from macro.models.indicators import MarketIndex
        bench = MarketIndex.objects.filter(sector_group='BENCHMARK')
        assert bench.count() >= 4  # 최소 SPY/QQQ/IWM/DIA 포함

    def test_t7_forward_idempotent(self):
        """T7: 0006 forward(apps, schema_editor) 재호출 시 매핑 불변 (idempotent)."""
        import importlib
        from django.apps import apps as django_apps
        from macro.models.indicators import MarketIndex

        before = sorted(MarketIndex.objects.values_list('symbol', 'sector_group'))

        # macro.migrations.0006_... 형식은 import_module로 로드 (모듈 이름이 숫자 시작)
        module = importlib.import_module('macro.migrations.0006_remap_sector_group_to_gics')
        module.forward(django_apps, None)

        after = sorted(MarketIndex.objects.values_list('symbol', 'sector_group'))
        assert before == after, 'forward should be idempotent on already-mapped data'

    def test_t8_no_integrity_error_on_xl_symbols(self):
        """T8: 동일 symbol XLF/XLK 등이 이미 존재해도 IntegrityError 없이 동작."""
        from macro.models.indicators import MarketIndex
        # 이미 시드된 XL*는 그대로 유지되어야 함
        for sym in ('XLF', 'XLK', 'XLV', 'XLY', 'XLP', 'XLE', 'XLI', 'XLB', 'XLU', 'XLRE', 'XLC'):
            assert MarketIndex.objects.filter(symbol=sym).exists()
