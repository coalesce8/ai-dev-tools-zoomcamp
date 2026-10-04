"""OpenTelemetry setup for traces, metrics, and logs.

When OTEL_EXPORTER_OTLP_ENDPOINT is set (as it is in Docker Compose), every
signal is sent over OTLP/HTTP to that endpoint, normally the OpenTelemetry
Collector. Otherwise each signal is written to stdout as one JSON object per line.
"""

import logging
import os
import sys
import time

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.metrics import NoOpMeterProvider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogRecordExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def _one_line(item):
    return item.to_json(indent=None) + "\n"


def _exporters():
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        # The OTLP exporters read the endpoint from the environment themselves.
        return OTLPSpanExporter(), OTLPMetricExporter(), OTLPLogExporter()
    return (
        ConsoleSpanExporter(out=sys.stdout, formatter=_one_line),
        ConsoleMetricExporter(out=sys.stdout, formatter=_one_line),
        ConsoleLogRecordExporter(out=sys.stdout, formatter=_one_line),
    )


def configure_telemetry():
    resource = Resource.create({SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "order-tracker")})
    span_exporter, metric_exporter, log_exporter = _exporters()

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # The export interval comes from OTEL_METRIC_EXPORT_INTERVAL (milliseconds).
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)

    app_logger = logging.getLogger("order_tracker")
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(LoggingHandler(logger_provider=logger_provider))


class RequestMetricsMiddleware:
    """Counts requests and records their duration by method, route, and status code."""

    def __init__(self, app):
        self.app = app
        meter = metrics.get_meter("order_tracker")
        self.requests = meter.create_counter(
            "http.server.requests", unit="{request}", description="HTTP requests handled"
        )
        self.duration = meter.create_histogram(
            "http.server.request.duration", unit="s", description="HTTP request duration"
        )

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status_code = 500
        started = time.perf_counter()

        async def send_with_status(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        except Exception:
            status_code = 500
            raise
        finally:
            route = scope.get("route")
            attributes = {
                "http.request.method": scope["method"],
                # Use the route template, not the raw path, so order ids don't
                # create a new time series each.
                "http.route": getattr(route, "path", "unmatched"),
                "http.response.status_code": status_code,
            }
            self.requests.add(1, attributes)
            self.duration.record(time.perf_counter() - started, attributes)


def instrument_app(app):
    app.add_middleware(RequestMetricsMiddleware)
    # The instrumentation creates server spans; request metrics come from the
    # middleware above, so its own metrics are switched off. Health-check spans
    # and per-message ASGI send/receive spans are skipped to keep the output readable.
    FastAPIInstrumentor.instrument_app(
        app,
        meter_provider=NoOpMeterProvider(),
        excluded_urls="/healthz",
        exclude_spans=["receive", "send"],
    )
