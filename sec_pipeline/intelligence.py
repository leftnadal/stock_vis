"""
SEC-PR-16: Pipeline Intelligence — 5차원 데이터 수집 + LLM 분석 리포트.

⚠️ 리포트 숫자는 전부 내부 운영용 (원칙 6 Admin 허용).
"""

import json
import logging
from datetime import timedelta

from django.db.models import Avg, Count
from django.utils import timezone

logger = logging.getLogger(__name__)

PIPELINE_INTELLIGENCE_PROMPT = """You are an operations analyst reviewing a data pipeline's health metrics.

Analyze these 5 dimensions and provide:
1. A 2-3 sentence summary of overall pipeline health
2. Cross-dimensional insights (e.g., "low matching rate may be caused by...")
3. Up to 3 recommended actions, prioritized by impact

**Pipeline Metrics (last {hours_back} hours)**:

Collection:
  Total: {coll_total}, Success: {coll_success}, Failed: {coll_failed}
  Success Rate: {coll_rate:.1%}

Extraction (Track A - Supply Chain):
  Total Evidences: {ext_total}, Avg Confidence: {ext_avg_conf:.2f}
  Relationship Types: {ext_types}

Matching:
  Matched: {match_matched}, Unmatched: {match_unmatched}
  Match Rate: {match_rate:.1%}
  Queue Pending: {queue_pending}

Sync:
  Neo4j Synced: {sync_synced}, Neo4j Pending: {sync_pending}

Quality:
  Section Validation Failures: {qual_section_fail}
  Track B Snapshots: {qual_bm_total}, Unknown Fields: {qual_bm_unknown}

Return JSON:
{{
  "summary": "...",
  "cross_insights": "...",
  "recommended_actions": ["action1", "action2", "action3"],
  "dimension_scores": {{
    "collection": 0.0-1.0,
    "extraction": 0.0-1.0,
    "matching": 0.0-1.0,
    "sync": 0.0-1.0,
    "quality": 0.0-1.0
  }},
  "health_score": 0.0-1.0,
  "severity": "healthy|warning|critical"
}}
"""


class PipelineDataCollector:
    """5차원 파이프라인 데이터 수집."""

    def collect(self, hours_back: int = 24) -> dict:
        from .models import (
            BusinessModelSnapshot,
            FilingProcessLog,
            RawDocumentStore,
            SupplyChainEvidence,
            UnmatchedCompanyQueue,
        )

        since = timezone.now() - timedelta(hours=hours_back)

        # Collection
        recent_docs = RawDocumentStore.objects.filter(collected_at__gte=since)
        coll_total = recent_docs.count()
        coll_success = recent_docs.filter(status='success').count()
        coll_failed = recent_docs.filter(status='failed').count()

        # Extraction
        recent_ev = SupplyChainEvidence.objects.filter(extracted_at__gte=since)
        ext_total = recent_ev.count()
        ext_avg_conf = recent_ev.aggregate(avg=Avg('system_confidence'))['avg'] or 0
        ext_types = dict(
            recent_ev.values_list('relationship_type')
            .annotate(c=Count('id'))
            .values_list('relationship_type', 'c')
        )

        # Matching
        match_matched = recent_ev.filter(target_company__isnull=False).count()
        match_unmatched = recent_ev.filter(target_company__isnull=True).count()
        queue_pending = UnmatchedCompanyQueue.objects.filter(status='pending').count()

        # Sync
        all_ev = SupplyChainEvidence.objects.all()
        sync_synced = all_ev.filter(neo4j_dirty=False).count()
        sync_pending = all_ev.filter(neo4j_dirty=True, target_company__isnull=False).count()

        # Quality
        qual_section_fail = FilingProcessLog.objects.filter(
            started_at__gte=since,
            stage='section_extract',
            detail__startswith='FAIL:',
        ).count()

        recent_bm = BusinessModelSnapshot.objects.filter(created_at__gte=since)
        qual_bm_total = recent_bm.count()
        qual_bm_unknown = 0
        bm_fields = ['direct_customer_contact', 'contract_model',
                      'recurring_revenue_signal', 'channel_dependency',
                      'customer_concentration']
        for snap in recent_bm:
            for f in bm_fields:
                if getattr(snap, f) == 'unknown':
                    qual_bm_unknown += 1

        return {
            'hours_back': hours_back,
            'coll_total': coll_total,
            'coll_success': coll_success,
            'coll_failed': coll_failed,
            'coll_rate': coll_success / max(coll_total, 1),
            'ext_total': ext_total,
            'ext_avg_conf': ext_avg_conf,
            'ext_types': str(ext_types),
            'match_matched': match_matched,
            'match_unmatched': match_unmatched,
            'match_rate': match_matched / max(match_matched + match_unmatched, 1),
            'queue_pending': queue_pending,
            'sync_synced': sync_synced,
            'sync_pending': sync_pending,
            'qual_section_fail': qual_section_fail,
            'qual_bm_total': qual_bm_total,
            'qual_bm_unknown': qual_bm_unknown,
        }


class PipelineIntelligenceReporter:
    """Gemini Flash → DB 저장."""

    def generate_report(self, hours_back: int = 24) -> dict:
        from .models import PipelineIntelligenceReport

        collector = PipelineDataCollector()
        data = collector.collect(hours_back)

        prompt = PIPELINE_INTELLIGENCE_PROMPT.format(**data)

        try:
            from django.conf import settings
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            config = types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.2,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            )

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config,
            )

            text = response.text if hasattr(response, 'text') and response.text else '{}'
            result = json.loads(text)

        except Exception as e:
            logger.error(f"Intelligence report generation failed: {e}")
            result = {
                'summary': f'Report generation failed: {e}',
                'cross_insights': '',
                'recommended_actions': [],
                'dimension_scores': {
                    'collection': 0, 'extraction': 0,
                    'matching': 0, 'sync': 0, 'quality': 0,
                },
                'health_score': 0,
                'severity': 'critical',
            }

        scores = result.get('dimension_scores', {})
        report = PipelineIntelligenceReport.objects.create(
            report_date=timezone.localdate(),
            hours_back=hours_back,
            collection_score=scores.get('collection', 0),
            extraction_score=scores.get('extraction', 0),
            matching_score=scores.get('matching', 0),
            sync_score=scores.get('sync', 0),
            quality_score=scores.get('quality', 0),
            health_score=result.get('health_score', 0),
            severity=result.get('severity', 'warning'),
            summary=result.get('summary', ''),
            cross_insights=result.get('cross_insights', ''),
            recommended_actions=result.get('recommended_actions', []),
            trend_vs_previous=self._calculate_trend(result),
        )

        logger.info(
            f"Intelligence report generated: {report.severity} "
            f"(health={report.health_score:.2f})"
        )
        return {
            'report_id': report.id,
            'severity': report.severity,
            'health_score': report.health_score,
        }

    def _calculate_trend(self, current: dict) -> dict:
        """이전 리포트 대비 변화."""
        from .models import PipelineIntelligenceReport

        previous = PipelineIntelligenceReport.objects.order_by('-created_at').first()
        if not previous:
            return {}

        return {
            'health_delta': current.get('health_score', 0) - previous.health_score,
            'previous_severity': previous.severity,
        }
