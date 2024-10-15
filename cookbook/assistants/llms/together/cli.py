from phi.assistant import Assistant
from phi.llm.together import Together

assistant = Assistant(llm=Together(), description="You help people with their health and fitness goals.")
assistant.cli_app(markdown=True, stream=False)
