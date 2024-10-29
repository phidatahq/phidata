from typing import Optional, List
from phi.llm.openai.like import OpenAILike
from enum import Enum
import requests
from phi.llm.message import Message
from pydantic import Field


class CloudflareModel(Enum):
    LLAMA_3_8B_INSTRUCT = "@cf/meta/llama-3-8b-instruct"

    @classmethod
    def list_models(cls):
        return [model.name for model in cls]
    
class CloudflareChat(OpenAILike):
    """
    CloudflareChat class to interact with Cloudflare's AI workers.
    
    Available models:
    - LLAMA_2_7B_CHAT_FP16
    - LLAMA_2_7B_CHAT_INT8
    - LLAMA_3_8B_INSTRUCT_AWQ
    - LLAMA_3_8B_INSTRUCT
    - LLAMA_3_1_70B_INSTRUCT
    - LLAMA_3_1_8B_INSTRUCT_AWQ
    - LLAMA_3_1_8B_INSTRUCT_FAST
    - LLAMA_3_1_8B_INSTRUCT_FP8
    - LLAMA_3_2_11B_VISION_INSTRUCT
    """

    name: str = "CloudflareChat"
    api_key: Optional[str] = None
    account_id: Optional[str] = None
    model: CloudflareModel = Field(default=CloudflareModel.LLAMA_3_8B_INSTRUCT)
    base_url: str = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/"

    def __init__(self, api_key: Optional[str], account_id: str, model: CloudflareModel = CloudflareModel.LLAMA_3_8B_INSTRUCT):
        super().__init__(api_key=api_key)
        self.api_key = api_key
        self.account_id = account_id

        if not isinstance(model, CloudflareModel):
            raise ValueError(f"Invalid model specified. Choose from: {', '.join(CloudflareModel.list_models())}")
        
        self.model = model

        if self.account_id is None:
            raise ValueError("account_id must be specified")

        if self.api_key is None:
            raise ValueError("api_key must be specified")

    @property
    def full_url(self) -> str:
        """Returns the complete URL with the specified model."""
        return f"{self.base_url.format(account_id=self.account_id)}{self.model.value}"

    def _get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _call_for_prompt(self, prompt: Optional[List]) -> dict:
        """
        Call the Cloudflare API with the specified prompt and model.
        It will return the response as a dictionary.
        """
        headers = self._get_headers()
        payload = { "messages": prompt }
        
        try:
            print(f"Sending request to {self.full_url} with payload: {payload}")

            response = requests.post(self.full_url, headers=headers, json=payload)
            response.raise_for_status()  # Raises an HTTPError if the response was an error
            return response.json()
        except requests.exceptions.RequestException as e:
            # logger.error(f"API request failed: {e}")
            return {"error": str(e)}

    def invoke(self, message: Message) -> dict:
        """
        Invoke the Cloudflare API with the specified messages.
        
        Args:
            messages (List[Message]): The messages to send to the model.

        Returns:
            List[Dict]: The response from the model for each message.
        """
        if not message:
            raise ValueError("No messages provided")

        return self._call_for_prompt(message.to_dict()["content"])

# test call 
# api_key = ""
# account_id = ""
# inputs = [
#     { "role": "system", "content": "You are a friendly assistan that helps write stories" },
#     { "role": "user", "content": "Write a short story about a llama that goes on a journey to find an orange cloud "}
# ]

# obj = CloudflareChat(api_key=api_key, account_id=account_id, model=CloudflareModel.LLAMA_3_8B_INSTRUCT)
# message = Message(role="system", content=inputs)

# response = obj.invoke(message)
# print(response)
