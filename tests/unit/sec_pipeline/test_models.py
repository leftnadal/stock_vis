"""
sec_pipeline 모델 단위 테스트.

모델 생성, __str__, Meta 설정 검증.
"""

import pytest
from datetime import date
from unittest.mock import MagicMock


@pytest.mark.django_db
class TestRawDocumentStore:
    def test_create_and_str(self):
        from stocks.models import Stock
        from sec_pipeline.models import RawDocumentStore

        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        doc = RawDocumentStore.objects.create(
            symbol=stock,
            accession_no='0000320193-23-000106',
            filing_date=date(2023, 11, 3),
            fiscal_year=2023,
            final_link='https://sec.gov/test',
            status='success',
        )
        assert 'AAPL' in str(doc)
        assert '2023' in str(doc)

    def test_default_values(self):
        from stocks.models import Stock
        from sec_pipeline.models import RawDocumentStore

        stock = Stock.objects.create(symbol='MSFT', stock_name='Microsoft')
        doc = RawDocumentStore.objects.create(
            symbol=stock,
            accession_no='acc-test-001',
            filing_date=date(2023, 1, 1),
            fiscal_year=2022,
            final_link='https://sec.gov/test2',
        )
        assert doc.status == 'success'
        assert doc.extraction_method == 'regex'
        assert doc.item_1_text == ''
        assert doc.warnings == []


@pytest.mark.django_db
class TestSupplyChainEvidence:
    def test_create_and_str(self):
        from stocks.models import Stock
        from sec_pipeline.models import RawDocumentStore, SupplyChainEvidence

        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        doc = RawDocumentStore.objects.create(
            symbol=stock,
            accession_no='acc-sce-001',
            filing_date=date(2023, 11, 3),
            fiscal_year=2023,
            final_link='https://sec.gov/test',
        )
        evidence = SupplyChainEvidence.objects.create(
            source_document=doc,
            source_company=stock,
            target_company_name='TSMC',
            relationship_type='SUPPLIES_TO',
            evidence_text='TSMC manufactures chips',
            system_confidence=0.85,
        )
        assert 'TSMC' in str(evidence)
        assert 'SUPPLIES_TO' in str(evidence)
        assert evidence.neo4j_dirty is True

    def test_nullable_target(self):
        from stocks.models import Stock
        from sec_pipeline.models import RawDocumentStore, SupplyChainEvidence

        stock = Stock.objects.create(symbol='GOOG', stock_name='Google')
        doc = RawDocumentStore.objects.create(
            symbol=stock,
            accession_no='acc-sce-002',
            filing_date=date(2023, 6, 1),
            fiscal_year=2023,
            final_link='https://sec.gov/goog',
        )
        evidence = SupplyChainEvidence.objects.create(
            source_document=doc,
            source_company=stock,
            target_company=None,
            target_company_name='Unknown Corp',
            relationship_type='DEPENDS_ON',
            evidence_text='Depends on Unknown Corp',
        )
        assert evidence.target_company is None


@pytest.mark.django_db
class TestBusinessModelSnapshot:
    def test_create_and_str(self):
        from stocks.models import Stock
        from sec_pipeline.models import RawDocumentStore, BusinessModelSnapshot

        stock = Stock.objects.create(symbol='NVDA', stock_name='NVIDIA')
        doc = RawDocumentStore.objects.create(
            symbol=stock,
            accession_no='acc-bm-001',
            filing_date=date(2023, 3, 1),
            fiscal_year=2022,
            final_link='https://sec.gov/nvda',
        )
        bm = BusinessModelSnapshot.objects.create(
            symbol=stock,
            source_document=doc,
            as_of_date=date(2023, 3, 1),
            direct_customer_contact='direct',
            contract_model='subscription',
            recurring_revenue_signal='high',
        )
        assert 'NVDA' in str(bm)
        assert bm.confidence_grade == 'low'

    def test_default_unknown(self):
        from stocks.models import Stock
        from sec_pipeline.models import RawDocumentStore, BusinessModelSnapshot

        stock = Stock.objects.create(symbol='AMD', stock_name='AMD')
        doc = RawDocumentStore.objects.create(
            symbol=stock,
            accession_no='acc-bm-002',
            filing_date=date(2023, 2, 1),
            fiscal_year=2022,
            final_link='https://sec.gov/amd',
        )
        bm = BusinessModelSnapshot.objects.create(
            symbol=stock,
            source_document=doc,
            as_of_date=date(2023, 2, 1),
        )
        assert bm.direct_customer_contact == 'unknown'
        assert bm.contract_model == 'unknown'
        assert bm.channel_dependency == 'unknown'


@pytest.mark.django_db
class TestCompanyAlias:
    def test_create_and_str(self):
        from sec_pipeline.models import CompanyAlias

        alias = CompanyAlias.objects.create(
            alias='Taiwan Semiconductor',
            ticker='TSM',
            context_sector='Technology',
            source='manual_seed',
        )
        assert 'Taiwan Semiconductor' in str(alias)
        assert 'TSM' in str(alias)
        assert 'Technology' in str(alias)

    def test_unique_together(self):
        from sec_pipeline.models import CompanyAlias
        from django.db import IntegrityError

        CompanyAlias.objects.create(
            alias='Samsung', ticker='SSNLF', context_sector='',
        )
        with pytest.raises(IntegrityError):
            CompanyAlias.objects.create(
                alias='Samsung', ticker='005930', context_sector='',
            )


@pytest.mark.django_db
class TestUnmatchedCompanyQueue:
    def test_create_and_str(self):
        from sec_pipeline.models import UnmatchedCompanyQueue

        entry = UnmatchedCompanyQueue.objects.create(
            raw_company_name='Random Corp XYZ',
            source_symbol='AAPL',
        )
        assert 'Random Corp XYZ' in str(entry)
        assert entry.status == 'pending'
        assert entry.occurrence_count == 1

    def test_ordering_by_occurrence(self):
        from sec_pipeline.models import UnmatchedCompanyQueue

        UnmatchedCompanyQueue.objects.create(
            raw_company_name='Low Freq', source_symbol='A', occurrence_count=1,
        )
        UnmatchedCompanyQueue.objects.create(
            raw_company_name='High Freq', source_symbol='B', occurrence_count=10,
        )
        entries = list(UnmatchedCompanyQueue.objects.all())
        assert entries[0].raw_company_name == 'High Freq'


@pytest.mark.django_db
class TestFilingProcessLog:
    def test_create_and_str(self):
        from sec_pipeline.models import FilingProcessLog

        log = FilingProcessLog.objects.create(
            symbol='AAPL',
            stage='section_extract',
            status='success',
            detail='3 sections extracted',
        )
        assert 'AAPL' in str(log)
        assert 'section_extract' in str(log)
        assert 'success' in str(log)
