"""G2 dry-run 관리 명령 (TH-C3-LLM-DICT-1, 3f 종결) — READ-ONLY.

override(ovr_v1) 적용 후 2×2 after-credit tally 를 비변형으로 산출·출력한다.
어떤 원장/코퍼스 쓰기도 하지 않는다 (apps.chain_sight.services.g2_dry_run 참조).

사용:
    python manage.py g2_dry_run                       # date_cut=2026-07-11, gen=ovr_v1
    python manage.py g2_dry_run --date-cut 2026-07-11 --generation ovr_v1
    python manage.py g2_dry_run --json                # 기계 판독용 JSON
"""

import json as _json
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError

from apps.chain_sight.services.g2_dry_run import (
    DEFAULT_DATE_CUT,
    DEFAULT_GENERATION,
    format_report,
    run_g2_dry_run,
)


class Command(BaseCommand):
    help = "G2 dry-run: override 적용 후 2×2 after-credit tally 산출 (읽기 전용, 원장 무접촉)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date-cut",
            default=DEFAULT_DATE_CUT.isoformat(),
            help="동결 코퍼스 상한 (YYYY-MM-DD, 기본 2026-07-11)",
        )
        parser.add_argument(
            "--generation",
            default=DEFAULT_GENERATION,
            help="override 세대 (기본 ovr_v1)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="사람이 읽는 리포트 대신 JSON 출력",
        )

    def handle(self, *args, **opts):
        try:
            cut = datetime.strptime(opts["date_cut"], "%Y-%m-%d").date()
        except ValueError as e:
            raise CommandError(f"--date-cut 형식 오류(YYYY-MM-DD): {e}")

        result = run_g2_dry_run(date_cut=cut, generation=opts["generation"])

        if opts["json"]:
            self.stdout.write(_json.dumps(result, ensure_ascii=False, indent=2))
        else:
            self.stdout.write(format_report(result))
