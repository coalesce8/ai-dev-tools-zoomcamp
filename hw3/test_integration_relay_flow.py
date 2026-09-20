"""Integration test for the two-agent task exchange.

Unlike test_agent_relay.py (which drives the app in-process via TestClient),
this spins up the real ASGI app as a subprocess uvicorn server bound to a real
TCP port, backed by a real on-disk SQLite database, and drives it with actual
HTTP requests. No mocks, no ASGI transport shortcut.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture()
def live_server(tmp_path):
    db_path = tmp_path / "agent-relay-integration.db"
    port = _free_port()
    env = {**os.environ, "RELAY_DATABASE_URL": f"sqlite:///{db_path}"}
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 10
        healthy = False
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout else ""
                raise RuntimeError(f"server exited early:\n{output}")
            try:
                if httpx.get(f"{base_url}/health", timeout=0.5).status_code == 200:
                    healthy = True
                    break
            except httpx.TransportError:
                pass
            time.sleep(0.1)
        if not healthy:
            raise RuntimeError("server did not become healthy in time")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_two_agents_exchange_task_and_result_over_real_http(live_server):
    with httpx.Client(base_url=live_server, timeout=5) as client:
        alice = client.post("/api/v1/agents", json={"name": "alice"}).json()
        bob = client.post("/api/v1/agents", json={"name": "uppercase"}).json()
        alice_headers = {"Authorization": f"Bearer {alice['token']}"}
        bob_headers = {"Authorization": f"Bearer {bob['token']}"}

        created = client.post(
            "/api/v1/tasks",
            headers=alice_headers,
            json={"to": bob["agent_id"], "input": "hello from alice"},
        )
        assert created.status_code == 201
        task_id = created.json()["task_id"]

        claim = client.post(
            "/api/v1/tasks/claim",
            headers=bob_headers,
            json={"worker_id": "integration-worker", "wait_seconds": 0},
        )
        assert claim.status_code == 200
        claim_data = claim.json()
        assert claim_data["input"] == "hello from alice"

        complete = client.post(
            f"/api/v1/tasks/{task_id}/complete",
            headers=bob_headers,
            json={"claim_token": claim_data["claim_token"], "output": "HELLO FROM ALICE"},
        )
        assert complete.status_code == 200
        assert complete.json()["status"] == "completed"

        result = client.get(f"/api/v1/tasks/{task_id}", headers=alice_headers)
        assert result.status_code == 200
        body = result.json()
        assert body["status"] == "completed"
        assert body["output"] == "HELLO FROM ALICE"
        assert body["from"] == alice["agent_id"]
        assert body["to"] == bob["agent_id"]
