from __future__ import annotations

from enum import Enum
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from phi.agent import Agent

from pydantic import BaseModel, Field

from phi.model.base import Model


class NextAction(str, Enum):
    CONTINUE = "continue"
    VALIDATE = "validate"
    FINAL_ANSWER = "final_answer"


class ReasoningStep(BaseModel):
    title: Optional[str] = Field(None, description="A concise title summarizing the step's purpose")
    action: Optional[str] = Field(
        None, description="The action derived from this step. Talk in first person like I will ... "
    )
    result: Optional[str] = Field(
        None, description="The result of executing the action. Talk in first person like I did this and got ... "
    )
    reasoning: Optional[str] = Field(None, description="The thought process and considerations behind this step")
    next_action: Optional[NextAction] = Field(
        None,
        description="Indicates whether to continue reasoning, validate the provided result, or confirm that the result is the final answer",
    )
    confidence: Optional[float] = Field(None, description="Confidence score for this step (0.0 to 1.0)")


class ReasoningSteps(BaseModel):
    reasoning_steps: List[ReasoningStep] = Field(..., description="A list of reasoning steps")


class Reasoning(BaseModel):
    model: Optional[Model] = None
    agent: Optional[Agent] = None
    max_steps: int = 10
