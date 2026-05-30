from django.db import models


class BatchJobRun(models.Model):
    """
    배치 파이프라인 실행 이력.
    metrics, validation, chainsight 모든 배치에서 공용.
    """

    STATUS_CHOICES = [
        ("running", "Running"),
        ("success", "Success"),
        ("partial_failure", "Partial Failure"),
        ("failed", "Failed"),
    ]

    job_name = models.CharField(max_length=100, db_index=True)
    job_type = models.CharField(
        max_length=50,
        default="scheduled",
        choices=[
            ("scheduled", "Scheduled"),
            ("manual", "Manual"),
            ("retry", "Retry"),
        ],
    )

    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    total_symbols = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    failure_count = models.IntegerField(default=0)
    skip_count = models.IntegerField(default=0)

    failure_details = models.JSONField(default=list)
    pipeline_step = models.CharField(max_length=50, blank=True)
    depends_on_job_id = models.BigIntegerField(null=True, blank=True)
    triggered_by = models.CharField(max_length=50, default="celery_beat")
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "metrics_batch_job_run"
        indexes = [
            models.Index(fields=["job_name", "-started_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.job_name} [{self.status}] {self.started_at}"
