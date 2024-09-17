import json
from typing import Optional, List, Iterator, Dict, Any, Union

from phi.llm.message import Message
from phi.llm.aws.bedrock import AwsBedrock

class Claude(AwsBedrock):
    name: str = "AwsBedrockAnthropicClaude"
    model: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    # -*- Request parameters
    max_tokens: int = 8192
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    anthropic_version: str = "bedrock-2023-05-31"
    request_params: Optional[Dict[str, Any]] = None
    # -*- Client parameters
    client_params: Optional[Dict[str, Any]] = None

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        _request_params: Dict[str, Any] = {}
        if self.anthropic_version:
            _request_params["anthropic_version"] = self.anthropic_version
        if self.max_tokens:
            _request_params["max_tokens"] = self.max_tokens
        if self.temperature:
            _request_params["temperature"] = self.temperature
        if self.stop_sequences:
            _request_params["stop_sequences"] = self.stop_sequences
        if self.tools is not None:
            if _request_params.get("stop_sequences") is None:
                _request_params["stop_sequences"] = ["</function_calls>"]
            elif "</function_calls>" not in _request_params["stop_sequences"]:
                _request_params["stop_sequences"].append("</function_calls>")
        if self.top_p:
            _request_params["top_p"] = self.top_p
        if self.top_k:
            _request_params["top_k"] = self.top_k
        if self.request_params:
            _request_params.update(self.request_params)
        return _request_params

    def get_tools(self):
        """
        Refactors the tools in a format accepted by the Anthropic API.
        """
        if not self.functions:
            return None

        tools: List = []
        for f_name, function in self.functions.items():
            required_params = [
                param_name
                for param_name, param_info in function.parameters.get("properties", {}).items()
                if "null"
                not in (
                    param_info.get("type") if isinstance(param_info.get("type"), list) else [param_info.get("type")]
                )
            ]
            tools.append(
                {
                    "toolSpec": {
                        "name": f_name,
                        "description": function.description or "",
                        "inputSchema": {
                                "json": {
                                "type": function.parameters.get("type") or "object",
                                "properties": {
                                    param_name: {
                                        "type": param_info.get("type") or "",
                                        "description": param_info.get("description") or "",
                                    }
                                    for param_name, param_info in function.parameters.get("properties", {}).items()
                                },
                                "required": required_params,
                            }
                        },
                    }
                }
            )
        return tools

    def get_request_body(self, messages: List[Message]) -> Dict[str, Any]:
        system_prompt = None
        messages_for_api = []
        for m in messages:
            if m.role == "system":
                system_prompt = m.content
            else:
                messages_for_api.append({
                    "role": m.role, 
                    "content": [{"text": m.content}]
                })

        # -*- Build request body
        request_body = {
            "messages": messages_for_api,
            **self.api_kwargs,
        }
        if self.tools:
            request_body["tools"] = self.get_tools()            

        if system_prompt:
            request_body["system"] = system_prompt
        return request_body

    def parse_response_message(self, response: Dict[str, Any]) -> Message:
        output = response.get("output", {})
        message = output.get("message", {})
        
        role = message.get("role", "assistant")
        content = message.get("content", [])
        
        if isinstance(content, list):
            text_content = "\n".join([item.get("text", "") for item in content if isinstance(item, dict)])
        elif isinstance(content, dict):
            text_content = content.get("text", "")
        elif isinstance(content, str):
            text_content = content
        else:
            text_content = ""
        
        return Message(role=role, content=text_content)

    def parse_response_delta(self, response: Dict[str, Any]) -> Optional[str]:
        if "delta" in response:
            return response.get("delta", {}).get("text")
        return response.get("completion")