"""ThemeNewsVolume override 재산출 명령 (TH-C3-LLM-DICT-1 쓰기 3단, 결정35).

override(ovr_v1) 를 ≤date_cut 동결 코퍼스에 반영해 ThemeNewsVolume 을 **forward-only**
재작성한다. 기존 행은 삭제하지 않고(update_or_create), override 제거로 크레딧이 0 이 된
(theme,date) 는 mention_count=0 으로 갱신(zero_missing_existing=True). >date_cut 행 무접촉.

⚠ 실쓰기 명령. 롤백 스냅샷(`docs/chain_sight/theme_heat/tnv_pre_ovr_v1.json`) 확보 후 실행.
개정일 마커는 `heat_history_markers.HISTORY_MARKERS`(ovr_v1_dict_recompute) 에 등재됨.

사용:
    python manage.py recompute_theme_news_override                     # date_cut=2026-07-11
    python manage.py recompute_theme_news_override --date-cut 2026-07-11 --dry-run
"""

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "ThemeNewsVolume override(ovr_v1) 재산출 (≤date_cut, forward-only)"

    def add_arguments(self, parser):
        parser.add_argument("--date-cut", default="2026-07-11", help="동결 코퍼스 상한(YYYY-MM-DD)")
        parser.add_argument("--generation", default="ovr_v1", help="override 세대")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="집계 대상 일수만 보고하고 쓰기 안 함(스코프 확인용)",
        )

    def handle(self, *args, **opts):
        from apps.chain_sight.services.c3_narrative_service import aggregate_theme_news_volume
        from services.news.models import DailyNewsKeyword

        try:
            cut = datetime.strptime(opts["date_cut"], "%Y-%m-%d").date()
        except ValueError as e:
            raise CommandError(f"--date-cut 형식 오류(YYYY-MM-DD): {e}")

        n_days = (
            DailyNewsKeyword.objects.filter(date__lte=cut)
            .exclude(keywords__isnull=True)
            .values("date").distinct().count()
        )
        self.stdout.write(
            f"[recompute] date_cut={cut} generation={opts['generation']} "
            f"코퍼스 대상일수={n_days}"
        )

        if opts["dry_run"]:
            self.stdout.write("dry-run — 쓰기 없음 (스코프만 확인)")
            return

        res = aggregate_theme_news_volume(
            date_lte=cut,
            use_h2=True,
            use_override=True,
            override_generation=opts["generation"],
            zero_missing_existing=True,
        )
        self.stdout.write(
            f"[recompute 완료] days={res['days']} upserted={res['written']} "
            f"zeroed={res['zeroed']} (forward-only, >{cut} 무접촉)"
        )
