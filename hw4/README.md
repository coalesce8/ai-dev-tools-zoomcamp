# Order Tracker

A small order tracking app for the AI Dev Tools Zoomcamp observability homework. It includes a web page, API, tests, and a Docker Compose setup. You add telemetry, alerts, and an incident responder in Homework 4.

The main user flow is creating an order and checking its status. Three sample orders are created on first startup.

## Run it

You need Docker with Compose. To run the tests, you also need Python 3.11+ and `uv`.

```bash
docker compose up --build -d --wait
```

Open <http://127.0.0.1:8000>. The API is at `/api/orders`, and the health check is at `/healthz`. Data is stored in a Docker volume and survives container recreation.

If port 8000 is occupied, set `ORDER_TRACKER_PORT`, for example:

```bash
ORDER_TRACKER_PORT=18080 docker compose up --build -d --wait
```

Run tests with `uv run --frozen pytest -q`. Stop the stack with `docker compose down`. Add `-v` only if you also want to delete the order data and the stored telemetry.

## Telemetry

The app uses OpenTelemetry for traces, metrics, and logs. It sends all three over OTLP to an OpenTelemetry Collector, which forwards them like this:

| Signal | Stored in | Notes |
| --- | --- | --- |
| Metrics | Prometheus (OTLP receiver) | `http_server_requests_total` and `http_server_request_duration_seconds`, labeled with `http_request_method`, `http_route`, and `http_response_status_code` |
| Logs | Loki (native OTLP) | One per order lookup (found, not found, or failed with the stack trace); `trace_id` and `order_id` are structured metadata |
| Traces | Tempo | A server span per request (health checks excluded) with an `order.lookup` child span |

Open Grafana at <http://127.0.0.1:3000> (no login). The **Order Tracker** dashboard is the home page and shows request counts, 4xx/5xx errors, latency, and the lookup logs. To move from a log to its trace, expand the log line and use the `trace_id` link. To move from a trace to its logs, use the logs button on a span. Prometheus is also available at <http://127.0.0.1:9090>. Change the host ports with `GRAFANA_PORT` and `PROMETHEUS_PORT`.

All configuration lives in `observability/`. Metrics are exported every 10 seconds, so allow a few seconds before a new request appears. If `OTEL_EXPORTER_OTLP_ENDPOINT` isn't set, the app prints the signals to stdout instead. The tests turn the SDK off through `OTEL_SDK_DISABLED`.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Web page |
| GET | `/healthz` | Database health check |
| GET | `/api/orders` | List orders |
| POST | `/api/orders` | Create an order |
| GET | `/api/orders/{id}` | Check an order |
| PATCH | `/api/orders/{id}` | Change an order status |

The app uses SQLite to keep setup small. Run one app container at a time. The course exercise is about detecting and handling an incident, not scaling the database.
