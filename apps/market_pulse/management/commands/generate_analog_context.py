"""generate_analog_context — Slice C-L3: 모집단일 L3 맥락 생성(cached·멱등·동결).

대상: RegimeSnapshot summary=BACKFILL_MARK · coverage≥1.0(완전벡터 모집단, ~683일).
동작: 각 date → 그라운딩 선별 → Gemini 1문장 → 톤가드 → AnalogDayContext 저장.
멱등(D-CL3-FREEZE): 기존 생성분 skip. 재생성은 --regenerate + prompt_version 증가로만(조용한 덮어쓰기 금지).
dry-run 기본: 대상 일수·헤드라인 있는/없는 일수·예상 토큰·예상 비용 보고, 쓰기 0. 실쓰기는 --commit.

사용:
    python manage.py generate_analog_context                       # dry-run: 전체 모집단 산정
    python manage.py generate_analog_context --commit --limit 10   # 소량 검증 생성(≤10일)
    python manage.py generate_analog_context --date 2024-05-06 --commit
    python manage.py generate_analog_context --regenerate --prompt-version cl3_v2 --commit
"""

from __future__ import annotations

import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.market_pulse.llm.analog_context_prompt import PROMPT_VERSION
from apps.market_pulse.management.commands.backfill_v2_regime_vectors import BACKFILL_MARK
from apps.market_pulse.models import AnalogDayContext, RegimeSnapshot
from apps.market_pulse.regime import context_generator

# dry-run 토큰 근사(count_tokens 미사용 — 대략치). 참고용, 정밀 아님.
_APPROX_PROMPT_TOKENS = 220          # system_instruction 고정분 근사
_APPROX_TOKENS_PER_HEADLINE = 18     # 제목 1개 근사
_APPROX_OUTPUT_TOKENS = 40           # 한국어 1문장 근사
# Gemini 2.5 Flash 참고 단가(USD/1M, 변동 가능 — 단일출처 부재[translation.py]). 비용은 근사.
_REF_INPUT_USD_PER_M = 0.30
_REF_OUTPUT_USD_PER_M = 2.50


