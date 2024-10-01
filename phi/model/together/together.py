import json
from os import getenv
from typing import Optional, List, Iterator, Dict, Any

from phi.model.message import Message
from phi.model.openai.like import OpenAILike
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call


class Together(OpenAILike):
    """
    Together model class.

    Args:
        id (str): The id of the Anyscale model to use. Default is "mistralai/Mixtral-8x7B-Instruct-v0.1".
        name (str): The name of this chat model instance. Default is "Anyscale"
        provider (str): The provider of the model. Default is "Anyscale".
        api_key (str): The api key to authorize request to Anyscale.
        base_url (str): The base url to which the requests are sent.
    """

    id: str = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    name: str = "Together"
    provider: str = "Together"
    api_key: Optional[str] = getenv("TOGETHER_API_KEY")
    base_url: str = "https://api.together.xyz/v1"
    monkey_patch: bool = False

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        if not self.monkey_patch:
            yield from super().response_stream(messages)
            return

        logger.debug("---------- Together Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        agent_message_content = ""
        response_is_tool_call = False
        completion_tokens = 0
        response_timer = Timer()
        response_timer.start()
        for response in self.invoke_stream(messages=messages):
            # logger.debug(f"Together response type: {type(response)}")
            logger.debug(f"Together response: {response}")
            completion_tokens += 1

            # -*- Parse response
            response_content: Optional[str]
            try:
                response_token = response.token  # type: ignore
                # logger.debug(f"Together response: {response_token}")
                # logger.debug(f"Together response type: {type(response_token)}")
                response_content = response_token.get("text")
                response_tool_call = response_token.get("tool_call")
                if response_tool_call:
                    response_is_tool_call = True
                # logger.debug(f"Together response content: {response_content}")
                # logger.debug(f"Together response_is_tool_call: {response_tool_call}")
            except Exception:
                response_content = response.choices[0].delta.content

            # -*- Add response content to agent message
            if response_content is not None:
                agent_message_content += response_content
                # -*- Yield content if not a tool call
                if not response_is_tool_call:
                    yield response_content

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create agent message
        agent_message = Message(
            role="agent",
            content=agent_message_content,
        )
        # -*- Check if the response is a tool call
        try:
            if response_is_tool_call and agent_message_content != "":
                _tool_call_content = agent_message_content.strip()
                _tool_call_list = json.loads(_tool_call_content)
                if isinstance(_tool_call_list, list):
                    # Build tool calls
                    _tool_calls: List[Dict[str, Any]] = []
                    logger.debug(f"Building tool calls from {_tool_call_list}")
                    for _tool_call in _tool_call_list:
                        tool_call_name = _tool_call.get("name")
                        tool_call_args = _tool_call.get("arguments")
                        _function_def = {"name": tool_call_name}
                        if tool_call_args is not None:
                            _function_def["arguments"] = json.dumps(tool_call_args)
                        _tool_calls.append(
                            {
                                "type": "function",
                                "function": _function_def,
                            }
                        )
                    agent_message.tool_calls = _tool_calls
        except Exception:
            logger.warning(f"Could not parse tool calls from response: {agent_message_content}")
            pass

        # -*- Update usage metrics
        # Add response time to metrics
        agent_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        logger.debug(f"Estimated completion tokens: {completion_tokens}")
        agent_message.metrics["completion_tokens"] = completion_tokens
        if "completion_tokens" not in self.metrics:
            self.metrics["completion_tokens"] = completion_tokens
        else:
            self.metrics["completion_tokens"] += completion_tokens

        # -*- Add agent message to messages
        messages.append(agent_message)
        agent_message.log()

        # -*- Parse and run tool calls
        if agent_message.tool_calls is not None:
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in agent_message.tool_calls:
                _tool_call_id = tool_call.get("id")
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(
                        Message(role="tool", tool_call_id=_tool_call_id, content="Could not find function to call.")
                    )
                    continue
                if _function_call.error is not None:
                    messages.append(
                        Message(
                            role="tool", tool_call_id=_tool_call_id, tool_call_error=True, content=_function_call.error
                        )
                    )
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    yield f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    yield "\nRunning:"
                    for _f in function_calls_to_run:
                        yield f"\n - {_f.get_call_str()}"
                    yield "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run)
            # Add results of the function calls to the messages
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
            # -*- Yield new response using results of tool calls
            yield from self.response_stream(messages=messages)
        logger.debug("---------- Together Response End ----------")
