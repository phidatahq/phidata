"""Run `pip install openai pydantic-ai memory_profiler` to install dependencies."""

from pydantic_ai import Agent
from agno.eval.perf import PerfEval

def instantiate_agent():
    return Agent('openai:gpt-4o', system_prompt='Be concise, reply with one sentence.')

pydantic_instantiation_perf = PerfEval(func=instantiate_agent, num_iterations=10, show_results=True)

if __name__ == "__main__":
    pydantic_instantiation_perf.run()
