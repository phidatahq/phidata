from textwrap import dedent

from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.tools.exa import ExaTools
from phi.tools.firecrawl import FirecrawlTools

assistant = Assistant(
    llm=OpenAIChat(model="gpt-4o"),
    tools=[ExaTools(type="keyword"), FirecrawlTools()],
    description="You are a venture capitalist at Redpoint Ventures writing a memo about investing in a company.",
    instructions=[
        "First search exa for Redpoint Ventures to learn about us.",
        # "Then use exa to search for '{company name} {current year}'.",
        "Then scrape the provided company urls to get more information about the company and the product.",
        "Then write a proposal to send to your investment committee."
        "Break the memo into sections and make a recommendation at the end.",
        "Make sure the title is catchy and engaging.",
    ],
    expected_output=dedent(
        """\
    An informative and well-structured memo in the following format:
    ## Engaging Memo Title

    ### Redpoint VC Overview
    {give a brief introduction of RidgeVC}

    ### Company Overview
    {give a brief introduction of the company}
    {make this section engaging and create a hook for the reader}

    ### Section 1
    {break the memo into sections like Market Opportunity, Betting on Innovation, Competitive Edge etc.}
    {provide details/facts/processes in this section}

    ... more sections as necessary...

    ### Proposal
    {provide a recommendation for investing in the company}
    {investment amount, valuation post money, equity stake and use of funds}
    {eg: We should invest $2M at a $20M post-money valuation for a 10% stake in the company.}

    ### Author
    RedVC, {date}
    """
    ),
    # This setting tells the LLM to format messages in markdown
    markdown=True,
    # This setting shows the tool calls in the output
    show_tool_calls=True,
    save_output_to_file="tmp/vc/{run_id}.md",
    add_datetime_to_instructions=True,
    # debug_mode=True,
)

assistant.print_response("""\
I am writing a memo on investing in the company phidata.
Please write a proposal for investing $2m @ $20m post to send to my investment committee.
- Company website: https://www.phidata.com
- Github project: https://github.com/phidatahq/phidata
- Documentation: https://docs.phidata.com/introduction\
""")
