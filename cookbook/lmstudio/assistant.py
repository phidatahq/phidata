from phi.assistant import Assistant
from phi.llm.openai.like import OpenAILike

assistant = Assistant(llm=OpenAILike(base_url="http://localhost:1234/v1"))
assistant.print_response("Share a 2 sentence quick healthy breakfast recipe.", markdown=True)
