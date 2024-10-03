import os
from pathlib import Path
from dotenv import load_dotenv
from phi.tools.shell import ShellTools
from phi.tools.file import FileTools
from phi.llm.openai import OpenAIChat
from phi.assistant.web import WebAssistant

load_dotenv()


DEFAULT_MODEL = os.getenv("DEFAULT_MODEL") or "gpt-4o-mini"

cwd = Path(__file__).parent.resolve()
working_dir = cwd.joinpath("working_dir")
if not working_dir.exists():
    working_dir.mkdir(exist_ok=True, parents=True)

llm = OpenAIChat(model=DEFAULT_MODEL, max_tokens=8000, temperature=0.2)

agent = WebAssistant(
    description="You help write a full web site using web technologies.",
    instructions=[
        "When you recieved an input from the user do the following:\n"
        " - First **THINK** before writing any code.\n"
        " - Breakdown it into small manageable steps which you can do using the right tools.\n"
        " - Define for every step what tool(s) you need to use.\n"
        "After that, use the right tool to do every step as planned.",
        "Do not output any information about what you have to do, just perform your task.",
        # f"**IMPORTANT**: Save a summary file to output all the steps you took to accomplish your task into :{working_dir}summary.md",
    ],
    llm=llm,
    show_tool_calls=True,
    tools=[ShellTools, FileTools(base_dir=working_dir)],
    debug_mode=True,
)

result = agent.run("Build an agency website for AI development.")

if isinstance(result, dict):
    print(result)
else:
    for delta in result:
        print(delta, end="", flush=True)
