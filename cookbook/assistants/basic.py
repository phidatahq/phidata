from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
# from phi.llm.groq import Groq
# from phi.llm.ollama import Ollama

assistant = Assistant(
    llm=OpenAIChat(model="gpt-4o"),
    # llm=Groq(model="llama3-70b-8192"),
    # llm=Ollama(model="llama3"),
    description="You help people with their health and fitness goals.",
    instructions=["Recipes should be under 5 ingredients"],
)
# -*- Print a response to the cli
assistant.print_response("Share a breakfast recipe.", markdown=True)
