"""Run `pip install openai agno memory_profiler` to install dependencies."""

from agno.agent.agent import Agent
from agno.eval.perf import FunctionEval

def instantiate_agent():
    return Agent()

eval_agent_instantiation = FunctionEval(func=instantiate_agent, num_iterations=10, show_results=True)

if __name__ == "__main__":
    eval_agent_instantiation.run()
