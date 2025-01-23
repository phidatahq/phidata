from typing import Optional

from agno.agent import Agent
from agno.eval.reliability import ReliabilityEval, ReliabilityResult
from agno.tools.calculator import Calculator


def multiply_and_exponentiate():
    from agno.models.openai import OpenAIChat
    
    evaluation = ReliabilityEval(
        agent=Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            tools=[Calculator(add=True, multiply=True, exponentiate=True)],
        ),
        question="What is 10*5 then to the power of 2? do it step by step",
        expected_tool_calls=["multiply", "exponentiate"],
    )
    result: Optional[ReliabilityResult] = evaluation.run(print_results=True)


def factorial():
    from agno.models.openai import OpenAIChat

    evaluation = ReliabilityEval(
        agent=Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            tools=[Calculator(factorial=True)],
        ),
        question="What is 10!?",
        expected_tool_calls=["factorial"],
    )
    result: Optional[ReliabilityResult] = evaluation.run(print_results=True)


if __name__ == "__main__":
    multiply_and_exponentiate()
    # factorial()
