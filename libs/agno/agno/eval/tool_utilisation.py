from dataclasses import dataclass, field
from typing import List, Optional, Dict
from uuid import uuid4

from pydantic import BaseModel, Field


class ToolUtilisationResponse(BaseModel):
    tool_selection_accuracy: float = Field(..., description="Score for selecting the right tools")
    usage_efficiency: float = Field(..., description="Score for efficient tool usage")
    api_precision: float = Field(..., description="Score for API call precision")
    overall_score: float = Field(..., description="Combined weighted score")
    evaluation_reason: str = Field(..., description="Detailed reasoning for the scores")


@dataclass
class ToolUtilisationEvaluation:
    interaction_history: List[Dict]
    tool_selection_score: float
    usage_efficiency_score: float
    api_precision_score: float
    overall_score: float
    reason: str

    def print_eval(self, console: Optional["Console"] = None):
        from rich.box import ROUNDED
        from rich.console import Console
        from rich.table import Table

        if console is None:
            console = Console()

        results_table = Table(
            box=ROUNDED,
            border_style="blue",
            show_header=False,
            title="[ Tool Utilisation Evaluation ]",
            title_style="bold sky_blue1",
            title_justify="center",
        )
        results_table.add_row("Tool Selection Score", f"{self.tool_selection_score:.2f}")
        results_table.add_row("Usage Efficiency Score", f"{self.usage_efficiency_score:.2f}")
        results_table.add_row("API Precision Score", f"{self.api_precision_score:.2f}")
        results_table.add_row("Overall Score", f"{self.overall_score:.2f}")
        results_table.add_row("Evaluation Reason", self.reason)
        console.print(results_table)


@dataclass
class ToolUtilisationResult:
    results: List[ToolUtilisationEvaluation] = field(default_factory=list)
    avg_score: float = field(init=False)
    min_score: float = field(init=False)
    max_score: float = field(init=False)
    std_dev_score: float = field(init=False)

    def __post_init__(self):
        self.compute_stats()

    def compute_stats(self):
        import statistics

        if self.results:
            scores = [r.overall_score for r in self.results]
            self.avg_score = statistics.mean(scores)
            self.min_score = min(scores)
            self.max_score = max(scores)
            self.std_dev_score = statistics.stdev(scores) if len(scores) > 1 else 0


@dataclass
class ToolUtilisationEval:
    name: Optional[str] = None
    eval_id: Optional[str] = None
    weights: Dict[str, float] = field(default_factory=lambda: {"tool_selection": 0.4, "usage_efficiency": 0.3, "api_precision": 0.3})
    
    def set_eval_id(self) -> str:
        if self.eval_id is None:
            self.eval_id = str(uuid4())
        return self.eval_id

    def _determine_optimal_tool(self, task_requirements: Dict) -> str:
        # Implementation specific to your tool selection logic
        pass

    def _analyze_necessary_calls(self, interaction_history: List[Dict]) -> int:
        # Implementation specific to your efficiency analysis
        pass

    def _calculate_resource_usage(self, interaction_history: List[Dict]) -> float:
        # Implementation specific to your resource usage calculation
        pass

    def _validate_api_parameters(self, parameters: Dict) -> bool:
        # Implementation specific to your API validation
        pass

    def calculate(self, agent_state: Dict, interaction_history: List[Dict]) -> float:
        def calculate_tool_selection_accuracy() -> float:
            correct_selections = 0
            total_selections = len(interaction_history)
            
            for interaction in interaction_history:
                selected_tool = interaction.get("selected_tool")
                task_requirements = interaction.get("task_requirements", {})
                optimal_tool = self._determine_optimal_tool(task_requirements)
                
                if selected_tool == optimal_tool:
                    correct_selections += 1
            
            return correct_selections / total_selections if total_selections > 0 else 0
        
        def calculate_usage_efficiency() -> float:
            total_calls = len([call for interaction in interaction_history for call in interaction.get("tool_calls", [])])
            necessary_calls = self._analyze_necessary_calls(interaction_history)
            resource_usage = self._calculate_resource_usage(interaction_history)
            
            return (necessary_calls / total_calls) * (1 - resource_usage/100) if total_calls > 0 else 0
        
        def calculate_api_precision() -> float:
            valid_calls = 0
            total_calls = 0
            
            for interaction in interaction_history:
                for call in interaction.get("api_calls", []):
                    if self._validate_api_parameters(call.get("parameters", {})):
                        valid_calls += 1
                    total_calls += 1
            
            return valid_calls / total_calls if total_calls > 0 else 0

        return (
            self.weights["tool_selection"] * calculate_tool_selection_accuracy() +
            self.weights["usage_efficiency"] * calculate_usage_efficiency() +
            self.weights["api_precision"] * calculate_api_precision()
        )
