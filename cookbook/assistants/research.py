from pathlib import Path
from textwrap import dedent

from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.tools.exa import ExaTools

cwd = Path(__file__).parent.resolve()
scratch_dir = cwd.joinpath("scratch")
if not scratch_dir.exists():
    scratch_dir.mkdir(exist_ok=True, parents=True)

assistant = Assistant(
    llm=OpenAIChat(model="gpt-4o"),
    tools=[ExaTools()],
    description="You are a senior NYT researcher writing an article on a topic.",
    instructions=[
        "For the provided topic, search for the top 10 links.",
        "Read the results carefully and prepare a NYT worthy article.",
    ],
    add_datetime_to_instructions=True,
    expected_output=dedent(
        """\
    An engaging, informative, and well-structured article in the following format:
    <article_format>
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
    - [Title](url)
    - [Title](url)
    - [Title](url)
    </article_format>\
    """
    ),
    markdown=True,
    # show_tool_calls=True,
    save_output_to_file=str(scratch_dir.joinpath("new_article.md")),
    # debug_mode=True,
)
assistant.print_response("OpenAI GPT-4o")
