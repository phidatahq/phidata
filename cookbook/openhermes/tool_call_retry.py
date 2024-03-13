import random

from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.ollama import Ollama
from phi.utils.log import logger


def is_system_working() -> str:
    """Use this function do something unreliable.

    Returns:
        The result from the unreliable function.
    """

    num = random.randint(0, 10000)
    logger.debug(f"Random number: {num}")
    if num > 1:
        raise IOError("Broken sauce, everything is hosed!!!111one")
    else:
        return "Awesome sauce!"


assistant = Assistant(
    llm=Ollama(model="openhermes"),
    tools=[is_system_working],
    show_tool_calls=True,
    # debug_mode=True
)
assistant.print_response("Tell me about OpenAI Sora", markdown=True)
