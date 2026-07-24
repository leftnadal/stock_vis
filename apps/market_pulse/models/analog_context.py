"""MP2-ANALOG Slice C-L3 — 유사 국면 이웃일 L3 맥락(cached·동결).

소속: apps/market_pulse (app_label='marketpulse').
역할: 모집단일(RegimeSnapshot summary=BACKFILL_MARK·coverage≥1.0)별 "그날 무슨 일이 있었나" 1줄 맥락
  + 근거 헤드라인(provenance). 유사 국면 카드의 이웃 리스트가 date로 lookup해 "왜?" 슬롯을 채운다.
읽기 결정론(D-CL3-READ-DETERMINISTIC): 카드 READ 경로는 이 저장분만 읽는다(렌더 LLM 0).
  생성은 오프라인 커맨드(generate_analog_context) 전용.
동결(D-CL3-FREEZE): date 1회 생성 후 불변. 재생성은 명시 --regenerate + prompt_version 증가로만
  (조용한 덮어쓰기 금지). why=null(생성 실패·헤드라인 0건)은 행을 만들지 않는다(부재=null).
"""

from __future__ import annotations

from django.db import models


class AnalogDayContext(models.Model):
    """모집단일별 L3 맥락(1문장) + provenance. date unique(이웃일 lookup 키)."""

    date = models.DateField(unique=True, db_index=True, help_text="모집단일(이웃일 lookup 키)")
    why_text = models.TextField(help_text="L3 맥락 1문장(한국어, 톤가드 통과분)")
    provenance = models.JSONField(
        default=list, help_text="근거 헤드라인 목록 [{id, url, title}]"
    )
    prompt_version = models.CharField(max_length=20, help_text="생성 프롬프트 버전(동결 태깅)")
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "marketpulse"
        db_table = "mp_analog_day_context"
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.date}: {self.why_text[:40]}"
