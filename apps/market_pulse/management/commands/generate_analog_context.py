"""generate_analog_context — Slice C-L3: 모집단일 L3 맥락 생성(cached·멱등·동결).

대상: RegimeSnapshot summary=BACKFILL_MARK · coverage≥1.0(완전벡터 모집단, ~683일).
동작: 각 date → 그라운딩 선별 → Gemini 1문장 → 톤가드 → AnalogDayContext 저장.
멱등(D-CL3-FREEZE): 기존 생성분 skip. 재생성은 --regenerate + prompt_version 증가로만(조용한 덮어쓰기 금지).
dry-run 기본: 대상 일수·헤드라인 있는/없는 일수·예상 토큰·예상 비용 보고, 쓰기 0. 실쓰기는 --commit.

사용:
    python manage.py generate_analog_context                       # dry-run: 전체 모집단 산정(v1)
    python manage.py generate_analog_context --commit --limit 10   # 소량 검증 생성(≤10일)
    python manage.py generate_analog_context --date 2024-05-06 --commit
    python manage.py generate_analog_context --regenerate --prompt-version cl3_v2 --commit
    # REGEN-V2 전량(683=491 재생성+192 신규): macro 결정론 선별 v2로 균일 재생성
    python manage.py generate_analog_context --select-version v2 --regenerate --commit
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
        parser.add_argument("--prompt-version", default=None, help="프롬프트 버전 태그(미지정=선별버전 기본)")
        parser.add_argument(
            "--select-version", choices=["v1", "v2"], default="v1",
            help="그라운딩 선별기: v1(기본, 기존 경로)|v2(macro 결정론, REGEN-V2)",
        )

    def handle(self, *args, **opt):
        commit = opt["commit"]
        regenerate = opt["regenerate"]
        limit = opt["limit"]
        select_version = opt["select_version"]
        # 버전 태그: 미지정 시 선별버전에 커플링(v2→cl3_v2, v1→PROMPT_VERSION). 명시값 우선.
        prompt_version = opt["prompt_version"] or ("cl3_v2" if select_version == "v2" else PROMPT_VERSION)

        targets = self._resolve_targets(opt)
        if not targets:
            self.stdout.write("대상 모집단일 0 — 종료.")
            return

        # 버전 인지 멱등(REGEN-V2): 비-regenerate는 날짜 기반 skip(v1 IDENTICAL, 조용한 덮어쓰기 0).
        #   --regenerate는 목표 prompt_version과 다른 날만 pending(cl3_v1→cl3_v2 업그레이드 + 재실행 멱등).
        existing = dict(AnalogDayContext.objects.values_list("date", "prompt_version"))
        if regenerate:
            pending = [d for d in targets if existing.get(d) != prompt_version]
        else:
            pending = [d for d in targets if d not in existing]
        skipped_existing = len(targets) - len(pending)
        if limit is not None:
            pending = pending[:limit]

        self.stdout.write(
            f"[generate_analog_context] 모집단 {len(targets)}일 · 기존 {len(existing)} · "
            f"멱등 skip {skipped_existing} · 이번 대상 {len(pending)} · "
            f"select={select_version} · prompt={prompt_version} · {'COMMIT' if commit else 'DRY-RUN'}"
        )

        if not commit:
            self._dry_run_report(pending, select_version)
            return

        created = updated = null_empty = null_tone = 0
        for d in pending:
            grounding_present = bool(context_generator.select(d, select_version))
            out = context_generator.generate_for_date(
                d, prompt_version=prompt_version, select_version=select_version
            )
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

    def _dry_run_report(self, pending: list[datetime.date], select_version: str = "v1") -> None:
        from apps.market_pulse.regime.grounding import GROUNDING_TOP_N
        from apps.market_pulse.regime.grounding_v2 import SELECT_V2_TOP_N

        top_n = SELECT_V2_TOP_N if select_version == "v2" else GROUNDING_TOP_N

        if select_version == "v2":
            # v2 = macro 결정론 선별 → 실제 선별기를 태워 "비어있지 않은 날"을 실측(정확 LLM 호출수).
            #   순수 DB(외부 API 0). macro 신호 없는 날은 [] → why=null(호출 없음).
            sel_counts = {d: len(context_generator.select(d, "v2")) for d in pending}
            with_hl = [d for d in pending if sel_counts[d] > 0]
            per_day_headlines = max((sel_counts[d] for d in with_hl), default=0)
        else:
            from django.db.models import Count

            from services.news.models import NewsArticle

            # v1 = 그날 헤드라인 존재만으로 선별 성립 → date별 헤드라인 수(1쿼리)로 근사(기존 경로 IDENTICAL).
            counts = {
                row["published_at__date"]: row["c"]
                for row in NewsArticle.objects.filter(published_at__date__in=pending)
                .values("published_at__date")
                .annotate(c=Count("id"))
            }
            with_hl = [d for d in pending if counts.get(d, 0) > 0]
            per_day_headlines = min(top_n, max((counts.get(d, 0) for d in with_hl), default=0))

        without_hl = len(pending) - len(with_hl)
        # 토큰 근사: 호출 대상 일수 × (프롬프트 + top-N 헤드라인 + 출력).
        in_tokens = len(with_hl) * (_APPROX_PROMPT_TOKENS + top_n * _APPROX_TOKENS_PER_HEADLINE)
        out_tokens = len(with_hl) * _APPROX_OUTPUT_TOKENS
        cost = in_tokens / 1_000_000 * _REF_INPUT_USD_PER_M + out_tokens / 1_000_000 * _REF_OUTPUT_USD_PER_M

        empty_label = (
            "macro 신호 없음 → why=null 유지, 호출 없음" if select_version == "v2"
            else "why=null 유지, 호출 없음"
        )
        self.stdout.write(
            f"── DRY-RUN 산정 (쓰기 0, select={select_version}) ──\n"
            f"  대상 일수         : {len(pending)}\n"
            f"  헤드라인 있는 일수 : {len(with_hl)} (LLM 호출 대상)\n"
            f"  헤드라인 없는 일수 : {without_hl} ({empty_label})\n"
            f"  예상 LLM 호출     : {len(with_hl)}회 (일당 top-{top_n} 헤드라인, 최대 {per_day_headlines})\n"
            f"  예상 입력 토큰(근사): ~{in_tokens:,}\n"
            f"  예상 출력 토큰(근사): ~{out_tokens:,}\n"
            f"  예상 비용(근사·참고단가): ~${cost:.3f} USD "
            f"(Gemini 2.5 Flash in ${_REF_INPUT_USD_PER_M}/out ${_REF_OUTPUT_USD_PER_M} per 1M, 단가 미확정)\n"
            "  ※ 실쓰기는 --commit. 683 전량은 병진 승인 유보(§5)."
        )
