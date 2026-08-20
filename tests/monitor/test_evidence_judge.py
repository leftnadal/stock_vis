"""ClaimEvidence 일일 생사 판정 서비스 검증 (RECON-SWAP-0813 PART 1).

D-FIXTURE-FIXED-BASE 준수: 시계열 픽스처(readings)는 고정 base로 as_of에 정합
(now 앵커 금지 — coverage time-bomb 재발 방지, add_readings(base=) 활용).
"""
from datetime import date, datetime, timedelta

import pytest
from django.utils import timezone

from apps.monitor.models import Claim, ClaimEvidence
from apps.monitor.services import evidence_judge as svc

# readings 앵커 — as_of 판정에 정합된 고정 시각(그때그때 실제 오늘이 아님).
_BASE = timezone.make_aware(datetime(2026, 8, 10, 12, 0))
_AS_OF = _BASE.date()  # 2026-08-10


@pytest.fixture
def claim(monitor):
    return Claim.objects.create(monitor=monitor, assertion="애플 강세 지속")


def _fake_score_factory(violation_dates, insufficient_dates=frozenset()):
    """score_indicator_dispatch 대역 — 날짜별 raw_z/is_sufficient을 결정론적으로 통제."""

    def _fake(indicator, as_of_date=None):
        if as_of_date in insufficient_dates:
            return {"is_sufficient": False, "raw_z": None}
        raw_z = -1.0 if as_of_date in violation_dates else 1.0
        return {"is_sufficient": True, "raw_z": raw_z}

    return _fake


@pytest.mark.django_db
class TestJudgeAutoEvidence:
    def test_indicator_none_is_unknown(self, claim):
        ev = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=None, operator=ClaimEvidence.Operator.GTE, threshold=0.3,
        )
        results = svc.judge_claim_evidences(claim, as_of_date=_AS_OF)
        assert results == [
            {"evidence_id": ev.id, "kind": ClaimEvidence.Kind.AUTO,
             "status": svc.UNKNOWN, "dead_streak_days": 0}
        ]

    def test_insufficient_data_is_unknown(self, claim, make_indicator, add_readings, monkeypatch):
        ind = make_indicator(window=10)
        add_readings(ind, [float(i) for i in range(10)], base=_BASE)
        ev = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE, threshold=0.3,
        )
        monkeypatch.setattr(
            svc, "score_indicator_dispatch",
            _fake_score_factory(violation_dates=set(), insufficient_dates={_AS_OF}),
        )
        results = svc.judge_claim_evidences(claim, as_of_date=_AS_OF)
        assert results[0]["status"] == svc.UNKNOWN
        assert results[0]["dead_streak_days"] == 0

    def test_compliant_today_is_alive_real_scoring(self, claim, make_indicator, add_readings):
        # 실제 score_indicator_dispatch 배선 검증 — mock 없이 진짜 로직.
        # 상승 시계열의 최신값은 창구간 내 최고치라 z>0, threshold=0.0(gte) 위반 아님.
        ind = make_indicator(window=10)
        add_readings(ind, [float(i) for i in range(10)], base=_BASE)
        ev = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE, threshold=0.0, grace_days=5,
        )
        results = svc.judge_claim_evidences(claim, as_of_date=_AS_OF)
        assert results[0]["status"] == svc.ALIVE
        assert results[0]["dead_streak_days"] == 0

    def test_violation_within_grace_is_alive(self, claim, make_indicator, add_readings, monkeypatch):
        ind = make_indicator(window=10)
        add_readings(ind, [float(i) for i in range(8)], base=_BASE)
        ev = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE, threshold=0.3, grace_days=5,
        )
        # 최근 3거래일(포함 as_of)만 위반, 그 이전은 충족 — streak=3 <= grace_days=5.
        violation_dates = {_AS_OF, _AS_OF - timedelta(days=1), _AS_OF - timedelta(days=2)}
        monkeypatch.setattr(
            svc, "score_indicator_dispatch", _fake_score_factory(violation_dates)
        )
        results = svc.judge_claim_evidences(claim, as_of_date=_AS_OF)
        assert results[0]["status"] == svc.ALIVE
        assert results[0]["dead_streak_days"] == 3

    def test_violation_exceeds_grace_is_dead(self, claim, make_indicator, add_readings, monkeypatch):
        ind = make_indicator(window=10)
        add_readings(ind, [float(i) for i in range(8)], base=_BASE)
        ev = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE, threshold=0.3, grace_days=2,
        )
        # 최근 4거래일 연속 위반 — streak=4 > grace_days=2.
        violation_dates = {
            _AS_OF, _AS_OF - timedelta(days=1),
            _AS_OF - timedelta(days=2), _AS_OF - timedelta(days=3),
        }
        monkeypatch.setattr(
            svc, "score_indicator_dispatch", _fake_score_factory(violation_dates)
        )
        results = svc.judge_claim_evidences(claim, as_of_date=_AS_OF)
        assert results[0]["status"] == svc.DEAD
        assert results[0]["dead_streak_days"] == 4

    def test_streak_stops_at_first_non_violation_from_latest(
        self, claim, make_indicator, add_readings, monkeypatch
    ):
        # 위반-충족-위반 패턴이어도 최신일 기준 연속만 카운트(중간 과거 위반은 무시).
        ind = make_indicator(window=10)
        add_readings(ind, [float(i) for i in range(8)], base=_BASE)
        ev = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE, threshold=0.3, grace_days=5,
        )
        violation_dates = {_AS_OF, _AS_OF - timedelta(days=3)}  # 사이 1,2일은 충족
        monkeypatch.setattr(
            svc, "score_indicator_dispatch", _fake_score_factory(violation_dates)
        )
        results = svc.judge_claim_evidences(claim, as_of_date=_AS_OF)
        assert results[0]["dead_streak_days"] == 1
        assert results[0]["status"] == svc.ALIVE


