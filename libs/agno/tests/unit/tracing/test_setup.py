"""setup_tracing must not let OTel's default attribute cap evict span kind from long model spans."""

import logging
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("openinference.instrumentation.agno")

from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.trace import ProxyTracerProvider  # noqa: E402

from agno.tracing import setup as tracing_setup  # noqa: E402

SPAN_KIND = "openinference.span.kind"


def _build_provider() -> TracerProvider:
    captured = {}
    with (
        patch.object(tracing_setup.trace_api, "get_tracer_provider", return_value=ProxyTracerProvider()),
        patch.object(tracing_setup.trace_api, "set_tracer_provider", side_effect=lambda p: captured.update(p=p)),
        patch.object(tracing_setup, "AgnoInstrumentor"),
    ):
        tracing_setup.setup_tracing(db=MagicMock())
    return captured["p"]


def _start_llm_span(provider: TracerProvider, num_messages: int):
    # Same ordering as the openinference model wrapper: span kind first, then flattened messages
    attributes = {SPAN_KIND: "LLM"}
    for i in range(num_messages):
        attributes[f"llm.input_messages.{i}.message.role"] = "user"
        attributes[f"llm.input_messages.{i}.message.content"] = f"message {i}"
    span = provider.get_tracer("test").start_span("model.invoke", attributes=attributes)
    span.end()
    return span


@pytest.fixture(autouse=True)
def _clear_otel_limit_env(monkeypatch):
    monkeypatch.delenv("OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT", raising=False)
    monkeypatch.delenv("OTEL_ATTRIBUTE_COUNT_LIMIT", raising=False)


def test_long_model_span_keeps_span_kind_without_warnings(caplog):
    provider = _build_provider()

    with caplog.at_level(logging.WARNING, logger="opentelemetry.attributes"):
        span = _start_llm_span(provider, num_messages=200)

    assert span.attributes[SPAN_KIND] == "LLM"
    assert len(span.attributes) == 401
    assert not [r for r in caplog.records if "Attributes dict is full" in r.getMessage()]


def test_otel_env_limit_is_honored(monkeypatch):
    monkeypatch.setenv("OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT", "10")
    provider = _build_provider()

    span = _start_llm_span(provider, num_messages=200)

    assert len(span.attributes) == 10
