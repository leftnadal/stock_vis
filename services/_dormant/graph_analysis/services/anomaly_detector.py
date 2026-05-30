"""
Anomaly Detector Service

Detects anomalies in correlation changes and creates alerts
"""
import logging
from datetime import date, timedelta
from typing import List, Optional
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from users.models import Watchlist
from graph_analysis.models import (
    CorrelationEdge,
    CorrelationAnomaly,
    GraphMetadata,
)

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Detect and alert on correlation anomalies

    Threshold: ±0.2 correlation change
    Max alerts per day: 5
    Cooldown: 24 hours per stock pair
    """

    ANOMALY_THRESHOLD = 0.2  # Minimum change to trigger anomaly
    MIN_ABSOLUTE_CORRELATION = 0.3  # Minimum correlation level to monitor
    MAX_ALERTS_PER_DAY = 5  # Max anomalies to alert per day
    COOLDOWN_HOURS = 24  # Hours between alerts for same stock pair

    def __init__(self, watchlist: Watchlist, detection_date: Optional[date] = None):
        """
        Initialize anomaly detector

        Args:
            watchlist: User's watchlist to monitor
            detection_date: Date to detect anomalies (default: today)
        """
        self.watchlist = watchlist
        self.detection_date = detection_date or date.today()

    def detect_anomalies(self) -> List[CorrelationAnomaly]:
        """
        Detect correlation anomalies for the watchlist

        Returns:
            List of detected anomalies
        """
        try:
            # Get edges with anomalies
            anomalous_edges = self._get_anomalous_edges()

            if not anomalous_edges:
                logger.info(f"No anomalies detected for {self.watchlist.name} on {self.detection_date}")
                return []

            # Filter out recently alerted pairs (cooldown)
            filtered_edges = self._apply_cooldown(anomalous_edges)

            if not filtered_edges:
                logger.info(f"All anomalies are in cooldown for {self.watchlist.name}")
                return []

            # Rank by magnitude and limit to max alerts
            top_anomalies = self._rank_and_limit(filtered_edges)

            # Create anomaly records
            anomalies = self._create_anomaly_records(top_anomalies)

            # Update metadata
            self._update_metadata_anomaly_count(len(anomalies))

            logger.info(
                f"Detected {len(anomalies)} anomalies for {self.watchlist.name} on {self.detection_date}"
            )

            return anomalies

        except Exception as e:
            logger.error(f"Failed to detect anomalies for {self.watchlist.name}: {e}")
            return []

    def _get_anomalous_edges(self) -> List[CorrelationEdge]:
        """Get edges marked as anomalies"""
        edges = CorrelationEdge.objects.filter(
            watchlist=self.watchlist,
            date=self.detection_date,
            is_anomaly=True
        ).select_related('stock_a', 'stock_b')

        return list(edges)

    def _apply_cooldown(self, edges: List[CorrelationEdge]) -> List[CorrelationEdge]:
        """
        Filter out edges that were recently alerted (within cooldown period)

        Args:
            edges: List of anomalous edges

        Returns:
            Filtered list of edges
        """
        cooldown_cutoff = self.detection_date - timedelta(hours=self.COOLDOWN_HOURS)

        filtered = []

        for edge in edges:
            # Check if there's a recent alert for this pair
            recent_alert = CorrelationAnomaly.objects.filter(
                watchlist=self.watchlist,
                edge__stock_a=edge.stock_a,
                edge__stock_b=edge.stock_b,
                date__gt=cooldown_cutoff,
                alerted=True
            ).exists()

            if not recent_alert:
                filtered.append(edge)

        return filtered

    def _rank_and_limit(self, edges: List[CorrelationEdge]) -> List[CorrelationEdge]:
        """
        Rank anomalies by magnitude and limit to max alerts per day

        Args:
            edges: List of anomalous edges

        Returns:
            Top-ranked edges
        """
        # Sort by absolute change magnitude (descending)
        ranked = sorted(
            edges,
            key=lambda e: abs(e.correlation_change),
            reverse=True
        )

        # Limit to max alerts
        return ranked[:self.MAX_ALERTS_PER_DAY]

    @transaction.atomic
    def _create_anomaly_records(
        self,
        edges: List[CorrelationEdge]
    ) -> List[CorrelationAnomaly]:
        """
        Create anomaly records in database

        Args:
            edges: List of anomalous edges

        Returns:
            List of created CorrelationAnomaly objects
        """
        anomalies = []

        for edge in edges:
            # Determine anomaly type
            anomaly_type = CorrelationAnomaly.detect_anomaly_type(
                previous_corr=float(edge.previous_correlation) if edge.previous_correlation else 0,
                current_corr=float(edge.correlation)
            )

            # Create anomaly record
            anomaly = CorrelationAnomaly.objects.create(
                watchlist=self.watchlist,
                edge=edge,
                date=self.detection_date,
                anomaly_type=anomaly_type,
                previous_correlation=edge.previous_correlation or Decimal('0'),
                current_correlation=edge.correlation,
                change_magnitude=abs(edge.correlation_change),
                alerted=False,  # Will be set to True when alert is sent
            )

            anomalies.append(anomaly)

            logger.debug(
                f"Created anomaly: {edge.stock_a.symbol}-{edge.stock_b.symbol} "
                f"({anomaly_type}, change: {edge.correlation_change})"
            )

        return anomalies

    def _update_metadata_anomaly_count(self, count: int):
        """Update GraphMetadata with anomaly count"""
        try:
            metadata = GraphMetadata.objects.filter(
                watchlist=self.watchlist,
                date=self.detection_date
            ).first()

            if metadata:
                metadata.anomaly_count = count
                metadata.save(update_fields=['anomaly_count', 'updated_at'])

        except Exception as e:
            logger.warning(f"Failed to update metadata anomaly count: {e}")

    def get_pending_alerts(self) -> List[CorrelationAnomaly]:
        """
        Get anomalies that haven't been alerted yet

        Returns:
            List of CorrelationAnomaly objects pending alert
        """
        return list(
            CorrelationAnomaly.objects.filter(
                watchlist=self.watchlist,
                date=self.detection_date,
                alerted=False,
                dismissed=False
            ).select_related('edge__stock_a', 'edge__stock_b')
            .order_by('-change_magnitude')
        )

    @transaction.atomic
    def mark_as_alerted(self, anomaly: CorrelationAnomaly):
        """
        Mark anomaly as alerted

        Args:
            anomaly: CorrelationAnomaly to mark
        """
        anomaly.alerted = True
        anomaly.alert_sent_at = timezone.now()
        anomaly.save(update_fields=['alerted', 'alert_sent_at', 'updated_at'])

        logger.info(
            f"Marked anomaly as alerted: {anomaly.edge.stock_a.symbol}-{anomaly.edge.stock_b.symbol}"
        )

    @transaction.atomic
    def dismiss_anomaly(self, anomaly: CorrelationAnomaly, notes: str = ''):
        """
        Dismiss an anomaly (user action)

        Args:
            anomaly: CorrelationAnomaly to dismiss
            notes: Optional user notes
        """
        anomaly.dismissed = True
        if notes:
            anomaly.notes = notes
        anomaly.save(update_fields=['dismissed', 'notes', 'updated_at'])

        logger.info(
            f"Dismissed anomaly: {anomaly.edge.stock_a.symbol}-{anomaly.edge.stock_b.symbol}"
        )

    def get_anomaly_summary(self) -> dict:
        """
        Get summary of anomalies for the watchlist

        Returns:
            Dict with anomaly statistics
        """
        anomalies = CorrelationAnomaly.objects.filter(
            watchlist=self.watchlist,
            date=self.detection_date
        )

        return {
            'total_count': anomalies.count(),
            'alerted_count': anomalies.filter(alerted=True).count(),
            'pending_count': anomalies.filter(alerted=False, dismissed=False).count(),
            'dismissed_count': anomalies.filter(dismissed=True).count(),
            'by_type': {
                'divergence': anomalies.filter(anomaly_type='divergence').count(),
                'convergence': anomalies.filter(anomaly_type='convergence').count(),
                'reversal': anomalies.filter(anomaly_type='reversal').count(),
            }
        }

    @classmethod
    def check_stock_pair_anomaly(
        cls,
        watchlist: Watchlist,
        symbol_a: str,
        symbol_b: str,
        days: int = 7
    ) -> List[CorrelationAnomaly]:
        """
        Check anomaly history for a specific stock pair

        Args:
            watchlist: Watchlist to check
            symbol_a: First stock symbol
            symbol_b: Second stock symbol
            days: Number of days to look back

        Returns:
            List of anomalies for the pair
        """
        cutoff_date = date.today() - timedelta(days=days)

        anomalies = CorrelationAnomaly.objects.filter(
            watchlist=watchlist,
            date__gte=cutoff_date,
            edge__stock_a__symbol__in=[symbol_a, symbol_b],
            edge__stock_b__symbol__in=[symbol_a, symbol_b]
        ).select_related('edge__stock_a', 'edge__stock_b').order_by('-date')

        return list(anomalies)
