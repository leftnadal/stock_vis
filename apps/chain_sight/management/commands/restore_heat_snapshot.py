"""ThemeHeatScore 스냅샷 복원(롤백) 명령 (TH-C3-LLM-DICT-1 쓰기 3b 롤백 경로).

heat 재산출(compute_theme_heat)을 되돌린다. 스냅샷 JSON 전행을 **원자적으로 원복**:
현 ThemeHeatScore 전삭제 → 스냅샷(theme,date,score,status,components,evidence) 재삽입.
스냅샷은 재산출 PRE 상태(`docs/chain_sight/theme_heat/ths_pre_3b.json`).

--dry-run: 트랜잭션 안에서 복원 후 cksum 만 출력하고 **rollback**(실제 DB 무변경) = 리허설.
평시(--dry-run 없음): 실제 복원(commit).

사용:
    python manage.py restore_heat_snapshot --file docs/.../ths_pre_3b.json --dry-run
    python manage.py restore_heat_snapshot --file docs/.../ths_pre_3b.json
"""

import hashlib
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


def _cksum_current():
    """현 ThemeHeatScore 정렬 (theme,date,score,status) sha256[:16] + 행수."""
    from apps.chain_sight.models.heat import ThemeHeatScore

    rows = list(
        ThemeHeatScore.objects.select_related("theme")
        .order_by("theme__ref_id", "date")
        .values_list("theme__ref_id", "date", "score", "status")
    )
    payload = [[t, str(d), s, st] for t, d, s, st in rows]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()[:16], len(rows)


class Command(BaseCommand):
    help = "ThemeHeatScore 스냅샷 복원 (heat 재산출 롤백, 전행 원자 원복)"

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="스냅샷 JSON 경로")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="트랜잭션 내 복원 후 cksum만 출력하고 rollback(리허설, DB 무변경)",
        )

    def handle(self, *args, **opts):
        from apps.chain_sight.models import HeatEntity
        from apps.chain_sight.models.heat import ThemeHeatScore

        try:
            snap = json.load(open(opts["file"]))
        except (OSError, json.JSONDecodeError) as e:
            raise CommandError(f"스냅샷 로드 실패: {e}")

        # 스냅샷 = [{theme,date,score,status,components,evidence}, ...]
        want_payload = sorted(
            [[r["theme"], r["date"], r["score"], r["status"]] for r in snap],
            key=lambda x: (x[0], x[1]),
        )
        want_cksum = hashlib.sha256(
            json.dumps(want_payload, ensure_ascii=False).encode()
        ).hexdigest()[:16]

        entities = {e.ref_id: e for e in HeatEntity.objects.filter(kind="sector")}
        self.stdout.write(f"[restore-heat] file={opts['file']} rows={len(snap)}")

        try:
            with transaction.atomic():
                ThemeHeatScore.objects.all().delete()
                objs = [
                    ThemeHeatScore(
                        theme=entities[r["theme"]], date=r["date"],
                        score=r["score"], status=r["status"],
                        components=r["components"], evidence=r["evidence"],
                    )
                    for r in snap
                    if r["theme"] in entities
                ]
                ThemeHeatScore.objects.bulk_create(objs)
                cks, n = _cksum_current()
                match = cks == want_cksum
                self.stdout.write(
                    f"[restore-heat] 복원 후 cksum={cks} (기대={want_cksum}) rows={n} match={match}"
                )
                if not match:
                    raise CommandError(f"복원 cksum 불일치 — rollback (got {cks} != {want_cksum})")
                if opts["dry_run"]:
                    self.stdout.write("dry-run — rollback (DB 무변경, 리허설 성공)")
                    transaction.set_rollback(True)
                else:
                    self.stdout.write("복원 commit 완료")
        except CommandError:
            raise
