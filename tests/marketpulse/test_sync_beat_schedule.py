"""sync_beat_schedule reconcile 커맨드 단위 테스트.

검증:
    - dry-run (기본) 이 옛→새 diff 를 정확히 산출하고 DB 를 건드리지 않음
    - --apply 후 row 가 dict 값으로 갱신됨
    - 재실행 시 0 rows (idempotent)
    - dict 에 없는 name 은 변경하지 않음 (extra DB rows 보존)
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django_celery_beat.models import CrontabSchedule, PeriodicTask


def _make_task(name: str, task_path: str) -> PeriodicTask:
    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="*",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
    )
    return PeriodicTask.objects.create(
        name=name,
        task=task_path,
        crontab=crontab,
        enabled=False,
    )


@pytest.mark.django_db
def test_dry_run_reports_diff_without_writing(settings) -> None:
    """dry-run 은 변경 사항만 출력하고 DB row 는 그대로."""
    _make_task("update-economic-indicators", "macro.tasks.update_economic_indicators")

    out = StringIO()
    call_command("sync_beat_schedule", stdout=out)
    output = out.getvalue()

    assert "update-economic-indicators" in output
    assert "macro.tasks.update_economic_indicators" in output
    assert "apps.market_pulse.tasks.macro.update_economic_indicators" in output
    assert "[dry-run]" in output

    # DB 는 변경되지 않음
    actual = PeriodicTask.objects.get(name="update-economic-indicators").task
    assert actual == "macro.tasks.update_economic_indicators"


@pytest.mark.django_db
def test_apply_updates_then_idempotent() -> None:
    """--apply 후 row 갱신, 재실행은 0 rows."""
    _make_task("update-economic-indicators", "macro.tasks.update_economic_indicators")
    _make_task("update-market-indices", "macro.tasks.update_market_indices")

    out = StringIO()
    call_command("sync_beat_schedule", "--apply", stdout=out)
    output = out.getvalue()
    assert "2 rows updated" in output

    assert (
        PeriodicTask.objects.get(name="update-economic-indicators").task
        == "apps.market_pulse.tasks.macro.update_economic_indicators"
    )
    assert (
        PeriodicTask.objects.get(name="update-market-indices").task
        == "apps.market_pulse.tasks.macro.update_market_indices"
    )

    # 두 번째 실행 = idempotent (0 rows)
    out2 = StringIO()
    call_command("sync_beat_schedule", stdout=out2)
    assert "동기화 필요 없음" in out2.getvalue()


@pytest.mark.django_db
def test_extra_db_rows_left_untouched() -> None:
    """dict 에 없는 name 은 정보 출력만, UPDATE 하지 않음."""
    _make_task("custom-only-in-db", "some.legacy.task.path")

    out = StringIO()
    call_command("sync_beat_schedule", "--apply", stdout=out)
    output = out.getvalue()

    assert "custom-only-in-db" in output
    assert "dict 에 없는" in output

    # 보존됨
    assert (
        PeriodicTask.objects.get(name="custom-only-in-db").task
        == "some.legacy.task.path"
    )


@pytest.mark.django_db
def test_dict_entries_missing_in_db_are_reported_not_created() -> None:
    """dict 에 있지만 DB 에 없는 schedule 은 경고만, 생성 안 함."""
    # 빈 DB 상태에서 실행 → schedule dict 의 모든 name 이 missing_db
    out = StringIO()
    call_command("sync_beat_schedule", stdout=out)
    output = out.getvalue()

    assert "DB 에 없는 schedule" in output
    # 아무 row 도 생성되지 않음
    assert PeriodicTask.objects.count() == 0
