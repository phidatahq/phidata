from typing import Optional

from phi.eval import Eval, EvalResult

from agents.example import get_example_agent


def test_haiku():
    evaluation = Eval(
        agent=get_example_agent(),
        question="Share a haiku",
        expected_answer="Any haiku",
    )
    result: Optional[EvalResult] = evaluation.print_result()

    assert result is not None and result.accuracy_score >= 7


test_haiku()
