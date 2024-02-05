from phi.assistant import Assistant
from phi.llm.ollama import Ollama

prompt = "Who are you and who created you? Answer in 1 short sentence."

print("================ phi ================")
Assistant(llm=Ollama(model="phi"), system_prompt=prompt).print_response()

print("================ llava ================")
Assistant(llm=Ollama(model="llava"), system_prompt=prompt).print_response()

print("================ llama2 ================")
Assistant(llm=Ollama(model="llama2"), system_prompt=prompt).print_response()

print("================ mixtral ================")
Assistant(llm=Ollama(model="mixtral"), system_prompt=prompt).print_response()

print("================ openhermes ================")
Assistant(llm=Ollama(model="openhermes"), system_prompt=prompt).print_response()

print("================ tinyllama ================")
Assistant(llm=Ollama(model="tinyllama"), system_prompt=prompt).print_response()
