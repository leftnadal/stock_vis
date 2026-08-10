"""ADVISOR 브리핑 수동 트리거 (MON-P4-LA §7 실호출 검증 + 운영 수동 실행).

`--dry-run`: build_context + 프롬프트 v1 렌더까지만(LLM 호출·저장 없음 — 프롬프트 검수용).
기본: 실제 LLM 호출 → AdvisorNote 저장(멱등·lexical 가드·실패 무음은 서비스가 처리).
`ADVISOR_ENABLED` 플래그와 무관하게 실행한다(수동 트리거이므로) — beat 자동 발화만 이중잠금.
"""
from django.core.management.base import BaseCommand

from apps.monitor.models import Monitor
from apps.monitor.services import advisor_briefing as svc


class Command(BaseCommand):
    help = "ADVISOR L-A 브리핑 수동 실행 (실호출 또는 --dry-run 프롬프트 검수)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbol", help="단일 종목(target_ref). 미지정 시 전체 stock 모니터."
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="build_context + 프롬프트만 출력(LLM 호출·저장 없음).",
        )

    def handle(self, *args, **options):
        sym = options.get("symbol")
        dry = options["dry_run"]

        qs = Monitor.objects.filter(scope=Monitor.Scope.STOCK)
        if sym:
            qs = qs.filter(target_ref=sym.upper())
        if not qs.exists():
            self.stdout.write(self.style.WARNING(f"대상 모니터 없음 (symbol={sym})"))
            return

        for monitor in qs:
            ctx = svc.build_context(monitor)
            if ctx is None:
                self.stdout.write(f"{monitor.target_ref}: 스냅샷 없음 — 스킵")
                continue

            if dry:
                unchanged = svc.is_unchanged(ctx, monitor)
                prompt = svc._render_user_prompt(ctx, unchanged)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n===== {monitor.target_ref} (dry-run · unchanged={unchanged}) ====="
                    )
                )
                self.stdout.write(f"[커버리지] {ctx['coverage_n']}/{ctx['coverage_total']}")
                self.stdout.write("[SYSTEM PROMPT v1]\n" + svc.SYSTEM_PROMPT_V1)
                self.stdout.write("\n[USER PROMPT]\n" + prompt)
                continue

            note = svc.generate_briefing(monitor)
            if note is not None:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{monitor.target_ref}: 브리핑 생성 asof={note.asof} "
                        f"n/총={note.coverage_n}/{note.coverage_total} "
                        f"model={note.model_id} tokens={note.input_tokens}/{note.output_tokens}"
                    )
                )
                self.stdout.write(f"  headline: {note.headline}")
                self.stdout.write(f"  body: {note.body}")
            else:
                self.stdout.write(
                    f"{monitor.target_ref}: 미생성(스냅샷 없음·멱등 스킵·가드 거부·LLM 실패 중 하나 — 로그 확인)"
                )
