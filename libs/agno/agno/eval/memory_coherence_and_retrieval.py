from dataclasses import asdict, dataclass, field
from typing import List, Optional, Dict, Any
from uuid import uuid4

from agno.utils.timer import Timer
from agno.utils.log import logger


@dataclass
class MemoryAccessMetrics:
    operation_type: str
    duration: float
    context: Dict[str, Any]


@dataclass
class MCRResult:
    context_scores: List[float] = field(default_factory=list)
    retention_rates: List[float] = field(default_factory=list)
    latency_measurements: List[float] = field(default_factory=list)
    
    avg_context_score: float = field(init=False)
    avg_retention_rate: float = field(init=False)
    avg_latency: float = field(init=False)
    mcr_score: float = field(init=False)

    def __post_init__(self):
        self.compute_stats()

    def compute_stats(self):
        import statistics

        self.avg_context_score = statistics.mean(self.context_scores) if self.context_scores else 0
        self.avg_retention_rate = statistics.mean(self.retention_rates) if self.retention_rates else 0
        self.avg_latency = statistics.mean(self.latency_measurements) if self.latency_measurements else 0
        
        # Calculate final MCR score
        self.mcr_score = (self.avg_context_score * self.avg_retention_rate) / (1 + self.avg_latency)

    def print_summary(self, console: Optional["Console"] = None):
        from rich.console import Console
        from rich.table import Table

        if console is None:
            console = Console()

        table = Table(title="Memory Coherence and Retrieval Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Context Preservation Score", f"{self.avg_context_score:.4f}")
        table.add_row("Information Retention Rate", f"{self.avg_retention_rate:.4f}")
        table.add_row("Retrieval Latency (s)", f"{self.avg_latency:.4f}")
        table.add_row("MCR Score", f"{self.mcr_score:.4f}")

        console.print(table)


@dataclass
class MCREval:
    """Evaluate memory coherence and retrieval performance."""

    # Number of iterations to run
    num_iterations: int = 3
    # Result of the evaluation
    result: Optional[MCRResult] = None
    # Evaluation UUID
    eval_id: str = field(default_factory=lambda: str(uuid4()))

    def _calculate_context_similarity(self, prev_context: Dict[str, Any], current_context: Dict[str, Any]) -> float:
        """Calculate similarity between two contexts using cosine similarity."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np

        # Convert contexts to strings for TF-IDF
        prev_str = " ".join(str(v) for v in prev_context.values())
        curr_str = " ".join(str(v) for v in current_context.values())
        
        vectorizer = TfidfVectorizer()
        try:
            tfidf_matrix = vectorizer.fit_transform([prev_str, curr_str])
            return float((tfidf_matrix * tfidf_matrix.T).A[0][1])
        except:
            return 0.0

    def _identify_critical_information(self, interaction_history: List[Dict[str, Any]]) -> List[str]:
        """Identify important information from interaction history."""
        # Implementation depends on your specific criteria for important information
        # This is a placeholder that returns all unique keys
        important_info = set()
        for interaction in interaction_history:
            important_info.update(interaction.keys())
        return list(important_info)

    def _check_information_retention(self, memory: Dict[str, Any], important_info: List[str]) -> List[str]:
        """Check which important information is retained in memory."""
        return [info for info in important_info if info in memory]

    def evaluate(self, agent_state: Any, interaction_history: List[Dict[str, Any]]) -> MCRResult:
        """Run the evaluation."""
        from rich.console import Console
        from rich.live import Live
        from rich.status import Status

        context_scores = []
        retention_rates = []
        latency_measurements = []

        console = Console()
        with Live(console=console, transient=True) as live_log:
            for i in range(self.num_iterations):
                status = Status(f"Running evaluation {i + 1}...", spinner="dots")
                live_log.update(status)

                # Measure context preservation
                timer = Timer()
                timer.start()
                context_score = self._calculate_context_similarity(
                    interaction_history[i].get('context', {}),
                    interaction_history[i+1].get('context', {}) if i+1 < len(interaction_history) else {}
                )
                timer.stop()
                context_scores.append(context_score)

                # Measure retention rate
                important_info = self._identify_critical_information(interaction_history)
                retained_info = self._check_information_retention(agent_state.memory, important_info)
                retention_rate = len(retained_info) / len(important_info) if important_info else 0
                retention_rates.append(retention_rate)

                # Measure retrieval latency
                latency_measurements.append(timer.elapsed)

        self.result = MCRResult(
            context_scores=context_scores,
            retention_rates=retention_rates,
            latency_measurements=latency_measurements
        )

        return self.result
