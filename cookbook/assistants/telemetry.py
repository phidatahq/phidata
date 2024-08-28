from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.utils.log import logger

assistant = Assistant(llm=OpenAIChat(model="gpt-4o"))
assistant.print_response("Share a 1 line joke")
