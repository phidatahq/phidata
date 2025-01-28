from typing import Optional

from agno.agent import Agent
from agno.eval.reliability import ReliabilityEval, ReliabilityResult
from agno.tools.calculator import CalculatorTools
from agno.models.anthropic import Claude
from agno.run.response import RunResponse


def factorial():

    agent=Agent(
        model=Claude(id="claude-3-5-sonnet-20241022"),
        tools=[CalculatorTools(factorial=True)],
    )
    response: RunResponse = agent.run("What is 10!?")
    evaluation = ReliabilityEval(
        agent_response=response,
        expected_tool_calls=["factorial"],
    )
    result: Optional[ReliabilityResult] = evaluation.run(print_results=True)
    result.assert_passed()


if __name__ == "__main__":
    factorial()
