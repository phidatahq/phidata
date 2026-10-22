"""
Agent Storage Serialization and Manager Roundtrip
==================================================

Demonstrates saving and restoring an Agent with models and managers:
- parser_model and output_model
- session_summary_manager
- compression_manager
- compaction

Shows how to_dict() and from_dict() round-trip complex agent configurations
including all manager settings.
"""

from agno.agent.agent import Agent
from agno.compaction.compaction import Compaction
from agno.compression.manager import CompressionManager
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.session.summary import SessionSummaryManager

# ---------------------------------------------------------------------------
# Setup Storage
# ---------------------------------------------------------------------------
db = SqliteDb(db_file="tmp/agents_storage_demo.db")

# ---------------------------------------------------------------------------
# Create Agent with Models and Managers
# ---------------------------------------------------------------------------
model = OpenAIResponses(id="gpt-5.6-luna")
parser_model = OpenAIResponses(id="gpt-5.6-luna")
output_model = OpenAIResponses(id="gpt-5.6-luna")

summary_manager = SessionSummaryManager(
    model=model,
    session_summary_prompt="Extract concise high-level takeaways.",
    last_n_runs=5,
)

compression_manager = CompressionManager(
    model=model,
    compress_tool_results=True,
    compress_tool_results_limit=5,
)

compaction = Compaction(
    model=model,
    compact_at_tokens=60000,
    uncompacted_runs=3,
)

original_agent = Agent(
    id="enterprise-agent",
    name="Enterprise Analyst",
    model=model,
    parser_model=parser_model,
    parser_model_prompt="Parse output into structured format.",
    output_model=output_model,
    output_model_prompt="Format the final response for executive review.",
    db=db,
    enable_session_summaries=True,
    session_summary_manager=summary_manager,
    compress_tool_results=True,
    compression_manager=compression_manager,
    compaction=compaction,
)

# ---------------------------------------------------------------------------
# Run Serialization and Deserialization
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Serialize the agent configuration
    config = original_agent.to_dict()
    print("Serialized agent config keys:")
    print(sorted(config.keys()))

    # Reconstruct the agent from serialized config
    reconstructed_agent = Agent.from_dict(config)
    print("\nReconstructed Agent:")
    print("Name:", reconstructed_agent.name)
    print(
        "Parser Model:",
        reconstructed_agent.parser_model.id
        if reconstructed_agent.parser_model
        else None,
    )
    print(
        "Output Model:",
        reconstructed_agent.output_model.id
        if reconstructed_agent.output_model
        else None,
    )
    print(
        "Summary Manager Prompt:",
        reconstructed_agent.session_summary_manager.session_summary_prompt
        if reconstructed_agent.session_summary_manager
        else None,
    )
    print(
        "Compression Manager Tool Limit:",
        reconstructed_agent.compression_manager.compress_tool_results_limit
        if reconstructed_agent.compression_manager
        else None,
    )
    print(
        "Compaction Tokens:",
        reconstructed_agent.compaction.compact_at_tokens
        if reconstructed_agent.compaction
        else None,
    )
