"""
Engy Basic
==========

Run an Agno agent against Engy through OpenAILike.

Engy exposes an OpenAI-compatible Chat Completions API at
https://api.engy.ai/v1. Set ENGY_API_KEY before running. This example calls
the kimi-k3 flagship.
"""

from os import getenv

from agno.agent import Agent
from agno.models.openai.like import OpenAILike

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------

agent = Agent(
    model=OpenAILike(
        id="kimi-k3",
        api_key=getenv("ENGY_API_KEY"),
        base_url="https://api.engy.ai/v1",
    ),
    markdown=True,
)

# ---------------------------------------------------------------------------
# Run Agent
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    agent.print_response("Share a 2 sentence horror story.")
