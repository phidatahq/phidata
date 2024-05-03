from textwrap import dedent
from phi.assistant.team import Assistant
from phi.tools.serpapi_toolkit import SerpApiToolkit
from phi.tools.newspaper_toolkit import NewspaperToolkit


searcher = Assistant(
    name="Searcher",
    role="Searches for top URLs based on a topic",
    description=dedent(
        """\
    You are a world-class journalist for the New York Times. Given a topic, generate a list of 3 search terms
    for writing an article on that topic. Then search the web for each term, analyse the results
    and return the 10 most relevant URLs.
    """
    ),
    instructions=[
        "Given a topic, first generate a list of 3 search terms related to that topic.",
        "For each search term, `search_google` and analyze the results."
        "From the results of all searcher, return the 10 most relevant URLs to the topic.",
        "Remember: you are writing for the New York Times, so the quality of the sources is important.",
    ],
    tools=[SerpApiToolkit()],
    add_datetime_to_instructions=True,
)
writer = Assistant(
    name="Writer",
    role="Retrieves text from URLs and writes a high-quality article",
    description=dedent(
        """\
    You are a senior writer for the New York Times. Given a topic and a list of URLs,
    your goal is to write a high-quality NYT-worthy article on the topic.
    """
    ),
    instructions=[
        "Given a topic and a list of URLs, first read the article using `get_article_text`."
        "Then write a high-quality NYT-worthy article on the topic."
        "The article should be well-structured, informative, and engaging",
        "Ensure the length is at least as long as a NYT cover story -- at a minimum, 15 paragraphs.",
        "Ensure you provide a nuanced and balanced opinion, quoting facts where possible.",
        "Remember: you are writing for the New York Times, so the quality of the article is important.",
        "Focus on clarity, coherence, and overall quality.",
        "Never make up facts or plagiarize. Always provide proper attribution.",
    ],
    tools=[NewspaperToolkit()],
    add_datetime_to_instructions=True,
    add_chat_history_to_prompt=True,
    num_history_messages=3,
)

editor = Assistant(
    name="Editor",
    team=[searcher, writer],
    description="You are a senior NYT editor. Given a topic, your goal is to write a NYT worthy article.",
    instructions=[
        "Given a topic, ask the search journalist to search for the most relevant URLs for that topic.",
        "Then pass a description of the topic and URLs to the writer to get a draft of the article.",
        "Edit, proofread, and refine the article to ensure it meets the high standards of the New York Times.",
        "The article should be extremely articulate and well written. "
        "Focus on clarity, coherence, and overall quality.",
        "Ensure the article is engaging and informative.",
        "Remember: you are the final gatekeeper before the article is published.",
    ],
    add_datetime_to_instructions=True,
    # debug_mode=True,
    markdown=True,
)
editor.print_response("Write an article about latest developments in AI.")