@pytest.mark.django_db
class TestJudgeManualEvidence:
    def test_within_recheck_period_is_alive(self, claim):
        ev = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.MANUAL,
            description="AI 인프라 테마 열기 지속",
            recheck_period_days=90,
            last_confirmed_at=_AS_OF - timedelta(days=30),
        )
        results = svc.judge_claim_evidences(claim, as_of_date=_AS_OF)
        assert results == [
            {"evidence_id": ev.id, "kind": ClaimEvidence.Kind.MANUAL,
             "status": svc.ALIVE, "dead_streak_days": 0}
        ]

    def test_past_recheck_period_is_expired(self, claim):
        confirmed = _AS_OF - timedelta(days=120)
        ev = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.MANUAL,
            description="AI 인프라 테마 열기 지속",
            recheck_period_days=90,
            last_confirmed_at=confirmed,
        )
        results = svc.judge_claim_evidences(claim, as_of_date=_AS_OF)
        assert results[0]["status"] == svc.EXPIRED
        assert results[0]["dead_streak_days"] == (_AS_OF - confirmed).days

    def test_boundary_exact_due_date_is_alive(self, claim):
        # due == as_of(경과가 아직 아님) → alive. spec: "< as_of"만 expired.
        confirmed = _AS_OF - timedelta(days=90)
        ev = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.MANUAL,
            description="근거", recheck_period_days=90, last_confirmed_at=confirmed,
        )
        results = svc.judge_claim_evidences(claim, as_of_date=_AS_OF)
        assert results[0]["status"] == svc.ALIVE

    def test_null_last_confirmed_at_falls_back_to_created_at(self, claim):
        # 설계 판단: last_confirmed_at 미기입 시 created_at을 기준일로 사용(문서화 대상).
        ev = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.MANUAL,
            description="근거", recheck_period_days=10, last_confirmed_at=None,
        )
        # auto_now_add로 찍힌 실제 created_at을 고정 과거값으로 덮어써 결정론화(update()는
        # auto_now_add를 우회 — .save() 재호출이 아니므로 필드가 그대로 적용됨).
        fixed_created = timezone.make_aware(datetime(2026, 1, 1, 0, 0))
        ClaimEvidence.objects.filter(pk=ev.pk).update(created_at=fixed_created)
        ev.refresh_from_db()
        baseline = ev.created_at.date()  # TZ 왕복 후 실제 저장된 날짜(로컬 변환 오차 방지)

        as_of_within = baseline + timedelta(days=5)
        as_of_past = baseline + timedelta(days=20)

        within = svc.judge_claim_evidences(claim, as_of_date=as_of_within)
        assert within[0]["status"] == svc.ALIVE

        past = svc._judge_manual(ev, as_of_past)
        assert past["status"] == svc.EXPIRED
        assert past["dead_streak_days"] == (as_of_past - baseline).days


@pytest.mark.django_db
class TestJudgeClaimEvidencesMixed:
    def test_multiple_evidences_ordered_by_created_at(self, claim, make_indicator, add_readings, monkeypatch):
        ind = make_indicator(window=10)
        add_readings(ind, [float(i) for i in range(10)], base=_BASE)
        ev1 = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.AUTO,
            indicator=ind, operator=ClaimEvidence.Operator.GTE, threshold=0.0,
        )
        ev2 = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.MANUAL,
            description="근거", last_confirmed_at=_AS_OF, recheck_period_days=90,
        )
        results = svc.judge_claim_evidences(claim, as_of_date=_AS_OF)
        assert [r["evidence_id"] for r in results] == [ev1.id, ev2.id]
        assert all(r["status"] == svc.ALIVE for r in results)

    def test_default_as_of_date_is_today(self, claim):
        ev = ClaimEvidence.objects.create(
            claim=claim, kind=ClaimEvidence.Kind.MANUAL,
            description="근거", last_confirmed_at=date(2020, 1, 1), recheck_period_days=1,
        )
        results = svc.judge_claim_evidences(claim)  # as_of_date 생략 → localdate()
        assert results[0]["status"] == svc.EXPIRED
