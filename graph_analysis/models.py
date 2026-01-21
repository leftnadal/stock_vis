"""
Graph Analysis Models

Stores correlation matrices and graph relationships for stock price analysis
"""
from django.db import models
from django.contrib.postgres.fields import ArrayField
from users.models import Watchlist
from stocks.models import Stock


class CorrelationMatrix(models.Model):
    """
    Daily correlation matrix for a user's watchlist

    Stores the full correlation matrix as JSON for efficient retrieval
    """
    watchlist = models.ForeignKey(
        Watchlist,
        on_delete=models.CASCADE,
        related_name='correlation_matrices',
        db_index=True
    )

    date = models.DateField(
        db_index=True,
        help_text="Date of the correlation calculation"
    )

    # Matrix storage (JSON format)
    matrix_data = models.JSONField(
        help_text="Correlation matrix as nested dict: {symbol1: {symbol2: correlation}}"
    )

    # Metadata
    stock_count = models.IntegerField(
        default=0,
        help_text="Number of stocks in the matrix"
    )

    calculation_period = models.IntegerField(
        default=90,
        help_text="Number of days used for correlation calculation (default: 90 days = 3 months)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'graph_correlation_matrix'
        unique_together = [['watchlist', 'date']]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['watchlist', '-date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"CorrelationMatrix({self.watchlist.name}, {self.date}, {self.stock_count} stocks)"


class CorrelationEdge(models.Model):
    """
    Individual correlation relationship between two stocks

    Stores daily correlation coefficients for quick queries and anomaly detection
    """
    watchlist = models.ForeignKey(
        Watchlist,
        on_delete=models.CASCADE,
        related_name='correlation_edges',
        db_index=True
    )

    stock_a = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='correlation_edges_a',
        help_text="First stock in the pair"
    )

    stock_b = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='correlation_edges_b',
        help_text="Second stock in the pair"
    )

    date = models.DateField(
        db_index=True,
        help_text="Date of the correlation value"
    )

    # Correlation data
    correlation = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        help_text="Correlation coefficient (-1.0 to 1.0)"
    )

    previous_correlation = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Previous day's correlation coefficient"
    )

    correlation_change = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
        help_text="Change from previous correlation"
    )

    # Anomaly detection
    is_anomaly = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if change exceeds threshold (±0.2)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'graph_correlation_edge'
        unique_together = [['watchlist', 'stock_a', 'stock_b', 'date']]
        ordering = ['-date', 'stock_a', 'stock_b']
        indexes = [
            models.Index(fields=['watchlist', '-date']),
            models.Index(fields=['watchlist', 'is_anomaly', '-date']),
            models.Index(fields=['stock_a', 'stock_b', '-date']),
        ]

    def __str__(self):
        return f"{self.stock_a.symbol}-{self.stock_b.symbol}: {self.correlation} ({self.date})"

    @property
    def is_positive(self) -> bool:
        """Check if correlation is positive"""
        return self.correlation > 0

    @property
    def is_strong(self) -> bool:
        """Check if correlation is strong (|r| > 0.7)"""
        return abs(self.correlation) > 0.7

    @property
    def strength_label(self) -> str:
        """Get correlation strength label"""
        abs_corr = abs(self.correlation)
        if abs_corr >= 0.8:
            return "Very Strong"
        elif abs_corr >= 0.6:
            return "Strong"
        elif abs_corr >= 0.4:
            return "Moderate"
        elif abs_corr >= 0.2:
            return "Weak"
        else:
            return "Very Weak"


