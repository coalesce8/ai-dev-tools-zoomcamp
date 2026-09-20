# Agent Relay

Agent Relay is a small FastAPI service for registering agents, delivering one
task at a time, and recording results. Workers execute tasks on their own
machines. The included worker deterministically returns `input.upper()`.

## Run it

```bash
uv sync
uv run uvicorn main:app --reload
```

Open <http://127.0.0.1:8000/> for the token-based local dashboard. With no
`RELAY_DATABASE_URL` set, this uses a local SQLite file (`./agent-relay.db`)
so it runs with no external services. `GET /health` is a liveness check and
`GET /ready` verifies database connectivity and schema (it queries the real
tables, so a wiped volume reports not-ready instead of passing with zero
tables).

## Run it with PostgreSQL (Docker Compose)

```bash
docker compose up --build
```

This builds the app image and starts two services: `postgres` (PostgreSQL 16,
with a named volume for its data) and `agent-relay` (the FastAPI app, published
on `http://127.0.0.1:8000/`), wired together with `RELAY_DATABASE_URL` pointing
at the `postgres` service. Set `RELAY_DATABASE_URL` to any
`postgresql+psycopg://` or `sqlite:///` URL to point the app at a different
database outside Compose.

Register two identities and send a task:

```bash
alice=$(curl -sS -X POST http://127.0.0.1:8000/api/v1/agents \
  -H 'content-type: application/json' -d '{"name":"alice"}')
bob=$(curl -sS -X POST http://127.0.0.1:8000/api/v1/agents \
  -H 'content-type: application/json' -d '{"name":"uppercase"}')
```

The response contains each agent's secret `token` once. Keep it outside source
control. Use `Authorization: Bearer <token>` for all subsequent API calls;
registration is the only unauthenticated endpoint. For a shared installation,
set `RELAY_ENROLLMENT_SECRET` and send it as `X-Enrollment-Secret` when
registering.

## Run the deterministic worker

The worker can register itself and save credentials in a mode-0600 JSON file:

```bash
uv run python main.py worker \
  --base-url http://127.0.0.1:8000 \
  --name uppercase \
  --credentials ./uppercase-credentials.json \
  --worker-id laptop-1
```

For failure/redelivery demonstrations, make local execution intentionally slow
and stop the process after one completion:

```bash
uv run python main.py worker --credentials ./uppercase-credentials.json \
  --slow-seconds 75 --worker-id slow-laptop
```

The worker heartbeats during long work. Killing it leaves the claim leased;
after the 60-second lease expires, another worker can claim the task with a new
token and incremented attempt number. `RELAY_LEASE_SECONDS` and
`RELAY_MAX_ATTEMPTS` are configurable server settings.

An existing credential can also be supplied explicitly (the token is not
written to disk):

```bash
uv run python main.py worker --agent-id agent_123 --token agt_… --worker-id laptop-2
```

## Storage and delivery behavior

`database.py` contains SQLAlchemy models and the writer-transaction seam;
`storage.py` contains task/claim/recovery operations; routes and request
models are kept in `main.py` and `schemas.py`. On SQLite (no
`FOR UPDATE SKIP LOCKED`), a `BEGIN IMMEDIATE` writer reservation serializes
claims, heartbeats, terminal submissions, and recovery across processes. On
PostgreSQL, those same operations instead use ordinary transactions with
explicit row locking (`FOR UPDATE`, `FOR UPDATE SKIP LOCKED` for claims via
`database.for_update`), so unrelated tasks can be claimed concurrently. The
HTTP protocol and lifecycle in `SPEC.md` are identical on both backends.

Claims are at-least-once and leased for 60 seconds by default. Heartbeats extend
an active lease. A completion or failure must include the recipient's bearer
token and claim token. Repeating the exact terminal request with that claim
token is idempotent; a stale token or different result receives `409`.

## Verify

The test suite covers the main protocol, sender/recipient access boundaries,
hashed claim-token behavior, idempotent terminal retries, concurrent claims,
lease expiry before and after recovery, pagination/error shape, and dashboard
asset serving:

```bash
uv run pytest -q
```

Tests default to a scratch database at `/tmp/agent-relay-test.db` so they
don't reset your dev server's `./agent-relay.db`. The fixture drops and
recreates all tables on whatever `RELAY_DATABASE_URL` points at, so stop
the dev server first or set `RELAY_DATABASE_URL` to a scratch file before
running tests against another database.

## Run it on Kubernetes (kind)

`k8s/` has manifests for a namespace, a single-replica PostgreSQL deployment
(with a PVC and a secret holding `RELAY_DATABASE_URL`), and the agent-relay
deployment/service. The agent-relay deployment uses `imagePullPolicy: Never`,
so the image must be loaded into the cluster's nodes rather than pulled:

```bash
kind create cluster --name agent-relay
docker build -t agent-relay:local .
kind load docker-image agent-relay:local --name agent-relay
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/
kubectl -n agent-relay rollout status deployment/agent-relay
kubectl -n agent-relay port-forward svc/agent-relay 8000:8000
```

`readinessProbe`/`livenessProbe` on the agent-relay deployment hit `/ready`
and `/health`; a postgres init container blocks the app pod until
`pg_isready` succeeds.

## CI

`.github/workflows/ci.yml` runs on pushes/PRs touching `hw3/**`: a `test` job
runs `uv run pytest -q` against a real PostgreSQL service container, then a
`build-and-deploy` job builds the Docker image, loads it into an existing
kind cluster named `agent-relay`, applies `k8s/`, and waits for the rollout.
That second job targets a long-lived cluster created out-of-band (e.g. via
the `kind create cluster` command above) rather than provisioning one, so it
needs a self-hosted runner (or a local `act` run) with Docker and that
cluster available — it will not do anything useful on a plain GitHub-hosted
runner.

This starter intentionally does not include external brokers or an LLM;
those remain outside the local relay protocol.
