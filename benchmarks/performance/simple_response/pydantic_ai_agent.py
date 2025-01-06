"""Run `pip install openai pydantic-ai memory_profiler` to install dependencies."""

from pydantic_ai import Agent
from agno.eval.perf import PerfEval

def simple_response():
    agent = Agent('openai:gpt-4o-mini', system_prompt='Be concise, reply with one sentence.')
    response = agent.run_sync('What is the capital of France?')
    print(response.data)
    return response

simple_response_eval = PerfEval(func=simple_response, num_iterations=10, show_results=True)

if __name__ == "__main__":
    simple_response_eval.run()
