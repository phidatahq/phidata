from dataclasses import dataclass, field
from typing import Optional

from agno.utils.log import logger
from agno.utils.timer import Timer


@dataclass
class Metrics:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    prompt_tokens: int = 0
    completion_tokens: int = 0
    prompt_tokens_details: Optional[dict] = None
    completion_tokens_details: Optional[dict] = None

    time_to_first_token: Optional[float] = None
    response_timer: Timer = field(default_factory=Timer)

    def start_response_timer(self):
        self.response_timer.start()

    def stop_response_timer(self):
        self.response_timer.stop()

    def _log(self, metric_lines: list[str]):
        logger.debug("**************** METRICS START ****************")
        for line in metric_lines:
            logger.debug(line)
        logger.debug("**************** METRICS END ******************")

    def log(self):
        metric_lines = []
        if self.time_to_first_token is not None:
            metric_lines.append(f"* Time to first token:         {self.time_to_first_token:.4f}s")
        metric_lines.extend(
            [
                f"* Time to generate response:   {self.response_timer.elapsed:.4f}s",
                f"* Tokens per second:           {self.output_tokens / self.response_timer.elapsed:.4f} tokens/s",
                f"* Input tokens:                {self.input_tokens or self.prompt_tokens}",
                f"* Output tokens:               {self.output_tokens or self.completion_tokens}",
                f"* Total tokens:                {self.total_tokens}",
            ]
        )
        if self.prompt_tokens_details is not None:
            metric_lines.append(f"* Prompt tokens details:       {self.prompt_tokens_details}")
        if self.completion_tokens_details is not None:
            metric_lines.append(f"* Completion tokens details:   {self.completion_tokens_details}")
        self._log(metric_lines=metric_lines)
