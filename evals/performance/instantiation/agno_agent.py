"""Run `pip install agno openai memory_profiler` to install dependencies."""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.eval.perf import PerfEval

def instantiate_agent():
    return Agent(model=OpenAIChat(id='gpt-4o'), system_message='Be concise, reply with one sentence.')

agno_instantiation_perf = PerfEval(func=instantiate_agent, num_iterations=10, show_results=True)

if __name__ == "__main__":
    agno_instantiation_perf.run()
