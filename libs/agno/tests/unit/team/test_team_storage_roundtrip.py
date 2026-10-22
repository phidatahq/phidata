"""
Unit tests for Team storage round-trip serialization and deserialization of
models (parser_model, output_model) and managers (session_summary_manager,
compression_manager).
"""

from agno.agent.agent import Agent
from agno.compression.manager import CompressionManager
from agno.models.openai import OpenAIChat
from agno.session.summary import SessionSummaryManager
from agno.team.team import Team


def test_team_parser_model_roundtrip():
    """Verify parser_model and parser_model_prompt round-trip through Team to_dict and from_dict."""
    member = Agent(id="team-member", name="Member")
    team = Team(
        id="parser-team",
        members=[member],
        parser_model=OpenAIChat(id="gpt-4o-mini"),
        parser_model_prompt="Extract and parse the output accurately for team.",
    )
    config = team.to_dict()
    assert "parser_model" in config
    assert config["parser_model_prompt"] == "Extract and parse the output accurately for team."

    loaded = Team.from_dict(config)
    assert loaded.parser_model is not None
    assert loaded.parser_model.id == "gpt-4o-mini"
    assert loaded.parser_model_prompt == "Extract and parse the output accurately for team."


def test_team_output_model_roundtrip():
    """Verify output_model and output_model_prompt round-trip through Team to_dict and from_dict."""
    member = Agent(id="team-member-2", name="Member 2")
    team = Team(
        id="output-team",
        members=[member],
        output_model=OpenAIChat(id="gpt-4o-mini"),
        output_model_prompt="Format the final response clearly for team.",
    )
    config = team.to_dict()
    assert "output_model" in config
    assert config["output_model_prompt"] == "Format the final response clearly for team."

    loaded = Team.from_dict(config)
    assert loaded.output_model is not None
    assert loaded.output_model.id == "gpt-4o-mini"
    assert loaded.output_model_prompt == "Format the final response clearly for team."


def test_team_session_summary_manager_roundtrip():
    """Verify session_summary_manager round-trips through Team to_dict and from_dict."""
    summary_mgr = SessionSummaryManager(
        session_summary_prompt="Summarize the core team takeaways.",
        summary_request_message="What did the team accomplish?",
        last_n_runs=4,
        conversation_limit=12,
    )
    member = Agent(id="team-member-3", name="Member 3")
    team = Team(
        id="summary-team",
        members=[member],
        enable_session_summaries=True,
        session_summary_manager=summary_mgr,
    )
    config = team.to_dict()
    assert "session_summary_manager" in config
    assert config["session_summary_manager"]["session_summary_prompt"] == "Summarize the core team takeaways."
    assert config["session_summary_manager"]["summary_request_message"] == "What did the team accomplish?"
    assert config["session_summary_manager"]["last_n_runs"] == 4
    assert config["session_summary_manager"]["conversation_limit"] == 12

    loaded = Team.from_dict(config)
    assert loaded.session_summary_manager is not None
    assert loaded.session_summary_manager.session_summary_prompt == "Summarize the core team takeaways."
    assert loaded.session_summary_manager.summary_request_message == "What did the team accomplish?"
    assert loaded.session_summary_manager.last_n_runs == 4
    assert loaded.session_summary_manager.conversation_limit == 12


def test_team_compression_manager_roundtrip():
    """Verify compression_manager round-trips through Team to_dict and from_dict."""
    compression_mgr = CompressionManager(
        compress_tool_results_limit=6,
        compress_token_limit=1500,
        compress_tool_call_instructions="Retain only critical outputs.",
    )
    member = Agent(id="team-member-4", name="Member 4")
    team = Team(
        id="compression-team",
        members=[member],
        compress_tool_results=True,
        compression_manager=compression_mgr,
    )
    config = team.to_dict()
    assert "compression_manager" in config
    assert config["compression_manager"]["compress_tool_results_limit"] == 6
    assert config["compression_manager"]["compress_token_limit"] == 1500
    assert config["compression_manager"]["compress_tool_call_instructions"] == "Retain only critical outputs."

    loaded = Team.from_dict(config)
    assert loaded.compression_manager is not None
    assert loaded.compression_manager.compress_tool_results_limit == 6
    assert loaded.compression_manager.compress_token_limit == 1500
    assert loaded.compression_manager.compress_tool_call_instructions == "Retain only critical outputs."
