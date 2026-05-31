"""
sec_pipeline 모델 추가 엣지 케이스 테스트.

기존 test_models.py / test_models_advanced.py 에서 누락된 영역:
- SupplyChainEvidence default values (system_confidence=0.0, prompt_version='v1', neo4j_synced_at=None)
- FilingProcessLog ordering = ['-started_at']
- PipelineIntelligenceReport default 값 (health_score=0.0, hours_back=24)
- CompanyAlias context_country 가 unique_together 에 포함되지 않음
- RawDocumentStore CASCADE → SupplyChainEvidence 삭제
- BusinessModelEvidence 기본 confidence
"""

from datetime import date

import pytest


@pytest.mark.django_db
class TestSupplyChainEvidenceDefaults:
    def test_default_confidence_and_grade(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence

        stock = Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-sce-def-1',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/x',
        )
        ev = SupplyChainEvidence.objects.create(
            source_document=doc, source_company=stock,
            target_company_name='X Corp',
            relationship_type='SUPPLIES_TO',
            evidence_text='ev',
        )
        assert ev.system_confidence == 0.0
        assert ev.confidence_grade == 'low'
        assert ev.prompt_version == 'v1'
        assert ev.neo4j_synced_at is None
        assert ev.neo4j_dirty is True


@pytest.mark.django_db
class TestFilingProcessLogOrdering:
    def test_ordering_by_started_at_desc(self):
        from services.sec_pipeline.models import FilingProcessLog

        old = FilingProcessLog.objects.create(
            symbol='AAPL', stage='sec_fetch', status='success',
        )
        new = FilingProcessLog.objects.create(
            symbol='AAPL', stage='section_extract', status='success',
        )
        logs = list(FilingProcessLog.objects.all())
        assert logs[0].id == new.id
        assert logs[1].id == old.id

    def test_default_detail_empty(self):
        from services.sec_pipeline.models import FilingProcessLog
        log = FilingProcessLog.objects.create(
            symbol='AAPL', stage='neo4j_sync', status='started',
        )
        assert log.detail == ''
        assert log.duration_seconds is None


@pytest.mark.django_db
class TestPipelineIntelligenceReportDefaults:
    def test_default_scores_zero(self):
        from services.sec_pipeline.models import PipelineIntelligenceReport
        report = PipelineIntelligenceReport.objects.create(
            report_date=date(2023, 11, 15),
        )
        assert report.collection_score == 0.0
        assert report.extraction_score == 0.0
        assert report.matching_score == 0.0
        assert report.sync_score == 0.0
        assert report.quality_score == 0.0
        assert report.health_score == 0.0
        assert report.severity == 'healthy'
        assert report.hours_back == 24

    def test_default_json_fields(self):
        from services.sec_pipeline.models import PipelineIntelligenceReport
        report = PipelineIntelligenceReport.objects.create(
            report_date=date(2023, 11, 16),
        )
        assert report.recommended_actions == []
        assert report.trend_vs_previous == {}


@pytest.mark.django_db
class TestCompanyAliasContextCountry:
    def test_country_not_in_unique_constraint(self):
        """unique_together = (alias, context_sector) — country 는 무관."""
        from services.sec_pipeline.models import CompanyAlias
        CompanyAlias.objects.create(
            alias='SomeCo', ticker='SCO', context_sector='Tech',
            context_country='US',
        )
        # country 가 다르더라도 unique 위반
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            CompanyAlias.objects.create(
                alias='SomeCo', ticker='SCO_KR', context_sector='Tech',
                context_country='KR',
            )


@pytest.mark.django_db
class TestRawDocumentCascade:
    def test_cascade_deletes_supply_chain_evidence(self):
        """RawDocumentStore 삭제 시 관련 SupplyChainEvidence 도 삭제."""
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import RawDocumentStore, SupplyChainEvidence

        stock = Stock.objects.create(symbol='CSC', stock_name='Cascade Co')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-csc-1',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/csc',
        )
        SupplyChainEvidence.objects.create(
            source_document=doc, source_company=stock,
            target_company_name='Other Co', relationship_type='SUPPLIES_TO',
            evidence_text='ev',
        )
        assert SupplyChainEvidence.objects.filter(source_document=doc).count() == 1
        doc.delete()
        assert SupplyChainEvidence.objects.filter(source_document_id=doc.id).count() == 0


@pytest.mark.django_db
class TestBusinessModelEvidenceDefaults:
    def test_default_confidence_zero(self):
        from packages.shared.stocks.models import Stock
        from services.sec_pipeline.models import (
            BusinessModelEvidence,
            BusinessModelSnapshot,
            RawDocumentStore,
        )

        stock = Stock.objects.create(symbol='BME', stock_name='BME Co')
        doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-bme-def-1',
            filing_date=date(2023, 2, 1), fiscal_year=2022,
            final_link='https://sec.gov/bme',
        )
        snap = BusinessModelSnapshot.objects.create(
            symbol=stock, source_document=doc, as_of_date=date(2023, 2, 1),
        )
        ev = BusinessModelEvidence.objects.create(
            snapshot=snap, field_name='contract_model',
            evidence_text='one-time license sales',
        )
        assert ev.confidence == 0.0
