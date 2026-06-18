"""OpenTelemetry initialization for PARALLAX.

Centralized telemetry setup used by both the FastAPI application and Celery workers.
"""

import logging

from parallax.core.config import settings

logger = logging.getLogger(__name__)

# OpenTelemetry is optional in lightweight dev venvs (e.g. .venv-fast).
# Guarded imports allow the app to import in environments without the otel
# packages installed. Telemetry is silently disabled in that case.
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None  # type: ignore[assignment]
    OTLPSpanExporter = None  # type: ignore[assignment,misc]
    Resource = None  # type: ignore[assignment,misc]
    TracerProvider = None  # type: ignore[assignment,misc]
    BatchSpanProcessor = None  # type: ignore[assignment,misc]


def init_telemetry(service_name: str) -> None:
    """Initialize OpenTelemetry tracing with OTLP exporter to Jaeger.

    No-op if the opentelemetry packages are not installed (lightweight dev venv).
    """
    if not OTEL_AVAILABLE:
        logger.debug("OpenTelemetry not installed; skipping telemetry init")
        return
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.ENVIRONMENT,
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
