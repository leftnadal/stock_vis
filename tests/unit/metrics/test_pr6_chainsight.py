"""
PR-6 chainsight 앱 모델 테스트

검증 범위:
- CompanySensitivityProfile: OneToOne, 금리/환율/규제 민감도
- CompanyGrowthStage: stage 6단계, confidence
- CompanyCapitalDNA: capital_type, trend choices
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError

from chainsight.models import (
    CompanyCapitalDNA,
    CompanyGrowthStage,
    CompanySensitivityProfile,
)

# ===== CompanySensitivityProfile =====

class TestCompanySensitivityProfile:

    @pytest.mark.django_db
    def test_create_profile(self, stock_aapl):
        profile = CompanySensitivityProfile.objects.create(
            symbol=stock_aapl,
            debt_to_equity=Decimal('1.8700'),
            net_debt=98000000000,
            interest_coverage=Decimal('29.5000'),
            debt_maturity_risk='low',
            rate_sensitivity='low',
            foreign_revenue_pct=Decimal('58.00'),
            primary_currency_exposure='EUR',
            forex_sensitivity='medium',
            beta=Decimal('1.2500'),
            beta_sector_adj=Decimal('0.9800'),
            commodity_sensitivity='low',
            sector='Technology',
            industry='Consumer Electronics',
            is_regulated_industry=False,
            regulation_type='none',
            data_source={'provider': 'calculated', 'version': 1},
        )
        assert profile.pk == 'AAPL'
        assert profile.rate_sensitivity == 'low'
        assert profile.forex_sensitivity == 'medium'

    @pytest.mark.django_db
    def test_one_to_one(self, stock_aapl):
        CompanySensitivityProfile.objects.create(symbol=stock_aapl)
        with pytest.raises(IntegrityError):
            CompanySensitivityProfile.objects.create(symbol=stock_aapl)

    @pytest.mark.django_db
    def test_regulated_industry(self, stock_msft):
        profile = CompanySensitivityProfile.objects.create(
            symbol=stock_msft,
            is_regulated_industry=True,
            regulation_type='financial',
        )
        assert profile.is_regulated_industry is True
        assert profile.regulation_type == 'financial'

    @pytest.mark.django_db
    def test_all_fields_nullable(self, stock_aapl):
        """수치 필드 전부 null 가능 (데이터 부족 시)"""
        profile = CompanySensitivityProfile.objects.create(symbol=stock_aapl)
        assert profile.debt_to_equity is None
        assert profile.net_debt is None
        assert profile.beta is None

    @pytest.mark.django_db
    def test_reverse_relation(self, stock_aapl):
        CompanySensitivityProfile.objects.create(
            symbol=stock_aapl, rate_sensitivity='high',
        )
        assert stock_aapl.sensitivity_profile.rate_sensitivity == 'high'

    @pytest.mark.django_db
    def test_str_representation(self, stock_aapl):
        profile = CompanySensitivityProfile.objects.create(
            symbol=stock_aapl, debt_maturity_risk='medium', beta=Decimal('1.15'),
        )
        s = str(profile)
        assert 'AAPL' in s


# ===== CompanyGrowthStage =====

class TestCompanyGrowthStage:

    @pytest.mark.django_db
    def test_create_growth_stage(self, stock_aapl):
        gs = CompanyGrowthStage.objects.create(
            symbol=stock_aapl,
            stage='mature',
            revenue_cagr_3y=Decimal('0.0800'),
            revenue_cagr_5y=Decimal('0.1100'),
            revenue_acceleration=Decimal('-0.0300'),
            net_income_positive_years=10,
            net_income_turned_positive=False,
            fcf_trend='stable',
            fcf_positive_years=10,
            dividend_started=True,
            dividend_years=12,
            confidence='high',
        )
        assert gs.pk == 'AAPL'
        assert gs.stage == 'mature'
        assert gs.confidence == 'high'

    @pytest.mark.django_db
    def test_one_to_one(self, stock_aapl):
        CompanyGrowthStage.objects.create(symbol=stock_aapl)
        with pytest.raises(IntegrityError):
            CompanyGrowthStage.objects.create(symbol=stock_aapl)

    @pytest.mark.django_db
    @pytest.mark.parametrize('stage', [
        'early_growth', 'accelerating', 'mature',
        'cash_cow', 'turnaround', 'declining',
    ])
    def test_all_stage_choices(self, stock_aapl, stage):
        """6개 stage 모두 유효"""
        # 매번 새로 생성하기 위해 기존 삭제
        CompanyGrowthStage.objects.filter(symbol=stock_aapl).delete()
        gs = CompanyGrowthStage.objects.create(symbol=stock_aapl, stage=stage)
        gs.refresh_from_db()
        assert gs.stage == stage

    @pytest.mark.django_db
    def test_default_stage_is_mature(self, stock_aapl):
        gs = CompanyGrowthStage.objects.create(symbol=stock_aapl)
        assert gs.stage == 'mature'

    @pytest.mark.django_db
    def test_early_growth_profile(self, stock_msft):
        """early_growth 기업 프로파일"""
        gs = CompanyGrowthStage.objects.create(
            symbol=stock_msft,
            stage='early_growth',
            revenue_cagr_3y=Decimal('0.4500'),
            net_income_positive_years=1,
            net_income_turned_positive=True,
            fcf_trend='growing',
            fcf_positive_years=2,
            dividend_started=False,
            confidence='medium',
        )
        assert gs.net_income_turned_positive is True
        assert gs.dividend_started is False


# ===== CompanyCapitalDNA =====

class TestCompanyCapitalDNA:

    @pytest.mark.django_db
    def test_create_capital_dna(self, stock_aapl):
        dna = CompanyCapitalDNA.objects.create(
            symbol=stock_aapl,
            rd_to_revenue=Decimal('0.0700'),
            rd_trend='stable',
            capex_to_revenue=Decimal('0.0300'),
            capex_trend='stable',
            dividend_payout=Decimal('0.1500'),
            buyback_yield=Decimal('0.0280'),
            total_shareholder_return_pct=Decimal('0.0780'),
            net_cash_position=65000000000,
            cash_to_market_cap=Decimal('0.0220'),
            capital_type='shareholder_first',
        )
        assert dna.pk == 'AAPL'
        assert dna.capital_type == 'shareholder_first'

    @pytest.mark.django_db
    def test_one_to_one(self, stock_aapl):
        CompanyCapitalDNA.objects.create(symbol=stock_aapl)
        with pytest.raises(IntegrityError):
            CompanyCapitalDNA.objects.create(symbol=stock_aapl)

    @pytest.mark.django_db
    @pytest.mark.parametrize('cap_type', [
        'heavy_investor', 'balanced', 'shareholder_first',
        'cash_hoarder', 'aggressive_growth', 'unknown',
    ])
    def test_all_capital_types(self, stock_aapl, cap_type):
        """6개 capital_type 모두 유효"""
        CompanyCapitalDNA.objects.filter(symbol=stock_aapl).delete()
        dna = CompanyCapitalDNA.objects.create(symbol=stock_aapl, capital_type=cap_type)
        dna.refresh_from_db()
        assert dna.capital_type == cap_type

    @pytest.mark.django_db
    def test_heavy_investor_profile(self, stock_msft):
        """R&D/Capex 집중 기업"""
        dna = CompanyCapitalDNA.objects.create(
            symbol=stock_msft,
            rd_to_revenue=Decimal('0.1800'),
            rd_trend='increasing',
            capex_to_revenue=Decimal('0.1200'),
            capex_trend='expanding',
            dividend_payout=Decimal('0.0100'),
            capital_type='heavy_investor',
        )
        assert dna.rd_to_revenue > Decimal('0.10')
        assert dna.capex_trend == 'expanding'

    @pytest.mark.django_db
    def test_negative_net_cash(self, stock_aapl):
        """순부채 기업 (음수 net_cash_position)"""
        dna = CompanyCapitalDNA.objects.create(
            symbol=stock_aapl,
            net_cash_position=-50000000000,
            capital_type='balanced',
        )
        assert dna.net_cash_position < 0

    @pytest.mark.django_db
    def test_str_representation(self, stock_aapl):
        dna = CompanyCapitalDNA.objects.create(
            symbol=stock_aapl, capital_type='cash_hoarder',
        )
        s = str(dna)
        assert 'AAPL' in s
        assert 'cash_hoarder' in s
