"""
Unit tests for Agent storage round-trip serialization and deserialization of
models (parser_model, output_model) and managers (session_summary_manager,
compression_manager, compaction).
"""

from agno.agent.agent import Agent
from agno.compaction.compaction import Compaction
from agno.compression.manager import CompressionManager
from agno.models.openai import OpenAIChat
from agno.session.summary import SessionSummaryManager


def test_agent_parser_model_roundtrip():
    """Verify parser_model and parser_model_prompt round-trip through to_dict and from_dict."""
    agent = Agent(
        id="parser-agent",
        parser_model=OpenAIChat(id="gpt-4o-mini"),
        parser_model_prompt="Extract and parse the output accurately.",
    )
    config = agent.to_dict()
    assert "parser_model" in config
    assert config["parser_model_prompt"] == "Extract and parse the output accurately."

    loaded = Agent.from_dict(config)
    assert loaded.parser_model is not None
    assert loaded.parser_model.id == "gpt-4o-mini"
    assert loaded.parser_model_prompt == "Extract and parse the output accurately."


def test_agent_output_model_roundtrip():
    """Verify output_model and output_model_prompt round-trip through to_dict and from_dict."""
    agent = Agent(
        id="output-agent",
        output_model=OpenAIChat(id="gpt-4o-mini"),
        output_model_prompt="Format the final response clearly.",
    )
    config = agent.to_dict()
    assert "output_model" in config
    assert config["output_model_prompt"] == "Format the final response clearly."

    loaded = Agent.from_dict(config)
    assert loaded.output_model is not None
    assert loaded.output_model.id == "gpt-4o-mini"
    assert loaded.output_model_prompt == "Format the final response clearly."


def test_agent_session_summary_manager_roundtrip():
    """Verify session_summary_manager round-trips through to_dict and from_dict."""
    summary_mgr = SessionSummaryManager(
        session_summary_prompt="Summarize the core takeaways.",
        summary_request_message="What was discussed?",
        last_n_runs=5,
        conversation_limit=15,
    )
    agent = Agent(
        id="summary-agent",
        enable_session_summaries=True,
        session_summary_manager=summary_mgr,
    )
    config = agent.to_dict()
    assert "session_summary_manager" in config
    assert config["session_summary_manager"]["session_summary_prompt"] == "Summarize the core takeaways."
    assert config["session_summary_manager"]["summary_request_message"] == "What was discussed?"
    assert config["session_summary_manager"]["last_n_runs"] == 5
    assert config["session_summary_manager"]["conversation_limit"] == 15

    loaded = Agent.from_dict(config)
    assert loaded.session_summary_manager is not None
    assert loaded.session_summary_manager.session_summary_prompt == "Summarize the core takeaways."
    assert loaded.session_summary_manager.summary_request_message == "What was discussed?"
    assert loaded.session_summary_manager.last_n_runs == 5
    assert loaded.session_summary_manager.conversation_limit == 15


def test_agent_compression_manager_roundtrip():
    """Verify compression_manager round-trips through to_dict and from_dict."""
    compression_mgr = CompressionManager(
        compress_tool_results_limit=8,
        compress_token_limit=1000,
        compress_tool_call_instructions="Keep only essential key-value pairs.",
    )
    agent = Agent(
        id="compression-agent",
        compress_tool_results=True,
        compression_manager=compression_mgr,
    )
    config = agent.to_dict()
    assert "compression_manager" in config
    assert config["compression_manager"]["compress_tool_results_limit"] == 8
    assert config["compression_manager"]["compress_token_limit"] == 1000
    assert config["compression_manager"]["compress_tool_call_instructions"] == "Keep only essential key-value pairs."

    loaded = Agent.from_dict(config)
    assert loaded.compression_manager is not None
    assert loaded.compression_manager.compress_tool_results_limit == 8
    assert loaded.compression_manager.compress_token_limit == 1000
    assert loaded.compression_manager.compress_tool_call_instructions == "Keep only essential key-value pairs."


def test_agent_compaction_object_roundtrip():
    """Verify Compaction instance round-trips through to_dict and from_dict."""
    compaction = Compaction(
        instructions="Preserve key findings and action items.",
        compact_at_tokens=40000,
        uncompacted_runs=3,
        store_compacted_messages=True,
        search_compacted_messages=True,
    )
    agent = Agent(
        id="compaction-agent",
        compaction=compaction,
    )
    config = agent.to_dict()
    assert "compaction" in config
    assert isinstance(config["compaction"], dict)
    assert config["compaction"]["instructions"] == "Preserve key findings and action items."
    assert config["compaction"]["compact_at_tokens"] == 40000
    assert config["compaction"]["uncompacted_runs"] == 3

    loaded = Agent.from_dict(config)
    assert isinstance(loaded.compaction, Compaction)
    assert loaded.compaction.instructions == "Preserve key findings and action items."
    assert loaded.compaction.compact_at_tokens == 40000
    assert loaded.compaction.uncompacted_runs == 3
    assert loaded.compaction.store_compacted_messages is True
    assert loaded.compaction.search_compacted_messages is True


def test_agent_boolean_compaction_roundtrip():
    """Verify boolean compaction=True round-trips through to_dict and from_dict."""
    agent = Agent(
        id="bool-compaction-agent",
        compaction=True,
    )
    config = agent.to_dict()
    # When initialized, compaction=True resolves to a Compaction instance with on_context_overflow=True
    assert "compaction" in config

    loaded = Agent.from_dict(config)
    assert loaded.compaction is not None