class Command(BaseCommand):
    help = "C-L3: 모집단일 L3 맥락 생성(dry-run 기본, --commit 실쓰기, 멱등·동결)"

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true", help="실쓰기(기본=dry-run)")
        parser.add_argument("--date", help="단일일 생성 YYYY-MM-DD")
        parser.add_argument("--from", dest="from_date", help="시작일 YYYY-MM-DD(포함)")
        parser.add_argument("--to", dest="to_date", help="종료일 YYYY-MM-DD(포함)")
        parser.add_argument("--regenerate", action="store_true", help="기존 생성분 덮어쓰기(+버전 증가)")
        parser.add_argument("--limit", type=int, help="처리 상한(소량 검증용)")
        parser.add_argument("--prompt-version", default=PROMPT_VERSION, help="프롬프트 버전 태그")

    def handle(self, *args, **opt):
        commit = opt["commit"]
        regenerate = opt["regenerate"]
        limit = opt["limit"]
        prompt_version = opt["prompt_version"]

        targets = self._resolve_targets(opt)
        if not targets:
            self.stdout.write("대상 모집단일 0 — 종료.")
            return

        existing = set(AnalogDayContext.objects.values_list("date", flat=True))
        pending = targets if regenerate else [d for d in targets if d not in existing]
        skipped_existing = 0 if regenerate else len(targets) - len(pending)
        if limit is not None:
            pending = pending[:limit]

        self.stdout.write(
            f"[generate_analog_context] 모집단 {len(targets)}일 · 기존 {len(existing)} · "
            f"멱등 skip {skipped_existing} · 이번 대상 {len(pending)} · "
            f"prompt={prompt_version} · {'COMMIT' if commit else 'DRY-RUN'}"
        )

        if not commit:
            self._dry_run_report(pending)
            return

        created = updated = null_empty = null_tone = 0
        for d in pending:
            grounding_present = bool(context_generator.select_grounding(d))
            out = context_generator.generate_for_date(d, prompt_version=prompt_version)
            if out is None:
                if grounding_present:
                    null_tone += 1  # 헤드라인은 있었으나 톤가드 재실패
                else:
                    null_empty += 1  # 그날 헤드라인 0건
                continue
            _, was_created = AnalogDayContext.objects.update_or_create(date=d, defaults=out)
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"완료 — 생성 {created} · 갱신 {updated} · "
                f"null(헤드라인0) {null_empty} · null(톤가드실패) {null_tone}"
            )
        )

    # ── 대상 산정 ──

    def _resolve_targets(self, opt) -> list[datetime.date]:
        qs = RegimeSnapshot.objects.filter(summary=BACKFILL_MARK, coverage__gte=1.0)
        if opt["date"]:
            d = self._parse(opt["date"])
            return list(qs.filter(date=d).values_list("date", flat=True))
        if opt["from_date"]:
            qs = qs.filter(date__gte=self._parse(opt["from_date"]))
        if opt["to_date"]:
            qs = qs.filter(date__lte=self._parse(opt["to_date"]))
        return list(qs.order_by("date").values_list("date", flat=True))

    @staticmethod
    def _parse(s: str) -> datetime.date:
        try:
            return datetime.date.fromisoformat(s)
        except ValueError as exc:
            raise CommandError(f"날짜 형식 오류(YYYY-MM-DD): {s}") from exc

    # ── dry-run 산정(쓰기 0) ──

    def _dry_run_report(self, pending: list[datetime.date]) -> None:
        from django.db.models import Count

        from services.news.models import NewsArticle

        # date별 헤드라인 수(1쿼리, is_archived 무필터 — 그라운딩과 동형).
        counts = {
            row["published_at__date"]: row["c"]
            for row in NewsArticle.objects.filter(published_at__date__in=pending)
            .values("published_at__date")
            .annotate(c=Count("id"))
        }
        with_hl = [d for d in pending if counts.get(d, 0) > 0]
        without_hl = len(pending) - len(with_hl)
        # 토큰 근사: 헤드라인 있는 일수 × (프롬프트 + top-N 헤드라인 + 출력).
        from apps.market_pulse.regime.grounding import GROUNDING_TOP_N

        per_day_headlines = min(GROUNDING_TOP_N, max((counts.get(d, 0) for d in with_hl), default=0))
        in_tokens = len(with_hl) * (_APPROX_PROMPT_TOKENS + GROUNDING_TOP_N * _APPROX_TOKENS_PER_HEADLINE)
        out_tokens = len(with_hl) * _APPROX_OUTPUT_TOKENS
        cost = in_tokens / 1_000_000 * _REF_INPUT_USD_PER_M + out_tokens / 1_000_000 * _REF_OUTPUT_USD_PER_M

        self.stdout.write(
            "── DRY-RUN 산정 (쓰기 0) ──\n"
            f"  대상 일수         : {len(pending)}\n"
            f"  헤드라인 있는 일수 : {len(with_hl)} (LLM 호출 대상)\n"
            f"  헤드라인 없는 일수 : {without_hl} (why=null 유지, 호출 없음)\n"
            f"  예상 LLM 호출     : {len(with_hl)}회 (일당 top-{GROUNDING_TOP_N} 헤드라인, 최대 {per_day_headlines})\n"
            f"  예상 입력 토큰(근사): ~{in_tokens:,}\n"
            f"  예상 출력 토큰(근사): ~{out_tokens:,}\n"
            f"  예상 비용(근사·참고단가): ~${cost:.3f} USD "
            f"(Gemini 2.5 Flash in ${_REF_INPUT_USD_PER_M}/out ${_REF_OUTPUT_USD_PER_M} per 1M, 단가 미확정)\n"
            "  ※ 실쓰기는 --commit. 683 전량은 병진 승인 유보(§5)."
        )
