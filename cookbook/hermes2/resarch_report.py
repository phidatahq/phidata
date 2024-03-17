from pathlib import Path
from phi.assistant import Assistant, AssistantGroup
from phi.tools.exa import ExaTools
from phi.tools.website import WebsiteTools
from phi.tools.file import FileTools
from phi.llm.ollama import Hermes

hermes2 = Hermes(model="adrienbrault/nous-hermes2pro:Q8_0")
scratchpad = FileTools(base_dir=Path(__file__).parent / "scratchpad")

researcher = Assistant(
    # llm=hermes2,
    name="Researcher",
    role="Research information about a particular topic",
    description="You are an expert at researching complex topics",
    instructions=[
        "Your goal is to produce a detailed and thorough report on a topic",
        "Start by searching exa, then access each link in the result",
        "For each result, save important details about that article in a file named after that article. Make sure to save its link and important keywords",
        "After you have collected all the information, produce a detailed report on the from the information you have collected",
        "Save your report to the scratchpad.md file in markdown format",
    ],
    tools=[ExaTools(), WebsiteTools(), scratchpad],
    show_tool_calls=True,
)
writer = Assistant(
    # llm=hermes2,
    name="Writer",
    role="Summarize and write a report",
    description="You are an expert at writing easy to read reports. Your ability to summarize complex topics is unmatched",
    instructions=[
        "Your goal is to produce an easy to read report on a topic",
        "Start by reading the scratchpad.md file saved by the researcher",
        "Summarize the information in the scratchpad.md file in a new file named report.md",
        "Your report should be in markdown format",
        "The audience for you report is a general audience, so make sure to use simple language and avoid jargon",
    ],
    tools=[scratchpad],
    show_tool_calls=True,
)

team = AssistantGroup(name="AI Researcher", members=[researcher, writer], debug_mode=True)
team.print_response(
    "Write a research report on the different architectures of Large Language Foundation models", markdown=True
)
