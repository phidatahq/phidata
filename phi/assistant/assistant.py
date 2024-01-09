from typing import Optional

from phi.task.task import Task
from phi.task.llm import LLMTask
from phi.tools.function import Function


class Assistant(LLMTask):
    name: str = "assistant"
    description: Optional[str] = None

    def get_delegation_function(self, task: Task) -> Function:
        # Update assistant task
        self.conversation_id = task.conversation_id
        self.conversation_memory = task.conversation_memory
        self.conversation_message = task.conversation_message
        self.conversation_tasks = task.conversation_tasks

        # Prepare the delegation function
        f_name = f"run_{self.name}"
        f_description = f"Call this function to use the {self.__class__.__name__}."
        if self.description:
            f_description += f" {self.description}."
        f_description += "\n"
        f_description += f"""
        <instructions>
        - Only delegate 1 task at a time.
        - The task_description should be as specific as possible to avoid ambiguity.
        - The task_description should be in the language you would expect it.
        </instructions>

        @param task_description: A description of the task to be achieved by the {self.__class__.__name__}
        @return: The result of the task.
        """

        def delegation_function(task_description: str):
            return self.run(task_description, stream=False)

        _f = Function.from_callable(delegation_function)
        _f.name = f_name
        _f.description = f_description

        return _f
