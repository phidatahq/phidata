"""
Unit tests for OpenAI metrics collection.

Tests that the collect_metrics_on_completion flag works correctly for OpenAI models.
"""

from typing import Optional

import pytest
from openai.types.completion_usage import CompletionUsage
from openai.types.responses import ResponseUsage

from agno.metrics import coerce_token_count
from agno.models.openai.chat import OpenAIChat
from agno.models.openai.responses import OpenAIResponses


class MockCompletionUsage:
    """Mock CompletionUsage object for testing."""

    def __init__(
        self,
        prompt_tokens: Optional[int] = 0,
        completion_tokens: Optional[int] = 0,
        total_tokens: Optional[int] = 0,
        prompt_tokens_details=None,
        completion_tokens_details=None,
    ):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.prompt_tokens_details = prompt_tokens_details
        self.completion_tokens_details = completion_tokens_details


class MockChoice:
    """Mock Choice object for testing."""

    def __init__(self, finish_reason=None):
        self.finish_reason = finish_reason


class MockChatCompletionChunk:
    """Mock ChatCompletionChunk object for testing."""

    def __init__(self, usage=None, finish_reason=None):
        self.usage = usage
        self.choices = [MockChoice(finish_reason=finish_reason)]


def test_openai_chat_default_collect_metrics_flag():
    """Test that OpenAIChat has collect_metrics_on_completion set to False by default."""
    model = OpenAIChat(id="gpt-4o")
    assert model.collect_metrics_on_completion is False


def test_should_collect_metrics_when_usage_is_none():
    """Test that _should_collect_metrics returns False when usage is None."""
    model = OpenAIChat(id="gpt-4o")
    response = MockChatCompletionChunk(usage=None)
    assert model._should_collect_metrics(response) is False  # type: ignore[arg-type]


def test_should_collect_metrics_default_behavior():
    """Test that _should_collect_metrics returns True when collect_metrics_on_completion is False."""
    model = OpenAIChat(id="gpt-4o")
    usage = MockCompletionUsage(prompt_tokens=100, completion_tokens=20, total_tokens=120)

    # Test with no finish_reason (intermediate chunk)
    response = MockChatCompletionChunk(usage=usage, finish_reason=None)
    assert model._should_collect_metrics(response) is True  # type: ignore[arg-type]

    # Test with finish_reason (last chunk)
    response = MockChatCompletionChunk(usage=usage, finish_reason="stop")
    assert model._should_collect_metrics(response) is True  # type: ignore[arg-type]


def test_openai_streaming_metrics_simulation():
    """
    Simulate the default OpenAI streaming scenario.

    OpenAI returns incremental token counts, and we should collect on every chunk.
    """
    model = OpenAIChat(id="gpt-4o")

    chunks = [
        MockChatCompletionChunk(
            usage=MockCompletionUsage(prompt_tokens=100, completion_tokens=1, total_tokens=101),
            finish_reason=None,
        ),
        MockChatCompletionChunk(
            usage=MockCompletionUsage(prompt_tokens=0, completion_tokens=1, total_tokens=1),
            finish_reason=None,
        ),
        MockChatCompletionChunk(
            usage=MockCompletionUsage(prompt_tokens=0, completion_tokens=1, total_tokens=1),
            finish_reason="stop",
        ),
    ]

    collected_metrics = []
    for chunk in chunks:
        if model._should_collect_metrics(chunk):  # type: ignore[arg-type]
            metrics = model._get_metrics(chunk.usage)  # type: ignore[arg-type]
            collected_metrics.append(metrics)

    # Should collect metrics from all chunks with usage
    assert len(collected_metrics) == 3


def test_openai_get_metrics_computes_audio_total_tokens():
    """Audio totals should be derived from input and output audio token counts."""
    model = OpenAIChat(id="gpt-4o")

    class MockPromptTokensDetails:
        def __init__(self):
            self.audio_tokens = 11
            self.cached_tokens = 7

    class MockCompletionTokensDetails:
        def __init__(self):
            self.audio_tokens = 13
            self.reasoning_tokens = 5

    usage = MockCompletionUsage(
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        prompt_tokens_details=MockPromptTokensDetails(),
        completion_tokens_details=MockCompletionTokensDetails(),
    )

    metrics = model._get_metrics(usage)  # type: ignore[arg-type]

    assert metrics.audio_input_tokens == 11
    assert metrics.audio_output_tokens == 13
    assert metrics.audio_total_tokens == 24


