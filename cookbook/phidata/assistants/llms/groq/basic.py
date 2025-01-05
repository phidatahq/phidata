from phi.assistant import Assistant
from phi.llm.groq import Groq

assistant = Assistant(
    llm=Groq(model="llama3-70b-8192"),
    description="You help people with their health and fitness goals.",
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True)
