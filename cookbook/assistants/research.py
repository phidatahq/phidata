"""
The research Assistant searches for EXA for a topic
and writes an article in markdown format.
"""

from pathlib import Path
from textwrap import dedent
from datetime import datetime

from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.tools.exa import ExaTools

cwd = Path(__file__).parent.resolve()
scratch_dir = cwd.joinpath("scratch")
if not scratch_dir.exists():
    scratch_dir.mkdir(exist_ok=True, parents=True)

today = datetime.now().strftime("%Y-%m-%d")

assistant = Assistant(
    llm=OpenAIChat(model="gpt-4o"),
    tools=[ExaTools(start_published_date=today, type="keyword")],
    description="You are a senior NYT researcher writing an article on a topic.",
    instructions=[
        "For the provided topic, run 3 different searches.",
        "Read the results carefully and prepare a NYT worthy article.",
        "Focus on facts and make sure to provide references.",
    ],
    add_datetime_to_instructions=True,
    expected_output=dedent(
        """\
    An engaging, informative, and well-structured article in markdown format:

    ## Engaging Article Title

    ### Overview
    {give a brief introduction of the article and why the user should read this report}
    {make this section engaging and create a hook for the reader}

    ### Section 1
    {break the article into sections}
    {provide details/facts/processes in this section}

    ... more sections as necessary...

    ### Takeaways
    {provide key takeaways from the article}

    ### References
    - [Reference 1](link)
    - [Reference 2](link)
    - [Reference 3](link)

    ### About the Author
    {write a made up for yourself, give yourself a cyberpunk name and a title}

    - published on {date} in dd/mm/yyyy
    """
    ),
    markdown=True,
    save_output_to_file=str(scratch_dir.joinpath("{message}.md")),
    # show_tool_calls=True,
    # debug_mode=True,
)
assistant.print_response("Apple WWDC")
