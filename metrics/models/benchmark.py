from django.db import models
from django.contrib.postgres.fields import ArrayField


class PeerListCache(models.Model):
    """
    종목별 peer 목록 캐시.
    FMP stock-peers API 결과 저장.
    """
    symbol = models.OneToOneField(
        'stocks.Stock',
        on_delete=models.CASCADE,
        to_field='symbol',
        primary_key=True,
        related_name='peer_cache',
    )
    peer_symbols = ArrayField(
        models.CharField(max_length=10),
        default=list, blank=True,
        help_text='["MSFT", "GOOGL", "META"]'
    )
    peer_count = models.IntegerField(default=0)

    use_industry_fallback = models.BooleanField(default=False)
    fallback_reason = models.CharField(max_length=200, blank=True)

    source = models.CharField(max_length=20, default='fmp_peers')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'metrics_peer_list_cache'

    def __str__(self):
        return f"{self.symbol_id}: {self.peer_count} peers"