@pytest.mark.parametrize(
    "model_class,usage_class,input_field,output_field",
    [
        (OpenAIChat, CompletionUsage, "prompt_tokens", "completion_tokens"),
        (OpenAIResponses, ResponseUsage, "input_tokens", "output_tokens"),
    ],
)
@pytest.mark.parametrize(
    "cache_details,expected_writes",
    [({"cache_write_tokens": 3000}, 3000), ({"cache_write_tokens": 0}, 0), ({"cache_write_tokens": None}, 0), ({}, 0)],
    ids=["writes", "zero", "null", "omitted"],
)
def test_openai_get_metrics_preserves_cache_writes(
    model_class, usage_class, input_field, output_field, cache_details, expected_writes
):
    """Preserve cache-write usage without requiring the field in older payloads."""
    # Match the SDK's non-strict response parsing for older provider payloads.
    usage = usage_class.construct(
        **{
            input_field: 15000,
            output_field: 50,
            "total_tokens": 15050,
            f"{input_field}_details": {"cached_tokens": 12000, **cache_details},
            f"{output_field}_details": {"reasoning_tokens": 7},
        }
    )

    metrics = model_class()._get_metrics(usage)

    assert metrics.cache_write_tokens == expected_writes
    assert metrics.cache_read_tokens == 12000
    assert metrics.input_tokens == 15000
    assert metrics.output_tokens == 50
    assert metrics.total_tokens == 15050
    assert metrics.reasoning_tokens == 7


class MockDetailTokens:
    """Detail object whose token fields may hold non-numeric placeholders."""

    def __init__(self, **tokens):
        self.__dict__.update(tokens)


@pytest.mark.parametrize(
    "raw_value,expected",
    [
        ("N/A", 0),
        ("", 0),
        ("unknown", 0),
        (None, 0),
        ("42", 42),
        (" 42 ", 42),
        ("42.0", 42),
        (7.9, 7),
        (0, 0),
        (True, 0),
        (-5, 0),
    ],
)
def test_coerce_token_count_normalises_provider_values(raw_value, expected):
    assert coerce_token_count(raw_value) == expected


@pytest.mark.parametrize(
    "model_class,usage_class,input_field,output_field",
    [
        (OpenAIChat, CompletionUsage, "prompt_tokens", "completion_tokens"),
        (OpenAIResponses, ResponseUsage, "input_tokens", "output_tokens"),
    ],
)
def test_openai_get_metrics_tolerates_non_numeric_usage_fields(model_class, usage_class, input_field, output_field):
    """A non-numeric usage field must not abort metrics calculation (#10930)."""
    usage = usage_class.construct(
        **{
            input_field: "N/A",
            output_field: "N/A",
            "total_tokens": "N/A",
            f"{input_field}_details": {"cached_tokens": "N/A", "cache_write_tokens": "N/A"},
            f"{output_field}_details": {"reasoning_tokens": "N/A"},
        }
    )

    metrics = model_class()._get_metrics(usage)

    assert metrics.input_tokens == 0
    assert metrics.output_tokens == 0
    assert metrics.total_tokens == 0
    assert metrics.cache_read_tokens == 0
    assert metrics.cache_write_tokens == 0
    assert metrics.reasoning_tokens == 0


def test_openai_get_metrics_audio_totals_survive_placeholder_values():
    """The audio-total addition is where the non-numeric placeholder raised (#10930)."""
    model = OpenAIChat(id="gpt-4o")
    usage = MockCompletionUsage(
        prompt_tokens=12,
        completion_tokens=8,
        total_tokens=20,
        prompt_tokens_details=MockDetailTokens(audio_tokens=0, cached_tokens="N/A"),
        completion_tokens_details=MockDetailTokens(audio_tokens="N/A", reasoning_tokens="N/A"),
    )

    metrics = model._get_metrics(usage)  # type: ignore[arg-type]

    assert metrics.audio_input_tokens == 0
    assert metrics.audio_output_tokens == 0
    assert metrics.audio_total_tokens == 0
    # The valid fields of the same response are still reported.
    assert metrics.input_tokens == 12
    assert metrics.output_tokens == 8
    assert metrics.total_tokens == 20


def test_openai_get_metrics_coerces_numeric_string_token_counts():
    """Gateways that report counts as strings still yield integer metrics."""
    model = OpenAIChat(id="gpt-4o")
    usage = MockCompletionUsage(prompt_tokens="120", completion_tokens="30", total_tokens="150")

    metrics = model._get_metrics(usage)  # type: ignore[arg-type]

    assert metrics.input_tokens == 120
    assert metrics.output_tokens == 30
    assert metrics.total_tokens == 150


def test_openai_get_metrics_result_is_summable_after_placeholder_fields():
    """Metrics carrying a placeholder must stay addable for downstream aggregation."""
    model = OpenAIChat(id="gpt-4o")
    usage = MockCompletionUsage(
        prompt_tokens="N/A",
        completion_tokens=8,
        total_tokens="N/A",
        prompt_tokens_details=MockDetailTokens(audio_tokens="N/A", cached_tokens="N/A"),
        completion_tokens_details=MockDetailTokens(audio_tokens="N/A", reasoning_tokens="N/A"),
    )

    metrics = model._get_metrics(usage)  # type: ignore[arg-type]
    combined = metrics + metrics

    assert combined.input_tokens == 0
    assert combined.output_tokens == 16
