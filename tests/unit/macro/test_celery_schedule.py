"""
Celery Beat 스케줄 설정 테스트

검증 항목:
  - update-economic-indicators: 평일 4회/일 (6,12,18,22시)
"""

from config.celery import app


class TestEconomicIndicatorSchedule:
    """거시경제 지표 스케줄 최적화 검증"""

    def test_schedule_exists(self):
        """update-economic-indicators 스케줄 존재"""
        assert 'update-economic-indicators' in app.conf.beat_schedule

    def test_schedule_hours(self):
        """평일 6, 12, 18, 22시에만 실행"""
        schedule = app.conf.beat_schedule['update-economic-indicators']['schedule']
        assert schedule.hour == {6, 12, 18, 22}

    def test_schedule_weekdays_only(self):
        """평일만 (월~금)"""
        schedule = app.conf.beat_schedule['update-economic-indicators']['schedule']
        assert schedule.day_of_week == {1, 2, 3, 4, 5}

    def test_schedule_on_the_hour(self):
        """정각에 실행"""
        schedule = app.conf.beat_schedule['update-economic-indicators']['schedule']
        assert schedule.minute == {0}
