# Incident responder

A small service that receives Grafana alert webhooks and hands each firing alert to Claude Code in headless mode.

```bash
python3 incident-response/responder.py
```

It listens on `http://127.0.0.1:8001` and uses only the Python standard library. It runs on the host, not in Docker, because it starts the `claude` CLI and needs your login and the repository checkout.

## What happens on an alert

1. `POST /alerts` accepts a Grafana webhook payload and answers `202` right away. Resolved alerts are ignored. An alert that is already queued or being investigated (matched by fingerprint) isn't started again.
2. For each firing alert it creates `incidents/<time>-<alertname>/` and saves:
   - `alert.json`: the alert as Grafana sent it
   - `context.md`: the endpoint, time window, and dashboard link, plus request counts by route and status, WARN/ERROR logs, and full error traces. The responder queries Prometheus, Loki, and Tempo through Grafana's datasource proxy, starting 10 minutes before the alert began.
   - `status.json`: `queued` → `collecting` → `investigating` → `done` or `failed`
3. It runs `claude -p --output-format json --permission-mode dontAsk` from the repository root, with a prompt that points at the incident folder. Alerts are handled one at a time.
4. The agent's final report goes to `response.md`. The full JSON output (session id, turns, cost) goes to `agent-output.json`.

## Agent permissions

The agent may read the repository, edit files, and run `uv run --frozen pytest` and read-only `git` commands. Everything else is denied without prompting: other shell commands, network access, commits. The prompt tells it to fix only small, clear problems with a regression test, and to escalate otherwise.

Logs and trace attributes include user input, such as order ids. They are passed to the agent as files, and the prompt tells it to treat them as untrusted evidence.

## Settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `RESPONDER_HOST` | `127.0.0.1` | Address to listen on |
| `RESPONDER_PORT` | `8001` | Port to listen on |
| `GRAFANA_URL` | `http://localhost:3000` | Grafana used to query telemetry |
| `RESPONDER_AGENT` | `claude` | Agent command |
| `RESPONDER_AGENT_TIMEOUT` | `1800` | Seconds before the agent is stopped |
| `RESPONDER_INCIDENTS_DIR` | `incident-response/incidents` | Where incidents are saved |

## Test it

```bash
curl -X POST http://localhost:8001/alerts \
  -H 'Content-Type: application/json' \
  -d '{"alerts":[{"status":"firing","labels":{"alertname":"ResponderTest","test":"true"},"annotations":{"summary":"Test notification; no incident to fix"}}]}'
```

Then watch `incident-response/incidents/*/status.json` and read `response.md` when the state is `done`.
