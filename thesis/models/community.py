from django.conf import settings
from django.db import models


class ThesisFollow(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='thesis_follows',
    )
    original_thesis = models.ForeignKey(
        'thesis.Thesis',
        on_delete=models.CASCADE,
        related_name='followers',
    )
    user_thesis = models.ForeignKey(
        'thesis.Thesis',
        on_delete=models.CASCADE,
        related_name='followed_from',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'original_thesis']

    def __str__(self):
        return f"{self.user} follows {self.original_thesis.title}"


class PopularThesisCache(models.Model):
    thesis = models.OneToOneField(
        'thesis.Thesis',
        on_delete=models.CASCADE,
        related_name='popularity',
    )
    follower_count = models.PositiveIntegerField(default=0)
    support_ratio = models.FloatField(default=0.5)
    rank = models.PositiveIntegerField(default=0)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['rank']

    def __str__(self):
        return f"#{self.rank} {self.thesis.title} ({self.follower_count} followers)"
