import json
from dataclasses import dataclass, field
from typing import Optional, List, Iterator, Dict, Any, Union, Tuple

from phi.model.base import Model
from phi.model.message import Message
from phi.model.response import ModelResponse
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import (
    get_function_call_for_tool_call,
)

try:
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        StoppingCriteria,
        StoppingCriteriaList,
    )
except ImportError:
    logger.error("Please install transformers with `pip install transformers[torch]`")
    raise

class HuggingFaceModel(Model):
    """
    Class for  Hugging Face models using AutoModelForCausalLM.
    """

    id: str = "mistralai/Mistral-7B-Instruct-v0.2"
    name: str = "HuggingFace"
    provider: str = "HuggingFace"
    
    model: Optional[AutoModelForCausalLM] = None
    tokenizer: Optional[AutoTokenizer] = None
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    max_length: int = 2048
    temperature: float = 0.7
    
    def __init__(self, model_id: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        if model_id:
            self.id = model_id
            
        self.tokenizer = AutoTokenizer.from_pretrained(self.id)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.id,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto"
        )

    def _format_messages_to_prompt(self, messages: List[Message]) -> str:
        """Format messages into a prompt string."""
        formatted_messages = []
        for message in messages:
            role = message.role
            content = message.get_content_string()
            
            if role == "system":
                formatted_messages.append(f"<|system|>{content}")
            elif role == "user":
                formatted_messages.append(f"<|user|>{content}")
            elif role == "assistant":
                formatted_messages.append(f"<|assistant|>{content}")
            
        return "\n".join(formatted_messages)

    def get_response(
        self,
        messages: List[Message],
        stream: bool = False,
        **kwargs: Any,
    ) -> Union[ModelResponse, Iterator[ModelResponse]]:
        """Get a response from the model."""
        try:
            prompt = self._format_messages_to_prompt(messages)
            
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=self.max_length,
                    temperature=self.temperature,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    **kwargs
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            response = response[len(prompt):]
            
            return response

        except Exception as e:
            logger.error(f"Error getting response: {e}")
            raise