import pytest

from lab_automation.execution_records import InvocationRecord


def test_invocation_accepts_replication_as_distinct_intent():
    record = InvocationRecord(
        run_id="R1",
        actor="model",
        backend="local",
        execution_intent="replication",
    )
    assert record.execution_intent == "replication"


def test_invocation_rejects_unknown_intent_vocabulary():
    with pytest.raises(ValueError):
        InvocationRecord(
            run_id="R1",
            actor="model",
            backend="local",
            execution_intent="duplicate_but_maybe_retry",
        )
