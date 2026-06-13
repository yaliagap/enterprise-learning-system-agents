"""OpenTelemetry setup: OTLP exporter configuration and custom span helpers.

All public functions are no-ops when ENABLE_INSTRUMENTATION=false or when
the opentelemetry-sdk package is not installed.  They NEVER raise exceptions
so missing telemetry configuration cannot crash the application.
"""
from __future__ import annotations

import hashlib
import logging
import os
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------------

def _instrumentation_enabled() -> bool:
    """Return True unless ENABLE_INSTRUMENTATION is explicitly set to 'false'."""
    return os.environ.get("ENABLE_INSTRUMENTATION", "true").strip().lower() != "false"


# ---------------------------------------------------------------------------
# Lazy OTel imports — graceful degradation when SDK is not installed
# ---------------------------------------------------------------------------

def _try_import_otel():  # type: ignore[return]
    """Return (trace, resource) modules or None if OTel is not available."""
    try:
        from opentelemetry import trace  # noqa: PLC0415
        from opentelemetry.sdk.resources import Resource  # noqa: PLC0415
        from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: PLC0415
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: PLC0415
            OTLPSpanExporter,
        )
        return trace, Resource, TracerProvider, BatchSpanProcessor, OTLPSpanExporter
    except ImportError:
        return None


# Module-level sentinel: set to True once configure_otel_providers() succeeds.
_configured: bool = False


# ---------------------------------------------------------------------------
# Public API: configure_otel_providers
# ---------------------------------------------------------------------------

