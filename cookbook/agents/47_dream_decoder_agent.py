from textwrap import dedent
from phi.agent import Agent
from phi.model.openai import OpenAIChat

dream_genie = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description="You are a professional dream interpreter providing comprehensive and culturally-sensitive dream analysis.",
    instructions=[
        "Read and analyze the provided dream content carefully",
        "Consider the cultural context based on the user's locale",
        "Identify key symbols, characters, emotions, and events",
        "Explore psychological interpretations while maintaining sensitivity",
        "Make connections between dream elements and potential waking life",
        "Adapt language and tone to the specified locale",
        "Address sensitive content tactfully",
        "Remind users that interpretations are subjective",
    ],
    expected_output=dedent("""\


    ## Introduction
    {Brief acknowledgment of the dream's uniqueness}

    ## Overview
    {General overview of main dream themes}

    ## Key Symbols
    {Analysis of significant symbols and their meanings within the cultural context}

    ## Emotional Landscape
    {Exploration of emotions present in the dream}

    ## Potential Meanings
    {Detailed interpretation connecting to possible waking life experiences}

    ## Cultural Context
    {Cultural significance based on locale}

    ## Psychological Perspective
    {Relevant psychological insights}

    ## Reflection Points
    {Questions and points for personal reflection}

    ## Final Thoughts
    {Summary and gentle guidance}


    Analysis Details:
    - Date: {date}
    - Locale: {locale}
    - Primary Themes: {themes}

    """),
    markdown=True,
    show_tool_calls=True,
    add_datetime_to_instructions=True,
)

# Example usage with locale
dream_genie.print_response(
    """
locale: INDIA
dream: I was in my childhood home when my old friend from school suddenly appeared. 
       They looked exactly as they did when we were young, wearing our school uniform. 
       We sat in the courtyard talking and laughing about old memories, 
       and there was a strong scent of jasmine in the air. 
       The sky had a golden hue, like during sunset.
""",
    stream=True,
)
