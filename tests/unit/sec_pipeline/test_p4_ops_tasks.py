"""CS-P4-OPS Slice1 — ops 자동화 태스크 검증 (call_command mock, 무인 완주 체인).

LLM/FMP/SEC 무접촉 — call_command를 patch해 오케스트레이션(순서·인자·반환)만 검증.
"""
import pytest


@pytest.mark.django_db
def test_collect_and_extract_8k_daily_chains_commands(monkeypatch):
    """8-K 일일: collect_8k_filings(--apply --days) → extract_8k_relations(--apply) 순서 체인."""
    calls = []
    monkeypatch.setattr(
        "django.core.management.call_command",
        lambda name, *a, **k: calls.append((name, a)),
    )
    from services.sec_pipeline.tasks import collect_and_extract_8k_daily

    res = collect_and_extract_8k_daily.apply(kwargs={"days": 2}).get()

    assert res == {"status": "ok", "days": 2}
    assert [c[0] for c in calls] == ["collect_8k_filings", "extract_8k_relations"]
    # 증분·착지 규약: 수집은 --apply + --days=2, 추출은 --apply (status=collected만 처리)
    assert "--apply" in calls[0][1] and "--days=2" in calls[0][1]
    assert "--apply" in calls[1][1]


@pytest.mark.django_db
def test_recompute_sync_strength_weekly(monkeypatch):
    """sync 주간: compute_relation_sync_strength(--apply) 단일 재사용."""
    calls = []
    monkeypatch.setattr(
        "django.core.management.call_command",
        lambda name, *a, **k: calls.append((name, a)),
    )
    from apps.chain_sight.tasks.relation_tasks import recompute_sync_strength_weekly

    res = recompute_sync_strength_weekly.apply().get()

    assert res == {"status": "ok"}
    assert calls[0][0] == "compute_relation_sync_strength"
    assert "--apply" in calls[0][1]


def test_tasks_registered_by_name():
    """beat DB 등록용 task 경로가 shared_task name으로 노출되는지 (Bug #28 = DB 등록)."""
    from celery import current_app

    reg = current_app.tasks
    assert "sec-8k-daily" in reg
    assert "chainsight-sync-strength-weekly" in reg
