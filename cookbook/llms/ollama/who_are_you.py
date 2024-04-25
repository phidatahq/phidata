from phi.assistant import Assistant
from phi.llm.ollama import Ollama

prompt = "Who are you and who created you? Answer in 1 short sentence."
temp = 0.3
models = ["llama3", "phi3", "llava", "llama2", "mixtral", "openhermes", "tinyllama"]

for model in models:
    print(f"================ {model} ================")
    Assistant(llm=Ollama(model=model, options={"temperature": temp}), system_prompt=prompt).print_response(
        markdown=True
    )
