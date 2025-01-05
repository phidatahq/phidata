"""Run `pip install openai agno memory_profiler` to install dependencies."""

from rich.pretty import pprint
from agno.agent import Agent, RunResponse
from agno.models.openai import OpenAIChat
import time
import statistics
import cProfile
import pstats
from memory_profiler import profile

@profile
def run_agent():
    agent = Agent(
        model=OpenAIChat(id="gpt-4"),
        instructions="Write a poem, it should be less than 5 lines",
    )
    # run: RunResponse = agent.run("Write a poem about moonlight feeling peaceful")
    # return run

def measure_agent_performance(num_runs=3):
    times = []
    results = []

    # Set up cProfile
    profiler = cProfile.Profile()
    profiler.enable()

    for i in range(num_runs):
        start_time = time.time()
        run = run_agent()
        end_time = time.time()

        elapsed_time = end_time - start_time
        times.append(elapsed_time)
        results.append(run)

        print(f"\nRun {i+1}:")
        print(f"Time taken: {elapsed_time:.6f} seconds")
        # pprint(run)

    # Disable and print cProfile results
    profiler.disable()

    print("\nPerformance Summary:")
    print(f"Average time: {statistics.mean(times):.6f} seconds")
    print(f"Min time: {min(times):.6f} seconds")
    print(f"Max time: {max(times):.6f} seconds")
    print(f"Standard deviation: {statistics.stdev(times):.6f} seconds")

    # print("\ncProfile Results:")
    stats = pstats.Stats(profiler)
    # stats.sort_stats('cumulative').print_stats(20)  # Show top 20 functions by cumulative time

if __name__ == "__main__":
    measure_agent_performance()
