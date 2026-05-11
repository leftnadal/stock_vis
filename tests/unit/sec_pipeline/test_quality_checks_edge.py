"""
quality_checks.py 추가 엣지 케이스 테스트.

기존 test_quality_checks.py / test_quality_checks_advanced.py 에서 누락된 영역:
- run_post_batch_quality_checks: 임계 미달인 케이스 → 알림 없음
- get_dashboard_stats: avg_confidence 가 정확하게 계산되는지
- run_post_batch_quality_checks: hours_back 보다 오래된 데이터는 무시
- run_post_batch_quality_checks: 매칭 큐에 100건 (경계값) — 알림 없음
"""

import pytest
from datetime import date, timedelta

from django.utils import timezone


@pytest.fixture
def stock(db):
    from stocks.models import Stock
    return Stock.objects.create(symbol='AAPL', stock_name='Apple Inc.')


@pytest.fixture
def doc(stock):
    from sec_pipeline.models import RawDocumentStore
    return RawDocumentStore.objects.create(
        symbol=stock, accession_no='acc-qce-001',
        filing_date=date(2023, 11, 1), fiscal_year=2023,
        final_link='https://sec.gov/qce', status='success',
    )


@pytest.mark.django_db
class TestThresholdEdges:
    def test_failure_rate_at_or_below_20pct_no_alert(self, stock):
        """실패율 정확히 20% 이하면 알림 없음 (> 0.20 만 트리거)."""
        from sec_pipeline.models import RawDocumentStore
        from sec_pipeline.quality_checks import run_post_batch_quality_checks

        # 1 failed / 5 total = 20% (경계)
        for i in range(4):
            RawDocumentStore.objects.create(
                symbol=stock, accession_no=f'acc-ok-{i}',
                filing_date=date(2023, 11, 1), fiscal_year=2023,
                final_link=f'https://sec.gov/ok{i}', status='success',
            )
        RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-fail-edge',
            filing_date=date(2023, 11, 1), fiscal_year=2023,
            final_link='https://sec.gov/failedge', status='failed',
        )
        alerts = run_post_batch_quality_checks(hours_back=24)
        # 정확히 20% 이므로 ('> 0.20' 조건) 알림 없음
        assert not any('실패율' in a for a in alerts)

    def test_queue_at_100_no_alert(self):
        """미매칭 큐가 정확히 100건이면 알림 없음 (> 100 만 트리거)."""
        from sec_pipeline.models import UnmatchedCompanyQueue
        from sec_pipeline.quality_checks import run_post_batch_quality_checks

        for i in range(100):
            UnmatchedCompanyQueue.objects.create(
                raw_company_name=f'Co{i}', source_symbol='AAPL',
                status='pending',
            )
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert not any('미매칭' in a for a in alerts)

    def test_neo4j_dirty_at_50_no_alert(self, stock, doc):
        """Neo4j dirty 가 정확히 50건이면 알림 없음."""
        from sec_pipeline.models import SupplyChainEvidence
        from sec_pipeline.quality_checks import run_post_batch_quality_checks

        for i in range(50):
            SupplyChainEvidence.objects.create(
                source_document=doc, source_company=stock,
                target_company=stock,
                target_company_name=f'X{i}',
                relationship_type='SUPPLIES_TO', evidence_text='ev',
                system_confidence=0.8, neo4j_dirty=True,
            )
        alerts = run_post_batch_quality_checks(hours_back=24)
        assert not any('Neo4j dirty' in a for a in alerts)


@pytest.mark.django_db
class TestHoursBackFilter:
    def test_old_data_outside_window_ignored(self, stock):
        """hours_back 보다 오래된 데이터는 알림 계산에서 제외된다."""
        from sec_pipeline.models import RawDocumentStore
        from sec_pipeline.quality_checks import run_post_batch_quality_checks

        # 한 개를 24시간 전보다 더 오래 전으로 강제
        old_doc = RawDocumentStore.objects.create(
            symbol=stock, accession_no='acc-old',
            filing_date=date(2023, 1, 1), fiscal_year=2022,
            final_link='https://sec.gov/old', status='failed',
        )
        # collected_at 은 auto_now_add 이므로 update 로 강제 변경
        RawDocumentStore.objects.filter(pk=old_doc.pk).update(
            collected_at=timezone.now() - timedelta(days=10)
        )
        alerts = run_post_batch_quality_checks(hours_back=24)
        # 24시간 윈도우 내 데이터가 없으므로 실패율 계산되지 않음
        assert not any('실패율' in a for a in alerts)


@pytest.mark.django_db
class TestDashboardStatsAvgConfidence:
    def test_avg_confidence_calculated(self, stock, doc):
        """track_a.avg_confidence 가 평균값으로 계산된다."""
        from sec_pipeline.models import SupplyChainEvidence
        from sec_pipeline.quality_checks import get_dashboard_stats

        SupplyChainEvidence.objects.create(
            source_document=doc, source_company=stock,
            target_company=stock, target_company_name='A',
            relationship_type='SUPPLIES_TO', evidence_text='ev',
            system_confidence=0.4,
        )
        SupplyChainEvidence.objects.create(
            source_document=doc, source_company=stock,
            target_company=stock, target_company_name='B',
            relationship_type='SUPPLIES_TO', evidence_text='ev',
            system_confidence=0.6,
        )
        result = get_dashboard_stats()
        assert result['track_a']['avg_confidence'] == pytest.approx(0.5, abs=0.001)

    def test_avg_confidence_zero_when_no_evidence(self):
        """evidence 가 없을 때 avg_confidence 는 0."""
        from sec_pipeline.quality_checks import get_dashboard_stats
        result = get_dashboard_stats()
        assert result['track_a']['avg_confidence'] == 0


@pytest.mark.django_db
class TestNeo4jPendingCount:
    def test_neo4j_pending_excludes_unmatched(self, stock, doc):
        """neo4j_pending 은 target_company 가 매칭된 dirty 만 셈."""
        from sec_pipeline.models import SupplyChainEvidence
        from sec_pipeline.quality_checks import get_dashboard_stats

        # matched + dirty
        SupplyChainEvidence.objects.create(
            source_document=doc, source_company=stock,
            target_company=stock, target_company_name='M',
            relationship_type='SUPPLIES_TO', evidence_text='ev',
            neo4j_dirty=True,
        )
        # unmatched + dirty (neo4j_pending 에 포함되면 안 됨)
        SupplyChainEvidence.objects.create(
            source_document=doc, source_company=stock,
            target_company=None, target_company_name='U',
            relationship_type='SUPPLIES_TO', evidence_text='ev',
            neo4j_dirty=True,
        )
        result = get_dashboard_stats()
        assert result['track_a']['neo4j_pending'] == 1
        assert result['track_a']['unmatched'] == 1
        assert result['track_a']['matched'] == 1
