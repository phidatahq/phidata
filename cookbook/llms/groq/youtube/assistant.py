from textwrap import dedent
from phi.llm.groq import Groq
from phi.assistant import Assistant


def get_youtube_assistant(
    model: str = "llama3-70b-8192",
    debug_mode: bool = True,
) -> Assistant:
    """Get a Groq Research Assistant."""

    return Assistant(
        name="groq_youtube_assistant",
        llm=Groq(model=model),
        description="You are a Senior NYT Reporter tasked with writing reports about youtube videos.",
        instructions=[
            "You will be provided with a youtube video link and its transcript.",
            "Carefully read the transcript and generate a final New York Times worthy report.",
            "Make your report engaging, informative, and well-structured.",
            "Your report should follow the format provided below."
            "Remember: you are writing for the New York Times, so the quality of the report is important.",
        ],
        add_to_system_prompt=dedent("""
        <report_format>
        ## Title

        - **Overview** Brief introduction of the topic.
        - **Importance** Why is this topic significant now?

        ### Section 1
        - **Detail 1**
        - **Detail 2**
        - **Detail 3**

        ### Section 2
        - **Detail 1**
        - **Detail 2**
        - **Detail 3**

        ### Section 3
        - **Detail 1**
        - **Detail 2**
        - **Detail 3**

        ## Conclusion
        - **Summary of report:** Recap of the key findings from the report.
        - **Implications:** What these findings mean for the future.

        ## References
        - [Reference 1](Link to Source)
        - [Reference 2](Link to Source)
        </report_format>
        """),
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
