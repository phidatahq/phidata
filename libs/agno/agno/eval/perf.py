from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, List, Optional

from memory_profiler import memory_usage

from agno.utils.log import logger
from agno.utils.timer import Timer

if TYPE_CHECKING:
    from rich.console import Console


@dataclass
class PerfResult:
    # Run time performance in seconds
    run_times: List[float] = field(default_factory=list)
    avg_run_time: float = field(init=False)
    min_run_time: float = field(init=False)
    max_run_time: float = field(init=False)
    std_dev_run_time: float = field(init=False)
    # Memory performance in MiB
    memory_usages: List[float] = field(default_factory=list)
    avg_memory_usage: float = field(init=False)
    min_memory_usage: float = field(init=False)
    max_memory_usage: float = field(init=False)
    std_dev_memory_usage: float = field(init=False)

    def __post_init__(self):
        import statistics

        if self.run_times:
            self.avg_run_time = statistics.mean(self.run_times)
            self.min_run_time = min(self.run_times)
            self.max_run_time = max(self.run_times)
            self.std_dev_run_time = statistics.stdev(self.run_times) if len(self.run_times) > 1 else 0

        if self.memory_usages:
            self.avg_memory_usage = statistics.mean(self.memory_usages)
            self.min_memory_usage = min(self.memory_usages)
            self.max_memory_usage = max(self.memory_usages)
            self.std_dev_memory_usage = statistics.stdev(self.memory_usages) if len(self.memory_usages) > 1 else 0

    def print_summary(self, console: Optional["Console"] = None):
        from rich.table import Table

        # Create performance table
        perf_table = Table(title="Performance Summary", show_header=True, header_style="bold magenta")
        perf_table.add_column("Metric", style="cyan")
        perf_table.add_column("Time (seconds)", style="green")
        perf_table.add_column("Memory (MiB)", style="yellow")

        # Add rows
        perf_table.add_row("Average", f"{self.avg_run_time:.6f}", f"{self.avg_memory_usage:.2f}")
        perf_table.add_row("Minimum", f"{self.min_run_time:.6f}", f"{self.min_memory_usage:.2f}")
        perf_table.add_row("Maximum", f"{self.max_run_time:.6f}", f"{self.max_memory_usage:.2f}")
        perf_table.add_row("Std Dev", f"{self.std_dev_run_time:.6f}", f"{self.std_dev_memory_usage:.2f}")

        console.print(perf_table)

    def print_runs(self, console: Optional["Console"] = None):
        from rich.table import Table

        # Create runs table
        runs_table = Table(title="Individual Runs", show_header=True, header_style="bold magenta")
        runs_table.add_column("Run #", style="cyan")
        runs_table.add_column("Time (seconds)", style="green")
        runs_table.add_column("Memory (MiB)", style="yellow")

        # Add rows
        for i in range(len(self.run_times)):
            runs_table.add_row(str(i + 1), f"{self.run_times[i]:.6f}", f"{self.memory_usages[i]:.2f}")

        console.print(runs_table)


@dataclass
class PerfEval:
    """Evaluate the performance of a function."""

    eval_id: Optional[str] = None

    # Function to evaluate
    func: Optional[Callable] = None
    # Number of iterations to run
    num_iterations: int = 3
    # Print summary of results
    print_summary: bool = False
    # Print detailed results
    print_results: bool = False
    # Result of the evaluation
    result: Optional[PerfResult] = None

    def run(self, *, print_summary: bool = False, print_results: bool = False) -> PerfResult:
        from rich.console import Console
        from rich.live import Live
        from rich.status import Status

        console = Console()
        run_times = []
        memory_usages = []
        self.print_summary = print_summary
        self.print_results = print_results

        # Add a spinner while running the evaluations
        with Live(console=console, transient=True) as live_log:
            status = Status("Running evaluation...", spinner="dots", speed=1.0, refresh_per_second=10)
            live_log.update(status)

            # Measure run time
            logger.debug("Measuring run time...", style="bold")
            for i in range(self.num_iterations):
                timer = Timer()
                # Start the timer
                timer.start()
                # Run the function
                self.func()
                # Stop the timer
                timer.stop()
                # Append the time taken
                run_times.append(timer.elapsed)
                logger.debug(f"\nRun {i+1}:", style="bold")
                logger.debug(f"Time taken: {timer.elapsed:.6f} seconds", style="green")

            # Measure memory usage
            logger.debug("Measuring memory usage...", style="bold")
            for i in range(self.num_iterations):
                mem_usage = memory_usage((self.func, (), {}), interval=0.1, max_iterations=1, max_usage=True)
                memory_usages.append(mem_usage)
                logger.debug(f"\nRun {i+1}:", style="bold")
                logger.debug(f"Memory usage: {mem_usage} MiB", style="green")

            # Stop the status after completion
            status.stop()

        # Create and store the result
        self.result = PerfResult(run_times=run_times, memory_usages=memory_usages)

        # Show results
        if self.print_summary or self.print_results:
            self.result.print_summary(console)
        if self.print_results:
            self.result.print_runs(console)

        return self.result
