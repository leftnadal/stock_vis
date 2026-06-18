"""
LLM 감각 유추(번역) 모델 (Phase 1.5 Translation Layer S2).

소속: apps/market_pulse/models (app 레이어 Django models).
역할: TranslationLog — 1회 Gemini 호출이 만든 **카드별 감각 유추 문장 전부**를
  하루 1행에 담는 그릇. BriefingLog 미러(별도 translations envelope, 기존 테이블 무변경).
주요 심볼:
  - TranslationLog: date·model_version·status·senses(JSON)·prompt_inputs(JSON)·
    토큰/비용/지연·created_at.
소비처: tasks(S3) 적재, envelope serializer(S4)에서 카드별 감각 문장 노출.

설계 메모(BriefingLog 미러 정합):
  - 토큰은 Brief와 동일하게 `prompt_tokens`/`completion_tokens` **분리 정수 필드**
    (JSON 단일 필드 아님 — 2026-06-18 사용자 결정, 미러 정확도).
  - 타임스탬프는 Brief와 동일하게 `created_at`만(updated_at 미보유 — 사용자 결정).
  - 기존 모델로의 FK 없음(decouple) — prompt_inputs JSON으로 입력 스냅샷만 담아
    기존 테이블 변경 0을 보장한다.
  - status는 S2 범위에서 OK/REFUSED만(부분 실패 표현은 S3에서 논의).
"""

from django.db import models


class TranslationLog(models.Model):
    class Status(models.TextChoices):
        OK = "OK", "OK"
        REFUSED = "REFUSED", "LLM Refused"

    date = models.DateField(db_index=True)
    model_version = models.CharField(max_length=50, default="gemini-2.5-flash")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OK)

    # {card_key: sense_text} — 카드 키 정의는 S3, 여기선 자유 dict(빈 dict 기본)
    senses = models.JSONField(default=dict, blank=True)

    # 추적용 — 무엇을 LLM에 넣었나(밴드/raw 스냅샷 등). Brief 미러.
    prompt_inputs = models.JSONField(default=dict, blank=True)

    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)

    # LLM 비용 추적 (USD) — BriefingLog 동일 타입.
    cost_usd = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="LLM 호출 비용 USD",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_translation_log"
        verbose_name = "Translation Log"
        verbose_name_plural = "Translation Logs"
        unique_together = [("date", "model_version")]
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.date} ({self.model_version}) — {self.status}"
