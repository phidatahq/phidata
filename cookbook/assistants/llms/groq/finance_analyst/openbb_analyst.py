from openbb import obb
from phi.assistant import Assistant
from phi.llm.groq import Groq
from phi.tools.openbb_tools import OpenBBTools

assistant = Assistant(
    llm=Groq(model="llama3-70b-8192"),
    tools=[OpenBBTools(obb=obb, company_profile=True, company_news=True, price_targets=True)],
    show_tool_calls=True,
)

assistant.cli_app(markdown=True, stream=False, user="Groq")
# assistant.print_response("What's the stock price for meta", markdown=True, stream=False)
# assistant.print_response("Are analysts expecting meta to go up, share details", markdown=True, stream=False)
# assistant.print_response("What are analysts saying about NVDA", markdown=True, stream=False)
