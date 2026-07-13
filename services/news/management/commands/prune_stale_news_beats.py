"""
prune_stale_news_beats — 죽은 모듈 경로를 가리키는 orphan 뉴스 beat 정리 (Bug #28).

monorepo 이관(`news` → `services.news`) 이전에 등록된 PeriodicTask 중, task 경로가
**bare `news.tasks.*`**(현존하지 않는 모듈)를 가리키는 orphan 행이 DB에 잔존한다.
이들은:
  - config/celery.py의 beat_schedule dict에 **없다**(dict는 전부 `services.news.tasks.*`)
    → DatabaseScheduler startup/주기 sync가 부활시키지 않는다(#28 재정정: 비-dict DB
      엔트리는 sync가 삭제·변경하지 않으므로 dict 부재 = 부활 없음).
  - 참조 모듈 `news.tasks`가 존재하지 않아 dispatch되면 worker가 "unregistered task"로
    처리(#33 패턴) → 실질 작업 0, 로그 노이즈만 유발.
  - 정상 경로(`services.news.tasks.collect_daily_news` 등)와 이름·시각이 겹쳐 이중 등록처럼
    보이는 혼선 원천.

따라서 **DB에서만** 삭제한다(D-AVBEAT-DB-ONLY 일관: 스케줄 진실은 DB, 코드/dict는 건드리지
않음). 삭제 대상은 task 경로가 `news.tasks.` 로 시작하는 행으로 **엄격 한정**한다
(정상 `services.news.tasks.*`, 이름-as-task alias 행 등은 절대 건드리지 않음).

사용:
    python manage.py prune_stale_news_beats           # dry-run (삭제 계획만)
    python manage.py prune_stale_news_beats --apply    # 실제 삭제
    # --apply 후 별도 재시작 불요: DatabaseScheduler가 다음 sync tick에 스케줄 reload.
"""

from django.core.management.base import BaseCommand

# 죽은 pre-monorepo 모듈 경로 접두. 이 접두로 시작하는 task만 삭제(엄격 한정).
STALE_TASK_PREFIX = "news.tasks."


class Command(BaseCommand):
    help = "죽은 모듈(news.tasks.*)을 가리키는 orphan 뉴스 PeriodicTask를 DB에서 정리."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="실제 삭제 수행. 기본은 dry-run (삭제 계획만 출력).",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        # import는 handle 안에서(django_celery_beat 미설치 환경 대비)
        from django_celery_beat.models import PeriodicTask

        stale = PeriodicTask.objects.filter(task__startswith=STALE_TASK_PREFIX)
        count = stale.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("orphan 없음 (news.tasks.* 0건). 정리 불요."))
            return

        for pt in stale:
            self.stdout.write(
                f"  {'[dry-run] would delete' if not apply_changes else 'deleting'}: "
                f"id={pt.id} name={pt.name} task={pt.task} "
                f"enabled={pt.enabled} last_run={pt.last_run_at} total_run={pt.total_run_count}"
            )

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(f"dry-run: {count}건 삭제 대상. 실제 삭제는 --apply.")
            )
            return

        deleted, _ = stale.delete()
        self.stdout.write(self.style.SUCCESS(f"삭제 완료: PeriodicTask {count}건 (rows={deleted})."))
        self.stdout.write(
            "  DatabaseScheduler가 다음 sync tick에 스케줄 reload — beat 재시작 불요."
        )
