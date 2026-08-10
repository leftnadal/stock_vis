"""purge_analog_v1_residual — CL3-V1-RESIDUAL-CLEANUP: cl3_v1 잔존행 삭제(→정직한 null).

배경: REGEN-V2 완주 후 macro-null 기존일 12행이 v2 빈선별/톤가드실패로 예전 v1 filler를
  서빙 유지 중. 카드 read(cards.py)는 버전 무관 date read → 행없음=why=null(else None).
  삭제하면 이 12일이 행없음 5일과 **동형 렌더**(방식 i, why_text는 not-null이라 null화는 마이그 필요).
안전: 날짜 목록 ∧ prompt_version=cl3_v1 **이중 조건**(cl3_v2 구조적 차단). dry-run 기본, --commit 실쓰기.
멱등: 삭제 후 재실행 = 0행(재삭제 무해). 백업=docs/archive/cl3_v1_residual_backup_2026-08.json(선행 커밋).
"""

from __future__ import annotations

import datetime

from django.core.management.base import BaseCommand

from apps.market_pulse.models import AnalogDayContext

# 디렉터 확정 대상 12일(REGEN-V2 사후 스팟체크 실측). prompt_version 이중 조건과 AND.
RESIDUAL_DATES = [
    datetime.date.fromisoformat(s)
    for s in (
        "2023-10-05", "2024-02-09", "2024-10-03", "2025-01-31", "2025-02-25",
        "2025-05-19", "2025-06-11", "2025-12-09", "2025-12-17", "2026-01-15",
        "2026-02-20", "2026-03-06",
    )
]
RESIDUAL_VERSION = "cl3_v1"


class Command(BaseCommand):
    help = "CL3-V1-RESIDUAL: cl3_v1 잔존행 삭제(dry-run 기본, --commit 실쓰기, 이중 조건)"

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true", help="실삭제(기본=dry-run)")

    def handle(self, *args, **opt):
        commit = opt["commit"]
        qs = AnalogDayContext.objects.filter(
            date__in=RESIDUAL_DATES, prompt_version=RESIDUAL_VERSION
        )
        dates = sorted(str(d) for d in qs.values_list("date", flat=True))
        n = len(dates)

        self.stdout.write(
            f"[purge_analog_v1_residual] 대상(date∩cl3_v1) {n}행 · "
            f"{'COMMIT' if commit else 'DRY-RUN'}\n  날짜: {dates}"
        )

        if not commit:
            self.stdout.write("── DRY-RUN (삭제 0). 실삭제는 --commit. 대상이 12가 아니면 실행 금지. ──")
            return

        deleted, per_model = qs.delete()
        self.stdout.write(
            self.style.SUCCESS(f"삭제 완료 — {deleted}행 ({per_model})")
        )
