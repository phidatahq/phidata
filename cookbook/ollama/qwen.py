from phi.assistant import Assistant
from phi.llm.ollama import Ollama

qwen = Assistant(llm=Ollama(model="qwen:7b"))

qwen.print_response("Give me a short introduction to large language model.")
qwen.print_response("Write a python function to calculate the factorial of a number.")
