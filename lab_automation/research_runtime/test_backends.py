from pathlib import Path
import json
import sys

from lab_automation.research_runtime.backends import (
    BackendRequest,
    CommandBackendConfig,
    CommandJSONBackend,
    load_command_backend,
)


def test_command_backend_parses_one_json_object(tmp_path: Path):
    responder = tmp_path / "responder.py"
    responder.write_text(
        "import json, os\n"
        "print(json.dumps({'role': os.environ['STOCKVIS_RESEARCH_ROLE'], 'ok': True}))\n",
        encoding="utf-8",
    )
    backend = CommandJSONBackend(
        CommandBackendConfig(
            command=(sys.executable, str(responder)),
            requested_identity="fixture-command",
        )
    )
    result = backend.execute(
        BackendRequest(
            role="researcher",
            run_id="R1",
            instruction="test",
            payload={"x": 1},
            response_contract={"ok": "bool"},
        )
    )
    assert result.status == "completed"
    assert result.parsed_output == {"role": "researcher", "ok": True}


def test_command_backend_preserves_invalid_output(tmp_path: Path):
    responder = tmp_path / "bad.py"
    responder.write_text("print('not json')\n", encoding="utf-8")
    backend = CommandJSONBackend(
        CommandBackendConfig(command=(sys.executable, str(responder)))
    )
    result = backend.execute(
        BackendRequest(
            role="critic",
            run_id="R2",
            instruction="test",
            payload={},
            response_contract={},
        )
    )
    assert result.status == "invalid_output"
    assert result.parsed_output is None
    assert result.raw_stdout.strip() == "not json"


def test_role_specific_config_overrides_default(tmp_path: Path):
    responder = tmp_path / "responder.py"
    responder.write_text("import json; print(json.dumps({'ok': True}))\n", encoding="utf-8")
    config = tmp_path / "backend.json"
    config.write_text(
        json.dumps(
            {
                "backend_type": "command_json",
                "default": {
                    "command": [sys.executable, str(responder)],
                    "requested_identity": "default-model",
                },
                "roles": {"critic": {"requested_identity": "critic-model"}},
            }
        ),
        encoding="utf-8",
    )
    backend = load_command_backend(config, "critic")
    result = backend.execute(
        BackendRequest(
            role="critic",
            run_id="R3",
            instruction="test",
            payload={},
            response_contract={"ok": "bool"},
        )
    )
    assert result.requested_identity == "critic-model"
    assert result.status == "completed"
