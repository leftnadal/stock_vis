"""ThemeNewsVolume 스냅샷 복원(롤백) 명령 (TH-C3-LLM-DICT-1 쓰기 3단 롤백 경로).

재산출(recompute_theme_news_override) 을 되돌린다. 스냅샷 JSON 의 (theme,date,mention_count)
로 **스냅샷 범위(≤max_date) 를 원자적으로 원복**: 그 범위 현 행 삭제 → 스냅샷 재삽입.
스냅샷은 재산출 PRE 상태(`docs/chain_sight/theme_heat/tnv_pre_ovr_v1.json`).

--dry-run: 트랜잭션 안에서 복원 후 cksum 만 출력하고 **rollback**(실제 DB 무변경) = 리허설.
평시(--dry-run 없음): 실제 복원(commit). 스냅샷 밖(>max_date) 행은 무접촉.

사용:
    python manage.py restore_theme_news_snapshot --file docs/.../tnv_pre_ovr_v1.json --dry-run
    python manage.py restore_theme_news_snapshot --file docs/.../tnv_pre_ovr_v1.json
"""

import hashlib
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


def _cksum_current(max_date):
    """현 ThemeNewsVolume(≤max_date) 정렬 (theme,date,mention_count) sha256[:16]."""
    from apps.chain_sight.models.heat import ThemeNewsVolume

    rows = list(
        ThemeNewsVolume.objects.filter(date__lte=max_date)
        .values_list("theme__ref_id", "date", "mention_count")
        .order_by("theme__ref_id", "date")
    )
    payload = [[t, str(d), c] for t, d, c in rows]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()[:16], len(rows)


class Command(BaseCommand):
    help = "ThemeNewsVolume 스냅샷 복원 (재산출 롤백, ≤스냅샷 max_date 범위 원자 원복)"

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="스냅샷 JSON 경로")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="트랜잭션 내 복원 후 cksum만 출력하고 rollback(리허설, DB 무변경)",
        )

    def handle(self, *args, **opts):
        from apps.chain_sight.models import HeatEntity
        from apps.chain_sight.models.heat import ThemeNewsVolume

        try:
            snap = json.load(open(opts["file"]))
        except (OSError, json.JSONDecodeError) as e:
            raise CommandError(f"스냅샷 로드 실패: {e}")

        # 스냅샷 payload = [[ref_id, 'YYYY-MM-DD', mention_count], ...]
        snap_payload = [[r[0], r[1], r[2]] for r in snap]
        max_date = max(r[1] for r in snap_payload)
        want_cksum = hashlib.sha256(
            json.dumps(sorted(snap_payload, key=lambda x: (x[0], x[1])), ensure_ascii=False).encode()
        ).hexdigest()[:16]

        entities = {e.ref_id: e for e in HeatEntity.objects.filter(kind="sector")}
        self.stdout.write(f"[restore] file={opts['file']} rows={len(snap_payload)} max_date={max_date}")

        try:
            with transaction.atomic():
                # 스냅샷 범위 현 행 삭제 → 스냅샷 재삽입 (원자적 원복)
                ThemeNewsVolume.objects.filter(date__lte=max_date).delete()
                objs = [
                    ThemeNewsVolume(theme=entities[ref], date=d, mention_count=c)
                    for ref, d, c in snap_payload
                    if ref in entities
                ]
                ThemeNewsVolume.objects.bulk_create(objs)
                cks, n = _cksum_current(max_date)
                match = cks == want_cksum
                self.stdout.write(
                    f"[restore] 복원 후 cksum={cks} (기대={want_cksum}) rows={n} match={match}"
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
