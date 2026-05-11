"""
sec_pipeline 모델 추가 단위 테스트.

기존 test_models.py에서 누락된 영역:
- BusinessModelEvidence (스냅샷별 근거 문장)
- PipelineIntelligenceReport (LLM 품질 리포트)
- RawDocumentStore ordering by -filing_date
- CompanyAlias 다른 sector + 동일 alias 허용
- UnmatchedCompanyQueue source_sectors JSON
- BusinessModelSnapshot get_latest_by/ordering
"""

import pytest
from datetime import date


@pytest.mark.django_db
class TestBusinessModelEvidence:
    def test_create_and_str(self):
        from stocks.models import Stock
        from sec_pipeline.models import (
            RawDocumentStore, BusinessModelSnapshot, BusinessModelEvidence,
        )

        stock = Stock.objects.create(symbol='AMZN', stock_name='Amazon')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-bme-1',
            filing_date=date(2023, 2, 1), fiscal_year=2022,
            final_link='https://sec.gov/amzn',
        )
        snap = BusinessModelSnapshot.objects.create(
            symbol=stock, source_document=doc,
            as_of_date=date(2023, 2, 1),
            direct_customer_contact='direct',
        )
        ev = BusinessModelEvidence.objects.create(
            snapshot=snap,
            field_name='direct_customer_contact',
            evidence_text='Amazon sells directly to consumers via website.',
            confidence=0.9,
        )
        # __str__는 snapshot + field_name 포함
        s = str(ev)
        assert 'direct_customer_contact' in s
        assert ev.confidence == 0.9
        # 역참조 가능
        assert snap.evidences.count() == 1


@pytest.mark.django_db
class TestPipelineIntelligenceReport:
    def test_create_and_str(self):
        from sec_pipeline.models import PipelineIntelligenceReport

        report = PipelineIntelligenceReport.objects.create(
            report_date=date(2023, 11, 15),
            hours_back=24,
            collection_score=0.9,
            extraction_score=0.85,
            matching_score=0.7,
            sync_score=0.95,
            quality_score=0.88,
            health_score=0.86,
            severity='healthy',
            summary='All systems nominal.',
        )
        s = str(report)
        assert '2023-11-15' in s
        assert 'healthy' in s
        assert report.recommended_actions == []

    def test_severity_choices(self):
        from sec_pipeline.models import PipelineIntelligenceReport

        critical_report = PipelineIntelligenceReport.objects.create(
            report_date=date(2023, 11, 16), severity='critical',
            summary='Critical fail rate detected.',
        )
        assert critical_report.severity == 'critical'

    def test_get_latest_by_report_date(self):
        from sec_pipeline.models import PipelineIntelligenceReport

        PipelineIntelligenceReport.objects.create(
            report_date=date(2023, 11, 1), severity='healthy',
        )
        latest = PipelineIntelligenceReport.objects.create(
            report_date=date(2023, 11, 15), severity='warning',
        )
        result = PipelineIntelligenceReport.objects.latest()
        assert result.id == latest.id


@pytest.mark.django_db
class TestRawDocumentStoreOrdering:
    def test_ordering_by_filing_date_desc(self):
        from stocks.models import Stock
        from sec_pipeline.models import RawDocumentStore

        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple')
        old = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-old',
            filing_date=date(2020, 11, 1), fiscal_year=2020,
            final_link='https://sec.gov/old',
        )
        new = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-new',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/new',
        )
        docs = list(RawDocumentStore.objects.all())
        # ordering = ['-filing_date'] → 최신이 먼저
        assert docs[0].accession_no == 'acc-new'
        assert docs[1].accession_no == 'acc-old'


@pytest.mark.django_db
class TestCompanyAliasMultiSector:
    def test_same_alias_different_sectors_allowed(self):
        """unique_together=(alias, context_sector) 이므로 sector만 다르면 OK."""
        from sec_pipeline.models import CompanyAlias

        CompanyAlias.objects.create(
            alias='Apex', ticker='APX1', context_sector='Technology',
        )
        # 동일 alias, 다른 sector → 통과
        CompanyAlias.objects.create(
            alias='Apex', ticker='APX2', context_sector='Healthcare',
        )
        assert CompanyAlias.objects.filter(alias='Apex').count() == 2

    def test_source_default_manual_seed(self):
        from sec_pipeline.models import CompanyAlias

        alias = CompanyAlias.objects.create(
            alias='Test Co', ticker='TST', context_sector='',
        )
        assert alias.source == 'manual_seed'


@pytest.mark.django_db
class TestUnmatchedCompanyQueueExtra:
    def test_source_sectors_persisted_as_list(self):
        from sec_pipeline.models import UnmatchedCompanyQueue

        entry = UnmatchedCompanyQueue.objects.create(
            raw_company_name='X Co', source_symbol='AAPL',
            source_sectors=['Technology', 'Healthcare'],
        )
        entry.refresh_from_db()
        assert entry.source_sectors == ['Technology', 'Healthcare']

    def test_fuzzy_candidates_default_empty(self):
        from sec_pipeline.models import UnmatchedCompanyQueue

        entry = UnmatchedCompanyQueue.objects.create(
            raw_company_name='Y Co', source_symbol='MSFT',
        )
        assert entry.fuzzy_candidates == []
        assert entry.resolved_ticker == ''


@pytest.mark.django_db
class TestBusinessModelSnapshotMeta:
    def test_get_latest_by_as_of_date(self):
        """get_latest_by = 'as_of_date' (created_at 아님)."""
        from stocks.models import Stock
        from sec_pipeline.models import RawDocumentStore, BusinessModelSnapshot

        stock = Stock.objects.create(symbol='NFLX', stock_name='Netflix')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-bms-1',
            filing_date=date(2022, 2, 1), fiscal_year=2021,
            final_link='https://sec.gov/nflx1',
        )
        # 더 최근 as_of_date를 먼저 생성 (created_at은 더 이름)
        new_snap = BusinessModelSnapshot.objects.create(
            symbol=stock, source_document=doc,
            as_of_date=date(2023, 2, 1),
        )
        BusinessModelSnapshot.objects.create(
            symbol=stock, source_document=doc,
            as_of_date=date(2020, 2, 1),
        )
        latest = BusinessModelSnapshot.objects.latest()
        # as_of_date 기준이므로 2023년이 latest
        assert latest.id == new_snap.id
