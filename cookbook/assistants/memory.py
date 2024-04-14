from rich.pretty import pprint
from phi.assistant import Assistant, AssistantMemory

assistant = Assistant()

# -*- Print a response
assistant.print_response("Share a 5 word horror story.")

# -*- Get the memory
memory: AssistantMemory = assistant.memory

# -*- Print Chat History
print("============ Chat History ============")
pprint(memory.chat_history)

# -*- Print LLM Messages
print("============ LLM Messages ============")
pprint(memory.llm_messages)
