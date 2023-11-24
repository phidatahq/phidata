from typing import Optional, Dict, Any, List

from phi.llm.aws.bedrock import AwsBedrock


class AnthropicClaude(AwsBedrock):
    name: str = "AwsBedrockClaude"
    model: str = "anthropic.claude-v2"
    max_tokens: int = 8192
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stop_sequences: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        _dict = super().to_dict()
        _dict["max_tokens"] = self.max_tokens
        _dict["temperature"] = self.temperature
        _dict["top_p"] = self.top_p
        _dict["top_k"] = self.top_k
        _dict["stop_sequences"] = self.stop_sequences
        return _dict

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if self.max_tokens:
            kwargs["max_tokens_to_sample"] = self.max_tokens
        if self.temperature:
            kwargs["temperature"] = self.temperature
        if self.top_p:
            kwargs["top_p"] = self.top_p
        if self.top_k:
            kwargs["top_k"] = self.top_k
        if self.stop_sequences:
            kwargs["stop_sequences"] = self.stop_sequences
        return kwargs
