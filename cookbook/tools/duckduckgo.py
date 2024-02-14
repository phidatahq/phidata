from phi.assistant import Assistant
from phi.tools.resend import ResendTools
from phi.tools.arxiv import ArxivTools

assistant = Assistant(tools=[ResendTools(), ArxivTools()], show_tool_calls=True)
assistant.print_response('search arxiv for quantum computing and send me an email of the summary on yash@phidata.com')
