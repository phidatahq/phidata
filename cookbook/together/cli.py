from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.together import Together

assistant = Assistant(
    llm=Together(), tools=[DuckDuckGo()], description="You help people with their health and fitness goals."
)
assistant.cli_app(markdown=True, stream=False)
