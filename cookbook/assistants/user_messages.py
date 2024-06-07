from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat

Assistant(
    llm=OpenAIChat(model="gpt-3.5-turbo", stop="</answer>"),
    debug_mode=True,
).print_response(
    messages=[
        {"role": "user", "content": "What is the color of a banana? Provide your answer in the xml tag <answer>."},
        {"role": "assistant", "content": "<answer>"},
    ],
)
