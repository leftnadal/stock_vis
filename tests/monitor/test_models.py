"""Monitor·Claim 모델 행위 테스트 (MON-P2)."""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.monitor.models import Claim, Monitor

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="mon_user", password="pw12345")


@pytest.mark.django_db
class TestMonitor:
    def test_create_defaults_to_setting_up(self, user):
        m = Monitor.objects.create(
            user=user, scope=Monitor.Scope.STOCK, target_ref="AAPL", name="애플 감시"
        )
        assert m.status == Monitor.Status.SETTING_UP
        assert m.id is not None  # UUID 자동 발급
        assert str(m) == "애플 감시 [stock:AAPL]"

    def test_unique_per_user_scope_target(self, user):
        Monitor.objects.create(
            user=user, scope=Monitor.Scope.STOCK, target_ref="AAPL", name="A"
        )
        with pytest.raises(IntegrityError):
            Monitor.objects.create(
                user=user, scope=Monitor.Scope.STOCK, target_ref="AAPL", name="중복"
            )

    def test_same_target_different_scope_allowed(self, user):
        Monitor.objects.create(
            user=user, scope=Monitor.Scope.STOCK, target_ref="XLK", name="종목 XLK"
        )
        # 같은 참조라도 scope가 다르면 별개 대상 (fund XLK)
        Monitor.objects.create(
            user=user, scope=Monitor.Scope.FUND, target_ref="XLK", name="펀드 XLK"
        )
        assert Monitor.objects.filter(user=user, target_ref="XLK").count() == 2


@pytest.mark.django_db
class TestClaim:
    def test_claim_defaults(self, user):
        m = Monitor.objects.create(
            user=user, scope=Monitor.Scope.STOCK, target_ref="AAPL", name="애플"
        )
        c = Claim.objects.create(monitor=m, assertion="실적 개선으로 반등한다")
        assert c.status == Claim.Status.ACTIVE
        assert c.outcome == Claim.Outcome.PENDING
        assert c.deadline is None

    def test_cascade_delete_with_monitor(self, user):
        m = Monitor.objects.create(
            user=user, scope=Monitor.Scope.STOCK, target_ref="AAPL", name="애플"
        )
        Claim.objects.create(monitor=m, assertion="가설1")
        Claim.objects.create(monitor=m, assertion="가설2")
        assert Claim.objects.count() == 2
        m.delete()
        assert Claim.objects.count() == 0
