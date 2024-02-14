from phi.assistant import Assistant
from phi.llm.anyscale import Anyscale

assistant = Assistant(llm=Anyscale(model="mistralai/Mixtral-8x7B-Instruct-v0.1"))
assistant.cli_app(markdown=True)
