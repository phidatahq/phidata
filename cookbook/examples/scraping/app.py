from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.tools.jina_tools import JinaReaderTools

# Create an Assistant with JinaReaderTools
assistant = Assistant(
    llm=OpenAIChat(model="gpt-3.5-turbo"), tools=[JinaReaderTools(max_content_length=8000)], show_tool_calls=True
)

# Use the assistant to read a webpage
assistant.print_response("Search on openai.com for content related to Q* and summarize its main points", markdown=True)


# Use the assistant to search
# assistant.print_response("I there new release from phidata, provide your sources", markdown=True)
