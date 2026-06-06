"""
LLM 브리핑 모델 (PR-A2).

소속: apps/market_pulse/models (app 레이어 Django models).
역할: BriefingLog — Gemini 일일 브리핑 본문 + 입력 요약(JSON) 저장.
주요 심볼:
  - BriefingLog: date·body·inputs_summary(JSON)·status·generated_at.
소비처: tasks/briefing.py 적재, api 응답에서 일일 브리핑 노출.
"""

from django.db import models


class BriefingLog(models.Model):
    class Status(models.TextChoices):
        OK = "OK", "OK"
        INSUFFICIENT_DATA = "INSUFFICIENT_DATA", "Insufficient Data"
        REFUSED = "REFUSED", "LLM Refused"
        FAILED = "FAILED", "Failed"

    date = models.DateField(db_index=True)
    model_version = models.CharField(max_length=50, default="gemini-2.5-flash")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OK)

    headline = models.CharField(max_length=300, blank=True, default="")
    body = models.TextField(blank=True, default="")
    body_sections = models.JSONField(default=list, blank=True)

    prompt_inputs = models.JSONField(default=dict, blank=True)

    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)

    # PR-A2 §3.5: LLM 비용 추적 (USD, Gemini 단가 ÷ 토큰)
    cost_usd = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="LLM 호출 비용 USD",
    )
    # PR-A2 §3.5: 실패 시 에러 메시지 (status=FAILED일 때 채움)
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_briefing_log"
        verbose_name = "Briefing Log"
        verbose_name_plural = "Briefing Logs"
        unique_together = [("date", "model_version")]
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.date} ({self.model_version}) — {self.status}"
