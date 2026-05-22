# app/observability.py
"""
OpenTelemetry instrumentation for metrics and tracing.
"""
import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import structlog

# Environment configuration
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "true").lower() == "true"
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
SERVICE_NAME_VAL = os.getenv("SERVICE_NAME", "sre-k8s-agent")
SERVICE_VERSION_VAL = os.getenv("SERVICE_VERSION", "1.0.0")

# Prometheus metrics
task_counter = Counter(
    "agent_tasks_total",
    "Total number of tasks received",
    ["status", "task_type"]
)

task_duration = Histogram(
    "agent_task_duration_seconds",
    "Task execution duration in seconds",
    ["task_type"]
)

k8s_api_calls = Counter(
    "agent_k8s_api_calls_total",
    "Total K8s API calls",
    ["operation", "status"]
)

k8s_api_duration = Histogram(
    "agent_k8s_api_duration_seconds",
    "K8s API call duration",
    ["operation"]
)

active_tasks = Gauge(
    "agent_active_tasks",
    "Number of currently active tasks"
)

k8s_api_errors = Counter(
    "agent_k8s_api_errors_total",
    "Total K8s API errors",
    ["operation", "error_code"]
)


def setup_opentelemetry(app):
    """Initialize OpenTelemetry with OTLP exporters."""
    if not OTEL_ENABLED:
        structlog.get_logger().info("OpenTelemetry disabled")
        return

    # Resource identifies this service
    resource = Resource(attributes={
        SERVICE_NAME: SERVICE_NAME_VAL,
        SERVICE_VERSION: SERVICE_VERSION_VAL,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    # Tracing setup
    trace_provider = TracerProvider(resource=resource)
    otlp_span_exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_span_exporter))
    trace.set_tracer_provider(trace_provider)

    # Metrics setup
    otlp_metric_exporter = OTLPMetricExporter(endpoint=OTEL_ENDPOINT, insecure=True)
    metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=30000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    RequestsInstrumentor().instrument()

    structlog.get_logger().info(
        "opentelemetry_initialized",
        endpoint=OTEL_ENDPOINT,
        service=SERVICE_NAME_VAL
    )


def get_tracer():
    """Get tracer for manual span creation."""
    return trace.get_tracer(__name__)


def get_meter():
    """Get meter for custom metrics."""
    return metrics.get_meter(__name__)


def prometheus_metrics():
    """Generate Prometheus metrics in text format."""
    return generate_latest()
