from typing import Optional

from phi.agent import Agent
from phi.eval import Eval, EvalResult
from phi.model.openai import OpenAIChat
from phi.tools.calculator import Calculator


def multiply_and_exponentiate():
    evaluation = Eval(
        agent=Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            tools=[Calculator(add=True, multiply=True, exponentiate=True)],
        ),
        question="What is 10*5 then to the power of 2? do it step by step",
        expected_answer="2500",
    )
    result: Optional[EvalResult] = evaluation.print_result()

    assert result is not None and result.accuracy_score >= 8


def factorial():
    evaluation = Eval(
        agent=Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            tools=[Calculator(factorial=True)],
        ),
        question="What is 10!?",
        expected_answer="3628800",
    )
    result: Optional[EvalResult] = evaluation.print_result()

    assert result is not None and result.accuracy_score >= 8


if __name__ == "__main__":
    multiply_and_exponentiate()
    factorial()
