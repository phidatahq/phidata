"""Run `pip install openai agno memory_profiler` to install dependencies."""

from agno.agent.agent import Agent
from agno.utils.timer import Timer

import statistics
from memory_profiler import profile

@profile
def instantiate_agent():
    Agent()

def measure_agent_performance(num_runs=3):
    times = []

    for i in range(num_runs):
        timer = Timer()
        timer.start()
        instantiate_agent()
        timer.stop()

        times.append(timer.elapsed)
        print(f"\nRun {i+1}:")
        print(f"Time taken: {timer.elapsed:.6f} seconds")

    print("\nPerformance Summary:")
    print(f"Average time: {statistics.mean(times):.6f} seconds")
    print(f"Min time: {min(times):.6f} seconds")
    print(f"Max time: {max(times):.6f} seconds")
    print(f"Standard deviation: {statistics.stdev(times):.6f} seconds")

if __name__ == "__main__":
    measure_agent_performance()
