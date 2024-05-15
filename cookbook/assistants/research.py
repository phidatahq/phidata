from textwrap import dedent

from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.newspaper4k import Newspaper4k

assistant = Assistant(
    tools=[DuckDuckGo(), Newspaper4k()],
    description="You are a senior NYT researcher writing an article on a topic.",
    instructions=[
        "For the provided topic, search for the top 5 links.",
        "Then read each URL and extract the article text. If a URL isn't available, ignore and move on.",
        "Analyse and prepare an NYT worthy article based on the information.",
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
    # show_tool_calls=True,
    debug_mode=True,
    save_output_to_file="news_article.md",
)
assistant.print_response("Latest developments in AI", markdown=True)
