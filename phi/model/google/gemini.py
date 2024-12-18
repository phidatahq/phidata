from os import getenv
import time
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Iterator, Dict, Any, Union, Callable

from phi.model.base import Model
from phi.model.message import Message
from phi.model.response import ModelResponse
from phi.tools.function import Function, FunctionCall
from phi.tools import Tool, Toolkit
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call

try:
    from google import genai
    from google.genai import types
except (ModuleNotFoundError, ImportError):
    raise ImportError("`google-genai` not installed. Please install it using `pip install google-genai`")

@dataclass
class MessageData:
    response_content: str = ""
    response_parts: Optional[List] = None
    response_tool_calls: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class Metrics:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    time_to_first_token: Optional[float] = None
    response_timer: Timer = field(default_factory=Timer)

    def log(self):
        logger.debug("**************** METRICS START ****************")
        if self.time_to_first_token is not None:
            logger.debug(f"* Time to first token:         {self.time_to_first_token:.4f}s")
        logger.debug(f"* Time to generate response:   {self.response_timer.elapsed:.4f}s")
        logger.debug(f"* Input tokens:                {self.input_tokens}")
        logger.debug(f"* Output tokens:               {self.output_tokens}")
        logger.debug(f"* Total tokens:                {self.total_tokens}")
        logger.debug("**************** METRICS END ******************")

class Gemini(Model):
    id: str = "gemini-2.0-flash-exp"
    name: str = "Gemini"
    provider: str = "GenAI"

    # Initialization parameters
    api_key: Optional[str] = None
    model: Optional[genai.Client] = None

    def get_client(self) -> genai.Client:
        """
        Returns an instance of the GenAI Client.

        Returns:
            genai.Client: The GenAI Client.
        """
        if not self.model:
            self.api_key = self.api_key or getenv("GOOGLE_API_KEY")
            if not self.api_key:
                logger.error("GOOGLE_API_KEY not set. Please set the GOOGLE_API_KEY environment variable.")
                raise ValueError("API key not provided.")
            self.model = genai.Client(api_key=self.api_key)
        return self.model

    def invoke(self, messages: List[Message]):
        """
        Invokes the model with a list of messages and returns the response.

        Args:
            messages (List[Message]): The list of messages to send to the model.

        Returns:
            dict: The response from the model.
        """
        client = self.get_client()
        formatted_messages = self.format_messages(messages)
        response = client.models.generate_content(
            model=self.id,
            contents=formatted_messages
        )
        return response

    def format_messages(self, messages: List[Message]) -> List[str]:
        """
        Formats messages into the string format required by GenAI.

        Args:
            messages (List[Message]): The list of messages to format.

        Returns:
            List[str]: A list of formatted message strings.
        """
        return [message.content for message in messages]

    def response(self, messages: List[Message]) -> ModelResponse:
        """
        Sends a generate content request to the model and returns the response.

        Args:
            messages (List[Message]): The list of messages to send to the model.

        Returns:
            ModelResponse: The model response.
        """
        logger.debug("---------- GenAI Response Start ----------")
        self._log_messages(messages)
        model_response = ModelResponse()
        metrics = Metrics()

        # Generate response
        metrics.response_timer.start()
        response = self.invoke(messages=messages)
        metrics.response_timer.stop()

        # Process response
        response_text = response.text
        assistant_message = Message(role="assistant", content=response_text)
        model_response.content = response_text

        # Log metrics
        metrics.log()
        logger.debug("---------- GenAI Response End ----------")
        return model_response
