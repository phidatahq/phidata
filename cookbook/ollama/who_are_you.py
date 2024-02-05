from phi.assistant import Assistant
from phi.llm.ollama import Ollama

print("================ phi ================")
Assistant(llm=Ollama(model="phi"), system_prompt="Who are you? Answer in 1 sentence.").print_response()

print("================ llava ================")
Assistant(llm=Ollama(model="llava"), system_prompt="Who are you? Answer in 1 sentence.").print_response()
print("================ llama2 ================")
Assistant(llm=Ollama(model="llama2"), system_prompt="Who are you? Answer in 1 sentence.").print_response()

print("================ mixtral ================")
Assistant(llm=Ollama(model="mixtral"), system_prompt="Who are you? Answer in 1 sentence.").print_response()
