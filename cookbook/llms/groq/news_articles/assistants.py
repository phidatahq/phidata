from textwrap import dedent

from phi.llm.groq import Groq
from phi.assistant import Assistant


def get_article_summarizer(
    model: str = "llama3-8b-8192",
    length: int = 500,
    debug_mode: bool = False,
) -> Assistant:
    return Assistant(
        name="Article Summarizer",
        llm=Groq(model=model),
        description="You are a Senior NYT Editor and your task is to summarize a newspaper article.",
        instructions=[
            "You will be provided with the text from a newspaper article.",
            "Carefully read the article a prepare a thorough report of key facts and details.",
            f"Your report should be less than {length} words.",
            "Provide as many details and facts as possible in the summary.",
            "Your report will be used to generate a final New York Times worthy report.",
            "REMEMBER: you are writing for the New York Times, so the quality of the report is important.",
            "Make sure your report is properly formatted and follows the <report_format> provided below.",
        ],
        add_to_system_prompt=dedent(
            """
        <report_format>
        **Overview:**\n
        {overview of the article}

        **Details:**\n
        {details/facts/main points from the article}

        **Key Takeaways:**\n
        {provide key takeaways from the article}
        </report_format>
        """
        ),
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )


def get_article_writer(
    model: str = "llama3-70b-8192",
    debug_mode: bool = False,
) -> Assistant:
    return Assistant(
        name="Article Summarizer",
        llm=Groq(model=model),
        description="You are a Senior NYT Editor and your task is to write a NYT cover story worthy article due tomorrow.",
        instructions=[
            "You will be provided with a topic and pre-processed summaries from junior researchers.",
            "Carefully read the provided information and think about the contents",
            "Then generate a final New York Times worthy article in the <article_format> provided below.",
            "Make your article engaging, informative, and well-structured.",
            "Break the article into sections and provide key takeaways at the end.",
            "Make sure the title is catchy and engaging.",
            "Give the section relevant titles and provide details/facts/processes in each section."
            "REMEMBER: you are writing for the New York Times, so the quality of the article is important.",
        ],
        add_to_system_prompt=dedent(
            """
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
        </article_format>
        """
        ),
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
