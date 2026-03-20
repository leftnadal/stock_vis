import uuid

from django.db import models


class KeywordCache(models.Model):
    """빌더 Keyword Hint용 캐시 (Phase B)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.CharField(max_length=100, db_index=True)
    source = models.CharField(
        max_length=20,
        choices=[
            ('chain', 'Chain Sight'),
            ('eod', 'EOD Signals'),
            ('news', 'News'),
        ],
    )
    text = models.CharField(max_length=200)
    role = models.CharField(
        max_length=20,
        choices=[
            ('support', 'Support'),
            ('risk', 'Risk'),
            ('signal', 'Signal'),
            ('theme', 'Theme'),
        ],
    )
    strength = models.CharField(
        max_length=10,
        default='medium',
        choices=[
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
        ],
        help_text="키워드 강도: high=중요 단서, medium=일반, low=약한 힌트",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['target', 'source', 'text']
        indexes = [models.Index(fields=['target', 'source'])]

    def __str__(self):
        return f"[{self.source}/{self.role}] {self.target}: {self.text}"
