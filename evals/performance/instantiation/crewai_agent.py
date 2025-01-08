"""Run `pip install crewai openai memory_profiler` to install dependencies."""

from crewai.agent import Agent
from agno.eval.perf import PerfEval

def instantiate_agent():
    return Agent(role='Test Agent', goal='Be concise, reply with one sentence.', backstory='Test')

crew_instantiation_perf = PerfEval(func=instantiate_agent, num_iterations=10, show_results=True)

if __name__ == "__main__":
    crew_instantiation_perf.run()
