from phi.assistant import Assistant
from phi.llm.anthropic import Claude
from phi.tools.exa import ExaTools

assistant = Assistant(llm=Claude(), tools=[ExaTools()], show_tool_calls=True)
assistant.cli_app(markdown=True)
