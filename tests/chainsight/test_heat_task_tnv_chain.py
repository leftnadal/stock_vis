"""TH-TNV-CHAIN-1 §B.2 — theme-heat-daily 태스크의 TNV 체이닝 단위 테스트.

계약(D-TH-TNV-CHAIN):
  - TNV 집계(당일)가 heat 계산 前에 실행된다 (순서).
  - TNV 예외 → 태스크 실패 전파, heat 미실행 (재동결 방지: 빈 재료로 조용히 계산 금지).
  - TNV written=0 (keywords=[] 정상 공백) → 실패 아님, heat 진행 (예외 ≠ 0건).
"""

from unittest import mock

import pytest

from apps.chain_sight.tasks import heat_tasks

AGG = "apps.chain_sight.services.c3_narrative_service.aggregate_theme_news_volume"
HEAT = "apps.chain_sight.services.heat_beat.compute_theme_heat"
INSIDER = "apps.chain_sight.services.insider_service.collect_latest"


@pytest.mark.django_db
def test_chain_order_tnv_before_heat():
    """TNV 집계가 compute_theme_heat 前에 호출된다."""
    order = []
    with mock.patch(
        AGG, side_effect=lambda **kw: order.append("tnv") or {"written": 2, "zeroed": 0, "days": 1}
    ), mock.patch(
        HEAT, side_effect=lambda as_of: order.append("heat") or [{"stored": True}]
    ), mock.patch(INSIDER, return_value={}):
        result = heat_tasks.compute_theme_heat_task.apply().get()

    assert order == ["tnv", "heat"], f"순서 위반: {order}"
    assert result["stored"] == 1


@pytest.mark.django_db
def test_tnv_failure_propagates_and_heat_not_called():
    """TNV 예외 → 태스크 실패 전파, heat 미실행."""
    with mock.patch(AGG, side_effect=RuntimeError("TNV boom")), mock.patch(
        HEAT
    ) as heat_spy, mock.patch(INSIDER, return_value={}):
        with pytest.raises(RuntimeError, match="TNV boom"):
            heat_tasks.compute_theme_heat_task.apply().get()
        heat_spy.assert_not_called()


@pytest.mark.django_db
def test_written_zero_passes_to_heat():
    """TNV written=0 (정상 공백) → 실패 아님, heat 진행."""
    with mock.patch(
        AGG, return_value={"written": 0, "zeroed": 0, "days": 1}
    ), mock.patch(HEAT, return_value=[{"stored": True}]) as heat_spy, mock.patch(
        INSIDER, return_value={}
    ):
        result = heat_tasks.compute_theme_heat_task.apply().get()

    heat_spy.assert_called_once()
    assert result["stored"] == 1
