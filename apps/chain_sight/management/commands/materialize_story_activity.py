"""MIG-BUNDLE-1 C-2/L-3: co-mention 활동 캐시 물질화 수동 실행.

beat 등록(병진 수동) 전 1회 수동 적재·검증용. 태스크와 동일 코어 호출(중복 없음).

사용:
  python manage.py materialize_story_activity
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "SymbolStoryActivity 캐시를 전 종목 물질화(태스크 코어 1회 실행)."

    def handle(self, *args, **opts):
        from apps.chain_sight.tasks.story_activity_tasks import (
            materialize_story_activity,
        )

        self.stdout.write("[materialize] co-mention 활동 캐시 물질화 시작...")
        r = materialize_story_activity()
        self.stdout.write(
            self.style.SUCCESS(
                f"  완료: 대상 {r['candidates']}종목 → 물질화 {r['symbols']}종목 / {r['rows']}행."
            )
        )
