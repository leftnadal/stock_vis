"""@backend 일일 보고서 TL;DR System 줄 회귀 잠금 (MGMT-LEDGER-2 T3).

버그: `_build_tldr_backend`가 health dict에 없는 구 키(celery_beat_running/
neo4j_reachable)를 읽어 `.get(..., False)`가 항상 False → 실제 beat/neo4j가
살아 있어도 항상 "beat=DOWN neo4j=DOWN"·emoji ⚠️로 고착.

수정: collect_system_health()가 내보내는 실키(celery_beat_alive/neo4j_alive)를
재사용(단일 출처). 이 테스트가 구 키로의 회귀를 잠근다.
"""

import pytest

from packages.shared.metrics.services.agent_reports import _build_tldr_backend

# tests/unit/metrics/conftest.py의 autouse seed_metrics fixture가 DB를 요구 —
# _build_tldr_backend 자체는 순수 함수지만 패키지 관례(django_db)를 따른다.
pytestmark = pytest.mark.django_db

# collect_system_health() 스키마와 동일한 최소 llm 페이로드
_LLM = {"est_cost_usd_24h": 0, "total_calls_24h": 0, "est_monthly_cost_usd": 0}


def _system_line(health):
    return _build_tldr_backend(health, _LLM, [])[0]


def test_system_line_all_alive_shows_no_down():
    """worker≥1 + beat alive + neo4j alive → 'DOWN' 불출현·✅."""
    health = {"celery_worker_count": 2, "celery_beat_alive": True, "neo4j_alive": True}
    line = _system_line(health)
    assert "DOWN" not in line
    assert "beat=OK" in line
    assert "neo4j=OK" in line
    assert line.startswith("✅")


def test_system_line_beat_down_shows_down():
    """beat만 죽으면 beat=DOWN 출현·⚠️ (neo4j는 OK 유지)."""
    health = {"celery_worker_count": 2, "celery_beat_alive": False, "neo4j_alive": True}
    line = _system_line(health)
    assert "beat=DOWN" in line
    assert "neo4j=OK" in line
    assert line.startswith("⚠️")


def test_system_line_neo4j_down_shows_down():
    """neo4j만 죽으면 neo4j=DOWN 출현·⚠️ (beat는 OK 유지)."""
    health = {"celery_worker_count": 2, "celery_beat_alive": True, "neo4j_alive": False}
    line = _system_line(health)
    assert "neo4j=DOWN" in line
    assert "beat=OK" in line
    assert line.startswith("⚠️")


def test_system_line_all_down_shows_both_down():
    """전부 죽으면 beat·neo4j 모두 DOWN·⚠️."""
    health = {"celery_worker_count": 0, "celery_beat_alive": False, "neo4j_alive": False}
    line = _system_line(health)
    assert "beat=DOWN" in line
    assert "neo4j=DOWN" in line
    assert line.startswith("⚠️")


def test_system_line_ignores_stale_legacy_keys():
    """구 키(celery_beat_running/neo4j_reachable)만 있고 실키가 없으면 DOWN 판정 —

    실키를 읽는다는 증거(구 키로 회귀하면 이 케이스가 'OK'로 뒤집혀 실패한다).
    """
    health = {
        "celery_worker_count": 2,
        "celery_beat_running": True,   # 구 키 — 무시돼야 함
        "neo4j_reachable": True,       # 구 키 — 무시돼야 함
    }
    line = _system_line(health)
    assert "beat=DOWN" in line
    assert "neo4j=DOWN" in line
