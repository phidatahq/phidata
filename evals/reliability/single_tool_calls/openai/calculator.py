from typing import Optional

from agno.agent import Agent
from agno.eval.reliability import ReliabilityEval, ReliabilityResult
from agno.tools.calculator import Calculator
from agno.models.openai import OpenAIChat
from agno.run.response import RunResponse


def factorial():

    agent=Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[Calculator(factorial=True)],
    )
    response: RunResponse = agent.run("What is 10!?")
    evaluation = ReliabilityEval(
        agent_response=response,
        expected_tool_calls=["factorial"],
    )
    result: Optional[ReliabilityResult] = evaluation.run(print_results=True)
    assert result.eval_status == "PASSED"


if __name__ == "__main__":
    factorial()