def configure_otel_providers() -> None:
    """Configure a TracerProvider with an OTLP gRPC exporter.

    Reads OTEL_EXPORTER_OTLP_ENDPOINT (default: http://localhost:4317).
    Sets the global TracerProvider so all get_tracer() calls share it.

    Safe to call multiple times — subsequent calls are no-ops.
    Is a no-op when ENABLE_INSTRUMENTATION=false or OTel SDK is missing.
    Never raises.
    """
    global _configured  # noqa: PLW0603

    if _configured:
        return

    if not _instrumentation_enabled():
        logger.debug("OTel instrumentation disabled via ENABLE_INSTRUMENTATION=false")
        return

    modules = _try_import_otel()
    if modules is None:
        logger.warning(
            "opentelemetry-sdk not installed — instrumentation disabled. "
            "Install opentelemetry-sdk and opentelemetry-exporter-otlp-proto-grpc "
            "to enable tracing."
        )
        return

    trace, Resource, TracerProvider, BatchSpanProcessor, OTLPSpanExporter = modules

    try:
        endpoint = os.environ.get(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
        )
        service_name = os.environ.get("OTEL_SERVICE_NAME", "enterprise-learning-system")

        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": "1.0.0",
            }
        )

        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        _configured = True
        logger.info("OTel TracerProvider configured → %s (service=%s)", endpoint, service_name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OTel configuration failed (%s) — tracing disabled", exc)


# ---------------------------------------------------------------------------
# Public API: get_tracer
# ---------------------------------------------------------------------------

def get_tracer(name: str):  # type: ignore[return]
    """Return a named OTel Tracer, or a no-op stub if OTel is unavailable.

    Never raises.
    """
    if not _instrumentation_enabled():
        return _NoOpTracer()

    modules = _try_import_otel()
    if modules is None:
        return _NoOpTracer()

    trace = modules[0]
    try:
        return trace.get_tracer(name)
    except Exception as exc:  # noqa: BLE001
        logger.debug("get_tracer(%s) failed: %s", name, exc)
        return _NoOpTracer()


# ---------------------------------------------------------------------------
# Public API: context managers
# ---------------------------------------------------------------------------

@contextmanager
def trace_iq_call(
    provider_name: str,
    operation: str,
    result_count: int = 0,
) -> Generator[None, None, None]:
    """Context manager that wraps an IQ provider call in an OTel span.

    Span name follows GenAI OTel convention: ``iq.<operation>``.
    Attributes set:
      - iq.provider     (e.g. "foundry_iq", "fabric_iq", "work_iq")
      - iq.operation    (e.g. "search", "get_learner_profile")
      - iq.result_count (set to the *result_count* arg; callers may update
                         the span themselves via get_tracer)

    This is a no-op when instrumentation is disabled or OTel is missing.
    Never raises.
    """
    if not _instrumentation_enabled():
        yield
        return

    modules = _try_import_otel()
    if modules is None:
        yield
        return

    trace = modules[0]
    span_name = f"iq.{operation}"
    tracer = get_tracer(f"iq.{provider_name}")

    try:
        with tracer.start_as_current_span(span_name) as span:
            try:
                span.set_attribute("iq.provider", provider_name)
                span.set_attribute("iq.operation", operation)
                span.set_attribute("iq.result_count", result_count)
            except Exception:  # noqa: BLE001
                pass
            yield
    except Exception as exc:  # noqa: BLE001
        logger.debug("trace_iq_call span error (%s) — yielding without span", exc)
        yield


@contextmanager
def trace_agent_invocation(
    agent_name: str,
    learner_id: str,
) -> Generator[None, None, None]:
    """Context manager that wraps an agent invocation in an OTel span.

    Span name: ``agent.invoke``.
    Attributes:
      - agent.name            (e.g. "learning_path_curator")
      - agent.learner_id_hash (SHA-256[:12] of learner_id — no raw PII)

    No-op when instrumentation is disabled or OTel is missing.  Never raises.
    """
    if not _instrumentation_enabled():
        yield
        return

    modules = _try_import_otel()
    if modules is None:
        yield
        return

    learner_id_hash = hashlib.sha256(learner_id.encode()).hexdigest()[:12]
    tracer = get_tracer("agent.framework")

    try:
        with tracer.start_as_current_span("agent.invoke") as span:
            try:
                span.set_attribute("agent.name", agent_name)
                span.set_attribute("agent.learner_id_hash", learner_id_hash)
            except Exception:  # noqa: BLE001
                pass
            yield
    except Exception as exc:  # noqa: BLE001
        logger.debug("trace_agent_invocation span error (%s) — continuing without span", exc)
        raise


def trace_hitl_gate(state: str) -> None:
    """Record a span event for the HITL pause/resume lifecycle.

    *state* must be one of: ``"paused"``, ``"confirmed"``, ``"declined"``.
    The event is added to the current active span (if any) under the name
    ``hitl.gate`` with attribute ``hitl.state``.

    No-op when instrumentation is disabled, OTel is missing, or there is no
    active span.  Never raises.
    """
    if not _instrumentation_enabled():
        return

    modules = _try_import_otel()
    if modules is None:
        return

    trace = modules[0]

    try:
        span = trace.get_current_span()
        if span is None:
            return
        # Use a child span to make the HITL gate visible as its own node in
        # the Aspire Dashboard trace tree.
        tracer = get_tracer("hitl.gate")
        with tracer.start_as_current_span("hitl.gate") as hitl_span:
            hitl_span.set_attribute("hitl.state", state)
    except Exception as exc:  # noqa: BLE001
        logger.debug("trace_hitl_gate error (%s) — skipping", exc)


# ---------------------------------------------------------------------------
# No-op fallbacks
# ---------------------------------------------------------------------------

class _NoOpSpan:
    """Minimal no-op span returned when OTel is unavailable."""

    def set_attribute(self, key: str, value: object) -> None:  # noqa: ARG002
        pass

    def add_event(self, name: str, attributes: dict | None = None) -> None:  # noqa: ARG002
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _NoOpTracer:
    """Minimal no-op tracer returned when OTel is unavailable."""

    def start_as_current_span(self, name: str, **kwargs):  # noqa: ARG002
        return _NoOpSpan()

    def start_span(self, name: str, **kwargs):  # noqa: ARG002
        return _NoOpSpan()
