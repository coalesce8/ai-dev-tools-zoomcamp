import importlib.util
import json
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "responder", Path(__file__).parent.parent / "incident-response" / "responder.py"
)
responder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(responder)

FIRING = {
    "status": "firing",
    "fingerprint": "abc123",
    "labels": {"alertname": "Order Tracker 5xx responses", "http_route": "/api/orders/{order_id}"},
    "annotations": {"endpoint": "GET /api/orders/{order_id}", "window": "5m"},
    "startsAt": "2026-10-04T17:40:20Z",
}


@pytest.fixture
def fake_agent(tmp_path):
    script = tmp_path / "agent.py"
    script.write_text(
        "import json, sys\n"
        "prompt = sys.stdin.read()\n"
        "print(json.dumps({'result': 'Status: NO ACTION', 'is_error': False, 'args': sys.argv[1:],"
        " 'prompt': prompt}))\n"
    )
    return [sys.executable, str(script)]


def make_responder(tmp_path, agent):
    # Port 9 refuses connections, so every telemetry query fails fast.
    return responder.Responder(tmp_path / "incidents", "http://127.0.0.1:9", agent)


def test_receive_saves_firing_alerts_and_skips_duplicates(tmp_path, fake_agent):
    service = make_responder(tmp_path, fake_agent)
    payload = {"alerts": [FIRING, {**FIRING, "status": "resolved", "fingerprint": "other"}]}

    first = service.receive(payload)
    again = service.receive(payload)

    assert len(first) == 1 and again == []
    incident = tmp_path / "incidents" / first[0]
    assert json.loads((incident / "alert.json").read_text()) == FIRING
    assert json.loads((incident / "status.json").read_text())["state"] == "queued"


def test_investigate_saves_context_and_runs_agent_headless(tmp_path, fake_agent):
    service = make_responder(tmp_path, fake_agent)
    incident = service.create_incident(FIRING)

    service.investigate(incident, FIRING)

    context = (incident / "context.md").read_text()
    assert "Endpoint: GET /api/orders/{order_id}" in context
    assert "Window: 5m" in context
    assert "Unavailable:" in context  # Grafana is unreachable in this test
    assert (incident / "response.md").read_text() == "Status: NO ACTION\n"
    output = json.loads((incident / "agent-output.json").read_text())
    assert output["args"][:2] == ["-p", "--output-format"]
    assert "dontAsk" in output["args"]
    assert str(incident) in output["prompt"]
    assert json.loads((incident / "status.json").read_text())["state"] == "done"


def test_endpoint_falls_back_to_labels():
    alert = {"labels": {"http_request_method": "GET", "http_route": "/api/orders"}, "annotations": {}}
    assert responder.endpoint_of(alert) == "GET /api/orders"
    assert responder.endpoint_of({}) is None
