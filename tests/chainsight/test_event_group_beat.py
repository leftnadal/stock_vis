"""
C 컴퓨트 beat 태스크 + 등록 명령 테스트 (Slice C).

검증:
- compute_event_group_leadership_daily: 그룹 재적재 → C leadership 순서 오케스트레이션.
- 가격 없으면 leadership_rows=0(에러 아님).
- register_chainsight_beats: C 컴퓨트 beat가 attention(22:30)보다 앞선 22:15에 등록.
"""

from datetime import date
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command


class TestDailyTask:
    @patch("apps.chain_sight.tasks.event_group_tasks.compute_eventgroup_leadership_scores")
    @patch("apps.chain_sight.tasks.event_group_tasks.load_event_groups")
    @patch("apps.chain_sight.tasks.event_group_tasks.DailyPrice")
    def test_orchestration_order(self, m_price, m_groups, m_lead):
        from apps.chain_sight.tasks.event_group_tasks import (
            compute_event_group_leadership_daily,
        )
        m_groups.return_value = {"groups": 9, "kept": 9}
        m_price.objects.aggregate.return_value = {"m": date(2026, 6, 26)}
        m_lead.return_value = 114

        result = compute_event_group_leadership_daily()

        # 그룹 먼저, 그다음 leadership(최신 가격일)
        m_groups.assert_called_once()
        m_lead.assert_called_once_with(date(2026, 6, 26))
        assert result["leadership_rows"] == 114
        assert result["as_of"] == "2026-06-26"

    @patch("apps.chain_sight.tasks.event_group_tasks.compute_eventgroup_leadership_scores")
    @patch("apps.chain_sight.tasks.event_group_tasks.load_event_groups")
    @patch("apps.chain_sight.tasks.event_group_tasks.DailyPrice")
    def test_no_price_returns_zero(self, m_price, m_groups, m_lead):
        from apps.chain_sight.tasks.event_group_tasks import (
            compute_event_group_leadership_daily,
        )
        m_groups.return_value = {"groups": 0}
        m_price.objects.aggregate.return_value = {"m": None}

        result = compute_event_group_leadership_daily()
        assert result["leadership_rows"] == 0
        m_lead.assert_not_called()  # 가격 없으면 leadership 미호출


@pytest.mark.django_db
class TestBeatRegistration:
    def test_dry_run_lists_eg_leadership_beat_before_attention(self):
        out = StringIO()
        call_command("register_chainsight_beats", "--dry-run", stdout=out)
        text = out.getvalue()
        assert "chainsight-event-group-leadership-daily" in text
        assert "22:15" in text  # attention 22:30보다 앞

    def test_register_creates_eg_leadership_periodic_task(self):
        from django_celery_beat.models import PeriodicTask

        call_command("register_chainsight_beats")
        t = PeriodicTask.objects.get(name="chainsight-event-group-leadership-daily")
        assert t.task == "chainsight-event-group-leadership-daily"
        assert t.enabled is True
        assert t.crontab.hour == "22" and t.crontab.minute == "15"
        assert t.crontab.day_of_week == "1-5"
