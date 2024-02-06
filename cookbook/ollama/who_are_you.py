from phi.assistant import Assistant
from phi.llm.ollama import Ollama

temp = 0.3
question = "Who are you? Answer in 1 sentence."
models = ["phi", "llava", "llama2", "mixtral", "openhermes", "tinyllama"]

for model in models:
    print(f"================ {model} ================")
    Assistant(llm=Ollama(model=model), options={'temperature': temp}).print_response(question)
