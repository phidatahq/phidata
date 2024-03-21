from phi.assistant import Assistant
from phi.llm.cohere import Cohere

assistant = Assistant(
    llm=Cohere(model="command=r"), description="You help people with their health and fitness goals.", debug_mode=True
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True, stream=False)