class CorrelationAnomaly(models.Model):
    """
    Detected anomalies in correlation changes

    Triggered when correlation changes by ±0.2 or more
    """
    ANOMALY_TYPES = [
        ('divergence', 'Divergence'),  # Correlation decreased significantly
        ('convergence', 'Convergence'),  # Correlation increased significantly
        ('reversal', 'Reversal'),  # Changed from positive to negative or vice versa
    ]

    watchlist = models.ForeignKey(
        Watchlist,
        on_delete=models.CASCADE,
        related_name='correlation_anomalies',
        db_index=True
    )

    edge = models.ForeignKey(
        CorrelationEdge,
        on_delete=models.CASCADE,
        related_name='anomalies',
        help_text="The edge that triggered this anomaly"
    )

    date = models.DateField(
        db_index=True,
        help_text="Date when anomaly was detected"
    )

    anomaly_type = models.CharField(
        max_length=20,
        choices=ANOMALY_TYPES,
        help_text="Type of anomaly detected"
    )

    # Anomaly details
    previous_correlation = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        help_text="Previous correlation value"
    )

    current_correlation = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        help_text="Current correlation value"
    )

    change_magnitude = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        help_text="Absolute change in correlation"
    )

    # Alert management
    alerted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if user has been alerted about this anomaly"
    )

    alert_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when alert was sent"
    )

    # User engagement
    dismissed = models.BooleanField(
        default=False,
        help_text="True if user dismissed this anomaly"
    )

    notes = models.TextField(
        blank=True,
        help_text="User notes about this anomaly"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'graph_correlation_anomaly'
        ordering = ['-date', '-change_magnitude']
        indexes = [
            models.Index(fields=['watchlist', '-date']),
            models.Index(fields=['watchlist', 'alerted', '-date']),
            models.Index(fields=['-date', '-change_magnitude']),
        ]

    def __str__(self):
        return f"Anomaly: {self.edge.stock_a.symbol}-{self.edge.stock_b.symbol} ({self.anomaly_type}, {self.date})"

    @classmethod
    def detect_anomaly_type(cls, previous_corr: float, current_corr: float) -> str:
        """
        Detect anomaly type based on correlation change

        Args:
            previous_corr: Previous correlation value
            current_corr: Current correlation value

        Returns:
            Anomaly type string
        """
        # Check for sign reversal
        if (previous_corr > 0 and current_corr < 0) or (previous_corr < 0 and current_corr > 0):
            return 'reversal'

        # Check for divergence (correlation decreased)
        if abs(current_corr) < abs(previous_corr):
            return 'divergence'

        # Convergence (correlation increased)
        return 'convergence'


class PriceCache(models.Model):
    """
    Cached historical prices for correlation calculation

    Stores 90-day price history per stock to avoid repeated database queries
    """
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='price_caches',
        db_index=True
    )

    date = models.DateField(
        db_index=True,
        help_text="Cache date (latest date in the price data)"
    )

    # Price data (90 days)
    prices = models.JSONField(
        help_text="List of price records: [{date: '2026-01-09', close: 151.75}, ...]"
    )

    period_days = models.IntegerField(
        default=90,
        help_text="Number of days in cache"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'graph_price_cache'
        unique_together = [['stock', 'date']]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['stock', '-date']),
        ]

    def __str__(self):
        return f"PriceCache({self.stock.symbol}, {self.date}, {self.period_days} days)"


class GraphMetadata(models.Model):
    """
    Metadata about graph calculation runs

    Tracks performance and status of daily correlation calculations
    """
    watchlist = models.ForeignKey(
        Watchlist,
        on_delete=models.CASCADE,
        related_name='graph_metadata',
        db_index=True
    )

    date = models.DateField(
        db_index=True,
        help_text="Calculation date"
    )

    # Calculation metrics
    stock_count = models.IntegerField(
        help_text="Number of stocks processed"
    )

    edge_count = models.IntegerField(
        help_text="Number of edges (correlations) calculated"
    )

    anomaly_count = models.IntegerField(
        default=0,
        help_text="Number of anomalies detected"
    )

    # Performance metrics
    calculation_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Calculation time in milliseconds"
    )

    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    error_message = models.TextField(
        blank=True,
        help_text="Error message if calculation failed"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'graph_metadata'
        unique_together = [['watchlist', 'date']]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['watchlist', '-date']),
            models.Index(fields=['status', '-date']),
        ]

    def __str__(self):
        return f"GraphMetadata({self.watchlist.name}, {self.date}, {self.status})"
