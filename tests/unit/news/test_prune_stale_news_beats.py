"""prune_stale_news_beats 커맨드 단위 테스트 (Bug #28 / S1).

검증:
    - dry-run (기본) 은 news.tasks.* orphan 을 보고만 하고 삭제하지 않음
    - --apply 는 news.tasks.* 만 삭제하고 services.news.tasks.* 정상 행은 보존 (엄격 한정)
    - 재실행 시 0건 (idempotent)
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django_celery_beat.models import CrontabSchedule, PeriodicTask


def _make_task(name: str, task_path: str) -> PeriodicTask:
    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute="0", hour="6", day_of_week="*", day_of_month="*", month_of_year="*",
    )
    return PeriodicTask.objects.create(
        name=name, task=task_path, crontab=crontab, enabled=True,
    )


@pytest.mark.django_db
def test_dry_run_does_not_delete() -> None:
    _make_task("collect-daily-news", "news.tasks.collect_daily_news")
    out = StringIO()
    call_command("prune_stale_news_beats", stdout=out)
    assert "would delete" in out.getvalue()
    # DB 그대로
    assert PeriodicTask.objects.filter(task__startswith="news.tasks.").count() == 1


@pytest.mark.django_db
def test_apply_deletes_only_stale_prefix() -> None:
    # orphan (죽은 bare 경로)
    _make_task("collect-daily-news", "news.tasks.collect_daily_news")
    _make_task("collect-category-news-medium", "news.tasks.collect_category_news")
    # 정상 행 — 절대 삭제 금지
    _make_task("collect-daily-news-morning", "services.news.tasks.collect_daily_news")

    call_command("prune_stale_news_beats", "--apply", stdout=StringIO())

    assert not PeriodicTask.objects.filter(task__startswith="news.tasks.").exists()
    # 정상 services.news.tasks.* 는 보존
    assert PeriodicTask.objects.filter(
        task="services.news.tasks.collect_daily_news"
    ).exists()


@pytest.mark.django_db
def test_idempotent_second_run_noop() -> None:
    _make_task("collect-daily-news", "news.tasks.collect_daily_news")
    call_command("prune_stale_news_beats", "--apply", stdout=StringIO())
    out = StringIO()
    call_command("prune_stale_news_beats", "--apply", stdout=out)
    assert "orphan 없음" in out.getvalue()
