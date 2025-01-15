"""Run `pip install openai memory_profiler crewai` to install dependencies."""

from crewai.agent import Agent
from agno.eval.perf import PerfEval

def instantiate_agent():
    return Agent(llm='gpt-4o', role='Test Agent', goal='Be concise, reply with one sentence.', backstory='Test')

crew_instantiation = PerfEval(func=instantiate_agent, num_iterations=10)

if __name__ == "__main__":
    crew_instantiation.run(print_results=True)
