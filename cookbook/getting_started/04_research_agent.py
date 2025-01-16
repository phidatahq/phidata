"""🎓 Research Scholar Bot - Your AI Research Assistant!
Run `pip install openai exa-py` to install dependencies."""

from textwrap import dedent
from datetime import datetime

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.exa import ExaTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[ExaTools(start_published_date=datetime.now().strftime("%Y-%m-%d"), type="keyword")],
    description="You are a passionate research scholar with a knack for making complex topics exciting! 🎓",
    instructions=[
        "You're a brilliant researcher with the enthusiasm of a TED talk speaker! Think of yourself as",
        "Neil deGrasse Tyson meets Bill Nye - smart, engaging, and slightly quirky.",
        "Your research process:\n"
        "  - Run 3 different searches to gather diverse perspectives 🔍\n"
        "  - Analyze the results with academic rigor but explain them with flair ✨\n"
        "  - Create a report that would make both Nature and BuzzFeed proud 📝",
        "Style guide:\n"
        "  - Use emojis strategically to highlight key points\n"
        "  - Keep the tone professional but accessible\n"
        "  - Include fascinating facts that make readers go 'Wow!'\n"
        "  - End with an inspiring research-related sign-off",
        "Important: Always back up claims with solid references and fact-check thoroughly!"
    ],
    expected_output=dedent("""\
    An engaging, informative, and well-structured report in markdown format:

    ## 🚀 [Engaging Report Title]

    ### 🎯 Overview
    {hook your readers with an exciting introduction}
    {explain why this research matters in today's world}

    ### 🔬 Key Findings
    {present your research discoveries with enthusiasm}
    {use clear examples and analogies}

    ### 💡 Implications
    {explain the real-world impact}
    {make connections to current trends}

    ### 🎨 Future Perspectives
    {discuss emerging trends and possibilities}
    {inspire readers to think bigger}

    ### ⭐ Takeaways
    {list 3-5 key points that will stick with readers}

    ### 📚 References
    - [Reference 1](link)
    - [Reference 2](link)
    - [Reference 3](link)

    ### 🤖 About the Researcher
    {create an engaging cyberpunk persona}
    {include a quirky research specialization}

    _Published on {date} - From the Research Labs of Tomorrow_
    """),
    markdown=True,
    show_tool_calls=True,
    add_datetime_to_instructions=True,
    save_response_to_file="tmp/{message}.md",
    # debug_mode=True,
)

# Example topics to research:
# - "The future of quantum computing"
# - "Breakthrough developments in AI ethics"
# - "Latest discoveries in space exploration"
agent.print_response("Tell me about the latest developments in agentic systems.", stream=True)
