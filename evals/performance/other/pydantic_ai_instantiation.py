"""Run `pip install openai memory_profiler pydantic-ai` to install dependencies."""

from pydantic_ai import Agent
from agno.eval.perf import PerfEval

def instantiate_agent():
    return Agent('openai:gpt-4o', system_prompt='Be concise, reply with one sentence.')

pydantic_instantiation = PerfEval(func=instantiate_agent, num_iterations=10)

if __name__ == "__main__":
    pydantic_instantiation.run(print_results=True)
