from typing import List, Any, Optional, cast

from pydantic import BaseModel

from phi.llm.base import LLM
from phi.llm.message import Message
from phi.memory.memory import Memory
from phi.utils.log import logger


class MemoryClassifier(BaseModel):
    llm: Optional[LLM] = None

    # Provide the system prompt for the classifier as a string
    system_prompt: Optional[str] = None
    # Existing Memories
    existing_memories: Optional[List[Memory]] = None

    def update_llm(self) -> None:
        if self.llm is None:
            try:
                from phi.llm.openai import OpenAIChat
            except ModuleNotFoundError as e:
                logger.exception(e)
                logger.error(
                    "phidata uses `openai` as the default LLM. " "Please provide an `llm` or install `openai`."
                )
                exit(1)

            self.llm = OpenAIChat()

    def get_system_prompt(self) -> Optional[str]:
        # If the system_prompt is provided, use it
        if self.system_prompt is not None:
            return self.system_prompt

        # -*- Build a default system prompt for classification
        system_prompt_lines = [
            "Your task is to identify if the user's message contains information that is worth remembering for future conversations.",
            "This includes details that could personalize ongoing interactions with the user, such as:\n"
            "  - Personal facts: name, age, occupation, location, interests, preferences, etc.\n"
            "  - Significant life events or experiences shared by the user\n"
            "  - Important context about the user's current situation, challenges or goals\n"
            "  - What the user likes or dislikes, their opinions, beliefs, values, etc.\n"
            "  - Any other details that provide valuable insights into the user's personality, perspective or needs",
            "Your task is to decide whether the user input contains any of the above information worth remembering.",
            "If the user input contains any information worth remembering for future conversations, respond with 'yes'.",
            "If the input does not contain any important details worth saving, respond with 'no' to disregard it.",
            "You will also be provided with a list of existing memories to help you decide if the input is new or already known.",
            "If the memory already exists that matches the input, respond with 'no' to keep it as is.",
            "If a memory exists that needs to be updated or deleted, respond with 'yes' to update/delete it.",
            "You must only respond with 'yes' or 'no'. Nothing else will be considered as a valid response.",
        ]
        if self.existing_memories and len(self.existing_memories) > 0:
            system_prompt_lines.extend(
                [
                    "\nExisting memories:",
                    "<existing_memories>\n"
                    + "\n".join([f"  - {m.memory}" for m in self.existing_memories])
                    + "\n</existing_memories>",
                ]
            )
        return "\n".join(system_prompt_lines)

    def run(
        self,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        logger.debug("*********** MemoryClassifier Start ***********")

        # Update the LLM (set defaults, add logit etc.)
        self.update_llm()

        # -*- Prepare the List of messages sent to the LLM
        llm_messages: List[Message] = []

        # Get the System prompt
        system_prompt = self.get_system_prompt()
        # Create system prompt message
        system_prompt_message = Message(role="system", content=system_prompt)
        # Add system prompt message to the messages list
        if system_prompt_message.content_is_valid():
            llm_messages.append(system_prompt_message)

        # Build the user prompt message
        user_prompt_message = Message(role="user", content=message, **kwargs) if message else None
        if user_prompt_message is not None:
            llm_messages += [user_prompt_message]

        # -*- generate_a_response_from_the_llm (includes_running_function_calls)
        self.llm = cast(LLM, self.llm)
        classification_response = self.llm.response(messages=llm_messages)
        logger.debug("*********** MemoryClassifier End ***********")
        return classification_response
