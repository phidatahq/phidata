from typing import Optional

from phi.task.llm import LLMTask
from phi.conversation import Conversation


class Agent(Conversation):
    def get_agent_system_prompt(self) -> Optional[str]:
        """Return the system prompt for the agent"""

    @property
    def llm_task(self) -> LLMTask:
        _llm_task = super().llm_task

        # If a custom system prompt is not set for the agent, use the default agent prompt
        if self.system_prompt is None or self.system_prompt_function is None:
            _llm_task.system_prompt = self.get_agent_system_prompt()

        return _llm_task
