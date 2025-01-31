"""Run `pip install memory_profiler smolagents` to install dependencies."""

from agno.eval.perf import PerfEval
from smolagents import ToolCallingAgent, HfApiModel

def instantiate_agent():
    return ToolCallingAgent(tools=[], model=HfApiModel(model_id="meta-llama/Llama-3.3-70B-Instruct"))

smolagents_instantiation = PerfEval(func=instantiate_agent, num_iterations=10)

if __name__ == "__main__":
    smolagents_instantiation.run(print_results=True)
